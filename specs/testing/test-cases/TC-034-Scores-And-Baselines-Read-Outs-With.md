# Scores and baselines read-outs with CSV export (GET /scores, GET /analytics/baselines)

## Feature Description

`GET /api/v1/scores` (TRD 19 E-12) returns the scored sessions — the 7 unsigned per-feature z values, `composite_raw`, `composite_z`, `cusum_tally` and `alarm_state` — that draw the "Change score" chart, with `cusum_k` and one `baseline_periods` entry per resident-epoch; JSON is open to every role. `GET /api/v1/analytics/baselines` (E-19, researcher and admin) returns the frozen baselines in SRC-03 Exp_baselines shape. Both return `text/csv` when requested with `Accept: text/csv` by a researcher or admin: a header of the DTO field names (`z` flattened to `z_<feature>`), all matching rows, filename `echowell_<scores|baselines>_<as-of local date>.csv`, refused above 100,000 rows (413) and audited as `export.csv`. Values are stored pipeline output in full precision, study IDs only. Source: FEAT-034; TRD 05 API-079, API-088, API-129; TRD 19 OAS-018, OAS-022, OAS-023; TRD 12 §4.6, §4.12.

## Preconditions

1. Local Docker Compose stack running; environment file from `.env.development.example`.
2. **DS-07 state:** `docker compose exec backend python -m backend.cli seed test_v0_1` (as-of 2026-10-30 15:00 America/Chicago; 98 scored sessions; 180 baseline rows).
3. `API=http://localhost:8000/api/v1`; tokens `ADMIN`, `CLIN`, `RES` from `POST $API/auth/login` with the `SEED_*` passwords; `KEY` = the ingest API key from the environment file.
4. SRC-03 answer key `tests/fixtures/answer_key/EchoWell_pipeline_test_v0_1.xlsx` (sheet Exp_baselines) available for the value comparison.
5. `psql` read access; local development stack for the `pytest` cases.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-034-01 | `epoch` without `resident_code` 422; unknown `resident_code` R11 404 | High | Negative |
| TC-034-02 | DS-07 `GET /scores?resident_code=R09`: 14 rows, `cusum_k`, baseline period, tally values | High | Positive |
| TC-034-03 | Researcher scores CSV: media type, filename, header, 98 data rows; clinician 403 | High | Positive |
| TC-034-04 | DS-07 baselines: 180 rows equal Exp_baselines; R09 loudness values | High | Analytics |
| TC-034-05 | Baselines CSV header and rows equal JSON; clinician 403 for JSON and CSV | High | Security |
| TC-034-06 | Each CSV export writes one `export.csv` audit row with `row_count` | High | Database |
| TC-034-07 | Baseline row order within a resident-epoch: loudness_dbfs … mfcc4, then composite | High | Positive |
| TC-034-08 | Scores JSON for every role; API key 401 | Medium | Security |
| TC-034-09 | Scores filters: `from` / `to`, `epoch`, R07 two epochs, `from` > `to` 422 | Medium | API |
| TC-034-10 | CSV above 100,000 rows returns 413 (integration test) | Medium | Negative |
| TC-034-11 | Exports and JSON contain study IDs only and no free text | Medium | Security |
| TC-034-12 | Empty result: JSON empty arrays; CSV header only | Low | Positive |

### TC-034-01 `epoch` without `resident_code` 422; unknown `resident_code` R11 404

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s -i "$API/scores?epoch=1" -H "Authorization: Bearer $CLIN"` | HTTP 422; `type` "urn:echowell:error:INVALID_QUERY_PARAMETER" |
| 2 | `GET $API/scores?resident_code=R11` | HTTP 404; `type` "urn:echowell:error:RESIDENT_NOT_FOUND" |
| 3 | `GET $API/scores?resident_code=R09&epoch=0` | HTTP 422 `INVALID_QUERY_PARAMETER` |
| 4 | `GET $API/analytics/baselines?epoch=1` as researcher | HTTP 422 `INVALID_QUERY_PARAMETER` |

### TC-034-02 DS-07 `GET /scores?resident_code=R09`: 14 rows, `cusum_k`, baseline period, tally values

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/scores?resident_code=R09` as clinician | HTTP 200; `total` 14; `cusum_k` 0.5; `meta.cusum_h` 5.0 |
| 2 | `baseline_periods` | Exactly 1 entry: `{"resident_code": "R09", "epoch_number": 1, "first_local_date": "2026-10-01", "frozen_after_local_date": "2026-10-16", "frozen_after_session_id": "R09-20261016-01", "n_sessions": 16}` |
| 3 | Row `R09-20261021-01` | `local_date` "2026-10-21"; `cusum_tally` 5.431965 (±1e-6); `alarm_state` "rings"; `z.z_loudness_dbfs` -2.737502; `composite_raw` 2.325508; `composite_z` 4.288307 |
| 4 | Row `R09-20261030-01` | `cusum_tally` 26.830256 (±1e-6); `alarm_state` "on" |
| 5 | Order of `items` | By `resident_code`, then `local_date` ascending (2026-10-17 … 2026-10-30); every row `epoch_number` 1 |
| 6 | Row `R09-20261020-01` | `cusum_tally` 1.643658; `alarm_state` "off" |

