# User management API (GET/POST/PATCH /api/v1/users)

## Feature Description

FEAT-037 lets an admin list dashboard accounts, create an account (e-mail, display name, role, initial password) and change an account's display name, role, active flag or password through `GET /api/v1/users`, `POST /api/v1/users` and `PATCH /api/v1/users/{id}` (TRD 19 E-25, E-26, E-27). Accounts are never deleted. An admin cannot change their own role or deactivate themselves, the system never ends up without an active admin (`LAST_ADMIN`, a service-level invariant), passwords follow the SEC-012 policy and are stored as argon2id hashes, and every create or update writes an audit row (`user.created`, `user.updated`) that never contains the password or its hash.

## Preconditions

- Local Docker Compose (demo profile) running per `docs/deployment.md`, seeded with `python -m backend.cli seed test_v0_1 --reset`; API reachable at `http://localhost:8000/api/v1`.
- Seeded users `admin@example.com` (admin), `clinician@example.com` (clinician), `researcher@example.com` (researcher), passwords from `SEED_ADMIN_PASSWORD`, `SEED_CLINICIAN_PASSWORD`, `SEED_RESEARCHER_PASSWORD` in the environment file.
- A Bearer token per role obtained with `POST /api/v1/auth/login` (body `{"email": "<seeded e-mail>", "password": "$SEED_<ROLE>_PASSWORD"}`); referred to below as ADMIN_TOKEN, CLINICIAN_TOKEN, RESEARCHER_TOKEN.
- The ingest API key from the environment file (`SEED_INGEST_API_KEY`), referred to as INGEST_KEY.
- `psql` access to the local database (read-only `SELECT`).
- A tester-chosen new password of 14–20 characters that is not in `backend/core/common_passwords.txt` and is not the e-mail address; referred to as NEW_PW (never written into the test record).
- For TC-037-12: the local development stack (README quick start) with the test database for `pytest`.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-037-01 | Admin creates a user with a valid 14-character password | High | Positive |
| TC-037-02 | Stored password hash uses argon2id with the SEC-010 parameters and the e-mail is lower-cased | High | Database |
| TC-037-03 | Password policy violations ("short", "password1234", 129 characters, password equal to e-mail) return 422 and create no user | High | Negative |
| TC-037-04 | Duplicate e-mail in a different case returns 409 `EMAIL_ALREADY_EXISTS` | High | Negative |
| TC-037-05 | Admin lists users with role and active filters and pagination; no `password_hash` | High | API |
| TC-037-06 | Admin PATCHes another user's role and active flag; audit row lists changed fields | High | Positive |
| TC-037-07 | Role / active change takes effect on the user's next request | Medium | Security |
| TC-037-08 | PATCH display name and password; audit lists both names, never the password | Medium | Positive |
| TC-037-09 | Admin cannot change their own role or deactivate themselves (403) | High | Negative |
| TC-037-10 | Admin may change their own display name | Medium | Positive |
| TC-037-11 | Unknown id, empty PATCH, unknown role, extra property and malformed body are rejected | High | Negative |
| TC-037-12 | Last-admin guard raises `LAST_ADMIN` (409) and writes nothing (service-level test) | High | Negative |
| TC-037-13 | No DELETE route: `DELETE /users/{id}` returns 405 or 404; user still present | High | Negative |
| TC-037-14 | Clinician and researcher receive 403, API key and anonymous receive 401 on all three endpoints | High | Security |

