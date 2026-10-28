"""Read-model derivations, computed on read and never stored (TRD 23 §4.4; FEAT-014).

TRD 06 DB-041, DB-043..DB-045, DB-065, DB-066; DME-011, DME-012; TRD 24 D-41, D-42, D-64.

Every function takes the effective as-of local date (or instant and facility time zone) and
`baseline_n` as parameters and returns plain data objects. Local dates come from `zoneinfo`, never
a fixed offset (AGT-040). Values are returned at full precision; formatting (one-decimal tallies,
"Oct 21") belongs to the API and UI (DME-014, AGT-054).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from backend.models import (
    AlarmState,
    Alert,
    AlertReview,
    AlertStatus,
    Baseline,
    CusumState,
    DayLedgerEntry,
    DayStatus,
    Device,
    DeviceAssignment,
    Epoch,
    ProcessedSession,
    RawSession,
    Resident,
    Score,
    SessionStatus,
)

WINDOW_DAYS = 30
# Frozen baseline = the 19 feature rows plus the composite row (PGS-031).
FROZEN_BASELINE_ROWS = 20


def local_date(instant: datetime, timezone: str) -> date:
    """Facility-local calendar date of an instant (AGT-040)."""
    return instant.astimezone(ZoneInfo(timezone)).date()


@dataclass(frozen=True)
class Window:
    start: date
    end: date

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1


def window_for(enrolled_on: date, as_of_date: date) -> Window:
    """The 30 local days ending on the as-of date, never before enrolment (DB-041, D-42)."""
    return Window(max(as_of_date - timedelta(days=WINDOW_DAYS - 1), enrolled_on), as_of_date)


@dataclass(frozen=True)
class ActivityCounts:
    used: int = 0
    set_aside: int = 0
    quarantined: int = 0
    missed: int = 0


def activity_counts(
    session: Session, residents: Iterable[Resident], as_of_date: date
) -> dict[uuid.UUID, ActivityCounts]:
    """Used, set aside, quarantined and missed in each resident's window (DB-041, FR-135).

    Duplicates are never counted (AGT-053); missed = `missing_resident` + `missing_device_gap`.
    """
    people = list(residents)
    if not people:
        return {}
    ids = [r.id for r in people]
    start = func.greatest(as_of_date - timedelta(days=WINDOW_DAYS - 1), Resident.enrolled_on)
    status_rows = session.execute(
        select(ProcessedSession.resident_id, ProcessedSession.status, func.count())
        .join(Resident, Resident.id == ProcessedSession.resident_id)
        .where(
            ProcessedSession.resident_id.in_(ids),
            ProcessedSession.status != SessionStatus.DUPLICATE,
            ProcessedSession.local_date.between(start, as_of_date),
        )
        .group_by(ProcessedSession.resident_id, ProcessedSession.status)
    ).all()
    missed_rows = session.execute(
        select(DayLedgerEntry.resident_id, func.count())
        .join(Resident, Resident.id == DayLedgerEntry.resident_id)
        .where(
            DayLedgerEntry.resident_id.in_(ids),
            DayLedgerEntry.status != DayStatus.CHECKED_IN,
            DayLedgerEntry.local_date.between(start, as_of_date),
        )
        .group_by(DayLedgerEntry.resident_id)
    ).all()
    counts: dict[uuid.UUID, dict[str, int]] = {rid: {} for rid in ids}
    for resident_id, status, count in status_rows:
        counts[resident_id][str(status)] = count
    for resident_id, count in missed_rows:
        counts[resident_id]["missed"] = count
    return {
        rid: ActivityCounts(
            used=c.get(SessionStatus.USABLE, 0),
            set_aside=c.get(SessionStatus.SET_ASIDE, 0),
            quarantined=c.get(SessionStatus.QUARANTINED, 0),
            missed=c.get("missed", 0),
        )
        for rid, c in counts.items()
    }


def last_checkin(session: Session, resident_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, datetime]:
    """Latest non-duplicate `processed_sessions.timestamp_utc` of any status (DB-045, D-42)."""
    rows = session.execute(
        select(ProcessedSession.resident_id, ProcessedSession.timestamp_utc)
        .where(
            ProcessedSession.resident_id.in_(list(resident_ids)),
            ProcessedSession.status != SessionStatus.DUPLICATE,
        )
        .distinct(ProcessedSession.resident_id)
        .order_by(ProcessedSession.resident_id, ProcessedSession.timestamp_utc.desc())
    ).all()
    return {resident_id: ts for resident_id, ts in rows}


def current_epochs(session: Session, resident_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, Epoch]:
    rows = session.scalars(
        select(Epoch).where(Epoch.resident_id.in_(list(resident_ids)), Epoch.ended_at.is_(None))
    ).all()
    return {epoch.resident_id: epoch for epoch in rows}


@dataclass(frozen=True)
class BaselineProgress:
    n: int
    of: int
    frozen: bool
    first_session_date: date | None
    frozen_after_date: date | None


def _session_local_date(session: Session, epoch_id: uuid.UUID, session_id: str) -> date | None:
    return session.scalar(
        select(ProcessedSession.local_date).where(
            ProcessedSession.epoch_id == epoch_id,
            ProcessedSession.session_id == session_id,
            ProcessedSession.status != SessionStatus.DUPLICATE,
        )
    )


def baseline_progress(session: Session, epoch: Epoch | None, baseline_n: int) -> BaselineProgress:
    """`min(usable in current epoch, N)` of N, frozen flag and baseline dates (DME-012)."""
    if epoch is None:
        return BaselineProgress(0, baseline_n, False, None, None)
    usable = session.scalar(
        select(func.count())
        .select_from(ProcessedSession)
        .where(
            ProcessedSession.epoch_id == epoch.id,
            ProcessedSession.status == SessionStatus.USABLE,
            ProcessedSession.late_arrival.is_(False),
        )
    )
    rows = session.scalar(
        select(func.count()).select_from(Baseline).where(Baseline.epoch_id == epoch.id)
    )
    composite = session.scalars(
        select(Baseline).where(Baseline.epoch_id == epoch.id, Baseline.feature_key == "composite")
    ).first()
    first = frozen_after = None
    if composite is not None:
        first = _session_local_date(session, epoch.id, composite.first_session_id)
        frozen_after = _session_local_date(session, epoch.id, composite.frozen_after_session_id)
    return BaselineProgress(
        n=min(int(usable or 0), baseline_n),
        of=baseline_n,
        frozen=rows == FROZEN_BASELINE_ROWS,
        first_session_date=first,
        frozen_after_date=frozen_after,
    )


def watching_since(session: Session, epoch: Epoch | None, baseline_n: int) -> date | None:
    """First scored local date of the epoch; before any score, the day after the freeze (D-41)."""
    if epoch is None:
        return None
    first_score = session.scalar(
        select(func.min(Score.local_date)).where(Score.epoch_id == epoch.id)
    )
    if first_score is not None:
        return first_score
    progress = baseline_progress(session, epoch, baseline_n)
    if progress.frozen and progress.frozen_after_date is not None:
        return progress.frozen_after_date + timedelta(days=1)
    return None


@dataclass(frozen=True)
class AlarmFacts:
    alert_id: uuid.UUID
    alarm_since: date
    open_days: int
    tally: float | None
    reviewed: bool
    status: AlertStatus


def alarm_facts(session: Session, epoch: Epoch | None, as_of_date: date) -> AlarmFacts | None:
    """The current epoch's non-closed alert: since, open days, tally, reviewed (DME-012)."""
    if epoch is None:
        return None
    alert = session.scalars(
        select(Alert).where(Alert.epoch_id == epoch.id, Alert.status != AlertStatus.CLOSED)
    ).first()
    if alert is None:
        return None
    tally = session.scalar(
        select(CusumState.current_tally).where(CusumState.epoch_id == alert.epoch_id)
    )
    reviews = session.scalar(
        select(func.count()).select_from(AlertReview).where(AlertReview.alert_id == alert.id)
    )
    return AlarmFacts(
        alert_id=alert.id,
        alarm_since=alert.local_date,
        open_days=(as_of_date - alert.local_date).days,
        tally=tally,
        reviewed=bool(reviews),
        status=alert.status,
    )


def baseline_restarted(epoch: Epoch | None, timezone: str) -> date | None:
    """Local date of the current epoch's start when `epoch_number > 1` (DME-012)."""
    if epoch is None or epoch.epoch_number <= 1:
        return None
    return local_date(epoch.started_at, timezone)


@dataclass(frozen=True)
class RestartCause:
    cause: str
    previous_device_code: str | None
    from_value: str
    to_value: str


def restart_cause(session: Session, epoch: Epoch) -> RestartCause | None:
    """First differing part versus epoch e - 1: device, firmware, software (DB-065, D-64)."""
    if epoch.epoch_number <= 1:
        return None
    previous = session.scalars(
        select(Epoch).where(
            Epoch.resident_id == epoch.resident_id, Epoch.epoch_number == epoch.epoch_number - 1
        )
    ).first()
    if previous is None:
        return None
    codes: dict[uuid.UUID, str] = {
        device_id: code
        for device_id, code in session.execute(
            select(Device.id, Device.device_code).where(
                Device.id.in_([previous.device_id, epoch.device_id])
            )
        ).all()
    }
    previous_code = codes.get(previous.device_id)
    if previous.device_id != epoch.device_id:
        return RestartCause(
            "device", previous_code, str(previous_code), str(codes.get(epoch.device_id))
        )
    if previous.device_firmware_version != epoch.device_firmware_version:
        return RestartCause(
            "firmware",
            previous_code,
            previous.device_firmware_version,
            epoch.device_firmware_version,
        )
    if previous.extraction_software_version != epoch.extraction_software_version:
        return RestartCause(
            "software",
            previous_code,
            previous.extraction_software_version,
            epoch.extraction_software_version,
        )
    return None


@dataclass(frozen=True)
class ScorePoint:
    local_date: date
    cusum_tally: float
    alarm_state: AlarmState


@dataclass(frozen=True)
class ScoresSeries:
    points: list[ScorePoint]
    baseline_first_date: date | None
    baseline_frozen_after_date: date | None


def scores_series(session: Session, epoch: Epoch, baseline_n: int) -> ScoresSeries:
    """The epoch's scores in `local_date` order with the baseline period (DB-043)."""
    rows = session.execute(
        select(Score.local_date, Score.cusum_tally, Score.alarm_state)
        .where(Score.epoch_id == epoch.id)
        .order_by(Score.local_date)
    ).all()
    progress = baseline_progress(session, epoch, baseline_n)
    return ScoresSeries(
        points=[ScorePoint(d, tally, state) for d, tally, state in rows],
        baseline_first_date=progress.first_session_date,
        baseline_frozen_after_date=progress.frozen_after_date,
    )


def device_silent_days(session: Session, device_id: uuid.UUID, window: Window) -> list[date]:
    """Days with ≥ 1 ledger row for the device and none `checked_in` (DB-044, FR-154)."""
    rows = session.execute(
        select(DayLedgerEntry.local_date)
        .join(DeviceAssignment, DeviceAssignment.resident_id == DayLedgerEntry.resident_id)
        .where(
            DeviceAssignment.device_id == device_id,
            DeviceAssignment.valid_from <= DayLedgerEntry.local_date,
            or_(
                DeviceAssignment.valid_to.is_(None),
                DeviceAssignment.valid_to >= DayLedgerEntry.local_date,
            ),
            DayLedgerEntry.local_date.between(window.start, window.end),
        )
        .group_by(DayLedgerEntry.local_date)
        .having(
            func.count(case((DayLedgerEntry.status == DayStatus.CHECKED_IN, 1))) == 0,
        )
        .order_by(DayLedgerEntry.local_date)
    ).all()
    return [row[0] for row in rows]


def device_gap_days(session: Session, device_id: uuid.UUID, window: Window) -> list[date]:
    """Silent days of a shared device: ledger rows `missing_device_gap` (TRD 23 §4.4.2)."""
    rows = session.execute(
        select(DayLedgerEntry.local_date)
        .where(
            DayLedgerEntry.device_id == device_id,
            DayLedgerEntry.status == DayStatus.MISSING_DEVICE_GAP,
            DayLedgerEntry.local_date.between(window.start, window.end),
        )
        .group_by(DayLedgerEntry.local_date)
        .order_by(DayLedgerEntry.local_date)
    ).all()
    return [row[0] for row in rows]


@dataclass(frozen=True)
class DeviceUse:
    in_use_since: date | None
    in_use_until: date | None


def device_use(session: Session, device_id: uuid.UUID, as_of_date: date) -> DeviceUse:
    """`in_use_since` = earliest `valid_from`; `in_use_until` = NULL while an assignment covers
    the as-of date, else the latest `valid_to` (DB-066, D-82)."""
    since, latest_to = session.execute(
        select(func.min(DeviceAssignment.valid_from), func.max(DeviceAssignment.valid_to)).where(
            DeviceAssignment.device_id == device_id
        )
    ).one()
    covering = session.scalar(
        select(func.count())
        .select_from(DeviceAssignment)
        .where(
            DeviceAssignment.device_id == device_id,
            DeviceAssignment.valid_from <= as_of_date,
            or_(DeviceAssignment.valid_to.is_(None), DeviceAssignment.valid_to >= as_of_date),
        )
    )
    return DeviceUse(in_use_since=since, in_use_until=None if covering else latest_to)


def last_upload(session: Session, device_ids: Iterable[uuid.UUID]) -> dict[uuid.UUID, datetime]:
    """Max `raw_sessions.timestamp_utc` per device (TRD 23 §4.4.2)."""
    rows = session.execute(
        select(RawSession.device_id, func.max(RawSession.timestamp_utc))
        .where(RawSession.device_id.in_(list(device_ids)))
        .group_by(RawSession.device_id)
    ).all()
    return {device_id: ts for device_id, ts in rows}


@dataclass(frozen=True)
class DeviceLabel:
    device_code: str | None
    shared: bool
    was_device_code: str | None


def device_label(
    session: Session, resident: Resident, as_of_date: date, shared_device_min_residents: int
) -> DeviceLabel:
    """Current device, "(shared)" and "(was <code>)" facts of a resident (TRD 23 §4.4.1)."""
    assignments = session.execute(
        select(DeviceAssignment, Device.device_code)
        .join(Device, Device.id == DeviceAssignment.device_id)
        .where(DeviceAssignment.resident_id == resident.id)
        .order_by(DeviceAssignment.valid_from)
    ).all()
    current = previous = None
    for i, (assignment, code) in enumerate(assignments):
        covers = assignment.valid_from <= as_of_date and (
            assignment.valid_to is None or assignment.valid_to >= as_of_date
        )
        if covers:
            current = (assignment, code)
            previous = assignments[i - 1] if i > 0 else None
    if current is None:
        return DeviceLabel(None, False, None)
    assignment, code = current
    sharers = session.scalar(
        select(func.count(func.distinct(DeviceAssignment.resident_id))).where(
            DeviceAssignment.device_id == assignment.device_id,
            DeviceAssignment.valid_from <= as_of_date,
            or_(DeviceAssignment.valid_to.is_(None), DeviceAssignment.valid_to >= as_of_date),
        )
    )
    was = None
    if previous is not None:
        prev_assignment, prev_code = previous
        if prev_assignment.valid_to == assignment.valid_from - timedelta(days=1):
            was = prev_code
    return DeviceLabel(code, int(sharers or 0) >= shared_device_min_residents, was)


@dataclass(frozen=True)
class CheckinEventSource:
    """One source row of a check-in log event (TRD 23 §4.4.4); DTOs are built by FEAT-028."""

    event_type: str
    local_date: date
    detail: dict[str, object]


def checkin_event_sources(
    session: Session, resident: Resident, start: date, end: date, timezone: str
) -> list[CheckinEventSource]:
    """Alerts, first scores, baseline completion, set-aside, quarantined, missed, device-silent
    and restart rows of one resident between `start` and `end` (TRD 23 §4.4.4, FR-15)."""
    events: list[CheckinEventSource] = []
    for alert in session.scalars(
        select(Alert).where(Alert.resident_id == resident.id, Alert.local_date.between(start, end))
    ):
        events.append(CheckinEventSource("alarm_on", alert.local_date, {"alert_id": alert.id}))
    firsts = session.execute(
        select(Score.epoch_id, func.min(Score.local_date))
        .where(Score.resident_id == resident.id)
        .group_by(Score.epoch_id)
    ).all()
    for epoch_id, first in firsts:
        if start <= first <= end:
            events.append(CheckinEventSource("watching_started", first, {"epoch_id": epoch_id}))
    for composite in session.scalars(
        select(Baseline).where(
            Baseline.resident_id == resident.id, Baseline.feature_key == "composite"
        )
    ):
        day = _session_local_date(session, composite.epoch_id, composite.frozen_after_session_id)
        if day is not None and start <= day <= end:
            events.append(
                CheckinEventSource("baseline_complete", day, {"n_sessions": composite.n_sessions})
            )
    for row in session.scalars(
        select(ProcessedSession).where(
            ProcessedSession.resident_id == resident.id,
            ProcessedSession.status.in_([SessionStatus.SET_ASIDE, SessionStatus.QUARANTINED]),
            ProcessedSession.local_date.between(start, end),
        )
    ):
        events.append(
            CheckinEventSource(
                str(row.status),
                row.local_date,
                {"session_id": row.session_id, "reasons": row.reason_text},
            )
        )
    for entry in session.scalars(
        select(DayLedgerEntry).where(
            DayLedgerEntry.resident_id == resident.id,
            DayLedgerEntry.status != DayStatus.CHECKED_IN,
            DayLedgerEntry.local_date.between(start, end),
        )
    ):
        kind = "missed" if entry.status == DayStatus.MISSING_RESIDENT else "device_silent"
        events.append(CheckinEventSource(kind, entry.local_date, {"device_id": entry.device_id}))
    for epoch in session.scalars(
        select(Epoch).where(and_(Epoch.resident_id == resident.id, Epoch.epoch_number > 1))
    ):
        day = local_date(epoch.started_at, timezone)
        cause = restart_cause(session, epoch)
        if start <= day <= end:
            events.append(
                CheckinEventSource(
                    "baseline_restarted",
                    day,
                    {"epoch_number": epoch.epoch_number, "restart_cause": cause},
                )
            )
    return events
