"""ORM model User (TRD 23 §4.6; FEAT-009). Only hashes are stored (PGS-034, SEC-125)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import (
    USER_ROLE,
    Base,
    UserRole,
)


class User(Base):
    """`users` (TRD 20 §4.6.2; TRD 23 §4.2.2; FEAT-009)."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="users_email_uq"),
        CheckConstraint(
            "email = lower(email)",
            name="users_email_lower_ck",
        ),
        CheckConstraint(
            "email ~ '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$' AND char_length(email) <= 254",
            name="users_email_format_ck",
        ),
        CheckConstraint(
            "char_length(display_name) BETWEEN 1 AND 120",
            name="users_display_name_ck",
        ),
        CheckConstraint(
            "password_hash LIKE '$argon2id$%'",
            name="users_password_hash_ck",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(Text(), nullable=False)
    display_name: Mapped[str] = mapped_column(Text(), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text(), nullable=False)
    role: Mapped[UserRole] = mapped_column(USER_ROLE, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean(), server_default=text("true"), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
