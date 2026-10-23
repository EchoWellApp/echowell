# FEAT-026 Batch and CSV ingest endpoints (POST /api/v1/ingest, GET /api/v1/ingest/batches/{id})

| Field | Value |
|---|---|
| Epic | Data Processing |
| Build phase | Phase 5 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-025 |
| Status | Not Started |

## Purpose

Give Team 1 devices (API key) and study admins (dashboard upload) a way to submit many feature records at once, either as a JSON array or as a CSV file in the exact SRC-05 schema v0.1 format, and let admins and researchers read back the result of each batch. This is the path used to load the pipeline test input (SRC-05, 283 arrivals) for the R01–R10 answer-key run, the admin "Upload data" tab, the seed command and later the Team 1 calibration dataset. Every accepted arrival lands unaltered in the immutable raw store in file order, every invalid record is kept in `ingest_rejections`, and one background pipeline run is scheduled for the affected residents.

## Business Context

- BR-01 (devices send extracted features only, never audio): batch ingest accepts only JSON and CSV feature records; any other media type is refused (415).
- BR-02 (raw store kept as received): accepted records, duplicates included, are stored in `raw_sessions` with `payload` as received; rejected ones go to `ingest_rejections`.
- BR-03 (duplicates kept but marked): arrival order equals file or array order, so R04's late copy (arrival 283) is the duplicate.
- BR-15 (reproduce the answer key): uploading SRC-05 returns accepted 283, rejected 0, duplicates 2 (TST-046) and feeds the Tier B validation run (TDV-031).
- BR-16 (traceability): every batch is audited (`ingest.batch.received`) and records who uploaded it.
- FRs covered (BACKLOG.md): FR-002, FR-003, FR-004, FR-009, FR-010, FR-011, FR-032.

## Referenced TRDs

- TRD 10 ING-005..ING-009 (batch semantics, envelope errors, duplicates count, batch read-out), ING-031, ING-032 (CSV format, input order, row numbers), ING-053..ING-056 (answer-key and legacy SRC-06 rejection), ING-058 (audit, `api_keys.last_used_at`); context rows ING-012 (415), ING-029 (raw insert), ING-037 and ING-023 (`duplicate_payload_differs` warning), ING-057 (ingest log event), ING-059 (seed uses the same path).
- TRD 05 API-048..API-055 (content types, auth, limits, per-record validation, 202 body, background run, batch read-out, `device_assignment_mismatch`), API-031 (raw body read), API-041..API-043 (rejection storage, raw insert, session lock), API-056 (no feature values in responses or logs), API-104 (5 MB body limit), §4.7 error catalogue.
- TRD 19 §4.3 E-06 `POST /api/v1/ingest` and E-07 `GET /api/v1/ingest/batches/{id}`; schemas `IngestBatchRequest`, `IngestBatchAccepted`, `IngestBatch`, `IngestRejection`, `ProblemFieldError`.
- TRD 20 §4.6.7 `ingest_batches`, §4.6.8 `ingest_rejections`, §4.6.9 `raw_sessions`; TRD 23 §4.2.7, §4.2.8.
- TRD 12 §4.6 role matrix (POST /ingest: admin, API key `ingest:write`; GET /ingest/batches/{id}: admin, researcher), §4.12 audit vocabulary (`ingest.batch.received`).
- TRD 17 LOG-050, LOG-051, LOG-052, LOG-053 (ingest logs), LOG-021 (no bodies or feature values in logs).
- TRD 13 TST-046, TST-047, TST-124; TRD 14 TDV-005, TDV-031, VC-G11; AC-API-01, AC-API-17, AC-ING-01, AC-ING-03, AC-ING-06.
- TRD 24 D-25 (SRC-06 is never ingest input), D-09 (duplicates stored, first arrival kept).
- TRD 23 DME-018 (SRC-06 legacy data is mapped to no table; 422 rejections only).

## Scope

