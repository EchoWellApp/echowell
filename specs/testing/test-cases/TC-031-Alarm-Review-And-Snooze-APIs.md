# Alarm review and snooze APIs (POST/GET /alerts/{id}/reviews, POST /alerts/{id}/snooze)

## Feature Description

The single review model of the Resident chart's "Review and notes" section: a clinician or admin records a review of a change alarm with `POST /api/v1/alerts/{id}/reviews` (TRD 19 E-14) — optional explanation codes from the configured checklist, a required outcome (`no_concern`, `known_cause`, `referred`, `data_problem`) and an optional note of at most 2,000 characters. The first review turns the alert from `open` to `acknowledged`; later reviews add rows. `GET /api/v1/alerts/{id}/reviews` (E-28) lists the reviews newest first for every role. `POST /api/v1/alerts/{id}/snooze` (E-29) sets a reminder ("Remind me in 24 hours") with the application clock. A `data_problem` review raises or links a `review_flagged_data_problem` data alert. Reviewing or snoozing never changes the tally, the alarm state or the resident's status, and there is no acknowledge route. Every review and snooze is audited without the note text. Source: FEAT-031; TRD 05 API-081, API-082, API-128, API-130..API-132; TRD 09 CUS-008, CUS-016, CUS-017, CUS-038..CUS-040; TRD 24 D-03, D-35, D-37.

## Preconditions

1. Local Docker Compose stack running; environment file from `.env.development.example` (`PIPELINE_PROFILE=test_v0_1`, `PIPELINE_AS_OF=2026-10-30T15:00:00-05:00`).
2. **DS-07 state:** `docker compose exec backend python -m backend.cli seed test_v0_1`. Open alerts: R09 (2026-10-21) and R10 (2026-10-24).
3. `API=http://localhost:8000/api/v1`; tokens `ADMIN`, `CLIN`, `RES` from `POST $API/auth/login` with the `SEED_*` passwords; `KEY` = the ingest API key from the environment file.
4. `R09_ALERT` and `R10_ALERT` = the `id` values from `GET $API/alerts?resident_code=R09` / `R10`.
5. `psql` access; reads use the app login; TC-031-07 performs one `UPDATE` (stated in the case). Local development stack for the `pytest` cases.
6. Every case that writes ends with (or is followed by) `docker compose exec backend python -m backend.cli seed test_v0_1 --reset`.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-031-01 | Clinician `known_cause` review: 201, one row, alert `acknowledged`, scores and CUSUM unchanged | High | Positive |
| TC-031-02 | Second review adds a row; list returns both newest first | High | Positive |
| TC-031-03 | Invalid review bodies return 422 and write nothing | High | Negative |
| TC-031-04 | `data_problem` review creates one data alert; a second links the same open row | High | Positive |
| TC-031-05 | Snooze without body = now + 24 h; `{"hours": 4}` = now + 4 h; status unchanged | High | Positive |
| TC-031-06 | `POST /alerts/{id}/acknowledge` does not exist (404 or 405) | High | Negative |
| TC-031-07 | Closed alert 409 `ALERT_CLOSED`; unknown id 404 `ALERT_NOT_FOUND`; researcher POST 403 | High | Negative |
| TC-031-08 | Audit rows `alert.reviewed` and `alert.snoozed`; note text never in audit details | High | Security |
| TC-031-09 | Full rebuild keeps alert id, reviews, `acknowledged` and `snoozed_until` | High | Analytics |
| TC-031-10 | Snooze `hours` outside 1..168 and extra properties return 422 | Medium | Negative |
| TC-031-11 | Review list for every role; API key 401; malformed uuid 422 | Medium | Security |
| TC-031-12 | Resident status and `alarm_reviewed` after review and snooze | Medium | Positive |
| TC-031-13 | Exact snooze times with a frozen clock (integration test) | Medium | Positive |

### TC-031-01 Clinician `known_cause` review: 201, one row, alert `acknowledged`, scores and CUSUM unchanged

