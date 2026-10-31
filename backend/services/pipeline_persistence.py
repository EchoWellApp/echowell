"""Load engine inputs and write engine results (TRD 07 §4.8 ANL-033..ANL-042, ANL-060; TRD 06
DB-013..DB-018, DB-036; FEAT-053).

`load_inputs` reads the scope's residents plus every resident who shares a device with them
(ANL-016), their `raw_sessions` as `RawRecord`s built from the typed columns (ANL-035), all
assignments and the persisted baselines. `write_resident` replaces one resident's derived rows
inside the caller's transaction, which already holds the resident's advisory lock: epochs are
upserted, baselines inserted once, alerts and data alerts reconciled on their natural keys, and
nothing in `baselines`, `alerts`, `alert_reviews`, `staff_notes` or `raw_sessions` is deleted.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from analytics.config import (
    FEATURE_KEYS,
    AlertEvent,
    DataAlert,
    DeviceAssignment,
    EpochKey,
    PipelineResult,
    RawRecord,
    ResidentInfo,
)
from analytics.config import Baseline as EngineBaseline
from backend.models import (
    ActorType,
    Alert,
    AlertStatus,
    Baseline,
    CusumState,
    DataAlertKind,
    DataAlertStatus,
    DayLedgerEntry,
    Device,
    Epoch,
    ProcessedSession,
    RawSession,
    Resident,
    ResidentCohort,
    Score,
)
from backend.models import DataAlert as DataAlertRow
from backend.models import DeviceAssignment as AssignmentRow
from backend.services import audit_service
from backend.services.audit_service import AuditAction

RESIDENT_KINDS = ("baseline_stalled", "possible_other_speaker", "high_set_aside")


class EpochRenumberingBlockedError(Exception):
    """A computed epoch would change the key of an epoch with a frozen baseline (ANL-038)."""


@dataclass(frozen=True)
class Inputs:
    records: list[RawRecord]
    residents: list[ResidentInfo]
    assignments: list[DeviceAssignment]
    frozen: dict[EpochKey, tuple[EngineBaseline, ...]]
    resident_ids: dict[str, uuid.UUID]
    device_ids: dict[str, uuid.UUID]
    scope: list[str]  # resident codes whose rows this run writes


@dataclass(frozen=True)
class RunContext:
    run_id: uuid.UUID
    as_of: datetime


def _record(row: RawSession) -> RawRecord:
    return RawRecord(
        raw_session_id=str(row.id), arrival_seq=row.arrival_seq, received_at=row.received_at,
        schema_version=row.schema_version, session_id=row.session_id,
        resident_code=row.resident_code, device_code=row.device_code,
        timestamp_utc=row.timestamp_utc, mic_noise_level_dbfs=row.mic_noise_level_dbfs,
        audio_quality_flag=row.audio_quality_flag,
        extraction_software_version=row.extraction_software_version,
        device_firmware_version=row.device_firmware_version,
        speech_duration_s=row.speech_duration_s, phrase_id=row.phrase_id,
        features={key: float(getattr(row, key)) for key in FEATURE_KEYS},
    )  # fmt: skip


def load_inputs(session: Session, scope: Sequence[str] | str) -> Inputs:
    residents = session.scalars(select(Resident)).all()
    by_code = {r.resident_code: r for r in residents}
    devices = {d.id: d.device_code for d in session.scalars(select(Device)).all()}
    rows = session.scalars(select(AssignmentRow)).all()
    assignments = [
        DeviceAssignment(r.resident.resident_code, devices[r.device_id], r.valid_from, r.valid_to)
        for r in rows
    ]
    codes = sorted(by_code) if scope == "all" else sorted(set(scope) & set(by_code))
    sharers = _sharers(set(codes), assignments)
    loaded = sorted(sharers | set(codes))
    ids = [by_code[c].id for c in loaded]
    raw = session.scalars(
        select(RawSession).where(RawSession.resident_id.in_(ids)).order_by(RawSession.arrival_seq)
    ).all()
    return Inputs(
        records=[_record(r) for r in raw],
        residents=[
            ResidentInfo(c, by_code[c].enrolled_on, by_code[c].withdrawn_on,
                         by_code[c].status.value)
            for c in loaded
        ],
        assignments=[a for a in assignments if a.resident_code in set(loaded)],
        frozen=_frozen(session, ids, devices),
        resident_ids={c: by_code[c].id for c in loaded},
        device_ids={code: device_id for device_id, code in devices.items()},
        scope=codes,
    )  # fmt: skip


def _sharers(codes: set[str], assignments: Sequence[DeviceAssignment]) -> set[str]:
    """Residents whose assignment to a device overlaps an assignment of a scoped resident."""
    mine = [a for a in assignments if a.resident_code in codes]
    out = set()
    for a in assignments:
        for m in mine:
            if a.device_code == m.device_code and _overlap(a, m):
                out.add(a.resident_code)
    return out


def _overlap(a: DeviceAssignment, b: DeviceAssignment) -> bool:
    a_end, b_end = a.valid_to or datetime.max.date(), b.valid_to or datetime.max.date()
    return a.valid_from <= b_end and b.valid_from <= a_end


def _frozen(
    session: Session, resident_ids: Sequence[uuid.UUID], devices: Mapping[uuid.UUID, str]
) -> dict[EpochKey, tuple[EngineBaseline, ...]]:
    rows = session.execute(
        select(Baseline, Epoch, Resident.resident_code)
        .join(Epoch, Epoch.id == Baseline.epoch_id)
        .join(Resident, Resident.id == Baseline.resident_id)
        .where(Baseline.resident_id.in_(resident_ids))
    ).all()
    out: dict[EpochKey, list[EngineBaseline]] = {}
    for baseline, epoch, code in rows:
        out.setdefault((code, epoch.epoch_number), []).append(EngineBaseline(
            resident_code=code, epoch_number=epoch.epoch_number,
            device_code=devices[epoch.device_id], feature_key=baseline.feature_key,
            n_sessions=baseline.n_sessions, first_session_id=baseline.first_session_id,
            frozen_after_session_id=baseline.frozen_after_session_id, median=baseline.median,
            mad=baseline.mad, robust_spread=baseline.robust_spread,
            floor_applied=baseline.floor_applied, frozen_at=baseline.frozen_at,
        ))  # fmt: skip
    return {key: tuple(sorted(rows_, key=lambda b: b.feature_key)) for key, rows_ in out.items()}


def delete_baselines(session: Session, resident_id: uuid.UUID) -> None:
    """Operator rebuild only (ANL-032): the migrator role may DELETE `baselines` (DB-009)."""
    session.execute(delete(Baseline).where(Baseline.resident_id == resident_id))


def write_resident(
    session: Session, code: str, result: PipelineResult, inputs: Inputs, run: RunContext
) -> list[dict[str, Any]]:
    """Replace one resident's derived rows (ANL-036..ANL-039, ANL-060, DB-025); returns the
    warnings of this resident's reconciliation."""
    resident = session.get(Resident, inputs.resident_ids[code])
    assert resident is not None  # noqa: S101 - loaded by load_inputs
    warnings: list[dict[str, Any]] = []
    epoch_ids = _upsert_epochs(session, resident, result, inputs, run)
    session.execute(delete(Score).where(Score.resident_id == resident.id))
    session.execute(delete(CusumState).where(CusumState.resident_id == resident.id))
    session.execute(delete(ProcessedSession).where(ProcessedSession.resident_id == resident.id))
    session.execute(delete(DayLedgerEntry).where(DayLedgerEntry.resident_id == resident.id))
    stale = [e for e in session.scalars(select(Epoch).where(Epoch.resident_id == resident.id))
             if e.id not in epoch_ids.values() and not _has_baseline(session, e.id)]  # fmt: skip
    for epoch in stale:
        session.delete(epoch)
    session.flush()
    processed = _insert_sessions(session, resident, code, result, epoch_ids, run)
    _insert_baselines(session, resident, code, result, epoch_ids, run)
    _insert_scores(session, resident, code, result, epoch_ids, processed, run)
    _insert_cusum(session, resident, code, result, epoch_ids, run)
    _insert_ledger(session, resident, code, result, inputs, run)
    warnings += _reconcile_alerts(session, resident, code, result, epoch_ids, run)
    _reconcile_resident_data_alerts(session, resident, code, result, run)
    _update_cohort(session, resident, code, result)
    session.flush()
    return warnings


