# Devices API (GET /api/v1/devices)

## Feature Description

`GET /api/v1/devices` (TRD 19 E-17) returns one `Device` item per row of `devices` (active and retired), in natural `device_code` order, with the residents assigned on the as-of local date, the `shared` flag, the device it replaces or is replaced by, `in_use_since` / `in_use_until`, the last upload and firmware, `uploaded_on_as_of_date` (shown as "● Online" / "○ No upload today"), and the silent and device-gap days of the last 30 days. It feeds the Study team "Devices" section, the Resident chart "Device" section and the Summary device tile. The endpoint is read-only and open to every user role. Source: FEAT-029; TRD 05 API-086; TRD 06 DB-044, DB-066; TRD 23 §4.4.2; TRD 24 D-114, D-115.

## Preconditions

1. Local Docker Compose stack running; environment file from `.env.development.example`.
2. **DS-07 state:** `docker compose exec backend python -m backend.cli seed test_v0_1` (as-of `2026-10-30T20:00:00Z`, i.e. local date 2026-10-30).
3. `API=http://localhost:8000/api/v1`; tokens `ADMIN`, `CLIN`, `RES` from `POST $API/auth/login` with the `SEED_*` passwords; `KEY` = the ingest API key from the environment file.
4. `psql` read access; local development stack for the `pytest` case.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-029-01 | DS-07 list has 10 devices in natural order | High | Positive |
| TC-029-02 | DS-07 shared device D02: residents, silent and device-gap day, last upload | High | Positive |
| TC-029-03 | DS-07 device replacement D07 → D07B: active flag, in-use dates, replaces / replaced by | High | Positive |
| TC-029-04 | DS-07 D08: 12 silent days and no device-gap day | High | Positive |
| TC-029-05 | Schema, `meta` and role access (API key 401, user roles 200) | High | Security |
| TC-029-06 | DS-07 `uploaded_on_as_of_date` true for the nine active devices, false for D07; fixture case false | High | Positive |
| TC-029-07 | Pagination with `limit` / `offset` and invalid values | Medium | Negative |
| TC-029-08 | Device values cross-checked with the database | Medium | Database |
| TC-029-09 | No succeeded run: 200 with `meta.as_of` null and empty day lists | Low | Negative |

