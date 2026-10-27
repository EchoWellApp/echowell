# FEAT-031 Alarm review and snooze APIs (POST/GET /alerts/{id}/reviews, POST /alerts/{id}/snooze)

| Field | Value |
|---|---|
| Epic | Backend API |
| Build phase | Phase 5 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-030, FEAT-015 |
| Status | Complete |

## Purpose

Implement the single review model used by the Resident chart's "Review and notes" section (wireframe v0.2, SRC-21; the v0.1 Alert review page and "Mark as reviewed" dialog are retired, TRD 24 D-110): a clinician or admin records a review of a change alarm (optional explanations from the configured checklist, a required outcome, an optional note), may review the same alarm again later, can read the review history ("Previous reviews"), and can set a reminder with "Remind me in 24 hours" (snooze). A review with outcome `data_problem` also raises a data alert for the study team. Reviewing or snoozing never changes the tally, the alarm state or the resident's status in v0.1 (OQ-05).

## Business Context

- BR-11 (alarms persist until the epoch ends) and BR-13 (staff review workflow): reviews mark an alarm "Reviewed" without switching it off.
- BR-16 (audit): every review and snooze is audited; only clinicians and admins may act.
- BR-18: the alarm is a prompt to check in; the review records a human judgement, not a diagnosis.
- FRs covered (BACKLOG.md): FR-106, FR-107, FR-270, FR-271, FR-272, FR-273, FR-274, FR-275, FR-276, FR-279.

## Referenced TRDs

- TRD 05 API-081 (create review), API-082 (409/404/422, no acknowledge route), API-130 (data_problem → data alert), API-131 (list reviews), API-132 (snooze), API-128 (alert ids stable across rebuilds).
- TRD 19 §4.3 E-14, E-28, E-29; schemas `AlertReviewCreate`, `AlertReview`, `AlertReviewList`, `SnoozeRequest`, `Alert`, `ReviewOutcome`.
- TRD 09 CUS-008 (no reset), CUS-016, CUS-017 (review semantics, history), CUS-038 (checklist and outcomes), CUS-039 (snooze), CUS-040 (data_problem), CUS-042 (no SLA enforced).
- TRD 23 DME-007 (status transitions), DME-021 (immutable reviews, data alert link), DME-022 (application clock), §4.2.17, §4.2.18, §4.2.19, §4.3.2, §4.3.2a, §4.3.7.
- TRD 09 CUS-040 (title and v0.2 detail strings of `review_flagged_data_problem`, TRD 24 D-114); TRD 11 §4.17.2 (review panel, UX-310 to UX-322) and §4.18.2 (how the data alert is listed on the Study team page).
- TRD 12 §4.6 (clinician, admin), §4.12 (`alert.reviewed`, `alert.snoozed`), SEC-045 (researchers read-only).
- TRD 20 §4.6.17 (`alerts_ack_ck`, `alerts_snooze_ck`), §4.6.18 (`alert_reviews` checks), §4.6.19 (`data_alerts_subject_ck`, `data_alerts_run_ck`, `data_alerts_alert_review_uq`), PGS-042, PGS-043.
- TRD 13 TST-056..TST-059, TST-065..TST-067, AC-TST-12; TRD 05 AC-API-15; TRD 09 AC-CUS-06, AC-CUS-10.
- TRD 24 D-03, D-35 (single review model), D-37 (snooze).

## Scope

- Handlers in `backend/api/alarms.py`: `POST /api/v1/alerts/{id}/reviews` (`review_service.create`), `GET /api/v1/alerts/{id}/reviews` (`review_service.list`), `POST /api/v1/alerts/{id}/snooze` (`alert_service.snooze`).
- Validation of explanation codes against config `review_explanations` and of the outcome and note.
- Transactional write of the `alert_reviews` row, the alert status change on the first review, the create-or-link of the `review_flagged_data_problem` data alert, and the audit row.
- Snooze computation with the application clock.
- Guarantee that no `POST /api/v1/alerts/{id}/acknowledge` route exists.

## Out of Scope

