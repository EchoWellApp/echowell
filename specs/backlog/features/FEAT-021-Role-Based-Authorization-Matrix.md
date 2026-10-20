# FEAT-021 Role-based authorization matrix

| Field | Value |
|---|---|
| Epic | Authentication & Security |
| Build phase | Phase 5 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-020 |
| Status | Not Started |

## Purpose

Enforce on the server who may do what: the `require_roles(*roles)` dependency and a declared permission for every route, implementing the TRD 02 §4.26 / TRD 12 §4.6 role matrix for the roles `admin`, `clinician`, `researcher` and the API-key scopes `ingest:write`, `pipeline:run`, with an `access.denied` audit row for every 403. Hiding controls in the frontend is a convenience; this feature is the control.

## Business Context

- BR-16: three roles with least privilege (FR-213); researchers are read-only (SEC-045); analytics only for researchers and admins (FR-243, FR-310); reviews and snoozes only for clinicians and admins (FR-275, OQ-26 interim).
- BR-01: batch ingest is open to `ingest:write` keys and admins (FR-004); single-record ingest only to keys.

## Referenced TRDs

- TRD 12 SEC-040, SEC-042, SEC-045, SEC-108; §4.6 role matrix (endpoint × credential).
- TRD 02 §4.26 role permission matrix; FR-004, FR-213, FR-243, FR-275, FR-310.
- TRD 05 API-013.
- TRD 19 OAS-020; §4.3 endpoint/role summary (E-01..E-32 "Roles" column).
- TRD 25 AGT-062.
- TRD 13 TST-130 (exhaustive matrix, delivered by FEAT-039).

## Scope

- `backend/api/deps.py`: `require_roles(*roles)` returning a dependency that loads the current user (FEAT-020), compares the database role with `roles`, and on mismatch writes an `access.denied` audit row (`entity_type = 'route'`, `entity_id` = route template, `details` `{"status": 403, "code": "FORBIDDEN"}`) and raises 403 `FORBIDDEN`.
- Composite dependencies for the mixed cells: "admin JWT or `ingest:write` key" (`POST /ingest`, via `get_ingest_principal`), "admin JWT or `pipeline:run` key" (`POST /pipeline/run`), and content-negotiated role checks for CSV variants (`GET /scores` CSV: admin, researcher; JSON: admin, clinician, researcher).
- `backend/api/permissions.py` (or equivalent constants module): one declarative table mapping each TRD 12 §4.6 row (method + path) to its allowed roles/scopes, used by routers and by the coverage test.
- `access.denied` audit also for an API key that lacks the required scope (403), using `actor_type = 'api_key'`.
- Test `tests/integration/test_auth_coverage.py` (SEC-042): enumerate `app.routes` and fail if any route other than `/health`, `/auth/login`, `/openapi.json` (and `/docs` outside production) lacks an auth dependency.
- Role tests for the routers existing at Phase 5 start (auth endpoints, health); each later endpoint feature attaches its permission from the table and adds its role tests.

## Out of Scope

