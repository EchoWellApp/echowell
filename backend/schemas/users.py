"""User DTOs of TRD 19 §4.5 (`User`, `Role`, `LoginRequest`, `Token`, `UserCreate`, `UserUpdate`,
`UserList`)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator
from pydantic.config import JsonDict

from backend.schemas.common import PageMeta, RequestModel, ResponseModel

Role = Literal["admin", "clinician", "researcher"]
_EMAIL: JsonDict = {"format": "email"}
# The password length is documented here but checked by the SEC-012 policy, so a short password
# is 422 PASSWORD_POLICY_VIOLATION rather than VALIDATION_ERROR (FEAT-037-FR-04).
_PASSWORD: JsonDict = {"minLength": 12, "maxLength": 128}


class User(ResponseModel):
    id: uuid.UUID
    email: str = Field(json_schema_extra=_EMAIL)
    display_name: str = Field(min_length=1, max_length=100)
    role: Role
    active: bool
    last_login_at: datetime | None
    created_at: datetime


class LoginRequest(RequestModel):
    email: str = Field(max_length=254, json_schema_extra=_EMAIL)
    password: str = Field(min_length=1, max_length=128)


class Token(ResponseModel):
    access_token: str
    token_type: Literal["bearer"]
    expires_in: int = Field(examples=[3600])
    user: User


class UserCreate(RequestModel):
    email: str = Field(max_length=254, json_schema_extra=_EMAIL)
    display_name: str = Field(min_length=1, max_length=100)
    role: Role
    password: str = Field(json_schema_extra=_PASSWORD)


class UserUpdate(RequestModel):
    model_config = RequestModel.model_config | {"json_schema_extra": {"minProperties": 1}}

    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    role: Role | None = None
    active: bool | None = None
    password: str | None = Field(default=None, json_schema_extra=_PASSWORD)

    @model_validator(mode="after")
    def _at_least_one(self) -> UserUpdate:
        """`minProperties: 1` (TRD 19 `UserUpdate`): an empty PATCH is 422."""
        if not any(getattr(self, name) is not None for name in self.model_fields_set):
            raise ValueError("give at least one of display_name, role, active, password")
        return self


class UserList(PageMeta):
    items: list[User]
