# FEAT-093 Alarm-limit calibration on Team 1's 50-resident, 120-day dataset (DS-04)

| Field | Value |
|---|---|
| Epic | Analytics Engine |
| Build phase | Future research (TRD 25 Phase 12 open items; gated on OQ-13) |
| Priority | P2 |
| Complexity | High |
| MVP status | Future |
| Dependencies | FEAT-059 |
| Status | Not Started |

## Purpose

Calibrate the production alarm settings on a realistic dataset instead of the 30-day, 10-resident test fixture. When Team 1 delivers DS-04 (50 synthetic residents, ≥ 120 days, about 20 % with an inserted change, answer key in a separate file), ingest it into an isolated database, evaluate the grid `baseline_n` × `cusum_k` × `cusum_h` for false-alarm proportion, detection proportion and detection delay, apply the PI's selection rule, and change the `production` profile only through `set-config` followed by `rebuild`. The `test_v0_1` profile and the R01–R10 answer key stay unchanged.

## Business Context

- RSK-03: with a 16-session baseline about 10 % of no-change residents raise a false alarm within 14 scored sessions (61 of 600 = 10.2 % across 100 seeds, TRD 09 §4.6); uncalibrated limits raise false alarms.
- BR-11 (persistence rule) and BR-15 (the answer key must stay reproducible): calibration applies to `production` only (CUS-035).
- OQ-13: k and h calibration and the minimum length of stay are open; interim values are k = 0.5, h = 5.0 in both profiles and production `baseline_n` = 30 (D-01).

## Referenced TRDs

- TRD 09 CUS-029, CUS-030, CUS-031, CUS-032, CUS-033, CUS-034, CUS-035, §4.6.
- TRD 14 DS-04, TDV-004, TDV-090, TDV-091, TDV-092, TDV-007, TDV-010, §4.12.
- TRD 07 ANL-007 (`scripts/run_engine.py`), ANL-028..ANL-032 (profiles, validation, config hash, rebuild rule).
- TRD 15 §4.8 (`set-config`, `rebuild`).
- TRD 13 §2 out-of-scope note on detection performance, OQ-13 note in §9.
- TRD 24 OQ-13 (gate), RSK-03, D-01, D-26, D-56, D-69, ASM-04.
- TRD 25 AGT-007, AGT-008, AGT-009, AGT-014, AGT-021.

## Scope

Decided by the TRDs:

- Intake: DS-04 accepted only with its answer key as a separate file under `tests/fixtures/answer_key/team1_v1/`; ingested through `POST /api/v1/ingest` into an isolated database; every rejection listed with its reason in an intake report; the dataset is not used until rejections are 0 or explained by Team 1.
- Grid: `baseline_n` ∈ {16, 20, 30, 45, 60}, `cusum_k` ∈ {0.25, 0.5, 0.75, 1.0}, `cusum_h` ∈ {3, 4, 5, 6, 7, 8, 10}, one `run_pipeline` run per combination through `scripts/run_engine.py`, all other parameters at production values.
- Metrics per combination: (a) false-alarm proportion (no-change residents with ≥ 1 alert, plus alerts before the true onset in change residents); (b) false alerts per 100 scored sessions; (c) detection proportion (first alert on or after true onset and within 30 days); (d) detection delay in scored sessions and days (median and IQR); (e) share of residents whose baseline never forms. Plus TDV-091 per-resident outputs under profiles `production` and `test_v0_1` (alarm yes/no, delay, false alarm yes/no, epoch count for moved residents).
- Answer-key isolation: only the calibration evaluation code reads the DS-04 answer key, after the pipeline run; never `analytics/` or the backend.
- Selection rule: among combinations with false-alarm proportion ≤ the PI's target, highest detection proportion, then shortest median delay.
- Application: one `python -m backend.cli set-config --profile production --key <k> --value '<json>' --reason "<calibration report>"` per changed key, then `python -m backend.cli rebuild --profile production --confirm REBUILD`.
- Reporting: `docs/reports/CALIBRATION_REPORT.md` (grid results, chosen values, dataset version, code_version) and `docs/reports/calibration_results.json`.
- Results are informational and never gate CI until OQ-13 defines acceptance thresholds.

Blocked on open questions (not decided here):

- OQ-13: the PI's false-alarm target, the acceptance thresholds for detection metrics, and the minimum length of stay. Without the target the selection rule cannot be applied and no `set-config` is run.
- Delivery of DS-04 by Team 1 (SRC-13 §5–6).
- Whether `baseline_n` may change in production: D-01 records production `baseline_n` = 30 as an owner decision, while CUS-031 includes `baseline_n` in the grid and RSK-03 allows raising it "with owner approval". A `baseline_n` change therefore needs a new owner decision (D entry) in addition to OQ-13; k and h changes need only OQ-13.
- Where the isolated database lives: CUS-030 says "ingested by CSV upload into the staging environment", TDV-090 says "an isolated database". Staging runs profile `test_v0_1` with a fixed PIPELINE_AS_OF and is re-seeded with `seed test_v0_1 --reset`, which would wipe DS-04. Until TRD 24 settles this (new OQ under AGT-009), the evaluation runs in-process through `scripts/run_engine.py` and the intake on a local or disposable isolated database, never on production.

