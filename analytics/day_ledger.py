"""Resident-day ledger and missing-day classification (TRD 10 §4.9-§4.10 ING-044..ING-052;
FEAT-049).

One row per resident per facility-local day from `enrolled_on` to the as-of local date (or the
withdrawal date). A day with any non-duplicate record (any status, late arrivals included) is
checked in; otherwise it is a device gap when the resident's device is shared that day and no
sharer has a record, else a missed day. Missing days are never filled in (ING-051).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, timedelta

from analytics.config import (
    DeviceAssignment,
    EpochedRecord,
    LedgerDay,
    PipelineConfig,
    ResidentInfo,
)
from analytics.epoch_detection import time_key

MISSED = "no record received"


def device_on(resident: str, day: date, assignments: Sequence[DeviceAssignment]) -> str | None:
    """The covering assignment's device; the later `valid_from` wins (ING-045)."""
    covering = [a for a in assignments if a.resident_code == resident and a.covers(day)]
    if not covering:
        return None
    return max(covering, key=lambda a: (a.valid_from, a.device_code)).device_code


def enrolled_on_day(info: ResidentInfo, day: date) -> bool:
    return info.enrolled_on <= day and (info.withdrawn_on is None or day <= info.withdrawn_on)


def sharers(
    device: str,
    day: date,
    assignments: Sequence[DeviceAssignment],
    residents: dict[str, ResidentInfo],
) -> list[str]:
    """Enrolled residents with an assignment to `device` covering `day` (ING-046)."""
    return sorted({
        a.resident_code for a in assignments
        if a.device_code == device and a.covers(day) and a.resident_code in residents
        and enrolled_on_day(residents[a.resident_code], day)
    })  # fmt: skip


def last_day(info: ResidentInfo, as_of_date: date) -> date:
    return min(as_of_date, info.withdrawn_on) if info.withdrawn_on else as_of_date


def build_ledger(
    rows: Sequence[EpochedRecord],
    residents: Sequence[ResidentInfo],
    assignments: Sequence[DeviceAssignment],
    config: PipelineConfig,
    as_of: datetime,
) -> list[LedgerDay]:
    as_of_date = as_of.astimezone(config.tz).date()
    by_code = {r.resident_code: r for r in residents}
    first_record: dict[tuple[str, date], EpochedRecord] = {}
    for row in sorted(rows, key=time_key):
        if row.status == "duplicate" or row.record.timestamp_utc > as_of:
            continue
        first_record.setdefault((row.record.resident_code, row.local_date), row)
    out = []
    for info in sorted(residents, key=lambda r: r.resident_code):
        day = info.enrolled_on
        end = last_day(info, as_of_date)
        while day <= end:
            code = info.resident_code
            record = first_record.get((code, day))
            if record is not None:
                out.append(LedgerDay(code, day, "checked_in", record.record.device_code, ""))
            else:
                device = device_on(code, day, assignments)
                share = sharers(device, day, assignments, by_code) if device else []
                gap = (
                    device is not None and len(share) >= config.shared_device_min_residents
                    and not any((s, day) in first_record for s in share)
                )  # fmt: skip
                if gap:
                    reason = f"all residents on shared device {device} have no record"
                    out.append(LedgerDay(code, day, "missing_device_gap", device, reason))
                else:
                    out.append(LedgerDay(code, day, "missing_resident", device, MISSED))
            day += timedelta(days=1)
    return out
