"""Optional backend error monitoring with Sentry (TRD 17 LOG-070, LOG-100..LOG-102, LOG-111;
TRD 22 TPS-060, TPS-061; TRD 12 SEC-127; FEAT-084).

`init_sentry(settings)` is called once by the web application's lifespan and by
`backend.jobs.nightly_run.main`, never at import time, so `export-openapi` and the tests stay
offline. With an empty SENTRY_DSN nothing is initialised and the SDK is not even imported, so no
code path can make a network call (LOG-101). Sentry is enabled only for the interim staging and
production environments (LOG-102, TRD 21 §4.7); before AWS go-live SENTRY_DSN stays empty in
production unless the project coordinator and UND IT approve it (TPS-061, docs/deployment.md).

Events are errors only: every ERROR log record (`unhandled_exception`, LOG-070;
`nightly_run_missing`, LOG-111; `pipeline_run_failed`) becomes one event after the redaction of
the logs (LOG-023, LOG-024) is applied again in `before_send`, which also drops request headers,
cookies, query strings and bodies. No web-framework integration, tracing, breadcrumbs or local
variables are collected (`send_default_pii=False`, `traces_sample_rate=0`,
`max_request_body_size="never"`). Sentry is backend-only; the frontend has no SDK (TPS-060).
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from backend.core.config import DEPLOYED_ENVS, Settings
from backend.core.logging import mask_text, redact

logger = logging.getLogger("backend.monitoring")

# Request fields that never leave the process (LOG-100, SEC-127).
_DROPPED_REQUEST_FIELDS = ("data", "headers", "cookies", "query_string", "env")
# Top-level event fields that may carry log extras or free text.
_REDACTED_EVENT_FIELDS = ("extra", "contexts", "tags")


def sentry_options(settings: Settings) -> dict[str, Any]:
    """The `sentry_sdk.init` options of LOG-100 (without the DSN and integrations)."""
    return {
        "environment": settings.app_env,
        "release": settings.git_sha,
        "send_default_pii": False,
        "traces_sample_rate": 0,
        "max_request_body_size": "never",
        "include_local_variables": False,
        "max_breadcrumbs": 0,
        "before_send": before_send,
    }


def init_sentry(settings: Settings, *, transport: Any = None) -> bool:
    """Initialise `sentry-sdk` when SENTRY_DSN is set in staging or production; return whether
    it is enabled. `transport` is for unit tests only (a captured transport, FEAT-084)."""
    dsn = settings.sentry_dsn.get_secret_value()
    enabled = bool(dsn) and settings.app_env in DEPLOYED_ENVS
    if dsn and not enabled:
        # TRD 21 §4.7: SENTRY_DSN is empty in local and test; a value there is ignored.
        logger.warning(
            "sentry_dsn_ignored",
            extra={"event": "sentry_dsn_ignored", "reason": "only staging and production"},
        )
    if enabled:
        import sentry_sdk
        from sentry_sdk.integrations.dedupe import DedupeIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_sdk.init(
            dsn=dsn,
            default_integrations=False,
            auto_enabling_integrations=False,
            integrations=[
                LoggingIntegration(level=None, event_level=logging.ERROR, sentry_logs_level=None),
                DedupeIntegration(),
            ],
            transport=transport,
            **sentry_options(settings),
        )
    # The startup summary names only the boolean, never the DSN (TRD 21 §8).
    logger.info(
        "sentry_configured", extra={"event": "sentry_configured", "sentry_enabled": enabled}
    )
    return enabled


def _strip_url(url: str) -> str:
    parts = urlsplit(url)
    return mask_text(urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")))


def _scrub_exception(exception: Mapping[str, Any]) -> dict[str, Any]:
    values = []
    for value in exception.get("values") or []:
        item = dict(value)
        if isinstance(item.get("value"), str):
            item["value"] = mask_text(item["value"])
        stacktrace = item.get("stacktrace")
        if isinstance(stacktrace, Mapping):
            frames = [
                {k: v for k, v in frame.items() if k != "vars"}
                for frame in stacktrace.get("frames") or []
            ]
            item["stacktrace"] = {**stacktrace, "frames": frames}
        values.append(item)
    return {**exception, "values": values}


def before_send(event: dict[str, Any], hint: Any = None) -> dict[str, Any]:
    """Apply the LOG-023/LOG-024 redaction and drop request headers, cookies, query strings and
    bodies (LOG-100, SEC-127). Returns the sanitised event."""
    request = event.get("request")
    if isinstance(request, Mapping):
        kept = {k: v for k, v in request.items() if k not in _DROPPED_REQUEST_FIELDS}
        if isinstance(kept.get("url"), str):
            kept["url"] = _strip_url(kept["url"])
        event["request"] = kept
    event.pop("user", None)
    event.pop("breadcrumbs", None)
    for field in _REDACTED_EVENT_FIELDS:
        if isinstance(event.get(field), Mapping):
            event[field] = redact(event[field])
    logentry = event.get("logentry")
    if isinstance(logentry, Mapping):
        event["logentry"] = redact(logentry)
    if isinstance(event.get("message"), str):
        event["message"] = mask_text(event["message"])
    if isinstance(event.get("exception"), Mapping):
        event["exception"] = _scrub_exception(event["exception"])
    return event
