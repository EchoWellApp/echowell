"""Integration fixtures: role-specific connections to a migrated PostgreSQL 16 database.

TRD 13 §4.2, TST-002, TST-040; TRD 20 §4.3, §8; FEAT-008. Each `*_conn` fixture is one connection
inside a transaction that is rolled back after the test, so tests never leave rows behind (rows of
the append-only tables included). Tests that must commit use `fresh_db`, a throwaway database.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from sqlalchemy import Connection, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from tests.integration.db_support import (
    PgUrls,
    alembic,
    provision,
    throwaway_database,
    urls_for_superuser,
    urls_from_environment,
)
from tests.integration.world import World


@pytest.fixture(scope="session")
def pg_urls() -> Iterator[PgUrls]:
    """Provisioned database URLs per role (environment, else a testcontainer)."""
    urls = urls_from_environment()
    if urls is not None:
        yield urls
        return
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine", driver="psycopg") as container:
        superuser = container.get_connection_url()
        provision(superuser)
        yield urls_for_superuser(superuser)


@dataclass(frozen=True)
class RoundTrip:
    """Outcome of `alembic upgrade head`, `downgrade base`, `upgrade head` (TST-040)."""

    upgrade: int
    downgrade: int
    upgrade_again: int
    output: str


@pytest.fixture(scope="session")
def migrated(pg_urls: PgUrls) -> RoundTrip:
    """Migrate the shared test database once, through the full round trip (FEAT-008-AC-01)."""
    steps = [alembic(pg_urls, "upgrade", "head")]
    steps.append(alembic(pg_urls, "downgrade", "base"))
    steps.append(alembic(pg_urls, "upgrade", "head"))
    output = "\n".join(s.stdout + s.stderr for s in steps)
    assert steps[-1].returncode == 0, output
    return RoundTrip(*(s.returncode for s in steps), output=output)


def _engine(url: str) -> Engine:
    return create_engine(url, poolclass=NullPool)


@pytest.fixture
def app_conn(pg_urls: PgUrls, migrated: RoundTrip) -> Iterator[Connection]:
    """Connection as `echowell_app_login` in a rolled-back transaction."""
    yield from _rolled_back(pg_urls.app)


@pytest.fixture
def migrator_conn(pg_urls: PgUrls, migrated: RoundTrip) -> Iterator[Connection]:
    """Connection as the table owner `echowell_migrator` (SET LOCAL ROLE) in a rolled-back
    transaction."""
    yield from _rolled_back(pg_urls.migrator, "SET LOCAL ROLE echowell_migrator")


@pytest.fixture
def readonly_conn(pg_urls: PgUrls, migrated: RoundTrip) -> Iterator[Connection]:
    yield from _rolled_back(pg_urls.readonly)


@pytest.fixture
def app_session(app_conn: Connection) -> Iterator[Session]:
    """ORM session on `app_conn`; `session.commit()` only releases a savepoint."""
    with Session(bind=app_conn, join_transaction_mode="create_savepoint") as session:
        yield session


def _rolled_back(url: str, *setup: str) -> Iterator[Connection]:
    engine = _engine(url)
    with engine.connect() as connection:
        transaction = connection.begin()
        for statement in setup:
            connection.execute(text(statement))
        try:
            yield connection
        finally:
            transaction.rollback()
    engine.dispose()


@pytest.fixture
def superuser_urls(pg_urls: PgUrls, migrated: RoundTrip) -> PgUrls:
    if pg_urls.superuser is None:
        pytest.skip("throwaway databases need TEST_SUPERUSER_URL (TST-040, PGS-002)")
    return pg_urls


@pytest.fixture
def fresh_db(superuser_urls: PgUrls) -> Iterator[PgUrls]:
    """A provisioned and migrated throwaway database for tests that commit."""
    with throwaway_database(superuser_urls) as urls:
        yield urls


@pytest.fixture
def world(app_session: Session) -> World:
    """The test_v0_1 roster and one pipeline run, as `echowell_app` (rolled back)."""
    return World.build(app_session)


@pytest.fixture
def owner_session(migrator_conn: Connection) -> Iterator[Session]:
    """ORM session as the table owner `echowell_migrator` (rolled back)."""
    with Session(bind=migrator_conn, join_transaction_mode="create_savepoint") as session:
        yield session


@pytest.fixture
def owner_world(owner_session: Session) -> World:
    return World.build(owner_session)
