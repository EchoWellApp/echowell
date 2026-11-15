# E2E, performance and nightly workflows

## Feature Description

`.github/workflows/e2e.yml` runs the end-to-end suite on the Docker Compose `demo` stack (FEAT-080; TRD 16 CIC-030..CIC-037, CIC-112, CIC-116, §4.3, §4.10; TRD 13 TST-100, TST-110, TST-125, TST-150, TST-151; TRD 24 D-72..D-74). Triggers: every pull request to `main`, every push to `main`, nightly at 08:00 UTC (`cron: "0 8 * * *"`) and manual dispatch. Job `playwright` (the required check) seeds `test_v0_1` plus DS-10, runs Playwright only through `test:e2e:readonly`, `test:e2e:mutating` and `test:e2e:isolated` — Chromium on PRs and pushes, Chromium/Firefox/WebKit on the schedule and dispatch — then prepares `echowell_demo` and runs the isolated scenarios. Jobs `performance` and `nightly-validation` run only on schedule and dispatch; `lighthouse` runs on pull requests; none of these three is required. Job `ci-failure-issue` opens or comments on a `ci-failure` issue when a scheduled, `main` push or `main` dispatch run fails. Credentials are generated per job and masked; no repository secret is used.

## Preconditions

- GitHub access to the repository (Actions read; permission to run `workflow_dispatch` and open draft PRs); `gh` CLI authenticated.
- Throwaway branches `qa/tc-080-NN` for the negative cases, opened as draft PRs and closed afterwards; nothing is merged and no hosted deployment is touched.
- Optional local reproduction: Docker Compose, Node 20, the `.env` preparation of the `playwright` job steps.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-080-01 | Triggers: PR to `main`, push to `main`, 08:00 UTC schedule, manual dispatch | High | Documentation |
| TC-080-02 | PR run: `playwright` passes in Chromium incl. `a11y.spec.ts` and the isolated run; check named `playwright` | High | Positive |
| TC-080-03 | Dispatch run executes `performance` and `nightly-validation`; `performance-report` uploaded, budgets pass | High | Positive |
| TC-080-04 | `nightly-validation` prints the pytest-randomly seed; robustness step informational or skipped | High | Positive |
| TC-080-05 | A failing scheduled or `main` run opens or comments on a `ci-failure` issue | Medium | Positive |
| TC-080-06 | No `secrets.` in `e2e.yml`; every job `timeout-minutes` ≤ 20 | High | Security |
| TC-080-07 | Nightly run passes on `main` three consecutive nights before 15 Nov 2026 | High | Positive |
| TC-080-08 | `lighthouse` runs on a PR: Performance ≥ 80, LCP ≤ 2.5 s for `/residents` | High | Performance |
| TC-080-09 | Schedule loops Chromium, Firefox, WebKit: read-only then mutating per project | Medium | Positive |
| TC-080-10 | Isolated `echowell_demo` preparation steps | Medium | Positive |
| TC-080-11 | Per-job credentials masked, never printed; `RATE_LIMIT_LOGIN=60/minute` | High | Security |
| TC-080-12 | `playwright-report` artifact: 14-day retention, synthetic data only | Medium | Positive |
| TC-080-13 | Failure path: Compose logs collected, stack always torn down | Medium | Negative |
| TC-080-14 | `performance`, `nightly-validation` skipped on PRs; `lighthouse` skipped on schedule; none required | Medium | Negative |

### TC-080-01 Triggers: PR to `main`, push to `main`, 08:00 UTC schedule, manual dispatch

| Step | Action | Expected Result |
|---|---|---|
| 1 | `sed -n '/^on:/,/^concurrency/p' .github/workflows/e2e.yml` | `pull_request: branches: [main]`, `push: branches: [main]`, `schedule: - cron: "0 8 * * *"`, `workflow_dispatch:`. |
| 2 | `gh run list --workflow e2e.yml --limit 30 --json event --jq '[.[].event] | unique'` | Includes `pull_request`, `push`, `schedule` (and `workflow_dispatch` after TC-080-03). |

### TC-080-02 PR run: `playwright` passes in Chromium incl. `a11y.spec.ts` and the isolated run; check named `playwright`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open a draft PR from `qa/tc-080-02` with a docs-only change. | `E2E` workflow starts with jobs `playwright` and `lighthouse`; `performance`, `nightly-validation` skipped. |
| 2 | Open `playwright` → "Install dependencies and Playwright browsers". | Installs `chromium` only. |
| 3 | Open "Main run, one browser project at a time (TRD 24 D-73)". | One `test:e2e:readonly -- --project=chromium` and one `test:e2e:mutating -- --project=chromium` invocation; both pass; read-only output includes `a11y.spec.ts`. |
| 4 | Open "Isolated run (Chromium, serial; …)". | `npm run test:e2e:isolated` passes E2E-15, TST-187, E2E-19. |
| 5 | Check the PR checks list. | Status check named `playwright` is green. Close the PR. |

