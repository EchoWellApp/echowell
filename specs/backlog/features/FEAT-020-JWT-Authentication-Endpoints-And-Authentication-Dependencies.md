# FEAT-020 JWT authentication endpoints and authentication dependencies

| Field | Value |
|---|---|
| Epic | Authentication & Security |
| Build phase | Phase 5 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-016, FEAT-019 |
| Status | Not Started |

## Purpose

Authenticate every caller of the API: dashboard users through `POST /api/v1/auth/login` (HS256 JWT valid 60 minutes, no refresh token), `POST /api/v1/auth/logout` and `GET /api/v1/auth/me`; devices and schedulers through hashed `X-API-Key` keys with scopes. The reusable dependencies `get_current_user`, `get_api_key(scope)` and `get_ingest_principal` read role, active flag and key state from the database on every request, so deactivation and revocation take effect immediately.

## Business Context

- BR-16: authenticated access for all endpoints except health and login (FR-212); inactive users cannot log in (FR-214); logout is recorded (FR-217).
- BR-13: staff log in at `/login` and receive a 60-minute token (FR-210, D-04); `/auth/me` returns their e-mail, display name and role (FR-216).
- BR-01: devices authenticate to ingest with an API key of scope `ingest:write` (ARC-004).

## Referenced TRDs

- TRD 05 API-012..API-015 (auth dependencies), API-020..API-025 (auth endpoints).
- TRD 12 SEC-013..SEC-015 (dummy verification, uniform 401, lockout), SEC-025..SEC-027 (key usage), SEC-030..SEC-036 (JWT).
- TRD 19 §4.3 E-02, E-03, E-04; schemas `LoginRequest`, `Token`, `User`.
- TRD 02 FR-210, FR-212, FR-214, FR-216, FR-217.
- TRD 13 TST-032, TST-053, TST-069, TST-132.
- TRD 17 AC-LOG-02.
- TRD 24 D-04.

## Scope

- `backend/core/security.py` (extending FEAT-016): `issue_token(user)` and `decode_token(token)` with PyJWT 2.x, HS256, `JWT_SECRET`, claims `sub`, `role`, `iat`, `exp`, `jti` (UUID4), `iss="echowell-api"`, `aud="echowell-dashboard"`, decoding with `algorithms=["HS256"]` and verifying `iss`, `aud`, `exp`.
- `backend/api/deps.py`:
  - `get_current_user()` → decode Bearer token; 401 `NOT_AUTHENTICATED` without token, `TOKEN_EXPIRED` when expired, `TOKEN_INVALID` when malformed, wrongly signed, user missing or inactive; every 401 with `WWW-Authenticate: Bearer`; sets the logging actor context (FEAT-018).
  - `get_api_key(scope)` → SHA-256 of `X-API-Key`, load the active row whose `scopes` contain `scope`; 401 `API_KEY_INVALID` when missing, unknown or inactive; 403 `FORBIDDEN` when the scope is missing; update `last_used_at` at most once per minute per key.
  - `get_ingest_principal()` → valid `ingest:write` key or admin JWT user; returns `Principal(actor_type, actor_id, device_id)`.
- `backend/api/auth.py` and `backend/services/auth.py`:
  - `POST /api/v1/auth/login` (E-02): body `LoginRequest`; normalise e-mail; unknown e-mail verified against the dummy hash; wrong password, unknown e-mail and inactive user all 401 `INVALID_CREDENTIALS` with identical body; lockout 429 `ACCOUNT_TEMPORARILY_LOCKED` after 10 `auth.login.failed` rows for the e-mail in 15 minutes, until 15 minutes after the last failure; on success rehash if needed, update `last_login_at`, write `auth.login.succeeded`, return 200 `Token` (`access_token`, `token_type="bearer"`, `expires_in` = `JWT_EXPIRES_MINUTES`×60, `user`).
  - `POST /api/v1/auth/logout` (E-03): valid token required; write `auth.logout`; 204; no server-side revocation.
  - `GET /api/v1/auth/me` (E-04): returns `User`.
- DTOs in `backend/schemas/auth.py` (`LoginRequest`, `Token`) and `backend/schemas/user.py` (`User`) per TRD 23 §4.6.

## Out of Scope

