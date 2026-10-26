# FEAT-069 Alarm review panel in the resident chart (review form, reminder, previous reviews)

| Field | Value |
|---|---|
| Epic | Frontend |
| Build phase | Phase 8 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-066, FEAT-030, FEAT-031 |
| Status | Not Started |

## Purpose

Let clinicians and admins review a change alarm where wireframe v0.2 puts it (SRC-21, TRD 24 D-110): in the "Review and notes" section of a Changed resident's chart (`/residents/[residentCode]/review`), above the staff notes. The panel "Review alert: changed since <Mon D>" holds the explanation checklist "Anything that could explain it?" read from `GET /config/ui` (provisional, OQ-25), the required choice "What did you find?", an optional note (≤ 2000 characters), "Save review" and "Remind me in <h> hours" with query invalidation, the "Previous reviews" list (kept from v0.1, D-111), the open-questions note (OQ-05, OQ-26) and the read-only text for researchers. A saved review marks the alarm "Reviewed" but never changes the alarm state, change score or pill (OQ-05). The v0.1 Alert review page (`/alerts`, its change-alarm queue, selection in `?alert=`, mini chart and data-alert queue) and the v0.1 "Mark as reviewed" dialog are retired: the queue is replaced by the resident list (Changed first, FEAT-065) and the nav badge (FEAT-064), the mini chart by Voice trends (FEAT-067), "Leaning most" moves to the Summary (FEAT-066) and the data alerts to the Study team page (FEAT-072).

## Business Context

