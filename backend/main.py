"""FastAPI application factory (TRD 05 API-001, API-002, API-113; TRD 21 ENV-002).

Served by `uvicorn backend.main:app`; `app` is built on first access (PEP 562), so importing this
module has no side effects and never connects to the database (TRD 16 §8).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import health
from backend.core.config import DEPLOYED_ENVS, Settings, ensure_valid, load_settings_or_exit
from backend.core.errors import install_handlers
from backend.core.logging import REQUEST_ID_HEADER, configure_logging
from backend.core.middleware import BodyLimitMiddleware, RequestContextMiddleware

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Validate settings (exit code 1 on failure), configure logging, install middleware and
    error handlers, then mount every router under /api/v1 (TRD 05 §4.11 request lifecycle)."""
    if settings is None:
        settings = load_settings_or_exit()
    else:
        ensure_valid(settings)
    configure_logging(settings.log_level, settings.log_format, settings.app_env, settings.git_sha)
    app = FastAPI(
        title="EchoWell API",
        version="0.1.0",
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=None if settings.app_env == "production" else f"{API_PREFIX}/docs",
        swagger_ui_oauth2_redirect_url=f"{API_PREFIX}/docs/oauth2-redirect",
        redoc_url=None,
    )
    install_handlers(app)
    # Added innermost first, so requests pass RequestContext -> BodyLimit -> CORS -> routes
    # (API-101, API-104, API-105).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=settings.cors_origin_regex or None,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", REQUEST_ID_HEADER],
        expose_headers=[REQUEST_ID_HEADER, "Retry-After", "X-EchoWell-Experimental"],
        max_age=600,
    )
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(RequestContextMiddleware, hsts=settings.app_env in DEPLOYED_ENVS)
    app.include_router(health.router, prefix=API_PREFIX)
    return app


def __getattr__(name: str) -> FastAPI:
    if name == "app":
        return create_app()
    raise AttributeError(name)