- Router `backend/api/ingest.py` with `POST /api/v1/ingest` and `GET /api/v1/ingest/batches/{id}`, and service function `services.ingestion.ingest_batch` plus `services.ingestion.get_batch` (TRD 05 §4.12).
- Content negotiation: `application/json` body `{"records": [...]}` or `multipart/form-data` with one part named `file` holding a CSV; everything else 415.
- Envelope checks that store nothing: malformed JSON or missing `records` array, zero records, more than 5,000 records or a body over 5 MB, CSV header mismatch (including the answer-key columns and the legacy SRC-06 header), `.xlsx` upload.
- Per-record validation through the FEAT-023 validator and per-record storage through the FEAT-025 insert path (session advisory lock, `raw_sessions` insert with `arrival_seq` in input order, `ingest_rejections` row per invalid record).
- One `ingest_batches` row per request with counts, one `audit_logs` row, `api_keys.last_used_at` update, 202 response, one background pipeline run scheduled after commit.
- The batch read-out with counts, linked pipeline run and rejections.

## Out of Scope

- Single-record ingest `POST /api/v1/sessions` and the synchronous run (FEAT-025).
- The field-level validation rules, feature-name mapping and schema-version registry (FEAT-023).
- The body of `services.pipeline_runner.run` that persists derived results (FEAT-053) and the wiring/verification of ingest-triggered runs end to end (FEAT-054).
- The admin upload UI (FEAT-074) and the `seed test_v0_1` command that calls this code path with source `seed` (FEAT-055, ING-059).
- Rate limiting configuration (FEAT-022) and authentication dependencies (FEAT-020, FEAT-021); this feature only attaches them.
- Any converter from the legacy SRC-06 schema (explicitly excluded by ING-056).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-026-FR-01 | `POST /api/v1/ingest` shall accept `application/json` `{"records": [IngestRecord, ...]}` or `multipart/form-data` with one part named `file` holding a UTF-8 CSV; any other content type, including `audio/*`, shall return 415 `UNSUPPORTED_MEDIA_TYPE`, and an `.xlsx` file shall return 415. | API-048, ING-005, ING-012, ING-053; FR-002, FR-003 |
| FEAT-026-FR-02 | The endpoint shall be authorised for an API key with scope `ingest:write` (via `get_ingest_principal`) or a JWT user with role `admin`; clinicians and researchers receive 403 `FORBIDDEN`, missing credentials 401. | API-049, API-015, ING-005; FR-004; TRD 12 §4.6 |
| FEAT-026-FR-03 | The handler shall read the raw body itself (no FastAPI body-model binding) so that invalid records can be stored verbatim; the OpenAPI operation shall still reference `IngestBatchRequest` and the multipart `file` part through `openapi_extra`. | API-031; TRD 19 §8 |
| FEAT-026-FR-04 | Envelope errors shall store nothing in `raw_sessions`, `ingest_rejections` or `ingest_batches`: malformed JSON or missing `records` array → 422 `VALIDATION_ERROR`; zero records → 422 `EMPTY_BATCH`; more than 5,000 records or a file or body over 5 MB → 413 `PAYLOAD_TOO_LARGE`. | ING-007, API-050, API-104 |
| FEAT-026-FR-05 | A CSV shall be UTF-8 (optional BOM), comma-separated, RFC 4180 quoted, LF or CRLF; its header, after feature-name mapping, shall consist of exactly the 30 schema v0.1 fields in any order, else the whole file is rejected with 422 `CSV_HEADER_MISMATCH` whose `errors` list the missing and extra column names, and nothing is stored. | ING-031, API-048, API-050; FR-003 |
| FEAT-026-FR-06 | A CSV header containing any of `expected_status`, `expected_reason`, `expected_morning`, `expected_epoch`, `in_baseline`, `error_mode_tested`, `test_case`, `arrival_order` shall be rejected as a whole with 422 `CSV_HEADER_MISMATCH` and `errors[].code` `extra_forbidden` naming those columns. | ING-053 |
| FEAT-026-FR-07 | The legacy SRC-06 file (`echowell_mock_data_500.csv`, columns entry_id, resident_id, datetime, health_wifi, health_ping, health_mic_noise, device_id, speech_len, speech_feature_1..3) shall be rejected as a whole with 422 `CSV_HEADER_MISMATCH`; no converter exists. | ING-055, ING-056, API-050, D-25; FR-032 |
| FEAT-026-FR-08 | Within a valid envelope each record shall be validated independently by the FEAT-023 validator; record-level errors shall not fail the batch (202 also when `accepted = 0`). | ING-006, ING-007, API-051; FR-011 |
| FEAT-026-FR-09 | Valid records shall be inserted into `raw_sessions` in input order (JSON array order or CSV row order) so that `arrival_seq` increases in that order; `payload` is the record as received (for CSV an object of header → cell text before mapping); the session advisory lock of DB-021 (b) is taken before the duplicate check of each record. | ING-032, ING-029, API-042, API-043, API-051; FR-011 |
| FEAT-026-FR-10 | Each invalid record shall produce one `ingest_rejections` row linked to the batch with `raw_body` as received, `errors` identical to the validator errors, and `row_number` = the 1-based position of the record in the batch (CSV: data row, header excluded; JSON: array position); it shall never be written to `raw_sessions`. | ING-032, API-041, API-051, D-84 |
| FEAT-026-FR-11 | One `ingest_batches` row shall be created per request with `source` = `api_batch` (JSON) or `csv_upload` (CSV), `filename` (required for CSV), `record_count`, `accepted_count` (duplicates included), `rejected_count`, `duplicate_count`, `uploaded_by` = admin user id (null for API keys), `api_key_id` (null for users) and `received_at`. | ING-006, API-049; TRD 20 §4.6.7; FR-010 |
| FEAT-026-FR-12 | `duplicates` shall count accepted records whose `session_id` was already in `raw_sessions` before the batch or appears earlier in the same batch; a later copy whose field values differ shall carry warning `duplicate_payload_differs` in `raw_sessions.ingest_warnings`. | ING-008, ING-037, ING-023 |
| FEAT-026-FR-13 | The batch transaction shall write one `audit_logs` row with action `ingest.batch.received`, entity `ingest_batch` / batch id, actor `api_key` or `user`, and details `{source, record_count, accepted, rejected, duplicates}`; `api_keys.last_used_at` shall be updated when an API key authenticated the call. | ING-058; TRD 12 §4.12 |
| FEAT-026-FR-14 | After the batch transaction commits, the handler shall schedule exactly one pipeline run through FastAPI `BackgroundTasks` calling `services.pipeline_runner.run` with `trigger = ingest` and scope = residents that received a first-arrival record in the batch plus their co-assigned residents (API-045 rule); the run row is created with status `running` before the response so that its id is returned. | API-053, ING-006; TRD 07 ANL-044 |
| FEAT-026-FR-15 | The response shall be 202 `IngestBatchAccepted` `{ingest_batch_id, source, accepted, rejected, duplicates, pipeline_run_id}` where `pipeline_run_id` is null when no first-arrival record was accepted; for SRC-05 the values are accepted 283, rejected 0, duplicates 2. | API-052, ING-006; TRD 19 E-06; FR-009 |
| FEAT-026-FR-16 | A valid record whose device is known but not assigned to the resident on the record's local date shall be accepted; the warning `device_assignment_mismatch` is added to `pipeline_runs.warnings` by the pipeline run (not by this endpoint). | API-055 |
| FEAT-026-FR-17 | `GET /api/v1/ingest/batches/{id}` (admin, researcher) shall return `IngestBatch` with source, filename, the four counts, `uploaded_by`, `received_at`, linked `pipeline_run_id` and `rejections[]` (`row_number`, `session_id` if parseable, `received_at`, `errors`), never `raw_body`; an unknown id returns 404 `BATCH_NOT_FOUND` and a malformed uuid 422 `INVALID_QUERY_PARAMETER`. | ING-009, API-054; TRD 19 E-07; DME-005 |
| FEAT-026-FR-18 | Responses and logs shall never echo feature values or payloads; logs carry only identifiers, counts and error locations. | API-056, LOG-021 |
| FEAT-026-FR-19 | The SRC-06 legacy mock file shall be mapped to no table: submitting it produces 422 rejections only and no `raw_sessions` row. | DME-018, D-25 |

