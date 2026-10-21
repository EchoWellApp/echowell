# FEAT-070 Alarm review form, review history and snooze

| Field | Value |
|---|---|
| Epic | Frontend |
| Build phase | Phase 8 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-069, FEAT-031 |
| Status | Not Started |

## Purpose

Let clinicians and admins review a change alarm on `/alerts`: `AlertReviewForm` with the explanation checklist read from `GET /config/ui`, the required outcome radio group, an optional note (≤ 2000 characters), "Save review" and "Remind me in 24 h" with query invalidation, the "Previous reviews" history newest first, the open-questions note, and the read-only replacement text for researchers. A saved review marks the alarm "Reviewed" but never changes the alarm state or tally in the UI (OQ-05). The same form is reused in the Resident detail review dialog (FEAT-071).

## Business Context

- BR-13 (staff record what they checked and decided), BR-11 (an alarm stays on after review in v0.1, OQ-05), BR-16 (only clinicians and admins review; audited server-side).
- SRC-18 review panel; OQ-25 (provisional explanation checklist), OQ-26 (who may review).
- FRs covered (BACKLOG.md): FR-267, FR-268, FR-269, FR-270, FR-271, FR-272, FR-274, FR-277.

## Referenced TRDs

- TRD 04 FE-086 (invalidations after review/snooze), FE-136 (form contents, `getUiConfig`), FE-137 (request body, empty note omitted), FE-138 (snooze call, no review), FE-134 (UI never changes alarm state), FE-135 (role gating), FE-079 (field errors), FE-193 (E2E), §4.8 `AlertReviewForm`, `ReviewHistory`, `AlertReviewPanel`.
- TRD 11 UX-310..UX-322 (panel structure, checklist, outcome radios, note, Save review, Remind me, post-save state, empty panel, Previous reviews, open-questions note, researcher replacement), §4.17.4 wording rules.
- TRD 19 E-14 `POST /api/v1/alerts/{id}/reviews`, E-28 `GET /api/v1/alerts/{id}/reviews`, E-29 `POST /api/v1/alerts/{id}/snooze`, E-32 `GET /api/v1/config/ui`.
- TRD 02 FR-267..FR-272, FR-274, FR-277; TRD 24 OQ-05, OQ-25, OQ-26.
- TRD 13 E2E-18, E2E-21, TST-090, TST-111; TRD 14 TDV-076.

## Scope

- `AlertReviewForm` (`{ alertId, snoozeHours, explanations, onSaved }`) inside `AlertReviewPanel` on `/alerts`.
- `ReviewHistory` (`{ reviews, tz }`) from `GET /alerts/{id}/reviews`.
- Open-questions note at the end of the panel; researcher read-only replacement.
- Mutations `createAlertReview`, `snoozeAlert` with TanStack Query invalidations.
- `@mutating` E2E steps E2E-18 and the FE-193 snooze step in `frontend/tests/e2e/mutating.spec.ts` (order per D-73).

## Out of Scope

