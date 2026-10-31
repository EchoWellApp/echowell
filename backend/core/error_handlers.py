"""problem+json exception handlers (TRD 05 §4.7 API-095..API-097; TRD 17 LOG-040..LOG-044;
FEAT-019)."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.core.errors import (
    INTERNAL_DETAIL,
    PROBLEM_MEDIA_TYPE,
    AppError,
    FieldError,
    append_only_table,
    log_unhandled,
    problem_body,
    validation_field_errors,
)

logger = logging.getLogger("backend.errors")


def problem_response(
    code: str,
    detail: str,
    errors: Sequence[FieldError] = (),
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = problem_body(code, detail, errors)
    return JSONResponse(
        body, status_code=body["status"], headers=headers, media_type=PROBLEM_MEDIA_TYPE
    )


async def _app_error(_: Request, exc: Exception) -> JSONResponse:
    error = cast(AppError, exc)
    return problem_response(error.code, error.detail, error.errors, error.headers or None)


async def _validation_error(request: Request, exc: Exception) -> JSONResponse:
    raw = cast(RequestValidationError, exc).errors()
    items = validation_field_errors(raw)
    query_only = items and all(str(e.get("loc", ("",))[0]) in ("query", "path") for e in raw)
    if query_only and request.method == "GET":
        return problem_response("INVALID_QUERY_PARAMETER", "A query parameter is not valid.", items)
    return problem_response("VALIDATION_ERROR", "The request is not valid.", items)


def _app_error_behind(exc: BaseException) -> AppError | None:
    """The `AppError` that caused `exc`, also inside the exception group a middleware task group
    raises (e.g. a body over the limit while FastAPI reads it)."""
    pending: list[BaseException] = [exc]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, AppError):
            return current
        if isinstance(current, BaseExceptionGroup):
            pending.extend(current.exceptions)
        pending.extend(e for e in (current.__cause__, current.__context__) if e is not None)
    return None


async def _http_error(request: Request, exc: Exception) -> JSONResponse:
    cause = _app_error_behind(exc)
    if cause is not None:
        return await _app_error(request, cause)
    status = cast(StarletteHTTPException, exc).status_code
    if status == 400:
        return problem_response("VALIDATION_ERROR", "The request body could not be read.")
    if status == 405:
        return problem_response("METHOD_NOT_ALLOWED", "This method is not allowed on this path.")
    if status == 404:
        return problem_response("NOT_FOUND", "The requested resource does not exist.")
    logger.warning("http_exception", extra={"event": "http_exception", "status": status})
    return problem_response("INTERNAL_ERROR", INTERNAL_DETAIL)


async def _operational_error(_: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "database_unavailable",
        extra={"event": "database_unavailable", "exc_type": type(exc).__name__},
    )
    return problem_response(
        "SERVICE_UNAVAILABLE", "The database is not reachable. Try again shortly.",
        headers={"Retry-After": "30"},
    )  # fmt: skip


async def _database_error(_: Request, exc: Exception) -> JSONResponse:
    table = append_only_table(cast(DBAPIError, exc))
    if table is not None:
        logger.error(
            "append_only_violation", extra={"event": "append_only_violation", "table": table}
        )
    else:
        logger.error(
            "database_error", extra={"event": "database_error", "exc_type": type(exc).__name__}
        )
    return problem_response("INTERNAL_ERROR", INTERNAL_DETAIL)


async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
    log_unhandled(exc)
    return problem_response("INTERNAL_ERROR", INTERNAL_DETAIL)


def install_handlers(app: FastAPI) -> None:
    """Register the problem+json handlers (API-095)."""
    app.add_exception_handler(AppError, _app_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(OperationalError, _operational_error)
    app.add_exception_handler(DBAPIError, _database_error)
    app.add_exception_handler(Exception, _unhandled)
