# Backups, restore drill and rollback procedure

## Feature Description

FEAT-089 protects the interim production database and makes every deploy reversible: weekly (Mondays) and pre-migration-release `pg_dump --format=custom --no-owner` of production by the data steward to approved encrypted storage; the Neon point-in-time restore (PITR) window recorded; a Neon branch `pre-<short-sha>` before a release with a migration; one restore drill into a Neon branch `restore-drill` (schema diff, health, `run-pipeline --scope all`, row-count comparison, R01–R10 validation, record in `docs/deployment.md`); a timed rollback rehearsal (≤ 10 minutes, no `alembic downgrade` in production); the TRD 15 §4.12 rollback table and §4.13 PITR procedure documented. The interim stack holds synthetic and test data only (D-60 waiver of the AWS backup targets).

Status: Not Started in BACKLOG.md §10. Per TRD 24 D-180 the backups, restore drill and rollback rehearsal are carried out as Block 5 validation activities on the deployed interim stack, so these test cases are the runbook the team follows. Cases marked **Hosted** use placeholders (`<PRODUCTION_API_BASE_URL>`, `<STAGING_API_BASE_URL>`, `<STAGING_FRONTEND_URL>`, `<production direct URL>`, `<restore-drill app URL>`, `<restore-drill migrator URL>`). Nothing here migrates or re-seeds an environment (TRD 24 D-170): the drill writes only to the temporary `restore-drill` branch, and the rollback rehearsal is run on staging and ends in the state it started from.

Note: FEAT-089 does not say on which environment the rollback is rehearsed. To leave the working production deployment unchanged (D-170), TC-089-06 rehearses on staging (`echowell-und-staging`, `echowell-api`, `echowell-nightly-staging`); the same actions apply to `echowell-und`, `echowell-backend-production` and `echowell-nightly-production` in a real incident.

## Preconditions

- Data steward on a UND-managed workstation with `pg_dump` / `pg_restore` / `psql` 16 and access to the storage designated by the PI for the study's research data (encrypted at rest; never GitHub, never a personal device).
- Neon console access (DevOps owner) to project `echowell`; Render and Netlify dashboard access with permission to roll back and publish deploys on the staging services.
- Repository checked out at the SHA that production runs (read from `<PRODUCTION_API_BASE_URL>/health` `version`), Python 3.12 and the backend requirements installed on the workstation.
- Connection strings are taken from the Render dashboard or the Neon console at the time of use and are never written into a file, the repository, an issue or the test record.
- A window agreed with the algorithm lead for TC-089-06 and TC-089-07 (staging is briefly on an older version or shows a failed deploy).

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-089-01 | Runbook records PITR window, dump schedule, storage class, rollback table and PITR procedure | High | Documentation |
| TC-089-02 | No dump is tracked in Git and no workflow uploads a dump | High | Security |
| TC-089-03 | Weekly production dump is taken, encrypted and stored on approved storage | High | Hosted |
| TC-089-04 | Pre-release restore branch `pre-<short-sha>` is created before a migration release and deleted after 7 days | Medium | Hosted |
| TC-089-05 | Restore drill into Neon branch `restore-drill` with matching counts and healthy backend | High | Hosted |
| TC-089-06 | Rollback rehearsal restores the previous frontend and backend within 10 minutes | High | Hosted |
| TC-089-07 | A failing-healthcheck deploy on staging leaves the previous deploy serving | High | Hosted |
| TC-089-08 | Full pipeline re-run after restore reproduces frozen baselines | High | Hosted |
| TC-089-09 | `alembic downgrade` is never available against production | High | Negative |
| TC-089-10 | Temporary Neon branches are deleted within 7 days | Medium | Hosted |
| TC-089-11 | A failed drill or a rehearsal over 10 minutes is recorded as a failure | Medium | Negative |
| TC-089-12 | Connections to non-local databases use TLS | Medium | Security |

