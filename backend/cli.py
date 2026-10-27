"""Operator command line: `python -m backend.cli <command>` (TRD 15 §4.8; TRD 21 ENV-053).

Commands of FEAT-016 (credentials), FEAT-017 (master data, withdrawal, purge, seed, reset),
FEAT-032 (`resolve-data-alert`) and FEAT-038 (`export-openapi`); `run-pipeline`, `rebuild` and
`set-config` follow with their features. Exit codes (TRD 24 D-86): 0 success; 1 invalid settings
(ENV-002, checked by `load_settings_or_exit`); 2 a command-specific refusal, which prints the
reason and writes nothing.
RefusalErrors that depend only on the environment are checked before the settings are built.

Connections: `seed`, `reset-test-db` and `purge-resident` run as `echowell_migrator` through
DATABASE_MIGRATION_URL (TRD 20 §4.3 closed list); the other commands use the app role
(DATABASE_URL). Secrets are never printed or logged; `create-api-key` prints the new key once.
"""

from __future__ import annotations

import argparse
import csv
import getpass
import json
import sys
import uuid
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import ColumnElement, delete, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.core.config import Settings, environment_value, load_settings_or_exit
from backend.core.db import create_engine_for, migrator_connection
from backend.core.errors import PasswordPolicyError
from backend.core.security import (
    generate_api_key,
    hash_api_key,
    hash_password,
    normalise_email,
    validate_password,
)
from backend.models import (
    Alert,
    AlertReview,
    Base,
    Baseline,
    CusumState,
    DataAlert,
    DayLedgerEntry,
    DeviceAssignment,
    Epoch,
    ProcessedSession,
    RawSession,
    Resident,
    ResidentCohort,
    ResidentStatus,
    Score,
    StaffNote,
    UserRole,
)
from backend.repositories.api_key_repository import ApiKeyRepository
from backend.repositories.config_repository import CONFIG_KEYS, ConfigRepository
from backend.repositories.device_repository import DeviceRepository
from backend.repositories.facility_repository import FacilityRepository
from backend.repositories.resident_repository import ResidentRepository
from backend.repositories.user_repository import UserRepository
from backend.services import data_alert_service
from backend.services.audit_service import AuditAction, record_cli

ROOT = Path(__file__).resolve().parents[1]
TEST_ROSTER_DIR = ROOT / "database" / "seeds" / "test_v0_1"
API_KEY_SCOPES = ("ingest:write", "pipeline:run")
SEED_USERS = (
    ("admin@example.com", "Admin", UserRole.ADMIN, "SEED_ADMIN_PASSWORD"),
    ("clinician@example.com", "Clinician", UserRole.CLINICIAN, "SEED_CLINICIAN_PASSWORD"),
    ("researcher@example.com", "Researcher", UserRole.RESEARCHER, "SEED_RESEARCHER_PASSWORD"),
)
SEED_API_KEY_NAME = "test-ingest"
RESET_ENVS = ("local", "test", "staging")


class RefusalError(Exception):
    """A command-specific refusal: exit code 2, nothing written (TRD 15 §4.8, D-86)."""


@contextmanager
def app_session(settings: Settings) -> Iterator[Session]:
    """Session of the app role (DATABASE_URL), committed only by the command."""
    engine = create_engine_for(settings.database_url, app_env=settings.app_env)
    with Session(engine) as session:
        yield session


@contextmanager
def migrator_session(settings: Settings) -> Iterator[Session]:
    """Session as `echowell_migrator` (`SET ROLE` right after connecting, TRD 20 §4.3)."""
    with migrator_connection(settings) as connection, Session(bind=connection) as session:
        yield session


def _say(message: str) -> None:
    print(message, file=sys.stderr)


# --- FEAT-016: credentials -----------------------------------------------------------------


def _read_password(from_stdin: bool) -> str:
    if from_stdin:
        return sys.stdin.readline().rstrip("\r\n")
    return getpass.getpass("Password: ")


