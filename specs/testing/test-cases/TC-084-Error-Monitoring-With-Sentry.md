# Error monitoring with Sentry

## Feature Description

FEAT-084 offers optional backend error monitoring through Sentry for the interim staging and production environments (TRD 17 LOG-070, LOG-100..LOG-102, LOG-111, LOG-023, LOG-024; TRD 22 TPS-060, TPS-061; TRD 12 SEC-127; TRD 21 §4.2, §4.7). `backend/core/monitoring.py` `init_sentry(settings)` is called by the web application's lifespan and by `backend.jobs.nightly_run` main, never at import time. With SENTRY_DSN non-empty and APP_ENV `staging` or `production`, `sentry-sdk` is initialised with `environment`=APP_ENV, `release`=GIT_SHA, `send_default_pii=False`, `traces_sample_rate=0`, `max_request_body_size="never"` and a `before_send` hook that re-applies the log redaction and drops request headers, cookies, query strings and bodies; every ERROR log record (`unhandled_exception`, `nightly_run_missing`, `pipeline_run_failed`) becomes an event. With SENTRY_DSN empty the SDK is not imported and no network call is made; in local and test a DSN is ignored. Sentry is backend-only (no browser SDK), SENTRY_DSN is a `SecretStr`, and before AWS go-live SENTRY_DSN stays empty in production unless the project coordinator and UND IT approve.

## Preconditions

- Repository clone; Python 3.12 with `pip install -r backend/requirements.txt -r backend/requirements-dev.txt`.
- Local Compose stack (`cp .env.development.example .env`, `SENTRY_DSN=` empty, `docker compose up -d`).
- A dummy DSN that points nowhere real, e.g. `https://public@example.invalid/1`; never a real project DSN in a command line or record.
- For **Hosted** cases: read-only access to the Render services' Logs and Environment pages of staging and production. No variable is changed.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-084-01 | Empty SENTRY_DSN: unhandled exception gives the ERROR log and zero transport calls | High | Negative |
| TC-084-02 | Test DSN with captured transport: event has environment, release, exception and no request data or secrets | High | Security |
| TC-084-03 | `grep -rn "@sentry" frontend/package.json` returns nothing | High | Security |
| TC-084-04 | `docs/deployment.md` states the go-live rule and the empty local/test values | High | Documentation |
| TC-084-05 | `init_sentry` options: no PII, no tracing, no request bodies | High | Positive |
| TC-084-06 | DSN ignored in APP_ENV `local` and `test` | Medium | Negative |
| TC-084-07 | `nightly_run_missing` ERROR is reported when enabled | Medium | Positive |
| TC-084-08 | Startup log names only `sentry_enabled`; DSN never logged; `SecretStr` masking | High | Security |
| TC-084-09 | `sentry-sdk` pinned with `==`; init not at import time (export-openapi offline) | Medium | Documentation |
| TC-084-10 | Hosted: Sentry configuration of staging and production (read-only) | Medium | Hosted |

### TC-084-01 Empty SENTRY_DSN: unhandled exception gives the ERROR log and zero transport calls

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -q tests/unit/backend/core/test_monitoring.py -k empty_dsn` | `test_empty_dsn_logs_error_and_never_calls_transport` passes: `init_sentry` returns `False`, the failing request returns 500, an `unhandled_exception` ERROR record exists, transport `send` call count `0`, Sentry client inactive. |
| 2 | Local stack with `SENTRY_DSN=` : `docker compose logs backend | grep sentry_configured` | One line with `sentry_enabled` false. |
| 3 | `docker compose exec -T backend python -c "import sys, backend.main; print('sentry_sdk' in sys.modules)"` | `False` (SDK not imported with an empty DSN). |

### TC-084-02 Test DSN with captured transport: event has environment, release, exception and no request data or secrets

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -q tests/unit/backend/core/test_monitoring.py -k "sanitised or before_send"` | `test_unhandled_exception_event_is_sanitised` and `test_before_send_drops_request_fields_and_redacts` pass. |
| 2 | Review the assertions of the first test. | Exactly 1 event; `environment` `production`; `release` = the GIT_SHA set in the test; `level` `error`; exception present; no `request.data`, `headers`, `cookies`, `query_string`. |
| 3 | Review the redaction assertions. | A field `password` and a URL `postgresql://u:p@h/db` appear as `[REDACTED]`; the secret test values never appear in the serialised event. |

