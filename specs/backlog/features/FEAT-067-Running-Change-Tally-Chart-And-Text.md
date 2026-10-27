# FEAT-067 Voice trends: change score chart and the 7 voice measurements

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

Implement the "Voice trends" section of the resident chart (`/residents/[residentCode]/trends`, SRC-21): the "Change score" panel (the CUSUM tally, renamed in the UI by TRD 24 D-113) with the intro line, `ChangeScoreChart` (Recharts) with one bar per scored session of the displayed epoch, bars in `--c-aside` while the alarm is off and `--red` from the first crossing on (alarm persistence, D-03), the leading grey baseline slot (kept from v0.1, D-111), the dashed red "Alarm line: <h>", the "▲" marker and "<Mon D> · alarm" label, zero-value stubs, no animation, the equivalent `ChangeScoreTable` behind "Show change score as a table", the forming and new-device-period texts and the earlier-epoch selector; and the panel "The 7 voice measurements behind the score" with seven cards (plain-language label, technical name, signed sparkline), the eighth card "12 other measurements (pitch, jitter, MFCCs and others)" / "Stored, not scored", and the placeholder caption. The measurement cards move here from the v0.1 Resident detail feature, and this chart replaces the retired Alert review mini chart (UX-311).

## Business Context

- BR-11 (alarm only after a sustained change; persists after first crossing) and BR-13 (staff see how the change built up and which measurements moved): "See what changed" on the Summary leads here.
- BR-09 (baseline period visible), BR-10 (7 scored measurements, 12 stored), BR-18 (no per-measurement alarm or diagnosis), WCAG 1.1.1 / 1.4.11 (text alternative, non-text contrast; NFR-063).
- D-30 / contract §20 R1: the binding chart rules; D-111 keeps the baseline slot, the data table and the colouring by `alarm_state`; D-113 renames "Running change tally" to "Change score".
- FRs covered (BACKLOG.md): FR-165, FR-166, FR-167, FR-168, FR-169, FR-170, FR-171, FR-172.

## Referenced TRDs

- TRD 11 (v0.13) — owned by this feature: UX-080..UX-087, UX-089..UX-092 (Change score panel, bars, baseline slot, colours, alarm line, marker, x and y axes, forming text, table, accessible name, device-period line), UX-100..UX-108 (measurement panel, cards, sparklines, accessible names, forming state, no per-measurement alarm, "12 other measurements" card, stored keys not shown, caption), §4.5.3, §4.5.4, Voice trends values of §4.13.3. Retired, not built: UX-088 (caption folded into UX-080), UX-311 (mini chart).
- TRD 04 (v0.11) FE-093..FE-099 (Recharts `ComposedChart`, fills, reference line, baseline area, marker and tick, stub, size and scroll container, `role="img"` and table, sparkline, no animation), FE-154 (one decimal, h without trailing zeros), FE-183, FE-184 (component tests), FE-186 (E2E), §4.8 `ChangeScoreChart`, `ChangeScoreTable`, `MeasurementCards`, `FeatureCard`, `Sparkline`, `OtherMeasurementsCard`, §8 notes (baseline slot as category `"__baseline__"`; colour from `alarm_state`).
- TRD 13 TST-093 (chart assertions), TST-112 (table reachable by screen reader); E2E-08, E2E-10, E2E-11.
- TRD 19 E-12 `GET /api/v1/scores` (`items`, `baseline_periods`), E-11 `GET /api/v1/residents/{resident_code}/features`.
- TRD 02 FR-165..FR-172; TRD 24 D-03, D-30, D-111, D-113, OQ-03, OQ-28.

## Scope

