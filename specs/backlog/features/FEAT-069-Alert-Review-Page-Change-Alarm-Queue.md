# FEAT-069 Alert review page: change-alarm queue, data-alert queue and review panel

| Field | Value |
|---|---|
| Epic | Frontend |
| Build phase | Phase 8 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-064, FEAT-030, FEAT-032, FEAT-067, FEAT-048 |
| Status | Not Started |

## Purpose

Implement `/alerts` (SRC-18), the page where the charge nurse or clinical lead reviews change alarms and the study team sees data-quality alerts: the header and subline, a two-column layout (queues left, review panel right; stacked on narrow screens), Queue 1 "Change alarms · need a nurse review" with cards in the FR-261 group order and their review badges, the selected alarm kept in the URL, the review panel title and link, the mini tally chart reusing `CusumChart`, "Leaning most", Queue 2 "Data alerts · go to the study team" without alarm styling or review form, the empty states and the page footer. The review form, history and snooze are added by FEAT-070.

## Business Context

- BR-11, BR-13 (alarms are reviewed by staff; persistence and context visible), BR-12 (data problems routed to the study team).
- VIS-028 (Alert review page in the MVP), VIS-029 (data alerts are never presented as health alarms).
- BR-15: the page renders the SRC-18 reference values.
- FRs covered (BACKLOG.md): FR-260, FR-261, FR-262, FR-263, FR-264, FR-265, FR-266, FR-278, FR-280, FR-298.

## Referenced TRDs

- TRD 04 FE-139 (`?alert=` selection, default first card, empty panel), FE-193 (E2E `alerts.spec.ts`), FE-205 (snooze regrouping with fake timers), FE-036, §4.8 `AlertsPage`, `AlertQueue`, `AlertCard`, `DataAlertQueue`, `AlertReviewPanel`, `MiniTallyChart`, `LeaningMost`.
- TRD 11 UX-300..UX-309 (queues, card texts, badges, selection, empty texts, data-alert cards, order, links), UX-310 (panel title and link), UX-311 (mini chart), UX-312 (Leaning most), UX-319 (panel empty texts), UX-323, UX-324 (accessibility), UX-330, UX-331 (reference rendering), UX-246 (stacking), §4.17.2 data-alert wording, §4.17.6.
- TRD 09 CUS-037 (one card per non-closed alarm of a current epoch); TRD 00 VIS-028, VIS-029.
- TRD 19 E-13 `GET /api/v1/alerts`, E-30 `GET /api/v1/data-alerts`, E-12 `GET /api/v1/scores`.
- TRD 02 FR-260..FR-266, FR-278, FR-280, FR-298.
- TRD 13 E2E-17, TST-090; TRD 14 TDV-067, TDV-068, TDV-069.

## Scope

- `app/(protected)/alerts/page.tsx` (`AlertsPage`) with `AppHeader` (title "Alert review", active "alerts"), two-column grid (left 5fr, right 7fr, gap 24px), footer variant `alerts`.
- `AlertQueue`, `AlertCard`, `DataAlertQueue`, `AlertReviewPanel` frame with title row, link, `MiniTallyChart` (90px variant of `CusumChart`) and `LeaningMost`.
- Queries: `getAlerts({ status: "open" })` and `getAlerts({ status: "acknowledged" })` for the alarms of Queue 1 (TRD 02 UC-13), `getDataAlerts({ status: "open" })`, `getScores({ residentCode, epoch })` for the selected alarm.
- URL state `?alert=<id>`; live-region announcement on selection.

## Out of Scope

