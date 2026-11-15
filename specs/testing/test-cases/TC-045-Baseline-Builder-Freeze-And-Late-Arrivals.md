# Baseline builder, freeze and late arrivals

## Feature Description

FEAT-045 builds each resident's personal baseline per epoch (`analytics/baseline_builder.py::build_baselines`). Usable, non-late sessions are numbered 1, 2, … in `(timestamp_utc, arrival_seq)` order per epoch (`baseline_ordinal`, restarting in each epoch); the sessions with ordinal ≤ N (`baseline_n`: 16 in `test_v0_1`, 30 in `production`) form the baseline, which freezes when the N-th usable session exists and never changes afterwards. Set-aside, quarantined, duplicate and late records and missing days never count. For a formed epoch the engine writes 20 `Baseline` rows: 19 features with median, MAD, robust spread = max(MAD × 1.4826, floor) (floor 0.5 for number_of_pauses, 0 otherwise) and `floor_applied`, computed on adjusted values, plus a `composite` row built from the baseline sessions' own `composite_raw` with floor 0.1. An epoch with fewer than N usable sessions reports "n of N", produces no rows and no scores. A zero composite-feature spread gives z 0.0 and one `zero_spread` warning; persisted `frozen_baselines` win over a recomputation (warning `baseline_mismatch`). Late-arriving records that would have changed a frozen baseline or renumbered epochs are classified `late_arrival`, kept out of every baseline, reference, score and tally, given the appended reason "late arrival (not used for baseline or scores)" and a `late_arrival` warning. SRC-05 yields exactly 180 baseline rows equal to SRC-03 `Exp_baselines` within 1e-6.

## Preconditions

- Local development stack per `README.md` quick start; Python REPL started from the repository root with `import sys; sys.path.insert(0, ".")`.
- REPL helpers: `from tests.unit.analytics.src05 import records, result, RESIDENTS, ASSIGNMENTS, AS_OF; from tests.unit.analytics.factory import rec; from analytics.pipeline import run_pipeline; from analytics.config import TEST_V0_1 as C, PRODUCTION, ResidentInfo, DeviceAssignment; from datetime import date, datetime, UTC; from dataclasses import replace`; one-resident roster `R = [ResidentInfo("R01", date(2026, 10, 1))]; A = [DeviceAssignment("R01", "D01", date(2026, 10, 1))]; ASOF = datetime(2026, 10, 30, 20, tzinfo=UTC)`; synthetic series `def series(n): return [rec(i, f"2026-10-{i:02d} 19:00:00", loudness_dbfs=-24.0 + 0.1 * i, voiced_fraction=0.6 + 0.01 * i, mean_f0_hz=200 + i) for i in range(1, n + 1)]`.
- Local PostgreSQL freshly seeded with `python -m backend.cli seed test_v0_1 --reset`; `psql` read access.
- Local Docker Compose (demo profile) with the same data; ADMIN_TOKEN and RESEARCHER_TOKEN from `POST /api/v1/auth/login` (`SEED_*` passwords).

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-045-01 | 15 usable sessions: not formed, `usable_count` 15, no rows; 16: frozen after the 16th | High | Analytics |
| TC-045-02 | Sessions after the 16th never change the baseline; interleaved set-aside and quarantined sessions are skipped | High | Database |
| TC-045-03 | A formed epoch has 20 rows; floors 0.1 (composite), 0.5 (pauses), 0 otherwise; morning sessions enter adjusted | High | Database |
| TC-045-04 | `production` profile uses baseline_n 30 | High | Analytics |
| TC-045-05 | R09 epoch 1 baseline reproduces the TRD 08 §4.11 values | High | Analytics |
| TC-045-06 | 16 identical voiced_fraction values: z 0.0 afterwards and exactly one `zero_spread` warning | High | Analytics |
| TC-045-07 | AC-ANL-05 late-arrival fixture leaves R01 unchanged and flags the record | High | Analytics |
| TC-045-08 | SRC-05: exactly 180 rows equal to `Exp_baselines`; R08 and R07 epoch 1 none | High | Database |
| TC-045-09 | Forming progress "n of N" for R08 (13 of 16) via the API | High | API |
| TC-045-10 | Freeze metadata: `n_sessions`, first and frozen-after session ids, `frozen_at`, device | Medium | Database |
| TC-045-11 | Persisted baselines win; a differing recomputation warns `baseline_mismatch` | Medium | Analytics |
| TC-045-12 | Drift after freeze does not move the baseline (R10) | High | Analytics |
| TC-045-13 | Out-of-order but not late records are processed normally; two sessions on one day count separately | Medium | Analytics |
| TC-045-14 | Forming epochs and residents with only late or duplicate records raise no exception | Medium | Negative |

