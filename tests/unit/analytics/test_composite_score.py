"""Signed composite raw and composite z (TRD 08 §4.7-§4.8; FEAT-046)."""

from __future__ import annotations

import math
from dataclasses import replace

import pytest

from analytics.composite_score import composite_raw, composite_z
from analytics.config import TEST_V0_1
from tests.unit.analytics.src05 import result
from tests.unit.analytics.test_zscore_calculator import R09_Z

pytestmark = pytest.mark.unit


@pytest.mark.req("BSC-032", "BSC-038", "AC-BSC-06", "FEAT-046-AC-02")
def test_r09_composite() -> None:
    raw = composite_raw(R09_Z, TEST_V0_1)
    assert math.isclose(raw, 2.325508, abs_tol=1e-6)
    comp = next(b for b in result().baselines if b.resident_code == "R09"
                and b.feature_key == "composite")  # fmt: skip
    assert math.isclose(composite_z(raw, comp), 4.288307, abs_tol=1e-5)
    row = next(s for s in result().scores if s.session_id == "R09-20261021-01")
    assert math.isclose(row.composite_z, 4.288307, abs_tol=1e-6)
    assert composite_z(1.0, replace(comp, robust_spread=0.0)) == 0.0


@pytest.mark.req("BSC-036", "AC-BSC-03", "FEAT-046-AC-03")
def test_src05_scored_sessions() -> None:
    scores = result().scores
    assert len(scores) == 98
    assert len({s.session_id for s in scores}) == 98
    sessions = {s.record.session_id: s for s in result().sessions if s.status != "duplicate"}
    assert all(sessions[s.session_id].status == "usable" and not sessions[s.session_id].in_baseline
               for s in scores)  # fmt: skip
