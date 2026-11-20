# FEAT-003 Backend application factory, settings, startup guards and health

## Feature Description

FEAT-003 builds the single FastAPI application `backend.main:create_app()` with every router under `/api/v1`, the one `Settings` class of `backend/core/config.py` (cached `get_settings()`), the startup guards of TRD 21 (ENV-002..ENV-015, ENV-053, ENV-054) that exit with code 1 after one CRITICAL `startup_config_invalid` record naming the variables (never their values), the shared dependencies `get_db()` and `get_pagination()`, and E-01 `GET /api/v1/health` (200 `ok` / 503 `degraded`, no authentication, no rate limit, no audit row).

## Preconditions

- Local development stack (README quick start): Python 3.12 venv with `backend/requirements.txt` and `backend/requirements-dev.txt` installed, commands run from the repository root.
- Local Docker Compose stack running and seeded for the API cases: `cp .env.development.example .env && docker compose up --build -d`, then `docker compose exec backend python -m backend.cli seed test_v0_1`.
- A Bearer token for the API cases: `POST /api/v1/auth/login` with `{"email":"clinician@example.com","password":"<SEED_CLINICIAN_PASSWORD from .env>"}`; keep `access_token` as `$TOKEN`.
- Guard cases use a clean environment so `.env` and shell variables do not interfere. Define the base (synthetic, non-secret values; the JWT value is generated per run and never written down):
  - `BASE="env -i PATH=$PATH HOME=$HOME LOG_FORMAT=json FACILITY_NAME=Demo Facility CORS_ORIGINS=https://staging.example.org PIPELINE_PROFILE=production DATABASE_URL=postgresql://u:p@h/db?sslmode=require JWT_SECRET=$(openssl rand -hex 32)"`
  - `START='python -c "from backend.main import create_app; create_app()"'`
  - Run as `eval "$BASE APP_ENV=<env> <overrides> $START"; echo "exit=$?"`. Settings validation runs before any database connection, so `h` need not resolve.
- psql read access to the Compose database (`docker compose exec db psql -U echowell -d echowell`) for TC-003-12.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-003-01 | Production with `PIPELINE_PROFILE=test_v0_1` exits 1 with a CRITICAL log naming `PIPELINE_PROFILE` | High | Negative |
| TC-003-02 | Production with `PIPELINE_AS_OF` set exits non-zero with a logged error | High | Negative |
| TC-003-03 | Staging without `sslmode=require` exits 1; local with the same URL starts | High | Negative |
| TC-003-04 | 31-byte `JWT_SECRET` rejected in every `APP_ENV`; old facility name rejected | High | Negative |
| TC-003-05 | `postgres://` URL normalised to `postgresql+psycopg://` with query preserved | High | Positive |
| TC-003-06 | `repr(get_settings())` masks secrets; failure log contains no secret value | High | Security |
| TC-003-07 | Other production and staging guards (CORS, console logs, rate limit, unknown `ECHOWELL_*`) | Medium | Negative |
| TC-003-08 | Valid staging configuration with `LOG_LEVEL=DEBUG` starts and logs `debug_logging_enabled` | Low | Positive |
| TC-003-09 | Health returns 200 `ok` with the database up | High | API |
| TC-003-10 | Health returns 503 `degraded` with the database stopped | High | API |
| TC-003-11 | Health needs no `Authorization` header and is not rate limited | High | Security |
| TC-003-12 | Health writes no `audit_logs` row | High | Database |
| TC-003-13 | Pagination bounds: `limit=0`, `limit=501`, `offset=-1` rejected with 422; defaults 50 and 0 | High | API |
| TC-003-14 | No route exists outside `/api/v1` | Medium | API |
| TC-003-15 | `get_db` commit/rollback/close and settings unit suite pass | Medium | Positive |

