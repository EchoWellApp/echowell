# Residents overview API (GET /api/v1/residents) with display status and sorts

## Feature Description

`GET /api/v1/residents` (TRD 19 E-08) serves the v0.2 Resident list: one row per resident of the requested cohort with the pipeline `status` (`alarm_on`, `baseline_forming`, `no_alarm`), the attention flag (`needs_attention`, `attention_reasons`), `alarm_reviewed`, the current epoch and its `restart_cause`, device facts, last check-in and last-30-day counts; the display-status `summary` (`changed`, `needs_attention`, `learning`, `usual`) computed over all matching residents independent of paging; and three sort orders, whose default `sort=alarm` lists Changed → Needs attention → Learning → Usual. Everything is derived on read from the latest succeeded pipeline run. The endpoint is read-only and open to admin, clinician and researcher. Source: FEAT-027; TRD 05 API-070..API-074, API-138; TRD 23 §4.4.3; TRD 24 D-109, D-114.

## Preconditions

1. Local Docker Compose stack running (`docs/deployment.md` steps 1–5), environment file from `.env.development.example`.
2. **DS-07 state:** `docker compose exec backend python -m backend.cli seed test_v0_1` (SRC-05 ingested, pipeline run at as-of 2026-10-30 15:00 America/Chicago = `2026-10-30T20:00:00Z`).
3. `API=http://localhost:8000/api/v1`; tokens `ADMIN`, `CLIN`, `RES` from `POST $API/auth/login` for the three seeded users with their `SEED_*` passwords; `KEY` = the ingest API key from the environment file.
4. `psql` read access to the local database; Python 3.12 environment with the dev requirements for the `pytest` cases (local development stack).
5. Cases that change data (TC-027-05) end with `docker compose exec backend python -m backend.cli seed test_v0_1 --reset`.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-027-01 | DS-07 default sort, summary, attention flags and `alarm_reviewed` | High | Positive |
| TC-027-02 | DS-07 row facts for R08, R07, R09, R03 and the 30-day `window` | High | Positive |
| TC-027-03 | DS-07 `sort=last_checkin` and `sort=resident_id` orders | High | Positive |
| TC-027-04 | Invalid query parameters return 422 `INVALID_QUERY_PARAMETER` | High | Negative |
| TC-027-05 | Withdrawn resident excluded by default and included with `include_withdrawn=true` | High | Positive |
| TC-027-06 | `limit=1` keeps `summary` and `total` over all matching residents | High | API |
| TC-027-07 | Duplicates never counted (R04 stays 30 used) | High | Database |
| TC-027-08 | Response schema and `meta` with all seven fields | High | API |
| TC-027-09 | Role access: API key 401, anonymous 401, every user role 200 | High | Security |
| TC-027-10 | Four-resident status fixture and natural sort R2 < R10 (integration tests) | High | Analytics |
| TC-027-11 | After a saved review, R09 stays `alarm_on` with `alarm_reviewed` true | Medium | Positive |
| TC-027-12 | `cohort=new_admission` returns an empty list with zero summary for DS-07 | Medium | Positive |
| TC-027-13 | No succeeded run: 200 with `meta.as_of` null and `baseline_forming` rows | Medium | Negative |
| TC-027-14 | Database unavailable returns 503 with `Retry-After: 30` | Medium | Negative |

### TC-027-01 DS-07 default sort, summary, attention flags and `alarm_reviewed`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s $API/residents -H "Authorization: Bearer $CLIN"` | HTTP 200 |
| 2 | List `items[].resident_code` | R09, R10, R03, R08, R01, R02, R04, R05, R06, R07 (in this order); `total` 10; `limit` 50; `offset` 0 |
| 3 | Read `summary` | `{"changed": 2, "needs_attention": 2, "learning": 0, "usual": 6}`; the four sum to `total` 10 |
| 4 | Read `status` per row | R09 and R10 `alarm_on`; R08 `baseline_forming`; R01, R02, R03, R04, R05, R06, R07 `no_alarm` |
| 5 | Read `needs_attention` / `attention_reasons` per row | true only for R03 (`["high_set_aside"]`) and R08 (`["baseline_stalled"]`); all others false with `[]` (R05 false despite its open `possible_other_speaker` data alert; R02 and R03 status not changed by the D02 `device_silent` alert) |
| 6 | Read `alarm_reviewed`, `alarm_since`, `open_alert_id` | R09: false, "2026-10-21", a uuid; R10: false, "2026-10-24", a uuid; all other rows: null, null, null |