### TC-045-01 15 vs 16 usable sessions

| Step | Action | Expected Result |
|---|---|---|
| 1 | `res = run_pipeline(series(15), R, A, C, ASOF); e = res.epochs[0]; print(e.baseline_formed, e.usable_count, len(res.baselines), e.frozen_after_session_id, len(res.scores))` | `False 15 0 None 0`, no exception |
| 2 | `res = run_pipeline(series(16), R, A, C, ASOF); e = res.epochs[0]; print(e.baseline_formed, e.usable_count, len(res.baselines), e.frozen_after_session_id, {b.n_sessions for b in res.baselines})` | `True 16 20 R01-20261016-01 {16}` |
| 3 | `pytest -m unit tests/unit/analytics/test_baseline_builder.py -v` | `test_twenty_rows_per_formed_epoch`, `test_freeze_points_skip_non_usable_records`, `test_r09_worked_example`, `test_pause_floor_rows`, `test_membership_and_forming_epochs` PASSED |

### TC-045-02 Later sessions and interleaved non-usable sessions

| Step | Action | Expected Result |
|---|---|---|
| 1 | `a = run_pipeline(series(16), R, A, C, ASOF); b = run_pipeline(series(20), R, A, C, ASOF); print([(x.feature_key, x.median, x.mad, x.robust_spread) for x in a.baselines] == [(x.feature_key, x.median, x.mad, x.robust_spread) for x in b.baselines])` | `True` (sessions 17–20 change no statistic) |
| 2 | `SELECT b.n_sessions, b.first_session_id, b.frozen_after_session_id FROM baselines b JOIN residents r ON r.id = b.resident_id WHERE r.resident_code = 'R03' AND b.feature_key = 'composite';` | 16, R03-20261001-01, R03-20261023-01 (the 6 set-aside days 3, 7, 10, 14, 18, 22 and the missing day 12 are skipped) |
| 3 | `SELECT session_id, status, baseline_ordinal, in_baseline FROM processed_sessions WHERE session_id IN ('R05-20261007-01','R05-20261008-01','R05-20261009-01');` | (R05-20261007-01, usable, 7, true), (R05-20261008-01, quarantined, NULL, false), (R05-20261009-01, usable, 8, true) |
| 4 | `SELECT count(*) FROM processed_sessions WHERE in_baseline AND status <> 'usable';` | 0 |

