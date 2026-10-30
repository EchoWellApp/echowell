"""Data alerts: the read-only list and the operator resolution of review-flagged problems
(TRD 05 API-133; TRD 09 CUS-040, CUS-045; TRD 15 §4.8; TRD 19 E-30; FEAT-032).

The API never computes, creates or changes a rule-based data alert (CUS-045); data alerts never
count as alarms (FR-300).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.models import DataAlertKind, DataAlertStatus
from backend.repositories.data_alert_repository import DataAlertRepository
from backend.services import audit_service
from backend.services.audit_service import AuditAction
from backend.services.resident_service import ReadContext, natural_key

KIND_ORDER: tuple[str, ...] = tuple(kind.value for kind in DataAlertKind)  # the enum order


class DataAlertRefusalError(Exception):
    """`resolve-data-alert` refuses (exit code 2, TRD 15 §4.8)."""


def list_data_alerts(
    session: Session, ctx: ReadContext, *, status: str, kind: str | None, limit: int, offset: int
) -> dict[str, Any]:
    """By kind in enum order, then natural resident or device code (CUS-045)."""
    rows = DataAlertRepository(session).list_with_codes(
        status=DataAlertStatus(status), kind=DataAlertKind(kind) if kind else None
    )
    rows.sort(
        key=lambda r: (KIND_ORDER.index(r[0].kind.value), natural_key(r[1] or r[2] or ""), r[0].id)
    )
    items = [
        {
            "id": alert.id, "kind": alert.kind.value, "resident_code": resident_code,
            "device_code": device_code, "title": alert.title, "detail": alert.detail,
            "status": alert.status.value, "first_detected_at": alert.first_detected_at,
            "last_detected_at": alert.last_detected_at, "pipeline_run_id": alert.pipeline_run_id,
        }
        for alert, resident_code, device_code in rows[offset : offset + limit]
    ]  # fmt: skip
    return {"meta": ctx.meta, "items": items, "total": len(rows), "limit": limit, "offset": offset}


def resolve(session: Session, data_alert_id: uuid.UUID, reason: str, now: datetime) -> None:
    """Resolve one open `review_flagged_data_problem` row with a `data_alert.resolved` audit row
    in the caller's transaction (FR-297; the only resolution path, FEAT-032-FR-07)."""
    repository = DataAlertRepository(session)
    alert = repository.get(data_alert_id)
    if alert is None:
        raise DataAlertRefusalError(f"unknown data alert {data_alert_id}")
    if alert.kind != DataAlertKind.REVIEW_FLAGGED_DATA_PROBLEM:
        raise DataAlertRefusalError(
            f"data alert {data_alert_id} is {alert.kind.value}; only review_flagged_data_problem "
            "alerts are resolved by hand"
        )
    if alert.status != DataAlertStatus.OPEN:
        raise DataAlertRefusalError(f"data alert {data_alert_id} is not open")
    repository.resolve(alert, at=now)
    audit_service.record_cli(
        session, action=AuditAction.DATA_ALERT_RESOLVED, entity_type="data_alert",
        entity_id=str(alert.id),
        details={"alert_id": str(alert.id), "kind": alert.kind.value, "reason": reason},
    )  # fmt: skip
