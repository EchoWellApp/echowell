"""FastAPI application factory (TRD 05 API-001, API-002, API-113; TRD 21 ENV-002).

Served by `uvicorn backend.main:app`; `app` is built on first access (PEP 562), so importing this
module has no side effects and never connects to the database (TRD 16 §8).
"""

from __future__ import annotations

import json

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.middleware import SlowAPIASGIMiddleware

from backend.api import auth, health
from backend.api.deps import AuditWriter, client_ip
from backend.core import db, rate_limit
from backend.core.config import DEPLOYED_ENVS, Settings, ensure_valid, load_settings_or_exit
from backend.core.error_handlers import install_handlers, problem_response
from backend.core.logging import REQUEST_ID_HEADER, configure_logging
from backend.core.middleware import BodyLimitMiddleware, RequestContextMiddleware
from backend.core.security import normalise_email
from backend.models import ActorType
from backend.services import audit_service
from backend.services.audit_service import AuditAction

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
    app.state.settings = settings
    rate_limit.configure(settings)
    app.state.limiter = rate_limit.limiter
    install_handlers(app)
    app.add_exception_handler(rate_limit.RateLimitExceeded, _rate_limited)
    # Added innermost first, so requests pass RequestContext -> BodyLimit -> CORS -> rate limiter
    # -> routes (TRD 05 §4.11; API-101, API-102, API-104, API-105).
    app.add_middleware(SlowAPIASGIMiddleware)
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
    app.include_router(auth.router, prefix=API_PREFIX)
    return app


def _audit_writer(request: Request) -> AuditWriter:
    configured: AuditWriter | None = getattr(request.app.state, "audit_writer", None)
    if configured is not None:
        return configured
    settings: Settings = request.app.state.settings
    engine = db.create_engine_for(settings.database_url, app_env=settings.app_env)
    return AuditWriter(lambda **kwargs: audit_service.record_committed(engine, **kwargs))


async def _rate_limited(request: Request, exc: Exception) -> JSONResponse:
    """429 RATE_LIMITED with Retry-After (API-098); a limited login is audited (SEC-093)."""
    assert isinstance(exc, rate_limit.RateLimitExceeded)  # noqa: S101 - handler registration
    if request.url.path == f"{API_PREFIX}/auth/login":
        try:
            email = json.loads(await request.body()).get("email", "")
        except (ValueError, AttributeError):
            email = ""
        _audit_writer(request).committed(
            action=AuditAction.AUTH_LOGIN_FAILED, actor_type=ActorType.SYSTEM, actor_id=None,
            entity_type="user", entity_id=None,
            details={"email": normalise_email(str(email)), "reason": "rate_limited"},
            ip=client_ip(request),
        )  # fmt: skip
    return problem_response(
        "RATE_LIMITED", "Too many requests. Try again later.",
        headers={"Retry-After": str(rate_limit.retry_after(exc))},
    )  # fmt: skip


def __getattr__(name: str) -> FastAPI:
    if name == "app":
        return create_app()
    raise AttributeError(name)
