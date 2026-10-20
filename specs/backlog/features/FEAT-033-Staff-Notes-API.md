# FEAT-033 Staff notes API (GET/POST /residents/{code}/notes)

| Field | Value |
|---|---|
| Epic | Backend API |
| Build phase | Phase 5 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-021, FEAT-015 |
| Status | Not Started |

## Purpose

Let clinicians and admins write free-text staff notes about a resident (observation, action taken, follow-up), optionally linked to one of the resident's alarms, and let every user role read them newest first on the Resident detail "Staff review" section. Notes are append-only: an edit is a new note that supersedes the old one. Notes are a separate feature from alarm reviews and never change alert status.

## Business Context

- BR-13 (staff review on Resident detail): notes with type, author and time, newest first, only the latest version of edited notes.
- BR-16 (traceability, no PII): append-only storage, audited creation, body never logged or audited, UI hint against identifying details.
- FRs covered (BACKLOG.md): FR-190, FR-192, FR-193.

## Referenced TRDs

- TRD 05 API-083 (list), API-084 (create), API-085 (alert and supersedes checks), API-100, API-057.
- TRD 19 §4.3 E-15, E-16; schemas `StaffNoteCreate`, `StaffNote`, `StaffNoteList`, `NoteType`.
- TRD 06 DB-010 (corrections as new rows; show only non-superseded notes).
- TRD 12 SEC-113 (append-only for `echowell_app`), SEC-124 (note hint, 2000 characters), §4.6 (POST clinician, admin), §4.12 (`note.created`).
- TRD 20 §4.6.20 (`staff_notes`, `staff_notes_body_ck`, `staff_notes_supersedes_uq`, `staff_notes_not_self_ck`), PGS-036.
- TRD 23 §4.2.20.
- TRD 13 TST-053 (audit for note created), TST-041 (no UPDATE/DELETE as app role); TRD 12 AC-SEC-09.

## Scope

- Handlers in `backend/api/residents.py`: `GET /api/v1/residents/{resident_code}/notes` (`note_service.list`) and `POST /api/v1/residents/{resident_code}/notes` (`note_service.create`).
- Validation of note type, body length after trimming, `alert_id` ownership and `supersedes_id` ownership.
- `note.created` audit row in the same transaction.

## Out of Scope

- Alarm reviews and "Mark as reviewed" (FEAT-031); notes never acknowledge an alert.
- The Staff review UI, note form and hint text (FEAT-071).
- Editing in place or deleting notes (not allowed; corrections are new rows).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-033-FR-01 | `POST /residents/{resident_code}/notes` shall be allowed for roles clinician and admin; researchers receive 403 and an unknown resident 404 `RESIDENT_NOT_FOUND`. | API-084; TRD 12 §4.6; FR-190 |
| FEAT-033-FR-02 | The body `StaffNoteCreate` shall be `{note_type ∈ {observation, action_taken, follow_up}, body (1..2000 characters after trimming), alert_id?, supersedes_id?}` with no other properties; violations return 422 `VALIDATION_ERROR`. | API-084; TRD 19 E-16; FR-190 |
| FEAT-033-FR-03 | A note `alert_id` shall reference an alert of the same resident (else 422 `ALERT_RESIDENT_MISMATCH`; an unknown alert id returns 404 `ALERT_NOT_FOUND`); a `supersedes_id` shall reference a note of the same resident (else 422 `VALIDATION_ERROR`). | API-085; TRD 19 E-16 |
| FEAT-033-FR-04 | A valid note shall insert one new `staff_notes` row with `author_user_id` from the token and `marked_reviewed` = false, write audit `note.created` (details `{resident_code, note_type, alert_id, supersedes_id}`, never the body) in the same transaction, and return 201 `StaffNote` (`author` = {id, display_name}). | API-084; TRD 12 §4.12, SEC-104 |
| FEAT-033-FR-05 | Notes shall be append-only: an edit is a new row whose `supersedes_id` points to the corrected note; no UPDATE or DELETE of `staff_notes` exists in the application. | FR-192, DB-010, SEC-113 |
| FEAT-033-FR-06 | Creating a note shall never change any alert's status, acknowledgement or snooze. | API-084; FR-191 (statement on notes) |
| FEAT-033-FR-07 | `GET /residents/{resident_code}/notes` (all user roles) shall return `StaffNoteList` newest first (`created_at` descending) with pagination and `meta`, excluding notes that another note supersedes unless `include_superseded=true`; an unknown resident returns 404. | API-083, DB-010; TRD 19 E-15; FR-193 |

## Inputs

- Path `resident_code`; query `include_superseded` (boolean, default false), `limit`, `offset`; body `StaffNoteCreate`; bearer JWT.
- Tables `residents`, `alerts`, `staff_notes`, `users`.

## Outputs

- 201 `StaffNote`; 200 `StaffNoteList`; Problems 403, 404, 422.
- `staff_notes` row, `audit_logs` row.

## Data Flow

1. Auth: POST requires clinician or admin; GET any user role.
2. Create: load resident (404) → validate body → if `alert_id`: load alert (404 `ALERT_NOT_FOUND`) and compare resident (422 `ALERT_RESIDENT_MISMATCH`) → if `supersedes_id`: load note and compare resident (422) → insert row and audit in one transaction → 201.
3. List: load resident (404) → select notes of the resident, excluding ids that appear as `supersedes_id` of another note unless `include_superseded` → join `users.display_name` → order by `created_at` desc → page.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-021, FEAT-015

