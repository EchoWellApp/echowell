# FEAT-003 Backend application factory, settings, startup guards and health endpoint

| Field | Value |
|---|---|
| Epic | Infrastructure |
| Build phase | Phase 3 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-002 |
| Status | Complete |

## Purpose

Give the backend its single entry point and configuration backbone: `backend.main:create_app()`, one validated `Settings` class, the startup guards that make it impossible to run the `test_v0_1` profile or a fixed as-of in production or to connect to the database without TLS in staging and production, the shared request dependencies (`get_settings()`, `get_db()`, `get_pagination()`), and the unauthenticated `GET /api/v1/health` endpoint used by platforms, smoke tests and the local stack.

## Business Context

- BR-09 and D-01: production uses baseline_n 30; the `test_v0_1` profile (baseline_n 16) must never be selectable in production (FR-230, AGT-015).
- BR-16: database traffic encrypted in transit in staging and production (ARC-006, ARC-057); secrets masked (ENV-004).
- BR-17: FastAPI application served under `/api/v1`, health endpoint for platform checks (FR-253, ARC-083).

## Referenced TRDs

- TRD 05 API-001..API-008 (application structure and layering), API-010, API-011, API-016, API-017 (dependencies), API-058, API-059 (startup refusal), API-110..API-112 (health).
- TRD 21 ENV-001..ENV-006 (settings mechanics), ENV-010..ENV-018 (validation rules), ENV-053 (operator command variable subset), ENV-054 (login rate-limit guard); §4.2 and §4.3 variable tables; AC-ENV-01..AC-ENV-09.
- TRD 01 ARC-056, ARC-057, ARC-083.
- TRD 17 LOG-071, LOG-072.
- TRD 19 §4.3 E-01 (`Health` schema).
- TRD 02 FR-230, FR-253.
- TRD 25 AGT-015, AC-AGT-05, §4.6 Phase 3.
- TRD 24 D-01, D-50.

## Scope

- `backend/core/config.py`: `Settings` (pydantic-settings 2.x `BaseSettings`) with every backend variable of TRD 21 §4.2 and §4.3, their defaults and validation rules, and the cached `get_settings()`.
- Startup validation executed before the app accepts traffic: exit code 1 and one CRITICAL `startup_config_invalid` record naming invalid variables and the rule, never their values.
- Guards: `APP_ENV=production` refuses `PIPELINE_PROFILE=test_v0_1`, non-empty `PIPELINE_AS_OF`, non-empty `CORS_ORIGIN_REGEX` and `http://` CORS origins; `APP_ENV` in {staging, production} refuses `LOG_FORMAT=console` (D-103), database URLs without `sslmode=require`/`verify-full` and `RATE_LIMIT_LOGIN` other than `5/minute`; `JWT_SECRET` < 32 bytes refused everywhere; `FACILITY_NAME` containing `Edge4Care` refused; `DATABASE_URL` scheme normalised to `postgresql+psycopg://`.
- The guard function is reusable by `backend/jobs/nightly_run.py` and by `backend/cli.py` (operator commands validate only the ENV-053 subset).
- `backend/main.py`: `create_app()` mounting routers under `/api/v1`, served by uvicorn with `--proxy-headers --forwarded-allow-ips="*"` in the deployed start commands (API-001; TRD 15 DEP-022, DEP-040).
- `backend/api/deps.py`: `get_db()` (per-request session, commit/rollback/close), `get_pagination()` (limit 1..500 default 50, offset ≥ 0 default 0), override-friendly for tests.
- `backend/api/health.py` (existing skeleton file): `GET /api/v1/health`, whose handler calls the one service function `backend/services/health_service.py` `get_health()` (API-003; TRD 05 §4.1, §4.12).

## Out of Scope

