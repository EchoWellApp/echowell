"""Optional request properties may be left out but not sent as null, matching their TRD 19
schemas, which have no `null` type (OAS-004, OAS-012; FEAT-038-FR-05)."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from backend.schemas.alerts import SnoozeRequest
from backend.schemas.pipeline import PipelineRunRequest
from backend.schemas.users import UserUpdate

pytestmark = pytest.mark.unit

CASES: list[tuple[type[BaseModel], dict[str, Any], str]] = [
    (SnoozeRequest, {}, "hours"),
    (PipelineRunRequest, {"scope": "all"}, "profile"),
    (UserUpdate, {"active": True}, "display_name"),
    (UserUpdate, {"active": True}, "role"),
    (UserUpdate, {"display_name": "A"}, "active"),
    (UserUpdate, {"active": True}, "password"),
]


@pytest.mark.req("OAS-004", "OAS-012", "FEAT-038-FR-05")
@pytest.mark.parametrize(("model", "base", "field"), CASES)
def test_omitted_is_fine_null_is_refused(
    model: type[BaseModel], base: dict[str, Any], field: str
) -> None:
    assert getattr(model.model_validate(base), field) is None
    with pytest.raises(ValidationError) as caught:
        model.model_validate({**base, field: None})
    assert caught.value.errors()[0]["loc"] == (field,)
    schema = model.model_json_schema()["properties"][field]
    assert "anyOf" not in schema
    assert schema.get("type") != "null"


@pytest.mark.req("OAS-004")
def test_nullable_request_fields_stay_nullable() -> None:
    assert PipelineRunRequest.model_validate({"scope": "all", "as_of": None}).as_of is None
