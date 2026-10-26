"""Alerts and alert reviews (TRD 23 §4.2.17, §4.2.18, §4.3.2; TRD 06 DB-018; FEAT-012).

Alerts are keyed by `(epoch_id, session_id)` so their id, review state and snooze survive rebuilds
(D-45). The app may update alerts but never delete them; reviews are append-only (SELECT, INSERT).
Review and snooze only change `status`, `acknowledged_*` and `snoozed_*` (DME-007, DME-022).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Alert, AlertReview, AlertStatus, ReviewOutcome

CLOSED_REASONS = frozenset({"epoch ended", "admin", "superseded by rebuild"})


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
    ) -> AlertReview:
        review = AlertReview(
            alert_id=alert_id,
            reviewer_user_id=reviewer_user_id,
            outcome=outcome,
            explanations=explanations,
            note=note,
        )
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