### TC-034-03 Researcher scores CSV: media type, filename, header, 98 data rows; clinician 403

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s -D h.txt -o scores.csv $API/scores -H "Authorization: Bearer $RES" -H "Accept: text/csv"` | HTTP 200 |
| 2 | Inspect `h.txt` | `content-type: text/csv; charset=utf-8`; `content-disposition: attachment; filename="echowell_scores_2026-10-30.csv"` |
| 3 | `head -1 scores.csv` | `session_id,resident_code,epoch_number,local_date,is_morning,z_loudness_dbfs,z_total_phrase_duration_s,z_speech_rate_syl_per_s,z_articulation_rate_syl_per_s,z_number_of_pauses,z_pause_fraction,z_voiced_fraction,composite_raw,composite_z,cusum_tally,alarm_state` |
| 4 | `tail -n +2 scores.csv \| wc -l` | 98 (all rows; pagination ignored) |
| 5 | Same request with `$CLIN` | HTTP 403 `FORBIDDEN`; an `access.denied` audit row |
| 6 | Find the R09-20261021-01 line | Values equal the JSON row of TC-034-02 step 3 at full precision (e.g. `5.431965…`, `rings`) |

### TC-034-04 DS-07 baselines: 180 rows equal Exp_baselines; R09 loudness values

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/analytics/baselines?limit=500` as researcher | HTTP 200; `total` 180; 180 items |
| 2 | Item R09 / epoch 1 / `loudness_dbfs` | `device_code` "D09"; `n_sessions` 16; `first_session_id` "R09-20261001-01"; `frozen_after_session_id` "R09-20261016-01"; `median` -22.405; `mad` 1.45; `robust_spread` 2.14977 (±1e-6); `floor_applied` false |
| 3 | Compare every item with sheet Exp_baselines of the SRC-03 workbook (composite ↔ "COMPOSITE (raw signed mean of 7 z)") | All 180 rows match within 1e-6 on `median`, `mad`, `robust_spread`; `floor_applied` equal |
| 4 | `pytest tests/integration/api/test_scores.py::test_baselines -q` | Passes |

### TC-034-05 Baselines CSV header and rows equal JSON; clinician 403 for JSON and CSV

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s -D h.txt -o baselines.csv $API/analytics/baselines -H "Authorization: Bearer $RES" -H "Accept: text/csv"` | HTTP 200; `content-disposition` filename "echowell_baselines_2026-10-30.csv" |
| 2 | `head -1 baselines.csv` | `resident_code,epoch_number,device_code,feature_key,n_sessions,first_session_id,frozen_after_session_id,median,mad,robust_spread,floor_applied` |
| 3 | `tail -n +2 baselines.csv \| wc -l` | 180; each line equals the matching JSON item of TC-034-04 |
| 4 | `GET $API/analytics/baselines` as clinician (JSON) | HTTP 403 `FORBIDDEN` |
| 5 | Same with `Accept: text/csv` as clinician | HTTP 403 `FORBIDDEN` |

### TC-034-06 Each CSV export writes one `export.csv` audit row with `row_count`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Note `SELECT count(*) FROM audit_logs WHERE action='export.csv';` (= N) | N noted |
| 2 | Run TC-034-03 step 1 once | 200 |
| 3 | `SELECT actor_type, actor_id, entity_type, entity_id, details FROM audit_logs WHERE action='export.csv' ORDER BY id DESC LIMIT 1;` | Count N + 1; `actor_type` user; `actor_id` = researcher id; `entity_type` "route"; `entity_id` "/api/v1/scores"; `details.row_count` 98; `details.filters` {} |
| 4 | `curl ... "$API/scores?resident_code=R09" -H "Accept: text/csv"` as admin | One more row; `details.row_count` 14; `details.filters.resident_code` "R09" |
| 5 | Baselines CSV export (TC-034-05 step 1) | One more row; `entity_id` "/api/v1/analytics/baselines"; `row_count` 180 |
| 6 | A JSON request `GET /scores` | No new `export.csv` row |

### TC-034-07 Baseline row order within a resident-epoch: loudness_dbfs … mfcc4, then composite

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/analytics/baselines?resident_code=R09` as researcher | `total` 20 |
| 2 | List `feature_key` | loudness_dbfs, total_phrase_duration_s, speech_rate_syl_per_s, articulation_rate_syl_per_s, number_of_pauses, pause_fraction, voiced_fraction, mean_f0_hz, f0_variability_st, jitter_local_pct, shimmer_local_pct, hnr_db, cpps_db, alpha_ratio_db, hammarberg_index_db, mfcc1, mfcc2, mfcc3, mfcc4, composite |
| 3 | `GET $API/analytics/baselines?resident_code=R07` | 20 items, all `epoch_number` 2 and `device_code` "D07B", in the order of step 2 (epoch 1 on D07 had too few usable sessions to freeze a baseline) |

