"""Epoch numbering per resident (TRD 08 §4.3 BSC-006..BSC-010; FEAT-042).

Per resident, the non-duplicate, non-late records in time order `(timestamp_utc, arrival_seq)`
form epochs: a record whose (device, firmware, software) key differs from the previous record's
starts the next epoch, and numbers are never reused (BSC-007). A late record takes the epoch of
the last non-late record at or before it and never starts or splits one (TRD 08 §4.3).

The returned rows carry the UTC instant as `local_datetime` and its date as `local_date`; the
speaker screen, which receives the configuration, replaces them with facility-local values.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from datetime import datetime
from typing import Protocol

from analytics.config import EpochedRecord, RawRecord, ScreenedRecord


class HasRecord(Protocol):
    @property
    def record(self) -> RawRecord: ...


def time_key(row: HasRecord) -> tuple[datetime, int]:
    """Time order: `(timestamp_utc, arrival_seq)` (TRD 08 §4.1, ANL-021)."""
    return (row.record.timestamp_utc, row.record.arrival_seq)


def assign_epochs(
    rows: Sequence[ScreenedRecord], late: Collection[ScreenedRecord] = ()
) -> list[EpochedRecord]:
    late_ids = {row.record.raw_session_id for row in late}
    epoch_of: dict[str, int | None] = {}
    residents = sorted({row.record.resident_code for row in rows})
    for resident in residents:
        mine = sorted(
            (r for r in rows if r.record.resident_code == resident and r.status != "duplicate"),
            key=time_key,
        )
        key_prev: tuple[str, str, str] | None = None
        number = 0
        current: int | None = None
        for row in mine:
            if row.record.raw_session_id in late_ids:
                epoch_of[row.record.raw_session_id] = current
                continue
            if row.record.epoch_key != key_prev:
                number += 1
                key_prev = row.record.epoch_key
            current = number
            epoch_of[row.record.raw_session_id] = number
    return [
        EpochedRecord(
            record=row.record, status=row.status, reasons=row.reasons,
            reason_text=row.reason_text,
            epoch_number=epoch_of.get(row.record.raw_session_id),
            screen_detail=None, late_arrival=row.record.raw_session_id in late_ids,
            local_datetime=row.record.timestamp_utc, local_date=row.record.timestamp_utc.date(),
        )
        for row in rows
    ]  # fmt: skip
