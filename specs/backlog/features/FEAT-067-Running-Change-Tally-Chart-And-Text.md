# FEAT-067 Running change tally chart and text table

| Field | Value |
|---|---|
| Epic | Frontend |
| Build phase | Phase 8 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-066, FEAT-034 |
| Status | Not Started |

## Purpose

Implement the "Running change tally" section of Resident detail: `CusumChart` (Recharts) with one bar per scored session of the displayed epoch, grey outlined bars while the alarm is off and accent bars from the first crossing on (showing persistence), the leading grey baseline slot, the dashed "alarm line 5.0", the "▲" marker and "<Mon D> · alarm" label, 0-height stubs, no animation, and the equivalent `CusumTable` behind a visible toggle. Residents with more than one epoch can view an earlier epoch's tally. The same chart rules are reused by the Alert review mini chart (FEAT-069).

## Business Context

- BR-11 (alarm only after a sustained change; persists after first crossing) and BR-13 (staff see how the change built up).
- BR-09 (baseline period visible), WCAG 1.1.1 / 1.4.11 (text alternative, non-text contrast; NFR-063).
- D-30 / contract §20 R1: the binding chart rules.
- FRs covered (BACKLOG.md): FR-165, FR-166, FR-167, FR-168, FR-172.

## Referenced TRDs

- TRD 04 FE-093 (Recharts `ComposedChart`, bar fills, reference line, baseline `ReferenceArea`), FE-094 (▲ marker and "· alarm" tick), FE-095 (0-height stub), FE-096 (200px height, 700px min width, scroll container), FE-097 (`role="img"`, `cusumSummary()`, `<details>` "Show tally as a table"), FE-099 (no animation), FE-183, FE-184 (component tests), §4.8 `CusumChart`, `CusumTable`, §8 notes (baseline slot as category `"__baseline__"`; colour from `alarm_state`).
- TRD 11 UX-080..UX-092 (heading and subtitle, bars, baseline slot, colours, alarm line, marker, x labels, y axis, caption, forming text, table, accessible name, epoch > 1 line), §4.13.3 tally values.
- TRD 13 TST-093 (CusumChart assertions), TST-112 (table reachable by screen reader); E2E-08, E2E-10, E2E-11.
- TRD 19 E-12 `GET /api/v1/scores` (`items`, `baseline_periods`, `cusum_k`).
- TRD 02 FR-165..FR-168, FR-172; TRD 24 D-30.

## Scope

- Section "Running change tally" on `/residents/[residentCode]` with subtitle, optional epoch line, chart, caption, disclosure table, forming placeholder.
- Components `CusumChart` (`{ points, baselinePeriod, h, residentCode, tz }`) and `CusumTable` (`{ points, h }`), `lib/wording.ts` `cusumSummary()`.
- Epoch selection for residents with `epoch_count` > 1: `getScores({ residentCode, epoch })` for the chosen epoch, default the current epoch.
- Component tests with the R09, R10, R07 fixtures.

## Out of Scope