- `app/(protected)/residents/[residentCode]/trends/page.tsx`: queries `getScores({ residentCode, epoch })` and `getFeatures(code)`; panel "Change score" (intro, optional device-period line, epoch selector, chart, disclosure table, forming text) and panel "The 7 voice measurements behind the score".
- Components `ChangeScoreChart` (`{ points, baselinePeriod, h, residentCode, tz, restartedOn }`), `ChangeScoreTable` (`{ points, h }`), `MeasurementCards` (`{ features, residentCode, baselineForming }`) with `FeatureCard` (×7), `Sparkline`, `OtherMeasurementsCard`; `lib/wording.ts` `changeScoreSummary()` (accessible name) and the intro, forming and caption texts.
- Epoch selection for residents with `epoch_count` > 1 (`getScores({ residentCode, epoch })`, default the current epoch).
- Component tests with the R09, R10, R07, R08 fixtures.

## Out of Scope

- `GET /api/v1/scores`, baseline periods and features (FEAT-034, FEAT-028).
- The Summary tile "Change score <x.x>" (FEAT-066) and the Baseline section text and meter (FEAT-068).
- An EWMA trend or baseline band (FEAT-096, OQ-18).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-067-FR-01 | The section shall start with a panel headed "Change score" (h2) and the line "Goes up when check-ins keep leaning away from <R>’s usual. The alarm turns on at <h>. Missed, set-aside and held-back check-ins leave it unchanged." (14px, `--muted`) with h from `meta.cusum_h` formatted without trailing zeros. | UX-080, FR-167, D-113 |
| FEAT-067-FR-02 | `ChangeScoreChart` shall use Recharts `ComposedChart` with one `Bar` (`dataKey="cusum_tally"`) per scored session of the displayed epoch in time order, height = API `cusum_tally`. | FE-093, UX-081, FR-165 |
| FEAT-067-FR-03 | Bars with `alarm_state` `off` shall be filled `--c-aside`; bars with `rings` or `on` filled `--red`; the colour is chosen from `alarm_state`, never by comparing the value with h, so persistence after the first crossing stays visible. | FE-093, UX-083, FR-165, D-30, D-111 |
| FEAT-067-FR-04 | A leading slot (category placed before the first scored bar, fill `--grey-bg`, full plot height) shall be labelled "Baseline <first date>–<frozen-after date>" from `baseline_periods` (R09 "Baseline Oct 1–16"). | FE-093, UX-082, FR-165, D-111 |
| FEAT-067-FR-05 | A dashed horizontal line (2px, dash 6/4, `--red`) at y = h shall be labelled "Alarm line: <h>" ("Alarm line: 5", 12px, `--red`) at its left end above the line. | FE-093, UX-084, FR-165 |
| FEAT-067-FR-06 | The `rings` bar shall carry a "▲" marker above it and its x tick shall read "<Mon D> · alarm"; the x axis labels at least the first scored date, the alarm date and the last scored date (12px, `--muted`, minimum 48px apart); each bar has the tooltip "<Mon D>: <value>". | FE-094, UX-085, UX-086, FR-166 |
| FEAT-067-FR-07 | A bar with value 0 shall render as a 2px stub in `--rule`; missed, set-aside and held-back days have no bar. | FE-095 |
| FEAT-067-FR-08 | The y axis shall start at 0 with maximum max(1.2 × h, 1.05 × largest value) and ticks every 10 units when the maximum exceeds 20, else every 5, labelled 12px `--muted`. | UX-087 |
| FEAT-067-FR-09 | The chart shall sit in an `overflow-x: auto` container (min width 520px) that is keyboard-focusable with an accessible name; `isAnimationActive={false}` on every Recharts element. | FE-096, FE-099, UX-243, UX-230 |
| FEAT-067-FR-10 | The chart shall have `role="img"` and an `aria-label` from `changeScoreSummary()`: "Change score for <R> from <first Mon D> to <last Mon D>. Baseline <range>. Alarm line <h>. <Crossed the alarm line on <Mon D>; \| Below the alarm line throughout;> now <value>." | FE-097, UX-091 |
| FEAT-067-FR-11 | A `<details>` "Show change score as a table" shall contain `ChangeScoreTable` with columns "Date", "Change score", "Alarm", one row per bar, "Alarm" reading "—" (`off`), "▲ Alarm rings (first crossing)" (`rings`) or "▲ Alarm on" (`on`), values with one decimal; the table has a caption naming the resident. | FE-097, UX-090, TST-112, FR-168 |
| FEAT-067-FR-12 | When the baseline is forming the chart area shall be replaced by "No change score yet. Scoring starts after the baseline is complete (<n> of <N> usable check-ins so far)." | UX-089 |
| FEAT-067-FR-13 | When the current epoch > 1, a line above the chart (14px, `--muted`) shall read "Showing the current device period since <Mon D>. Earlier periods are not scored against this baseline." | UX-092, UX-065 |
| FEAT-067-FR-14 | For a resident with more than one epoch a labelled native `<select>` "Device period" above the chart shall list epochs 1..`epoch_count` (default current; hidden when `epoch_count` is 1); choosing one loads `GET /api/v1/scores?resident_code=<R>&epoch=<n>` and shows that epoch's bars and baseline slot. | FR-172, OQ-28 |
| FEAT-067-FR-15 | A second panel shall have the heading "The 7 voice measurements behind the score" and the intro "Each is compared with <R>’s own baseline. The score rises when the voice is:" (14px, `--muted`). | UX-100, FR-169 |
| FEAT-067-FR-16 | The panel shall show exactly 7 `FeatureCard`s in a grid (min card width 300px, gap 10px; padding 10px 12px; label left, sparkline right) in the order and with the labels Quieter (loudness), Slower to say the phrase (phrase duration), Fewer syllables per second (speech rate), Slower while talking (articulation rate), More pauses (number of pauses), More time in pauses (pause fraction), Less voiced sound (voiced fraction), the technical name in parentheses 14px `--muted`. | UX-101, UX-163, FR-169 |
| FEAT-067-FR-17 | Each sparkline (110 × 28px) shall plot `sign × z` of the scored sessions of the current epoch with a dashed zero line for the resident's own frozen baseline, no axes, grid, tooltip or animation, and have the accessible name "<label> (<technical name>): latest <signed value> compared with own baseline over <k> scored check-ins". | UX-102, UX-103, FE-098 |
| FEAT-067-FR-18 | While the baseline is forming each card shall show "Not scored yet" (12px, `--muted`) with a 1px dashed `--rule` border instead of a sparkline (otherwise 1px solid `--rule`); cards show no per-measurement alarm, threshold or "abnormal" label and no red. | UX-104, UX-105 |
| FEAT-067-FR-19 | An eighth card (background `--surface-2`) shall read "12 other measurements (pitch, jitter, MFCCs and others)" on the left and "Stored, not scored" (14px, `--muted`) on the right, with the number from `stored_feature_keys.length`; those measurements are not listed, plotted or summarised. | UX-106, UX-107, FR-170 |
| FEAT-067-FR-20 | Below the cards the caption (12px, `--muted`) "Measurement names are placeholders until Team 1 confirms the openSMILE output names. Morning check-ins are adjusted before comparing." shall appear. | UX-108, FR-171, OQ-03 |
| FEAT-067-FR-21 | With the reference data the section shall render the Voice trends values of TRD 11 §4.13.3: R09 "Baseline Oct 1–16", 14 bars Oct 17–30 with 3.2, 2.6, 1.8, 1.6 (`--c-aside`), 5.4 (▲, "Oct 21 · alarm"), 8.0, 8.3, 10.7, 12.4, 15.3, 16.7, 18.8, 23.1, 26.8 (`--red`); R10 Oct 17–23 `off`, Oct 24 ▲ 6.0, Oct 25–30 `on` ending 13.4; R07 the device-period line, "Baseline Oct 13–28" and two stubs; R08 the forming text and "Not scored yet" on all 7 cards. | UX-262 (values), FR-165 |

