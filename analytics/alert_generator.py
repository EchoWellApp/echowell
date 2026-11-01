"""Alarm events, epoch-end closure facts and "Leaning most" (TRD 09 §4.2, §4.8 CUS-011..CUS-013,
CUS-041; FEAT-048).

One `AlertEvent` per resident-epoch whose scores contain a "rings" session; it carries the facts
the persistence service needs to upsert on `(epoch_id, session_id)` and to close the alert when a
later epoch exists. The engine never closes an alert itself and never notifies anyone.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

from analytics.config import (
    COMPOSITE_KEYS,
    COMPOSITE_SIGNS,
    AlertEvent,
    ContractError,
    EpochSummary,
    PipelineConfig,
    ScoreRow,
)


def generate_alerts(
    scores: Sequence[ScoreRow],
    epochs: Sequence[EpochSummary],
    config: PipelineConfig,
    *,
    timestamps: Mapping[str, datetime] | None = None,
) -> list[AlertEvent]:
    """`timestamps` maps session_id to the `timestamp_utc` of the ringing session, which a score
    row does not carry; the orchestrator supplies it."""
    stamps = timestamps or {}
    ended = {
        (e.resident_code, e.epoch_number): e.ended_at for e in epochs if e.ended_at is not None
    }
    out = []
    for row in scores:
        if row.alarm_state != "rings":
            continue
        ended_at = ended.get((row.resident_code, row.epoch_number))
        if row.session_id not in stamps:
            raise ContractError(f"{row.session_id}: no timestamp for the ringing session")
        alert = AlertEvent(
            resident_code=row.resident_code, epoch_number=row.epoch_number,
            session_id=row.session_id,
            triggered_at=stamps[row.session_id],
            local_date=row.local_date, cusum_value=row.cusum_tally,
            epoch_ended=ended_at is not None, epoch_ended_at=ended_at,
        )  # fmt: skip
        out.append(alert)
    return sorted(out, key=lambda a: (a.resident_code, a.epoch_number))


def leaning_most(
    scores: Sequence[ScoreRow], alert: AlertEvent, config: PipelineConfig
) -> tuple[str, ...]:
    """Up to 3 composite features with the highest positive mean signed z over the alert's epoch
    from its local date on; ties keep canonical order (CUS-041)."""
    rows = [
        s for s in scores
        if s.resident_code == alert.resident_code and s.epoch_number == alert.epoch_number
        and s.local_date >= alert.local_date
    ]  # fmt: skip
    if not rows:
        return ()
    means = []
    for index, key in enumerate(COMPOSITE_KEYS):
        total = 0.0
        for s in rows:
            total += COMPOSITE_SIGNS[key] * s.z[f"z_{key}"]
        mean = total / len(rows)
        if mean > 0:
            means.append((-mean, index, key))
    return tuple(key for _, _, key in sorted(means)[:3])
