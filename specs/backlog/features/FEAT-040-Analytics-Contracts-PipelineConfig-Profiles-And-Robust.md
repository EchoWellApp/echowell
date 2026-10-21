# FEAT-040 Analytics contracts, PipelineConfig profiles and robust statistics

| Field | Value |
|---|---|
| Epic | Analytics Engine |
| Build phase | Phase 6 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-002, FEAT-009 |
| Status | Not Started |

## Purpose

Lay the foundation every analytics stage builds on: the frozen data contracts passed between stages, the canonical feature list with composite signs, the `PipelineConfig` with its two built-in profiles (`production` with baseline_n 30 and `test_v0_1` with 16), validation of configuration values, a reproducible config snapshot and hash, loading of the active profile from `config_parameters`, the two analytics exception types and the run-warning codes, and the robust statistics (median, MAD, spread with floors) that baselines and the speaker screen use. Getting these exactly right is what makes the R01–R10 answer key reproducible to 1e-6.

## Business Context

- BR-09, BR-10, BR-11 (deterministic, configurable baseline, score and alarm): parameters come only from configuration, never hard-coded.
- BR-07 (morning adjustment): morning offsets are configured, not estimated (FR-073).
- BR-15 (reproduce the answer key): even-count medians and spread floors match SRC-03 Exp_baselines exactly.
- BR-16 (controlled configuration changes): `from_mapping` validation is what `set-config` uses to refuse invalid values (FR-229).
- FRs covered (BACKLOG.md): FR-073, FR-229.

## Referenced TRDs

- TRD 07 ANL-008..ANL-013 (module signatures, exports, frozen contracts, contract types, 19 canonical keys), ANL-028..ANL-031 (profiles, validation, snapshot and hash, profile loading), ANL-051, ANL-052 (exceptions, warning codes), §4.3 (contracts), §4.4 (helper types), §4.7 (`PipelineConfig` and `OperationalConfig` fields).
- TRD 08 BSC-001..BSC-005 (robust statistics), §4.1 (signs, offsets, floors), §4.2 unit vectors.
- TRD 21 ENV-020 (parameters never from env vars), ENV-021 (profile rows required; defaults), ENV-022 (`config_mismatch`).
- TRD 23 DME-002 (`FEATURE_KEYS`, `COMPOSITE_KEYS`, `COMPOSITE_SIGNS` defined once).
- TRD 20 §4.11 (23 seeded keys per profile), PGS-024, PGS-025.
- TRD 01 ARC-053 (parameters only through `PipelineConfig`).
- TRD 13 Table 4.3-A ROB-01..ROB-06, CFG-01..CFG-05; TST-011, TST-021, TST-022; TRD 08 AC-BSC-01.
- TRD 25 AGT-020, AGT-041, AGT-042; TRD 24 D-14, D-56.

## Scope

- `analytics/__init__.py` exports (`run_pipeline` is added by FEAT-052), `ENGINE_VERSION = "0.1.0"`.
- `analytics/config.py`: frozen `slots=True` dataclasses `RawRecord`, `ScreenedRecord`, `EpochedRecord`, `AdjustedRecord`, `Baseline`, `ScoreRow`, `AlertEvent`, `LedgerDay`, `PipelineResult`, `FeatureSpec`, `RobustStats`, `ResidentInfo`, `DeviceAssignment`, `BaselineMembership`, `EpochSummary`, `RunWarning`, `DataAlert`, `AnalyticsSummary`, `ReviewExplanation`, `OperationalConfig`, `PipelineConfig`; type alias `EpochKey`; `FEATURE_KEYS`, `COMPOSITE_KEYS`, `COMPOSITE_SIGNS`, `FEATURES`; constants `PRODUCTION`, `TEST_V0_1`; `PipelineConfig.from_mapping`, `snapshot()`, `config_hash()`; exceptions `AnalyticsError`, `ContractError`, `ConfigError`; the warning-code constants of ANL-052.
- `analytics/robust_stats.py::robust(values, floor, mad_scale) -> RobustStats`.
- Backend profile loader in `backend/services/config_service.py` that reads the `config_parameters` rows of `PIPELINE_PROFILE` into a `PipelineConfig` (with default fallback and warnings).
- Unit tests `tests/unit/analytics/test_config.py`, `tests/unit/analytics/test_robust_stats.py`.

