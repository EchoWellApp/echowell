"""Arrival-order duplicate marking (TRD 10 §4.7 ING-034..ING-039; FEAT-041).

The first arrival of a `session_id` (exact string) is kept; every later arrival is a duplicate,
whatever its values. Arrival order is `arrival_seq`, never the timestamp (ING-035).
"""

from __future__ import annotations

from collections.abc import Sequence

from analytics.config import RawRecord, ScreenedRecord

DUPLICATE_REASON = "session_id already received"


def mark_duplicates(records: Sequence[RawRecord]) -> list[ScreenedRecord]:
    seen: set[str] = set()
    out = []
    for record in sorted(records, key=lambda r: r.arrival_seq):
        if record.session_id in seen:
            out.append(ScreenedRecord(record, "duplicate", (DUPLICATE_REASON,), DUPLICATE_REASON))
            continue
        seen.add(record.session_id)
        out.append(ScreenedRecord(record, "pending_screen"))
    return out