- The alerts list and the `Alert` DTO builder (FEAT-030; reused here for the snooze response).
- Resolving `review_flagged_data_problem` data alerts (CLI, FEAT-032) and listing data alerts (FEAT-032).
- Alert creation, closure and natural-key upserts during rebuilds (FEAT-048, FEAT-053).
- The review form, review history and snooze button (FEAT-070, FEAT-071).
- Review deadlines or escalation (FR-276, OQ-26).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-031-FR-01 | `POST /alerts/{id}/reviews` shall be allowed for roles clinician and admin only; researchers receive 403 `FORBIDDEN`. | API-081, FR-275, SEC-045; TRD 12 §4.6 |
| FEAT-031-FR-02 | The body `AlertReviewCreate` shall be `{explanations: 0..5 unique codes, outcome ∈ {no_concern, known_cause, referred, data_problem} (required), note?: ≤ 2000 characters}` with no other properties; a missing or unknown outcome, an explanation code not in the active profile's `review_explanations`, duplicate codes, more than 5 codes, or a note over 2000 characters returns 422 `VALIDATION_ERROR` and writes nothing. | API-081, API-082, CUS-038, DME-021; FR-271 |
| FEAT-031-FR-03 | A valid review shall insert one immutable `alert_reviews` row (`alert_id`, `reviewer_user_id` from the token, `explanations`, `outcome`, `note`) and, if the alert status is `open`, set it to `acknowledged` with `acknowledged_by` and `acknowledged_at`; further reviews add rows and leave status `acknowledged`. Response 201 `AlertReview` (`reviewer` = {id, display_name}). | API-081, CUS-016, CUS-017, DME-007; FR-106, FR-270, FR-272 |
| FEAT-031-FR-04 | A review or snooze shall not change `cusum_state`, any `scores` row, the alert's `cusum_value`, `alarm_state` values or the resident's display status. | API-081, API-132, CUS-008, DME-007; FR-107; D-03 |
| FEAT-031-FR-05 | A review with outcome `data_problem` shall, in the same transaction, insert a `data_alerts` row of kind `review_flagged_data_problem` for the alert's resident with `alert_review_id` = the new review, title "<R> · review flagged a data problem", detail "a review flagged a data problem (<Mon D>, <display name>)." (facility-local date of the review; reviewer display name; D-114), `first_detected_at` = `last_detected_at` = review time, `pipeline_run_id` null; when such a data alert is already open for the resident, it shall not insert another but set that row's `alert_review_id` to the new review and refresh `detail` and `last_detected_at`. | API-130, CUS-040, DME-021; FR-273; D-114 |
| FEAT-031-FR-06 | `GET /alerts/{id}/reviews` (all user roles) shall return `AlertReviewList` newest first (`created_at` descending) with pagination and `meta`. | API-131; TRD 19 E-28; FR-272 |
| FEAT-031-FR-07 | `POST /alerts/{id}/snooze` (clinician, admin) shall accept `{hours?: integer 1..168}` (default `alert_snooze_hours` of the active profile, 24), set `alerts.snoozed_until` = application-clock now (computed in Python, never database `now()`) + hours and `snoozed_by` = caller, and return 200 with the `Alert` DTO; status and alarm state are unchanged. | API-132, CUS-039, DME-022, D-37; FR-274 |
| FEAT-031-FR-08 | Reviewing or snoozing a `closed` alert shall return 409 `ALERT_CLOSED` and write nothing; an unknown alert id returns 404 `ALERT_NOT_FOUND`; a malformed uuid returns 422. | API-082; TRD 19 E-14, E-29 |
| FEAT-031-FR-09 | No route `POST /api/v1/alerts/{id}/acknowledge` shall exist (404 or 405). | API-082, D-35; TST-066 |
| FEAT-031-FR-10 | Each saved review shall write one `audit_logs` row `alert.reviewed` (entity alert / alert id; details `{resident_code, review_id, outcome, explanation_count, previous_status}`, never the note text) and each snooze one row `alert.snoozed` (details `{resident_code, hours, snoozed_until}`), in the same transaction as the change. | FR-279; TRD 12 §4.12, SEC-100, SEC-101, SEC-104 |
| FEAT-031-FR-11 | No review deadline, escalation or role beyond clinician and admin shall be enforced. | FR-276, CUS-042, OQ-26 |
| FEAT-031-FR-12 | Reviews, status `acknowledged` and `snoozed_until` shall be stored on the alert row whose id is stable under rebuilds (natural key `(epoch_id, session_id)`), so they survive a full pipeline rebuild. | API-128, TST-067 |

## Inputs

- Path `id` (uuid); bodies `AlertReviewCreate` and `SnoozeRequest`; query `limit`, `offset`; bearer JWT.
- Tables `alerts`, `alert_reviews`, `data_alerts`, `residents`, `users`, `config_parameters` (`review_explanations`, `alert_snooze_hours`).
- Application clock (injectable; frozen with `time-machine` in tests).

## Outputs

- 201 `AlertReview`; 200 `AlertReviewList`; 200 `Alert`; Problems 403, 404, 409, 422.
- Rows in `alert_reviews`, updated `alerts` (`status`, `acknowledged_by`, `acknowledged_at`, `snoozed_until`, `snoozed_by`), inserted or updated `data_alerts`, `audit_logs`.

## Data Flow

