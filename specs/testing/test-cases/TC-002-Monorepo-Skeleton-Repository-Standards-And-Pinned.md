# FEAT-002 Monorepo skeleton, repository standards and pinned dependencies

## Feature Description

FEAT-002 materialises the TRD 01 §4.6 monorepo layout in `EchoWellApp/echowell`: the root `analytics/` package with exactly the 16 modules of TRD 07 §4.2, the empty backend layer modules, `pyproject.toml` with ruff, mypy and import-linter configuration, exact-pinned `backend/requirements.txt` and `backend/requirements-dev.txt`, `.gitignore`, `.editorconfig`, `.pre-commit-config.yaml`, the `.github/` templates (PR template, CODEOWNERS, issue templates, Dependabot) and the README purpose sentence (GIT-056). It also keeps every ARC-050 skeleton file at its original path. It has no runtime behaviour: test cases are command runs and file inspections.

## Preconditions

- A clean clone of the repository (no uncommitted changes) on the branch under test.
- Python 3.12 virtual environment with `pip install -r backend/requirements.txt -r backend/requirements-dev.txt` completed.
- `git`, `grep` available. Commands are run from the repository root.
- For TC-002-04 a scratch copy of the working tree you may modify and revert (`git stash` or `git checkout -- .` afterwards).

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-002-01 | Every ARC-050 skeleton file exists at its original path | High | Positive |
| TC-002-02 | `analytics/` holds exactly the 16 TRD 07 modules plus `__init__.py` and imports | High | Positive |
| TC-002-03 | `lint-imports` passes on the tree with the four contracts configured | High | Positive |
| TC-002-04 | `lint-imports` fails when `import sqlalchemy` is added to an `analytics/` module | High | Negative |
| TC-002-05 | `backend/requirements.txt` has exact pins, one `psycopg[binary]` line and no `psycopg2` | High | Positive |
| TC-002-06 | `backend/requirements-dev.txt` is the single dev-tool list of TRD 16 §6 | Medium | Positive |
| TC-002-07 | `ruff check .`, `ruff format --check .` and `mypy analytics backend` exit 0 | High | Positive |
| TC-002-08 | `pyproject.toml` ruff and mypy settings match TRD 18 §4.5 | Medium | Documentation |
| TC-002-09 | `.gitignore` holds every TRD 18 §4.11 entry and keeps generated references tracked | High | Positive |
| TC-002-10 | `.github/` templates, CODEOWNERS and Dependabot exist; blank issues disabled | High | Documentation |
| TC-002-11 | No audio file, no `.env` file other than examples and no `LICENSE` file is tracked | High | Negative |
| TC-002-12 | README states the exact GIT-056 sentence, quick start and links | High | Documentation |
| TC-002-13 | Backend layer modules exist, import and contain no business logic; analytics dependencies limited | Medium | Positive |
| TC-002-14 | `.editorconfig` and `.pre-commit-config.yaml` provide the TRD 18 hooks | Low | Documentation |

### TC-002-01 Every ARC-050 skeleton file exists at its original path

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `ls backend/api/{alarms,analytics,health,residents,sessions}.py`. | All 5 files listed, no "No such file" error. |
| 2 | Run `ls backend/models/{alarm,baseline,resident,score,session}.py`. | All 5 files listed. |
| 3 | Run `ls backend/services/{baseline,cusum,ingestion,morning_adjustment,scoring,speaker_screen,validation}.py`. | All 7 files listed. |
| 4 | Run `pytest -q tests/unit/test_repository_layout.py::test_skeleton_files_kept`. | `1 passed` (AC-AGT-06). |

