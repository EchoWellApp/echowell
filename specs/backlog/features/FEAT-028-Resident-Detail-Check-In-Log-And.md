# FEAT-028 Resident detail, check-in log and features APIs

| Field | Value |
|---|---|
| Epic | Backend API |
| Build phase | Phase 5 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-027 |
| Status | Not Started |

## Purpose

Serve everything the Resident detail page (`/residents/[residentCode]`, SRC-10) needs except the tally series and notes: the header and baseline facts with structured "What this means" facts (`GET /residents/{resident_code}`), the newest-first check-in log of meaningful events (`/checkins`), and the 7 scored measurements with raw, adjusted and z values plus the 12 stored-not-scored keys (`/features`). Clinicians open this page from the overview to understand why a resident has an alarm, how the baseline was formed and what happened day by day.

## Business Context

- BR-13 (resident detail with baseline, alarm, measurements and log): header, explanation facts, check-in log and measurement series of SRC-10.
- BR-09 (frozen personal baseline): baseline state, first and frozen-after sessions and dates, forming progress.
- BR-08 (device moves restart the baseline): `baseline_restarted` events with restart cause derived on read.
- BR-04, BR-05, BR-06, BR-11: set-aside, quarantined, missed, device-silent and alarm events appear in the log; duplicates never (BR-03).
- BR-18: the API returns facts only, no clinical prose (OQ-12).
- FRs covered (BACKLOG.md): FR-161, FR-162, FR-163, FR-172, FR-173, FR-180, FR-181, FR-182, FR-183.

## Referenced TRDs

- TRD 05 API-075 (detail), API-076 (facts, no prose), API-077 (check-in log), API-078 (features), API-093 (date parameters), API-094 (time formats), API-057, API-069 (meta, as-of), API-100 (list envelope), API-121 (latency).
- TRD 19 §4.3 E-09, E-10, E-11; schemas `ResidentDetail`, `EpochInfo`, `BaselineInfo`, `DeviceRef`, `Explanation`, `CheckinEvent`, `CheckinEventList`, `CheckinEventType`, `RestartCause`, `FeaturesResponse`, `FeatureSeries`, `FeaturePoint`, `ScoredFeatureKey`, `FeatureKey`.
- TRD 23 §4.4.1 (watching since, alarm since, baseline dates, last check-in), §4.4.3 (display status), §4.4.4 (check-in log events), DME-010 (baseline state), DME-012.
- TRD 06 DB-065 (restart cause derived on read).
- TRD 11 §4.5.2.1 (situations the explanation facts must support), §4.5.4 (labels of the 7 measurements), §4.5.6 (check-in log).
- TRD 08 BSC-037, BSC-039 (unsigned z, 12 features not scored); TRD 09 CUS-020 (alarm while open or acknowledged).
- TRD 13 AC-API-03; TRD 14 TDV-066; TRD 13 §4.10 E2E-08, E2E-10, E2E-11, E2E-12.
- TRD 24 D-41 (watching since), D-64 (restart and in-use fields derived on read), D-67 (check-in log event set; usable check-ins are not events).

## Scope

- Handlers in `backend/api/residents.py`: `GET /api/v1/residents/{resident_code}` (`resident_service.detail`), `GET /api/v1/residents/{resident_code}/checkins` (`checkin_service.list_events`), `GET /api/v1/residents/{resident_code}/features` (`feature_service.series`).
- Detail DTO assembly including `device` (`DeviceRef` with `shared_with`), `current_epoch` (`EpochInfo`), `epoch_count`, `baseline` (`BaselineInfo`), `watching_since`, `alarm_since`, `open_alert_id`, `current_tally`, last check-in, `last_30_days` and `explanation` facts.
- Check-in log event builder for the 8 event types with `from`/`to` filters, newest-first order and pagination.
- Feature series builder for the 7 composite features in contract §6 order and the list of 12 stored-not-scored keys.

## Out of Scope

