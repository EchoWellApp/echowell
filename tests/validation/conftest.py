"""Validation harness fixtures (TRD 14 §4.4; TRD 13 TST-080..TST-083; FEAT-058, FEAT-059).

`tier_a` runs the engine in-process on DS-01; `tier_b` builds the full system on a throwaway
PostgreSQL 16 database once per session (`tests.support.system`). Case tests record their
comparison results with `record`; after a full-suite session `report.write` renders
`docs/reports/ALGORITHM_VALIDATION_REPORT.md` and `docs/reports/validation_results.json`, failures
included (CIC-100); partial selections leave them alone (TRD 24 D-137).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from analytics import PipelineResult
from tests.support.system import TierB, tier_b
from tests.validation import report
from tests.validation.guard import (  # noqa: F401 - pytest hooks (TST-083)
    pytest_collection_modifyitems,
    pytest_runtest_logreport,
)
from tests.validation.guard import pytest_sessionfinish as _guard_finish
from tests.validation.outputs import Outputs, from_result, run_tier_a
from tests.validation.tier_b import collect


@pytest.fixture(scope="session")
def tier_a_result() -> PipelineResult:
    result = run_tier_a()
    report.RESULTS.config_snapshot = result.run_config  # the report header hash (TDV-070)
    return result


@pytest.fixture(scope="session")
def tier_a(tier_a_result: PipelineResult) -> Outputs:
    return from_result(tier_a_result)


@pytest.fixture(scope="session")
def tier_b_harness() -> Iterator[TierB]:
    with tier_b() as harness:
        yield harness


@pytest.fixture(scope="session")
def tier_b_outputs(tier_b_harness: TierB) -> Outputs:
    return collect(tier_b_harness)


@pytest.fixture(scope="session")
def tiers(tier_a: Outputs, tier_b_outputs: Outputs) -> dict[str, Outputs]:
    return {"A": tier_a, "B": tier_b_outputs}


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if report.complete(report.RESULTS):  # full-suite sessions only (TRD 24 D-137)
        report.write(report.RESULTS)
    elif report.RESULTS.cases:
        print("\nPartial validation run: docs/reports/ALGORITHM_VALIDATION_REPORT.md not written.")
    _guard_finish(session, exitstatus)
