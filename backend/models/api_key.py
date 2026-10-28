"""ORM model ApiKey (TRD 23 §4.6; FEAT-009). Only the SHA-256 hash is stored (PGS-035)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import (
    Base,
)


class ApiKey(Base):
    """`api_keys` (TRD 20 §4.6.6; TRD 23 §4.2.6; FEAT-009)."""

    __tablename__ = "api_keys"
    __table_args__ = (
        UniqueConstraint("key_hash", name="api_keys_key_hash_uq"),
        CheckConstraint(
            "key_hash ~ '^[0-9a-f]{64}$'",
            name="api_keys_key_hash_ck",
        ),
        CheckConstraint(
            "char_length(name) BETWEEN 1 AND 120",
            name="api_keys_name_ck",
        ),
        CheckConstraint(
            "cardinality(scopes) >= 1 AND scopes <@ ARRAY['ingest:write', "
            "'pipeline:run']::text[]",
            name="api_keys_scopes_ck",
        ),
        Index("api_keys_device_idx", "device_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name: Mapped[str] = mapped_column(Text(), nullable=False)
    key_hash: Mapped[str] = mapped_column(Text(), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(
        ARRAY(Text()), server_default=text("ARRAY['ingest:write']::text[]"), nullable=False
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="RESTRICT"), nullable=True
    )
    active: Mapped[bool] = mapped_column(Boolean(), server_default=text("true"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
