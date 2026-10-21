# FEAT-049 Device assignment resolution and day ledger stage

| Field | Value |
|---|---|
| Epic | Data Processing |
| Build phase | Phase 6 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-041, FEAT-043 |
| Status | Not Started |

## Purpose

Record, for every resident and every facility-local day from enrolment to the as-of date, whether a check-in arrived (`checked_in`), the resident was missed (`missing_resident`), or the whole shared device was silent (`missing_device_gap`, e.g. D02 on Oct 12 for R02 and R03). This day ledger is the only place missing days exist: they are never backfilled, imputed or carried forward. To classify shared-device gaps the stage resolves which device each resident used on each day from the device assignment table.

## Business Context

- BR-06 (missed check-ins visible, distinguished by cause, never filled in): ledger statuses and reasons.
- BR-08 (device moves): assignments with inclusive date ranges define the device per day.
- BR-15: 300 ledger rows for SRC-05 — 281 checked_in, 17 missing_resident, 2 missing_device_gap (R02 and R03 on 2026-10-12).
- FRs covered (BACKLOG.md): FR-120, FR-121, FR-122, FR-123, FR-124, FR-125.

## Referenced TRDs

- TRD 10 ING-044..ING-047 (assignment resolution, shared rule, epochs use the record's device), ING-048..ING-052 (ledger range, checked-in rule, device gap vs resident miss, never backfilled, stored device), §4.9 test roster, §4.10 pseudocode and worked check.
- TRD 06 DB-023 (one row per resident per day; never later days; never filled).
- TRD 07 §4.2 (`build_ledger` signature), §4.3 (`LedgerDay`), §4.4 (`ResidentInfo`, `DeviceAssignment`), ANL-016 (ledger reads all residents sharing a device), ANL-052 (`no_device_assignment`, `device_assignment_mismatch` warnings).
- TRD 05 API-055 (assignment mismatch warning on the run).
- TRD 13 Table 4.3-A DL-01..DL-09; TRD 14 VC-G09, VC-R02, VC-R03, VC-R08.
- TRD 25 AGT-046; TRD 24 D-16, OQ-15.

## Scope

- Assignment resolution helpers in `analytics/day_ledger.py`: device of a resident on a local date (inclusive ranges, later `valid_from` wins), residents sharing a device on a date (≥ `shared_device_min_residents`, enrolled and not withdrawn before that date).
- `analytics/day_ledger.py::build_ledger(rows, residents, assignments, config, as_of) -> list[LedgerDay]`.
- The facts for the `no_device_assignment` and `device_assignment_mismatch` run warnings (emitted by `run_pipeline`, FEAT-052).
- Unit tests `tests/unit/analytics/test_day_ledger.py`.

## Out of Scope

- Device-panel read values (silent days, device-gap days, in-use dates) derived on read (FEAT-014, FEAT-029).
- `device_silent` data alerts (FEAT-050).
- Persisting `day_ledger` (FEAT-053) and the nightly trigger that extends the ledger daily (FEAT-054).
- Store-and-forward after outages (OQ-15): lost records stay missing days.

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-049-FR-01 | A resident's device on local date d shall be the device of the assignment whose inclusive range covers d (null `valid_to` = open); if two cover d, the one with the later `valid_from` wins; if none covers d, the device is unknown (None). | ING-044, ING-045 |
| FEAT-049-FR-02 | A device shall be shared on d when at least `shared_device_min_residents` (2) distinct residents enrolled on d (`enrolled_on` ≤ d and not withdrawn before d) have an assignment to it covering d. | ING-046 |
| FEAT-049-FR-03 | Epochs shall keep using each record's own `device_id`; assignments are used only for the ledger, the shared/was labels and the `device_assignment_mismatch` warning. | ING-047 |
| FEAT-049-FR-04 | The ledger shall contain one `LedgerDay` per resident per facility-local day from `enrolled_on` through the local date of `as_of`, or through `withdrawn_on` (inclusive) when earlier, and none for other days. | ING-048, DB-023; FR-120 |
| FEAT-049-FR-05 | A day with ≥ 1 non-duplicate record of the resident with `timestamp_utc` ≤ as_of (any status: usable, set aside, quarantined, including late arrivals) shall be `checked_in` with reason "" and the device of the earliest such record; duplicates alone do not count. | ING-049, ING-052; FR-121 |
| FEAT-049-FR-06 | A day without such a record shall be `missing_device_gap` with reason "all residents on shared device <device_code> have no record" when the resident's device that day is shared and none of the sharing residents has a non-duplicate record of any status that day; otherwise `missing_resident` with reason "no record received"; missing rows store the resident's assigned device (None if unknown). | ING-050, ING-052; FR-122, FR-123 |
| FEAT-049-FR-07 | Missing days shall never be backfilled, carried forward or imputed and create no session, score or tally update; the ledger is recomputed on every run, so a day becomes `checked_in` only when a real record for that day arrives. | ING-051, AGT-046, D-16; FR-124 |
| FEAT-049-FR-08 | The ledger shall extend to the as-of local date even when no record arrived (a later as-of adds days). | ING-048; FR-125 |
| FEAT-049-FR-09 | Local dates shall come from the FEAT-043 zoneinfo conversion (a record at 2026-10-02 04:30:00 UTC counts for 2026-10-01). | ING-027; DL-05 |
| FEAT-049-FR-10 | The stage shall supply the facts for warnings `no_device_assignment` (a missing day of a resident without a covering assignment; one per resident per run) and `device_assignment_mismatch` (a record whose device is not the resident's assigned device on its local date, with resident, session and device in the detail). | ANL-052, API-055 |

## Inputs

- `Sequence[EpochedRecord]` (all residents that share a device with residents in scope; statuses and local dates), `Sequence[ResidentInfo]`, `Sequence[DeviceAssignment]` (all facility assignments), `PipelineConfig` (`shared_device_min_residents`, `facility_tz`), `as_of`.

## Outputs

- `list[LedgerDay]` sorted by (resident_code, local_date); warning facts.

## Data Flow

1. `run_pipeline` step 13 (FEAT-052): `build_ledger(epoched, residents, assignments, config, as_of)`.
2. For each resident (sorted by code) and day in range: look for non-duplicate records that day; else resolve the device and its sharers on that day and check whether any sharer has a record.
3. Ledger rows feed data alerts (FEAT-050), aggregates (FEAT-051) and, via the runner, the `day_ledger` table.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-041, FEAT-043

- FEAT-041 (Duplicate detection and quality gate): duplicate vs non-duplicate statuses (duplicates never count).
- FEAT-043 (Local time derivation): local dates of records and of the as-of.

Features that build directly on this one (BACKLOG.md §4): FEAT-050, FEAT-052.

## Database Impact

None directly. The runner replaces each resident's `day_ledger` rows (`resident_id`, `local_date`, `status`, `device_id`, `reason`) (FEAT-053); TRD 20 `day_ledger_reason_ck` and `day_ledger_resident_date_uq` enforce the reasons and one row per day. Assignments are read from `device_assignments` by the runner and passed in.

## API Impact

None directly; ledger rows drive `missed` counts, `device_silent` events and device days (FEAT-027, FEAT-028, FEAT-029).

## Frontend Impact

None.

## Analytics Impact

- Algorithms: inclusive-range assignment resolution; per-day classification over all residents of a shared device.
- Stage 10 of ANL-006 (`day_ledger`, LOG-063).

## Security Requirements

None specific (pure function).

## Error Handling

- Residents with no records produce a ledger of missing days (no error, ANL-019).
- Days before `enrolled_on` or after the as-of / `withdrawn_on` produce no rows (DL-08).

## Logging Requirements

None in `analytics/` (LOG-006).

## Testing Requirements

- Unit (`tests/unit/analytics/test_day_ledger.py`, marker `unit`): DL-01..DL-09; later `valid_from` wins on overlap; withdrawn resident's last row is `withdrawn_on`; set-aside record on the other sharer's side prevents a device gap (R02 day 10 case); assignment resolution helpers; warning facts.
- Validation (FEAT-059): VC-G09 (300 rows: 281, 17, 2; no ledger row carries feature values), VC-R02 (days 4, 9, 10, 17, 23 missing_resident; day 12 device gap), VC-R03 (day 12 device gap), VC-R08 (12 missing days).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-049-AC-01 | A day with a record is `checked_in`; with no record on an own device `missing_resident` with reason "no record received". | DL-01, DL-02 |
| FEAT-049-AC-02 | Shared device D02 (R02, R03) with no record from either on a day gives both `missing_device_gap` with reason "all residents on shared device D02 have no record"; if the other resident has a record (any status), the missing resident is `missing_resident`. | DL-03, DL-04, DL-07, ING-050 |
| FEAT-049-AC-03 | A record at 2026-10-02 04:30:00 UTC counts for local date 2026-10-01; a day with only a duplicate arrival is not checked in. | DL-05, DL-06 |
| FEAT-049-AC-04 | No rows exist before `enrolled_on` or after the as-of local date; a missing day never gains values when a record arrives for another day. | DL-08, DL-09 |
| FEAT-049-AC-05 | On SRC-05 at as-of 2026-10-30 15:00 America/Chicago the ledger has 300 rows: 281 `checked_in`, 17 `missing_resident`, 2 `missing_device_gap` (R02 and R03 on 2026-10-12); R02 2026-10-10 is `missing_resident` (R03's set-aside record counts). | VC-G09, TRD 10 §4.10 worked check |
| FEAT-049-AC-06 | R07's assignments D07 (2026-10-01..2026-10-12) and D07B (from 2026-10-13) resolve to D07 on 2026-10-12 and D07B on 2026-10-13, and R07 has no missing day. Verified by: Validation (VC-R03, VC-R08). | ING-044, ING-045 |

## Definition of Done

- All FEAT-049 acceptance criteria pass.
- `build_ledger` and the resolution helpers implemented; DL-01..DL-09 pass (TST-020); test file exists (TST-011).
- VC-G09 and VC-R02/VC-R03/VC-R08 ledger values pass in the validation suite.

## Implementation Notes

- A resident-scoped run must receive the records of all residents sharing that resident's devices in the window (ANL-016, TRD 10 §8); the runner loads them, this stage assumes it.
- Counting only usable records as "a record" would wrongly create a device gap for R02 on 2026-10-10 (TRD 10 §4.10); count every non-duplicate status.
- Iterate days with `date` arithmetic in the facility zone; the as-of local date comes from the same zoneinfo helper as FEAT-043.
- OQ-15: records lost during an outage are missing days; nothing here infers them.
