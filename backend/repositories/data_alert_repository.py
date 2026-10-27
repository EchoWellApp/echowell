"""Data alerts (TRD 23 §4.2.19, §4.3.7; TRD 06 DB-036; FEAT-012).

Rule kinds are keyed by `(kind, resident_id, device_id)` with at most one open row per subject
(`data_alerts_open_subject_uq`, PGS-041). The app updates data alerts but never deletes them.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import DataAlert, DataAlertKind, DataAlertStatus, Device, Resident


class DataAlertRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def open_for_subject(
        self,
        kind: DataAlertKind,
        *,
        resident_id: uuid.UUID | None = None,
        device_id: uuid.UUID | None = None,
        for_update: bool = False,
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
        if for_update:
            query = query.with_for_update()
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

    def get(self, data_alert_id: uuid.UUID) -> DataAlert | None:
        return self.session.get(DataAlert, data_alert_id)

    def list_with_codes(
        self, *, status: DataAlertStatus, kind: DataAlertKind | None = None
    ) -> list[tuple[DataAlert, str | None, str | None]]:
        """Data alerts with the resident and device codes of their subject (API-133)."""
        query = (
            select(DataAlert, Resident.resident_code, Device.device_code)
            .outerjoin(Resident, Resident.id == DataAlert.resident_id)
            .outerjoin(Device, Device.id == DataAlert.device_id)
            .where(DataAlert.status == status)
        )
        if kind is not None:
            query = query.where(DataAlert.kind == kind)
        return [(row, r, d) for row, r, d in self.session.execute(query).all()]
