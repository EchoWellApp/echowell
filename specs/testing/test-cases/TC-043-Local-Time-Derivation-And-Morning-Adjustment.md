# Local time derivation and morning adjustment

## Feature Description

FEAT-043 implements `analytics/morning_offset.py::adjust(rows, config)` and the single local-time helper of the analytics package. Every non-duplicate record's `timestamp_utc` is converted with `astimezone(ZoneInfo(config.facility_tz))` ("America/Chicago", DST-aware); the local date and local time come from that local datetime (never from the UTC hour or date). A record is morning if and only if its local hour is less than `morning_cutoff_hour` (12). For a morning record each of the 19 features is adjusted as raw − configured morning offset (loudness_dbfs −1.50, total_phrase_duration_s +0.10, speech_rate_syl_per_s −0.12, articulation_rate_syl_per_s −0.10, pause_fraction +0.010, voiced_fraction −0.020, all others 0); other records keep adjusted = raw. Baselines and scores use adjusted values; the speaker screen uses raw values. On SRC-05 exactly 10 R06 sessions (days 1, 4, …, 28) are morning and 4 of them are scored.

## Preconditions

- Local development stack per `README.md` quick start; Python REPL started from the repository root with `import sys; sys.path.insert(0, ".")`.
- REPL helpers: `from analytics.config import TEST_V0_1 as C; from analytics.morning_offset import local_time, is_morning; from datetime import datetime, UTC` and `def show(s): t = datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC); l, d = local_time(t, C); return l.strftime("%Y-%m-%d %H:%M:%S %Z"), str(d), is_morning(l, C)`.
- SRC-05 engine run helper: `from tests.unit.analytics.src05 import records, result, RESIDENTS, ASSIGNMENTS, AS_OF; from analytics.pipeline import run_pipeline`.
- Local PostgreSQL freshly seeded with `python -m backend.cli seed test_v0_1 --reset` (`FACILITY_TZ=America/Chicago`); `psql` read access.
- The backend image includes `tzdata` (TRD 07 §6).

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-043-01 | Morning cutoff in CDT: 16:59:59 UTC is 11:59:59 morning; 17:00:00 UTC is 12:00:00 not morning | High | Analytics |
| TC-043-02 | Morning cutoff after DST end: 17:59:59 UTC is 11:59:59 CST morning; 18:00:00 UTC not morning | High | Analytics |
| TC-043-03 | NFR-131 / NFR-132 DST and midnight vectors | High | Analytics |
| TC-043-04 | R06 day 1 morning adjustment of the 7 composite features | High | Analytics |
| TC-043-05 | Afternoon sessions and the 12 stored-not-scored features are unchanged | High | Analytics |
| TC-043-06 | SRC-05: exactly 10 R06 morning sessions; 4 scored with `is_morning` true | High | Database |
| TC-043-07 | Stored local fields and adjusted features of R06-20261001-01 and R06-20261004-01 | High | Database |
| TC-043-08 | No session outside R06 is morning (UTC-hour regression guard) | Medium | Database |
| TC-043-09 | Offsets come only from configuration; baselines use adjusted values, the screen uses raw values | High | Analytics |
| TC-043-10 | Configured offsets equal SRC-03 `Exp_morning_offset` (VC-G07) | Medium | Database |
| TC-043-11 | Unresolvable time zone and naive timestamps are refused | Medium | Negative |

### TC-043-01 Morning cutoff in CDT

| Step | Action | Expected Result |
|---|---|---|
| 1 | `print(show("2026-10-01 16:59:59"))` | `('2026-10-01 11:59:59 CDT', '2026-10-01', True)` |
| 2 | `print(show("2026-10-01 17:00:00"))` | `('2026-10-01 12:00:00 CDT', '2026-10-01', False)` |
| 3 | `pytest -m unit tests/unit/analytics/test_morning_offset.py -v` | `test_local_time_vectors`, `test_r06_day_1_adjustment`, `test_afternoon_and_stored_features_unchanged`, `test_src05_r06_mornings` PASSED |

### TC-043-02 Morning cutoff after DST end

