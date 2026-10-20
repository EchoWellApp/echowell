# FEAT-066 Resident detail page: header, What this means and the 7 measurements

| Field | Value |
|---|---|
| Epic | Frontend |
| Build phase | Phase 8 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-064, FEAT-028 |
| Status | Not Started |

## Purpose

Implement the frame and the explanatory sections of `/residents/[residentCode]` (SRC-10): the back link, the header with device and large status badge, the baseline line (frozen range and watched-since date, or forming progress, plus the restart suffix), the "What this means" section from the PI-reviewed wording with the confirmation marker, the seven measurement cards with plain-language labels and signed sparklines, the "12 other measurements" card, the captions, and the "Resident not found" state. The tally chart, check-in log and staff review sections are added by FEAT-067, FEAT-068 and FEAT-071.

## Business Context

- BR-13 (staff understand why a resident is flagged and what it means): plain-language explanation and the measurements behind the score.
- BR-09 (frozen personal baseline) and BR-08 (baseline restarts on device change): the baseline line states exactly what the resident is compared with.
- BR-10 (7 scored features, 12 stored), BR-18 (detection, not diagnosis; OQ-12 marker).
- FRs covered (BACKLOG.md): FR-160, FR-161, FR-162, FR-163, FR-164, FR-169, FR-170, FR-171, FR-173.

## Referenced TRDs

- TRD 04 FE-087 (parallel queries, per-section errors), FE-092 (`StatusBadge` via `statusLabel()`), FE-098 (`Sparkline` signed deviations), FE-142 (404 → whole-page not-found), §4.8 `ResidentHeader`, `WhatThisMeans`, `FeatureCard`, `Sparkline`, `OtherMeasurementsCard`, `BackLink`, FE-186 (E2E `resident-detail.spec.ts`).
- TRD 11 UX-060..UX-066 (back link, header, large badge, baseline line, progress element, restart text, stable dates), §4.5.1.1 baseline line templates, UX-070..UX-075 (What this means), §4.5.2.1 templates, UX-100..UX-108 (measurement cards, sparkline, accessible names, forming state, 12 other measurements, caption), UX-205, §4.13.3.
- TRD 13 TST-096 (marker), TST-097 (wording), TST-090; E2E-08, E2E-10, E2E-11.
- TRD 19 E-09 `GET /api/v1/residents/{resident_code}`, E-11 `GET /api/v1/residents/{resident_code}/features`.
- TRD 02 FR-160..FR-164, FR-169..FR-171, FR-173; TRD 24 OQ-12, D-18.

## Scope

- `app/(protected)/residents/[residentCode]/page.tsx`: validated code, parallel queries (`getResident`, `getFeatures`; `getScores`, `getCheckins`, `getNotes` are issued here and consumed by FEAT-067, FEAT-068, FEAT-071 sections), layout order Back link → header → What this means → Running change tally → measurements → (Staff review | Check-in log) → default footer.
- Components: `ResidentHeader`, `WhatThisMeans`, `FeatureCard` (×7), `Sparkline`, `OtherMeasurementsCard`; resident not-found state.
- Wording templates in `lib/wording.ts` for the baseline line and "What this means" (all situations of §4.5.1.1 and §4.5.2.1).

## Out of Scope