### TC-045-03 Twenty rows per formed epoch, floors, adjusted values

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT b.epoch_id, count(*) FROM baselines b GROUP BY 1 HAVING count(*) <> 20;` | 0 rows |
| 2 | `SELECT feature_key, count(*) FROM baselines WHERE floor_applied GROUP BY 1;` | Only `number_of_pauses`, 8 rows (R01, R02, R03, R04, R05, R06, R07 epoch 2, R10; each MAD 0, spread 0.5) |
| 3 | `SELECT count(*) FROM baselines WHERE feature_key NOT IN ('number_of_pauses','composite') AND robust_spread <> mad * 1.4826;` | 0 (floor 0 for the other 18 features) |
| 4 | `SELECT count(*) FROM baselines WHERE feature_key = 'composite' AND robust_spread < 0.1;` | 0 (composite floor 0.1) |
| 5 | `SELECT median FROM baselines b JOIN residents r ON r.id = b.resident_id WHERE r.resident_code = 'R06' AND feature_key = 'loudness_dbfs';` | −22.42 (built from adjusted values; R06 has 6 morning sessions among its 16 baseline sessions — with zero offsets the median would be −22.92) |

### TC-045-04 production profile uses baseline_n 30

| Step | Action | Expected Result |
|---|---|---|
| 1 | `print(PRODUCTION.baseline_n)` | `30` |
| 2 | `p = run_pipeline(records(), RESIDENTS, ASSIGNMENTS, PRODUCTION, AS_OF); print(len(p.baselines), sorted({(b.resident_code, b.n_sessions, b.frozen_after_session_id) for b in p.baselines}), len(p.scores))` | `100 [('R01', 30, 'R01-20261030-01'), ('R04', 30, 'R04-20261030-01'), ('R06', 30, 'R06-20261030-01'), ('R09', 30, 'R09-20261030-01'), ('R10', 30, 'R10-20261030-01')] 0` (only residents with 30 usable sessions form; nothing is scored) |

### TC-045-05 R09 worked example

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT feature_key, median, mad, robust_spread, floor_applied FROM baselines b JOIN residents r ON r.id = b.resident_id WHERE r.resident_code = 'R09' AND feature_key IN ('loudness_dbfs','composite') ORDER BY 1;` | composite: median 0.038219, MAD 0.359758, spread 0.533378, false; loudness_dbfs: median −22.405, MAD 1.45, spread 2.149770, false (each ±1e-6) |
| 2 | REPL: `print([(b.feature_key, b.median, b.mad, b.robust_spread) for b in result().baselines if b.resident_code == "R09" and b.feature_key in ("loudness_dbfs", "composite")])` | Same values (0.03821908250083445, 0.3597584797917072, 0.5333779221391851; −22.405, 1.450000000000001, 2.1497700000000015) |

### TC-045-06 Zero spread of a composite feature

| Step | Action | Expected Result |
|---|---|---|
| 1 | `recs = [replace(r, features={**r.features, "voiced_fraction": 0.6}) if r.resident_code == "R01" and r.timestamp_utc.day <= 16 else r for r in records()]; res = run_pipeline(recs, RESIDENTS, ASSIGNMENTS, C, AS_OF)` | No exception |
| 2 | `print([(w.code, w.resident_code, w.detail) for w in res.warnings])` | `[('zero_spread', 'R01', 'voiced_fraction')]` — exactly one warning |
| 3 | `print({s.z["z_voiced_fraction"] for s in res.scores if s.resident_code == "R01"})` | `{0.0}` (all 14 later R01 sessions) |
| 4 | `print(next(b for b in res.baselines if b.resident_code == "R01" and b.feature_key == "voiced_fraction").robust_spread)` | `0.0` |

Note: the `zero_spread` warning is emitted by the orchestrator (`analytics/pipeline.py:238-241`), not inside `build_baselines`; FEAT-045-FR-08 / BSC-035 only require the warning per run, so the behaviour matches, but `tests/unit/analytics/test_baseline_builder.py` has no assertion on the warning count.

### TC-045-07 Late-arrival fixture (AC-ANL-05)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `d10 = next(r for r in records() if r.session_id == "R01-20261010-01"); late = replace(d10, session_id="R01-20261010-02", arrival_seq=1000, raw_session_id="00000000-0000-0000-0000-000000001000", timestamp_utc=datetime(2026, 10, 10, 19, tzinfo=UTC)); res = run_pipeline([*records(), late], RESIDENTS, ASSIGNMENTS, C, AS_OF)` | No exception |
| 2 | `print([w.code for w in res.warnings])` | `['late_arrival']` |
| 3 | `row = next(s for s in res.sessions if s.record.session_id == "R01-20261010-02"); print(row.status, row.in_baseline, row.late_arrival, row.baseline_ordinal, row.reasons)` | `usable False True None ('late arrival (not used for baseline or scores)',)` |
| 4 | `f = lambda rows: [x for x in rows if x.resident_code == "R01"]; print(f(res.baselines) == f(result().baselines), f(res.scores) == f(result().scores))` | `True True` |
| 5 | `print(res.counts["late_arrival"])` | `1` |
| 6 | `pytest -m unit tests/unit/analytics/test_pipeline.py -k "late_arrival or detect_late" -v` | `test_late_arrival_leaves_r01_unchanged`, `test_detect_late_arrival` PASSED |

