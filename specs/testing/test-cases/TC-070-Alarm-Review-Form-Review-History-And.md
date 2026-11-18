# Device section of the resident chart

## Feature Description

The "Device" section of the resident chart (`/residents/[residentCode]/device`, wireframe v0.2): the panel "Device <D>" for the resident's current device with four facts — "Status" ("● Online" when the device uploaded on the as-of date, otherwise "○ No upload today"), "Last upload", "Firmware" and "Used by" ("This resident only" or "Shared with <codes>") —, the "History" list of the device's problems in the last 30 days (silent days of a shared device, a replacement, a firmware change), the empty text "No problems in the last 30 days." and the caption "Audio never leaves the device. Only voice measurements are uploaded.". A device without uploads does not change its residents' status (OQ-31, D-115). The feature ID previously named the v0.1 alarm review form; that content is now covered by FEAT-069 (TRD 11 §4.5.8, UX-430..UX-433, §4.13.3; TRD 04 §4.8 `DevicePanel`, FE-087; TRD 19 E-10, E-17).

## Preconditions

- Local Docker Compose demo profile running, seeded with `test_v0_1` and the DS-07 pipeline run (as-of Oct 30, 2026, 3:00 PM CT; `FACILITY_TZ=America/Chicago`).
- Signed in as `clinician@example.com` (`SEED_CLINICIAN_PASSWORD`).
- Browser developer tools (Network panel with request blocking); `psql` read access.
- `frontend/node_modules` installed for the component-test cases.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-070-01 | R03 shared device D02: facts and silent-day history | High | Positive |
| TC-070-02 | R07 replacement device D07B: facts and replacement history | High | Positive |
| TC-070-03 | R09 device without problems; caption on every resident | High | Positive |
| TC-070-04 | Entry points: Summary "Check the device" button and Device tile | Medium | Positive |
| TC-070-05 | Status not conveyed by colour alone; layout of facts and history | Medium | UI |
| TC-070-06 | No upload today: status fact, tile text, pill unchanged | High | Negative |
| TC-070-07 | History variants: firmware change, one/three affected residents, order | Medium | Positive |
| TC-070-08 | Devices request fails: error only in the Device panel | High | Negative |
| TC-070-09 | Device section has no audio and no controls | Medium | Security |
| TC-070-10 | Unknown resident on the device route | Medium | Negative |

### TC-070-01 R03 shared device

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R03/device` | Title "R03 · Device – EchoWell"; `<h2>` "Device D02" |
| 2 | Read the four facts | "● Online" (in `--green`) / "Status"; "Oct 30, 2:55 PM CT" / "Last upload"; "fw-1.0.0" / "Firmware"; "Shared with R02" / "Used by" (value 18px weight 700, label 13px `--muted`) |
| 3 | Read "History" | `<h3>` "History"; one row "Oct 12" "Silent all day. Affected R02 and R03." |
| 4 | Read the caption | "Audio never leaves the device. Only voice measurements are uploaded." (14px, `--muted`) |
| 5 | Note that the last upload is later than R03's own last check-in (Oct 30, 2:19 PM CT) | "Last upload" is the device's latest record from any resident on it (R02 at 2:55 PM CT) |
| 6 | Open `/residents/R02/device` | "Device D02", "Shared with R03", same history row |

### TC-070-02 R07 replacement device

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R07/device` | `<h2>` "Device D07B" |
| 2 | Read the facts | "● Online"; "Oct 30, 2:52 PM CT"; "fw-1.0.0"; "This resident only" |
| 3 | Read "History" | One row "Oct 13" "Replaced D07 with D07B. Baseline restarted." |
| 4 | Check that D07 (retired) has no own panel | Only the current device D07B is shown |

