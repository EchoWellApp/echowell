# Role-based authorization matrix

## Feature Description

FEAT-021 enforces the TRD 12 §4.6 / TRD 02 §4.26 role matrix on the server. Every route declares `authorize("<METHOD> <path>")`, which reads the single declarative table `backend/api/permissions.py::PERMISSIONS` (roles `admin`, `clinician`, `researcher`; API-key scopes `ingest:write`, `pipeline:run`). A caller with the wrong credential type receives 401; a valid user with the wrong database role, or a key without the scope, receives 403 `FORBIDDEN` and one `access.denied` audit row (committed in its own transaction); 401 responses are not audited. The role is read from `users` on every request, never from the token claim. Mixed cells: `POST /ingest` accepts an admin JWT or an `ingest:write` key; `POST /pipeline/run` an admin JWT or a `pipeline:run` key; `GET /scores` with `Accept: text/csv` is limited to admin and researcher. `tests/integration/test_auth_coverage.py` fails if a route other than `/health`, `/auth/login`, `/openapi.json` (and `/docs` outside production) lacks an auth dependency. The frontend shows "You do not have access to this page." on a 403 (display only).

## Preconditions

- Local development stack running (backend on `http://localhost:8000`, frontend on `http://localhost:3000`); `.env` from `.env.development.example` (`APP_ENV=local`, `PIPELINE_PROFILE=test_v0_1`, `SEED_*`, `JWT_SECRET` set; values never written down).
- Database seeded: `python -m backend.cli seed test_v0_1 --reset` (R09 and R10 have open alerts).
- Bearer tokens `ADMIN`, `CLIN`, `RES` from `POST /api/v1/auth/login` for the three seeded users (send each login with a distinct `X-Forwarded-For: 203.0.113.<n>` or wait 60 s after five logins; FEAT-022).
- Keys: `SEED_INGEST_API_KEY` (scopes `ingest:write`, `pipeline:run`); `python -m backend.cli create-api-key --name qa-ingest-only` (scope `ingest:write` only) and `--name qa-pipeline-only --scope pipeline:run`.
- R09's open alert id: `GET /api/v1/alerts` as `CLIN`, item with `resident_code` `R09` → `ALERT_ID`.
- `psql` for read-only checks on `audit_logs`.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-021-01 | Route-coverage test passes and fails when an unprotected route is added | High | Security |
| TC-021-02 | Database role wins over the token's `role` claim | High | Security |
| TC-021-03 | Every 403 writes exactly one `access.denied` row; 401 writes none | High | Database |
| TC-021-04 | Permission table has one entry per TRD 12 §4.6 row with equal cells | High | Documentation |
| TC-021-05 | Analytics: researcher and admin allowed, clinician 403 | High | API |
| TC-021-06 | Reviews, snoozes and notes: clinician and admin allowed, researcher 403 | High | API |
| TC-021-07 | `POST /ingest` admin or `ingest:write` key; clinician 403; `POST /sessions` user token 401 | High | API |
| TC-021-08 | `GET /scores` JSON for all roles; CSV only admin and researcher | Medium | API |
| TC-021-09 | Pipeline run and batch endpoints | Medium | API |
| TC-021-10 | User management is admin-only | Medium | API |
| TC-021-11 | Researcher is read-only: no write succeeds and nothing is stored | High | Security |
| TC-021-12 | Wrong credential type returns 401; key without scope returns 403 with an `api_key` audit row | High | Negative |
| TC-021-13 | Roles and scopes are exactly the three roles and two scopes | Medium | Negative |
| TC-021-14 | Frontend shows the access-denied state for a clinician on the Study team page | Medium | UI |
| TC-021-15 | Exhaustive matrix and role-check suites pass | High | Security |