### TC-045-08 SRC-05: 180 baseline rows equal to Exp_baselines

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT count(*) FROM baselines;` | 180 (9 formed epochs × 20) |
| 2 | `SELECT r.resident_code, e.epoch_number, count(*) FROM baselines b JOIN residents r ON r.id = b.resident_id JOIN epochs e ON e.id = b.epoch_id GROUP BY 1, 2 ORDER BY 1, 2;` | R01 1, R02 1, R03 1, R04 1, R05 1, R06 1, R07 2, R09 1, R10 1 — 20 rows each; no row for R08 or R07 epoch 1 |
| 3 | `pytest -m validation tests/validation/test_global_checks.py -k vc_g05 -v` | `test_vc_g05_baselines` PASSED (VC-G05: every value equals `Exp_baselines` within 1e-6; `floor_applied`, `n_sessions`, first and frozen-after session ids exact) |
| 4 | `GET /api/v1/analytics/baselines` as researcher | `total` = 180 |

### TC-045-09 Forming progress for R08

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents/R08` as admin | `baseline.state` = "forming"; `baseline.n_usable` = 13; `baseline.n_required` = 16; `baseline.frozen_after_session_id` = null |
| 2 | `GET /api/v1/residents/R07` | `baseline.state` = "frozen" (epoch 2), `baseline.frozen_after_session_id` = "R07-20261028-01" |
| 3 | REPL: `print([(e.resident_code, e.epoch_number, e.baseline_formed, e.usable_count) for e in result().epochs if not e.baseline_formed])` | `[('R07', 1, False, 12), ('R08', 1, False, 13)]` |
| 4 | `SELECT count(*) FROM scores s JOIN residents r ON r.id = s.resident_id WHERE r.resident_code = 'R08';` | 0 |

### TC-045-10 Freeze metadata

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT DISTINCT b.n_sessions, b.first_session_id, b.frozen_after_session_id, b.frozen_at, d.device_code FROM baselines b JOIN residents r ON r.id = b.resident_id JOIN epochs e ON e.id = b.epoch_id JOIN devices d ON d.id = e.device_id WHERE r.resident_code = 'R09';` | One row: 16, R09-20261001-01, R09-20261016-01, 2026-10-16 19:36:57+00 (timestamp of R09-20261016-01), D09 |
| 2 | `SELECT DISTINCT frozen_after_session_id FROM baselines b JOIN residents r ON r.id = b.resident_id ORDER BY 1;` | R01-20261016-01, R02-20261021-01, R03-20261023-01, R04-20261016-01, R05-20261017-01, R06-20261016-01, R07-20261028-01, R09-20261016-01, R10-20261016-01 |
| 3 | `SELECT count(*) FROM processed_sessions WHERE in_baseline;` | 169 (9 formed epochs × 16 = 144, plus the 12 R07 epoch-1 and 13 R08 sessions whose ordinal ≤ 16 in still-forming epochs; equals the 169 "yes" rows of SRC-03 `Annotated_sessions` `in_baseline`) |

### TC-045-11 Persisted baselines win; mismatch warns

| Step | Action | Expected Result |
|---|---|---|
| 1 | `r09 = tuple(b for b in result().baselines if b.resident_code == "R09"); same = run_pipeline(records(), RESIDENTS, ASSIGNMENTS, C, AS_OF, frozen_baselines={("R09", 1): r09}); print(same.scores == result().scores, same.warnings)` | `True ()` |
| 2 | `shifted = tuple(replace(b, median=b.median + 0.5) if b.feature_key == "loudness_dbfs" else b for b in r09); res = run_pipeline(records(), RESIDENTS, ASSIGNMENTS, C, AS_OF, frozen_baselines={("R09", 1): shifted}); print([w.code for w in res.warnings])` | `['baseline_mismatch']` |
| 3 | `print(next(b for b in res.baselines if b.resident_code == "R09" and b.feature_key == "loudness_dbfs").median)` | −21.905 (the persisted value is kept, not the recomputed −22.405) |
| 4 | `pytest -m unit tests/unit/analytics/test_pipeline.py -k frozen_baselines -v` | `test_frozen_baselines_win_and_mismatch_warns` PASSED |

### TC-045-12 Drift after freeze does not move the baseline (R10)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -m validation tests/validation/test_r10_gradual_drift.py -v` | All PASSED (VC-R10, VC-R10-FRZ) |
| 2 | `SELECT frozen_after_session_id, median FROM baselines b JOIN residents r ON r.id = b.resident_id WHERE r.resident_code = 'R10' AND feature_key = 'composite';` | R10-20261016-01; median equals `Exp_baselines` R10 composite within 1e-6 |
| 3 | Run `python -m backend.cli run-pipeline --scope all --profile test_v0_1 --as-of 2026-10-30T15:00:00-05:00` a second time and repeat step 2 | Same `frozen_after_session_id` and median; `SELECT count(*) FROM baselines` still 180 (insert-only) |

