# Ingest record validation, schema-version registry and feature-name mapping

## Feature Description

FEAT-023 decides for every incoming feature record whether it may enter the immutable raw store (`backend/services/validation.py`). Field names are first translated through the configurable `feature_name_map` of the active profile (validated at load; an invalid map stops start-up). The validator is chosen from `VALIDATORS = {"0.1": validate_v0_1}` by `schema_version` (must be in `supported_schema_versions`, seeded `["0.1"]`). Every reject rule of TRD 10 §4.4 is applied and all violations are collected as `{field, code, message}` with codes `missing_field`, `invalid_type`, `invalid_format`, `invalid_enum`, `out_of_range`, `not_integer`, `non_finite`, `extra_forbidden`, `unsupported_schema_version`, `session_id_mismatch`, `unknown_resident`, `resident_withdrawn`, `unknown_device`; messages never echo the value. The resident and device are resolved (no auto-registration), withdrawn residents are refused ("resident withdrawn"), a device-bound key cannot submit another device's record (403 `DEVICE_KEY_MISMATCH`). Plausibility and other warnings (`implausible_value`, `session_id_date_mismatch`, `before_enrollment`, `device_inactive`, `timestamp_in_future`; `device_assignment_mismatch` is a pipeline run warning since TRD 24 D-125) never reject and are stored in `raw_sessions.ingest_warnings`. The request-level code of a rejected single record is the first applicable of `UNSUPPORTED_SCHEMA_VERSION`, `UNKNOWN_RESIDENT`, `UNKNOWN_DEVICE`, `RESIDENT_WITHDRAWN`, `SESSION_ID_MISMATCH`, else `VALIDATION_ERROR`. The rules are observed through `POST /api/v1/sessions` (E-05) and `POST /api/v1/ingest` (E-06).

## Preconditions

