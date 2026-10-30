"""CORS refuses unknown origins (TRD 13 TST-134; TRD 05 API-101; FEAT-039-FR-05,
FEAT-039-AC-05)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.security

ALLOWED = "http://localhost:3000"  # CORS_ORIGINS of the test settings
PATHS = ("/api/v1/health", "/api/v1/auth/login", "/api/v1/residents", "/api/v1/ingest")


@pytest.mark.req("TST-134", "API-101", "FEAT-039-FR-05", "FEAT-039-AC-05")
@pytest.mark.parametrize("path", PATHS)
def test_preflight(bare_client: TestClient, path: str) -> None:
    for method in ("GET", "POST"):
        preflight = {"Access-Control-Request-Method": method}
        evil = bare_client.options(path, headers={"Origin": "https://evil.example", **preflight})
        assert "access-control-allow-origin" not in evil.headers
        good = bare_client.options(path, headers={"Origin": ALLOWED, **preflight})
        assert good.headers["access-control-allow-origin"] == ALLOWED
    simple = bare_client.get(path, headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in simple.headers
