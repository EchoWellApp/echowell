# Speaker screen stage

## Feature Description

FEAT-044 implements `analytics/speaker_screen.py::screen_speakers(rows, config)`. Within each (resident, epoch), records that passed the quality gate (`pending_screen`) are visited in `(timestamp_utc, arrival_seq)` order, late records excluded from the walk. The reference for a record is the first up to `baseline_n` (16) earlier usable sessions of the same epoch (not the most recent ones); the screen runs only when the reference holds at least `screen_min_n` (5) sessions, otherwise the record becomes `usable` with `screen_detail` None. Using raw (unadjusted) values, z = (x − median) / robust spread for `mean_f0_hz` and the 7 composite features (z = 0.0 when the spread is 0; number_of_pauses floor 0.5). The record is quarantined if and only if |z_F0| ≥ 4.0 and at least 2 composite features have |z| ≥ 3.0 (both inclusive); its single reason equals its `reason_text`, "possible other speaker (F0 z=<z with 2 decimals>; composite features with |z|>=3: <n>)". Quarantined records are not appended to the reference and never enter a baseline, a score or the tally. `screen_detail` is set for every screened record. Late records are screened against their own reference without joining it. On SRC-05 exactly R05-20261008-01 and R05-20261022-01 are quarantined and 267 records are usable.

## Preconditions

- Local development stack per `README.md` quick start; Python REPL started from the repository root with `import sys; sys.path.insert(0, ".")`.
- REPL helpers: `from tests.unit.analytics.factory import rec; from analytics.duplicate_detection import mark_duplicates as md; from analytics.quality_screening import apply_quality_gate as qg; from analytics.epoch_detection import assign_epochs as ae; from analytics.speaker_screen import screen_speakers as ss; from analytics.config import TEST_V0_1 as C` and `def scr(recs): return [(x.record.session_id, x.status, x.screen_detail, x.reasons, x.reason_text) for x in ss(ae(qg(md(recs), C)), C)]`. `rec(...)` builds synthetic R01/D01 records whose default features include `mean_f0_hz` 200.0 and `number_of_pauses` 1.
- SRC-05 helpers: `from tests.unit.analytics.src05 import records, result, RESIDENTS, ASSIGNMENTS, AS_OF; from analytics.pipeline import run_pipeline`.
- Local PostgreSQL freshly seeded with `python -m backend.cli seed test_v0_1 --reset`; `psql` read access. Local Docker Compose (demo profile) with the same data; ADMIN_TOKEN from `POST /api/v1/auth/login` (`admin@example.com`, `SEED_ADMIN_PASSWORD`).

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-044-01 | 4 prior usable sessions: no screen, `screen_detail` None; 5: screen runs with the detail format | High | Analytics |
| TC-044-02 | Inclusive thresholds: \|z_F0\| 4.0 with 2 features at 3.0 quarantined; 4.5 with 1 usable; 3.99 with 7 usable | High | Analytics |
| TC-044-03 | Quarantine reason format; quarantined record not appended to the reference | High | Analytics |
| TC-044-04 | With 20 prior usable sessions only the first 16 form the reference | High | Analytics |
| TC-044-05 | Identical prior pauses give spread 0.5 (floor); identical prior F0 gives z_F0 = 0 | High | Analytics |
| TC-044-06 | Morning sessions are screened on raw values | High | Analytics |
| TC-044-07 | SRC-05: exactly the two R05 quarantines with exact strings; 267 usable | High | Database |
| TC-044-08 | Quarantined sessions excluded from baseline, scores and tally | High | Database |
| TC-044-09 | Set-aside records are not screened; every screened record stores `screen_detail` | Medium | Database |
| TC-044-10 | Late record screened against its own reference without joining it | Medium | Analytics |
| TC-044-11 | Check-in log shows the quarantine event | Medium | API |
| TC-044-12 | Zero spread and short references raise no error | Medium | Negative |

### TC-044-01 Four vs five prior usable sessions

| Step | Action | Expected Result |
|---|---|---|
| 1 | `for r in scr([rec(i, f"2026-10-{i:02d} 19:00:00") for i in range(1, 7)]): print(r[1], r[2])` | Records 1–5: `usable None` (record 5 has 4 priors); record 6: `usable F0 z=0.00; composite features with \|z\|>=3: 0` (5 priors) |
| 2 | `print(C.screen_min_n, C.baseline_n)` | `5 16` |
| 3 | `pytest -m unit tests/unit/analytics/test_speaker_screen.py -v` | `test_no_screen_below_screen_min_n`, `test_quarantine_needs_f0_and_two_composite_features`, `test_late_record_reasons`, `test_src05_r05_quarantines_use_the_first_n` PASSED |