### TC-070-03 Device without problems

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R09/device` | "Device D09"; "● Online"; "Oct 30, 2:28 PM CT"; "fw-1.0.0"; "This resident only" |
| 2 | Read "History" | "No problems in the last 30 days." |
| 3 | Open the Device section of R01, R04, R05, R06, R08, R10 | Each shows "● Online", "This resident only", "No problems in the last 30 days." and ends with the caption "Audio never leaves the device. Only voice measurements are uploaded." |

### TC-070-04 Entry points

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `/residents/R08` click "Check the device" | Opens `/residents/R08/device` ("Device D08") |
| 2 | On `/residents/R09` click the "Device" tile ("D09 online") | Opens `/residents/R09/device` |
| 3 | Click "Device" in the section navigation | Link has `aria-current="page"` on the device route |

### TC-070-05 Colour independence and layout

| Step | Action | Expected Result |
|---|---|---|
| 1 | Emulate achromatopsia in developer tools on `/residents/R03/device` | Status still reads "● Online" (glyph and word) |
| 2 | Inspect the History row | Grid with an 80px `--muted` date column "Oct 12" and a text column |
| 3 | View at 375px | No horizontal page scroll; facts wrap |

### TC-070-06 No upload today

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `npx vitest run components/DevicePanel tests/pages/resident-device.test.tsx` in `frontend/` | Passes: fixture with `uploaded_on_as_of_date` false shows "○ No upload today" in `--muted`; the Summary tile reads "<D> no upload today"; the resident's pill and Summary are unchanged |
| 2 | **Optional on the isolated `echowell_demo` stack** (as-of = current time): open `/residents/R01/device` on a day with no new R01 record | "○ No upload today"; R01's pill stays "● Usual" on `/residents` (device silence does not set Needs attention) |

### TC-070-07 History variants

| Step | Action | Expected Result |
|---|---|---|
| 1 | In the `DevicePanel` component test, check the firmware-change case | Line "Firmware changed (<from> to <to>). Baseline restarted." |
| 2 | Check the device-gap cases with one and three residents | "Silent all day. Affected R01." and "Silent all day. Affected R01, R02 and R03." |
| 3 | Check ordering with several events | Newest first |

### TC-070-08 Devices request failure

| Step | Action | Expected Result |
|---|---|---|
| 1 | Block `*/api/v1/devices*` and open `/residents/R03/device` | Device panel shows "Could not load the device. Check your connection and try again." with "Try again"; banner and section navigation still render |
| 2 | Unblock and click "Try again" | Panel loads with "Device D02" |

### TC-070-09 No audio, no controls

| Step | Action | Expected Result |
|---|---|---|
| 1 | Inspect the Device section | No `<audio>` element, no recording or playback control, no link to audio |
| 2 | Look for controls to reassign, edit or delete the device | None (devices are managed by CLI and seed files) |

### TC-070-10 Unknown resident

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R99/device` | "Resident R99 was not found." with "← Resident list"; no Device panel |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/devices` (clinician) | 200; D02 with residents R02 and R03, `device_gap_days_last_30` including 2026-10-12, firmware "fw-1.0.0", last upload 2026-10-30T19:55…Z (2:55 PM CT), `uploaded_on_as_of_date` true |
| 2 | Same response, D07B and D07 | D07B `in_use_since` 2026-10-13, `replaces_device_code` "D07", `uploaded_on_as_of_date` true; D07 `uploaded_on_as_of_date` false, `replaced_by_device_code` "D07B" |
| 3 | `GET /api/v1/residents/R07/checkins` | `baseline_restarted` 2026-10-13 with `restart_cause` "device" (source of the replacement line) |
| 4 | `GET /api/v1/devices` without token | 401 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT d.device_code, r.resident_code, da.valid_from, da.valid_to FROM device_assignments da JOIN devices d ON d.id = da.device_id JOIN residents r ON r.id = da.resident_id WHERE d.device_code IN ('D02','D07','D07B') ORDER BY 1, 2;` | D02 → R02 and R03 (open-ended); D07 → R07 until 2026-10-12; D07B → R07 from 2026-10-13 |
| 2 | `SELECT device_code, firmware_version_last, active FROM devices ORDER BY device_code;` | All `fw-1.0.0`; D07 inactive; others active |
| 3 | `SELECT dl.local_date, r.resident_code FROM day_ledger dl JOIN residents r ON r.id = dl.resident_id WHERE dl.status = 'missing_device_gap';` | 2026-10-12 for R02 and R03 |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Devices request fails | Error only in the Device panel (TC-070-08) |
| 2 | Device did not upload on the as-of date | "○ No upload today", pill unchanged (TC-070-06) |
| 3 | Unknown resident | Not-found state (TC-070-10) |
| 4 | Device code missing from the devices list | Panel error state (FE-078; component test in TC-070-06) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-070-AC-01 | R03: "Device D02", "● Online", "Oct 30, 2:55 PM CT", "fw-1.0.0", "Shared with R02", "Oct 12 Silent all day. Affected R02 and R03." | TC-070-01 |
| FEAT-070-AC-02 | R07: "Device D07B", "● Online", "Oct 30, 2:52 PM CT", "fw-1.0.0", "This resident only", "Oct 13 Replaced D07 with D07B. Baseline restarted." | TC-070-02 |
| FEAT-070-AC-03 | R09: "Device D09", "● Online", "No problems in the last 30 days."; every Device section ends with the caption | TC-070-03 |
| FEAT-070-AC-04 | `uploaded_on_as_of_date` false → "○ No upload today", tile "<D> no upload today", pill unchanged | TC-070-06 |

## Test Data Requirements

- DS-07 `test_v0_1`: D02 shared by R02 and R03 with the device-gap day Oct 12; R07 replacement D07 → D07B on Oct 13; all firmware fw-1.0.0; last uploads per §4.13.3.
- Component-test fixtures for no-upload, firmware change and three-resident cases.
- Seeded clinician (`SEED_CLINICIAN_PASSWORD`).

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-070-FR-01 | FEAT-070 | TC-070-01, TC-070-02, TC-070-03 |
| FEAT-070-FR-02 | FEAT-070 | TC-070-01, TC-070-02, TC-070-03, TC-070-07 |
| FEAT-070-FR-03 | FEAT-070 | TC-070-01, TC-070-03 |
| FEAT-070-FR-04 | FEAT-070 | TC-070-06 |
| FEAT-070-FR-05 | FEAT-070 | TC-070-01 |
| FEAT-070-FR-06 | FEAT-070 | TC-070-05 |
| FEAT-070-FR-07 | FEAT-070 | TC-070-01, TC-070-02, TC-070-03 |
| UX-430 | FEAT-070 | TC-070-01, TC-070-02, TC-070-03 |
| UX-431 | FEAT-070 | TC-070-01, TC-070-02, TC-070-03, TC-070-07 |
| UX-432 | FEAT-070 | TC-070-03 |
| UX-433 | FEAT-070 | TC-070-06 |
| UX-004 | FEAT-070 | TC-070-05 |
| UX-202, FE-087 | FEAT-070 | TC-070-08 |
| UX-262 | FEAT-070 | TC-070-01, TC-070-02, TC-070-03 |
| E2E-10 | FEAT-070 | TC-070-02 |
| E2E-12 | FEAT-070 | TC-070-01 |
| TST-090, TST-094 | FEAT-070 | TC-070-06, TC-070-07 |
