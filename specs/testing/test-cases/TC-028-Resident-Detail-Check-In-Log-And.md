# Resident detail, check-in log and features APIs

## Feature Description

Three read-only endpoints serve the v0.2 Resident chart: `GET /api/v1/residents/{resident_code}` (TRD 19 E-09) returns the banner, Summary and Baseline facts with structured `explanation` facts, the attention flag, `alarm_reviewed`, `restart_cause`, `device`, `current_epoch`, `baseline`, `watching_since`, `current_tally`, last check-in and the 30-day `window`; `GET /residents/{resident_code}/checkins` (E-10) returns the newest-first check-in log of the 9 event types including the derived `checkins_started`, never duplicates or usable check-ins; `GET /residents/{resident_code}/features` (E-11) returns the 7 scored measurements with raw, adjusted and unsigned z values and the 12 stored-not-scored keys. The API returns facts only, no clinical prose. All roles may read; withdrawn residents stay readable. Source: FEAT-028; TRD 05 API-075..API-078, API-138; TRD 23 §4.4.1, §4.4.3, §4.4.4; TRD 24 D-41, D-64, D-113, D-114.

## Preconditions

1. Local Docker Compose stack running; environment file from `.env.development.example`.
2. **DS-07 state:** `docker compose exec backend python -m backend.cli seed test_v0_1` (as-of `2026-10-30T20:00:00Z`).
3. `API=http://localhost:8000/api/v1`; tokens `ADMIN`, `CLIN`, `RES` from `POST $API/auth/login` with the `SEED_*` passwords; `KEY` = the ingest API key from the environment file.
4. `psql` read access; local development stack with dev requirements for the `pytest` cases.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-028-01 | Unknown resident R11 returns 404 `RESIDENT_NOT_FOUND` on detail, checkins and features | High | Negative |
| TC-028-02 | DS-07 R09 detail: alarm, baseline, watching since, tally, explanation, window | High | Positive |
| TC-028-03 | DS-07 R07 check-in log: `baseline_restarted` with device restart fields, `baseline_complete`, `checkins_started` on D07 | High | Positive |
| TC-028-04 | DS-07 event details for R03 (set aside, device silent) and R05 (quarantined) | High | Positive |
| TC-028-05 | DS-07 R04 log has no event for duplicates and only the 9 event types | High | Positive |
| TC-028-06 | `from` > `to` and a 367-day span return 422 `INVALID_QUERY_PARAMETER` | High | Negative |
| TC-028-07 | DS-07 R09 features: 7 series in contract order, loudness baseline values, z values, 12 stored keys | High | Positive |
| TC-028-08 | DS-07 R08 detail and features: forming baseline, attention flag, all z null | High | Positive |
| TC-028-09 | All three responses validate against their schemas and contain `meta` | High | API |
| TC-028-10 | Same-date events follow the UX-141 order (integration fixture) | High | Positive |
| TC-028-11 | DS-07 R09 check-in log: 4 events newest first with exact details | Medium | Positive |
| TC-028-12 | Withdrawn resident detail is still returned | Medium | Positive |
| TC-028-13 | Role access: every user role 200, API key 401; responses carry facts only | Medium | Security |
| TC-028-14 | `from`/`to` filtering of the check-in log and features window | Medium | API |
| TC-028-15 | Malformed resident code returns 404; malformed date returns 422 | Low | Negative |

### TC-028-01 Unknown resident R11 returns 404 `RESIDENT_NOT_FOUND` on detail, checkins and features

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s -i $API/residents/R11 -H "Authorization: Bearer $CLIN"` | HTTP 404; `type` "urn:echowell:error:RESIDENT_NOT_FOUND"; `title` "Resident not found"; `detail` "No resident with code 'R11'." |
| 2 | `GET $API/residents/R11/checkins` | HTTP 404 `RESIDENT_NOT_FOUND` |
| 3 | `GET $API/residents/R11/features` | HTTP 404 `RESIDENT_NOT_FOUND` |

Note: TRD 19 §4.2 and FEAT-028 Error Handling give the detail "No resident with code 'R11'."; the code returns "No resident R11." (`backend/services/resident_service.py:268`).

### TC-028-02 DS-07 R09 detail: alarm, baseline, watching since, tally, explanation, window

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/residents/R09` as clinician | HTTP 200 |
| 2 | Status facts | `status` "alarm_on"; `alarm_since` "2026-10-21"; `open_alert_id` a uuid; `needs_attention` false; `attention_reasons` []; `alarm_reviewed` false; `restart_cause` null |
| 3 | `baseline` | `{"state": "frozen", "n_usable": 16, "n_required": 16, "first_session_id": "R09-20261001-01", "frozen_after_session_id": "R09-20261016-01", "first_local_date": "2026-10-01", "frozen_after_local_date": "2026-10-16"}` |
| 4 | Other facts | `watching_since` "2026-10-17"; `current_tally` 26.830256 (±1e-6); `epoch_count` 1; `current_epoch.epoch_number` 1, `device_code` "D09", `from_value` null, `to_value` null |
| 5 | `explanation` | `{"compared_with": "own_baseline", "alarm_crossed_on": "2026-10-21", "still_above_line": true, "baseline_restarted_on": null, "baseline_n_usable": 16, "baseline_n_required": 16}` — no sentence-type field |
| 6 | `window`, `last_30_days`, last check-in, device | `window` `{"from": "2026-10-01", "to": "2026-10-30", "days": 30}`; `last_30_days` 30 · 0 · 0 · 0; `last_checkin_at` "2026-10-30T19:28:04Z"; `last_checkin_local` "2026-10-30T14:28:04-05:00"; `device` `{"device_code": "D09", "shared": false, "shared_with": [], "previous_device_code": null}` |

