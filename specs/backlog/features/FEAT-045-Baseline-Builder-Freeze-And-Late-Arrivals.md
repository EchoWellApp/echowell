# FEAT-045 Baseline builder, freeze and late arrivals

| Field | Value |
|---|---|
| Epic | Analytics Engine |
| Build phase | Phase 6 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-044 |
| Status | Not Started |

## Purpose

Build each resident's personal baseline per epoch from the first N usable check-ins (30 in production, 16 in the test profile), compute the median, MAD, robust spread and floor flag for all 19 features plus a composite entry, and freeze it: later sessions, drift and late-arriving records never change it. Report "Baseline forming · n of N" while fewer than N usable sessions exist. Classify late-arriving records that would have changed a frozen baseline or renumbered epochs, keep them out of every baseline, screen reference, score and tally, and flag them with a `late_arrival` warning. This is what makes R10's slow drift detectable ("baseline unchanged by drift") and keeps rebuilds reproducible.

## Business Context

- BR-09 (personal baseline, frozen after N usable sessions): membership, statistics, freeze metadata and forming progress.
- BR-08: the count restarts in each new epoch (R07 epoch 1 never forms; epoch 2 freezes after R07-20261028-01).
- BR-02 / BR-15: frozen baselines are reproducible from the raw store; 180 baseline rows equal SRC-03 Exp_baselines within 1e-6.
- FRs covered (BACKLOG.md): FR-052, FR-080, FR-081, FR-082, FR-083, FR-084, FR-085, FR-086.

## Referenced TRDs

