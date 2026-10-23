# FEAT-022 Rate limiting and abuse controls

| Field | Value |
|---|---|
| Epic | Authentication & Security |
| Build phase | Phase 5 (TRD 25) |
| Priority | P1 |
| Complexity | Low |
| MVP status | Required |
| Dependencies | FEAT-020 |
| Status | Not Started |

## Purpose

Bound the request rate of every authenticated caller so that password guessing, a misbehaving device or a runaway script cannot exhaust the small interim backend: in-memory slowapi limits of 5 logins per minute per client IP, 600 ingest requests per minute per API key (or admin user), and 300 requests per minute per user on other authenticated endpoints, each returning 429 `RATE_LIMITED` with `Retry-After`; the health endpoint is exempt.

## Business Context

- BR-16: brute-force and abuse protection for login and ingest (FR-014, FR-215).
- BR-17 / ASM-08: the interim single-instance stack needs protection against accidental overload without extra infrastructure (in-memory storage, no Redis).

## Referenced TRDs

- TRD 12 SEC-090..SEC-093.
- TRD 05 API-098, API-102, API-103, API-112.
- TRD 10 ING-011.
- TRD 21 ENV-054, `RATE_LIMIT_LOGIN` and `RATE_LIMIT_INGEST` variables.
- TRD 02 FR-014, FR-215.
- TRD 13 TST-131, §4.2 autouse limiter reset.
- TRD 24 D-74.

## Scope

- `backend/core/rate_limit.py`: one slowapi `Limiter` with in-memory storage, created in `create_app()`.
- Key functions: client IP = left-most `X-Forwarded-For` address set by the Railway edge (uvicorn `--proxy-headers --forwarded-allow-ips="*"` in the deployed start commands, TRD 15 DEP-022 and DEP-040), socket peer locally (the Compose command omits the flags); API key identity = SHA-256 of `X-API-Key`; user identity = user id from the authenticated principal.
- Limits: `POST /api/v1/auth/login` = `RATE_LIMIT_LOGIN` per client IP (default `5/minute`); `POST /api/v1/sessions` and `POST /api/v1/ingest` = `RATE_LIMIT_INGEST` (default `600/minute`) per API key hash or per admin user id; all other authenticated endpoints = `300/minute` per user id; `GET /api/v1/health` exempt.
- 429 handler producing Problem `RATE_LIMITED` with `Retry-After` (seconds) through the FEAT-019 error model.
- On a login request rejected by the limiter, an `auth.login.failed` audit row with `reason = rate_limited`; no audit row for other 429s.
- Test-support hook used by the autouse fixture of `tests/conftest.py` to empty the in-memory storage before every test (D-74).

## Out of Scope

- Account lockout after 10 failed logins (SEC-015, FEAT-020), which returns `ACCOUNT_TEMPORARILY_LOCKED`.
- Startup validation that `RATE_LIMIT_LOGIN` is `5/minute` in staging and production (ENV-054, FEAT-003).
- Distributed or persistent rate-limit storage (not in SRC-01; single instance).
- E2E stack configuration of `60/minute` (FEAT-080, D-74).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-022-FR-01 | Rate limiting shall use slowapi with in-memory storage. | API-102 |
| FEAT-022-FR-02 | `POST /api/v1/auth/login` shall be limited to `RATE_LIMIT_LOGIN` per client IP (5/minute; 60/minute only on the E2E stack with `APP_ENV` in {local, test}). | SEC-091, API-102, FR-215, ENV-054, D-74 |
| FEAT-022-FR-03 | `POST /api/v1/sessions` and `POST /api/v1/ingest` shall be limited to `RATE_LIMIT_INGEST` (600/minute) per API key hash or per admin user id. | SEC-090, ING-011, API-102, FR-014 |
| FEAT-022-FR-04 | All other authenticated endpoints shall be limited to 300/minute per user id. | SEC-092, API-102 |
| FEAT-022-FR-05 | Exceeding a limit shall return 429 `RATE_LIMITED` with a `Retry-After` header in seconds. | SEC-093, API-098, ING-011 |
| FEAT-022-FR-06 | A rate-limited login shall write `auth.login.failed` with reason `rate_limited`; other 429s write no audit row. | SEC-093 |
| FEAT-022-FR-07 | The client IP for rate limiting shall be the left-most `X-Forwarded-For` address set by the Railway edge; locally it is the socket peer. | API-103 |
| FEAT-022-FR-08 | `GET /api/v1/health` shall be exempt from rate limiting. | API-112 |
| FEAT-022-FR-09 | The limiter storage shall be resettable by the test suite before every test so limits never leak between tests. | TST-131, D-74 |

## Inputs

- Requests to login, ingest and other authenticated endpoints; `X-Forwarded-For`, `X-API-Key`, authenticated principal; settings `RATE_LIMIT_LOGIN`, `RATE_LIMIT_INGEST`.