### TC-045-13 Out of order but not late; two sessions on one day

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -m unit tests/unit/analytics/test_pipeline.py -k out_of_order -v` | `test_out_of_order_after_freeze_is_not_late` PASSED (a re-sent R01 record one hour before R01's last record is scored and gives no `late_arrival` warning) |
| 2 | `recs = series(15) + [rec(16, "2026-10-15 21:00:00", session="R01-20261015-02", loudness_dbfs=-22.0, voiced_fraction=0.7, mean_f0_hz=210)]; res = run_pipeline(recs, R, A, C, ASOF); print(res.epochs[0].baseline_formed, res.epochs[0].frozen_after_session_id, [(s.record.session_id, s.baseline_ordinal) for s in res.sessions][-2:])` | `True R01-20261015-02 [('R01-20261015-01', 15), ('R01-20261015-02', 16)]` (two sessions on Oct 15 counted separately in time order) |

### TC-045-14 No exception for normal conditions

| Step | Action | Expected Result |
|---|---|---|
| 1 | `res = run_pipeline([], R, A, C, ASOF); print(res.baselines, res.scores)` | `() ()`, no exception |
| 2 | `res = run_pipeline(series(3), R, A, C, ASOF); print(res.epochs[0].usable_count, res.epochs[0].baseline_formed)` | `3 False` |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/analytics/baselines` (researcher or admin) | 200, `total` 180 rows of `BaselineRow` (`resident_code`, `epoch_number`, `device_code`, `feature_key`, `n_sessions`, `first_session_id`, `frozen_after_session_id`, `median`, `mad`, `robust_spread`, `floor_applied`) |
| 2 | `GET /api/v1/analytics/baselines?resident_code=R09&epoch=1` | 20 rows; loudness_dbfs and composite values of TC-045-05 |
| 3 | `GET /api/v1/analytics/baselines` as clinician | 403 `urn:echowell:error:FORBIDDEN` |
| 4 | `GET /api/v1/residents/R08` | `baseline.state` "forming", 13 of 16 (TC-045-09) |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `baselines` row count and per-epoch grouping | 180; 20 per formed epoch (TC-045-08) |
| 2 | `processed_sessions.baseline_ordinal` / `in_baseline` | 169 rows `in_baseline` (TC-045-10); ordinals 1, 2, … per epoch; NULL for non-usable rows |
| 3 | `pipeline_runs.warnings` of the seed run | No `late_arrival`, `zero_spread` or `baseline_mismatch` (SRC-05 has none) |
| 4 | Re-run of the pipeline | Baseline rows unchanged (insert-only; TC-045-12) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | 15 usable sessions | Not formed, no rows, no exception (TC-045-01) |
| 2 | Late record predating a frozen baseline | `late_arrival`, baseline and scores unchanged (TC-045-07) |
| 3 | Persisted baseline differing from recomputation | Persisted kept, `baseline_mismatch` (TC-045-11) |
| 4 | Zero composite spread | z 0.0, one `zero_spread` warning, no division error (TC-045-06) |
| 5 | Empty input | No exception (TC-045-14) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-045-AC-01 | 15 usable → `formed` false, `usable_count` 15, no rows, no exception; 16 → frozen after the 16th session_id, `n_sessions` 16 | TC-045-01 |
| FEAT-045-AC-02 | Sessions 17–20 change no statistic; interleaved set-aside and quarantined sessions excluded from membership and ordinal | TC-045-02 |
| FEAT-045-AC-03 | 20 rows per formed epoch; composite floor 0.1, pauses floor 0.5, others 0; morning sessions enter adjusted | TC-045-03 |
| FEAT-045-AC-04 | `production` uses baseline_n 30 | TC-045-04 |
| FEAT-045-AC-05 | R09 epoch 1: loudness −22.405 / 1.45 / 2.149770; composite 0.038219 / 0.359758 / 0.533378 (±1e-6) | TC-045-05 |
| FEAT-045-AC-06 | 16 identical voiced_fraction values → z_voiced_fraction 0.0 later and exactly one `zero_spread` warning | TC-045-06 |
| FEAT-045-AC-07 | AC-ANL-05 fixture: `late_arrival` warning, unchanged R01 baselines and scores, late record `usable`, `in_baseline` false, reason "late arrival (not used for baseline or scores)" | TC-045-07 |
| FEAT-045-AC-08 | SRC-05: exactly 180 rows equal to `Exp_baselines` within 1e-6 with exact `floor_applied`, `n_sessions`, session ids; none for R08 and R07 epoch 1 | TC-045-08, TC-045-10 |