def _has_baseline(session: Session, epoch_id: uuid.UUID) -> bool:
    return (
        session.scalar(select(Baseline.id).where(Baseline.epoch_id == epoch_id).limit(1))
        is not None
    )


def _upsert_epochs(
    session: Session, resident: Resident, result: PipelineResult, inputs: Inputs, run: RunContext
) -> dict[int, uuid.UUID]:
    """ANL-038: reuse `epochs.id` per epoch number; refuse to change a frozen epoch's key."""
    existing = {e.epoch_number: e for e in session.scalars(
        select(Epoch).where(Epoch.resident_id == resident.id))}  # fmt: skip
    computed = [e for e in result.epochs if e.resident_code == resident.resident_code]
    for e in computed:
        old = existing.get(e.epoch_number)
        if old is not None and _has_baseline(session, old.id) and (
            inputs.device_ids[e.device_code], e.device_firmware_version,
            e.extraction_software_version, e.started_at,
        ) != (old.device_id, old.device_firmware_version, old.extraction_software_version,
              old.started_at):  # fmt: skip
            raise EpochRenumberingBlockedError(f"epoch {e.epoch_number}")
    frozen_numbers = {n for n, old in existing.items() if _has_baseline(session, old.id)}
    if frozen_numbers - {e.epoch_number for e in computed}:
        raise EpochRenumberingBlockedError("a frozen epoch would disappear")
    ids = {}
    for e in computed:
        row = existing.get(e.epoch_number)
        if row is None:
            row = Epoch(resident_id=resident.id, epoch_number=e.epoch_number)
            session.add(row)
        row.device_id = inputs.device_ids[e.device_code]
        row.device_firmware_version = e.device_firmware_version
        row.extraction_software_version = e.extraction_software_version
        row.started_at = e.started_at
        row.ended_at = e.ended_at
        row.pipeline_run_id = run.run_id
        session.flush()
        ids[e.epoch_number] = row.id
    return ids


