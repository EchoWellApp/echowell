"""Staff notes (TRD 23 §4.2.20; TRD 06 DB-010; FEAT-012).

Append-only for the application (SELECT, INSERT): a correction is a new row whose `supersedes_id`
points to the corrected note; the current notes are those no other note supersedes.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from backend.models import NoteType, StaffNote


class StaffNoteRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def insert(
        self,
        *,
        resident_id: uuid.UUID,
        author_user_id: uuid.UUID,
        note_type: NoteType,
        body: str,
        alert_id: uuid.UUID | None = None,
        supersedes_id: uuid.UUID | None = None,
    ) -> StaffNote:
        note = StaffNote(
            resident_id=resident_id,
            author_user_id=author_user_id,
            note_type=note_type,
            body=body,
            alert_id=alert_id,
            supersedes_id=supersedes_id,
        )
        self.session.add(note)
        self.session.flush()
        return note

    def current_for_resident(self, resident_id: uuid.UUID) -> list[StaffNote]:
        """The resident's notes that no later note supersedes, newest first."""
        newer = aliased(StaffNote)
        superseded = select(newer.supersedes_id).where(newer.supersedes_id.is_not(None))
        return list(
            self.session.scalars(
                select(StaffNote)
                .where(StaffNote.resident_id == resident_id, StaffNote.id.not_in(superseded))
                .order_by(StaffNote.created_at.desc())
            ).all()
        )
