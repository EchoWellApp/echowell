# 10 Data Ingestion and Validation Spec

Document ID: ECHOWELL-TRD-10 · Version 0.4 (draft for review) · Date: 18 October 2026 · Owner: Team 2 · Status: Draft

## 1. Purpose

This document specifies how EchoWell receives per-session acoustic feature records from Team 1 devices (or CSV uploads),
validates them field by field, stores every accepted arrival unaltered in the raw record store, rejects invalid records
with a logged reason, detects duplicates in arrival order, applies the quality gate, resolves which device a resident
used on each day (shared devices and moves), and classifies missing days in the day ledger. EchoWell receives numeric
features only; no endpoint accepts, stores or replays audio (BR-01, BR-02).

## 2. Scope

In scope:
- Ingest interfaces `POST /api/v1/sessions` (single JSON record) and `POST /api/v1/ingest` (batch JSON or CSV upload), batch status.
- Schema version handling, feature-name mapping (OQ-03), field-by-field validation, timestamp parsing, warnings versus rejections.
- Raw store immutability (`raw_sessions`), `ingest_batches`, `ingest_rejections`.
- Duplicate detection (stage 1) and quality gate (stage 2) of the analytics engine (`analytics/duplicate_detection.py`, `analytics/quality_screening.py`).
- Device assignment resolution and the day ledger (stage 10, `analytics/day_ledger.py`).
- Separation of the answer key from ingestion; incompatibility of the legacy SRC-06 file.
- Idempotency and concurrency rules of ingestion.

Out of scope:
- Device capture, wake word, feature extraction, transport to the endpoint (Team 1; ASM-05), store-and-forward (Team 1; OQ-15).
- A converter for the legacy SRC-06 mock file (not provided; section 4.11).
- Authentication mechanics and key management (TRD 12), endpoint OpenAPI schemas (TRD 19), DDL (TRD 20).
- Speaker screen, morning adjustment, baselines, scores, CUSUM (TRD 08, TRD 09).

## 3. References

| ID | Document |
|---|---|
| SRC-02 | Flowcharts: "Only the raw store receives data from Team 1. Every other table can be rebuilt from it, and the answer key never touches the analytics"; stage 1 "Ingest and validate: drop duplicates, check schema and device"; stage 2 "Quality gate: check audio quality, noise, speech length" |
| SRC-03 | Workbook: Parameters (noise limit, minimum speech, duplicate rule, set-aside reason order, missing_resident, missing_device_gap), Data_dictionary, Annotated_sessions, Exp_status_counts |
| SRC-04 | Generator script (duplicate loop, gate, placeholders for missing days) |
| SRC-05 | Pipeline test input CSV v0.1 (283 arrivals, header defines field order) |
| SRC-06 | Legacy mock data (old schema) |
| SRC-13 | Dataset specification §3 (extractor version), §4 (features), §5 (moves, missing, poor quality, answer key separate file), §6 (record fields and status) |
| TRD 05 / TRD 19 | Backend API / OpenAPI contracts |
| TRD 06 / TRD 20 | Database design / schema (`raw_sessions`, `ingest_batches`, `ingest_rejections`, `device_assignments`, `day_ledger`) |
| TRD 07 | Analytics engine (triggers ANL-043, ANL-044; contracts) |
| TRD 08 | Baseline and scoring (consumes gate output) |
| TRD 12 | Security (API keys, roles, rate limits) |
| TRD 14 | Test data and validation |

## 4. Requirements

