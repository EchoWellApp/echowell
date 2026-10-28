"""ORM model Baseline (TRD 23 §4.6; FEAT-011). The app may only insert frozen baselines (DB-016)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import (
    FEATURE_KEYS,
    Base,
    sql_list,
)


class Baseline(Base):
    """`baselines` (TRD 20 §4.6.14; TRD 23 §4.2.14; FEAT-011)."""

    __tablename__ = "baselines"
    __table_args__ = (
        UniqueConstraint("epoch_id", "feature_key", name="baselines_epoch_feature_uq"),
        CheckConstraint(
            f"feature_key IN ({sql_list((*FEATURE_KEYS, 'composite'))})",
            name="baselines_feature_key_ck",
        ),
        CheckConstraint(
            "n_sessions >= 1",
            name="baselines_n_sessions_ck",
        ),
        CheckConstraint(
            "mad >= 0 AND robust_spread >= 0",
            name="baselines_spread_ck",
        ),
        Index("baselines_resident_idx", "resident_id"),
        Index("baselines_run_idx", "pipeline_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id", ondelete="RESTRICT"), nullable=False
    )
    epoch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("epochs.id", ondelete="RESTRICT"), nullable=False
    )
    feature_key: Mapped[str] = mapped_column(Text(), nullable=False)
    n_sessions: Mapped[int] = mapped_column(Integer(), nullable=False)
    first_session_id: Mapped[str] = mapped_column(Text(), nullable=False)
    frozen_after_session_id: Mapped[str] = mapped_column(Text(), nullable=False)
    median: Mapped[float] = mapped_column(Double(), nullable=False)
    mad: Mapped[float] = mapped_column(Double(), nullable=False)
    robust_spread: Mapped[float] = mapped_column(Double(), nullable=False)
    floor_applied: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    frozen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
