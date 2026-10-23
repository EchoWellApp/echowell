# FEAT-023 Ingest record validation, schema-version registry and feature-name mapping

| Field | Value |
|---|---|
| Epic | Data Processing |
| Build phase | Phase 5 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-010, FEAT-009, FEAT-019 |
| Status | Not Started |

## Purpose

Decide, for every incoming feature record, whether it may enter the immutable raw store: translate external field names to canonical names through the configurable `feature_name_map`, select the validator by `schema_version` from a registry, apply every reject rule of schema v0.1 (collecting all violations, never stopping at the first), resolve the resident and device, refuse withdrawn residents and device-key mismatches, and compute non-blocking plausibility warnings. It is pure service logic shared by the single-record, batch-JSON and CSV ingest paths; it stores nothing and contains no HTTP handler.

## Business Context

- BR-01: only well-formed feature records of schema v0.1 are accepted; any unexpected field (e.g. audio content) is rejected (FR-013, FR-020..FR-025).
- BR-16 and OQ-11: withdrawn residents' records are refused with "resident withdrawn" (FR-026, FR-228).
- OQ-03 / RSK-02: Team 1's final extractor names can be adopted by configuration, not code (FR-012, D-12, ARC-054).
- BR-15: all 283 SRC-05 records pass validation with the test roster (ING-024).

## Referenced TRDs

- TRD 10 ING-013..ING-028, ING-004 (request-code precedence); §4.4 field-by-field validation table (reject and warn rules); §8 notes; AC-ING-04, AC-ING-05, AC-ING-08, AC-ING-10.
- TRD 05 API-033..API-040; §4.7 error catalogue (`VALIDATION_ERROR`, `UNSUPPORTED_SCHEMA_VERSION`, `UNKNOWN_RESIDENT`, `UNKNOWN_DEVICE`, `RESIDENT_WITHDRAWN`, `SESSION_ID_MISMATCH`, `DEVICE_KEY_MISMATCH`).
- TRD 23 DME-015; §4.7.1 column mapping.
- TRD 13 TST-030, TST-031.
- TRD 01 ARC-054.
- TRD 02 FR-012, FR-013, FR-020..FR-027, FR-228.
- TRD 24 D-12; OQ-03, OQ-04.

## Scope

- `backend/services/validation.py` (existing skeleton file):
  - `VALIDATORS = {"0.1": validate_v0_1}` registry; `validate(raw: Mapping[str, Any], *, source: "json" | "csv", principal, context) -> ValidationResult`.
  - Feature-name mapping: load `feature_name_map` from `config_parameters` for the active profile; validate on load (each target one of the 30 canonical names, no two external names mapping to the same key, no external name equal to a different canonical key); an invalid mapping is a configuration error that prevents startup.
  - `validate_v0_1` applying every Reject rule of TRD 10 §4.4 and collecting all violations as `{field, code, message}` with codes exactly from ING-023: `missing_field`, `invalid_type`, `invalid_format`, `invalid_enum`, `out_of_range`, `not_integer`, `non_finite`, `extra_forbidden`, `unsupported_schema_version`, `session_id_mismatch`, `unknown_resident`, `resident_withdrawn`, `unknown_device`.
  - Type rules per source: JSON numbers must be numbers (numeric strings → `invalid_type`), JSON text must be strings; CSV cells parsed with `float()` after a non-empty check; `nan`, `inf`, `-inf` in any case → `non_finite`; `number_of_pauses` integer (JSON without fractional part; CSV matching `^\d+(\.0+)?$`) and ≥ 0.
  - `timestamp_utc` must match `^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$`, parsed with `datetime.strptime(..., "%Y-%m-%d %H:%M:%S")`, UTC; ISO `T`/`Z`/offset/fraction forms → `invalid_format`.
  - `session_id` pattern `^([A-Z0-9]{1,16})-(\d{8})-(\d{2})$`, ≤ 64 characters, group 1 must equal `resident_id` (`session_id_mismatch`).
  - Lookups: `resident_id` → `residents.resident_code` (`unknown_resident`; withdrawn → `resident_withdrawn`, detail "resident withdrawn"); `device_id` → `devices.device_code` (`unknown_device`).
  - Device-bound key check: when the principal's API key has `device_id` and the record's device differs → `DEVICE_KEY_MISMATCH` outcome (403).
  - Warnings (never reject): `implausible_value` per TRD 10 §4.4 Warn column (F0 range by resident sex), `session_id_date_mismatch` (group 2 ≠ local date in `FACILITY_TZ`), `before_enrollment`, `device_inactive`, `device_assignment_mismatch`, `timestamp_in_future` (later than `received_at` + 24 h); all aggregated into one `ingest_warnings` array.
  - Result: request-level problem code for single-record responses (precedence of ING-004), field `errors[]`, canonical typed values for the `raw_sessions` columns, original payload (unmapped names and values) for `raw_sessions.payload`, resolved `resident_id`/`device_id` UUIDs, `ingest_warnings`.
