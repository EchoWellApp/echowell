"""Alerts and alert reviews (TRD 23 §4.2.17, §4.2.18, §4.3.2; TRD 06 DB-018; FEAT-012).

Alerts are keyed by `(epoch_id, session_id)` so their id, review state and snooze survive rebuilds
(D-45). The app may update alerts but never delete them; reviews are append-only (SELECT, INSERT).
Review and snooze only change `status`, `acknowledged_*` and `snoozed_*` (DME-007, DME-022).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from backend.models import (
    Alert,
    AlertReview,
    AlertStatus,
    CusumState,
    Device,
    Epoch,
    Resident,
    ReviewOutcome,
    User,
)

CLOSED_REASONS = frozenset({"epoch ended", "admin", "superseded by rebuild"})
_FactsRow = tuple[Alert, str, int, str | None, float | None, int, datetime | None]


@dataclass(frozen=True)
class AlertFacts:
    """An alert with the facts of the `Alert` DTO that live in other tables (TRD 23 §4.4.1)."""

    alert: Alert
    resident_code: str
    epoch_number: int
    device_code: str | None
    current_tally: float | None
    review_count: int
    last_reviewed_at: datetime | None


class AlertRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, alert_id: uuid.UUID) -> Alert | None:
        return self.session.get(Alert, alert_id)

    def get_by_key(self, epoch_id: uuid.UUID, session_id: str) -> Alert | None:
        return self.session.scalars(
            select(Alert).where(Alert.epoch_id == epoch_id, Alert.session_id == session_id)
        ).first()

    def non_closed_for_epoch(self, epoch_id: uuid.UUID) -> Alert | None:
        """The epoch's open or acknowledged alert (at most one, PGS-029)."""
        return self.session.scalars(
            select(Alert).where(Alert.epoch_id == epoch_id, Alert.status != AlertStatus.CLOSED)
        ).first()

    def list_by_status(
        self, *, statuses: tuple[AlertStatus, ...] = (AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED)
    ) -> list[Alert]:
        return list(
            self.session.scalars(
                select(Alert)
                .where(Alert.status.in_(statuses))
                .order_by(Alert.local_date, Alert.triggered_at)
            ).all()
        )

    def insert(self, alert: Alert) -> Alert:
        self.session.add(alert)
        self.session.flush()
        return alert

    def close(self, alert: Alert, *, reason: str, at: datetime) -> Alert:
        if reason not in CLOSED_REASONS:
            raise ValueError(f"unknown closed_reason {reason!r}")
        alert.status = AlertStatus.CLOSED
        alert.closed_reason = reason
        alert.closed_at = at
        self.session.flush()
        return alert

    def set_acknowledged(self, alert: Alert, *, by: uuid.UUID, at: datetime) -> Alert:
        """A saved review marks the alarm reviewed; the alarm itself stays on (OQ-05)."""
        if alert.status == AlertStatus.CLOSED:
            raise ValueError("a closed alert cannot be acknowledged")
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_by = by
        alert.acknowledged_at = at
        self.session.flush()
        return alert

    def snooze(self, alert: Alert, *, by: uuid.UUID, until: datetime) -> Alert:
        """Set the "Remind me in 24 hours" reminder (D-37); never changes the alarm or tally."""
        alert.snoozed_until = until
        alert.snoozed_by = by
        self.session.flush()
        return alert

    def insert_review(
        self,
        *,
        alert_id: uuid.UUID,
        reviewer_user_id: uuid.UUID,
        outcome: ReviewOutcome,
        explanations: list[str],
        note: str | None,
        created_at: datetime | None = None,
    ) -> AlertReview:
        """`created_at` defaults to the database clock; the API passes the application clock."""
        review = AlertReview(
            alert_id=alert_id,
            reviewer_user_id=reviewer_user_id,
            outcome=outcome,
            explanations=explanations,
            note=note,
        )
        if created_at is not None:
            review.created_at = created_at
        self.session.add(review)
        self.session.flush()
        return review

    def reviews(self, alert_id: uuid.UUID) -> list[AlertReview]:
        """The alert's reviews, newest first (CUS-017)."""
        return list(
            self.session.scalars(
                select(AlertReview)
                .where(AlertReview.alert_id == alert_id)
                .order_by(AlertReview.created_at.desc())
            ).all()
        )

    def _facts_query(self) -> Select[_FactsRow]:
        reviews = (
            select(
                AlertReview.alert_id,
                func.count().label("n"),
                func.max(AlertReview.created_at).label("last"),
            )
            .group_by(AlertReview.alert_id)
            .subquery()
        )
        return (
            select(
                Alert, Resident.resident_code, Epoch.epoch_number, Device.device_code,
                CusumState.current_tally, func.coalesce(reviews.c.n, 0), reviews.c.last,
            )
            .join(Resident, Resident.id == Alert.resident_id)
            .join(Epoch, Epoch.id == Alert.epoch_id)
            .outerjoin(Device, Device.id == Epoch.device_id)
            .outerjoin(CusumState, CusumState.epoch_id == Alert.epoch_id)
            .outerjoin(reviews, reviews.c.alert_id == Alert.id)
        )  # fmt: skip

    def list_with_facts(
        self,
        *,
        status: AlertStatus | None = None,
        resident_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AlertFacts], int]:
        """Alerts by `triggered_at` ascending with their DTO facts in one query (API-080)."""
        query = self._facts_query()
        if status is not None:
            query = query.where(Alert.status == status)
        if resident_id is not None:
            query = query.where(Alert.resident_id == resident_id)
        total = self.session.scalar(select(func.count()).select_from(query.subquery())) or 0
        rows = self.session.execute(
            query.order_by(Alert.triggered_at, Alert.id).limit(limit).offset(offset)
        ).all()
        return [AlertFacts(*row) for row in rows], total

    def facts(self, alert_id: uuid.UUID) -> AlertFacts | None:
        row = self.session.execute(self._facts_query().where(Alert.id == alert_id)).first()
        return AlertFacts(*row) if row is not None else None

    def get_for_update(self, alert_id: uuid.UUID) -> Alert | None:
        """The alert row locked for a review or snooze (one writer at a time)."""
        return self.session.scalars(
            select(Alert).where(Alert.id == alert_id).with_for_update()
        ).first()

    def reviews_page(
        self, alert_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> tuple[list[tuple[AlertReview, str]], int]:
        """Reviews newest first with the reviewer's display name (API-131)."""
        total = self.session.scalar(
            select(func.count()).select_from(AlertReview).where(AlertReview.alert_id == alert_id)
        )
        rows = self.session.execute(
            select(AlertReview, User.display_name)
            .join(User, User.id == AlertReview.reviewer_user_id)
            .where(AlertReview.alert_id == alert_id)
            .order_by(AlertReview.created_at.desc(), AlertReview.id)
            .limit(limit)
            .offset(offset)
        ).all()
        return [(review, name) for review, name in rows], int(total or 0)
