"""The one engine factory, sessions, advisory locks and the database probe.

TRD 05 API-007, API-110, API-125; TRD 06 DB-021, DB-053; TRD 20 PGS-027; FEAT-013.

Engines are created lazily, never at import time, so the OpenAPI export needs no database
(TRD 16 §8). URLs use the `postgresql+psycopg://` scheme (ENV-014). Every engine (app, read-only,
Alembic, CLI) comes from `create_engine_for`, which refuses a non-local URL without TLS.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from contextlib import contextmanager
from functools import lru_cache
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from pydantic import SecretStr
from sqlalchemy import Connection, Engine, TextClause, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

if TYPE_CHECKING:
    from backend.core.config import Settings

# "Non-local" = every APP_ENV other than local and test (TRD 06 DB-053, TRD 24 D-88).
LOCAL_ENVS = ("local", "test")
_TLS_QUERY = re.compile(r"(^|&)sslmode=(require|verify-full)(&|$)")
# The four advisory-lock namespaces of DB-021.
ADVISORY_NAMESPACES = frozenset({"resident", "session", "device_alerts", "nightly"})
# Alembic's migration lock (TRD 15 DEP-064) and the migrator session setup (DB-028).
MIGRATION_LOCK_KEY = 0x45434857
MIGRATOR_SETUP = (
    "SET ROLE echowell_migrator",
    "SET lock_timeout = '5s'",
    "SET statement_timeout = '120s'",
)
_MIGRATOR_RESET = ("RESET ROLE", "RESET lock_timeout", "RESET statement_timeout")


class InsecureDatabaseUrlError(ValueError):
    """A non-local database URL without `sslmode=require` or `verify-full` (PGS-027)."""


def require_tls(url: str, app_env: str) -> None:
    """Refuse a URL without TLS unless APP_ENV is local or test (DB-053, PGS-027)."""
    if app_env in LOCAL_ENVS:
        return
    if not _TLS_QUERY.search(urlsplit(url).query):
        raise InsecureDatabaseUrlError(
            "database URLs outside local and test must specify sslmode=require or verify-full"
        )


@lru_cache(maxsize=8)
def _engine(url: str) -> Engine:
    return create_engine(
        url,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={"prepare_threshold": None, "connect_timeout": 5},
    )


def create_engine_for(url: SecretStr | str, *, app_env: str) -> Engine:
    """Return the shared engine for `url` with the API-125 pool settings (FEAT-013-FR-01)."""
    raw = url.get_secret_value() if isinstance(url, SecretStr) else url
    require_tls(raw, app_env)
    return _engine(raw)


@lru_cache(maxsize=2)
def _read_only_engine(url: str) -> Engine:
    return create_engine(
        url,
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={"prepare_threshold": None, "connect_timeout": 5},
        execution_options={"postgresql_readonly": True},
    )


def create_read_only_engine(url: SecretStr | str, *, app_env: str) -> Engine:
    """A second engine whose transactions are read-only (`pool_size=1`, API-136, ARC-015).

    Used only by the analytics summary for the evaluation answer key; created on first use, never
    at startup, and never in the production profile.
    """
    raw = url.get_secret_value() if isinstance(url, SecretStr) else url
    require_tls(raw, app_env)
    return _read_only_engine(raw)


@lru_cache(maxsize=8)
def session_factory(engine: Engine) -> sessionmaker[Session]:
    """The `SessionLocal` factory of an engine; `get_db()` opens one session per request."""
    return sessionmaker(bind=engine, expire_on_commit=False)


def advisory_key(namespace: str, value: str) -> TextClause:
    """SQL expression of the application advisory-lock key (DB-021).

    `hashtextextended('echowell:' || namespace || ':' || value, 0)`; the namespace is one of
    `resident` (resident_code), `session` (session_id), `device_alerts` (`all`) and `nightly`
    (facility-local date).
    """
    if namespace not in ADVISORY_NAMESPACES:
        raise ValueError(f"unknown advisory-lock namespace: {namespace}")
    return text("hashtextextended('echowell:' || :namespace || ':' || :value, 0)").bindparams(
        namespace=namespace, value=value
    )


def lock_xact(session: Session, namespace: str, value: str) -> None:
    """Take a transaction-scoped advisory lock, released at commit or rollback (D-62)."""
    key = advisory_key(namespace, value)
    session.execute(text(f"SELECT pg_advisory_xact_lock({key.text})"), key.compile().params)


def lock_residents(session: Session, resident_codes: Iterable[str]) -> None:
    """Lock several residents in ascending `resident_code` order, so callers cannot deadlock."""
    for code in sorted(set(resident_codes)):
        lock_xact(session, "resident", code)


@contextmanager
def migrator_connection(settings: Settings) -> Iterator[Connection]:
    """Connection for Alembic and the migrator CLI commands (TRD 20 §4.3, DB-028).

    Uses DATABASE_MIGRATION_URL and runs `MIGRATOR_SETUP` right after connecting, so objects are
    owned by `echowell_migrator` and `current_user` is that role (PGS-019). This is the only
    `SET ROLE` in the codebase (FEAT-008-FR-17).
    """
    engine = create_engine_for(settings.migration_url, app_env=settings.app_env)
    with engine.connect() as connection:
        for statement in MIGRATOR_SETUP:
            connection.execute(text(statement))
        # Session-level settings survive this commit; callers then begin their own transaction.
        connection.commit()
        try:
            yield connection
        finally:
            if connection.in_transaction():
                connection.rollback()
            for statement in _MIGRATOR_RESET:
                connection.execute(text(statement))
            connection.commit()


def _select_one(engine: Engine) -> bool:
    try:
        with engine.connect() as conn:
            return bool(conn.execute(text("SELECT 1")).scalar_one() == 1)
    except SQLAlchemyError:
        return False


def ping(engine: Engine, timeout_s: float = 2.0) -> bool:
    """True when `SELECT 1` succeeds within `timeout_s` seconds (API-110, API-111)."""
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        return pool.submit(_select_one, engine).result(timeout=timeout_s)
    except FutureTimeoutError:
        return False
    finally:
        pool.shutdown(wait=False)
