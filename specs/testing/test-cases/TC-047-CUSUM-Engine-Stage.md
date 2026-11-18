# CUSUM engine stage

## Feature Description

FEAT-047 implements `analytics/cusum_engine.py::run_cusum(rows, config)`, the "running change tally". Per (resident, epoch), in time order (`scored_ordinal`), the tally is S_i = max(0, S_{i−1} + composite_z_i − k) with S_0 = 0, k = `cusum_k` (0.5) and h = `cusum_h` (5.0), computed in float64 without rounding. Only scored sessions update it; set-aside, quarantined, duplicate and late records, baseline sessions and missing days leave it unchanged. Each epoch starts its own tally at 0. The first session with S ≥ h (inclusive) has `alarm_state` "rings", every later scored session of the epoch is "on" regardless of S, every earlier one "off"; nothing but a new epoch resets the tally or state (reviews and snoozes are not inputs). The per-epoch facts are `current_tally` (S of the last scored session, 0.0 if none), `last_scored_session_id`, `alarm_on` and `first_alarm_session_id`. On SRC-05 R09 rings on R09-20261021-01 at 5.431965 and R10 on R10-20261024-01 at 5.972050; the 98 alarm states are off 81, on 15, rings 2.

## Preconditions

- Local development stack per `README.md` quick start; Python REPL started from the repository root with `import sys; sys.path.insert(0, ".")`.
- REPL helpers: `from analytics.cusum_engine import run_cusum; from analytics.config import TEST_V0_1 as C, ScoreRow; from datetime import date; import dataclasses` and `def rows(zs, ep=1, tag="S"): return [ScoreRow(f"{tag}{i}", "x", "R01", ep, date(2026, 10, 1), False, {}, 0.0, z, scored_ordinal=i + 1) for i, z in enumerate(zs)]` and `def tally(zs): return [(round(r.cusum_tally, 6), r.alarm_state) for r in run_cusum(rows(zs), C)]`.
- SRC-05 helpers: `from tests.unit.analytics.src05 import records, result, RESIDENTS, ASSIGNMENTS, AS_OF; from analytics.pipeline import run_pipeline`.
- Local PostgreSQL freshly seeded with `python -m backend.cli seed test_v0_1 --reset`; `psql` read access.
- Local Docker Compose (demo profile) with the same data; ADMIN_TOKEN and CLINICIAN_TOKEN from `POST /api/v1/auth/login` (`SEED_*` passwords).

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-047-01 | composite_z [3.0, 3.0] gives tallies [2.5, 5.0] and states [off, rings] | High | Analytics |
| TC-047-02 | composite_z [−10.0] gives 0.0; [0.5] × 10 stays 0.0 | High | Analytics |
| TC-047-03 | composite_z [6.0, −20.0, 6.0] gives [5.5, 0.0, 5.5], [rings, on, on], one "rings" | High | Analytics |
| TC-047-04 | Two epochs of one resident each start at tally 0 | High | Analytics |
| TC-047-05 | R09 series reproduces `Exp_scores`; rings at the 5th scored session with 5.431965; epoch facts | High | Database |
| TC-047-06 | SRC-05: all 98 tallies match; alarm states off 81, on 15, rings 2 | High | Database |
| TC-047-07 | R10 rings at R10-20261024-01 with 5.972050; R05 peaks at 4.005975 and never rings | High | Database |
| TC-047-08 | Non-scored days between scored sessions leave the tally unchanged | High | Analytics |
| TC-047-09 | k and h come from the configuration | Medium | Analytics |
| TC-047-10 | Reviews and snoozes do not reset the tally; a rerun reproduces every tally | High | Database |
| TC-047-11 | API shows current tallies and alarm states | Medium | API |
| TC-047-12 | Empty groups raise no error; the tally is never negative | Medium | Negative |

### TC-047-01 [3.0, 3.0]

| Step | Action | Expected Result |
|---|---|---|
| 1 | `print(tally([3.0, 3.0]))` | `[(2.5, 'off'), (5.0, 'rings')]` (5.0 ≥ h rings: inclusive) |
| 2 | `pytest -m unit tests/unit/analytics/test_cusum_engine.py -v` | `test_tally_and_states`, `test_epochs_have_their_own_tally`, `test_src05_alarms` PASSED |