## Outputs

- 429 `RATE_LIMITED` Problem responses with `Retry-After`; `auth.login.failed` audit rows for limited logins.

## Data Flow

Request → (FEAT-018 request-ID, FEAT-019 middleware) → limiter computes the key (IP, API key hash or user id) for the route's limit → within limit: handler runs → over limit: 429 Problem with `Retry-After`; for login, the `auth.login.failed` (`rate_limited`) audit row is written in its own committed transaction.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-020

- FEAT-020 provides the authenticated principal (user id or API key) used as the limit key, and the login endpoint that is limited.

Features that build directly on this one (BACKLOG.md §4): FEAT-025.

## Database Impact

- Tables written: `audit_logs` (`auth.login.failed` with `reason = rate_limited`).
- Tables created or modified: none; limiter state is in memory only.

## API Impact

- Applies to E-02 login, E-05 `/sessions`, E-06 `/ingest`, and every other authenticated endpoint (300/minute); E-01 health exempt.
- Adds 429 `RATE_LIMITED` with `Retry-After` to their documented error sets (TRD 19 §4.3).

## Frontend Impact

None in code; the frontend shows the Problem message for 429 (FEAT-062).

## Analytics Impact

None.

## Security Requirements

- Login brute-force protection per IP (SEC-091) in addition to per-e-mail lockout (SEC-015).
- Ingest flood protection per key (SEC-090).
- The IP is taken from the trusted platform header only behind the hosting edge (`--forwarded-allow-ips="*"` only in the deployed start commands; API-103).

## Error Handling

- Over limit: 429 `RATE_LIMITED`, `Retry-After` seconds, Problem body with `request_id` (API-098).
- Limiter internal error: treat as a 500 through FEAT-019 (no silent bypass).
- Memory reset on process restart is acceptable (in-memory storage, single instance).

## Logging Requirements

- `request_completed` at WARNING for 429 (LOG-010).
- Audit `auth.login.failed` with `details.reason = "rate_limited"` for limited logins only (SEC-093, TRD 12 §4.12).

## Testing Requirements

- Security (`tests/security/test_rate_limits.py`, marker `security`): TST-131 — on an app created with `RATE_LIMIT_LOGIN=5/minute` and `RATE_LIMIT_INGEST=600/minute`, the 6th login within 60 s from one IP returns 429; the 601st `POST /api/v1/sessions` within 60 s with one key returns 429; both carry `Retry-After`.
- Integration: rate-limited login writes one `auth.login.failed` row with reason `rate_limited`; a 429 on ingest writes no audit row (SEC-093); health is never limited (API-112); `X-Forwarded-For: 203.0.113.5, 10.0.0.1` keys on `203.0.113.5` (API-103).
- Unit: the autouse limiter reset fixture empties storage (D-74).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-022-AC-01 | With `RATE_LIMIT_LOGIN=5/minute`, the sixth `POST /api/v1/auth/login` within 60 s from one IP returns 429 `RATE_LIMITED` with a numeric `Retry-After`. | TST-131, FR-215, AC-API-09 |
| FEAT-022-AC-02 | With `RATE_LIMIT_INGEST=600/minute`, the 601st `POST /api/v1/sessions` within 60 s with one API key returns 429 `RATE_LIMITED` with `Retry-After`. | TST-131, FR-014, ING-011 |
| FEAT-022-AC-03 | The rate-limited login writes exactly one `auth.login.failed` audit row with `details.reason = "rate_limited"`; the rate-limited ingest request writes no audit row. Verified by: Integration (a 429 on ingest writes no audit row (SEC-093)). | SEC-093 |
| FEAT-022-AC-04 | 1,000 consecutive `GET /api/v1/health` requests within a minute all return 200 or 503, never 429. Verified by: Integration (health is never limited (API-112)). | API-112 |
| FEAT-022-AC-05 | Two requests with different left-most `X-Forwarded-For` addresses are counted separately for the login limit. Verified by: Integration (`X-Forwarded-For: 203.0.113.5, 10.0.0.1` keys on `203.0.113.5` (API-103)). | API-103 |

## Definition of Done

- All FEAT-022 acceptance criteria pass; TST-131 passes with the autouse reset fixture.
- Delivered in the Phase 5 checkpoint PR of Block 3.

## Implementation Notes

- Set uvicorn `--proxy-headers --forwarded-allow-ips="*"` only in the deployed start commands (DEP-022 image default, DEP-040 Railway start command), never in the local Compose command; locally the socket peer is the key (API-103).
- slowapi decorators need the `Request` parameter on handlers; keep handlers `def` (API-007).
- Use the SHA-256 of the key (not the plaintext) as the limit key so no plaintext key is held in limiter memory beyond the request.
- Because `get_db()` rolls back on exceptions, write the `rate_limited` audit row in its own committed transaction (same pattern as FEAT-020's failed-login row).