### TC-003-01 Production with `PIPELINE_PROFILE=test_v0_1` exits 1 with a CRITICAL log naming `PIPELINE_PROFILE`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `eval "$BASE APP_ENV=production DATABASE_READONLY_URL=postgresql://r:p@h/db?sslmode=require PIPELINE_PROFILE=test_v0_1 $START"; echo "exit=$?"`. | The process stops before serving; stderr has one CRITICAL record starting `startup_config_invalid:` that contains `PIPELINE_PROFILE: test_v0_1 is refused when APP_ENV=production`; last line `exit=1`. |
| 2 | Repeat with `PIPELINE_PROFILE=production` (no other change). | No `startup_config_invalid` record; `exit=0`. |
| 3 | Run `pytest -q tests/unit/backend/core/test_config.py -k cfg_06`. | `test_cfg_06_production_refuses_test_profile` and `test_cfg_06_process_exits_1_with_critical_log` pass. |

### TC-003-02 Production with `PIPELINE_AS_OF` set exits non-zero with a logged error

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `eval "$BASE APP_ENV=production PIPELINE_AS_OF=2026-10-30T15:00:00-05:00 $START"; echo "exit=$?"`. | CRITICAL `startup_config_invalid:` record containing `PIPELINE_AS_OF: must be empty when APP_ENV=production`; `exit=1`. |
| 2 | Run `pytest -q tests/unit/backend/core/test_config.py::test_tst_038_production_refuses_pipeline_as_of`. | `1 passed`. |

### TC-003-03 Staging without `sslmode=require` exits 1; local with the same URL starts

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `eval "$BASE APP_ENV=staging DATABASE_URL=postgresql://u:p@h/db $START"; echo "exit=$?"`. | CRITICAL record containing `DATABASE_URL: must specify sslmode=require or verify-full`; `exit=1`. |
| 2 | Repeat step 1 with `DATABASE_URL=postgresql://u:p@h/db?sslmode=disable`. | Same message; `exit=1`. |
| 3 | Repeat step 1 with `DATABASE_URL=postgresql://u:p@h/db?sslmode=verify-full`. | No `DATABASE_URL` problem; `exit=0`. |
| 4 | Run `eval "$BASE APP_ENV=local CORS_ORIGINS=http://localhost:3000 DATABASE_URL=postgresql://u:p@h/db $START"; echo "exit=$?"`. | No `startup_config_invalid` record; `exit=0`. |
| 5 | Repeat step 1 with `DATABASE_MIGRATION_URL=postgresql://m:p@h/db` added and `DATABASE_URL` carrying `?sslmode=require`. | CRITICAL record names `DATABASE_MIGRATION_URL: must specify sslmode=require or verify-full`; `exit=1`. |

### TC-003-04 31-byte `JWT_SECRET` rejected in every `APP_ENV`; old facility name rejected

| Step | Action | Expected Result |
|---|---|---|
| 1 | For each of `local`, `test`, `staging`, `production` run `eval "$BASE APP_ENV=<env> JWT_SECRET=$(openssl rand -hex 16 \| cut -c1-31) $START"; echo "exit=$?"`. | Every run logs `startup_config_invalid:` containing `JWT_SECRET` and `must be at least 32 bytes (ENV-013)`; every run ends `exit=1`. |
| 2 | Run once with a 32-byte value (`openssl rand -hex 16`) and `APP_ENV=local`, `CORS_ORIGINS=http://localhost:3000`. | No `JWT_SECRET` problem; `exit=0`. |
| 3 | Run `pytest -q tests/unit/backend/core/test_config.py::test_forbidden_facility_name_rejected` (it sets `FACILITY_NAME` to the old facility name of AGT-019, in upper case with a suffix, and with spaces). | `1 passed`: each value raises a validation error on `facility_name` ("must not contain the forbidden facility name (ENV-015)"). |
| 4 | Run `eval "$BASE APP_ENV=local FACILITY_NAME=Demo Facility CORS_ORIGINS=http://localhost:3000 $START"; echo "exit=$?"`. | `exit=0` (the current facility name is accepted). |

