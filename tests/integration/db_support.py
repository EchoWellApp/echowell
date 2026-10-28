"""Database helpers shared by the integration tests (TRD 13 §4.2, TST-002; TRD 20 §8).

URLs come from the environment in CI and locally (APP_ENV=test with DATABASE_URL,
DATABASE_MIGRATION_URL and DATABASE_READONLY_URL, provisioned and migrated by the CI steps);
`TEST_SUPERUSER_URL` (optional) enables the tests that create throwaway databases. Without those
variables a `postgres:16-alpine` testcontainer is started and provisioned here.
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import psycopg
from psycopg import sql
from sqlalchemy import Connection, Executable, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
ROLE_PASSWORDS = {
    "echowell_migrator_login": os.environ.get("ECHOWELL_MIGRATOR_DB_PASSWORD", "ci-only-migrator"),
    "echowell_app_login": os.environ.get("ECHOWELL_APP_DB_PASSWORD", "ci-only-app"),
    "echowell_readonly_login": os.environ.get("ECHOWELL_READONLY_DB_PASSWORD", "ci-only-readonly"),
}


@dataclass(frozen=True)
class PgUrls:
    app: str
    migrator: str
    readonly: str
    superuser: str | None

    def for_database(self, name: str) -> PgUrls:
        return PgUrls(
            app=with_database(self.app, name),
            migrator=with_database(self.migrator, name),
            readonly=with_database(self.readonly, name),
            superuser=with_database(self.superuser, name) if self.superuser else None,
        )


def with_database(url: str, name: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(parts._replace(path=f"/{name}"))


def with_user(url: str, user: str, password: str) -> str:
    parts = urlsplit(url)
    host = parts.hostname or "localhost"
    netloc = f"{user}:{password}@{host}" + (f":{parts.port}" if parts.port else "")
    return urlunsplit(parts._replace(netloc=netloc))


def libpq(url: str) -> str:
    """psycopg / pg_dump form of a SQLAlchemy URL."""
    return url.replace("postgresql+psycopg://", "postgresql://", 1)


def urls_from_environment() -> PgUrls | None:
    names = ("DATABASE_URL", "DATABASE_MIGRATION_URL", "DATABASE_READONLY_URL")
    if os.environ.get("APP_ENV") != "test" or not all(os.environ.get(n) for n in names):
        return None
    return PgUrls(
        app=os.environ["DATABASE_URL"],
        migrator=os.environ["DATABASE_MIGRATION_URL"],
        readonly=os.environ["DATABASE_READONLY_URL"],
        superuser=os.environ.get("TEST_SUPERUSER_URL") or None,
    )


def provision(superuser_url: str, *, extensions: bool = True) -> None:
    """Python twin of `database/roles/provision_login_roles.sql` for the current database."""
    with psycopg.connect(libpq(superuser_url), autocommit=True) as conn:
        if extensions:
            conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
            conn.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
        name = conn.execute("SELECT current_database()").fetchone()[0]  # type: ignore[index]
        conn.execute(sql.SQL("ALTER DATABASE {} SET timezone = 'UTC'").format(sql.Identifier(name)))
        for group in ("echowell_migrator", "echowell_app", "echowell_readonly"):
            if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (group,)).fetchone():
                conn.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(sql.Identifier(group)))
        conn.execute("ALTER SCHEMA public OWNER TO echowell_migrator")
        for login, password in ROLE_PASSWORDS.items():
            group = login.removesuffix("_login")
            if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (login,)).fetchone():
                conn.execute(
                    sql.SQL("CREATE ROLE {} LOGIN IN ROLE {}").format(
                        sql.Identifier(login), sql.Identifier(group)
                    )
                )
            conn.execute(
                sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                    sql.Identifier(login), sql.Literal(password)
                )
            )


def urls_for_superuser(superuser_url: str) -> PgUrls:
    return PgUrls(
        app=with_user(superuser_url, "echowell_app_login", ROLE_PASSWORDS["echowell_app_login"]),
        migrator=with_user(
            superuser_url, "echowell_migrator_login", ROLE_PASSWORDS["echowell_migrator_login"]
        ),
        readonly=with_user(
            superuser_url, "echowell_readonly_login", ROLE_PASSWORDS["echowell_readonly_login"]
        ),
        superuser=superuser_url,
    )


def cli_environment(urls: PgUrls, **extra: str) -> dict[str, str]:
    """Environment for Alembic and the operator CLI against `urls` (TRD 21 ENV-053)."""
    env = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "LANG", "PYTHONPATH")}
    env.update(
        {
            "APP_ENV": "test",
            "DATABASE_URL": urls.app,
            "DATABASE_MIGRATION_URL": urls.migrator,
            "DATABASE_READONLY_URL": urls.readonly,
            "PIPELINE_PROFILE": "test_v0_1",
            "FACILITY_NAME": "Edgewood",
            "FACILITY_TZ": "America/Chicago",
            "LOG_FORMAT": "json",
        }
    )
    env.update(extra)
    return env


def alembic(urls: PgUrls, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed interpreter and arguments
        [sys.executable, "-m", "alembic", *args],
        cwd=ROOT, env=cli_environment(urls), capture_output=True, text=True, check=False,
        timeout=300,
    )  # fmt: skip


@contextmanager
def throwaway_database(
    urls: PgUrls, *, extensions: bool = True, migrate: bool = True
) -> Iterator[PgUrls]:
    """Create, provision and (optionally) migrate a database; drop it afterwards."""
    assert urls.superuser is not None
    name = f"echowell_t_{uuid.uuid4().hex[:10]}"
    admin = libpq(with_database(urls.superuser, "postgres"))
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    fresh = urls.for_database(name)
    try:
        assert fresh.superuser is not None
        provision(fresh.superuser, extensions=extensions)
        if migrate:
            result = alembic(fresh, "upgrade", "head")
            assert result.returncode == 0, result.stderr
        yield fresh
    finally:
        from backend.core import db

        db._engine.cache_clear()
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s", (name,)
            )
            conn.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(name)))


def sqlstate(exc: BaseException) -> str | None:
    """SQLSTATE of a SQLAlchemy or psycopg error."""
    orig = getattr(exc, "orig", exc)
    return getattr(orig, "sqlstate", None)


def outcome(target: Connection | Session, statement: Executable | str, params: Any = None) -> str:
    """Run one statement in a savepoint: "ok", or the SQLSTATE it failed with."""
    stmt = text(statement) if isinstance(statement, str) else statement
    try:
        with target.begin_nested():
            target.execute(stmt, params)
    except DBAPIError as exc:
        return sqlstate(exc) or "error"
    return "ok"


__all__ = [
    "ROOT",
    "PgUrls",
    "alembic",
    "cli_environment",
    "libpq",
    "outcome",
    "provision",
    "replace",
    "sqlstate",
    "throwaway_database",
    "urls_for_superuser",
    "urls_from_environment",
]