### TC-027-02 DS-07 row facts for R08, R07, R09, R03 and the 30-day `window`

| Step | Action | Expected Result |
|---|---|---|
| 1 | From the TC-027-01 response read `window` | `{"from": "2026-10-01", "to": "2026-10-30", "days": 30}` |
| 2 | Row R08 | `baseline_progress` `{"n_usable": 13, "n_required": 16}`; `last_30_days` `{"used": 13, "set_aside": 5, "quarantined": 0, "missed": 12}`; `current_epoch` 1; `restart_cause` null |
| 3 | Row R07 | `device_code` "D07B"; `previous_device_code` "D07"; `current_epoch` 2; `baseline_restarted_on` "2026-10-13"; `restart_cause` "device"; `device_shared` false |
| 4 | Row R09 | `device_code` "D09"; `device_shared` false; `baseline_progress` 16 of 16; `last_checkin_at` "2026-10-30T19:28:04Z"; `last_checkin_local` "2026-10-30T14:28:04-05:00"; `last_30_days` 30 · 0 · 0 · 0 |
| 5 | Row R03 | `device_code` "D02"; `device_shared` true; `last_checkin_at` "2026-10-30T19:19:17Z"; `last_30_days` 22 · 7 · 0 · 1 |
| 6 | Rows R02 and R05 | R02 `last_30_days` 24 · 0 · 0 · 6 and `device_shared` true; R05 28 · 0 · 2 · 0 |
| 7 | Every row | Only `resident_code` identifies the resident (no `id`, name or room field); `cohort` "longitudinal"; `resident_status` "active" |

### TC-027-03 DS-07 `sort=last_checkin` and `sort=resident_id` orders

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/residents?sort=last_checkin` | `items` order R02, R07, R05, R10, R06, R08, R09, R03, R04, R01 (most recent last check-in first) |
| 2 | `GET $API/residents?sort=resident_id` | `items` order R01, R02, R03, R04, R05, R06, R07, R08, R09, R10 |
| 3 | Compare `summary` of steps 1, 2 and TC-027-01 | Identical (sorting never changes counts) |

### TC-027-04 Invalid query parameters return 422 `INVALID_QUERY_PARAMETER`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/residents?sort=foo` | HTTP 422; `type` "urn:echowell:error:INVALID_QUERY_PARAMETER"; `title` "Invalid query parameter"; `errors[]` names `sort` |
| 2 | `GET $API/residents?limit=0` | HTTP 422 `INVALID_QUERY_PARAMETER` |
| 3 | `?limit=501`, `?offset=-1`, `?cohort=other`, `?include_withdrawn=maybe` (one request each) | Each HTTP 422 `INVALID_QUERY_PARAMETER` |
| 4 | `?limit=500` and `?offset=0` | HTTP 200 |

### TC-027-05 Withdrawn resident excluded by default and included with `include_withdrawn=true`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker compose exec backend python -m backend.cli withdraw-resident R06 --on 2026-10-30` | "Resident R06 withdrawn on 2026-10-30."; exit 0 |
| 2 | `GET $API/residents` | R06 absent; `total` 9; `summary` `{"changed": 2, "needs_attention": 2, "learning": 0, "usual": 5}` |
| 3 | `GET $API/residents?include_withdrawn=true` | R06 present with `resident_status` "withdrawn"; `total` 10 |
| 4 | `SELECT status, withdrawn_on FROM residents WHERE resident_code='R06';` | `withdrawn`, 2026-10-30 |
| 5 | Restore: `docker compose exec backend python -m backend.cli seed test_v0_1 --reset` | DS-07 state again |

