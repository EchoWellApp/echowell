"""Routers for E-06 `POST /api/v1/ingest` (JSON batch or CSV upload) and E-07
`GET /api/v1/ingest/batches/{id}` (TRD 05 API-048..API-056; TRD 10 ING-005..ING-012; FEAT-026).

The batch handler reads the body itself (API-031). After the batch transaction commits, the
pipeline run it started is executed as a background task (API-053).
"""

# No `from __future__ import annotations`: slowapi wraps the batch route (see sessions.py).

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from backend.api.deps import Principal, authorize, get_db, get_ingest_service
from backend.api.responses import errors
from backend.core.errors import BatchNotFoundError, UnsupportedMediaTypeError, ValidationFailedError
from backend.core.rate_limit import ingest_key, ingest_limit, limiter
from backend.models import IngestSource
from backend.schemas.ingest import IngestBatch, IngestBatchAccepted
from backend.services import ingestion
from backend.services.ingestion import IngestService

router = APIRouter(prefix="/ingest", tags=["ingest"])

CSV_MEDIA_TYPES = frozenset({"text/csv", "application/vnd.ms-excel"})  # browsers send the latter
BATCH_BODY = {
    "requestBody": {
        "required": True,
        "content": {
            "application/json": {"schema": {"$ref": "#/components/schemas/IngestBatchRequest"}},
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "required": ["file"],
                    "properties": {
                        "file": {
                            "type": "string",
                            "contentMediaType": "text/csv",
                            "description": "UTF-8 CSV with the SRC-05 header, max 5 MB",
                        }
                    },
                }
            },
        },
    }
}


async def _csv_upload(request: Request) -> tuple[bytes, str]:
    """The `file` part of an upload: CSV only, never audio or `.xlsx` (ING-012, ING-053)."""
    form = await request.form()
    upload = form.get("file")
    if not isinstance(upload, UploadFile):
        raise ValidationFailedError("The upload needs one part named file.")
    filename = upload.filename or "upload.csv"
    media_type = (upload.content_type or "").split(";")[0].strip().lower()
    if media_type not in CSV_MEDIA_TYPES or filename.lower().endswith((".xlsx", ".xls")):
        raise UnsupportedMediaTypeError("Upload a CSV file (text/csv).")
    return await upload.read(), filename


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=IngestBatchAccepted,
    operation_id="ingestBatch",
    responses=errors(401, 403, 413, 415, 422, 429),
    openapi_extra=BATCH_BODY,
)
@limiter.shared_limit(ingest_limit, scope="ingest", key_func=ingest_key)
async def ingest_batch(
    request: Request,
    background: BackgroundTasks,
    principal: Annotated[Principal, Depends(authorize("POST /ingest"))],
    service: Annotated[IngestService, Depends(get_ingest_service)],
) -> IngestBatchAccepted:
    media_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if media_type == "multipart/form-data":
        data, filename = await _csv_upload(request)
        name_map = await run_in_threadpool(ingestion.name_map, service.session, service.settings)
        records = ingestion.parse_csv_batch(data, name_map)
        source = IngestSource.CSV_UPLOAD
    else:
        records = ingestion.parse_json_batch(await request.body())
        source, filename = IngestSource.API_BATCH, None
    result, handle = await run_in_threadpool(
        service.ingest_batch, principal.caller(), records, source, filename
    )
    if handle is not None:
        background.add_task(service.runner.execute, handle)
    return IngestBatchAccepted.model_validate(result)


@router.get(
    "/batches/{id}",
    response_model=IngestBatch,
    operation_id="getIngestBatch",
    responses=errors(401, 403, 404, 422),
)
def get_ingest_batch(
    id: uuid.UUID,
    _: Annotated[Principal, Depends(authorize("GET /ingest/batches/{id}"))],
    session: Annotated[Session, Depends(get_db)],
) -> IngestBatch:
    detail = ingestion.batch_detail(session, id)
    if detail is None:
        raise BatchNotFoundError("No ingest batch with this id.")
    return IngestBatch.model_validate(detail)
