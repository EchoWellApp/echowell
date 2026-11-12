# Final Implementation Audit

Document: docs/reports/FINAL_IMPLEMENTATION_AUDIT.md · Date: 8 November 2026 · Audited commit: `23e558b` (`main` after the checkpoint 8 merge, GitHub PR #31) · Block 3 checkpoint 9, `Implement_Feature_Batches.md` Phase 15, TRD 25 Phase 11, FEAT-091 · Updated 12 Nov 2026 with the review round 1 decisions (TRD 24 D-171..D-180) · Location per TRD 25 AGT-032 / TRD 24 D-21

This is the Phase 15 audit of the finished build against `specs/TRD/`, `specs/backlog/`, `docs/design/`, the source code, the test results and the deployment configuration. It records findings only: no code, configuration or TRD was changed (TRD 25 §4.6 Phase 11 Pitfalls). The live deployment (Block 4) has not happened yet, so every deployment-dependent check is recorded as **pending Block 4**, never as a failure (IMPLEMENTATION_ROADMAP §3.3, TRD 24 D-100), and the verdict is provisional on those items.

Companion reports (same commit):

| Report | Content |
|---|---|
| `docs/reports/TRD_Implementation_Audit.md` | Status and evidence for all 2,050 TRD requirement IDs (§2–§5) and all 247 TRD acceptance criteria (§6) |
| `docs/reports/traceability_inspections.md` | Inspection register for untested requirements and acceptance criteria (TST-013) |
| `docs/reports/DOCUMENTATION_COMPLETENESS_AUDIT.md` | Ten documentation checks, findings DCA-01..DCA-14 |
| `docs/reports/UI_REQUIREMENTS_TRACEABILITY_MATRIX.md` | 63 wireframe elements → feature → component → endpoint → test |
| `specs/backlog/MVP_READINESS_CHECKLIST.md` | Status column of sections A–M audited on this commit |
| `docs/reports/ALGORITHM_VALIDATION_REPORT.md` | R01–R10 and global checks, regenerated on `23e558b`: Overall PASS |

## 1. Verification of the ten Phase 15 items

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Every TRD requirement is implemented | **PASS WITH FINDINGS** | 1,806 of 2,050 PASS, 81 FAIL (0 S1, 4 S2, 40 S3, 37 S4), 88 pending Block 4, 75 not applicable (`TRD_Implementation_Audit.md` §2). The four S2 failures are GitHub repository settings, not application behaviour (§3.1). |
| 2 | Every feature specification is implemented | **PASS** | FEAT-001..FEAT-087 Complete and merged (GitHub PRs #3, #4, #17, #18, #20, #22, #28, #31); every FR-* of TRD 02 is PASS or retired (203 PASS, 9 retired by D-110). FEAT-088..FEAT-090 are Block 4, FEAT-091 is this audit, FEAT-092..FEAT-097 are After MVP / research. |
| 3 | Every API endpoint is functional | **PASS** | 32 endpoints in TRD 19 = `docs/api_reference/openapi.json` = routes in `backend/api/` (TST-062 `tests/contract/test_openapi_contract.py::test_path_set`); authorisation matrix over every endpoint × 5 credential types (TST-130 `tests/security/test_auth_matrix.py`); `openapi-contract` CI job success. |
| 4 | Every database entity is implemented | **PASS** | 24 tables of TRD 20 present in migrations 0001–0004 (`alembic check`: no differences); grants and immutability tested (TST-041, SEC-114). Minor findings DB-040, DB-042, DB-046 (§5). |
| 5 | Every analytics module is implemented | **PASS** | TRDs 07–09 and 10: 209 PASS, 0 FAIL, 7 not applicable (calibration and "May" items deferred to OQs). Coverage gate `analytics/` ≥ 95 % met in CI. |
| 6 | All R01–R10 tests pass | **PASS** | `ALGORITHM_VALIDATION_REPORT.md` regenerated on `23e558b`: "Overall: PASS", Tier A and Tier B, VC-R01..VC-R10, VC-G01..VC-G12; `pytest tests/validation` part of the 757-passed run. |
| 7 | Frontend connects successfully to backend | **PASS** (local and CI) | `e2e.yml` `playwright` on `23e558b` success: read-only, mutating and isolated suites against the Compose `demo` stack (real backend, real database); axe scan with zero serious/critical violations (TST-110). On the hosted origins: pending Block 4. |
| 8 | Deployment is operational | **COMPLETE per the algorithm lead (D-180)** | Configuration complete and validated (`CONFIGURATION_VALIDATION_REPORT.md` 96/96 PASS). `deploy-staging.yml` on `23e558b` stopped at "Wait for staging" because the GitHub variables `STAGING_API_BASE_URL` and `STAGING_FRONTEND_URL` are not set yet (DEPLOYMENT_CHECKLIST, Block 4). Review round 1: the interim deployment is complete and functioning (D-180); hosted smoke tests run in Block 5. |
| 9 | CI/CD pipeline functions | **PASS WITH FINDINGS** | All 7 `ci.yml` jobs and `e2e.yml` `playwright` succeed on `23e558b`; but the `main` ruleset makes none of them a required check (CIC-070, S2), and the scheduled `e2e.yml` jobs (`nightly-validation`, `performance`) have not yet run on GitHub. |
| 10 | MVP readiness checklist passes | **ACCEPTED (D-171..D-180)** | MVP-01..MVP-15: 11 PASS, 1 FAIL (MVP-02, a missing test), 3 pending Block 4 (MVP-07 HTTPS part, MVP-08 hosting, MVP-15 hosted data). Sections A–L: 94 passed, 11 failed, 30 pending Block 4. Review round 1: MVP-02's test is in GitHub PR #38 (Block 5, D-174); the hosted items are Block 5 validation (D-180). |

## 2. Requirements Traceability Matrix

Per TRD (full matrix with evidence for every ID: `TRD_Implementation_Audit.md` §5):

| TRD | Requirements | PASS | FAIL (S2/S3/S4) | Pending Block 4 | N/A |
|---|---|---|---|---|---|
| 00 Project Vision and Scope | 30 | 22 | 3 (0/0/3) | 3 | 2 |
| 01 System Architecture TRD | 76 | 72 | 0 | 4 | 0 |
| 02 Functional Requirements Specification | 212 | 203 | 0 | 0 | 9 |
| 03 Non Functional Requirements | 102 | 80 | 11 (0/7/4) | 9 | 2 |
| 04 Frontend TRD | 148 | 138 | 5 (0/2/3) | 1 | 4 |
| 05 Backend API TRD | 122 | 120 | 2 (0/0/2) | 0 | 0 |
| 06 Database Design TRD | 63 | 56 | 4 (0/2/2) | 3 | 0 |
| 07 Analytics Engine TRD | 65 | 63 | 0 | 0 | 2 |
| 08 Baseline and Scoring Algorithm Spec | 43 | 43 | 0 | 0 | 0 |
| 09 CUSUM and Alerting Spec | 49 | 44 | 0 | 0 | 5 |
| 10 Data Ingestion and Validation Spec | 59 | 59 | 0 | 0 | 0 |
| 11 User Interface UX Spec | 275 | 243 | 1 (0/1/0) | 0 | 31 |
| 12 Security and Authentication Spec | 121 | 99 | 8 (0/5/3) | 12 | 2 |
| 13 Testing Strategy and Acceptance Criteria | 121 | 102 | 12 (1/8/3) | 7 | 0 |
| 14 Test Data and Validation Spec | 72 | 66 | 1 (0/1/0) | 1 | 4 |
| 15 Deployment and DevOps Spec | 83 | 46 | 0 | 29 | 8 |
| 16 CI CD Pipeline Spec | 59 | 51 | 4 (1/1/2) | 4 | 0 |
| 17 Logging Monitoring and Error Handling | 62 | 54 | 5 (0/1/4) | 2 | 1 |
| 18 GitHub Repository Standards | 63 | 36 | 20 (2/9/9) | 6 | 1 |
| 19 API Contracts OpenAPI Spec | 27 | 27 | 0 | 0 | 0 |
| 20 PostgreSQL Schema Definition | 44 | 44 | 0 | 0 | 0 |
| 21 Environment Configuration Spec | 29 | 27 | 1 (0/1/0) | 1 | 0 |
| 22 Third Party Services and Hosting | 30 | 20 | 0 | 6 | 4 |
| 23 Data Model and Entity Definitions | 25 | 24 | 1 (0/0/1) | 0 | 0 |
| 24 Risk Assumptions and Open Questions | 18 | 18 | 0 | 0 | 0 |
| 25 AI Agent Build Instructions | 52 | 49 | 3 (0/2/1) | 0 | 0 |

Business requirements: BR-01..BR-18 each map to TRD requirements and features (DOCUMENTATION_COMPLETENESS_AUDIT.md check 1); success criteria SC-01..SC-08 and the vision acceptance criteria are audited in `MVP_READINESS_CHECKLIST.md` §B and §K. Acceptance criteria: 247 TRD ACs, 203 PASS, 14 FAIL, 28 pending Block 4, 2 N/A (`TRD_Implementation_Audit.md` §6). Wireframe elements: 63, of which 61 fully traced (UI matrix).

### 2.1 Test results on the audited commit

| Command | Result |
|---|---|
| `pytest -q -p randomly` (unit, integration, contract, security, validation, smoke) | 757 passed, 19 skipped (smoke tests without `SMOKE_API_BASE_URL`), 16 deselected (performance), 0 failed, 300 s |
| `alembic upgrade head`; `alembic check` | migrations 0001→0004 applied; no new upgrade operations detected |
| `cd frontend && npx vitest run` | 429 passed (71 files) |
| `npm run lint`; `npx tsc --noEmit` | no warnings or errors; exit 0 |
| CI `ci.yml` run 42502819983 on `23e558b` | repo-hygiene, backend-lint, backend-test (coverage gates and PR-scope budgets), openapi-contract, frontend, security-audit, docker-build: all success |
| CI `e2e.yml` run 42502819942 on `23e558b` | `playwright` success (`test:e2e:readonly`, `test:e2e:mutating`, `test:e2e:isolated`, a11y); `lighthouse` passed on PR #31 head `57adc71` |
| `python tests/trace_report.py` | 13 Must requirements without a test or inspection entry: exactly the Musts that failed inspection |

### 2.2 Repository text checks (AGT-004, AGT-007, AGT-018, AGT-019; AC-AGT-02, AC-AGT-03)

Run with `git grep` on tracked files of `23e558b`:

```text
$ git grep -niE "openai|anthropic|langchain|llama|gpt" -- frontend backend analytics
backend/core/common_passwords.txt:8524:llamas
(exit 0)

$ git grep -n "pipeline_test_v0_1.xlsx" -- analytics backend
(exit 1)

$ git grep -n "evaluation_ground_truth" -- analytics
(exit 1)

$ git grep -niE "diagnos(e|is)|severity" -- frontend/app frontend/components
frontend/components/SummaryPanel/SummaryPanel.test.tsx:45:    const note = screen.getByText(/It is a prompt to check in, not a diagnosis\./);
frontend/components/SummaryPanel/SummaryPanel.test.tsx:129:        `Once the baseline is complete, R08 will be compared only with R08. A change is a prompt to check in, not a diagnosis. ${NOTE_TAIL}`,
(exit 0)

$ git grep -ni "edge""4care" -- frontend backend analytics
(exit 1)
```

Classification: the only LLM-pattern hit is the word "llamas" in `backend/core/common_passwords.txt` (a common-password deny list, SEC-012), not a dependency; AGT-004 PASS. No answer-key file name in `analytics`/`backend` and no `evaluation_ground_truth` in `analytics`; AGT-007, AC-AGT-02 PASS. Both "diagnosis" hits are the approved negative wording "a prompt to check in, not a diagnosis" asserted by a component test; AGT-018 PASS. The old facility name of AGT-019 does not occur; AGT-019, AC-AGT-03 PASS.

### 2.3 Authentication and security checks (roadmap §5.9)

| Check | IDs | Result |
|---|---|---|
| Authorisation matrix: every endpoint × anon, key, admin, clinician, researcher | TST-130, AC-SEC-01, AC-SEC-02 | PASS (`tests/security/test_auth_matrix.py`) |
| Login and ingest rate limits | TST-131 | PASS (`tests/integration/api/test_rate_limits.py`) |
| Token and key attacks (expired, altered, `alg: none`, revoked key, missing scope) | TST-132, AC-SEC-04 | PASS (`tests/integration/api/test_auth.py`) |
| No audio route or field; `audio/*` refused | TST-133, AGT-006 | PASS (`tests/security/test_no_audio.py`) |
| CORS allow-list | TST-134 | PASS (`tests/integration/api/test_http_middleware.py`) |
| Dependency and secret scans | TST-136 | PASS with finding: pip-audit, npm audit and gitleaks run on every PR; advisories needing a major upgrade are excepted until 20 Dec 2026 (D-159, SEC-156 S3); `scripts/ci/audit_gate.py` passes if a scanner prints nothing (fail-open, S3, §5) |
| No PII in responses and logs | TST-137, AGT-017 | PASS (`tests/security/test_data_minimisation.py`) |
| Audit trail (login, logout, ingest, note, review, snooze, export, pipeline run) | TST-053, AC-SEC-09 | PASS |
| Password policy and argon2id hash format | TST-032, AC-SEC-05 | PASS |
| Seeded test users log in with their roles | TST-188 | FAIL S3: no `tests/integration/test_seed_logins.py`; covered indirectly by the E2E global setup |
| Credential CLI refusals; key revocation | TST-195, AC-SEC-06 | FAIL S3: refusals implemented, five refusal cases untested |
| Database role grants and immutability | SEC-114, TST-041, AC-SEC-03 | PASS |
| Startup guards (production refuses `test_v0_1`, `PIPELINE_AS_OF`, short `JWT_SECRET`, missing `sslmode=require`, login limit ≠ 5/minute) | AC-AGT-05, AC-SEC-08, AC-ENV-01..04, ENV-054 | PASS; findings SEC-032 (no 60-minute cap on token lifetime outside the Blueprint) and SEC-033 (repository test secrets not refused), both S3 |
| Secrets masked in settings `repr` | AC-ENV-09, ENV-004 | PASS |
| Login, bad login, role restriction in the browser | E2E-01, E2E-02, E2E-14, E2E-21 | PASS (CI `playwright`) |
| API text rendered as text; no `dangerouslySetInnerHTML` | SEC-074, SEC-076 | PASS (`react/no-danger` lint rule; NotesList test) |
| HTTPS, HSTS, TLS 1.2 and CSP on hosted origins | DEP-080, DEP-081, SEC-066, AC-SEC-07 | Pending Block 4 (smoke tests exist: `tests/smoke/test_tls.py`) |

No authentication bypass was found (no S1).

## 3. Pass/Fail Status

### 3.1 Serious findings (S2)

All four S2 failures have the same two causes, both GitHub settings that only a repository admin can change:

| Finding | IDs | Detail |
|---|---|---|
| **No required status checks on `main`** | CIC-070, TST-150 (and AC-CIC-01, AC-CIC-08, AC-TST-09, MVP checklist J.07) | The active ruleset "Require Pull Requests" (id 25310033) requires a pull request, one approval and resolved conversations, and blocks force-push and deletion, but its `required_status_checks` list is empty. The eight checks of CIC-070 (`repo-hygiene`, `backend-lint`, `backend-test`, `openapi-contract`, `frontend`, `security-audit`, `docker-build`, `playwright`) therefore do not block a merge. TRD 24 D-162 records branch protection as "already configured"; the live setting does not match it. |
| **Ruleset and CODEOWNERS weaker than GIT-010/GIT-037** | GIT-010, GIT-037 (and AC-GIT-01) | Stale approvals are not dismissed, code-owner review is not required, and GitHub reports "Unknown owner" for all three teams in `.github/CODEOWNERS` (`team2-maintainers`, `team2-algorithm`, `team2-devops`; 15 errors), so CODEOWNERS has no effect. Seven commits reached `main` by direct push (29 Oct–3 Nov 2026, deployment hotfixes and README), so an admin bypass is in use. In practice the algorithm lead approved every checkpoint PR. |

Review round 1 (12 Nov 2026): the algorithm lead accepted these findings as recorded and not blocking MVP readiness or the demo (TRD 24 D-171, D-172, D-173). Listing the checks in the ruleset and updating CODEOWNERS to the existing Developer team are follow-up cleanups.

### 3.2 Moderate and minor findings

S3 (40) and S4 (37) are listed with evidence in `TRD_Implementation_Audit.md` §3. Grouped:

| Theme | IDs | Severity |
|---|---|---|
| Missing tests for behaviour that is implemented | TST-049 (SRC-05 one-by-one vs batch, also MVP-02, AC-ANL-06), TST-185 (new-admission cohort move), TST-188, TST-194, TST-195, TST-095, TDV-016, TST-020 (≈ 49 of 83 Table 4.3-A unit cases not identifiable by ID), NFR-086, NFR-125, NFR-141, DB-040, DB-042 | S3 |
| Accessibility contrast | UX-224, FE-211: light-scheme `--c-aside` 2.23:1 and `--c-quar` 2.94:1 against `--surface` (limit 3:1) as unoutlined bar segments; the colours are the TRD 11 §4.15 palette, so spec and build agree but both miss the limit | S3 |
| Frontend robustness | FE-078: API responses are not checked at runtime, so a missing field does not become an error state | S3 |
| Security hardening | SEC-032, SEC-033, SEC-058, SEC-155 (`@netlify/plugin-nextjs` caret range), SEC-156 (advisories excepted to 20 Dec, D-159), fail-open `audit_gate.py` | S3 |
| CI and traceability gaps | TST-013/NFR-111 (trace report not run in CI), NFR-067 (forbidden-wording step scans only the `wording.ts` barrel, not `frontend/lib/wording/*.ts`; no forbidden term present today), NFR-036 (no hashed Python lock file), NFR-066 (no readability check), CIC-031 | S3 |
| Process history | GIT-012, GIT-030, GIT-031, AGT-013, AGT-030 (checkpoint 4 started before checkpoint 3 merged; 7 direct pushes), GIT-014, GIT-020, GIT-032, GIT-033, GIT-070 (project labels absent), GIT-071 (no OQ issues) | S3 |
| Logging detail | LOG-053 (no `ingest_batch_completed` event), LOG-063, LOG-080 (error pages without request reference), LOG-081 (429/503 messages), LOG-115, ENV-022 (no startup `config_mismatch` warning) | S3–S4 |
| Spec drift and cosmetic | VIS-012, VIS-014, VIS-020 (`/login` lacks the "Test data only" prefix), FE-002, FE-005, FE-091, API-003, API-005, DB-031, DB-046, DME-013, TST-001 and CIC-037 (Dependabot moved pytest 9, pytest-cov 7, pytest-randomly 5 past the TRD pins), TST-012, TST-160, CIC-072, NFR-010, NFR-013, NFR-085, NFR-093, SEC-055..SEC-057 (rotation procedures not in operator docs), GIT-003, GIT-011, GIT-021, GIT-024, GIT-043, GIT-094, GIT-095, GIT-097, GIT-111, AGT-012 | S4 |

## 4. Missing Functionality

No MVP feature is missing. Behaviour that the TRDs specify and the build does not provide:

1. Required status checks and working CODEOWNERS on `main` (§3.1).
2. A startup `config_mismatch` warning (ENV-022), an `ingest_batch_completed` log event (LOG-053), resolved counts in `data_alerts_updated` (LOG-115), the request reference on error pages (LOG-080) and the LOG-081 429/503 messages.
3. Runtime validation of API responses in the frontend (FE-078).
4. A staging/production cap of 60 minutes on `JWT_EXPIRES_MINUTES` (SEC-032) and refusal of all repository-known secrets (SEC-033); a `config.changed` audit row for secret rotation (SEC-058).
5. The "Test data only (…). No real residents." prefix on `/login` (VIS-020).
6. CI execution of `tests/trace_report.py` (TST-013) and a forbidden-wording scan of all copy files (NFR-067).
7. Deployment-dependent behaviour, pending Block 4 (88 requirements, 28 acceptance criteria): hosted staging and production, smoke tests, HTTPS/HSTS/TLS, backups and restore drill, rollback rehearsal, uptime monitoring, demo acceptance TST-180..TST-184, three green nightly runs, tags and releases.

## 5. Technical Debt

| Item | Where | Effect |
|---|---|---|
| Fail-open audit gate | `scripts/ci/audit_gate.py:46`, `:58` (`json.loads(done.stdout or "{}")`) | If pip-audit or npm audit crashes with no output, `security-audit` passes without auditing. The current CI log shows real output (7 pip and 14 npm advisories, all excepted). |
| Security exceptions with an end date | `SECURITY_EXCEPTIONS.md` (D-159) | The gate fails again after 20 Dec 2026; Next.js and FastAPI/Starlette major upgrades must land before real data or a public demo (D-160). |
| Unpinned test-tool majors | `backend/requirements-dev.txt` (pytest 9, pytest-cov 7, pytest-randomly 5) | Merged by Dependabot past the TRD pins without a D entry. Open Dependabot PR #27 (24 updates) is the first that the R01–R10 suite will gate. |
| Missing tests | §3.2 first row | Implemented paths (alert superseded by rebuild FR-110, data alert resolution FR-296, cohort move, device sharers in a resident-scoped run ARC-065) are exercised only indirectly. |
| Stub service modules | `backend/services/{baseline,cusum,scoring,speaker_screen,morning_adjustment}.py` | Docstring-only skeleton files kept under their names (API-008); logic lives in `analytics/`. |
| Services building queries | `pipeline_persistence.py`, `engine_read.py`, `pipeline_runner.py` | Bypass the repository layer (API-005) and the JSON-column validators (DME-013). |
| Index created without `CONCURRENTLY` | migration 0003 | Fine on today's data; locks the table on a large database (DB-046). |
| Empty top-level docs | `docs/architecture.md`, `docs/algorithm.md`, `docs/database_design.md` | Content lives in `docs/design/`; the empty files are skeleton leftovers (GIT-003). |
| Scheduled jobs never run on GitHub | `e2e.yml` `nightly-validation`, `performance` | Random-order and nightly budget runs evidenced only locally (CHECKPOINT_8 §5). |
| README | `README.md` "Run Backend" | Windows commands inside an `sh` block, typo; human-authored (commit 66c7705). |

## 6. Risks

TRD 24 RSK-01..RSK-17 remain as recorded, with their mitigations implemented where they are software (for example RSK-09 wording rules: AGT-018 PASS; RSK-10 facility name: AGT-019 PASS; RSK-05 day ledger and `missing_device_gap`: PASS). Risks raised or sharpened by this audit:

| Risk | Likelihood / impact | Mitigation |
|---|---|---|
| A PR with failing checks is merged because no check is required (§3.1) | M / H | Admin adds the eight CIC-070 checks as required in ruleset 25310033, or the algorithm lead keeps confirming green CI before each merge. |
| Timeline (RSK-12): Block 4 not started on 8 Nov; DEP-090 anchor of 5 Nov for production smoke tests has passed | H / H | Block 4 next; the local Docker Compose demo (DEP-090 fallback) works today (`e2e.yml` runs against it). |
| Security debt (RSK-16) expires 20 Dec 2026 | H / M | Separate upgrade PR before real data or public demo (D-160). |
| A scanner failure hides advisories (fail-open gate) | L / M | Treat empty scanner output as an error. |
| Dependency drift through Dependabot majors | M / M | Review major bumps against TRD pins; record a D entry when accepted. |
| Light-scheme chart segments below 3:1 | M / L | Outline the segments or adjust the two tokens (UX-083 already outlines `--c-aside` change-score bars). |

## 7. Batch reports (AGT-022)

Checkpoint reports 1–8 (`docs/reports/CHECKPOINT_1_DESIGN_DOCS.md` … `CHECKPOINT_8_DEPLOYMENT_CONFIG.md`) each list the requirement IDs implemented, tests added, commands run with results, new OQ/D IDs and deviations, and record each review round's resolutions (AGT-022 PASS). This checkpoint adds no OQ and no D ID; it records findings for the algorithm lead's decision.

## 8. Open questions and interim decisions

The 26 OQs with status Open in TRD 24 (FEAT-091-FR-05, FEAT-091-AC-06); the MVP runs on each interim decision. The six answered OQs (OQ-21, OQ-22, OQ-23; OQ-30 → D-105, OQ-31 → D-115, OQ-32 → D-116) are not repeated.

| OQ | Question | Owner | Status | Interim decision used by the MVP |
|---|---|---|---|---|
| OQ-01 | Data retention architecture: what feature data is stored, where, and for how long? | Grant team (PI Dr. Zvika Shinar); retention rules for research data confirmed with faculty/IRB | Open | Keep all records indefinitely in the MVP database; no deletion or archival jobs; no PII and no audio stored; `raw_sessions` and `audit_logs` are append-only. Interim weekly dumps of the interim stack (synthetic and test data only, D-28) are stored encrypted on the UND-managed storage designated by the PI for the study's research data (TRD 15 DEP-096), never on GitHub or personal devices. |
| OQ-02 | Does the unit count mean units deployed or units built? | Grant team | Open | No software dependency: the `devices` table holds any number of devices; capacity sized by ASM-08. |
| OQ-03 | What are the final feature column names from Team 1's extractor, and which extractor and version will the v1 rig run? | Team 1 (extraction: Lexi Hartman, JT/Yitzi Devor per SRC-15 step 2) | Open | Use the SRC-05 placeholder names; map incoming column names through a configurable feature-name mapping so renaming needs no code change; store `extraction_software_version` on every record (e.g. "openSMILE 3.0.2", eGeMAPS v02 requested). |
| OQ-04 | Is the spoken phrase identical for every resident and fixed for the whole study (keep or drop `phrase_id`)? | Team 1 | Open | Accept and store `phrase_id` ("P01" in test data) as a required text field; do not use it in any computation or epoch key. |
| OQ-05 | Does staff review ("Mark as reviewed") reset the CUSUM tally or turn the alarm off? | PI Dr. Zvika Shinar, with Shaba Rahavi (Team 2 software) | Open | Saving a review (`POST /api/v1/alerts/{id}/reviews`) creates an `alert_reviews` row and sets `alerts.status=acknowledged` (badge "Reviewed"); it does not reset the tally and does not close or turn off the alarm (D-03, D-35). UI keeps the note "does review reset the tally? — open question OQ-05". |
| OQ-06 | Alert delivery: who is told, how, and how fast? | PI Dr. Zvika Shinar, informed by Ann Hartman and Lovette Ochieng (Edgewood staff interviews) | Open | In-dashboard only: alarm badge, alerts list and resident detail. No SMS, email or push (D-05). |
| OQ-07 | When will the AWS budget be approved, and who owns the AWS account (UND IT)? | Shaba Rahavi and PI Dr. Zvika Shinar, with UND IT (account ownership) (SRC-15 item 5) | Open | Run on the interim stack Netlify + Render + Neon PostgreSQL (or Render Postgres) with synthetic and test data only (backend host Render since D-153); no go-live until AWS is approved (D-28); keep the code portable to AWS Amplify / App Runner / RDS PostgreSQL + KMS + Secrets Manager + CloudWatch with no significant code change. Devices send records by HTTPS POST to `/api/v1/sessions` or `/api/v1/ingest` with `X-API-Key`. |
| OQ-08 | Facility norm definition for the new-admission arm: which statistic or percentiles, which residents, minimum N, and how many days for the new resident's own baseline? | Shaba Rahavi and PI Dr. Zvika Shinar (SRC-11 note) | Open | Arm is experimental (D-06): `/admissions` carries the banner "Future / experimental study arm"; ranges are stored in `facility_reference_ranges` with the method name recorded per row; the arm raises no alerts and never feeds the longitudinal pipeline; a resident moves to the main list when their own baseline forms. |
| OQ-09 | Which method estimates the morning offsets on a larger dataset? | Megan Stubbs (Team 2 data processing), on Team 1's 50-resident, 120-day dataset | Open | Use the configured offsets table (loudness −1.50, phrase duration +0.10, speech rate −0.12, articulation rate −0.10, pause fraction +0.010, voiced fraction −0.020, others 0) in both profiles (D-02). |
| OQ-10 | How should a late-arriving record that predates a frozen baseline be handled? | Shaba Rahavi with Megan Stubbs | Open | Keep the frozen baseline unchanged (ASM-07); process the record otherwise as normal; add a `late_arrival` warning to `pipeline_runs.warnings` (D-10). |
| OQ-11 | How is data handled when a participant withdraws? | Faculty / IRB | Open | `residents.status=withdrawn` stops ingestion (422 "resident withdrawn") and hides the resident from default lists; no data is deleted. |
| OQ-12 | What is the final clinical wording of "What this means" on the Resident detail page? | PI Dr. Zvika Shinar | Open | Text comes from `frontend/lib/wording.ts`, reviewed by the PI; while `CLINICAL_WORDING_APPROVED=false` the page shows "[Final clinical wording: confirm with PI]". Draft wording uses "detects a change" and "prompt to check in, not a diagnosis" (D-18). |
| OQ-13 | How are the alarm limit h and reference value k calibrated on Team 1's 50-resident, 120-day dataset, and what minimum length of stay should the participant criteria require now that the baseline is 30 usable sessions (the criteria assume a 90-day baseline)? | Megan Stubbs (analysis specification) with PI Dr. Zvika Shinar | Open | k = 0.5 and h = 5.0 (within-person robust z units) in both profiles; production baseline_n = 30 (decided, D-01). Participant criteria are outside the software. |
| OQ-14 | When will speaker verification be scheduled, and will it output a binary decision or a confidence score? | Team 1 | Open | Not in schema 0.1. The statistical speaker screen (F0 + composite features) quarantines likely other speakers (D-13). A future field arrives with a new `schema_version`; adopting it also requires a TRD 10 ING-017 change (mapping targets are limited to the canonical v0.1 fields), a new typed `raw_sessions` column and a TRD 20 PGS-012 change (quarantine reason CHECK). |
| OQ-15 | Is store-and-forward after a network outage in the alpha? | Team 1 | Open | Treat lost records as missing days in the day ledger (never "resident did not speak", never imputed); any record that does arrive late follows OQ-10. |
| OQ-16 | How does a smart-home wake phrase ("Hey Alexa") fit the rule that no raw audio leaves the room, and who buys the devices? | PI Dr. Zvika Shinar and Tal Klap | Open | No change to Team 2 scope: the EchoWell cloud exposes no audio endpoint and accepts only §5 feature records; activation method is Team 1's. |
| OQ-17 | What are the Edgewood site access windows and visit cadence? | Grant team | Open | No software dependency; the device panel lists silent days so a visit can be planned when access exists. |
| OQ-18 | Should an EWMA trend be displayed against a baseline band (SRC-02 final processing box)? | Megan Stubbs with Shaba Rahavi | Open | Deferred: no EWMA computed or displayed in the MVP; the Resident detail page shows the CUSUM "Running change tally" chart only. |
| OQ-19 | Which team owns "compare to baseline" (baseline comparison, score and alarm logic between device and dashboard)? | Both teams; settled at the joint meeting led by Megan Stubbs | Open | Team 2's cloud pipeline (`analytics/` package, TRDs 07–09) implements baseline, scoring and alarm, consistent with SRC-14 B.3 (Team 2 owns analytics). The device sends features only. |
| OQ-20 | Which residents' sex values are known and recorded? | Ann Hartman and Lovette Ochieng (Edgewood interviews), with faculty/IRB for consent to record it | Open | `residents.sex` is nullable (F / M / null). The longitudinal arm does not use sex (each resident is compared with their own baseline). Facility F0 ranges are computed only per known sex and exclude residents with null sex. |
| OQ-24 | Are the data-alert rules and thresholds right (baseline stalled when days since epoch start ≥ baseline_n; possible other speaker on ≥ 1 quarantined session in 30 days; high set-aside at ≥ 0.20 of ≥ 10 received; device silent on shared devices or ≥ 2 consecutive silent days on a single-resident device)? | Study team (Megan Stubbs, Team 2 data processing) | Open | Use the provisional defaults in `config_parameters` (same in both profiles): `data_alert_set_aside_fraction`=0.20, `data_alert_device_silent_days`=2, `data_alert_baseline_stalled_enabled`=true; suppression baseline_stalled > high_set_aside (D-36). |
| OQ-25 | Is the "Anything that could explain it?" checklist complete and correctly worded (cold, cough or sore throat; dental problem or dentures out; new or changed medication; poor sleep or unusual day; room or device moved)? | Clinical team (PI Dr. Zvika Shinar with Edgewood clinical staff, input via Ann Hartman and Lovette Ochieng) | Open | Use the five provisional codes stored as the config list `review_explanations`; changing the list is a config change, not a code change (D-35). |
| OQ-26 | Who may review alarms, and how soon after an alarm must a review happen? | PI Dr. Zvika Shinar / clinical lead | Open | Roles clinician and admin may save reviews; no review deadline (SLA) is enforced; "Remind me in 24 h" snooze only changes emphasis (D-35, D-37). |
| OQ-27 | What false-alarm target (maximum false-alarm proportion of TRD 09 CUS-032 (a)) must the alarm-limit calibration meet, and which detection thresholds make DS-04 results gating? | PI Dr. Zvika Shinar, with Megan Stubbs (analysis specification) | Open | No target is assumed: the calibration (backlog FEAT-093) may run the CUS-031 grid and report the CUS-032 metrics for every combination, but no combination is selected and no `set-config` is run; production keeps k = 0.5, h = 5.0 and baseline_n = 30 (D-01). |
| OQ-28 | How does a user choose and view an earlier epoch's tally and baseline (TRD 02 FR-172): which control, label and position on the Resident detail page? | Shaba Rahavi (Team 2 software), with Megan Stubbs | Open | Interim (backlog FEAT-067): a labelled native `<select>` "Device period" above the tally chart lists epochs 1..`epoch_count` (default the current epoch); choosing an earlier epoch loads its scores and baseline period with `GET /api/v1/scores?resident_code=&epoch=` and reuses the tally chart and the UX-092 baseline line; the control is not shown when `epoch_count` is 1. |
| OQ-29 | For the new-admission comparison (TRD 02 FR-202 to FR-204), what minimum number of usable check-ins separates `not_enough_checkins` from a comparison, is the resident value taken from raw or morning-adjusted values, which features are compared, and how is a sex-specific range chosen (OQ-20)? | Shaba Rahavi and PI Dr. Zvika Shinar (with OQ-08) | Open | Interim (backlog FEAT-036, experimental arm only, D-06): compare the 7 composite features (TST-186) using the median of the resident's morning-adjusted usable values (as TRD 07 ANL-057 reads adjusted values); `not_enough_checkins` below 5 usable check-ins (the speaker-screen minimum reference count, TRD 25 AGT-044); use the range row whose `sex` equals the resident's sex, else the row with `sex` NULL, else `range_not_available`. In v0.1 no range rows exist, so every resident shows `range_not_available`. |

## 9. Overall MVP Readiness Assessment

The application is functionally complete for the MVP scope: every feature of checkpoints 1–8 is implemented and merged, the full automated suite passes on the audited commit (757 backend tests, 429 frontend tests, all E2E suites in CI), R01–R10 validation passes in both tiers, the security suite finds no bypass, and the hard rules hold (no LLM, no ML on the alarm path, no audio, synthetic data only, correct facility name).

**First verdict (8 Nov 2026): NOT READY FOR DEMO**, for three reasons: (1) open S2 repository-setting findings (no required status checks on `main`, inert CODEOWNERS); (2) MVP-02 without its test (TST-049); (3) deployment-dependent items pending Block 4.

**Review round 1 (algorithm lead, 12 Nov 2026, TRD 24 D-171..D-180)** resolved each reason:

1. The S2 findings are accepted as recorded: CIC-070's intent is met by PR review, restricted direct pushes and passing builds before merge (D-171); no team setup is needed for the demo and CODEOWNERS is a follow-up cleanup (D-172); the current protection settings are accepted (D-173). They are no longer blockers.
2. TST-049 and the other missing tests are added as part of Block 5 (D-174). TST-049 is already written and passing in GitHub PR #38 (all 283 SRC-05 records posted one at a time equal the batch plus a full run, with the trailing duplicate counted at the next run, API-044).
3. The interim deployment (Netlify, Render, Neon) is complete and functioning (D-180); the hosted smoke tests, backups and restore drill and demo acceptance are carried out as Block 5 validation activities, and the documentation is updated to match the deployed state.

Known gaps that remain, none blocking the demo:

- The GitHub variables with the hosted URLs (`STAGING_API_BASE_URL`, `STAGING_FRONTEND_URL`, production equivalents) are not set, so `deploy-staging.yml` stops at "Wait for staging" and `uptime.yml` skips every check. Setting them is a repository setting, not a deployment change; until then the hosted stack is checked by hand. This audit could not reach the hosted origins from its environment (network allow-list), so the deployed state is recorded on the algorithm lead's statement (D-180), supported by the Netlify deploy previews built for GitHub PRs #38 and #39.
- The informational TST-121 budget (`POST /sessions` p95 ≤ 1 s, 200 requests) is borderline on GitHub runners (1,014–1,070 ms in two of five recent runs).
- The nightly Firefox run fails until GitHub PR #39 (pin `@playwright/test` 1.64.1) is merged.
- The S3/S4 findings of §3.2 stay open, with their handling decided in D-174..D-179.

## 10. Recommendation

READY FOR DEMO

Justification: the build passes every functional, analytic and security test on `23e558b`, and the algorithm lead's review decisions (TRD 24 D-171..D-180) resolve the three reasons of the first verdict: the S2 repository-setting findings are accepted as not blocking (D-171..D-173), the TST-049 test for MVP-02 exists and passes in GitHub PR #38 and is completed with the other missing tests in Block 5 (D-174), and the interim deployment is complete with its hosted checks carried out as Block 5 validation (D-180). No application defect stands in the way; the remaining gaps are listed in §9.