- `GET /api/v1/scores` and baseline periods (FEAT-034).
- The mini chart on `/alerts` (FEAT-069 reuses `CusumChart` via `MiniTallyChart`).
- An EWMA trend or baseline band (FEAT-096, OQ-18).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-067-FR-01 | The section shall have the heading "Running change tally" and, right-aligned on the same row (wrapping on narrow screens), the subtitle "Builds up when check-ins keep leaning the same way; alarm at <h>" with h from `meta.cusum_h`. | UX-080, UX-245 |
| FEAT-067-FR-02 | `CusumChart` shall use Recharts `ComposedChart` with one `Bar` (`dataKey="cusum_tally"`) per scored session of the displayed epoch in time order, height = API `cusum_tally`. | FE-093, UX-081, FR-165 |
| FEAT-067-FR-03 | Bars with `alarm_state` `off` shall be filled `--color-baseline-bar` (#BDBDB8) with a 1px `--color-border` (#8A8A85) stroke; bars with `rings` or `on` filled `--color-accent` (#9A4508); the colour is chosen from `alarm_state`, never by comparing the tally with h. | FE-093, UX-083, FR-165, D-30 |
| FEAT-067-FR-04 | A leading grey slot (category placed before the first scored bar, `ReferenceArea` fill #BDBDB8 at 40 % opacity, full height) shall be labelled "Baseline <first date>–<frozen-after date>" from `baseline_periods` (R09 "Baseline Oct 1–16"). | FE-093, UX-082, FR-165 |
| FEAT-067-FR-05 | A dashed `ReferenceLine` at y = h (stroke #9A4508, width 2, dash "6 4") shall be labelled "alarm line <h>" ("alarm line 5.0") in IBM Plex Mono 12px accent at its right end. | FE-093, UX-084, FR-165 |
| FEAT-067-FR-06 | The `rings` bar shall carry a "▲" marker above it and its x tick shall read "<Mon D> · alarm"; the x axis labels at least the first scored date, the alarm date and the last scored date (minimum 48px apart). | FE-094, UX-085, UX-086, FR-166 |
| FEAT-067-FR-07 | A bar with `cusum_tally` 0 shall render as a 2px stub in `--color-border`. | FE-095 |
| FEAT-067-FR-08 | The y axis shall start at 0 with maximum max(1.2 × h, 1.05 × largest tally) and ticks every 5 units in IBM Plex Mono 12px. | UX-087 |
| FEAT-067-FR-09 | Plot height 200px, minimum width 700px, inside an `overflow-x: auto` container that is keyboard-focusable with an accessible name; `isAnimationActive={false}` on every Recharts element. | FE-096, FE-099, UX-243, UX-230 |
| FEAT-067-FR-10 | Below the chart the caption "Set-aside, quarantined and missed days leave the tally unchanged." shall appear in IBM Plex Mono 12px secondary. | UX-088, FR-167 |
| FEAT-067-FR-11 | The chart shall have `role="img"` and an `aria-label` from `cusumSummary()`: "Running change tally for <R> from <first Mon D> to <last Mon D>. Baseline <range>. Alarm line <h>. <Crossed the alarm line on <Mon D>; \| Below the alarm line throughout;> now <tally>." | FE-097, UX-091 |
| FEAT-067-FR-12 | A `<details>` "Show tally as a table" shall contain `CusumTable` with columns "Date", "Tally", "Alarm", one row per bar, "Alarm" reading "—" (off), "▲ Alarm rings (first crossing)" (rings) or "▲ Alarm on" (on), tallies with one decimal; the table has role `table` and a caption naming the resident. | FE-097, UX-090, TST-112, FR-168 |
| FEAT-067-FR-13 | When the baseline is forming the chart area shall be replaced by "No tally yet. The tally starts after the baseline is complete (<n> of <N> usable check-ins so far)." | UX-089 |
| FEAT-067-FR-14 | When the current epoch > 1, a line above the chart shall read "Showing the current device period since <Mon D>. Earlier periods are not scored against this baseline." | UX-092 |
| FEAT-067-FR-15 | For a resident with more than one epoch the user shall be able to select an earlier epoch; the chart and table then show that epoch's scores and baseline period from `GET /api/v1/scores?resident_code=<R>&epoch=<n>`. | FR-172, TRD 04 §4.6.2 `getScores` |
| FEAT-067-FR-16 | With the reference data, R09 shows "Baseline Oct 1–16", 14 bars Oct 17–30 with tallies 3.2, 2.6, 1.8, 1.6 (grey), 5.4 (▲, "Oct 21 · alarm"), 8.0 … 26.8 (accent); R10 Oct 17–23 grey and Oct 24 ▲ 6.0; R07 epoch 2 "Baseline Oct 13–28" with two 0.0 stubs. | UX-262, TRD 11 §4.13.3 |

## Inputs

- `GET /api/v1/scores?resident_code=<R>&epoch=<n>` → `ScoresResponse` (`items: ScoreRow[]`, `baseline_periods[]`, `meta`).
- `ResidentDetail` (`current_epoch`, `epoch_count`, `baseline` state and progress) from FEAT-066's query; `meta.cusum_h`, `meta.facility_tz`.

## Outputs

- Rendered chart, caption, disclosure table, forming text and epoch selector.

## Data Flow

Page query `["resident", code, "scores", epoch]` → points (scored sessions, API order by time) and baseline period → `CusumChart` (bars coloured by `alarm_state`, baseline slot, reference line, marker) and `CusumTable` (same points, formatted with `formatTally`, `formatLocalDate`).

## Dependencies

Required before implementation (BACKLOG.md): FEAT-066, FEAT-034

- FEAT-066 provides the Resident detail page and resident query.
- FEAT-034 provides `GET /api/v1/scores` with `baseline_periods`.

Features that build directly on this one (BACKLOG.md §4): FEAT-069, FEAT-075, FEAT-096.

## Database Impact

None (frontend only).

## API Impact

Endpoint consumed: `GET /api/v1/scores` (E-12) with `resident_code` and optional `epoch`. None exposed.

## Frontend Impact

- Section on `app/(protected)/residents/[residentCode]/page.tsx`.
- Components: `CusumChart`, `CusumTable`; wording helper `cusumSummary()`.

## Analytics Impact

None. Tally values and alarm states are rendered as returned (no client CUSUM computation, no rounding except display to one decimal, NFR-037).

## Security Requirements

None beyond the page's authenticated, client-side fetching (FE-040).

## Error Handling

- Scores query error → error state only in this section (FE-087, UX-202).
- No scored sessions and baseline frozen → chart with baseline slot and no bars, or forming text when forming (UX-089).

## Logging Requirements

None in the frontend.

## Testing Requirements

- Component (`components/CusumChart/CusumChart.test.tsx`): TST-093 assertions on the R09 fixture — 14 bars, first 4 grey with outline, last 10 accent, slot "Baseline Oct 1–16", reference line at 5.0 labelled "alarm line 5.0", tick "Oct 21 · alarm", caption, accessible table (FE-183); R07 stubs; R10 colouring.
- Component (`components/CusumTable/CusumTable.test.tsx`): 14 rows with 3.2, 2.6, 1.8, 1.6, 5.4, 8.0, 8.3, 10.7, 12.4, 15.3, 16.7, 18.8, 23.1, 26.8 (FE-184); alarm column texts.
- Accessibility: TST-112 table reachable by screen reader (RTL and axe).
- E2E: E2E-08 (R09 chart), E2E-10 (R07 epoch 2 only with 2 bars), E2E-11 (R08 chart empty state).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-067-AC-01 | The R09 `CusumChart` renders 14 bars: Oct 17–20 with fill #BDBDB8 and 1px #8A8A85 stroke, Oct 21–30 with fill #9A4508, a reference line at y = 5.0 labelled "alarm line 5.0", a "Baseline Oct 1–16" slot and the tick "Oct 21 · alarm". | FE-183; TST-093; AC-FE-03 |
| FEAT-067-AC-02 | The R09 `CusumTable` lists 14 rows with tallies 3.2, 2.6, 1.8, 1.6, 5.4, 8.0, 8.3, 10.7, 12.4, 15.3, 16.7, 18.8, 23.1, 26.8 and Oct 21 marked "▲ Alarm rings (first crossing)". | FE-184; UX-090 |
| FEAT-067-AC-03 | The R09 chart's accessible name equals "Running change tally for R09 from Oct 17 to Oct 30. Baseline Oct 1–16. Alarm line 5.0. Crossed the alarm line on Oct 21; now 26.8." Verified by: Component (`components/CusumChart/CusumChart.test.tsx`; TST-093, FE-183). | UX-091; FE-097 |
| FEAT-067-AC-04 | `/residents/R07` shows "Showing the current device period since Oct 13. Earlier periods are not scored against this baseline.", "Baseline Oct 13–28" and 2 bars drawn as stubs. | E2E-10; UX-092; FE-095 |
| FEAT-067-AC-05 | `/residents/R08` shows "No tally yet. The tally starts after the baseline is complete (13 of 16 usable check-ins so far)." and no bars. | E2E-11; UX-089 |
| FEAT-067-AC-06 | For R07, selecting epoch 1 requests `GET /api/v1/scores?resident_code=R07&epoch=1` and renders no bars (epoch 1 never formed). Verified by: E2E (E2E-08, E2E-10, E2E-11). | FR-172 |
| FEAT-067-AC-07 | axe reports no serious or critical violation on `/residents/R09` related to the chart, and the table has role `table` with a caption naming R09. | TST-112; TST-110 |

## Definition of Done

- All FEAT-067 acceptance criteria pass; component and E2E tests green.
- R09 detail shows the alarm line labelled "alarm line 5.0", grey baseline slot and accent post-alarm bars (TRD 25 Phase 8 DoD).
- Batch report lists IDs and the TRD gaps below (AGT-022).

## Implementation Notes

- Implement the baseline slot as the categorical x value `"__baseline__"` before the first scored date and keep it even with many scored sessions (TRD 04 §8).
- Bars follow `alarm_state` from `/scores`; after a first crossing bars stay accent even if the tally drops below h (TRD 04 §8, TRD 11 §8).
- Missed days have no bar (TRD 11 §8); never draw zero-height bars for non-scored days.
- The text table columns are "Date", "Tally", "Alarm" (UX-090, TST-093, FE-184); TRD 02 FR-168 was aligned in the PR #2 consistency fixes.
- FR-172 (Should, earlier epoch view) has no control in TRD 04 or TRD 11; it is TRD 24 OQ-28 (open). Implement its interim decision: a labelled native `<select>` "Device period" above the chart listing epochs 1..`epoch_count` (default current, hidden when `epoch_count` is 1), loading the chosen epoch with `GET /api/v1/scores?resident_code=&epoch=` and reusing the chart and the UX-092 line pattern.
