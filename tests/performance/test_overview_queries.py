"""Resident-list query time and index use on DS-08 (TRD 06 DB-040, DB-042; TRD 24 D-174).

- DB-040: the resident list queries (current epoch, open alerts, last check-in, 30-day counts,
  baseline progress, attention flag), issued by `resident_service.overview` exactly as
  `GET /api/v1/residents` issues them, take ≤ 150 ms total database time on DS-08 (100 residents,
  10,800 records). Database time is the sum of the `cursor.execute` times of those statements
  (SQLAlchemy cursor events; psycopg returns the rows inside `execute`, so the transfer is
  included and ORM work is not), p95 over warm samples.
- DB-042: the resident-scoped statements on `raw_sessions`, `processed_sessions`, `scores` and
  `day_ledger` that the per-resident pipeline input load and the resident pages (detail, scores,
  check-in log, features) issue for one DS-08 resident are captured with their parameters and
  explained; no plan has a `Seq Scan` on those tables.

The planner works from statistics: the DS-08 stack loads 10,800 records just before these tests,
faster than autovacuum's analyze threshold may react, so the tables are `ANALYZE`d first (as the
table owner), which is what autovacuum does in a running deployment. No planner setting is
changed (`enable_seqscan` stays on).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from backend.repositories.resident_repository import ResidentRepository
from backend.services import (
    checkin_service,
    feature_service,
    pipeline_persistence,
    resident_service,
    score_service,
)
from backend.services.resident_service import ReadContext
from tests.conftest import make_settings
from tests.performance.conftest import PerfReport, Stack, p95

pytestmark = pytest.mark.performance

LIST_BUDGET_MS = 150
WARMUP = 3
SAMPLES = 20
SCOPED_TABLES = ("raw_sessions", "processed_sessions", "scores", "day_ledger")
RESIDENT = "L001"


@dataclass
class Capture:
    """Statements and their `cursor.execute` times on one engine while `active`."""

    active: bool = False
    statements: list[tuple[str, Any]] = field(default_factory=list)
    elapsed_ms: float = 0.0

    def reset(self) -> None:
        self.statements.clear()
        self.elapsed_ms = 0.0


def _listen(engine: Engine, capture: Capture) -> None:
    @event.listens_for(engine, "before_cursor_execute")
    def before(conn: Connection, _c: Any, statement: str, params: Any, *_: Any) -> None:
        conn.info["query_started"] = time.perf_counter()
        if capture.active:
            capture.statements.append((statement, params))

    @event.listens_for(engine, "after_cursor_execute")
    def after(conn: Connection, *_: Any) -> None:
        if capture.active:
            capture.elapsed_ms += (time.perf_counter() - conn.info["query_started"]) * 1000


@contextmanager
def _session(stack: Stack) -> Iterator[tuple[Session, ReadContext, Capture]]:
    """A session as the app role (the role that serves the API) with a capture on its engine."""
    engine = create_engine(stack.urls.app, poolclass=NullPool)
    capture = Capture()
    _listen(engine, capture)
    settings = make_settings(database_url=stack.urls.app, database_readonly_url=stack.urls.readonly,
                             facility_name="Demo Facility")  # fmt: skip
    try:
        with Session(engine) as session:
            yield session, resident_service.read_context(session, settings), capture
    finally:
        engine.dispose()


def _analyze(stack: Stack) -> None:
    engine = create_engine(stack.urls.migrator, poolclass=NullPool)
    try:
        with engine.begin() as conn:
            conn.execute(text("SET LOCAL ROLE echowell_migrator"))
            for table in (*SCOPED_TABLES, "epochs", "baselines", "alerts", "data_alerts",
                          "cusum_state", "residents", "device_assignments"):  # fmt: skip
                conn.execute(text(f"ANALYZE {table}"))
    finally:
        engine.dispose()


def _overview(session: Session, ctx: ReadContext) -> dict[str, Any]:
    return resident_service.overview(session, ctx, sort="alarm", cohort="longitudinal",
                                     include_withdrawn=False, limit=100, offset=0)  # fmt: skip


@pytest.mark.req("DB-040", "NFR-001", "R8")
def test_resident_list_queries_within_150_ms_on_ds08(
    ds08_stack: Stack, perf_report: PerfReport
) -> None:
    """TRD 06 DB-040: the resident list queries take ≤ 150 ms total database time on DS-08."""
    _analyze(ds08_stack)
    with _session(ds08_stack) as (session, ctx, capture):
        body = _overview(session, ctx)
        assert body["total"] == 100
        for _ in range(WARMUP):
            _overview(session, ctx)
        samples: list[float] = []
        for _ in range(SAMPLES):
            session.expire_all()
            capture.reset()
            capture.active = True
            _overview(session, ctx)
            capture.active = False
            samples.append(capture.elapsed_ms)
        statements = len(capture.statements)
    perf_report.record("DB-040", "Resident list queries, total database time on DS-08",
                       measured_ms=p95(samples), budget_ms=LIST_BUDGET_MS, samples=len(samples),
                       max_ms=round(max(samples), 1), statements=statements)  # fmt: skip
    perf_report.check("DB-040")


def _resident_scoped_calls(
    session: Session, ctx: ReadContext, settings_profile: str
) -> list[Callable[[], object]]:
    assert ResidentRepository(session).get_by_code(RESIDENT) is not None
    start, end = feature_service.default_window(ctx)
    where = score_service.score_filter(session, resident_code=RESIDENT, epoch=None, start=None,
                                       end=None)  # fmt: skip
    return [
        lambda: pipeline_persistence.load_inputs(session, [RESIDENT]),  # per-resident run input
        lambda: resident_service.detail(session, ctx, RESIDENT),
        lambda: score_service.scores(session, ctx, settings_profile, where, limit=500, offset=0),
        lambda: checkin_service.events(session, ctx, RESIDENT, start, end),
        lambda: feature_service.series(session, ctx, RESIDENT, start, end),
    ]


def _seq_scans(plan: list[str]) -> list[str]:
    return [
        line.strip()
        for line in plan
        if any(f"Seq Scan on {table}" in line for table in SCOPED_TABLES)
    ]


@pytest.mark.req("DB-042")
def test_resident_scoped_queries_use_no_seq_scan_on_ds08(ds08_stack: Stack) -> None:
    """TRD 06 DB-042: resident-scoped queries on `raw_sessions`, `processed_sessions`, `scores`
    and `day_ledger` use no sequential scan on DS-08 (EXPLAIN shows no `Seq Scan` on them)."""
    _analyze(ds08_stack)
    with _session(ds08_stack) as (session, ctx, capture):
        calls = _resident_scoped_calls(session, ctx, "test_v0_1")
        capture.active = True
        for call in calls:
            call()
        capture.active = False
        scoped = [
            (statement, params)
            for statement, params in capture.statements
            if any(t in statement for t in SCOPED_TABLES) and "resident_id" in statement
        ]
        assert {t for t in SCOPED_TABLES if any(t in s for s, _ in scoped)} == set(SCOPED_TABLES)
        found: dict[str, list[str]] = {}
        connection = session.connection()
        for statement, params in scoped:
            plan = [r[0] for r in connection.exec_driver_sql(f"EXPLAIN {statement}", params)]
            if bad := _seq_scans(plan):
                found[" ".join(statement.split())[:300]] = bad
    assert found == {}, found