### TC-029-01 DS-07 list has 10 devices in natural order

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s $API/devices -H "Authorization: Bearer $CLIN"` | HTTP 200 |
| 2 | Read `total` and `items[].device_code` | `total` 10; order D01, D02, D04, D05, D06, D07, D07B, D08, D09, D10 (D07 before D07B before D08) |
| 3 | Read `firmware_version` and `room_label` of every item | `firmware_version` "fw-1.0.0" for all; `room_label` null for all |

### TC-029-02 DS-07 shared device D02: residents, silent and device-gap day, last upload

| Step | Action | Expected Result |
|---|---|---|
| 1 | Find item `device_code` "D02" | `resident_codes` ["R02", "R03"]; `shared` true; `active` true |
| 2 | Day lists | `silent_days_last_30` ["2026-10-12"]; `device_gap_days_last_30` ["2026-10-12"] (R02's other missed days 4, 9, 10, 17, 23 Oct are not silent days because R03 still sent a record from D02) |
| 3 | Upload facts | `last_upload_at` "2026-10-30T19:55:23Z"; `last_upload_local` "2026-10-30T14:55:23-05:00"; `in_use_since` "2026-10-01"; `in_use_until` null; `replaces_device_code` null; `replaced_by_device_code` null |

### TC-029-03 DS-07 device replacement D07 → D07B: active flag, in-use dates, replaces / replaced by

| Step | Action | Expected Result |
|---|---|---|
| 1 | Item D07 | `active` false; `in_use_since` "2026-10-01"; `in_use_until` "2026-10-12"; `replaced_by_device_code` "D07B"; `replaces_device_code` null |
| 2 | Item D07B | `active` true; `resident_codes` ["R07"]; `shared` false; `replaces_device_code` "D07"; `replaced_by_device_code` null; `in_use_since` "2026-10-13"; `in_use_until` null; `last_upload_at` "2026-10-30T19:52:57Z"; `silent_days_last_30` []; `device_gap_days_last_30` [] |

### TC-029-04 DS-07 D08: 12 silent days and no device-gap day

| Step | Action | Expected Result |
|---|---|---|
| 1 | Item D08 | `resident_codes` ["R08"]; `shared` false |
| 2 | Count `silent_days_last_30` | 12 dates, ascending ISO dates, all between 2026-10-01 and 2026-10-30 |
| 3 | `device_gap_days_last_30` | [] (single-resident device: missed days are silent days but not device-gap days) |
| 4 | Cross-check: `SELECT local_date FROM day_ledger dl JOIN residents r ON r.id=dl.resident_id WHERE r.resident_code='R08' AND dl.status='missing_resident' ORDER BY local_date;` | The same 12 dates as `silent_days_last_30` |

### TC-029-05 Schema, `meta` and role access (API key 401, user roles 200)

| Step | Action | Expected Result |
|---|---|---|
| 1 | Validate the response against `DeviceList` from `GET $API/openapi.json` | Valid; keys `meta`, `items`, `total`, `limit` (50), `offset` (0) |
| 2 | `meta` | Seven fields; `as_of` "2026-10-30T20:00:00Z"; `facility_tz` "America/Chicago" |
| 3 | `GET $API/devices` with `$ADMIN`, `$CLIN`, `$RES` | 200 each, identical bodies |
| 4 | `GET $API/devices -H "X-API-Key: $KEY"` and with no credentials | 401 `NOT_AUTHENTICATED` each |
| 5 | Inspect item keys | No `id` or resident surrogate id; residents only as `resident_codes` |

### TC-029-06 DS-07 `uploaded_on_as_of_date` true for the nine active devices, false for D07; fixture case false

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read `uploaded_on_as_of_date` per item | true for D01, D02, D04, D05, D06, D07B, D08, D09, D10; false for D07 |
| 2 | Read `last_upload_at` of D07 | A timestamp on 2026-10-12 (local Oct 12, 2:14 PM CT, i.e. `2026-10-12T19:14:…Z`) |
| 3 | `pytest tests/integration/api/test_devices.py::test_device_panel -q` | Passes; includes a fixture device whose last record is the day before the as-of date and whose `uploaded_on_as_of_date` is false, a device without any upload (`last_upload_at` null) and a silent day on a single-resident device that is not a device-gap day |
| 4 | `GET $API/residents` after step 1 | Statuses unchanged by the upload flag (D07 false changes no resident status, D-115) |

### TC-029-07 Pagination with `limit` / `offset` and invalid values

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/devices?limit=3` | `items` D01, D02, D04; `total` 10; `limit` 3 |
| 2 | `GET $API/devices?limit=3&offset=5` | `items` D07, D07B, D08; `total` 10 |
| 3 | `GET $API/devices?limit=0` and `?offset=-1` | 422 `INVALID_QUERY_PARAMETER` each |

