"""VC-R05 Possible other speaker (TRD 14 §4.7.5, TDV-055; FEAT-059-FR-05; AGT-044)."""

from __future__ import annotations

import pytest

from tests.validation.cases import TIERS, days, finish, outputs, resident_sheets, rule

pytestmark = pytest.mark.validation

QUARANTINED = {
    8: "possible other speaker (F0 z=-8.61; composite features with |z|>=3: 4)",
    22: "possible other speaker (F0 z=-7.34; composite features with |z|>=3: 3)",
}


@pytest.mark.req("VC-R05", "TDV-055", "FEAT-059-FR-05", "AGT-044")
@pytest.mark.parametrize("tier", TIERS)
def test_vc_r05_possible_other_speaker(request: pytest.FixtureRequest, tier: str) -> None:
    out = outputs(request, tier)
    result = resident_sheets(out, "R05")
    by_day = days(out, "R05")
    for day, reason in QUARANTINED.items():
        result += rule(
            "Annotated_sessions",
            f"R05/{day}",
            "expected_status",
            "quarantined",
            by_day[day]["expected_status"],
            4,
        )
        result += rule(
            "Annotated_sessions",
            f"R05/{day}",
            "expected_reason",
            reason,
            by_day[day]["expected_reason"],
            4,
        )
        result += rule(
            "Annotated_sessions", f"R05/{day}", "in_baseline", False, by_day[day]["in_baseline"], 6
        )
        result += rule(
            "Exp_scores",
            f"R05/{day}",
            "row",
            False,
            f"R05-202610{day:02d}-01" in {k[0] for k in out.scores},
            7,
        )
    result += rule(
        "Exp_resident_outcomes",
        "R05/1",
        "baseline_frozen_after",
        "R05-20261017-01",
        out.outcomes[("R05", 1)]["baseline_frozen_after"],
        6,
    )
    scores = [s for k, s in out.scores.items() if k[0].startswith("R05-")]
    result += rule("Exp_scores", "R05", "scored", 12, len(scores), 7)
    result += rule(
        "Exp_scores",
        "R05",
        "max cusum_tally",
        4.005975,
        max(s["cusum_tally"] for s in scores),
        8,
        "float",
    )
    finish("VC-R05", tier, result)
