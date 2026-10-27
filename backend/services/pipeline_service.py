"""Operator endpoints of the pipeline (TRD 05 API-065..API-067, API-134; TRD 19 E-20, E-21, E-31;
FEAT-024)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from backend.core.config import Settings
from backend.core.errors import PipelineRunInProgressError, ResidentNotFoundError
from backend.models import PipelineRun, PipelineRunStatus, PipelineTrigger
from backend.repositories.pipeline_run_repository import PipelineRunRepository
from backend.repositories.resident_repository import ResidentRepository
from backend.services.pipeline_runner import (
    Actor,
    PipelineRunner,
    RunHandle,
    Scope,
    check_profile,
    full_run_in_progress,
    nightly_run_for_local_date,
    scope_from_value,
)


def request_run(
    session: Session,
    settings: Settings,
    runner: PipelineRunner,
    *,
    actor: Actor,
    nightly: bool,
    scope: Scope,
    profile: str | None,
    as_of: datetime | None,
) -> tuple[uuid.UUID, RunHandle | None]:
    """Validate and start a run; the caller executes the handle in the background.

    A `pipeline:run` key always runs a nightly full run, once per facility-local date (D-70);
    an admin runs `manual` with the requested scope.
    """
    profile = profile or settings.pipeline_profile
    check_profile(profile, settings)  # 422 PROFILE_NOT_ALLOWED (API-066)
    if nightly:
        scope = "all"
        tz = ZoneInfo(settings.facility_tz)
        existing = nightly_run_for_local_date(session, runner.clock().astimezone(tz).date(), tz)
        if existing is not None:
            return existing.id, None
    elif scope != "all":
        known = {r.resident_code for r in ResidentRepository(session).list_all()}
        unknown = sorted(set(scope) - known)
        if unknown:
            raise ResidentNotFoundError(f"Unknown resident code(s): {', '.join(unknown)}.")
    if full_run_in_progress(session) is not None:
        raise PipelineRunInProgressError("A full pipeline run is in progress. Try again later.")
    trigger = PipelineTrigger.NIGHTLY if nightly else PipelineTrigger.MANUAL
    handle = runner.start(scope, trigger, profile, as_of, actor)
    return handle.id, handle


def run_dto(run: PipelineRun) -> dict[str, Any]:
    """The `PipelineRun` DTO (TRD 19): scope as `"all"` or a list of resident codes."""
    return {
        "id": run.id,
        "trigger": run.trigger.value,
        "scope": scope_from_value(run.scope),
        "config_profile": run.config_profile,
        "code_version": run.code_version,
        "as_of": run.as_of,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "status": run.status.value,
        "counts": dict(run.counts or {}),
        "warnings": list(run.warnings or []),
    }


def get_run(session: Session, run_id: uuid.UUID) -> PipelineRun | None:
    return PipelineRunRepository(session).get(run_id)


def list_runs(
    session: Session,
    *,
    trigger: str | None,
    status: str | None,
    limit: int,
    offset: int,
) -> tuple[list[PipelineRun], int]:
    """Runs newest first (API-134)."""
    return PipelineRunRepository(session).list_page(
        trigger=PipelineTrigger(trigger) if trigger else None,
        status=PipelineRunStatus(status) if status else None,
        limit=limit,
        offset=offset,
    )