def create_user(settings: Settings, args: argparse.Namespace) -> int:
    """`create-user --email E --display-name N --role R [--password-stdin]` (SEC-017, FR-05)."""
    email = normalise_email(args.email)
    password = _read_password(args.password_stdin)
    try:
        validate_password(password, email)
    except PasswordPolicyError as exc:
        raise RefusalError(exc.detail) from None
    with app_session(settings) as session:
        users = UserRepository(session)
        if users.get_by_email(email) is not None:
            raise RefusalError(f"a user with e-mail {email} already exists")
        user = users.insert(
            email=email,
            display_name=args.display_name,
            password_hash=hash_password(password),
            role=UserRole(args.role),
        )
        record_cli(
            session,
            action=AuditAction.USER_CREATED,
            entity_type="user",
            entity_id=str(user.id),
            details={"role": user.role.value},
        )
        session.commit()
    _say(f"Created user {email} ({args.role}).")
    return 0


def create_api_key(settings: Settings, args: argparse.Namespace) -> int:
    """`create-api-key --name N [--device D] [--scope S]…`, key printed once (SEC-020..SEC-023)."""
    scopes = sorted(set(args.scope or ["ingest:write"]))
    with app_session(settings) as session:
        keys = ApiKeyRepository(session)
        existing = keys.get_by_name(args.name)
        if existing is not None and existing.active:
            raise RefusalError(f"an active API key named {args.name} already exists")
        device_id = None
        if args.device:
            device = DeviceRepository(session).get_by_code(args.device)
            if device is None:
                raise RefusalError(f"unknown device {args.device}")
            device_id = device.id
        key = generate_api_key()
        api_key = keys.insert(
            name=args.name, key_hash=hash_api_key(key), scopes=scopes, device_id=device_id
        )
        record_cli(
            session,
            action=AuditAction.API_KEY_CREATED,
            entity_type="api_key",
            entity_id=str(api_key.id),
            details={"name": args.name, "device_code": args.device},
        )
        session.commit()
    _say("New API key (shown only once; store it in the device's secret store):")
    print(key)
    return 0


def revoke_api_key(settings: Settings, args: argparse.Namespace) -> int:
    """`revoke-api-key --name N` sets `active = false` (SEC-024)."""
    with app_session(settings) as session:
        keys = ApiKeyRepository(session)
        api_key = keys.get_by_name(args.name)
        if api_key is None or not api_key.active:
            raise RefusalError(f"no active API key named {args.name}")
        keys.revoke(api_key)
        record_cli(
            session,
            action=AuditAction.API_KEY_REVOKED,
            entity_type="api_key",
            entity_id=str(api_key.id),
            details={"name": args.name},
        )
        session.commit()
    _say(f"Revoked API key {args.name}.")
    return 0


# --- FEAT-017: master data --------------------------------------------------------------------


@dataclass(frozen=True)
class RosterCounts:
    residents: int
    devices: int
    device_assignments: int


