"""API-key attacks (TRD 13 TST-132; TRD 12 AC-SEC-04; FEAT-039-FR-03, FEAT-039-AC-03)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.repositories.api_key_repository import ApiKeyRepository
from tests.integration.api.conftest import Principals
from tests.integration.api.test_sessions import src05_record

pytestmark = pytest.mark.security

RECORD = src05_record("R09-20261021-01")
WRITES = (("/api/v1/sessions", RECORD), ("/api/v1/ingest", {"records": [RECORD]}))


def _problem(response: object, status: int, code: str) -> None:
    assert response.status_code == status, response.text  # type: ignore[attr-defined]
    assert response.json()["type"] == f"urn:echowell:error:{code}"  # type: ignore[attr-defined]


@pytest.mark.req("TST-132", "AC-SEC-04", "SEC-022", "FEAT-039-FR-03", "FEAT-039-AC-03")
def test_revoked_key_is_invalid(api: TestClient, roster: object, principals: Principals) -> None:
    ApiKeyRepository(principals.session).revoke(principals.keys["ingest"])
    principals.session.commit()
    for path, body in WRITES:
        _problem(api.post(path, json=body, headers=principals.api_key("ingest")), 401,
                 "API_KEY_INVALID")  # fmt: skip


@pytest.mark.req("TST-132", "AC-SEC-04", "SEC-024", "FEAT-039-FR-03", "FEAT-039-AC-03")
def test_key_without_ingest_scope_is_forbidden(
    api: TestClient, roster: object, principals: Principals
) -> None:
    _problem(api.post("/api/v1/ingest", json=WRITES[1][1], headers=principals.api_key("pipeline")),
             403, "FORBIDDEN")  # fmt: skip
    # `POST /sessions` accepts only `ingest:write` keys, so the pipeline key is not a credential.
    response = api.post("/api/v1/sessions", json=RECORD, headers=principals.api_key("pipeline"))
    assert response.status_code in (401, 403), response.text


@pytest.mark.req("TST-132", "SEC-026", "FEAT-039-FR-03")
def test_unknown_or_query_string_key_is_refused(
    api: TestClient, roster: object, principals: Principals
) -> None:
    _problem(api.post("/api/v1/sessions", json=RECORD, headers={"X-API-Key": "ewk_unknown"}), 401,
             "API_KEY_INVALID")  # fmt: skip
    _problem(api.post("/api/v1/sessions", json=RECORD,
                      params={"api_key": principals.raw_keys["ingest"]}), 401,
             "NOT_AUTHENTICATED")  # fmt: skip
