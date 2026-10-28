"""ORM models Alert, AlertReview, DataAlert (TRD 23 §4.6, D-24; FEAT-012)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import (
    ALERT_STATUS,
    DATA_ALERT_KIND,
    DATA_ALERT_STATUS,
    REVIEW_OUTCOME,
    AlertStatus,
    Base,
    DataAlertKind,
    DataAlertStatus,
    ReviewOutcome,
)


class Alert(Base):
    """`alerts` (TRD 20 §4.6.17; TRD 23 §4.2.17; FEAT-012)."""

    __tablename__ = "alerts"
    __table_args__ = (
        UniqueConstraint("epoch_id", "session_id", name="alerts_epoch_session_uq"),
        CheckConstraint(
            "cusum_value >= 0",
            name="alerts_cusum_ck",
        ),
        CheckConstraint(
            "(status = 'closed') = (closed_reason IS NOT NULL) AND (status = 'closed') "
            "= (closed_at IS NOT NULL)",
            name="alerts_closed_ck",
        ),
        CheckConstraint(
            "closed_reason IS NULL OR closed_reason IN ('epoch ended', 'admin', "
            "'superseded by rebuild')",
            name="alerts_closed_reason_ck",
        ),
        CheckConstraint(
            "(acknowledged_by IS NULL) = (acknowledged_at IS NULL)",
            name="alerts_ack_ck",
        ),
        CheckConstraint(
            "status <> 'acknowledged' OR acknowledged_at IS NOT NULL",
            name="alerts_ack_status_ck",
        ),
        CheckConstraint(
            "(snoozed_until IS NULL) = (snoozed_by IS NULL)",
            name="alerts_snooze_ck",
        ),
        Index(
            "alerts_one_active_per_epoch_uq",
            "epoch_id",
            unique=True,
            postgresql_where=text("status <> 'closed'"),
        ),
        Index("alerts_status_triggered_idx", "status", text("triggered_at DESC")),
        Index("alerts_resident_triggered_idx", "resident_id", text("triggered_at DESC")),
        Index("alerts_acknowledged_by_idx", "acknowledged_by"),
        Index("alerts_run_idx", "pipeline_run_id"),
        Index("alerts_snoozed_by_idx", "snoozed_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id", ondelete="RESTRICT"), nullable=False
    )
    epoch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("epochs.id", ondelete="RESTRICT"), nullable=False
    )
    session_id: Mapped[str] = mapped_column(Text(), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    local_date: Mapped[date] = mapped_column(Date(), nullable=False)
    cusum_value: Mapped[float] = mapped_column(Double(), nullable=False)
    status: Mapped[AlertStatus] = mapped_column(
        ALERT_STATUS, server_default=text("'open'"), nullable=False
    )
    closed_reason: Mapped[str | None] = mapped_column(Text(), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snoozed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    reviews: Mapped[list[AlertReview]] = relationship(
        back_populates="alert", order_by="AlertReview.created_at.desc()"
    )


class AlertReview(Base):
    """`alert_reviews` (TRD 20 §4.6.18; TRD 23 §4.2.18; FEAT-012)."""

    __tablename__ = "alert_reviews"
    __table_args__ = (
        CheckConstraint(
            "cardinality(explanations) <= 20 AND array_to_string(explanations, ',') ~ "
            "'^([a-z][a-z0-9_]{0,63}(,[a-z][a-z0-9_]{0,63})*)?$'",
            name="alert_reviews_explanations_ck",
        ),
        CheckConstraint(
            "note IS NULL OR (char_length(btrim(note)) >= 1 AND char_length(note) <= " "2000)",
            name="alert_reviews_note_ck",
        ),
        Index("alert_reviews_alert_created_idx", "alert_id", text("created_at DESC")),
        Index("alert_reviews_reviewer_idx", "reviewer_user_id"),
        Index("alert_reviews_outcome_idx", "outcome"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="RESTRICT"), nullable=False
    )
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    explanations: Mapped[list[str]] = mapped_column(
        ARRAY(Text()), server_default=text("'{}'::text[]"), nullable=False
    )
    outcome: Mapped[ReviewOutcome] = mapped_column(REVIEW_OUTCOME, nullable=False)
    note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )

    alert: Mapped[Alert] = relationship(back_populates="reviews")


class DataAlert(Base):
    """`data_alerts` (TRD 20 §4.6.19; TRD 23 §4.2.19; FEAT-012)."""

    __tablename__ = "data_alerts"
    __table_args__ = (
        UniqueConstraint("alert_review_id", name="data_alerts_alert_review_uq"),
        CheckConstraint(
            "(kind = 'device_silent' AND device_id IS NOT NULL AND resident_id IS NULL "
            "AND alert_review_id IS NULL) OR (kind IN ('baseline_stalled', "
            "'possible_other_speaker', 'high_set_aside') AND resident_id IS NOT NULL "
            "AND device_id IS NULL AND alert_review_id IS NULL) OR (kind = "
            "'review_flagged_data_problem' AND resident_id IS NOT NULL AND "
            "alert_review_id IS NOT NULL)",
            name="data_alerts_subject_ck",
        ),
        CheckConstraint(
            "(kind = 'review_flagged_data_problem') = (pipeline_run_id IS NULL)",
            name="data_alerts_run_ck",
        ),
        CheckConstraint(
            "(status = 'resolved') = (resolved_at IS NOT NULL)",
            name="data_alerts_resolved_ck",
        ),
        CheckConstraint(
            "last_detected_at >= first_detected_at",
            name="data_alerts_detected_ck",
        ),
        CheckConstraint(
            "char_length(title) BETWEEN 1 AND 200 AND char_length(detail) <= 500",
            name="data_alerts_text_ck",
        ),
        Index(
            "data_alerts_open_subject_uq",
            "kind",
            "resident_id",
            "device_id",
            unique=True,
            postgresql_nulls_not_distinct=True,
            postgresql_where=text("status = 'open' AND kind <> 'review_flagged_data_problem'"),
        ),
        Index("data_alerts_status_detected_idx", "status", text("last_detected_at DESC")),
        Index("data_alerts_resident_idx", "resident_id"),
        Index("data_alerts_device_idx", "device_id"),
        Index("data_alerts_run_idx", "pipeline_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    kind: Mapped[DataAlertKind] = mapped_column(DATA_ALERT_KIND, nullable=False)
    resident_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id", ondelete="RESTRICT"), nullable=True
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="RESTRICT"), nullable=True
    )
    alert_review_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alert_reviews.id", ondelete="RESTRICT"), nullable=True
    )
    title: Mapped[str] = mapped_column(Text(), nullable=False)
    detail: Mapped[str] = mapped_column(Text(), server_default=text("''"), nullable=False)
    first_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[DataAlertStatus] = mapped_column(
        DATA_ALERT_STATUS, server_default=text("'open'"), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pipeline_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )
