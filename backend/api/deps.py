"""Shared request dependencies (TRD 05 API-010, API-011, API-016, API-017).

All are overridable through `app.dependency_overrides`. The authentication dependencies
(`get_current_user`, `require_roles`, `get_api_key`, `get_ingest_principal`) are added by FEAT-020.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from backend.core import db
from backend.core.config import Settings, get_settings
from backend.core.errors import InvalidQueryParameterError

__all__ = ["Pagination", "get_db", "get_engine", "get_pagination", "get_settings"]


def get_engine(settings: Annotated[Settings, Depends(get_settings)]) -> Engine:
    """Engine of the app role (`DATABASE_URL`); never the migrator URL (ARC-015)."""
    return db.get_engine(settings.database_url)


def get_db(engine: Annotated[Engine, Depends(get_engine)]) -> Iterator[Session]:
    """One session per request: commit on success, roll back on any exception, always close."""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@dataclass(frozen=True)
class Pagination:
    limit: int
    offset: int


def get_pagination(limit: int = 50, offset: int = 0) -> Pagination:
    """`limit` 1..500 (default 50), `offset` >= 0 (default 0); else 422 INVALID_QUERY_PARAMETER."""
    if not 1 <= limit <= 500:
        raise InvalidQueryParameterError("limit must be between 1 and 500")
    if offset < 0:
        raise InvalidQueryParameterError("offset must be 0 or greater")
    return Pagination(limit=limit, offset=offset)
