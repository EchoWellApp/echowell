"""Epoch numbering (TRD 08 §4.3; FEAT-042)."""

from __future__ import annotations

import pytest

from analytics.config import TEST_V0_1
from analytics.duplicate_detection import mark_duplicates
from analytics.epoch_detection import assign_epochs
from analytics.quality_screening import apply_quality_gate
from tests.unit.analytics.factory import rec

pytestmark = pytest.mark.unit


def _epochs(records: list, late_seqs: tuple[int, ...] = ()) -> list[int | None]:  # type: ignore[type-arg]
    rows = apply_quality_gate(mark_duplicates(records), TEST_V0_1)
    late = [r for r in rows if r.record.arrival_seq in late_seqs]
    return [
        r.epoch_number
        for r in sorted(assign_epochs(rows, late), key=lambda r: r.record.arrival_seq)
    ]


def _day(n: int) -> str:
    return f"2026-10-{n:02d} 19:00:00"


@pytest.mark.req("EP-01", "FEAT-042-AC-01")
def test_same_key_one_epoch() -> None:
    assert _epochs([rec(i, _day(i)) for i in range(1, 4)]) == [1, 1, 1]


@pytest.mark.req("EP-02", "EP-03", "EP-04", "BSC-007", "FEAT-042-AC-02", "FEAT-042-FR-02")
def test_device_firmware_and_software_changes() -> None:
    assert _epochs([rec(1, _day(1)), rec(2, _day(2), device="D07B")]) == [1, 2]
    assert _epochs([rec(1, _day(1)), rec(2, _day(2), firmware="fw-1.0.1")]) == [1, 2]
    assert _epochs([rec(1, _day(1)), rec(2, _day(2), software="openSMILE 3.0.3")]) == [1, 2]


@pytest.mark.req("EP-05", "BSC-006", "FEAT-042-AC-03")
def test_set_aside_record_starts_an_epoch() -> None:
    assert _epochs([rec(1, _day(1)), rec(2, _day(2), device="D9", flag="poor"),
                    rec(3, _day(3), device="D9")]) == [1, 2, 2]  # fmt: skip


@pytest.mark.req("EP-06", "EP-07", "BSC-009", "FEAT-042-AC-04", "FEAT-042-FR-04")
def test_time_order_and_duplicates() -> None:
    records = [rec(1, _day(3), device="B"), rec(2, _day(1)), rec(3, _day(2)),
               rec(4, _day(1), device="X", session="R01-20261001-01")]  # fmt: skip
    assert _epochs(records) == [2, 1, 1, None]


@pytest.mark.req("BSC-007", "FEAT-042-AC-05")
def test_returning_key_gets_a_new_epoch() -> None:
    assert _epochs([rec(1, _day(1)), rec(2, _day(2), device="B"), rec(3, _day(3))]) == [1, 2, 3]


@pytest.mark.req("FEAT-042-FR-05", "ANL-025")
def test_late_record_takes_the_previous_epoch() -> None:
    records = [rec(1, _day(1)), rec(2, _day(3), device="B"), rec(3, _day(2), device="C")]
    assert _epochs(records, late_seqs=(3,)) == [1, 2, 1]
    assert _epochs([rec(1, _day(2)), rec(2, _day(1), device="Z")], late_seqs=(2,)) == [1, None]


@pytest.mark.req("VC-R07", "BSC-008", "AC-BSC-05", "FEAT-042-AC-06", "FEAT-042-FR-06")
def test_src05_r07_epochs() -> None:
    from tests.unit.analytics.src05 import result

    epochs = {(e.resident_code, e.epoch_number): e for e in result().epochs}
    assert sorted(k for k in epochs if k[0] == "R07") == [("R07", 1), ("R07", 2)]
    assert len(epochs) == 11
    e1, e2 = epochs[("R07", 1)], epochs[("R07", 2)]
    assert (e1.device_code, e2.device_code) == ("D07", "D07B")
    assert e1.ended_at == e2.started_at
    assert e2.ended_at is None
    first2 = min((s for s in result().sessions if s.record.resident_code == "R07"
                  and s.epoch_number == 2), key=lambda s: s.record.timestamp_utc)  # fmt: skip
    assert first2.record.session_id == "R07-20261013-01"
    assert sum(1 for s in result().sessions if s.record.resident_code == "R07"
               and s.epoch_number == 1) == 12  # fmt: skip
