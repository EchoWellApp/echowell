"""Router for E-05 `POST /api/v1/sessions`: one record from a device (TRD 05 API-030..API-047;
TRD 10 ING-001..ING-004; FEAT-025).

The handler reads the raw body itself so an invalid record is stored verbatim (API-031); the
OpenAPI request body references `IngestRecord`.
"""

# No `from __future__ import annotations`: slowapi wraps this route, and FastAPI would resolve
# string annotations against slowapi's module globals.

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from starlette.concurrency import run_in_threadpool

from backend.api.deps import Principal, authorize, get_ingest_service
from backend.api.responses import errors
from backend.core.rate_limit import ingest_key, ingest_limit, limiter
from backend.schemas.ingest import IngestResult
from backend.services.ingestion import IngestService

router = APIRouter(tags=["ingest"])

RECORD_BODY = {
    "requestBody": {
        "required": True,
        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/IngestRecord"}}},
    }
}


@router.post(
    "/sessions",
    status_code=status.HTTP_201_CREATED,
    response_model=IngestResult,
    operation_id="ingestSession",
    responses={
        200: {"model": IngestResult, "description": "Duplicate session_id stored and dropped"},
        **errors(401, 403, 413, 415, 422, 429),
    },
    openapi_extra=RECORD_BODY,
)
@limiter.limit(ingest_limit, key_func=ingest_key)
async def ingest_session(
    request: Request,
    response: Response,
    principal: Annotated[Principal, Depends(authorize("POST /sessions"))],
    service: Annotated[IngestService, Depends(get_ingest_service)],
) -> IngestResult:
    body = await request.body()
    code, result = await run_in_threadpool(service.ingest_single, principal.caller(), body)
    response.status_code = code
    return IngestResult.model_validate(result)
