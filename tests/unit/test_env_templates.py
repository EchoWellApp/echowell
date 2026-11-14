"""Environment templates, Compose file and backend Dockerfile against TRD 21 and TRD 15 (FEAT-077).

TRD 21 §4.6/§4.7 (ENV-040, ENV-041, ENV-050, SEC-054), AC-ENV-02, AC-ENV-03, AC-ENV-09;
TRD 15 DEP-011, DEP-017, DEP-018, DEP-021, DEP-022, AC-DEP-10; TRD 24 D-55. The verbatim TRD 21
comparison and the Settings-field check live in tests/unit/backend/core/test_env_templates.py; this
module checks the per-environment values and the guards they must satisfy.
"""

from __future__ import annotations

import re
import secrets
from pathlib import Path
from typing import Any

import pytest
import yaml

from backend.core.config import Settings, startup_violations
from tests.conftest import make_settings

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
LINE = re.compile(r"^(?P<key>[A-Z][A-Z0-9_]*)=(?P<value>.*?)(?:\s+#\s?(?P<comment>.*))?$")
DB_URLS = ("DATABASE_URL", "DATABASE_MIGRATION_URL", "DATABASE_READONLY_URL")
SEEDS = (
    "SEED_ADMIN_PASSWORD",
    "SEED_CLINICIAN_PASSWORD",
    "SEED_RESEARCHER_PASSWORD",
    "SEED_INGEST_API_KEY",
)
SECRETS = (*DB_URLS, "JWT_SECRET", "SENTRY_DSN", *SEEDS)
TEMPLATES = (".env.example", ".env.development.example", ".env.production.example")
PLACEHOLDER = "local-dev-only"


def entries(name: str) -> dict[str, tuple[str, str]]:
    """`KEY -> (value, inline comment)` of the assignments in a template (comment lines skipped)."""
    found: dict[str, tuple[str, str]] = {}
    for line in (ROOT / name).read_text().splitlines():
        match = LINE.match(line.strip())
        if match:
            found[match["key"]] = (match["value"].strip(), (match["comment"] or "").strip())
    return found


def values(name: str) -> dict[str, str]:
    return {key: value for key, (value, _) in entries(name).items()}


def mentioned(name: str) -> set[str]:
    """Every variable name assigned or listed in a comment line (the SEED_* checklist line)."""
    return set(re.findall(r"\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)\b", (ROOT / name).read_text()))


def settings_from(template: dict[str, str], **overrides: Any) -> Settings:
    fields = set(Settings.model_fields)
    kwargs: dict[str, Any] = {
        k.lower(): v for k, v in template.items() if k.lower() in fields and v
    }
    kwargs.update(overrides)
    return make_settings(**kwargs)


def deployed_secrets() -> dict[str, str | None]:
    """Stand-ins for the platform-store values (never committed): TLS URLs, a random JWT secret."""
    host = "db.example.org/echowell?sslmode=require"
    return {
        "database_url": f"postgresql+psycopg://app:{secrets.token_hex(8)}@{host}",
        "database_migration_url": f"postgresql+psycopg://mig:{secrets.token_hex(8)}@{host}",
        "database_readonly_url": None,  # not set in production (SEC-116)
        # 16 distinct characters guaranteed: the config's low-entropy rule (len(set(jwt)) < 16) also
        # refuses about one in four `openssl rand -hex 32` values (reported, backend/core/config.py)
        "jwt_secret": "0123456789abcdef" + secrets.token_hex(24),
        "cors_origins": "https://echowell-und.netlify.app",
    }


# --- .env.production.example (TRD 21 §4.6, §4.7 production column; FEAT-077-FR-12, AC-07) ---


@pytest.mark.req("ENV-050", "AGT-015")
def test_production_template_profile_and_as_of() -> None:
    prod = values(".env.production.example")
    assert prod["APP_ENV"] == "production"
    assert prod["PIPELINE_PROFILE"] == "production"
    assert "PIPELINE_AS_OF" in prod
    assert prod["PIPELINE_AS_OF"] == ""


@pytest.mark.req("ENV-040", "SEC-051")
def test_production_template_has_no_secret_value() -> None:
    prod = values(".env.production.example")
    for key in (*DB_URLS, "JWT_SECRET", "SENTRY_DSN"):
        assert prod[key] == "", key
    for key in SEEDS:  # listed in a comment as never set; production refuses them
        assert key not in prod
        assert key in mentioned(".env.production.example")


@pytest.mark.req("ENV-050", "SEC-116")
def test_production_template_requires_sslmode_and_no_readonly_url() -> None:
    prod = entries(".env.production.example")
    for key in DB_URLS:
        assert "sslmode=require" in prod[key][1], key
    assert "empty in production" in prod["DATABASE_READONLY_URL"][1]


