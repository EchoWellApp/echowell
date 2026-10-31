"""The response checker that validates every integration-test response (TRD 13 TST-061, TST-064;
TRD 19 OAS-006, OAS-017; FEAT-038-AC-04, FEAT-038-AC-05).

`tests/integration/api/conftest.py` installs `check_response` on the `api` client, so the
integration API tests are the evidence for AC-04 and AC-05; these tests show the checker rejects
what it must.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from tests.contract.response_validation import META_FIELDS, ContractViolationError, check_response

pytestmark = pytest.mark.contract

META = dict.fromkeys(META_FIELDS, None) | {
    "facility_name": "Edgewood", "facility_tz": "America/Chicago",
    "data_source_label": "pipeline test data v0.1", "baseline_n": 16, "cusum_h": 5.0,
    "pipeline_profile": "test_v0_1",
}  # fmt: skip
HEADERS = {"x-request-id": "req-12345678"}
EMPTY_PAGE = {"meta": META, "total": 0, "limit": 50, "offset": 0, "items": []}


def _response(
    method: str, path: str, status: int, body: Any, content_type: str = "application/json"
) -> httpx.Response:
    request = httpx.Request(method, f"http://testserver/api/v1{path}")
    return httpx.Response(
        status, content=json.dumps(body).encode(), request=request,
        headers={**HEADERS, "content-type": content_type},
    )  # fmt: skip


def _problem(status: int, code: str) -> dict[str, Any]:
    return {"type": f"urn:echowell:error:{code}", "title": "t", "status": status, "detail": "d",
            "request_id": "req-12345678", "errors": []}  # fmt: skip


@pytest.mark.req("TST-061", "OAS-006", "FEAT-038-AC-04")
def test_valid_responses_pass() -> None:
    check_response(_response("GET", "/devices", 200, EMPTY_PAGE))
    check_response(_response("GET", "/devices", 401, _problem(401, "NOT_AUTHENTICATED"),
                             "application/problem+json"))  # fmt: skip
    check_response(_response("GET", "/devices", 500, _problem(500, "INTERNAL_ERROR"),
                             "application/problem+json"))  # fmt: skip
    check_response(_response("GET", "/_test/boom", 200, {"anything": True}))


@pytest.mark.req("TST-061", "OAS-006", "OAS-009", "FEAT-038-AC-04")
@pytest.mark.parametrize(
    ("status", "body", "content_type"),
    [
        (200, {**EMPTY_PAGE, "total": -1}, "application/json"),
        (200, {"total": 0, "limit": 50, "offset": 0, "items": []}, "application/json"),
        (401, {"type": "urn:echowell:error:NOT_AUTHENTICATED"}, "application/problem+json"),
        (500, {"detail": "boom"}, "application/problem+json"),
        (409, _problem(409, "CONFLICT"), "application/problem+json"),
    ],
)  # fmt: skip
def test_contract_breaks_are_caught(status: int, body: Any, content_type: str) -> None:
    with pytest.raises(ContractViolationError):
        check_response(_response("GET", "/devices", status, body, content_type))


@pytest.mark.req("OAS-010", "FEAT-038-FR-06")
def test_request_id_header_is_required() -> None:
    response = _response("GET", "/devices", 200, EMPTY_PAGE)
    del response.headers["x-request-id"]
    with pytest.raises(ContractViolationError, match="X-Request-ID"):
        check_response(response)


@pytest.mark.req("TST-064", "OAS-017", "FEAT-038-AC-05", "FEAT-038-FR-11")
def test_meta_only_where_declared() -> None:
    health = {"status": "ok", "database": "ok", "version": "0.1.0", "time": "2026-10-27T12:00:00Z"}
    with pytest.raises(ContractViolationError, match="undeclared meta"):
        check_response(_response("GET", "/health", 200, {**health, "meta": META}))
    short = {k: v for k, v in META.items() if k != "cusum_h"}
    with pytest.raises(ContractViolationError):
        check_response(_response("GET", "/devices", 200, {**EMPTY_PAGE, "meta": short}))
