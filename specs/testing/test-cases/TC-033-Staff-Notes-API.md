# Staff notes API (GET/POST /residents/{code}/notes)

## Feature Description

Clinicians and admins write free-text staff notes about a resident with `POST /api/v1/residents/{resident_code}/notes` (TRD 19 E-16): a `note_type` (`observation`, `action_taken`, `follow_up`), a body of 1–2,000 characters after trimming, optionally linked to one of the resident's alarms (`alert_id`) or superseding an earlier note of the same resident (`supersedes_id`). Every user role reads the notes newest first with `GET /api/v1/residents/{resident_code}/notes` (E-15), which hides superseded notes unless `include_superseded=true`. Notes are append-only, never change an alert's status, acknowledgement or snooze, and their body is never written to audit details or logs. Source: FEAT-033; TRD 05 API-083..API-085; TRD 06 DB-010; TRD 12 SEC-104, SEC-113, SEC-124; TRD 24 D-83.

## Preconditions

1. Local Docker Compose stack running; environment file from `.env.development.example`.
2. **DS-07 state:** `docker compose exec backend python -m backend.cli seed test_v0_1` (no staff notes; open alerts R09 and R10).
3. `API=http://localhost:8000/api/v1`; tokens `ADMIN`, `CLIN`, `RES` from `POST $API/auth/login` with the `SEED_*` passwords; `KEY` = the ingest API key from the environment file.
4. `R09_ALERT`, `R10_ALERT` = `id` values from `GET $API/alerts?resident_code=R09` / `R10`.
5. `psql` access with the app login (`echowell_app_login`); local development stack for the `pytest` cases.
6. Restore afterwards with `docker compose exec backend python -m backend.cli seed test_v0_1 --reset`.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-033-01 | Clinician observation note for R09: 201, one row, one `note.created` audit row without body | High | Positive |
| TC-033-02 | Body of only spaces and body of 2001 characters return 422 and create no row | High | Negative |
| TC-033-03 | `alert_id` of R10's alert posted to R09 returns 422 `ALERT_RESIDENT_MISMATCH` | High | Negative |
| TC-033-04 | Supersede flow: B supersedes A; default list shows B only; `include_superseded=true` shows B then A | High | Positive |
| TC-033-05 | Note linked to an open alert leaves it `open` with `acknowledged_at` null | High | Positive |
| TC-033-06 | Role access: researcher POST 403; API key GET 401; every user role GET 200 | High | Security |
| TC-033-07 | Each note type accepted; admin can post | Medium | Positive |
| TC-033-08 | Unknown resident 404; unknown `alert_id` 404; foreign or unknown `supersedes_id` 422 | Medium | Negative |
| TC-033-09 | Superseding an already superseded note returns 422 on `supersedes_id` | Medium | Negative |
| TC-033-10 | Unknown `note_type` and extra property return 422 | Medium | Negative |
| TC-033-11 | Append-only: app role cannot UPDATE or DELETE `staff_notes` | Medium | Database |
| TC-033-12 | Note body never in logs; response schema and `meta` | Medium | Security |

