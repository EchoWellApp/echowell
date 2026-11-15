# FEAT-012 Alert, review, note, data-alert, reference-range, audit and ground-truth tables

## Feature Description

FEAT-012 creates the tables that carry alarm events and the human response to them (`alerts`, `alert_reviews`, `staff_notes`), rule-based data-quality flags (`data_alerts`), facility reference ranges for the new-admission arm (`facility_reference_ranges`), the append-only `audit_logs`, and the test-only `evaluation_ground_truth` (TRD 20 §4.6.17–§4.6.21, §4.6.23, §4.6.24). Constraints and grants guarantee one non-closed alert per epoch, natural keys that keep human-entered data across rebuilds (D-45), append-only reviews, notes and audit entries (trigger `reject_mutation()` on `audit_logs`, SELECT/INSERT-only grants), and that the application role cannot read the answer key (D-38).

## Preconditions

- Local Docker Compose stack running and seeded: `cp .env.development.example .env && docker compose up --build -d`, then `docker compose exec backend python -m backend.cli seed test_v0_1`.
- For TC-012-03 step 4 the answer-key loader has been run once: `docker compose exec backend python database/seeds/load_evaluation_ground_truth.py tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv` (test profile only; refuses in production).
- Sign in once at `POST /api/v1/auth/login` (any seeded user) so `audit_logs` holds at least one row.
- Connection shorthands (inside the `db` container, which holds the `ECHOWELL_*_DB_PASSWORD` variables; no password typed):
  - `SU` = `docker compose exec db psql -U echowell -d echowell -v VERBOSITY=verbose -v ON_ERROR_ROLLBACK=on`
  - `APP` = `docker compose exec db sh -c 'PGPASSWORD=$ECHOWELL_APP_DB_PASSWORD psql -h 127.0.0.1 -U echowell_app_login -d echowell -v VERBOSITY=verbose -v ON_ERROR_ROLLBACK=on'`
  - `RO` / `OWNER` = the same with `ECHOWELL_READONLY_DB_PASSWORD` / `echowell_readonly_login`, or `ECHOWELL_MIGRATOR_DB_PASSWORD` / `echowell_migrator_login` followed by `SET ROLE echowell_migrator;`.
- Every mutating case runs inside `BEGIN; … ROLLBACK;` (this matters most in TC-012-02, which really deletes audit rows before the rollback). `VERBOSITY=verbose` prints the SQLSTATE after `ERROR:`.
- Helper values (run inside the transaction as needed): `SELECT id AS run FROM pipeline_runs ORDER BY started_at DESC LIMIT 1 \gset`, `SELECT id AS clin FROM users WHERE email='clinician@example.com' \gset`, `SELECT id AS d02 FROM devices WHERE device_code='D02' \gset`, `SELECT id AS r01 FROM residents WHERE resident_code='R01' \gset`.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-012-01 | `audit_logs` UPDATE/DELETE fail for app (42501) and owner (`EW001`) | High | Security |
| TC-012-02 | Migrator with `echowell.allow_purge = 'on'` can DELETE `audit_logs`; UPDATE `raw_sessions` still fails | High | Security |
| TC-012-03 | App cannot read `evaluation_ground_truth` or `SET ROLE echowell_readonly`; read-only role can | High | Security |
| TC-012-04 | Second open `device_silent` for D02 fails 23505; missing `pipeline_run_id` fails 23514; app cannot DELETE alerts | High | Negative |
| TC-012-05 | Second non-closed alert per epoch fails 23505; closed + new open alert succeed | High | Database |
| TC-012-06 | `snoozed_until` without `snoozed_by` fails 23514; acknowledgement and closure pairs | High | Negative |
| TC-012-07 | Reviews and notes are append-only; two notes superseding the same note fail 23505 | High | Security |
| TC-012-08 | `audit_logs.action` accepts `auth.logout`, `auth.login.succeeded`; rejects `Auth.Login`, `login` | High | Database |
| TC-012-09 | No reference to `evaluation_ground_truth` in `analytics/` or `backend/repositories/` | High | Security |
| TC-012-10 | `alert_reviews` explanation, note and outcome rules | Medium | Negative |
| TC-012-11 | `data_alerts` subject, run and resolution rules | Medium | Negative |
| TC-012-12 | `facility_reference_ranges` and `evaluation_ground_truth` CHECKs | Medium | Negative |
| TC-012-13 | Audit row commits or rolls back with the audited change | Medium | Database |
| TC-012-14 | Grant matrix, triggers and the absence of review columns on `scores` / `cusum_state` | Medium | Database |

