# Epoch detection stage

## Feature Description

FEAT-042 implements `analytics/epoch_detection.py::assign_epochs(rows, late=())`. Per resident, all non-duplicate, non-late records (usable candidates and set-aside records alike) are sorted by `(timestamp_utc, arrival_seq)`; the first record starts epoch 1 and any record whose key (device_id, device_firmware_version, extraction_software_version) differs from the previous record's key starts a new epoch numbered previous + 1 (numbers are never reused, so A, B, A gives 1, 2, 3). The key uses the device code carried by the record, not the assignment table. Duplicates get `epoch_number` None; a late record takes the epoch of the last non-late record at or before it and never starts or splits an epoch. Each epoch has `started_at` = its first record's timestamp and `ended_at` = the next epoch's `started_at` (None for the current one). Baseline count, screen reference and CUSUM restart in each epoch. On SRC-05 R07 has epoch 1 (D07, 12 records, Oct 1–12) and epoch 2 from R07-20261013-01 on D07B; every other resident has one epoch.

## Preconditions

- Local development stack per `README.md` quick start; Python REPL started from the repository root with `import sys; sys.path.insert(0, ".")`.
- REPL helpers: `from tests.unit.analytics.factory import rec; from analytics.duplicate_detection import mark_duplicates as md; from analytics.quality_screening import apply_quality_gate as qg; from analytics.epoch_detection import assign_epochs as ae; from analytics.config import TEST_V0_1 as C` and the helper `def run(recs, late_ids=()): s = qg(md(recs), C); late = [x for x in s if x.record.session_id in late_ids]; return [(x.record.session_id, x.status, x.epoch_number, x.late_arrival) for x in ae(s, late)]`. `rec(seq, "YYYY-MM-DD HH:MM:SS", device=..., firmware=..., software=..., flag=..., session=...)` builds a synthetic R01 record (defaults D01, "fw-1.0.0", "openSMILE 3.0.2"; session id `R01-<date>-01`).
- Local PostgreSQL freshly seeded with `python -m backend.cli seed test_v0_1 --reset`; `psql` read access.
- Local Docker Compose (demo profile) with the same data; ADMIN_TOKEN from `POST /api/v1/auth/login` (`admin@example.com`, `SEED_ADMIN_PASSWORD`).

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-042-01 | Three records with the same key all get epoch 1 | High | Analytics |
| TC-042-02 | Device change D07 → D07B at record 13: records 1–12 epoch 1, 13+ epoch 2 | High | Analytics |
| TC-042-03 | Firmware-only and software-only changes each start a new epoch | High | Analytics |
| TC-042-04 | A set-aside record carrying a new key starts the new epoch | High | Analytics |
| TC-042-05 | Out-of-order input numbered by `(timestamp_utc, arrival_seq)`; a duplicate with a different key gets None | High | Analytics |
| TC-042-06 | Keys A, B, A give epochs 1, 2, 3 | High | Analytics |
| TC-042-07 | A late record inherits the preceding epoch and does not split it | Medium | Analytics |
| TC-042-08 | SRC-05 R07: epoch 1 (12 records, D07) and epoch 2 from R07-20261013-01 (D07B) with contiguous boundaries | High | Database |
| TC-042-09 | SRC-05: every other resident has exactly one epoch; set-aside records of R03/R08 are in epoch 1 | High | Database |
| TC-042-10 | Baseline and tally restart in the new epoch (R07) | High | Database |
| TC-042-11 | API shows R07's current epoch, epoch count and the baseline-restart event | Medium | API |
| TC-042-12 | Residents with only duplicates or no records, and naive timestamps | Medium | Negative |

### TC-042-01 Same key, one epoch

| Step | Action | Expected Result |
|---|---|---|
| 1 | `print(run([rec(i, f"2026-10-0{i} 19:00:00") for i in (1, 2, 3)]))` | `[('R01-20261001-01', 'pending_screen', 1, False), ('R01-20261002-01', 'pending_screen', 1, False), ('R01-20261003-01', 'pending_screen', 1, False)]` |
| 2 | `pytest -m unit tests/unit/analytics/test_epoch_detection.py -v` | `test_same_key_one_epoch`, `test_device_firmware_and_software_changes`, `test_set_aside_record_starts_an_epoch`, `test_time_order_and_duplicates`, `test_returning_key_gets_a_new_epoch`, `test_late_record_takes_the_previous_epoch`, `test_src05_r07_epochs` PASSED |

