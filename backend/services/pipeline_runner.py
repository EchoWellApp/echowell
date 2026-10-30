"""The one door of every pipeline execution (TRD 05 API-063..API-069, API-135; TRD 07 ARC-060;
FEAT-024).

`PipelineRunner.start()` marks abandoned runs, resolves `as_of`, checks the profile, inserts the
`running` row with its config snapshot and writes `pipeline.run.started`, in its own committed
transaction; `execute()` calls the stage executor and finishes the row (`succeeded` with counts,
or `failed` with `error_message`) and writes `pipeline.run.finished`. `run()` does both.

The stage executor is pluggable (`Executor`). Until FEAT-053 (Phase 6) the default
`InterimExecutor` fails every run with "pipeline not available until Phase 6", so ingest answers
`status_after_processing = "pending"` (TRD 24 D-52, D-91). This module takes no advisory lock;
the executor locks residents per transaction (API-064).
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal, Protocol
from zoneinfo import ZoneInfo

from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session
from sqlalchemy.types import Date

from backend.core.config import Settings
from backend.core.errors import ProfileNotAllowedError
from backend.core.logging import bound, format_exception, mask_text
from backend.models import ActorType, PipelineRun, PipelineRunStatus, PipelineTrigger
from backend.repositories.config_repository import ConfigRepository
from backend.repositories.pipeline_run_repository import PipelineRunRepository
from backend.services import audit_service
from backend.services.audit_service import AuditAction

logger = logging.getLogger("backend.pipeline")

Scope = Literal["all"] | Sequence[str]
SessionFactory = Callable[[], Session]
Clock = Callable[[], datetime]

ABANDON_AFTER = timedelta(minutes=30)
INTERIM_MESSAGE = "pipeline not available until Phase 6"


@dataclass(frozen=True)
class RunHandle:
    """A started run, as handed to the executor."""

    id: uuid.UUID
    trigger: PipelineTrigger
    scope: Scope
    profile: str
    as_of: datetime
    config: Mapping[str, Any]


@dataclass(frozen=True)
class ExecutorResult:
    counts: dict[str, int]
    warnings: list[dict[str, Any]] = field(default_factory=list)


class Executor(Protocol):
    def execute(self, session_factory: SessionFactory, run: RunHandle) -> ExecutorResult: ...


class PipelineUnavailableError(RuntimeError):
    pass


class InterimExecutor:
    """Fails every run until the analytics executor exists (FEAT-024 scope; D-91)."""

    def execute(self, session_factory: SessionFactory, run: RunHandle) -> ExecutorResult:
        raise PipelineUnavailableError(INTERIM_MESSAGE)


def scope_value(scope: Scope) -> dict[str, Any]:
    """The `pipeline_runs.scope` JSON (TRD 23 §4.5)."""
    if scope == "all":
        return {"type": "all"}
    return {"type": "residents", "resident_codes": sorted(set(scope))}


def scope_from_value(value: Mapping[str, Any]) -> Scope:
    """`"all"` or the list of resident codes, as in the `PipelineRun` DTO (TRD 19)."""
    return "all" if value.get("type") == "all" else list(value.get("resident_codes", []))


def resolve_as_of(explicit: datetime | None, settings: Settings, clock: Clock) -> datetime:
    """Explicit `as_of` → PIPELINE_AS_OF (never in production) → current time (API-135, D-50)."""
    if explicit is not None:
        return explicit.astimezone(UTC)
    if settings.pipeline_as_of and settings.app_env != "production":
        return datetime.fromisoformat(settings.pipeline_as_of).astimezone(UTC)
    return clock().astimezone(UTC)


def check_profile(profile: str, settings: Settings) -> None:
    """Production runs only its own PIPELINE_PROFILE, never `test_v0_1` (API-066)."""
    if settings.app_env == "production" and (
        profile == "test_v0_1" or profile != settings.pipeline_profile
    ):
        raise ProfileNotAllowedError(f"Profile {profile} is not allowed in production.")


def config_snapshot(values: Mapping[str, Any], as_of: datetime) -> dict[str, Any]:
    """The 23 keys plus `config_hash` and `as_of` (DB-020). The hash covers all 23 keys until
    FEAT-052 supplies `PipelineConfig.config_hash()`."""
    canonical = json.dumps(dict(values), sort_keys=True, separators=(",", ":"))
    return {
        **dict(values),
        "config_hash": hashlib.sha256(canonical.encode()).hexdigest(),
        "as_of": as_of.isoformat(),
    }


def abandon_stale_runs(session: Session, now: datetime) -> list[uuid.UUID]:
    """Mark runs `running` for more than 30 minutes as failed (API-068, LOG-066)."""
    stale = session.scalars(
        select(PipelineRun).where(
            PipelineRun.status == PipelineRunStatus.RUNNING,
            PipelineRun.started_at < now - ABANDON_AFTER,
        )
    ).all()
    repository = PipelineRunRepository(session)
    for run in stale:
        warning = {
            "code": "run_abandoned", "resident_code": None, "session_id": None,
            "detail": "still running 30 minutes after it started",
        }  # fmt: skip
        repository.finish(
            run, status=PipelineRunStatus.FAILED, finished_at=now,
            warnings=[*(run.warnings or []), warning],
            error_message="Run abandoned: still running 30 minutes after it started.",
        )  # fmt: skip
        logger.warning("pipeline_run_abandoned", extra={"pipeline_run_id": str(run.id)})
    return [run.id for run in stale]


def full_run_in_progress(session: Session) -> PipelineRun | None:
    """A `running` run of scope `all` (409 PIPELINE_RUN_IN_PROGRESS, API-065)."""
    return session.scalars(
        select(PipelineRun).where(
            PipelineRun.status == PipelineRunStatus.RUNNING,
            PipelineRun.scope["type"].astext == "all",
        )
    ).first()


def nightly_run_for_local_date(session: Session, day: date, tz: ZoneInfo) -> PipelineRun | None:
    """The nightly run (`running` or `succeeded`) started on facility-local `day` (D-70)."""
    local_day = cast(func.timezone(tz.key, PipelineRun.started_at), Date)
    return session.scalars(
        select(PipelineRun)
        .where(
            PipelineRun.trigger == PipelineTrigger.NIGHTLY,
            PipelineRun.status.in_([PipelineRunStatus.RUNNING, PipelineRunStatus.SUCCEEDED]),
            local_day == day,
        )
        .order_by(PipelineRun.started_at)
    ).first()


@dataclass(frozen=True)
class Actor:
    type: ActorType = ActorType.SYSTEM
    id: str | None = None


class PipelineRunner:
    def __init__(
        self,
        session_factory: SessionFactory,
        settings: Settings,
        executor: Executor | None = None,
        clock: Clock | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.executor = executor or InterimExecutor()
        self.clock = clock or (lambda: datetime.now(UTC))

    def start(
        self,
        scope: Scope,
        trigger: PipelineTrigger,
        profile: str | None = None,
        as_of: datetime | None = None,
        actor: Actor | None = None,
        session: Session | None = None,
    ) -> RunHandle:
        """Insert the `running` row and write `pipeline.run.started`: committed on its own, or
        in `session` when given (a batch ingest records the run id in its own transaction)."""
        profile = profile or self.settings.pipeline_profile
        check_profile(profile, self.settings)
        if session is not None:
            return self._start(session, scope, trigger, profile, as_of, actor or Actor())
        with self.session_factory() as own, own.begin():
            return self._start(own, scope, trigger, profile, as_of, actor or Actor())

    def _start(
        self,
        session: Session,
        scope: Scope,
        trigger: PipelineTrigger,
        profile: str,
        as_of: datetime | None,
        actor: Actor,
    ) -> RunHandle:
        resolved = resolve_as_of(as_of, self.settings, self.clock)
        abandon_stale_runs(session, self.clock())
        values = ConfigRepository(session).values_for_profile(profile)
        snapshot = config_snapshot(values, resolved)
        run = PipelineRunRepository(session).insert_running(
            trigger=trigger, scope=scope_value(scope), config_profile=profile,
            config_snapshot=snapshot, code_version=self.settings.git_sha, as_of=resolved,
        )  # fmt: skip
        audit_service.record(
            session, action=AuditAction.PIPELINE_RUN_STARTED, actor_type=actor.type,
            actor_id=actor.id, entity_type="pipeline_run", entity_id=str(run.id),
            details={"trigger": trigger.value, "scope": run.scope, "profile": profile},
        )  # fmt: skip
        handle = RunHandle(run.id, trigger, scope, profile, resolved, snapshot)
        logger.info(
            "pipeline_run_started",
            extra={"pipeline_run_id": str(handle.id), "trigger": trigger.value},
        )
        return handle

    def execute(self, handle: RunHandle) -> PipelineRunStatus:
        """Run the executor and finish the row; never raises for an executor failure."""
        started = time.monotonic()
        with bound(pipeline_run_id=str(handle.id)):
            try:
                result: ExecutorResult | None = self.executor.execute(self.session_factory, handle)
                error = None
            except Exception as exc:  # the run is recorded failed (API-047, D-52)
                result, error = None, exc
                logger.error(
                    "pipeline_run_failed",
                    extra={
                        "exc_type": type(exc).__name__,
                        "exc_message": mask_text(str(exc))[:200],
                        "stack": format_exception(exc),
                    },
                )
            status = PipelineRunStatus.SUCCEEDED if error is None else PipelineRunStatus.FAILED
            duration_ms = round((time.monotonic() - started) * 1000)
            with self.session_factory() as session, session.begin():
                run = PipelineRunRepository(session).get(handle.id)
                assert run is not None  # noqa: S101 - inserted by start()
                warnings = list(result.warnings) if result else list(run.warnings or [])
                PipelineRunRepository(session).finish(
                    run, status=status, finished_at=self.clock(),
                    counts=result.counts if result else None, warnings=warnings,
                    error_message=None if error is None else (str(error) or type(error).__name__),
                )  # fmt: skip
                audit_service.record(
                    session, action=AuditAction.PIPELINE_RUN_FINISHED,
                    actor_type=ActorType.SYSTEM, actor_id=None, entity_type="pipeline_run",
                    entity_id=str(handle.id),
                    details={"status": status.value, "duration_ms": duration_ms,
                             "warning_count": len(warnings)},
                )  # fmt: skip
            logger.info(
                "pipeline_run_finished",
                extra={"status": status.value, "duration_ms": duration_ms},
            )
        return status

    def run(
        self,
        scope: Scope,
        trigger: PipelineTrigger,
        profile: str | None = None,
        as_of: datetime | None = None,
        actor: Actor | None = None,
    ) -> tuple[RunHandle, PipelineRunStatus]:
        """`start()` then `execute()` in the caller's thread (ingest, CLI, tests)."""
        handle = self.start(scope, trigger, profile, as_of, actor)
        return handle, self.execute(handle)
