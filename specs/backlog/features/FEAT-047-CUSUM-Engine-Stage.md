# FEAT-047 CUSUM engine stage

| Field | Value |
|---|---|
| Epic | Analytics Engine |
| Build phase | Phase 6 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-046 |
| Status | Not Started |

## Purpose

Turn the daily composite scores into the "running change tally" that decides when an alarm rings: a one-sided upper CUSUM per resident-epoch, S = max(0, S + composite_z − 0.5), starting at 0 with the first scored session. A single odd day does not raise a flag; a sustained shift does. The first session whose tally reaches 5.0 "rings", every later session of the epoch is "on" (there is no reset in v0.1), and days that are set aside, quarantined, duplicated or missing leave the tally unchanged. R09 rings on Oct 21 at 5.431965 and R10 on Oct 24.

## Business Context

- BR-11 (alarm when a sustained change crosses a fixed line; alarm persists): tally, crossing, alarm states, no reset.
- BR-06 (missing days are not data): missing and non-usable days leave the tally unchanged.
- BR-15: all 98 Exp_scores tallies within 1e-6 and alarm states exact (off 81, on 15, RINGS 2).
- FRs covered (BACKLOG.md): FR-044, FR-065, FR-100, FR-101, FR-102, FR-103, FR-105.

## Referenced TRDs

- TRD 09 CUS-001..CUS-010 (tally formula, k and h from config, start, unchanged on non-scored days, per-epoch tally, inclusive alarm condition, alarm states, no reset, `cusum_state` facts, rebuild reproducibility), §4.1 pseudocode, §4.5 reference tables.
- TRD 07 §4.2 (`run_cusum` signature), §4.3 (`ScoreRow`), §4.4 (`EpochSummary.current_tally`, `last_scored_session_id`, `alarm_on`, `first_alarm_session_id`), §4.5 step 10.
- TRD 13 Table 4.3-A CUS-01..CUS-07; TRD 09 AC-CUS-01, AC-CUS-04, AC-CUS-05; TRD 14 VC-G06, VC-R09, VC-R10; TST-022 (tally ≥ 0 property).
- TRD 25 AGT-047, AGT-048, AGT-058.

## Scope

- `analytics/cusum_engine.py::run_cusum(rows: Sequence[ScoreRow], config) -> list[ScoreRow]` filling `cusum_tally` and `alarm_state`.
- The per-epoch CUSUM facts (current tally, last scored session, alarm flag, first alarm session) derived from the `run_cusum` output for `EpochSummary` and the `cusum_state` table.
- Unit tests `tests/unit/analytics/test_cusum_engine.py`.

## Out of Scope

- Alert events and closure (FEAT-048); persistence of `scores` and `cusum_state` (FEAT-053).
- Any tally reset on review, snooze or note (forbidden in v0.1, OQ-05).
- Calibration of k and h (OQ-13, future FEAT-093).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-047-FR-01 | For each (resident, epoch) group in time order, the tally shall be S_i = max(0, S_{i−1} + composite_z_i − k) with S_0 = 0, computed in float64 without rounding. | CUS-001, AGT-047; FR-100 |
| FEAT-047-FR-02 | k shall be read from `config.cusum_k` (0.5) and h from `config.cusum_h` (5.0). | CUS-002 |
| FEAT-047-FR-03 | The tally shall start at 0 with the first scored session of an epoch; baseline sessions shall not update it. | CUS-003 |
| FEAT-047-FR-04 | Only scored sessions shall update the tally; set-aside, quarantined, duplicate and late records and missing days leave it unchanged (no decay, no zero insertion). | CUS-004, AGT-047; FR-044, FR-065, FR-101 |
| FEAT-047-FR-05 | Each epoch shall have its own tally starting at 0 after its own baseline freezes; nothing carries over between epochs. | CUS-005 |
| FEAT-047-FR-06 | The alarm condition shall be S_i ≥ h (inclusive); the first such session has `alarm_state` "rings", every later scored session of the epoch "on" regardless of S, every earlier one "off". | CUS-006, CUS-007, AGT-048; FR-102, FR-103 |
| FEAT-047-FR-07 | The engine shall not reset the tally or alarm state for any reason other than a new epoch; reviews and snoozes are not inputs to `run_cusum`. | CUS-008, AGT-058 |
| FEAT-047-FR-08 | Per epoch, the CUSUM facts shall be: `current_tally` = S of the last scored session (0.0 if none), `last_scored_session_id`, `alarm_on` = a crossing occurred, `first_alarm_session_id` = the "rings" session (None if none). | CUS-009; TRD 07 §4.4; FR-105 |
| FEAT-047-FR-09 | Because the tally is a pure function of the ordered composite_z sequence, a rebuild shall reproduce every `cusum_tally` and `alarm_state` exactly. | CUS-010, ANL-020 |

