"""Local time, morning flag and adjusted values (TRD 08 §4.5 BSC-020..BSC-024; FEAT-043).

The local time is the UTC instant converted to `facility_tz` with zoneinfo, so it is right
across DST changes; the UTC hour or date is never used (BSC-020, AGT-040). Morning sessions are
adjusted by the configured offsets only; nothing is estimated (BSC-022, ANL-055).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime

from analytics.config import (
    FEATURE_KEYS,
    AdjustedRecord,
    ContractError,
    EpochedRecord,
    PipelineConfig,
)


def local_time(instant: datetime, config: PipelineConfig) -> tuple[datetime, date]:
    """The facility-local datetime and date of an aware instant."""
    local = instant.astimezone(config.tz)
    return local, local.date()


def is_morning(local: datetime, config: PipelineConfig) -> bool:
    return local.hour < config.morning_cutoff_hour


def adjusted_values(
    values: Mapping[str, float], morning: bool, config: PipelineConfig
) -> dict[str, float]:
    if not morning:
        return {key: values[key] for key in FEATURE_KEYS}
    return {key: values[key] - config.morning_offsets[key] for key in FEATURE_KEYS}


def adjust(rows: Sequence[EpochedRecord], config: PipelineConfig) -> list[AdjustedRecord]:
    out = []
    for row in rows:
        if row.status == "pending_screen":
            raise ContractError(f"{row.record.session_id}: adjust() before the speaker screen")
        morning = is_morning(row.local_datetime, config)
        out.append(
            AdjustedRecord(
                record=row.record, status=row.status, reasons=row.reasons,
                reason_text=row.reason_text, epoch_number=row.epoch_number,
                screen_detail=row.screen_detail, late_arrival=row.late_arrival,
                local_datetime=row.local_datetime, local_date=row.local_date,
                is_morning=morning,
                adjusted=adjusted_values(row.record.features, morning, config),
            )
        )  # fmt: skip
    return out
