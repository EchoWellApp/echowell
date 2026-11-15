# Morning offset estimation from data

## Feature Description

Status: Not Started — these test cases are written from the feature file and run only once the feature is built (BACKLOG.md §10).

FEAT-094 replaces the configured placeholder morning offsets with values estimated from a larger dataset once a method is agreed (gate OQ-09; DS-04 delivered by Team 1). The extension point is fixed: a separate pure function `analytics/morning_offset.py::estimate_offsets(rows, config) -> Mapping[str, float]`, evaluated offline on DS-04, never called by `run_pipeline`; its output (exactly the 19 feature keys, valid for `PipelineConfig.from_mapping`) reaches the pipeline only through `set-config --profile production --key morning_offsets` followed by `rebuild --profile production --confirm REBUILD`. The adjustment rule (morning = local hour < 12 after `zoneinfo` conversion; adjusted = raw − offset for morning records; baselines and scores use adjusted values; the speaker screen uses raw values) and the `test_v0_1` offsets (SRC-03) do not change. The estimation statistic and its thresholds come only from the OQ-09 decision; method-specific expected values are added when OQ-09 closes.

Configuration changes are rehearsed on a local database; on hosted production they are made only by the operator after the gate opens, and the test cases then inspect the audit rows (TRD 24 D-170).

## Preconditions

- Repository at the commit under test; Python 3.12 with backend requirements; local Compose stack seeded with `test_v0_1` for the configuration cases.
- OQ-09 answered in TRD 24 and TRD 07/TRD 08 updated with the method (for TC-094-05 and TC-094-09).
- DS-04 records available for the offline evaluation (synthetic).

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-094-01 | `run_pipeline` never calls `estimate_offsets` | High | Documentation |
| TC-094-02 | `estimate_offsets` returns exactly the 19 feature keys accepted by `PipelineConfig.from_mapping` | High | Analytics |
| TC-094-03 | `estimate_offsets` is pure: same input twice gives equal mappings; no file, database, clock or random access | High | Analytics |
| TC-094-04 | MO-01..MO-07 and the R01–R10 validation pass unchanged | High | Analytics |
| TC-094-05 | The method is the one recorded for OQ-09; no invented method | High | Documentation |
| TC-094-06 | A mapping with missing or extra keys is refused by `set-config` with exit 2 and no change | High | Negative |
| TC-094-07 | Production change of `morning_offsets` writes one `config.changed` and is followed by `pipeline.rebuild` | High | Database |
| TC-094-08 | Before the rebuild an ingest-triggered run fails with `config_changed_requires_rebuild` | High | Negative |
| TC-094-09 | Offline evaluation report on DS-04 lists proposed offsets per feature, dataset version and `code_version` | Medium | Documentation |
| TC-094-10 | `test_v0_1` morning offsets stay at the SRC-03 values | High | Database |
| TC-094-11 | The adjustment rule is unchanged after a new offset set is applied | High | Analytics |

### TC-094-01 `run_pipeline` never calls `estimate_offsets`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -n "estimate_offsets" analytics/pipeline.py; echo "exit=$?"` | No output; `exit=1` |
| 2 | `grep -rn "estimate_offsets" analytics backend` | Only the definition in `analytics/morning_offset.py` (and no call from `backend/` request paths) |

### TC-094-02 `estimate_offsets` returns exactly the 19 feature keys accepted by `PipelineConfig.from_mapping`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/unit/analytics/test_morning_offset.py -q` | All tests pass, including the new estimator tests |
| 2 | In a Python shell: call `estimate_offsets(rows, config)` on a small synthetic `rows` set prepared per the OQ-09 method; compare `set(result)` with `analytics.config.FEATURE_KEYS` | Equal sets of 19 keys (`loudness_dbfs` … `mfcc4`) |
| 3 | Merge the result into the production mapping and call `PipelineConfig.from_mapping(...)` | No `ConfigError` |

### TC-094-03 `estimate_offsets` is pure: same input twice gives equal mappings; no file, database, clock or random access

| Step | Action | Expected Result |
|---|---|---|
| 1 | Call `estimate_offsets(rows, config)` twice with the same arguments | The two mappings are equal (`==`), float64 values, no rounding |
| 2 | `grep -nE "import (random\|requests\|httpx\|sqlalchemy\|psycopg)\|datetime\.now\|time\.time\|open\(" analytics/morning_offset.py; echo "exit=$?"` | No output; `exit=1` |
| 3 | CI job `backend-lint` (import-linter contracts for `analytics/`) | `success` |