### 4.1 Ingest interfaces

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| ING-001 | `POST /api/v1/sessions` shall accept one record as a JSON object (`Content-Type: application/json`, body ≤ 64 KB, TRD 05 API-104) authenticated by header `X-API-Key` with scope `ingest:write`. | Must | BR-01, ASM-05, contract §10 | Test |
| ING-002 | For a valid record that is not a duplicate, `POST /api/v1/sessions` shall store it, run the pipeline for the resident synchronously (TRD 07 ANL-043, `as_of` per contract R21 precedence: request → PIPELINE_AS_OF (non-production) → current time) and return 201 `{raw_session_id, arrival_seq, session_id, status_after_processing, reasons, pipeline_run_id}` where `status_after_processing` ∈ {usable, set_aside, quarantined} and `reasons` lists the gate or screen reasons; if the pipeline run failed, it shall return 201 with `status_after_processing = "pending"` (the record stays stored and is processed by the next run; TRD 05 API-047, TRD 17 LOG-054). | Must | contract §10, TRD 05 API-046 | Test |
| ING-003 | For a valid record whose `session_id` was already received, `POST /api/v1/sessions` shall store the arrival and return 200 with `status_after_processing = "duplicate"`, `reasons = ["session_id already received"]` and `pipeline_run_id = null`. | Must | BR-03, contract §10, TRD 05 API-044 | Test |
| ING-004 | For an invalid record `POST /api/v1/sessions` shall return 422 `application/problem+json` with `type` = `urn:echowell:error:<CODE>`, where CODE is `UNSUPPORTED_SCHEMA_VERSION`, `UNKNOWN_RESIDENT`, `UNKNOWN_DEVICE`, `RESIDENT_WITHDRAWN` or `SESSION_ID_MISMATCH` when that is a violation (first in this order), else `VALIDATION_ERROR`; the `errors` array lists every violation as `{field, code, message}` (codes of ING-023); it shall write one `ingest_rejections` row (whose `errors` are identical to the response `errors`, TRD 05 API-041, with no `value` echo; the offending values remain available in `raw_body`) and shall not write to `raw_sessions`. | Must | BR-02, contract §7 step 1, §21 R19, TRD 05 §4.7 | Test |
| ING-005 | `POST /api/v1/ingest` shall accept either `Content-Type: application/json` with body `{"records": [ … ]}` (≤ 5,000 records, ≤ 5 MB) or `multipart/form-data` with one part named `file` holding a CSV (≤ 5 MB, ≤ 5,000 data rows), authenticated by `X-API-Key` (scope `ingest:write`) or by a JWT of role `admin`. | Must | BR-01, contract §10 | Test |
| ING-006 | `POST /api/v1/ingest` shall validate every record synchronously, store accepted records, write one `ingest_rejections` row per invalid record, create one `ingest_batches` row (`source` = `api_batch` for JSON, `csv_upload` for CSV, `seed` for the seeding script; `filename`; `record_count`; `accepted_count`; `rejected_count`; `uploaded_by` = admin user id or null for API keys; `received_at`), enqueue the background pipeline run (TRD 07 ANL-044) and return 202 `{ingest_batch_id, accepted, rejected, duplicates}`. | Must | contract §10 | Test |
| ING-007 | Record-level errors shall not fail the batch: valid records shall be accepted even when other records of the batch are rejected (202 also when `accepted = 0`). Request-level errors shall store nothing: malformed JSON or missing `records` array → 422 `VALIDATION_ERROR`; zero records → 422 `EMPTY_BATCH`; CSV header not equal to the schema v0.1 field set (ING-031, ING-053, ING-055) → 422 `CSV_HEADER_MISMATCH`; size limits → 413. | Must | BR-02, TRD 05 §4.7 | Test |
| ING-008 | `duplicates` in the batch response shall count accepted records whose `session_id` was already present in `raw_sessions` before the batch or appears earlier in the same batch. | Must | BR-03 | Test |
| ING-009 | `GET /api/v1/ingest/batches/{id}` (roles admin, researcher) shall return the `ingest_batches` row, the counts, and the batch's rejections (`row_number`, `errors`). | Must | contract §10 | Test |
| ING-010 | Single-record ingests shall have `raw_sessions.ingest_batch_id = null` and `ingest_rejections.ingest_batch_id = null`. | Must | TRD 06 | Test |
| ING-011 | Ingest requests shall be rate-limited to `RATE_LIMIT_INGEST` (600/minute) per API key; excess requests shall receive 429 with a `Retry-After` header. Missing or invalid key → 401 `API_KEY_INVALID`; key without `ingest:write` → 403 `FORBIDDEN`; unsupported content type → 415. | Must | TRD 12, contract §12, §21 R19 | Test |
| ING-012 | No ingest endpoint shall accept audio or binary media; a part or body with a content type other than `application/json`, `multipart/form-data` holding `text/csv` (or `application/vnd.ms-excel` sent by browsers for .csv files) shall be rejected with 415. | Must | BR-01, contract §2 | Test |

### 4.2 Schema version handling

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| ING-013 | Every record shall carry `schema_version` as a string; the value shall be in the configured list `supported_schema_versions` (`config_parameters` key, both profiles, seeded `["0.1"]`, TRD 20 §4.11); otherwise the record is rejected with code `unsupported_schema_version`. | Must | SRC-13 §6, contract §5 | Test |
| ING-014 | Validation rules shall be selected by `schema_version` through a registry `backend/services/validation.py::VALIDATORS = {"0.1": validate_v0_1}`; adding a version shall add a validator and a feature-name mapping without changing existing ones. | Must | SRC-13 §6 | Inspection |
| ING-015 | The stored `schema_version` shall be the received value; derived processing shall not depend on it in v0.1 beyond validation. | Must | BR-02 | Test |

