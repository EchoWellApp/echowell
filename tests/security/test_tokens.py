"""Token attacks (TRD 13 TST-132; TRD 12 AC-SEC-04; TRD 05 API-012, API-024; FEAT-039-FR-03,
FEAT-039-AC-03). Each forged or stale token is sent to a read, a write and the ingest endpoint."""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from fastapi.testclient import TestClient

from backend.core import security
from backend.repositories.user_repository import UserRepository
from tests.conftest import TEST_JWT_SECRET
from tests.integration.api.conftest import Principals

pytestmark = pytest.mark.security

CALLS = (("GET", "/api/v1/residents"), ("POST", "/api/v1/ingest"), ("GET", "/api/v1/users"))


def _alg_none(principals: Principals) -> str:
    def part(data: dict[str, Any]) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    claims = jwt.decode(
        principals.token("admin"), options={"verify_signature": False}, algorithms=["HS256"]
    )
    return f"{part({'alg': 'none', 'typ': 'JWT'})}.{part(claims)}."


def _refused(api: TestClient, token: str, code: str) -> None:
    for method, path in CALLS:
        response = api.request(method, path, headers={"Authorization": f"Bearer {token}"},
                               json={} if method == "POST" else None)  # fmt: skip
        assert response.status_code == 401, (path, response.text)
        assert response.json()["type"] == f"urn:echowell:error:{code}", path
        assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.req("TST-132", "AC-SEC-04", "API-024", "FEAT-039-FR-03", "FEAT-039-AC-03")
def test_token_61_minutes_old_is_expired(api: TestClient, principals: Principals) -> None:
    user = principals.users["admin"]
    issued = datetime.now(UTC) - timedelta(minutes=61)
    token = security.create_access_token(user.id, "admin", TEST_JWT_SECRET, 60, now=issued)
    _refused(api, token, "TOKEN_EXPIRED")


@pytest.mark.req("TST-132", "AC-SEC-04", "API-024", "FEAT-039-FR-03", "FEAT-039-AC-03")
def test_altered_and_unsigned_tokens_are_invalid(api: TestClient, principals: Principals) -> None:
    good = principals.token("admin")
    header, claims, signature = good.split(".")
    payload = json.loads(base64.urlsafe_b64decode(claims + "=" * (-len(claims) % 4)))
    forged = base64.urlsafe_b64encode(json.dumps({**payload, "role": "admin", "sub": "x"})
                                      .encode()).rstrip(b"=").decode()  # fmt: skip
    flipped = signature[:-2] + ("AA" if not signature.endswith("AA") else "BB")
    for token in (f"{header}.{claims}.{flipped}", f"{header}.{forged}.{signature}",
                  _alg_none(principals)):  # fmt: skip
        _refused(api, token, "TOKEN_INVALID")


@pytest.mark.req("TST-132", "API-012", "FEAT-039-FR-03")
def test_token_of_a_deactivated_user_is_invalid(api: TestClient, principals: Principals) -> None:
    token = principals.token("admin")
    UserRepository(principals.session).update(principals.users["admin"], active=False)
    principals.session.commit()
    _refused(api, token, "TOKEN_INVALID")
