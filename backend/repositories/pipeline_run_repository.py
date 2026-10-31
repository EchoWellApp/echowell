"""Pipeline runs (TRD 23 §4.2.10; TRD 06 DB-020; FEAT-011).

JSON columns are validated against the TRD 23 §4.5 shapes before insert (FEAT-011-FR-12).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import PipelineRun, PipelineRunStatus, PipelineTrigger
from backend.schemas.json_columns import (
    config_snapshot_json,
    counts_json,
    scope_json,
    warnings_json,
)


class PipelineRunRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, run_id: uuid.UUID) -> PipelineRun | None:
        return self.session.get(PipelineRun, run_id)

    def insert_running(
        self,
        *,
        trigger: PipelineTrigger,
        scope: dict[str, Any],
        config_profile: str,
        config_snapshot: dict[str, Any],
        code_version: str,
        as_of: datetime,
        started_at: datetime | None = None,
    ) -> PipelineRun:
        run = PipelineRun(
            trigger=trigger,
            scope=scope_json(scope),
            config_profile=config_profile,
            config_snapshot=config_snapshot_json(config_snapshot),
            code_version=code_version,
            as_of=as_of,
        )
        if started_at is not None:  # the application clock (TRD 23 DME-022)
            run.started_at = started_at
        self.session.add(run)
        self.session.flush()
        return run

    def finish(
        self,
        run: PipelineRun,
        *,
        status: PipelineRunStatus,
        finished_at: datetime,
        counts: dict[str, int] | None = None,
        warnings: list[dict[str, Any]] | None = None,
        error_message: str | None = None,
    ) -> PipelineRun:
        """Mark a running run succeeded or failed (`pipeline_runs_finished_ck`, `_error_ck`)."""
        if status == PipelineRunStatus.RUNNING:
            raise ValueError("finish() needs status succeeded or failed")
        run.status = status
        run.finished_at = finished_at
        if counts is not None:
            run.counts = counts_json(counts)
        if warnings is not None:
            run.warnings = warnings_json(warnings)
        run.error_message = error_message
        self.session.flush()
        return run

    def latest_succeeded(self, config_profile: str | None = None) -> PipelineRun | None:
        """Latest succeeded run by `started_at`; its `as_of` is the API as-of (contract R21)."""
        query = select(PipelineRun).where(PipelineRun.status == PipelineRunStatus.SUCCEEDED)
        if config_profile is not None:
            query = query.where(PipelineRun.config_profile == config_profile)
        return self.session.scalars(query.order_by(PipelineRun.started_at.desc()).limit(1)).first()

    def list_page(
        self,
        *,
        trigger: PipelineTrigger | None = None,
        status: PipelineRunStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[PipelineRun], int]:
        """Runs newest first with optional filters and the total count."""
        query = select(PipelineRun)
        if trigger is not None:
            query = query.where(PipelineRun.trigger == trigger)
        if status is not None:
            query = query.where(PipelineRun.status == status)
        total = self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        rows = self.session.scalars(
            query.order_by(PipelineRun.started_at.desc()).limit(limit).offset(offset)
        ).all()
        return list(rows), total