def _rows(path: Path, header: Sequence[str]) -> list[dict[str, str]]:
    if not path.is_file():
        raise RefusalError(f"{path.name} is missing in {path.parent}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(header):
            raise RefusalError(f"{path.name}: header must be {','.join(header)}")
        return list(reader)


def _optional(value: str) -> str | None:
    return value.strip() or None


def _optional_date(value: str) -> date | None:
    return date.fromisoformat(value) if value.strip() else None


def load_roster(session: Session, directory: Path) -> RosterCounts:
    """Idempotent upsert of the four roster CSV files (DB-060), in the caller's transaction."""
    facilities = _rows(directory / "facilities.csv", ("name", "timezone"))
    residents = _rows(
        directory / "residents.csv",
        ("resident_code", "sex", "cohort", "enrolled_on", "admitted_on"),
    )
    devices = _rows(
        directory / "devices.csv", ("device_code", "room_label", "active", "firmware_version_last")
    )
    assignments = _rows(
        directory / "device_assignments.csv",
        ("resident_code", "device_code", "valid_from", "valid_to"),
    )
    if len(facilities) != 1:
        raise RefusalError("facilities.csv must contain exactly one facility (ARC-105)")
    facility = FacilityRepository(session).upsert(
        facilities[0]["name"].strip(), facilities[0]["timezone"].strip()
    )
    resident_repo, device_repo = ResidentRepository(session), DeviceRepository(session)

    def each(
        name: str, rows: list[dict[str, str]], apply: Callable[[dict[str, str]], object]
    ) -> None:
        for number, row in enumerate(rows, start=2):
            try:
                with session.begin_nested():
                    apply(row)
            except (ValueError, SQLAlchemyError) as exc:
                reason = getattr(exc, "orig", exc)
                raise RefusalError(f"{name} row {number}: {reason}") from None

    each(
        "residents.csv",
        residents,
        lambda r: resident_repo.upsert_roster(
            facility_id=facility.id,
            resident_code=r["resident_code"].strip(),
            sex=_optional(r["sex"]),
            cohort=ResidentCohort(r["cohort"].strip()),
            enrolled_on=date.fromisoformat(r["enrolled_on"]),
            admitted_on=_optional_date(r["admitted_on"]),
        ),
    )
    each(
        "devices.csv",
        devices,
        lambda r: device_repo.upsert(
            facility_id=facility.id,
            device_code=r["device_code"].strip(),
            room_label=_optional(r["room_label"]),
            active=_bool(r["active"]),
            firmware_version_last=_optional(r["firmware_version_last"]),
        ),
    )

    def assign(row: dict[str, str]) -> None:
        resident = resident_repo.get_by_code(row["resident_code"].strip())
        device = device_repo.get_by_code(row["device_code"].strip())
        if resident is None or device is None:
            raise ValueError("unknown resident_code or device_code")
        device_repo.upsert_assignment(
            resident_id=resident.id,
            device_id=device.id,
            valid_from=date.fromisoformat(row["valid_from"]),
            valid_to=_optional_date(row["valid_to"]),
        )

    each("device_assignments.csv", assignments, assign)
    counts = RosterCounts(len(residents), len(devices), len(assignments))
    record_cli(
        session,
        action=AuditAction.ROSTER_LOADED,
        entity_type="facility",
        entity_id=str(facility.id),
        details={
            "residents": counts.residents,
            "devices": counts.devices,
            "device_assignments": counts.device_assignments,
        },
    )
    return counts


def _bool(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered not in ("true", "false"):
        raise ValueError(f"active must be true or false, not {value!r}")
    return lowered == "true"


def import_master_data(settings: Settings, args: argparse.Namespace) -> int:
    """`import-master-data --dir D` in one transaction with one `roster.loaded` row (DB-060)."""
    with app_session(settings) as session:
        counts = load_roster(session, Path(args.dir))
        session.commit()
    _say(
        f"Loaded {counts.residents} residents, {counts.devices} devices, "
        f"{counts.device_assignments} assignments."
    )
    return 0


def bootstrap(settings: Settings, _: argparse.Namespace) -> int:
    """Create the facility from FACILITY_NAME if missing; verify the 0002 rows (DEP-072, D-85)."""
    with app_session(settings) as session:
        facilities = FacilityRepository(session)
        if facilities.get_by_name(settings.facility_name) is None:
            facilities.upsert(settings.facility_name, settings.facility_tz)
        config = ConfigRepository(session)
        missing = [
            f"{profile}.{key}"
            for profile in ("production", "test_v0_1")
            for key in CONFIG_KEYS
            if key not in config.values_for_profile(profile)
        ]
        if missing:
            raise RefusalError(f"config_parameters rows missing: {', '.join(missing)}")
        session.commit()
    _say("Bootstrap complete.")
    return 0


def withdraw_resident(settings: Settings, args: argparse.Namespace) -> int:
    """`withdraw-resident <code> --on <date>`: one UPDATE plus `resident.withdrawn` (DB-062)."""
    on = _parse_date(args.on)
    with app_session(settings) as session:
        residents = ResidentRepository(session)
        resident = residents.get_by_code(args.resident_code)
        if resident is None:
            raise RefusalError(f"unknown resident {args.resident_code}")
        if resident.status != ResidentStatus.ACTIVE:
            raise RefusalError(f"resident {args.resident_code} is already withdrawn")
        if on < resident.enrolled_on:
            raise RefusalError("the withdrawal date is before the enrolment date")
        residents.set_withdrawn(resident, on)
        record_cli(
            session,
            action=AuditAction.RESIDENT_WITHDRAWN,
            entity_type="resident",
            entity_id=str(resident.id),
            details={"resident_code": resident.resident_code, "withdrawn_on": on.isoformat()},
        )
        session.commit()
    _say(f"Resident {args.resident_code} withdrawn on {on.isoformat()}.")
    return 0


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise RefusalError(f"{value!r} is not a date (YYYY-MM-DD)") from None


def purge_resident(settings: Settings, args: argparse.Namespace) -> int:
    """`purge-resident <code> --confirm <code>`: IRB-directed deletion (DB-064, PGS-019)."""
    if args.confirm != args.resident_code:
        raise RefusalError("--confirm must repeat the resident code")
    with migrator_session(settings) as session:
        resident = ResidentRepository(session).get_by_code(args.resident_code)
        if resident is None:
            raise RefusalError(f"unknown resident {args.resident_code}")
        if resident.status != ResidentStatus.WITHDRAWN:
            raise RefusalError(f"resident {args.resident_code} is not withdrawn")
        session.execute(text("SET LOCAL echowell.allow_purge = 'on'"))
        rid = resident.id
        alert_ids = select(Alert.id).where(Alert.resident_id == rid).scalar_subquery()
        steps: list[tuple[str, type[Base], ColumnElement[bool]]] = [
            ("scores", Score, Score.resident_id == rid),
            ("cusum_state", CusumState, CusumState.resident_id == rid),
            ("data_alerts", DataAlert, DataAlert.resident_id == rid),
            ("alert_reviews", AlertReview, AlertReview.alert_id.in_(alert_ids)),
            ("staff_notes", StaffNote, StaffNote.resident_id == rid),
            ("alerts", Alert, Alert.resident_id == rid),
            ("baselines", Baseline, Baseline.resident_id == rid),
            ("day_ledger", DayLedgerEntry, DayLedgerEntry.resident_id == rid),
            ("processed_sessions", ProcessedSession, ProcessedSession.resident_id == rid),
            ("epochs", Epoch, Epoch.resident_id == rid),
            ("raw_sessions", RawSession, RawSession.resident_id == rid),
            ("device_assignments", DeviceAssignment, DeviceAssignment.resident_id == rid),
            ("residents", Resident, Resident.id == rid),
        ]
        row_counts: dict[str, int] = {}
        for name, model, condition in steps:
            result = session.execute(delete(model).where(condition))
            row_counts[name] = int(result.rowcount or 0)
        record_cli(
            session,
            action=AuditAction.RESIDENT_PURGED,
            entity_type="resident",
            entity_id=str(rid),
            details={"resident_code": args.resident_code, "row_counts": row_counts},
        )
        session.commit()
    _say(f"Purged resident {args.resident_code}: {row_counts}.")
    return 0


# --- FEAT-017: test database seed and reset --------------------------------------------------


def _refuse_reset_environment() -> None:
    if environment_value("APP_ENV") not in RESET_ENVS:
        raise RefusalError("reset-test-db is allowed only when APP_ENV is local, test or staging")
    if environment_value("PIPELINE_PROFILE") != "test_v0_1":
        raise RefusalError("reset-test-db is allowed only with PIPELINE_PROFILE=test_v0_1")


def _reset(settings: Settings) -> None:
    """`alembic downgrade base` then `upgrade head` as the migrator; one `seed.reset` row (D-71)."""
    from alembic import command
    from alembic.config import Config

    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "backend" / "alembic"))
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    with migrator_session(settings) as session:
        record_cli(
            session,
            action=AuditAction.SEED_RESET,
            entity_type="database",
            entity_id=None,
            details={"profile": settings.pipeline_profile},
        )
        session.commit()