| Step | Action | Expected Result |
|---|---|---|
| 1 | Snapshot: `SELECT md5(string_agg(s::text, '\|' ORDER BY s.id)) FROM scores s;` and `SELECT md5(string_agg(c::text, '\|' ORDER BY c.epoch_id)) FROM cusum_state c;` | Two hashes noted (H1, H2) |
| 2 | `curl -s -i -X POST $API/alerts/$R09_ALERT/reviews -H "Authorization: Bearer $CLIN" -H "Content-Type: application/json" -d '{"explanations": ["cold_cough_sore_throat"], "outcome": "known_cause", "note": "Resident has a cold; nurse notified."}'` | HTTP 201; body `id`, `alert_id` = R09_ALERT, `reviewer` `{"id": <clinician id>, "display_name": "Clinician"}`, `explanations` ["cold_cough_sore_throat"], `outcome` "known_cause", `note` as sent, `created_at` UTC with Z |
| 3 | `SELECT count(*) FROM alert_reviews WHERE alert_id='$R09_ALERT';` | 1 |
| 4 | `SELECT status, acknowledged_by, acknowledged_at FROM alerts WHERE id='$R09_ALERT';` | `acknowledged`; `acknowledged_by` = clinician user id; `acknowledged_at` not null |
| 5 | Repeat the two hashes of step 1 | Equal to H1 and H2 (byte-identical) |
| 6 | `GET $API/alerts?resident_code=R09` | `current_tally` 26.830256 (±1e-6); `cusum_value` 5.431965 |

### TC-031-02 Second review adds a row; list returns both newest first

| Step | Action | Expected Result |
|---|---|---|
| 1 | After TC-031-01, POST a second review on R09_ALERT as admin: `{"explanations": [], "outcome": "no_concern"}` | HTTP 201; `reviewer.display_name` "Admin" |
| 2 | `SELECT count(*) FROM alert_reviews WHERE alert_id='$R09_ALERT';` and `SELECT status FROM alerts WHERE id='$R09_ALERT';` | 2 rows; status still `acknowledged` |
| 3 | `GET $API/alerts/$R09_ALERT/reviews` as researcher | HTTP 200; `total` 2; `items[0].outcome` "no_concern" (newest), `items[1].outcome` "known_cause"; `items[0].created_at` > `items[1].created_at`; `meta` present |

### TC-031-03 Invalid review bodies return 422 and write nothing

| Step | Action | Expected Result |
|---|---|---|
| 1 | Note `SELECT count(*) FROM alert_reviews;` and R10's alert `status` | Count noted; status `open` |
| 2 | POST to R10_ALERT as clinician `{"explanations": []}` (no outcome) | HTTP 422 `VALIDATION_ERROR` |
| 3 | POST `{"outcome": "fine"}` | HTTP 422 `VALIDATION_ERROR` |
| 4 | POST `{"explanations": ["headache"], "outcome": "no_concern"}` | HTTP 422 `VALIDATION_ERROR` |
| 5 | POST `{"outcome": "no_concern", "note": "<2001 × the letter a>"}` | HTTP 422 `VALIDATION_ERROR` |
| 6 | POST `{"explanations": ["dental_dentures", "dental_dentures"], "outcome": "no_concern"}` | HTTP 422 `VALIDATION_ERROR` |
| 7 | POST with 6 explanation codes (the 5 configured codes plus one repeated) | HTTP 422 `VALIDATION_ERROR` |
| 8 | POST `{"outcome": "no_concern", "extra": 1}` | HTTP 422 `VALIDATION_ERROR` |
| 9 | Re-read the count and R10's status | Count unchanged; status still `open`; no new `alert.reviewed` audit row |

### TC-031-04 `data_problem` review creates one data alert; a second links the same open row

| Step | Action | Expected Result |
|---|---|---|
| 1 | POST to R10_ALERT as clinician `{"outcome": "data_problem"}`; note the review `id` (REV1) | HTTP 201 |
| 2 | `SELECT id, kind, status, alert_review_id, title, detail, pipeline_run_id, first_detected_at, last_detected_at FROM data_alerts d JOIN residents r ON r.id=d.resident_id WHERE r.resident_code='R10' AND kind='review_flagged_data_problem';` | 1 row: `status` open; `alert_review_id` = REV1; `title` "R10 · review flagged a data problem"; `detail` "a review flagged a data problem (<Mon D>, Clinician)." with today's facility-local date (e.g. "Nov 15"); `pipeline_run_id` NULL; `first_detected_at` = `last_detected_at` = review time |
| 3 | POST a second `data_problem` review on R10_ALERT as admin; note its id (REV2) | HTTP 201 |
| 4 | Repeat the query of step 2 | Still exactly 1 open row of that kind for R10, same `id`; `alert_review_id` = REV2; `detail` ends "…, Admin)."; `last_detected_at` later than `first_detected_at`; `title` unchanged |
| 5 | `GET $API/data-alerts?kind=review_flagged_data_problem` | 1 item for R10 |
| 6 | `GET $API/alerts?status=open` | R10 no longer listed as open (now `acknowledged`); data alert not counted in alerts |

