# FEAT-007 CI workflow core jobs (lint, unit/integration tests, frontend build)

| Field | Value |
|---|---|
| Epic | DevOps & Deployment |
| Build phase | Phase 3 (TRD 25) |
| Priority | P0 |
| Complexity | Low |
| MVP status | Required |
| Dependencies | FEAT-005, FEAT-004 |
| Status | Complete |

## Purpose

Create the first working `.github/workflows/ci.yml` so that every pull request from Phase 4 onward is gated by static checks, the Python test suites against a real PostgreSQL 16 service container, and the frontend lint/type/format/test/build chain. The remaining required checks (repository hygiene, OpenAPI contract, security audit, docker build, coverage gates, Playwright) are added to the same file by FEAT-078 in Phase 9 (D-55).

## Business Context

- BR-17: GitHub Actions CI/CD for the monorepo (SRC-01).
- BR-15: the validation suite runs in `backend-test` on every PR once it exists (CIC-013, TST-150).
- BR-16: CI uses no repository secret and only GitHub-hosted runners (CIC-026, CIC-027).

## Referenced TRDs

- TRD 16 CIC-010..CIC-013 (triggers, lint, PostgreSQL service, one pytest invocation), CIC-017 (frontend job), CIC-024..CIC-027 (permissions, action pinning, no secrets, runners); §4.2 job table and `ci.yml` outline.
- TRD 13 TST-150 (PR checks), TST-002 (database used when `DATABASE_URL` is set and `APP_ENV=test`).
- TRD 04 FE-202 (frontend CI order).
- TRD 25 §4.6 Phase 3 (outputs include `.github/workflows/ci.yml`).
- TRD 24 D-55 (legacy CI stub replaced; full gates in Phase 9).

## Scope

- `.github/workflows/ci.yml` with name `CI`, triggers `pull_request` (all branches), `push` to `main`, `workflow_dispatch`; concurrency group `ci-${{ github.ref }}` cancelling in-progress runs for pull requests only; top-level `permissions: contents: read`; env `PYTHON_VERSION: "3.12"`, `NODE_VERSION: "20"`.
- Job `backend-lint`: checkout, setup-python 3.12 with pip cache, install `backend/requirements.txt` and `backend/requirements-dev.txt`, `ruff check .`, `ruff format --check .`, `mypy analytics backend`, `lint-imports`.
- Job `backend-test`: `postgres:16-alpine` service (`POSTGRES_USER: echowell`, `POSTGRES_PASSWORD: ci-only-postgres`, `POSTGRES_DB: echowell_test`, health command `pg_isready`), env `APP_ENV: test` and the `ci-only-*` database URLs and settings of the TRD 16 outline, `JWT_SECRET` generated per run with `openssl rand -hex 32`, then one pytest invocation over `tests/unit tests/integration tests/validation` (and `tests/contract tests/security` as soon as they contain tests) with `-p no:randomly`, writing `build/junit.xml`; upload `build/` as artifact `backend-reports`.
- Job `frontend`: working directory `frontend`, setup-node 20 with npm cache on `frontend/package-lock.json`, `npm ci`, `npm run lint`, `npm run typecheck`, `npm run format:check`, `npm run test:coverage`, `npm run build`; upload `frontend/coverage/` as `frontend-coverage`.

## Out of Scope

- Jobs `repo-hygiene`, `openapi-contract`, `security-audit`, `docker-build`, the coverage-gate steps (CIC-016), the `--validation-report` option, branch protection (CIC-070) and E2E/performance workflows (FEAT-078, FEAT-080).
- The migration round-trip step of `backend-test` (CIC-015): it is added when FEAT-008 delivers the migrations (Phase 4 checkpoint PR of Block 3 updates `ci.yml`; the full form is audited in FEAT-078). The provisioning step can run from Phase 3, because FEAT-006 delivers `database/roles/provision_login_roles.sql` and `alembic.ini` in Phase 3 (TRD 24 D-90); this job set is the Phase 3 state of `ci.yml` fixed by D-94.
- Deploy workflows (FEAT-086).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-007-FR-01 | `ci.yml` shall run on every pull request, on every push to `main`, and on manual dispatch. | CIC-010 |
| FEAT-007-FR-02 | `backend-lint` shall fail on any `ruff check` finding, `ruff format --check` difference, `mypy` error (strict for `analytics/`) or import-linter contract violation. | CIC-011, AC-ARC-01 |
| FEAT-007-FR-03 | `backend-test` shall use a `postgres:16-alpine` service container and never SQLite; the test suite receives the database through `DATABASE_URL` with `APP_ENV=test`. | CIC-012, TST-002 |
| FEAT-007-FR-04 | `backend-test` shall run the unit, integration and validation suites in one pytest invocation and fail if any test fails or errors. | CIC-013 |
| FEAT-007-FR-05 | The `frontend` job shall run `npm ci`, `npm run lint` (`--max-warnings=0`), `npm run typecheck`, `npm run format:check`, `npm run test:coverage` and `npm run build` in that order, failing on any non-zero exit. | CIC-017, FE-202 |
| FEAT-007-FR-06 | The workflow shall use `permissions: contents: read`. | CIC-024 |
| FEAT-007-FR-07 | Actions shall be pinned to a major version tag only for publishers `actions/*`, `docker/*` and `microsoft/playwright`; any other action shall be pinned to a full commit SHA. | CIC-025 |
| FEAT-007-FR-08 | `ci.yml` shall use no repository secret; `JWT_SECRET` is generated per run with `openssl rand -hex 32`; database passwords are `ci-only-*` throwaway values. | CIC-026, ENV-041 |
| FEAT-007-FR-09 | All jobs shall run on GitHub-hosted `ubuntu-24.04` runners. | CIC-027 |
| FEAT-007-FR-10 | The legacy CI stub, if present, shall be replaced by this workflow, keeping the job ids `backend-lint`, `backend-test` and `frontend` used by branch protection later. | D-55, TST-150 |