### TC-084-03 `grep -rn "@sentry" frontend/package.json` returns nothing

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -rn "@sentry" frontend/package.json` | No output. |
| 2 | `grep -rn "sentry" frontend/app frontend/components frontend/lib frontend/package-lock.json | head` | No browser SDK reference. |
| 3 | `pytest -q tests/unit/backend/core/test_monitoring.py -k no_browser_sdk` | Pass. |

### TC-084-04 `docs/deployment.md` states the go-live rule and the empty local/test values

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read "## Error monitoring with Sentry (optional, FEAT-084)" in `docs/deployment.md`. | Bullet "Go-live rule (TPS-061, LOG-102): before AWS go-live, `SENTRY_DSN` is empty in production unless the project coordinator and UND IT approve Sentry for PHI-derived data …". |
| 2 | Read the SENTRY_DSN bullet. | "values per TRD 21 §4.7: **local empty, test empty**, staging optional, interim production optional (synthetic data only)". |
| 3 | `grep -n "^SENTRY_DSN" .env.development.example .env.example .env.production.example` | All three empty. |

### TC-084-05 `init_sentry` options: no PII, no tracing, no request bodies

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -q tests/unit/backend/core/test_monitoring.py -k init_options` | Pass: `dsn` the dummy DSN, `environment` `staging`, `release` GIT_SHA, `send_default_pii` False, `traces_sample_rate` 0, `max_request_body_size` `"never"`, `before_send` is `monitoring.before_send`, `default_integrations` False. |
| 2 | `grep -n "include_local_variables\|max_breadcrumbs" backend/core/monitoring.py` | `include_local_variables: False`, `max_breadcrumbs: 0`. |

### TC-084-06 DSN ignored in APP_ENV `local` and `test`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -q tests/unit/backend/core/test_monitoring.py -k ignored_outside` | Pass for `local` and `test`. |
| 2 | Local: set `SENTRY_DSN=https://public@example.invalid/1` in `.env`, `docker compose up -d --force-recreate backend`, then `docker compose logs backend | grep -E "sentry_dsn_ignored|sentry_configured"`. | WARNING `sentry_dsn_ignored` (reason "only staging and production") and `sentry_configured` with `sentry_enabled` false; the DSN text does not appear. |
| 3 | Restore `SENTRY_DSN=` and recreate the backend. | Back to TC-084-01 state. |

### TC-084-07 `nightly_run_missing` ERROR is reported when enabled

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -q tests/unit/backend/core/test_monitoring.py -k nightly_run_missing` | Pass: the `nightly_run_missing` ERROR record produces one event through the captured transport. |
| 2 | `grep -n "init_sentry" backend/jobs/nightly_run.py` | Called in the job's main before work starts. |

### TC-084-08 Startup log names only `sentry_enabled`; DSN never logged; `SecretStr` masking

| Step | Action | Expected Result |
|---|---|---|
| 1 | `set -a; . ./.env.development.example; set +a; SENTRY_DSN=https://public@example.invalid/1 python -c "from backend.core.config import get_settings; print(repr(get_settings().sentry_dsn))"` | `SecretStr('**********')`. |
| 2 | In the TC-084-06 logs search for `example.invalid`. | Not found. |
| 3 | `grep -n "sentry_dsn" backend/core/config.py` | Field typed `SecretStr`. |

