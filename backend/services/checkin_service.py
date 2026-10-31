"""The resident check-in log (TRD 05 API-077; TRD 19 E-10; TRD 23 §4.4.4; FEAT-028).

Events are derived on read from alerts, scores, baselines, processed sessions, the day ledger and
epochs; duplicates and usable check-ins never appear (FR-182, D-67).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from backend.repositories import read_models as rm
from backend.services.resident_service import ReadContext, get_resident

# Same-date order of TRD 11 UX-141 (TRD 19 E-10); the frontend does not re-sort (FE-101).
EVENT_ORDER: tuple[str, ...] = (
    "alarm_on",
    "watching_started",
    "baseline_complete",
    "baseline_restarted",
    "quarantined",
    "set_aside",
    "device_silent",
    "missed",
    "checkins_started",
)
_RANK = {kind: rank for rank, kind in enumerate(EVENT_ORDER)}
MISSED_DETAIL = "no record received"


def _event(local_date: date, event_type: str, **values: Any) -> dict[str, Any]:
    """A `CheckinEvent` with every property present (OAS-012)."""
    event: dict[str, Any] = dict.fromkeys(
        ("epoch_number", "session_id", "detail", "cusum_tally", "restart_cause",
         "previous_device_code", "from_value", "to_value", "device_code"),
    )  # fmt: skip
    event.update(local_date=local_date, event_type=event_type, **values)
    return event


def _build(
    source: rm.CheckinEventSource,
    epoch_number: int | None,
    codes: dict[Any, str],
    cusum_h: float,
) -> dict[str, Any]:
    d, kind, day = source.detail, source.event_type, source.local_date
    if kind == "alarm_on":
        return _event(
            day, kind, epoch_number=epoch_number, session_id=d["session_id"],
            detail=f"tally crossed {cusum_h:.1f}", cusum_tally=d["cusum_value"],
        )  # fmt: skip
    if kind == "watching_started":
        return _event(day, kind, epoch_number=epoch_number, session_id=d["session_id"])
    if kind == "baseline_complete":
        n = d["n_sessions"]
        return _event(
            day, kind, epoch_number=epoch_number, session_id=d["session_id"], detail=f"{n} of {n}"
        )
    if kind == "baseline_restarted":
        cause: rm.RestartCause | None = d["restart_cause"]
        number = d["epoch_number"]
        return _event(
            day, kind, epoch_number=number,
            detail=f"new epoch {number} on device {codes.get(d['device_id'], '')}",  # D-82
            restart_cause=cause.cause if cause else None,
            previous_device_code=cause.previous_device_code if cause else None,
            from_value=cause.from_value if cause else None,
            to_value=cause.to_value if cause else None,
        )  # fmt: skip
    if kind in ("set_aside", "quarantined"):
        return _event(
            day, kind, epoch_number=epoch_number, session_id=d["session_id"], detail=d["reasons"]
        )
    if kind == "missed":
        return _event(day, kind, detail=MISSED_DETAIL)
    if kind == "device_silent":
        return _event(day, kind, detail=d["reason"] or None)
    return _event(  # checkins_started (D-113, D-114)
        day, kind, epoch_number=epoch_number, session_id=d["session_id"],
        device_code=codes.get(d["device_id"]),
    )  # fmt: skip


def events(
    session: Session, ctx: ReadContext, resident_code: str, start: date, end: date
) -> list[dict[str, Any]]:
    """Every event of one resident between `start` and `end`, newest first (API-077)."""
    resident = get_resident(session, resident_code)
    numbers: dict[Any, int] = {e.id: e.epoch_number for e in rm.epochs_of(session, resident.id)}
    codes = rm.device_codes(session)
    out = [
        _build(source, numbers.get(source.detail.get("epoch_id")), codes, ctx.cusum_h)
        for source in rm.checkin_event_sources(session, resident, start, end, ctx.tz.key)
    ]
    out.sort(
        key=lambda e: (-e["local_date"].toordinal(), _RANK[e["event_type"]], e["session_id"] or "")
    )
    return out