@pytest.mark.req("ENV-050")
def test_production_template_matches_matrix() -> None:
    prod = values(".env.production.example")
    assert prod["LOG_FORMAT"] == "json"
    assert prod["RATE_LIMIT_LOGIN"] == "5/minute"
    assert prod["CORS_ORIGIN_REGEX"] == ""
    assert prod["DATA_SOURCE_LABEL"] == "demo data (synthetic)"
    assert prod["NEXT_PUBLIC_APP_ENV"] == "production"
    assert not any(PLACEHOLDER in v for v in prod.values())


@pytest.mark.req("ENV-050", "AC-ENV-02")
def test_production_template_values_pass_the_startup_guards() -> None:
    settings = settings_from(values(".env.production.example"), **deployed_secrets())
    assert startup_violations(settings) == []


@pytest.mark.req("AC-ENV-02")
@pytest.mark.parametrize("key", ["database_url", "database_migration_url"])
def test_ac_env_02_production_url_without_sslmode_refused(key: str) -> None:
    urls = deployed_secrets()
    urls[key] = str(urls[key]).replace("?sslmode=require", "")
    settings = settings_from(values(".env.production.example"), **urls)
    assert (key.upper(), "must specify sslmode=require or verify-full") in startup_violations(
        settings
    )


@pytest.mark.req("AC-ENV-03", "ENV-041")
def test_ac_env_03_development_jwt_refused_in_production() -> None:
    dev_jwt = values(".env.development.example")["JWT_SECRET"]
    overrides = deployed_secrets() | {"jwt_secret": dev_jwt}
    problems = startup_violations(settings_from(values(".env.production.example"), **overrides))
    assert "JWT_SECRET" in {name for name, _ in problems}
    assert dev_jwt not in repr(problems)


# --- .env.development.example (TRD 21 §4.7 local column; ENV-041) ---


@pytest.mark.req("ENV-050")
def test_development_template_matches_local_column() -> None:
    dev = values(".env.development.example")
    assert dev["APP_ENV"] == "local"
    assert dev["PIPELINE_PROFILE"] == "test_v0_1"
    assert dev["PIPELINE_AS_OF"] == "2026-10-30T15:00:00-05:00"
    assert dev["CORS_ORIGINS"] == "http://localhost:3000,http://localhost:3001"
    assert dev["LOG_FORMAT"] == "console"
    assert dev["RATE_LIMIT_LOGIN"] == "5/minute"
    assert dev["NEXT_PUBLIC_API_BASE_URL"] == "http://localhost:8000"
    assert dev["NEXT_PUBLIC_APP_ENV"] == "local"


@pytest.mark.req("ENV-041", "DEP-018")
def test_development_secrets_are_local_dev_only_placeholders() -> None:
    dev = values(".env.development.example")
    for key in (*DB_URLS, "JWT_SECRET", *SEEDS):
        assert PLACEHOLDER in dev[key], key
    assert dev["SENTRY_DSN"] == ""


@pytest.mark.req("AC-ENV-02")
def test_ac_env_02_local_template_starts_without_sslmode() -> None:
    settings = settings_from(values(".env.development.example"))
    assert startup_violations(settings) == []


@pytest.mark.req("AC-ENV-09")
def test_ac_env_09_template_secrets_masked_in_repr() -> None:
    dev = values(".env.development.example")
    text = repr(settings_from(dev, sentry_dsn="https://key@o1.ingest.example.org/1"))
    assert "**********" in text
    for secret in ("local-dev-only-app", "local-dev-only-migrator", "local-dev-only-readonly"):
        assert secret not in text
    assert dev["JWT_SECRET"] not in text
    assert "o1.ingest.example.org" not in text


# --- all templates ---


@pytest.mark.req("ENV-040", "SEC-051")
def test_env_example_secrets_empty_and_commented() -> None:
    example = entries(".env.example")
    for key in SECRETS:
        assert example[key][0] == "", key
    uncommented = {key for key, (_, comment) in example.items() if not comment}
    # the two role passwords share the comment of ECHOWELL_MIGRATOR_DB_PASSWORD on the line above
    assert uncommented <= {"ECHOWELL_APP_DB_PASSWORD", "ECHOWELL_READONLY_DB_PASSWORD"}


@pytest.mark.req("ENV-040")
@pytest.mark.parametrize("template", TEMPLATES[1:])
def test_every_template_key_is_in_env_example(template: str) -> None:
    assert set(values(template)) - set(values(".env.example")) == set()


