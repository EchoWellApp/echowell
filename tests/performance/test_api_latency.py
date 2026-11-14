"""API latency budgets (TRD 13 TST-121, TST-122, TST-124, TST-126; TRD 05 API-120..API-123;
TRD 03 NFR-001..NFR-004, NFR-009; TRD 07 ANL-049; FEAT-079-FR-03, FR-04, FR-06, FR-08, FR-09).

- TST-121: `POST /api/v1/sessions` (API key, synchronous per-resident pipeline) for a resident with
  120 days of history, p95 ≤ 1,000 ms: 50 sequential requests on every PR (`budget`), 200 nightly.
- TST-122 (nightly): six read endpoints on DS-08, 100 warm requests each, p95 ≤ 500 ms.
- TST-124 (`budget`): `POST /api/v1/ingest` with SRC-05 as CSV answers 202 in ≤ 2 s and its batch
  run reaches `succeeded` in ≤ 30 s (from the POST).
- API-120 (nightly): `GET /api/v1/health` p95 ≤ 200 ms.

The read tests empty the in-memory rate-limit counters between endpoints (`limiter.reset()`, as
the suite does before every test, TRD 24 D-74) so 105 requests per endpoint stay under the
300/minute per-user default; no limit is raised.
"""

from __future__ import annotations

import pytest

from backend.core.rate_limit import limiter
from tests.performance.conftest import History, PerfReport, Stack, p95, stack
from tests.support.system import INPUT_CSV, TEST_AS_OF

pytestmark = pytest.mark.performance

SESSIONS_BUDGET_MS = 1_000
READ_BUDGET_MS = 500
HEALTH_BUDGET_MS = 200
INGEST_ACCEPT_BUDGET_MS = 2_000
INGEST_DONE_BUDGET_MS = 30_000
WARMUP = 5
READ_SAMPLES = 100


def _post_sessions(history: History, count: int, budget_id: str, report: PerfReport) -> None:
    s = history.stack
    limiter.reset()
    warm, *_ = history.take(1)
    response, _ = s.timed("POST", "/sessions", headers=s.key(), json=warm)
    assert response.status_code == 201, f"warm-up: {response.status_code} {response.text}"
    samples: list[float] = []
    for record in history.take(count):
        response, ms = s.timed("POST", "/sessions", headers=s.key(), json=record)
        assert response.status_code == 201, f"{record['session_id']}: {response.text}"
        assert response.json()["pipeline_run_id"], "the synchronous per-resident run is missing"
        samples.append(ms)
    report.record(budget_id, f"POST /sessions with the per-resident pipeline ({count} requests)",
                  measured_ms=p95(samples), budget_ms=SESSIONS_BUDGET_MS, samples=len(samples),
                  max_ms=round(max(samples), 1))  # fmt: skip
    report.check(budget_id)


@pytest.mark.budget
@pytest.mark.req("TST-121", "TST-126", "API-122", "ANL-049", "NFR-004")
def test_post_sessions_p95_pr_scope(history: History, perf_report: PerfReport) -> None:
    _post_sessions(history, 50, "TST-121-PR", perf_report)


@pytest.mark.req("TST-121", "API-122", "ANL-049", "NFR-004")
def test_post_sessions_p95_200_requests(history: History, perf_report: PerfReport) -> None:
    _post_sessions(history, 200, "TST-121", perf_report)


READ_ENDPOINTS = (
    ("NFR-001", "/residents", {}),
    ("NFR-002", "/residents/L001", {}),
    ("NFR-002", "/scores", {"resident_code": "L001"}),
    ("NFR-003", "/alerts", {}),
    ("NFR-003", "/data-alerts", {}),
    ("NFR-003", "/analytics", {}),
)


@pytest.mark.req("TST-122", "API-121", "NFR-001", "NFR-002", "NFR-003", "NFR-150")
@pytest.mark.parametrize(("nfr", "path", "params"), READ_ENDPOINTS,
                         ids=[p for _, p, _ in READ_ENDPOINTS])  # fmt: skip
def test_read_endpoints_p95_on_ds08(
    ds08_stack: Stack, perf_report: PerfReport, nfr: str, path: str, params: dict[str, str]
) -> None:
    s = ds08_stack
    headers = s.admin()
    limiter.reset()
    samples: list[float] = []
    for index in range(WARMUP + READ_SAMPLES):
        response, ms = s.timed("GET", path, headers=headers, params=params)
        assert response.status_code == 200, f"GET {path}: {response.status_code} {response.text}"
        if index >= WARMUP:
            samples.append(ms)
    budget_id = f"TST-122 GET {path}" + (f"?{params}" if params else "")
    perf_report.record(budget_id, f"GET {path} on DS-08 ({nfr})", measured_ms=p95(samples),
                       budget_ms=READ_BUDGET_MS, samples=len(samples))  # fmt: skip
    perf_report.check(budget_id)


@pytest.mark.budget
@pytest.mark.req("TST-124", "TST-126", "API-123", "NFR-009", "ANL-048")
def test_ingest_src05_accepted_and_processed(perf_report: PerfReport) -> None:
    with stack(seed_test_roster=True, pipeline_as_of=TEST_AS_OF) as s:  # empty test_v0_1 roster
        headers = s.admin()
        limiter.reset()
        response, accepted_ms = s.timed(
            "POST", "/ingest", headers=headers,
            files={"file": (INPUT_CSV.name, INPUT_CSV.read_bytes(), "text/csv")},
        )  # fmt: skip
        assert response.status_code == 202, f"POST /ingest: {response.status_code} {response.text}"
        run_id = response.json()["pipeline_run_id"]
        run, waited_ms = s.wait_run(run_id, INGEST_DONE_BUDGET_MS / 1000)
    perf_report.record("TST-124-accepted", "POST /ingest SRC-05 CSV answers 202",
                       measured_ms=accepted_ms, budget_ms=INGEST_ACCEPT_BUDGET_MS,
                       statistic="elapsed")  # fmt: skip
    perf_report.record("TST-124-processed", "SRC-05 batch run reaches succeeded",
                       measured_ms=accepted_ms + waited_ms, budget_ms=INGEST_DONE_BUDGET_MS,
                       statistic="elapsed",
                       run_status=None if run is None else run["status"])  # fmt: skip
    perf_report.check("TST-124-accepted")
    assert run is not None, f"batch run {run_id} still running after 30 s"
    assert run["status"] == "succeeded", f"batch run: {run}"
    perf_report.check("TST-124-processed")


@pytest.mark.req("API-120")
def test_health_p95(ds08_stack: Stack, perf_report: PerfReport) -> None:
    s = ds08_stack
    samples: list[float] = []
    for index in range(WARMUP + READ_SAMPLES):
        response, ms = s.timed("GET", "/health")
        assert response.status_code == 200, f"GET /health: {response.status_code} {response.text}"
        if index >= WARMUP:
            samples.append(ms)
    perf_report.record("API-120", "GET /health", measured_ms=p95(samples),
                       budget_ms=HEALTH_BUDGET_MS, samples=len(samples))  # fmt: skip
    perf_report.check("API-120")
