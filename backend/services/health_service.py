"""Health service for E-01 `GET /api/v1/health` (TRD 05 API-110..API-112; checkpoint 1 Q-1).

No authentication, no rate limit and no audit row; the response reveals only the `Health` fields.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Engine

from backend.core.config import Settings
from backend.core.db import ping
from backend.schemas.health import Health


def get_health(settings: Settings, engine: Engine) -> Health:
    """`SELECT 1` within 2 s: `ok`/`ok`, otherwise `degraded`/`unavailable` (API-110, API-111)."""
    database_ok = ping(engine, timeout_s=2.0)
    return Health(
        status="ok" if database_ok else "degraded",
        database="ok" if database_ok else "unavailable",
        version=settings.git_sha,
        time=datetime.now(UTC).replace(microsecond=0),
    )
