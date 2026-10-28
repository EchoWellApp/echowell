"""Audit service without a database (TRD 12 §4.12; SEC-103, SEC-104, SEC-109; LOG-092; FEAT-015)."""

from __future__ import annotations

import logging
from typing import Any

import pytest

from backend.models import ActorType
from backend.services import audit_service
from backend.services.audit_service import AuditAction, AuditDetailsError

pytestmark = pytest.mark.unit


class FakeSession:
    """Records calls instead of sending SQL."""

    def __init__(self) -> None:
        self.calls: list[Any] = []

    def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(statement)

        class Result:
            def scalar_one(self) -> int:
                return 7

        return Result()


def _record(session: FakeSession, **overrides: Any) -> int:
    kwargs: dict[str, Any] = {
        "action": AuditAction.AUTH_LOGOUT,
        "actor_type": ActorType.USER,
        "actor_id": "u1",
        "entity_type": "user",
        "entity_id": "u1",
        "details": {},
    }
    kwargs.update(overrides)
    return audit_service.record(session, **kwargs)  # type: ignore[arg-type]


@pytest.mark.req("SEC-109", "FEAT-015-AC-02")
@pytest.mark.parametrize("action", ["login", "Auth.Login", "auth.login"])
def test_unknown_action_raises_before_sql(action: str) -> None:
    session = FakeSession()
    with pytest.raises(ValueError, match="unknown audit action"):
        _record(session, action=action)
    assert session.calls == []


@pytest.mark.req("SEC-109")
def test_vocabulary_has_24_actions() -> None:
    assert len(AuditAction) == 24
    assert set(audit_service.DETAIL_KEYS) == set(AuditAction)


@pytest.mark.req("SEC-104", "FEAT-015-AC-04")
@pytest.mark.parametrize(
    ("action", "details"),
    [
        (AuditAction.AUTH_LOGOUT, {"password": "x"}),
        (AuditAction.NOTE_CREATED, {"loudness_dbfs": -30.1}),
        (AuditAction.CONFIG_CHANGED, {"new": {"token": "x"}}),
        (AuditAction.CONFIG_CHANGED, {"new": "$argon2id$v=19$abc"}),
        (AuditAction.API_KEY_CREATED, {"name": "ewk_abcdef"}),
        (AuditAction.CONFIG_CHANGED, {"new": "eyJhbGciOiJIUzI1NiJ9.x.y"}),
    ],
)
def test_forbidden_details_raise_and_write_nothing(
    action: AuditAction, details: dict[str, Any]
) -> None:
    session = FakeSession()
    with pytest.raises(AuditDetailsError):
        _record(session, action=action, details=details)
    assert session.calls == []


@pytest.mark.req("SEC-103", "FEAT-015-AC-05")
def test_cli_rows_are_system_with_operator(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(audit_service, "cli_operator", lambda: "ops-user")
    monkeypatch.setattr(audit_service, "record", lambda _s, **kw: captured.update(kw) or 1)
    audit_service.record_cli(
        FakeSession(), action=AuditAction.API_KEY_REVOKED, entity_type="api_key",  # type: ignore[arg-type]
        entity_id="k", details={"name": "t1"},
    )  # fmt: skip
    assert captured["actor_type"] is ActorType.SYSTEM
    assert captured["actor_id"] is None
    assert captured["details"] == {"name": "t1", "operator": "ops-user"}


@pytest.mark.req("LOG-092", "FEAT-015-AC-06")
def test_one_info_record_without_details(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    assert _record(FakeSession(), details={}) == 7
    records = [r for r in caplog.records if r.getMessage() == "audit_event"]
    assert len(records) == 1
    record = records[0]
    assert record.levelno == logging.INFO
    assert (record.action, record.entity_type, record.entity_id) == ("auth.logout", "user", "u1")  # type: ignore[attr-defined]
    assert not hasattr(record, "details")


@pytest.mark.req("SEC-101", "D-87")
def test_record_committed_only_for_refused_requests() -> None:
    with pytest.raises(ValueError, match="only for"):
        audit_service.record_committed(object(), action=AuditAction.AUTH_LOGOUT)  # type: ignore[arg-type]
