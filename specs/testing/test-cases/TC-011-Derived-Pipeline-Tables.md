# FEAT-011 Derived pipeline tables

## Feature Description

FEAT-011 creates the tables that hold every result the pipeline derives from `raw_sessions` (TRD 20 §4.6.10–§4.6.16): `pipeline_runs`, `epochs`, `processed_sessions`, `day_ledger`, `baselines`, `scores` and `cusum_state`. Their CHECK constraints make it impossible to persist an invalid status/reason combination, a wrong late-arrival combination (D-57), a wrong ledger reason or an unknown baseline key; `epochs_current_uq` allows one open epoch per resident; `echowell_app` may only SELECT and INSERT `baselines`, so a frozen baseline cannot be changed; `scores.processed_session_id` cascades on delete. JSON columns (`counts`, `warnings`, `config_snapshot`, `scope`) are validated by Pydantic models before insert.

## Preconditions

- Local Docker Compose stack running and seeded: `cp .env.development.example .env && docker compose up --build -d`, then `docker compose exec backend python -m backend.cli seed test_v0_1` (pipeline run at as-of 2026-10-30 15:00 America/Chicago).
- Connection shorthands (inside the `db` container, which holds the `ECHOWELL_*_DB_PASSWORD` variables; no password typed):
  - `SU` = `docker compose exec db psql -U echowell -d echowell -v VERBOSITY=verbose -v ON_ERROR_ROLLBACK=on`
  - `APP` = `docker compose exec db sh -c 'PGPASSWORD=$ECHOWELL_APP_DB_PASSWORD psql -h 127.0.0.1 -U echowell_app_login -d echowell -v VERBOSITY=verbose -v ON_ERROR_ROLLBACK=on'`
- Every mutating case runs as `APP` inside `BEGIN; … ROLLBACK;`. `VERBOSITY=verbose` prints the SQLSTATE after `ERROR:`.
- Recipe NEW-RAW (fresh raw row so a new `processed_sessions` row has a unique `raw_session_id`): `SELECT string_agg(quote_ident(column_name), ', ' ORDER BY ordinal_position) AS cols FROM information_schema.columns WHERE table_schema='public' AND table_name='raw_sessions' AND column_name NOT IN ('id','arrival_seq','received_at') \gset` then `INSERT INTO raw_sessions (:cols) SELECT :cols FROM raw_sessions WHERE session_id='R01-20261001-01' ORDER BY arrival_seq LIMIT 1 RETURNING id AS new_raw \gset`.
- Recipe CLONE-PS(status): `CREATE TEMP TABLE p AS SELECT * FROM processed_sessions WHERE status = '<status>' ORDER BY timestamp_utc LIMIT 1; UPDATE p SET id = gen_random_uuid(), raw_session_id = :'new_raw', <overrides>; INSERT INTO processed_sessions SELECT * FROM p; DROP TABLE p;`
- Seeded totals (TRD 14 VC-G01): `processed_sessions` usable 267, set_aside 12, quarantined 2, duplicate 2; `day_ledger` missing_resident 17, missing_device_gap 2 (R02 and R03 on 2026-10-12, device D02).

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-011-01 | `set_aside` row inserts only when `reason_text` equals the joined reasons | High | Database |
| TC-011-02 | `quarantined` row requires `screen_detail` | High | Database |
| TC-011-03 | `duplicate` row with an epoch or with `late_arrival = true` fails | High | Negative |
| TC-011-04 | Ledger reason rules: wrong `missing_resident` reason fails; D02 gap row inserts | High | Database |
| TC-011-05 | Late `usable` row with NULL epoch, no ordinal and the late reason inserts | High | Database |
| TC-011-06 | 21st baseline row with an existing `feature_key`, or `feature_key = 'f0'`, fails | High | Negative |
| TC-011-07 | `scores` row without `z_voiced_fraction` or with `cusum_tally = -0.1` fails 23514 | High | Negative |
| TC-011-08 | App role cannot UPDATE/DELETE `baselines` but can DELETE `scores` | High | Security |
| TC-011-09 | Second open epoch for a resident fails 23505 | High | Negative |
| TC-011-10 | Seeded derived data satisfy the status totals and invariants | Medium | Database |
| TC-011-11 | `local_date` window, ordinal, `in_baseline` and `adjusted_features` rules | Medium | Negative |
| TC-011-12 | `pipeline_runs` CHECKs and the `counts` / `warnings` shapes | Medium | Database |
| TC-011-13 | `cusum_state` rules and `scores` FK cascade | Medium | Database |
| TC-011-14 | Uniqueness, provenance and baseline state per epoch | Medium | Database |

