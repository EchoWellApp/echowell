# FEAT-068 Check-in log and Baseline sections of the resident chart

| Field | Value |
|---|---|
| Epic | Frontend |
| Build phase | Phase 8 (TRD 25) |
| Priority | P1 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-066 |
| Status | Not Started |

## Purpose

Implement two sections of the resident chart as wireframe v0.2 draws them (SRC-21, TRD 24 D-110). "Check-in log" (`/residents/[residentCode]/log`): the panel "Check-ins, last 30 days" with the four counts Used, Set aside (noise, poor quality or too short), Held back (possible other voice) and Missed, and the panel "Events" with one row per event, newest first — alarm on, comparing with baseline started, baseline complete, baseline restarted (by cause), check-in set aside (with the pipeline's reasons), check-in held back, check-in missed, shared device silent and the new "Check-ins started" event (TRD 24 D-113) — with date-range paging ("Show earlier entries"), never any duplicate or ordinary usable check-in, the caption "Duplicate records are removed quietly and not shown." and the empty state. "Baseline" (`/residents/[residentCode]/baseline`): the panel "Baseline: <R>’s usual" with the frozen, forming or restarted baseline text, the progress meter and the explanation of how the baseline is built and when it restarts (the v0.1 header baseline line and `<progress>` move here, UX-064 → UX-422).

## Business Context

- BR-13 (staff see what happened and when), BR-04, BR-05, BR-06, BR-08 (set-aside, held-back, missed days and device changes visible with their reasons), BR-03 (duplicates never shown): "See missed and set-aside check-ins" on the Summary of a Needs-attention resident leads to the log.
- BR-09 (frozen personal baseline) and BR-08 (restart on device, firmware or software change): the Baseline section states exactly what the resident is compared with.
- D-67: usable check-ins are not log events; D-113: UI wording "held back", "change score", "Comparing with baseline started" and the derived `checkins_started` event.
- FRs covered (BACKLOG.md): FR-135, FR-162, FR-163, FR-180, FR-181, FR-182, FR-183.

## Referenced TRDs

- TRD 11 (v0.13) — owned by this feature: UX-047, UX-048 (missed days as counted, counts equal the API), §4.3.5 count semantics, UX-140..UX-150 (counts and events panels, ordering, line texts by event type and restart cause, included events, no usable or duplicate lines, held-back text, 30-day window and "Show earlier entries", no colour reliance, caption, empty state, missed days exactly as ledger), §4.5.6 table, UX-066 (baseline dates stable after freeze), UX-420..UX-423 (Baseline panel, text templates §4.5.7.1, meter, explanation), log, counts and Baseline values of §4.13.3. Retired here: UX-064 (replaced by UX-422).
- TRD 04 FE-101 (render API order as a list with TRD 11 wording), §4.8 `CheckinCounts`, `CheckinLog` (`{ events, h, tz, residentCode }`), `BaselinePanel`, §4.6.2 `getCheckins(code, { from?, to? })`, FE-186 (as updated for wireframe v0.2).
- TRD 19 E-10 `GET /api/v1/residents/{resident_code}/checkins` (`CheckinEvent`: `local_date`, `event_type` incl. `checkins_started`, `detail`, `restart_cause`, `previous_device_code`, `device_code`, `from_value`, `to_value`; D-114), E-09 (`last_30_days`, baseline fields, epoch).
- TRD 02 FR-135, FR-162, FR-163, FR-180..FR-183; TRD 24 D-67, D-113, D-114.
- TRD 13 E2E-08, E2E-10, E2E-11, E2E-12; TST-090.

## Scope

- `app/(protected)/residents/[residentCode]/log/page.tsx`: `CheckinCounts` (from the resident query of FEAT-066) and `CheckinLog` (query `getCheckins`), caption, "Show earlier entries".
- `app/(protected)/residents/[residentCode]/baseline/page.tsx`: `BaselinePanel` (from the resident query).
- Line wording in `lib/wording.ts` for every `CheckinEventType` and restart cause, and the baseline templates of §4.5.7.1.
- Initial log window: last 30 days ending on the as-of date; "Show earlier entries" loads the previous 30 days via `from`/`to`.

## Out of Scope

- Event derivation (including `checkins_started`), counts and ordering (backend FEAT-028, TRD 06 DB-065); baseline computation (FEAT-045).
- Staff notes and reviews (FEAT-069, FEAT-071) — they are not log events.
- The change score chart (FEAT-067); the banner "Baseline" fact (FEAT-066); device history (FEAT-070).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-068-FR-01 | The Check-in log section shall start with a panel headed "Check-ins, last 30 days" showing four count tiles (grid, min width 150px; number 24px weight 700 above its label) "Used", "Set aside (noise, poor quality or too short)", "Held back (possible other voice)", "Missed", equal to the API `last_30_days` values (missed = `missing_resident` + `missing_device_gap`; duplicates never counted). | UX-140, UX-047, UX-048, §4.3.5, FR-135 |
| FEAT-068-FR-02 | A panel headed "Events" shall follow with one row per event (grid: 80px `--muted` date column "<Mon D>", text column; 1px solid `--rule` bottom border, padding 10px 0). | UX-140, FE-101 |
| FEAT-068-FR-03 | Events shall be rendered in the order returned by the API (newest local date first; same-date order alarm_on, watching_started, baseline_complete, baseline_restarted, quarantined, set_aside, device_silent, missed, checkins_started); the frontend shall not re-sort. | UX-141, FE-101, FR-180 |
| FEAT-068-FR-04 | Lines shall use: alarm_on "Alarm on. Change score crossed <h>."; watching_started "Comparing with baseline started."; baseline_complete "Baseline complete (<N> of <N>)."; baseline_restarted by `restart_cause` — device "New device <D>. Baseline restarted.", firmware "Device firmware changed (<from> to <to>). Baseline restarted.", software "Extraction software changed (<from> to <to>). Baseline restarted."; set_aside "Check-in set aside: <pipeline reasons>."; quarantined "Check-in held back: possible other voice."; missed "Check-in missed."; device_silent "Shared device <D> silent all day. Check-in missed."; checkins_started "Check-ins started." or, when the first record came from a device other than the current one, "Check-ins started on <D>." | UX-142, FR-180, FR-181, D-113 |
| FEAT-068-FR-05 | Set-aside reasons shall be the pipeline reason text verbatim in the fixed order quality flag, noise, speech duration joined by "; " (e.g. "quality flag poor; noise above limit"). | UX-142, BR-04 |
| FEAT-068-FR-06 | The held-back line shall show only "possible other voice", never the screen statistics. | UX-145 |
| FEAT-068-FR-07 | The log shall include alarms, set-asides, hold-backs, missed days (resident and device-gap), baseline restarts, baseline complete, comparing started and check-ins started; ordinary usable check-ins and duplicates shall never appear. | UX-143, UX-144, FR-181, FR-182, D-67 |
| FEAT-068-FR-08 | The log shall first show events of the 30 days ending on the as-of date and offer "Show earlier entries", which loads the previous 30 days through `GET /checkins?from=&to=` when earlier events exist. | UX-146, FR-183 |
| FEAT-068-FR-09 | No line shall rely on colour; each line's text names its type. | UX-147, UX-004 |
| FEAT-068-FR-10 | Below the events the caption (14px, `--muted`) "Duplicate records are removed quietly and not shown." shall appear; with no events the Events panel reads "Nothing to report yet." followed by the caption. | UX-148, UX-149, UX-204 |
| FEAT-068-FR-11 | Missed days shall be exactly the ledger's missed days, never filled with a value, a previous check-in or an estimate. | UX-150, UX-047 |
| FEAT-068-FR-12 | h in the alarm line and N in "Baseline complete" shall come from `meta` and the event, never hard-coded. | FE-077, UX-007 |
| FEAT-068-FR-13 | The Baseline section shall show a panel headed "Baseline: <R>’s usual" (h2) whose first paragraph uses the §4.5.7.1 templates: frozen with scored sessions "First <N> usable check-ins, <first>–<frozen-after>, then frozen. Compared with it since <first scored date>."; frozen without scored session "… then frozen. Comparing starts with the next usable check-in."; forming "Still forming: <n> of <N> usable check-ins so far." plus, when missed or set-aside check-ins occurred in the current epoch, " <m> missed and <s> set-aside check-ins have slowed it down."; with the restart prefix by cause when the current epoch > 1 ("Restarted <Mon D> when the device was replaced (<old D> to <D>), so readings from the old device are not mixed in. ", firmware and software variants). | UX-420, UX-421, UX-065, FR-162, FR-163 |
| FEAT-068-FR-14 | A native `<progress>` (max N, value n, height 14px, full width, accessible name "<n> of <N> usable check-ins") shall follow, with the caption "<n> of <N> usable check-ins" (14px, `--muted`). | UX-422, FR-163 |
| FEAT-068-FR-15 | The panel shall end with the explanation (14px, `--muted`) "The baseline is built from the first <N> usable check-ins, then frozen so slow changes still show up. It restarts if the resident gets a new device or the device or extraction software changes." | UX-423 |
| FEAT-068-FR-16 | Baseline dates and the frozen state shall be rendered only from the API (`first_session_date`, `frozen_after_date`, first scored date) and never change after freeze across reloads and later check-ins of the same epoch. | UX-066 |
| FEAT-068-FR-17 | With the reference data the sections shall render the counts, log lines and Baseline texts of TRD 11 §4.13.3. | UX-262 (values) |

## Inputs

- `GET /api/v1/residents/{code}/checkins?from=<date>&to=<date>` → `CheckinEventList` (newest first) with `meta`.
- `ResidentDetail` from FEAT-066's layout query: `last_30_days`, baseline (`first_session_date`, `frozen_after_date`, n, frozen), first scored date, `current_epoch`, epoch start, `restart_cause`, previous device, from/to values, missed and set-aside counts of the current epoch; `meta.cusum_h`, `meta.baseline_n`, `meta.facility_tz`, `meta.as_of`.

## Outputs

- Rendered counts panel, events list, caption, "Show earlier entries" button, empty state; Baseline panel with text, meter and explanation.

## Data Flow

Log: resident query → `CheckinCounts`; `["resident", code, "checkins"]` (initial window) → `CheckinLog` maps each `CheckinEvent` to its wording template with `formatLocalDate` → "Show earlier entries" → additional query with the previous 30-day `from`/`to` → appended below. Baseline: resident query → `BaselinePanel` (template chosen from frozen/forming/epoch/cause; meter n of N).

## Dependencies

Required before implementation (BACKLOG.md): FEAT-066

- FEAT-066 provides the chart layout, the resident query and the `/log` and `/baseline` route shells; the endpoints are FEAT-028 (via FEAT-066).

Features that build directly on this one (BACKLOG.md §4): FEAT-075.

## Database Impact

None (frontend only).

## API Impact

Endpoints consumed: `GET /api/v1/residents/{resident_code}/checkins` (E-10) with optional `from`, `to`; `GET /api/v1/residents/{resident_code}` (E-09, through FEAT-066). None exposed.

## Frontend Impact

- Section pages `app/(protected)/residents/[residentCode]/log/page.tsx` and `.../baseline/page.tsx`.
- Components: `CheckinCounts`, `CheckinLog`, `BaselinePanel`; templates in `lib/wording.ts`.

## Analytics Impact

None. Counts, events and baseline facts come from the API.

## Security Requirements

- API detail strings rendered as text only (SEC-076); no PII in events.

## Error Handling

- Check-ins query error → error state in the Events panel only; the counts panel stays (FE-087, UX-202).
- "Show earlier entries" failure → error with "Try again"; already shown events remain.

## Logging Requirements

None in the frontend.

## Testing Requirements

- Component (`components/CheckinLog/CheckinLog.test.tsx`, TST-090): each event type and restart cause renders its exact line, including "Check-ins started." and "Check-ins started on D07."; held-back line hides statistics; no usable or duplicate events; caption; empty state with caption.
- Component (`CheckinCounts`, `BaselinePanel`): four counts and labels; every §4.5.7.1 template incl. restart prefixes and the "slowed it down" clause; meter value, max and accessible name; explanation.
- Page test: panel error isolation (TST-094).
- E2E (FE-186): E2E-08 (R09 log and Baseline), E2E-10 (R07 restart and "Check-ins started on D07."), E2E-11 (R08 counts 13 / 5 / 0 / 12, set-aside and missed lines, forming Baseline text), E2E-12 (R03 set-aside reasons and the D02 silent day), as updated in TRD 13 Table 4.10-A for v0.2.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-068-AC-01 | `/residents/R09/log` shows the counts 30 / 0 / 0 / 0 and starts with "Oct 21 Alarm on. Change score crossed 5.", "Oct 17 Comparing with baseline started.", "Oct 16 Baseline complete (16 of 16)." and ends with "Oct 1 Check-ins started." | E2E-08; AC-UX-04; UX-142 |
| FEAT-068-AC-02 | `/residents/R07/log` contains "Oct 29 Comparing with baseline started.", "Oct 28 Baseline complete (16 of 16).", "Oct 13 New device D07B. Baseline restarted." and "Oct 1 Check-ins started on D07." | E2E-10; AC-UX-05 |
| FEAT-068-AC-03 | `/residents/R08/log` shows the counts Used 13, Set aside 5, Held back 0, Missed 12, 12 "Check-in missed." lines and 5 set-aside lines, newest first starting "Oct 29 Check-in set aside: speech too short." | E2E-11; UX-048; TRD 11 §4.13.3 |
| FEAT-068-AC-04 | `/residents/R03/log` contains "Oct 18 Check-in set aside: quality flag poor; noise above limit." and "Oct 12 Shared device D02 silent all day. Check-in missed."; `/residents/R05/log` contains "Oct 22 Check-in held back: possible other voice." | E2E-12; UX-145 |
| FEAT-068-AC-05 | No log line exists for a usable check-in or a duplicate (R04 shows no entry for its duplicate arrivals), and the caption "Duplicate records are removed quietly and not shown." is shown under the events. Verified by: Component (`CheckinLog.test.tsx`). | UX-144; UX-148; FR-182 |
| FEAT-068-AC-06 | `/residents/R09/baseline` shows "Baseline: R09’s usual", "First 16 usable check-ins, Oct 1–16, then frozen. Compared with it since Oct 17.", a meter 16 of 16 with the caption "16 of 16 usable check-ins" and the explanation of UX-423. | E2E-08; UX-420..UX-423 |
| FEAT-068-AC-07 | `/residents/R08/baseline` shows "Still forming: 13 of 16 usable check-ins so far. 12 missed and 5 set-aside check-ins have slowed it down." and a `<progress>` 13/16 named "13 of 16 usable check-ins"; `/residents/R07/baseline` shows "Restarted Oct 13 when the device was replaced (D07 to D07B), so readings from the old device are not mixed in. First 16 usable check-ins, Oct 13–28, then frozen. Compared with it since Oct 29." | E2E-10; E2E-11; AC-UX-05 |
| FEAT-068-AC-08 | A resident fixture with no events shows "Nothing to report yet." followed by the caption. Verified by: Component (`CheckinLog.test.tsx`). | UX-149 |

## Definition of Done

- All FEAT-068 acceptance criteria pass; component and E2E tests green.
- Batch report lists IDs (AGT-022).

## Implementation Notes

- Branch the baseline_restarted wording on `restart_cause`, not on detail text (UX-142).
- `checkins_started` is derived on read by the API (local date of the resident's first non-duplicate record in the enrolment, with its `device_code`; D-114); print "on <D>" only when that device differs from the current one.
- Use `formatLocalDate` (string split, no `Date` parsing) for "<Mon D>" (TRD 04 §8).
- The API `detail` for set_aside is the pipeline reason text; for missed and device_silent the UI uses the TRD 11 line text, not the API detail.
- The v0.1 legend line "Other residents’ logs can also show: …" is not built; the caption of UX-148 replaces it.
- The file name keeps the v0.1 title (feature IDs and file names are never renamed, TRD 25 §4.2).
