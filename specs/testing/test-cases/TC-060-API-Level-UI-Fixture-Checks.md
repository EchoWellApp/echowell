# API-level UI fixture checks (DS-07: overview, devices, alerts, data alerts, analytics)

## Feature Description

FEAT-060 proves, before any page is built, that the API returns exactly the values the wireframe v0.2 pages (Resident list, Resident chart, Study team, New admissions) must render for the reference data DS-07 (SRC-05 ingested under `test_v0_1`, roster loaded, as-of set by an explicit pipeline run with no clock override) with DS-10 loaded. The checks cover `GET /api/v1/residents` (rows, default order R09, R10, R03, R08, R01, R02, R04, R05, R06, R07, summary 2/2/0/6, attention flags, `alarm_reviewed`, `restart_cause`), the other sorts, the 30-day counts and last check-in, `GET /api/v1/devices`, R09's detail and check-in log, `GET /api/v1/alerts?status=open` with `leaning_most`, exactly four data alerts, every Study team figure of TRD 14 Table 4.9-E (also recomputed from DS-02) and the state after a review of R09. The assertions in `tests/integration/api/test_ui_fixture_ds07.py` are the specification the frontend fixtures must equal.

## Preconditions

- Empty migrated database, then `python -m backend.cli seed test_v0_1` (roster, users, SRC-05 ingest, `manual` run at as-of 2026-10-30T20:00:00Z) and `python database/seeds/load_evaluation_ground_truth.py tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv`.
- Backend API running with no clock override and no `PIPELINE_AS_OF`; `DATA_SOURCE_LABEL` "pipeline test data v0.1"; `PIPELINE_PROFILE=test_v0_1`.
- Tokens from `POST /api/v1/auth/login` for `admin@example.com`, `clinician@example.com`, `researcher@example.com` (passwords from the `SEED_*` variables).
- TC-060-11 runs on a separate copy of the database or last, because it saves a review.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-060-01 | Every read endpoint reports `meta.as_of` 2026-10-30T20:00:00Z without a clock override | High | API |
| TC-060-02 | `GET /api/v1/residents` default order, summary 2/2/0/6, Table 4.9-B values and attention flags | High | API |
| TC-060-03 | `sort=resident_id` and `sort=last_checkin` orders | Medium | API |
| TC-060-04 | 30-day window semantics and last check-in | High | API |
| TC-060-05 | `GET /api/v1/data-alerts?status=open` returns exactly the four Table 4.9-D rows and none of the non-alerts | High | API |
| TC-060-06 | `GET /api/v1/devices` values incl. D02, D07, D07B and `uploaded_on_as_of_date` | High | API |
| TC-060-07 | `GET /api/v1/analytics` (researcher) equals Table 4.9-E incl. alarm timing | High | API |
| TC-060-08 | `GET /api/v1/alerts?status=open` returns R09 and R10 with open days, tallies and `leaning_most` | High | API |
| TC-060-09 | R09 detail and check-in log; every log ends with `checkins_started` on 2026-10-01 | High | API |
| TC-060-10 | Table 4.9-E figures recomputed from DS-02 equal the API | High | Analytics |
| TC-060-11 | After a clinician review of R09: open total 1, tallies unchanged | High | API |
| TC-060-12 | Resident list, data alerts and analytics agree for the same as-of | Medium | API |
| TC-060-13 | Clinician gets 403 on analytics; responses validate against OpenAPI | High | Security |

### TC-060-01 Every read endpoint reports `meta.as_of` 2026-10-30T20:00:00Z without a clock override

| Step | Action | Expected Result |
|---|---|---|
| 1 | Admin `GET /api/v1/pipeline/runs?status=succeeded&limit=1` | Latest succeeded run `trigger` "manual", `as_of` "2026-10-30T20:00:00Z" |
| 2 | Clinician `GET /api/v1/residents`, `GET /api/v1/devices`, `GET /api/v1/alerts`, `GET /api/v1/data-alerts`; researcher `GET /api/v1/analytics` | Each `meta.as_of` "2026-10-30T20:00:00Z", `meta.data_source_label` "pipeline test data v0.1", `meta.facility_tz` "America/Chicago", `meta.baseline_n` 16, `meta.cusum_h` 5.0, `meta.pipeline_profile` "test_v0_1" |
| 3 | Confirm the API process environment | No `PIPELINE_AS_OF`, no frozen clock |

