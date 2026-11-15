# Admin page: users, pipeline runs and CSV upload

## Feature Description

`/admin` is the admin-only page (FEAT-074, TRD 11 UX-210..UX-219, §4.10; kept in the v0.2 visual style, D-111). It has the `<h1>` "Admin" and three ARIA tabs "Users", "Pipeline runs", "Upload data" with arrow-key navigation and the selected tab kept in `?tab=` (`users`, `runs`, `upload`). Users: list ("Email", "Display name", "Role", "Active", "Last sign-in"), "Add user" form (`POST /api/v1/users`), "Deactivate"/"Reactivate" with confirmation and role change (`PATCH /api/v1/users/{id}`), errors mapped by `ApiError.code`. Pipeline runs: latest 50 runs newest first, "Run pipeline now" with the environment profile only and 5-second polling, banners for a failed latest run and a missing nightly run. Upload data: CSV upload with the synthetic-data line, batch result "Accepted <a> · Rejected <r> · Duplicates <d>", rejections table and the whole-file rejection text. The page ends with the API status line from `GET /api/v1/health`. Non-admins see the access-denied state and no admin API call is made. Residents, devices, assignments and API keys stay CLI-managed.

## Preconditions

- Local Docker Compose demo profile running and seeded (`docker compose exec -T backend python -m backend.cli seed test_v0_1 --reset`); frontend `http://localhost:3001`, API `http://localhost:8000/api/v1`; `.env` from `.env.development.example` (`PIPELINE_PROFILE=test_v0_1`, `PIPELINE_AS_OF=2026-10-30T15:00:00-05:00`).
- Seeded users `admin@example.com`, `clinician@example.com`, `researcher@example.com` with the `SEED_*` passwords from `.env`.
- Fixture files: `tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv` (SRC-05) and `tests/fixtures/legacy/echowell_mock_data_500.csv` (SRC-06).
- For TC-074-08 a database holding the roster without records: `docker compose exec -T backend python -m backend.cli seed test_v0_1 --reset --master-only` (local only), followed by `docker compose restart backend`.
- `cd frontend && npm ci` for the page and component tests (`frontend/tests/pages/admin.test.tsx`, `frontend/components/AdminPanel/AdminPanel.test.tsx`).
- Re-seed with `seed test_v0_1 --reset` after the cases that write (TC-074-05, -06, -07, -08) so later suites see the pristine seed.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-074-01 | Admin sees app bar with "Admin" current, data bar, `<h1>` "Admin" and the three tabs | High | UI |
| TC-074-02 | Clinician and researcher see the access-denied state and no admin API call | High | Security |
| TC-074-03 | Tabs: arrow keys, Home/End and `?tab=` URL state | Medium | UI |
| TC-074-04 | Users tab lists the seeded users with the five columns | Medium | Positive |
| TC-074-05 | Add a user through the form | High | Positive |
| TC-074-06 | Duplicate e-mail shows the 409 error under the Email field; policy and required-field errors | High | Negative |
| TC-074-07 | Deactivate asks for confirmation before `PATCH`; reactivate; role change; last admin protected | High | Positive |
| TC-074-08 | Upload SRC-05 shows "Accepted 283 · Rejected 0 · Duplicates 2" | High | Positive |
| TC-074-09 | Upload legacy SRC-06 shows the whole-file rejection and stores nothing | High | Negative |
| TC-074-10 | Upload tab synthetic-data line, "Choose a CSV file first." and no master-data controls | High | UI |
| TC-074-11 | Pipeline runs tab lists at most 50 runs newest first with all columns | High | Positive |
| TC-074-12 | "Run pipeline now" offers only `meta.pipeline_profile` and polls the run every 5 s | High | Positive |
| TC-074-13 | Run errors 409 `PIPELINE_RUN_IN_PROGRESS` and 422 `PROFILE_NOT_ALLOWED` | Medium | Negative |
| TC-074-14 | Failed-latest-run banner and "Nightly run missing for <date>" banner | High | Positive |
| TC-074-15 | API status line: ok, degraded (503) and unavailable | High | Positive |
| TC-074-16 | Users, runs and upload panels show loading, empty and error states; 401 → login | Medium | Negative |

### TC-074-01 Admin sees app bar with "Admin" current, data bar, `<h1>` "Admin" and the three tabs

