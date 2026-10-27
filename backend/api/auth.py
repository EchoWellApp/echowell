"""Routers for E-02 `POST /auth/login`, E-03 `POST /auth/logout`, E-04 `GET /auth/me`
(TRD 05 §4.3 API-020..API-025; TRD 19; FEAT-020)."""

# No `from __future__ import annotations`: slowapi wraps these routes, and FastAPI would resolve
# string annotations against slowapi's module globals.

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from backend.api.deps import (
    AuditWriter,
    Principal,
    authorize,
    client_ip,
    get_audit_writer,
    get_db,
    get_settings,
)
from backend.api.responses import errors
from backend.core.config import Settings
from backend.core.rate_limit import limiter, login_key, login_limit
from backend.schemas.users import LoginRequest, Token, User
from backend.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token, operation_id="login", responses=errors(401, 422, 429))
@limiter.limit(login_limit, key_func=login_key)
def login(
    request: Request,
    body: LoginRequest,
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    audit: Annotated[AuditWriter, Depends(get_audit_writer)],
) -> Token:
    return auth_service.login(
        session, settings, body.email, body.password, client_ip(request), audit.committed
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    operation_id="logout",
    responses=errors(401),
)
def logout(
    request: Request,
    principal: Annotated[Principal, Depends(authorize("POST /auth/logout"))],
    session: Annotated[Session, Depends(get_db)],
) -> Response:
    auth_service.logout(session, principal.require_user(), client_ip(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=User, operation_id="getMe", responses=errors(401))
def me(principal: Annotated[Principal, Depends(authorize("GET /auth/me"))]) -> User:
    return User.model_validate(principal.require_user())
