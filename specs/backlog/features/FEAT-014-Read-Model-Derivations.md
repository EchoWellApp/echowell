# FEAT-014 Read-model derivations (30-day window, last check-in, silent days, restart cause, in-use-until)

| Field | Value |
|---|---|
| Epic | Database |
| Build phase | Phase 4 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-013 |
| Status | Complete |

## Purpose

Implement, once and in the repository layer, every value that the dashboard shows but the database never stores: the 30-day window and its used / set aside / quarantined / missed counts, last check-in, baseline progress and dates, watching-since and alarm-since, device silent days and device-gap days, an epoch's restart cause and a device's `in_use_until`. Centralising these derivations keeps the overview, detail, devices and analytics APIs consistent with each other and with the answer-key tiles 2 / 7 / 1 / 19.

## Business Context

- BR-12: overview rows show "Last 30 days: used · set aside · quarantined · missed" with duplicates never counted (FR-135, DB-041); devices report silent days (FR-154, DB-044).
- BR-13: the detail page shows baseline progress and dates, watching-since, alarm-since and the scores series with the baseline period (DB-043, DME-012).
- BR-06 and BR-08: missed days and device gaps are reported honestly; epoch restarts explain their cause (DB-065) and retired devices their last use (DB-066).
- D-41, D-42, D-64: the exact definitions of watching-since, last check-in, the 30-day window, restart cause and `in_use_until`.

## Referenced TRDs

- TRD 06 DB-041, DB-043..DB-045, DB-065, DB-066; §4.7 query patterns; AC-DB-05.
- TRD 23 DME-011, DME-012; §4.4 derived values (§4.4.1 activity values, §4.4.2 device values, §4.4.3 display-status inputs, §4.4.4 check-in log sources).
- TRD 02 §4.1 definitions ("Silent day", "Last check-in"), FR-135, FR-154.
- TRD 24 D-41, D-42, D-64.

## Scope

- Repository module(s) under `backend/repositories/` (for example `read_models.py`, or methods on the resident, device and score repositories) that take the effective `as_of` instant, the facility time zone and `baseline_n` as parameters and return plain data objects:
  - `window_for(resident, as_of_date)` → `(max(as_of_date − 29, enrolled_on), as_of_date)`.
  - `activity_counts(resident_ids, window)` → used, set aside, quarantined (from `processed_sessions` by `local_date` and status) and missed (`day_ledger` `missing_resident` + `missing_device_gap`), duplicates never counted.
  - `last_checkin(resident_ids)` → latest `timestamp_utc` of non-duplicate `processed_sessions` (any of usable, set_aside, quarantined).
  - `current_epoch(resident_ids)`, `baseline_progress(epoch, N)` → `min(count usable in current epoch, N)`, frozen flag (20 baselines rows), baseline first/frozen-after dates (composite row).
  - `watching_since(epoch)` → local date of the first `scores` row of the current epoch, else the local date after the freeze session.
  - `alarm_since(epoch)` → `local_date` of the epoch's non-closed alert; `alert_open_days` = as-of date − alarm since; alert tally from `cusum_state.current_tally`; reviewed flag (≥ 1 `alert_reviews` row).
  - `baseline_restarted(epoch)` → local date of `started_at` when `epoch_number > 1`.
  - `scores_series(epoch)` → scores in `local_date` order with `cusum_tally`, `alarm_state`, and the baseline period from `first_session_id`/`frozen_after_session_id`.
  - `device_silent_days(device, window)` and `device_gap_days(device, window)` from `day_ledger`; devices' assigned residents, shared flag, replaced-by/was, last upload (`max(raw_sessions.timestamp_utc)`), firmware (`devices.firmware_version_last`).
  - `restart_cause(epoch)` → first differing part (device, firmware, software) versus epoch e − 1 with `previous_device_code`, `from_value`, `to_value`; none for epoch 1.
  - `in_use_until(device, as_of_date)` → NULL when an assignment covers the as-of date, else the latest `valid_to`.
  - Device label suffix inputs: "(shared)" when ≥ `shared_device_min_residents` residents are assigned on the as-of date; "(was <code>)" when the previous assignment ended the day before the current started.