## Out of Scope

- Any stage function (FEAT-041..FEAT-051) and the orchestrator (FEAT-052).
- The `set-config` and `rebuild` CLI commands (FEAT-055) and the rebuild-required rule at run time (ANL-032, FEAT-053/FEAT-055); this feature provides the validation and hash they use.
- The `config_parameters` table and seed migration (FEAT-009).
- Morning-offset estimation (OQ-09, future FEAT-094).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-040-FR-01 | All data contracts of TRD 07 §4.3 and §4.4 shall be `@dataclass(frozen=True, slots=True)` classes with full type hints defined in `analytics/config.py`, with exactly the fields listed there. | ANL-010, ANL-011 |
| FEAT-040-FR-02 | Feature mappings inside contracts shall always contain the 19 canonical keys in contract §6 order (loudness_dbfs … mfcc4); any other key set raises `ContractError`. | ANL-013, DME-002 |
| FEAT-040-FR-03 | `FEATURE_KEYS` (19 keys in order), `COMPOSITE_KEYS` (first 7) and `COMPOSITE_SIGNS` {loudness_dbfs −1, total_phrase_duration_s +1, speech_rate_syl_per_s −1, articulation_rate_syl_per_s −1, number_of_pauses +1, pause_fraction +1, voiced_fraction −1} shall be defined once; `FEATURES` holds a `FeatureSpec(key, unit, sign, morning_offset, in_composite, spread_floor)` per feature (spread floor 0.5 for number_of_pauses, else 0.0). | DME-002; TRD 07 §4.4; TRD 08 §4.1 |
| FEAT-040-FR-04 | `PRODUCTION` and `TEST_V0_1` shall be `PipelineConfig` constants with exactly the TRD 07 §4.7 values (equal except `profile` and `baseline_n` 30 / 16), including `OperationalConfig` (data_alert_set_aside_fraction 0.20, data_alert_device_silent_days 2, data_alert_baseline_stalled_enabled true, alert_snooze_hours 24, the 5 review explanations); these values equal the TRD 20 §4.11 seed. | ANL-028, PGS-024, PGS-025 |
| FEAT-040-FR-05 | `PipelineConfig.from_mapping(values)` shall validate: `baseline_n` ≥ `screen_min_n` ≥ 1; `mad_scale` > 0; floors ≥ 0; `cusum_k` ≥ 0; `cusum_h` > 0; 0 ≤ `morning_cutoff_hour` ≤ 24; `facility_tz` resolvable by `zoneinfo`; `morning_offsets` keys equal the 19 feature keys; `data_alert_set_aside_fraction` in (0, 1]; `data_alert_device_silent_days` ≥ 1; `alert_snooze_hours` in 1..168; `review_explanations` 1–20 entries with unique lower-case codes; any failure, unknown key or wrong type raises `ConfigError` naming the key. | ANL-029; FR-229 |
| FEAT-040-FR-06 | `snapshot()` shall return a JSON-serialisable dict of all fields (algorithm and operational keys); `config_hash()` shall return the SHA-256 hex digest of `json.dumps(s, sort_keys=True, separators=(",", ":"))` over the snapshot restricted to the algorithm keys (every field except `operational`). | ANL-030, D-56 |
| FEAT-040-FR-07 | The backend loader shall read the rows of the profile named by `PIPELINE_PROFILE` from `config_parameters` into a `PipelineConfig` via `from_mapping`; a missing key uses the built-in constant's value and records warning `config_default_used`; a profile with no rows or an invalid value makes every run end `failed` with warning `pipeline_config_invalid`; if `FACILITY_TZ` differs from the profile's `facility_tz`, warning `config_mismatch` is recorded and the profile value is used. | ANL-031, ENV-021, ENV-022 |
| FEAT-040-FR-08 | Algorithm, data-alert and review parameters shall never be read from environment variables; stage functions receive them only through `PipelineConfig`. | ENV-020, ARC-053, AGT-020 |
| FEAT-040-FR-09 | Morning offsets shall be read only from `PipelineConfig.morning_offsets`; no estimation runs in v0.1. | FR-073, D-02; TRD 07 ANL-055 |
| FEAT-040-FR-10 | `analytics/` shall define exactly `AnalyticsError(Exception)` with subclasses `ContractError` and `ConfigError`, and `RunWarning` codes exactly as ANL-052 lists (`after_as_of`, `late_arrival`, `zero_spread`, `baseline_mismatch`, `config_default_used`, `config_mismatch`, `no_device_assignment`, `alert_first_crossing_changed`, `device_assignment_mismatch`; runner codes `exception`, `run_abandoned`; failure codes `config_changed_requires_rebuild`, `pipeline_config_invalid`), all lower-case. | ANL-051, ANL-052 |
| FEAT-040-FR-11 | `robust(values, floor, mad_scale)` shall compute `median = numpy.median(float64 array)` (even count: mean of the two middle values), `mad = numpy.median(abs(a − median))`, `spread = max(mad × mad_scale, floor)`, `floor_applied = spread > mad × mad_scale` (strict), and raise `ContractError` for an empty input or a non-finite value. | BSC-001..BSC-005, AGT-041, AGT-042 |
| FEAT-040-FR-12 | Every module of `analytics/` shall be pure (no I/O, clock, randomness or argument mutation) and import only the standard library and numpy; no `sqlalchemy`, `psycopg`, `fastapi`, `httpx`, `requests`, environment readers or `backend.*`. | ANL-002, ANL-003, ANL-005; D-14, D-20 |

