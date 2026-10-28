"""ORM model ConfigParameter (TRD 23 §4.6; FEAT-009); rows are seeded by migration 0002."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import (
    Base,
)


class ConfigParameter(Base):
    """`config_parameters` (TRD 20 §4.6.22; TRD 23 §4.2.22; FEAT-009)."""

    __tablename__ = "config_parameters"
    __table_args__ = (
        PrimaryKeyConstraint("profile", "key", name="config_parameters_pk"),
        CheckConstraint(
            "profile IN ('production', 'test_v0_1')",
            name="config_parameters_profile_ck",
        ),
        CheckConstraint(
            "key ~ '^[a-z][a-z0-9_]{0,63}$'",
            name="config_parameters_key_ck",
        ),
        Index("config_parameters_updated_by_idx", "updated_by"),
    )

    profile: Mapped[str] = mapped_column(Text(), nullable=False)
    key: Mapped[str] = mapped_column(Text(), nullable=False)
    value: Mapped[Any] = mapped_column(JSONB(), nullable=False)
    description: Mapped[str] = mapped_column(Text(), server_default=text("''"), nullable=False)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