### TC-060-02 `GET /api/v1/residents` default order, summary 2/2/0/6, Table 4.9-B values and attention flags

| Step | Action | Expected Result |
|---|---|---|
| 1 | Clinician `GET /api/v1/residents` | 200; `total` 10; `summary` {"changed": 2, "needs_attention": 2, "learning": 0, "usual": 6} |
| 2 | Read `items[*].resident_code` | R09, R10, R03, R08, R01, R02, R04, R05, R06, R07 |
| 3 | Read `status`, `alarm_since`, `alarm_reviewed` | R09 `alarm_on` 2026-10-21 false; R10 `alarm_on` 2026-10-24 false; all others not `alarm_on`, `alarm_reviewed` null |
| 4 | Read `needs_attention`, `attention_reasons` | R03 true ["high_set_aside"]; R08 true ["baseline_stalled"]; all others false [] |
| 5 | Read `last_30_days` (used · set_aside · quarantined · missed) | R09 30·0·0·0; R10 30·0·0·0; R03 22·7·0·1; R08 13·5·0·12; R01 30·0·0·0; R02 24·0·0·6; R04 30·0·0·0; R05 28·0·2·0; R06 30·0·0·0; R07 30·0·0·0 |
| 6 | Read `device_code`, `device_shared`, `previous_device_code`, `restart_cause`, `baseline_restarted_on` | R02 and R03 D02 shared true; R07 D07B, previous D07, `restart_cause` "device", restarted 2026-10-13; others own device, `restart_cause` null |

### TC-060-03 `sort=resident_id` and `sort=last_checkin` orders

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents?sort=resident_id` | R01, R02, R03, R04, R05, R06, R07, R08, R09, R10 |
| 2 | `GET /api/v1/residents?sort=last_checkin` | R02, R07, R05, R10, R06, R08, R09, R03, R04, R01 |
| 3 | `GET /api/v1/residents?sort=bogus` | 422 `INVALID_QUERY_PARAMETER` |

### TC-060-04 30-day window semantics and last check-in

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents` → `window` | {"from": "2026-10-01", "to": "2026-10-30", "days": 30} (as-of local date and the 29 preceding dates) |
| 2 | R04 `last_30_days.used` | 30 (the 2 duplicate copies excluded) |
| 3 | Missed definition | R02 missed 6 = 5 `missing_resident` + 1 `missing_device_gap`; R03 missed 1 (device gap) |
| 4 | `last_checkin_local` of R09, R10, R03, R08, R01, R02, R04, R05, R06, R07 | Oct 30 at 14:28, 14:39, 14:19, 14:28, 14:07, 14:55, 14:17, 14:40, 14:38, 14:52 (−05:00), i.e. "Oct 30, 2:28 PM CT" etc. — latest non-duplicate record of any status |

### TC-060-05 `GET /api/v1/data-alerts?status=open` returns exactly the four Table 4.9-D rows and none of the non-alerts

| Step | Action | Expected Result |
|---|---|---|
| 1 | Clinician `GET /api/v1/data-alerts?status=open` | 200; `total` 4 |
| 2 | Item 1 | `kind` "baseline_stalled", `resident_code` "R08", `device_code` null, `title` "R08 · baseline stuck at 13 of 16", `detail` "baseline stuck at 13 of 16. 12 missed and 5 set aside in 30 days." |
| 3 | Item 2 | "possible_other_speaker", R05, "R05 · possible other speaker", "2 check-ins held back as possible other voice (Oct 8, Oct 22)." |
| 4 | Item 3 | "high_set_aside", R03, "R03 · many check-ins set aside", "7 of 29 received check-ins set aside (noise, quality flag, too short)." |
| 5 | Item 4 | "device_silent", `resident_code` null, `device_code` "D02", "D02 · device silent all day", "silent all day Oct 12. Affected R02 and R03." |
| 6 | Non-alerts | No R08 `high_set_aside`, no D08 or D07 `device_silent`, no R07 `baseline_stalled` |
| 7 | Each item | `status` "open", `first_detected_at` = `last_detected_at` = "2026-10-30T20:00:00Z" |

