"""ORM models Device and DeviceAssignment (TRD 23 §4.6; FEAT-009)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    column,
    func,
    literal_column,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import (
    Base,
)

if TYPE_CHECKING:
    from backend.models.resident import Resident


class Device(Base):
    """`devices` (TRD 20 §4.6.4; TRD 23 §4.2.4; FEAT-009)."""

    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint("device_code", name="devices_device_code_uq"),
        CheckConstraint(
            "device_code ~ '^[A-Z0-9]{1,16}$'",
            name="devices_device_code_ck",
        ),
        CheckConstraint(
            "room_label IS NULL OR char_length(room_label) BETWEEN 1 AND 60",
            name="devices_room_label_ck",
        ),
        Index("devices_facility_idx", "facility_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False
    )
    device_code: Mapped[str] = mapped_column(Text(), nullable=False)
    room_label: Mapped[str | None] = mapped_column(Text(), nullable=True)
    firmware_version_last: Mapped[str | None] = mapped_column(Text(), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean(), server_default=text("true"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    assignments: Mapped[list[DeviceAssignment]] = relationship(back_populates="device")


class DeviceAssignment(Base):
    """`device_assignments` (TRD 20 §4.6.5; TRD 23 §4.2.5; FEAT-009)."""

    __tablename__ = "device_assignments"
    __table_args__ = (
        CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="device_assignments_range_ck",
        ),
        ExcludeConstraint(  # type: ignore[no-untyped-call]
            (column("resident_id"), "="),
            (
                func.daterange(column("valid_from"), column("valid_to"), literal_column("'[]'")),
                "&&",
            ),
            name="device_assignments_no_overlap_ex",
            using="gist",
        ),
        Index("device_assignments_device_idx", "device_id", "valid_from"),
        Index("device_assignments_resident_idx", "resident_id", "valid_from"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id", ondelete="RESTRICT"), nullable=False
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False
    )
    valid_from: Mapped[date] = mapped_column(Date(), nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    device: Mapped[Device] = relationship(back_populates="assignments")
    resident: Mapped[Resident] = relationship(back_populates="assignments")
