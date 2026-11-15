# Alarm review panel in the resident chart (review form, reminder, previous reviews)

## Feature Description

Clinicians and admins review a change alarm in the "Review and notes" section of a Changed resident's chart (`/residents/[residentCode]/review`), above the staff notes. The panel "Review alert: changed since <Mon D>" holds the checklist "Anything that could explain it?" (from `GET /api/v1/config/ui` `review_explanations`, provisional, OQ-25), the required choice "What did you find?", an optional "Note" (at most 2000 characters), the buttons "Save review" and "Remind me in <h> hours", the "Previous reviews" list, the open-questions note (OQ-05, OQ-26) and, for researchers, the read-only text "Only clinicians and admins can review alarms.". A saved review marks the alarm "Reviewed" but never changes the alarm state, change score or pill (OQ-05). The v0.1 Alert review page (`/alerts`) and its change-alarm queue are retired and verified as absent (TRD 11 §4.17; TRD 04 FE-079, FE-086, FE-134..FE-138, FE-205, FE-209; TRD 19 E-13, E-14, E-28, E-29, E-32).

## Preconditions

- Local Docker Compose demo profile running, freshly seeded with `test_v0_1` and the DS-07 pipeline run (as-of Oct 30, 2026, 3:00 PM CT): open alarms R09 (Oct 21) and R10 (Oct 24), no reviews, no reminders; `alert_snooze_hours` 24.
- Seeded users `clinician@example.com`, `researcher@example.com`, `admin@example.com` with the `SEED_*` passwords.
- Cases that save data (TC-069-04 to TC-069-08) change the database; re-seed between runs with `docker compose exec -T backend python -m backend.cli seed test_v0_1 --reset` followed by the DS-07 pipeline run.
- Browser developer tools (Network panel, Accessibility tree); `psql` read access.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-069-01 | R09 review panel renders the §4.17.5 values | High | Positive |
| TC-069-02 | Non-Changed resident (R01) has no review panel; `/alerts` retired | High | Negative |
| TC-069-03 | "Save review" without a choice: "Choose what you found.", focus, no request | High | Negative |
| TC-069-04 | Save R09 "Checked on resident, no concern": messages, badges, list text, alarm unchanged | High | Positive |
| TC-069-05 | Request body: explanation codes, outcome, whitespace note omitted | High | API |
| TC-069-06 | Outcome "Looks like a data problem: send to study team" creates a study-team data problem | High | Positive |
| TC-069-07 | "Remind me in 24 hours" on R10: reminder line, no review, alarm unchanged | High | Positive |
| TC-069-08 | Previous reviews: two reviews newest first with explanations and note | Medium | Positive |
| TC-069-09 | Researcher: form replaced, previous reviews visible, direct POST 403 | High | Security |
| TC-069-10 | Note field counter and 2000-character limit; field errors on 422 | Medium | Negative |
| TC-069-11 | 409 `ALERT_CLOSED` and network failure keep entered values | Medium | Negative |
| TC-069-12 | Config request fails: error inside the panel, previous reviews still shown | Medium | Negative |
| TC-069-13 | Keyboard operation and 44px label rows | Medium | Accessibility |
| TC-069-14 | Reminder line disappears after `snoozed_until` passes | Low | Positive |

### TC-069-01 R09 panel

