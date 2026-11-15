# Demo acceptance and local fallback rehearsal (SRC-15 steps 4–5)

## Feature Description

FEAT-090 executes and records the end-of-semester demo acceptance. Step 4a: the answer-key validation passes (profile `test_v0_1`) on an isolated database seeded only with DS-01, on the commit deployed to the demo environment. Step 4b: one device record from a team-member speaker under a `T`-prefixed demo study ID is posted to interim production (`POST /api/v1/sessions`, profile `production`), returns 201, is stored unaltered in `raw_sessions` and gets a processed status with reasons. Step 5: within 60 s of the POST, `/residents` shows the demo resident's last check-in at the record's local time and its 30-day used count +1, with the pill "○ Learning" and "Learning their usual: 1 of 30 check-ins so far." and no alarm. Automated evidence TST-187 (≤ 5 s on the warm Compose stack) and TST-188 (seeded logins) is attached, and the local Docker Compose fallback is rehearsed end to end. Results go to `docs/reports/DEPLOYMENT_REPORT.md` ("Demo acceptance"), `docs/deployment.md` (fallback record) and `specs/backlog/MVP_READINESS_CHECKLIST.md`.

Status: Not Started in BACKLOG.md §10. Per TRD 24 D-180 the demo acceptance is carried out as a Block 5 validation activity, so these test cases are the runbook the team follows. Cases marked **Hosted** use the placeholders `<PRODUCTION_API_BASE_URL>`, `<PRODUCTION_FRONTEND_URL>`, `<STAGING_FRONTEND_URL>` and `<laptop LAN IP>`. Posting the demo check-in to production is the designed demo path (D-59, DEP-093); no case migrates, re-seeds or changes a hosted service setting (D-170), and `test_v0_1` data is never loaded into production.

## Preconditions

- Interim production deployed (FEAT-088) and passing the DEP-081 smoke tests; its `version` read from `<PRODUCTION_API_BASE_URL>/health` is the demo commit D.
- A `T`-prefixed demo resident (e.g. `T01`) and a test device registered on production with `import-master-data`, and an interim API key bound to that test device (`create-api-key --name <name> --device <device>`), held by Team 1; never a device deployed at the facility.
- Team 1 can produce one schema v0.1 feature record from a team-member speaker (no audio leaves the device; only the feature record is sent).
- A production account with role clinician or admin for the dashboard; read-only `psql` access to the production database from the operator workstation (connection string from the Render dashboard, never written down).
- Local: Docker Compose v2, the repository at D, `cp .env.development.example .env`.
- A clock synchronised to network time on the tester's machine (for the 60 s measurement).

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-090-01 | Step 4a: validation reports "Overall: PASS" on an isolated DS-01-only database at the demo commit | High | Analytics |
| TC-090-02 | Step 4b: demo POST to interim production returns 201 and is stored unaltered | High | Hosted |
| TC-090-03 | Step 4b: the demo session has a processed status with its reasons under profile `production` | High | Hosted |
| TC-090-04 | Step 5: Resident list shows last check-in, used count +1 and the Learning pill within 60 s | High | Hosted |
| TC-090-05 | Step 5: change score bar appears only once the demo baseline is frozen | Low | Hosted |
| TC-090-06 | The demo POST is never sent to staging; staging shows the full R01–R10 behaviour | High | Hosted |
| TC-090-07 | TST-187 (≤ 5 s) and TST-188 (seeded logins) pass on the release candidate commit | High | Performance |
| TC-090-08 | Local fallback rehearsal: `curl` POST to the laptop appears on the dashboard | High | Positive |
| TC-090-09 | Fallback steps and rehearsal record are written in `docs/deployment.md` | High | Documentation |
| TC-090-10 | MVP readiness checklist shows status and evidence for MVP-01..MVP-15 | High | Documentation |
| TC-090-11 | Rejected demo record (422) is diagnosed and reposted with a new session ID | Medium | Negative |
| TC-090-12 | Reposting the same session ID is stored as a duplicate and not shown | Medium | Negative |
| TC-090-13 | Demo data is test data only; no real resident data on the interim stack | High | Security |

