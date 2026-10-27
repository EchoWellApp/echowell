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
from datetime import UTC, date, datetime
from functools import cache
from typing import Annotated, Any

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Connection
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from backend.api.deps import (
    AuditWriter,
    Principal,
    authorize,
    get_db,
    get_session_factory,
    get_settings,
)
from backend.cli import load_roster
from backend.core import security
from backend.core.config import Settings
from backend.main import create_app
from backend.models import ApiKey, User, UserRole
from backend.repositories.api_key_repository import ApiKeyRepository
from backend.repositories.resident_repository import ResidentRepository
from backend.repositories.user_repository import UserRepository
from tests.conftest import TEST_JWT_SECRET, make_settings
from tests.integration.db_support import PgUrls
from tests.integration.world import ROSTER, World


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
    app.dependency_overrides[get_session_factory] = lambda: lambda: Session(
        bind=app_conn, join_transaction_mode="create_savepoint"
    )
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

    def add_key(self, name: str, scopes: list[str], device_id: uuid.UUID | None = None) -> str:
        raw = security.generate_api_key()
        key = ApiKeyRepository(self.session).insert(
            name=f"{name}-{uuid.uuid4().hex[:6]}", key_hash=security.hash_api_key(raw),
            scopes=scopes, device_id=device_id,
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


@pytest.fixture
def roster(app_session: Session) -> Session:
    """The test_v0_1 roster (R01-R10, devices, assignments), rolled back after the test."""
    load_roster(app_session, ROSTER)
    app_session.commit()
    return app_session


AS_OF = datetime(2026, 10, 30, 20, 0, tzinfo=UTC)  # 15:00 America/Chicago


def _day(n: int) -> date:
    return date(2026, 10, n)


@pytest.fixture
def scene(world: World) -> World:
    """A synthetic read-model scenario, as-of 2026-10-30 (TRD 23 §4.4; FEAT-027..FEAT-029):

    - R01 (D01): epoch 1 frozen after Oct 1..16, scored Oct 17..20, open alert Oct 20 (tally 7.5),
      set aside Oct 21, a duplicate of Oct 17 on Oct 22, missed Oct 23.
    - R02 (D02, shared): 13 usable Oct 1..13 (forming); device gap Oct 14.
    - R03 (D02, shared): frozen epoch 1, open `high_set_aside` data alert; device gap Oct 14.
    - R05 (D05): epoch 2 by firmware on Oct 5 with a set-aside and a first score that day.
    - R07: epoch 1 on D07 (Oct 1), epoch 2 on D07B from Oct 13, frozen; a record on Oct 30.
    - R10: withdrawn on Oct 25.
    """
    w = world
    sid = lambda code, n: f"{code}-202610{n:02d}-01"  # noqa: E731
    e1 = w.epoch("R01", "D01", started_at=datetime(2026, 10, 1, 12, tzinfo=UTC))
    for n in range(1, 17):
        w.processed("R01", "D01", _day(n), "usable", e1, ordinal=n, session_id=sid("R01", n),
                    in_baseline=True)  # fmt: skip
    w.freeze("R01", e1, sid("R01", 1), sid("R01", 16))
    for n, tally in ((17, 1.0), (18, 2.5), (19, 4.0), (20, 5.4)):
        pid, _ = w.processed(
            "R01", "D01", _day(n), "usable", e1, ordinal=n, session_id=sid("R01", n)
        )
        w.score("R01", e1, pid, _day(n), tally=tally)
    w.alert("R01", e1, sid("R01", 20), _day(20), value=5.4)
    w.cusum("R01", e1, 7.5, sid("R01", 20))
    w.processed("R01", "D01", _day(21), "set_aside", e1, session_id=sid("R01", 21))
    w.processed("R01", "D01", _day(22), "duplicate", None, session_id=sid("R01", 17))
    w.ledger("R01", _day(23), "missing_resident")

    e2 = w.epoch("R02", "D02", started_at=datetime(2026, 10, 1, 12, tzinfo=UTC))
    for n in range(1, 14):
        w.processed("R02", "D02", _day(n), "usable", e2, ordinal=n, session_id=sid("R02", n))
    e3 = w.epoch("R03", "D02", started_at=datetime(2026, 10, 1, 12, tzinfo=UTC))
    for n in (1, 2):
        w.processed("R03", "D02", _day(n), "usable", e3, ordinal=n, session_id=sid("R03", n))
    w.freeze("R03", e3, sid("R03", 1), sid("R03", 2))
    w.data_alert("R03", "high_set_aside")
    w.data_alert("R02", "possible_other_speaker")  # not an attention kind
    for code in ("R02", "R03"):
        w.ledger(code, _day(14), "missing_device_gap", "D02")

    w.epoch("R05", "D05", started_at=datetime(2026, 10, 1, 12, tzinfo=UTC),
            ended_at=datetime(2026, 10, 5, 12, tzinfo=UTC))  # fmt: skip
    e5 = w.epoch("R05", "D05", number=2, firmware="fw-1.1.0",
                 started_at=datetime(2026, 10, 5, 12, tzinfo=UTC))  # fmt: skip
    w.processed("R05", "D05", _day(5), "set_aside", e5, session_id="R05-20261005-02", hour=14)
    pid, _ = w.processed("R05", "D05", _day(5), "usable", e5, ordinal=1, hour=15,
                         session_id="R05-20261005-01")  # fmt: skip
    w.score("R05", e5, pid, _day(5))

    e7a = w.epoch("R07", "D07", started_at=datetime(2026, 10, 1, 12, tzinfo=UTC),
                  ended_at=datetime(2026, 10, 13, 12, tzinfo=UTC))  # fmt: skip
    w.processed("R07", "D07", _day(1), "usable", e7a, ordinal=1, session_id=sid("R07", 1))
    e7 = w.epoch("R07", "D07B", number=2, started_at=datetime(2026, 10, 13, 12, tzinfo=UTC))
    for n in (13, 14):
        w.processed("R07", "D07B", _day(n), "usable", e7, ordinal=n - 12, session_id=sid("R07", n))
    w.freeze("R07", e7, sid("R07", 13), sid("R07", 14))
    w.processed(
        "R07", "D07B", _day(30), "usable", e7, ordinal=3, hour=19, session_id=sid("R07", 30)
    )

    residents = ResidentRepository(w.session)
    r10 = residents.get_by_code("R10")
    assert r10 is not None
    residents.set_withdrawn(r10, _day(25))
    w.succeed(AS_OF)
    w.session.commit()
    return w