## Inputs

- `ScoreRow`s with `composite_z` per formed (resident, epoch), in or out of time order.
- `PipelineConfig` (`cusum_k`, `cusum_h`).

## Outputs

- New `ScoreRow`s with `cusum_tally` and `alarm_state`; per-epoch facts for `EpochSummary`.

## Data Flow

1. `run_pipeline` step 10 (FEAT-052) passes the ScoreRows grouped per (resident, epoch).
2. `run_cusum` sorts each group by `scored_ordinal` (time order), runs the loop of TRD 09 §4.1, emits rows.
3. Step 11 builds `EpochSummary` with the CUSUM facts; step 12 (FEAT-048) creates alert events from "rings" rows; the runner writes `scores.cusum_tally`, `scores.alarm_state` and `cusum_state`.

## Dependencies

- FEAT-046 (Z-score and composite scoring): `ScoreRow`s with `composite_z` and `scored_ordinal`.
- Downstream: FEAT-048 (alerts), FEAT-052, FEAT-053.

## Database Impact

None directly. The runner writes `scores.cusum_tally`, `scores.alarm_state` and one `cusum_state` row per epoch (`current_tally`, `last_scored_session_id`, `alarm_on`) (FEAT-053); TRD 20 `scores_cusum_ck` and `cusum_state_tally_ck` require tally ≥ 0.

## API Impact

None directly; read through `GET /scores` (FEAT-034), `current_tally` in `GET /alerts` and `/residents/{code}` (FEAT-030, FEAT-028).

## Frontend Impact

None.

## Analytics Impact

- Algorithm: one-sided upper CUSUM (k 0.5, h 5.0) with persistent alarm state; stage 8 of ANL-006 (`cusum`, LOG-063).

## Security Requirements

None specific (pure function).

## Error Handling

- Empty groups (forming epochs) produce no rows and no error; negative contributions clamp at 0 (CUS-02).

## Logging Requirements

None in `analytics/` (LOG-006).

## Testing Requirements

- Unit (`tests/unit/analytics/test_cusum_engine.py`, marker `unit`): CUS-01..CUS-07; AC-CUS-04 ([6.0, −10.0, 0.0] → [5.5, 0.0, 0.0], states [rings, on, on]); AC-CUS-05 (non-scored days between scored sessions change nothing); Hypothesis property tally ≥ 0 (TST-022); facts derivation (current tally, first alarm session).
- Validation (FEAT-059): VC-G06 alarm counts (off 81, on 15, RINGS 2), VC-R09 (first ring R09-20261021-01 at 5.431965), VC-R10 (first ring R10-20261024-01 at 5.972050), AC-CUS-01.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-047-AC-01 | composite_z [3.0, 3.0] gives tallies [2.5, 5.0] and states [off, rings]. | CUS-01, CUS-006 |
| FEAT-047-AC-02 | composite_z [−10.0] gives tally 0.0; [0.5] × 10 gives tally 0.0 throughout. | CUS-02, CUS-07 |
| FEAT-047-AC-03 | composite_z [6.0, −20.0, 6.0] gives tallies [5.5, 0.0, 5.5], states [rings, on, on] and exactly one "rings". | CUS-03, AGT-048 |
| FEAT-047-AC-04 | Two epochs of one resident each start at tally 0. | CUS-06, CUS-005 |
| FEAT-047-AC-05 | The R09 composite_z series reproduces the Exp_scores tallies within 1e-6 and rings at the 5th scored session with 5.431965; the epoch's facts are `current_tally` 26.830256, `alarm_on` true, `first_alarm_session_id` R09-20261021-01. | CUS-04, VC-R09, AC-CUS-02 |
| FEAT-047-AC-06 | On SRC-05 all 98 tallies match Exp_scores within 1e-6 and alarm states map exactly (off 81, on 15, rings 2). | AC-CUS-01, VC-G06 |

## Definition of Done

- `run_cusum` implemented with the binding signature; CUS-01..CUS-07 pass (TST-020); test file exists (TST-011).
- VC-R09, VC-R10 and AC-CUS-01 pass in the validation suite.

## Implementation Notes

- Implement with a plain Python float loop; do not vectorise with cumulative sums (the `max(0, ·)` makes it path dependent, TRD 09 §8).
- Keep "rings" as a state of the score row, not of the alert; alerts are created from the "rings" row (FEAT-048).
- `alarm_state` stays "on" after the first crossing even when S drops below h; never recompute it from S alone.
- Treat R05's near-miss (maximum 4.006) as a regression signal: a change that pushes R05 above 5.0 is wrong (TRD 09 §8).
- Sort by `scored_ordinal` (assigned in time order by FEAT-046) inside each group.