### TC-060-06 `GET /api/v1/devices` values incl. D02, D07, D07B and `uploaded_on_as_of_date`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Clinician `GET /api/v1/devices` | 200; `total` 10; codes D01, D02, D04, D05, D06, D07, D07B, D08, D09, D10 (natural order, no D03) |
| 2 | D02 | `resident_codes` ["R02", "R03"], `shared` true, `last_upload_at` "2026-10-30T19:55:23Z", `silent_days_last_30` ["2026-10-12"], `device_gap_days_last_30` ["2026-10-12"], `firmware_version` "fw-1.0.0", `uploaded_on_as_of_date` true |
| 3 | D07B | `replaces_device_code` "D07", `in_use_since` "2026-10-13", `in_use_until` null, `last_upload_at` "2026-10-30T19:52:57Z", `uploaded_on_as_of_date` true |
| 4 | D07 | `active` false, `in_use_since` "2026-10-01", `in_use_until` "2026-10-12", `replaced_by_device_code` "D07B", `uploaded_on_as_of_date` false |
| 5 | All nine active devices | `uploaded_on_as_of_date` true, `firmware_version` "fw-1.0.0" |

### TC-060-07 `GET /api/v1/analytics` (researcher) equals Table 4.9-E incl. alarm timing

| Step | Action | Expected Result |
|---|---|---|
| 1 | Researcher `GET /api/v1/analytics` | 200 |
| 2 | `kpis` | received 281 / 300 / 94; used 267 / 300 / 89; baselines `formed` 9 of `residents` 10, `forming_resident_codes` ["R08"], `restarts` [{"resident_code": "R07", "restart_count": 1}]; alarms `count` 2, `resident_codes` ["R09", "R10"], `not_reviewed_count` 2 |
| 3 | `funnel` | 300 → 281 (`missed` 19, `duplicates_removed` 2) → 269 (`set_aside` 12: quality_flag_poor 5, noise_above_limit 5, speech_too_short 3, `set_aside_multi_reason` 1) → 267 (`quarantined` 2) |
| 4 | `by_resident` | R08 43, R03 73, R02 80, R05 93, then R01, R04, R06, R07, R09, R10 at 100 |
| 5 | `daily_series` | 30 rows equal to the TRD 14 §4.9.2 per-day list (see TC-051-06); day 1 10/0/0/0; 2026-10-12 8/0/0/2 with `silent_device_codes` ["D02"]; day 30 10/0/0/0 |
| 6 | `alarm_timing` | R09 "Sudden step" `change_began` 2026-10-21 `alarm_rang` 2026-10-21 `delay_days` 0 `result` "detected"; R10 "Slow drift" 2026-10-17 → 2026-10-24, 7 days, "detected"; the other 8 "None", nulls, `result` "correct_no_alarm" |
| 7 | `review_outcomes` | null (test profile) |

### TC-060-08 `GET /api/v1/alerts?status=open` returns R09 and R10 with open days, tallies and `leaning_most`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Clinician `GET /api/v1/alerts?status=open` | 200; `total` 2, ordered by `triggered_at` |
| 2 | R09 item | `session_id` "R09-20261021-01", `local_date` "2026-10-21", `status` "open", `open_days` 9, `current_tally` 26.830256 ±1e-6, `leaning_most` ["number_of_pauses", "loudness_dbfs", "voiced_fraction"] |
| 3 | R10 item | "R10-20261024-01", "2026-10-24", "open", `open_days` 6, `current_tally` 13.418183 ±1e-6, `leaning_most` ["number_of_pauses", "articulation_rate_syl_per_s", "speech_rate_syl_per_s"] |
| 4 | Review state | Both `reviewed` false, `review_count` 0, `last_reviewed_at` null, `snoozed_until` null |

### TC-060-09 R09 detail and check-in log; every log ends with `checkins_started` on 2026-10-01

| Step | Action | Expected Result |
|---|---|---|
| 1 | Clinician `GET /api/v1/residents/R09` | `status` "alarm_on", `alarm_since` "2026-10-21", `baseline` {`state` "frozen", `n_usable` 16, `n_required` 16, `first_session_id` "R09-20261001-01", `frozen_after_session_id` "R09-20261016-01", `first_local_date` "2026-10-01", `frozen_after_local_date` "2026-10-16"}, `watching_since` "2026-10-17", `current_tally` 26.830256, `needs_attention` false, `alarm_reviewed` false, `window` {"from": "2026-10-01", "to": "2026-10-30", "days": 30} |
| 2 | `GET /api/v1/residents/R09/checkins?limit=500` | `total` 4, newest first: `alarm_on` 2026-10-21 (`detail` "tally crossed 5.0", `cusum_tally` 5.431965), `watching_started` 2026-10-17, `baseline_complete` 2026-10-16 (`detail` "16 of 16"), `checkins_started` 2026-10-01 (`session_id` "R09-20261001-01", `device_code` "D09"); `device_code` null on the other events |
| 3 | `GET /api/v1/residents/R07/checkins?limit=500` | Last item `checkins_started` 2026-10-01, `session_id` "R07-20261001-01", `epoch_number` 1, `device_code` "D07"; a `baseline_restarted` event on 2026-10-13 with `detail` "new epoch 2 on device D07B", `restart_cause` "device" |
| 4 | Repeat step 2 for R01–R06, R08, R10 | Each log ends with `checkins_started` on 2026-10-01 |
| 5 | `GET /api/v1/residents/R99` | 404 `RESIDENT_NOT_FOUND` |

