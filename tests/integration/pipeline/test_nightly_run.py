"""The nightly job (TRD 07 ANL-045, AC-ANL-13; TRD 05 API-060..API-062; FEAT-054-FR-07..FR-12,
FEAT-056-FR-08, FEAT-056-FR-09). A fake clock walks across the 1 Nov 2026 DST change."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from backend.jobs import nightly_run
from backend.services.pipeline_runner import PipelineRunner
from tests.conftest import make_settings
from tests.integration.api.conftest import LogCapture

pytestmark = pytest.mark.integration


@pytest.fixture
def factory(app_conn: Connection, roster: Session) -> Callable[[], Session]:
    def make() -> Session:
        return Session(bind=app_conn, join_transaction_mode="create_savepoint")

    return make


def _night(factory: Callable[[], Session], when: datetime) -> int:
    settings = make_settings()
    clock = lambda: when  # noqa: E731
    return nightly_run.run_night(
        settings, factory, clock, PipelineRunner(factory, settings, clock=clock)
    )


def _nightly_runs(roster: Session) -> list[tuple[str, str]]:
    rows = roster.execute(text("SELECT status, as_of FROM pipeline_runs WHERE trigger = 'nightly' "
                               "ORDER BY started_at")).all()  # fmt: skip
    return [(r.status, r.as_of.isoformat()) for r in rows]


@pytest.mark.req(
    "ANL-045", "AC-ANL-13", "AGT-059", "API-060", "API-061", "DEP-047", "FEAT-054-AC-03",
    "FEAT-054-FR-07", "FEAT-054-FR-08", "FEAT-054-FR-09",
)  # fmt: skip
def test_one_run_per_local_night_across_dst(
    factory: Callable[[], Session], roster: Session
) -> None:
    cdt_0230 = datetime(2026, 10, 31, 7, 30, tzinfo=UTC)  # 02:30 CDT
    assert _night(factory, cdt_0230) == 0
    assert _night(factory, cdt_0230.replace(minute=45)) == 0  # second firing: deduped
    assert _night(factory, datetime(2026, 10, 31, 8, 30, tzinfo=UTC)) == 0  # 03:30 CDT
    cst_0230 = datetime(2026, 11, 2, 8, 30, tzinfo=UTC)  # 02:30 CST after the change
    assert _night(factory, datetime(2026, 11, 2, 7, 30, tzinfo=UTC)) == 0  # 01:30 CST
    assert _night(factory, cst_0230) == 0
    assert [status for status, _ in _nightly_runs(roster)] == ["succeeded", "succeeded"]
    counts = (
        roster.execute(text("SELECT counts FROM pipeline_runs WHERE trigger = 'nightly'"))
        .scalars()
        .first()
    )
    assert counts["db_size_bytes"] > 0


@pytest.mark.req("LOG-111", "FEAT-056-FR-09")
def test_missed_night_is_reported(
    factory: Callable[[], Session], roster: Session, log_capture: LogCapture
) -> None:
    log_capture.start()
    assert _night(factory, datetime(2026, 10, 31, 15, 0, tzinfo=UTC)) == 0  # 10:00, no run
    events = [r for r in log_capture.lines() if r["msg"] == "nightly_run_missing"]
    assert [e["local_date"] for e in events] == ["2026-10-31"]
    assert roster.execute(text("SELECT count(*) FROM pipeline_runs")).scalar_one() == 0


@pytest.mark.req("DEP-048", "FEAT-054-FR-12")
def test_schema_mismatch_refuses(
    factory: Callable[[], Session], monkeypatch: pytest.MonkeyPatch, roster: Session
) -> None:
    real = nightly_run.database_revision
    monkeypatch.setattr(nightly_run, "database_revision", lambda _: "0001")
    assert _night(factory, datetime(2026, 10, 31, 7, 30, tzinfo=UTC)) == 1
    assert roster.execute(text("SELECT count(*) FROM pipeline_runs")).scalar_one() == 0
    assert real(factory) == nightly_run.UNREADABLE  # the app role may not read alembic_version
