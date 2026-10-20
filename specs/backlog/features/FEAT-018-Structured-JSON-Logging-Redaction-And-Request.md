# FEAT-018 Structured JSON logging, redaction and request-ID propagation

| Field | Value |
|---|---|
| Epic | Monitoring & Logging |
| Build phase | Phase 5 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-003 |
| Status | Not Started |

## Purpose

Make every backend log line machine-readable, safe and traceable: configure logging once in `backend/core/logging.py` (single-line JSON in staging and production, console locally), carry request and pipeline context in `contextvars`, redact secrets, e-mails, bodies and connection strings before formatting, accept or generate an `X-Request-ID` for every request and return it on every response, and write exactly one `request_completed` access-log line per request. This is the observability base for incident triage without exposing research data or credentials.

## Business Context

- BR-16: logs never contain passwords, tokens, API keys, feature values, request bodies or personal data (ARC-095, LOG-020..LOG-022, SEC-107).
- BR-17: structured JSON logs on stdout for the hosting platforms (NFR-100); every response carries `X-Request-ID` so users can quote a reference (FR-254).

## Referenced TRDs

- TRD 17 LOG-001..LOG-006, LOG-010..LOG-012, LOG-020..LOG-025, LOG-030..LOG-035, LOG-070, LOG-120, LOG-122; §8 implementation notes; AC-LOG-01, AC-LOG-02, AC-LOG-04.
- TRD 05 API-105, API-107.
- TRD 12 SEC-107.
- TRD 01 ARC-095.
- TRD 03 NFR-100..NFR-105.
- TRD 02 FR-254.
- TRD 21 ENV-012 (`console` refused in staging/production), ENV-018 (`version` = `GIT_SHA`).

## Scope

- `backend/core/logging.py`: `configure_logging(settings)` via `logging.config.dictConfig`, called once from `create_app()`, `backend/jobs/nightly_run.py` and `backend/cli.py`:
  - JSON formatter (one line per record) with at least `ts` (UTC ISO 8601), `level`, `logger`, `msg`, `event`, `env` (`APP_ENV`), `version` (`GIT_SHA`), plus context fields.
  - Console formatter `ts level logger event key=value…` for `LOG_FORMAT=console`.
  - uvicorn `error` logger routed through the same formatter; uvicorn default access log disabled (`uvicorn.access` `propagate=False`, level WARNING).
  - `contextvars` for `request_id`, `actor`, `user_id`, `pipeline_run_id`, `resident_code`, injected into every record by a filter.
  - Redaction filter by key pattern `password|secret|token|authorization|api_key|apikey|cookie|dsn|database_url|body|note` → `"[REDACTED]"`, and substring redaction of credentialed URLs (`\w+://[^:\s]+:[^@\s]+@`) and `Bearer\s+\S+` in `msg` and `exc_message`.
- Request-ID middleware (pure ASGI, outermost): reuse an incoming `X-Request-ID` matching `^[A-Za-z0-9-]{8,64}$`, else generate UUID4; set the context variable; add `X-Request-ID` to every response including errors, 404s, 429s and CORS preflights.
- Access-log middleware (pure ASGI): one `request_completed` record per request with `route` (template), `method`, `status`, `duration_ms`, `actor_type`, `actor_id`; level INFO for status < 400, WARNING for 400–499 except 401 and 404 (INFO), ERROR for ≥ 500; `GET /api/v1/health` returning 200 logged at DEBUG.
- `unhandled_exception` ERROR record (once) with `exc_type`, sanitised `exc_message`, `stack`, `request_id`; the hook to report it to Sentry when `SENTRY_DSN` is set is provided for FEAT-084.
- Constant `REQUEST_ID_HEADER = "X-Request-ID"` exported for the CORS `expose_headers` configuration in FEAT-019.

## Out of Scope

