"""Rate limits (TRD 05 API-098, API-102, API-103, API-112; TRD 12 SEC-090..SEC-093; FEAT-022)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.core import rate_limit
from tests.conftest import make_settings
from tests.integration.api.conftest import Principals
from tests.integration.api.test_sessions import src05_record

pytestmark = pytest.mark.integration

LOGIN = "/api/v1/auth/login"
WRONG = {"email": "Someone@Example.test", "password": "wrong-password-123"}


def _rate_limited(response: Any) -> None:
    assert response.status_code == 429, response.text
    assert response.json()["type"] == "urn:echowell:error:RATE_LIMITED"
    assert response.headers["content-type"].startswith("application/problem+json")
    assert 1 <= int(response.headers["retry-after"]) <= 60


@pytest.mark.req(
    "SEC-091", "SEC-093", "API-098", "TST-131", "FR-215", "AC-API-09",
    "FEAT-022-AC-01", "FEAT-022-AC-03", "FEAT-022-FR-02", "FEAT-022-FR-05", "FEAT-022-FR-06",
)  # fmt: skip
def test_sixth_login_in_a_minute_is_rate_limited(
    api: TestClient, audit_rows: list[dict[str, Any]]
) -> None:
    for _ in range(5):
        assert api.post(LOGIN, json=WRONG).status_code == 401
    _rate_limited(api.post(LOGIN, json=WRONG))
    limited = [r for r in audit_rows if r["details"]["reason"] == "rate_limited"]
    assert [r["details"] for r in limited] == [
        {"email": "someone@example.test", "reason": "rate_limited"}
    ]
    assert len(audit_rows) == 6


@pytest.mark.req("API-103", "FEAT-022-AC-05", "FEAT-022-FR-07")
def test_login_limit_keys_on_the_left_most_forwarded_address(api: TestClient) -> None:
    first = {"X-Forwarded-For": "203.0.113.5, 10.0.0.1"}
    for _ in range(5):
        assert api.post(LOGIN, json=WRONG, headers=first).status_code == 401
    _rate_limited(api.post(LOGIN, json=WRONG, headers={"X-Forwarded-For": "203.0.113.5"}))
    other = {"X-Forwarded-For": "198.51.100.7, 10.0.0.1"}
    assert api.post(LOGIN, json=WRONG, headers=other).status_code == 401


@pytest.mark.req("API-112", "FEAT-022-AC-04", "FEAT-022-FR-08")
def test_health_is_never_rate_limited(bare_client: TestClient) -> None:
    statuses = {bare_client.get("/api/v1/health").status_code for _ in range(1000)}
    assert statuses <= {200, 503}


@pytest.mark.req("SEC-092", "SEC-093", "API-102", "FEAT-022-FR-04", "FEAT-022-FR-05")
def test_other_endpoints_allow_300_a_minute_per_user(
    api: TestClient, principals: Principals, audit_rows: list[dict[str, Any]]
) -> None:
    admin, clinician = principals.bearer("admin"), principals.bearer("clinician")
    for _ in range(300):
        assert api.get("/api/v1/auth/me", headers=admin).status_code == 200
    _rate_limited(api.get("/api/v1/auth/me", headers=admin))
    assert api.get("/api/v1/auth/me", headers=clinician).status_code == 200
    assert audit_rows == []


@pytest.mark.req("SEC-090", "SEC-093", "ING-011", "TST-131", "FEAT-022-AC-02", "FEAT-022-AC-03",
                 "FEAT-022-FR-03")  # fmt: skip
def test_ingest_limit_is_per_api_key(
    api: TestClient,
    roster: Session,
    principals: Principals,
    audit_rows: list[dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert make_settings().rate_limit_ingest == "600/minute"
    # The same limit path with a small value, so the test sends 4 requests instead of 601.
    monkeypatch.setattr(
        rate_limit, "_current_settings", make_settings(rate_limit_ingest="3/minute")
    )
    record = {**src05_record("R09-20261021-01"), "schema_version": "9.9"}  # rejected: no pipeline
    ingest = principals.api_key("ingest")
    for _ in range(3):
        assert api.post("/api/v1/sessions", json=record, headers=ingest).status_code == 422
    _rate_limited(api.post("/api/v1/sessions", json=record, headers=ingest))
    _rate_limited(api.post("/api/v1/ingest", json={"records": [record]}, headers=ingest))
    other = principals.add_key("other", ["ingest:write"])
    assert (
        api.post("/api/v1/sessions", json=record, headers={"X-API-Key": other}).status_code == 422
    )
    assert audit_rows == []