- Pydantic 2 model for the JSON body with `extra="forbid"`, `strict=True` for numbers and strings, feeding the single rule function shared with CSV.

## Out of Scope

- HTTP handlers, response building, storage in `raw_sessions`/`ingest_rejections`, advisory locks and duplicate verdicts (FEAT-025, FEAT-026).
- CSV file-level checks (encoding, header equality → `CSV_HEADER_MISMATCH`, `EMPTY_BATCH`) (FEAT-026).
- Warning `duplicate_payload_differs` (needs the earlier arrival; FEAT-041 / FEAT-025 per ING-037).
- Exclusion of future-timestamp records from runs whose `as_of` precedes them (ING-028 second half; TRD 07 ANL-015, FEAT-052).
- The `set-config` command that changes `feature_name_map` (FEAT-055).
- Speaker-verification input (FEAT-097, Future, OQ-14).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-023-FR-01 | Incoming field names shall be translated to canonical names through `feature_name_map` (active profile) before validation. | ING-016, API-033, FR-012, ARC-054, D-12 |
| FEAT-023-FR-02 | The mapping shall be validated when loaded (targets among the 30 canonical names, no two external names to one key, no external name equal to a different canonical key); an invalid mapping prevents startup with a configuration error. | ING-017 |
| FEAT-023-FR-03 | `raw_sessions.payload` input shall keep the original unmapped names and values; typed values use canonical names. | ING-018, DME-015 |
| FEAT-023-FR-04 | Validators shall be selected through `backend/services/validation.py::VALIDATORS = {"0.1": validate_v0_1}`; adding a version adds a validator and mapping without changing existing ones. | ING-014 |
| FEAT-023-FR-05 | `schema_version` shall be a string in `supported_schema_versions` (seeded `["0.1"]`), else `unsupported_schema_version` and request code `UNSUPPORTED_SCHEMA_VERSION`; the stored value is the received value. | ING-013, ING-015, API-035, FR-020 |
| FEAT-023-FR-06 | Every Reject rule of TRD 10 §4.4 shall be applied and all violations of a record collected before rejecting it. | ING-019, API-034 |
| FEAT-023-FR-07 | All 30 fields (11 metadata including `phrase_id`, 19 features) are required; any other field after mapping is `extra_forbidden`. | FR-021, FR-013, OQ-04 |
| FEAT-023-FR-08 | JSON numeric fields must be JSON numbers and text fields strings; CSV numeric cells are parsed with `float()` after a non-empty check; `nan`, `inf`, `-inf` (any case) are `non_finite`. | ING-021, FR-023 |
| FEAT-023-FR-09 | `number_of_pauses` shall be an integer ≥ 0 (`not_integer`, `out_of_range`); `pause_fraction`, `voiced_fraction` in [0, 1]; `speech_duration_s`, `total_phrase_duration_s` and the other non-negative features ≥ 0; `mic_noise_level_dbfs`, `loudness_dbfs` ≤ 0; `mean_f0_hz` > 0; `audio_quality_flag` exactly `ok` or `poor` (`invalid_enum`). | TRD 10 §4.4, API-034, FR-023, FR-024 |
| FEAT-023-FR-10 | Text values shall be kept exactly as received (no trimming, no case change); version strings with leading/trailing whitespace are rejected. | ING-022, TRD 10 §4.4 |
| FEAT-023-FR-11 | `timestamp_utc` shall match `^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$`, be parsed as UTC with `strptime`, and ISO forms with `T`, `Z`, offsets or fractions rejected with `invalid_format`; the typed value is the UTC instant. | ING-025, ING-026, FR-022 |
| FEAT-023-FR-12 | Local date/time for warnings shall be derived only by converting to `FACILITY_TZ` with `zoneinfo`. | ING-027 |
| FEAT-023-FR-13 | `session_id` group 1 must equal the record's `resident_id`, else `session_id_mismatch` and request code `SESSION_ID_MISMATCH`. | API-039 |
| FEAT-023-FR-14 | An unknown `resident_id` → `unknown_resident` (`UNKNOWN_RESIDENT`); unknown `device_id` → `unknown_device` (`UNKNOWN_DEVICE`); no auto-registration. | API-036, API-037, FR-025 |
| FEAT-023-FR-15 | A record for a resident with `status = withdrawn` → `resident_withdrawn` (`RESIDENT_WITHDRAWN`, detail "resident withdrawn"). | API-038, FR-026, FR-228 |
| FEAT-023-FR-16 | When the authenticating key is bound to a device and the record's `device_id` differs, the outcome shall be 403 `DEVICE_KEY_MISMATCH` with the body to be stored in `ingest_rejections`. | API-040, SEC-023 |
| FEAT-023-FR-17 | Plausibility (Warn column) and the other warning codes of ING-023 shall never cause rejection and shall be aggregated into one `ingest_warnings` array of `{field, code, message}`. | ING-020, ING-023 |
| FEAT-023-FR-18 | Records with a future timestamp shall be accepted with `timestamp_in_future`. | ING-028 |
| FEAT-023-FR-19 | Field-level `errors[]` shall be `{field, code, message}` without the submitted value, suitable for the 422 Problem body. | FR-027, LOG-043 |
| FEAT-023-FR-20 | All 283 SRC-05 records shall pass validation when the TRD 20 §4.12 roster exists. | ING-024 |

