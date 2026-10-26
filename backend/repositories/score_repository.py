"""Scores and CUSUM state (TRD 23 §4.2.15, §4.2.16; TRD 06 DB-014, DB-043; FEAT-011).

`scores.z` is validated before insert (PGS-032). Scores are deleted with their processed session
(`ON DELETE CASCADE`) or per resident before a recomputation (DB-014).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.models import CusumState, Score
from backend.schemas.json_columns import score_z_json


class ScoreRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def insert_many(self, rows: Iterable[Score]) -> list[Score]:
        items = list(rows)
        for row in items:
            row.z = score_z_json(row.z)
        self.session.add_all(items)
        self.session.flush()
        return items

    def delete_for_resident(self, resident_id: uuid.UUID) -> int:
        result = self.session.execute(delete(Score).where(Score.resident_id == resident_id))
        return int(result.rowcount or 0)

    def series(self, epoch_id: uuid.UUID) -> list[Score]:
        """The epoch's scores in `local_date` order (DB-043; index scores_epoch_date_idx)."""
        return list(
            self.session.scalars(
                select(Score).where(Score.epoch_id == epoch_id).order_by(Score.local_date)
            ).all()
        )

    def first_for_epoch(self, epoch_id: uuid.UUID) -> Score | None:
        return self.session.scalars(
            select(Score).where(Score.epoch_id == epoch_id).order_by(Score.local_date).limit(1)
        ).first()

    def cusum_state(self, epoch_id: uuid.UUID) -> CusumState | None:
        return self.session.get(CusumState, epoch_id)

    def upsert_cusum_state(self, state: CusumState) -> CusumState:
        merged = self.session.merge(state)
        self.session.flush()
        return merged

    def delete_cusum_for_resident(self, resident_id: uuid.UUID) -> int:
        result = self.session.execute(
            delete(CusumState).where(CusumState.resident_id == resident_id)
        )
        return int(result.rowcount or 0)