## Inputs

- `GET /api/v1/scores?resident_code=<R>&epoch=<n>` → `ScoresResponse` (`items: ScoreRow[]` with `cusum_tally`, `alarm_state`, local date; `baseline_periods[]`; `meta`).
- `GET /api/v1/residents/{code}/features` → `FeaturesResponse` (`scored_features[7]` with `label`, `composite_sign`, `points[{z, …}]`, `stored_feature_keys[12]`).
- `ResidentDetail` (`current_epoch`, `epoch_count`, baseline state and progress, epoch start) from FEAT-066's layout query; `meta.cusum_h`, `meta.facility_tz`, `meta.baseline_n`.

## Outputs

- Rendered Change score panel (chart, intro, device-period line, epoch selector, disclosure table, forming text) and measurement panel (7 cards, eighth card, caption).

## Data Flow

`["resident", code, "scores", epoch]` → points (scored sessions in time order) and baseline period → `ChangeScoreChart` (bars coloured by `alarm_state`, baseline slot, reference line, marker) and `ChangeScoreTable` (same points, `formatTally`, `formatLocalDate`). `["resident", code, "features"]` → `MeasurementCards` → `FeatureCard` ×7 (label, sign, series of `z`) + `OtherMeasurementsCard` (stored keys).

## Dependencies

