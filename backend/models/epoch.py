"""ORM model Epoch (TRD 23 §4.6; FEAT-011)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import (
    Base,
)

if TYPE_CHECKING:
    from backend.models.baseline import Baseline


class Epoch(Base):
    """`epochs` (TRD 20 §4.6.11; TRD 23 §4.2.11; FEAT-011)."""

    __tablename__ = "epochs"
    __table_args__ = (
        UniqueConstraint("resident_id", "epoch_number", name="epochs_resident_number_uq"),
        CheckConstraint(
            "epoch_number >= 1",
            name="epochs_number_ck",
        ),
        CheckConstraint(
            "ended_at IS NULL OR ended_at > started_at",
            name="epochs_order_ck",
        ),
        Index(
            "epochs_current_uq",
            "resident_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
        Index("epochs_device_idx", "device_id"),
        Index("epochs_run_idx", "pipeline_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id", ondelete="RESTRICT"), nullable=False
    )
    epoch_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False
    )
    device_firmware_version: Mapped[str] = mapped_column(Text(), nullable=False)
    extraction_software_version: Mapped[str] = mapped_column(Text(), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    baselines: Mapped[list[Baseline]] = relationship(order_by="Baseline.feature_key", viewonly=True)
