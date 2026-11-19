# Read-model derivations (30-day window, last check-in, silent days, restart cause, in-use-until)

## Feature Description

FEAT-014 computes, in the repository layer (`backend/repositories/read_models.py`), every value the dashboard shows but the database never stores: the 30-day window (`d − 29` … `d`, never before `enrolled_on`) and its used / set aside / quarantined / missed counts, last check-in, baseline progress and dates, watching-since, alarm-since, alert tally and reviewed flag, baseline-restarted date, the scores series of an epoch, device silent days and device-gap days, an epoch's restart cause, a device's `in_use_until`, the attention flag inputs (open `baseline_stalled` / `high_set_aside` data alerts), the `checkins_started` source and a device's upload on the as-of date. The feature has no endpoint of its own; its values are observed through the read APIs (`GET /api/v1/residents`, `/residents/{resident_code}`, `/devices`, `/scores`), the matching screens, `psql` and the integration test `tests/integration/db/test_read_models.py`. All expected values are the answer-key values of the `test_v0_1` seed as of 2026-10-30 15:00 America/Chicago (TRD 06 AC-DB-05, TRD 23 §4.4, TRD 11 §4.13).

## Preconditions

- Local development stack running; `.env` from `.env.development.example` with `APP_ENV=local`, `PIPELINE_PROFILE=test_v0_1`, `FACILITY_TZ=America/Chicago`, `SEED_*` set.
- Database reset and seeded: `python -m backend.cli seed test_v0_1 --reset` (exit code 0); the seed runs the pipeline with `as_of` 2026-10-30T20:00:00Z (15:00 CDT).
- Bearer token of `admin@example.com` (password from `SEED_ADMIN_PASSWORD`) from `POST /api/v1/auth/login`, used as `Authorization: Bearer <token>` below.
- `psql` access to the local database (read-only `SELECT` statements).
- Frontend running at `http://localhost:3000` for the screen checks.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-014-01 | 30-day activity counts for R02, R03, R08 and the missed sum of 19 | High | API |
| TC-014-02 | Duplicates never counted (R04 used stays 30) and R05 held-back count | High | Positive |
| TC-014-03 | R09 last check-in is 2026-10-30 14:28 in America/Chicago | High | API |
| TC-014-04 | D02 and D08 silent days and D02 device-gap days | High | API |
| TC-014-05 | R07 restart cause `device` (D07 → D07B); epoch 1 has none | High | API |
| TC-014-06 | D07 `in_use_until` 2026-10-12; D07B `in_use_until` NULL | High | API |
| TC-014-07 | Baseline progress, watching-since and alarm-since of R08, R09, R10 | High | API |
| TC-014-08 | Alert tally, open days and reviewed flag of R09 and R10; R07 baseline restarted Oct 13 | Medium | UI |
| TC-014-09 | R09 scores series: 14 rows ascending with baseline period Oct 1–16 within 50 ms | High | Database |
| TC-014-10 | No table or column stores a derived value | High | Database |
| TC-014-11 | Attention flag, `checkins_started` source and uploads on the as-of date | High | API |
| TC-014-12 | Device values: assigned residents, shared flag, replaced-by / was, last upload, firmware | Medium | API |
| TC-014-13 | Window clipping at `enrolled_on` | Medium | Positive |
| TC-014-14 | Resident without a current epoch (R11 overlay) gets 0 of 16 and no dates | Medium | Negative |
| TC-014-15 | Automated read-model suite passes | High | Positive |

### TC-014-01 30-day activity counts for R02, R03, R08 and the missed sum of 19

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents` with the admin token | 200; `window.from` = `2026-10-01`, `window.to` = `2026-10-30`; `total` = 10 |
| 2 | Read `last_30_days` of the R02 row | `{"used": 24, "set_aside": 0, "quarantined": 0, "missed": 6}` |
| 3 | Read `last_30_days` of the R03 row | `{"used": 22, "set_aside": 7, "quarantined": 0, "missed": 1}` |
| 4 | Read `last_30_days` of the R08 row | `{"used": 13, "set_aside": 5, "quarantined": 0, "missed": 12}` |
| 5 | Sum `last_30_days.missed` over R01–R10 | 19 |
| 6 | Read R01, R04, R06, R07, R09, R10 | Each `{"used": 30, "set_aside": 0, "quarantined": 0, "missed": 0}` |
| 7 | Open `http://localhost:3000/residents/R08` and find the check-in counts | Used / Set aside / Held back / Missed shows 13 / 5 / 0 / 12 (TRD 11 §4.13.3) |