### TC-028-03 DS-07 R07 check-in log: `baseline_restarted` with device restart fields, `baseline_complete`, `checkins_started` on D07

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/residents/R07/checkins` | HTTP 200; items newest first by `local_date` |
| 2 | Find `event_type` "baseline_restarted" | One item: `local_date` "2026-10-13", `epoch_number` 2, `detail` "new epoch 2 on device D07B", `restart_cause` "device", `previous_device_code` "D07", `from_value` "D07", `to_value` "D07B", `device_code` null |
| 3 | Find `event_type` "baseline_complete" | `local_date` "2026-10-28", `detail` "16 of 16" |
| 4 | Every other item | `restart_cause`, `previous_device_code`, `from_value`, `to_value` all null |
| 5 | Last (oldest) item | `event_type` "checkins_started", `local_date` "2026-10-01", `session_id` "R07-20261001-01", `epoch_number` 1, `device_code` "D07", `detail` null |
| 6 | `GET $API/residents/R07` | `restart_cause` "device"; `current_epoch.epoch_number` 2, `device_code` "D07B", `from_value` "D07", `to_value` "D07B"; `epoch_count` 2; `device.previous_device_code` "D07" |

### TC-028-04 DS-07 event details for R03 (set aside, device silent) and R05 (quarantined)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/residents/R03/checkins` | Contains `set_aside` on "2026-10-18" with `detail` "quality flag poor; noise above limit" |
| 2 | Same response | Contains `device_silent` on "2026-10-12" with `detail` "all residents on shared device D02 have no record" |
| 3 | `GET $API/residents/R05/checkins` | Contains `quarantined` on "2026-10-08" with `detail` "possible other speaker (F0 z=-8.61; composite features with \|z\|>=3: 4)" |
| 4 | `GET $API/residents/R02/checkins` | Contains `missed` on "2026-10-04" with `detail` "no record received" and `device_silent` on "2026-10-12" |

### TC-028-05 DS-07 R04 log has no event for duplicates and only the 9 event types

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/residents/R04/checkins?limit=500` | HTTP 200 |
| 2 | Search items for `session_id` R04-20261005-01 and R04-20261018-01 | No item references either duplicate arrival |
| 3 | Collect distinct `event_type` values | Each is one of `alarm_on`, `watching_started`, `baseline_complete`, `baseline_restarted`, `quarantined`, `set_aside`, `device_silent`, `missed`, `checkins_started`; for R04 exactly `watching_started` (2026-10-17), `baseline_complete` (2026-10-16), `checkins_started` (2026-10-01); `total` 3 |
| 4 | Confirm no usable check-in is listed as an event | No item per usable session; `total` 3 although R04 has 30 usable sessions |

### TC-028-06 `from` > `to` and a 367-day span return 422 `INVALID_QUERY_PARAMETER`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/residents/R09/checkins?from=2026-10-20&to=2026-10-10` | HTTP 422; `type` "urn:echowell:error:INVALID_QUERY_PARAMETER"; detail "'from' must not be later than 'to'" |
| 2 | `GET $API/residents/R09/checkins?from=2025-10-29&to=2026-10-30` (367 days) | HTTP 422 `INVALID_QUERY_PARAMETER`; detail "'from'..'to' may span at most 366 days" |
| 3 | `GET $API/residents/R09/checkins?from=2025-10-30&to=2026-10-30` (366 days) | HTTP 200 |

