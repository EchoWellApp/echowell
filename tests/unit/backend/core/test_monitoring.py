"""Optional Sentry error monitoring (TRD 17 LOG-070, LOG-100..LOG-102, LOG-111; TRD 22 TPS-060;
FEAT-084-AC-01..AC-03)."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
import sentry_sdk
from fastapi.testclient import TestClient
from sentry_sdk.envelope import Envelope
from sentry_sdk.transport import HttpTransport, Transport

from backend.core import monitoring
from backend.core.logging import REDACTED
from backend.main import create_app
from tests.conftest import make_settings

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[4]
DUMMY_DSN = "https://public@o0.ingest.us.sentry.io/0"
SHA = "0123456789abcdef0123456789abcdef01234567"


class CapturingTransport(Transport):
    """Keeps every envelope in memory instead of sending it."""

    def __init__(self) -> None:
        super().__init__()
        self.envelopes: list[Envelope] = []

    def capture_envelope(self, envelope: Envelope) -> None:
        self.envelopes.append(envelope)

    @property
    def events(self) -> list[dict[str, Any]]:
        return [e.get_event() for e in self.envelopes if e.get_event() is not None]  # type: ignore[misc]


@pytest.fixture(autouse=True)
def _no_sentry_client() -> Iterator[None]:
    """Every test starts and ends without an active Sentry client."""
    sentry_sdk.get_global_scope().set_client(None)
    yield
    sentry_sdk.get_client().close()
    sentry_sdk.get_global_scope().set_client(None)


def _boom_app(**overrides: Any) -> TestClient:
    app = create_app(make_settings(**overrides))

    def boom() -> None:
        raise RuntimeError("failed at postgresql://u:p@h/db")

    app.add_api_route("/api/v1/boom", boom)
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.req("LOG-101", "FEAT-084-FR-02", "FEAT-084-AC-01")
def test_empty_dsn_logs_error_and_never_calls_transport(caplog: pytest.LogCaptureFixture) -> None:
    client = _boom_app()
    with (
        mock.patch.object(HttpTransport, "capture_envelope") as send,
        mock.patch.object(HttpTransport, "__init__", side_effect=AssertionError("no transport")),
    ):
        assert monitoring.init_sentry(make_settings(sentry_dsn="")) is False
        with caplog.at_level(logging.ERROR):
            response = client.get("/api/v1/boom")
    assert response.status_code == 500
    assert any(getattr(r, "event", None) == "unhandled_exception" for r in caplog.records)
    assert send.call_count == 0
    assert not sentry_sdk.get_client().is_active()


@pytest.mark.req("LOG-102", "FEAT-084-FR-03")
@pytest.mark.parametrize("env", ["local", "test"])
def test_dsn_is_ignored_outside_staging_and_production(env: str) -> None:
    transport = CapturingTransport()
    settings = make_settings(app_env=env, sentry_dsn=DUMMY_DSN)
    assert monitoring.init_sentry(settings, transport=transport) is False
    assert not sentry_sdk.get_client().is_active()


@pytest.mark.req("LOG-100", "FEAT-084-FR-01")
def test_init_options() -> None:
    settings = make_settings(app_env="staging", sentry_dsn=DUMMY_DSN, git_sha=SHA)
    with mock.patch("sentry_sdk.init") as init:
        assert monitoring.init_sentry(settings) is True
    kwargs = init.call_args.kwargs
    assert kwargs["dsn"] == DUMMY_DSN
    assert kwargs["environment"] == "staging"
    assert kwargs["release"] == SHA
    assert kwargs["send_default_pii"] is False
    assert kwargs["traces_sample_rate"] == 0
    assert kwargs["max_request_body_size"] == "never"
    assert kwargs["before_send"] is monitoring.before_send
    assert kwargs["default_integrations"] is False


@pytest.mark.req("LOG-070", "LOG-100", "SEC-127", "FEAT-084-FR-05", "FEAT-084-AC-02")
def test_unhandled_exception_event_is_sanitised() -> None:
    transport = CapturingTransport()
    settings = make_settings(app_env="production", sentry_dsn=DUMMY_DSN, git_sha=SHA)
    assert monitoring.init_sentry(settings, transport=transport) is True
    response = _boom_app().get(
        "/api/v1/boom?token=abc",
        headers={"Authorization": "Bearer secret-token", "Cookie": "session=1"},
    )
    assert response.status_code == 500
    sentry_sdk.flush()
    events = [e for e in transport.events if e.get("extra", {}).get("exc_type") == "RuntimeError"]
    assert len(events) == 1
    event = events[0]
    assert event["environment"] == "production"
    assert event["release"] == SHA
    assert event["level"] == "error"
    text = str(event)
    for leaked in ("u:p@", "secret-token", "session=1", "token=abc"):
        assert leaked not in text
    assert "[REDACTED]" in event["extra"]["exc_message"]
    assert "request" not in event or not set(event["request"]) & {
        "data", "headers", "cookies", "query_string",
    }  # fmt: skip


@pytest.mark.req("LOG-100", "LOG-023", "LOG-024", "FEAT-084-AC-02")
def test_before_send_drops_request_fields_and_redacts() -> None:
    transport = CapturingTransport()
    settings = make_settings(app_env="staging", sentry_dsn=DUMMY_DSN, git_sha=SHA)
    assert monitoring.init_sentry(settings, transport=transport) is True
    sentry_sdk.capture_event(
        {
            "message": "connect to postgresql://u:p@h/db failed",
            "level": "error",
            "request": {
                "method": "POST",
                "url": "https://api.example.test/api/v1/auth/login?next=/residents",
                "query_string": "next=/residents",
                "headers": {"Authorization": "Bearer abc.def.ghi", "X-API-Key": "ewk_abcdefgh"},
                "cookies": {"session": "1"},
                "data": {"email": "someone@example.com", "password": "hunter2"},
            },
            "extra": {"password": "hunter2", "url": "postgresql://u:p@h/db", "count": 3},
            "user": {"email": "someone@example.com"},
        }
    )
    sentry_sdk.flush()
    (event,) = transport.events
    assert event["environment"] == "staging"
    assert event["release"] == SHA
    assert event["request"] == {
        "method": "POST",
        "url": "https://api.example.test/api/v1/auth/login",
    }
    assert event["extra"]["password"] == REDACTED
    assert event["extra"]["url"] == "postgresql://u:[REDACTED]@h/db"
    assert event["extra"]["count"] == 3
    assert "u:p@" not in event["message"]
    assert "user" not in event
    assert "hunter2" not in str(event)
    assert "someone@example.com" not in str(event)


@pytest.mark.req("LOG-111", "FEAT-084-FR-06")
def test_nightly_run_missing_error_is_reported() -> None:
    transport = CapturingTransport()
    settings = make_settings(app_env="staging", sentry_dsn=DUMMY_DSN, git_sha=SHA)
    assert monitoring.init_sentry(settings, transport=transport) is True
    logger = logging.getLogger(f"backend.jobs.nightly_run.{uuid.uuid4().hex}")
    logger.info("nightly_run_skipped", extra={"local_date": "2026-10-30"})
    logger.error("nightly_run_missing", extra={"local_date": "2026-10-29"})
    sentry_sdk.flush()
    messages = [e.get("logentry", {}).get("message") for e in transport.events]
    assert messages == ["nightly_run_missing"]


@pytest.mark.req("TPS-060", "LOG-082", "FEAT-084-FR-04", "FEAT-084-AC-03")
def test_no_browser_sdk() -> None:
    package = (ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
    assert "@sentry" not in package


@pytest.mark.req("GIT-112", "FEAT-084")
def test_sentry_sdk_pinned_exactly() -> None:
    lines = (ROOT / "backend" / "requirements.txt").read_text(encoding="utf-8").splitlines()
    assert [line for line in lines if line.startswith("sentry-sdk")] == ["sentry-sdk==2.74.0"]