### TC-014-02 Duplicates never counted (R04 used stays 30) and R05 held-back count

| Step | Action | Expected Result |
|---|---|---|
| 1 | In `psql`: `SELECT count(*) FROM processed_sessions p JOIN residents r ON r.id = p.resident_id WHERE r.resident_code = 'R04' AND p.status = 'duplicate';` | 2 |
| 2 | `GET /api/v1/residents/R04` | `last_30_days.used` = 30; no count field includes the 2 duplicates |
| 3 | `GET /api/v1/residents/R05` | `last_30_days` = `{"used": 28, "set_aside": 0, "quarantined": 2, "missed": 0}` |

### TC-014-03 R09 last check-in is 2026-10-30 14:28 in America/Chicago

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents/R09` | `last_checkin_local` starts with `2026-10-30T14:28` and ends with `-05:00`; `last_checkin_at` is the same instant in UTC ending with `Z` (`2026-10-30T19:28…Z`) |
| 2 | In `psql`: `SELECT max(p.timestamp_utc) FROM processed_sessions p JOIN residents r ON r.id = p.resident_id WHERE r.resident_code = 'R09' AND p.status <> 'duplicate';` | Same instant as `last_checkin_at` |
| 3 | Open the resident list in the browser | R09 row shows "Oct 30, 2:28 PM CT" in the Last check-in column |

### TC-014-04 D02 and D08 silent days and D02 device-gap days

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/devices` and read the D02 item | `silent_days_last_30` = `["2026-10-12"]`; `device_gap_days_last_30` = `["2026-10-12"]` |
| 2 | Read the D08 item | `silent_days_last_30` has 12 dates |
| 3 | In `psql`: `SELECT d.local_date FROM day_ledger d JOIN residents r ON r.id = d.resident_id WHERE r.resident_code = 'R08' AND d.status = 'missing_resident' ORDER BY 1;` | 12 dates, identical to D08's `silent_days_last_30` |
| 4 | Read the D01, D04, D05, D06, D09, D10 items | `silent_days_last_30` = `[]` and `device_gap_days_last_30` = `[]` |

### TC-014-05 R07 restart cause `device` (D07 → D07B); epoch 1 has none

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents/R07` | `restart_cause` = `"device"`; `current_epoch.epoch_number` = 2; `current_epoch.from_value` = `"D07"`; `current_epoch.to_value` = `"D07B"`; `device.previous_device_code` = `"D07"`; `epoch_count` = 2 |
| 2 | `GET /api/v1/residents/R01` | `restart_cause` = `null`; `current_epoch.epoch_number` = 1; `from_value` and `to_value` = `null` |
| 3 | `GET /api/v1/residents/R07/checkins` | One event with `event_type` `"baseline_restarted"` on `2026-10-13` with `restart_cause` `"device"`, `previous_device_code` `"D07"`, `from_value` `"D07"`, `to_value` `"D07B"`; no restart event for epoch 1 |

### TC-014-06 D07 `in_use_until` 2026-10-12; D07B `in_use_until` NULL

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/devices`, item D07 | `in_use_until` = `"2026-10-12"`; `active` = `false`; `replaced_by_device_code` = `"D07B"` |
| 2 | Item D07B | `in_use_until` = `null`; `in_use_since` = `"2026-10-13"`; `replaces_device_code` = `"D07"` |
| 3 | Item D01 | `in_use_until` = `null` (assignment covers 2026-10-30) |

### TC-014-07 Baseline progress, watching-since and alarm-since of R08, R09, R10

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents/R08` | `baseline.n_usable` = 13, `baseline.n_required` = 16, `baseline.state` = `"forming"`; `watching_since` = `null`; `alarm_since` = `null` |
| 2 | `GET /api/v1/residents/R09` | `baseline.state` = `"frozen"`, `n_usable` 16 of 16; `baseline.first_local_date` = `"2026-10-01"`; `baseline.frozen_after_local_date` = `"2026-10-16"`; `watching_since` = `"2026-10-17"`; `alarm_since` = `"2026-10-21"` |
| 3 | `GET /api/v1/residents/R10` | `alarm_since` = `"2026-10-24"`; `watching_since` = `"2026-10-17"` |
| 4 | In the `GET /api/v1/residents` R08 row | `baseline_progress` = `{"n_usable": 13, "n_required": 16}` |

### TC-014-08 Alert tally, open days and reviewed flag of R09 and R10; R07 baseline restarted Oct 13

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents/R09` | `current_tally` rounds to 26.8 at 1 decimal; `alarm_reviewed` = `false`; `open_alert_id` is a UUID |
| 2 | `GET /api/v1/residents/R10` | `current_tally` rounds to 13.4 at 1 decimal; `alarm_reviewed` = `false` |
| 3 | Open `http://localhost:3000/residents/R09` Summary | Facts "Oct 21" Alarm started, "9 days" Open, "Not reviewed" Review status; tile "Change score 26.8" |
| 4 | Open R10 Summary | Alarm Oct 24, "6 days" Open; tile "Change score 13.4" |
| 5 | `GET /api/v1/residents` R07 row | `baseline_restarted_on` = `"2026-10-13"`; R01 row `baseline_restarted_on` = `null` |

