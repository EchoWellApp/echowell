"""VC-R10 Gradual drift (TRD 14 §4.7.10, TDV-060; FEAT-059-FR-10; CUS-027, AGT-047, AGT-048).

VC-R10-FRZ (b) and (c) are in `test_invariance.py`; (a) is the Exp_baselines R10 comparison here.
"""

from __future__ import annotations

import pytest

from tests.validation.cases import TIERS, finish, outputs, resident_sheets, rule

pytestmark = pytest.mark.validation

# TRD 14 §4.7.10: session, composite_raw, composite_z, cusum_tally, alarm (rounded to 6 decimals)
TABLE = (
    ("R10-20261017-01", 0.822306, 0.683927, 0.183927, "off"),
    ("R10-20261018-01", 1.145133, 0.965072, 0.648998, "off"),
    ("R10-20261019-01", 1.017307, 0.853750, 1.002749, "off"),
    ("R10-20261020-01", 1.018585, 0.854863, 1.357612, "off"),
    ("R10-20261021-01", 1.761905, 1.502208, 2.359820, "off"),
    ("R10-20261022-01", 2.231009, 1.910743, 3.770563, "off"),
    ("R10-20261023-01", 1.318402, 1.115968, 4.386532, "off"),
    ("R10-20261024-01", 2.431695, 2.085518, 5.972050, "rings"),
    ("R10-20261025-01", 1.189916, 1.004072, 6.476122, "on"),
    ("R10-20261026-01", 1.193254, 1.006980, 6.983102, "on"),
    ("R10-20261027-01", 3.096243, 2.664262, 9.147364, "on"),
    ("R10-20261028-01", 2.527292, 2.168771, 10.816135, "on"),
    ("R10-20261029-01", 2.623978, 2.252973, 12.569108, "on"),
    ("R10-20261030-01", 1.586069, 1.349075, 13.418183, "on"),
)
FROZEN_AFTER = "R10-20261016-01"
FIRST_ALARM = ("R10-20261024-01", "2026-10-24", 5.97205)


@pytest.mark.req("VC-R10", "TDV-060", "FEAT-059-FR-10", "CUS-027", "AGT-047", "AGT-048")
@pytest.mark.parametrize("tier", TIERS)
def test_vc_r10_gradual_drift(request: pytest.FixtureRequest, tier: str) -> None:
    out = outputs(request, tier)
    result = resident_sheets(out, "R10")
    scores = {k[0]: s for k, s in out.scores.items() if k[0].startswith("R10-")}
    result += rule("Exp_scores", "R10", "sessions", [row[0] for row in TABLE], sorted(scores), 7)
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
    outcome = out.outcomes[("R10", 1)]
    result += rule(
        "Exp_resident_outcomes",
        "R10/1",
        "baseline_frozen_after",
        FROZEN_AFTER,
        outcome["baseline_frozen_after"],
        6,
    )
    result += rule(
        "Exp_resident_outcomes",
        "R10/1",
        "first_alarm_session",
        FIRST_ALARM[0],
        outcome["first_alarm_session"],
        9,
    )
    alerts = [a for a in out.alerts if a["resident_id"] == "R10"]
    result += rule("alerts", "R10", "rows", 1, len(alerts), 9)
    for alert in alerts:
        result += rule("alerts", "R10", "session_id", FIRST_ALARM[0], alert["session_id"], 9)
        result += rule("alerts", "R10", "local_date", FIRST_ALARM[1], alert["local_date"], 9)
        result += rule(
            "alerts", "R10", "cusum_value", FIRST_ALARM[2], alert["cusum_value"], 9, "float"
        )
        result += rule("alerts", "R10", "status", "open", alert["status"], 9)
    finish("VC-R10", tier, result)
