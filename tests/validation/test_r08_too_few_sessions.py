"""VC-R08 Too few sessions (TRD 14 §4.7.8, TDV-058; FEAT-059-FR-08)."""

from __future__ import annotations

import pytest

from tests.validation.cases import TIERS, days, finish, outputs, resident_sheets, rule

pytestmark = pytest.mark.validation

SET_ASIDE = {5: "noise above limit", 9: "quality flag poor", 20: "noise above limit",
             25: "quality flag poor", 29: "speech too short"}  # fmt: skip
MISSING = (2, 4, 6, 8, 11, 13, 15, 17, 19, 21, 24, 27)
USABLE = (1, 3, 7, 10, 12, 14, 16, 18, 22, 23, 26, 28, 30)
NOT_FORMED = "Too few usable sessions: baseline pending, nothing scored"


@pytest.mark.req("VC-R08", "TDV-058", "FEAT-059-FR-08")
@pytest.mark.parametrize("tier", TIERS)
def test_vc_r08_too_few_sessions(request: pytest.FixtureRequest, tier: str) -> None:
    out = outputs(request, tier)
    result = resident_sheets(
        out, "R08", ("Annotated_sessions", "Exp_status_counts", "Exp_resident_outcomes")
    )
    by_day = days(out, "R08")
    for day, reason in SET_ASIDE.items():
        result += rule(
            "Annotated_sessions",
            f"R08/{day}",
            "expected_reason",
            reason,
            by_day[day]["expected_reason"],
            2,
        )
    for day in MISSING:
        result += rule(
            "Annotated_sessions",
            f"R08/{day}",
            "expected_status",
            "missing_resident",
            by_day[day]["expected_status"],
            10,
        )
    usable = sorted(d for d, r in by_day.items() if r["expected_status"] == "usable")
    result += rule("Annotated_sessions", "R08", "usable days", list(USABLE), usable, 2)
    outcome = out.outcomes[("R08", 1)]
    result += rule(
        "Exp_resident_outcomes", "R08/1", "baseline_formed", False, outcome["baseline_formed"], 6
    )
    result += rule("Exp_resident_outcomes", "R08/1", "note", NOT_FORMED, outcome["note"], 6)
    result += rule("baselines", "R08", "rows", 0, sum(k[0] == "R08" for k in out.baselines), 6)
    result += rule("scores", "R08", "rows", 0, sum(k[0].startswith("R08-") for k in out.scores), 7)
    result += rule(
        "alerts", "R08", "rows", 0, sum(a["resident_id"] == "R08" for a in out.alerts), 9
    )
    if tier == "B":
        harness = request.getfixturevalue("tier_b_harness")
        result += rule(
            "pipeline_runs", harness.run["id"], "status", "succeeded", harness.run["status"], 6
        )
        result += rule(
            "pipeline_runs",
            harness.run["id"],
            "error_message",
            None,
            harness.run.get("error_message"),
            6,
        )
    finish("VC-R08", tier, result)
