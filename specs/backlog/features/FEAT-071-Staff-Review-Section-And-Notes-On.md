# FEAT-071 Staff review section and notes on Resident detail

| Field | Value |
|---|---|
| Epic | Frontend |
| Build phase | Phase 8 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-066, FEAT-033, FEAT-070 |
| Status | Not Started |

## Purpose

Implement the "Staff review" section on Resident detail (SRC-10): a note form (type, body 1–2000 characters, identifying-details hint, character counter, draft preserved on failure), the "Previous notes" list newest first showing only the latest versions, a "Mark as reviewed" button that opens the same `AlertReviewForm` as `/alerts` in a modal dialog only when the resident has a change alarm in the current epoch, the latest-review line, the OQ-05 open-question note, and a read-only mode without forms for researchers. Notes never change alert status; reviews are separate records.

## Business Context

- BR-13 (staff document observations, actions and follow-up, and review alarms from the resident view); BR-16 (no identifying details in notes; append-only notes; role control).
- Contract §20 R5 (single review model): "Mark as reviewed" creates an alarm review, never a note-based acknowledgement; OQ-05 (review does not reset the alarm).
- FRs covered (BACKLOG.md): FR-190, FR-191, FR-193, FR-194, FR-195.

## Referenced TRDs

- TRD 04 FE-085 (invalidations after note), FE-089 (draft preserved), FE-130..FE-135 (save note with `alert_id`, review dialog, disabled rules, confirmation, no UI state change after review, role gating), FE-187 (E2E step), §4.8 `StaffReviewForm`, `NotesList`, `ReviewDialog`.
- TRD 11 UX-120..UX-138 (layout, controls and order, button styles, note vs review, empty-note message, OQ-05 note, API state after review, latest-review line, plain-text notes, append-only, confirmation, failure text, researcher text, note types, notes list, "Show all notes", review dialog, dialog save, role hiding).
- TRD 12 SEC-124 (hint "Do not enter names or other identifying details.", 2000-character limit), SEC-043, SEC-076.
- TRD 19 E-15 `GET /residents/{code}/notes`, E-16 `POST /residents/{code}/notes`, E-13 (open alarm), E-14 (review via dialog).
- TRD 02 FR-190, FR-191, FR-193, FR-194, FR-195.
- TRD 13 E2E-09, TST-090; AC-UX-06, AC-FE-10.

## Scope

- `StaffReviewForm` (`{ residentCode, openAlertId, canWrite }`), `NotesList` (`{ notes, tz }`), `ReviewDialog` (`{ alarm, open, onClose }`, native `<dialog>` wrapping `AlertReviewForm` from FEAT-070).
- Section placement as the left column of the review row next to the check-in log (stacking on narrow screens per FEAT-075).
- Queries `getNotes(code)`, `getAlerts({ residentCode })` (open alarm of the current epoch); mutation `createNote`.
- E2E step 2 of `mutating.spec.ts` (E2E-09 / FE-187).

## Out of Scope