### TC-021-01 Route-coverage test passes and fails when an unprotected route is added

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `pytest -m integration tests/integration/test_auth_coverage.py -q` | Passes |
| 2 | In a throw-away local working copy (never committed), add to any router a route `@router.get("/qa-open")` whose handler has no `authorize(...)` dependency; rerun the test | Fails, naming the route `/api/v1/…/qa-open` as lacking an auth dependency |
| 3 | Discard the change (`git checkout -- <file>` in the throw-away copy) and rerun | Passes again |
| 4 | Without credentials call `GET /api/v1/openapi.json` and `GET /api/v1/docs` | 200 and 200 (`/docs` exists only outside production) |

### TC-021-02 Database role wins over the token's `role` claim

| Step | Action | Expected Result |
|---|---|---|
| 1 | In a REPL with the environment loaded, mint a token for the researcher's user id with role claim `admin`: `create_access_token(<researcher uuid>, "admin", os.environ["JWT_SECRET"], 60)` | Token string (claim `role` = `admin`) |
| 2 | `GET /api/v1/users` with that token | 403; `type` `urn:echowell:error:FORBIDDEN`, `title` `Not allowed for this role`, `detail` `Not allowed for this role.` |
| 3 | `SELECT actor_type, actor_id, details FROM audit_logs WHERE action = 'access.denied' ORDER BY id DESC LIMIT 1;` | `actor_type` `user`; `actor_id` = researcher id; `details` `{"status": 403, "code": "FORBIDDEN"}` |
| 4 | Run `pytest -m integration tests/integration/api/test_role_checks.py -q -k role_comes_from_the_database_not_the_token` | Passes |

### TC-021-03 Every 403 writes exactly one `access.denied` row; 401 writes none

| Step | Action | Expected Result |
|---|---|---|
| 1 | Record `SELECT count(*) FROM audit_logs WHERE action = 'access.denied';` | Baseline D |
| 2 | As `CLIN`, `GET /api/v1/analytics` with `X-Request-ID: qa-rbac-403-01` | 403 `FORBIDDEN` |
| 3 | `SELECT count(*), max(details::text) FROM audit_logs WHERE action = 'access.denied' AND request_id = 'qa-rbac-403-01';` | `1`; details contain `"status": 403` and `"code": "FORBIDDEN"` |
| 4 | Without credentials, `GET /api/v1/analytics` with `X-Request-ID: qa-rbac-401-01` | 401 `NOT_AUTHENTICATED` |
| 5 | `SELECT count(*) FROM audit_logs WHERE request_id = 'qa-rbac-401-01';` | 0 |
| 6 | Re-count all `access.denied` rows | D + 1 |

Note: TRD 12 §4.12 specifies `entity_type` `route` and `entity_id` = route template for `access.denied`; `backend/api/deps.py:196` writes both as NULL. Check the columns and record the difference.

### TC-021-04 Permission table has one entry per TRD 12 §4.6 row with equal cells

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `backend/api/permissions.py` and TRD 12 §4.6 side by side | Each TRD row (`GET /health` … `GET /openapi.json`) has exactly one `PERMISSIONS` key; `GET /scores (JSON)` maps to `"GET /scores"` and `GET /scores (Accept: text/csv)` to `"GET /scores (text/csv)"` |
| 2 | Compare cells for `POST /ingest`, `POST /pipeline/run`, `GET /ingest/batches/{id}`, `GET /analytics/baselines`, `PATCH /users/{id}` | `POST /ingest`: admin + `ingest:write`; `POST /pipeline/run`: admin + `pipeline:run`; batches: admin, researcher; baselines: admin, researcher; users: admin only |
| 3 | Run `pytest -m integration tests/integration/api/test_role_checks.py -q -k permissions_equal_the_trd_matrix` | Passes |

Note: FEAT-021-AC-04 is aligned to the TRD (TRD 24 D-184): it names the 34 rows of the TRD 12 §4.6 table (including `GET /health` and `GET /openapi.json`); `PERMISSIONS` has 34 keys.

