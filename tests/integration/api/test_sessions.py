"""`POST /api/v1/sessions`: one record from a device (TRD 05 API-030..API-047; TRD 10 ING-001..
ING-004; FEAT-023, FEAT-025)."""

from __future__ import annotations

import csv
import json
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.models import FEATURE_KEYS, ProcessedSession, RawSession, SessionStatus
from backend.repositories.device_repository import DeviceRepository
from backend.repositories.resident_repository import ResidentRepository
from backend.services.pipeline_runner import (
    ExecutorResult,
    InterimExecutor,
    RunHandle,
    SessionFactory,
)
from tests.integration.api.conftest import LogCapture, Principals

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[3]
SRC_05 = ROOT / "tests" / "fixtures" / "pipeline_input" / "EchoWell_pipeline_test_input_v0_1.csv"
SESSIONS = "/api/v1/sessions"
TEXT_FIELDS = {
    "schema_version", "session_id", "resident_id", "device_id", "timestamp_utc",
    "audio_quality_flag", "extraction_software_version", "device_firmware_version", "phrase_id",
}  # fmt: skip


def src05_record(session_id: str) -> dict[str, Any]:
    """One SRC-05 row as a JSON record (numbers as JSON numbers)."""
    with SRC_05.open(newline="", encoding="utf-8") as handle:
        row = next(r for r in csv.DictReader(handle) if r["session_id"] == session_id)
    return {
        k: v if k in TEXT_FIELDS else int(v) if k == "number_of_pauses" else float(v)
        for k, v in row.items()
    }


def _count(session: Session, table: str) -> int:
    return int(session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())  # noqa: S608


def _problem(response: Any, status: int, code: str) -> dict[str, Any]:
    assert response.status_code == status, response.text
    body: dict[str, Any] = response.json()
    assert body["type"] == f"urn:echowell:error:{code}", body
    return body


LATE = "late arrival (not used for baseline or scores)"


class UsableExecutor:
    """Stands in for FEAT-053: marks every unprocessed arrival of the scope `usable` as a late
    arrival, a valid row that needs no epoch."""

    def __init__(self) -> None:
        self.runs: list[RunHandle] = []

    def execute(self, session_factory: SessionFactory, run: RunHandle) -> ExecutorResult:
        self.runs.append(run)
        tz = ZoneInfo("America/Chicago")
        with session_factory() as session, session.begin():
            done = select(ProcessedSession.raw_session_id)
            rows = session.scalars(
                select(RawSession).where(
                    RawSession.resident_code.in_(list(run.scope)), RawSession.id.not_in(done)
                )
            ).all()
            for raw in rows:
                local = raw.timestamp_utc.astimezone(tz)
                session.add(
                    ProcessedSession(
                        raw_session_id=raw.id,
                        session_id=raw.session_id,
                        resident_id=raw.resident_id,
                        status=SessionStatus.USABLE,
                        reasons=[LATE],
                        reason_text=LATE,
                        late_arrival=True,
                        timestamp_utc=raw.timestamp_utc,
                        local_date=local.date(),
                        local_time=local.time().replace(microsecond=0),
                        is_morning=local.hour < 12,
                        adjusted_features={k: float(getattr(raw, k)) for k in FEATURE_KEYS},
                        pipeline_run_id=run.id,
                    )
                )
        return ExecutorResult(counts=_counts(arrivals=len(rows), usable=len(rows)))


def _counts(**values: int) -> dict[str, int]:
    keys = ("arrivals", "usable", "set_aside", "quarantined", "duplicate", "missing_resident",
            "missing_device_gap", "late_arrival", "scored", "alerts_opened",
            "excluded_after_as_of", "residents")  # fmt: skip
    return {key: values.get(key, 0) for key in keys}


def _app(api: TestClient) -> FastAPI:
    app: FastAPI = api.app  # type: ignore[assignment]
    return app


@pytest.mark.req("TST-043", "API-042", "API-046", "AC-API-05", "FEAT-025-AC-01", "FEAT-025-FR-06",
                 "FEAT-025-FR-10", "FEAT-025-FR-12", "ING-029", "ING-010")  # fmt: skip
