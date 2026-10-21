# FEAT-029 Devices API (GET /api/v1/devices)

| Field | Value |
|---|---|
| Epic | Backend API |
| Build phase | Phase 5 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-021, FEAT-014 |
| Status | Not Started |

## Purpose

Serve the Devices panel of the Residents overview (`/residents#devices`, SRC-09): one item per device with the residents assigned on the as-of date, whether it is shared, which device it replaced or was replaced by, when it was in use, its last upload and firmware, and its silent and device-gap days over the last 30 days. Staff and the study team use it to spot devices that stopped sending data and to understand shared-device gaps such as D02 on Oct 12.

## Business Context

- BR-12 (overview including device status), BR-06 (missed days visible; device-gap days distinguished from resident misses), BR-08 (device moves visible: "In use since Oct 13 (replaced D07)").
- BR-15: with the test data the list has 10 devices; D02 is shared by R02 and R03 with device-gap day 2026-10-12; D07 is retired with `in_use_until` 2026-10-12 and replaced by D07B.
- FRs covered (BACKLOG.md): FR-150, FR-151, FR-152, FR-153, FR-154, FR-155.

## Referenced TRDs

- TRD 05 API-086 (fields and test values), API-057, API-069 (meta, as-of), API-100 (envelope), API-094 (times), API-121 (latency).
- TRD 19 §4.3 E-17; schemas `Device`, `DeviceList`, `DeviceCode`.
- TRD 06 DB-044 (silent day derived), DB-066 (`in_use_until` derived).
- TRD 02 §4.1 glossary "Silent day (device)" and "Device-gap day".
- TRD 23 §4.4.2 (device values), §4.2.4 (devices), §4.2.5 (device assignments).
- TRD 10 ING-044..ING-046 (assignment resolution, shared definition).
- TRD 11 §4.4 (Devices panel the API serves), §4.13.4 (expected rendering).
- TRD 14 TDV-066; TRD 13 §4.10 E2E-07.
- TRD 24 D-64 (fields derived on read).

## Scope

- Router `backend/api/devices.py` with `GET /api/v1/devices` calling `services.device_service.panel`.
- Assembly of every `Device` field from FEAT-014 read-model queries over `devices`, `device_assignments`, `raw_sessions` and `day_ledger`.
- Natural ordering by `device_code`, pagination, `meta`.

## Out of Scope

- The `DevicePanel` component and device-range labels (`compressDeviceCodes`, FEAT-065).
- Device registration or assignment changes (CLI `import-master-data`, FEAT-017; no device endpoint exists in the MVP, TRD 10 §4.9).
- `device_silent` data alerts (FEAT-050) — the panel reports silent days, the data alert is a separate rule.

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-029-FR-01 | `GET /api/v1/devices` shall return one `Device` item per row of `devices` (active and retired), ordered by `device_code` in natural order, with `limit`/`offset` pagination and `meta`. | API-086, API-100; TRD 19 E-17; FR-150 |
| FEAT-029-FR-02 | `resident_codes` shall list the residents with an assignment to the device covering the as-of local date, and `shared` shall be true when that list has ≥ `shared_device_min_residents` (2) residents. | API-086, ING-045, ING-046; FR-150, FR-151 |
| FEAT-029-FR-03 | `replaces_device_code` shall be the device of the assignment that precedes this device's assignment for the same resident, and `replaced_by_device_code` the device of the assignment that follows it (null when none). | API-086; TRD 23 §4.4.2; FR-155 |
| FEAT-029-FR-04 | `in_use_since` shall be the earliest `valid_from` of the device's assignments (null when it has none) and `in_use_until` shall be null when the device has an assignment covering the as-of local date, otherwise the latest `valid_to` of its assignments. | DB-066; TRD 19 E-17 (D07 2026-10-01..2026-10-12, D07B from 2026-10-13); FR-155 |
| FEAT-029-FR-05 | `last_upload_at` shall be the maximum `raw_sessions.timestamp_utc` of the device and `last_upload_local` the same instant with the facility offset; `firmware_version` shall be `devices.firmware_version_last`; `active` and `room_label` come from `devices`. | API-086; TRD 23 §4.4.2; FR-152 |
| FEAT-029-FR-06 | `silent_days_last_30` shall list the local dates in the 30-day window, on or after `in_use_since`, on which at least one `day_ledger` row has the device and none of those rows is `checked_in`. | DB-044, API-086; TRD 02 §4.1; FR-154 |
| FEAT-029-FR-07 | `device_gap_days_last_30` shall list the local dates in the window on which the ledger recorded `missing_device_gap` for the device's residents. | API-086; TRD 02 §4.1; FR-153 |
| FEAT-029-FR-08 | Both day lists shall be ascending ISO dates; the window is the 30 local days ending on the as-of local date (latest succeeded run). | API-069, API-094 |

## Inputs

- Bearer JWT (admin, clinician, researcher); query `limit`, `offset`.
- Tables `devices`, `device_assignments`, `residents`, `raw_sessions` (`device_code`/`device_id`, `timestamp_utc`), `day_ledger` (`device_id`, `local_date`, `status`), `pipeline_runs` (as-of), `facilities` (timezone).

## Outputs

- 200 `DeviceList` `{meta, items, total, limit, offset}`.

## Data Flow