- Integration tests against the `test_v0_1` dataset once FEAT-055 can seed it; until then, tests use small hand-built fixtures inserted through the repositories.

## Out of Scope

- HTTP routers, DTOs and the `meta` block (FEAT-019, FEAT-027..FEAT-030, FEAT-034, FEAT-035).
- The display-status label and sort logic (FEAT-027); this feature supplies its inputs (open alert in current epoch, frozen-baseline flag, epoch number).
- Determining the effective `as_of` (latest succeeded run, FEAT-019/FEAT-024); it is a parameter here.
- Writing any derived value to the database (forbidden by DME-012).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-014-FR-01 | The 30-day window shall be the 30 local calendar days ending on the as-of local date inclusive (`d − 29` … `d`), never starting before the resident's `enrolled_on`. | DB-041, D-42 |
| FEAT-014-FR-02 | Used, set aside and quarantined counts shall come from `processed_sessions` by `local_date` and status within the window; missed from `day_ledger` `missing_resident` + `missing_device_gap`; duplicates are never counted. | DB-041, FR-135, AGT-053 |
| FEAT-014-FR-03 | Last check-in shall be the `timestamp_utc` of the resident's latest non-duplicate `processed_sessions` row of any status, returned as an instant for presentation in facility local time. | DB-045, D-42 |
| FEAT-014-FR-04 | Baseline progress shall be `min(count usable in current epoch, N)` of N, with N the active profile's `baseline_n`; baseline dates are the local dates of `first_session_id` and `frozen_after_session_id` of the composite baseline row. | DME-012, TRD 23 §4.4.1 |
| FEAT-014-FR-05 | Watching-since shall be the local date of the first scored session of the current epoch; before any scored session, the local date after the freeze session. | D-41, TRD 23 §4.4.1 |
| FEAT-014-FR-06 | Alarm-since shall be the `local_date` of the non-closed alert of the current epoch; alert open days = as-of date − alarm-since; alert tally = `cusum_state.current_tally` of the alert's epoch; reviewed = at least one `alert_reviews` row. | DME-012, TRD 23 §4.4.1 |
| FEAT-014-FR-07 | Baseline restarted shall be the local date of the current epoch's `started_at` when `epoch_number > 1`. | DME-012 |
| FEAT-014-FR-08 | The scores series of one epoch shall be returned in `local_date` order with `cusum_tally` and `alarm_state`, plus the baseline period, in ≤ 50 ms database time. | DB-043 |
| FEAT-014-FR-09 | A device shall be silent on local day d when at least one `day_ledger` row has that `device_id` and `local_date = d` and none of them is `checked_in`; silent days and device-gap days (silent days of a shared device, ledger `missing_device_gap`) are counted over the 30-day window. | DB-044, FR-154, TRD 23 §4.4.2 |
| FEAT-014-FR-10 | The restart cause of epoch e > 1 shall be the first differing part, in the order device, firmware, software, versus epoch e − 1, with `previous_device_code` and `from_value`/`to_value`; epoch 1 has none. | DB-065, D-64 |
| FEAT-014-FR-11 | A device's `in_use_until` shall be NULL when it has an assignment covering the as-of local date, otherwise the latest `valid_to` of its assignments. | DB-066, D-64 |
| FEAT-014-FR-12 | Device values shall include residents assigned on the as-of date, shared flag (≥ 2 residents), replaced-by/was devices, last upload (max `raw_sessions.timestamp_utc`) and firmware (`devices.firmware_version_last`). | TRD 23 §4.4.2 |
| FEAT-014-FR-13 | The display-status inputs (non-closed alert in the current epoch; frozen baseline in the current epoch; epoch number) shall be derived on read and never stored. | DME-011 |
| FEAT-014-FR-14 | None of these values shall be persisted; all are computed per request from stored rows and the as-of instant. | DME-012 |
| FEAT-014-FR-15 | The check-in log source rows of TRD 23 §4.4.4 (alerts, first scores row per epoch, composite baseline row, set-aside and quarantined sessions, missing ledger days, epochs with number > 1) shall be retrievable by resident and date range for FEAT-028. | TRD 23 §4.4.4 |

