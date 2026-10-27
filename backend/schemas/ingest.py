"""Ingest DTOs of TRD 19 §4.5 (`IngestRecord`, `IngestBatchRequest`, `IngestResult`,
`IngestBatchAccepted`, `IngestBatch`, `IngestRejection`).

The ingest handlers read the raw body themselves (API-031): `IngestRecord` and
`IngestBatchRequest` document the request bodies in OpenAPI; validation is
`backend.services.validation` so that every violation is collected and stored (ING-019).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import ConfigDict, Field

from backend.schemas.common import (
    DeviceCode,
    ProblemFieldError,
    RequestModel,
    ResidentCode,
    ResponseModel,
    SessionId,
)

type IngestOutcome = Literal["usable", "set_aside", "quarantined", "duplicate", "pending"]
type IngestSource = Literal["api_single", "api_batch", "csv_upload", "seed"]
_Version = Annotated[str, Field(min_length=1, max_length=64)]


class IngestRecord(RequestModel):
    """Schema v0.1; property order equals the SRC-05 CSV header. Feature names are placeholders
    (OQ-03) mapped by configuration."""

    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal["0.1"]
    session_id: SessionId
    resident_id: ResidentCode
    device_id: DeviceCode
    timestamp_utc: str = Field(
        pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$",
        examples=["2026-10-21 19:07:50"],
    )
    mic_noise_level_dbfs: float
    audio_quality_flag: Literal["ok", "poor"]
    extraction_software_version: _Version
    device_firmware_version: _Version
    speech_duration_s: float = Field(ge=0)
    phrase_id: str = Field(min_length=1, max_length=16)
    loudness_dbfs: float
    total_phrase_duration_s: float = Field(ge=0)
    speech_rate_syl_per_s: float
    articulation_rate_syl_per_s: float
    number_of_pauses: int = Field(ge=0)
    pause_fraction: float = Field(ge=0, le=1)
    voiced_fraction: float = Field(ge=0, le=1)
    mean_f0_hz: float
    f0_variability_st: float
    jitter_local_pct: float
    shimmer_local_pct: float
    hnr_db: float
    cpps_db: float
    alpha_ratio_db: float
    hammarberg_index_db: float
    mfcc1: float
    mfcc2: float
    mfcc3: float
    mfcc4: float


class IngestBatchRequest(RequestModel):
    records: list[IngestRecord] = Field(min_length=1, max_length=5000)


class IngestResult(ResponseModel):
    raw_session_id: uuid.UUID
    arrival_seq: int = Field(ge=1)
    session_id: SessionId
    status_after_processing: IngestOutcome
    reasons: list[str]
    pipeline_run_id: uuid.UUID | None


class IngestBatchAccepted(ResponseModel):
    ingest_batch_id: uuid.UUID
    source: IngestSource
    accepted: int = Field(ge=0, description="stored in raw_sessions, duplicates included")
    rejected: int = Field(ge=0)
    duplicates: int = Field(ge=0)
    pipeline_run_id: uuid.UUID | None = Field(
        description="null when no first-arrival record was accepted"
    )


class IngestRejection(ResponseModel):
    row_number: int = Field(ge=1, description="1-based position in the batch (CSV excludes header)")
    session_id: str | None
    received_at: datetime
    errors: list[ProblemFieldError]


class IngestBatch(ResponseModel):
    id: uuid.UUID
    source: IngestSource
    filename: str | None
    record_count: int
    accepted_count: int
    rejected_count: int
    duplicate_count: int
    uploaded_by: uuid.UUID | None
    received_at: datetime
    pipeline_run_id: uuid.UUID | None
    rejections: list[IngestRejection]