## Test Data Requirements

- SRC-05 seeded with `test_v0_1`; SRC-03 `Exp_baselines` (180 rows), `Exp_resident_outcomes`.
- Synthetic one-resident series from `tests/unit/analytics/factory.py::rec` (R01/D01, 3–20 sessions, Oct 2026).
- Late-arrival fixture R01-20261010-02 (copy of R01-20261010-01, arrival_seq 1000, 2026-10-10 19:00:00 UTC), REPL only.
- Profiles `test_v0_1` (baseline_n 16) and `production` (baseline_n 30).

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-045-FR-01 | FEAT-045 | TC-045-02, TC-045-13 |
| FEAT-045-FR-02 | FEAT-045 | TC-045-01, TC-045-02, TC-045-12 |
| FEAT-045-FR-03 | FEAT-045 | TC-045-02, TC-045-07 |
| FEAT-045-FR-04 | FEAT-045 | TC-045-01, TC-045-09, TC-045-14 |
| FEAT-045-FR-05 | FEAT-045 | TC-045-03, TC-045-05 |
| FEAT-045-FR-06 | FEAT-045 | TC-045-03, TC-045-05 |
| FEAT-045-FR-07 | FEAT-045 | TC-045-03, TC-045-10 |
| FEAT-045-FR-08 | FEAT-045 | TC-045-06 |
| FEAT-045-FR-09 | FEAT-045 | TC-045-11 |
| FEAT-045-FR-10 | FEAT-045 | TC-045-07 |
| FEAT-045-FR-11 | FEAT-045 | TC-045-07 |
| FEAT-045-FR-12 | FEAT-045 | TC-045-13 |
| FEAT-045-FR-13 | FEAT-045 | TC-045-07, TC-045-12 |
| FEAT-045-FR-14 | FEAT-045 | TC-045-13 |
| TRD 08 BSC-025..BSC-035 | FEAT-045 | TC-045-01..TC-045-06, TC-045-10 |
| TRD 08 BSC-040..BSC-043 | FEAT-045 | TC-045-07, TC-045-13 |
| TRD 08 AC-BSC-02, AC-BSC-05, AC-BSC-06, AC-BSC-07, AC-BSC-08 | FEAT-045 | TC-045-08, TC-045-05, TC-045-06, TC-045-02 |
| TRD 07 ANL-024..ANL-027, ANL-037, AC-ANL-05 | FEAT-045 | TC-045-07, TC-045-11, TC-045-13 |
| TRD 06 DB-016 | FEAT-045 | TC-045-12 |
| TRD 13 BL-01..BL-07, PIP-04 | FEAT-045 | TC-045-01..TC-045-04, TC-045-07 |
| TRD 14 VC-G05, VC-R07, VC-R08, VC-R10, VC-R10-FRZ | FEAT-045 | TC-045-08, TC-045-09, TC-045-12 |
| FR-052, FR-080..FR-086 | FEAT-045 | TC-045-01..TC-045-10 |