| Step | Action | Expected Result |
|---|---|---|
| 1 | Sign in as clinician; open `/residents/R09/review` | Title "R09 · Review and notes – EchoWell"; first panel `<h2>` "Review alert: changed since Oct 21" |
| 2 | Read the first fieldset | Legend "Anything that could explain it?" (weight 700, 1px `--rule` border, radius 6px, padding 12px 14px); checkboxes in order "Cold, cough or sore throat", "Dental problem or dentures out", "New or changed medication", "Poor sleep or unusual day", "Room or device moved"; hint "Provisional list — to be confirmed with the clinical team (OQ-25)." (13px, `--muted`) |
| 3 | Read the second fieldset | Legend "What did you find?"; radios "Checked on resident, no concern", "Explained by a known cause", "Referred to nurse or provider", "Looks like a data problem: send to study team"; none selected |
| 4 | Read the note field | Label "Note", 3 rows, placeholder "What you saw or did", counter "0 / 2000" |
| 5 | Read the buttons | Primary "Save review"; secondary "Remind me in 24 hours" |
| 6 | Read under the buttons | `<h3>` "Previous reviews" followed by "Not reviewed yet." |
| 7 | Read the end of the panel | "Open questions (OQ-05, OQ-26): Does a saved review reset the change score or turn the alarm off? Who may review? How soon must an alarm be reviewed? Pipeline v0.1 keeps alarms on." (13px, `--muted`) |
| 8 | Open `/residents/R10/review` | Heading "Review alert: changed since Oct 24"; same controls and "Not reviewed yet." |
| 9 | Check the panel below | "Staff notes" panel follows the review panel |

