"""The one door of every pipeline execution (TRD 05 API-063..API-069, API-135; TRD 07 ARC-060;
FEAT-024).

`PipelineRunner.start()` marks abandoned runs, resolves `as_of`, checks the profile, inserts the
`running` row with its config snapshot and writes `pipeline.run.started`, in its own committed
transaction; `execute()` calls the stage executor and finishes the row (`succeeded` with counts,
or `failed` with `error_message`) and writes `pipeline.run.finished`. `run()` does both.

The stage executor is pluggable (`Executor`); the default is `AnalyticsExecutor` (FEAT-053),
which calls `analytics.run_pipeline` and writes one transaction per resident under that
resident's advisory lock (API-064). `InterimExecutor`, which fails every run with "pipeline not
available until Phase 6" (checkpoint 4, D-52, D-91), remains for tests of the failure path.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal, Protocol
from zoneinfo import ZoneInfo

from sqlalchemy import cast, func, select, text
from sqlalchemy.orm import Session
from sqlalchemy.types import Date

from analytics import run_pipeline
from analytics.config import ConfigError
from backend.core.config import Settings
from backend.core.db import lock_xact
from backend.core.errors import ProfileNotAllowedError
from backend.core.logging import bound, format_exception, mask_text
from backend.models import ActorType, PipelineRun, PipelineRunStatus, PipelineTrigger
from backend.repositories.config_repository import ConfigRepository
from backend.repositories.pipeline_run_repository import PipelineRunRepository
from backend.services import audit_service, config_service, pipeline_persistence
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
    rebuild: bool = False


@dataclass(frozen=True)
class ExecutorResult:
    counts: dict[str, int]
    warnings: list[dict[str, Any]] = field(default_factory=list)


class Executor(Protocol):
    def execute(self, session_factory: SessionFactory, run: RunHandle) -> ExecutorResult: ...


class PipelineUnavailableError(RuntimeError):
    pass


class RunFailedError(RuntimeError):
    """A run that ends `failed` with its counts and warnings kept (ANL-041)."""

    def __init__(
        self, message: str, counts: dict[str, int] | None = None,
        warnings: list[dict[str, Any]] | None = None,
    ) -> None:  # fmt: skip
        super().__init__(message)
        self.counts = counts
        self.warnings = warnings or []


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


def config_snapshot(values: Mapping[str, Any], as_of: datetime, profile: str) -> dict[str, Any]:
    """The 23 keys plus `config_hash` and `as_of` (DB-020). The hash is
    `PipelineConfig.config_hash()` (algorithm keys only, D-56); when the stored values are invalid
    it falls back to a hash of the raw values, and the run then fails with
    `pipeline_config_invalid`."""
    try:
        config_hash = config_service.pipeline_config(values, profile)[0].config_hash()
    except ConfigError:
        canonical = json.dumps(dict(values), sort_keys=True, separators=(",", ":"))
        config_hash = hashlib.sha256(canonical.encode()).hexdigest()
    return {**dict(values), "config_hash": config_hash, "as_of": as_of.isoformat()}


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
        self.executor = executor or AnalyticsExecutor(settings)
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
        snapshot = config_snapshot(values, resolved, profile)
        run = PipelineRunRepository(session).insert_running(
            trigger=trigger, scope=scope_value(scope), config_profile=profile,
            config_snapshot=snapshot, code_version=self.settings.git_sha, as_of=resolved,
            started_at=self.clock(),
        )  # fmt: skip
        audit_service.record(
            session, action=AuditAction.PIPELINE_RUN_STARTED, actor_type=actor.type,
            actor_id=actor.id, entity_type="pipeline_run", entity_id=str(run.id),
            details={"trigger": trigger.value, "scope": run.scope, "profile": profile},
        )  # fmt: skip
        handle = RunHandle(run.id, trigger, scope, profile, resolved, snapshot)
        logger.info("pipeline_run_started", extra={
            "pipeline_run_id": str(handle.id), "trigger": trigger.value,
            "scope": run.scope, "profile": profile, "config_hash": snapshot["config_hash"],
        })  # fmt: skip
        return handle

    def execute(self, handle: RunHandle) -> PipelineRunStatus:
        """Run the executor and finish the row; never raises for an executor failure.

        Logs `pipeline_run_succeeded` (INFO) or `pipeline_run_failed` (ERROR) and one
        `pipeline_warning` per warning (ANL-053, LOG-061..LOG-065, D-80)."""
        started = time.monotonic()
        with bound(pipeline_run_id=str(handle.id)):
            counts: dict[str, int] | None = None
            warnings: list[dict[str, Any]] = []
            error: Exception | None = None
            try:
                result = self.executor.execute(self.session_factory, handle)
                counts, warnings = result.counts, list(result.warnings)
            except RunFailedError as exc:
                error, counts, warnings = exc, exc.counts, list(exc.warnings)
            except Exception as exc:  # the run is recorded failed (API-047, D-52)
                error = exc
                detail = f"{type(exc).__name__}: {mask_text(str(exc))[:200]}"
                warnings = [_warning("exception", None, detail)]
            status = PipelineRunStatus.SUCCEEDED if error is None else PipelineRunStatus.FAILED
            duration_ms = round((time.monotonic() - started) * 1000)
            with self.session_factory() as session, session.begin():
                run = PipelineRunRepository(session).get(handle.id)
                assert run is not None  # noqa: S101 - inserted by start()
                warnings = [*(run.warnings or []), *warnings]
                PipelineRunRepository(session).finish(
                    run, status=status, finished_at=self.clock(), counts=counts,
                    warnings=warnings,
                    error_message=None if error is None else (str(error) or type(error).__name__),
                )  # fmt: skip
                audit_service.record(
                    session, action=AuditAction.PIPELINE_RUN_FINISHED,
                    actor_type=ActorType.SYSTEM, actor_id=None, entity_type="pipeline_run",
                    entity_id=str(handle.id),
                    details={"status": status.value, "duration_ms": duration_ms,
                             "warning_count": len(warnings)},
                )  # fmt: skip
            for warning in warnings:
                level = logging.ERROR if warning["code"] == "baseline_mismatch" else logging.WARNING
                logger.log(level, "pipeline_warning", extra={
                    "code": warning["code"], "resident_code": warning.get("resident_code"),
                    "session_id": warning.get("session_id"),
                })  # fmt: skip
            fields = {
                "trigger": handle.trigger.value, "scope": scope_value(handle.scope),
                "profile": handle.profile, "config_hash": handle.config.get("config_hash"),
                "duration_ms": duration_ms, "counts": counts or {},
                "warning_count": len(warnings),
            }  # fmt: skip
            if error is None:
                logger.info("pipeline_run_succeeded", extra=fields)
            else:
                logger.error("pipeline_run_failed", extra={
                    **fields, "exc_type": type(error).__name__,
                    "exc_message": mask_text(str(error))[:200],
                    "stack": "" if isinstance(error, RunFailedError) else format_exception(error),
                })  # fmt: skip
        return status

    def run(
        self,
        scope: Scope,
        trigger: PipelineTrigger,
        profile: str | None = None,
        as_of: datetime | None = None,
        actor: Actor | None = None,
        rebuild: bool = False,
    ) -> tuple[RunHandle, PipelineRunStatus]:
        """`start()` then `execute()` in the caller's thread (ingest, CLI, tests)."""
        handle = self.start(scope, trigger, profile, as_of, actor)
        if rebuild:
            handle = replace(handle, rebuild=True)
        return handle, self.execute(handle)