### TC-037-01 Admin creates a user with a valid 14-character password

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/users` with `Authorization: Bearer ADMIN_TOKEN`, `Content-Type: application/json`, body `{"email": "New.Clinician@Example.TEST", "display_name": "New clinician", "role": "clinician", "password": "<NEW_PW, 14 characters>"}` | HTTP 201; `Content-Type: application/json`; header `X-Request-ID` present |
| 2 | Inspect the response body | Body is a `User` with exactly the keys `id` (uuid), `email`, `display_name`, `role`, `active`, `last_login_at`, `created_at`; `email` = "new.clinician@example.test"; `display_name` = "New clinician"; `role` = "clinician"; `active` = true; `last_login_at` = null |
| 3 | Search the raw response text for `password` | Neither `password` nor `password_hash` appears; the response has no `meta` block |
| 4 | `SELECT action, actor_type, actor_id, entity_type, entity_id, details FROM audit_logs WHERE action = 'user.created' ORDER BY id DESC LIMIT 1;` | One row: `action` = `user.created`, `actor_type` = `user`, `actor_id` = the seeded admin's users.id, `entity_type` = `user`, `entity_id` = the new id from step 2, `details` = `{"role": "clinician"}` |

### TC-037-02 Stored password hash uses argon2id with the SEC-010 parameters and the e-mail is lower-cased

| Step | Action | Expected Result |
|---|---|---|
| 1 | After TC-037-01: `SELECT email, role, active, left(password_hash, 31) AS prefix FROM users WHERE id = '<new id>';` | `email` = `new.clinician@example.test`; `role` = `clinician`; `active` = true; `prefix` = `$argon2id$v=19$m=65536,t=3,p=4$` |
| 2 | `SELECT count(*) FROM users WHERE email = 'New.Clinician@Example.TEST';` | 0 (only the lower-case form is stored, PGS-034) |
| 3 | `SELECT details::text FROM audit_logs WHERE entity_id = '<new id>';` | No row contains the string `argon2`, `password` or NEW_PW |

### TC-037-03 Password policy violations return 422 and create no user

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/users` as admin with body `{"email": "staff@example.test", "display_name": "Staff", "role": "researcher", "password": "short"}` | HTTP 422; `Content-Type: application/problem+json`; `type` = `urn:echowell:error:PASSWORD_POLICY_VIOLATION`; `title` = "Password does not meet policy"; `status` = 422 |
| 2 | Repeat with `"password": "password1234"` (12 characters, on the common-password list) | HTTP 422 `urn:echowell:error:PASSWORD_POLICY_VIOLATION` |
| 3 | Repeat with a password of 129 `x` characters | HTTP 422 `urn:echowell:error:PASSWORD_POLICY_VIOLATION` |
| 4 | Repeat with `"password": "staff@example.test"` (equal to the e-mail) | HTTP 422 `urn:echowell:error:PASSWORD_POLICY_VIOLATION` |
| 5 | `SELECT count(*) FROM users WHERE email = 'staff@example.test';` | 0 |
| 6 | `SELECT count(*) FROM audit_logs WHERE action = 'user.created' AND details->>'role' = 'researcher' AND occurred_at > now() - interval '10 minutes';` | 0 (no audit row for a refused create) |
| 7 | Repeat step 1 with a 12-character password made of lower-case letters only that is not on the list | HTTP 201 (no composition rule is imposed, SEC-012) |

