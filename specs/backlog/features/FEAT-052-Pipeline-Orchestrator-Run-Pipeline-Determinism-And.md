# FEAT-052 Pipeline orchestrator run_pipeline, determinism and engine CLI

| Field | Value |
|---|---|
| Epic | Analytics Engine |
| Build phase | Phase 6 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-041, FEAT-042, FEAT-044, FEAT-045, FEAT-046, FEAT-047, FEAT-048, FEAT-049, FEAT-050, FEAT-051 |
| Status | Not Started |

## Purpose

Implement `analytics/pipeline.py::run_pipeline`, the single entry point of the analytics engine used by every trigger (ingest, nightly, manual, test). It wires the stage functions delivered by FEAT-041..FEAT-051 in the fixed 16-step order of TRD 07 §4.5, enforces the input contract, excludes records after the as-of instant, assembles the `PipelineResult` with counts and sorted warnings, and guarantees bit-identical output for identical input. It also delivers the file-based command-line entry point `scripts/run_engine.py` so the engine can be run outside the backend (Pytest, local use, demo fallback).

## Business Context

- BR-15 (reproduce the answer key exactly): `run_pipeline` on SRC-05 with `test_v0_1` must reproduce SRC-03 (ANL-017); determinism makes the result repeatable.
- BR-02 and SRC-02 ("every other table can be rebuilt"): the same raw input always yields the same derived result (D-07).
- BR-03..BR-11: the stage order realises duplicate removal, quality gate, epochs, speaker screen, morning adjustment, baseline, scoring, CUSUM and alerts in sequence.
- FRs covered (BACKLOG.md): FR-031 (results with duplicates equal results without them).

## Referenced TRDs

- TRD 07 ANL-006 (stage order), ANL-007 (`scripts/run_engine.py`), ANL-014..ANL-023 (orchestrator, as-of exclusion, per-resident independence, answer-key reproduction, `ContractError`, no exceptions for normal data, determinism, stable keyed sorting, float64, rebuild equality), ANL-047 (≤ 5 s on SRC-05), ANL-050 (complexity), §4.3 (`PipelineResult`, `counts` keys), §4.5 (signature and 16-step algorithm), ANL-051, ANL-052 (warning codes).
- TRD 01 ARC-040..ARC-046 (single entry point, purity, determinism, frozen baselines as input, human data preserved, natural keys, numpy median semantics).
- TRD 03 NFR-030..NFR-037 (float64, 1e-6 tolerance, double precision storage, bit-identical runs, no randomness/clock/locale, config snapshot, pinned dependencies, presentation-only rounding).
- TRD 25 AGT-021 (purity), §4.8 pitfalls AGT-040..AGT-058; TRD 24 D-07, D-20.
- TRD 13 PIP-01..PIP-05, TST-011, TST-022, TST-120, TST-140; TRD 14 VC-G12, VC-R04-INV.

## Scope

- `analytics/pipeline.py::run_pipeline(records, residents, assignments, config, as_of, *, frozen_baselines=None) -> PipelineResult` implementing steps 1–16 of TRD 07 §4.5.
- Input validation (step 1): types, timezone-aware `as_of`, unique `arrival_seq`, exactly the 19 feature keys, every resident in `assignments` known, `config` is a `PipelineConfig`; violation → `ContractError`, no partial result.
- As-of exclusion (step 3) with one `RunWarning(code="after_as_of")` per excluded record and `counts["excluded_after_as_of"]`.
- Calls of the stage functions in order, including the late-arrival classification of FEAT-045 (step 5), assembly of `EpochSummary` per resident-epoch (step 11), and `PipelineResult` with `run_config`, `config_hash`, `engine_version` (`ENGINE_VERSION = "0.1.0"`), `as_of`, the tuples of the contract and `counts` with the 12 keys of TRD 23 §4.2.10.
- Deterministic ordering of every output tuple and warnings sorted by `(code, resident_code, session_id)`.
- `scripts/run_engine.py --input <csv> --profile test_v0_1 --as-of "2026-10-30 15:00" --assignments <json> --residents <json> --out <dir>` writing the result as JSON files (outside the `analytics/` package).
- `analytics/__init__.py` exports (`run_pipeline`, `PipelineConfig`, `PRODUCTION`, `TEST_V0_1`, the contract dataclasses, `ENGINE_VERSION`).
- Unit tests `tests/unit/analytics/test_pipeline.py` (PIP-01..PIP-05), determinism and performance tests.

## Out of Scope

