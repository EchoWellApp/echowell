# Analytics contracts, PipelineConfig profiles and robust statistics

## Feature Description

FEAT-040 lays the analytics foundation: the frozen data contracts in `analytics/config.py`, the 19 canonical feature keys with the 7 composite keys and their signs, the `PipelineConfig` with the two built-in profiles `production` (baseline_n 30) and `test_v0_1` (baseline_n 16), validation of configuration values (`PipelineConfig.from_mapping`, also used by `set-config`), a JSON-serialisable snapshot and a SHA-256 config hash over the algorithm keys only, the backend loader that reads the active profile from `config_parameters` (warnings `config_default_used`, `config_mismatch`; failure `pipeline_config_invalid`), the exceptions `AnalyticsError` / `ContractError` / `ConfigError`, the run-warning codes, and `robust(values, floor, mad_scale)` (median, MAD, spread = max(MAD × 1.4826, floor), strict `floor_applied`). The module is pure: no I/O, database, HTTP or environment access.

## Preconditions

- Local development stack per `README.md` quick start (virtual environment with `backend/requirements-dev.txt`, numpy 2.x), working directory = repository root; Python steps run as `python -I -c "import sys; sys.path.insert(0, '.'); ..."` or in a `python` REPL started from the repository root.
- Local PostgreSQL seeded with `python -m backend.cli seed test_v0_1 --reset` (46 `config_parameters` rows: 23 keys × 2 profiles); `psql` access.
- Environment file with `PIPELINE_PROFILE=test_v0_1`, `FACILITY_TZ=America/Chicago`; `DATABASE_MIGRATION_URL` set for `set-config` (runs as `echowell_migrator`).
- TC-040-12 to TC-040-14 modify configuration on purpose; run them last and reseed with `python -m backend.cli seed test_v0_1 --reset` afterwards.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-040-01 | `robust()` reproduces the three TRD 08 §4.2 vectors (AC-BSC-01) | High | Analytics |
| TC-040-02 | `robust()` on R01 loudness days 1–16 gives median −29.925, MAD 2.165, spread 3.209829 (ROB-03) | High | Analytics |
| TC-040-03 | `robust()` refuses empty and non-finite input with `ContractError` | High | Negative |
| TC-040-04 | Seeded `test_v0_1` and `production` rows load into configs equal to the constants (baseline_n 16 / 30) | High | Database |
| TC-040-05 | `from_mapping` refuses `cusum_h = 0`, unknown key `foo`, `morning_offsets` without `mfcc4`, naming the key | High | Negative |
| TC-040-06 | `config_hash()` ignores operational keys and changes with algorithm keys; `snapshot()` round-trips through JSON; run snapshot stored | High | Analytics |
| TC-040-07 | Import-linter purity contract passes and forbids database / HTTP / backend imports | High | Positive |
| TC-040-08 | Contracts are frozen; a `RawRecord` with 18 feature keys raises `ContractError` | High | Negative |
| TC-040-09 | Feature constants: 19 keys in order, 7 composite keys, signs, floors, morning offsets | High | Analytics |
| TC-040-10 | Operational values and review explanations equal in both profiles (CFG-05) | Medium | Analytics |
| TC-040-11 | Exceptions and warning codes exactly as ANL-051 / ANL-052 | Medium | Analytics |
| TC-040-12 | `set-config` refuses an invalid value using the same validation (FR-229) | High | Negative |
| TC-040-13 | Missing key uses the built-in value and records `config_default_used`; `FACILITY_TZ` mismatch records `config_mismatch` | Medium | Database |
| TC-040-14 | Profile with no rows: run ends `failed` with `pipeline_config_invalid`; `GET /health` stays 200 | Medium | Negative |
| TC-040-15 | Parameters are never read from environment variables inside `analytics/` | Medium | Security |

### TC-040-01 robust() reproduces the TRD 08 §4.2 vectors