### TC-060-10 Table 4.9-E figures recomputed from DS-02 equal the API

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation/test_ui_fixture_recompute.py -q` | `test_study_team_figures_match_the_answer_key` passes: every Table 4.9-E figure recomputed from Annotated_sessions, Exp_status_counts and Exp_resident_outcomes equals the API value |

### TC-060-11 After a clinician review of R09: open total 1, tallies unchanged

| Step | Action | Expected Result |
|---|---|---|
| 1 | Clinician `GET /api/v1/alerts?status=open&resident_code=R09`; note `id` | 1 item |
| 2 | `POST /api/v1/alerts/{id}/reviews` `{"explanations": [], "outcome": "no_concern"}` | 201 |
| 3 | `GET /api/v1/alerts?status=open` | `total` 1 (R10 only) |
| 4 | `GET /api/v1/alerts?resident_code=R09` | `status` "acknowledged", `current_tally` 26.830256 ±1e-6 (unchanged) |
| 5 | `GET /api/v1/residents` | R09 `status` still "alarm_on", `alarm_reviewed` true; `summary` still 2/2/0/6; R10 `alarm_reviewed` false |
| 6 | Researcher `GET /api/v1/analytics` | `kpis.alarms_raised.not_reviewed_count` 1, `count` 2 |
| 7 | `SELECT r.resident_code, c.current_tally FROM cusum_state c JOIN residents r ON r.id=c.resident_id WHERE c.alarm_on;` | R09 26.830256, R10 13.418183 (unchanged) |

### TC-060-12 Resident list, data alerts and analytics agree for the same as-of

| Step | Action | Expected Result |
|---|---|---|
| 1 | Compare R08 across `GET /api/v1/residents` (13/5/0/12), `GET /api/v1/analytics` `by_resident` R08 (`used_days` 13, `set_aside_days` 5, `missed_days` 12) and the baseline_stalled detail ("12 missed and 5 set aside") | All agree |
| 2 | Compare R03: resident row set_aside 7, high_set_aside detail "7 of 29", `by_resident` `set_aside_days` 7 | All agree |
| 3 | Sum of `last_30_days.missed` over the 10 residents | 19 = `funnel.missed` |

### TC-060-13 Clinician gets 403 on analytics; responses validate against OpenAPI

| Step | Action | Expected Result |
|---|---|---|
| 1 | Clinician `GET /api/v1/analytics` | 403 `FORBIDDEN` |
| 2 | `pytest tests/integration/api/test_ui_fixture_ds07.py -q` | All tests pass (each response validated against the OpenAPI schema, TST-061) |
| 3 | Any endpoint without a token | 401 |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents` (A, C, Rs) | 200 `ResidentsOverviewResponse` |
| 2 | `GET /api/v1/residents/R09`, `/R09/checkins` | 200 `ResidentDetail`, `CheckinEventList` |
| 3 | `GET /api/v1/devices` | 200 `DeviceList`, `total` 10 |
| 4 | `GET /api/v1/alerts?status=open` | 200 `AlertList`, `total` 2 |
| 5 | `GET /api/v1/data-alerts?status=open` | 200 `DataAlertList`, `total` 4 |
| 6 | `GET /api/v1/analytics` researcher 200 / clinician 403 | As stated |
| 7 | `POST /api/v1/alerts/{id}/reviews` as researcher | 403 (reviews are admin or clinician only) |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT count(*) FROM raw_sessions; SELECT count(*) FROM evaluation_ground_truth;` | 283; 10 |
| 2 | `SELECT status, count(*) FROM alerts GROUP BY 1;` before TC-060-11 | `open` 2 |
| 3 | `SELECT status, count(*) FROM data_alerts GROUP BY 1;` | `open` 4 |
| 4 | After TC-060-11: `SELECT count(*) FROM alert_reviews; SELECT action FROM audit_logs WHERE action='alert.reviewed';` | 1; one `alert.reviewed` row |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Clinician `GET /api/v1/analytics` | 403 `FORBIDDEN` |
| 2 | `GET /api/v1/residents?sort=bogus` | 422 `INVALID_QUERY_PARAMETER` |
| 3 | `GET /api/v1/residents/R99` | 404 `RESIDENT_NOT_FOUND` |
| 4 | Researcher `POST /api/v1/alerts/{id}/reviews` | 403 |
| 5 | Non-alerts of TC-060-05 step 6 | Absent |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-060-AC-01 | `GET /api/v1/residents` summary 2/2/0/6, default order R09…R07, Table 4.9-B values and attention flags | TC-060-02, TC-060-04 |
| FEAT-060-AC-02 | `GET /api/v1/alerts?status=open` exactly R09 (open_days 9, 26.830256) and R10 (open_days 6, 13.418183) with the `leaning_most` lists | TC-060-08 |
| FEAT-060-AC-03 | `GET /api/v1/data-alerts?status=open` exactly the four Table 4.9-D rows and nothing else | TC-060-05 |
| FEAT-060-AC-04 | `GET /api/v1/analytics` researcher: 281/300/94, 267/300/89, 9 of 10, 2 alarms, funnel 300/281/269/267 with 5/5/3, by-resident R08 43, R03 73, R02 80, R05 93, others 100, alarm timing R09 0 days, R10 7 days | TC-060-07 |
| FEAT-060-AC-05 | Every Table 4.9-E figure recomputed from DS-02 equals the API | TC-060-10 |
| FEAT-060-AC-06 | D02 `device_gap_days_last_30` ["2026-10-12"], `uploaded_on_as_of_date` true; D07 `in_use_until` "2026-10-12", `replaced_by_device_code` "D07B", `uploaded_on_as_of_date` false; every log ends with `checkins_started` 2026-10-01 (R07 on D07) | TC-060-06, TC-060-09 |
| FEAT-060-AC-07 | After a clinician review of R09, open `total` 1 and R09's `current_tally` still 26.830256 | TC-060-11 |

## Test Data Requirements

- DS-07 (seed `test_v0_1`) plus DS-10; a separate copy for TC-060-11; DS-02 for TC-060-10.
- `SEED_ADMIN_PASSWORD`, `SEED_CLINICIAN_PASSWORD`, `SEED_RESEARCHER_PASSWORD`; `DATA_SOURCE_LABEL="pipeline test data v0.1"`.
- Study IDs R01–R10, devices D01–D10 and D07B only; synthetic R99 for the 404 check.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-060-FR-01 / TDV-061, API-069 | FEAT-060 | TC-060-01 |
| FEAT-060-FR-02 / TDV-062, TDV-063, FR-137, FR-302, AC-FR-04, OAS-021 | FEAT-060 | TC-060-02 |
| FEAT-060-FR-03 / TDV-063 | FEAT-060 | TC-060-03 |
| FEAT-060-FR-04 / TDV-064, TDV-065 | FEAT-060 | TC-060-04 |
| FEAT-060-FR-05 / TDV-066, API-086 | FEAT-060 | TC-060-06 |
| FEAT-060-FR-06 / TDV-066 | FEAT-060 | TC-060-09 |
| FEAT-060-FR-07 / TDV-067, FR-263, OAS-027 | FEAT-060 | TC-060-08 |
| FEAT-060-FR-08 / TDV-068, FR-301, AC-FR-12 | FEAT-060 | TC-060-05 |
| FEAT-060-FR-09 / TDV-069 | FEAT-060 | TC-060-08 |
| FEAT-060-FR-10 / TDV-074, FR-323, AC-FR-13, OAS-028 | FEAT-060 | TC-060-07 |
| FEAT-060-FR-11 / TDV-075 | FEAT-060 | TC-060-10 |
| FEAT-060-FR-12 / TDV-076, TST-056 | FEAT-060 | TC-060-11 |
| FEAT-060-FR-13 / NFR-128 | FEAT-060 | TC-060-12 |
| FR-310, TST-061 | FEAT-060 | TC-060-13 |
| AC-TDV-07, AC-TDV-10, AC-TDV-11 | FEAT-060 | TC-060-02, TC-060-05, TC-060-07 |
