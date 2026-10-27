"""Alert, review, data-alert and UI-configuration DTOs of TRD 19 §4.5 (`Alert`, `AlertList`,
`AlertReviewCreate`, `AlertReview`, `AlertReviewList`, `SnoozeRequest`, `DataAlert`,
`DataAlertList`, `UiConfig`)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import Field

from backend.schemas.common import Meta, PageMeta, RequestModel, ResponseModel
from backend.schemas.ingest import SessionId
from backend.schemas.residents import ResidentCode, ScoredFeatureKey

AlertStatus = Literal["open", "acknowledged", "closed"]
ReviewOutcome = Literal["no_concern", "known_cause", "referred", "data_problem"]
ReviewExplanationCode = Annotated[str, Field(pattern=r"^[a-z_]{1,40}$")]
DataAlertKind = Literal[
    "baseline_stalled",
    "possible_other_speaker",
    "high_set_aside",
    "device_silent",
    "review_flagged_data_problem",
]
DataAlertStatus = Literal["open", "resolved"]


class Alert(ResponseModel):
    id: uuid.UUID = Field(description="stable across rebuilds (upsert key epoch_id + session_id)")
    resident_code: ResidentCode
    device_code: str | None
    epoch_number: int
    session_id: SessionId
    triggered_at: datetime
    local_date: date
    cusum_value: float = Field(description="tally at first crossing")
    current_tally: float | None = Field(
        description="cusum_state.current_tally of the alert's epoch"
    )
    open_days: int = Field(ge=0, description="as-of local date minus local_date")
    status: AlertStatus
    reviewed: bool = Field(description="true when status is acknowledged")
    review_count: int = Field(ge=0)
    last_reviewed_at: datetime | None
    snoozed_until: datetime | None
    snoozed_by: uuid.UUID | None
    leaning_most: list[ScoredFeatureKey] = Field(max_length=3)
    closed_reason: str | None = Field(examples=["epoch ended"])


class AlertList(PageMeta):
    items: list[Alert]


class AlertReviewCreate(RequestModel):
    explanations: list[ReviewExplanationCode] = Field(
        default_factory=list, max_length=5, json_schema_extra={"uniqueItems": True}
    )
    outcome: ReviewOutcome
    note: str | None = Field(default=None, max_length=2000)


class UserRef(ResponseModel):
    id: uuid.UUID
    display_name: str


class AlertReview(ResponseModel):
    id: uuid.UUID
    alert_id: uuid.UUID
    reviewer: UserRef
    explanations: list[ReviewExplanationCode]
    outcome: ReviewOutcome
    note: str | None
    created_at: datetime


class AlertReviewList(PageMeta):
    items: list[AlertReview]


class SnoozeRequest(RequestModel):
    hours: int | None = Field(default=None, ge=1, le=168, json_schema_extra={"default": 24})


class DataAlert(ResponseModel):
    id: uuid.UUID
    kind: DataAlertKind
    resident_code: str | None
    device_code: str | None
    title: str = Field(examples=["R08 · baseline stuck at 13 of 16"])
    detail: str = Field(
        description="v0.2 text without the leading code (TRD 09 §4.9, TRD 24 D-114); the UI "
        "renders '<code>: <detail>'"
    )
    status: DataAlertStatus
    first_detected_at: datetime
    last_detected_at: datetime
    pipeline_run_id: uuid.UUID | None


class DataAlertList(PageMeta):
    items: list[DataAlert]


class ReviewExplanation(ResponseModel):
    code: ReviewExplanationCode
    label: str = Field(examples=["Cold, cough or sore throat"])


class UiConfig(ResponseModel):
    meta: Meta
    alert_snooze_hours: int = Field(ge=1, le=168, examples=[24])
    review_explanations: list[ReviewExplanation] = Field(min_length=1, max_length=20)
