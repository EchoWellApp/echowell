"""API fixtures (TRD 13 §4.2; TRD 05 API-017).

`bare_app` is the real application with test-only routes and no database; `api` is a client of
the application on the migrated test database, whose request sessions join one rolled-back
connection (each request's commit releases a savepoint), so tests leave no rows behind.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Connection
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from backend.api.deps import get_db, get_settings
from backend.core.config import Settings
from backend.main import create_app
from tests.conftest import make_settings
from tests.integration.db_support import PgUrls


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str


def extra_routes() -> APIRouter:
    """Routes used only by the middleware and error-handler tests."""
    router = APIRouter()

    @router.get("/_test/boom")
    def boom() -> dict[str, str]:
        raise RuntimeError("secret detail postgresql://u:pw@db/x")

    @router.post("/_test/echo")
    def echo(body: StrictBody) -> dict[str, str]:
        return {"name": body.name}

    @router.get("/_test/db-down")
    def db_down() -> dict[str, str]:
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    return router


@pytest.fixture
def app_factory() -> Callable[..., FastAPI]:
    def build(**overrides: Any) -> FastAPI:
        settings = make_settings(**overrides)
        app = create_app(settings)
        app.include_router(extra_routes(), prefix="/api/v1")
        app.dependency_overrides[get_settings] = lambda: settings
        return app

    return build


@pytest.fixture
def bare_client(app_factory: Callable[..., FastAPI]) -> Iterator[TestClient]:
    with TestClient(app_factory(), raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def api_settings(pg_urls: PgUrls) -> Settings:
    return make_settings(database_url=pg_urls.app, database_readonly_url=pg_urls.readonly)


@pytest.fixture
def api(api_settings: Settings, app_conn: Connection) -> Iterator[TestClient]:
    """Client of the full app on the migrated database, rolled back after the test."""
    app = create_app(api_settings)
    app.dependency_overrides[get_settings] = lambda: api_settings

    def shared_session() -> Iterator[Session]:
        with Session(bind=app_conn, join_transaction_mode="create_savepoint") as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    app.dependency_overrides[get_db] = shared_session
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
