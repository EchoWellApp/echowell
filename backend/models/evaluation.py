"""ORM model EvaluationGroundTruth (TRD 23 §4.6; FEAT-012).

Test_v0_1 answer-key facts. No repository on the DATABASE_URL engine maps this model; it is
read only by `backend/services/analytics_summary.py` through DATABASE_READONLY_URL
(PGS-040, D-38).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import (
    Base,
)


class EvaluationGroundTruth(Base):
    """`evaluation_ground_truth` (TRD 20 §4.6.24; TRD 23 §4.2.24; FEAT-012)."""

    __tablename__ = "evaluation_ground_truth"
    __table_args__ = (
        UniqueConstraint("resident_code", name="evaluation_ground_truth_resident_code_uq"),
        CheckConstraint(
            "(planted_change = 'None') = (true_onset_date IS NULL)",
            name="evaluation_ground_truth_onset_ck",
        ),
        CheckConstraint(
            "char_length(planted_change) BETWEEN 1 AND 60 AND char_length(source_file) "
            "BETWEEN 1 AND 200",
            name="evaluation_ground_truth_text_ck",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    resident_code: Mapped[str] = mapped_column(Text(), nullable=False)
    planted_change: Mapped[str] = mapped_column(Text(), nullable=False)
    true_onset_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    source_file: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