### TC-012-01 `audit_logs` UPDATE/DELETE fail for app (42501) and owner (`EW001`)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `SELECT count(*), max(id) FROM audit_logs;` | N ≥ 1 rows; note N and max id M. |
| 2 | `APP`: `BEGIN; UPDATE audit_logs SET action = 'auth.logout' WHERE id = (SELECT max(id) FROM audit_logs);` | `ERROR:  42501: permission denied for table audit_logs`. |
| 3 | `APP` (same transaction): `DELETE FROM audit_logs;` then `TRUNCATE audit_logs;` then `ROLLBACK;` | `42501` for both. |
| 4 | `OWNER`: `BEGIN; UPDATE audit_logs SET action = 'auth.logout' WHERE id = (SELECT max(id) FROM audit_logs);` | `ERROR:  EW001: table audit_logs is append-only: UPDATE is not allowed`. |
| 5 | `OWNER` (same transaction): `DELETE FROM audit_logs WHERE id = (SELECT max(id) FROM audit_logs);` then `TRUNCATE audit_logs;` then `ROLLBACK;` | `EW001 … DELETE is not allowed`; `EW001 … TRUNCATE is not allowed`. |
| 6 | Repeat step 1. | Still N rows, max id M. |

### TC-012-02 Migrator with `echowell.allow_purge = 'on'` can DELETE `audit_logs`; UPDATE `raw_sessions` still fails

| Step | Action | Expected Result |
|---|---|---|
| 1 | `OWNER`: `BEGIN; SET LOCAL echowell.allow_purge = 'on'; DELETE FROM audit_logs WHERE id = (SELECT max(id) FROM audit_logs);` | `DELETE 1` (no error). |
| 2 | Same transaction: `UPDATE raw_sessions SET phrase_id = 'x' WHERE session_id = 'R01-20261001-01';` | `EW001: table raw_sessions is append-only: UPDATE is not allowed`. |
| 3 | Same transaction: `UPDATE audit_logs SET action = 'auth.logout' WHERE id = (SELECT min(id) FROM audit_logs);` | `EW001 … UPDATE is not allowed` (purge never allows UPDATE). |
| 4 | `ROLLBACK;` then `APP`: `SELECT count(*), max(id) FROM audit_logs;` | N and M of TC-012-01 (the deleted row is back after the rollback). |
| 5 | `APP`: `BEGIN; SET LOCAL echowell.allow_purge = 'on'; DELETE FROM audit_logs; ROLLBACK;` | `42501` (the setting does not help the app role). |

### TC-012-03 App cannot read `evaluation_ground_truth` or `SET ROLE echowell_readonly`; read-only role can

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `SELECT count(*) FROM evaluation_ground_truth;` | `ERROR:  42501: permission denied for table evaluation_ground_truth`. |
| 2 | `APP`: `SET ROLE echowell_readonly;` | `ERROR:  42501: permission denied to set role "echowell_readonly"`. |
| 3 | `RO`: `SELECT count(*) FROM evaluation_ground_truth;` | Succeeds; `10` after the loader of Preconditions (`0` if it was not run). |
| 4 | `RO`: `SELECT resident_code, planted_change, true_onset_date FROM evaluation_ground_truth WHERE resident_code IN ('R01','R02');` | `R01` `None` NULL; `R02` `None` NULL. |
| 5 | `RO`: `BEGIN; INSERT INTO evaluation_ground_truth (resident_code, planted_change, source_file) VALUES ('R11','None','qa.csv'); ROLLBACK;` | `42501` (read-only role cannot write). |
| 6 | `SU`: `SELECT has_table_privilege('echowell_app','evaluation_ground_truth','SELECT'), has_table_privilege('echowell_readonly','evaluation_ground_truth','SELECT');` | `f`, `t`. |

