# FEAT-027 Residents overview API (GET /api/v1/residents) with display status and sorts

| Field | Value |
|---|---|
| Epic | Backend API |
| Build phase | Phase 5 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-021, FEAT-014 |
| Status | Not Started |

## Purpose

Serve the data of the Residents overview (`/residents`, SRC-09): one row per resident with the single display status (`alarm_on`, `baseline_forming`, `no_alarm`), device label facts, last check-in and last-30-day counts, the four summary tiles, and the three sort orders ("Alarms first", "Resident ID", "Last check-in"). Staff use this list every day to see who needs attention first; the display status and the "Alarms first" order are derived on read so they always reflect the latest succeeded pipeline run.

## Business Context

- BR-12 (overview of all residents with status and missed check-ins): rows, badges, tiles and sort orders of SRC-09.
- BR-06 (missed days visible, never imputed): `missed` = missing_resident + missing_device_gap ledger days.
- BR-03 (duplicates never shown): 30-day counts and last check-in ignore duplicates.
- BR-08 (device moves): "(was <old>)" and "baseline restarted <Mon D>" facts.
- BR-15: with the test data the tiles are 2 / 7 / 1 / 19 and the default order is R09, R10, R08, R07, R03, R02, R05, R01, R04, R06.
- FRs covered (BACKLOG.md): FR-130, FR-131, FR-132, FR-133, FR-134, FR-135, FR-136.

## Referenced TRDs

- TRD 05 API-070..API-074 (parameters, sorts, summary, counts), API-069 and API-057 (as-of and `meta`), API-016 (pagination), API-100 (list envelope), API-094 (time formats), API-121 (latency budget).
- TRD 19 §4.3 E-08; schemas `ResidentsOverviewResponse`, `ResidentOverviewRow`, `OverviewSummary`, `BaselineProgress`, `Last30Days`, `DateWindow`, `DisplayStatus`; OAS-021.
- TRD 11 §4.3.2 (sort rules), §4.3.4 (status badge facts), §4.3.5 (count semantics), UX-030..UX-033 (sort control the API supports), UX-047, UX-048.
- TRD 23 §4.4.1 (activity values), §4.4.3 (display status rules), DME-011, DME-012.
- TRD 09 CUS-020, CUS-021 (alarm_on while open or acknowledged; status follows the new epoch).
- TRD 13 TST-033, TST-055; TRD 14 TDV-062..TDV-065; TRD 13 §4.10 scenarios E2E-03..E2E-06 (expected orders); AC-API-02.
- TRD 25 AGT-052 (natural sort), AGT-053 (never display duplicates); TRD 24 D-17 (Alarms-first rule authoritative), D-42 (last check-in and 30-day window).

## Scope

- Router handler in `backend/api/residents.py` for `GET /api/v1/residents` calling `services.resident_service.overview`.
- A display-status service function in `backend/services/resident_service.py` implementing TRD 23 §4.4.3 (reused by FEAT-028 for the detail page).
- Query parameter validation (`sort`, `cohort`, `include_withdrawn`, `limit`, `offset`).
- Row assembly from the FEAT-014 read-model queries: device code, shared flag, previous device, status, alarm since, open alert id, current epoch, baseline restarted date, baseline progress, last check-in (UTC and local), last-30-day counts.
- The three sort orders and the summary tiles computed over all rows that match the filters, independent of paging.
- `meta` and `window` blocks.

## Out of Scope