### TC-002-02 `analytics/` holds exactly the 16 TRD 07 modules plus `__init__.py` and imports

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `ls analytics/*.py \| xargs -n1 basename`. | Exactly 17 names: `__init__.py`, `aggregates.py`, `alert_generator.py`, `baseline_builder.py`, `composite_score.py`, `config.py`, `cusum_engine.py`, `data_alerts.py`, `day_ledger.py`, `duplicate_detection.py`, `epoch_detection.py`, `morning_offset.py`, `pipeline.py`, `quality_screening.py`, `robust_stats.py`, `speaker_screen.py`, `zscore_calculator.py`. |
| 2 | Compare the list with the module column of TRD 07 §4.2. | The 16 module names are identical; no extra module. |
| 3 | Run `python -c "import analytics"; echo "exit=$?"`. | Prints `exit=0` with no traceback. |
| 4 | Run `pytest -q tests/unit/test_repository_layout.py::test_analytics_has_exactly_the_trd07_modules`. | `1 passed`. |

### TC-002-03 `lint-imports` passes on the tree with the four contracts configured

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `pyproject.toml` section `[tool.importlinter]`. | `root_packages = ["analytics", "backend"]`; a `forbidden` contract with `source_modules = ["analytics"]` and `forbidden_modules = ["backend", "sqlalchemy", "psycopg", "fastapi", "httpx", "requests", "os", "random"]`; a `layers` contract with `layers = ["backend.api", "backend.services", "backend.repositories", "backend.models"]`. |
| 2 | Run `lint-imports; echo "exit=$?"`. | Every contract is reported `KEPT`; summary shows 0 broken; `exit=0`. |

### TC-002-04 `lint-imports` fails when `import sqlalchemy` is added to an `analytics/` module

| Step | Action | Expected Result |
|---|---|---|
| 1 | In the scratch tree add the line `import sqlalchemy  # noqa` at the top of `analytics/robust_stats.py`. | File saved. |
| 2 | Run `lint-imports; echo "exit=$?"`. | The contract "analytics is pure: no backend, database, HTTP, environment or randomness" is reported `BROKEN`, naming `analytics.robust_stats -> sqlalchemy`; exit status is non-zero. |
| 3 | Revert the change (`git checkout -- analytics/robust_stats.py`) and run `lint-imports` again. | All contracts `KEPT`, exit 0. |

### TC-002-05 `backend/requirements.txt` has exact pins, one `psycopg[binary]` line and no `psycopg2`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -n "psycopg2" backend/requirements.txt; echo "exit=$?"`. | No line printed; `exit=1`. |
| 2 | Run `grep -v '^#' backend/requirements.txt \| grep -n "psycopg\[binary\]"`. | Exactly one line: `psycopg[binary]==3.2.4` (a `3.x` pin). |
| 3 | Run `grep -vE '^\s*(#\|$)' backend/requirements.txt \| grep -v '=='`. | No output: every non-comment line has an `==` pin. |
| 4 | Read the pins of `fastapi`, `sqlalchemy`, `alembic`, `pydantic`, `numpy`. | `fastapi==0.115.12` (0.115.x), `sqlalchemy==2.0.41` (2.0.x), `alembic==1.13.3` (1.13.x), `pydantic==2.10.6` (2.x), `numpy==2.1.3` (2.x). |
| 5 | Run `pytest -q tests/unit/test_repository_layout.py::test_requirements_pinned_without_psycopg2`. | `1 passed`. |

Note: the literal AC command `grep -n "psycopg\[binary\]" backend/requirements.txt` also matches the comment on line 2 (`# Driver: psycopg 3 as psycopg[binary] …`); only one match is a pinned line (backend/requirements.txt:2 and :10).