### TC-014-09 R09 scores series: 14 rows ascending with baseline period Oct 1–16 within 50 ms

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/scores?resident_code=R09&epoch=1` | 200; `total` = 14; items' `local_date` run from `2026-10-17` to `2026-10-30` in ascending order; each item has `cusum_tally` and `alarm_state`; `baseline_periods` has one entry for R09 epoch 1 with `first_local_date` `2026-10-01`, `frozen_after_local_date` `2026-10-16`, `n_sessions` 16 |
| 2 | In `psql`: `EXPLAIN (ANALYZE, BUFFERS) SELECT s.* FROM scores s JOIN epochs e ON e.id = s.epoch_id JOIN residents r ON r.id = e.resident_id WHERE r.resident_code = 'R09' AND e.ended_at IS NULL ORDER BY s.local_date;` | `Execution Time` ≤ 50 ms; 14 rows |
| 3 | `GET /api/v1/residents/R09` | Baseline period `baseline.first_local_date` `2026-10-01`, `baseline.frozen_after_local_date` `2026-10-16` |

### TC-014-10 No table or column stores a derived value

| Step | Action | Expected Result |
|---|---|---|
| 1 | In `psql`: `SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = 'public' AND column_name IN ('last_checkin','silent_days','in_use_until','restart_cause','watching_since','needs_attention','uploaded_on_as_of_date');` | 0 rows |
| 2 | Run `grep -rn "INSERT\|UPDATE\|\.add(" backend/repositories/read_models.py` | No write statement (read-only module) |

### TC-014-11 Attention flag, `checkins_started` source and uploads on the as-of date

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents` | R03 `needs_attention` `true`, `attention_reasons` `["high_set_aside"]`; R08 `needs_attention` `true`, `attention_reasons` `["baseline_stalled"]`; the other 8 rows `needs_attention` `false`, `attention_reasons` `[]` |
| 2 | In `psql`: `SELECT r.resident_code, a.kind FROM data_alerts a JOIN residents r ON r.id = a.resident_id WHERE a.status = 'open' AND a.kind IN ('baseline_stalled','high_set_aside') ORDER BY 1;` | Exactly `R03 high_set_aside` and `R08 baseline_stalled` |
| 3 | `GET /api/v1/residents/R07/checkins` and read the oldest event | `event_type` `"checkins_started"` on `2026-10-01` with `device_code` `"D07"` |
| 4 | Repeat step 3 for R01 | `checkins_started` on `2026-10-01` |
| 5 | `GET /api/v1/devices` | D07 `uploaded_on_as_of_date` = `false`; D01, D02, D04, D05, D06, D07B, D08, D09, D10 each `true` |
| 6 | Open the R07 check-in log in the browser | Oldest line "Oct 1 Check-ins started on D07." |