### TC-047-02 Clamping at zero

| Step | Action | Expected Result |
|---|---|---|
| 1 | `print(tally([-10.0]))` | `[(0.0, 'off')]` |
| 2 | `print(tally([0.5] * 10))` | Ten times `(0.0, 'off')` (k = 0.5 cancels each step) |

### TC-047-03 [6.0, −20.0, 6.0]

| Step | Action | Expected Result |
|---|---|---|
| 1 | `out = tally([6.0, -20.0, 6.0]); print(out, sum(1 for _, s in out if s == "rings"))` | `[(5.5, 'rings'), (0.0, 'on'), (5.5, 'on')] 1` — the state stays "on" after the tally drops below h and there is no second "rings" |

### TC-047-04 Two epochs each start at 0

| Step | Action | Expected Result |
|---|---|---|
| 1 | `out = run_cusum(rows([6.0], 1, "A") + rows([1.0], 2, "B"), C); print([(r.epoch_number, r.cusum_tally, r.alarm_state) for r in out])` | `[(1, 5.5, 'rings'), (2, 0.5, 'off')]` (epoch 2 starts from 0, not from 5.5) |

### TC-047-05 R09 series and epoch facts

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT p.session_id, s.cusum_tally, s.alarm_state FROM scores s JOIN processed_sessions p ON p.id = s.processed_session_id JOIN residents r ON r.id = s.resident_id WHERE r.resident_code = 'R09' ORDER BY p.timestamp_utc;` | 14 rows; first five: R09-20261017-01 3.245474 off; R09-20261018-01 2.609763 off; R09-20261019-01 1.773061 off; R09-20261020-01 1.643658 off; R09-20261021-01 5.431965 rings; then R09-20261022-01 7.959257 on … R09-20261030-01 26.830256 on (±1e-6, `Exp_scores`) |
| 2 | `SELECT c.current_tally, c.last_scored_session_id, c.alarm_on FROM cusum_state c JOIN residents r ON r.id = c.resident_id WHERE r.resident_code = 'R09';` | 26.830256 (±1e-6), R09-20261030-01, true |
| 3 | REPL: `e = next(x for x in result().epochs if x.resident_code == "R09"); print(e.current_tally, e.alarm_on, e.first_alarm_session_id)` | `26.83025585245945 True R09-20261021-01` |
| 4 | `pytest -m validation tests/validation/test_r09_step_change.py -v` | All PASSED (VC-R09) |

### TC-047-06 All 98 tallies and alarm states

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT alarm_state, count(*) FROM scores GROUP BY 1 ORDER BY 1;` | off 81, rings 2, on 15 |
| 2 | `pytest -m validation tests/validation/test_global_checks.py -k vc_g06 -v` | `test_vc_g06_scores` PASSED (all 98 `cusum_tally` within 1e-6; `alarm` "RINGS (first crossing)" ↔ `rings`, "on", "off" exact) |
| 3 | `SELECT p.session_id FROM scores s JOIN processed_sessions p ON p.id = s.processed_session_id WHERE s.alarm_state = 'rings' ORDER BY 1;` | R09-20261021-01, R10-20261024-01 |