- Backend review, snooze and config endpoints (FEAT-031, FEAT-030).
- The Resident detail "Mark as reviewed" dialog wrapper `ReviewDialog` (FEAT-071, reuses this form).
- Queue layout and panel frame (FEAT-069).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-070-FR-01 | A fieldset with legend "Anything that could explain it?" shall list one checkbox per `review_explanations` entry of `GET /api/v1/config/ui`, in the returned order, with the hint "Provisional list — to be confirmed with the clinical team (OQ-25)."; any number may be checked. | FE-136, UX-313, FR-267, OQ-25 |
| FEAT-070-FR-02 | A fieldset "Review outcome" shall offer exactly one required radio among "Checked on resident, no concern" (`no_concern`), "Explained by a known cause" (`known_cause`), "Referred to nurse or provider" (`referred`), "Looks like a data problem: send to study team" (`data_problem`), none preselected. | FE-136, UX-314, FR-268 |
| FEAT-070-FR-03 | A textarea "Note" (3 rows, optional, ≤ 2000 characters, counter "<count> / 2000", placeholder "What you saw or did") shall follow. | FE-136, UX-315, FR-269 |
| FEAT-070-FR-04 | "Save review" without an outcome shall not call the API, shall show "Choose a review outcome." linked to the outcome fieldset and move focus to the first radio. | FE-136, UX-316 |
| FEAT-070-FR-05 | "Save review" shall send `POST /api/v1/alerts/{id}/reviews` with `{ explanations: string[] (codes), outcome, note? }`, omitting an empty or whitespace-only note. | FE-137, FR-270, E-14 |
| FEAT-070-FR-06 | After success the form shall reset, announce "Review saved." (outcome `data_problem`: "Review saved and sent to the study team as a data alert.") politely, and invalidate `["alerts"]`, `["data-alerts"]`, `["resident", code]`, `["residents"]` and `["analytics"]`; the card then shows "Reviewed" as returned by the API. | UX-318, FE-086, FR-270 |
| FEAT-070-FR-07 | The UI shall not change the alarm state, badge, tally or chart after a save; it renders only the API state after refetch. | FE-134, UX-318, OQ-05 |
| FEAT-070-FR-08 | 422 responses shall show field errors under the matching control (`explanations`, `outcome`, `note`) and other errors above the button; 409 `ALERT_CLOSED` shall show the API error message above the button. | FE-079, FR-271, UX-207 |
| FEAT-070-FR-09 | "Remind me in <alert_snooze_hours> h" (secondary style) shall call `POST /api/v1/alerts/{id}/snooze` with `{}`, create no review, change no alarm state, announce "Reminder set for <Mon D, h:mm AM/PM>. The alarm stays on." and invalidate the queries of FE-086. | FE-138, UX-317, FR-274, E-29 |
| FEAT-070-FR-10 | Under the buttons, "Previous reviews" (h3) shall list the alarm's reviews newest first as "<Mon D, h:mm AM/PM> · <display name> · <outcome label>", then "Possible explanations: <labels joined by ', '>" when any and the note text; with none, "Not reviewed yet."; several reviews per alarm are allowed. | UX-320, FR-272, E-28 |
| FEAT-070-FR-11 | The panel shall end with "Open questions (OQ-05, OQ-26): Does a saved review reset the tally or turn the alarm off? Who may review? How soon must an alarm be reviewed? Pipeline v0.1 keeps alarms on." | UX-321, FR-277 |
| FEAT-070-FR-12 | For role researcher the checklist, outcome, note and both buttons shall be replaced by "Only clinicians and admins can review alarms."; chart, Leaning most and Previous reviews stay visible; `canReviewAlarms(role)` gates every review and snooze control. | UX-322, FE-135, SEC-043 |
| FEAT-070-FR-13 | Explanation and outcome labels shall be shown exactly as listed; labels for codes outside the current configured list use the API-supplied labels. | TRD 11 §4.17.4 |
| FEAT-070-FR-14 | Every control shall be keyboard-operable with visible focus and 44px-high label rows. | TST-111, UX-324 |

## Inputs

- `GET /api/v1/config/ui` → `UiConfig {meta, alert_snooze_hours, review_explanations[{code, label}]}`.
- Selected `ChangeAlarm` (from FEAT-069); `GET /api/v1/alerts/{id}/reviews` → `AlertReviewList`.
- User input (checkboxes, outcome, note); role from `useAuth()`.

## Outputs

- `POST /alerts/{id}/reviews` and `POST /alerts/{id}/snooze` requests; refreshed queries; live-region messages; rendered review history.

## Data Flow

`getUiConfig()` (`["config", "ui"]`) → checklist and snooze hours → user submits → `createAlertReview` → success → reset + announce + invalidate (alerts, data-alerts, resident, residents, analytics) → FEAT-069 queue/badge re-render from API → `getAlertReviews(id)` shows the new entry. "Remind me" → `snoozeAlert(id, {})` → invalidate → card moves to the snoozed group (FEAT-069).

## Dependencies

Required before implementation (BACKLOG.md): FEAT-069, FEAT-031

- FEAT-069 provides the `/alerts` page, queue and panel frame into which the form is placed.
- FEAT-031 provides the review, review-list and snooze endpoints.

Features that build directly on this one (BACKLOG.md §4): FEAT-071, FEAT-075.

## Database Impact

None directly. The backend writes `alert_reviews`, updates `alerts.status`/`snoozed_until`/`snoozed_by`, may create a `review_flagged_data_problem` data alert, and writes audit rows `alert.reviewed` / `alert.snoozed` (FEAT-031).

## API Impact

Endpoints consumed: `GET /api/v1/config/ui` (E-32), `POST /api/v1/alerts/{id}/reviews` (E-14), `GET /api/v1/alerts/{id}/reviews` (E-28), `POST /api/v1/alerts/{id}/snooze` (E-29). None exposed. There is no `/alerts/{id}/acknowledge` call.

## Frontend Impact

- Components: `AlertReviewForm`, `ReviewHistory` (inside `AlertReviewPanel` on `app/(protected)/alerts/page.tsx`); wording in `lib/wording.ts`.