- `AlertReviewForm`, "Save review", "Remind me in 24 h", `ReviewHistory`, open-questions note, researcher read-only replacement (FEAT-070).
- Backend alert list, `leaning_most`, data alerts (FEAT-030, FEAT-048, FEAT-032).
- Chart rules themselves (FEAT-067 `CusumChart`).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-069-FR-01 | `/alerts` shall show the header "Alert review", the subline "For the charge nurse or clinical lead · <data_source_label> as of <Mon D, YYYY>", and a two-column layout with the queues on the left and the review panel for the selected alarm on the right, stacking (queues first) on narrow screens. | FR-260, UX-017, UX-246 |
| FEAT-069-FR-02 | Queue 1 headed "Change alarms · need a nurse review" shall contain one card per change alarm that is on in a resident's current epoch (status `open` or `acknowledged`), ordered (1) not reviewed and not snoozed, (2) not reviewed and snoozed (`snoozed_until` after now), (3) reviewed; within each group alarm date ascending, then resident code; closed alerts are not listed. | FR-261, UX-300, UX-301, CUS-037 |
| FEAT-069-FR-03 | Each card shall show line 1 "<R> · <D>" (600) with the review badge right-aligned and line 2 "Alarm since <Mon D> · open <d> days · tally <x.x>" ("open 1 day" for 1, "opened today" for 0), d = `open_days`, tally = `current_tally` with one decimal. | FR-262, UX-302 |
| FEAT-069-FR-04 | The badge shall read "Not reviewed" (accent, 600) for `open` without an active reminder; "Not reviewed · reminder <Mon D, h:mm AM/PM>" (secondary, 400) while `snoozed_until` is in the future; "Reviewed" (secondary) for `acknowledged`; when `snoozed_until` passes, the card returns to group 1 with the emphasis without a new API call. | UX-303, FR-261, FE-205 |
| FEAT-069-FR-05 | Each card shall be a full-card button (min-height 44px) that selects the alarm and sets `?alert=<id>`; the selected card has a 2px ink left border and `aria-current="true"`; with no valid `?alert` the first card is selected. Selecting does not move focus; the panel is an `aria-live="polite"` region announcing "Reviewing <R>, alarm since <Mon D>." | FE-139, UX-304, UX-323, FR-264 |
| FEAT-069-FR-06 | With no change alarms, Queue 1 shall show its empty text and the panel shall show its empty state (see Implementation Notes for the wording conflict). | UX-305, UX-319, FR-280 |
| FEAT-069-FR-07 | The review panel shall start with the heading "<R> · alarm since <Mon D>" (h2) and the link "Open full resident view →" to `/residents/<R>`. | UX-310, FR-264 |
| FEAT-069-FR-08 | Under the label "Change tally since watching began (alarm line <h>)" the panel shall show `MiniTallyChart` (plot height 90px) with the same rules as the Resident detail chart: grey baseline slot "Baseline <Mon D>–<Mon D>", one bar per scored session of the current epoch, #BDBDB8 with #8A8A85 outline while `off`, #9A4508 when `rings`/`on`, dashed accent line at h, x labels for first and last scored dates, accessible name in the UX-091 form. | UX-311, FR-265, D-30 |
| FEAT-069-FR-09 | "Leaning most" shall list up to 3 labels from the alert's `leaning_most` keys as lower-cased plain-language labels without the technical name, joined by ", " (R09 "more pauses, quieter, less voiced sound"); with none, "No single measurement stands out." | UX-312, FR-266 |
| FEAT-069-FR-10 | Queue 2 headed "Data alerts · go to the study team" shall list one card per open data alert with line 1 the API `title` and line 2 the API `detail`, ordered by kind (baseline_stalled, possible_other_speaker, high_set_aside, device_silent, review_flagged_data_problem) then code, without "▲", accent colour or any review form. | UX-306, UX-307, FR-298, VIS-029 |
| FEAT-069-FR-11 | A resident data-alert card shall link to `/residents/<R>` and a device card to `/residents#devices`, with the title as accessible name; with none, "No data alerts in the last 30 days." | UX-308, UX-309 |
| FEAT-069-FR-12 | The page footer shall read "An alarm is a prompt to check in, not a diagnosis. No audio is stored or played here." | FR-278, UX-005 |
| FEAT-069-FR-13 | Checkbox and radio rows in the panel shall each be at least 44px high (applies to the form added by FEAT-070 inside this panel). | UX-324 |
| FEAT-069-FR-14 | With the reference data the page shall render exactly TRD 11 §4.17.6: nav "Alerts (2)"; R09 · D09 "Not reviewed" "Alarm since Oct 21 · open 9 days · tally 26.8"; R10 · D10 "Not reviewed" "Alarm since Oct 24 · open 6 days · tally 13.4"; the four data alerts in order; R09 panel with 14 bars and "more pauses, quieter, less voiced sound"; R10 panel "more pauses, slower while talking, fewer syllables per second". | UX-330, UX-331, FR-263 |

## Inputs

- `GET /api/v1/alerts?status=open` and `?status=acknowledged` (`AlertList` with `open_days`, `current_tally`, `snoozed_until`, `reviewed`, `leaning_most`), `GET /api/v1/data-alerts?status=open`, `GET /api/v1/scores?resident_code=<R>&epoch=<n>` for the selected alarm; `meta` for formatting; `?alert=` URL parameter; the client clock (for the snooze comparison).

## Outputs

- Rendered `/alerts` page with queues, panel frame, mini chart, Leaning most, empty states and footer.

## Data Flow

`["alerts", {status: "open"}]`, `["alerts", {status: "acknowledged"}]` and `["data-alerts", {status: "open"}]` queries → client groups and orders alarm cards per FR-261 using `reviewed`/`status`, `snoozed_until` vs now, `local_date`, `resident_code` → selected id from `?alert` → `["resident", code, "scores", epoch]` → `AlertReviewPanel` (title, link, `MiniTallyChart`, `LeaningMost`; form slot for FEAT-070).

## Dependencies

Required before implementation (BACKLOG.md): FEAT-064, FEAT-030, FEAT-032, FEAT-067, FEAT-048

- FEAT-064: header, nav, route shell; FEAT-030: `GET /alerts`; FEAT-032: `GET /data-alerts`; FEAT-067: `CusumChart` reused by `MiniTallyChart`; FEAT-048: `leaning_most` values.

## Database Impact

None (frontend only).

## API Impact