### TC-021-05 Analytics: researcher and admin allowed, clinician 403

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/analytics` as `RES` and as `ADMIN` | 200 and 200 |
| 2 | `GET /api/v1/analytics` as `CLIN` | 403 `FORBIDDEN`; one `access.denied` row |
| 3 | `GET /api/v1/analytics/baselines` as `CLIN`, then with `Accept: text/csv` as `CLIN` | 403 for both |
| 4 | `GET /api/v1/analytics/baselines` with `Accept: text/csv` as `RES` | 200; `Content-Type` starts with `text/csv` |

### TC-021-06 Reviews, snoozes and notes: clinician and admin allowed, researcher 403

| Step | Action | Expected Result |
|---|---|---|
| 1 | As `RES`, `POST /api/v1/alerts/<ALERT_ID>/reviews` with `{"outcome": "no_concern", "explanations": []}` | 403 `FORBIDDEN`; no `alert_reviews` row added (`SELECT count(*) FROM alert_reviews;` unchanged) |
| 2 | As `RES`, `POST /api/v1/alerts/<ALERT_ID>/snooze` with `{"hours": 24}` | 403 `FORBIDDEN`; `alerts.snoozed_until` of the alert unchanged |
| 3 | As `RES`, `POST /api/v1/residents/R09/notes` with `{"note_type": "observation", "body": "QA synthetic note"}` | 403 `FORBIDDEN`; `staff_notes` count unchanged |
| 4 | As `CLIN`, `POST /api/v1/alerts/<ALERT_ID>/snooze` with `{"hours": 24}` | 2xx (allowed) |
| 5 | As `ADMIN`, `POST /api/v1/residents/R09/notes` with the same note body | 201 |
| 6 | `GET /api/v1/alerts/<ALERT_ID>/reviews` and `GET /api/v1/residents/R09/notes` as `RES` | 200 and 200 (reads allowed) |

### TC-021-07 `POST /ingest` admin or `ingest:write` key; clinician 403; `POST /sessions` user token 401

| Step | Action | Expected Result |
|---|---|---|
| 1 | As `ADMIN`, `POST /api/v1/ingest` with a JSON batch of one synthetic R01/D01 record | Not 401/403 (admin allowed; outcome per ingest rules) |
| 2 | `POST /api/v1/ingest` with `X-API-Key: <qa-ingest-only key>` and the same body shape (new `session_id`) | Not 401/403 |
| 3 | As `CLIN`, `POST /api/v1/ingest` | 403 `FORBIDDEN`; one `access.denied` row |
| 4 | `POST /api/v1/sessions` with `ADMIN`, `CLIN`, `RES` tokens (no key) | 401 for each; no `access.denied` row |
| 5 | `POST /api/v1/sessions` with `X-API-Key: <qa-ingest-only key>` and a synthetic record | Not 401/403 |

### TC-021-08 `GET /scores` JSON for all roles; CSV only admin and researcher

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/scores?resident_code=R09` as `ADMIN`, `CLIN`, `RES` (default JSON) | 200 for each |
| 2 | Same with `Accept: text/csv` as `CLIN` | 403 `FORBIDDEN`; one `access.denied` row |
| 3 | Same with `Accept: text/csv` as `RES` and as `ADMIN` | 200; `Content-Type` starts with `text/csv` |

### TC-021-09 Pipeline run and batch endpoints

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/pipeline/runs` as `ADMIN` and `RES` | 200 and 200 |
| 2 | `GET /api/v1/pipeline/runs` as `CLIN` | 403 |
| 3 | `POST /api/v1/pipeline/run` `{"scope": ["R01"]}` as `CLIN` and as `RES` | 403 and 403 |
| 4 | `POST /api/v1/pipeline/run` with `X-API-Key: <qa-ingest-only key>` | 403 `FORBIDDEN` (scope `pipeline:run` missing); `access.denied` with `actor_type` `api_key` |
| 5 | `POST /api/v1/pipeline/run` `{"scope": "all"}` with `X-API-Key: <qa-pipeline-only key>` | 202 |
| 6 | `GET /api/v1/ingest/batches/<id from step 1 of TC-021-07>` as `CLIN`, then as `RES` | 403, then 200 |

### TC-021-10 User management is admin-only

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/users` as `ADMIN` | 200 |
| 2 | `GET /api/v1/users` as `CLIN` and `RES` | 403 each |
| 3 | `POST /api/v1/users` as `CLIN` with a syntactically valid body for `qa.new@example.com` | 403; no `users` row for that e-mail |
| 4 | `PATCH /api/v1/users/<clinician id>` as `RES` with `{"display_name": "QA"}` | 403; display name unchanged |