### 4.3 Feature-name mapping (OQ-03)

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| ING-016 | Incoming field names shall be translated to canonical names through the configuration value `feature_name_map` (`config_parameters` key, both profiles; JSON object `{ "<external name>": "<canonical key>" }`, seeded as the identity map of the 11 record fields and 19 features, TRD 20 §4.11) before validation, so that Team 1's final extractor names can be adopted without a code change. | Must | OQ-03, RSK-02, SRC-13 §4 | Test |
| ING-017 | The mapping shall be validated when loaded: each target shall be one of the 30 canonical record field names (the 11 record fields and the 19 feature keys of the schema v0.1 header, so the seeded identity map of TRD 20 §4.11 is valid), no two external names shall map to the same key, and no external name shall equal a different canonical key; an invalid mapping shall prevent startup with a configuration error. | Must | OQ-03 | Test |
| ING-018 | `raw_sessions.payload` shall keep the original (unmapped) names and values; the typed columns shall use canonical names. | Must | BR-02 | Test |

### 4.4 Field-by-field validation (schema v0.1)

Reject = record rejected (422 / ingest_rejections). Warn = record accepted; warning code stored in
`raw_sessions.ingest_warnings` (jsonb array of `{field, code, message}`) and counted in the batch result (`GET /api/v1/ingest/batches/{id}`).

| Field | Type / format | Reject if | Warn if |
|---|---|---|---|
| schema_version | string | missing; not a string; not in `supported_schema_versions` | — |
| session_id | string ≤ 64 chars matching `^([A-Z0-9]{1,16})-(\d{8})-(\d{2})$` (group 1 uses the resident-code pattern of TRD 19/20) | missing; no match; group 1 ≠ `resident_id` (code `session_id_mismatch`) | group 2 ≠ local date (FACILITY_TZ) of `timestamp_utc` as YYYYMMDD (`session_id_date_mismatch`) |
| resident_id | string ≤ 16 chars | missing; no `residents.resident_code` equal to it (`unknown_resident`); resident `status = withdrawn` (`resident_withdrawn`, detail "resident withdrawn") | `timestamp_utc` local date before `enrolled_on` (`before_enrollment`) |
| device_id | string ≤ 16 chars | missing; no `devices.device_code` equal to it (`unknown_device`) | device `active = false` (`device_inactive`); device differs from the resident's assigned device on the local date (`device_assignment_mismatch`) |
| timestamp_utc | string `YYYY-MM-DD HH:MM:SS` (UTC) | missing; format mismatch; invalid calendar date/time | later than `received_at` + 24 h (`timestamp_in_future`) |
| mic_noise_level_dbfs | number | missing; non-finite; > 0 | — (noise above limit is handled by the quality gate) |
| audio_quality_flag | string enum | missing; not exactly `ok` or `poor` | — |
| extraction_software_version | string 1–64 chars | missing; empty; leading/trailing whitespace | — |
| device_firmware_version | string 1–64 chars | missing; empty; leading/trailing whitespace | — |
| speech_duration_s | number | missing; non-finite; < 0 | — (short speech is handled by the quality gate) |
| phrase_id | string 1–16 chars | missing; empty | — (field status open, OQ-04) |
| loudness_dbfs | number | missing; non-finite; > 0 | outside −30..−18 |
| total_phrase_duration_s | number | missing; non-finite; < 0 | outside 2.0..4.0 |
| speech_rate_syl_per_s | number | missing; non-finite; < 0 | outside 3.0..4.5 |
| articulation_rate_syl_per_s | number | missing; non-finite; < 0 | outside 4.0..5.5 |
| number_of_pauses | integer | missing; not an integer (JSON number with a fractional part; CSV text not matching `^\d+(\.0+)?$`); < 0 | > 3 |
| pause_fraction | number | missing; non-finite; < 0 or > 1 | outside 0.05..0.25 |
| voiced_fraction | number | missing; non-finite; < 0 or > 1 | outside 0.50..0.75 |
| mean_f0_hz | number | missing; non-finite; ≤ 0 (TRD 20 `raw_sessions_mean_f0_ck` requires > 0) | outside 165..200 (sex F), 110..145 (sex M), 110..200 (sex null) |
| f0_variability_st | number | missing; non-finite | outside 2.0..4.5 |
| jitter_local_pct | number | missing; non-finite; < 0 | outside 0.2..1.0 |
| shimmer_local_pct | number | missing; non-finite; < 0 | outside 2.0..6.0 |
| hnr_db | number | missing; non-finite | outside 10..20 |
| cpps_db | number | missing; non-finite | outside 8..16 |
| alpha_ratio_db | number | missing; non-finite | outside −20..0 |
| hammarberg_index_db | number | missing; non-finite | outside 15..30 |
| mfcc1 / mfcc2 / mfcc3 / mfcc4 | number | missing; non-finite | outside 20..40 / 0..15 / −5..10 / −10..5 |
| any other field | — | present (`extra_forbidden`; TRD 05 API-034) | — |

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| ING-019 | The validator shall apply every Reject rule of the table above and collect all violations of a record (not stop at the first) before rejecting it. | Must | BR-01, contract §5 | Test |
| ING-020 | Plausibility ranges (Warn column) shall never cause rejection; they are placeholders until measured on the v1 rig (SRC-13 §2, RSK-02). Warnings of one record shall be aggregated into one `ingest_warnings` array; plausibility warnings use code `implausible_value` with the field name. | Must | SRC-13 §2, RSK-02 | Test |
| ING-021 | In JSON, numeric fields shall be JSON numbers (a numeric string is rejected with `invalid_type`) and text fields JSON strings; in CSV every cell is text and numeric cells shall be parsed with Python `float()` after confirming the cell is non-empty; the literals `nan`, `inf`, `-inf` (any case) shall be rejected as `non_finite`. | Must | contract §5 | Test |
| ING-022 | Text values shall be stored exactly as received (no trimming, no case change); this keeps epoch keys exact (TRD 08 BSC-007). | Must | BR-02, BR-08 | Test |
| ING-023 | Field-level codes in `errors[].code` shall be exactly: `missing_field`, `invalid_type`, `invalid_format`, `invalid_enum`, `out_of_range`, `not_integer`, `non_finite`, `extra_forbidden`, `unsupported_schema_version`, `session_id_mismatch`, `unknown_resident`, `resident_withdrawn`, `unknown_device`; request-level problems use the TRD 05 codes `VALIDATION_ERROR`, `EMPTY_BATCH`, `CSV_HEADER_MISMATCH`. Warning codes shall be exactly: `implausible_value`, `session_id_date_mismatch`, `before_enrollment`, `device_inactive`, `device_assignment_mismatch`, `timestamp_in_future`, `duplicate_payload_differs`. | Must | TRD 17, TRD 05 §4.7, §21 R19 | Test |
| ING-024 | All 283 records of SRC-05 shall pass validation (no rejection) when the R01–R10 residents and devices D01, D02, D04, D05, D06, D07, D07B, D08, D09, D10 of section 4.9 exist. | Must | BR-15, SRC-05 | Test |

