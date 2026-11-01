"""Rule-based data-quality alerts (TRD 09 §4.9 CUS-043..CUS-046; TRD 07 ANL-059; FEAT-050).

Recomputed on every run over the 30 facility-local days ending on the as-of local date (never
before a resident's enrolment). Data alerts are for the study team: they never create an alarm or
touch a tally. Output order: kind (enum order), then resident or device code in natural order.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import date, datetime, timedelta

from analytics.config import (
    AdjustedRecord,
    DataAlert,
    DeviceAssignment,
    EpochSummary,
    LedgerDay,
    PipelineConfig,
    ResidentInfo,
)
from analytics.day_ledger import device_on, enrolled_on_day
from analytics.quality_screening import NOISE, QUALITY_FLAG, TOO_SHORT

WINDOW_DAYS = 30
MIN_RECEIVED = 10  # fixed rule constant for high_set_aside (contract §19)
KIND_ORDER = ("baseline_stalled", "possible_other_speaker", "high_set_aside", "device_silent")
SET_ASIDE_KINDS = ((NOISE, "noise"), (QUALITY_FLAG, "quality flag"), (TOO_SHORT, "too short"))


def natural_key(code: str) -> tuple[object, ...]:
    """R2 before R10 (TRD 05 API-070)."""
    return tuple(int(p) if p.isdigit() else p for p in re.split(r"(\d+)", code))


def month_day(day: date) -> str:
    return f"{day:%b} {day.day}"


def join_and(items: Sequence[str]) -> str:
    """ "R02 and R03", "R01, R02 and R03"."""
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def window(as_of: datetime, config: PipelineConfig) -> tuple[date, date]:
    end = as_of.astimezone(config.tz).date()
    return end - timedelta(days=WINDOW_DAYS - 1), end


def _in_window(day: date, start: date, end: date, info: ResidentInfo) -> bool:
    return max(start, info.enrolled_on) <= day <= end


def generate_data_alerts(
    sessions: Sequence[AdjustedRecord],
    ledger: Sequence[LedgerDay],
    epochs: Sequence[EpochSummary],
    residents: Sequence[ResidentInfo],
    assignments: Sequence[DeviceAssignment],
    config: PipelineConfig,
    as_of: datetime,
) -> list[DataAlert]:
    start, end = window(as_of, config)
    op = config.operational
    active = sorted((r for r in residents if r.status != "withdrawn"),
                    key=lambda r: natural_key(r.resident_code))  # fmt: skip
    current: dict[str, EpochSummary] = {}
    for e in epochs:
        if e.resident_code not in current or e.epoch_number > current[e.resident_code].epoch_number:
            current[e.resident_code] = e
    alerts: list[DataAlert] = []
    stalled: set[str] = set()
    for info in active:
        code = info.resident_code
        mine = [s for s in sessions if s.record.resident_code == code and s.status != "duplicate"
                and _in_window(s.local_date, start, end, info)]  # fmt: skip
        days = [d for d in ledger if d.resident_code == code
                and _in_window(d.local_date, start, end, info)]  # fmt: skip
        missed = sum(d.status != "checked_in" for d in days)
        set_aside = [s for s in mine if s.status == "set_aside"]
        epoch = current.get(code)
        if (
            op.data_alert_baseline_stalled_enabled and epoch is not None
            and not epoch.baseline_formed
            and (end - epoch.started_at.astimezone(config.tz).date()).days + 1 >= config.baseline_n
        ):  # fmt: skip
            n, big_n = epoch.usable_count, config.baseline_n
            stalled.add(code)
            alerts.append(DataAlert(
                "baseline_stalled", code, None, f"{code} · baseline stuck at {n} of {big_n}",
                f"baseline stuck at {n} of {big_n}. {missed} missed and {len(set_aside)} set "
                "aside in 30 days.",
            ))  # fmt: skip
        quarantined = sorted(s.local_date for s in mine if s.status == "quarantined")
        if quarantined:
            q = len(quarantined)
            dates = ", ".join(month_day(d) for d in quarantined)
            noun = "check-in" if q == 1 else "check-ins"
            alerts.append(DataAlert(
                "possible_other_speaker", code, None, f"{code} · possible other speaker",
                f"{q} {noun} held back as possible other voice ({dates}).", tuple(quarantined),
            ))  # fmt: skip
        received = len(mine)
        if (
            code not in stalled and received >= MIN_RECEIVED
            and len(set_aside) / received >= op.data_alert_set_aside_fraction
        ):  # fmt: skip
            kinds = [label for reason, label in SET_ASIDE_KINDS
                     if any(reason in s.reasons for s in set_aside)]  # fmt: skip
            alerts.append(DataAlert(
                "high_set_aside", code, None, f"{code} · many check-ins set aside",
                f"{len(set_aside)} of {received} received check-ins set aside "
                f"({', '.join(kinds)}).", tuple(sorted({s.local_date for s in set_aside})),
            ))  # fmt: skip
    alerts.extend(_device_silent(ledger, active, assignments, config, start, end))
    return sorted(alerts, key=_order)


def _order(alert: DataAlert) -> tuple[int, tuple[object, ...]]:
    return (
        KIND_ORDER.index(alert.kind),
        natural_key(alert.resident_code or alert.device_code or ""),
    )


def _device_silent(
    ledger: Sequence[LedgerDay], residents: Sequence[ResidentInfo],
    assignments: Sequence[DeviceAssignment], config: PipelineConfig, start: date, end: date,
) -> list[DataAlert]:  # fmt: skip
    status = {(d.resident_code, d.local_date): d.status for d in ledger}
    devices = sorted({a.device_code for a in assignments}, key=natural_key)
    out = []
    for device in devices:
        silent: list[tuple[date, list[str]]] = []
        day = start
        while day <= end:
            users = sorted(
                (r.resident_code for r in residents if enrolled_on_day(r, day)
                 and device_on(r.resident_code, day, assignments) == device),
                key=natural_key,
            )  # fmt: skip
            if users and all(
                status.get((u, day)) in ("missing_resident", "missing_device_gap") for u in users
            ):
                silent.append((day, users))
            day += timedelta(days=1)
        flagged = _flagged(silent, config.operational.data_alert_device_silent_days,
                           config.shared_device_min_residents)  # fmt: skip
        if not flagged:
            continue
        affected = sorted({u for _, users in flagged for u in users}, key=natural_key)
        days = tuple(d for d, _ in flagged)
        who = f"Affected {join_and(affected)}."
        if len(days) == 1:
            title = f"{device} · device silent all day"
            detail = f"silent all day {month_day(days[0])}. {who}"
        else:
            title = f"{device} · device silent on {len(days)} days"
            detail = f"silent on {len(days)} days ({', '.join(month_day(d) for d in days)}). {who}"
        out.append(DataAlert("device_silent", None, device, title, detail, days))
    return out


def _flagged(
    silent: list[tuple[date, list[str]]], min_run: int, shared: int
) -> list[tuple[date, list[str]]]:
    """Shared-device silent days always; single-resident silent days in runs of >= min_run
    consecutive silent single-resident days."""
    keep: list[tuple[date, list[str]]] = []
    run: list[tuple[date, list[str]]] = []

    def close() -> None:
        if len(run) >= min_run:
            keep.extend(run)
        run.clear()

    for item in silent:
        day, users = item
        if len(users) >= shared:
            close()
            keep.append(item)
            continue
        if run and run[-1][0] != day - timedelta(days=1):
            close()
        run.append(item)
    close()
    return sorted(keep, key=lambda item: item[0])