- The Problem-details error handler and CORS middleware (FEAT-019); this feature only guarantees the header is present and provides the context.
- Pipeline-run log events (`pipeline_run_started`, `pipeline_run_finished`, stage warnings, `run_abandoned`, `nightly_run_missing`) (FEAT-056) and the Admin warning (NFR-103, FEAT-074).
- Sentry SDK integration (FEAT-084, NFR-102), uptime monitoring (FEAT-085, NFR-104), silent-device visibility (NFR-105, delivered by FEAT-049 and FEAT-029).
- Ingest-specific log events (`ingest_record_rejected`, etc.) (FEAT-025, FEAT-026).
- Frontend sending a UUID `X-Request-ID` and showing "Reference: <id>" (LOG-032, FEAT-062).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-018-FR-01 | With `LOG_FORMAT=json`, every log record shall be a single-line JSON object on stdout containing at least `ts`, `level`, `logger`, `msg`, `event`, `env`, `version`. | LOG-001, NFR-100, ENV-018 |
| FEAT-018-FR-02 | With `LOG_FORMAT=console`, lines shall be human-readable (`ts level logger event key=value…`); `console` is refused in staging and production by settings validation. | LOG-002, ENV-012 |
| FEAT-018-FR-03 | Logging shall be configured once in `backend/core/logging.py` with the standard library and a custom JSON formatter; uvicorn loggers use the same formatter and the uvicorn default access log is disabled. | LOG-003 |
| FEAT-018-FR-04 | `request_id`, `actor`, `user_id`, `pipeline_run_id` and `resident_code` shall be carried in `contextvars` and added to every record emitted in that context. | LOG-004 |
| FEAT-018-FR-05 | Log timestamps shall be UTC. | LOG-005 |
| FEAT-018-FR-06 | `analytics/` shall not configure logging or import logging handlers; warnings are returned as data and logged by the backend. | LOG-006 |
| FEAT-018-FR-07 | Every HTTP request shall produce exactly one `request_completed` record (INFO < 400; WARNING 400–499 except 401 and 404 at INFO; ERROR ≥ 500) with `route` template, `method`, `status`, `duration_ms`, `request_id`, `actor_type`, `actor_id`, without query values of `from`/`to` beyond dates, bodies or credential headers. | LOG-010, API-107 |
| FEAT-018-FR-08 | `GET /api/v1/health` responses with 200 shall be logged at DEBUG only. | LOG-011 |
| FEAT-018-FR-09 | Default `LOG_LEVEL` shall be `INFO`; `DEBUG` in staging/production triggers the `debug_logging_enabled` warning (ENV-012) and is for at most 24 h investigations. | LOG-012 |
| FEAT-018-FR-10 | Logs shall never contain passwords, password hashes, JWTs, API keys or their hashes, `Authorization`, `X-API-Key` or `Cookie` values, `JWT_SECRET`, database URLs, `SENTRY_DSN`, request or response bodies, feature values, e-mail addresses, names or note bodies; users are identified by `user_id`, residents by study ID. | LOG-020, LOG-021, LOG-022, SEC-107, ARC-095 |
| FEAT-018-FR-11 | A key-based redaction filter (pattern `password\|secret\|token\|authorization\|api_key\|apikey\|cookie\|dsn\|database_url\|body\|note`, case-insensitive) and a substring filter for credentialed URLs and bearer tokens shall run before formatting. | LOG-023, LOG-024 |
| FEAT-018-FR-12 | No audio or audio-derived data is logged. | LOG-025 |
| FEAT-018-FR-13 | An incoming `X-Request-ID` shall be accepted only if it matches `^[A-Za-z0-9-]{8,64}$`, otherwise a UUID4 is generated; the ID is stored in a context variable used by logging and audit. | LOG-030, API-105 |
| FEAT-018-FR-14 | Every HTTP response, including errors, 404s and 429s, shall carry `X-Request-ID`. | LOG-031, API-105, FR-254 |
| FEAT-018-FR-15 | The current request ID shall be available to `audit_service.record` so every audit row written during a request stores it. | LOG-033 |
| FEAT-018-FR-16 | A pipeline run started by a request shall log with both `request_id` and `pipeline_run_id`; nightly and CLI runs log without `request_id` and with `actor = system` (context helpers provided here; used by FEAT-053, FEAT-054). | LOG-034 |
| FEAT-018-FR-17 | `X-Request-ID` shall be listed in the CORS `Access-Control-Expose-Headers` (configured by FEAT-019 using the exported constant). | LOG-035 |
| FEAT-018-FR-18 | An unhandled exception during a request shall be logged once at ERROR `unhandled_exception` with `exc_type`, sanitised `exc_message`, `stack`, `request_id`. | LOG-070 |
| FEAT-018-FR-19 | Logs shall not be exported to an additional log store on the interim stack; incident excerpts beyond retention are summarised by IDs and timestamps only. | LOG-120, LOG-122 |

## Inputs

- `Settings.LOG_FORMAT`, `LOG_LEVEL`, `APP_ENV`, `GIT_SHA` (FEAT-003).
- HTTP requests (headers, route, status); exceptions; context set by services.

## Outputs

- Structured log records on stdout; `X-Request-ID` response header; request-ID context for audit rows.

## Data Flow

Request arrives → request-ID middleware (outermost) validates or generates the ID and sets the context → actor context is set later by the auth dependencies (FEAT-020) → handler runs; any log record gets context fields and passes the redaction filters → response leaves with `X-Request-ID` → access-log middleware writes one `request_completed` record with duration and status → unhandled exceptions produce one `unhandled_exception` record (the Problem response itself is FEAT-019).

## Dependencies

Required before implementation (BACKLOG.md): FEAT-003

- FEAT-003 provides `create_app()`, `Settings` (`LOG_FORMAT`, `LOG_LEVEL`, `GIT_SHA`) and the guard that refuses `console` in production.

Features that build directly on this one: FEAT-019, FEAT-056, FEAT-084.

