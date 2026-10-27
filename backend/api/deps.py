"""Shared request dependencies (TRD 05 §4.2 API-010..API-017; TRD 12 §4.6; FEAT-020, FEAT-021).

All are overridable through `app.dependency_overrides` (API-017). Every route declares
`authorize("<METHOD> <path>")`, which applies the `permissions.PERMISSIONS` row for that endpoint:
the Bearer JWT for user roles, the `X-API-Key` header for the API-key scope, 401 for a missing or
wrong credential type and 403 `FORBIDDEN` (with an `access.denied` audit row) for a wrong role or
scope (SEC-040, SEC-108).
"""

from __future__ import annotations

import ipaddress
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date
from typing import Annotated, Any, NoReturn

from fastapi import Depends, Request
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from backend.api.permissions import PERMISSIONS
from backend.core import db
from backend.core.config import Settings, get_settings
from backend.core.errors import (
    AppError,
    ForbiddenError,
    InvalidQueryParameterError,
    NotAuthenticatedError,
)
from backend.core.logging import set_context
from backend.models import ActorType, ApiKey, User
from backend.schemas.common import Meta
from backend.services import audit_service, auth_service, meta_service
from backend.services.audit_service import AuditAction
from backend.services.ingestion import Caller, IngestService
from backend.services.pipeline_runner import Executor, PipelineRunner, SessionFactory

__all__ = [
    "AuditWriter",
    "Pagination",
    "Principal",
    "authorize",
    "check_date_range",
    "client_ip",
    "get_audit_writer",
    "get_db",
    "get_engine",
    "get_ingest_service",
    "get_meta",
    "get_pagination",
    "get_pipeline_runner",
    "get_session_factory",
    "get_settings",
]

bearer_scheme = HTTPBearer(auto_error=False, scheme_name="bearerAuth", bearerFormat="JWT")
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False, scheme_name="apiKeyAuth")
BEARER_CHALLENGE = {"WWW-Authenticate": "Bearer"}


def get_engine(settings: Annotated[Settings, Depends(get_settings)]) -> Engine:
    """Engine of the app role (`DATABASE_URL`); never the migrator URL (ARC-015)."""
    return db.create_engine_for(settings.database_url, app_env=settings.app_env)


def get_db(engine: Annotated[Engine, Depends(get_engine)]) -> Iterator[Session]:
    """One session per request: commit on success, roll back on any exception, always close."""
    session = db.session_factory(engine)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session_factory(engine: Annotated[Engine, Depends(get_engine)]) -> SessionFactory:
    """Sessions for work in its own transactions (pipeline runs, API-063)."""
    return db.session_factory(engine)


def get_pipeline_runner(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    session_factory: Annotated[SessionFactory, Depends(get_session_factory)],
) -> PipelineRunner:
    """The runner with `app.state.pipeline_executor` when set (tests), else the interim
    executor until FEAT-053."""
    executor: Executor | None = getattr(request.app.state, "pipeline_executor", None)
    return PipelineRunner(session_factory, settings, executor)


def get_ingest_service(
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    runner: Annotated[PipelineRunner, Depends(get_pipeline_runner)],
) -> IngestService:
    return IngestService(session, settings, runner)


@dataclass(frozen=True)
class AuditWriter:
    """Writes `auth.login.failed` and `access.denied` rows in their own committed transaction
    (SEC-101, D-87), so the request's rollback does not remove them."""

    write: Callable[..., Any]

    def committed(self, **kwargs: Any) -> None:
        self.write(**kwargs)


def get_audit_writer(
    request: Request, engine: Annotated[Engine, Depends(get_engine)]
) -> AuditWriter:
    """`app.state.audit_writer` when set (tests), else a writer on the app engine."""
    configured: AuditWriter | None = getattr(request.app.state, "audit_writer", None)
    if configured is not None:
        return configured
    return AuditWriter(lambda **kwargs: audit_service.record_committed(engine, **kwargs))


def client_ip(request: Request) -> str | None:
    """Left-most `X-Forwarded-For` behind the Railway edge, else the socket peer (API-103).

    Only a valid IP address is returned (the audit `ip` column is INET); anything else, such
    as a forged header value, is recorded as unknown (None).
    """
    forwarded = request.headers.get("x-forwarded-for")
    candidate = forwarded.split(",", 1)[0].strip() if forwarded else None
    if not candidate and request.client:
        candidate = request.client.host
    try:
        return str(ipaddress.ip_address(candidate)) if candidate else None
    except ValueError:
        return None


