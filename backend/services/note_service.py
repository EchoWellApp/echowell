"""Staff notes (TRD 05 API-083..API-085; TRD 19 E-15, E-16; TRD 06 DB-010; FEAT-033).

Notes are append-only: a correction is a new row that supersedes the old one. Creating a note never
changes an alert (FR-191). The note body is never written to the audit log (SEC-104).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.core.errors import (
    AlertNotFoundError,
    AlertResidentMismatchError,
    FieldError,
    ValidationFailedError,
)
from backend.models import ActorType, NoteType, StaffNote, User
from backend.repositories.alert_repository import AlertRepository
from backend.repositories.staff_note_repository import StaffNoteRepository
from backend.services import audit_service
from backend.services.audit_service import AuditAction
from backend.services.resident_service import get_resident

_SUPERSEDES = "supersedes_id"


def _dto(note: StaffNote, resident_code: str, author_name: str) -> dict[str, Any]:
    return {
        "id": note.id,
        "resident_code": resident_code,
        "alert_id": note.alert_id,
        "author": {"id": note.author_user_id, "display_name": author_name},
        "note_type": note.note_type.value,
        "body": note.body,
        "supersedes_id": note.supersedes_id,
        "created_at": note.created_at,
    }


def list_notes(
    session: Session, resident_code: str, *, include_superseded: bool, limit: int, offset: int
) -> tuple[list[dict[str, Any]], int]:
    """Newest first; superseded notes only with `include_superseded` (API-083, DB-010)."""
    resident = get_resident(session, resident_code)
    rows, total = StaffNoteRepository(session).page(
        resident.id, include_superseded=include_superseded, limit=limit, offset=offset
    )
    return [_dto(note, resident.resident_code, name) for note, name in rows], total


def _invalid_supersedes(message: str) -> ValidationFailedError:
    return ValidationFailedError(
        "The note is not valid.", errors=[FieldError(_SUPERSEDES, "invalid", message)]
    )


def create(
    session: Session,
    resident_code: str,
    user: User,
    *,
    note_type: str,
    body: str,
    alert_id: uuid.UUID | None,
    supersedes_id: uuid.UUID | None,
    now: Callable[[], datetime],
) -> dict[str, Any]:
    """Insert one note and its `note.created` audit row (API-084, API-085)."""
    resident = get_resident(session, resident_code)
    if not body.strip():  # the body is stored as received; only the check trims (PGS-036)
        raise ValidationFailedError(
            "The note is not valid.",
            errors=[FieldError("body", "string_too_short", "The note must not be empty.")],
        )
    if alert_id is not None:
        alert = AlertRepository(session).get(alert_id)
        if alert is None:
            raise AlertNotFoundError("No alert with this id.")
        if alert.resident_id != resident.id:
            raise AlertResidentMismatchError("The alert belongs to another resident.")
    notes = StaffNoteRepository(session)
    if supersedes_id is not None:
        previous = notes.get(supersedes_id)
        if previous is None or previous.resident_id != resident.id:
            raise _invalid_supersedes("supersedes_id must name a note of this resident.")
        if notes.is_superseded(supersedes_id):
            raise _invalid_supersedes("This note has already been superseded.")
    try:
        with session.begin_nested():
            note = notes.insert(
                resident_id=resident.id, author_user_id=user.id, note_type=NoteType(note_type),
                body=body, alert_id=alert_id, supersedes_id=supersedes_id, created_at=now(),
            )  # fmt: skip
    except IntegrityError:  # a concurrent correction of the same note (staff_notes_supersedes_uq)
        raise _invalid_supersedes("This note has already been superseded.") from None
    audit_service.record(
        session, action=AuditAction.NOTE_CREATED, actor_type=ActorType.USER,
        actor_id=str(user.id), entity_type="staff_note", entity_id=str(note.id),
        details={"resident_code": resident.resident_code, "note_type": note_type,
                 "alert_id": str(alert_id) if alert_id else None,
                 "supersedes_id": str(supersedes_id) if supersedes_id else None},
    )  # fmt: skip
    return _dto(note, resident.resident_code, user.display_name)