| Step | Action | Expected Result |
|---|---|---|
| 1 | `print(show("2026-11-01 17:59:59"))` | `('2026-11-01 11:59:59 CST', '2026-11-01', True)` |
| 2 | `print(show("2026-11-01 18:00:00"))` | `('2026-11-01 12:00:00 CST', '2026-11-01', False)` |
| 3 | Compare with a fixed −5 h offset (17:59:59 − 5 h = 12:59:59) | The engine result differs from the fixed-offset result (morning true vs false): the zone database is used |

### TC-043-03 NFR-131 and NFR-132 vectors

| Step | Action | Expected Result |
|---|---|---|
| 1 | `print(show("2026-11-01 06:30:00"))` | `('2026-11-01 01:30:00 CDT', '2026-11-01', True)` |
| 2 | `print(show("2026-11-01 07:30:00"))` | `('2026-11-01 01:30:00 CST', '2026-11-01', True)` |
| 3 | `print(show("2027-03-14 08:30:00"))` | `('2027-03-14 03:30:00 CDT', '2027-03-14', True)` |
| 4 | `print(show("2026-10-02 04:59:59"))` | `('2026-10-01 23:59:59 CDT', '2026-10-01', False)` (local date is the previous day) |

### TC-043-04 R06 day 1 morning adjustment

| Step | Action | Expected Result |
|---|---|---|
| 1 | `x = next(s for s in result().sessions if s.record.session_id == "R06-20261001-01"); print(x.local_datetime, x.is_morning)` | `2026-10-01 09:08:37-05:00 True` |
| 2 | `keys = ["loudness_dbfs", "total_phrase_duration_s", "speech_rate_syl_per_s", "articulation_rate_syl_per_s", "number_of_pauses", "pause_fraction", "voiced_fraction"]; print([x.record.features[k] for k in keys])` | `[-25.42, 4.01, 4.14, 4.52, 2.0, 0.126, 0.595]` |
| 3 | `print([round(x.adjusted[k], 9) for k in keys])` | `[-23.92, 3.91, 4.26, 4.62, 2.0, 0.116, 0.615]` (each within 1e-9) |
| 4 | Check raw values are kept separately | `x.record.features["loudness_dbfs"]` is still −25.42 after step 3 |

### TC-043-05 Afternoon sessions and stored-not-scored features unchanged

| Step | Action | Expected Result |
|---|---|---|
| 1 | `y = next(s for s in result().sessions if s.record.session_id == "R06-20261017-01"); print(y.is_morning, dict(y.adjusted) == dict(y.record.features))` | `False True` (all 19 adjusted = raw) |
| 2 | `others = [k for k in x.record.features if k not in keys]; print(len(others), all(x.adjusted[k] == x.record.features[k] for k in others))` (x from TC-043-04) | `12 True` |
| 3 | `print(all(dict(s.adjusted) == dict(s.record.features) for s in result().sessions if s.status != "duplicate" and not s.is_morning))` | `True` |

### TC-043-06 SRC-05: 10 R06 morning sessions, 4 scored

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT p.session_id, p.local_time FROM processed_sessions p JOIN residents r ON r.id = p.resident_id WHERE r.resident_code = 'R06' AND p.is_morning ORDER BY 1;` | 10 rows: R06-20261001-01, R06-20261004-01, R06-20261007-01, R06-20261010-01, R06-20261013-01, R06-20261016-01, R06-20261019-01, R06-20261022-01, R06-20261025-01, R06-20261028-01; every `local_time` before 12:00:00 (e.g. 09:08:37 for day 1, 09:35:55 for day 4) |
| 2 | `SELECT p.session_id FROM scores s JOIN processed_sessions p ON p.id = s.processed_session_id WHERE s.is_morning ORDER BY 1;` | Exactly R06-20261019-01, R06-20261022-01, R06-20261025-01, R06-20261028-01 |
| 3 | `SELECT count(*) FROM scores s JOIN residents r ON r.id = s.resident_id WHERE r.resident_code = 'R06';` | 14 |
| 4 | `pytest -m validation tests/validation/test_r06_morning_effect.py -v` | All PASSED (VC-R06) |

### TC-043-07 Stored local fields and adjusted features

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT timestamp_utc, local_date, local_time, is_morning FROM processed_sessions WHERE session_id = 'R06-20261004-01';` | 2026-10-04 14:35:55+00, 2026-10-04, 09:35:55, true (TRD 08 §4.5 worked example) |
| 2 | `SELECT adjusted_features->>'loudness_dbfs', adjusted_features->>'voiced_fraction', adjusted_features->>'mean_f0_hz' FROM processed_sessions WHERE session_id = 'R06-20261001-01';` | −23.92, 0.615, 108.8 (mean_f0_hz unchanged, offset 0) |
| 3 | `SELECT count(*) FROM processed_sessions WHERE status <> 'duplicate' AND (SELECT count(*) FROM jsonb_object_keys(adjusted_features)) <> 19;` | 0 (19 adjusted keys on every non-duplicate row) |
| 4 | `SELECT count(*) FROM processed_sessions WHERE abs(local_date - (timestamp_utc AT TIME ZONE 'UTC')::date) > 1;` | 0 |

