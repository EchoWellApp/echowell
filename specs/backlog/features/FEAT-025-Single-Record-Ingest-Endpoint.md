# FEAT-025 Single-record ingest endpoint (POST /api/v1/sessions)

| Field | Value |
|---|---|
| Epic | Data Processing |
| Build phase | Phase 5 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-023, FEAT-022, FEAT-024, FEAT-015 |
| Status | Not Started |

## Purpose

Implement the device-facing door of EchoWell, `POST /api/v1/sessions`: accept one feature record from a device holding an `ingest:write` API key, reject invalid records into `ingest_rejections` with a 422 listing every violation, store every valid arrival (including repeats) in the immutable raw store under the per-`session_id` advisory lock, commit it, run the pipeline synchronously for the affected residents and tell the caller what happened to the record — `usable`, `set_aside`, `quarantined`, `duplicate`, or `pending` when the record is safe but processing failed. This is the path used by the demo's live check-in.

## Business Context

- BR-01: per-session feature records arrive from devices without audio (FR-001, FR-015, ARC-001, ARC-002).
- BR-02: every valid arrival is kept unaltered and committed before processing; a failed run never loses or alters it (FR-005, DB-022, ARC-021, ARC-025, D-52).
- BR-03: a repeat `session_id` is stored and reported as `duplicate` without re-running the pipeline (FR-008).
- SRC-15 demo step 4: a posted check-in is processed within the same request and shows on the dashboard (ARC-022).

## Referenced TRDs

- TRD 10 ING-001..ING-004, ING-010, ING-012, ING-029, ING-030, ING-033, ING-038, ING-057; AC-ING-04, AC-ING-05, AC-ING-09, AC-ING-10, AC-ING-11.
- TRD 05 API-030..API-032, API-041..API-047, API-056.
- TRD 17 LOG-050..LOG-052, LOG-054.
- TRD 06 DB-021 (b), DB-022.
- TRD 01 ARC-020..ARC-025; AC-ARC-03, AC-ARC-06.
- TRD 19 §4.3 E-05; schemas `IngestRecord`, `IngestResult`.
- TRD 02 FR-001, FR-005, FR-007, FR-008, FR-015, FR-028.
- TRD 13 TST-037, TST-043, TST-044, TST-045, TST-137; TRD 05 AC-API-05..AC-API-07.
- TRD 24 D-52.

## Scope

