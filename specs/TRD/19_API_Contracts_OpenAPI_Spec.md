# 19 API Contracts OpenAPI Spec

Document ID: ECHOWELL-TRD-19 · Version 0.8 (draft for review) · Date: 18 October 2026, revised 27 October 2026 · Owner: Team 2 · Status: Draft

## 1. Purpose

This document is the wire contract of the EchoWell REST API: for every endpoint it fixes the method, path,
authentication and roles, parameters with types and constraints, request body schema, response schemas
with example JSON taken from the pipeline test data (SRC-03, SRC-05), status codes and error codes. It
includes an OpenAPI 3.1 skeleton with `components/schemas` for every DTO. The FastAPI implementation
(TRD 05) and the frontend API client (`frontend/services/api.ts`, TRD 04) are both built from this contract.

## 2. Scope

In scope: every endpoint in the shared contract §10 as amended by §19–§21 (alert reviews and snooze, data alerts,
full analytics payload, pipeline run list, CSV export, logout; no acknowledge endpoint);
all request/response DTOs; enums aligned with the database enums (TRD 06/20); the error (Problem) schema
and error code catalogue (owned by TRD 05 §4.7, repeated here per endpoint); security schemes; contract tests.

Out of scope: endpoint behaviour beyond what a client observes (TRD 05), algorithm definitions (TRD 07–09),
DDL (TRD 20), any audio, chat/LLM or push-notification endpoint (none exist; BR-01, BR-18, OQ-06).

## 3. References

| ID | Document |
|---|---|
| SRC-03 | Pipeline test workbook v0.1 (Exp_scores, Exp_baselines, Exp_status_counts, Exp_resident_outcomes used in examples) |
| SRC-05 | Pipeline test input CSV v0.1 (field order of `IngestRecord`; CSV header for `POST /ingest`) |
| SRC-21 | Clinical dashboard wireframe v0.2 (specs/UI-wireframe/echowell-wireframes-v0.2.html; fields the dashboard needs: Resident list, Resident chart, New admissions, Study team) |
| SRC-09, SRC-10, SRC-11, SRC-18, SRC-19 | Wireframes v0.1 (Main, Resident, Admission, Alerts, Analytics): superseded by SRC-21 (TRD 24 D-108); removed from the repository |
| SRC-17 | Implement_Feature_Batches.md ("Match OpenAPI specification exactly") |
| TRD 11 | UI/UX specification (consumer of every field; expected test-data rendering §4.13, §4.18.8) |
| TRD 24 | D-109 (display statuses and default order), D-113 (`checkins_started`), D-114 (v0.2 API additions) |
| TRD 05 | Backend API TRD (behaviour, error catalogue, pagination, rate limits) |
| TRD 06 / TRD 20 / TRD 23 | Database design, PostgreSQL schema, entity definitions (enum sources) |
| TRD 08 / TRD 09 | Baseline/scoring and CUSUM/alerting (meaning of z, composite, tally) |
| TRD 10 | Ingestion and validation |
| TRD 12 | Security and authentication (role matrix) |
| TRD 13 | Testing strategy (contract tests) |

## 4. Requirements

### 4.1 Contract-level requirements

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| OAS-001 | The API shall be versioned in the path as `/api/v1`; a breaking change (removed/renamed field, changed type, new required request field, removed enum value) shall require a new path version `/api/v2`. | Must | BR-17 | Inspection |
| OAS-002 | The FastAPI-generated document at `/api/v1/openapi.json` shall declare `openapi: 3.1.0`, `info.title` "EchoWell API", `info.version` "0.1.0", and the servers `/api/v1`-relative paths defined in §4.4. The generated document shall be committed as `docs/api_reference/openapi.json`, produced by `python -m backend.cli export-openapi`. | Must | SRC-17, contract §21 R22 | Test |
| OAS-003 | Every path, method, parameter (name, location, type, required flag, constraints), request body and response status code in this document shall appear in the generated document, and no other paths shall appear. | Must | SRC-17 | Test |
| OAS-004 | Every schema in `components/schemas` of §4.5 shall exist in the generated document with the same property names, types, `required` lists and enum values; additional optional response properties are a contract change and shall be added here first. | Must | SRC-17 | Test |
| OAS-005 | CI shall regenerate the schema with `python -m backend.cli export-openapi` and fail when it differs from the committed `docs/api_reference/openapi.json`. A contract test (`tests/contract/test_openapi_contract.py`, TRD 13 TST-060) shall also compare the generated document with the §4.5 skeleton (stored verbatim as `tests/fixtures/trd19_openapi_skeleton.yaml`) and fail on any difference in paths, methods, status codes, parameter definitions, schema property names, types, required lists or enums. | Must | SRC-17, TRD 13, contract §21 R22 | Test |
| OAS-006 | Response-validation tests shall validate every response body produced by the integration test suite against the declared response schema for its status code (using `openapi-core` or `jsonschema` with the 3.1 dialect). | Must | TRD 13 | Test |
| OAS-007 | Enum values in DTOs shall equal the database enum values in TRD 20: `ProcessedStatus`, `DayStatus`, `AlarmState`, `AlertStatus`, `NoteType`, `Role`, `Cohort`, `ResidentStatus`, `PipelineTrigger`, `PipelineStatus`, `IngestSource`, `ReviewOutcome`, `DataAlertKind`, `DataAlertStatus`; a test shall compare them with `pg_enum`. | Must | TRD 20, TRD 23 | Test |
| OAS-008 | Property names shall be snake_case, identical to the database column names where a column exists (for example `resident_code`, `cusum_tally`, `alarm_state`). | Must | TRD 06 | Inspection |
| OAS-009 | All non-2xx responses shall use media type `application/problem+json` and the `Problem` schema; all other responses `application/json`, except 204. | Must | contract §10 | Test |
| OAS-010 | Every response shall declare the `X-Request-ID` header (string). | Must | contract §10 | Test |
| OAS-011 | Floating-point values shall be serialised as JSON numbers in full float64 precision (no rounding in the API); rounding is a presentation concern (TRD 04). | Must | BR-15 | Test |
| OAS-012 | Nullable fields shall be declared with `type: [<type>, "null"]` and shall always be present in responses (never omitted). | Must | — | Test |
| OAS-013 | Security schemes shall be `bearerAuth` (`type: http`, `scheme: bearer`, `bearerFormat: JWT`) and `apiKeyAuth` (`type: apiKey`, `in: header`, `name: X-API-Key`); each operation shall list the schemes in §4.3. | Must | TRD 12 | Test |
| OAS-014 | The frontend TypeScript types in `frontend/lib/api-types.ts` shall be generated from `docs/api_reference/openapi.json` with `openapi-typescript` 7.x, and CI shall fail if regeneration produces a diff. | Must | TRD 04, TRD 16, contract §21 R22 | Test |
| OAS-015 | Examples in this document shall be included as `examples` in the YAML and the contract test shall validate each example against its schema. | Should | BR-15 | Test |
| OAS-017 | Every paged list response and the `ResidentDetail`, `FeaturesResponse`, `AdmissionComparison` and `AnalyticsResponse` bodies shall contain the `Meta` object; single-object action responses (`Token`, `User`, `IngestResult`, `IngestBatchAccepted`, `IngestBatch`, `Alert`, `AlertReview`, `StaffNote`, `PipelineRun`, `PipelineRunAccepted`, `Health`) shall not. | Must | contract §20 R3 | Test |
| OAS-018 | `GET /scores` and `GET /analytics/baselines` shall declare a `text/csv` response alternative in addition to `application/json`, selected by the `Accept` header (researcher, admin only). | Must | contract §20 R4 | Test |
| OAS-016 | No schema shall contain a property for audio data, audio URLs, resident names, dates of birth or any free-text identifier other than study IDs (`resident_code`, `device_code`, `session_id`). | Must | BR-01, BR-16 | Inspection |

### 4.2 Common conventions

- Base URL: `${NEXT_PUBLIC_API_BASE_URL}/api/v1` (for local development `http://localhost:8000/api/v1`).
- Time fields: `*_at` = ISO 8601 UTC with `Z`; `*_local` = ISO 8601 with facility offset; `local_date`,
  `*_on`, `*_since`, `from`, `to` = `YYYY-MM-DD` facility-local calendar dates.
- Pagination query: `limit` integer 1..500 default 50, `offset` integer ≥ 0 default 0. Paged responses:
  `{"items": [...], "total": int, "limit": int, "offset": int}` plus endpoint-specific top-level fields.
- `meta`: every paged list and every resident/analytics detail response carries
  `meta {facility_name, facility_tz, data_source_label, as_of, baseline_n, cusum_h, pipeline_profile}`;
  `meta.as_of` is the as-of of the most recent succeeded pipeline run (TRD 05 API-069, API-135). Test-data value:

```json
{"meta": {"facility_name": "Edgewood", "facility_tz": "America/Chicago", "data_source_label": "pipeline test data v0.1",
          "as_of": "2026-10-30T20:00:00Z", "baseline_n": 16, "cusum_h": 5.0, "pipeline_profile": "test_v0_1"}}
```

- CSV export: `GET /scores` and `GET /analytics/baselines` with `Accept: text/csv` (researcher, admin) return
  `text/csv; charset=utf-8`, header row = DTO field names (`z` flattened to `z_<feature>` columns), all matching rows.
- Error codes listed per endpoint are in addition to the universal ones: 401 `NOT_AUTHENTICATED`/`TOKEN_EXPIRED`/
  `TOKEN_INVALID` (bearer endpoints) or `API_KEY_INVALID` (key endpoints), 403 `FORBIDDEN`, 413 `PAYLOAD_TOO_LARGE`,
  429 `RATE_LIMITED`, 500 `INTERNAL_ERROR`, 503 `SERVICE_UNAVAILABLE`.

Problem example (all errors):

```json
{
  "type": "urn:echowell:error:RESIDENT_NOT_FOUND",
  "title": "Resident not found",
  "status": 404,
  "detail": "No resident with code 'R11'.",
  "request_id": "6c1f3f5e-2b7d-4a7e-9a39-1f0d2f8a4c11",
  "errors": []
}
```

### 4.3 Endpoint contracts

Role abbreviations: A = admin, C = clinician, Rs = researcher, K = API key with scope `ingest:write`.

#### E-01 GET /api/v1/health
- Auth: none. Parameters: none.
- 200 `Health`; 503 `Health` with `status`="degraded".

```json
{"status": "ok", "database": "ok", "version": "3f2c9ab", "time": "2026-10-30T20:00:00Z"}
```

#### E-02 POST /api/v1/auth/login
- Auth: none. Body `LoginRequest` `{email: string (email, ≤254), password: string (1..128)}`.
- 200 `Token`. Errors: 401 `INVALID_CREDENTIALS`, 422 `VALIDATION_ERROR`, 429 `RATE_LIMITED`, 429 `ACCOUNT_TEMPORARILY_LOCKED`.

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.<payload>.<signature>",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {"id": "5a0c3f8e-1d2b-4c6a-8e9f-0a1b2c3d4e5f", "email": "clinician1@example.org",
           "display_name": "Clinician One", "role": "clinician", "active": true,
           "last_login_at": "2026-10-30T19:58:41Z", "created_at": "2026-10-19T15:02:10Z"}
}
```

#### E-03 POST /api/v1/auth/logout
- Auth: bearer (A, C, Rs). Body: none. 204. Errors: universal.

#### E-04 GET /api/v1/auth/me
- Auth: bearer (A, C, Rs). 200 `User`.

#### E-32 GET /api/v1/config/ui
- Auth: bearer (A, C, Rs). 200 `UiConfig`: the operational config values the frontend needs (TRD 07 §4.7
  `OperationalConfig`), read from `config_parameters` of the active profile on each request. Errors: universal.

```json
{"meta": {"facility_name": "Edgewood", "facility_tz": "America/Chicago", "data_source_label": "pipeline test data v0.1",
          "as_of": "2026-10-30T20:00:00Z", "baseline_n": 16, "cusum_h": 5.0, "pipeline_profile": "test_v0_1"},
 "alert_snooze_hours": 24,
 "review_explanations": [
  {"code": "cold_cough_sore_throat", "label": "Cold, cough or sore throat"},
  {"code": "dental_dentures", "label": "Dental problem or dentures out"},
  {"code": "medication_change", "label": "New or changed medication"},
  {"code": "poor_sleep_unusual_day", "label": "Poor sleep or unusual day"},
  {"code": "room_device_moved", "label": "Room or device moved"}]}
```

#### E-05 POST /api/v1/sessions
- Auth: apiKeyAuth (K). Body `IngestRecord` (application/json, ≤ 64 KB). Rate limit RATE_LIMIT_INGEST per key.
- 201 `IngestResult` (first arrival, processed); 200 `IngestResult` with `status_after_processing`="duplicate".
- Errors: 422 `VALIDATION_ERROR`, `UNSUPPORTED_SCHEMA_VERSION`, `UNKNOWN_RESIDENT`, `UNKNOWN_DEVICE`,
  `RESIDENT_WITHDRAWN`, `SESSION_ID_MISMATCH`; 403 `DEVICE_KEY_MISMATCH`; 415 `UNSUPPORTED_MEDIA_TYPE`.

Request (SRC-05 row R09-20261021-01):

```json
{
  "schema_version": "0.1", "session_id": "R09-20261021-01", "resident_id": "R09", "device_id": "D09",
  "timestamp_utc": "2026-10-21 19:07:50", "mic_noise_level_dbfs": -54.6, "audio_quality_flag": "ok",
  "extraction_software_version": "openSMILE 3.0.2", "device_firmware_version": "fw-1.0.0",
  "speech_duration_s": 2.72, "phrase_id": "P01",
  "loudness_dbfs": -28.29, "total_phrase_duration_s": 2.72, "speech_rate_syl_per_s": 3.48,
  "articulation_rate_syl_per_s": 4.93, "number_of_pauses": 2, "pause_fraction": 0.199,
  "voiced_fraction": 0.517, "mean_f0_hz": 178.8, "f0_variability_st": 2.97, "jitter_local_pct": 0.305,
  "shimmer_local_pct": 5.96, "hnr_db": 15.26, "cpps_db": 10.94, "alpha_ratio_db": -3.6,
  "hammarberg_index_db": 29.88, "mfcc1": 26.8, "mfcc2": 10.31, "mfcc3": 2.02, "mfcc4": -4.5
}
```

Response 201:

```json
{"raw_session_id": "9d7e1c44-3b2a-4f0e-8c1d-6e5f4a3b2c10", "arrival_seq": 254, "session_id": "R09-20261021-01",
 "status_after_processing": "usable", "reasons": [], "pipeline_run_id": "c2a1b0f9-8e7d-4c6b-a5f4-e3d2c1b0a998"}
```

Response 200 (same body posted again):

```json
{"raw_session_id": "1f2e3d4c-5b6a-4978-8695-a4b3c2d1e0f9", "arrival_seq": 284, "session_id": "R09-20261021-01",
 "status_after_processing": "duplicate", "reasons": ["session_id already received"], "pipeline_run_id": null}
```

Response 201 for SRC-05 row R03-20261018-01 (`audio_quality_flag` poor, noise −30.0):

```json
{"raw_session_id": "...", "arrival_seq": 78, "session_id": "R03-20261018-01", "status_after_processing": "set_aside",
 "reasons": ["quality flag poor", "noise above limit"], "pipeline_run_id": "..."}
```

Response 422 (unknown resident):

```json
{"type": "urn:echowell:error:UNKNOWN_RESIDENT", "title": "Unknown resident", "status": 422,
 "detail": "resident_id 'R11' is not enrolled.", "request_id": "0e4b2f7a-9c1d-4e8b-a3f6-5d2c7b1e9a40",
 "errors": [{"field": "resident_id", "code": "unknown_resident", "message": "resident_id 'R11' is not enrolled."}]}
```

(`arrival_seq` and UUID values in examples are illustrative; all other values are from SRC-05/SRC-03.)

#### E-06 POST /api/v1/ingest
- Auth: apiKeyAuth (K) or bearerAuth (A).
- Body, one of: `application/json` `IngestBatchRequest` `{records: IngestRecord[1..5000]}`; or
  `multipart/form-data` with part `file` (text/csv, ≤ 5 MB, header = SRC-05 header).
- 202 `IngestBatchAccepted`. Errors: 422 `EMPTY_BATCH`, `CSV_HEADER_MISMATCH`, `VALIDATION_ERROR` (envelope only);
  413 `PAYLOAD_TOO_LARGE`; 415 `UNSUPPORTED_MEDIA_TYPE`. Record-level errors do not fail the request.

```json
{"ingest_batch_id": "7b6a5c4d-3e2f-4a1b-9c8d-7e6f5a4b3c2d", "source": "csv_upload",
 "accepted": 283, "rejected": 0, "duplicates": 2, "pipeline_run_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"}
```

#### E-07 GET /api/v1/ingest/batches/{id}
- Auth: bearer (A, Rs). Path `id` uuid. 200 `IngestBatch`. Errors: 404 `BATCH_NOT_FOUND`, 422 `INVALID_QUERY_PARAMETER` (malformed uuid).

```json
{"id": "7b6a5c4d-3e2f-4a1b-9c8d-7e6f5a4b3c2d", "source": "csv_upload", "filename": "EchoWell_pipeline_test_input_v0_1.csv",
 "record_count": 283, "accepted_count": 283, "rejected_count": 0, "duplicate_count": 2,
 "uploaded_by": "5a0c3f8e-1d2b-4c6a-8e9f-0a1b2c3d4e5f", "received_at": "2026-10-30T20:01:05Z",
 "pipeline_run_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d", "rejections": []}
