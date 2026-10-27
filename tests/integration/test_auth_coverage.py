"""Every route declares its auth dependency (TRD 12 SEC-042; FEAT-021-FR-12, FEAT-021-AC-01).

Only `GET /health`, `POST /auth/login`, the OpenAPI document and (outside production) `/docs` may be
anonymous. Every other route must depend on `authorize("<METHOD> <path>")` for its own method and
path, so a route cannot borrow another endpoint's row of the matrix.
"""

from __future__ import annotations

from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from backend.api.deps import Principal, authorize
from backend.main import create_app
from tests.conftest import make_settings

pytestmark = pytest.mark.integration

PREFIX = "/api/v1"
ANONYMOUS_API_ROUTES = {"GET /health", "POST /auth/login"}
ANONYMOUS_DOC_PATHS = {f"{PREFIX}/openapi.json", f"{PREFIX}/docs", f"{PREFIX}/docs/oauth2-redirect"}


def _authorize_keys(dependant: Dependant) -> set[str]:
    keys = set()
    for sub in dependant.dependencies:
        name = getattr(sub.call, "__name__", "")
        if name.startswith("authorize_"):
            keys.add(name.removeprefix("authorize_"))
        keys |= _authorize_keys(sub)
    return keys


def offenders(app: FastAPI) -> list[str]:
    """Routes that are neither allowed to be anonymous nor guarded by their own matrix row."""
    found = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            if getattr(route, "path", "") not in ANONYMOUS_DOC_PATHS:
                found.append(f"{getattr(route, 'path', route)} (not an API route)")
            continue
        for method in sorted(route.methods):
            key = f"{method} {route.path.removeprefix(PREFIX)}"
            if key in ANONYMOUS_API_ROUTES:
                continue
            if _authorize_keys(route.dependant) != {key}:
                found.append(key)
    return found


@pytest.mark.req("SEC-042", "FR-212", "FEAT-021-AC-01", "FEAT-020-FR-17")
def test_every_route_has_its_auth_dependency() -> None:
    assert offenders(create_app(make_settings())) == []


@pytest.mark.req("SEC-042", "FEAT-021-AC-01")
def test_production_has_no_docs_route() -> None:
    remote = "postgresql+psycopg://u:p@db.example.org/x?sslmode=require"
    settings = make_settings(
        app_env="production", cors_origins="https://app.example.org", database_url=remote,
        database_readonly_url=remote, jwt_secret="Zq8vN3xK1pL7wR4tY6uI0oP2aS5dF9gHk3Lm",  # noqa: S106
        pipeline_profile="production", facility_name="Synthetic Facility", log_format="json",
    )  # fmt: skip
    paths = {getattr(r, "path", "") for r in create_app(settings).routes}
    assert f"{PREFIX}/docs" not in paths
    assert f"{PREFIX}/openapi.json" in paths


@pytest.mark.req("SEC-042", "FEAT-021-AC-01")
def test_a_route_without_auth_is_detected() -> None:
    app = create_app(make_settings())

    @app.get(f"{PREFIX}/residents")
    def unguarded() -> dict[str, str]:
        return {}

    @app.get(f"{PREFIX}/devices")
    def borrowed(
        _: Annotated[Principal, Depends(authorize("GET /residents"))],
    ) -> dict[str, str]:
        return {}

    assert offenders(app) == ["GET /residents", "GET /devices"]
