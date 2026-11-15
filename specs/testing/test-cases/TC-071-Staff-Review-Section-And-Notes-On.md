# Staff notes in the resident chart

## Feature Description

The "Staff notes" panel of the chart's "Review and notes" section (`/residents/[residentCode]/review`, SRC-21), after the alarm review panel of a Changed resident or alone for any other resident: the select "Type of note" ("Observation", "Action taken", "Follow-up"), the textarea "New note" with placeholder "Add a note", the hint "Do not enter names or other identifying details.", the counter "<count> / 2000", the secondary button "Add note" with the empty-note message, the confirmation "Note saved." and the failure message with the draft kept, the "Previous notes" list newest first with type and author, the empty text, "Show all notes (<count>)" and the read-only text for researchers. Notes are append-only and separate from alarm reviews: a note never marks an alarm reviewed. The v0.1 "Mark as reviewed" button and dialog are retired and verified as absent (TRD 11 UX-120..UX-135; TRD 04 FE-085, FE-089, FE-130..FE-135; TRD 12 SEC-124; TRD 19 E-15, E-16).

## Preconditions

- Local Docker Compose demo profile running, freshly seeded with `test_v0_1` and the DS-07 pipeline run (as-of Oct 30, 2026, 3:00 PM CT); no staff notes, no reviews.
- Seeded users `clinician@example.com` (display name "Clinician"), `researcher@example.com`, `admin@example.com` with the `SEED_*` passwords.
- Cases that save notes change the database; re-seed between runs (`docker compose exec -T backend python -m backend.cli seed test_v0_1 --reset` plus the DS-07 pipeline run).
- Browser developer tools (Network panel, Accessibility tree); `psql` read access.
- Note texts are synthetic only; never a name, room or other identifying detail.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-071-01 | Panel placement and controls (R01 only panel; R09 after review panel) | High | UI |
| TC-071-02 | Empty state of "Previous notes" | High | UI |
| TC-071-03 | Add an "Observation" note on R10: message, list entry, alarm unchanged | High | Positive |
| TC-071-04 | Notes of each type show their type label; newest first | High | Positive |
| TC-071-05 | Plain text kept exactly (line breaks, markup not rendered) | High | Security |
| TC-071-06 | Empty or whitespace note: button blocked, "Write a short note before saving." | High | Negative |
| TC-071-07 | 2000-character limit and counter | Medium | Negative |
| TC-071-08 | Save failure keeps the draft | High | Negative |
| TC-071-09 | Researcher: form replaced, notes visible, POST 403 | High | Security |
| TC-071-10 | "Show all notes (<count>)" after more than 10 notes | Medium | Positive |
| TC-071-11 | No edit, delete or "Mark as reviewed" controls | Medium | Negative |
| TC-071-12 | Notes request fails: error only in the notes list | Medium | Negative |
| TC-071-13 | API validation of note requests (422, 404, alert mismatch) | Medium | API |

### TC-071-01 Placement and controls

| Step | Action | Expected Result |
|---|---|---|
| 1 | Sign in as clinician; open `/residents/R01/review` | Only panel: `<h2>` "Staff notes" |
| 2 | Read the controls in order | Select "Type of note" with "Observation" (selected), "Action taken", "Follow-up"; textarea (3 rows, vertical resize) with accessible name "New note" and placeholder "Add a note"; hint "Do not enter names or other identifying details." (13px, `--muted`); counter "0 / 2000"; secondary button "Add note"; then "Previous notes" |
| 3 | Inspect the textarea | `aria-describedby` references the hint |
| 4 | Open `/residents/R09/review` | "Staff notes" panel follows the "Review alert: changed since Oct 21" panel |
| 5 | Inspect "Add note" | Secondary style: min-height 44px, `--surface` background, ink text, 1px solid `--rule` border |

### TC-071-02 Empty notes list

| Step | Action | Expected Result |
|---|---|---|
| 1 | On a fresh seed open `/residents/R01/review` | Under the form: "No notes yet. Add what you saw or did, for example “Resident has a cold; nurse notified.”" in `--muted`, no list |

### TC-071-03 Add an Observation note on R10

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `/residents/R10/review` keep "Observation", type "Resident has a cold; nurse notified." | Counter "36 / 2000"; "Add note" enabled |
| 2 | Click "Add note" | `POST /api/v1/residents/R10/notes` returns 201 with body `{"note_type": "observation", "body": "Resident has a cold; nurse notified.", "alert_id": "<R10 open alert id>"}` |
| 3 | Observe the form | Polite announcement "Note saved."; textarea cleared; "Type of note" still "Observation" |
| 4 | Read "Previous notes" (`<h3>`, 16px) | "<Mon D, h:mm AM/PM CT> · Observation · Clinician" followed by "Resident has a cold; nurse notified." |
| 5 | Check the review panel and Summary | "Previous reviews" still "Not reviewed yet."; Summary "Review status" "Not reviewed"; pill "▲ Changed"; section badge "1"; nav badge "2" |

