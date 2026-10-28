"""Processed sessions (TRD 23 §4.2.12, §4.3.1; TRD 06 DB-014; FEAT-011).

Rebuildable derived rows keyed by `raw_session_id`. JSON values are validated before insert
(PGS-033). Only the persisted statuses `usable`, `set_aside`, `quarantined` and `duplicate` exist
in the database (DME-006).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.models import ProcessedSession, SessionStatus
from backend.schemas.json_columns import adjusted_features_json


class ProcessedSessionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def insert_many(self, rows: Iterable[ProcessedSession]) -> list[ProcessedSession]:
        """Insert computed rows after validating `adjusted_features` (FEAT-011-FR-12)."""
        items = list(rows)
        for row in items:
            if row.status != SessionStatus.DUPLICATE:
                row.adjusted_features = adjusted_features_json(row.adjusted_features)
        self.session.add_all(items)
        self.session.flush()
        return items

    def delete_for_resident(self, resident_id: uuid.UUID) -> int:
        """Remove a resident's rows before re-inserting them; their scores cascade (PGS-010)."""
        result = self.session.execute(
            delete(ProcessedSession).where(ProcessedSession.resident_id == resident_id)
        )
        return int(result.rowcount or 0)

    def by_resident(self, resident_id: uuid.UUID) -> list[ProcessedSession]:
        return list(
            self.session.scalars(
                select(ProcessedSession)
                .where(ProcessedSession.resident_id == resident_id)
                .order_by(ProcessedSession.timestamp_utc)
            ).all()
        )

    def by_epoch(self, epoch_id: uuid.UUID) -> list[ProcessedSession]:
        return list(
            self.session.scalars(
                select(ProcessedSession)
                .where(ProcessedSession.epoch_id == epoch_id)
                .order_by(ProcessedSession.timestamp_utc)
            ).all()
        )

    def by_raw_session(self, raw_session_id: uuid.UUID) -> ProcessedSession | None:
        return self.session.scalars(
            select(ProcessedSession).where(ProcessedSession.raw_session_id == raw_session_id)
        ).first()

    def by_session_id(self, session_id: str) -> list[ProcessedSession]:
        return list(
            self.session.scalars(
                select(ProcessedSession).where(ProcessedSession.session_id == session_id)
            ).all()
        )