## Inputs

- HTTP `POST /api/v1/ingest` with header `X-API-Key` (scope `ingest:write`) or `Authorization: Bearer <JWT>` (admin), body JSON `{"records": [...]}` (1..5,000 `IngestRecord` objects, ≤ 5 MB) or multipart part `file` (CSV, ≤ 5 MB, ≤ 5,000 data rows, header = SRC-05 header after mapping).
- Configuration rows `supported_schema_versions` and `feature_name_map` of the active profile (read by the FEAT-023 validator).
- Master data `residents`, `devices`, `device_assignments`, `api_keys` (FEAT-009, FEAT-016, FEAT-017).
- HTTP `GET /api/v1/ingest/batches/{id}` with an admin or researcher JWT.

## Outputs

- `raw_sessions` rows (one per accepted arrival, duplicates included) with `ingest_batch_id`, `arrival_seq`, `received_at`, `payload`, typed columns and `ingest_warnings`.
- `ingest_rejections` rows (one per invalid record) with `ingest_batch_id`, `api_key_id`, `row_number` (batch position, CSV and JSON), `raw_body`, `errors`.
- One `ingest_batches` row, one `audit_logs` row, updated `api_keys.last_used_at`.
- One `pipeline_runs` row (status `running`, trigger `ingest`) when at least one first arrival was accepted.
- 202 `IngestBatchAccepted` body, `IngestBatch` body for the read-out, `application/problem+json` bodies for errors.
- Log events `ingest_record_rejected` (WARNING, per rejected record), `ingest_duplicate` (INFO, per duplicate), `ingest_batch_completed` (INFO), `ingest_request` (INFO).