### TC-080-03 Dispatch run executes `performance` and `nightly-validation`; `performance-report` uploaded, budgets pass

| Step | Action | Expected Result |
|---|---|---|
| 1 | `gh workflow run e2e.yml --ref main`; open the run. | Jobs `playwright`, `performance`, `nightly-validation` run; `lighthouse` skipped. |
| 2 | `performance` steps. | "Generate DS-08 (100 residents, 10,800 records; never committed)"; "Contract R8 budgets and sustained ingest" runs `pytest -p no:randomly tests/performance -m performance` and passes. |
| 3 | `gh run download <run-id> -n performance-report` | Contains `build/performance.json`; every budget `passed: true`. |

### TC-080-04 `nightly-validation` prints the pytest-randomly seed; robustness step informational or skipped

| Step | Action | Expected Result |
|---|---|---|
| 1 | In the TC-080-03 run, open `nightly-validation` → "Suites in random order". | Header line `Using --randomly-seed=<n>`; suites `tests/unit tests/integration tests/contract tests/security tests/validation` run. |
| 2 | Inspect the step "Multi-seed robustness check". | `if: always() && hashFiles('tests/validation/robustness.py') != ''` and `continue-on-error: true`. |
| 3 | On `qa/tc-080-04a`, make `tests/validation/robustness.py` exit 1 at start; `gh workflow run e2e.yml --ref qa/tc-080-04a`. | Robustness step shows failed (orange), `nightly-validation` job conclusion `success`. |
| 4 | On `qa/tc-080-04b`, delete `tests/validation/robustness.py`; dispatch on that branch. | Robustness step "skipped"; job passes. |
| 5 | Artifact `nightly-validation-report` uploaded in each run. Delete both branches. | Present. |

### TC-080-05 A failing scheduled or `main` run opens or comments on a `ci-failure` issue

| Step | Action | Expected Result |
|---|---|---|
| 1 | Inspect job `ci-failure-issue` in `e2e.yml`. | `needs: [playwright, performance, nightly-validation, lighthouse]`; runs on `failure()` with `github.ref == 'refs/heads/main'` and event `schedule`, `push` or `workflow_dispatch`; `permissions: issues: write` on this job only; uses `gh label create ci-failure`, `gh issue list --label ci-failure`, `gh issue create --title "E2E workflow failure on main" --label ci-failure` or a comment. |
| 2 | `gh issue list --label ci-failure --state all --limit 10` and open the most recent. | Issue created or commented by `github-actions` with the failing run URL. |
| 3 | `gh run list --workflow e2e.yml --event schedule --status failure --limit 5` and compare with step 2. | Every failed scheduled `main` run has a matching issue comment. |

Note: if no failed scheduled run exists, a forced failure on `main` needs a deliberate team-approved commit; record the demo per CIC-033 instead of creating one ad hoc.