Required before implementation (BACKLOG.md): FEAT-066, FEAT-034

- FEAT-066 provides the chart layout, the resident query and the `/trends` route shell (the features endpoint of FEAT-028 is reached through FEAT-066).
- FEAT-034 provides `GET /api/v1/scores` with `baseline_periods`.

Features that build directly on this one (BACKLOG.md §4): FEAT-075, FEAT-096.

## Database Impact

None (frontend only).

## API Impact

Endpoints consumed: `GET /api/v1/scores` (E-12) with `resident_code` and optional `epoch`; `GET /api/v1/residents/{resident_code}/features` (E-11). None exposed.

## Frontend Impact

- Section page `app/(protected)/residents/[residentCode]/trends/page.tsx`.
- Components: `ChangeScoreChart`, `ChangeScoreTable`, `MeasurementCards`, `FeatureCard`, `Sparkline`, `OtherMeasurementsCard`; wording helper `changeScoreSummary()`.

## Analytics Impact

None. Change score values, alarm states and z values are rendered as returned (no client CUSUM computation; the UI multiplies `z` by `composite_sign` for display only; one-decimal display, NFR-037).

## Security Requirements

None beyond the page's authenticated, client-side fetching (FE-040); API strings rendered as text (SEC-076).

## Error Handling

- Scores query error → error state only in the Change score panel; features query error → error state only in the measurement panel (FE-087, UX-202).
- No scored sessions and baseline frozen → chart with baseline slot and no bars; forming → forming text (UX-089).

## Logging Requirements

None in the frontend.

## Testing Requirements

