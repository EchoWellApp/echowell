"""Pipeline runner and persistence on PostgreSQL (TRD 07 §4.8 ANL-033..ANL-041, ANL-060; TRD 06
DB-013..DB-019, DB-036; FEAT-053).

SRC-05 is uploaded through `POST /api/v1/ingest` (its own background run is replaced by a failing
interim run), then the analytics executor runs with the test as-of. All writes stay in the test's
rolled-back transaction.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from backend.models import PipelineRunStatus, PipelineTrigger
from backend.services import pipeline_persistence
from backend.services.pipeline_runner import InterimExecutor, PipelineRunner
from tests.conftest import make_settings
from tests.integration.api.conftest import Principals
from tests.integration.api.test_sessions import SRC_05, src05_record
from tests.unit.analytics.src05 import result as engine_result

pytestmark = pytest.mark.integration

AS_OF = datetime(2026, 10, 30, 20, 0, tzinfo=UTC)
COUNTS = {"arrivals": 283, "usable": 267, "set_aside": 12, "quarantined": 2, "duplicate": 2,
          "missing_resident": 17, "missing_device_gap": 2, "late_arrival": 0, "scored": 98,
          "alerts_opened": 2, "excluded_after_as_of": 0, "residents": 10}  # fmt: skip
DERIVED = ("epochs", "processed_sessions", "baselines", "scores", "cusum_state", "day_ledger",
           "alerts", "data_alerts")  # fmt: skip
VOLATILE = {"id", "created_at", "updated_at", "pipeline_run_id", "epoch_id",
            "processed_session_id", "last_detected_at"}  # fmt: skip


@pytest.fixture
def runner(app_conn: Connection) -> PipelineRunner:
    def factory() -> Session:
        return Session(bind=app_conn, join_transaction_mode="create_savepoint")

    return PipelineRunner(factory, make_settings())


@pytest.fixture
def uploaded(api: TestClient, roster: Session, principals: Principals) -> Session:
    app: FastAPI = api.app  # type: ignore[assignment]
    app.state.pipeline_executor = InterimExecutor()
    response = api.post("/api/v1/ingest", files={"file": ("input.csv", SRC_05.read_bytes(),
                        "text/csv")}, headers=principals.bearer("admin"))  # fmt: skip
    assert response.status_code == 202, response.text
    return roster


def _run(runner: PipelineRunner) -> tuple[uuid.UUID, PipelineRunStatus]:
    handle, status = runner.run("all", PipelineTrigger.TEST, as_of=AS_OF)
    return handle.id, status


def _rows(session: Session, table: str) -> list[tuple[Any, ...]]:
    result = session.execute(text(f"SELECT * FROM {table}"))  # noqa: S608
    keep = [i for i, c in enumerate(result.keys()) if c not in VOLATILE]
    return sorted(tuple(str(row[i]) for i in keep) for row in result)


@pytest.mark.req("ANL-033", "ANL-036", "ANL-040", "AC-ANL-09", "TST-051", "FEAT-053-AC-01",
                 "FEAT-053-AC-05", "FEAT-053-FR-01", "FEAT-053-FR-05", "FEAT-053-FR-16",
                 "FEAT-053-FR-19")  # fmt: skip
def test_full_run_on_src05(uploaded: Session, runner: PipelineRunner) -> None:
    run_id, status = _run(runner)
    assert status == PipelineRunStatus.SUCCEEDED
    query = text("SELECT counts, warnings, config_snapshot FROM pipeline_runs WHERE id = :i")
    run = uploaded.execute(query, {"i": run_id}).one()
    assert run.counts == COUNTS
    assert run.warnings == []
    assert len(run.config_snapshot) == 25
    assert run.config_snapshot["as_of"] == AS_OF.isoformat()
    assert run.config_snapshot["config_hash"] == engine_result().config_hash
    query = text("SELECT session_id, status, reason_text FROM processed_sessions")
    statuses = sorted(uploaded.execute(query).tuples().all())
    assert statuses == sorted((s.record.session_id, s.status, s.reason_text)
                              for s in engine_result().sessions)  # fmt: skip
    counts = dict(uploaded.execute(text(
        "SELECT 'baselines', count(*) FROM baselines UNION ALL SELECT 'scores', count(*) "
        "FROM scores UNION ALL SELECT 'ledger', count(*) FROM day_ledger UNION ALL "
        "SELECT 'epochs', count(*) FROM epochs")).tuples().all())  # fmt: skip
    assert counts == {"baselines": 180, "scores": 98, "ledger": 300, "epochs": 11}
    stored = dict(uploaded.execute(text(
        "SELECT p.session_id, s.cusum_tally FROM scores s "
        "JOIN processed_sessions p ON p.id = s.processed_session_id")).tuples().all())  # fmt: skip
    assert stored == {s.session_id: s.cusum_tally for s in engine_result().scores}
    alerts = uploaded.execute(
        text("SELECT session_id, status FROM alerts ORDER BY session_id")
    ).all()
    assert [tuple(a) for a in alerts] == [("R09-20261021-01", "open"), ("R10-20261024-01", "open")]
    data = uploaded.execute(text("SELECT title, status, first_detected_at FROM data_alerts "
                                 "ORDER BY title")).all()  # fmt: skip
    assert [a.title for a in data] == [
        "D02 · device silent all day", "R03 · many check-ins set aside",
        "R05 · possible other speaker", "R08 · baseline stuck at 13 of 16",
    ]  # fmt: skip
    assert {(a.status, a.first_detected_at) for a in data} == {("open", AS_OF)}


@pytest.mark.req("DB-019", "ANL-023", "AGT-056", "TST-050", "FEAT-053-AC-02", "FEAT-053-FR-17")
def test_second_run_changes_nothing(uploaded: Session, runner: PipelineRunner) -> None:
    _run(runner)
    before = {t: _rows(uploaded, t) for t in DERIVED}
    ids = uploaded.execute(text("SELECT id FROM alerts ORDER BY session_id")).scalars().all()
    _, status = _run(runner)
    assert status == PipelineRunStatus.SUCCEEDED
    assert {t: _rows(uploaded, t) for t in DERIVED} == before
    assert (
        uploaded.execute(text("SELECT id FROM alerts ORDER BY session_id")).scalars().all() == ids
    )


@pytest.mark.req("ANL-039", "AC-ANL-11", "TST-067", "CUS-015", "FEAT-053-AC-03", "FEAT-053-FR-09")
def test_reviews_and_snooze_survive_a_rerun(
    uploaded: Session, runner: PipelineRunner, principals: Principals
) -> None:
    _run(runner)
    alert_id = uploaded.execute(
        text("SELECT id FROM alerts WHERE session_id = 'R09-20261021-01'")
    ).scalar_one()
    user = principals.users["clinician"].id
    uploaded.execute(text(
        "INSERT INTO alert_reviews (alert_id, reviewer_user_id, explanations, outcome) "
        "VALUES (:a, :u, '{}', 'no_concern')"), {"a": alert_id, "u": user})  # fmt: skip
    uploaded.execute(text(
        "UPDATE alerts SET status = 'acknowledged', acknowledged_by = :u, acknowledged_at = :t, "
        "snoozed_until = :t, snoozed_by = :u WHERE id = :a"),
        {"a": alert_id, "u": user, "t": AS_OF})  # fmt: skip
    uploaded.commit()
    _run(runner)
    row = uploaded.execute(text("SELECT status, snoozed_until FROM alerts WHERE id = :a"),
                           {"a": alert_id}).one()  # fmt: skip
    assert tuple(row) == ("acknowledged", AS_OF)
    reviews = uploaded.execute(text("SELECT count(*) FROM alert_reviews WHERE alert_id = :a"),
                               {"a": alert_id}).scalar_one()  # fmt: skip
    assert reviews == 1


@pytest.mark.req("ANL-041", "DB-013", "AC-ANL-08", "FEAT-053-AC-04", "FEAT-053-FR-13",
                 "FEAT-053-FR-14")  # fmt: skip
def test_a_failing_resident_is_rolled_back_alone(
    uploaded: Session, runner: PipelineRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    _run(runner)
    r05_before = _r05_scores(uploaded)
    original: Callable[..., Any] = pipeline_persistence._insert_scores

    def failing(session: Session, resident: Any, code: str, *args: Any) -> None:
        if code == "R05":
            raise RuntimeError("injected write failure")
        original(session, resident, code, *args)

    monkeypatch.setattr(pipeline_persistence, "_insert_scores", failing)
    uploaded.execute(text("DELETE FROM scores WHERE resident_id = (SELECT id FROM residents "
                          "WHERE resident_code = 'R01')"))  # fmt: skip
    uploaded.commit()
    run_id, status = _run(runner)
    assert status == PipelineRunStatus.FAILED
    run = uploaded.execute(text("SELECT error_message, warnings FROM pipeline_runs WHERE id = :i"),
                           {"i": run_id}).one()  # fmt: skip
    assert run.error_message == "failed residents: R05"
    assert [w["code"] for w in run.warnings] == ["exception"]
    assert run.warnings[0]["resident_code"] == "R05"
    assert _r05_scores(uploaded) == r05_before  # rolled back
    r01 = uploaded.execute(text(
        "SELECT count(*) FROM scores s JOIN residents r ON r.id = s.resident_id "
        "WHERE r.resident_code = 'R01'")).scalar_one()  # fmt: skip
    assert r01 == sum(s.resident_code == "R01" for s in engine_result().scores)  # rewritten


def _r05_scores(session: Session) -> list[tuple[Any, ...]]:
    return sorted(tuple(r) for r in session.execute(text(
        "SELECT s.id, s.cusum_tally FROM scores s JOIN residents r ON r.id = s.resident_id "
        "WHERE r.resident_code = 'R05'")))  # fmt: skip


@pytest.mark.req("DB-016", "ANL-026", "AC-ANL-05", "FEAT-053-AC-07", "FEAT-053-FR-08")
def test_late_record_keeps_frozen_baselines(
    api: TestClient, uploaded: Session, runner: PipelineRunner, principals: Principals
) -> None:
    _run(runner)
    query = text("SELECT b.feature_key, b.median, b.mad, b.robust_spread, b.id FROM baselines b "
                 "JOIN residents r ON r.id = b.resident_id WHERE r.resident_code = 'R01' "
                 "ORDER BY b.feature_key")  # fmt: skip
    before = [tuple(r) for r in uploaded.execute(query)]
    late = {**src05_record("R01-20261010-01"), "session_id": "R01-20261010-02",
            "timestamp_utc": "2026-10-10 19:00:00"}  # fmt: skip
    response = api.post("/api/v1/sessions", json=late, headers=principals.api_key("ingest"))
    assert response.status_code == 201, response.text
    run_id, status = _run(runner)
    assert status == PipelineRunStatus.SUCCEEDED
    assert [tuple(r) for r in uploaded.execute(query)] == before
    warnings = uploaded.execute(text("SELECT warnings FROM pipeline_runs WHERE id = :i"),
                                {"i": run_id}).scalar_one()  # fmt: skip
    assert [(w["code"], w["session_id"]) for w in warnings] == [("late_arrival", "R01-20261010-02")]
    late_row = uploaded.execute(text(
        "SELECT status, late_arrival, in_baseline FROM processed_sessions "
        "WHERE session_id = 'R01-20261010-02'")).one()  # fmt: skip
    assert tuple(late_row) == ("usable", True, False)


@pytest.mark.req("ANL-064", "AGT-057", "FEAT-053-AC-06", "FEAT-053-FR-18")
def test_runner_never_reads_the_answer_key() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    for module in (
        "backend/services/pipeline_runner.py",
        "backend/services/pipeline_persistence.py",
    ):
        assert "evaluation_ground_truth" not in (root / module).read_text(encoding="utf-8")


@pytest.mark.req("FEAT-051-AC-05", "FEAT-051-FR-11", "FEAT-051-FR-12", "FEAT-051-FR-13",
                 "API-087", "D-79")  # fmt: skip
def test_analytics_endpoint_after_the_run(
    api: TestClient, uploaded: Session, runner: PipelineRunner, principals: Principals
) -> None:
    _run(runner)
    body = api.get("/api/v1/analytics", headers=principals.bearer("researcher")).json()
    k = body["kpis"]
    assert k["checkins_received"] == {"count": 281, "expected": 300, "percent": 94}
    assert k["used_for_scoring"] == {"count": 267, "expected": 300, "percent": 89}
    assert k["baselines_formed"] == {
        "formed": 9, "residents": 10, "forming_resident_codes": ["R08"],
        "restarts": [{"resident_code": "R07", "restart_count": 1}],
    }  # fmt: skip
    assert k["alarms_raised"] == {"count": 2, "resident_codes": ["R09", "R10"],
                                  "not_reviewed_count": 2}  # fmt: skip
    f = body["funnel"]
    assert (f["expected"], f["received"], f["passed_quality"], f["used"]) == (300, 281, 269, 267)
    assert (f["missed"], f["duplicates_removed"], f["set_aside_multi_reason"]) == (19, 2, 1)
    oct12 = next(d for d in body["daily_series"] if d["local_date"] == "2026-10-12")
    assert (oct12["used"], oct12["missed"], oct12["silent_device_codes"]) == (8, 2, ["D02"])
    assert [r["used_percent"] for r in body["by_resident"]][:4] == [43, 73, 80, 93]


@pytest.mark.req("FEAT-048-FR-07", "CUS-041", "API-080")
def test_alerts_endpoint_leaning_most(
    api: TestClient, uploaded: Session, runner: PipelineRunner, principals: Principals
) -> None:
    _run(runner)
    items = api.get("/api/v1/alerts", headers=principals.bearer("clinician")).json()["items"]
    leaning = {a["resident_code"]: a["leaning_most"] for a in items}
    assert leaning == {
        "R09": ["number_of_pauses", "loudness_dbfs", "voiced_fraction"],
        "R10": ["number_of_pauses", "articulation_rate_syl_per_s", "speech_rate_syl_per_s"],
    }
    tallies = {a["resident_code"]: round(a["current_tally"], 1) for a in items}
    assert tallies == {"R09": 26.8, "R10": 13.4}