- Tally series and baseline periods for the chart, including earlier epochs (`GET /scores`, FEAT-034); staff notes (FEAT-033); alerts list and reviews (FEAT-030, FEAT-031).
- The detail page, `ResidentHeader`, `WhatThisMeans`, `CheckinLog`, `FeatureCard`, `Sparkline`, `OtherMeasurementsCard` and all wording (FEAT-066, FEAT-068).
- Derivation queries shared with the overview (FEAT-014) and the display-status function (FEAT-027).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-028-FR-01 | `GET /residents/{resident_code}` shall return `ResidentDetail` for any resident including withdrawn ones; an unknown code (or one not matching `^[A-Z0-9]{1,16}$`) returns 404 `RESIDENT_NOT_FOUND`. | API-075; FR-173; TRD 19 E-09 |
| FEAT-028-FR-02 | `status` shall be computed by the FEAT-027 display-status function; `alarm_since` and `open_alert_id` refer to the non-closed alert of the current epoch; `current_tally` is `cusum_state.current_tally` of the current epoch (null when no epoch). | FR-161, CUS-020, TRD 23 §4.4.1 |
| FEAT-028-FR-03 | `device` shall give the device on the as-of local date, `shared`, `shared_with` (other residents assigned to it that day) and `previous_device_code`; `current_epoch` the epoch with `ended_at IS NULL` (device, firmware, software, `started_at`, `started_on`) or null; `epoch_count` the number of epochs of the resident. | FR-161, FR-172; TRD 19 `DeviceRef`, `EpochInfo` |
| FEAT-028-FR-04 | `baseline` shall be `{state: forming\|frozen, n_usable, n_required, first_session_id, frozen_after_session_id, first_local_date, frozen_after_local_date}` for the current epoch; ids and dates are null while forming; `state` never returns from `frozen` to `forming` within an epoch. | FR-162, FR-163, DME-010; TRD 19 `BaselineInfo` |
| FEAT-028-FR-05 | `watching_since` shall be the local date of the first scored session of the current epoch or, before any scored session, the local date after the freeze session; null while forming. | API-075, D-41; FR-162 |
| FEAT-028-FR-06 | `last_checkin_at`/`last_checkin_local` shall be the latest non-duplicate record of any status; `last_30_days` the four counts of the 30-day window (FEAT-027 rules). | API-075, D-42 |
| FEAT-028-FR-07 | `explanation` shall contain only structured facts: `compared_with` = `own_baseline`, `alarm_crossed_on` (= `alarm_since`), `still_above_line` (latest tally of the current epoch ≥ `cusum_h`, TRD 19 `Explanation`, D-82; the TRD 11 §4.5.2.1 situation split), `baseline_restarted_on` (current epoch start date when epoch > 1), `baseline_n_usable`, `baseline_n_required`; no sentence or clinical wording. | API-076; TRD 11 §4.5.2.1; OQ-12 |
| FEAT-028-FR-08 | `GET /residents/{resident_code}/checkins` shall accept optional `from` and `to` ISO local dates (`from` ≤ `to`, span ≤ 366 days, else 422 `INVALID_QUERY_PARAMETER`) and pagination, and return `CheckinEventList` newest first (by `local_date` descending). | API-077, API-093; FR-180, FR-183 |
| FEAT-028-FR-09 | Events shall be built as TRD 23 §4.4.4 defines: `alarm_on` (alerts, detail "tally crossed 5.0" built from `cusum_h`, `cusum_tally` = alert `cusum_value`), `watching_started` (first scores row of an epoch), `baseline_complete` (composite baseline row, detail "<N> of <N>", date of `frozen_after_session_id`), `set_aside` (detail = `reason_text`), `quarantined` (detail = `reason_text`), `missed` (`missing_resident`, detail "no record received"), `device_silent` (`missing_device_gap`, detail = ledger reason), `baseline_restarted` (epochs with number > 1, date = local date of `started_at`). | API-077; TRD 23 §4.4.4; TRD 19 E-10; FR-181 |
| FEAT-028-FR-10 | `baseline_restarted` events shall carry `restart_cause` = the first differing part of (device, firmware, software) between epoch e and e − 1, `previous_device_code` = device of epoch e − 1, `from_value`/`to_value` = previous and new value of that part (device codes for `device`); all four fields are null on every other event type. | API-077, DB-065, D-64 |
| FEAT-028-FR-11 | The log shall never contain duplicate records and shall not list usable check-ins as events. | FR-182, D-67, AGT-053 |
| FEAT-028-FR-12 | `GET /residents/{resident_code}/features` shall accept optional `from`/`to` (default: the 30 local days ending on as-of) and return `FeaturesResponse` with `epoch_number` of the current epoch, exactly 7 `scored_features` in contract §6 order (loudness_dbfs, total_phrase_duration_s, speech_rate_syl_per_s, articulation_rate_syl_per_s, number_of_pauses, pause_fraction, voiced_fraction), each with `label` ("<card label> (<technical name>)", e.g. "Quieter (loudness)"), `unit`, `composite_sign`, current-epoch `baseline_median` and `baseline_robust_spread` (null while forming) and `points`. | API-078; TRD 19 E-11; TRD 11 §4.5.4 |
| FEAT-028-FR-13 | Each point shall carry `session_id`, `local_date`, `is_morning`, `raw_value` (raw typed column), `adjusted_value` (from `processed_sessions.adjusted_features`), `z` (unsigned stored z from `scores.z`, null when the session was not scored) and `in_baseline`; only non-duplicate usable sessions of the current epoch in the window are points. | API-078, BSC-037; TRD 19 `FeaturePoint` |
| FEAT-028-FR-14 | `stored_feature_keys` shall list the 12 stored-not-scored keys in contract §6 order (mean_f0_hz … mfcc4); their values are not returned as series. | API-078, BSC-039 |
| FEAT-028-FR-15 | All three responses carry `meta` (as-of of the latest succeeded run); times follow API-094 (`*_at` UTC with Z, `*_local` with facility offset, `local_date` YYYY-MM-DD). | API-057, API-094, OAS-017 |