### TC-012-04 Second open `device_silent` for D02 fails 23505; missing `pipeline_run_id` fails 23514; app cannot DELETE alerts

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `SELECT count(*) FROM data_alerts WHERE kind='device_silent' AND status='open' AND device_id = (SELECT id FROM devices WHERE device_code='D02');` | 0 or 1. |
| 2 | `APP`: `BEGIN;` helpers; if step 1 returned 0, insert one: `INSERT INTO data_alerts (kind, device_id, title, first_detected_at, last_detected_at, pipeline_run_id) VALUES ('device_silent', :'d02', 'D02 · device silent', now(), now(), :'run');` | `INSERT 0 1` (or skipped when one already exists). |
| 3 | Insert the same row again. | `ERROR:  23505: duplicate key value violates unique constraint "data_alerts_open_subject_uq"`. |
| 4 | Insert `('device_silent', :'d02', 'D02 · device silent', now(), now(), NULL)` with status `'resolved'` and `resolved_at = now()` (so the unique index does not apply). | `23514` on `data_alerts_run_ck` (rule kinds need `pipeline_run_id`). |
| 5 | `DELETE FROM alerts;` | `42501: permission denied for table alerts`. |
| 6 | `ROLLBACK;` | Seed unchanged. |

### TC-012-05 Second non-closed alert per epoch fails 23505; closed + new open alert succeed

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `SELECT a.id, r.resident_code, a.status, a.session_id FROM alerts a JOIN residents r ON r.id=a.resident_id ORDER BY triggered_at;` | Lists the seeded alerts; at least one with `status` `open` or `acknowledged`. Pick one as A. |
| 2 | `BEGIN; CREATE TEMP TABLE a AS SELECT * FROM alerts WHERE id = '<A>'; UPDATE a SET id = gen_random_uuid(), session_id = session_id || '-qa', status = 'open', acknowledged_by = NULL, acknowledged_at = NULL; INSERT INTO alerts SELECT * FROM a;` | `23505` on `alerts_one_active_per_epoch_uq`. |
| 3 | `UPDATE alerts SET status = 'closed', closed_reason = 'admin', closed_at = now() WHERE id = '<A>';` | `UPDATE 1`. |
| 4 | `INSERT INTO alerts SELECT * FROM a;` | `INSERT 0 1` (closed + new open alert for the same epoch). |
| 5 | `UPDATE a SET id = gen_random_uuid(); INSERT INTO alerts SELECT * FROM a;` | `23505` on `alerts_epoch_session_uq` (same `(epoch_id, session_id)`). |
| 6 | `ROLLBACK;` | Seed unchanged. |
| 7 | `APP`: `SELECT epoch_id, count(*) FROM alerts WHERE status <> 'closed' GROUP BY 1 HAVING count(*) > 1;` | 0 rows. |

### TC-012-06 `snoozed_until` without `snoozed_by` fails 23514; acknowledgement and closure pairs

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `BEGIN; UPDATE alerts SET snoozed_until = now() + interval '24 hours' WHERE id = '<A>';` | `23514` on `alerts_snooze_ck`. |
| 2 | `UPDATE alerts SET snoozed_until = now() + interval '24 hours', snoozed_by = :'clin' WHERE id = '<A>';` | `UPDATE 1`. |
| 3 | `UPDATE alerts SET acknowledged_by = :'clin', acknowledged_at = NULL WHERE id = '<A>';` | `23514` on `alerts_ack_ck`. |
| 4 | `UPDATE alerts SET status = 'acknowledged', acknowledged_by = NULL, acknowledged_at = NULL WHERE id = '<A>';` | `23514` on `alerts_ack_status_ck`. |
| 5 | `UPDATE alerts SET status = 'closed', closed_reason = NULL, closed_at = now() WHERE id = '<A>';` | `23514` on `alerts_closed_ck`. |
| 6 | `UPDATE alerts SET status = 'closed', closed_reason = 'resolved', closed_at = now() WHERE id = '<A>';` | `23514` on `alerts_closed_reason_ck` (allowed: `epoch ended`, `admin`, `superseded by rebuild`). |
| 7 | `UPDATE alerts SET cusum_value = -1 WHERE id = '<A>';` then `ROLLBACK;` | `23514` on `alerts_cusum_ck`. |