### TC-043-08 No session outside R06 is morning

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT count(*) FROM processed_sessions WHERE is_morning;` | 10 (all R06; SRC-05 has no other session before local noon) |
| 2 | `SELECT count(*) FROM processed_sessions WHERE extract(hour FROM timestamp_utc) < 12;` | 0 (a UTC-hour rule would classify none of R06's sessions as morning; the stored flag uses local time) |

### TC-043-09 Offsets only from configuration; adjusted for baselines, raw for the screen

| Step | Action | Expected Result |
|---|---|---|
| 1 | `import dataclasses; c0 = dataclasses.replace(C, morning_offsets={k: 0.0 for k in C.morning_offsets}); a = run_pipeline(records(), RESIDENTS, ASSIGNMENTS, c0, AS_OF)` | No exception |
| 2 | `x0 = next(s for s in a.sessions if s.record.session_id == "R06-20261001-01"); print(x0.is_morning, dict(x0.adjusted) == dict(x0.record.features))` | `True True` (zero offsets → adjusted = raw; nothing is estimated) |
| 3 | `b = lambda res: next(v for v in res.baselines if v.resident_code == "R06" and v.feature_key == "loudness_dbfs").median; print(b(a) == b(result()))` | `False` (baselines use adjusted values, so the R06 baseline changes with the offsets) |
| 4 | `f = lambda res: [(s.record.session_id, s.status, s.screen_detail) for s in res.sessions if s.record.resident_code == "R06"]; print(f(a) == f(result()))` | `True` (the speaker screen uses raw values) |

### TC-043-10 Configured offsets equal Exp_morning_offset

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT value FROM config_parameters WHERE profile = 'test_v0_1' AND key = 'morning_offsets';` | JSON object with 19 keys: loudness_dbfs −1.5, total_phrase_duration_s 0.1, speech_rate_syl_per_s −0.12, articulation_rate_syl_per_s −0.1, pause_fraction 0.01, voiced_fraction −0.02, the other 13 keys 0 |
| 2 | Compare with SRC-03 sheet `Exp_morning_offset` | All 19 `configured_morning_offset` values equal |
| 3 | `SELECT value FROM config_parameters WHERE profile = 'test_v0_1' AND key = 'morning_cutoff_hour';` | 12 |

### TC-043-11 Unresolvable time zone and naive timestamps