1. Auth dependencies authorise any user role.
2. `device_service.panel` reads all devices and all assignments, resolves the as-of local date from `meta`, and computes per device: assigned residents on that date, shared flag, predecessor and successor devices per resident, `in_use_since`, `in_use_until`.
3. One grouped query gets `max(timestamp_utc)` per device from `raw_sessions`; one grouped query over `day_ledger` in the window yields silent and device-gap dates per device.
4. Items are sorted naturally by `device_code`, paged and mapped to `Device`.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-021, FEAT-014

- FEAT-021 (Role-based authorization matrix): role check for GET /devices.
- FEAT-014 (Read-model derivations): silent days (DB-044), device-gap days and `in_use_until` (DB-066) queries.

Features that build directly on this one (BACKLOG.md §4): FEAT-038, FEAT-060, FEAT-065.

## Database Impact

- Tables read: `devices` (`device_code`, `room_label`, `active`, `firmware_version_last`), `device_assignments` (`resident_id`, `device_id`, `valid_from`, `valid_to`), `residents` (`resident_code`), `raw_sessions` (`device_id`, `timestamp_utc`), `day_ledger` (`device_id`, `local_date`, `status`), `pipeline_runs`.
- Tables created or modified: none.

## API Impact

- Exposed: `GET /api/v1/devices` (E-17; 200 `DeviceList`; universal errors only).
- Consumed: none.

## Frontend Impact

None in this feature. Consumer: `DevicePanel` on `/residents#devices` via client function `getDevices()` (TRD 04 §4.6.2), delivered by FEAT-065.

## Analytics Impact

None: silent and device-gap days are read-model derivations over the persisted day ledger (DB-044), not engine computations.

## Security Requirements

- Authentication: bearer JWT; admin, clinician and researcher allowed; API key and anonymous 401 (TRD 12 §4.6).
- `room_label` is non-identifying by rule (SEC-123); no resident or device surrogate ids exposed (DME-004).

## Error Handling

- Invalid `limit`/`offset` → 422 `INVALID_QUERY_PARAMETER`.
- No succeeded run yet → 200 with `meta.as_of` null; day lists are empty and assignment facts use the current facility-local date.
- Database unavailable → 503 `SERVICE_UNAVAILABLE`.

## Logging Requirements

- Access log `request_completed` (LOG-010); no audit row.

## Testing Requirements

- Integration (`tests/integration/api/test_devices.py`, marker `integration`) with fixture rows: shared device with two residents; retired device with a successor (D07 → D07B pattern) giving `active` false, `in_use_until`, `replaced_by_device_code`; device without any upload (`last_upload_at` null); silent day on a single-resident device that is not a device-gap day; natural ordering D07 before D07B before D08; schema validation (TST-061) and `meta` (TST-064).
- DS-07 values (FEAT-060, TDV-066, E2E-07): 10 devices; D02 residents [R02, R03], shared true, `silent_days_last_30` [2026-10-12], `device_gap_days_last_30` [2026-10-12]; D07 `active` false, `in_use_until` 2026-10-12, `replaced_by_device_code` D07B; D08 has 12 silent days and no device-gap day.
- Performance: API-121 / TST-122 (FEAT-079).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-029-AC-01 | With DS-07 loaded, `GET /api/v1/devices` returns `total` 10 with codes in the order D01, D02, D04, D05, D06, D07, D07B, D08, D09, D10. Verified by: Test (E2E-07). | API-086, TRD 19 E-17 |
| FEAT-029-AC-02 | With DS-07 loaded, D02 has `resident_codes` [R02, R03], `shared` true, `silent_days_last_30` [2026-10-12], `device_gap_days_last_30` [2026-10-12] and `last_upload_at` 2026-10-30T19:55:23Z. Verified by: Test (E2E-07). | API-086, TDV-066 |
| FEAT-029-AC-03 | With DS-07 loaded, D07 has `active` false, `in_use_since` 2026-10-01, `in_use_until` 2026-10-12, `replaced_by_device_code` D07B; D07B has `replaces_device_code` D07, `in_use_since` 2026-10-13, `in_use_until` null. Verified by: Integration (`tests/integration/api/test_devices.py`). | API-086, DB-066, FR-155 |
| FEAT-029-AC-04 | With DS-07 loaded, D08 has 12 dates in `silent_days_last_30` and an empty `device_gap_days_last_30`. Verified by: DS-07 values (D02 residents [R02, R03], shared true, `silent_days_last_30` [2026-10-12], `device_gap_days_last_30` [2026-10-12]). | DB-044, TRD 19 E-17 notes |
| FEAT-029-AC-05 | The response validates against `DeviceList`, contains `meta`, and an API key receives 401 while every user role receives 200. | TST-061, TST-064, TRD 13 Table 4.13-A |

## Definition of Done

- All FEAT-029 acceptance criteria pass.
- Endpoint implemented with the TRD 19 schema; integration tests pass; DS-07 criteria pass in the FEAT-060 suite.
- Requirement markers present (TST-013); coverage ≥ 85 % (TST-141); OpenAPI drift check passes (FEAT-038).

## Implementation Notes

- Natural sort key for device codes: prefix letters, integer part, then the remaining suffix (D07 < D07B < D08).
- `in_use_since` = earliest `valid_from` of the device's assignments is now stated in TRD 06 DB-066 and TRD 23 §4.4.2 (TRD 24 D-82); it reproduces every TRD 19 E-17 example value (D02 2026-10-01, D07 2026-10-01, D07B 2026-10-13).
- FR-150 says the panel lists every active device; the API returns all devices including retired ones with `active` false (API-086 test values require D07), and the frontend decides what to show.
- Compute everything with grouped queries over the window (no per-device loops of queries) to stay inside the 500 ms budget on DS-08.