- Notes and alert endpoints (FEAT-033, FEAT-030/FEAT-031).
- `AlertReviewForm` itself (FEAT-070).
- Editing or deleting notes (not offered, UX-129); note supersession through the UI is not specified (see Implementation Notes).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-071-FR-01 | The section shall contain, in order: heading "Staff review"; select "Type of note" with "Observation" (default), "Action taken", "Follow-up"; textarea "Note (what staff saw or did)" (3 rows, placeholder "e.g. “Resident has a cold; nurse notified.”"); counter "<count> / 2000"; the hint "Do not enter names or other identifying details."; buttons "Mark as reviewed" (only with a change alarm in the current epoch) and "Save note"; the open-question note. | UX-121, UX-120, SEC-124, FR-190 |
| FEAT-071-FR-02 | "Mark as reviewed" shall be the primary button (min-height 44px, 2px ink border, 600) and "Save note" secondary (1px `--color-border`). | UX-122 |
| FEAT-071-FR-03 | "Save note" shall call `createNote(code, { note_type, body, alert_id })` with `alert_id` = the resident's open alarm id when one exists; notes never change alert status. | FE-130, UX-123, FR-191 |
| FEAT-071-FR-04 | "Save note" shall be disabled while the trimmed body is empty or longer than 2000 characters and while a request is in flight; attempting to save an empty note shows "Write a short note before saving." under the textarea via `aria-describedby`. | FE-132, UX-124, FR-190 |
| FEAT-071-FR-05 | After a successful save the body is cleared, the note type kept, "Note saved." announced in an `aria-live="polite"` region, and `["resident", code]`, `["residents"]`, `["alerts"]` invalidated. | FE-133, FE-085, UX-130 |
| FEAT-071-FR-06 | On failure "Could not save the note. Your text is kept — try again." shall appear and the typed text and type remain. | FE-089, UX-131 |
| FEAT-071-FR-07 | "Previous notes" (h3) shall list notes newest first as "<Mon D, h:mm AM/PM> · <Type> · <display name>" followed by the note text exactly as typed (plain text, line breaks preserved), showing only latest versions (API default excludes superseded notes); "No notes yet." when empty; at most 10 initially with "Show all notes (<count>)". | UX-133, UX-134, UX-135, UX-128, FR-193 |
| FEAT-071-FR-08 | "Mark as reviewed" shall open a modal native `<dialog>` titled "Review alarm · <R> · alarm since <Mon D>" containing the `/alerts` `AlertReviewForm` and a "Cancel" button; focus moves to its heading; Escape and Cancel close without saving and return focus to "Mark as reviewed". | FE-131, UX-136, FR-191 |
| FEAT-071-FR-09 | Saving in the dialog shall create an alarm review (`POST /alerts/{id}/reviews`), close the dialog and announce "Review saved." (or the data-problem variant); `POST /alerts/{id}/acknowledge` is never called. | FE-131, UX-137 |
| FEAT-071-FR-10 | After a review the badge, chart and alarm wording stay as returned by the API; when the alarm has at least one review, a line under the heading reads "Reviewed by <display name>, <Mon D, h:mm AM/PM> · <outcome label>. The alarm stays on (open question OQ-05)." from the latest review. | FE-134, UX-126, UX-127 |
| FEAT-071-FR-11 | The open-question note shall read "Open question (OQ-05): does review reset the tally or turn the alarm off? Not in pipeline v0.1 — a saved review marks the alarm as reviewed only; the alarm and the tally stay as they are." | UX-125, FR-195 |
| FEAT-071-FR-12 | For researchers (`canWriteNotes` false) the controls shall be replaced by "Only clinicians and admins can add notes." while previous notes remain; "Mark as reviewed" shall not render for roles without `canReviewAlarms`. | FE-135, UX-132, UX-138, FR-194, SEC-043 |
| FEAT-071-FR-13 | The UI shall offer no editing or deleting of saved notes. | UX-129 |

## Inputs

- `GET /api/v1/residents/{code}/notes` → `StaffNoteList`; `GET /api/v1/alerts?resident_code=<R>` (open alarm id and alarm date of the current epoch); `GET /api/v1/alerts/{id}/reviews` (latest review line); `UiConfig` (via FEAT-070 form).
- User input: note type and body; role from `useAuth()`.

## Outputs

- `POST /residents/{code}/notes` and (via dialog) `POST /alerts/{id}/reviews` requests; rendered notes list, messages and dialog.

## Data Flow

Page queries `["resident", code, "notes"]` and `["alerts", {residentCode}]` → `StaffReviewForm` (draft in component state) → `createNote` → invalidate → `NotesList` refresh. "Mark as reviewed" → `ReviewDialog` → `AlertReviewForm` (FEAT-070) → `createAlertReview` → FE-086 invalidations → badge and alerts reflect API state.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-066, FEAT-033, FEAT-070

- FEAT-066 provides the Resident detail page and its parallel `getNotes` query.
- FEAT-033 provides the notes endpoints.
- FEAT-070 provides `AlertReviewForm` reused in the dialog.

Features that build directly on this one (BACKLOG.md §4): FEAT-075.

## Database Impact

None directly; the backend inserts `staff_notes` rows (append-only) and audit `note.created` (FEAT-033), and `alert_reviews` via FEAT-031.

## API Impact

Endpoints consumed: `GET /api/v1/residents/{resident_code}/notes` (E-15), `POST /api/v1/residents/{resident_code}/notes` (E-16), `GET /api/v1/alerts` (E-13), `GET /api/v1/alerts/{id}/reviews` (E-28), `POST /api/v1/alerts/{id}/reviews` (E-14), `GET /api/v1/config/ui` (E-32). None exposed.

## Frontend Impact

