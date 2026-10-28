"""ORM model Facility (TRD 23 §4.6; FEAT-009)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
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


class Facility(Base):
    """`facilities` (TRD 20 §4.6.1; TRD 23 §4.2.1; FEAT-009)."""

    __tablename__ = "facilities"
    __table_args__ = (
        UniqueConstraint("name", name="facilities_name_uq"),
        CheckConstraint(
            "char_length(name) BETWEEN 1 AND 120",
            name="facilities_name_ck",
        ),
        CheckConstraint(
            "char_length(timezone) BETWEEN 1 AND 64",
            name="facilities_timezone_ck",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(Text(), nullable=False)
    timezone: Mapped[str] = mapped_column(
        Text(), server_default=text("'America/Chicago'"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
