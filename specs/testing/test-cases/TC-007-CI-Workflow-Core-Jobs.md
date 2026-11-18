# FEAT-007 CI workflow core jobs

## Feature Description

FEAT-007 creates `.github/workflows/ci.yml`, which runs on every pull request, every push to `main` and on manual dispatch, with read-only permissions (`contents: read`), no repository secret, GitHub-hosted `ubuntu-24.04` runners and action pins per CIC-025. Its core jobs are `backend-lint` (ruff check, ruff format check, mypy, import-linter), `backend-test` (pytest unit, integration and validation suites in one invocation against a `postgres:16-alpine` service container through `DATABASE_URL` with `APP_ENV=test`) and `frontend` (`npm ci`, `npm run lint`, `npm run typecheck`, `npm run format:check`, `npm run test:coverage`, `npm run build`, in that order). Further jobs in the same file come from FEAT-078.

## Preconditions

- Write access to a branch of `EchoWellApp/echowell` and permission to open (draft) pull requests against `main`; GitHub CLI `gh` signed in.
- A local clone for the file inspections; commands run from the repository root.
- Each negative case uses its own throwaway branch and draft PR, closed and deleted afterwards. Never merge them.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-007-01 | A pull request triggers `backend-lint`, `backend-test` and `frontend`, all green | High | Positive |
| TC-007-02 | A `ruff` finding fails `backend-lint` | High | Negative |
| TC-007-03 | A `mypy` error fails `backend-lint` | High | Negative |
| TC-007-04 | A forbidden import in `analytics/` fails `backend-lint` | High | Negative |
| TC-007-05 | `backend-test` uses the `postgres:16-alpine` service through `DATABASE_URL` | High | Positive |
| TC-007-06 | A failing test fails `backend-test` | High | Negative |
| TC-007-07 | `frontend` runs the six npm commands in the CIC-017 order | High | Positive |
| TC-007-08 | An ESLint warning fails `frontend` | High | Negative |
| TC-007-09 | No repository secret; permissions `contents: read`; `JWT_SECRET` generated per run | High | Security |
| TC-007-10 | Every job runs on `ubuntu-24.04`; every `uses:` follows CIC-025 | High | Security |
| TC-007-11 | Triggers: pull request, push to `main`, manual dispatch | Medium | Positive |

### TC-007-01 A pull request triggers `backend-lint`, `backend-test` and `frontend`, all green

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create branch `qa/ci-green` from `main`, change one line in a Markdown file under `docs/`, push, and run `gh pr create --draft --base main --title "docs: qa ci check" --body "QA"`. | Draft PR created. |
| 2 | Run `gh pr checks <PR number> --watch`. | Checks named `backend-lint`, `backend-test` and `frontend` (workflow `ci.yml`) appear and finish with `pass`. |
| 3 | Open the run in the Actions tab. | Jobs `backend-lint`, `backend-test`, `frontend` show a green tick; no step is marked `continue-on-error`. |

### TC-007-02 A `ruff` finding fails `backend-lint`

| Step | Action | Expected Result |
|---|---|---|
| 1 | On branch `qa/ci-ruff` add `import json` (unused) at the top of `backend/cli.py`; push; open a draft PR. | PR created. |
| 2 | Open the `backend-lint` job log. | Step `ruff check .` prints `F401 [*] \`json\` imported but unused` for `backend/cli.py`; step exits 1; job status `failure`; PR check `backend-lint` shows `fail`. |
| 3 | Revert the change and push. | `backend-lint` passes. Close the PR and delete the branch. |

### TC-007-03 A `mypy` error fails `backend-lint`

| Step | Action | Expected Result |
|---|---|---|
| 1 | On branch `qa/ci-mypy` add `def qa(x: int) -> str: return x` to `analytics/robust_stats.py`; push; open a draft PR. | PR created. |
| 2 | Open the `backend-lint` log. | Step `mypy analytics backend` prints `error: Incompatible return value type (got "int", expected "str")`; job `failure`. |
| 3 | Close the PR and delete the branch. | Cleaned up. |

### TC-007-04 A forbidden import in `analytics/` fails `backend-lint`

| Step | Action | Expected Result |
|---|---|---|
| 1 | On branch `qa/ci-import` add `import sqlalchemy  # noqa: F401` to `analytics/robust_stats.py`; push; open a draft PR. | PR created. |
| 2 | Open the `backend-lint` log. | Step `lint-imports` reports contract "analytics is pure: no backend, database, HTTP, environment or randomness" `BROKEN` (`analytics.robust_stats -> sqlalchemy`); job `failure`. |
| 3 | Close the PR and delete the branch. | Cleaned up. |

### TC-007-05 `backend-test` uses the `postgres:16-alpine` service through `DATABASE_URL`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open the `backend-test` log of the green run of TC-007-01, section "Initialize containers". | Service container image `postgres:16-alpine` is pulled and started; health check `pg_isready -U echowell -d echowell_test` reports healthy. |
| 2 | Open the job's environment block in the log (or `grep -n -A16 "backend-test:" .github/workflows/ci.yml`). | `APP_ENV: test`; `DATABASE_URL: postgresql+psycopg://echowell_app_login:…@localhost:5432/echowell_test` with a `ci-only-*` password; no `sqlite`. |
| 3 | Find the pytest step. | One invocation `pytest -p no:randomly tests/unit tests/integration tests/contract tests/security tests/validation …` runs the unit, integration and validation suites together; summary `N passed`, `0 failed`, `0 errors`. |
| 4 | Run `grep -n "sqlite" .github/workflows/ci.yml; echo "exit=$?"`. | `exit=1`. |

### TC-007-06 A failing test fails `backend-test`

| Step | Action | Expected Result |
|---|---|---|
| 1 | On branch `qa/ci-test` add `tests/unit/test_qa_fail.py` with `import pytest`, `pytestmark = pytest.mark.unit` and `def test_qa_fail() -> None: assert 1 == 2`; push; open a draft PR. | PR created. |
| 2 | Open the `backend-test` log. | Pytest reports `FAILED tests/unit/test_qa_fail.py::test_qa_fail - assert 1 == 2`; summary `1 failed`; job `failure`. |
| 3 | Close the PR and delete the branch. | Cleaned up. |

### TC-007-07 `frontend` runs the six npm commands in the CIC-017 order

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open the `frontend` job log of the green run of TC-007-01. | Steps run in this order: `npm ci`, `npm run lint`, `npm run typecheck`, `npm run format:check`, `npm run test:coverage`, `npm run build`; each succeeds. |
| 2 | Run `grep -n "run: npm" .github/workflows/ci.yml`. | In the `frontend` job the six lines appear in that order (a later `npm run check:bundle` from FEAT-078 may follow `npm run build`). |
| 3 | Check the `npm run lint` step output. | Command is `next lint --max-warnings 0`. |

### TC-007-08 An ESLint warning fails `frontend`

| Step | Action | Expected Result |
|---|---|---|
| 1 | On branch `qa/ci-eslint` add an unused variable `const qaUnused = 1;` inside the component of `frontend/app/login/page.tsx`; push; open a draft PR. | PR created. |
| 2 | Open the `frontend` log. | Step `npm run lint` reports `'qaUnused' is assigned a value but never used` and `ESLint found too many warnings (maximum: 0)`; the step exits non-zero; later steps (`typecheck` … `build`) are skipped; job `failure`. |
| 3 | Close the PR and delete the branch. | Cleaned up. |

### TC-007-09 No repository secret; permissions `contents: read`; `JWT_SECRET` generated per run

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -n "secrets\." .github/workflows/ci.yml; echo "exit=$?"`. | No line printed; `exit=1`. |
| 2 | Run `grep -n -A1 "^permissions" .github/workflows/ci.yml` and `grep -n "permissions" .github/workflows/ci.yml`. | Top-level `permissions:` with only `contents: read`; no job-level permission that widens it. |
| 3 | Run `grep -n "openssl rand -hex 32" .github/workflows/ci.yml`. | The `backend-test` job writes `JWT_SECRET=$(openssl rand -hex 32)` to `$GITHUB_ENV`. |
| 4 | In the `backend-test` log, search for `JWT_SECRET=`. | The generated value is not printed (only the masked command). |
| 5 | Run `grep -nE "PASSWORD:\|_PASSWORD:" .github/workflows/ci.yml`. | Every database password value starts with `ci-only-`. |

### TC-007-10 Every job runs on `ubuntu-24.04`; every `uses:` follows CIC-025

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -c "runs-on: ubuntu-24.04" .github/workflows/ci.yml` and `grep -cE "^  [a-z-]+:$" .github/workflows/ci.yml` (jobs). | Both counts are equal (8 at the time of writing); no other `runs-on` value. |
| 2 | Run `grep -n "uses:" .github/workflows/ci.yml`. | Each `actions/*`, `docker/*` or `microsoft/playwright` action is pinned to a major tag (for example `actions/checkout@v7`, `docker/build-push-action@v6`). |
| 3 | Run `grep -n "uses:" .github/workflows/ci.yml \| grep -vE "uses: (actions\|docker\|microsoft/playwright)"`. | No line, or every printed line ends `@` + a 40-character commit SHA. |

