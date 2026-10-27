"""Pipeline-run DTOs of TRD 19 §4.5 (`PipelineRunRequest`, `PipelineRunAccepted`, `PipelineRun`,
`PipelineRunList`)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, field_validator

from backend.schemas.common import (
    ConfigProfile,
    Omitted,
    PageMeta,
    RequestModel,
    ResidentCode,
    ResponseModel,
    reject_null,
)

type PipelineTrigger = Literal["ingest", "nightly", "manual", "test"]
type PipelineStatus = Literal["running", "succeeded", "failed"]


class PipelineRunRequest(RequestModel):
    scope: Literal["all"] | Annotated[list[ResidentCode], Field(min_length=1)]
    profile: ConfigProfile | Omitted = None
    as_of: AwareDatetime | None = None

    _not_null = field_validator("profile", mode="before")(reject_null)


class PipelineRunAccepted(ResponseModel):
    pipeline_run_id: uuid.UUID


class PipelineRunWarning(ResponseModel):
    code: str = Field(examples=["late_arrival", "device_assignment_mismatch", "run_abandoned"])
    resident_code: str | None
    session_id: str | None
    detail: str | None


class PipelineRun(ResponseModel):
    id: uuid.UUID
    trigger: PipelineTrigger
    scope: Literal["all"] | list[ResidentCode]
    config_profile: ConfigProfile
    code_version: str
    as_of: datetime
    started_at: datetime
    finished_at: datetime | None
    status: PipelineStatus
    counts: dict[str, int]
    warnings: list[PipelineRunWarning]


class PipelineRunList(PageMeta):
    items: list[PipelineRun]