- Authentication dependencies `get_current_user`, `get_api_key`, `get_ingest_principal` and `require_roles` (FEAT-020, FEAT-021).
- Request-ID middleware and structured logging configuration (FEAT-018); this feature emits the CRITICAL startup record through the standard `logging` module, which FEAT-018 later formats as JSON.
- Problem-details error handler, CORS middleware, security headers and body limits (FEAT-019); the 422 `INVALID_QUERY_PARAMETER` code raised by `get_pagination()` is rendered by FEAT-019's handler.
- Rate limiting (FEAT-022); only the `RATE_LIMIT_LOGIN` startup guard is here.
- Engine pool tuning and advisory locks (FEAT-013); the `meta` block and as-of from the latest succeeded run (FEAT-019, FEAT-024).
- The nightly job body (FEAT-054).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-003-FR-01 | `backend.main:create_app()` shall build the single FastAPI 0.115.x application; all routers shall be mounted under `/api/v1` and no route shall exist outside it. | API-001, API-002 |
| FEAT-003-FR-02 | The layering rules shall hold from the first router: routers call one service and return DTOs, services do not import `fastapi` and raise `AppError` subclasses from `backend/core/errors.py`, only repositories build queries, analytics computation only via `analytics.pipeline`. | API-003..API-006 |
| FEAT-003-FR-03 | Route handlers shall be declared with `def` (synchronous SQLAlchemy 2.0 with `postgresql+psycopg://`), except health and middleware which may be `async`. | API-007 |
| FEAT-003-FR-04 | Existing skeleton files `backend/api/{alarms,analytics,health,residents,sessions}.py` and `backend/services/{baseline,cusum,ingestion,morning_adjustment,scoring,speaker_screen,validation}.py` shall be kept and filled. | API-008 |
| FEAT-003-FR-05 | All backend configuration shall be read through one `Settings` class in `backend/core/config.py`, exposed by a cached `get_settings()`; no other module reads `os.environ`. | ENV-001, API-010 |
| FEAT-003-FR-06 | Settings validation shall run before traffic is accepted; any failure exits with code 1 and logs one CRITICAL `startup_config_invalid` record listing the variable names and the rule violated, never the values. | ENV-002, LOG-072 |
| FEAT-003-FR-07 | Unknown variables beginning with `ECHOWELL_` shall be rejected; other unknown variables ignored. | ENV-003 |
| FEAT-003-FR-08 | Secret variables (`DATABASE_URL`, `DATABASE_MIGRATION_URL`, `DATABASE_READONLY_URL`, `JWT_SECRET`, `SENTRY_DSN`, the `SEED_*` values) shall be typed `SecretStr`. | ENV-004, AC-ENV-09 |
| FEAT-003-FR-09 | A `.env` file shall be loaded only when `APP_ENV` is `local` or `test`. | ENV-006 |
| FEAT-003-FR-10 | With `APP_ENV=production`, startup shall fail if `PIPELINE_PROFILE=test_v0_1`; the same guard shall be callable by `backend/jobs/nightly_run.py`. | ENV-010, API-058, ARC-056, AGT-015, FR-230, D-01 |
| FEAT-003-FR-11 | With `APP_ENV` `staging` or `production`, startup shall fail if `DATABASE_URL`, `DATABASE_MIGRATION_URL` or `DATABASE_READONLY_URL` (when set) lacks `sslmode=require` or `sslmode=verify-full`. | ENV-011, API-059, ARC-057 |
| FEAT-003-FR-12 | With `APP_ENV=production`, startup shall fail if `PIPELINE_AS_OF` or `CORS_ORIGIN_REGEX` is non-empty or any CORS origin uses `http://`; with `APP_ENV` `staging` or `production`, startup shall fail if `LOG_FORMAT` is `console` (D-103); `LOG_LEVEL=DEBUG` in staging or production logs WARNING `debug_logging_enabled` at startup. | ENV-012, D-50, D-103 |
| FEAT-003-FR-13 | `JWT_SECRET` shorter than 32 bytes shall be rejected in every environment; in staging and production it shall also be rejected if it equals a value in a committed template or has fewer than 16 distinct characters. | ENV-013, TRD 21 §4.2 |
| FEAT-003-FR-14 | `DATABASE_URL` values starting `postgres://` or `postgresql://` shall be normalised to `postgresql+psycopg://` with all query parameters preserved. | ENV-014, AC-ENV-05 |
| FEAT-003-FR-15 | `FACILITY_NAME` containing `Edge4Care` (case-insensitive) shall be rejected. | ENV-015, AC-ENV-07 |
| FEAT-003-FR-16 | With `APP_ENV` `staging` or `production`, startup shall fail unless `RATE_LIMIT_LOGIN` is `5/minute`. | ENV-054 |
| FEAT-003-FR-17 | Operator commands shall validate only the ENV-053 variable subset (`JWT_SECRET`, `CORS_ORIGINS`, `CORS_ORIGIN_REGEX`, `DATABASE_READONLY_URL` not required). | ENV-053, ENV-002 |
| FEAT-003-FR-18 | `get_db()` shall yield one SQLAlchemy `Session` per request, commit on normal return, roll back on any exception and always close. | API-011 |
| FEAT-003-FR-19 | `get_pagination()` shall accept `limit` 1..500 (default 50) and `offset` ≥ 0 (default 0) and reject other values with 422 `INVALID_QUERY_PARAMETER`. | API-016 |
| FEAT-003-FR-20 | `get_db`, `get_settings` and auth dependencies shall be overridable through `app.dependency_overrides`. | API-017 |
| FEAT-003-FR-21 | `GET /api/v1/health` shall need no authentication and return 200 `{"status":"ok","database":"ok","version":GIT_SHA,"time":<UTC now>}` when `SELECT 1` succeeds within 2 seconds. | API-110, LOG-071, ARC-083, FR-253, ENV-018 |
| FEAT-003-FR-22 | When the database check fails or times out, health shall return 503 `{"status":"degraded","database":"unavailable","version":...,"time":...}` in the `Health` shape (not Problem) and reveal no other configuration. | API-111, LOG-071, FR-253 |
| FEAT-003-FR-23 | Health shall be exempt from rate limiting and shall write no audit row. | API-112 |

