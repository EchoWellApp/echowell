"""ORM model FacilityReferenceRange (TRD 23 §4.6; FEAT-012)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
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


class FacilityReferenceRange(Base):
    """`facility_reference_ranges` (TRD 20 §4.6.21; TRD 23 §4.2.21; FEAT-012)."""

    __tablename__ = "facility_reference_ranges"
    __table_args__ = (
        UniqueConstraint(
            "facility_id",
            "feature_key",
            "sex",
            "pipeline_run_id",
            name="facility_reference_ranges_uq",
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint(
            f"feature_key IN ({sql_list(FEATURE_KEYS)})",
            name="facility_reference_ranges_feature_ck",
        ),
        CheckConstraint(
            "sex IS NULL OR sex IN ('F', 'M')",
            name="facility_reference_ranges_sex_ck",
        ),
        CheckConstraint(
            "low <= high",
            name="facility_reference_ranges_bounds_ck",
        ),
        CheckConstraint(
            "n_residents >= 1",
            name="facility_reference_ranges_n_ck",
        ),
        CheckConstraint(
            "char_length(method) BETWEEN 1 AND 200",
            name="facility_reference_ranges_method_ck",
        ),
        Index(
            "facility_reference_ranges_lookup_idx",
            "facility_id",
            "feature_key",
            text("computed_at DESC"),
        ),
        Index("facility_reference_ranges_run_idx", "pipeline_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False
    )
    feature_key: Mapped[str] = mapped_column(Text(), nullable=False)
    sex: Mapped[str | None] = mapped_column(Text(), nullable=True)
    low: Mapped[float] = mapped_column(Double(), nullable=False)
    high: Mapped[float] = mapped_column(Double(), nullable=False)
    method: Mapped[str] = mapped_column(Text(), nullable=False)
    n_residents: Mapped[int] = mapped_column(Integer(), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="RESTRICT"), nullable=False
    )