### TC-011-01 `set_aside` row inserts only when `reason_text` equals the joined reasons

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `BEGIN;` NEW-RAW; CLONE-PS(`set_aside`) with `reasons = ARRAY['quality flag poor','noise above limit'], reason_text = 'quality flag poor; noise above limit'`. | `INSERT 0 1`. |
| 2 | NEW-RAW; CLONE-PS(`set_aside`) with the same `reasons` and `reason_text = 'noise above limit'`. | `ERROR:  23514: … violates check constraint "processed_sessions_reason_text_ck"`. |
| 3 | NEW-RAW; CLONE-PS(`set_aside`) with `reasons = ARRAY['too quiet'], reason_text = 'too quiet'`. | `23514` on `processed_sessions_status_reason_ck` (reason not in the fixed three). |
| 4 | NEW-RAW; CLONE-PS(`set_aside`) with `reasons = '{}'::text[], reason_text = ''`. | `23514` on `processed_sessions_status_reason_ck` (1–3 reasons required). |
| 5 | `ROLLBACK;` | Nothing stored. |

### TC-011-02 `quarantined` row requires `screen_detail`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `BEGIN;` NEW-RAW; CLONE-PS(`quarantined`) with `reasons = ARRAY['possible other speaker (F0 z=5.12; composite features with \|z\|>=3: 3)'], reason_text = 'possible other speaker (F0 z=5.12; composite features with \|z\|>=3: 3)', screen_detail = 'F0 z=5.12'`. | `INSERT 0 1`. |
| 2 | Repeat with `screen_detail = NULL` (new raw row). | `23514` on `processed_sessions_screen_ck`. |
| 3 | Repeat with `reasons = ARRAY['other speaker'], reason_text = 'other speaker'` and a non-null `screen_detail`. | `23514` on `processed_sessions_status_reason_ck`. |
| 4 | `ROLLBACK;` | Nothing stored. |

### TC-011-03 `duplicate` row with an epoch or with `late_arrival = true` fails

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `SELECT session_id, epoch_id, late_arrival, reasons, adjusted_features IS NULL FROM processed_sessions WHERE status='duplicate';` | 2 rows; `epoch_id` NULL, `late_arrival` f, `reasons` `{"session_id already received"}`, `adjusted_features IS NULL` t. |
| 2 | `BEGIN;` NEW-RAW; CLONE-PS(`duplicate`) with `epoch_id = (SELECT id FROM epochs LIMIT 1)`. | `23514` on `processed_sessions_epoch_ck`. |
| 3 | NEW-RAW; CLONE-PS(`duplicate`) with `late_arrival = true`. | `23514` on `processed_sessions_epoch_ck`. |
| 4 | NEW-RAW; CLONE-PS(`duplicate`) with no override. | `INSERT 0 1` (control). `ROLLBACK;` |