### TC-047-07 R10 ring and R05 near-miss

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT p.session_id, s.cusum_tally FROM scores s JOIN processed_sessions p ON p.id = s.processed_session_id WHERE p.session_id IN ('R10-20261023-01','R10-20261024-01');` | R10-20261023-01 4.386532 (off); R10-20261024-01 5.972050 (rings) (±1e-6) |
| 2 | `SELECT c.current_tally, c.last_scored_session_id, c.alarm_on FROM cusum_state c JOIN residents r ON r.id = c.resident_id WHERE r.resident_code = 'R10';` | 13.418183 (±1e-6), R10-20261030-01, true |
| 3 | `SELECT max(s.cusum_tally) FROM scores s JOIN residents r ON r.id = s.resident_id WHERE r.resident_code = 'R05';` | 4.005975 (±1e-6, R05-20261026-01); no R05 row is `rings` or `on` |
| 4 | `pytest -m validation tests/validation/test_r10_gradual_drift.py -v` | All PASSED (VC-R10) |

### TC-047-08 Non-scored days leave the tally unchanged

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT p.session_id, s.cusum_tally FROM scores s JOIN processed_sessions p ON p.id = s.processed_session_id WHERE p.session_id IN ('R05-20261021-01','R05-20261023-01');` | R05-20261021-01 0.047607; R05-20261023-01 1.452260 (±1e-6) — the quarantined day 22 between them adds no step (1.452260 = max(0, 0.047607 + composite_z of R05-20261023-01 − 0.5)) |
| 2 | Verify step 1 arithmetic: `SELECT round((0.047607 + s.composite_z - 0.5)::numeric, 6) FROM scores s JOIN processed_sessions p ON p.id = s.processed_session_id WHERE p.session_id = 'R05-20261023-01';` | 1.452260 (±1e-6) |
| 3 | For R02 (missing days 9, 10, 17, 23) and R03 (set-aside days 22, 26): compare consecutive scored tallies with `Exp_scores` | Each tally equals the previous scored tally + composite_z − 0.5 (clamped at 0); no decay or zero insertion for gaps |
| 4 | `SELECT count(*) FROM scores s JOIN processed_sessions p ON p.id = s.processed_session_id WHERE p.in_baseline;` | 0 (baseline sessions never update the tally) |

### TC-047-09 k and h from configuration

| Step | Action | Expected Result |
|---|---|---|
| 1 | `print(C.cusum_k, C.cusum_h)` | `0.5 5.0` |
| 2 | `a = run_pipeline(records(), RESIDENTS, ASSIGNMENTS, dataclasses.replace(C, cusum_h=4.0), AS_OF); print([(x.resident_code, x.session_id) for x in a.alerts])` | `[('R05', 'R05-20261026-01'), ('R09', 'R09-20261021-01'), ('R10', 'R10-20261023-01')]` (with h = 4.0 R05 rings at 4.005975 and R10 rings one day earlier at 4.386532) |
| 3 | `SELECT value FROM config_parameters WHERE profile = 'test_v0_1' AND key IN ('cusum_k','cusum_h') ORDER BY key;` | 5.0 (cusum_h), 0.5 (cusum_k) |

### TC-047-10 No reset by review or snooze; rerun reproduces

| Step | Action | Expected Result |
|---|---|---|
| 1 | Note `SELECT p.session_id, s.cusum_tally, s.alarm_state FROM scores s JOIN processed_sessions p ON p.id = s.processed_session_id ORDER BY 1;` (98 rows) | Baseline list |
| 2 | As clinician `POST /api/v1/alerts/<R09 alert id>/reviews` body `{"outcome": "known_cause"}` and `POST /api/v1/alerts/<R09 alert id>/snooze` body `{}` | 201, 200 |
| 3 | Admin `POST /api/v1/pipeline/run` body `{"scope": "all", "profile": "test_v0_1", "as_of": "2026-10-30T15:00:00-05:00"}`; wait for `succeeded` via `GET /api/v1/pipeline/runs/{id}` | 202, then `succeeded` |
| 4 | Repeat the query of step 1 | Identical 98 rows (R09 still 26.830256 / `on` at R09-20261030-01) |
| 5 | REPL: `print(run_pipeline(records(), RESIDENTS, ASSIGNMENTS, C, AS_OF).scores == result().scores)` | `True` |