### 4.5 Timestamp parsing and local time

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| ING-025 | `timestamp_utc` shall match `^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$`, be parsed with `datetime.strptime(value, "%Y-%m-%d %H:%M:%S")` and interpreted as UTC (`tzinfo=timezone.utc`); ISO forms with `T`, `Z`, offsets or fractional seconds shall be rejected with `invalid_format` in schema 0.1. | Must | SRC-03 Data_dictionary, SRC-13 §6 | Test |
| ING-026 | `raw_sessions.timestamp_utc` shall be stored as `timestamptz` equal to that UTC instant; the received string stays in `payload`. | Must | BR-02 | Test |
| ING-027 | Local date and time shall be derived only by converting to `FACILITY_TZ` (default America/Chicago) with `zoneinfo`, never from the UTC date or hour (TRD 08 BSC-020). | Must | ASM-01, BR-06, BR-07 | Test |
| ING-028 | Records with a future timestamp shall be accepted (with warning) and excluded from pipeline runs whose `as_of` precedes them (TRD 07 ANL-015). | Must | BR-02 | Test |

### 4.6 Raw store, rejections and immutability

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| ING-029 | Every accepted arrival, including duplicates, shall be inserted into `raw_sessions` with `arrival_seq` (bigserial), `received_at` (server UTC time), `ingest_batch_id`, `payload` (the record as received: the JSON object, or for CSV an object of header → cell text, before mapping and conversion), typed copies of all §5 fields and the 19 canonical feature columns, and `ingest_warnings`. | Must | BR-02, SRC-02, contract §9 | Test |
| ING-030 | `raw_sessions` shall be insert-only: a database trigger shall raise on UPDATE and DELETE, and the application role `echowell_app` (used via `DATABASE_URL`) shall have no UPDATE/DELETE grant on it (trigger `raw_sessions_no_update_delete`, TRD 20 PGS-018); `ingest_rejections` is append-only through grants only (`echowell_app`: SELECT, INSERT; TRD 20 PGS-021), without a trigger. | Must | BR-02, SRC-02, contract §12, §21 R20 | Test |
| ING-031 | A CSV upload shall be UTF-8 (optional BOM), comma-separated, RFC 4180 quoting, LF or CRLF line endings; its header row, after feature-name mapping, shall consist of exactly the 30 fields of contract section 5 in any order (no missing, no extra columns), else the request is rejected with 422 `CSV_HEADER_MISMATCH` whose `errors` list the missing and extra column names, and nothing is stored. | Must | SRC-05, TRD 05 §4.7 | Test |
| ING-032 | Within a batch, records shall be inserted in input order (JSON array order or CSV row order) so that `arrival_seq` increases in that order; `ingest_rejections.raw_body` shall hold the rejected record as received and `errors` the violation list, plus `row_number` = the 1-based position of the record in the batch (CSV: data row, header excluded; JSON: array position); `row_number` is NULL only for a rejection of a single-record `POST /api/v1/sessions`, which has no batch (TRD 19 `IngestRejection`; TRD 24 D-84). | Must | BR-03 | Test |
| ING-033 | Rejected records shall never enter `raw_sessions` and shall never be processed by the pipeline; a corrected record re-sent later is treated as a new arrival. | Must | contract §7 step 1 | Test |

