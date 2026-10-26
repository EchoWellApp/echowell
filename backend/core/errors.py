"""Application errors raised by services and dependencies (TRD 05 API-004, API-095).

The `application/problem+json` handler that renders them is added by FEAT-019 (D-48).
"""

from __future__ import annotations


class AppError(Exception):
    """Base class of every expected failure; `code` is the TRD 05 error-catalogue code."""

    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class InvalidQueryParameterError(AppError):
    """A query parameter is out of range (API-016)."""

    status_code = 422
    code = "INVALID_QUERY_PARAMETER"


class PasswordPolicyError(AppError):
    """A password breaks TRD 12 SEC-012 (length, equal to e-mail, common password)."""

    status_code = 422
    code = "PASSWORD_POLICY_VIOLATION"