Trigger for starting: Team 1 delivers DS-04 with a separate answer key, and OQ-13 is answered in TRD 24 with the PI's false-alarm target (the grid evaluation of CUS-031/CUS-032 may run as soon as DS-04 arrives; the selection and any `set-config` wait for OQ-13).

## Out of Scope

- Any change to the `test_v0_1` profile, its expected values or tolerances (AGT-008, CUS-035).
- Any change to stage code in `analytics/`; calibration changes parameters only (AGT-020).
- Clinical validation and detection-performance claims in the UI (CUS-029; TRD 13 §2).
- Morning-offset estimation on DS-04 (FEAT-094).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-093-FR-01 | DS-04 shall be accepted for evaluation only with its answer key as a separate file stored under `tests/fixtures/answer_key/team1_v1/`, never in a pipeline input folder. | TDV-004, TDV-010 |
| FEAT-093-FR-02 | On receipt, DS-04 shall be ingested through `POST /api/v1/ingest` into an isolated database, with every rejection listed with its reason in an intake report; the dataset shall not be used until rejections are 0 or explained by Team 1. | TDV-090, CUS-030 |
| FEAT-093-FR-03 | DS-04 and its outputs shall never be loaded into production, and test fixture data shall never share a database with real records. | CUS-030, TDV-007, AGT-014 |
| FEAT-093-FR-04 | The calibration shall evaluate every combination of `baseline_n` ∈ {16, 20, 30, 45, 60}, `cusum_k` ∈ {0.25, 0.5, 0.75, 1.0}, `cusum_h` ∈ {3, 4, 5, 6, 7, 8, 10} by running `run_pipeline` once per combination through the engine CLI with all other parameters at production values. | CUS-031, ANL-007 |
| FEAT-093-FR-05 | For each combination the calibration shall report metrics (a)–(e) of CUS-032. | CUS-032 |
| FEAT-093-FR-06 | The evaluation shall also report, under profiles `production` and `test_v0_1`, per changed resident alarm yes/no and delay in days from true onset to first alarm, per unchanged resident false alarm yes/no, and the epoch count for moved residents. | TDV-091 |
| FEAT-093-FR-07 | The DS-04 answer key shall be read only by the calibration evaluation code after the pipeline run, never by `analytics/` or the backend. | CUS-033, AGT-007 |
| FEAT-093-FR-08 | The chosen values shall be selected by the rule: false-alarm proportion ≤ the PI's target, then highest detection proportion, then shortest median delay. The target is not defined in the TRDs (OQ-13); without it no selection is made. | CUS-034, OQ-13 |
| FEAT-093-FR-09 | Chosen values shall be written to profile `production` only, one `set-config` call per key with the calibration report as reason, then applied with `rebuild --profile production --confirm REBUILD`; until the rebuild runs, other runs fail with `config_changed_requires_rebuild`. | CUS-034, ANL-032, D-56, D-69 |
| FEAT-093-FR-10 | The SRC-03 validation (profile `test_v0_1`) shall remain unchanged and pass after calibration. | CUS-035, AGT-008 |
| FEAT-093-FR-11 | `docs/reports/CALIBRATION_REPORT.md` and `docs/reports/calibration_results.json` shall contain the grid results, chosen values, dataset version and code_version. | CUS-034 |
| FEAT-093-FR-12 | DS-04 results shall be informational and shall not gate CI until OQ-13 defines acceptance thresholds. | TDV-092 |
| FEAT-093-FR-13 | The analytics page shall continue to show the active `cusum_k`, `cusum_h`, `baseline_n` and profile, and no documentation shall present v0.1 alarm rates as validated detection performance. | CUS-029 |

## Inputs

- DS-04 CSV(s) in schema v0.1 and the separate answer key file from Team 1 (SRC-13 §5–6).
- The pipeline (`analytics.pipeline.run_pipeline`) and `scripts/run_engine.py`; production profile values (TRD 07 §4.7).
- PI false-alarm target (OQ-13).

## Outputs

- Intake report (rejections with reasons), `docs/reports/CALIBRATION_REPORT.md`, `docs/reports/calibration_results.json`.
- After OQ-13: `config_parameters` rows of profile `production` changed by `set-config` and `audit_logs` rows `config.changed` and `pipeline.rebuild`.
- Calibration evaluation script under `tests/validation/` or `scripts/` (outside `analytics/` and `backend/`), e.g. `scripts/calibrate_alarm_limits.py`.

