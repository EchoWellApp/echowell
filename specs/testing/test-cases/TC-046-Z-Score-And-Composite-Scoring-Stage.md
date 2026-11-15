# Z-score and composite scoring stage

## Feature Description

FEAT-046 scores every usable, non-late session with `baseline_ordinal > N` in a formed epoch, exactly once and in `(timestamp_utc, arrival_seq)` order. For each of the 7 composite features z_f = (adjusted value − baseline median_f) / baseline robust spread_f is stored unsigned as `z_<feature>` (0.0 when the spread is 0). `composite_raw` = (1/7) × Σ sign_f × z_f summed in canonical order with signs loudness −1, phrase duration +1, speech rate −1, articulation rate −1, pauses +1, pause fraction +1, voiced fraction −1; `composite_z` = (composite_raw − composite baseline median) / composite baseline robust spread (`analytics/composite_score.py::composite_z`). Each `ScoreRow` carries `session_id`, `raw_session_id`, `resident_code`, `epoch_number`, `local_date`, `is_morning`, the 7 z values, `composite_raw`, `composite_z` and `scored_ordinal`. The 12 stored-not-scored features never contribute. All arithmetic is float64 without rounding. On SRC-05 exactly 98 sessions are scored (R01 14, R02 8, R03 6, R04 14, R05 12, R06 14, R07 2, R08 0, R09 14, R10 14), equal to SRC-03 `Exp_scores` within 1e-6.

## Preconditions

- Local development stack per `README.md` quick start; Python REPL started from the repository root with `import sys; sys.path.insert(0, ".")`.
- REPL helpers: `from tests.unit.analytics.src05 import records, result, RESIDENTS, ASSIGNMENTS, AS_OF; from analytics.pipeline import run_pipeline; from analytics.zscore_calculator import feature_z; from analytics.composite_score import composite_raw, composite_z; from analytics.config import TEST_V0_1 as C, COMPOSITE_KEYS, Baseline; from dataclasses import replace; from datetime import datetime, UTC`.
- Local PostgreSQL freshly seeded with `python -m backend.cli seed test_v0_1 --reset`; `psql` read access.
- Local Docker Compose (demo profile) with the same data; ADMIN_TOKEN from `POST /api/v1/auth/login` (`admin@example.com`, `SEED_ADMIN_PASSWORD`).

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-046-01 | `feature_z` for adjusted −27.0 against median −29.925, spread 3.209829 returns 0.9112635 (unsigned) | High | Analytics |
| TC-046-02 | `composite_raw` of seven z = +1.0 returns −1/7 | High | Analytics |
| TC-046-03 | `composite_z` with composite_raw 0.5, composite median 0.0, MAD 0.0 (spread floored 0.1) returns 5.0 | High | Analytics |
| TC-046-04 | R09-20261021-01 reproduces all seven z, composite_raw 2.325508 and composite_z 4.288307 | High | Analytics |
| TC-046-05 | R09-20261017-01 (first scored R09 session) composite_raw 2.035972, composite_z 3.745474 | Medium | Database |
| TC-046-06 | SRC-05: exactly 98 scored sessions with the VC-G06 per-resident counts | High | Database |
| TC-046-07 | Every scored value equals `Exp_scores` (±1e-6, booleans exact) | High | Analytics |
| TC-046-08 | Baseline, set-aside, quarantined, duplicate, late and forming-epoch sessions are never scored | High | Database |
| TC-046-09 | Changing `mfcc1` of a scored session changes none of its score values | High | Analytics |
| TC-046-10 | z stored unsigned; signs applied only inside `composite_raw` | Medium | Database |
| TC-046-11 | Zero baseline spread gives z = 0.0 without error | Medium | Negative |
| TC-046-12 | Scores read-out via the API matches the stored values | Medium | API |