- The derivation queries themselves (30-day window, counts, last check-in, silent days, restart cause) — FEAT-014.
- Resident detail, check-in log and features (FEAT-028); devices panel (FEAT-029).
- The overview page, `SortSelect`, `SummaryTiles`, `ResidentsTable`, `StatusBadge`, `DeviceCell` (FEAT-065) and badge wording (`frontend/lib/wording.ts`).
- Producing alerts, epochs or ledger rows (Phase 6 pipeline features).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-027-FR-01 | `GET /api/v1/residents` shall accept `sort` ∈ {`alarm`, `resident_id`, `last_checkin`} (default `alarm`), `cohort` ∈ {`longitudinal`, `new_admission`} (default `longitudinal`), `include_withdrawn` boolean (default false), `limit` 1..500 (default 50) and `offset` ≥ 0 (default 0); any other value returns 422 `INVALID_QUERY_PARAMETER`. | API-070, API-016; FR-133 |
| FEAT-027-FR-02 | The list shall contain the residents of the requested cohort; withdrawn residents shall be excluded unless `include_withdrawn=true`. | FR-130, API-070, TST-055 |
| FEAT-027-FR-03 | Each row shall carry exactly one `status`: `alarm_on` when a non-closed alert (status `open` or `acknowledged`) exists for the current epoch; else `baseline_forming` when the current epoch has no frozen baseline (fewer than `baseline_n` usable sessions, or no epoch yet); else `no_alarm`. The status shall be derived on read and never stored. | FR-131, DME-011, TRD 23 §4.4.3, CUS-020, CUS-021 |
| FEAT-027-FR-04 | `alarm_since` shall be the `local_date` of the non-closed alert of the current epoch and `open_alert_id` its id (both null otherwise). | FR-131, TRD 23 §4.4.1 |
| FEAT-027-FR-05 | `current_epoch` shall be the epoch number of the resident's epoch with `ended_at IS NULL` (null if none), and `baseline_restarted_on` the local date of that epoch's `started_at` when `current_epoch > 1`, else null. | FR-132, TRD 23 §4.4.1 |
| FEAT-027-FR-06 | `baseline_progress` shall be `{n_usable: min(usable sessions in the current epoch, N), n_required: N}` with N = `baseline_n` of the active profile. | FR-131, TRD 23 §4.4.1 |
| FEAT-027-FR-07 | `device_code` shall be the resident's device on the as-of local date, `device_shared` true when ≥ `shared_device_min_residents` residents have an assignment to it covering that date, and `previous_device_code` the device of the resident's previous assignment when it ended the day before the current one started (else null). | FR-134, TRD 23 §4.4.1, TRD 19 `ResidentOverviewRow` |
| FEAT-027-FR-08 | `last_checkin_at` shall be the maximum `timestamp_utc` of the resident's non-duplicate processed sessions of any status, and `last_checkin_local` the same instant with the facility offset; both null when none exists. | FR-134, API-094, D-42 |
| FEAT-027-FR-09 | `last_30_days` shall count, over the 30 local days ending on the as-of local date and not before `enrolled_on`: `used` (status usable), `set_aside`, `quarantined` and `missed` (= day_ledger missing_resident + missing_device_gap); duplicates are never counted. | API-074, FR-135, UX-047, UX-048, AGT-053 |
| FEAT-027-FR-10 | `sort=alarm` shall order rows alarm_on → baseline_forming → no_alarm; alarm group by `alarm_since` ascending then resident code; forming group by resident code; no-alarm group with `current_epoch > 1` first, then (set_aside + quarantined + missed in the last 30 days) descending, then resident code ascending. | API-071, TRD 11 §4.3.2, D-17; FR-133 |
| FEAT-027-FR-11 | `sort=resident_id` shall use natural ascending order of `resident_code` (R2 before R10); `sort=last_checkin` shall order by most recent `last_checkin_at` first, residents without a check-in last, ties broken by `resident_code`. All resident-code tie-breaks use natural order. | API-072, AGT-052; FR-133 |
| FEAT-027-FR-12 | `summary` shall be computed over all residents matching the filters, independent of `limit` and `offset`: `alarm_on`, `no_alarm`, `baseline_forming` counts and `missed_last_30_days` = sum of `last_30_days.missed` over those residents. | API-073, FR-136 |
| FEAT-027-FR-13 | The response shall be `ResidentsOverviewResponse` with `meta` (as-of = latest succeeded run), `window` `{from, to}` of the 30-day window, `summary`, `items`, `total`, `limit`, `offset`. | API-057, API-069, API-100; TRD 19 E-08 |
| FEAT-027-FR-14 | When no pipeline run has succeeded yet, `meta.as_of` shall be null and rows shall be derived from the empty derived tables (status `baseline_forming`, zero counts), without error. | TRD 19 `Meta.as_of` nullable; ANL-019 |

## Inputs

- HTTP GET with bearer JWT of role admin, clinician or researcher and the query parameters above.
- Tables (via FEAT-014 queries): `residents`, `device_assignments`, `devices`, `processed_sessions`, `day_ledger`, `epochs`, `baselines`, `alerts`, `cusum_state`, `pipeline_runs`, `facilities`, `config_parameters` (`baseline_n`, `shared_device_min_residents`).

