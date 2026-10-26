# FEAT-066 Resident chart frame and Summary (back link, banner, section navigation, Right now, Leaning most, More detail)

| Field | Value |
|---|---|
| Epic | Frontend |
| Build phase | Phase 8 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-064, FEAT-028, FEAT-029, FEAT-048 |
| Status | Not Started |

## Purpose

Implement the frame of the resident chart `/residents/[residentCode]` as wireframe v0.2 draws it (SRC-21, TRD 24 D-110) and its first section, Summary: the back link "← Resident list" (keeping the list's filter), the banner with the resident code as `<h1>`, the facts Device, Last check-in, Usable check-ins (last 30 days) and Baseline and the large status pill, the left section navigation with its six links (Summary, Review and notes with an unreviewed-alarm badge, Voice trends, Baseline, Check-in log, Device; each section its own URL), the two-column chart grid, the "Right now" panel (lead sentence per situation, alarm facts, "Leaning most", action buttons, the "not a diagnosis" note with the PI-confirmation marker), the "More detail" tiles linking to the other sections, and the "Resident not found" state. The other sections are added by FEAT-067 (Voice trends), FEAT-068 (Baseline, Check-in log), FEAT-069 and FEAT-071 (Review and notes) and FEAT-070 (Device).

## Business Context

- BR-13 (staff understand right away whether a resident changed and what to do next): the chart opens on "Right now", the way staff read an electronic health record, and goes into detail only on request.
- BR-11, BR-18: a Changed resident's alarm date, open days and review status are visible together with the reminder that the status is a prompt to check in, not a diagnosis (OQ-12 marker).
- BR-08, BR-09: the banner and the Summary state the current device, the baseline state and any restart.
- The alarm facts and "Leaning most" of the retired Alert review page move here (TRD 11 §4.17, UX-312; TRD 24 D-92, D-110, D-111).
- FRs covered (BACKLOG.md): FR-134, FR-160, FR-161, FR-164, FR-173, FR-262, FR-263, FR-266, FR-331.

## Referenced TRDs

- TRD 11 (v0.13) — owned by this feature: UX-060 (back link), UX-061..UX-063 (banner, large pill, facts), UX-065 (restart stated in Summary, Baseline and Voice trends; this feature owns the Summary sentence and checks the other two sections), UX-070..UX-073, UX-075..UX-078 (Right now panel, lead templates §4.5.2.1, note and marker, facts, buttons, More detail tiles), UX-312 (Leaning most), UX-410, UX-411 (section navigation and badge), UX-412 (unknown resident), UX-262 (reference rendering of the chart, §4.13.3; section values are asserted by the section features). Uses: `StatusPill` and wording (FEAT-062). Retired, not built: UX-064 (moved to UX-422, FEAT-068), UX-302, UX-311.
- TRD 04 (v0.11) FE-025 (back link with the last `?show=`), FE-206 (six section routes sharing the chart layout), FE-210 (section badge, review status and list text from `alarm_reviewed`), FE-087 (per-section reads, per-panel errors), FE-142 (404 → not-found for every chart route), FE-186 (E2E `resident-chart.spec.ts`), FE-193 (E2E `review.spec.ts`, Summary part), §4.3 chart routes, §4.8 `BackLink`, `ChartBanner`, `ChartSectionNav`, `CountBadge`, `SummaryPanel`, `LeaningMost`, `MoreDetailTiles`.
- TRD 19 E-09 `GET /api/v1/residents/{resident_code}` (`ResidentDetail` with `needs_attention`, `attention_reasons`, `alarm_reviewed`, D-114), E-13 `GET /api/v1/alerts?resident_code=` (`open_days`, `leaning_most`, status), E-17 `GET /api/v1/devices` (`uploaded_on_as_of_date`).
- TRD 13 TST-090, TST-096, TST-097; E2E-08, E2E-10, E2E-11, E2E-12.
- TRD 02 FR-134, FR-160, FR-161, FR-164, FR-173, FR-262, FR-263, FR-266, FR-331; TRD 24 D-18, D-92, D-108..D-111, D-113, OQ-12.

## Scope

- `app/(protected)/residents/[residentCode]/layout.tsx`: validated code, the chart queries shared by all sections (`getResident`, `getAlerts({ residentCode })`, `getDevices()`), `BackLink`, `ChartBanner`, two-column grid (200px `ChartSectionNav` | section content, gap 16px, top-aligned; one column below 760px per UX-241, verified by FEAT-075), resident not-found state.
- Section route files `page.tsx` (Summary), `review/page.tsx`, `trends/page.tsx`, `baseline/page.tsx`, `log/page.tsx`, `device/page.tsx`; this feature fills Summary and provides empty shells that FEAT-067..FEAT-071 fill.
- Components: `BackLink` ("← Resident list"), `ChartBanner`, `ChartSectionNav`, `SummaryPanel`, `LeaningMost`, `MoreDetailTiles`; Summary templates (§4.5.2.1), fact labels and button texts in `lib/wording.ts`.

## Out of Scope

- Change score chart and the 7 measurement cards (FEAT-067); Baseline and Check-in log sections (FEAT-068); alarm review panel (FEAT-069); Device section (FEAT-070); staff notes (FEAT-071).
- The status, attention flag, baseline, alert and `leaning_most` computations (backend FEAT-028, FEAT-030, FEAT-048).
- Approval of the final clinical wording (OQ-12, PI decision); the marker stays until then.

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-066-FR-01 | Every chart page shall start with the link "← Resident list" (weight 600, no underline, min-height 44px) to `/residents`, keeping the list's last `?show=` value (read from `sessionStorage["echowell.residentList.show"]`, default `all`). | UX-060, FE-025, FR-160, FR-331 |
| FEAT-066-FR-02 | The banner (`<section aria-label="Resident">`, panel) shall show the resident code as the page `<h1>` (26px, weight 700) and at its right end the large `StatusPill`. | UX-061, UX-062, FR-161 |
| FEAT-066-FR-03 | The banner shall show a `<dl>` (term 13px `--muted`, value weight 600) with "Device" — the current device code, plus " (replaced <previous device>)" when the API returns `previous_device_code`, or " (shared with <other resident codes>)" when the device is shared (e.g. "D07B (replaced D07)", "D02 (shared with R03)", "D09"); "Last check-in" — "Oct 30, 2:28 PM" or "No check-ins yet"; "Usable check-ins, last 30 days" — "<used> of <days in window>" (e.g. "30 of 30", "13 of 30"); "Baseline" — "Complete" when the current epoch's baseline is frozen, otherwise "<n> of <N>". | UX-063, FR-134 |
| FEAT-066-FR-04 | The section navigation (`<nav aria-label="Resident chart">`, in a panel) shall list "Summary" (`/residents/<R>`), "Review and notes" (`/review`), "Voice trends" (`/trends`), "Baseline" (`/baseline`), "Check-in log" (`/log`), "Device" (`/device`) in that order (weight 600, padding 10px 12px, min-height 44px); the current section's link has `aria-current="page"`, `--chrome` background and `--chrome-ink` text; each section has its own URL, so bookmarks and the browser back button work. | UX-410, FE-206 |
| FEAT-066-FR-05 | When the resident has an open, unreviewed change alarm (`ResidentDetail.alarm_reviewed` is `false`), the "Review and notes" link shall end with the `CountBadge` "1" and have the accessible name "Review and notes, alarm not reviewed"; the Summary review status uses the same field. | UX-411, FE-210 |
| FEAT-066-FR-06 | The Summary section shall start with a panel headed "Right now" with a 6px left border in the status colour (`--red`, `--yellow-edge`, `--grey`, `--green`) and the lead paragraph (20px, weight 600, max 62 characters per line) from the §4.5.2.1 template for the situation: Changed with current change score ≥ h ("<R>’s voice has moved away from their own usual pattern, steadily and long enough to set off the alarm on <Mon D>. It is still changed.") or < h ("… The change score is now below the alarm line, but the alarm stays on: in this version alarms are not switched off automatically."); Needs attention (the "What's happening" sentence + " EchoWell can’t judge their voice well until more good check-ins come in."); Learning; Usual with or without scored sessions; plus, when the current epoch > 1, " The baseline restarted on <Mon D> because <cause text>; <R> is now compared only with the new baseline." | UX-070, UX-071, UX-065, FR-164 |
| FEAT-066-FR-07 | For a Changed resident the panel shall show three facts (value 18px weight 700 above a 13px `--muted` label): "<alarm Mon D>" / "Alarm started"; "<d> days" / "Open" ("1 day"; "opened today" for 0); "Not reviewed" or "Reviewed" / "Review status"; then the line "Leaning most: <labels>"; then the primary button "Review this alert" (link to `/residents/<R>/review`) and the secondary button "See what changed" (link to `/residents/<R>/trends`). | UX-076, FR-262 |
| FEAT-066-FR-08 | "Leaning most" shall list up to 3 labels from the alert's `leaning_most` as the §4.5.4 plain-language labels in lower case without the technical name, joined by ", " (R09 "more pauses, quieter, less voiced sound"); with none it shall read "Leaning most: no single measurement stands out." | UX-312, FR-266, D-92 |
| FEAT-066-FR-09 | For a Needs-attention resident the panel shall show the secondary buttons "See missed and set-aside check-ins" (to `/residents/<R>/log`) and "Check the device" (to `/residents/<R>/device`). | UX-077 |
| FEAT-066-FR-10 | The panel shall end with the note (14px, `--muted`) "This compares <R> only with <R>. It is a prompt to check in, not a diagnosis." (Learning: "Once the baseline is complete, <R> will be compared only with <R>. A change is a prompt to check in, not a diagnosis."), followed by " [Final clinical wording: confirm with PI]" while `CLINICAL_WORDING_APPROVED` is false; no text states or implies a diagnosis, condition, severity or cause. | UX-072, UX-073, UX-075, FR-164, OQ-12, D-18 |
| FEAT-066-FR-11 | Below "Right now" a heading "More detail" (h2) shall head four link tiles (grid, min tile width 200px, gap 12px; label 13px `--muted`, value 18px weight 700, "Open" 14px link colour): "Voice trends" — "Change score <x.x>" (Changed), "Not scored yet" (no frozen baseline), otherwise "No change"; "Baseline" — "<n> of <N> check-ins"; "Check-ins, last 30 days" — "<used> used, <missed> missed"; "Device" — "<D> online" or "<D> no upload today" (`uploaded_on_as_of_date`); each tile links to its section. | UX-078 |
| FEAT-066-FR-12 | The chart layout shall issue `getResident`, `getAlerts({ residentCode })` and `getDevices()` in parallel; a failure of one renders the error state only in the panels that need it (UX-202); sections load their own data. | FE-087, UX-202 |
| FEAT-066-FR-13 | A 404 from `getResident` (or an invalid code) shall render "Resident <code> was not found." with the back link, and no banner, navigation or section. | UX-412, FE-142, FR-173 |
| FEAT-066-FR-14 | With the reference data the banners and Summaries shall equal TRD 11 §4.13.3 (R09, R10, R08, R03, R07). | UX-262, FR-263 |

## Inputs

- `GET /api/v1/residents/{code}` → `ResidentDetail` (status, `needs_attention`, `attention_reasons`, `alarm_reviewed`, device and previous device, shared-with codes, last check-in, `last_30_days`, current epoch, epoch start and restart cause, baseline state and progress, alarm since, current change score, meta).
- `GET /api/v1/alerts?resident_code=<R>` → the non-closed alert of the current epoch (`id`, `local_date`, `open_days`, `status`, `leaning_most`).
- `GET /api/v1/devices?limit=500` → `uploaded_on_as_of_date` of the resident's device.
- Route parameter `residentCode`; last list filter (`sessionStorage["echowell.residentList.show"]`, written by FEAT-065).

## Outputs

- Rendered chart frame (back link, banner, section navigation) and Summary section; not-found state; section route shells.

## Data Flow

`residentCode` validated (FEAT-064) → parallel queries `["resident", code]`, `["alerts", {residentCode}]`, `["devices"]` → `ChartBanner` (resident, meta → `displayStatus()` → large `StatusPill`) and `ChartSectionNav` (current section, `alarm_reviewed`) → Summary: `SummaryPanel` (resident, alert, meta, wording templates) and `MoreDetailTiles` (resident, device). Other sections render inside the same layout.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-064, FEAT-028, FEAT-029, FEAT-048

- FEAT-064 provides the route shell, app bar, code validation.
- FEAT-028 provides `GET /residents/{code}` (with the D-114 attention fields).
- FEAT-029 provides `GET /devices` with `uploaded_on_as_of_date` for the Device tile.
- FEAT-048 provides `leaning_most` on the alerts of `GET /alerts` (FEAT-030).

Features that build directly on this one (BACKLOG.md §4): FEAT-067, FEAT-068, FEAT-069, FEAT-070, FEAT-071.

## Database Impact

None (frontend only).

## API Impact

Endpoints consumed: `GET /api/v1/residents/{resident_code}` (E-09), `GET /api/v1/alerts` (E-13), `GET /api/v1/devices` (E-17). None exposed.

## Frontend Impact

- Pages: `app/(protected)/residents/[residentCode]/layout.tsx`, `page.tsx` (Summary) and the shells of `review/`, `trends/`, `baseline/`, `log/`, `device/`.
- Components: `BackLink`, `ChartBanner`, `ChartSectionNav`, `CountBadge`, `SummaryPanel`, `LeaningMost`, `MoreDetailTiles`, `StatusPill` (size `lg`), `SectionState`.

## Analytics Impact

None. Open days, change score, baseline progress and `leaning_most` come from the API; the UI maps measurement keys to labels only.

## Security Requirements

- Study ID only; no PII (UX-001); API strings rendered as text (SEC-076).
- Resident code validated and encoded (FE-030, FE-031, via FEAT-064).
- The "Review this alert" button is a link for every role; the review controls are gated by FEAT-069.

## Error Handling

- 404 → whole-page not-found (FE-142, UX-412).
- Alerts or devices query error → error state in the facts and tiles that need it; the lead text still renders from `ResidentDetail` (UX-202).
- Missing required field in a response → panel error state (FE-078).

## Logging Requirements

None in the frontend.

## Testing Requirements

- Component (TST-090): `ChartBanner` (device texts "D07B (replaced D07)", "D02 (shared with R02)", "D09"; "30 of 30", "13 of 30"; "Complete" / "13 of 16"; large pill), `ChartSectionNav` (order, `aria-current`, badge "1" and accessible name only for an open alarm), `SummaryPanel` (every §4.5.2.1 template incl. below-line and restart sentences, facts "9 days" / "1 day" / "opened today", Leaning most incl. the empty text, buttons per status; marker "[Final clinical wording: confirm with PI]" present while unapproved — TST-096; "It is a prompt to check in, not a diagnosis." present — TST-097), `MoreDetailTiles` (four values per status).
- Page test (`frontend/tests/pages/resident-chart.test.tsx`): loading, populated (R09 fixture), 404 not-found, panel error isolation, back link keeps `?show=`, 401 → login (TST-094).
- E2E (`resident-chart.spec.ts`, FE-186; `review.spec.ts` Summary part, FE-193): E2E-08 (R09 banner and Summary), E2E-10 (R07 banner and restart sentence), E2E-11 (R08 Needs attention), E2E-17 (alarm entry points: R09 and R10 facts and tiles) of TRD 13 Table 4.10-A.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-066-AC-01 | `/residents/R09` shows "← Resident list", the `<h1>` "R09", Device "D09", Last check-in "Oct 30, 2:28 PM", Usable check-ins "30 of 30", Baseline "Complete", the large pill "▲ Changed", and the lead "R09’s voice has moved away from their own usual pattern, steadily and long enough to set off the alarm on Oct 21. It is still changed." | E2E-08; AC-UX-04; UX-262 |
| FEAT-066-AC-02 | R09's Summary shows "Oct 21" Alarm started, "9 days" Open, "Not reviewed" Review status, "Leaning most: more pauses, quieter, less voiced sound", the buttons "Review this alert" and "See what changed", and the tiles "Change score 26.8", "16 of 16 check-ins", "30 used, 0 missed", "D09 online"; R10 shows "6 days", "more pauses, slower while talking, fewer syllables per second" and "Change score 13.4". | E2E-08; UX-076; UX-078; UX-312 |
| FEAT-066-AC-03 | The Summary note contains "It is a prompt to check in, not a diagnosis." and ends with "[Final clinical wording: confirm with PI]". Verified by: Component (TST-096, TST-097). | UX-072; UX-073 |
| FEAT-066-AC-04 | `/residents/R08` shows "! Needs attention", Usable "13 of 30", Baseline "13 of 16", the lead "Missing many check-ins. Baseline stuck at 13 of 16. EchoWell can’t judge their voice well until more good check-ins come in.", the buttons "See missed and set-aside check-ins" and "Check the device", and the tiles "Not scored yet", "13 of 16 check-ins", "13 used, 12 missed", "D08 online", with no error banner. | E2E-11; AC-UX-05; UX-077 |
| FEAT-066-AC-05 | `/residents/R07` shows Device "D07B (replaced D07)", "● Usual" and the lead "R07’s voice is within their own usual range. Nothing to do. The baseline restarted on Oct 13 because the device changed (D07B, was D07); R07 is now compared only with the new baseline."; `/residents/R03` shows Device "D02 (shared with R02)", "22 of 30" and "! Needs attention". | E2E-10; E2E-12; UX-065 |
| FEAT-066-AC-06 | The section navigation lists the six links in order; on R09 and R10 "Review and notes" carries the badge "1" with the accessible name "Review and notes, alarm not reviewed"; on R01 it has no badge; each link opens its own URL. Verified by: Component and Page test (TST-090, TST-094). | UX-410; UX-411; AC-UX-11 |
| FEAT-066-AC-07 | `/residents/R11` (unknown) shows "Resident R11 was not found." with the back link and no banner, navigation or section. Verified by: Page test (TST-094). | UX-412; FE-142; FR-173 |
| FEAT-066-AC-08 | Switching the backend to the production profile shows "of 30" in Baseline facts and Learning texts without a frontend change. Verified by: Component test with a production fixture. | UX-007; AC-UX-10 |

## Definition of Done

- All FEAT-066 acceptance criteria pass; component, page and E2E tests green.
- OQ-12 marker present in the Summary note (TRD 25 Phase 8 DoD).
- The batch report lists the implemented requirement IDs (AGT-022).

## Implementation Notes

- Use the typographic apostrophe "’" exactly as in TRD 11 ("R09’s", "can’t").
- "Leaning most" is the alert's `leaning_most` (mean signed z since the alarm date, TRD 24 D-92); lower-case the §4.5.4 labels ("Quieter" → "quieter"). The v0.2 wireframe note asking for the 2 or 3 measurements leaning most is answered by this line (D-111).
- The open-day count and the change score come from the API; never compute them in the browser.
- The v0.1 header text "<R> · Device <D>", the "What this means" heading, the baseline line in the header and the `<progress>` in the header are not built; the baseline text and meter are the Baseline section (FEAT-068).
- Pages that FEAT-067..FEAT-071 fill render a `SectionState` until their feature is merged within this checkpoint; no section may stay empty at the checkpoint exit.
- The file name keeps the v0.1 title (feature IDs and file names are never renamed, TRD 25 §4.2).
