"""`python -m backend.cli resolve-data-alert` (TRD 15 §4.8; TRD 09 CUS-040; FEAT-032-FR-05..07)."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from backend.core.security import DUMMY_PASSWORD_HASH
from backend.models import DataAlert, ReviewOutcome, UserRole
from backend.repositories.alert_repository import AlertRepository
from backend.repositories.user_repository import UserRepository
from tests.integration.conftest import Cli
from tests.integration.world import T0, World

pytestmark = pytest.mark.integration


def _world(cli: Cli) -> tuple[World, Session]:
    """The test_v0_1 roster, a run and one reviewed alert of R09, committed in the CLI's
    throwaway database."""
    session = Session(create_engine(cli.urls.app, poolclass=NullPool))
    world = World.build(session)
    user = UserRepository(session).insert(
        email="ops@example.test",
        display_name="Ops",
        password_hash=DUMMY_PASSWORD_HASH,
        role=UserRole.ADMIN,
    )
    epoch = world.epoch("R09", "D09")
    world.alert_id = world.alert("R09", epoch, "R09-20261021-01", date(2026, 10, 21))  # type: ignore[attr-defined]
    world.user_id = user.id  # type: ignore[attr-defined]
    session.commit()
    return world, session


def _data_alert(world: World, session: Session, kind: str, *, status: str = "open") -> str:
    """Insert one data alert of R09 (or of device D02 for `device_silent`) and commit it."""
    if kind == "device_silent":
        row = DataAlert(
            kind=kind, device_id=world.devices["D02"], title="t", detail="d", first_detected_at=T0,
            last_detected_at=T0, status="open", pipeline_run_id=world.run_id,
        )  # fmt: skip
    else:
        review = AlertRepository(session).insert_review(
            alert_id=world.alert_id, reviewer_user_id=world.user_id,  # type: ignore[attr-defined]
            outcome=ReviewOutcome.DATA_PROBLEM, explanations=[], note=None,
        )  # fmt: skip
        row = DataAlert(
            kind=kind, resident_id=world.residents["R09"], alert_review_id=review.id,
            title="t", detail="d", first_detected_at=T0, last_detected_at=T0, status=status,
            resolved_at=T0 if status == "resolved" else None,
        )  # fmt: skip
    session.add(row)
    session.commit()
    return str(row.id)


def _state(cli: Cli) -> tuple[list[tuple[str, str]], int]:
    alerts = [
        tuple(r) for r in cli.rows("SELECT id::text, status::text FROM data_alerts ORDER BY id")
    ]
    audits = int(cli.scalar("SELECT count(*) FROM audit_logs WHERE action = 'data_alert.resolved'"))
    return alerts, audits  # type: ignore[return-value]


@pytest.mark.req("FR-297", "TST-189", "SEC-103", "FEAT-032-AC-04", "FEAT-032-FR-05")
def test_resolves_a_review_flagged_data_problem(cli: Cli) -> None:
    world, session = _world(cli)
    alert_id = _data_alert(world, session, "review_flagged_data_problem")
    session.close()
    result = cli("resolve-data-alert", "--id", alert_id, "--reason", "checked")
    assert result.code == 0, result.out + result.err
    status, resolved_at = cli.rows(
        "SELECT status::text, resolved_at FROM data_alerts WHERE id = :i", i=alert_id
    )[0]
    assert status == "resolved"
    assert resolved_at is not None
    audits = cli.rows(
        "SELECT actor_type::text, entity_type, entity_id, details FROM audit_logs "
        "WHERE action = 'data_alert.resolved'"
    )
    assert len(audits) == 1
    actor, entity_type, entity_id, details = audits[0]
    assert (actor, entity_type, entity_id) == ("system", "data_alert", alert_id)
    assert {k: details[k] for k in ("alert_id", "kind", "reason")} == {
        "alert_id": alert_id, "kind": "review_flagged_data_problem", "reason": "checked"
    }  # fmt: skip
    assert details["operator"]


@pytest.mark.req("TST-189", "TRD 15 §4.8", "FEAT-032-AC-05", "FEAT-032-FR-06")
def test_refusals_change_nothing(cli: Cli) -> None:
    world, session = _world(cli)
    silent = _data_alert(world, session, "device_silent")
    resolved = _data_alert(world, session, "review_flagged_data_problem", status="resolved")
    open_id = _data_alert(world, session, "review_flagged_data_problem")
    session.close()
    before = _state(cli)
    for alert_id in (silent, resolved, str(uuid.uuid4()), "not-a-uuid"):
        result = cli("resolve-data-alert", "--id", alert_id, "--reason", "x")
        assert result.code == 2, (alert_id, result.err)
        assert "Refused" in result.err
    assert cli("resolve-data-alert", "--id", open_id, "--reason", "  ").code == 2
    assert _state(cli) == before
    assert before[1] == 0