### TC-080-06 No `secrets.` in `e2e.yml`; every job `timeout-minutes` ≤ 20

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -n "secrets\." .github/workflows/e2e.yml` | No output. |
| 2 | `grep -n "timeout-minutes" .github/workflows/e2e.yml` | `playwright` 20, `performance` 20, `nightly-validation` 20, `lighthouse` 20, `ci-failure-issue` 5. |
| 3 | `gh run view <TC-080-03 run> --json jobs --jq '.jobs[] | [.name, .startedAt, .completedAt]'` | Each job completes within 20 minutes. |

### TC-080-07 Nightly run passes on `main` three consecutive nights before 15 Nov 2026

| Step | Action | Expected Result |
|---|---|---|
| 1 | `gh run list --workflow e2e.yml --event schedule --branch main --limit 10 --json createdAt,conclusion` | Three consecutive nightly runs (consecutive dates) with `conclusion` `success`, the last before 2026-11-15. |
| 2 | Open each of those runs. | `playwright` ran `chromium firefox webkit`; `performance` and `nightly-validation` succeeded. |
| 3 | Record the run IDs in the FEAT-087 readiness checklist. | Recorded. |

### TC-080-08 `lighthouse` runs on a PR: Performance ≥ 80, LCP ≤ 2.5 s for `/residents`

| Step | Action | Expected Result |
|---|---|---|
| 1 | In the TC-080-02 PR run, open job `lighthouse`. | Step "Lighthouse CI 0.14.x, desktop preset (…)" runs `npx --yes -p @lhci/cli@0.14.x -p puppeteer@23 lhci autorun` and passes. |
| 2 | Download `lighthouse-report`. | `/residents` Performance ≥ 80 and LCP ≤ 2.5 s; also `/residents/R09`, `/residents/R09/trends`, `/study` reported. |
| 3 | Check branch protection. | `lighthouse` is not a required check. |

### TC-080-09 Schedule loops Chromium, Firefox, WebKit: read-only then mutating per project

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -n "BROWSERS:" .github/workflows/e2e.yml` | `chromium firefox webkit` for `schedule` and `workflow_dispatch`, otherwise `chromium`. |
| 2 | In a scheduled run, read "Main run …". | For each of chromium, firefox, webkit: `test:e2e:readonly` then `test:e2e:mutating`; every project runs even if an earlier one fails; reports in `playwright-report/<project>-readonly` and `<project>-mutating`. |
| 3 | `grep -n "playwright test" .github/workflows/e2e.yml` | No direct `playwright test` call (only the three npm scripts). |

### TC-080-10 Isolated `echowell_demo` preparation steps

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read the step "Isolated database echowell_demo for E2E-15, E2E-19, TST-187" in a run log. | `CREATE DATABASE echowell_demo`; `provision_login_roles.sql` run on it as superuser; backend stopped and restarted on the `echowell_demo` URLs with `PIPELINE_AS_OF=` empty; health wait via `curl -fsS --retry 30`; `seed test_v0_1 --master-only`; `import-master-data --dir tests/fixtures/seeds/demo_overlay` — all succeed. |
| 2 | Then "Isolated run (Chromium, serial; isolated-setup.ts logs in once per role, D-74)". | `npm run test:e2e:isolated` passes. |

### TC-080-11 Per-job credentials masked, never printed; `RATE_LIMIT_LOGIN=60/minute`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read the step "Per-job seed credentials (TRD 21 SEED_*, masked, never printed; CIC-034)". | Values generated with `openssl rand`, `::add-mask::` emitted before use, written to `.env` and `$GITHUB_ENV`; nothing echoed. |
| 2 | Search the full `playwright` log for `SEED_ADMIN_PASSWORD=`. | Only masked `***` values, never a clear value. |
| 3 | Read "Login limit 60/minute for the E2E stack only (D-74, TRD 21 ENV-054)". | `sed -i 's#^RATE_LIMIT_LOGIN=.*#RATE_LIMIT_LOGIN=60/minute#' .env`; `.env` comes from `.env.development.example` (`APP_ENV=local`). |
| 4 | Confirm the generated values cannot work on staging/production. | They exist only in the job; staging uses `STAGING_SEED_*` and production refuses `SEED_*` (FEAT-083). |

### TC-080-12 `playwright-report` artifact: 14-day retention, synthetic data only

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read "Upload playwright-report (synthetic data only, CIC-101)". | `if: always()`; paths `frontend/playwright-report/` and `e2e-compose.log`; `retention-days: 14`. |
| 2 | Download the artifact of a run and browse it. | Only study IDs R01–R11/N01 and synthetic values; no audio files, no real names. |

### TC-080-13 Failure path: Compose logs collected, stack always torn down

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `qa/tc-080-13`, change one expected text in `frontend/tests/e2e/resident-list.spec.ts` (e.g. "All (10)" → "All (11)"); open a draft PR. | `playwright` fails at the main run. |
| 2 | Read later steps. | "Collect Compose logs" runs and writes `e2e-compose.log`; artifact `playwright-report` uploaded with traces and the log; "Tear down the stack" runs `docker compose --profile demo down -v --remove-orphans`. |
| 3 | Check issues. | No `ci-failure` issue for this PR run (PR events are excluded). Close the PR and delete the branch. |

### TC-080-14 `performance`, `nightly-validation` skipped on PRs; `lighthouse` skipped on schedule; none required

| Step | Action | Expected Result |
|---|---|---|
| 1 | In the TC-080-02 PR run, view the job list. | `performance` and `nightly-validation` "skipped". |
| 2 | In a scheduled run, view the job list. | `lighthouse` "skipped". |
| 3 | `gh api repos/{owner}/{repo}/branches/main/protection --jq '.required_status_checks.contexts'` | Contains `playwright`; does not contain `performance`, `lighthouse`, `nightly-validation`. |

