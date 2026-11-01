"""Stage orchestration, late-arrival detection, as-of filter and result assembly (TRD 07 §4.5,
§4.6 ANL-014..ANL-027; FEAT-052).

`run_pipeline` is the single engine entry point for every trigger. It is pure: equal arguments
give an equal `PipelineResult` (ANL-020), whatever the order of `records`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import datetime

from analytics.aggregates import build_analytics_summary
from analytics.alert_generator import generate_alerts, leaning_most
from analytics.baseline_builder import baselines_by_epoch, build_baselines, number_sessions
from analytics.composite_score import composite_raw, composite_z
from analytics.config import (
    COMPOSITE,
    COMPOSITE_KEYS,
    ENGINE_VERSION,
    AdjustedRecord,
    Baseline,
    ContractError,
    DeviceAssignment,
    EpochedRecord,
    EpochKey,
    EpochSummary,
    LedgerDay,
    PipelineConfig,
    PipelineResult,
    RawRecord,
    ResidentInfo,
    RunWarning,
    ScoreRow,
    ScreenedRecord,
)
from analytics.cusum_engine import run_cusum
from analytics.data_alerts import generate_data_alerts
from analytics.day_ledger import build_ledger, device_on
from analytics.duplicate_detection import mark_duplicates
from analytics.epoch_detection import assign_epochs, time_key
from analytics.morning_offset import adjust
from analytics.quality_screening import apply_quality_gate
from analytics.speaker_screen import screen_speakers
from analytics.zscore_calculator import feature_z

MISMATCH_TOLERANCE = 1e-12


def _validate(
    records: Sequence[RawRecord], residents: Sequence[ResidentInfo],
    assignments: Sequence[DeviceAssignment], config: PipelineConfig, as_of: datetime,
) -> None:  # fmt: skip
    if not isinstance(config, PipelineConfig):
        raise ContractError("config must be a PipelineConfig")
    if not isinstance(as_of, datetime) or as_of.tzinfo is None:
        raise ContractError("as_of must be a timezone-aware datetime")
    seqs = [r.arrival_seq for r in records]
    if len(seqs) != len(set(seqs)):
        raise ContractError("arrival_seq values must be unique")
    known = {r.resident_code for r in residents}
    for a in assignments:
        if a.resident_code not in known:
            raise ContractError(f"assignment for unknown resident {a.resident_code}")


def _stages_1_to_3(records: Sequence[RawRecord], config: PipelineConfig) -> list[ScreenedRecord]:
    return apply_quality_gate(mark_duplicates(records), config)


def _frozen_after_times(prefix: Sequence[ScreenedRecord], config: PipelineConfig) -> list[datetime]:
    """Stages 3-8 on a prefix: the frozen-after timestamps of its formed baselines."""
    adjusted = number_sessions(adjust(screen_speakers(assign_epochs(prefix), config), config),
                               config)  # fmt: skip
    _, membership = build_baselines(adjusted, config)
    stamp = {a.record.session_id: a.record.timestamp_utc for a in adjusted}
    return [stamp[m.session_ids[-1]] for m in membership.values() if m.formed]


def detect_late_arrivals(
    screened: Sequence[ScreenedRecord], config: PipelineConfig
) -> list[ScreenedRecord]:
    """ANL-024: out-of-order records that would precede a frozen-after session or renumber
    epochs. Evaluated per resident in arrival order so earlier verdicts count."""
    late: list[ScreenedRecord] = []
    by_resident: dict[str, list[ScreenedRecord]] = {}
    for row in screened:
        if row.status != "duplicate":
            by_resident.setdefault(row.record.resident_code, []).append(row)
    for code in sorted(by_resident):
        rows = sorted(by_resident[code], key=lambda r: r.record.arrival_seq)
        late_ids: set[str] = set()
        for i, row in enumerate(rows):
            earlier = rows[:i]
            if not any(e.record.timestamp_utc > row.record.timestamp_utc for e in earlier):
                continue  # (a) in order
            prefix = [e for e in earlier if e.record.raw_session_id not in late_ids]
            if _is_late(row, prefix, config):
                late_ids.add(row.record.raw_session_id)
                late.append(row)
    return late


def _is_late(row: ScreenedRecord, prefix: Sequence[ScreenedRecord], config: PipelineConfig) -> bool:
    ts = row.record.timestamp_utc
    if any(t > ts for t in _frozen_after_times(prefix, config)):  # (b1)
        return True
    ordered = sorted(prefix, key=time_key)
    before = [p for p in ordered if time_key(p) < time_key(row)]
    after = [p for p in ordered if time_key(p) > time_key(row)]
    key = row.record.epoch_key
    differs_before = not before or before[-1].record.epoch_key != key
    return bool(after) and differs_before and after[0].record.epoch_key != key  # (b2)


def _check_frozen(
    key: EpochKey, computed: Sequence[Baseline], persisted: Sequence[Baseline],
) -> list[RunWarning]:  # fmt: skip
    """ANL-037: persisted baselines win; a difference is reported, never written."""
    by_feature = {b.feature_key: b for b in persisted}
    for b in computed:
        p = by_feature.get(b.feature_key)
        same = p is not None and (
            (p.first_session_id, p.frozen_after_session_id, p.n_sessions)
            == (b.first_session_id, b.frozen_after_session_id, b.n_sessions)
            and all(abs(getattr(p, f) - getattr(b, f)) <= MISMATCH_TOLERANCE
                    for f in ("median", "mad", "robust_spread"))
        )  # fmt: skip
        if not same:
            return [RunWarning("baseline_mismatch", key[0], None,
                               f"epoch {key[1]}: persisted baseline kept")]  # fmt: skip
    return []


def _score(
    adjusted: Sequence[AdjustedRecord], baselines: Mapping[EpochKey, Mapping[str, Baseline]],
    config: PipelineConfig,
) -> list[ScoreRow]:  # fmt: skip
    """Step 9: usable, non-late sessions after the frozen-after session, in time order."""
    rows = []
    ordinals: dict[EpochKey, int] = {}
    for a in sorted(adjusted, key=lambda r: (r.record.resident_code, r.epoch_number or 0,
                                             *time_key(r))):  # fmt: skip
        if a.status != "usable" or a.late_arrival or a.epoch_number is None or a.in_baseline:
            continue
        key = (a.record.resident_code, a.epoch_number)
        if key not in baselines or a.baseline_ordinal is None:
            continue
        z = feature_z(a, baselines[key], config)
        raw = composite_raw(z, config)
        ordinals[key] = ordinals.get(key, 0) + 1
        rows.append(ScoreRow(
            session_id=a.record.session_id, raw_session_id=a.record.raw_session_id,
            resident_code=key[0], epoch_number=key[1], local_date=a.local_date,
            is_morning=a.is_morning, z={f"z_{k}": z[k] for k in COMPOSITE_KEYS},
            composite_raw=raw, composite_z=composite_z(raw, baselines[key][COMPOSITE]),
            scored_ordinal=ordinals[key],
        ))  # fmt: skip
    return rows


def _epoch_summaries(
    epoched: Sequence[EpochedRecord], adjusted: Sequence[AdjustedRecord],
    membership: Mapping[EpochKey, object], baselines: Mapping[EpochKey, Mapping[str, Baseline]],
    scores: Sequence[ScoreRow], config: PipelineConfig,
) -> list[EpochSummary]:  # fmt: skip
    first: dict[EpochKey, EpochedRecord] = {}
    for row in sorted(epoched, key=time_key):
        if row.status == "duplicate" or row.late_arrival or row.epoch_number is None:
            continue
        first.setdefault((row.record.resident_code, row.epoch_number), row)
    usable: dict[EpochKey, int] = {}
    for a in adjusted:
        if a.baseline_ordinal is not None and a.epoch_number is not None:
            k = (a.record.resident_code, a.epoch_number)
            usable[k] = usable.get(k, 0) + 1
    by_epoch: dict[EpochKey, list[ScoreRow]] = {}
    for s in scores:
        by_epoch.setdefault((s.resident_code, s.epoch_number), []).append(s)
    local_of = {a.record.session_id: a.local_date for a in adjusted}
    out = []
    for key in sorted(first):
        row = first[key]
        nxt = first.get((key[0], key[1] + 1))
        formed = key in baselines
        frozen_after = baselines[key][COMPOSITE].frozen_after_session_id if formed else None
        mine = by_epoch.get(key, [])
        rings = [s for s in mine if s.alarm_state == "rings"]
        if mine:
            watching = mine[0].local_date
        elif frozen_after is not None:
            watching = local_of[frozen_after].fromordinal(local_of[frozen_after].toordinal() + 1)
        else:
            watching = None
        out.append(EpochSummary(
            resident_code=key[0], epoch_number=key[1], device_code=row.record.device_code,
            device_firmware_version=row.record.device_firmware_version,
            extraction_software_version=row.record.extraction_software_version,
            started_at=row.record.timestamp_utc,
            ended_at=nxt.record.timestamp_utc if nxt else None,
            usable_count=usable.get(key, 0), baseline_formed=formed,
            frozen_after_session_id=frozen_after, scored_count=len(mine),
            watching_since=watching, current_tally=mine[-1].cusum_tally if mine else 0.0,
            last_scored_session_id=mine[-1].session_id if mine else None,
            alarm_on=bool(rings), first_alarm_session_id=rings[0].session_id if rings else None,
        ))  # fmt: skip
    return out


def run_pipeline(
    records: Sequence[RawRecord],
    residents: Sequence[ResidentInfo],
    assignments: Sequence[DeviceAssignment],
    config: PipelineConfig,
    as_of: datetime,
    *,
    frozen_baselines: Mapping[EpochKey, tuple[Baseline, ...]] | None = None,
) -> PipelineResult:
    _validate(records, residents, assignments, config, as_of)  # 1
    warnings: list[RunWarning] = []
    recs = sorted(records, key=lambda r: r.arrival_seq)  # 2
    excluded = [r for r in recs if r.timestamp_utc > as_of]  # 3
    warnings += [RunWarning("after_as_of", r.resident_code, r.session_id) for r in excluded]
    recs = [r for r in recs if r.timestamp_utc <= as_of]
    screened = _stages_1_to_3(recs, config)  # 4
    late = detect_late_arrivals(screened, config)  # 5
    warnings += [RunWarning("late_arrival", r.record.resident_code, r.record.session_id)
                 for r in late]  # fmt: skip
    epoched = screen_speakers(assign_epochs(screened, late), config)  # 6
    adjusted = number_sessions(adjust(epoched, config), config)  # 7
    computed, membership = build_baselines(adjusted, config)  # 8
    by_epoch = baselines_by_epoch(computed)
    for key, persisted in sorted((frozen_baselines or {}).items()):
        if key in by_epoch:
            warnings += _check_frozen(key, list(by_epoch[key].values()), persisted)
        by_epoch[key] = {b.feature_key: b for b in persisted}
    for key in sorted(by_epoch):
        for feature in COMPOSITE_KEYS:
            if by_epoch[key][feature].robust_spread == 0:
                warnings.append(RunWarning("zero_spread", key[0], None, feature))
    baselines = [b for key in sorted(by_epoch) for b in by_epoch[key].values()]
    scores = run_cusum(_score(adjusted, by_epoch, config), config)  # 9, 10
    epochs = _epoch_summaries(epoched, adjusted, membership, by_epoch, scores, config)  # 11
    stamps = {a.record.session_id: a.record.timestamp_utc for a in adjusted}
    alerts = [
        replace(a, leaning_most=leaning_most(scores, a, config))
        for a in generate_alerts(scores, epochs, config, timestamps=stamps)
    ]  # 12
    ledger = build_ledger(epoched, residents, assignments, config, as_of)  # 13
    warnings += _assignment_warnings(adjusted, ledger, assignments)
    data_alerts = generate_data_alerts(adjusted, ledger, epochs, residents, assignments, config,
                                       as_of)  # 14  # fmt: skip
    summary = build_analytics_summary(adjusted, ledger, epochs, alerts, data_alerts, residents,
                                      config, as_of)  # 15  # fmt: skip
    sessions = tuple(sorted(adjusted, key=lambda a: a.record.arrival_seq))
    counts = {
        "arrivals": len(recs),
        "usable": sum(s.status == "usable" for s in sessions),
        "set_aside": sum(s.status == "set_aside" for s in sessions),
        "quarantined": sum(s.status == "quarantined" for s in sessions),
        "duplicate": sum(s.status == "duplicate" for s in sessions),
        "missing_resident": sum(d.status == "missing_resident" for d in ledger),
        "missing_device_gap": sum(d.status == "missing_device_gap" for d in ledger),
        "late_arrival": len(late), "scored": len(scores), "alerts_opened": len(alerts),
        "excluded_after_as_of": len(excluded), "residents": len(residents),
    }  # fmt: skip
    return PipelineResult(
        run_config=config.snapshot(), config_hash=config.config_hash(),
        engine_version=ENGINE_VERSION, as_of=as_of, sessions=sessions, epochs=tuple(epochs),
        baselines=tuple(baselines),
        scores=tuple(sorted(scores, key=lambda s: (s.resident_code, s.epoch_number,
                                                   s.scored_ordinal))),
        alerts=tuple(alerts), ledger=tuple(ledger), data_alerts=tuple(data_alerts),
        analytics=summary, warnings=tuple(sorted(warnings, key=RunWarning.sort_key)),
        counts=counts,
    )  # 16  # fmt: skip


def _assignment_warnings(
    adjusted: Sequence[AdjustedRecord], ledger: Sequence[LedgerDay],
    assignments: Sequence[DeviceAssignment],
) -> list[RunWarning]:  # fmt: skip
    """`no_device_assignment` once per resident; `device_assignment_mismatch` per record whose
    device is not the resident's assigned device that day (ANL-052, API-055)."""
    out = []
    unassigned = sorted({d.resident_code for d in ledger
                         if d.status != "checked_in" and d.device_code is None})  # fmt: skip
    out += [RunWarning("no_device_assignment", code, None, "missing day without a device")
            for code in unassigned]  # fmt: skip
    for a in sorted(adjusted, key=lambda r: r.record.arrival_seq):
        if a.status == "duplicate":
            continue
        assigned = device_on(a.record.resident_code, a.local_date, assignments)
        if assigned is not None and assigned != a.record.device_code:
            out.append(RunWarning(
                "device_assignment_mismatch", a.record.resident_code, a.record.session_id,
                f"record device {a.record.device_code}, assigned {assigned}",
            ))  # fmt: skip
    return out


__all__ = ["detect_late_arrivals", "run_pipeline"]