### TC-084-09 `sentry-sdk` pinned with `==`; init not at import time (export-openapi offline)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -n "sentry" backend/requirements.txt` | `sentry-sdk==2.74.0`. |
| 2 | `grep -rn "init_sentry(" backend --include=*.py` | Only `backend/main.py` (lifespan) and `backend/jobs/nightly_run.py` (main), plus the definition. |
| 3 | `APP_ENV=test JWT_SECRET=$(openssl rand -hex 32) DATABASE_URL=postgresql+psycopg://x:x@localhost/x SENTRY_DSN=https://public@example.invalid/1 python -m backend.cli export-openapi > /tmp/o.json; echo $?` | `0`; no network call to Sentry (command works offline). |

### TC-084-10 Hosted: Sentry configuration of staging and production (read-only)

| Step | Action | Expected Result |
|---|---|---|
| 1 | Render → environment groups `echowell-staging-shared` and `echowell-production-shared` → Environment (read only). | SENTRY_DSN exists only in the groups, as a secret (value hidden); not on the web services directly. |
| 2 | Render → `echowell-backend-production` → Logs → search `sentry_configured`. | Line with `"sentry_enabled": false`, unless the approval recorded in checklist row C.12 exists; the DSN never appears. |
| 3 | Same search on staging `echowell-api` and the two cron jobs. | `sentry_configured` with a boolean only. |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | Request that raises an unhandled exception (unit test client, TC-084-01/02) | 500 with RFC 7807 body; same response whether Sentry is enabled or not |
| 2 | `GET http://localhost:8000/api/v1/health` with SENTRY_DSN empty | 200; no outbound call to Sentry |

## Database Validation

Not applicable: FEAT-084 writes no rows (Logging Requirements: no audit rows).

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Empty DSN with an unhandled exception (TC-084-01) | ERROR log, zero transport calls |
| 2 | DSN set in local/test (TC-084-06) | `sentry_dsn_ignored`, SDK not initialised |
| 3 | Event with password field and credentialed URL (TC-084-02) | Values `[REDACTED]`; request headers, cookies, query, body dropped |
| 4 | Look for a browser SDK (TC-084-03) | None |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-084-AC-01 | With SENTRY_DSN empty an unhandled exception produces the ERROR log and zero calls to the Sentry transport | TC-084-01 |
| FEAT-084-AC-02 | With a test DSN and captured transport the event has `environment`, `release` = GIT_SHA and the exception, and no request body, headers, cookies, query string, password or connection-URL credentials | TC-084-02 |
| FEAT-084-AC-03 | `grep -rn "@sentry" frontend/package.json` returns nothing | TC-084-03 |
| FEAT-084-AC-04 | `docs/deployment.md` states SENTRY_DSN is empty in production before AWS go-live unless approved, and the TRD 21 §4.7 local and test values are empty | TC-084-04 |

## Test Data Requirements

- Dummy DSN `https://public@example.invalid/1`; captured transport of the unit tests.
- Variables: SENTRY_DSN, APP_ENV, GIT_SHA (from `RENDER_GIT_COMMIT` on Render), JWT_SECRET (generated per command), DATABASE_URL (dummy for `export-openapi`).
- No resident data.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-084-FR-01 / LOG-100, SEC-127 | FEAT-084 | TC-084-02, TC-084-05 |
| FEAT-084-FR-02 / LOG-101 | FEAT-084 | TC-084-01, TC-084-09 |
| FEAT-084-FR-03 / LOG-102, TPS-060, TRD 21 §4.7 | FEAT-084 | TC-084-06, TC-084-10 |
| FEAT-084-FR-04 / TPS-060, LOG-082 | FEAT-084 | TC-084-03 |
| FEAT-084-FR-05 / LOG-070 | FEAT-084 | TC-084-01, TC-084-02 |
| FEAT-084-FR-06 / LOG-111 | FEAT-084 | TC-084-07 |
| FEAT-084-FR-07 / TPS-061, SEC-127, LOG-102 | FEAT-084 | TC-084-04, TC-084-10 |
| FEAT-084-FR-08 / TRD 21 §4.2, SEC-050 | FEAT-084 | TC-084-08, TC-084-10 |
