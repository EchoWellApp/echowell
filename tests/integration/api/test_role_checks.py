"""Server-side role matrix (TRD 12 §4.6 SEC-040, SEC-041, SEC-108; FEAT-021).

`test_permissions_equal_the_trd_matrix` compares `PERMISSIONS` with the matrix parsed from TRD 12.
`test_every_matrix_cell` calls every mounted route once per credential type (anonymous, each
role, an `ingest:write` key, a `pipeline:run` key) and asserts the allowed status or 401/403; it
covers each route as soon as its router is mounted.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from backend.api.permissions import PERMISSIONS, Access
from backend.core import security
from tests.conftest import TEST_JWT_SECRET
from tests.integration.api.conftest import Principals

pytestmark = pytest.mark.integration

TRD_DIR = Path(__file__).resolve().parents[3] / "specs" / "TRD"
CREDENTIALS = ("anonymous", "admin", "clinician", "researcher", "key:ingest", "key:pipeline")
SCOPE_OF = {"key:ingest": "ingest:write", "key:pipeline": "pipeline:run"}


def _matrix() -> dict[str, dict[str, str]]:
    text = next(TRD_DIR.glob("12_*.md")).read_text(encoding="utf-8")
    section = text[text.index("### 4.6 Authorisation") : text.index("| SEC-040 |")]
    rows: dict[str, dict[str, str]] = {}
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 6 or not re.match(r"^(GET|POST|PATCH) /", cells[0]):
            continue
        endpoint = cells[0]
        if "text/csv" in endpoint and "JSON or" not in endpoint:
            endpoint = endpoint.split(" (")[0] + " (text/csv)"
        else:
            endpoint = endpoint.split(" (")[0]
        rows[endpoint] = dict(zip(("anonymous", *CREDENTIALS[1:4], "key"), cells[1:], strict=True))
    return rows


@pytest.mark.req("SEC-040", "FR-213", "FEAT-021-AC-04", "FEAT-021-FR-02", "FEAT-021-FR-03")
def test_permissions_equal_the_trd_matrix() -> None:
    matrix = _matrix()
    assert set(matrix) == set(PERMISSIONS)
    for endpoint, cells in matrix.items():
        access = PERMISSIONS[endpoint]
        assert access.anonymous == (cells["anonymous"] == "Y"), endpoint
        if access.anonymous:
            continue
        roles = {role for role in CREDENTIALS[1:4] if cells[role] == "Y"}
        assert access.roles == roles, endpoint
        scope = re.search(r"`([a-z]+:[a-z]+)`", cells["key"])
        assert access.api_key_scope == (scope.group(1) if scope else None), endpoint


def _expected(access: Access, credential: str) -> int | None:
    """None when allowed, else the refusal status."""
    if access.anonymous:
        return None
    if credential in ("admin", "clinician", "researcher"):
        if not access.roles:
            return 401
        return None if credential in access.roles else 403
    if credential in SCOPE_OF:
        if access.api_key_scope is None:
            return 401
        return None if SCOPE_OF[credential] == access.api_key_scope else 403
    return 401


def _routes(api: TestClient) -> list[tuple[str, str, str]]:
    """(matrix key, method, concrete path) of every mounted route of the matrix."""
    found = []
    for route in api.app.routes:  # type: ignore[attr-defined]
        if not isinstance(route, APIRoute) or "/_test/" in route.path:
            continue
        path = route.path.removeprefix("/api/v1")
        concrete = route.path.replace("{id}", str(uuid.uuid4())).replace("{resident_code}", "R01")
        for method in sorted(route.methods):
            key = f"{method} {path}"
            assert key in PERMISSIONS, f"{key} is not in the TRD 12 §4.6 matrix"
            found.append((key, method, concrete))
            if key == "GET /scores":
                found.append(("GET /scores (text/csv)", method, concrete))
    return found


def _headers(principals: Principals, credential: str) -> dict[str, str]:
    if credential == "anonymous":
        return {}
    if credential.startswith("key:"):
        return principals.api_key(credential.removeprefix("key:"))
    return principals.bearer(credential)


@pytest.mark.req("SEC-041", "SEC-108", "FEAT-021-AC-03", "FEAT-021-FR-11", "FEAT-021-FR-02")
def test_every_matrix_cell(
    api: TestClient, principals: Principals, audit_rows: list[dict[str, Any]]
) -> None:
    routes = _routes(api)
    assert {key for key, _, _ in routes} >= {"GET /health", "POST /auth/login", "GET /auth/me"}
    for key, method, path in routes:
        access = PERMISSIONS[key]
        for credential in CREDENTIALS:
            if access.anonymous and credential != "anonymous":
                continue  # anonymous rows ignore credentials
            headers = _headers(principals, credential)
            if key.endswith("(text/csv)"):
                headers["Accept"] = "text/csv"
            audit_rows.clear()
            body = {} if method != "GET" else None
            response = api.request(method, path, headers=headers, json=body)
            expected = _expected(access, credential)
            cell = f"{key} as {credential}: {response.status_code} {response.text[:200]}"
            if expected is None:
                assert response.status_code not in (401, 403), cell
                continue
            assert response.status_code == expected, cell
            denied = [r for r in audit_rows if r["action"] == "access.denied"]
            if expected == 403:
                assert response.json()["type"] == "urn:echowell:error:FORBIDDEN", cell
                assert len(denied) == 1, cell
                assert denied[0]["details"] == {"status": 403, "code": "FORBIDDEN"}
            else:
                assert denied == [], cell


@pytest.mark.req("API-013", "SEC-034", "FEAT-021-AC-02", "FEAT-021-FR-01")
def test_role_comes_from_the_database_not_the_token(
    api: TestClient, principals: Principals, audit_rows: list[dict[str, Any]]
) -> None:
    researcher = principals.users["researcher"]
    claims_admin = security.create_access_token(researcher.id, "admin", TEST_JWT_SECRET, 60)
    headers = {"Authorization": f"Bearer {claims_admin}"}
    response = api.get("/api/v1/_test/admin-only", headers=headers)
    assert response.status_code == 403
    assert response.json()["type"] == "urn:echowell:error:FORBIDDEN"
    assert [r["actor_id"] for r in audit_rows] == [str(researcher.id)]
    assert (
        api.get("/api/v1/_test/admin-only", headers=principals.bearer("admin")).status_code == 200
    )