### TC-021-11 Researcher is read-only: no write succeeds and nothing is stored

| Step | Action | Expected Result |
|---|---|---|
| 1 | Record counts of `alert_reviews`, `staff_notes`, `users`, `pipeline_runs`, `raw_sessions` | Baselines |
| 2 | As `RES`, call every write endpoint: `POST /alerts/<ALERT_ID>/reviews`, `POST /alerts/<ALERT_ID>/snooze`, `POST /residents/R01/notes`, `POST /users`, `PATCH /users/<id>`, `POST /pipeline/run`, `POST /ingest`, `POST /sessions` | 403 for the first seven; 401 for `POST /sessions` |
| 3 | Re-count | All unchanged; `access.denied` count increased by 7 |

### TC-021-12 Wrong credential type returns 401; key without scope returns 403 with an `api_key` audit row

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents` with only `X-API-Key: $SEED_INGEST_API_KEY` | 401 `NOT_AUTHENTICATED` with `WWW-Authenticate: Bearer`; no audit row |
| 2 | `POST /api/v1/sessions` with `X-API-Key: <qa-pipeline-only key>` | 403 `FORBIDDEN`, `detail` `This API key does not have the scope ingest:write.` |
| 3 | Newest `access.denied` row | `actor_type` `api_key`; `actor_id` = the key id; `details` `{"status": 403, "code": "FORBIDDEN"}` |

### TC-021-13 Roles and scopes are exactly the three roles and two scopes

| Step | Action | Expected Result |
|---|---|---|
| 1 | As `ADMIN`, `PATCH /api/v1/users/<clinician id>` with `{"role": "superuser"}` | 422 `VALIDATION_ERROR` with an `errors[]` item for `role` |
| 2 | `python -m backend.cli create-api-key --name qa-bad --scope admin` | Exit code 2; `Refused: unknown scope admin (allowed: ingest:write, pipeline:run)` |
| 3 | `SELECT DISTINCT role FROM users;` and `SELECT DISTINCT unnest(scopes) FROM api_keys;` | Roles within {`admin`, `clinician`, `researcher`}; scopes within {`ingest:write`, `pipeline:run`} |

### TC-021-14 Frontend shows the access-denied state for a clinician on the Study team page

| Step | Action | Expected Result |
|---|---|---|
| 1 | Sign in at `http://localhost:3000/login` as `clinician@example.com` | Resident list opens; no "Study team" or "Admin" link in the navigation |
| 2 | Type `http://localhost:3000/study` in the address bar | Page shows "You do not have access to this page."; no analytics data rendered |
| 3 | Sign in as the researcher and open `/study` | Study team page renders |