def test_valid_record_is_stored_and_processed(
    api: TestClient, roster: Session, principals: Principals
) -> None:
    executor = UsableExecutor()
    _app(api).state.pipeline_executor = executor
    record = src05_record("R09-20261021-01")
    body = json.dumps(record)
    response = api.post(SESSIONS, content=body, headers={
        **principals.api_key("ingest"), "Content-Type": "application/json"})  # fmt: skip
    assert response.status_code == 201, response.text
    result = response.json()
    assert set(result) == {"raw_session_id", "arrival_seq", "session_id",
                           "status_after_processing", "reasons", "pipeline_run_id"}  # fmt: skip
    assert result["session_id"] == "R09-20261021-01"
    assert result["status_after_processing"] == "usable"
    assert result["reasons"] == [LATE]
    rows = roster.scalars(select(RawSession)).all()
    assert len(rows) == 1
    raw = rows[0]
    assert raw.payload == record
    assert str(raw.id) == result["raw_session_id"]
    assert raw.arrival_seq == result["arrival_seq"]
    assert raw.ingest_batch_id is None
    assert raw.api_key_id == principals.keys["ingest"].id
    assert raw.loudness_dbfs == record["loudness_dbfs"]
    assert _count(roster, "ingest_batches") == 0
    run = executor.runs[0]
    assert str(run.id) == result["pipeline_run_id"]
    assert run.trigger.value == "ingest"
    assert "R09" in run.scope
    status = roster.execute(
        text("SELECT status FROM pipeline_runs WHERE id = :i"), {"i": run.id}
    ).scalar_one()
    assert status == "succeeded"
    device = DeviceRepository(roster).get_by_code("D09")
    assert device is not None
    assert device.firmware_version_last == record["device_firmware_version"]


@pytest.mark.req("TST-037", "AC-ING-11", "API-047", "D-52", "FEAT-025-AC-05", "FEAT-025-FR-11",
                 "FEAT-024-FR-01")  # fmt: skip
def test_failed_run_answers_pending(
    api: TestClient, roster: Session, principals: Principals
) -> None:
    _app(api).state.pipeline_executor = InterimExecutor()  # a run that fails
    response = api.post(SESSIONS, json=src05_record("R09-20261021-01"),
                        headers=principals.api_key("ingest"))  # fmt: skip
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["status_after_processing"] == "pending"
    assert result["reasons"] == []
    run = roster.execute(
        text("SELECT status, error_message, trigger FROM pipeline_runs WHERE id = :i"),
        {"i": result["pipeline_run_id"]},
    ).one()
    assert tuple(run) == ("failed", "pipeline not available until Phase 6", "ingest")
    assert _count(roster, "raw_sessions") == 1
    # the next successful run processes the stored record
    executor = UsableExecutor()
    _app(api).state.pipeline_executor = executor
    second = api.post(SESSIONS, json=src05_record("R09-20261022-01"),
                      headers=principals.api_key("ingest"))  # fmt: skip
    assert second.json()["status_after_processing"] == "usable"
    statuses = roster.execute(
        text("SELECT session_id, status FROM processed_sessions ORDER BY session_id")
    ).all()
    assert [tuple(s) for s in statuses] == [
        ("R09-20261021-01", "usable"),
        ("R09-20261022-01", "usable"),
    ]


@pytest.mark.req("TST-044", "AC-API-05", "API-044", "ING-003", "FEAT-025-AC-02", "FEAT-025-FR-08",
                 "ING-037")  # fmt: skip
def test_repeat_session_id_is_a_duplicate(
    api: TestClient, roster: Session, principals: Principals
) -> None:
    record = src05_record("R09-20261021-01")
    first = api.post(SESSIONS, json=record, headers=principals.api_key("ingest"))
    runs = _count(roster, "pipeline_runs")
    again = api.post(SESSIONS, json=record, headers=principals.api_key("ingest"))
    assert again.status_code == 200
    result = again.json()
    assert result["status_after_processing"] == "duplicate"
    assert result["reasons"] == ["session_id already received"]
    assert result["pipeline_run_id"] is None
    assert result["arrival_seq"] > first.json()["arrival_seq"]
    assert _count(roster, "raw_sessions") == 2
    assert _count(roster, "pipeline_runs") == runs
    changed = api.post(SESSIONS, json={**record, "hnr_db": record["hnr_db"] + 1},
                       headers=principals.api_key("ingest"))  # fmt: skip
    warnings = roster.execute(
        text("SELECT ingest_warnings FROM raw_sessions WHERE id = :i"),
        {"i": changed.json()["raw_session_id"]},
    ).scalar_one()
    assert "duplicate_payload_differs" in {w["code"] for w in warnings}