- `backend/api/sessions.py` (existing skeleton file) and `backend/services/ingestion.py` (existing skeleton file):
  - `POST /api/v1/sessions` (E-05): `application/json` only (other types, including `audio/*`, → 415 `UNSUPPORTED_MEDIA_TYPE`), body ≤ 64 KB, authenticated by `get_api_key("ingest:write")`, rate-limited per key (FEAT-022).
  - Read the raw request body directly (not via FastAPI body binding) and parse JSON; the OpenAPI operation still references `IngestRecord` through `openapi_extra`.
  - Validate through FEAT-023 (`validate(raw, source="json", principal=…)`).
  - Invalid: insert one `ingest_rejections` row (`raw_body` = exact received body, `errors` identical to the response, `api_key_id`, `ingest_batch_id` NULL), commit, return 422 Problem with the ING-004 code precedence; device-key mismatch → 403 `DEVICE_KEY_MISMATCH` with the body stored in `ingest_rejections`.
  - Valid: in one transaction take `pg_advisory_xact_lock(advisory_key('session', session_id))`, check `raw_sessions` for an earlier arrival of the `session_id`, insert the arrival (`payload` = parsed JSON before mapping, typed canonical columns, `received_at` server UTC, new `arrival_seq`, `api_key_id`, `ingest_batch_id` NULL, `ingest_warnings`), update `devices.firmware_version_last` when this record is newer, commit.
  - Repeat `session_id`: return 200 `IngestResult` with `status_after_processing = "duplicate"`, `reasons = ["session_id already received"]`, `pipeline_run_id = null`; no pipeline run.
  - First arrival: after commit, call `pipeline_runner.run(scope, trigger="ingest", profile=PIPELINE_PROFILE, as_of=None)` synchronously for {record's resident} ∪ {residents with an assignment to the record's device valid on the record's local date}; return 201 `IngestResult` (`raw_session_id`, `arrival_seq`, `session_id`, `status_after_processing` ∈ {usable, set_aside, quarantined}, `reasons`, `pipeline_run_id`).
  - Pipeline failure: run recorded `failed`, error logged with the request ID, response 201 with `status_after_processing = "pending"`; the raw row is untouched.
- Logging: `ingest_record_rejected` (WARNING), `ingest_duplicate` (INFO), `ingest_request` (one per request) with identifiers and counts only.

## Out of Scope

- `POST /api/v1/ingest` and `GET /api/v1/ingest/batches/{id}` (FEAT-026).
- The pipeline stage execution that determines `usable`/`set_aside`/`quarantined` (FEAT-053 executor); until FEAT-053 lands, the default executor of FEAT-024 fails runs, so first arrivals return `pending` — which exercises the D-52 path.
- Duplicate status inside `processed_sessions` and warning `duplicate_payload_differs` (FEAT-041, ING-037).
- Exclusion of records timestamped after the run's `as_of` (FEAT-052).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-025-FR-01 | `POST /api/v1/sessions` shall accept exactly one record as `application/json` (≤ 64 KB) authenticated by `X-API-Key` with scope `ingest:write`. | ING-001, API-030, FR-001 |
| FEAT-025-FR-02 | The handler shall read the raw body itself so invalid bodies can be stored verbatim; the OpenAPI operation references `IngestRecord` via `openapi_extra`. | API-031 |
| FEAT-025-FR-03 | An invalid record shall return 422 Problem with `type` `urn:echowell:error:<CODE>` (first applicable of `UNSUPPORTED_SCHEMA_VERSION`, `UNKNOWN_RESIDENT`, `UNKNOWN_DEVICE`, `RESIDENT_WITHDRAWN`, `SESSION_ID_MISMATCH`, else `VALIDATION_ERROR`) and `errors[]` listing every violation; write one `ingest_rejections` row whose `errors` equal the response `errors` and whose `raw_body` is the exact body; write nothing to `raw_sessions`. | ING-004, API-041, ARC-020, FR-028 |
| FEAT-025-FR-04 | A key bound to another device shall get 403 `DEVICE_KEY_MISMATCH`, with the body stored in `ingest_rejections`. | API-040 |
| FEAT-025-FR-05 | Rejected records shall never enter `raw_sessions` nor be processed; a corrected re-send is a new arrival. | ING-033 |
| FEAT-025-FR-06 | A valid record shall be inserted into `raw_sessions` with `payload` equal to the JSON body as received (after parsing, before name mapping), typed column copies, `received_at` = server UTC time, a new `arrival_seq`, and committed before any pipeline processing starts. | API-042, ING-029, ARC-021, FR-005, DB-022 |
| FEAT-025-FR-07 | The service shall take the session advisory lock (`advisory_key('session', session_id)`) before checking `raw_sessions` for an earlier arrival and inserting, so concurrent arrivals of one `session_id` are ordered by `arrival_seq` and only the first is new. | ING-038, API-043, DB-021 |
| FEAT-025-FR-08 | A repeat `session_id` shall be stored and answered 200 with `status_after_processing = "duplicate"`, `reasons = ["session_id already received"]`, `pipeline_run_id = null`, without triggering the pipeline. | ING-003, API-044, FR-008 |
| FEAT-025-FR-09 | A first arrival shall trigger the pipeline synchronously in the same request with `trigger = ingest` for the record's resident plus every resident assigned to the record's device on the record's local date; `as_of` follows the precedence of FEAT-024. | API-045, ING-002, ARC-022 |
| FEAT-025-FR-10 | After the run, the response shall be 201 with `raw_session_id`, `arrival_seq`, `session_id`, `status_after_processing` (usable, set_aside, quarantined), `reasons` and `pipeline_run_id`. | API-046, ING-002, FR-007 |
| FEAT-025-FR-11 | If the synchronous run raises, the raw record stays stored, the run is recorded `failed`, the error is logged with the request ID, and the response is 201 with `status_after_processing = "pending"`; the next run processes the record. | API-047, ARC-025, LOG-054, D-52 |
| FEAT-025-FR-12 | Single-record ingest shall create no `ingest_batches` row (`ingest_batch_id` NULL on both tables) and write no audit row of its own; provenance is `raw_sessions.api_key_id`. | API-032, ING-010 |
| FEAT-025-FR-13 | Content types other than `application/json` (including any `audio/*`) shall be rejected with 415; no endpoint accepts, returns or replays audio. | ING-012, FR-015 |
| FEAT-025-FR-14 | `raw_sessions` stays insert-only: the service never updates or deletes a raw row. | ING-030 |
| FEAT-025-FR-15 | With the database unavailable, the endpoint shall return 503 `SERVICE_UNAVAILABLE` with `Retry-After: 30` and persist no partial record (single transaction per record). | LOG-052 |
| FEAT-025-FR-16 | Responses and logs shall never echo feature values; logs carry only `session_id`, resident and device codes, outcome and error codes. | API-056, ING-057 |
| FEAT-025-FR-17 | A rejected record shall be logged once at WARNING `ingest_record_rejected` with `session_id` and `resident_code` when parseable and error locations; a duplicate at INFO `ingest_duplicate` with `session_id`; every request emits one `ingest_request` event with `request_id`, `endpoint`, `api_key_id`, `record_count`, `accepted`, `rejected`, `duplicates`, `warning_count`, `duration_ms`. | LOG-050, LOG-051, ING-057 |
| FEAT-025-FR-18 | Dashboard reads never invoke the pipeline; only ingest and the run triggers do. | ARC-024 |

## Inputs

- HTTP request with `X-API-Key` and a JSON body of schema v0.1 (`IngestRecord`).
- Validation (FEAT-023), principal (FEAT-020), runner (FEAT-024), advisory-lock helper (FEAT-013).

## Outputs

- `raw_sessions` row (valid) or `ingest_rejections` row (invalid); `pipeline_runs` row from the synchronous run; `IngestResult` (201/200) or Problem (422/403/415/429/503).

## Data Flow

Request → request ID, size and media-type guards → `get_api_key("ingest:write")` → rate limit → raw body read and JSON parsed → validation → invalid: rejection row committed, 422/403 → valid: transaction { session lock → duplicate check → insert raw row → firmware update } commit → duplicate: 200 → first arrival: runner (`trigger = ingest`, resident ∪ device co-residents) → executor result gives the record's status and reasons → 201; runner failure → 201 `pending`.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-023, FEAT-022, FEAT-024, FEAT-015

- FEAT-023 validates the record and resolves resident and device.
- FEAT-022 rate-limits the endpoint per API key.
- FEAT-024 provides `pipeline_runner.run` for the synchronous resident-scoped run.
- FEAT-015 provides the audit writer used by the runner's `pipeline.run.*` events triggered here.

Features that build directly on this one (BACKLOG.md §4): FEAT-026, FEAT-054.

## Database Impact

- Tables written: `raw_sessions` (INSERT), `ingest_rejections` (INSERT), `devices` (`firmware_version_last` UPDATE), `pipeline_runs` (via runner), `audit_logs` (runner events).
- Tables read: `raw_sessions` (duplicate check), `residents`, `devices`, `device_assignments`, `api_keys`, `config_parameters`.
- Locks: transaction-scoped `advisory_key('session', session_id)`.

## API Impact

- Exposed: E-05 `POST /api/v1/sessions` — 201 `IngestResult`, 200 `IngestResult` (duplicate); 422 `VALIDATION_ERROR`, `UNSUPPORTED_SCHEMA_VERSION`, `UNKNOWN_RESIDENT`, `UNKNOWN_DEVICE`, `RESIDENT_WITHDRAWN`, `SESSION_ID_MISMATCH`; 403 `DEVICE_KEY_MISMATCH`; 415 `UNSUPPORTED_MEDIA_TYPE`; 401/403 auth; 429 `RATE_LIMITED`; 503 `SERVICE_UNAVAILABLE`.
- Consumes the internal runner interface (no HTTP).

## Frontend Impact

None. The dashboard reflects new check-ins on its next fetch (demo step 5 is verified by FEAT-090).

## Analytics Impact

None computed here; the synchronous run executes the analytics pipeline through FEAT-024/FEAT-053.

## Security Requirements

- Authentication: API key with scope `ingest:write` only (TRD 12 §4.6: user tokens get 401); device-bound keys restricted to their device (SEC-023).
- No audio: `extra="forbid"` validation and media-type guard (FR-015, ARC-003).
- No feature values in responses, logs or audit (API-056, LOG-021).
- Rate limit per key (SEC-090).

## Error Handling

| Failure | Behaviour | Trace |
|---|---|---|
| Invalid record | 422 Problem; `ingest_rejections` row; nothing in `raw_sessions` | ING-004, API-041 |
| Bound key mismatch | 403 `DEVICE_KEY_MISMATCH`; body stored in `ingest_rejections` | API-040 |
| Non-JSON or audio content type | 415 | ING-012 |
| Database down | 503 + `Retry-After: 30`; nothing persisted | LOG-052 |
| Pipeline run fails after commit | 201 `pending`; run `failed`; raw row unchanged; next run processes it | API-047, ARC-025, D-52 |
| Concurrent same `session_id` | One 201 (or pending), one 200 duplicate | AC-ING-09, DB-021 |

## Logging Requirements

- `ingest_record_rejected` WARNING, `ingest_duplicate` INFO, `ingest_request` per request (LOG-050, LOG-051, ING-057).
- Pipeline failure logged with `request_id` and `pipeline_run_id` (API-047, LOG-034).
- Audit: no row for the single record itself (API-032); the runner writes `pipeline.run.started`/`pipeline.run.finished`.

## Testing Requirements

- Integration (`tests/integration/api/test_sessions.py`, marker `integration`):
  - TST-043: valid SRC-05 record → 201, exactly one `raw_sessions` row whose `payload` equals the request body.
  - TST-044 / AC-API-05: repeat `session_id` → 200 `duplicate`, a second `raw_sessions` row, derived results unchanged, no new run.
  - TST-045 / AC-API-06: invalid record (R11) → 422 `UNKNOWN_RESIDENT`, one `ingest_rejections` row, no raw row.
  - AC-API-07 / AC-ING-04: extra field `audio_base64` → 422 `VALIDATION_ERROR` with `errors[0].code` `extra_forbidden`.
  - AC-ING-05, AC-ING-10 (withdrawn resident → 422 `RESIDENT_WITHDRAWN`, "resident withdrawn").
  - TST-037 / AC-ING-11: fault-injected executor → 201 `pending`, raw row stored, the next run processes it.
  - AC-ARC-03: one valid record → 201 with `status_after_processing`, one `raw_sessions` row, one `pipeline_runs` row with `trigger = ingest` and `status = succeeded` (requires FEAT-053; in Phase 5 the same test asserts `pending` with a `failed` run).
  - 415 for `Content-Type: audio/wav` and `text/plain`; 503 with the database stopped; 403 `DEVICE_KEY_MISMATCH`.
- Integration (`tests/integration/pipeline/test_concurrent_ingest.py`): AC-ING-09 and DB-021 (two concurrent POSTs of one `session_id`: one 201/pending, one 200 duplicate); AC-ARC-06 (concurrent R02 and R03 on shared D02 complete without deadlock).
- Security: TST-137 (responses and logs for SRC-05 ingestion contain only study IDs); log capture shows no feature value (API-056).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-025-AC-01 | Posting SRC-05 row R09-20261021-01 with a valid `ingest:write` key returns 201 with `raw_session_id`, `arrival_seq`, `session_id`, `status_after_processing`, `reasons`, `pipeline_run_id`, and creates exactly one `raw_sessions` row whose `payload` equals the posted JSON. | TST-043, API-042, API-046 |
| FEAT-025-AC-02 | Posting the same record again returns 200 with `status_after_processing = "duplicate"`, `reasons = ["session_id already received"]`, `pipeline_run_id = null`, adds one `raw_sessions` row and creates no `pipeline_runs` row. | TST-044, AC-API-05, API-044 |
| FEAT-025-AC-03 | Posting a record with `resident_id` R11 returns 422 `UNKNOWN_RESIDENT`, creates one `ingest_rejections` row (with `errors` equal to the response `errors` and `ingest_batch_id` NULL) and no `raw_sessions` row. | TST-045, AC-API-06, API-041 |
| FEAT-025-AC-04 | Posting a record with an extra field `audio_base64` returns 422 `VALIDATION_ERROR` whose `errors[0].code` is `extra_forbidden`; posting with `Content-Type: audio/wav` returns 415 and stores nothing. Verified by: Integration (`tests/integration/api/test_sessions.py`; TST-043, TST-044, TST-045). | AC-API-07, ING-012, FR-015 |
| FEAT-025-AC-05 | With the executor forced to raise, the POST returns 201 with `status_after_processing = "pending"`, the raw row exists, the run row is `failed`; a subsequent successful run processes the record. | TST-037, AC-ING-11, D-52 |
| FEAT-025-AC-06 | Two concurrent POSTs of one `session_id` yield exactly one non-duplicate response and one 200 `duplicate`, with `arrival_seq` order matching the verdicts. Verified by: Integration (`tests/integration/pipeline/test_concurrent_ingest.py`). | AC-ING-09, DB-021 |
| FEAT-025-AC-07 | A record for a withdrawn resident returns 422 `RESIDENT_WITHDRAWN` with detail "resident withdrawn". Verified by: Integration (`tests/integration/api/test_sessions.py`; TST-043, TST-044, TST-045). | AC-ING-10 |
| FEAT-025-AC-08 | Captured logs for a valid, an invalid and a duplicate POST contain one `ingest_request` event each, one `ingest_record_rejected` WARNING, one `ingest_duplicate` INFO, and no feature value or API key. Verified by: Security (log capture shows no feature value (API-056)). | LOG-050, LOG-051, ING-057, API-056 |
| FEAT-025-AC-09 | With the database stopped, the POST returns 503 `SERVICE_UNAVAILABLE` with `Retry-After: 30`. Verified by: Integration (`tests/integration/api/test_sessions.py`). | LOG-052 |

## Definition of Done

- All FEAT-025 acceptance criteria pass; the TRD 25 §4.6 Phase 5 required tests for this endpoint (duplicate 200, withdrawn 422, pending on pipeline failure) pass.
- E-05 appears in the OpenAPI document with `IngestRecord`/`IngestResult`; delivered in the Phase 5 checkpoint PR of Block 3.

## Implementation Notes

- Commit the raw insert before calling the runner, and run the pipeline in a separate transaction scope (per resident, FEAT-053) so a failing run cannot roll back the raw row (DB-022).
- Use `request.body()` and `json.loads`; keep the exact bytes for `raw_body` on rejection (API-031).
- Compute the device co-resident scope from `device_assignments` valid on the record's facility-local date (`zoneinfo`, ING-027).
- `TST-121` (p95 ≤ 1,000 ms including the synchronous run) is measured by FEAT-079; keep the synchronous run resident-scoped.