### TC-090-01 Step 4a: validation reports "Overall: PASS" on an isolated DS-01-only database at the demo commit

| Step | Action | Expected Result |
|---|---|---|
| 1 | `git checkout D`; `docker compose down -v`; `docker compose up -d --build --wait db backend` | Fresh local database; health 200 |
| 2 | `docker compose exec backend python -m backend.cli seed test_v0_1` and the DS-10 loader (`python database/seeds/load_evaluation_ground_truth.py tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv`) | Exit 0 for both |
| 3 | `docker compose exec db psql -U echowell -d echowell -c "SELECT count(*) FROM residents WHERE resident_code !~ '^R(0[1-9]\|10)\$';"` | `0` (no `T`-prefixed or device resident in this database) |
| 4 | `docker compose exec db psql -U echowell -d echowell -c "SELECT DISTINCT source FROM ingest_batches;"` | Only `seed` |
| 5 | On the host at D: `pytest tests/validation -q` | All tests pass, 0 failed |
| 6 | Open the `backend-reports` artifact of the `ci.yml` run on D, file `ALGORITHM_VALIDATION_REPORT.md` | Contains "Overall: PASS"; VC-R01..VC-R10 and VC-G01..VC-G12 PASS; the report's Git SHA = D |
| 7 | Record the result in `DEPLOYMENT_REPORT.md` "Demo acceptance" (step 4a) and `MVP_READINESS_CHECKLIST.md` E.01 | Rows filled with D and the run link |

### TC-090-02 Step 4b: demo POST to interim production returns 201 and is stored unaltered

| Step | Action | Expected Result |
|---|---|---|
| 1 | Record the time t0 (UTC). Team 1 sends the device record for `T01` with a new session ID `T01-<YYYYMMDD>-NN` to `<PRODUCTION_API_BASE_URL>/sessions` with header `X-API-Key` (the interim test key); keep a copy of the exact request body B | HTTP `201`; response contains the `session_id` |
| 2 | Production (read-only): `SELECT payload FROM raw_sessions WHERE session_id = 'T01-<YYYYMMDD>-NN';` | One row |
| 3 | Compare the stored `payload` with B (`jq -S . B.json` vs the `payload` value formatted with `jq -S .`) | Identical: same keys, names and values (BR-01) |
| 4 | `SELECT r.schema_version, b.source FROM raw_sessions r JOIN ingest_batches b ON r.ingest_batch_id = b.id WHERE r.session_id = 'T01-<YYYYMMDD>-NN';` | `0.1`; source is not `seed` |

### TC-090-03 Step 4b: the demo session has a processed status with its reasons under profile `production`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT p.status, p.reasons FROM processed_sessions p JOIN raw_sessions r ON p.raw_session_id = r.id WHERE r.session_id = 'T01-<YYYYMMDD>-NN';` | One row; `status` is `usable`, `set_aside` or `quarantined`; `reasons` is `{}` for usable, otherwise the exact reason strings (e.g. `quality flag poor`) |
| 2 | `SELECT trigger, config_profile, status FROM pipeline_runs ORDER BY started_at DESC LIMIT 1;` | `ingest`, `production`, `succeeded` |
| 3 | `SELECT action FROM audit_logs WHERE occurred_at >= '<t0>' ORDER BY occurred_at;` | Contains `pipeline.run.started` and `pipeline.run.finished` |
| 4 | Record status, reasons, run ID and timestamps in `DEPLOYMENT_REPORT.md` (step 4b) and `MVP_READINESS_CHECKLIST.md` E.02 | Filled; no feature values copied |

### TC-090-04 Step 5: Resident list shows last check-in, used count +1 and the Learning pill within 60 s

