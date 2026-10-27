"""Login, tokens, logout, the current user and API keys (TRD 05 §4.3; TRD 12 SEC-010..SEC-036;
FEAT-020)."""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.core import security
from backend.repositories.api_key_repository import ApiKeyRepository
from backend.repositories.user_repository import UserRepository
from backend.services import auth_service
from tests.conftest import TEST_JWT_SECRET
from tests.integration.api.conftest import PASSWORD, LogCapture, Principals

pytestmark = pytest.mark.integration

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
LOGOUT = "/api/v1/auth/logout"


def _problem(response: Any, status: int, code: str) -> dict[str, Any]:
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith("application/problem+json")
    body: dict[str, Any] = response.json()
    assert body["type"] == f"urn:echowell:error:{code}", body
    return body


def _audit(principals: Principals, action: str) -> list[dict[str, Any]]:
    rows = principals.session.execute(
        text("SELECT actor_type, actor_id, details FROM audit_logs WHERE action = :a ORDER BY id"),
        {"a": action},
    )
    return [dict(r._mapping) for r in rows]


def _failed_logins(principals: Principals, email: str, ages: list[timedelta]) -> None:
    for age in ages:
        principals.session.execute(
            text(
                "INSERT INTO audit_logs (occurred_at, actor_type, action, entity_type, details) "
                "VALUES (:at, 'system', 'auth.login.failed', 'user', "
                "jsonb_build_object('email', CAST(:e AS text), 'reason', 'invalid_credentials'))"
            ),
            {"at": datetime.now(UTC) - age, "e": email},
        )


@pytest.mark.req("API-020", "API-022", "SEC-030", "SEC-031", "FEAT-020-AC-01", "FEAT-020-FR-07")
def test_valid_login_returns_a_bearer_token(api: TestClient, principals: Principals) -> None:
    user = principals.users["clinician"]
    response = api.post(LOGIN, json={"email": user.email.upper(), "password": PASSWORD})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"  # noqa: S105 - the OAuth token type
    assert body["expires_in"] == 3600
    assert body["user"]["email"] == user.email
    assert body["user"]["role"] == "clinician"
    token = body["access_token"]
    assert jwt.get_unverified_header(token)["alg"] == "HS256"
    claims = jwt.decode(
        token, TEST_JWT_SECRET, algorithms=["HS256"], audience="echowell-dashboard",
        issuer="echowell-api",
    )  # fmt: skip
    assert set(claims) == {"sub", "role", "iat", "exp", "jti", "iss", "aud"}
    assert claims["sub"] == str(user.id)
    assert claims["exp"] - claims["iat"] == 3600
    principals.session.refresh(user)
    assert user.last_login_at is not None
    rows = _audit(principals, "auth.login.succeeded")
    assert [(r["actor_type"], r["actor_id"]) for r in rows] == [("user", str(user.id))]


@pytest.mark.req("SEC-013", "SEC-014", "API-021", "FEAT-020-AC-02", "FEAT-020-FR-05")
def test_failed_logins_are_indistinguishable(
    api: TestClient, principals: Principals, audit_rows: list[dict[str, Any]]
) -> None:
    inactive = principals.add_user("clinician", active=False)
    attempts = [
        {"email": "Nobody@Example.test", "password": PASSWORD},
        {"email": principals.users["admin"].email, "password": "wrong-password-123"},
        {"email": inactive.email, "password": PASSWORD},
    ]
    bodies = []
    for attempt in attempts:
        body = _problem(api.post(LOGIN, json=attempt), 401, "INVALID_CREDENTIALS")
        body.pop("request_id")
        bodies.append(body)
    assert bodies[0] == bodies[1] == bodies[2]
    assert [r["action"] for r in audit_rows] == ["auth.login.failed"] * 3
    assert {r["ip"] for r in audit_rows} == {None}  # the test client's peer is not an IP
    assert [r["details"] for r in audit_rows] == [
        {"email": "nobody@example.test", "reason": "invalid_credentials"},
        {"email": principals.users["admin"].email, "reason": "invalid_credentials"},
        {"email": inactive.email, "reason": "invalid_credentials"},
    ]
    assert _audit(principals, "auth.login.succeeded") == []


