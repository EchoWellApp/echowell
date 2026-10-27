# FEAT-080 E2E, performance and nightly workflows (e2e.yml)

| Field | Value |
|---|---|
| Epic | DevOps & Deployment |
| Build phase | Phase 9 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-078, FEAT-076, FEAT-079 |
| Status | Not Started |

## Purpose

Create `.github/workflows/e2e.yml`, the workflow that runs the end-to-end suite on the Docker Compose `demo` stack for every pull request (Chromium plus accessibility, a required check), runs the full three-browser suite nightly, and hosts the scheduled `performance` and `nightly-validation` (random-order and robustness) jobs plus the `lighthouse` job, opening a `ci-failure` issue when a scheduled or `main` run fails. It is the only place where the isolated `echowell_demo` database is prepared for the `@isolated` scenarios.

## Business Context

- BR-12, BR-13, BR-14, SRC-21: the UI behaviour of every page is a merge gate through the `playwright` check (CIC-031, CIC-032, CIC-070).
- BR-15: nightly random-order runs and the multi-seed robustness report watch for hidden order dependence and rule differences (CIC-037, TST-084).
- RSK-07 / contract R8 budgets: nightly performance job (CIC-035).

## Referenced TRDs

- TRD 16 CIC-030, CIC-031, CIC-032, CIC-033, CIC-034, CIC-035, CIC-036, CIC-037, CIC-112, CIC-116, §4.3 outline, §4.10 artifacts.
- TRD 13 TST-004, TST-005, TST-084, TST-100, TST-110, TST-125, TST-150, TST-151.
- TRD 14 TDV-080, TDV-081, TDV-082, TDV-083.
- TRD 15 DEP-017, DEP-119.
- TRD 21 ENV-054.
- TRD 24 D-72, D-73, D-74.

## Scope