- `require_roles` and the role matrix enforcement with `access.denied` audit (FEAT-021).
- Rate limiting `RATE_LIMITED` (5/minute per IP) on login (FEAT-022).
- `/users` management (FEAT-037).
- Device-key mismatch checks on ingest records (FEAT-023, FEAT-025).
- Frontend token storage and route guard (FEAT-063).
- The exhaustive endpoint × credential matrix test (FEAT-039).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-020-FR-01 | `POST /api/v1/auth/login` shall accept JSON `{email, password}` and on success return 200 `Token` with `access_token`, `token_type` "bearer", `expires_in` = `JWT_EXPIRES_MINUTES`×60 and `user`. | API-020, FR-210, D-04 |
| FEAT-020-FR-02 | Tokens shall be HS256 JWTs signed with `JWT_SECRET` via PyJWT 2.x; decoding passes `algorithms=["HS256"]` so `none` and other algorithms are rejected. | SEC-030 |
| FEAT-020-FR-03 | Claims shall be `sub` (user UUID), `role`, `iat`, `exp`, `jti` (UUID4), `iss` "echowell-api", `aud` "echowell-dashboard"; `iss`, `aud` and `exp` are verified on every request. | SEC-031 |
| FEAT-020-FR-04 | Token lifetime shall be `JWT_EXPIRES_MINUTES` (default 60; at most 60 in staging and production); no refresh tokens. | SEC-032, D-04 |
| FEAT-020-FR-05 | Unknown e-mail, wrong password and inactive user shall all return 401 `INVALID_CREDENTIALS` with identical body and comparable latency; an unknown e-mail performs one argon2id verification against a fixed dummy hash. | API-021, SEC-013, SEC-014, FR-214 |
| FEAT-020-FR-06 | After 10 failed logins for the same e-mail within 15 minutes (counted from `audit_logs` `auth.login.failed`), further attempts shall return 429 `ACCOUNT_TEMPORARILY_LOCKED` until 15 minutes after the last failure. | SEC-015 |
| FEAT-020-FR-07 | Login shall update `users.last_login_at` and write `auth.login.succeeded`; a failure writes `auth.login.failed` with details `{email (lower-cased), reason}` (`invalid_credentials`, `locked` or `rate_limited`). | API-022, TRD 12 §4.12 |
| FEAT-020-FR-08 | On successful login, a stored hash with parameters other than SEC-010 shall be recomputed and stored. | SEC-011 |
| FEAT-020-FR-09 | `GET /api/v1/auth/me` shall return the current `User` (e-mail, display name, role and the other `User` fields) for any active user role. | API-023, FR-216 |
| FEAT-020-FR-10 | `POST /api/v1/auth/logout` shall require a valid token, write `auth.logout`, return 204, and not revoke the token server-side. | API-025, SEC-036, FR-217 |
| FEAT-020-FR-11 | `get_current_user()` shall load the user by `sub` and reject with 401 `TOKEN_INVALID` when missing or inactive; requests without a token get 401 `NOT_AUTHENTICATED`, expired tokens 401 `TOKEN_EXPIRED`, malformed or wrongly signed tokens 401 `TOKEN_INVALID`; every 401 carries `WWW-Authenticate: Bearer`. | API-012, API-024 |
| FEAT-020-FR-12 | Authorisation data (role, `active`) shall be read from `users` on every request; the `role` claim is informational only. | SEC-034 |
| FEAT-020-FR-13 | `get_api_key(scope)` shall hash `X-API-Key` with SHA-256, load an active key containing the required scope, and reject with 401 `API_KEY_INVALID` (missing, unknown, inactive) or 403 `FORBIDDEN` (scope missing). | API-014, SEC-022, SEC-024 |
| FEAT-020-FR-14 | `get_ingest_principal()` shall accept a valid `ingest:write` API key or an admin JWT user and return `Principal(actor_type, actor_id, device_id)`. | API-015 |
| FEAT-020-FR-15 | API keys shall be accepted only in the `X-API-Key` header (never query or body) and rejected with 401 on every endpoint except `POST /sessions`, `POST /ingest` (`ingest:write`) and `POST /pipeline/run` (`pipeline:run`). | SEC-026, SEC-027 |
| FEAT-020-FR-16 | `api_keys.last_used_at` shall be updated at most once per minute per key. | SEC-025 |
| FEAT-020-FR-17 | All endpoints except `GET /api/v1/health` and `POST /api/v1/auth/login` shall return 401 without valid credentials (each router declares an auth dependency). | FR-212 |
| FEAT-020-FR-18 | Rotating `JWT_SECRET` shall invalidate all issued tokens (emergency revocation). | SEC-035 |

