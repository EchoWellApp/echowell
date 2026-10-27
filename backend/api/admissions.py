"""Routers for the experimental new-admission arm: E-22 `GET /api/v1/admissions`, E-23
`GET /admissions/{resident_code}/comparison`, E-24 `GET /facility/reference-ranges`
(TRD 05 API-089, API-090; FEAT-036). Every response carries `X-EchoWell-Experimental: true`."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from backend.api.deps import (
    Pagination,
    Principal,
    authorize,
    get_db,
    get_pagination,
    get_read_context,
)
from backend.api.responses import errors
from backend.schemas.admissions import AdmissionComparison, AdmissionList, ReferenceRangeList
from backend.services import admission_service
from backend.services.resident_service import ReadContext

router = APIRouter(tags=["admissions"])

EXPERIMENTAL = "X-EchoWell-Experimental"


@router.get("/admissions", response_model=AdmissionList, operation_id="listAdmissions",
            responses=errors(401))  # fmt: skip
def list_admissions(
    response: Response,
    _: Annotated[Principal, Depends(authorize("GET /admissions"))],
    session: Annotated[Session, Depends(get_db)],
    ctx: Annotated[ReadContext, Depends(get_read_context)],
    page: Annotated[Pagination, Depends(get_pagination)],
) -> AdmissionList:
    response.headers[EXPERIMENTAL] = "true"
    body = admission_service.list_admissions(session, ctx, limit=page.limit, offset=page.offset)
    return AdmissionList.model_validate(body)


@router.get(
    "/admissions/{resident_code}/comparison",
    response_model=AdmissionComparison,
    operation_id="getAdmissionComparison",
    responses=errors(401, 404),
)
def get_comparison(
    resident_code: str,
    response: Response,
    _: Annotated[Principal, Depends(authorize("GET /admissions/{resident_code}/comparison"))],
    session: Annotated[Session, Depends(get_db)],
    ctx: Annotated[ReadContext, Depends(get_read_context)],
) -> AdmissionComparison:
    response.headers[EXPERIMENTAL] = "true"
    body = admission_service.comparison(session, ctx, resident_code)
    return AdmissionComparison.model_validate(body)


@router.get(
    "/facility/reference-ranges",
    response_model=ReferenceRangeList,
    operation_id="listReferenceRanges",
    responses=errors(401),
)
def list_reference_ranges(
    response: Response,
    _: Annotated[Principal, Depends(authorize("GET /facility/reference-ranges"))],
    session: Annotated[Session, Depends(get_db)],
    ctx: Annotated[ReadContext, Depends(get_read_context)],
    page: Annotated[Pagination, Depends(get_pagination)],
) -> ReferenceRangeList:
    response.headers[EXPERIMENTAL] = "true"
    body = admission_service.reference_ranges(session, ctx, limit=page.limit, offset=page.offset)
    return ReferenceRangeList.model_validate(body)