- The stage algorithms themselves (FEAT-041..FEAT-051) and the config/contract dataclasses (FEAT-040).
- Loading inputs from the database, persisting results, advisory locks and `pipeline_runs` rows (FEAT-053).
- Triggers: ingest, nightly, `POST /api/v1/pipeline/run` (FEAT-054, FEAT-024) and the operator CLI `backend.cli run-pipeline` (FEAT-055).
- The R01–R10 validation harness and report (FEAT-058, FEAT-059).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-052-FR-01 | `run_pipeline` shall have the five positional parameters `records, residents, assignments, config, as_of` and the optional keyword `frozen_baselines` of TRD 07 §4.5, and shall be the single engine entry point for every trigger. | ANL-014, ARC-040, TRD 07 §4.5 |
| FEAT-052-FR-02 | It shall execute the stages in the fixed order duplicate detection, quality gate, epoch detection, speaker screen, context (morning) adjustment, baseline, score, CUSUM, alert generation, day ledger, data alerts, analytics aggregates, following steps 1–16 of TRD 07 §4.5. | ANL-006, ANL-014, ARC-040 |
| FEAT-052-FR-03 | Step 1 shall validate inputs (timezone-aware `as_of`, unique `arrival_seq`, 19 canonical feature keys, residents in `assignments` known, `config` of type `PipelineConfig`) and raise `ContractError` with no partial result on any violation. | ANL-018, ANL-013 |
| FEAT-052-FR-04 | Records with `timestamp_utc > as_of` shall be excluded before stage 1 and produce one `RunWarning(code="after_as_of")` each; they shall not appear in `sessions`, scores or ledger, and shall be counted in `counts.excluded_after_as_of`. | ANL-015 |
| FEAT-052-FR-05 | Residents shall be processed independently except for the day ledger, which reads the records and assignments of every resident sharing a device; the orchestrator shall pass all `assignments` of the facility to the ledger stage. | ANL-016, ARC-065 |
| FEAT-052-FR-06 | All sorting shall be stable and fully keyed: records by `(timestamp_utc, arrival_seq)` within a resident, residents by `resident_code`, outputs by `(resident_code, epoch_number, timestamp_utc, arrival_seq)`; no output shall depend on set iteration or unsorted dict order. | ANL-021, NFR-034 |
| FEAT-052-FR-07 | All arithmetic shall be float64; medians with `numpy.median`; signed z sums in canonical feature order; no rounding of stored numeric results. | ANL-022, ARC-046, NFR-030, NFR-037 |
| FEAT-052-FR-08 | Two calls with equal arguments shall return `PipelineResult` objects equal field by field (bitwise-equal floats); shuffling the input order while keeping `arrival_seq` shall not change the result. | ANL-020, ARC-042, NFR-033, AGT-021 |
| FEAT-052-FR-09 | Normal data conditions (baseline forming, zero usable sessions, a resident with no records or only duplicates, empty input) shall produce valid results without raising. | ANL-019 |
| FEAT-052-FR-10 | `PipelineResult.sessions` shall contain exactly one `AdjustedRecord` per non-excluded input record including duplicates, ordered by `arrival_seq`. | ANL-012 |
| FEAT-052-FR-11 | `PipelineResult` shall carry `run_config` (snapshot), `config_hash`, `engine_version`, `as_of`, `counts` with keys arrivals, usable, set_aside, quarantined, duplicate, missing_resident, missing_device_gap, late_arrival, scored, alerts_opened, excluded_after_as_of, residents, and `warnings` sorted by `(code, resident_code, session_id)`. | TRD 07 §4.3, §4.5 step 16 |
| FEAT-052-FR-12 | When `frozen_baselines` is supplied for an epoch, scoring shall use those persisted values (passed through to the baseline stage of FEAT-045). | ARC-043, ANL-037, TRD 07 §4.5 |
| FEAT-052-FR-13 | For profile `test_v0_1`, SRC-05, R01–R10 enrolled 2026-10-01, the TRD 10 §4.9 assignments and as-of 2026-10-30 15:00 America/Chicago, the result shall reproduce SRC-03 (Annotated_sessions, Exp_status_counts, Exp_resident_outcomes, Exp_baselines 180 rows, Exp_scores 98 rows) within 1e-6 and exact strings. | ANL-017, NFR-031 |
| FEAT-052-FR-14 | Removing duplicate arrivals from the input shall leave every non-duplicate result unchanged (R04 arrivals 89 and 283). | FR-031; AC-ANL-03 |
| FEAT-052-FR-15 | `run_pipeline` on SRC-05 including data alerts and aggregates shall complete in ≤ 5 s on a GitHub-hosted ubuntu-latest runner; no stage worse than O(n log n) per resident except late-arrival detection. | ANL-047, ANL-050 |
| FEAT-052-FR-16 | `scripts/run_engine.py` shall run the engine from files with the arguments of ANL-007 and write the result as JSON files to `--out`; it shall live outside `analytics/` so no `analytics` module performs file I/O. | ANL-007, ARC-041 |
| FEAT-052-FR-17 | `analytics/pipeline.py` shall not import a database, HTTP or `backend` module, read a clock or environment variable, or use randomness. | ANL-002, ANL-003, ARC-041 |

