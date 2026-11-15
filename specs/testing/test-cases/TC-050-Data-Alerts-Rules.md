# Data alerts rules (stage 11)

## Feature Description

Stage 11 of the analytics engine (`analytics/data_alerts.py::generate_data_alerts`, FEAT-050) recomputes the rule-based data-quality alerts on every run over the 30 facility-local days ending on the as-of local date: `baseline_stalled`, `possible_other_speaker`, `high_set_aside` and `device_silent`, with exact title and detail strings (v0.1 titles, v0.2 details, TRD 24 D-114), suppression of `high_set_aside` by `baseline_stalled`, one alert per subject per kind and a fixed order (kind, then code). Thresholds come from `config.operational` (`data_alert_baseline_stalled_enabled` true, `data_alert_set_aside_fraction` 0.20, `data_alert_device_silent_days` 2) and the fixed minimum of 10 received records. Data alerts never create an alarm or change a tally. On SRC-05 exactly four alerts result: R08 baseline_stalled, R05 possible_other_speaker, R03 high_set_aside, D02 device_silent.

## Preconditions

- Local development stack, repository root as working directory, `backend/requirements-dev.txt` installed.
- For database and API cases: database seeded with `python -m backend.cli seed test_v0_1` (DS-07, as-of 2026-10-30T20:00:00Z); backend running locally; users from the seed with the `SEED_*` passwords.
- REPL helper (paste into `python` at the repository root):

```python
from dataclasses import replace
from datetime import datetime
from zoneinfo import ZoneInfo
from analytics.config import TEST_V0_1
from analytics.pipeline import run_pipeline
from analytics.data_alerts import _flagged, join_and
from tests.unit.analytics.src05 import records, RESIDENTS, ASSIGNMENTS
CT = ZoneInfo("America/Chicago")
AS_OF = datetime(2026, 10, 30, 15, tzinfo=CT)
def run(recs=None, as_of=AS_OF, cfg=TEST_V0_1):
    return run_pipeline(recs if recs is not None else records(), RESIDENTS, ASSIGNMENTS, cfg, as_of)
def alerts(**kw):
    return [(a.kind, a.resident_code or a.device_code, a.title, a.detail) for a in run(**kw).data_alerts]
```

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-050-01 | SRC-05 produces exactly the four reference alerts in order | High | Analytics |
| TC-050-02 | R08 baseline_stalled title and detail | High | Positive |
| TC-050-03 | baseline_stalled boundary: 15 inclusive days gives none, 16 gives one | High | Analytics |
| TC-050-04 | possible_other_speaker plural and singular details | High | Positive |
| TC-050-05 | high_set_aside 7 of 29 with reason kinds in fixed order | High | Positive |
| TC-050-06 | high_set_aside not raised below 10 received (2 of 9) | High | Negative |
| TC-050-07 | Suppression: R08 gets baseline_stalled only, not high_set_aside | High | Negative |
| TC-050-08 | device_silent for shared device D02 on Oct 12 | High | Positive |
| TC-050-09 | Single-resident device: isolated silent days give none, 2 consecutive give one | High | Analytics |
| TC-050-10 | Device with no assigned resident (D07 after 2026-10-12) gives no alert | Medium | Negative |
| TC-050-11 | Threshold change via config changes the result without changing `config_hash()` | High | Analytics |
| TC-050-12 | Data alerts never touch alarms, tallies or alarm counts | High | Negative |
| TC-050-13 | Persisted `data_alerts` and `GET /api/v1/data-alerts` show the four rows after the seed | High | API |
| TC-050-14 | Unit test file for data alerts passes | Medium | Positive |

### TC-050-01 SRC-05 produces exactly the four reference alerts in order

