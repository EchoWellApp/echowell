# Alerts list and UI configuration APIs (GET /api/v1/alerts, GET /api/v1/config/ui)

## Feature Description

`GET /api/v1/alerts` (TRD 19 E-13) lists change alarms ordered by `triggered_at` ascending with device, epoch, current tally, open days, review state, snooze state, `leaning_most` and `closed_reason`; `?status=open` gives the red badge count on the "Resident list" navigation link and `?resident_code=<R>` gives a resident's alarm for the chart. `GET /api/v1/config/ui` (E-32) returns the operational settings the review form needs — `alert_snooze_hours` and the `review_explanations` checklist — read from `config_parameters` of the active profile on every request. Alerts surface only in the dashboard; there is no e-mail, SMS or push channel. Both endpoints are read-only and open to every user role. Source: FEAT-030; TRD 05 API-080, API-137; TRD 09 CUS-022, CUS-025, CUS-041; TRD 24 D-05, D-64, D-92.

## Preconditions

1. Local Docker Compose stack running; environment file from `.env.development.example` (`PIPELINE_PROFILE=test_v0_1`).
2. **DS-07 state:** `docker compose exec backend python -m backend.cli seed test_v0_1` (as-of `2026-10-30T20:00:00Z`; open alarms R09 and R10).
3. `API=http://localhost:8000/api/v1`; tokens `ADMIN`, `CLIN`, `RES` from `POST $API/auth/login` with the `SEED_*` passwords; `KEY` = the ingest API key from the environment file.
4. `psql` read access; local development stack for the `pytest` cases.
5. Cases that write (TC-030-03, TC-030-07, TC-030-09) end with `docker compose exec backend python -m backend.cli seed test_v0_1 --reset`.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-030-01 | Invalid `status` returns 422 `INVALID_QUERY_PARAMETER` | High | Negative |
| TC-030-02 | Ordering by `triggered_at` (R09 Oct 21 before R10 Oct 24) and `?status=open` total counts open alerts only | High | Positive |
| TC-030-03 | After a review, item shows `reviewed` true, `review_count` 1, `last_reviewed_at` = review time | High | Positive |
| TC-030-04 | DS-07 open alerts: exact facts for R09 and R10 | High | Positive |
| TC-030-05 | `GET /config/ui` under test_v0_1: 24 h and the 5 explanation codes and labels in order | High | Positive |
| TC-030-06 | `leaning_most` present on every item (array ≤ 3); both responses validate with `meta` | High | API |
| TC-030-07 | Inspection: no e-mail, SMS or push library or code path in `backend/` | High | Documentation |
| TC-030-08 | `resident_code` filter: R09 alert only; unknown code gives empty list | Medium | Positive |
| TC-030-09 | Changed `alert_snooze_hours` visible on the next request without restart | Medium | Positive |
| TC-030-10 | Role access: every user role 200 on both endpoints; API key and anonymous 401 | Medium | Security |
| TC-030-11 | Data alerts are never counted in `GET /alerts` | Medium | Positive |
| TC-030-12 | Invalid paging returns 422 | Low | Negative |

### TC-030-01 Invalid `status` returns 422 `INVALID_QUERY_PARAMETER`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s -i "$API/alerts?status=bogus" -H "Authorization: Bearer $CLIN"` | HTTP 422; `type` "urn:echowell:error:INVALID_QUERY_PARAMETER"; `errors[]` names `status` |
| 2 | `GET $API/alerts?status=closed` | HTTP 200; `items` [] and `total` 0 for DS-07 (no closed alert) |

### TC-030-02 Ordering by `triggered_at` (R09 Oct 21 before R10 Oct 24) and `?status=open` total counts open alerts only

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/alerts` | `items[0].resident_code` "R09" (`triggered_at` "2026-10-21T19:07:50Z"), `items[1].resident_code` "R10" (`triggered_at` "2026-10-24T19:25:37Z"); `total` 2 |
| 2 | `GET $API/alerts?status=open` | `total` 2 |
| 3 | Fixture variant: `pytest tests/integration/api/test_alerts.py::test_alert_list -q` | Passes (fixture alerts with `triggered_at` 2026-10-24 and 2026-10-21: the 2026-10-21 alert comes first; `?status=open` `total` = number of `open` alerts only) |
| 4 | After TC-030-03 step 1 (R09 reviewed → `acknowledged`): `GET $API/alerts?status=open` | `total` 1 (R10 only); `GET $API/alerts?status=acknowledged` returns R09 |

### TC-030-03 After a review, item shows `reviewed` true, `review_count` 1, `last_reviewed_at` = review time

| Step | Action | Expected Result |
|---|---|---|
| 1 | Take R09's alert `id` from TC-030-02; `POST $API/alerts/<id>/reviews` as clinician with `{"explanations": [], "outcome": "no_concern"}` | HTTP 201; note `created_at` |
| 2 | `GET $API/alerts?resident_code=R09` | Item: `status` "acknowledged"; `reviewed` true; `review_count` 1; `last_reviewed_at` equal to the review `created_at` |
| 3 | `SELECT count(*), max(created_at) FROM alert_reviews WHERE alert_id='<id>';` | 1 and the same timestamp as `last_reviewed_at` |
| 4 | Restore with `seed test_v0_1 --reset` | DS-07 state again |

### TC-030-04 DS-07 open alerts: exact facts for R09 and R10

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/alerts?status=open` | Exactly 2 items, R09 then R10 |
| 2 | R09 item | `device_code` "D09"; `epoch_number` 1; `session_id` "R09-20261021-01"; `local_date` "2026-10-21"; `cusum_value` 5.431965; `current_tally` 26.830256 (±1e-6); `open_days` 9; `status` "open"; `reviewed` false; `review_count` 0; `last_reviewed_at` null; `snoozed_until` null; `snoozed_by` null; `closed_reason` null |
| 3 | R10 item | `device_code` "D10"; `session_id` "R10-20261024-01"; `local_date` "2026-10-24"; `cusum_value` 5.97205; `current_tally` 13.418183 (±1e-6); `open_days` 6; `reviewed` false |
| 4 | Response values | Raw facts only: no formatted text such as "Alarm started", "9 days" or a 1-decimal score in the API |