### TC-027-06 `limit=1` keeps `summary` and `total` over all matching residents

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/residents?limit=1` | `items` has exactly 1 row (R09); `total` 10; `limit` 1; `summary` 2 / 2 / 0 / 6 |
| 2 | `GET $API/residents?limit=3&offset=3` | `items` R08, R01, R02; `total` 10; `summary` unchanged |
| 3 | `GET $API/residents?offset=20` | `items` []; `total` 10; `summary` unchanged |

### TC-027-07 Duplicates never counted (R04 stays 30 used)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT session_id, status FROM processed_sessions ps JOIN residents r ON r.id = ps.resident_id WHERE r.resident_code='R04' AND status='duplicate';` | 2 rows: R04-20261005-01 and R04-20261018-01 |
| 2 | Row R04 of `GET $API/residents` | `last_30_days` `{"used": 30, "set_aside": 0, "quarantined": 0, "missed": 0}` (duplicates not counted) |
| 3 | `SELECT max(timestamp_utc) FROM processed_sessions ps JOIN residents r ON r.id=ps.resident_id WHERE r.resident_code='R04' AND status <> 'duplicate';` | Equals row R04 `last_checkin_at` (Oct 30, 2:17 PM CT = 19:17 UTC) |
| 4 | Fixture case: `pytest tests/integration/api/test_residents.py::test_overview -q` | Passes; it asserts R01's `last_checkin_at` ignores a later duplicate dated inside the window |

### TC-027-08 Response schema and `meta` with all seven fields

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read `meta` from TC-027-01 | Exactly the keys `facility_name`, `facility_tz` ("America/Chicago"), `data_source_label` ("pipeline test data v0.1"), `as_of` ("2026-10-30T20:00:00Z"), `baseline_n` (16), `cusum_h` (5.0), `pipeline_profile` ("test_v0_1") |
| 2 | Validate the body against `ResidentsOverviewResponse` from `GET $API/openapi.json` | Valid; top-level keys `meta`, `window`, `summary`, `items`, `total`, `limit`, `offset` |
| 3 | Every row has the `ResidentOverviewRow` keys | `resident_code`, `cohort`, `resident_status`, `device_code`, `device_shared`, `previous_device_code`, `status`, `needs_attention`, `attention_reasons`, `alarm_since`, `open_alert_id`, `alarm_reviewed`, `current_epoch`, `baseline_restarted_on`, `restart_cause`, `baseline_progress`, `last_checkin_at`, `last_checkin_local`, `last_30_days` |

### TC-027-09 Role access: API key 401, anonymous 401, every user role 200

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/residents` with `$ADMIN`, `$CLIN`, `$RES` (three requests) | Each HTTP 200 with identical bodies |
| 2 | `GET $API/residents -H "X-API-Key: $KEY"` | HTTP 401; `type` "urn:echowell:error:NOT_AUTHENTICATED" |
| 3 | `GET $API/residents` with no header | HTTP 401 `NOT_AUTHENTICATED` |
| 4 | `GET $API/residents` with `Authorization: Bearer invalid.token.value` | HTTP 401 `TOKEN_INVALID` |
| 5 | `SELECT count(*) FROM audit_logs WHERE occurred_at > now() - interval '5 minutes' AND action NOT LIKE 'auth.%' AND action <> 'access.denied';` | 0 (read endpoint writes no audit row) |

### TC-027-10 Four-resident status fixture and natural sort R2 < R10 (integration tests)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/integration/api/test_residents.py::test_overview -q` | Passes: fixture covers an `alarm_on` resident (non-closed alert in the current epoch), a forming resident, a frozen resident in epoch 2 with `restart_cause` "device" and `baseline_restarted_on`, and a `no_alarm` resident with `needs_attention` true and `attention_reasons` ["high_set_aside"]; default order alarm → attention → forming → usual |
| 2 | `pytest tests/integration/api/test_residents.py::test_other_sort_orders -q` | Passes: `sort=resident_id` puts R2 before R10 (natural order) and `sort=last_checkin` puts residents without a check-in last |
| 3 | `pytest tests/integration/api/test_residents.py -q -m integration` | All tests pass; none skipped |

Note: FEAT-027 names unit tests in `tests/unit/backend/services/test_resident_service.py`; that file does not exist. The criteria are asserted by the integration tests above (`tests/integration/api/test_residents.py:38-101`).

### TC-027-11 After a saved review, R09 stays `alarm_on` with `alarm_reviewed` true

| Step | Action | Expected Result |
|---|---|---|
| 1 | Take R09's `open_alert_id` from TC-027-01; `POST $API/alerts/<id>/reviews` as clinician with `{"explanations": ["cold_cough_sore_throat"], "outcome": "known_cause"}` | HTTP 201 |
| 2 | `GET $API/residents` | R09 `status` "alarm_on", `alarm_reviewed` true; order and `summary` unchanged (R09 still first, changed 2) |
| 3 | Restore with `seed test_v0_1 --reset` | DS-07 state again |

