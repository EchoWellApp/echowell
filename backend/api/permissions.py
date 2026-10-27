"""Server-side role matrix of TRD 12 §4.6 (SEC-040, SEC-041; FEAT-021).

One entry per matrix row, keyed `"<METHOD> <path>"` as the path appears under `/api/v1`. Every
route depends on `deps.authorize(<key>)`, which reads this table, so the matrix is enforced in one
place and `tests/integration/api/test_role_checks.py` compares it with the TRD.
"""

from __future__ import annotations

from dataclasses import dataclass

ADMIN, CLINICIAN, RESEARCHER = "admin", "clinician", "researcher"
ALL_ROLES = frozenset({ADMIN, CLINICIAN, RESEARCHER})
INGEST_WRITE, PIPELINE_RUN = "ingest:write", "pipeline:run"


@dataclass(frozen=True)
class Access:
    roles: frozenset[str] = frozenset()
    api_key_scope: str | None = None
    anonymous: bool = False


_STAFF = Access(roles=ALL_ROLES)
_ADMIN_RESEARCHER = Access(roles=frozenset({ADMIN, RESEARCHER}))
_ADMIN_CLINICIAN = Access(roles=frozenset({ADMIN, CLINICIAN}))
_ADMIN_ONLY = Access(roles=frozenset({ADMIN}))

PERMISSIONS: dict[str, Access] = {
    "GET /health": Access(anonymous=True),
    "POST /auth/login": Access(anonymous=True),
    "POST /auth/logout": _STAFF,
    "GET /auth/me": _STAFF,
    "POST /sessions": Access(api_key_scope=INGEST_WRITE),
    "POST /ingest": Access(roles=frozenset({ADMIN}), api_key_scope=INGEST_WRITE),
    "GET /ingest/batches/{id}": _ADMIN_RESEARCHER,
    "GET /residents": _STAFF,
    "GET /residents/{resident_code}": _STAFF,
    "GET /residents/{resident_code}/checkins": _STAFF,
    "GET /residents/{resident_code}/features": _STAFF,
    "GET /scores": _STAFF,
    "GET /scores (text/csv)": _ADMIN_RESEARCHER,
    "GET /alerts": _STAFF,
    "POST /alerts/{id}/reviews": _ADMIN_CLINICIAN,
    "GET /alerts/{id}/reviews": _STAFF,
    "POST /alerts/{id}/snooze": _ADMIN_CLINICIAN,
    "GET /data-alerts": _STAFF,
    "GET /config/ui": _STAFF,
    "GET /residents/{resident_code}/notes": _STAFF,
    "POST /residents/{resident_code}/notes": _ADMIN_CLINICIAN,
    "GET /devices": _STAFF,
    "GET /analytics": _ADMIN_RESEARCHER,
    "GET /analytics/baselines": _ADMIN_RESEARCHER,
    "POST /pipeline/run": Access(roles=frozenset({ADMIN}), api_key_scope=PIPELINE_RUN),
    "GET /pipeline/runs": _ADMIN_RESEARCHER,
    "GET /pipeline/runs/{id}": _ADMIN_RESEARCHER,
    "GET /admissions": _STAFF,
    "GET /admissions/{resident_code}/comparison": _STAFF,
    "GET /facility/reference-ranges": _STAFF,
    "GET /users": _ADMIN_ONLY,
    "POST /users": _ADMIN_ONLY,
    "PATCH /users/{id}": _ADMIN_ONLY,
    "GET /openapi.json": Access(anonymous=True),
}
