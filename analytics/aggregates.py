"""Study team page aggregates over the 30-day window (TRD 07 §4.13 ANL-061..ANL-065; FEAT-051).

Everything is derived from the same pipeline result (sessions, ledger, epochs, alerts, data alerts)
so the counts equal the pipeline's status counts (ANL-062). Percentages are integer half-up
`pct(n, d) = (200·n + d) // (2·d)`, null when d = 0 (ANL-063). Notes that need human state (the
alarm review state) are left to the backend (ANL-065).

Shapes (the backend maps them to the TRD 19 E-18 DTO):

- `kpis`: `checkins_received` and `used_for_scoring` {value, expected, percent};
  `baselines_formed` {value, total, forming, restarts, note}; `alarms_raised` {value, residents}.
- `daily_series`: {local_date, used, set_aside, quarantined, missed, silent_device_codes}.
- `funnel`: four steps {step, value, note} plus the counts each step needs.
- `by_resident`: {resident_code, days, used_days, set_aside_days, quarantined_days, missed_days,
  used_percent}, sorted by used_percent then natural resident order.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, timedelta
from typing import Any

from analytics.config import (
    AdjustedRecord,
    AlertEvent,
    AnalyticsSummary,
    DataAlert,
    EpochSummary,
    LedgerDay,
    PipelineConfig,
    ResidentInfo,
)
from analytics.data_alerts import natural_key, window
from analytics.quality_screening import NOISE, QUALITY_FLAG, TOO_SHORT

DAY_ORDER = ("usable", "set_aside", "quarantined")  # a day counts once, in the first that applies


def pct(n: int, d: int) -> int | None:
    return None if d == 0 else (200 * n + d) // (2 * d)


def _days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def _enrolled_days(info: ResidentInfo, start: date, end: date) -> list[date]:
    last = min(end, info.withdrawn_on) if info.withdrawn_on else end
    return _days(max(start, info.enrolled_on), last)


def _times(n: int) -> str:
    return "once" if n == 1 else "twice" if n == 2 else f"{n} times"


def build_analytics_summary(
    sessions: Sequence[AdjustedRecord],
    ledger: Sequence[LedgerDay],
    epochs: Sequence[EpochSummary],
    alerts: Sequence[AlertEvent],
    data_alerts: Sequence[DataAlert],
    residents: Sequence[ResidentInfo],
    config: PipelineConfig,
    as_of: datetime,
) -> AnalyticsSummary:
    start, end = window(as_of, config)
    active = sorted((r for r in residents if r.status != "withdrawn"),
                    key=lambda r: natural_key(r.resident_code))  # fmt: skip
    codes = {r.resident_code for r in active}
    enrolled = {r.resident_code: _enrolled_days(r, start, end) for r in active}
    expected = sum(len(days) for days in enrolled.values())

    def in_period(code: str, day: date) -> bool:
        return code in codes and day in set(enrolled[code])

    received = [s for s in sessions if s.status != "duplicate"
                and in_period(s.record.resident_code, s.local_date)]  # fmt: skip
    duplicates = [s for s in sessions if s.status == "duplicate"
                  and in_period(s.record.resident_code, s.local_date)]  # fmt: skip
    usable = [s for s in received if s.status == "usable"]
    set_aside = [s for s in received if s.status == "set_aside"]
    quarantined = [s for s in received if s.status == "quarantined"]
    ledger_in = [d for d in ledger if in_period(d.resident_code, d.local_date)]
    missed = [d for d in ledger_in if d.status != "checked_in"]

    day_status: dict[tuple[str, date], str] = {}
    for s in received:
        key = (s.record.resident_code, s.local_date)
        if key not in day_status or DAY_ORDER.index(s.status) < DAY_ORDER.index(day_status[key]):
            day_status[key] = s.status
    for d in missed:
        day_status.setdefault((d.resident_code, d.local_date), "missed")

    silent: dict[date, list[str]] = {}
    for alert in data_alerts:
        if alert.kind == "device_silent" and alert.device_code:
            for day in alert.days:
                silent.setdefault(day, []).append(alert.device_code)

    daily = []
    for day in _days(start, end):
        statuses = [day_status.get((code, day)) for code in codes if day in set(enrolled[code])]
        daily.append({
            "local_date": day, "used": statuses.count("usable"),
            "set_aside": statuses.count("set_aside"), "quarantined": statuses.count("quarantined"),
            "missed": statuses.count("missed"),
            "silent_device_codes": sorted(silent.get(day, []), key=natural_key),
        })  # fmt: skip

    current: dict[str, EpochSummary] = {}
    for e in epochs:
        if e.resident_code not in current or e.epoch_number > current[e.resident_code].epoch_number:
            current[e.resident_code] = e
    forming = [
        r.resident_code for r in active
        if not (r.resident_code in current and current[r.resident_code].baseline_formed)
    ]  # fmt: skip
    restarts = {
        r.resident_code: current[r.resident_code].epoch_number - 1 for r in active
        if r.resident_code in current and current[r.resident_code].epoch_number > 1
    }  # fmt: skip
    parts = []
    if forming:
        parts.append(f"{', '.join(forming)} still forming")
    parts.extend(f"{code} restarted {_times(n)}" for code, n in restarts.items())
    period_alerts = sorted(
        (a for a in alerts if a.resident_code in codes and start <= a.local_date <= end),
        key=lambda a: (natural_key(a.resident_code), a.epoch_number),
    )

    kpis: dict[str, Any] = {
        "checkins_received": {"value": len(received), "expected": expected,
                              "percent": pct(len(received), expected)},
        "used_for_scoring": {"value": len(usable), "expected": expected,
                             "percent": pct(len(usable), expected)},
        "baselines_formed": {"value": len(active) - len(forming), "total": len(active),
                             "forming": forming, "restarts": restarts, "note": "; ".join(parts)},
        "alarms_raised": {"value": len(period_alerts),
                          "residents": [a.resident_code for a in period_alerts]},
    }  # fmt: skip
    return AnalyticsSummary(
        period_start=start, period_end=end, kpis=kpis, daily_series=tuple(daily),
        funnel=_funnel(active, enrolled, start, end, expected, received, duplicates, missed,
                       set_aside, quarantined),
        by_resident=_by_resident(active, enrolled, day_status),
    )  # fmt: skip


def _funnel(
    active: Sequence[ResidentInfo], enrolled: dict[str, list[date]], start: date, end: date,
    expected: int, received: Sequence[AdjustedRecord], duplicates: Sequence[AdjustedRecord],
    missed: Sequence[LedgerDay], set_aside: Sequence[AdjustedRecord],
    quarantined: Sequence[AdjustedRecord],
) -> tuple[dict[str, Any], ...]:  # fmt: skip
    days = (end - start).days + 1
    whole = all(len(d) == days for d in enrolled.values())
    expected_note = (f"{len(active)} residents × {days} days" if whole  # noqa: RUF001
                     else f"sum of days enrolled across {len(active)} residents")  # fmt: skip
    dup = len(duplicates)
    copies = "1 duplicate copy removed" if dup == 1 else f"{dup} duplicate copies removed"
    reasons = {
        "quality_flag_poor": sum(QUALITY_FLAG in s.reasons for s in set_aside),
        "noise_above_limit": sum(NOISE in s.reasons for s in set_aside),
        "speech_too_short": sum(TOO_SHORT in s.reasons for s in set_aside),
    }
    multi = [s for s in set_aside if len(s.reasons) > 1]
    quality_note = (
        f"{len(set_aside)} set aside: quality flag {reasons['quality_flag_poor']}, "
        f"noise {reasons['noise_above_limit']}, too short {reasons['speech_too_short']}"
    )
    if multi:
        how = "two reasons" if all(len(s.reasons) == 2 for s in multi) else "more than one reason"
        quality_note += f" ({len(multi)} had {how})"
    passed = len(received) - len(set_aside)
    return (
        {"step": "expected", "value": expected, "note": expected_note,
         "residents": len(active), "days": days},
        {"step": "received", "value": len(received), "note": f"{len(missed)} missed; {copies}",
         "missed": len(missed), "duplicates_removed": dup},
        {"step": "passed_quality", "value": passed, "note": quality_note,
         "set_aside": len(set_aside), "set_aside_reasons": reasons,
         "set_aside_multi_reason": len(multi)},
        {"step": "used", "value": passed - len(quarantined),
         "note": f"{len(quarantined)} held back as possible other voice",
         "quarantined": len(quarantined)},
    )  # fmt: skip


def _by_resident(
    active: Sequence[ResidentInfo], enrolled: dict[str, list[date]],
    day_status: dict[tuple[str, date], str],
) -> tuple[dict[str, Any], ...]:  # fmt: skip
    rows = []
    for info in active:
        code = info.resident_code
        statuses = [day_status.get((code, d)) for d in enrolled[code]]
        days = len(statuses)
        used_days = statuses.count("usable")
        rows.append({
            "resident_code": code, "days": days, "used_days": used_days,
            "set_aside_days": statuses.count("set_aside"),
            "quarantined_days": statuses.count("quarantined"),
            "missed_days": statuses.count("missed"), "used_percent": pct(used_days, days),
        })  # fmt: skip
    rows.sort(key=lambda r: (-1 if r["used_percent"] is None else r["used_percent"],
                             natural_key(str(r["resident_code"]))))  # fmt: skip
    return tuple(rows)
