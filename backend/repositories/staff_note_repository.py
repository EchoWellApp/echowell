"""Staff notes (TRD 23 §4.2.20; TRD 06 DB-010; FEAT-012).

Append-only for the application (SELECT, INSERT): a correction is a new row whose `supersedes_id`
points to the corrected note; the current notes are those no other note supersedes.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session, aliased

from backend.models import NoteType, StaffNote, User


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
        created_at: datetime | None = None,
    ) -> StaffNote:
        """`created_at` defaults to the database clock; the API passes the application clock."""
        note = StaffNote(
            resident_id=resident_id,
            author_user_id=author_user_id,
            note_type=note_type,
            body=body,
            alert_id=alert_id,
            supersedes_id=supersedes_id,
        )
        if created_at is not None:
            note.created_at = created_at
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

    def get(self, note_id: uuid.UUID) -> StaffNote | None:
        return self.session.get(StaffNote, note_id)

    def is_superseded(self, note_id: uuid.UUID) -> bool:
        return bool(self.session.scalar(select(exists().where(StaffNote.supersedes_id == note_id))))

    def page(
        self,
        resident_id: uuid.UUID,
        *,
        include_superseded: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[tuple[StaffNote, str]], int]:
        """Notes newest first with the author's display name (API-083)."""
        query = (
            select(StaffNote, User.display_name)
            .join(User, User.id == StaffNote.author_user_id)
            .where(StaffNote.resident_id == resident_id)
        )
        if not include_superseded:
            newer = aliased(StaffNote)
            superseded = select(newer.supersedes_id).where(newer.supersedes_id.is_not(None))
            query = query.where(StaffNote.id.not_in(superseded))
        total = self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        rows = self.session.execute(
            query.order_by(StaffNote.created_at.desc(), StaffNote.id).limit(limit).offset(offset)
        ).all()
        return [(note, name) for note, name in rows], total