### TC-042-02 Device change at record 13

| Step | Action | Expected Result |
|---|---|---|
| 1 | `recs = [rec(i, f"2026-10-{i:02d} 19:00:00", device="D07" if i < 13 else "D07B") for i in range(1, 15)]; print([e for _, _, e, _ in run(recs)])` | `[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2]` |

### TC-042-03 Firmware-only and software-only changes

| Step | Action | Expected Result |
|---|---|---|
| 1 | `print(run([rec(1, "2026-10-01 19:00:00"), rec(2, "2026-10-02 19:00:00", firmware="fw-1.0.1")]))` | Epochs 1, 2 |
| 2 | `print(run([rec(1, "2026-10-01 19:00:00"), rec(2, "2026-10-02 19:00:00", software="openSMILE 3.0.3")]))` | Epochs 1, 2 |
| 3 | `print(run([rec(1, "2026-10-01 19:00:00"), rec(2, "2026-10-02 19:00:00", firmware="fw-1.0.1"), rec(3, "2026-10-03 19:00:00", firmware="fw-1.0.1", software="openSMILE 3.0.3")]))` | Epochs 1, 2, 3 |

### TC-042-04 Set-aside record with a new key starts the epoch

| Step | Action | Expected Result |
|---|---|---|
| 1 | `print(run([rec(1, "2026-10-01 19:00:00"), rec(2, "2026-10-02 19:00:00", device="D07B", flag="poor"), rec(3, "2026-10-03 19:00:00", device="D07B")]))` | `[('R01-20261001-01', 'pending_screen', 1, False), ('R01-20261002-01', 'set_aside', 2, False), ('R01-20261003-01', 'pending_screen', 2, False)]` |

### TC-042-05 Out-of-order input and a duplicate with a different key

| Step | Action | Expected Result |
|---|---|---|
| 1 | `print(run([rec(1, "2026-10-03 19:00:00"), rec(2, "2026-10-01 19:00:00"), rec(3, "2026-10-02 19:00:00", device="D07B"), rec(4, "2026-10-03 19:00:00", session="R01-20261001-01", device="D09")]))` | `[('R01-20261003-01', 'pending_screen', 3, False), ('R01-20261001-01', 'pending_screen', 1, False), ('R01-20261002-01', 'pending_screen', 2, False), ('R01-20261001-01', 'duplicate', None, False)]` — numbers follow time order (Oct 1 → 1, Oct 2 → 2, Oct 3 → 3); the duplicate on D09 has `None` and starts no epoch |
| 2 | Shuffle the input list of step 1 (same `arrival_seq` values) and repeat | Identical epoch numbers per session (output order follows `arrival_seq`) |

### TC-042-06 Keys A, B, A give 1, 2, 3

| Step | Action | Expected Result |
|---|---|---|
| 1 | `print(run([rec(1, "2026-10-01 19:00:00"), rec(2, "2026-10-02 19:00:00", device="D07B"), rec(3, "2026-10-03 19:00:00")]))` | Epochs 1, 2, 3 (the return to D01 does not reuse epoch 1) |

### TC-042-07 Late record inherits the preceding epoch

| Step | Action | Expected Result |
|---|---|---|
| 1 | `print(run([rec(1, "2026-10-01 19:00:00"), rec(2, "2026-10-03 19:00:00", device="D07B"), rec(3, "2026-10-02 19:00:00", device="D09")], late_ids=("R01-20261002-01",)))` | `[('R01-20261001-01', 'pending_screen', 1, False), ('R01-20261003-01', 'pending_screen', 2, False), ('R01-20261002-01', 'pending_screen', 1, True)]` — the late D09 record takes epoch 1 and creates no epoch 3 |
| 2 | Same with a late record timestamped before every other record of the resident | Late record `epoch_number` None |

