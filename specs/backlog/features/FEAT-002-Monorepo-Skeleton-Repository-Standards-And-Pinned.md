# FEAT-002 Monorepo skeleton, repository standards and pinned dependencies

| Field | Value |
|---|---|
| Epic | Infrastructure |
| Build phase | Phase 3 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-001 |
| Status | Not Started |

## Purpose

Lay down the single-monorepo structure that every later feature fills in: the backend package tree, the empty `analytics/` modules with enforced import boundaries, `database/`, `tests/`, repository hygiene files (`.gitignore`, PR and issue templates, CODEOWNERS, editor and pre-commit configuration), Python tooling configuration, and exact dependency pins (psycopg 3 replacing `psycopg2-binary`). It contains no business logic; its value is that every later batch starts from the same layout, lint rules and versions.

## Business Context

- BR-17: one GitHub monorepo, FastAPI backend, Next.js frontend, PostgreSQL, GitHub Actions (ARC-016, GIT-001).
- BR-16: no secrets, `.env` files, audio or real data committed (GIT-080, GIT-091, GIT-092, AGT-016).
- BR-15 and BR-18: the `analytics/` package is pure and deterministic, enforced by import contracts from the first commit (ANL-002, ARC-041).

## Referenced TRDs

- TRD 01 ARC-010..ARC-019 (containers, roles, monorepo), ARC-050..ARC-055 (layout, dependency direction, thin service adapters, config-driven parameters, feature-name mapping, facility timezone), §4.6 layout, §8 implementation notes.
- TRD 07 ANL-001..ANL-005, §4.2 module list.
- TRD 18 GIT-001..GIT-004, GIT-010..GIT-015, GIT-020..GIT-024, GIT-030..GIT-037, GIT-040..GIT-045, GIT-050..GIT-056, GIT-060..GIT-064, GIT-070..GIT-073, GIT-080..GIT-084, GIT-090..GIT-097, GIT-100; §4.5 code style table; §4.11 `.gitignore`; PR template and CODEOWNERS blocks.
- TRD 03 NFR-080..NFR-089.
- TRD 16 §6 (`backend/requirements-dev.txt` tool list, root `pyproject.toml` sections).
- TRD 25 AGT-010, AGT-016, AGT-024, §4.6 Phase 3, §4.7 version pins.
- TRD 24 D-24, D-53, D-61.

## Scope

- Directory tree of TRD 01 §4.6: `backend/` with `api/`, `models/`, `schemas/`, `services/`, `repositories/`, `core/`, `jobs/` (with `nightly_run.py` entry-point module), `alembic/`, `cli.py`; `analytics/` module files of TRD 07 §4.2 plus `__init__.py`; `database/` (`seeds/`, `roles/`); `tests/` (directories are populated by FEAT-005); `docs/`.
- Keep every existing skeleton file at its path and fill it in later: `backend/api/{alarms,analytics,health,residents,sessions}.py`, `backend/models/{alarm,baseline,resident,score,session}.py`, `backend/services/{baseline,cusum,ingestion,morning_adjustment,scoring,speaker_screen,validation}.py`, existing `analytics/*.py`.
- Create missing `analytics/` modules: `config.py`, `robust_stats.py`, `speaker_screen.py`, `day_ledger.py`, `data_alerts.py`, `aggregates.py`, `pipeline.py`, `__init__.py` (TRD 01 §8).
- Root `pyproject.toml` with `[tool.ruff]`, `[tool.mypy]` and `[tool.importlinter]` contracts (the `[tool.pytest.ini_options]` and `[tool.coverage]` blocks are added by FEAT-005).
- `backend/requirements.txt` with exact pins per TRD 25 §4.7 (`psycopg[binary]` 3.x, never `psycopg2-binary`) and `backend/requirements-dev.txt` with the TRD 16 §6 tool list.
- `.gitignore` of TRD 18 §4.11; `.editorconfig`; `.pre-commit-config.yaml`; `.github/pull_request_template.md`; `.github/CODEOWNERS`; `.github/ISSUE_TEMPLATE/bug_report.yml` and `feature_request.yml` with blank issues disabled; `.github/dependabot.yml` (AC-GIT-06).
- `README.md` content required by GIT-056.

