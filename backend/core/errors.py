"""Error catalogue, application errors and the problem+json handlers (TRD 05 §4.7; TRD 17
LOG-040..LOG-044; D-48; FEAT-019).

Every non-2xx response is `application/problem+json` with `type` = `urn:echowell:error:<CODE>`,
the catalogue title, `status`, `detail`, `request_id` and `errors[]` (`{field, code, message}`).
Services raise `AppError` subclasses; only codes of `CATALOGUE` can be emitted. The HTTP
handlers live in `backend.core.error_handlers`, so services never import FastAPI.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy.exc import DBAPIError

from backend.core.logging import get_request_id

logger = logging.getLogger("backend.errors")

PROBLEM_MEDIA_TYPE = "application/problem+json"
TYPE_PREFIX = "urn:echowell:error:"
INTERNAL_DETAIL = "An unexpected error occurred."

# The complete TRD 05 §4.7 catalogue: code -> (HTTP status, title).
CATALOGUE: dict[str, tuple[int, str]] = {
    "VALIDATION_ERROR": (422, "Validation failed"),
    "INVALID_QUERY_PARAMETER": (422, "Invalid query parameter"),
    "UNSUPPORTED_SCHEMA_VERSION": (422, "Unsupported schema version"),
    "UNKNOWN_RESIDENT": (422, "Unknown resident"),
    "UNKNOWN_DEVICE": (422, "Unknown device"),
    "RESIDENT_WITHDRAWN": (422, "Resident withdrawn"),
    "SESSION_ID_MISMATCH": (422, "Session ID does not match resident"),
    "CSV_HEADER_MISMATCH": (422, "CSV header does not match schema v0.1"),
    "EMPTY_BATCH": (422, "Empty batch"),
    "ALERT_RESIDENT_MISMATCH": (422, "Alert belongs to another resident"),
    "PASSWORD_POLICY_VIOLATION": (422, "Password does not meet policy"),
    "PROFILE_NOT_ALLOWED": (422, "Pipeline profile not allowed"),
    "NOT_AUTHENTICATED": (401, "Authentication required"),
    "INVALID_CREDENTIALS": (401, "Invalid email or password"),
    "TOKEN_EXPIRED": (401, "Token expired"),
    "TOKEN_INVALID": (401, "Token invalid"),
    "API_KEY_INVALID": (401, "API key invalid"),
    "FORBIDDEN": (403, "Not allowed for this role"),
    "DEVICE_KEY_MISMATCH": (403, "API key not valid for this device"),
    "NOT_FOUND": (404, "Not found"),
    "RESIDENT_NOT_FOUND": (404, "Resident not found"),
    "ALERT_NOT_FOUND": (404, "Alert not found"),
    "BATCH_NOT_FOUND": (404, "Ingest batch not found"),
    "PIPELINE_RUN_NOT_FOUND": (404, "Pipeline run not found"),
    "USER_NOT_FOUND": (404, "User not found"),
    "METHOD_NOT_ALLOWED": (405, "Method not allowed"),
    "ALERT_CLOSED": (409, "Alert already closed"),
    "EMAIL_ALREADY_EXISTS": (409, "Email already in use"),
    "LAST_ADMIN": (409, "Cannot remove the last admin"),
    "PIPELINE_RUN_IN_PROGRESS": (409, "A full pipeline run is in progress"),
    "PAYLOAD_TOO_LARGE": (413, "Payload too large"),
    "UNSUPPORTED_MEDIA_TYPE": (415, "Unsupported media type"),
    "RATE_LIMITED": (429, "Too many requests"),
    "ACCOUNT_TEMPORARILY_LOCKED": (429, "Too many failed logins"),
    "INTERNAL_ERROR": (500, "Internal error"),
    "SERVICE_UNAVAILABLE": (503, "Service unavailable"),
}


@dataclass(frozen=True)
class FieldError:
    """One `errors[]` item; `message` never echoes the submitted value (LOG-043)."""

    field: str
    code: str
    message: str


class AppError(Exception):
    """Base class of every expected failure; `code` is a catalogue code."""

    code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        detail: str,
        errors: Sequence[FieldError] = (),
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.errors = list(errors)
        self.headers = headers or {}

    @property
    def status_code(self) -> int:
        return CATALOGUE[self.code][0]


class InvalidQueryParameterError(AppError):
    """A query parameter is out of range (API-016, API-093)."""

    code = "INVALID_QUERY_PARAMETER"


class PasswordPolicyError(AppError):
    """A password breaks TRD 12 SEC-012 (length, equal to e-mail, common password)."""

    code = "PASSWORD_POLICY_VIOLATION"


class ValidationFailedError(AppError):
    code = "VALIDATION_ERROR"


class NotAuthenticatedError(AppError):
    code = "NOT_AUTHENTICATED"


class InvalidCredentialsError(AppError):
    code = "INVALID_CREDENTIALS"


class TokenExpiredError(AppError):
    code = "TOKEN_EXPIRED"


class TokenInvalidError(AppError):
    code = "TOKEN_INVALID"


class ApiKeyInvalidError(AppError):
    code = "API_KEY_INVALID"


class ForbiddenError(AppError):
    code = "FORBIDDEN"


class DeviceKeyMismatchError(AppError):
    code = "DEVICE_KEY_MISMATCH"


class NotFoundError(AppError):
    code = "NOT_FOUND"


class ResidentNotFoundError(AppError):
    code = "RESIDENT_NOT_FOUND"


class AlertNotFoundError(AppError):
    code = "ALERT_NOT_FOUND"


class BatchNotFoundError(AppError):
    code = "BATCH_NOT_FOUND"


class PipelineRunNotFoundError(AppError):
    code = "PIPELINE_RUN_NOT_FOUND"


class UserNotFoundError(AppError):
    code = "USER_NOT_FOUND"


class AlertClosedError(AppError):
    code = "ALERT_CLOSED"


class EmailAlreadyExistsError(AppError):
    code = "EMAIL_ALREADY_EXISTS"


class LastAdminError(AppError):
    code = "LAST_ADMIN"


class PipelineRunInProgressError(AppError):
    code = "PIPELINE_RUN_IN_PROGRESS"


class PayloadTooLargeError(AppError):
    code = "PAYLOAD_TOO_LARGE"


class UnsupportedMediaTypeError(AppError):
    code = "UNSUPPORTED_MEDIA_TYPE"


class RateLimitedError(AppError):
    code = "RATE_LIMITED"


class AccountLockedError(AppError):
    code = "ACCOUNT_TEMPORARILY_LOCKED"


class ProfileNotAllowedError(AppError):
    code = "PROFILE_NOT_ALLOWED"


class AlertResidentMismatchError(AppError):
    code = "ALERT_RESIDENT_MISMATCH"


class ServiceUnavailableError(AppError):
    code = "SERVICE_UNAVAILABLE"


def problem_body(
    code: str, detail: str, errors: Sequence[FieldError] = (), request_id: str | None = None
) -> dict[str, Any]:
    status, title = CATALOGUE[code]
    return {
        "type": TYPE_PREFIX + code,
        "title": title,
        "status": status,
        "detail": detail,
        "request_id": request_id or get_request_id() or "",
        "errors": [{"field": e.field, "code": e.code, "message": e.message} for e in errors],
    }


def _location(loc: Sequence[Any]) -> str:
    parts = [str(p) for p in loc]
    if parts and parts[0] in ("body", "query", "path", "header", "cookie"):
        parts = parts[1:]
    return ".".join(parts)


def validation_field_errors(errors: Sequence[Any]) -> list[FieldError]:
    """Pydantic errors as `errors[]` items: dotted field, Pydantic type, message, no input."""
    items = []
    for error in errors:
        items.append(
            FieldError(
                field=_location(error.get("loc", ())),
                code=str(error.get("type", "invalid")),
                message=str(error.get("msg", "Invalid value.")),
            )
        )
    return items


def append_only_table(exc: DBAPIError) -> str | None:
    """The table named by an `EW001` append-only refusal (TRD 20 PGS-028), else None."""
    orig = getattr(exc, "orig", None)
    if getattr(orig, "sqlstate", None) != "EW001":
        return None
    diag = getattr(orig, "diag", None)
    message = getattr(diag, "message_primary", "") or str(orig)
    parts = message.split()
    return parts[1] if len(parts) > 1 and parts[0] == "table" else "unknown"


def log_unhandled(exc: BaseException) -> None:
    """One ERROR `unhandled_exception` record without the raw message (LOG-070, SEC-085)."""
    from backend.core.logging import format_exception, mask_text

    logger.error(
        "unhandled_exception",
        extra={
            "event": "unhandled_exception",
            "exc_type": type(exc).__name__,
            "exc_message": mask_text(str(exc))[:200],
            "stack": format_exception(exc),
        },
    )
