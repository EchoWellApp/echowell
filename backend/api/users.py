"""Routers for E-25 `GET /api/v1/users`, E-26 `POST /users`, E-27 `PATCH /users/{id}` (TRD 05
API-091, API-092; FEAT-037). Admin only; there is no DELETE route (FR-221)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.api.deps import (
    Pagination,
    Principal,
    authorize,
    get_db,
    get_pagination,
    get_read_context,
)
from backend.api.responses import errors
from backend.schemas.users import Role, User, UserCreate, UserList, UserUpdate
from backend.services import user_service
from backend.services.resident_service import ReadContext

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=UserList, operation_id="listUsers", responses=errors(401, 403))
def list_users(
    _: Annotated[Principal, Depends(authorize("GET /users"))],
    session: Annotated[Session, Depends(get_db)],
    ctx: Annotated[ReadContext, Depends(get_read_context)],
    page: Annotated[Pagination, Depends(get_pagination)],
    role: Role | None = None,
    active: bool | None = None,
) -> UserList:
    items, total = user_service.list_users(
        session, role=role, active=active, limit=page.limit, offset=page.offset
    )
    return UserList.model_validate(
        {"meta": ctx.meta, "items": items, "total": total, "limit": page.limit,
         "offset": page.offset}
    )  # fmt: skip


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=User,
    operation_id="createUser",
    responses=errors(401, 403, 409, 422),
)
def create_user(
    body: UserCreate,
    principal: Annotated[Principal, Depends(authorize("POST /users"))],
    session: Annotated[Session, Depends(get_db)],
) -> User:
    user = user_service.create(
        session, principal.require_user(), email=body.email, display_name=body.display_name,
        role=body.role, password=body.password,
    )  # fmt: skip
    return User.model_validate(user)


@router.patch(
    "/{id}",
    response_model=User,
    operation_id="updateUser",
    responses=errors(401, 403, 404, 409, 422),
)
def update_user(
    id: uuid.UUID,
    body: UserUpdate,
    principal: Annotated[Principal, Depends(authorize("PATCH /users/{id}"))],
    session: Annotated[Session, Depends(get_db)],
) -> User:
    changes = body.model_dump(exclude_unset=True)
    user = user_service.update(session, principal.require_user(), id, changes)
    return User.model_validate(user)
