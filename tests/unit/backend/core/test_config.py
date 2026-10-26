"""Settings and startup guards (TRD 21 ENV-001..ENV-054, TRD 25 AGT-015, AC-AGT-05; FEAT-003)."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.core.config import (
    ensure_valid,
    load_settings_or_exit,
    normalise_database_url,
    startup_violations,
)
from tests.conftest import make_settings

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[4]
PROD_URL = "postgresql+psycopg://app:s3cret-pw@db.example.org/echowell?sslmode=require"
PROD_SECRET = "Zq8vN3xK1pL7wR4tY6uI0oP2aS5dF9gH"  # noqa: S105 - test-only value


def prod(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "app_env": "production",
        "database_url": PROD_URL,
        "database_readonly_url": None,
        "jwt_secret": PROD_SECRET,
        "pipeline_profile": "production",
        "cors_origins": "https://echowell-und.netlify.app",
        "facility_name": "Edgewood",
    }
    values.update(overrides)
    return values


def names(**overrides: object) -> set[str]:
    return {name for name, _ in startup_violations(make_settings(**prod(**overrides)))}


def run_backend(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Start the app factory in a fresh process, as uvicorn would (AC-AGT-05)."""
    clean = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "SYSTEMROOT")}
    return subprocess.run(  # noqa: S603 - fixed interpreter and arguments
        [sys.executable, "-c", "import backend.main as m; m.create_app()"],
        cwd=ROOT,
        env={**clean, **env},
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


@pytest.mark.req("AGT-015", "ENV-010", "ARC-056", "CFG-06")
def test_cfg_06_production_refuses_test_profile() -> None:
    assert names(pipeline_profile="test_v0_1", database_readonly_url=PROD_URL) == {
        "PIPELINE_PROFILE"
    }


@pytest.mark.req("AGT-015", "AC-AGT-05", "AC-ENV-01")
def test_cfg_06_process_exits_1_with_critical_log() -> None:
    env = {k.upper(): str(v) for k, v in prod(pipeline_profile="test_v0_1").items() if v}
    result = run_backend(env)
    assert result.returncode == 1
    assert "startup_config_invalid" in result.stderr
    assert "PIPELINE_PROFILE" in result.stderr
    assert PROD_SECRET not in result.stderr
    assert "s3cret-pw" not in result.stderr


@pytest.mark.req("AGT-015", "ENV-012", "TST-038", "AC-ENV-06", "AC-AGT-05")
def test_tst_038_production_refuses_pipeline_as_of() -> None:
    assert names(pipeline_as_of="2026-10-30T15:00:00-05:00") == {"PIPELINE_AS_OF"}
    env = {
        k.upper(): str(v) for k, v in prod(pipeline_as_of="2026-10-30T15:00:00-05:00").items() if v
    }
    assert run_backend(env).returncode == 1


@pytest.mark.req("ENV-012")
def test_production_refuses_unsafe_cors_and_console_logs() -> None:
    assert names(cors_origin_regex=r"^https://x\.netlify\.app$") == {"CORS_ORIGIN_REGEX"}
    assert names(log_format="console") == {"LOG_FORMAT"}
    assert names(cors_origins="http://echowell.example.org") == {"CORS_ORIGINS"}


@pytest.mark.req("ENV-012", "LOG-002", "D-103")
def test_staging_refuses_console_logs() -> None:
    assert names(app_env="staging", log_format="console") == {"LOG_FORMAT"}


@pytest.mark.req("ENV-011", "ARC-057", "AC-ENV-02", "AC-ARC-09")
def test_staging_requires_sslmode_but_local_does_not() -> None:
    no_tls = "postgresql+psycopg://app:pw-1@db.example.org/echowell"
    assert "DATABASE_URL" in names(app_env="staging", database_url=no_tls)
    assert "DATABASE_MIGRATION_URL" in names(database_migration_url=no_tls)
    local = make_settings(app_env="local", database_url=no_tls)
    assert startup_violations(local) == []


@pytest.mark.req("ENV-013", "AC-ENV-04")
@pytest.mark.parametrize("app_env", ["local", "test", "staging", "production"])
def test_short_jwt_secret_rejected_everywhere(app_env: str) -> None:
    with pytest.raises(ValidationError, match="jwt_secret"):
        make_settings(**prod(app_env=app_env, jwt_secret="x" * 31))


@pytest.mark.req("ENV-013", "ENV-041", "AC-ENV-03")
def test_deployed_refuses_template_and_placeholder_secrets() -> None:
    template = "local-dev-only-0123456789abcdef0123456789abcdef"
    assert names(jwt_secret=template) == {"JWT_SECRET"}
    assert names(jwt_secret="a" * 40) == {"JWT_SECRET"}
    placeholder_url = PROD_URL.replace("s3cret-pw", "ci-only-app")
    assert names(app_env="staging", database_url=placeholder_url) == {"DATABASE_URL"}


@pytest.mark.req("ENV-015", "AC-ENV-07", "AGT-019")
def test_forbidden_facility_name_rejected() -> None:
    forbidden = "Edge" + "4Care"  # split so the repo-hygiene forbidden-term scan stays clean
    for name in (forbidden, forbidden.upper() + " North", "Edge 4 Care"):
        with pytest.raises(ValidationError, match="facility_name"):
            make_settings(facility_name=name)


@pytest.mark.req("ENV-014", "AC-ENV-05")
def test_database_url_normalised_with_query_preserved() -> None:
    settings = make_settings(database_url="postgres://u:p@h/db?sslmode=require")
    expected = "postgresql+psycopg://u:p@h/db?sslmode=require"
    assert settings.database_url.get_secret_value() == expected
    assert normalise_database_url("postgresql://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    with pytest.raises(ValueError, match="scheme"):
        normalise_database_url("mysql://u:p@h/db")


@pytest.mark.req("ENV-004", "AC-ENV-09")
def test_secrets_masked_in_repr() -> None:
    settings = make_settings(
        database_url=PROD_URL,
        database_migration_url=PROD_URL,
        sentry_dsn="https://key@o0.ingest.us.sentry.io/0",
    )
    text = repr(settings)
    assert "s3cret-pw" not in text
    assert "test-only-jwt-secret" not in text
    assert "o0.ingest" not in text
    assert "**********" in text


@pytest.mark.req("ENV-054")
def test_login_rate_limit_fixed_in_deployed_environments() -> None:
    assert names(rate_limit_login="60/minute") == {"RATE_LIMIT_LOGIN"}
    assert startup_violations(make_settings(rate_limit_login="60/minute")) == []


@pytest.mark.req("ENV-003")
def test_unknown_echowell_variable_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ECHOWELL_APP_DB_PASWORD", "typo")
    with pytest.raises(SystemExit) as exc:
        ensure_valid(make_settings())
    assert exc.value.code == 1


@pytest.mark.req("ENV-006")
def test_dotenv_ignored_in_staging(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("FACILITY_NAME=FromDotenv\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("DATABASE_URL", PROD_URL)
    monkeypatch.delenv("FACILITY_NAME", raising=False)
    from backend.core.config import build_settings

    assert build_settings().facility_name == "Edgewood"
    monkeypatch.setenv("APP_ENV", "local")
    assert build_settings().facility_name == "FromDotenv"


@pytest.mark.req("ENV-053", "ENV-002")
def test_operator_commands_need_only_their_subset(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.chdir(ROOT / "tests")  # no .env here
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.setenv("PIPELINE_PROFILE", "test_v0_1")
    for var in ("JWT_SECRET", "CORS_ORIGINS", "DATABASE_READONLY_URL"):
        monkeypatch.delenv(var, raising=False)
    from backend.core.config import get_settings

    get_settings.cache_clear()
    try:
        assert load_settings_or_exit(operator=True).app_env == "test"
        with caplog.at_level(logging.CRITICAL), pytest.raises(SystemExit):
            load_settings_or_exit()
    finally:
        get_settings.cache_clear()
    assert "JWT_SECRET" in caplog.text
    assert "DATABASE_READONLY_URL" in caplog.text
