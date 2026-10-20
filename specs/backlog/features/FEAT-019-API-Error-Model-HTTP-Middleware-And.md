# FEAT-019 API error model, HTTP middleware and response metadata

| Field | Value |
|---|---|
| Epic | Backend API |
| Build phase | Phase 5 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-018, FEAT-014 |
| Status | Not Started |

## Purpose

Give every endpoint the same outer contract before any business endpoint is written: one RFC 7807 `application/problem+json` error shape with a closed code catalogue, exception handlers that never leak internals, CORS with exact origins, security headers, request-size and media-type limits, the shared list envelope, ISO date and range validation, and the `meta` block whose `as_of` is the latest succeeded pipeline run. The frontend's generated types and error display depend on these shapes being uniform.

## Business Context

- BR-01: rejected records get a 422 Problem body listing every failed field (FR-027).
- BR-12 and BR-15: every list, detail and analytics response states facility, data source, as-of, baseline_n, cusum_h and profile so staff and researchers know what they are looking at (FR-332, FR-333, D-32).
- BR-16: no stack traces, SQL or secrets in errors; strict CORS; security headers; size and media-type limits; no audio media types (SEC-080..SEC-086, SEC-094).

## Referenced TRDs

- TRD 05 API-057, API-069, API-093..API-098, API-100, API-101, API-104, API-106; §4.7 error model and code catalogue; §4.8.
- TRD 17 LOG-040..LOG-044; AC-LOG-08.
- TRD 12 SEC-080..SEC-086, SEC-094.
- TRD 20 PGS-028.
- TRD 19 `Problem`, `ProblemFieldError`, `Meta`, `PageMeta` component schemas.
- TRD 21 ENV-016.
- TRD 02 FR-027, FR-332, FR-333.
- TRD 13 TST-034, TST-133 (request part), TST-134.
- TRD 24 D-32, D-48, D-66.

## Scope

- `backend/core/errors.py`: domain base class `EchoWellError(code, status, detail, errors=[])` (the `AppError` hierarchy of API-004), the closed code catalogue of TRD 05 §4.7 with fixed titles, and handlers for `HTTPException` (404 `NOT_FOUND`, 405 `METHOD_NOT_ALLOWED`), `RequestValidationError` (`VALIDATION_ERROR` with `errors[]` `{field, code, message}`, no `input` echo), `EchoWellError`, SQLAlchemy `OperationalError` (503 `SERVICE_UNAVAILABLE`, `Retry-After: 30`), SQLSTATE `EW001` (500 `INTERNAL_ERROR` plus an `error` log naming the table), and `Exception` (500 `INTERNAL_ERROR`, detail "An unexpected error occurred.").
- Problem body `{type: "urn:echowell:error:<CODE>", title, status, detail, request_id, errors}` with `Content-Type: application/problem+json`; `request_id` from the FEAT-018 context.
- `RATE_LIMITED`/`ACCOUNT_TEMPORARILY_LOCKED` responses carry `Retry-After` (the limiter itself is FEAT-022).
- CORS via Starlette `CORSMiddleware` exactly as API-101 (exact `CORS_ORIGINS`, `CORS_ORIGIN_REGEX` only when non-empty, `allow_credentials=False`, methods GET/POST/PATCH/OPTIONS, headers Authorization/Content-Type/X-Request-ID, expose X-Request-ID/Retry-After/X-EchoWell-Experimental, `max_age=600`).
- Security-header middleware (API-106).
- Request-size middleware: 64 KB default, 5 MB for `POST /api/v1/ingest`, checking `Content-Length` and streamed bytes → 413 `PAYLOAD_TOO_LARGE`.
- Media-type guard: `application/json` everywhere; `multipart/form-data` with a single `text/csv` (or browser `application/vnd.ms-excel`, ING-012) part only on `POST /api/v1/ingest`; any `audio/*` or other type → 415 `UNSUPPORTED_MEDIA_TYPE`.
- `backend/schemas/common.py`: `Meta`, `PageMeta`, generic `Page[T]` (`{meta, items, total, limit, offset}`), `Problem`, `ProblemFieldError` (TRD 23 §4.6 cross-cutting schemas).
- `get_meta()` dependency: `facility_name` from `facilities.name`, `facility_tz` from `FACILITY_TZ`, `data_source_label` from `DATA_SOURCE_LABEL`, `as_of` = `as_of` of the most recent `succeeded` `pipeline_runs` row (NULL when none), `baseline_n` and `cusum_h` of the active profile, `pipeline_profile`.
- Date parameter helpers: ISO calendar dates interpreted in `FACILITY_TZ`; `from` > `to` → 422 `INVALID_QUERY_PARAMETER`; response timestamp serialisation rules (UTC `Z`; `*_local` with facility offset; `local_date` as `YYYY-MM-DD`).
- Path/query pattern constants (resident and device codes `^[A-Z0-9]{1,16}$`, UUIDs, enums) for routers to reuse.
- Pydantic request-model base with `extra="forbid"`.