- Local development stack running; `.env` from `.env.development.example` (`APP_ENV=local`, `PIPELINE_PROFILE=test_v0_1`, `FACILITY_TZ=America/Chicago`, `SEED_*` set).
- Database seeded: `python -m backend.cli seed test_v0_1 --reset` (roster R01–R10, D01–D10 with D07 inactive and D07B; 283 SRC-05 records).
- Ingest key in the shell variable from `SEED_INGEST_API_KEY` (`test-ingest`, not device-bound); a device-bound key created with `python -m backend.cli create-api-key --name qa-d01 --device D01` (plaintext kept only in the tester's shell).
- **BASE record** (synthetic, derived from SRC-05 row `R02-20261001-01`, no warnings): `{"schema_version": "0.1", "session_id": "R02-20261031-01", "resident_id": "R02", "device_id": "D02", "timestamp_utc": "2026-10-31 19:58:08", "mic_noise_level_dbfs": -48.2, "audio_quality_flag": "ok", "extraction_software_version": "openSMILE 3.0.2", "device_firmware_version": "fw-1.0.0", "speech_duration_s": 2.49, "phrase_id": "P01", "loudness_dbfs": -25.94, "total_phrase_duration_s": 2.49, "speech_rate_syl_per_s": 4.42, "articulation_rate_syl_per_s": 5.21, "number_of_pauses": 1, "pause_fraction": 0.095, "voiced_fraction": 0.696, "mean_f0_hz": 144.4, "f0_variability_st": 2.57, "jitter_local_pct": 0.719, "shimmer_local_pct": 5.59, "hnr_db": 14.28, "cpps_db": 10.49, "alpha_ratio_db": -10.24, "hammarberg_index_db": 15.62, "mfcc1": 31.47, "mfcc2": 5.56, "mfcc3": 0.67, "mfcc4": -5.44}`. Each case changes only the fields it names and uses a fresh `session_id` (`R02-20261031-NN`, NN = 01…99, matching the timestamp date) unless it tests the session ID.
- All calls: `POST http://localhost:8000/api/v1/sessions` with `Content-Type: application/json` and `X-API-Key`.
- `psql` for read-only checks on `raw_sessions`, `ingest_rejections`, `config_parameters`.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-023-01 | BASE record is accepted with no warnings and the payload kept verbatim | High | Positive |
| TC-023-02 | Three violations in one record are all collected | High | Negative |
| TC-023-03 | `loudness_dbfs = -35` is accepted with one `implausible_value` warning | High | Positive |
| TC-023-04 | ISO timestamp is `invalid_format`; `schema_version` "0.2" is `UNSUPPORTED_SCHEMA_VERSION` | High | Negative |
| TC-023-05 | Unknown resident R11 → `UNKNOWN_RESIDENT`; withdrawn resident → `RESIDENT_WITHDRAWN` "resident withdrawn" | High | Negative |
| TC-023-06 | Unknown device and session-ID prefix mismatch | High | Negative |
| TC-023-07 | Request-code precedence when several record-level problems occur | Medium | Negative |
| TC-023-08 | Device-bound key and another device → 403 `DEVICE_KEY_MISMATCH` | High | Security |
| TC-023-09 | JSON numeric string is `invalid_type`; CSV `-30.1` accepted and `NaN` is `non_finite` | High | Negative |
| TC-023-10 | Range, integer and enum rules of TRD 10 §4.4 | High | Negative |
| TC-023-11 | Missing field and text rules (exact text, whitespace in versions) | Medium | Negative |
| TC-023-12 | Non-blocking warnings: date mismatch, inactive device, assignment mismatch, future timestamp, F0 by sex | Medium | Positive |
| TC-023-13 | Renamed column through `feature_name_map` is accepted; payload keeps the external name | High | Positive |
| TC-023-14 | Invalid `feature_name_map` prevents start-up | High | Negative |
| TC-023-15 | All 283 SRC-05 rows validate with zero errors | High | Positive |
| TC-023-16 | Validator registry and code lists equal the TRD | Medium | Documentation |

### TC-023-01 BASE record is accepted with no warnings and the payload kept verbatim

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/sessions` with BASE (`session_id` `R02-20261031-01`) | 201; body has `raw_session_id`, `arrival_seq`, `session_id` `R02-20261031-01`, `status_after_processing`, `reasons`, `pipeline_run_id` |
| 2 | `SELECT schema_version, loudness_dbfs, ingest_warnings, payload->>'phrase_id', timestamp_utc FROM raw_sessions WHERE session_id = 'R02-20261031-01';` | `0.1`; `-25.94`; `[]`; `P01`; `2026-10-31 19:58:08+00` |
| 3 | `SELECT count(*) FROM ingest_rejections WHERE raw_body->>'session_id' = 'R02-20261031-01';` | 0 |

### TC-023-02 Three violations in one record are all collected

| Step | Action | Expected Result |
|---|---|---|
| 1 | Post BASE with `session_id` `R02-20261031-02`, `"pause_fraction": 1.2`, `"number_of_pauses": 1.5` and an extra property `"audio_base64": "AAAA"` (a 4-character placeholder, not audio) | 422; `type` `urn:echowell:error:VALIDATION_ERROR` |
| 2 | Inspect `errors` | Exactly three items: `{field: "pause_fraction", code: "out_of_range"}`, `{field: "number_of_pauses", code: "not_integer"}`, `{field: "audio_base64", code: "extra_forbidden"}`; no message contains `1.2`, `1.5` or `AAAA` |
| 3 | `SELECT jsonb_array_length(errors) FROM ingest_rejections WHERE raw_body->>'session_id' = 'R02-20261031-02';` | 3 (rejection stored verbatim; nothing in `raw_sessions`) |
| 4 | `SELECT count(*) FROM raw_sessions WHERE session_id = 'R02-20261031-02';` | 0 |

### TC-023-03 `loudness_dbfs = -35` is accepted with one `implausible_value` warning

| Step | Action | Expected Result |
|---|---|---|
| 1 | Post BASE with `session_id` `R02-20261031-03` and `"loudness_dbfs": -35` | 201 (accepted) |
| 2 | `SELECT ingest_warnings FROM raw_sessions WHERE session_id = 'R02-20261031-03';` | Exactly one item `{"field": "loudness_dbfs", "code": "implausible_value", "message": "loudness_dbfs is outside its plausible range."}`; value `-35` not in the message |
| 3 | Post BASE with `session_id` `R02-20261031-04` and `"loudness_dbfs": 0.5` | 422 `VALIDATION_ERROR`, `loudness_dbfs` `out_of_range` (must be ≤ 0) |

### TC-023-04 ISO timestamp is `invalid_format`; `schema_version` "0.2" is `UNSUPPORTED_SCHEMA_VERSION`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Post BASE (`R02-20261031-05`) with `"timestamp_utc": "2026-10-01T19:45:11Z"` | 422 `VALIDATION_ERROR`; `errors[]` has `{field: "timestamp_utc", code: "invalid_format"}` |
| 2 | Repeat with `"2026-10-31 19:58:08+00:00"`, `"2026-10-31 19:58:08.5"` and `"2026/10/31 19:58:08"` | Each 422 with `timestamp_utc` `invalid_format` |
| 3 | Post BASE (`R02-20261031-06`) with `"schema_version": "0.2"` | 422; `type` `urn:echowell:error:UNSUPPORTED_SCHEMA_VERSION`, title `Unsupported schema version`; `errors[]` has `schema_version` `unsupported_schema_version` |
| 4 | Post BASE (`R02-20261031-07`) with `"schema_version": 0.1` (number) | 422; `schema_version` `invalid_type` |

### TC-023-05 Unknown resident R11 → `UNKNOWN_RESIDENT`; withdrawn resident → `RESIDENT_WITHDRAWN` "resident withdrawn"

| Step | Action | Expected Result |
|---|---|---|
| 1 | Post BASE with `"resident_id": "R11"`, `"session_id": "R11-20261031-01"` | 422; `type` `urn:echowell:error:UNKNOWN_RESIDENT`; `errors[]` has `resident_id` `unknown_resident`; no `residents` row for R11 created |
| 2 | Run `python -m backend.cli withdraw-resident R08 --on 2026-10-20` | Exit code 0 |
| 3 | Post BASE with `"resident_id": "R08"`, `"device_id": "D08"`, `"session_id": "R08-20261031-01"` | 422; `type` `urn:echowell:error:RESIDENT_WITHDRAWN`; `detail` `resident withdrawn`; `errors[]` has `resident_id` `resident_withdrawn` |
| 4 | `SELECT count(*) FROM raw_sessions WHERE session_id = 'R08-20261031-01';` | 0 |
| 5 | Reset afterwards: `python -m backend.cli seed test_v0_1 --reset` | Exit code 0 |

### TC-023-06 Unknown device and session-ID prefix mismatch

| Step | Action | Expected Result |
|---|---|---|
| 1 | Post BASE (`R02-20261031-08`) with `"device_id": "D99"` | 422 `UNKNOWN_DEVICE`; `errors[]` has `device_id` `unknown_device`; no `devices` row created |
| 2 | Post BASE with `"session_id": "R03-20261031-01"` (resident R02) | 422 `SESSION_ID_MISMATCH`, title `Session ID does not match resident`; `errors[]` has `session_id` `session_id_mismatch` |
| 3 | Post BASE with `"session_id": "R02-2026-10-31"` | 422 `VALIDATION_ERROR`; `session_id` `invalid_format` |

### TC-023-07 Request-code precedence when several record-level problems occur

| Step | Action | Expected Result |
|---|---|---|
| 1 | Post BASE with `"schema_version": "0.2"`, `"resident_id": "R11"`, `"session_id": "R11-20261031-02"`, `"device_id": "D99"` | 422 `type` `urn:echowell:error:UNSUPPORTED_SCHEMA_VERSION`; `errors[]` lists `unsupported_schema_version`, `unknown_resident` and `unknown_device` |
| 2 | Post BASE with `"resident_id": "R11"`, `"session_id": "R11-20261031-03"`, `"device_id": "D99"` | 422 `UNKNOWN_RESIDENT` (precedes `UNKNOWN_DEVICE`) |
| 3 | Post BASE with `"device_id": "D99"`, `"session_id": "R03-20261031-02"` | 422 `UNKNOWN_DEVICE` (precedes `SESSION_ID_MISMATCH`) |
| 4 | Post BASE with `"session_id": "R03-20261031-03"` and `"pause_fraction": 1.2` | 422 `SESSION_ID_MISMATCH`; `errors[]` also lists `pause_fraction` `out_of_range` |

### TC-023-08 Device-bound key and another device → 403 `DEVICE_KEY_MISMATCH`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Post BASE (R02 on D02, `R02-20261031-09`) with `X-API-Key: <qa-d01 key>` (bound to D01) | 403; `type` `urn:echowell:error:DEVICE_KEY_MISMATCH`, title `API key not valid for this device` |
| 2 | `SELECT raw_body->>'device_id', errors FROM ingest_rejections WHERE raw_body->>'session_id' = 'R02-20261031-09';` | 1 row; `D02`; body stored for audit of the refusal |
| 3 | Post a record of R01 on D01 (BASE with `resident_id` R01, `device_id` D01, `session_id` `R01-20261031-05`, `mean_f0_hz` 180.0) with the `qa-d01` key | 201 |

### TC-023-09 JSON numeric string is `invalid_type`; CSV `-30.1` accepted and `NaN` is `non_finite`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Post BASE (`R02-20261031-10`) with `"loudness_dbfs": "-30.1"` (string) | 422 `VALIDATION_ERROR`; `loudness_dbfs` `invalid_type` |
| 2 | Post BASE with `"phrase_id": 1` (number) | 422; `phrase_id` `invalid_type` |
| 3 | As admin, upload `POST /api/v1/ingest` multipart (`file=@qa.csv;type=text/csv`) with the SRC-05 header and one row equal to BASE (`R02-20261031-11`) but `loudness_dbfs` cell `-30.1` | Batch response `accepted` 1, `rejected` 0 |
| 4 | Upload a second CSV row (`R02-20261031-12`) whose `loudness_dbfs` cell is `NaN`; and a third (`-13`) with `inf` | Each row rejected with `loudness_dbfs` `non_finite` (`rejected` counts them; rejection rows stored) |
| 5 | CSV row (`-14`) with `number_of_pauses` cell `2.0` | Accepted (CSV integer rule `^\d+(\.0+)?$`); cell `2.5` → `not_integer` |

### TC-023-10 Range, integer and enum rules of TRD 10 §4.4

| Step | Action | Expected Result |
|---|---|---|
| 1 | Post BASE variants (each with a new `session_id`): `"number_of_pauses": -1` | 422; `number_of_pauses` `out_of_range` |
| 2 | `"voiced_fraction": -0.01` | `voiced_fraction` `out_of_range` |
| 3 | `"speech_duration_s": -0.1` and `"total_phrase_duration_s": -1` | `out_of_range` for each |
| 4 | `"mic_noise_level_dbfs": 1.0` | `mic_noise_level_dbfs` `out_of_range` (must be ≤ 0) |
| 5 | `"mean_f0_hz": 0` | `mean_f0_hz` `out_of_range` (must be > 0) |
| 6 | `"audio_quality_flag": "OK"` and `"good"` | `audio_quality_flag` `invalid_enum` (exactly `ok` or `poor`) |
| 7 | `"audio_quality_flag": "poor"` | 201 accepted (quality gate is a later pipeline stage, not a reject rule) |

### TC-023-11 Missing field and text rules (exact text, whitespace in versions)

| Step | Action | Expected Result |
|---|---|---|
| 1 | Post BASE without `phrase_id` | 422; `errors[]` has `{field: "phrase_id", code: "missing_field"}` |
| 2 | Post `{}` | 422 listing `missing_field` for all 30 fields |
| 3 | Post BASE with `"extraction_software_version": " openSMILE 3.0.2"` (leading space) | 422; `extraction_software_version` `invalid_format` (version strings with leading/trailing whitespace rejected) |
| 4 | Post BASE (`R02-20261031-20`) with `"phrase_id": "p01"` | 201; `SELECT phrase_id FROM raw_sessions WHERE session_id = 'R02-20261031-20';` = `p01` (no case change) |

### TC-023-12 Non-blocking warnings: date mismatch, inactive device, assignment mismatch, future timestamp, F0 by sex

| Step | Action | Expected Result |
|---|---|---|
| 1 | Post BASE with `"session_id": "R02-20261030-31"` (timestamp local date Oct 31) | 201; `ingest_warnings` contains `session_id_date_mismatch` |
| 2 | Post BASE (`R07-20261031-01`, resident R07) with `"device_id": "D07"`, `"mean_f0_hz": 180.0` | 201; `ingest_warnings` contains `device_inactive` and does not contain `device_assignment_mismatch`; the run started by the record lists `device_assignment_mismatch` for `R07-20261031-01` in `pipeline_runs.warnings` (run warning per TRD 10 v0.6, D-125) |
| 3 | Post BASE with `timestamp_utc` 2 days after now (`session_id` with that local date) | 201; `ingest_warnings` contains `timestamp_in_future` |
| 4 | Post BASE (`R02-20261031-21`, R02 is `M`) with `"mean_f0_hz": 180.0` | 201; `implausible_value` on `mean_f0_hz` (male range 110–145) |
| 5 | Post an R01 (`F`) record with `"mean_f0_hz": 180.0` | 201; no `mean_f0_hz` warning (female range 165–200) |

Note: FEAT-023 (Scope, FR-17) lists `device_assignment_mismatch` among the ingest warnings; TRD 10 revision 0.6 (TRD 24 D-125) moved it to the pipeline run warnings, and the code follows the TRD (`analytics/pipeline.py:297`; not produced in `backend/services/validation.py`). This case follows the TRD.

### TC-023-13 Renamed column through `feature_name_map` is accepted; payload keeps the external name

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read the current map: `SELECT value FROM config_parameters WHERE profile = 'test_v0_1' AND key = 'feature_name_map';` and save it | Identity map of the 30 names |
| 2 | Build a copy in which the key `loudness_dbfs` is replaced by `Loudness_sma3_amean` (value still `loudness_dbfs`); apply with `python -m backend.cli set-config --profile test_v0_1 --key feature_name_map --value '<json>' --reason "QA TST-031 rename"` | Exit code 0; one `config.changed` audit row |
| 3 | Post BASE (`R02-20261031-22`) with the key `loudness_dbfs` renamed to `Loudness_sma3_amean` (value `-25.94`) | 201 |
| 4 | `SELECT loudness_dbfs, payload ? 'Loudness_sma3_amean', payload ? 'loudness_dbfs' FROM raw_sessions WHERE session_id = 'R02-20261031-22';` | `-25.94`, `true`, `false` |
| 5 | Restore the saved map with `set-config` | Exit code 0 |
| 6 | Run `pytest -m integration tests/integration/api/test_ingest.py -q -k mapped_header_is_accepted` | Passes (AC-ING-08 / TST-031) |

### TC-023-14 Invalid `feature_name_map` prevents start-up

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `set-config --profile test_v0_1 --key feature_name_map` with a map in which both `loudness_dbfs` and `Loudness_sma3_amean` map to `loudness_dbfs` | Refused (exit code 2) naming the duplicate target; map unchanged |
| 2 | Run `pytest tests/unit/backend/services/test_validation.py -q -k invalid_name_maps_are_refused` and `pytest -m integration tests/integration/api/test_ingest.py -q -k invalid_name_map_stops_startup` | Both pass: the invalid map raises `NameMapError` and the app exits with `Configuration error: …` and a CRITICAL `invalid_feature_name_map` log line |
| 3 | Local only: write the invalid map directly as the migrator (`UPDATE config_parameters SET value = '<invalid json>' WHERE profile = 'test_v0_1' AND key = 'feature_name_map';`) and `docker compose restart backend` | Backend does not become healthy; log shows `invalid_feature_name_map`; restore the saved map and restart |

### TC-023-15 All 283 SRC-05 rows validate with zero errors

| Step | Action | Expected Result |
|---|---|---|
| 1 | After `seed test_v0_1 --reset`, run `SELECT count(*) FROM raw_sessions;` and `SELECT count(*) FROM ingest_rejections;` | 283 and 0 |
| 2 | Run `pytest tests/unit/backend/services/test_validation.py -q -k every_src_05_row_validates` | Passes (283 rows of `tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv`) |

### TC-023-16 Validator registry and code lists equal the TRD

| Step | Action | Expected Result |
|---|---|---|
| 1 | `python -c "from backend.services.validation import VALIDATORS; print(sorted(VALIDATORS))"` | `['0.1']` |
| 2 | `SELECT value FROM config_parameters WHERE profile = 'test_v0_1' AND key = 'supported_schema_versions';` | `["0.1"]` |
| 3 | Run `pytest tests/unit/backend/services/test_validation.py -q` | All pass (TST-030; codes equal ING-023) |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/sessions` valid record | 201 `IngestResult` |
| 2 | Invalid record | 422 Problem with `type` per ING-004 precedence and `errors[]` `{field, code, message}` without values |
| 3 | Device-bound key, other device | 403 `DEVICE_KEY_MISMATCH` |
| 4 | `POST /api/v1/ingest` CSV | Per-row rejections counted; batch not failed by record errors |
| 5 | Field names in `errors[]` | Canonical names after mapping, or the extra property name for `extra_forbidden` |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT count(*) FROM raw_sessions;` after seed | 283 |
| 2 | Every rejected case | One `ingest_rejections` row with `raw_body` as received and `errors` array ≥ 1 item; no `raw_sessions` row |
| 3 | `SELECT ingest_warnings FROM raw_sessions WHERE session_id = 'R02-20261031-03';` | One `implausible_value` item |
| 4 | `SELECT count(*) FROM residents WHERE resident_code = 'R11';` and devices `D99` | 0 (no auto-registration) |
| 5 | `SELECT count(*) FROM ingest_rejections WHERE errors::text ~ '(-30\.1|1\.2|AAAA)';` | 0 (messages never echo values) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Unsupported `schema_version` | 422 `UNSUPPORTED_SCHEMA_VERSION` |
| 2 | Unknown resident / device | 422 `UNKNOWN_RESIDENT` / `UNKNOWN_DEVICE` |
| 3 | Withdrawn resident | 422 `RESIDENT_WITHDRAWN`, "resident withdrawn" |
| 4 | Session prefix ≠ resident | 422 `SESSION_ID_MISMATCH` |
| 5 | Extra field `audio_base64` | `extra_forbidden` |
| 6 | Invalid `feature_name_map` | Start-up refused |
| 7 | Bound key, other device | 403 `DEVICE_KEY_MISMATCH` |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-023-AC-01 | `pause_fraction` 1.2, `number_of_pauses` 1.5 and extra `audio_base64` give three errors `out_of_range`, `not_integer`, `extra_forbidden` in one result | TC-023-02 |
| FEAT-023-AC-02 | `loudness_dbfs` -35 accepted with one `implausible_value` warning on `loudness_dbfs` | TC-023-03 |
| FEAT-023-AC-03 | `"2026-10-01T19:45:11Z"` → `invalid_format`; `schema_version` "0.2" → `UNSUPPORTED_SCHEMA_VERSION` | TC-023-04 |
| FEAT-023-AC-04 | R11 → `UNKNOWN_RESIDENT`; withdrawn resident → `RESIDENT_WITHDRAWN` with detail "resident withdrawn" | TC-023-05 |
| FEAT-023-AC-05 | With `Loudness_sma3_amean` mapped to `loudness_dbfs`, the record is accepted with typed `loudness_dbfs` and payload keeping `Loudness_sma3_amean` | TC-023-13 |
| FEAT-023-AC-06 | Two external names mapping to `loudness_dbfs` rejected at load; application refuses to start | TC-023-14 |
| FEAT-023-AC-07 | All 283 rows of the SRC-05 input validate with zero errors | TC-023-15 |
| FEAT-023-AC-08 | D02 record with a key bound to D01 → `DEVICE_KEY_MISMATCH` | TC-023-08 |
| FEAT-023-AC-09 | JSON `"loudness_dbfs": "-30.1"` → `invalid_type`; CSV `-30.1` accepted; CSV `NaN` → `non_finite` | TC-023-09 |

## Test Data Requirements

- `test_v0_1` seed (roster per TRD 20 §4.12; SRC-05 input of 283 rows).
- BASE record (synthetic, from SRC-05 row `R02-20261001-01` with a new session ID); variants with session IDs `R02-20261031-NN`, `R01-20261031-05`, `R07-20261031-01`, `R08-20261031-01`, `R11-20261031-0N`.
- Fixture codes R11 (not enrolled) and D99 (unknown); withdrawn R08 (temporary, reset afterwards).
- Keys: `SEED_INGEST_API_KEY`; device-bound `qa-d01` (D01).
- Placeholder `"AAAA"` for the extra-field check (not audio). No audio is sent anywhere.
- Saved copy of the original `feature_name_map` for restoration.
- Accepted test records start ingest-triggered pipeline runs and change R01, R02 and R07 state; run `python -m backend.cli seed test_v0_1 --reset` after the suite before any DS-07 check.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-023-FR-01 / ING-016 / API-033 / FR-012 / ARC-054 / D-12 | FEAT-023 | TC-023-13 |
| FEAT-023-FR-02 / ING-017 | FEAT-023 | TC-023-14 |
| FEAT-023-FR-03 / ING-018 / DME-015 | FEAT-023 | TC-023-01, TC-023-13 |
| FEAT-023-FR-04 / ING-014 | FEAT-023 | TC-023-16 |
| FEAT-023-FR-05 / ING-013 / ING-015 / API-035 / FR-020 | FEAT-023 | TC-023-04, TC-023-16 |
| FEAT-023-FR-06 / ING-019 / API-034 | FEAT-023 | TC-023-02, TC-023-07 |
| FEAT-023-FR-07 / FR-021 / FR-013 / OQ-04 | FEAT-023 | TC-023-02, TC-023-11 |
| FEAT-023-FR-08 / ING-021 / FR-023 | FEAT-023 | TC-023-09 |
| FEAT-023-FR-09 / TRD 10 §4.4 / FR-024 | FEAT-023 | TC-023-10 |
| FEAT-023-FR-10 / ING-022 | FEAT-023 | TC-023-11 |
| FEAT-023-FR-11 / ING-025 / ING-026 / FR-022 | FEAT-023 | TC-023-04 |
| FEAT-023-FR-12 / ING-027 | FEAT-023 | TC-023-12 |
| FEAT-023-FR-13 / API-039 | FEAT-023 | TC-023-06 |
| FEAT-023-FR-14 / API-036 / API-037 / FR-025 | FEAT-023 | TC-023-05, TC-023-06 |
| FEAT-023-FR-15 / API-038 / FR-026 / FR-228 / AC-ING-10 | FEAT-023 | TC-023-05 |
| FEAT-023-FR-16 / API-040 / SEC-023 | FEAT-023 | TC-023-08 |
| FEAT-023-FR-17 / ING-020 / ING-023 | FEAT-023 | TC-023-03, TC-023-12 |
| FEAT-023-FR-18 / ING-028 | FEAT-023 | TC-023-12 |
| FEAT-023-FR-19 / FR-027 / LOG-043 | FEAT-023 | TC-023-02, Database Validation 5 |
| FEAT-023-FR-20 / ING-024 | FEAT-023 | TC-023-15 |
| TST-030 | FEAT-023 | TC-023-16 |
| TST-031 / AC-ING-08 | FEAT-023 | TC-023-13 |
| AC-ING-04, AC-ING-05, AC-API-06, AC-API-07 | FEAT-023 | TC-023-02, TC-023-03, TC-023-04, TC-023-05 |
