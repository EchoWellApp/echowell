"""Sustained ingest (TRD 13 TST-190; TRD 03 NFR-151; TRD 16 CIC-035; FEAT-079-FR-14). Nightly.

600 valid records are sent to `POST /api/v1/sessions` with one API key at a steady 10 records/s
for 60 s (request i leaves at t0 + i * 100 ms; concurrent clients so a slow response never delays
the schedule). Every response must be 201 or 200: no 429 (the production limit RATE_LIMIT_INGEST
600/minute stays as configured) and no 5xx. The 60 residents S001..S060 each receive one record
every 6 s on consecutive days, so two requests for the same resident never overlap.
"""

from __future__ import annotations

import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from backend.core.rate_limit import limiter
from tests.performance import make_load_dataset as ds
from tests.performance.conftest import PerfReport, p95, stack

pytestmark = pytest.mark.performance

RATE_PER_S = 10
DURATION_S = 60
RESIDENTS = 60
TOTAL = RATE_PER_S * DURATION_S


@pytest.mark.slow
@pytest.mark.req("TST-190", "NFR-151")
def test_sustained_10_records_per_second_for_60_s(tmp_path: Path, perf_report: PerfReport) -> None:
    data = ds.generate(ds.SEED + 2, residents=RESIDENTS, days=TOTAL // RESIDENTS,
                       start=date(2026, 9, 1), drop_fraction=0.0, noisy_fraction=0.0,
                       prefix="S")  # fmt: skip
    ds.write(data, tmp_path)
    by_day = sorted(data.records, key=lambda r: (r["timestamp_utc"][:10], r["resident_id"]))
    assert len(by_day) == TOTAL
    with stack(tmp_path) as s:
        limiter.reset()
        headers = s.key()
        results: list[tuple[int, float]] = [(0, 0.0)] * TOTAL
        lock = threading.Lock()
        t0 = time.perf_counter() + 0.5

        def send(index: int, record: dict[str, Any]) -> None:
            delay = t0 + index / RATE_PER_S - time.perf_counter()
            if delay > 0:
                time.sleep(delay)
            response, ms = s.timed("POST", "/sessions", headers=headers, json=record)
            with lock:
                results[index] = (response.status_code, ms)

        with ThreadPoolExecutor(max_workers=32) as pool:
            for index, record in enumerate(by_day):
                pool.submit(send, index, record)
        elapsed_s = time.perf_counter() - t0
    codes = Counter(code for code, _ in results)
    latencies = [ms for _, ms in results]
    passed = set(codes) <= {200, 201}
    perf_report.outcome("TST-190", "sustained POST /sessions, 10 records/s for 60 s, all 201/200",
                        passed=passed, samples=TOTAL, elapsed_s=round(elapsed_s, 1),
                        status_codes={str(k): v for k, v in sorted(codes.items())},
                        p95_ms=round(p95(latencies), 1))  # fmt: skip
    assert passed, f"non-2xx responses during sustained ingest: {dict(codes)}"
    assert elapsed_s <= DURATION_S + 5, f"the schedule slipped: {elapsed_s:.1f} s for {TOTAL}"
