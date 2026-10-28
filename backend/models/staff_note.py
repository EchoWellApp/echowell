"""ORM model StaffNote (TRD 23 §4.6; FEAT-012).

Notes are append-only; a correction is a new row that supersedes the old one (DB-010)."""

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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import (
    NOTE_TYPE,
    Base,
    NoteType,
)


class StaffNote(Base):
    """`staff_notes` (TRD 20 §4.6.20; TRD 23 §4.2.20; FEAT-012)."""

    __tablename__ = "staff_notes"
    __table_args__ = (
        CheckConstraint(
            "char_length(btrim(body)) >= 1 AND char_length(body) <= 2000",
            name="staff_notes_body_ck",
        ),
        UniqueConstraint("supersedes_id", name="staff_notes_supersedes_uq"),
        CheckConstraint(
            "supersedes_id IS NULL OR supersedes_id <> id",
            name="staff_notes_not_self_ck",
        ),
        Index("staff_notes_resident_created_idx", "resident_id", text("created_at DESC")),
        Index("staff_notes_alert_idx", "alert_id"),
        Index("staff_notes_author_idx", "author_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id", ondelete="RESTRICT"), nullable=False
    )
    alert_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="RESTRICT"), nullable=True
    )
    author_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    note_type: Mapped[NoteType] = mapped_column(NOTE_TYPE, nullable=False)
    body: Mapped[str] = mapped_column(Text(), nullable=False)
    marked_reviewed: Mapped[bool] = mapped_column(
        Boolean(), server_default=text("false"), nullable=False
    )
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("staff_notes.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    supersedes: Mapped[StaffNote | None] = relationship(remote_side="StaffNote.id")