Endpoints consumed: `GET /api/v1/alerts` (E-13), `GET /api/v1/data-alerts` (E-30), `GET /api/v1/scores` (E-12). None exposed.

## Frontend Impact

- Page: `app/(protected)/alerts/page.tsx`.
- Components: `AlertsPage`, `AlertQueue`, `AlertCard`, `DataAlertQueue`, `AlertReviewPanel`, `MiniTallyChart`, `LeaningMost`, `Footer` (alerts).

## Analytics Impact

None. "Leaning most" keys come from the API (FEAT-048); the UI only maps keys to labels.

## Security Requirements

- All roles may view (`GET /alerts`, `GET /data-alerts`: admin, clinician, researcher); review controls are gated in FEAT-070 (SEC-043).
- Data alerts never styled as health alarms (VIS-029).

## Error Handling

- Each queue and the panel have independent loading/empty/error states (LOG-083, UX-202).
- Unknown `?alert` id → first card selected (FE-139).
- Scores query error → error state inside the panel chart area only.

## Logging Requirements

None in the frontend.

## Testing Requirements

- Component (TST-090): `AlertCard` (texts, badges incl. reminder form), `AlertQueue` (FR-261 grouping and order; FE-205 with `vi.useFakeTimers()` — snoozed card moves back to "Not reviewed" when time passes `snoozed_until`, no API call), `DataAlertQueue` (four cards, no "▲", links), `AlertReviewPanel` (title, link, mini chart bars, Leaning most texts and empty text).
- Page test (`frontend/tests/pages/alerts.test.tsx`): loading, populated, empty (no alarms), error, 401 → login (TST-094).
- E2E: E2E-17 (queues on DS-07), `alerts.spec.ts` read-only part of FE-193 (cards, data alerts, R09 default selection, Leaning most).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-069-AC-01 | As clinician on DS-07, `/alerts` shows nav "Alerts (2)" and the cards "R09 · D09" "Not reviewed" "Alarm since Oct 21 · open 9 days · tally 26.8" then "R10 · D10" "Not reviewed" "Alarm since Oct 24 · open 6 days · tally 13.4". | E2E-17; FR-263; TDV-067 |
| FEAT-069-AC-02 | Queue 2 shows exactly the four data alerts of TRD 11 §4.17.6 in order (R08, R05, R03, D02 titles and details) with no "▲" and no form. | E2E-17; UX-331; TDV-068 |
| FEAT-069-AC-03 | Without `?alert`, R09 is selected; the panel shows "R09 · alarm since Oct 21", "Open full resident view →" linking to `/residents/R09`, a mini chart with "Baseline Oct 1–16" and 14 bars (Oct 17–20 grey, Oct 21–30 accent), and "Leaning most" "more pauses, quieter, less voiced sound". | FE-193; UX-330; TDV-069 |
| FEAT-069-AC-04 | Selecting R10 sets `?alert=<R10 id>`, does not move focus, announces "Reviewing R10, alarm since Oct 24." and shows "more pauses, slower while talking, fewer syllables per second". | UX-304; UX-323; UX-330 |
| FEAT-069-AC-05 | With fake timers, an open alert whose `snoozed_until` is 1 minute after now is in the snoozed group without the "Not reviewed" emphasis, and after advancing past `snoozed_until` it re-enters the "Not reviewed" group with no new API call. | FE-205; UX-303 |
| FEAT-069-AC-06 | The page footer reads "An alarm is a prompt to check in, not a diagnosis. No audio is stored or played here." | FR-278; UX-005 |
| FEAT-069-AC-07 | With an empty alert list, Queue 1 shows its empty text and the panel shows its empty state, and no review form is rendered. | UX-305; UX-319; FR-280 |

## Definition of Done

- All FEAT-069 acceptance criteria pass; component, page and E2E (read-only) tests green.
- Alert review shows R09 and R10 and the four data alerts with test data (TRD 25 Phase 8 DoD).
- Batch report lists IDs and the TRD conflicts below (AGT-022).

## Implementation Notes

- Columns stack below 1024px (UX-246, the TRD 04 FE-165 tablet breakpoint); TRD 02 FR-260 was aligned in the PR #2 consistency fixes.
- With no open alarm, Queue 1 reads "No change alarms right now." (UX-305) and the panel "No change alarms to review." (UX-319, FE-139); TRD 02 FR-280 was aligned in the PR #2 consistency fixes.
- FR-266 writes the empty Leaning-most text without a final period, UX-312 with one ("No single measurement stands out."); use the UX-312 string from `lib/wording.ts`.
- The queue order is defined once in FR-261; compute the snoozed group client-side from `snoozed_until` vs the current time, because the API exposes only `snoozed_until` (TST-065 note).
- Lower-case the TRD 11 §4.5.4 labels for Leaning most ("Quieter" → "quieter").
- E-13 accepts a single `status` value; as TRD 02 UC-13 describes, call `getAlerts({ status: "open" })` and `getAlerts({ status: "acknowledged" })` (the open call also feeds the nav count, FE-036) and merge them for Queue 1.