### TC-042-08 SRC-05 R07 epochs

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT e.epoch_number, d.device_code, e.device_firmware_version, e.extraction_software_version, e.started_at, e.ended_at FROM epochs e JOIN residents r ON r.id = e.resident_id JOIN devices d ON d.id = e.device_id WHERE r.resident_code = 'R07' ORDER BY 1;` | 2 rows: (1, D07, fw-1.0.0, openSMILE 3.0.2, 2026-10-01 19:17:43+00, 2026-10-13 19:00:20+00) and (2, D07B, fw-1.0.0, openSMILE 3.0.2, 2026-10-13 19:00:20+00, NULL) |
| 2 | `SELECT e.epoch_number, count(*), min(p.local_date), max(p.local_date) FROM processed_sessions p JOIN epochs e ON e.id = p.epoch_id JOIN residents r ON r.id = p.resident_id WHERE r.resident_code = 'R07' GROUP BY 1 ORDER BY 1;` | (1, 12, 2026-10-01, 2026-10-12) and (2, 18, 2026-10-13, 2026-10-30) |
| 3 | `SELECT p.session_id, e.epoch_number, r2.device_code FROM processed_sessions p JOIN epochs e ON e.id = p.epoch_id JOIN raw_sessions r2 ON r2.id = p.raw_session_id WHERE p.session_id IN ('R07-20261012-01','R07-20261013-01') ORDER BY 1;` | R07-20261012-01 → epoch 1, D07; R07-20261013-01 → epoch 2, D07B (epoch follows the record's own `device_code`) |
| 4 | `pytest -m validation tests/validation/test_r07_device_move.py -v` | All PASSED (VC-R07) |

### TC-042-09 Every other resident has one epoch

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT r.resident_code, count(*) FROM epochs e JOIN residents r ON r.id = e.resident_id GROUP BY 1 ORDER BY 1;` | R01 1, R02 1, R03 1, R04 1, R05 1, R06 1, R07 2, R08 1, R09 1, R10 1 (11 epochs in total) |
| 2 | `SELECT count(*) FROM processed_sessions p JOIN epochs e ON e.id = p.epoch_id WHERE p.status = 'set_aside' AND e.epoch_number = 1;` | 12 (all R03/R08 set-aside records belong to epoch 1) |
| 3 | `SELECT count(*) FROM processed_sessions WHERE status = 'duplicate' AND epoch_id IS NOT NULL;` | 0 |
| 4 | `SELECT count(*) FROM epochs WHERE ended_at IS NULL;` | 10 (one current epoch per resident) |

### TC-042-10 Baseline and tally restart in the new epoch

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT e.epoch_number, b.n_sessions, b.first_session_id, b.frozen_after_session_id FROM baselines b JOIN epochs e ON e.id = b.epoch_id JOIN residents r ON r.id = b.resident_id WHERE r.resident_code = 'R07' AND b.feature_key = 'composite';` | One row only: (2, 16, R07-20261013-01, R07-20261028-01); no baseline for epoch 1 (12 usable sessions < 16) |
| 2 | `SELECT p.session_id, p.baseline_ordinal FROM processed_sessions p WHERE p.session_id IN ('R07-20261012-01','R07-20261013-01');` | R07-20261012-01 ordinal 12; R07-20261013-01 ordinal 1 (count restarts) |
| 3 | `SELECT p.session_id, s.cusum_tally FROM scores s JOIN processed_sessions p ON p.id = s.processed_session_id WHERE p.session_id LIKE 'R07-%' ORDER BY 1;` | R07-20261029-01 0.0; R07-20261030-01 0.0 (Exp_scores; tally starts at 0 in epoch 2) |

### TC-042-11 API shows R07's epochs

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents/R07` as admin | `epoch_count` = 2; `current_epoch.epoch_number` = 2; `current_epoch.device_code` = "D07B"; `current_epoch.started_on` = "2026-10-13"; `current_epoch.from_value` = "D07", `to_value` = "D07B"; `restart_cause` = "device"; `explanation.baseline_restarted_on` = "2026-10-13" |
| 2 | `GET /api/v1/residents/R07/checkins?from=2026-10-13&to=2026-10-13` | Contains an event with `event_type` = "baseline_restarted", `local_date` = "2026-10-13", `epoch_number` = 2, `detail` = "new epoch 2 on device D07B", `restart_cause` = "device", `previous_device_code` = "D07", `from_value` = "D07", `to_value` = "D07B" |
| 3 | `GET /api/v1/residents/R01` | `epoch_count` = 1; `restart_cause` = null |

### TC-042-12 Residents with only duplicates, no records, naive timestamps

