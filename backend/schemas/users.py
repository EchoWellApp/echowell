"""User DTOs of TRD 19 §4.5 (`User`, `Role`, `LoginRequest`, `Token`, `UserCreate`, `UserUpdate`,
`UserList`)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field
from pydantic.config import JsonDict

from backend.schemas.common import PageMeta, RequestModel, ResponseModel

Role = Literal["admin", "clinician", "researcher"]
_EMAIL: JsonDict = {"format": "email"}


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
    password: str = Field(min_length=12, max_length=128)


class UserUpdate(RequestModel):
    model_config = RequestModel.model_config | {"json_schema_extra": {"minProperties": 1}}

    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    role: Role | None = None
    active: bool | None = None
    password: str | None = Field(default=None, min_length=12, max_length=128)


class UserList(PageMeta):
    items: list[User]
