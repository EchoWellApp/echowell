"""CORS with the deployed configuration of `/render.yaml` (TRD 13 TST-134; TRD 05 API-101;
TRD 21 §4.7 CORS_ORIGINS / CORS_ORIGIN_REGEX; TRD 15 DEP-051, DEP-054; FEAT-081, FEAT-082).

The staging API admits the staging site and its deploy previews only; the production API admits
the production site only. Values are read from render.yaml so Blueprint and guard cannot drift."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from backend.main import create_app
from tests.conftest import make_settings

pytestmark = pytest.mark.security

ROOT = Path(__file__).resolve().parents[2]
TLS_URL = "postgresql+psycopg://app:Pw-cors-test-only@db.example.org/echowell?sslmode=require"
SECRET = "0f1e2d3c4b5a69788796a5b4c3d2e1f00f1e2d3c4b5a69788796a5b4c3d2e1f0"  # noqa: S105
WEB = {"staging": "echowell-api", "production": "echowell-backend-production"}
STAGING_SITE = "https://echowell-und-staging.netlify.app"
PRODUCTION_SITE = "https://echowell-und.netlify.app"
ALLOWED = {
    "staging": [STAGING_SITE, "https://deploy-preview-42--echowell-und-staging.netlify.app"],
    "production": [PRODUCTION_SITE],
}
REFUSED = {
    "staging": [
        PRODUCTION_SITE,
        "https://deploy-preview-42--echowell-und.netlify.app",
        "https://deploy-preview-x--echowell-und-staging.netlify.app",
        "https://deploy-preview-42--echowell-und-staging.netlify.app.evil.example",
        "http://echowell-und-staging.netlify.app",
        "https://evil.example",
    ],
    "production": [
        STAGING_SITE,
        "https://deploy-preview-42--echowell-und-staging.netlify.app",
        "http://echowell-und.netlify.app",
        "https://evil.example",
    ],
}


def web_cors(env: str) -> dict[str, str]:
    services = yaml.safe_load((ROOT / "render.yaml").read_text())["services"]
    (web,) = (s for s in services if s["name"] == WEB[env])
    return {
        v["key"].lower(): v["value"]
        for v in web["envVars"]
        if v.get("key") in ("CORS_ORIGINS", "CORS_ORIGIN_REGEX")
    }


def client(env: str) -> TestClient:
    settings = make_settings(
        app_env=env,
        database_url=TLS_URL,
        database_readonly_url=TLS_URL if env == "staging" else None,
        jwt_secret=SECRET,
        pipeline_profile="test_v0_1" if env == "staging" else "production",
        facility_name="Edgewood",
        log_format="json",
        **web_cors(env),
    )
    # No `with`: CORS needs no database, so the lifespan checks are not run.
    return TestClient(create_app(settings), raise_server_exceptions=False)


def preflight(api: TestClient, origin: str) -> dict[str, str]:
    headers = {"Origin": origin, "Access-Control-Request-Method": "POST"}
    return dict(api.options("/api/v1/auth/login", headers=headers).headers)


@pytest.mark.req("TST-134", "API-101", "DEP-051", "DEP-054")
@pytest.mark.parametrize("env", ["staging", "production"])
def test_deployed_cors_admits_only_its_own_site(env: str) -> None:
    api = client(env)
    for origin in ALLOWED[env]:
        assert preflight(api, origin).get("access-control-allow-origin") == origin
    for origin in REFUSED[env]:
        assert "access-control-allow-origin" not in preflight(api, origin), origin