### TC-034-08 Scores JSON for every role; API key 401

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/scores?resident_code=R09` with each of `$ADMIN`, `$CLIN`, `$RES` | 200 each, identical bodies |
| 2 | `GET $API/scores -H "X-API-Key: $KEY"` and `GET $API/analytics/baselines -H "X-API-Key: $KEY"` | 401 `NOT_AUTHENTICATED` each |
| 3 | `GET $API/analytics/baselines` with `$ADMIN` | 200 |

### TC-034-09 Scores filters: `from` / `to`, `epoch`, R07 two epochs, `from` > `to` 422

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/scores?resident_code=R09&from=2026-10-21&to=2026-10-22` | `total` 2: R09-20261021-01, R09-20261022-01 |
| 2 | `GET $API/scores?resident_code=R07&epoch=2` | 2 rows (2026-10-29, 2026-10-30), `epoch_number` 2; `baseline_periods` one entry epoch 2, 2026-10-13..2026-10-28 |
| 3 | `GET $API/scores?resident_code=R07&epoch=1` | HTTP 200; `items` []; `total` 0; `baseline_periods` [] (epoch 1 never froze a baseline, so nothing was scored) |
| 4 | `GET $API/scores?from=2026-10-25&to=2026-10-20` | 422 `INVALID_QUERY_PARAMETER` |
| 5 | `GET $API/scores?limit=501` | 422 `INVALID_QUERY_PARAMETER` |
| 6 | `GET $API/scores` (no filter) | `total` 98; `limit` 50; 50 items |

### TC-034-10 CSV above 100,000 rows returns 413 (integration test)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/integration/api/test_scores.py::test_csv_row_limit -q` | Passes: with the row limit lowered below the fixture's row count, both the scores and the baselines CSV requests return 413 `PAYLOAD_TOO_LARGE` (the count is checked before streaming, so no partial body) |
| 2 | Code check: `grep -n "MAX_CSV_ROWS" backend/services/export_service.py` | `MAX_CSV_ROWS = 100_000` (limit of TRD 05 API-129) |

### TC-034-11 Exports and JSON contain study IDs only and no free text

| Step | Action | Expected Result |
|---|---|---|
| 1 | Inspect columns of `scores.csv` and `baselines.csv` | Identifiers only `session_id`, `resident_code`, `device_code`; no name, room, note or reason text column |
| 2 | Create a staff note on R09 with body "QA free text marker", then re-export scores CSV | `grep -c "QA free text marker" scores.csv` = 0 |
| 3 | Restore with `seed test_v0_1 --reset` | DS-07 state again |

