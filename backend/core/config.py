"""Backend settings and startup guards (TRD 21 ENV-001..ENV-054; TRD 05 API-010, API-058, API-059).

This is the only module that reads the process environment (ENV-001). `get_settings()` returns the
cached `Settings`; `load_settings_or_exit()` validates them before a process accepts work and exits
with code 1 after one CRITICAL `startup_config_invalid` record that names the invalid variables and
the rule, never their values (ENV-002, LOG-072).
"""

from __future__ import annotations

import logging
import os
import re
import sys
from datetime import datetime
from functools import lru_cache
from typing import Literal, NoReturn
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("backend.startup")

DOTENV_ENVS = ("local", "test")
DEPLOYED_ENVS = ("staging", "production")
# ECHOWELL_* variables defined by TRD 21 §4.5 (Compose/CI); any other is a typo (ENV-003).
KNOWN_ECHOWELL_VARS = frozenset(
    {"ECHOWELL_MIGRATOR_DB_PASSWORD", "ECHOWELL_APP_DB_PASSWORD", "ECHOWELL_READONLY_DB_PASSWORD"}
)
# JWT_SECRET value of the committed .env.development.example (ENV-013).
TEMPLATE_JWT_SECRETS = frozenset({"local-dev-only-0123456789abcdef0123456789abcdef"})
PLACEHOLDER_MARKERS = ("local-dev-only", "ci-only")
_RATE_RE = re.compile(r"^\d+/(second|minute|hour|day)$")
_SHA_RE = re.compile(r"^(unknown|[0-9a-f]{7,40})$")
_DB_SCHEMES = ("postgres://", "postgresql://", "postgresql+psycopg://")
# RSK-10: the former facility name, matched loosely so the literal never appears in code (AGT-019).
_FORBIDDEN_FACILITY = re.compile(r"edge\W*4\W*care", re.IGNORECASE)

AppEnv = Literal["local", "staging", "production", "test"]


def normalise_database_url(value: str) -> str:
    """Normalise `postgres://` and `postgresql://` to `postgresql+psycopg://` (ENV-014)."""
    if not value.startswith(_DB_SCHEMES):
        raise ValueError("scheme must be postgres, postgresql or postgresql+psycopg")
    scheme, rest = value.split("://", 1)
    return f"postgresql+psycopg://{rest}" if scheme != "postgresql+psycopg" else value