### TC-044-02 Inclusive thresholds (SCR-03..SCR-05)

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read `test_quarantine_needs_f0_and_two_composite_features` in `tests/unit/analytics/test_speaker_screen.py` and run it with `-k quarantine_needs -v` | PASSED; the test builds references giving \|z_F0\| = 4.0 exactly with exactly 2 composite features at \|z\| = 3.0 → `quarantined`; \|z_F0\| = 4.5 with 1 composite feature at \|z\| ≥ 3 → `usable`; \|z_F0\| = 3.99 with 7 → `usable` |
| 2 | `print(C.screen_f0_z, C.screen_other_z, C.screen_other_count)` | `4.0 3.0 2` |

### TC-044-03 Quarantine reason format; not appended to the reference

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pri = [rec(i, f"2026-10-{i:02d} 19:00:00", mean_f0_hz=200.0 + i, loudness_dbfs=-24.0 + 0.1 * i, voiced_fraction=0.70 + 0.01 * i) for i in range(1, 6)]` | 5 synthetic reference records (F0 201–205) |
| 2 | `out = scr(pri + [rec(6, "2026-10-06 19:00:00", mean_f0_hz=150.0, loudness_dbfs=-40.0, voiced_fraction=0.1, number_of_pauses=9), rec(7, "2026-10-07 19:00:00", mean_f0_hz=203.0, loudness_dbfs=-23.7, voiced_fraction=0.73)]); print(out[5]); print(out[6])` | Record 6: `quarantined`, `screen_detail` "F0 z=-35.75; composite features with \|z\|>=3: 3", `reasons` = ("possible other speaker (F0 z=-35.75; composite features with \|z\|>=3: 3)",), `reason_text` equal to that single reason. Record 7: `usable`, `screen_detail` "F0 z=0.00; composite features with \|z\|>=3: 0" |
| 3 | Interpret record 7 | Its reference is still records 1–5 (median F0 203.0 → z 0.00); had record 6 been appended the F0 median would be 202.5 and z would not be 0.00 |

### TC-044-04 First-16 reference with 20 priors

| Step | Action | Expected Result |
|---|---|---|
| 1 | `x = next(s for s in result().sessions if s.record.session_id == "R05-20261022-01"); print(x.status, x.screen_detail)` | `quarantined F0 z=-7.34; composite features with \|z\|>=3: 3` (R05 day 22 has 20 earlier usable sessions; the reference is the first 16 = the baseline sessions R05-20261001-01..R05-20261017-01 without day 8) |
| 2 | `pytest -m unit tests/unit/analytics/test_speaker_screen.py -k first_n -v` | `test_src05_r05_quarantines_use_the_first_n` PASSED (a "most recent 16" reference would not reproduce −7.34) |
| 3 | `SELECT b.frozen_after_session_id FROM baselines b JOIN residents r ON r.id = b.resident_id WHERE r.resident_code = 'R05' AND b.feature_key = 'mean_f0_hz';` | `R05-20261017-01` (after freeze the reference equals the baseline members) |

### TC-044-05 Spread floor for pauses and zero F0 spread

| Step | Action | Expected Result |
|---|---|---|
| 1 | `print(scr([rec(i, f"2026-10-{i:02d} 19:00:00") for i in range(1, 6)] + [rec(6, "2026-10-06 19:00:00", mean_f0_hz=120.0, number_of_pauses=3)])[-1][2])` | `F0 z=0.00; composite features with \|z\|>=3: 1` — identical prior F0 (spread 0) gives z_F0 = 0.00 despite F0 120 vs 200; identical prior pauses (MAD 0) use the floor 0.5, so pauses 3 vs 1 gives z = 4.0 and counts once |
| 2 | `from analytics.robust_stats import robust; print(robust([1, 1, 1, 1, 1], C.pause_floor, C.mad_scale))` | `RobustStats(median=1.0, mad=0.0, spread=0.5, floor_applied=True)` |

### TC-044-06 Morning sessions screened on raw values

| Step | Action | Expected Result |
|---|---|---|
| 1 | `import dataclasses; c9 = dataclasses.replace(C, morning_offsets={k: (v * 10) for k, v in C.morning_offsets.items()}); a = run_pipeline(records(), RESIDENTS, ASSIGNMENTS, c9, AS_OF)` | No exception |
| 2 | `f = lambda res: [(s.record.session_id, s.status, s.screen_detail) for s in res.sessions if s.record.resident_code == "R06"]; print(f(a) == f(result()))` | `True` (R06 has 10 morning sessions; changing the offsets changes no screen result) |
| 3 | `print([d for i, s, d in f(result()) if i == "R06-20261019-01"])` | `['F0 z=0.76; composite features with \|z\|>=3: 0']`, identical in both runs |

### TC-044-07 SRC-05 quarantines

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT session_id, reasons, reason_text, screen_detail FROM processed_sessions WHERE status = 'quarantined' ORDER BY session_id;` | Exactly 2 rows: R05-20261008-01, `reasons` = {"possible other speaker (F0 z=-8.61; composite features with \|z\|>=3: 4)"}, `reason_text` "possible other speaker (F0 z=-8.61; composite features with \|z\|>=3: 4)", `screen_detail` "F0 z=-8.61; composite features with \|z\|>=3: 4"; R05-20261022-01, `reason_text` "possible other speaker (F0 z=-7.34; composite features with \|z\|>=3: 3)", `screen_detail` "F0 z=-7.34; composite features with \|z\|>=3: 3" |
| 2 | `SELECT count(*) FROM processed_sessions WHERE status = 'usable';` | 267 |
| 3 | `pytest -m validation tests/validation/test_r05_possible_other_speaker.py -v` | All PASSED (VC-R05) |