### TC-003-05 `postgres://` URL normalised to `postgresql+psycopg://` with query preserved

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `eval "$BASE APP_ENV=local CORS_ORIGINS=http://localhost:3000 DATABASE_URL='postgres://u:p@h/db?sslmode=require' python -c \"from backend.core.config import get_settings; print(get_settings().database_url.get_secret_value())\""`. | Prints exactly `postgresql+psycopg://u:p@h/db?sslmode=require`. |
| 2 | Repeat with `DATABASE_URL='postgresql://u:p@h/db?sslmode=require&application_name=qa'`. | Prints `postgresql+psycopg://u:p@h/db?sslmode=require&application_name=qa` (all query parameters kept). |
| 3 | Run `pytest -q tests/unit/backend/core/test_config.py::test_database_url_normalised_with_query_preserved`. | `1 passed`. |

### TC-003-06 `repr(get_settings())` masks secrets; failure log contains no secret value

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `eval "$BASE APP_ENV=local CORS_ORIGINS=http://localhost:3000 DATABASE_MIGRATION_URL=postgresql://m:p@h/db DATABASE_READONLY_URL=postgresql://r:p@h/db SENTRY_DSN=https://k@o0.ingest.example.org/0 python -c \"from backend.core.config import get_settings; print(repr(get_settings()))\""`. | Output shows `**********` for `database_url`, `database_migration_url`, `database_readonly_url`, `jwt_secret` and `sentry_dsn`; the strings `u:p@h`, `m:p@h`, `r:p@h`, `o0.ingest` and the generated JWT value do not appear. |
| 2 | Run TC-003-03 step 1 again and capture stderr (`2> /tmp/qa_guard.log`); then `grep -c "u:p@h" /tmp/qa_guard.log`; separately export a JWT with `JWT=$(openssl rand -hex 32)`, run step 1 of TC-003-04 style with `APP_ENV=staging DATABASE_URL=postgresql://u:p@h/db JWT_SECRET=$JWT` and run `grep -c "$JWT" /tmp/qa_guard.log`. | The log names `DATABASE_URL` and the rule only; both counts are `0` (no URL, password or JWT value). |
| 3 | Run `pytest -q tests/unit/backend/core/test_config.py::test_secrets_masked_in_repr`. | `1 passed`. |

### TC-003-07 Other production and staging guards (CORS, console logs, rate limit, unknown `ECHOWELL_*`)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP_ENV=production` with `CORS_ORIGIN_REGEX='^https://.*\.example\.org$'`. | CRITICAL record contains `CORS_ORIGIN_REGEX: must be empty when APP_ENV=production`; `exit=1`. |
| 2 | `APP_ENV=production` with `CORS_ORIGINS=http://staging.example.org`. | Record contains `CORS_ORIGINS: http:// is allowed only for localhost in local/test`; `exit=1`. |
| 3 | `APP_ENV=staging` with `LOG_FORMAT=console`. | Record contains `LOG_FORMAT: console is refused in staging and production`; `exit=1`. |
| 4 | `APP_ENV=staging` with `RATE_LIMIT_LOGIN=60/minute`. | Record contains `RATE_LIMIT_LOGIN: must be 5/minute in staging and production`; `exit=1`. |
| 5 | `APP_ENV=local`, `CORS_ORIGINS=http://localhost:3000`, plus `ECHOWELL_APP_DB_PASSWRD=x` (typo). | Record contains `ECHOWELL_APP_DB_PASSWRD: unknown ECHOWELL_ variable`; `exit=1`. |
| 6 | `APP_ENV=local`, `CORS_ORIGINS=http://localhost:3000`, plus `OTHER_UNKNOWN_VAR=x` (no `ECHOWELL_` prefix). | No problem reported for `OTHER_UNKNOWN_VAR`; `exit=0` (non-`ECHOWELL_` unknowns ignored, ENV-003). |
| 7 | Run `pytest -q tests/unit/backend/core/test_config.py -k "cors or console or rate_limit or echowell or dotenv or operator"`. | All selected tests pass, including `test_dotenv_ignored_in_staging` (ENV-006) and `test_operator_commands_need_only_their_subset` (ENV-053). |

### TC-003-08 Valid staging configuration with `LOG_LEVEL=DEBUG` starts and logs `debug_logging_enabled`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `eval "$BASE APP_ENV=staging LOG_LEVEL=DEBUG python -c \"from backend.core.config import load_settings_or_exit; load_settings_or_exit()\""; echo "exit=$?"`. | One WARNING record `debug_logging_enabled`; no `startup_config_invalid`; `exit=0`. |
| 2 | Repeat with `LOG_LEVEL=INFO`. | No `debug_logging_enabled` record; `exit=0`. |