### TC-089-01 Runbook records PITR window, dump schedule, storage class, rollback table and PITR procedure

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `docs/deployment.md` section "Neon (database)", row "Point-in-time restore window in force (DEP-095)" | A concrete window from the Neon plan in use (e.g. a number of hours or days) and the date it was verified |
| 2 | Open section "Backups and restore" | Weekly (Mondays) and pre-migration-release `pg_dump --format=custom --no-owner` by the data steward from a UND-managed workstation, encrypted at rest, stored only on the storage designated by the PI; never committed or uploaded as an Actions artifact |
| 3 | Read the PITR bullet | Neon console → project `echowell` → branch `main` → "Restore" → timestamp (UTC) → `SELECT max(received_at) FROM raw_sessions` → redeploy the matching backend → `python -m backend.cli run-pipeline --scope all` |
| 4 | Open section "Rollback" | Five rows: frontend broken (5 min), backend fails health check or pre-deploy (0 min), backend functionally broken without migration (10 min), broken after additive migration (10 min, "Do not run `alembic downgrade` in production"), data damaged (60 min: `revoke-api-key`, restore, redeploy, `run-pipeline --scope all`, `create-api-key`, issue labelled `incident`) |
| 5 | Read the rehearsal and drill record lines | After TC-089-05 and TC-089-06: date, duration, dump timestamp, row counts and result filled in (no data, no secrets) |

Note: on 15 Nov 2026 the PITR window row and the drill and rehearsal records read "recorded in Phase 10" (`docs/deployment.md:87`, `:216`, `:223`); steps 1 and 5 pass only after the team fills them in.

### TC-089-02 No dump is tracked in Git and no workflow uploads a dump

| Step | Action | Expected Result |
|---|---|---|
| 1 | `git ls-files \| grep -Ei '\.(dump\|sql\.gz\|backup)$'; echo "exit=$?"` | No output; `exit=1` |
| 2 | `grep -rnE "\.(dump\|sql\.gz\|backup)\b\|pg_dump" .github/workflows/; echo "exit=$?"` | No output; `exit=1` |
| 3 | `grep -rn "path:" -A3 .github/workflows/*.yml` around every `upload-artifact` step | Paths are test reports and coverage only (e.g. `build/smoke-junit.xml`, `frontend/coverage/`); none is a database dump |

### TC-089-03 Weekly production dump is taken, encrypted and stored on approved storage

| Step | Action | Expected Result |
|---|---|---|
| 1 | On Monday, on the UND-managed workstation, mount the PI-designated encrypted storage | Storage mounted; location class recorded as "UND-managed storage designated by the PI" |
| 2 | `pg_dump --format=custom --no-owner --file="<storage path>/echowell-production-<YYYYMMDD>.dump" "<production direct URL>"; echo "exit=$?"` | `exit=0`; file size > 0 |
| 3 | `pg_restore --list "<storage path>/echowell-production-<YYYYMMDD>.dump" \| grep -c "TABLE DATA"` | Count ≥ 24 (one per TRD 20 table with data) and the list includes `raw_sessions`, `audit_logs`, `alerts` |
| 4 | Immediately after the dump, on production (read-only): `SELECT (SELECT count(*) FROM raw_sessions) AS raw, (SELECT count(*) FROM alerts) AS alerts, (SELECT count(*) FROM audit_logs) AS audit;` | Counts recorded with the dump timestamp (used in TC-089-05) |
| 5 | Check that no copy remains outside the approved storage (`ls ~/Downloads`, the repository folder, temp folders) | No `.dump` file outside the approved storage |
| 6 | Record date, file name and storage class (not the path contents) in the weekly team status | Entry present for the week |

### TC-089-04 Pre-release restore branch `pre-<short-sha>` is created before a migration release and deleted after 7 days

Run only when a release containing a migration is planned (no migration is created for this test).

| Step | Action | Expected Result |
|---|---|---|
| 1 | Determine whether the release SHA R adds a file under `backend/alembic/versions/` since the deployed SHA: `git diff --name-only <deployed SHA> R -- backend/alembic/versions` | Non-empty list → this case applies; empty → record "not applicable, no migration" |
| 2 | Neon console → `echowell` → Branches → Create branch from `main`, name `pre-<first 7 characters of R>` | Branch listed with parent `main` and creation time |
| 3 | Take the TC-089-03 dump for this release | Dump recorded |
| 4 | Seven days after the release, if the branch was not used, delete it | Branch no longer listed; deletion date recorded (TPS-031) |

