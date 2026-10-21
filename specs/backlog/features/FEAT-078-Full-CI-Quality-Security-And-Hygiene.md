# FEAT-078 Full CI quality, security and hygiene gates (ci.yml) and branch protection

| Field | Value |
|---|---|
| Epic | DevOps & Deployment |
| Build phase | Phase 9 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-007, FEAT-038, FEAT-059, FEAT-077 |
| Status | Not Started |

## Purpose

Complete `.github/workflows/ci.yml` so that every pull request and every push to `main` runs all required quality, security and hygiene gates: repository hygiene (no audio, no `.env`, file size, forbidden terms, LLM dependencies, Conventional Commit titles), backend lint with import-linter, the full pytest run including the R01–R10 validation suite with coverage gates, the OpenAPI drift check, the frontend job, the security audit (pip-audit, npm audit, gitleaks, Bandit) and the image build check; then configure branch protection and Dependabot so nothing merges without these checks. This turns the TRD rules on answer-key reproduction, no audio, no LLM and no secrets into automatic merge blockers.

## Business Context

- BR-15: the validation suite gates every merge (CIC-013, CIC-014); an answer-key regression cannot be merged (AC-CIC-01).
- BR-01, BR-16: audio files, `.env` files, secrets and vulnerable dependencies fail CI (CIC-020, CIC-021, CIC-019, CIC-115).
- BR-17: GitHub Actions CI is part of the fixed stack (SRC-01).
- BR-18 and RSK-10: forbidden wording, "Edge4Care" and LLM SDKs fail `repo-hygiene` (CIC-114).

## Referenced TRDs

- TRD 16 CIC-010..CIC-027 (`ci.yml` jobs and rules), CIC-070, CIC-071, CIC-072 (required checks, waiver), CIC-080..CIC-083 (caching), CIC-100, CIC-101, CIC-102 (reports and artifacts), CIC-110, CIC-111, CIC-113, CIC-114, CIC-115, §4.2 outline, §8 Implementation Notes.
- TRD 13 TST-006, TST-083, TST-140, TST-141, TST-142, TST-143, TST-144, TST-150, TST-153.
- TRD 12 SEC-052, SEC-053, SEC-128, SEC-150..SEC-156.
- TRD 18 GIT-010, GIT-110, GIT-111, GIT-112, GIT-113, §4.12 `dependabot.yml` outline.
- TRD 01 ARC-041 (analytics purity, import-linter contracts).
- TRD 25 AGT-004, AGT-007, AGT-019, AC-AGT-02, AC-AGT-03, AC-AGT-11; TRD 24 D-39, D-51, D-55, D-72.
- TRD 01 ARC-104 (no LLM component and no ML model in the processing path).

## Scope

- Replace the Phase 3 `ci.yml` (FEAT-007: `backend-lint`, `backend-test`, `frontend`) with the full TRD 16 §4.2 outline: jobs `repo-hygiene`, `backend-lint`, `backend-test`, `openapi-contract`, `frontend`, `security-audit`, `docker-build`; triggers `pull_request`, `push` to `main`, `workflow_dispatch`; concurrency `ci-${{ github.ref }}` cancelling only on pull requests; `permissions: contents: read`; `runs-on: ubuntu-24.04`; `timeout-minutes` ≤ 20 per job.
- `backend-test`: provisioning with `database/roles/provision_login_roles.sql` as superuser, `alembic upgrade head`, `alembic downgrade base && alembic upgrade head`, one pytest invocation over `tests/unit tests/integration tests/contract tests/security tests/validation` with `-p no:randomly`, coverage XML/HTML, junit and `--validation-report=docs/reports/ALGORITHM_VALIDATION_REPORT.md`, then the coverage gates for `analytics/` (95) and `backend/` (85); artifact `backend-reports` (30 days); job summary with the R01–R10 table and coverage percentages.
- `pyproject.toml` `[tool.importlinter]` contracts forbidding `analytics` from importing `backend`, `sqlalchemy`, `psycopg`, `fastapi`, `httpx`, `requests` and `random`; coverage exclusions limited to TST-144.
- `.gitleaks.toml` allow-list limited to the `local-dev-only-*` and `ci-only-*` placeholders in `.env.development.example`, `docker-compose.yml` and `ci.yml`.
- `.github/dependabot.yml` exactly as TRD 18 §4.12 (pip `/backend`, npm `/frontend` weekly; github-actions `/` and docker `/backend` monthly; target `main`).
- Branch protection (ruleset) on `main`, the only long-lived branch (D-99), per GIT-010 with the eight required checks of CIC-070 (`repo-hygiene`, `backend-lint`, `backend-test`, `openapi-contract`, `frontend`, `security-audit`, `docker-build`, `playwright`) and "branch up to date before merging"; secret scanning with push protection where available.
- `SECURITY_EXCEPTIONS.md` format for time-boxed waivers (TST-136, CIC-072).

