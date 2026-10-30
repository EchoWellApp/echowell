"""The OpenAPI contract (TRD 19 OAS-002..OAS-018; TRD 13 TST-060, TST-062; FEAT-038).

The generated document must equal the committed `docs/api_reference/openapi.json` and agree with
the TRD 19 §4.5 skeleton (`tests/fixtures/trd19_openapi_skeleton.yaml`) in paths, methods,
operation ids, security, status codes, parameters, request bodies and, for every skeleton schema,
property names, types, `required` lists and enum values. The comparison is semantic: `$ref`s are
resolved, `allOf` is merged, `anyOf [X, null]` equals `type: [X, "null"]` (FEAT-038-FR-06) and a
one-value `const` equals a one-value `enum`. The generated document may name nested objects that
the skeleton writes inline (`UserRef`, `Period`, ...).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi.testclient import TestClient
from openapi_spec_validator import validate

from backend.api.openapi import build_openapi
from backend.main import create_app
from tests.conftest import make_settings

pytestmark = pytest.mark.contract

ROOT = Path(__file__).resolve().parents[2]
COMMITTED = ROOT / "docs" / "api_reference" / "openapi.json"
SKELETON = ROOT / "tests" / "fixtures" / "trd19_openapi_skeleton.yaml"
METHODS = ("get", "post", "put", "patch", "delete")


@pytest.fixture(scope="module")
def generated() -> dict[str, Any]:
    return build_openapi(create_app(make_settings()))


@pytest.fixture(scope="module")
def skeleton() -> dict[str, Any]:
    document: dict[str, Any] = yaml.safe_load(SKELETON.read_text(encoding="utf-8"))
    return document


class Normaliser:
    """Reduces a schema to the facts the contract fixes (FEAT-038-FR-05)."""

    def __init__(self, document: dict[str, Any]) -> None:
        self.document = document

    def resolve(self, node: dict[str, Any]) -> dict[str, Any]:
        while "$ref" in node:
            target: Any = self.document
            for part in node["$ref"].removeprefix("#/").split("/"):
                target = target[part]
            node = target
        return node

    def __call__(self, node: dict[str, Any], depth: int = 0) -> Any:
        node = self.resolve(node)
        if depth > 6:
            return "..."
        if "allOf" in node:
            merged: dict[str, Any] = {"type": "object", "properties": {}, "required": []}
            for part in node["allOf"]:
                part = self.resolve(part)
                merged["properties"].update(part.get("properties", {}))
                merged["required"] += part.get("required", [])
            node = merged
        for key in ("anyOf", "oneOf"):
            if key in node:
                options = [self(o, depth + 1) for o in node[key]]
                if "null" in options:
                    options.remove("null")
                    inner = (
                        options[0] if len(options) == 1 else ("union", sorted(map(str, options)))
                    )
                    return ("nullable", inner)
                return ("union", sorted(map(str, options)))
        types = node.get("type")
        if isinstance(types, list):
            rest = [t for t in types if t != "null"]
            stripped = {**node, "type": rest[0] if len(rest) == 1 else rest}
            if "enum" in stripped:
                stripped["enum"] = [v for v in stripped["enum"] if v is not None]
            inner = self(stripped, depth + 1)
            return ("nullable", inner) if "null" in types else inner
        if "const" in node:
            return ("enum", (str(node["const"]),))
        if "enum" in node:
            return ("enum", tuple(sorted(str(v) for v in node["enum"])))
        if types == "array":
            return ("array", self(node.get("items", {}), depth + 1))
        if types == "object" or "properties" in node:
            return (
                "object",
                tuple(sorted(node.get("required", []))),
                tuple(
                    sorted(
                        (k, str(self(v, depth + 1))) for k, v in node.get("properties", {}).items()
                    )
                ),
            )
        return types or "any"


def _operations(document: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (method, path): operation
        for path, item in document["paths"].items()
        for method, operation in item.items()
        if method in METHODS
    }


def _parameters(document: dict[str, Any], operation: dict[str, Any]) -> list[tuple[Any, ...]]:
    normalise = Normaliser(document)
    out = []
    for parameter in operation.get("parameters", []):
        parameter = normalise.resolve(parameter)
        out.append(
            (parameter["in"], parameter["name"], bool(parameter.get("required")),
             str(normalise(parameter.get("schema", {}))))
        )  # fmt: skip
    return sorted(out)


def _body(document: dict[str, Any], operation: dict[str, Any]) -> Any:
    body = operation.get("requestBody")
    if body is None:
        return None
    normalise = Normaliser(document)
    content = {
        media: str(normalise(spec.get("schema", {}))) for media, spec in body["content"].items()
    }
    return bool(body.get("required")), content


def _responses(document: dict[str, Any], operation: dict[str, Any]) -> dict[str, Any]:
    normalise = Normaliser(document)
    out = {}
    for status, response in operation["responses"].items():
        response = normalise.resolve(response)
        content = {
            media: str(normalise(spec.get("schema", {})))
            for media, spec in response.get("content", {}).items()
        }
        out[str(status)] = (content, sorted(response.get("headers", {})))
    return out


@pytest.mark.req("TST-060", "OAS-005", "D-51", "D-89", "FEAT-038-AC-01", "FEAT-038-FR-03")
def test_generated_equals_committed(generated: dict[str, Any]) -> None:
    """Regenerate with `python -m backend.cli export-openapi > docs/api_reference/openapi.json`."""
    committed = json.loads(COMMITTED.read_text(encoding="utf-8"))
    assert generated == committed


@pytest.mark.req("AC-OAS-01", "FEAT-038-AC-02")
def test_documents_are_valid_openapi_31(
    generated: dict[str, Any], skeleton: dict[str, Any]
) -> None:
    validate(generated)
    validate(skeleton)
    assert generated["openapi"] == skeleton["openapi"] == "3.1.0"


@pytest.mark.req("OAS-002", "FEAT-038-FR-02")
def test_document_header(generated: dict[str, Any], skeleton: dict[str, Any]) -> None:
    assert generated["info"]["title"] == "EchoWell API"
    assert generated["info"]["version"] == "0.1.0"
    assert [s["url"] for s in generated["servers"]] == [s["url"] for s in skeleton["servers"]]
    assert generated["security"] == []
    assert [t["name"] for t in generated["tags"]] == [t["name"] for t in skeleton["tags"]]


@pytest.mark.req("TST-062", "OAS-003", "OAS-020", "OAS-001", "FEAT-038-AC-03", "FEAT-038-FR-01",
                 "FEAT-038-FR-04")  # fmt: skip
def test_path_set(generated: dict[str, Any], skeleton: dict[str, Any]) -> None:
    assert set(generated["paths"]) == set(skeleton["paths"])
    assert set(_operations(generated)) == set(_operations(skeleton))
    assert "/alerts/{id}/acknowledge" not in generated["paths"]
    app = create_app(make_settings())
    mounted = {r.path for r in app.routes if getattr(r, "include_in_schema", False)}  # type: ignore[attr-defined]
    assert mounted == {f"/api/v1{p}" for p in skeleton["paths"]}


@pytest.mark.req("OAS-003", "OAS-013", "OAS-018", "FEAT-038-FR-04", "FEAT-038-FR-07",
                 "FEAT-038-FR-08")  # fmt: skip
def test_operations_match_skeleton(generated: dict[str, Any], skeleton: dict[str, Any]) -> None:
    mine, theirs = _operations(generated), _operations(skeleton)
    for key, expected in theirs.items():
        actual = mine[key]
        assert actual.get("operationId") == expected.get("operationId"), key
        assert actual.get("tags") == expected.get("tags"), key
        assert actual.get("security") == expected.get("security"), key
        assert _parameters(generated, actual) == _parameters(skeleton, expected), key
        assert _body(generated, actual) == _body(skeleton, expected), key
        assert _responses(generated, actual) == _responses(skeleton, expected), key


@pytest.mark.req("OAS-004", "OAS-007", "OAS-008", "OAS-012", "FEAT-038-FR-05", "FEAT-038-FR-06")
def test_schemas_match_skeleton(generated: dict[str, Any], skeleton: dict[str, Any]) -> None:
    mine, theirs = Normaliser(generated), Normaliser(skeleton)
    schemas = generated["components"]["schemas"]
    for name, expected in skeleton["components"]["schemas"].items():
        assert name in schemas, name
        assert mine(schemas[name]) == theirs(expected), name


@pytest.mark.req("OAS-009", "OAS-010", "OAS-013", "FEAT-038-FR-06", "FEAT-038-FR-07")
def test_shared_components(generated: dict[str, Any], skeleton: dict[str, Any]) -> None:
    components, expected = generated["components"], skeleton["components"]
    assert components["securitySchemes"] == expected["securitySchemes"]
    assert components["responses"].keys() == expected["responses"].keys()
    for name, response in components["responses"].items():
        assert list(response["content"]) == ["application/problem+json"], name
        assert "X-Request-ID" in response["headers"], name
    for (method, path), operation in _operations(generated).items():
        for status, response in operation["responses"].items():
            response = Normaliser(generated).resolve(response)
            assert "X-Request-ID" in response.get("headers", {}), (method, path, status)
            if not str(status).startswith("2") and path != "/health":  # 503 is a Health body
                assert list(response["content"]) == ["application/problem+json"]


def _property_names(node: Any) -> set[str]:
    names: set[str] = set()
    if isinstance(node, dict):
        names |= set(node.get("properties", {}))
        for value in node.values():
            names |= _property_names(value)
    elif isinstance(node, list):
        for value in node:
            names |= _property_names(value)
    return names


@pytest.mark.req("OAS-016", "AC-OAS-07", "FR-015", "FEAT-038-AC-07", "FEAT-038-FR-09")
def test_no_audio_or_identity_properties(generated: dict[str, Any]) -> None:
    names = _property_names(generated)
    assert {n for n in names if "audio" in n.lower()} == {"audio_quality_flag"}
    forbidden = {"name", "first_name", "last_name", "full_name", "dob", "date_of_birth",
                 "birth_date", "audio_url", "recording", "wav"}  # fmt: skip
    assert not names & forbidden
    assert not [p for p in generated["paths"] if "audio" in p or "recording" in p]
    media = {
        m
        for operation in _operations(generated).values()
        for m in operation.get("requestBody", {}).get("content", {})
    }
    assert not [m for m in media if m.startswith("audio/")]


@pytest.mark.req("TST-060", "API-113", "FEAT-038-AC-08", "FEAT-038-FR-02")
@pytest.mark.parametrize(("app_env", "docs_status"), [("production", 404), ("test", 200)])
def test_served_document_and_docs(app_env: str, docs_status: int) -> None:
    overrides: dict[str, Any] = {"app_env": app_env}
    if app_env == "production":
        remote = "postgresql+psycopg://u:p@db.example.org/x?sslmode=require"
        overrides |= {
            "cors_origins": "https://app.example.org", "database_url": remote,
            "database_readonly_url": remote, "jwt_secret": "Zq8vN3xK1pL7wR4tY6uI0oP2aS5dF9gHk3Lm",
            "pipeline_profile": "production", "facility_name": "Synthetic Facility",
            "log_format": "json",
        }  # fmt: skip
    app = create_app(make_settings(**overrides))
    client = TestClient(app)
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    assert response.json() == build_openapi(create_app(make_settings()))
    assert client.get("/api/v1/docs").status_code == docs_status
    assert client.get("/api/v1/redoc").status_code == 404
