"""Raw sessions: the immutable raw store (TRD 06 DB-001..DB-004; TRD 20 §4.6.9; FEAT-010).

Insert-only by design: this class has no update or delete method, and the database blocks UPDATE,
DELETE and TRUNCATE twice (trigger `reject_mutation()` and the `echowell_app` grants, DB-004).
`arrival_seq` is assigned by its sequence and never supplied (TRD 20 §8); duplicate detection
orders by it (AGT-043).
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import exists, func, insert, select
from sqlalchemy.orm import Session

from backend.models import RawSession

# The typed columns copied from the payload (TRD 10 schema v0.1 fields and the 19 features).
_PROTECTED = frozenset({"id", "arrival_seq", "received_at"})


class RawSessionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def insert(self, values: Mapping[str, Any]) -> tuple[uuid.UUID, int]:
        """Insert one arrival (duplicates included, DB-001) and return `(id, arrival_seq)`."""
        given = _PROTECTED.intersection(values)
        if given:
            raise ValueError(f"{sorted(given)} are assigned by the database")
        row = self.session.execute(
            insert(RawSession).values(**values).returning(RawSession.id, RawSession.arrival_seq)
        ).one()
        return row.id, row.arrival_seq

    def by_resident(self, resident_id: uuid.UUID) -> list[RawSession]:
        """The resident's arrivals in `arrival_seq` order (pipeline input, FEAT-053)."""
        return list(
            self.session.scalars(
                select(RawSession)
                .where(RawSession.resident_id == resident_id)
                .order_by(RawSession.arrival_seq)
            ).all()
        )

    def by_session_id(self, session_id: str) -> list[RawSession]:
        return list(
            self.session.scalars(
                select(RawSession)
                .where(RawSession.session_id == session_id)
                .order_by(RawSession.arrival_seq)
            ).all()
        )

    def exists_session_id(self, session_id: str) -> bool:
        return bool(
            self.session.scalar(select(exists().where(RawSession.session_id == session_id)))
        )

    def first_payload(self, session_id: str) -> Any | None:
        """`payload` of the first arrival of a `session_id` (ING-037), else None."""
        return self.session.scalar(
            select(RawSession.payload)
            .where(RawSession.session_id == session_id)
            .order_by(RawSession.arrival_seq)
            .limit(1)
        )

    def latest_timestamp_for_device(self, device_id: uuid.UUID) -> datetime | None:
        return self.session.scalar(
            select(func.max(RawSession.timestamp_utc)).where(RawSession.device_id == device_id)
        )
