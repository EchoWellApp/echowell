"""Rate limits with slowapi and in-memory storage (TRD 05 API-102, API-103; TRD 12 SEC-090..SEC-093;
FEAT-022).

- `POST /auth/login`: RATE_LIMIT_LOGIN per client IP (left-most `X-Forwarded-For`).
- `POST /sessions`, `POST /ingest`: RATE_LIMIT_INGEST per API-key hash or admin user id.
- every other authenticated endpoint: 300/minute per user id (`DEFAULT_LIMIT`).
- `GET /health` and the OpenAPI document are exempt (API-112).

Limits read the active settings from `app.state.settings`, so tests can choose them per app.
The test suite empties the storage before every test (`limiter.reset()`, TRD 24 D-74).
"""

from __future__ import annotations

import hashlib

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from backend.core.config import Settings

DEFAULT_LIMIT = "300/minute"


def _settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def client_address(request: Request) -> str:
    """Left-most `X-Forwarded-For` (set by the Railway edge), else the socket peer (API-103)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and forwarded.split(",", 1)[0].strip():
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def _bearer(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    return token.strip() if scheme.lower() == "bearer" and token.strip() else None


def user_key(request: Request) -> str:
    """User id from a verifying token; otherwise the client address."""
    from backend.services.auth_service import user_id_from_token

    token = _bearer(request)
    user_id = user_id_from_token(token, _settings(request)) if token else None
    return f"user:{user_id}" if user_id else f"ip:{client_address(request)}"


def ingest_key(request: Request) -> str:
    """API-key hash, else the admin user id (SEC-090)."""
    raw = request.headers.get("x-api-key")
    if raw:
        return "key:" + hashlib.sha256(raw.encode()).hexdigest()
    return user_key(request)


def login_key(request: Request) -> str:
    return "login:" + client_address(request)


def login_limit(key: str) -> str:
    return _current_settings.rate_limit_login


def ingest_limit(key: str) -> str:
    return _current_settings.rate_limit_ingest


limiter = Limiter(key_func=user_key, default_limits=[DEFAULT_LIMIT], storage_uri="memory://")
_current_settings: Settings


def configure(settings: Settings) -> None:
    """Bind the limits of the app being created (one app per process outside tests)."""
    global _current_settings
    _current_settings = settings


def retry_after(exc: RateLimitExceeded) -> int:
    """Seconds until the limit window resets (API-098)."""
    limit = getattr(exc, "limit", None)
    item = getattr(limit, "limit", None)
    if item is None:
        return 60
    return max(1, int(item.get_expiry()))


__all__ = [
    "DEFAULT_LIMIT",
    "RateLimitExceeded",
    "client_address",
    "configure",
    "ingest_key",
    "ingest_limit",
    "limiter",
    "login_key",
    "login_limit",
    "retry_after",
    "user_key",
]
