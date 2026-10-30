"""OpenAPI response declarations shared by the routers (TRD 19 §4.5 `components/responses`).

`errors(401, 422)` documents Problem responses for the given status codes; the custom OpenAPI
builder (`backend.api.openapi`) replaces them with references to the TRD 19 response components.
"""

from __future__ import annotations

from typing import Any

PROBLEM_REF = {"$ref": "#/components/schemas/Problem"}
_DESCRIPTIONS = {
    401: "Unauthorized",
    403: "Forbidden",
    404: "NotFound",
    409: "Conflict",
    413: "PayloadTooLarge",
    415: "UnsupportedMediaType",
    422: "Unprocessable",
    429: "TooManyRequests",
}


def errors(*statuses: int) -> dict[int | str, dict[str, Any]]:
    return {
        status: {
            "description": _DESCRIPTIONS[status],
            "content": {"application/problem+json": {"schema": PROBLEM_REF}},
        }
        for status in statuses
    }