def reset_test_db(_: Settings, __: argparse.Namespace) -> int:
    """Handled in `main` so its refusals run before settings validation (DB-024, D-71)."""
    raise NotImplementedError


def seed(settings: Settings, args: argparse.Namespace) -> int:
    """`seed test_v0_1 [--master-only] [--reset]` (DB-056, DB-057, D-68, D-71)."""
    secrets = {
        "SEED_ADMIN_PASSWORD": settings.seed_admin_password,
        "SEED_CLINICIAN_PASSWORD": settings.seed_clinician_password,
        "SEED_RESEARCHER_PASSWORD": settings.seed_researcher_password,
        "SEED_INGEST_API_KEY": settings.seed_ingest_api_key,
    }
    missing = [name for name, value in secrets.items() if not value or not value.get_secret_value()]
    if missing:
        raise RefusalError(f"missing {', '.join(missing)}")
    if args.reset:
        _refuse_reset_environment()
        _reset(settings)
    with migrator_session(settings) as session:
        load_roster(session, TEST_ROSTER_DIR)
        users = UserRepository(session)
        for email, display_name, role, variable in SEED_USERS:
            password_hash = hash_password(secrets[variable].get_secret_value())  # type: ignore[union-attr]
            user = users.get_by_email(email)
            if user is None:
                user = users.insert(
                    email=email, display_name=display_name, password_hash=password_hash, role=role
                )
                action = AuditAction.USER_CREATED
                details: dict[str, object] = {"role": role.value}
            else:
                users.update(user, role=role, active=True, password_hash=password_hash)
                action = AuditAction.USER_UPDATED
                details = {"changed": ["password"]}
            record_cli(
                session, action=action, entity_type="user", entity_id=str(user.id), details=details
            )
        key = secrets["SEED_INGEST_API_KEY"].get_secret_value()  # type: ignore[union-attr]
        api_key = ApiKeyRepository(session).upsert_by_name(
            name=SEED_API_KEY_NAME, key_hash=hash_api_key(key), scopes=list(API_KEY_SCOPES)
        )
        record_cli(
            session,
            action=AuditAction.API_KEY_CREATED,
            entity_type="api_key",
            entity_id=str(api_key.id),
            details={"name": SEED_API_KEY_NAME, "device_code": None},
        )
        session.commit()
    if not args.master_only:
        _say("Ingesting SRC-05 and running the pipeline are added by FEAT-055 (checkpoint 5).")
    _say("Seed test_v0_1 complete.")
    return 0


