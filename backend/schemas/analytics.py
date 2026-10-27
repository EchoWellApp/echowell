"""Study-team analytics DTOs of TRD 19 §4.5 (`AnalyticsResponse` and its blocks)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field

from backend.schemas.common import Meta, ResponseModel
from backend.schemas.devices import DeviceCode
from backend.schemas.pipeline import PipelineRun
from backend.schemas.residents import ResidentCode


class CountOfExpected(ResponseModel):
    count: int
    expected: int
    percent: int = Field(ge=0, le=100, description="rounded half-up")


class BaselinesFormedRestart(ResponseModel):
    resident_code: ResidentCode
    restart_count: int = Field(ge=1)


class BaselinesFormed(ResponseModel):
    formed: int
    residents: int
    forming_resident_codes: list[ResidentCode]
    restarts: list[BaselinesFormedRestart]


class AlarmsRaised(ResponseModel):
    count: int
    resident_codes: list[ResidentCode]
    not_reviewed_count: int


class AnalyticsKpis(ResponseModel):
    checkins_received: CountOfExpected
    used_for_scoring: CountOfExpected
    baselines_formed: BaselinesFormed
    alarms_raised: AlarmsRaised


class DailySeriesPoint(ResponseModel):
    local_date: date
    used: int
    set_aside: int
    quarantined: int
    missed: int
    silent_device_codes: list[DeviceCode]


class SetAsideReasons(ResponseModel):
    quality_flag_poor: int
    noise_above_limit: int
    speech_too_short: int


class Funnel(ResponseModel):
    expected: int = Field(description="sum over residents of enrolled days in period")
    residents: int
    days: int
    received: int = Field(description="non-duplicate records")
    missed: int
    duplicates_removed: int
    passed_quality: int
    set_aside: int
    set_aside_reasons: SetAsideReasons
    set_aside_multi_reason: int = Field(description="set-aside sessions with more than one reason")
    quarantined: int
    used: int


class ByResidentRow(ResponseModel):
    resident_code: ResidentCode
    days: int
    used_days: int
    set_aside_days: int = Field(description="days with a set-aside record and no usable record")
    quarantined_days: int = Field(
        description="days with a quarantined record and no usable or set-aside record"
    )
    missed_days: int
    used_percent: int = Field(ge=0, le=100)


class AlarmTimingRow(ResponseModel):
    resident_code: ResidentCode
    planted_change: str = Field(examples=["Sudden step", "Slow drift", "None"])
    change_began: date | None
    alarm_rang: date | None
    delay_days: int | None
    result: Literal["detected", "missed", "correct_no_alarm", "false_alarm"]


class ByOutcome(ResponseModel):
    no_concern: int
    known_cause: int
    referred: int
    data_problem: int


class ReviewOutcomes(ResponseModel):
    alarms_raised: int
    reviewed: int
    by_outcome: ByOutcome


class StatusTotals(ResponseModel):
    usable: int
    set_aside: int
    quarantined: int
    duplicate: int
    missing_resident: int
    missing_device_gap: int


class StatusCountsRow(StatusTotals):
    resident_code: ResidentCode


class ResidentOutcome(ResponseModel):
    resident_code: ResidentCode
    epoch_number: int
    device_code: str
    usable_in_epoch: int
    baseline_formed: bool
    baseline_frozen_after: str | None
    scored_sessions: int | None
    first_alarm_session: str | None
    note: str | None


class Period(ResponseModel):
    from_: date = Field(alias="from")
    to: date
    days: int


class AnalyticsResponse(ResponseModel):
    meta: Meta
    period: Period
    kpis: AnalyticsKpis
    daily_series: list[DailySeriesPoint]
    funnel: Funnel
    by_resident: list[ByResidentRow]
    alarm_timing: list[AlarmTimingRow] | None = Field(description="test_v0_1 profile only")
    review_outcomes: ReviewOutcomes | None = Field(description="production profile only")
    status_totals: StatusTotals
    status_counts: list[StatusCountsRow]
    resident_outcomes: list[ResidentOutcome]
    pipeline_run: PipelineRun | None
