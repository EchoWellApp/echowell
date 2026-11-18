# Analytics page aggregates (stage 12) wired into GET /api/v1/analytics

## Feature Description

Stage 12 of the analytics engine (`analytics/aggregates.py::build_analytics_summary`, FEAT-051) turns one pipeline result into the counts of the Study team page (`/study`): four KPIs (`checkins_received`, `used_for_scoring`, `baselines_formed`, `alarms_raised`), the 30-day `daily_series`, the 4-step loss `funnel` and the usable share per resident (`by_resident`). Percentages use the integer half-up helper `pct(n, d) = (200·n + d) // (2·d)` (null when `d = 0`). `backend/services/analytics_summary.py` maps the summary onto the `kpis`, `daily_series`, `funnel` and `by_resident` blocks of `GET /api/v1/analytics` (TRD 19 E-18) for the latest succeeded run, adding `alarms_raised.not_reviewed_count` from persisted alert status at response time. All figures derive from the same pipeline result, so they equal the status counts and the answer key.

## Preconditions

- Local development stack; database seeded with `python -m backend.cli seed test_v0_1` (DS-07, as-of 2026-10-30T20:00:00Z); DS-10 loaded with `python database/seeds/load_evaluation_ground_truth.py tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv`; backend API running.
- Tokens: `POST /api/v1/auth/login` for `researcher@example.com`, `admin@example.com`, `clinician@example.com` with the `SEED_*` passwords from the environment file.
- REPL helper for engine cases:

```python
from datetime import datetime
from zoneinfo import ZoneInfo
from analytics.config import TEST_V0_1
from analytics.pipeline import run_pipeline
from analytics.aggregates import pct
from tests.unit.analytics.src05 import result
S = result().analytics
```

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-051-01 | Unit cases AN-01..AN-05 pass; `pct(1, 8)` returns 13 | High | Analytics |
| TC-051-02 | Period is 2026-10-01..2026-10-30 for the SRC-05 as-of | High | Analytics |
| TC-051-03 | KPIs equal 281/300/94, 267/300/89, 9 of 10 (R08 forming, R07 restarted once), 2 alarms R09 R10 | High | Analytics |
| TC-051-04 | Funnel 300 → 281 → 269 → 267 with reasons 5/5/3 and 1 multi-reason | High | Analytics |
| TC-051-05 | by_resident order and percentages | High | Analytics |
| TC-051-06 | daily_series has 30 rows equal to the TRD 14 per-day list; Oct 12 silent ["D02"] | High | Analytics |
| TC-051-07 | Sum of daily segments equals status totals 267/12/2/19 | High | Analytics |
| TC-051-08 | `GET /api/v1/analytics` as researcher returns the four blocks with TRD 19 field names and values | High | API |
| TC-051-09 | `not_reviewed_count` drops to 1 after a review on R09 while `count` stays 2 | High | API |
| TC-051-10 | Zero residents / `expected = 0` returns null percentages without an exception | High | Negative |
| TC-051-11 | Clinician and unauthenticated calls are refused | High | Security |
| TC-051-12 | Response uses the latest succeeded run's as-of and no float rounding outside `pct` | Medium | API |