# --- argument parsing --------------------------------------------------------------------------


def resolve_data_alert(settings: Settings, args: argparse.Namespace) -> int:
    """`resolve-data-alert --id <uuid> --reason "<text>"`: the only way a review-flagged data
    problem is resolved (TRD 15 §4.8, FR-297); one id per call, no `--force`."""
    try:
        data_alert_id = uuid.UUID(args.id)
    except ValueError:
        raise RefusalError(f"{args.id!r} is not a uuid") from None
    if not args.reason.strip():
        raise RefusalError("--reason must not be empty")
    with app_session(settings) as session:
        try:
            data_alert_service.resolve(session, data_alert_id, args.reason, datetime.now(UTC))
        except data_alert_service.DataAlertRefusalError as exc:
            raise RefusalError(str(exc)) from None
        session.commit()
    _say(f"Data alert {data_alert_id} resolved.")
    return 0


def export_openapi(settings: Settings, _: argparse.Namespace) -> int:
    """`export-openapi`: print the TRD 19 document as JSON, without a database connection
    (FEAT-038-FR-03, D-89)."""
    from backend.api.openapi import build_openapi
    from backend.main import create_app

    sys.stdout.write(json.dumps(build_openapi(create_app(settings)), indent=2, sort_keys=True))
    sys.stdout.write("\n")
    return 0


