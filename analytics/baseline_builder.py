"""Baseline membership, per-feature and composite baseline, freeze (TRD 08 §4.6-§4.7
BSC-025..BSC-035; FEAT-045).

Per (resident, epoch) the usable, non-late sessions are numbered in time order; the first N form
the baseline, which freezes on the N-th and never changes afterwards (BSC-026, ASM-07). Each formed
epoch yields 20 rows: the 19 features from adjusted values, then the composite of the baseline
sessions' own `composite_raw` values (BSC-031..BSC-034).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from analytics.composite_score import composite_raw
from analytics.config import (
    COMPOSITE,
    FEATURE_KEYS,
    AdjustedRecord,
    Baseline,
    BaselineMembership,
    EpochKey,
    PipelineConfig,
    RobustStats,
)
from analytics.epoch_detection import time_key
from analytics.robust_stats import robust
from analytics.zscore_calculator import feature_z


def number_sessions(rows: Sequence[AdjustedRecord], config: PipelineConfig) -> list[AdjustedRecord]:
    """Set `baseline_ordinal` and `in_baseline` on usable, non-late sessions (BSC-025, BSC-026)."""
    ordinal: dict[str, int] = {}
    groups: dict[EpochKey, list[AdjustedRecord]] = {}
    for row in rows:
        if row.status == "usable" and not row.late_arrival and row.epoch_number is not None:
            groups.setdefault((row.record.resident_code, row.epoch_number), []).append(row)
    for members in groups.values():
        for i, row in enumerate(sorted(members, key=time_key), start=1):
            ordinal[row.record.raw_session_id] = i
    out = []
    for row in rows:
        n = ordinal.get(row.record.raw_session_id)
        out.append(replace(row, baseline_ordinal=n,
                           in_baseline=n is not None and n <= config.baseline_n))  # fmt: skip
    return out


def baseline_rows(
    resident: str, epoch: int, members: Sequence[AdjustedRecord], config: PipelineConfig
) -> list[Baseline]:
    """The 20 rows of a formed baseline from its N sessions in time order."""
    first, last = members[0], members[-1]

    def row(key: str, stats: RobustStats) -> Baseline:
        return Baseline(
            resident_code=resident, epoch_number=epoch, device_code=first.record.device_code,
            feature_key=key, n_sessions=len(members), first_session_id=first.record.session_id,
            frozen_after_session_id=last.record.session_id, median=stats.median, mad=stats.mad,
            robust_spread=stats.spread, floor_applied=stats.floor_applied,
            frozen_at=last.record.timestamp_utc,
        )  # fmt: skip

    rows = [
        row(key, robust([m.adjusted[key] for m in members], config.spread_floor(key),
                        config.mad_scale))
        for key in FEATURE_KEYS
    ]  # fmt: skip
    by_key = {b.feature_key: b for b in rows}
    raws = [composite_raw(feature_z(m, by_key, config), config) for m in members]
    rows.append(row(COMPOSITE, robust(raws, config.composite_floor, config.mad_scale)))
    return rows


def build_baselines(
    rows: Sequence[AdjustedRecord], config: PipelineConfig
) -> tuple[list[Baseline], dict[EpochKey, BaselineMembership]]:
    """Baselines of every formed epoch and the membership of every epoch with usable sessions.
    `rows` must already carry `baseline_ordinal` (see `number_sessions`)."""
    groups: dict[EpochKey, list[AdjustedRecord]] = {}
    for row in rows:
        if row.baseline_ordinal is not None and row.epoch_number is not None:
            groups.setdefault((row.record.resident_code, row.epoch_number), []).append(row)
    baselines: list[Baseline] = []
    membership: dict[EpochKey, BaselineMembership] = {}
    for key in sorted(groups):
        ordered = sorted(groups[key], key=lambda r: r.baseline_ordinal or 0)
        members = [r for r in ordered if r.in_baseline]
        formed = len(members) >= config.baseline_n
        membership[key] = BaselineMembership(
            session_ids=tuple(m.record.session_id for m in members), formed=formed,
            usable_count=len(ordered),
        )  # fmt: skip
        if formed:
            baselines.extend(baseline_rows(key[0], key[1], members, config))
    return baselines, membership


def baselines_by_epoch(baselines: Sequence[Baseline]) -> dict[EpochKey, dict[str, Baseline]]:
    out: dict[EpochKey, dict[str, Baseline]] = {}
    for b in baselines:
        out.setdefault((b.resident_code, b.epoch_number), {})[b.feature_key] = b
    return dict(out.items())