| Step | Action | Expected Result |
|---|---|---|
| 1 | REPL: `for a in alerts(): print(a)` | Exactly 4 lines, in this order |
| 2 | Check line 1 | `('baseline_stalled', 'R08', 'R08 · baseline stuck at 13 of 16', 'baseline stuck at 13 of 16. 12 missed and 5 set aside in 30 days.')` |
| 3 | Check line 2 | `('possible_other_speaker', 'R05', 'R05 · possible other speaker', '2 check-ins held back as possible other voice (Oct 8, Oct 22).')` |
| 4 | Check line 3 | `('high_set_aside', 'R03', 'R03 · many check-ins set aside', '7 of 29 received check-ins set aside (noise, quality flag, too short).')` |
| 5 | Check line 4 | `('device_silent', 'D02', 'D02 · device silent all day', 'silent all day Oct 12. Affected R02 and R03.')` |
| 6 | `[(a.resident_code, a.device_code) for a in run().data_alerts]` | `[('R08', None), ('R05', None), ('R03', None), (None, 'D02')]` (never both codes) |

### TC-050-02 R08 baseline_stalled title and detail

| Step | Action | Expected Result |
|---|---|---|
| 1 | `e=[e for e in run().epochs if e.resident_code=="R08"]; [(e.epoch_number, e.baseline_formed, e.usable_count) for e in e]` | `[(1, False, 13)]` (forming, 13 usable) |
| 2 | Inclusive days: as-of local date 2026-10-30 − epoch start 2026-10-01 + 1 | 30 ≥ `baseline_n` 16 |
| 3 | `[a for a in alerts() if a[0]=="baseline_stalled"]` | One alert for R08 only, detail "baseline stuck at 13 of 16. 12 missed and 5 set aside in 30 days." (12 = missing_resident + missing_device_gap days of R08) |

### TC-050-03 baseline_stalled boundary: 15 inclusive days gives none, 16 gives one

| Step | Action | Expected Result |
|---|---|---|
| 1 | `[a for a in alerts(as_of=datetime(2026,10,15,15,tzinfo=CT)) if a[0]=="baseline_stalled"]` | `[]` (2026-10-15 − 2026-10-01 + 1 = 15 < 16) |
| 2 | `[a[1] for a in alerts(as_of=datetime(2026,10,16,15,tzinfo=CT)) if a[0]=="baseline_stalled"]` | `['R02', 'R03', 'R05', 'R08']` (16 ≥ 16 for every resident still forming) |
| 3 | In step 2 output check R08's title | `R08 · baseline stuck at 7 of 16` |

### TC-050-04 possible_other_speaker plural and singular details

| Step | Action | Expected Result |
|---|---|---|
| 1 | `[a for a in alerts() if a[0]=="possible_other_speaker"]` | One R05 alert, detail `2 check-ins held back as possible other voice (Oct 8, Oct 22).` (dates ascending, "Mon D" without leading zero) |
| 2 | `[a for a in alerts(recs=[r for r in records() if r.session_id!="R05-20261022-01"]) if a[0]=="possible_other_speaker"]` | One R05 alert, detail `1 check-in held back as possible other voice (Oct 8).` |
| 3 | `[a for a in alerts() if a[0]=="possible_other_speaker" and a[1]!="R05"]` | `[]` (no other resident has a quarantined record) |

### TC-050-05 high_set_aside 7 of 29 with reason kinds in fixed order

| Step | Action | Expected Result |
|---|---|---|
| 1 | `[a for a in alerts() if a[0]=="high_set_aside"]` | Exactly one alert: R03, title `R03 · many check-ins set aside`, detail `7 of 29 received check-ins set aside (noise, quality flag, too short).` |
| 2 | Verify ratio | 7 / 29 = 0.241 ≥ 0.20 and received 29 ≥ 10 (30 days − 1 device-gap day) |
| 3 | `[a.days for a in run().data_alerts if a.kind=="high_set_aside"]` | R03 set-aside dates 2026-10-03, 07, 10, 14, 18, 22, 26 |