### TC-002-06 `backend/requirements-dev.txt` is the single dev-tool list of TRD 16 §6

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -vE '^\s*(#\|$)' backend/requirements-dev.txt`. | Lines include `ruff==`, `mypy==`, `pytest==9.`, `pytest-cov==`, `pytest-randomly==`, `time-machine==`, `httpx==`, `testcontainers==4.`, `openapi-core==0.19.`, `hypothesis==`, `openpyxl==3.1.`, `import-linter==2.`, `bandit==`, `pip-audit==`; every line has `==`. |
| 2 | Run `grep -n "pandas\|openpyxl" backend/requirements.txt; echo "exit=$?"`. | No output, `exit=1` (pandas and openpyxl are dev-only, ANL-005). |
| 3 | Run `ls requirements*.txt backend/requirements*.txt 2>/dev/null`. | Only `backend/requirements.txt` and `backend/requirements-dev.txt` exist (single list). |

### TC-002-07 `ruff check .`, `ruff format --check .` and `mypy analytics backend` exit 0

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `ruff check .; echo "exit=$?"`. | `All checks passed!`, `exit=0`. |
| 2 | Run `ruff format --check .; echo "exit=$?"`. | `N files already formatted` and no "Would reformat" line; `exit=0`. |
| 3 | Run `mypy analytics backend; echo "exit=$?"`. | `Success: no issues found in N source files`; `exit=0`. |

### TC-002-08 `pyproject.toml` ruff and mypy settings match TRD 18 §4.5

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `[tool.ruff]` in `pyproject.toml`. | `target-version = "py312"`, `line-length = 100`. |
| 2 | Open `[tool.ruff.lint]` and `[tool.ruff.lint.per-file-ignores]`. | `select` lists the TRD 18 §4.5 rule set; `"tests/**" = ["S101"]`. |
| 3 | Open `[tool.mypy]` and its overrides. | `plugins = ["pydantic.mypy"]`; override for `analytics.*` has `strict = true`; override for `backend.*` has `disallow_untyped_defs = true` and `warn_unused_ignores = true`. |

### TC-002-09 `.gitignore` holds every TRD 18 §4.11 entry and keeps generated references tracked

| Step | Action | Expected Result |
|---|---|---|
| 1 | Copy the block of TRD 18 §4.11 into a scratch file and, for each line, run `grep -qxF "<line>" .gitignore \|\| echo MISSING "<line>"`. | No `MISSING` line is printed (every entry from `__pycache__/` to `!.vscode/extensions.json` is present, including `*.wav`, `*.mp3`, `*.flac`, `*.m4a`, `*.ogg`, `*.opus`, `*.aac`, `*.webm`, `.env`, `.env.*`, `!.env.example`, `!.env.development.example`, `!.env.production.example`). |
| 2 | Run `git check-ignore database/schema.sql docs/api_reference/openapi.json; echo "exit=$?"`. | No path printed; `exit=1` (neither file ignored). |
| 3 | Run `git ls-files database/schema.sql docs/api_reference/openapi.json docs/reports \| head -3`. | `database/schema.sql`, `docs/api_reference/openapi.json` and at least one `docs/reports/` file are tracked. |

### TC-002-10 `.github/` templates, CODEOWNERS and Dependabot exist; blank issues disabled

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `ls .github/CODEOWNERS .github/pull_request_template.md .github/dependabot.yml .github/ISSUE_TEMPLATE/bug_report.yml .github/ISSUE_TEMPLATE/feature_request.yml`. | All 5 files listed. |
| 2 | Run `cat .github/ISSUE_TEMPLATE/config.yml`. | Contains `blank_issues_enabled: false`. |
| 3 | Read `.github/CODEOWNERS`. | `/analytics/`, `/tests/validation/`, `/database/seeds/` and `/backend/alembic/` are owned by `@EchoWellApp/team2-algorithm`; `/specs/TRD/07_*`, `08_*`, `09_*`, `14_*` by the algorithm team; `/.github/`, `/netlify.toml`, `/render.yaml`, `/docker-compose.yml` by `@EchoWellApp/team2-devops`. |
| 4 | Read the `##` headings of `.github/pull_request_template.md`. | `Summary`, `Prompt batch`, `Requirements implemented`, `Changes`, `Testing`, `Data and privacy checklist`, `Migration and rollback`, `Screenshots (frontend changes)`, `Open questions touched`. |
| 5 | Read the `id:` fields of both issue templates. | `bug_report.yml`: `what-happened`, `expected`, `steps`, `environment`, `request-reference`; `feature_request.yml`: `requirement-ids`, `user-need`, `acceptance` (GIT-072 fields). |

