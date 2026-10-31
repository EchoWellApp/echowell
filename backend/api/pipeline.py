"""Routers for E-20 `POST /api/v1/pipeline/run`, E-31 `GET /api/v1/pipeline/runs` and E-21
`GET /api/v1/pipeline/runs/{id}` (TRD 05 API-063..API-069, API-134; FEAT-024)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session

from backend.api.deps import (
    Pagination,
    Principal,
    authorize,
    get_db,
    get_meta,
    get_pagination,
    get_pipeline_runner,
    get_settings,
)
from backend.api.responses import errors
from backend.core.config import Settings
from backend.core.errors import PipelineRunNotFoundError
from backend.schemas.common import Meta
from backend.schemas.pipeline import (
    PipelineRun,
    PipelineRunAccepted,
    PipelineRunList,
    PipelineRunRequest,
    PipelineStatus,
    PipelineTrigger,
)
from backend.services import pipeline_service
from backend.services.pipeline_runner import Actor, PipelineRunner

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post(
    "/run",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=PipelineRunAccepted,
    operation_id="startPipelineRun",
    responses=errors(401, 403, 404, 409, 422),
)
def start_pipeline_run(
    body: PipelineRunRequest,
    background: BackgroundTasks,
    principal: Annotated[Principal, Depends(authorize("POST /pipeline/run"))],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    runner: Annotated[PipelineRunner, Depends(get_pipeline_runner)],
) -> PipelineRunAccepted:
    run_id, handle = pipeline_service.request_run(
        session, settings, runner,
        actor=Actor(principal.actor_type, principal.actor_id),
        nightly=principal.api_key is not None,
        scope=body.scope, profile=body.profile, as_of=body.as_of,
    )  # fmt: skip
    if handle is not None:
        background.add_task(runner.execute, handle)
    return PipelineRunAccepted(pipeline_run_id=run_id)


@router.get(
    "/runs",
    response_model=PipelineRunList,
    operation_id="listPipelineRuns",
    responses=errors(401, 403, 422),
)
def list_pipeline_runs(
    _: Annotated[Principal, Depends(authorize("GET /pipeline/runs"))],
    session: Annotated[Session, Depends(get_db)],
    meta: Annotated[Meta, Depends(get_meta)],
    page: Annotated[Pagination, Depends(get_pagination)],
    trigger: Annotated[PipelineTrigger | None, Query()] = None,
    run_status: Annotated[PipelineStatus | None, Query(alias="status")] = None,
) -> PipelineRunList:
    runs, total = pipeline_service.list_runs(
        session, trigger=trigger, status=run_status, limit=page.limit, offset=page.offset
    )
    return PipelineRunList(
        meta=meta, total=total, limit=page.limit, offset=page.offset,
        items=[PipelineRun.model_validate(pipeline_service.run_dto(r)) for r in runs],
    )  # fmt: skip


@router.get(
    "/runs/{id}",
    response_model=PipelineRun,
    operation_id="getPipelineRun",
    responses=errors(401, 403, 404),
)
def get_pipeline_run(
    id: uuid.UUID,
    _: Annotated[Principal, Depends(authorize("GET /pipeline/runs/{id}"))],
    session: Annotated[Session, Depends(get_db)],
) -> PipelineRun:
    run = pipeline_service.get_run(session, id)
    if run is None:
        raise PipelineRunNotFoundError("No pipeline run with this id.")
    return PipelineRun.model_validate(pipeline_service.run_dto(run))