## Out of Scope

- Application factory, settings and health endpoint (FEAT-003).
- Frontend scaffold under `frontend/` (FEAT-004).
- Test directories, `conftest.py`, pytest markers and coverage configuration (FEAT-005).
- Docker Compose and Dockerfiles (FEAT-006); CI workflow (FEAT-007; full gates FEAT-078).
- Branch protection and repository settings in GitHub (GIT-010, GIT-081 are applied with FEAT-078); GitHub teams creation by the organisation owner (GIT-037) is an organisational action, only referenced here by CODEOWNERS.
- Any business logic, stage implementation or migration.
- A `LICENSE` file (GIT-090: none until the owner chooses a licence).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-002-FR-01 | The repository shall follow the TRD 01 §4.6 layout in the single repo `EchoWellApp/echowell`; no new top-level directory beyond that layout is added. | ARC-016, GIT-001, GIT-002 |
| FEAT-002-FR-02 | Every existing skeleton file listed in ARC-050 shall remain at its original path, unrenamed; missing modules are added next to them. | ARC-050, GIT-003, AGT-010, D-24 |
| FEAT-002-FR-03 | `analytics/` shall be the root Python 3.12 package containing exactly the modules of TRD 07 §4.2 plus `__init__.py`, importable as `import analytics`. | ANL-001, ANL-004, ARC-013, D-61 |
| FEAT-002-FR-04 | `pyproject.toml` shall define import-linter contracts that fail when any `analytics.*` module imports `backend`, `sqlalchemy`, `psycopg`, `fastapi`, `httpx`, `requests`, `os` or `random`, and a layers contract enforcing `backend.api → backend.services → backend.repositories → backend.models`. | ANL-002, ARC-041, ARC-051, AC-ARC-01, TST-021 |
| FEAT-002-FR-05 | `analytics/` runtime dependencies shall be limited to the standard-library modules of ANL-005 and `numpy` 2.x; `pandas` and `openpyxl` appear only in `backend/requirements-dev.txt`. | ANL-005 |
| FEAT-002-FR-06 | `backend/requirements.txt` shall pin exact versions consistent with TRD 25 §4.7 (Python 3.12, FastAPI 0.115.x, SQLAlchemy 2.0.x, Alembic 1.13.x, Pydantic 2.x, `psycopg[binary]` 3.x, numpy 2.x) and shall not contain `psycopg2`. | AGT-024, NFR-089, D-53, AC-AGT-11 |
| FEAT-002-FR-07 | `backend/requirements-dev.txt` shall be the single dev-tool list of TRD 16 §6 (ruff, mypy, pytest 8.x, pytest-cov, pytest-randomly, time-machine, httpx, testcontainers-python 4.x, openapi-core 0.19.x, Hypothesis, openpyxl 3.1.x, import-linter 2.x, Bandit, pip-audit). | TRD 16 §6 |
| FEAT-002-FR-08 | `pyproject.toml` `[tool.ruff]` and `[tool.mypy]` shall match TRD 18 §4.5 (`target-version = "py312"`, `line-length = 100`, the listed rule selection and `tests/**` S101 ignore; `strict = true` for `analytics.*`, `disallow_untyped_defs` and `warn_unused_ignores` for `backend.*`, `pydantic.mypy` plugin). | GIT-040, GIT-041, NFR-080, NFR-081 |
| FEAT-002-FR-09 | `.gitignore` shall contain at least the TRD 18 §4.11 entries while keeping `database/schema.sql`, `docs/api_reference/openapi.json` and `docs/reports/` tracked. | GIT-100, AGT-016 |
| FEAT-002-FR-10 | `.github/pull_request_template.md` and `.github/CODEOWNERS` shall reproduce the TRD 18 blocks (template sections and the team ownership lines for `analytics/`, `tests/validation/`, `database/seeds/`, `backend/alembic/`, `specs/`, algorithm TRDs, `.github/`, deploy files). | GIT-032, GIT-033, GIT-037 |
| FEAT-002-FR-11 | Issue templates `bug_report.yml` and `feature_request.yml` shall exist with the GIT-072 fields, and blank issues shall be disabled. | GIT-072 |
| FEAT-002-FR-12 | `.editorconfig` and `.pre-commit-config.yaml` (ruff, ruff-format, prettier, audio-extension and `.env` checks) shall be provided. | GIT-044, GIT-045, TRD 18 §4.5 |
| FEAT-002-FR-13 | `README.md` shall state the project purpose, the sentence "EchoWell is a research system, not a medical device; it detects a change and prompts a check-in, it does not diagnose", the local quick start and links to `specs/TRD/` and `docs/`. | GIT-056, AGT-018 |
| FEAT-002-FR-14 | No secret, `.env` file, audio file, real resident data, third-party-licensed document, font file or Git LFS pointer shall be added. | GIT-080, GIT-091..GIT-097, AGT-016 |
| FEAT-002-FR-15 | Backend modules `backend/core/`, `backend/services/`, `backend/repositories/`, `backend/schemas/`, `backend/models/`, `backend/jobs/` and `backend/cli.py` shall exist as importable modules (module docstring citing the owning TRD) with no business logic. | TRD 25 §4.6 Phase 3 Outputs and DoD |

