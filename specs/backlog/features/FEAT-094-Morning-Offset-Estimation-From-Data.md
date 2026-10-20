# FEAT-094 Morning offset estimation from data

| Field | Value |
|---|---|
| Epic | Analytics Engine |
| Build phase | Future research (TRD 25) |
| Priority | P2 |
| Complexity | Medium |
| MVP status | Future |
| Dependencies | FEAT-043, FEAT-059 |
| Status | Not Started |
| Gate | Gated on OQ-09 |

## Purpose

Replace the configured placeholder morning offsets with values estimated from a larger dataset once a method is agreed. The extension point is fixed by the TRDs: a separate pure function `morning_offset.estimate_offsets(rows, config) -> Mapping[str, float]` that is evaluated offline on Team 1's DS-04, never runs inside `run_pipeline`, and whose output reaches the pipeline only through `PipelineConfig.morning_offsets` written with `set-config` and applied with `rebuild`. In the MVP the configured offsets stay in force (FR-073).

## Business Context

- BR-07 (morning sessions are adjusted before comparison with the baseline): offsets estimated from one resident's ~6 morning sessions are unreliable (SRC-03 README note 3), so the MVP uses configured offsets (D-02).
- FR-073: morning offsets are read from configuration and not estimated from data in the MVP; this feature is the post-MVP continuation covered by that FR.
- OQ-09: the estimation method on a larger dataset is open (owner: Team 2 data processing).

## Referenced TRDs

- TRD 07 ANL-055 (extension point), ANL-028, ANL-029 (`morning_offsets` keys equal the 19 feature keys), ANL-030, ANL-032 (algorithm-key change requires rebuild).
- TRD 08 BSC-020, BSC-021, BSC-022, BSC-023, BSC-024.
- TRD 02 FR-070, FR-071, FR-072, FR-073, FR-074.
- TRD 14 DS-04, TDV-093, §4.12 ("slightly worse morning values" in DS-04).
- TRD 15 §4.8 (`set-config`, `rebuild`).
- TRD 20 §4.11 (`morning_offsets` seed: loudness −1.5, phrase duration +0.10, speech rate −0.12, articulation rate −0.10, pause fraction +0.010, voiced fraction −0.020, others 0), AC-PGS-10.
- TRD 24 OQ-09 (gate), D-02, D-56, D-69, AGT-008 via TRD 25.
- TRD 25 AGT-008, AGT-020, AGT-021, AGT-050.

## Scope

Decided by the TRDs:

- Function signature and placement: `analytics/morning_offset.py::estimate_offsets(rows, config) -> Mapping[str, float]`, pure (no database, HTTP, clock or random access), separate from the stage function `adjust(rows: Sequence[EpochedRecord], config) -> list[AdjustedRecord]` (TRD 07 §4.2), not called by `run_pipeline` in v0.1.
- Output shape: a mapping with exactly the 19 feature keys (ANL-029), suitable as the JSON value of the `morning_offsets` key.
- Evaluation: offline on DS-04 (TDV-093); configured offsets remain in force until OQ-09 closes.
- Application path: `python -m backend.cli set-config --profile production --key morning_offsets --value '<json>' --reason "<estimation report>"`, then `python -m backend.cli rebuild --profile production --confirm REBUILD`; `morning_offsets` is an algorithm key, so runs fail with `config_changed_requires_rebuild` until the rebuild.
- The adjustment rule itself is unchanged: morning = local hour < `morning_cutoff_hour` (12) after `zoneinfo` conversion; adjusted = raw − offset for morning records; baselines and scores use adjusted values, the speaker screen raw values.
- The `test_v0_1` profile keeps the SRC-03 offsets (AGT-008); the answer key does not change.

Blocked on OQ-09 (not decided here):

- The estimation statistic, the minimum number of morning and afternoon sessions per resident, how residents are pooled, and whether offsets differ per facility or sex. The TRDs give no method; the implementer shall not choose one.
- Acceptance criteria for an estimated offset set (no threshold is defined).

Trigger for starting: OQ-09 answered in TRD 24 with the estimation method, and DS-04 delivered by Team 1.

## Out of Scope

- Estimating offsets at run time or inside `run_pipeline` (ANL-055, FR-073).
- Changing the morning cutoff, the time-zone conversion or the adjustment formula (BSC-020..BSC-022).
- Changing `test_v0_1` offsets or expected values (AGT-008).
- Alarm-limit calibration (FEAT-093).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-094-FR-01 | Morning offsets shall be read only from `PipelineConfig.morning_offsets`; the estimator shall be a separate pure function `morning_offset.estimate_offsets(rows, config) -> Mapping[str, float]` that does not run inside `run_pipeline`. | ANL-055, FR-073, AGT-021 |
| FEAT-094-FR-02 | The estimator output shall have exactly the 19 feature keys and pass `PipelineConfig.from_mapping` validation. | ANL-029 |
| FEAT-094-FR-03 | The estimation method shall be the one recorded in TRD 24 when OQ-09 closes; until then the function shall not be implemented with an invented method. | OQ-09, AGT-009 |
| FEAT-094-FR-04 | The estimator shall be evaluated offline on DS-04; configured offsets remain in force until OQ-09 closes. | TDV-093, D-02 |
| FEAT-094-FR-05 | Estimated offsets shall reach the pipeline only through `set-config` on profile `production` followed by `rebuild --profile production --confirm REBUILD`. | ANL-055, ANL-032, D-56, D-69 |
| FEAT-094-FR-06 | The adjustment shall keep the rules: local time by `zoneinfo` in `facility_tz`; morning iff local hour < 12; adjusted = raw − offset for morning records, raw otherwise; baselines and scores use adjusted values; the speaker screen uses raw values. | BSC-020, BSC-021, BSC-022, BSC-023, FR-074 |
| FEAT-094-FR-07 | The `test_v0_1` profile's `morning_offsets` shall stay at the SRC-03 values and the R01–R10 suite shall pass unchanged. | AGT-008, TDV-003 |
| FEAT-094-FR-08 | The estimator shall receive its records as the `rows` argument and shall not read files, the database, the clock or random numbers; which records and values form `rows` (statuses, raw or adjusted values, residents included) is not specified by the TRDs and follows the OQ-09 decision. | ANL-055, ARC-041, AGT-021, OQ-09 |