### TC-012-07 Reviews and notes are append-only; two notes superseding the same note fail 23505

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `BEGIN; INSERT INTO alert_reviews (alert_id, reviewer_user_id, outcome, explanations, note) VALUES ('<A>', :'clin', 'known_cause', ARRAY['cold_cough_sore_throat'], 'QA synthetic note') RETURNING id AS rev \gset` | `INSERT 0 1`. |
| 2 | `UPDATE alert_reviews SET outcome = 'no_concern' WHERE id = :'rev';` | `42501: permission denied for table alert_reviews`. |
| 3 | `DELETE FROM alert_reviews WHERE id = :'rev';` | `42501`. |
| 4 | `INSERT INTO staff_notes (resident_id, author_user_id, note_type, body) VALUES (:'r01', :'clin', 'observation', 'QA synthetic note 1') RETURNING id AS n1 \gset` | `INSERT 0 1`. |
| 5 | `UPDATE staff_notes SET body = 'changed' WHERE id = :'n1';` and `DELETE FROM staff_notes WHERE id = :'n1';` | `42501` for both. |
| 6 | Insert note 2 with `supersedes_id = :'n1'`, then note 3 with `supersedes_id = :'n1'`. | Note 2 `INSERT 0 1`; note 3 `23505` on `staff_notes_supersedes_uq`. |
| 7 | `INSERT INTO staff_notes (id, resident_id, author_user_id, note_type, body, supersedes_id) VALUES ('00000000-0000-4000-8000-000000000001', :'r01', :'clin', 'follow_up', 'QA', '00000000-0000-4000-8000-000000000001');` | `23514` on `staff_notes_not_self_ck`. |
| 8 | Insert a note with `body = '   '`, then one with `body = repeat('x', 2001)`; then `ROLLBACK;` | `23514` on `staff_notes_body_ck` for both. |

### TC-012-08 `audit_logs.action` accepts `auth.logout`, `auth.login.succeeded`; rejects `Auth.Login`, `login`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `BEGIN; INSERT INTO audit_logs (actor_type, action) VALUES ('system', 'auth.logout');` | `INSERT 0 1`. |
| 2 | `INSERT INTO audit_logs (actor_type, action) VALUES ('system', 'auth.login.succeeded');` | `INSERT 0 1`. |
| 3 | `INSERT INTO audit_logs (actor_type, action) VALUES ('system', 'Auth.Login');` | `23514` on `audit_logs_action_ck`. |
| 4 | `INSERT INTO audit_logs (actor_type, action) VALUES ('system', 'login');` | `23514` on `audit_logs_action_ck`. |
| 5 | `INSERT INTO audit_logs (actor_type, action) VALUES ('user', 'auth.logout');` (no `actor_id`). | `23514` on `audit_logs_actor_ck`. |
| 6 | `INSERT INTO audit_logs (actor_type, action, details) VALUES ('system', 'auth.logout', '[]');` then `ROLLBACK;` | `23514` on `audit_logs_details_ck`. |
| 7 | `APP`: `SELECT DISTINCT action FROM audit_logs ORDER BY 1;` | Every stored action matches `^[a-z_]+(\.[a-z_]+){1,2}$` (for example `auth.login.succeeded`). |

### TC-012-09 No reference to `evaluation_ground_truth` in `analytics/` or `backend/repositories/`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -rn "evaluation_ground_truth" analytics; echo "exit=$?"`. | No output; `exit=1`. |
| 2 | Run `grep -rn "evaluation_ground_truth\|EvaluationGroundTruth" analytics backend/repositories; echo "exit=$?"`. | No output; `exit=1`. |
| 3 | Run `grep -n "evaluation_ground_truth" backend/cli.py; echo "exit=$?"`. | `exit=1` (the seed CLI never references the answer key, TRD 20 §4.12). |
| 4 | Run `pytest -q tests/unit/backend/test_ground_truth_boundary.py`. | Passes. |

