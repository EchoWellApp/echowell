"""SQLAlchemy 2.0 ORM models (TRD 23 §4.6); the Python enums of DME-003 are added with the tables
(FEAT-009)."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base whose metadata Alembic compares against (TRD 06)."""