### TC-028-07 DS-07 R09 features: 7 series in contract order, loudness baseline values, z values, 12 stored keys

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/residents/R09/features` | HTTP 200; `resident_code` "R09"; `epoch_number` 1 |
| 2 | `scored_features[].feature_key` | Exactly 7 in order loudness_dbfs, total_phrase_duration_s, speech_rate_syl_per_s, articulation_rate_syl_per_s, number_of_pauses, pause_fraction, voiced_fraction |
| 3 | Loudness series | `label` "Quieter (loudness)"; `unit` "dBFS"; `composite_sign` -1; `baseline_median` -22.405 (±1e-6); `baseline_robust_spread` 2.14977 (±1e-6) |
| 4 | Loudness point `R09-20261021-01` | `local_date` "2026-10-21"; `raw_value` -28.29; `adjusted_value` -28.29; `z` -2.737502 (±1e-6); `in_baseline` false |
| 5 | Loudness point `R09-20261016-01` (a baseline session) | `z` null; `in_baseline` true |
| 6 | `stored_feature_keys` | mean_f0_hz, f0_variability_st, jitter_local_pct, shimmer_local_pct, hnr_db, cpps_db, alpha_ratio_db, hammarberg_index_db, mfcc1, mfcc2, mfcc3, mfcc4 (12, in this order); no series for them |

### TC-028-08 DS-07 R08 detail and features: forming baseline, attention flag, all z null

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/residents/R08` | `status` "baseline_forming"; `needs_attention` true; `attention_reasons` ["baseline_stalled"]; `alarm_reviewed` null; `alarm_since` null |
| 2 | Baseline and counts | `baseline.state` "forming", `n_usable` 13, `n_required` 16, `first_session_id`, `frozen_after_session_id`, `first_local_date`, `frozen_after_local_date` all null; `watching_since` null; `last_30_days` 13 · 5 · 0 · 12 |
| 3 | `current_tally` | 0 or null, equal to `SELECT current_tally FROM cusum_state cs JOIN residents r ON r.id=cs.resident_id WHERE r.resident_code='R08';` (null when no row) |
| 4 | `GET $API/residents/R08/features` | 7 series; every point has `z` null; `baseline_median` and `baseline_robust_spread` null on every series |

### TC-028-09 All three responses validate against their schemas and contain `meta`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Validate `GET /residents/R09` against `ResidentDetail` from `GET $API/openapi.json` | Valid; `meta` has the seven fields (`as_of` "2026-10-30T20:00:00Z") |
| 2 | Validate `GET /residents/R09/checkins` against `CheckinEventList` | Valid; `meta`, `items`, `total`, `limit` 50, `offset` 0; every item has all `CheckinEvent` properties (null where not applicable) |
| 3 | Validate `GET /residents/R09/features` against `FeaturesResponse` | Valid; `meta` present |
| 4 | Check time formats | `*_at` UTC with `Z`; `*_local` with `-05:00`; `local_date` `YYYY-MM-DD` |

### TC-028-10 Same-date events follow the UX-141 order (integration fixture)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/integration/api/test_residents.py::test_same_date_events_follow_ux_141 -q` | Passes: fixture rows producing `set_aside`, `baseline_restarted` and `watching_started` on one local date (inserted in that order) come back as `watching_started`, `baseline_restarted`, `set_aside` |
| 2 | DS-07 cross-check: `GET $API/residents/R09/checkins` | Items are sorted by `local_date` descending (2026-10-21, 2026-10-17, 2026-10-16, 2026-10-01); no client-side re-sort is needed |

### TC-028-11 DS-07 R09 check-in log: 4 events newest first with exact details

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/residents/R09/checkins` | `total` 4 |
| 2 | Items in order | (1) `alarm_on` 2026-10-21, `session_id` "R09-20261021-01", `detail` "tally crossed 5.0", `cusum_tally` 5.431965; (2) `watching_started` 2026-10-17, "R09-20261017-01", `detail` null; (3) `baseline_complete` 2026-10-16, "R09-20261016-01", `detail` "16 of 16"; (4) `checkins_started` 2026-10-01, `device_code` "D09" |

### TC-028-12 Withdrawn resident detail is still returned

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker compose exec backend python -m backend.cli withdraw-resident R06 --on 2026-10-30` | Exit 0 |
| 2 | `GET $API/residents/R06` | HTTP 200; `resident_status` "withdrawn"; `withdrawn_on` "2026-10-30" |
| 3 | `GET $API/residents/R06/checkins` and `/features` | Both HTTP 200 |
| 4 | Restore: `seed test_v0_1 --reset` | DS-07 state again |