| Step | Action | Expected Result |
|---|---|---|
| 1 | Before the POST of TC-090-02, open `<PRODUCTION_FRONTEND_URL>/residents` as a clinician and note the `T01` row and, in `/residents/T01`, the 30-day used count U | Values recorded (first record: no last check-in, U = 0) |
| 2 | Within 60 s of t0, reload `/residents` | `T01` row "Last check-in" = the record's facility-local time in the form `Mon D, h:mm AM/PM CT` |
| 3 | Read the `T01` row pill and text (first usable record) | Pill "○ Learning"; text "Learning their usual: 1 of 30 check-ins so far."; no alarm pill |
| 4 | Open `/residents/T01` | 30-day used count = U + 1 (for a usable record) |
| 5 | Record the elapsed time from t0 to step 2 and a screenshot reference | ≤ 60 s; filled in `MVP_READINESS_CHECKLIST.md` E.03 and E.04 |
| 6 | If over 60 s: confirm `echowell-backend-production` is on instance type Starter, call `GET <PRODUCTION_API_BASE_URL>/health` to wake the Neon compute, and repeat with a new session ID | Repeat within 60 s; both attempts recorded |

Note: `MVP_READINESS_CHECKLIST.md:91` (E.04) words the expected text as "Baseline forming · 1 of 30 sessions"; this case follows TRD 13 TST-184 ("○ Learning", "Learning their usual: 1 of 30 check-ins so far."), which is also what `frontend/lib/wording/list.ts:143` renders.

### TC-090-05 Step 5: change score bar appears only once the demo baseline is frozen

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/T01/trends` after the first usable demo record | Heading "Change score" shown; no score bar (baseline not frozen; production baseline_n 30) |
| 2 | Record in the report that the bar criterion is not reachable in the demo window (D-67, FEAT-090 Implementation Notes) | Recorded |
| 3 | Only if 30 usable demo check-ins exist later: post one more record and reload `/residents/T01/trends` | One more bar than before the POST, within 60 s |

### TC-090-06 The demo POST is never sent to staging; staging shows the full R01–R10 behaviour

| Step | Action | Expected Result |
|---|---|---|
| 1 | Staging (read-only): `SELECT count(*) FROM residents WHERE resident_code ~ '^T';` | `0` |
| 2 | Open `<STAGING_FRONTEND_URL>/residents` | Filters "All (10)", "Changed (2)", "Needs attention (2)", "Usual (6)"; header "pipeline test data v0.1" |
| 3 | Open R09 on staging | Pill "▲ Changed"; change score chart with "Alarm line: 5" |
| 4 | Production (read-only): `SELECT count(*) FROM residents WHERE resident_code ~ '^R';` | `0` (no `test_v0_1` data in production) |

### TC-090-07 TST-187 (≤ 5 s) and TST-188 (seeded logins) pass on the release candidate commit

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open the `e2e.yml` run on the release candidate commit, job `playwright`, step "Isolated run" | Test "TST-187 a posted check-in shows within 5 s" passed (and "E2E-15 new check-in appears") |
| 2 | Locate the TST-188 test `tests/integration/test_seed_logins.py` and its result in `backend-test` | Test exists and passed: login as `admin@example.com`, `clinician@example.com`, `researcher@example.com` returns 200 with the matching `role` |
| 3 | Record both run links in `MVP_READINESS_CHECKLIST.md` E.05 and in the report | Filled |

Note: on 15 Nov 2026 `tests/integration/test_seed_logins.py` is not in the repository (`TRD_Implementation_Audit.md` TST-188 FAIL, S3; to be added in Block 5 under D-174); step 2 passes only once it exists.

### TC-090-08 Local fallback rehearsal: `curl` POST to the laptop appears on the dashboard

| Step | Action | Expected Result |
|---|---|---|
| 1 | On a team laptop at the commit on `main`: `cp .env.development.example .env`, then set `PIPELINE_AS_OF=` (empty) in `.env` for the rehearsal | `.env` has `PIPELINE_PROFILE=test_v0_1` and an empty `PIPELINE_AS_OF` |
| 2 | `docker compose --profile demo up -d --build --wait db backend frontend-prod` | `db`, `backend`, `frontend-prod` healthy |
| 3 | `docker compose exec backend python -m backend.cli seed test_v0_1 --master-only`; `docker compose exec backend python -m backend.cli import-master-data --dir tests/fixtures/seeds/demo_overlay` | Exit 0; synthetic resident R11 with device D11 registered |
| 4 | `docker compose exec backend python -m backend.cli create-api-key --name fallback-d11 --device D11` | Key printed once; held only for the rehearsal |
| 5 | Bind the backend port to the laptop's LAN address for the rehearsal only (uncommitted local override `ports: ["<laptop LAN IP>:8000:8000"]`, then `docker compose --profile demo up -d backend`) | `curl -s http://<laptop LAN IP>:8000/api/v1/health` from a second machine on the LAN returns `"status":"ok"` |
| 6 | From the second machine: `curl -sS -X POST "http://<laptop LAN IP>:8000/api/v1/sessions" -H "X-API-Key: <key from step 4>" -H 'Content-Type: application/json' -d @r11.json` (body in Test Data Requirements, `session_id` `R11-<today YYYYMMDD>-01`, `timestamp_utc` = now) | HTTP `201` |
| 7 | Open `http://localhost:3001/residents` on the laptop and sign in as `clinician@example.com` | Row R11 with pill "○ Learning", "Learning their usual: 1 of 16 check-ins so far." (profile `test_v0_1`) and "Last check-in" = the record's local time `Mon D, h:mm AM/PM CT` |
| 8 | Remove the override and restart so the port is bound to `127.0.0.1` again | `curl http://<laptop LAN IP>:8000/api/v1/health` from the second machine fails to connect |
| 9 | Record date, commit, steps and result in `docs/deployment.md` "Demo fallback (RSK-12)" | Rehearsal record present, dated before 15 Nov 2026 or with the actual date |

