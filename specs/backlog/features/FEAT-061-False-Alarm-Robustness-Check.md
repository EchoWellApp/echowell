# FEAT-061 False-alarm robustness check (informational, not gating)

| Field | Value |
|---|---|
| Epic | Testing & Validation |
| Build phase | Phase 7 (TRD 25) |
| Priority | P2 |
| Complexity | Medium |
| MVP status | Optional |
| Dependencies | FEAT-059 |
| Status | Not Started |

## Purpose

Measure how often the pipeline raises a false alarm on residents with no planted change when the synthetic test data is regenerated with other seeds. `tests/validation/robustness.py` regenerates the data for seeds 1..100 with the reference generator into a temporary directory, runs the Tier A pipeline with profile `test_v0_1`, and reports the false-alarm count and rate over R01–R06 plus agreement of the pipeline output with each seed's generated answer key. The check is informational: it runs nightly or on manual dispatch only and never gates CI.

## Business Context

- SRC-03 README note 5 and RSK-03 (false alarms): the fixture seed was chosen so the eight no-change residents do not alarm; across 100 other seeds about 10 % of them raise a false alarm within 14 scored sessions using a 16-session baseline. The study team needs that rate visible.
- BR-15: multi-seed reproduction exposes rule differences that seed 20261004 does not exercise.
- OQ-13 (alarm-limit calibration): results inform calibration but set no acceptance threshold.
- FRs covered (BACKLOG.md): none directly (enabling feature).

## Referenced TRDs

- TRD 14 TDV-080 (per-seed generation and Tier A run, record alarms for R01–R08), TDV-081 (count over R01–R06, rate = count / 600, per-resident counts, report section 7 and `validation_results.json.robustness`, never fails a build), TDV-082 (multi-seed answer-key reproduction, S2 defect on mismatch), TDV-083 (nightly and manual dispatch only), §4.10 report section 7, §4.11.
- TRD 13 TST-084 (nightly, reported, not gating), TST-151 (nightly job `nightly-validation`).
- TRD 16 CIC-037 (`e2e.yml` job `nightly-validation`, `continue-on-error: true`, not a required check).
- TRD 09 §4.6 (61 of 600 = 10.2 % reference rate); TRD 24 OQ-13, RSK-03.

## Scope

- `tests/validation/robustness.py` runnable as a script or pytest module outside the gating selection: for each seed 1..100, run `python -I specs/algorithm/generate_pipeline_test_v0_1.py <tmpdir> <seed>`, run Tier A on the generated CSV with profile `test_v0_1`, record per resident R01–R08 whether any alarm rang, and compare the pipeline output with that seed's generated workbook using the FEAT-058 comparator.
- Aggregation: false-alarm count over R01–R06, rate = count / 600, per-resident counts for R01–R08 (R07 and R08 reported but excluded from the rate).
- Writing the results into report section 7 ("Informational: false-alarm robustness (not gating)") of `docs/reports/ALGORITHM_VALIDATION_REPORT.md` and into `validation_results.json` field `robustness`.
- Exclusion from PR runs (e.g. a dedicated marker or path excluded from the `pytest tests/validation` gate) and invocation from the `nightly-validation` job.

## Out of Scope

- The `e2e.yml` workflow and its `nightly-validation` job definition (FEAT-080).
- Alarm-limit calibration on DS-04 (FEAT-093) and any change of `cusum_h` or `baseline_n` (OQ-13).
- The gating R01–R10 suite (FEAT-059).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-061-FR-01 | For each seed in 1..100, `robustness.py` shall run the generator as `python -I generate_pipeline_test_v0_1.py <tmpdir> <seed>` (never importing it), run the Tier A pipeline on the generated CSV with profile `test_v0_1`, and record for R01–R08 whether any alarm rang. | TDV-080, TDV-024 |
| FEAT-061-FR-02 | It shall report the false-alarm count over R01–R06, the rate = count / 600 (6 residents × 100 seeds), and per-resident counts for R01–R08, with R07 and R08 reported but excluded from the rate. | TDV-081 |
| FEAT-061-FR-03 | Results shall be written to section 7 of `docs/reports/ALGORITHM_VALIDATION_REPORT.md` and to `validation_results.json.robustness`. | TDV-081, TRD 14 §4.10 |
| FEAT-061-FR-04 | For each seed, the pipeline output shall be compared with that seed's generated answer key; a mismatch shall be logged as an S2 defect by the nightly job. | TDV-082 |
| FEAT-061-FR-05 | The check shall never fail a build; it shall run only nightly and on manual dispatch in the `nightly-validation` job as an informational step (`continue-on-error: true`), not on pull requests. | TDV-081, TDV-083, TST-084, CIC-037 |
| FEAT-061-FR-06 | Each seed's generated files shall be written to a temporary directory and never into `tests/fixtures/` or `specs/`. | TDV-010, TRD 14 §4.3 |

