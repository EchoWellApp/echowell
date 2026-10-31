"""Nightly pipeline entry point: `python -m backend.jobs.nightly_run` (TRD 07 ANL-045; TRD 05
API-060..API-062; TRD 15 DEP-046..DEP-048; TRD 24 D-47, D-70; FEAT-054, FEAT-056).

The external cron (`0 7,8 * * *` UTC) fires twice a day; exactly one firing lands in the
facility-local hour `NIGHTLY_RUN_HOUR_LOCAL` (02:xx) whatever the DST state, so the job:

1. exits 1 when the database schema revision is not the one bundled with this code (it never
   runs migrations, DEP-048); the app role cannot read `alembic_version`, so this check
   currently only warns `schema_revision_unreadable`;
2. exits 0 outside that local hour, after checking that the previous night's run exists
   (`nightly_run_missing`, LOG-111);
3. inside it, takes `pg_advisory_xact_lock(advisory_key('nightly', <local date>))`, exits 0 when
   a nightly run of that local date is already running or succeeded (D-70), and otherwise inserts
   the run row in that same transaction;
4. runs the full pipeline (`scope = all`, `trigger = nightly`) and exits 1 when the run fails.

There is no in-process scheduler (AGT-059).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from backend.core import db
from backend.core.config import Settings, load_settings_or_exit
from backend.core.logging import configure_logging
from backend.models import PipelineRunStatus, PipelineTrigger
from backend.services.pipeline_runner import PipelineRunner, nightly_run_for_local_date

logger = logging.getLogger("backend.jobs.nightly_run")
Clock = Callable[[], datetime]
ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def bundled_revision() -> str:
    script = ScriptDirectory.from_config(Config(str(ALEMBIC_INI)))
    head = script.get_current_head()
    assert head is not None  # noqa: S101 - the repository has migrations
    return head


UNREADABLE = "unreadable"


def database_revision(session_factory: Callable[[], Session]) -> str | None:
    """The applied revision, or `UNREADABLE` when the app role may not read `alembic_version`
    (TRD 20 §4.8 grants it nothing; see the checkpoint 5 report, Q-1)."""
    with session_factory() as session:
        try:
            return session.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one_or_none()
        except ProgrammingError:
            session.rollback()
            return UNREADABLE


def last_due_night(local: datetime, hour: int) -> date:
    """The latest facility-local date whose nightly hour has fully passed."""
    return local.date() if local.hour > hour else local.date() - timedelta(days=1)


def check_missing(session: Session, local: datetime, settings: Settings) -> bool:
    """ERROR `nightly_run_missing` when the last due night has no succeeded run (LOG-111)."""
    night = last_due_night(local, settings.nightly_run_hour_local)
    run = nightly_run_for_local_date(session, night, ZoneInfo(settings.facility_tz))
    if run is None or run.status != PipelineRunStatus.SUCCEEDED:
        logger.error("nightly_run_missing", extra={"local_date": night.isoformat()})
        return True
    return False


def run_night(
    settings: Settings,
    session_factory: Callable[[], Session],
    clock: Clock | None = None,
    runner: PipelineRunner | None = None,
) -> int:
    now = (clock or (lambda: datetime.now(UTC)))()
    zone = ZoneInfo(settings.facility_tz)
    local = now.astimezone(zone)
    runner = runner or PipelineRunner(session_factory, settings, clock=clock)
    found = database_revision(session_factory)
    if found == UNREADABLE:
        logger.warning("schema_revision_unreadable")
    elif found != bundled_revision():
        logger.error("schema_revision_mismatch", extra={"database": found})
        return 1
    with session_factory() as session:
        if local.hour != settings.nightly_run_hour_local:
            check_missing(session, local, settings)
            return 0
    with session_factory() as session, session.begin():
        db.lock_xact(session, "nightly", local.date().isoformat())
        if (
            nightly_run_for_local_date(session, local.date(), ZoneInfo(settings.facility_tz))
            is not None
        ):
            logger.info("nightly_run_skipped", extra={"local_date": local.date().isoformat()})
            check_missing(session, local, settings)
            return 0
        handle = runner.start("all", PipelineTrigger.NIGHTLY, session=session)
    status = runner.execute(handle)
    return 0 if status == PipelineRunStatus.SUCCEEDED else 1


def main() -> int:
    settings = load_settings_or_exit()
    configure_logging(settings.log_level, settings.log_format, settings.app_env, settings.git_sha)
    engine = db.create_engine_for(settings.database_url, app_env=settings.app_env)
    try:
        return run_night(settings, db.session_factory(engine))
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