## Out of Scope

- `e2e.yml` and its `playwright`, `performance`, `lighthouse`, `nightly-validation` jobs (FEAT-080); this feature only lists `playwright` as a required check.
- `deploy-staging.yml`, `deploy-production.yml` (FEAT-086) and `uptime.yml` (FEAT-085).
- Writing the tests themselves (validation suite FEAT-059, contract tests FEAT-038, security suite FEAT-039).
- Any workflow other than the five of CIC-002.

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-078-FR-01 | `ci.yml` shall run on every pull request, every push to `main`, and on manual dispatch, with default `permissions: contents: read` and no repository secret; the test JWT_SECRET shall be generated per run with `openssl rand -hex 32`. | CIC-010, CIC-024, CIC-026 |
| FEAT-078-FR-02 | `repo-hygiene` shall fail on any tracked file with an audio extension (wav, mp3, flac, m4a, ogg, opus, aac, wma, aif, aiff, amr, webm, caf, pcm), any tracked `.env` or `.env.*` other than `*.example`, any tracked file above 10 MB, and (pull requests only) a title that is not a Conventional Commit header of types feat, fix, docs, chore, refactor, test, ci, build, perf, release. | CIC-020, CIC-021, CIC-022 |
| FEAT-078-FR-03 | `repo-hygiene` shall fail when "Edge4Care" appears in a tracked file outside `specs/` and `docs/reports/`, when "diagnoses" or "severity" appears as a word in `frontend/app`, `frontend/components` or `frontend/lib/wording.ts`, or when an LLM SDK of SEC-128 appears in `backend/requirements*.txt` or `frontend/package.json`. | CIC-114, SEC-128, AGT-004, AGT-019 |
| FEAT-078-FR-04 | `backend-lint` shall fail on any `ruff check` finding, any `ruff format --check` difference, any `mypy` error (strict for `analytics/`) or any import-linter contract violation. | CIC-011, CIC-115, ARC-041 |
| FEAT-078-FR-05 | `backend-test` shall run on a `postgres:16-alpine` service, provision extensions and login roles first, use DATABASE_URL = `echowell_app_login`, DATABASE_MIGRATION_URL = `echowell_migrator_login`, DATABASE_READONLY_URL = `echowell_readonly_login`, apply `alembic upgrade head`, then `alembic downgrade base` and `alembic upgrade head`, and fail on any migration error. | CIC-012, CIC-015, D-72 |
| FEAT-078-FR-06 | `backend-test` shall run unit, integration, contract, security and validation suites in one pytest invocation, fail on any failure or error, and compare R01–R10 at absolute tolerance 1e-6 with exact strings. | CIC-013, CIC-014, TST-083 |
| FEAT-078-FR-07 | Line coverage gates shall be `analytics/` ≥ 95 % and `backend/` ≥ 85 % in `backend-test`, and `frontend/` ≥ 80 % in the `frontend` job (via `vitest.config.ts`). | CIC-016, CIC-017, TST-140, TST-141, TST-142, D-39 |
| FEAT-078-FR-08 | `openapi-contract` shall fail when `python -m backend.cli export-openapi` differs from `docs/api_reference/openapi.json` or when `frontend/lib/api-types.ts` differs from the output of openapi-typescript. | CIC-018, D-51, AC-AGT-11 |
| FEAT-078-FR-09 | `frontend` shall run `npm ci`, `npm run lint` (`--max-warnings=0`), `npm run typecheck`, `npm run format:check`, `npm run test:coverage`, `npm run build`. | CIC-017 |
| FEAT-078-FR-10 | `security-audit` shall run `pip-audit` on runtime and dev requirements, `npm audit --audit-level=high --omit=dev`, `gitleaks detect` 8.x over the full history, and Bandit on `backend` and `analytics` failing at medium or higher severity. | CIC-019, CIC-115, SEC-052, SEC-151, SEC-152, SEC-153 |
| FEAT-078-FR-11 | `docker-build` shall build both images with Buildx `type=gha` caches and fail if the backend image runs as root or contains `.env`, `tests/`, `specs/` or `frontend/` under `/app`. | CIC-023, CIC-082 |
| FEAT-078-FR-12 | pip and npm downloads shall be cached keyed on `backend/requirements*.txt` and `frontend/package-lock.json`; `npm ci` shall always be used. | CIC-080, CIC-081, CIC-083 |
| FEAT-078-FR-13 | Every job shall set `timeout-minutes` ≤ 20; runners shall be GitHub-hosted `ubuntu-24.04`. | CIC-111, CIC-027 |
| FEAT-078-FR-14 | `backend-test` shall upload `backend-reports` (coverage, junit, `ALGORITHM_VALIDATION_REPORT.md`, `validation_results.json`) even on failure, write outputs to `build/`, never commit them, and print the R01–R10 table and coverage percentages to the job summary. | CIC-100, CIC-101, CIC-102 |
| FEAT-078-FR-15 | Branch protection on `main` shall require the eight checks of CIC-070, evaluated on the up-to-date merge, plus the GIT-010 rules (1 approval, stale-approval dismissal, CODEOWNERS, conversation resolution, no force push, no deletion, no admin bypass). | CIC-070, CIC-071, GIT-010, TST-150 |
| FEAT-078-FR-16 | Third-party actions shall be pinned per CIC-025 (major tags only for `actions/*`, `docker/*`, `microsoft/playwright`; full commit SHA otherwise). | CIC-025, SEC-154 |
| FEAT-078-FR-17 | `.github/dependabot.yml` shall match TRD 18 §4.12, target `main`, and Dependabot security updates and alerts shall be enabled; dependency PRs merge only with all required checks green. | GIT-110, GIT-113, SEC-150 |
| FEAT-078-FR-18 | A security-audit failure on an unchanged dependency may be waived for at most 7 days with an ignore entry that references a tracking issue and is recorded in `SECURITY_EXCEPTIONS.md` with an expiry date. | CIC-072, TST-136 |
| FEAT-078-FR-19 | A merge shall be blocked when any test was skipped without a `reason=` naming a requirement or OQ ID (conftest hook). | TST-153 |
| FEAT-078-FR-20 | The CI dependency scan shall fail when an LLM SDK or a machine-learning model dependency appears in the processing path (`backend/`, `analytics/`, `frontend/`). | ARC-104, AGT-004, AGT-005 |