@dataclass(frozen=True)
class Principal:
    """The caller of an authorised request (API-015)."""

    actor_type: ActorType
    actor_id: str
    user: User | None = None
    api_key: ApiKey | None = None

    @property
    def device_id(self) -> uuid.UUID | None:
        return self.api_key.device_id if self.api_key is not None else None

    @property
    def role(self) -> str | None:
        return self.user.role.value if self.user is not None else None

    def caller(self) -> Caller:
        """The ingest caller (FEAT-020-FR-14, `get_ingest_principal`)."""
        if self.api_key is not None:
            key = self.api_key
            return Caller(ActorType.API_KEY, str(key.id), api_key_id=key.id,
                          bound_device_id=key.device_id)  # fmt: skip
        user = self.require_user()
        return Caller(ActorType.USER, str(user.id), user_id=user.id)

    def require_user(self) -> User:
        """The signed-in user of a user-only endpoint."""
        if self.user is None:
            raise NotAuthenticatedError("Sign in to use this endpoint.", headers=BEARER_CHALLENGE)
        return self.user


def _deny(
    audit: AuditWriter, request: Request, actor: ActorType, actor_id: str, detail: str
) -> NoReturn:
    audit.committed(
        action=AuditAction.ACCESS_DENIED, actor_type=actor, actor_id=actor_id,
        entity_type=None, entity_id=None, details={"status": 403, "code": "FORBIDDEN"},
        ip=client_ip(request),
    )  # fmt: skip
    raise ForbiddenError(detail)


def authorize(endpoint: str) -> Callable[..., Principal]:
    """Dependency applying the `PERMISSIONS[endpoint]` row (SEC-040; API-012..API-015)."""
    access = PERMISSIONS[endpoint]

    def dependency(
        request: Request,
        session: Annotated[Session, Depends(get_db)],
        settings: Annotated[Settings, Depends(get_settings)],
        audit: Annotated[AuditWriter, Depends(get_audit_writer)],
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
        api_key_header: Annotated[str | None, Depends(api_key_scheme)],
    ) -> Principal:
        if access.roles and credentials is not None:
            try:
                user = auth_service.current_user(session, settings, credentials.credentials)
            except AppError as exc:
                exc.headers = {**exc.headers, **BEARER_CHALLENGE}
                raise
            set_context(actor=ActorType.USER.value, user_id=str(user.id))
            if user.role.value not in access.roles:
                _deny(audit, request, ActorType.USER, str(user.id), "Not allowed for this role.")
            return Principal(ActorType.USER, str(user.id), user=user)
        if access.api_key_scope is not None and api_key_header:
            key = auth_service.authenticate_api_key(session, api_key_header)
            set_context(actor=ActorType.API_KEY.value, user_id=str(key.id))
            if access.api_key_scope not in (key.scopes or []):
                detail = f"This API key does not have the scope {access.api_key_scope}."
                _deny(audit, request, ActorType.API_KEY, str(key.id), detail)
            return Principal(ActorType.API_KEY, str(key.id), api_key=key)
        if access.roles:
            raise NotAuthenticatedError("Sign in to use this endpoint.", headers=BEARER_CHALLENGE)
        raise NotAuthenticatedError("A valid API key is required for this endpoint.")

    dependency.__name__ = f"authorize_{endpoint}"
    return dependency


@dataclass(frozen=True)
class Pagination:
    limit: int
    offset: int


def get_pagination(limit: int = 50, offset: int = 0) -> Pagination:
    """`limit` 1..500 (default 50), `offset` >= 0 (default 0); else 422 INVALID_QUERY_PARAMETER."""
    if not 1 <= limit <= 500:
        raise InvalidQueryParameterError("limit must be between 1 and 500")
    if offset < 0:
        raise InvalidQueryParameterError("offset must be 0 or greater")
    return Pagination(limit=limit, offset=offset)


def get_meta(
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Meta:
    """The `meta` block of list, detail and analytics responses (API-057)."""
    return meta_service.get_meta(session, settings)


def check_date_range(start: date | None, end: date | None) -> None:
    """`from` later than `to` is 422 INVALID_QUERY_PARAMETER (API-093)."""
    if start is not None and end is not None and start > end:
        raise InvalidQueryParameterError("'from' must not be later than 'to'")