- Components: `StaffReviewForm`, `NotesList`, `ReviewDialog` on `app/(protected)/residents/[residentCode]/page.tsx`; wording in `lib/wording.ts`.

## Analytics Impact

None.

## Security Requirements

- Note form and "Mark as reviewed" only for admin and clinician (SEC-043, FE-135); backend returns 403 otherwise.
- Hint against identifying details and 2000-character limit (SEC-124); note bodies rendered as text, never HTML (FE-063, SEC-076).

## Error Handling

- Empty note → inline message, no request (UX-124).
- Save failure → message, draft kept (UX-131, FE-089); 422 `ALERT_RESIDENT_MISMATCH` or `VALIDATION_ERROR` → field/form error by `ApiError.code` (FE-079).
- Dialog save failure → errors inside the dialog; dialog stays open.

## Logging Requirements

None in the frontend; the backend writes `note.created` and `alert.reviewed` audit rows (TRD 12 §4.12).

## Testing Requirements

- Component (`components/StaffReviewForm/StaffReviewForm.test.tsx`, TST-090): controls and order, disabled rules (empty, > 2000), empty-note message, success message and cleared body with type kept, failure keeps draft, researcher replacement, "Mark as reviewed" only with an alarm; `NotesList` formatting, "No notes yet.", "Show all notes (n)"; `ReviewDialog` focus handling (Escape, Cancel, focus return).
- E2E (`@mutating`, `mutating.spec.ts` step 2, FE-187 / E2E-09): add "Observation" note "Resident has a cold; nurse notified." on R09 and see it listed; "Mark as reviewed" → "Cold, cough or sore throat" + "Explained by a known cause" → Save → dialog closes, review in history, `/alerts` R09 "Reviewed", nav "Alerts (1)", badge "▲ Alarm since Oct 21".
- E2E FE-188 part: researcher sees no note form.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-071-AC-01 | As clinician on R09, saving an "Observation" note "Resident has a cold; nurse notified." announces "Note saved.", lists the note with author and time, and leaves the alert status unchanged. | E2E-09; FE-187; UX-130 |
| FEAT-071-AC-02 | "Mark as reviewed" opens the dialog "Review alarm · R09 · alarm since Oct 21"; saving with "Cold, cough or sore throat" and "Explained by a known cause" closes it, the review appears in the alert's history, `/alerts` shows R09 "Reviewed" and "Alerts (1)", and the badge still reads "▲ Alarm since Oct 21". | FE-187; AC-FE-10; AC-UX-06 |
| FEAT-071-AC-03 | A clinician can save a note of each type and each appears with its type label. Verified by: Component (`components/StaffReviewForm/StaffReviewForm.test.tsx`; TST-090). | AC-UX-06; UX-133 |
| FEAT-071-AC-04 | As researcher the section shows "Only clinicians and admins can add notes.", previous notes, and no "Mark as reviewed" button. | AC-UX-06; FE-188; FR-194 |
| FEAT-071-AC-05 | On R01 (no change alarm) "Mark as reviewed" is not rendered. Verified by: Component (`components/StaffReviewForm/StaffReviewForm.test.tsx`; TST-090). | UX-121; FR-191 |
| FEAT-071-AC-06 | A mocked failed save shows "Could not save the note. Your text is kept — try again." and the textarea keeps the typed text. Verified by: Component (`components/StaffReviewForm/StaffReviewForm.test.tsx`; TST-090). | UX-131; FE-089 |
| FEAT-071-AC-07 | "Save note" is disabled for a whitespace-only body and for 2001 characters. Verified by: Component (`components/StaffReviewForm/StaffReviewForm.test.tsx`; TST-090). | FE-132 |

## Definition of Done

- All FEAT-071 acceptance criteria pass; component tests and the `@mutating` E2E step pass in Chromium.
- OQ-05 note present (TRD 25 Phase 8 DoD).
- Batch report lists IDs and the gap below (AGT-022).

## Implementation Notes

- FR-192 and E-16 allow a new note to supersede an earlier one (`supersedes_id`), but TRD 11 offers no edit control (UX-129, now also stated in FR-192) and FR-193 only requires that the list shows the latest versions; do not build an edit UI. The list relies on the API default `include_superseded=false` (API-083).
- Keep the draft in component state only, never in storage (FE-089, FE-045).
- Use the native `<dialog>` element with `showModal()` so focus trapping and Escape work without extra libraries (FE-131).
