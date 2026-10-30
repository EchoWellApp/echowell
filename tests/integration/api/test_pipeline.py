"""Pipeline runner and run endpoints (TRD 05 API-063..API-069, API-134, API-135; TRD 24 D-50,
D-70; FEAT-024)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.core.errors import ProfileNotAllowedError
from backend.models import PipelineRunStatus, PipelineTrigger
from backend.repositories.config_repository import CONFIG_KEYS
from backend.repositories.pipeline_run_repository import PipelineRunRepository
from backend.services import pipeline_service
from backend.services.pipeline_runner import (
    Actor,
    ExecutorResult,
    PipelineRunner,
    RunHandle,
    SessionFactory,
    resolve_as_of,
)
from tests.conftest import make_settings
from tests.integration.api.conftest import Principals

pytestmark = pytest.mark.integration

RUN = "/api/v1/pipeline/run"
RUNS = "/api/v1/pipeline/runs"


def _problem(response: Any, status: int, code: str) -> dict[str, Any]:
    assert response.status_code == status, response.text
    body: dict[str, Any] = response.json()
    assert body["type"] == f"urn:echowell:error:{code}", body
    return body


def _factory(session: Session) -> SessionFactory:
    bind = session.connection()
    return lambda: Session(bind=bind, join_transaction_mode="create_savepoint")


def _running(session: Session, *, scope: dict[str, Any], minutes_ago: int = 0) -> uuid.UUID:
    run = PipelineRunRepository(session).insert_running(
        trigger=PipelineTrigger.MANUAL, scope=scope, config_profile="test_v0_1",
        config_snapshot={}, code_version="test", as_of=datetime.now(UTC),
    )  # fmt: skip
    session.execute(
        text("UPDATE pipeline_runs SET started_at = now() - make_interval(mins => :m) "
             "WHERE id = :i"),
        {"m": minutes_ago, "i": run.id},
    )  # fmt: skip
    session.commit()
    return run.id


class CountingExecutor:
    def execute(self, session_factory: SessionFactory, run: RunHandle) -> ExecutorResult:
        keys = ("arrivals", "usable", "set_aside", "quarantined", "duplicate", "missing_resident",
                "missing_device_gap", "late_arrival", "scored", "alerts_opened",
                "excluded_after_as_of", "residents")  # fmt: skip
        return ExecutorResult(counts=dict.fromkeys(keys, 0))


@pytest.mark.req("API-135", "D-50", "TST-038", "FEAT-024-AC-01", "FEAT-024-FR-03")
def test_as_of_precedence() -> None:
    explicit = datetime(2026, 10, 31, tzinfo=UTC)
    frozen = datetime(2026, 11, 2, 9, 30, tzinfo=UTC)
    with_env = make_settings(pipeline_as_of="2026-10-30T15:00:00-05:00")
    assert resolve_as_of(explicit, with_env, lambda: frozen) == explicit
    assert resolve_as_of(None, with_env, lambda: frozen) == datetime(2026, 10, 30, 20, tzinfo=UTC)
    assert resolve_as_of(None, make_settings(), lambda: frozen) == frozen
    production = make_settings(app_env="production", pipeline_as_of="2026-10-30T15:00:00-05:00")
    assert resolve_as_of(None, production, lambda: frozen) == frozen


@pytest.mark.req("API-063", "LOG-060", "DB-020", "FEAT-024-FR-01", "FEAT-024-FR-02")
def test_run_lifecycle_and_snapshot(roster: Session) -> None:
    settings = make_settings(git_sha="abc1234")
    runner = PipelineRunner(_factory(roster), settings, CountingExecutor())
    handle, status = runner.run("all", PipelineTrigger.TEST, actor=Actor())
    assert status == PipelineRunStatus.SUCCEEDED
    run = roster.execute(
        text("SELECT status, code_version, config_snapshot, counts, finished_at, scope "
             "FROM pipeline_runs WHERE id = :i"), {"i": handle.id},
    ).one()  # fmt: skip
    assert (run.status, run.code_version, run.scope) == ("succeeded", "abc1234", {"type": "all"})
    assert set(run.config_snapshot) == {*CONFIG_KEYS, "config_hash", "as_of"}
    assert run.counts["arrivals"] == 0
    assert run.finished_at is not None
    actions = roster.execute(
        text("SELECT action, details FROM audit_logs WHERE entity_id = :i ORDER BY id"),
        {"i": str(handle.id)},
    ).all()
    assert [a.action for a in actions] == ["pipeline.run.started", "pipeline.run.finished"]
    assert actions[0].details == {"trigger": "test", "scope": {"type": "all"},
                                  "profile": "test_v0_1"}  # fmt: skip
    assert actions[1].details["status"] == "succeeded"


@pytest.mark.req("API-065", "FR-223", "FEAT-024-AC-02", "FEAT-024-FR-05")
def test_admin_starts_a_manual_run(
    api: TestClient, roster: Session, principals: Principals
) -> None:
    response = api.post(RUN, json={"scope": "all"}, headers=principals.bearer("admin"))
    assert response.status_code == 202, response.text
    run_id = response.json()["pipeline_run_id"]
    run = roster.execute(
        text("SELECT trigger, status, error_message FROM pipeline_runs WHERE id = :i"),
        {"i": run_id},
    ).one()
    assert tuple(run) == ("manual", "failed", "pipeline not available until Phase 6")
    actions = roster.execute(
        text("SELECT action, actor_type FROM audit_logs WHERE entity_id = :i ORDER BY id"),
        {"i": run_id},
    ).all()
    assert [tuple(a) for a in actions] == [
        ("pipeline.run.started", "user"),
        ("pipeline.run.finished", "system"),
    ]


@pytest.mark.req("API-065", "FEAT-024-AC-03", "FEAT-024-FR-06")
def test_full_run_in_progress_is_409(
    api: TestClient, roster: Session, principals: Principals
) -> None:
    _running(roster, scope={"type": "all"})
    _problem(api.post(RUN, json={"scope": ["R01"]}, headers=principals.bearer("admin")), 409,
             "PIPELINE_RUN_IN_PROGRESS")  # fmt: skip


@pytest.mark.req("API-066", "FR-230", "FEAT-024-AC-04", "FEAT-024-FR-08")
def test_production_refuses_other_profiles(roster: Session) -> None:
    production = make_settings(app_env="production", pipeline_profile="production")
    runner = PipelineRunner(_factory(roster), production)
    with pytest.raises(ProfileNotAllowedError):
        pipeline_service.request_run(
            roster, production, runner, actor=Actor(), nightly=False, scope="all",
            profile="test_v0_1", as_of=None,
        )  # fmt: skip
    local = make_settings(pipeline_profile="test_v0_1")
    run_id, handle = pipeline_service.request_run(
        roster, local, PipelineRunner(_factory(roster), local), actor=Actor(), nightly=False,
        scope="all", profile="production", as_of=None,
    )  # fmt: skip
    assert handle is not None
    assert handle.profile == "production"


@pytest.mark.req("TRD 19 E-20", "FEAT-024-FR-09")
def test_unknown_resident_in_scope_is_404(
    api: TestClient, roster: Session, principals: Principals
) -> None:
    _problem(api.post(RUN, json={"scope": ["R01", "R99"]}, headers=principals.bearer("admin")),
             404, "RESIDENT_NOT_FOUND")  # fmt: skip
    _problem(api.post(RUN, json={"scope": []}, headers=principals.bearer("admin")), 422,
             "VALIDATION_ERROR")  # fmt: skip
    _problem(api.post(RUN, json={"scope": "all", "profile": "x"},
                      headers=principals.bearer("admin")), 422, "VALIDATION_ERROR")  # fmt: skip


@pytest.mark.req("API-065", "D-70", "FEAT-024-AC-05", "FEAT-024-FR-07")
def test_scheduler_key_runs_nightly_once_per_local_date(
    api: TestClient, roster: Session, principals: Principals
) -> None:
    api.app.state.pipeline_executor = CountingExecutor()  # type: ignore[attr-defined]
    first = api.post(RUN, json={"scope": ["R01"]}, headers=principals.api_key("pipeline"))
    assert first.status_code == 202, first.text
    run = roster.execute(
        text("SELECT trigger, scope, status FROM pipeline_runs WHERE id = :i"),
        {"i": first.json()["pipeline_run_id"]},
    ).one()
    assert tuple(run) == ("nightly", {"type": "all"}, "succeeded")
    second = api.post(RUN, json={"scope": "all"}, headers=principals.api_key("pipeline"))
    assert second.status_code == 202
    assert second.json() == first.json()
    count = roster.execute(text("SELECT count(*) FROM pipeline_runs")).scalar_one()
    assert count == 1


@pytest.mark.req("API-134", "TST-069", "FR-225", "FEAT-024-AC-06", "FEAT-024-FR-11")
def test_list_runs(api: TestClient, roster: Session, principals: Principals) -> None:
    older = _running(roster, scope={"type": "residents", "resident_codes": ["R01"]}, minutes_ago=5)
    newer = _running(roster, scope={"type": "residents", "resident_codes": ["R02"]}, minutes_ago=1)
    repository = PipelineRunRepository(roster)
    failed = repository.get(older)
    assert failed is not None
    repository.finish(failed, status=PipelineRunStatus.FAILED, finished_at=datetime.now(UTC),
                      error_message="boom")  # fmt: skip
    roster.commit()
    response = api.get(RUNS, headers=principals.bearer("researcher"))
    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body["items"]] == [str(newer), str(older)]
    assert (body["total"], body["limit"], body["offset"]) == (2, 50, 0)
    assert body["meta"]["pipeline_profile"] == "test_v0_1"
    assert body["items"][0]["scope"] == ["R02"]
    only_failed = api.get(RUNS, params={"status": "failed"}, headers=principals.bearer("admin"))
    assert [item["id"] for item in only_failed.json()["items"]] == [str(older)]
    page = api.get(RUNS, params={"limit": 1, "offset": 1}, headers=principals.bearer("admin"))
    assert [item["id"] for item in page.json()["items"]] == [str(older)]
    _problem(api.get(RUNS, headers=principals.bearer("clinician")), 403, "FORBIDDEN")
    _problem(api.get(RUNS, params={"status": "done"}, headers=principals.bearer("admin")), 422,
             "INVALID_QUERY_PARAMETER")  # fmt: skip


@pytest.mark.req("API-067", "FR-224", "TST-038", "FEAT-024-AC-07", "FEAT-024-FR-10")
def test_get_run(api: TestClient, roster: Session, principals: Principals) -> None:
    run_id = _running(roster, scope={"type": "all"})
    response = api.get(f"{RUNS}/{run_id}", headers=principals.bearer("admin"))
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"id", "trigger", "scope", "config_profile", "code_version", "as_of",
                         "started_at", "finished_at", "status", "counts", "warnings"}  # fmt: skip
    assert (body["scope"], body["status"], body["finished_at"]) == ("all", "running", None)
    _problem(api.get(f"{RUNS}/{uuid.uuid4()}", headers=principals.bearer("admin")), 404,
             "PIPELINE_RUN_NOT_FOUND")  # fmt: skip


@pytest.mark.req("API-068", "LOG-066", "AC-LOG-06", "FEAT-024-AC-08", "FEAT-024-FR-12")
def test_stale_running_run_is_abandoned(roster: Session) -> None:
    stale = _running(roster, scope={"type": "residents", "resident_codes": ["R01"]},
                     minutes_ago=31)  # fmt: skip
    recent = _running(roster, scope={"type": "residents", "resident_codes": ["R02"]},
                      minutes_ago=29)  # fmt: skip
    runner = PipelineRunner(_factory(roster), make_settings(), CountingExecutor())
    runner.run(["R03"], PipelineTrigger.MANUAL)
    rows = {
        r.id: r
        for r in roster.execute(
            text("SELECT id, status, warnings, error_message FROM pipeline_runs")
        ).all()
    }
    assert rows[stale].status == "failed"
    assert rows[stale].warnings[-1]["code"] == "run_abandoned"
    assert rows[stale].error_message
    assert rows[recent].status == "running"