### TC-044-08 Quarantined sessions excluded from baseline, scores and tally

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT session_id, in_baseline, baseline_ordinal FROM processed_sessions WHERE status = 'quarantined';` | Both rows `in_baseline` false, `baseline_ordinal` NULL |
| 2 | `SELECT p.session_id, p.baseline_ordinal FROM processed_sessions p WHERE p.session_id IN ('R05-20261007-01','R05-20261009-01','R05-20261017-01');` | Ordinals 7, 8, 16 (day 8 skipped in the count) |
| 3 | `SELECT count(*) FROM scores s JOIN residents r ON r.id = s.resident_id WHERE r.resident_code = 'R05';` and check that no score row points to R05-20261022-01 | 12 scored sessions; none is R05-20261022-01 |
| 4 | Compare R05 `cusum_tally` of R05-20261021-01 and R05-20261023-01 with SRC-03 `Exp_scores` | Equal within 1e-6 (the quarantined day 22 leaves the tally unchanged) |

### TC-044-09 Set-aside records not screened; screen_detail stored

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT count(*) FROM processed_sessions WHERE status = 'set_aside' AND screen_detail IS NOT NULL;` | 0 |
| 2 | `SELECT count(*) FROM processed_sessions WHERE status = 'usable' AND screen_detail IS NOT NULL;` | > 0; every usable session with at least 5 earlier usable sessions in its epoch has a `screen_detail` matching `^F0 z=-?[0-9]+\.[0-9]{2}; composite features with \|z\|>=3: [0-7]$` |
| 3 | `SELECT session_id, screen_detail FROM processed_sessions WHERE session_id IN ('R01-20261005-01','R01-20261006-01');` | R01-20261005-01 NULL (4 priors); R01-20261006-01 "F0 z=0.30; composite features with \|z\|>=3: 1" (5 priors) |
| 4 | `SELECT count(*) FROM processed_sessions WHERE status = 'quarantined' AND screen_detail IS NULL;` | 0 |

### TC-044-10 Late record screened against its own reference

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -m unit tests/unit/analytics/test_speaker_screen.py -k late -v` | `test_late_record_reasons` PASSED |
| 2 | `from dataclasses import replace; from datetime import datetime, UTC; d10 = next(r for r in records() if r.session_id == "R01-20261010-01"); late = replace(d10, session_id="R01-20261010-02", arrival_seq=1000, raw_session_id="00000000-0000-0000-0000-000000001000", timestamp_utc=datetime(2026, 10, 10, 19, tzinfo=UTC)); res = run_pipeline([*records(), late], RESIDENTS, ASSIGNMENTS, C, AS_OF); row = next(s for s in res.sessions if s.record.session_id == "R01-20261010-02"); print(row.status, row.screen_detail is not None, row.late_arrival)` | `usable True True`; its `screen_detail` is "F0 z=-0.78; composite features with \|z\|>=3: 1" and `reasons` = ("late arrival (not used for baseline or scores)",) |
| 3 | `print([s.screen_detail for s in res.sessions if s.record.session_id == "R01-20261011-01"] == [s.screen_detail for s in result().sessions if s.record.session_id == "R01-20261011-01"])` | `True` (the late record joined no reference) |

### TC-044-11 Check-in log shows the quarantine

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents/R05/checkins?from=2026-10-08&to=2026-10-08` as admin | One event `event_type` "quarantined", `session_id` "R05-20261008-01", `detail` "possible other speaker (F0 z=-8.61; composite features with \|z\|>=3: 4)" |
| 2 | Same for 2026-10-22 | `detail` "possible other speaker (F0 z=-7.34; composite features with \|z\|>=3: 3)" |

### TC-044-12 Zero spread and short references

