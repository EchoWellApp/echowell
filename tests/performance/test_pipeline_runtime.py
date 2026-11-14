"""Pipeline runtime budgets (TRD 13 TST-120, TST-123; TRD 07 ANL-047, ANL-048; TRD 05 API-124;
TRD 03 NFR-005..NFR-007, NFR-152; FEAT-079-FR-02, FR-05, FR-07, FR-13).

- TST-120 (`budget`, every PR in `backend-test`, CIC-036): `analytics.pipeline.run_pipeline` with
  profile test_v0_1 on SRC-05 (283 arrivals), in memory, ≤ 5 s.
- TST-123 (nightly): `POST /pipeline/run {scope: all}` on DS-08 (100 residents, 10,800 records)
  until `succeeded` (load, compute, write) ≤ 120 s; records the database size for the NFR-152
  projection (100 residents x 3 years ≤ 2 GB, DB-049).
- API-124 / NFR-006 (nightly): the same full rebuild on SRC-05 including database writes ≤ 30 s.
"""

from __future__ import annotations

import time

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from analytics.config import TEST_V0_1
from analytics.pipeline import run_pipeline
from tests.performance.conftest import PerfReport, Stack
from tests.support.system import AS_OF_PARAM, INPUT_CSV
from tests.unit.analytics import src05

pytestmark = pytest.mark.performance

PIPELINE_BUDGET_MS = 5_000
DS08_REBUILD_BUDGET_MS = 120_000
SRC05_REBUILD_BUDGET_MS = 30_000
NFR152_BYTES = 2 * 1024**3
DAYS_3_YEARS = 3 * 365


@pytest.mark.budget
@pytest.mark.req("TST-120", "ANL-047", "NFR-005")
def test_pipeline_on_src05_within_5_s(perf_report: PerfReport) -> None:
    records = src05.records()
    run_pipeline(records, src05.RESIDENTS, src05.ASSIGNMENTS, TEST_V0_1, src05.AS_OF)  # warm
    started = time.perf_counter()
    result = run_pipeline(records, src05.RESIDENTS, src05.ASSIGNMENTS, TEST_V0_1, src05.AS_OF)
    elapsed = (time.perf_counter() - started) * 1000
    assert len(records) == 283
    assert result is not None
    perf_report.record("TST-120", "run_pipeline on SRC-05 (in memory)", measured_ms=elapsed,
                       budget_ms=PIPELINE_BUDGET_MS, statistic="elapsed")  # fmt: skip
    perf_report.check("TST-120")


def _rebuild(s: Stack, timeout_s: float, **body: object) -> tuple[dict[str, object] | None, float]:
    """`POST /pipeline/run {scope: all}` and the wait for its end; (run, ms from the POST)."""
    started = time.perf_counter()
    response = s.client.post("/api/v1/pipeline/run", headers=s.admin(),
                             json={"scope": "all", "profile": "test_v0_1", **body})  # fmt: skip
    assert response.status_code == 202, f"pipeline/run: {response.status_code} {response.text}"
    run, _ = s.wait_run(response.json()["pipeline_run_id"], timeout_s)
    return run, (time.perf_counter() - started) * 1000


@pytest.mark.req("TST-123", "ANL-048", "API-124", "NFR-007", "NFR-152", "DB-049")
def test_ds08_full_rebuild_within_120_s(ds08_stack: Stack, perf_report: PerfReport) -> None:
    run, elapsed = _rebuild(ds08_stack, DS08_REBUILD_BUDGET_MS / 1000)
    passed = run is not None and run["status"] == "succeeded"
    perf_report.record("TST-123", "full rebuild of DS-08 (POST /pipeline/run scope all)",
                       measured_ms=elapsed, budget_ms=DS08_REBUILD_BUDGET_MS, statistic="elapsed",
                       run_status=None if run is None else run["status"],
                       counts=None if run is None else run.get("counts"))  # fmt: skip
    engine = create_engine(ds08_stack.urls.readonly, poolclass=NullPool)
    try:
        with engine.connect() as connection:
            size = int(connection.execute(text("SELECT pg_database_size(current_database())"))
                       .scalar_one())  # fmt: skip
            sessions = int(connection.execute(text("SELECT count(*) FROM raw_sessions"))
                           .scalar_one())  # fmt: skip
    finally:
        engine.dispose()
    projection = round(size * DAYS_3_YEARS / 120)
    perf_report.info.update({
        "ds08_raw_sessions": sessions, "ds08_db_size_bytes": size,
        "nfr152_projection_bytes": projection, "nfr152_budget_bytes": NFR152_BYTES,
        "ds08_load_s": ds08_stack.info.get("load_s"),
    })  # fmt: skip
    assert passed, f"DS-08 rebuild did not succeed within the budget: {run}"
    perf_report.check("TST-123")
    assert sessions == 10_800
    assert projection <= NFR152_BYTES, f"NFR-152 projection {projection} B exceeds 2 GB"


@pytest.mark.req("API-124", "NFR-006", "ANL-048")
def test_src05_full_rebuild_within_30_s(src05_stack: Stack, perf_report: PerfReport) -> None:
    if not src05_stack.info.get("src05_loaded"):
        response = src05_stack.client.post(
            "/api/v1/ingest", headers=src05_stack.admin(),
            files={"file": (INPUT_CSV.name, INPUT_CSV.read_bytes(), "text/csv")},
        )  # fmt: skip
        assert response.status_code == 202, response.text
        run, _ = src05_stack.wait_run(response.json()["pipeline_run_id"], 120)
        assert run is not None
        assert run["status"] == "succeeded", run
        src05_stack.info["src05_loaded"] = True
    run, elapsed = _rebuild(src05_stack, SRC05_REBUILD_BUDGET_MS / 1000, as_of=AS_OF_PARAM)
    perf_report.record("API-124", "full rebuild of SRC-05 with database writes",
                       measured_ms=elapsed, budget_ms=SRC05_REBUILD_BUDGET_MS, statistic="elapsed",
                       run_status=None if run is None else run["status"])  # fmt: skip
    assert run is not None, "SRC-05 rebuild still running after 30 s"
    assert run["status"] == "succeeded", f"SRC-05 rebuild: {run}"
    perf_report.check("API-124")