## Inputs

- Path `resident_code`; query `from`, `to`, `limit`, `offset`; bearer JWT (admin, clinician, researcher).
- Tables: `residents`, `device_assignments`, `devices`, `epochs`, `processed_sessions`, `raw_sessions` (typed feature columns for raw values), `day_ledger`, `baselines`, `scores`, `cusum_state`, `alerts`, `pipeline_runs`, `config_parameters`.
- `analytics.config.FEATURES` / `COMPOSITE_KEYS` / `COMPOSITE_SIGNS` and units (DME-002) imported, not repeated.

## Outputs

- 200 `ResidentDetail`, `CheckinEventList`, `FeaturesResponse`; 404 `RESIDENT_NOT_FOUND`; 422 `INVALID_QUERY_PARAMETER`.

## Data Flow

1. Auth dependencies authorise any user role; the path code is looked up in `residents` (404 when absent).
2. Detail: FEAT-014 queries give current epoch, baseline rows of that epoch, first scores row, non-closed alert, `cusum_state`, device facts and counts; the FEAT-027 status function assigns the status; facts are mapped to the DTO.
3. Check-ins: the service collects events from `alerts`, `scores` (first per epoch), `baselines` (composite rows), `processed_sessions` (set_aside, quarantined; status duplicate excluded), `day_ledger` (missing rows) and `epochs` (number > 1, cause computed against the previous epoch), filters by `from`/`to`, sorts newest first and pages.
4. Features: the service reads current-epoch baseline rows for the 7 keys, the usable processed sessions in the window with their raw typed values from `raw_sessions`, adjusted values and matching `scores.z`, and assembles 7 series in canonical order.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-027

- FEAT-027 (Residents overview API): provides the display-status function, the device-label and 30-day count assembly reused by the detail response, and transitively FEAT-021 (roles) and FEAT-014 (read-model queries, DB-065 restart cause).
- Downstream: FEAT-038, FEAT-066, FEAT-068.

## Database Impact