### TC-021-15 Exhaustive matrix and role-check suites pass

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `pytest -m integration tests/integration/api/test_role_checks.py -q` | All pass (every matrix cell for anonymous, admin, clinician, researcher, `ingest:write` key, `pipeline:run` key) |
| 2 | Run `pytest -m security tests/security/test_auth_matrix.py -q` | All pass (TST-130, delivered with FEAT-039) |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | Allowed caller on each endpoint of TC-021-05..TC-021-10 | 2xx success code of the TRD 19 endpoint summary |
| 2 | Wrong role | 403 Problem `urn:echowell:error:FORBIDDEN`, title `Not allowed for this role` |
| 3 | Wrong credential type / no credential | 401 (`NOT_AUTHENTICATED`) |
| 4 | Key lacking scope | 403 `FORBIDDEN` |
| 5 | No endpoint returns a status code outside its TRD 19 success codes and the TRD 05 catalogue | Checked by the contract tests `pytest -m contract tests/contract -q` (OAS-020) |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT count(*) FROM audit_logs WHERE action = 'access.denied';` delta over a run | Equals the number of 403 responses produced |
| 2 | `SELECT DISTINCT details::text FROM audit_logs WHERE action = 'access.denied';` | Only `{"code": "FORBIDDEN", "status": 403}` |
| 3 | `SELECT DISTINCT actor_type FROM audit_logs WHERE action = 'access.denied';` | Subset of {`user`, `api_key`} |
| 4 | Write tables after researcher calls (TC-021-11) | Unchanged |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Clinician on `GET /analytics` | 403 + `access.denied` |
| 2 | Researcher on review, snooze, note | 403, nothing stored |
| 3 | User token on `POST /sessions` | 401 |
| 4 | API key on `GET /residents` | 401 |
| 5 | `ingest:write`-only key on `POST /pipeline/run` | 403 + `access.denied` (`api_key`) |
| 6 | Token claim `admin` with database role `researcher` on `GET /users` | 403 |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-021-AC-01 | `test_auth_coverage.py` passes; adding a route without an auth dependency makes it fail | TC-021-01 |
| FEAT-021-AC-02 | Database role `researcher`, token claim `admin`: 403 `FORBIDDEN` on an admin-only route | TC-021-02 |
| FEAT-021-AC-03 | Each 403 creates exactly one `access.denied` row with `details.status = 403`; no 401 creates a row | TC-021-03, TC-021-11, TC-021-12 |
| FEAT-021-AC-04 | Permission table has one entry per TRD 12 §4.6 row and equal cells (unit comparison passes) | TC-021-04 |
| FEAT-021-AC-05 | Clinician 403 on `GET /analytics`; researcher 403 on `POST /alerts/{id}/reviews` and `POST /alerts/{id}/snooze` | TC-021-05, TC-021-06 |
| FEAT-021-AC-06 | `POST /ingest` succeeds for admin and `ingest:write` key, 403 for clinician; `POST /sessions` 401 for any user token | TC-021-07 |

## Test Data Requirements

- `test_v0_1` seed: three users with `SEED_*` passwords; open alerts of R09 and R10; residents R01, R09.
- Keys: `test-ingest` (`SEED_INGEST_API_KEY`), synthetic `qa-ingest-only` and `qa-pipeline-only` from the CLI.
- Synthetic records of R01 on D01 with new `session_id` values (e.g. `R01-20261031-03`, `R01-20261031-04`); note text "QA synthetic note"; synthetic user `qa.new@example.com`.
- `JWT_SECRET` read inside the REPL only (TC-021-02).

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-021-FR-01 / API-013 / SEC-034 | FEAT-021 | TC-021-02 |
| FEAT-021-FR-02 / SEC-040 / FR-213 | FEAT-021 | TC-021-04, TC-021-15 |
| FEAT-021-FR-03 / AGT-062 | FEAT-021 | TC-021-13 |
| FEAT-021-FR-04 / FR-004 | FEAT-021 | TC-021-07 |
| FEAT-021-FR-05 / FR-243 / FR-310 | FEAT-021 | TC-021-05, TC-021-14 |
| FEAT-021-FR-06 / FR-275 | FEAT-021 | TC-021-06 |
| FEAT-021-FR-07 / TRD 12 §4.6 | FEAT-021 | TC-021-08 |
| FEAT-021-FR-08 / TRD 12 §4.6 | FEAT-021 | TC-021-09 |
| FEAT-021-FR-09 / TRD 12 §4.6 | FEAT-021 | TC-021-10 |
| FEAT-021-FR-10 / SEC-045 | FEAT-021 | TC-021-11 |
| FEAT-021-FR-11 / SEC-108 | FEAT-021 | TC-021-03, TC-021-12 |
| FEAT-021-FR-12 / SEC-042 | FEAT-021 | TC-021-01 |
| FEAT-021-FR-13 / OAS-020 | FEAT-021 | API Validation 5 |
| TST-130 | FEAT-021 (mechanism), FEAT-039 (suite) | TC-021-15 |
| SEC-043 / FE-037 (display only) | FEAT-021, FEAT-064 | TC-021-14 |