### TC-047-11 API read-out

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/alerts?status=open` as admin | 2 alerts; R09 `current_tally` 26.830256 and R10 13.418183 (±1e-6); `cusum_value` 5.431965 and 5.972050 |
| 2 | `GET /api/v1/scores?resident_code=R10` | 14 items; R10-20261024-01 `alarm_state` "rings", items after it "on", items before it "off" |
| 3 | `GET /api/v1/residents/R09` | `current_tally` 26.830256 (±1e-6) |
| 4 | `SELECT count(*) FROM cusum_state;` | 11 (one row per epoch, including forming epochs) |

### TC-047-12 Empty groups and non-negative tally

| Step | Action | Expected Result |
|---|---|---|
| 1 | `print(run_cusum([], C))` | `[]`, no exception |
| 2 | `SELECT count(*) FROM scores WHERE cusum_tally < 0; SELECT count(*) FROM cusum_state WHERE current_tally < 0;` | 0, 0 |
| 3 | `SELECT c.current_tally, c.last_scored_session_id, c.alarm_on FROM cusum_state c JOIN residents r ON r.id = c.resident_id WHERE r.resident_code = 'R08';` | One row: 0.0, NULL, false (forming epoch, nothing scored) |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/scores` | `cusum_tally` and `alarm_state` per scored session as in `Exp_scores` |
| 2 | `GET /api/v1/alerts?status=open` | `current_tally` from `cusum_state` (TC-047-11) |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `scores.alarm_state` distribution | off 81, on 15, rings 2 |
| 2 | `cusum_state` for R09 / R10 | 26.830256 / 13.418183, `alarm_on` true, last scored R09-20261030-01 / R10-20261030-01 |
| 3 | Tallies ≥ 0 (`scores_cusum_ck`, `cusum_state_tally_ck`) | No violation |
| 4 | Exactly one `rings` per alarmed epoch | `SELECT epoch_id, count(*) FROM scores WHERE alarm_state = 'rings' GROUP BY 1 HAVING count(*) > 1;` → 0 rows |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Large negative composite_z | Tally clamps at 0.0 (TC-047-02) |
| 2 | Tally falls below h after ringing | State stays "on"; no second "rings" (TC-047-03) |
| 3 | Review and snooze | No reset (TC-047-10) |
| 4 | Empty group | No error (TC-047-12) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-047-AC-01 | [3.0, 3.0] → tallies [2.5, 5.0], states [off, rings] | TC-047-01 |
| FEAT-047-AC-02 | [−10.0] → 0.0; [0.5] × 10 → 0.0 throughout | TC-047-02 |
| FEAT-047-AC-03 | [6.0, −20.0, 6.0] → [5.5, 0.0, 5.5], [rings, on, on], exactly one "rings" | TC-047-03 |
| FEAT-047-AC-04 | Two epochs of one resident each start at tally 0 | TC-047-04 |
| FEAT-047-AC-05 | R09 tallies equal `Exp_scores` (±1e-6), rings at the 5th scored session with 5.431965; facts `current_tally` 26.830256, `alarm_on` true, `first_alarm_session_id` R09-20261021-01 | TC-047-05 |
| FEAT-047-AC-06 | SRC-05: all 98 tallies within 1e-6; states off 81, on 15, rings 2 | TC-047-06, TC-047-07 |

## Test Data Requirements

- SRC-05 seeded with `test_v0_1`; SRC-03 `Exp_scores` (`cusum_tally`, `alarm`).
- Synthetic `ScoreRow` sequences built in the REPL (R01, epochs 1 and 2).
- One open R09 alert id from `GET /api/v1/alerts?status=open`.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-047-FR-01 | FEAT-047 | TC-047-01, TC-047-02, TC-047-05 |
| FEAT-047-FR-02 | FEAT-047 | TC-047-09 |
| FEAT-047-FR-03 | FEAT-047 | TC-047-05, TC-047-08 |
| FEAT-047-FR-04 | FEAT-047 | TC-047-08 |
| FEAT-047-FR-05 | FEAT-047 | TC-047-04 |
| FEAT-047-FR-06 | FEAT-047 | TC-047-01, TC-047-03, TC-047-06 |
| FEAT-047-FR-07 | FEAT-047 | TC-047-10 |
| FEAT-047-FR-08 | FEAT-047 | TC-047-05, TC-047-07, TC-047-12 |
| FEAT-047-FR-09 | FEAT-047 | TC-047-10 |
| TRD 09 CUS-001..CUS-010 | FEAT-047 | TC-047-01..TC-047-10 |
| TRD 09 AC-CUS-01, AC-CUS-04, AC-CUS-05 | FEAT-047 | TC-047-06, TC-047-03, TC-047-08 |
| TRD 13 CUS-01..CUS-07 | FEAT-047 | TC-047-01..TC-047-05, TC-047-08 |
| TRD 14 VC-G06, VC-R09, VC-R10 | FEAT-047 | TC-047-06, TC-047-05, TC-047-07 |
| TRD 13 TST-022 | FEAT-047 | TC-047-12 |
| FR-044, FR-065, FR-100..FR-103, FR-105 | FEAT-047 | TC-047-01..TC-047-08 |