## Inputs

- Process environment variables of TRD 21 §4.2 and §4.3 (and `.env` only for `local`/`test`).
- HTTP `GET /api/v1/health` requests (no body, no auth).
- Database reachability (`SELECT 1`).

## Outputs

- A running FastAPI application or a non-zero exit (code 1) with a CRITICAL `startup_config_invalid` log record.
- Health JSON `Health` object (TRD 19 E-01) with status 200 or 503.
- Reusable dependencies for later routers.

## Data Flow

Process start → `Settings()` reads environment (plus `.env` in local/test) → validators and guards run → on failure: CRITICAL log, `sys.exit(1)` → on success: `create_app()` builds the app, mounts routers under `/api/v1` → uvicorn serves. Health request → `health` handler → `health_service.get_health()` → `SELECT 1` with 2 s timeout through the engine → 200 ok or 503 degraded with `version` = `GIT_SHA` and `time` = UTC now.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-002

- FEAT-002 provides the `backend/` package tree, `backend/api/health.py` skeleton, pinned FastAPI/SQLAlchemy/psycopg 3 versions and lint configuration.

Features that build directly on this one (BACKLOG.md §4): FEAT-005, FEAT-006, FEAT-008, FEAT-018.

## Database Impact

- Tables used: none. Health executes `SELECT 1` only.
- Tables created or modified: none.
- Connection: engine built from the normalised `DATABASE_URL` (role `echowell_app`); the final pool settings and TLS enforcement for non-local URLs are completed in FEAT-013 (API-125).

## API Impact

- Exposed: E-01 `GET /api/v1/health` (TRD 19 §4.3; schema `Health`).
- Consumed: none.
- Provides `get_settings`, `get_db`, `get_pagination` used by every later endpoint.

## Frontend Impact

None. The frontend never calls health; platforms and smoke tests do (TST-152 is delivered by FEAT-086).

## Analytics Impact

None. `PIPELINE_PROFILE` is validated here but only consumed by the pipeline runner (FEAT-024, FEAT-053).

## Security Requirements

- Authentication: none for health (API-110); all other endpoints get authentication from FEAT-020.
- No secret value appears in logs, error output or `repr(Settings)` (ENV-004, ENV-002).
- TLS to the database required in staging and production (ENV-011); production refuses unsafe configuration (ENV-012).
- `.env` ignored outside local/test (ENV-006); secrets are never set in committed files (ENV-005).

## Error Handling

| Failure | Behaviour | Trace |
|---|---|---|
| Invalid or missing variable, guard violated | CRITICAL `startup_config_invalid` naming variables and rule; exit code 1; app never accepts traffic | ENV-002, LOG-072 |
| Database down or `SELECT 1` > 2 s | Health returns 503 `degraded`; process keeps running | API-111 |
| Handler raises | `get_db()` rolls back and closes the session | API-011 |
| Bad `limit`/`offset` | 422 `INVALID_QUERY_PARAMETER` | API-016 |

## Logging Requirements

- CRITICAL `startup_config_invalid` with the list of invalid variable names and rules, never values (LOG-072).
- WARNING `debug_logging_enabled` at startup when `LOG_LEVEL=DEBUG` in staging or production (ENV-012).
- No audit row for health (API-112). `GIT_SHA` is the `version` reported (ENV-018).

## Testing Requirements