### TC-071-04 Note types and order

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `/residents/R01/review` add notes in order: "Action taken" "Offered water before the check-in.", then "Follow-up" "Check device placement tomorrow." | Each save announces "Note saved." |
| 2 | Read "Previous notes" | Newest first: "<time> · Follow-up · Clinician" / "Check device placement tomorrow."; then "<time> · Action taken · Clinician" / "Offered water before the check-in." |
| 3 | Check the type select after the second save | Still "Follow-up" (type kept) |

### TC-071-05 Plain text

| Step | Action | Expected Result |
|---|---|---|
| 1 | Add a note with two lines ("Line one" Enter "Line two") | Listed on two lines, exactly as typed |
| 2 | Add a note `<b>bold</b> <a href="https://example.com">link</a>` | Shown literally as text; no bold, no clickable link; no script runs |
| 3 | Run Database Validation step 2 | `body` stored exactly as typed |

### TC-071-06 Empty note

| Step | Action | Expected Result |
|---|---|---|
| 1 | With an empty textarea inspect "Add note" | `aria-disabled="true"` |
| 2 | Click "Add note" | Message "Write a short note before saving." under the textarea, linked by `aria-describedby`; no `POST` in the Network panel |
| 3 | Type only spaces and click "Add note" | Same message; no request |

### TC-071-07 Character limit

| Step | Action | Expected Result |
|---|---|---|
| 1 | Paste 2000 characters | Counter "2000 / 2000"; "Add note" enabled |
| 2 | Add one more character (2001) | "Add note" blocked (`aria-disabled="true"`); no request on click |
| 3 | Send `POST /api/v1/residents/R01/notes` with a 2001-character body (curl, clinician token) | 422 `VALIDATION_ERROR` with a `body` field error |

### TC-071-08 Save failure

| Step | Action | Expected Result |
|---|---|---|
| 1 | Type "Resident tired this morning." and select "Follow-up"; set the Network panel to "Offline"; click "Add note" | Message "Could not save the note. Your text is kept — try again." |
| 2 | Check the form | Text "Resident tired this morning." and type "Follow-up" kept |
| 3 | Go online and click "Add note" | "Note saved."; note listed |

### TC-071-09 Researcher

| Step | Action | Expected Result |
|---|---|---|
| 1 | After TC-071-03, sign in as researcher; open `/residents/R10/review` | Form controls replaced by "Only clinicians and admins can add notes." |
| 2 | Read "Previous notes" | The clinician's note is visible |
| 3 | With the researcher token call `POST /api/v1/residents/R10/notes` `{"note_type": "observation", "body": "Test note."}` | 403; no row created |

### TC-071-10 Show all notes

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `/residents/R01/review` add 11 short notes ("Note 1" … "Note 11") | List shows 10 notes ("Note 11" … "Note 2") and a button "Show all notes (11)" |
| 2 | Click "Show all notes (11)" | All 11 notes, newest first, "Note 1" last |

### TC-071-11 No editing, deleting or reviewing

| Step | Action | Expected Result |
|---|---|---|
| 1 | Inspect each listed note | No edit or delete control |
| 2 | Search the section for "Mark as reviewed" | Not present |
| 3 | Run Database Validation step 3 | `marked_reviewed` false for all notes; alerts unchanged |

### TC-071-12 Notes request failure

| Step | Action | Expected Result |
|---|---|---|
| 1 | Block `*/api/v1/residents/R09/notes*` and open `/residents/R09/review` | Notes list area shows "Could not load staff notes. Check your connection and try again." with "Try again"; the review panel above renders normally |