- Tables read: `residents`, `devices`, `device_assignments`, `epochs` (`epoch_number`, `device_id`, `device_firmware_version`, `extraction_software_version`, `started_at`, `ended_at`), `baselines` (`feature_key`, `median`, `robust_spread`, `first_session_id`, `frozen_after_session_id`, `n_sessions`), `processed_sessions` (`status`, `reason_text`, `local_date`, `is_morning`, `in_baseline`, `adjusted_features`, `timestamp_utc`), `raw_sessions` (19 feature columns), `scores` (`z`, `local_date`, `epoch_id`), `day_ledger` (`status`, `reason`, `local_date`), `cusum_state` (`current_tally`), `alerts` (`status`, `local_date`, `cusum_value`, `session_id`).
- Tables created or modified: none.

## API Impact

- Exposed: `GET /api/v1/residents/{resident_code}` (E-09), `GET /api/v1/residents/{resident_code}/checkins` (E-10), `GET /api/v1/residents/{resident_code}/features` (E-11).
- Consumed: none.

## Frontend Impact

None in this feature. Consumers: `ResidentHeader`, `WhatThisMeans`, `StaffReviewForm` (open alert id) via `getResident(code)`; `CheckinLog` via `getCheckins(code, {from, to})`; `FeatureCard`, `Sparkline`, `OtherMeasurementsCard` via `getFeatures(code)` (TRD 04 §4.6.2), delivered by FEAT-066 and FEAT-068.

## Analytics Impact

None: values are read from persisted pipeline output (`scores.z` unsigned, `adjusted_features`); no z, composite or tally is recomputed (API-006).

## Security Requirements

- Authentication: bearer JWT; roles admin, clinician, researcher allowed; API key and anonymous 401 (TRD 12 §4.6).
- Data minimisation: residents by `resident_code` only; `sex` is the only demographic attribute (SEC-122); no `raw_sessions.payload` exposed (DME-005).
- No clinical wording or diagnosis in API output (API-076, SEC-129).

## Error Handling

- Unknown resident → 404 `RESIDENT_NOT_FOUND` on all three paths (detail "No resident with code '<code>'.").
- `from` > `to`, span > 366 days, malformed date → 422 `INVALID_QUERY_PARAMETER`.
- Resident without epochs or scores (e.g. R08, new residents) → 200 with nulls and empty arrays, no error (ANL-019).
- Database unavailable → 503 `SERVICE_UNAVAILABLE`.

## Logging Requirements

- Access log `request_completed` per call (LOG-010); 404 logged at INFO (LOG-010 exception for 404).
- No audit rows (read-only).

## Testing Requirements

