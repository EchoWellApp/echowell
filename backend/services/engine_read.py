"""Engine contracts rebuilt from persisted rows, for the read-side analytics helpers (TRD 24 D-79;
TRD 05 API-006; FEAT-048-FR-07, FEAT-051-FR-11..FR-13).

`GET /api/v1/analytics` calls `analytics.aggregates.build_analytics_summary` and
`GET /api/v1/alerts` calls `analytics.alert_generator.leaning_most` on the rows the latest runs
wrote; nothing here
re-implements a formula. A `device_silent` data alert stores no day list, so its days are read
back from its detail text: every "<Mon D>" falls in the 30-day window and maps to one date.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from analytics.config import (
    COMPOSITE,
    FEATURE_KEYS,
    AdjustedRecord,
    AlertEvent,
    DataAlert,
    EpochSummary,
    LedgerDay,
    PipelineConfig,
    RawRecord,
    ResidentInfo,
    ScoreRow,
)
from backend.models import (
    Alert,
    Baseline,
    CusumState,
    DataAlertStatus,
    DayLedgerEntry,
    Device,
    Epoch,
    ProcessedSession,
    RawSession,
    Resident,
    Score,
)
from backend.models import DataAlert as DataAlertRow
from backend.repositories.config_repository import ConfigRepository
from backend.services import config_service

SUPERSEDED = "superseded by rebuild"
_MONTH_DAY = re.compile(r"\b([A-Z][a-z]{2}) (\d{1,2})\b")


def config_for(session: Session, profile: str) -> PipelineConfig:
    values = ConfigRepository(session).values_for_profile(profile)
    return config_service.pipeline_config(values, profile)[0]


def _record(raw: RawSession) -> RawRecord:
    return RawRecord(
        raw_session_id=str(raw.id), arrival_seq=raw.arrival_seq, received_at=raw.received_at,
        schema_version=raw.schema_version, session_id=raw.session_id,
        resident_code=raw.resident_code, device_code=raw.device_code,
        timestamp_utc=raw.timestamp_utc, mic_noise_level_dbfs=raw.mic_noise_level_dbfs,
        audio_quality_flag=raw.audio_quality_flag,
        extraction_software_version=raw.extraction_software_version,
        device_firmware_version=raw.device_firmware_version,
        speech_duration_s=raw.speech_duration_s, phrase_id=raw.phrase_id,
        features={k: float(getattr(raw, k)) for k in FEATURE_KEYS},
    )  # fmt: skip


@dataclass(frozen=True)
class StoredResult:
    sessions: list[AdjustedRecord]
    ledger: list[LedgerDay]
    epochs: list[EpochSummary]
    alerts: list[AlertEvent]
    data_alerts: list[DataAlert]
    residents: list[ResidentInfo]


def stored_result(session: Session, period: tuple[date, date]) -> StoredResult:
    devices = {d.id: d.device_code for d in session.scalars(select(Device))}
    residents = session.scalars(select(Resident)).all()
    codes = {r.id: r.resident_code for r in residents}
    epochs = {e.id: e for e in session.scalars(select(Epoch))}
    sessions = []
    for processed, raw in session.execute(
        select(ProcessedSession, RawSession).join(RawSession,
                                                  RawSession.id == ProcessedSession.raw_session_id)
    ):  # fmt: skip
        epoch = epochs.get(processed.epoch_id) if processed.epoch_id else None
        record = _record(raw)
        adjusted = processed.adjusted_features or dict(record.features)
        sessions.append(AdjustedRecord(
            record=record, status=processed.status.value, reasons=tuple(processed.reasons),
            reason_text=processed.reason_text,
            epoch_number=epoch.epoch_number if epoch else None,
            screen_detail=processed.screen_detail, late_arrival=processed.late_arrival,
            local_datetime=datetime.combine(processed.local_date, processed.local_time),
            local_date=processed.local_date, is_morning=processed.is_morning,
            adjusted={k: float(adjusted[k]) for k in FEATURE_KEYS},
            baseline_ordinal=processed.baseline_ordinal, in_baseline=processed.in_baseline,
        ))  # fmt: skip
    ledger = [
        LedgerDay(codes[d.resident_id], d.local_date, d.status.value,
                  devices.get(d.device_id) if d.device_id else None, d.reason)
        for d in session.scalars(select(DayLedgerEntry))
    ]  # fmt: skip
    formed = {b.epoch_id: b for b in session.scalars(
        select(Baseline).where(Baseline.feature_key == COMPOSITE))}  # fmt: skip
    states = {c.epoch_id: c for c in session.scalars(select(CusumState))}
    summaries = [_epoch(e, codes, devices, formed.get(e.id), states.get(e.id), epochs)
                 for e in epochs.values()]  # fmt: skip
    alerts = [
        AlertEvent(codes[a.resident_id], epochs[a.epoch_id].epoch_number, a.session_id,
                   a.triggered_at, a.local_date, a.cusum_value, a.closed_reason == "epoch ended",
                   None)
        for a in session.scalars(select(Alert)) if a.closed_reason != SUPERSEDED
    ]  # fmt: skip
    open_rule_alerts = session.scalars(select(DataAlertRow).where(
        DataAlertRow.status == DataAlertStatus.OPEN,
        DataAlertRow.kind != "review_flagged_data_problem",
    )).all()  # fmt: skip
    data_alerts = [
        DataAlert(
            row.kind.value,  # type: ignore[arg-type]  # the four rule kinds only
            codes.get(row.resident_id) if row.resident_id else None,
            devices.get(row.device_id) if row.device_id else None, row.title, row.detail,
            days_in(row.detail, period),
        )
        for row in open_rule_alerts
    ]  # fmt: skip
    infos = [ResidentInfo(r.resident_code, r.enrolled_on, r.withdrawn_on, r.status.value)
             for r in residents]  # fmt: skip
    return StoredResult(sessions, ledger, summaries, alerts, data_alerts, infos)


def _epoch(
    e: Epoch, codes: dict[Any, str], devices: dict[Any, str], composite: Baseline | None,
    state: CusumState | None, epochs: dict[Any, Epoch],
) -> EpochSummary:  # fmt: skip
    return EpochSummary(
        resident_code=codes[e.resident_id], epoch_number=e.epoch_number,
        device_code=devices[e.device_id], device_firmware_version=e.device_firmware_version,
        extraction_software_version=e.extraction_software_version, started_at=e.started_at,
        ended_at=e.ended_at, usable_count=0, baseline_formed=composite is not None,
        frozen_after_session_id=composite.frozen_after_session_id if composite else None,
        scored_count=0, watching_since=None,
        current_tally=state.current_tally if state else 0.0,
        last_scored_session_id=state.last_scored_session_id if state else None,
        alarm_on=state.alarm_on if state else False, first_alarm_session_id=None,
    )  # fmt: skip


def days_in(detail: str, period: tuple[date, date]) -> tuple[date, ...]:
    """The "<Mon D>" dates of a detail text inside the window `period` (at most 30 days, so each
    month-day names one date)."""
    start, end = period
    by_label = {}
    day = start
    while day <= end:
        by_label[(f"{day:%b}", day.day)] = day
        day += timedelta(days=1)
    found = {by_label[(m, int(d))] for m, d in _MONTH_DAY.findall(detail)
             if (m, int(d)) in by_label}  # fmt: skip
    return tuple(sorted(found))


def epoch_scores(
    session: Session, alert: Alert, resident_code: str, epoch_number: int
) -> list[ScoreRow]:
    """The stored scores of an alert's epoch as engine rows (for `leaning_most`)."""
    rows = session.execute(
        select(Score, ProcessedSession.session_id, ProcessedSession.raw_session_id)
        .join(ProcessedSession, ProcessedSession.id == Score.processed_session_id)
        .where(Score.epoch_id == alert.epoch_id)
        .order_by(ProcessedSession.timestamp_utc)
    ).all()
    return [
        ScoreRow(session_id, str(raw_id), resident_code, epoch_number, score.local_date,
                 score.is_morning, dict(score.z), score.composite_raw, score.composite_z,
                 score.cusum_tally, score.alarm_state.value)
        for score, session_id, raw_id in rows
    ]  # fmt: skip