### TC-028-13 Role access: every user role 200, API key 401; responses carry facts only

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /residents/R09`, `/checkins`, `/features` with each of `$ADMIN`, `$CLIN`, `$RES` | 200 for all nine requests |
| 2 | Same three paths with `X-API-Key: $KEY` | 401 `NOT_AUTHENTICATED` each |
| 3 | Inspect the R09 detail for demographic and identifying fields | Only `sex` as demographic; no name, room, date of birth or `payload` field |
| 4 | Inspect all string values of the R09 detail | Only codes, dates, enum values and fixed fact strings; no sentence of clinical wording (the words "diagnosis" and "severity" are absent) |

### TC-028-14 `from`/`to` filtering of the check-in log and features window

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/residents/R09/checkins?from=2026-10-16&to=2026-10-20` | `total` 2: `watching_started` 2026-10-17, `baseline_complete` 2026-10-16 |
| 2 | `GET $API/residents/R09/checkins?limit=1&offset=1` | 1 item (`watching_started`); `total` 4 |
| 3 | `GET $API/residents/R09/features?from=2026-10-21&to=2026-10-21` | Each series has exactly 1 point, `session_id` "R09-20261021-01" |
| 4 | `GET $API/residents/R09/features?from=2026-10-25&to=2026-10-20` | HTTP 422 `INVALID_QUERY_PARAMETER` |

