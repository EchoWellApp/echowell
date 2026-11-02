"""API-level UI fixture checks on DS-07 (TRD 14 §4.9, TDV-061..TDV-069, TDV-074, TDV-076;
TRD 13 TST-056, TST-061; FEAT-060).

DS-07 is built as CI builds it: an empty migrated database, `seed test_v0_1` (roster, users, SRC-05
and the explicit-as-of run) and the DS-10 loader, with no clock override in the services. Every
response is validated against the OpenAPI document. The after-review check runs on its own copy so
the read-only assertions see the pristine seed (TDV-076, D-73).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from tests.contract.response_validation import check_response
from tests.support.system import TierB, ds07

pytestmark = pytest.mark.integration

AS_OF = "2026-10-30T20:00:00Z"
DEFAULT_ORDER = ["R09", "R10", "R03", "R08", "R01", "R02", "R04", "R05", "R06", "R07"]
# Table 4.9-B: device, last check-in (local time), used · set aside · held back · missed
ROWS = {
    "R09": ("D09", "14:28", [30, 0, 0, 0]), "R10": ("D10", "14:39", [30, 0, 0, 0]),
    "R03": ("D02", "14:19", [22, 7, 0, 1]), "R08": ("D08", "14:28", [13, 5, 0, 12]),
    "R01": ("D01", "14:07", [30, 0, 0, 0]), "R02": ("D02", "14:55", [24, 0, 0, 6]),
    "R04": ("D04", "14:17", [30, 0, 0, 0]), "R05": ("D05", "14:40", [28, 0, 2, 0]),
    "R06": ("D06", "14:38", [30, 0, 0, 0]), "R07": ("D07B", "14:52", [30, 0, 0, 0]),
}  # fmt: skip
DATA_ALERTS = [
    ("baseline_stalled", "R08", "R08 · baseline stuck at 13 of 16",
     "baseline stuck at 13 of 16. 12 missed and 5 set aside in 30 days."),
    ("possible_other_speaker", "R05", "R05 · possible other speaker",
     "2 check-ins held back as possible other voice (Oct 8, Oct 22)."),
    ("high_set_aside", "R03", "R03 · many check-ins set aside",
     "7 of 29 received check-ins set aside (noise, quality flag, too short)."),
    ("device_silent", "D02", "D02 · device silent all day",
     "silent all day Oct 12. Affected R02 and R03."),
]  # fmt: skip
# TRD 14 §4.9.2 per-day used/set aside/held back/missed, days 1..30
PER_DAY = ("10/0/0/0 9/0/0/1 9/1/0/0 8/0/0/2 9/1/0/0 9/0/0/1 9/1/0/0 8/0/1/1 8/1/0/1 8/1/0/1 "
           "9/0/0/1 8/0/0/2 9/0/0/1 9/1/0/0 9/0/0/1 10/0/0/0 8/0/0/2 9/1/0/0 9/0/0/1 9/1/0/0 "
           "9/0/0/1 8/1/1/0 9/0/0/1 9/0/0/1 9/1/0/0 9/1/0/0 9/0/0/1 10/0/0/0 9/1/0/0 "
           "10/0/0/0").split()  # fmt: skip


def _built() -> Iterator[TierB]:
    with ds07() as harness:
        harness.client.event_hooks["response"] = [check_response]  # TST-061
        yield harness


@pytest.fixture(scope="module")
def ui() -> Iterator[TierB]:
    yield from _built()


@pytest.mark.req("TDV-061", "API-069", "FEAT-060-FR-01")
def test_as_of_without_clock_override(ui: TierB) -> None:
    assert ui.run["as_of"] == AS_OF
    for path in ("/residents", "/residents/R09", "/devices", "/data-alerts"):
        meta = ui.get(path)["meta"]
        assert (meta["as_of"], meta["data_source_label"]) == (AS_OF, "pipeline test data v0.1")


@pytest.mark.req("TDV-062", "TDV-063", "TDV-064", "TDV-065", "FR-137", "FR-302", "AC-FR-04",
                 "OAS-021", "D-109", "D-114", "FEAT-060-FR-02", "FEAT-060-FR-04",
                 "FEAT-060-AC-01")  # fmt: skip
def test_resident_list(ui: TierB) -> None:
    body = ui.get("/residents")
    assert body["summary"] == {"changed": 2, "needs_attention": 2, "learning": 0, "usual": 6}
    assert body["window"] == {"from": "2026-10-01", "to": "2026-10-30", "days": 30}
    assert [r["resident_code"] for r in body["items"]] == DEFAULT_ORDER
    for row in body["items"]:
        code = row["resident_code"]
        device, local, counts = ROWS[code]
        assert row["device_code"] == device, code
        assert row["last_checkin_local"].startswith(f"2026-10-30T{local}:"), code
        assert list(row["last_30_days"].values()) == counts, code
        assert row["needs_attention"] == (code in ("R03", "R08")), code
        assert row["alarm_reviewed"] == (False if code in ("R09", "R10") else None), code
    attention = {r["resident_code"]: r["attention_reasons"] for r in body["items"]
                 if r["needs_attention"]}  # fmt: skip
    assert attention == {"R03": ["high_set_aside"], "R08": ["baseline_stalled"]}
    r07 = next(r for r in body["items"] if r["resident_code"] == "R07")
    assert (r07["restart_cause"], r07["previous_device_code"]) == ("device", "D07")
    assert sum(r["last_30_days"]["missed"] for r in body["items"]) == 19


@pytest.mark.req("TDV-063", "FEAT-060-FR-03")
def test_resident_list_sorts(ui: TierB) -> None:
    by_code = [r["resident_code"] for r in ui.get("/residents", sort="resident_id")["items"]]
    assert by_code == [f"R{n:02d}" for n in range(1, 11)]
    by_last = [r["resident_code"] for r in ui.get("/residents", sort="last_checkin")["items"]]
    assert by_last == ["R02", "R07", "R05", "R10", "R06", "R08", "R09", "R03", "R04", "R01"]


@pytest.mark.req("TDV-066", "API-086", "D-114", "FEAT-060-FR-05", "FEAT-060-AC-06")
def test_devices(ui: TierB) -> None:
    body = ui.get("/devices")
    assert body["total"] == 10
    devices = {d["device_code"]: d for d in body["items"]}
    d02, d07, d07b = devices["D02"], devices["D07"], devices["D07B"]
    assert (d02["shared"], d02["resident_codes"]) == (True, ["R02", "R03"])
    assert d02["last_upload_at"] == "2026-10-30T19:55:23Z"
    assert d02["silent_days_last_30"] == d02["device_gap_days_last_30"] == ["2026-10-12"]
    assert (d07["active"], d07["in_use_until"], d07["replaced_by_device_code"]) == (
        False, "2026-10-12", "D07B")  # fmt: skip
    assert (d07b["in_use_since"], d07b["replaces_device_code"]) == ("2026-10-13", "D07")
    assert {d["firmware_version"] for d in devices.values()} == {"fw-1.0.0"}
    assert {c for c, d in devices.items() if d["uploaded_on_as_of_date"]} == set(devices) - {"D07"}


@pytest.mark.req("TDV-066", "D-113", "D-114", "FEAT-060-FR-06", "FEAT-060-AC-06")
def test_resident_chart_r09(ui: TierB) -> None:
    r09 = ui.get("/residents/R09")
    assert (r09["status"], r09["alarm_since"], r09["watching_since"]) == (
        "alarm_on", "2026-10-21", "2026-10-17")  # fmt: skip
    assert (r09["needs_attention"], r09["alarm_reviewed"]) == (False, False)
    baseline = r09["baseline"]
    assert (baseline["frozen_after_session_id"], baseline["first_local_date"],
            baseline["frozen_after_local_date"]) == ("R09-20261016-01", "2026-10-01",
                                                     "2026-10-16")  # fmt: skip
    assert r09["window"] == {"from": "2026-10-01", "to": "2026-10-30", "days": 30}
    events = ui.get("/residents/R09/checkins")["items"]
    assert [(e["event_type"], e["local_date"], e["detail"]) for e in events] == [
        ("alarm_on", "2026-10-21", "tally crossed 5.0"),
        ("watching_started", "2026-10-17", None),
        ("baseline_complete", "2026-10-16", "16 of 16"),
        ("checkins_started", "2026-10-01", None),
    ]  # fmt: skip
    assert events[-1]["device_code"] == "D09"
    for code in DEFAULT_ORDER:  # every log ends with checkins_started on Oct 1
        last = ui.items(f"/residents/{code}/checkins")[-1]
        assert (last["event_type"], last["local_date"]) == ("checkins_started", "2026-10-01")
        assert last["device_code"] == ("D07" if code == "R07" else ROWS[code][0])


@pytest.mark.req("TDV-067", "TDV-069", "FR-263", "OAS-027", "FEAT-060-FR-07", "FEAT-060-FR-09",
                 "FEAT-060-AC-02")  # fmt: skip
def test_open_alarms_and_leaning_most(ui: TierB) -> None:
    body = ui.get("/alerts", status="open")
    assert body["total"] == 2
    alarms = {a["resident_code"]: a for a in body["items"]}
    expected = {"R09": ("R09-20261021-01", "2026-10-21", 9, 26.830256,
                        ["number_of_pauses", "loudness_dbfs", "voiced_fraction"]),
                "R10": ("R10-20261024-01", "2026-10-24", 6, 13.418183,
                        ["number_of_pauses", "articulation_rate_syl_per_s",
                         "speech_rate_syl_per_s"])}  # fmt: skip
    for code, (session, local, days, tally, leaning) in expected.items():
        alarm = alarms[code]
        assert (alarm["session_id"], alarm["local_date"], alarm["open_days"]) == (
            session, local, days)  # fmt: skip
        assert abs(alarm["current_tally"] - tally) <= 1e-6
        assert (alarm["status"], alarm["reviewed"], alarm["leaning_most"]) == (
            "open", False, leaning)  # fmt: skip


@pytest.mark.req("TDV-068", "FR-301", "AC-FR-12", "FEAT-060-FR-08", "FEAT-060-AC-03")
def test_exactly_four_data_alerts(ui: TierB) -> None:
    items = ui.items("/data-alerts", status="open")
    assert [(a["kind"], a["resident_code"] or a["device_code"], a["title"], a["detail"])
            for a in items] == DATA_ALERTS  # fmt: skip
    subjects = {(a["kind"], a["resident_code"] or a["device_code"]) for a in items}
    for absent in (("high_set_aside", "R08"), ("device_silent", "D08"),
                   ("device_silent", "D07"), ("baseline_stalled", "R07")):  # fmt: skip
        assert absent not in subjects


def _percent_rows(analytics: dict[str, Any]) -> list[tuple[str, int]]:
    return [(b["resident_code"], b["used_percent"]) for b in analytics["by_resident"]]


@pytest.mark.req("TDV-074", "FR-323", "AC-FR-13", "OAS-028", "FR-310", "FEAT-060-FR-10",
                 "FEAT-060-AC-04")  # fmt: skip
def test_study_team_analytics(ui: TierB) -> None:
    body = ui.get("/analytics", role="researcher")
    kpis = body["kpis"]
    assert [kpis["checkins_received"][k] for k in ("count", "expected", "percent")] == [
        281,
        300,
        94,
    ]
    assert [kpis["used_for_scoring"][k] for k in ("count", "expected", "percent")] == [267, 300, 89]
    assert kpis["baselines_formed"] == {
        "formed": 9, "residents": 10, "forming_resident_codes": ["R08"],
        "restarts": [{"resident_code": "R07", "restart_count": 1}]}  # fmt: skip
    assert kpis["alarms_raised"] == {"count": 2, "resident_codes": ["R09", "R10"],
                                     "not_reviewed_count": 2}  # fmt: skip
    funnel = body["funnel"]
    assert [funnel[k] for k in ("expected", "received", "passed_quality", "used")] == [
        300,
        281,
        269,
        267,
    ]
    assert funnel["set_aside_reasons"] == {"quality_flag_poor": 5, "noise_above_limit": 5,
                                           "speech_too_short": 3}  # fmt: skip
    assert (funnel["missed"], funnel["duplicates_removed"], funnel["quarantined"],
            funnel["set_aside_multi_reason"]) == (19, 2, 2, 1)  # fmt: skip
    assert _percent_rows(body) == [("R08", 43), ("R03", 73), ("R02", 80), ("R05", 93),
                                   ("R01", 100), ("R04", 100), ("R06", 100), ("R07", 100),
                                   ("R09", 100), ("R10", 100)]  # fmt: skip
    days = [f"{d['used']}/{d['set_aside']}/{d['quarantined']}/{d['missed']}"
            for d in body["daily_series"]]  # fmt: skip
    assert days == PER_DAY
    assert body["daily_series"][11]["silent_device_codes"] == ["D02"]
    timing = {t["resident_code"]: t for t in body["alarm_timing"]}
    assert [timing["R09"][k] for k in ("planted_change", "change_began", "alarm_rang",
                                       "delay_days")] == ["Sudden step", "2026-10-21",
                                                          "2026-10-21", 0]  # fmt: skip
    assert [timing["R10"][k] for k in ("planted_change", "change_began", "alarm_rang",
                                       "delay_days")] == ["Slow drift", "2026-10-17",
                                                          "2026-10-24", 7]  # fmt: skip
    assert [c for c, t in timing.items() if t["result"] == "correct_no_alarm"] == [
        f"R{n:02d}" for n in range(1, 9)]  # fmt: skip
    denied = ui.client.get("/api/v1/analytics", headers=ui.headers("clinician"))
    assert denied.status_code == 403


@pytest.mark.req("NFR-128", "FR-302", "FEAT-060-FR-13")
def test_pages_agree_for_the_same_as_of(ui: TierB) -> None:
    rows = {r["resident_code"]: r["last_30_days"] for r in ui.get("/residents")["items"]}
    by_resident = {b["resident_code"]: b for b in ui.get("/analytics", role="researcher")[
        "by_resident"]}  # fmt: skip
    for code, counts in rows.items():
        b = by_resident[code]
        assert [b["used_days"], b["set_aside_days"], b["quarantined_days"], b["missed_days"]] == [
            counts["used"],
            counts["set_aside"],
            counts["quarantined"],
            counts["missed"],
        ], code
    details = {a["kind"]: a["detail"] for a in ui.items("/data-alerts", status="open")}
    assert "12 missed and 5 set aside" in details["baseline_stalled"]  # R08 13/5/0/12
    assert details["high_set_aside"].startswith(f"{rows['R03']['set_aside']} of 29")


@pytest.mark.req("TDV-076", "TST-056", "D-114", "FEAT-060-FR-12", "FEAT-060-AC-07")
def test_after_a_review_of_r09() -> None:
    for harness in _built():
        r09 = next(a for a in harness.get("/alerts", status="open")["items"]
                   if a["resident_code"] == "R09")  # fmt: skip
        saved = harness.client.post(
            f"/api/v1/alerts/{r09['id']}/reviews", headers=harness.headers("clinician"),
            json={"explanations": ["cold_cough_sore_throat"], "outcome": "known_cause",
                  "note": "Has a cold; nurse informed."},
        )  # fmt: skip
        assert saved.status_code == 201, saved.text
        open_alarms = harness.get("/alerts", status="open")
        assert open_alarms["total"] == 1
        assert open_alarms["items"][0]["resident_code"] == "R10"
        reviewed = next(a for a in harness.get("/alerts")["items"] if a["resident_code"] == "R09")
        assert (reviewed["status"], reviewed["reviewed"]) == ("acknowledged", True)
        assert abs(reviewed["current_tally"] - 26.830256) <= 1e-6
        kpis = harness.get("/analytics", role="researcher")["kpis"]
        assert kpis["alarms_raised"]["not_reviewed_count"] == 1
        residents = {r["resident_code"]: r for r in harness.get("/residents")["items"]}
        assert (residents["R09"]["status"], residents["R09"]["alarm_reviewed"]) == (
            "alarm_on", True)  # fmt: skip
        assert residents["R10"]["alarm_reviewed"] is False
        assert harness.get("/residents")["summary"] == {
            "changed": 2, "needs_attention": 2, "learning": 0, "usual": 6}  # fmt: skip