def _insert_sessions(
    session: Session, resident: Resident, code: str, result: PipelineResult,
    epoch_ids: Mapping[int, uuid.UUID], run: RunContext,
) -> dict[str, uuid.UUID]:  # fmt: skip
    rows = {}
    for s in result.sessions:
        if s.record.resident_code != code:
            continue
        duplicate = s.status == "duplicate"
        row = ProcessedSession(
            raw_session_id=uuid.UUID(s.record.raw_session_id), session_id=s.record.session_id,
            resident_id=resident.id,
            epoch_id=None if duplicate or s.epoch_number is None else epoch_ids[s.epoch_number],
            status=s.status, reasons=list(s.reasons), reason_text=s.reason_text,
            timestamp_utc=s.record.timestamp_utc, local_date=s.local_date,
            local_time=s.local_datetime.time().replace(microsecond=0, tzinfo=None),
            is_morning=s.is_morning, screen_detail=s.screen_detail,
            baseline_ordinal=s.baseline_ordinal, in_baseline=s.in_baseline,
            late_arrival=s.late_arrival,
            adjusted_features=None if duplicate else dict(s.adjusted),
            pipeline_run_id=run.run_id,
        )  # fmt: skip
        session.add(row)
        rows[s.record.raw_session_id] = row
    session.flush()
    return {raw_id: row.id for raw_id, row in rows.items()}


