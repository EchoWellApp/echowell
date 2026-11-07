"""VC-R06 Morning effect (TRD 14 §4.7.6, TDV-056; FEAT-059-FR-06; AGT-040, AGT-050).

VC-R06-MUT (all offsets 0 must break the R06 loudness baseline) is in `test_invariance.py`.
"""

from __future__ import annotations

import pytest

from tests.validation.cases import TIERS, days, finish, outputs, resident_sheets, rule
from tests.validation.comparator import compare_sheet

pytestmark = pytest.mark.validation

MORNING_DAYS = (1, 4, 7, 10, 13, 16, 19, 22, 25, 28)
DAY1_ADJUSTED = {"loudness_dbfs": -23.92, "total_phrase_duration_s": 3.91,
                 "speech_rate_syl_per_s": 4.26, "articulation_rate_syl_per_s": 4.62,
                 "number_of_pauses": 2.0, "pause_fraction": 0.116,
                 "voiced_fraction": 0.615}  # fmt: skip
MORNING_SCORED = ("R06-20261019-01", "R06-20261022-01", "R06-20261025-01", "R06-20261028-01")


@pytest.mark.req("VC-R06", "TDV-056", "FEAT-059-FR-06", "AGT-040", "AGT-050")
@pytest.mark.parametrize("tier", TIERS)
def test_vc_r06_morning_effect(request: pytest.FixtureRequest, tier: str) -> None:
    out = outputs(request, tier)
    result = resident_sheets(out, "R06")
    result += compare_sheet("Exp_morning_offset", out)
    by_day = days(out, "R06")
    for day, row in by_day.items():
        result += rule(
            "Annotated_sessions",
            f"R06/{day}",
            "expected_morning",
            day in MORNING_DAYS,
            row["expected_morning"],
            5,
        )
    adjusted = out.adjusted[("R06-20261001-01",)]
    for key, value in DAY1_ADJUSTED.items():
        result += rule("adjusted", "R06-20261001-01", key, value, adjusted[key], 5, "float")
    afternoon = by_day[2]
    for key in DAY1_ADJUSTED:
        result += rule(
            "adjusted",
            "R06-20261002-01",
            key,
            afternoon[key],
            out.adjusted[("R06-20261002-01",)][key],
            5,
            "float",
        )
    morning_scored = sorted(
        k[0] for k, s in out.scores.items() if k[0].startswith("R06-") and s["morning"]
    )
    result += rule("Exp_scores", "R06", "morning sessions", list(MORNING_SCORED), morning_scored, 5)
    baseline_morning = [d for d in MORNING_DAYS if d <= 16 and by_day[d]["in_baseline"]]
    result += rule(
        "Annotated_sessions",
        "R06",
        "morning baseline days",
        [1, 4, 7, 10, 13, 16],
        baseline_morning,
        6,
    )
    finish("VC-R06", tier, result)
