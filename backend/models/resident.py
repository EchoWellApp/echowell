"""ORM model Resident (TRD 23 §4.6; FEAT-009). Study IDs only; no names or other PII (DB-035)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import (
    RESIDENT_COHORT,
    RESIDENT_STATUS,
    Base,
    ResidentCohort,
    ResidentStatus,
)

if TYPE_CHECKING:
    from backend.models.device import DeviceAssignment


class Resident(Base):
    """`residents` (TRD 20 §4.6.3; TRD 23 §4.2.3; FEAT-009)."""

    __tablename__ = "residents"
    __table_args__ = (
        UniqueConstraint("resident_code", name="residents_resident_code_uq"),
        CheckConstraint(
            "resident_code ~ '^[A-Z0-9]{1,16}$'",
            name="residents_resident_code_ck",
        ),
        CheckConstraint(
            "sex IS NULL OR sex IN ('F', 'M')",
            name="residents_sex_ck",
        ),
        CheckConstraint(
            "(status = 'withdrawn') = (withdrawn_on IS NOT NULL)",
            name="residents_withdrawn_ck",
        ),
        CheckConstraint(
            "withdrawn_on IS NULL OR withdrawn_on >= enrolled_on",
            name="residents_withdrawn_after_enrol_ck",
        ),
        CheckConstraint(
            "admitted_on IS NULL OR admitted_on <= enrolled_on",
            name="residents_admitted_ck",
        ),
        Index("residents_facility_idx", "facility_id"),
        Index("residents_status_cohort_idx", "status", "cohort"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False
    )
    resident_code: Mapped[str] = mapped_column(Text(), nullable=False)
    sex: Mapped[str | None] = mapped_column(Text(), nullable=True)
    cohort: Mapped[ResidentCohort] = mapped_column(
        RESIDENT_COHORT, server_default=text("'longitudinal'"), nullable=False
    )
    enrolled_on: Mapped[date] = mapped_column(Date(), nullable=False)
    admitted_on: Mapped[date | None] = mapped_column(Date(), nullable=True)
    withdrawn_on: Mapped[date | None] = mapped_column(Date(), nullable=True)
    status: Mapped[ResidentStatus] = mapped_column(
        RESIDENT_STATUS, server_default=text("'active'"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    assignments: Mapped[list[DeviceAssignment]] = relationship(back_populates="resident")
