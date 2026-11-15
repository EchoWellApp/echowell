# Block 5 Report — Test Cases

Block 5 "Test Cases", one PR (branch `docs/test-cases`, created from `main` at `6e58520` after GitHub PR #32 was merged on 15 November 2026) · Prompt: `specs/prompts/Test_Case_Generation_Prompt.md` · Plan: `specs/backlog/IMPLEMENTATION_ROADMAP.md` §7 · Decisions: TRD 24 D-106 (output folder), D-174 (missing tests of the checkpoint 9 audit), D-180 (no Block 4 PR; hosted verification items become Block 5 validation activities).

**Block 5 adds no feature and changes no application code.** It adds manual QA test cases (`specs/testing/test-cases/`), the automated tests the checkpoint 9 audit found missing (`tests/`), and refreshes the tracking documents. No migration, re-seed or change to the Render, Netlify or Neon deployments (D-170). Nothing was deployed.

## 1. Result

| Measure | Value |
|---|---|
| Test-case files | 97, one per feature file FEAT-001..FEAT-097 (`TC-NNN-<Feature-Name>.md`) |
| Test cases | 1,332 (IDs `TC-NNN-MM`) |
| Feature acceptance criteria covered | All of them: every `FEAT-NNN-AC-xx` of every feature file appears in its file's Acceptance Criteria Validation table with at least one test case (checked by script, 0 missing) |
| Positive and negative cases | Every file has at least one of each |
| Hosted cases (run by the team on the deployed origins) | 55 cases in 18 files, written with placeholders (`<FRONTEND_URL>`, `<API_BASE_URL>`, …); mainly TC-085..TC-090 |
| Missing tests of the checkpoint 9 audit (D-174) | All added and passing (section 3) |
| Test data | Synthetic only: `test_v0_1` (R01–R10), DS-07, DS-08, TRD fixtures (R11, N01, D01, …); study IDs only; no password, secret, hosted URL or audio in any file |

## 2. Deliverables

| File | Content |
|---|---|
| `specs/testing/test-cases/README.md` | Conventions: file names and IDs, environments, data rules, file structure, coverage check |
| `specs/testing/test-cases/TC-001-….md` … `TC-097-….md` | One file per feature: Feature Description, Preconditions, Manual Test Cases (summary and per-case steps), API Validation, Database Validation, Negative Test Cases, Acceptance Criteria Validation, Test Data Requirements, Traceability (TRD → FEAT → TC) |
| `tests/integration/api/test_admissions.py` | TST-185 (two tests) |
| `tests/integration/test_seed_logins.py` (new) | TST-188 (two tests) |
| `tests/integration/test_cli_pipeline.py` | TST-194 |
| `tests/integration/test_cli_credentials.py` | TST-195 (five refusals) |
| `tests/integration/pipeline/test_runner_persistence.py` | FR-110 superseded-by-rebuild closure; FR-296 data-alert history and resolution |
| `tests/performance/test_overview_queries.py` (new) | DB-040, DB-042 |
| `specs/backlog/BACKLOG.md` §10, `IMPLEMENTATION_ROADMAP.md` §2.1, `MVP_READINESS_CHECKLIST.md` (C.02, J.02, MVP-02) | Tracking refreshed (D-95, D-104) |

Notes on the test cases:
- Features FEAT-092..FEAT-097 are Not Started; their files carry the line "Status: Not Started" and run only once the feature is built.
- Where an acceptance criterion needs fault injection, a frozen clock, the production profile or a fixture that the demo data does not contain, the test case runs the named existing automated test and lists what to check in its result.
- Some file names keep the v0.1 feature titles (feature file names are never renamed, TRD 25 §4.2); each file's heading uses the current title.

## 3. Missing tests added (D-174)

| Test | Requirement IDs | Result |
|---|---|---|
| `test_new_admission_moves_to_the_resident_list_when_its_baseline_forms`, `test_cohort_change_shares_the_pipeline_transaction` | TST-185, BR-14, FR-205, DB-025, DB-013 | Pass |
| `test_seeded_users_log_in_with_their_role`, `test_seeded_emails_validate_against_login_request` | TST-188, DB-056, DB-057, D-71 | Pass |
| `test_run_pipeline_scope_all_matches_an_api_full_run` | TST-194, TST-050, BR-15 | Pass |
| `test_create_user_refuses_an_invalid_email`, `…_an_email_already_in_use`, `…_an_unknown_role`, `test_create_api_key_refuses_an_unknown_device`, `test_revoke_api_key_refuses_an_unknown_name` | TST-195, D-86, SEC-016..SEC-024 | Pass |
| `test_rebuild_without_the_first_crossing_supersedes_the_alert` | FR-110, CUS-015 | Pass |
| `test_data_alert_history_and_resolution` | FR-296, ANL-060, DB-036 | Pass |
| `test_resident_list_queries_within_150_ms_on_ds08` | DB-040 | Pass (p95 49.8 ms against 150 ms) |
| `test_resident_scoped_queries_use_no_seq_scan_on_ds08` | DB-042 | Pass (after `ANALYZE`; `enable_seqscan` unchanged) |

TST-049, the first of the D-174 tests, was merged separately with GitHub PR #38 (merged 12 November 2026). Local run: `pytest tests/integration` 303 passed against PostgreSQL 16; `pytest -m performance tests/performance` 17 passed and 1 failed — the existing `test_ingest_sustained.py::test_sustained_10_records_per_second_for_60_s` (untouched), whose 60-second schedule slipped to 65–70 s on the slower local machine; it runs in the nightly performance job, not on PRs. `ruff check`, `ruff format --check`, `mypy analytics backend` and `lint-imports` pass. No application defect was found.

Limit: TST-188 checks the e-mail format with the OpenAPI schema and jsonschema's format checker; `email-validator` (Pydantic `EmailStr`) is not a project dependency, so the stricter check DB-057 describes is not exercised. No dependency was added.

## 4. Hosted validation activities (D-180)

FEAT-089 (backups, restore drill, rollback) and FEAT-090 (demo acceptance, local fallback rehearsal) and the hosted checks of FEAT-081..FEAT-088 are written as test cases marked **Hosted**. They need the deployed URLs and platform access, which are held by the team and are not in the repository; they were not run from this branch. Their results are recorded when the team runs them. Two of them touch a deployment setting and need the algorithm lead's approval first (section 6, Q-2, Q-3).

Hosted cases that will fail until the team acts (state on 15 November 2026):
- the four repository variables `STAGING_API_BASE_URL`, `STAGING_FRONTEND_URL`, `PRODUCTION_API_BASE_URL`, `PRODUCTION_FRONTEND_URL` are not set (TC-088-03; `uptime.yml` skips its checks and `deploy-staging.yml` stops at "Wait for staging" until then);
- `docs/reports/DEPLOYMENT_REPORT.md` does not exist (TC-088-07);
- `docs/deployment.md` still reads "recorded in Phase 10" for the "Verified on" dates, the Neon restore window and the drill and rehearsal records (TC-085-08, TC-089-01).

## 5. Findings recorded in the test cases

Each finding is a one-line "Note:" under its test case; the test case follows the TRD. None blocks the demo; none was fixed in this PR (Block 5 changes no application code).

**Code differs from the TRD**

| Test case | Finding |
|---|---|
| TC-013-17 | Migration `0003` creates an index with plain `CREATE INDEX`; DB-046 asks for `CONCURRENTLY` (already S4 in the checkpoint 9 audit) |
| TC-015-11, TC-021-03 | `access.denied` audit rows write `entity_type` and `entity_id` as NULL; TRD 12 §4.12 says `'route'` and the route template (`backend/api/deps.py:196`) |
| TC-022-05 | Locally the rate-limit key reads `X-Forwarded-For` when present; API-103 says the socket peer (`backend/core/rate_limit.py:35`) |
| TC-025-03, TC-028-01 | 404 and `UNKNOWN_RESIDENT` detail texts differ from the TRD 19 wording |
| TC-026-15 | No `ingest_batch_completed` log event (LOG-053) |
| TC-056-01 | Exception warnings do not start with the stage name (LOG-062/063; `backend/services/pipeline_runner.py:274`) |
| TC-056 | `data_alerts_updated` log carries open counts only (LOG-115) |
| TC-055 | `config.changed` audit puts `profile` and `key` in `entity_id`, not `details` (`backend/cli.py:599-601`) |
| TC-061-11 | The robustness script stops on a generator failure instead of recording it and continuing (`tests/validation/robustness.py:47`) |
| TC-075-06 | Light-theme tokens `--c-aside` (2.23:1) and `--c-quar` (2.94:1) are below the 3:1 of UX-224 (already in the checkpoint 9 audit) |
| TC-078-12 | The CI forbidden-term scan checks `frontend/lib/wording.ts`, which now only re-exports; the texts in `frontend/lib/wording/*.ts` are not scanned |
| TC-090-08 | The documented demo fallback copies `PIPELINE_AS_OF=2026-10-30T15:00:00-05:00`, so a check-in posted during the rehearsal is ignored; the case runs with `PIPELINE_AS_OF` empty, as `e2e.yml` does |

**Documentation gaps**: `docs/deployment.md` has no secret inventory with owner and rotation interval (SEC-055..SEC-057), no per-provider encryption-at-rest statement (SEC-063) and no Render Postgres fallback procedure (DEP-035) (TC-083-06, TC-083-11, TC-083-13, TC-081-15).

**Feature files older than the TRD** (the test cases follow the TRD): FEAT-004 (fonts; now Source Sans 3 from a committed file, D-168), FEAT-021-AC-04 (33 vs 34 matrix rows), FEAT-023 (`device_assignment_mismatch` moved to the pipeline, D-125), FEAT-024 (`ingest:write` key on `POST /pipeline/run` answers 403, not 401), FEAT-062-FR-18 (429/503 texts replaced by LOG-081, D-179), FEAT-077-FR-01 (`database/` is in the image), FEAT-086-AC-05 (smoke items), FEAT-088 (staging service name `echowell-api`, D-154), FEAT-093, FEAT-095; several feature files name test files that live at other paths. `MVP_READINESS_CHECKLIST.md` E.04 still quotes the v0.1 "Baseline forming" text.

## 6. Questions for the algorithm lead

| # | Question |
|---|---|
| Q-1 | The findings of section 5 are recorded, not fixed (Block 5 changes no application code). Should they become a follow-up fix PR after Block 5, or stay as recorded S3/S4 findings? |
| Q-2 | TC-089-06 rehearses a rollback on **staging** (production untouched; the rehearsal ends in its starting state). Is staging the right place, and may the team run it? |
| Q-3 | TC-089-07 (FEAT-089-AC-01, a deploy with a failing health check) temporarily changes the staging health-check path. If no temporary setting change is allowed (D-170), it is recorded as not executed. Allowed or not? |
| Q-4 | Should the out-of-date feature files (section 5) be aligned with the TRD in a docs PR, or left as history (the TRD is the source of truth)? |
| Q-5 | Who on the team runs the Hosted cases and records the results, and should the four hosted-URL repository variables be set now (setting them changes no deployment)? |