- Unit (`tests/unit/backend/core/test_config.py`, marker `unit`): CFG-06; AC-ENV-01..AC-ENV-05, AC-ENV-07, AC-ENV-09; `ECHOWELL_` typo rejection; `.env` ignored in staging; `RATE_LIMIT_LOGIN` guard (ENV-054); PIPELINE_AS_OF refusal (TST-038 startup part, AC-ENV-06 first clause).
- Integration (`tests/integration/api/test_health.py`, marker `integration`): TST-054 (200 ok with database up; 503 degraded with the database container stopped or the `get_db` override raising).
- Dependency tests: `get_db` commit/rollback/close behaviour (API-011) and `get_pagination` bounds (API-016) in `tests/unit/backend/test_deps.py`.
- Smoke: health smoke test and startup-guard test required by TRD 25 §4.6 Phase 3.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-003-AC-01 | Starting the backend with `APP_ENV=production` and `PIPELINE_PROFILE=test_v0_1` exits with code 1 and a CRITICAL log naming `PIPELINE_PROFILE`. | AC-ENV-01, AC-AGT-05, CFG-06 |
| FEAT-003-AC-02 | Starting with `APP_ENV=production` and `PIPELINE_AS_OF` set exits non-zero with a logged error. | AC-AGT-05, AC-ENV-06, TST-038 |
| FEAT-003-AC-03 | `APP_ENV=staging` with a `DATABASE_URL` lacking `sslmode=require` exits with code 1; the same URL with `APP_ENV=local` starts. Verified by: Unit (`tests/unit/backend/core/test_config.py`). | AC-ENV-02, AC-ARC-09 |
| FEAT-003-AC-04 | A 31-byte `JWT_SECRET` is rejected in every `APP_ENV`; `FACILITY_NAME=Edge4Care` is rejected. Verified by: Unit (`tests/unit/backend/core/test_config.py`). | AC-ENV-04, AC-ENV-07 |
| FEAT-003-AC-05 | `DATABASE_URL=postgres://u:p@h/db?sslmode=require` yields engine URL `postgresql+psycopg://u:p@h/db?sslmode=require`. Verified by: Unit (`tests/unit/backend/core/test_config.py`). | AC-ENV-05 |
| FEAT-003-AC-06 | `repr(get_settings())` shows `**********` for `DATABASE_URL`, `DATABASE_MIGRATION_URL`, `DATABASE_READONLY_URL`, `JWT_SECRET` and `SENTRY_DSN`, and the startup failure log never contains a secret value. Verified by: Unit (`tests/unit/backend/core/test_config.py`). | AC-ENV-09, AC-ENV-03 |
| FEAT-003-AC-07 | `GET /api/v1/health` with the database up returns 200 with `status` "ok", `database` "ok", `version` equal to `GIT_SHA`; with the database stopped returns 503 with `status` "degraded" and `database` "unavailable". | TST-054, FR-253 |
| FEAT-003-AC-08 | `GET /api/v1/health` succeeds without an `Authorization` header and creates no `audit_logs` row (verified once FEAT-012 exists). Verified by: Unit (`tests/unit/backend/core/test_config.py`; CFG-06). | API-110, API-112 |
| FEAT-003-AC-09 | `limit=0`, `limit=501` and `offset=-1` are rejected with 422 `INVALID_QUERY_PARAMETER`; omitted values default to 50 and 0. Verified by: Dependency tests (`tests/unit/backend/test_deps.py`). | API-016 |

## Definition of Done

- All FEAT-003 acceptance criteria pass; `pytest -q` green.
- `docker compose up -d` followed by `curl -fsS http://localhost:8000/api/v1/health` returns 200 once FEAT-006 is in place (TRD 25 §4.6 Phase 3 DoD).
- Lint, format, mypy (`disallow_untyped_defs`) pass; no business logic added.
- Requirement IDs cited in test names or `@pytest.mark.req` markers (TST-013).

## Implementation Notes

- Exit code 1 is the single code for settings-validation failures in the backend, the nightly job and every CLI command; exit code 2 is reserved for command-specific operator refusals, checked before settings validation (ENV-002).
- Run the guards in a module-level function (for example `validate_startup(settings)`) called by `create_app()`, `backend/jobs/nightly_run.py` and `backend/cli.py` so every process type enforces the same rules.
- Use `functools.lru_cache` for `get_settings()`; tests clear the cache or use `app.dependency_overrides`.
- `DATABASE_MIGRATION_URL` defaults to `DATABASE_URL`; the application code never reads it (ARC-015); only Alembic and the operator CLI do.
- Health is the one place where the response is not `application/problem+json` on failure (API-111).