| Step | Action | Expected Result |
|---|---|---|
| 1 | `from analytics.config import PipelineConfig; PipelineConfig.from_mapping(dict(C.values(), facility_tz="America/Chicag"))` | Raises `ConfigError` "facility_tz: unknown time zone 'America/Chicag'" |
| 2 | `from tests.unit.analytics.factory import rec; import datetime; dataclasses.replace(rec(1, "2026-10-01 19:00:00"), timestamp_utc=datetime.datetime(2026, 10, 1, 19))` | Raises `ContractError` "R01-20261001-01: timestamp_utc must be timezone-aware" |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/scores?resident_code=R06` (admin, DS-07) | 14 items; `is_morning` true exactly for R06-20261019-01, R06-20261022-01, R06-20261025-01, R06-20261028-01 |
| 2 | `GET /api/v1/residents/R06/features` | Values per day returned for the 7 scored measurements; no morning flag computed from UTC |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `processed_sessions.local_date`, `local_time`, `is_morning`, `adjusted_features` | As in TC-043-06, TC-043-07 |
| 2 | `scores.is_morning` | True for 4 rows only (TC-043-06) |
| 3 | `processed_sessions_local_date_ck` | No violation (TC-043-07 step 4) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | 12:00:00 local (17:00:00 UTC CDT; 18:00:00 UTC CST) | Not morning (TC-043-01, TC-043-02) |
| 2 | 04:59:59 UTC on Oct 2 | Local date 2026-10-01, not Oct 2 (TC-043-03) |
| 3 | Unknown `facility_tz` | `ConfigError` (TC-043-11) |
| 4 | Naive `timestamp_utc` | `ContractError` (TC-043-11) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-043-AC-01 | `2026-10-01 16:59:59` UTC is 11:59:59 CDT morning; `17:00:00` UTC is 12:00:00 not morning | TC-043-01 |
| FEAT-043-AC-02 | `2026-11-01 17:59:59` UTC is 11:59:59 CST morning; `18:00:00` UTC not morning | TC-043-02 |
| FEAT-043-AC-03 | NFR-131 and NFR-132 vectors give the stated local times, dates and morning flags | TC-043-03 |
| FEAT-043-AC-04 | R06 day 1 raw −25.42, 4.01, 4.14, 4.52, 2, 0.126, 0.595 adjusts to −23.92, 3.91, 4.26, 4.62, 2, 0.116, 0.615 (±1e-9) | TC-043-04, TC-043-07 |
| FEAT-043-AC-05 | Afternoon session adjusted == raw for all 19; the 12 stored-not-scored features of a morning session unchanged | TC-043-05 |
| FEAT-043-AC-06 | SRC-05: exactly 10 R06 sessions (days 1, 4, …, 28) morning; scored R06-20261019-01, -22, -25, -28 with `is_morning` true | TC-043-06, TC-043-08 |

## Test Data Requirements

- SRC-05 seeded with `test_v0_1` (R06 morning sessions at about 09:00 local; all other sessions in the afternoon).
- SRC-03 `Exp_morning_offset`, `Exp_scores` (`morning` column) and `Annotated_sessions` (`expected_morning`).
- `FACILITY_TZ=America/Chicago`; `config_parameters` keys `facility_tz`, `morning_cutoff_hour`, `morning_offsets`.
- Synthetic UTC instants of TC-043-01..03 (no resident data).

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-043-FR-01 | FEAT-043 | TC-043-01, TC-043-02, TC-043-08 |
| FEAT-043-FR-02 | FEAT-043 | TC-043-03, TC-043-07 |
| FEAT-043-FR-03 | FEAT-043 | TC-043-01, TC-043-02 |
| FEAT-043-FR-04 | FEAT-043 | TC-043-04, TC-043-09, TC-043-10 |
| FEAT-043-FR-05 | FEAT-043 | TC-043-07, TC-043-09 |
| FEAT-043-FR-06 | FEAT-043 | TC-043-03 |
| FEAT-043-FR-07 | FEAT-043 | TC-043-04 |
| TRD 08 BSC-020..BSC-024, §4.5 | FEAT-043 | TC-043-01..TC-043-07 |
| TRD 10 ING-027 | FEAT-043 | TC-043-01 |
| TRD 03 NFR-130, NFR-131, NFR-132 | FEAT-043 | TC-043-03, TC-043-07 |
| TRD 07 ANL-055 | FEAT-043 | TC-043-09 |
| TRD 13 MO-01..MO-07 | FEAT-043 | TC-043-01, TC-043-02, TC-043-04, TC-043-05 |
| TRD 14 VC-R06, VC-G07 | FEAT-043 | TC-043-06, TC-043-10 |
| FR-070..FR-074 | FEAT-043 | TC-043-01..TC-043-09 |