1. Auth dependency `require_roles("clinician","admin")` (POST) or any user role (GET).
2. Review create: parse body (extra properties forbidden) → load alert (404) → reject closed (409) → validate codes against `review_explanations` of `PIPELINE_PROFILE` → in one transaction: insert `alert_reviews`; if alert `open` → update to `acknowledged` with reviewer and time; if outcome `data_problem` → create or link the `review_flagged_data_problem` data alert; write `alert.reviewed` audit → commit → 201.
3. Review list: load alert (404) → select reviews joined to `users.display_name` ordered by `created_at` desc → page.
4. Snooze: load alert (404/409) → hours = body or `alert_snooze_hours` → `snoozed_until = clock.now() + hours` → update alert, audit `alert.snoozed` → return the FEAT-030 `Alert` DTO.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-030, FEAT-015

- FEAT-030 (Alerts list and UI configuration APIs): the `Alert` DTO builder, alert loading and `review_explanations` / `alert_snooze_hours` reading.
- FEAT-015 (Audit log writer): `audit_service.record` in the same transaction.
- Transitively FEAT-021 (roles) and FEAT-012 (tables and append-only grants).
- TST-067 performs a real full rebuild and therefore runs once FEAT-053 (pipeline runner) is merged; until then this feature's guarantee is FEAT-031-FR-12 (stable ids, no review data held outside the alert's natural key).

Features that build directly on this one (BACKLOG.md §4): FEAT-038, FEAT-069.

## Database Impact

- Tables written: `alert_reviews` (INSERT only; app role has SELECT, INSERT), `alerts` (`status`, `acknowledged_by`, `acknowledged_at`, `snoozed_until`, `snoozed_by`, `updated_at`), `data_alerts` (INSERT or UPDATE of `alert_review_id`, `detail`, `last_detected_at`), `audit_logs` (INSERT).
- Tables read: `alerts`, `alert_reviews`, `users`, `residents`, `config_parameters`, `data_alerts`.
- Constraints relied on: `alerts_ack_ck`, `alerts_ack_status_ck`, `alerts_snooze_ck`, `alert_reviews_explanations_ck`, `alert_reviews_note_ck`, `data_alerts_subject_ck`, `data_alerts_run_ck`, `data_alerts_alert_review_uq`.
- Tables created or altered: none.

## API Impact

- Exposed: `POST /api/v1/alerts/{id}/reviews` (E-14, 201), `GET /api/v1/alerts/{id}/reviews` (E-28, 200), `POST /api/v1/alerts/{id}/snooze` (E-29, 200).
- Explicitly not exposed: `POST /api/v1/alerts/{id}/acknowledge`.

## Frontend Impact

None in this feature. Consumers: the review panel of the chart's "Review and notes" section (`createAlertReview`, `snoozeAlert`) and its "Previous reviews" list (`getAlertReviews`) (TRD 04), delivered by FEAT-070 and FEAT-071 as re-scoped for wireframe v0.2.

## Analytics Impact

None: reviews and snoozes are human state outside the engine; the pipeline never reads them for scoring and they never reset the tally (CUS-008, AGT-058).

## Security Requirements

- Authentication: bearer JWT; POST endpoints clinician and admin (researcher 403, API key 401); GET reviews all user roles (TRD 13 Table 4.13-A).
- Role read from the database on every request (API-013); `reviewer_user_id` and `snoozed_by` come from the token subject, never from the body.
- Note text is never written to audit details or logs (SEC-104, LOG-022); the UI hint against identifying details is SEC-124 (frontend).
- 403 responses write `access.denied` (SEC-108, via FEAT-021).

## Error Handling

| Condition | Response |
|---|---|
| Unknown alert id | 404 `ALERT_NOT_FOUND` |
| Malformed uuid | 422 `VALIDATION_ERROR` |
| Alert `closed` | 409 `ALERT_CLOSED`, nothing written |
| Missing/unknown outcome, unknown or duplicate code, > 5 codes, note > 2000, extra property, hours outside 1..168 | 422 `VALIDATION_ERROR`, nothing written |
| Audit write fails | whole transaction rolls back (LOG-090) |
| Database unavailable | 503 `SERVICE_UNAVAILABLE` |

## Logging Requirements

- Access log per request (LOG-010) and `audit_event` INFO line per audit row (LOG-092).
- Audit rows `alert.reviewed` and `alert.snoozed` with `request_id` of the request (LOG-033).
- Never log the note text or reviewer e-mail (LOG-022).

## Testing Requirements