## Inputs

- `config_parameters` rows (23 keys per profile, TRD 20 §4.11) and env `PIPELINE_PROFILE`, `FACILITY_TZ`.
- Arrays of float values for `robust()`.

## Outputs

- Importable contracts, constants and functions in `analytics/`; a `PipelineConfig` instance for the active profile; `RunWarning` records for default/mismatch conditions.

## Data Flow

1. Backend: `config_service` selects `key, value` for `PIPELINE_PROFILE`, builds a mapping, fills missing keys from the built-in constant (recording `config_default_used`) and calls `PipelineConfig.from_mapping` (raising `ConfigError` → run fails with `pipeline_config_invalid`).
2. The resulting config is passed to every stage and its `snapshot()` plus `config_hash()` are stored by the runner in `pipeline_runs.config_snapshot` (FEAT-053).
3. Stages call `robust()` with the feature's floor and `config.mad_scale`.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-002, FEAT-009

- FEAT-002 (Monorepo skeleton): `analytics/` package location, pinned numpy 2.x, pytest configuration.
- FEAT-009 (Master data, identity and configuration tables): `config_parameters` with the 46 seeded rows the loader reads.

Features that build directly on this one (BACKLOG.md §4): FEAT-041, FEAT-043.

## Database Impact

- Tables read: `config_parameters` (`profile`, `key`, `value`).
- Tables created or modified: none.

## API Impact

None directly. `GET /api/v1/config/ui` (FEAT-030) reads the same operational keys; `meta.baseline_n` and `meta.cusum_h` come from the loaded profile (API-057).

## Frontend Impact

None.

## Analytics Impact

- Algorithms: median (numpy, even-count mean of middle values), MAD, robust spread = max(MAD × 1.4826, floor) with floors 0.5 (number_of_pauses), 0.1 (composite), 0 otherwise; `floor_applied` strict comparison.
- Calculations: SHA-256 config hash over the canonical JSON of algorithm keys.
- Module: `analytics/config.py`, `analytics/robust_stats.py`.

## Security Requirements

None beyond purity: no secrets or environment access in `analytics/` (ANL-002); configuration changes are audited by the CLI (FEAT-055).

## Error Handling

- Invalid configuration → `ConfigError` naming the key; the runner records `pipeline_config_invalid` and fails the run; `GET /health` stays 200 (ENV-021).
- Contract violations (wrong key set, empty input to `robust`) → `ContractError`; normal data conditions never raise (ANL-019).

## Logging Requirements

None in `analytics/` (LOG-006, ANL-053). The backend logs `config_mismatch` at WARNING at startup (ENV-022) and records `config_default_used` as a run warning.

## Testing Requirements