- The exhaustive endpoint × credential test `tests/security/test_auth_matrix.py` across all 33 matrix rows (TST-130, SEC-041), delivered by FEAT-039 once every endpoint exists.
- Self-role-change and self-deactivation rules of `PATCH /users/{id}` (SEC-044, FEAT-037).
- Frontend role-based hiding (SEC-043, FEAT-064).
- The OAS-021..OAS-026 data assertions on specific endpoint responses (verified by the endpoint and contract features).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-021-FR-01 | `require_roles(*roles)` shall raise 403 `FORBIDDEN` when the current user's role, read from the database (not the token), is not in `roles`. | API-013, SEC-034 |
| FEAT-021-FR-02 | Every endpoint shall enforce the TRD 12 §4.6 matrix on the server; for each row the allowed callers are exactly those marked Y, others receive 401 (wrong credential type) or 403 `FORBIDDEN` (wrong role or scope). | SEC-040, FR-213 |
| FEAT-021-FR-03 | User roles shall be exactly `admin`, `clinician`, `researcher`; API-key scopes exactly `ingest:write` and `pipeline:run`. | AGT-062 |
| FEAT-021-FR-04 | `POST /ingest` shall accept an `ingest:write` key or an admin user; `POST /sessions` only an `ingest:write` key. | FR-004, TRD 02 §4.26 |
| FEAT-021-FR-05 | `GET /analytics` and `GET /analytics/baselines` (JSON or CSV) shall allow only `researcher` and `admin`; a clinician receives 403. | FR-243, FR-310 |
| FEAT-021-FR-06 | `POST /alerts/{id}/reviews`, `POST /alerts/{id}/snooze` and `POST /residents/{code}/notes` shall allow only `clinician` and `admin`. | FR-275, TRD 02 §4.26 |
| FEAT-021-FR-07 | `GET /scores` JSON shall allow admin, clinician, researcher; with `Accept: text/csv` only admin and researcher. | TRD 12 §4.6, TRD 02 §4.26 |
| FEAT-021-FR-08 | `GET /pipeline/runs`, `GET /pipeline/runs/{id}` and `GET /ingest/batches/{id}` shall allow admin and researcher; `POST /pipeline/run` admin or a `pipeline:run` key. | TRD 12 §4.6 |
| FEAT-021-FR-09 | `GET/POST /users` and `PATCH /users/{id}` shall allow admin only. | TRD 12 §4.6 |
| FEAT-021-FR-10 | Researchers shall have read-only API access: no researcher request creates, updates, reviews or snoozes any record. | SEC-045 |
| FEAT-021-FR-11 | Each 403 response shall write an `access.denied` audit row; 401 responses are logged in application logs only. | SEC-108 |
| FEAT-021-FR-12 | A route without an explicit auth dependency shall fail `tests/integration/test_auth_coverage.py`, which allows only `/health`, `/auth/login` and `/openapi.json` (plus `/docs` outside production) to be anonymous. | SEC-042 |
| FEAT-021-FR-13 | Each endpoint shall return only the success codes of the TRD 19 endpoint/role summary and error codes from the TRD 05 catalogue (401, 403 included). | OAS-020 |

## Inputs

- `CurrentUser` (role, active) or `Principal` from FEAT-020; route template; request `Accept` header for CSV variants.

## Outputs

- Pass-through to the handler, or 403 `FORBIDDEN` with an `access.denied` audit row, or 401 from FEAT-020.
- The permission table used by later endpoint features.

## Data Flow

Request → FEAT-020 authenticates (401 on failure) → `require_roles`/composite dependency compares the database role or key scope with the route's entry in the permission table → allowed: handler runs → denied: `access.denied` audit row written (committed despite the error response) → 403 Problem.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-020

- FEAT-020 provides `get_current_user`, `get_api_key(scope)` and `get_ingest_principal`.

Features that build directly on this one (BACKLOG.md §4): FEAT-024, FEAT-027, FEAT-029, FEAT-030, FEAT-032, FEAT-033, FEAT-034, FEAT-036, FEAT-037.

## Database Impact

- Tables read: `users` (role, active via FEAT-020).
- Tables written: `audit_logs` (`access.denied`).
- Tables created or modified: none.

## API Impact

- Applies the matrix to E-02..E-32 (TRD 19 §4.3 "Roles" column: A = admin, C = clinician, Rs = researcher, K = key).
- No endpoint exposed.

## Frontend Impact

None in code; the frontend mirrors these rules for display only (SEC-043, FEAT-064) and shows the access-denied state "You do not have access to this page." on 403 (FR-310, FE-037, FEAT-064).

## Analytics Impact

None.

## Security Requirements

- Authorization decided server-side from database state on every request (SEC-034, SEC-040).
- Deny by default: unauthenticated routes limited to the SEC-042 allow-list.
- 403s audited (SEC-108).

## Error Handling

