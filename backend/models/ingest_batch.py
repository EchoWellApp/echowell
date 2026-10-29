"""ORM models IngestBatch and IngestRejection (TRD 23 §4.6; FEAT-010)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import (
    INGEST_SOURCE,
    Base,
    IngestSource,
)


class IngestBatch(Base):
    """`ingest_batches` (TRD 20 §4.6.7; TRD 23 §4.2.7; FEAT-010)."""

    __tablename__ = "ingest_batches"
    __table_args__ = (
        CheckConstraint(
            "record_count >= 0 AND accepted_count >= 0 AND rejected_count >= 0 AND "
            "duplicate_count >= 0 AND accepted_count + rejected_count <= record_count "
            "AND duplicate_count <= accepted_count",
            name="ingest_batches_counts_ck",
        ),
        CheckConstraint(
            "source = 'seed' OR uploaded_by IS NOT NULL OR api_key_id IS NOT NULL",
            name="ingest_batches_actor_ck",
        ),
        CheckConstraint(
            "(source = 'csv_upload') <= (filename IS NOT NULL)",
            name="ingest_batches_filename_ck",
        ),
        Index("ingest_batches_received_idx", text("received_at DESC")),
        Index("ingest_batches_uploaded_by_idx", "uploaded_by"),
        Index("ingest_batches_api_key_idx", "api_key_id"),
        Index("ingest_batches_pipeline_run_idx", "pipeline_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    source: Mapped[IngestSource] = mapped_column(INGEST_SOURCE, nullable=False)
    filename: Mapped[str | None] = mapped_column(Text(), nullable=True)
    record_count: Mapped[int] = mapped_column(Integer(), server_default=text("0"), nullable=False)
    accepted_count: Mapped[int] = mapped_column(Integer(), server_default=text("0"), nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer(), server_default=text("0"), nullable=False)
    duplicate_count: Mapped[int] = mapped_column(
        Integer(), server_default=text("0"), nullable=False
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_keys.id", ondelete="RESTRICT"), nullable=True
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    # The run this batch started (migration 0003, TRD 20 §4.13, D-124); null when none was.
    pipeline_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    rejections: Mapped[list[IngestRejection]] = relationship(back_populates="batch")


class IngestRejection(Base):
    """`ingest_rejections` (TRD 20 §4.6.8; TRD 23 §4.2.8; FEAT-010)."""

    __tablename__ = "ingest_rejections"
    __table_args__ = (
        CheckConstraint(
            "jsonb_typeof(errors) = 'array' AND jsonb_array_length(errors) >= 1",
            name="ingest_rejections_errors_ck",
        ),
        CheckConstraint(
            "row_number IS NULL OR row_number >= 1",
            name="ingest_rejections_row_number_ck",
        ),
        Index("ingest_rejections_batch_idx", "ingest_batch_id"),
        Index("ingest_rejections_received_idx", text("received_at DESC")),
        Index("ingest_rejections_api_key_idx", "api_key_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    ingest_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ingest_batches.id", ondelete="RESTRICT"), nullable=True
    )
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("api_keys.id", ondelete="RESTRICT"), nullable=True
    )
    row_number: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    raw_body: Mapped[Any] = mapped_column(JSONB(), nullable=False)
    errors: Mapped[Any] = mapped_column(JSONB(), nullable=False)

    batch: Mapped[IngestBatch | None] = relationship(back_populates="rejections")