| Step | Action | Expected Result |
|---|---|---|
| 1 | Sign in as `admin@example.com`; click "Admin" in the app bar. | URL `/admin`; tab title "Admin – EchoWell". |
| 2 | Inspect the app bar links. | "Admin" link has `aria-current="page"`. |
| 3 | Read the data bar. | "Test data only (pipeline test data v0.1, Oct 1–30, 2026). No real residents. No audio is stored or played anywhere in EchoWell." |
| 4 | Read the heading and the tab list. | `<h1>` "Admin"; `role="tablist"` named "Admin sections" with `role="tab"` buttons "Users", "Pipeline runs", "Upload data"; "Users" selected by default (`aria-selected="true"`). |
| 5 | Check the selected tab style in light and dark scheme. | Selected tab uses `--link` colour (readable in both schemes). |

### TC-074-02 Clinician and researcher see the access-denied state and no admin API call

| Step | Action | Expected Result |
|---|---|---|
| 1 | Sign in as `clinician@example.com`; check the app bar. | No "Admin" link. |
| 2 | Open developer tools Network panel, clear it, then type `http://localhost:3001/admin` in the address bar. | `<h1>` "You do not have access to this page." and link "← Resident list"; URL stays `/admin` (no redirect). |
| 3 | Inspect the Network panel. | No request to `/api/v1/users`, `/api/v1/pipeline/runs`, `/api/v1/ingest` or `/api/v1/health` from the page. |
| 4 | Click "← Resident list". | `/residents` opens. |
| 5 | Repeat steps 2–3 as `researcher@example.com`. | Same access-denied state, no admin API call. |
| 6 | `curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/v1/users -H "Authorization: Bearer $CLINICIAN_TOKEN"`. | `403`. |

### TC-074-03 Tabs: arrow keys, Home/End and `?tab=` URL state

| Step | Action | Expected Result |
|---|---|---|
| 1 | As admin on `/admin`, Tab to the "Users" tab and press ArrowRight. | "Pipeline runs" is selected and focused; URL becomes `/admin?tab=runs`. |
| 2 | Press ArrowRight, then ArrowRight again. | "Upload data" (`?tab=upload`), then wraps to "Users" (`?tab=users`). |
| 3 | Press ArrowLeft; then Home; then End. | "Upload data"; "Users"; "Upload data". |
| 4 | Open `http://localhost:3001/admin?tab=runs` directly. | "Pipeline runs" tab selected on load. |
| 5 | Open `http://localhost:3001/admin?tab=unknown`. | "Users" tab selected (fallback). |

