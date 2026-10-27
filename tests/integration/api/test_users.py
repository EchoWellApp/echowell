"""User management (TRD 05 API-091, API-092; TRD 12 SEC-010..SEC-012, SEC-044; FEAT-037)."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from tests.integration.api.conftest import Principals

pytestmark = pytest.mark.integration

USERS = "/api/v1/users"
GOOD_PASSWORD = "Synthetic-Pw-14"  # noqa: S105 - test-only value, 15 characters


def _problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status, response.text
    assert response.json()["type"] == f"urn:echowell:error:{code}"


def _audits(session: Session, action: str) -> list[Any]:
    return list(
        session.execute(
            text("SELECT entity_id, details FROM audit_logs WHERE action = :a ORDER BY id"),
            {"a": action},
        ).all()
    )


@pytest.mark.req("API-091", "SEC-010", "PGS-034", "AC-SEC-05", "FR-220", "FEAT-037-AC-01",
                 "FEAT-037-FR-03", "FEAT-037-FR-08")  # fmt: skip
def test_create_user(api: TestClient, principals: Principals) -> None:
    response = api.post(USERS, headers=principals.bearer("admin"), json={
        "email": "New.Clinician@Example.TEST", "display_name": "New clinician",
        "role": "clinician", "password": GOOD_PASSWORD,
    })  # fmt: skip
    assert response.status_code == 201, response.text
    user = response.json()
    assert user["email"] == "new.clinician@example.test"
    assert (user["role"], user["active"], user["last_login_at"]) == ("clinician", True, None)
    assert "password_hash" not in response.text
    stored = principals.session.execute(
        text("SELECT password_hash FROM users WHERE id = :i"), {"i": user["id"]}
    ).scalar_one()
    assert stored.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    audits = _audits(principals.session, "user.created")
    assert [(a.entity_id, a.details) for a in audits] == [(user["id"], {"role": "clinician"})]


@pytest.mark.req("SEC-012", "AC-SEC-05", "FEAT-037-AC-02", "FEAT-037-FR-04")
@pytest.mark.parametrize("password", ["short", "password1234", "x" * 129, "staff@example.test"])
def test_password_policy(api: TestClient, principals: Principals, password: str) -> None:
    response = api.post(USERS, headers=principals.bearer("admin"), json={
        "email": "staff@example.test", "display_name": "Staff", "role": "researcher",
        "password": password,
    })  # fmt: skip
    _problem(response, 422, "PASSWORD_POLICY_VIOLATION")
    count = principals.session.execute(
        text("SELECT count(*) FROM users WHERE email = 'staff@example.test'")
    ).scalar_one()
    assert count == 0


@pytest.mark.req("API-091", "PGS-034", "FEAT-037-AC-03")
def test_duplicate_email(api: TestClient, principals: Principals) -> None:
    principals.add_user("clinician", email="clinician@example.com")
    response = api.post(USERS, headers=principals.bearer("admin"), json={
        "email": "Clinician@Example.com", "display_name": "Twin", "role": "clinician",
        "password": GOOD_PASSWORD,
    })  # fmt: skip
    _problem(response, 409, "EMAIL_ALREADY_EXISTS")


@pytest.mark.req("API-091", "API-092", "SEC-034", "FR-221", "FEAT-037-AC-04", "FEAT-037-FR-05",
                 "FEAT-037-FR-09")  # fmt: skip
def test_update_user(api: TestClient, principals: Principals) -> None:
    target = principals.users["clinician"]
    old_token = principals.bearer("clinician")
    response = api.patch(f"{USERS}/{target.id}", headers=principals.bearer("admin"),
                         json={"role": "researcher", "active": False})  # fmt: skip
    assert response.status_code == 200, response.text
    assert (response.json()["role"], response.json()["active"]) == ("researcher", False)
    audits = _audits(principals.session, "user.updated")
    assert [a.details for a in audits] == [{"changed": ["active", "role"]}]
    assert api.get("/api/v1/auth/me", headers=old_token).status_code == 401  # next request
    renamed = api.patch(f"{USERS}/{target.id}", headers=principals.bearer("admin"),
                        json={"display_name": "Renamed", "password": GOOD_PASSWORD})  # fmt: skip
    assert renamed.json()["display_name"] == "Renamed"
    details = _audits(principals.session, "user.updated")[-1].details
    assert details == {"changed": ["display_name", "password"]}
    assert GOOD_PASSWORD not in str(details)
    _problem(api.patch(f"{USERS}/{uuid.uuid4()}", headers=principals.bearer("admin"),
                       json={"display_name": "x"}), 404, "USER_NOT_FOUND")  # fmt: skip
    _problem(api.patch(f"{USERS}/{target.id}", headers=principals.bearer("admin"), json={}),
             422, "VALIDATION_ERROR")  # fmt: skip
    _problem(api.patch(f"{USERS}/{target.id}", headers=principals.bearer("admin"),
                       json={"password": "short"}), 422, "PASSWORD_POLICY_VIOLATION")  # fmt: skip


@pytest.mark.req("SEC-044", "FEAT-037-AC-05", "FEAT-037-FR-06")
def test_self_changes(api: TestClient, principals: Principals) -> None:
    me = principals.users["admin"]
    admin = principals.bearer("admin")
    for change in ({"role": "researcher"}, {"active": False}):
        _problem(api.patch(f"{USERS}/{me.id}", headers=admin, json=change), 403, "FORBIDDEN")
    ok = api.patch(f"{USERS}/{me.id}", headers=admin, json={"display_name": "Me", "role": "admin"})
    assert ok.status_code == 200


@pytest.mark.req("FR-221", "DME-005", "TRD 13 Table 4.13-A", "FEAT-037-AC-07", "FEAT-037-AC-08",
                 "FEAT-037-FR-01", "FEAT-037-FR-02")  # fmt: skip
def test_list_and_access(api: TestClient, principals: Principals) -> None:
    listed = api.get(USERS, headers=principals.bearer("admin"))
    assert listed.status_code == 200
    assert listed.json()["total"] == 3
    assert "password_hash" not in listed.text
    only = api.get(USERS, params={"role": "researcher"}, headers=principals.bearer("admin"))
    assert [u["role"] for u in only.json()["items"]] == ["researcher"]
    inactive = api.get(USERS, params={"active": "false"}, headers=principals.bearer("admin"))
    assert inactive.json()["total"] == 0
    first = listed.json()["items"][0]["id"]
    assert api.delete(f"{USERS}/{first}", headers=principals.bearer("admin")).status_code in (
        404, 405
    )  # fmt: skip
    for role in ("clinician", "researcher"):
        _problem(api.get(USERS, headers=principals.bearer(role)), 403, "FORBIDDEN")
    _problem(api.get(USERS, headers=principals.api_key("ingest")), 401, "NOT_AUTHENTICATED")