### 4.7 Duplicates and idempotency (`analytics/duplicate_detection.py`)

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| ING-034 | The duplicate key shall be `session_id` (exact string). Processing all non-rejected arrivals in ascending `arrival_seq`, the first arrival of a `session_id` shall be kept and every later arrival shall get status `duplicate` with reason "session_id already received". | Must | BR-03, SRC-03 Parameters, SRC-04 | Test |
| ING-035 | Duplicate detection shall run before the quality gate and before any sorting by timestamp; duplicates shall not be gated, screened, given an epoch, counted toward any baseline, scored or counted as a record for the day ledger. | Must | SRC-04, contract §7 | Test |
| ING-036 | Duplicates shall be logged (processed_sessions row with status `duplicate`, counted in pipeline run counts) but never shown in the resident UI ("Duplicate records are removed quietly and not shown"). | Must | SRC-09, contract §8 | Test |
| ING-037 | A later arrival with the same `session_id` but different field values shall still be a duplicate (first arrival wins) and shall carry the ingest warning `duplicate_payload_differs` (ING-023, stored in `raw_sessions.ingest_warnings` by the ingest service; it is not a pipeline `RunWarning` of TRD 07 ANL-052). | Must | BR-03 | Test |
| ING-038 | The ingest service shall take the session advisory lock of TRD 06 DB-021 (b) before checking `raw_sessions` for the `session_id` and inserting, so that the duplicate verdict returned to the caller agrees with the arrival-order rule under concurrent requests. | Must | BR-03 | Test |
| ING-039 | Re-sending a record or re-uploading a file shall be safe: the repeated arrivals are stored as duplicates, change no derived result and return status `duplicate`; no `Idempotency-Key` header is required. | Must | BR-03, SRC-03 R04 | Test |

Fixture check: R04-20261005-01 arrives at arrival_seq 88 and again at 89 (adjacent copy); R04-20261018-01 arrives at 102
and again at 283 (last in the file). Arrivals 89 and 283 are `duplicate`; R04 results are identical to a run without them.

### 4.8 Quality gate (`analytics/quality_screening.py`)

```
for each non-duplicate record r:
    reasons = []
    if r.audio_quality_flag != "ok":                  reasons.append("quality flag poor")
    if r.mic_noise_level_dbfs > noise_limit_dbfs:      reasons.append("noise above limit")      # -40.0
    if r.speech_duration_s < min_speech_s:             reasons.append("speech too short")       # 1.0
    status = "set_aside" if reasons else "pending_screen"
    reason_text = "; ".join(reasons)
```

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| ING-040 | A non-duplicate record shall be set aside when `audio_quality_flag` ≠ "ok", when `mic_noise_level_dbfs > noise_limit_dbfs` (strictly greater; −40.0 itself passes), or when `speech_duration_s < min_speech_s` (strictly less; 1.0 itself passes). | Must | BR-04, SRC-03 Parameters | Test |
| ING-041 | All applicable reasons shall be recorded in the fixed order "quality flag poor", "noise above limit", "speech too short", stored in `processed_sessions.reasons` (text[]) and joined with "; " in `reason_text` (e.g. "quality flag poor; noise above limit" for R03-20261018-01). | Must | BR-04, SRC-03 Annotated_sessions | Test |
| ING-042 | Set-aside records shall be logged, never scored and never used for a baseline or the speaker-screen reference; they still belong to an epoch and count as a record for the day ledger. | Must | BR-04, SRC-02, SRC-03 | Test |
| ING-043 | Records passing the gate shall get the interim status `pending_screen` and be passed to the speaker screen (TRD 08). | Must | contract §7 step 2 | Test |

Fixture check: 12 set-aside records — R03 days 3, 14 (noise), 7, 22 (flag), 10, 26 (short), 18 (flag + noise); R08 days 5,
20 (noise), 9, 25 (flag), 29 (short).