### TC-027-12 `cohort=new_admission` returns an empty list with zero summary for DS-07

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/residents?cohort=new_admission` | HTTP 200; `items` []; `total` 0; `summary` `{"changed": 0, "needs_attention": 0, "learning": 0, "usual": 0}`; `meta` present |

### TC-027-13 No succeeded run: 200 with `meta.as_of` null and `baseline_forming` rows

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker compose exec backend python -m backend.cli seed test_v0_1 --master-only --reset` (no records, no run) | Exit 0 |
| 2 | `GET $API/residents` | HTTP 200; `meta.as_of` null; 10 rows; every `status` "baseline_forming"; `last_30_days` all 0; `last_checkin_at` null; `summary` `{"changed": 0, "needs_attention": 0, "learning": 10, "usual": 0}` |
| 3 | Restore with `seed test_v0_1 --reset` | DS-07 state again |

### TC-027-14 Database unavailable returns 503 with `Retry-After: 30`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker compose stop db`; `curl -i $API/residents -H "Authorization: Bearer $CLIN"` | HTTP 503; `Retry-After: 30`; `type` "urn:echowell:error:SERVICE_UNAVAILABLE" |
| 2 | `docker compose start db`; repeat the request | HTTP 200 with the DS-07 body |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents` defaults | `sort=alarm`, `cohort=longitudinal`, `include_withdrawn=false`, `limit` 50, `offset` 0 |
| 2 | Status rule | `alarm_on` iff a non-closed (`open` or `acknowledged`) alert exists for the current epoch; else `baseline_forming` without frozen baseline; else `no_alarm` |
| 3 | Summary | Computed over all filtered residents, independent of `limit`/`offset`; precedence Changed > Needs attention > Learning > Usual |
| 4 | Error responses | 422 `INVALID_QUERY_PARAMETER` (offending parameter in `errors[]`); 401 for API key / anonymous; 503 with `Retry-After: 30` |
| 5 | Time formats | `last_checkin_at` UTC with `Z`; `last_checkin_local` with `-05:00`; `window` dates `YYYY-MM-DD` |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT r.resident_code FROM alerts a JOIN residents r ON r.id=a.resident_id WHERE a.status IN ('open','acknowledged');` | R09, R10 — matches the `alarm_on` rows |
| 2 | `SELECT kind, r.resident_code FROM data_alerts d JOIN residents r ON r.id=d.resident_id WHERE d.status='open' AND kind IN ('baseline_stalled','high_set_aside');` | `baseline_stalled` R08, `high_set_aside` R03 — matches `needs_attention` |
| 3 | `SELECT r.resident_code, e.epoch_number FROM epochs e JOIN residents r ON r.id=e.resident_id WHERE e.ended_at IS NULL AND e.epoch_number > 1;` | Only R07 epoch 2 — matches `current_epoch` and `restart_cause` |
| 4 | `SELECT count(*) FROM day_ledger dl JOIN residents r ON r.id=dl.resident_id WHERE r.resident_code='R08' AND dl.status IN ('missing_resident','missing_device_gap') AND dl.local_date BETWEEN '2026-10-01' AND '2026-10-30';` | 12 — equals R08 `last_30_days.missed` |
| 5 | Row counts of all tables before and after the read cases | Unchanged (read-only endpoint; status is never stored) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | `sort=foo`, `limit=0`, `limit=501`, `offset=-1`, `cohort=other`, `include_withdrawn=maybe` | 422 `INVALID_QUERY_PARAMETER` each |
| 2 | API key or no credentials | 401 `NOT_AUTHENTICATED` |
| 3 | Invalid bearer token | 401 `TOKEN_INVALID` |
| 4 | No succeeded run (TC-027-13) | 200, `meta.as_of` null, no 500 |
| 5 | Database stopped (TC-027-14) | 503 `SERVICE_UNAVAILABLE`, `Retry-After: 30` |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-027-AC-01 | `?sort=foo` and `?limit=0` each return 422 `urn:echowell:error:INVALID_QUERY_PARAMETER` | TC-027-04 |
| FEAT-027-AC-02 | Four-resident fixture gives `alarm_on`, `baseline_forming`, `no_alarm` (epoch 2, `restart_cause` device) and `no_alarm` with `needs_attention` true / [`high_set_aside`]; `sort=alarm` alarm, attention, forming, epoch-2; summary 1/1/1/1 | TC-027-10 |
| FEAT-027-AC-03 | `sort=resident_id` returns R2 before R10 | TC-027-10 |
| FEAT-027-AC-04 | Withdrawn resident absent by default, present with `include_withdrawn=true` | TC-027-05 |
| FEAT-027-AC-05 | With `limit=1`, `summary` counts every matching resident and `total` = number of matching residents | TC-027-06 |
| FEAT-027-AC-06 | A duplicate inside the window changes neither `last_30_days` nor `last_checkin_at` | TC-027-07 |
| FEAT-027-AC-07 | DS-07 default order R09, R10, R03, R08, R01, R02, R04, R05, R06, R07; summary 2/2/0/6; attention only R03 and R08; `alarm_reviewed` false R09/R10, null others; R08 13 of 16 and 13·5·0·12; R07 D07B/D07/2026-10-13/device; window 2026-10-01..2026-10-30, 30 | TC-027-01, TC-027-02 |
| FEAT-027-AC-08 | DS-07 `sort=last_checkin` R02, R07, R05, R10, R06, R08, R09, R03, R04, R01; `sort=resident_id` R01 … R10 | TC-027-03 |
| FEAT-027-AC-09 | Every 200 validates against `ResidentsOverviewResponse` with `meta` of seven fields | TC-027-08 |
| FEAT-027-AC-10 | API key 401; each user role 200 | TC-027-09 |