| Condition | Response |
|---|---|
| Valid user, role not allowed | 403 `FORBIDDEN` + `access.denied` audit row |
| API key on a user-only endpoint | 401 (wrong credential type, TRD 12 §4.6 legend; SEC-027) |
| User token on a key-only endpoint (`POST /sessions`) | 401 for wrong credential type per TRD 12 §4.6 legend |
| API key lacking the scope | 403 `FORBIDDEN` (API-014) + `access.denied` audit row |

## Logging Requirements

- Audit `access.denied` with `{"status": 403, "code"}` and the route template (TRD 12 §4.12, SEC-108).
- 401s appear only in the `request_completed` access log (INFO, LOG-010).

## Testing Requirements

- Unit (`tests/unit/backend/api/test_require_roles.py`): role allowed/denied using a database role that differs from the token's `role` claim (role change takes effect immediately).
- Integration (`tests/integration/test_auth_coverage.py`): SEC-042 route enumeration.
- Integration (`tests/integration/api/test_role_checks.py`): for the endpoints present in this Phase 5 PR, each matrix row's cells (anonymous, admin, clinician, researcher, `ingest:write` key, `pipeline:run` key) return the TRD 12 §4.6 status; 403 writes one `access.denied` row; 401 writes none. TRD 25 §4.6 Phase 5 required role tests: review (clinician, admin) and analytics (researcher, admin; clinician 403) are added by FEAT-031 and FEAT-035 using this mechanism.
- TST-130 (full matrix) is delivered by FEAT-039.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-021-AC-01 | `tests/integration/test_auth_coverage.py` passes, and adding a test route without an auth dependency makes it fail. | SEC-042 |
| FEAT-021-AC-02 | A user whose database role is `researcher` but whose token claims `admin` receives 403 `FORBIDDEN` on an admin-only route. Verified by: Integration (`tests/integration/api/test_role_checks.py`). | API-013, SEC-034 |
| FEAT-021-AC-03 | Every 403 produced in the role-check suite creates exactly one `access.denied` audit row with `details.status = 403`; no 401 creates an audit row. Verified by: Integration (`tests/integration/api/test_role_checks.py`). | SEC-108 |
| FEAT-021-AC-04 | The permission table contains one entry per row of TRD 12 §4.6 (33 endpoint rows) and its allowed callers equal the matrix cells (compared by a unit test against a transcription of the matrix). Verified by: Integration (`tests/integration/api/test_role_checks.py`). | SEC-040, FR-213 |
| FEAT-021-AC-05 | With the analytics and review routers present, a clinician gets 403 on `GET /analytics` and a researcher gets 403 on `POST /alerts/{id}/reviews` and `POST /alerts/{id}/snooze`. Verified by: Integration (`tests/integration/api/test_role_checks.py`). | FR-310, FR-275, SEC-045 |
| FEAT-021-AC-06 | `POST /ingest` succeeds for an admin user and an `ingest:write` key and returns 403 for a clinician; `POST /sessions` returns 401 for any user token. Verified by: Integration (`tests/integration/api/test_role_checks.py`). | FR-004, TRD 12 §4.6 |

## Definition of Done

- All FEAT-021 acceptance criteria pass (AC-05 and AC-06 once the corresponding routers exist in the same Phase 5 PR).
- The permission table is the single source used by routers; delivered in the Phase 5 PR.

## Implementation Notes

- Write the `access.denied` row in its own committed transaction before raising, because `get_db()` rolls back on exceptions (API-011); TRD 12 SEC-101 prescribes this mechanism (TRD 24 D-87).
- Use the route template (`request.scope["route"].path`) as `entity_id`, never the concrete path with resident codes beyond study IDs.
- TRD 12 §4.6 and TRD 02 §4.26 are consistent; keep both role names and scope names exactly as AGT-062 lists them.
- The BACKLOG row cites OAS-020 only (aligned in the PR #2 consistency fixes); OAS-021..OAS-026 are response-content checks realised by FEAT-027, FEAT-034, FEAT-035 and FEAT-038.