### TC-030-05 `GET /config/ui` under test_v0_1: 24 h and the 5 explanation codes and labels in order

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s $API/config/ui -H "Authorization: Bearer $CLIN"` | HTTP 200 |
| 2 | `alert_snooze_hours` | 24 |
| 3 | `review_explanations` | Exactly, in order: `{"code": "cold_cough_sore_throat", "label": "Cold, cough or sore throat"}`, `{"code": "dental_dentures", "label": "Dental problem or dentures out"}`, `{"code": "medication_change", "label": "New or changed medication"}`, `{"code": "poor_sleep_unusual_day", "label": "Poor sleep or unusual day"}`, `{"code": "room_device_moved", "label": "Room or device moved"}` |
| 4 | `meta.pipeline_profile` | "test_v0_1" |

### TC-030-06 `leaning_most` present on every item (array ≤ 3); both responses validate with `meta`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/alerts` | Every item has the key `leaning_most` with an array of 0–3 `ScoredFeatureKey` values |
| 2 | Validate against `AlertList` from `GET $API/openapi.json` | Valid; `meta` with seven fields; `total`, `limit` 50, `offset` 0 |
| 3 | Validate `GET $API/config/ui` against `UiConfig` | Valid; `meta` present |

### TC-030-07 Inspection: no e-mail, SMS or push library or code path in `backend/`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -inE "smtp\|sendgrid\|twilio\|mailgun\|firebase\|pywebpush\|apns\|onesignal" backend/requirements.txt` | No match |
| 2 | `grep -rniE "import smtplib\|from email\.mime\|twilio\|sendgrid\|pywebpush\|firebase_admin" backend --include=*.py` | No match |
| 3 | `pytest tests/unit/backend/test_no_outbound_alerts.py -q` | Passes |

### TC-030-08 `resident_code` filter: R09 alert only; unknown code gives empty list

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/alerts?resident_code=R09` | `total` 1; item R09 |
| 2 | `GET $API/alerts?resident_code=R01` | `items` []; `total` 0 |
| 3 | `GET $API/alerts?resident_code=R11` | HTTP 200; `items` []; `total` 0 (unknown code is not an error) |

### TC-030-09 Changed `alert_snooze_hours` visible on the next request without restart

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker compose exec backend python -m backend.cli set-config --profile test_v0_1 --key alert_snooze_hours --value 12 --reason "QA config check"` | "test_v0_1.alert_snooze_hours updated."; exit 0 |
| 2 | `GET $API/config/ui` (no backend restart) | `alert_snooze_hours` 12 |
| 3 | `SELECT details FROM audit_logs WHERE action='config.changed' ORDER BY id DESC LIMIT 1;` | Details hold old 24, new 12 and the reason |
| 4 | Set it back: same command with `--value 24` | `GET $API/config/ui` returns 24 |

### TC-030-10 Role access: every user role 200 on both endpoints; API key and anonymous 401

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /alerts` and `GET /config/ui` with each of `$ADMIN`, `$CLIN`, `$RES` | 200 for all six |
| 2 | Same two paths with `X-API-Key: $KEY` | 401 `NOT_AUTHENTICATED` |
| 3 | Same two paths without credentials | 401 `NOT_AUTHENTICATED` |
| 4 | `snoozed_by` field in any item | A user uuid or null only; no e-mail or name |

### TC-030-11 Data alerts are never counted in `GET /alerts`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT count(*) FROM data_alerts WHERE status='open';` | 4 (DS-07) |
| 2 | `GET $API/alerts?status=open` | `total` 2 (only change alarms R09, R10; no data alert) |