## Outputs

- 200 `ResidentsOverviewResponse` (JSON); 422 Problem for invalid parameters; 401/403 Problems from the auth dependencies.

## Data Flow

1. `get_current_user` and `require_roles("admin","clinician","researcher")` authorise the call (FEAT-020, FEAT-021); `get_pagination` and the router validate parameters.
2. `get_meta()` resolves the as-of from the latest succeeded `pipeline_runs` row and the active profile's `baseline_n`, `cusum_h` (FEAT-019).
3. `resident_service.overview` loads the matching residents and, through FEAT-014 repository queries, their current epoch, baseline state, non-closed alert, device assignment facts, last check-in and 30-day counts for the window ending on the as-of local date.
4. The display-status function assigns one status per resident; the summary is computed over the full filtered set; the requested sort is applied; `limit`/`offset` slice the sorted list.
5. The router maps the result to the DTO; the access log records duration (FEAT-018).

## Dependencies

- FEAT-021 (Role-based authorization matrix): `require_roles` and the role matrix for GET /residents (admin, clinician, researcher).
- FEAT-014 (Read-model derivations): the 30-day window, counts, last check-in, baseline progress, alarm-since and restart facts.
- Downstream: FEAT-028 (reuses the display-status service), FEAT-060 (asserts DS-07 values), FEAT-065 (overview page).

## Database Impact

- Tables read: `residents` (`resident_code`, `cohort`, `status`, `enrolled_on`, `withdrawn_on`), `device_assignments` (`valid_from`, `valid_to`), `devices` (`device_code`), `processed_sessions` (`status`, `local_date`, `timestamp_utc`, `epoch_id`), `day_ledger` (`status`, `local_date`), `epochs` (`epoch_number`, `started_at`, `ended_at`), `baselines` (composite row presence), `alerts` (`status`, `local_date`, `epoch_id`), `pipeline_runs` (`as_of`, `status`).
- Tables created or modified: none (read-only endpoint).

## API Impact

- Exposed: `GET /api/v1/residents` (E-08; 200 `ResidentsOverviewResponse`; 422 `INVALID_QUERY_PARAMETER`; universal 401/403/429/500/503).
- Consumed: none.

## Frontend Impact

None in this feature. Consumers (FEAT-065): `/residents` page components `SummaryTiles`, `SortSelect`, `ResidentsTable`, `StatusBadge`, `DeviceCell`, and `AppHeader` subline via client function `getResidents({ sort })` (TRD 04 §4.6.2, §4.16).

## Analytics Impact

None: no algorithm runs here. The endpoint reads persisted pipeline output; display status and counts are read-model derivations (DME-011, DME-012), not analytics computations (API-006).

## Security Requirements

- Authentication: bearer JWT (`get_current_user`, active user, role read from the database, API-012, API-013).
- Authorisation: admin, clinician and researcher 200; API key and anonymous 401 (TRD 12 §4.6, TRD 13 Table 4.13-A).
- Data minimisation: residents identified by `resident_code` only; no `residents.id` exposed (DME-004, SEC-120).

## Error Handling

- Invalid `sort`, `cohort`, boolean, `limit` or `offset` → 422 `INVALID_QUERY_PARAMETER` with the offending parameter in `errors[]`.
- Database unavailable → 503 `SERVICE_UNAVAILABLE` with `Retry-After: 30` (API-097).
- No succeeded run → 200 with `meta.as_of` null (no 500); empty roster → 200 with `items` [] and zero tiles.

## Logging Requirements

- One `request_completed` access log record per call with route template, status and `duration_ms` (LOG-010, API-107); no query values beyond dates.
- No audit row (read endpoint; TRD 12 §4.12 has no read action).

## Testing Requirements

