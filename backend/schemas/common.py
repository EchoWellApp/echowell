"""Shared DTOs of TRD 19 §4.5: `Meta`, `PageMeta`, `Problem`, `DateWindow` and the code patterns.

Response models list nullable fields as `X | None` without defaults, so every field is present in
the JSON (TRD 19 §8, OAS-011). Request models forbid unknown properties (SEC-080).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.json_schema import SkipJsonSchema

CODE_PATTERN = r"^[A-Z0-9]{1,16}$"
SESSION_ID_PATTERN = r"^[A-Z0-9]{1,16}-[0-9]{8}-[0-9]{2}$"
# `type` aliases become `components/schemas` entries of the same name (TRD 19 §4.5).
type ConfigProfile = Literal["production", "test_v0_1"]
type ResidentCode = Annotated[str, Field(pattern=CODE_PATTERN, examples=["R09"])]
type DeviceCode = Annotated[str, Field(pattern=CODE_PATTERN, examples=["D07B"])]
type SessionId = Annotated[str, Field(pattern=SESSION_ID_PATTERN, examples=["R09-20261021-01"])]
# Database enums no DTO property uses; documented for clients (OAS-007).
type ProcessedStatus = Literal["usable", "set_aside", "quarantined", "duplicate"]
type DayStatus = Literal["checked_in", "missing_resident", "missing_device_gap"]


class ResponseModel(BaseModel):
    """Times must be timezone-aware UTC; Pydantic writes them with `Z` (API-094)."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# An optional request property that may be left out but not sent as null: `X | Omitted` keeps
# `null` out of its schema, and `reject_null` (a `mode="before"` field validator, which runs only
# for properties that are sent) makes an explicit null 422 (TRD 19 §4.5).
Omitted = SkipJsonSchema[None]


def reject_null(value: object) -> object:
    if value is None:
        raise ValueError("must not be null")
    return value


class Meta(ResponseModel):
    facility_name: str = Field(examples=["Edgewood"])
    facility_tz: str = Field(examples=["America/Chicago"])
    data_source_label: str = Field(examples=["pipeline test data v0.1"])
    as_of: datetime | None = Field(description="as-of of the latest succeeded pipeline run")
    baseline_n: int = Field(ge=1)
    cusum_h: float
    pipeline_profile: ConfigProfile


class PageMeta(ResponseModel):
    meta: Meta
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=500)
    offset: int = Field(ge=0)


class ProblemFieldError(ResponseModel):
    field: str = Field(examples=["records.3.loudness_dbfs"])
    code: str = Field(
        description=(
            "ingest endpoints: TRD 10 ING-023 field codes; other endpoints: Pydantic error type"
        ),
        examples=["invalid_type", "unknown_resident", "float_parsing"],
    )
    message: str


class Problem(ResponseModel):
    type: str = Field(pattern=r"^urn:echowell:error:[A-Z_]+$")
    title: str
    status: int = Field(ge=400, le=599)
    detail: str
    request_id: str
    errors: list[ProblemFieldError]


class DateWindow(ResponseModel):
    from_: date = Field(
        alias="from",
        description="first local date; not before the resident's enrolled_on in ResidentDetail",
    )
    to: date = Field(description="as-of local date")
    days: int = Field(ge=0, description="local days from..to inclusive (TRD 24 D-114)")