## Analytics Impact

None. The UI never recomputes the tally or alarm state (OQ-05).

## Security Requirements

- Review and snooze controls only for admin and clinician (`canReviewAlarms`); the backend returns 403 for researchers (FR-275); the UI shows the read-only text (UX-322, SEC-043).
- The note is plain text sent as typed and rendered as text (SEC-076); no identifying details should be entered (staff guidance; SEC-124 applies to the note form of FEAT-071).

## Error Handling

- Missing outcome → client-side error, no request (UX-316).
- 422 → field errors; 409 `ALERT_CLOSED` → message above the button; 403 → "You do not have access to this information." (FE-035); network error → message with "Reference:" (FEAT-062).
- On failure the form keeps the entered values.

## Logging Requirements

None in the frontend. Audit rows `alert.reviewed` and `alert.snoozed` are written by the backend (TRD 12 §4.12, FR-279).

## Testing Requirements

- Component (`components/AlertReviewForm/AlertReviewForm.test.tsx`, TST-090): checklist from config order, required outcome error and focus, body without empty note, success message variants, snooze call `{}` and message, researcher replacement, 422 field mapping; `ReviewHistory` formatting and empty text.
- Keyboard test: explanation checkboxes, outcome radios, "Save review", "Remind me in 24 h" reachable and operable with visible focus (TST-111, part of FEAT-075's suite).
- E2E (`@mutating`, `mutating.spec.ts`, D-73 order): E2E-18 (1st: save without outcome → validation; then "Checked on resident, no concern" → R09 "Reviewed", nav "Alerts (1)", tally 26.8 unchanged, footer text); FE-193 snooze step (3rd: "Remind me in 24 h" on R10 → snoozed badge form).
- E2E-21 researcher part: form replaced by "Only clinicians and admins can review alarms."; direct `POST /alerts/{id}/reviews` returns 403.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-070-AC-01 | Clicking "Save review" without an outcome shows "Choose a review outcome.", moves focus to the first radio and sends no request. | E2E-18; UX-316 |
| FEAT-070-AC-02 | Saving R09 with "Checked on resident, no concern" announces "Review saved.", the R09 card shows "Reviewed", the nav shows "Alerts (1)", and the tally still reads 26.8. | E2E-18; TDV-076; AC-UX-11 |
| FEAT-070-AC-03 | The checklist shows the five labels in the `GET /config/ui` order with the OQ-25 hint, and the request body contains the checked codes (e.g. `["cold_cough_sore_throat"]`). Verified by: Component (`components/AlertReviewForm/AlertReviewForm.test.tsx`; TST-090). | FE-136; FE-137; UX-313 |
| FEAT-070-AC-04 | "Remind me in 24 h" on R10 sends `POST /api/v1/alerts/{id}/snooze` with `{}`, creates no review, and the R10 badge changes to "Not reviewed · reminder <Mon D, h:mm AM/PM>". | FE-193; FE-138; UX-303 |
| FEAT-070-AC-05 | As researcher on `/alerts`, the form is replaced by "Only clinicians and admins can review alarms." while chart, Leaning most and Previous reviews remain; a direct review POST returns 403. | E2E-21; UX-322 |
| FEAT-070-AC-06 | After two reviews on the same alarm, "Previous reviews" lists both newest first with time, reviewer and outcome label. Verified by: Component (`components/AlertReviewForm/AlertReviewForm.test.tsx`; TST-090). | UX-320; FR-272 |
| FEAT-070-AC-07 | The panel ends with the UX-321 open-questions note. Verified by: Inspection (the inspection method of FR-277, applied to the condition stated in the criterion). | UX-321; FR-277 |

## Definition of Done

- All FEAT-070 acceptance criteria pass; component tests and the `@mutating` E2E group steps pass in Chromium.
- OQ-05 note present (TRD 25 Phase 8 DoD).
- Batch report lists IDs (AGT-022).

## Implementation Notes

- The `@mutating` scenarios run after all read-only ones on a freshly re-seeded database in the D-73 order E2E-18 → E2E-09/FE-187 → FE-193 snooze step; do not add other writes to read-only specs.
- Use `snoozeHours` from `UiConfig.alert_snooze_hours` only for the button label; send `{}` so the server default applies (FE-138).
- Show the reminder time from the API's returned `snoozed_until` formatted in `meta.facility_tz`.
- Branch on `ApiError.code` (`ALERT_CLOSED`, `VALIDATION_ERROR`), never on message text (FE-079).