### TC-094-04 MO-01..MO-07 and the R01–R10 validation pass unchanged

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/unit/analytics/test_morning_offset.py -q -k "local_time_vectors or r06_day_1_adjustment or afternoon_and_stored_features_unchanged"` | MO-01..MO-07 tests pass |
| 2 | `git diff <feature base>..<feature head> -- tests/unit/analytics/test_morning_offset.py` | Existing MO-01..MO-07 tests unchanged (only additions) |
| 3 | `pytest tests/validation -q` | All pass; VC-R06 (morning adjustment) unchanged |

### TC-094-05 The method is the one recorded for OQ-09; no invented method

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read OQ-09 in TRD 24 | Status closed with a decided method (statistic, minimum morning and afternoon sessions, pooling) |
| 2 | Read TRD 07 ANL-055 and TRD 08 BSC-020..BSC-024 at the feature commit | Updated with that method before the code merge |
| 3 | Read `estimate_offsets` | Implements exactly the recorded method; handling of insufficient data follows the decision |
| 4 | Before OQ-09 closes: `grep -n "def estimate_offsets" analytics/morning_offset.py; echo "exit=$?"` | No output (`exit=1`): the function is not implemented with an invented method |

### TC-094-06 A mapping with missing or extra keys is refused by `set-config` with exit 2 and no change

| Step | Action | Expected Result |
|---|---|---|
| 1 | Local: `docker compose exec backend python -m backend.cli set-config --profile production --key morning_offsets --value '{"loudness_dbfs": -1.5}' --reason "TC-094-06"; echo "exit=$?"` | `exit=2`; message names `morning_offsets` |
| 2 | Same with the 19 keys plus `"extra_key": 0` | `exit=2` |
| 3 | `SELECT value FROM config_parameters WHERE profile = 'production' AND key = 'morning_offsets';` | Unchanged |
| 4 | `SELECT count(*) FROM audit_logs WHERE action = 'config.changed' AND occurred_at > now() - interval '5 minutes';` | `0` |

### TC-094-07 Production change of `morning_offsets` writes one `config.changed` and is followed by `pipeline.rebuild`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Local: `set-config --profile production --key morning_offsets --value '<19-key JSON from the report>' --reason "MORNING_OFFSET_REPORT.md <version>"` | Exit 0 |
| 2 | `rebuild --profile production --confirm REBUILD` | Exit 0 |
| 3 | `SELECT action FROM audit_logs WHERE action IN ('config.changed','pipeline.rebuild') ORDER BY occurred_at DESC LIMIT 2;` | `pipeline.rebuild` (newest) preceded by exactly one `config.changed` for `morning_offsets` with old and new value and the report as reason |
| 4 | `SELECT config_snapshot->'morning_offsets' FROM pipeline_runs ORDER BY started_at DESC LIMIT 1;` | Shows the new offsets; the config hash differs from the previous run |
| 5 | Hosted production (read-only, after the operator's approved change) | Same audit pattern |

### TC-094-08 Before the rebuild an ingest-triggered run fails with `config_changed_requires_rebuild`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Local: run `set-config` for `morning_offsets` (valid 19-key JSON); do not run `rebuild` | Exit 0 |
| 2 | POST one valid record for a production-profile resident to `/api/v1/sessions` | 201; the triggered run fails |
| 3 | `SELECT status, error_message FROM pipeline_runs ORDER BY started_at DESC LIMIT 1;` | `failed`; "configuration changed; run the rebuild command"; warning `config_changed_requires_rebuild` |

### TC-094-09 Offline evaluation report on DS-04 lists proposed offsets per feature, dataset version and `code_version`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open the estimation report under `docs/reports/` (e.g. `MORNING_OFFSET_REPORT.md`) | 19 rows (one per feature) with the proposed offset, plus DS-04 dataset version and `code_version` |
| 2 | Check that the evaluation used DS-04 offline | No DS-04 data in staging or production (`SELECT count(*) FROM residents WHERE resident_code IN (<DS-04 codes>)` = 0) |
| 3 | Check review | Report reviewed by the algorithm lead before any `set-config` |

### TC-094-10 `test_v0_1` morning offsets stay at the SRC-03 values

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT value FROM config_parameters WHERE profile = 'test_v0_1' AND key = 'morning_offsets';` | `loudness_dbfs` −1.5, `total_phrase_duration_s` 0.10, `speech_rate_syl_per_s` −0.12, `articulation_rate_syl_per_s` −0.10, `pause_fraction` 0.010, `voiced_fraction` −0.020, all other 13 keys 0 |
| 2 | Repeat after TC-094-07 | Unchanged |