## Data Flow

1. Request passes the request-ID, body-size, CORS and rate-limit middleware (FEAT-018, FEAT-019, FEAT-022); `get_ingest_principal` resolves the API key or admin user (FEAT-020, FEAT-021).
2. `ingest.py` reads the raw body, checks the content type and the envelope (JSON parse, `records` array, record count, size; for CSV: decode UTF-8 with optional BOM, `csv.DictReader`, map the header through `feature_name_map`, compare with the 30 canonical fields and the forbidden answer-key columns). Any envelope error returns the Problem response and writes nothing.
3. `services.ingestion.ingest_batch` opens one database transaction, inserts the `ingest_batches` row, then iterates the records in input order: validate (FEAT-023) → on failure insert `ingest_rejections` (with `row_number` = batch position) → on success take `pg_advisory_xact_lock(advisory_key('session', session_id))`, check for an earlier arrival of the same `session_id` (in `raw_sessions` or earlier in this batch), insert into `raw_sessions` (FEAT-025 insert helper).
4. The service updates the batch counts, writes the `ingest.batch.received` audit row and `api_keys.last_used_at`, determines the scope (residents with a first arrival plus residents co-assigned to their devices on the record's local date) and, when the scope is not empty, creates the `pipeline_runs` row through the FEAT-024 interface; the transaction commits.
5. The router registers `services.pipeline_runner.run(scope, trigger="ingest", ...)` with `BackgroundTasks`, returns 202, and logs `ingest_batch_completed`.
6. The background task runs the pipeline after the response; its results become visible through the read endpoints once the run is `succeeded` (`meta.as_of`).
7. `GET /ingest/batches/{id}` loads the batch, its rejections and the linked run id through `backend/repositories/ingest_repository.py` (docs/design/Database_ERD.md §5) and maps them to `IngestBatch`.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-025

- FEAT-025 (Single-record ingest endpoint): provides the validated-record insert path (`raw_sessions` insert, session advisory lock, rejection storage, payload-as-received rules) that this feature reuses per record, and transitively FEAT-023 (validator), FEAT-022 (ingest rate limit), FEAT-024 (`pipeline_runner.run` interface) and FEAT-015 (audit writer).

Features that build directly on this one (BACKLOG.md §4): FEAT-038, FEAT-054, FEAT-055, FEAT-074.

## Database Impact

- Tables written: `ingest_batches` (all columns of TRD 20 §4.6.7; CHECKs `ingest_batches_counts_ck`, `ingest_batches_actor_ck`, `ingest_batches_filename_ck` must hold), `ingest_rejections` (`ingest_batch_id`, `api_key_id`, `row_number`, `received_at`, `raw_body`, `errors`), `raw_sessions` (insert only), `audit_logs` (insert only), `api_keys.last_used_at` (update), `pipeline_runs` (insert of the `running` row through FEAT-024).
- Tables read: `residents`, `devices`, `device_assignments`, `api_keys`, `config_parameters`, `raw_sessions` (duplicate check), `ingest_batches`, `ingest_rejections`, `pipeline_runs` (read-out).
- Tables created or altered: none (all created by FEAT-010, FEAT-011, FEAT-012).
- Role: `echowell_app` via `DATABASE_URL` only (INSERT/SELECT on `raw_sessions`, `ingest_rejections`, `audit_logs`).

## API Impact

- Exposed: `POST /api/v1/ingest` (E-06; 202 `IngestBatchAccepted`; errors 401, 403, 413 `PAYLOAD_TOO_LARGE`, 415 `UNSUPPORTED_MEDIA_TYPE`, 422 `EMPTY_BATCH`, `CSV_HEADER_MISMATCH`, `VALIDATION_ERROR`, 429 `RATE_LIMITED`).
- Exposed: `GET /api/v1/ingest/batches/{id}` (E-07; 200 `IngestBatch`; errors 401, 403, 404 `BATCH_NOT_FOUND`, 422 `INVALID_QUERY_PARAMETER`).
- Consumed (internal): `services.pipeline_runner.run` (FEAT-024 interface), `services.validation` (FEAT-023), `services.audit_service.record` (FEAT-015).
- `IngestBatch` and `IngestBatchAccepted` carry no `meta` block (OAS-017).

## Frontend Impact

None in this feature. Consumers are the `/admin` "Upload data" tab (`AdminPanel`, client functions `uploadIngestCsv(file)` and `getIngestBatch(id)`, TRD 04 §4.6.2), delivered by FEAT-074.

## Analytics Impact

None directly: no algorithm runs in the request. The feature fixes the arrival order (`arrival_seq` = file order) that duplicate detection (FEAT-041, ING-034) relies on, and triggers one background run of the analytics pipeline through the runner.

## Security Requirements

- Authentication: API key (SHA-256 hash lookup, active, scope `ingest:write`, optional device binding: `DEVICE_KEY_MISMATCH` per record per FEAT-023/API-040) or admin JWT; researcher JWT or admin JWT for the read-out (TRD 12 §4.6, TRD 13 Table 4.13-A rows POST /ingest and GET /ingest/batches/{id}).
- Authorisation: clinicians 403 on both endpoints; researchers 403 on POST; API keys 401 on the read-out.
- No audio: only JSON and CSV accepted (ING-012, AGT-006).
- Data minimisation: no response or log contains feature values, payloads or `raw_body` (API-056, DME-005, LOG-021); audit details hold counts only (SEC-104).
- Interim stack holds synthetic and test data only (AGT-014); nothing in this feature loads real data.

## Error Handling

| Failure | Response | Stored |
|---|---|---|
| Unsupported content type or `.xlsx` | 415 `UNSUPPORTED_MEDIA_TYPE` | nothing |
| Malformed JSON, missing `records` | 422 `VALIDATION_ERROR` | nothing |
| Zero records | 422 `EMPTY_BATCH` | nothing |
| > 5,000 records or > 5 MB | 413 `PAYLOAD_TOO_LARGE` | nothing |
| CSV header mismatch, answer-key columns, SRC-06 file | 422 `CSV_HEADER_MISMATCH` with missing/extra column names | nothing |
| Invalid individual record | counted in `rejected`; 202 | one `ingest_rejections` row |
| Database unavailable | 503 `SERVICE_UNAVAILABLE` with `Retry-After: 30`; accepted rows of one batch commit together or not at all | nothing partial (LOG-052) |
| Background run fails | 202 already returned; run row ends `failed` (handled by FEAT-053); the raw rows stay stored and the next run processes them | raw rows kept |
| Unknown batch id | 404 `BATCH_NOT_FOUND` | — |

Recovery: the caller may re-send the whole file; re-sent records become duplicates and change no derived result (ING-039, AC-ING-03).

## Logging Requirements

- `ingest_record_rejected` (WARNING) per rejected record with `session_id` and `resident_code` if parseable and error locations (LOG-050).
- `ingest_duplicate` (INFO) per duplicate arrival with `session_id` (LOG-051).
- `ingest_batch_completed` (INFO) with `ingest_batch_id`, `accepted`, `rejected`, `duplicates`, `duration_ms` (LOG-053).
- `ingest_request` (INFO) with `request_id`, `endpoint`, `api_key_id` or `user_id`, `ingest_batch_id`, `record_count`, `accepted`, `rejected`, `duplicates`, `warning_count`, `duration_ms` (ING-057).
- Audit: one `audit_logs` row `ingest.batch.received` per accepted envelope, in the same transaction (SEC-100, SEC-101, LOG-090), with the paired `audit_event` log line (LOG-092).

## Testing Requirements

- Integration (`tests/integration/api/test_ingest.py`, marker `integration`):
  - TST-046: SRC-05 multipart upload as admin → 202, accepted 283, rejected 0, duplicates 2; `raw_sessions` has 283 rows with `arrival_seq` in file order (AC-ING-01, AC-API-01 first half).
  - TST-047 / AC-API-17 / TDV-005: upload `tests/fixtures/legacy/echowell_mock_data_500.csv` → 422 `CSV_HEADER_MISMATCH`, `raw_sessions` count unchanged.
  - AC-ING-06: Annotated_sessions-style header with `expected_status` → 422 `CSV_HEADER_MISMATCH`, `errors[].code` `extra_forbidden`.
  - AC-ING-03: re-upload SRC-05 → duplicates 283.
  - Envelope cases: empty `records` → 422 `EMPTY_BATCH`; 5,001 records → 413; `.xlsx` and `audio/wav` → 415; nothing stored in each case.
  - Mixed batch: one invalid record among valid ones → 202, rejected 1, one `ingest_rejections` row with `row_number`, valid rows stored.
  - Duplicate within the same batch and across batches counted in `duplicates`; differing payload carries `duplicate_payload_differs`.
  - Audit row `ingest.batch.received` with counts and `request_id` (TST-053); `api_keys.last_used_at` updated.
  - Background task scheduled once with `trigger = ingest` and the API-053 scope (the runner is replaced with a recording double through `app.dependency_overrides` or a service seam, API-017).
  - `GET /ingest/batches/{id}`: admin and researcher 200 with rejections and no `raw_body`; clinician 403; unknown id 404 `BATCH_NOT_FOUND`.
- Unit (`tests/unit/backend/services/test_ingestion.py`, marker `unit`): CSV header comparison with BOM, CRLF, reordered columns, missing and extra columns.
- Contract: responses validated against the OpenAPI document (TST-061); role cells checked by TST-130 (FEAT-039).
- Performance: TST-124 (202 within 2 s for SRC-05; background run ≤ 30 s) runs in FEAT-079.
- Algorithm validation: Tier B (TDV-031, VC-G11) uses this endpoint (FEAT-058, FEAT-059).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-026-AC-01 | Uploading `tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv` as admin returns 202 with `accepted` 283, `rejected` 0, `duplicates` 2, `source` `csv_upload`, a non-null `pipeline_run_id`, and `raw_sessions` gains exactly 283 rows whose `arrival_seq` order equals the CSV row order. | TST-046, AC-ING-01, API-052 |
| FEAT-026-AC-02 | Uploading the legacy SRC-06 file returns 422 with `type` `urn:echowell:error:CSV_HEADER_MISMATCH` and the counts of `raw_sessions`, `ingest_rejections` and `ingest_batches` are unchanged. | TST-047, AC-API-17, FR-032 |
| FEAT-026-AC-03 | A CSV whose header contains `expected_status` returns 422 `CSV_HEADER_MISMATCH` with an `errors[]` item of code `extra_forbidden` naming `expected_status`; nothing is stored. Verified by: Integration (`tests/integration/api/test_ingest.py`; TST-047). | ING-053, AC-ING-06 |
| FEAT-026-AC-04 | `{"records": []}` returns 422 `EMPTY_BATCH`, a 5,001-record body returns 413 `PAYLOAD_TOO_LARGE`, and a `Content-Type: audio/wav` request returns 415; none creates any row. Verified by: Integration (`tests/integration/api/test_ingest.py`; TST-047). | ING-007, API-050, ING-012 |
| FEAT-026-AC-05 | A JSON batch of 3 records where the second has `audio_quality_flag = "bad"` returns 202 with accepted 2, rejected 1, and creates one `ingest_rejections` row whose `errors` contain code `invalid_enum`. Verified by: Integration (`tests/integration/api/test_ingest.py`). | ING-006, ING-007, API-051 |
| FEAT-026-AC-06 | Re-uploading SRC-05 returns `duplicates` 283 and `accepted` 283. Verified by: Integration (`tests/integration/api/test_ingest.py`; TST-047). | AC-ING-03, ING-008 |
| FEAT-026-AC-07 | After a successful upload exactly one `audit_logs` row with action `ingest.batch.received`, entity id = the batch id and details containing `record_count`, `accepted`, `rejected`, `duplicates` exists, and its `request_id` equals the response `X-Request-ID`. | ING-058, TST-053, AC-SEC-09 |
| FEAT-026-AC-08 | A clinician JWT calling `POST /ingest` receives 403; a researcher JWT calling `GET /ingest/batches/{id}` receives 200 and a clinician 403; an unknown batch id returns 404 `BATCH_NOT_FOUND`. Verified by: Integration (`tests/integration/api/test_ingest.py`). | TRD 13 Table 4.13-A, API-054 |
| FEAT-026-AC-09 | The `GET /ingest/batches/{id}` body validates against `IngestBatch` and contains no `raw_body` or payload field. | DME-005, TST-061 |
| FEAT-026-AC-10 | Exactly one background call of `pipeline_runner.run` is registered per accepted batch with `trigger = "ingest"`, and none when every record was rejected or a duplicate (`pipeline_run_id` null). Verified by: Integration (`tests/integration/api/test_ingest.py`). | API-053, TRD 19 `IngestBatchAccepted` |

## Definition of Done

- All FEAT-026 acceptance criteria pass.
- Both endpoints exist under `/api/v1` with the TRD 19 schemas, status codes and auth; `python -m backend.cli export-openapi` output includes them (checked by FEAT-038).
- All tests listed above pass with `pytest tests/integration -q` against PostgreSQL 16 (testcontainers); no test skipped.
- Every requirement ID of this file is referenced by a test via `@pytest.mark.req("<ID>")` or listed in `docs/reports/traceability_inspections.md` (TST-013).
- Backend line coverage stays ≥ 85 % (TST-141).
- No log line or response in the test run contains a feature value (asserted for SRC-05 upload by TST-137 in FEAT-039).
- The batch report lists the implemented requirement IDs (AGT-022); the TRD differences noted under Implementation Notes were resolved in PR #2 and need no report. JSON rejection row numbers follow D-84.
- Batch report lists requirement IDs, tests and commands (AGT-022); no commit made by the agent (AGT-012).

## Implementation Notes

- Read the body with `await request.body()` in a thin async wrapper and call the synchronous service with `run_in_threadpool` (TRD 05 §8); never declare `IngestBatchRequest` as the FastAPI body type, or FastAPI answers 422 before rejections are stored.
- Parse CSV with `csv.DictReader` on the decoded text (strip a leading BOM); do not use pandas (TRD 10 §8). Keep every cell as text in `payload`; typed columns are filled from the validated values.
- Multipart: accept part content types `text/csv` and `application/vnd.ms-excel` (browsers label .csv that way, ING-012); reject `.xlsx` by extension or content type with 415.
- Compute `duplicates` with a per-batch `set` of first-seen `session_id`s plus the database check under the session advisory lock, so a copy appearing twice in one file is counted (ING-008).
- Insert records strictly in input order inside one transaction so `arrival_seq` (bigserial) preserves file order; R04's late copy must be arrival 283 (TRD 05 API-051).
- Scope for the background run: for each first-arrival record take its resident plus every resident with an assignment to the record's device valid on the record's local date (API-045), deduplicate, sort by `resident_code`.
- `pipeline_run_id` must exist in the 202 response, so create the `running` run row (FEAT-024 interface) inside or right after the batch transaction and pass its id to the background task.
- Resolved (TRD 24 D-84): `row_number` is the 1-based batch position for CSV and JSON batches (TRD 10 ING-032 and TRD 23 §4.2.8 aligned with TRD 19 `IngestRejection`); it is NULL only for single-record `POST /sessions` rejections, which never appear in a batch read-out.
- Pitfall: slowapi needs the `request: Request` parameter on the limited route (TRD 05 §8).