### TC-051-01 Unit cases AN-01..AN-05 pass; `pct(1, 8)` returns 13

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/unit/analytics/test_aggregates.py -q` | Exit code 0; `test_pct_half_up_integer`, `test_src05_kpis`, `test_src05_daily_series`, `test_src05_funnel`, `test_src05_by_resident` pass |
| 2 | REPL: `pct(1, 8), pct(281, 300), pct(267, 300), pct(1, 0)` | `(13, 94, 89, None)` (12.5 % rounds half-up to 13, not 12) |

### TC-051-02 Period is 2026-10-01..2026-10-30 for the SRC-05 as-of

| Step | Action | Expected Result |
|---|---|---|
| 1 | REPL: `S.period_start, S.period_end` | `(datetime.date(2026, 10, 1), datetime.date(2026, 10, 30))` |
| 2 | API: `GET /api/v1/analytics` (researcher) | `period` = `{"from": "2026-10-01", "to": "2026-10-30", "days": 30}` |

### TC-051-03 KPIs equal 281/300/94, 267/300/89, 9 of 10 (R08 forming, R07 restarted once), 2 alarms R09 R10

| Step | Action | Expected Result |
|---|---|---|
| 1 | REPL: `S.kpis["checkins_received"]` | `{'value': 281, 'expected': 300, 'percent': 94}` |
| 2 | `S.kpis["used_for_scoring"]` | `{'value': 267, 'expected': 300, 'percent': 89}` |
| 3 | `S.kpis["baselines_formed"]` | `value` 9, `total` 10, `forming` ['R08'], `restarts` {'R07': 1} |
| 4 | `S.kpis["alarms_raised"]` | `{'value': 2, 'residents': ['R09', 'R10']}` (no not-reviewed count in the engine) |

### TC-051-04 Funnel 300 → 281 → 269 → 267 with reasons 5/5/3 and 1 multi-reason

| Step | Action | Expected Result |
|---|---|---|
| 1 | REPL: `[(f["step"], f["value"]) for f in S.funnel]` | `[('expected', 300), ('received', 281), ('passed_quality', 269), ('used', 267)]` |
| 2 | `S.funnel[1]["missed"], S.funnel[1]["duplicates_removed"]` | `(19, 2)` |
| 3 | `S.funnel[2]["set_aside"], S.funnel[2]["set_aside_reasons"], S.funnel[2]["set_aside_multi_reason"]` | `12`, `{'quality_flag_poor': 5, 'noise_above_limit': 5, 'speech_too_short': 3}`, `1` (R03 day 18 has two reasons) |
| 4 | `S.funnel[3]["quarantined"]` | `2` |

### TC-051-05 by_resident order and percentages

| Step | Action | Expected Result |
|---|---|---|
| 1 | REPL: `[(r["resident_code"], r["used_percent"]) for r in S.by_resident]` | `[('R08', 43), ('R03', 73), ('R02', 80), ('R05', 93), ('R01', 100), ('R04', 100), ('R06', 100), ('R07', 100), ('R09', 100), ('R10', 100)]` |
| 2 | `S.by_resident[0]` | R08: `days` 30, `used_days` 13, `set_aside_days` 5, `quarantined_days` 0, `missed_days` 12 |
| 3 | `S.by_resident[1]`, `S.by_resident[2]`, `S.by_resident[3]` | R03 22/7/0/1; R02 24/0/0/6; R05 28/0/2/0 (days 30 each) |

### TC-051-06 daily_series has 30 rows equal to the TRD 14 per-day list; Oct 12 silent ["D02"]

| Step | Action | Expected Result |
|---|---|---|
| 1 | REPL: `len(S.daily_series)` | `30` |
| 2 | `[(d["local_date"].day, d["used"], d["set_aside"], d["quarantined"], d["missed"]) for d in S.daily_series]` | Equals TRD 14 §4.9.2: 1 10/0/0/0; 2 9/0/0/1; 3 9/1/0/0; 4 8/0/0/2; 5 9/1/0/0; 6 9/0/0/1; 7 9/1/0/0; 8 8/0/1/1; 9 8/1/0/1; 10 8/1/0/1; 11 9/0/0/1; 12 8/0/0/2; 13 9/0/0/1; 14 9/1/0/0; 15 9/0/0/1; 16 10/0/0/0; 17 8/0/0/2; 18 9/1/0/0; 19 9/0/0/1; 20 9/1/0/0; 21 9/0/0/1; 22 8/1/1/0; 23 9/0/0/1; 24 9/0/0/1; 25 9/1/0/0; 26 9/1/0/0; 27 9/0/0/1; 28 10/0/0/0; 29 9/1/0/0; 30 10/0/0/0 |
| 3 | `[(d["local_date"].day, d["silent_device_codes"]) for d in S.daily_series if d["silent_device_codes"]]` | `[(12, ['D02'])]` only |

### TC-051-07 Sum of daily segments equals status totals 267/12/2/19

| Step | Action | Expected Result |
|---|---|---|
| 1 | REPL: `[sum(d[k] for d in S.daily_series) for k in ("used","set_aside","quarantined","missed")]` | `[267, 12, 2, 19]`; grand total 300 |
| 2 | API: `GET /api/v1/analytics` `status_totals` | `usable` 267, `set_aside` 12, `quarantined` 2, `missing_resident` 17 + `missing_device_gap` 2 = 19 |
| 3 | Compare step 1 with step 2 | Each pair equal; duplicates (2) appear in neither series |

### TC-051-08 `GET /api/v1/analytics` as researcher returns the four blocks with TRD 19 field names and values

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/analytics` with the researcher token | 200 |
| 2 | Inspect `kpis` | `checkins_received` {`count` 281, `expected` 300, `percent` 94}; `used_for_scoring` {`count` 267, `expected` 300, `percent` 89}; `baselines_formed` {`formed` 9, `residents` 10, `forming_resident_codes` ["R08"], `restarts` [{"resident_code": "R07", "restart_count": 1}]}; `alarms_raised` {`count` 2, `resident_codes` ["R09", "R10"], `not_reviewed_count` 2} |
| 3 | Inspect `funnel` | `expected` 300, `residents` 10, `days` 30, `received` 281, `missed` 19, `duplicates_removed` 2, `passed_quality` 269, `set_aside` 12, `set_aside_reasons` {`quality_flag_poor` 5, `noise_above_limit` 5, `speech_too_short` 3}, `set_aside_multi_reason` 1, `quarantined` 2, `used` 267 |
| 4 | Inspect `by_resident` | 10 rows in the order of TC-051-05 with fields `resident_code`, `days`, `used_days`, `set_aside_days`, `quarantined_days`, `missed_days`, `used_percent` |
| 5 | Inspect `daily_series` | 30 `DailySeriesPoint` rows; the `2026-10-12` row = {`used` 8, `set_aside` 0, `quarantined` 0, `missed` 2, `silent_device_codes` ["D02"]} |
| 6 | Open Swagger UI `/api/v1/docs`, `GET /analytics` "Try it out" with the researcher token | Response schema `AnalyticsResponse` shown with the same property names; no `note` field inside `kpis` |

