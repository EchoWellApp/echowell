"""Routers for E-18 `GET /api/v1/analytics` and E-19 `GET /analytics/baselines` (JSON or CSV)
(TRD 05 API-087, API-088, API-129; FEAT-034, FEAT-035)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.api.deps import (
    Pagination,
    Principal,
    authorize,
    get_db,
    get_pagination,
    get_read_context,
    get_settings,
)
from backend.api.responses import errors
from backend.core.config import Settings
from backend.schemas.analytics import AnalyticsResponse
from backend.schemas.common import CODE_PATTERN
from backend.schemas.scores import BaselineRowList
from backend.services import analytics_summary, export_service, score_service
from backend.services.analytics_summary import GroundTruthSessions
from backend.services.resident_service import ReadContext

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_ground_truth(
    settings: Annotated[Settings, Depends(get_settings)],
) -> GroundTruthSessions | None:
    """Sessions for the alarm-timing answer key, profile test_v0_1 only (API-136)."""
    return analytics_summary.ground_truth_sessions(settings)


@router.get(
    "", response_model=AnalyticsResponse, operation_id="getAnalytics", responses=errors(401, 403)
)
def get_analytics(
    _: Annotated[Principal, Depends(authorize("GET /analytics"))],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    ctx: Annotated[ReadContext, Depends(get_read_context)],
    ground_truth: Annotated[GroundTruthSessions | None, Depends(get_ground_truth)],
) -> AnalyticsResponse:
    body = analytics_summary.build(session, ctx, settings, ground_truth)
    return AnalyticsResponse.model_validate(body)


@router.get(
    "/baselines",
    response_model=BaselineRowList,
    operation_id="listBaselines",
    responses={
        200: {
            "description": "Baselines (JSON) or CSV export when Accept is text/csv",
            "content": {"text/csv": {"schema": {"type": "string"}}},
        },
        **errors(401, 403, 413, 422),
    },
)
def list_baselines(
    request: Request,
    principal: Annotated[Principal, Depends(authorize("GET /analytics/baselines"))],
    session: Annotated[Session, Depends(get_db)],
    ctx: Annotated[ReadContext, Depends(get_read_context)],
    page: Annotated[Pagination, Depends(get_pagination)],
    resident_code: Annotated[str | None, Query(pattern=CODE_PATTERN)] = None,
    epoch: Annotated[int | None, Query(ge=1)] = None,
) -> Any:
    rows = score_service.baseline_rows(session, resident_code=resident_code, epoch=epoch)
    if not export_service.wants_csv(request.headers.get("accept")):
        return BaselineRowList.model_validate(
            {
                "meta": ctx.meta, "items": rows[page.offset : page.offset + page.limit],
                "total": len(rows), "limit": page.limit, "offset": page.offset,
            }
        )  # fmt: skip
    export_service.check_size(len(rows))
    export_service.audit_export(
        session, route="/api/v1/analytics/baselines", row_count=len(rows),
        actor_id=principal.actor_id, filters={"resident_code": resident_code, "epoch": epoch},
    )  # fmt: skip
    name = export_service.filename("baselines", ctx.as_of_date)
    fields = score_service.BASELINE_FIELDS
    return StreamingResponse(
        export_service.lines(fields, ([row[f] for f in fields] for row in rows)),
        media_type=export_service.CSV_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )
