# Full CI quality, security and hygiene gates

## Feature Description

`.github/workflows/ci.yml` runs on every pull request, every push to `main` and on manual dispatch with `permissions: contents: read` and no repository secret (FEAT-078; TRD 16 CIC-010..CIC-027, CIC-070..CIC-072, CIC-080..CIC-083, CIC-100..CIC-102, CIC-110..CIC-115; TRD 13 TST-140..TST-144, TST-150, TST-153; TRD 12 SEC-052, SEC-128, SEC-150..SEC-154; TRD 18 GIT-010, GIT-110..GIT-113). Its jobs are the required checks: `repo-hygiene` (audio files, `.env` files, 10 MB limit, forbidden terms, LLM/ML dependencies, Conventional Commit PR title), `backend-lint` (ruff, ruff format, mypy, import-linter), `backend-test` (PostgreSQL 16 service, login roles, migrations up/down/up, one pytest invocation including the R01–R10 validation suite, coverage gates 95 % `analytics/` and 85 % `backend/`, `backend-reports` artifact), `openapi-contract`, `frontend` (lint, typecheck, format, tests with 80 % coverage, build, bundle check), `security-audit` (pip-audit, npm audit, gitleaks, Bandit) and `docker-build`. Branch protection on `main` requires these seven plus `playwright` (e2e.yml). Dependabot keeps dependencies current.

## Preconditions

- GitHub access to the EchoWell repository with permission to push throwaway branches and open draft pull requests against `main`, and read access to Settings → Branches / Rules (admin needed only to view branch protection).
- `gh` CLI authenticated; local clone at `main`.
- Every negative case uses a throwaway branch named `qa/tc-078-NN`, opened as a draft PR, never merged, and closed and deleted afterwards. Staging deploys only from `main` (DEP-043), so these PRs do not touch the Render, Netlify production or Neon deployments.
- Python 3.12 and Node 20 locally for the optional local reproductions.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-078-01 | Triggers, default permissions, no repository secret, per-run JWT_SECRET | High | Security |
| TC-078-02 | A composite sign change in `analytics/config.py` fails `backend-test` | High | Negative |
| TC-078-03 | Adding `tests/fixtures/sample.wav` fails `repo-hygiene` | High | Negative |
| TC-078-04 | An endpoint without updating `openapi.json` fails `openapi-contract` | High | Negative |
| TC-078-05 | PR title "Updated stuff" fails, "feat(api): add device panel endpoint" passes | High | Negative |
| TC-078-06 | `ci.yml` on `main` under 15 minutes and `backend-reports` with 10 of 10 residents passing | High | Positive |
| TC-078-07 | Branch protection on `main` lists exactly the eight CIC-070 checks plus the GIT-010 rules | High | Security |
| TC-078-08 | `openai`, an ML package or the old facility name of AGT-019 fails `repo-hygiene` | High | Negative |
| TC-078-09 | Coverage below 95 % / 85 % / 80 % fails the respective job | High | Negative |
| TC-078-10 | A committed fake key fails gitleaks; a Bandit medium finding fails `security-audit` | High | Security |
| TC-078-11 | A tracked `.env` file or a file above 10 MB fails `repo-hygiene` | Medium | Negative |
| TC-078-12 | "diagnoses" or "severity" in UI copy fails `repo-hygiene` | Medium | Negative |
| TC-078-13 | `backend-lint` fails on ruff, format, mypy or import-linter findings | Medium | Negative |
| TC-078-14 | `backend-test` provisions roles and runs migrations up, down and up | Medium | Positive |
| TC-078-15 | `frontend` job steps and `docker-build` image checks | Medium | Positive |
| TC-078-16 | Action pinning, `timeout-minutes` ≤ 20, `ubuntu-24.04`, caches | Medium | Documentation |
| TC-078-17 | Dependabot configuration and security updates | Medium | Documentation |
| TC-078-18 | Security-audit waiver recorded in `SECURITY_EXCEPTIONS.md` with expiry | Medium | Documentation |
| TC-078-19 | A test skipped without a requirement or OQ ID fails collection | Medium | Negative |

### TC-078-01 Triggers, default permissions, no repository secret, per-run JWT_SECRET

| Step | Action | Expected Result |
|---|---|---|
| 1 | `sed -n '/^on:/,/^concurrency/p' .github/workflows/ci.yml` | `pull_request:`, `push: branches: [main]`, `workflow_dispatch:`. |
| 2 | `grep -n -A1 "^permissions:" .github/workflows/ci.yml` | `contents: read`. |
| 3 | `grep -r "secrets\." .github/workflows/ci.yml` | No output. |
| 4 | `grep -n "openssl rand -hex 32" .github/workflows/ci.yml` | JWT_SECRET written to `$GITHUB_ENV` per run in `backend-test` (and inline in `openapi-contract`). |
| 5 | `gh workflow run ci.yml --ref main`, then `gh run list --workflow ci.yml --limit 1`. | A run with event `workflow_dispatch` starts. |

### TC-078-02 A composite sign change in `analytics/config.py` fails `backend-test`

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `qa/tc-078-02`, in `analytics/config.py` flip the `sign` of one of the 7 composite features (e.g. 1 → -1), commit "test(ci): flip composite sign", open a draft PR. | `ci.yml` starts. |
| 2 | Wait for `backend-test`. | Job fails: validation tests for R01–R10 report mismatches against the answer key (tolerance 1e-6, exact strings); job summary shows the R01–R10 table with failures. |
| 3 | Check the PR merge box. | Merging blocked: required check `backend-test` failed. |
| 4 | Close the PR and delete the branch. | Done. |

### TC-078-03 Adding `tests/fixtures/sample.wav` fails `repo-hygiene`

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `qa/tc-078-03`, create an empty file `tests/fixtures/sample.wav` (`: > tests/fixtures/sample.wav`, no audio content), commit, open a draft PR titled "test(ci): add wav". | `ci.yml` starts. |
| 2 | Open `repo-hygiene`, step "No audio files (CIC-020, BR-01)". | Prints `tests/fixtures/sample.wav` and `Audio files are forbidden in this repository`; job fails; merge blocked. |
| 3 | Close and delete. | Done. |

### TC-078-04 An endpoint without updating `openapi.json` fails `openapi-contract`

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `qa/tc-078-04`, add a trivial GET route to an existing router in `backend/api/` without changing `docs/api_reference/openapi.json`; open a draft PR "test(ci): undocumented endpoint". | `ci.yml` starts. |
| 2 | Open `openapi-contract`. | Step "Committed contract is up to date (docs/api_reference/openapi.json)" shows a `diff -u` and the error "The API changed: run 'python -m backend.cli export-openapi > docs/api_reference/openapi.json' and 'cd frontend && npm run gen:api', and commit both (CIC-018)"; job fails. |
| 3 | Close and delete. | Done. |

### TC-078-05 PR title "Updated stuff" fails, "feat(api): add device panel endpoint" passes

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `qa/tc-078-05` with a one-line docs change, open a draft PR titled "Updated stuff". | `repo-hygiene` step "PR title is a Conventional Commit (CIC-022)" fails with "PR title must be a Conventional Commit header, e.g. 'feat(api): add device panel endpoint'". |
| 2 | Edit the title to "feat(api): add device panel endpoint" and re-run the job (`gh run rerun <id> --failed`). | Step passes. |
| 3 | Close and delete. | Done. |

### TC-078-06 `ci.yml` on `main` under 15 minutes and `backend-reports` with 10 of 10 residents passing

| Step | Action | Expected Result |
|---|---|---|
| 1 | `gh run list --workflow ci.yml --branch main --limit 20 --json createdAt,updatedAt,conclusion` | 90th percentile of (updatedAt − createdAt) < 15 minutes; all `conclusion` `success`. |
| 2 | Open the latest `main` run; download artifact `backend-reports` (`gh run download <id> -n backend-reports`). | Contains `build/coverage.xml`, `build/junit.xml`, `docs/reports/ALGORITHM_VALIDATION_REPORT.md`, `docs/reports/validation_results.json`. |
| 3 | Read `ALGORITHM_VALIDATION_REPORT.md`. | 10 of 10 residents (R01–R10) pass. |
| 4 | Read the `backend-test` job summary. | R01–R10 pass/fail table and the coverage table with `analytics/` and `backend/` percentages and gates 95 % / 85 %. |

### TC-078-07 Branch protection on `main` lists exactly the eight CIC-070 checks plus the GIT-010 rules

| Step | Action | Expected Result |
|---|---|---|
| 1 | `gh api repos/{owner}/{repo}/branches/main/protection --jq '.required_status_checks'` (or Settings → Branches/Rules). | `strict: true`; contexts exactly `repo-hygiene`, `backend-lint`, `backend-test`, `openapi-contract`, `frontend`, `security-audit`, `docker-build`, `playwright`. |
| 2 | Read the review and push settings. | 1 required approval; dismiss stale approvals; CODEOWNERS review required; conversation resolution required; force pushes and deletion blocked; admins included (no bypass). |
| 3 | Confirm `performance`, `lighthouse`, `nightly-validation` are not required. | Absent from the list. |

### TC-078-08 `openai`, an ML package or the old facility name of AGT-019 fails `repo-hygiene`

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `qa/tc-078-08a`, append `openai==1.0.0` to `backend/requirements.txt`; draft PR "test(ci): llm dependency". | Step "No LLM SDK or ML model dependencies" prints the line and "LLM SDKs and machine-learning model packages are not allowed"; job fails. |
| 2 | On `qa/tc-078-08b`, add `"@tensorflow/tfjs": "4.0.0"` to `frontend/package.json` dependencies; draft PR. | Same step fails. |
| 3 | On `qa/tc-078-08c`, add a comment line under `backend/` containing the old facility name of AGT-019 (the term matched by the job's character-class pattern); draft PR. | Step "Forbidden terms" prints the file and line and "The old facility name must not be used (the facility is Edgewood)"; job fails. |
| 4 | Close and delete the three branches. | Done. |

### TC-078-09 Coverage below 95 % / 85 % / 80 % fails the respective job

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read the latest `main` run: `backend-test` steps `coverage report --include='analytics/*' --fail-under=95` and `--include='backend/*' --fail-under=85`. | Both pass with the printed totals ≥ gate. |
| 2 | On `qa/tc-078-09a`, add an untested module of ~200 executable lines under `analytics/` (e.g. `analytics/qa_uncovered.py`); draft PR. | `backend-test` fails at the `analytics/*` coverage step ("Coverage failure: total of <n> is less than fail-under=95"). |
| 3 | On `qa/tc-078-09b`, add an untested ~300-line module under `frontend/lib/`; draft PR. | `frontend` fails at `npm run test:coverage` (line threshold 80 % in `vitest.config.ts`). |
| 4 | `grep -n "lines" frontend/vitest.config.ts` | Line threshold `80`. |
| 5 | Close and delete. | Done. |

### TC-078-10 A committed fake key fails gitleaks; a Bandit medium finding fails `security-audit`

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `qa/tc-078-10a`, commit a file `backend/qa_fake.py` with a fake AWS-style access key ID made up for this test (`AKIA` followed by 16 random upper-case letters/digits; never a real key); draft PR. | Step "Secret scan over the full history" (gitleaks v8) reports a leak (redacted); `security-audit` fails. |
| 2 | Close the PR and delete the branch so the fake key stays only in the deleted branch. | Done. |
| 3 | On `qa/tc-078-10b`, add to a module under `backend/` `import pickle` and `pickle.loads(data)` on untrusted input; draft PR. | Step "Bandit, medium severity or higher fails" (`bandit -r backend analytics -ll -q`) reports B301 (Medium) and fails the job. |
| 4 | Close and delete. | Done. |

### TC-078-11 A tracked `.env` file or a file above 10 MB fails `repo-hygiene`

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `qa/tc-078-11a`, `git add -f backend/.env.local` containing only `APP_ENV=local`; draft PR. | Step "No env files (CIC-021)" prints the path and ".env files must not be committed"; fails. |
| 2 | On `qa/tc-078-11b`, add `head -c 11000000 /dev/zero > docs/qa-big.bin`; draft PR. | Step "File size limit 10 MB (CIC-021)" prints the file; fails. |
| 3 | Confirm `*.example` files pass: the step ignores `.env.example`, `.env.development.example`, `.env.production.example`. | No error for them on `main`. |
| 4 | Close and delete. | Done. |

### TC-078-12 "diagnoses" or "severity" in UI copy fails `repo-hygiene`

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `qa/tc-078-12`, add a JSX comment containing the word "severity" to a file under `frontend/components/`; draft PR. | Step "Forbidden terms" prints the line and "Forbidden wording in UI copy (detection, not diagnosis)"; fails. |
| 2 | Locally run `git grep -n -I -w -i -E "diagnoses|severity" -- frontend/app frontend/components frontend/lib/wording.ts` on `main`. | No output. |
| 3 | Close and delete. | Done. |

Note: CIC-114 and `ci.yml:42` scan `frontend/lib/wording.ts`, which is now a re-export barrel; the copy itself lives in `frontend/lib/wording/*.ts`, which the check does not scan.

### TC-078-13 `backend-lint` fails on ruff, format, mypy or import-linter findings

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `qa/tc-078-13`, add `import os` unused to a module under `backend/` and `from backend.core import config` inside a module under `analytics/`; draft PR. | `backend-lint` fails at `ruff check .` (F401); after fixing that locally, `lint-imports` reports a broken analytics-purity contract. |
| 2 | Locally: `ruff check . && ruff format --check . && mypy analytics backend && lint-imports` on `main`. | All exit 0. |
| 3 | Close and delete. | Done. |

### TC-078-14 `backend-test` provisions roles and runs migrations up, down and up

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open the latest `main` run, job `backend-test`. | Service `postgres:16-alpine`; steps in order: `psql … -f database/roles/provision_login_roles.sql`, `alembic upgrade head`, `alembic downgrade base && alembic upgrade head`, `alembic check`, then one `pytest -p no:randomly tests/unit tests/integration tests/contract tests/security tests/validation …`. |
| 2 | Check the job `env`. | DATABASE_URL uses `echowell_app_login`, DATABASE_MIGRATION_URL `echowell_migrator_login`, DATABASE_READONLY_URL `echowell_readonly_login`; only `ci-only-*` throwaway passwords. |
| 3 | Check the pytest step output. | 0 failed, 0 errors. |

### TC-078-15 `frontend` job steps and `docker-build` image checks

| Step | Action | Expected Result |
|---|---|---|
| 1 | Latest `main` run, job `frontend`. | Steps `npm ci`, `npm run lint` (`next lint --max-warnings 0`), `npm run typecheck`, `npm run format:check`, `npm run test:coverage`, `npm run build`, `npm run check:bundle` — all pass. |
| 2 | Job `docker-build`. | Both images built with `cache-from/cache-to: type=gha`; step "Backend image runs as non-root and holds no .env, tests, specs or frontend" passes (`id -u` = `10001`). |

### TC-078-16 Action pinning, `timeout-minutes` ≤ 20, `ubuntu-24.04`, caches

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -n "uses:" .github/workflows/ci.yml` | `actions/*` and `docker/*` on major tags (e.g. `actions/checkout@v7`); any other action pinned to a 40-character commit SHA. |
| 2 | `grep -n "timeout-minutes\|runs-on" .github/workflows/ci.yml` | Every job `runs-on: ubuntu-24.04`; timeouts 5, 8, 20, 8, 12, 10, 12 (all ≤ 20). |
| 3 | `grep -n "cache" .github/workflows/ci.yml` | pip cache keyed on `backend/requirements*.txt`; npm cache keyed on `frontend/package-lock.json`; `npm ci` used everywhere (never `npm install`). |

### TC-078-17 Dependabot configuration and security updates

| Step | Action | Expected Result |
|---|---|---|
| 1 | `cat .github/dependabot.yml` | Ecosystems `pip` (`/backend`), `npm` (`/frontend`), `github-actions` (`/`), `docker` (`/backend`), each `target-branch: main`, matching TRD 18 §4.12. |
| 2 | Settings → Code security. | Dependabot alerts and security updates enabled. |
| 3 | Open any Dependabot PR. | Shows the same required checks; not mergeable until all are green. |

### TC-078-18 Security-audit waiver recorded in `SECURITY_EXCEPTIONS.md` with expiry

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `SECURITY_EXCEPTIONS.md`. | Each row names advisory, package, severity, ignore entry, tracking issue, Added and Expires dates and the approver role. |
| 2 | Read `scripts/ci/audit_gate.py`. | A row counts only until its `Expires` date; after it the gate fails again. |
| 3 | Check each row's `Expires` − `Added`. | ≤ 7 days per CIC-072, or covered by a recorded TRD 24 decision. |

Note: the current rows run from 2026-11-05 to 2026-12-20 (more than 7 days) under TRD 24 D-159, as stated in `SECURITY_EXCEPTIONS.md`.

### TC-078-19 A test skipped without a requirement or OQ ID fails collection

| Step | Action | Expected Result |
|---|---|---|
| 1 | Locally add to a unit test module `@pytest.mark.skip(reason="later")` on a test; run `pytest -q tests/unit -p no:randomly`. | Collection error "<nodeid>: skip reason must name a requirement or OQ ID"; run fails. |
| 2 | Change to `reason="OQ-08 open"` and re-run. | Collection succeeds; the test is skipped. |
| 3 | Revert the local change. | Working tree clean. |

## API Validation

Not applicable: FEAT-078 is CI configuration; the only API check is the OpenAPI drift check covered by TC-078-04.

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `backend-test` log: `alembic upgrade head`, `alembic downgrade base && alembic upgrade head`, `alembic check` | All three steps exit 0 on the ephemeral `echowell_test` database |
| 2 | `backend-test` log: provisioning step | Roles `echowell_app_login`, `echowell_migrator_login`, `echowell_readonly_login` created before migration |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Composite sign flip (TC-078-02) | `backend-test` fails; merge blocked |
| 2 | `tests/fixtures/sample.wav` (TC-078-03) | `repo-hygiene` fails |
| 3 | Undocumented endpoint (TC-078-04) | `openapi-contract` fails |
| 4 | Title "Updated stuff" (TC-078-05) | `repo-hygiene` fails |
| 5 | `openai`, ML package, old facility name (TC-078-08) | `repo-hygiene` fails |
| 6 | Coverage drop (TC-078-09) | `backend-test` / `frontend` fails |
| 7 | Fake key, Bandit medium (TC-078-10) | `security-audit` fails |
| 8 | Tracked `.env`, file > 10 MB (TC-078-11) | `repo-hygiene` fails |
| 9 | Skip without ID (TC-078-19) | Collection error |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-078-AC-01 | A PR changing one composite sign in `analytics/config.py` fails `backend-test` and cannot be merged | TC-078-02 |
| FEAT-078-AC-02 | A PR adding `tests/fixtures/sample.wav` fails `repo-hygiene` | TC-078-03 |
| FEAT-078-AC-03 | A PR adding an endpoint without updating `docs/api_reference/openapi.json` fails `openapi-contract` | TC-078-04 |
| FEAT-078-AC-04 | Title "Updated stuff" fails `repo-hygiene`; "feat(api): add device panel endpoint" passes | TC-078-05 |
| FEAT-078-AC-05 | `ci.yml` on `main` completes all required checks in under 15 minutes and uploads `backend-reports` with 10 of 10 residents passing and `validation_results.json` | TC-078-06 |
| FEAT-078-AC-06 | `grep -r "secrets\." .github/workflows/ci.yml` returns nothing | TC-078-01 |
| FEAT-078-AC-07 | Branch protection for `main` lists exactly the eight CIC-070 checks | TC-078-07 |
| FEAT-078-AC-08 | `openai` in `backend/requirements.txt` or the old facility name under `backend/` fails `repo-hygiene` | TC-078-08 |
| FEAT-078-AC-09 | Coverage below 95 % `analytics/`, 85 % `backend/` or 80 % `frontend/` fails the respective job | TC-078-09 |
| FEAT-078-AC-10 | A fake key matching a gitleaks rule fails `security-audit`; a Bandit medium finding in `backend/` fails it too | TC-078-10 |

## Test Data Requirements

- Throwaway branches `qa/tc-078-NN` and draft PRs, closed and deleted after each case.
- Synthetic artefacts only: an empty `sample.wav`, an 11 MB zero file, a made-up fake key string, a dummy `.env.local` with `APP_ENV=local`.
- Answer key `tests/fixtures/answer_key/EchoWell_pipeline_test_v0_1.xlsx` and SRC-05 (used by `backend-test`).
- No repository secret; CI uses only `ci-only-*` throwaway values.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-078-FR-01 / CIC-010, CIC-024, CIC-026 | FEAT-078 | TC-078-01 |
| FEAT-078-FR-02 / CIC-020, CIC-021, CIC-022 | FEAT-078 | TC-078-03, TC-078-05, TC-078-11 |
| FEAT-078-FR-03 / CIC-114, SEC-128, AGT-019 | FEAT-078 | TC-078-08, TC-078-12 |
| FEAT-078-FR-04 / CIC-011, CIC-115, ARC-041 | FEAT-078 | TC-078-13 |
| FEAT-078-FR-05 / CIC-012, CIC-015, D-72 | FEAT-078 | TC-078-14 |
| FEAT-078-FR-06 / CIC-013, CIC-014, TST-083 | FEAT-078 | TC-078-02, TC-078-14 |
| FEAT-078-FR-07 / CIC-016, CIC-017, TST-140..TST-142 | FEAT-078 | TC-078-09 |
| FEAT-078-FR-08 / CIC-018, D-51 | FEAT-078 | TC-078-04 |
| FEAT-078-FR-09 / CIC-017 | FEAT-078 | TC-078-15 |
| FEAT-078-FR-10 / CIC-019, SEC-151..SEC-153 | FEAT-078 | TC-078-10 |
| FEAT-078-FR-11 / CIC-023, CIC-082 | FEAT-078 | TC-078-15 |
| FEAT-078-FR-12 / CIC-080, CIC-081, CIC-083 | FEAT-078 | TC-078-16 |
| FEAT-078-FR-13 / CIC-111, CIC-027 | FEAT-078 | TC-078-16 |
| FEAT-078-FR-14 / CIC-100, CIC-101, CIC-102 | FEAT-078 | TC-078-06 |
| FEAT-078-FR-15 / CIC-070, CIC-071, GIT-010, TST-150 | FEAT-078 | TC-078-07 |
| FEAT-078-FR-16 / CIC-025, SEC-154 | FEAT-078 | TC-078-16 |
| FEAT-078-FR-17 / GIT-110, GIT-113, SEC-150 | FEAT-078 | TC-078-17 |
| FEAT-078-FR-18 / CIC-072, TST-136 | FEAT-078 | TC-078-18 |
| FEAT-078-FR-19 / TST-153 | FEAT-078 | TC-078-19 |
| FEAT-078-FR-20 / ARC-104, AGT-004, AGT-005 | FEAT-078 | TC-078-08 |
| CIC-110 | FEAT-078 | TC-078-06 |
