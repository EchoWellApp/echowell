"""Per-feature z (TRD 08 §4.8; FEAT-046)."""

from __future__ import annotations

import math
from dataclasses import replace

import pytest

from analytics.config import COMPOSITE_KEYS, TEST_V0_1
from analytics.zscore_calculator import feature_z
from tests.unit.analytics.src05 import result

pytestmark = pytest.mark.unit

R09_Z = {
    "loudness_dbfs": -2.737502, "total_phrase_duration_s": 2.420232,
    "speech_rate_syl_per_s": -1.180359, "articulation_rate_syl_per_s": -1.584269,
    "number_of_pauses": 1.348982, "pause_fraction": 2.285774, "voiced_fraction": -4.721435,
}  # fmt: skip


@pytest.mark.req("BSC-037", "AC-BSC-06", "FEAT-046-AC-01")
def test_r09_ringing_session_z() -> None:
    row = next(s for s in result().scores if s.session_id == "R09-20261021-01")
    assert list(row.z) == [f"z_{k}" for k in COMPOSITE_KEYS]
    for key, value in R09_Z.items():
        assert math.isclose(row.z[f"z_{key}"], value, abs_tol=1e-6), key


@pytest.mark.req("BSC-035")
def test_zero_spread_gives_zero() -> None:
    session = next(s for s in result().sessions if s.record.session_id == "R09-20261021-01")
    baselines = {b.feature_key: b for b in result().baselines if b.resident_code == "R09"}
    baselines["pause_fraction"] = replace(baselines["pause_fraction"], robust_spread=0.0)
    assert feature_z(session, baselines, TEST_V0_1)["pause_fraction"] == 0.0