### TC-094-11 The adjustment rule is unchanged after a new offset set is applied

| Step | Action | Expected Result |
|---|---|---|
| 1 | After TC-094-07, take one morning record (local hour < 12, `America/Chicago`) and one afternoon record: `SELECT is_morning, adjusted_features->>'loudness_dbfs' FROM processed_sessions p JOIN raw_sessions r ON p.raw_session_id = r.id WHERE r.session_id IN ('<morning id>','<afternoon id>');` | Morning: adjusted = raw − new offset; afternoon: adjusted = raw |
| 2 | A record at local 12:00 exactly | `is_morning` false |
| 3 | Speaker screen inputs for the morning record (`screen_detail`) | Computed from raw values, not adjusted |

## API Validation

Not applicable: FEAT-094 adds and changes no endpoint (API Impact "None"); the effect is visible only in `pipeline_runs.config_snapshot` and the recomputed baselines and scores (Database Validation).

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `config_parameters` production `morning_offsets` after the change (TC-094-07) | 19 keys, new values |
| 2 | `config_parameters` `test_v0_1` `morning_offsets` (TC-094-10) | SRC-03 values unchanged |
| 3 | Audit rows `config.changed` then `pipeline.rebuild` (TC-094-07) | Present in that order |
| 4 | Failed run before rebuild (TC-094-08) | `failed`, `config_changed_requires_rebuild` |
| 5 | `adjusted_features` of morning vs afternoon records (TC-094-11) | Rule unchanged |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | `set-config` with 1 key or 20 keys (TC-094-06) | Exit 2, no change |
| 2 | Run after `set-config` without `rebuild` (TC-094-08) | Run fails with `config_changed_requires_rebuild` |
| 3 | `estimate_offsets` referenced in `analytics/pipeline.py` (TC-094-01) | No reference |
| 4 | Non-deterministic or impure estimator (TC-094-03) | Equal outputs; no forbidden import |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-094-AC-01 | `grep -n "estimate_offsets" analytics/pipeline.py` returns nothing | TC-094-01 |
| FEAT-094-AC-02 | `estimate_offsets` returns exactly the 19 feature keys accepted by `PipelineConfig.from_mapping`; two calls with the same input are equal | TC-094-02, TC-094-03 |
| FEAT-094-AC-03 | MO-01..MO-07 and `pytest tests/validation -q` pass unchanged | TC-094-04, TC-094-10 |
| FEAT-094-AC-04 | A production change of `morning_offsets` has one `config.changed` row, followed by `pipeline.rebuild`; before the rebuild an ingest-triggered run fails with `config_changed_requires_rebuild` | TC-094-07, TC-094-08, TC-094-06 |

## Test Data Requirements

- `test_v0_1` seed (R01–R10; R06 morning cases of VC-R06) for regression.
- DS-04 records (synthetic) for the offline evaluation, never loaded into staging or production.
- A valid 19-key `morning_offsets` JSON from the estimation report; invalid 1-key and 20-key JSON for the negative case.
- Local production-profile records (e.g. SRC-05 loaded under profile `production`) for the rehearsal of `set-config` / `rebuild`.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| ANL-055, FR-073, AGT-021 | FEAT-094 | TC-094-01, TC-094-03 |
| ANL-029 | FEAT-094 | TC-094-02, TC-094-06 |
| OQ-09, AGT-009 | FEAT-094 | TC-094-05 |
| TDV-093, D-02 | FEAT-094 | TC-094-09 |
| ANL-032, D-56, D-69 | FEAT-094 | TC-094-07, TC-094-08 |
| BSC-020..BSC-023, FR-074 | FEAT-094 | TC-094-11 |
| AGT-008, TDV-003 | FEAT-094 | TC-094-04, TC-094-10 |
| ARC-041 | FEAT-094 | TC-094-03 |
| FEAT-094-FR-01..FEAT-094-FR-08 | FEAT-094 | TC-094-01..TC-094-11 |
