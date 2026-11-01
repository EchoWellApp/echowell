"""CUSUM tally and alarm state (TRD 09 §4.1; FEAT-047)."""

from __future__ import annotations

import math
from datetime import date

import pytest

from analytics.config import TEST_V0_1, ScoreRow
from analytics.cusum_engine import run_cusum
from tests.unit.analytics.src05 import result

pytestmark = pytest.mark.unit


def _rows(zs: list[float], epoch: int = 1) -> list[ScoreRow]:
    return [ScoreRow(f"S{i}", f"r{i}", "R01", epoch, date(2026, 10, i + 1), False, {}, 0.0, z)
            for i, z in enumerate(zs)]  # fmt: skip


@pytest.mark.req("CUS-001", "CUS-006", "CUS-007", "CU-01", "FEAT-047-AC-01")
def test_tally_and_states() -> None:
    out = run_cusum(_rows([3.0, 3.0, 0.0, -20.0, 6.0]), TEST_V0_1)
    assert [r.cusum_tally for r in out] == [2.5, 5.0, 4.5, 0.0, 5.5]
    assert [r.alarm_state for r in out] == ["off", "rings", "on", "on", "on"]


@pytest.mark.req("CUS-005", "FEAT-047-AC-02")
def test_epochs_have_their_own_tally() -> None:
    out = run_cusum([*_rows([6.0]), *_rows([1.0], epoch=2)], TEST_V0_1)
    assert [(r.cusum_tally, r.alarm_state) for r in out] == [(5.5, "rings"), (0.5, "off")]


@pytest.mark.req("CUS-011", "VC-R09", "VC-R10", "FEAT-047-AC-03")
def test_src05_alarms() -> None:
    rings = {s.resident_code: s for s in result().scores if s.alarm_state == "rings"}
    assert sorted(rings) == ["R09", "R10"]
    assert rings["R09"].session_id == "R09-20261021-01"
    assert math.isclose(rings["R09"].cusum_tally, 5.431965, abs_tol=1e-6)
    assert rings["R10"].session_id == "R10-20261024-01"
    tallies = {e.resident_code: e.current_tally for e in result().epochs if e.alarm_on}
    assert (round(tallies["R09"], 1), round(tallies["R10"], 1)) == (26.8, 13.4)
    r05 = max(s.cusum_tally for s in result().scores if s.resident_code == "R05")
    assert 4.0 < r05 < 5.0  # the R05 near-miss stays below the alarm line
