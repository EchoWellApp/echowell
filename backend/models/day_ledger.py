"""ORM model DayLedgerEntry (TRD 23 §4.6; FEAT-011)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import (
    DAY_STATUS,
    Base,
    DayStatus,
)


class DayLedgerEntry(Base):
    """`day_ledger` (TRD 20 §4.6.13; TRD 23 §4.2.13; FEAT-011)."""

    __tablename__ = "day_ledger"
    __table_args__ = (
        UniqueConstraint("resident_id", "local_date", name="day_ledger_resident_date_uq"),
        CheckConstraint(
            "(status = 'checked_in' AND reason = '') OR (status = 'missing_resident' "
            "AND reason = 'no record received') OR (status = 'missing_device_gap' AND "
            "device_id IS NOT NULL AND reason LIKE 'all residents on shared device % "
            "have no record')",
            name="day_ledger_reason_ck",
        ),
        Index(
            "day_ledger_missing_idx",
            "resident_id",
            "local_date",
            postgresql_where=text("status <> 'checked_in'"),
        ),
        Index("day_ledger_device_date_idx", "device_id", "local_date"),
        Index("day_ledger_run_idx", "pipeline_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id", ondelete="RESTRICT"), nullable=False
    )
    local_date: Mapped[date] = mapped_column(Date(), nullable=False)
    status: Mapped[DayStatus] = mapped_column(DAY_STATUS, nullable=False)
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="RESTRICT"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text(), server_default=text("''"), nullable=False)
    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