## Inputs

- A raw record (JSON object or CSV row as header → cell text), its source type, the authenticating `Principal` (from FEAT-020), the received time.
- `config_parameters` (`supported_schema_versions`, `feature_name_map`), `residents`, `devices`, `device_assignments`, `api_keys` (FEAT-009); `FACILITY_TZ`.

## Outputs

- `ValidationResult`: accepted flag; request-level code; `errors[]`; canonical typed values for the 30 `raw_sessions` columns; original payload; resolved resident and device UUIDs; `ingest_warnings`; or a device-key-mismatch outcome.

## Data Flow

Ingest handler (FEAT-025/026) passes the raw record → mapping renames keys → registry selects `validate_v0_1` by `schema_version` → field rules run and collect violations → lookups resolve resident (status) and device → device-binding check against the principal → warnings computed in `FACILITY_TZ` → result returned to the handler, which stores the record (accepted) or the rejection (rejected).

## Dependencies

Required before implementation (BACKLOG.md): FEAT-010, FEAT-009, FEAT-019

- FEAT-010 defines the `raw_sessions` typed columns and `ingest_rejections.errors` shape the result must fit.
- FEAT-009 provides `config_parameters` (`supported_schema_versions`, `feature_name_map`), `residents`, `devices`, `device_assignments`, `api_keys`.
- FEAT-019 provides the error codes and the Problem rendering used by the callers.

Features that build directly on this one (BACKLOG.md §4): FEAT-025, FEAT-097.

## Database Impact

- Tables read: `config_parameters`, `residents`, `devices`, `device_assignments`.
- Tables written: none (callers write `raw_sessions` and `ingest_rejections`).

## API Impact

None exposed. Determines the 422/403 outcomes of E-05 `POST /sessions` and E-06 `POST /ingest`.

## Frontend Impact

None directly; rejection rows appear in the admin batch result (FEAT-074) through E-07.

## Analytics Impact

None. Validation is not an analytics stage; quality-gate decisions (noise, speech duration, quality flag) are made later by FEAT-041 and are not reject rules.

## Security Requirements

- `extra="forbid"`: no unexpected field, so no audio or free text can enter the raw store (FR-013, AGT-006).
- Device-bound keys cannot submit records for other devices (SEC-023, API-040).
- Error messages and warnings never echo feature values (LOG-021, LOG-043).

## Error Handling

| Condition | Field code | Request code (single record) |
|---|---|---|
| Unsupported `schema_version` | `unsupported_schema_version` | `UNSUPPORTED_SCHEMA_VERSION` (422) |
| Unknown resident | `unknown_resident` | `UNKNOWN_RESIDENT` (422) |
| Unknown device | `unknown_device` | `UNKNOWN_DEVICE` (422) |
| Withdrawn resident | `resident_withdrawn` | `RESIDENT_WITHDRAWN` (422, "resident withdrawn") |
| Session prefix ≠ resident | `session_id_mismatch` | `SESSION_ID_MISMATCH` (422) |
| Any other rule | `missing_field`, `invalid_type`, `invalid_format`, `invalid_enum`, `out_of_range`, `not_integer`, `non_finite`, `extra_forbidden` | `VALIDATION_ERROR` (422) |
| Bound key, other device | — | `DEVICE_KEY_MISMATCH` (403) |
| Invalid `feature_name_map` | — | startup refused with a configuration error |

When several record-level problems occur, all field codes are listed in `errors[]`, and the request-level code is the first of `UNSUPPORTED_SCHEMA_VERSION`, `UNKNOWN_RESIDENT`, `UNKNOWN_DEVICE`, `RESIDENT_WITHDRAWN`, `SESSION_ID_MISMATCH` that applies, else `VALIDATION_ERROR` (ING-004).

## Logging Requirements

None directly; callers log `ingest_record_rejected` with identifiers and error locations only (LOG-021, FEAT-025). No audit rows.

## Testing Requirements