| Step | Action | Expected Result |
|---|---|---|
| 1 | `print(ae([], ()))` | `[]`, no exception |
| 2 | `s = qg(md([rec(1, "2026-10-01 19:00:00", session="S1"), rec(2, "2026-10-01 19:00:00", session="S1", resident="R02", device="D02")]), C); print([(x.record.resident_code, x.status, x.epoch_number) for x in ae(s, ())])` | R01 `pending_screen` epoch 1; R02 `duplicate` epoch None; R02 gets no epoch and no error |
| 3 | `import dataclasses, datetime; r = rec(1, "2026-10-01 19:00:00"); dataclasses.replace(r, timestamp_utc=datetime.datetime(2026, 10, 1, 19))` | Raises `ContractError` "R01-20261001-01: timestamp_utc must be timezone-aware" |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents/R07` | `epoch_count` 2, current epoch 2 on D07B, `restart_cause` "device" (TC-042-11) |
| 2 | `GET /api/v1/residents/R07/checkins` | `baseline_restarted` event on 2026-10-13 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `epochs` rows per resident | 1 each, R07 2 (TC-042-09) |
| 2 | R07 epoch 1 `ended_at` = epoch 2 `started_at` | Both 2026-10-13 19:00:20+00 (TC-042-08) |
| 3 | Duplicates `epoch_id` | NULL |
| 4 | `SELECT count(*) FROM epochs e1 JOIN epochs e2 ON e1.resident_id = e2.resident_id AND e2.epoch_number = e1.epoch_number + 1 WHERE e1.ended_at IS DISTINCT FROM e2.started_at;` | 0 |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Duplicate carrying a different key | `epoch_number` None, no new epoch (TC-042-05) |
| 2 | Late record with a different key | Inherits the preceding epoch, no split (TC-042-07) |
| 3 | Resident with only duplicates / empty input | No epoch, no exception (TC-042-12) |
| 4 | Naive `timestamp_utc` | `ContractError` (TC-042-12) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-042-AC-01 | Three records with the same key all get epoch 1 | TC-042-01 |
| FEAT-042-AC-02 | D07 → D07B at record 13 gives 1–12 epoch 1 and 13+ epoch 2; firmware-only and software-only changes each start a new epoch | TC-042-02, TC-042-03 |
| FEAT-042-AC-03 | A set-aside record carrying a new key starts the new epoch at that record | TC-042-04 |
| FEAT-042-AC-04 | Out-of-order records numbered by `(timestamp_utc, arrival_seq)`; a duplicate with a different key gets None and starts no epoch | TC-042-05 |
| FEAT-042-AC-05 | Keys A, B, A give epochs 1, 2, 3 | TC-042-06 |
| FEAT-042-AC-06 | SRC-05 R07 epoch 1 = 12 records (2026-10-01..2026-10-12, D07), epoch 2 from R07-20261013-01 (D07B), epoch 1 `ended_at` = epoch 2 `started_at`; every other resident exactly one epoch | TC-042-08, TC-042-09 |

## Test Data Requirements

- SRC-05 (R07 records 1–12 on D07 `fw-1.0.0` / `openSMILE 3.0.2`, R07-20261013-01 onward on D07B) seeded with `test_v0_1`.
- SRC-03 `Exp_resident_outcomes` (R07 epoch 1 usable 12, epoch 2 usable 18, frozen after R07-20261028-01).
- Synthetic records from `tests/unit/analytics/factory.py::rec` (R01/R02, devices D01, D07, D07B, D09; firmware "fw-1.0.1"; software "openSMILE 3.0.3").

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-042-FR-01 | FEAT-042 | TC-042-04, TC-042-05 |
| FEAT-042-FR-02 | FEAT-042 | TC-042-01, TC-042-02, TC-042-03, TC-042-06 |
| FEAT-042-FR-03 | FEAT-042 | TC-042-08 |
| FEAT-042-FR-04 | FEAT-042 | TC-042-05, TC-042-09 |
| FEAT-042-FR-05 | FEAT-042 | TC-042-07 |
| FEAT-042-FR-06 | FEAT-042 | TC-042-08 |
| FEAT-042-FR-07 | FEAT-042 | TC-042-10 |
| FEAT-042-FR-08 | FEAT-042 | TC-042-05 |
| TRD 08 BSC-006..BSC-010 | FEAT-042 | TC-042-01..TC-042-10 |
| TRD 08 AC-BSC-05 (epoch part) | FEAT-042 | TC-042-08 |
| TRD 10 ING-047 | FEAT-042 | TC-042-08 |
| TRD 01 ARC-074 | FEAT-042 | TC-042-05 |
| TRD 13 EP-01..EP-07 | FEAT-042 | TC-042-01..TC-042-05 |
| TRD 14 VC-R07 | FEAT-042 | TC-042-08 |
| FR-050, FR-051 | FEAT-042 | TC-042-02, TC-042-08, TC-042-11 |