- `CusumChart`/`CusumTable` (FEAT-067), `CheckinLog` (FEAT-068), `StaffReviewForm`/`NotesList`/`ReviewDialog` (FEAT-071).
- The status, baseline and feature computations (backend FEAT-028).
- Approval of the final clinical wording (OQ-12, PI decision); the marker stays until then.

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-066-FR-01 | The page shall start with "← Back to all residents" to `/residents`, preserving the last overview `?sort=`. | UX-060, FR-160 |
| FEAT-066-FR-02 | The `<h1>` shall read "<R> · Device <D>" with the current device (e.g. "R09 · Device D09", "R07 · Device D07B") and a large status badge on the right with the §4.3.4 text and style rules (via `statusLabel()`, "▲" on alarm). | UX-061, UX-062, FE-092, FR-161 |
| FEAT-066-FR-03 | Below the `<h1>` the baseline line shall use the §4.5.1.1 templates: frozen with scored sessions "Baseline: first <N> usable check-ins, <first>–<frozen-after> (then frozen) · watched since <first scored date>"; frozen without scored session "… · watched since <local date after the freeze session>"; forming "Baseline: forming · <n> of <N> usable check-ins so far (frozen when <N> are reached)"; plus the restart suffix by cause (device, firmware, software) when the current epoch > 1. | UX-063, UX-065, FR-162, FR-163 |
| FEAT-066-FR-04 | When forming, a native `<progress>` (max N, value n, width 200px) with accessible name "Baseline progress: <n> of <N> usable check-ins" shall be shown. | UX-064, FR-163 |
| FEAT-066-FR-05 | Baseline dates and frozen state shall be rendered only from the API (`baseline.first_local_date`, `baseline.frozen_after_local_date`, `watching_since`) and never change after freeze. | UX-066 |
| FEAT-066-FR-06 | "What this means" shall show a main paragraph (16px) from the §4.5.2.1 template for the resident's situation (alarm_on above/below line, no_alarm with/without scored sessions, baseline_forming, plus the restart sentence for epoch > 1) and a note paragraph "This compares <R> only with <R>. It is a prompt to check in, not a diagnosis." (forming: "Once the baseline is complete, <R> will be compared only with <R>. An alarm is a prompt to check in, not a diagnosis."). | UX-070, UX-071, UX-072, FR-164 |
| FEAT-066-FR-07 | Until `CLINICAL_WORDING_APPROVED` is true the note shall end with " [Final clinical wording: confirm with PI]"; all texts come from `lib/wording.ts`; no diagnosis, condition, severity or cause is stated. | UX-073, UX-074, UX-075, FR-164, OQ-12, D-18 |
| FEAT-066-FR-08 | "The 7 measurements behind the score" shall show the intro "Each is compared with <R>’s own baseline. The score rises when the voice is:" and exactly 7 cards in order: Quieter (loudness), Slower to say the phrase (phrase duration), Fewer syllables per second (speech rate), Slower while talking (articulation rate), More pauses (number of pauses), More time in pauses (pause fraction), Less voiced sound (voiced fraction), in a 2-column grid. | UX-100, UX-101, FR-169 |
| FEAT-066-FR-09 | Each card's sparkline (120 × 32px) shall plot `sign × z` of the scored sessions of the current epoch as a 1.5px ink line with a dashed zero line, no axes, grid, tooltip or animation, and have the accessible name "<label> (<technical name>): latest <signed value> compared with own baseline over <k> scored check-ins". | UX-102, UX-103, FE-098, FE-099 |
| FEAT-066-FR-10 | While the baseline is forming each card shall show "Not scored yet" with a 1px dashed border instead of a sparkline; cards show no per-feature alarm, threshold or "abnormal" label and no accent colour. | UX-104, UX-105 |
| FEAT-066-FR-11 | An eighth card (muted panel, 1px rule border) shall read "12 other measurements (pitch, jitter, MFCCs …)" and "stored, not scored", with the number from `stored_feature_keys.length`; those features are not listed, plotted or summarised. | UX-106, UX-107, FR-170 |
| FEAT-066-FR-12 | Below the cards the caption "Column names are placeholders until Team 1 confirms extractor output names. Morning check-ins are adjusted before comparing." shall appear (IBM Plex Mono 12px, secondary). | UX-108, FR-171 |
| FEAT-066-FR-13 | The page shall issue `getResident`, `getScores`, `getFeatures`, `getCheckins` and `getNotes` in parallel; a failure of one renders the error state only in its section. | FE-087, UX-202 |
| FEAT-066-FR-14 | A 404 from `getResident` (or an invalid code) shall render "Resident <code> was not found." with the back link and no other section. | FE-142, UX-205, FR-173 |
| FEAT-066-FR-15 | With the reference data the header, badge and baseline lines shall equal TRD 11 §4.13.3 (e.g. R09 "Baseline: first 16 usable check-ins, Oct 1–16 (then frozen) · watched since Oct 17"; R08 forming 13 of 16; R07 "… Oct 13–28 (then frozen) · watched since Oct 29 · restarted Oct 13 (new device D07B, was D07)"). | UX-262 |

## Inputs

- `GET /api/v1/residents/{code}` → `ResidentDetail` (status, device, current_epoch, epoch_count, baseline, watching_since, alarm_since, current_tally, explanation, meta).
- `GET /api/v1/residents/{code}/features` → `FeaturesResponse` (`scored_features[7]` with `label`, `composite_sign`, `points[{z, …}]`, `stored_feature_keys[12]`).
- Route parameter `residentCode`.

## Outputs

- Rendered header, baseline line, "What this means", measurement cards and captions; not-found state.

## Data Flow

`residentCode` validated (FEAT-064) → parallel queries `["resident", code]`, `["resident", code, "features"]` (and scores, check-ins, notes for sibling sections) → `ResidentHeader` (resident, meta) → `WhatThisMeans` (resident, meta, wording templates) → `FeatureCard` ×7 (label, sign, series of `z` per scored session) + `OtherMeasurementsCard` (stored keys).

## Dependencies

Required before implementation (BACKLOG.md): FEAT-064, FEAT-028

- FEAT-064 provides the route shell, `BackLink`, code validation.
- FEAT-028 provides `GET /residents/{code}`, `/checkins` and `/features`.