## Inputs

- `docs/design/Repository_Structure.md` from FEAT-001.
- TRD 01 §4.6, TRD 07 §4.2, TRD 18 §4.5 and §4.11 and template blocks, TRD 16 §6, TRD 25 §4.7.
- The existing skeleton files in the repository.

## Outputs

- The directory tree and empty modules listed in Scope.
- `pyproject.toml`, `backend/requirements.txt`, `backend/requirements-dev.txt`.
- `.gitignore`, `.editorconfig`, `.pre-commit-config.yaml`, `.github/pull_request_template.md`, `.github/CODEOWNERS`, `.github/ISSUE_TEMPLATE/*`, `.github/dependabot.yml`, updated `README.md`.

## Data Flow

No runtime data flow. At development time: a developer or agent runs `ruff check .`, `ruff format --check .`, `mypy analytics backend` and `lint-imports` against the tree; the import-linter contracts read `pyproject.toml` and fail on any forbidden import edge; pip installs exactly the pinned versions from `backend/requirements.txt` and `backend/requirements-dev.txt`.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-001

- FEAT-001 supplies `docs/design/Repository_Structure.md`, the agreed layout and dependency diagram this feature materialises.

Features that build directly on this one (BACKLOG.md §4): FEAT-003, FEAT-004, FEAT-005, FEAT-040.

## Database Impact

None. `database/` and `database/roles/` directories are created empty; schema work starts in FEAT-008.

## API Impact

None. Router modules exist as empty files; endpoints are added from FEAT-003 onward.

## Frontend Impact

None. `frontend/` is scaffolded by FEAT-004; only `.gitignore` entries for `frontend/` build outputs are added here.

## Analytics Impact

Module files of TRD 07 §4.2 are created without logic; import contracts (ANL-002) and the dependency limit (ANL-005) apply from now on. No algorithm is implemented.

## Security Requirements

- No secret in any file, including examples and docs (GIT-080); `.env` and `.env.*` ignored except the three example templates (TRD 18 §4.11).
- No audio file under any name (GIT-091); no real resident data or dumps (GIT-092); no third-party-licensed documents (GIT-093, GIT-094).
- CODEOWNERS routes `analytics/`, `tests/validation/`, `database/seeds/` and `backend/alembic/` to the algorithm team (GIT-032).

## Error Handling

- If an existing skeleton file conflicts with the layout, it is kept and filled in, never moved (AGT-010); a missing directory is added.
- If a pinned version cannot be installed on Python 3.12, the agent stops and records an OQ in TRD 24 rather than changing a major version (AGT-024, AGT-009).

## Logging Requirements

None at runtime. The Phase 3 batch report lists requirement IDs, commands and results (AGT-022). No audit records.

## Testing Requirements

