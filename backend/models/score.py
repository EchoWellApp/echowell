"""ORM models Score and CusumState (TRD 23 §4.6; FEAT-011)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import (
    ALARM_STATE,
    COMPOSITE_Z_KEYS,
    AlarmState,
    Base,
    sql_list,
)

if TYPE_CHECKING:
    from backend.models.session import ProcessedSession


class Score(Base):
    """`scores` (TRD 20 §4.6.15; TRD 23 §4.2.15; FEAT-011)."""

    __tablename__ = "scores"
    __table_args__ = (
        UniqueConstraint("processed_session_id", name="scores_processed_session_uq"),
        CheckConstraint(
            f"jsonb_typeof(z) = 'object' AND z ?& ARRAY[{sql_list(COMPOSITE_Z_KEYS)}]",
            name="scores_z_ck",
        ),
        CheckConstraint(
            "cusum_tally >= 0",
            name="scores_cusum_ck",
        ),
        Index("scores_resident_date_idx", "resident_id", "local_date"),
        Index("scores_epoch_date_idx", "epoch_id", "local_date"),
        Index("scores_run_idx", "pipeline_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    processed_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("processed_sessions.id", ondelete="CASCADE"), nullable=False
    )
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id", ondelete="RESTRICT"), nullable=False
    )
    epoch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("epochs.id", ondelete="RESTRICT"), nullable=False
    )
    local_date: Mapped[date] = mapped_column(Date(), nullable=False)
    is_morning: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    z: Mapped[Any] = mapped_column(JSONB(), nullable=False)
    composite_raw: Mapped[float] = mapped_column(Double(), nullable=False)
    composite_z: Mapped[float] = mapped_column(Double(), nullable=False)
    cusum_tally: Mapped[float] = mapped_column(Double(), nullable=False)
    alarm_state: Mapped[AlarmState] = mapped_column(ALARM_STATE, nullable=False)
    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    processed_session: Mapped[ProcessedSession] = relationship(back_populates="score")


class CusumState(Base):
    """`cusum_state` (TRD 20 §4.6.16; TRD 23 §4.2.16; FEAT-011)."""

    __tablename__ = "cusum_state"
    __table_args__ = (
        CheckConstraint(
            "current_tally >= 0",
            name="cusum_state_tally_ck",
        ),
        CheckConstraint(
            "last_scored_session_id IS NOT NULL OR (current_tally = 0 AND NOT alarm_on)",
            name="cusum_state_scored_ck",
        ),
        Index("cusum_state_resident_idx", "resident_id"),
        Index("cusum_state_run_idx", "pipeline_run_id"),
    )

    epoch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("epochs.id", ondelete="RESTRICT"), primary_key=True
    )
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id", ondelete="RESTRICT"), nullable=False
    )
    current_tally: Mapped[float] = mapped_column(Double(), server_default=text("0"), nullable=False)
    last_scored_session_id: Mapped[str | None] = mapped_column(Text(), nullable=True)
    alarm_on: Mapped[bool] = mapped_column(Boolean(), server_default=text("false"), nullable=False)
    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="RESTRICT"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