- Unit (`tests/unit/backend/services/test_resident_service.py`, marker `unit`): TST-033 — `alarm_on`, `no_alarm` with and without epoch > 1, `baseline_forming`, and each sort with its tie rules (natural sort R2 < R10; no-check-in residents last; no-alarm group ordering by epoch > 1 then non-used events then code).
- Integration (`tests/integration/api/test_residents.py`, marker `integration`) with fixture rows written through repositories: parameter validation (422 cases), `include_withdrawn` behaviour (TST-055 overview half), summary independent of `limit=1`, list envelope with `meta` (TST-064), response schema validation (TST-061).
- DS-07 value checks (run once the pipeline exists, owned by FEAT-060): OAS-021 / AC-API-02 / TDV-062 tiles 2/7/1/19 and default order; TDV-063 Alarms-first rule; TDV-064, TDV-065 counts and last check-in; E2E-05/E2E-06 orders through the API.
- Performance: API-121 / TST-122 p95 ≤ 500 ms on DS-08 (FEAT-079).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-027-AC-01 | `GET /api/v1/residents?sort=foo` and `?limit=0` each return 422 with `type` `urn:echowell:error:INVALID_QUERY_PARAMETER`. | API-070, API-016 |
| FEAT-027-AC-02 | With a fixture of three residents (one with a non-closed alert in the current epoch, one with 13 of 16 usable sessions, one frozen with epoch 2), the statuses are `alarm_on`, `baseline_forming` and `no_alarm` with `baseline_restarted_on` set, and `sort=alarm` lists them in that order. | TST-033, FR-131, FR-132 |
| FEAT-027-AC-03 | For residents R2 and R10, `sort=resident_id` returns R2 before R10. | API-072, AGT-052 |
| FEAT-027-AC-04 | A withdrawn resident is absent by default and present with `include_withdrawn=true`. | TST-055, FR-130 |
| FEAT-027-AC-05 | With `limit=1`, `summary` still counts every matching resident and `total` equals the number of matching residents. | API-073 |
| FEAT-027-AC-06 | A duplicate processed session dated inside the window changes neither `last_30_days` nor `last_checkin_at` of its resident. | API-074, AGT-053 |
| FEAT-027-AC-07 | With DS-07 loaded (as-of 2026-10-30 15:00 America/Chicago), the default sort returns R09, R10, R08, R07, R03, R02, R05, R01, R04, R06; summary is 2 / 7 / 1 / 19; R08 shows `baseline_progress` 13 of 16 and `last_30_days` 13 · 5 · 0 · 12; R07 shows `device_code` D07B, `previous_device_code` D07, `baseline_restarted_on` 2026-10-13; `window` is 2026-10-01..2026-10-30. | AC-API-02, OAS-021, TDV-062, TDV-063 |
| FEAT-027-AC-08 | With DS-07 loaded, `sort=last_checkin` returns R02, R07, R05, R10, R06, R08, R09, R03, R04, R01 and `sort=resident_id` returns R01 … R10. | E2E-05, E2E-06, API-072 |
| FEAT-027-AC-09 | Every 200 response validates against `ResidentsOverviewResponse` and contains `meta` with all seven fields. | TST-061, TST-064 |
| FEAT-027-AC-10 | An API key calling the endpoint receives 401 and each user role receives 200. | TRD 13 Table 4.13-A |

## Definition of Done

- Endpoint implemented with the TRD 19 schema; display-status function unit-tested (TST-033) and reusable by FEAT-028.
- Integration tests pass on PostgreSQL 16; DS-07 assertions (FEAT-027-AC-07, FEAT-027-AC-08) are part of the FEAT-060 suite and pass there.
- Requirement IDs referenced by `@pytest.mark.req` (TST-013); backend coverage ≥ 85 % (TST-141).
- OpenAPI regenerated (FEAT-038 drift check passes).

## Implementation Notes

- Natural sort key: split `resident_code` into the leading letters and the numeric part and compare `(prefix, int(number), code)`; use the same key for every resident-code tie-break.
- Compute the 30-day window from the as-of local date in `facilities.timezone` with `zoneinfo` (d − 29 … d, clipped at `enrolled_on`); do not use the server clock.
- Fetch all filtered residents, derive status and counts, sort in Python, then slice; ASM-08 (< 100 residents) keeps this within the 500 ms budget. Use the FEAT-014 aggregate queries (one grouped query per measure) rather than per-resident queries.
- "Alarms first" uses `set_aside + quarantined + missed` for the no-alarm group (R03 8 and R02 6 before R05 2), not the wireframe order (D-17, TDV-063).
- `alarm_on` counts `acknowledged` alerts too: a saved review does not turn the alarm off (CUS-020, OQ-05).
- `resident_status` and `cohort` are returned per row; badge wording is built by the frontend, never by the API.