### TC-033-01 Clinician observation note for R09: 201, one row, one `note.created` audit row without body

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s -i -X POST $API/residents/R09/notes -H "Authorization: Bearer $CLIN" -H "Content-Type: application/json" -d '{"note_type": "observation", "body": "Resident has a cold; nurse notified."}'` | HTTP 201; body `id`, `resident_code` "R09", `alert_id` null, `author` `{"id": <clinician id>, "display_name": "Clinician"}`, `note_type` "observation", `body` as sent, `supersedes_id` null, `created_at` UTC with Z |
| 2 | `SELECT note_type, body, author_user_id, marked_reviewed, alert_id, supersedes_id FROM staff_notes;` | 1 row: observation, the body, clinician id, `marked_reviewed` false, NULL, NULL |
| 3 | `SELECT actor_type, entity_type, details FROM audit_logs WHERE action='note.created';` | 1 row: `actor_type` user; `details` = `{resident_code: "R09", note_type: "observation", alert_id: null, supersedes_id: null}`; no `body` key |
| 4 | `SELECT count(*) FROM audit_logs WHERE details::text LIKE '%nurse notified%';` | 0 |

### TC-033-02 Body of only spaces and body of 2001 characters return 422 and create no row

| Step | Action | Expected Result |
|---|---|---|
| 1 | Note `SELECT count(*) FROM staff_notes;` | Count noted |
| 2 | POST to R09 as clinician `{"note_type": "observation", "body": "   "}` | HTTP 422 `VALIDATION_ERROR` |
| 3 | POST `{"note_type": "observation", "body": "<2001 × the letter a>"}` | HTTP 422 `VALIDATION_ERROR` |
| 4 | POST `{"note_type": "observation", "body": "<2000 × the letter a>"}` | HTTP 201 (boundary accepted) |
| 5 | Re-read the count | Increased by exactly 1 (only step 4) |

### TC-033-03 `alert_id` of R10's alert posted to R09 returns 422 `ALERT_RESIDENT_MISMATCH`

| Step | Action | Expected Result |
|---|---|---|
| 1 | POST to R09 as clinician `{"note_type": "follow_up", "body": "Check tomorrow.", "alert_id": "$R10_ALERT"}` | HTTP 422; `type` "urn:echowell:error:ALERT_RESIDENT_MISMATCH"; `title` "Alert belongs to another resident" |
| 2 | `SELECT count(*) FROM staff_notes WHERE alert_id='$R10_ALERT';` | 0 |

### TC-033-04 Supersede flow: B supersedes A; default list shows B only; `include_superseded=true` shows B then A

| Step | Action | Expected Result |
|---|---|---|
| 1 | POST note A to R09 as clinician `{"note_type": "observation", "body": "First version."}`; note its `id` (A) | HTTP 201 |
| 2 | POST note B to R09 `{"note_type": "observation", "body": "Corrected version.", "supersedes_id": "<A>"}`; note `id` (B) | HTTP 201; `supersedes_id` = A |
| 3 | `GET $API/residents/R09/notes` as researcher | `items` contains B and not A; B has `supersedes_id` A (the client shows it as edited) |
| 4 | `GET $API/residents/R09/notes?include_superseded=true` | `items[0].id` = B, `items[1].id` = A (newest first) |
| 5 | `SELECT count(*) FROM staff_notes WHERE id IN ('<A>','<B>');` and `SELECT body FROM staff_notes WHERE id='<A>';` | 2 rows; A's body still "First version." (not edited in place) |

### TC-033-05 Note linked to an open alert leaves it `open` with `acknowledged_at` null

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT status, acknowledged_at, snoozed_until FROM alerts WHERE id='$R09_ALERT';` | `open`, NULL, NULL |
| 2 | POST to R09 as clinician `{"note_type": "action_taken", "body": "Nurse informed.", "alert_id": "$R09_ALERT"}` | HTTP 201; `alert_id` = R09_ALERT |
| 3 | Repeat the query of step 1 | Still `open`, NULL, NULL |
| 4 | `GET $API/alerts?resident_code=R09` | `reviewed` false; `review_count` 0 |

### TC-033-06 Role access: researcher POST 403; API key GET 401; every user role GET 200

| Step | Action | Expected Result |
|---|---|---|
| 1 | POST a valid note to R09 as researcher | HTTP 403 `FORBIDDEN`; no `staff_notes` row; an `access.denied` audit row |
| 2 | `GET $API/residents/R09/notes -H "X-API-Key: $KEY"` | HTTP 401 `NOT_AUTHENTICATED` |
| 3 | POST with `X-API-Key: $KEY` | HTTP 401 |
| 4 | `GET $API/residents/R09/notes` with each of `$ADMIN`, `$CLIN`, `$RES` | 200 each |

### TC-033-07 Each note type accepted; admin can post