### TC-031-05 Snooze without body = now + 24 h; `{"hours": 4}` = now + 4 h; status unchanged

| Step | Action | Expected Result |
|---|---|---|
| 1 | Note UTC time T0; `curl -s -X POST $API/alerts/$R10_ALERT/snooze -H "Authorization: Bearer $CLIN"`; note UTC time T1 | HTTP 200; body is the `Alert` DTO; `status` "open"; `snoozed_by` = clinician user id |
| 2 | Compare `snoozed_until` with T0 and T1 | T0 + 24 h ≤ `snoozed_until` ≤ T1 + 24 h (application clock, not the `PIPELINE_AS_OF` date) |
| 3 | `SELECT snoozed_until, snoozed_by, status FROM alerts WHERE id='$R10_ALERT';` | Same `snoozed_until` and `snoozed_by`; `status` open |
| 4 | Repeat with body `{"hours": 4}` (`-H "Content-Type: application/json"`) | HTTP 200; `snoozed_until` within [T0' + 4 h, T1' + 4 h] |
| 5 | `GET $API/residents` | R10 `status` "alarm_on"; summary unchanged |

### TC-031-06 `POST /alerts/{id}/acknowledge` does not exist (404 or 405)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s -i -X POST $API/alerts/$R09_ALERT/acknowledge -H "Authorization: Bearer $CLIN"` | HTTP 404 (`NOT_FOUND`) or 405 (`METHOD_NOT_ALLOWED`) |
| 2 | `curl -s $API/openapi.json \| jq '.paths \| keys[]' \| grep acknowledge` | No match |
| 3 | `SELECT status FROM alerts WHERE id='$R09_ALERT';` | Unchanged (`open` on DS-07) |

### TC-031-07 Closed alert 409 `ALERT_CLOSED`; unknown id 404 `ALERT_NOT_FOUND`; researcher POST 403

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST $API/alerts/00000000-0000-4000-8000-000000000000/reviews` as clinician with `{"outcome": "no_concern"}` | HTTP 404; `type` "urn:echowell:error:ALERT_NOT_FOUND"; `title` "Alert not found" |
| 2 | Same id on `/snooze` | HTTP 404 `ALERT_NOT_FOUND` |
| 3 | `POST $API/alerts/$R09_ALERT/reviews` as researcher | HTTP 403 `FORBIDDEN`; one `access.denied` audit row; no review row |
| 4 | `POST $API/alerts/$R09_ALERT/snooze` as researcher | HTTP 403 `FORBIDDEN` |
| 5 | Write step (test database only): `UPDATE alerts SET status='closed', closed_reason='admin', closed_at=now() WHERE id='$R10_ALERT';` | 1 row updated |
| 6 | Review and snooze R10_ALERT as clinician | HTTP 409 `ALERT_CLOSED` (`title` "Alert already closed") for both |
| 7 | `SELECT count(*) FROM alert_reviews WHERE alert_id='$R10_ALERT'; SELECT snoozed_until FROM alerts WHERE id='$R10_ALERT';` | 0 and NULL (nothing written) |
| 8 | Restore with `seed test_v0_1 --reset` | DS-07 state again |

### TC-031-08 Audit rows `alert.reviewed` and `alert.snoozed`; note text never in audit details

| Step | Action | Expected Result |
|---|---|---|
| 1 | After TC-031-01: `SELECT actor_type, actor_id, entity_type, entity_id, details, request_id FROM audit_logs WHERE action='alert.reviewed';` | 1 row per saved review: `actor_type` user, `entity_type` "alert", `entity_id` = R09_ALERT, `details` = `{resident_code: "R09", review_id, outcome: "known_cause", explanation_count: 1, previous_status: "open"}`, `request_id` set |
| 2 | `SELECT count(*) FROM audit_logs WHERE details::text LIKE '%nurse notified%';` | 0 (note text never stored in audit) |
| 3 | After TC-031-05: `SELECT details FROM audit_logs WHERE action='alert.snoozed' ORDER BY id;` | One row per snooze; details `{resident_code: "R10", hours: 24, snoozed_until}` then `{…, hours: 4, …}` |
| 4 | `docker compose logs backend --since 10m \| grep -c "nurse notified"` | 0 (note text never logged) |

### TC-031-09 Full rebuild keeps alert id, reviews, `acknowledged` and `snoozed_until`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Review R09_ALERT (`known_cause`) and snooze it as clinician; note `snoozed_until` and the review ids | 201 and 200 |
| 2 | `curl -s -X POST $API/pipeline/run -H "Authorization: Bearer $ADMIN" -H "Content-Type: application/json" -d '{"scope": "all"}'` | HTTP 202 with `pipeline_run_id` |
| 3 | Poll `GET $API/pipeline/runs/<pipeline_run_id>` as admin | `status` "succeeded" |
| 4 | `GET $API/alerts?resident_code=R09` | Same `id` = R09_ALERT; `status` "acknowledged"; `review_count` 1; `snoozed_until` unchanged |
| 5 | `SELECT id FROM alert_reviews WHERE alert_id='$R09_ALERT';` | Same review ids as step 1 |

### TC-031-10 Snooze `hours` outside 1..168 and extra properties return 422

| Step | Action | Expected Result |
|---|---|---|
| 1 | Snooze R10_ALERT with `{"hours": 0}`, `{"hours": 169}`, `{"hours": null}`, `{"hours": 4, "until": "x"}` (one request each) | HTTP 422 `VALIDATION_ERROR` each |
| 2 | `SELECT snoozed_until FROM alerts WHERE id='$R10_ALERT';` | NULL (unchanged on DS-07) |

### TC-031-11 Review list for every role; API key 401; malformed uuid 422

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/alerts/$R09_ALERT/reviews` with each of `$ADMIN`, `$CLIN`, `$RES` | 200 each; `items` [] and `total` 0 on DS-07 |
| 2 | Same with `X-API-Key: $KEY` | 401 `NOT_AUTHENTICATED` |
| 3 | `GET $API/alerts/00000000-0000-4000-8000-000000000000/reviews` | 404 `ALERT_NOT_FOUND` |
| 4 | `POST $API/alerts/not-a-uuid/reviews` with a valid body | 422 `VALIDATION_ERROR` |

