"""E-01 GET /api/v1/health against PostgreSQL 16 (TRD 13 TST-054, TRD 05 API-110..API-112)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from backend.api.deps import get_engine
from backend.core import db
from backend.core.config import SecretStr

pytestmark = pytest.mark.integration


@pytest.mark.req("TST-054", "API-110", "FR-253", "ENV-018")
def test_tst_054_health_ok_with_database_up(client: TestClient) -> None:
    response = client.get("/api/v1/health")  # no Authorization header (API-110)
    assert response.status_code == 200
    body = response.json()
    assert (body["status"], body["database"], body["version"]) == ("ok", "ok", "0123abc")
    assert set(body) == {"status", "database", "version", "time"}
    assert datetime.fromisoformat(body["time"]).tzinfo == UTC


@pytest.mark.req("TST-054", "API-111", "FR-253")
def test_tst_054_health_degraded_with_database_down(client: TestClient) -> None:
    down = SecretStr("postgresql+psycopg://nobody:x@127.0.0.1:1/none")
    client.app.dependency_overrides[get_engine] = lambda: db.create_engine_for(down, app_env="test")  # type: ignore[attr-defined]
    response = client.get("/api/v1/health")
    assert response.status_code == 503
    body = response.json()
    assert (body["status"], body["database"]) == ("degraded", "unavailable")
    assert set(body) == {"status", "database", "version", "time"}


@pytest.mark.req("API-002", "API-113")
def test_routes_only_under_api_v1(client: TestClient) -> None:
    paths = {route.path for route in client.app.routes}  # type: ignore[attr-defined]
    assert all(p.startswith("/api/v1/") for p in paths)
    assert client.get("/api/v1/openapi.json").status_code == 200