## Inputs

- Generator SRC-04 `specs/algorithm/generate_pipeline_test_v0_1.py`; seeds 1..100.
- Tier A runner and comparator (FEAT-058); `TEST_V0_1` config; registry for R01–R10.

## Outputs

- Report section 7: seeds, residents, false alarms, rate, per-resident counts; `validation_results.json.robustness` object.
- S2 defect entries in the nightly job log for any multi-seed reproduction mismatch.

## Data Flow

Nightly schedule or manual dispatch → `nightly-validation` job → `robustness.py` → loop seeds: generator → temp CSV + workbook → Tier A run → alarm flags + comparator result → aggregate → `report.py` section 7 and JSON → artifact upload.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-059

- FEAT-059 provides the report writer and the passing validation suite whose Tier A runner and comparator (FEAT-058) this check reuses.
- FEAT-080 later wires the script into `e2e.yml`.

Features that build directly on this one (BACKLOG.md §4): none.

## Database Impact

None. The check runs Tier A only (in-process, no database).

## API Impact

None.

## Frontend Impact

None.

## Analytics Impact

None in production code; runs `analytics.pipeline.run_pipeline` 100 times with unchanged `test_v0_1` parameters (AGT-008).

## Security Requirements

- Synthetic data only; generated files stay in a temporary directory and are deleted after the run.
- The generator is executed with `python -I` in a temp working directory (TDV-024).

## Error Handling

- A generator or pipeline failure for one seed is recorded for that seed and the loop continues; the step never fails the build (TDV-081).
- A reproduction mismatch is reported as an S2 defect, not a build failure (TDV-082).

## Logging Requirements

- The job log prints per-seed status and the final count, rate and per-resident counts; mismatches are logged with seed and first failing stage.
- No audit records.

## Testing Requirements

- Unit test of the aggregation (`tests/unit/validation/test_robustness_aggregate.py` or within `tests/validation/` under a non-gating marker): given synthetic per-seed alarm flags, count and rate over R01–R06 = count / 600 and R07/R08 excluded from the rate.
- Smoke run on 2 seeds in a non-gating job to prove the loop and the report section render.
- The PR selection of `pytest tests/validation` must not collect the 100-seed run (TST-084).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-061-AC-01 | Running `python -m tests.validation.robustness` produces a report section 7 with seeds 1..100, the false-alarm count over R01–R06, rate = count / 600 and per-resident counts for R01–R08. Verified by: Test (run the command in the criterion against the stated environment and check the stated result). | TDV-080; TDV-081 |
| FEAT-061-AC-02 | `validation_results.json` contains a non-null `robustness` object after the run. Verified by: Inspection (the inspection method of TDV-081, applied to the condition stated in the criterion). | TDV-081 |
| FEAT-061-AC-03 | A forced failure inside the robustness step leaves the CI job status successful (informational step). Verified by: Inspection (the inspection method of CIC-037, applied to the condition stated in the criterion). | AC-TDV-09; CIC-037 |
| FEAT-061-AC-04 | The pull-request validation run (`pytest tests/validation -q`) does not execute the 100-seed loop. | TDV-083; TST-084 |
| FEAT-061-AC-05 | After the run, no generated file exists under `tests/fixtures/` or `specs/`. | TDV-010 |

## Definition of Done

- All FEAT-061 acceptance criteria pass locally; the script is ready for FEAT-080 to schedule.
- Batch report records the first measured rate for information (no threshold, OQ-13).

## Implementation Notes

- TRD 09 §4.6 reports 61 of 600 (10.2 %) as the reference rate; use it only as context in the report text, not as an assertion.
- Re-use the comparator's mapping tables so a seed's workbook is compared exactly like DS-02.
- Keep the run time bounded: Tier A on one seed is ≤ 5 s (TST-120), so 100 seeds fit a nightly job.
