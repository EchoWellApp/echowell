"""The TRD 19 §4.3 JSON examples in the OpenAPI document (TRD 19 OAS-015, AC-OAS-04;
FEAT-038-FR-10).

Every `json` block of §4.3 is in `backend/api/openapi_examples.json`, in order and unchanged, except
where the TRD abbreviates (`completed` says how); every example in the generated document validates
against the schema of its request body or response, formats included.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from backend.api.openapi import build_openapi, examples
from backend.main import create_app
from tests.conftest import make_settings

pytestmark = pytest.mark.contract

TRD19 = Path(__file__).resolve().parents[2] / "specs" / "TRD" / "19_API_Contracts_OpenAPI_Spec.md"
_BLOCK = re.compile(r"^```json\n(.*?)^```", re.DOTALL | re.MULTILINE)


def _section_43() -> str:
    text = TRD19.read_text(encoding="utf-8")
    return text[text.index("### 4.3 Endpoint contracts") : text.index("### 4.4 Servers")]


def _schema_of(document: dict[str, Any], media: dict[str, Any]) -> dict[str, Any]:
    return {**media["schema"], "components": document["components"]}


@pytest.mark.req("OAS-015", "FEAT-038-FR-10")
def test_examples_are_the_trd_examples() -> None:
    blocks = [json.loads(b) for b in _BLOCK.findall(_section_43())]
    stored = examples()
    assert len(stored) == len(blocks) == 26
    for example, block in zip(stored, blocks, strict=True):
        assert example["path"] in _section_43()
        if "completed" not in example:
            assert example["value"] == block, example["name"]


@pytest.mark.req("OAS-015", "AC-OAS-04", "FEAT-038-FR-10")
def test_examples_validate_against_their_schemas() -> None:
    document = build_openapi(create_app(make_settings()))
    checked = 0
    for path, item in document["paths"].items():
        for method, operation in item.items():
            holders = [operation.get("requestBody", {}), *operation["responses"].values()]
            for holder in holders:
                for media in holder.get("content", {}).values():
                    validator = Draft202012Validator(
                        _schema_of(document, media),
                        format_checker=Draft202012Validator.FORMAT_CHECKER,
                    )
                    for name, example in media.get("examples", {}).items():
                        errors = [e.message for e in validator.iter_errors(example["value"])]
                        assert errors == [], f"{method.upper()} {path} {name}: {errors[:3]}"
                        checked += 1
    assert checked == 26
    assert "examples" not in json.dumps(document["components"]["responses"])