- BR-13 (staff record what they checked and decided, from the resident's own chart), BR-11 (an alarm stays on after review in v0.1, OQ-05), BR-16 (only clinicians and admins review; audited server-side).
- One review model (contract §20 R5): the review form is the only way to mark an alarm reviewed; notes never do.
- OQ-25 (provisional explanation checklist), OQ-26 (who may review and how soon); D-108, D-110, D-111, D-113 ("Review outcome" becomes "What did you find?").
- FRs covered (BACKLOG.md): FR-191, FR-194, FR-264, FR-267, FR-268, FR-269, FR-270, FR-271, FR-272, FR-274, FR-277, FR-280.

## Referenced TRDs

- TRD 11 (v0.13) — owned by this feature: UX-310 (panel only for a Changed resident, heading), UX-313..UX-318 (checklist and hint, "What did you find?", note, "Save review" and its validation, "Remind me in <h> hours" and the reminder line, post-save state), UX-320 (Previous reviews), UX-321 (open-questions note), UX-322 (researcher replacement), §4.17.3 wording rules, UX-324 (44px label rows), UX-330 and §4.17.5 (reference rendering and badges after a review). Retired, not built: UX-300..UX-305 (queue), UX-311 (mini chart), UX-319 (empty panel), UX-323 (card selection), UX-125 (moved to UX-321), UX-136..UX-138 (review dialog).
- TRD 04 (v0.11) FE-209 (review panel for `ResidentDetail.open_alert_id` on `/review`, only for a Changed resident), FE-086 (invalidations after review and reminder), FE-134 (UI never changes alarm state), FE-135 (role gating), FE-136..FE-138 (form contents from `getUiConfig`, request body, reminder call), FE-079 (field errors), FE-205 (reminder line with fake timers), FE-187 (E2E-09 review step), FE-193 (E2E `review.spec.ts`), §4.9, §4.8 `AlarmReviewPanel`, `AlertReviewForm`, `ReviewHistory`. Retired: FE-131, FE-139.
- TRD 19 E-13 `GET /api/v1/alerts`, E-14 `POST /api/v1/alerts/{id}/reviews`, E-28 `GET /api/v1/alerts/{id}/reviews`, E-29 `POST /api/v1/alerts/{id}/snooze`, E-32 `GET /api/v1/config/ui`.
- TRD 02 FR-191, FR-194, FR-264, FR-267..FR-272, FR-274, FR-277, FR-280; TRD 24 D-03, D-35, D-37, D-110, D-111, D-113, OQ-05, OQ-25, OQ-26.
- TRD 13 E2E-09 (review step), E2E-18, E2E-21, TST-090, TST-111; TRD 14 TDV-076.

## Scope

- `app/(protected)/residents/[residentCode]/review/page.tsx` (shared with FEAT-071): `AlarmReviewPanel` first, only when the resident's display status is Changed; `StaffNotes` (FEAT-071) after it.
- `AlarmReviewPanel` (`{ alarm, reviews, uiConfig, canReview, meta }`) for the alert whose id is `ResidentDetail.open_alert_id`, with `AlertReviewForm` (`{ alertId, snoozeHours, explanations, snoozedUntil, onSaved }`) and `ReviewHistory` (`{ reviews, tz }`) from `GET /alerts/{id}/reviews`; open-questions note; researcher replacement text.
- Mutations `createAlertReview`, `snoozeAlert` with TanStack Query invalidations, so that the Summary review status, the list's "What's happening" text and both badges update from the API.
- `@mutating` E2E steps E2E-18 and the FE-193 reminder step in `frontend/tests/e2e/mutating.spec.ts` (order per D-73), and the review step of E2E-09.

## Out of Scope

- Backend review, review-list, snooze and config endpoints (FEAT-031, FEAT-030).
- Staff notes (FEAT-071); the Summary facts and "Leaning most" (FEAT-066); the change score chart (FEAT-067); data problems (FEAT-072).
- Any reset of the change score or switching the alarm off (OQ-05; not in pipeline v0.1).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-069-FR-01 | When the resident is Changed, the "Review and notes" section shall start with a panel headed "Review alert: changed since <alarm Mon D>" (h2) that reviews the non-closed alert of the current epoch; for other residents no review panel is rendered (only the staff notes, FEAT-071). | UX-310, FE-209, FR-264, FR-280 |
| FEAT-069-FR-02 | A fieldset with legend "Anything that could explain it?" (weight 700, 1px `--rule` border, radius 6px, padding 12px 14px) shall list one checkbox per `review_explanations` entry of `GET /api/v1/config/ui`, in the returned order (test configuration: "Cold, cough or sore throat", "Dental problem or dentures out", "New or changed medication", "Poor sleep or unusual day", "Room or device moved"), with the hint (13px, `--muted`) "Provisional list — to be confirmed with the clinical team (OQ-25)."; any number may be checked. | UX-313, FE-136, FR-267, OQ-25 |
| FEAT-069-FR-03 | A fieldset with legend "What did you find?" shall offer exactly one required radio among "Checked on resident, no concern" (`no_concern`), "Explained by a known cause" (`known_cause`), "Referred to nurse or provider" (`referred`), "Looks like a data problem: send to study team" (`data_problem`), none preselected. | UX-314, FE-136, FR-268, D-113 |
| FEAT-069-FR-04 | A textarea labelled "Note" (3 rows, optional, ≤ 2000 characters, counter "<count> / 2000", placeholder "What you saw or did") shall follow. | UX-315, FR-269 |
| FEAT-069-FR-05 | The primary button "Save review" without a choice under "What did you find?" shall not call the API, shall show "Choose what you found." linked to that fieldset and move focus to the first radio; otherwise it sends `POST /api/v1/alerts/{id}/reviews` with `{ explanations: string[] (codes), outcome, note? }`, omitting an empty or whitespace-only note. | UX-316, FE-137, FR-270 |
| FEAT-069-FR-06 | After success the form shall reset, announce politely "Review saved." (outcome `data_problem`: "Review saved and sent to the study team as a data problem."), and invalidate `["alerts"]`, `["data-alerts"]`, `["resident", code]`, `["residents"]` and `["analytics"]`, so that the Summary review status and the list's "What's happening" text read "Reviewed" and the nav and section badges decrease, as returned by the API. | UX-318, FE-086, FR-270 |
| FEAT-069-FR-07 | The UI shall not change the alarm state, change score, chart or pill after a save or a reminder; it renders only the API state after refetch (no reset, OQ-05). | UX-318, FE-134, OQ-05 |
| FEAT-069-FR-08 | 422 responses shall show field errors under the matching control (`explanations`, `outcome`, `note`) and other errors above the buttons; 409 `ALERT_CLOSED` shows the API error message above the buttons; entered values are kept on failure. | FE-079, FR-271, UX-207 |
| FEAT-069-FR-09 | The secondary button "Remind me in <h> hours" (h = `alert_snooze_hours`, 24) shall call `POST /api/v1/alerts/{id}/snooze` with `{}`, create no review, change no alarm state, announce "Reminder set for <Mon D, h:mm AM/PM>. The alarm stays on." and invalidate the queries of FE-086; while `snoozed_until` is in the future the panel shows the line "Reminder set for <Mon D, h:mm AM/PM>." under the buttons. | UX-317, FE-138, FR-274 |
| FEAT-069-FR-10 | Under the buttons, "Previous reviews" (h3) shall list the alarm's reviews newest first as "<Mon D, h:mm AM/PM> · <display name> · <outcome label>", then "Possible explanations: <labels joined by ', '>" when any and the note text; with none, "Not reviewed yet."; several reviews per alarm are allowed. | UX-320, FR-272, D-111 |
| FEAT-069-FR-11 | The panel shall end with the note (13px, `--muted`) "Open questions (OQ-05, OQ-26): Does a saved review reset the change score or turn the alarm off? Who may review? How soon must an alarm be reviewed? Pipeline v0.1 keeps alarms on." | UX-321, FR-277 |
| FEAT-069-FR-12 | For role researcher (`canReviewAlarms` false) the checklist, choices, note and both buttons shall be replaced by "Only clinicians and admins can review alarms."; "Previous reviews" stays visible. | UX-322, FE-135, FR-194, SEC-043 |
| FEAT-069-FR-13 | Explanation and outcome labels shall be shown exactly as listed; labels for codes outside the current configured list use the API-supplied labels. | TRD 11 §4.17.3 |
| FEAT-069-FR-14 | Checkbox and radio controls shall each have a 44px-high clickable label row; every control is keyboard-operable with visible focus. | UX-324, TST-111 |
| FEAT-069-FR-15 | With the reference data the panels shall render TRD 11 §4.17.5 (R09 "Review alert: changed since Oct 21", R10 "… since Oct 24", five checkboxes, four choices, "Save review", "Remind me in 24 hours", "Previous reviews": "Not reviewed yet."; no panel for other residents), and after a review of R09 the nav badge reads "1", R09's section badge is gone and R09's pill still reads "Changed". | UX-330, AC-UX-11 |

## Inputs

- `GET /api/v1/config/ui` → `UiConfig {meta, alert_snooze_hours, review_explanations[{code, label}]}`.
- The resident's non-closed alert from FEAT-066's `["alerts", {residentCode}]` query (`id`, `local_date`, `status`, `snoozed_until`); `GET /api/v1/alerts/{id}/reviews` → `AlertReviewList`.
- User input (checkboxes, choice, note); role from `useAuth()`.

## Outputs

- `POST /alerts/{id}/reviews` and `POST /alerts/{id}/snooze` requests; refreshed queries; live-region messages; rendered review history and reminder line.

## Data Flow

Layout queries (FEAT-066) → display status Changed? → `getUiConfig()` (`["config", "ui"]`) → checklist and reminder hours → user submits → `createAlertReview` → success → reset + announce + invalidate (alerts, data-alerts, resident, residents, analytics) → Summary, list text and badges re-render from the API → `getAlertReviews(id)` shows the new entry. "Remind me" → `snoozeAlert(id, {})` → invalidate → reminder line from the returned `snoozed_until`.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-066, FEAT-030, FEAT-031

- FEAT-066 provides the chart layout, the `/review` route shell, the resident's alert query and the section badge.
- FEAT-030 provides `GET /alerts` and `GET /config/ui`; FEAT-031 provides the review, review-list and snooze endpoints.

Features that build directly on this one (BACKLOG.md §4): FEAT-075.

## Database Impact

None directly. The backend writes `alert_reviews`, updates `alerts.status`/`snoozed_until`/`snoozed_by`, may create a `review_flagged_data_problem` data alert, and writes audit rows `alert.reviewed` / `alert.snoozed` (FEAT-031).

## API Impact

Endpoints consumed: `GET /api/v1/config/ui` (E-32), `POST /api/v1/alerts/{id}/reviews` (E-14), `GET /api/v1/alerts/{id}/reviews` (E-28), `POST /api/v1/alerts/{id}/snooze` (E-29); `GET /api/v1/alerts` (E-13) through FEAT-066. None exposed. There is no `/alerts/{id}/acknowledge` call and no `/alerts` page.

## Frontend Impact

- Section page `app/(protected)/residents/[residentCode]/review/page.tsx` (review panel part).
- Components: `AlarmReviewPanel`, `AlertReviewForm`, `ReviewHistory`; wording in `lib/wording.ts`.

## Analytics Impact

None. The UI never recomputes the change score or alarm state (OQ-05).

## Security Requirements

- Review and reminder controls only for admin and clinician (`canReviewAlarms`); the backend returns 403 for researchers (FR-275); the UI shows the read-only text (UX-322, SEC-043).
- The note is plain text sent as typed and rendered as text (SEC-076).

## Error Handling

- Missing choice → client-side error, no request (UX-316).
- 422 → field errors; 409 `ALERT_CLOSED` → message above the buttons; 403 → "You do not have access to this information." (FE-035); network error → message with "Reference:" (FEAT-062).
- Config query error → error state inside the panel; "Previous reviews" still shown when its query succeeds (UX-202).

## Logging Requirements

None in the frontend. Audit rows `alert.reviewed` and `alert.snoozed` are written by the backend (TRD 12 §4.12, FR-279).

## Testing Requirements

- Component (`components/AlertReviewForm/AlertReviewForm.test.tsx`, TST-090): checklist from config order with the OQ-25 hint, required choice error "Choose what you found." and focus, request body without empty note, both success messages, reminder call `{}`, message and reminder line, researcher replacement, 422 field mapping; `ReviewHistory` formatting and "Not reviewed yet."; no panel for a non-Changed resident.
- Component (FE-205, fake timers): `AlarmReviewPanel` with `snoozed_until` 1 minute after now shows the reminder line and "Not reviewed"; after the timers pass `snoozed_until` the line is gone without a new API call.
- E2E read-only (`review.spec.ts`, FE-193): the R09 and R10 panels of §4.17.5 and "Choose what you found.".
- Keyboard test: checkboxes, radios, "Save review", "Remind me in 24 hours" reachable and operable with visible focus (TST-111, part of FEAT-075's suite).
- E2E (`@mutating`, `mutating.spec.ts`, D-73 order): E2E-18 (1st: on `/residents/R09/review` save without a choice → "Choose what you found."; then "Checked on resident, no concern" → "Review saved.", R09 Summary "Reviewed", list text "Changed from their usual since Oct 21. Reviewed.", nav badge "1", R09 section badge gone, pill "▲ Changed", change score 26.8 unchanged); E2E-09 review step (2nd: "Cold, cough or sore throat" + "Explained by a known cause" → both reviews in "Previous reviews"); FE-193 reminder step (3rd: "Remind me in 24 hours" on R10 → reminder line).
- E2E-21 researcher part: form replaced by "Only clinicians and admins can review alarms."; a direct `POST /alerts/{id}/reviews` returns 403.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-069-AC-01 | `/residents/R09/review` shows "Review alert: changed since Oct 21", five explanation checkboxes in the configured order with the OQ-25 hint, the four choices of "What did you find?", "Save review", "Remind me in 24 hours", "Previous reviews" "Not reviewed yet." and the open-questions note; `/residents/R01/review` shows no review panel. | UX-330; §4.17.5; UX-310; AC-UX-11 |
| FEAT-069-AC-02 | Clicking "Save review" without a choice shows "Choose what you found.", moves focus to the first radio and sends no request. | E2E-18; UX-316 |
| FEAT-069-AC-03 | Saving R09 with "Checked on resident, no concern" announces "Review saved.", the nav badge reads "1", R09's "Review and notes" badge is gone, R09's Summary shows "Reviewed", the list reads "Changed from their usual since Oct 21. Reviewed.", and the pill still reads "Changed" with change score 26.8. | E2E-18; TDV-076; UX-318; AC-UX-06 |
| FEAT-069-AC-04 | The request body contains the checked codes (e.g. `["cold_cough_sore_throat"]`) and the chosen `outcome`, and omits a whitespace-only note; with outcome `data_problem` the message reads "Review saved and sent to the study team as a data problem." Verified by: Component (`AlertReviewForm.test.tsx`; TST-090). | FE-137; UX-318 |
| FEAT-069-AC-05 | "Remind me in 24 hours" on R10 sends `POST /api/v1/alerts/{id}/snooze` with `{}`, creates no review, announces "Reminder set for <Mon D, h:mm AM/PM>. The alarm stays on." and shows "Reminder set for <Mon D, h:mm AM/PM>." under the buttons; R10's pill stays "Changed". | FE-193; FE-138; UX-317 |
| FEAT-069-AC-06 | As researcher on `/residents/R09/review`, the form is replaced by "Only clinicians and admins can review alarms." while "Previous reviews" remains; a direct review POST returns 403. | E2E-21; UX-322 |
| FEAT-069-AC-07 | After two reviews on the same alarm, "Previous reviews" lists both newest first with time, reviewer and outcome label, and "Possible explanations: Cold, cough or sore throat" for the one that had a checked explanation. | E2E-09; UX-320; FR-272 |

## Definition of Done

- All FEAT-069 acceptance criteria pass; component tests and the `@mutating` E2E steps pass in Chromium.
- OQ-05 note present (TRD 25 Phase 8 DoD).
- Batch report lists IDs (AGT-022).

## Implementation Notes

- The `@mutating` scenarios run after all read-only ones on a freshly re-seeded database in the D-73 order E2E-18 → E2E-09/FE-187 → FE-193 reminder step; do not add other writes to read-only specs.
- Use `UiConfig.alert_snooze_hours` only for the button label; send `{}` so the server default applies (FE-138). Show the reminder time from the API's `snoozed_until` in `meta.facility_tz`.
- The v0.1 queue grouping by reminder state (FE-205) has no place in v0.2; the reminder is shown only as the line under the buttons.
- Branch on `ApiError.code` (`ALERT_CLOSED`, `VALIDATION_ERROR`), never on message text (FE-079).
- The file name keeps the v0.1 title (feature IDs and file names are never renamed, TRD 25 §4.2).