def _insert_baselines(
    session: Session, resident: Resident, code: str, result: PipelineResult,
    epoch_ids: Mapping[int, uuid.UUID], run: RunContext,
) -> None:  # fmt: skip
    """Insert-only: the 20 rows of an epoch whose baseline formed for the first time (ANL-037)."""
    for number, epoch_id in epoch_ids.items():
        if _has_baseline(session, epoch_id):
            continue
        rows = [b for b in result.baselines if b.resident_code == code and b.epoch_number == number]
        if not rows:
            continue
        session.add_all(Baseline(
            resident_id=resident.id, epoch_id=epoch_id, feature_key=b.feature_key,
            n_sessions=b.n_sessions, first_session_id=b.first_session_id,
            frozen_after_session_id=b.frozen_after_session_id, median=b.median, mad=b.mad,
            robust_spread=b.robust_spread, floor_applied=b.floor_applied, frozen_at=b.frozen_at,
            pipeline_run_id=run.run_id,
        ) for b in rows)  # fmt: skip
    session.flush()


def _insert_scores(
    session: Session, resident: Resident, code: str, result: PipelineResult,
    epoch_ids: Mapping[int, uuid.UUID], processed: Mapping[str, uuid.UUID], run: RunContext,
) -> None:  # fmt: skip
    session.add_all(Score(
        processed_session_id=processed[s.raw_session_id], resident_id=resident.id,
        epoch_id=epoch_ids[s.epoch_number], local_date=s.local_date, is_morning=s.is_morning,
        z=dict(s.z), composite_raw=s.composite_raw, composite_z=s.composite_z,
        cusum_tally=s.cusum_tally, alarm_state=s.alarm_state, pipeline_run_id=run.run_id,
    ) for s in result.scores if s.resident_code == code)  # fmt: skip
    session.flush()


def _insert_cusum(
    session: Session, resident: Resident, code: str, result: PipelineResult,
    epoch_ids: Mapping[int, uuid.UUID], run: RunContext,
) -> None:  # fmt: skip
    session.add_all(CusumState(
        epoch_id=epoch_ids[e.epoch_number], resident_id=resident.id,
        current_tally=e.current_tally, last_scored_session_id=e.last_scored_session_id,
        alarm_on=e.alarm_on, pipeline_run_id=run.run_id,
    ) for e in result.epochs if e.resident_code == code)  # fmt: skip
    session.flush()


def _insert_ledger(
    session: Session, resident: Resident, code: str, result: PipelineResult, inputs: Inputs,
    run: RunContext,
) -> None:  # fmt: skip
    session.add_all(DayLedgerEntry(
        resident_id=resident.id, local_date=d.local_date, status=d.status,
        device_id=inputs.device_ids.get(d.device_code) if d.device_code else None,
        reason=d.reason, pipeline_run_id=run.run_id,
    ) for d in result.ledger if d.resident_code == code)  # fmt: skip
    session.flush()


def _close(session: Session, alert: Alert, code: str, reason: str, run: RunContext) -> None:
    alert.status = AlertStatus.CLOSED
    alert.closed_reason = reason
    alert.closed_at = run.as_of
    audit_service.record(
        session, action=AuditAction.ALERT_CLOSED, actor_type=ActorType.SYSTEM, actor_id=None,
        entity_type="alert", entity_id=str(alert.id),
        details={"resident_code": code, "closed_reason": reason},
    )  # fmt: skip


def _reconcile_alerts(
    session: Session, resident: Resident, code: str, result: PipelineResult,
    epoch_ids: Mapping[int, uuid.UUID], run: RunContext,
) -> list[dict[str, Any]]:  # fmt: skip
    """ANL-039, CUS-014, CUS-015, CUS-018: upsert on (epoch_id, session_id), never delete."""
    warnings: list[dict[str, Any]] = []
    events: dict[uuid.UUID, AlertEvent] = {
        epoch_ids[a.epoch_number]: a for a in result.alerts if a.resident_code == code
    }
    alerts = session.scalars(select(Alert).where(Alert.resident_id == resident.id)).all()
    for alert in alerts:
        event = events.get(alert.epoch_id)
        if alert.status == AlertStatus.CLOSED:
            continue
        if event is None or event.session_id != alert.session_id:
            _close(session, alert, code, "superseded by rebuild", run)
            warnings.append({"code": "alert_first_crossing_changed", "resident_code": code,
                             "session_id": alert.session_id,
                             "detail": "first crossing no longer produced"})  # fmt: skip
        elif event.epoch_ended:
            _close(session, alert, code, "epoch ended", run)
    session.flush()
    keys = {(a.epoch_id, a.session_id) for a in alerts}
    for epoch_id, event in sorted(events.items(), key=lambda item: item[1].epoch_number):
        if (epoch_id, event.session_id) in keys:
            continue
        alert = Alert(
            resident_id=resident.id, epoch_id=epoch_id, session_id=event.session_id,
            triggered_at=event.triggered_at, local_date=event.local_date,
            cusum_value=event.cusum_value, status=AlertStatus.OPEN, pipeline_run_id=run.run_id,
        )  # fmt: skip
        session.add(alert)
        session.flush()
        if event.epoch_ended:
            _close(session, alert, code, "epoch ended", run)
    session.flush()
    return warnings