### TC-007-11 Triggers: pull request, push to `main`, manual dispatch

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `sed -n '/^on:/,/^[a-z]/p' .github/workflows/ci.yml`. | `pull_request:`, `push:` with `branches: [main]`, and `workflow_dispatch:`. |
| 2 | In the Actions tab select workflow CI and click "Run workflow" on `main`. | A run starts with event `workflow_dispatch`. |
| 3 | Check the run list after the last merge to `main`. | A run with event `push` on `main` exists. |

## API Validation

Not applicable: FEAT-007 is a CI workflow; it exposes and calls no EchoWell endpoint.

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `backend-test` service container definition | `image: postgres:16-alpine`, database `echowell_test`, health check `pg_isready` every 5 s, 10 retries |
| 2 | Provisioning step in the `backend-test` log | `psql -v ON_ERROR_STOP=1 -f database/roles/provision_login_roles.sql` succeeds before pytest |

No persistent database is touched; the service database is discarded with the runner.

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Ruff finding (TC-007-02) | `backend-lint` fails |
| 2 | Mypy error (TC-007-03) | `backend-lint` fails |
| 3 | Forbidden analytics import (TC-007-04) | `backend-lint` fails |
| 4 | Failing unit test (TC-007-06) | `backend-test` fails |
| 5 | ESLint warning (TC-007-08) | `frontend` fails at `npm run lint` |
| 6 | Search for `secrets.` (TC-007-09) | No match |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-007-AC-01 | A PR triggers `ci.yml` with `backend-lint`, `backend-test`, `frontend`, all green. | TC-007-01 |
| FEAT-007-AC-02 | A `ruff` finding, a `mypy` error or a forbidden `analytics/` import fails `backend-lint`. | TC-007-02, TC-007-03, TC-007-04 |
| FEAT-007-AC-03 | `backend-test` log shows `postgres:16-alpine` and pytest via `DATABASE_URL`; a failing test fails the job. | TC-007-05, TC-007-06 |
| FEAT-007-AC-04 | `frontend` runs the six npm commands in CIC-017 order and fails on an ESLint warning. | TC-007-07, TC-007-08 |
| FEAT-007-AC-05 | `grep -n "secrets\." ci.yml` returns nothing; `permissions` is `contents: read` only. | TC-007-09 |
| FEAT-007-AC-06 | Every job `runs-on: ubuntu-24.04`; every `uses:` per CIC-025. | TC-007-10 |

## Test Data Requirements

- Throwaway branches `qa/ci-*` and draft PRs; no merge.
- `ci-only-*` database passwords and the per-run `JWT_SECRET` live only in the workflow; nothing is added to repository secrets.
- No resident data beyond what the test suites build themselves (synthetic `test_v0_1`).

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-007-FR-01 (CIC-010) | FEAT-007 | TC-007-01, TC-007-11 |
| FEAT-007-FR-02 (CIC-011, AC-ARC-01) | FEAT-007 | TC-007-02, TC-007-03, TC-007-04 |
| FEAT-007-FR-03 (CIC-012, TST-002) | FEAT-007 | TC-007-05 |
| FEAT-007-FR-04 (CIC-013) | FEAT-007 | TC-007-05, TC-007-06 |
| FEAT-007-FR-05 (CIC-017, FE-202) | FEAT-007 | TC-007-07, TC-007-08 |
| FEAT-007-FR-06 (CIC-024) | FEAT-007 | TC-007-09 |
| FEAT-007-FR-07 (CIC-025) | FEAT-007 | TC-007-10 |
| FEAT-007-FR-08 (CIC-026, ENV-041) | FEAT-007 | TC-007-09 |
| FEAT-007-FR-09 (CIC-027) | FEAT-007 | TC-007-10 |
| FEAT-007-FR-10 (D-55, TST-150) | FEAT-007 | TC-007-01 |
| FE-203 | FEAT-007 | TC-007-08 |