## Inputs

- Stored rows of `residents`, `devices`, `device_assignments`, `raw_sessions`, `processed_sessions`, `day_ledger`, `epochs`, `baselines`, `scores`, `cusum_state`, `alerts`, `alert_reviews`, `config_parameters` (FEAT-009..FEAT-012).
- Parameters: effective `as_of`, facility time zone (`facilities.timezone`), `baseline_n` and `shared_device_min_residents` of the active profile.

## Outputs

- Plain Python data objects (dataclasses or typed dicts) consumed by services of FEAT-027, FEAT-028, FEAT-029, FEAT-030, FEAT-034, FEAT-035.

## Data Flow

Service receives a request → resolves `as_of` from the latest succeeded run (FEAT-019) → calls the read-model repository functions with `as_of`, time zone and profile values → each function issues indexed SQL (TRD 06 §4.7 patterns) and returns plain values → the service assembles DTOs. No write occurs.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-013

- FEAT-013 provides the session factory and the indexes (`processed_sessions_resident_date_idx`, `processed_sessions_resident_ts_idx`, `day_ledger_missing_idx`, `day_ledger_device_date_idx`, `scores_epoch_date_idx`, `epochs_current_uq`, `raw_sessions_device_ts_idx`) these queries rely on.

Features that build directly on this one (BACKLOG.md §4): FEAT-017, FEAT-019, FEAT-027, FEAT-029, FEAT-030, FEAT-034, FEAT-036.

## Database Impact

- Tables read: `residents`, `devices`, `device_assignments`, `raw_sessions`, `processed_sessions`, `day_ledger`, `epochs`, `baselines`, `scores`, `cusum_state`, `alerts`, `alert_reviews`, `config_parameters`, `facilities`.
- Tables created or modified: none.

## API Impact

None exposed. Consumed by E-08 `/residents`, E-09 `/residents/{resident_code}`, E-10 `/checkins`, E-12 `/scores`, E-13 `/alerts`, E-17 `/devices`, E-18 `/analytics` (later features).

## Frontend Impact

None directly; the values feed the Residents overview tiles and rows, the Devices panel and the Resident detail header (TRD 11) through the APIs.

## Analytics Impact

None. These are presentation derivations over stored pipeline output, not algorithm stages; they never recompute baselines, z or CUSUM.

## Security Requirements

- Read-only queries on the `echowell_app` connection; no access to `evaluation_ground_truth`.
- Residents and devices are returned by code; UUIDs stay internal (DME-004).

## Error Handling

- Resident without a current epoch: baseline progress 0 of N, no watching-since, no alarm-since (display input "no epoch yet", TRD 23 §4.4.3).
- Resident enrolled after `d − 29`: window starts at `enrolled_on` (DB-041).
- Device with no ledger rows in the window: 0 silent days.
- Epoch 1: no restart cause (DB-065).
- Database errors propagate to the request handler (FEAT-019 maps them to 500/503).

## Logging Requirements

None. Read paths are covered by the `request_completed` access log (FEAT-018). No audit rows (reads are not audited).

## Testing Requirements

- Integration (`tests/integration/db/test_read_models.py`, marker `integration`), against the `test_v0_1` seed as of 2026-10-30 15:00 America/Chicago:
  - DB-041: R02 24·0·0·6, R03 22·7·0·1, R08 13·5·0·12; missed tile sum 19 (AC-DB-05).
  - DB-045: R09 last check-in 2026-10-30 14:28 local.
  - DB-044: D02 silent on 2026-10-12 only; D08 silent on R08's 12 missing days.
  - DB-065: R07 epoch 2 restart cause `device`, D07 → D07B.
  - DB-066: D07 `in_use_until` 2026-10-12.
  - TRD 23 §4.4.1: R08 baseline progress 13 of 16; R09 baseline dates Oct 1–16, watching since Oct 17, alarm since Oct 21; R10 alarm since Oct 24; alert open days R09 9, R10 6; tallies 26.8 and 13.4 (1 decimal); R07 baseline restarted Oct 13; device labels "D02 (shared)" and "D07B (was D07)".
  - DB-043: scores series of R09's epoch in `local_date` order with 14 rows.
