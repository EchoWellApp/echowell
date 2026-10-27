"""Single-record, batch and CSV ingest (TRD 10 §4.1, §4.6, §4.7, §4.12; TRD 05 API-030..API-056;
FEAT-025, FEAT-026).

Every record goes through `validation.validate`. A rejected record is written only to
`ingest_rejections`; an accepted one (duplicates included) to `raw_sessions` under the session
advisory lock (ING-038), and only first arrivals trigger the pipeline. Neither responses nor logs
carry feature values or payloads (API-056, ING-057).
"""

from __future__ import annotations

import csv
import io
import json
import logging
import time
import uuid
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from backend.core import db
from backend.core.config import Settings
from backend.core.errors import (
    AppError,
    CsvHeaderMismatchError,
    DeviceKeyMismatchError,
    EmptyBatchError,
    FieldError,
    PayloadTooLargeError,
    ResidentWithdrawnError,
    SessionIdMismatchError,
    UnknownDeviceError,
    UnknownResidentError,
    UnsupportedSchemaVersionError,
    ValidationFailedError,
)
from backend.models import (
    ActorType,
    Device,
    IngestSource,
    PipelineRunStatus,
    PipelineTrigger,
    Resident,
)
from backend.repositories.config_repository import ConfigRepository
from backend.repositories.device_repository import DeviceRepository
from backend.repositories.ingest_repository import IngestRepository
from backend.repositories.processed_session_repository import ProcessedSessionRepository
from backend.repositories.raw_session_repository import RawSessionRepository
from backend.repositories.resident_repository import ResidentRepository
from backend.services import audit_service, validation
from backend.services.audit_service import AuditAction
from backend.services.pipeline_runner import Actor, PipelineRunner, RunHandle
from backend.services.validation import DeviceInfo, ResidentInfo, ValidationContext

logger = logging.getLogger("backend.ingest")

MAX_BATCH_RECORDS = 5000
DUPLICATE_REASON = "session_id already received"
EXTRA_CELLS = "_extra_cells"

_REQUEST_ERRORS: dict[str, type[AppError]] = {
    "UNSUPPORTED_SCHEMA_VERSION": UnsupportedSchemaVersionError,
    "UNKNOWN_RESIDENT": UnknownResidentError,
    "UNKNOWN_DEVICE": UnknownDeviceError,
    "RESIDENT_WITHDRAWN": ResidentWithdrawnError,
    "SESSION_ID_MISMATCH": SessionIdMismatchError,
    "VALIDATION_ERROR": ValidationFailedError,
}
_REQUEST_DETAILS = {
    "UNSUPPORTED_SCHEMA_VERSION": "The schema version is not supported.",
    "UNKNOWN_RESIDENT": "The resident is not enrolled.",
    "UNKNOWN_DEVICE": "The device is not registered.",
    "RESIDENT_WITHDRAWN": "resident withdrawn",
    "SESSION_ID_MISMATCH": "session_id does not match resident_id.",
    "VALIDATION_ERROR": "The record is not valid.",
}


@dataclass(frozen=True)
class Caller:
    """Who sent the records: an API key (bound to a device or not) or an admin user."""

    actor_type: ActorType
    actor_id: str
    api_key_id: uuid.UUID | None = None
    bound_device_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None

    @property
    def actor(self) -> Actor:
        return Actor(self.actor_type, self.actor_id)


@dataclass
class Roster:
    """Configuration and roster loaded once per request."""

    context: ValidationContext
    residents: dict[str, Resident]
    devices: dict[str, Device]


def load_roster(session: Session, settings: Settings, received_at: datetime) -> Roster:
    values = ConfigRepository(session).values_for_profile(settings.pipeline_profile)
    residents = {r.resident_code: r for r in ResidentRepository(session).list_all()}
    devices = {d.device_code: d for d in DeviceRepository(session).list_all()}
    context = ValidationContext(
        supported_versions=frozenset(values.get("supported_schema_versions") or []),
        name_map=validation.check_name_map(values.get("feature_name_map") or {}),
        residents={
            code: ResidentInfo(r.status.value, r.enrolled_on, r.sex)
            for code, r in residents.items()
        },
        devices={code: DeviceInfo(d.active) for code, d in devices.items()},
        facility_tz=ZoneInfo(settings.facility_tz),
        received_at=received_at,
    )
    return Roster(context, residents, devices)


@dataclass(frozen=True)
class Arrival:
    raw_session_id: uuid.UUID
    arrival_seq: int
    session_id: str
    duplicate: bool
    scope: frozenset[str]  # residents to process for a first arrival (API-045)
    warning_count: int