## Inputs

- `LoginRequest` JSON; `Authorization: Bearer <jwt>` header; `X-API-Key` header.
- `users`, `api_keys`, `audit_logs` rows; `JWT_SECRET`, `JWT_EXPIRES_MINUTES` settings.

## Outputs

- `Token` and `User` responses; 204 on logout; 401/403/429 Problem responses.
- Audit rows `auth.login.succeeded`, `auth.login.failed`, `auth.logout`; `users.last_login_at` and `api_keys.last_used_at` updates.
- `CurrentUser` and `Principal` objects for downstream dependencies.

## Data Flow

Login: request → e-mail normalised → lockout check (count of `auth.login.failed` for the e-mail in 15 min) → user lookup → argon2id verify (dummy hash if unknown) → on failure write `auth.login.failed` and return 401 → on success rehash if needed, update `last_login_at`, write `auth.login.succeeded`, issue JWT → 200. Authenticated request: `get_current_user` decodes and verifies the JWT → loads the user → checks `active` → sets actor context → handler. Key request: `get_api_key(scope)` hashes the header → loads the active key → checks scope → updates `last_used_at` if older than one minute → handler.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-016, FEAT-019

- FEAT-016 provides argon2id hashing, rehash detection, e-mail normalisation, the dummy hash and API-key hashing.
- FEAT-019 provides the Problem error rendering for `NOT_AUTHENTICATED`, `TOKEN_EXPIRED`, `TOKEN_INVALID`, `INVALID_CREDENTIALS`, `API_KEY_INVALID`, `FORBIDDEN`, `ACCOUNT_TEMPORARILY_LOCKED`.

Features that build directly on this one (BACKLOG.md §4): FEAT-021, FEAT-022, FEAT-063.

## Database Impact

- Tables read: `users`, `api_keys`, `audit_logs` (lockout count).
- Tables written: `users` (`last_login_at`, `password_hash` on rehash), `api_keys` (`last_used_at`), `audit_logs` (INSERT).
- Tables created or modified (schema): none.

## API Impact

- Exposed: E-02 `POST /api/v1/auth/login` (no auth; 200 `Token`; 401 `INVALID_CREDENTIALS`, 422, 429 `RATE_LIMITED`, 429 `ACCOUNT_TEMPORARILY_LOCKED`), E-03 `POST /api/v1/auth/logout` (bearer A/C/Rs; 204), E-04 `GET /api/v1/auth/me` (bearer A/C/Rs; 200 `User`).
- Provides the `bearerAuth` and `apiKeyAuth` security schemes used by every other endpoint.

## Frontend Impact

None in code; the login page and session handling (FEAT-063) call E-02, E-03, E-04.

## Analytics Impact

None.

## Security Requirements

- Authentication: HS256 JWT with explicit algorithm list and verified `iss`/`aud`/`exp` (SEC-030, SEC-031); API keys only via header, hashed lookup (SEC-026, API-014).
- Authorization inputs (role, active) come from the database each request (SEC-034).
- Account enumeration resistance: uniform 401 and dummy verification (SEC-013, SEC-014).
- Brute-force resistance: lockout (SEC-015); per-IP rate limit added by FEAT-022.
- No password, token, key or e-mail in logs (LOG-020, LOG-022).

## Error Handling

| Condition | Response |
|---|---|
| No credentials | 401 `NOT_AUTHENTICATED` + `WWW-Authenticate: Bearer` |
| Expired JWT | 401 `TOKEN_EXPIRED` |
| Bad signature, `alg: none`, wrong `iss`/`aud`, missing or inactive user | 401 `TOKEN_INVALID` |
| Wrong password, unknown e-mail, inactive user at login | 401 `INVALID_CREDENTIALS` (identical body) |
| 10 failures in 15 min for an e-mail | 429 `ACCOUNT_TEMPORARILY_LOCKED` with `Retry-After` |
| Missing, unknown or revoked API key | 401 `API_KEY_INVALID` |
| API key without required scope | 403 `FORBIDDEN` |

## Logging Requirements

- Audit: `auth.login.succeeded` (actor user), `auth.login.failed` (actor system, `details.email` lower-cased and `details.reason`), `auth.logout` (actor user) (TRD 12 §4.12, API-022, API-025).
- Application logs: 401s are logged in application logs only (SEC-108); no password, JWT or e-mail in any log line (AC-LOG-02).