### TC-011-04 Ledger reason rules: wrong `missing_resident` reason fails; D02 gap row inserts

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `SELECT r.resident_code, l.status, d.device_code, l.reason FROM day_ledger l JOIN residents r ON r.id=l.resident_id LEFT JOIN devices d ON d.id=l.device_id WHERE l.local_date = DATE '2026-10-12' AND r.resident_code IN ('R02','R03') ORDER BY 1;` | 2 rows: R02 and R03, `missing_device_gap`, `D02`, `all residents on shared device D02 have no record`. |
| 2 | `BEGIN; CREATE TEMP TABLE l AS SELECT * FROM day_ledger WHERE status='missing_resident' LIMIT 1; DELETE FROM day_ledger WHERE id = (SELECT id FROM l); UPDATE l SET reason = 'no record'; INSERT INTO day_ledger SELECT * FROM l;` | DELETE 1, then the INSERT fails `23514` on `day_ledger_reason_ck`. |
| 3 | `UPDATE l SET reason = 'no record received'; INSERT INTO day_ledger SELECT * FROM l;` | `INSERT 0 1`. |
| 4 | `DELETE FROM day_ledger WHERE local_date = DATE '2026-10-12' AND resident_id = (SELECT id FROM residents WHERE resident_code='R02') RETURNING pipeline_run_id AS run \gset` then `INSERT INTO day_ledger (resident_id, local_date, status, device_id, reason, pipeline_run_id) SELECT r.id, DATE '2026-10-12', 'missing_device_gap', d.id, 'all residents on shared device D02 have no record', :'run' FROM residents r, devices d WHERE r.resident_code='R02' AND d.device_code='D02';` | `DELETE 1`; `INSERT 0 1`. |
| 5 | Repeat the INSERT of step 4. | `23505` on `day_ledger_resident_date_uq`. |
| 6 | Insert the same row with `device_id = NULL` for R02 on 2026-10-13 (after deleting that day's row). | `23514` on `day_ledger_reason_ck` (gap needs a device). |
| 7 | `ROLLBACK;` | Seed unchanged. |

### TC-011-05 Late `usable` row with NULL epoch, no ordinal and the late reason inserts

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `BEGIN;` NEW-RAW; CLONE-PS(`usable`) with `late_arrival = true, epoch_id = NULL, baseline_ordinal = NULL, in_baseline = false, reasons = ARRAY['late arrival (not used for baseline or scores)'], reason_text = 'late arrival (not used for baseline or scores)'`. | `INSERT 0 1`. |
| 2 | Repeat with `baseline_ordinal = 1` (new raw row). | `23514` on `processed_sessions_ordinal_ck`. |
| 3 | Repeat with `in_baseline = true`, `baseline_ordinal = NULL`. | `23514` on `processed_sessions_in_baseline_ck`. |
| 4 | Late quarantined: CLONE-PS(`quarantined`) with `late_arrival = true, epoch_id = NULL, reasons = ARRAY[<the quarantine reason of TC-011-02>, 'late arrival (not used for baseline or scores)'], reason_text = <both joined by "; ">`. | `INSERT 0 1` (D-57 two-reason form). |
| 5 | Repeat step 1 with `late_arrival = false` and `epoch_id = NULL`. | `23514` on `processed_sessions_epoch_ck`. `ROLLBACK;` |

### TC-011-06 21st baseline row with an existing `feature_key`, or `feature_key = 'f0'`, fails

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `SELECT epoch_id, count(*) FROM baselines GROUP BY epoch_id;` | Every listed epoch has exactly `20` rows (19 features + `composite`). |
| 2 | `BEGIN; CREATE TEMP TABLE b AS SELECT * FROM baselines WHERE feature_key='composite' LIMIT 1; UPDATE b SET id = gen_random_uuid(); INSERT INTO baselines SELECT * FROM b;` | `23505` on `baselines_epoch_feature_uq`. |
| 3 | `UPDATE b SET feature_key = 'f0'; INSERT INTO baselines SELECT * FROM b;` | `23514` on `baselines_feature_key_ck`. |
| 4 | `UPDATE b SET feature_key = 'composite', mad = -0.1; INSERT INTO baselines SELECT * FROM b;` | `23514` on `baselines_spread_ck`. |
| 5 | `UPDATE b SET mad = 0, n_sessions = 0; INSERT INTO baselines SELECT * FROM b;` then `ROLLBACK;` | `23514` on `baselines_n_sessions_ck`. |

### TC-011-07 `scores` row without `z_voiced_fraction` or with `cusum_tally = -0.1` fails 23514

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `BEGIN; CREATE TEMP TABLE s AS SELECT * FROM scores LIMIT 1; UPDATE s SET id = gen_random_uuid(), z = z - 'z_voiced_fraction'; INSERT INTO scores SELECT * FROM s;` | `23514` on `scores_z_ck`. |
| 2 | `UPDATE s SET z = (SELECT z FROM scores LIMIT 1), cusum_tally = -0.1; INSERT INTO scores SELECT * FROM s;` | `23514` on `scores_cusum_ck`. |
| 3 | `UPDATE s SET cusum_tally = 0; INSERT INTO scores SELECT * FROM s;` then `ROLLBACK;` | `23505` on `scores_processed_session_uq` (one score per processed session). |
| 4 | `APP`: `SELECT count(*) FROM scores WHERE NOT (z ?& ARRAY['z_loudness_dbfs','z_total_phrase_duration_s','z_speech_rate_syl_per_s','z_articulation_rate_syl_per_s','z_number_of_pauses','z_pause_fraction','z_voiced_fraction']);` | `0`. |

### TC-011-08 App role cannot UPDATE/DELETE `baselines` but can DELETE `scores`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SU`: `SELECT has_table_privilege('echowell_app','baselines','UPDATE'), has_table_privilege('echowell_app','baselines','DELETE'), has_table_privilege('echowell_app','scores','DELETE');` | `f`, `f`, `t`. |
| 2 | `APP`: `BEGIN; UPDATE baselines SET median = median + 1 WHERE feature_key='composite';` | `ERROR:  42501: permission denied for table baselines`. |
| 3 | `APP`: `DELETE FROM baselines WHERE feature_key='composite';` then `ROLLBACK;` | `42501`. |
| 4 | `SU`: `SELECT t, has_table_privilege('echowell_app', t, 'DELETE') FROM unnest(ARRAY['epochs','processed_sessions','day_ledger','scores','cusum_state','pipeline_runs']) t;` | `t` for the first five (rebuildable), `f` for `pipeline_runs`. |
| 5 | Run `pytest -q tests/integration/db/test_grants.py`. | All tests pass. |

### TC-011-09 Second open epoch for a resident fails 23505

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `SELECT r.resident_code, count(*) FILTER (WHERE e.ended_at IS NULL) AS open, count(*) AS total FROM epochs e JOIN residents r ON r.id=e.resident_id GROUP BY 1 ORDER BY 1;` | Every resident has `open` = 1; R07 has `total` = 2 (device change on 2026-10-13); others `total` = 1. |
| 2 | `BEGIN; CREATE TEMP TABLE e AS SELECT * FROM epochs WHERE ended_at IS NULL AND resident_id = (SELECT id FROM residents WHERE resident_code='R01'); UPDATE e SET id = gen_random_uuid(), epoch_number = 99; INSERT INTO epochs SELECT * FROM e;` | `23505` on `epochs_current_uq`. |
| 3 | `UPDATE e SET epoch_number = 0; INSERT INTO epochs SELECT * FROM e;` | `23514` on `epochs_number_ck`. |
| 4 | `UPDATE e SET epoch_number = 1, ended_at = started_at + interval '1 day'; INSERT INTO epochs SELECT * FROM e;` then `ROLLBACK;` | `23505` on `epochs_resident_number_uq` (epoch 1 of R01 exists). |

### TC-011-10 Seeded derived data satisfy the status totals and invariants

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `SELECT status, count(*) FROM processed_sessions GROUP BY 1 ORDER BY 1;` | `usable` 267, `set_aside` 12, `quarantined` 2, `duplicate` 2 (sum 283 = `raw_sessions`). |
| 2 | `APP`: `SELECT status, count(*) FROM day_ledger GROUP BY 1 ORDER BY 1;` | `missing_resident` 17, `missing_device_gap` 2; `checked_in` = remaining resident-days (281). |
| 3 | `APP`: `SELECT count(*) FROM processed_sessions WHERE reason_text <> array_to_string(reasons, '; ');` | `0`. |
| 4 | `APP`: `SELECT DISTINCT status FROM processed_sessions;` | Only the four persisted values; never `pending_screen` (DME-006). |
| 5 | `APP`: `SELECT reasons FROM processed_sessions WHERE session_id IN ('R03-20261003-01','R03-20261007-01') ORDER BY session_id;` | `{"noise above limit"}` and `{"quality flag poor"}` (DS-07 set-aside examples). |

### TC-011-11 `local_date` window, ordinal, `in_baseline` and `adjusted_features` rules

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `BEGIN;` NEW-RAW; CLONE-PS(`usable`) with `local_date = (timestamp_utc AT TIME ZONE 'UTC')::date + 2`. | `23514` on `processed_sessions_local_date_ck`. |
| 2 | NEW-RAW; CLONE-PS(`usable`) with `baseline_ordinal = NULL` (not late). | `23514` on `processed_sessions_ordinal_ck`. |
| 3 | NEW-RAW; CLONE-PS(`set_aside`) with `in_baseline = true`. | `23514` on `processed_sessions_in_baseline_ck`. |
| 4 | NEW-RAW; CLONE-PS(`usable`) with `adjusted_features = adjusted_features - 'mfcc4'`. | `23514` on `processed_sessions_adjusted_ck`. |
| 5 | NEW-RAW; CLONE-PS(`usable`) with `adjusted_features = NULL`; then `ROLLBACK;` | `23514` on `processed_sessions_adjusted_ck`. |
| 6 | `APP`: `SELECT count(*) FROM processed_sessions WHERE local_date NOT BETWEEN (timestamp_utc AT TIME ZONE 'UTC')::date - 1 AND (timestamp_utc AT TIME ZONE 'UTC')::date + 1;` | `0`. |

### TC-011-12 `pipeline_runs` CHECKs and the `counts` / `warnings` shapes

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `SELECT trigger, status, config_profile, scope, finished_at IS NOT NULL AS finished, error_message FROM pipeline_runs ORDER BY started_at DESC LIMIT 1;` | Latest run: `status` `succeeded`, `config_profile` `test_v0_1`, `scope` `{"type": "all"}`, `finished` t, `error_message` NULL. |
| 2 | `APP`: `SELECT k FROM pipeline_runs p, jsonb_object_keys(p.counts) k WHERE p.id = (SELECT id FROM pipeline_runs ORDER BY started_at DESC LIMIT 1) ORDER BY k;` | Exactly `alerts_opened, arrivals, duplicate, excluded_after_as_of, late_arrival, missing_device_gap, missing_resident, quarantined, residents, scored, set_aside, usable` (plus `db_size_bytes` only on nightly runs). |
| 3 | `APP`: `SELECT counts->'arrivals', counts->'usable', counts->'set_aside', counts->'quarantined', counts->'duplicate' FROM pipeline_runs ORDER BY started_at DESC LIMIT 1;` | `283`, `267`, `12`, `2`, `2`. |
| 4 | `APP`: `SELECT DISTINCT jsonb_object_keys(w) FROM pipeline_runs p, jsonb_array_elements(p.warnings) w;` | Only `code`, `resident_code`, `session_id`, `detail` (or no row when there are no warnings). |
| 5 | `APP`: `BEGIN; CREATE TEMP TABLE r AS SELECT * FROM pipeline_runs ORDER BY started_at DESC LIMIT 1; UPDATE r SET id = gen_random_uuid(), status = 'running'; INSERT INTO pipeline_runs SELECT * FROM r;` | `23514` on `pipeline_runs_finished_ck` (running ⇔ no `finished_at`). |
| 6 | `UPDATE r SET status = 'failed'; INSERT INTO pipeline_runs SELECT * FROM r;` | `23514` on `pipeline_runs_error_ck` (failed ⇔ `error_message`). |
| 7 | `UPDATE r SET status = 'succeeded', config_profile = 'staging'; INSERT …;` then `UPDATE r SET config_profile = 'test_v0_1', scope = '{"type":"residents","resident_codes":[]}'; INSERT …;` then `ROLLBACK;` | `23514` on `pipeline_runs_profile_ck`; then `23514` on `pipeline_runs_scope_ck`. |
| 8 | Run `pytest -q tests/unit/backend/schemas/test_json_columns.py`. | Passes: the TRD 23 §4.5 examples are accepted; a `counts` object with a missing or extra key raises a validation error. |

### TC-011-13 `cusum_state` rules and `scores` FK cascade

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `SELECT count(*) FROM cusum_state; SELECT count(*) FROM epochs;` | Equal counts (one `cusum_state` row per epoch, `epoch_id` primary key). |
| 2 | `APP`: `BEGIN; CREATE TEMP TABLE c AS SELECT * FROM cusum_state LIMIT 1; DELETE FROM cusum_state WHERE epoch_id = (SELECT epoch_id FROM c); UPDATE c SET last_scored_session_id = NULL, current_tally = 1.0, alarm_on = false; INSERT INTO cusum_state SELECT * FROM c;` | `23514` on `cusum_state_scored_ck` (unscored state must have tally 0 and no alarm). |
| 3 | `UPDATE c SET last_scored_session_id = 'R01-20261030-01', current_tally = -1; INSERT INTO cusum_state SELECT * FROM c;` | `23514` on `cusum_state_tally_ck`. |
| 4 | `UPDATE c SET current_tally = 0; INSERT INTO cusum_state SELECT * FROM c;` then repeat the INSERT. | `INSERT 0 1`; then `23505` on `cusum_state_pkey`. `ROLLBACK;` |
| 5 | `SU`: `SELECT confdeltype FROM pg_constraint WHERE conname = 'scores_processed_session_id_fkey';` | `c` (ON DELETE CASCADE). |
| 6 | `APP`: `BEGIN; SELECT processed_session_id AS ps FROM scores LIMIT 1 \gset` then `DELETE FROM processed_sessions WHERE id = :'ps'; SELECT count(*) FROM scores WHERE processed_session_id = :'ps'; ROLLBACK;` | `DELETE 1`; count `0` (the score row was removed by the cascade). |

### TC-011-14 Uniqueness, provenance and baseline state per epoch

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `BEGIN; CREATE TEMP TABLE p AS SELECT * FROM processed_sessions LIMIT 1; UPDATE p SET id = gen_random_uuid(); INSERT INTO processed_sessions SELECT * FROM p; ROLLBACK;` | `23505` on `processed_sessions_raw_session_uq`. |
| 2 | `APP`: `SELECT count(*) FROM processed_sessions WHERE pipeline_run_id IS NULL UNION ALL SELECT count(*) FROM epochs WHERE pipeline_run_id IS NULL UNION ALL SELECT count(*) FROM scores WHERE pipeline_run_id IS NULL;` | `0`, `0`, `0` (every derived row names the run that wrote it). |
| 3 | `APP`: `SELECT r.resident_code, e.epoch_number, count(b.id) FROM epochs e JOIN residents r ON r.id=e.resident_id LEFT JOIN baselines b ON b.epoch_id=e.id GROUP BY 1,2 ORDER BY 1,2;` | Each epoch has either 0 baseline rows (not started or forming) or exactly 20 (frozen); never a number in between. |
| 4 | `APP`: `SELECT trigger_name FROM information_schema.triggers WHERE event_object_table IN ('pipeline_runs','epochs','cusum_state') ORDER BY 1;` | `cusum_state_set_updated_at`, `epochs_set_updated_at`, `pipeline_runs_set_updated_at`. |
| 5 | Run `pytest -q tests/integration/test_schema_behaviour.py -k "pgs_04 or pgs_05 or pgs_06 or pgs_07 or late_usable or open_epoch"`. | All selected tests pass. |

## API Validation

Not applicable: FEAT-011 exposes no endpoint; read APIs over these tables are delivered by later features (FEAT-027 onward).

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | Status totals (TC-011-10) | usable 267, set_aside 12, quarantined 2, duplicate 2 |
| 2 | Ledger totals (TC-011-10) | missing_resident 17, missing_device_gap 2 |
| 3 | One open epoch per resident (TC-011-09) | `epochs_current_uq` holds; R07 has 2 epochs |
| 4 | Baselines per epoch (TC-011-06, TC-011-14) | 0 or 20 rows |
| 5 | `baselines` privileges (TC-011-08) | App: SELECT, INSERT only |
| 6 | `scores_processed_session_id_fkey` (TC-011-13) | `confdeltype = 'c'` |
| 7 | Latest `pipeline_runs.counts` keys (TC-011-12) | The 12 TRD 23 §4.5 keys |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | `reason_text` not equal to joined reasons (TC-011-01) | 23514 |
| 2 | Quarantined without `screen_detail` (TC-011-02) | 23514 |
| 3 | Duplicate with epoch / late flag (TC-011-03) | 23514 |
| 4 | `missing_resident` with reason `no record` (TC-011-04) | 23514 |
| 5 | Duplicate baseline key / `f0` (TC-011-06) | 23505 / 23514 |
| 6 | Score without `z_voiced_fraction` / negative tally (TC-011-07) | 23514 |
| 7 | UPDATE / DELETE on `baselines` as app (TC-011-08) | 42501 |
| 8 | Second open epoch (TC-011-09) | 23505 |
| 9 | Running run with `finished_at`, failed run without message (TC-011-12) | 23514 |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-011-AC-01 | `set_aside` with reasons {quality flag poor, noise above limit} and matching `reason_text` inserts; with `reason_text` `noise above limit` → 23514. | TC-011-01 |
| FEAT-011-AC-02 | `quarantined` with the "possible other speaker (F0 z=5.12; composite features with \|z\|>=3: 3)" reason and non-null `screen_detail` inserts; NULL `screen_detail` fails. | TC-011-02 |
| FEAT-011-AC-03 | `duplicate` with non-null `epoch_id` fails; `duplicate` with `late_arrival = true` fails. | TC-011-03 |
| FEAT-011-AC-04 | `missing_resident` with reason `no record` fails; R02 2026-10-12 `missing_device_gap` with D02 and the D02 reason inserts. | TC-011-04 |
| FEAT-011-AC-05 | Late `usable` with NULL `epoch_id`, no `baseline_ordinal`, `in_baseline = false` and the late reason inserts. | TC-011-05 |
| FEAT-011-AC-06 | 21st baseline row with an existing `feature_key`, or `feature_key = 'f0'`, fails. | TC-011-06 |
| FEAT-011-AC-07 | `scores` without `z_voiced_fraction` or with `cusum_tally = -0.1` → 23514. | TC-011-07 |
| FEAT-011-AC-08 | App UPDATE and DELETE on `baselines` false; DELETE on `scores` true. | TC-011-08 |
| FEAT-011-AC-09 | Second `epochs` row with `ended_at IS NULL` for the same resident → 23505. | TC-011-09 |

## Test Data Requirements

- `test_v0_1` seed with its pipeline run (DS-01 input, as-of 2026-10-30 15:00 America/Chicago); totals of TRD 14 VC-G01; DS-07 rows `R03-20261003-01` and `R03-20261007-01`; the D02 shared-device gap of 2026-10-12 (R02, R03).
- Template rows chosen by status from the seed; fresh raw rows cloned from `R01-20261001-01`.
- All mutations as `echowell_app_login` inside `BEGIN … ROLLBACK`.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-011-FR-01 (PGS-006) | FEAT-011 | TC-011-14 |
| FEAT-011-FR-02 (PGS-012, D-57) | FEAT-011 | TC-011-01, TC-011-02, TC-011-03, TC-011-05, TC-011-11 |
| FEAT-011-FR-03 (PGS-013) | FEAT-011 | TC-011-11 |
| FEAT-011-FR-04 (PGS-033) | FEAT-011 | TC-011-03, TC-011-11 |
| FEAT-011-FR-05 (PGS-014) | FEAT-011 | TC-011-04 |
| FEAT-011-FR-06 (PGS-030, FR-051) | FEAT-011 | TC-011-09 |
| FEAT-011-FR-07 (PGS-031, FR-086) | FEAT-011 | TC-011-06 |
| FEAT-011-FR-08 (DB-016, PGS-021) | FEAT-011 | TC-011-08 |
| FEAT-011-FR-09 (PGS-032, PGS-010, FR-094) | FEAT-011 | TC-011-07, TC-011-13 |
| FEAT-011-FR-10 (FR-105, PGS-007) | FEAT-011 | TC-011-13 |
| FEAT-011-FR-11 (DB-020) | FEAT-011 | TC-011-12 |
| FEAT-011-FR-12 (DME-013, DB-020) | FEAT-011 | TC-011-12 |
| FEAT-011-FR-13 (DME-014) | FEAT-011 | TC-011-12 (step 8, Pydantic models), TC-011-07 (`double precision` columns) |
| FEAT-011-FR-14 (DME-006) | FEAT-011 | TC-011-10 |
| FEAT-011-FR-15 (DB-006, TRD 20 §4.10) | FEAT-011 | TC-011-14 |
| FEAT-011-FR-16 (DME-010) | FEAT-011 | TC-011-14 |
| AC-PGS-04, AC-PGS-05, AC-PGS-06, AC-PGS-07 | FEAT-011 | TC-011-01, TC-011-02, TC-011-03, TC-011-04 |
| AC-PGS-13 | FEAT-011 | TC-011-13 |
| TST-041 (baselines grants) | FEAT-011 | TC-011-08 |
| TST-042 (uniqueness) | FEAT-011 | TC-011-06, TC-011-09, TC-011-04, TC-011-14 |