@pytest.mark.req("TST-045", "AC-API-06", "API-041", "ING-004", "ING-033", "FEAT-025-AC-03",
                 "FEAT-025-FR-03", "FEAT-023-AC-04")  # fmt: skip
def test_unknown_resident_is_rejected_and_stored(
    api: TestClient, roster: Session, principals: Principals
) -> None:
    record = {**src05_record("R09-20261021-01"), "resident_id": "R11",
              "session_id": "R11-20261021-01"}  # fmt: skip
    body = json.dumps(record, separators=(",", ":"))
    response = api.post(SESSIONS, content=body, headers={
        **principals.api_key("ingest"), "Content-Type": "application/json"})  # fmt: skip
    problem = _problem(response, 422, "UNKNOWN_RESIDENT")
    rejection = roster.execute(
        text("SELECT raw_body, errors, ingest_batch_id, row_number, api_key_id "
             "FROM ingest_rejections")
    ).one()  # fmt: skip
    assert rejection.raw_body == record
    assert rejection.errors == problem["errors"]
    assert rejection.ingest_batch_id is None
    assert rejection.row_number is None
    assert rejection.api_key_id == principals.keys["ingest"].id
    assert _count(roster, "raw_sessions") == 0
    assert _count(roster, "pipeline_runs") == 0


@pytest.mark.req("AC-API-07", "ING-012", "FR-015", "FEAT-025-AC-04", "FEAT-023-AC-01",
                 "FEAT-025-FR-13")  # fmt: skip
def test_extra_field_and_audio_are_refused(
    api: TestClient, roster: Session, principals: Principals
) -> None:
    record = {**src05_record("R09-20261021-01"), "audio_base64": "UklGRg=="}
    problem = _problem(api.post(SESSIONS, json=record, headers=principals.api_key("ingest")),
                       422, "VALIDATION_ERROR")  # fmt: skip
    assert problem["errors"][0]["code"] == "extra_forbidden"
    rejected = _count(roster, "ingest_rejections")
    audio = api.post(SESSIONS, content=b"RIFF....WAVE", headers={
        **principals.api_key("ingest"), "Content-Type": "audio/wav"})  # fmt: skip
    _problem(audio, 415, "UNSUPPORTED_MEDIA_TYPE")
    assert _count(roster, "ingest_rejections") == rejected
    assert _count(roster, "raw_sessions") == 0


@pytest.mark.req("AC-ING-05", "FEAT-023-AC-03")
def test_version_and_timestamp_problems(
    api: TestClient, roster: Session, principals: Principals
) -> None:
    record = src05_record("R09-20261021-01")
    key = principals.api_key("ingest")
    newer = api.post(SESSIONS, json={**record, "schema_version": "0.2"}, headers=key)
    _problem(newer, 422, "UNSUPPORTED_SCHEMA_VERSION")
    iso = api.post(SESSIONS, json={**record, "timestamp_utc": "2026-10-01T19:45:11Z"}, headers=key)
    problem = _problem(iso, 422, "VALIDATION_ERROR")
    assert [(e["field"], e["code"]) for e in problem["errors"]] == [
        ("timestamp_utc", "invalid_format")
    ]
    _problem(api.post(SESSIONS, content=b"{not json", headers={
        **principals.api_key("ingest"), "Content-Type": "application/json"}), 422,
        "VALIDATION_ERROR")  # fmt: skip