### TC-069-02 No panel for non-Changed residents

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R01/review` | No "Review alert…" panel; "Staff notes" is the only panel |
| 2 | Repeat for R03, R07, R08 | No review panel |
| 3 | Open `/alerts` | "This page was not found." with "← Resident list" (no alarm queue page) |

### TC-069-03 Missing choice

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `/residents/R09/review` clear the Network panel; check "Cold, cough or sore throat" only and click "Save review" | Message "Choose what you found." appears, linked to the "What did you find?" fieldset via `aria-describedby` |
| 2 | Check focus | Focus is on the first radio "Checked on resident, no concern" |
| 3 | Check the Network panel | No `POST /api/v1/alerts/{id}/reviews` was sent |
| 4 | Check the checkbox | "Cold, cough or sore throat" still checked |

### TC-069-04 Save a review on R09

| Step | Action | Expected Result |
|---|---|---|
| 1 | Choose "Checked on resident, no concern" and click "Save review" | `POST /api/v1/alerts/{id}/reviews` returns 201 |
| 2 | Observe the panel | Polite announcement "Review saved."; the form is reset (no radio selected, note empty, counter "0 / 2000") |
| 3 | Read "Previous reviews" | One entry "<Mon D, h:mm AM/PM CT> · Clinician · Checked on resident, no concern" |
| 4 | Check the badges | App bar "Resident list" badge "1" (accessible name "Resident list, 1 alarm not reviewed"); R09 "Review and notes" link has no badge |
| 5 | Open R09 Summary | "Review status" "Reviewed"; pill "▲ Changed"; tile "Change score 26.8" |
| 6 | Open `/residents/R09/trends` | Chart unchanged: 14 bars, last value 26.8, Oct 21–30 red |
| 7 | Open `/residents` | R09 "Changed from their usual since Oct 21. Reviewed."; filters still "Changed (2)" |

### TC-069-05 Request body

| Step | Action | Expected Result |
|---|---|---|
| 1 | Re-seed; on `/residents/R10/review` check "Cold, cough or sore throat", choose "Explained by a known cause", type three spaces in "Note", click "Save review" | Request body `{"explanations": ["cold_cough_sore_throat"], "outcome": "known_cause"}` with no `note` key |
| 2 | Check the response | 201 with the review |
| 3 | Read "Previous reviews" | "<Mon D, h:mm AM/PM CT> · Clinician · Explained by a known cause" and "Possible explanations: Cold, cough or sore throat" |

### TC-069-06 Data problem outcome

| Step | Action | Expected Result |
|---|---|---|
| 1 | Re-seed; on `/residents/R09/review` choose "Looks like a data problem: send to study team" and click "Save review" | Announcement "Review saved and sent to the study team as a data problem." |
| 2 | Sign in as researcher and open `/study` | "Data problems to follow up" includes a "Study team" row "**R09:** a review flagged a data problem (Oct 30, Clinician)." (date = facility-local date of the review) |
| 3 | Run Database Validation step 3 | One open `review_flagged_data_problem` data alert linked to the new review |

### TC-069-07 Reminder on R10

| Step | Action | Expected Result |
|---|---|---|
| 1 | Re-seed; as clinician on `/residents/R10/review` click "Remind me in 24 hours" | `POST /api/v1/alerts/{id}/snooze` with body `{}` returns 200 |
| 2 | Observe | Announcement "Reminder set for <Mon D, h:mm AM/PM CT>. The alarm stays on." (time = now + 24 hours, facility time); line "Reminder set for <Mon D, h:mm AM/PM CT>." under the buttons |
| 3 | Check "Previous reviews" and the Summary | Still "Not reviewed yet."; Summary "Not reviewed"; section badge "1" still shown |
| 4 | Check the pill and the nav badge | Pill "▲ Changed"; nav badge "2" |

### TC-069-08 Two reviews on one alarm

| Step | Action | Expected Result |
|---|---|---|
| 1 | Re-seed; on R09 save "Explained by a known cause" with "Cold, cough or sore throat" checked and note "Resident has a cold; nurse notified." | Entry with "Possible explanations: Cold, cough or sore throat" and the note text |
| 2 | As admin save a second review on R09 with "Referred to nurse or provider" and no explanation | Two entries, newest first: "<time> · <admin display name> · Referred to nurse or provider" above the clinician's entry |
| 3 | Run `npx vitest run components/ReviewHistory components/AlertReviewForm` in `frontend/` | Passes (two fixture reviews, D-118) |

### TC-069-09 Researcher

| Step | Action | Expected Result |
|---|---|---|
| 1 | Sign in as researcher; open `/residents/R09/review` | Panel heading "Review alert: changed since Oct 21"; checklist, choices, note and buttons replaced by "Only clinicians and admins can review alarms." |
| 2 | Check "Previous reviews" | Still visible ("Not reviewed yet." on a fresh seed) |
| 3 | With the researcher token call `POST /api/v1/alerts/<R09 alert id>/reviews` with `{"outcome": "no_concern"}` | 403 problem+json; no review row created |
| 4 | Call `POST /api/v1/alerts/<R09 alert id>/snooze` with the researcher token | 403 |

### TC-069-10 Note limit and field errors

| Step | Action | Expected Result |
|---|---|---|
| 1 | Type 2000 characters into "Note" | Counter "2000 / 2000" |
| 2 | Try to type or paste more | Text stops at 2000 characters, or the API returns 422 with a field error shown under "Note" (linked by `aria-describedby`) |
| 3 | Send `POST /api/v1/alerts/<id>/reviews` with `{"outcome": "bogus"}` (curl, clinician token) | 422 `VALIDATION_ERROR` with `errors[]` item for `outcome` |
| 4 | Send `{"outcome": "no_concern", "explanations": ["unknown_code"]}` | 422 with an `explanations` field error |

### TC-069-11 Conflict and network errors

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `npx vitest run components/AlertReviewForm` in `frontend/` (a closed alert cannot be produced on DS-07 without changing the epoch) | The 409 `ALERT_CLOSED` case passes: the API error message is shown above the buttons and the entered values are kept |
| 2 | Fill the form, set the Network panel to "Offline", click "Save review" | Error message above the buttons with the connection text; the selected choice, checkboxes and note stay |
| 3 | Go online and click "Save review" again | 201, "Review saved." |

### TC-069-12 Config failure

| Step | Action | Expected Result |
|---|---|---|
| 1 | Block `*/api/v1/config/ui*` and open `/residents/R09/review` | Review form area shows "Could not load the alarm review. Check your connection and try again." with "Try again" |
| 2 | Check "Previous reviews" and "Staff notes" | Still rendered |

### TC-069-13 Keyboard and target size

| Step | Action | Expected Result |
|---|---|---|
| 1 | Tab through the panel | Order: five checkboxes, four radios (arrow keys move within the group), "Note", "Save review", "Remind me in 24 hours"; each shows a 3px `--link` focus outline |
| 2 | Press Space on a checkbox and arrows on the radios | Toggle and select |
| 3 | Measure the label rows | Each checkbox and radio label row is at least 44px high |

### TC-069-14 Reminder expiry

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `npx vitest run components/AlarmReviewPanel` | Passes FE-205: with `snoozed_until` 1 minute after now the reminder line and "Not reviewed" show; after the fake timers pass `snoozed_until` the line is gone without a new API call |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/config/ui` | 200; `alert_snooze_hours` 24; `review_explanations` codes `cold_cough_sore_throat`, `dental_dentures`, `medication_change`, `poor_sleep_unusual_day`, `room_device_moved` with their labels |
| 2 | `GET /api/v1/alerts?resident_code=R09` | One alert with `status` "open", `local_date` 2026-10-21 |
| 3 | `POST /api/v1/alerts/{id}/reviews` (clinician) `{"outcome": "no_concern"}` | 201 review; then `GET /api/v1/alerts?resident_code=R09` shows `status` "acknowledged" (reviewed); `GET /api/v1/residents/R09` `alarm_reviewed` true, `status` still "alarm_on" |
| 4 | `GET /api/v1/alerts/{id}/reviews` | 200 list newest first with `outcome`, `explanations`, `note`, reviewer display name, `created_at` |
| 5 | `POST /api/v1/alerts/{id}/snooze` `{}` (clinician) | 200; `snoozed_until` = now + 24 h; no review created |
| 6 | `POST /api/v1/alerts/{id}/reviews` with researcher token | 403 |
| 7 | `POST /api/v1/alerts/00000000-0000-0000-0000-000000000000/reviews` | 404 `ALERT_NOT_FOUND` |
| 8 | `POST /api/v1/alerts/{id}/reviews` with `{}` | 422 `VALIDATION_ERROR` (`outcome` required) |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | After TC-069-04: `SELECT ar.outcome, ar.explanations, ar.note FROM alert_reviews ar JOIN alerts a ON a.id = ar.alert_id JOIN residents r ON r.id = a.resident_id WHERE r.resident_code = 'R09';` | One row `no_concern`, `{}`, NULL |
| 2 | `SELECT a.status, a.acknowledged_by IS NOT NULL FROM alerts a JOIN residents r ON r.id = a.resident_id WHERE r.resident_code = 'R09';` | `acknowledged`, true (not `closed`; alarm stays on) |
| 3 | After TC-069-06: `SELECT kind, status, alert_review_id IS NOT NULL FROM data_alerts WHERE kind = 'review_flagged_data_problem';` | One row, `open`, true |
| 4 | After TC-069-07: `SELECT a.status, a.snoozed_until, a.snoozed_by IS NOT NULL FROM alerts a JOIN residents r ON r.id = a.resident_id WHERE r.resident_code = 'R10';` | `open`, now + 24 h, true; no `alert_reviews` row for R10 |
| 5 | `SELECT action FROM audit_logs WHERE action IN ('alert.reviewed','alert.snoozed') ORDER BY id DESC LIMIT 3;` | `alert.reviewed` per saved review, `alert.snoozed` per reminder |
| 6 | `SELECT s.cusum_tally FROM scores s JOIN residents r ON r.id = s.resident_id WHERE r.resident_code = 'R09' ORDER BY s.local_date DESC LIMIT 1;` | Unchanged by the review (≈ 26.8) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Save without a choice | "Choose what you found.", focus first radio, no request (TC-069-03) |
| 2 | Researcher tries to review | Form replaced; API 403 (TC-069-09) |
| 3 | Invalid outcome / explanation code | 422 field errors (TC-069-10) |
| 4 | Alert closed meanwhile | 409 `ALERT_CLOSED` message, values kept (TC-069-11) |
| 5 | Offline on save | Error above buttons, values kept (TC-069-11) |
| 6 | Config fails | Error inside the panel; previous reviews still shown (TC-069-12) |
| 7 | Resident not Changed | No review panel (TC-069-02) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-069-AC-01 | R09 panel with heading, five checkboxes and hint, four choices, two buttons, "Not reviewed yet.", open-questions note; none on R01 | TC-069-01, TC-069-02 |
| FEAT-069-AC-02 | Missing choice → "Choose what you found.", focus first radio, no request | TC-069-03 |
| FEAT-069-AC-03 | R09 "no concern" → "Review saved.", nav badge "1", section badge gone, Summary "Reviewed", list "… Reviewed.", pill "Changed", 26.8 | TC-069-04 |
| FEAT-069-AC-04 | Body with codes and outcome, whitespace note omitted; data-problem message | TC-069-05, TC-069-06 |
| FEAT-069-AC-05 | R10 reminder: snooze `{}`, no review, both reminder texts, pill "Changed" | TC-069-07 |
| FEAT-069-AC-06 | Researcher sees "Only clinicians and admins can review alarms.", previous reviews remain, POST 403 | TC-069-09 |
| FEAT-069-AC-07 | Two reviews newest first with time, reviewer, outcome; "Possible explanations: Cold, cough or sore throat" | TC-069-08 |