def reconcile_data_alerts(
    session: Session, detected: Sequence[DataAlert], kinds: Sequence[str],
    subject: tuple[str, uuid.UUID], run: RunContext, existing: Sequence[DataAlertRow],
) -> None:  # fmt: skip
    """ANL-060, DB-036 for one subject: insert, update while open, resolve when gone; a resolved
    row is never reopened and review-flagged rows are never touched."""
    column, subject_id = subject
    found: dict[str, DataAlert] = {a.kind: a for a in detected}
    open_rows = {r.kind.value: r for r in existing
                 if r.status == DataAlertStatus.OPEN and r.kind.value in kinds}  # fmt: skip
    for kind in kinds:
        alert, row = found.get(kind), open_rows.get(kind)
        if alert is not None and row is None:
            session.add(DataAlertRow(
                kind=DataAlertKind(kind), title=alert.title, detail=alert.detail,
                first_detected_at=run.as_of, last_detected_at=run.as_of,
                status=DataAlertStatus.OPEN, pipeline_run_id=run.run_id,
                **{column: subject_id},
            ))  # fmt: skip
        elif alert is not None and row is not None:
            row.title, row.detail = alert.title, alert.detail
            row.last_detected_at, row.pipeline_run_id = run.as_of, run.run_id
        elif row is not None:
            row.status, row.resolved_at = DataAlertStatus.RESOLVED, run.as_of
    session.flush()


def _reconcile_resident_data_alerts(
    session: Session, resident: Resident, code: str, result: PipelineResult, run: RunContext
) -> None:
    existing = session.scalars(
        select(DataAlertRow).where(DataAlertRow.resident_id == resident.id)
    ).all()
    detected = [a for a in result.data_alerts if a.resident_code == code]
    reconcile_data_alerts(session, detected, RESIDENT_KINDS, ("resident_id", resident.id), run,
                          existing)  # fmt: skip


def reconcile_device_alerts(
    session: Session, result: PipelineResult, inputs: Inputs, devices: Sequence[str],
    run: RunContext,
) -> None:  # fmt: skip
    """`device_silent` for the devices the run covered (FEAT-053-FR-11); the caller holds
    `advisory_key('device_alerts', 'all')`."""
    for device in sorted(devices):
        device_id = inputs.device_ids[device]
        existing = session.scalars(
            select(DataAlertRow).where(DataAlertRow.device_id == device_id)
        ).all()
        detected = [a for a in result.data_alerts if a.device_code == device]
        reconcile_data_alerts(session, detected, ("device_silent",), ("device_id", device_id),
                              run, existing)  # fmt: skip


def _update_cohort(session: Session, resident: Resident, code: str, result: PipelineResult) -> None:
    """DB-025: a new admission whose current epoch has a frozen baseline becomes longitudinal."""
    if resident.cohort != ResidentCohort.NEW_ADMISSION:
        return
    mine = [e for e in result.epochs if e.resident_code == code]
    if not mine or not mine[-1].baseline_formed:
        return
    resident.cohort = ResidentCohort.LONGITUDINAL
    audit_service.record(
        session, action=AuditAction.RESIDENT_COHORT_CHANGED, actor_type=ActorType.SYSTEM,
        actor_id=None, entity_type="resident", entity_id=code,
        details={"from": "new_admission", "to": "longitudinal",
                 "epoch_number": mine[-1].epoch_number},
    )  # fmt: skip
