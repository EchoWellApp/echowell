"""API fixtures (TRD 13 §4.2; TRD 05 API-017).

`bare_app` is the real application with test-only routes and no database; `api` is a client of
the application on the migrated test database, whose request sessions join one rolled-back
connection (each request's commit releases a savepoint), so tests leave no rows behind.

Rows the app writes in their own committed transaction (`auth.login.failed`, `access.denied`)
are captured in `audit_rows` instead, because a second transaction could not see the test's
uncommitted users. `principals` holds one user per role and API keys per scope.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from functools import cache
from typing import Annotated, Any

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Connection
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from backend.api.deps import AuditWriter, Principal, authorize, get_db, get_settings
from backend.core import security
from backend.core.config import Settings
from backend.main import create_app
from backend.models import ApiKey, User, UserRole
from backend.repositories.api_key_repository import ApiKeyRepository
from backend.repositories.user_repository import UserRepository
from tests.conftest import TEST_JWT_SECRET, make_settings
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

    @router.get("/_test/admin-only")
    def admin_only(
        principal: Annotated[Principal, Depends(authorize("GET /users"))],
    ) -> dict[str, str]:
        return {"actor": principal.actor_id}

    @router.post("/_test/ingest-key")
    def ingest_key(
        principal: Annotated[Principal, Depends(authorize("POST /sessions"))],
    ) -> dict[str, str]:
        return {"actor": principal.actor_id}

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
def audit_rows() -> list[dict[str, Any]]:
    """Keyword arguments of every committed-mode audit write (`AuditWriter.committed`)."""
    return []


@pytest.fixture
def api(
    api_settings: Settings, app_conn: Connection, audit_rows: list[dict[str, Any]]
) -> Iterator[TestClient]:
    """Client of the full app plus the test-only routes on the migrated database, rolled back
    after the test."""
    app = create_app(api_settings)
    app.include_router(extra_routes(), prefix="/api/v1")
    app.dependency_overrides[get_settings] = lambda: api_settings
    app.state.audit_writer = AuditWriter(lambda **kwargs: audit_rows.append(kwargs))

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


PASSWORD = "Synthetic-Pass-2026!"  # noqa: S105 - test-only value
ROLES = ("admin", "clinician", "researcher")
KEY_SCOPES = {"ingest": ["ingest:write"], "pipeline": ["pipeline:run"]}


@cache
def password_hash() -> str:
    return security.hash_password(PASSWORD)


@dataclass
class Principals:
    """One active user per role and one API key per scope, in the test's transaction."""

    session: Session
    users: dict[str, User] = field(default_factory=dict)
    raw_keys: dict[str, str] = field(default_factory=dict)
    keys: dict[str, ApiKey] = field(default_factory=dict)

    def add_user(self, role: str, email: str | None = None, active: bool = True) -> User:
        email = email or f"{role}-{uuid.uuid4().hex[:8]}@example.test"
        users = UserRepository(self.session)
        user = users.insert(
            email=email, display_name=f"Test {role}", password_hash=password_hash(),
            role=UserRole(role),
        )  # fmt: skip
        if not active:
            users.update(user, active=False)
        self.session.commit()
        return user

    def add_key(self, name: str, scopes: list[str]) -> str:
        raw = security.generate_api_key()
        key = ApiKeyRepository(self.session).insert(
            name=f"{name}-{uuid.uuid4().hex[:6]}", key_hash=security.hash_api_key(raw),
            scopes=scopes,
        )  # fmt: skip
        self.session.commit()
        self.raw_keys[name], self.keys[name] = raw, key
        return raw

    def token(self, role: str, *, minutes: int = 60, secret: str = TEST_JWT_SECRET) -> str:
        user = self.users[role]
        return security.create_access_token(user.id, user.role.value, secret, minutes)

    def bearer(self, role: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token(role)}"}

    def api_key(self, name: str) -> dict[str, str]:
        return {"X-API-Key": self.raw_keys[name]}


@pytest.fixture
def principals(app_session: Session) -> Principals:
    found = Principals(app_session)
    for role in ROLES:
        found.users[role] = found.add_user(role)
    for name, scopes in KEY_SCOPES.items():
        found.add_key(name, scopes)
    return found