### TC-037-04 Duplicate e-mail in a different case returns 409

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/users` as admin with body `{"email": "Clinician@Example.com", "display_name": "Twin", "role": "clinician", "password": "<NEW_PW>"}` (seeded `clinician@example.com` exists) | HTTP 409; `type` = `urn:echowell:error:EMAIL_ALREADY_EXISTS`; `title` = "Email already in use" |
| 2 | `SELECT count(*) FROM users WHERE lower(email) = 'clinician@example.com';` | 1 |

### TC-037-05 Admin lists users with filters and pagination

| Step | Action | Expected Result |
|---|---|---|
| 1 | On a freshly seeded database `GET /api/v1/users` with ADMIN_TOKEN | HTTP 200; body has `meta` (7 fields), `items`, `total` = 3, `limit` = 50, `offset` = 0 |
| 2 | Inspect each item | Each item has exactly `id`, `email`, `display_name`, `role`, `active`, `last_login_at`, `created_at`; roles are `admin`, `clinician`, `researcher` |
| 3 | Search the response text for `password_hash` | Not present |
| 4 | `GET /api/v1/users?role=researcher` | HTTP 200; `items` holds only rows with `role` = `researcher` (1 row) |
| 5 | `GET /api/v1/users?active=false` | HTTP 200; `total` = 0 |
| 6 | `GET /api/v1/users?limit=1&offset=1` | HTTP 200; `items` length 1; `limit` = 1; `offset` = 1; `total` = 3 |
| 7 | `GET /api/v1/users?role=nurse` | HTTP 422 problem+json (unknown role value) |
| 8 | `GET /api/v1/users?limit=0` | HTTP 422 `urn:echowell:error:INVALID_QUERY_PARAMETER` |

### TC-037-06 Admin PATCHes another user's role and active flag

| Step | Action | Expected Result |
|---|---|---|
| 1 | Find the clinician id: `SELECT id FROM users WHERE email = 'clinician@example.com';` | One uuid |
| 2 | `PATCH /api/v1/users/<clinician id>` with ADMIN_TOKEN, body `{"role": "researcher", "active": false}` | HTTP 200; body `User` with `role` = "researcher", `active` = false, `display_name` unchanged |
| 3 | `SELECT role, active FROM users WHERE id = '<clinician id>';` | `researcher`, false |
| 4 | `SELECT details FROM audit_logs WHERE action = 'user.updated' ORDER BY id DESC LIMIT 1;` | `{"changed": ["active", "role"]}`; no password value or hash |

### TC-037-07 Role or active change takes effect on the user's next request

| Step | Action | Expected Result |
|---|---|---|
| 1 | Log in as `clinician@example.com` and keep CLINICIAN_TOKEN; `GET /api/v1/auth/me` | HTTP 200, `role` = "clinician" |
| 2 | As admin, `PATCH /api/v1/users/<clinician id>` with `{"active": false}` | HTTP 200 |
| 3 | Repeat `GET /api/v1/auth/me` with the old CLINICIAN_TOKEN (no new login) | HTTP 401 problem+json (`urn:echowell:error:TOKEN_INVALID`) |
| 4 | As admin, reactivate with `{"active": true, "role": "researcher"}`; log in again as the clinician account | Login 200; `user.role` = "researcher" |
| 5 | With the new token call `POST /api/v1/alerts/<any alert id>/snooze` body `{}` | HTTP 403 `urn:echowell:error:FORBIDDEN` (researcher cannot snooze) |
| 6 | Restore: PATCH `{"role": "clinician"}` | HTTP 200 |

### TC-037-08 PATCH display name and password; audit lists both names, never the password

| Step | Action | Expected Result |
|---|---|---|
| 1 | `PATCH /api/v1/users/<researcher id>` as admin with `{"display_name": "Renamed", "password": "<NEW_PW>"}` | HTTP 200; `display_name` = "Renamed" |
| 2 | `SELECT details FROM audit_logs WHERE action = 'user.updated' ORDER BY id DESC LIMIT 1;` | `{"changed": ["display_name", "password"]}` |
| 3 | `SELECT count(*) FROM audit_logs WHERE details::text LIKE '%argon2%';` | 0 |
| 4 | `POST /api/v1/auth/login` with the researcher e-mail and NEW_PW | HTTP 200 |
| 5 | `PATCH` the same user with `{"password": "short"}` | HTTP 422 `urn:echowell:error:PASSWORD_POLICY_VIOLATION`; stored hash unchanged (compare `password_hash` before/after with `SELECT md5(password_hash)`) |

### TC-037-09 Admin cannot change their own role or deactivate themselves

| Step | Action | Expected Result |
|---|---|---|
| 1 | Get the admin's own id: `GET /api/v1/auth/me` with ADMIN_TOKEN | HTTP 200; note `id` |
| 2 | `PATCH /api/v1/users/<own id>` with `{"role": "researcher"}` | HTTP 403; `type` = `urn:echowell:error:FORBIDDEN`; `title` = "Not allowed for this role" |
| 3 | `PATCH /api/v1/users/<own id>` with `{"active": false}` | HTTP 403 `urn:echowell:error:FORBIDDEN` |
| 4 | `SELECT role, active FROM users WHERE id = '<own id>';` | `admin`, true |
| 5 | `SELECT count(*) FROM audit_logs WHERE action = 'user.updated' AND entity_id = '<own id>';` | Unchanged from before step 2 |

### TC-037-10 Admin may change their own display name

| Step | Action | Expected Result |
|---|---|---|
| 1 | `PATCH /api/v1/users/<own id>` with `{"display_name": "Me", "role": "admin"}` (role unchanged) | HTTP 200; `display_name` = "Me"; `role` = "admin" |
| 2 | Latest `user.updated` audit row for `<own id>` | `details` has the single key `changed`, whose list contains `display_name`; no password value |
| 3 | `PATCH /api/v1/users/<own id>` with `{"password": "<NEW_PW>"}` | HTTP 200 (SEC-044 restricts only role and deactivation) |

### TC-037-11 Unknown id, empty PATCH, unknown role, extra property and malformed body are rejected

| Step | Action | Expected Result |
|---|---|---|
| 1 | `PATCH /api/v1/users/00000000-0000-4000-8000-000000000000` as admin with `{"display_name": "x"}` | HTTP 404 `urn:echowell:error:USER_NOT_FOUND`; `title` = "User not found" |
| 2 | `PATCH /api/v1/users/<clinician id>` with `{}` | HTTP 422 `urn:echowell:error:VALIDATION_ERROR` |
| 3 | `POST /api/v1/users` with role `"nurse"` | HTTP 422 `urn:echowell:error:VALIDATION_ERROR`; `errors[]` names field `role` |
| 4 | `POST /api/v1/users` with a valid body plus `"is_superuser": true` | HTTP 422 `urn:echowell:error:VALIDATION_ERROR` (extra properties forbidden) |
| 5 | `POST /api/v1/users` with `display_name` of 101 characters | HTTP 422 `urn:echowell:error:VALIDATION_ERROR` |
| 6 | `POST /api/v1/users` with body `{"email": ` (invalid JSON) | HTTP 422 `urn:echowell:error:VALIDATION_ERROR` |
| 7 | `PATCH /api/v1/users/not-a-uuid` with `{"display_name": "x"}` | HTTP 422 problem+json |
| 8 | `SELECT count(*) FROM users;` | Unchanged by steps 1–7 |

### TC-037-12 Last-admin guard raises LAST_ADMIN and writes nothing

| Step | Action | Expected Result |
|---|---|---|
| 1 | In the local development stack run `pytest -m unit tests/unit/backend/services/test_user_service.py -v` | `test_last_active_admin_cannot_be_removed` (all parametrisations) PASSED; 0 failed |
| 2 | Read the test output / source | With the target as the only active admin, a change of `active` to false and a change of `role` to a non-admin value each raise `LastAdminError` (code `LAST_ADMIN`, HTTP 409, title "Cannot remove the last admin") and the repository double records no update |
| 3 | Through HTTP, as the only admin, try `PATCH /api/v1/users/<own id>` `{"active": false}` | HTTP 403 `FORBIDDEN` (SEC-044 is checked first; `LAST_ADMIN` is not reachable through the API, TRD 05 API-092) |

### TC-037-13 No DELETE route

| Step | Action | Expected Result |
|---|---|---|
| 1 | `DELETE /api/v1/users/<clinician id>` with ADMIN_TOKEN | HTTP 405 or 404 (problem+json) |
| 2 | `SELECT count(*) FROM users WHERE id = '<clinician id>';` | 1 |
| 3 | Open `http://localhost:8000/api/v1/openapi.json` and look at path `/users/{id}` | Only `patch` is defined; no `delete` operation |

### TC-037-14 Role and credential checks on all three endpoints

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/users`, `POST /api/v1/users` (valid body), `PATCH /api/v1/users/<researcher id>` (`{"display_name": "x"}`) with CLINICIAN_TOKEN | Each HTTP 403 `urn:echowell:error:FORBIDDEN` |
| 2 | The same three calls with RESEARCHER_TOKEN | Each HTTP 403 `urn:echowell:error:FORBIDDEN` |
| 3 | The same three calls with header `X-API-Key: INGEST_KEY` and no Bearer token | Each HTTP 401 `urn:echowell:error:NOT_AUTHENTICATED` |
| 4 | The same three calls with no credentials | Each HTTP 401 `urn:echowell:error:NOT_AUTHENTICATED` |
| 5 | `SELECT action, count(*) FROM audit_logs WHERE action = 'access.denied' AND occurred_at > now() - interval '10 minutes' GROUP BY action;` | count ≥ 6 (one `access.denied` row per 403 call of steps 1–2, FEAT-021) |
| 6 | `SELECT count(*) FROM users;` | Unchanged |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/users` (admin) | 200 `UserList`: `meta`, `items[]` of `User`, `total`, `limit`, `offset`; validates against `docs/api_reference/openapi.json` `UserList` |
| 2 | `POST /api/v1/users` (admin, valid `UserCreate`) | 201 `User` (7 required properties, no `meta`, no `password_hash`) |
| 3 | `PATCH /api/v1/users/{id}` (admin, valid `UserUpdate`) | 200 `User` |
| 4 | Error responses of the three endpoints | `application/problem+json` with `type` `urn:echowell:error:<CODE>`, `title`, `status`, `detail`, `request_id`, `errors`; codes 401 `NOT_AUTHENTICATED`, 403 `FORBIDDEN`, 404 `USER_NOT_FOUND`, 409 `EMAIL_ALREADY_EXISTS`, 409 `LAST_ADMIN` (service level), 422 `PASSWORD_POLICY_VIOLATION`, 422 `VALIDATION_ERROR` |
| 5 | Every response | Header `X-Request-ID` present |
| 6 | `DELETE /api/v1/users/{id}` | 405 or 404 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT email FROM users WHERE email <> lower(email);` | 0 rows |
| 2 | `SELECT count(*) FROM users WHERE password_hash NOT LIKE '$argon2id$%';` | 0 |
| 3 | `SELECT details FROM audit_logs WHERE action IN ('user.created','user.updated') ORDER BY id;` | `user.created` rows carry only `{"role": ...}`; `user.updated` rows carry only `{"changed": [...]}` with names from `display_name`, `role`, `active`, `password` |
| 4 | `SELECT count(*) FROM audit_logs WHERE details::text ~* 'argon2\|password_hash';` | 0 |
| 5 | Row count of `users` after every refused request (403, 404, 409, 422) | Unchanged; no user is ever deleted |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create with password "short" / "password1234" / 129 characters / equal to e-mail | 422 `PASSWORD_POLICY_VIOLATION`, no row (TC-037-03) |
| 2 | Create `Clinician@Example.com` while `clinician@example.com` exists | 409 `EMAIL_ALREADY_EXISTS` (TC-037-04) |
| 3 | PATCH unknown id | 404 `USER_NOT_FOUND` (TC-037-11) |
| 4 | Empty PATCH, unknown role, extra property, malformed JSON | 422 `VALIDATION_ERROR` (TC-037-11) |
| 5 | Admin changes own role / deactivates self | 403 `FORBIDDEN` (TC-037-09) |
| 6 | Change that would leave no active admin | 409 `LAST_ADMIN`, no write (TC-037-12, service level) |
| 7 | Clinician / researcher / API key / anonymous callers | 403 / 403 / 401 / 401 (TC-037-14) |
| 8 | `DELETE /users/{id}` | 405 or 404 (TC-037-13) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-037-AC-01 | Admin create with a valid 14-character password returns 201, stores the lower-cased e-mail and a hash starting `$argon2id$v=19$m=65536,t=3,p=4$`, writes one `user.created` audit row with `{"role": ...}` | TC-037-01, TC-037-02 |
| FEAT-037-AC-02 | "short" and "password1234" each return 422 `PASSWORD_POLICY_VIOLATION` and create no user | TC-037-03 |
| FEAT-037-AC-03 | `Clinician@Example.com` with `clinician@example.com` existing returns 409 `EMAIL_ALREADY_EXISTS` | TC-037-04 |
| FEAT-037-AC-04 | PATCH `{"role": "researcher", "active": false}` on another user returns 200 and audit `changed` contains `role` and `active`, no password value | TC-037-06 |
| FEAT-037-AC-05 | Admin PATCH of own `role` or own `active: false` returns 403 `FORBIDDEN` | TC-037-09 |
| FEAT-037-AC-06 | Unit test: only active admin losing admin role or active flag raises `LAST_ADMIN` (409), no write | TC-037-12 |
| FEAT-037-AC-07 | `DELETE /api/v1/users/{id}` returns 405 or 404; no response of the three endpoints contains `password_hash` | TC-037-13, TC-037-01, TC-037-05 |
| FEAT-037-AC-08 | Clinician and researcher JWTs get 403 on all three endpoints; an API key gets 401 | TC-037-14 |

## Test Data Requirements

- Freshly seeded `test_v0_1` database (3 seeded users, no others).
- Synthetic new accounts only, with e-mails under `example.test` (e.g. `new.clinician@example.test`, `staff@example.test`).
- Environment variables: `SEED_ADMIN_PASSWORD`, `SEED_CLINICIAN_PASSWORD`, `SEED_RESEARCHER_PASSWORD`, `SEED_INGEST_API_KEY` (values never recorded).
- `backend/core/common_passwords.txt` (contains "password1234").
- At least one alert id from DS-07 for TC-037-07 step 5 (`GET /api/v1/alerts?status=open`).

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-037-FR-01 | FEAT-037 | TC-037-14 |
| FEAT-037-FR-02 | FEAT-037 | TC-037-05 |
| FEAT-037-FR-03 | FEAT-037 | TC-037-01, TC-037-02, TC-037-04 |
| FEAT-037-FR-04 | FEAT-037 | TC-037-03, TC-037-08 |
| FEAT-037-FR-05 | FEAT-037 | TC-037-06, TC-037-08, TC-037-11, TC-037-13 |
| FEAT-037-FR-06 | FEAT-037 | TC-037-09, TC-037-10 |
| FEAT-037-FR-07 | FEAT-037 | TC-037-12 |
| FEAT-037-FR-08 | FEAT-037 | TC-037-01, TC-037-06, TC-037-08 |
| FEAT-037-FR-09 | FEAT-037 | TC-037-07 |
| TRD 05 API-091 | FEAT-037 | TC-037-01, TC-037-04, TC-037-05, TC-037-06 |
| TRD 05 API-092 | FEAT-037 | TC-037-06, TC-037-12 |
| TRD 19 E-25, E-26, E-27 | FEAT-037 | TC-037-05, TC-037-01, TC-037-06 |
| TRD 12 SEC-010 | FEAT-037 | TC-037-02 |
| TRD 12 SEC-012 | FEAT-037 | TC-037-03 |
| TRD 12 SEC-044 | FEAT-037 | TC-037-09, TC-037-10 |
| TRD 12 SEC-104 | FEAT-037 | TC-037-08 |
| TRD 12 AC-SEC-05 | FEAT-037 | TC-037-02, TC-037-03 |
| TRD 20 PGS-034 | FEAT-037 | TC-037-02, TC-037-04 |
| TRD 23 DME-005 | FEAT-037 | TC-037-05, TC-037-13 |
| TRD 13 TST-053 | FEAT-037 | TC-037-06, TC-037-08 |
| TRD 13 Table 4.13-A (users row) | FEAT-037 | TC-037-14 |
| FR-220, FR-221 | FEAT-037 | TC-037-01, TC-037-13 |
