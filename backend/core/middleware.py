"""HTTP middleware (TRD 05 §4.8, §4.11; TRD 17 LOG-010, LOG-030..LOG-035, LOG-070; FEAT-018,
FEAT-019).

Pure ASGI middleware, so streamed bodies can be counted and every response, errors included,
gets the same headers:

- `RequestContextMiddleware` (outermost): request ID (API-105), security headers (API-106),
  one `request_completed` access-log record (API-107) and the 500 Problem for unhandled
  exceptions (API-096, LOG-070).
- `BodyLimitMiddleware`: 413 above 64 KB, or 5 MB for `POST /ingest` (API-104), and 415 for
  media types other than JSON and the ingest CSV upload (SEC-082).
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from backend.core.errors import (
    INTERNAL_DETAIL,
    PROBLEM_MEDIA_TYPE,
    PayloadTooLargeError,
    log_unhandled,
    problem_body,
)
from backend.core.logging import (
    REQUEST_ID_HEADER,
    accept_request_id,
    get_context,
    start_context,
)

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

access_logger = logging.getLogger("backend.access")

API_PREFIX = "/api/v1"
INGEST_PATH = f"{API_PREFIX}/ingest"
HEALTH_PATH = f"{API_PREFIX}/health"
BODY_LIMIT = 64 * 1024
INGEST_BODY_LIMIT = 5 * 1024 * 1024
SECURITY_HEADERS = (
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"cache-control", b"no-store"),
)
HSTS = (b"strict-transport-security", b"max-age=31536000; includeSubDomains")


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key.lower() == name:
            return str(value.decode("latin-1"))
    return None


async def _send_problem(
    send: Send, code: str, detail: str, headers: list[tuple[bytes, bytes]]
) -> None:
    body = json.dumps(problem_body(code, detail)).encode()
    await send(
        {
            "type": "http.response.start",
            "status": problem_body(code, detail)["status"],
            "headers": [
                (b"content-type", PROBLEM_MEDIA_TYPE.encode()),
                (b"content-length", str(len(body)).encode()),
                *headers,
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp, *, hsts: bool) -> None:
        self.app = app
        self.hsts = hsts

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = accept_request_id(_header(scope, b"x-request-id"))
        start_context(request_id=request_id)
        extra_headers = [
            (REQUEST_ID_HEADER.lower().encode(), request_id.encode()),
            *SECURITY_HEADERS,
        ]
        if self.hsts:
            extra_headers.append(HSTS)
        state: dict[str, Any] = {"status": 500, "started": False}
        started = time.perf_counter()

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                state["status"], state["started"] = message["status"], True
                present = {k.lower() for k, _ in message.get("headers", [])}
                message["headers"] = list(message.get("headers", [])) + [
                    (k, v) for k, v in extra_headers if k not in present
                ]
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        except Exception as exc:
            log_unhandled(exc)
            if not state["started"]:
                state["status"] = 500
                await _send_problem(send, "INTERNAL_ERROR", INTERNAL_DETAIL, extra_headers)
        finally:
            self._log(scope, state["status"], started)

    def _log(self, scope: Scope, status: int, started: float) -> None:
        route = scope.get("route")
        template = getattr(route, "path", None) or scope.get("path", "")
        if status >= 500:
            level = logging.ERROR
        elif status < 400 or status in (401, 404):
            level = logging.INFO
        else:
            level = logging.WARNING
        if template == HEALTH_PATH and status == 200:
            level = logging.DEBUG
        access_logger.log(
            level,
            "request_completed",
            extra={
                "event": "request_completed",
                "method": scope.get("method"),
                "route": template,
                "status": status,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                "actor_type": get_context("actor") or "anonymous",
                "actor_id": get_context("user_id"),
            },
        )


class BodyLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        is_audio = (_header(scope, b"content-type") or "").lower().startswith("audio/")
        if scope["type"] == "http" and is_audio:
            # No route accepts audio, whatever the method (TRD 13 TST-133, TRD 12 SEC-121).
            await _send_problem(send, "UNSUPPORTED_MEDIA_TYPE", "Audio is never accepted.", [])
            return
        if scope["type"] != "http" or scope.get("method") in ("GET", "HEAD", "OPTIONS"):
            await self.app(scope, receive, send)
            return
        is_ingest = scope.get("path") == INGEST_PATH and scope.get("method") == "POST"
        limit = INGEST_BODY_LIMIT if is_ingest else BODY_LIMIT
        length = _header(scope, b"content-length")
        has_body = (length not in (None, "0")) or _header(scope, b"transfer-encoding") is not None
        if length is not None and length.isdigit() and int(length) > limit:
            await _send_problem(send, "PAYLOAD_TOO_LARGE", self._too_large(limit), [])
            return
        if has_body and not self._media_type_allowed(_header(scope, b"content-type"), is_ingest):
            await _send_problem(
                send, "UNSUPPORTED_MEDIA_TYPE",
                "Send application/json" + (" or a multipart CSV upload." if is_ingest else "."), [],
            )  # fmt: skip
            return
        received = 0

        async def counting_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise PayloadTooLargeError(self._too_large(limit))
            return message

        await self.app(scope, counting_receive, send)

    @staticmethod
    def _too_large(limit: int) -> str:
        return f"The request body is larger than {limit // 1024} KB."

    @staticmethod
    def _media_type_allowed(content_type: str | None, is_ingest: bool) -> bool:
        media = (content_type or "").split(";", 1)[0].strip().lower()
        if media == "application/json":
            return True
        return is_ingest and media == "multipart/form-data"
