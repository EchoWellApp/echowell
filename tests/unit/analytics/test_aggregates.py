"""Study team aggregates (TRD 07 §4.13; FEAT-051)."""

from __future__ import annotations

from datetime import date

import pytest

from analytics.aggregates import pct
from tests.unit.analytics.src05 import result

pytestmark = pytest.mark.unit


@pytest.mark.req("ANL-063", "FEAT-051-FR-05")
def test_pct_half_up_integer() -> None:
    assert (pct(281, 300), pct(267, 300), pct(1, 8), pct(1, 3), pct(0, 0)) == (94, 89, 13, 33, None)


@pytest.mark.req("ANL-061", "ANL-062", "AC-ANL-10", "FEAT-051-AC-01", "FEAT-051-FR-02",
                 "FEAT-051-FR-04", "FEAT-051-FR-06", "FEAT-051-FR-07")  # fmt: skip
def test_src05_kpis() -> None:
    a = result().analytics
    assert (a.period_start, a.period_end) == (date(2026, 10, 1), date(2026, 10, 30))
    assert a.kpis["checkins_received"] == {"value": 281, "expected": 300, "percent": 94}
    assert a.kpis["used_for_scoring"] == {"value": 267, "expected": 300, "percent": 89}
    b = a.kpis["baselines_formed"]
    assert (b["value"], b["total"], b["forming"], b["restarts"]) == (9, 10, ["R08"], {"R07": 1})
    assert b["note"] == "R08 still forming; R07 restarted once"
    assert a.kpis["alarms_raised"] == {"value": 2, "residents": ["R09", "R10"]}


@pytest.mark.req("FEAT-051-AC-02", "FEAT-051-FR-08")
def test_src05_daily_series() -> None:
    series = result().analytics.daily_series
    assert len(series) == 30
    oct12 = series[11]
    assert (oct12["used"], oct12["missed"], oct12["silent_device_codes"]) == (8, 2, ["D02"])
    assert sum(d["used"] + d["set_aside"] + d["quarantined"] + d["missed"] for d in series) == 300


@pytest.mark.req("FEAT-051-AC-03", "FEAT-051-FR-09", "UX-363", "UX-364", "UX-365", "UX-366")
def test_src05_funnel() -> None:
    funnel = result().analytics.funnel
    assert [(f["step"], f["value"], f["note"]) for f in funnel] == [
        ("expected", 300, "10 residents × 30 days"),  # noqa: RUF001
        ("received", 281, "19 missed; 2 duplicate copies removed"),
        ("passed_quality", 269,
         "12 set aside: quality flag 5, noise 5, too short 3 (1 had two reasons)"),
        ("used", 267, "2 held back as possible other voice"),
    ]  # fmt: skip
    assert funnel[2]["set_aside_reasons"] == {"quality_flag_poor": 5, "noise_above_limit": 5,
                                              "speech_too_short": 3}  # fmt: skip


@pytest.mark.req("FEAT-051-AC-04", "FEAT-051-FR-10", "UX-369")
def test_src05_by_resident() -> None:
    rows = result().analytics.by_resident
    assert [(r["resident_code"], r["used_percent"]) for r in rows] == [
        ("R08", 43), ("R03", 73), ("R02", 80), ("R05", 93), ("R01", 100), ("R04", 100),
        ("R06", 100), ("R07", 100), ("R09", 100), ("R10", 100),
    ]  # fmt: skip