- Unit (`tests/unit/backend/services/test_validation.py`, marker `unit`): TST-030 (each required field missing → error naming the field; wrong type; `audio_quality_flag` outside {ok, poor}; `schema_version` not supported; `number_of_pauses` negative or non-integer; `timestamp_utc` not `YYYY-MM-DD HH:MM:SS`); collect-all behaviour (ING-019); JSON numeric string → `invalid_type`; CSV `NaN`/`inf` → `non_finite`; text preserved exactly (ING-022); warning codes (ING-020, ING-023), F0 range by sex; mapping validation errors (ING-017).
- Integration (`tests/integration/api/test_sessions.py` via FEAT-025): AC-ING-04 (`pause_fraction = 1.2` → `out_of_range`; `number_of_pauses = 1.5` → `not_integer`; extra `audio_base64` → `extra_forbidden`; `loudness_dbfs = −35` accepted with `implausible_value`), AC-ING-05, AC-ING-10, AC-API-06, AC-API-07.
- Integration (`tests/integration/api/test_ingest.py` via FEAT-026): AC-ING-08 and TST-031 (renamed column through configuration yields identical pipeline output on SRC-05); ING-024 (all 283 SRC-05 rows valid).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-023-AC-01 | Validating a record with `pause_fraction = 1.2`, `number_of_pauses = 1.5` and an extra field `audio_base64` returns three errors with codes `out_of_range`, `not_integer`, `extra_forbidden` (all collected in one result). Verified by: Integration (`tests/integration/api/test_sessions.py`). | AC-ING-04, ING-019 |
| FEAT-023-AC-02 | A record with `loudness_dbfs = -35` is accepted with one warning `implausible_value` on `loudness_dbfs`. Verified by: Unit (`tests/unit/backend/services/test_validation.py`). | AC-ING-04, ING-020 |
| FEAT-023-AC-03 | `timestamp_utc = "2026-10-01T19:45:11Z"` yields `invalid_format`; `schema_version = "0.2"` yields request code `UNSUPPORTED_SCHEMA_VERSION`. Verified by: Integration (`tests/integration/api/test_sessions.py`). | AC-ING-05, ING-025, ING-013 |
| FEAT-023-AC-04 | A record with `resident_id` R11 (not enrolled) yields `UNKNOWN_RESIDENT`; a record for a withdrawn resident yields `RESIDENT_WITHDRAWN` with detail "resident withdrawn". Verified by: Integration (`tests/integration/api/test_sessions.py`). | AC-API-06, AC-ING-10, FR-026 |
| FEAT-023-AC-05 | With `feature_name_map = {"Loudness_sma3_amean": "loudness_dbfs", …identity for the rest}`, a record keyed `Loudness_sma3_amean` is accepted with canonical typed `loudness_dbfs` and the payload keeps `Loudness_sma3_amean`. Verified by: Integration (`tests/integration/api/test_ingest.py`; TST-031). | AC-ING-08, ING-016, ING-018 |
| FEAT-023-AC-06 | A mapping with two external names mapping to `loudness_dbfs` is rejected at load, and the application refuses to start with a configuration error. Verified by: Unit (`tests/unit/backend/services/test_validation.py`). | ING-017 |
| FEAT-023-AC-07 | With the TRD 20 §4.12 roster, every one of the 283 rows of `tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv` validates with zero errors. | ING-024 |
| FEAT-023-AC-08 | A record for device D02 authenticated by a key bound to D01 yields the `DEVICE_KEY_MISMATCH` outcome. Verified by: Integration (`tests/integration/api/test_ingest.py`; TST-031). | API-040 |
| FEAT-023-AC-09 | In JSON, `"loudness_dbfs": "-30.1"` yields `invalid_type`; in CSV the cell `-30.1` is accepted and `NaN` yields `non_finite`. Verified by: Unit (`tests/unit/backend/services/test_validation.py`). | ING-021 |

## Definition of Done

- All FEAT-023 acceptance criteria pass; TST-030 passes; TST-031 passes once FEAT-026 and the pipeline exist.
- The ING-023 code lists in code equal the TRD (unit test compares them); delivered in the Phase 5 checkpoint PR of Block 3.

## Implementation Notes

- Run the rules in one function returning all violations so JSON and CSV share one path (TRD 10 §8); the Pydantic model with `strict=True` handles shape, the rule function handles every TRD 10 §4.4 rule.
- Do not use pandas for uploads; CSV rows arrive as `csv.DictReader` dictionaries of strings (TRD 10 §8).
- Cache `feature_name_map` and `supported_schema_versions` per request (they are operational keys that take effect on the next request, NFR-084).
- Plausibility ranges are placeholders until measured on the v1 rig (ING-020, RSK-02); keep them in one table in code that mirrors TRD 10 §4.4.