### TC-051-09 `not_reviewed_count` drops to 1 after a review on R09 while `count` stays 2

Run on a disposable copy of the DS-07 database (the review changes data).

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/alerts?status=open&resident_code=R09` (clinician token) | 200, 1 item; note its `id` |
| 2 | `POST /api/v1/alerts/{id}/reviews` with body `{"explanations": [], "outcome": "no_concern"}` (clinician token) | 201 `AlertReview` |
| 3 | `GET /api/v1/analytics` (researcher token) | `kpis.alarms_raised.count` 2, `resident_codes` ["R09", "R10"], `not_reviewed_count` 1 |
| 4 | `SELECT r.resident_code, a.status FROM alerts a JOIN residents r ON r.id=a.resident_id ORDER BY 1;` | R09 `acknowledged`, R10 `open` |

### TC-051-10 Zero residents / `expected = 0` returns null percentages without an exception

| Step | Action | Expected Result |
|---|---|---|
| 1 | REPL: `E = run_pipeline([], [], [], TEST_V0_1, datetime(2026,10,30,15,tzinfo=ZoneInfo("America/Chicago"))).analytics` | No exception |
| 2 | `E.kpis["checkins_received"], E.kpis["used_for_scoring"]` | `{'value': 0, 'expected': 0, 'percent': None}` twice |
| 3 | `E.by_resident, len(E.daily_series)` | `()` and `30` (days still listed, all zero) |

### TC-051-11 Clinician and unauthenticated calls are refused

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/analytics` with the clinician token | 403, problem body `type` ends with `FORBIDDEN`; no `kpis` in the body |
| 2 | `GET /api/v1/analytics` without `Authorization` | 401 |
| 3 | `GET /api/v1/analytics` with the admin token | 200 with the same `kpis` as TC-051-08 |
| 4 | Search the researcher response body for any e-mail address, name or audio field | None present; only counts, dates and study IDs |

