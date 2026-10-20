# FEAT-039 Security and privacy verification suite (auth matrix, token attacks, no-audio, data minimisation)

| Field | Value |
|---|---|
| Epic | Authentication & Security |
| Build phase | Phase 5 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-038 |
| Status | Not Started |

## Purpose

Prove, with automated tests that run on every PR, that the finished API enforces the TRD 12 role matrix for every endpoint and credential type, that no route is reachable without an explicit auth dependency, that forged, expired or `alg: none` tokens and revoked or under-scoped API keys are refused, that nothing in the API accepts or returns audio, that CORS refuses unknown origins, and that responses, logs and schemas expose study IDs only — no names, password or key hashes, payloads or ground truth. This suite is the evidence for MVP-07 and AC-SEC-01/02/04.

## Business Context

- BR-16 (access control, privacy, data minimisation): role matrix, credential checks, no PII.
- BR-01 (no audio): no endpoint or field can carry audio.
- BR-18 (no LLM): no AI service dependency.
- FRs covered (BACKLOG.md): FR-015, FR-212, FR-213, FR-245.

## Referenced TRDs

- TRD 12 §4.6 role matrix, SEC-040, SEC-041, SEC-042, SEC-044, SEC-045, SEC-120..SEC-129; AC-SEC-01, AC-SEC-02, AC-SEC-04.
- TRD 13 TST-130, TST-132, TST-133, TST-134, TST-137 (in scope); TST-135 and TST-136 (executed by later features); Table 4.13-A; MVP-07.
- TRD 03 NFR-040..NFR-052 (no audio, no PII, TLS, least privilege, logs without secrets, export limits).
- TRD 23 DME-005 (no hashes, payloads, raw bodies or ground truth in response schemas), DME-020 (no names, contacts or audio in any entity).
- TRD 06 DB-035 (no PII or audio columns).
- TRD 22 TPS-080..TPS-086 (no LLM, analytics trackers, voice services, notification services, third-party auth or CDNs, ML services).
- TRD 25 AGT-004, AGT-006, AGT-017; TRD 05 API-012, API-014, API-024, API-101; TRD 02 §4.26.

## Scope

- `tests/security/test_auth_matrix.py`: every endpoint of contract §10 as amended (TRD 13 Table 4.13-A) × caller types anon, API key `ingest:write`, API key `pipeline:run` (for `POST /pipeline/run`), admin, clinician, researcher, asserting the listed status.
- `tests/integration/test_auth_coverage.py`: enumerate `app.routes`; only `/health`, `/auth/login`, `/openapi.json` (and `/docs` outside production) may lack an auth dependency.
- `tests/security/test_tokens.py`: expired JWT (61 min), altered signature, `alg: none`, JWT of an inactive user; `tests/security/test_api_keys.py`: revoked key, key without `ingest:write`.
- `tests/security/test_no_audio.py`: OpenAPI scan for "audio" (only `audio_quality_flag`), no `audio/*` request content type, `Content-Type: audio/wav` to every endpoint → 415 or 422 with nothing stored.
- CORS preflight test (allowed origin echoed; unknown origin gets no `Access-Control-Allow-Origin`).
- Data-minimisation test: ingest SRC-05, then capture all API responses and log records and assert no field other than study IDs identifies a person.
- Static checks: no response schema exposes `password_hash`, `key_hash`, `raw_sessions.payload`, `ingest_rejections.raw_body` or ground-truth columns outside `alarm_timing`; schema column whitelist without names, birth dates, contacts or audio; no LLM, analytics-tracker, voice-service, notification or third-party-auth dependency in backend requirements and frontend `package.json`.

## Out of Scope