| Step | Action | Expected Result |
|---|---|---|
| 1 | `from analytics.robust_stats import robust; print(robust([1,2,3,4], 0, 1.4826))` | `RobustStats(median=2.5, mad=1.0, spread=1.4826, floor_applied=False)` |
| 2 | `print(robust([1,1,1,1,2,2], 0.5, 1.4826))` | `RobustStats(median=1.0, mad=0.0, spread=0.5, floor_applied=True)` |
| 3 | `print(robust([0,0,1,1,1,1,1,1,1,1,2,2,2,2,2,2], 0.5, 1.4826))` | `RobustStats(median=1.0, mad=0.5, spread=0.7413, floor_applied=False)` |
| 4 | `print(robust([3.0, 1.0, 2.0], 0, 1.4826))` (ROB-01) and `print(robust([5.0, 5.0, 5.0], 0, 1.4826))` (ROB-06) | median 2.0, MAD 1.0, spread 1.4826; then spread 0.0, `floor_applied=False` |
| 5 | `print(robust([0.0, 1.0, 2.0], 0.5, 1.4826))` (ROB-05) | spread 1.4826, `floor_applied=False` |
| 6 | `pytest -m unit tests/unit/analytics/test_robust_stats.py -v` | `test_vectors`, `test_r01_loudness_days_1_to_16`, `test_floor_equal_to_scaled_mad_is_not_applied`, `test_refuses_empty_or_non_finite` PASSED |

### TC-040-02 robust() on R01 loudness days 1–16 (ROB-03)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `from tests.unit.analytics.src05 import records; v = sorted((r for r in records() if r.resident_code == "R01"), key=lambda r: r.timestamp_utc)[:16]; print([r.session_id for r in v][0], [r.session_id for r in v][-1])` | `R01-20261001-01 R01-20261016-01` |
| 2 | `print(robust([r.features["loudness_dbfs"] for r in v], 0.0, 1.4826))` | median −29.925; MAD 2.165 (printed 2.164999999999999); spread 3.209829 (printed 3.2098289999999987); `floor_applied=False` — each within 1e-6 |
| 3 | Compare with SRC-03 `Exp_baselines` row R01 / loudness_dbfs | median −29.925, mad 2.165, robust_spread 3.209829, floor_applied "no" |

### TC-040-03 robust() refuses empty and non-finite input

| Step | Action | Expected Result |
|---|---|---|
| 1 | `robust([], 0, 1.4826)` | Raises `analytics.config.ContractError` with message "robust(): no values" |
| 2 | `robust([1.0, float("nan")], 0, 1.4826)` | Raises `ContractError` with message "robust(): non-finite value" |
| 3 | `robust([1.0, float("inf")], 0, 1.4826)` | Raises `ContractError` "robust(): non-finite value" |

