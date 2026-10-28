"""Epochs (TRD 23 §4.2.11, §4.3.5; TRD 06 DB-015; FEAT-011).

Natural key `(resident_id, epoch_number)`; at most one current epoch (`ended_at IS NULL`) per
resident (`epochs_current_uq`, PGS-030). The per-resident upsert and delete logic of a pipeline run
is FEAT-053; this module offers the keyed reads and the primitives it needs.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.models import Epoch


class EpochRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def current(self, resident_id: uuid.UUID) -> Epoch | None:
        return self.session.scalars(
            select(Epoch).where(Epoch.resident_id == resident_id, Epoch.ended_at.is_(None))
        ).first()

    def current_for_residents(self, resident_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, Epoch]:
        ids = list(resident_ids)
        rows = self.session.scalars(
            select(Epoch).where(Epoch.resident_id.in_(ids), Epoch.ended_at.is_(None))
        ).all()
        return {row.resident_id: row for row in rows}

    def by_resident(self, resident_id: uuid.UUID) -> list[Epoch]:
        return list(
            self.session.scalars(
                select(Epoch).where(Epoch.resident_id == resident_id).order_by(Epoch.epoch_number)
            ).all()
        )

    def get_by_number(self, resident_id: uuid.UUID, epoch_number: int) -> Epoch | None:
        return self.session.scalars(
            select(Epoch).where(
                Epoch.resident_id == resident_id, Epoch.epoch_number == epoch_number
            )
        ).first()

    def add(self, epoch: Epoch) -> Epoch:
        self.session.add(epoch)
        self.session.flush()
        return epoch

    def delete_ids(self, epoch_ids: Iterable[uuid.UUID]) -> int:
        """Delete epochs without a frozen baseline that a rebuild no longer produces (DB-015)."""
        ids = list(epoch_ids)
        if not ids:
            return 0
        result = self.session.execute(delete(Epoch).where(Epoch.id.in_(ids)))
        return int(result.rowcount or 0)