### TC-074-04 Users tab lists the seeded users with the five columns

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/admin?tab=users`. | Table headers "Email", "Display name", "Role", "Active", "Last sign-in" and a hidden "Actions" header. |
| 2 | Read the rows. | Rows for `admin@example.com` (Role "Admin"), `clinician@example.com` ("Clinician"), `researcher@example.com` ("Researcher"); Active "Yes" for all three. |
| 3 | Read "Last sign-in" of a user who never signed in. | "Never"; the admin row shows the facility-local time of the current sign-in. |
| 4 | `SELECT email, role, active, last_login_at FROM users ORDER BY email;` | Same 3 users, roles `admin`/`clinician`/`researcher`, `active = true`; values match the table. |

### TC-074-05 Add a user through the form

| Step | Action | Expected Result |
|---|---|---|
| 1 | On the Users tab, check the "Add user" form. | Fields with visible labels "Email", "Display name", "Role" (options "Admin", "Clinician", "Researcher"), "Temporary password" (type `password`). |
| 2 | Enter Email `qa-user01@example.com`, Display name `QA User 01`, Role "Researcher", and a generated temporary password of 12–128 characters (e.g. from `openssl rand -base64 18`; do not record it); click "Add user". | Button shows "Adding user…" while sending; then status message "qa-user01@example.com was added." announced; form cleared. |
| 3 | Check the Network panel. | `POST /api/v1/users` returned 201; the password is not shown anywhere on the page afterwards. |
| 4 | Check the users table. | New row `qa-user01@example.com`, "QA User 01", "Researcher", "Yes", "Never". |
| 5 | `SELECT role, active FROM users WHERE email = 'qa-user01@example.com';` and `SELECT action FROM audit_logs WHERE action = 'user.created' ORDER BY occurred_at DESC LIMIT 1;` | `researcher`, `true`; one `user.created` audit row. |

### TC-074-06 Duplicate e-mail shows the 409 error under the Email field; policy and required-field errors

| Step | Action | Expected Result |
|---|---|---|
| 1 | Submit "Add user" with Email `clinician@example.com`, any display name, role, and a valid generated password. | API 409 `EMAIL_ALREADY_EXISTS`; under the Email field: "A user with this email already exists."; field linked with `aria-describedby`. |
| 2 | Submit Email `qa-user02@example.com` with a temporary password of fewer than 12 characters. | API 422 `PASSWORD_POLICY_VIOLATION`; under "Temporary password": the API message or "This password does not meet the password rules." |
| 3 | Submit the form with all fields empty. | "This field is required." under each empty field; no `POST /api/v1/users` request is sent. |
| 4 | Simulate offline (developer tools → Network → Offline) and submit valid values. | Above the submit button: "Could not save. Check your connection and try again." |
| 5 | `SELECT count(*) FROM users WHERE email IN ('qa-user02@example.com');` | `0`. |

### TC-074-07 Deactivate asks for confirmation before `PATCH`; reactivate; role change; last admin protected

| Step | Action | Expected Result |
|---|---|---|
| 1 | On the `qa-user01@example.com` row (from TC-074-05) click "Deactivate" (accessible name "Deactivate qa-user01@example.com"), with the Network panel open. | Confirmation "Deactivate qa-user01@example.com? They will not be able to sign in." with "Deactivate" and "Cancel"; no `PATCH` request yet. |
| 2 | Click "Cancel". | Dialog closes; no `PATCH`; Active still "Yes". |
| 3 | Click "Deactivate" again and confirm. | `PATCH /api/v1/users/{id}` 200; message "qa-user01@example.com updated."; Active "No"; button now "Reactivate". |
| 4 | Click "Reactivate". | `PATCH` 200; Active "Yes". |
| 5 | Change the role select "Role for qa-user01@example.com" to "Clinician". | `PATCH` 200; Role "Clinician". |
| 6 | Try to deactivate your own account `admin@example.com`, then run `npx vitest run tests/pages/admin.test.tsx -t "LAST_ADMIN"`. | Own account: 403 `FORBIDDEN` and above the button "You cannot change your own role or deactivate yourself."; admin stays active. Page test: 409 `LAST_ADMIN` shows "At least one active admin must remain." |
| 7 | `SELECT active, role FROM users WHERE email='qa-user01@example.com';` and `SELECT count(*) FROM audit_logs WHERE action='user.updated';` | `true`, `clinician`; at least 3 `user.updated` rows; no row deleted from `users`. |

### TC-074-08 Upload SRC-05 shows "Accepted 283 · Rejected 0 · Duplicates 2"

| Step | Action | Expected Result |
|---|---|---|
| 1 | Prepare the roster-only database (Preconditions, `--master-only`), sign in as admin, open `/admin?tab=upload`. | Upload tab shown. |
| 2 | Choose `tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv` in "CSV file (pipeline input format v0.1)" and click "Upload". | Button shows "Uploading…"; `POST /api/v1/ingest` (multipart field `file`) returns 202. |
| 3 | Wait for the result. | `GET /api/v1/ingest/batches/{id}` is polled; text "Accepted 283 · Rejected 0 · Duplicates 2"; no rejections table rows. |
| 4 | `SELECT source, record_count, accepted_count, rejected_count, duplicate_count FROM ingest_batches ORDER BY received_at DESC LIMIT 1;` | `csv_upload`, 283, 283, 0, 2. |
| 5 | `SELECT count(*) FROM raw_sessions;` and `SELECT action FROM audit_logs WHERE action='ingest.batch.received';` | 283; one `ingest.batch.received` row. |
| 6 | Upload the same file again. | "Accepted 283 · Rejected 0 · Duplicates 283" (re-upload is all duplicates). |

### TC-074-09 Upload legacy SRC-06 shows the whole-file rejection and stores nothing

| Step | Action | Expected Result |
|---|---|---|
| 1 | Record `SELECT count(*) FROM raw_sessions;` and `SELECT count(*) FROM ingest_batches;`. | Baseline counts noted. |
| 2 | On the Upload tab choose `tests/fixtures/legacy/echowell_mock_data_500.csv` and click "Upload". | API 422 `CSV_HEADER_MISMATCH`. |
| 3 | Read the message. | "The file was not accepted: <detail>. Nothing was stored." (no doubled full stop) and a list of the `errors[]` messages, including the extra column `speech_feature_1` and the missing `loudness_dbfs`. |
| 4 | Repeat the counts of step 1. | Both counts unchanged. |

### TC-074-10 Upload tab synthetic-data line, "Choose a CSV file first." and no master-data controls

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/admin?tab=upload`. | Line "Only synthetic or test data may be uploaded to this environment."; file input accepts `.csv` (`accept=".csv,text/csv"`). |
| 2 | Click "Upload" with no file chosen. | "Choose a CSV file first."; no `POST /api/v1/ingest`. |
| 3 | Visit all three tabs and search for "Add resident", "device", "assignment", "API key". | No control to create or edit residents, devices, device assignments or API keys. |