## Inputs

- `records`: `Sequence[RawRecord]` (any order), built by the backend from `raw_sessions` typed columns (FEAT-053) or by `scripts/run_engine.py` from a CSV.
- `residents`: `Sequence[ResidentInfo]`; `assignments`: all `DeviceAssignment`s of the facility; `config`: `PipelineConfig` (FEAT-040); `as_of`: timezone-aware datetime; optional `frozen_baselines: Mapping[EpochKey, tuple[Baseline, ...]]`.
- CLI: SRC-05 CSV, `--assignments` JSON and `--residents` JSON files.

## Outputs

- `PipelineResult` (TRD 07 §4.3): sessions, epochs, baselines, scores, alerts, ledger, data_alerts, analytics, warnings, counts, run_config, config_hash, engine_version, as_of.
- SRC-05 counts: arrivals 283, usable 267, set_aside 12, quarantined 2, duplicate 2, missing_resident 17, missing_device_gap 2, late_arrival 0, scored 98, alerts_opened 2, excluded_after_as_of 0, residents 10 (TRD 06 DB-020).
- CLI: JSON files of the result in the `--out` directory.

## Data Flow

Caller → `run_pipeline` → (1) validate → (2) sort by `arrival_seq` → (3) exclude after as-of → (4) `apply_quality_gate(mark_duplicates(recs))` → (5) late-arrival classification → (6) `screen_speakers(assign_epochs(...))` → (7) `adjust` → (8) `build_baselines` (with `frozen_baselines`) → (9) per formed epoch `feature_z`, `composite_raw`, `composite_z` → (10) `run_cusum` → (11) `EpochSummary` → (12) `generate_alerts` → (13) `build_ledger` → (14) `generate_data_alerts` → (15) `build_analytics_summary` → (16) `PipelineResult` with counts and sorted warnings → caller (FEAT-053 persists it; tests compare it; the CLI serialises it).

## Dependencies

Required before implementation (BACKLOG.md): FEAT-041, FEAT-042, FEAT-044, FEAT-045, FEAT-046, FEAT-047, FEAT-048, FEAT-049, FEAT-050, FEAT-051

- Each dependency delivers one stage function the orchestrator calls (duplicates and gate, epochs, speaker screen, baseline and late arrivals, scoring, CUSUM, alerts, ledger, data alerts, aggregates); FEAT-043 (morning adjustment) and FEAT-040 (contracts, config) are reached through them.
- FEAT-053 (runner) and FEAT-058 (validation harness) depend on this feature.

## Database Impact

None. `analytics/` performs no database access (ANL-002, ARC-041). The persisted shapes (`processed_sessions`, `epochs`, `baselines`, `scores`, `cusum_state`, `alerts`, `day_ledger`, `data_alerts`, `pipeline_runs.counts`/`warnings`) are written by FEAT-053.

## API Impact

None. No endpoint is exposed or consumed; the backend reaches the engine only through `pipeline_runner` (FEAT-053, API-006).

## Frontend Impact

None. The engine has no UI; its results reach the pages through the API features.

## Analytics Impact

- Module: `analytics/pipeline.py` (orchestration, as-of filter, result assembly), `analytics/__init__.py` exports.
- Algorithms orchestrated: TRD 10 duplicate/quality/ledger rules, TRD 08 epoch/speaker/morning/baseline/score rules, TRD 09 CUSUM/alert/data-alert rules, TRD 07 §4.13 aggregates.
- Calculations performed here: counts aggregation over statuses and ledger, `EpochSummary` assembly (`watching_since`, `current_tally`, `alarm_on`, `first_alarm_session_id`), warning sorting.

## Security Requirements

- The engine never receives evaluation ground truth: no parameter, input object or import carries true onset or planted change (PIP-05, ANL-064, AGT-057).
- No audio or personal data enters the engine; inputs carry study IDs and numeric features only.
- `scripts/run_engine.py` reads only files given on its command line and never the answer-key workbook (AGT-007).

## Error Handling

- Contract violations → `ContractError` (subclass of `AnalyticsError`), raised before any stage runs (ANL-018, ANL-051).
- Invalid configuration → `ConfigError` raised by `PipelineConfig.from_mapping` (FEAT-040); the orchestrator raises no other exception type intentionally.
- Data-quality findings are returned as `RunWarning` (`after_as_of`, `late_arrival`, `zero_spread`, `baseline_mismatch`, `config_mismatch`, `no_device_assignment`, `alert_first_crossing_changed`, `device_assignment_mismatch`, ANL-052), never raised.
- The CLI exits non-zero with a message on `ContractError`, `ConfigError` or unreadable input files.

