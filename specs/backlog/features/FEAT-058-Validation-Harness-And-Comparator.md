# FEAT-058 Validation harness (Tier A in-process, Tier B database) and comparator

| Field | Value |
|---|---|
| Epic | Testing & Validation |
| Build phase | Phase 7 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-057, FEAT-052, FEAT-055 |
| Status | Not Started |

## Purpose

Build the infrastructure under `tests/validation/` that runs the pipeline on the reference input and compares its output with the answer key. Tier A runs `analytics.pipeline.run_pipeline` in-process on DS-01 with profile `test_v0_1`; Tier B starts from an empty migrated PostgreSQL 16 database, loads the roster, ingests SRC-05 through the API, runs the pipeline at the reference as-of and reads results back through the API and the database. A declarative comparator matches rows by natural keys with 1e-6 numeric tolerance and exact strings, records every mismatch with its pipeline stage, and checks that Tier A equals Tier B. The R01–R10 cases and the report (FEAT-059) are built on top of it.

## Business Context

- BR-15 (reproduce the answer key exactly) and D-26 (1e-6 tolerance, exact strings): the comparator is the instrument that proves it.
- BR-01, BR-02: Tier B proves that ingest through the API and persistence preserve the result end to end.
- SRC-02 / D-38: the harness proves the pipeline output does not change when evaluation ground truth is loaded.
- FRs covered (BACKLOG.md): FR-031 (results with duplicates equal results without them, checked through the comparator).

## Referenced TRDs

- TRD 14 TDV-030..TDV-038 (tiers, tolerances, blank rule, natural keys, mismatch recording, full precision), TDV-040..TDV-042 (declarative mappings, unsigned z, composite row), TDV-101, TDV-102 (ground-truth isolation), §4.4 sequence, §4.5 Tables 4.5-A..4.5-G, §4.9 registry, §8 implementation notes.
- TRD 13 TST-080, TST-081, TST-083 (no skip/xfail/retry under `tests/validation/`), TST-048, TST-012.
- TRD 23 DME-016, DME-017 (column mappings; `expected_status` vs `processed_sessions`/`day_ledger`).
- TRD 07 ANL-017, ANL-042 (value mapping); TRD 05 API-065, API-069; TRD 19 E-06, E-12, E-13, E-18, E-19, E-20, E-21.
- TRD 24 D-26.

## Scope

- `tests/validation/conftest.py`: answer-key loader (workbook read-only via pandas/openpyxl), DS-01 reader in file order, registry from `database/seeds/test_v0_1/`, Tier A fixture (in-process `run_pipeline`) and Tier B fixture (testcontainers PostgreSQL 16, migrations, `seed test_v0_1 --master-only`, admin login, CSV upload, explicit-as-of run).
- `tests/validation/comparator.py`: declarative mapping tables for Tables 4.5-A..4.5-F, natural-key row matching, tolerance and type rules, stage attribution (Table 4.5-G), mismatch records, Tier A = Tier B comparison.
- Tier B data access: `GET /api/v1/analytics`, `/analytics/baselines`, `/scores`, `/alerts`, `/residents` and read-only `SELECT` of `processed_sessions`, `day_ledger`, `epochs`.
- Ground-truth isolation checks: static reference scan (TDV-101) and identical outputs with `evaluation_ground_truth` empty and loaded (TDV-102).
- A conftest hook that fails the job on any skip, xfail or retry under `tests/validation/`.

## Out of Scope