@pytest.mark.req("SEC-015", "FEAT-020-AC-03", "FEAT-020-FR-06")
def test_eleventh_attempt_after_ten_failures_is_locked(
    api: TestClient, principals: Principals, audit_rows: list[dict[str, Any]]
) -> None:
    email = principals.users["researcher"].email
    _failed_logins(principals, email, [timedelta(minutes=m) for m in range(10)])
    response = api.post(LOGIN, json={"email": email, "password": PASSWORD})
    _problem(response, 429, "ACCOUNT_TEMPORARILY_LOCKED")
    assert 0 < int(response.headers["retry-after"]) <= 15 * 60
    assert audit_rows[-1]["details"] == {"email": email, "reason": "locked"}


@pytest.mark.req("SEC-015")
def test_failures_older_than_fifteen_minutes_do_not_lock(
    api: TestClient, principals: Principals
) -> None:
    email = principals.users["researcher"].email
    _failed_logins(principals, email, [timedelta(minutes=16)] * 10)
    assert api.post(LOGIN, json={"email": email, "password": PASSWORD}).status_code == 200


def _none_token(principals: Principals) -> str:
    def part(data: dict[str, Any]) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    claims = jwt.decode(
        principals.token("admin"), options={"verify_signature": False}, algorithms=["HS256"]
    )
    return f"{part({'alg': 'none', 'typ': 'JWT'})}.{part(claims)}."


@pytest.mark.req("API-024", "SEC-030", "SEC-031", "SEC-035", "TST-132", "FEAT-020-AC-04")
@pytest.mark.parametrize(
    ("kind", "code"),
    [
        ("missing", "NOT_AUTHENTICATED"),
        ("expired", "TOKEN_EXPIRED"),
        ("altered", "TOKEN_INVALID"),
        ("alg-none", "TOKEN_INVALID"),
        ("other-secret", "TOKEN_INVALID"),
        ("wrong-audience", "TOKEN_INVALID"),
        ("wrong-issuer", "TOKEN_INVALID"),
        ("garbage", "TOKEN_INVALID"),
    ],
)
def test_bad_tokens_are_refused_with_a_bearer_challenge(
    api: TestClient, principals: Principals, kind: str, code: str
) -> None:
    user = principals.users["admin"]
    good = principals.token("admin")
    other = "another-secret-0123456789abcdefghijklmnopqrstuv"
    base = {"sub": str(user.id), "role": "admin", "jti": "x", "iat": datetime.now(UTC)}
    later = datetime.now(UTC) + timedelta(minutes=5)
    tokens = {
        "missing": None,
        "expired": security.create_access_token(
            user.id, "admin", TEST_JWT_SECRET, 60, now=datetime.now(UTC) - timedelta(minutes=121)
        ),
        "altered": good[:-4] + ("AAAA" if not good.endswith("AAAA") else "BBBB"),
        "alg-none": _none_token(principals),
        "other-secret": principals.token("admin", secret=other),
        "wrong-audience": jwt.encode(
            {**base, "exp": later, "iss": "echowell-api", "aud": "x"}, TEST_JWT_SECRET
        ),
        "wrong-issuer": jwt.encode(
            {**base, "exp": later, "iss": "x", "aud": "echowell-dashboard"}, TEST_JWT_SECRET
        ),
        "garbage": "not-a-jwt",
    }
    token = tokens[kind]
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = api.get(ME, headers=headers)
    _problem(response, 401, code)
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.req("SEC-034", "API-012", "FEAT-020-AC-05", "FEAT-020-FR-12")
def test_deactivated_user_token_stops_working(api: TestClient, principals: Principals) -> None:
    headers = principals.bearer("clinician")
    assert api.get(ME, headers=headers).status_code == 200
    UserRepository(principals.session).update(principals.users["clinician"], active=False)
    principals.session.commit()
    _problem(api.get(ME, headers=headers), 401, "TOKEN_INVALID")


