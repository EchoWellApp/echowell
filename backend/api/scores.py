"""Router for E-12 `GET /api/v1/scores`, JSON or CSV (TRD 05 API-079, API-129; FEAT-034).

`Accept: text/csv` selects the export, allowed for researcher and admin only (matrix row
`GET /scores (text/csv)`); the JSON read-out is open to every user role.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.api.deps import (
    AuditWriter,
    Pagination,
    Principal,
    authorize,
    check_access,
    check_date_range,
    get_audit_writer,
    get_db,
    get_pagination,
    get_read_context,
    get_settings,
)
from backend.api.responses import errors
from backend.core.config import Settings
from backend.schemas.common import CODE_PATTERN
from backend.schemas.scores import ScoresResponse
from backend.services import export_service, score_service
from backend.services.resident_service import ReadContext

router = APIRouter(tags=["scores"])

CSV_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {
        "description": "Scored sessions (JSON) or CSV export when Accept is text/csv "
        "(researcher, admin)",
        "content": {"text/csv": {"schema": {"type": "string"}}},
    }
}


@router.get(
    "/scores",
    response_model=ScoresResponse,
    operation_id="listScores",
    responses={**CSV_RESPONSE, **errors(401, 403, 404, 413, 422)},
)
def list_scores(
    request: Request,
    principal: Annotated[Principal, Depends(authorize("GET /scores"))],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    ctx: Annotated[ReadContext, Depends(get_read_context)],
    audit: Annotated[AuditWriter, Depends(get_audit_writer)],
    page: Annotated[Pagination, Depends(get_pagination)],
    resident_code: Annotated[str | None, Query(pattern=CODE_PATTERN)] = None,
    epoch: Annotated[int | None, Query(ge=1)] = None,
    start: Annotated[date | None, Query(alias="from")] = None,
    end: Annotated[date | None, Query(alias="to")] = None,
) -> Any:
    csv = export_service.wants_csv(request.headers.get("accept"))
    if csv:
        check_access(principal, "GET /scores (text/csv)", request, audit)
    check_date_range(start, end)
    where = score_service.score_filter(
        session, resident_code=resident_code, epoch=epoch, start=start, end=end
    )
    if not csv:
        body = score_service.scores(
            session, ctx, settings.pipeline_profile, where, limit=page.limit, offset=page.offset
        )
        return ScoresResponse.model_validate(body)
    export_service.check_size(score_service.count_scores(session, where))
    rows = score_service.score_csv_rows(session, where)
    export_service.audit_export(
        session, route="/api/v1/scores", row_count=len(rows), actor_id=principal.actor_id,
        filters={"resident_code": resident_code, "epoch": epoch, "from": start, "to": end},
    )  # fmt: skip
    name = export_service.filename("scores", ctx.as_of_date)
    return StreamingResponse(
        export_service.lines(score_service.SCORE_FIELDS, rows),
        media_type=export_service.CSV_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )
