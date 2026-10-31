"""Resident overview and detail (TRD 05 API-070..API-076, API-138; TRD 23 §4.4.1, §4.4.3;
TRD 24 D-109, D-114; FEAT-027, FEAT-028).

Display status, attention flags and every count are derived on read from the derived tables and
never stored (DME-011). The as-of local date is that of the latest succeeded run (API-069); before
any run it is the current facility-local date.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from backend.core.config import Settings
from backend.core.errors import ResidentNotFoundError
from backend.models import AlertStatus, Epoch, Resident, ResidentCohort, ResidentStatus
from backend.repositories import read_models as rm
from backend.repositories.config_repository import ConfigRepository
from backend.repositories.device_repository import DeviceRepository
from backend.repositories.resident_repository import ResidentRepository
from backend.schemas.common import Meta
from backend.services import meta_service

Sort = Literal["alarm", "resident_id", "last_checkin"]
CHANGED, NEEDS_ATTENTION, LEARNING, USUAL = 0, 1, 2, 3
_CODE = re.compile(r"^([A-Z]*)(\d*)(.*)$")


def natural_key(code: str) -> tuple[str, int, str, str]:
    """`R2` before `R10`, `D07` before `D07B` before `D08` (AGT-052)."""
    match = _CODE.match(code)
    assert match is not None  # noqa: S101 - the pattern matches every string
    prefix, number, rest = match.groups()
    return prefix, int(number) if number else -1, rest, code


@dataclass(frozen=True)
class ReadContext:
    """What every read endpoint needs: `meta`, the facility zone and the active parameters."""

    meta: Meta
    tz: ZoneInfo
    as_of_date: date
    baseline_n: int
    cusum_h: float
    shared_device_min_residents: int

    def local(self, instant: datetime | None) -> datetime | None:
        return instant.astimezone(self.tz) if instant is not None else None

    def local_date(self, instant: datetime) -> date:
        return instant.astimezone(self.tz).date()


def read_context(
    session: Session, settings: Settings, clock: Callable[[], datetime] | None = None
) -> ReadContext:
    meta = meta_service.get_meta(session, settings)
    tz = ZoneInfo(settings.facility_tz)
    instant = meta.as_of or (clock or (lambda: datetime.now(UTC)))()
    values = ConfigRepository(session).values_for_profile(settings.pipeline_profile)
    return ReadContext(
        meta=meta,
        tz=tz,
        as_of_date=instant.astimezone(tz).date(),
        baseline_n=int(values["baseline_n"]),
        cusum_h=float(values["cusum_h"]),
        shared_device_min_residents=int(values.get("shared_device_min_residents", 2)),
    )


@dataclass
class ResidentFacts:
    """The derived facts shared by the overview row and the detail page (FEAT-027-FR-03..09)."""

    resident: Resident
    epoch: Epoch | None
    status: str
    attention_reasons: list[str]
    alert_id: uuid.UUID | None
    alarm_since: date | None
    alarm_reviewed: bool | None
    progress: rm.BaselineProgress
    restart: rm.RestartCause | None
    restarted_on: date | None
    device: rm.DeviceLabel
    last_checkin_at: datetime | None
    counts: rm.ActivityCounts
    window: rm.Window

    @property
    def needs_attention(self) -> bool:
        return bool(self.attention_reasons)

    @property
    def group(self) -> int:
        """Display status, first match Changed, Needs attention, Learning, Usual (D-109)."""
        if self.status == "alarm_on":
            return CHANGED
        if self.needs_attention:
            return NEEDS_ATTENTION
        return LEARNING if self.status == "baseline_forming" else USUAL


def resident_facts(
    session: Session, ctx: ReadContext, residents: Sequence[Resident]
) -> list[ResidentFacts]:
    ids = [r.id for r in residents]
    epochs = rm.current_epochs(session, ids)
    alerts = rm.open_alerts_by_epoch(session, [e.id for e in epochs.values()])
    attention = rm.attention_kinds(session, ids)
    counts = rm.activity_counts(session, residents, ctx.as_of_date)
    last = rm.last_checkin(session, ids)
    facts = []
    for resident in residents:
        epoch = epochs.get(resident.id)
        alert = alerts.get(epoch.id) if epoch is not None else None
        progress = rm.baseline_progress(session, epoch, ctx.baseline_n)
        if alert is not None:
            status = "alarm_on"
        elif not progress.frozen:
            status = "baseline_forming"
        else:
            status = "no_alarm"
        restart = rm.restart_cause(session, epoch) if epoch is not None else None
        facts.append(
            ResidentFacts(
                resident=resident,
                epoch=epoch,
                status=status,
                attention_reasons=attention.get(resident.id, []),
                alert_id=alert.id if alert else None,
                alarm_since=alert.local_date if alert else None,
                alarm_reviewed=(alert.status == AlertStatus.ACKNOWLEDGED) if alert else None,
                progress=progress,
                restart=restart,
                restarted_on=rm.baseline_restarted(epoch, ctx.tz.key),
                device=rm.device_label(
                    session, resident, ctx.as_of_date, ctx.shared_device_min_residents
                ),
                last_checkin_at=last.get(resident.id),
                counts=counts.get(resident.id, rm.ActivityCounts()),
                window=rm.window_for(resident.enrolled_on, ctx.as_of_date),
            )
        )
    return facts


def _sorted(facts: list[ResidentFacts], sort: Sort) -> list[ResidentFacts]:
    if sort == "resident_id":
        return sorted(facts, key=lambda f: natural_key(f.resident.resident_code))
    if sort == "last_checkin":
        return sorted(
            facts,
            key=lambda f: (
                f.last_checkin_at is None,
                -f.last_checkin_at.timestamp() if f.last_checkin_at else 0.0,
                natural_key(f.resident.resident_code),
            ),
        )
    return sorted(
        facts,
        key=lambda f: (
            f.group,
            f.alarm_since if f.group == CHANGED and f.alarm_since else date.min,
            natural_key(f.resident.resident_code),
        ),
    )


def _counts(f: ResidentFacts) -> dict[str, int]:
    c = f.counts
    return {
        "used": c.used,
        "set_aside": c.set_aside,
        "quarantined": c.quarantined,
        "missed": c.missed,
    }


def _row(f: ResidentFacts, ctx: ReadContext) -> dict[str, Any]:
    r = f.resident
    epoch_number = f.epoch.epoch_number if f.epoch else None
    restarted = epoch_number is not None and epoch_number > 1
    return {
        "resident_code": r.resident_code,
        "cohort": r.cohort.value,
        "resident_status": r.status.value,
        "device_code": f.device.device_code,
        "device_shared": f.device.shared,
        "previous_device_code": f.device.was_device_code,
        "status": f.status,
        "needs_attention": f.needs_attention,
        "attention_reasons": f.attention_reasons,
        "alarm_since": f.alarm_since,
        "open_alert_id": f.alert_id,
        "alarm_reviewed": f.alarm_reviewed,
        "current_epoch": epoch_number,
        "baseline_restarted_on": f.restarted_on if restarted else None,
        "restart_cause": f.restart.cause if restarted and f.restart else None,
        "baseline_progress": {"n_usable": f.progress.n, "n_required": f.progress.of},
        "last_checkin_at": f.last_checkin_at,
        "last_checkin_local": ctx.local(f.last_checkin_at),
        "last_30_days": _counts(f),
    }


def overview(
    session: Session,
    ctx: ReadContext,
    *,
    sort: Sort,
    cohort: str,
    include_withdrawn: bool,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    """`ResidentsOverviewResponse` (TRD 19 E-08); `summary` covers every matching resident."""
    residents = [
        r
        for r in ResidentRepository(session).list_all()
        if r.cohort == ResidentCohort(cohort)
        and (include_withdrawn or r.status == ResidentStatus.ACTIVE)
    ]
    facts = _sorted(resident_facts(session, ctx, residents), sort)
    groups = [f.group for f in facts]
    start = ctx.as_of_date - timedelta(days=rm.WINDOW_DAYS - 1)
    return {
        "meta": ctx.meta,
        "window": {"from": start, "to": ctx.as_of_date, "days": rm.WINDOW_DAYS},
        "summary": {
            "changed": groups.count(CHANGED),
            "needs_attention": groups.count(NEEDS_ATTENTION),
            "learning": groups.count(LEARNING),
            "usual": groups.count(USUAL),
        },
        "items": [_row(f, ctx) for f in facts[offset : offset + limit]],
        "total": len(facts),
        "limit": limit,
        "offset": offset,
    }


def get_resident(session: Session, resident_code: str) -> Resident:
    resident = ResidentRepository(session).get_by_code(resident_code)
    if resident is None:
        raise ResidentNotFoundError(f"No resident {resident_code}.")
    return resident


def detail(session: Session, ctx: ReadContext, resident_code: str) -> dict[str, Any]:
    """`ResidentDetail` (TRD 19 E-09), for withdrawn residents too (FEAT-028)."""
    resident = get_resident(session, resident_code)
    f = resident_facts(session, ctx, [resident])[0]
    row = _row(f, ctx)
    epoch = f.epoch
    codes = rm.device_codes(session)
    shared_with: list[str] = []
    if f.device.device_code is not None:
        device = DeviceRepository(session).get_by_code(f.device.device_code)
        if device is not None:
            sharing = DeviceRepository(session).residents_on_device(device.id, ctx.as_of_date)
            shared_with = [r.resident_code for r in sharing if r.id != resident.id]
    composite = rm.composite_baseline(session, epoch)
    frozen = f.progress.frozen and composite is not None
    tally = rm.current_tally(session, epoch)
    current_epoch = None
    if epoch is not None:
        current_epoch = {
            "epoch_number": epoch.epoch_number,
            "device_code": codes.get(epoch.device_id, ""),
            "device_firmware_version": epoch.device_firmware_version,
            "extraction_software_version": epoch.extraction_software_version,
            "started_at": epoch.started_at,
            "started_on": ctx.local_date(epoch.started_at),
            "from_value": f.restart.from_value if f.restart else None,
            "to_value": f.restart.to_value if f.restart else None,
        }
    return {
        "meta": ctx.meta,
        "resident_code": resident.resident_code,
        "cohort": row["cohort"],
        "resident_status": row["resident_status"],
        "sex": resident.sex,
        "enrolled_on": resident.enrolled_on,
        "admitted_on": resident.admitted_on,
        "withdrawn_on": resident.withdrawn_on,
        "status": f.status,
        "needs_attention": f.needs_attention,
        "attention_reasons": f.attention_reasons,
        "alarm_reviewed": f.alarm_reviewed,
        "restart_cause": row["restart_cause"],
        "device": {
            "device_code": f.device.device_code,
            "shared": f.device.shared,
            "shared_with": sorted(shared_with, key=natural_key),
            "previous_device_code": f.device.was_device_code,
        },
        "current_epoch": current_epoch,
        "epoch_count": len(rm.epochs_of(session, resident.id)),
        "baseline": {
            "state": "frozen" if frozen else "forming",
            "n_usable": f.progress.n,
            "n_required": f.progress.of,
            "first_session_id": composite.first_session_id if frozen and composite else None,
            "frozen_after_session_id": (
                composite.frozen_after_session_id if frozen and composite else None
            ),
            "first_local_date": f.progress.first_session_date if frozen else None,
            "frozen_after_local_date": f.progress.frozen_after_date if frozen else None,
        },
        "watching_since": rm.watching_since(session, epoch, ctx.baseline_n),
        "alarm_since": f.alarm_since,
        "open_alert_id": f.alert_id,
        "current_tally": tally,
        "last_checkin_at": f.last_checkin_at,
        "last_checkin_local": ctx.local(f.last_checkin_at),
        "window": {"from": f.window.start, "to": f.window.end, "days": f.window.days},
        "last_30_days": _counts(f),
        "explanation": {
            "compared_with": "own_baseline",
            "alarm_crossed_on": f.alarm_since,
            "still_above_line": tally is not None and tally >= ctx.cusum_h,
            "baseline_restarted_on": row["baseline_restarted_on"],
            "baseline_n_usable": f.progress.n,
            "baseline_n_required": f.progress.of,
        },
    }
