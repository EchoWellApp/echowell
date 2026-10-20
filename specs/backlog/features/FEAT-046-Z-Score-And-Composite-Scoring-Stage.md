# FEAT-046 Z-score and composite scoring stage

| Field | Value |
|---|---|
| Epic | Analytics Engine |
| Build phase | Phase 6 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-045 |
| Status | Not Started |

## Purpose

Score every usable check-in that arrives after a resident's baseline has frozen: for each of the seven composite voice features compute how far the morning-adjusted value lies from the resident's own baseline in robust standard units (z), combine them with fixed signs into one daily composite score (positive = toward the depression-associated direction), and standardise that against the composite baseline (composite_z). These numbers feed the running change tally and are shown per measurement on the Resident detail page.

## Business Context

- BR-10 (daily deviation score from 7 features compared with the person's own baseline): unsigned z per feature, signed composite mean, composite z.
- BR-15: 98 scored rows equal SRC-03 Exp_scores within 1e-6 (R09-20261021-01 composite_raw 2.325508, composite_z 4.288307).
- FRs covered (BACKLOG.md): FR-090, FR-091, FR-092, FR-093, FR-094, FR-095.

## Referenced TRDs

- TRD 08 BSC-036..BSC-039 (which sessions are scored, unsigned stored z, composite_z, 12 features not scored), §4.8 pseudocode, §4.11 worked example, BSC-035 (z = 0 for zero spread).
- TRD 07 §4.2 (`feature_z`, `composite_raw`, `composite_z` signatures), §4.3 (`ScoreRow`), §4.5 step 9, ANL-022 (float64, canonical summation order).
- TRD 23 DME-002 (signs defined once), §4.5 (`scores.z` shape).
- TRD 13 Table 4.3-A Z-01, Z-02, CMP-01..CMP-03; TRD 08 AC-BSC-03, AC-BSC-06; TRD 14 VC-G06.
- TRD 25 AGT-054, AGT-055.

## Scope

- `analytics/composite_score.py::composite_z(raw: float, composite_baseline: Baseline) -> float`.
- The scoring of each usable, non-late session with `baseline_ordinal > N` in a formed epoch into a `ScoreRow` (7 unsigned `z_<feature>` values, `composite_raw`, `composite_z`, `local_date`, `is_morning`, `scored_ordinal`), using `zscore_calculator.feature_z` and `composite_score.composite_raw` delivered by FEAT-045.
- Unit tests `tests/unit/analytics/test_zscore_calculator.py`, `tests/unit/analytics/test_composite_score.py`.

## Out of Scope

- `feature_z` and `composite_raw` themselves (delivered with the composite baseline in FEAT-045).
- Tally and alarm state (FEAT-047); persistence of `scores` (FEAT-053); the 7-measurement API (FEAT-028).
- Any EWMA trend (OQ-18, future FEAT-096).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-046-FR-01 | Every usable, non-late session with `baseline_ordinal > N` in a formed epoch shall be scored exactly once, in `(timestamp_utc, arrival_seq)` order; no other session (baseline, set-aside, quarantined, duplicate, late, forming epoch) shall be scored. | BSC-036; FR-090 |
| FEAT-046-FR-02 | For each of the 7 composite features z_f = (adjusted value − baseline median_f) / baseline robust spread_f, stored unsigned as `z_<feature>` (z = 0.0 when the spread is 0, BSC-035). | BSC-037, BSC-035; FR-091 |
| FEAT-046-FR-03 | `composite_raw` = (1/7) × Σ sign_f × z_f over the 7 features summed in canonical order with signs loudness −1, phrase duration +1, speech rate −1, articulation rate −1, pauses +1, pause fraction +1, voiced fraction −1. | BSC-032, AGT-055, ANL-022; FR-092 |
| FEAT-046-FR-04 | `composite_z` = (composite_raw − composite baseline median) / composite baseline robust spread. | BSC-038; FR-093 |
| FEAT-046-FR-05 | Each `ScoreRow` shall carry `session_id`, `raw_session_id`, `resident_code`, `epoch_number`, `local_date`, `is_morning`, `z` (7 keys), `composite_raw`, `composite_z` and `scored_ordinal`; `cusum_tally` and `alarm_state` are filled by FEAT-047. | TRD 07 §4.3; FR-094 |
| FEAT-046-FR-06 | The 12 stored-not-scored features shall not be scored and shall never contribute to composite, tally or alarm. | BSC-039; FR-095 |
| FEAT-046-FR-07 | All arithmetic shall be float64 without rounding of intermediate or stored values. | ANL-022, AGT-054 |

## Inputs

- `AdjustedRecord`s with `baseline_ordinal`, `in_baseline`, `late_arrival`, adjusted values.
- `Baseline` rows (19 features + composite) per formed epoch (fresh or persisted `frozen_baselines`).
- `PipelineConfig` (`features`, signs).

## Outputs

- `ScoreRow`s per formed epoch in time order with z, composite_raw, composite_z (tally fields pending).

## Data Flow

1. `run_pipeline` step 9 (FEAT-052): for each formed (resident, epoch), iterate post-freeze usable non-late sessions in time order.
2. `feature_z(row, baselines, config)` → 7 unsigned z; `composite_raw(z, config)`; `composite_z(raw, composite_baseline)`.
3. ScoreRows go to `run_cusum` (FEAT-047), then to the runner's `scores` table.

## Dependencies

- FEAT-045 (Baseline builder): formed baselines, membership ordinals, `feature_z`, `composite_raw`.
- Downstream: FEAT-047 (CUSUM), FEAT-048 (leaning most uses signed z), FEAT-052.

## Database Impact

None directly. The runner writes `scores` (`z`, `composite_raw`, `composite_z`, `local_date`, `is_morning`, plus tally fields) (FEAT-053); TRD 20 `scores_z_ck` requires the 7 `z_*` keys.

## API Impact

None directly; read through `GET /scores` (FEAT-034) and `/features` (FEAT-028).

## Frontend Impact

None.

## Analytics Impact

- Algorithms: robust z against a frozen baseline; signed mean composite; robust standardisation of the composite.
- Stage 7 of ANL-006 (`scoring`, LOG-063).

## Security Requirements

None specific (pure functions).

## Error Handling

- Zero spread → z 0.0 (no exception); missing feature keys are contract violations rejected earlier (BSC-042).
- An epoch without a formed baseline yields no ScoreRows and no error.

## Logging Requirements

None in `analytics/` (LOG-006).

## Testing Requirements

- Unit (`tests/unit/analytics/test_zscore_calculator.py`, `test_composite_score.py`, marker `unit`): Z-01 (adj −27.0, median −29.925, spread 3.209829 → 0.9112635 ±1e-6), Z-02 (7 unsigned z keyed `z_<feature>`), CMP-01 (all z +1.0 → −1/7), CMP-02 (composite MAD 0 → spread 0.1, composite_z 5.0), CMP-03 (R09-20261017-01 composite_raw 2.035972, composite_z 3.745474); R09-20261021-01 worked example (TRD 08 §4.11).
- Validation (FEAT-059): VC-G06 (98 scored rows: R01 14, R02 8, R03 6, R04 14, R05 12, R06 14, R07 2, R08 0, R09 14, R10 14), AC-BSC-03.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-046-AC-01 | `feature_z` for adjusted −27.0 against median −29.925 and spread 3.209829 returns 0.9112635 (±1e-6), unsigned. | Z-01, BSC-037 |
| FEAT-046-AC-02 | With all seven unsigned z equal to +1.0, `composite_raw` returns −1/7; with composite_raw 0.5 and a composite baseline of median 0.0, MAD 0.0 (spread floored 0.1), `composite_z` returns 5.0. | CMP-01, CMP-02 |
| FEAT-046-AC-03 | R09-20261021-01 yields z loudness −2.737502, phrase 2.420232, speech rate −1.180359, articulation −1.584269, pauses 1.348982, pause fraction 2.285774, voiced −4.721435, composite_raw 2.325508 and composite_z 4.288307 (±1e-6). | AC-BSC-06, TRD 08 §4.11 |
| FEAT-046-AC-04 | On SRC-05 exactly 98 sessions are scored with the per-resident counts of VC-G06, and every `z_*`, `composite_raw`, `composite_z` and `morning` value equals Exp_scores (±1e-6, booleans exact). | VC-G06, AC-BSC-03 |
| FEAT-046-AC-05 | Changing a stored-not-scored feature value (e.g. `mfcc1`) of a scored session changes none of its ScoreRow values. | BSC-039, FR-095 |

## Definition of Done

- `composite_z` and the scoring loop implemented; Z-01, Z-02, CMP-01..CMP-03 pass (TST-020); test files exist (TST-011).
- VC-G06 and AC-BSC-03 pass in the validation suite (FEAT-059).

## Implementation Notes

- Store z unsigned exactly as Exp_scores; apply signs only inside `composite_raw` (TRD 19 §8, TDV-041).
- Use the composite baseline row (`feature_key = "composite"`) for `composite_z`; never recompute it from scored sessions.
- Iterate features in `COMPOSITE_KEYS` order for the sum so floating results are bit-identical across runs (ANL-020, ANL-022).
- When `frozen_baselines` are passed, score against the persisted rows (ANL-037), which FEAT-045 selects.