### TC-089-05 Restore drill into Neon branch `restore-drill` with matching counts and healthy backend

| Step | Action | Expected Result |
|---|---|---|
| 1 | Neon console → Branches → create branch `restore-drill` (from `main`, then restore the latest dump into it with `pg_restore --no-owner --clean --if-exists --role=echowell_migrator -d "<restore-drill migrator URL>" "<dump file>"`; or, per DEP-097, create it from a chosen point in time) | Branch `restore-drill` listed; `pg_restore` exit 0 with no `ERROR` line (any error is recorded and the drill fails) |
| 2 | Schema diff against `database/schema.sql` (same normalisation as `scripts/dump_schema.sh`, without overwriting the file): `pg_dump --schema-only --no-owner --no-comments --dbname="<restore-drill migrator URL>" \| grep -v -E '^(SET \|SELECT pg_catalog\.set_config\|\\restrict \|\\unrestrict \|-- Dumped (from\|by) )' \| grep -v -E '^ALTER TABLE ONLY [^ ]+ ALTER COLUMN [^ ]+ SET \(pg_attver=[0-9]+\);$' \| cat -s \| diff - database/schema.sql; echo "exit=$?"` | No diff output; `exit=0` |
| 3 | `psql "<restore-drill app URL>" -c "SELECT (SELECT count(*) FROM raw_sessions), (SELECT count(*) FROM alerts), (SELECT count(*) FROM audit_logs);"` | All three equal the source counts recorded in TC-089-03 step 4 |
| 4 | On the workstation, start a temporary backend from the deployed SHA with DATABASE_URL and DATABASE_MIGRATION_URL set to the `restore-drill` URLs (`sslmode=require`), GIT_SHA = deployed SHA and the production-profile variables of TRD 21 §4.7 (no PIPELINE_AS_OF); `curl -s http://localhost:8000/api/v1/health` | 200; `"status":"ok"`, `"database":"ok"`, `"version"` = deployed SHA |
| 5 | With the same variables: `python -m backend.cli run-pipeline --scope all --profile production; echo "exit=$?"` | `exit=0`; a new `pipeline_runs` row with `status` `succeeded` on the branch |
| 6 | Re-run the count query of step 3 | `raw_sessions` and `alerts` still equal the source; `audit_logs` = source + 2 (`pipeline.run.started`, `pipeline.run.finished`) |
| 7 | On the deployed SHA: `pytest tests/validation -q` | All pass, 0 failed |
| 8 | Stop the temporary backend; write the drill record in `docs/deployment.md` "Backups and restore": date, dump timestamp, the three counts (source / restored), schema diff result, health result, validation result | Record present; contains no connection string, no data |
| 9 | Delete branch `restore-drill` within 7 days | Branch no longer listed (TC-089-10) |
| 10 | Confirm the drill date is before 15 Nov 2026, or record the actual date as a late drill | Date recorded in `DEPLOYMENT_CHECKLIST.md` J.03 |

### TC-089-06 Rollback rehearsal restores the previous frontend and backend within 10 minutes

| Step | Action | Expected Result |
|---|---|---|
| 1 | Record the starting state: staging health `version` A, `echowell-build` meta of `<STAGING_FRONTEND_URL>/login` B; identify in Render → `echowell-api` → Events the previous successful deploy with SHA A′ and confirm `git diff --name-only A′ A -- backend/alembic/versions` is empty | A, B, A′ recorded; no migration between A′ and A |
| 2 | Start the timer. Netlify → `echowell-und-staging` → Deploys → the deploy before the current one → "Publish deploy" | Netlify shows that deploy as published |
| 3 | Render → `echowell-api` → Events → deploy A′ → "Rollback"; then the same for `echowell-nightly-staging` | Both show a rollback deploy in progress, then live |
| 4 | Poll `curl -s "<STAGING_API_BASE_URL>/health"` and the `/login` meta | `version` = A′; meta = the previous frontend build SHA |
| 5 | Stop the timer | Elapsed time ≤ 10 minutes (DEP-085); recorded |
| 6 | Note in Render the service setting "Auto-Deploy" | Render has turned auto-deploy off on the rolled-back services |
| 7 | Restore the starting state: Netlify → publish the deploy that was current at step 1; Render → Events → the deploy of A → "Rollback" for both services; set Auto-Deploy back to "After CI checks pass" | Health `version` = A; meta = B; auto-deploy "After CI checks pass" on both staging services |
| 8 | Record date, measured time, whether the rollback's pre-deploy command ran, and the result in `docs/deployment.md` "Rollback" | Record present |

