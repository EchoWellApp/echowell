"""The OpenAPI 3.1 document of TRD 19 (OAS-002..OAS-018; FEAT-038).

FastAPI generates paths and schemas from the routers and DTOs; `build_openapi` then applies the
TRD 19 conventions: paths relative to the `/api/v1` servers, per-operation security from the role
matrix (`permissions.PERMISSIONS`), shared `components/responses`, `headers` and `parameters`,
`X-Request-ID` on every response, the ingest request bodies, and no FastAPI validation schemas.
The committed `docs/api_reference/openapi.json` is this document printed by
`python -m backend.cli export-openapi` (D-89).

The JSON examples of TRD 19 §4.3 live in `openapi_examples.json` and are attached as media-type
`examples` (OAS-015; FEAT-038-FR-10); an example of a shared error response is attached to an
inline copy of that response, so the shared component stays example-free.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import TypeAdapter

from backend.api.permissions import INGEST_WRITE, PERMISSIONS
from backend.schemas.common import DayStatus, PageMeta, Problem, ProcessedStatus
from backend.schemas.ingest import IngestBatchRequest, IngestRecord

API_PREFIX = "/api/v1"
TITLE = "EchoWell API"
VERSION = "0.1.0"
DESCRIPTION = (
    "EchoWell research system API. Detects a change in a resident's voice measurements relative to "
    "their own frozen baseline; a prompt to check in, not a diagnosis. No audio endpoints exist.\n"
)
SERVERS = [
    {"url": "http://localhost:8000/api/v1", "description": "local (docker-compose)"},
    {
        "url": "/api/v1",
        "description": "relative to the deployed Railway API origin (staging, production)",
    },
]
TAGS = [
    {"name": name}
    for name in (
        "health", "auth", "ingest", "residents", "scores", "alerts", "devices", "analytics",
        "pipeline",
    )
] + [
    {"name": "admissions", "description": "Future / experimental study arm"},
    {"name": "users"},
    {"name": "config"},
]  # fmt: skip

_PROBLEM = {"application/problem+json": {"schema": {"$ref": "#/components/schemas/Problem"}}}
_REQUEST_ID = {"X-Request-ID": {"$ref": "#/components/headers/XRequestID"}}
ERROR_RESPONSES: dict[str, tuple[str, str]] = {
    "401": ("Unauthorized", "NOT_AUTHENTICATED | INVALID_CREDENTIALS | TOKEN_EXPIRED | "
                            "TOKEN_INVALID | API_KEY_INVALID"),
    "403": ("Forbidden", "FORBIDDEN | DEVICE_KEY_MISMATCH"),
    "404": ("NotFound", "*_NOT_FOUND"),
    "409": ("Conflict", "ALERT_CLOSED | EMAIL_ALREADY_EXISTS | LAST_ADMIN | "
                        "PIPELINE_RUN_IN_PROGRESS"),
    "413": ("PayloadTooLarge", "PAYLOAD_TOO_LARGE"),
    "415": ("UnsupportedMediaType", "UNSUPPORTED_MEDIA_TYPE"),
    "422": ("Unprocessable", "VALIDATION_ERROR and the other 422 codes of TRD 05 §4.7"),
    "429": ("TooManyRequests", "RATE_LIMITED | ACCOUNT_TEMPORARILY_LOCKED"),
}  # fmt: skip
SHARED_PARAMETERS: dict[tuple[str, str], str] = {
    ("query", "limit"): "Limit",
    ("query", "offset"): "Offset",
    ("query", "from"): "FromDate",
    ("query", "to"): "ToDate",
    ("path", "id"): "IdPath",
    ("path", "resident_code"): "ResidentCodePath",
}
EXPERIMENTAL_PATHS = ("/admissions", "/facility/reference-ranges")
FASTAPI_SCHEMAS = ("HTTPValidationError", "ValidationError")
EXAMPLES_FILE = Path(__file__).with_name("openapi_examples.json")


def _components() -> dict[str, Any]:
    responses: dict[str, Any] = {}
    for _, (name, description) in ERROR_RESPONSES.items():
        headers = dict(_REQUEST_ID)
        if name == "TooManyRequests":
            headers["Retry-After"] = {"$ref": "#/components/headers/RetryAfter"}
        responses[name] = {"description": description, "headers": headers, "content": _PROBLEM}
    return {
        "securitySchemes": {
            "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
            "apiKeyAuth": {"type": "apiKey", "in": "header", "name": "X-API-Key"},
        },
        "headers": {
            "XRequestID": {"description": "Request correlation ID", "schema": {"type": "string"}},
            "XExperimental": {
                "description": "Future / experimental study arm",
                "schema": {"type": "string", "const": "true"},
            },
            "RetryAfter": {"description": "Seconds to wait", "schema": {"type": "integer"}},
        },
        "parameters": {
            "Limit": {
                "name": "limit",
                "in": "query",
                "schema": {"type": "integer", "minimum": 1, "maximum": 500, "default": 50},
            },
            "Offset": {
                "name": "offset",
                "in": "query",
                "schema": {"type": "integer", "minimum": 0, "default": 0},
            },
            "FromDate": {
                "name": "from",
                "in": "query",
                "schema": {"type": "string", "format": "date"},
            },
            "ToDate": {"name": "to", "in": "query", "schema": {"type": "string", "format": "date"}},
            "IdPath": {
                "name": "id",
                "in": "path",
                "required": True,
                "schema": {"type": "string", "format": "uuid"},
            },
            "ResidentCodePath": {
                "name": "resident_code",
                "in": "path",
                "required": True,
                "schema": {"$ref": "#/components/schemas/ResidentCode"},
            },
        },
        "responses": responses,
    }


def _security(method: str, path: str) -> list[dict[str, list[str]]] | None:
    """The TRD 19 security of an operation, from its matrix row (OAS-013)."""
    access = PERMISSIONS[f"{method.upper()} {path}"]
    if access.anonymous:
        return None
    bearer: dict[str, list[str]] = {"bearerAuth": []}
    key: dict[str, list[str]] = {"apiKeyAuth": []}
    if access.roles and access.api_key_scope:
        return [key, bearer] if access.api_key_scope == INGEST_WRITE else [bearer, key]
    return [bearer] if access.roles else [key]


def _parameters(parameters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for parameter in parameters:
        shared = SHARED_PARAMETERS.get((parameter["in"], parameter["name"]))
        if shared is not None:
            out.append({"$ref": f"#/components/parameters/{shared}"})
            continue
        parameter = {k: v for k, v in parameter.items() if k != "description" or v}
        schema = parameter.get("schema", {})
        options = schema.get("anyOf", [])
        if len(options) == 2 and {"type": "null"} in options:
            # `X | None = None`: an omitted query parameter, never a null one.
            extra = {k: v for k, v in schema.items() if k != "anyOf"}
            parameter["schema"] = {**next(o for o in options if o != {"type": "null"}), **extra}
        out.append(parameter)
    return out


def _responses(path: str, responses: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for status, response in responses.items():
        if status in ERROR_RESPONSES:
            if response.get("description") == "Validation Error":
                continue  # FastAPI's automatic 422; kept only where the router declares it
            out[status] = {"$ref": f"#/components/responses/{ERROR_RESPONSES[status][0]}"}
            continue
        response = copy.deepcopy(response)
        headers = dict(_REQUEST_ID)
        if path.startswith(EXPERIMENTAL_PATHS):
            headers["X-EchoWell-Experimental"] = {"$ref": "#/components/headers/XExperimental"}
        response["headers"] = headers
        if not response.get("content"):
            response.pop("content", None)
        out[status] = response
    return out


BOUNDS = ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum")


def _request_body(body: dict[str, Any]) -> dict[str, Any]:
    """An optional body (`X | None = Body(None)`) is `required: false` with the plain schema."""
    for media in body.get("content", {}).values():
        options = media.get("schema", {}).get("anyOf", [])
        if len(options) == 2 and {"type": "null"} in options:
            media["schema"] = next(o for o in options if o != {"type": "null"})
            body["required"] = False
    return body


def _tidy(node: Any) -> Any:
    """Drop Pydantic's generated `title` keywords, which add nothing to the contract, and write
    whole-number bounds as integers (FastAPI emits `168.0`)."""
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            if key == "title" and isinstance(value, str):
                continue
            if key in BOUNDS and isinstance(value, float) and value.is_integer():
                value = int(value)
            out[key] = _tidy(value)
        return out
    if isinstance(node, list):
        return [_tidy(v) for v in node]
    return node


# Schemas no route declares: the ingest bodies the handlers read raw (API-031), `Problem` of the
# shared error responses, `PageMeta` of the list schemas, and two database enums (OAS-007).
EXTRA_SCHEMAS: tuple[Any, ...] = (
    IngestRecord, IngestBatchRequest, Problem, PageMeta, ProcessedStatus, DayStatus,
)  # fmt: skip
PAGE_FIELDS = ("meta", "total", "limit", "offset")


def _extra_schemas() -> dict[str, Any]:
    defs: dict[str, Any] = {}
    for item in EXTRA_SCHEMAS:
        schema = TypeAdapter(item).json_schema(ref_template="#/components/schemas/{model}")
        defs.update(schema.pop("$defs", {}))
        if "$ref" not in schema:
            defs[item.__name__] = schema
    return defs


def _page_lists(schemas: dict[str, Any]) -> None:
    """A paged list is `allOf: [PageMeta, {items, ...}]` as in TRD 19 §4.5 (Pydantic flattens
    the inheritance)."""
    for name, schema in schemas.items():
        properties = schema.get("properties", {})
        if name == "PageMeta" or not set(PAGE_FIELDS) <= set(properties):
            continue
        own = {k: v for k, v in properties.items() if k not in PAGE_FIELDS}
        required = [k for k in schema.get("required", []) if k not in PAGE_FIELDS]
        schemas[name] = {
            "allOf": [
                {"$ref": "#/components/schemas/PageMeta"},
                {"type": "object", "required": required, "properties": own},
            ]
        }


def build_openapi(app: FastAPI) -> dict[str, Any]:
    """The TRD 19 document of `app` (OAS-002)."""
    generated = get_openapi(
        title=TITLE, version=VERSION, openapi_version="3.1.0", description=DESCRIPTION,
        routes=app.routes, servers=SERVERS, tags=TAGS,
    )  # fmt: skip
    paths: dict[str, Any] = {}
    for full_path, operations in generated.get("paths", {}).items():
        if not full_path.startswith(API_PREFIX):
            continue
        path = full_path.removeprefix(API_PREFIX)
        if path.startswith("/_test/"):
            continue
        for method, operation in operations.items():
            operation.pop("security", None)
            security = _security(method, path)
            if security is not None:
                operation["security"] = security
            if "parameters" in operation:
                operation["parameters"] = _parameters(operation["parameters"])
            operation["responses"] = _responses(path, operation["responses"])
            if "requestBody" in operation:
                operation["requestBody"] = _request_body(operation["requestBody"])
            if not operation.get("description"):
                operation.pop("description", None)
        paths[path] = operations
    schemas = {
        name: schema
        for name, schema in generated.get("components", {}).get("schemas", {}).items()
        if name not in FASTAPI_SCHEMAS
    }
    schemas.update(_extra_schemas())
    _page_lists(schemas)
    document = {
        "openapi": "3.1.0",
        "info": generated["info"],
        "servers": SERVERS,
        "security": [],
        "tags": TAGS,
        "paths": _tidy(paths),
        "components": {**_components(), "schemas": _tidy(schemas)},
    }
    _attach_examples(document)
    return document


def examples() -> list[dict[str, Any]]:
    """The TRD 19 §4.3 examples: `endpoint`, `method`, `path`, `target` (`request` or a status),
    `name`, `value`, and `completed` where the TRD abbreviates the example."""
    loaded: list[dict[str, Any]] = json.loads(EXAMPLES_FILE.read_text(encoding="utf-8"))
    return loaded


def _attach_examples(document: dict[str, Any]) -> None:
    shared = document["components"]["responses"]
    for example in examples():
        operation = document["paths"][example["path"]][example["method"].lower()]
        if example["target"] == "request":
            holder = operation["requestBody"]
        else:
            holder = operation["responses"][example["target"]]
            if "$ref" in holder:
                holder = copy.deepcopy(shared[holder["$ref"].split("/")[-1]])
                operation["responses"][example["target"]] = holder
        media = next(iter(holder["content"].values()))
        media.setdefault("examples", {})[example["name"]] = {
            "summary": f"TRD 19 {example['endpoint']}", "value": example["value"],
        }  # fmt: skip


def install(app: FastAPI) -> None:
    """Serve `build_openapi(app)` at `/api/v1/openapi.json` (built once per app)."""

    def openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            app.openapi_schema = build_openapi(app)
        return app.openapi_schema

    app.openapi = openapi  # type: ignore[method-assign]