### TC-002-11 No audio file, no `.env` file other than examples and no `LICENSE` file is tracked

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `git ls-files \| grep -Ei '\.(wav\|mp3\|flac\|m4a\|ogg\|opus\|aac\|webm)$'; echo "exit=$?"`. | No path printed; `exit=1`. |
| 2 | Run `git ls-files \| grep -E '(^\|/)\.env' \| grep -v example; echo "exit=$?"`. | No path printed; `exit=1`. Only `.env.example`, `.env.development.example`, `.env.production.example` (and `frontend/.env.example`) are tracked. |
| 3 | Run `git ls-files \| grep -E '^LICENSE'; echo "exit=$?"`. | No path printed; `exit=1`. |
| 4 | Run `grep -n "filter=lfs" .gitattributes; echo "exit=$?"`. | No line printed; `exit=1` (no Git LFS pointer). |
| 5 | Run `pytest -q tests/unit/test_repository_layout.py -k "audio or licence"`. | `2 passed`. |

### TC-002-12 README states the exact GIT-056 sentence, quick start and links

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -nF "EchoWell is a research system, not a medical device; it detects a change and prompts a check-in, it does not diagnose." README.md`. | Exactly one match (line 5 at the time of writing). |
| 2 | Read README.md. | A section "Local quick start" is present with `cp .env.development.example .env`, `docker compose up --build -d` and `curl -fsS http://localhost:8000/api/v1/health`; links `[specs/TRD/](specs/TRD/)` and `[docs/](docs/)` exist and resolve to existing paths. |

### TC-002-13 Backend layer modules exist, import and contain no business logic; analytics dependencies limited

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `ls -d backend/core backend/services backend/repositories backend/schemas backend/models backend/jobs backend/cli.py`. | All 7 paths exist. |
| 2 | Run `python -c "import backend.core, backend.services, backend.repositories, backend.schemas, backend.models, backend.jobs, backend.cli"; echo "exit=$?"` with `APP_ENV=test` exported. | `exit=0`, no traceback. |
| 3 | Run `head -3 backend/repositories/__init__.py backend/jobs/__init__.py`. | Each module starts with a docstring naming its owning TRD. |
| 4 | Run `grep -rhoE "^\s*(import\|from) [a-z_]+" analytics/*.py \| awk '{print $2}' \| sort -u`. | Only standard-library modules of ANL-005, `numpy` and `analytics` itself appear; no `pandas`, `openpyxl`, `os`, `random`, `sqlalchemy`. |

Note: FEAT-002-FR-15 asks for empty modules in Phase 3; later features filled them, so step 3 checks only the docstring and step 2 the import.

### TC-002-14 `.editorconfig` and `.pre-commit-config.yaml` provide the TRD 18 hooks

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `ls .editorconfig .pre-commit-config.yaml`. | Both files exist. |
| 2 | Run `grep -n "id:" .pre-commit-config.yaml`. | Hook ids `ruff`, `ruff-format`, `prettier`, `no-audio-files`, `no-env-files` are present. |

## API Validation

Not applicable: FEAT-002 exposes no endpoint (router modules are empty skeletons in this feature).

## Database Validation