## API Validation

Not applicable: FEAT-080 is a workflow; the API is exercised by the suites it runs (FEAT-076, FEAT-079), whose checks are listed there.

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `playwright` log: seed and DS-10 loader steps | `seed test_v0_1` and `load_evaluation_ground_truth.py` exit 0 on the Compose database |
| 2 | `playwright` log: isolated preparation (TC-080-10) | `echowell_demo` created, provisioned, migrated and seeded with `--master-only` plus the demo overlay |
| 3 | `performance` / `nightly-validation` logs | Roles provisioned and `alembic upgrade head` succeeds on the `postgres:16-alpine` service `echowell_test` |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Failing robustness step (TC-080-04 step 3) | Job still `success` |
| 2 | Robustness module absent (TC-080-04 step 4) | Step skipped, job passes |
| 3 | Broken E2E assertion on a PR (TC-080-13) | `playwright` fails; logs uploaded; stack torn down; no `ci-failure` issue |
| 4 | PR event (TC-080-14) | `performance`, `nightly-validation` not run |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-080-AC-01 | On a PR to `main`, `playwright` passes in Chromium incl. `a11y.spec.ts` and the isolated run and reports the check `playwright` | TC-080-02 |
| FEAT-080-AC-02 | A `workflow_dispatch` run executes `performance` and `nightly-validation`; `performance` uploads `performance-report` and passes all budgets | TC-080-03 |
| FEAT-080-AC-03 | `nightly-validation` log has the pytest-randomly seed; a failing robustness step does not fail the job; without `tests/validation/robustness.py` the step is skipped and the job passes | TC-080-04 |
| FEAT-080-AC-04 | A forced failure on a scheduled run creates or comments on a `ci-failure` issue | TC-080-05 |
| FEAT-080-AC-05 | `grep -n "secrets\." .github/workflows/e2e.yml` returns nothing; every job `timeout-minutes` ≤ 20 | TC-080-06 |
| FEAT-080-AC-06 | Nightly `e2e.yml` passes on `main` for 3 consecutive nights before 15 Nov 2026 | TC-080-07 |
| FEAT-080-AC-07 | `lighthouse` runs on a PR and reports Performance ≥ 80 and LCP ≤ 2.5 s for `/residents` | TC-080-08 |

## Test Data Requirements

- `test_v0_1` seed and DS-10 (`tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv`); demo overlay `tests/fixtures/seeds/demo_overlay` (R11, N01); DS-08 generated in the `performance` job.
- Per-job generated `SEED_ADMIN_PASSWORD`, `SEED_CLINICIAN_PASSWORD`, `SEED_RESEARCHER_PASSWORD`, `SEED_INGEST_API_KEY` (masked); `RATE_LIMIT_LOGIN=60/minute`; `ci-only-*` throwaway database passwords.
- Throwaway branches `qa/tc-080-NN`.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-080-FR-01 / CIC-031, TST-151 | FEAT-080 | TC-080-01 |
| FEAT-080-FR-02 / CIC-030, D-73 | FEAT-080 | TC-080-02, TC-080-09 |
| FEAT-080-FR-03 / CIC-031, TST-100, TST-110 | FEAT-080 | TC-080-02, TC-080-09 |
| FEAT-080-FR-04 / CIC-030, D-72, D-73 | FEAT-080 | TC-080-10 |
| FEAT-080-FR-05 / CIC-034, D-71 | FEAT-080 | TC-080-11 |
| FEAT-080-FR-06 / D-74 (b), ENV-054 | FEAT-080 | TC-080-11 |
| FEAT-080-FR-07 / CIC-035, TST-190 | FEAT-080 | TC-080-03 |
| FEAT-080-FR-08 / CIC-037, TST-005, TST-084, TDV-083 | FEAT-080 | TC-080-04 |
| FEAT-080-FR-09 / CIC-116, TST-125, D-167 | FEAT-080 | TC-080-08 |
| FEAT-080-FR-10 / CIC-033 | FEAT-080 | TC-080-05 |
| FEAT-080-FR-11 / CIC-111, CIC-112 | FEAT-080 | TC-080-06 |
| FEAT-080-FR-12 / TRD 16 §4.10, CIC-101 | FEAT-080 | TC-080-12, TC-080-13 |
| FEAT-080-FR-13 / CIC-070, TST-150 | FEAT-080 | TC-080-02, TC-080-14 |