- Implementing authentication, roles and rate limits (FEAT-020, FEAT-021, FEAT-022); this feature only verifies them.
- Rate-limit tests TST-131 (FEAT-022).
- HSTS and HTTP→HTTPS smoke tests TST-135 (post-deploy smoke, FEAT-086) and the dependency audit and secret scan TST-136 (CI `security-audit`, FEAT-078).
- Frontend CSP and headers (FEAT-082); database grant tests TST-041 (FEAT-012).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-039-FR-01 | An automated test shall call every endpoint in TRD 13 Table 4.13-A with each caller type and assert exactly the listed status (allowed status, 401 or 403), including both API-key scopes on `POST /pipeline/run` (403 for `ingest:write`, 202 for `pipeline:run`) and the CSV variants of `GET /scores` (clinician 403). | SEC-041, TST-130, AC-SEC-01; FR-212, FR-213 |
| FEAT-039-FR-02 | A test shall enumerate `app.routes` and fail when a route other than `/api/v1/health`, `/api/v1/auth/login`, `/api/v1/openapi.json` (and `/api/v1/docs` outside production) has no explicit auth dependency; adding an unprotected route makes it fail. | SEC-042, AC-SEC-02 |
| FEAT-039-FR-03 | Tests shall assert that an expired JWT (61 minutes old) returns 401 `TOKEN_EXPIRED`, a JWT with an altered signature and a JWT with `alg: none` return 401 `TOKEN_INVALID`, a JWT of a deactivated user returns 401 `TOKEN_INVALID`, a revoked (inactive) API key returns 401 `API_KEY_INVALID`, and an API key without `ingest:write` on an ingest endpoint returns 403 `FORBIDDEN`. | TST-132, AC-SEC-04, API-012, API-014, API-024 |
| FEAT-039-FR-04 | Tests shall assert that the OpenAPI document contains no path or schema property containing "audio" except `audio_quality_flag` and no `audio/*` request content type, and that a request with `Content-Type: audio/wav` to every endpoint returns 415 or 422 and stores nothing. | TST-133, SEC-121, NFR-040, AGT-006; FR-015 |
| FEAT-039-FR-05 | A test shall assert that a CORS preflight from an origin not in `CORS_ORIGINS` receives no `Access-Control-Allow-Origin` header and that an allowed origin is echoed. | TST-134, API-101 |
| FEAT-039-FR-06 | A test shall ingest SRC-05 and assert that API responses and captured log records contain no field other than study IDs (`resident_code`, `device_code`, `session_id`) that identifies a person — no name, date of birth or room-number field — and no feature value in logs. | TST-137, SEC-120, NFR-041, NFR-048, AGT-017 |
| FEAT-039-FR-07 | A static test shall assert that no response schema contains `password_hash`, `key_hash`, `payload`, `raw_body` or any `evaluation_ground_truth` column outside the Analytics `alarm_timing` block, and that no table has a column for names, dates of birth, contact details or audio. | DME-005, DME-020, DB-035, SEC-121, SEC-122 |
| FEAT-039-FR-08 | A static test shall fail if `openai`, `anthropic`, `langchain`, `google-generativeai`, `cohere` or `mistralai` appears in `backend/requirements*.txt` or `frontend/package.json`, and if a web-analytics, voice-service, notification-service or third-party-auth package named in TRD 22 TPS-080..TPS-085 is a dependency. | SEC-128, TPS-080..TPS-086, AGT-004 |
| FEAT-039-FR-09 | Tests shall assert that researchers cannot create, update, review or snooze any record (every researcher write call returns 403) and that a user cannot change their own role or deactivate themselves. | SEC-045, SEC-044 |
| FEAT-039-FR-10 | Exports (CSV) shall be tested to contain study IDs only and no staff-note text. | FR-245, NFR-050 |

## Inputs

- The complete API (all Phase 5 endpoint features via FEAT-038) and its OpenAPI document.
- Seeded users (admin, clinician, researcher, one inactive user), API keys with `ingest:write` and `pipeline:run`, a revoked key; SRC-05 fixture; `CORS_ORIGINS` test setting.

## Outputs

- Test modules under `tests/security/` and `tests/integration/test_auth_coverage.py` (marker `security` or `integration`), run on every PR.

## Data Flow

1. Session fixtures create the users and keys and a role-specific token for each caller.
2. A parametrised table (one entry per Table 4.13-A row and caller) drives HTTP calls through `TestClient`; path parameters use fixture ids (an existing alert, batch, run, user, resident R09).
3. Static tests load `app.openapi()`, `app.routes`, the SQLAlchemy metadata and dependency files and scan them.
4. The data-minimisation test captures logs with a handler on the root logger during an SRC-05 upload and response reads.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-038

- FEAT-038 (OpenAPI contract export and drift check): every endpoint exists and the document is final, so the matrix and the audio scan cover the whole API (and transitively all Phase 5 endpoint features, FEAT-020, FEAT-021).
- Downstream: FEAT-078 (CI runs the suite as a required check), FEAT-091 (audit evidence).

## Database Impact

None created or modified. Tests read `raw_sessions` counts (nothing stored on audio requests) and the SQLAlchemy metadata (column whitelist); fixtures insert users, keys and test data in rolled-back transactions.

