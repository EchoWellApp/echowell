"""`POST /api/v1/ingest` (JSON batch and CSV upload) and `GET /api/v1/ingest/batches/{id}`
(TRD 05 API-048..API-056; TRD 10 ING-005..ING-012, ING-031, ING-053, ING-055; FEAT-023,
FEAT-026)."""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.repositories.config_repository import ConfigRepository
from backend.services.ingestion import check_startup_name_map
from backend.services.validation import CANONICAL_FIELDS, NameMapError
from tests.conftest import make_settings
from tests.integration.api.conftest import Principals
from tests.integration.api.test_sessions import src05_record

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[3]
SRC_05 = ROOT / "tests" / "fixtures" / "pipeline_input" / "EchoWell_pipeline_test_input_v0_1.csv"
SRC_06 = ROOT / "tests" / "fixtures" / "legacy" / "echowell_mock_data_500.csv"
INGEST = "/api/v1/ingest"
TABLES = ("raw_sessions", "ingest_rejections", "ingest_batches", "pipeline_runs")


def _counts(session: Session) -> dict[str, int]:
    return {
        table: int(session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())  # noqa: S608
        for table in TABLES
    }


def _upload(
    api: TestClient,
    data: bytes,
    headers: dict[str, str],
    name: str = "input.csv",
    media_type: str = "text/csv",
) -> Any:
    return api.post(INGEST, files={"file": (name, data, media_type)}, headers=headers)


def _problem(response: Any, status: int, code: str) -> dict[str, Any]:
    assert response.status_code == status, response.text
    body: dict[str, Any] = response.json()
    assert body["type"] == f"urn:echowell:error:{code}", body
    return body


@pytest.mark.req("TST-046", "AC-ING-01", "API-052", "API-053", "ING-032", "FEAT-026-AC-01",
                 "FEAT-026-AC-10", "FEAT-026-FR-09", "FEAT-026-FR-11", "FEAT-026-FR-14",
                 "FEAT-026-FR-15")  # fmt: skip
def test_src05_upload(api: TestClient, roster: Session, principals: Principals) -> None:
    response = _upload(api, SRC_05.read_bytes(), principals.bearer("admin"))
    assert response.status_code == 202, response.text
    body = response.json()
    assert {k: body[k] for k in ("source", "accepted", "rejected", "duplicates")} == {
        "source": "csv_upload", "accepted": 283, "rejected": 0, "duplicates": 2,
    }  # fmt: skip
    assert body["pipeline_run_id"] is not None
    with SRC_05.open(newline="", encoding="utf-8") as handle:
        expected = [row["session_id"] for row in csv.DictReader(handle)]
    stored = (
        roster.execute(text("SELECT session_id FROM raw_sessions ORDER BY arrival_seq"))
        .scalars()
        .all()
    )
    assert stored == expected
    batch = roster.execute(
        text("SELECT source, filename, record_count, accepted_count, rejected_count, "
             "duplicate_count, uploaded_by, api_key_id, pipeline_run_id FROM ingest_batches")
    ).one()  # fmt: skip
    assert tuple(batch[:8]) == ("csv_upload", "input.csv", 283, 283, 0, 2,
                                principals.users["admin"].id, None)  # fmt: skip
    assert str(batch.pipeline_run_id) == body["pipeline_run_id"]  # D-124
    runs = roster.execute(text("SELECT id, trigger, status FROM pipeline_runs")).all()
    assert [(str(r.id), r.trigger, r.status) for r in runs] == [
        (body["pipeline_run_id"], "ingest", "succeeded")  # executed in the background
    ]
    payload = roster.execute(
        text("SELECT payload FROM raw_sessions ORDER BY arrival_seq LIMIT 1")
    ).scalar_one()
    assert payload["loudness_dbfs"] == "-30.67"  # the CSV cell text as received (ING-029)


@pytest.mark.req("AC-ING-03", "ING-008", "ING-039", "FEAT-026-AC-06", "FEAT-026-FR-12",
                 "FEAT-026-AC-10")  # fmt: skip
def test_reupload_is_all_duplicates(
    api: TestClient, roster: Session, principals: Principals
) -> None:
    headers = principals.bearer("admin")
    _upload(api, SRC_05.read_bytes(), headers)
    runs = _counts(roster)["pipeline_runs"]
    again = _upload(api, SRC_05.read_bytes(), headers).json()
    assert (again["accepted"], again["duplicates"], again["rejected"]) == (283, 283, 0)
    assert again["pipeline_run_id"] is None
    assert _counts(roster)["pipeline_runs"] == runs


@pytest.mark.req("TST-047", "AC-API-17", "AC-ING-06", "ING-055", "FR-032", "FEAT-026-AC-02",
                 "FEAT-026-FR-07", "FEAT-026-FR-19")  # fmt: skip