## Out of Scope

- Authentication and authorization errors' raising logic (FEAT-020, FEAT-021) — only the codes and rendering exist here.
- Rate limiting (FEAT-022); ingest-specific validation codes (FEAT-023); CSV parsing (FEAT-026) — SEC-086 parsing rules are applied there, this feature provides the media-type gate.
- Business endpoints (FEAT-024 onward).
- Request-ID middleware and access logs (FEAT-018).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-019-FR-01 | Every non-2xx response shall have `Content-Type: application/problem+json` and body fields `type`, `title`, `status`, `detail`, `request_id`, `errors` (array, empty when not applicable). | LOG-040, D-48 |
| FEAT-019-FR-02 | `type` shall be `urn:echowell:error:<CODE>` with `<CODE>` from the TRD 05 §4.7 catalogue and `title` its fixed English title; each `errors[]` item is `{field, code, message}`; no code outside the catalogue is emitted. | LOG-041, TRD 05 §4.7 |
| FEAT-019-FR-03 | `RequestValidationError`, Starlette `HTTPException` (404/405) and unhandled exceptions shall be converted by handlers in `backend/core/errors.py`; handlers are registered for `HTTPException`, `RequestValidationError`, `EchoWellError`, `OperationalError` and `Exception`. | API-095, LOG-044 |
| FEAT-019-FR-04 | `RequestValidationError` shall become `VALIDATION_ERROR` with `errors[]` whose `field` is the dotted location without the leading `body`/`query` segment and whose `code` is the field-level code, never echoing the submitted value. | LOG-043, FR-027 |
| FEAT-019-FR-05 | A 500 response shall contain `detail` "An unexpected error occurred." and the request ID, and never stack traces, SQL, file paths, library versions, exception messages or secrets. | API-096, LOG-042, SEC-085 |
| FEAT-019-FR-06 | `sqlalchemy.exc.OperationalError` shall map to 503 `SERVICE_UNAVAILABLE` with `Retry-After: 30`. | API-097 |
| FEAT-019-FR-07 | SQLSTATE `EW001` shall map to 500 `INTERNAL_ERROR` and log an `error` event naming the table. | PGS-028 |
| FEAT-019-FR-08 | 429 responses shall include `Retry-After` in seconds. | API-098 |
| FEAT-019-FR-09 | Every list endpoint shall return `{"meta": {...}, "items": [...], "total": n, "limit": l, "offset": o}` plus endpoint-specific top-level fields of TRD 19, via the shared `Page[T]` schema. | API-100 |
| FEAT-019-FR-10 | Every list, detail and analytics response shall include `meta {facility_name, facility_tz, data_source_label, as_of, baseline_n, cusum_h, pipeline_profile}` built by `get_meta()`; `facility_name` comes from `facilities.name`. | API-057, ENV-016, FR-332, D-32 |
| FEAT-019-FR-11 | Read endpoints using a reference date shall use `as_of` = the `as_of` of the most recent `succeeded` pipeline run and return it in `meta.as_of` (NULL before any succeeded run, per the TRD 19 `Meta` schema). | API-069, FR-333 |
| FEAT-019-FR-12 | Date query parameters shall be ISO 8601 calendar dates interpreted in `FACILITY_TZ`; `from` later than `to` returns 422 `INVALID_QUERY_PARAMETER`. | API-093 |
| FEAT-019-FR-13 | Response timestamps shall be ISO 8601 UTC with `Z`; `*_local` fields carry the facility offset; `local_date` fields are `YYYY-MM-DD`. | API-094 |
| FEAT-019-FR-14 | CORS shall be configured exactly as API-101; a request from an origin not in `CORS_ORIGINS` (or, in staging only, not matching `CORS_ORIGIN_REGEX`) receives no `Access-Control-Allow-Origin` header. | API-101, SEC-094, D-66, LOG-035 |
| FEAT-019-FR-15 | Bodies larger than 64 KB (5 MB for `POST /ingest`) shall be rejected with 413 `PAYLOAD_TOO_LARGE`, checking `Content-Length` and the streamed byte count. | API-104, SEC-081 |
| FEAT-019-FR-16 | Every response shall carry `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`, plus `Strict-Transport-Security: max-age=31536000; includeSubDomains` in staging and production. | API-106 |
| FEAT-019-FR-17 | All request bodies shall be validated by Pydantic models with `extra="forbid"`; unknown properties return 422. | SEC-080 |
| FEAT-019-FR-18 | Only `application/json` (all endpoints) and `multipart/form-data` with a single `text/csv` part (`POST /ingest` only; `application/vnd.ms-excel` as sent by browsers for .csv files is also accepted for that part) shall be accepted; `audio/*` or any other media type returns 415 `UNSUPPORTED_MEDIA_TYPE`. | SEC-082, ING-012 |
| FEAT-019-FR-19 | Database access shall use SQLAlchemy expressions or `text()` with bound parameters only (Bandit B608 clean). | SEC-083 |
| FEAT-019-FR-20 | Path and query parameters shall be validated against the TRD 19 patterns (codes `^[A-Z0-9]{1,16}$`, UUIDs, dates, enums, ranges). | SEC-084 |
| FEAT-019-FR-21 | CSV cell values starting with `=`, `+`, `-`, `@` shall be treated as data only and never evaluated; this rule is exposed as a shared helper for the CSV features. | SEC-086 |