```

#### E-08 GET /api/v1/residents
- Auth: bearer (A, C, Rs).
- Query: `sort` enum [alarm, resident_id, last_checkin] default alarm; `cohort` enum [longitudinal, new_admission]
  default longitudinal; `include_withdrawn` boolean default false; `limit`, `offset`.
- `sort=alarm` (default; TRD 24 D-109, amending D-17): Changed (`status` `alarm_on`; `alarm_since` oldest first, then
  natural resident-code order) → Needs attention (`needs_attention` true and not `alarm_on`) → Learning
  (`baseline_forming`, no attention flag) → Usual (`no_alarm`, no attention flag), each of the last three in natural
  resident-code order. `resident_id` and `last_checkin` keep their v0.1 rules (TRD 05 API-072); they stay in the API
  but are not offered by the v0.2 UI, which shows rows in the default order and filters them in the browser (TRD 11 UX-408).
- `summary` (`OverviewSummary`, over all residents matching the filters, independent of `limit`/`offset`) counts the
  residents per display status with the same precedence (Changed, Needs attention, Learning, Usual); the four counts
  sum to `total`.
- 200 `ResidentsOverviewResponse`. Errors: 422 `INVALID_QUERY_PARAMETER`.

Example (test_v0_1, as of 2026-10-30 15:00 CDT; rows R09, R03, R08 and R07 shown, `total` 10):

```json
{
  "meta": {"facility_name": "Edgewood", "facility_tz": "America/Chicago", "data_source_label": "pipeline test data v0.1",
          "as_of": "2026-10-30T20:00:00Z", "baseline_n": 16, "cusum_h": 5.0, "pipeline_profile": "test_v0_1"},
  "window": {"from": "2026-10-01", "to": "2026-10-30", "days": 30},
  "summary": {"changed": 2, "needs_attention": 2, "learning": 0, "usual": 6},
  "items": [
    {"resident_code": "R09", "cohort": "longitudinal", "resident_status": "active", "device_code": "D09",
     "device_shared": false, "previous_device_code": null, "status": "alarm_on",
     "needs_attention": false, "attention_reasons": [], "alarm_since": "2026-10-21",
     "open_alert_id": "0b8f3c2e-5d1a-4c3e-9f7a-2a6d1e4b7c90", "alarm_reviewed": false, "current_epoch": 1,
     "baseline_restarted_on": null, "restart_cause": null,
     "baseline_progress": {"n_usable": 16, "n_required": 16},
     "last_checkin_at": "2026-10-30T19:28:04Z", "last_checkin_local": "2026-10-30T14:28:04-05:00",
     "last_30_days": {"used": 30, "set_aside": 0, "quarantined": 0, "missed": 0}},
    {"resident_code": "R03", "cohort": "longitudinal", "resident_status": "active", "device_code": "D02",
     "device_shared": true, "previous_device_code": null, "status": "no_alarm",
     "needs_attention": true, "attention_reasons": ["high_set_aside"], "alarm_since": null,
     "open_alert_id": null, "alarm_reviewed": null, "current_epoch": 1,
     "baseline_restarted_on": null, "restart_cause": null,
     "baseline_progress": {"n_usable": 16, "n_required": 16},
     "last_checkin_at": "2026-10-30T19:19:17Z", "last_checkin_local": "2026-10-30T14:19:17-05:00",
     "last_30_days": {"used": 22, "set_aside": 7, "quarantined": 0, "missed": 1}},
    {"resident_code": "R08", "cohort": "longitudinal", "resident_status": "active", "device_code": "D08",
     "device_shared": false, "previous_device_code": null, "status": "baseline_forming",
     "needs_attention": true, "attention_reasons": ["baseline_stalled"], "alarm_since": null,
     "open_alert_id": null, "alarm_reviewed": null, "current_epoch": 1,
     "baseline_restarted_on": null, "restart_cause": null,
     "baseline_progress": {"n_usable": 13, "n_required": 16},
     "last_checkin_at": "2026-10-30T19:28:26Z", "last_checkin_local": "2026-10-30T14:28:26-05:00",
     "last_30_days": {"used": 13, "set_aside": 5, "quarantined": 0, "missed": 12}},
    {"resident_code": "R07", "cohort": "longitudinal", "resident_status": "active", "device_code": "D07B",
     "device_shared": false, "previous_device_code": "D07", "status": "no_alarm",
     "needs_attention": false, "attention_reasons": [], "alarm_since": null,
     "open_alert_id": null, "alarm_reviewed": null, "current_epoch": 2,
     "baseline_restarted_on": "2026-10-13", "restart_cause": "device",
     "baseline_progress": {"n_usable": 16, "n_required": 16},
     "last_checkin_at": "2026-10-30T19:52:57Z", "last_checkin_local": "2026-10-30T14:52:57-05:00",
     "last_30_days": {"used": 30, "set_aside": 0, "quarantined": 0, "missed": 0}}
  ],
  "total": 10, "limit": 50, "offset": 0
}
```

Full default order: R09, R10, R03, R08, R01, R02, R04, R05, R06, R07 (Changed R09 Oct 21, R10 Oct 24; Needs attention
R03, R08; no Learning resident; Usual R01, R02, R04, R05, R06, R07). The R10 row has `alarm_since` 2026-10-24 and
`alarm_reviewed` false; R05 has `needs_attention` false although it has an open `possible_other_speaker` data alert,
and R02 and R03 are unaffected in status by the D02 `device_silent` alert (TRD 24 D-109, OQ-31). After a review of the
R09 alert, R09's `alarm_reviewed` is true and its `status` stays `alarm_on`.
`needs_attention` is true when the resident has at least one open data alert of kind `baseline_stalled` or
`high_set_aside` (independent of `status`; the display status gives Changed precedence); `attention_reasons` lists those
kinds in the order baseline_stalled, high_set_aside (empty when `needs_attention` is false); `alarm_reviewed` is null
without a non-closed alert in the current epoch, otherwise true when that alert's status is `acknowledged` and false when
it is `open`; `restart_cause` is the restart cause of the current epoch (TRD 06 DB-065) when
`current_epoch` > 1, otherwise null (TRD 23 §4.4.3).

#### E-09 GET /api/v1/residents/{resident_code}
- Auth: bearer (A, C, Rs). Path `resident_code` string pattern `^[A-Z0-9]{1,16}$`.
- 200 `ResidentDetail`. Errors: 404 `RESIDENT_NOT_FOUND`.

```json
{
  "resident_code": "R09", "cohort": "longitudinal", "resident_status": "active", "sex": "F",
  "enrolled_on": "2026-10-01", "admitted_on": null, "withdrawn_on": null,
  "meta": {"facility_name": "Edgewood", "facility_tz": "America/Chicago", "data_source_label": "pipeline test data v0.1",
          "as_of": "2026-10-30T20:00:00Z", "baseline_n": 16, "cusum_h": 5.0, "pipeline_profile": "test_v0_1"},
  "status": "alarm_on",
  "needs_attention": false, "attention_reasons": [], "alarm_reviewed": false,
  "device": {"device_code": "D09", "shared": false, "shared_with": [], "previous_device_code": null},
  "current_epoch": {"epoch_number": 1, "device_code": "D09", "device_firmware_version": "fw-1.0.0",
                    "extraction_software_version": "openSMILE 3.0.2", "started_at": "2026-10-01T19:40:50Z",
                    "started_on": "2026-10-01", "from_value": null, "to_value": null},
  "restart_cause": null,
  "epoch_count": 1,
  "baseline": {"state": "frozen", "n_usable": 16, "n_required": 16,
               "first_session_id": "R09-20261001-01", "frozen_after_session_id": "R09-20261016-01",
               "first_local_date": "2026-10-01", "frozen_after_local_date": "2026-10-16"},
  "watching_since": "2026-10-17",
  "alarm_since": "2026-10-21",
  "open_alert_id": "0b8f3c2e-5d1a-4c3e-9f7a-2a6d1e4b7c90",
  "current_tally": 26.830256,
  "last_checkin_at": "2026-10-30T19:28:04Z",
  "last_checkin_local": "2026-10-30T14:28:04-05:00",
  "window": {"from": "2026-10-01", "to": "2026-10-30", "days": 30},
  "last_30_days": {"used": 30, "set_aside": 0, "quarantined": 0, "missed": 0},
  "explanation": {"compared_with": "own_baseline", "alarm_crossed_on": "2026-10-21", "still_above_line": true,
                  "baseline_restarted_on": null, "baseline_n_usable": 16, "baseline_n_required": 16}
}
```

`needs_attention`, `attention_reasons`, `alarm_reviewed` and `restart_cause` follow the E-08 rules (TRD 24 D-114).
`window` is the resident's 30-day window (`DateWindow`, the same window as `last_30_days`, starting no earlier than
`enrolled_on`); the chart banner shows "Usable check-ins, last 30 days" as "<used> of <window.days>" ("30 of 30").
R07 has `restart_cause` "device" and `current_epoch` epoch 2 on D07B with `from_value` "D07", `to_value` "D07B" (derived
as for the `baseline_restarted` event, TRD 06 DB-065); R08 has `needs_attention` true, `attention_reasons`
["baseline_stalled"]; R03 has `needs_attention` true, `attention_reasons` ["high_set_aside"].

#### E-10 GET /api/v1/residents/{resident_code}/checkins
- Auth: bearer (A, C, Rs). Query `from`, `to` (date, optional, from ≤ to, span ≤ 366 days), `limit`, `offset`.
- 200 `CheckinEventList` (newest first; events on the same local date in the order `alarm_on`, `watching_started`, `baseline_complete`, `baseline_restarted`, `quarantined`, `set_aside`, `device_silent`, `missed`, `checkins_started`, TRD 11 UX-141). Errors: 404 `RESIDENT_NOT_FOUND`, 422 `INVALID_QUERY_PARAMETER`.

```json
{"meta": {"facility_name": "Edgewood", "facility_tz": "America/Chicago", "data_source_label": "pipeline test data v0.1",
          "as_of": "2026-10-30T20:00:00Z", "baseline_n": 16, "cusum_h": 5.0, "pipeline_profile": "test_v0_1"},
 "items": [
  {"local_date": "2026-10-21", "event_type": "alarm_on", "epoch_number": 1, "session_id": "R09-20261021-01",
   "detail": "tally crossed 5.0", "cusum_tally": 5.431965},
  {"local_date": "2026-10-17", "event_type": "watching_started", "epoch_number": 1, "session_id": "R09-20261017-01",
   "detail": null, "cusum_tally": null},
  {"local_date": "2026-10-16", "event_type": "baseline_complete", "epoch_number": 1, "session_id": "R09-20261016-01",
   "detail": "16 of 16", "cusum_tally": null}
 ], "total": 4, "limit": 50, "offset": 0}
```

(The first three items are shown; the fourth and oldest is R09's `checkins_started` event on 2026-10-01. The restart
fields and `device_code`, null on these events, are omitted for brevity; in responses every `CheckinEvent` property is
present, OAS-012.)

Other event examples: R03 2026-10-18 `set_aside` detail "quality flag poor; noise above limit"; R05 2026-10-08
`quarantined` detail "possible other speaker (F0 z=-8.61; composite features with |z|>=3: 4)"; R02 2026-10-04
`missed` detail "no record received"; R02 2026-10-12 `device_silent` detail "all residents on shared device D02
have no record"; R07 2026-10-13 `baseline_restarted` detail "new epoch 2 on device D07B" with `restart_cause` "device",
`previous_device_code` "D07", `from_value` "D07", `to_value` "D07B". A firmware or software restart uses the same detail template "new epoch <n> on device <device code of the new epoch>"; its `restart_cause`, `from_value` and `to_value` carry the change (TRD 24 D-82). For every other event type `restart_cause`,
`previous_device_code`, `from_value` and `to_value` are null. When several parts of the epoch key change at once,
`restart_cause` is the first changed part in the order device, firmware, software, derived from the epoch and the
resident's previous epoch (TRD 06 DB-065). `Device.in_use_until` is derived per TRD 06 DB-066.

`checkins_started` (TRD 24 D-113, D-114; derived on read, no table or database enum): exactly one per resident, dated the
facility-local date of the resident's first non-duplicate record of the enrolment (any status, any epoch), with
`session_id` and `epoch_number` of that record and `device_code` = the device of that record; `detail`, `cusum_tally`
and the restart fields are null. `device_code` is null on every other event type. Test data: every resident
2026-10-01; R07 `{"local_date": "2026-10-01", "event_type": "checkins_started", "epoch_number": 1, "session_id":
"R07-20261001-01", "device_code": "D07"}`, which the UI shows as "Check-ins started on D07." because R07's current device
is D07B (TRD 11 §4.5.6).

#### E-11 GET /api/v1/residents/{resident_code}/features
- Auth: bearer (A, C, Rs). Query `from`, `to` (date, optional; default 30 local days ending at as-of).
- 200 `FeaturesResponse`. Errors: 404 `RESIDENT_NOT_FOUND`, 422 `INVALID_QUERY_PARAMETER`.

```json
{"meta": {"facility_name": "Edgewood", "facility_tz": "America/Chicago", "data_source_label": "pipeline test data v0.1",
          "as_of": "2026-10-30T20:00:00Z", "baseline_n": 16, "cusum_h": 5.0, "pipeline_profile": "test_v0_1"},
 "resident_code": "R09", "epoch_number": 1,
 "scored_features": [
  {"feature_key": "loudness_dbfs", "label": "Quieter (loudness)", "unit": "dBFS", "composite_sign": -1,
   "baseline_median": -22.405, "baseline_robust_spread": 2.14977,
   "points": [
     {"session_id": "R09-20261016-01", "local_date": "2026-10-16", "is_morning": false, "raw_value": -21.21,
      "adjusted_value": -21.21, "z": null, "in_baseline": true},
     {"session_id": "R09-20261017-01", "local_date": "2026-10-17", "is_morning": false, "raw_value": -30.03,
      "adjusted_value": -30.03, "z": -3.546891, "in_baseline": false},
     {"session_id": "R09-20261021-01", "local_date": "2026-10-21", "is_morning": false, "raw_value": -28.29,
      "adjusted_value": -28.29, "z": -2.737502, "in_baseline": false}
   ]}
 ],
 "stored_feature_keys": ["mean_f0_hz", "f0_variability_st", "jitter_local_pct", "shimmer_local_pct", "hnr_db",
   "cpps_db", "alpha_ratio_db", "hammarberg_index_db", "mfcc1", "mfcc2", "mfcc3", "mfcc4"]}
```

(`scored_features` always has 7 entries in contract §6 order; abbreviated here.)

#### E-12 GET /api/v1/scores
- Auth: bearer (A, C, Rs). Query `resident_code` (optional), `epoch` (integer ≥ 1, requires `resident_code`),
  `from`, `to`, `limit`, `offset`.
- 200 `ScoresResponse` (`application/json`), or `text/csv` when `Accept: text/csv` (researcher, admin; clinician → 403 `FORBIDDEN`).
  Errors: 404 `RESIDENT_NOT_FOUND` (unknown resident_code), 413 `PAYLOAD_TOO_LARGE` (> 100,000 CSV rows), 422 `INVALID_QUERY_PARAMETER`.

```json
{"meta": {"facility_name": "Edgewood", "facility_tz": "America/Chicago", "data_source_label": "pipeline test data v0.1",
          "as_of": "2026-10-30T20:00:00Z", "baseline_n": 16, "cusum_h": 5.0, "pipeline_profile": "test_v0_1"},
 "cusum_k": 0.5,
 "baseline_periods": [{"resident_code": "R09", "epoch_number": 1, "first_local_date": "2026-10-01",
   "frozen_after_local_date": "2026-10-16", "frozen_after_session_id": "R09-20261016-01", "n_sessions": 16}],
 "items": [
  {"session_id": "R09-20261020-01", "resident_code": "R09", "epoch_number": 1, "local_date": "2026-10-20",
   "is_morning": false,
   "z": {"z_loudness_dbfs": 0.918703, "z_total_phrase_duration_s": 0.753843, "z_speech_rate_syl_per_s": -0.22483,
         "z_articulation_rate_syl_per_s": 0.298031, "z_number_of_pauses": 0.0, "z_pause_fraction": 0.524604,
         "z_voiced_fraction": -1.364667},
   "composite_raw": 0.235887, "composite_z": 0.370597, "cusum_tally": 1.643658, "alarm_state": "off"},
  {"session_id": "R09-20261021-01", "resident_code": "R09", "epoch_number": 1, "local_date": "2026-10-21",
   "is_morning": false,
   "z": {"z_loudness_dbfs": -2.737502, "z_total_phrase_duration_s": 2.420232, "z_speech_rate_syl_per_s": -1.180359,
         "z_articulation_rate_syl_per_s": -1.584269, "z_number_of_pauses": 1.348982, "z_pause_fraction": 2.285774,
         "z_voiced_fraction": -4.721435},
   "composite_raw": 2.325508, "composite_z": 4.288307, "cusum_tally": 5.431965, "alarm_state": "rings"},
  {"session_id": "R09-20261022-01", "resident_code": "R09", "epoch_number": 1, "local_date": "2026-10-22",
   "is_morning": false,
   "z": {"z_loudness_dbfs": -1.597845, "z_total_phrase_duration_s": 2.420232, "z_speech_rate_syl_per_s": 0.056208,
         "z_articulation_rate_syl_per_s": -2.086216, "z_number_of_pauses": 1.348982, "z_pause_fraction": 1.836114,
         "z_voiced_fraction": -2.337189},
   "composite_raw": 1.65291, "composite_z": 3.027292, "cusum_tally": 7.959257, "alarm_state": "on"}
 ],
 "total": 14, "limit": 50, "offset": 0}
