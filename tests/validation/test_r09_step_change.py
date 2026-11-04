"""VC-R09 Step change (TRD 14 §4.7.9, TDV-059; FEAT-059-FR-09; CUS-027, AGT-047, AGT-048)."""

from __future__ import annotations

import pytest

from tests.validation.cases import TIERS, finish, outputs, resident_sheets, rule

pytestmark = pytest.mark.validation

# TRD 14 §4.7.9: session, composite_raw, composite_z, cusum_tally, alarm (rounded to 6 decimals)
TABLE = (
    ("R09-20261017-01", 2.035972, 3.745474, 3.245474, "off"),
    ("R09-20261018-01", -0.034166, -0.135711, 2.609763, "off"),
    ("R09-20261019-01", -0.141370, -0.336702, 1.773061, "off"),
    ("R09-20261020-01", 0.235887, 0.370597, 1.643658, "off"),
    ("R09-20261021-01", 2.325508, 4.288307, 5.431965, "rings"),
    ("R09-20261022-01", 1.652910, 3.027292, 7.959257, "on"),
    ("R09-20261023-01", 0.481301, 0.830709, 8.289966, "on"),
    ("R09-20261024-01", 1.598263, 2.924838, 10.714804, "on"),
    ("R09-20261025-01", 1.225627, 2.226203, 12.441007, "on"),
    ("R09-20261026-01", 1.814181, 3.329651, 15.270658, "on"),
    ("R09-20261027-01", 1.070469, 1.935308, 16.705966, "on"),
    ("R09-20261028-01", 1.401480, 2.555900, 18.761866, "on"),
    ("R09-20261029-01", 2.633015, 4.864836, 23.126702, "on"),
    ("R09-20261030-01", 2.280302, 4.203554, 26.830256, "on"),
)
FROZEN_AFTER = "R09-20261016-01"
FIRST_ALARM = ("R09-20261021-01", "2026-10-21", 5.431965)


@pytest.mark.req("VC-R09", "TDV-059", "FEAT-059-FR-09", "CUS-027", "AGT-047", "AGT-048")
@pytest.mark.parametrize("tier", TIERS)
def test_vc_r09_step_change(request: pytest.FixtureRequest, tier: str) -> None:
    out = outputs(request, tier)
    result = resident_sheets(out, "R09")
    scores = {k[0]: s for k, s in out.scores.items() if k[0].startswith("R09-")}
    result += rule("Exp_scores", "R09", "sessions", [row[0] for row in TABLE], sorted(scores), 7)
    for session, raw, z, tally, alarm in TABLE:
        score = scores.get(session, {})
        result += rule(
            "Exp_scores", session, "composite_raw", raw, score.get("composite_raw"), 7, "float"
        )
        result += rule(
            "Exp_scores", session, "composite_z", z, score.get("composite_z"), 7, "float"
        )
        result += rule(
            "Exp_scores", session, "cusum_tally", tally, score.get("cusum_tally"), 8, "float"
        )
        result += rule("Exp_scores", session, "alarm", alarm, score.get("alarm"), 8)
    outcome = out.outcomes[("R09", 1)]
    result += rule(
        "Exp_resident_outcomes",
        "R09/1",
        "baseline_frozen_after",
        FROZEN_AFTER,
        outcome["baseline_frozen_after"],
        6,
    )
    result += rule(
        "Exp_resident_outcomes",
        "R09/1",
        "first_alarm_session",
        FIRST_ALARM[0],
        outcome["first_alarm_session"],
        9,
    )
    alerts = [a for a in out.alerts if a["resident_id"] == "R09"]
    result += rule("alerts", "R09", "rows", 1, len(alerts), 9)
    for alert in alerts:
        result += rule("alerts", "R09", "session_id", FIRST_ALARM[0], alert["session_id"], 9)
        result += rule("alerts", "R09", "local_date", FIRST_ALARM[1], alert["local_date"], 9)
        result += rule(
            "alerts", "R09", "cusum_value", FIRST_ALARM[2], alert["cusum_value"], 9, "float"
        )
        result += rule("alerts", "R09", "status", "open", alert["status"], 9)
    finish("VC-R09", tier, result)
