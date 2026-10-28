"""Data alerts (TRD 23 §4.2.19, §4.3.7; TRD 06 DB-036; FEAT-012).

Rule kinds are keyed by `(kind, resident_id, device_id)` with at most one open row per subject
(`data_alerts_open_subject_uq`, PGS-041). The app updates data alerts but never deletes them.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import DataAlert, DataAlertKind, DataAlertStatus


class DataAlertRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def open_for_subject(
        self,
        kind: DataAlertKind,
        *,
        resident_id: uuid.UUID | None = None,
        device_id: uuid.UUID | None = None,
    ) -> DataAlert | None:
        query = select(DataAlert).where(
            DataAlert.kind == kind, DataAlert.status == DataAlertStatus.OPEN
        )
        query = query.where(
            DataAlert.resident_id.is_(None)
            if resident_id is None
            else DataAlert.resident_id == resident_id
        )
        query = query.where(
            DataAlert.device_id.is_(None) if device_id is None else DataAlert.device_id == device_id
        )
        return self.session.scalars(query).first()

    def list_open(self) -> list[DataAlert]:
        return list(
            self.session.scalars(
                select(DataAlert)
                .where(DataAlert.status == DataAlertStatus.OPEN)
                .order_by(DataAlert.kind, DataAlert.first_detected_at)
            ).all()
        )

    def insert(self, data_alert: DataAlert) -> DataAlert:
        self.session.add(data_alert)
        self.session.flush()
        return data_alert

    def resolve(self, data_alert: DataAlert, *, at: datetime) -> DataAlert:
        data_alert.status = DataAlertStatus.RESOLVED
        data_alert.resolved_at = at
        self.session.flush()
        return data_alert
