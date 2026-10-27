"""Dashboard login, logout and the current user (TRD 05 API-020..API-025; TRD 12 SEC-010..SEC-036;
FEAT-020).

Failed logins are audited in their own committed transaction (`AuditWriter.committed`), because
the request transaction rolls back with the 401 or 429 (SEC-101, D-87).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from backend.core import security
from backend.core.config import Settings
from backend.core.errors import (
    AccountLockedError,
    ApiKeyInvalidError,
    InvalidCredentialsError,
    TokenInvalidError,
)
from backend.models import ActorType, ApiKey, User
from backend.repositories.api_key_repository import ApiKeyRepository
from backend.repositories.user_repository import UserRepository
from backend.schemas.users import Token
from backend.schemas.users import User as UserDto
from backend.services import audit_service
from backend.services.audit_service import AuditAction

LOCKOUT_FAILURES = 10
LOCKOUT_WINDOW = timedelta(minutes=15)
INVALID_DETAIL = "The e-mail address or password is not correct."

CommittedAudit = Callable[..., Any]


def _secret(settings: Settings) -> str:
    if settings.jwt_secret is None:
        raise TokenInvalidError("Authentication is not configured.")
    return settings.jwt_secret.get_secret_value()


def login(
    session: Session,
    settings: Settings,
    email: str,
    password: str,
    ip: str | None,
    audit_committed: CommittedAudit,
    now: datetime | None = None,
) -> Token:
    """Issue a token; 401 INVALID_CREDENTIALS or 429 ACCOUNT_TEMPORARILY_LOCKED (SEC-013..015)."""
    moment = now or datetime.now(UTC)
    address = security.normalise_email(email)

    def failed(reason: str) -> None:
        audit_committed(
            action=AuditAction.AUTH_LOGIN_FAILED, actor_type=ActorType.SYSTEM, actor_id=None,
            entity_type="user", entity_id=None, details={"email": address, "reason": reason}, ip=ip,
        )  # fmt: skip

    failures, last = audit_service.login_failures_since(session, address, moment - LOCKOUT_WINDOW)
    if failures >= LOCKOUT_FAILURES and last is not None:
        failed("locked")
        retry = max(1, int((last + LOCKOUT_WINDOW - moment).total_seconds()))
        raise AccountLockedError(
            "Too many failed logins for this account. Try again later.",
            headers={"Retry-After": str(retry)},
        )
    users = UserRepository(session)
    user = users.get_by_email(address)
    if user is None:
        security.verify_password(password, security.DUMMY_PASSWORD_HASH)  # equal timing (SEC-013)
        failed("invalid_credentials")
        raise InvalidCredentialsError(INVALID_DETAIL)
    if not security.verify_password(password, user.password_hash) or not user.active:
        failed("invalid_credentials")
        raise InvalidCredentialsError(INVALID_DETAIL)
    if security.needs_rehash(user.password_hash):
        users.update(user, password_hash=security.hash_password(password))  # SEC-011
    users.touch_login(user, moment)
    audit_service.record(
        session, action=AuditAction.AUTH_LOGIN_SUCCEEDED, actor_type=ActorType.USER,
        actor_id=str(user.id), entity_type="user", entity_id=str(user.id), details={}, ip=ip,
    )  # fmt: skip
    token = security.create_access_token(
        user.id, user.role.value, _secret(settings), settings.jwt_expires_minutes, now=moment
    )
    return Token(
        access_token=token,
        token_type="bearer",  # noqa: S106 - the OAuth token type, not a secret
        expires_in=settings.jwt_expires_minutes * 60,
        user=UserDto.model_validate(user),
    )


def current_user(session: Session, settings: Settings, token: str) -> User:
    """The active user named by a valid token; the role is read from the database (SEC-034)."""
    claims = security.decode_access_token(token, _secret(settings))
    user = UserRepository(session).get(claims.user_id)
    if user is None or not user.active:
        raise TokenInvalidError("The access token is not valid.")
    return user


def logout(session: Session, user: User, ip: str | None) -> None:
    """Audit the logout; the token itself is not revoked server-side (SEC-036)."""
    audit_service.record(
        session, action=AuditAction.AUTH_LOGOUT, actor_type=ActorType.USER,
        actor_id=str(user.id), entity_type="user", entity_id=str(user.id), details={}, ip=ip,
    )  # fmt: skip


def user_id_from_token(token: str, settings: Settings) -> uuid.UUID | None:
    """Best-effort `sub` for rate-limit keys; None when the token does not verify."""
    try:
        return security.decode_access_token(token, _secret(settings)).user_id
    except Exception:  # any invalid token falls back to the client address
        return None


LAST_USED_INTERVAL = timedelta(minutes=1)


def authenticate_api_key(session: Session, raw_key: str, now: datetime | None = None) -> ApiKey:
    """The active key whose SHA-256 matches (API-014, SEC-022, SEC-024); `last_used_at` is
    updated at most once per minute (SEC-025). The scope is checked by the caller."""
    api_key = ApiKeyRepository(session).get_active_by_hash(security.hash_api_key(raw_key))
    if api_key is None:
        raise ApiKeyInvalidError("The API key is missing, unknown or revoked.")
    moment = now or datetime.now(UTC)
    if api_key.last_used_at is None or moment - api_key.last_used_at >= LAST_USED_INTERVAL:
        ApiKeyRepository(session).touch_last_used(api_key, moment)
    return api_key