### 4.9 Device assignment resolution

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| ING-044 | `device_assignments` rows `(resident, device, valid_from, valid_to)` with inclusive dates (null `valid_to` = open) shall define which device a resident uses on each local date; a device move is recorded by closing the old row (`valid_to` = last day) and opening a new one (`valid_from` = first day on the new device). | Must | BR-06, SRC-13 §5, contract §9 | Test |
| ING-045 | The resident's device on local date d shall be the device of the assignment covering d; if two assignments of the resident cover d, the one with the later `valid_from` wins; if none covers d, the device is unknown (null). | Must | BR-06 | Test |
| ING-046 | A device shall be shared on date d when at least `shared_device_min_residents` (2) distinct residents who are enrolled on d (`enrolled_on ≤ d` and not withdrawn before d) have an assignment to it covering d. | Must | SRC-03 Parameters, contract §7 | Test |
| ING-047 | Epochs shall use the `device_id` carried by each record, not the assignment table; assignments are used only for the day ledger, the "(shared)" / "(was D07)" labels and the `device_assignment_mismatch` warning. | Must | BR-08, SRC-04 | Inspection, Test |

Residents, devices and device assignments have no API endpoints in the MVP; they are managed by the CLI
(`python -m backend.cli ...`) and seed files (contract §20 R4). Test fixture (seeded by `database/seeds/`, used by TRD 14) — facility Edgewood (`FACILITY_NAME`), all residents cohort
`longitudinal`, `enrolled_on` 2026-10-01, status active:

| resident | sex | assignments |
|---|---|---|
| R01 | F | D01 from 2026-10-01 |
| R02 | M | D02 from 2026-10-01 (shared with R03) |
| R03 | F | D02 from 2026-10-01 (shared with R02) |
| R04 | M | D04 from 2026-10-01 |
| R05 | F | D05 from 2026-10-01 |
| R06 | M | D06 from 2026-10-01 |
| R07 | F | D07 2026-10-01 to 2026-10-12; D07B from 2026-10-13 |
| R08 | M | D08 from 2026-10-01 |
| R09 | F | D09 from 2026-10-01 |
| R10 | M | D10 from 2026-10-01 |

### 4.10 Day ledger (`analytics/day_ledger.py`)

```
for each resident X (sorted by resident_code):
    last_day = min(local date of as_of, withdrawn_on if withdrawn_on else +inf)   # inclusive (TRD 02 FR-120)
    for d in enrolled_on .. last_day:
        recs_X_d = non-duplicate records of X with local_date == d and timestamp_utc <= as_of   # any status
        if recs_X_d: status = "checked_in"; device = device_id of the earliest of them; reason = ""
        else:
            dev = device of X on d (ING-045)
            sharers = residents with an assignment to dev covering d (ING-046)
            if dev and len(sharers) >= shared_device_min_residents
               and no sharer has a non-duplicate record with local_date == d:
                status = "missing_device_gap"; reason = f"all residents on shared device {dev} have no record"
            else:
                status = "missing_resident"; reason = "no record received"
```

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| ING-048 | The ledger shall contain one row per resident per facility-local calendar day from `enrolled_on` through the local date of `as_of`, or through `withdrawn_on` (inclusive) when that is earlier (TRD 02 FR-120). | Must | BR-06, contract §7 step 10 | Test |
| ING-049 | A day with at least one non-duplicate record of the resident (any status: usable, set_aside, quarantined, including late arrivals) shall be `checked_in`; duplicates alone do not make a day checked in. | Must | BR-06, SRC-03 | Test |
| ING-050 | A day without such a record shall be `missing_device_gap` with reason "all residents on shared device <device_code> have no record" when the resident's device that day is shared (ING-046) and none of the residents sharing it has a non-duplicate record of any status that day; otherwise it shall be `missing_resident` with reason "no record received". | Must | BR-06, SRC-03 Parameters | Test |
| ING-051 | Missing days shall never be backfilled, carried forward or imputed; they create no processed session and no score and do not update the CUSUM. The ledger is recomputed on each run, so a day changes from missing to `checked_in` only if a real record for that day arrives. | Must | BR-06, SRC-13 §6 | Test |
| ING-052 | Missing-day rows shall store `device_id` = the resident's assigned device that day (null if unknown); `checked_in` rows store the device of the earliest record. | Must | TRD 06 | Test |

Worked check (SRC-05, as_of 2026-10-30 15:00 America/Chicago; 10 residents × 30 days = 300 ledger rows):
- 2026-10-12: neither R02 nor R03 has a record; D02 is shared by both → R02 and R03 `missing_device_gap` ("all residents on shared device D02 have no record").
- R02 days 4, 9, 10, 17, 23: R03 has a record on each of these days → R02 `missing_resident`. On day 10 R03's record is set aside (speech too short), which still counts; a variant that counts only usable records wrongly produces a device gap for R02 on 2026-10-10.
- R08 days 2, 4, 6, 8, 11, 13, 15, 17, 19, 21, 24, 27: D08 not shared → `missing_resident` (12 days).
- R07 has no missing day (D07 to 10-12, D07B from 10-13).
- Totals: 281 `checked_in`, 17 `missing_resident`, 2 `missing_device_gap`; together with 2 duplicate arrivals this gives the 302 annotated rows of SRC-03.

