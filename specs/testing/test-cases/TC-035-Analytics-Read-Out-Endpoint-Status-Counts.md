# Analytics read-out endpoint (GET /api/v1/analytics): status counts, outcomes, run info, alarm timing and review outcomes

## Feature Description

`GET /api/v1/analytics` (TRD 19 E-18) gives researchers and admins the Study team read-out: `meta`, the 30-day `period`, per-resident `status_counts` (SRC-03 Exp_status_counts shape) and their `status_totals`, `resident_outcomes` per resident-epoch (Exp_resident_outcomes shape), the latest succeeded `pipeline_run`, and exactly one of `alarm_timing` (profile `test_v0_1`: alarms compared with the planted change dates of `evaluation_ground_truth`) or `review_outcomes` (profile `production`). The ground truth is read only by `backend/services/analytics_summary.py`, after the pipeline has run, through a separate read-only engine on `DATABASE_READONLY_URL`, so it can never influence the analytics. Clinicians receive 403. The `kpis`, `daily_series`, `funnel` and `by_resident` blocks come from FEAT-051 and are not asserted here. Source: FEAT-035; TRD 05 API-087, API-136; TRD 09 CUS-047..CUS-049; TRD 12 SEC-116; TRD 20 PGS-040; TRD 24 D-38, D-81.

## Preconditions

1. Local Docker Compose stack running; environment file from `.env.development.example` (`PIPELINE_PROFILE=test_v0_1`, `DATABASE_READONLY_URL` set).
2. **DS-07 + DS-10 state:** `docker compose exec backend python -m backend.cli seed test_v0_1`, then `docker compose exec backend python database/seeds/load_evaluation_ground_truth.py tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv` (`docs/deployment.md` step 6).
3. `API=http://localhost:8000/api/v1`; tokens `ADMIN`, `CLIN`, `RES` from `POST $API/auth/login` with the `SEED_*` passwords; `KEY` = the ingest API key from the environment file.
4. `psql` access as the app login (`echowell_app_login`) for read checks and the grant check.
5. Local development stack with dev requirements for the `pytest` cases.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-035-01 | Role access: clinician 403; researcher and admin 200; API key 401 | High | Security |
| TC-035-02 | DS-07 status totals, R02 status counts, 10 count rows, 11 outcome rows | High | Analytics |
| TC-035-03 | DS-07 + DS-10 alarm timing: R09 0 days, R10 7 days, 8 `correct_no_alarm`; `review_outcomes` null | High | Analytics |
| TC-035-04 | Production profile: `alarm_timing` null, `review_outcomes` present, no read-only connection | High | Positive |
| TC-035-05 | Static boundary: only `analytics_summary.py` references the read-only URL / ground-truth table | High | Security |
| TC-035-06 | `pipeline_run` equals the latest succeeded run; response validates against `AnalyticsResponse` | High | API |
| TC-035-07 | `period` and `meta` with `baseline_n`, `cusum_h`, `pipeline_profile` | Medium | Positive |
| TC-035-08 | R07 and R08 outcome rows (two epochs; baseline not formed note) | Medium | Analytics |
| TC-035-09 | App role cannot read `evaluation_ground_truth` (42501); no `SET ROLE` in code | Medium | Security |
| TC-035-10 | Ground truth not loaded: `alarm_timing` is an empty array, no 500 | Medium | Negative |
| TC-035-11 | No succeeded run: `pipeline_run` null, `meta.as_of` null, zero totals | Low | Negative |

### TC-035-01 Role access: clinician 403; researcher and admin 200; API key 401

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s -i $API/analytics -H "Authorization: Bearer $CLIN"` | HTTP 403; `type` "urn:echowell:error:FORBIDDEN"; one `access.denied` audit row |
| 2 | Same with `$RES` and with `$ADMIN` | HTTP 200 each |
| 3 | Same with `X-API-Key: $KEY` and with no credentials | HTTP 401 `NOT_AUTHENTICATED` |

### TC-035-02 DS-07 status totals, R02 status counts, 10 count rows, 11 outcome rows

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/analytics` as researcher; read `status_totals` | `{"usable": 267, "set_aside": 12, "quarantined": 2, "duplicate": 2, "missing_resident": 17, "missing_device_gap": 2}` |
| 2 | `status_counts` | 10 rows, one per resident R01–R10; the six counts of each column sum to the `status_totals` values |
| 3 | Row R02 | `usable` 24, `set_aside` 0, `quarantined` 0, `duplicate` 0, `missing_resident` 5, `missing_device_gap` 1 |
| 4 | `resident_outcomes` | 11 rows (one per resident-epoch with ≥ 1 usable session; R07 has epochs 1 and 2) |
| 5 | Row R09 of `resident_outcomes` | `epoch_number` 1, `device_code` "D09", `usable_in_epoch` 30, `baseline_formed` true, `baseline_frozen_after` "R09-20261016-01", `scored_sessions` 14, `first_alarm_session` "R09-20261021-01", `note` null |