### TC-028-15 Malformed resident code returns 404; malformed date returns 422

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/residents/r09` (lower case, does not match `^[A-Z0-9]{1,16}$`) | HTTP 404 `RESIDENT_NOT_FOUND` |
| 2 | `GET $API/residents/R09/checkins?from=2026-13-01` | HTTP 422 `INVALID_QUERY_PARAMETER` |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /residents/{code}` | 200 `ResidentDetail`; 404 `RESIDENT_NOT_FOUND` for unknown code |
| 2 | `GET /residents/{code}/checkins` | 200 `CheckinEventList` newest first; same-date UX-141 order; 422 for bad range |
| 3 | `GET /residents/{code}/features` | 200 `FeaturesResponse` with 7 `scored_features` and 12 `stored_feature_keys` |
| 4 | Status facts | Detail `status`, `needs_attention`, `attention_reasons`, `alarm_reviewed`, `restart_cause` equal the R-row values of `GET /residents` |
| 5 | Auth | Admin, clinician, researcher 200; API key / anonymous 401 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT current_tally FROM cusum_state cs JOIN epochs e ON e.id=cs.epoch_id JOIN residents r ON r.id=cs.resident_id WHERE r.resident_code='R09' AND e.ended_at IS NULL;` | 26.830256 (±1e-6) = detail `current_tally` |
| 2 | `SELECT z FROM scores s JOIN processed_sessions p ON p.id=s.processed_session_id WHERE p.session_id='R09-20261021-01';` | `z` JSON holds loudness -2.737502 = features point `z` |
| 3 | `SELECT reason_text FROM processed_sessions WHERE session_id='R03-20261018-01';` | "quality flag poor; noise above limit" = `set_aside` event detail |
| 4 | `SELECT d.device_code FROM raw_sessions rs JOIN devices d ON d.id=rs.device_id WHERE rs.session_id='R07-20261001-01' LIMIT 1;` | "D07" = R07 `checkins_started.device_code` |
| 5 | Row counts before and after all cases (except TC-028-12) | Unchanged (read-only) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Unknown code R11 on the three paths | 404 `RESIDENT_NOT_FOUND` |
| 2 | Lower-case code `r09` | 404 `RESIDENT_NOT_FOUND` |
| 3 | `from` > `to`; 367-day span; malformed date | 422 `INVALID_QUERY_PARAMETER` |
| 4 | API key / anonymous | 401 |
| 5 | `docker compose stop db` then `GET /residents/R09` | 503 `SERVICE_UNAVAILABLE`; restart with `docker compose start db` |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-028-AC-01 | R11 returns 404 `urn:echowell:error:RESIDENT_NOT_FOUND` on detail, checkins and features | TC-028-01 |
| FEAT-028-AC-02 | DS-07 R09: `alarm_on`, `alarm_since` 2026-10-21, frozen 16/16, frozen after R09-20261016-01, first 2026-10-01, frozen 2026-10-16, `watching_since` 2026-10-17, `current_tally` 26.830256, `still_above_line` true, `needs_attention` false, `alarm_reviewed` false, `restart_cause` null, window 2026-10-01..2026-10-30 (30) | TC-028-02 |
| FEAT-028-AC-03 | R07 log: `baseline_restarted` 2026-10-13 device/D07/D07/D07B; `baseline_complete` 2026-10-28; other events restart fields null; oldest `checkins_started` 2026-10-01 on D07; detail `restart_cause` device, `current_epoch` D07→D07B | TC-028-03 |
| FEAT-028-AC-04 | R03 `set_aside` 2026-10-18 "quality flag poor; noise above limit"; `device_silent` 2026-10-12 "all residents on shared device D02 have no record"; R05 `quarantined` 2026-10-08 with the F0 detail | TC-028-04 |
| FEAT-028-AC-05 | R04 log: no event for R04-20261005-01 / R04-20261018-01; only the 9 types; `checkins_started` 2026-10-01 | TC-028-05 |
| FEAT-028-AC-06 | `from=2026-10-20&to=2026-10-10` and a 367-day span return 422 `INVALID_QUERY_PARAMETER` | TC-028-06 |
| FEAT-028-AC-07 | R09 features: 7 series in order; loudness median -22.405, spread 2.14977; R09-20261021-01 `z` -2.737502; baseline point `z` null and `in_baseline` true; 12 stored keys | TC-028-07 |
| FEAT-028-AC-08 | R08: `baseline_forming`, `needs_attention` true [`baseline_stalled`], `alarm_reviewed` null, 13·5·0·12, `n_usable` 13, `watching_since` null, `current_tally` 0 or null as stored; features all `z` null | TC-028-08 |
| FEAT-028-AC-09 | All three responses validate against their TRD 19 schemas and contain `meta` | TC-028-09 |
| FEAT-028-AC-10 | Same-date fixture returns `watching_started`, `baseline_restarted`, `set_aside` | TC-028-10 |

## Test Data Requirements

- DS-07 (`seed test_v0_1`, as-of 2026-10-30 15:00 America/Chicago); expected values from TRD 19 E-09..E-11 and TRD 11 §4.13.3.
- Residents R02, R03, R04, R05, R06, R07, R08, R09; duplicate arrivals R04-20261005-01 and R04-20261018-01; device change D07 → D07B on 2026-10-13.
- Synthetic fixture R11 (not enrolled); same-date fixture of `tests/integration/api/test_residents.py`.
- Environment: `SEED_*` passwords and `SEED_INGEST_API_KEY` from the environment file.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-028-FR-01 (API-075; FR-173) | FEAT-028 | TC-028-01, TC-028-12, TC-028-15 |
| FEAT-028-FR-02 (FR-161, FR-302, CUS-020, API-138) | FEAT-028 | TC-028-02, TC-028-08 |
| FEAT-028-FR-03 (FR-161, FR-172) | FEAT-028 | TC-028-02, TC-028-03 |
| FEAT-028-FR-04 (FR-162, FR-163, DME-010) | FEAT-028 | TC-028-02, TC-028-08 |
| FEAT-028-FR-05 (API-075, D-41) | FEAT-028 | TC-028-02, TC-028-08 |
| FEAT-028-FR-06 (API-075, API-138, D-42, D-114) | FEAT-028 | TC-028-02 |
| FEAT-028-FR-07 (API-076; OQ-12) | FEAT-028 | TC-028-02, TC-028-13 |
| FEAT-028-FR-08 (API-077, API-093, UX-141; FR-180, FR-183) | FEAT-028 | TC-028-06, TC-028-10, TC-028-14 |
| FEAT-028-FR-09 (API-077; TRD 23 §4.4.4; FR-181; D-113) | FEAT-028 | TC-028-03, TC-028-04, TC-028-11 |
| FEAT-028-FR-10 (API-077, DB-065, D-64, D-114) | FEAT-028 | TC-028-03 |
| FEAT-028-FR-11 (FR-182, D-67, AGT-053) | FEAT-028 | TC-028-05 |
| FEAT-028-FR-12 (API-078; TRD 11 §4.5.4) | FEAT-028 | TC-028-07, TC-028-14 |
| FEAT-028-FR-13 (API-078, BSC-037) | FEAT-028 | TC-028-07, TC-028-08 |
| FEAT-028-FR-14 (API-078, BSC-039) | FEAT-028 | TC-028-07 |
| FEAT-028-FR-15 (API-057, API-094, OAS-017) | FEAT-028 | TC-028-09 |
| AC-API-03 / TDV-066 | FEAT-028 | TC-028-02 |
| E2E-08 | FEAT-028 | TC-028-02, TC-028-11 |
| E2E-10 | FEAT-028 | TC-028-03 |
| E2E-11 | FEAT-028 | TC-028-08 |
| E2E-12 | FEAT-028 | TC-028-04 |
| TST-061, TST-064 | FEAT-028 | TC-028-09 |
