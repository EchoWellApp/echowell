# Structured JSON logging, redaction and request-ID propagation

## Feature Description

FEAT-018 configures backend logging once in `backend/core/logging.py`: single-line JSON on stdout with at least `ts` (UTC), `level`, `logger`, `msg`, `event`, `env` (`APP_ENV`) and `version` (`GIT_SHA`) when `LOG_FORMAT=json`, a readable `ts level logger event key=value…` line when `LOG_FORMAT=console` (refused in staging and production). Context variables carry `request_id`, `actor`, `user_id`, `pipeline_run_id` and `resident_code` into every record. A redaction filter replaces values under keys matching `password|secret|token|authorization|api_key|apikey|cookie|dsn|database_url|body|note` with `[REDACTED]` and masks credentialed URLs and bearer tokens in text. The outermost middleware accepts an incoming `X-Request-ID` matching `^[A-Za-z0-9-]{8,64}$` or generates a UUID4, returns it on every response, and writes exactly one `request_completed` record per request (INFO < 400, WARNING 400–499 except 401 and 404 at INFO, ERROR ≥ 500, healthy `GET /api/v1/health` at DEBUG). An unhandled exception is logged once as ERROR `unhandled_exception`.

## Preconditions

- Local development stack running (`docker compose up -d`); `.env` from `.env.development.example` with `APP_ENV=local`, `LOG_FORMAT=json`, `LOG_LEVEL=INFO`, `GIT_SHA` set, `PIPELINE_PROFILE=test_v0_1`, `SEED_*` set.
- Database seeded: `python -m backend.cli seed test_v0_1 --reset` (exit code 0).
- Backend log stream captured: `docker compose logs -f --no-log-prefix backend > backend.log` started before each case (lines after the `alembic upgrade head` start-up step are the application's).
- `curl` (with `-i` to show headers) against `http://localhost:8000/api/v1`; bearer tokens of the seeded users (passwords from `SEED_*`).
- Python 3.12 virtual environment with the backend requirements for REPL and pytest steps.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-018-01 | Every application log line is one JSON object with the seven required keys | High | Positive |
| TC-018-02 | Timestamps are UTC and `env` / `version` come from `APP_ENV` / `GIT_SHA` | Medium | Positive |
| TC-018-03 | Console format locally; `console` refused in staging | Medium | Negative |
| TC-018-04 | Valid `X-Request-ID` is echoed; invalid value replaced by a UUID4 | High | API |
| TC-018-05 | `X-Request-ID` is present on 200, 401, 404, 422, 429, 503 responses and CORS preflights | High | API |
| TC-018-06 | One `request_completed` per request with the right level per status | High | Positive |
| TC-018-07 | `request_completed` carries the route template, method, status, duration and actor | Medium | Positive |
| TC-018-08 | Healthy health check is logged at DEBUG only | Medium | Positive |
| TC-018-09 | Key-based redaction and URL / bearer masking | High | Security |
| TC-018-10 | Login and an authorised request leave no password, JWT or e-mail in the logs | High | Security |
| TC-018-11 | Forced exception produces exactly one ERROR `unhandled_exception` record | High | Negative |
| TC-018-12 | Request ID reaches `audit_logs.request_id`, including `pipeline.run.started` | High | Database |
| TC-018-13 | Ingest leaves no feature value, body or audio data in the logs | High | Security |
| TC-018-14 | `analytics/` configures no logging | Medium | Documentation |
| TC-018-15 | `LOG_LEVEL=DEBUG` in staging warns `debug_logging_enabled` | Low | Negative |

### TC-018-01 Every application log line is one JSON object with the seven required keys

| Step | Action | Expected Result |
|---|---|---|
| 1 | With the log capture running, log in as admin, call `GET /api/v1/residents`, `GET /api/v1/residents/R09`, `GET /api/v1/does-not-exist`, then stop the capture | Requests complete (200, 200, 404) |
| 2 | Run `python -c "import json,sys; [json.loads(l) for l in open('backend.log') if l.strip().startswith('{')]; print('ok')"` and count lines not starting with `{` after the uvicorn start-up line | Prints `ok`; 0 non-JSON application lines |
| 3 | For every parsed line check the keys | Each object contains `ts`, `level`, `logger`, `msg`, `event`, `env`, `version` |
| 4 | Run `pytest tests/unit/backend/core/test_logging.py -q` | All tests pass |

Note: FEAT-018 names a session-scoped capture fixture that enforces AC-LOG-01 over the whole integration suite; no such fixture exists in `tests/conftest.py` or `tests/integration/conftest.py`, so this manual capture is the check.

### TC-018-02 Timestamps are UTC and `env` / `version` come from `APP_ENV` / `GIT_SHA`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Inspect `ts` of any line in `backend.log` | Format `YYYY-MM-DDTHH:MM:SS.mmmZ` (ends with `Z`) and equals the UTC wall clock within a few seconds |
| 2 | Inspect `env` and `version` | `env` = `local`; `version` = the `GIT_SHA` value of the environment file |

### TC-018-03 Console format locally; `console` refused in staging

| Step | Action | Expected Result |
|---|---|---|
| 1 | Set `LOG_FORMAT=console`, restart the backend, call `GET /api/v1/residents` with no token | Log line of the form `2026-…Z INFO backend.access request_completed actor_type=anonymous … method=GET route=/api/v1/residents status=401` (one readable line, not JSON) |
| 2 | Start the backend with `APP_ENV=staging`, `LOG_FORMAT=console` and otherwise valid staging variables | Process exits with code 1; CRITICAL `startup_config_invalid` naming `LOG_FORMAT: console is refused in staging and production` |
| 3 | Restore `LOG_FORMAT=json` and restart | JSON lines again |

### TC-018-04 Valid `X-Request-ID` is echoed; invalid value replaced by a UUID4

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -i -H "X-Request-ID: abcd1234-test" http://localhost:8000/api/v1/health` | Response header `X-Request-ID: abcd1234-test` |
| 2 | `curl -i -H "X-Request-ID: bad id!" http://localhost:8000/api/v1/health` | `X-Request-ID` is a new UUID4 (matches `^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`), not `bad id!` |
| 3 | Send `X-Request-ID: short` (5 characters) and a 65-character value | Both replaced by a generated UUID4 |
| 4 | Send no header | Generated UUID4 returned |
| 5 | Find the `request_completed` line of step 1 | Its `request_id` field = `abcd1234-test` |

### TC-018-05 `X-Request-ID` is present on 200, 401, 404, 422, 429, 503 responses and CORS preflights

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/health` | 200 with `X-Request-ID` |
| 2 | `GET /api/v1/residents` without a token | 401 with `X-Request-ID`; Problem body `request_id` equals the header |
| 3 | `GET /api/v1/does-not-exist` | 404 `NOT_FOUND` with `X-Request-ID` |
| 4 | `POST /api/v1/auth/login` with body `{"email": "admin@example.com"}` | 422 `VALIDATION_ERROR` with `X-Request-ID` |
| 5 | Six `POST /api/v1/auth/login` calls with wrong credentials within 60 s from one machine | Sixth returns 429 `RATE_LIMITED` with `X-Request-ID` and `Retry-After` |
| 6 | `docker compose stop db`; `GET /api/v1/residents` with a valid token; then `docker compose start db` | 503 `SERVICE_UNAVAILABLE` with `X-Request-ID` |
| 7 | `curl -i -X OPTIONS -H "Origin: http://localhost:3000" -H "Access-Control-Request-Method: GET" http://localhost:8000/api/v1/residents` | Response carries `X-Request-ID` |
| 8 | 500 response: run `pytest -m integration tests/integration/api/test_http_middleware.py -q -k unhandled_exception` | Test passes (500 Problem carries `X-Request-ID`) |

### TC-018-06 One `request_completed` per request with the right level per status

| Step | Action | Expected Result |
|---|---|---|
| 1 | Send one request each with distinct `X-Request-ID` values `qa-log-200-01` (`GET /api/v1/residents` with token), `qa-log-401-01` (no token), `qa-log-404-01` (`GET /api/v1/does-not-exist`), `qa-log-422-01` (login body without `password`) | 200, 401, 404, 422 |
| 2 | `grep -c '"request_id": "qa-log-200-01"' backend.log` filtered on `"event": "request_completed"`; repeat per ID | Exactly 1 `request_completed` line per ID |
| 3 | Read the `level` of each line | 200 → `INFO`; 401 → `INFO`; 404 → `INFO`; 422 → `WARNING` |
| 4 | Read the `level` of the 429 line of TC-018-05 step 5 and the 503 line of step 6 | 429 → `WARNING`; 503 → `ERROR` |
| 5 | Run `pytest -m integration tests/integration/api/test_http_middleware.py -q -k one_access_record_per_request` | Test passes (also covers the 500 → `ERROR` case) |

### TC-018-07 `request_completed` carries the route template, method, status, duration and actor

| Step | Action | Expected Result |
|---|---|---|
| 1 | As the clinician, `GET /api/v1/residents/R09` with `X-Request-ID: qa-log-route-01` | 200 |
| 2 | Read its `request_completed` line | `route` = `/api/v1/residents/{resident_code}` (template, not the concrete path); `method` `GET`; `status` 200; numeric `duration_ms`; `actor_type` `user`; `actor_id` = the clinician's user UUID; no `Authorization` value, no query values, no body |
| 3 | Read the 401 line of TC-018-06 | `actor_type` `anonymous`; `actor_id` null |

### TC-018-08 Healthy health check is logged at DEBUG only

| Step | Action | Expected Result |
|---|---|---|
| 1 | With `LOG_LEVEL=INFO`, call `GET /api/v1/health` with `X-Request-ID: qa-log-health-01` | 200; no line with that request ID in `backend.log` |
| 2 | Set `LOG_LEVEL=DEBUG`, restart, repeat with `qa-log-health-02` | One `request_completed` line with `"level": "DEBUG"`, `route` `/api/v1/health`, `status` 200 |
| 3 | Restore `LOG_LEVEL=INFO` | Restarted |

### TC-018-09 Key-based redaction and URL / bearer masking

| Step | Action | Expected Result |
|---|---|---|
| 1 | In a REPL: `from backend.core.logging import configure_logging; import logging; configure_logging("INFO", "json", "local", "qa"); logging.getLogger("qa").info("probe", extra={"password": "x", "Authorization": "Bearer abc", "note": "text"})` | Printed JSON has `"password": "[REDACTED]"`, `"Authorization": "[REDACTED]"`, `"note": "[REDACTED]"` |
| 2 | `logging.getLogger("qa").info("connect to postgresql://u:secretpw@h/db")` | `msg` is `connect to postgresql://u:[REDACTED]@h/db`; the string `secretpw` does not appear |
| 3 | `logging.getLogger("qa").info("header Bearer abc.def.ghi")` | `msg` is `header Bearer [REDACTED]` |
| 4 | Log extras `{"api_key": "k", "DATABASE_URL": "x", "cookie": "c", "body": "b", "client_secret": "s", "dsn": "d"}` | Every value `[REDACTED]` (case-insensitive key match) |

### TC-018-10 Login and an authorised request leave no password, JWT or e-mail in the logs

| Step | Action | Expected Result |
|---|---|---|
| 1 | With the capture running, `POST /api/v1/auth/login` as `researcher@example.com` with `SEED_RESEARCHER_PASSWORD`; then `GET /api/v1/auth/me` with the returned token | 200 and 200 |
| 2 | `grep -cF "$SEED_RESEARCHER_PASSWORD" backend.log`; `grep -cF "<access_token value>" backend.log`; `grep -c "researcher@example.com" backend.log` | 0, 0, 0 |
| 3 | `grep -c "eyJ" backend.log` | 0 (no JWT fragment) |
| 4 | Run `pytest -m integration tests/integration/api/test_auth.py -q -k logs_hold_no_password_token_or_email` | Test passes (uses the AC-LOG-02 sample password) |

### TC-018-11 Forced exception produces exactly one ERROR `unhandled_exception` record

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `pytest -m integration tests/integration/api/test_http_middleware.py -q -k unhandled_exception` | Test passes |
| 2 | Alternatively in a REPL: create an app with `create_app(settings)`, add a temporary route that raises `RuntimeError("qa boom")`, call it through `fastapi.testclient.TestClient(app, raise_server_exceptions=False)` with `X-Request-ID: qa-log-500-01` while capturing stdout | 500 Problem `INTERNAL_ERROR`, detail `An unexpected error occurred.` |
| 3 | Inspect captured log lines | Exactly one `"event": "unhandled_exception"` line at `ERROR` with `exc_type` `RuntimeError`, a `stack` field and `request_id` `qa-log-500-01`; plus one `request_completed` line at `ERROR` with `status` 500 |

### TC-018-12 Request ID reaches `audit_logs.request_id`, including `pipeline.run.started`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/auth/login` as admin with `X-Request-ID: qa-log-audit-01` | 200 |
| 2 | `SELECT action FROM audit_logs WHERE request_id = 'qa-log-audit-01';` | One row `auth.login.succeeded` |
| 3 | As admin, `POST /api/v1/pipeline/run` with `X-Request-ID: qa-log-run-01` and body `{"scope": ["R01"]}` | 202 with `pipeline_run_id` |
| 4 | `SELECT action FROM audit_logs WHERE request_id = 'qa-log-run-01';` | Includes `pipeline.run.started` |
| 5 | In `backend.log`, find lines with `pipeline_run_id` equal to the returned id | They also carry `request_id` `qa-log-run-01` |

### TC-018-13 Ingest leaves no feature value, body or audio data in the logs

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/sessions` with `X-API-Key: $SEED_INGEST_API_KEY` and a synthetic R01/D01 record whose `loudness_dbfs` is `-27.13` and `session_id` `R01-20261031-01` | 201 or 422 depending on validation; any status is acceptable here |
| 2 | `grep -c -- "-27.13" backend.log` and `grep -ci "audio_base64\|loudness_dbfs\": -" backend.log` | 0 and 0 |
| 3 | `grep -c "ewk_" backend.log` | 0 |

### TC-018-14 `analytics/` configures no logging

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -rnE "basicConfig|dictConfig|addHandler|StreamHandler|FileHandler|import logging" analytics --include=*.py` | No handler configuration (no `basicConfig`, `dictConfig`, `addHandler` or handler class) |

### TC-018-15 `LOG_LEVEL=DEBUG` in staging warns `debug_logging_enabled`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Start the app with `APP_ENV=staging`, `LOG_LEVEL=DEBUG` and otherwise valid staging variables (in-process `create_app` in a REPL is sufficient) | Start-up proceeds; one WARNING line with `event`/`msg` `debug_logging_enabled` |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | Any request with `X-Request-ID: abcd1234-test` | Same value returned in `X-Request-ID` |
| 2 | Any request with `X-Request-ID: bad id!` | Generated UUID4 returned |
| 3 | Error responses (401, 404, 422, 429, 503) | Header `X-Request-ID` present and equal to the Problem `request_id` |
| 4 | CORS preflight from `http://localhost:3000` | `X-Request-ID` present; `Access-Control-Expose-Headers` includes `X-Request-ID` (FR-17, configured by FEAT-019) |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT request_id FROM audit_logs WHERE action = 'auth.login.succeeded' ORDER BY id DESC LIMIT 1;` after a login with `X-Request-ID: qa-log-audit-01` | `qa-log-audit-01` |
| 2 | `SELECT count(*) FROM audit_logs WHERE action = 'pipeline.run.started' AND request_id = 'qa-log-run-01';` | 1 |
| 3 | No table stores log lines (`SELECT count(*) FROM information_schema.tables WHERE table_name ILIKE '%log%' AND table_name <> 'audit_logs';`) | 0 (logs go to stdout only, LOG-120) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | `X-Request-ID: bad id!` | Replaced by a UUID4; request continues (TC-018-04) |
| 2 | `X-Request-ID` of 5 or 65 characters | Replaced by a UUID4 |
| 3 | `LOG_FORMAT=console` with `APP_ENV=staging` | Exit code 1 (TC-018-03) |
| 4 | Secret-looking keys and credentialed URLs in a log call | `[REDACTED]` / masked (TC-018-09) |
| 5 | Unhandled exception | One ERROR `unhandled_exception`; client sees only the generic 500 (TC-018-11) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-018-AC-01 | Every emitted line parses as JSON with `ts`, `level`, `logger`, `msg`, `event`, `env`, `version` | TC-018-01, TC-018-02 |
| FEAT-018-AC-02 | `abcd1234-test` echoed; `bad id!` replaced by a UUID4 | TC-018-04 |
| FEAT-018-AC-03 | 200, 401, 404, 422, 429 and 500 responses carry `X-Request-ID` | TC-018-05 |
| FEAT-018-AC-04 | Exactly one `request_completed` per request; 404 INFO, 422 WARNING, 500 ERROR; health 200 DEBUG | TC-018-06, TC-018-08 |
| FEAT-018-AC-05 | `password`, `Authorization`, `note` values `[REDACTED]`; `postgresql://u:secretpw@h/db` logged without `secretpw` | TC-018-09 |
| FEAT-018-AC-06 | Login plus authorised request: zero matches for the password, the JWT and the e-mail | TC-018-10 |
| FEAT-018-AC-07 | Forced exception: exactly one ERROR `unhandled_exception` with `exc_type`, `stack`, `request_id` | TC-018-11 |

## Test Data Requirements

- `test_v0_1` seed; seeded users and `SEED_*` passwords (never written down); ingest key `SEED_INGEST_API_KEY`.
- Synthetic request IDs prefixed `qa-log-`; probe values `abcd1234-test`, `bad id!`, `postgresql://u:secretpw@h/db` (dummy, from FEAT-018-AC-05).
- One synthetic R01/D01 record with `session_id` `R01-20261031-01` for TC-018-13 (study IDs only, no audio).
- Environment: `APP_ENV`, `LOG_FORMAT`, `LOG_LEVEL`, `GIT_SHA`.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-018-FR-01 / LOG-001 / NFR-100 / ENV-018 / AC-LOG-01 | FEAT-018 | TC-018-01, TC-018-02 |
| FEAT-018-FR-02 / LOG-002 / ENV-012 | FEAT-018 | TC-018-03 |
| FEAT-018-FR-03 / LOG-003 | FEAT-018 | TC-018-01, TC-018-06 |
| FEAT-018-FR-04 / LOG-004 | FEAT-018 | TC-018-07, TC-018-12 |
| FEAT-018-FR-05 / LOG-005 | FEAT-018 | TC-018-02 |
| FEAT-018-FR-06 / LOG-006 | FEAT-018 | TC-018-14 |
| FEAT-018-FR-07 / LOG-010 / API-107 | FEAT-018 | TC-018-06, TC-018-07 |
| FEAT-018-FR-08 / LOG-011 | FEAT-018 | TC-018-08 |
| FEAT-018-FR-09 / LOG-012 / ENV-012 | FEAT-018 | TC-018-15 |
| FEAT-018-FR-10 / LOG-020..LOG-022 / SEC-107 / ARC-095 / AC-LOG-02 | FEAT-018 | TC-018-10, TC-018-13 |
| FEAT-018-FR-11 / LOG-023 / LOG-024 | FEAT-018 | TC-018-09 |
| FEAT-018-FR-12 / LOG-025 | FEAT-018 | TC-018-13 |
| FEAT-018-FR-13 / LOG-030 / API-105 / AC-LOG-04 | FEAT-018 | TC-018-04 |
| FEAT-018-FR-14 / LOG-031 / FR-254 | FEAT-018 | TC-018-05 |
| FEAT-018-FR-15 / LOG-033 | FEAT-018 | TC-018-12 |
| FEAT-018-FR-16 / LOG-034 | FEAT-018 | TC-018-12 |
| FEAT-018-FR-17 / LOG-035 | FEAT-018 | API Validation 4 |
| FEAT-018-FR-18 / LOG-070 | FEAT-018 | TC-018-11 |
| FEAT-018-FR-19 / LOG-120 / LOG-122 | FEAT-018 | Database Validation 3 |
| FEAT-018-FR-20 / ARC-100 | FEAT-018 | TC-018-05, TC-018-12 |