### TC-071-13 API validation

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/residents/R01/notes` with `{"note_type": "observation", "body": "x", "alert_id": "<R09 alert id>"}` (clinician) | 422 `ALERT_RESIDENT_MISMATCH` |
| 2 | `POST /api/v1/residents/R01/notes` with `{"note_type": "diary", "body": "x"}` | 422 `VALIDATION_ERROR` (`note_type`) |
| 3 | `POST /api/v1/residents/R99/notes` with a valid body | 404 |
| 4 | `GET /api/v1/residents/R10/notes` | 200; notes newest first with `note_type`, `body`, author display name, `created_at` |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents/R01/notes` on a fresh seed | 200 with an empty list |
| 2 | `POST /api/v1/residents/R10/notes` (clinician) valid body | 201 note |
| 3 | `POST` with researcher token | 403 |
| 4 | `POST` with empty or whitespace `body` | 422 `VALIDATION_ERROR` |
| 5 | `POST` with mismatching `alert_id` | 422 `ALERT_RESIDENT_MISMATCH` |
| 6 | `GET /api/v1/alerts?resident_code=R10` after a note | Alert `status` still "open" (a note does not review the alarm) |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | After TC-071-03: `SELECT n.note_type, n.body, n.alert_id IS NOT NULL, u.email FROM staff_notes n JOIN users u ON u.id = n.author_user_id JOIN residents r ON r.id = n.resident_id WHERE r.resident_code = 'R10';` | `observation`, "Resident has a cold; nurse notified.", true, clinician@example.com |
| 2 | After TC-071-05: `SELECT body FROM staff_notes ORDER BY created_at DESC LIMIT 2;` | Bodies exactly as typed (line break and markup text preserved) |
| 3 | `SELECT count(*) FROM staff_notes WHERE marked_reviewed;` and `SELECT a.status FROM alerts a JOIN residents r ON r.id = a.resident_id WHERE r.resident_code = 'R10';` | 0; `open` |
| 4 | `SELECT count(*) FROM alert_reviews;` after notes only | 0 |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Empty or whitespace note | "Write a short note before saving.", no request (TC-071-06) |
| 2 | 2001 characters | Button blocked; API 422 (TC-071-07) |
| 3 | Offline save | "Could not save the note. Your text is kept — try again.", draft kept (TC-071-08) |
| 4 | Researcher | Form replaced; API 403 (TC-071-09) |
| 5 | Notes request fails | Error only in the notes list (TC-071-12) |
| 6 | Alert of another resident | 422 `ALERT_RESIDENT_MISMATCH` (TC-071-13) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-071-AC-01 | R10 Observation note: "Note saved.", listed "<Mon D, h:mm AM/PM CT> · Observation · <display name>" with text; R10 still "Not reviewed" and "Changed" | TC-071-03 |
| FEAT-071-AC-02 | A note of each type appears with its type label | TC-071-03, TC-071-04 |
| FEAT-071-AC-03 | Researcher sees "Only clinicians and admins can add notes." and previous notes | TC-071-09 |
| FEAT-071-AC-04 | R01 shows only "Staff notes"; empty text "No notes yet. Add what you saw or did, for example “Resident has a cold; nurse notified.”" | TC-071-01, TC-071-02 |
| FEAT-071-AC-05 | Failed save shows "Could not save the note. Your text is kept — try again." and keeps the text | TC-071-08 |
| FEAT-071-AC-06 | "Add note" blocked for whitespace and 2001 characters; empty attempt shows "Write a short note before saving." | TC-071-06, TC-071-07 |

## Test Data Requirements

- DS-07 `test_v0_1`; R10 open alarm (note linked by `alert_id`), R01 without alarm.
- Synthetic note texts listed in the steps; no names or identifying details.
- Seeded clinician, researcher, admin with `SEED_*` passwords; re-seed command.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-071-FR-01 | FEAT-071 | TC-071-01 |
| FEAT-071-FR-02 | FEAT-071 | TC-071-01 |
| FEAT-071-FR-03 | FEAT-071 | TC-071-03, TC-071-13 |
| FEAT-071-FR-04 | FEAT-071 | TC-071-06, TC-071-07 |
| FEAT-071-FR-05 | FEAT-071 | TC-071-03, TC-071-04 |
| FEAT-071-FR-06 | FEAT-071 | TC-071-08 |
| FEAT-071-FR-07 | FEAT-071 | TC-071-02, TC-071-04, TC-071-05, TC-071-10 |
| FEAT-071-FR-08 | FEAT-071 | TC-071-03 |
| FEAT-071-FR-09 | FEAT-071 | TC-071-09 |
| FEAT-071-FR-10 | FEAT-071 | TC-071-11 |
| UX-120, UX-121, UX-122 | FEAT-071 | TC-071-01 |
| UX-123, UX-126 | FEAT-071 | TC-071-03, TC-071-11 |
| UX-124 | FEAT-071 | TC-071-06, TC-071-07 |
| UX-128 | FEAT-071 | TC-071-05 |
| UX-129 | FEAT-071 | TC-071-11 |
| UX-130 | FEAT-071 | TC-071-03 |
| UX-131 | FEAT-071 | TC-071-08 |
| UX-132 | FEAT-071 | TC-071-09 |
| UX-133, UX-134 | FEAT-071 | TC-071-02, TC-071-04 |
| UX-135 | FEAT-071 | TC-071-10 |
| FE-085, FE-130, FE-133 | FEAT-071 | TC-071-03 |
| FE-089 | FEAT-071 | TC-071-08 |
| FE-132 | FEAT-071 | TC-071-06, TC-071-07 |
| FE-135 | FEAT-071 | TC-071-09 |
| FE-187 | FEAT-071 | TC-071-03 |
| FE-188 | FEAT-071 | TC-071-09 |
| SEC-124 | FEAT-071 | TC-071-01, TC-071-07 |
| SEC-076 | FEAT-071 | TC-071-05 |
| E2E-09 | FEAT-071 | TC-071-03 |
| TST-090 | FEAT-071 | TC-071-04, TC-071-06, TC-071-08 |
