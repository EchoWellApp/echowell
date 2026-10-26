"""ORM models RawSession and ProcessedSession (TRD 23 §4.6; FEAT-010, FEAT-011).

`raw_sessions` is append-only: a trigger and the grants each block UPDATE and DELETE (DB-004)."""

from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Double,
    FetchedValue,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TIME, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import (
    FEATURE_KEYS,
    SESSION_STATUS,
    Base,
    SessionStatus,
    sql_list,
)

if TYPE_CHECKING:
    from backend.models.score import Score


class RawSession(Base):
    """`raw_sessions` (TRD 20 §4.6.9; TRD 23 §4.2.9; FEAT-010)."""

    __tablename__ = "raw_sessions"
    __table_args__ = (
        UniqueConstraint("arrival_seq", name="raw_sessions_arrival_seq_uq"),
        CheckConstraint(
            "jsonb_typeof(payload) = 'object'",
            name="raw_sessions_payload_ck",
        ),
        CheckConstraint(
            "char_length(schema_version) BETWEEN 1 AND 16",
            name="raw_sessions_schema_version_ck",
        ),
        CheckConstraint(
            "char_length(session_id) BETWEEN 1 AND 64",
            name="raw_sessions_session_id_ck",
        ),
        CheckConstraint(
            "audio_quality_flag IN ('ok', 'poor')",
            name="raw_sessions_audio_quality_flag_ck",
        ),
        CheckConstraint(
            "speech_duration_s >= 0",
            name="raw_sessions_speech_duration_ck",
        ),
        CheckConstraint(
            "number_of_pauses >= 0",
            name="raw_sessions_number_of_pauses_ck",
        ),
        CheckConstraint(
            "pause_fraction BETWEEN 0 AND 1",
            name="raw_sessions_pause_fraction_ck",
        ),
        CheckConstraint(
            "voiced_fraction BETWEEN 0 AND 1",
            name="raw_sessions_voiced_fraction_ck",
        ),
        CheckConstraint(
            "mean_f0_hz > 0",
            name="raw_sessions_mean_f0_ck",
        ),
        CheckConstraint(
            "char_length(phrase_id) BETWEEN 1 AND 16",
            name="raw_sessions_phrase_id_ck",
        ),
        CheckConstraint(
            "char_length(extraction_software_version) BETWEEN 1 AND 64 AND "
            "char_length(device_firmware_version) BETWEEN 1 AND 64",
            name="raw_sessions_versions_ck",
        ),
        Index("raw_sessions_session_id_idx", "session_id", "arrival_seq"),
        Index("raw_sessions_resident_ts_idx", "resident_id", "timestamp_utc", "arrival_seq"),
        Index("raw_sessions_device_ts_idx", "device_id", text("timestamp_utc DESC")),
        Index("raw_sessions_batch_idx", "ingest_batch_id"),
        Index("raw_sessions_api_key_idx", "api_key_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    arrival_seq: Mapped[int] = mapped_column(
        BigInteger(), server_default=FetchedValue(), nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    ingest_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingest_batches.id", ondelete="RESTRICT"), nullable=True
    )
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_keys.id", ondelete="RESTRICT"), nullable=True
    )
    payload: Mapped[Any] = mapped_column(JSONB(), nullable=False)
    ingest_warnings: Mapped[Any] = mapped_column(
        JSONB(), server_default=text("'[]'::jsonb"), nullable=False
    )
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id", ondelete="RESTRICT"), nullable=False
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False
    )
    schema_version: Mapped[str] = mapped_column(Text(), nullable=False)
    session_id: Mapped[str] = mapped_column(Text(), nullable=False)
    resident_code: Mapped[str] = mapped_column(Text(), nullable=False)
    device_code: Mapped[str] = mapped_column(Text(), nullable=False)
    timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    mic_noise_level_dbfs: Mapped[float] = mapped_column(Double(), nullable=False)
    audio_quality_flag: Mapped[str] = mapped_column(Text(), nullable=False)
    extraction_software_version: Mapped[str] = mapped_column(Text(), nullable=False)
    device_firmware_version: Mapped[str] = mapped_column(Text(), nullable=False)
    speech_duration_s: Mapped[float] = mapped_column(Double(), nullable=False)
    phrase_id: Mapped[str] = mapped_column(Text(), nullable=False)
    loudness_dbfs: Mapped[float] = mapped_column(Double(), nullable=False)
    total_phrase_duration_s: Mapped[float] = mapped_column(Double(), nullable=False)
    speech_rate_syl_per_s: Mapped[float] = mapped_column(Double(), nullable=False)
    articulation_rate_syl_per_s: Mapped[float] = mapped_column(Double(), nullable=False)
    number_of_pauses: Mapped[int] = mapped_column(Integer(), nullable=False)
    pause_fraction: Mapped[float] = mapped_column(Double(), nullable=False)
    voiced_fraction: Mapped[float] = mapped_column(Double(), nullable=False)
    mean_f0_hz: Mapped[float] = mapped_column(Double(), nullable=False)
    f0_variability_st: Mapped[float] = mapped_column(Double(), nullable=False)
    jitter_local_pct: Mapped[float] = mapped_column(Double(), nullable=False)
    shimmer_local_pct: Mapped[float] = mapped_column(Double(), nullable=False)
    hnr_db: Mapped[float] = mapped_column(Double(), nullable=False)
    cpps_db: Mapped[float] = mapped_column(Double(), nullable=False)
    alpha_ratio_db: Mapped[float] = mapped_column(Double(), nullable=False)
    hammarberg_index_db: Mapped[float] = mapped_column(Double(), nullable=False)
    mfcc1: Mapped[float] = mapped_column(Double(), nullable=False)
    mfcc2: Mapped[float] = mapped_column(Double(), nullable=False)
    mfcc3: Mapped[float] = mapped_column(Double(), nullable=False)
    mfcc4: Mapped[float] = mapped_column(Double(), nullable=False)