```

The `z` values are unsigned standardised deviations `(adjusted − median)/robust_spread` (as in SRC-03 Exp_scores);
`composite_raw` is the mean of `composite_sign × z` over the 7 features. Full R09 tally series (Exp_scores):
Oct 17 3.245474, Oct 18 2.609763, Oct 19 1.773061, Oct 20 1.643658, Oct 21 5.431965 (rings), Oct 22 7.959257,
Oct 23 8.289966, Oct 24 10.714804, Oct 25 12.441007, Oct 26 15.270658, Oct 27 16.705966, Oct 28 18.761866,
Oct 29 23.126702, Oct 30 26.830256 (all `on` after Oct 21).

#### E-13 GET /api/v1/alerts
- Auth: bearer (A, C, Rs). Query `status` enum [open, acknowledged, closed] (optional), `resident_code` (optional), `limit`, `offset`.
- 200 `AlertList` (ordered by `triggered_at` ascending). Errors: 422 `INVALID_QUERY_PARAMETER`.
- `status` `open` = "Not reviewed", `acknowledged` = "Reviewed" (alarm still on; OQ-05). The red badge on the "Resident
  list" navigation link (TRD 11 UX-018) is `total` of `GET /alerts?status=open`; the chart's "Review and notes" section
  and Summary read the resident's alert with `GET /alerts?resident_code=<R>`.

```json
{"meta": {"facility_name": "Edgewood", "facility_tz": "America/Chicago", "data_source_label": "pipeline test data v0.1",
          "as_of": "2026-10-30T20:00:00Z", "baseline_n": 16, "cusum_h": 5.0, "pipeline_profile": "test_v0_1"},
 "items": [
  {"id": "0b8f3c2e-5d1a-4c3e-9f7a-2a6d1e4b7c90", "resident_code": "R09", "device_code": "D09", "epoch_number": 1,
   "session_id": "R09-20261021-01", "triggered_at": "2026-10-21T19:07:50Z", "local_date": "2026-10-21",
   "cusum_value": 5.431965, "current_tally": 26.830256, "open_days": 9, "status": "open", "reviewed": false,
   "review_count": 0, "last_reviewed_at": null, "snoozed_until": null, "snoozed_by": null,
   "leaning_most": ["number_of_pauses", "loudness_dbfs", "voiced_fraction"], "closed_reason": null},
  {"id": "4e3d2c1b-0a9f-4e8d-b7c6-5a4f3e2d1c0b", "resident_code": "R10", "device_code": "D10", "epoch_number": 1,
   "session_id": "R10-20261024-01", "triggered_at": "2026-10-24T19:25:37Z", "local_date": "2026-10-24",
   "cusum_value": 5.97205, "current_tally": 13.418183, "open_days": 6, "status": "open", "reviewed": false,
   "review_count": 0, "last_reviewed_at": null, "snoozed_until": null, "snoozed_by": null,
   "leaning_most": ["number_of_pauses", "articulation_rate_syl_per_s", "speech_rate_syl_per_s"], "closed_reason": null}
 ], "total": 2, "limit": 50, "offset": 0}
```

`triggered_at` is the `timestamp_utc` of the first-crossing session (deterministic under rebuild; alerts are upserted by
(epoch_id, session_id) so ids survive rebuilds); alert `id` values are illustrative. `leaning_most` = up to 3 composite
feature keys with the highest mean signed z over scored sessions from the alarm session onward (only mean > 0); for R09 the
means are 2.158 (pauses), 2.133 (loudness), 2.092 (voiced fraction); the frontend renders them with the lower-cased §6
labels ("more pauses, quieter, less voiced sound"). `current_tally` is shown to 1 dp in the UI (26.8, 13.4).

#### E-14 POST /api/v1/alerts/{id}/reviews
- Auth: bearer (A, C). Path `id` uuid. Body `AlertReviewCreate`.
- 201 `AlertReview`; side effects: alert status `open` → `acknowledged`; outcome `data_problem` also creates or links a `DataAlert`
  of kind `review_flagged_data_problem` (TRD 02 FR-273; title and detail strings TRD 09 CUS-040). CUSUM tally, alarm state and resident `status` are unchanged (OQ-05); the resident's `alarm_reviewed` becomes true.
- Errors: 404 `ALERT_NOT_FOUND`, 409 `ALERT_CLOSED`, 422 `VALIDATION_ERROR` (missing outcome, unknown explanation code,
  duplicate codes, note > 2000 characters).

```json
{"explanations": ["cold_cough_sore_throat"], "outcome": "known_cause", "note": "Resident has a cold; nurse notified."}
```
```json
{"id": "2d4f6a8c-1b3e-4c5d-8e7f-9a0b1c2d3e4f", "alert_id": "0b8f3c2e-5d1a-4c3e-9f7a-2a6d1e4b7c90",
 "reviewer": {"id": "5a0c3f8e-1d2b-4c6a-8e9f-0a1b2c3d4e5f", "display_name": "Clinician One"},
 "explanations": ["cold_cough_sore_throat"], "outcome": "known_cause",
 "note": "Resident has a cold; nurse notified.", "created_at": "2026-10-30T20:10:00Z"}
```

Explanation codes (configured list `review_explanations`, OQ-25): `cold_cough_sore_throat`, `dental_dentures`,
`medication_change`, `poor_sleep_unusual_day`, `room_device_moved`. Outcomes: `no_concern`, `known_cause`, `referred`,
`data_problem`. There is no `POST /alerts/{id}/acknowledge` endpoint.

#### E-28 GET /api/v1/alerts/{id}/reviews
- Auth: bearer (A, C, Rs). Query `limit`, `offset`. 200 `AlertReviewList` newest first. Errors: 404 `ALERT_NOT_FOUND`.

#### E-29 POST /api/v1/alerts/{id}/snooze
- Auth: bearer (A, C). Body `SnoozeRequest` `{hours?: integer 1..168}` (default config `alert_snooze_hours` = 24).
- 200 `Alert` with `snoozed_until` = now + hours, `snoozed_by` = caller. Status and alarm unchanged.
- Errors: 404 `ALERT_NOT_FOUND`, 409 `ALERT_CLOSED`, 422 `VALIDATION_ERROR`.

#### E-30 GET /api/v1/data-alerts
- Auth: bearer (A, C, Rs). Query `status` enum [open, resolved] default open; `kind` (optional `DataAlertKind`); `limit`, `offset`.
- 200 `DataAlertList` ordered by kind (enum order) then resident/device code. Errors: 422 `INVALID_QUERY_PARAMETER`.
- Consumer: the Study team page "Data problems to follow up" (TRD 11 §4.18.2), which renders "**<code>:** <detail>"
  with `title` as the code link's accessible name and groups the rows by the TRD 11 UX-307 kind order (R08, R03, R05,
  D02 for the test data); open `baseline_stalled` and `high_set_aside` alerts also drive `needs_attention` on E-08/E-09.

```json
{"meta": {"facility_name": "Edgewood", "facility_tz": "America/Chicago", "data_source_label": "pipeline test data v0.1",
          "as_of": "2026-10-30T20:00:00Z", "baseline_n": 16, "cusum_h": 5.0, "pipeline_profile": "test_v0_1"},
 "items": [
  {"id": "6a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d", "kind": "baseline_stalled", "resident_code": "R08", "device_code": null,
   "title": "R08 · baseline stuck at 13 of 16", "detail": "baseline stuck at 13 of 16. 12 missed and 5 set aside in 30 days.",
   "status": "open",
   "first_detected_at": "2026-10-30T20:00:00Z", "last_detected_at": "2026-10-30T20:00:00Z",
   "pipeline_run_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"},
  {"id": "7b2c3d4e-5f6a-4b7c-9d8e-0f1a2b3c4d5e", "kind": "possible_other_speaker", "resident_code": "R05", "device_code": null,
   "title": "R05 · possible other speaker", "detail": "2 check-ins held back as possible other voice (Oct 8, Oct 22).",
   "status": "open",
   "first_detected_at": "2026-10-30T20:00:00Z", "last_detected_at": "2026-10-30T20:00:00Z",
   "pipeline_run_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"},
  {"id": "8c3d4e5f-6a7b-4c8d-ae9f-1a2b3c4d5e6f", "kind": "high_set_aside", "resident_code": "R03", "device_code": null,
   "title": "R03 · many check-ins set aside", "detail": "7 of 29 received check-ins set aside (noise, quality flag, too short).",
   "status": "open",
   "first_detected_at": "2026-10-30T20:00:00Z", "last_detected_at": "2026-10-30T20:00:00Z",
   "pipeline_run_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"},
  {"id": "9d4e5f6a-7b8c-4d9e-bf0a-2b3c4d5e6f7a", "kind": "device_silent", "resident_code": null, "device_code": "D02",
   "title": "D02 · device silent all day", "detail": "silent all day Oct 12. Affected R02 and R03.", "status": "open",
   "first_detected_at": "2026-10-30T20:00:00Z", "last_detected_at": "2026-10-30T20:00:00Z",
   "pipeline_run_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"}
 ], "total": 4, "limit": 50, "offset": 0}
```

(ids illustrative; `first_detected_at`/`last_detected_at` are the run's `as_of` 2026-10-30T20:00:00Z (TRD 06 DB-036); titles are the v0.1 titles, details the v0.2 texts of TRD 09 §4.9 (TRD 24 D-114), and the list is the expected test-data result of TRD 11 §4.18.8.)

#### E-15 GET /api/v1/residents/{resident_code}/notes
- Auth: bearer (A, C, Rs). Query `include_superseded` boolean default false, `limit`, `offset`.
- 200 `StaffNoteList` (newest first). Errors: 404 `RESIDENT_NOT_FOUND`.

#### E-16 POST /api/v1/residents/{resident_code}/notes
- Auth: bearer (A, C). Body `StaffNoteCreate`.
- 201 `StaffNote`. Notes never change alert status (reviews use E-14). Errors: 404 `RESIDENT_NOT_FOUND`, 404 `ALERT_NOT_FOUND`,
  422 `VALIDATION_ERROR`, `ALERT_RESIDENT_MISMATCH`.

```json
{"note_type": "observation", "body": "Resident has a cold; nurse notified.",
 "alert_id": "0b8f3c2e-5d1a-4c3e-9f7a-2a6d1e4b7c90", "supersedes_id": null}
```

```json
{"id": "8c7b6a59-4d3e-4f2a-9b1c-0d9e8f7a6b5c", "resident_code": "R09",
 "alert_id": "0b8f3c2e-5d1a-4c3e-9f7a-2a6d1e4b7c90",
 "author": {"id": "5a0c3f8e-1d2b-4c6a-8e9f-0a1b2c3d4e5f", "display_name": "Clinician One"},
 "note_type": "observation", "body": "Resident has a cold; nurse notified.",
 "supersedes_id": null, "created_at": "2026-10-30T20:10:00Z"}
```

#### E-17 GET /api/v1/devices
- Auth: bearer (A, C, Rs). Query `limit`, `offset`. 200 `DeviceList` ordered by `device_code` (natural).

```json
{"meta": {"facility_name": "Edgewood", "facility_tz": "America/Chicago", "data_source_label": "pipeline test data v0.1",
          "as_of": "2026-10-30T20:00:00Z", "baseline_n": 16, "cusum_h": 5.0, "pipeline_profile": "test_v0_1"},
 "items": [
  {"device_code": "D02", "room_label": null, "active": true, "resident_codes": ["R02", "R03"], "shared": true,
   "replaces_device_code": null, "replaced_by_device_code": null, "in_use_since": "2026-10-01", "in_use_until": null,
   "last_upload_at": "2026-10-30T19:55:23Z", "last_upload_local": "2026-10-30T14:55:23-05:00",
   "firmware_version": "fw-1.0.0", "uploaded_on_as_of_date": true, "silent_days_last_30": ["2026-10-12"],
   "device_gap_days_last_30": ["2026-10-12"]},
  {"device_code": "D07B", "room_label": null, "active": true, "resident_codes": ["R07"], "shared": false,
   "replaces_device_code": "D07", "replaced_by_device_code": null, "in_use_since": "2026-10-13", "in_use_until": null,
   "last_upload_at": "2026-10-30T19:52:57Z", "last_upload_local": "2026-10-30T14:52:57-05:00",
   "firmware_version": "fw-1.0.0", "uploaded_on_as_of_date": true, "silent_days_last_30": [],
   "device_gap_days_last_30": []}
 ], "total": 10, "limit": 50, "offset": 0}
```

`total` is 10 for the test data (D01, D02, D04, D05, D06, D07, D07B, D08, D09, D10). D07 (retired) reports `active`
false, `in_use_since` "2026-10-01", `in_use_until` "2026-10-12" (last day of its last assignment; null while the device
has a current assignment), `replaced_by_device_code` "D07B" and `uploaded_on_as_of_date` false.

`uploaded_on_as_of_date` (TRD 24 D-114) is true when the device has at least one non-duplicate record whose
facility-local date is the as-of local date, otherwise false; the UI shows "● Online" / "○ No upload today" from it
(TRD 11 UX-050, UX-078, UX-430). For the test data it is true for the nine active devices and false for D07. Whether a
device without upload changes a resident's status was OQ-31; it does not (TRD 24 D-115).

Day definitions (TRD 02 §4.1 glossary is the single definition): `silent_days_last_30` = the device's **silent days**,
`device_gap_days_last_30` = its **device-gap days**. `silent_days_last_30` lists local dates in the 30-day window, on or after `in_use_since`, with zero arrivals from
the device. For D02 only 2026-10-12 qualifies: on R02's other missed days (4, 9, 10, 17, 23 Oct) R03 still sent a
record from D02. For D08 (single resident R08) the 12 missed days are silent days but not device-gap days.

#### E-18 GET /api/v1/analytics
- Auth: bearer (A, Rs). Clinicians receive 403 `FORBIDDEN`. 200 `AnalyticsResponse`.
- Exactly one of `alarm_timing` (PIPELINE_PROFILE `test_v0_1`; read from `evaluation_ground_truth` via the DATABASE_READONLY_URL engine in `analytics_summary.py`, TRD 05 API-136) and
  `review_outcomes` (production) is non-null. Percentages are rounded half-up to integers.

```json
{"meta": {"facility_name": "Edgewood", "facility_tz": "America/Chicago", "data_source_label": "pipeline test data v0.1",
          "as_of": "2026-10-30T20:00:00Z", "baseline_n": 16, "cusum_h": 5.0, "pipeline_profile": "test_v0_1"},
 "period": {"from": "2026-10-01", "to": "2026-10-30", "days": 30},
 "kpis": {
   "checkins_received": {"count": 281, "expected": 300, "percent": 94},
   "used_for_scoring": {"count": 267, "expected": 300, "percent": 89},
   "baselines_formed": {"formed": 9, "residents": 10, "forming_resident_codes": ["R08"],
                        "restarts": [{"resident_code": "R07", "restart_count": 1}]},
   "alarms_raised": {"count": 2, "resident_codes": ["R09", "R10"], "not_reviewed_count": 2}},
 "daily_series": [
   {"local_date": "2026-10-12", "used": 8, "set_aside": 0, "quarantined": 0, "missed": 2, "silent_device_codes": ["D02"]}],
 "funnel": {"expected": 300, "residents": 10, "days": 30, "received": 281, "missed": 19, "duplicates_removed": 2,
            "passed_quality": 269, "set_aside": 12,
            "set_aside_reasons": {"quality_flag_poor": 5, "noise_above_limit": 5, "speech_too_short": 3},
            "set_aside_multi_reason": 1, "quarantined": 2, "used": 267},
 "by_resident": [
   {"resident_code": "R08", "days": 30, "used_days": 13, "set_aside_days": 5, "quarantined_days": 0, "missed_days": 12, "used_percent": 43},
   {"resident_code": "R03", "days": 30, "used_days": 22, "set_aside_days": 7, "quarantined_days": 0, "missed_days": 1, "used_percent": 73},
   {"resident_code": "R02", "days": 30, "used_days": 24, "set_aside_days": 0, "quarantined_days": 0, "missed_days": 6, "used_percent": 80},
   {"resident_code": "R05", "days": 30, "used_days": 28, "set_aside_days": 0, "quarantined_days": 2, "missed_days": 0, "used_percent": 93},
   {"resident_code": "R01", "days": 30, "used_days": 30, "set_aside_days": 0, "quarantined_days": 0, "missed_days": 0, "used_percent": 100}],
 "alarm_timing": [
   {"resident_code": "R09", "planted_change": "Sudden step", "change_began": "2026-10-21", "alarm_rang": "2026-10-21",
    "delay_days": 0, "result": "detected"},
   {"resident_code": "R10", "planted_change": "Slow drift", "change_began": "2026-10-17", "alarm_rang": "2026-10-24",
    "delay_days": 7, "result": "detected"},
   {"resident_code": "R01", "planted_change": "None", "change_began": null, "alarm_rang": null,
    "delay_days": null, "result": "correct_no_alarm"}],
 "review_outcomes": null,
 "status_totals": {"usable": 267, "set_aside": 12, "quarantined": 2, "duplicate": 2,
                   "missing_resident": 17, "missing_device_gap": 2},
 "status_counts": [
   {"resident_code": "R02", "usable": 24, "set_aside": 0, "quarantined": 0, "duplicate": 0,
    "missing_resident": 5, "missing_device_gap": 1}],
 "resident_outcomes": [
   {"resident_code": "R09", "epoch_number": 1, "device_code": "D09", "usable_in_epoch": 30, "baseline_formed": true,
    "baseline_frozen_after": "R09-20261016-01", "scored_sessions": 14, "first_alarm_session": "R09-20261021-01",
    "note": null}],
 "pipeline_run": {"id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d", "trigger": "manual", "scope": "all",
   "config_profile": "test_v0_1", "code_version": "3f2c9ab", "as_of": "2026-10-30T20:00:00Z",
   "started_at": "2026-10-30T20:01:06Z", "finished_at": "2026-10-30T20:01:14Z", "status": "succeeded",
   "counts": {"arrivals": 283, "usable": 267, "set_aside": 12, "quarantined": 2, "duplicate": 2,
              "missing_resident": 17, "missing_device_gap": 2, "late_arrival": 0, "scored": 98, "alerts_opened": 2,
              "excluded_after_as_of": 0, "residents": 10},
   "warnings": []}}
