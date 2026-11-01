"""Alert list and snooze (TRD 05 API-080, API-132; TRD 09 CUS-022..CUS-026, CUS-039; TRD 19 E-13,
E-29; FEAT-030, FEAT-031).

Alerts surface only through the authenticated API (FR-109); nothing here sends e-mail, SMS or push
messages. A snooze sets the reminder only; status, tallies and scores never change (CUS-008).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from analytics.alert_generator import leaning_most as engine_leaning_most
from analytics.config import AlertEvent
from backend.core.errors import AlertClosedError, AlertNotFoundError
from backend.models import ActorType, Alert, AlertStatus, User
from backend.repositories.alert_repository import AlertFacts, AlertRepository
from backend.repositories.config_repository import ConfigRepository
from backend.repositories.resident_repository import ResidentRepository
from backend.services import audit_service, engine_read
from backend.services.audit_service import AuditAction
from backend.services.resident_service import ReadContext


def leaning_most(session: Session, ctx: ReadContext, facts: AlertFacts) -> list[str]:
    """The up-to-3 features leaning most in the alarm direction, by the engine's pure
    `leaning_most` on the stored scores of the alert's epoch (CUS-041, FEAT-048-FR-07, D-79)."""
    alert = facts.alert
    event = AlertEvent(
        facts.resident_code, facts.epoch_number, alert.session_id, alert.triggered_at,
        alert.local_date, alert.cusum_value, False, None,
    )  # fmt: skip
    stored = engine_read.epoch_scores(session, alert, facts.resident_code, facts.epoch_number)
    scores = [s for s in stored if s.local_date <= ctx.as_of_date]
    return list(engine_leaning_most(scores, event, ctx.pipeline_config))


def alert_dto(session: Session, ctx: ReadContext, facts: AlertFacts) -> dict[str, Any]:
    """The `Alert` DTO (TRD 19): facts only, wording is the frontend's (CUS-026)."""
    alert = facts.alert
    return {
        "id": alert.id,
        "resident_code": facts.resident_code,
        "device_code": facts.device_code,
        "epoch_number": facts.epoch_number,
        "session_id": alert.session_id,
        "triggered_at": alert.triggered_at,
        "local_date": alert.local_date,
        "cusum_value": alert.cusum_value,
        "current_tally": facts.current_tally,
        "open_days": max(0, (ctx.as_of_date - alert.local_date).days),
        "status": alert.status.value,
        "reviewed": alert.status == AlertStatus.ACKNOWLEDGED,
        "review_count": facts.review_count,
        "last_reviewed_at": facts.last_reviewed_at,
        "snoozed_until": alert.snoozed_until,
        "snoozed_by": alert.snoozed_by,
        "leaning_most": leaning_most(session, ctx, facts),
        "closed_reason": alert.closed_reason,
    }


def list_alerts(
    session: Session,
    ctx: ReadContext,
    *,
    status: str | None,
    resident_code: str | None,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    """`AlertList` by `triggered_at` ascending; `?status=open` total is the nav badge (CUS-025)."""
    resident_id: uuid.UUID | None = None
    if resident_code is not None:
        resident = ResidentRepository(session).get_by_code(resident_code)
        if resident is None:
            return {"meta": ctx.meta, "items": [], "total": 0, "limit": limit, "offset": offset}
        resident_id = resident.id
    rows, total = AlertRepository(session).list_with_facts(
        status=AlertStatus(status) if status else None, resident_id=resident_id,
        limit=limit, offset=offset,
    )  # fmt: skip
    return {
        "meta": ctx.meta, "items": [alert_dto(session, ctx, f) for f in rows],
        "total": total, "limit": limit, "offset": offset,
    }  # fmt: skip


def open_alert_for_change(session: Session, alert_id: uuid.UUID) -> Alert:
    """The alert locked for a review or snooze: 404 unknown, 409 closed (API-082)."""
    alert = AlertRepository(session).get_for_update(alert_id)
    if alert is None:
        raise AlertNotFoundError("No alert with this id.")
    if alert.status == AlertStatus.CLOSED:
        raise AlertClosedError("This alert is closed.")
    return alert


def snooze(
    session: Session,
    ctx: ReadContext,
    profile: str,
    alert_id: uuid.UUID,
    user: User,
    hours: int | None,
    now: Callable[[], datetime],
) -> dict[str, Any]:
    """Set `snoozed_until` = application-clock now + hours (DME-022, D-37); audit it."""
    alert = open_alert_for_change(session, alert_id)
    if hours is None:
        hours = int(ConfigRepository(session).values_for_profile(profile)["alert_snooze_hours"])
    until = now() + timedelta(hours=hours)
    AlertRepository(session).snooze(alert, by=user.id, until=until)
    facts = AlertRepository(session).facts(alert.id)
    assert facts is not None  # noqa: S101 - the alert was just loaded
    audit_service.record(
        session, action=AuditAction.ALERT_SNOOZED, actor_type=ActorType.USER,
        actor_id=str(user.id), entity_type="alert", entity_id=str(alert.id),
        details={"resident_code": facts.resident_code, "hours": hours,
                 "snoozed_until": until.isoformat()},
    )  # fmt: skip
    return alert_dto(session, ctx, facts)