### TC-074-11 Pipeline runs tab lists at most 50 runs newest first with all columns

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/admin?tab=runs` on the seeded stack with the Network panel open. | `GET /api/v1/pipeline/runs?limit=50` returns 200. |
| 2 | Read the table "Pipeline runs table". | Columns "Started", "Finished", "Trigger", "Profile", "Status", "As of", "Counts", "Warnings"; the seed run shows Trigger "Manual", Profile `test_v0_1`, Status "Succeeded", Counts in the form "Arrivals <n> · Usable <n> · Scored <n> · Residents <n> · Alarms opened <n>" (labels in this fixed order, only those present in `counts`), values equal to `counts` of the run in the API. |
| 3 | Compare "Started"/"Finished" with the API `started_at`/`finished_at`. | Shown in facility-local time (America/Chicago). |
| 4 | Run `npx vitest run tests/pages/admin.test.tsx -t "newest first"` and `npx vitest run components/AdminPanel -t "keeps 50"`. | Pass: newest `started_at` first, at most 50 rows. |
| 5 | `SELECT trigger, status, config_profile FROM pipeline_runs ORDER BY started_at DESC LIMIT 50;` | Same order and values as the table. |

### TC-074-12 "Run pipeline now" offers only `meta.pipeline_profile` and polls the run every 5 s

| Step | Action | Expected Result |
|---|---|---|
| 1 | On the Runs tab, open the "Profile" select. | Exactly one option: `test_v0_1` (= `meta.pipeline_profile`). |
| 2 | Click "Run pipeline now". | Button shows "Starting…"; `POST /api/v1/pipeline/run` returns 202 with `pipeline_run_id`. |
| 3 | Watch the Network panel and the status text. | "Pipeline run started. Status: Running (refreshed every 5 seconds)." while running; `GET /api/v1/pipeline/runs/{id}` repeats about every 5 s; polling stops at a terminal status with "Pipeline run succeeded." |
| 4 | `SELECT trigger, status FROM pipeline_runs ORDER BY started_at DESC LIMIT 1;` and the latest `pipeline.run.started` audit row. | `manual`, `succeeded`; one new `pipeline.run.started` row. |

### TC-074-13 Run errors 409 `PIPELINE_RUN_IN_PROGRESS` and 422 `PROFILE_NOT_ALLOWED`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s -X POST http://localhost:8000/api/v1/pipeline/run -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' -d '{"scope":"all","profile":"production"}'`. | 422 with `code` `PROFILE_NOT_ALLOWED`. |
| 2 | Run `npx vitest run tests/pages/admin.test.tsx -t "Pipeline"` and inspect the error mapping in `RunsTab.tsx`. | 409 `PIPELINE_RUN_IN_PROGRESS` shows "A pipeline run is already in progress. Try again when it has finished."; 422 `PROFILE_NOT_ALLOWED` shows "This profile is not allowed in this environment."; other failures "Could not start the pipeline run. Check your connection and try again." |

### TC-074-14 Failed-latest-run banner and "Nightly run missing for <date>" banner