class Settings(BaseSettings):
    """Every backend variable of TRD 21 §4.2 and §4.3; secrets are `SecretStr` (ENV-004)."""

    model_config = SettingsConfigDict(extra="ignore", env_file_encoding="utf-8")

    app_env: AppEnv
    database_url: SecretStr
    database_migration_url: SecretStr | None = None
    database_readonly_url: SecretStr | None = None
    jwt_secret: SecretStr | None = None
    jwt_expires_minutes: int = Field(default=60, ge=5, le=1440)
    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    cors_origin_regex: str = ""
    facility_name: str = Field(default="Edgewood", min_length=1, max_length=80)
    facility_tz: str = "America/Chicago"
    pipeline_profile: Literal["production", "test_v0_1"] = "production"
    pipeline_as_of: str = ""
    nightly_run_hour_local: int = Field(default=2, ge=0, le=23)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_format: Literal["json", "console"] = "json"
    sentry_dsn: SecretStr = SecretStr("")
    rate_limit_login: str = "5/minute"
    rate_limit_ingest: str = "600/minute"
    git_sha: str = "unknown"
    data_source_label: str = Field(default="pipeline test data v0.1", min_length=1, max_length=60)
    seed_admin_password: SecretStr | None = None
    seed_clinician_password: SecretStr | None = None
    seed_researcher_password: SecretStr | None = None
    seed_ingest_api_key: SecretStr | None = None
    port: int = Field(default=8000, ge=1, le=65535)

    @field_validator(
        "database_url", "database_migration_url", "database_readonly_url", mode="before"
    )
    @classmethod
    def _normalise_urls(cls, value: object) -> object:
        raw = value.get_secret_value() if isinstance(value, SecretStr) else value
        if raw is None or raw == "":
            return None
        if not isinstance(raw, str):
            raise ValueError("must be a string")
        return SecretStr(normalise_database_url(raw))

    @field_validator("jwt_secret")
    @classmethod
    def _jwt_length(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and len(value.get_secret_value().encode()) < 32:
            raise ValueError("must be at least 32 bytes (ENV-013)")
        return value

    @field_validator("cors_origins")
    @classmethod
    def _cors_origins(cls, value: str) -> str:
        for origin in [o.strip() for o in value.split(",") if o.strip()]:
            parts = urlsplit(origin)
            if origin == "*" or parts.scheme not in ("http", "https") or not parts.netloc:
                raise ValueError("each item must be an http(s) origin; '*' is forbidden")
            if parts.path or parts.query or parts.fragment:
                raise ValueError("origins must not contain a path")
        return value

    @field_validator("cors_origin_regex")
    @classmethod
    def _cors_regex(cls, value: str) -> str:
        if value:
            if not (value.startswith("^https://") and value.endswith("$")):
                raise ValueError("must start with ^https:// and end with $")
            re.compile(value)
        return value

    @field_validator("facility_name")
    @classmethod
    def _facility_name(cls, value: str) -> str:
        if _FORBIDDEN_FACILITY.search(value):
            raise ValueError("must not contain the forbidden facility name (ENV-015)")
        return value

    @field_validator("facility_tz")
    @classmethod
    def _facility_tz(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("must be a valid IANA time zone") from exc
        return value

    @field_validator("pipeline_as_of")
    @classmethod
    def _as_of(cls, value: str) -> str:
        if not value:
            return value
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            parsed = None
        if parsed is None or parsed.tzinfo is None:
            raise ValueError("must be ISO 8601 with a UTC offset")
        return value

    @field_validator("rate_limit_login", "rate_limit_ingest")
    @classmethod
    def _rate(cls, value: str) -> str:
        if not _RATE_RE.match(value):
            raise ValueError("must be <int>/<second|minute|hour|day>")
        return value

    @field_validator("git_sha")
    @classmethod
    def _sha(cls, value: str) -> str:
        if not _SHA_RE.match(value):
            raise ValueError("must be 'unknown' or 7-40 hex characters")
        return value

    @field_validator("sentry_dsn")
    @classmethod
    def _sentry(cls, value: SecretStr) -> SecretStr:
        if value.get_secret_value() and not value.get_secret_value().startswith("https://"):
            raise ValueError("must be empty or an https URL")
        return value

    @property
    def migration_url(self) -> SecretStr:
        """DATABASE_MIGRATION_URL, else DATABASE_URL (TRD 21 §4.3); Alembic and CLI only."""
        return self.database_migration_url or self.database_url

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


def _secret(value: SecretStr | None) -> str:
    return value.get_secret_value() if value is not None else ""


def _url_password(url: SecretStr | None) -> str:
    return urlsplit(_secret(url)).password or ""


def startup_violations(settings: Settings, *, operator: bool = False) -> list[tuple[str, str]]:
    """Cross-variable guards (ENV-010..ENV-013, ENV-041, ENV-053, ENV-054) as (name, rule) pairs."""
    env, problems = settings.app_env, []
    prod, deployed = env == "production", env in DEPLOYED_ENVS
    if prod and settings.pipeline_profile == "test_v0_1":
        problems.append(("PIPELINE_PROFILE", "test_v0_1 is refused when APP_ENV=production"))
    if prod and settings.pipeline_as_of:
        problems.append(("PIPELINE_AS_OF", "must be empty when APP_ENV=production"))
    if deployed and settings.log_format == "console":
        problems.append(("LOG_FORMAT", "console is refused in staging and production"))
    if deployed and settings.rate_limit_login != "5/minute":
        problems.append(("RATE_LIMIT_LOGIN", "must be 5/minute in staging and production"))
    urls = {
        "DATABASE_URL": settings.database_url,
        "DATABASE_MIGRATION_URL": settings.database_migration_url,
        "DATABASE_READONLY_URL": settings.database_readonly_url,
    }
    for name, url in urls.items():
        query = urlsplit(_secret(url)).query
        if deployed and url is not None and not re.search(r"sslmode=(require|verify-full)", query):
            problems.append((name, "must specify sslmode=require or verify-full"))
        if deployed and any(m in _url_password(url) for m in PLACEHOLDER_MARKERS):
            problems.append((name, "placeholder password refused in staging and production"))
    seeds = {
        "SEED_ADMIN_PASSWORD": settings.seed_admin_password,
        "SEED_CLINICIAN_PASSWORD": settings.seed_clinician_password,
        "SEED_RESEARCHER_PASSWORD": settings.seed_researcher_password,
        "SEED_INGEST_API_KEY": settings.seed_ingest_api_key,
    }
    for name, value in seeds.items():
        if prod and _secret(value):
            problems.append((name, "must not be set when APP_ENV=production"))
        elif deployed and any(m in _secret(value) for m in PLACEHOLDER_MARKERS):
            problems.append((name, "placeholder value refused in staging and production"))
    if not operator:
        problems.extend(_web_violations(settings))
    return problems


def _web_violations(settings: Settings) -> list[tuple[str, str]]:
    """Variables required only by the web application (ENV-053)."""
    env, problems = settings.app_env, []
    deployed = env in DEPLOYED_ENVS
    jwt = _secret(settings.jwt_secret)
    if not jwt:
        problems.append(("JWT_SECRET", "is required"))
    elif deployed and (
        jwt in TEMPLATE_JWT_SECRETS
        or len(set(jwt)) < 16
        or any(m in jwt for m in PLACEHOLDER_MARKERS)
    ):
        problems.append(("JWT_SECRET", "template, placeholder or low-entropy value refused"))
    if deployed and "cors_origins" not in settings.model_fields_set:
        problems.append(("CORS_ORIGINS", "is required in staging and production"))
    if deployed and "facility_name" not in settings.model_fields_set:
        problems.append(("FACILITY_NAME", "is required in staging and production"))
    for origin in settings.cors_origin_list:
        parts = urlsplit(origin)
        if parts.scheme == "http" and (env not in DOTENV_ENVS or parts.hostname != "localhost"):
            problems.append(("CORS_ORIGINS", "http:// is allowed only for localhost in local/test"))
    if env == "production" and settings.cors_origin_regex:
        problems.append(("CORS_ORIGIN_REGEX", "must be empty when APP_ENV=production"))
    if settings.pipeline_profile == "test_v0_1" and settings.database_readonly_url is None:
        problems.append(("DATABASE_READONLY_URL", "is required when PIPELINE_PROFILE=test_v0_1"))
    return problems


def _environment_violations() -> list[tuple[str, str]]:
    """Unknown ECHOWELL_* variables are typos (ENV-003)."""
    unknown = sorted(
        k for k in os.environ if k.startswith("ECHOWELL_") and k not in KNOWN_ECHOWELL_VARS
    )
    return [(name, "unknown ECHOWELL_ variable") for name in unknown]


def build_settings() -> Settings:
    """Read the environment; a `.env` file is read only when APP_ENV is local or test (ENV-006)."""
    use_dotenv = os.environ.get("APP_ENV", "local") in DOTENV_ENVS
    settings = Settings(_env_file=".env" if use_dotenv else None)
    if use_dotenv and settings.app_env not in DOTENV_ENVS:
        settings = Settings(_env_file=None)
    return settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings (API-010); tests clear the cache or use `app.dependency_overrides`."""
    return build_settings()


def ensure_valid(settings: Settings, *, operator: bool = False) -> None:
    """Exit with code 1 after one CRITICAL `startup_config_invalid` record when a guard fails."""
    problems = _environment_violations() + startup_violations(settings, operator=operator)
    if problems:
        _exit_invalid(problems)
    if settings.log_level == "DEBUG" and settings.app_env in DEPLOYED_ENVS:
        logger.warning("debug_logging_enabled")


def load_settings_or_exit(*, operator: bool = False) -> Settings:
    """Load and validate settings for the web app, the nightly job (operator=False) or the CLI."""
    try:
        settings = get_settings()
    except ValidationError as exc:
        problems = [
            (str(err["loc"][0]).upper() if err["loc"] else "SETTINGS", err["msg"])
            for err in exc.errors(include_input=False, include_url=False)
        ]
        _exit_invalid(_environment_violations() + problems)
    ensure_valid(settings, operator=operator)
    return settings


def _exit_invalid(problems: list[tuple[str, str]]) -> NoReturn:
    detail = "; ".join(f"{name}: {rule}" for name, rule in problems)
    logger.critical(
        "startup_config_invalid: %s",
        detail,
        extra={"event": "startup_config_invalid", "invalid": [n for n, _ in problems]},
    )
    sys.exit(1)