### TC-003-09 Health returns 200 `ok` with the database up

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `curl -s -i http://localhost:8000/api/v1/health`. | Status `HTTP/1.1 200 OK`; `content-type: application/json`. |
| 2 | Read the JSON body. | Exactly the keys `status`, `database`, `version`, `time`; `"status":"ok"`, `"database":"ok"`, `"version"` equal to the `GIT_SHA` value of `.env` (`unknown` with the development template); `time` is an ISO 8601 UTC instant within 5 s of the tester's clock. |
| 3 | Open `http://localhost:8000/api/v1/docs` and expand `GET /api/v1/health` (`getHealth`). | Responses 200 and 503 both use schema `Health`; no security requirement is shown. |

### TC-003-10 Health returns 503 `degraded` with the database stopped

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `docker compose stop db`, wait 5 s, then `curl -s -i http://localhost:8000/api/v1/health`. | Status `503 Service Unavailable` returned within about 2–3 s; `content-type: application/json` (not `application/problem+json`). |
| 2 | Read the body. | `{"status":"degraded","database":"unavailable","version":"<GIT_SHA>","time":"<UTC now>"}`; no other key; no host name, URL, driver error or stack trace. |
| 3 | Run `docker compose ps backend`. | The backend container is still running (the process does not exit). |
| 4 | Run `docker compose start db`, wait until healthy, repeat step 1. | 200 with `"database":"ok"` again. |
| 5 | Run `pytest -q tests/integration/api/test_health.py`. | `test_tst_054_health_ok_with_database_up` and `test_tst_054_health_degraded_with_database_down` pass. |

### TC-003-11 Health needs no `Authorization` header and is not rate limited

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/health` (no header). | `200`. |
| 2 | Run `curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer invalid" http://localhost:8000/api/v1/health`. | `200` (the header is ignored, not rejected). |
| 3 | Run `for i in $(seq 1 30); do curl -s -o /dev/null -w "%{http_code} " http://localhost:8000/api/v1/health; done; echo`. | Thirty `200` codes; no `429`. |
| 4 | Compare with a protected endpoint without token: `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/alerts`. | `401` (shows that health is the exception). |

### TC-003-12 Health writes no `audit_logs` row

| Step | Action | Expected Result |
|---|---|---|
| 1 | In psql run `SELECT count(*), max(id) FROM audit_logs;` and note both values. | Values noted (N, M). |
| 2 | Call `GET /api/v1/health` 5 times (TC-003-11 step 1). | Five `200`. |
| 3 | Re-run `SELECT count(*), max(id) FROM audit_logs;`. | Still N and M. |
| 4 | Run `SELECT count(*) FROM audit_logs WHERE action LIKE '%health%';`. | `0`. |

### TC-003-13 Pagination bounds: `limit=0`, `limit=501`, `offset=-1` rejected with 422; defaults 50 and 0

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s -i -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/alerts?limit=0"`. | `422`; `content-type: application/problem+json`; body `type` = `urn:echowell:error:INVALID_QUERY_PARAMETER`, `title` = `Invalid query parameter`, `status` = 422, `detail` = `limit must be between 1 and 500`, non-empty `request_id`. |
| 2 | Same with `?limit=501`. | `422`, same `type`, `detail` = `limit must be between 1 and 500`. |
| 3 | Same with `?offset=-1`. | `422`, same `type`, `detail` = `offset must be 0 or greater`. |
| 4 | Same with `?limit=abc`. | `422`, `type` = `urn:echowell:error:INVALID_QUERY_PARAMETER`, `detail` = `A query parameter is not valid.` |
| 5 | Same with no `limit`/`offset`. | `200`; body has `"limit":50` and `"offset":0`. |
| 6 | Same with `?limit=500&offset=0` and `?limit=1`. | `200`; `"limit":500` and `"limit":1` respectively. |
| 7 | Run `pytest -q tests/unit/backend/test_deps.py::test_pagination_defaults_and_bounds`. | `1 passed`. |

