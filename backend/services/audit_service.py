"""The audit writer (TRD 12 §4.12, SEC-100..SEC-109; TRD 06 DB-011; FEAT-015).

`record()` inserts one `audit_logs` row through the audit repository inside the caller's
transaction and never commits, so the audited change and its audit row commit or roll back together
(SEC-101, DB-011). `record_committed()` is the separate-transaction mode reserved for refused
requests that accompany no change (`auth.login.failed`, `access.denied`; SEC-101, TRD 24 D-87).

`AuditAction` is the closed TRD 12 §4.12 vocabulary: an unlisted action is rejected before any SQL
(SEC-109). `details` may only carry the keys documented for its action and never a password,
hash, token, API key, database URL, ingest body or feature value (SEC-104).
"""

from __future__ import annotations

import getpass
import logging
from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from backend.core.logging import get_request_id
from backend.models import FEATURE_KEYS, ActorType
from backend.repositories.audit_repository import AuditRepository

logger = logging.getLogger("backend.audit")


class AuditAction(StrEnum):
    """The 24 audit actions of TRD 12 §4.12 (the single vocabulary)."""

    AUTH_LOGIN_SUCCEEDED = "auth.login.succeeded"
    AUTH_LOGIN_FAILED = "auth.login.failed"
    AUTH_LOGOUT = "auth.logout"
    INGEST_BATCH_RECEIVED = "ingest.batch.received"
    NOTE_CREATED = "note.created"
    ALERT_REVIEWED = "alert.reviewed"
    ALERT_SNOOZED = "alert.snoozed"
    EXPORT_CSV = "export.csv"
    PIPELINE_RUN_STARTED = "pipeline.run.started"
    PIPELINE_RUN_FINISHED = "pipeline.run.finished"
    CONFIG_CHANGED = "config.changed"
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    API_KEY_CREATED = "api_key.created"
    API_KEY_REVOKED = "api_key.revoked"
    ACCESS_DENIED = "access.denied"
    ALERT_CLOSED = "alert.closed"
    DATA_ALERT_RESOLVED = "data_alert.resolved"
    RESIDENT_COHORT_CHANGED = "resident.cohort_changed"
    RESIDENT_WITHDRAWN = "resident.withdrawn"
    RESIDENT_PURGED = "resident.purged"
    ROSTER_LOADED = "roster.loaded"
    SEED_RESET = "seed.reset"
    PIPELINE_REBUILD = "pipeline.rebuild"


# Documented `details` keys per action (TRD 12 §4.12); CLI actions add `operator` (SEC-103).
DETAIL_KEYS: dict[AuditAction, frozenset[str]] = {
    AuditAction.AUTH_LOGIN_SUCCEEDED: frozenset(),
    AuditAction.AUTH_LOGIN_FAILED: frozenset({"email", "reason"}),
    AuditAction.AUTH_LOGOUT: frozenset(),
    AuditAction.INGEST_BATCH_RECEIVED: frozenset(
        {"source", "record_count", "accepted", "rejected", "duplicates", "pipeline_run_id"}
    ),
    AuditAction.NOTE_CREATED: frozenset(
        {"resident_code", "note_type", "alert_id", "supersedes_id"}
    ),
    AuditAction.ALERT_REVIEWED: frozenset(
        {"resident_code", "review_id", "outcome", "explanation_count", "previous_status"}
    ),
    AuditAction.ALERT_SNOOZED: frozenset({"resident_code", "hours", "snoozed_until"}),
    AuditAction.EXPORT_CSV: frozenset({"filters", "row_count"}),
    AuditAction.PIPELINE_RUN_STARTED: frozenset({"trigger", "scope", "profile"}),
    AuditAction.PIPELINE_RUN_FINISHED: frozenset({"status", "duration_ms", "warning_count"}),
    AuditAction.CONFIG_CHANGED: frozenset({"old", "new", "reason", "operator", "rotated"}),
    AuditAction.USER_CREATED: frozenset({"role", "operator"}),
    AuditAction.USER_UPDATED: frozenset({"changed", "operator"}),
    AuditAction.API_KEY_CREATED: frozenset({"name", "device_code", "operator"}),
    AuditAction.API_KEY_REVOKED: frozenset({"name", "operator"}),
    AuditAction.ACCESS_DENIED: frozenset({"status", "code"}),
    AuditAction.ALERT_CLOSED: frozenset({"resident_code", "closed_reason"}),
    AuditAction.DATA_ALERT_RESOLVED: frozenset({"alert_id", "kind", "reason", "operator"}),
    AuditAction.RESIDENT_COHORT_CHANGED: frozenset({"from", "to", "epoch_number"}),
    AuditAction.RESIDENT_WITHDRAWN: frozenset({"resident_code", "withdrawn_on", "operator"}),
    AuditAction.RESIDENT_PURGED: frozenset({"resident_code", "row_counts", "operator"}),
    AuditAction.ROSTER_LOADED: frozenset(
        {"residents", "devices", "device_assignments", "operator"}
    ),
    AuditAction.SEED_RESET: frozenset({"profile", "operator"}),
    AuditAction.PIPELINE_REBUILD: frozenset(
        {"profile", "old_config_hash", "new_config_hash", "operator"}
    ),
}