### TC-089-07 A failing-healthcheck deploy on staging leaves the previous deploy serving

If the algorithm lead decides that no staging setting may be changed even temporarily (D-170), record FEAT-089-AC-01 as not executed with that reason instead of running this case.

| Step | Action | Expected Result |
|---|---|---|
| 1 | Record staging health `version` A and run a loop `while true; do curl -s -o /dev/null -w '%{http_code} ' "<STAGING_API_BASE_URL>/health"; sleep 30; done` | Prints `200` every 30 s |
| 2 | Render → `echowell-api` → Settings → Health Check Path: change `/api/v1/health` to `/api/v1/health-missing`; Manual Deploy → "Deploy latest commit" | New deploy starts |
| 3 | Watch Events for up to about 15 minutes (Render's deploy window) | The new deploy ends failed (health check not passing); no traffic switch |
| 4 | Read the loop output during the whole window | Only `200`; health `version` remains A |
| 5 | Set Health Check Path back to `/api/v1/health` | Setting restored; record in `DEPLOYMENT_CHECKLIST.md` F.06 |
| 6 | Check Render workspace notifications | Failed-deploy e-mail received by the DevOps owner |

### TC-089-08 Full pipeline re-run after restore reproduces frozen baselines

| Step | Action | Expected Result |
|---|---|---|
| 1 | Before TC-089-05 step 5, on the `restore-drill` branch: `SELECT count(*), md5(string_agg(resident_id::text \|\| epoch_id::text \|\| feature_key \|\| median::text \|\| robust_spread::text, ',' ORDER BY resident_id, epoch_id, feature_key)) FROM baselines;` | Count C and hash H recorded (both may be 0 / empty if no baseline is frozen yet) |
| 2 | After TC-089-05 step 5, run the same query | Same C and H |
| 3 | `SELECT count(*) FROM alert_reviews; SELECT count(*) FROM staff_notes;` before and after | Unchanged (human-entered rows survive the run, SEC-163) |

### TC-089-09 `alembic downgrade` is never available against production

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -rn "downgrade" .github/workflows/ render.yaml; echo "exit=$?"` | No match; `exit=1` |
| 2 | Locally: `docker compose exec -e APP_ENV=production backend python -m backend.cli reset-test-db; echo "exit=$?"` | `exit=2`; "reset-test-db is not allowed in production" (the only command that downgrades) |
| 3 | Read `docs/deployment.md` "Hard rules" and "Rollback" | Both state no `alembic downgrade` in production; schema rollback only by Neon branch or PITR |

### TC-089-10 Temporary Neon branches are deleted within 7 days

| Step | Action | Expected Result |
|---|---|---|
| 1 | Neon console → `echowell` → Branches, 7 days after TC-089-05 and TC-089-04 | No `restore-drill` branch and no unused `pre-<short-sha>` branch older than 7 days |
| 2 | Compare with the recorded creation dates | Deletion within 7 days of creation |

### TC-089-11 A failed drill or a rehearsal over 10 minutes is recorded as a failure

| Step | Action | Expected Result |
|---|---|---|
| 1 | If any of TC-089-05 steps 2, 3, 4, 6 or 7 does not meet its expected result | Drill recorded in `docs/deployment.md` as failed with the cause; drill repeated after the fix |
| 2 | If TC-089-06 step 5 exceeds 10 minutes | Recorded as a failure of DEP-085 with the measured time and the corrective action |
| 3 | Check `DEPLOYMENT_CHECKLIST.md` I.02 and J.03 | Status `[ ]` with the failure noted until a passing repeat |

### TC-089-12 Connections to non-local databases use TLS

| Step | Action | Expected Result |
|---|---|---|
| 1 | Inspect the connection strings used in TC-089-03 and TC-089-05 (do not copy them) | Each ends with `sslmode=require` (or `verify-full`) |
| 2 | During the dump, run on production: `SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid();` from the same workstation session | `t` |
| 3 | Attempt `psql "<production direct URL with sslmode=disable>" -c "SELECT 1"` | Connection refused by Neon (TLS required) |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | Temporary backend on the drill branch: `GET http://localhost:8000/api/v1/health` | 200; `status` `ok`; `database` `ok`; `version` = deployed SHA |
| 2 | During the rehearsal: `GET <STAGING_API_BASE_URL>/health` | `version` changes from A to A′ and back to A |
| 3 | During the failing-healthcheck deploy: `GET <STAGING_API_BASE_URL>/health` | 200 throughout; `version` A |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | Source vs restored counts of `raw_sessions`, `alerts`, `audit_logs` (TC-089-05) | Equal before the pipeline run; `audit_logs` +2 after |
| 2 | `SELECT status, trigger, config_profile FROM pipeline_runs ORDER BY started_at DESC LIMIT 1;` on the drill branch | `succeeded`, `manual`, `production` |
| 3 | Baseline hash before and after the re-run (TC-089-08) | Identical |
| 4 | Production after the drill: `SELECT max(started_at) FROM pipeline_runs WHERE trigger = 'manual';` | Unchanged by the drill (production not modified) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Look for tracked dumps (TC-089-02) | None |
| 2 | Deploy with a failing health check path on staging (TC-089-07) | Previous deploy keeps serving; new deploy failed |
| 3 | `reset-test-db` with `APP_ENV=production` (TC-089-09) | Exit 2 with the refusal message |
| 4 | Connect without TLS (TC-089-12) | Refused |
| 5 | Drill counts differ or rehearsal exceeds 10 minutes (TC-089-11) | Recorded as failure, repeated |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-089-AC-01 | A failing-healthcheck deployment on staging leaves the previous deployment serving (health `version` unchanged) | TC-089-07 |
| FEAT-089-AC-02 | Rollback rehearsal restores previous frontend and backend within 10 minutes, time recorded | TC-089-06, TC-089-11 |
| FEAT-089-AC-03 | Restore drill completed and documented before 15 Nov 2026 with matching `raw_sessions` and `alerts` counts and healthy `GET /api/v1/health` | TC-089-05, TC-089-08, TC-089-11 |
| FEAT-089-AC-04 | `docs/deployment.md` records the Neon restore window, weekly dump schedule, storage location class and the rollback table | TC-089-01, TC-089-03 |
| FEAT-089-AC-05 | `git ls-files \| grep -Ei '\.(dump\|sql\.gz\|backup)$'` returns nothing and no workflow uploads a dump | TC-089-02 |

## Test Data Requirements

- Interim production data only (synthetic and team-test, `T`-prefixed demo IDs); no real resident data exists to protect (D-28, D-60).
- The latest weekly dump file on the PI-designated storage; source row counts captured at dump time.
- Temporary Neon branches `restore-drill` and, when applicable, `pre-<short-sha>`.
- Staging deploy history with at least two successful deploys and no migration between them (TC-089-06).
- Placeholders for all URLs and connection strings; no credential in the record.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| DEP-095, NFR-024, SEC-160, D-60 | FEAT-089 | TC-089-01 |
| DEP-096, DB-054 | FEAT-089 | TC-089-03 |
| DEP-098, CIC-101 | FEAT-089 | TC-089-02 |
| DEP-063, TPS-031 | FEAT-089 | TC-089-04, TC-089-10 |
| DEP-085, AC-DEP-07 | FEAT-089 | TC-089-06, TC-089-11 |
| DEP-041, AC-DEP-06 | FEAT-089 | TC-089-07 |
| DEP-086 | FEAT-089 | TC-089-09 |
| DEP-087, ASM-07, SEC-163 | FEAT-089 | TC-089-08 |
| DEP-097, DB-051, SEC-162, NFR-025, D-77, AC-DEP-08, PGS-016 | FEAT-089 | TC-089-05 |
| TRD 15 §4.12, §4.13 | FEAT-089 | TC-089-01 |
| DB-052, DB-053, PGS-039 | FEAT-089 | TC-089-12 |
| FEAT-089-FR-01..FEAT-089-FR-11 | FEAT-089 | TC-089-01..TC-089-12 |