- Component (`components/ChangeScoreChart/ChangeScoreChart.test.tsx`): TST-093 assertions on the R09 fixture — 14 bars, first 4 `--c-aside`, last 10 `--red`, slot "Baseline Oct 1–16", reference line at 5 labelled "Alarm line: 5", tick "Oct 21 · alarm", accessible name (FE-183); R07 stubs; R10 colouring; y-axis ticks every 10 for R09.
- Component (`components/ChangeScoreTable/ChangeScoreTable.test.tsx`): 14 rows with 3.2, 2.6, 1.8, 1.6, 5.4, 8.0, 8.3, 10.7, 12.4, 15.3, 16.7, 18.8, 23.1, 26.8 (FE-184); "Change score" column header; alarm column texts.
- Component (`FeatureCard`, `Sparkline`, `OtherMeasurementsCard`, TST-090): order and labels, signed series, accessible name, "Not scored yet" with dashed border, eighth card text and count, caption.
- Accessibility: TST-112 table reachable by screen reader (RTL and axe).
- E2E: E2E-08 (R09 Voice trends), E2E-10 (R07 epoch 2 only with 2 bars), E2E-11 (R08 forming), as updated in TRD 13 Table 4.10-A for v0.2.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-067-AC-01 | The R09 `ChangeScoreChart` renders 14 bars: Oct 17–20 filled `--c-aside`, Oct 21–30 filled `--red`, a dashed line at y = 5 labelled "Alarm line: 5", a "Baseline Oct 1–16" slot, "▲" on Oct 21 and the tick "Oct 21 · alarm". | FE-183; TST-093; AC-UX-04 |
| FEAT-067-AC-02 | The R09 `ChangeScoreTable` lists 14 rows with change scores 3.2, 2.6, 1.8, 1.6, 5.4, 8.0, 8.3, 10.7, 12.4, 15.3, 16.7, 18.8, 23.1, 26.8 and Oct 21 marked "▲ Alarm rings (first crossing)". | FE-184; UX-090 |
| FEAT-067-AC-03 | The R09 chart's accessible name equals "Change score for R09 from Oct 17 to Oct 30. Baseline Oct 1–16. Alarm line 5. Crossed the alarm line on Oct 21; now 26.8." Verified by: Component (`ChangeScoreChart.test.tsx`; TST-093). | UX-091; FE-097 |
| FEAT-067-AC-04 | `/residents/R07/trends` shows "Showing the current device period since Oct 13. Earlier periods are not scored against this baseline.", "Baseline Oct 13–28" and 2 bars drawn as stubs. | E2E-10; UX-092; FE-095 |
| FEAT-067-AC-05 | `/residents/R08/trends` shows "No change score yet. Scoring starts after the baseline is complete (13 of 16 usable check-ins so far).", no bars, and "Not scored yet" on all 7 cards. | E2E-11; UX-089; UX-104; AC-UX-05 |
| FEAT-067-AC-06 | `/residents/R09/trends` shows the 7 cards with the §4.5.4 labels in order, the card "12 other measurements (pitch, jitter, MFCCs and others)" / "Stored, not scored" and the placeholder caption. | E2E-08; UX-101; UX-106; UX-108 |
| FEAT-067-AC-07 | For R07, selecting epoch 1 requests `GET /api/v1/scores?resident_code=R07&epoch=1` and renders no bars (epoch 1 never formed). Verified by: Page test (TST-094). | FR-172 |
| FEAT-067-AC-08 | axe reports no serious or critical violation on `/residents/R09/trends`, and the table has role `table` with a caption naming R09. | TST-112; TST-110 |

## Definition of Done

- All FEAT-067 acceptance criteria pass; component and E2E tests green.
- R09 Voice trends shows "Alarm line: 5", the grey baseline slot and red post-alarm bars, 7 measurement cards plus the "12 other measurements" card (TRD 25 Phase 8 DoD, as updated for v0.2).
- Batch report lists IDs (AGT-022).

## Implementation Notes

- Implement the baseline slot as the categorical x value `"__baseline__"` before the first scored date and keep it even with many scored sessions (TRD 04 §8).
- Bars follow `alarm_state` from `/scores`; after a first crossing bars stay red even if the value drops below h (TRD 11 §8, D-03). The wireframe colours bars by ≥ 5, which gives the same result on the test data; the bar heights of SRC-21 are approximate and the SRC-03 values are binding (TRD 11 §4.13.3).
- Missed days have no bar (TRD 11 §8); never draw zero-height bars for non-scored days.
- FR-172 (Should, earlier epoch view) is TRD 24 OQ-28; the "Device period" select is its interim decision.
- Labels for the 7 cards come from the API `label` where it matches TRD 11 §4.5.4; split "Quieter (loudness)" into label and technical name.
- The file name keeps the v0.1 title (feature IDs and file names are never renamed, TRD 25 §4.2).