```

Abbreviated arrays: `daily_series` has 30 rows (Oct 12 shown: R02 and R03 missed via the D02 device gap),
`by_resident` 10 rows ordered by `used_percent` ascending then resident code (R08 43, R03 73, R02 80, R05 93, then R01,
R04, R06, R07, R09, R10 at 100), `alarm_timing` 10 rows (the 8 residents with planted change "None" all
`correct_no_alarm`; the UI groups them as "Other 8"; a resident whose first alarm precedes its planted change would be `false_alarm` with `delay_days` null, D-81), `status_counts` 10 rows, `resident_outcomes` 11 rows; `pipeline_run` is the latest succeeded run (TRD 05 API-069).
In production `alarm_timing` is null and `review_outcomes` is
`{"alarms_raised": n, "reviewed": n, "by_outcome": {"no_concern": n, "known_cause": n, "referred": n, "data_problem": n}}`.

#### E-19 GET /api/v1/analytics/baselines
- Auth: bearer (A, Rs). Query `resident_code`, `epoch` (requires resident_code), `limit` (default 50, max 500), `offset`.
- 200 `BaselineRowList`, or `text/csv` with `Accept: text/csv`. Test data total = 180.

```json
{"meta": {"...": "as above"},
 "items": [
  {"resident_code": "R09", "epoch_number": 1, "device_code": "D09", "feature_key": "loudness_dbfs", "n_sessions": 16,
   "first_session_id": "R09-20261001-01", "frozen_after_session_id": "R09-20261016-01",
   "median": -22.405, "mad": 1.45, "robust_spread": 2.14977, "floor_applied": false},
  {"resident_code": "R09", "epoch_number": 1, "device_code": "D09", "feature_key": "composite", "n_sessions": 16,
   "first_session_id": "R09-20261001-01", "frozen_after_session_id": "R09-20261016-01",
   "median": 0.038219, "mad": 0.359758, "robust_spread": 0.533378, "floor_applied": false}
 ], "total": 20, "limit": 50, "offset": 0}
```

#### E-20 POST /api/v1/pipeline/run
- Auth: bearer (A) or apiKeyAuth with scope `pipeline:run` (scheduler). Body `PipelineRunRequest`.
- 202 `PipelineRunAccepted`. Errors: 404 `RESIDENT_NOT_FOUND` (unknown code in scope), 409 `PIPELINE_RUN_IN_PROGRESS`,
  422 `VALIDATION_ERROR`, `PROFILE_NOT_ALLOWED` (production with `test_v0_1` or a profile other than PIPELINE_PROFILE).

```json
{"scope": "all", "profile": "test_v0_1", "as_of": "2026-10-30T20:00:00Z"}
```
```json
{"pipeline_run_id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"}
```

#### E-31 GET /api/v1/pipeline/runs
- Auth: bearer (A, Rs). Query `trigger` (optional `PipelineTrigger`), `status` (optional `PipelineStatus`), `limit`, `offset`.
- 200 `PipelineRunList` newest first.

#### E-21 GET /api/v1/pipeline/runs/{id}
- Auth: bearer (A, Rs). 200 `PipelineRun`. Errors: 404 `PIPELINE_RUN_NOT_FOUND`.

#### E-22 GET /api/v1/admissions (experimental)
- Auth: bearer (A, C, Rs). Query `limit`, `offset`. Header `X-EchoWell-Experimental: true`.
- 200 `AdmissionList`. Test data: `{"meta": {...}, "items": [], "total": 0, "limit": 50, "offset": 0}`.
- `comparison_status` is `range_not_available` when no `facility_reference_ranges` row exists (the v0.1 state, OQ-08);
  otherwise `not_enough_checkins`, `outside_range` or `within_range` (TRD 02 FR-202).

#### E-23 GET /api/v1/admissions/{resident_code}/comparison (experimental)
- Auth: bearer (A, C, Rs). 200 `AdmissionComparison`. Errors: 404 `RESIDENT_NOT_FOUND` (unknown or not new_admission).

#### E-24 GET /api/v1/facility/reference-ranges (experimental)
- Auth: bearer (A, C, Rs). Query `limit`, `offset`. 200 `ReferenceRangeList` (empty for test data; method per OQ-08).

#### E-25 GET /api/v1/users · E-26 POST /api/v1/users · E-27 PATCH /api/v1/users/{id}
- Auth: bearer (A).
- GET: query `limit`, `offset`, `role` (optional enum), `active` (optional boolean) → 200 `UserList`.
- POST: body `UserCreate` → 201 `User`; errors 409 `EMAIL_ALREADY_EXISTS`, 422 `PASSWORD_POLICY_VIOLATION`, `VALIDATION_ERROR`.
- PATCH: path `id` uuid, body `UserUpdate` (at least one property) → 200 `User`; errors 404 `USER_NOT_FOUND`,
  409 `LAST_ADMIN`, 422 `PASSWORD_POLICY_VIOLATION`, `VALIDATION_ERROR`.

#### Endpoint/role summary

| # | Method | Path | Security | Roles/keys | Success | Endpoint-specific errors |
|---|---|---|---|---|---|---|
| E-01 | GET | /health | none | — | 200/503 | — |
| E-02 | POST | /auth/login | none | — | 200 | 401 INVALID_CREDENTIALS, 429 ACCOUNT_TEMPORARILY_LOCKED |
| E-03 | POST | /auth/logout | bearer | A C Rs | 204 | — |
| E-04 | GET | /auth/me | bearer | A C Rs | 200 | — |
| E-05 | POST | /sessions | apiKey | K | 201/200 | 422 ingest codes, 403 DEVICE_KEY_MISMATCH, 415 |
| E-06 | POST | /ingest | apiKey or bearer | K, A | 202 | 422 EMPTY_BATCH, CSV_HEADER_MISMATCH, 413, 415 |
| E-07 | GET | /ingest/batches/{id} | bearer | A Rs | 200 | 404 BATCH_NOT_FOUND |
| E-08 | GET | /residents | bearer | A C Rs | 200 | 422 INVALID_QUERY_PARAMETER |
| E-09 | GET | /residents/{resident_code} | bearer | A C Rs | 200 | 404 RESIDENT_NOT_FOUND |
| E-10 | GET | /residents/{resident_code}/checkins | bearer | A C Rs | 200 | 404, 422 |
| E-11 | GET | /residents/{resident_code}/features | bearer | A C Rs | 200 | 404, 422 |
| E-12 | GET | /scores | bearer | A C Rs (CSV: A Rs) | 200 | 404, 413, 422 |
| E-13 | GET | /alerts | bearer | A C Rs | 200 | 422 |
| E-14 | POST | /alerts/{id}/reviews | bearer | A C | 201 | 404 ALERT_NOT_FOUND, 409 ALERT_CLOSED, 422 |
| E-15 | GET | /residents/{resident_code}/notes | bearer | A C Rs | 200 | 404 |
| E-16 | POST | /residents/{resident_code}/notes | bearer | A C | 201 | 404, 422 ALERT_RESIDENT_MISMATCH |
| E-17 | GET | /devices | bearer | A C Rs | 200 | — |
| E-18 | GET | /analytics | bearer | A Rs | 200 | — |
| E-19 | GET | /analytics/baselines | bearer | A Rs | 200 (JSON or CSV) | 413, 422 |
| E-20 | POST | /pipeline/run | bearer or apiKey | A, key `pipeline:run` | 202 | 409 PIPELINE_RUN_IN_PROGRESS, 422 PROFILE_NOT_ALLOWED |
| E-21 | GET | /pipeline/runs/{id} | bearer | A Rs | 200 | 404 PIPELINE_RUN_NOT_FOUND |
| E-22 | GET | /admissions | bearer | A C Rs | 200 | — |
| E-23 | GET | /admissions/{resident_code}/comparison | bearer | A C Rs | 200 | 404 |
| E-24 | GET | /facility/reference-ranges | bearer | A C Rs | 200 | — |
| E-25 | GET | /users | bearer | A | 200 | — |
| E-26 | POST | /users | bearer | A | 201 | 409 EMAIL_ALREADY_EXISTS, 422 PASSWORD_POLICY_VIOLATION |
| E-27 | PATCH | /users/{id} | bearer | A | 200 | 404 USER_NOT_FOUND, 409 LAST_ADMIN |
| E-28 | GET | /alerts/{id}/reviews | bearer | A C Rs | 200 | 404 ALERT_NOT_FOUND |
| E-29 | POST | /alerts/{id}/snooze | bearer | A C | 200 | 404, 409 ALERT_CLOSED, 422 |
| E-30 | GET | /data-alerts | bearer | A C Rs | 200 | 422 |
| E-31 | GET | /pipeline/runs | bearer | A Rs | 200 | 422 |
| E-32 | GET | /config/ui | bearer | A C Rs | 200 | — |

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| OAS-020 | Each endpoint E-01..E-32 shall return exactly the success status codes listed in the endpoint/role summary and only error codes from the TRD 05 catalogue. | Must | TRD 05 | Test |
| OAS-021 | The E-08 example values (summary changed 2, needs_attention 2, learning 0, usual 6; default order R09, R10, R03, R08, R01, R02, R04, R05, R06, R07; `needs_attention` true only for R03 [high_set_aside] and R08 [baseline_stalled]; `alarm_reviewed` false for R09 and R10 and null for the others; R08 13 of 16 with 13·5·0·12; R07 `restart_cause` device) shall be asserted by an integration test on the test_v0_1 data, together with E-10 `checkins_started` on 2026-10-01 for every resident (R07 `device_code` D07) and E-17 `uploaded_on_as_of_date` true for the nine active devices and false for D07. | Must | BR-12, SRC-21, D-109, D-114 | Test |
| OAS-022 | The E-12 R09 series (14 rows, Oct 21 tally 5.431965 `rings`, Oct 30 tally 26.830256 `on`) shall be asserted with absolute tolerance 1e-6. | Must | BR-15, SRC-03 | Test |
| OAS-023 | The E-19 response for the test data shall contain 180 rows whose values equal SRC-03 Exp_baselines within 1e-6, with Exp_baselines feature "COMPOSITE (raw signed mean of 7 z)" mapped to `feature_key`="composite". | Must | BR-09, BR-15 | Test |
| OAS-027 | On the test data, E-30 shall return exactly the four data alerts shown (kinds, codes, titles and the v0.2 details, in the order R08, R05, R03, D02) and E-13 shall return R09 (open_days 9, current_tally 26.830256, leaning_most [number_of_pauses, loudness_dbfs, voiced_fraction]) and R10 (open_days 6, current_tally 13.418183). | Must | SRC-21, D-114 | Test |
| OAS-028 | On the test data, E-18 `kpis`, `funnel`, `by_resident` and `alarm_timing` shall equal the values in the E-18 example and notes. | Must | SRC-21, BR-15 | Test |
| OAS-024 | The E-18 `status_totals` for the test data shall be usable 267, set_aside 12, quarantined 2, duplicate 2, missing_resident 17, missing_device_gap 2 | Must | BR-15 | Test |
| OAS-025 | `IngestRecord` property order in the YAML shall equal the SRC-05 CSV header order. | Must | SRC-05 | Inspection |
| OAS-026 | `ScoredFeatureKey` shall list the 7 composite features in contract §6 order and `FeatureKey` all 19; `BaselineFeatureKey` shall be `FeatureKey` plus `composite`. | Must | contract §6 | Test |

### 4.4 Servers

```yaml
servers:
  - url: http://localhost:8000/api/v1
    description: local (docker-compose)
  - url: /api/v1
    description: relative to the deployed Railway API origin (staging, production)
```

### 4.5 OpenAPI 3.1 skeleton

The YAML below is the design skeleton; it is stored verbatim as `tests/fixtures/trd19_openapi_skeleton.yaml` for the
OAS-005 contract test. The committed artefact is the generated `docs/api_reference/openapi.json`
(`python -m backend.cli export-openapi`, contract §21 R22).
Response components for errors are shared via `components/responses`.

```yaml
openapi: 3.1.0
info:
  title: EchoWell API
  version: 0.1.0
  description: >
    EchoWell research system API. Detects a change in a resident's voice measurements relative to their own
    frozen baseline; a prompt to check in, not a diagnosis. No audio endpoints exist.
servers:
  - url: http://localhost:8000/api/v1
  - url: /api/v1
security: []
tags:
  - {name: health}
  - {name: auth}
  - {name: ingest}
  - {name: residents}
  - {name: scores}
  - {name: alerts}
  - {name: devices}
  - {name: analytics}
  - {name: pipeline}
  - {name: admissions, description: "Future / experimental study arm"}
  - {name: users}
  - {name: config}