Note: `docs/deployment.md` "Demo fallback" step 1 copies `.env.development.example`, whose `PIPELINE_AS_OF=2026-10-30T15:00:00-05:00` (`.env.development.example:12`); `analytics/pipeline.py:223-225` excludes records stamped after the as-of (warning `after_as_of`), so a record stamped with the current time would not appear. The rehearsal therefore runs with an empty `PIPELINE_AS_OF`, as the isolated E2E run does (`.github/workflows/e2e.yml:85`).

### TC-090-09 Fallback steps and rehearsal record are written in `docs/deployment.md`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `docs/deployment.md` section "Demo fallback (RSK-12)" | Steps include `docker compose --profile demo up -d … db backend frontend-prod`, dashboard at `http://localhost:3001`, device posts to `http://<laptop LAN IP>:8000/api/v1/sessions`, LAN binding only for the demo and rebinding to 127.0.0.1 afterwards |
| 2 | Read the "Rehearsal (DEP-092, AC-DEP-09)" line | Date and result of TC-090-08 filled in (not "record date and result here in Phase 10") |
| 3 | Open `DEPLOYMENT_CHECKLIST.md` L.02 | Evidence column links the rehearsal record |

### TC-090-10 MVP readiness checklist shows status and evidence for MVP-01..MVP-15

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -c "^| MVP-" specs/backlog/MVP_READINESS_CHECKLIST.md` | `15` |
| 2 | Read the Status and Evidence columns of each MVP row in section M | Each row has a status (`[x]`, `[ ] FAIL` with reason, or pending with reason) and an evidence link or file reference |
| 3 | Read sections D and E | Rows D.01..D.07 and E.01..E.08 carry the evidence produced by TC-090-01..TC-090-09 and the FEAT-088/FEAT-089 runbooks |
| 4 | Check the GitHub Release of the release candidate commit | Release notes link the same evidence (TST-170, AC-TST-10) |

### TC-090-11 Rejected demo record (422) is diagnosed and reposted with a new session ID

| Step | Action | Expected Result |
|---|---|---|
| 1 | Locally (Compose), POST the R11 body of TC-090-08 with `session_id` `R11-<today>-02` and an extra field `"speaker_confidence": 0.9` | HTTP `422`; error for field `speaker_confidence` code `extra_forbidden` "This field is not part of schema v0.1." |
| 2 | `SELECT errors FROM ingest_rejections ORDER BY received_at DESC LIMIT 1;` and `SELECT count(*) FROM raw_sessions WHERE session_id = 'R11-<today>-02';` | The latest rejection's `errors` names `speaker_confidence` with `extra_forbidden`; `raw_sessions` count `0` |
| 3 | Remove the field and repost with session ID `R11-<today>-02` | HTTP `201` |
| 4 | On production, if Team 1's record returns 422: read the rejection reason with Team 1, fix the record format, repost with a new session ID | Repost returns 201; both attempts recorded |

### TC-090-12 Reposting the same session ID is stored as a duplicate and not shown

| Step | Action | Expected Result |
|---|---|---|
| 1 | Locally, repost the exact body of TC-090-08 step 6 (same `session_id`) | HTTP `200` ("Duplicate session_id stored and dropped"), not 201 |
| 2 | `SELECT p.status, p.reasons FROM processed_sessions p JOIN raw_sessions r ON p.raw_session_id = r.id WHERE r.session_id = 'R11-<today>-01' ORDER BY r.arrival_seq;` | Second row `duplicate` with reason `session_id already received` |
| 3 | Reload `/residents` | R11 text "Learning their usual: n of 16 check-ins so far." and "Last check-in" are the same as before step 1 (the duplicate is not counted) |

### TC-090-13 Demo data is test data only; no real resident data on the interim stack

| Step | Action | Expected Result |
|---|---|---|
| 1 | Production (read-only): `SELECT resident_code FROM residents WHERE resident_code !~ '^T';` | 0 rows |
| 2 | Confirm with Team 1 that the record came from a team-member speaker and the device is a test device | Written confirmation in the report (roles only) |
| 3 | `SELECT name, device_id IS NOT NULL AS bound FROM api_keys WHERE active;` on production | Only test-device or harness keys |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `POST <PRODUCTION_API_BASE_URL>/sessions` with `X-API-Key` (test device) and a valid v0.1 record | 201 |
| 2 | Same without `X-API-Key` | 401 |
| 3 | `GET <PRODUCTION_API_BASE_URL>/residents` with clinician token | 200; `T01` item with last check-in and status Learning |
| 4 | `GET <PRODUCTION_API_BASE_URL>/residents/T01` | 200; used count increased by 1 after a usable record |
| 5 | `GET <PRODUCTION_API_BASE_URL>/scores?resident_code=T01` | 200; empty list while the baseline is forming |
| 6 | Local fallback: `POST http://<laptop LAN IP>:8000/api/v1/sessions` | 201 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `raw_sessions.payload` of the demo session vs the request body (TC-090-02) | Identical |
| 2 | `processed_sessions.status` / `reasons` of the demo session (TC-090-03) | Valid status with exact reasons |
| 3 | Latest `pipeline_runs` row (TC-090-03) | `ingest`, `production`, `succeeded` |
| 4 | Isolated validation database residents and batch sources (TC-090-01) | Only R01–R10; only `seed` |
| 5 | Staging `T`-prefixed residents; production `R`-prefixed residents (TC-090-06) | 0 and 0 |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Record with an extra field (TC-090-11) | 422 `extra_forbidden`; no `raw_sessions` row |
| 2 | Repeated session ID (TC-090-12) | HTTP 200; stored as `duplicate`, not displayed |
| 3 | POST without API key (API Validation step 2) | 401 |
| 4 | Step 5 slower than 60 s (TC-090-04 step 6) | Cold-start checks, repeat; both attempts recorded |
| 5 | Port still bound to the LAN after the rehearsal (TC-090-08 step 8) | Not reachable from the LAN after rebinding |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-090-AC-01 | Validation report on the demo commit shows "Overall: PASS" on a database with no real or demo-device record | TC-090-01 |
| FEAT-090-AC-02 | Demo POST to interim production returns 201; stored `raw_sessions.payload` equals the body; status usable, set_aside or quarantined with reasons | TC-090-02, TC-090-03, TC-090-11 |
| FEAT-090-AC-03 | Within 60 s `/residents` shows last check-in at local time and used count +1, pill "○ Learning" with "Learning their usual: 1 of 30 check-ins so far.", no alarm | TC-090-04, TC-090-05, TC-090-12 |
| FEAT-090-AC-04 | TST-187 (≤ 5 s) and TST-188 pass on the release candidate commit | TC-090-07 |
| FEAT-090-AC-05 | Fallback rehearsal documented in `docs/deployment.md` and a `curl` POST to the laptop appears on the dashboard after processing | TC-090-08, TC-090-09 |
| FEAT-090-AC-06 | `MVP_READINESS_CHECKLIST.md` shows status and evidence for each of MVP-01..MVP-15 | TC-090-10 |