class ProcessedSession(Base):
    """`processed_sessions` (TRD 20 §4.6.12; TRD 23 §4.2.12; FEAT-011)."""

    __tablename__ = "processed_sessions"
    __table_args__ = (
        UniqueConstraint("raw_session_id", name="processed_sessions_raw_session_uq"),
        CheckConstraint(
            "(status = 'duplicate' AND epoch_id IS NULL AND NOT late_arrival) OR "
            "(status <> 'duplicate' AND (epoch_id IS NOT NULL OR late_arrival))",
            name="processed_sessions_epoch_ck",
        ),
        CheckConstraint(
            "local_date BETWEEN (timestamp_utc AT TIME ZONE 'UTC')::date - 1 AND "
            "(timestamp_utc AT TIME ZONE 'UTC')::date + 1",
            name="processed_sessions_local_date_ck",
        ),
        CheckConstraint(
            "reason_text = array_to_string(reasons, '; ')",
            name="processed_sessions_reason_text_ck",
        ),
        CheckConstraint(
            "(status = 'usable' AND NOT late_arrival AND cardinality(reasons) = 0) OR "
            "(status = 'usable' AND late_arrival AND reasons = ARRAY['late arrival (not "
            "used for baseline or scores)']::text[]) OR (status = 'duplicate' AND "
            "reasons = ARRAY['session_id already received']::text[]) OR (status = "
            "'set_aside' AND cardinality(reasons) BETWEEN 1 AND 3 AND reasons <@ "
            "ARRAY['quality flag poor', 'noise above limit', 'speech too "
            "short']::text[]) OR (status = 'quarantined' AND NOT late_arrival AND "
            "cardinality(reasons) = 1 AND reasons[1] LIKE 'possible other speaker (F0 "
            "z=%; composite features with |z|>=3: %)') OR (status = 'quarantined' AND "
            "late_arrival AND cardinality(reasons) = 2 AND reasons[1] LIKE 'possible "
            "other speaker (F0 z=%; composite features with |z|>=3: %)' AND reasons[2] "
            "= 'late arrival (not used for baseline or scores)')",
            name="processed_sessions_status_reason_ck",
        ),
        CheckConstraint(
            "status <> 'quarantined' OR screen_detail IS NOT NULL",
            name="processed_sessions_screen_ck",
        ),
        CheckConstraint(
            "(status = 'usable' AND NOT late_arrival) = (baseline_ordinal IS NOT NULL) "
            "AND (baseline_ordinal IS NULL OR baseline_ordinal >= 1)",
            name="processed_sessions_ordinal_ck",
        ),
        CheckConstraint(
            "NOT in_baseline OR (status = 'usable' AND NOT late_arrival)",
            name="processed_sessions_in_baseline_ck",
        ),
        CheckConstraint(
            "(status = 'duplicate' AND adjusted_features IS NULL) OR (status <> 'duplicate' "
            "AND jsonb_typeof(adjusted_features) = 'object' "
            f"AND adjusted_features ?& ARRAY[{sql_list(FEATURE_KEYS)}])",
            name="processed_sessions_adjusted_ck",
        ),
        Index(
            "processed_sessions_resident_date_idx",
            "resident_id",
            "local_date",
            postgresql_include=["status"],
        ),
        Index(
            "processed_sessions_resident_ts_idx",
            "resident_id",
            text("timestamp_utc DESC"),
            postgresql_where=text("status <> 'duplicate'"),
        ),
        Index("processed_sessions_epoch_idx", "epoch_id", "timestamp_utc"),
        Index("processed_sessions_session_id_idx", "session_id"),
        Index("processed_sessions_run_idx", "pipeline_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    raw_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("raw_sessions.id", ondelete="RESTRICT"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(Text(), nullable=False)
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id", ondelete="RESTRICT"), nullable=False
    )
    epoch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("epochs.id", ondelete="RESTRICT"), nullable=True
    )
    status: Mapped[SessionStatus] = mapped_column(SESSION_STATUS, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(
        ARRAY(Text()), server_default=text("'{}'::text[]"), nullable=False
    )
    reason_text: Mapped[str] = mapped_column(Text(), server_default=text("''"), nullable=False)
    timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    local_date: Mapped[date] = mapped_column(Date(), nullable=False)
    local_time: Mapped[time] = mapped_column(TIME(precision=0), nullable=False)
    is_morning: Mapped[bool] = mapped_column(Boolean(), nullable=False)
    screen_detail: Mapped[str | None] = mapped_column(Text(), nullable=True)
    baseline_ordinal: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    in_baseline: Mapped[bool] = mapped_column(
        Boolean(), server_default=text("false"), nullable=False
    )
    late_arrival: Mapped[bool] = mapped_column(
        Boolean(), server_default=text("false"), nullable=False
    )
    adjusted_features: Mapped[Any | None] = mapped_column(JSONB(), nullable=True)
    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    raw_session: Mapped[RawSession] = relationship()
    score: Mapped[Score | None] = relationship(back_populates="processed_session")
