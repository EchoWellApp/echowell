"""FastAPI application factory (TRD 05 API-001, API-002, API-113; TRD 21 ENV-002).

Served by `uvicorn backend.main:app`; `app` is built on first access (PEP 562), so importing this
module has no side effects and never connects to the database (TRD 16 §8).
"""

from __future__ import annotations

from fastapi import FastAPI

from backend.api import health
from backend.core.config import Settings, ensure_valid, load_settings_or_exit

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Validate settings (exit code 1 on failure), then mount every router under /api/v1."""
    if settings is None:
        settings = load_settings_or_exit()
    else:
        ensure_valid(settings)
    app = FastAPI(
        title="EchoWell API",
        version="0.1.0",
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=None if settings.app_env == "production" else f"{API_PREFIX}/docs",
        swagger_ui_oauth2_redirect_url=f"{API_PREFIX}/docs/oauth2-redirect",
        redoc_url=None,
    )
    app.include_router(health.router, prefix=API_PREFIX)
    return app


def __getattr__(name: str) -> FastAPI:
    if name == "app":
        return create_app()
    raise AttributeError(name)