### TC-035-03 DS-07 + DS-10 alarm timing: R09 0 days, R10 7 days, 8 `correct_no_alarm`; `review_outcomes` null

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/analytics` as researcher; read `alarm_timing` | 10 rows, one per resident |
| 2 | Row R09 | `planted_change` "Sudden step"; `change_began` "2026-10-21"; `alarm_rang` "2026-10-21"; `delay_days` 0; `result` "detected" |
| 3 | Row R10 | "Slow drift"; "2026-10-17"; "2026-10-24"; 7; "detected" |
| 4 | Other 8 rows (R01–R08) | `planted_change` "None"; `change_began` null; `alarm_rang` null; `delay_days` null; `result` "correct_no_alarm" |
| 5 | `review_outcomes` | null |

### TC-035-04 Production profile: `alarm_timing` null, `review_outcomes` present, no read-only connection

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/integration/api/test_analytics.py::test_production_profile -q` (app instance configured with `PIPELINE_PROFILE=production` against the test database, no `PIPELINE_AS_OF`) | Passes: `alarm_timing` null; `review_outcomes` non-null with `alarms_raised`, `reviewed` and `by_outcome` keys `no_concern`, `known_cause`, `referred`, `data_problem`; each alert counted once by its latest review's outcome |
| 2 | `pytest tests/integration/api/test_analytics.py::test_read_only_engine -q` | Passes: under `production` no connection to `DATABASE_READONLY_URL` is opened; under `test_v0_1` the read-only engine is used for the ground truth only |
| 3 | `pytest tests/integration/api/test_analytics.py -q` | All tests pass |

### TC-035-05 Static boundary: only `analytics_summary.py` references the read-only URL / ground-truth table

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/unit/backend/test_ground_truth_boundary.py -q` | Passes on the delivered code |
| 2 | `grep -rlE "DATABASE_READONLY_URL\|database_readonly_url\|evaluation_ground_truth\|EvaluationGroundTruth" analytics --include=*.py` | No file |
| 3 | `grep -rlE "DATABASE_READONLY_URL\|database_readonly_url\|evaluation_ground_truth\|EvaluationGroundTruth" backend --include=*.py \| grep -v "^backend/alembic/"` | `backend/services/analytics_summary.py` plus only the table definition (`backend/models/evaluation.py`, `backend/models/__init__.py` export) and the settings field (`backend/core/config.py`); no pipeline, repository or router module |
| 4 | Negative check of the test: add a line `# evaluation_ground_truth` to a copy of `backend/services/pipeline_runner.py` in a scratch checkout and re-run step 1 there | The test fails naming that file (discard the scratch change) |

Note: FEAT-035-AC-05 and TRD 05 API-136 state that no file other than `analytics_summary.py` may reference these names; the delivered boundary test also allows `backend/core/config.py`, `backend/models/__init__.py`, `backend/models/evaluation.py` and `backend/alembic/` (`tests/unit/backend/test_ground_truth_boundary.py:22-36`).