### TC-014-12 Device values: assigned residents, shared flag, replaced-by / was, last upload, firmware

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/devices`, item D02 | `resident_codes` = `["R02","R03"]`; `shared` = `true`; `last_upload_local` starts with `2026-10-30T14:55`; `firmware_version` = `"fw-1.0.0"` |
| 2 | Item D07B | `resident_codes` = `["R07"]`; `shared` = `false`; `last_upload_local` starts with `2026-10-30T14:52` |
| 3 | Item D07 | `last_upload_local` starts with `2026-10-12T14:14` |
| 4 | `GET /api/v1/residents` | R02 and R03 rows `device_code` `"D02"`, `device_shared` `true`; R07 row `device_code` `"D07B"`, `previous_device_code` `"D07"` |
| 5 | In `psql`: `SELECT max(timestamp_utc) FROM raw_sessions rs JOIN devices d ON d.id = rs.device_id WHERE d.device_code = 'D02';` | Same instant as D02 `last_upload_at` |

### TC-014-13 Window clipping at `enrolled_on`

| Step | Action | Expected Result |
|---|---|---|
| 1 | In a Python REPL: `from datetime import date; from backend.repositories.read_models import window_for; w = window_for(date(2026,10,20), date(2026,10,30)); print(w)` | Window from `2026-10-20` to `2026-10-30` (start clipped to `enrolled_on`; `w.days()` = 11) |
| 2 | `window_for(date(2026,9,1), date(2026,10,30))` | Window from `2026-10-01` to `2026-10-30` (`d − 29`; 30 days) |

### TC-014-14 Resident without a current epoch (R11 overlay) gets 0 of 16 and no dates

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `python -m backend.cli import-master-data --dir tests/fixtures/seeds/demo_overlay` | Exit code 0; stderr `Loaded 1 residents, 1 devices, 1 assignments.` |
| 2 | `GET /api/v1/residents/R11` (no pipeline run since import) | 200; `baseline.n_usable` = 0, `baseline.n_required` = 16; `current_epoch` = `null`; `watching_since`, `alarm_since`, `last_checkin_at` = `null`; `restart_cause` = `null` |
| 3 | `GET /api/v1/devices`, item D11 | `silent_days_last_30` = `[]` (no ledger rows); `last_upload_at` = `null`; `uploaded_on_as_of_date` = `false` |
| 4 | Reset afterwards: `python -m backend.cli seed test_v0_1 --reset` | Exit code 0; R11 no longer present |

### TC-014-15 Automated read-model suite passes

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `pytest -m integration tests/integration/db/test_read_models.py -q` | All tests pass, `0 failed` |

Note: FEAT-014 is aligned to the TRD (TRD 24 D-184): it names `tests/integration/db/test_read_models.py` for the window, restart-cause and silent-day checks (there is no separate unit file); they are also covered here by TC-014-13.

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents` (admin) | 200; each item has `last_30_days {used, set_aside, quarantined, missed}`, `baseline_progress {n_usable, n_required}`, `needs_attention`, `attention_reasons`, `alarm_since`, `restart_cause`, `last_checkin_at`, `last_checkin_local`; `meta.as_of` = `2026-10-30T20:00:00Z` |
| 2 | `GET /api/v1/residents/R09` | 200; `ResidentDetail` with `watching_since`, `alarm_since`, `current_tally`, `baseline.first_local_date`, `baseline.frozen_after_local_date`, `window` |
| 3 | `GET /api/v1/devices` | 200; each item has `in_use_until`, `silent_days_last_30`, `device_gap_days_last_30`, `uploaded_on_as_of_date`, `resident_codes`, `shared` |
| 4 | `GET /api/v1/scores?resident_code=R09&epoch=1` | 200; `total` 14, ascending `local_date` |
| 5 | Repeat step 1 twice | Byte-identical `items` apart from `X-Request-ID` (values recomputed per request from stored rows) |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `information_schema.columns` for the seven derived names (TC-014-10) | 0 rows |
| 2 | Missed sum: `SELECT count(*) FROM day_ledger WHERE status IN ('missing_resident','missing_device_gap') AND local_date BETWEEN '2026-10-01' AND '2026-10-30';` | 19 |
| 3 | `SELECT d.local_date, d.status FROM day_ledger d JOIN devices v ON v.id = d.device_id WHERE v.device_code = 'D02' AND d.status <> 'checked_in';` | 2 rows, both `2026-10-12`, status `missing_device_gap` (R02 and R03) |
| 4 | `SELECT max(valid_to) FROM device_assignments a JOIN devices d ON d.id = a.device_id WHERE d.device_code = 'D07';` | `2026-10-12` |
| 5 | `SELECT epoch_number, device_id IS NOT NULL FROM epochs e JOIN residents r ON r.id = e.resident_id WHERE r.resident_code = 'R07' ORDER BY 1;` | 2 rows: epoch 1 and epoch 2 |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Resident with no current epoch (R11, TC-014-14) | Baseline 0 of 16; `watching_since`, `alarm_since` `null`; no error |
| 2 | Resident enrolled after `d − 29` (TC-014-13) | Window starts at `enrolled_on`, never before |
| 3 | Device with no ledger rows (D11) | `silent_days_last_30` = `[]` |
| 4 | Epoch 1 resident (R01) | `restart_cause` = `null` |
| 5 | `GET /api/v1/residents/R99` | 404 `RESIDENT_NOT_FOUND` Problem body; no derived value computed |
| 6 | Stop the database (`docker compose stop db`) and call `GET /api/v1/residents` | 503 `SERVICE_UNAVAILABLE` with `Retry-After: 30` (FEAT-019 mapping); restart with `docker compose start db` |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-014-AC-01 | R02 24·0·0·6, R03 22·7·0·1, R08 13·5·0·12; missed sum over R01–R10 = 19 | TC-014-01, TC-014-15 |
| FEAT-014-AC-02 | R09 last check-in = 2026-10-30 14:28 America/Chicago | TC-014-03, TC-014-15 |
| FEAT-014-AC-03 | D02 silent days {2026-10-12}; D08 silent days = R08's 12 missing days; D02 device-gap days {2026-10-12} | TC-014-04, TC-014-15 |
| FEAT-014-AC-04 | R07 epoch 2 restart cause `device`, previous D07, from D07, to D07B; epoch 1 none | TC-014-05, TC-014-15 |
| FEAT-014-AC-05 | D07 `in_use_until` 2026-10-12; D07B NULL | TC-014-06, TC-014-15 |
| FEAT-014-AC-06 | R08 13 of 16; R09 watching-since 2026-10-17, alarm-since 2026-10-21; R10 alarm-since 2026-10-24 | TC-014-07, TC-014-15 |
| FEAT-014-AC-07 | R09 scores series 14 rows ascending, baseline Oct 1–16, ≤ 50 ms database time | TC-014-09, TC-014-15 |
| FEAT-014-AC-08 | No column named `last_checkin`, `silent_days`, `in_use_until`, `restart_cause`, `watching_since`, `needs_attention`, `uploaded_on_as_of_date` | TC-014-10, TC-014-15 |
| FEAT-014-AC-09 | Attention flag R03 [high_set_aside], R08 [baseline_stalled] only; first record of every resident 2026-10-01 (R07 on D07); D07 no upload on 2026-10-30, nine active devices uploaded | TC-014-11, TC-014-15 |