### TC-003-14 No route exists outside `/api/v1`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s -i http://localhost:8000/health`. | `404`; `content-type: application/problem+json`; `type` = `urn:echowell:error:NOT_FOUND`. |
| 2 | `curl -s http://localhost:8000/api/v1/openapi.json \| python -c "import json,sys; d=json.load(sys.stdin); print(d['servers'][0]['url'], len(d['paths']))"`. | Prints `/api/v1 29`: the single server base is `/api/v1` and every documented path (TRD 19 convention: relative to that server) lives under it. |
| 3 | Run `pytest -q tests/integration/api/test_health.py::test_routes_only_under_api_v1`. | `1 passed`. |

### TC-003-15 `get_db` commit/rollback/close and settings unit suite pass

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `pytest -q tests/unit/backend/test_deps.py`. | `test_get_db_commits_on_success_and_closes` and `test_get_db_rolls_back_on_exception_and_closes` pass (API-011). |
| 2 | Run `pytest -q tests/unit/backend/core/test_config.py`. | All tests pass; 0 failed. |
| 3 | Run `grep -rn "os.environ" backend --include=*.py \| grep -v "backend/core/config.py"`. | No settings read outside `backend/core/config.py` (any match is limited to operator refusals documented in `config.environment_value`, which lives in that file). |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/health`, database up, no auth | 200, `Health` `{"status":"ok","database":"ok","version":GIT_SHA,"time":...}` |
| 2 | `GET /api/v1/health`, database stopped | 503, `Health` `{"status":"degraded","database":"unavailable",...}`, `application/json` |
| 3 | Verify response schema against `docs/api_reference/openapi.json` (`getHealth`) | Body matches `Health`; 503 is not a Problem document |
| 4 | `GET /api/v1/alerts?limit=0` / `limit=501` / `offset=-1` with Bearer token | 422 `INVALID_QUERY_PARAMETER` Problem |
| 5 | `GET /api/v1/alerts` without `limit`/`offset` | 200, `limit` 50, `offset` 0 |
| 6 | `GET /health` (outside prefix) | 404 `NOT_FOUND` Problem |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT count(*), max(id) FROM audit_logs;` before and after 5 health calls | Unchanged (API-112) |
| 2 | Health executes `SELECT 1` only | No row created or changed in any table (compare `SELECT sum(n_tup_ins+n_tup_upd+n_tup_del) FROM pg_stat_user_tables;` before and after: unchanged) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Production + `PIPELINE_PROFILE=test_v0_1` (TC-003-01) | Exit 1, CRITICAL `startup_config_invalid` naming `PIPELINE_PROFILE` |
| 2 | Production + `PIPELINE_AS_OF` set (TC-003-02) | Exit 1, names `PIPELINE_AS_OF` |
| 3 | Staging + URL without `sslmode` (TC-003-03) | Exit 1, names `DATABASE_URL` |
| 4 | 31-byte `JWT_SECRET`; old facility name (TC-003-04) | Exit 1 / validation error |
| 5 | Unknown `ECHOWELL_` variable (TC-003-07) | Exit 1 |
| 6 | Database stopped (TC-003-10) | Health 503 `degraded`, process keeps running |
| 7 | Bad pagination values (TC-003-13) | 422 `INVALID_QUERY_PARAMETER` |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-003-AC-01 | Production + `PIPELINE_PROFILE=test_v0_1` exits 1 with a CRITICAL log naming `PIPELINE_PROFILE`. | TC-003-01 |
| FEAT-003-AC-02 | Production + `PIPELINE_AS_OF` set exits non-zero with a logged error. | TC-003-02 |
| FEAT-003-AC-03 | Staging + URL lacking `sslmode=require` exits 1; the same URL with `APP_ENV=local` starts. | TC-003-03 |
| FEAT-003-AC-04 | 31-byte `JWT_SECRET` rejected in every `APP_ENV`; the old facility name of AGT-019 rejected. | TC-003-04 |
| FEAT-003-AC-05 | `postgres://u:p@h/db?sslmode=require` yields `postgresql+psycopg://u:p@h/db?sslmode=require`. | TC-003-05 |
| FEAT-003-AC-06 | `repr(get_settings())` shows `**********` for the five secret URLs/keys; failure log has no secret value. | TC-003-06 |
| FEAT-003-AC-07 | Health 200 `ok`/`ok`/`GIT_SHA` with database up; 503 `degraded`/`unavailable` with database stopped. | TC-003-09, TC-003-10 |
| FEAT-003-AC-08 | Health succeeds without `Authorization` and creates no `audit_logs` row. | TC-003-11, TC-003-12 |
| FEAT-003-AC-09 | `limit=0`, `limit=501`, `offset=-1` → 422 `INVALID_QUERY_PARAMETER`; defaults 50 and 0. | TC-003-13 |

