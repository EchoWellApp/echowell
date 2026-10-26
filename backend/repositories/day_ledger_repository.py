"""Day ledger (TRD 23 §4.2.13; TRD 06 DB-023; FEAT-011).

One row per resident per local day (`day_ledger_resident_date_uq`); missed days are never filled
from other days (BR-06).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.models import DayLedgerEntry, DayStatus


class DayLedgerRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def insert_many(self, rows: Iterable[DayLedgerEntry]) -> list[DayLedgerEntry]:
        items = list(rows)
        self.session.add_all(items)
        self.session.flush()
        return items

    def delete_for_resident(self, resident_id: uuid.UUID) -> int:
        result = self.session.execute(
            delete(DayLedgerEntry).where(DayLedgerEntry.resident_id == resident_id)
        )
        return int(result.rowcount or 0)

    def for_resident(
        self, resident_id: uuid.UUID, start: date | None = None, end: date | None = None
    ) -> list[DayLedgerEntry]:
        query = select(DayLedgerEntry).where(DayLedgerEntry.resident_id == resident_id)
        if start is not None:
            query = query.where(DayLedgerEntry.local_date >= start)
        if end is not None:
            query = query.where(DayLedgerEntry.local_date <= end)
        return list(self.session.scalars(query.order_by(DayLedgerEntry.local_date)).all())

    def missing_days(self, resident_id: uuid.UUID, start: date, end: date) -> list[DayLedgerEntry]:
        """Missed days (`missing_resident` or `missing_device_gap`) in the window (DB-041)."""
        return list(
            self.session.scalars(
                select(DayLedgerEntry)
                .where(
                    DayLedgerEntry.resident_id == resident_id,
                    DayLedgerEntry.status != DayStatus.CHECKED_IN,
                    DayLedgerEntry.local_date.between(start, end),
                )
                .order_by(DayLedgerEntry.local_date)
            ).all()
        )
