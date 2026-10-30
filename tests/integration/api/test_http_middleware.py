"""HTTP middleware and the error model (TRD 05 §4.7, §4.8; TRD 17 LOG-010..LOG-070; FEAT-018,
FEAT-019)."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.core.config import Settings
from backend.core.errors import CATALOGUE
from backend.models import PipelineRunStatus, PipelineTrigger
from backend.repositories.pipeline_run_repository import PipelineRunRepository
from backend.services.meta_service import get_meta

pytestmark = pytest.mark.integration

PROBLEM = "application/problem+json"


def _is_problem(response: object, code: str) -> dict[str, object]:
    assert response.headers["content-type"] == PROBLEM  # type: ignore[attr-defined]
    body = response.json()  # type: ignore[attr-defined]
    assert set(body) == {"type", "title", "status", "detail", "request_id", "errors"}
    assert body["type"] == f"urn:echowell:error:{code}"
    assert (body["status"], body["title"]) == CATALOGUE[code]
    assert body["request_id"] == response.headers["x-request-id"]  # type: ignore[attr-defined]
    return body  # type: ignore[no-any-return]


@pytest.mark.req("LOG-030", "API-105", "FEAT-018-AC-02")
def test_request_id_is_echoed_or_generated(bare_client: TestClient) -> None:
    good = bare_client.get("/api/v1/_test/none", headers={"X-Request-ID": "abcd1234-test"})
    assert good.headers["x-request-id"] == "abcd1234-test"
    bad = bare_client.get("/api/v1/_test/none", headers={"X-Request-ID": "bad id!"})
    assert uuid.UUID(bad.headers["x-request-id"]).version == 4


@pytest.mark.req("LOG-031", "FR-254", "API-105", "FEAT-018-AC-03", "FEAT-019-AC-02")
def test_errors_carry_the_request_id_and_problem_shape(bare_client: TestClient) -> None:
    body = _is_problem(bare_client.get("/api/v1/nowhere"), "NOT_FOUND")
    assert body["errors"] == []
    _is_problem(bare_client.delete("/api/v1/_test/echo"), "METHOD_NOT_ALLOWED")
    _is_problem(bare_client.post("/api/v1/_test/echo", json={}), "VALIDATION_ERROR")
    _is_problem(bare_client.get("/api/v1/_test/boom"), "INTERNAL_ERROR")


@pytest.mark.req("AC-LOG-08", "API-096", "LOG-042", "SEC-085", "FEAT-019-AC-01", "FEAT-018-AC-07")
def test_unhandled_exception_is_a_generic_500(
    bare_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO)
    response = bare_client.get("/api/v1/_test/boom", headers={"X-Request-ID": "boom-request-1"})
    body = _is_problem(response, "INTERNAL_ERROR")
    assert body["detail"] == "An unexpected error occurred."
    assert "secret" not in response.text
    assert "Traceback" not in response.text
    records = [r for r in caplog.records if r.getMessage() == "unhandled_exception"]
    assert len(records) == 1
    assert records[0].levelno == logging.ERROR
    assert records[0].exc_type == "RuntimeError"  # type: ignore[attr-defined]
    assert "stack" in vars(records[0])


@pytest.mark.req("LOG-010", "LOG-011", "API-107", "FEAT-018-AC-04")
def test_one_access_record_per_request_with_levels(
    bare_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="backend.access")
    expectations = [
        ("/api/v1/nowhere", "get", None, logging.INFO, 404),
        ("/api/v1/_test/echo", "post", {}, logging.WARNING, 422),
        ("/api/v1/_test/boom", "get", None, logging.ERROR, 500),
    ]
    for path, method, body, level, status in expectations:
        caplog.clear()
        getattr(bare_client, method)(path, **({"json": body} if body is not None else {}))
        records = [r for r in caplog.records if r.getMessage() == "request_completed"]
        assert len(records) == 1, path
        assert records[0].levelno == level
        assert records[0].status == status  # type: ignore[attr-defined]
    caplog.clear()
    bare_client.post("/api/v1/_test/echo", json={"name": "x"})
    (record,) = (r for r in caplog.records if r.getMessage() == "request_completed")
    assert record.route == "/api/v1/_test/echo"  # type: ignore[attr-defined]
    assert record.method == "POST"  # type: ignore[attr-defined]
    assert record.actor_type == "anonymous"  # type: ignore[attr-defined]


@pytest.mark.req("LOG-011")
def test_healthy_health_check_logs_at_debug(
    app_factory: Callable[..., FastAPI],
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from backend.schemas.health import Health
    from backend.services import health_service

    healthy = Health(status="ok", database="ok", version="0123abc", time=datetime.now(UTC))
    monkeypatch.setattr(health_service, "get_health", lambda settings, engine: healthy)
    caplog.set_level(logging.DEBUG, logger="backend.access")
    with TestClient(app_factory()) as client:
        assert client.get("/api/v1/health").status_code == 200
    (record,) = (r for r in caplog.records if r.getMessage() == "request_completed")
    assert record.levelno == logging.DEBUG


@pytest.mark.req("SEC-080", "LOG-043", "FEAT-019-AC-03")
def test_unknown_property_is_rejected_without_echoing_input(bare_client: TestClient) -> None:
    response = bare_client.post("/api/v1/_test/echo", json={"name": "a", "secret_extra": "zz-77"})
    body = _is_problem(response, "VALIDATION_ERROR")
    assert body["errors"] == [
        {
            "field": "secret_extra",
            "code": "extra_forbidden",
            "message": "Extra inputs are not permitted",
        }
    ]
    assert "zz-77" not in response.text


@pytest.mark.req("API-104", "SEC-081", "SEC-082", "TST-133", "FEAT-019-AC-05")
def test_body_size_and_media_type_limits(bare_client: TestClient) -> None:
    big = '{"name": "' + "x" * 65_537 + '"}'
    too_large = bare_client.post(
        "/api/v1/_test/echo", content=big, headers={"Content-Type": "application/json"}
    )
    _is_problem(too_large, "PAYLOAD_TOO_LARGE")
    wav = bare_client.post(
        "/api/v1/_test/echo", content=b"RIFF....", headers={"Content-Type": "audio/wav"}
    )
    _is_problem(wav, "UNSUPPORTED_MEDIA_TYPE")
    text = bare_client.post(
        "/api/v1/_test/echo", content=b"name=a", headers={"Content-Type": "text/plain"}
    )
    _is_problem(text, "UNSUPPORTED_MEDIA_TYPE")
    ok = bare_client.post("/api/v1/_test/echo", json={"name": "a"})
    assert ok.status_code == 200


@pytest.mark.req("API-104")
def test_streamed_body_over_the_limit_is_rejected(bare_client: TestClient) -> None:
    def chunks() -> object:
        yield b'{"name": "'
        for _ in range(70):
            yield b"x" * 1024
        yield b'"}'

    response = bare_client.post(
        "/api/v1/_test/echo", content=chunks(), headers={"Content-Type": "application/json"}
    )
    _is_problem(response, "PAYLOAD_TOO_LARGE")


@pytest.mark.req("API-097", "FEAT-019-AC-04")
def test_database_unreachable_is_503_with_retry_after(bare_client: TestClient) -> None:
    response = bare_client.get("/api/v1/_test/db-down")
    _is_problem(response, "SERVICE_UNAVAILABLE")
    assert response.headers["retry-after"] == "30"


@pytest.mark.req("API-101", "SEC-094", "LOG-035", "TST-134", "FEAT-019-AC-06")
def test_cors_allows_only_configured_origins(bare_client: TestClient) -> None:
    preflight = {"Access-Control-Request-Method": "GET"}
    allowed = bare_client.options(
        "/api/v1/health", headers={"Origin": "http://localhost:3000", **preflight}
    )
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    simple = bare_client.get("/api/v1/nowhere", headers={"Origin": "http://localhost:3000"})
    assert "X-Request-ID" in simple.headers["access-control-expose-headers"]
    other = bare_client.options(
        "/api/v1/health", headers={"Origin": "https://evil.example", **preflight}
    )
    assert "access-control-allow-origin" not in other.headers


@pytest.mark.req("API-106", "TST-134", "FEAT-019-AC-07")
def test_security_headers_and_hsts(app_factory: Callable[..., FastAPI]) -> None:
    expected = {
        "x-content-type-options": "nosniff",
        "x-frame-options": "DENY",
        "referrer-policy": "no-referrer",
        "cache-control": "no-store",
    }
    with TestClient(app_factory(), raise_server_exceptions=False) as client:
        for response in (client.get("/api/v1/nowhere"), client.get("/api/v1/_test/boom")):
            for name, value in expected.items():
                assert response.headers[name] == value
            assert "strict-transport-security" not in response.headers
    staging = app_factory(
        app_env="staging", cors_origins="https://staging.example.org",
        database_url="postgresql+psycopg://u:p@db.example.org/x?sslmode=require",
        database_readonly_url="postgresql+psycopg://u:p@db.example.org/x?sslmode=require",
        jwt_secret="Zq8vN3xK1pL7wR4tY6uI0oP2aS5dF9gHk3Lm",  # noqa: S106 - test-only
        facility_name="Edgewood", git_sha="0123abc", log_format="json",
    )  # fmt: skip
    with TestClient(staging, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/nowhere")
        assert (
            response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"
        )


@pytest.mark.req("API-057", "API-069", "FR-332", "FR-333", "FEAT-019-AC-08")
def test_meta_uses_the_latest_succeeded_run(app_session: Session, api_settings: Settings) -> None:
    from tests.integration.world import World

    World.build(app_session)
    meta = get_meta(app_session, api_settings)
    assert meta.as_of is None
    assert (meta.facility_name, meta.baseline_n, meta.cusum_h) == ("Edgewood", 16, 5.0)
    assert meta.pipeline_profile == "test_v0_1"
    runs = PipelineRunRepository(app_session)
    run = runs.insert_running(
        trigger=PipelineTrigger.TEST, scope={"type": "all"}, config_profile="test_v0_1",
        config_snapshot={}, code_version="t", as_of=datetime(2026, 10, 30, 20, tzinfo=UTC),
    )  # fmt: skip
    runs.finish(run, status=PipelineRunStatus.SUCCEEDED, finished_at=datetime.now(UTC))
    meta = get_meta(app_session, api_settings)
    assert meta.model_dump(mode="json")["as_of"] == "2026-10-30T20:00:00Z"


@pytest.mark.req("API-093", "FEAT-019-AC-09")
def test_reversed_date_range_is_invalid() -> None:
    from datetime import date

    from backend.api.deps import check_date_range
    from backend.core.errors import InvalidQueryParameterError

    with pytest.raises(InvalidQueryParameterError):
        check_date_range(date(2026, 10, 20), date(2026, 10, 10))
    check_date_range(date(2026, 10, 10), date(2026, 10, 20))
