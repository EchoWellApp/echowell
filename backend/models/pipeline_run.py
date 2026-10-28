"""ORM model PipelineRun (TRD 23 §4.6; FEAT-011)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import (
    PIPELINE_RUN_STATUS,
    PIPELINE_TRIGGER,
    Base,
    PipelineRunStatus,
    PipelineTrigger,
)


class PipelineRun(Base):
    """`pipeline_runs` (TRD 20 §4.6.10; TRD 23 §4.2.10; FEAT-011)."""

    __tablename__ = "pipeline_runs"
    __table_args__ = (
        CheckConstraint(
            "config_profile IN ('production', 'test_v0_1')",
            name="pipeline_runs_profile_ck",
        ),
        CheckConstraint(
            "(scope = '{\"type\": \"all\"}'::jsonb) OR (scope->>'type' = 'residents' AND "
            "jsonb_typeof(scope->'resident_codes') = 'array' AND "
            "jsonb_array_length(scope->'resident_codes') >= 1)",
            name="pipeline_runs_scope_ck",
        ),
        CheckConstraint(
            "jsonb_typeof(config_snapshot) = 'object'",
            name="pipeline_runs_snapshot_ck",
        ),
        CheckConstraint(
            "jsonb_typeof(counts) = 'object'",
            name="pipeline_runs_counts_ck",
        ),
        CheckConstraint(
            "jsonb_typeof(warnings) = 'array'",
            name="pipeline_runs_warnings_ck",
        ),
        CheckConstraint(
            "(status = 'running') = (finished_at IS NULL)",
            name="pipeline_runs_finished_ck",
        ),
        CheckConstraint(
            "(status = 'failed') = (error_message IS NOT NULL)",
            name="pipeline_runs_error_ck",
        ),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="pipeline_runs_order_ck",
        ),
        Index("pipeline_runs_started_idx", text("started_at DESC")),
        Index("pipeline_runs_status_idx", "status", postgresql_where=text("status = 'running'")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    trigger: Mapped[PipelineTrigger] = mapped_column(PIPELINE_TRIGGER, nullable=False)
    scope: Mapped[Any] = mapped_column(JSONB(), nullable=False)
    config_profile: Mapped[str] = mapped_column(Text(), nullable=False)
    config_snapshot: Mapped[Any] = mapped_column(JSONB(), nullable=False)
    code_version: Mapped[str] = mapped_column(Text(), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[PipelineRunStatus] = mapped_column(
        PIPELINE_RUN_STATUS, server_default=text("'running'"), nullable=False
    )
    counts: Mapped[Any] = mapped_column(JSONB(), server_default=text("'{}'::jsonb"), nullable=False)
    warnings: Mapped[Any] = mapped_column(
        JSONB(), server_default=text("'[]'::jsonb"), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