## Test Data Requirements

- DS-07: `test_v0_1` profile, SRC-05 ingested by `seed test_v0_1`, as-of 2026-10-30 15:00 America/Chicago; expected values from TRD 11 §4.13.1–§4.13.3 and TRD 19 E-08.
- Master-only database (`seed test_v0_1 --master-only --reset`) for TC-027-13.
- Integration-test fixtures of `tests/integration/world.py` (`scene`) for TC-027-07 step 4 and TC-027-10 (residents R2 and R10 among them).
- Environment: `SEED_ADMIN_PASSWORD`, `SEED_CLINICIAN_PASSWORD`, `SEED_RESEARCHER_PASSWORD`, `SEED_INGEST_API_KEY` from the environment file.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-027-FR-01 (API-070, API-016; FR-133) | FEAT-027 | TC-027-04 |
| FEAT-027-FR-02 (FR-130, TST-055) | FEAT-027 | TC-027-05, TC-027-12 |
| FEAT-027-FR-03 (FR-131, FR-302, DME-011, API-138, CUS-020, CUS-021) | FEAT-027 | TC-027-01, TC-027-10, TC-027-11 |
| FEAT-027-FR-04 (FR-131, FR-134, API-138) | FEAT-027 | TC-027-01, TC-027-11 |
| FEAT-027-FR-05 (FR-132, DB-065, D-114) | FEAT-027 | TC-027-02 |
| FEAT-027-FR-06 (FR-131) | FEAT-027 | TC-027-02 |
| FEAT-027-FR-07 (FR-134) | FEAT-027 | TC-027-02 |
| FEAT-027-FR-08 (FR-134, API-094, D-42) | FEAT-027 | TC-027-02, TC-027-07 |
| FEAT-027-FR-09 (API-074, FR-135, UX-047, UX-048, AGT-053) | FEAT-027 | TC-027-02, TC-027-07 |
| FEAT-027-FR-10 (API-071, UX-408, D-109) | FEAT-027 | TC-027-01, TC-027-10 |
| FEAT-027-FR-11 (API-072, AGT-052) | FEAT-027 | TC-027-03, TC-027-10 |
| FEAT-027-FR-12 (API-073, D-114) | FEAT-027 | TC-027-01, TC-027-06 |
| FEAT-027-FR-13 (API-057, API-069, API-100) | FEAT-027 | TC-027-08 |
| FEAT-027-FR-14 (ANL-019) | FEAT-027 | TC-027-13 |
| TST-033 | FEAT-027 | TC-027-10 |
| TST-055 | FEAT-027 | TC-027-05 |
| TST-061, TST-064 | FEAT-027 | TC-027-08 |
| AC-API-02 / OAS-021 / TDV-062 / TDV-063 | FEAT-027 | TC-027-01, TC-027-02 |
| TDV-064, TDV-065 | FEAT-027 | TC-027-02, TC-027-07 |
| E2E-05, E2E-06 | FEAT-027 | TC-027-03 |
| API-097 | FEAT-027 | TC-027-14 |