- TRD 08 BSC-025..BSC-035 (ordinal, membership, freeze, forming, metadata, exclusions, never recomputed, feature and composite statistics, 20 rows, zero spread), BSC-040..BSC-043 (late records' own status, isolation, no imputation, multiple sessions per day), §4.6, §4.7, §4.9, §4.10, §4.11 worked example.
- TRD 07 ANL-024..ANL-027 (late-arrival detection, invisibility, rebuild reproducibility, out-of-order but not late), ANL-037 (engine side of `frozen_baselines`, `baseline_mismatch`), §4.2 (`build_baselines` signature), §4.3 (`Baseline`, `AdjustedRecord`), §4.4 (`BaselineMembership`, `EpochSummary`), §4.5 step 5.
- TRD 06 DB-016 (persisted baseline kept; `late_arrival` warning detail "epoch <n>").
- TRD 13 Table 4.3-A BL-01..BL-07, PIP-04; TRD 07 AC-ANL-05; TRD 08 AC-BSC-02, AC-BSC-05, AC-BSC-07, AC-BSC-08; TRD 14 VC-R07, VC-R08, VC-R10 (including VC-R10-FRZ), VC-G05.
- TRD 25 AGT-041, AGT-042, AGT-051; TRD 24 D-10, D-57, ASM-07, OQ-10.

## Scope

- `analytics/baseline_builder.py::build_baselines(rows: Sequence[AdjustedRecord], config) -> tuple[list[Baseline], dict[EpochKey, BaselineMembership]]`, including the baseline ordinal and `in_baseline` flags that the orchestrator writes into `AdjustedRecord`.
- Per-feature baselines (19) and the composite baseline, which needs the per-feature unsigned z and signed composite mean of BSC-032; this feature therefore delivers `zscore_calculator.feature_z` and `composite_score.composite_raw` in their owning modules (ANL-004), and FEAT-046 builds the scoring stage on them.
- Engine use of `frozen_baselines`: score against persisted rows and emit `baseline_mismatch` when recomputation differs.
- Late-arrival classification (`detect_late_arrivals`, TRD 07 §4.5 step 5, hosted in `analytics/pipeline.py`, which owns late-arrival detection per TRD 07 §4.2) and the own-status rule for late records (late reason appended).
- `zero_spread` warning for composite features.
- Unit tests `tests/unit/analytics/test_baseline_builder.py` and the late-arrival cases in `tests/unit/analytics/test_pipeline.py`.

## Out of Scope

- Scoring post-freeze sessions and `composite_z` (FEAT-046); CUSUM (FEAT-047).
- Wiring all stages into `run_pipeline` (FEAT-052) and persisting baselines insert-only (FEAT-053, ANL-037 persistence side, DB-016 row handling, DB-017 renumbering block).
- The operator rebuild that may recompute frozen baselines after an algorithm-key change (FEAT-055, ANL-032).
- Any late-arrival policy other than the MVP default (OQ-10).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-045-FR-01 | For each (resident, epoch) the usable, non-late sessions shall be numbered 1, 2, … in `(timestamp_utc, arrival_seq)` order (`baseline_ordinal`); the count restarts at 1 in every epoch. | BSC-025, BSC-010; FR-052 |
| FEAT-045-FR-02 | The baseline shall consist of the sessions with ordinal ≤ N (`baseline_n`; `in_baseline = true`); it forms when the N-th usable session exists and is then frozen — later sessions never change it. | BSC-026, AGT-051; FR-080, FR-083 |
| FEAT-045-FR-03 | Set-aside, quarantined, duplicate and late records and missing days shall never count toward N. | BSC-029 |
| FEAT-045-FR-04 | An epoch with fewer than N usable sessions shall produce `BaselineMembership(formed=False, usable_count=n)`, no `Baseline` rows and no scored session, without raising; progress is "n of N". | BSC-027, ANL-019; FR-085 |
| FEAT-045-FR-05 | For each formed epoch and each of the 19 features, a `Baseline` shall hold median, MAD, robust spread and `floor_applied` from `robust(adjusted values of the N baseline sessions, floor_f, mad_scale)` with floor 0.5 for number_of_pauses and 0 for the others. | BSC-031, AGT-042; FR-081 |
| FEAT-045-FR-06 | `composite_raw(s)` = (1/7) Σ over the 7 composite features in canonical order of sign_f × (a_f(s) − median_f) / spread_f; the composite baseline shall be `robust(composite_raw of the N baseline sessions, composite_floor 0.1, mad_scale)` stored as `feature_key = "composite"`. | BSC-032, BSC-033; FR-082 |
| FEAT-045-FR-07 | Each formed resident-epoch shall produce exactly 20 `Baseline` rows (19 features + composite) with `n_sessions` = N, `first_session_id` (ordinal 1), `frozen_after_session_id` (ordinal N), `frozen_at` = `timestamp_utc` of the frozen-after session, `device_code` of the epoch. | BSC-028, BSC-034; FR-086 |
| FEAT-045-FR-08 | If a composite feature's robust spread is 0, its z shall be 0.0 for every session of that epoch and one `RunWarning(code="zero_spread", detail=<feature_key>)` shall be emitted; the 12 non-composite features may have spread 0 without warning. | BSC-035 |
| FEAT-045-FR-09 | When `frozen_baselines` contains an epoch, the engine shall use the persisted rows; if recomputed values differ by more than 1e-12 or the membership (`first_session_id`, `frozen_after_session_id`, `n_sessions`) differs, it shall emit `RunWarning(code="baseline_mismatch")` and keep the persisted values. | ANL-037 (engine side), BSC-030, ASM-07 |
| FEAT-045-FR-10 | A non-duplicate record R shall be `late_arrival` when (a) a non-duplicate record of the same resident with smaller `arrival_seq` has a later `timestamp_utc`, and (b) on the prefix P of non-duplicate non-late records with smaller `arrival_seq`, either (b1) stages 1–8 yield a formed baseline whose frozen-after session is later than R, or (b2) R's epoch key differs from both neighbours in P; records are evaluated in `arrival_seq` order. | ANL-024, OQ-10 |
| FEAT-045-FR-11 | A late record shall be invisible to every other record (no epoch start or split, no screen reference, no baseline membership, no score, no tally update) but shall still pass the gate and its own speaker screen, count for the day ledger, and produce `RunWarning(code="late_arrival")`; it is `usable` or `quarantined` with `in_baseline = false`, no ordinal, the reason "late arrival (not used for baseline or scores)" appended last, or keeps only its quality reasons when set aside. | ANL-025, BSC-040, BSC-041, D-57; FR-084 |
| FEAT-045-FR-12 | Records that are out of order but not late shall be processed in timestamp order like any other record. | ANL-027 |
| FEAT-045-FR-13 | Late classification shall depend only on raw-store content and `arrival_seq`, so a rebuild reproduces the baselines persisted before the late record arrived. | ANL-026, D-10 |
| FEAT-045-FR-14 | The engine shall never impute, carry forward or interpolate values and shall process several records of one resident on one local day as separate sessions in time order. | BSC-042, BSC-043 |

## Inputs

- `Sequence[AdjustedRecord]` after the speaker screen and morning adjustment (statuses, adjusted values, epochs, late flag).
- `PipelineConfig` (`baseline_n`, `mad_scale`, `pause_floor`, `composite_floor`, `features`).
- Optional `frozen_baselines: Mapping[EpochKey, tuple[Baseline, ...]]` (persisted rows passed by the runner).

## Outputs

- `list[Baseline]` (20 per formed epoch), `dict[EpochKey, BaselineMembership]` (session ids in time order, formed flag, usable count), ordinal and `in_baseline` per session.
- The late set for the orchestrator; `RunWarning`s `late_arrival`, `zero_spread`, `baseline_mismatch`.

## Data Flow

1. `run_pipeline` step 5 (FEAT-052) calls `detect_late_arrivals(screened, config)` on the gate output; the late set is passed to epoch assignment and the screen.
2. Step 8 calls `build_baselines(adjusted, config)`: group usable non-late sessions per (resident, epoch), number them, take the first N, compute 19 feature baselines with `robust`, then each baseline session's `composite_raw`, then the composite baseline.
3. If `frozen_baselines` has the epoch, compare and keep the persisted rows (warning on mismatch).
4. Baselines feed scoring (FEAT-046); membership feeds `EpochSummary` and the forming progress shown by the API.

## Dependencies

- FEAT-044 (Speaker screen): final `usable` / `quarantined` statuses that define baseline membership (and transitively FEAT-042 epochs, FEAT-043 adjusted values, FEAT-040 `robust` and config).
- Downstream: FEAT-046 (scoring), FEAT-049/FEAT-050 (forming state for data alerts via `EpochSummary`), FEAT-052, FEAT-053.

## Database Impact

None directly. The runner inserts the 20 `baselines` rows once per epoch (insert-only, `baselines_epoch_feature_uq`), stores `processed_sessions.baseline_ordinal`, `in_baseline`, `late_arrival` and appends `late_arrival` warnings to `pipeline_runs.warnings` (FEAT-053, DB-016).

## API Impact

None directly; baselines are read by `GET /analytics/baselines` (FEAT-034) and the detail baseline line (FEAT-028).

## Frontend Impact

None.

## Analytics Impact

- Algorithms: first-N membership, robust statistics with floors, signed composite mean, robust composite baseline with floor 0.1, freeze; late-arrival detection by prefix replay of stages 1–8.
- Stage 6 of ANL-006 (`baseline`, LOG-063).

## Security Requirements

None specific (pure functions).

## Error Handling

- Forming epochs, zero usable sessions, residents with only late or duplicate records → valid results, no exception (ANL-019).
- Zero composite spread → z 0 and `zero_spread` warning (no division error).
- Persisted vs recomputed mismatch → keep persisted, warn `baseline_mismatch` (logged at ERROR by the runner, ANL-053).

## Logging Requirements

None in `analytics/` (LOG-006); warnings are returned as `RunWarning` data.

## Testing Requirements

- Unit (`tests/unit/analytics/test_baseline_builder.py`, marker `unit`): BL-01..BL-07; R09 worked example (TRD 08 §4.11: loudness median −22.405, MAD 1.45, spread 2.149770; composite median 0.038219, MAD 0.359758, spread 0.533378) (AC-BSC-06 baseline part); AC-BSC-07 zero spread warning; AC-BSC-08 later values never change the baseline; `frozen_baselines` mismatch warning.
- Unit (`tests/unit/analytics/test_pipeline.py` late-arrival cases): PIP-04; AC-ANL-05 fixture (R01 day 10 re-sent as `R01-20261010-02` after all other R01 records → `late_arrival` warning, unchanged R01 baselines and scores, status `usable`, `in_baseline` false); epoch-key late case (b2).
- Validation (FEAT-059): VC-G05 (180 rows; `floor_applied` on 8 number_of_pauses rows), VC-R07 (epoch 1 not formed with 12 usable; epoch 2 frozen after R07-20261028-01), VC-R08 (forming 13 of 16, no rows), VC-R10-FRZ (baseline unchanged by drift).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-045-AC-01 | 15 usable sessions → `formed` false, `usable_count` 15, no rows, no exception; 16 → frozen after the 16th session_id with `n_sessions` 16. | BL-01, BL-02 |
| FEAT-045-AC-02 | With 20 usable sessions, sessions 17–20 do not change any baseline statistic; set-aside and quarantined sessions interleaved are excluded from membership and ordinal. | BL-03, BL-04, AC-BSC-08 |
| FEAT-045-AC-03 | A formed epoch yields 20 rows; the composite row uses floor 0.1, number_of_pauses floor 0.5, other floors 0; morning sessions enter with adjusted values. | BL-05, BL-06, BSC-034 |
| FEAT-045-AC-04 | The `production` profile uses baseline_n 30. | BL-07 |
| FEAT-045-AC-05 | The R09 epoch 1 baseline reproduces loudness median −22.405, MAD 1.45, spread 2.149770 and composite median 0.038219, MAD 0.359758, spread 0.533378 (±1e-6). | AC-BSC-06, TRD 08 §4.11 |
| FEAT-045-AC-06 | A baseline with 16 identical voiced_fraction values yields z_voiced_fraction 0.0 for later sessions and exactly one `zero_spread` warning. | AC-BSC-07, BSC-035 |
| FEAT-045-AC-07 | The AC-ANL-05 late-arrival fixture yields a `late_arrival` warning, unchanged R01 baselines and scores, and the late record `usable` with `in_baseline` false and reason "late arrival (not used for baseline or scores)". | AC-ANL-05, PIP-04, BSC-040 |
| FEAT-045-AC-08 | On SRC-05, the engine produces exactly 180 baseline rows equal to Exp_baselines within 1e-6 with exact `floor_applied`, `n_sessions`, first and frozen-after session ids; R08 and R07 epoch 1 produce none. | AC-BSC-02, AC-BSC-05, VC-G05 |

## Definition of Done

- `build_baselines`, `feature_z`, `composite_raw` and `detect_late_arrivals` implemented; BL-01..BL-07 and PIP-04 pass (TST-020); `tests/unit/analytics/test_baseline_builder.py` exists (TST-011).
- VC-G05, VC-R07, VC-R08, VC-R10 pass in the validation suite (FEAT-059).
- Sequencing note below recorded in the batch report.

## Implementation Notes

- Medians with `numpy.median` on float64 (even N = 16 and 30 on purpose, AGT-041); spread `max(mad × 1.4826, floor)`, `floor_applied` strict (AGT-042).
- Compute the composite baseline from the baseline sessions' own `composite_raw` values using the just-built feature baselines, not from per-feature MADs (TRD 08 §8).
- Sum signed z in canonical order (ANL-022) and never round intermediates (AGT-054).
- Late detection reruns stages 1–8 on a prefix once per out-of-order record (ANL-050); SRC-05 has no late record, so test the slow path with the dedicated fixture.
- Backlog sequencing observation: BSC-032/BSC-033 need `feature_z` and `composite_raw` to build the composite baseline, but BACKLOG assigns `zscore_calculator.py` and `composite_score.py` to FEAT-046, which depends on this feature. To avoid duplicated stage logic (ANL-004) this feature implements those two functions in their owning modules; FEAT-046 adds `composite_z` and the scoring of post-freeze sessions.
- `detect_late_arrivals` is hosted in `analytics/pipeline.py` because TRD 07 §4.2 gives late-arrival detection to that module; FEAT-052 calls it as step 5.