### TC-012-10 `alert_reviews` explanation, note and outcome rules

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `BEGIN;` insert a review (as TC-012-07 step 1) with `explanations = ARRAY['Cold_Cough']`. | `23514` on `alert_reviews_explanations_ck`. |
| 2 | Same with `explanations = (SELECT array_agg('code' \|\| g) FROM generate_series(1,21) g)`. | `23514` on `alert_reviews_explanations_ck` (more than 20). |
| 3 | Same with `note = ''`; then `note = repeat('x', 2001)`. | `23514` on `alert_reviews_note_ck` for both. |
| 4 | Same with `outcome = 'resolved'`. | `ERROR:  22P02: invalid input value for enum review_outcome: "resolved"`. |
| 5 | Same with `explanations = '{}'`, `note = NULL`, `outcome = 'data_problem'`; then `ROLLBACK;` | `INSERT 0 1`. |

### TC-012-11 `data_alerts` subject, run and resolution rules

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `BEGIN;` insert `('device_silent', resident_id = :'r01', device_id = :'d02', …, pipeline_run_id = :'run')`. | `23514` on `data_alerts_subject_ck` (device kind must not name a resident). |
| 2 | Insert `kind = 'high_set_aside'` with `device_id = :'d02'` and no resident. | `23514` on `data_alerts_subject_ck`. |
| 3 | Insert `kind = 'review_flagged_data_problem'` with `resident_id = :'r01'`, `alert_review_id = :'rev'` (a review inserted as in TC-012-07) and `pipeline_run_id = :'run'`. | `23514` on `data_alerts_run_ck` (review-flagged rows have no run). |
| 4 | Same with `pipeline_run_id = NULL`. | `INSERT 0 1`. |
| 5 | Insert a `baseline_stalled` row for R01 with `status = 'resolved'` and `resolved_at = NULL`. | `23514` on `data_alerts_resolved_ck`. |
| 6 | Insert a `baseline_stalled` row for R01 with `last_detected_at = first_detected_at - interval '1 day'`; then `ROLLBACK;` | `23514` on `data_alerts_detected_ck`. |
| 7 | `APP`: `SELECT column_name, data_type FROM information_schema.columns WHERE table_name='data_alerts' AND column_name='days';` | `days`, `ARRAY` (`date[]`, migration 0004). |

### TC-012-12 `facility_reference_ranges` and `evaluation_ground_truth` CHECKs

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `BEGIN; INSERT INTO facility_reference_ranges (facility_id, feature_key, sex, low, high, method, n_residents, computed_at, pipeline_run_id) SELECT id, 'mean_f0_hz', 'F', 150, 250, 'p10-p90 of longitudinal residents', 5, now(), :'run' FROM facilities;` | `INSERT 0 1`. |
| 2 | Repeat step 1 unchanged. | `23505` on `facility_reference_ranges_uq`. |
| 3 | Repeat with `sex = NULL` twice. | First `INSERT 0 1`; second `23505` (`NULLS NOT DISTINCT`). |
| 4 | Repeat with `feature_key = 'composite'`; then `low = 300, high = 250`; then `sex = 'X'`; then `n_residents = 0`; then `method = ''`. | `23514` on `facility_reference_ranges_feature_ck`, `_bounds_ck`, `_sex_ck`, `_n_ck`, `_method_ck` respectively. `ROLLBACK;` |
| 5 | `OWNER`: `BEGIN; INSERT INTO evaluation_ground_truth (resident_code, planted_change, true_onset_date, source_file) VALUES ('R11', 'None', DATE '2026-10-15', 'qa.csv');` | `23514` on `evaluation_ground_truth_onset_ck` (`None` ⇔ NULL onset). |
| 6 | Same with `planted_change = 'gradual drift'` and `true_onset_date = NULL`. | `23514` on `evaluation_ground_truth_onset_ck`. |
| 7 | If the loader was run: insert `('R01', 'None', NULL, 'qa.csv')`; then `ROLLBACK;` | `23505` on `evaluation_ground_truth_resident_code_uq`. |