- Static checks: `ruff check .`, `ruff format --check .`, `mypy analytics backend`, `lint-imports` (TRD 16 `backend-lint` job; GIT-040, GIT-041).
- Import-boundary test: `lint-imports` fails if a deliberate `import sqlalchemy` is added to an `analytics/` module (AC-ARC-01, TST-021); revert after the check.
- Inspection commands: `grep -n "psycopg2" backend/requirements.txt` returns nothing (AC-AGT-11); `git ls-files | grep -Ei '\.(wav|mp3|flac|m4a|ogg|opus|aac|webm)$'` returns nothing and `git ls-files | grep -E '(^|/)\.env' | grep -v example` returns nothing (AC-GIT-02).
- Skeleton presence: a check that every ARC-050 file still exists (AC-AGT-06).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-002-AC-01 | Every file listed in ARC-050 exists at its original path. Verified by: Skeleton presence (a check that every ARC-050 file still exists (AC-AGT-06)). | AC-AGT-06, ARC-050 |
| FEAT-002-AC-02 | `ls analytics/` lists exactly the 16 modules of TRD 07 §4.2 plus `__init__.py`, and `python -c "import analytics"` exits 0. Verified by: Test (run the command in the criterion against the stated environment and check the stated result). | ANL-001, ANL-004 |
| FEAT-002-AC-03 | `lint-imports` exits 0 on the tree and exits non-zero when `import sqlalchemy` is added to any `analytics/` module. Verified by: Import-boundary test (TST-021). | AC-ARC-01, ANL-002 |
| FEAT-002-AC-04 | `grep -n "psycopg2" backend/requirements.txt` returns no match and `grep -n "psycopg\[binary\]" backend/requirements.txt` returns exactly one pinned line; every line of `backend/requirements.txt` has an `==` pin. Verified by: Inspection (run the command in the criterion and check its output). | AC-AGT-11, D-53, AGT-024 |
| FEAT-002-AC-05 | `ruff check .`, `ruff format --check .` and `mypy analytics backend` exit 0. Verified by: Static checks (`ruff check .`, `ruff format --check .`, `mypy analytics backend`, `lint-imports` (TRD 16 `backend-lint` job). | AC-GIT-05, NFR-080, NFR-081 |
| FEAT-002-AC-06 | `.gitignore` contains every entry of TRD 18 §4.11, and `git check-ignore database/schema.sql docs/api_reference/openapi.json` reports neither path as ignored. Verified by: Test (run the command in the criterion against the stated environment and check the stated result). | GIT-100 |
| FEAT-002-AC-07 | `.github/CODEOWNERS`, `.github/pull_request_template.md`, `.github/dependabot.yml` and both issue templates exist. Verified by: Import-boundary test (TST-021). | AC-GIT-06 |
| FEAT-002-AC-08 | `git ls-files` shows no audio file, no `.env` file other than the examples, and no `LICENSE` file. Verified by: Test (run the command in the criterion against the stated environment and check the stated result). | AC-GIT-02, GIT-090 |
| FEAT-002-AC-09 | `README.md` contains the exact GIT-056 sentence about research system and detection. Verified by: Inspection (the inspection method of GIT-056, applied to the condition stated in the criterion). | GIT-056 |

## Definition of Done

- All FEAT-002 acceptance criteria pass locally.
- No business logic is present in any created module (TRD 25 §4.6 Phase 3 DoD).
- Batch report lists IDs implemented and command results (AGT-022); the PR is delivered together with the other Phase 3 features (FEAT-003..FEAT-007) as one PR (AGT-013).

## Implementation Notes

- SQLAlchemy URLs use the `postgresql+psycopg://` scheme (TRD 01 §8).
- Do not create `pytest.ini`; pytest configuration lives only in `pyproject.toml` (TST-006, delivered by FEAT-005).
- Give each new module a docstring naming the TRD that owns it (NFR-085) so later agents know where to look.
- Keep the PR under about 1,500 changed lines excluding generated files (GIT-034); lockfiles do not count.
- The current `.gitignore` (`__pycache__/`, `.env`, `node_modules/`) is replaced, not appended to.
