# Device speaker-verification input

## Feature Description

Status: Not Started — these test cases are written from the feature file and run only once the feature is built (BACKLOG.md §10).

FEAT-097 accepts the speaker-verification result that Team 1's device may produce in future, so that a record spoken by someone other than the resident can be recognised from the device's own verification instead of only from the statistical speaker screen. The mechanism is fixed by the TRDs: the field arrives only under a new record `schema_version` (string set by Team 1's record specification, written `<new version>` below), added to `supported_schema_versions` with `set-config` (operational key, effective at the next request, no rebuild) and to the registry `backend/services/validation.py::VALIDATORS` with a new validator; `validate_v0_1` and the v0.1 `feature_name_map` entries stay unchanged; `raw_sessions.payload` keeps the original names and values and `raw_sessions.schema_version` the received value. Schema v0.1 records keep being validated, processed and screened exactly as today, and R05 days 8 and 22 stay quarantined with the exact SRC-03 reasons. No ML model or speaker-recognition service runs in EchoWell. The field name, type (binary or confidence), range, missing-value semantics and the combination rule with the statistical screen come from the OQ-14 decision (gate); cases that depend on them are completed from that decision.

TC-097-01, TC-097-02, TC-097-06, TC-097-07 and TC-097-10 can already be run today as regression checks of the v0.1 behaviour. All cases run on the local Compose stack with synthetic data.

## Preconditions

- Local Compose stack (`docker compose up -d --build`), seeded with `test_v0_1` (R01–R10, devices, API key `test-ingest` whose value is `SEED_INGEST_API_KEY` in `.env`).
- `.env` loaded into the shell (`set -a; . ./.env; set +a`) so the key is used without typing it.
- Python 3.12 with backend requirements for `pytest`.
- For TC-097-03..TC-097-05, TC-097-08, TC-097-09, TC-097-12: OQ-14 answered in TRD 24 with the output type and the record specification of `<new version>`; TRD 10, 08, 19, 20 updated.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-097-01 | v0.1 record with an extra verification field is rejected with 422 and stores nothing | High | Negative |
| TC-097-02 | Unregistered `schema_version` is rejected with `unsupported_schema_version` | High | Negative |
| TC-097-03 | With `<new version>` in `supported_schema_versions`, a valid new-version record returns 201 and is stored as received | High | API |
| TC-097-04 | The same record without the `set-config` change is rejected with `unsupported_schema_version` | High | Negative |
| TC-097-05 | Registry dispatches v0.1 to `validate_v0_1` and `<new version>` to the new validator | High | Positive |
| TC-097-06 | The feature diff leaves `validate_v0_1` and the v0.1 mapping entries unchanged | High | Documentation |
| TC-097-07 | R01–R10 validation passes; R05 days 8 and 22 keep their exact reasons | High | Analytics |
| TC-097-08 | Invalid verification value under `<new version>` returns 422 with all field errors | Medium | Negative |
| TC-097-09 | Adding the version and mapping is operational: effective at the next request, no rebuild | Medium | Database |
| TC-097-10 | No ML model or speaker-recognition service is on the pipeline path | High | Security |
| TC-097-11 | Ingest logs contain identifiers and error locations only, never verification values | Medium | Security |
| TC-097-12 | The statistical speaker screen keeps its behaviour until the OQ-14 combination rule is decided | High | Analytics |

### TC-097-01 v0.1 record with an extra verification field is rejected with 422 and stores nothing

| Step | Action | Expected Result |
|---|---|---|
| 1 | Prepare a valid v0.1 record for R01 / D01 (SRC-05 values of `R01-20261001-01`) with a new `session_id` `R01-20261029-09` and `timestamp_utc` `2026-10-29 14:00:00`, and add `"speaker_verification": 0.93` | Body ready |
| 2 | `curl -sS -i -X POST http://localhost:8000/api/v1/sessions -H "X-API-Key: $SEED_INGEST_API_KEY" -H 'Content-Type: application/json' -d @record.json` | `422`; `application/problem+json`; field error for `speaker_verification` with code `extra_forbidden` and message "This field is not part of schema v0.1." |
| 3 | `SELECT count(*) FROM raw_sessions WHERE session_id = 'R01-20261029-09';` | `0` |
| 4 | `SELECT errors FROM ingest_rejections ORDER BY received_at DESC LIMIT 1;` | Names `speaker_verification` / `extra_forbidden` |
| 5 | `pytest tests/integration/api/test_sessions.py -q -k tst_045` (TST-045) | Pass |

### TC-097-02 Unregistered `schema_version` is rejected with `unsupported_schema_version`

| Step | Action | Expected Result |
|---|---|---|
| 1 | POST the record of TC-097-01 without the extra field and with `"schema_version": "0.2"` | `422`; request-level code `UNSUPPORTED_SCHEMA_VERSION`; field `schema_version` code `unsupported_schema_version` "This schema version is not supported." |
| 2 | `SELECT count(*) FROM raw_sessions WHERE session_id = 'R01-20261029-09';` | `0` |
| 3 | `SELECT value FROM config_parameters WHERE key = 'supported_schema_versions';` | `["0.1"]` in both profiles |

### TC-097-03 With `<new version>` in `supported_schema_versions`, a valid new-version record returns 201 and is stored as received

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker compose exec backend python -m backend.cli set-config --profile test_v0_1 --key supported_schema_versions --value '["0.1","<new version>"]' --reason "TC-097-03 OQ-14 record specification"` | Exit 0 |
| 2 | POST a valid `<new version>` record (per Team 1's specification, with the verification field) for R01 / D01, `session_id` `R01-20261029-10` | `201` |
| 3 | `SELECT schema_version, payload FROM raw_sessions WHERE session_id = 'R01-20261029-10';` | `schema_version` = `<new version>`; `payload` equals the request body with the original field names and values (unmapped) |
| 4 | `SELECT status, reasons FROM processed_sessions p JOIN raw_sessions r ON p.raw_session_id = r.id WHERE r.session_id = 'R01-20261029-10';` | A processed status with reasons per the updated TRDs |

### TC-097-04 The same record without the `set-config` change is rejected with `unsupported_schema_version`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Reset `supported_schema_versions` to `["0.1"]` with `set-config` | Exit 0 |
| 2 | POST the `<new version>` record of TC-097-03 with `session_id` `R01-20261029-11` | `422`, `unsupported_schema_version` (even though the validator is registered) |
| 3 | `SELECT count(*) FROM raw_sessions WHERE session_id = 'R01-20261029-11';` | `0`; an `ingest_rejections` row exists |

### TC-097-05 Registry dispatches v0.1 to `validate_v0_1` and `<new version>` to the new validator

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -n "^VALIDATORS" -A3 backend/services/validation.py` | `{"0.1": validate_v0_1, "<new version>": <new validator>}` |
| 2 | Run the registry dispatch unit test (`pytest tests/unit -q -k "registry or validators"`) | Pass: v0.1 → `validate_v0_1`, new version → new validator |
| 3 | `pytest tests/integration/api/test_ingest.py -q -k "tst_030 or tst_031"` and the TST-030 test | Pass unchanged |

### TC-097-06 The feature diff leaves `validate_v0_1` and the v0.1 mapping entries unchanged

| Step | Action | Expected Result |
|---|---|---|
| 1 | `git diff <feature base>..<feature head> -- backend/services/validation.py` | Only additions (new validator, new registry entry); no line of `def validate_v0_1` or its helpers removed or changed |
| 2 | `git diff <feature base>..<feature head> -- backend/alembic database/seeds` and the `feature_name_map` values | The identity v0.1 `feature_name_map` entries unchanged; new entries only for `<new version>` |
| 3 | Today (before the feature): `grep -n '^VALIDATORS' backend/services/validation.py` | `VALIDATORS: dict[str, Validator] = {"0.1": validate_v0_1}` (baseline for the diff) |

### TC-097-07 R01–R10 validation passes; R05 days 8 and 22 keep their exact reasons

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation -q` | All pass, 0 failed |
| 2 | Local: `SELECT p.local_date, p.status, p.reasons FROM processed_sessions p JOIN residents r ON r.id = p.resident_id WHERE r.resident_code = 'R05' AND p.status = 'quarantined' ORDER BY p.local_date;` | Two rows: day 8 reason "possible other speaker (F0 z=-8.61; composite features with \|z\|>=3: 4)"; day 22 reason "possible other speaker (F0 z=-7.34; composite features with \|z\|>=3: 3)" |

### TC-097-08 Invalid verification value under `<new version>` returns 422 with all field errors

| Step | Action | Expected Result |
|---|---|---|
| 1 | With `<new version>` supported, POST a record whose verification value is outside the specified range and whose `loudness_dbfs` is `5.0` (above 0) | `422`; errors list both fields (all violations collected, ING-019) |
| 2 | Same with the verification field missing, if the specification makes it required | `422` naming the missing field |
| 3 | `SELECT count(*) FROM raw_sessions WHERE session_id IN (<ids used>);` | `0` |

### TC-097-09 Adding the version and mapping is operational: effective at the next request, no rebuild

| Step | Action | Expected Result |
|---|---|---|
| 1 | Record `SELECT config_snapshot->>'config_hash' FROM pipeline_runs WHERE status = 'succeeded' ORDER BY started_at DESC LIMIT 1;` | Hash H |
| 2 | `set-config` of `supported_schema_versions` (and `feature_name_map` entries for `<new version>` if needed) | Exit 0; `audit_logs` row `config.changed` per key |
| 3 | Immediately POST a valid `<new version>` record (no restart, no `rebuild`) | `201`; the triggered run `succeeded` (no `config_changed_requires_rebuild`) |
| 4 | Re-read the latest run's config hash | Still H (operational keys are not part of the algorithm hash) |

### TC-097-10 No ML model or speaker-recognition service is on the pipeline path

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/security/test_static_scans.py -q -k no_forbidden_dependencies` | Pass |
| 2 | `grep -niE "torch\|tensorflow\|sklearn\|scikit\|speechbrain\|pyannote\|resemblyzer" backend/requirements*.txt; echo "exit=$?"` | No output; `exit=1` |
| 3 | Search the new validator and speaker-screen code for outbound HTTP calls | None; only the device's output field is read |

### TC-097-11 Ingest logs contain identifiers and error locations only, never verification values

| Step | Action | Expected Result |
|---|---|---|
| 1 | After TC-097-01 and TC-097-08, `docker compose logs backend --since 10m` | Lines show `request_id`, session ID, field names and error codes |
| 2 | Search the log output for the verification value used (e.g. `0.93`) and for feature values | Not present |

### TC-097-12 The statistical speaker screen keeps its behaviour until the OQ-14 combination rule is decided

| Step | Action | Expected Result |
|---|---|---|
| 1 | Before the combination rule is decided, POST a `<new version>` record for R05 whose features match R05's usual values and whose verification output says "other speaker" | Status decided by the statistical screen only (`usable` here); no verification-based quarantine reason |
| 2 | POST a `<new version>` record whose F0 z ≥ 4.0 in magnitude and ≥ 2 composite features with \|z\| ≥ 3.0, verification "same speaker" | `quarantined` with reason "possible other speaker (F0 z=…; composite features with \|z\|>=3: …)" |
| 3 | After OQ-14 decides the rule | Tests written from the decision pass; PGS-012 reason CHECK updated through the TRD 20 change before any new reason string is stored |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/sessions` v0.1 record with an extra field | 422 `extra_forbidden` |
| 2 | `POST /api/v1/sessions` with `schema_version` not in `supported_schema_versions` | 422 `unsupported_schema_version` |
| 3 | `POST /api/v1/sessions` valid `<new version>` record (version supported) | 201 |
| 4 | `POST /api/v1/ingest` CSV with one v0.1 row and one `<new version>` row (version supported) | Both accepted; each validated by its own validator |
| 5 | `POST /api/v1/sessions` without `X-API-Key` | 401 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `raw_sessions.schema_version` and `payload` of a new-version record (TC-097-03) | Received value; unmapped payload |
| 2 | No `raw_sessions` row for rejected records (TC-097-01, -02, -04, -08) | 0 rows |
| 3 | `ingest_rejections` rows for rejected records | Present with field codes |
| 4 | `config_parameters` `supported_schema_versions` (TC-097-02, TC-097-03) | `["0.1"]` before; `["0.1","<new version>"]` after |
| 5 | R05 quarantine reasons (TC-097-07) | Exact SRC-03 strings |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Extra verification field in a v0.1 record (TC-097-01) | 422, nothing stored |
| 2 | Unregistered version `0.2` (TC-097-02) | 422 `unsupported_schema_version` |
| 3 | Registered validator but version not in `supported_schema_versions` (TC-097-04) | 422 `unsupported_schema_version` |
| 4 | Out-of-range verification value plus another invalid field (TC-097-08) | 422 listing both |
| 5 | Request without API key (API Validation step 5) | 401 |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-097-AC-01 | A v0.1 record with an extra verification field is rejected with 422 and creates no `raw_sessions` row | TC-097-01 |
| FEAT-097-AC-02 | With the new version supported, a valid record returns 201 and is stored with the received `schema_version` and unmapped payload; without it, rejected with `unsupported_schema_version` | TC-097-03, TC-097-04, TC-097-02, TC-097-09 |
| FEAT-097-AC-03 | `git diff` of the feature shows no change to `validate_v0_1` or the v0.1 mapping entries | TC-097-06, TC-097-05 |
| FEAT-097-AC-04 | `pytest tests/validation -q` passes unchanged; R05 days 8 and 22 quarantined with the exact SRC-03 reasons | TC-097-07, TC-097-12 |

## Test Data Requirements

- `test_v0_1` seed (R01–R10, R05 with possible-other-speaker days 8 and 22), API key `test-ingest` (value from `.env`).
- A valid v0.1 record built from the SRC-05 values of `R01-20261001-01` with new session IDs `R01-20261029-09` … `-11`.
- `<new version>` records per Team 1's record specification once OQ-14 is answered (synthetic values only; no audio).

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| ING-013, RSK-01 | FEAT-097 | TC-097-02, TC-097-03, TC-097-04 |
| ING-014, ING-016 | FEAT-097 | TC-097-05, TC-097-06 |
| FR-013, ING-019, TST-045 | FEAT-097 | TC-097-01, TC-097-08 |
| ING-015, ING-018 | FEAT-097 | TC-097-03 |
| BSC-011..BSC-019, D-13, AGT-044 | FEAT-097 | TC-097-07, TC-097-12 |
| OQ-14, AGT-009, PGS-012 | FEAT-097 | TC-097-12 |
| AGT-005, TPS-082 | FEAT-097 | TC-097-10 |
| D-56, D-69 | FEAT-097 | TC-097-09 |
| LOG-021 | FEAT-097 | TC-097-11 |
| AGT-008, BSC-016 | FEAT-097 | TC-097-07 |
| FEAT-097-FR-01..FEAT-097-FR-08 | FEAT-097 | TC-097-01..TC-097-12 |