- Unit (`tests/unit/backend/repositories/test_read_models.py`): window clipping at `enrolled_on`; restart-cause ordering device → firmware → software; silent-day rule with mixed ledger statuses.
- Until the full seed exists (FEAT-055), the same checks run on hand-built fixtures inserted through repositories; the `test_v0_1` assertions become active when the seed lands.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-014-AC-01 | With the `test_v0_1` seed as of 2026-10-30 15:00 CT, activity counts are R02 24·0·0·6, R03 22·7·0·1, R08 13·5·0·12, and the sum of missed over R01–R10 is 19. Verified by: Integration (`tests/integration/db/test_read_models.py`). | DB-041, AC-DB-05, FR-135 |
| FEAT-014-AC-02 | R09 last check-in equals 2026-10-30 14:28 in America/Chicago. Verified by: Integration (`tests/integration/db/test_read_models.py`). | DB-045 |
| FEAT-014-AC-03 | D02 silent days in the window = {2026-10-12}; D08 silent days equal R08's 12 missing days; D02 device-gap days = {2026-10-12}. Verified by: Integration (`tests/integration/db/test_read_models.py`). | DB-044, FR-154 |
| FEAT-014-AC-04 | R07 epoch 2 restart cause is `device` with `previous_device_code` D07, `from_value` D07, `to_value` D07B; R07 epoch 1 has no restart cause. Verified by: Integration (`tests/integration/db/test_read_models.py`). | DB-065, D-64 |
| FEAT-014-AC-05 | D07 `in_use_until` is 2026-10-12; D07B `in_use_until` is NULL. Verified by: Integration (`tests/integration/db/test_read_models.py`). | DB-066 |
| FEAT-014-AC-06 | R08 baseline progress is 13 of 16; R09 watching-since is 2026-10-17 and alarm-since 2026-10-21; R10 alarm-since 2026-10-24. Verified by: Integration (`tests/integration/db/test_read_models.py`). | DME-012, D-41 |
| FEAT-014-AC-07 | The R09 scores series returns 14 rows in ascending `local_date` with the baseline period Oct 1–Oct 16, in ≤ 50 ms database time on the seeded database. Verified by: Integration (`tests/integration/db/test_read_models.py`). | DB-043 |
| FEAT-014-AC-08 | No table or column stores any of these values (schema review: no column named `last_checkin`, `silent_days`, `in_use_until`, `restart_cause`, `watching_since`). Verified by: Integration (`tests/integration/db/test_read_models.py`). | DME-012 |

## Definition of Done

- All FEAT-014 acceptance criteria pass (FEAT-014-AC-01 to FEAT-014-AC-07 against the seed as soon as FEAT-055 provides it; fixture-based equivalents pass in Phase 4).
- No HTTP code in the module (TRD 25 §4.6 Phase 4 Pitfalls "Do not implement APIs"); docstrings cite DB/DME IDs; delivered in the Phase 4 checkpoint PR of Block 3.

## Implementation Notes

- Convert `as_of` to the facility local date with `zoneinfo` (never a fixed offset; AGT-040).
- Use the exact SQL shapes of TRD 06 §4.7 (e.g. `DISTINCT ON (resident_id) … ORDER BY resident_id, timestamp_utc DESC` for last check-in) so the indexes are used.
- Natural sort of resident codes (R2 before R10, AGT-052) is a service concern (FEAT-027), not a repository concern.
- The 1-decimal tally display is formatting in the API/UI; return the full float64 value here (DME-014, AGT-054).