### TC-040-04 Seeded profiles load into configs equal to the constants

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT profile, count(*) FROM config_parameters GROUP BY profile ORDER BY profile;` | `production` 23, `test_v0_1` 23 |
| 2 | `SELECT key, a.value AS production, b.value AS test_v0_1 FROM config_parameters a JOIN config_parameters b USING (key) WHERE a.profile='production' AND b.profile='test_v0_1' AND a.value <> b.value;` | Exactly one row: `baseline_n`, 30, 16 |
| 3 | `SELECT key, value FROM config_parameters WHERE profile='test_v0_1' AND key IN ('noise_limit_dbfs','min_speech_s','screen_min_n','screen_f0_z','screen_other_z','screen_other_count','mad_scale','pause_floor','composite_floor','cusum_k','cusum_h','morning_cutoff_hour','facility_tz') ORDER BY key;` | composite_floor 0.1; cusum_h 5.0; cusum_k 0.5; facility_tz "America/Chicago"; mad_scale 1.4826; min_speech_s 1.0; morning_cutoff_hour 12; noise_limit_dbfs −40.0; pause_floor 0.5; screen_f0_z 4.0; screen_min_n 5; screen_other_count 2; screen_other_z 3.0 |
| 4 | `pytest -m unit tests/unit/analytics/test_config.py -k profiles -v` | `test_profiles_differ_only_in_profile_and_baseline_n` PASSED |
| 5 | `GET /api/v1/residents` as admin (stack running with `PIPELINE_PROFILE=test_v0_1`) | `meta.baseline_n` = 16, `meta.cusum_h` = 5.0, `meta.pipeline_profile` = "test_v0_1" |
| 6 | Python: `from analytics.config import TEST_V0_1, PRODUCTION; print(TEST_V0_1.baseline_n, PRODUCTION.baseline_n)` | `16 30` |

### TC-040-05 from_mapping refuses invalid values naming the key

| Step | Action | Expected Result |
|---|---|---|
| 1 | `from analytics.config import TEST_V0_1 as C, PipelineConfig; v = C.values(); PipelineConfig.from_mapping(dict(v, cusum_h=0))` | Raises `ConfigError`; message starts with "cusum_h:" ("cusum_h: value 0.0 is out of range") |
| 2 | `PipelineConfig.from_mapping(dict(v, foo=1))` | `ConfigError` "foo: unknown configuration key" |
| 3 | `PipelineConfig.from_mapping(dict(v, morning_offsets={k: x for k, x in v["morning_offsets"].items() if k != "mfcc4"}))` | `ConfigError` "morning_offsets: must have exactly the 19 feature keys" |
| 4 | `PipelineConfig.from_mapping(dict(v, facility_tz="Mars/Base"))` | `ConfigError` starting "facility_tz: unknown time zone" |
| 5 | `PipelineConfig.from_mapping(dict(v, baseline_n=4))` (below `screen_min_n` 5) | `ConfigError` naming `baseline_n` or `screen_min_n` |
| 6 | `PipelineConfig.from_mapping(dict(v, alert_snooze_hours=169))` | `ConfigError` naming `alert_snooze_hours` |
| 7 | `PipelineConfig.from_mapping(dict(v, baseline_n="16"))` (wrong type) | `ConfigError` "baseline_n: must be an integer" |
| 8 | `PipelineConfig.from_mapping(v)` | Returns a config equal to `TEST_V0_1` (no error) |

### TC-040-06 Config hash and snapshot

| Step | Action | Expected Result |
|---|---|---|
| 1 | `import dataclasses, json; c2 = dataclasses.replace(C, operational=dataclasses.replace(C.operational, alert_snooze_hours=48)); print(c2.config_hash() == C.config_hash())` | `True` (operational keys are not hashed) |
| 2 | `c3 = dataclasses.replace(C, cusum_h=4.0); print(c3.config_hash() == C.config_hash())` | `False` |
| 3 | `print(json.loads(json.dumps(C.snapshot())) == C.snapshot())` | `True` |
| 4 | `print(len(C.config_hash()), sorted(C.snapshot())[:3])` | `64` (SHA-256 hex) and the first keys `['baseline_n', 'composite_floor', 'cusum_h']`; the snapshot includes `operational` |
| 5 | `SELECT config_snapshot->>'config_hash', config_snapshot->>'as_of', config_snapshot->>'baseline_n' FROM pipeline_runs WHERE status='succeeded' ORDER BY started_at DESC LIMIT 1;` | 64-character hex hash; as_of `2026-10-30T20:00:00+00:00`; baseline_n `16` |
| 6 | Compare the stored hash with `C.config_hash()` printed in Python | Equal |

### TC-040-07 Import-linter purity contract

| Step | Action | Expected Result |
|---|---|---|
| 1 | `lint-imports` | Contract "analytics is pure: no backend, database, HTTP, environment or randomness" KEPT; overall "Contracts: N kept, 0 broken" |
| 2 | Read `[tool.importlinter]` in `pyproject.toml` | Forbidden modules for `analytics`: `backend`, `sqlalchemy`, `psycopg`, `fastapi`, `httpx`, `requests`, `os`, `random` |
| 3 | `grep -rn -E "^(import\|from) (sqlalchemy\|psycopg\|fastapi\|httpx\|requests\|backend\|os\|random)" analytics/` | No match |

### TC-040-08 Frozen contracts and canonical key set

| Step | Action | Expected Result |
|---|---|---|
| 1 | `C.baseline_n = 3` | Raises `dataclasses.FrozenInstanceError` |
| 2 | `from tests.unit.analytics.factory import rec; r = rec(1, "2026-10-01 19:00:00"); r.session_id = "X"` | Raises `dataclasses.FrozenInstanceError` |
| 3 | `f = dict(r.features); f.pop("mfcc4"); dataclasses.replace(r, features=f)` | Raises `ContractError` "R01-20261001-01: features must be the 19 canonical keys in contract order" |
| 4 | `dataclasses.replace(r, features={**r.features, "extra": 1.0})` | Raises `ContractError` (20 keys) |
| 5 | `pytest -m unit tests/unit/analytics/test_config.py -k frozen -v` | `test_contracts_are_frozen_and_check_features` PASSED |

### TC-040-09 Feature constants

| Step | Action | Expected Result |
|---|---|---|
| 1 | `from analytics.config import FEATURE_KEYS, COMPOSITE_KEYS, COMPOSITE_SIGNS, FEATURES; print(FEATURE_KEYS)` | 19 keys in this order: loudness_dbfs, total_phrase_duration_s, speech_rate_syl_per_s, articulation_rate_syl_per_s, number_of_pauses, pause_fraction, voiced_fraction, mean_f0_hz, f0_variability_st, jitter_local_pct, shimmer_local_pct, hnr_db, cpps_db, alpha_ratio_db, hammarberg_index_db, mfcc1, mfcc2, mfcc3, mfcc4 |
| 2 | `print(COMPOSITE_KEYS == FEATURE_KEYS[:7], COMPOSITE_SIGNS)` | `True`; signs loudness_dbfs −1, total_phrase_duration_s +1, speech_rate_syl_per_s −1, articulation_rate_syl_per_s −1, number_of_pauses +1, pause_fraction +1, voiced_fraction −1 |
| 3 | `print([(f.key, f.spread_floor, f.morning_offset) for f in FEATURES if f.spread_floor or f.morning_offset])` | number_of_pauses floor 0.5 (others 0.0); offsets loudness_dbfs −1.5, total_phrase_duration_s 0.1, speech_rate_syl_per_s −0.12, articulation_rate_syl_per_s −0.1, pause_fraction 0.01, voiced_fraction −0.02 |
| 4 | `head -1 tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv \| cut -d, -f12-30` | Same 19 names in the same order (DME-002) |

### TC-040-10 Operational values and review explanations

| Step | Action | Expected Result |
|---|---|---|
| 1 | `from analytics.config import PRODUCTION; print(C.operational == PRODUCTION.operational, C.operational)` | `True`; `data_alert_set_aside_fraction=0.2`, `data_alert_device_silent_days=2`, `data_alert_baseline_stalled_enabled=True`, `alert_snooze_hours=24` |
| 2 | `print([e.code for e in C.operational.review_explanations])` | `['cold_cough_sore_throat', 'dental_dentures', 'medication_change', 'poor_sleep_unusual_day', 'room_device_moved']` |
| 3 | `GET /api/v1/config/ui` as clinician | `alert_snooze_hours` = 24; `review_explanations` codes as in step 2 with labels "Cold, cough or sore throat", "Dental problem or dentures out", "New or changed medication", "Poor sleep or unusual day", "Room or device moved" |

### TC-040-11 Exceptions and warning codes

| Step | Action | Expected Result |
|---|---|---|
| 1 | `from analytics.config import AnalyticsError, ContractError, ConfigError; print(issubclass(ContractError, AnalyticsError), issubclass(ConfigError, AnalyticsError), AnalyticsError.__bases__)` | `True True (<class 'Exception'>,)` |
| 2 | `from analytics.config import ENGINE_WARNING_CODES, RUNNER_WARNING_CODES, FAILURE_CODES; print(ENGINE_WARNING_CODES, RUNNER_WARNING_CODES, FAILURE_CODES)` | `('after_as_of', 'late_arrival', 'zero_spread', 'baseline_mismatch', 'config_default_used', 'config_mismatch', 'no_device_assignment', 'alert_first_crossing_changed', 'device_assignment_mismatch')`, `('exception', 'run_abandoned')`, `('config_changed_requires_rebuild', 'pipeline_config_invalid')` — all lower-case |
| 3 | `import analytics; print(analytics.ENGINE_VERSION)` | `0.1.0` |

### TC-040-12 set-config refuses an invalid value

| Step | Action | Expected Result |
|---|---|---|
| 1 | `python -m backend.cli set-config --profile test_v0_1 --key cusum_h --value 0 --reason "QA invalid value check"; echo "exit=$?"` | Prints "Refused: cusum_h: value 0.0 is out of range"; `exit=2` |
| 2 | `SELECT value FROM config_parameters WHERE profile='test_v0_1' AND key='cusum_h';` | `5.0` (unchanged) |
| 3 | `SELECT count(*) FROM audit_logs WHERE action='config.changed' AND entity_id='test_v0_1.cusum_h';` | 0 (no audit for a refused change) |
| 4 | `python -m backend.cli set-config --profile test_v0_1 --key foo --value 1 --reason "QA"; echo "exit=$?"` | Prints "Refused: unknown key foo for profile test_v0_1"; `exit=2` |
| 5 | `python -m backend.cli set-config --profile test_v0_1 --key alert_snooze_hours --value 48 --reason "QA valid change"` then restore with `--value 24` | Exit 0 each; "test_v0_1.alert_snooze_hours updated."; no "Algorithm key changed" line (operational key); two `config.changed` audit rows with `details.old` / `details.new` |

### TC-040-13 Missing key and FACILITY_TZ mismatch

| Step | Action | Expected Result |
|---|---|---|
| 1 | As the migrator role: `DELETE FROM config_parameters WHERE profile='test_v0_1' AND key='alert_snooze_hours';` (deliberate write, restored by reseed) | 1 row deleted |
| 2 | `python -m backend.cli run-pipeline --scope all --profile test_v0_1 --as-of 2026-10-30T15:00:00-05:00` | Exit 0 |
| 3 | `SELECT status, warnings FROM pipeline_runs ORDER BY started_at DESC LIMIT 1;` | `succeeded`; `warnings` contains `{"code": "config_default_used", "resident_code": null, "session_id": null, "detail": "alert_snooze_hours: built-in value used"}` |
| 4 | Reseed (`seed test_v0_1 --reset`); set `FACILITY_TZ=America/New_York` in the environment and repeat step 2 | Exit 0 |
| 5 | Latest run's `warnings` | Contains `config_mismatch` with detail "FACILITY_TZ America/New_York differs from the profile's America/Chicago"; local dates of processed sessions unchanged (`SELECT local_time FROM processed_sessions WHERE session_id='R09-20261021-01'` = `14:07:50`) |
| 6 | Restore `FACILITY_TZ=America/Chicago` | — |

### TC-040-14 Profile with no rows

| Step | Action | Expected Result |
|---|---|---|
| 1 | As the migrator role: `DELETE FROM config_parameters WHERE profile='test_v0_1';` (deliberate write) | 23 rows deleted |
| 2 | `python -m backend.cli run-pipeline --scope all --profile test_v0_1 --as-of 2026-10-30T15:00:00-05:00; echo "exit=$?"` | `exit=1` (failed run) |
| 3 | `SELECT status, warnings, error_message FROM pipeline_runs ORDER BY started_at DESC LIMIT 1;` | `failed`; `warnings` contains code `pipeline_config_invalid`; `error_message` starts with "invalid configuration:" |
| 4 | `GET /api/v1/health` | HTTP 200 (ENV-021) |
| 5 | Reseed with `python -m backend.cli seed test_v0_1 --reset` | 46 rows back |

### TC-040-15 No parameters from environment variables in analytics/

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -rn -E "os\.environ\|getenv\|dotenv" analytics/` | No match |
| 2 | Start a Python shell with `CUSUM_H=1.0 BASELINE_N=3` exported and print `TEST_V0_1.cusum_h, TEST_V0_1.baseline_n` | `5.0 16` (environment ignored) |
| 3 | `grep -rn -E "= *-40\.0\|= *1\.4826\|= *5\.0\b" analytics/*.py \| grep -v config.py` | No threshold literal outside `analytics/config.py` (AGT-020) |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents` (any role) with `PIPELINE_PROFILE=test_v0_1` | `meta.baseline_n` 16, `meta.cusum_h` 5.0, `meta.pipeline_profile` "test_v0_1" (values from the loaded profile, API-057) |
| 2 | `GET /api/v1/config/ui` | Operational values of TC-040-10 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `config_parameters` row count per profile | 23 each (TC-040-04) |
| 2 | Values differing between profiles | Only `baseline_n` (30 / 16) |
| 3 | `pipeline_runs.config_snapshot` of the seed run | 23 keys plus `config_hash` and `as_of` |
| 4 | `pipeline_runs.warnings` after the loader cases | `config_default_used`, `config_mismatch`, `pipeline_config_invalid` as in TC-040-13/14 |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | `robust([])`, `robust([nan])` | `ContractError` (TC-040-03) |
| 2 | `from_mapping` with `cusum_h=0`, `foo`, incomplete `morning_offsets`, unknown time zone, wrong type | `ConfigError` naming the key (TC-040-05) |
| 3 | Assign to a contract field; 18 feature keys | `FrozenInstanceError`; `ContractError` (TC-040-08) |
| 4 | `set-config` with an invalid value or unknown key | "Refused: …", exit 2, no change, no audit (TC-040-12) |
| 5 | Empty profile | Run `failed` with `pipeline_config_invalid` (TC-040-14) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-040-AC-01 | The three `robust` vectors return (2.5, 1.0, 1.4826, false), (1.0, 0.0, 0.5, true), (1.0, 0.5, 0.7413, false) | TC-040-01 |
| FEAT-040-AC-02 | ROB-03 returns median −29.925, MAD 2.165, spread 3.209829 (±1e-6) | TC-040-02 |
| FEAT-040-AC-03 | Seeded `test_v0_1` loads equal to `TEST_V0_1` (baseline_n 16); `production` gives baseline_n 30, every other value equal | TC-040-04 |
| FEAT-040-AC-04 | `cusum_h = 0`, unknown key `foo`, `morning_offsets` missing `mfcc4` each raise `ConfigError` naming the key | TC-040-05, TC-040-12 |
| FEAT-040-AC-05 | Hash unchanged when only `alert_snooze_hours` changes, changed when `cusum_h` changes; snapshot survives JSON round-trip | TC-040-06 |
| FEAT-040-AC-06 | Import-linter fails on forbidden imports in `analytics/` and passes on delivered code | TC-040-07 |
| FEAT-040-AC-07 | Assigning to a contract field raises `FrozenInstanceError`; `RawRecord` with 18 feature keys raises `ContractError` | TC-040-08 |

## Test Data Requirements

- SRC-05 `tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv` (R01 days 1–16) and SRC-03 `tests/fixtures/answer_key/EchoWell_pipeline_test_v0_1.xlsx` (`Exp_baselines`, `Parameters`).
- Seeded `config_parameters` (46 rows); `PIPELINE_PROFILE=test_v0_1`, `FACILITY_TZ=America/Chicago`, `DATABASE_MIGRATION_URL`.
- Test helpers `tests/unit/analytics/factory.py` (`rec`) and `tests/unit/analytics/src05.py` (`records`).

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-040-FR-01 | FEAT-040 | TC-040-08 |
| FEAT-040-FR-02 | FEAT-040 | TC-040-08 |
| FEAT-040-FR-03 | FEAT-040 | TC-040-09 |
| FEAT-040-FR-04 | FEAT-040 | TC-040-04, TC-040-10 |
| FEAT-040-FR-05 | FEAT-040 | TC-040-05, TC-040-12 |
| FEAT-040-FR-06 | FEAT-040 | TC-040-06 |
| FEAT-040-FR-07 | FEAT-040 | TC-040-13, TC-040-14 |
| FEAT-040-FR-08 | FEAT-040 | TC-040-15 |
| FEAT-040-FR-09 | FEAT-040 | TC-040-09 |
| FEAT-040-FR-10 | FEAT-040 | TC-040-11 |
| FEAT-040-FR-11 | FEAT-040 | TC-040-01, TC-040-02, TC-040-03 |
| FEAT-040-FR-12 | FEAT-040 | TC-040-07, TC-040-15 |
| TRD 07 ANL-008..ANL-013 | FEAT-040 | TC-040-08, TC-040-09, TC-040-11 |
| TRD 07 ANL-028..ANL-031 | FEAT-040 | TC-040-04, TC-040-05, TC-040-06, TC-040-13, TC-040-14 |
| TRD 07 ANL-051, ANL-052 | FEAT-040 | TC-040-11 |
| TRD 08 BSC-001..BSC-005, AC-BSC-01 | FEAT-040 | TC-040-01, TC-040-02, TC-040-03 |
| TRD 21 ENV-020, ENV-021, ENV-022 | FEAT-040 | TC-040-15, TC-040-14, TC-040-13 |
| TRD 23 DME-002 | FEAT-040 | TC-040-09 |
| TRD 13 ROB-01..ROB-06 | FEAT-040 | TC-040-01, TC-040-02 |
| TRD 13 CFG-01..CFG-05 | FEAT-040 | TC-040-04, TC-040-05, TC-040-06, TC-040-10 |
| TRD 13 TST-021 | FEAT-040 | TC-040-07 |
| FR-073, FR-229 | FEAT-040 | TC-040-09, TC-040-12 |