## Inputs

- DS-04 records (schema v0.1) as processed by the existing stages (local time, morning flag, status); the exact selection passed as `rows` follows OQ-09.
- Current `PipelineConfig` (production profile).
- The OQ-09 decision (method).

## Outputs

- `estimate_offsets` in `analytics/morning_offset.py` with unit tests.
- An estimation report (proposed offsets per feature, dataset version, code_version) under `docs/reports/` (name to follow the CUS-034 pattern, e.g. `docs/reports/MORNING_OFFSET_REPORT.md`).
- After acceptance: `config_parameters` production row `morning_offsets` changed by `set-config`; `audit_logs` `config.changed` and `pipeline.rebuild`.

## Data Flow

DS-04 → pipeline run (in-process) → records selected per the OQ-09 method → `estimate_offsets(rows, config)` → proposed mapping → report reviewed → `set-config` (production, `morning_offsets`) → `rebuild` → baselines and scores recomputed with new adjusted values.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-043, FEAT-059

- [FEAT-043](FEAT-043-Local-Time-Derivation-And-Morning-Adjustment.md) Local time derivation and morning adjustment (the stage whose offsets are estimated).
- [FEAT-059](FEAT-059-R01-R10-Validation-Cases-Global-Checks.md) R01–R10 validation (proves `test_v0_1` stays unchanged).

Gate: OQ-09 (estimation method on DS-04).

Features that build directly on this one (BACKLOG.md §4): none.

## Database Impact

- No schema change. Production `config_parameters` row (`profile` = `production`, `key` = `morning_offsets`) updated only through `set-config`; derived tables recomputed by `rebuild`; audit rows written.

## API Impact

None. No endpoint change; `pipeline_runs.config_snapshot` will show the new offsets.

## Frontend Impact

None.

## Analytics Impact

- New pure function `estimate_offsets` (method per OQ-09).
- Downstream effect after `rebuild`: adjusted values of morning sessions, hence baselines, z scores, composite and CUSUM in production change; `config_hash()` changes (ANL-030).

## Security Requirements

- `set-config` and `rebuild` run by an operator as `echowell_migrator`, audited (D-56, D-69).
- DS-04 is synthetic and never loaded into production (TDV-007).

## Error Handling

- Output failing ANL-029 validation → `ConfigError` naming the key; `set-config` refuses with exit code 2 and no change.
- Insufficient morning or afternoon data for a feature → behaviour to be defined by the OQ-09 method; the TRDs are silent (OQ-09).

## Logging Requirements

- `analytics/` does not log (LOG-006); the report and audit rows are the record.

## Testing Requirements

- Unit tests (`tests/unit/analytics/test_morning_offset.py`): purity (run twice, identical output), 19 keys returned, existing MO-01..MO-07 cases unchanged.
- Validation: `pytest tests/validation -q` passes with `test_v0_1` (VC-R06 morning adjustment unchanged).
- Method-specific tests are written from the OQ-09 decision.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-094-AC-01 | `grep -n "estimate_offsets" analytics/pipeline.py` returns nothing. Verified by: Inspection (run the command in the criterion and check its output). | ANL-055, FR-073 |
| FEAT-094-AC-02 | `estimate_offsets` returns a mapping with exactly the 19 feature keys that `PipelineConfig.from_mapping` accepts, and two calls with the same input return equal mappings. Verified by: Unit tests (`tests/unit/analytics/test_morning_offset.py`; MO-01, MO-07). | ANL-029, AGT-021 |
| FEAT-094-AC-03 | Unit cases MO-01..MO-07 and `pytest tests/validation -q` pass unchanged after the feature. | AGT-008, TDV-003 |
| FEAT-094-AC-04 | A production change of `morning_offsets` has one `config.changed` audit row and is followed by `pipeline.rebuild`; before the rebuild an ingest-triggered run fails with `config_changed_requires_rebuild`. Verified by: Unit tests (`tests/unit/analytics/test_morning_offset.py`; MO-01, MO-07). | ANL-032, D-69 |

## Definition of Done

- All FEAT-094 acceptance criteria pass.
- Gate satisfied (OQ-09 answered); all FEAT-094 acceptance criteria pass; estimation report reviewed by the algorithm lead.
- TRD 08/TRD 07 updated through a TRD change with the chosen method before code merges (AGT-001).

## Implementation Notes

- Keep `adjust` (the stage) and `estimate_offsets` separate so the stage stays a pure application of configured values.
- Use float64 throughout and never round intermediate values (AGT-054).
- The interim offsets (TRD 20 §4.11) remain the production values until the `set-config` change is approved.