@pytest.mark.req("AC-ING-10", "API-038", "FEAT-025-AC-07", "FEAT-023-FR-15")
def test_withdrawn_resident(api: TestClient, roster: Session, principals: Principals) -> None:
    residents = ResidentRepository(roster)
    resident = residents.get_by_code("R09")
    assert resident is not None
    residents.set_withdrawn(resident, date(2026, 10, 20))
    roster.commit()
    response = api.post(
        SESSIONS, json=src05_record("R09-20261021-01"), headers=principals.api_key("ingest")
    )
    problem = _problem(response, 422, "RESIDENT_WITHDRAWN")
    assert problem["detail"] == "resident withdrawn"


@pytest.mark.req("API-040", "SEC-023", "FEAT-023-AC-08", "FEAT-025-FR-04")
def test_device_bound_key_refuses_another_device(
    api: TestClient, roster: Session, principals: Principals
) -> None:
    d01 = DeviceRepository(roster).get_by_code("D01")
    assert d01 is not None
    principals.add_key("bound", ["ingest:write"], device_id=d01.id)
    record = src05_record("R09-20261021-01")  # recorded by D09
    _problem(api.post(SESSIONS, json=record, headers=principals.api_key("bound")), 403,
             "DEVICE_KEY_MISMATCH")  # fmt: skip
    stored = roster.execute(text("SELECT raw_body, errors FROM ingest_rejections")).one()
    assert stored.raw_body == record
    assert stored.errors[0]["code"] == "device_key_mismatch"
    assert _count(roster, "raw_sessions") == 0
    own = src05_record("R01-20261001-01")
    assert api.post(SESSIONS, json=own, headers=principals.api_key("bound")).status_code == 201


@pytest.mark.req("ING-001", "API-030", "FEAT-025-FR-01", "TRD 12 §4.6")
def test_only_an_ingest_key_may_post(
    api: TestClient, roster: Session, principals: Principals
) -> None:
    record = src05_record("R09-20261021-01")
    _problem(api.post(SESSIONS, json=record, headers=principals.bearer("admin")), 401,
             "NOT_AUTHENTICATED")  # fmt: skip
    _problem(api.post(SESSIONS, json=record, headers=principals.api_key("pipeline")), 403,
             "FORBIDDEN")  # fmt: skip


@pytest.mark.req("LOG-050", "LOG-051", "ING-057", "API-056", "FEAT-025-AC-08", "FEAT-025-FR-16",
                 "FEAT-025-FR-17")  # fmt: skip
def test_logs_carry_no_feature_value_or_key(
    api: TestClient, roster: Session, principals: Principals, log_capture: LogCapture
) -> None:
    record = {**src05_record("R09-20261021-01"), "mfcc1": 31.4159265}
    headers = principals.api_key("ingest")
    log_capture.start()
    api.post(SESSIONS, json=record, headers=headers)
    api.post(SESSIONS, json={**record, "pause_fraction": 1.5}, headers=headers)
    api.post(SESSIONS, json=record, headers=headers)
    lines = log_capture.lines()
    events = [line.get("event") for line in lines]
    assert events.count("ingest_request") == 3
    assert events.count("ingest_record_rejected") == 1
    assert events.count("ingest_duplicate") == 1
    rejected = next(line for line in lines if line.get("event") == "ingest_record_rejected")
    assert rejected["level"] == "WARNING"
    assert rejected["session_id"] == "R09-20261021-01"
    dumped = json.dumps(lines)
    assert "31.4159" not in dumped
    assert "1.5" not in json.dumps(
        [line for line in lines if line.get("event") != "request_completed"]
    )
    assert principals.raw_keys["ingest"] not in dumped


@pytest.mark.req("LOG-052", "FEAT-025-AC-09", "FEAT-025-FR-15")
def test_database_unavailable_is_503(app_factory: Callable[..., FastAPI]) -> None:
    app = app_factory(
        database_url="postgresql+psycopg://u:p@127.0.0.1:9/x",
        database_readonly_url="postgresql+psycopg://u:p@127.0.0.1:9/x",
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(SESSIONS, json=src05_record("R09-20261021-01"),
                               headers={"X-API-Key": "ewk_any"})  # fmt: skip
    _problem(response, 503, "SERVICE_UNAVAILABLE")
    assert response.headers["retry-after"] == "30"
