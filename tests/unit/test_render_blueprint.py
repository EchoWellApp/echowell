"""Render Blueprint `/render.yaml` (TRD 15 §4.5 outline, DEP-040..DEP-048, DEP-033, DEP-044;
TRD 21 §4.7; TRD 12 SEC-111, SEC-116; TRD 24 D-153..D-158; FEAT-081) and the DATABASE_MIGRATION_URL
import boundary (DEP-040, FEAT-081-AC-03).

The Blueprint cannot be validated against Render here (no deployment, TRD 25 §4.6 Phase 9); the
Render dashboard Blueprint preview is the final check in Phase 10 (FEAT-088)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from backend.core.config import startup_violations
from tests.conftest import make_settings

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
BLUEPRINT = ROOT / "render.yaml"
TRD15 = ROOT / "specs" / "TRD" / "15_Deployment_and_DevOps_Spec.md"

ENVS = ("staging", "production")
WEB = {"staging": "echowell-api", "production": "echowell-backend-production"}
CRON = {"staging": "echowell-nightly-staging", "production": "echowell-nightly-production"}
GROUP = {"staging": "echowell-staging-shared", "production": "echowell-production-shared"}
TRIGGER = {"staging": "checksPass", "production": "off"}
SECRETS = {
    "DATABASE_URL",
    "DATABASE_MIGRATION_URL",
    "DATABASE_READONLY_URL",
    "JWT_SECRET",
    "SENTRY_DSN",
}
# DEP-046 / FEAT-081-FR-08: the only variables a cron job may see (via its environment group).
CRON_ALLOW = {
    "DATABASE_URL",
    "APP_ENV",
    "PIPELINE_PROFILE",
    "PIPELINE_AS_OF",
    "FACILITY_NAME",
    "FACILITY_TZ",
    "NIGHTLY_RUN_HOUR_LOCAL",
    "LOG_LEVEL",
    "LOG_FORMAT",
    "SENTRY_DSN",
}
WEB_COMMAND = (
    'sh -c \'export GIT_SHA="${RENDER_GIT_COMMIT:-unknown}"; exec uvicorn backend.main:app '
    '--host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips="*"\''
)
CRON_COMMAND = (
    'sh -c \'export GIT_SHA="${RENDER_GIT_COMMIT:-unknown}"; '
    "exec python -m backend.jobs.nightly_run'"
)
BUILD_PATHS = ["backend/**", "analytics/**", "database/**", "alembic.ini"]
COMMON = {
    "runtime": "docker",
    "repo": "https://github.com/EchoWellApp/echowell",
    "branch": "main",
    "region": "ohio",
    "plan": "starter",
    "dockerfilePath": "./backend/Dockerfile",
    "dockerContext": ".",
}
# TRD 21 §4.7 matrix values (non-secret).
MATRIX: dict[str, dict[str, str]] = {
    "staging": {
        "APP_ENV": "staging",
        "PIPELINE_PROFILE": "test_v0_1",
        "PIPELINE_AS_OF": "2026-10-30T15:00:00-05:00",
        "FACILITY_NAME": "Edgewood",
        "FACILITY_TZ": "America/Chicago",
        "NIGHTLY_RUN_HOUR_LOCAL": "2",
        "LOG_LEVEL": "INFO",
        "LOG_FORMAT": "json",
        "JWT_EXPIRES_MINUTES": "60",
        "CORS_ORIGINS": "https://echowell-und-staging.netlify.app",
        "CORS_ORIGIN_REGEX": r"^https://deploy-preview-\d+--echowell-und-staging\.netlify\.app$",
        "RATE_LIMIT_LOGIN": "5/minute",
        "RATE_LIMIT_INGEST": "600/minute",
        "DATA_SOURCE_LABEL": "pipeline test data v0.1",
    },
    "production": {
        "APP_ENV": "production",
        "PIPELINE_PROFILE": "production",
        "FACILITY_NAME": "Edgewood",
        "FACILITY_TZ": "America/Chicago",
        "NIGHTLY_RUN_HOUR_LOCAL": "2",
        "LOG_LEVEL": "INFO",
        "LOG_FORMAT": "json",
        "JWT_EXPIRES_MINUTES": "60",
        "CORS_ORIGINS": "https://echowell-und.netlify.app",
        "RATE_LIMIT_LOGIN": "5/minute",
        "RATE_LIMIT_INGEST": "600/minute",
        "DATA_SOURCE_LABEL": "demo data (synthetic)",
    },
}
SECRET_KEYS: dict[str, set[str]] = {
    "staging": SECRETS,
    "production": SECRETS - {"DATABASE_READONLY_URL"},
}


def blueprint() -> dict[str, Any]:
    data = yaml.safe_load(BLUEPRINT.read_text())
    assert isinstance(data, dict)
    return data


def service(name: str) -> dict[str, Any]:
    matches = [s for s in blueprint()["services"] if s["name"] == name]
    assert len(matches) == 1, name
    return matches[0]


def group(name: str) -> list[dict[str, Any]]:
    matches = [g for g in blueprint()["envVarGroups"] if g["name"] == name]
    assert len(matches) == 1, name
    return list(matches[0]["envVars"])


def own_vars(svc: dict[str, Any]) -> list[dict[str, Any]]:
    return [v for v in svc.get("envVars", []) if "fromGroup" not in v]


def effective_vars(env: str, svc: dict[str, Any]) -> list[dict[str, Any]]:
    groups = [v["fromGroup"] for v in svc.get("envVars", []) if "fromGroup" in v]
    assert groups == [GROUP[env]]
    return group(GROUP[env]) + own_vars(svc)


def trd_outline() -> dict[str, Any]:
    text = TRD15.read_text()
    start = text.index("`render.yaml` outline")
    block = re.search(r"```yaml\n(.*?)```", text[start:], re.DOTALL)
    assert block is not None
    data = yaml.safe_load(block.group(1))
    assert isinstance(data, dict)
    return data


@pytest.mark.req("DEP-044", "FEAT-081-FR-06")
def test_four_services_and_two_groups() -> None:
    data = blueprint()
    assert set(data) == {"envVarGroups", "services"}
    assert {g["name"] for g in data["envVarGroups"]} == set(GROUP.values())
    kinds = {(s["type"], s["name"]) for s in data["services"]}
    assert kinds == {("web", n) for n in WEB.values()} | {("cron", n) for n in CRON.values()}


@pytest.mark.req("DEP-044", "D-153", "D-154", "D-156")
def test_staging_matches_trd15_outline_field_by_field() -> None:
    """Every field of the TRD 15 §4.5 outline (staging) appears unchanged in render.yaml."""
    outline = trd_outline()
    assert outline["envVarGroups"] == [
        {"name": GROUP["staging"], "envVars": group(GROUP["staging"])}
    ]
    for expected in outline["services"]:
        actual = service(expected["name"])
        for field, value in expected.items():
            if field == "envVars":
                assert all(v in actual["envVars"] for v in value), expected["name"]
            else:
                assert actual[field] == value, (expected["name"], field)


@pytest.mark.req("DEP-040", "DEP-041", "DEP-042", "DEP-043", "FEAT-081-AC-01")
@pytest.mark.parametrize("env", ENVS)
def test_web_service(env: str) -> None:
    web = service(WEB[env])
    assert web["type"] == "web"
    assert {k: web[k] for k in COMMON} == COMMON
    assert web["plan"] != "free"
    assert web["numInstances"] == 1
    assert "autoscaling" not in web
    assert web["autoDeployTrigger"] == TRIGGER[env]
    assert web["preDeployCommand"] == "alembic upgrade head"
    assert web["dockerCommand"] == WEB_COMMAND
    assert "alembic" not in web["dockerCommand"]
    assert web["healthCheckPath"] == "/api/v1/health"
    assert web["buildFilter"] == {"paths": BUILD_PATHS}


@pytest.mark.req("DEP-046", "DEP-048", "SEC-111", "FEAT-081-AC-02", "FEAT-081-FR-08")
@pytest.mark.parametrize("env", ENVS)
def test_cron_job(env: str) -> None:
    cron = service(CRON[env])
    assert cron["type"] == "cron"
    assert {k: cron[k] for k in COMMON} == COMMON
    assert cron["schedule"] == "0 7,8 * * *"
    assert cron["dockerCommand"] == CRON_COMMAND
    assert cron["autoDeployTrigger"] == service(WEB[env])["autoDeployTrigger"]
    assert cron["buildFilter"] == {"paths": BUILD_PATHS}
    for absent in ("preDeployCommand", "healthCheckPath", "numInstances", "domains"):
        assert absent not in cron
    assert "alembic" not in cron["dockerCommand"]
    assert "alembic upgrade" not in yaml.safe_dump(cron)
    assert cron["envVars"] == [{"fromGroup": GROUP[env]}]
    assert {v["key"] for v in group(GROUP[env])} <= CRON_ALLOW


@pytest.mark.req("DEP-040", "SEC-111", "SEC-116", "FEAT-081-FR-02", "FEAT-081-FR-12")
def test_migration_and_readonly_urls_only_on_the_right_web_service() -> None:
    for env in ENVS:
        assert "DATABASE_MIGRATION_URL" not in {v["key"] for v in group(GROUP[env])}
        assert "DATABASE_MIGRATION_URL" in {v["key"] for v in own_vars(service(WEB[env]))}
    readonly = {
        svc["name"]
        for svc in blueprint()["services"]
        for v in own_vars(svc)
        if v["key"] == "DATABASE_READONLY_URL"
    }
    assert readonly == {WEB["staging"]}
    assert "PIPELINE_AS_OF" not in {v["key"] for v in group(GROUP["production"])}
    assert "CORS_ORIGIN_REGEX" not in {v["key"] for v in own_vars(service(WEB["production"]))}


@pytest.mark.req("ENV-050", "DEP-033", "ENV-005", "FEAT-081-AC-06", "AC-DEP-10")
@pytest.mark.parametrize("env", ENVS)
def test_variables_follow_the_trd21_matrix_and_secrets_are_sync_false(env: str) -> None:
    variables = effective_vars(env, service(WEB[env]))
    keys = [v["key"] for v in variables]
    assert len(keys) == len(set(keys)), "duplicate key"
    assert "GIT_SHA" not in keys  # from RENDER_GIT_COMMIT / injected
    assert "PORT" not in keys
    secrets = {v["key"]: v for v in variables if v["key"] in SECRETS}
    assert set(secrets) == SECRET_KEYS[env]
    assert all(v == {"key": k, "sync": False} for k, v in secrets.items())
    plain = {v["key"]: v["value"] for v in variables if v["key"] not in SECRETS}
    assert plain == MATRIX[env]
    assert all(isinstance(value, str) for value in plain.values())


@pytest.mark.req("AC-DEP-10", "FEAT-081-AC-06", "SEC-050")
def test_no_hostnames_or_credentials_in_blueprint() -> None:
    text = BLUEPRINT.read_text()
    assert "neon.tech" not in text
    assert not re.search(r"[a-z+]+://[^\s/'\"]*:[^\s/'\"]*@", text)  # user:password@ in a URL
    assert "local-dev-only" not in text
    assert "ci-only" not in text


@pytest.mark.req("ENV-041", "ENV-053", "SEC-111", "DEP-046")
@pytest.mark.parametrize("env", ENVS)
def test_blueprint_values_pass_startup_validation(env: str) -> None:
    """With sslmode=require URLs and a generated secret in place of the `sync: false` entries, the
    web service's variables pass the web guards and the cron job's pass the operator guards."""
    url = "postgresql+psycopg://app:Pw0rd-example-only@db.example.org/echowell?sslmode=require"
    fills = {
        "DATABASE_URL": url,
        "DATABASE_MIGRATION_URL": url,
        "DATABASE_READONLY_URL": url,
        "JWT_SECRET": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        "SENTRY_DSN": "",
    }

    def settings_for(svc: dict[str, Any]) -> Any:
        values = {
            v["key"].lower(): (fills[v["key"]] if v.get("sync") is False else v["value"])
            for v in effective_vars(env, svc)
        }
        return make_settings(**{"database_readonly_url": None, **values})

    assert startup_violations(settings_for(service(WEB[env]))) == []
    assert startup_violations(settings_for(service(CRON[env])), operator=True) == []


# --- DATABASE_MIGRATION_URL import boundary (DEP-040, TRD 20 §4.3 closed list, RSK-15) ---------

# Modules that may reach the migrator connection: Alembic, the operator CLI (seed, reset-test-db,
# purge-resident, rebuild, set-config), the ground-truth loader, and the settings and engine
# modules that define the accessors they use.
MIGRATOR_ALLOWED = {
    "backend/alembic/env.py",
    "backend/cli.py",
    "backend/core/config.py",
    "backend/core/db.py",
    "database/seeds/load_evaluation_ground_truth.py",
}
_MIGRATOR_TOKENS = re.compile(
    r"DATABASE_MIGRATION_URL|database_migration_url|migration_url|migrator_connection"
)


def migrator_references(root: Path) -> set[str]:
    found = set()
    for top in ("backend", "analytics", "database"):
        for path in (root / top).rglob("*.py"):
            rel = path.relative_to(root).as_posix()
            if "/alembic/versions/" in rel:
                continue
            if _MIGRATOR_TOKENS.search(path.read_text()):
                found.add(rel)
    return found


@pytest.mark.req("DEP-040", "SEC-111", "FEAT-081-FR-02", "FEAT-081-AC-03")
def test_only_the_closed_list_reads_database_migration_url() -> None:
    assert migrator_references(ROOT) <= MIGRATOR_ALLOWED


@pytest.mark.req("DEP-040", "FEAT-081-AC-03")
@pytest.mark.parametrize("package", ["api", "services", "jobs"])
def test_boundary_check_catches_application_code(tmp_path: Path, package: str) -> None:
    module = tmp_path / "backend" / package / "leak.py"
    module.parent.mkdir(parents=True)
    module.write_text('import os\nURL = os.environ["DATABASE_MIGRATION_URL"]\n')
    assert not migrator_references(tmp_path) <= MIGRATOR_ALLOWED