| Step | Action | Expected Result |
|---|---|---|
| 1 | POST to R10 as admin with `note_type` "observation", then "action_taken", then "follow_up" (body "QA note") | 201 each; `author.display_name` "Admin" |
| 2 | `GET $API/residents/R10/notes` | `total` 3; order follow_up, action_taken, observation (newest first) |
| 3 | `SELECT count(*) FROM audit_logs WHERE action='note.created' AND details->>'resident_code'='R10';` | 3 |

### TC-033-08 Unknown resident 404; unknown `alert_id` 404; foreign or unknown `supersedes_id` 422

| Step | Action | Expected Result |
|---|---|---|
| 1 | POST a valid note to `$API/residents/R11/notes` as clinician | HTTP 404 `RESIDENT_NOT_FOUND` |
| 2 | `GET $API/residents/R11/notes` | HTTP 404 `RESIDENT_NOT_FOUND` |
| 3 | POST to R09 with `alert_id` "00000000-0000-4000-8000-000000000000" | HTTP 404 `ALERT_NOT_FOUND` |
| 4 | Create a note on R10 (id C); POST to R09 with `supersedes_id` C | HTTP 422 `VALIDATION_ERROR`; `errors[]` names `supersedes_id` |
| 5 | POST to R09 with `supersedes_id` "00000000-0000-4000-8000-000000000000" | HTTP 422 `VALIDATION_ERROR` |

### TC-033-09 Superseding an already superseded note returns 422 on `supersedes_id`

| Step | Action | Expected Result |
|---|---|---|
| 1 | After TC-033-04 (A superseded by B), POST to R09 `{"note_type": "observation", "body": "Third.", "supersedes_id": "<A>"}` | HTTP 422 `VALIDATION_ERROR`; `errors[0].field` "supersedes_id"; detail "This note has already been superseded." |
| 2 | POST with `supersedes_id` B | HTTP 201 (latest version can be superseded) |

### TC-033-10 Unknown `note_type` and extra property return 422

| Step | Action | Expected Result |
|---|---|---|
| 1 | POST `{"note_type": "diary", "body": "x"}` to R09 | HTTP 422 `VALIDATION_ERROR` |
| 2 | POST `{"note_type": "observation", "body": "x", "marked_reviewed": true}` | HTTP 422 `VALIDATION_ERROR` (no such request field) |
| 3 | POST `{"body": "x"}` | HTTP 422 `VALIDATION_ERROR` |

### TC-033-11 Append-only: app role cannot UPDATE or DELETE `staff_notes`

| Step | Action | Expected Result |
|---|---|---|
| 1 | As `echowell_app_login`: `UPDATE staff_notes SET body='changed' WHERE id='<A>';` | ERROR: permission denied for table staff_notes (SQLSTATE 42501) |
| 2 | As `echowell_app_login`: `DELETE FROM staff_notes WHERE id='<A>';` | ERROR: permission denied (42501) |
| 3 | `curl -s $API/openapi.json \| jq '.paths["/api/v1/residents/{resident_code}/notes"] \| keys'` | ["get", "post"] only (no PUT, PATCH or DELETE) |

### TC-033-12 Note body never in logs; response schema and `meta`

