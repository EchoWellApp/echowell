"""Validate API responses against the generated OpenAPI document (TRD 13 TST-061, TST-064;
TRD 19 OAS-006, OAS-017; FEAT-038-FR-11 c, d).

`check_response` is installed as an httpx response hook on the `api` client of
`tests/integration/api/conftest.py`, so every response an integration test receives is validated
with openapi-core, Problem bodies included, and a response that breaks its schema fails the test
that received it. Responses to paths the contract does not have (the test-only `/_test/*` routes,
unknown paths, wrong methods) are skipped.
"""

from __future__ import annotations

import functools
import json
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import httpx
import jsonschema
from openapi_core import Config, OpenAPI
from openapi_core.templating.paths.exceptions import PathError
from openapi_core.templating.responses.exceptions import ResponseNotFound
from openapi_core.testing import MockRequest, MockResponse

from backend.api.openapi import build_openapi
from backend.main import create_app
from tests.conftest import make_settings

# Universal responses, documented once in TRD 19 §4.2 rather than per operation (TRD 24 D-126):
# the body-limit middleware (413, 415), the default rate limit (429) and the global handlers
# (500, 503) can return them on any operation (API-095..API-097, API-104, API-139).
GLOBAL_STATUSES = (413, 415, 429, 500, 503)
META_FIELDS = {"facility_name", "facility_tz", "data_source_label", "as_of", "baseline_n",
               "cusum_h", "pipeline_profile"}  # fmt: skip


@functools.cache
def document() -> dict[str, Any]:
    return build_openapi(create_app(make_settings()))


@functools.cache
def openapi() -> OpenAPI:
    config = Config(
        extra_media_type_deserializers={
            "application/problem+json": json.loads,
            "text/csv": lambda body: body.decode("utf-8"),
        }
    )
    return OpenAPI.from_dict(document(), config=config)


class ContractViolationError(AssertionError):
    pass


def _declared_schema(request: MockRequest, status: int, media: str) -> dict[str, Any] | None:
    """The 2xx JSON schema the document declares for this call, resolved."""
    spec = document()
    path = request.path.removeprefix("/api/v1")
    for template, item in spec["paths"].items():
        pattern = template.split("/")
        parts = path.split("/")
        if len(pattern) != len(parts):
            continue
        if all(p == q or p.startswith("{") for p, q in zip(pattern, parts, strict=True)):
            operation = item.get(request.method.lower())
            if operation is None:
                return None
            response = operation["responses"].get(str(status), {})
            schema = response.get("content", {}).get(media, {}).get("schema")
            while schema is not None and "$ref" in schema:
                schema = spec["components"]["schemas"][schema["$ref"].split("/")[-1]]
            return schema
    return None


def _has_meta(schema: dict[str, Any]) -> bool:
    if "allOf" in schema:
        return any(_has_meta(part) for part in schema["allOf"]) or any(
            part.get("$ref", "").endswith("/PageMeta") for part in schema["allOf"]
        )
    return "meta" in schema.get("properties", {})


def check_response(response: httpx.Response) -> None:
    url = urlsplit(str(response.request.url))
    if not url.path.startswith("/api/v1/") or url.path.startswith("/api/v1/_test/"):
        return
    if url.path in ("/api/v1/openapi.json",) or url.path.startswith("/api/v1/docs"):
        return
    response.read()
    content_type = response.headers.get("content-type", "").split(";")[0].strip()
    request = MockRequest(
        "http://localhost:8000", response.request.method, url.path,
        args=dict(parse_qsl(url.query)), headers=dict(response.request.headers),
    )  # fmt: skip
    mock = MockResponse(
        response.content, status_code=response.status_code, headers=dict(response.headers),
        content_type=content_type,
    )  # fmt: skip
    try:
        openapi().validate_response(request, mock)
    except PathError:
        return
    except ResponseNotFound:
        if response.status_code not in GLOBAL_STATUSES:
            raise ContractViolationError(
                f"{request.method} {url.path}: undeclared status {response.status_code}"
            ) from None
        _check_problem(request, response, content_type)
    except Exception as exc:
        detail = getattr(exc, "__cause__", None) or exc
        raise ContractViolationError(
            f"{request.method} {url.path} -> {response.status_code} breaks the contract: "
            f"{detail}\n{response.text[:500]}"
        ) from exc
    if "x-request-id" not in response.headers:
        raise ContractViolationError(f"{request.method} {url.path}: no X-Request-ID (OAS-010)")
    _check_meta(request, response, content_type)


def _check_problem(request: MockRequest, response: httpx.Response, content_type: str) -> None:
    """Undeclared global statuses still carry a valid Problem (API-095..API-097)."""
    problem = document()["components"]["schemas"]["Problem"]
    if content_type != "application/problem+json":
        raise ContractViolationError(f"{request.method} {request.path}: {content_type}")
    resolver = {"components": document()["components"], **problem}
    try:
        jsonschema.validate(response.json(), resolver)
    except jsonschema.ValidationError as exc:
        raise ContractViolationError(f"{request.method} {request.path}: {exc.message}") from None


def _check_meta(request: MockRequest, response: httpx.Response, content_type: str) -> None:
    """`meta` with its seven fields exactly where the schema declares it (TST-064, OAS-017)."""
    if content_type != "application/json" or not 200 <= response.status_code < 300:
        return
    body = response.json()
    if not isinstance(body, dict):
        return
    schema = _declared_schema(request, response.status_code, content_type)
    if schema is None:
        return
    if _has_meta(schema):
        if set(body.get("meta") or {}) != META_FIELDS:
            raise ContractViolationError(f"{request.method} {request.path}: meta fields")
    elif "meta" in body:
        raise ContractViolationError(f"{request.method} {request.path}: undeclared meta")
