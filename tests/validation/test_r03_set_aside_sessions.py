"""VC-R03 Set-aside sessions (TRD 14 §4.7.3, TDV-053; FEAT-059-FR-03; AGT-049)."""

from __future__ import annotations

import pytest

from tests.validation.cases import TIERS, days, finish, outputs, resident_sheets, rule

pytestmark = pytest.mark.validation

SET_ASIDE = {3: "noise above limit", 7: "quality flag poor", 10: "speech too short",
             14: "noise above limit", 18: "quality flag poor; noise above limit",
             22: "quality flag poor", 26: "speech too short"}  # fmt: skip
SCORED_DAYS = (24, 25, 27, 28, 29, 30)


@pytest.mark.req("VC-R03", "TDV-053", "FEAT-059-FR-03", "AGT-049")
@pytest.mark.parametrize("tier", TIERS)
def test_vc_r03_set_aside_sessions(request: pytest.FixtureRequest, tier: str) -> None:
    out = outputs(request, tier)
    result = resident_sheets(out, "R03")
    by_day = days(out, "R03")
    for day, reason in SET_ASIDE.items():
        row = by_day[day]
        result += rule(
            "Annotated_sessions",
            f"R03/{day}",
            "expected_status",
            "set_aside",
            row["expected_status"],
            2,
        )
        result += rule(
            "Annotated_sessions", f"R03/{day}", "expected_reason", reason, row["expected_reason"], 2
        )
        result += rule(
            "Annotated_sessions", f"R03/{day}", "expected_epoch", 1, row["expected_epoch"], 3
        )
        result += rule(
            "Annotated_sessions", f"R03/{day}", "in_baseline", False, row["in_baseline"], 6
        )
    result += rule(
        "Annotated_sessions",
        "R03/12",
        "expected_status",
        "missing_device_gap",
        by_day[12]["expected_status"],
        10,
    )
    result += rule(
        "Exp_resident_outcomes",
        "R03/1",
        "baseline_frozen_after",
        "R03-20261023-01",
        out.outcomes[("R03", 1)]["baseline_frozen_after"],
        6,
    )
    scores = {k[0]: s for k, s in out.scores.items() if k[0].startswith("R03-")}
    result += rule(
        "Exp_scores",
        "R03",
        "scored days",
        list(SCORED_DAYS),
        sorted(int(s["local_date"][-2:]) for s in scores.values()),
        7,
    )
    result += rule(
        "Exp_scores",
        "R03",
        "max cusum_tally",
        2.202944,
        max(s["cusum_tally"] for s in scores.values()),
        8,
        "float",
    )
    finish("VC-R03", tier, result)
