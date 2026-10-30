"""Routers for /api/v1/alerts, reviews, snooze and /data-alerts (TRD 05 §4.1, API-080..API-082,
API-130..API-133; D-24; FEAT-030..FEAT-032).

There is deliberately no `POST /alerts/{id}/acknowledge` route: a saved review acknowledges an
alert (API-082, D-35).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from backend.api.deps import (
    Clock,
    Pagination,
    Principal,
    authorize,
    get_clock,
    get_db,
    get_pagination,
    get_read_context,
    get_settings,
)
from backend.api.responses import errors
from backend.core.config import Settings
from backend.schemas.alerts import (
    Alert,
    AlertList,
    AlertReview,
    AlertReviewCreate,
    AlertReviewList,
    AlertStatus,
    DataAlertKind,
    DataAlertList,
    DataAlertStatus,
    SnoozeRequest,
)
from backend.schemas.common import CODE_PATTERN
from backend.services import alert_service, data_alert_service, review_service
from backend.services.resident_service import ReadContext

router = APIRouter(tags=["alerts"])


@router.get("/alerts", response_model=AlertList, operation_id="listAlerts",
            responses=errors(401, 422))  # fmt: skip
def list_alerts(
    _: Annotated[Principal, Depends(authorize("GET /alerts"))],
    session: Annotated[Session, Depends(get_db)],
    ctx: Annotated[ReadContext, Depends(get_read_context)],
    page: Annotated[Pagination, Depends(get_pagination)],
    alert_status: Annotated[AlertStatus | None, Query(alias="status")] = None,
    resident_code: Annotated[str | None, Query(pattern=CODE_PATTERN)] = None,
) -> AlertList:
    body = alert_service.list_alerts(
        session, ctx, status=alert_status, resident_code=resident_code,
        limit=page.limit, offset=page.offset,
    )  # fmt: skip
    return AlertList.model_validate(body)


@router.post(
    "/alerts/{id}/reviews",
    status_code=status.HTTP_201_CREATED,
    response_model=AlertReview,
    operation_id="createAlertReview",
    responses=errors(401, 403, 404, 409, 422),
)
def create_review(
    id: uuid.UUID,
    body: AlertReviewCreate,
    principal: Annotated[Principal, Depends(authorize("POST /alerts/{id}/reviews"))],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> AlertReview:
    review = review_service.create(
        session, alert_id=id, user=principal.require_user(), explanations=body.explanations,
        outcome=body.outcome, note=body.note, profile=settings.pipeline_profile,
        facility_tz=settings.facility_tz, now=clock,
    )  # fmt: skip
    return AlertReview.model_validate(review)


@router.get(
    "/alerts/{id}/reviews",
    response_model=AlertReviewList,
    operation_id="listAlertReviews",
    responses=errors(401, 404),
)
def list_reviews(
    id: uuid.UUID,
    _: Annotated[Principal, Depends(authorize("GET /alerts/{id}/reviews"))],
    session: Annotated[Session, Depends(get_db)],
    ctx: Annotated[ReadContext, Depends(get_read_context)],
    page: Annotated[Pagination, Depends(get_pagination)],
) -> AlertReviewList:
    items, total = review_service.list_reviews(session, id, limit=page.limit, offset=page.offset)
    return AlertReviewList.model_validate(
        {"meta": ctx.meta, "items": items, "total": total, "limit": page.limit,
         "offset": page.offset}
    )  # fmt: skip


@router.post(
    "/alerts/{id}/snooze",
    response_model=Alert,
    operation_id="snoozeAlert",
    responses=errors(401, 403, 404, 409, 422),
)
def snooze_alert(
    id: uuid.UUID,
    principal: Annotated[Principal, Depends(authorize("POST /alerts/{id}/snooze"))],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    ctx: Annotated[ReadContext, Depends(get_read_context)],
    clock: Annotated[Clock, Depends(get_clock)],
    body: Annotated[SnoozeRequest | None, Body()] = None,
) -> Alert:
    alert = alert_service.snooze(
        session, ctx, settings.pipeline_profile, id, principal.require_user(),
        body.hours if body else None, clock,
    )  # fmt: skip
    return Alert.model_validate(alert)


@router.get("/data-alerts", response_model=DataAlertList, operation_id="listDataAlerts",
            responses=errors(401, 422))  # fmt: skip
def list_data_alerts(
    _: Annotated[Principal, Depends(authorize("GET /data-alerts"))],
    session: Annotated[Session, Depends(get_db)],
    ctx: Annotated[ReadContext, Depends(get_read_context)],
    page: Annotated[Pagination, Depends(get_pagination)],
    alert_status: Annotated[DataAlertStatus, Query(alias="status")] = "open",
    kind: DataAlertKind | None = None,
) -> DataAlertList:
    body = data_alert_service.list_data_alerts(
        session, ctx, status=alert_status, kind=kind, limit=page.limit, offset=page.offset
    )
    return DataAlertList.model_validate(body)