## Database Impact

None (frontend only).

## API Impact

Endpoints consumed: `GET /api/v1/residents/{resident_code}` (E-09), `GET /api/v1/residents/{resident_code}/features` (E-11); the page also starts `GET /api/v1/scores` (E-12), `/checkins` (E-10) and `/notes` (E-15) for sibling sections. None exposed.

## Frontend Impact

- Page: `app/(protected)/residents/[residentCode]/page.tsx`.
- Components: `ResidentHeader`, `WhatThisMeans`, `FeatureCard`, `Sparkline`, `OtherMeasurementsCard`, `StatusBadge` (size `lg`), `BackLink`, `Footer` (default), `SectionState`.

## Analytics Impact

None. The UI multiplies the API's unsigned `z` by `composite_sign` for display only (FE-098); no scoring is computed.

## Security Requirements

- Study ID only; no PII (UX-001); API strings rendered as text (SEC-076).
- Resident code validated and encoded (FE-030, FE-031, via FEAT-064).

## Error Handling

- 404 → whole-page not-found (FE-142).
- Features query error → error state in the measurements section only (FE-087).
- Missing required field in a response → section error state (FE-078).

## Logging Requirements

None in the frontend.

## Testing Requirements

- Component: `ResidentHeader` (baseline line templates incl. restart suffix and forming progress), `WhatThisMeans` (each template; marker "[Final clinical wording: confirm with PI]" present while unapproved — TST-096; "It is a prompt to check in, not a diagnosis." present — TST-097), `FeatureCard`/`Sparkline` (signed series, accessible name, "Not scored yet"), `OtherMeasurementsCard` (TST-090).
- Page test (`frontend/tests/pages/resident-detail.test.tsx`): loading, populated (R09 fixture), 404 not-found, section error isolation, 401 → login (TST-094).
- E2E: `resident-detail.spec.ts` (FE-186) header, badge, baseline line for R09, R10, R08, R07; E2E-08 (R09 header and 7 cards plus "12 other measurements"), E2E-10 (R07 badge), E2E-11 (R08 forming, no error banner).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-066-AC-01 | `/residents/R09` shows "R09 · Device D09", "▲ Alarm since Oct 21", "Baseline: first 16 usable check-ins, Oct 1–16 (then frozen) · watched since Oct 17", and the main paragraph "R09’s voice has moved away from their own usual pattern, steadily enough and for long enough to cross the alarm line on Oct 21. It is still above the line." | E2E-08; AC-UX-04; UX-262 |
| FEAT-066-AC-02 | The note paragraph contains "It is a prompt to check in, not a diagnosis." and ends with "[Final clinical wording: confirm with PI]". | TST-096; TST-097 |
| FEAT-066-AC-03 | R09 shows 7 measurement cards with the §4.5.4 labels in order and the card "12 other measurements (pitch, jitter, MFCCs …)" / "stored, not scored". | E2E-08; UX-101; UX-106 |
| FEAT-066-AC-04 | `/residents/R08` shows "Baseline forming · 13 of 16 sessions", the forming baseline line, a `<progress>` 13/16 and "Not scored yet" on all 7 cards, with no error banner. | E2E-11; AC-FE-04; AC-UX-05 |
| FEAT-066-AC-05 | `/residents/R07` shows "No alarm · baseline restarted Oct 13" and the restart suffix "restarted Oct 13 (new device D07B, was D07)". | E2E-10; AC-UX-05 |
| FEAT-066-AC-06 | `/residents/R11` (unknown) shows "Resident R11 was not found." with the back link and no other section. | FE-142; UX-205; FR-173 |
| FEAT-066-AC-07 | Switching the backend to the production profile shows "of 30" in forming texts without a frontend change. | AC-FE-04; AC-UX-10 |

## Definition of Done

- All FEAT-066 acceptance criteria pass; component, page and E2E tests green.
- OQ-12 marker present (TRD 25 Phase 8 DoD).
- Batch report lists IDs and the TRD conflict below (AGT-022).

## Implementation Notes

- TRD conflict: FR-169 describes the sparkline as "recent adjusted values", while UX-102 and FE-098 require signed deviations `sign × z`. Implement `sign × z` (two detailed rows agree with the SRC-10 wireframe semantics) and report FR-169 for correction.
- FR-163 says the header shows "Baseline forming · n of N sessions" as a progress indicator; this is satisfied by the large badge text plus the UX-063 baseline line and the UX-064 `<progress>` element.
- Use the typographic apostrophe "’" exactly as in TRD 11 (e.g. "R09’s", "<R>’s own baseline").
- Labels for the 7 cards come from the API `label` where it matches TRD 11 §4.5.4; split "Quieter (loudness)" into label and technical name for the two-tone rendering.
