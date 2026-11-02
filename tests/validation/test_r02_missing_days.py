"""VC-R02 Missing days (TRD 14 §4.7.2, TDV-052; FEAT-059-FR-02; AGT-046)."""

from __future__ import annotations

import pytest

from tests.validation.cases import TIERS, days, finish, outputs, resident_sheets, rule

pytestmark = pytest.mark.validation

MISSING = (4, 9, 10, 17, 23)
GAP = 12
SCORED_DAYS = (22, 24, 25, 26, 27, 28, 29, 30)


@pytest.mark.req("VC-R02", "TDV-052", "FEAT-059-FR-02", "AGT-046")
@pytest.mark.parametrize("tier", TIERS)
def test_vc_r02_missing_days(request: pytest.FixtureRequest, tier: str) -> None:
    out = outputs(request, tier)
    result = resident_sheets(out, "R02")
    by_day = days(out, "R02")
    for day in MISSING:
        result += rule(
            "Annotated_sessions",
            f"R02/{day}",
            "expected_status",
            "missing_resident",
            by_day[day]["expected_status"],
            10,
        )
        result += rule(
            "Annotated_sessions",
            f"R02/{day}",
            "expected_reason",
            "no record received",
            by_day[day]["expected_reason"],
            10,
        )
    result += rule(
        "Annotated_sessions",
        f"R02/{GAP}",
        "expected_status",
        "missing_device_gap",
        by_day[GAP]["expected_status"],
        10,
    )
    result += rule(
        "Annotated_sessions",
        f"R02/{GAP}",
        "expected_reason",
        "all residents on shared device D02 have no record",
        by_day[GAP]["expected_reason"],
        10,
    )
    usable = [d for d, r in by_day.items() if r["expected_status"] == "usable"]
    result += rule("Annotated_sessions", "R02", "usable days", 24, len(usable), 2)
    result += rule(
        "Exp_resident_outcomes",
        "R02/1",
        "baseline_frozen_after",
        "R02-20261021-01",
        out.outcomes[("R02", 1)]["baseline_frozen_after"],
        6,
    )
    scored = sorted(
        int(s["local_date"][-2:]) for k, s in out.scores.items() if k[0].startswith("R02-")
    )
    result += rule("Exp_scores", "R02", "scored days", list(SCORED_DAYS), scored, 7)
    # nothing carried forward: a missing day has no record values and no score
    for day in (*MISSING, GAP):
        result += rule(
            "Annotated_sessions",
            f"R02/{day}",
            "loudness_dbfs",
            None,
            by_day[day]["loudness_dbfs"],
            10,
        )
        result += rule(
            "Exp_scores",
            f"R02/{day}",
            "row",
            False,
            f"R02-202610{day:02d}-01" in {k[0] for k in out.scores},
            10,
        )
    finish("VC-R02", tier, result)