## Database Impact

None. (Audit rows receive `request_id` through FEAT-015 using this context.)

## API Impact

- Adds the `X-Request-ID` response header to every endpoint (E-01..E-32) and accepts it on every request.
- No endpoint added.

## Frontend Impact

None in this feature; the frontend client (FEAT-062) sends its own UUID `X-Request-ID` and shows the returned ID in errors (LOG-032).

## Analytics Impact

None; `analytics/` stays free of logging handlers (LOG-006).

## Security Requirements

- Redaction of secrets, credentials, bodies, e-mails and note text (LOG-020..LOG-024, SEC-107).
- Request IDs restricted to `^[A-Za-z0-9-]{8,64}$` to prevent log injection (LOG-030).
- No logging of feature values or ingest bodies (LOG-021, ARC-095).

## Error Handling

- Invalid incoming `X-Request-ID`: replaced by a generated UUID4, request continues (LOG-030, AC-LOG-04).
- Formatter failure on a non-serialisable field: the field is converted with `str()` after redaction, so logging never raises into the request path.
- Unhandled exception: one ERROR `unhandled_exception` record; the client-facing 500 Problem response is produced by FEAT-019.

## Logging Requirements

- `request_completed` per request (LOG-010) with the API-107 fields.
- `unhandled_exception` on 500s (LOG-070).
- `debug_logging_enabled` WARNING when `LOG_LEVEL=DEBUG` in staging/production (ENV-012).
- No audit rows are produced by this feature.

## Testing Requirements

- Unit (`tests/unit/backend/core/test_logging.py`): JSON formatter fields (LOG-001), UTC timestamps (LOG-005), context injection (LOG-004), key redaction for each pattern word (LOG-023), URL and bearer substring redaction (LOG-024), console format (LOG-002).
- Integration (`tests/integration/api/test_request_id.py`): AC-LOG-04 (valid ID echoed; `bad id!` replaced by a UUID); header present on 404 and error responses (LOG-031); one `request_completed` per request with correct levels for 200, 401, 404, 422 and 500 (LOG-010); health 200 logged at DEBUG (LOG-011).
- Integration: AC-LOG-01 (every captured line in the integration suite parses as JSON with the required keys) — enforced by a session-scoped `caplog`/stdout capture fixture.
- Integration: AC-LOG-02 once FEAT-020 exists (login with password `Secret-123!` and an authorised request: logs contain neither the password, the JWT nor the e-mail).
- Static check: `grep -rn "import logging" analytics` returns no handler configuration (LOG-006).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-018-AC-01 | With `LOG_FORMAT=json`, every line emitted during the integration test suite parses as JSON and contains `ts`, `level`, `logger`, `msg`, `event`, `env`, `version`. | AC-LOG-01, LOG-001 |
| FEAT-018-AC-02 | A request with `X-Request-ID: abcd1234-test` returns that header value; a request with `X-Request-ID: bad id!` returns a generated UUID4. | AC-LOG-04, LOG-030 |
| FEAT-018-AC-03 | Responses with status 200, 401, 404, 422, 429 and 500 all carry `X-Request-ID`. | LOG-031, FR-254, API-105 |
| FEAT-018-AC-04 | Each request in a test produces exactly one `request_completed` record; a 404 is INFO, a 422 is WARNING, a 500 is ERROR; `GET /api/v1/health` with 200 is DEBUG. | LOG-010, LOG-011 |
| FEAT-018-AC-05 | Logging `{"password": "x", "Authorization": "Bearer abc", "note": "text"}` yields `[REDACTED]` for all three values, and a message containing `postgresql://u:secretpw@h/db` is logged without `secretpw`. | LOG-023, LOG-024, SEC-107 |
| FEAT-018-AC-06 | After FEAT-020 lands, a login with password `Secret-123!` followed by an authorised request produces logs with zero matches for `Secret-123!`, the JWT and the e-mail address. | AC-LOG-02, LOG-020, LOG-022 |
| FEAT-018-AC-07 | A forced exception produces exactly one ERROR `unhandled_exception` record with `exc_type`, `stack` and the request's `request_id`. | LOG-070 |

## Definition of Done

- All FEAT-018 acceptance criteria pass (AC-06 when FEAT-020 is present in the same Phase 5 PR).
- `create_app()`, the nightly job entry point and the CLI all call `configure_logging` once; delivered in the Phase 5 PR.

## Implementation Notes

- Implement both middlewares as pure ASGI middleware, not `BaseHTTPMiddleware`, so `contextvars` survive into background tasks (TRD 17 §8).
- Place the request-ID middleware outermost so CORS preflight and 404 responses carry the header (TRD 17 §8).
- Use the route template (`/api/v1/residents/{resident_code}`) in `route`, not the concrete path, to avoid logging values beyond study IDs in a structured field.
- Never log `request.body()`; ingest identifiers are logged explicitly by the ingest features (LOG-021).
