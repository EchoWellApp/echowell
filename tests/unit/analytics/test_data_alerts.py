"""Data-quality alerts (TRD 09 §4.9; FEAT-050)."""

from __future__ import annotations

from datetime import date

import pytest

from analytics.data_alerts import _flagged, join_and, natural_key
from tests.unit.analytics.src05 import result

pytestmark = pytest.mark.unit


@pytest.mark.req("CUS-043", "CUS-044", "FEAT-050-AC-01", "FEAT-050-FR-09", "VC-G12")
def test_src05_exactly_four_alerts_in_order() -> None:
    got = [
        (a.kind, a.resident_code or a.device_code, a.title, a.detail) for a in result().data_alerts
    ]
    assert got == [
        ("baseline_stalled", "R08", "R08 · baseline stuck at 13 of 16",
         "baseline stuck at 13 of 16. 12 missed and 5 set aside in 30 days."),
        ("possible_other_speaker", "R05", "R05 · possible other speaker",
         "2 check-ins held back as possible other voice (Oct 8, Oct 22)."),
        ("high_set_aside", "R03", "R03 · many check-ins set aside",
         "7 of 29 received check-ins set aside (noise, quality flag, too short)."),
        ("device_silent", "D02", "D02 · device silent all day",
         "silent all day Oct 12. Affected R02 and R03."),
    ]  # fmt: skip
    assert result().data_alerts[3].days == (date(2026, 10, 12),)


@pytest.mark.req("FEAT-050-FR-05", "FEAT-050-AC-02")
def test_single_resident_device_needs_a_run() -> None:
    d = [(date(2026, 10, n), ["R08"]) for n in (2, 4, 5, 9)]
    assert [x[0].day for x in _flagged(d, 2, 2)] == [4, 5]
    assert _flagged([(date(2026, 10, 3), ["R08"])], 2, 2) == []
    assert [x[0].day for x in _flagged([(date(2026, 10, 3), ["R02", "R03"])], 2, 2)] == [3]


@pytest.mark.req("FEAT-050-FR-05", "FEAT-050-FR-06")
def test_wording_helpers() -> None:
    assert join_and(["R08"]) == "R08"
    assert join_and(["R02", "R03"]) == "R02 and R03"
    assert join_and(["R01", "R02", "R03"]) == "R01, R02 and R03"
    assert sorted(["R10", "R2"], key=natural_key) == ["R2", "R10"]
