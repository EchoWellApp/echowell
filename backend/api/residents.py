"""Routers for E-08 `GET /api/v1/residents`, E-09 `GET /residents/{resident_code}`, E-10
`.../checkins` and E-11 `.../features` (TRD 05 API-070..API-078; FEAT-027, FEAT-028).

A resident code that is unknown or does not match `^[A-Z0-9]{1,16}$` is 404 RESIDENT_NOT_FOUND
(FEAT-028-FR-01), so the path parameter is checked by the service, not by FastAPI.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.api.deps import (
    Clock,
    Pagination,
    Principal,
    authorize,
    check_date_range,
    get_clock,
    get_db,
    get_pagination,
    get_read_context,
)
from backend.api.responses import errors
from backend.schemas.notes import StaffNote, StaffNoteCreate, StaffNoteList
from backend.schemas.residents import (
    CheckinEventList,
    FeaturesResponse,
    ResidentDetail,
    ResidentsOverviewResponse,
)
from backend.services import checkin_service, feature_service, note_service, resident_service
from backend.services.resident_service import ReadContext, Sort

router = APIRouter(prefix="/residents", tags=["residents"])

MAX_LOG_DAYS = 366
FromDate = Annotated[date | None, Query(alias="from")]
ToDate = Annotated[date | None, Query(alias="to")]


@router.get(
    "",
    response_model=ResidentsOverviewResponse,
    operation_id="listResidents",
    responses=errors(401, 422),
)
def list_residents(
    _: Annotated[Principal, Depends(authorize("GET /residents"))],
    session: Annotated[Session, Depends(get_db)],
    ctx: Annotated[ReadContext, Depends(get_read_context)],
    page: Annotated[Pagination, Depends(get_pagination)],
    sort: Sort = "alarm",
    cohort: Literal["longitudinal", "new_admission"] = "longitudinal",
    include_withdrawn: bool = False,
) -> ResidentsOverviewResponse:
    body = resident_service.overview(
        session, ctx, sort=sort, cohort=cohort, include_withdrawn=include_withdrawn,
        limit=page.limit, offset=page.offset,
    )  # fmt: skip
    return ResidentsOverviewResponse.model_validate(body)


@router.get(
    "/{resident_code}",
    response_model=ResidentDetail,
    operation_id="getResident",
    responses=errors(401, 404),
)
def get_resident(
    resident_code: str,
    _: Annotated[Principal, Depends(authorize("GET /residents/{resident_code}"))],
    session: Annotated[Session, Depends(get_db)],
    ctx: Annotated[ReadContext, Depends(get_read_context)],
) -> ResidentDetail:
    return ResidentDetail.model_validate(resident_service.detail(session, ctx, resident_code))


@router.get(
    "/{resident_code}/checkins",
    response_model=CheckinEventList,
    operation_id="listCheckinEvents",
    responses=errors(401, 404, 422),
)
def list_checkins(
    resident_code: str,
    _: Annotated[Principal, Depends(authorize("GET /residents/{resident_code}/checkins"))],
    session: Annotated[Session, Depends(get_db)],
    ctx: Annotated[ReadContext, Depends(get_read_context)],
    page: Annotated[Pagination, Depends(get_pagination)],
    start: FromDate = None,
    end: ToDate = None,
) -> CheckinEventList:
    check_date_range(start, end, MAX_LOG_DAYS)
    items = checkin_service.events(session, ctx, resident_code, start or date.min, end or date.max)
    return CheckinEventList.model_validate(
        {
            "meta": ctx.meta, "items": items[page.offset : page.offset + page.limit],
            "total": len(items), "limit": page.limit, "offset": page.offset,
        }
    )  # fmt: skip


@router.get(
    "/{resident_code}/features",
    response_model=FeaturesResponse,
    operation_id="getResidentFeatures",
    responses=errors(401, 404, 422),
)
def get_features(
    resident_code: str,
    _: Annotated[Principal, Depends(authorize("GET /residents/{resident_code}/features"))],
    session: Annotated[Session, Depends(get_db)],
    ctx: Annotated[ReadContext, Depends(get_read_context)],
    start: FromDate = None,
    end: ToDate = None,
) -> FeaturesResponse:
    check_date_range(start, end)
    default_start, default_end = feature_service.default_window(ctx)
    body = feature_service.series(
        session, ctx, resident_code, start or default_start, end or default_end
    )
    return FeaturesResponse.model_validate(body)


@router.get(
    "/{resident_code}/notes",
    response_model=StaffNoteList,
    operation_id="listNotes",
    responses=errors(401, 404),
)
def list_notes(
    resident_code: str,
    _: Annotated[Principal, Depends(authorize("GET /residents/{resident_code}/notes"))],
    session: Annotated[Session, Depends(get_db)],
    ctx: Annotated[ReadContext, Depends(get_read_context)],
    page: Annotated[Pagination, Depends(get_pagination)],
    include_superseded: bool = False,
) -> StaffNoteList:
    items, total = note_service.list_notes(
        session, resident_code, include_superseded=include_superseded,
        limit=page.limit, offset=page.offset,
    )  # fmt: skip
    return StaffNoteList.model_validate(
        {"meta": ctx.meta, "items": items, "total": total, "limit": page.limit,
         "offset": page.offset}
    )  # fmt: skip


@router.post(
    "/{resident_code}/notes",
    status_code=status.HTTP_201_CREATED,
    response_model=StaffNote,
    operation_id="createNote",
    responses=errors(401, 403, 404, 409, 422),
)
def create_note(
    resident_code: str,
    body: StaffNoteCreate,
    principal: Annotated[Principal, Depends(authorize("POST /residents/{resident_code}/notes"))],
    session: Annotated[Session, Depends(get_db)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> StaffNote:
    note = note_service.create(
        session, resident_code, principal.require_user(), note_type=body.note_type,
        body=body.body, alert_id=body.alert_id, supersedes_id=body.supersedes_id, now=clock,
    )  # fmt: skip
    return StaffNote.model_validate(note)