def test_legacy_file_is_refused(api: TestClient, roster: Session, principals: Principals) -> None:
    before = _counts(roster)
    response = _upload(api, SRC_06.read_bytes(), principals.bearer("admin"), SRC_06.name)
    problem = _problem(response, 422, "CSV_HEADER_MISMATCH")
    fields = {(e["field"], e["code"]) for e in problem["errors"]}
    assert ("speech_feature_1", "extra_forbidden") in fields
    assert ("loudness_dbfs", "missing_field") in fields
    assert _counts(roster) == before


@pytest.mark.req("ING-053", "AC-ING-06", "FEAT-026-AC-03", "FEAT-026-FR-06")
def test_answer_key_columns_are_refused(
    api: TestClient, roster: Session, principals: Principals
) -> None:
    lines = SRC_05.read_text(encoding="utf-8").splitlines()
    lines[0] += ",expected_status"
    lines[1:] = [line + ",usable" for line in lines[1:3]]
    before = _counts(roster)
    response = _upload(api, "\n".join(lines).encode(), principals.bearer("admin"))
    problem = _problem(response, 422, "CSV_HEADER_MISMATCH")
    assert {"field": "expected_status", "code": "extra_forbidden",
            "message": "This column is not part of schema v0.1."} in problem["errors"]  # fmt: skip
    assert _counts(roster) == before


@pytest.mark.req("ING-007", "API-050", "ING-012", "ING-053", "FEAT-026-AC-04", "FEAT-026-FR-01",
                 "FEAT-026-FR-04")  # fmt: skip
def test_envelope_errors_store_nothing(
    api: TestClient, roster: Session, principals: Principals
) -> None:
    headers = principals.bearer("admin")
    before = _counts(roster)
    _problem(api.post(INGEST, json={"records": []}, headers=headers), 422, "EMPTY_BATCH")
    _problem(api.post(INGEST, json={"records": [{}] * 5001}, headers=headers), 413,
             "PAYLOAD_TOO_LARGE")  # fmt: skip
    _problem(api.post(INGEST, json={"rows": []}, headers=headers), 422, "VALIDATION_ERROR")
    _problem(api.post(INGEST, content=b"{oops", headers={**headers,
             "Content-Type": "application/json"}), 422, "VALIDATION_ERROR")  # fmt: skip
    _problem(api.post(INGEST, content=b"RIFF", headers={**headers, "Content-Type": "audio/wav"}),
             415, "UNSUPPORTED_MEDIA_TYPE")  # fmt: skip
    _problem(_upload(api, b"PK\x03\x04", headers, "input.xlsx",
                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
             415, "UNSUPPORTED_MEDIA_TYPE")  # fmt: skip
    _problem(_upload(api, b"x", headers, "notes.wav", "audio/wav"), 415, "UNSUPPORTED_MEDIA_TYPE")
    header_only = SRC_05.read_text(encoding="utf-8").splitlines()[0].encode()
    _problem(_upload(api, header_only, headers), 422, "EMPTY_BATCH")
    assert _counts(roster) == before


@pytest.mark.req("ING-006", "ING-007", "API-051", "ING-032", "D-84", "FEAT-026-AC-05",
                 "FEAT-026-FR-08", "FEAT-026-FR-10")  # fmt: skip
def test_record_errors_do_not_fail_the_batch(
    api: TestClient, roster: Session, principals: Principals
) -> None:
    records = [
        src05_record("R01-20261001-01"),
        {**src05_record("R02-20261001-01"), "audio_quality_flag": "bad"},
        src05_record("R03-20261001-01"),
    ]
    response = api.post(INGEST, json={"records": records}, headers=principals.api_key("ingest"))
    assert response.status_code == 202, response.text
    body = response.json()
    assert (body["source"], body["accepted"], body["rejected"]) == ("api_batch", 2, 1)
    rejection = roster.execute(
        text("SELECT row_number, errors, raw_body, ingest_batch_id FROM ingest_rejections")
    ).one()
    assert rejection.row_number == 2
    assert [e["code"] for e in rejection.errors] == ["invalid_enum"]
    assert rejection.raw_body == records[1]
    assert str(rejection.ingest_batch_id) == body["ingest_batch_id"]
    batch = roster.execute(text("SELECT uploaded_by, api_key_id FROM ingest_batches")).one()
    assert tuple(batch) == (None, principals.keys["ingest"].id)


@pytest.mark.req("ING-058", "TST-053", "AC-SEC-09", "FEAT-026-AC-07", "FEAT-026-FR-13")
def test_batch_is_audited_with_the_request_id(
    api: TestClient, roster: Session, principals: Principals
) -> None:
    records = [src05_record("R01-20261001-01")]
    response = api.post(INGEST, json={"records": records}, headers=principals.bearer("admin"))
    body = response.json()
    rows = roster.execute(
        text("SELECT actor_type, actor_id, entity_type, entity_id, details, request_id "
             "FROM audit_logs WHERE action = 'ingest.batch.received'")
    ).all()  # fmt: skip
    assert len(rows) == 1
    row = rows[0]
    assert (row.actor_type, row.actor_id) == ("user", str(principals.users["admin"].id))
    assert (row.entity_type, row.entity_id) == ("ingest_batch", body["ingest_batch_id"])
    assert row.details == {
        "source": "api_batch", "record_count": 1, "accepted": 1, "rejected": 0,
        "duplicates": 0, "pipeline_run_id": body["pipeline_run_id"],
    }  # fmt: skip
    assert row.request_id == response.headers["x-request-id"]


@pytest.mark.req("ING-009", "API-054", "DME-005", "TST-061", "FEAT-026-AC-08", "FEAT-026-AC-09",
                 "FEAT-026-FR-17", "FEAT-026-FR-02", "FEAT-021-AC-06")  # fmt: skip
def test_batch_detail_and_roles(api: TestClient, roster: Session, principals: Principals) -> None:
    _problem(api.post(INGEST, json={"records": [src05_record("R01-20261001-01")]},
                      headers=principals.bearer("clinician")), 403, "FORBIDDEN")  # fmt: skip
    records = [src05_record("R01-20261001-01"), {**src05_record("R02-20261001-01"), "hnr_db": "x"}]
    created = api.post(INGEST, json={"records": records}, headers=principals.bearer("admin")).json()
    url = f"{INGEST}/batches/{created['ingest_batch_id']}"
    detail = api.get(url, headers=principals.bearer("researcher"))
    assert detail.status_code == 200
    batch = detail.json()
    assert set(batch) == {"id", "source", "filename", "record_count", "accepted_count",
                          "rejected_count", "duplicate_count", "uploaded_by", "received_at",
                          "pipeline_run_id", "rejections"}  # fmt: skip
    assert batch["pipeline_run_id"] == created["pipeline_run_id"]
    assert batch["uploaded_by"] == str(principals.users["admin"].id)
    assert [(r["row_number"], r["session_id"]) for r in batch["rejections"]] == [
        (2, "R02-20261001-01")
    ]
    assert batch["rejections"][0]["errors"] == [
        {"field": "hnr_db", "code": "invalid_type", "message": "hnr_db must be a JSON number."}
    ]
    assert "raw_body" not in detail.text
    assert "payload" not in detail.text
    _problem(api.get(url, headers=principals.bearer("clinician")), 403, "FORBIDDEN")
    _problem(api.get(f"{INGEST}/batches/00000000-0000-4000-8000-000000000000",
                     headers=principals.bearer("admin")), 404, "BATCH_NOT_FOUND")  # fmt: skip
    _problem(api.get(f"{INGEST}/batches/not-a-uuid", headers=principals.bearer("admin")), 422,
             "INVALID_QUERY_PARAMETER")  # fmt: skip


@pytest.mark.req("AC-ING-08", "ING-016", "ING-018", "TST-031", "FEAT-023-AC-05")
def test_mapped_header_is_accepted(
    api: TestClient, roster: Session, principals: Principals
) -> None:
    mapping = {name: name for name in CANONICAL_FIELDS if name != "loudness_dbfs"}
    mapping["Loudness_sma3_amean"] = "loudness_dbfs"
    ConfigRepository(roster).update_value("test_v0_1", "feature_name_map", mapping)
    roster.commit()
    rows = list(csv.reader(io.StringIO(SRC_05.read_text(encoding="utf-8"))))
    rows[0] = ["Loudness_sma3_amean" if c == "loudness_dbfs" else c for c in rows[0]]
    out = io.StringIO()
    csv.writer(out, lineterminator="\r\n").writerows(rows[:3])
    response = _upload(api, ("﻿" + out.getvalue()).encode(), principals.bearer("admin"))
    assert response.status_code == 202, response.text
    assert response.json()["accepted"] == 2
    stored = roster.execute(
        text("SELECT loudness_dbfs, payload FROM raw_sessions ORDER BY arrival_seq LIMIT 1")
    ).one()
    assert stored.loudness_dbfs == -30.67
    assert stored.payload["Loudness_sma3_amean"] == "-30.67"
    assert "loudness_dbfs" not in stored.payload


@pytest.mark.req("ING-017", "FEAT-023-FR-02", "FEAT-023-AC-06")
def test_invalid_name_map_stops_startup(roster: Session) -> None:
    bind = roster.connection()

    def factory() -> Session:
        return Session(bind=bind, join_transaction_mode="create_savepoint")

    settings = make_settings()
    assert check_startup_name_map(factory, settings) is True
    broken = {"A": "loudness_dbfs", "B": "loudness_dbfs"}
    ConfigRepository(roster).update_value("test_v0_1", "feature_name_map", broken)
    roster.commit()
    with pytest.raises(NameMapError):
        check_startup_name_map(factory, settings)