### 4.11 Source separation and legacy data

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| ING-053 | The answer key shall never be ingested: a CSV whose header contains any of `expected_status`, `expected_reason`, `expected_morning`, `expected_epoch`, `in_baseline`, `error_mode_tested`, `test_case`, `arrival_order` shall be rejected as a whole with 422 `CSV_HEADER_MISMATCH` (errors[].code `extra_forbidden` naming those columns); `.xlsx` files shall be rejected with 415. | Must | SRC-02, SRC-03 README, SRC-13 §5 | Test |
| ING-054 | No backend or analytics code shall read `EchoWell_pipeline_test_v0_1.xlsx` or any answer-key file, except the test-only loader `database/seeds/load_evaluation_ground_truth.py` (profile test_v0_1 only), which fills `evaluation_ground_truth` (resident_code, planted_change, true_onset_date, source_file) and writes nothing to `raw_sessions`. The pipeline and all ingest code connect with `DATABASE_URL` (role `echowell_app`), which has no SELECT on `evaluation_ground_truth` (contract §21 R20, R27; TRD 09 CUS-047, CUS-048); tests under `tests/validation/` may read the workbook. | Must | SRC-02, §19, §21 R20, R27 | Inspection, Test |
| ING-055 | The legacy SRC-06 file (`echowell_mock_data_500.csv`, columns entry_id, resident_id (integer), datetime "YYYYMMDD_HHMMSS", health_wifi, health_ping, health_mic_noise, device_id (integer), speech_len, speech_feature_1..3) is not compatible with schema 0.1; an upload of it shall be rejected as a whole with 422 `CSV_HEADER_MISMATCH` and nothing stored (contract §20 R12). | Must | SRC-06, contract §1, R12 | Test |
| ING-056 | A converter from the SRC-06 schema is out of scope: its features `speech_feature_1..3` do not correspond to any of the 19 canonical features, its timestamps carry no time zone, and its integer resident/device IDs have no mapping to study codes; SRC-06 shall not be used as pipeline input. | Must | SRC-06, SRC-13 | Inspection |

### 4.12 Logging and audit

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| ING-057 | Each ingest request shall emit one structured log event `ingest_request` with `request_id`, `endpoint`, `api_key_id` or `user_id`, `ingest_batch_id`, `record_count`, `accepted`, `rejected`, `duplicates`, `warning_count`, `duration_ms`; feature values and payloads shall not be logged. | Must | TRD 17, BR-16 | Test |
| ING-058 | Each batch ingest (JSON or CSV) shall write one `audit_logs` row (action `ingest.batch.received`, TRD 12 §4.12; entity `ingest_batch`, details with counts); `api_keys.last_used_at` shall be updated on each authenticated ingest. | Must | BR-16, contract §12 | Test |
| ING-059 | The seeding script shall load SRC-05 through the same validation and insertion code path as `POST /api/v1/ingest` (source `seed`), never by direct SQL inserts into `raw_sessions`. | Must | BR-02, TRD 14 | Inspection |

## 5. Assumptions

- ASM-01 Facility timezone America/Chicago.
- ASM-02 At most one session per resident per local day (session_id suffix -01); not enforced by validation.
- ASM-03 Single facility (Edgewood); resident and device codes are unique facility-wide.
- ASM-05 Records arrive via HTTPS POST from Team 1 or CSV upload; transport is Team 1's.
- ASM-08 Volumes below 100 residents and 1 session per resident per day.
- D-OWNER-4: the interim Netlify/Railway/Neon stack receives synthetic and test data only; live resident data is ingested only after AWS approval.
- Note for lead (TRD-local definitions): config keys `supported_schema_versions` and `feature_name_map` (now `config_parameters` keys, lead decision 18 Oct 2026); column
  `raw_sessions.ingest_warnings` (jsonb); `status_after_processing = "pending"` (now contract §21 R23); size limits (64 KB single per TRD 05 API-104, 5 MB / 5,000
  records batch); rejection and warning code lists (ING-023); `row_number` inside `ingest_rejections.errors`.

## 6. Dependencies

- TRD 12 for API key hashing, scopes, roles and rate limiting; TRD 05/19 for response schemas; TRD 06/20 for tables and the
  immutability trigger; TRD 07 for pipeline triggers; TRD 08 for the speaker screen that follows the gate.
- Seeded `residents`, `devices`, `device_assignments` (section 4.9) for validation and the ledger.
- Python `csv` module, `zoneinfo` + `tzdata`, FastAPI `UploadFile` (python-multipart).