### TC-012-13 Audit row commits or rolls back with the audited change

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `pytest -q tests/integration/db/test_audit_writer.py`. | Passes, including the forced-rollback case: neither the change nor its audit row remains (DB-011). |
| 2 | `APP`: `BEGIN; UPDATE alerts SET snoozed_until = now() + interval '24 hours', snoozed_by = :'clin' WHERE id = '<A>'; INSERT INTO audit_logs (actor_type, actor_id, action, entity_type, entity_id) VALUES ('user', :'clin', 'alert.snooze', 'alert', '<A>'); ROLLBACK;` then `SELECT snoozed_until IS NULL FROM alerts WHERE id = '<A>'; SELECT count(*) FROM audit_logs WHERE entity_id = '<A>' AND action = 'alert.snooze';` | `t` (if A was not snoozed before) and `0`: change and audit row rolled back together. |

### TC-012-14 Grant matrix, triggers and the absence of review columns on `scores` / `cusum_state`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SU`: `SELECT t, has_table_privilege('echowell_app',t,'INSERT') ins, has_table_privilege('echowell_app',t,'UPDATE') upd, has_table_privilege('echowell_app',t,'DELETE') del FROM unnest(ARRAY['alerts','alert_reviews','data_alerts','staff_notes','facility_reference_ranges','audit_logs']) t ORDER BY 1;` | `alert_reviews` t f f; `alerts` t t f; `audit_logs` t f f; `data_alerts` t t f; `facility_reference_ranges` t t t; `staff_notes` t f f. |
| 2 | `SU`: `SELECT has_sequence_privilege('echowell_app','audit_logs_id_seq','USAGE');` | `t`. |
| 3 | `SU`: `SELECT tgname FROM pg_trigger WHERE NOT tgisinternal AND tgrelid IN ('audit_logs'::regclass,'alerts'::regclass,'data_alerts'::regclass) ORDER BY 1;` | `alerts_set_updated_at`, `audit_logs_no_truncate`, `audit_logs_no_update_delete`, `data_alerts_set_updated_at`. |
| 4 | `SU`: `SELECT indexname FROM pg_indexes WHERE indexname IN ('alerts_one_active_per_epoch_uq','data_alerts_open_subject_uq');` | Both indexes exist. |
| 5 | `APP`: `SELECT table_name, column_name FROM information_schema.columns WHERE table_name IN ('scores','cusum_state') AND column_name ~ '(review\|snooze\|acknowledg)';` | 0 rows (review and snooze state lives only on `alerts`, D-37). |
| 6 | Run `pytest -q tests/integration/test_schema_behaviour.py -k "pgs_03 or pgs_09 or pgs_14 or pgs_15 or non_closed or snooze or append_only or audit_action"`. | All selected tests pass. |

## API Validation

Not applicable: FEAT-012 exposes no endpoint; the alert, review, snooze, note and data-alert endpoints are delivered by later features.

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | Grant matrix (TC-012-14) | Reviews, notes, audit: SELECT/INSERT only; alerts, data alerts: no DELETE; ground truth: no app privilege |
| 2 | `audit_logs` triggers (TC-012-14) | `audit_logs_no_update_delete`, `audit_logs_no_truncate` |
| 3 | `SELECT epoch_id FROM alerts WHERE status <> 'closed' GROUP BY 1 HAVING count(*) > 1;` | 0 rows |
| 4 | `SELECT kind, resident_id, device_id FROM data_alerts WHERE status='open' AND kind <> 'review_flagged_data_problem' GROUP BY 1,2,3 HAVING count(*) > 1;` | 0 rows |
| 5 | `RO`: `SELECT count(*) FROM evaluation_ground_truth;` | 10 after the loader |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | UPDATE / DELETE `audit_logs` as app / owner (TC-012-01) | 42501 / `EW001` |
| 2 | UPDATE `raw_sessions` with purge setting (TC-012-02) | `EW001` |
| 3 | App SELECT `evaluation_ground_truth`; `SET ROLE echowell_readonly` (TC-012-03) | 42501 |
| 4 | Second open `device_silent` for D02 (TC-012-04) | 23505 |
| 5 | `DELETE FROM alerts` as app (TC-012-04) | 42501 |
| 6 | Second non-closed alert per epoch (TC-012-05) | 23505 |
| 7 | Snooze without `snoozed_by` (TC-012-06) | 23514 |
| 8 | UPDATE/DELETE reviews and notes; duplicate `supersedes_id` (TC-012-07) | 42501; 23505 |
| 9 | `Auth.Login`, `login` (TC-012-08) | 23514 |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-012-AC-01 | As `echowell_app_login`, `UPDATE audit_logs …` and `DELETE FROM audit_logs` fail. | TC-012-01 |
| FEAT-012-AC-02 | As `echowell_migrator` with `SET echowell.allow_purge = 'on'`, `DELETE FROM audit_logs` succeeds and `UPDATE raw_sessions` still fails. | TC-012-02 |
| FEAT-012-AC-03 | App `SELECT count(*) FROM evaluation_ground_truth` and `SET ROLE echowell_readonly` → 42501; read-only SELECT succeeds. | TC-012-03 |
| FEAT-012-AC-04 | Second open `device_silent` for D02 → 23505; `device_silent` without `pipeline_run_id` → 23514; app `DELETE FROM alerts` → 42501. | TC-012-04 |
| FEAT-012-AC-05 | Second non-closed alert per epoch → 23505; closed alert plus new open alert succeed. | TC-012-05 |
| FEAT-012-AC-06 | Alert with `snoozed_until` set and `snoozed_by` NULL → 23514. | TC-012-06 |
| FEAT-012-AC-07 | UPDATE and DELETE on `alert_reviews` and `staff_notes` as app fail; two notes with the same `supersedes_id` → 23505. | TC-012-07 |
| FEAT-012-AC-08 | `audit_logs` accepts `auth.logout` and `auth.login.succeeded`; rejects `Auth.Login` and `login` with 23514. | TC-012-08 |
| FEAT-012-AC-09 | `grep -rn "evaluation_ground_truth" analytics` returns nothing. | TC-012-09 |