@pytest.mark.req("ENV-031", "SEC-054")
@pytest.mark.parametrize("template", TEMPLATES)
def test_no_next_public_variable_holds_a_secret(template: str) -> None:
    public = {k: v for k, v in values(template).items() if k.startswith("NEXT_PUBLIC_")}
    assert set(public) <= {"NEXT_PUBLIC_API_BASE_URL", "NEXT_PUBLIC_APP_ENV"}
    assert public.get("NEXT_PUBLIC_APP_ENV", "") in {"", "local", "staging", "production"}
    url = public.get("NEXT_PUBLIC_API_BASE_URL", "")
    assert url == "" or re.fullmatch(r"https?://[A-Za-z0-9.-]+(:\d+)?", url), url


# --- docker-compose.yml and the Dockerfiles (TRD 15 §4.2, DEP-011, DEP-017, DEP-018, DEP-022) ---


def compose() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    return data


@pytest.mark.req("D-55", "DEP-010", "DEP-017")
def test_compose_services_and_no_version_key() -> None:
    data = compose()
    assert "version" not in data
    assert set(data["services"]) == {"db", "backend", "frontend", "frontend-prod"}
    prod = data["services"]["frontend-prod"]
    assert prod["profiles"] == ["demo"]
    assert prod["ports"] == ["127.0.0.1:3001:3000"]
    assert prod["build"]["args"] == {
        "NEXT_PUBLIC_API_BASE_URL": "http://localhost:8000",
        "NEXT_PUBLIC_APP_ENV": "local",
    }
    assert set(data["volumes"]) == {"pgdata", "frontend_node_modules"}


@pytest.mark.req("DEP-011", "DEP-012", "DEP-119")
def test_compose_db_and_backend_wiring() -> None:
    services = compose()["services"]
    db, backend = services["db"], services["backend"]
    assert db["image"] == "postgres:16-alpine"
    assert db["ports"] == ["127.0.0.1:5432:5432"]
    assert db["healthcheck"]["test"] == ["CMD-SHELL", "pg_isready -U echowell -d echowell"]
    assert (db["healthcheck"]["interval"], db["healthcheck"]["retries"]) == ("5s", 10)
    assert any("provision_login_roles.sql:/docker-entrypoint-initdb.d/" in v for v in db["volumes"])
    assert backend["depends_on"] == {"db": {"condition": "service_healthy"}}
    assert backend["command"].startswith('sh -c "alembic upgrade head && uvicorn ')
    assert "./database:/app/database:ro" in backend["volumes"]
    assert "./tests/fixtures:/app/tests/fixtures:ro" in backend["volumes"]
    for name in ("backend", "frontend-prod"):  # `docker compose up --wait` (TRD 16 §8)
        assert "healthcheck" in services[name], name
    assert "/api/v1/health" in str(backend["healthcheck"]["test"])
    assert "/login" in str(services["frontend-prod"]["healthcheck"]["test"])


@pytest.mark.req("DEP-018", "ENV-041")
def test_compose_urls_match_development_template_and_hold_placeholders_only() -> None:
    data = compose()
    backend_env = data["services"]["backend"]["environment"]
    dev = values(".env.development.example")
    for key in DB_URLS:
        assert backend_env[key] == dev[key], key
    for key, value in data["services"]["db"]["environment"].items():
        if "PASSWORD" in key:
            assert str(value).startswith(f"{PLACEHOLDER}-"), key


@pytest.mark.req("AC-DEP-10", "DEP-018")
@pytest.mark.parametrize(
    "path", ["docker-compose.yml", "backend/Dockerfile", "frontend/Dockerfile"]
)
def test_no_hosted_database_or_secret_in_container_files(path: str) -> None:
    text = (ROOT / path).read_text()
    assert "neon.tech" not in text
    assert "sslmode=require" not in text
    hosted = r"(secrets\.|STAGING_|PRODUCTION_|RENDER_API_KEY|NETLIFY_AUTH_TOKEN)"
    assert not re.search(hosted, text)


@pytest.mark.req("DEP-021", "DEP-022")
def test_backend_dockerfile_user_and_command() -> None:
    text = (ROOT / "backend/Dockerfile").read_text()
    assert re.search(r"^FROM python:3\.12-slim$", text, flags=re.MULTILINE)
    assert re.search(r"^USER 10001(:10001)?$", text, flags=re.MULTILINE)
    assert "PYTHONPATH=/app" in text
    cmd = re.findall(r"^CMD (.*)$", text, flags=re.MULTILINE)
    assert cmd == [
        '["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} '
        "--proxy-headers --forwarded-allow-ips='*'\"]"
    ]
    assert "alembic" not in cmd[0]


@pytest.mark.req("DEP-021")
def test_dockerignore_excludes_secrets_tests_specs_frontend() -> None:
    lines = set((ROOT / ".dockerignore").read_text().splitlines())
    assert {".env", ".env.*", "tests", "specs", "frontend", "docs", ".git"} <= lines
