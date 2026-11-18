# Device assignment resolution and day ledger stage

## Feature Description

Stage 10 of the analytics engine (`analytics/day_ledger.py::build_ledger`, FEAT-049) writes one `LedgerDay` per resident per facility-local day from `enrolled_on` to the as-of local date (or `withdrawn_on`). A day is `checked_in` when at least one non-duplicate record of any status exists; otherwise it is `missing_device_gap` (the resident's device is shared that day and no sharer has a record) or `missing_resident` ("no record received"). Missing days are never backfilled, imputed or carried forward. The stage resolves each resident's device per day from `device_assignments` (inclusive ranges, later `valid_from` wins) and supplies the facts for the `no_device_assignment` and `device_assignment_mismatch` run warnings. The runner (FEAT-053) persists the rows in `day_ledger`.

## Preconditions

- Local development stack (`README.md` quick start), repository root as working directory, Python dependencies from `backend/requirements-dev.txt` installed.
- For database cases: an empty migrated test database seeded with `python -m backend.cli seed test_v0_1` (DS-07: roster R01–R10, SRC-05 ingested, `manual` run at as-of 2026-10-30T20:00:00Z, i.e. 2026-10-30 15:00 America/Chicago). `psql` connected read-only.
- Test roster assignments (TRD 10 §4.9): R01 D01, R02 D02, R03 D02 (shared), R04 D04, R05 D05, R06 D06, R07 D07 2026-10-01..2026-10-12 and D07B from 2026-10-13, R08 D08, R09 D09, R10 D10; all residents enrolled 2026-10-01.
- REPL helper for the engine cases (paste into `python` started at the repository root):

```python
from datetime import date, datetime
from zoneinfo import ZoneInfo
from analytics.config import TEST_V0_1, DeviceAssignment, ResidentInfo
from analytics.pipeline import run_pipeline
from analytics.day_ledger import device_on, sharers
from tests.unit.analytics.factory import rec
from tests.unit.analytics.src05 import result, ASSIGNMENTS
CT = ZoneInfo("America/Chicago")
def run(records, residents, assignments, as_of):
    return run_pipeline(records, residents, assignments, TEST_V0_1, as_of)
```

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-049-01 | SRC-05 ledger has 300 rows: 281 checked_in, 17 missing_resident, 2 missing_device_gap | High | Analytics |
| TC-049-02 | Persisted `day_ledger` after the DS-07 seed matches the engine counts and one row per resident per day | High | Database |
| TC-049-03 | Day with a record is checked_in; own-device day without a record is missing_resident "no record received" | High | Positive |
| TC-049-04 | Shared device D02 silent on 2026-10-12 gives both R02 and R03 missing_device_gap | High | Positive |
| TC-049-05 | Other sharer's set-aside record prevents a device gap (R02 on 2026-10-10 is missing_resident) | High | Positive |
| TC-049-06 | Record at 2026-10-02 04:30:00 UTC counts for local date 2026-10-01 | High | Analytics |
| TC-049-07 | A day with only a duplicate arrival is not checked in | High | Negative |
| TC-049-08 | No rows before enrolled_on or after the as-of local date; a later as-of adds days | High | Negative |
| TC-049-09 | Withdrawn resident's last ledger row is `withdrawn_on` | Medium | Positive |
| TC-049-10 | Missing days are never backfilled and carry no feature values | High | Negative |
| TC-049-11 | R07 resolves to D07 on 2026-10-12 and D07B on 2026-10-13 and has no missing day | High | Positive |
| TC-049-12 | Overlapping assignments: later `valid_from` wins; no covering assignment gives no device | Medium | Analytics |
| TC-049-13 | `device_assignment_mismatch` and `no_device_assignment` warning facts | Medium | Negative |
| TC-049-14 | Unit test file for the day ledger passes | Medium | Positive |

### TC-049-01 SRC-05 ledger has 300 rows: 281 checked_in, 17 missing_resident, 2 missing_device_gap

| Step | Action | Expected Result |
|---|---|---|
| 1 | In the REPL helper run `L = result().ledger; len(L)` | `300` |
| 2 | Run `from collections import Counter; Counter(d.status for d in L)` | `checked_in` 281, `missing_resident` 17, `missing_device_gap` 2 |
| 3 | Run `sorted((d.resident_code, str(d.local_date)) for d in L if d.status == "missing_device_gap")` | `[('R02', '2026-10-12'), ('R03', '2026-10-12')]` |
| 4 | Run `[(d.resident_code, d.local_date) for d in L] == sorted((d.resident_code, d.local_date) for d in L)` | `True` (sorted by resident_code, local_date) |

### TC-049-02 Persisted `day_ledger` after the DS-07 seed matches the engine counts and one row per resident per day

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT status, count(*) FROM day_ledger GROUP BY status ORDER BY status;` | `checked_in` 281, `missing_device_gap` 2, `missing_resident` 17 |
| 2 | `SELECT r.resident_code, count(*), min(l.local_date), max(l.local_date) FROM day_ledger l JOIN residents r ON r.id = l.resident_id GROUP BY 1 ORDER BY 1;` | 10 rows R01–R10, each count 30, min 2026-10-01, max 2026-10-30 |
| 3 | `SELECT resident_id, local_date, count(*) FROM day_ledger GROUP BY 1,2 HAVING count(*) > 1;` | 0 rows (constraint `day_ledger_resident_date_uq`) |

### TC-049-03 Day with a record is checked_in; own-device day without a record is missing_resident "no record received"

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT l.local_date, l.status, d.device_code, l.reason FROM day_ledger l JOIN residents r ON r.id = l.resident_id LEFT JOIN devices d ON d.id = l.device_id WHERE r.resident_code = 'R01' ORDER BY 1;` | 30 rows, all `checked_in`, device `D01`, reason `""` (empty) |
| 2 | Same query for `R08` filtered `AND l.status <> 'checked_in'` | 12 rows, all `missing_resident`, device `D08`, reason `no record received` |
| 3 | Same query for `R02` filtered `AND l.status = 'missing_resident'` | Exactly 2026-10-04, 2026-10-09, 2026-10-10, 2026-10-17, 2026-10-23, each reason `no record received`, device `D02` |

### TC-049-04 Shared device D02 silent on 2026-10-12 gives both R02 and R03 missing_device_gap

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT r.resident_code, l.status, d.device_code, l.reason FROM day_ledger l JOIN residents r ON r.id = l.resident_id LEFT JOIN devices d ON d.id = l.device_id WHERE l.local_date = '2026-10-12' AND r.resident_code IN ('R02','R03') ORDER BY 1;` | R02 and R03 both `missing_device_gap`, device `D02`, reason `all residents on shared device D02 have no record` |
| 2 | In the REPL run `from tests.unit.analytics.src05 import RESIDENTS; sharers("D02", date(2026,10,12), ASSIGNMENTS, {r.resident_code: r for r in RESIDENTS})` | `['R02', 'R03']` (2 ≥ `shared_device_min_residents` 2) |
| 3 | `SELECT count(*) FROM day_ledger WHERE status = 'missing_device_gap' AND local_date <> '2026-10-12';` | `0` |

### TC-049-05 Other sharer's set-aside record prevents a device gap (R02 on 2026-10-10 is missing_resident)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT r.resident_code, l.status, l.reason FROM day_ledger l JOIN residents r ON r.id = l.resident_id WHERE l.local_date = '2026-10-10' AND r.resident_code IN ('R02','R03') ORDER BY 1;` | R02 `missing_resident` "no record received"; R03 `checked_in` |
| 2 | `SELECT status, reasons FROM processed_sessions WHERE session_id = 'R03-20261010-01';` | `set_aside`, reasons `{"speech too short"}` (a set-aside record still counts as a record) |
| 3 | Synthetic: `res=[ResidentInfo("R01",date(2026,10,1)),ResidentInfo("R02",date(2026,10,1))]; a=[DeviceAssignment(c,"D1",date(2026,10,1)) for c in ("R01","R02")]; L=run([rec(1,"2026-10-01 19:00:00",resident="R01",device="D1",flag="poor")],res,a,datetime(2026,10,1,20,tzinfo=CT)).ledger; [(d.resident_code,d.status) for d in L]` | `[('R01', 'checked_in'), ('R02', 'missing_resident')]` |

### TC-049-06 Record at 2026-10-02 04:30:00 UTC counts for local date 2026-10-01

| Step | Action | Expected Result |
|---|---|---|
| 1 | `res=[ResidentInfo("R01",date(2026,10,1))]; a=[DeviceAssignment("R01","D01",date(2026,10,1))]; L=run([rec(1,"2026-10-02 04:30:00")],res,a,datetime(2026,10,2,12,tzinfo=CT)).ledger` | No exception |
| 2 | `[(str(d.local_date), d.status) for d in L]` | `[('2026-10-01', 'checked_in'), ('2026-10-02', 'missing_resident')]` (04:30 UTC = 23:30 CDT on Oct 1) |

### TC-049-07 A day with only a duplicate arrival is not checked in

| Step | Action | Expected Result |
|---|---|---|
| 1 | `res=[ResidentInfo("R01",date(2026,10,1))]; a=[DeviceAssignment("R01","D01",date(2026,10,1))]; recs=[rec(1,"2026-10-01 15:00:00",session="R01-20261001-01"), rec(2,"2026-10-02 15:00:00",session="R01-20261001-01")]` | Two records share session_id `R01-20261001-01`; arrival 2 is the duplicate copy |
| 2 | `r=run(recs,res,a,datetime(2026,10,2,20,tzinfo=CT)); [(str(d.local_date), d.status) for d in r.ledger]` | `[('2026-10-01', 'checked_in'), ('2026-10-02', 'missing_resident')]` |
| 3 | `[(s.record.arrival_seq, s.status) for s in r.sessions]` | `[(1, 'usable'), (2, 'duplicate')]` |

### TC-049-08 No rows before enrolled_on or after the as-of local date; a later as-of adds days

| Step | Action | Expected Result |
|---|---|---|
| 1 | `res=[ResidentInfo("R01",date(2026,10,3))]; a=[DeviceAssignment("R01","D01",date(2026,10,1))]; L=run([rec(1,"2026-10-02 15:00:00")],res,a,datetime(2026,10,5,9,tzinfo=CT)).ledger; [str(d.local_date) for d in L]` | `['2026-10-03', '2026-10-04', '2026-10-05']` (no row for Oct 1–2, none after Oct 5) |
| 2 | Re-run with `as_of=datetime(2026,10,7,9,tzinfo=CT)` | 5 rows, last `2026-10-07`, Oct 6–7 `missing_resident` although no record arrived |
| 3 | `SELECT count(*) FROM day_ledger WHERE local_date < '2026-10-01' OR local_date > '2026-10-30';` (DS-07) | `0` |

### TC-049-09 Withdrawn resident's last ledger row is `withdrawn_on`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `res=[ResidentInfo("R01",date(2026,10,1),withdrawn_on=date(2026,10,2))]; a=[DeviceAssignment("R01","D01",date(2026,10,1))]; L=run([],res,a,datetime(2026,10,5,9,tzinfo=CT)).ledger` | No exception (resident with no records, ANL-019) |
| 2 | `[(str(d.local_date), d.status, d.reason) for d in L]` | `[('2026-10-01','missing_resident','no record received'), ('2026-10-02','missing_resident','no record received')]`; no row for Oct 3–5 |

### TC-049-10 Missing days are never backfilled and carry no feature values

| Step | Action | Expected Result |
|---|---|---|
| 1 | `res=[ResidentInfo("R01",date(2026,10,1))]; a=[DeviceAssignment("R01","D01",date(2026,10,1))]; L1=run([rec(1,"2026-10-01 15:00:00")],res,a,datetime(2026,10,3,20,tzinfo=CT)).ledger` | Oct 2 and Oct 3 `missing_resident` |
| 2 | `L2=run([rec(1,"2026-10-01 15:00:00"), rec(2,"2026-10-03 15:00:00")],res,a,datetime(2026,10,3,20,tzinfo=CT)).ledger; [(str(d.local_date), d.status, d.reason) for d in L2]` | Oct 2 still `missing_resident` "no record received"; only Oct 3 changes to `checked_in` |
| 3 | `\d day_ledger` in psql | Columns limited to `id`, `resident_id`, `local_date`, `status`, `device_id`, `reason`, `pipeline_run_id`, `created_at`; no feature column |
| 4 | `SELECT count(*) FROM scores s JOIN day_ledger l ON l.resident_id = s.resident_id AND l.local_date = s.local_date WHERE l.status <> 'checked_in';` | `0` (no score exists for a missing day) |

### TC-049-11 R07 resolves to D07 on 2026-10-12 and D07B on 2026-10-13 and has no missing day

| Step | Action | Expected Result |
|---|---|---|
| 1 | REPL: `device_on("R07", date(2026,10,12), ASSIGNMENTS), device_on("R07", date(2026,10,13), ASSIGNMENTS)` | `('D07', 'D07B')` |
| 2 | `SELECT l.local_date, l.status, d.device_code FROM day_ledger l JOIN residents r ON r.id=l.resident_id JOIN devices d ON d.id=l.device_id WHERE r.resident_code='R07' AND l.local_date IN ('2026-10-12','2026-10-13') ORDER BY 1;` | 2026-10-12 `checked_in` D07; 2026-10-13 `checked_in` D07B |
| 3 | `SELECT count(*) FROM day_ledger l JOIN residents r ON r.id=l.resident_id WHERE r.resident_code='R07' AND l.status <> 'checked_in';` | `0` |

### TC-049-12 Overlapping assignments: later `valid_from` wins; no covering assignment gives no device

| Step | Action | Expected Result |
|---|---|---|
| 1 | `a=[DeviceAssignment("R01","D1",date(2026,10,1)), DeviceAssignment("R01","D2",date(2026,10,5),date(2026,10,6))]` | Two assignments overlap on Oct 5–6 |
| 2 | `device_on("R01",date(2026,10,4),a), device_on("R01",date(2026,10,5),a), device_on("R01",date(2026,10,6),a), device_on("R01",date(2026,10,7),a)` | `('D1', 'D2', 'D2', 'D1')` (inclusive `valid_to`, later `valid_from` wins) |
| 3 | `device_on("R01", date(2026,9,30), a)` | `None` |

### TC-049-13 `device_assignment_mismatch` and `no_device_assignment` warning facts

| Step | Action | Expected Result |
|---|---|---|
| 1 | `res=[ResidentInfo("R01",date(2026,10,1))]; a=[DeviceAssignment("R01","D01",date(2026,10,1))]; r=run([rec(1,"2026-10-01 15:00:00",device="D99")],res,a,datetime(2026,10,1,20,tzinfo=CT))` | No exception |
| 2 | `[(w.code, w.resident_code, w.session_id, w.detail) for w in r.warnings]` | Contains `('device_assignment_mismatch', 'R01', 'R01-20261001-01', 'record device D99, assigned D01')` |
| 3 | `[(str(d.local_date), d.status, d.device_code) for d in r.ledger]` | `[('2026-10-01', 'checked_in', 'D99')]` (checked-in row stores the record's own device) |
| 4 | `r2=run([],res,[DeviceAssignment("R01","D01",date(2026,10,3))],datetime(2026,10,2,20,tzinfo=CT)); [w.code for w in r2.warnings]` | Exactly one `no_device_assignment` for R01 (one per resident per run although 2 days are missing); ledger rows have `device_code` `None` |

### TC-049-14 Unit test file for the day ledger passes

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/unit/analytics/test_day_ledger.py -q` | Exit code 0; `test_device_resolution`, `test_checked_in_gap_and_missed`, `test_src05_ledger` pass |

## API Validation

Not applicable directly: the stage exposes no endpoint (FEAT-049 API Impact). Ledger values reach the API through `GET /api/v1/residents` (`last_30_days.missed`), `GET /api/v1/devices` and `GET /api/v1/analytics`, which are validated in TC-060 and TC-051. One consistency check:

| Step | API Action | Expected Result |
|---|---|---|
| 1 | Log in as researcher (`POST /api/v1/auth/login`, password from `SEED_RESEARCHER_PASSWORD`), `GET /api/v1/analytics` | 200; `status_totals.missing_resident` 17 and `status_totals.missing_device_gap` 2, equal to TC-049-02 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT count(*) FROM day_ledger;` | `300` |
| 2 | `SELECT status, reason, count(*) FROM day_ledger GROUP BY 1,2 ORDER BY 1;` | `checked_in` "" 281; `missing_device_gap` "all residents on shared device D02 have no record" 2; `missing_resident` "no record received" 17 |
| 3 | `SELECT count(*) FROM day_ledger WHERE status <> 'checked_in' AND device_id IS NULL;` | `0` (every test resident has a covering assignment) |
| 4 | `SELECT count(DISTINCT pipeline_run_id) FROM day_ledger;` | `1`, equal to the id of the latest succeeded run in `pipeline_runs` |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Duplicate-only day (TC-049-07) | Day is `missing_resident`, not `checked_in` |
| 2 | As-of earlier than enrolment: `run([], [ResidentInfo("R01",date(2026,10,3))], [DeviceAssignment("R01","D01",date(2026,10,1))], datetime(2026,10,2,9,tzinfo=CT)).ledger` | Empty result `()` (no rows, no exception) |
| 3 | Shared device but the other resident is not yet enrolled on the day: `res=[ResidentInfo("R01",date(2026,10,1)), ResidentInfo("R02",date(2026,10,5))]`, both assigned D1 from Oct 1, no records, as-of Oct 2 | R01 Oct 1–2 `missing_resident` (only 1 enrolled sharer, below 2), no `missing_device_gap` |
| 4 | Record after the as-of: `run([rec(1,"2026-10-03 15:00:00")], ...)` with as-of 2026-10-02 20:00 CT | Oct 3 has no row; record excluded with `after_as_of` warning |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-049-AC-01 | Day with a record `checked_in`; own-device day without a record `missing_resident` "no record received" | TC-049-03 |
| FEAT-049-AC-02 | D02 with no record from R02 or R03 gives both `missing_device_gap` with the exact reason; a sharer's record of any status makes the missing resident `missing_resident` | TC-049-04, TC-049-05 |
| FEAT-049-AC-03 | 2026-10-02 04:30:00 UTC counts for 2026-10-01; duplicate-only day not checked in | TC-049-06, TC-049-07 |
| FEAT-049-AC-04 | No rows before `enrolled_on` or after the as-of local date; a missing day never gains values | TC-049-08, TC-049-10 |
| FEAT-049-AC-05 | SRC-05: 300 rows, 281/17/2, gaps R02 and R03 on 2026-10-12, R02 2026-10-10 `missing_resident` | TC-049-01, TC-049-02, TC-049-05 |
| FEAT-049-AC-06 | R07 resolves to D07 on 2026-10-12 and D07B on 2026-10-13 and has no missing day | TC-049-11 |

## Test Data Requirements

- SRC-05 `tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv` (283 arrivals) and the test roster `database/seeds/test_v0_1/` (R01–R10, devices D01–D10, D07B).
- Synthetic REPL records built with `tests.unit.analytics.factory.rec` (residents R01/R02, devices D01, D1, D2, D99 are synthetic codes).
- Environment: `DATABASE_URL`, `DATABASE_MIGRATION_URL`, `PIPELINE_PROFILE=test_v0_1`, `FACILITY_TZ=America/Chicago`, `SEED_*` variables from the environment file.
- No audio, names or rooms.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-049-FR-01 / ING-044, ING-045 | FEAT-049 | TC-049-11, TC-049-12 |
| FEAT-049-FR-02 / ING-046 | FEAT-049 | TC-049-04, Negative step 3 |
| FEAT-049-FR-03 / ING-047 | FEAT-049 | TC-049-13 |
| FEAT-049-FR-04 / ING-048, DB-023, FR-120 | FEAT-049 | TC-049-02, TC-049-08, TC-049-09 |
| FEAT-049-FR-05 / ING-049, ING-052, FR-121 | FEAT-049 | TC-049-03, TC-049-05, TC-049-07 |
| FEAT-049-FR-06 / ING-050, ING-052, FR-122, FR-123 | FEAT-049 | TC-049-03, TC-049-04, TC-049-05 |
| FEAT-049-FR-07 / ING-051, AGT-046, D-16, FR-124 | FEAT-049 | TC-049-10 |
| FEAT-049-FR-08 / FR-125 | FEAT-049 | TC-049-08 |
| FEAT-049-FR-09 / ING-027 | FEAT-049 | TC-049-06 |
| FEAT-049-FR-10 / ANL-052, API-055 | FEAT-049 | TC-049-13 |
| DL-01, DL-02 | FEAT-049 | TC-049-03 |
| DL-03, DL-04, DL-07 | FEAT-049 | TC-049-04, TC-049-05 |
| DL-05, DL-06 | FEAT-049 | TC-049-06, TC-049-07 |
| DL-08, DL-09 | FEAT-049 | TC-049-08, TC-049-10 |
| TST-020, TST-011 | FEAT-049 | TC-049-14 |
| VC-G09 | FEAT-049 | TC-049-01, TC-049-02, TC-049-10 |
| VC-R02, VC-R03 | FEAT-049 | TC-049-03, TC-049-04 |
| VC-R08 | FEAT-049 | TC-049-03 |