- Integration (`tests/integration/api/test_alerts.py` and `tests/integration/test_alert_snooze.py`, marker `integration`):
  - TST-056: clinician review `{explanations: ["cold_cough_sore_throat"], outcome: "known_cause", note: "..."}` → 201, one row, status `acknowledged`, every `scores.cusum_tally`, `scores.alarm_state`, `cusum_state.current_tally` and `cusum_state.alarm_on` unchanged.
  - TST-057: second review → two rows, list newest first.
  - TST-058: each invalid body variant → 422, no row.
  - TST-059: `data_problem` → one open `review_flagged_data_problem` data alert; a second `data_problem` review on the same resident links the existing open row (no second row).
  - TST-065: snooze with frozen clock → `snoozed_until` = now + 24 h exactly; `{hours: 4}` → now + 4 h; after advancing the clock 24 h + 1 s `snoozed_until` < now; status unchanged.
  - TST-066: `POST /alerts/{id}/acknowledge` → 404 or 405.
  - 409 on a closed alert; 404 on unknown id; researcher 403; audit rows for review and snooze (TST-053).
  - TST-067: after a review and a snooze, a full rebuild keeps the alert id, reviews, `acknowledged` and `snoozed_until` (executes once FEAT-053 is merged).
- Contract: TST-061 for every response; auth cells via TST-130 (FEAT-039).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-031-AC-01 | A clinician review with outcome `known_cause` returns 201, creates exactly one `alert_reviews` row, sets the alert to `acknowledged` with `acknowledged_by` = the clinician, and leaves every `scores` row and the `cusum_state` row byte-identical (with DS-07: R09 `current_tally` stays 26.830256 ±1e-6). | TST-056, AC-API-15 (first part), AC-CUS-06 |
| FEAT-031-AC-02 | A second review on the same alert creates a second row and `GET /alerts/{id}/reviews` returns both, newest first. | TST-057 |
| FEAT-031-AC-03 | Each of: no outcome, outcome `fine`, explanation `headache`, note of 2001 characters returns 422 and creates no row. | TST-058, FR-271 |
| FEAT-031-AC-04 | A `data_problem` review creates one `data_alerts` row with kind `review_flagged_data_problem`, the alert's resident, `alert_review_id` = the review id, title "<R> · review flagged a data problem" and status `open`; a second `data_problem` review for the same resident leaves exactly one open row of that kind, now linked to the newer review. | TST-059, FR-273 |
| FEAT-031-AC-05 | With the clock frozen at T, `POST /alerts/{id}/snooze` without body stores and returns `snoozed_until` = T + 24 h and `snoozed_by` = caller; with `{"hours": 4}` it is T + 4 h; `status` is unchanged. | TST-065, AC-CUS-10 |
| FEAT-031-AC-06 | `POST /api/v1/alerts/{id}/acknowledge` returns 404 or 405. | TST-066 |
| FEAT-031-AC-07 | Reviewing or snoozing a `closed` alert returns 409 `ALERT_CLOSED`; an unknown id returns 404 `ALERT_NOT_FOUND`; a researcher POST returns 403. Verified by: Integration (`tests/integration/api/test_alerts.py`; TST-066). | API-082, FR-275 |
| FEAT-031-AC-08 | One `audit_logs` row `alert.reviewed` per saved review and one `alert.snoozed` per snooze exist, and no audit `details` value contains the note text. | FR-279, TST-053, SEC-104 |
| FEAT-031-AC-09 | After a review and a snooze, a full rebuild (`POST /pipeline/run {scope: "all"}`) keeps the alert id, its `alert_reviews` rows, status `acknowledged` and `snoozed_until`. | TST-067, AC-API-15 (rebuild part) |

## Definition of Done

- All FEAT-031 acceptance criteria pass.
- Three endpoints implemented; no acknowledge route; all writes transactional with audit rows.
- TST-056..TST-059, TST-065, TST-066 pass in Phase 5; TST-067 passes in the Phase 6 checkpoint PR of Block 3 that delivers FEAT-053 (AC-TST-12).
- Requirement markers (TST-013); coverage ≥ 85 %; OpenAPI drift check passes.

## Implementation Notes

- Inject the clock (a `now()` provider dependency) so `time-machine` controls it; never use `func.now()` or a database default for `snoozed_until` (DME-022).
- Validate explanation codes against the configured list on each request (no caching across requests), so a `set-config` change applies at once (D-56 operational key).
- The display name in the data-alert detail comes from `users.display_name` of the reviewer; format the date as "<Mon D>" of the review time in `facilities.timezone`.
- Do the create-or-link with `SELECT ... FOR UPDATE` on the open `review_flagged_data_problem` row of the resident to avoid two concurrent reviews inserting two rows.
- The detail of a linked (existing) data alert is refreshed with the new review's date and reviewer; the title stays the same.
- Saving a review never touches `cusum_state` or `scores`; write a regression test that snapshots both tables before and after (AGT-058).
