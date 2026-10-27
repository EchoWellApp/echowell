"""New-admission (experimental) DTOs of TRD 19 §4.5 (`AdmissionRow`, `AdmissionList`,
`AdmissionComparison`, `ReferenceRange`, `ReferenceRangeList`)."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import Field

from backend.schemas.common import Meta, PageMeta, ResponseModel
from backend.schemas.residents import BaselineProgress, FeatureKey, ResidentCode

ComparisonStatus = Literal[
    "outside_range", "within_range", "not_enough_checkins", "range_not_available"
]


class AdmissionRow(ResponseModel):
    resident_code: ResidentCode
    admitted_on: date | None
    checkins_so_far: int = Field(ge=0)
    comparison_status: ComparisonStatus
    own_baseline_progress: BaselineProgress


class AdmissionList(PageMeta):
    items: list[AdmissionRow]


class ComparisonFeature(ResponseModel):
    feature_key: FeatureKey
    resident_value: float | None = Field(
        description="median of the resident's usable check-ins so far"
    )
    low: float | None
    high: float | None
    outside_range: bool | None


class AdmissionComparison(ResponseModel):
    meta: Meta
    resident_code: ResidentCode
    comparison_status: ComparisonStatus
    features: list[ComparisonFeature]


class ReferenceRange(ResponseModel):
    feature_key: FeatureKey
    low: float
    high: float
    method: str = Field(description="definition pending OQ-08")
    n_residents: int = Field(ge=0)
    computed_at: datetime
    pipeline_run_id: uuid.UUID | None


class ReferenceRangeList(PageMeta):
    items: list[ReferenceRange]