### TC-029-08 Device values cross-checked with the database

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT max(timestamp_utc) FROM raw_sessions rs JOIN devices d ON d.id=rs.device_id WHERE d.device_code='D02';` | 2026-10-30 19:55:23+00 = D02 `last_upload_at` |
| 2 | `SELECT firmware_version_last, active FROM devices WHERE device_code='D07';` | "fw-1.0.0", false = D07 `firmware_version`, `active` |
| 3 | `SELECT d.device_code, a.valid_from, a.valid_to FROM device_assignments a JOIN devices d ON d.id=a.device_id JOIN residents r ON r.id=a.resident_id WHERE r.resident_code='R07' ORDER BY valid_from;` | D07 2026-10-01..2026-10-12; D07B 2026-10-13..NULL — matches `in_use_since` / `in_use_until` |
| 4 | Row counts of all tables before and after the cases | Unchanged (read-only) |

### TC-029-09 No succeeded run: 200 with `meta.as_of` null and empty day lists

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker compose exec backend python -m backend.cli seed test_v0_1 --master-only --reset` | Exit 0 |
| 2 | `GET $API/devices` | HTTP 200; `meta.as_of` null; `total` 10; every `silent_days_last_30` and `device_gap_days_last_30` []; `last_upload_at` null for all; assignment facts use the current facility-local date |
| 3 | Restore with `seed test_v0_1 --reset` | DS-07 state again |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/devices` | 200 `DeviceList`; one item per `devices` row incl. retired; natural order |
| 2 | Item fields | `device_code`, `room_label`, `active`, `resident_codes`, `shared`, `replaces_device_code`, `replaced_by_device_code`, `in_use_since`, `in_use_until`, `last_upload_at`, `last_upload_local`, `firmware_version`, `uploaded_on_as_of_date`, `silent_days_last_30`, `device_gap_days_last_30` |
| 3 | Day lists | Ascending `YYYY-MM-DD` within the 30-day window ending on the as-of local date |
| 4 | Errors | 422 `INVALID_QUERY_PARAMETER` for bad paging; 401 for API key / anonymous; 503 with database down |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT count(*) FROM devices;` | 10 = `total` |
| 2 | `SELECT dl.local_date FROM day_ledger dl JOIN devices d ON d.id=dl.device_id WHERE d.device_code='D02' AND dl.status='missing_device_gap';` | Only 2026-10-12 (two rows, R02 and R03) |
| 3 | Assignments covering 2026-10-30 for D02 | R02 and R03 (shared, `shared_device_min_residents` 2) |
| 4 | No write | No table row count changes during the cases |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | `limit=0`, `limit=501`, `offset=-1` | 422 `INVALID_QUERY_PARAMETER` |
| 2 | API key or no credentials | 401 `NOT_AUTHENTICATED` |
| 3 | `docker compose stop db`, then `GET /devices` | 503 `SERVICE_UNAVAILABLE`, `Retry-After: 30`; `docker compose start db` afterwards |
| 4 | No succeeded run (TC-029-09) | 200, `meta.as_of` null, no 500 |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-029-AC-01 | `total` 10, order D01, D02, D04, D05, D06, D07, D07B, D08, D09, D10 | TC-029-01 |
| FEAT-029-AC-02 | D02 `resident_codes` [R02, R03], `shared` true, silent and device-gap days [2026-10-12], `last_upload_at` 2026-10-30T19:55:23Z | TC-029-02 |
| FEAT-029-AC-03 | D07 `active` false, 2026-10-01..2026-10-12, replaced by D07B; D07B replaces D07, since 2026-10-13, until null | TC-029-03 |
| FEAT-029-AC-04 | D08 has 12 silent days and empty device-gap days | TC-029-04 |
| FEAT-029-AC-05 | Validates against `DeviceList`, contains `meta`; API key 401; every user role 200 | TC-029-05 |
| FEAT-029-AC-06 | `uploaded_on_as_of_date` true for the nine active devices, false for D07; fixture device with last record the day before as-of: false | TC-029-06 |

## Test Data Requirements

- DS-07 (`seed test_v0_1`): devices D01, D02 (shared by R02, R03), D04–D06, D07 (retired 2026-10-12), D07B (from 2026-10-13), D08–D10; expected values from TRD 19 E-17 and TRD 11 §4.13.4.
- Integration fixture of `tests/integration/api/test_devices.py` (device without upload; last record the day before as-of).
- Master-only database for TC-029-09.
- Environment: `SEED_*` passwords, `SEED_INGEST_API_KEY` from the environment file.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-029-FR-01 (API-086, API-100; FR-150) | FEAT-029 | TC-029-01, TC-029-07 |
| FEAT-029-FR-02 (ING-045, ING-046; FR-150, FR-151) | FEAT-029 | TC-029-02 |
| FEAT-029-FR-03 (TRD 23 §4.4.2; FR-155) | FEAT-029 | TC-029-03 |
| FEAT-029-FR-04 (DB-066; FR-155) | FEAT-029 | TC-029-03, TC-029-08 |
| FEAT-029-FR-05 (API-086; FR-152) | FEAT-029 | TC-029-02, TC-029-08 |
| FEAT-029-FR-06 (DB-044; FR-154) | FEAT-029 | TC-029-02, TC-029-04 |
| FEAT-029-FR-07 (TRD 02 §4.1; FR-153) | FEAT-029 | TC-029-02, TC-029-04 |
| FEAT-029-FR-08 (API-069, API-094) | FEAT-029 | TC-029-04, TC-029-09 |
| FEAT-029-FR-09 (API-086, D-114; FR-152) | FEAT-029 | TC-029-06 |
| TDV-066 | FEAT-029 | TC-029-02, TC-029-03 |
| E2E-07 | FEAT-029 | TC-029-01, TC-029-02 |
| TST-061, TST-064 | FEAT-029 | TC-029-05 |
| TRD 13 Table 4.13-A (GET /devices) | FEAT-029 | TC-029-05 |
