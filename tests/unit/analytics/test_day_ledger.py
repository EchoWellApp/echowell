"""Day ledger (TRD 10 §4.9-§4.10; FEAT-049)."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from analytics.config import TEST_V0_1, DeviceAssignment, ResidentInfo
from analytics.day_ledger import build_ledger, device_on
from analytics.duplicate_detection import mark_duplicates
from analytics.epoch_detection import assign_epochs
from analytics.quality_screening import apply_quality_gate
from analytics.speaker_screen import screen_speakers
from tests.unit.analytics.factory import rec
from tests.unit.analytics.src05 import result

pytestmark = pytest.mark.unit
CHICAGO = ZoneInfo("America/Chicago")


def _ledger(records, residents, assignments, as_of):  # type: ignore[no-untyped-def]
    rows = screen_speakers(assign_epochs(apply_quality_gate(mark_duplicates(records), TEST_V0_1)),
                           TEST_V0_1)  # fmt: skip
    return build_ledger(rows, residents, assignments, TEST_V0_1, as_of)


@pytest.mark.req("ING-045", "DL-01", "FEAT-049-AC-01", "FEAT-049-FR-01")
def test_device_resolution() -> None:
    a = [DeviceAssignment("R01", "D1", date(2026, 10, 1)),
         DeviceAssignment("R01", "D2", date(2026, 10, 5), date(2026, 10, 6))]  # fmt: skip
    assert device_on("R01", date(2026, 10, 4), a) == "D1"
    assert device_on("R01", date(2026, 10, 5), a) == "D2"
    assert device_on("R01", date(2026, 9, 30), a) is None


@pytest.mark.req(
    "ING-048", "ING-049", "ING-050", "ING-052", "DL-02", "DL-03", "DL-04", "DL-05",
    "FEAT-049-AC-02", "FEAT-049-FR-05", "FEAT-049-FR-06", "FEAT-049-FR-09",
)  # fmt: skip
def test_checked_in_gap_and_missed() -> None:
    oct1 = date(2026, 10, 1)
    residents = [
        ResidentInfo("R01", oct1), ResidentInfo("R02", oct1),
        ResidentInfo("R03", oct1, withdrawn_on=date(2026, 10, 2)),
    ]  # fmt: skip
    shared = [DeviceAssignment(r, "D1", date(2026, 10, 1)) for r in ("R01", "R02", "R03")]
    records = [
        rec(1, "2026-10-02 04:30:00", resident="R02", device="D1"),  # local Oct 1
        rec(2, "2026-10-02 19:00:00", resident="R01", device="D1", flag="poor"),
    ]
    as_of = datetime(2026, 10, 3, 12, tzinfo=CHICAGO)
    ledger = {(d.resident_code, d.local_date.day): d
              for d in _ledger(records, residents, shared, as_of)}  # fmt: skip
    assert ledger[("R02", 1)].status == "checked_in"
    assert ledger[("R01", 1)].status == "missing_resident"  # R02 had a record on the device
    assert ledger[("R01", 2)].status == "checked_in"  # a set-aside record counts
    assert (ledger[("R01", 3)].status, ledger[("R01", 3)].reason) == (
        "missing_device_gap", "all residents on shared device D1 have no record"
    )  # fmt: skip
    assert ("R03", 3) not in ledger  # withdrawn after Oct 2
    assert ledger[("R02", 3)].device_code == "D1"


@pytest.mark.req("FEAT-049-AC-03", "VC-G05", "TRD 10 §4.10")
def test_src05_ledger() -> None:
    ledger = result().ledger
    assert len(ledger) == 300
    assert Counter(d.status for d in ledger) == {
        "checked_in": 281, "missing_resident": 17, "missing_device_gap": 2,
    }  # fmt: skip
    gaps = sorted(
        (d.resident_code, d.local_date.day) for d in ledger if d.status == "missing_device_gap"
    )
    assert gaps == [("R02", 12), ("R03", 12)]
    r02 = sorted(d.local_date.day for d in ledger if d.resident_code == "R02"
                 and d.status == "missing_resident")  # fmt: skip
    assert r02 == [4, 9, 10, 17, 23]
    assert not any(d.resident_code == "R07" and d.status != "checked_in" for d in ledger)