### TC-034-12 Empty result: JSON empty arrays; CSV header only

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/scores?resident_code=R08` | HTTP 200; `items` []; `total` 0; `baseline_periods` [] |
| 2 | Same with `Accept: text/csv` as researcher | HTTP 200; file has only the header line |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/scores` JSON | 200 `ScoresResponse` with `meta`, `cusum_k`, `baseline_periods`, `items`, `total`, `limit`, `offset` |
| 2 | `GET /api/v1/analytics/baselines` JSON | 200 `BaselineRowList`; limit max 500 |
| 3 | `Accept: text/csv` (researcher, admin) | 200 `text/csv; charset=utf-8`, attachment filename with the as-of local date |
| 4 | OpenAPI | `curl -s $API/openapi.json \| jq '.paths["/api/v1/scores"].get.responses["200"].content \| keys'` lists `application/json` and `text/csv`; same for `/api/v1/analytics/baselines` |
| 5 | Errors | 403 clinician CSV / baselines; 404 unknown resident (scores); 413 > 100,000 rows; 422 invalid parameters |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT count(*) FROM scores;` | 98 = CSV data rows |
| 2 | `SELECT count(*) FROM baselines;` | 180 = baselines `total` |
| 3 | `SELECT cusum_tally, alarm_state FROM scores s JOIN processed_sessions p ON p.id=s.processed_session_id WHERE p.session_id='R09-20261021-01';` | 5.431965, rings |
| 4 | `SELECT median, mad, robust_spread, floor_applied FROM baselines b JOIN residents r ON r.id=b.resident_id WHERE r.resident_code='R09' AND feature_key='loudness_dbfs';` | -22.405, 1.45, 2.14977, false |
| 5 | `audit_logs` | One `export.csv` row per CSV export; none for JSON |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | `epoch` without `resident_code`; `epoch=0`; `from` > `to`; `limit=501` | 422 `INVALID_QUERY_PARAMETER` |
| 2 | Unknown `resident_code` R11 on scores | 404 `RESIDENT_NOT_FOUND` |
| 3 | Clinician CSV scores; clinician baselines JSON / CSV | 403 `FORBIDDEN` |
| 4 | API key on either endpoint | 401 |
| 5 | CSV > 100,000 rows | 413 `PAYLOAD_TOO_LARGE` |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-034-AC-01 | `?epoch=1` without `resident_code` 422 `INVALID_QUERY_PARAMETER`; `?resident_code=R11` 404 `RESIDENT_NOT_FOUND` | TC-034-01 |
| FEAT-034-AC-02 | R09: `total` 14, `cusum_k` 0.5, one baseline period (epoch 1, 2026-10-01..2026-10-16, R09-20261016-01, n 16); R09-20261021-01 5.431965 `rings`; R09-20261030-01 26.830256 `on` | TC-034-02 |
| FEAT-034-AC-03 | Researcher CSV: `text/csv; charset=utf-8`, filename `echowell_scores_2026-10-30.csv`, header = `ScoreRow` fields with 7 `z_*` columns, 98 data rows; clinician 403 | TC-034-03 |
| FEAT-034-AC-04 | Baselines `limit=500` as researcher: `total` 180, values = Exp_baselines within 1e-6; R09 loudness median -22.405, mad 1.45, robust_spread 2.14977, `floor_applied` false | TC-034-04 |
| FEAT-034-AC-05 | Baselines CSV header = `BaselineRow` fields, rows = JSON items; clinician 403 for JSON and CSV | TC-034-05 |
| FEAT-034-AC-06 | Each CSV export writes exactly one `export.csv` row with `row_count` = data rows | TC-034-06 |
| FEAT-034-AC-07 | Within a resident-epoch: loudness_dbfs … mfcc4, then `composite` | TC-034-07 |

## Test Data Requirements

- DS-07 (`seed test_v0_1`): 98 scored sessions, 180 baseline rows (9 resident-epochs with a frozen baseline × 20 rows: R01–R06, R09, R10 epoch 1 and R07 epoch 2; R08 and R07 epoch 1 have none); values from TRD 19 E-12 and SRC-03 Exp_scores / Exp_baselines.
- SRC-03 workbook `tests/fixtures/answer_key/EchoWell_pipeline_test_v0_1.xlsx` (read only for comparison).
- Synthetic note text "QA free text marker" for TC-034-11.
- Environment: `SEED_*` passwords and `SEED_INGEST_API_KEY` from the environment file.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-034-FR-01 (API-079, API-093; FR-242) | FEAT-034 | TC-034-01, TC-034-09 |
| FEAT-034-FR-02 (API-079, CUS-024, OAS-011; FR-242) | FEAT-034 | TC-034-02 |
| FEAT-034-FR-03 (API-079, CUS-024) | FEAT-034 | TC-034-02, TC-034-09 |
| FEAT-034-FR-04 (TRD 12 §4.6) | FEAT-034 | TC-034-08 |
| FEAT-034-FR-05 (API-088; FR-241) | FEAT-034 | TC-034-04, TC-034-07 |
| FEAT-034-FR-06 (API-129, OAS-018, TST-079; FR-244) | FEAT-034 | TC-034-03, TC-034-05 |
| FEAT-034-FR-07 (API-129) | FEAT-034 | TC-034-03, TC-034-10 |
| FEAT-034-FR-08 (API-129; TRD 12 §4.12) | FEAT-034 | TC-034-06 |
| FEAT-034-FR-09 (FR-245, NFR-050, DME-004) | FEAT-034 | TC-034-11 |
| TST-079 | FEAT-034 | TC-034-03, TC-034-05 |
| AC-API-04 / OAS-022 | FEAT-034 | TC-034-02 |
| AC-API-16 (CSV part) | FEAT-034 | TC-034-03 |
| OAS-023 | FEAT-034 | TC-034-04 |
| AC-SEC-09 | FEAT-034 | TC-034-06 |
| ANL-042 | FEAT-034 | TC-034-04 |