## Inputs

- Exceptions raised by routers, services, repositories and the database; request headers (`Origin`, `Content-Type`, `Content-Length`); settings `CORS_ORIGINS`, `CORS_ORIGIN_REGEX`, `APP_ENV`, `FACILITY_TZ`, `DATA_SOURCE_LABEL`, `PIPELINE_PROFILE`.
- `facilities`, `pipeline_runs`, `config_parameters` rows for `get_meta()` (FEAT-014 repositories).

## Outputs

- Problem responses; CORS and security headers; 413/415 rejections; `Meta`/`Page` envelopes for later endpoints.

## Data Flow

Request → (FEAT-018 request-ID) → CORS → size and media-type guards → security headers → router → service → repository. Errors raised anywhere propagate to the registered handlers, which build the Problem body with the current `request_id`. Successful list/detail handlers call `get_meta()` (latest succeeded run, active profile's `baseline_n`/`cusum_h`) and return `Page[T]` or a detail DTO containing `meta`.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-018, FEAT-014

- FEAT-018 provides the request-ID context included in every Problem body and the `X-Request-ID` header exposed by CORS.
- FEAT-014 provides the repositories used by `get_meta()` (facility row, latest succeeded run, profile parameters).

Features that build directly on this one: FEAT-020, FEAT-023, and every endpoint feature.

## Database Impact

- Tables read: `facilities` (name), `pipeline_runs` (latest succeeded `as_of`), `config_parameters` (`baseline_n`, `cusum_h` of `PIPELINE_PROFILE`).
- Tables created or modified: none.

## API Impact

- Applies to every endpoint E-01..E-32 (headers, CORS, size/media limits, Problem errors); E-01 health keeps its own `Health` shape on 503 (API-111).
- Provides `Meta`, `PageMeta`, `Problem`, `ProblemFieldError` component schemas of TRD 19.

## Frontend Impact

None in code; the frontend error display (FEAT-062) relies on the Problem shape and `request_id`.

## Analytics Impact

None.

## Security Requirements

- No internals in errors (SEC-085, LOG-042); no input echo in validation errors (LOG-043).
- Exact-origin CORS with no credentials; regex only in staging (SEC-094, D-66).
- Security headers and HSTS in staging/production (API-106).
- Size and media-type limits; audio types refused (SEC-081, SEC-082, ARC-003).
- Parameterised SQL only (SEC-083).

## Error Handling

This feature is the error handling layer. Mapping summary: validation → 422 `VALIDATION_ERROR`; bad query → 422 `INVALID_QUERY_PARAMETER`; unknown route → 404 `NOT_FOUND`; wrong method → 405 `METHOD_NOT_ALLOWED`; oversize → 413 `PAYLOAD_TOO_LARGE`; media type → 415 `UNSUPPORTED_MEDIA_TYPE`; database down → 503 `SERVICE_UNAVAILABLE` + `Retry-After: 30`; `EW001` and anything else → 500 `INTERNAL_ERROR`.

## Logging Requirements

- `EW001` → `error` event naming the table (PGS-028).
- Unhandled exceptions are logged once by FEAT-018 (`unhandled_exception`); the handler here does not log a second time.
- No audit rows (403 `access.denied` audit is FEAT-021).

## Testing Requirements

- Unit (`tests/unit/backend/core/test_errors.py`): TST-034 (Content-Type, body fields, `type` URN, `errors[]` shape, `X-Request-ID` header on errors); `RequestValidationError` field path without `body` and no `input`; 500 detail text; `OperationalError` → 503 with `Retry-After: 30`; `EW001` → 500 with table-naming log.
- Integration (`tests/integration/api/test_http_middleware.py`): CORS allowed and disallowed origins (SEC-094, TST-134), staging regex only when set; security headers present, HSTS only in staging/production; 64 KB + 1 byte body → 413 on a JSON endpoint and accepted up to 5 MB on `/ingest`; `Content-Type: audio/wav` → 415 and nothing stored (TST-133, request part); unknown JSON property → 422 (SEC-080); `from` > `to` → 422.
- Integration: AC-LOG-08 (forced 500 returns Problem with `INTERNAL_ERROR`, no stack trace, `request_id`).
- Unit: `get_meta()` returns NULL `as_of` with no succeeded run and the latest succeeded run's `as_of` otherwise; `baseline_n` 16 under `test_v0_1` and 30 under `production`.
- CI: Bandit `-ll` reports no B608 (SEC-083; job delivered by FEAT-078).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-019-AC-01 | A forced exception returns 500 with `Content-Type: application/problem+json`, `type` `urn:echowell:error:INTERNAL_ERROR`, `detail` "An unexpected error occurred.", a `request_id` equal to the `X-Request-ID` header, and no stack trace or exception text. | AC-LOG-08, API-096, LOG-042 |
| FEAT-019-AC-02 | A request to an unknown path returns 404 `NOT_FOUND` and a wrong method 405 `METHOD_NOT_ALLOWED`, both as Problem bodies with `errors: []`. | API-095, LOG-040 |
| FEAT-019-AC-03 | A body with an unknown property returns 422 `VALIDATION_ERROR` with an `errors[]` item whose `code` is `extra_forbidden` and which contains no `input` key. | SEC-080, LOG-043 |
| FEAT-019-AC-04 | With the database stopped, a read endpoint returns 503 `SERVICE_UNAVAILABLE` with `Retry-After: 30`. | API-097 |
| FEAT-019-AC-05 | A 65,537-byte JSON body to any endpoint other than `/ingest` returns 413 `PAYLOAD_TOO_LARGE`; a `Content-Type: audio/wav` request returns 415 `UNSUPPORTED_MEDIA_TYPE`. | API-104, SEC-081, SEC-082 |
| FEAT-019-AC-06 | A preflight from an origin in `CORS_ORIGINS` gets `Access-Control-Allow-Origin` equal to that origin and `Access-Control-Expose-Headers` including `X-Request-ID`; an origin not listed gets no `Access-Control-Allow-Origin`. | API-101, SEC-094, LOG-035, TST-134 |
| FEAT-019-AC-07 | Every response carries `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`; with `APP_ENV=staging` it also carries `Strict-Transport-Security: max-age=31536000; includeSubDomains`. | API-106 |
| FEAT-019-AC-08 | With one succeeded run whose `as_of` is 2026-10-30T20:00:00Z under `test_v0_1`, `get_meta()` returns `as_of` "2026-10-30T20:00:00Z", `baseline_n` 16, `cusum_h` 5.0, `pipeline_profile` "test_v0_1", `facility_name` "Edgewood". | API-057, API-069, FR-332, FR-333 |
| FEAT-019-AC-09 | A query with `from=2026-10-20&to=2026-10-10` returns 422 `INVALID_QUERY_PARAMETER`. | API-093 |

## Definition of Done

- All FEAT-019 acceptance criteria pass; TST-034 passes.
- The error catalogue in code equals TRD 05 §4.7 (a unit test compares codes, statuses and titles); delivered in the Phase 5 PR.

## Implementation Notes

- Register handlers in `create_app()`; keep the request-ID middleware outermost (FEAT-018) so every Problem has an ID.
- The `Meta` schema permits `as_of: null` (TRD 19 `Meta`); do not substitute the current time when no run has succeeded.
- `CORS_ORIGIN_REGEX` is refused in production at startup (ENV-012); pass `allow_origin_regex` only when non-empty.
- `facility_tz` in `meta` comes from `FACILITY_TZ` (API-057, ENV-016), while local dates are computed with `facilities.timezone` (DME-019); both default to `America/Chicago` and are set from the same variable by `bootstrap`/`seed`.