- Unit (`tests/unit/analytics/test_robust_stats.py`, marker `unit`): ROB-01..ROB-06; the three TRD 08 §4.2 vectors (AC-BSC-01); empty input and NaN raise `ContractError`; Hypothesis property `robust_spread ≥ floor` (TST-022).
- Unit (`tests/unit/analytics/test_config.py`): CFG-01 (test_v0_1 equals TRD 14 Table 4.5-E), CFG-02 (production baseline_n 30), CFG-03 (`ConfigError` naming the key for unknown key or wrong type), CFG-04 (snapshot JSON round-trip), CFG-05 (operational values both profiles); hash unchanged when `alert_snooze_hours` changes and changed when `cusum_h` changes (ANL-030); `FEATURE_KEYS` equals SRC-05 header columns 12–30 (DME-002); contracts are frozen (assignment raises).
- Unit (`tests/unit/backend/services/test_config_service.py`): missing key → default plus `config_default_used`; empty profile → `pipeline_config_invalid`; `FACILITY_TZ` mismatch → `config_mismatch`.
- Import-linter contract that `analytics/` imports no database, HTTP or backend module (TST-021, AC-ANL-04).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-040-AC-01 | `robust([1,2,3,4], 0, 1.4826)` returns median 2.5, MAD 1.0, spread 1.4826, floor_applied false; `robust([1,1,1,1,2,2], 0.5, 1.4826)` returns 1.0, 0.0, 0.5, true; `robust([0,0,1,1,1,1,1,1,1,1,2,2,2,2,2,2], 0.5, 1.4826)` returns 1.0, 0.5, 0.7413, false. Verified by: Unit (`tests/unit/analytics/test_robust_stats.py`). | AC-BSC-01, BSC-001..BSC-004 |
| FEAT-040-AC-02 | ROB-03 (R01 loudness days 1–16) returns median −29.925, MAD 2.165, spread 3.209829 (±1e-6). | ROB-03, AGT-041 |
| FEAT-040-AC-03 | Loading `test_v0_1` from the seeded `config_parameters` yields a config equal to `TEST_V0_1` (baseline_n 16) and `production` yields baseline_n 30 with every other value equal. | CFG-01, CFG-02, ANL-028 |
| FEAT-040-AC-04 | `from_mapping` with `cusum_h = 0`, with an unknown key `foo`, or with `morning_offsets` missing `mfcc4` raises `ConfigError` whose message names the key. | CFG-03, ANL-029 |
| FEAT-040-AC-05 | `config_hash()` is unchanged when only `alert_snooze_hours` changes and changes when `cusum_h` changes; `snapshot()` survives `json.loads(json.dumps(...))` unchanged. | ANL-030, CFG-04 |
| FEAT-040-AC-06 | An import-linter check fails if any `analytics/` module imports `sqlalchemy`, `psycopg`, `fastapi`, `httpx`, `requests` or `backend`, and passes on the delivered code. Verified by: Test (TST-021). | ANL-002, AC-ANL-04 |
| FEAT-040-AC-07 | Assigning to any field of a contract instance raises `dataclasses.FrozenInstanceError`, and a `RawRecord` with 18 feature keys raises `ContractError`. Verified by: Unit (`tests/unit/analytics/test_robust_stats.py`). | ANL-010, ANL-013 |

## Definition of Done

- All FEAT-040 acceptance criteria pass.
- `analytics/config.py`, `analytics/robust_stats.py` and the backend loader implemented; unit tests ROB-01..ROB-06 and CFG-01..CFG-05 pass (TST-020).
- `tests/unit/analytics/test_config.py` and `test_robust_stats.py` exist (TST-011); `analytics/` coverage contribution keeps the 95 % gate reachable (TST-140).
- No threshold, floor or offset literal appears in any other analytics module (AGT-020, inspection).

## Implementation Notes

- Use `numpy.median(np.asarray(values, dtype=np.float64))`; never `statistics.median_low/high` (AGT-041). `number_of_pauses` is cast to float64 for all arithmetic.
- Keep `PRODUCTION` and `TEST_V0_1` as the single source of default values; the seed migration values must equal them (a test compares the seeded rows with the constants).
- The 23 `config_parameters` keys include the ingest keys `supported_schema_versions` and `feature_name_map`, which are operational and read by the ingestion service, not by `PipelineConfig` (TRD 07 §4.7); the loader ignores them when building `PipelineConfig` but includes them in the stored snapshot (ANL-030).
- `features` is not a `config_parameters` key; it is built in code (ANL-058), so `set-config` cannot change signs or composite membership.
- Contract classes live in `config.py` to avoid circular imports (TRD 07 §4.3).
