# FEAT-068 Check-in log

| Field | Value |
|---|---|
| Epic | Frontend |
| Build phase | Phase 8 (TRD 25) |
| Priority | P1 |
| Complexity | Low |
| MVP status | Required |
| Dependencies | FEAT-066 |
| Status | Not Started |

## Purpose

Implement `CheckinLog`, the right-hand "Check-in log" section of Resident detail (SRC-10): one line per event, newest first and in the order the API returns them, as "<Mon D> · <event> · <detail>" — alarm on, watching started, baseline complete, baseline restarted (with cause), set aside (with the pipeline's reasons), quarantined, missed and device silent — with date-range paging ("Show earlier entries"), never any duplicate or ordinary usable check-in, the legend line and the empty state.

## Business Context

- BR-13 (staff see what happened and when), BR-04, BR-05, BR-06, BR-08 (set-aside, quarantine, missed days, device changes are visible with their reasons), BR-03 (duplicates never shown).
- D-67: usable check-ins are not log events; the log keeps the wireframe event set.
- FRs covered (BACKLOG.md): FR-180, FR-181, FR-182, FR-183.

## Referenced TRDs

- TRD 04 FE-101 (render API order as a `<ul>` with TRD 11 wording), §4.8 `CheckinLog` (`{ events, h, tz, residentCode }`), §4.6.2 `getCheckins(code, { from?, to? })`, FE-186.
- TRD 11 UX-140..UX-150 (placement, ordering, line texts by event type and restart cause, included events, no usable/duplicate lines, quarantine text, 30-day window and "Show earlier entries", no colour reliance, legend, empty state, missed days exactly as ledger), §4.5.6 table, §4.13.3 expected lines.
- TRD 19 E-10 `GET /api/v1/residents/{resident_code}/checkins` (`CheckinEvent`: `local_date`, `event_type`, `detail`, `restart_cause`, `previous_device_code`, `from_value`, `to_value`).
- TRD 02 FR-180..FR-183; TRD 24 D-67.
- TRD 13 E2E-08, E2E-10, E2E-11, E2E-12; TST-090.

## Scope

- `components/CheckinLog/` rendering the events of `getCheckins` on `/residents/[residentCode]`.
- Line wording in `lib/wording.ts` for every `CheckinEventType` and restart cause.
- Initial window: last 30 days ending on the as-of date; "Show earlier entries" loads the previous 30 days via `from`/`to`.
- Legend line and empty state.

## Out of Scope

- Event derivation and ordering (backend FEAT-028, TRD 06 DB-065).
- Staff notes and reviews (FEAT-071) — they are not log events.
- The tally chart (FEAT-067).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-068-FR-01 | The "Check-in log" section shall be the right column of the review row with heading "Check-in log" and one `<li>` per event (15px, 1px rule bottom border, padding-bottom 8px). | UX-140, FE-101 |
| FEAT-068-FR-02 | Events shall be rendered in the order returned by the API (newest local date first; same-date order alarm, watching_started, baseline_complete, baseline_restarted, quarantined, set_aside, device_silent, missed); the frontend shall not re-sort. | UX-141, FE-101, FR-180 |
| FEAT-068-FR-03 | Lines shall use: alarm_on "<Mon D> · Alarm on · tally crossed <h>"; watching_started "<Mon D> · Watching started"; baseline_complete "<Mon D> · Baseline complete (<N> of <N>)"; baseline_restarted by `restart_cause` — device "<Mon D> · Baseline restarted · new device <D> (was <previous_device_code>)", firmware "… · device firmware changed (<from_value> to <to_value>)", software "… · extraction software changed (<from_value> to <to_value>)"; set_aside "<Mon D> · Set aside · <pipeline reasons>"; quarantined "<Mon D> · Quarantined · possible other speaker"; missed "<Mon D> · Missed · no check-in received"; device_silent "<Mon D> · Device silent · no record from any resident on shared device <D>". | UX-142, FR-180, FR-181 |
| FEAT-068-FR-04 | Set-aside reasons shall be the pipeline reason text verbatim in the fixed order quality flag, noise, speech duration joined by "; " (e.g. "quality flag poor; noise above limit"). | UX-142, BR-04 |
| FEAT-068-FR-05 | The quarantined line shall show only "possible other speaker", never the screen statistics. | UX-145 |
| FEAT-068-FR-06 | The log shall include alarms, set-asides, quarantines, missed days (resident and device-gap), baseline restarts, baseline complete and watching started; ordinary usable check-ins and duplicates shall never appear. | UX-143, UX-144, FR-181, FR-182, D-67 |
| FEAT-068-FR-07 | The log shall first show events of the 30 days ending on the as-of date and offer "Show earlier entries", which loads the previous 30 days through `GET /checkins?from=&to=` when earlier events exist. | UX-146, FR-183 |
| FEAT-068-FR-08 | No line shall rely on colour; the alarm line begins its status text with "Alarm on". | UX-147, UX-004 |
| FEAT-068-FR-09 | Below the events the legend "Other residents’ logs can also show: set aside (noise, quality flag, too short) · quarantined (possible other speaker) · missed · device silent · baseline restarted (new device)" shall appear (14px, secondary). | UX-148 |
| FEAT-068-FR-10 | With no events the log shall read "Nothing to report yet." followed by the legend. | UX-149, UX-204 |
| FEAT-068-FR-11 | Missed days shall be exactly the ledger's missed days, never filled with a value, a previous check-in or an estimate. | UX-150, UX-047 |
| FEAT-068-FR-12 | `h` in the alarm line and `N` in "Baseline complete" shall come from `meta` / the event detail, never hard-coded. | FE-077, UX-007 |

## Inputs

- `GET /api/v1/residents/{code}/checkins?from=<date>&to=<date>` → `CheckinEventList` (newest first) with `meta`.
- `meta.cusum_h`, `meta.facility_tz`, `meta.as_of`.

## Outputs

- Rendered log list, legend, "Show earlier entries" button, empty state.

## Data Flow

Page query `["resident", code, "checkins"]` (initial window) → `CheckinLog` maps each `CheckinEvent` to its wording template with `formatLocalDate` → "Show earlier entries" → additional query with the previous 30-day `from`/`to` → appended below.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-066

- FEAT-066 provides the Resident detail page and its parallel `getCheckins` query; the endpoint itself is FEAT-028 (via FEAT-066).

Features that build directly on this one (BACKLOG.md §4): FEAT-075.

## Database Impact

None (frontend only).

## API Impact

Endpoint consumed: `GET /api/v1/residents/{resident_code}/checkins` (E-10) with optional `from`, `to`. None exposed.

## Frontend Impact

- Component: `CheckinLog` on `app/(protected)/residents/[residentCode]/page.tsx`; templates in `lib/wording.ts`.

## Analytics Impact

None.

## Security Requirements

- API detail strings rendered as text only (SEC-076); no PII in events.

## Error Handling

- Check-ins query error → error state in this section only (FE-087).
- "Show earlier entries" failure → section error with "Try again"; already shown events remain.

## Logging Requirements

None in the frontend.

## Testing Requirements

- Component (`components/CheckinLog/CheckinLog.test.tsx`, TST-090): each event type and restart cause renders its exact line; quarantined line hides statistics; no usable or duplicate events; empty state with legend.
- Page test: section error isolation (TST-094).
- E2E: E2E-08 (R09 "Oct 21 · Alarm on · tally crossed 5.0", "Oct 17 · Watching started", "Oct 16 · Baseline complete (16 of 16)"), E2E-10 (R07 restart Oct 13 and baseline complete Oct 28), E2E-11 (R08 12 missed and 5 set-aside entries), E2E-12 (R03 Oct 18 set aside reasons and Oct 12 device silent); FE-186 first three lines for R09, R10, R08, R07.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-068-AC-01 | `/residents/R09` log starts with "Oct 21 · Alarm on · tally crossed 5.0", "Oct 17 · Watching started", "Oct 16 · Baseline complete (16 of 16)". | E2E-08; AC-FE-03; UX-262 |
| FEAT-068-AC-02 | `/residents/R07` log contains "Oct 13 · Baseline restarted · new device D07B (was D07)" and "Oct 28 · Baseline complete (16 of 16)". | E2E-10; AC-UX-05 |
| FEAT-068-AC-03 | `/residents/R08` log contains 12 "Missed · no check-in received" lines and 5 "Set aside" lines, newest first starting "Oct 29 · Set aside · speech too short". | E2E-11; TRD 11 §4.13.3 |
| FEAT-068-AC-04 | `/residents/R03` log contains "Oct 18 · Set aside · quality flag poor; noise above limit" and "Oct 12 · Device silent · no record from any resident on shared device D02". | E2E-12 |
| FEAT-068-AC-05 | No log line exists for a usable check-in or a duplicate (R04 log shows no entry for its duplicate arrivals). Verified by: Component (`components/CheckinLog/CheckinLog.test.tsx`). | UX-144; FR-182 |
| FEAT-068-AC-06 | A resident fixture with no events shows "Nothing to report yet." followed by the legend line. Verified by: Component (`components/CheckinLog/CheckinLog.test.tsx`). | UX-149 |

## Definition of Done

- All FEAT-068 acceptance criteria pass; component and E2E tests green.
- Batch report lists IDs (AGT-022).

## Implementation Notes

- Branch the baseline_restarted wording on `restart_cause`, not on detail text (UX-142).
- Use `formatLocalDate` (string split, no `Date` parsing) for "<Mon D>" (TRD 04 §8).
- The API `detail` for set_aside is the pipeline reason text; for missed and device_silent the UI uses the TRD 11 line text, not the API detail ("no record received"), as the table of §4.5.6 defines.
