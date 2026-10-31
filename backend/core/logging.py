"""Structured logging, redaction and request context (TRD 17 LOG-001..LOG-035; FEAT-018).

Logging is configured once by `configure_logging()` with the standard library: one JSON object per
line on stdout (`LOG_FORMAT=json`) or a readable line (`console`, local and test only). Context
variables carry `request_id`, `actor`, `user_id`, `pipeline_run_id` and `resident_code` into every
record. Two filters run before formatting: values under secret-looking keys become `[REDACTED]`
(LOG-023) and credentialed URLs, bearer tokens and API keys are masked in any text (LOG-024).
"""

from __future__ import annotations

import json
import logging
import re
import sys
import traceback
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

REQUEST_ID_HEADER = "X-Request-ID"
REDACTED = "[REDACTED]"
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{8,64}$")
_SECRET_KEY = re.compile(
    r"password|secret|token|authorization|api_key|apikey|cookie|dsn|database_url|body|note",
    re.IGNORECASE,
)
_TEXT_MASKS = (
    (
        re.compile(r"([a-z][a-z0-9+.-]*://)([^:/@\s]+):([^@/\s]+)@", re.IGNORECASE),
        r"\1\2:" + REDACTED + "@",
    ),
    (re.compile(r"(bearer\s+)[A-Za-z0-9._~+/=-]+", re.IGNORECASE), r"\1" + REDACTED),
    (re.compile(r"\bewk_[A-Za-z0-9_-]{8,}"), REDACTED),
    (re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*"), REDACTED),
)  # fmt: skip

_CONTEXT_FIELDS = ("request_id", "actor", "user_id", "pipeline_run_id", "resident_code")
# One mutable dict per request or task: sync dependencies run in a thread pool on a copy of the
# context, so they mutate the shared dict instead of setting context variables (LOG-004).
_context: ContextVar[dict[str, str | None] | None] = ContextVar(
    "echowell_log_context", default=None
)
# Attributes every LogRecord has; anything else was passed through `extra=`.
_RECORD_ATTRS = frozenset(vars(logging.makeLogRecord({}))) | {"message", "asctime", "taskName"}


def accept_request_id(value: str | None) -> str:
    """The incoming X-Request-ID when it matches LOG-030, otherwise a new UUID4."""
    if value and _REQUEST_ID_PATTERN.match(value):
        return value
    return str(uuid.uuid4())


def get_context(name: str) -> str | None:
    values = _context.get()
    return values.get(name) if values else None


def get_request_id() -> str | None:
    return get_context("request_id")


def start_context(**values: str | None) -> None:
    """Begin a fresh context for one request (called by the request middleware)."""
    _context.set(dict(values))


def set_context(**values: str | None) -> None:
    """Set fields of the current context (visible to the request middleware and every record)."""
    current = _context.get()
    if current is None:
        current = {}
        _context.set(current)
    current.update(values)


@contextmanager
def bound(**values: str | None) -> Iterator[None]:
    """Run a block (pipeline run, CLI command) with extra context fields, restored afterwards."""
    token = _context.set({**(_context.get() or {}), **values})
    try:
        yield
    finally:
        _context.reset(token)


def mask_text(text: str) -> str:
    """Mask credentialed URLs, bearer tokens, API keys and JWTs in free text (LOG-024)."""
    for pattern, replacement in _TEXT_MASKS:
        text = pattern.sub(replacement, text)
    return text


def redact(value: Any, key: str = "") -> Any:
    """Recursively replace values under secret-looking keys and mask secrets in strings."""
    if key and _SECRET_KEY.search(key):
        return REDACTED
    if isinstance(value, Mapping):
        return {k: redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return mask_text(value)
    return value


class RedactionFilter(logging.Filter):
    """Applies `redact` to the message and every `extra` field before formatting (LOG-023)."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except (TypeError, ValueError):
            message = str(record.msg)
        record.msg = mask_text(message)
        record.args = None
        for name, value in list(vars(record).items()):
            if name not in _RECORD_ATTRS:
                setattr(record, name, redact(value, name))
        return True


class ContextFilter(logging.Filter):
    """Adds the context-variable fields that are set (LOG-004)."""

    def filter(self, record: logging.LogRecord) -> bool:
        for name, value in (_context.get() or {}).items():
            if value is not None and not hasattr(record, name):
                setattr(record, name, value)
        return True


def _timestamp(record: logging.LogRecord) -> str:
    moment = datetime.fromtimestamp(record.created, tz=UTC)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{int(record.msecs):03d}Z"


def _extras(record: logging.LogRecord) -> dict[str, Any]:
    return {k: v for k, v in vars(record).items() if k not in _RECORD_ATTRS and k != "event"}


class JsonFormatter(logging.Formatter):
    """One JSON object per record with `ts level logger msg event env version` first (LOG-001)."""

    def __init__(self, env: str, version: str) -> None:
        super().__init__()
        self.env, self.version = env, version

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        payload: dict[str, Any] = {
            "ts": _timestamp(record),
            "level": record.levelname,
            "logger": record.name,
            "msg": message,
            "event": getattr(record, "event", None) or message,
            "env": self.env,
            "version": self.version,
        }
        payload.update(_extras(record))
        if record.exc_info:
            payload.setdefault(
                "exc_type", record.exc_info[0].__name__ if record.exc_info[0] else None
            )
            payload.setdefault("stack", mask_text(self.formatException(record.exc_info)))
        return json.dumps(payload, default=str, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """`ts level logger event key=value…` for local development (LOG-002)."""

    def format(self, record: logging.LogRecord) -> str:
        event = getattr(record, "event", None) or record.getMessage()
        pairs = " ".join(f"{k}={v}" for k, v in sorted(_extras(record).items()))
        line = f"{_timestamp(record)} {record.levelname} {record.name} {event} {pairs}".rstrip()
        if record.exc_info:
            line += "\n" + mask_text(self.formatException(record.exc_info))
        return line


def configure_logging(level: str, fmt: str, env: str, version: str) -> None:
    """Install the single stdout handler; uvicorn loggers propagate and its access log is off."""
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(ContextFilter())
    handler.addFilter(RedactionFilter())
    handler.setFormatter(JsonFormatter(env, version) if fmt == "json" else ConsoleFormatter())
    root = logging.getLogger()
    for existing in list(root.handlers):
        if getattr(existing, "_echowell", False):
            root.removeHandler(existing)
    handler._echowell = True  # type: ignore[attr-defined]
    root.addHandler(handler)
    root.setLevel(level)
    for name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
    access = logging.getLogger("uvicorn.access")
    access.handlers.clear()
    access.propagate = False
    access.disabled = True


def format_exception(exc: BaseException) -> str:
    return mask_text("".join(traceback.format_exception(exc)))