### TC-051-12 Response uses the latest succeeded run's as-of and no float rounding outside `pct`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT id, as_of FROM pipeline_runs WHERE status='succeeded' ORDER BY started_at DESC LIMIT 1;` | as-of 2026-10-30 20:00:00+00 |
| 2 | `GET /api/v1/analytics` `meta.as_of` and `pipeline_run.id` | `meta.as_of` "2026-10-30T20:00:00Z"; `pipeline_run.id` equals step 1 id |
| 3 | `GET /api/v1/residents` `window` | `{"from": "2026-10-01", "to": "2026-10-30", "days": 30}`, the same window as `period` |
| 4 | Inspect every `percent` / `used_percent` | Integers (no decimals) |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/analytics` (researcher) | 200 `AnalyticsResponse` with `meta`, `period`, `kpis`, `daily_series`, `funnel`, `by_resident`, `alarm_timing`, `review_outcomes` null, `status_totals`, `status_counts`, `resident_outcomes`, `pipeline_run` |
| 2 | Validate the body against `docs/api_reference/openapi.json` (or `pytest tests/integration/api/test_analytics.py -q`) | Valid; test exit code 0 |
| 3 | `alarm_timing` (test_v0_1 with DS-10) | R09 Sudden step 2026-10-21 → 2026-10-21 `delay_days` 0; R10 Slow drift 2026-10-17 → 2026-10-24 `delay_days` 7; eight `correct_no_alarm` |
| 4 | Clinician call | 403 `FORBIDDEN` |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT status, count(*) FROM processed_sessions GROUP BY 1;` | usable 267, set_aside 12, quarantined 2, duplicate 2 (matches `kpis.used_for_scoring.count` and funnel) |
| 2 | `SELECT count(*) FROM day_ledger WHERE status IN ('missing_resident','missing_device_gap');` | `19` (= `funnel.missed`) |
| 3 | `SELECT count(*) FROM alerts WHERE local_date BETWEEN '2026-10-01' AND '2026-10-30' AND (closed_reason IS DISTINCT FROM 'superseded by rebuild');` | `2` (= `kpis.alarms_raised.count`) |
| 4 | `\dt` | No table storing `AnalyticsSummary` (computed at request time, TRD 20 §4.6) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Clinician `GET /api/v1/analytics` | 403 `FORBIDDEN` |
| 2 | No token | 401 |
| 3 | Zero residents (TC-051-10) | Null percentages, no exception |
| 4 | Fresh migrated database with no succeeded pipeline run, `GET /api/v1/analytics` as researcher | FEAT-035 empty-state behaviour: 200 with `pipeline_run` null and no alarm counted; the Study team page (FEAT-072) shows "No pipeline run yet" |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-051-AC-01 | `pytest tests/unit/analytics/test_aggregates.py -q` passes AN-01..AN-05; 1 of 8 → 13 | TC-051-01 |
| FEAT-051-AC-02 | SRC-05 summary equals every TRD 07 §4.13 value | TC-051-03, TC-051-04, TC-051-05 |
| FEAT-051-AC-03 | 30 `daily_series` rows equal the TRD 14 §4.9.2 list; Oct 12 `silent_device_codes` ["D02"] | TC-051-06 |
| FEAT-051-AC-04 | DS-07 `GET /api/v1/analytics` as researcher returns the E-18 example `kpis`, `funnel`, `by_resident` and passes OpenAPI validation | TC-051-08, API Validation step 2 |
| FEAT-051-AC-05 | Daily sums 267, 12, 2, 19 equal `status_totals` | TC-051-07 |
| FEAT-051-AC-06 | After a review on R09, `not_reviewed_count` 1 while `count` stays 2 | TC-051-09 |
| FEAT-051-AC-07 | Zero residents returns null percentages and no exception | TC-051-10 |

## Test Data Requirements

- DS-07 (seed `test_v0_1`), DS-10 (`tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv`), SRC-05 via `tests.unit.analytics.src05`.
- A disposable copy of the DS-07 database for TC-051-09.
- `SEED_ADMIN_PASSWORD`, `SEED_CLINICIAN_PASSWORD`, `SEED_RESEARCHER_PASSWORD` from the environment file; `PIPELINE_PROFILE=test_v0_1`.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-051-FR-01 / ANL-061, ANL-003 | FEAT-051 | TC-051-01, TC-051-03 |
| FEAT-051-FR-02 / FR-312, API-069 | FEAT-051 | TC-051-02 |
| FEAT-051-FR-03 / FR-313 | FEAT-051 | TC-051-03, TC-051-04 |
| FEAT-051-FR-04 / FR-313, FR-314 | FEAT-051 | TC-051-03 |
| FEAT-051-FR-05 / ANL-063 | FEAT-051 | TC-051-01, TC-051-10, TC-051-12 |
| FEAT-051-FR-06 | FEAT-051 | TC-051-03 |
| FEAT-051-FR-07 / ANL-065 | FEAT-051 | TC-051-03, TC-051-09 |
| FEAT-051-FR-08 / FR-315 | FEAT-051 | TC-051-06 |
| FEAT-051-FR-09 / FR-316 | FEAT-051 | TC-051-04 |
| FEAT-051-FR-10 / FR-317, UX-369 | FEAT-051 | TC-051-05 |
| FEAT-051-FR-11 / ANL-062, NFR-128, API-006 | FEAT-051 | TC-051-07, Database Validation |
| FEAT-051-FR-12 / FR-322, API-087 | FEAT-051 | TC-051-08 |
| FEAT-051-FR-13 / API-069, NFR-128 | FEAT-051 | TC-051-12 |
| AN-01..AN-05, TST-011 | FEAT-051 | TC-051-01 |
| TDV-074, OAS-028, OAS-024 | FEAT-051 | TC-051-06, TC-051-07, TC-051-08 |
| TDV-076 | FEAT-051 | TC-051-09 |
| FR-310 | FEAT-051 | TC-051-11 |