## Test Data Requirements

- `test_v0_1` seed (R01–R10) in the Compose database for the authenticated pagination calls; seeded user `clinician@example.com` with `SEED_CLINICIAN_PASSWORD` from `.env`.
- Synthetic URLs `postgresql://u:p@h/db…` (no real host or password) for guard cases; `JWT_SECRET` generated per run with `openssl rand -hex 32` and never recorded.
- `GIT_SHA` from `.env` (`unknown` in `.env.development.example`).
- No audio, no real facility or resident data.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-003-FR-01 (API-001, API-002) | FEAT-003 | TC-003-14 |
| FEAT-003-FR-02, FR-03, FR-04 (API-003..API-008) | FEAT-003 | TC-003-15 (structure enforced by `lint-imports`, see TC-002-03) |
| FEAT-003-FR-05 (ENV-001, API-010) | FEAT-003 | TC-003-15 |
| FEAT-003-FR-06 (ENV-002, LOG-072) | FEAT-003 | TC-003-01, TC-003-06 |
| FEAT-003-FR-07 (ENV-003) | FEAT-003 | TC-003-07 |
| FEAT-003-FR-08 (ENV-004, AC-ENV-09) | FEAT-003 | TC-003-06 |
| FEAT-003-FR-09 (ENV-006) | FEAT-003 | TC-003-07 |
| FEAT-003-FR-10 (ENV-010, API-058, ARC-056, AGT-015, FR-230) | FEAT-003 | TC-003-01 |
| FEAT-003-FR-11 (ENV-011, API-059, ARC-057) | FEAT-003 | TC-003-03 |
| FEAT-003-FR-12 (ENV-012, D-50, D-103) | FEAT-003 | TC-003-02, TC-003-07, TC-003-08 |
| FEAT-003-FR-13 (ENV-013) | FEAT-003 | TC-003-04 |
| FEAT-003-FR-14 (ENV-014, AC-ENV-05) | FEAT-003 | TC-003-05 |
| FEAT-003-FR-15 (ENV-015, AC-ENV-07) | FEAT-003 | TC-003-04 |
| FEAT-003-FR-16 (ENV-054) | FEAT-003 | TC-003-07 |
| FEAT-003-FR-17 (ENV-053) | FEAT-003 | TC-003-07 |
| FEAT-003-FR-18 (API-011) | FEAT-003 | TC-003-15 |
| FEAT-003-FR-19 (API-016) | FEAT-003 | TC-003-13 |
| FEAT-003-FR-20 (API-017) | FEAT-003 | TC-003-10 (step 5 uses the `get_db` override) |
| FEAT-003-FR-21 (API-110, LOG-071, FR-253, ENV-018) | FEAT-003 | TC-003-09 |
| FEAT-003-FR-22 (API-111) | FEAT-003 | TC-003-10 |
| FEAT-003-FR-23 (API-112) | FEAT-003 | TC-003-11, TC-003-12 |
| CFG-06, AC-ENV-01, AC-AGT-05 | FEAT-003 | TC-003-01 |
| TST-038, AC-ENV-06 | FEAT-003 | TC-003-02 |
| AC-ENV-02, AC-ARC-09 | FEAT-003 | TC-003-03 |
| AC-ENV-03, AC-ENV-04 | FEAT-003 | TC-003-06, TC-003-04 |
| TST-054 | FEAT-003 | TC-003-09, TC-003-10 |