### TC-050-06 high_set_aside not raised below 10 received (2 of 9)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `alerts(as_of=datetime(2026,10,9,23,tzinfo=CT))` | No `high_set_aside` row (R03 received 9, set aside 2 on Oct 3 and Oct 7; 2/9 = 0.22 but received < 10) |
| 2 | Same output | Only `('possible_other_speaker', 'R05', 'R05 · possible other speaker', '1 check-in held back as possible other voice (Oct 8).')` |

### TC-050-07 Suppression: R08 gets baseline_stalled only, not high_set_aside

| Step | Action | Expected Result |
|---|---|---|
| 1 | `[a[:2] for a in alerts() if a[1]=="R08"]` | `[('baseline_stalled', 'R08')]` only |
| 2 | Turn the stalled rule off: `cfg=replace(TEST_V0_1, operational=replace(TEST_V0_1.operational, data_alert_baseline_stalled_enabled=False)); [a for a in alerts(cfg=cfg) if a[1]=="R08"]` | `[('high_set_aside', 'R08', 'R08 · many check-ins set aside', '5 of 18 received check-ins set aside (noise, quality flag, too short).')]` (5/18 = 0.278 qualifies, proving step 1 is suppression) |

### TC-050-08 device_silent for shared device D02 on Oct 12

| Step | Action | Expected Result |
|---|---|---|
| 1 | `[(a.title, a.detail, a.days) for a in run().data_alerts if a.kind=="device_silent"]` | `[('D02 · device silent all day', 'silent all day Oct 12. Affected R02 and R03.', (datetime.date(2026, 10, 12),))]` |
| 2 | Verify D02 on Oct 9 and Oct 10 is not silent | Not flagged: R03 has records on those days (R02's missed days are `missing_resident`) |
| 3 | `join_and(["R01","R02","R03"])` | `'R01, R02 and R03'` (three-resident join rule) |

### TC-050-09 Single-resident device: isolated silent days give none, 2 consecutive give one

| Step | Action | Expected Result |
|---|---|---|
| 1 | `[a for a in alerts() if a[1]=="D08"]` | `[]` (R08's 12 missed days are never 2 consecutive) |
| 2 | `alerts(recs=[r for r in records() if r.session_id not in ("R01-20261005-01","R01-20261006-01")])` | Contains `('device_silent', 'D01', 'D01 · device silent on 2 days', 'silent on 2 days (Oct 5, Oct 6). Affected R01.')` placed before the D02 row |
| 3 | `from datetime import date; [d.day for d,_ in _flagged([(date(2026,10,n),["R08"]) for n in (2,4,5,9)], 2, 2)]` | `[4, 5]` (only the 2-day run is flagged) |

### TC-050-10 Device with no assigned resident (D07 after 2026-10-12) gives no alert

| Step | Action | Expected Result |
|---|---|---|
| 1 | `[a for a in alerts() if a[1] in ("D07","D07B")]` | `[]` (D07 has no assigned resident from 2026-10-13; R07 has no missing day) |
| 2 | `[a for a in alerts() if a[0]=="baseline_stalled" and a[1]=="R07"]` | `[]` (R07's current epoch 2 formed on 2026-10-28) |

### TC-050-11 Threshold change via config changes the result without changing `config_hash()`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `cfg=replace(TEST_V0_1, operational=replace(TEST_V0_1.operational, data_alert_set_aside_fraction=0.25))` | New config object |
| 2 | `[a[0] for a in alerts(cfg=cfg)]` | `['baseline_stalled', 'possible_other_speaker', 'device_silent']` (R03 0.241 < 0.25, no high_set_aside) |
| 3 | `cfg.config_hash() == TEST_V0_1.config_hash()` | `True` (operational keys are not hashed, D-56) |
| 4 | `grep -n -e "0\.20" -e "0\.2\b" analytics/data_alerts.py` | No match: the fraction is read from `config.operational`; only `MIN_RECEIVED = 10` is a module constant |

### TC-050-12 Data alerts never touch alarms, tallies or alarm counts

| Step | Action | Expected Result |
|---|---|---|
| 1 | `r=run(); [(a.resident_code, a.session_id) for a in r.alerts]` | Only R09 `R09-20261021-01` and R10 `R10-20261024-01`; no alert for R08, R05, R03 or D02 |
| 2 | `r2=run(cfg=replace(TEST_V0_1, operational=replace(TEST_V0_1.operational, data_alert_set_aside_fraction=0.99))); r2.scores == r.scores and r2.alerts == r.alerts and r2.epochs == r.epochs` | `True` (changing data-alert thresholds changes no score, tally, alarm state or alert) |
| 3 | `grep -n -e alert_reviews -e acknowledged -e snooze analytics/data_alerts.py` | No match (the stage has no access to alerts' human state) |
| 4 | API: `GET /api/v1/analytics` as researcher | `kpis.alarms_raised.count` 2 with `resident_codes` ["R09", "R10"]; the 4 data alerts are not counted |

### TC-050-13 Persisted `data_alerts` and `GET /api/v1/data-alerts` show the four rows after the seed

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/auth/login` as `clinician@example.com` (password from `SEED_CLINICIAN_PASSWORD`) | 200 with an access token |
| 2 | `GET /api/v1/data-alerts?status=open` with the Bearer token | 200; `total` 4; items in order R08 `baseline_stalled`, R05 `possible_other_speaker`, R03 `high_set_aside`, D02 `device_silent` with the titles and details of TC-050-01; `first_detected_at` and `last_detected_at` "2026-10-30T20:00:00Z"; `status` "open" |
| 3 | `SELECT kind, title, detail, status FROM data_alerts ORDER BY kind;` | 4 rows, values equal to step 2 |

### TC-050-14 Unit test file for data alerts passes

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/unit/analytics/test_data_alerts.py -q` | Exit code 0; `test_src05_exactly_four_alerts_in_order`, `test_single_resident_device_needs_a_run`, `test_wording_helpers` pass |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/data-alerts?status=open` (any role: admin, clinician, researcher) | 200 `DataAlertList`, `total` 4, ordered by kind enum then code (TRD 19 E-30) |
| 2 | Verify each item's fields | `id`, `kind`, `resident_code` or `device_code` (the other null), `title`, `detail`, `status`, `first_detected_at`, `last_detected_at`, `pipeline_run_id` present |
| 3 | `GET /api/v1/data-alerts?status=open&kind=device_silent` | 200, 1 item D02 |
| 4 | `GET /api/v1/data-alerts?status=bogus` | 422 `INVALID_QUERY_PARAMETER` |
| 5 | `GET /api/v1/data-alerts` without a token | 401 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT d.kind, r.resident_code, v.device_code, d.status FROM data_alerts d LEFT JOIN residents r ON r.id=d.resident_id LEFT JOIN devices v ON v.id=d.device_id ORDER BY d.kind;` | 4 rows: baseline_stalled R08, possible_other_speaker R05, high_set_aside R03, device_silent D02; all `open` |
| 2 | `SELECT count(*) FROM data_alerts WHERE resident_id IS NOT NULL AND device_id IS NOT NULL;` | `0` (`data_alerts_subject_ck`) |
| 3 | `SELECT days FROM data_alerts WHERE kind='device_silent';` | `{2026-10-12}` |
| 4 | `SELECT count(*) FROM alerts;` | `2` (data alerts create no alarm) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Received below 10 (TC-050-06) | No `high_set_aside` |
| 2 | Resident qualifying for both baseline_stalled and high_set_aside (TC-050-07) | Only `baseline_stalled` |
| 3 | Isolated silent days on a single-resident device (TC-050-09 step 1) | No `device_silent` |
| 4 | Device without an assigned resident (TC-050-10) | No alert |
| 5 | Empty input: `run(recs=[]).data_alerts` | No exception; only `device_silent` alerts (one per device, e.g. "D01 · device silent on 30 days", "D07 · device silent on 12 days", "D07B · device silent on 18 days"); no `baseline_stalled` (no epoch exists), no `possible_other_speaker`, no `high_set_aside` |
| 6 | `data_alert_baseline_stalled_enabled` false (TC-050-07 step 2) | No `baseline_stalled` row at all |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-050-AC-01 | R08 gives "R08 · baseline stuck at 13 of 16" with the exact detail; 15 inclusive days none, 16 one | TC-050-02, TC-050-03 |
| FEAT-050-AC-02 | Oct 8 and Oct 22 quarantines give the plural R05 detail; one session gives the singular detail | TC-050-04 |
| FEAT-050-AC-03 | 7 of 29 gives the R03 alert with kinds in fixed order; 2 of 9 none; both rules → only baseline_stalled | TC-050-05, TC-050-06, TC-050-07 |
| FEAT-050-AC-04 | D02 Oct 12 alert exact; isolated single-device days none; 2 consecutive days one "device silent on 2 days"; unassigned device none | TC-050-08, TC-050-09, TC-050-10 |
| FEAT-050-AC-05 | SRC-05 output exactly the four FR-09 alerts in order and no other | TC-050-01, TC-050-13 |
| FEAT-050-AC-06 | Changing `data_alert_set_aside_fraction` changes high_set_aside without changing `config_hash()`; no tally or alarm state touched | TC-050-11, TC-050-12 |

## Test Data Requirements

- SRC-05 and the R01–R10 roster (`tests.unit.analytics.src05`), as-of 2026-10-30 15:00 America/Chicago; variants: as-of 2026-10-09 23:00, 2026-10-15 15:00, 2026-10-16 15:00; SRC-05 without `R05-20261022-01`; SRC-05 without `R01-20261005-01` and `R01-20261006-01`.
- DS-07 database for TC-050-13; `SEED_CLINICIAN_PASSWORD`, `SEED_RESEARCHER_PASSWORD` from the environment file.
- No audio, names or rooms.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-050-FR-01 / FR-290, CUS-046, ANL-059 | FEAT-050 | TC-050-03, TC-050-11 |
| FEAT-050-FR-02 / FR-291 | FEAT-050 | TC-050-02, TC-050-03 |
| FEAT-050-FR-03 / FR-292 | FEAT-050 | TC-050-04 |
| FEAT-050-FR-04 / FR-293, FR-295 | FEAT-050 | TC-050-05, TC-050-06, TC-050-07 |
| FEAT-050-FR-05 / FR-294 | FEAT-050 | TC-050-08, TC-050-09, TC-050-10 |
| FEAT-050-FR-06 / FR-295, CUS-043 | FEAT-050 | TC-050-01, TC-050-09 |
| FEAT-050-FR-07 / FR-300, D-36 | FEAT-050 | TC-050-12 |
| FEAT-050-FR-08 / FR-296 | FEAT-050 | TC-050-01 step 6, TC-050-08, TC-050-13 |
| FEAT-050-FR-09 / FR-301, CUS-044, D-114 | FEAT-050 | TC-050-01, TC-050-13 |
| DA-01, DA-02 | FEAT-050 | TC-050-02, TC-050-03 |
| DA-03 | FEAT-050 | TC-050-04 |
| DA-04, DA-05, DA-06 | FEAT-050 | TC-050-05, TC-050-06, TC-050-07 |
| DA-07, DA-08, DA-09, DA-10 | FEAT-050 | TC-050-08, TC-050-09, TC-050-10 |
| DA-11 | FEAT-050 (via FEAT-053) | TC-053-09 |
| AC-ANL-10, AC-CUS-09, TDV-068 | FEAT-050 | TC-050-01, TC-050-13, TC-060-05 |
| TST-020, TST-011 | FEAT-050 | TC-050-14 |