## Data Flow

DS-04 CSV → `POST /api/v1/ingest` on the isolated database → intake report. DS-04 records → `scripts/run_engine.py` per grid combination (in-process, pure) → per-run JSON results → evaluation script joins results with the DS-04 answer key → metrics table → report. After OQ-13: chosen values → `set-config` (production) → `rebuild` → new frozen baselines and scores in production.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-059

- [FEAT-059](FEAT-059-R01-R10-Validation-Cases-Global-Checks.md) R01–R10 validation cases (proves the `test_v0_1` answer key still passes after calibration, CUS-035).

Gate: OQ-13 and delivery of DS-04 by Team 1.

## Database Impact

- Isolated intake database: `raw_sessions`, `ingest_batches`, `ingest_rejections` and derived tables for DS-04.
- Production (after OQ-13 only): `config_parameters` rows of profile `production` for the changed keys; `baselines`, `scores`, `cusum_state`, `alerts` recomputed by `rebuild`; `audit_logs` rows `config.changed` and `pipeline.rebuild`.
- No schema change.

## API Impact

- Consumed: `POST /api/v1/ingest`, `GET /api/v1/ingest/batches/{id}` on the isolated database.
- Exposed: none new; `GET /api/v1/analytics` keeps reporting the active parameters (CUS-029).

## Frontend Impact

None. The Analytics page already shows the active settings; no detection-performance claim is added.

## Analytics Impact

- Algorithms used unchanged: robust baseline (median, MAD × 1.4826 with floors), composite z, one-sided CUSUM S = max(0, S + z − k) with alarm at S ≥ h (TRD 08, TRD 09).
- Calculations added (outside `analytics/`): per-combination false-alarm proportion, false alerts per 100 scored sessions, detection proportion within 30 days of onset, median and IQR delay, share of residents without a formed baseline.

## Security Requirements

- DS-04 is synthetic; it never reaches production (CUS-030, AGT-014).
- `set-config` and `rebuild` run as `echowell_migrator` by an operator (D-56, D-69); every change is audited.

## Error Handling

- Intake rejections > 0 without Team 1 explanation → stop; report to Team 1.
- A grid run raising `ConfigError` (e.g. `baseline_n` < `screen_min_n`) is recorded as invalid for that combination.
- No combination meets the target → report "no admissible combination"; production values stay unchanged (interim decision of OQ-13 remains in force).
- `set-config` refuses unknown keys or invalid values with exit code 2 and no change (TRD 15 §4.8).

## Logging Requirements

- Calibration script logs progress (combination index, runtime) without feature values.
- Audit rows `config.changed` (old, new, reason) and `pipeline.rebuild` (old and new config hash) for any production change (TRD 12 §4.12).

## Testing Requirements

- Unit tests of the metric functions on small hand-made result sets (false alarm before onset counted; detection window 30 days inclusive).
- Regression: `pytest tests/validation -q` passes after any production change (CUS-035).
- Integration: after `set-config` without `rebuild`, an ingest-triggered run fails with `config_changed_requires_rebuild` (ANL-032 test exists; re-run).
- No CI gating on DS-04 metrics (TDV-092).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-093-AC-01 | The intake report lists 0 rejections, or every rejection with a Team 1 explanation, before any evaluation run. | TDV-090 |
| FEAT-093-AC-02 | `calibration_results.json` contains 140 combinations (5 × 4 × 7), each with metrics (a)–(e) of CUS-032. | CUS-031, CUS-032 |
| FEAT-093-AC-03 | `grep -rn "team1_v1" analytics backend` returns no matches. | CUS-033 |
| FEAT-093-AC-04 | After calibration, `pytest tests/validation -q` passes and the `test_v0_1` rows of `config_parameters` are unchanged. | CUS-035 |
| FEAT-093-AC-05 | Each production parameter change has one `config.changed` audit row with the calibration report as reason, followed by one `pipeline.rebuild` row. | CUS-034, D-69 |
| FEAT-093-AC-06 | No CI required check depends on DS-04 results. | TDV-092 |

## Definition of Done

- Gate satisfied (OQ-13 answered in TRD 24; DS-04 delivered); all FEAT-093 acceptance criteria pass; calibration report reviewed by the algorithm lead and the PI.
- TRD 24 updated with the decision (new D entry) and OQ-13 closed by its owner.

## Implementation Notes

- Run the grid in-process (pure `run_pipeline`) for speed; 140 runs on 50 × 120 records fit easily within the ANL-048 scale.
- Keep the evaluation code out of `analytics/` and `backend/` so the import-linter and AGT-007 checks stay green.
- When TRD gaps block a step (target, baseline_n authority, database location), stop that step and raise an OQ in TRD 24 (AGT-009) rather than choosing.
