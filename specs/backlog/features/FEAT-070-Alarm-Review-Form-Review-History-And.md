# FEAT-070 Device section of the resident chart

| Field | Value |
|---|---|
| Epic | Frontend |
| Build phase | Phase 8 (TRD 25) |
| Priority | P1 |
| Complexity | Low |
| MVP status | Required |
| Dependencies | FEAT-066, FEAT-029 |
| Status | Not Started |

## Purpose

Implement the "Device" section of the resident chart (`/residents/[residentCode]/device`), new in wireframe v0.2 (SRC-21, TRD 24 D-110): the panel "Device <D>" for the resident's current device with four facts — Status ("● Online" when the device uploaded on the as-of date, otherwise "○ No upload today"), Last upload, Firmware and Used by ("This resident only" or "Shared with <codes>") —, the "History" list of the device's problems in the last 30 days (silent days of a shared device, a replacement, a firmware change), the empty text "No problems in the last 30 days." and the caption "Audio never leaves the device. Only voice measurements are uploaded." "Check the device" on the Summary of a Needs-attention resident and the Summary's Device tile lead here. A device without uploads does not turn its residents to Needs attention (OQ-31 answered, TRD 24 D-115): this section only reports the upload state, and device silence stays a study-team item.

This feature ID was the v0.1 "Alarm review form, review history and snooze" on the retired Alert review page. Wireframe v0.2 moves the review form, reminder and review history into the chart's "Review and notes" section, where they are delivered together with the review panel by FEAT-069 (TRD 11 §4.17); the ID and file name are kept (TRD 25 §4.2) and reused for the new Device section so that no feature ID is left empty.

## Business Context

- BR-12 (staff can check a resident's device when check-ins are missing), BR-06 (silent days of a shared device are shown, never filled), BR-08 (device replacement and firmware change restart the baseline), BR-01 (no audio leaves the device).
- OQ-31, answered by TRD 24 D-115: a silent device is a device-health item and does not change the resident's status (UX-433).
- D-110 (Device section), D-114 (`uploaded_on_as_of_date` on `Device`).
- FRs covered (BACKLOG.md): FR-151, FR-152, FR-153, FR-155.

## Referenced TRDs

- TRD 11 (v0.13) — owned by this feature: UX-430 (panel and four facts), UX-431 (History list and empty text), UX-432 (caption), UX-433 (no status change, D-115), §4.8 "Online / No upload today", Device section values of §4.13.3 (R03, R07, others).
- TRD 04 §4.8 `DevicePanel` (as updated for wireframe v0.2), FE-087 (per-panel errors).
- TRD 19 E-17 `GET /api/v1/devices` (`Device`: `uploaded_on_as_of_date`, last upload, firmware, assigned residents, `device_gap_days_last_30`, `in_use_since`, `replaces_device_code`); E-10 check-in events (`baseline_restarted` with `restart_cause` `firmware`, `from_value`, `to_value`).
- TRD 02 FR-151, FR-152, FR-153, FR-155; TRD 24 D-110, D-114, OQ-31.
- TRD 13 E2E-12 (R03 device), E2E-10 (R07 device), TST-090.

## Scope

- `app/(protected)/residents/[residentCode]/device/page.tsx`: `DevicePanel` from the devices query of FEAT-066's layout and the resident's check-in events (firmware changes).
- History wording ("Silent all day. Affected <R> and <R>.", "Replaced <old D> with <D>. Baseline restarted.", "Firmware changed (<from> to <to>). Baseline restarted.") in `lib/wording.ts`.

## Out of Scope

- Device data derivation (`uploaded_on_as_of_date`, silent days, device-gap days, replacement; FEAT-029, FEAT-014).
- The Study team "Devices" section with all devices (FEAT-072).
- Any rule that changes a resident's status because a device is offline (OQ-31).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-070-FR-01 | The Device section shall show a panel headed "Device <D>" (h2, the resident's current device) with four facts (value 18px weight 700 above a 13px `--muted` label): "● Online" in `--green` when the API reports `uploaded_on_as_of_date` true, otherwise "○ No upload today" in `--muted` / "Status"; "<last upload date-time>" / "Last upload"; "<firmware version>" / "Firmware"; "This resident only" or "Shared with <other resident codes>" / "Used by". | UX-430, FR-152, D-114 |
| FEAT-070-FR-02 | Below the facts, a heading "History" (h3) shall list the device events of the last 30 days newest first (grid: 80px `--muted` date column "<Mon D>", text column): each device-gap day "Silent all day. Affected <R> and <R>." (one resident: "Affected <R>."; three or more: "Affected R01, R02 and R03."); a replacement "Replaced <old D> with <D>. Baseline restarted."; a firmware change "Firmware changed (<from> to <to>). Baseline restarted."; with none, "No problems in the last 30 days." | UX-431, FR-153, FR-155, BR-06, BR-08 |
| FEAT-070-FR-03 | The panel shall end with the caption (14px, `--muted`) "Audio never leaves the device. Only voice measurements are uploaded." | UX-432, BR-01 |
| FEAT-070-FR-04 | The section shall report the upload state only and shall not change the resident's display status, pill or Summary (OQ-31). | UX-433 |
| FEAT-070-FR-05 | "Last upload" shall be the device's latest non-duplicate record from any resident on it, formatted "Oct 30, 2:55 PM CT" in `meta.facility_tz`. | UX-430, UX-002 |
| FEAT-070-FR-06 | The status fact shall not rely on colour: it carries the glyph "●" or "○" and the words "Online" or "No upload today". | UX-004 |
| FEAT-070-FR-07 | With the reference data the section shall render TRD 11 §4.13.3: R03 "Device D02", "● Online", "Oct 30, 2:55 PM CT", "fw-1.0.0", "Shared with R02", History "Oct 12 Silent all day. Affected R02 and R03."; R07 "Device D07B", "● Online", "Oct 30, 2:52 PM CT", "fw-1.0.0", "This resident only", History "Oct 13 Replaced D07 with D07B. Baseline restarted."; every other resident "No problems in the last 30 days." | UX-262 (values), UX-430, UX-431 |

