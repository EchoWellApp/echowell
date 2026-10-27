"""Alarm reviews (TRD 05 API-081, API-082, API-130, API-131; TRD 09 CUS-016, CUS-017, CUS-038,
CUS-040; TRD 19 E-14, E-28; FEAT-031).

A review adds one immutable `alert_reviews` row, marks an open alert acknowledged and, for outcome
`data_problem`, creates or links the resident's `review_flagged_data_problem` data alert, all in
one transaction. It never touches `cusum_state`, `scores` or the alarm itself (CUS-008, D-03).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from backend.core.errors import AlertNotFoundError, FieldError, ValidationFailedError
from backend.models import (
    ActorType,
    AlertStatus,
    DataAlert,
    DataAlertKind,
    DataAlertStatus,
    ReviewOutcome,
    User,
)
from backend.repositories.alert_repository import AlertRepository
from backend.repositories.config_repository import ConfigRepository
from backend.repositories.data_alert_repository import DataAlertRepository
from backend.repositories.resident_repository import ResidentRepository
from backend.services import audit_service
from backend.services.alert_service import open_alert_for_change
from backend.services.audit_service import AuditAction


def explanation_codes(session: Session, profile: str) -> list[str]:
    """The configured codes, read on every request so `set-config` applies at once (D-56)."""
    values = ConfigRepository(session).values_for_profile(profile)
    return [item["code"] for item in values.get("review_explanations") or []]


def _check_explanations(codes: list[str], allowed: list[str]) -> None:
    errors = [
        FieldError(f"explanations.{i}", "unknown_explanation", "This code is not configured.")
        for i, code in enumerate(codes)
        if code not in allowed
    ]
    if len(set(codes)) != len(codes):
        errors.append(FieldError("explanations", "duplicate", "Each code may appear once."))
    if errors:
        raise ValidationFailedError("The review is not valid.", errors=errors)


def _review_dto(review: Any, display_name: str) -> dict[str, Any]:
    return {
        "id": review.id,
        "alert_id": review.alert_id,
        "reviewer": {"id": review.reviewer_user_id, "display_name": display_name},
        "explanations": list(review.explanations),
        "outcome": review.outcome.value,
        "note": review.note,
        "created_at": review.created_at,
    }


def create(
    session: Session,
    *,
    alert_id: uuid.UUID,
    user: User,
    explanations: list[str],
    outcome: str,
    note: str | None,
    profile: str,
    facility_tz: str,
    now: Callable[[], datetime],
) -> dict[str, Any]:
    """Save a review (201 `AlertReview`); 404 unknown, 409 closed, 422 invalid (API-082)."""
    alert = open_alert_for_change(session, alert_id)
    _check_explanations(explanations, explanation_codes(session, profile))
    previous_status = alert.status.value
    alerts = AlertRepository(session)
    at = now()  # the application clock for every timestamp of the review (DME-022)
    review = alerts.insert_review(
        alert_id=alert.id, reviewer_user_id=user.id, outcome=ReviewOutcome(outcome),
        explanations=explanations, note=note, created_at=at,
    )  # fmt: skip
    if alert.status == AlertStatus.OPEN:
        alerts.set_acknowledged(alert, by=user.id, at=at)
    resident = ResidentRepository(session).get_by_id(alert.resident_id)
    code = resident.resident_code if resident else ""
    if outcome == ReviewOutcome.DATA_PROBLEM.value:
        _flag_data_problem(session, alert.resident_id, code, review, user, facility_tz)
    audit_service.record(
        session, action=AuditAction.ALERT_REVIEWED, actor_type=ActorType.USER,
        actor_id=str(user.id), entity_type="alert", entity_id=str(alert.id),
        details={"resident_code": code, "review_id": str(review.id), "outcome": outcome,
                 "explanation_count": len(explanations), "previous_status": previous_status},
    )  # fmt: skip
    return _review_dto(review, user.display_name)


def _flag_data_problem(
    session: Session,
    resident_id: uuid.UUID,
    resident_code: str,
    review: Any,
    user: User,
    facility_tz: str,
) -> None:
    """Create the resident's `review_flagged_data_problem` data alert, or link the open one to the
    new review (CUS-040, D-114); the open row is locked so two reviews cannot both insert."""
    at = review.created_at
    local = at.astimezone(ZoneInfo(facility_tz))
    detail = f"a review flagged a data problem ({local:%b} {local.day}, {user.display_name})."
    repository = DataAlertRepository(session)
    existing = repository.open_for_subject(
        DataAlertKind.REVIEW_FLAGGED_DATA_PROBLEM, resident_id=resident_id, for_update=True
    )
    if existing is not None:
        existing.alert_review_id = review.id
        existing.detail = detail
        existing.last_detected_at = at
        session.flush()
        return
    repository.insert(
        DataAlert(
            kind=DataAlertKind.REVIEW_FLAGGED_DATA_PROBLEM, resident_id=resident_id,
            alert_review_id=review.id, title=f"{resident_code} · review flagged a data problem",
            detail=detail, first_detected_at=at, last_detected_at=at,
            status=DataAlertStatus.OPEN, pipeline_run_id=None,
        )
    )  # fmt: skip


def list_reviews(
    session: Session, alert_id: uuid.UUID, *, limit: int, offset: int
) -> tuple[list[dict[str, Any]], int]:
    """Reviews of one alert, newest first (API-131)."""
    alerts = AlertRepository(session)
    if alerts.get(alert_id) is None:
        raise AlertNotFoundError("No alert with this id.")
    rows, total = alerts.reviews_page(alert_id, limit=limit, offset=offset)
    return [_review_dto(review, name) for review, name in rows], total