## Testing Requirements

- Unit (`tests/unit/backend/core/test_security.py`): TST-032 JWT issue/verify/expiry at 60 min; claims and `iss`/`aud` verification.
- Integration (`tests/integration/api/test_auth.py`): login success returns `Token` with `expires_in` 3600 and writes `auth.login.succeeded` and `last_login_at`; unknown e-mail, wrong password and inactive user return identical 401 bodies (SEC-014); lockout after 10 failures (SEC-015); `/auth/me` returns the user; logout returns 204 and writes `auth.logout` (TST-069); 401 variants with `WWW-Authenticate: Bearer` (API-024); rehash on login (SEC-011).
- Security (`tests/security/test_tokens.py`, `tests/security/test_api_keys.py`): TST-132 (expired 61-minute JWT, altered signature, `alg: none`, revoked API key → 401; key without `ingest:write` → 403); API key in query string ignored (401) (SEC-026); key on a user endpoint → 401 (SEC-027); `last_used_at` updated at most once per minute (SEC-025).
- Integration: TST-053 audit rows for login, failed login and logout; AC-LOG-02 log capture (no password, JWT or e-mail).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-020-AC-01 | A valid login returns 200 with `token_type` "bearer", `expires_in` 3600 and a JWT whose header `alg` is HS256 and whose claims include `sub`, `role`, `iat`, `exp`, `jti`, `iss` "echowell-api", `aud` "echowell-dashboard"; one `auth.login.succeeded` row is written. Verified by: Unit (`tests/unit/backend/core/test_security.py`). | API-020, SEC-030, SEC-031, FR-210 |
| FEAT-020-AC-02 | Unknown e-mail, wrong password and an inactive user each return 401 `INVALID_CREDENTIALS` with byte-identical bodies apart from `request_id`, and each writes one `auth.login.failed` row. Verified by: Integration (`tests/integration/api/test_auth.py`). | SEC-014, API-021, FR-214 |
| FEAT-020-AC-03 | The 11th login attempt for one e-mail within 15 minutes after 10 failures returns 429 `ACCOUNT_TEMPORARILY_LOCKED`. Verified by: Integration (`tests/integration/api/test_auth.py`). | SEC-015 |
| FEAT-020-AC-04 | A JWT expired by 61 minutes returns 401 `TOKEN_EXPIRED`; an altered signature or `alg: none` token returns 401 `TOKEN_INVALID`; no token returns 401 `NOT_AUTHENTICATED`; all three carry `WWW-Authenticate: Bearer`. | TST-132, API-024 |
| FEAT-020-AC-05 | Deactivating a user makes their still-valid token return 401 `TOKEN_INVALID` on the next request. Verified by: Integration (`tests/integration/api/test_auth.py`). | SEC-034, API-012 |
| FEAT-020-AC-06 | `POST /auth/logout` with a valid token returns 204 and writes one `auth.logout` row; `GET /auth/me` returns the user's e-mail, display name and role. | TST-069, FR-216, FR-217 |
| FEAT-020-AC-07 | A revoked API key returns 401 `API_KEY_INVALID`; a key without `ingest:write` on an `ingest:write` dependency returns 403 `FORBIDDEN`; a valid key sent as a query parameter is treated as absent (401). | TST-132, SEC-024, SEC-026 |
| FEAT-020-AC-08 | Captured logs of a login with password `Secret-123!` and an authorised request contain neither `Secret-123!`, the JWT nor the e-mail address. Verified by: Integration (AC-LOG-02 log capture (no password, JWT or e-mail)). | AC-LOG-02 |

## Definition of Done

- All FEAT-020 acceptance criteria pass; TST-032, TST-069 and TST-132 pass.
- E-02..E-04 appear in the OpenAPI document with the TRD 19 schemas; delivered in the Phase 5 PR.

## Implementation Notes

- `get_db()` rolls back on exceptions (API-011), so the `auth.login.failed` audit row must be written and committed in the failure path before the 401 is raised in its own short transaction on a separate session, as TRD 12 SEC-101 now requires (TRD 24 D-87).
- Count lockout failures with an indexed query on `audit_logs (action, occurred_at DESC)` filtered by `details->>'email'` (index `audit_logs_action_idx`).
- Keep the dummy hash generated with the SEC-010 parameters so verification time matches real users.
- `expires_in` is in seconds (`JWT_EXPIRES_MINUTES` × 60).
