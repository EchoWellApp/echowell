"""VC-R01 Clean control (TRD 14 §4.7.1, TDV-051; FEAT-059-FR-01)."""

from __future__ import annotations

import pytest

from tests.validation.cases import TIERS, days, finish, outputs, resident_sheets, rule

pytestmark = pytest.mark.validation


@pytest.mark.req("VC-R01", "TDV-051", "FEAT-059-FR-01", "AGT-041")
@pytest.mark.parametrize("tier", TIERS)
def test_vc_r01_clean_control(request: pytest.FixtureRequest, tier: str) -> None:
    out = outputs(request, tier)
    result = resident_sheets(out, "R01")
    for day, row in days(out, "R01").items():
        result += rule(
            "Annotated_sessions",
            f"R01/{day}",
            "expected_status",
            "usable",
            row["expected_status"],
            2,
        )
        result += rule(
            "Annotated_sessions", f"R01/{day}", "expected_reason", None, row["expected_reason"], 2
        )
        result += rule(
            "Annotated_sessions",
            f"R01/{day}",
            "expected_morning",
            False,
            row["expected_morning"],
            5,
        )
        result += rule(
            "Annotated_sessions", f"R01/{day}", "expected_epoch", 1, row["expected_epoch"], 3
        )
    outcome = out.outcomes[("R01", 1)]
    result += rule(
        "Exp_resident_outcomes",
        "R01/1",
        "baseline_frozen_after",
        "R01-20261016-01",
        outcome["baseline_frozen_after"],
        6,
    )
    result += rule(
        "Exp_resident_outcomes", "R01/1", "scored_sessions", 14, outcome["scored_sessions"], 7
    )
    result += rule(
        "Exp_resident_outcomes",
        "R01/1",
        "first_alarm_session",
        None,
        outcome["first_alarm_session"],
        9,
    )
    tallies = [s["cusum_tally"] for k, s in out.scores.items() if k[0].startswith("R01-")]
    result += rule("Exp_scores", "R01", "max cusum_tally", 0.333077, max(tallies), 8, "float")
    ledger = [d for d in out.ledger if d[0] == "R01"]
    result += rule(
        "day_ledger", "R01", "checked_in days", 30, sum(d[2] == "checked_in" for d in ledger), 10
    )
    result += rule("day_ledger", "R01", "rows", 30, len(ledger), 10)
    finish("VC-R01", tier, result)
