"""VC-R07 Device move (TRD 14 §4.7.7, TDV-057; FEAT-059-FR-07; AGT-045)."""

from __future__ import annotations

import pytest

from tests.validation.cases import TIERS, days, finish, outputs, resident_sheets, rule

pytestmark = pytest.mark.validation

NOT_FORMED = "Too few usable sessions: baseline pending, nothing scored"


@pytest.mark.req("VC-R07", "TDV-057", "FEAT-059-FR-07", "AGT-045", "ASM-06")
@pytest.mark.parametrize("tier", TIERS)
def test_vc_r07_device_move(request: pytest.FixtureRequest, tier: str) -> None:
    out = outputs(request, tier)
    result = resident_sheets(out, "R07")
    by_day = days(out, "R07")
    for day, row in by_day.items():
        result += rule(
            "Annotated_sessions",
            f"R07/{day}",
            "expected_epoch",
            1 if day <= 12 else 2,
            row["expected_epoch"],
            3,
        )
        result += rule(
            "Annotated_sessions",
            f"R07/{day}",
            "device_id",
            "D07" if day <= 12 else "D07B",
            row["device_id"],
            3,
        )
    first, second = out.outcomes[("R07", 1)], out.outcomes[("R07", 2)]
    result += rule(
        "Exp_resident_outcomes", "R07/1", "usable_in_epoch", 12, first["usable_in_epoch"], 3
    )
    result += rule(
        "Exp_resident_outcomes", "R07/1", "baseline_formed", False, first["baseline_formed"], 6
    )
    result += rule("Exp_resident_outcomes", "R07/1", "note", NOT_FORMED, first["note"], 6)
    result += rule(
        "baselines", "R07/1", "rows", 0, sum(k[:2] == ("R07", 1) for k in out.baselines), 6
    )
    result += rule(
        "scores",
        "R07/1",
        "rows",
        0,
        sum(s["resident_id"] == "R07" and s["epoch"] == 1 for s in out.scores.values()),
        7,
    )
    result += rule(
        "alerts", "R07", "rows", 0, sum(a["resident_id"] == "R07" for a in out.alerts), 9
    )
    result += rule(
        "Exp_resident_outcomes", "R07/2", "usable_in_epoch", 18, second["usable_in_epoch"], 3
    )
    result += rule(
        "Exp_resident_outcomes",
        "R07/2",
        "baseline_frozen_after",
        "R07-20261028-01",
        second["baseline_frozen_after"],
        6,
    )
    result += rule(
        "Exp_baselines",
        "R07/2",
        "first_session",
        "R07-20261013-01",
        out.baselines[("R07", 2, "loudness_dbfs")]["first_session"],
        3,
    )
    scores = {k[0]: s for k, s in out.scores.items() if k[0].startswith("R07-")}
    result += rule(
        "Exp_scores", "R07", "scored", ["R07-20261029-01", "R07-20261030-01"], sorted(scores), 7
    )
    for session, score in scores.items():
        result += rule("Exp_scores", session, "cusum_tally", 0.0, score["cusum_tally"], 8, "float")
    result += rule(
        "Annotated_sessions",
        "R07/13",
        "baseline restart",
        1,
        1 if by_day[13]["in_baseline"] and by_day[12]["in_baseline"] else 0,
        6,
    )
    finish("VC-R07", tier, result)