- FEAT-021 (Role-based authorization matrix): POST clinician/admin, GET all roles.
- FEAT-015 (Audit log writer): `note.created`.
- Transitively FEAT-012 (`staff_notes` table with append-only grants).

## Database Impact

- Tables written: `staff_notes` (INSERT only; app role SELECT, INSERT), `audit_logs` (INSERT).
- Tables read: `residents`, `alerts` (`id`, `resident_id`), `staff_notes`, `users` (`display_name`).
- Constraints relied on: `staff_notes_body_ck`, `staff_notes_supersedes_uq`, `staff_notes_not_self_ck`.
- Tables created or altered: none.

## API Impact

- Exposed: `GET /api/v1/residents/{resident_code}/notes` (E-15), `POST /api/v1/residents/{resident_code}/notes` (E-16).

## Frontend Impact

None in this feature. Consumers: `NotesList` (`getNotes(code)`) and `StaffReviewForm` (`createNote(code, body)`) on Resident detail (TRD 04 §4.6.2), delivered by FEAT-071, which also shows the SEC-124 hint.

## Analytics Impact

None: notes are human state; the pipeline never reads them and rebuilds never delete them (ANL-036).

## Security Requirements

- POST: clinician and admin only (researcher 403, API key 401); GET: all user roles (TRD 13 Table 4.13-A).
- `author_user_id` from the authenticated user only.
- Note body never written to logs or audit details (LOG-022, SEC-104); notes limited to 2000 characters (SEC-124).
- Append-only enforced by grants (SEC-113); the app role cannot UPDATE or DELETE `staff_notes` (TST-041).

## Error Handling

| Condition | Response |
|---|---|
| Unknown resident | 404 `RESIDENT_NOT_FOUND` |
| Unknown `alert_id` | 404 `ALERT_NOT_FOUND` |
| `alert_id` of another resident | 422 `ALERT_RESIDENT_MISMATCH` |
| `supersedes_id` of another resident or unknown | 422 `VALIDATION_ERROR` |
| Empty body after trimming, > 2000 characters, unknown `note_type`, extra property | 422 `VALIDATION_ERROR` |
| Researcher POST | 403 `FORBIDDEN` |

## Logging Requirements

- Access log per request (LOG-010); `audit_event` INFO line for `note.created` (LOG-092); never the note body (LOG-022, LOG-023 redacts keys named `body`/`note`).

## Testing Requirements

- Integration (`tests/integration/api/test_notes.py`, marker `integration`): create each note type → 201 and audit row (TST-053); body "   " → 422; 2001 characters → 422; alert of another resident → 422 `ALERT_RESIDENT_MISMATCH`; unknown alert → 404; supersede flow: create A, create B with `supersedes_id` A → list returns B only, `include_superseded=true` returns both; researcher POST → 403; alert status unchanged after a note with `alert_id`; schema validation (TST-061).
- DB grant test TST-041 (app role cannot UPDATE/DELETE `staff_notes`) is owned by FEAT-012 and must stay green.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-033-AC-01 | A clinician POST `{note_type: "observation", body: "Resident has a cold; nurse notified."}` for R09 returns 201 with `author.display_name` of the clinician and creates one `staff_notes` row and one `audit_logs` row `note.created` whose details contain no `body`. | API-084, TST-053, AC-SEC-09 |
| FEAT-033-AC-02 | A body of only spaces and a body of 2001 characters each return 422 and create no row. | API-084, PGS-036 |
| FEAT-033-AC-03 | A note with `alert_id` of R10's alert posted to R09 returns 422 `ALERT_RESIDENT_MISMATCH`. | API-085 |
| FEAT-033-AC-04 | After note B supersedes note A, `GET /residents/R09/notes` returns B and not A; with `include_superseded=true` it returns B then A (newest first). | API-083, DB-010, FR-192, FR-193 |
| FEAT-033-AC-05 | Creating a note with `alert_id` of an `open` alert leaves the alert `open` with `acknowledged_at` null. | API-084 |
| FEAT-033-AC-06 | A researcher POST returns 403; an API key on GET returns 401; every user role GET returns 200. | TRD 13 Table 4.13-A |

## Definition of Done

- Both endpoints implemented with TRD 19 schemas; append-only behaviour verified.
- Integration tests pass; requirement markers (TST-013); coverage ≥ 85 %; OpenAPI drift check passes.
- The supersede-twice gap below is reported in the batch report (AGT-009, AGT-022).

## Implementation Notes

- Trim only for the length check; store the body as received (TRD 20 check uses `btrim` for the minimum and raw length for the maximum).
- The "edited" marker of DB-010 is derivable by the client from `supersedes_id` being non-null on the shown note; TRD 19 `StaffNote` has no separate flag, so do not add one (OAS-004).
- Resolved (TRD 24 D-83, TRD 05 API-085): a `supersedes_id` that names a note already superseded returns 422 `VALIDATION_ERROR` with field `supersedes_id`; a concurrent insert rejected by `staff_notes_supersedes_uq` is mapped to the same 422, never an unhandled database error.
- `marked_reviewed` is always written false; the request has no such field (TRD 12 §8).