## Test Data Requirements

- `test_v0_1` seed with its pipeline run, seeded alerts (at least one non-closed alert A) and users; `clinician@example.com` as reviewer/author.
- Answer-key fixture `tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv` (10 rows, R01–R10) loaded with the test-only loader.
- Synthetic values only: note bodies "QA synthetic note…", code `R11` for rejected ground-truth rows, explanation code `cold_cough_sore_throat` from `review_explanations`.
- All mutations inside `BEGIN … ROLLBACK`.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-012-FR-01 (PGS-006) | FEAT-012 | TC-012-14 |
| FEAT-012-FR-02 (PGS-029, D-45) | FEAT-012 | TC-012-05 |
| FEAT-012-FR-03 (PGS-043) | FEAT-012 | TC-012-06 |
| FEAT-012-FR-04 (PGS-042, DME-021) | FEAT-012 | TC-012-07, TC-012-10 |
| FEAT-012-FR-05 (PGS-041, D-36) | FEAT-012 | TC-012-04, TC-012-11 |
| FEAT-012-FR-06 (PGS-036, FR-192, DB-010, SEC-113) | FEAT-012 | TC-012-07 |
| FEAT-012-FR-07 (PGS-044, SEC-102, FR-252) | FEAT-012 | TC-012-01, TC-012-08 |
| FEAT-012-FR-08 (DB-007, DME-024, PGS-040, D-38) | FEAT-012 | TC-012-03, TC-012-12 |
| FEAT-012-FR-09 (FR-204) | FEAT-012 | TC-012-12 |
| FEAT-012-FR-10 (DME-025, D-45, ARC-045) | FEAT-012 | TC-012-05, TC-012-04 |
| FEAT-012-FR-11 (DME-007, DME-022, D-37) | FEAT-012 | TC-012-14 |
| FEAT-012-FR-12 (DB-011) | FEAT-012 | TC-012-13 |
| FEAT-012-FR-13 (SEC-114, SEC-112, TST-041, D-49) | FEAT-012 | TC-012-01, TC-012-03, TC-012-04, TC-012-07 |
| FEAT-012-FR-14 (DB-007) | FEAT-012 | TC-012-09 |
| AC-PGS-03, AC-PGS-09, AC-PGS-14, AC-PGS-15 | FEAT-012 | TC-012-01, TC-012-02, TC-012-03, TC-012-04 |
| AC-AGT-02 | FEAT-012 | TC-012-09 |
| TST-041 (complete set) | FEAT-012 | TC-012-14 |
