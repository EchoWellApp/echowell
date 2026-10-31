"""Audit log inserts (TRD 23 §4.2.23; TRD 06 DB-011; TRD 12 SEC-100..SEC-109; FEAT-012).

Insert-only and transaction-neutral: `insert` never commits, so an audited change and its audit row
commit or roll back together (DB-011). The table is append-only (trigger and grants, PGS-018).
Only `backend/services/audit_service.py` calls this module (FEAT-015-AC-07).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from backend.models import ActorType, AuditLog


class AuditRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def insert(
        self,
        *,
        actor_type: ActorType,
        actor_id: str | None,
        action: str,
        entity_type: str | None,
        entity_id: str | None,
        details: dict[str, Any],
        ip: str | None = None,
        request_id: str | None = None,
    ) -> int:
        """Insert one row in the caller's transaction and return its id."""
        return int(
            self.session.execute(
                insert(AuditLog)
                .values(
                    actor_type=actor_type,
                    actor_id=actor_id,
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    details=details,
                    ip=ip,
                    request_id=request_id,
                )
                .returning(AuditLog.id)
            ).scalar_one()
        )

    def login_failures_since(self, email: str, since: datetime) -> tuple[int, datetime | None]:
        """Count and latest time of `auth.login.failed` rows for `email` since `since` (SEC-015)."""
        count, latest = self.session.execute(
            select(func.count(), func.max(AuditLog.occurred_at)).where(
                AuditLog.action == "auth.login.failed",
                AuditLog.details["email"].astext == email,
                AuditLog.occurred_at >= since,
            )
        ).one()
        return int(count), latest
