"""Frozen baselines (TRD 23 §4.2.14, §4.3.5; TRD 06 DB-016; DME-010; FEAT-011).

Insert-only for the application: a frozen baseline is never updated or deleted by `echowell_app`
(grants SELECT, INSERT; DB-016). Deleting baselines is reserved for the operator `rebuild` command
as `echowell_migrator` (TRD 07 ANL-032).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from enum import StrEnum

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import FEATURE_KEYS, Baseline, Epoch

# A frozen resident-epoch has one row per feature plus the composite row (PGS-031).
BASELINE_KEYS: tuple[str, ...] = (*FEATURE_KEYS, "composite")


class BaselineState(StrEnum):
    """Baseline state of a resident-epoch (DME-010); never returns from frozen to forming."""

    NOT_STARTED = "not_started"
    FORMING = "forming"
    FROZEN = "frozen"


class BaselineRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def insert_frozen(self, rows: Iterable[Baseline]) -> list[Baseline]:
        """Insert the 20 rows of one newly frozen epoch (19 features and `composite`)."""
        items = list(rows)
        epochs = {row.epoch_id for row in items}
        keys = sorted(row.feature_key for row in items)
        if len(epochs) != 1 or keys != sorted(BASELINE_KEYS):
            raise ValueError("a frozen baseline is exactly the 20 rows of one epoch")
        self.session.add_all(items)
        self.session.flush()
        return items

    def for_epoch(self, epoch_id: uuid.UUID) -> list[Baseline]:
        return list(
            self.session.scalars(
                select(Baseline).where(Baseline.epoch_id == epoch_id).order_by(Baseline.feature_key)
            ).all()
        )

    def composite(self, epoch_id: uuid.UUID) -> Baseline | None:
        return self.session.scalars(
            select(Baseline).where(
                Baseline.epoch_id == epoch_id, Baseline.feature_key == "composite"
            )
        ).first()

    def state(self, epoch: Epoch | None) -> BaselineState:
        """`not_started` without an epoch, `frozen` with its 20 rows, otherwise `forming`."""
        if epoch is None:
            return BaselineState.NOT_STARTED
        count = self.session.scalar(
            select(func.count()).select_from(Baseline).where(Baseline.epoch_id == epoch.id)
        )
        return BaselineState.FROZEN if count == len(BASELINE_KEYS) else BaselineState.FORMING

    def list_all(self, *, limit: int = 500, offset: int = 0) -> list[Baseline]:
        """All frozen baselines for the researcher export (`GET /analytics/baselines`)."""
        return list(
            self.session.scalars(
                select(Baseline)
                .order_by(Baseline.resident_id, Baseline.epoch_id, Baseline.feature_key)
                .limit(limit)
                .offset(offset)
            ).all()
        )
