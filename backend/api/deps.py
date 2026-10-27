"""Shared request dependencies (TRD 05 API-010, API-011, API-016, API-017).

All are overridable through `app.dependency_overrides`. The authentication dependencies
(`get_current_user`, `require_roles`, `get_api_key`, `get_ingest_principal`) are added by FEAT-020.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from backend.core import db
from backend.core.config import Settings, get_settings
from backend.core.errors import InvalidQueryParameterError
from backend.schemas.common import Meta
from backend.services import meta_service

__all__ = [
    "Pagination",
    "check_date_range",
    "get_db",
    "get_engine",
    "get_meta",
    "get_pagination",
    "get_settings",
]


def get_engine(settings: Annotated[Settings, Depends(get_settings)]) -> Engine:
    """Engine of the app role (`DATABASE_URL`); never the migrator URL (ARC-015)."""
    return db.create_engine_for(settings.database_url, app_env=settings.app_env)


def get_db(engine: Annotated[Engine, Depends(get_engine)]) -> Iterator[Session]:
    """One session per request: commit on success, roll back on any exception, always close."""
    session = db.session_factory(engine)()
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


def get_meta(
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Meta:
    """The `meta` block of list, detail and analytics responses (API-057)."""
    return meta_service.get_meta(session, settings)


def check_date_range(start: date | None, end: date | None) -> None:
    """`from` later than `to` is 422 INVALID_QUERY_PARAMETER (API-093)."""
    if start is not None and end is not None and start > end:
        raise InvalidQueryParameterError("'from' must not be later than 'to'")