### TC-046-01 feature_z (Z-01)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `s = next(x for x in result().sessions if x.record.session_id == "R01-20261017-01"); b = {x.feature_key: x for x in result().baselines if x.resident_code == "R01"}; print(b["loudness_dbfs"].median, b["loudness_dbfs"].robust_spread)` | `-29.925 3.2098289999999987` |
| 2 | `z = feature_z(replace(s, adjusted={**s.adjusted, "loudness_dbfs": -27.0}), b, C); print(z["loudness_dbfs"], list(z))` | `0.9112634972143382` (= 0.9112635 ±1e-6, positive, unsigned); keys are the 7 composite features in canonical order |
| 3 | `pytest -m unit tests/unit/analytics/test_zscore_calculator.py tests/unit/analytics/test_composite_score.py -v` | `test_r09_ringing_session_z`, `test_zero_spread_gives_zero`, `test_r09_composite`, `test_src05_scored_sessions` PASSED |

### TC-046-02 composite_raw of seven z = +1.0 (CMP-01)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `print(composite_raw({k: 1.0 for k in COMPOSITE_KEYS}, C), -1/7)` | `-0.14285714285714285 -0.14285714285714285` ((−1 + 1 − 1 − 1 + 1 + 1 − 1) / 7) |

### TC-046-03 composite_z with floored composite spread (CMP-02)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `cb = Baseline("R01", 1, "D01", "composite", 16, "a", "b", 0.0, 0.0, 0.1, True, datetime(2026, 10, 16, tzinfo=UTC)); print(composite_z(0.5, cb))` | `5.0` |
| 2 | `from analytics.robust_stats import robust; print(robust([0.2] * 16, C.composite_floor, C.mad_scale))` | `RobustStats(median=0.2, mad=0.0, spread=0.1, floor_applied=True)` (composite floor 0.1) |

### TC-046-04 R09-20261021-01 worked example

| Step | Action | Expected Result |
|---|---|---|
| 1 | `r = next(x for x in result().scores if x.session_id == "R09-20261021-01"); print(dict(r.z))` | `z_loudness_dbfs` −2.737502, `z_total_phrase_duration_s` 2.420232, `z_speech_rate_syl_per_s` −1.180359, `z_articulation_rate_syl_per_s` −1.584269, `z_number_of_pauses` 1.348982, `z_pause_fraction` 2.285774, `z_voiced_fraction` −4.721435 (each ±1e-6) |
| 2 | `print(r.composite_raw, r.composite_z, r.scored_ordinal, r.is_morning, r.local_date)` | `2.3255075140163086 4.288307289401839 5 False 2026-10-21` |
| 3 | `SELECT s.z, s.composite_raw, s.composite_z FROM scores s JOIN processed_sessions p ON p.id = s.processed_session_id WHERE p.session_id = 'R09-20261021-01';` | Same 7 z values, composite_raw 2.325508, composite_z 4.288307 (±1e-6) |

### TC-046-05 R09-20261017-01 (CMP-03)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT s.composite_raw, s.composite_z, s.local_date FROM scores s JOIN processed_sessions p ON p.id = s.processed_session_id WHERE p.session_id = 'R09-20261017-01';` | 2.035972, 3.745474 (±1e-6), 2026-10-17 |
| 2 | `SELECT p.baseline_ordinal FROM processed_sessions p WHERE p.session_id = 'R09-20261017-01';` | 17 (first ordinal above N = 16) |

### TC-046-06 SRC-05: 98 scored sessions

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT count(*) FROM scores;` | 98 |
| 2 | `SELECT r.resident_code, count(s.id) FROM residents r LEFT JOIN scores s ON s.resident_id = r.id GROUP BY 1 ORDER BY 1;` | R01 14, R02 8, R03 6, R04 14, R05 12, R06 14, R07 2, R08 0, R09 14, R10 14 |
| 3 | `SELECT counts->>'scored' FROM pipeline_runs WHERE status = 'succeeded' ORDER BY started_at DESC LIMIT 1;` | `98` |

### TC-046-07 Every scored value equals Exp_scores

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -m validation tests/validation/test_global_checks.py -k vc_g06 -v` | `test_vc_g06_scores` PASSED (98 rows; all `z_*`, `composite_raw`, `composite_z` within 1e-6; `morning` exact) |
| 2 | `pytest -m validation tests/validation/test_r09_step_change.py tests/validation/test_r10_gradual_drift.py -v` | All PASSED |
| 3 | Spot-check R10-20261024-01 in the DB: `SELECT s.composite_raw, s.composite_z FROM scores s JOIN processed_sessions p ON p.id = s.processed_session_id WHERE p.session_id = 'R10-20261024-01';` | 2.431695, 2.085518 (±1e-6, `Exp_scores`) |