# Keys that would carry secrets or raw content anywhere in `details` (SEC-104).
FORBIDDEN_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "token",
        "access_token",
        "jwt",
        "api_key",
        "key",
        "key_hash",
        "secret",
        "database_url",
        "body",
        "raw_body",
        "payload",
        "note",
        "features",
        *FEATURE_KEYS,
    }
)
# Value fragments that identify a secret even under an allowed key (SEC-104).
_SECRET_MARKERS = ("$argon2", "ewk_", "postgres://", "postgresql://", "postgresql+psycopg://")


class AuditDetailsError(ValueError):
    """`details` breaks SEC-104 or carries a key not documented for the action."""


def cli_operator() -> str:
    """The OS user name running the CLI, stored as `details.operator` (SEC-103)."""
    return getpass.getuser()


def _check_value(value: Any, path: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).lower() in FORBIDDEN_KEYS:
                raise AuditDetailsError(f"details key {path}{key!s} is not allowed (SEC-104)")
            _check_value(item, f"{path}{key!s}.")
    elif isinstance(value, list | tuple):
        for item in value:
            _check_value(item, path)
    elif isinstance(value, str):
        lowered = value.lower()
        if any(marker in lowered for marker in _SECRET_MARKERS) or value.startswith("eyJ"):
            raise AuditDetailsError(f"details value at {path or 'top level'} looks like a secret")


def sanitise_details(action: AuditAction, details: Mapping[str, Any] | None) -> dict[str, Any]:
    """Validate `details` for `action` and return a plain dict (SEC-104, TRD 12 §4.12)."""
    clean = dict(details or {})
    unknown = set(clean) - DETAIL_KEYS[action]
    if unknown:
        raise AuditDetailsError(f"details keys {sorted(unknown)} are not documented for {action}")
    _check_value(clean, "")
    return clean


def _action(action: AuditAction | str) -> AuditAction:
    try:
        return AuditAction(action)
    except ValueError:
        raise ValueError(f"unknown audit action {action!r} (TRD 12 §4.12)") from None


def record(
    session: Session,
    *,
    action: AuditAction | str,
    actor_type: ActorType,
    actor_id: str | None,
    entity_type: str | None,
    entity_id: str | None,
    details: Mapping[str, Any] | None = None,
    ip: str | None = None,
    request_id: str | None = None,
) -> int:
    """Insert one audit row in the caller's transaction (no commit) and return its id."""
    checked = _action(action)
    clean = sanitise_details(checked, details)
    if request_id is None:
        request_id = get_request_id()  # LOG-033: rows written during a request carry its ID
    audit_id = AuditRepository(session).insert(
        actor_type=actor_type,
        actor_id=actor_id,
        action=checked.value,
        entity_type=entity_type,
        entity_id=entity_id,
        details=clean,
        ip=ip,
        request_id=request_id,
    )
    logger.info(
        "audit_event",
        extra={
            "event": "audit_event",
            "action": checked.value,
            "entity_type": entity_type,
            "entity_id": entity_id,
        },
    )
    return audit_id


def record_cli(
    session: Session,
    *,
    action: AuditAction | str,
    entity_type: str | None,
    entity_id: str | None,
    details: Mapping[str, Any] | None = None,
) -> int:
    """A CLI action: `actor_type = system`, `details.operator` = OS user (SEC-103)."""
    return record(
        session,
        action=action,
        actor_type=ActorType.SYSTEM,
        actor_id=None,
        entity_type=entity_type,
        entity_id=entity_id,
        details={**(details or {}), "operator": cli_operator()},
    )


_SEPARATE_ACTIONS = frozenset({AuditAction.AUTH_LOGIN_FAILED, AuditAction.ACCESS_DENIED})


def record_committed(engine: Engine, **kwargs: Any) -> int:
    """Write a refused-request row in its own committed transaction (SEC-101, D-87).

    Only `auth.login.failed` and `access.denied` use this mode; they accompany no change, so the
    rollback of the request session must not remove them.
    """
    if _action(kwargs["action"]) not in _SEPARATE_ACTIONS:
        raise ValueError("record_committed() is only for auth.login.failed and access.denied")
    with Session(engine) as session, session.begin():
        return record(session, **kwargs)


def login_failures_since(
    session: Session, email: str, since: datetime
) -> tuple[int, datetime | None]:
    """Failed logins for one e-mail since `since`, for the SEC-015 lockout."""
    return AuditRepository(session).login_failures_since(email, since)