### TC-031-12 Resident status and `alarm_reviewed` after review and snooze

| Step | Action | Expected Result |
|---|---|---|
| 1 | Review R09_ALERT and snooze it | 201 and 200 |
| 2 | `GET $API/residents/R09` | `status` "alarm_on"; `alarm_reviewed` true; `current_tally` 26.830256; `open_alert_id` = R09_ALERT |
| 3 | `GET $API/residents` | Order and `summary` (2 / 2 / 0 / 6) unchanged |

### TC-031-13 Exact snooze times with a frozen clock (integration test)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/integration/api/test_alerts.py::test_snooze -q` | Passes: with the clock frozen at T, no body gives `snoozed_until` = T + 24 h exactly and `{"hours": 4}` gives T + 4 h; after advancing the clock 24 h + 1 s, `snoozed_until` < now; status unchanged |
| 2 | `pytest tests/integration/api/test_alerts.py -q` | All tests pass |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `POST /alerts/{id}/reviews` | 201 `AlertReview`; 404 `ALERT_NOT_FOUND`; 409 `ALERT_CLOSED`; 422 `VALIDATION_ERROR`; 403 for researcher |
| 2 | `GET /alerts/{id}/reviews` | 200 `AlertReviewList` newest first with `meta`; 404 for unknown id |
| 3 | `POST /alerts/{id}/snooze` | 200 `Alert` DTO with `snoozed_until`, `snoozed_by`; 404 / 409 / 422 as above |
| 4 | Body rules | `explanations` 0..5 unique configured codes; `outcome` required enum; `note` ≤ 2000; no other properties; `hours` 1..168 |
| 5 | No acknowledge route | 404 or 405 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `alert_reviews` | One immutable row per saved review (`reviewer_user_id` from the token) |
| 2 | `alerts` after first review | `status` acknowledged; `acknowledged_by`, `acknowledged_at` set (`alerts_ack_ck` holds) |
| 3 | `alerts` after snooze | `snoozed_until`, `snoozed_by` both set (`alerts_snooze_ck` holds) |
| 4 | `data_alerts` after `data_problem` | One open `review_flagged_data_problem` per resident; `pipeline_run_id` NULL (`data_alerts_run_ck`) |
| 5 | `scores`, `cusum_state` | Hashes unchanged by any review or snooze |
| 6 | `audit_logs` | `alert.reviewed` / `alert.snoozed` per action in the same transaction; no note text |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Missing/unknown outcome, unknown or duplicate code, > 5 codes, note > 2000, extra property (TC-031-03) | 422, nothing written |
| 2 | Closed alert (TC-031-07) | 409 `ALERT_CLOSED` |
| 3 | Unknown id | 404 `ALERT_NOT_FOUND` |
| 4 | Researcher POST | 403 `FORBIDDEN` |
| 5 | API key | 401 |
| 6 | `hours` 0 / 169 / null | 422 |
| 7 | `POST /alerts/{id}/acknowledge` | 404 or 405 |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-031-AC-01 | `known_cause` review: 201, exactly one row, alert `acknowledged` with `acknowledged_by` = clinician; `scores` and `cusum_state` byte-identical; R09 `current_tally` 26.830256 | TC-031-01 |
| FEAT-031-AC-02 | Second review creates a second row; list returns both newest first | TC-031-02 |
| FEAT-031-AC-03 | No outcome, outcome `fine`, explanation `headache`, 2001-character note each return 422 and create no row | TC-031-03 |
| FEAT-031-AC-04 | `data_problem` creates one `review_flagged_data_problem` row (resident, review id, title "<R> · review flagged a data problem", open); second leaves one open row linked to the newer review | TC-031-04 |
| FEAT-031-AC-05 | Snooze without body = T + 24 h, `snoozed_by` = caller; `{"hours": 4}` = T + 4 h; status unchanged | TC-031-05, TC-031-13 |
| FEAT-031-AC-06 | `POST /api/v1/alerts/{id}/acknowledge` returns 404 or 405 | TC-031-06 |
| FEAT-031-AC-07 | Closed alert 409 `ALERT_CLOSED`; unknown id 404 `ALERT_NOT_FOUND`; researcher POST 403 | TC-031-07 |
| FEAT-031-AC-08 | One `alert.reviewed` per review and one `alert.snoozed` per snooze; no audit `details` contains the note text | TC-031-08 |
| FEAT-031-AC-09 | After review and snooze, full rebuild keeps alert id, reviews, `acknowledged`, `snoozed_until` | TC-031-09 |

