"""Study team figures recomputed from the answer key (TRD 14 TDV-075, Table 4.9-E; FEAT-060-FR-11,
FEAT-060-AC-05).

Every Table 4.9-E figure is derived here from DS-02 (Annotated_sessions, Exp_status_counts,
Exp_resident_outcomes) and DS-10, independently of the pipeline, and compared with
`GET /api/v1/analytics` on Tier B, so the page "matches the pipeline answer key".
"""

from __future__ import annotations

import csv
from collections import Counter
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

import pytest

from tests.validation.answer_key import GROUND_TRUTH, local_date, rows
from tests.validation.tier_b import TierB, load_ground_truth

pytestmark = pytest.mark.validation

DAYS, RESIDENTS = 30, 10
REASON_KEYS = {"quality flag poor": "quality_flag_poor", "noise above limit": "noise_above_limit",
               "speech too short": "speech_too_short"}  # fmt: skip


def _percent(part: int, whole: int) -> int:
    return int((Decimal(part) * 100 / Decimal(whole)).quantize(Decimal(1), ROUND_HALF_UP))


def recompute() -> dict[str, Any]:
    annotated = rows("Annotated_sessions")
    statuses = Counter(r["expected_status"] for r in annotated)
    received = sum(r["arrival_order"] != "no record" and r["expected_status"] != "duplicate"
                   for r in annotated)  # fmt: skip
    expected = RESIDENTS * DAYS
    missed = statuses["missing_resident"] + statuses["missing_device_gap"]
    reasons: Counter[str] = Counter()
    multi = 0
    for r in annotated:
        if r["expected_status"] == "set_aside":
            parts = str(r["expected_reason"]).split("; ")
            multi += len(parts) > 1
            reasons.update(REASON_KEYS[p] for p in parts)
    outcomes = rows("Exp_resident_outcomes")
    current = {}
    for o in sorted(outcomes, key=lambda o: (o["resident_id"], o["epoch"])):
        current[o["resident_id"]] = o
    epochs = Counter(o["resident_id"] for o in outcomes)
    alarms = sorted(o["resident_id"] for o in outcomes
                    if o["first_alarm_session"] not in (None, "none"))  # fmt: skip
    counts = {r["resident_id"]: r for r in rows("Exp_status_counts")}
    by_resident = sorted(((code, _percent(int(c["usable"]), DAYS)) for code, c in counts.items()),
                         key=lambda item: (item[1], item[0]))  # fmt: skip
    daily = []
    for day in range(1, DAYS + 1):
        same = [
            r for r in annotated if int(r["day"]) == day and r["expected_status"] != "duplicate"
        ]
        tally = Counter(r["expected_status"] for r in same)
        silent = sorted(
            {r["device_id"] for r in same if r["expected_status"] == "missing_device_gap"}
        )
        daily.append({"local_date": local_date(day).isoformat(), "used": tally["usable"],
                      "set_aside": tally["set_aside"], "quarantined": tally["quarantined"],
                      "missed": tally["missing_resident"] + tally["missing_device_gap"],
                      "silent_device_codes": silent})  # fmt: skip
    first_alarm = {o["resident_id"]: o["first_alarm_session"] for o in outcomes
                   if o["first_alarm_session"] not in (None, "none")}  # fmt: skip
    timing = []
    with GROUND_TRUTH.open(newline="", encoding="utf-8") as handle:
        for truth in csv.DictReader(handle):
            code, began = truth["resident_code"], truth["true_onset_date"] or None
            session = first_alarm.get(code)
            rang = f"{session[4:8]}-{session[8:10]}-{session[10:12]}" if session else None
            delay = ((date.fromisoformat(rang) - date.fromisoformat(began)).days
                     if rang and began else None)  # fmt: skip
            result = ("detected" if began and rang else "missed" if began
                      else "false_alarm" if rang else "correct_no_alarm")  # fmt: skip
            timing.append({"resident_code": code, "planted_change": truth["planted_change"],
                           "change_began": began, "alarm_rang": rang, "delay_days": delay,
                           "result": result})  # fmt: skip
    return {
        "kpis": {
            "checkins_received": {"count": received, "expected": expected,
                                  "percent": _percent(received, expected)},
            "used_for_scoring": {"count": statuses["usable"], "expected": expected,
                                 "percent": _percent(statuses["usable"], expected)},
            "baselines_formed": {
                "formed": sum(o["baseline_formed"] == "yes" for o in current.values()),
                "residents": len(current),
                "forming_resident_codes": sorted(c for c, o in current.items()
                                                 if o["baseline_formed"] != "yes"),
                "restarts": [{"resident_code": c, "restart_count": n - 1}
                             for c, n in sorted(epochs.items()) if n > 1]},
            "alarms_raised": {"count": len(alarms), "resident_codes": alarms,
                              "not_reviewed_count": len(alarms)},
        },
        "funnel": {"expected": expected, "residents": RESIDENTS, "days": DAYS,
                   "received": received, "missed": missed,
                   "duplicates_removed": statuses["duplicate"],
                   "passed_quality": received - statuses["set_aside"],
                   "set_aside": statuses["set_aside"], "set_aside_reasons": dict(reasons),
                   "set_aside_multi_reason": multi, "quarantined": statuses["quarantined"],
                   "used": statuses["usable"]},
        "by_resident": by_resident,
        "daily_series": daily,
        "alarm_timing": timing,
    }  # fmt: skip


@pytest.mark.req("TDV-075", "FEAT-060-FR-11", "FEAT-060-AC-05")
def test_study_team_figures_match_the_answer_key(tier_b_harness: TierB) -> None:
    load_ground_truth(tier_b_harness.urls)  # replaces DS-10; outputs never depend on it (TDV-102)
    api = tier_b_harness.get("/analytics", role="researcher")
    expected = recompute()
    assert api["kpis"] == expected["kpis"]
    assert api["funnel"] == expected["funnel"]
    assert [(b["resident_code"], b["used_percent"]) for b in api["by_resident"]] == expected[
        "by_resident"]  # fmt: skip
    assert api["daily_series"] == expected["daily_series"]
    assert api["alarm_timing"] == expected["alarm_timing"]
    assert expected["kpis"]["checkins_received"]["percent"] == 94  # 281 / 300 = 93.67 % (4.9-E)