| Step | Action | Expected Result |
|---|---|---|
| 1 | On the seeded local stack (no nightly run exists) open `/admin`. | Yellow banner `role="alert"` "Nightly run missing for <Mon D>", where the date is the facility-local date of now − 2 h (the latest local date whose 02:00 has passed). |
| 2 | `SELECT count(*) FROM pipeline_runs WHERE trigger='nightly' AND status='succeeded' AND started_at >= now() - interval '26 hours';` | `0`, which is why the banner shows. |
| 3 | Run `npx vitest run tests/pages/admin.test.tsx -t "hides the nightly banner"`. | With a succeeded nightly run started within 26 h, no "Nightly run missing" banner. |
| 4 | Run `npx vitest run tests/pages/admin.test.tsx -t "latest run failed"`. | Red banner "The latest pipeline run failed (started <time>)." while the most recent run of any trigger is `failed`. |

### TC-074-15 API status line: ok, degraded (503) and unavailable

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s http://localhost:8000/api/v1/health`. | 200; JSON with `status` `ok`, `database` `ok` and a `version`. |
| 2 | Scroll to the end of `/admin`. | Line (14px, `--muted`) "API status: ok · version <version>" with the `version` of step 1. |
| 3 | `docker compose stop db`, wait 10 s, `curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/api/v1/health`, then reload `/admin`. | `503`; line "API status: degraded (database unavailable) · version <version>". |
| 4 | `docker compose stop backend` and reload `/admin`. | Line "API status: unavailable". |
| 5 | `docker compose start db backend` and wait for health 200. | Line returns to "API status: ok · version <version>". |

### TC-074-16 Users, runs and upload panels show loading, empty and error states; 401 → login

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `npx vitest run tests/pages/admin.test.tsx`. | All tests pass, including "shows the empty and error states", "shows the users loading and empty states", "shows a network error with its reference". |
| 2 | Check the expected texts in those tests. | "Loading users…", "No users yet.", "No pipeline runs yet.", "Could not load pipeline runs. Check your connection and try again.", upload network error "Could not upload the file. Check your connection and try again." with "Reference: <id>". |
| 3 | In a private window open `http://localhost:3001/admin`. | Redirect to `/login`. |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/users` as admin / as clinician | 200 list of users / 403 |
| 2 | `POST /api/v1/users` with an existing e-mail | 409 `EMAIL_ALREADY_EXISTS` (RFC 7807, `type` `urn:echowell:error:EMAIL_ALREADY_EXISTS`) |
| 3 | `POST /api/v1/users` with a password under 12 characters | 422 `PASSWORD_POLICY_VIOLATION` |
| 4 | `PATCH /api/v1/users/{id}` `{"active": false}` | 200; user `active` false |
| 5 | `GET /api/v1/pipeline/runs?limit=50` | 200; `items` newest first; at most 50 |
| 6 | `POST /api/v1/pipeline/run` `{"scope":"all","profile":"production"}` on the local stack | 422 `PROFILE_NOT_ALLOWED` |
| 7 | `POST /api/v1/ingest` multipart `file`=SRC-05 on a roster-only database | 202; `accepted` 283, `rejected` 0, `duplicates` 2 |
| 8 | `POST /api/v1/ingest` with SRC-06 | 422 `CSV_HEADER_MISMATCH` with `errors[]` |
| 9 | `GET /api/v1/health` with db up / db stopped | 200 `status` ok / 503 degraded |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT email, role, active FROM users;` after TC-074-05/07 | New user present, never deleted; role and active match the UI |
| 2 | `SELECT action, count(*) FROM audit_logs WHERE action IN ('user.created','user.updated','ingest.batch.received','pipeline.run.started') GROUP BY action;` | One row per performed action type with counts matching the actions taken |
| 3 | `SELECT accepted_count, rejected_count, duplicate_count FROM ingest_batches ORDER BY received_at DESC LIMIT 1;` after TC-074-08 | 283, 0, 2 |
| 4 | `SELECT count(*) FROM raw_sessions;` before/after TC-074-09 | Unchanged |
| 5 | `SELECT trigger, status FROM pipeline_runs ORDER BY started_at DESC LIMIT 1;` after TC-074-12 | `manual`, `succeeded` |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Clinician opens `/admin` (TC-074-02) | "You do not have access to this page." with "← Resident list"; no admin API call |
| 2 | Duplicate e-mail / short password / empty form (TC-074-06) | Field errors; no user created |
| 3 | Deactivate own account / last admin (TC-074-07 step 6) | 403 "You cannot change your own role or deactivate yourself." / 409 "At least one active admin must remain." |
| 4 | Upload SRC-06 (TC-074-09) | "The file was not accepted: <detail>. Nothing was stored."; nothing stored |
| 5 | Upload with no file (TC-074-10) | "Choose a CSV file first." |
| 6 | Run with a profile not allowed (TC-074-13) | "This profile is not allowed in this environment." |
| 7 | Database or backend down (TC-074-15) | "API status: degraded (database unavailable) · version <version>" / "API status: unavailable" |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-074-AC-01 | `/admin?tab=runs` lists at most 50 runs newest first with trigger, profile, status, local start/finish, as-of, counts and warnings | TC-074-11 |
| FEAT-074-AC-02 | Failed latest run shows the failure banner; no succeeded nightly run in 26 h shows "Nightly run missing for <date>" | TC-074-14 |
| FEAT-074-AC-03 | Uploading SRC-05 shows "Accepted 283 · Rejected 0 · Duplicates 2" | TC-074-08 |
| FEAT-074-AC-04 | Uploading SRC-06 shows "The file was not accepted: <detail>. Nothing was stored." with the error messages | TC-074-09 |
| FEAT-074-AC-05 | Existing e-mail shows the 409 error under Email; deactivation asks "Deactivate <email>? They will not be able to sign in." before `PATCH` | TC-074-06, TC-074-07 |
| FEAT-074-AC-06 | Upload tab shows the synthetic-data line; no resident, device, assignment or API-key control exists | TC-074-10 |
| FEAT-074-AC-07 | With health 503 degraded the line reads "API status: degraded (database unavailable) · version <version>" | TC-074-15 |
| FEAT-074-AC-08 | Admin sees app bar with "Admin" current, data bar, `<h1>` "Admin"; clinician sees "You do not have access to this page." with "← Resident list" | TC-074-01, TC-074-02 |

