"""Error catalogue and problem bodies (TRD 05 §4.7; TRD 20 PGS-028; FEAT-019)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from sqlalchemy.exc import DBAPIError

from backend.core import errors

pytestmark = pytest.mark.unit

TRD_05 = Path(__file__).resolve().parents[4] / "specs" / "TRD" / "05_Backend_API_TRD.md"


@pytest.mark.req("API-095", "LOG-041", "FEAT-019-FR-02")
def test_catalogue_equals_trd_05() -> None:
    text = TRD_05.read_text(encoding="utf-8")
    section = text[
        text.index("Error code catalogue") : text.index(
            "| ID | Requirement", text.index("Error code catalogue")
        )
    ]
    rows = re.findall(r"^\| ([A-Z_]+) \| (\d{3}) \| ([^|]+) \|", section, re.MULTILINE)
    assert {code: (int(status), title.strip()) for code, status, title in rows} == errors.CATALOGUE


@pytest.mark.req("FEAT-019-FR-02")
def test_every_app_error_uses_a_catalogue_code() -> None:
    def subclasses(cls: type) -> list[type]:
        return [c for s in cls.__subclasses__() for c in (s, *subclasses(s))]

    for cls in subclasses(errors.AppError):
        assert cls.code in errors.CATALOGUE, cls


@pytest.mark.req("LOG-040", "D-48")
def test_problem_body_shape() -> None:
    body = errors.problem_body(
        "UNKNOWN_RESIDENT", "resident_id 'R11' is not enrolled.",
        [errors.FieldError("resident_id", "unknown_resident", "resident_id 'R11' is not enrolled.")],  # noqa: E501
        request_id="6c1f3f5e-2b7d",
    )  # fmt: skip
    assert body == {
        "type": "urn:echowell:error:UNKNOWN_RESIDENT",
        "title": "Unknown resident",
        "status": 422,
        "detail": "resident_id 'R11' is not enrolled.",
        "request_id": "6c1f3f5e-2b7d",
        "errors": [
            {
                "field": "resident_id",
                "code": "unknown_resident",
                "message": "resident_id 'R11' is not enrolled.",
            }
        ],
    }


@pytest.mark.req("LOG-043", "FR-027")
def test_validation_locations_drop_the_body_segment() -> None:
    items = errors.validation_field_errors(
        [
            {
                "loc": ("body", "records", 3, "loudness_dbfs"),
                "type": "float_parsing",
                "msg": "bad",
                "input": "x",
            }
        ]
    )
    assert items == [errors.FieldError("records.3.loudness_dbfs", "float_parsing", "bad")]


class _Diag:
    message_primary = "table raw_sessions is append-only: UPDATE is not allowed"


class _OrigError(Exception):
    sqlstate = "EW001"
    diag = _Diag()


@pytest.mark.req("PGS-028", "FEAT-019-FR-07")
def test_append_only_refusal_names_the_table() -> None:
    exc = DBAPIError("UPDATE raw_sessions", {}, _OrigError())
    assert errors.append_only_table(exc) == "raw_sessions"
    other = DBAPIError("SELECT 1", {}, Exception("x"))
    assert errors.append_only_table(other) is None
