"""Possible-other-speaker quarantine (TRD 08 §4.4 BSC-011..BSC-019, §4.9 BSC-040; FEAT-044).

Within each resident-epoch, in time order, a `pending_screen` record is compared on RAW values
with the FIRST up to N usable sessions before it (`prior[:baseline_n]`, BSC-012), once there are
at least `screen_min_n` of them. It is quarantined when |z(F0)| >= screen_f0_z and at least
`screen_other_count` composite features have |z| >= screen_other_z (BSC-015); otherwise it is
usable and joins the reference list. Late records are screened against the same list but never
join it and get the late reason appended (BSC-040).

This stage also replaces the UTC placeholders of `assign_epochs` with facility-local time.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from analytics.config import (
    COMPOSITE_KEYS,
    F0_KEY,
    EpochedRecord,
    PipelineConfig,
    SessionStatus,
)
from analytics.epoch_detection import time_key
from analytics.morning_offset import local_time
from analytics.robust_stats import robust

LATE_REASON = "late arrival (not used for baseline or scores)"


def _screen(
    row: EpochedRecord, prior: Sequence[EpochedRecord], config: PipelineConfig
) -> tuple[bool, str | None]:
    """(quarantine?, screen_detail); the detail is None when the screen did not run."""
    ref = prior[: config.baseline_n]
    if len(ref) < config.screen_min_n:
        return False, None
    z: dict[str, float] = {}
    for key in (F0_KEY, *COMPOSITE_KEYS):
        stats = robust([p.record.features[key] for p in ref], config.spread_floor(key),
                       config.mad_scale)  # fmt: skip
        x = row.record.features[key]
        z[key] = (x - stats.median) / stats.spread if stats.spread > 0 else 0.0
    others = sum(abs(z[key]) >= config.screen_other_z for key in COMPOSITE_KEYS)
    detail = f"F0 z={z[F0_KEY]:.2f}; composite features with |z|>=3: {others}"
    quarantine = abs(z[F0_KEY]) >= config.screen_f0_z and others >= config.screen_other_count
    return quarantine, detail


def screen_speakers(rows: Sequence[EpochedRecord], config: PipelineConfig) -> list[EpochedRecord]:
    result: dict[str, EpochedRecord] = {}
    groups: dict[tuple[str, int], list[EpochedRecord]] = {}
    for row in rows:
        local, day = local_time(row.record.timestamp_utc, config)
        row = replace(row, local_datetime=local, local_date=day)
        result[row.record.raw_session_id] = row
        if row.status != "duplicate" and row.epoch_number is not None:
            groups.setdefault((row.record.resident_code, row.epoch_number), []).append(row)
    for key in sorted(groups):
        prior: list[EpochedRecord] = []
        for row in sorted(groups[key], key=time_key):
            if row.status != "pending_screen":
                continue  # set aside: never screened, never a reference (ING-042)
            quarantine, detail = _screen(row, prior, config)
            if quarantine:
                text = f"possible other speaker ({detail})"
                reasons: tuple[str, ...] = (text,)
                status: SessionStatus = "quarantined"
            else:
                reasons, text, status = (), "", "usable"
                if not row.late_arrival:
                    prior.append(row)
            if row.late_arrival:
                reasons = (*reasons, LATE_REASON)
                text = "; ".join(reasons)
            result[row.record.raw_session_id] = replace(
                row, status=status, reasons=reasons, reason_text=text, screen_detail=detail
            )
    # late records without an epoch: no screen (BSC-040)
    for raw_id, row in result.items():
        if row.status == "pending_screen":
            reasons = (LATE_REASON,) if row.late_arrival else ()
            result[raw_id] = replace(
                row, status="usable", reasons=reasons, reason_text="; ".join(reasons)
            )
    return [result[row.record.raw_session_id] for row in rows]