## Test Data Requirements

- `test_v0_1` seed (R01–R10, three seeded users, the seed's manual pipeline run); roster-only variant via `seed test_v0_1 --reset --master-only` for TC-074-08.
- SRC-05 `tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv`; SRC-06 `tests/fixtures/legacy/echowell_mock_data_500.csv`.
- Synthetic new user `qa-user01@example.com` / `QA User 01`; a generated temporary password never written down.
- Environment: `SEED_ADMIN_PASSWORD`, `SEED_CLINICIAN_PASSWORD`, `SEED_RESEARCHER_PASSWORD`, `PIPELINE_PROFILE=test_v0_1`, `PIPELINE_AS_OF`.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-074-FR-01 / UX-210 | FEAT-074 | TC-074-01, TC-074-03 |
| FEAT-074-FR-02 / UX-215, FE-034 | FEAT-074 | TC-074-02 |
| FEAT-074-FR-03 / UX-211, FR-220, E-25, E-26 | FEAT-074 | TC-074-04, TC-074-05 |
| FEAT-074-FR-04 / UX-211, FR-221, E-27 | FEAT-074 | TC-074-07 |
| FEAT-074-FR-05 / FE-079, UX-207 | FEAT-074 | TC-074-06, TC-074-07 |
| FEAT-074-FR-06 / UX-212, LOG-112, FR-225, E-31 | FEAT-074 | TC-074-11 |
| FEAT-074-FR-07 / UX-212, E-20, E-21, D-96 | FEAT-074 | TC-074-12, TC-074-13 |
| FEAT-074-FR-08 / LOG-112, LOG-111, UX-219 | FEAT-074 | TC-074-14 |
| FEAT-074-FR-09 / UX-213, FR-222, FE-072, E-06, E-07 | FEAT-074 | TC-074-08 |
| FEAT-074-FR-10 / UX-217 | FEAT-074 | TC-074-09 |
| FEAT-074-FR-11 / UX-214 | FEAT-074 | TC-074-10 |
| FEAT-074-FR-12 / UX-218 | FEAT-074 | TC-074-10 |
| FEAT-074-FR-13 / UX-216, E-01 | FEAT-074 | TC-074-15 |
| TST-094 (page states, 401) | FEAT-074 | TC-074-16 |
| E2E-14 | FEAT-074 | TC-074-02 |
