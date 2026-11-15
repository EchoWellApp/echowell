# EchoWell manual QA test cases (Block 5)

One file per feature file in `specs/backlog/features/` (FEAT-001..FEAT-097), written by `specs/prompts/Test_Case_Generation_Prompt.md` (TRD 24 D-106; `IMPLEMENTATION_ROADMAP.md` §7). The test cases restate the TRDs and the feature acceptance criteria; they add no requirement. Where a test case and a TRD disagree, the TRD wins.

## File names and IDs

- File: `TC-NNN-<Feature-Name>.md`, where `NNN` is the feature number and `<Feature-Name>` is the feature file's name after `FEAT-NNN-` (for example `TC-065-Residents-Overview-Page-With-Devices-Panel.md` for `FEAT-065-Residents-Overview-Page-With-Devices-Panel.md`).
- Test case IDs: `TC-NNN-MM` (two-digit sequence inside the file, e.g. `TC-065-01`), unique across the suite.

## Test environment

| Environment | Use | How to start |
|---|---|---|
| Local Docker Compose (demo profile) | Default for every test case unless the case says otherwise | `docs/deployment.md` (Compose demo profile), seeded with `test_v0_1` |
| Local development stack | Analytics, CLI and database cases | `README.md` quick start; `python -m backend.cli seed test_v0_1` |
| Hosted staging / production (Netlify, Render, Neon) | Only the cases marked **Hosted** (TRD 24 D-180) | URLs held by the team; synthetic data only |

- Test data are synthetic only: the `test_v0_1` profile (residents R01–R10, plus fixtures such as R11 and N01 where a case names them), the DS-07 reference values of TRD 11 §4.13, and the answer key of the validation suite. Study IDs only; never a name, room or real recording. No audio is ever uploaded, stored or played.
- Seeded users: `admin@example.com`, `clinician@example.com`, `researcher@example.com` with the `SEED_*` passwords from the environment file (never write a password into a test case).
- API: base path `/api/v1`; Swagger UI at `/api/v1/docs`; ingest calls use the `X-API-Key` header, user calls a Bearer token from `POST /api/v1/auth/login`.
- Database checks: `psql` against the local database (read-only `SELECT` statements unless the case says otherwise).

## File structure

Every file follows the prompt's structure: Feature Description, Preconditions, Manual Test Cases (summary table with ID, scenario, priority, type), Test Steps for each case, API Validation, Database Validation, Negative Test Cases, Acceptance Criteria Validation, Test Data Requirements, Traceability. A section that does not apply to the feature says "Not applicable" and why. Types are Positive, Negative, UI, API, Database, Analytics, Security, Accessibility, Performance, Documentation, Hosted. Priorities: High (P0 or an acceptance criterion), Medium, Low.

## Coverage

Every `FEAT-NNN-AC-xx` acceptance criterion appears in its file's Acceptance Criteria Validation table with at least one test case ID. `scripts`-free check: `grep -o 'FEAT-[0-9]*-AC-[0-9]*' specs/backlog/features/*.md | sort -u` against the same grep over this folder.
