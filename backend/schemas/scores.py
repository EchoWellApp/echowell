"""Score and baseline read-out DTOs of TRD 19 §4.5 (`ScoreRow`, `ZValues`, `BaselinePeriod`,
`ScoresResponse`, `BaselineRow`, `BaselineRowList`)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import ConfigDict, Field

from backend.schemas.common import PageMeta, ResponseModel
from backend.schemas.ingest import SessionId
from backend.schemas.residents import ResidentCode

AlarmState = Literal["off", "rings", "on"]
BaselineFeatureKey = Literal[
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
    "composite",
]


class ZValues(ResponseModel):
    """The 7 unsigned z values of the scored features (contract §6 order)."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    z_loudness_dbfs: float
    z_total_phrase_duration_s: float
    z_speech_rate_syl_per_s: float
    z_articulation_rate_syl_per_s: float
    z_number_of_pauses: float
    z_pause_fraction: float
    z_voiced_fraction: float


class ScoreRow(ResponseModel):
    session_id: SessionId
    resident_code: ResidentCode
    epoch_number: int = Field(ge=1)
    local_date: date
    is_morning: bool
    z: ZValues
    composite_raw: float
    composite_z: float
    cusum_tally: float = Field(ge=0)
    alarm_state: AlarmState


class BaselinePeriod(ResponseModel):
    resident_code: ResidentCode
    epoch_number: int
    first_local_date: date
    frozen_after_local_date: date
    frozen_after_session_id: SessionId
    n_sessions: int


class ScoresResponse(PageMeta):
    cusum_k: float = Field(examples=[0.5])
    baseline_periods: list[BaselinePeriod]
    items: list[ScoreRow]


class BaselineRow(ResponseModel):
    resident_code: ResidentCode
    epoch_number: int
    device_code: str
    feature_key: BaselineFeatureKey
    n_sessions: int
    first_session_id: SessionId
    frozen_after_session_id: SessionId
    median: float
    mad: float = Field(ge=0)
    robust_spread: float = Field(
        ge=0,
        description="0 is possible only for a non-composite feature with floor 0 (TRD 08 "
        "BSC-035, TRD 20 baselines_spread_ck)",
    )
    floor_applied: bool


class BaselineRowList(PageMeta):
    items: list[BaselineRow]