## Test Data Requirements

- DS-07 (`seed test_v0_1`): open alerts R09 and R10; four open rule-based data alerts.
- `config_parameters` `review_explanations` (5 codes) and `alert_snooze_hours` (24) of test_v0_1.
- Synthetic note text "Resident has a cold; nurse notified." (TRD 19 E-14 example; no real person).
- Unknown alert id `00000000-0000-4000-8000-000000000000`.
- Environment: `SEED_ADMIN_PASSWORD`, `SEED_CLINICIAN_PASSWORD`, `SEED_RESEARCHER_PASSWORD`, `SEED_INGEST_API_KEY` from the environment file.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-031-FR-01 (API-081, FR-275, SEC-045) | FEAT-031 | TC-031-07 |
| FEAT-031-FR-02 (API-081, API-082, CUS-038, DME-021; FR-271) | FEAT-031 | TC-031-03 |
| FEAT-031-FR-03 (CUS-016, CUS-017, DME-007; FR-106, FR-270, FR-272) | FEAT-031 | TC-031-01, TC-031-02 |
| FEAT-031-FR-04 (CUS-008, DME-007; FR-107; D-03) | FEAT-031 | TC-031-01, TC-031-05, TC-031-12 |
| FEAT-031-FR-05 (API-130, CUS-040, DME-021; FR-273; D-114) | FEAT-031 | TC-031-04 |
| FEAT-031-FR-06 (API-131; FR-272) | FEAT-031 | TC-031-02, TC-031-11 |
| FEAT-031-FR-07 (API-132, CUS-039, DME-022, D-37; FR-274) | FEAT-031 | TC-031-05, TC-031-10, TC-031-13 |
| FEAT-031-FR-08 (API-082) | FEAT-031 | TC-031-07, TC-031-11 |
| FEAT-031-FR-09 (API-082, D-35) | FEAT-031 | TC-031-06 |
| FEAT-031-FR-10 (FR-279; SEC-100, SEC-101, SEC-104) | FEAT-031 | TC-031-08 |
| FEAT-031-FR-11 (FR-276, CUS-042, OQ-26) | FEAT-031 | TC-031-02 (reviews accepted without any deadline field) |
| FEAT-031-FR-12 (API-128, TST-067) | FEAT-031 | TC-031-09 |
| TST-056 / AC-API-15 / AC-CUS-06 | FEAT-031 | TC-031-01 |
| TST-057 | FEAT-031 | TC-031-02 |
| TST-058 | FEAT-031 | TC-031-03 |
| TST-059 | FEAT-031 | TC-031-04 |
| TST-065 / AC-CUS-10 | FEAT-031 | TC-031-05, TC-031-13 |
| TST-066 | FEAT-031 | TC-031-06 |
| TST-067 / AC-TST-12 | FEAT-031 | TC-031-09 |
| TST-053 | FEAT-031 | TC-031-08 |
