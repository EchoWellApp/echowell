"""The one engine factory and the database probe (TRD 05 API-125, API-110; TRD 01 §8).

Engines are created lazily, never at import time, so the OpenAPI export needs no database
(TRD 16 §8). URLs use the `postgresql+psycopg://` scheme (ENV-014).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from functools import lru_cache

from pydantic import SecretStr
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError


@lru_cache(maxsize=4)
def _engine(url: str) -> Engine:
    return create_engine(
        url,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={"prepare_threshold": None, "connect_timeout": 5},
    )


def get_engine(url: SecretStr) -> Engine:
    """Return the shared engine for `url` (app, readonly, Alembic and CLI engines, API-125)."""
    return _engine(url.get_secret_value())


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