## Test Data Requirements

- Isolated validation database: DS-01 via `seed test_v0_1` and the DS-10 answer key (R01–R10 only).
- Production: `T`-prefixed demo resident (e.g. `T01`), a test device and its interim API key; one record from Team 1 (team-member speaker, feature values only).
- Fallback: synthetic R11 / D11 from `tests/fixtures/seeds/demo_overlay`; body `r11.json` with the SRC-05 values of `R01-20261001-01` used by `frontend/tests/e2e/isolated.spec.ts`: `{"schema_version":"0.1","session_id":"R11-<YYYYMMDD>-01","resident_id":"R11","device_id":"D11","timestamp_utc":"<YYYY-MM-DD HH:MM:SS UTC now>","mic_noise_level_dbfs":-55.7,"audio_quality_flag":"ok","extraction_software_version":"openSMILE 3.0.2","device_firmware_version":"fw-1.0.0","speech_duration_s":2.78,"phrase_id":"P01","loudness_dbfs":-30.67,"total_phrase_duration_s":2.78,"speech_rate_syl_per_s":3.83,"articulation_rate_syl_per_s":5.52,"number_of_pauses":1,"pause_fraction":0.239,"voiced_fraction":0.564,"mean_f0_hz":202.8,"f0_variability_st":4.31,"jitter_local_pct":0.885,"shimmer_local_pct":1.18,"hnr_db":10.68,"cpps_db":12.04,"alpha_ratio_db":-14.18,"hammarberg_index_db":16.77,"mfcc1":39.22,"mfcc2":16.66,"mfcc3":-0.24,"mfcc4":-8.71}`.
- Seeded local users and passwords from `.env` (never written down); production accounts created per FEAT-088.
- No audio anywhere.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| TST-180, AC-TST-11 | FEAT-090 | TC-090-01, TC-090-02, TC-090-03 |
| TST-182, TDV-007 | FEAT-090 | TC-090-01, TC-090-06 |
| D-59, DEP-093, AC-VIS-03 | FEAT-090 | TC-090-02, TC-090-06 |
| TST-181, FR-184, D-67, UX-144 | FEAT-090 | TC-090-04, TC-090-05 |
| TST-184 | FEAT-090 | TC-090-04 |
| TST-187, TST-188, NFR-011, SC-03 | FEAT-090 | TC-090-07 |
| DEP-090, TST-183, RSK-12 | FEAT-090 | TC-090-08 |
| DEP-091 | FEAT-090 | TC-090-08 |
| DEP-092, AC-DEP-09 | FEAT-090 | TC-090-08, TC-090-09 |
| DEP-093 | FEAT-090 | TC-090-06 |
| TST-170, AC-TST-10 | FEAT-090 | TC-090-10 |
| VIS-024, DEP-008, D-28, SEC-003 | FEAT-090 | TC-090-13 |
| FEAT-090-FR-01..FEAT-090-FR-11 | FEAT-090 | TC-090-01..TC-090-13 |
