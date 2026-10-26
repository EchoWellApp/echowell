# FEAT-071 Staff notes in the resident chart

| Field | Value |
|---|---|
| Epic | Frontend |
| Build phase | Phase 8 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-066, FEAT-033 |
| Status | Not Started |

## Purpose

Implement the "Staff notes" panel of the chart's "Review and notes" section (`/residents/[residentCode]/review`, SRC-21), after the alarm review panel of a Changed resident (FEAT-069) or alone for any other resident: the select "Type of note" (Observation, Action taken, Follow-up; kept from v0.1 because SRC-12 and BR-13 require the three note types, TRD 24 D-111), a textarea "New note" with placeholder "Add a note" and a character counter, the secondary button "Add note" with the empty-note message, the confirmation and failure messages with the draft preserved, the "Previous notes" list newest first with type and author, the empty text and "Show all notes (<count>)", and the read-only text for researchers. Notes are free staff notes, append-only and separate from alarm reviews: a note never marks an alarm reviewed (contract §20 R5). The v0.1 "Staff review" heading, the "Mark as reviewed" button and its dialog, and the OQ-05 note in this panel are retired (TRD 11 UX-125, UX-136..UX-138; the review form and the open-questions note are in FEAT-069).

## Business Context

- BR-13 (staff document observations, actions taken and follow-up next to the resident's chart); BR-16 (append-only notes; role control; no identifying details).
- Contract §20 R5 (single review model): notes and reviews are separate records; OQ-05 (nothing a note or review does resets the alarm).
- D-110 (notes in "Review and notes"), D-111 (note types and previous notes kept although the wireframe shows a single text box).
- FRs covered (BACKLOG.md): FR-190, FR-192, FR-193, FR-194.

## Referenced TRDs

- TRD 11 (v0.13) — owned by this feature: UX-120, UX-121 (placement and controls), UX-123, UX-124 (note vs review, empty-note rule and message), UX-126 (pill, chart and alarm wording unchanged after a save), UX-128..UX-135 (plain-text notes, append-only, confirmation, failure text, researcher text, note types, "Previous notes" and empty text, "Show all notes"). Uses the button styles of UX-122 (FEAT-062). Retired, not built: UX-125 (moved to UX-321, FEAT-069), UX-127 (withdrawn, D-102), UX-136..UX-138 (review dialog).
- TRD 04 FE-085 (invalidations after a note), FE-089 (draft preserved), FE-130, FE-132, FE-133, FE-135 (save note, disabled rules, confirmation, role gating), FE-187 (E2E step), §4.8 `StaffNotes`, `NotesList` (as updated for wireframe v0.2).
- TRD 12 SEC-124 (identifying-details hint, 2000-character limit), SEC-043, SEC-076.
- TRD 19 E-15 `GET /residents/{code}/notes`, E-16 `POST /residents/{code}/notes`.
- TRD 02 FR-190, FR-192, FR-193, FR-194; TRD 24 D-102, D-110, D-111.
- TRD 13 E2E-09 (note step), TST-090; AC-UX-06.

## Scope

- `StaffNotes` (`{ residentCode, openAlertId, canWrite }`) and `NotesList` (`{ notes, tz }`) on `app/(protected)/residents/[residentCode]/review/page.tsx`, after `AlarmReviewPanel` (FEAT-069) when present.
- Query `getNotes(code)`; mutation `createNote`.
- Note step of E2E-09 in `mutating.spec.ts` (FE-187).

## Out of Scope

- Notes endpoints (FEAT-033).
- The alarm review form, reminder, previous reviews and open-questions note (FEAT-069).
- Editing or deleting notes (not offered, UX-129); note supersession through the UI is not specified (see Implementation Notes).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-071-FR-01 | The "Staff notes" panel shall follow the alarm review panel of a Changed resident, or be the only panel of the "Review and notes" section for any other resident. | UX-120 |
| FEAT-071-FR-02 | The panel shall contain, in order: heading "Staff notes" (h2); a select labelled "Type of note" with "Observation" (default), "Action taken", "Follow-up"; a textarea (3 rows, vertical resize, padding 10px, accessible name "New note", placeholder "Add a note"); the hint "Do not enter names or other identifying details."; a counter "<count> / 2000"; the secondary button "Add note"; then the list of FEAT-071-FR-07. | UX-121, UX-133, SEC-124, FR-190, D-111 |
| FEAT-071-FR-03 | "Add note" shall call `createNote(code, { note_type, body, alert_id })` with `alert_id` = the resident's open alarm id when one exists; a note never changes alert status or marks an alarm reviewed. | FE-130, UX-123, contract §20 R5 |
| FEAT-071-FR-04 | "Add note" shall be disabled while the trimmed body is empty or longer than 2000 characters and while a request is in flight; an attempt to save an empty note shows "Write a short note before saving." under the textarea, linked via `aria-describedby`. | FE-132, UX-124, FR-190 |
| FEAT-071-FR-05 | After a successful save the textarea is cleared, the note type kept, "Note saved." announced in an `aria-live="polite"` region, and `["resident", code]`, `["resident", code, "notes"]` and `["residents"]` invalidated. | FE-133, FE-085, UX-130 |
| FEAT-071-FR-06 | On failure "Could not save the note. Your text is kept — try again." shall appear and the typed text and type remain. | FE-089, UX-131 |
| FEAT-071-FR-07 | Under the form, "Previous notes" (h3, 16px) shall list the resident's notes newest first as "<Mon D, h:mm AM/PM> · <Type> · <display name>" followed by the note text exactly as typed (plain text, line breaks preserved), showing only latest versions (API default excludes superseded notes); with no notes the panel reads "No notes yet. Add what you saw or did, for example “Resident has a cold; nurse notified.”" (`--muted`) instead of the list; at most 10 notes initially with "Show all notes (<count>)". | UX-128, UX-133, UX-134, UX-135, FR-193 |
| FEAT-071-FR-08 | After a note is saved the status pill, change score chart and alarm wording stay as returned by the API. | UX-126 |
| FEAT-071-FR-09 | For researchers (`canWriteNotes` false) the form controls shall be replaced by "Only clinicians and admins can add notes." while previous notes remain visible. | FE-135, UX-132, FR-194, SEC-043 |
| FEAT-071-FR-10 | The UI shall offer no editing or deleting of saved notes. | UX-129, FR-192 |

## Inputs

- `GET /api/v1/residents/{code}/notes` → `StaffNoteList`; the resident's open alarm id from FEAT-066's alerts query.
- User input: note type and body; role from `useAuth()`.

## Outputs

- `POST /residents/{code}/notes` requests; rendered notes list and messages.

## Data Flow

Section page → `["resident", code, "notes"]` → `NotesList`; `StaffNotes` (draft in component state) → `createNote` → invalidate → `NotesList` refresh.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-066, FEAT-033

- FEAT-066 provides the chart layout, the `/review` route shell and the open-alarm query.
- FEAT-033 provides the notes endpoints.

Features that build directly on this one (BACKLOG.md §4): FEAT-075.

## Database Impact

None directly; the backend inserts `staff_notes` rows (append-only) and audit `note.created` (FEAT-033).

## API Impact

Endpoints consumed: `GET /api/v1/residents/{resident_code}/notes` (E-15), `POST /api/v1/residents/{resident_code}/notes` (E-16). None exposed.

## Frontend Impact

- Components: `StaffNotes`, `NotesList` on `app/(protected)/residents/[residentCode]/review/page.tsx`; wording in `lib/wording.ts`.

## Analytics Impact

None.

## Security Requirements

- Note form only for admin and clinician (SEC-043, FE-135); backend returns 403 otherwise.
- Hint against identifying details and 2000-character limit (SEC-124); note bodies rendered as text, never HTML (FE-063, SEC-076).

## Error Handling

- Empty note → inline message, no request (UX-124).
- Save failure → message, draft kept (UX-131, FE-089); 422 `ALERT_RESIDENT_MISMATCH` or `VALIDATION_ERROR` → field or form error by `ApiError.code` (FE-079).
- Notes query error → error state in the notes list only; the review panel above is unaffected (UX-202).

## Logging Requirements

None in the frontend; the backend writes `note.created` audit rows (TRD 12 §4.12).

## Testing Requirements

- Component (`components/StaffNotes/StaffNotes.test.tsx`, TST-090): controls and order, accessible name "New note" and placeholder "Add a note", disabled rules (empty, > 2000), empty-note message, success message with cleared text and type kept, failure keeps draft, researcher replacement; `NotesList` formatting, empty text, "Show all notes (n)"; no "Mark as reviewed" control exists.
- E2E (`@mutating`, `mutating.spec.ts` note step of E2E-09 / FE-187): add "Observation" note "Resident has a cold; nurse notified." on `/residents/R09/review` and see it listed with type, author and time; R09's pill still "Changed".
- E2E FE-188 part: researcher sees no note form.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-071-AC-01 | As clinician on `/residents/R09/review`, adding an "Observation" note "Resident has a cold; nurse notified." announces "Note saved.", lists the note as "<Mon D, h:mm AM/PM> · Observation · <display name>" with its text, and leaves R09's review status "Not reviewed" and pill "Changed". | E2E-09; FE-187; UX-130; UX-123 |
| FEAT-071-AC-02 | A clinician can save a note of each type and each appears with its type label. Verified by: Component (`StaffNotes.test.tsx`; TST-090). | AC-UX-06; UX-133 |
| FEAT-071-AC-03 | As researcher the panel shows "Only clinicians and admins can add notes." and the previous notes. | AC-UX-06; FE-188; FR-194 |
| FEAT-071-AC-04 | On R01 the "Review and notes" section shows only the "Staff notes" panel; with no notes it reads "No notes yet. Add what you saw or did, for example “Resident has a cold; nurse notified.”" Verified by: Component and Page test (TST-090, TST-094). | UX-120; UX-134 |
| FEAT-071-AC-05 | A mocked failed save shows "Could not save the note. Your text is kept — try again." and the textarea keeps the typed text. Verified by: Component (`StaffNotes.test.tsx`; TST-090). | UX-131; FE-089 |
| FEAT-071-AC-06 | "Add note" is disabled for a whitespace-only body and for 2001 characters; trying to save an empty note shows "Write a short note before saving." Verified by: Component (`StaffNotes.test.tsx`; TST-090). | FE-132; UX-124 |

## Definition of Done

- All FEAT-071 acceptance criteria pass; component tests and the `@mutating` E2E step pass in Chromium.
- Batch report lists IDs and the gap below (AGT-022).

## Implementation Notes

- FR-192 and E-16 allow a new note to supersede an earlier one (`supersedes_id`), but TRD 11 offers no edit control (UX-129); do not build an edit UI. The list relies on the API default `include_superseded=false` (API-083).
- The hint "Do not enter names or other identifying details." comes from TRD 12 SEC-124; TRD 11 v0.13 UX-121 does not list it. Keep it until TRD 11 and TRD 12 are aligned (question for the algorithm lead).
- Keep the draft in component state only, never in storage (FE-089, FE-045).
- The file name keeps the v0.1 title (feature IDs and file names are never renamed, TRD 25 §4.2).