- `.github/workflows/e2e.yml` with triggers `pull_request` to `main`, `push` to `main`, `schedule` `0 8 * * *` and `workflow_dispatch`; `permissions: contents: read` (plus `issues: write` only in the failure-reporting step's job).
- Job `playwright` (timeout 20 min): copy `.env.development.example` to `.env`, append a per-run JWT_SECRET, set `RATE_LIMIT_LOGIN=60/minute`, generate masked SEED_ADMIN_PASSWORD, SEED_CLINICIAN_PASSWORD, SEED_RESEARCHER_PASSWORD and SEED_INGEST_API_KEY into `.env` and `$GITHUB_ENV`; `docker compose --profile demo up -d --build --wait db backend frontend-prod`; `seed test_v0_1`; DS-10 loader; install Playwright browsers (Chromium on PR/push, Chromium, Firefox and WebKit on schedule); for each browser project run `npm run test:e2e:readonly -- --project=<p>` then `npm run test:e2e:mutating -- --project=<p>`; then create and provision `echowell_demo`, restart the backend on it with `PIPELINE_AS_OF` empty, `seed test_v0_1 --master-only`, `import-master-data --dir tests/fixtures/seeds/demo_overlay`, and run `npm run test:e2e:isolated`; on failure collect `docker compose logs`; always upload `playwright-report` (14 days) and run `docker compose down -v`.
- Job `performance` (schedule and dispatch only): `postgres:16-alpine` service, `python tests/performance/make_load_dataset.py`, `pytest tests/performance -m performance`, artifact `performance-report` (30 days).
- Job `nightly-validation` (schedule and dispatch only): setup identical to `ci.yml` `backend-test`, `pytest -p randomly tests/unit tests/integration tests/contract tests/security tests/validation` (seed printed), then `python tests/validation/robustness.py` with `continue-on-error: true`; artifact `nightly-validation-report` (30 days).
- Job `lighthouse` (pull requests to `main`, not required): seeded Compose `demo` stack, scripted login, Lighthouse CI on `/residents`.
- Failure reporting: on a failing scheduled or `main` run, open or comment on a GitHub issue labelled `ci-failure` with the `gh` CLI and the default `GITHUB_TOKEN`.

## Out of Scope

- The Playwright specs, configs and setup scripts (FEAT-076); the performance tests and Lighthouse config (FEAT-079); `robustness.py` (Optional FEAT-061, run only when present).
- `ci.yml`, branch protection settings (FEAT-078) beyond the fact that `playwright` is one of the required checks.
- Deploy and uptime workflows (FEAT-085, FEAT-086).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-080-FR-01 | `e2e.yml` shall run on every pull request to `main`, every push to `main`, nightly at 08:00 UTC and on manual dispatch. | CIC-031, TST-151 |
| FEAT-080-FR-02 | The `playwright` job shall run Playwright against the Compose `demo` stack (db, backend, `frontend-prod` on :3001) seeded with `seed test_v0_1` and loaded with DS-10, and shall invoke Playwright only through `test:e2e:readonly`, `test:e2e:mutating` and `test:e2e:isolated`. | CIC-030, D-73 |
| FEAT-080-FR-03 | On pull requests and pushes the main run shall use Chromium only (including `a11y.spec.ts`); on the schedule it shall loop over Chromium, Firefox and WebKit, running read-only then mutating per project. | CIC-031, TST-100, TST-110 |
| FEAT-080-FR-04 | After the main run, the job shall create `echowell_demo` in the same Postgres service, run `provision_login_roles.sql` on it as superuser, restart the backend on it with `PIPELINE_AS_OF` empty and the `echowell_demo` URLs, wait for `/api/v1/health`, run `seed test_v0_1 --master-only` and `import-master-data --dir tests/fixtures/seeds/demo_overlay`, then run `npm run test:e2e:isolated` (Chromium, serial). | CIC-030, D-72, D-73 |
| FEAT-080-FR-05 | The E2E credentials shall be generated per job, masked with `::add-mask::` before use, written to `.env` and `$GITHUB_ENV`, never printed, and never valid on staging or production. | CIC-034, D-71 |
| FEAT-080-FR-06 | The E2E stack `.env` shall set `RATE_LIMIT_LOGIN=60/minute` (APP_ENV `local`). | D-74 (b), ENV-054 |
| FEAT-080-FR-07 | The `performance` job shall run only on schedule and dispatch, generate DS-08 and run `pytest tests/performance -m performance` against a `postgres:16-alpine` service, failing if any contract R8 budget or the sustained-ingest check of TST-190 (NFR-151) fails, and upload `performance-report`. | CIC-035, TST-151, TST-190 |
| FEAT-080-FR-08 | The `nightly-validation` job shall run only on schedule and dispatch with the `backend-test` setup, run the pytest suites in random order with the seed printed, then, when `tests/validation/robustness.py` exists (Optional FEAT-061), run it as an informational step (`continue-on-error: true`), and upload `nightly-validation-report`; it is not a required check. | CIC-037, TST-005, TST-084, TDV-083 |
| FEAT-080-FR-09 | The `lighthouse` job shall run on pull requests to `main`, use `@lhci/cli` 0.14.x with the desktop preset on `/residents` of the seeded `demo` stack after `frontend/tests/lighthouse/login.js`, and fail below Performance 80 or above LCP 2.5 s; it is not a required check. | CIC-116, TST-125 |
| FEAT-080-FR-10 | A failing scheduled or `main` run shall open or comment on a GitHub issue labelled `ci-failure` via `gh` with `issues: write` scoped to that job. | CIC-033, TST-151 |
| FEAT-080-FR-11 | Each job (`playwright`, `performance`, `lighthouse`, `nightly-validation`) shall define `timeout-minutes` ≤ 20 and complete within 20 minutes. | CIC-111, CIC-112 |
| FEAT-080-FR-12 | `playwright-report` (HTML report, failure traces, `e2e-compose.log`) shall be uploaded with 14-day retention and contain only synthetic data. | TRD 16 §4.10, CIC-101 |
| FEAT-080-FR-13 | The job id `playwright` shall be the required status check name used by branch protection. | CIC-070, TST-150 |

## Inputs

- Specs and scripts from FEAT-076; performance suite and Lighthouse config from FEAT-079; `robustness.py` from FEAT-061 when present (Optional, soft dependency); Compose file and templates from FEAT-077; `ci.yml` setup steps from FEAT-078.
- Repository checkout with `database/`, `tests/fixtures/` (mounted read-only into the backend, DEP-119).

## Outputs

- `.github/workflows/e2e.yml`.
- Artifacts `playwright-report`, `performance-report`, `nightly-validation-report`, Lighthouse results.
- `ci-failure` issues or comments on failures.

## Data Flow

Trigger → `playwright` job builds the stack → seed and DS-10 → per-project `globalSetup` re-seeds → read-only and mutating groups → `echowell_demo` prepared → isolated group → report upload → stack torn down. Schedule → `performance` and `nightly-validation` jobs in parallel on their own PostgreSQL services → reports uploaded → failure → `ci-failure` issue.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-078, FEAT-076, FEAT-079

- [FEAT-078](FEAT-078-Full-CI-Quality-Security-And-Hygiene.md) Full CI gates and branch protection (`backend-test` setup reused; `playwright` registered as required).
- [FEAT-076](FEAT-076-End-To-End-Test-Suite-And.md) End-to-end suite and isolation harness.
- [FEAT-079](FEAT-079-Performance-And-Load-Tests.md) Performance and load tests, Lighthouse config.
- Soft dependency (not required, BACKLOG.md §8.2): [FEAT-061](FEAT-061-False-Alarm-Robustness-Check.md) False-alarm robustness check; the nightly job runs it only when `tests/validation/robustness.py` exists.

Features that build directly on this one (BACKLOG.md §4): FEAT-086.

## Database Impact

- Ephemeral databases only: `echowell` (main E2E, reset per invocation), `echowell_demo` (isolated run) in the Compose `db` service, and `echowell_test` in the `performance` and `nightly-validation` service containers.
- No hosted database is used; no table is created by this feature's own code.

## API Impact

None exposed. The workflow calls `GET /api/v1/health` while waiting for the backend; the suites call the API as described in FEAT-076 and FEAT-079.

## Frontend Impact

None in application code. The workflow builds `frontend-prod` with `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` and `NEXT_PUBLIC_APP_ENV=local`.

## Analytics Impact

None in code. `nightly-validation` runs the validation suite in random order and the multi-seed robustness check (TDV-080..TDV-083), whose false-alarm rate is informational (about 10 % expected, TDV-081).

## Security Requirements

- No repository secret used; credentials are generated and masked per job (CIC-034); `permissions: contents: read` by default, `issues: write` only where issues are opened (CIC-024, CIC-033).
- Fork PRs receive no secrets; `pull_request_target` is not used (CIC-091).
- Artifacts never contain database dumps or real data (CIC-101).

## Error Handling

- Any failing step fails the job; `docker compose logs` are captured on failure and the stack is always torn down (`docker compose down -v`).
- The robustness step never fails the job (`continue-on-error: true`); its multi-seed mismatches are logged as S2 defects by the team (TDV-082).
- Flaky tests (pass on retry) are reported per TST-101 and tracked per TST-161.

## Logging Requirements

- Workflow logs show step names and timings; secrets are masked (CIC-092).
- The nightly-validation log prints the pytest-randomly seed (CIC-037).
- No application audit rows are produced beyond those the tests themselves create in ephemeral databases.

## Testing Requirements

- Dry run of `e2e.yml` on the Phase 9 checkpoint PR of Block 3 (Chromium path) and one `workflow_dispatch` run covering `performance` and `nightly-validation` (TRD 25 §4.6 Phase 9 Required tests).
- Suites executed: E2E-01..E2E-21, FE-185..FE-193, TST-110, TST-187 (FEAT-076); TST-120..TST-125 (FEAT-079); TDV-080..TDV-083 (FEAT-061).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-080-AC-01 | On a pull request to `main`, the `playwright` job passes in Chromium, including `a11y.spec.ts` and the isolated run, and reports the status check `playwright`. | CIC-030, CIC-031, AC-TST-07 |
| FEAT-080-AC-02 | A `workflow_dispatch` run executes `performance` and `nightly-validation`; `performance` uploads `performance-report` and passes all budgets. Verified by: Test (Dry run of `e2e.yml` on the Phase 9 checkpoint PR of Block 3 (Chromium path) and one `workflow_dispatch` run covering `performance` and `nightly-validation` (TRD 25 §4.6 Phase 9 Required tests)). | CIC-035, AC-CIC-10 |
| FEAT-080-AC-03 | The `nightly-validation` log contains the pytest-randomly seed, and a deliberately failing robustness step does not fail the job; without `tests/validation/robustness.py` the step is skipped and the job still passes. | CIC-037, AC-TDV-09 |
| FEAT-080-AC-04 | A forced failure on a scheduled run creates or comments on an issue labelled `ci-failure`. Verified by: Demo (the demo method of CIC-033, applied to the condition stated in the criterion). | CIC-033 |
| FEAT-080-AC-05 | `grep -n "secrets\." .github/workflows/e2e.yml` returns nothing, and every job has `timeout-minutes` ≤ 20. Verified by: Inspection (run the command in the criterion and check its output). | CIC-034, CIC-111 |
| FEAT-080-AC-06 | The nightly `e2e.yml` run passes on `main` for 3 consecutive nights before 15 Nov 2026. Verified by: Test (Dry run of `e2e.yml` on the Phase 9 checkpoint PR of Block 3 (Chromium path) and one `workflow_dispatch` run covering `performance` and `nightly-validation` (TRD 25 §4.6 Phase 9 Required tests)). | AC-CIC-09 |
| FEAT-080-AC-07 | The `lighthouse` job runs on a pull request and reports Performance ≥ 80 and LCP ≤ 2.5 s for `/residents`. | CIC-116, TST-125 |

## Definition of Done

- All FEAT-080 acceptance criteria pass.
- All FEAT-080 acceptance criteria demonstrated (FEAT-080-AC-06 recorded later in the readiness checklist of FEAT-087).
- Workflow passes `actionlint` (or equivalent YAML validation) and uses actions pinned per CIC-025.
- Batch report entry (AGT-022).

## Implementation Notes

- `docker compose up --wait` needs healthchecks on `backend` and `frontend-prod` (FEAT-077).
- The backend start command migrates on start, so the `echowell_demo` restart via `docker compose run -d --no-deps --service-ports` applies `alembic upgrade head` there.
- Keep the loop `for p in ...` so each browser project is one Playwright invocation, which triggers `global-setup.ts` and therefore a fresh seed (D-73).
- If the repository becomes private, the nightly E2E should become weekly to stay within free minutes (TRD 16 §5); record such a change as a TRD 24 decision.
