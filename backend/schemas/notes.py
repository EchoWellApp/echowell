"""Staff-note DTOs of TRD 19 §4.5 (`StaffNoteCreate`, `StaffNote`, `StaffNoteList`)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field

from backend.schemas.alerts import UserRef
from backend.schemas.common import PageMeta, RequestModel, ResponseModel
from backend.schemas.residents import ResidentCode

NoteType = Literal["observation", "action_taken", "follow_up"]


class StaffNoteCreate(RequestModel):
    note_type: NoteType
    body: str = Field(min_length=1, max_length=2000)
    alert_id: uuid.UUID | None = None
    supersedes_id: uuid.UUID | None = None


class StaffNote(ResponseModel):
    id: uuid.UUID
    resident_code: ResidentCode
    alert_id: uuid.UUID | None
    author: UserRef
    note_type: NoteType
    body: str
    supersedes_id: uuid.UUID | None
    created_at: datetime


class StaffNoteList(PageMeta):
    items: list[StaffNote]