- The ten R01–R10 case modules, global checks VC-G01..VC-G12 and the report writer (FEAT-059).
- Golden files, checksums and the DS-10 loader (FEAT-057).
- API-level UI fixture checks (FEAT-060) and the robustness check (FEAT-061).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-058-FR-01 | Tier A shall run `analytics.pipeline.run_pipeline` in-process on the DS-01 records (file order = arrival order 1..283) with profile `test_v0_1`, facility timezone America/Chicago, R01–R10 enrolled 2026-10-01, the §4.9 device assignments and as-of 2026-10-30 15:00 America/Chicago. | TDV-030, TDV-002, ANL-017 |
| FEAT-058-FR-02 | DS-01 shall be the only pipeline input; no file, column or parameter derived from DS-02 shall be passed to the pipeline. | TDV-001 |
| FEAT-058-FR-03 | Tier B shall start from an empty migrated PostgreSQL 16 database, load the registry, upload DS-01 through `POST /api/v1/ingest` (multipart CSV, admin token), wait for the batch's run to finish, call `POST /api/v1/pipeline/run` with `{"scope": "all", "profile": "test_v0_1", "as_of": "2026-10-30T15:00:00-05:00"}`, wait until that run is `succeeded` (timeout 60 s, polling `GET /api/v1/pipeline/runs/{id}`), then compare API responses and database rows. | TDV-031, TST-081, TST-048 |
| FEAT-058-FR-04 | Floats (median, MAD, robust_spread, z, composite_raw, composite_z, cusum_tally, adjusted and raw feature values) shall pass iff `abs(actual − expected) ≤ 1e-6`; NaN or missing actual where a number is expected fails. | TDV-032, D-26 |
| FEAT-058-FR-05 | Strings shall compare exactly (case-sensitive, no trimming); integers, counts and booleans exactly; a blank workbook cell equals null or ""; `first_alarm_session` "none" equals null. | TDV-033, TDV-034, TDV-035 |
| FEAT-058-FR-06 | Rows shall be matched by natural keys, never by order: Annotated_sessions (resident_id, day, arrival_order); Exp_status_counts resident_id; Exp_resident_outcomes (resident_id, epoch); Exp_baselines (resident_id, epoch, feature); Exp_morning_offset feature; Exp_scores session_id; missing or extra rows on either side fail. | TDV-036 |
| FEAT-058-FR-07 | Every mismatch shall be recorded with sheet, key, column, expected, actual, absolute difference and the pipeline stage of Table 4.5-G; the comparator shall continue after a mismatch so all mismatches are reported in one run. | TDV-037 |
| FEAT-058-FR-08 | The harness shall use the workbook's full stored precision and open it read-only. | TDV-038, TDV-015 |
| FEAT-058-FR-09 | `comparator.py` shall implement Tables 4.5-A..4.5-F as declarative mapping tables so that a TRD 19 field rename changes only the mapping. | TDV-040, DME-016 |
| FEAT-058-FR-10 | `scores.z` shall be compared as unsigned z; the composite baseline shall be matched by `feature_key = 'composite'` ↔ "COMPOSITE (raw signed mean of 7 z)"; alarm strings mapped off/RINGS (first crossing)/on ↔ off/rings/on. | TDV-041, TDV-042, ANL-042 |
| FEAT-058-FR-11 | `expected_status` shall be compared with `processed_sessions.status` for rows with an arrival and with `day_ledger.status` for "no record" rows; `in_baseline` via `baseline_candidate` (usable and `baseline_ordinal ≤ baseline_n`) and the stored `in_baseline`. | DME-017, TRD 14 Table 4.5-A note |
| FEAT-058-FR-12 | The harness shall check that Tier A and Tier B results are equal on every compared value. | TRD 14 §4.4, TST-081 |
| FEAT-058-FR-13 | A static scan of `analytics/`, `backend/services/pipeline_runner.py`, its repositories and the ingest service (excluding `analytics_summary.py` and `database/seeds/`) shall fail on `evaluation_ground_truth`, `true_onset` or `planted_change`; Tier A and Tier B outputs including alerts and data alerts shall be identical with `evaluation_ground_truth` empty and with DS-10 loaded between two full runs. | TDV-101, TDV-102 |
| FEAT-058-FR-14 | No test under `tests/validation/` shall be skipped, marked xfail or retried; a conftest hook shall fail the session if one is. | TST-083 |
| FEAT-058-FR-15 | The comparator shall support running a case on a reduced input (records removed or truncated) so invariance checks such as removing the R04 duplicates can compare two Tier A results by exact equality. | FR-031, TRD 14 §4.7.4 |

## Inputs

- DS-01 `tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv`; DS-02 `tests/fixtures/answer_key/EchoWell_pipeline_test_v0_1.xlsx`; DS-10 `tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv` (FEAT-057).
- Registry `database/seeds/test_v0_1/` (FEAT-017); `PipelineConfig` `TEST_V0_1` (FEAT-040).
- Running backend app (in-process `TestClient`) on a testcontainers PostgreSQL 16 database (TST-002).

## Outputs