## Inputs

- The Phase 3 `ci.yml` of FEAT-007; the contract export of FEAT-038; the validation suite and `--validation-report` option of FEAT-059; the images of FEAT-077.
- `backend/requirements.txt`, `backend/requirements-dev.txt` (TRD 16 §6 tool list), `frontend/package.json` and `package-lock.json`, root `pyproject.toml`.

## Outputs

- `.github/workflows/ci.yml` (full), `.github/dependabot.yml`, `.gitleaks.toml`, `pyproject.toml` `[tool.importlinter]` and `[tool.coverage]` sections, `SECURITY_EXCEPTIONS.md` (empty table with header).
- Repository settings: branch protection ruleset on `main` (screenshot in PR #3 at the Phase 9 checkpoint, AC-GIT-01).
- Per-run artifacts `backend-reports` and `frontend-coverage`.

## Data Flow

Pull request or push → seven parallel `ci.yml` jobs → each posts a status check named by its job id → branch protection compares the set with the eight required checks (the eighth, `playwright`, comes from `e2e.yml`, FEAT-080) → merge allowed only when all are green → Railway "Wait for CI" (FEAT-081) deploys only commits whose checks passed.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-007, FEAT-038, FEAT-059, FEAT-077

- [FEAT-007](FEAT-007-CI-Workflow-Core-Jobs.md) CI workflow core jobs (extended here).
- [FEAT-038](FEAT-038-OpenAPI-Contract-Export-And-Drift-Check.md) OpenAPI contract export and drift check (`export-openapi`, committed contract).
- [FEAT-059](FEAT-059-R01-R10-Validation-Cases-Global-Checks.md) R01–R10 validation cases and validation report.
- [FEAT-077](FEAT-077-Production-Container-Images-Compose-Demo-Profile.md) Production container images (built and inspected by `docker-build`).

Features that build directly on this one (BACKLOG.md §4): FEAT-080.

## Database Impact

- CI creates an ephemeral `echowell_test` database in the service container, runs the provisioning script and the full Alembic round trip; no hosted database is touched (CIC-003).
- No table is created, altered or read by this feature's own code.

## API Impact

None exposed. `openapi-contract` consumes the generated OpenAPI document (`python -m backend.cli export-openapi`) without a database.

## Frontend Impact

None in application code. The `frontend` job runs lint, typecheck, format check, Vitest coverage and build; `frontend/lib/api-types.ts` is regenerated and diffed.

## Analytics Impact

None in code. The import-linter contracts enforce `analytics/` purity (ARC-041) and the validation suite enforces the algorithm results; coverage of `analytics/` must stay ≥ 95 %.

## Security Requirements

- No secrets in `ci.yml` (CIC-026); fork PRs get no secrets and `pull_request_target` is not used (CIC-091).
- gitleaks over full history with the narrow placeholder allow-list (CIC-115); secret scanning with push protection enabled where the plan allows (SEC-053).
- Least-privilege `permissions` per workflow (CIC-024, SEC-154).
- Critical vulnerabilities in deployed components patched within 7 days, high within 30 days (SEC-156).

## Error Handling

- Any failing job blocks the merge (CIC-070); artifacts are uploaded with `if: always()` so failures can be analysed.
- A newly disclosed vulnerability on an unchanged dependency is handled by a ≤ 7-day waiver with a tracking issue (CIC-072).
- If the 90th percentile of `ci.yml` exceeds 12 minutes for a week, split `backend-test` into a matrix (CIC-113).

## Logging Requirements

- Job logs never echo secrets; values are passed through `env:` (CIC-092).
- The job summary shows the R01–R10 pass/fail table and coverage percentages (CIC-102).
- No application audit rows are produced.

## Testing Requirements

- CI dry run on PR #3 at the Phase 9 checkpoint (TRD 25 §4.6 Phase 9 Required tests).
- Negative tests per AC-CIC-01..AC-CIC-04 executed on throwaway branches: composite sign change, `tests/fixtures/sample.wav`, endpoint without contract update, PR title "Updated stuff".
- Grep checks AC-AGT-02, AC-AGT-03 reproduced by `repo-hygiene` and the TDV-011 scan inside the validation suite.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-078-AC-01 | A PR that changes one composite sign in `analytics/config.py` fails `backend-test` and cannot be merged. Verified by: Test (composite sign change, `tests/fixtures/sample.wav`, endpoint without contract update, PR title "Updated stuff"). | AC-CIC-01 |
| FEAT-078-AC-02 | A PR that adds `tests/fixtures/sample.wav` fails `repo-hygiene`. | AC-CIC-02, CIC-020 |
| FEAT-078-AC-03 | A PR that adds an endpoint without updating `docs/api_reference/openapi.json` fails `openapi-contract`. Verified by: Test (the test method of CIC-018, applied to the condition stated in the criterion). | AC-CIC-03, CIC-018 |
| FEAT-078-AC-04 | A PR titled "Updated stuff" fails `repo-hygiene`; "feat(api): add device panel endpoint" passes. Verified by: Test (composite sign change, `tests/fixtures/sample.wav`, endpoint without contract update, PR title "Updated stuff"). | AC-CIC-04, CIC-022 |
| FEAT-078-AC-05 | `ci.yml` on `main` completes all required checks in under 15 minutes and uploads `backend-reports` containing `ALGORITHM_VALIDATION_REPORT.md` with 10 of 10 residents passing and `validation_results.json`. Verified by: Analysis (the analysis method of CIC-110, applied to the condition stated in the criterion). | AC-CIC-05, CIC-110 |
| FEAT-078-AC-06 | `grep -r "secrets\." .github/workflows/ci.yml` returns nothing. Verified by: Inspection (run the command in the criterion and check its output). | CIC-026, AC-CIC-06 |
| FEAT-078-AC-07 | Branch protection for `main` lists exactly the eight required checks of CIC-070. Verified by: Inspection (review of `main` against the cited requirements). | AC-CIC-08, AC-GIT-01 |
| FEAT-078-AC-08 | A PR adding `openai` to `backend/requirements.txt`, or the string "Edge4Care" to a file under `backend/`, fails `repo-hygiene`. Verified by: Test (Grep checks AC-AGT-02, AC-AGT-03 reproduced by `repo-hygiene` and the TDV-011 scan inside the validation suite). | CIC-114, AC-AGT-03 |
| FEAT-078-AC-09 | Coverage below 95 % for `analytics/`, 85 % for `backend/` or 80 % for `frontend/` fails the respective job. Verified by: Test (the test method of CIC-016, applied to the condition stated in the criterion). | CIC-016, CIC-017, AC-TST-06 |
| FEAT-078-AC-10 | A committed fake key matching a gitleaks rule (outside the allow-list) fails `security-audit`; a Bandit medium finding in `backend/` fails it too. Verified by: Test (the test method of CIC-115, applied to the condition stated in the criterion). | CIC-115, SEC-052 |

## Definition of Done

- All FEAT-078 acceptance criteria pass.
- All FEAT-078 acceptance criteria demonstrated (negative cases on throwaway branches, then closed).
- Every job has `timeout-minutes` ≤ 20 and runs on `ubuntu-24.04`.
- Branch protection screenshot attached to PR #3 at the Phase 9 checkpoint (AC-GIT-01); `CONFIGURATION_VALIDATION_REPORT.md` (FEAT-087) records the check list.
- Batch report entry (AGT-022).

## Implementation Notes

- Job ids are the status check names; do not rename them (TRD 16 §8).
- `openapi-contract` must not need a database: the app factory connects lazily in the lifespan handler (TRD 16 §8).
- Register `--validation-report` with `pytest_addoption` in `tests/validation/conftest.py` and write the report in `pytest_sessionfinish` (owned by FEAT-059; only invoked here).
- `npm audit --omit=dev` deliberately ignores build-only packages; Dependabot still raises them.
- Action pinning follows TRD 16 CIC-025 (major tags for `actions/*`, `docker/*` and `microsoft/playwright`, full SHA otherwise); TRD 12 SEC-154 was aligned to CIC-025 in the PR #2 consistency fixes.
