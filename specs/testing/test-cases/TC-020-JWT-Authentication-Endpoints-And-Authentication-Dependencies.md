# JWT authentication endpoints and authentication dependencies

## Feature Description

FEAT-020 authenticates every API caller. Dashboard users call `POST /api/v1/auth/login` (E-02) with `{email, password}` and receive 200 `Token` (`access_token` HS256 JWT, `token_type` "bearer", `expires_in` = `JWT_EXPIRES_MINUTES` × 60 = 3600, `user`); claims `sub`, `role`, `iat`, `exp`, `jti`, `iss` "echowell-api", `aud` "echowell-dashboard"; no refresh token. Unknown e-mail, wrong password and inactive user return the same 401 `INVALID_CREDENTIALS`; 10 failed logins for one e-mail within 15 minutes lock it (429 `ACCOUNT_TEMPORARILY_LOCKED` with `Retry-After`). `POST /api/v1/auth/logout` (E-03) returns 204 and writes `auth.logout` without revoking the token; `GET /api/v1/auth/me` (E-04) returns the `User`. The dependencies read role and `active` from `users` on every request (401 `NOT_AUTHENTICATED`, `TOKEN_EXPIRED`, `TOKEN_INVALID`, each with `WWW-Authenticate: Bearer`) and authenticate devices by the SHA-256 of `X-API-Key` (401 `API_KEY_INVALID`, 403 `FORBIDDEN` without the scope; `last_used_at` at most once per minute).

## Preconditions