## Inputs

- Repository checkout on PR or push; `backend/requirements*.txt` (FEAT-002); `pyproject.toml` test configuration (FEAT-005); `frontend/package.json` scripts and lockfile (FEAT-004).

## Outputs

- Status checks `backend-lint`, `backend-test`, `frontend` on every PR.
- Artifacts `backend-reports` (`build/junit.xml`) and `frontend-coverage` (retention 30 days).

## Data Flow

GitHub event (PR, push, dispatch) → three parallel jobs on `ubuntu-24.04` → `backend-lint` installs Python deps and runs static checks → `backend-test` starts the `postgres:16-alpine` service, waits for health, runs pytest with `DATABASE_URL` pointing at the service → `frontend` installs npm deps and runs lint, typecheck, format check, tests with coverage and build → each job reports a status check and uploads its artifact.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-005, FEAT-004

- FEAT-005 provides the pytest layout, markers and database fixture that `backend-test` runs.
- FEAT-004 provides the frontend scripts and lockfile that the `frontend` job runs.

Features that build directly on this one (BACKLOG.md §4): FEAT-078.

## Database Impact

None on persistent databases. `backend-test` uses an ephemeral `echowell_test` database in the service container.

## API Impact

None.

## Frontend Impact

None in code; the `frontend` job builds and tests the app.

## Analytics Impact

None; `lint-imports` enforces `analytics/` purity in CI.

## Security Requirements

- No secrets in `ci.yml` (CIC-026); `ci-only-*` placeholders only (ENV-041); `contents: read` (CIC-024).
- GitHub-hosted runners only (public repository, untrusted fork PRs; CIC-027).
- Third-party actions pinned per CIC-025.

## Error Handling

- Any failing step fails its job and the PR status check; no `continue-on-error` on required steps.
- Service container not healthy: the job fails after the health retries; rerun manually after fixing the cause.

## Logging Requirements

- Job logs on GitHub Actions; JUnit XML in `backend-reports`. No secrets are echoed (generated `JWT_SECRET` is written to `$GITHUB_ENV`, not printed). No audit rows.

## Testing Requirements

- Workflow validation: open a test PR with a deliberate `ruff` violation → `backend-lint` fails; revert → passes.
- A deliberately failing unit test → `backend-test` fails.
- A deliberate ESLint warning in `frontend/` → `frontend` fails (FE-203).
- Inspection: `grep -r "secrets\." .github/workflows/ci.yml` returns nothing (CIC-026); every `uses:` line follows CIC-025.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-007-AC-01 | A pull request triggers `ci.yml` with jobs `backend-lint`, `backend-test` and `frontend`, all green on the Phase 3 tree. | CIC-010, TST-150 |
| FEAT-007-AC-02 | A PR introducing a `ruff` finding, a `mypy` error or a forbidden import in `analytics/` fails `backend-lint`. Verified by: Workflow validation (open a test PR with a deliberate `ruff` violation → `backend-lint` fails). | CIC-011, AC-ARC-01 |
| FEAT-007-AC-03 | The `backend-test` log shows the `postgres:16-alpine` service and pytest connecting through `DATABASE_URL`; a failing test fails the job. | CIC-012, CIC-013 |
| FEAT-007-AC-04 | The `frontend` job runs the six npm commands in the CIC-017 order and fails on an ESLint warning. Verified by: Test (A deliberate ESLint warning in `frontend/` → `frontend` fails (FE-203)). | CIC-017, FE-202 |
| FEAT-007-AC-05 | `grep -n "secrets\." .github/workflows/ci.yml` returns nothing and `grep -n "permissions" .github/workflows/ci.yml` shows `contents: read` only. Verified by: Inspection (run the command in the criterion and check its output). | CIC-024, CIC-026 |
| FEAT-007-AC-06 | Every job declares `runs-on: ubuntu-24.04`; every `uses:` references `actions/*`, `docker/*` or `microsoft/playwright` by major tag or another action by full SHA. | CIC-025, CIC-027 |

## Definition of Done

- All FEAT-007 acceptance criteria pass on a real PR in the repository.
- Job ids match TRD 16 §4.2 so FEAT-078 can extend the file and CIC-070 can reference them.
- Batch report lists IDs and command results (AGT-022).

## Implementation Notes

- Copy the TRD 16 §4.2 outline for these three jobs and omit only the steps owned by later features (provisioning, migrations round-trip, coverage gates, validation report); keep the environment block so later additions are small diffs.
- Until `tests/validation/` contains tests, pytest exits with code 5 when no tests are collected for an empty path set; pass the directories that exist or rely on the FEAT-005 tree containing at least one test per directory listed.
- Use `-p no:randomly` in the PR job (deterministic order); the nightly randomised run is FEAT-080 (CIC-037).