| Step | Action | Expected Result |
|---|---|---|
| 1 | `scr([rec(i, f"2026-10-{i:02d} 19:00:00") for i in range(1, 7)])` (all spreads 0) | No `ZeroDivisionError`; record 6 detail "F0 z=0.00; composite features with \|z\|>=3: 0" |
| 2 | `scr([rec(1, "2026-10-01 19:00:00", mean_f0_hz=100.0)])` (no reference) | `usable`, `screen_detail` None, no error |
| 3 | `print(ss([], C))` | `[]` |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents/R05/checkins` | Two `quarantined` events (Oct 8, Oct 22) with the exact reason texts (TC-044-11) |
| 2 | `GET /api/v1/scores?resident_code=R05` | `total` 12; no item for R05-20261008-01 or R05-20261022-01 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `processed_sessions` with `status='quarantined'` | 2 rows with the exact reasons and non-null `screen_detail` (TC-044-07) |
| 2 | `SELECT count(*) FROM processed_sessions WHERE status='quarantined' AND reason_text <> reasons[1];` | 0 (single reason equals reason text) |
| 3 | Quarantined rows in `scores` or baseline membership | None (TC-044-08) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Only 4 references | No screen, `usable` (TC-044-01) |
| 2 | \|z_F0\| 4.5 with one composite outlier; \|z_F0\| 3.99 with 7 | `usable` (TC-044-02) |
| 3 | Zero spread | z = 0.0, no error (TC-044-05, TC-044-12) |
| 4 | Different morning offsets | Screen result unchanged (TC-044-06) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-044-AC-01 | 4 prior usable sessions: no screen, `usable`, `screen_detail` None; 5: screen runs, `screen_detail` "F0 z=<2dp>; composite features with \|z\|>=3: <n>" | TC-044-01, TC-044-09 |
| FEAT-044-AC-02 | \|z_F0\| 4.0 with exactly 2 features at 3.0 → `quarantined`; 4.5 with 1 → `usable`; 3.99 with 7 → `usable` | TC-044-02, TC-044-03 |
| FEAT-044-AC-03 | With 20 prior usable sessions the reference uses only the first 16 | TC-044-04 |
| FEAT-044-AC-04 | Identical prior `number_of_pauses` → spread 0.5; identical prior F0 → z_F0 = 0 | TC-044-05 |
| FEAT-044-AC-05 | A morning session is screened on raw values (offsets change nothing) | TC-044-06 |
| FEAT-044-AC-06 | SRC-05: R05-20261008-01 and R05-20261022-01 exact reason texts; no other quarantine; 267 usable | TC-044-07, TC-044-08 |

## Test Data Requirements

- SRC-05 seeded with `test_v0_1` (R05 day 8 and day 22 spoken-by-someone-else shapes; R06 morning sessions).
- SRC-03 `Annotated_sessions` (`expected_reason`), `Exp_status_counts` (quarantined R05 2), `Exp_scores` (R05 tallies, maximum 4.006).
- Synthetic records from `tests/unit/analytics/factory.py::rec` (R01/D01, F0 values 120–205 Hz).
- Late-arrival fixture R01-20261010-02 (arrival_seq 1000, 2026-10-10 19:00:00 UTC) built in the REPL only.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-044-FR-01 | FEAT-044 | TC-044-01, TC-044-09 |
| FEAT-044-FR-02 | FEAT-044 | TC-044-04 |
| FEAT-044-FR-03 | FEAT-044 | TC-044-01, TC-044-12 |
| FEAT-044-FR-04 | FEAT-044 | TC-044-05, TC-044-06 |
| FEAT-044-FR-05 | FEAT-044 | TC-044-01, TC-044-03 |
| FEAT-044-FR-06 | FEAT-044 | TC-044-02, TC-044-03, TC-044-07 |
| FEAT-044-FR-07 | FEAT-044 | TC-044-03, TC-044-08 |
| FEAT-044-FR-08 | FEAT-044 | TC-044-04 |
| FEAT-044-FR-09 | FEAT-044 | TC-044-10 |
| FEAT-044-FR-10 | FEAT-044 | TC-044-09 |
| TRD 08 BSC-011..BSC-019 | FEAT-044 | TC-044-01..TC-044-09 |
| TRD 08 BSC-040 | FEAT-044 | TC-044-10 |
| TRD 08 AC-BSC-04 | FEAT-044 | TC-044-07 |
| TRD 13 SCR-01..SCR-10 | FEAT-044 | TC-044-01..TC-044-07 |
| TRD 14 VC-R05 | FEAT-044 | TC-044-07 |
| TRD 20 PGS-012 | FEAT-044 | TC-044-07 |
| FR-060..FR-065 | FEAT-044 | TC-044-01..TC-044-08 |