### TC-030-12 Invalid paging returns 422

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/alerts?limit=0`, `?limit=501`, `?offset=-1` | 422 `INVALID_QUERY_PARAMETER` each |
| 2 | `GET $API/alerts?limit=1` | `items` [R09]; `total` 2 |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/alerts` | 200 `AlertList`; `triggered_at` ascending; each item has `id`, `resident_code`, `device_code`, `epoch_number`, `session_id`, `triggered_at`, `local_date`, `cusum_value`, `current_tally`, `open_days`, `status`, `reviewed`, `review_count`, `last_reviewed_at`, `snoozed_until`, `snoozed_by`, `leaning_most`, `closed_reason` |
| 2 | `reviewed` rule | true iff `status` is `acknowledged` |
| 3 | `open_days` rule | as-of local date (2026-10-30) − alert `local_date` in days |
| 4 | `GET /api/v1/config/ui` | 200 `UiConfig` `{meta, alert_snooze_hours, review_explanations}` |
| 5 | Errors | 422 `INVALID_QUERY_PARAMETER`; 401 for API key / anonymous; 503 with database down |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT r.resident_code, a.local_date, a.cusum_value, a.status FROM alerts a JOIN residents r ON r.id=a.resident_id ORDER BY a.triggered_at;` | R09 2026-10-21 5.431965 open; R10 2026-10-24 5.97205 open — matches the list |
| 2 | `SELECT cs.current_tally FROM cusum_state cs JOIN alerts a ON a.epoch_id=cs.epoch_id JOIN residents r ON r.id=a.resident_id WHERE r.resident_code='R10';` | 13.418183 (±1e-6) = `current_tally` |
| 3 | `SELECT key, value FROM config_parameters WHERE profile='test_v0_1' AND key IN ('alert_snooze_hours','review_explanations');` | 24 and the five `{code, label}` items = `UiConfig` |
| 4 | No write by the GET endpoints | Row counts unchanged |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | `status=bogus` | 422 `INVALID_QUERY_PARAMETER` |
| 2 | Bad paging | 422 `INVALID_QUERY_PARAMETER` |
| 3 | Unknown `resident_code` R11 | 200 with empty list (not an error) |
| 4 | API key / anonymous on either endpoint | 401 |
| 5 | `docker compose stop db`, then `GET /alerts` | 503 `SERVICE_UNAVAILABLE`, `Retry-After: 30`; `docker compose start db` afterwards |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-030-AC-01 | `?status=bogus` returns 422 `INVALID_QUERY_PARAMETER` | TC-030-01 |
| FEAT-030-AC-02 | 2026-10-21 alert listed before 2026-10-24 alert; `?status=open` `total` = number of `open` alerts only | TC-030-02 |
| FEAT-030-AC-03 | After one review row and status `acknowledged`: `reviewed` true, `review_count` 1, `last_reviewed_at` = review `created_at` | TC-030-03 |
| FEAT-030-AC-04 | DS-07 `?status=open` returns exactly R09 (D09, 2026-10-21, 9 days, 26.830256) and R10 (D10, 2026-10-24, 6 days, 13.418183), in that order, both `reviewed` false | TC-030-04 |
| FEAT-030-AC-05 | test_v0_1 `config/ui`: `alert_snooze_hours` 24 and the five codes in order with their E-32 labels | TC-030-05 |
| FEAT-030-AC-06 | Every item has `leaning_most` array of length ≤ 3; both responses validate against `AlertList` / `UiConfig` with `meta` | TC-030-06 |
| FEAT-030-AC-07 | No e-mail, SMS or push client library and no code sending alerts outside the API | TC-030-07 |

## Test Data Requirements

- DS-07 (`seed test_v0_1`): open alerts R09 (Oct 21) and R10 (Oct 24); four open data alerts; values from TRD 19 E-13 and E-32.
- `config_parameters` rows `alert_snooze_hours` (24) and `review_explanations` (5 codes) of profile test_v0_1.
- Integration fixture of `tests/integration/api/test_alerts.py`.
- Environment: `SEED_*` passwords, `SEED_INGEST_API_KEY` from the environment file.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-030-FR-01 (API-080; FR-108) | FEAT-030 | TC-030-01, TC-030-08, TC-030-12 |
| FEAT-030-FR-02 (API-080, CUS-025, CUS-022) | FEAT-030 | TC-030-02, TC-030-11 |
| FEAT-030-FR-03 (API-080, CUS-025; FR-262) | FEAT-030 | TC-030-03, TC-030-04 |
| FEAT-030-FR-04 (CUS-041; D-92) | FEAT-030 | TC-030-06 |
| FEAT-030-FR-05 (FR-109, CUS-022, D-05) | FEAT-030 | TC-030-07 |
| FEAT-030-FR-06 (API-137; ENV-020) | FEAT-030 | TC-030-05, TC-030-09 |
| FEAT-030-FR-07 (CUS-026, OAS-011, D-113) | FEAT-030 | TC-030-04 |
| FEAT-030-FR-08 (FR-262, FR-274, D-110) | FEAT-030 | TC-030-03, TC-030-04 |
| AC-API-14 (alerts half) / TDV-067 / OAS-027 | FEAT-030 | TC-030-04 |
| AC-CUS-08 | FEAT-030 | TC-030-07 |
| TST-061, TST-064 | FEAT-030 | TC-030-06 |
| TRD 13 Table 4.13-A (GET /alerts, GET /config/ui) | FEAT-030 | TC-030-10 |
