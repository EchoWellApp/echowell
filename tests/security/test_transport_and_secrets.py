"""Transport security and secret handling at startup (TRD 21 AC-ENV-02, AC-ENV-03, AC-ENV-09,
ENV-004, ENV-011, ENV-041; TRD 12 SEC-050, SEC-061, SEC-062; TRD 15 DEP-034, DEP-045;
TRD 13 TST-135 (in-process part); FEAT-083-AC-01..AC-03, FEAT-081-FR-07).

The platform half of TST-135 and SEC-066 (HTTP redirected to HTTPS by the Render/Netlify edge,
TLS 1.1 refused, TLS 1.2 accepted) can only run against the deployed origins: those are the post-
deploy smoke tests (tests/smoke, FEAT-086)."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from backend.core.config import Settings, startup_violations
from backend.main import create_app
from tests.conftest import make_settings

pytestmark = pytest.mark.security

ROOT = Path(__file__).resolve().parents[2]
HSTS = "max-age=31536000; includeSubDomains"
PASSWORD = "Pw-transport-test-only-7f3a"  # noqa: S105 - test-only value
TLS_URL = f"postgresql+psycopg://app:{PASSWORD}@db.example.org/echowell?sslmode=require"
NO_TLS_URL = f"postgresql+psycopg://app:{PASSWORD}@db.example.org/echowell"
SECRET = "c4b1e2f3a4d5c6b7a8f9e0d1c2b3a4f5e6d7c8b9a0f1e2d3c4b5a6f7e8d9c0b1"  # noqa: S105


def dev_template_jwt_secret() -> str:
    match = re.search(r"^JWT_SECRET=(\S+)", (ROOT / ".env.development.example").read_text(), re.M)
    assert match is not None
    return match.group(1)


def deployed_env(app_env: str, **overrides: str) -> dict[str, str]:
    env = {
        "APP_ENV": app_env,
        "DATABASE_URL": TLS_URL,
        "JWT_SECRET": SECRET,
        "PIPELINE_PROFILE": "production",
        "CORS_ORIGINS": "https://echowell-und.netlify.app",
        "FACILITY_NAME": "Edgewood",
        "LOG_FORMAT": "json",
    }
    env.update(overrides)
    return env


def start_backend(env: dict[str, str], tmp_path: Path) -> subprocess.CompletedProcess[str]:
    """Build the app in a fresh process, as uvicorn would; cwd has no `.env` file."""
    clean = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "SYSTEMROOT")}
    return subprocess.run(  # noqa: S603 - fixed interpreter and arguments
        [sys.executable, "-c", "import backend.main as m; m.create_app(); print('started')"],
        cwd=tmp_path,
        env={**clean, "PYTHONPATH": str(ROOT), **env},
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


@pytest.mark.req("AC-ENV-02", "ENV-011", "SEC-061", "DEP-034", "FEAT-083-AC-01")
def test_staging_without_sslmode_exits_1_and_local_starts(tmp_path: Path) -> None:
    refused = start_backend(deployed_env("staging", DATABASE_URL=NO_TLS_URL), tmp_path)
    assert refused.returncode == 1
    assert "startup_config_invalid" in refused.stderr
    assert "DATABASE_URL" in refused.stderr
    assert PASSWORD not in refused.stdout + refused.stderr
    local = start_backend(
        {
            "APP_ENV": "local",
            "DATABASE_URL": NO_TLS_URL,
            "DATABASE_READONLY_URL": NO_TLS_URL,
            "JWT_SECRET": dev_template_jwt_secret(),
        },
        tmp_path,
    )
    assert local.returncode == 0, local.stderr
    assert "started" in local.stdout


@pytest.mark.req("AC-ENV-03", "ENV-041", "SEC-050", "FEAT-083-AC-02", "FEAT-083-FR-12")
def test_production_with_development_jwt_secret_exits_1_without_logging_it(
    tmp_path: Path,
) -> None:
    secret = dev_template_jwt_secret()
    result = start_backend(deployed_env("production", JWT_SECRET=secret), tmp_path)
    assert result.returncode == 1
    assert "startup_config_invalid" in result.stderr
    assert "JWT_SECRET" in result.stderr
    assert secret not in result.stdout + result.stderr


@pytest.mark.req("ENV-041", "FEAT-083-FR-12")
@pytest.mark.parametrize("app_env", ["staging", "production"])
@pytest.mark.parametrize("marker", ["local-dev-only", "ci-only"])
def test_placeholders_refused_for_web_and_operator_processes(app_env: str, marker: str) -> None:
    jwt = f"{marker}-0123456789abcdef0123456789abcdef"
    placeholder_url = TLS_URL.replace(PASSWORD, f"{marker}-app")
    for operator in (False, True):
        problems = {
            name
            for name, _ in startup_violations(
                make_settings(**_settings(app_env, jwt_secret=jwt)), operator=operator
            )
        }
        assert "JWT_SECRET" in problems
        for field in ("database_url", "database_migration_url", "database_readonly_url"):
            settings = make_settings(**_settings(app_env, **{field: placeholder_url}))
            assert field.upper() in {n for n, _ in startup_violations(settings, operator=operator)}
    assert startup_violations(make_settings(app_env="local", jwt_secret=jwt)) == []


def _settings(app_env: str, **overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "app_env": app_env,
        "database_url": TLS_URL,
        "database_readonly_url": None,
        "jwt_secret": SECRET,
        "pipeline_profile": "production",
        "cors_origins": "https://echowell-und.netlify.app",
        "facility_name": "Edgewood",
        "log_format": "json",
    }
    values.update(overrides)
    return values


@pytest.mark.req("ENV-011", "SEC-061", "DB-053", "FEAT-083-FR-11")
@pytest.mark.parametrize("app_env", ["staging", "production"])
@pytest.mark.parametrize(
    ("query", "accepted"),
    [
        ("sslmode=require", True),
        ("sslmode=verify-full", True),
        ("application_name=x&sslmode=require", True),
        ("sslmode=disable&sslmode=require", True),
        ("", False),
        ("sslmode=prefer", False),
        ("sslmode=disable", False),
        ("sslmode=requirex", False),
        ("sslmode=require&sslmode=disable", False),
        ("xsslmode=require", False),
    ],
)
def test_every_database_url_needs_sslmode_require(app_env: str, query: str, accepted: bool) -> None:
    url = NO_TLS_URL + (f"?{query}" if query else "")
    for field in ("database_url", "database_migration_url", "database_readonly_url"):
        problems = {
            n for n, _ in startup_violations(make_settings(**_settings(app_env, **{field: url})))
        }
        assert (field.upper() not in problems) is accepted, field


@pytest.mark.req("AC-ENV-09", "ENV-004", "FEAT-083-AC-03", "FEAT-083-FR-02")
def test_repr_masks_the_five_secret_settings() -> None:
    values = {
        "database_url": TLS_URL.replace(PASSWORD, "pw-main-11"),
        "database_migration_url": TLS_URL.replace(PASSWORD, "pw-migr-22"),
        "database_readonly_url": TLS_URL.replace(PASSWORD, "pw-read-33"),
        "jwt_secret": SECRET,
        "sentry_dsn": "https://dsnkey44@o0.ingest.us.sentry.io/0",
    }
    settings = make_settings(**values)
    for text in (repr(settings), str(settings)):
        for needle in ("pw-main-11", "pw-migr-22", "pw-read-33", SECRET, "dsnkey44", "db.example"):
            assert needle not in text
        for field in values:
            assert re.search(rf"{field}=SecretStr\('\*{{10}}'\)", text), field
    for field in values:
        assert Settings.model_fields[field].annotation in (SecretStr, SecretStr | None), field


def _app(app_env: str) -> TestClient:
    overrides: dict[str, object] = {"app_env": "test"}
    if app_env != "test":
        overrides = _settings(app_env, database_readonly_url=TLS_URL)
    # No `with`: the lifespan (database checks) is not needed for header behaviour.
    return TestClient(create_app(make_settings(**overrides)), raise_server_exceptions=False)


@pytest.mark.req("TST-135", "SEC-062", "DEP-045", "API-106", "FEAT-081-FR-07", "FEAT-083-FR-13")
@pytest.mark.parametrize("app_env", ["staging", "production"])
def test_backend_sends_hsts_in_staging_and_production(app_env: str) -> None:
    client = _app(app_env)
    for path in ("/api/v1/nowhere", "/api/v1/openapi.json"):
        response = client.get(path)
        assert response.headers["strict-transport-security"] == HSTS


@pytest.mark.req("SEC-065", "DEP-045")
def test_no_hsts_outside_deployed_environments() -> None:
    assert "strict-transport-security" not in _app("test").get("/api/v1/nowhere").headers