- Integration (`tests/integration/api/test_residents.py`, marker `integration`) with fixture rows: 404 for unknown code; withdrawn resident retrievable; forming resident has `baseline.state` `forming`, null ids, `watching_since` null; frozen resident without scores has `watching_since` = day after freeze (D-41); event types and details for each source row; `restart_cause` `device`/`firmware`/`software` precedence (DB-065) with D07 → D07B; duplicates absent; `from`/`to` filtering and 422 cases; features endpoint returns 7 series in canonical order and 12 stored keys; unscored points have `z` null.
- Unit (`tests/unit/backend/services/test_checkin_service.py`): restart-cause precedence when several key parts change at once.
- Contract: TST-061 schema validation; TST-064 `meta` presence on detail, checkins and features.
- DS-07 values (FEAT-060, TDV-066): AC-API-03 R09 detail; E-10 example events (R03 Oct 18 set-aside reason, R05 Oct 8 quarantine reason, R02 Oct 4 missed, R02 Oct 12 device silent, R07 Oct 13 baseline restarted).
- Performance: API-121 / TST-122 on `/residents/{code}` (FEAT-079).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-028-AC-01 | `GET /api/v1/residents/R11` (no such resident) returns 404 with `type` `urn:echowell:error:RESIDENT_NOT_FOUND` on the detail, checkins and features paths. | API-075, FR-173 |
| FEAT-028-AC-02 | With DS-07 loaded, `GET /residents/R09` returns `status` `alarm_on`, `alarm_since` 2026-10-21, `baseline.state` `frozen` with `n_usable` 16, `n_required` 16, `frozen_after_session_id` R09-20261016-01, `first_local_date` 2026-10-01, `frozen_after_local_date` 2026-10-16, `watching_since` 2026-10-17, `current_tally` 26.830256 (±1e-6) and `explanation.still_above_line` true. | AC-API-03, TDV-066, TRD 19 E-09 |
| FEAT-028-AC-03 | With DS-07 loaded, `GET /residents/R07/checkins` contains a `baseline_restarted` event on 2026-10-13 with `restart_cause` `device`, `previous_device_code` D07, `from_value` D07, `to_value` D07B, and a `baseline_complete` event on 2026-10-28; every other event has the four restart fields null. | API-077, DB-065, E2E-10 |
| FEAT-028-AC-04 | With DS-07 loaded, `GET /residents/R03/checkins` contains a `set_aside` event on 2026-10-18 with detail "quality flag poor; noise above limit" and a `device_silent` event on 2026-10-12 with detail "all residents on shared device D02 have no record"; `GET /residents/R05/checkins` contains `quarantined` on 2026-10-08 with detail "possible other speaker (F0 z=-8.61; composite features with \|z\|>=3: 4)". | TRD 19 E-10, FR-181, E2E-12 |
| FEAT-028-AC-05 | With DS-07 loaded, R04's check-in log contains no event for the duplicate arrivals of R04-20261005-01 and R04-20261018-01 and the log contains no event type other than the 8 of `CheckinEventType`. | FR-182, D-67 |
| FEAT-028-AC-06 | `GET /residents/R09/checkins?from=2026-10-20&to=2026-10-10` returns 422 `INVALID_QUERY_PARAMETER`; a 367-day span returns 422. | API-077, API-093 |
| FEAT-028-AC-07 | With DS-07 loaded, `GET /residents/R09/features` returns 7 `scored_features` in contract §6 order, the loudness series has `baseline_median` -22.405 and `baseline_robust_spread` 2.14977 (±1e-6), point R09-20261021-01 has `z` -2.737502 (±1e-6), a baseline point has `z` null and `in_baseline` true, and `stored_feature_keys` has the 12 keys from `mean_f0_hz` to `mfcc4`. | API-078, TRD 19 E-11 |
| FEAT-028-AC-08 | With DS-07 loaded, `GET /residents/R08` returns `status` `baseline_forming`, `baseline.n_usable` 13, `watching_since` null, `current_tally` 0 or null as stored in `cusum_state`, and `/features` returns 7 series whose points all have `z` null. | FR-163, E2E-11 |
| FEAT-028-AC-09 | All three responses validate against their TRD 19 schemas and contain `meta`. | TST-061, TST-064 |

## Definition of Done

- Three endpoints implemented with TRD 19 schemas and reusing the FEAT-027 status function.
- Integration tests pass; DS-07 criteria pass in the FEAT-060 suite; coverage ≥ 85 % (TST-141); requirement markers present (TST-013).
- OpenAPI regenerated and unchanged by the drift check (FEAT-038).
- The open points in Implementation Notes are reported in the batch report (AGT-022).

## Implementation Notes

- Earlier epochs (FR-172): the detail returns `epoch_count`; the frontend reads an earlier epoch's tally and baseline period with `GET /scores?resident_code=&epoch=` (FEAT-034). TRD 19 defines no separate epochs list on `ResidentDetail`; the BACKLOG description now says `epoch_count` as well (aligned in the PR #2 consistency fixes). The UI control for earlier epochs is TRD 24 OQ-28.
- Resolved (TRD 24 D-82): every `baseline_restarted` event uses the detail "new epoch <n> on device <device code of the new epoch>" (TRD 19 E-10), also for firmware and software restarts; the structured fields `restart_cause`, `from_value`, `to_value` carry the change in every case.
- Build the "tally crossed 5.0" detail from the active `cusum_h` formatted with one decimal so it stays correct if h changes.
- Sort events newest first by `local_date`, then by a fixed event-type order within one day so paging is stable (TRD 19 shows only date order; choose a deterministic secondary key and document it in the batch report).
- Raw values come from the typed columns of `raw_sessions` (joined through `processed_sessions.raw_session_id`), never from `payload` re-parsing.
- Plain-language labels and units come from `analytics.config.FEATURES` and the TRD 11 §4.5.4 table; do not hard-code a second copy of the feature list (DME-002).
