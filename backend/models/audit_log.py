"""ORM model AuditLog (TRD 23 §4.6; FEAT-012).

Append-only (PGS-018); written only through `audit_service`."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Index,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import (
    ACTOR_TYPE,
    ActorType,
    Base,
)


class AuditLog(Base):
    """`audit_logs` (TRD 20 §4.6.23; TRD 23 §4.2.23; FEAT-012)."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint(
            "action ~ '^[a-z_]+(\\.[a-z_]+){1,2}$'",
            name="audit_logs_action_ck",
        ),
        CheckConstraint(
            "jsonb_typeof(details) = 'object'",
            name="audit_logs_details_ck",
        ),
        CheckConstraint(
            "actor_type = 'system' OR actor_id IS NOT NULL",
            name="audit_logs_actor_ck",
        ),
        Index("audit_logs_occurred_idx", text("occurred_at DESC")),
        Index("audit_logs_entity_idx", "entity_type", "entity_id"),
        Index("audit_logs_actor_idx", "actor_type", "actor_id", text("occurred_at DESC")),
        Index("audit_logs_action_idx", "action", text("occurred_at DESC")),
    )

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    actor_type: Mapped[ActorType] = mapped_column(ACTOR_TYPE, nullable=False)
    actor_id: Mapped[str | None] = mapped_column(Text(), nullable=True)
    action: Mapped[str] = mapped_column(Text(), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(Text(), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(Text(), nullable=True)
    details: Mapped[Any] = mapped_column(
        JSONB(), server_default=text("'{}'::jsonb"), nullable=False
    )
    ip: Mapped[str | None] = mapped_column(INET(), nullable=True)
    request_id: Mapped[str | None] = mapped_column(Text(), nullable=True)