## Logging Requirements

- `analytics/` shall not log (ANL-053); warnings are returned in `PipelineResult.warnings` for the runner to log and store (FEAT-053, FEAT-056).
- `scripts/run_engine.py` prints only file paths and counts, never feature values (ANL-054).
- No audit records.

## Testing Requirements

- Unit (`tests/unit/analytics/test_pipeline.py`, marker `unit`): PIP-01 (SRC-05 equals answer key, delegating to the Tier A comparator), PIP-02 (byte-identical serialised output twice), PIP-03 (stage order via call-order spy), PIP-04 (late record before a frozen baseline → `late_arrival`, baseline unchanged), PIP-05 (no ground-truth input); `ContractError` cases (naive `as_of`, duplicate `arrival_seq`, missing feature key, unknown resident, wrong config type); `after_as_of` exclusion; empty input and R08-style forming resident (ANL-019).
- Property-based (Hypothesis): pipeline output identical for two runs on the same input; shuffled input equal (TST-022, AC-ANL-02).
- Invariance: R04 duplicates removed → identical R04 outputs (AC-ANL-03, VC-R04-INV).
- Static: import-linter contract fails on database/HTTP/backend imports in `analytics/` (AC-ANL-04, TST-021).
- Performance (`tests/performance/test_pipeline_runtime.py`, marker `performance`): TST-120 ≤ 5 s.
- CLI smoke: `python scripts/run_engine.py` on SRC-05 writes JSON whose counts equal FR-11 values.
- Coverage `analytics/` ≥ 95 % (TST-140).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-052-AC-01 | `run_pipeline` on SRC-05 with `test_v0_1` and as-of 2026-10-30 15:00 America/Chicago passes all SRC-03 comparisons (302, 10, 11, 180, 98 rows) at 1e-6 and exact strings. | AC-ANL-01; PIP-01 |
| FEAT-052-AC-02 | Two calls on the same inputs, and a call on a shuffled input list with unchanged `arrival_seq`, return equal results. | AC-ANL-02; PIP-02 |
| FEAT-052-AC-03 | Removing arrivals 89 and 283 changes nothing in R04's baselines, scores or ledger. | AC-ANL-03; FR-031 |
| FEAT-052-AC-04 | A static import check fails the build when any `analytics/` module imports a database, HTTP or `backend` module. | AC-ANL-04 |
| FEAT-052-AC-05 | `PipelineResult.counts` on SRC-05 equals 283/267/12/2/2/17/2/0/98/2/0/10 for the 12 keys in TRD 23 order. | DB-020; TST-051 |
| FEAT-052-AC-06 | A record with `timestamp_utc` after `as_of` is absent from sessions, scores and ledger and yields exactly one `after_as_of` warning. | ANL-015 |
| FEAT-052-AC-07 | A naive `as_of`, a duplicate `arrival_seq` or a missing feature key each raises `ContractError` and returns no result. | ANL-018 |
| FEAT-052-AC-08 | The engine on SRC-05 completes in ≤ 5 s in CI. | AC-ANL-07; TST-120 |
| FEAT-052-AC-09 | `python scripts/run_engine.py --input tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv --profile test_v0_1 --as-of "2026-10-30 15:00" --assignments <json> --residents <json> --out <dir>` exits 0 and writes the result JSON files. | ANL-007 |

## Definition of Done

- All FEAT-052 acceptance criteria pass; `pytest tests/unit -q` green; `analytics/` coverage ≥ 95 %.
- Stage order matches TRD 07; full input reproduces the answer key in Tier A (TRD 25 Phase 6 DoD).
- `docs/reports/ANALYTICS_IMPLEMENTATION_REPORT.md` updated with the orchestrator section (TRD 25 Phase 6 Outputs).
- Batch report lists requirement IDs, tests and commands (AGT-022).

## Implementation Notes

- Fill the existing skeleton by creating `analytics/pipeline.py` and `analytics/__init__.py` only; do not add modules (TRD 07 §8, ANL-004).
- Sort explicitly with `(timestamp_utc, arrival_seq)` keys even though `sorted` is stable (TRD 07 §8).
- Parse `timestamp_utc` in the CLI with `datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)`; read the CSV in file row order (arrival order, TDV-002).
- `frozen_baselines` is a keyword addition to the contract signature (TRD 07 §5 note); keep the five positional parameters unchanged.
- TRD 01 ARC-040 says "data-alert generation last" while TRD 07 ANL-006/§4.5 place analytics aggregates (step 15) after data alerts; follow the TRD 07 order, which is the binding algorithm (aggregates read data alerts).
- Late-arrival detection reruns stages 1–8 on a prefix only for out-of-order records (ANL-024, ANL-050); SRC-05 exercises only the fast path.