## 7. Acceptance Criteria

- AC-ING-01: Uploading SRC-05 as CSV returns 202 with `accepted = 283`, `rejected = 0`, `duplicates = 2`; `raw_sessions` has 283 rows with `arrival_seq` in file order.
- AC-ING-02: After the pipeline run, statuses equal SRC-03: usable 267, set_aside 12, quarantined 2, duplicate 2; ledger missing_resident 17, missing_device_gap 2 (R02 and R03 on 2026-10-12), with exact reason strings.
- AC-ING-03: Re-uploading SRC-05 returns `duplicates = 283` and leaves every derived table unchanged.
- AC-ING-04: Posting a record with `pause_fraction = 1.2` returns 422 `VALIDATION_ERROR` with errors[].code `out_of_range`; with `number_of_pauses = 1.5` errors[].code `not_integer`; with an extra field `audio_base64` errors[].code `extra_forbidden`; with `loudness_dbfs = −35` is accepted with warning `implausible_value`.
- AC-ING-05: Posting `timestamp_utc = "2026-10-01T19:45:11Z"` returns 422 `VALIDATION_ERROR` with errors[].code `invalid_format`; posting `schema_version = "0.2"` returns 422 with type `urn:echowell:error:UNSUPPORTED_SCHEMA_VERSION`.
- AC-ING-06: Uploading the SRC-03 Annotated_sessions sheet exported as CSV returns 422 `CSV_HEADER_MISMATCH`; uploading SRC-06 returns 422 `CSV_HEADER_MISMATCH`; neither stores any row.
- AC-ING-07: An UPDATE or DELETE on `raw_sessions` by the application role fails.
- AC-ING-08: With `feature_name_map = {"Loudness_sma3_amean": "loudness_dbfs"}` a CSV using that header is accepted and stored with canonical column `loudness_dbfs` while `payload` keeps `Loudness_sma3_amean`.
- AC-ING-09: Two concurrent single POSTs of the same session_id result in exactly one non-duplicate arrival and one `duplicate` response.
- AC-ING-10: A record for a withdrawn resident returns 422 `RESIDENT_WITHDRAWN` with detail "resident withdrawn".
- AC-ING-11: When the synchronous pipeline run fails, `POST /api/v1/sessions` returns 201 with `status_after_processing = "pending"`, the record is in `raw_sessions`, and the next run (nightly or ingest) processes it.

## 8. Implementation Notes

- Fill `backend/services/ingestion.py` (request handling, batch creation, locking, insertion) and `backend/services/validation.py` (validator registry, field rules, mapping); routers in `backend/api/sessions.py` and an ingest router.
- Build Pydantic 2 models for the JSON body with `strict=True` for numbers and strings, but run the field rules of section 4.4 in a single function that returns all violations, so JSON and CSV share one code path.
- Do not use pandas to read uploads (it coerces types and drops leading zeros); use `csv.DictReader` on the decoded text.
- Keep `payload` as received; never write mapped or converted values back into it.
- The gate's comparisons are strict (`>` and `<`); boundary tests: noise −40.0 passes, −39.9 is set aside; speech 1.0 passes, 0.99 is set aside.
- Compute the ledger with all residents' records available (shared devices); a single-resident run must load the records of residents sharing that resident's devices (TRD 07 ANL-016).
- Plausibility warnings are frequent with placeholder ranges (248 of the 283 SRC-05 records carry at least one); they are informational and must not be surfaced as errors in the UI.

## 9. Open Questions

- OQ-03 Final feature column names from Team 1's extractor (mapping config ING-016).
- OQ-04 Whether `phrase_id` is kept.
- OQ-07 AWS budget approval timing and account ownership (UND IT); device-to-cloud transport is Team 1's (ASM-05).
- OQ-10 Late-arriving records (handled in TRD 07/08).
- OQ-11 Data handling on participant withdrawal (ingestion stops with 422 "resident withdrawn").
- OQ-14 Speaker verification output (not a v0.1 field).
- OQ-15 Store-and-forward after network outage (gaps are missing data).
- OQ-01 Retention of raw records.

## Revision History

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1 | 18 Oct 2026 | Initial generation from TRD_Generation_Prompt.md | — |
| 0.1 | 18 Oct 2026 | Cross-TRD consistency review | — |
| 0.2 | 19 Oct 2026 | Phase 1 validation fixes (F-01, F-04, F-21, F-22, F-35, F-43, F-44) | — |
| 0.3 | 19 Oct 2026 | Phase 1 round-2 fixes (R2-08) | — |
| 0.4 | 20 Oct 2026 | PR #2 backlog consistency fixes (ING-032 row_number for JSON batches (D-84); ING-037 ingest warning, not RunWarning) | — |