- Pytest fixtures `tier_a_result`, `tier_b_result` (API responses + DB rows), `answer_key`.
- `ComparisonResult` objects per case: number of checks, list of mismatches `{sheet, key, column, expected, actual, abs_diff, stage}` (consumed by FEAT-059's report).

## Data Flow

DS-01 → Tier A `run_pipeline` → `PipelineResult` → comparator ↔ DS-02. DS-01 → Tier B `POST /ingest` → batch run → `POST /pipeline/run` (as-of) → poll run → `GET` endpoints + SELECT derived tables → comparator ↔ DS-02. Tier A result ↔ Tier B result. DS-10 loaded between two Tier B full runs → outputs compared for equality.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-057, FEAT-052, FEAT-055

- FEAT-057 provides the golden files, checksums and DS-10.
- FEAT-052 provides `run_pipeline` for Tier A.
- FEAT-055 provides the full runner/CLI path (seed roster, explicit-as-of run) used by Tier B.

## Database Impact

- Tier B creates a disposable test database, applies all migrations and writes through the normal API paths only.
- Reads (read-only SELECT): `processed_sessions`, `day_ledger`, `epochs`, `baselines`, `scores`, `alerts`, `cusum_state`, `pipeline_runs`, `raw_sessions`, `ingest_rejections`.
- Writes `evaluation_ground_truth` only through the FEAT-057 loader for TDV-102.

## API Impact

Endpoints consumed: `POST /api/v1/auth/login` (E-02), `POST /api/v1/ingest` (E-06), `GET /api/v1/ingest/batches/{id}` (E-07), `POST /api/v1/pipeline/run` (E-20), `GET /api/v1/pipeline/runs/{id}` (E-21), `GET /api/v1/analytics` (E-18), `GET /api/v1/analytics/baselines` (E-19), `GET /api/v1/scores` (E-12), `GET /api/v1/alerts` (E-13), `GET /api/v1/residents` (E-08). None exposed.

## Frontend Impact

None.

## Analytics Impact

None in production code; the harness exercises the full stage chain and attributes mismatches to stages 1–10 per Table 4.5-G.

## Security Requirements

- The workbook and DS-10 are read only under `tests/` (TDV-011, AGT-007); the harness never passes them to the pipeline.
- Tier B uses test-only seeded credentials from environment variables and a disposable database; no real data (AGT-014).

## Error Handling

- Tier B run not `succeeded` within 60 s → test failure with the run's `error_message` and warnings.
- Missing sheet or column in the workbook → test failure naming it (never silently skipped, TST-083).
- Mismatches never stop the comparison; all are collected (TDV-037).

## Logging Requirements

- The harness writes mismatch lists to the case result objects for the report (FEAT-059); no application audit records beyond those produced by the API calls (login, ingest batch, pipeline run).

## Testing Requirements

- Self-tests of the comparator (`tests/validation/test_comparator.py`, marker `validation`): tolerance boundary (1e-6 passes, 1.1e-6 fails), NaN handling, blank/"none" rules, extra/missing rows fail, stage attribution.
- Tier A vs Tier B equality test; TDV-102 ground-truth isolation test; TDV-101 static scan.
- Conftest hook test: a deliberately skipped validation test makes the session fail (TST-083).
- Marker `validation`; run with `pytest tests/validation -q`.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-058-AC-01 | Tier A on DS-01 completes and the comparator reports 0 mismatches against Annotated_sessions (302 rows), Exp_status_counts (10), Exp_resident_outcomes (11), Exp_baselines (180) and Exp_scores (98). | AC-ANL-01; TDV-030 |
| FEAT-058-AC-02 | Tier B from an empty database reaches a `succeeded` explicit-as-of run within 60 s and the comparator reports 0 mismatches for the same sheets. | TDV-031; TST-081 |
| FEAT-058-AC-03 | Tier A and Tier B compared values are identical. | TST-081 |
| FEAT-058-AC-04 | A synthetic mismatch of 1.1e-6 in one `cusum_tally` is reported with sheet `Exp_scores`, key session_id, column, expected, actual, abs diff and stage 8, and the comparison continues to report a second injected mismatch. | TDV-032; TDV-037 |
| FEAT-058-AC-05 | Outputs (all compared values, alerts, data alerts) are identical with `evaluation_ground_truth` empty and with DS-10 loaded, and the TDV-101 scan passes. | AC-TDV-12; TDV-102 |
| FEAT-058-AC-06 | Adding `pytest.skip()` to any test under `tests/validation/` makes `pytest tests/validation -q` exit non-zero. | TST-083 |

## Definition of Done

- All FEAT-058 acceptance criteria pass; `pytest tests/validation -q` runs both tiers.
- Comparator mappings are declarative and cover Tables 4.5-A..4.5-F (TDV-040).
- Batch report lists IDs and commands (AGT-022).

## Implementation Notes

- Read sheets with `pd.read_excel(path, sheet_name=None, dtype=object, engine="openpyxl")` then cast numeric columns to float64; cast non-null `expected_epoch` to int (TRD 14 §8).
- Derive local date from `day` as `date(2026, 10, 1) + timedelta(days=day − 1)`; `local_time` is truncated to minutes (TRD 14 §8).
- Always include `arrival_order` in the Annotated_sessions key; the two duplicates share `(resident_id, day)` with their originals.
- Tier B must wait on `GET /api/v1/pipeline/runs/{id}`; never sleep a fixed time.
- In-process tests freeze the clock with `time-machine` where needed (TDV-061); Tier B uses the explicit as-of run instead of a clock override.
