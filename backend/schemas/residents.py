"""Resident DTOs of TRD 19 §4.5 (`ResidentsOverviewResponse`, `ResidentOverviewRow`,
`ResidentDetail`, `CheckinEventList`, `FeaturesResponse` and their parts)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import Field

from backend.schemas.common import CODE_PATTERN, DateWindow, Meta, PageMeta, ResponseModel

ResidentCode = Annotated[str, Field(pattern=CODE_PATTERN, examples=["R09"])]
Cohort = Literal["longitudinal", "new_admission"]
ResidentStatus = Literal["active", "withdrawn"]
DisplayStatus = Literal["alarm_on", "no_alarm", "baseline_forming"]
AttentionReason = Literal["baseline_stalled", "high_set_aside"]
RestartCause = Literal["device", "firmware", "software"] | None
Sex = Literal["F", "M"] | None
CheckinEventType = Literal[
    "alarm_on",
    "watching_started",
    "baseline_complete",
    "baseline_restarted",
    "set_aside",
    "quarantined",
    "missed",
    "device_silent",
    "checkins_started",
]
FeatureKey = Literal[
    "loudness_dbfs",
    "total_phrase_duration_s",
    "speech_rate_syl_per_s",
    "articulation_rate_syl_per_s",
    "number_of_pauses",
    "pause_fraction",
    "voiced_fraction",
    "mean_f0_hz",
    "f0_variability_st",
    "jitter_local_pct",
    "shimmer_local_pct",
    "hnr_db",
    "cpps_db",
    "alpha_ratio_db",
    "hammarberg_index_db",
    "mfcc1",
    "mfcc2",
    "mfcc3",
    "mfcc4",
]
ScoredFeatureKey = Literal[
    "loudness_dbfs",
    "total_phrase_duration_s",
    "speech_rate_syl_per_s",
    "articulation_rate_syl_per_s",
    "number_of_pauses",
    "pause_fraction",
    "voiced_fraction",
]


class OverviewSummary(ResponseModel):
    changed: int = Field(ge=0, description="status alarm_on")
    needs_attention: int = Field(ge=0, description="needs_attention true and status not alarm_on")
    learning: int = Field(ge=0, description="status baseline_forming and needs_attention false")
    usual: int = Field(ge=0, description="status no_alarm and needs_attention false")


class BaselineProgress(ResponseModel):
    n_usable: int = Field(ge=0)
    n_required: int = Field(ge=1)


class Last30Days(ResponseModel):
    used: int = Field(ge=0)
    set_aside: int = Field(ge=0)
    quarantined: int = Field(ge=0)
    missed: int = Field(ge=0, description="missing_resident + missing_device_gap")


class ResidentOverviewRow(ResponseModel):
    resident_code: ResidentCode
    cohort: Cohort
    resident_status: ResidentStatus
    device_code: str | None
    device_shared: bool
    previous_device_code: str | None
    status: DisplayStatus
    needs_attention: bool
    attention_reasons: list[AttentionReason]
    alarm_since: date | None
    open_alert_id: uuid.UUID | None
    alarm_reviewed: bool | None
    current_epoch: int | None = Field(ge=1)
    baseline_restarted_on: date | None
    restart_cause: RestartCause
    baseline_progress: BaselineProgress
    last_checkin_at: datetime | None
    last_checkin_local: datetime | None
    last_30_days: Last30Days


class ResidentsOverviewResponse(PageMeta):
    window: DateWindow
    summary: OverviewSummary
    items: list[ResidentOverviewRow]


class DeviceRef(ResponseModel):
    device_code: str | None
    shared: bool
    shared_with: list[ResidentCode]
    previous_device_code: str | None


class EpochInfo(ResponseModel):
    epoch_number: int = Field(ge=1)
    device_code: str
    device_firmware_version: str
    extraction_software_version: str
    started_at: datetime
    started_on: date
    from_value: str | None
    to_value: str | None


class BaselineInfo(ResponseModel):
    state: Literal["forming", "frozen"]
    n_usable: int = Field(ge=0)
    n_required: int = Field(ge=1)
    first_session_id: str | None
    frozen_after_session_id: str | None
    first_local_date: date | None
    frozen_after_local_date: date | None


class Explanation(ResponseModel):
    """Structured facts only; wording is rendered by the frontend (OQ-12)."""

    compared_with: Literal["own_baseline"]
    alarm_crossed_on: date | None
    still_above_line: bool
    baseline_restarted_on: date | None
    baseline_n_usable: int
    baseline_n_required: int


class ResidentDetail(ResponseModel):
    meta: Meta
    resident_code: ResidentCode
    cohort: Cohort
    resident_status: ResidentStatus
    sex: Sex
    enrolled_on: date
    admitted_on: date | None
    withdrawn_on: date | None
    status: DisplayStatus
    needs_attention: bool
    attention_reasons: list[AttentionReason]
    alarm_reviewed: bool | None
    restart_cause: RestartCause
    device: DeviceRef
    current_epoch: EpochInfo | None
    epoch_count: int = Field(ge=0)
    baseline: BaselineInfo
    watching_since: date | None
    alarm_since: date | None
    open_alert_id: uuid.UUID | None
    current_tally: float | None
    last_checkin_at: datetime | None
    last_checkin_local: datetime | None
    window: DateWindow
    last_30_days: Last30Days
    explanation: Explanation


class CheckinEvent(ResponseModel):
    local_date: date
    event_type: CheckinEventType
    epoch_number: int | None
    session_id: str | None
    detail: str | None = Field(description='pipeline reason text or progress, e.g. "16 of 16"')
    cusum_tally: float | None
    restart_cause: RestartCause
    previous_device_code: str | None
    from_value: str | None
    to_value: str | None
    device_code: str | None


class CheckinEventList(PageMeta):
    items: list[CheckinEvent]


class FeaturePoint(ResponseModel):
    session_id: str
    local_date: date
    is_morning: bool
    raw_value: float
    adjusted_value: float
    z: float | None = Field(description="null for sessions not scored")
    in_baseline: bool


class FeatureSeries(ResponseModel):
    feature_key: ScoredFeatureKey
    label: str = Field(examples=["Quieter (loudness)"])
    unit: str
    composite_sign: Literal[-1, 1]
    baseline_median: float | None
    baseline_robust_spread: float | None
    points: list[FeaturePoint]


class FeaturesResponse(ResponseModel):
    meta: Meta
    resident_code: ResidentCode
    epoch_number: int | None
    scored_features: list[FeatureSeries] = Field(min_length=7, max_length=7)
    stored_feature_keys: list[FeatureKey] = Field(min_length=12, max_length=12)