## API Impact

None exposed. Consumes every endpoint E-01..E-32 and `/api/v1/openapi.json`.

## Frontend Impact

None: the frontend dependency scan reads `frontend/package.json` only; role-based hiding in the UI is tested by FEAT-064/FEAT-075 (SEC-043).

## Analytics Impact

None.

## Security Requirements

- This feature is the verification of TRD 12 §4.6 and §4.14; it must not weaken any production setting (test-only argon2 cost override only, TRD 12 §8).
- Tests use synthetic users and study IDs only (AGT-017); no real secrets in fixtures (AGT-016).

## Error Handling

- A failing matrix cell reports endpoint, caller and expected vs actual status.
- The suite must not be skipped; a skip without a `reason=` naming a requirement or OQ ID fails CI (TST-153).

## Logging Requirements

- The suite asserts on application logs (no feature values, no PII, no secrets: LOG-020..LOG-022) but adds no production logging.

## Testing Requirements

- Security (`pytest -m security tests/security`): TST-130 / SEC-041 matrix (AC-TST-05); TST-132 token and key attacks; TST-133 no-audio; TST-134 CORS; TST-137 data minimisation; static schema and dependency scans (DME-005, DME-020, DB-035, SEC-128, TPS-080..TPS-086).
- Integration: SEC-042 route coverage (`tests/integration/test_auth_coverage.py`).
- Referenced, executed elsewhere: TST-131 (FEAT-022), TST-135 (FEAT-086), TST-136 (FEAT-078).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-039-AC-01 | The matrix test passes for every row of TRD 13 Table 4.13-A and every caller type, with API keys tested in both scopes. | TST-130, SEC-041, AC-SEC-01, AC-TST-05 |
| FEAT-039-AC-02 | The route-coverage test passes on the delivered app and fails when a test-only route without an auth dependency is registered. | SEC-042, AC-SEC-02 |
| FEAT-039-AC-03 | A 61-minute-old JWT returns 401 `TOKEN_EXPIRED`; altered-signature and `alg: none` JWTs return 401 `TOKEN_INVALID`; a revoked key returns 401 `API_KEY_INVALID`; an API key without `ingest:write` on `POST /ingest` returns 403. | TST-132, AC-SEC-04 |
| FEAT-039-AC-04 | No OpenAPI property except `audio_quality_flag` contains "audio"; `Content-Type: audio/wav` to every endpoint returns 415 or 422 and `raw_sessions` count is unchanged. | TST-133, FR-015 |
| FEAT-039-AC-05 | A preflight from `https://evil.example` receives no `Access-Control-Allow-Origin`; from a configured origin the header echoes that origin. | TST-134 |
| FEAT-039-AC-06 | During and after an SRC-05 upload, no captured response or log record contains a field named like name, birth date or room number, and no log record contains a feature value. | TST-137, NFR-048 |
| FEAT-039-AC-07 | The static scans find no `password_hash`, `key_hash`, `payload`, `raw_body` or ground-truth column in response schemas (except `alarm_timing`) and no LLM, tracker, voice, notification or third-party-auth dependency. | DME-005, SEC-128, TPS-080..TPS-086 |
| FEAT-039-AC-08 | Every researcher write call (POST reviews, snooze, notes, ingest, pipeline run, users) returns 403, and a researcher CSV export of scores contains no note text. | SEC-045, FR-245 |

## Definition of Done

- All security tests pass on PostgreSQL 16 and are registered with marker `security` (TST-006); no skips.
- MVP-07 evidence (TST-130, TST-132..TST-134, TST-137 results) attached to the batch report; TST-131, TST-135, TST-136 referenced to their owning features.
- Coverage of `backend/` stays ≥ 85 %.

## Implementation Notes

- Drive the matrix from one data table in the test module that mirrors TRD 13 Table 4.13-A row by row, so a new endpoint without a row fails a completeness check against `app.routes`.
- For `alg: none`, build the token manually (header `{"alg":"none"}`, empty signature); PyJWT must be called with `algorithms=["HS256"]` so it rejects it (TRD 12 §8).
- Use `time-machine` to create the expired token deterministically (TST-005).
- The audio request test should send a small byte body to every route template with fixture path parameters; any 2xx is a failure.
- Run the data-minimisation test with `LOG_FORMAT=json` and parse each captured line; check keys and values against an allow-list of identifier fields.