### TC-046-08 Non-eligible sessions are never scored

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT p.status, p.in_baseline, p.late_arrival, count(*) FROM scores s JOIN processed_sessions p ON p.id = s.processed_session_id GROUP BY 1, 2, 3;` | One group only: `usable`, false, false, 98 |
| 2 | `SELECT min(p.baseline_ordinal) FROM scores s JOIN processed_sessions p ON p.id = s.processed_session_id;` | 17 |
| 3 | `SELECT count(*) FROM scores s JOIN epochs e ON e.id = s.epoch_id JOIN residents r ON r.id = s.resident_id WHERE (r.resident_code = 'R07' AND e.epoch_number = 1) OR r.resident_code = 'R08';` | 0 (forming epochs) |
| 4 | Late fixture: `d10 = next(x for x in records() if x.session_id == "R01-20261010-01"); late = replace(d10, session_id="R01-20261010-02", arrival_seq=1000, raw_session_id="00000000-0000-0000-0000-000000001000", timestamp_utc=datetime(2026, 10, 10, 19, tzinfo=UTC)); res = run_pipeline([*records(), late], RESIDENTS, ASSIGNMENTS, C, AS_OF); print(any(x.session_id == "R01-20261010-02" for x in res.scores), len(res.scores))` | `False 98` |

### TC-046-09 Stored-not-scored features never contribute

| Step | Action | Expected Result |
|---|---|---|
| 1 | `recs = [replace(x, features={**x.features, "mfcc1": 99.0}) if x.session_id == "R09-20261021-01" else x for x in records()]; b = run_pipeline(recs, RESIDENTS, ASSIGNMENTS, C, AS_OF)` | No exception |
| 2 | `print([x for x in b.scores if x.session_id == "R09-20261021-01"] == [x for x in result().scores if x.session_id == "R09-20261021-01"])` | `True` |
| 3 | Repeat with `"hnr_db": 0.0` instead of `mfcc1` | `True` |
| 4 | `SELECT DISTINCT jsonb_object_keys(z) FROM scores ORDER BY 1;` | Exactly the 7 keys `z_articulation_rate_syl_per_s`, `z_loudness_dbfs`, `z_number_of_pauses`, `z_pause_fraction`, `z_speech_rate_syl_per_s`, `z_total_phrase_duration_s`, `z_voiced_fraction` |

### TC-046-10 z unsigned; signs only inside composite_raw

| Step | Action | Expected Result |
|---|---|---|
| 1 | From TC-046-04, `z_voiced_fraction` of R09-20261021-01 | −4.721435 (stored as (adjusted − median)/spread, the sign is not flipped) |
| 2 | `SELECT round((( -(z->>'z_loudness_dbfs')::float8 + (z->>'z_total_phrase_duration_s')::float8 - (z->>'z_speech_rate_syl_per_s')::float8 - (z->>'z_articulation_rate_syl_per_s')::float8 + (z->>'z_number_of_pauses')::float8 + (z->>'z_pause_fraction')::float8 - (z->>'z_voiced_fraction')::float8) / 7 - composite_raw)::numeric, 9) FROM scores;` | 0.000000000 on all 98 rows |

### TC-046-11 Zero baseline spread

| Step | Action | Expected Result |
|---|---|---|
| 1 | `s = next(x for x in result().sessions if x.record.session_id == "R09-20261021-01"); b9 = {x.feature_key: x for x in result().baselines if x.resident_code == "R09"}; b9["pause_fraction"] = replace(b9["pause_fraction"], robust_spread=0.0); print(feature_z(s, b9, C)["pause_fraction"])` | `0.0`, no `ZeroDivisionError` |

### TC-046-12 Scores read-out via the API

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/scores?resident_code=R09` as admin | 200; `total` 14; each item has `resident_code`, `session_id`, `epoch_number`, `local_date`, `is_morning`, `z` (7 keys), `composite_raw`, `composite_z`, `cusum_tally`, `alarm_state` |
| 2 | Item for R09-20261021-01 | `composite_raw` 2.3255075140163086, `composite_z` 4.288307289401839 (full precision) |
| 3 | `GET /api/v1/scores?resident_code=R08` | 200; `total` 0 |
| 4 | `GET /api/v1/scores?resident_code=r09` | 422 problem+json (invalid study ID format) |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/scores` (all user roles, JSON) | 200; `total` 98 for DS-07 |
| 2 | `GET /api/v1/scores?resident_code=R09` | Values of TC-046-04 / TC-046-05 |
| 3 | Invalid `resident_code` | 422 problem+json |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `scores` row count and per-resident counts | 98; VC-G06 counts (TC-046-06) |
| 2 | `scores.z` keys | Exactly 7 `z_*` keys on every row (`scores_z_ck`) |
| 3 | Linked `processed_sessions` | All `usable`, not in baseline, not late, ordinal ≥ 17 (TC-046-08) |
| 4 | `composite_raw` consistency with stored z | Difference 0 to 9 decimals (TC-046-10) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Zero spread | z 0.0, no error (TC-046-11) |
| 2 | Changed `mfcc1` / `hnr_db` | No score change (TC-046-09) |
| 3 | Forming epoch / late record | Not scored (TC-046-08) |
| 4 | Lower-case resident code in the read-out | 422 (TC-046-12) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-046-AC-01 | `feature_z` for adjusted −27.0, median −29.925, spread 3.209829 returns 0.9112635 (±1e-6), unsigned | TC-046-01 |
| FEAT-046-AC-02 | Seven z = +1.0 → `composite_raw` −1/7; composite_raw 0.5 with median 0.0, MAD 0.0 (spread 0.1) → `composite_z` 5.0 | TC-046-02, TC-046-03 |
| FEAT-046-AC-03 | R09-20261021-01 z −2.737502, 2.420232, −1.180359, −1.584269, 1.348982, 2.285774, −4.721435; composite_raw 2.325508; composite_z 4.288307 (±1e-6) | TC-046-04 |
| FEAT-046-AC-04 | SRC-05: exactly 98 scored with VC-G06 counts; every `z_*`, `composite_raw`, `composite_z`, `morning` equals `Exp_scores` | TC-046-05, TC-046-06, TC-046-07 |
| FEAT-046-AC-05 | Changing a stored-not-scored feature (e.g. `mfcc1`) of a scored session changes none of its ScoreRow values | TC-046-09 |

## Test Data Requirements

- SRC-05 seeded with `test_v0_1`; SRC-03 `Exp_scores` (98 rows) and `Exp_baselines`.
- Synthetic composite baseline row (median 0.0, MAD 0.0, spread 0.1) built in the REPL.
- Late-arrival fixture R01-20261010-02 built in the REPL only.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-046-FR-01 | FEAT-046 | TC-046-06, TC-046-08 |
| FEAT-046-FR-02 | FEAT-046 | TC-046-01, TC-046-10, TC-046-11 |
| FEAT-046-FR-03 | FEAT-046 | TC-046-02, TC-046-10 |
| FEAT-046-FR-04 | FEAT-046 | TC-046-03, TC-046-04 |
| FEAT-046-FR-05 | FEAT-046 | TC-046-04, TC-046-12 |
| FEAT-046-FR-06 | FEAT-046 | TC-046-09 |
| FEAT-046-FR-07 | FEAT-046 | TC-046-04, TC-046-07 |
| TRD 08 BSC-032, BSC-035..BSC-039 | FEAT-046 | TC-046-01..TC-046-11 |
| TRD 08 AC-BSC-03, AC-BSC-06 | FEAT-046 | TC-046-07, TC-046-04 |
| TRD 07 ANL-022 | FEAT-046 | TC-046-04 |
| TRD 13 Z-01, Z-02, CMP-01..CMP-03 | FEAT-046 | TC-046-01..TC-046-05, TC-046-09 |
| TRD 14 VC-G06 | FEAT-046 | TC-046-06, TC-046-07 |
| TRD 23 DME-002 | FEAT-046 | TC-046-02 |
| FR-090..FR-095 | FEAT-046 | TC-046-01..TC-046-09 |