- Local development stack running; `.env` from `.env.development.example` (`APP_ENV=local`, `JWT_EXPIRES_MINUTES=60`, `RATE_LIMIT_LOGIN=5/minute`, `PIPELINE_PROFILE=test_v0_1`, `SEED_*` and `JWT_SECRET` set; values never written down).
- Database seeded: `python -m backend.cli seed test_v0_1 --reset` (exit code 0).
- Synthetic extra accounts created with the CLI (passwords chosen locally and piped on stdin): `qa.inactive@example.com` (role `clinician`) and `qa.rehash@example.com` (role `researcher`); extra key `python -m backend.cli create-api-key --name qa-pipeline-only --scope pipeline:run` (plaintext kept only in the tester's shell variable).
- Login is limited to 5 requests per minute per client IP (FEAT-022). Send each login of a multi-attempt case with a distinct `X-Forwarded-For: 203.0.113.<n>` header (documentation range), or wait 60 s after every fifth attempt.
- `curl -i` against `http://localhost:8000/api/v1`; `psql` for read-only checks; Python 3.12 environment with PyJWT for token decoding.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-020-01 | Valid login returns a 60-minute HS256 token with the SEC-031 claims | High | API |
| TC-020-02 | Login updates `last_login_at` and writes `auth.login.succeeded`; e-mail is normalised | High | Database |
| TC-020-03 | Unknown e-mail, wrong password and inactive user give identical 401 bodies and one `auth.login.failed` each | High | Security |
| TC-020-04 | Eleventh attempt after 10 failures within 15 minutes is locked | High | Security |
| TC-020-05 | Expired, altered-signature, `alg: none` and missing tokens are refused with `WWW-Authenticate: Bearer` | High | Negative |
| TC-020-06 | Wrong `iss` or `aud` is refused | Medium | Negative |
| TC-020-07 | Deactivating a user invalidates the still-valid token immediately | High | Security |
| TC-020-08 | `GET /auth/me` returns the user; logout returns 204, writes `auth.logout`, does not revoke | High | API |
| TC-020-09 | API keys: revoked → 401, missing scope → 403, key in query string → 401 | High | Security |
| TC-020-10 | Wrong credential type: key on a user endpoint and token on `POST /sessions` → 401 | Medium | Negative |
| TC-020-11 | `last_used_at` is updated at most once per minute | Medium | Database |
| TC-020-12 | Stored hash with old parameters is rehashed on login | Medium | Database |
| TC-020-13 | Role is read from the database on every request | Medium | Security |
| TC-020-14 | Every endpoint except health and login requires credentials | High | Security |
| TC-020-15 | Logs of a login and an authorised request contain no password, JWT or e-mail | High | Security |
| TC-020-16 | Rotating `JWT_SECRET` invalidates issued tokens | Medium | Security |
| TC-020-17 | Login body validation | Medium | Negative |

### TC-020-01 Valid login returns a 60-minute HS256 token with the SEC-031 claims

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/auth/login` with `{"email": "clinician@example.com", "password": "$SEED_CLINICIAN_PASSWORD"}` | 200; body keys `access_token`, `token_type`, `expires_in`, `user`; `token_type` `"bearer"`; `expires_in` 3600 |
| 2 | Inspect `user` | `email` `clinician@example.com`, `role` `clinician`, `active` `true`, `display_name` non-empty, `id` UUID, `last_login_at` set, `created_at` set; no `password_hash` field |
| 3 | Decode the token header without verification: `jwt.get_unverified_header(tok)` | `{"alg": "HS256", "typ": "JWT"}` |
| 4 | Decode the claims without verification: `jwt.decode(tok, options={"verify_signature": False})` | Keys exactly `sub`, `role`, `iat`, `exp`, `jti`, `iss`, `aud`; `sub` = `user.id`; `role` `clinician`; `iss` `echowell-api`; `aud` `echowell-dashboard`; `exp − iat` = 3600; `jti` a UUID4 |
| 5 | Log in again | Different `jti` |
| 6 | Run `pytest tests/unit/backend/core/test_security.py -q` and `pytest -m integration tests/integration/api/test_auth.py -q -k valid_login_returns_a_bearer_token` | All pass (TST-032) |

### TC-020-02 Login updates `last_login_at` and writes `auth.login.succeeded`; e-mail is normalised

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/auth/login` with `{"email": "  Admin@Example.COM ", "password": "$SEED_ADMIN_PASSWORD"}` and `X-Request-ID: qa-auth-ok-01` | 200; `user.email` `admin@example.com` |
| 2 | `SELECT last_login_at FROM users WHERE email = 'admin@example.com';` | Within a few seconds of the request (UTC) |
| 3 | `SELECT actor_type, actor_id, entity_type, details FROM audit_logs WHERE request_id = 'qa-auth-ok-01';` | Exactly 1 row: `auth.login.succeeded`, `actor_type` `user`, `actor_id` = admin id, `entity_type` `user`, `details` `{}` |

### TC-020-03 Unknown e-mail, wrong password and inactive user give identical 401 bodies and one `auth.login.failed` each

| Step | Action | Expected Result |
|---|---|---|
| 1 | As admin, deactivate the synthetic user: `PATCH /api/v1/users/<qa.inactive id>` with `{"active": false}` | 200; `active` `false` |
| 2 | Record `SELECT count(*) FROM audit_logs WHERE action = 'auth.login.failed';` | Baseline F |
| 3 | Login with `{"email": "nobody@example.com", "password": "qa-probe-value-1"}` | 401 |
| 4 | Login with `clinician@example.com` and a wrong value `qa-probe-value-1` | 401 |
| 5 | Login with `qa.inactive@example.com` and its correct password | 401 |
| 6 | Compare the three bodies after removing `request_id` | Byte-identical: `{"type": "urn:echowell:error:INVALID_CREDENTIALS", "title": "Invalid email or password", "status": 401, "detail": "The e-mail address or password is not correct.", "errors": []}` |
| 7 | Compare response times of steps 3–5 | Same order of magnitude (each includes one argon2id verification; no instant reply for the unknown e-mail) |
| 8 | Re-count; read the three newest rows | F + 3; each `actor_type` `system`, `actor_id` NULL, `details.reason` `invalid_credentials`, `details.email` lower-cased (`nobody@example.com`, `clinician@example.com`, `qa.inactive@example.com`); no password value |

### TC-020-04 Eleventh attempt after 10 failures within 15 minutes is locked

| Step | Action | Expected Result |
|---|---|---|
| 1 | Send 10 logins for `researcher@example.com` with a wrong value, each with a different `X-Forwarded-For: 203.0.113.<1..10>`, within 5 minutes | Each 401 `INVALID_CREDENTIALS` |
| 2 | Send the 11th attempt with the correct `SEED_RESEARCHER_PASSWORD` and `X-Forwarded-For: 203.0.113.11` | 429; `type` `urn:echowell:error:ACCOUNT_TEMPORARILY_LOCKED`, `title` `Too many failed logins`, `detail` `Too many failed logins for this account. Try again later.`; numeric `Retry-After` ≤ 900 |
| 3 | `SELECT details FROM audit_logs WHERE action = 'auth.login.failed' ORDER BY id DESC LIMIT 1;` | `{"email": "researcher@example.com", "reason": "locked"}` |
| 4 | Log in as `clinician@example.com` with its correct password | 200 (lockout is per e-mail) |
| 5 | Wait until 15 minutes after the 10th failure and log in as the researcher with the correct password | 200 |
| 6 | Run `pytest -m integration tests/integration/api/test_auth.py -q -k "eleventh_attempt or older_than_fifteen_minutes"` | Both pass |

### TC-020-05 Expired, altered-signature, `alg: none` and missing tokens are refused with `WWW-Authenticate: Bearer`

| Step | Action | Expected Result |
|---|---|---|
| 1 | In a REPL with the environment loaded: `from backend.core.security import create_access_token; from datetime import datetime, timedelta, UTC; t = create_access_token(<clinician uuid>, "clinician", os.environ["JWT_SECRET"], 60, now=datetime.now(UTC) - timedelta(minutes=121))` (expired 61 minutes ago) | Token string |
| 2 | `GET /api/v1/auth/me` with `Authorization: Bearer <t>` | 401; `type` `urn:echowell:error:TOKEN_EXPIRED`; header `WWW-Authenticate: Bearer` |
| 3 | Take a valid token and change the last character of its signature; call `GET /api/v1/auth/me` | 401 `TOKEN_INVALID`; `WWW-Authenticate: Bearer` |
| 4 | Build an unsigned token `jwt.encode(<valid claims>, key=None, algorithm="none")`; call `GET /api/v1/auth/me` | 401 `TOKEN_INVALID`; `WWW-Authenticate: Bearer` |
| 5 | Call `GET /api/v1/auth/me` without `Authorization` | 401 `NOT_AUTHENTICATED`; `WWW-Authenticate: Bearer` |
| 6 | Call with `Authorization: Bearer not-a-jwt` | 401 `TOKEN_INVALID` |
| 7 | `SELECT count(*) FROM audit_logs WHERE action = 'access.denied';` before and after steps 2–6 | Unchanged (401s are not audited) |
| 8 | Run `pytest -m security tests/security/test_tokens.py -q` | All pass (TST-132) |

### TC-020-06 Wrong `iss` or `aud` is refused

| Step | Action | Expected Result |
|---|---|---|
| 1 | In the REPL sign valid claims with `JWT_SECRET` but `iss` = `other-issuer` | `GET /api/v1/auth/me` → 401 `TOKEN_INVALID` |
| 2 | Same with `aud` = `other-audience` | 401 `TOKEN_INVALID` |
| 3 | Same with `sub` = a random UUID of no user | 401 `TOKEN_INVALID` |

### TC-020-07 Deactivating a user invalidates the still-valid token immediately

| Step | Action | Expected Result |
|---|---|---|
| 1 | Reactivate `qa.inactive@example.com` (`PATCH … {"active": true}`), log in as it, call `GET /api/v1/auth/me` | 200 |
| 2 | As admin, `PATCH /api/v1/users/<id>` with `{"active": false}` | 200 |
| 3 | Call `GET /api/v1/auth/me` with the token from step 1 (still within 60 minutes) | 401 `TOKEN_INVALID` with `WWW-Authenticate: Bearer` |
| 4 | Run `pytest -m integration tests/integration/api/test_auth.py -q -k deactivated_user_token_stops_working` | Passes |

### TC-020-08 `GET /auth/me` returns the user; logout returns 204, writes `auth.logout`, does not revoke

| Step | Action | Expected Result |
|---|---|---|
| 1 | Log in as the researcher; `GET /api/v1/auth/me` | 200 `User` with `email` `researcher@example.com`, `display_name`, `role` `researcher`, `active` `true` |
| 2 | `POST /api/v1/auth/logout` with the token and `X-Request-ID: qa-auth-logout-01` | 204 with empty body |
| 3 | `SELECT action, actor_type FROM audit_logs WHERE request_id = 'qa-auth-logout-01';` | Exactly 1 row `auth.logout`, `actor_type` `user` |
| 4 | Call `GET /api/v1/auth/me` again with the same token | 200 (no server-side revocation, SEC-036) |
| 5 | `POST /api/v1/auth/logout` without a token | 401 `NOT_AUTHENTICATED`; no `auth.logout` row |

### TC-020-09 API keys: revoked → 401, missing scope → 403, key in query string → 401

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create and revoke a key: `create-api-key --name qa-revoked` then `revoke-api-key --name qa-revoked`; `POST /api/v1/sessions` with that key and a JSON body | 401; `type` `urn:echowell:error:API_KEY_INVALID`, `detail` `The API key is missing, unknown or revoked.` |
| 2 | `POST /api/v1/sessions` with `X-API-Key: <qa-pipeline-only key>` (scope `pipeline:run` only) | 403 `FORBIDDEN`, `detail` `This API key does not have the scope ingest:write.`; one `access.denied` row with `actor_type` `api_key` |
| 3 | `POST /api/v1/sessions?X-API-Key=$SEED_INGEST_API_KEY` without the header | 401 (`NOT_AUTHENTICATED` "A valid API key is required for this endpoint."); query value ignored |
| 4 | `POST /api/v1/sessions` with `X-API-Key: ewk_unknownunknownunknownunknownunknownunknow` | 401 `API_KEY_INVALID` |
| 5 | Run `pytest -m security tests/security/test_api_keys.py -q` | All pass |

### TC-020-10 Wrong credential type: key on a user endpoint and token on `POST /sessions` → 401

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents` with only `X-API-Key: $SEED_INGEST_API_KEY` | 401 `NOT_AUTHENTICATED` with `WWW-Authenticate: Bearer` |
| 2 | `POST /api/v1/sessions` with an admin bearer token and no key | 401 `NOT_AUTHENTICATED` |
| 3 | `POST /api/v1/ingest` with an admin bearer token and a JSON batch | Not 401/403 (admin JWT accepted by `get_ingest_principal`) |
| 4 | `POST /api/v1/pipeline/run` with `X-API-Key: $SEED_INGEST_API_KEY` (has `pipeline:run`) and `{"scope": "all"}` | 202 |

### TC-020-11 `last_used_at` is updated at most once per minute

| Step | Action | Expected Result |
|---|---|---|
| 1 | Note `SELECT last_used_at FROM api_keys WHERE name = 't2'` for a key created with `--scope ingest:write --device D01` (or use `test-ingest`) | Value L0 (may be NULL) |
| 2 | Make an authenticated key request (e.g. `POST /api/v1/sessions` with a synthetic record) | `last_used_at` = L1 ≈ now |
| 3 | Within 30 s make 3 more key requests | `last_used_at` still L1 |
| 4 | After 61 s make one more request | `last_used_at` > L1 |

### TC-020-12 Stored hash with old parameters is rehashed on login

| Step | Action | Expected Result |
|---|---|---|
| 1 | In the REPL compute `old = PasswordHasher(time_cost=2, memory_cost=32768, parallelism=2).hash(<qa.rehash password>)`; as the migrator (write step, local only) run `UPDATE users SET password_hash = :old WHERE email = 'qa.rehash@example.com';` | 1 row updated |
| 2 | Log in as `qa.rehash@example.com` with its password | 200 |
| 3 | `SELECT left(password_hash, 31) FROM users WHERE email = 'qa.rehash@example.com';` | `$argon2id$v=19$m=65536,t=3,p=4$` (rehashed with SEC-010 parameters) |

### TC-020-13 Role is read from the database on every request

| Step | Action | Expected Result |
|---|---|---|
| 1 | Log in as `qa.rehash@example.com` (role `researcher`); `GET /api/v1/users` | 403 `FORBIDDEN` |
| 2 | As admin, `PATCH /api/v1/users/<qa.rehash id>` with `{"role": "admin"}` | 200 |
| 3 | Repeat step 1's call with the old token (its `role` claim still says `researcher`) | 200 (database role used) |
| 4 | Set the role back to `researcher` and repeat | 403 |

### TC-020-14 Every endpoint except health and login requires credentials

| Step | Action | Expected Result |
|---|---|---|
| 1 | Without credentials call `GET /api/v1/health` and `POST /api/v1/auth/login` (empty JSON object) | 200 (or 503 health) and 422 — neither 401 |
| 2 | Without credentials call `GET /api/v1/residents`, `GET /api/v1/residents/R01`, `GET /api/v1/devices`, `GET /api/v1/alerts`, `GET /api/v1/config/ui`, `GET /api/v1/auth/me`, `GET /api/v1/pipeline/runs`, `GET /api/v1/users` | Each 401 |
| 3 | Run `pytest -m integration tests/integration/test_auth_coverage.py -q` | Passes (SEC-042 route enumeration) |

### TC-020-15 Logs of a login and an authorised request contain no password, JWT or e-mail

| Step | Action | Expected Result |
|---|---|---|
| 1 | Capture `docker compose logs -f --no-log-prefix backend > auth.log`; log in as admin; call `GET /api/v1/residents` with the token | 200, 200 |
| 2 | `grep -cF "$SEED_ADMIN_PASSWORD" auth.log`; `grep -cF "<token>" auth.log`; `grep -c "admin@example.com" auth.log`; `grep -c "eyJ" auth.log` | 0, 0, 0, 0 |
| 3 | Run `pytest -m integration tests/integration/api/test_auth.py -q -k logs_hold_no_password_token_or_email` | Passes (AC-LOG-02 sample password) |
| 4 | Delete `auth.log` | Removed |

### TC-020-16 Rotating `JWT_SECRET` invalidates issued tokens

| Step | Action | Expected Result |
|---|---|---|
| 1 | Log in as the clinician; `GET /api/v1/auth/me` | 200 |
| 2 | Replace `JWT_SECRET` in `.env` with a newly generated local value (`python -c "import secrets; print(secrets.token_urlsafe(48))"`), restart the backend | Backend healthy |
| 3 | Repeat `GET /api/v1/auth/me` with the old token | 401 `TOKEN_INVALID` |
| 4 | Log in again | 200 with a token that works |

### TC-020-17 Login body validation

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/auth/login` with `{"email": "admin@example.com"}` | 422 `VALIDATION_ERROR`; `errors[]` item `field` `password`, `code` `missing` |
| 2 | Body with `"password": ""` | 422 `VALIDATION_ERROR` (min length 1) |
| 3 | Body with an extra property `"otp": "1"` | 422 with `code` `extra_forbidden` |
| 4 | `SELECT count(*) FROM audit_logs WHERE action = 'auth.login.failed';` before/after | Unchanged (validation failures are not failed logins) |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/auth/login` valid | 200 `Token` (`access_token`, `token_type` "bearer", `expires_in` 3600, `user`) |
| 2 | `POST /api/v1/auth/login` invalid | 401 `INVALID_CREDENTIALS`; 422 for a malformed body; 429 `ACCOUNT_TEMPORARILY_LOCKED` after 10 failures; 429 `RATE_LIMITED` above 5/minute (FEAT-022) |
| 3 | `POST /api/v1/auth/logout` | 204 (bearer A/C/Rs); 401 without token |
| 4 | `GET /api/v1/auth/me` | 200 `User` for admin, clinician, researcher |
| 5 | `GET /api/v1/openapi.json` | E-02, E-03, E-04 present; security schemes `bearerAuth` and `apiKeyAuth` defined |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT last_login_at FROM users WHERE email = 'admin@example.com';` after login | Updated to the login time |
| 2 | `SELECT action, count(*) FROM audit_logs WHERE action LIKE 'auth.%' GROUP BY 1;` | Rows for `auth.login.succeeded`, `auth.login.failed`, `auth.logout` matching the calls made |
| 3 | `SELECT count(*) FROM audit_logs WHERE action = 'auth.login.failed' AND (details->>'email') <> lower(details->>'email');` | 0 |
| 4 | `SELECT last_used_at FROM api_keys WHERE name = 'test-ingest';` | Set after key use; changes at most once per minute |
| 5 | `SELECT left(password_hash, 31) FROM users WHERE email = 'qa.rehash@example.com';` after TC-020-12 | `$argon2id$v=19$m=65536,t=3,p=4$` |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | No credentials | 401 `NOT_AUTHENTICATED` + `WWW-Authenticate: Bearer` |
| 2 | Expired JWT (61 min) | 401 `TOKEN_EXPIRED` |
| 3 | Bad signature, `alg: none`, wrong `iss`/`aud`, missing or inactive user | 401 `TOKEN_INVALID` |
| 4 | Wrong password / unknown e-mail / inactive user at login | 401 `INVALID_CREDENTIALS`, identical body |
| 5 | 10 failures in 15 minutes for one e-mail | 429 `ACCOUNT_TEMPORARILY_LOCKED` with `Retry-After` |
| 6 | Missing, unknown or revoked API key | 401 `API_KEY_INVALID` (missing header on a key endpoint: 401 `NOT_AUTHENTICATED`) |
| 7 | API key without the required scope | 403 `FORBIDDEN` |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-020-AC-01 | 200, `token_type` "bearer", `expires_in` 3600, header `alg` HS256, claims `sub`, `role`, `iat`, `exp`, `jti`, `iss` "echowell-api", `aud` "echowell-dashboard"; one `auth.login.succeeded` row | TC-020-01, TC-020-02 |
| FEAT-020-AC-02 | Unknown e-mail, wrong password, inactive user: 401 `INVALID_CREDENTIALS`, byte-identical bodies apart from `request_id`; one `auth.login.failed` each | TC-020-03 |
| FEAT-020-AC-03 | 11th attempt within 15 minutes after 10 failures: 429 `ACCOUNT_TEMPORARILY_LOCKED` | TC-020-04 |
| FEAT-020-AC-04 | Token expired by 61 minutes: 401 `TOKEN_EXPIRED`; altered signature or `alg: none`: 401 `TOKEN_INVALID`; no token: 401 `NOT_AUTHENTICATED`; all with `WWW-Authenticate: Bearer` | TC-020-05, TC-020-06 |
| FEAT-020-AC-05 | Deactivated user's still-valid token: 401 `TOKEN_INVALID` on the next request | TC-020-07 |
| FEAT-020-AC-06 | Logout 204 with one `auth.logout` row; `/auth/me` returns e-mail, display name and role | TC-020-08 |
| FEAT-020-AC-07 | Revoked key 401 `API_KEY_INVALID`; key without `ingest:write` 403 `FORBIDDEN`; key in query string treated as absent (401) | TC-020-09 |
| FEAT-020-AC-08 | Logs of login plus authorised request contain neither the password, the JWT nor the e-mail | TC-020-15 |

## Test Data Requirements

- `test_v0_1` seed: `admin@example.com`, `clinician@example.com`, `researcher@example.com` with `SEED_*` passwords; key `test-ingest` (`SEED_INGEST_API_KEY`).
- Synthetic users `qa.inactive@example.com`, `qa.rehash@example.com` and synthetic keys `qa-pipeline-only`, `qa-revoked`, created by the CLI; passwords chosen at run time and never recorded.
- Non-existent e-mail `nobody@example.com`; synthetic wrong value `qa-probe-value-1` (not a credential).
- `X-Forwarded-For` addresses from 203.0.113.0/24 (TEST-NET-3) to stay under the per-IP login limit.
- `JWT_SECRET` read from the environment inside the REPL only; never printed.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-020-FR-01 / API-020 / FR-210 / D-04 | FEAT-020 | TC-020-01 |
| FEAT-020-FR-02 / SEC-030 | FEAT-020 | TC-020-01, TC-020-05 |
| FEAT-020-FR-03 / SEC-031 | FEAT-020 | TC-020-01, TC-020-06 |
| FEAT-020-FR-04 / SEC-032 | FEAT-020 | TC-020-01, TC-020-05 |
| FEAT-020-FR-05 / API-021 / SEC-013 / SEC-014 / FR-214 | FEAT-020 | TC-020-03 |
| FEAT-020-FR-06 / SEC-015 | FEAT-020 | TC-020-04 |
| FEAT-020-FR-07 / API-022 | FEAT-020 | TC-020-02, TC-020-03, TC-020-04 |
| FEAT-020-FR-08 / SEC-011 | FEAT-020 | TC-020-12 |
| FEAT-020-FR-09 / API-023 / FR-216 | FEAT-020 | TC-020-08 |
| FEAT-020-FR-10 / API-025 / SEC-036 / FR-217 / TST-069 | FEAT-020 | TC-020-08 |
| FEAT-020-FR-11 / API-012 / API-024 | FEAT-020 | TC-020-05, TC-020-06, TC-020-07 |
| FEAT-020-FR-12 / SEC-034 | FEAT-020 | TC-020-07, TC-020-13 |
| FEAT-020-FR-13 / API-014 / SEC-022 / SEC-024 | FEAT-020 | TC-020-09 |
| FEAT-020-FR-14 / API-015 | FEAT-020 | TC-020-10 |
| FEAT-020-FR-15 / SEC-026 / SEC-027 | FEAT-020 | TC-020-09, TC-020-10 |
| FEAT-020-FR-16 / SEC-025 | FEAT-020 | TC-020-11 |
| FEAT-020-FR-17 / FR-212 | FEAT-020 | TC-020-14 |
| FEAT-020-FR-18 / SEC-035 | FEAT-020 | TC-020-16 |
| TST-032 | FEAT-020 | TC-020-01 |
| TST-053 | FEAT-020 | TC-020-02, TC-020-03, TC-020-08 |
| TST-132 | FEAT-020 | TC-020-05, TC-020-09 |
| AC-LOG-02 | FEAT-020, FEAT-018 | TC-020-15 |