| Step | Action | Expected Result |
|---|---|---|
| 1 | After TC-033-01: `docker compose logs backend --since 10m \| grep -c "nurse notified"` | 0 |
| 2 | Validate `GET $API/residents/R09/notes` against `StaffNoteList` | Valid; `meta` with seven fields; `items`, `total`, `limit`, `offset` |
| 3 | Validate the 201 body of TC-033-01 against `StaffNote` | Valid; no `meta` (single object) |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `POST /residents/{code}/notes` | 201 `StaffNote`; 403 researcher; 404 `RESIDENT_NOT_FOUND` / `ALERT_NOT_FOUND`; 422 `VALIDATION_ERROR` / `ALERT_RESIDENT_MISMATCH` |
| 2 | `GET /residents/{code}/notes` | 200 `StaffNoteList` newest first; superseded notes hidden unless `include_superseded=true`; 404 unknown resident |
| 3 | Body rules | `note_type` enum; `body` 1..2000 after trimming; optional `alert_id`, `supersedes_id`; no other properties |
| 4 | Author | `author` from the token, never from the body |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `staff_notes` after a valid POST | One new row; `author_user_id` = caller; `marked_reviewed` false; body stored as received |
| 2 | Supersede | New row with `supersedes_id`; old row unchanged; `staff_notes_supersedes_uq` allows one successor |
| 3 | `audit_logs` | One `note.created` per note with `{resident_code, note_type, alert_id, supersedes_id}`; no body |
| 4 | `alerts` | Unchanged by any note |
| 5 | Grants | App role: SELECT, INSERT only on `staff_notes` |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Blank body / 2001 characters | 422 |
| 2 | Alert of another resident | 422 `ALERT_RESIDENT_MISMATCH` |
| 3 | Unknown alert | 404 `ALERT_NOT_FOUND` |
| 4 | Foreign, unknown or already superseded `supersedes_id` | 422 `VALIDATION_ERROR` |
| 5 | Unknown resident | 404 `RESIDENT_NOT_FOUND` |
| 6 | Researcher POST / API key | 403 / 401 |
| 7 | `docker compose stop db`, then POST a note | 503 `SERVICE_UNAVAILABLE`; no row after `docker compose start db` |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-033-AC-01 | Clinician observation note for R09: 201 with `author.display_name` of the clinician; one `staff_notes` row; one `note.created` row without `body` | TC-033-01 |
| FEAT-033-AC-02 | Spaces-only body and 2001-character body each 422, no row | TC-033-02 |
| FEAT-033-AC-03 | `alert_id` of R10's alert posted to R09 gives 422 `ALERT_RESIDENT_MISMATCH` | TC-033-03 |
| FEAT-033-AC-04 | After B supersedes A: list shows B not A; `include_superseded=true` shows B then A | TC-033-04 |
| FEAT-033-AC-05 | Note with `alert_id` of an `open` alert leaves it `open` with `acknowledged_at` null | TC-033-05 |
| FEAT-033-AC-06 | Researcher POST 403; API key GET 401; every user role GET 200 | TC-033-06 |

## Test Data Requirements

- DS-07 (`seed test_v0_1`): residents R09, R10 with open alerts; no staff notes.
- Synthetic note texts ("Resident has a cold; nurse notified.", "First version.", "Corrected version.", "QA note") with no personal details.
- Unknown resident R11; unknown id `00000000-0000-4000-8000-000000000000`.
- Environment: `SEED_*` passwords and `SEED_INGEST_API_KEY` from the environment file; `psql` app login.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-033-FR-01 (API-084; FR-190) | FEAT-033 | TC-033-06, TC-033-08 |
| FEAT-033-FR-02 (API-084; FR-190) | FEAT-033 | TC-033-02, TC-033-07, TC-033-10 |
| FEAT-033-FR-03 (API-085) | FEAT-033 | TC-033-03, TC-033-08, TC-033-09 |
| FEAT-033-FR-04 (API-084; SEC-104) | FEAT-033 | TC-033-01 |
| FEAT-033-FR-05 (FR-192, DB-010, SEC-113) | FEAT-033 | TC-033-04, TC-033-11 |
| FEAT-033-FR-06 (FR-191) | FEAT-033 | TC-033-05 |
| FEAT-033-FR-07 (API-083, DB-010; FR-193) | FEAT-033 | TC-033-04, TC-033-06 |
| TST-053 / AC-SEC-09 | FEAT-033 | TC-033-01 |
| TST-041 | FEAT-033 | TC-033-11 |
| PGS-036 | FEAT-033 | TC-033-02 |
| SEC-124, LOG-022 | FEAT-033 | TC-033-02, TC-033-12 |
| D-83 | FEAT-033 | TC-033-09 |