## Test Data Requirements

- DS-07 `test_v0_1` with open alarms R09 and R10; configured `review_explanations` (five provisional entries) and `alert_snooze_hours` 24.
- Seeded clinician ("Clinician"), researcher and admin with the `SEED_*` passwords.
- Synthetic note text only (e.g. "Resident has a cold; nurse notified."); no names or identifying details.
- Re-seed command between data-changing cases.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-069-FR-01 | FEAT-069 | TC-069-01, TC-069-02 |
| FEAT-069-FR-02, FR-03, FR-04 | FEAT-069 | TC-069-01 |
| FEAT-069-FR-05 | FEAT-069 | TC-069-03, TC-069-05 |
| FEAT-069-FR-06 | FEAT-069 | TC-069-04, TC-069-06 |
| FEAT-069-FR-07 | FEAT-069 | TC-069-04, TC-069-07 |
| FEAT-069-FR-08 | FEAT-069 | TC-069-10, TC-069-11 |
| FEAT-069-FR-09 | FEAT-069 | TC-069-07, TC-069-14 |
| FEAT-069-FR-10 | FEAT-069 | TC-069-04, TC-069-08 |
| FEAT-069-FR-11 | FEAT-069 | TC-069-01 |
| FEAT-069-FR-12 | FEAT-069 | TC-069-09 |
| FEAT-069-FR-13 | FEAT-069 | TC-069-01, TC-069-05 |
| FEAT-069-FR-14 | FEAT-069 | TC-069-13 |
| FEAT-069-FR-15 | FEAT-069 | TC-069-01, TC-069-04 |
| UX-310 | FEAT-069 | TC-069-01, TC-069-02 |
| UX-313, UX-314, UX-315 | FEAT-069 | TC-069-01 |
| UX-316 | FEAT-069 | TC-069-03 |
| UX-317 | FEAT-069 | TC-069-07, TC-069-14 |
| UX-318 | FEAT-069 | TC-069-04, TC-069-06 |
| UX-320 | FEAT-069 | TC-069-08 |
| UX-321 | FEAT-069 | TC-069-01 |
| UX-322 | FEAT-069 | TC-069-09 |
| UX-324 | FEAT-069 | TC-069-13 |
| UX-330 | FEAT-069 | TC-069-01, TC-069-04 |
| UX-207 | FEAT-069 | TC-069-10 |
| FE-079 | FEAT-069 | TC-069-10, TC-069-11 |
| FE-086, FE-134 | FEAT-069 | TC-069-04, TC-069-07 |
| FE-135 | FEAT-069 | TC-069-09 |
| FE-136, FE-137 | FEAT-069 | TC-069-01, TC-069-05 |
| FE-138 | FEAT-069 | TC-069-07 |
| FE-187 | FEAT-069 | TC-069-05 |
| FE-193 | FEAT-069 | TC-069-01, TC-069-07 |
| FE-205 | FEAT-069 | TC-069-14 |
| FE-209 | FEAT-069 | TC-069-01, TC-069-02 |
| E2E-09 | FEAT-069 | TC-069-05 |
| E2E-18 | FEAT-069 | TC-069-03, TC-069-04 |
| E2E-21 | FEAT-069 | TC-069-09 |
| TST-090 | FEAT-069 | TC-069-08, TC-069-11 |
| TST-111 | FEAT-069 | TC-069-13 |
| TDV-076 | FEAT-069 | TC-069-04 |