## Inputs

- `GET /api/v1/devices?limit=500` (FEAT-066 layout query `["devices"]`) → the resident's current device: code, `uploaded_on_as_of_date`, last upload, firmware, assigned residents, `device_gap_days_last_30`, `in_use_since`, `replaces_device_code`.
- `ResidentDetail` (current device code) and the resident's check-in events (`baseline_restarted` with cause `firmware`); `meta.facility_tz`, `meta.as_of`.

## Outputs

- Rendered Device panel with facts, History list or empty text, and caption.

## Data Flow

Layout queries (FEAT-066) → current device code → device row from `["devices"]` → facts (`uploaded_on_as_of_date`, last upload, firmware, assigned residents) → History built from `device_gap_days_last_30`, `in_use_since` + `replaces_device_code` (within the last 30 days) and firmware restart events → newest first → `DevicePanel`.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-066, FEAT-029

- FEAT-066 provides the chart layout, the `/device` route shell and the devices query.
- FEAT-029 provides `GET /api/v1/devices` with `uploaded_on_as_of_date` (D-114).

Features that build directly on this one (BACKLOG.md §4): FEAT-075.

## Database Impact

None (frontend only).

## API Impact

Endpoints consumed: `GET /api/v1/devices` (E-17) and `GET /api/v1/residents/{resident_code}/checkins` (E-10), both through FEAT-066's and FEAT-068's queries. None exposed.

## Frontend Impact

- Section page `app/(protected)/residents/[residentCode]/device/page.tsx`.
- Component: `DevicePanel`; wording in `lib/wording.ts`.

## Analytics Impact

None. The online state and silent days come from the API.

## Security Requirements

- Study IDs and device codes only; no audio and no link to audio (UX-006, BR-01).

## Error Handling

- Devices query error → error state inside the Device panel only (UX-202).
- A device code missing from the devices list → panel error state (FE-078).

## Logging Requirements

None in the frontend.

## Testing Requirements

- Component (`components/DevicePanel/DevicePanel.test.tsx`, TST-090): online and no-upload facts with glyphs, shared and single-resident "Used by", history lines for a device-gap day (two and three residents), a replacement and a firmware change, newest-first order, the empty text and the caption.
- Page test: panel error isolation; no status change when `uploaded_on_as_of_date` is false (TST-094).
- E2E: E2E-12 (R03 Device section), E2E-10 (R07 Device section), as updated in TRD 13 Table 4.10-A for v0.2.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-070-AC-01 | `/residents/R03/device` shows "Device D02", "● Online" / Status, "Oct 30, 2:55 PM CT" / Last upload, "fw-1.0.0" / Firmware, "Shared with R02" / Used by, and History "Oct 12 Silent all day. Affected R02 and R03." | E2E-12; UX-430; UX-431 |
| FEAT-070-AC-02 | `/residents/R07/device` shows "Device D07B", "● Online", "Oct 30, 2:52 PM CT", "fw-1.0.0", "This resident only" and History "Oct 13 Replaced D07 with D07B. Baseline restarted." | E2E-10; UX-431 |
| FEAT-070-AC-03 | `/residents/R09/device` shows "Device D09", "● Online" and "No problems in the last 30 days.", and every Device section ends with "Audio never leaves the device. Only voice measurements are uploaded." | UX-431; UX-432 |
| FEAT-070-AC-04 | With a fixture whose device has `uploaded_on_as_of_date` false, the section shows "○ No upload today", the Summary tile reads "<D> no upload today" and the resident's pill is unchanged. Verified by: Component and Page test (TST-090, TST-094). | UX-433; OQ-31 |

## Definition of Done

- All FEAT-070 acceptance criteria pass; component, page and E2E tests green.
- Batch report lists IDs and records that FEAT-070 now holds the Device section (its v0.1 scope moved to FEAT-069) (AGT-022).

## Implementation Notes

- "Online" = a non-duplicate record from the device on the as-of local date (TRD 11 §4.8, D-114); a silent device never changes the status (OQ-31 answered, TRD 24 D-115; if that ever changes, two consecutive silent days are needed).
- Show a replacement only when it happened within the last 30 days (TRD 11 §5 note); the retired device is not described further here (the Study team "Show all devices" table lists it, FEAT-072).
- The file name keeps the v0.1 title (feature IDs and file names are never renamed, TRD 25 §4.2).