@pytest.mark.req("API-023", "API-025", "SEC-036", "TST-069", "FEAT-020-AC-06")
def test_me_and_logout(api: TestClient, principals: Principals) -> None:
    user = principals.users["researcher"]
    headers = principals.bearer("researcher")
    me = api.get(ME, headers=headers)
    assert me.status_code == 200
    assert {k: me.json()[k] for k in ("id", "email", "display_name", "role", "active")} == {
        "id": str(user.id), "email": user.email, "display_name": user.display_name,
        "role": "researcher", "active": True,
    }  # fmt: skip
    response = api.post(LOGOUT, headers=headers)
    assert response.status_code == 204
    assert response.content == b""
    rows = _audit(principals, "auth.logout")
    assert [(r["actor_type"], r["actor_id"]) for r in rows] == [("user", str(user.id))]
    assert api.get(ME, headers=headers).status_code == 200  # not revoked server-side (SEC-036)


@pytest.mark.req("SEC-011", "FEAT-020-FR-08")
def test_login_rehashes_a_hash_with_old_parameters(api: TestClient, principals: Principals) -> None:
    user = principals.users["admin"]
    old = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1).hash(PASSWORD)
    UserRepository(principals.session).update(user, password_hash=old)
    principals.session.commit()
    assert api.post(LOGIN, json={"email": user.email, "password": PASSWORD}).status_code == 200
    principals.session.refresh(user)
    assert user.password_hash != old
    assert not security.needs_rehash(user.password_hash)


@pytest.mark.req("SEC-024", "SEC-026", "SEC-022", "TST-132", "FEAT-020-AC-07", "FEAT-020-FR-13")
def test_api_key_checks(api: TestClient, principals: Principals) -> None:
    route = "/api/v1/_test/ingest-key"
    assert api.post(route, headers=principals.api_key("ingest")).status_code == 200
    _problem(api.post(route, headers=principals.api_key("pipeline")), 403, "FORBIDDEN")
    _problem(api.post(route, params={"api_key": principals.raw_keys["ingest"]}), 401,
             "NOT_AUTHENTICATED")  # fmt: skip
    _problem(api.post(route, headers={"X-API-Key": "ewk_unknown"}), 401, "API_KEY_INVALID")
    ApiKeyRepository(principals.session).revoke(principals.keys["ingest"])
    principals.session.commit()
    _problem(api.post(route, headers=principals.api_key("ingest")), 401, "API_KEY_INVALID")


@pytest.mark.req("SEC-025", "FEAT-020-FR-16")
def test_last_used_at_is_written_at_most_once_a_minute(principals: Principals) -> None:
    raw, key = principals.raw_keys["ingest"], principals.keys["ingest"]
    start = datetime(2026, 10, 2, 13, 0, tzinfo=UTC)
    auth_service.authenticate_api_key(principals.session, raw, now=start)
    assert key.last_used_at == start
    auth_service.authenticate_api_key(principals.session, raw, now=start + timedelta(seconds=59))
    assert key.last_used_at == start
    auth_service.authenticate_api_key(principals.session, raw, now=start + timedelta(seconds=60))
    assert key.last_used_at == start + timedelta(seconds=60)


@pytest.mark.req("AC-LOG-02", "SEC-085", "FEAT-020-AC-08")
def test_logs_hold_no_password_token_or_email(
    api: TestClient, principals: Principals, log_capture: LogCapture
) -> None:
    user = principals.users["admin"]
    secret = "Secret-123!"  # noqa: S105 - the AC-08 probe value
    UserRepository(principals.session).update(user, password_hash=security.hash_password(secret))
    principals.session.commit()
    log_capture.start()
    login = api.post(LOGIN, json={"email": user.email, "password": secret})
    token = login.json()["access_token"]
    assert api.get(ME, headers={"Authorization": f"Bearer {token}"}).status_code == 200
    api.post(LOGIN, json={"email": user.email, "password": secret + "x"})
    logged = log_capture.text()
    assert "request_completed" in logged
    for value in (secret, token, user.email):
        assert value not in logged


@pytest.mark.req("API-103", "LOG-033")
def test_audit_ip_comes_from_a_valid_forwarded_address(
    api: TestClient, principals: Principals, audit_rows: list[dict[str, Any]]
) -> None:
    for forwarded in ("203.0.113.5, 10.0.0.1", "not-an-ip"):
        api.post(LOGIN, json={"email": "x@example.test", "password": "x"},
                 headers={"X-Forwarded-For": forwarded})  # fmt: skip
    assert [r["ip"] for r in audit_rows] == ["203.0.113.5", None]