COMMANDS: dict[str, Callable[[Settings, argparse.Namespace], int]] = {
    "create-user": create_user,
    "create-api-key": create_api_key,
    "revoke-api-key": revoke_api_key,
    "bootstrap": bootstrap,
    "import-master-data": import_master_data,
    "withdraw-resident": withdraw_resident,
    "purge-resident": purge_resident,
    "seed": seed,
    "reset-test-db": reset_test_db,
    "resolve-data-alert": resolve_data_alert,
    "export-openapi": export_openapi,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m backend.cli", description="EchoWell operator commands (TRD 15 §4.8)."
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    p = sub.add_parser("create-user", help="create a dashboard user (password prompted)")
    p.add_argument("--email", required=True)
    p.add_argument("--display-name", required=True)
    p.add_argument("--role", required=True, choices=[r.value for r in UserRole])
    p.add_argument("--password-stdin", action="store_true", help="read the password from stdin")

    p = sub.add_parser("create-api-key", help="create an ingest/pipeline API key (printed once)")
    p.add_argument("--name", required=True)
    p.add_argument("--device", help="bind the key to this device code")
    p.add_argument("--scope", action="append", help="ingest:write (default) or pipeline:run")

    p = sub.add_parser("revoke-api-key", help="deactivate an API key")
    p.add_argument("--name", required=True)

    sub.add_parser("bootstrap", help="create the facility row and verify config_parameters")

    p = sub.add_parser("import-master-data", help="load the four roster CSV files")
    p.add_argument("--dir", required=True)

    p = sub.add_parser("withdraw-resident", help="record a resident's withdrawal")
    p.add_argument("resident_code")
    p.add_argument("--on", required=True, help="withdrawal date YYYY-MM-DD")

    p = sub.add_parser("purge-resident", help="IRB-directed deletion of a withdrawn resident")
    p.add_argument("resident_code")
    p.add_argument("--confirm", required=True, help="repeat the resident code")

    p = sub.add_parser("seed", help="seed the test_v0_1 roster, users and API key")
    p.add_argument("profile", choices=["test_v0_1"])
    p.add_argument("--master-only", action="store_true")
    p.add_argument("--reset", action="store_true", help="run reset-test-db first")

    sub.add_parser("reset-test-db", help="drop and recreate the schema (test profile only)")

    p = sub.add_parser("resolve-data-alert", help="resolve a review-flagged data problem")
    p.add_argument("--id", required=True, help="data alert id (uuid)")
    p.add_argument("--reason", required=True)

    sub.add_parser("export-openapi", help="print the OpenAPI document (no database connection)")
    return parser


def _validate_scopes(args: argparse.Namespace) -> None:
    for scope in args.scope or []:
        if scope not in API_KEY_SCOPES:
            raise RefusalError(f"unknown scope {scope} (allowed: {', '.join(API_KEY_SCOPES)})")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        # Command-specific refusals that need no settings come first (exit 2, TRD 15 §4.8).
        if args.command == "create-api-key":
            _validate_scopes(args)
        if (
            args.command in ("seed", "reset-test-db")
            and environment_value("APP_ENV") == "production"
        ):
            raise RefusalError(
                "seeding is not allowed in production"
                if args.command == "seed"
                else "reset-test-db is not allowed in production"
            )
        if args.command == "reset-test-db":
            _refuse_reset_environment()
        settings = load_settings_or_exit(operator=True)
        if args.command == "reset-test-db":
            _reset(settings)
            _say("Test database reset.")
            return 0
        return COMMANDS[args.command](settings, args)
    except RefusalError as exc:
        _say(f"Refused: {exc}")
        return 2
    except IntegrityError as exc:
        _say(f"Refused: {exc.orig}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