Not applicable: FEAT-002 creates only the empty `database/` and `database/roles/` directories; schema work starts in FEAT-008.

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Add `import sqlalchemy` to an `analytics/` module and run `lint-imports` (TC-002-04). | Non-zero exit, contract `BROKEN`. |
| 2 | Search `backend/requirements.txt` for `psycopg2` (TC-002-05). | No match. |
| 3 | Search tracked files for audio, `.env` and `LICENSE` (TC-002-11). | No match. |
| 4 | Introduce a ruff finding (for example an unused import `import json` in `backend/cli.py`) in the scratch tree and run `ruff check .`. | `F401 [*] json imported but unused`; non-zero exit. Revert afterwards. |
| 5 | Run `git check-ignore database/schema.sql` (TC-002-09). | Not ignored (exit 1). |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-002-AC-01 | Every ARC-050 file exists at its original path. | TC-002-01 |
| FEAT-002-AC-02 | `ls analytics/` lists exactly the 16 TRD 07 modules plus `__init__.py`; `python -c "import analytics"` exits 0. | TC-002-02 |
| FEAT-002-AC-03 | `lint-imports` exits 0 on the tree and non-zero with `import sqlalchemy` in `analytics/`. | TC-002-03, TC-002-04 |
| FEAT-002-AC-04 | No `psycopg2`; exactly one pinned `psycopg[binary]` line; every line `==` pinned. | TC-002-05 |
| FEAT-002-AC-05 | `ruff check .`, `ruff format --check .`, `mypy analytics backend` exit 0. | TC-002-07 |
| FEAT-002-AC-06 | `.gitignore` contains every TRD 18 §4.11 entry; `git check-ignore` reports neither generated reference as ignored. | TC-002-09 |
| FEAT-002-AC-07 | CODEOWNERS, PR template, `dependabot.yml` and both issue templates exist. | TC-002-10 |
| FEAT-002-AC-08 | `git ls-files` shows no audio, no `.env` other than examples, no `LICENSE`. | TC-002-11 |
| FEAT-002-AC-09 | README contains the exact GIT-056 sentence. | TC-002-12 |

## Test Data Requirements

- Repository files only; no database, no resident records, no environment file.
- `APP_ENV=test` exported for TC-002-13 step 2 so no settings guard fires on import.
- No audio file is created; the audio check is a search for absence.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-002-FR-01 (ARC-016, GIT-001, GIT-002) | FEAT-002 | TC-002-13 |
| FEAT-002-FR-02 (ARC-050, GIT-003, AGT-010, D-24) | FEAT-002 | TC-002-01 |
| FEAT-002-FR-03 (ANL-001, ANL-004, D-61) | FEAT-002 | TC-002-02 |
| FEAT-002-FR-04 (ANL-002, ARC-041, ARC-051, AC-ARC-01) | FEAT-002 | TC-002-03, TC-002-04 |
| FEAT-002-FR-05 (ANL-005) | FEAT-002 | TC-002-06, TC-002-13 |
| FEAT-002-FR-06 (AGT-024, NFR-089, D-53, AC-AGT-11) | FEAT-002 | TC-002-05 |
| FEAT-002-FR-07 (TRD 16 §6) | FEAT-002 | TC-002-06 |
| FEAT-002-FR-08 (GIT-040, GIT-041, NFR-080, NFR-081) | FEAT-002 | TC-002-07, TC-002-08 |
| FEAT-002-FR-09 (GIT-100, AGT-016) | FEAT-002 | TC-002-09 |
| FEAT-002-FR-10 (GIT-032, GIT-033, GIT-037) | FEAT-002 | TC-002-10 |
| FEAT-002-FR-11 (GIT-072) | FEAT-002 | TC-002-10 |
| FEAT-002-FR-12 (GIT-044, GIT-045) | FEAT-002 | TC-002-14 |
| FEAT-002-FR-13 (GIT-056, AGT-018) | FEAT-002 | TC-002-12 |
| FEAT-002-FR-14 (GIT-080, GIT-091..GIT-097, AGT-016) | FEAT-002 | TC-002-11 |
| FEAT-002-FR-15 (TRD 25 §4.6 Phase 3) | FEAT-002 | TC-002-13 |
| AC-AGT-06 | FEAT-002 | TC-002-01 |
| AC-GIT-02, AC-GIT-05, AC-GIT-06 | FEAT-002 | TC-002-11, TC-002-07, TC-002-10 |
| TST-021 (import-boundary test) | FEAT-002 | TC-002-04 |
| TST-007 (no audio files) | FEAT-002 | TC-002-11 |