### TC-035-06 `pipeline_run` equals the latest succeeded run; response validates against `AnalyticsResponse`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT id, trigger, scope, config_profile, as_of, status, counts FROM pipeline_runs WHERE status='succeeded' ORDER BY as_of DESC, finished_at DESC LIMIT 1;` | The seed run: `trigger` manual, `scope` {"type": "all"}, `config_profile` test_v0_1, `as_of` 2026-10-30 20:00:00+00 |
| 2 | `pipeline_run` of `GET $API/analytics` | Same `id`, `trigger` "manual", `scope` "all", `config_profile` "test_v0_1", `as_of` "2026-10-30T20:00:00Z", `status` "succeeded"; `counts` includes `arrivals` 283, `usable` 267, `set_aside` 12, `quarantined` 2, `duplicate` 2, `missing_resident` 17, `missing_device_gap` 2, `scored` 98, `alerts_opened` 2 |
| 3 | Validate the body against `AnalyticsResponse` from `GET $API/openapi.json` | Valid; keys `meta`, `period`, `kpis`, `daily_series`, `funnel`, `by_resident`, `alarm_timing`, `review_outcomes`, `status_totals`, `status_counts`, `resident_outcomes`, `pipeline_run` |

### TC-035-07 `period` and `meta` with `baseline_n`, `cusum_h`, `pipeline_profile`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read `period` | `{"from": "2026-10-01", "to": "2026-10-30", "days": 30}` |
| 2 | Read `meta` | `baseline_n` 16; `cusum_h` 5.0; `pipeline_profile` "test_v0_1"; `as_of` "2026-10-30T20:00:00Z"; no `cusum_k` field in the response |

### TC-035-08 R07 and R08 outcome rows (two epochs; baseline not formed note)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `resident_outcomes` rows for R07 | Two rows: epoch 1 `device_code` "D07", `baseline_formed` false, `scored_sessions` null, `first_alarm_session` null, `note` "Too few usable sessions: baseline pending, nothing scored"; epoch 2 `device_code` "D07B", `baseline_formed` true, `scored_sessions` 2, `note` null |
| 2 | Row R08 | `epoch_number` 1; `usable_in_epoch` 13; `baseline_formed` false; `baseline_frozen_after` null; `scored_sessions` null; `note` "Too few usable sessions: baseline pending, nothing scored" |

### TC-035-09 App role cannot read `evaluation_ground_truth` (42501); no `SET ROLE` in code

| Step | Action | Expected Result |
|---|---|---|
| 1 | As `echowell_app_login`: `SELECT * FROM evaluation_ground_truth;` | ERROR: permission denied for table evaluation_ground_truth (SQLSTATE 42501) |
| 2 | `grep -rni "set role" backend analytics --include=*.py` | No match in application code |
| 3 | `docker compose logs backend --since 10m \| grep -ciE "readonly_login\|Sudden step\|Slow drift"` | 0 (no connection URL or ground-truth value logged) |

### TC-035-10 Ground truth not loaded: `alarm_timing` is an empty array, no 500

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker compose exec backend python -m backend.cli seed test_v0_1 --reset` (do not run the DS-10 loader) | Exit 0 |
| 2 | `GET $API/analytics` as researcher | HTTP 200; `alarm_timing` []; `review_outcomes` null; `status_totals` as in TC-035-02 |
| 3 | Reload DS-10 with the loader command of the preconditions | Alarm timing rows return |

### TC-035-11 No succeeded run: `pipeline_run` null, `meta.as_of` null, zero totals

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker compose exec backend python -m backend.cli seed test_v0_1 --master-only --reset` | Exit 0 |
| 2 | `GET $API/analytics` as admin | HTTP 200; `pipeline_run` null; `meta.as_of` null; all `status_totals` 0; `resident_outcomes` [] |
| 3 | Restore: `seed test_v0_1 --reset` and the DS-10 loader | DS-07 + DS-10 again |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/analytics` (researcher, admin) | 200 `AnalyticsResponse` |
| 2 | Profile branch | `test_v0_1`: `alarm_timing` array, `review_outcomes` null; `production`: `alarm_timing` null, `review_outcomes` object |
| 3 | `AlarmTimingRow.result` values | One of `detected`, `missed`, `correct_no_alarm`, `false_alarm`; `delay_days` = alarm local date − onset date (null for an alarm before onset) |
| 4 | Errors | 403 clinician; 401 API key / anonymous; 503 when the read-only engine is unavailable under test_v0_1 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT status, count(*) FROM processed_sessions GROUP BY status;` | usable 267, set_aside 12, quarantined 2, duplicate 2 = `status_totals` |
| 2 | `SELECT status, count(*) FROM day_ledger WHERE status IN ('missing_resident','missing_device_gap') GROUP BY status;` | missing_resident 17, missing_device_gap 2 |
| 3 | `SELECT count(*) FROM evaluation_ground_truth;` (as the readonly or migrator login) | 10 after DS-10 load |
| 4 | Row counts before and after the endpoint calls | Unchanged (read-only) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Clinician GET | 403 `FORBIDDEN` |
| 2 | API key / anonymous | 401 |
| 3 | App role reads `evaluation_ground_truth` | 42501 permission denied |
| 4 | Ground truth empty | `alarm_timing` [], no 500 |
| 5 | No succeeded run | 200 with null `pipeline_run` and zero totals |
| 6 | `docker compose stop db`, then GET | 503 `SERVICE_UNAVAILABLE`; `docker compose start db` afterwards |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-035-AC-01 | Clinician 403 `FORBIDDEN`; researcher and admin 200 | TC-035-01 |
| FEAT-035-AC-02 | `status_totals` 267/12/2/2/17/2; 10 `status_counts` rows (R02 24, 5, 1); 11 `resident_outcomes` rows (R07 epochs 1 and 2) | TC-035-02, TC-035-08 |
| FEAT-035-AC-03 | `alarm_timing` R09 Sudden step 2026-10-21/2026-10-21/0/detected; R10 Slow drift 2026-10-17/2026-10-24/7/detected; 8 rows "None", null, `correct_no_alarm`; `review_outcomes` null | TC-035-03 |
| FEAT-035-AC-04 | Production: `alarm_timing` null; `review_outcomes` with the four `by_outcome` keys; no `DATABASE_READONLY_URL` connection | TC-035-04 |
| FEAT-035-AC-05 | Static test fails on any other file referencing `DATABASE_READONLY_URL` / `evaluation_ground_truth` and passes on delivered code | TC-035-05 |
| FEAT-035-AC-06 | `pipeline_run` = latest succeeded run (id, trigger, scope, config_profile, as_of, status succeeded, counts); response validates against `AnalyticsResponse` | TC-035-06 |