## Test Data Requirements

- `test_v0_1` seed with the SRC-05 records and the pipeline run as of 2026-10-30 15:00 America/Chicago (`seed test_v0_1 --reset`).
- DS-07 reference values of TRD 11 §4.13 (resident list rows, resident chart banners and counts, Study team devices table).
- Fixture overlay `tests/fixtures/seeds/demo_overlay` (R11, D11) for TC-014-14 only; reset afterwards.
- Seeded user `admin@example.com` with `SEED_ADMIN_PASSWORD`.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-014-FR-01 / DB-041 / D-42 | FEAT-014 | TC-014-01, TC-014-13 |
| FEAT-014-FR-02 / DB-041 / FR-135 / AGT-053 / AC-DB-05 | FEAT-014 | TC-014-01, TC-014-02 |
| FEAT-014-FR-03 / DB-045 | FEAT-014 | TC-014-03 |
| FEAT-014-FR-04 / DME-012 | FEAT-014 | TC-014-07 |
| FEAT-014-FR-05 / D-41 | FEAT-014 | TC-014-07 |
| FEAT-014-FR-06 / DME-012 | FEAT-014 | TC-014-07, TC-014-08 |
| FEAT-014-FR-07 / DME-012 | FEAT-014 | TC-014-08 |
| FEAT-014-FR-08 / DB-043 | FEAT-014 | TC-014-09 |
| FEAT-014-FR-09 / DB-044 / FR-154 | FEAT-014 | TC-014-04, TC-014-14 |
| FEAT-014-FR-10 / DB-065 / D-64 | FEAT-014 | TC-014-05 |
| FEAT-014-FR-11 / DB-066 / D-64 | FEAT-014 | TC-014-06 |
| FEAT-014-FR-12 / TRD 23 §4.4.2 | FEAT-014 | TC-014-12 |
| FEAT-014-FR-13 / DME-011 / D-114 | FEAT-014 | TC-014-11 |
| FEAT-014-FR-14 / DME-012 | FEAT-014 | TC-014-10 |
| FEAT-014-FR-15 / TRD 23 §4.4.4 / D-113 | FEAT-014 | TC-014-05, TC-014-11 |
| FEAT-014-FR-16 / TRD 23 §4.4.2 / D-114 | FEAT-014 | TC-014-11 |
| UX-058, UX-260, UX-262, UX-263 (DS-07 rendering) | FEAT-014 (inputs) | TC-014-01, TC-014-03, TC-014-08, TC-014-11 |
