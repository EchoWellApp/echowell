# Rate limiting and abuse controls

## Feature Description

FEAT-022 bounds request rates with one slowapi `Limiter` using in-memory storage (`backend/core/rate_limit.py`): `POST /api/v1/auth/login` is limited to `RATE_LIMIT_LOGIN` per client IP (default `5/minute`; the client IP is the left-most `X-Forwarded-For` address behind the Render edge, the socket peer locally); `POST /api/v1/sessions` and `POST /api/v1/ingest` share `RATE_LIMIT_INGEST` (default `600/minute`) per API-key hash or per admin user id; every other authenticated endpoint is limited to `300/minute` per user id; `GET /api/v1/health` is exempt. Exceeding a limit returns 429 `RATE_LIMITED` (Problem body, title "Too many requests", detail "Too many requests. Try again later.") with a numeric `Retry-After` in seconds. A rate-limited login writes one `auth.login.failed` audit row with `details.reason = "rate_limited"`; other 429s write no audit row. The test suite empties the limiter storage before every test.

## Preconditions

- Local development stack running; `.env` from `.env.development.example` with `RATE_LIMIT_LOGIN=5/minute`, `RATE_LIMIT_INGEST=600/minute`, `APP_ENV=local`, `PIPELINE_PROFILE=test_v0_1`, `SEED_*` set (values never written down).
- Database seeded: `python -m backend.cli seed test_v0_1 --reset`.
- Restart the backend (`docker compose restart backend`) before each case so the in-memory counters start empty.
- `curl -i` against `http://localhost:8000/api/v1`; Python 3.12 with `httpx` for the loop steps (a short script in the tester's scratch folder sending N requests and printing the status of each).
- `psql` for read-only checks on `audit_logs`, `ingest_rejections`.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-022-01 | Sixth login within 60 s from one IP returns 429 `RATE_LIMITED` with numeric `Retry-After` | High | Negative |
| TC-022-02 | Rate-limited login writes exactly one `auth.login.failed` row with reason `rate_limited` | High | Database |
| TC-022-03 | 601st `POST /sessions` within 60 s with one key returns 429; no audit row | High | Negative |
| TC-022-04 | `/sessions` and `/ingest` share one counter per key; another key is unaffected | Medium | API |
| TC-022-05 | Different left-most `X-Forwarded-For` addresses are counted separately for login | High | Security |
| TC-022-06 | 1,000 health requests in a minute never return 429 | High | Performance |
| TC-022-07 | Other authenticated endpoints allow 300 per minute per user | Medium | Negative |
| TC-022-08 | 429 response shape and access-log level | Medium | API |
| TC-022-09 | Counters are in memory and reset on restart; window expiry lifts the limit | Medium | Positive |
| TC-022-10 | Automated rate-limit suite passes twice in a row (autouse reset) | Medium | Positive |

### TC-022-01 Sixth login within 60 s from one IP returns 429 `RATE_LIMITED` with numeric `Retry-After`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Within 60 s send 5 `POST /api/v1/auth/login` requests with `{"email": "admin@example.com", "password": "$SEED_ADMIN_PASSWORD"}` and no `X-Forwarded-For` | Each 200 |
| 2 | Send a 6th identical request within the same 60 s | 429; `Content-Type: application/problem+json`; `type` `urn:echowell:error:RATE_LIMITED`; `title` `Too many requests`; `detail` `Too many requests. Try again later.` |
| 3 | Read `Retry-After` | Integer between 1 and 60 |
| 4 | Send a 7th request with a wrong password | 429 (limit applies before credentials are checked) |

### TC-022-02 Rate-limited login writes exactly one `auth.login.failed` row with reason `rate_limited`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Restart the backend; record `SELECT count(*) FROM audit_logs WHERE action = 'auth.login.failed';` | Baseline F |
| 2 | Send 5 logins for `clinician@example.com` with the correct `SEED_CLINICIAN_PASSWORD`, then a 6th with `X-Request-ID: qa-rate-login-06` | 5 × 200, then 429 |
| 3 | `SELECT actor_type, actor_id, details FROM audit_logs WHERE request_id = 'qa-rate-login-06';` | Exactly 1 row: `auth.login.failed`, `actor_type` `system`, `actor_id` NULL, `details` `{"email": "clinician@example.com", "reason": "rate_limited"}`; no password |
| 4 | Re-count | F + 1 |

### TC-022-03 601st `POST /sessions` within 60 s with one key returns 429; no audit row

| Step | Action | Expected Result |
|---|---|---|
| 1 | Restart the backend; record `SELECT count(*) FROM audit_logs;` | Baseline A |
| 2 | With a script, send 601 `POST /api/v1/sessions` requests within 60 s, each with `X-API-Key: $SEED_INGEST_API_KEY`, `Content-Type: application/json` and body `{}` | Requests 1–600 return 422 (rejected record, counted by the limiter); request 601 returns 429 `RATE_LIMITED` with a numeric `Retry-After` |
| 3 | `SELECT count(*) FROM audit_logs WHERE action = 'auth.login.failed' AND occurred_at > now() - interval '2 minutes';` | 0 (ingest 429 writes no audit row) |
| 4 | Check that no `access.denied` row was written for the 429 | `SELECT count(*) FROM audit_logs WHERE action = 'access.denied' AND occurred_at > now() - interval '2 minutes';` = 0 |
| 5 | Reset afterwards: `python -m backend.cli seed test_v0_1 --reset` | Exit code 0 (removes the 600 stored rejections) |
| 6 | Run `pytest -m integration tests/integration/api/test_rate_limits.py -q -k ingest_limit_is_per_api_key` | Passes (TST-131) |

### TC-022-04 `/sessions` and `/ingest` share one counter per key; another key is unaffected

| Step | Action | Expected Result |
|---|---|---|
| 1 | Restart the backend with `RATE_LIMIT_INGEST=10/minute` (local only, to keep the test short) | Backend healthy |
| 2 | With `X-API-Key: $SEED_INGEST_API_KEY`, send 6 `POST /api/v1/sessions` (body `{}`) then 4 `POST /api/v1/ingest` (body `[]`) within 60 s | None returns 429 |
| 3 | Send an 11th request (either path) with the same key | 429 `RATE_LIMITED` |
| 4 | Send `POST /api/v1/sessions` with a second key `qa-rate-key` (created with `create-api-key --name qa-rate-key`) | Not 429 (separate counter per key hash) |
| 5 | As admin (bearer token), send `POST /api/v1/ingest` | Not 429 (admin counted per user id) |
| 6 | Restore `RATE_LIMIT_INGEST=600/minute`, restart, reset the database | Done |

### TC-022-05 Different left-most `X-Forwarded-For` addresses are counted separately for login

| Step | Action | Expected Result |
|---|---|---|
| 1 | Restart the backend. Send 5 logins (correct admin credentials) with `X-Forwarded-For: 203.0.113.5, 10.0.0.1` | Each 200 |
| 2 | Send a 6th with `X-Forwarded-For: 203.0.113.5, 10.0.0.99` | 429 (keyed on the left-most `203.0.113.5`, not the right-hand entry) |
| 3 | Send a login with `X-Forwarded-For: 198.51.100.7, 10.0.0.1` | 200 (different left-most address, separate counter) |
| 4 | Run `pytest -m integration tests/integration/api/test_rate_limits.py -q -k left_most_forwarded_address` | Passes |
| 5 | **Hosted**: on staging, send 6 logins within 60 s from one workstation | 6th returns 429 (Render edge sets `X-Forwarded-For`; uvicorn runs with `--proxy-headers --forwarded-allow-ips="*"`) |

Note: TRD 05 API-103 says the key is the socket peer locally (the Compose command has no `--proxy-headers`); `backend/core/rate_limit.py:35` reads `X-Forwarded-For` from the request headers whenever it is present, so locally a client-supplied header changes the key. Steps 1–3 rely on that behaviour; record it as a difference from API-103.

### TC-022-06 1,000 health requests in a minute never return 429

| Step | Action | Expected Result |
|---|---|---|
| 1 | With a script send 1,000 `GET /api/v1/health` requests within 60 s from one client | Every status is 200 (or 503 if the database is down); count of 429 = 0 |
| 2 | Run `pytest -m integration tests/integration/api/test_rate_limits.py -q -k health_is_never_rate_limited` | Passes |

### TC-022-07 Other authenticated endpoints allow 300 per minute per user

| Step | Action | Expected Result |
|---|---|---|
| 1 | Restart the backend; as the researcher send 300 `GET /api/v1/config/ui` requests within 60 s | All 200 |
| 2 | Send the 301st within the same minute | 429 `RATE_LIMITED` with `Retry-After` |
| 3 | As the clinician, `GET /api/v1/config/ui` immediately | 200 (counter is per user id) |
| 4 | `SELECT count(*) FROM audit_logs WHERE occurred_at > now() - interval '2 minutes' AND action IN ('auth.login.failed','access.denied');` | 0 |
| 5 | Run `pytest -m integration tests/integration/api/test_rate_limits.py -q -k other_endpoints_allow_300` | Passes |

### TC-022-08 429 response shape and access-log level

| Step | Action | Expected Result |
|---|---|---|
| 1 | Produce a 429 as in TC-022-01 with `X-Request-ID: qa-rate-shape-01` | Body keys exactly `type`, `title`, `status` (429), `detail`, `request_id` (`qa-rate-shape-01`), `errors` (`[]`); headers `Retry-After` and `X-Request-ID` |
| 2 | Find the `request_completed` log line with that request ID (`docker compose logs backend`) | `"level": "WARNING"`, `status` 429, `route` `/api/v1/auth/login` |

### TC-022-09 Counters are in memory and reset on restart; window expiry lifts the limit

| Step | Action | Expected Result |
|---|---|---|
| 1 | Reach the login limit (6th request 429) and note `Retry-After` = R | 429 |
| 2 | Wait R + 1 seconds and log in again | 200 |
| 3 | Reach the limit again, then `docker compose restart backend` and log in once | 200 (in-memory storage emptied by the restart) |
| 4 | Run `grep -n "storage_uri" backend/core/rate_limit.py` | `storage_uri="memory://"` (no Redis or database storage) |

### TC-022-10 Automated rate-limit suite passes twice in a row (autouse reset)

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `pytest -m integration tests/integration/api/test_rate_limits.py -q` twice in a row | Both runs pass with the same count (no limit leaks between tests) |
| 2 | Run `grep -n "limiter.reset\|reset()" tests/conftest.py` | An autouse fixture empties the limiter storage before every test (D-74) |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/auth/login` × 6 in 60 s, one IP | 6th: 429 `RATE_LIMITED`, numeric `Retry-After` |
| 2 | `POST /api/v1/sessions` × 601 in 60 s, one key | 601st: 429 `RATE_LIMITED`, `Retry-After` |
| 3 | Authenticated `GET` × 301 in 60 s, one user | 301st: 429 |
| 4 | `GET /api/v1/health` × 1,000 | Never 429 |
| 5 | `GET /api/v1/openapi.json` | 429 `RATE_LIMITED` listed in the error responses of E-02, E-05 and E-06 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT details FROM audit_logs WHERE action = 'auth.login.failed' AND details->>'reason' = 'rate_limited' ORDER BY id DESC LIMIT 1;` after TC-022-02 | `{"email": "clinician@example.com", "reason": "rate_limited"}` |
| 2 | Audit rows written during TC-022-03, TC-022-06, TC-022-07 | No `auth.login.failed` or `access.denied` row caused by a 429 |
| 3 | `SELECT count(*) FROM information_schema.tables WHERE table_name ILIKE '%rate%';` | 0 (limiter state is in memory only) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Sixth login in 60 s from one IP | 429 + `auth.login.failed` (`rate_limited`) |
| 2 | 601st ingest request in 60 s with one key | 429, no audit row |
| 3 | 301st other request in 60 s by one user | 429 |
| 4 | Wrong password while rate-limited | 429 (not 401) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-022-AC-01 | With `RATE_LIMIT_LOGIN=5/minute`, the 6th login within 60 s from one IP returns 429 `RATE_LIMITED` with numeric `Retry-After` | TC-022-01, TC-022-08 |
| FEAT-022-AC-02 | With `RATE_LIMIT_INGEST=600/minute`, the 601st `POST /api/v1/sessions` within 60 s with one key returns 429 `RATE_LIMITED` with `Retry-After` | TC-022-03 |
| FEAT-022-AC-03 | Rate-limited login writes exactly one `auth.login.failed` row with `details.reason = "rate_limited"`; rate-limited ingest writes no audit row | TC-022-02, TC-022-03 |
| FEAT-022-AC-04 | 1,000 consecutive health requests within a minute return 200 or 503, never 429 | TC-022-06 |
| FEAT-022-AC-05 | Requests with different left-most `X-Forwarded-For` addresses are counted separately for login | TC-022-05 |

## Test Data Requirements

- `test_v0_1` seed: seeded users with `SEED_*` passwords; key `test-ingest` (`SEED_INGEST_API_KEY`); synthetic key `qa-rate-key`.
- Addresses from the documentation ranges 203.0.113.0/24 and 198.51.100.0/24, plus private 10.0.0.0/8 for proxy entries.
- Load script (httpx loop) kept in the tester's scratch folder; bodies `{}` / `[]` only (no feature values, no audio).
- Environment: `RATE_LIMIT_LOGIN`, `RATE_LIMIT_INGEST` (temporary `10/minute` only in TC-022-04, restored afterwards).

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-022-FR-01 / API-102 | FEAT-022 | TC-022-09 |
| FEAT-022-FR-02 / SEC-091 / FR-215 / ENV-054 / D-74 | FEAT-022 | TC-022-01, TC-022-05 |
| FEAT-022-FR-03 / SEC-090 / ING-011 / FR-014 | FEAT-022 | TC-022-03, TC-022-04 |
| FEAT-022-FR-04 / SEC-092 | FEAT-022 | TC-022-07 |
| FEAT-022-FR-05 / SEC-093 / API-098 | FEAT-022 | TC-022-01, TC-022-03, TC-022-08 |
| FEAT-022-FR-06 / SEC-093 | FEAT-022 | TC-022-02, TC-022-03 |
| FEAT-022-FR-07 / API-103 | FEAT-022 | TC-022-05 |
| FEAT-022-FR-08 / API-112 | FEAT-022 | TC-022-06 |
| FEAT-022-FR-09 / TST-131 / D-74 | FEAT-022 | TC-022-10 |
| TST-131 | FEAT-022 | TC-022-01, TC-022-03 |
| AC-API-09 | FEAT-022 | TC-022-01 |
| LOG-010 (429 at WARNING) | FEAT-022, FEAT-018 | TC-022-08 |