@dataclass
class Tally:
    """Counts of one request, for the `ingest_request` event (ING-057)."""

    records: int = 0
    accepted: int = 0
    rejected: int = 0
    duplicates: int = 0
    warnings: int = 0
    first_arrival_scope: set[str] = field(default_factory=set)


def _errors_json(errors: Sequence[FieldError]) -> list[dict[str, str]]:
    return [asdict(e) for e in errors]


def _code(raw: Any, key: str) -> str | None:
    value = raw.get(key) if isinstance(raw, dict) else None
    return value if isinstance(value, str) and len(value) <= 64 else None


class IngestService:
    def __init__(
        self,
        session: Session,
        settings: Settings,
        runner: PipelineRunner,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.runner = runner
        self.clock = clock or runner.clock

    # --- shared -----------------------------------------------------------------------------

    @contextmanager
    def _request_event(self, endpoint: str, caller: Caller, tally: Tally) -> Iterator[None]:
        """One `ingest_request` event per request, also when it fails (ING-057, LOG-050)."""
        started = time.monotonic()
        try:
            yield
        finally:
            logger.info(
                "ingest_request",
                extra={
                    "event": "ingest_request", "endpoint": endpoint,
                    "api_key_id": str(caller.api_key_id) if caller.api_key_id else None,
                    "user_id": str(caller.user_id) if caller.user_id else None,
                    "record_count": tally.records, "accepted": tally.accepted,
                    "rejected": tally.rejected, "duplicates": tally.duplicates,
                    "warning_count": tally.warnings,
                    "duration_ms": round((time.monotonic() - started) * 1000, 1),
                },
            )  # fmt: skip

    def _check(
        self, raw: Any, source: validation.Source, roster: Roster, caller: Caller
    ) -> tuple[validation.ValidationResult, bool]:
        """The validation result and whether a device-bound key sent another device's record."""
        result = validation.validate(raw, source=source, context=roster.context)
        if not result.accepted or caller.bound_device_id is None:
            return result, False
        device = roster.devices[result.values["device_id"]]
        return result, device.id != caller.bound_device_id

    def _reject(
        self,
        raw: Any,
        errors: Sequence[FieldError],
        caller: Caller,
        batch_id: uuid.UUID | None = None,
        row_number: int | None = None,
    ) -> None:
        IngestRepository(self.session).insert_rejection(
            raw_body=raw, errors=_errors_json(errors), ingest_batch_id=batch_id,
            api_key_id=caller.api_key_id, row_number=row_number,
        )  # fmt: skip
        logger.warning(
            "ingest_record_rejected",
            extra={
                "event": "ingest_record_rejected", "session_id": _code(raw, "session_id"),
                "resident_code": _code(raw, "resident_id"), "row_number": row_number,
                "fields": sorted({e.field for e in errors}),
                "codes": sorted({e.code for e in errors}),
            },
        )  # fmt: skip

    def _store(
        self,
        raw: Any,
        result: validation.ValidationResult,
        roster: Roster,
        caller: Caller,
        received_at: datetime,
        batch_id: uuid.UUID | None = None,
    ) -> Arrival:
        """Insert one accepted arrival under the session lock (ING-029, ING-037, ING-038)."""
        values = result.values
        session_id = values["session_id"]
        resident = roster.residents[values["resident_id"]]
        device = roster.devices[values["device_id"]]
        db.lock_xact(self.session, "session", session_id)
        raw_sessions = RawSessionRepository(self.session)
        first_payload = raw_sessions.first_payload(session_id)
        duplicate = first_payload is not None
        warnings = list(result.warnings)
        if duplicate and first_payload != raw:
            warnings.append(
                FieldError(
                    "session_id", "duplicate_payload_differs",
                    "An earlier arrival of this session_id has different values.",
                )
            )  # fmt: skip
        latest = raw_sessions.latest_timestamp_for_device(device.id)
        typed = {k: v for k, v in values.items() if k not in ("resident_id", "device_id")}
        raw_id, arrival_seq = raw_sessions.insert(
            {
                **typed,
                "payload": raw,
                "ingest_warnings": _errors_json(warnings),
                "ingest_batch_id": batch_id,
                "api_key_id": caller.api_key_id,
                "resident_id": resident.id,
                "device_id": device.id,
                "resident_code": resident.resident_code,
                "device_code": device.device_code,
            }
        )
        if latest is None or values["timestamp_utc"] >= latest:
            DeviceRepository(self.session).set_firmware(device, values["device_firmware_version"])
        scope: frozenset[str] = frozenset()
        if duplicate:
            logger.info(
                "ingest_duplicate", extra={"event": "ingest_duplicate", "session_id": session_id}
            )
        else:
            local_date = values["timestamp_utc"].astimezone(roster.context.facility_tz).date()
            sharing = DeviceRepository(self.session).residents_on_device(device.id, local_date)
            scope = frozenset({resident.resident_code, *(r.resident_code for r in sharing)})
        return Arrival(raw_id, arrival_seq, session_id, duplicate, scope, len(warnings))

    # --- POST /sessions ---------------------------------------------------------------------

    def ingest_single(self, caller: Caller, body: bytes) -> tuple[int, dict[str, Any]]:
        """201 processed, 200 duplicate; 422/403 after storing the rejection (FEAT-025)."""
        tally = Tally(records=1)
        with self._request_event("POST /api/v1/sessions", caller, tally):
            try:
                raw = json.loads(body)
            except (ValueError, UnicodeDecodeError):
                tally.rejected = 1
                raise ValidationFailedError("The request body is not valid JSON.") from None
            received_at = self.clock()
            roster = load_roster(self.session, self.settings, received_at)
            result, mismatch = self._check(raw, "json", roster, caller)
            if not result.accepted or mismatch:
                tally.rejected = 1
                if mismatch:
                    errors = [_mismatch_error()]
                    self._reject(raw, errors, caller)
                    self.session.commit()  # the rejection survives the error response
                    raise DeviceKeyMismatchError(
                        "This API key is bound to another device.", errors=errors
                    )
                self._reject(raw, result.errors, caller)
                self.session.commit()
                code = result.request_code
                raise _REQUEST_ERRORS[code](_REQUEST_DETAILS[code], errors=result.errors)
            arrival = self._store(raw, result, roster, caller, received_at)
            self.session.commit()  # stored before any processing (DB-022)
            tally.accepted, tally.warnings = 1, arrival.warning_count
            body_out = {
                "raw_session_id": str(arrival.raw_session_id),
                "arrival_seq": arrival.arrival_seq,
                "session_id": arrival.session_id,
            }
            if arrival.duplicate:
                tally.duplicates = 1
                return 200, {
                    **body_out, "status_after_processing": "duplicate",
                    "reasons": [DUPLICATE_REASON], "pipeline_run_id": None,
                }  # fmt: skip
            handle, status = self.runner.run(
                sorted(arrival.scope), PipelineTrigger.INGEST, actor=caller.actor
            )
            outcome, reasons = "pending", []
            if status == PipelineRunStatus.SUCCEEDED:
                processed = ProcessedSessionRepository(self.session).by_raw_session(
                    arrival.raw_session_id
                )
                if processed is not None:
                    outcome, reasons = processed.status.value, list(processed.reasons)
            return 201, {
                **body_out, "status_after_processing": outcome, "reasons": reasons,
                "pipeline_run_id": str(handle.id),
            }  # fmt: skip

    # --- POST /ingest -----------------------------------------------------------------------

    def ingest_batch(
        self,
        caller: Caller,
        records: Sequence[Any],
        source: IngestSource,
        filename: str | None = None,
    ) -> tuple[dict[str, Any], RunHandle | None]:
        """Store a batch; the caller schedules `runner.execute(handle)` after commit (API-053)."""
        tally = Tally(records=len(records))
        endpoint = "seed" if source == IngestSource.SEED else "POST /api/v1/ingest"
        with self._request_event(endpoint, caller, tally):
            received_at = self.clock()
            roster = load_roster(self.session, self.settings, received_at)
            ingest = IngestRepository(self.session)
            batch = ingest.insert_batch(
                source=source, record_count=len(records), filename=filename,
                uploaded_by=caller.user_id, api_key_id=caller.api_key_id,
            )  # fmt: skip
            for row_number, raw in enumerate(records, start=1):
                result, mismatch = self._check(
                    raw, "csv" if _is_csv(source) else "json", roster, caller
                )
                if not result.accepted or mismatch:
                    errors = [_mismatch_error()] if mismatch else result.errors
                    self._reject(raw, errors, caller, batch.id, row_number)
                    tally.rejected += 1
                    continue
                arrival = self._store(raw, result, roster, caller, received_at, batch.id)
                tally.accepted += 1
                tally.warnings += arrival.warning_count
                if arrival.duplicate:
                    tally.duplicates += 1
                tally.first_arrival_scope |= arrival.scope
            ingest.update_counts(
                batch, record=tally.records, accepted=tally.accepted, rejected=tally.rejected,
                duplicates=tally.duplicates,
            )  # fmt: skip
            handle = None
            if tally.first_arrival_scope:
                handle = self.runner.start(
                    sorted(tally.first_arrival_scope), PipelineTrigger.INGEST,
                    actor=caller.actor, session=self.session,
                )  # fmt: skip
            audit_service.record(
                self.session, action=AuditAction.INGEST_BATCH_RECEIVED,
                actor_type=caller.actor_type, actor_id=caller.actor_id,
                entity_type="ingest_batch", entity_id=str(batch.id),
                details={
                    "source": source.value, "record_count": tally.records,
                    "accepted": tally.accepted, "rejected": tally.rejected,
                    "duplicates": tally.duplicates,
                    "pipeline_run_id": str(handle.id) if handle else None,
                },
            )  # fmt: skip
            self.session.commit()
            return {
                "ingest_batch_id": str(batch.id), "source": source.value,
                "accepted": tally.accepted, "rejected": tally.rejected,
                "duplicates": tally.duplicates,
                "pipeline_run_id": str(handle.id) if handle else None,
            }, handle  # fmt: skip


def _is_csv(source: IngestSource) -> bool:
    return source in (IngestSource.CSV_UPLOAD, IngestSource.SEED)


def _mismatch_error() -> FieldError:
    return FieldError(
        "device_id", "device_key_mismatch", "This API key may only send records of its own device."
    )


# --- envelopes ----------------------------------------------------------------------------------


def parse_json_batch(body: bytes) -> list[Any]:
    """`{"records": [...]}`: 422 VALIDATION_ERROR, 422 EMPTY_BATCH, 413 over 5,000 (ING-007)."""
    try:
        envelope = json.loads(body)
    except (ValueError, UnicodeDecodeError):
        raise ValidationFailedError("The request body is not valid JSON.") from None
    if not isinstance(envelope, dict) or not isinstance(envelope.get("records"), list):
        raise ValidationFailedError(
            "The body must be an object with a records array.",
            errors=[FieldError("records", "missing_field", "This field is required.")],
        )
    extra = sorted(set(envelope) - {"records"})
    if extra:
        raise ValidationFailedError(
            "The body has fields other than records.",
            errors=[
                FieldError(name, "extra_forbidden", "Only records is allowed.") for name in extra
            ],
        )
    return _sized(envelope["records"])


def parse_csv_batch(data: bytes, name_map: dict[str, str]) -> list[dict[str, Any]]:
    """Rows of a UTF-8 CSV as `{header: cell text}`; the header must be the 30 schema fields
    after mapping (ING-031, ING-053, ING-055)."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValidationFailedError("The file is not UTF-8 text.") from None
    reader = csv.DictReader(io.StringIO(text, newline=""), restkey=EXTRA_CELLS)
    header = reader.fieldnames or []
    errors = validation.csv_header_errors(list(header), name_map)
    if errors:
        raise CsvHeaderMismatchError("The CSV header does not match schema v0.1.", errors=errors)
    rows: list[dict[str, Any]] = []
    for row in reader:
        rows.append(dict(row))
        if len(rows) > MAX_BATCH_RECORDS:
            break
    return _sized(rows)


def _sized(records: list[Any]) -> list[Any]:
    if not records:
        raise EmptyBatchError("The batch has no records.")
    if len(records) > MAX_BATCH_RECORDS:
        raise PayloadTooLargeError(f"A batch holds at most {MAX_BATCH_RECORDS} records.")
    return records


def batch_detail(session: Session, batch_id: uuid.UUID) -> dict[str, Any] | None:
    """`IngestBatch` with its rejections, never `raw_body` (API-054, DME-005)."""
    ingest = IngestRepository(session)
    batch = ingest.get_batch(batch_id)
    if batch is None:
        return None
    return {
        "id": batch.id, "source": batch.source.value, "filename": batch.filename,
        "record_count": batch.record_count, "accepted_count": batch.accepted_count,
        "rejected_count": batch.rejected_count, "duplicate_count": batch.duplicate_count,
        "uploaded_by": batch.uploaded_by, "received_at": batch.received_at,
        "pipeline_run_id": audit_service.batch_pipeline_run_id(session, str(batch.id)),
        "rejections": [
            {
                "row_number": r.row_number, "session_id": _code(r.raw_body, "session_id"),
                "received_at": r.received_at, "errors": r.errors,
            }
            for r in ingest.rejections_for_batch(batch.id)
        ],
    }  # fmt: skip


def name_map(session: Session, settings: Settings) -> dict[str, str]:
    """The active profile's validated `feature_name_map` (ING-016, ING-017)."""
    values = ConfigRepository(session).values_for_profile(settings.pipeline_profile)
    return validation.check_name_map(values.get("feature_name_map") or {})


def check_startup_name_map(session_factory: Callable[[], Session], settings: Settings) -> bool:
    """Refuse to start with an invalid `feature_name_map` (ING-017): raises `NameMapError`.

    Returns False when the database cannot be reached; `/health` then reports it and the map
    is checked again on every ingest request.
    """
    try:
        with session_factory() as session:
            name_map(session, settings)
    except OperationalError:
        logger.warning("name_map_check_skipped", extra={"event": "name_map_check_skipped"})
        return False
    return True
