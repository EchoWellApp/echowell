"""Structured logging, redaction and request context (TRD 17 LOG-001..LOG-035; FEAT-018)."""

from __future__ import annotations

import io
import json
import logging
import uuid

import pytest

from backend.core import logging as ew_logging

pytestmark = pytest.mark.unit


def _emit(fmt: str, message: str, **extra: object) -> str:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(ew_logging.ContextFilter())
    handler.addFilter(ew_logging.RedactionFilter())
    handler.setFormatter(
        ew_logging.JsonFormatter("test", "0123abc")
        if fmt == "json"
        else ew_logging.ConsoleFormatter()
    )
    logger = logging.getLogger(f"test.logging.{uuid.uuid4().hex}")
    logger.propagate = False
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.info(message, extra=extra)
    return stream.getvalue()


@pytest.mark.req("LOG-001", "NFR-100", "FEAT-018-AC-01")
def test_json_lines_have_the_required_keys() -> None:
    line = _emit("json", "request_completed", event="request_completed", status=200)
    record = json.loads(line)
    for key in ("ts", "level", "logger", "msg", "event", "env", "version"):
        assert key in record
    assert record["ts"].endswith("Z")  # LOG-005
    assert (record["env"], record["version"], record["status"]) == ("test", "0123abc", 200)
    assert line.count("\n") == 1


@pytest.mark.req("LOG-023", "LOG-024", "SEC-107", "FEAT-018-AC-05")
def test_secret_keys_and_credentialed_urls_are_redacted() -> None:
    line = _emit(
        "json", "connecting to postgresql://u:secretpw@h/db",
        password="x", Authorization="Bearer abc", note="text",  # noqa: S106 - redaction input
        details={"api_key": "ewk_abcdefghijklmnop", "count": 3},
    )  # fmt: skip
    record = json.loads(line)
    redacted = "[REDACTED]"
    assert record["password"] == record["Authorization"] == record["note"] == redacted
    assert record["details"] == {"api_key": "[REDACTED]", "count": 3}
    assert "secretpw" not in line
    assert "u:[REDACTED]@h/db" in record["msg"]


@pytest.mark.req("LOG-024", "SEC-107")
def test_bearer_tokens_api_keys_and_jwts_are_masked_in_text() -> None:
    text = "Bearer abc.def ewk_0123456789abcdef eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.sig"
    masked = ew_logging.mask_text(text)
    assert "abc.def" not in masked
    assert "ewk_0123456789abcdef" not in masked
    assert "eyJ" not in masked


@pytest.mark.req("LOG-030", "API-105", "FEAT-018-AC-02")
def test_request_id_acceptance() -> None:
    assert ew_logging.accept_request_id("abcd1234-test") == "abcd1234-test"
    for bad in (None, "", "bad id!", "short", "x" * 65):
        generated = ew_logging.accept_request_id(bad)
        assert uuid.UUID(generated).version == 4


@pytest.mark.req("LOG-004", "LOG-034")
def test_context_fields_are_added_and_restored() -> None:
    ew_logging.start_context(request_id="req-12345678")
    ew_logging.set_context(actor="user", user_id="u1")
    with ew_logging.bound(pipeline_run_id="run-1"):
        record = json.loads(_emit("json", "pipeline_stage"))
        assert (record["request_id"], record["user_id"], record["pipeline_run_id"]) == (
            "req-12345678", "u1", "run-1",
        )  # fmt: skip
    record = json.loads(_emit("json", "after"))
    assert "pipeline_run_id" not in record
    assert ew_logging.get_request_id() == "req-12345678"


@pytest.mark.req("LOG-002")
def test_console_format_is_one_readable_line() -> None:
    line = _emit("console", "request_completed", event="request_completed", status=404)
    assert " INFO " in line
    assert "request_completed" in line
    assert "status=404" in line