paths:
  /health:
    get:
      tags: [health]
      operationId: getHealth
      responses:
        "200": {description: OK, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/Health"}}}}
        "503": {description: Database unavailable, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/Health"}}}}
  /auth/login:
    post:
      tags: [auth]
      operationId: login
      requestBody: {required: true, content: {application/json: {schema: {$ref: "#/components/schemas/LoginRequest"}}}}
      responses:
        "200": {description: Token issued, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/Token"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "422": {$ref: "#/components/responses/Unprocessable"}
        "429": {$ref: "#/components/responses/TooManyRequests"}
  /auth/logout:
    post:
      tags: [auth]
      operationId: logout
      security: [{bearerAuth: []}]
      responses:
        "204": {description: Logged out, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
  /auth/me:
    get:
      tags: [auth]
      operationId: getMe
      security: [{bearerAuth: []}]
      responses:
        "200": {description: Current user, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/User"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
  /config/ui:
    get:
      tags: [config]
      operationId: getUiConfig
      security: [{bearerAuth: []}]
      responses:
        "200": {description: Operational configuration for the UI, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/UiConfig"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
  /sessions:
    post:
      tags: [ingest]
      operationId: ingestSession
      security: [{apiKeyAuth: []}]
      requestBody: {required: true, content: {application/json: {schema: {$ref: "#/components/schemas/IngestRecord"}}}}
      responses:
        "201": {description: Stored and processed, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/IngestResult"}}}}
        "200": {description: Duplicate session_id stored and dropped from processing, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/IngestResult"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "403": {$ref: "#/components/responses/Forbidden"}
        "413": {$ref: "#/components/responses/PayloadTooLarge"}
        "415": {$ref: "#/components/responses/UnsupportedMediaType"}
        "422": {$ref: "#/components/responses/Unprocessable"}
        "429": {$ref: "#/components/responses/TooManyRequests"}
  /ingest:
    post:
      tags: [ingest]
      operationId: ingestBatch
      security: [{apiKeyAuth: []}, {bearerAuth: []}]
      requestBody:
        required: true
        content:
          application/json: {schema: {$ref: "#/components/schemas/IngestBatchRequest"}}
          multipart/form-data:
            schema:
              type: object
              required: [file]
              properties:
                file: {type: string, contentMediaType: text/csv, description: "UTF-8 CSV with the SRC-05 header, max 5 MB"}
      responses:
        "202": {description: Batch stored; pipeline scheduled, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/IngestBatchAccepted"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "403": {$ref: "#/components/responses/Forbidden"}
        "413": {$ref: "#/components/responses/PayloadTooLarge"}
        "415": {$ref: "#/components/responses/UnsupportedMediaType"}
        "422": {$ref: "#/components/responses/Unprocessable"}
        "429": {$ref: "#/components/responses/TooManyRequests"}
  /ingest/batches/{id}:
    get:
      tags: [ingest]
      operationId: getIngestBatch
      security: [{bearerAuth: []}]
      parameters: [{$ref: "#/components/parameters/IdPath"}]
      responses:
        "200": {description: Batch, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/IngestBatch"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "403": {$ref: "#/components/responses/Forbidden"}
        "404": {$ref: "#/components/responses/NotFound"}
        "422": {$ref: "#/components/responses/Unprocessable"}
  /residents:
    get:
      tags: [residents]
      operationId: listResidents
      security: [{bearerAuth: []}]
      parameters:
        - {name: sort, in: query, description: "alarm = Changed (alarm date oldest first), Needs attention, Learning, Usual, each then natural resident code (TRD 24 D-109); resident_id and last_checkin are not used by the v0.2 UI", schema: {type: string, enum: [alarm, resident_id, last_checkin], default: alarm}}
        - {name: cohort, in: query, schema: {$ref: "#/components/schemas/Cohort"}}
        - {name: include_withdrawn, in: query, schema: {type: boolean, default: false}}
        - {$ref: "#/components/parameters/Limit"}
        - {$ref: "#/components/parameters/Offset"}
      responses:
        "200": {description: Overview, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/ResidentsOverviewResponse"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "422": {$ref: "#/components/responses/Unprocessable"}
  /residents/{resident_code}:
    get:
      tags: [residents]
      operationId: getResident
      security: [{bearerAuth: []}]
      parameters: [{$ref: "#/components/parameters/ResidentCodePath"}]
      responses:
        "200": {description: Detail, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/ResidentDetail"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "404": {$ref: "#/components/responses/NotFound"}
  /residents/{resident_code}/checkins:
    get:
      tags: [residents]
      operationId: listCheckinEvents
      security: [{bearerAuth: []}]
      parameters:
        - {$ref: "#/components/parameters/ResidentCodePath"}
        - {$ref: "#/components/parameters/FromDate"}
        - {$ref: "#/components/parameters/ToDate"}
        - {$ref: "#/components/parameters/Limit"}
        - {$ref: "#/components/parameters/Offset"}
      responses:
        "200": {description: Events newest first, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/CheckinEventList"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "404": {$ref: "#/components/responses/NotFound"}
        "422": {$ref: "#/components/responses/Unprocessable"}
  /residents/{resident_code}/features:
    get:
      tags: [residents]
      operationId: getResidentFeatures
      security: [{bearerAuth: []}]
      parameters:
        - {$ref: "#/components/parameters/ResidentCodePath"}
        - {$ref: "#/components/parameters/FromDate"}
        - {$ref: "#/components/parameters/ToDate"}
      responses:
        "200": {description: Feature series, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/FeaturesResponse"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "404": {$ref: "#/components/responses/NotFound"}
        "422": {$ref: "#/components/responses/Unprocessable"}
  /residents/{resident_code}/notes:
    get:
      tags: [residents]
      operationId: listNotes
      security: [{bearerAuth: []}]
      parameters:
        - {$ref: "#/components/parameters/ResidentCodePath"}
        - {name: include_superseded, in: query, schema: {type: boolean, default: false}}
        - {$ref: "#/components/parameters/Limit"}
        - {$ref: "#/components/parameters/Offset"}
      responses:
        "200": {description: Notes newest first, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/StaffNoteList"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "404": {$ref: "#/components/responses/NotFound"}
    post:
      tags: [residents]
      operationId: createNote
      security: [{bearerAuth: []}]
      parameters: [{$ref: "#/components/parameters/ResidentCodePath"}]
      requestBody: {required: true, content: {application/json: {schema: {$ref: "#/components/schemas/StaffNoteCreate"}}}}
      responses:
        "201": {description: Created, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/StaffNote"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "403": {$ref: "#/components/responses/Forbidden"}
        "404": {$ref: "#/components/responses/NotFound"}
        "409": {$ref: "#/components/responses/Conflict"}
        "422": {$ref: "#/components/responses/Unprocessable"}
  /scores:
    get:
      tags: [scores]
      operationId: listScores
      security: [{bearerAuth: []}]
      parameters:
        - {name: resident_code, in: query, schema: {$ref: "#/components/schemas/ResidentCode"}}
        - {name: epoch, in: query, schema: {type: integer, minimum: 1}}
        - {$ref: "#/components/parameters/FromDate"}
        - {$ref: "#/components/parameters/ToDate"}
        - {$ref: "#/components/parameters/Limit"}
        - {$ref: "#/components/parameters/Offset"}
      responses:
        "200": {description: "Scored sessions (JSON) or CSV export when Accept is text/csv (researcher, admin)", headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/ScoresResponse"}}, text/csv: {schema: {type: string}}}}
        "403": {$ref: "#/components/responses/Forbidden"}
        "413": {$ref: "#/components/responses/PayloadTooLarge"}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "404": {$ref: "#/components/responses/NotFound"}
        "422": {$ref: "#/components/responses/Unprocessable"}
  /alerts:
    get:
      tags: [alerts]
      operationId: listAlerts
      security: [{bearerAuth: []}]
      parameters:
        - {name: status, in: query, schema: {$ref: "#/components/schemas/AlertStatus"}}
        - {name: resident_code, in: query, schema: {$ref: "#/components/schemas/ResidentCode"}}
        - {$ref: "#/components/parameters/Limit"}
        - {$ref: "#/components/parameters/Offset"}
      responses:
        "200": {description: Alerts, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/AlertList"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "422": {$ref: "#/components/responses/Unprocessable"}
  /alerts/{id}/reviews:
    get:
      tags: [alerts]
      operationId: listAlertReviews
      security: [{bearerAuth: []}]
      parameters: [{$ref: "#/components/parameters/IdPath"}, {$ref: "#/components/parameters/Limit"}, {$ref: "#/components/parameters/Offset"}]
      responses:
        "200": {description: Reviews newest first, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/AlertReviewList"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "404": {$ref: "#/components/responses/NotFound"}
    post:
      tags: [alerts]
      operationId: createAlertReview
      security: [{bearerAuth: []}]
      parameters: [{$ref: "#/components/parameters/IdPath"}]
      requestBody: {required: true, content: {application/json: {schema: {$ref: "#/components/schemas/AlertReviewCreate"}}}}
      responses:
        "201": {description: Review saved; alert acknowledged; tally and alarm unchanged, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/AlertReview"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "403": {$ref: "#/components/responses/Forbidden"}
        "404": {$ref: "#/components/responses/NotFound"}
        "409": {$ref: "#/components/responses/Conflict"}
        "422": {$ref: "#/components/responses/Unprocessable"}
  /alerts/{id}/snooze:
    post:
      tags: [alerts]
      operationId: snoozeAlert
      security: [{bearerAuth: []}]
      parameters: [{$ref: "#/components/parameters/IdPath"}]
      requestBody: {required: false, content: {application/json: {schema: {$ref: "#/components/schemas/SnoozeRequest"}}}}
      responses:
        "200": {description: Snoozed, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/Alert"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "403": {$ref: "#/components/responses/Forbidden"}
        "404": {$ref: "#/components/responses/NotFound"}
        "409": {$ref: "#/components/responses/Conflict"}
        "422": {$ref: "#/components/responses/Unprocessable"}
  /data-alerts:
    get:
      tags: [alerts]
      operationId: listDataAlerts
      security: [{bearerAuth: []}]
      parameters:
        - {name: status, in: query, schema: {$ref: "#/components/schemas/DataAlertStatus"}}
        - {name: kind, in: query, schema: {$ref: "#/components/schemas/DataAlertKind"}}
        - {$ref: "#/components/parameters/Limit"}
        - {$ref: "#/components/parameters/Offset"}
      responses:
        "200": {description: Data-quality alerts for the study team, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/DataAlertList"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "422": {$ref: "#/components/responses/Unprocessable"}
  /devices:
    get:
      tags: [devices]
      operationId: listDevices
      security: [{bearerAuth: []}]
      parameters: [{$ref: "#/components/parameters/Limit"}, {$ref: "#/components/parameters/Offset"}]
      responses:
        "200": {description: Device panel, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/DeviceList"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
  /analytics:
    get:
      tags: [analytics]
      operationId: getAnalytics
      security: [{bearerAuth: []}]
      responses:
        "200": {description: Summary, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/AnalyticsResponse"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "403": {$ref: "#/components/responses/Forbidden"}
  /analytics/baselines:
    get:
      tags: [analytics]
      operationId: listBaselines
      security: [{bearerAuth: []}]
      parameters:
        - {name: resident_code, in: query, schema: {$ref: "#/components/schemas/ResidentCode"}}
        - {name: epoch, in: query, schema: {type: integer, minimum: 1}}
        - {$ref: "#/components/parameters/Limit"}
        - {$ref: "#/components/parameters/Offset"}
      responses:
        "200": {description: Baselines (JSON) or CSV export when Accept is text/csv, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/BaselineRowList"}}, text/csv: {schema: {type: string}}}}
        "413": {$ref: "#/components/responses/PayloadTooLarge"}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "403": {$ref: "#/components/responses/Forbidden"}
        "422": {$ref: "#/components/responses/Unprocessable"}
  /pipeline/run:
    post:
      tags: [pipeline]
      operationId: startPipelineRun
      security: [{bearerAuth: []}, {apiKeyAuth: []}]
      requestBody: {required: true, content: {application/json: {schema: {$ref: "#/components/schemas/PipelineRunRequest"}}}}
      responses:
        "202": {description: Run started, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/PipelineRunAccepted"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "403": {$ref: "#/components/responses/Forbidden"}
        "404": {$ref: "#/components/responses/NotFound"}
        "409": {$ref: "#/components/responses/Conflict"}
        "422": {$ref: "#/components/responses/Unprocessable"}
  /pipeline/runs:
    get:
      tags: [pipeline]
      operationId: listPipelineRuns
      security: [{bearerAuth: []}]
      parameters:
        - {name: trigger, in: query, schema: {$ref: "#/components/schemas/PipelineTrigger"}}
        - {name: status, in: query, schema: {$ref: "#/components/schemas/PipelineStatus"}}
        - {$ref: "#/components/parameters/Limit"}
        - {$ref: "#/components/parameters/Offset"}
      responses:
        "200": {description: Runs newest first, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/PipelineRunList"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "403": {$ref: "#/components/responses/Forbidden"}
        "422": {$ref: "#/components/responses/Unprocessable"}
  /pipeline/runs/{id}:
    get:
      tags: [pipeline]
      operationId: getPipelineRun
      security: [{bearerAuth: []}]
      parameters: [{$ref: "#/components/parameters/IdPath"}]
      responses:
        "200": {description: Run, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/PipelineRun"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "403": {$ref: "#/components/responses/Forbidden"}
        "404": {$ref: "#/components/responses/NotFound"}
  /admissions:
    get:
      tags: [admissions]
      operationId: listAdmissions
      security: [{bearerAuth: []}]
      parameters: [{$ref: "#/components/parameters/Limit"}, {$ref: "#/components/parameters/Offset"}]
      responses:
        "200": {description: New admissions (experimental), headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}, X-EchoWell-Experimental: {$ref: "#/components/headers/XExperimental"}}, content: {application/json: {schema: {$ref: "#/components/schemas/AdmissionList"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
  /admissions/{resident_code}/comparison:
    get:
      tags: [admissions]
      operationId: getAdmissionComparison
      security: [{bearerAuth: []}]
      parameters: [{$ref: "#/components/parameters/ResidentCodePath"}]
      responses:
        "200": {description: Comparison (experimental), headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}, X-EchoWell-Experimental: {$ref: "#/components/headers/XExperimental"}}, content: {application/json: {schema: {$ref: "#/components/schemas/AdmissionComparison"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "404": {$ref: "#/components/responses/NotFound"}
  /facility/reference-ranges:
    get:
      tags: [admissions]
      operationId: listReferenceRanges
      security: [{bearerAuth: []}]
      parameters: [{$ref: "#/components/parameters/Limit"}, {$ref: "#/components/parameters/Offset"}]
      responses:
        "200": {description: Facility ranges (experimental), headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}, X-EchoWell-Experimental: {$ref: "#/components/headers/XExperimental"}}, content: {application/json: {schema: {$ref: "#/components/schemas/ReferenceRangeList"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
  /users:
    get:
      tags: [users]
      operationId: listUsers
      security: [{bearerAuth: []}]
      parameters:
        - {name: role, in: query, schema: {$ref: "#/components/schemas/Role"}}
        - {name: active, in: query, schema: {type: boolean}}
        - {$ref: "#/components/parameters/Limit"}
        - {$ref: "#/components/parameters/Offset"}
      responses:
        "200": {description: Users, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/UserList"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "403": {$ref: "#/components/responses/Forbidden"}
    post:
      tags: [users]
      operationId: createUser
      security: [{bearerAuth: []}]
      requestBody: {required: true, content: {application/json: {schema: {$ref: "#/components/schemas/UserCreate"}}}}
      responses:
        "201": {description: Created, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/User"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "403": {$ref: "#/components/responses/Forbidden"}
        "409": {$ref: "#/components/responses/Conflict"}
        "422": {$ref: "#/components/responses/Unprocessable"}
  /users/{id}:
    patch:
      tags: [users]
      operationId: updateUser
      security: [{bearerAuth: []}]
      parameters: [{$ref: "#/components/parameters/IdPath"}]
      requestBody: {required: true, content: {application/json: {schema: {$ref: "#/components/schemas/UserUpdate"}}}}
      responses:
        "200": {description: Updated, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/json: {schema: {$ref: "#/components/schemas/User"}}}}
        "401": {$ref: "#/components/responses/Unauthorized"}
        "403": {$ref: "#/components/responses/Forbidden"}
        "404": {$ref: "#/components/responses/NotFound"}
        "409": {$ref: "#/components/responses/Conflict"}
        "422": {$ref: "#/components/responses/Unprocessable"}

components:
  securitySchemes:
    bearerAuth: {type: http, scheme: bearer, bearerFormat: JWT}
    apiKeyAuth: {type: apiKey, in: header, name: X-API-Key}

  headers:
    XRequestID: {description: Request correlation ID, schema: {type: string}}
    XExperimental: {description: Future / experimental study arm, schema: {type: string, const: "true"}}
    RetryAfter: {description: Seconds to wait, schema: {type: integer}}

  parameters:
    Limit: {name: limit, in: query, schema: {type: integer, minimum: 1, maximum: 500, default: 50}}
    Offset: {name: offset, in: query, schema: {type: integer, minimum: 0, default: 0}}
    FromDate: {name: from, in: query, schema: {type: string, format: date}}
    ToDate: {name: to, in: query, schema: {type: string, format: date}}
    IdPath: {name: id, in: path, required: true, schema: {type: string, format: uuid}}
    ResidentCodePath: {name: resident_code, in: path, required: true, schema: {$ref: "#/components/schemas/ResidentCode"}}

  responses:
    Unauthorized: {description: "NOT_AUTHENTICATED | INVALID_CREDENTIALS | TOKEN_EXPIRED | TOKEN_INVALID | API_KEY_INVALID", headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/problem+json: {schema: {$ref: "#/components/schemas/Problem"}}}}
    Forbidden: {description: "FORBIDDEN | DEVICE_KEY_MISMATCH", headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/problem+json: {schema: {$ref: "#/components/schemas/Problem"}}}}
    NotFound: {description: "*_NOT_FOUND", headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/problem+json: {schema: {$ref: "#/components/schemas/Problem"}}}}
    Conflict: {description: "ALERT_CLOSED | EMAIL_ALREADY_EXISTS | LAST_ADMIN | PIPELINE_RUN_IN_PROGRESS", headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/problem+json: {schema: {$ref: "#/components/schemas/Problem"}}}}
    PayloadTooLarge: {description: PAYLOAD_TOO_LARGE, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/problem+json: {schema: {$ref: "#/components/schemas/Problem"}}}}
    UnsupportedMediaType: {description: UNSUPPORTED_MEDIA_TYPE, headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/problem+json: {schema: {$ref: "#/components/schemas/Problem"}}}}
    Unprocessable: {description: "VALIDATION_ERROR and other 422 codes (TRD 05 §4.7)", headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}}, content: {application/problem+json: {schema: {$ref: "#/components/schemas/Problem"}}}}
    TooManyRequests: {description: "RATE_LIMITED | ACCOUNT_TEMPORARILY_LOCKED", headers: {X-Request-ID: {$ref: "#/components/headers/XRequestID"}, Retry-After: {$ref: "#/components/headers/RetryAfter"}}, content: {application/problem+json: {schema: {$ref: "#/components/schemas/Problem"}}}}

  schemas:
    # ---------- shared scalars and enums ----------
    ResidentCode: {type: string, pattern: "^[A-Z0-9]{1,16}$", examples: ["R09"], description: "single pattern for resident codes in all TRDs (TRD 20 residents_resident_code_ck)"}
    DeviceCode: {type: string, pattern: "^[A-Z0-9]{1,16}$", examples: ["D07B"], description: "single pattern for device codes in all TRDs (TRD 20 devices_device_code_ck)"}
    SessionId: {type: string, pattern: "^[A-Z0-9]{1,16}-[0-9]{8}-[0-9]{2}$", examples: ["R09-20261021-01"]}
    ProcessedStatus: {type: string, enum: [usable, set_aside, quarantined, duplicate]}
    IngestOutcome: {type: string, enum: [usable, set_aside, quarantined, duplicate, pending]}
    DayStatus: {type: string, enum: [checked_in, missing_resident, missing_device_gap]}
    DisplayStatus: {type: string, enum: [alarm_on, no_alarm, baseline_forming], description: "pipeline status (TRD 23 §4.4.3); the UI maps status + needs_attention to Changed / Needs attention / Learning / Usual (TRD 24 D-109)"}
    AttentionReason: {type: string, enum: [baseline_stalled, high_set_aside], description: "subset of DataAlertKind that sets needs_attention (TRD 24 D-109, D-114; OQ-31)"}
    AlarmState: {type: string, enum: ["off", rings, "on"]}
    AlertStatus: {type: string, enum: [open, acknowledged, closed]}
    NoteType: {type: string, enum: [observation, action_taken, follow_up]}
    Role: {type: string, enum: [admin, clinician, researcher]}
    Cohort: {type: string, enum: [longitudinal, new_admission]}
    ResidentStatus: {type: string, enum: [active, withdrawn]}
    Sex: {type: [string, "null"], enum: [F, M, null]}
    PipelineTrigger: {type: string, enum: [ingest, nightly, manual, test]}
    PipelineStatus: {type: string, enum: [running, succeeded, failed]}
    ConfigProfile: {type: string, enum: [production, test_v0_1]}
    IngestSource: {type: string, enum: [api_single, api_batch, csv_upload, seed]}
    CheckinEventType: {type: string, enum: [alarm_on, watching_started, baseline_complete, baseline_restarted, set_aside, quarantined, missed, device_silent, checkins_started], description: "API-only enum, derived on read (TRD 23 §4.4.4); no database enum (OAS-007). checkins_started added by TRD 24 D-113/D-114"}
    ComparisonStatus: {type: string, enum: [outside_range, within_range, not_enough_checkins, range_not_available], description: "range_not_available = no facility reference range exists (TRD 02 FR-202, OQ-08), UI 'Facility range not available yet'"}
    RestartCause: {type: [string, "null"], enum: [device, firmware, software, null]}
    ReviewOutcome: {type: string, enum: [no_concern, known_cause, referred, data_problem]}
    ReviewExplanationCode:
      type: string
      pattern: "^[a-z_]{1,40}$"
      description: "code from config list review_explanations (OQ-25); v0.1 values cold_cough_sore_throat, dental_dentures, medication_change, poor_sleep_unusual_day, room_device_moved"
    ReviewExplanation:
      type: object
      required: [code, label]
      properties:
        code: {$ref: "#/components/schemas/ReviewExplanationCode"}
        label: {type: string, examples: ["Cold, cough or sore throat"]}
    UiConfig:
      type: object
      required: [meta, alert_snooze_hours, review_explanations]
      properties:
        meta: {$ref: "#/components/schemas/Meta"}
        alert_snooze_hours: {type: integer, minimum: 1, maximum: 168, examples: [24]}
        review_explanations: {type: array, minItems: 1, maxItems: 20, items: {$ref: "#/components/schemas/ReviewExplanation"}}
    DataAlertKind: {type: string, enum: [baseline_stalled, possible_other_speaker, high_set_aside, device_silent, review_flagged_data_problem]}
    DataAlertStatus: {type: string, enum: [open, resolved]}
    Meta:
      type: object
      required: [facility_name, facility_tz, data_source_label, as_of, baseline_n, cusum_h, pipeline_profile]
      properties:
        facility_name: {type: string, examples: ["Edgewood"]}
        facility_tz: {type: string, examples: ["America/Chicago"]}
        data_source_label: {type: string, examples: ["pipeline test data v0.1"]}
        as_of: {type: [string, "null"], format: date-time, description: as-of of the latest succeeded pipeline run}
        baseline_n: {type: integer, minimum: 1}
        cusum_h: {type: number}
        pipeline_profile: {$ref: "#/components/schemas/ConfigProfile"}
    ScoredFeatureKey:
      type: string
      enum: [loudness_dbfs, total_phrase_duration_s, speech_rate_syl_per_s, articulation_rate_syl_per_s, number_of_pauses, pause_fraction, voiced_fraction]
    FeatureKey:
      type: string
      enum: [loudness_dbfs, total_phrase_duration_s, speech_rate_syl_per_s, articulation_rate_syl_per_s, number_of_pauses, pause_fraction, voiced_fraction,
             mean_f0_hz, f0_variability_st, jitter_local_pct, shimmer_local_pct, hnr_db, cpps_db, alpha_ratio_db, hammarberg_index_db, mfcc1, mfcc2, mfcc3, mfcc4]
    BaselineFeatureKey:
      type: string
      enum: [loudness_dbfs, total_phrase_duration_s, speech_rate_syl_per_s, articulation_rate_syl_per_s, number_of_pauses, pause_fraction, voiced_fraction,
             mean_f0_hz, f0_variability_st, jitter_local_pct, shimmer_local_pct, hnr_db, cpps_db, alpha_ratio_db, hammarberg_index_db, mfcc1, mfcc2, mfcc3, mfcc4, composite]
    PageMeta:
      type: object
      required: [meta, total, limit, offset]
      properties:
        meta: {$ref: "#/components/schemas/Meta"}
        total: {type: integer, minimum: 0}
        limit: {type: integer, minimum: 1, maximum: 500}
        offset: {type: integer, minimum: 0}
    Last30Days:
      type: object
      required: [used, set_aside, quarantined, missed]
      properties:
        used: {type: integer, minimum: 0}
        set_aside: {type: integer, minimum: 0}
        quarantined: {type: integer, minimum: 0}
        missed: {type: integer, minimum: 0, description: missing_resident + missing_device_gap}
    DateWindow:
      type: object
      required: [from, to, days]
      properties:
        from: {type: string, format: date, description: "first local date; not before the resident's enrolled_on in ResidentDetail"}
        to: {type: string, format: date, description: as-of local date}
        days: {type: integer, minimum: 0, description: "local days from..to inclusive (TRD 24 D-114)"}

    # ---------- errors, health, auth ----------
    ProblemFieldError:
      type: object
      required: [field, code, message]
      properties:
        field: {type: string, examples: ["records.3.loudness_dbfs"]}
        code: {type: string, description: "ingest endpoints: TRD 10 ING-023 field codes; other endpoints: Pydantic error type", examples: ["invalid_type", "unknown_resident", "float_parsing"]}
        message: {type: string}
    Problem:
      type: object
      required: [type, title, status, detail, request_id, errors]
      properties:
        type: {type: string, pattern: "^urn:echowell:error:[A-Z_]+$"}
        title: {type: string}
        status: {type: integer, minimum: 400, maximum: 599}
        detail: {type: string}
        request_id: {type: string}
        errors: {type: array, items: {$ref: "#/components/schemas/ProblemFieldError"}}
    Health:
      type: object
      required: [status, database, version, time]
      properties:
        status: {type: string, enum: [ok, degraded]}
        database: {type: string, enum: [ok, unavailable]}
        version: {type: string, description: GIT_SHA}
        time: {type: string, format: date-time}
    LoginRequest:
      type: object
      additionalProperties: false
      required: [email, password]
      properties:
        email: {type: string, format: email, maxLength: 254}
        password: {type: string, minLength: 1, maxLength: 128}
    User:
      type: object
      required: [id, email, display_name, role, active, last_login_at, created_at]
      properties:
        id: {type: string, format: uuid}
        email: {type: string, format: email}
        display_name: {type: string, minLength: 1, maxLength: 100}
        role: {$ref: "#/components/schemas/Role"}
        active: {type: boolean}
        last_login_at: {type: [string, "null"], format: date-time}
        created_at: {type: string, format: date-time}
    UserCreate:
      type: object
      additionalProperties: false
      required: [email, display_name, role, password]
      properties:
        email: {type: string, format: email, maxLength: 254}
        display_name: {type: string, minLength: 1, maxLength: 100}
        role: {$ref: "#/components/schemas/Role"}
        password: {type: string, minLength: 12, maxLength: 128}
    UserUpdate:
      type: object
      additionalProperties: false
      minProperties: 1
      properties:
        display_name: {type: string, minLength: 1, maxLength: 100}
        role: {$ref: "#/components/schemas/Role"}
        active: {type: boolean}
        password: {type: string, minLength: 12, maxLength: 128}
    UserList:
      allOf:
        - {$ref: "#/components/schemas/PageMeta"}
        - {type: object, required: [items], properties: {items: {type: array, items: {$ref: "#/components/schemas/User"}}}}
    Token:
      type: object
      required: [access_token, token_type, expires_in, user]
      properties:
        access_token: {type: string}
        token_type: {type: string, const: bearer}
        expires_in: {type: integer, examples: [3600]}
        user: {$ref: "#/components/schemas/User"}

    # ---------- ingest ----------
    IngestRecord:
      type: object
      additionalProperties: false
      description: Schema v0.1; property order equals the SRC-05 CSV header. Feature names are placeholders (OQ-03) mapped by configuration.
      required: [schema_version, session_id, resident_id, device_id, timestamp_utc, mic_noise_level_dbfs, audio_quality_flag,
                 extraction_software_version, device_firmware_version, speech_duration_s, phrase_id,
                 loudness_dbfs, total_phrase_duration_s, speech_rate_syl_per_s, articulation_rate_syl_per_s, number_of_pauses,
                 pause_fraction, voiced_fraction, mean_f0_hz, f0_variability_st, jitter_local_pct, shimmer_local_pct, hnr_db,
                 cpps_db, alpha_ratio_db, hammarberg_index_db, mfcc1, mfcc2, mfcc3, mfcc4]
      properties:
        schema_version: {type: string, enum: ["0.1"]}
        session_id: {$ref: "#/components/schemas/SessionId"}
        resident_id: {$ref: "#/components/schemas/ResidentCode"}
        device_id: {$ref: "#/components/schemas/DeviceCode"}
        timestamp_utc: {type: string, pattern: "^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$", examples: ["2026-10-21 19:07:50"]}
        mic_noise_level_dbfs: {type: number}
        audio_quality_flag: {type: string, enum: [ok, poor]}
        extraction_software_version: {type: string, minLength: 1, maxLength: 64}
        device_firmware_version: {type: string, minLength: 1, maxLength: 64}
        speech_duration_s: {type: number, minimum: 0}
        phrase_id: {type: string, minLength: 1, maxLength: 16}
        loudness_dbfs: {type: number}
        total_phrase_duration_s: {type: number, minimum: 0}
        speech_rate_syl_per_s: {type: number}
        articulation_rate_syl_per_s: {type: number}
        number_of_pauses: {type: integer, minimum: 0}
        pause_fraction: {type: number, minimum: 0, maximum: 1}
        voiced_fraction: {type: number, minimum: 0, maximum: 1}
        mean_f0_hz: {type: number}
        f0_variability_st: {type: number}
        jitter_local_pct: {type: number}
        shimmer_local_pct: {type: number}
        hnr_db: {type: number}
        cpps_db: {type: number}
        alpha_ratio_db: {type: number}
        hammarberg_index_db: {type: number}
        mfcc1: {type: number}
        mfcc2: {type: number}
        mfcc3: {type: number}
        mfcc4: {type: number}
    IngestResult:
      type: object
      required: [raw_session_id, arrival_seq, session_id, status_after_processing, reasons, pipeline_run_id]
      properties:
        raw_session_id: {type: string, format: uuid}
        arrival_seq: {type: integer, minimum: 1}
        session_id: {$ref: "#/components/schemas/SessionId"}
        status_after_processing: {$ref: "#/components/schemas/IngestOutcome"}
        reasons: {type: array, items: {type: string}}
        pipeline_run_id: {type: [string, "null"], format: uuid}
    IngestBatchRequest:
      type: object
      additionalProperties: false
      required: [records]
      properties:
        records: {type: array, minItems: 1, maxItems: 5000, items: {$ref: "#/components/schemas/IngestRecord"}}
    IngestBatchAccepted:
      type: object
      required: [ingest_batch_id, source, accepted, rejected, duplicates, pipeline_run_id]
      properties:
        ingest_batch_id: {type: string, format: uuid}
        source: {$ref: "#/components/schemas/IngestSource"}
        accepted: {type: integer, minimum: 0, description: "stored in raw_sessions, duplicates included"}
        rejected: {type: integer, minimum: 0}
        duplicates: {type: integer, minimum: 0}
        pipeline_run_id: {type: [string, "null"], format: uuid, description: null when no first-arrival record was accepted}
    IngestRejection:
      type: object
      required: [row_number, session_id, received_at, errors]
      properties:
        row_number: {type: integer, minimum: 1, description: 1-based position in the batch (CSV excludes header)}
        session_id: {type: [string, "null"]}
        received_at: {type: string, format: date-time}
        errors: {type: array, items: {$ref: "#/components/schemas/ProblemFieldError"}}
    IngestBatch:
      type: object
      required: [id, source, filename, record_count, accepted_count, rejected_count, duplicate_count, uploaded_by, received_at, pipeline_run_id, rejections]
      properties:
        id: {type: string, format: uuid}
        source: {$ref: "#/components/schemas/IngestSource"}
        filename: {type: [string, "null"]}
        record_count: {type: integer}
        accepted_count: {type: integer}
        rejected_count: {type: integer}
        duplicate_count: {type: integer}
        uploaded_by: {type: [string, "null"], format: uuid}
        received_at: {type: string, format: date-time}
        pipeline_run_id: {type: [string, "null"], format: uuid}
        rejections: {type: array, items: {$ref: "#/components/schemas/IngestRejection"}}

    # ---------- residents ----------
    BaselineProgress:
      type: object
      required: [n_usable, n_required]
      properties:
        n_usable: {type: integer, minimum: 0, description: usable sessions counted toward the current epoch baseline (capped at n_required)}
        n_required: {type: integer, minimum: 1, description: baseline_n of the active profile}
    ResidentOverviewRow:
      type: object
      required: [resident_code, cohort, resident_status, device_code, device_shared, previous_device_code, status, needs_attention,
                 attention_reasons, alarm_since, open_alert_id, alarm_reviewed, current_epoch, baseline_restarted_on,
                 restart_cause, baseline_progress, last_checkin_at, last_checkin_local, last_30_days]
      properties:
        resident_code: {$ref: "#/components/schemas/ResidentCode"}
        cohort: {$ref: "#/components/schemas/Cohort"}
        resident_status: {$ref: "#/components/schemas/ResidentStatus"}
        device_code: {type: [string, "null"]}
        device_shared: {type: boolean}
        previous_device_code: {type: [string, "null"], description: "rendered as '(replaced D07)' in the chart banner (TRD 11 UX-063)"}
        status: {$ref: "#/components/schemas/DisplayStatus"}
        needs_attention: {type: boolean, description: "true when the resident has an open data alert of kind baseline_stalled or high_set_aside (TRD 24 D-114)"}
        attention_reasons: {type: array, uniqueItems: true, items: {$ref: "#/components/schemas/AttentionReason"}, description: "kinds behind needs_attention in the order baseline_stalled, high_set_aside; empty when needs_attention is false"}
        alarm_since: {type: [string, "null"], format: date}
        open_alert_id: {type: [string, "null"], format: uuid}
        alarm_reviewed: {type: [boolean, "null"], description: "null without a non-closed alert in the current epoch; true when that alert is acknowledged, false when open (TRD 24 D-114)"}
        current_epoch: {type: [integer, "null"], minimum: 1}
        baseline_restarted_on: {type: [string, "null"], format: date, description: start date of current epoch when epoch > 1}
        restart_cause: {$ref: "#/components/schemas/RestartCause", description: "restart cause of the current epoch when current_epoch > 1 (TRD 06 DB-065); null when current_epoch is 1 or null (TRD 24 D-114)"}
        baseline_progress: {$ref: "#/components/schemas/BaselineProgress"}
        last_checkin_at: {type: [string, "null"], format: date-time}
        last_checkin_local: {type: [string, "null"], format: date-time}
        last_30_days: {$ref: "#/components/schemas/Last30Days"}
    OverviewSummary:
      type: object
      description: "residents per display status, first match Changed, Needs attention, Learning, Usual (TRD 24 D-109, D-114); the four counts sum to total"
      required: [changed, needs_attention, learning, usual]
      properties:
        changed: {type: integer, minimum: 0, description: "status alarm_on"}
        needs_attention: {type: integer, minimum: 0, description: "needs_attention true and status not alarm_on"}
        learning: {type: integer, minimum: 0, description: "status baseline_forming and needs_attention false"}
        usual: {type: integer, minimum: 0, description: "status no_alarm and needs_attention false"}
    ResidentsOverviewResponse:
      allOf:
        - {$ref: "#/components/schemas/PageMeta"}
        - type: object
          required: [window, summary, items]
          properties:
            window: {$ref: "#/components/schemas/DateWindow"}
            summary: {$ref: "#/components/schemas/OverviewSummary"}
            items: {type: array, items: {$ref: "#/components/schemas/ResidentOverviewRow"}}
    EpochInfo:
      type: object
      required: [epoch_number, device_code, device_firmware_version, extraction_software_version, started_at, started_on,
                 from_value, to_value]
      properties:
        epoch_number: {type: integer, minimum: 1}
        device_code: {type: string}
        device_firmware_version: {type: string}
        extraction_software_version: {type: string}
        started_at: {type: string, format: date-time}
        started_on: {type: string, format: date}
        from_value: {type: [string, "null"], description: "previous value of the part named by ResidentDetail.restart_cause (derived as for the baseline_restarted event, TRD 06 DB-065); null for epoch 1"}
        to_value: {type: [string, "null"], description: "new value of that part; null for epoch 1"}
    BaselineInfo:
      type: object
      required: [state, n_usable, n_required, first_session_id, frozen_after_session_id, first_local_date, frozen_after_local_date]
      properties:
        state: {type: string, enum: [forming, frozen]}
        n_usable: {type: integer, minimum: 0}
        n_required: {type: integer, minimum: 1}
        first_session_id: {type: [string, "null"]}
        frozen_after_session_id: {type: [string, "null"]}
        first_local_date: {type: [string, "null"], format: date}
        frozen_after_local_date: {type: [string, "null"], format: date}
    DeviceRef:
      type: object
      required: [device_code, shared, shared_with, previous_device_code]
      properties:
        device_code: {type: [string, "null"]}
        shared: {type: boolean}
        shared_with: {type: array, items: {$ref: "#/components/schemas/ResidentCode"}}
        previous_device_code: {type: [string, "null"]}
    Explanation:
      type: object
      description: Structured facts only; wording is rendered by the frontend from PI-reviewed strings (OQ-12).
      required: [compared_with, alarm_crossed_on, still_above_line, baseline_restarted_on, baseline_n_usable, baseline_n_required]
      properties:
        compared_with: {type: string, const: own_baseline}
        alarm_crossed_on: {type: [string, "null"], format: date}
        still_above_line: {type: boolean, description: "true when the latest cusum_tally of the current epoch is >= cusum_h (TRD 24 D-82)"}
        baseline_restarted_on: {type: [string, "null"], format: date}
        baseline_n_usable: {type: integer}
        baseline_n_required: {type: integer}
    ResidentDetail:
      type: object
      required: [meta, resident_code, cohort, resident_status, sex, enrolled_on, admitted_on, withdrawn_on, status, needs_attention,
                 attention_reasons, alarm_reviewed, restart_cause, device, current_epoch, epoch_count, baseline, watching_since,
                 alarm_since, open_alert_id, current_tally, last_checkin_at, last_checkin_local, window, last_30_days, explanation]
      properties:
        resident_code: {$ref: "#/components/schemas/ResidentCode"}
        cohort: {$ref: "#/components/schemas/Cohort"}
        resident_status: {$ref: "#/components/schemas/ResidentStatus"}
        sex: {$ref: "#/components/schemas/Sex"}
        enrolled_on: {type: string, format: date}
        admitted_on: {type: [string, "null"], format: date}
        withdrawn_on: {type: [string, "null"], format: date}
        meta: {$ref: "#/components/schemas/Meta"}
        status: {$ref: "#/components/schemas/DisplayStatus"}
        needs_attention: {type: boolean, description: "as ResidentOverviewRow (TRD 24 D-114)"}
        attention_reasons: {type: array, uniqueItems: true, items: {$ref: "#/components/schemas/AttentionReason"}}
        alarm_reviewed: {type: [boolean, "null"], description: "as ResidentOverviewRow"}
        restart_cause: {$ref: "#/components/schemas/RestartCause", description: "as ResidentOverviewRow"}
        device: {$ref: "#/components/schemas/DeviceRef"}
        current_epoch: {oneOf: [{$ref: "#/components/schemas/EpochInfo"}, {type: "null"}]}
        epoch_count: {type: integer, minimum: 0}
        baseline: {$ref: "#/components/schemas/BaselineInfo"}
        watching_since: {type: [string, "null"], format: date, description: "local date of first scored session in current epoch; before any, the local date after the freeze session"}
        alarm_since: {type: [string, "null"], format: date}
        open_alert_id: {type: [string, "null"], format: uuid}
        current_tally: {type: [number, "null"]}
        last_checkin_at: {type: [string, "null"], format: date-time, description: latest non-duplicate record of any status}
        last_checkin_local: {type: [string, "null"], format: date-time}
        window: {$ref: "#/components/schemas/DateWindow", description: "the resident's 30-day window of last_30_days (TRD 24 D-114)"}
        last_30_days: {$ref: "#/components/schemas/Last30Days"}
        explanation: {$ref: "#/components/schemas/Explanation"}
    CheckinEvent:
      type: object
      required: [local_date, event_type, epoch_number, session_id, detail, cusum_tally, restart_cause, previous_device_code, from_value, to_value, device_code]
      properties:
        local_date: {type: string, format: date}
        event_type: {$ref: "#/components/schemas/CheckinEventType"}
        epoch_number: {type: [integer, "null"]}
        session_id: {type: [string, "null"]}
        detail: {type: [string, "null"], description: 'pipeline reason text or progress, e.g. "16 of 16"'}
        cusum_tally: {type: [number, "null"]}
        restart_cause: {$ref: "#/components/schemas/RestartCause"}
        previous_device_code: {type: [string, "null"], description: "baseline_restarted only: device of the previous epoch"}
        from_value: {type: [string, "null"], description: "baseline_restarted only: previous value of the restart_cause part"}
        to_value: {type: [string, "null"], description: "baseline_restarted only: new value of the restart_cause part"}
        device_code: {type: [string, "null"], description: "checkins_started only: device of the resident's first non-duplicate record (TRD 24 D-114); null on other events"}
    CheckinEventList:
      allOf:
        - {$ref: "#/components/schemas/PageMeta"}
        - {type: object, required: [items], properties: {items: {type: array, items: {$ref: "#/components/schemas/CheckinEvent"}}}}
    FeaturePoint:
      type: object
      required: [session_id, local_date, is_morning, raw_value, adjusted_value, z, in_baseline]
      properties:
        session_id: {$ref: "#/components/schemas/SessionId"}
        local_date: {type: string, format: date}
        is_morning: {type: boolean}
        raw_value: {type: number}
        adjusted_value: {type: number}
        z: {type: [number, "null"], description: null for sessions not scored}
        in_baseline: {type: boolean}
    FeatureSeries:
      type: object
      required: [feature_key, label, unit, composite_sign, baseline_median, baseline_robust_spread, points]
      properties:
        feature_key: {$ref: "#/components/schemas/ScoredFeatureKey"}
        label: {type: string, examples: ["Quieter (loudness)"]}
        unit: {type: string}
        composite_sign: {type: integer, enum: [-1, 1]}
        baseline_median: {type: [number, "null"]}
        baseline_robust_spread: {type: [number, "null"]}
        points: {type: array, items: {$ref: "#/components/schemas/FeaturePoint"}}
    FeaturesResponse:
      type: object
      required: [meta, resident_code, epoch_number, scored_features, stored_feature_keys]
      properties:
        meta: {$ref: "#/components/schemas/Meta"}
        resident_code: {$ref: "#/components/schemas/ResidentCode"}
        epoch_number: {type: [integer, "null"]}
        scored_features: {type: array, minItems: 7, maxItems: 7, items: {$ref: "#/components/schemas/FeatureSeries"}}
        stored_feature_keys: {type: array, minItems: 12, maxItems: 12, items: {$ref: "#/components/schemas/FeatureKey"}}

    # ---------- scores and alerts ----------
    ZValues:
      type: object
      additionalProperties: false
      required: [z_loudness_dbfs, z_total_phrase_duration_s, z_speech_rate_syl_per_s, z_articulation_rate_syl_per_s, z_number_of_pauses, z_pause_fraction, z_voiced_fraction]
      properties:
        z_loudness_dbfs: {type: number}
        z_total_phrase_duration_s: {type: number}
        z_speech_rate_syl_per_s: {type: number}
        z_articulation_rate_syl_per_s: {type: number}
        z_number_of_pauses: {type: number}
        z_pause_fraction: {type: number}
        z_voiced_fraction: {type: number}
    ScoreRow:
      type: object
      required: [session_id, resident_code, epoch_number, local_date, is_morning, z, composite_raw, composite_z, cusum_tally, alarm_state]
      properties:
        session_id: {$ref: "#/components/schemas/SessionId"}
        resident_code: {$ref: "#/components/schemas/ResidentCode"}
        epoch_number: {type: integer, minimum: 1}
        local_date: {type: string, format: date}
        is_morning: {type: boolean}
        z: {$ref: "#/components/schemas/ZValues"}
        composite_raw: {type: number}
        composite_z: {type: number}
        cusum_tally: {type: number, minimum: 0}
        alarm_state: {$ref: "#/components/schemas/AlarmState"}
    BaselinePeriod:
      type: object
      required: [resident_code, epoch_number, first_local_date, frozen_after_local_date, frozen_after_session_id, n_sessions]
      properties:
        resident_code: {$ref: "#/components/schemas/ResidentCode"}
        epoch_number: {type: integer}
        first_local_date: {type: string, format: date}
        frozen_after_local_date: {type: string, format: date}
        frozen_after_session_id: {$ref: "#/components/schemas/SessionId"}
        n_sessions: {type: integer}
    ScoresResponse:
      allOf:
        - {$ref: "#/components/schemas/PageMeta"}
        - type: object
          required: [cusum_k, baseline_periods, items]
          properties:
            cusum_k: {type: number, examples: [0.5]}
            baseline_periods: {type: array, items: {$ref: "#/components/schemas/BaselinePeriod"}}
            items: {type: array, items: {$ref: "#/components/schemas/ScoreRow"}}
    Alert:
      type: object
      required: [id, resident_code, device_code, epoch_number, session_id, triggered_at, local_date, cusum_value, current_tally, open_days,
                 status, reviewed, review_count, last_reviewed_at, snoozed_until, snoozed_by, leaning_most, closed_reason]
      properties:
        id: {type: string, format: uuid, description: stable across rebuilds (upsert key epoch_id + session_id)}
        resident_code: {$ref: "#/components/schemas/ResidentCode"}
        device_code: {type: [string, "null"]}
        epoch_number: {type: integer}
        session_id: {$ref: "#/components/schemas/SessionId"}
        triggered_at: {type: string, format: date-time}
        local_date: {type: string, format: date}
        cusum_value: {type: number, description: tally at first crossing}
        current_tally: {type: [number, "null"], description: cusum_state.current_tally of the alert's epoch}
        open_days: {type: integer, minimum: 0, description: as-of local date minus local_date}
        status: {$ref: "#/components/schemas/AlertStatus"}
        reviewed: {type: boolean, description: true when status is acknowledged}
        review_count: {type: integer, minimum: 0}
        last_reviewed_at: {type: [string, "null"], format: date-time}
        snoozed_until: {type: [string, "null"], format: date-time}
        snoozed_by: {type: [string, "null"], format: uuid}
        leaning_most: {type: array, maxItems: 3, items: {$ref: "#/components/schemas/ScoredFeatureKey"}}
        closed_reason: {type: [string, "null"], examples: ["epoch ended"]}
    AlertList:
      allOf:
        - {$ref: "#/components/schemas/PageMeta"}
        - {type: object, required: [items], properties: {items: {type: array, items: {$ref: "#/components/schemas/Alert"}}}}
    AlertReviewCreate:
      type: object
      additionalProperties: false
      required: [outcome]
      properties:
        explanations: {type: array, maxItems: 5, uniqueItems: true, default: [], items: {$ref: "#/components/schemas/ReviewExplanationCode"}}
        outcome: {$ref: "#/components/schemas/ReviewOutcome"}
        note: {type: [string, "null"], maxLength: 2000}
    AlertReview:
      type: object
      required: [id, alert_id, reviewer, explanations, outcome, note, created_at]
      properties:
        id: {type: string, format: uuid}
        alert_id: {type: string, format: uuid}
        reviewer:
          type: object
          required: [id, display_name]
          properties: {id: {type: string, format: uuid}, display_name: {type: string}}
        explanations: {type: array, items: {$ref: "#/components/schemas/ReviewExplanationCode"}}
        outcome: {$ref: "#/components/schemas/ReviewOutcome"}
        note: {type: [string, "null"]}
        created_at: {type: string, format: date-time}
    AlertReviewList:
      allOf:
        - {$ref: "#/components/schemas/PageMeta"}
        - {type: object, required: [items], properties: {items: {type: array, items: {$ref: "#/components/schemas/AlertReview"}}}}
    SnoozeRequest:
      type: object
      additionalProperties: false
      properties:
        hours: {type: integer, minimum: 1, maximum: 168, default: 24}
    DataAlert:
      type: object
      required: [id, kind, resident_code, device_code, title, detail, status, first_detected_at, last_detected_at, pipeline_run_id]
      properties:
        id: {type: string, format: uuid}
        kind: {$ref: "#/components/schemas/DataAlertKind"}
        resident_code: {type: [string, "null"]}
        device_code: {type: [string, "null"]}
        title: {type: string, examples: ["R08 · baseline stuck at 13 of 16"]}
        detail: {type: string, examples: ["baseline stuck at 13 of 16. 12 missed and 5 set aside in 30 days."], description: "v0.2 text without the leading code (TRD 09 §4.9, TRD 24 D-114); the UI renders '<code>: <detail>'"}
        status: {$ref: "#/components/schemas/DataAlertStatus"}
        first_detected_at: {type: string, format: date-time}
        last_detected_at: {type: string, format: date-time}
        pipeline_run_id: {type: [string, "null"], format: uuid}
    DataAlertList:
      allOf:
        - {$ref: "#/components/schemas/PageMeta"}
        - {type: object, required: [items], properties: {items: {type: array, items: {$ref: "#/components/schemas/DataAlert"}}}}
    StaffNoteCreate:
      type: object
      additionalProperties: false
      required: [note_type, body]
      properties:
        note_type: {$ref: "#/components/schemas/NoteType"}
        body: {type: string, minLength: 1, maxLength: 2000}
        alert_id: {type: [string, "null"], format: uuid}
        supersedes_id: {type: [string, "null"], format: uuid}
    StaffNote:
      type: object
      required: [id, resident_code, alert_id, author, note_type, body, supersedes_id, created_at]
      properties:
        id: {type: string, format: uuid}
        resident_code: {$ref: "#/components/schemas/ResidentCode"}
        alert_id: {type: [string, "null"], format: uuid}
        author:
          type: object
          required: [id, display_name]
          properties: {id: {type: string, format: uuid}, display_name: {type: string}}
        note_type: {$ref: "#/components/schemas/NoteType"}
        body: {type: string}
        supersedes_id: {type: [string, "null"], format: uuid}
        created_at: {type: string, format: date-time}
    StaffNoteList:
      allOf:
        - {$ref: "#/components/schemas/PageMeta"}
        - {type: object, required: [items], properties: {items: {type: array, items: {$ref: "#/components/schemas/StaffNote"}}}}

    # ---------- devices ----------
    Device:
      type: object
      required: [device_code, room_label, active, resident_codes, shared, replaces_device_code, replaced_by_device_code, in_use_since,
                 in_use_until, last_upload_at, last_upload_local, firmware_version, uploaded_on_as_of_date, silent_days_last_30,
                 device_gap_days_last_30]
      properties:
        device_code: {$ref: "#/components/schemas/DeviceCode"}
        room_label: {type: [string, "null"], description: non-identifying label only}
        active: {type: boolean}
        resident_codes: {type: array, items: {$ref: "#/components/schemas/ResidentCode"}}
        shared: {type: boolean}
        replaces_device_code: {type: [string, "null"]}
        replaced_by_device_code: {type: [string, "null"]}
        in_use_since: {type: [string, "null"], format: date}
        in_use_until: {type: [string, "null"], format: date, description: "last local day of the device's last assignment; null while it has a current assignment"}
        last_upload_at: {type: [string, "null"], format: date-time}
        last_upload_local: {type: [string, "null"], format: date-time}
        firmware_version: {type: [string, "null"]}
        uploaded_on_as_of_date: {type: boolean, description: "true when the device has a non-duplicate record on the as-of local date ('● Online'), else false ('○ No upload today'); TRD 24 D-114"}
        silent_days_last_30: {type: array, items: {type: string, format: date}}
        device_gap_days_last_30: {type: array, items: {type: string, format: date}}
    DeviceList:
      allOf:
        - {$ref: "#/components/schemas/PageMeta"}
        - {type: object, required: [items], properties: {items: {type: array, items: {$ref: "#/components/schemas/Device"}}}}

    # ---------- analytics and pipeline ----------
    StatusCountsRow:
      type: object
      required: [resident_code, usable, set_aside, quarantined, duplicate, missing_resident, missing_device_gap]
      properties:
        resident_code: {$ref: "#/components/schemas/ResidentCode"}
        usable: {type: integer}
        set_aside: {type: integer}
        quarantined: {type: integer}
        duplicate: {type: integer}
        missing_resident: {type: integer}
        missing_device_gap: {type: integer}
    StatusTotals:
      type: object
      required: [usable, set_aside, quarantined, duplicate, missing_resident, missing_device_gap]
      properties:
        usable: {type: integer}
        set_aside: {type: integer}
        quarantined: {type: integer}
        duplicate: {type: integer}
        missing_resident: {type: integer}
        missing_device_gap: {type: integer}
    ResidentOutcome:
      type: object
      required: [resident_code, epoch_number, device_code, usable_in_epoch, baseline_formed, baseline_frozen_after, scored_sessions, first_alarm_session, note]
      properties:
        resident_code: {$ref: "#/components/schemas/ResidentCode"}
        epoch_number: {type: integer}
        device_code: {type: string}
        usable_in_epoch: {type: integer}
        baseline_formed: {type: boolean}
        baseline_frozen_after: {type: [string, "null"]}
        scored_sessions: {type: [integer, "null"]}
        first_alarm_session: {type: [string, "null"]}
        note: {type: [string, "null"]}
    PipelineRun:
      type: object
      required: [id, trigger, scope, config_profile, code_version, as_of, started_at, finished_at, status, counts, warnings]
      properties:
        id: {type: string, format: uuid}
        trigger: {$ref: "#/components/schemas/PipelineTrigger"}
        scope:
          oneOf:
            - {type: string, const: all}
            - {type: array, items: {$ref: "#/components/schemas/ResidentCode"}}
        config_profile: {$ref: "#/components/schemas/ConfigProfile"}
        code_version: {type: string}
        as_of: {type: string, format: date-time}
        started_at: {type: string, format: date-time}
        finished_at: {type: [string, "null"], format: date-time}
        status: {$ref: "#/components/schemas/PipelineStatus"}
        counts: {type: object, additionalProperties: {type: integer}}
        warnings:
          type: array
          items:
            type: object
            required: [code, resident_code, session_id, detail]
            properties:
              code: {type: string, examples: ["late_arrival", "device_assignment_mismatch", "run_abandoned"]}
              resident_code: {type: [string, "null"]}
              session_id: {type: [string, "null"]}
              detail: {type: [string, "null"]}
    PipelineRunRequest:
      type: object
      additionalProperties: false
      required: [scope]
      properties:
        scope:
          oneOf:
            - {type: string, const: all}
            - {type: array, minItems: 1, items: {$ref: "#/components/schemas/ResidentCode"}}
        profile: {$ref: "#/components/schemas/ConfigProfile"}
        as_of: {type: [string, "null"], format: date-time}
    PipelineRunAccepted:
      type: object
      required: [pipeline_run_id]
      properties: {pipeline_run_id: {type: string, format: uuid}}
    PipelineRunList:
      allOf:
        - {$ref: "#/components/schemas/PageMeta"}
        - {type: object, required: [items], properties: {items: {type: array, items: {$ref: "#/components/schemas/PipelineRun"}}}}
    CountOfExpected:
      type: object
      required: [count, expected, percent]
      properties:
        count: {type: integer}
        expected: {type: integer}
        percent: {type: integer, minimum: 0, maximum: 100, description: rounded half-up}
    AnalyticsKpis:
      type: object
      required: [checkins_received, used_for_scoring, baselines_formed, alarms_raised]
      properties:
        checkins_received: {$ref: "#/components/schemas/CountOfExpected"}
        used_for_scoring: {$ref: "#/components/schemas/CountOfExpected"}
        baselines_formed:
          type: object
          required: [formed, residents, forming_resident_codes, restarts]
          properties:
            formed: {type: integer}
            residents: {type: integer}
            forming_resident_codes: {type: array, items: {$ref: "#/components/schemas/ResidentCode"}}
            restarts:
              type: array
              items:
                type: object
                required: [resident_code, restart_count]
                properties: {resident_code: {$ref: "#/components/schemas/ResidentCode"}, restart_count: {type: integer, minimum: 1}}
        alarms_raised:
          type: object
          required: [count, resident_codes, not_reviewed_count]
          properties:
            count: {type: integer}
            resident_codes: {type: array, items: {$ref: "#/components/schemas/ResidentCode"}}
            not_reviewed_count: {type: integer}
    DailySeriesPoint:
      type: object
      required: [local_date, used, set_aside, quarantined, missed, silent_device_codes]
      properties:
        local_date: {type: string, format: date}
        used: {type: integer}
        set_aside: {type: integer}
        quarantined: {type: integer}
        missed: {type: integer}
        silent_device_codes: {type: array, items: {$ref: "#/components/schemas/DeviceCode"}}
    Funnel:
      type: object
      required: [expected, residents, days, received, missed, duplicates_removed, passed_quality, set_aside, set_aside_reasons, set_aside_multi_reason, quarantined, used]
      properties:
        expected: {type: integer, description: sum over residents of enrolled days in period}
        residents: {type: integer}
        days: {type: integer}
        received: {type: integer, description: non-duplicate records}
        missed: {type: integer}
        duplicates_removed: {type: integer}
        passed_quality: {type: integer}
        set_aside: {type: integer}
        set_aside_reasons:
          type: object
          required: [quality_flag_poor, noise_above_limit, speech_too_short]
          properties:
            quality_flag_poor: {type: integer}
            noise_above_limit: {type: integer}
            speech_too_short: {type: integer}
        set_aside_multi_reason: {type: integer, description: set-aside sessions with more than one reason}
        quarantined: {type: integer}
        used: {type: integer}
    ByResidentRow:
      type: object
      required: [resident_code, days, used_days, set_aside_days, quarantined_days, missed_days, used_percent]
      properties:
        resident_code: {$ref: "#/components/schemas/ResidentCode"}
        days: {type: integer}
        used_days: {type: integer}
        set_aside_days: {type: integer, description: "days with a set-aside record and no usable record"}
        quarantined_days: {type: integer, description: "days with a quarantined record and no usable or set-aside record"}
        missed_days: {type: integer}
        used_percent: {type: integer, minimum: 0, maximum: 100}
    AlarmTimingRow:
      type: object
      required: [resident_code, planted_change, change_began, alarm_rang, delay_days, result]
      properties:
        resident_code: {$ref: "#/components/schemas/ResidentCode"}
        planted_change: {type: string, examples: ["Sudden step", "Slow drift", "None"]}
        change_began: {type: [string, "null"], format: date}
        alarm_rang: {type: [string, "null"], format: date}
        delay_days: {type: [integer, "null"]}
        result: {type: string, enum: [detected, missed, correct_no_alarm, false_alarm], description: "detected = first alarm on or after change_began; missed = planted change and no alarm; correct_no_alarm = no planted change and no alarm; false_alarm = alarm with no planted change, or an alarm before change_began (delay_days null) (TRD 09 CUS-032, TRD 24 D-81)"}
    ReviewOutcomes:
      type: object
      required: [alarms_raised, reviewed, by_outcome]
      properties:
        alarms_raised: {type: integer}
        reviewed: {type: integer}
        by_outcome:
          type: object
          required: [no_concern, known_cause, referred, data_problem]
          properties:
            no_concern: {type: integer}
            known_cause: {type: integer}
            referred: {type: integer}
            data_problem: {type: integer}
    AnalyticsResponse:
      type: object
      required: [meta, period, kpis, daily_series, funnel, by_resident, alarm_timing, review_outcomes, status_totals, status_counts, resident_outcomes, pipeline_run]
      properties:
        meta: {$ref: "#/components/schemas/Meta"}
        period:
          type: object
          required: [from, to, days]
          properties: {from: {type: string, format: date}, to: {type: string, format: date}, days: {type: integer}}
        kpis: {$ref: "#/components/schemas/AnalyticsKpis"}
        daily_series: {type: array, items: {$ref: "#/components/schemas/DailySeriesPoint"}}
        funnel: {$ref: "#/components/schemas/Funnel"}
        by_resident: {type: array, items: {$ref: "#/components/schemas/ByResidentRow"}}
        alarm_timing: {type: [array, "null"], items: {$ref: "#/components/schemas/AlarmTimingRow"}, description: test_v0_1 profile only}
        review_outcomes: {oneOf: [{$ref: "#/components/schemas/ReviewOutcomes"}, {type: "null"}], description: production profile only}
        status_totals: {$ref: "#/components/schemas/StatusTotals"}
        status_counts: {type: array, items: {$ref: "#/components/schemas/StatusCountsRow"}}
        resident_outcomes: {type: array, items: {$ref: "#/components/schemas/ResidentOutcome"}}
        pipeline_run: {oneOf: [{$ref: "#/components/schemas/PipelineRun"}, {type: "null"}]}
    BaselineRow:
      type: object
      required: [resident_code, epoch_number, device_code, feature_key, n_sessions, first_session_id, frozen_after_session_id, median, mad, robust_spread, floor_applied]
      properties:
        resident_code: {$ref: "#/components/schemas/ResidentCode"}
        epoch_number: {type: integer}
        device_code: {type: string}
        feature_key: {$ref: "#/components/schemas/BaselineFeatureKey"}
        n_sessions: {type: integer}
        first_session_id: {$ref: "#/components/schemas/SessionId"}
        frozen_after_session_id: {$ref: "#/components/schemas/SessionId"}
        median: {type: number}
        mad: {type: number, minimum: 0}
        robust_spread: {type: number, minimum: 0, description: "0 is possible only for a non-composite feature with floor 0 (TRD 08 BSC-035, TRD 20 baselines_spread_ck)"}
        floor_applied: {type: boolean}
    BaselineRowList:
      allOf:
        - {$ref: "#/components/schemas/PageMeta"}
        - {type: object, required: [items], properties: {items: {type: array, items: {$ref: "#/components/schemas/BaselineRow"}}}}

    # ---------- future arm (experimental) ----------
    AdmissionRow:
      type: object
      required: [resident_code, admitted_on, checkins_so_far, comparison_status, own_baseline_progress]
      properties:
        resident_code: {$ref: "#/components/schemas/ResidentCode"}
        admitted_on: {type: [string, "null"], format: date}
        checkins_so_far: {type: integer, minimum: 0}
        comparison_status: {$ref: "#/components/schemas/ComparisonStatus"}
        own_baseline_progress: {$ref: "#/components/schemas/BaselineProgress"}
    AdmissionList:
      allOf:
        - {$ref: "#/components/schemas/PageMeta"}
        - {type: object, required: [items], properties: {items: {type: array, items: {$ref: "#/components/schemas/AdmissionRow"}}}}
    ReferenceRange:
      type: object
      required: [feature_key, low, high, method, n_residents, computed_at, pipeline_run_id]
      properties:
        feature_key: {$ref: "#/components/schemas/FeatureKey"}
        low: {type: number}
        high: {type: number}
        method: {type: string, description: definition pending OQ-08}
        n_residents: {type: integer, minimum: 0}
        computed_at: {type: string, format: date-time}
        pipeline_run_id: {type: [string, "null"], format: uuid}
    ReferenceRangeList:
      allOf:
        - {$ref: "#/components/schemas/PageMeta"}
        - {type: object, required: [items], properties: {items: {type: array, items: {$ref: "#/components/schemas/ReferenceRange"}}}}
    AdmissionComparison:
      type: object
      required: [meta, resident_code, comparison_status, features]
      properties:
        meta: {$ref: "#/components/schemas/Meta"}
        resident_code: {$ref: "#/components/schemas/ResidentCode"}
        comparison_status: {$ref: "#/components/schemas/ComparisonStatus"}
        features:
          type: array
          items:
            type: object
            required: [feature_key, resident_value, low, high, outside_range]
            properties:
              feature_key: {$ref: "#/components/schemas/FeatureKey"}
              resident_value: {type: [number, "null"], description: median of the resident's usable check-ins so far}
              low: {type: [number, "null"]}
              high: {type: [number, "null"]}
              outside_range: {type: [boolean, "null"]}
```

## 5. Assumptions

- ASM-01 Facility timezone America/Chicago (`*_local`, `local_date`).
- ASM-02 One session per resident per local day (`session_id` suffix `-01` in test data; pattern allows `-NN`).
- ASM-03 Single facility; no facility path parameter in v1.
- ASM-04 `n_required` = 16 under test_v0_1, 30 under production.
- ASM-08 Lists are small; `limit` maximum 500 covers every test-data list in one page (180 baseline rows).

## 6. Dependencies

- TRD 05 (behaviour, error catalogue), TRD 20 (enum values), TRD 10 (ingest validation and feature-name mapping),
  TRD 08/09 (meaning of z, composite, tally, alarm_state).
- Tooling: FastAPI 0.115.x OpenAPI 3.1 output; `openapi-spec-validator` 0.7.x and `jsonschema` 4.x (tests);
  `openapi-typescript` 7.x (frontend types).
- SRC-03 workbook values for example and contract-test assertions.

## 7. Acceptance Criteria

- AC-OAS-01: `docs/api_reference/openapi.json` and the §4.5 skeleton both validate with `openapi-spec-validator` as OpenAPI 3.1.
- AC-OAS-02: The contract test (OAS-005) passes: the regenerated schema equals the committed `docs/api_reference/openapi.json`, and it matches the §4.5 skeleton.
- AC-OAS-03: Every response captured by the integration suite validates against its declared schema (OAS-006), including all Problem responses.
- AC-OAS-04: Each JSON example in §4.3 validates against its schema (OAS-015).
- AC-OAS-05: On the test_v0_1 data, the assertions OAS-021..OAS-024 pass with tolerance 1e-6 for numbers and exact match for strings/enums.
- AC-OAS-06: The enum comparison test (OAS-007) finds identical value sets between DTO enums and `pg_enum`.
- AC-OAS-07: A search of the YAML for `audio`, `wav`, `name` (as a resident property), `dob` finds no resident-level property (OAS-016).

## 8. Implementation Notes

- Name Pydantic models exactly as the schema names (`IngestRecord`, `ResidentOverviewRow`, ...); FastAPI uses the
  class name as the component name. Use `model_config = ConfigDict(extra="forbid")` for request models.
- Nullable fields: declare `X | None` without a default for response models and serialise with
  `response_model_exclude_none=False` so nulls are present (OAS-012).
- Pydantic v2 renders `X | None` as `anyOf: [{type: X}, {type: null}]`; the contract test shall normalise
  `anyOf`-with-null and `type: [X, "null"]` as equivalent.
- For `POST /sessions` and `POST /ingest` the body is read manually (TRD 05 API-031); attach the schema with
  `openapi_extra={"requestBody": {...}}` so the generated document still matches.
- `ScoreRow.z` holds unsigned z as in SRC-03 Exp_scores; do not multiply by sign before returning.
- The SRC-03 Exp_scores `alarm` column values map: "off" → `off`, "RINGS (first crossing)" → `rings`, "on" → `on`.
- Commit the generated `docs/api_reference/openapi.json` (via `python -m backend.cli export-openapi`) and the human summary in `docs/api_reference.md`; the skeleton YAML lives in `tests/fixtures/trd19_openapi_skeleton.yaml`.
- CSV export: implement with `StreamingResponse` and `csv.writer`; choose the representation in the handler from `request.headers["accept"]` and declare both media types via `responses=` so the generated schema matches OAS-018.
- `meta` is produced by one `get_meta()` dependency (TRD 05 API-057) and injected into every DTO listed in OAS-017.

## 9. Open Questions

- OQ-03 Feature key names are placeholders; renaming will change `FeatureKey` values only through a v2 or a mapping (see TRD 10).
- OQ-04 `phrase_id` required status.
- OQ-05 Review/tally reset: `POST /alerts/{id}/reviews` documents that tally and alarm are unchanged.
- OQ-24 Data-alert thresholds; OQ-25 review explanation list (`ReviewExplanationCode` is config-driven); OQ-26 who may review and how soon.
- OQ-08 Facility norm definition (`ReferenceRange.method`, `ComparisonStatus` thresholds).
- OQ-12 Final chart Summary ("Right now") wording (only structured `Explanation` facts are returned).
- OQ-31 (answered 26 Oct 2026, TRD 24 D-115) Only `baseline_stalled` and `high_set_aside` set `needs_attention` (changing it would change `AttentionReason`); `uploaded_on_as_of_date` false never sets it.
- OQ-14 Speaker verification confidence field (not in schema v0.1; adding it is a schema_version change).

## Revision History

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1 | 18 Oct 2026 | Initial generation from TRD_Generation_Prompt.md | — |
| 0.1 | 18 Oct 2026 | Cross-TRD consistency review | — |
| 0.2 | 19 Oct 2026 | Phase 1 validation fixes (F-08, F-09, F-10, F-12, F-39, F-41, F-43) | — |
| 0.3 | 19 Oct 2026 | Phase 1 round-2 fixes (R2-11) | — |
| 0.4 | 20 Oct 2026 | PR #2 backlog consistency fixes (BaselineRow.robust_spread minimum 0; still_above_line and restart detail (D-82); AlarmTimingRow.result (D-81); E-18 latest succeeded run) | — |
| 0.5 | 20 Oct 2026 | Documentation audit fixes (DA-05: E-10 same-date event order of TRD 11 UX-141) | — |
| 0.6 | 26 Oct 2026 | Wireframe v0.2 (SRC-21; TRD 24 D-108 to D-114): SRC-09/10/11/18/19 superseded; D-114 additions: `ResidentOverviewRow` and `ResidentDetail` gain `needs_attention`, `attention_reasons` (new `AttentionReason`) and `alarm_reviewed`; `OverviewSummary` becomes `changed`, `needs_attention`, `learning`, `usual` (2/2/0/6); `sort=alarm` order per D-109 (R09, R10, R03, R08, R01, R02, R04, R05, R06, R07); `CheckinEventType` gains `checkins_started` and `CheckinEvent` gains `device_code`; `Device` gains `uploaded_on_as_of_date`; restart cause for the v0.2 texts (`restart_cause` on `ResidentOverviewRow` and `ResidentDetail`; `EpochInfo.from_value`, `to_value`); `ResidentDetail.window` and `DateWindow.days`; E-30 examples use the v0.2 data-alert details; consumers redirected from `/alerts` and `/analytics` to the Resident chart, nav badge and Study team page; OAS-021, OAS-027, OAS-028 updated | — |
| 0.7 | 26 Oct 2026 | PR #5 review round 1 (TRD 24 D-115 to D-119): OQ-31 answered (D-115) | — |
| 0.8 | 27 Oct 2026 | Checkpoint 4: three YAML quoting fixes so the §8 skeleton parses as intended (the `/scores` 200 description, `IngestBatchAccepted.accepted.description` and `CheckinEvent.detail.description` contained an unquoted comma); no contract change | — |
