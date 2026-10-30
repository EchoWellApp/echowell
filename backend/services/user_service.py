"""Dashboard user management (TRD 05 API-091, API-092; TRD 12 SEC-010..SEC-012, SEC-044;
TRD 19 E-25..E-27; FEAT-037).

Passwords go through the SEC-012 policy and argon2id hashing of `core.security`; the hash is never
returned or audited (DME-005, SEC-104). There is no delete: users are deactivated.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from backend.core import security
from backend.core.errors import (
    EmailAlreadyExistsError,
    ForbiddenError,
    LastAdminError,
    UserNotFoundError,
)
from backend.models import ActorType, User, UserRole
from backend.repositories.user_repository import UserRepository
from backend.schemas.users import User as UserDto
from backend.services import audit_service
from backend.services.audit_service import AuditAction


def _dto(user: User) -> dict[str, Any]:
    return UserDto.model_validate(user).model_dump()


def list_users(
    session: Session, *, role: str | None, active: bool | None, limit: int, offset: int
) -> tuple[list[dict[str, Any]], int]:
    rows, total = UserRepository(session).list_page(
        role=UserRole(role) if role else None, active=active, limit=limit, offset=offset
    )
    return [_dto(u) for u in rows], total


def create(
    session: Session, actor: User, *, email: str, display_name: str, role: str, password: str
) -> dict[str, Any]:
    """201 `User`; 409 EMAIL_ALREADY_EXISTS; 422 PASSWORD_POLICY_VIOLATION (API-091)."""
    users = UserRepository(session)
    if users.get_by_email(email) is not None:
        raise EmailAlreadyExistsError("A user with this e-mail address already exists.")
    security.validate_password(password, email)
    user = users.insert(
        email=email, display_name=display_name, password_hash=security.hash_password(password),
        role=UserRole(role),
    )  # fmt: skip
    audit_service.record(
        session, action=AuditAction.USER_CREATED, actor_type=ActorType.USER,
        actor_id=str(actor.id), entity_type="user", entity_id=str(user.id),
        details={"role": role},
    )  # fmt: skip
    return _dto(user)


def update(
    session: Session, actor: User, user_id: uuid.UUID, changes: dict[str, Any]
) -> dict[str, Any]:
    """Apply only the given fields (API-091); 403 for one's own role or deactivation (SEC-044);
    409 LAST_ADMIN when no active admin would remain (API-092)."""
    users = UserRepository(session)
    target = users.get(user_id)
    if target is None:
        raise UserNotFoundError("No user with this id.")
    new_role = UserRole(changes["role"]) if changes.get("role") is not None else None
    new_active = changes.get("active")
    if target.id == actor.id and (
        (new_role is not None and new_role != target.role) or new_active is False
    ):
        raise ForbiddenError("You cannot change your own role or deactivate yourself.")
    loses_admin = (
        target.role == UserRole.ADMIN
        and target.active
        and ((new_role is not None and new_role != UserRole.ADMIN) or new_active is False)
    )
    if loses_admin and [a.id for a in users.active_admins_for_update()] == [target.id]:
        raise LastAdminError("At least one active admin must remain.")
    password_hash = None
    if changes.get("password") is not None:
        security.validate_password(changes["password"], target.email)
        password_hash = security.hash_password(changes["password"])
    users.update(
        target, display_name=changes.get("display_name"), role=new_role, active=new_active,
        password_hash=password_hash,
    )  # fmt: skip
    changed = sorted(k for k in ("display_name", "role", "active", "password")
                     if changes.get(k) is not None)  # fmt: skip
    audit_service.record(
        session, action=AuditAction.USER_UPDATED, actor_type=ActorType.USER,
        actor_id=str(actor.id), entity_type="user", entity_id=str(target.id),
        details={"changed": changed},
    )  # fmt: skip
    return _dto(target)
