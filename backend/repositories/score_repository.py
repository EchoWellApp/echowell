"""Scores and CUSUM state (TRD 23 §4.2.15, §4.2.16; TRD 06 DB-014, DB-043; FEAT-011).

`scores.z` is validated before insert (PGS-032). Scores are deleted with their processed session
(`ON DELETE CASCADE`) or per resident before a recomputation (DB-014).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import Select, delete, func, select
from sqlalchemy.orm import Session

from backend.models import CusumState, Epoch, ProcessedSession, Resident, Score
from backend.schemas.json_columns import score_z_json


@dataclass(frozen=True)
class ScoreFilter:
    resident_id: uuid.UUID | None = None
    epoch_number: int | None = None
    start: date | None = None
    end: date | None = None


@dataclass(frozen=True)
class ScoreReadRow:
    """One `ScoreRow` (TRD 19) with the ids of its resident-epoch."""

    session_id: str
    resident_code: str
    epoch_number: int
    local_date: date
    is_morning: bool
    z: dict[str, Any]
    composite_raw: float
    composite_z: float
    cusum_tally: float
    alarm_state: str
    epoch_id: uuid.UUID


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

    def _read_query(self, where: ScoreFilter) -> Select[Any]:
        query = (
            select(
                ProcessedSession.session_id, Resident.resident_code, Epoch.epoch_number,
                Score.local_date, Score.is_morning, Score.z, Score.composite_raw,
                Score.composite_z, Score.cusum_tally, Score.alarm_state, Score.epoch_id,
            )
            .join(ProcessedSession, ProcessedSession.id == Score.processed_session_id)
            .join(Resident, Resident.id == Score.resident_id)
            .join(Epoch, Epoch.id == Score.epoch_id)
        )  # fmt: skip
        if where.resident_id is not None:
            query = query.where(Score.resident_id == where.resident_id)
        if where.epoch_number is not None:
            query = query.where(Epoch.epoch_number == where.epoch_number)
        if where.start is not None:
            query = query.where(Score.local_date >= where.start)
        if where.end is not None:
            query = query.where(Score.local_date <= where.end)
        return query

    def count_rows(self, where: ScoreFilter) -> int:
        return int(
            self.session.scalar(
                select(func.count()).select_from(self._read_query(where).subquery())
            )
            or 0
        )

    def read_rows(
        self, where: ScoreFilter, *, limit: int | None = None, offset: int = 0
    ) -> list[ScoreReadRow]:
        """Score rows ordered by resident code, local date and session id (API-079)."""
        query = self._read_query(where).order_by(
            Resident.resident_code, Score.local_date, ProcessedSession.session_id
        )
        if limit is not None:
            query = query.limit(limit).offset(offset)
        return [
            ScoreReadRow(
                session_id=r[0], resident_code=r[1], epoch_number=r[2], local_date=r[3],
                is_morning=r[4], z=r[5], composite_raw=r[6], composite_z=r[7],
                cusum_tally=r[8], alarm_state=str(r[9]), epoch_id=r[10],
            )
            for r in self.session.execute(query).all()
        ]  # fmt: skip

    def epochs_in(self, where: ScoreFilter) -> list[uuid.UUID]:
        """The resident-epochs present in a filtered result (`baseline_periods`)."""
        sub = self._read_query(where).subquery()
        return list(self.session.scalars(select(sub.c.epoch_id).distinct()).all())