# --- the analytics executor (FEAT-053) ----------------------------------------------------------

CONFIG_CHANGED = "configuration changed; run the rebuild command"


def _warning(
    code: str, resident: str | None, detail: str, session_id: str | None = None
) -> dict[str, Any]:
    return {"code": code, "resident_code": resident, "session_id": session_id, "detail": detail}


class AnalyticsExecutor:
    """Load → `analytics.run_pipeline` → write, one transaction per resident (TRD 07 §4.8).

    This is the backend's only caller of `run_pipeline` (API-006). A resident whose write fails
    is rolled back alone and the run ends `failed` naming it (ANL-041); an epoch renumbering that
    would touch a frozen baseline leaves that resident unchanged with a `late_arrival` warning
    (ANL-038). `rebuild` (operator command only) deletes each resident's baselines inside its
    transaction and needs the migrator connection (ANL-032, DB-009).
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def execute(self, session_factory: SessionFactory, run: RunHandle) -> ExecutorResult:
        values = {k: v for k, v in run.config.items() if k not in ("config_hash", "as_of")}
        try:
            config, warnings = config_service.pipeline_config(
                values, run.profile, self.settings.facility_tz
            )
        except ConfigError as exc:
            raise RunFailedError(
                f"invalid configuration: {exc}",
                warnings=[_warning("pipeline_config_invalid", None, str(exc))],
            ) from None
        with session_factory() as session:
            latest = PipelineRunRepository(session).latest_succeeded(run.profile)
            previous = (latest.config_snapshot or {}).get("config_hash") if latest else None
            if previous and previous != config.config_hash() and not run.rebuild:
                raise RunFailedError(
                    CONFIG_CHANGED,
                    warnings=[_warning("config_changed_requires_rebuild", None, CONFIG_CHANGED)],
                )
            inputs = pipeline_persistence.load_inputs(session, run.scope)
        frozen = {} if run.rebuild else inputs.frozen
        result = run_pipeline(inputs.records, inputs.residents, inputs.assignments, config,
                              run.as_of, frozen_baselines=frozen)  # fmt: skip
        warnings += [_warning(w.code, w.resident_code, w.detail, w.session_id)
                     for w in result.warnings]  # fmt: skip
        context = pipeline_persistence.RunContext(run.id, run.as_of)
        failed = []
        for code in inputs.scope:
            try:
                with session_factory() as session, session.begin():
                    lock_xact(session, "resident", code)
                    if run.rebuild:
                        pipeline_persistence.delete_baselines(session, inputs.resident_ids[code])
                    warnings += pipeline_persistence.write_resident(
                        session, code, result, inputs, context
                    )
            except pipeline_persistence.EpochRenumberingBlockedError:
                warnings.append(_warning("late_arrival", code, "epoch renumbering blocked"))
            except Exception as exc:  # one resident's failure never rolls back another (DB-013)
                failed.append(code)
                warnings.append(_warning(
                    "exception", code, f"persistence: {type(exc).__name__}: "
                    f"{mask_text(str(exc))[:200]}",
                ))  # fmt: skip
                logger.error(
                    "pipeline_resident_failed",
                    extra={"resident_code": code, "stack": format_exception(exc)},
                )
        devices = sorted({
            a.device_code for a in inputs.assignments
            if run.scope == "all" or a.resident_code in inputs.scope
        })  # fmt: skip
        with session_factory() as session, session.begin():
            lock_xact(session, "device_alerts", "all")
            pipeline_persistence.reconcile_device_alerts(session, result, inputs, devices, context)
        _log_data_alerts(result)
        counts = dict(result.counts)
        if run.trigger == PipelineTrigger.NIGHTLY:
            with session_factory() as session:
                counts["db_size_bytes"] = int(session.execute(
                    text("SELECT pg_database_size(current_database())")).scalar_one())  # fmt: skip
        if failed:
            raise RunFailedError(f"failed residents: {', '.join(failed)}", counts, warnings)
        return ExecutorResult(counts, warnings)


def _log_data_alerts(result: Any) -> None:
    """One INFO `data_alerts_updated` with the open count per kind (LOG-115)."""
    open_by_kind: dict[str, int] = {}
    for alert in result.data_alerts:
        open_by_kind[alert.kind] = open_by_kind.get(alert.kind, 0) + 1
    logger.info("data_alerts_updated", extra={"open": open_by_kind})
