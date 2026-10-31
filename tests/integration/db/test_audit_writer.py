"""Audit writer against PostgreSQL (TRD 12 §4.12; SEC-100..SEC-109; FEAT-015)."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from backend.models import ActorType, AuditLog, NoteType, StaffNote
from backend.services import audit_service
from backend.services.audit_service import DETAIL_KEYS, AuditAction
from tests.integration.db_support import PgUrls
from tests.integration.world import World

pytestmark = pytest.mark.integration

SAMPLE_VALUES: dict[str, Any] = {
    "email": "a@example.com", "reason": "bad_credentials", "source": "api",
    "record_count": 1, "accepted": 1, "rejected": 0, "duplicates": 0, "resident_code": "R01",
    "note_type": "observation", "alert_id": "x", "supersedes_id": None, "review_id": "x",
    "outcome": "no_concern", "explanation_count": 0, "previous_status": "open", "hours": 24,
    "snoozed_until": "2026-10-31T00:00:00Z", "filters": {}, "row_count": 0, "trigger": "manual",
    "scope": {"type": "all"}, "profile": "test_v0_1", "status": "succeeded",
    "duration_ms": 1, "warning_count": 0, "old": 1, "new": 2, "operator": "ops",
    "rotated": False, "role": "admin", "changed": ["active"], "name": "k", "device_code": "D01",
    "code": "FORBIDDEN", "closed_reason": "admin", "kind": "device_silent", "from": "a", "to": "b",
    "epoch_number": 1, "withdrawn_on": "2026-10-20", "row_counts": {}, "residents": 10,
    "devices": 10, "device_assignments": 11, "old_config_hash": "a", "new_config_hash": "b",
    "pipeline_run_id": None,
}  # fmt: skip


@pytest.mark.req("SEC-109", "SEC-100", "FEAT-015-AC-01")
def test_every_action_inserts_exactly_one_row(app_session: Session) -> None:
    before = app_session.scalar(select(func.count()).select_from(AuditLog))
    for action in AuditAction:
        details = {key: SAMPLE_VALUES[key] for key in DETAIL_KEYS[action]}
        if action is AuditAction.ACCESS_DENIED:
            details["status"] = 403
        audit_service.record(
            app_session, action=action, actor_type=ActorType.SYSTEM, actor_id=None,
            entity_type="test", entity_id=action.value, details=details,
        )  # fmt: skip
    rows = app_session.execute(
        select(AuditLog.action, func.count())
        .where(AuditLog.entity_type == "test")
        .group_by(AuditLog.action)
    ).all()
    assert dict(map(tuple, rows)) == {a.value: 1 for a in AuditAction}
    assert app_session.scalar(select(func.count()).select_from(AuditLog)) == before + 24


def _note_with_audit(session: Session, world: World) -> None:
    author = session.execute(
        text(
            "INSERT INTO users (email, display_name, password_hash, role) "
            "VALUES ('n@example.com', 'N', '$argon2id$x', 'clinician') RETURNING id"
        )
    ).scalar_one()
    note = StaffNote(
        resident_id=world.residents["R01"], author_user_id=author,
        note_type=NoteType.OBSERVATION, body="Synthetic note",
    )  # fmt: skip
    session.add(note)
    session.flush()
    audit_service.record(
        session, action=AuditAction.NOTE_CREATED, actor_type=ActorType.USER,
        actor_id=str(author), entity_type="staff_note", entity_id=str(note.id),
        details={"resident_code": "R01", "note_type": "observation"},
    )  # fmt: skip


def _counts(engine_url: str) -> tuple[int, int]:
    engine = create_engine(engine_url, poolclass=NullPool)
    try:
        with engine.connect() as conn:
            notes = conn.execute(text("SELECT count(*) FROM staff_notes")).scalar_one()
            audits = conn.execute(
                text("SELECT count(*) FROM audit_logs WHERE action = 'note.created'")
            ).scalar_one()
        return notes, audits
    finally:
        engine.dispose()


@pytest.mark.req("DB-011", "SEC-101", "LOG-090", "FEAT-015-AC-03")
def test_audit_row_shares_the_change_transaction(fresh_db: PgUrls) -> None:
    engine = create_engine(fresh_db.app, poolclass=NullPool)
    try:
        with Session(engine) as session:
            world = World.build(session)
            session.commit()
            _note_with_audit(session, world)
            session.rollback()
        assert _counts(fresh_db.app) == (0, 0)
        with Session(engine) as session:
            world = World.build(session)
            _note_with_audit(session, world)
            session.commit()
        assert _counts(fresh_db.app) == (1, 1)
    finally:
        engine.dispose()


@pytest.mark.req("SEC-101", "D-87", "FEAT-015-FR-06")
def test_refused_request_rows_survive_a_rollback(fresh_db: PgUrls) -> None:
    engine = create_engine(fresh_db.app, poolclass=NullPool)
    try:
        audit_service.record_committed(
            engine, action=AuditAction.ACCESS_DENIED, actor_type=ActorType.SYSTEM,
            actor_id=None, entity_type=None, entity_id=None,
            details={"status": 403, "code": "FORBIDDEN"},
        )  # fmt: skip
        with engine.connect() as conn:
            count = conn.execute(
                text("SELECT count(*) FROM audit_logs WHERE action = 'access.denied'")
            ).scalar_one()
        assert count == 1
    finally:
        engine.dispose()