## Test Data Requirements

- DS-07 (`seed test_v0_1`) and DS-10 (`evaluation_ground_truth` from `tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv`); expected values from TRD 19 E-18 and TRD 05 API-087.
- Master-only database for TC-035-11; DS-07 without DS-10 for TC-035-10.
- Environment: `PIPELINE_PROFILE`, `DATABASE_URL`, `DATABASE_READONLY_URL` (test_v0_1 only), `SEED_*` passwords and `SEED_INGEST_API_KEY` from the environment file.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-035-FR-01 (API-087, FR-243; D-46) | FEAT-035 | TC-035-01 |
| FEAT-035-FR-02 (FR-312, API-069) | FEAT-035 | TC-035-07 |
| FEAT-035-FR-03 (FR-240; TRD 23 §4.7.3; OAS-024) | FEAT-035 | TC-035-02 |
| FEAT-035-FR-04 (FR-240; TRD 23 §4.7.4) | FEAT-035 | TC-035-02, TC-035-08 |
| FEAT-035-FR-05 (FR-240, API-069) | FEAT-035 | TC-035-06, TC-035-11 |
| FEAT-035-FR-06 (API-087, FR-322) | FEAT-035 | TC-035-03, TC-035-04 |
| FEAT-035-FR-07 (CUS-047, FR-318; D-81) | FEAT-035 | TC-035-03, TC-035-10 |
| FEAT-035-FR-08 (API-136, SEC-116, ARC-015, ARC-034, ANL-064, D-38) | FEAT-035 | TC-035-04, TC-035-05, TC-035-09 |
| FEAT-035-FR-09 (CUS-049, FR-319, TDV-104) | FEAT-035 | TC-035-04 |
| FEAT-035-FR-10 (API-087, CUS-029; D-92) | FEAT-035 | TC-035-06, TC-035-07 |
| FEAT-035-FR-11 (ARC-035) | FEAT-035 | TC-035-04 |
| TST-068 / TDV-101 | FEAT-035 | TC-035-05 |
| TDV-104 | FEAT-035 | TC-035-04 |
| OAS-024, OAS-028, AC-API-16 (analytics part) | FEAT-035 | TC-035-02, TC-035-03 |
| PGS-040 / AC-ANL-14 | FEAT-035 | TC-035-09 |
| TST-061, TST-064 | FEAT-035 | TC-035-06 |
