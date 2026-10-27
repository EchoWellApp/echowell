"""Shared pytest fixtures and collection rules (TRD 13 §4.2, TST-002, TST-005, TST-006, TST-153).

The answer-key loader lives only in tests/validation/conftest.py (TRD 13 §8, AGT-007).
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
import time_machine
from fastapi.testclient import TestClient
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from backend.api.deps import get_engine, get_settings
from backend.core import db
from backend.core.config import Settings
from backend.main import create_app

LEVEL_MARKERS = frozenset(
    {"unit", "integration", "contract", "validation", "security", "performance", "smoke"}
)
_SKIP_REASON_ID = re.compile(r"\b([A-Z]{2,4}-\d{2,3}|OQ-\d{2}|D-\d{2,3})\b")
# Test-only signing key; never valid outside tests (TRD 18 GIT-083).
TEST_JWT_SECRET = "test-only-jwt-secret-0123456789abcdefghijklmnop"  # noqa: S105 - test-only value
FROZEN_NOW = datetime(2026, 10, 30, 20, 0, tzinfo=UTC)  # 15:00 America/Chicago (TRD 14 as-of)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Each test module carries exactly one level marker (TST-006); skips name an ID (TST-153)."""
    errors: set[str] = set()
    for item in items:
        module = item.module
        marks = getattr(module, "pytestmark", [])
        marks = marks if isinstance(marks, list) else [marks]
        levels = {m.name for m in marks} & LEVEL_MARKERS
        if len(levels) != 1:
            errors.add(
                f"{item.location[0]}: needs exactly one level marker, found {sorted(levels)}"
            )
        for mark in item.iter_markers("skip"):
            reason = str(mark.kwargs.get("reason", mark.args[0] if mark.args else ""))
            if not _SKIP_REASON_ID.search(reason):
                errors.add(f"{item.nodeid}: skip reason must name a requirement or OQ ID")
    if errors:
        raise pytest.UsageError("\n".join(sorted(errors)))


class IsolatedSettings(Settings):
    """Settings built only from constructor values: no environment variables, no .env file."""

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        **_: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (init_settings,)


def make_settings(**overrides: Any) -> Settings:
    """Settings for tests, independent of the process environment (profile test_v0_1 by default)."""
    values: dict[str, Any] = {
        "app_env": "test",
        "database_url": "postgresql+psycopg://test:test@localhost:5432/echowell_test",
        "database_readonly_url": "postgresql+psycopg://test:test@localhost:5432/echowell_test",
        "jwt_secret": TEST_JWT_SECRET,
        "pipeline_profile": "test_v0_1",
        "cors_origins": "http://localhost:3000",
        "git_sha": "0123abc",
    }
    values.update(overrides)
    return IsolatedSettings(**values)


@pytest.fixture
def settings_factory() -> Callable[..., Settings]:
    """Build settings for a chosen profile or environment (keyword overrides)."""
    return make_settings


@pytest.fixture
def frozen_clock() -> Iterator[time_machine.Coordinates]:
    """Wall clock frozen at the test_v0_1 as-of (TST-005)."""
    with time_machine.travel(FROZEN_NOW, tick=False) as traveller:
        yield traveller


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    """PostgreSQL 16: DATABASE_URL when APP_ENV=test, else testcontainers postgres:16-alpine.

    TST-002; SQLite is never used.
    """
    if os.environ.get("APP_ENV") == "test" and os.environ.get("DATABASE_URL"):
        yield os.environ["DATABASE_URL"]
        return
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine", driver="psycopg") as container:
        yield container.get_connection_url()


@pytest.fixture(scope="session")
def engine(database_url: str) -> Engine:
    return db.create_engine_for(database_url, app_env="test")


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    """Per-test session inside a transaction that is rolled back, so test order never matters."""
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()


@pytest.fixture
def client(database_url: str) -> Iterator[TestClient]:
    """API client from create_app() with get_settings and get_engine overridden (API-017)."""
    settings = make_settings(database_url=database_url, database_readonly_url=database_url)
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_engine] = lambda: db.create_engine_for(
        settings.database_url, app_env="test"
    )
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> Iterator[None]:
    """Empty the in-memory slowapi storage before each test (TRD 24 D-74; FEAT-022-FR-09)."""
    from backend.core.rate_limit import limiter

    limiter.reset()
    yield
