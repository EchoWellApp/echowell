# TRD Implementation Audit

Document: docs/reports/TRD_Implementation_Audit.md · Date: 8 November 2026 · Audited commit: `23e558b` (main after the checkpoint 8 merge, GitHub PR #31) · Checkpoint 9, `Implement_Feature_Batches.md` Phase 15, TRD 25 Phase 11, FEAT-091 · Location per TRD 25 AGT-032 / TRD 24 D-21

This report gives every requirement ID defined in the first column of a requirement table in TRDs 00–25 a status with evidence (FEAT-091-FR-02, FEAT-091-AC-02). It records findings only; no code, configuration or TRD was changed (TRD 25 §4.6 Phase 11 Pitfalls).

## 1. Method

1. IDs were extracted by script from every table row of `specs/TRD/*.md` whose first cell matches `[A-Z]{2,5}-\d{3}` (2,050 IDs, no duplicates across TRDs; AC-* acceptance criteria are tracked in `MVP_READINESS_CHECKLIST.md` §M and FEAT-091-FR-03).
2. **Test evidence:** an ID referenced by `req("ID")` in `tests/` or `// req: ID` in frontend tests is PASS when every referencing test passed on the audited commit: `pytest -q -p randomly` 757 passed, 19 skipped (smoke), 16 deselected (performance), 0 failed; `npx vitest run` 429 passed (71 files); CI `ci.yml` and `e2e.yml` on `23e558b` all required jobs `success` (`playwright` included). IDs covered only by post-deploy smoke tests are PENDING BLOCK 4; retired rows are NOT APPLICABLE.
3. **Inspection evidence:** every ID with no test reference (1,024) was inspected against code, configuration, workflows, docs, git history and read-only GitHub settings by seven independent reviewers, one per TRD group, with the rule that missing evidence is FAIL. Severity per TRD 13 §4.16 (S1 blocker … S4 cosmetic).
4. **PENDING BLOCK 4** marks a check that needs the hosted deployment (IMPLEMENTATION_ROADMAP §3.3, TRD 24 D-100); it is never FAIL in this checkpoint. **NOT APPLICABLE** marks retired rows (with the retiring D-ID), After-MVP / AWS / research items and requirements on people or later blocks.

## 2. Summary

| Status | Count |
|---|---|
| PASS | 1806 |
| FAIL | 81 |
| PENDING BLOCK 4 | 88 |
| NOT APPLICABLE | 75 |
| **Total** | **2050** |

Failures by severity: S1 0, S2 4, S3 40, S4 37. No S1 (no authentication bypass, no wrong research result, no audio path, no data loss).

### 2.1 By TRD

| TRD | IDs | PASS | FAIL | PENDING BLOCK 4 | NOT APPLICABLE |
|---|---|---|---|---|---|
| 00 Project Vision and Scope | 30 | 22 | 3 | 3 | 2 |
| 01 System Architecture TRD | 76 | 72 | 0 | 4 | 0 |
| 02 Functional Requirements Specification | 212 | 203 | 0 | 0 | 9 |
| 03 Non Functional Requirements | 102 | 80 | 11 | 9 | 2 |
| 04 Frontend TRD | 148 | 138 | 5 | 1 | 4 |
| 05 Backend API TRD | 122 | 120 | 2 | 0 | 0 |
| 06 Database Design TRD | 63 | 56 | 4 | 3 | 0 |
| 07 Analytics Engine TRD | 65 | 63 | 0 | 0 | 2 |
| 08 Baseline and Scoring Algorithm Spec | 43 | 43 | 0 | 0 | 0 |
| 09 CUSUM and Alerting Spec | 49 | 44 | 0 | 0 | 5 |
| 10 Data Ingestion and Validation Spec | 59 | 59 | 0 | 0 | 0 |
| 11 User Interface UX Spec | 275 | 243 | 1 | 0 | 31 |
| 12 Security and Authentication Spec | 121 | 99 | 8 | 12 | 2 |
| 13 Testing Strategy and Acceptance Criteria | 121 | 102 | 12 | 7 | 0 |
| 14 Test Data and Validation Spec | 72 | 66 | 1 | 1 | 4 |
| 15 Deployment and DevOps Spec | 83 | 46 | 0 | 29 | 8 |
| 16 CI CD Pipeline Spec | 59 | 51 | 4 | 4 | 0 |
| 17 Logging Monitoring and Error Handling | 62 | 54 | 5 | 2 | 1 |
| 18 GitHub Repository Standards | 63 | 36 | 20 | 6 | 1 |
| 19 API Contracts OpenAPI Spec | 27 | 27 | 0 | 0 | 0 |
| 20 PostgreSQL Schema Definition | 44 | 44 | 0 | 0 | 0 |
| 21 Environment Configuration Spec | 29 | 27 | 1 | 1 | 0 |
| 22 Third Party Services and Hosting | 30 | 20 | 0 | 6 | 4 |
| 23 Data Model and Entity Definitions | 25 | 24 | 1 | 0 | 0 |
| 24 Risk Assumptions and Open Questions | 18 | 18 | 0 | 0 | 0 |
| 25 AI Agent Build Instructions | 52 | 49 | 3 | 0 | 0 |

## 3. Failures

Ordered by severity. S2 = a Must fails with no workaround; S3 = a Should fails or a workaround exists; S4 = cosmetic, documentation or spec drift without wrong behaviour.

| ID | TRD | Priority | Severity | Finding | Evidence |
|---|---|---|---|---|---|
| CIC-070 | 16 | Must | S2 | Ruleset 25310033 requires PRs but lists no required status checks; D-162 says configured, live settings disagree | gh api repos/EchoWellApp/echowell/rules/branches/main (required_status_checks: []); branches/main protection.enabled=false |
| GIT-010 | 18 | Must | S2 | PR/1 approval/no force/no delete/conversations OK, but no stale dismissal, no CODEOWNER review, no required checks; admin bypass (7 direct pushes by srahavi). | gh api repos/../rules/branches/main: ruleset 25310033 has dismiss_stale_reviews_on_push=false, require_code_owner_review=false, required_status_checks=[]; direct pushes to main 29 Oct-3 Nov |
| GIT-037 | 18 | Must | S2 | Teams absent, not visible or lack write access, so CODEOWNERS is inert. Membership unverifiable via API (403). | gh api repos/EchoWellApp/echowell/codeowners/errors: 'Unknown owner' for team2-maintainers/-algorithm/-devops on all 14 lines |
| TST-150 | 13 | Must | S2 | All jobs run on PRs, but the main ruleset lists zero required status checks (contradicts D-162); red PRs could merge | gh api repos/EchoWellApp/echowell/rules/branches/main (required_status_checks: []); ci.yml, e2e.yml |
| AGT-013 | 25 | Must | S3 | One checkpoint not created from latest main / started before previous merge. | Checkpoint PRs #3,#4,#17,#18,#20,#22,#28,#31 each approved by Shaba9; cp4 branch built on feat/cp3 before PR #17 merged (CHECKPOINT_4_BACKEND_API.md:3) |
| AGT-030 | 25 | Must | S3 | A phase started before the previous checkpoint PR was merged. | Checkpoint order 1-8 correct, but cp4 (Phase 5) started on 27 Oct before PR #17 (cp3) merged 28 Oct |
| CIC-031 | 16 | Must | S3 | Triggers correct, but playwright is not a required check (ruleset lists no checks) | .github/workflows/e2e.yml:11-18; gh api rules/branches/main |
| DB-040 | 06 | Must | S3 | No test measuring <=150 ms DB time for resident-list queries on DS-08; only end-to-end read p95 is tested | tests/performance/test_api_latency.py::test_read_endpoints_p95_on_ds08; tests/performance/test_overview_queries.py (absent) |
| DB-042 | 06 | Should | S3 | No EXPLAIN check that resident-scoped queries avoid Seq Scan on DS-08 | tests/performance/ (no EXPLAIN / Seq Scan assertion) |
| ENV-022 | 21 | Must | S3 | Startup WARNING config_mismatch not implemented; per-run warning and profile precedence are. | backend/services/config_service.py:52-56 adds per-run config_mismatch warning; backend/main.py:53-66 lifespan logs nothing for FACILITY_TZ mismatch |
| FE-078 | 04 | Must | S3 | no runtime check of required fields; a missing field is not turned into an error state; no test found | frontend/services/api.ts:166-170 (res.json() as T) |
| FE-211 | 04 | Should | S3 | dark scheme via prefers-color-scheme, no toggle; but light --c-aside 2.23:1 and --c-quar 2.94:1 on --surface (<3:1), no pair check recorded | frontend/styles/tokens.css:42-66; no token-pair contrast analysis found |
| GIT-012 | 18 | Must | S3 | 7 commits reached main without a PR; checkpoint 4 branch was not created from latest main. | git log --first-parent main: 66c7705, aa7358e, fb46e63, f340545, 019b9e1, 756ea3c, caf3ade pushed directly; feat/cp4 built on feat/cp3 (CHECKPOINT_4_BACKEND_API.md:3) |
| GIT-014 | 18 | Should | S3 | Checkpoint PRs use merge commits (OK) but rebase merging is enabled and non-plan PRs are not squashed. | repo settings allow_rebase_merge=true; dependabot PRs #6-#26 and PRs #29/#30 merged with merge commits (git log --first-parent main) |
| GIT-020 | 18 | Must | S3 | Most commits on main are not Conventional Commits; CI PR-title check (ci.yml:61) only added in CP8. | git log --no-merges 7a607dc..main: 73/126 subjects not Conventional (e.g. 'CP8 group 1b: ...', 'Fix Netlify deploy'); merge titles 'Merge pull request #N' |
| GIT-030 | 18 | Must | S3 | Checkpoint-per-PR structure followed; other changes not always via short-lived PRs; cp4 not branched from latest main. | PRs #3,#4,#17,#18,#20,#22,#28,#31 = checkpoints 1-8; but direct pushes to main and cp4 built on cp3 branch (CHECKPOINT_4_BACKEND_API.md:3) |
| GIT-031 | 18 | Must | S3 | Checkpoint 4 work started while PR #17 (cp3) was still in review. All other checkpoints complied. | feat/cp4 first commit 9289b93 (27 Oct 20:20Z) parent c9b8cd4 on feat/cp3; PR #17 approved/merged 28 Oct 16:58Z; CHECKPOINT_4_BACKEND_API.md:3 |
| GIT-032 | 18 | Must | S3 | Not enforced by CODEOWNERS; in practice Shaba9 (algorithm lead) approved every PR (workaround). | .github/CODEOWNERS:2-10 maps paths to team2-algorithm, but gh api codeowners/errors: 'Unknown owner' for every team; ruleset require_code_owner_review=false |
| GIT-033 | 18 | Must | S3 | Most PR descriptions do not follow .github/pull_request_template.md. | PR bodies #18,#20,#22,#28,#29,#30,#31 lack 'Requirements implemented'/'Testing' template sections (only #4,#17 follow template) |
| GIT-070 | 18 | Should | S3 | Project labels (defect, sev:S1..S4, incident, open-question, area:*) absent; dependabot.yml and docs/deployment.md:244 reference them. | gh api labels: only GitHub defaults (bug, documentation, ...); docs/team_workflow.md (12 lines) has no gh label create script |
| GIT-071 | 18 | Should | S3 | No open-question issues exist. | specs/TRD/24: 26 OQs status Open; gh api issues: 0 issues |
| LOG-053 | 17 | Must | S3 | No 'ingest_batch_completed' event; batch path logs 'ingest_request' (no ingest_batch_id) and audit row ingest_batch.received. | backend/services/ingestion.py:175-193,368-442 |
| NFR-036 | 03 | Must | S3 | package-lock.json OK; Python has exact top-level pins only, no lock file with hashes and transitive deps unpinned | backend/requirements.txt:3-17; backend/requirements-dev.txt; frontend/package-lock.json |
| NFR-066 | 03 | Should | S3 | Plain-language labels exist; no Flesch-Kincaid grade check of the "Right now" strings | grep frontend/tests/docs/scripts for Flesch/readability: none |
| NFR-067 | 03 | Must | S3 | CI check greps only diagnoses\|severity and scans frontend/lib/wording.ts (a re-export barrel), not frontend/lib/wording/*.ts where copy lives; current copy is clean | .github/workflows/ci.yml:41 |
| NFR-086 | 03 | Must | S3 | Round trip only on empty DB (reset-test-db test uses master data only); no up/down test with the reference dataset loaded | tests/integration/db/test_migrations.py::test_tst_040_upgrade_downgrade_upgrade_round_trip; .github/workflows/ci.yml:116 |
| NFR-111 | 03 | Must | S3 | Traceability report not generated in CI and many Musts lack a linked test or documented inspection (this audit is the workaround) | tests/trace_report.py (not run in CI); docs/reports/traceability_inspections.md missing; trace_report lists 378 Must IDs w/o test/inspection |
| NFR-125 | 03 | Must | S3 | No invariant check after runs; holds on reference data via answer-key totals only | grep backend/analytics/tests for a per-resident count invariant: none; only SRC-05 totals in tests/validation/test_global_checks.py::test_vc_g01_status_totals |
| NFR-141 | 03 | Should | S3 | No tablet device emulation (iPad/Android) or 768 px test | frontend/playwright.config.ts:16-20; frontend/tests/e2e/responsive.spec.ts:8 |
| SEC-032 | 12 | Must | S3 | No guard caps JWT_EXPIRES_MINUTES at 60 in staging/production (le=1440 everywhere); blueprint sets 60 as workaround. No refresh tokens: OK. | backend/core/config.py:63; render.yaml:62,107 |
| SEC-033 | 12 | Must | S3 | Length/template/placeholder/profile/AS_OF guards exist, but other repo values (e.g. test secret Zq8vN3x... in tests/) are not refused in staging/production. | backend/core/config.py:33-35,202-205,227,243-251; tests/unit/backend/core/test_config.py |
| SEC-058 | 12 | Should | S3 | No code path writes config.changed for secret rotation and docs/deployment.md has no operations log section. | backend/services/audit_service.py:79; docs/deployment.md |
| SEC-155 | 12 | Must | S3 | Python pinned exactly and lockfile committed, but @netlify/plugin-nextjs is '^5.13.1' (not exact). | frontend/package.json:35; backend/requirements*.txt; frontend/package-lock.json |
| SEC-156 | 12 | Should | S3 | Critical Next.js 14.2.35 and high advisories waived until 2026-12-20 by owner decision D-159, beyond 7/30-day patch windows. | SECURITY_EXCEPTIONS.md:11-16; specs/TRD/24 D-159 |
| TDV-016 | 14 | Must | S3 | Fixtures captured from the API, but no test re-records and diffs them | frontend/tests/fixtures/capture.mjs; frontend/tests/fixtures/ds07/ |
| TST-013 | 13 | Must | S3 | Script exists but CI does not run/publish it, inspections file missing, and many Musts still lack a req marker (this audit) | tests/trace_report.py:1-30; .github/workflows/ci.yml (no trace_report step); docs/reports/traceability_inspections.md absent |
| TST-020 | 13 | Must | S3 | Table 4.3-A cases not implemented by ID; ~49 of 83 (ROB-01,SCR-05,BL-01,CUS-07,PIP-03,CFG-05...) have no identifiable test; validation suite covers end results | tests/unit/analytics/test_robust_stats.py:15-34; test_speaker_screen.py; test_cusum_engine.py |
| TST-049 | 13 | Must | S3 | No test ingests all SRC-05 one-by-one via POST /sessions and compares all derived tables with batch+full run; only R10 baselines via CSV | tests/validation/test_invariance.py:95-120 (R10 only, baselines only); tests/validation/test_global_checks.py:261 |
| TST-095 | 13 | Must | S3 | Property holds today but no test asserts production builds contain no MSW/fixture imports | grep: no msw/fixture import in frontend/app\|components\|lib\|services (non-test) |
| TST-185 | 13 | Must | S3 | Cohort change implemented, but no test of N01 15→16 records, cohort_changed audit row and list move | backend/services/pipeline_persistence.py:433-445; tests/integration/api/test_admissions.py (no 16th-record transition) |
| TST-188 | 13 | Must | S3 | No integration test of seeded logins + LoginRequest email validation; only indirect E2E coverage | tests/integration/test_seed_logins.py absent; frontend/tests/e2e/global-setup.ts (logs in all roles) |
| TST-194 | 13 | Must | S3 | No test of run-pipeline --scope all vs POST /pipeline/run derived-table equality; only scope R01,R02 tested | tests/integration/test_cli_pipeline.py:58-67; backend/cli.py:540-545 |
| TST-195 | 13 | Must | S3 | Refusals implemented, but tests miss invalid e-mail, duplicate e-mail, unknown role, unknown device, unknown key name | tests/integration/test_cli_credentials.py:35-90; backend/cli.py:131-191 |
| UX-224 | 11 | Must | S3 | light --c-aside 2.23:1, --c-quar 2.94:1 vs --surface as unoutlined bar segments; no §4.15 token-pair analysis recorded (axe text checks only) | frontend/styles/tokens.css:28-29; components/DailyCheckinsChart/DailyCheckinsChart.tsx:30-31 |
| AGT-012 | 25 | Must | S4 | Agent commits and opens PRs itself; human review gates merge, not commits. Process drift from literal rule. | 106 commits authored 'Claude' made before review (e.g. CP8 groups committed 5-7 Nov, first review 7 Nov 21:40Z) |
| API-003 | 05 | Must | S4 | No SQL in routers, but some handlers call several service functions/do logic (ingest_batch: name_map+parse_csv_batch+ingest_batch; checkins paging in router) | backend/api/ingest.py:75-95; backend/api/residents.py:84-96,108-112 |
| API-005 | 05 | Must | S4 | Services other than analytics_summary build SQLAlchemy select/delete queries directly instead of via repositories; behaviour correct | backend/services/pipeline_persistence.py:20,95-180; backend/services/engine_read.py:17,88-170; backend/services/pipeline_runner.py:28,145-180 |
| CIC-037 | 16 | Should | S4 | Job as specified, but pytest-randomly pinned 5.0.0 not 3.x (Dependabot f3a27b7) | .github/workflows/e2e.yml:167-226; backend/requirements-dev.txt:7 |
| CIC-072 | 16 |  | S4 | Waivers run to 20 Dec (D-159 allows), but none references a tracking issue; repo has no issues | SECURITY_EXCEPTIONS.md:11-15 |
| DB-031 | 06 | Must | S4 | Deploy job does not create the branch; manual runbook step named pre-<short-sha> (DEP-063), not pre-migration-<git sha>; live part Block 4 | .github/workflows/deploy-production.yml:9-11; specs/TRD/15_Deployment_and_DevOps_Spec.md:399; docs/deployment.md:161 |
| DB-046 | 06 | Should | S4 | ingest_batches_pipeline_run_idx created without CONCURRENTLY/autocommit_block and not listed in TRD 06 query-pattern section (TRD 20 §4.13 SQL) | backend/alembic/versions/0003_ingest_batch_pipeline_run.py:24 |
| DME-013 | 23 | Must | S4 | Pipeline writes adjusted_features, scores.z, data_alerts.days via ORM without the json_columns Pydantic helpers; DB CHECKs still guard shape | backend/services/pipeline_persistence.py:241-305; backend/schemas/json_columns.py:119-127 |
| FE-002 | 04 | Must | S4 | eslint-config-prettier is 10.x, §4.1 pins 9.x; other pins match, lockfile committed | frontend/package.json:50 ("eslint-config-prettier": "10.1.8"); specs/TRD/04_Frontend_TRD.md:80 |
| FE-005 | 04 | Must | S4 | Recharts 2.13.3, no other chart lib, but the facility range chart (§4.1 lists it as Recharts) is hand-built HTML/CSS | frontend/components/FacilityRangeChart/FacilityRangeChart.tsx:1-20 (no recharts import); frontend/package.json:31 |
| FE-091 | 04 | Must | S4 | AppHeader (listed as presentational) calls useOpenAlarmCount (useQuery GET /alerts) itself instead of receiving the count as a prop | frontend/components/AppHeader/AppHeader.tsx:49-51 |
| GIT-003 | 18 | Must | S4 | Skeleton docs kept but never filled in; content lives in docs/design/*. No backlog feature fills them. | docs/architecture.md, docs/algorithm.md, docs/database_design.md are 0-byte files (wc -l = 0) |
| GIT-011 | 18 | Must | S4 | Block 1/2 branches lack feat/docs/chore prefix; all Block 3 branches comply. | PR #1 head trd-generation, PR #2 head backlog-generation; later branches feat/cpN-*, docs/*, fix/* comply |
| GIT-021 | 18 | Should | S4 | Scopes outside the allowed list are in use. | scopes used on main: cp8, security, cli, e2e (git log subjects) |
| GIT-024 | 18 | Should | S4 | Commit bodies do not consistently reference implemented requirement IDs. | git log 7a607dc..main: 0 'Implements:' lines; 61/106 agent commits cite any requirement/feature ID |
| GIT-043 | 18 | Should | S4 | Many suppressions name the rule but carry no reason. | e.g. backend/cli.py:485,556; backend/services/validation.py:371; backend/api/openapi.py:328 — rule named but no reason comment |
| GIT-094 | 18 | Must | S4 | A document still references the removed repository path for SRC-07 (human-authored prompt). | specs/prompts/TRD_Generation_Prompt.md:31 lists 'EchoWell_preprint-113062-submitted.pdf' under specs/business-requirements/ |
| GIT-095 | 18 | Must | S4 | Allowed by D-168 and TST-070 but GIT-095 not amended; CI does not check 1 MB/location rule. | frontend/app/fonts/SourceSans3-latin-variable.woff2 (binary not .svg/.png/.ico); tests/fixtures/answer_key/*.xlsx outside specs/; ci.yml:34 checks only 10 MB |
| GIT-097 | 18 | Should | S4 | Doc drift: font committed per D-168; TRD 18 not updated. | frontend/app/fonts/SourceSans3-latin-variable.woff2 committed (c9ea154); TRD 24 D-168 accepts it but TRD 18 GIT-097 unchanged |
| GIT-111 | 18 | Must | S4 | Platform pin upgrade merged before demo (not a security fix), then reverted; current pins compliant. | PR #21 (python 3.12-slim→3.15-slim) merged 1 Nov, reverted by direct push 019b9e1; backend/Dockerfile:5 now python:3.12-slim |
| LOG-063 | 17 | Must | S4 | Failed-resident warnings use stage 'persistence' (not in the list); whole-run exceptions carry no stage name. | backend/services/pipeline_runner.py:402; pipeline_runner.py:273 |
| LOG-080 | 17 | Must | S4 | Both boundaries show copy + Reload but never show the request reference when available (FE-067). | frontend/app/(protected)/error.tsx; frontend/app/global-error.tsx |
| LOG-081 | 17 | Must | S4 | 401/403/404 mapped; 429 and 503 messages of LOG-081 absent (only login 429 text, other errors go to panel error state). TRD 04/11 lack these strings. | frontend/services/api.ts:157-163; frontend/components/SectionState/SectionState.tsx:43-55; frontend/lib/wording/common.ts:99 |
| LOG-115 | 17 | Must | S4 | data_alerts_updated logs only open counts per kind; resolved counts missing. | backend/services/pipeline_runner.py:422-427 |
| NFR-010 | 03 | Should | S4 | LCP<=2.5s asserted (desktop preset, passing on PRs); INP<200ms and Fast 4G throttling not checked (TST-125 narrowed it) | frontend/lighthouserc.json:20-27; .github/workflows/e2e.yml:255 |
| NFR-013 | 03 | Should | S4 | Updates without reload via query invalidation; the 1 s budget is never asserted (default expect timeout) | frontend/components/AlarmReviewPanel/AlarmReviewPanel.tsx:44; frontend/tests/e2e/mutating.spec.ts:55 |
| NFR-085 | 03 | Should | S4 | Docstrings with TRD IDs only partial (many IDs in module docstrings) | AST scan: 44 of 71 public analytics functions and 35 of 134 public service functions lack docstrings |
| NFR-093 | 03 | Should | S4 | Cut-over procedure documented; no effort estimate (<=5 person-days) or migration analysis recorded | specs/TRD/15_Deployment_and_DevOps_Spec.md:507,558 (DEP-117) |
| SEC-055 | 12 | Must | S4 | Generator and per-env documented; 180-day and departure rotation not in docs/deployment.md or checklist. | .env.example:8; .env.production.example:8; docs/deployment.md:277; docs/reports/DEPLOYMENT_CONFIGURATION_GUIDE.md:119 |
| SEC-056 | 12 | Must | S4 | Per-env role passwords are Block 4 (B.04); 180-day/departure rotation cadence and >=32-char rule not documented in ops docs. | specs/backlog/DEPLOYMENT_CHECKLIST.md:52 (B.04); docs/deployment.md:278 |
| SEC-057 | 12 | Must | S4 | Create/revoke CLI exists, but 365-day/device-replacement rotation procedure is not documented for operators. | backend/cli.py:185 (revoke-api-key); docs/deployment.md:212 |
| TST-001 | 13 | Must | S4 | pytest 9.1.1 (Dependabot cf1b511) not 8.x as TST-001/TRD16 §6 pin; pytest-cov 7.1 vs 5.x; no D entry; Py3.12+TestClient+httpx ok | backend/requirements-dev.txt:5 (pytest==9.1.1); pyproject.toml:57-61 |
| TST-012 | 13 | Should | S4 | Test names mostly lack §4.3 case IDs (e.g. test_vectors, test_r01_loudness...; no test_rob_*/test_cus_*); only vc_r/vc_g/tst_011 names carry IDs | tests/unit/analytics/test_robust_stats.py:34; tests/unit/analytics/*.py |
| TST-160 | 13 | Must | S4 | Defects tracked in PR review rounds, never as labelled GitHub issues | gh api labels (no defect / sev:S* labels); no issues exist |
| VIS-012 | 00 | Must | S4 | Marker only on Summary note and list note (per UX-164); status legend and What's happening texts carry no marker as VIS-012 literally requires; TRD drift | frontend/lib/wording/common.ts:7; frontend/lib/wording/chart.ts:188; frontend/lib/wording/list.ts:66; frontend/components/StatusLegend/StatusLegend.tsx:12 |
| VIS-014 | 00 | Must | S4 | Traceability rule not met across TRDs; documentation drift, no behaviour impact | script over specs/TRD/*.md requirement rows: 936 of 1983 rows have no BR-xx in the trace column (e.g. VIS-007, FE-003, NFR-114) |
| VIS-020 | 00 | Must | S4 | Protected pages and /study line OK; /login passes meta=undefined so on test_v0_1 it omits the required "Test data only (...). No real residents." prefix (UX-400) | frontend/app/login/page.tsx:29; frontend/lib/wording/common.ts:20; frontend/tests/pages/login.test.tsx:13 |

## 4. Pending Block 4

| ID | TRD | Repo-side evidence and what remains |
|---|---|---|
| ARC-005 | 01 | tests/smoke/test_tls.py; netlify.toml:27 (HSTS); render.yaml — TLS terminated by Netlify/Render; verification needs hosted origins |
| ARC-007 | 01 | docs/deployment.md:68,81; specs/TRD/22_Third_Party_Services_and_Hosting.md — Provider-managed encryption evidence is a platform-settings check |
| ARC-008 | 01 | render.yaml:20 (DATA_SOURCE_LABEL); docs/deployment.md:11 — Policy documented; ingest-batch audit on hosted stack is Block 4 |
| ARC-084 | 01 | render.yaml:47 (region ohio); docs/deployment.md:26 — Render region in Blueprint; Neon region is a dashboard setting |
| CIC-043 | 16 | .github/workflows/deploy-staging.yml:77 — environment: staging in repo; branch rule is GitHub env setting (API not accessible) |
| CIC-053 | 16 | .github/workflows/deploy-production.yml:15-94,96-103 — verify job present; production env required reviewer is a GitHub setting (Block 4) |
| CIC-060 | 16 | .github/workflows/uptime.yml:133-211 — Workflow complete; real URLs/vars not configured yet |
| CIC-090 | 16 | .github/workflows/*.yml (only the 7 named secrets referenced) — Stored GitHub secrets not readable via API; env setup is Block 4 |
| DB-050 | 06 | specs/TRD/22_Third_Party_Services_and_Hosting.md:115; docs/deployment.md:219-221 — Needs Neon plan restore window settings and restore drill on hosted DB; repo docs record the weekly dump policy |
| DB-051 | 06 | docs/deployment.md:221 — Restore drill on Neon not yet run; deployment.md has placeholder to record result |
| DB-052 | 06 | specs/TRD/22_Third_Party_Services_and_Hosting.md:115 — Provider-managed encryption at rest is a platform setting; MVP data is synthetic only |
| DEP-002 | 15 | .github/workflows/deploy-production.yml:153-160; netlify.toml:1-3 — Netlify site builds-stopped setting; repo-side CLI publish exists |
| DEP-003 | 15 | render.yaml:87-128; .github/workflows/deploy-production.yml:113-150 — autoDeployTrigger off + Render API commitId deploy in repo; live services pending |
| DEP-004 | 15 | render.yaml:41-84 (checksPass); netlify.toml — Platform GitHub integrations; staging vars not yet set |
| DEP-005 | 15 | docs/deployment.md:81-84 — Neon branches main/staging live check |
| DEP-006 | 15 | render.yaml:61,106 (JWT_SECRET sync:false per service) — Cross-environment credential rejection needs live envs |
| DEP-007 | 15 | tests/integration/test_cli_seed.py:54-63 — Live DB content; repo refuses seed in production |
| DEP-008 | 15 | docs/deployment.md — Policy on hosted interim stack; checked in Block 4 |
| DEP-009 | 15 | backend/core/config.py:191-195 (sslmode=require check) — TLS on hosted hops and at-rest encryption are platform checks |
| DEP-030 | 15 | docs/deployment.md:81 — SELECT version() on hosted DBs |
| DEP-031 | 15 | docs/deployment.md:26,81 — Neon region is a platform setting |
| DEP-032 | 15 | backend/alembic/env.py:3-6; render.yaml:25,59 — Repo uses DATABASE_MIGRATION_URL for Alembic; Neon pooled/direct endpoints live |
| DEP-062 | 15 | .github/workflows/deploy-production.yml:70-94 — Guard on successful deploy-staging run exists; staging run not yet green |
| DEP-063 | 15 | docs/deployment.md:161 — Release-time Neon restore branch |
| DEP-073 | 15 | tests/smoke/test_production_smoke.py:35-80 — Live production content; note: no SQL check possible in smoke (CIC-050 forbids DB URL) |
| DEP-074 | 15 | .github/workflows/deploy-staging.yml:39-57,88-107 — Repo-side re-seed logic exists; live staging pending |
| DEP-075 | 15 | docs/deployment.md:168 — First production admin in Render Shell at release |
| DEP-080 | 15 | tests/smoke/test_staging_smoke.py::test_a_health_ok_with_expected_version; tests/smoke/test_staging_smoke.py::test_b_frontend_login_page; tests/smoke/test_staging_smoke.py::test_c_login_as_seeded_researcher — Covered only by post-deploy smoke tests (skipped without SMOKE_API_BASE_URL) |
| DEP-081 | 15 | tests/smoke/test_production_smoke.py::test_a_health_ok_with_expected_version; tests/smoke/test_production_smoke.py::test_b_frontend_login_page_over_https; tests/smoke/test_production_smoke.py::test_c_residents_without_token_is_401_problem — Covered only by post-deploy smoke tests (skipped without SMOKE_API_BASE_URL) |
| DEP-082 | 15 | tests/smoke/wait_for_deploy.py; deploy-staging.yml:66-69 — 15 s poll/15 min timeout in repo; duration measured on live run |
| DEP-083 | 15 | docs/deployment.md:198-200; deploy-production.yml:236-238 — Manual check after production deploy |
| DEP-085 | 15 | docs/deployment.md:214 — Rollback rehearsal |
| DEP-090 | 15 | docker-compose.yml:65-78; docs/deployment.md:57 — Demo fallback; compose demo profile exists |
| DEP-091 | 15 | docs/deployment.md:229 — Fallback laptop demo |
| DEP-092 | 15 | docs/deployment.md:232 — Fallback rehearsal to be recorded |
| DEP-093 | 15 |  — Demo content |
| DEP-095 | 15 | docs/deployment.md:85,218 — PITR window to be recorded in Phase 10 |
| DEP-096 | 15 | docs/deployment.md:219 — Weekly dumps by data steward |
| DEP-097 | 15 | docs/deployment.md:221 — Restore drill |
| DEP-101 | 15 | docs/deployment.md:250-256 — Weekly live usage check procedure documented |
| ENV-051 | 21 | docs/reports/DEPLOYMENT_CONFIGURATION_GUIDE.md:119 unique secret per env; tests/unit/test_env_templates.py:139 dev JWT refused in production — Hosted values set in Block 4. |
| FE-061 | 04 | netlify.toml:24-31 — repo side done: header set verbatim in netlify.toml; response-header check needs hosted Netlify origins |
| GIT-060 | 18 | .github/workflows/deploy-production.yml:61-66 computes/creates v0.x.y tag; gh api tags = [] — No release yet; repo-side workflow exists. |
| GIT-061 | 18 | .github/workflows/deploy-production.yml (version input/tag); no tags — Applies to production releases (Block 4). |
| GIT-062 | 18 | gh api repos/../tags = []; deploy-production.yml:234 gh release create — First release v0.1.0 is a Block 4 event. |
| GIT-063 | 18 | deploy-production.yml:234 sole tag creator; tag protection is a platform setting (API 404/403) — Repo-side done; tag rule unverifiable until Block 4. |
| GIT-064 | 18 | backend/services/health_service.py:23 version=settings.git_sha; deploy-production.yml:234 release --target SHA — Backend reports GIT_SHA; release mapping awaits first release. |
| GIT-081 | 18 | security_and_analysis not readable (null/403); repo-side gitleaks gate in ci.yml (.gitleaks.toml) — Platform setting; verify in Block 4. |
| LOG-103 | 17 | .github/workflows/uptime.yml:12-13; docs/deployment.md:238 — Workflow exists (every 30 min); live run history needed. |
| LOG-114 | 17 | docs/deployment.md:244; specs/backlog/DEPLOYMENT_CHECKLIST.md:162 (K.04) — Watchers documented; confirmation is a Phase 10 GitHub setting. |
| NFR-008 | 03 | frontend/services/api.ts:40; frontend/lib/queryClient.ts:5 — Manual staging cold-start check; client retries timeouts so loading persists |
| NFR-020 | 03 | .github/workflows/uptime.yml:13 — Uptime workflow exists; availability during demo window needs production |
| NFR-024 | 03 | docs/deployment.md:219; .github/workflows/deploy-production.yml:10 — Interim waiver; Neon PITR window and DEP-096 dump are platform/procedure evidence |
| NFR-025 | 03 | docs/deployment.md — Restore drill before 15 Nov is a Block 4 rehearsal |
| NFR-042 | 03 | tests/smoke/test_tls.py; backend/core/config.py:217 — Startup sslmode check exists; TLS scan of hosted endpoints is Block 4 |
| NFR-043 | 03 | tests/security/test_transport_and_secrets.py::test_backend_sends_hsts_in_staging_and_production; netlify.toml:27; tests/smoke/test_staging_smoke.py::test_i_api_hsts_and_https_redirect — HSTS in code/config; redirect check on hosted origins pending |
| NFR-044 | 03 | docs/deployment.md:68 — Provider encryption evidence is a platform check |
| NFR-045 | 03 | render.yaml:20; docs/deployment.md:11 — Policy documented; hosted ingest audit pending |
| NFR-052 | 03 | render.yaml:47; docs/deployment.md:26 — Render ohio in Blueprint; Neon region is a dashboard setting |
| SEC-001 | 12 | docs/deployment.md:11; specs/backlog/DEPLOYMENT_CHECKLIST.md:22 — Rule documented; seeds are synthetic (database/seeds/test_v0_1). Hosted data content verifiable only on live stack. |
| SEC-003 | 12 | specs/backlog/DEPLOYMENT_CHECKLIST.md:23; docs/deployment.md:168; checklist G.08 — Rule documented (test devices only); key issuance happens on hosted stack in Phase 10. |
| SEC-053 | 12 | gh api repos/EchoWellApp/echowell -> security_and_analysis null (not visible) — Repo setting not readable with available token; platform setting to confirm in Block 4. |
| SEC-060 | 12 | netlify.toml:27 (HSTS); tests/smoke/test_tls.py; checklist DEP-080(j)/DEP-081(g) — TLS/redirect on hosted origins needs live check; repo-side HSTS header and TLS smoke test exist. |
| SEC-063 | 12 | docs/deployment.md:68,81 — Provider-managed encryption at rest is a Neon platform property; AWS KMS part is AWS cut-over. |
| SEC-064 | 12 | tests/smoke/test_tls.py; render.yaml — No plain-HTTP path is a Render edge property; verify on live origin. |
| SEC-066 | 12 | tests/smoke/test_tls.py::test_tls_policy_api; tests/smoke/test_tls.py::test_tls_policy_frontend — Covered only by post-deploy smoke tests (skipped without SMOKE_API_BASE_URL) |
| SEC-115 | 12 | specs/backlog/DEPLOYMENT_CHECKLIST.md:56 (B.08) — Custody of Neon owner credentials is checklist row B.08 (unchecked, Phase 10); apps use echowell_* roles. |
| SEC-160 | 12 | specs/backlog/DEPLOYMENT_CHECKLIST.md:57,152 (B.09, J.01); docs/deployment.md:85 — PITR window to be recorded in Phase 10; regeneration from seeds available (database/seeds). |
| SEC-162 | 12 | specs/backlog/DEPLOYMENT_CHECKLIST.md:154 (J.03) — Restore drill needs hosted stack. |
| SEC-163 | 12 | docs/deployment.md:212; specs/backlog/DEPLOYMENT_CHECKLIST.md:145 (I.04) — Recovery procedure documented; demo requires a restore drill. |
| SEC-170 | 12 | docs/deployment.md:271-279; backend/cli.py:185 — Containment table complete in docs; 1-hour executability is a drill. |
| TDV-007 | 14 | tests/integration/test_cli_seed.py:54-63 (seed refused in production); render.yaml:17-19,29-30 — No real records exist yet; separation on hosted DBs checked in Block 4; repo guards exist |
| TPS-005 | 22 | docs/deployment.md:63-69 owner/administrator columns — Account ownership/MFA verified in Block 4. |
| TPS-006 | 22 | docs/deployment.md:63-69 table; 'Verified on' = 'recorded in Phase 10' — Table exists; verification dates pending Block 4. |
| TPS-007 | 22 | docs/deployment.md:61 limits indicative until verified at account creation |
| TPS-031 | 22 | docs/deployment.md:24,26 Neon PG16 aws-us-east-1 main/staging — Neon project configuration is a Block 4 platform check. |
| TPS-040 | 22 | docs/deployment.md:65; org settings not readable (API 403) — Org 2FA requirement unverifiable from repo. |
| TPS-061 | 22 | backend/core/monitoring.py:9; docs/deployment.md:266 go-live rule; production SENTRY_DSN decision 'recorded in Phase 10' — Repo-side rule documented; production value set in Block 4. |
| TST-152 | 13 | tests/smoke/test_production_smoke.py::test_a_health_ok_with_expected_version; tests/smoke/test_production_smoke.py::test_b_frontend_login_page_over_https; tests/smoke/test_staging_smoke.py::test_a_health_ok_with_expected_version — Covered only by post-deploy smoke tests (skipped without SMOKE_API_BASE_URL) |
| TST-170 | 13 | docs/reports/CHECKPOINT_8_DEPLOYMENT_CONFIG.md — Acceptance on the release candidate with Block 4 PR and GitHub Release evidence |
| TST-180 | 13 |  — Demo acceptance step 4 on the demo environment |
| TST-181 | 13 |  — Demo acceptance step 5 |
| TST-182 | 13 | docs/deployment.md — Demo-time database separation (answer key on isolated DB, real record in production) |
| TST-183 | 13 | docker-compose.yml:65-78; docs/deployment.md:229 — Local fallback demo; repo-side compose demo profile exists |
| TST-184 | 13 |  — Demo resident pill under production profile |
| VIS-016 | 00 | render.yaml; netlify.toml; .github/workflows/deploy-staging.yml; .github/workflows/deploy-production.yml — Repo-side Netlify/Render/Neon config and deploy workflows exist; live deployment is Block 4 |
| VIS-023 | 00 | backend/core/config.py:217; tests/security/test_transport_and_secrets.py::test_every_database_url_needs_sslmode_require; tests/smoke/test_tls.py — Repo-side sslmode startup check and TLS smoke test exist; hosted TLS and provider at-rest encryption need live stack |
| VIS-024 | 00 | render.yaml:20 (DATA_SOURCE_LABEL); database/seeds/test_v0_1/; docs/deployment.md:11 — Only synthetic seeds in repo; audit of hosted ingest batches needs live stack |

## 5. Full matrix

Evidence: test node IDs (`path::test`), frontend test files with the test title, or `path:line` for inspection. Source = how the status was established.

### 00 Project Vision and Scope

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| VIS-001 | Must | PASS |  | tests/security/test_no_audio.py::test_audio_is_refused_everywhere; tests/contract/test_openapi_contract.py::test_no_audio_or_identity_properties; .github/workflows/ci.yml:26 | No audio endpoint/column/field; audio refused on ingest; CI blocks audio files | inspection |
| VIS-002 | Must | PASS |  | tests/validation/test_harness.py::test_tier_a_matches_the_answer_key; tests/validation/test_r09_step_change.py; analytics/pipeline.py:231 | Per-resident frozen baseline per epoch; R01-R10 validation suite | inspection |
| VIS-003 | Must | PASS |  | frontend/lib/wording/chart.ts:185; frontend/lib/wording/list.ts:63; grep of frontend/app,components,lib for §4.2 forbidden terms: none | UI copy uses detection wording; no diagnosis/severity/risk-score/abnormal/at-risk terms found in UI or API text | inspection |
| VIS-004 | Must | PASS |  | backend/requirements.txt; frontend/package.json; .github/workflows/ci.yml:44; tests/security/test_static_scans.py::test_no_forbidden_dependencies | No LLM SDK/API; CI dependency/import scan | inspection |
| VIS-005 | Must | PASS |  | pyproject.toml:39 (import-linter analytics purity); analytics/pipeline.py:211; .github/workflows/ci.yml:44 | Alarm path is robust stats + CUSUM in pure analytics/; ML packages blocked in CI | inspection |
| VIS-006 | Must | PASS |  | database/schema.sql:699; tests/integration/db/test_master_tables.py::test_no_identifying_columns; tests/security/test_static_scans.py::test_no_personal_or_audio_columns | Residents identified by resident_code only | inspection |
| VIS-007 | Must | PASS |  | frontend/lib/wording/common.ts:11; render.yaml:20; tests/unit/backend/core/test_config.py::test_forbidden_facility_name_rejected | UI renders meta.facility_name (seeded from FACILITY_NAME=Edgewood) | inspection |
| VIS-008 | Must | PASS |  | .github/workflows/ci.yml:37; repo grep: term only in specs/ and docs/reports prohibition/grep statements | Old name never used for the facility; CI check excludes specs/ and docs/reports/ | inspection |
| VIS-009 | Must | PASS |  | tests/integration/api/test_admissions.py::test_empty_state |  | test |
| VIS-010 | Must | PASS |  | tests/validation/test_harness.py::test_tier_a_matches_the_answer_key; tests/validation/test_harness.py::test_tier_b_matches_the_answer_key; .github/workflows/ci.yml:122 | R01-R10 at 1e-6 in backend-test CI job | inspection |
| VIS-011 | Must | PASS |  | backend/alembic/versions/0002_seed_config_parameters.py:45; tests/integration/db/test_config_seed.py::test_ac_pgs_10_config_rows_per_profile | baseline_n 30 production / 16 test_v0_1 via PIPELINE_PROFILE | inspection |
| VIS-012 | Must | FAIL | S4 | frontend/lib/wording/common.ts:7; frontend/lib/wording/chart.ts:188; frontend/lib/wording/list.ts:66; frontend/components/StatusLegend/StatusLegend.tsx:12 | Marker only on Summary note and list note (per UX-164); status legend and What's happening texts carry no marker as VIS-012 literally requires; TRD drift | inspection |
| VIS-013 | Must | PASS |  | tests/unit/backend/test_no_outbound_alerts.py::test_no_messaging_client; backend/requirements.txt | No messaging/notification client; alerts only in dashboard | inspection |
| VIS-014 | Must | FAIL | S4 | script over specs/TRD/*.md requirement rows: 936 of 1983 rows have no BR-xx in the trace column (e.g. VIS-007, FE-003, NFR-114) | Traceability rule not met across TRDs; documentation drift, no behaviour impact | inspection |
| VIS-015 | Must | PASS |  | specs/TRD/10_Data_Ingestion_and_Validation_Spec.md; specs/TRD/19_API_Contracts_OpenAPI_Spec.md; docs/api_reference/openapi.json | Team 1 boundary specified as record schema, endpoints and X-API-Key only | inspection |
| VIS-016 | Must | PENDING BLOCK 4 |  | render.yaml; netlify.toml; .github/workflows/deploy-staging.yml; .github/workflows/deploy-production.yml | Repo-side Netlify/Render/Neon config and deploy workflows exist; live deployment is Block 4 | inspection |
| VIS-017 | Must | PASS |  | tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv; tests/fixtures/answer_key/SHA256SUMS; tests/validation/test_answer_key_integrity.py | Validation uses synthetic SRC-03/SRC-05 only; no public datasets | inspection |
| VIS-018 | Must | PASS |  | specs/TRD/01_System_Architecture_TRD.md:364 (§4.10 mapping); backend/core/config.py:42; backend/Dockerfile:36; specs/TRD/15_Deployment_and_DevOps_Spec.md:507 | Env-only config, OCI image, standard PG16; migration mapping analysis in TRD 01 §4.10/TRD 15 §4.16 | inspection |
| VIS-019 | Must | PASS |  | tests/validation/test_r02_missing_days.py; tests/unit/analytics/test_day_ledger.py::test_checked_in_gap_and_missed | Missing days recorded in ledger, never imputed | inspection |
| VIS-020 | Must | FAIL | S4 | frontend/app/login/page.tsx:29; frontend/lib/wording/common.ts:20; frontend/tests/pages/login.test.tsx:13 | Protected pages and /study line OK; /login passes meta=undefined so on test_v0_1 it omits the required "Test data only (...). No real residents." prefix (UX-400) | inspection |
| VIS-021 | Should | NOT APPLICABLE |  | specs/TRD/00_Project_Vision_and_Scope.md:149, :302 | Requirement on people/process: interviews 26-30 Oct; revision due ~13 Nov 2026, not yet due; personas still marked PROVISIONAL | inspection |
| VIS-022 | Must | PASS |  | specs/TRD/24_Risk_Assumptions_and_Open_Questions.md:92 (OQ-12); frontend/lib/wording/common.ts:7 | OQ-dependent items cite OQ IDs and implement interim behaviour (e.g. CLINICAL_WORDING_APPROVED=false) | inspection |
| VIS-023 | Must | PENDING BLOCK 4 |  | backend/core/config.py:217; tests/security/test_transport_and_secrets.py::test_every_database_url_needs_sslmode_require; tests/smoke/test_tls.py | Repo-side sslmode startup check and TLS smoke test exist; hosted TLS and provider at-rest encryption need live stack | inspection |
| VIS-024 | Must | PENDING BLOCK 4 |  | render.yaml:20 (DATA_SOURCE_LABEL); database/seeds/test_v0_1/; docs/deployment.md:11 | Only synthetic seeds in repo; audit of hosted ingest batches needs live stack | inspection |
| VIS-025 | Must | PASS |  | specs/business-requirements/REFERENCES.md:7; git ls-files (only team-owned PROSPERO.pdf and flowchart .docx) | SRC-07 preprint linked, not committed | inspection |
| VIS-026 | Must | PASS |  | backend/core/config.py:202; tests/unit/backend/core/test_config.py::test_cfg_06_production_refuses_test_profile; tests/unit/backend/core/test_config.py::test_cfg_06_process_exits_1_with_critical_log | Startup refused, exit 1 | inspection |
| VIS-027 | Must | NOT APPLICABLE |  | specs/TRD/15_Deployment_and_DevOps_Spec.md:558 (DEP-117) | AWS go-live/cut-over item; not part of this build | inspection |
| VIS-028 | Must | PASS |  | frontend/app/(protected)/residents/[residentCode]/review/page.tsx; frontend/app/(protected)/study/page.tsx; backend/api/permissions.py:44; frontend/tests/e2e/mutating.spec.ts (E2E-18 save review on R09) | Review saving clinician/admin; /study researcher/admin | inspection |
| VIS-029 | Must | PASS |  | frontend/lib/wording/study.ts:78; backend/api/permissions.py:47 | Data alerts shown as "Data problems to follow up" on Study team page, not as alarms | inspection |
| VIS-030 | Must | PASS |  | database/seeds/load_evaluation_ground_truth.py; tests/integration/db/test_ground_truth_loader.py::test_refuses_outside_test_v0_1; tests/integration/pipeline/test_runner_persistence.py::test_runner_never_reads_the_answer_key | Loader refuses outside test_v0_1; pipeline never reads the table | inspection |

### 01 System Architecture TRD

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| ARC-001 | Must | PASS |  | backend/api/sessions.py:32; backend/api/ingest.py:66 | Ingest API is the only Team 1 boundary; nothing runs on the device | inspection |
| ARC-002 | Must | PASS |  | backend/services/validation.py; tests/integration/api/test_sessions.py::test_extra_field_and_audio_are_refused; tests/integration/api/test_ingest.py::test_src05_upload | Schema v0.1 record over JSON/CSV; extra fields refused | inspection |
| ARC-003 | Must | PASS |  | tests/contract/test_openapi_contract.py::test_no_audio_or_identity_properties; tests/security/test_no_audio.py::test_audio_inside_a_multipart_upload_is_refused |  | inspection |
| ARC-004 | Must | PASS |  | backend/api/deps.py; tests/security/test_auth_matrix.py::test_pipeline_run_key_scopes; tests/security/test_api_keys.py::test_key_without_ingest_scope_is_forbidden | X-API-Key scopes ingest:write/pipeline:run; JWT for users | inspection |
| ARC-005 | Must | PENDING BLOCK 4 |  | tests/smoke/test_tls.py; netlify.toml:27 (HSTS); render.yaml | TLS terminated by Netlify/Render; verification needs hosted origins | inspection |
| ARC-006 | Must | PASS |  | backend/core/config.py:217; tests/security/test_transport_and_secrets.py::test_every_database_url_needs_sslmode_require; tests/security/test_transport_and_secrets.py::test_staging_without_sslmode_exits_1_and_local_starts | Startup check enforces sslmode in staging/production | inspection |
| ARC-007 | Must | PENDING BLOCK 4 |  | docs/deployment.md:68,81; specs/TRD/22_Third_Party_Services_and_Hosting.md | Provider-managed encryption evidence is a platform-settings check | inspection |
| ARC-008 | Must | PENDING BLOCK 4 |  | render.yaml:20 (DATA_SOURCE_LABEL); docs/deployment.md:11 | Policy documented; ingest-batch audit on hosted stack is Block 4 | inspection |
| ARC-010 | Must | PASS |  | frontend/app/layout.tsx; frontend/tsconfig.json:7; netlify.toml:7 | Next.js App Router, TypeScript strict, Netlify | inspection |
| ARC-011 | Must | PASS |  | backend/main.py; backend/Dockerfile:5; render.yaml:43 | FastAPI on python:3.12-slim, Render web service | inspection |
| ARC-012 | Must | PASS |  | docker-compose.yml:10; .github/workflows/ci.yml:84; docs/deployment.md:81 | PostgreSQL 16 (postgres:16-alpine in compose/CI; Neon PG16 documented) | inspection |
| ARC-013 | Must | PASS |  | backend/services/pipeline_runner.py:32 | analytics/ package imported and run in backend process | inspection |
| ARC-014 | Must | PASS |  | frontend/services/api.ts; frontend/lib/config.ts; grep frontend for DATABASE/postgres: none | Frontend uses REST API only | inspection |
| ARC-015 | Must | PASS |  | tests/integration/api/test_analytics.py::test_read_only_engine |  | test |
| ARC-016 | Must | PASS |  | tests/unit/test_repository_layout.py::test_skeleton_files_kept; tests/unit/test_repository_layout.py::test_analytics_has_exactly_the_trd07_modules |  | inspection |
| ARC-017 | Must | PASS |  | backend/main.py:79; .github/workflows/ci.yml:164; tests/contract/test_openapi_contract.py::test_generated_equals_committed; tests/contract/test_openapi_contract.py::test_served_document_and_docs | Served at /api/v1/openapi.json; CI diff of contract and api-types.ts | inspection |
| ARC-018 | Must | PASS |  | backend/requirements.txt; netlify.toml:27 (CSP connect-src); frontend/app/fonts/ | Only Netlify/Render/Neon/GitHub + optional Sentry; fonts self-hosted | inspection |
| ARC-019 | Must | PASS |  | tests/integration/db/test_roles.py::test_group_and_login_roles; tests/integration/db/test_grants.py::test_app_privileges_are_exactly_section_4_8; tests/integration/test_schema_behaviour.py::test_ac_pgs_14_ground_truth_only_through_readonly |  | inspection |
| ARC-020 | Must | PASS |  | tests/integration/api/test_sessions.py::test_unknown_resident_is_rejected_and_stored | 422, row in ingest_rejections, raw_sessions count 0 | inspection |
| ARC-021 | Must | PASS |  | tests/integration/api/test_sessions.py::test_repeat_session_id_is_a_duplicate; tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed |  | inspection |
| ARC-022 | Must | PASS |  | tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed | status_after_processing returned synchronously | inspection |
| ARC-023 | Must | PASS |  | tests/integration/api/test_ingest.py::test_src05_upload | 202 and background processing | inspection |
| ARC-024 | Must | PASS |  | backend/api/residents.py, scores.py, alarms.py, analytics.py import no PipelineRunner (only pipeline.py, deps.py, ingestion) | Reads from persisted derived tables | inspection |
| ARC-025 | Must | PASS |  | tests/integration/api/test_sessions.py::test_failed_run_answers_pending | 201 pending, run failed, next run processes the record | inspection |
| ARC-030 | Must | PASS |  | tests/integration/test_schema_behaviour.py::test_ac_pgs_01_raw_sessions_update_fails_for_app; tests/integration/test_schema_behaviour.py::test_ac_pgs_02_raw_sessions_delete_and_truncate_fail_for_app |  | inspection |
| ARC-031 | Must | PASS |  | tests/validation/test_global_checks.py::test_vc_g11_raw_store_fidelity; tests/unit/backend/services/test_validation.py::test_text_is_kept_exactly |  | inspection |
| ARC-032 | Must | PASS |  | backend/services/pipeline_persistence.py:1; backend/services/review_service.py | Derived writes in pipeline_persistence; review service writes alert status/snooze and review data alerts only | inspection |
| ARC-033 | Must | PASS |  | tests/unit/backend/test_ground_truth_boundary.py::test_only_the_summary_reads_the_answer_key; .github/workflows/ci.yml:244 (image holds no tests/specs) | Answer key under tests/fixtures (source copy in specs/business-requirements per TRD 14); not readable by runtime | inspection |
| ARC-034 | Must | PASS |  | tests/integration/db/test_ground_truth_loader.py::test_refuses_outside_test_v0_1; tests/integration/test_schema_behaviour.py::test_ac_pgs_14_ground_truth_only_through_readonly; tests/unit/backend/test_db_inspection.py::test_ground_truth_is_not_referenced_by_the_pipeline_or_cli |  | inspection |
| ARC-035 | Must | PASS |  | tests/integration/api/test_analytics.py::test_production_profile; frontend/components/ReviewOutcomesTable/ReviewOutcomesTable.tsx |  | inspection |
| ARC-040 | Must | PASS |  | analytics/pipeline.py:211-270; backend/services/pipeline_runner.py:32; tests/unit/analytics/test_pipeline.py::test_src05_counts_and_sessions | Data alerts then aggregates last; single entry point for API, CLI, nightly | inspection |
| ARC-041 | Must | PASS |  | pyproject.toml:39; .github/workflows/ci.yml:78; tests/unit/backend/test_import_boundary.py::test_analytics_imports_are_allowed | No clock/random/file access found in analytics/ | inspection |
| ARC-042 | Must | PASS |  | tests/unit/analytics/test_pipeline.py::test_deterministic_and_order_independent; tests/validation/test_global_checks.py::test_vc_g12_determinism_and_rebuild |  | inspection |
| ARC-043 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_late_record_keeps_frozen_baselines; tests/unit/analytics/test_pipeline.py::test_late_arrival_leaves_r01_unchanged |  | inspection |
| ARC-044 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_reviews_and_snooze_survive_a_rerun |  | inspection |
| ARC-045 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_second_run_changes_nothing; backend/services/pipeline_persistence.py:1 |  | inspection |
| ARC-046 | Must | PASS |  | analytics/robust_stats.py:17-23; tests/unit/analytics/test_robust_stats.py::test_vectors |  | inspection |
| ARC-050 | Must | PASS |  | tests/unit/test_repository_layout.py::test_skeleton_files_kept |  | test |
| ARC-051 | Must | PASS |  | pyproject.toml:45 (layers contract); grep backend/api for session.execute/select: none |  | inspection |
| ARC-052 | Must | PASS |  | backend/services/{baseline,cusum,morning_adjustment,scoring,speaker_screen}.py (1-line docstring stubs) | No statistics in backend services; computation only in analytics/ | inspection |
| ARC-053 | Must | PASS |  | backend/services/pipeline_runner.py:238; tests/integration/test_cli_pipeline.py::test_set_config_then_rebuild | Fixed contract constant MIN_RECEIVED=10 in analytics/data_alerts.py:27 (contract §19) | inspection |
| ARC-054 | Must | PASS |  | tests/integration/api/test_ingest.py::test_mapped_header_is_accepted; tests/unit/backend/services/test_validation.py::test_name_mapping |  | inspection |
| ARC-055 | Must | PASS |  | frontend/lib/format.ts; frontend/tests/unit/format.test.ts | Formats with facility tz; CI runs in UTC. test:tz script exists but not wired in CI | inspection |
| ARC-056 | Must | PASS |  | tests/unit/backend/core/test_config.py::test_cfg_06_production_refuses_test_profile |  | test |
| ARC-057 | Must | PASS |  | tests/unit/backend/core/test_config.py::test_staging_requires_sslmode_but_local_does_not |  | test |
| ARC-060 | Must | PASS |  | tests/integration/api/test_pipeline.py::test_run_lifecycle_and_snapshot |  | inspection |
| ARC-061 | Must | PASS |  | render.yaml:77; backend/jobs/nightly_run.py; tests/integration/pipeline/test_nightly_run.py::test_one_run_per_local_night_across_dst | No APScheduler in backend | inspection |
| ARC-062 | Must | PASS |  | tests/unit/analytics/test_day_ledger.py::test_checked_in_gap_and_missed; backend/jobs/nightly_run.py | Ledger filled to as_of without records | inspection |
| ARC-063 | Must | PASS |  | tests/integration/db/test_advisory_locks.py::test_second_transaction_waits_for_the_first; tests/integration/pipeline/test_concurrent_ingest.py::test_concurrent_posts_of_one_session_id; tests/unit/backend/test_db_inspection.py::test_only_transaction_scoped_advisory_locks |  | inspection |
| ARC-064 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_a_failing_resident_is_rolled_back_alone |  | inspection |
| ARC-065 | Must | PASS |  | backend/services/pipeline_persistence.py:104 | load_inputs adds device sharers; no dedicated test found | inspection |
| ARC-066 | Should | PASS |  | tests/integration/test_cli_pipeline.py::test_run_pipeline_command |  | inspection |
| ARC-067 | Must | PASS |  | tests/unit/backend/test_db_inspection.py::test_no_api_route_creates_keys_or_writes_master_data |  | test |
| ARC-068 | Must | PASS |  | tests/integration/api/test_pipeline.py::test_as_of_precedence; tests/integration/api/test_http_middleware.py::test_meta_uses_the_latest_succeeded_run; tests/unit/backend/core/test_config.py::test_tst_038_production_refuses_pipeline_as_of |  | inspection |
| ARC-070 | Must | PASS |  | tests/integration/api/test_pipeline.py::test_admin_starts_a_manual_run | POST scope all by admin | inspection |
| ARC-071 | Must | PASS |  | tests/integration/test_cli_pipeline.py::test_rebuild_reproduces_identical_derived_tables |  | inspection |
| ARC-072 | Must | PASS |  | tests/validation/test_harness.py::test_tier_b_matches_the_answer_key | Tier B rebuilds into empty schema | inspection |
| ARC-073 | Must | PASS |  | tests/integration/api/test_pipeline.py::test_run_lifecycle_and_snapshot; tests/validation/test_global_checks.py::test_vc_g08_parameters |  | inspection |
| ARC-074 | Must | PASS |  | analytics/pipeline.py:222; analytics/epoch_detection.py (time_key); tests/unit/analytics/test_pipeline.py::test_deterministic_and_order_independent |  | inspection |
| ARC-080 | Must | PASS |  | .env.example; .env.development.example; .env.production.example; tests/unit/backend/core/test_env_templates.py::test_env_040_templates_match_trd21 |  | inspection |
| ARC-081 | Must | PASS |  | docker-compose.yml; .github/workflows/e2e.yml:52; docs/deployment.md:39 | Same images run locally (compose demo profile) | inspection |
| ARC-082 | Must | PASS |  | render.yaml:53 (preDeployCommand); backend/alembic/env.py:29 |  | inspection |
| ARC-083 | Must | PASS |  | tests/integration/api/test_health.py::test_tst_054_health_ok_with_database_up; tests/integration/api/test_health.py::test_tst_054_health_degraded_with_database_down |  | inspection |
| ARC-084 | Must | PENDING BLOCK 4 |  | render.yaml:47 (region ohio); docs/deployment.md:26 | Render region in Blueprint; Neon region is a dashboard setting | inspection |
| ARC-090 | Must | PASS |  | backend/Dockerfile:36; .github/workflows/ci.yml:230 (docker-build) |  | inspection |
| ARC-091 | Must | PASS |  | tests/integration/api/test_pipeline.py::test_stale_running_run_is_abandoned; backend/services/pipeline_runner.py:161 | No local-disk state found; stale runs recovered from DB | inspection |
| ARC-092 | Must | PASS |  | .github/workflows/ci.yml:84 (postgres:16-alpine); tests/unit/backend/test_db_inspection.py::test_migrations_never_manage_extensions_or_the_database |  | inspection |
| ARC-093 | Must | PASS |  | frontend/package.json (build: next build); netlify.toml:17 | Netlify plugin is build adapter only; no vendor runtime APIs in source | inspection |
| ARC-094 | Must | PASS |  | specs/TRD/01_System_Architecture_TRD.md:364; backend/core/config.py; tests/unit/test_render_blueprint.py::test_boundary_check_catches_application_code | Analysis: config by env only; demo run vs postgres:16 sslmode part not executed | inspection |
| ARC-095 | Must | PASS |  | tests/integration/api/test_sessions.py::test_logs_carry_no_feature_value_or_key; tests/unit/backend/core/test_logging.py::test_secret_keys_and_credentialed_urls_are_redacted |  | inspection |
| ARC-100 | Must | PASS |  | backend/core/middleware.py:92; tests/integration/api/test_http_middleware.py::test_request_id_is_echoed_or_generated; tests/integration/api/test_pipeline.py:102 |  | inspection |
| ARC-101 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_errors_carry_the_request_id_and_problem_shape; tests/unit/backend/core/test_errors.py::test_problem_body_shape |  | inspection |
| ARC-102 | Must | PASS |  | database/schema.sql (53 timestamptz, no timestamp without tz); analytics/morning_offset.py; tests/unit/analytics/test_morning_offset.py |  | inspection |
| ARC-103 | Must | PASS |  | tests/integration/db/test_audit_writer.py::test_every_action_inserts_exactly_one_row |  | inspection |
| ARC-104 | Must | PASS |  | .github/workflows/ci.yml:44; tests/security/test_static_scans.py::test_no_forbidden_dependencies |  | inspection |
| ARC-105 | Must | PASS |  | database/schema.sql:486, :701; database/seeds/test_v0_1/facilities.csv; tests/integration/test_cli_seed.py::test_bootstrap_is_idempotent |  | inspection |

### 02 Functional Requirements Specification

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| FR-001 | Must | PASS |  | tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed; tests/integration/api/test_sessions.py::test_only_an_ingest_key_may_post | 201 for ingest:write key; bearer 401, pipeline key 403 | inspection |
| FR-002 | Must | PASS |  | tests/integration/api/test_ingest.py::test_record_errors_do_not_fail_the_batch; backend/api/ingest.py:66 | JSON {records:[...]} accepted, source api_batch | inspection |
| FR-003 | Must | PASS |  | tests/integration/api/test_ingest.py::test_src05_upload; tests/unit/backend/services/test_validation.py::test_csv_header_errors; tests/integration/api/test_ingest.py::test_legacy_file_is_refused | 30-field header any order (reversed) accepted; others CSV_HEADER_MISMATCH | inspection |
| FR-004 | Must | PASS |  | tests/integration/api/test_ingest.py::test_batch_detail_and_roles; tests/integration/api/test_ingest.py::test_record_errors_do_not_fail_the_batch | admin JWT and ingest key accepted; clinician 403 | inspection |
| FR-005 | Must | PASS |  | tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed; tests/integration/db/test_raw_store.py::test_same_session_id_twice_gets_increasing_arrival_seq; tests/integration/api/test_ingest.py::test_src05_upload | payload stored as received, repeats get new rows/arrival_seq | inspection |
| FR-006 | Must | PASS |  | tests/integration/test_schema_behaviour.py::test_ac_pgs_01_raw_sessions_update_fails_for_app; ::test_ac_pgs_02_raw_sessions_delete_and_truncate_fail_for_app; tests/unit/backend/repositories/test_raw_session_repository.py::test_repository_has_no_update_or_delete | UPDATE/DELETE/TRUNCATE refused for app and owner; repository has no update/delete | inspection |
| FR-007 | Must | PASS |  | tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed; tests/integration/api/test_sessions.py::test_failed_run_answers_pending | 201 with raw_session_id, arrival_seq, status; pending when run fails, next run processes | inspection |
| FR-008 | Must | PASS |  | tests/integration/api/test_sessions.py::test_repeat_session_id_is_a_duplicate | 200 with status duplicate | inspection |
| FR-009 | Must | PASS |  | tests/integration/api/test_ingest.py::test_src05_upload | 202 with ingest_batch_id, accepted, rejected, duplicates | inspection |
| FR-010 | Must | PASS |  | tests/integration/db/test_raw_store.py::test_rejection_and_batch_checks; tests/integration/db/test_repositories.py::test_ingest_batches_and_rejections |  | test |
| FR-011 | Must | PASS |  | tests/integration/api/test_ingest.py::test_record_errors_do_not_fail_the_batch; tests/integration/api/test_ingest.py::test_src05_upload | per-record reject; stored arrival order equals file order | inspection |
| FR-012 | Must | PASS |  | tests/unit/backend/services/test_validation.py::test_name_mapping; tests/integration/api/test_ingest.py::test_mapped_header_is_accepted | feature_name_map in config_parameters; renamed header accepted without code change | inspection |
| FR-013 | Must | PASS |  | tests/integration/api/test_sessions.py::test_extra_field_and_audio_are_refused; tests/integration/api/test_ingest.py::test_answer_key_columns_are_refused | extra field -> extra_forbidden 422; nothing stored | inspection |
| FR-014 | Must | PASS |  | tests/integration/api/test_rate_limits.py::test_ingest_limit_is_per_api_key | 600/minute default asserted; 429 per key on both ingest routes | inspection |
| FR-015 | Must | PASS |  | tests/contract/test_openapi_contract.py::test_no_audio_or_identity_properties; tests/integration/api/test_sessions.py::test_extra_field_and_audio_are_refused; tests/security/test_no_audio.py::test_audio_is_refused_everywhere |  | test |
| FR-020 | Must | PASS |  | tests/unit/backend/services/test_validation.py::test_schema_versions; tests/integration/api/test_sessions.py::test_version_and_timestamp_problems | 0.2 -> UNSUPPORTED_SCHEMA_VERSION | inspection |
| FR-021 | Must | PASS |  | tests/unit/backend/services/test_validation.py::test_a_missing_field_is_reported; backend/services/validation.py:36 | missing field rejected; phrase_id in required set | inspection |
| FR-022 | Must | PASS |  | tests/unit/backend/services/test_validation.py::test_timestamp_formats; tests/integration/api/test_sessions.py::test_version_and_timestamp_problems | ISO/fractional/offset/invalid dates rejected invalid_format | inspection |
| FR-023 | Must | PASS |  | tests/unit/backend/services/test_validation.py::test_json_numbers_and_csv_cells; tests/unit/backend/services/test_validation.py::test_csv_whole_numbers; tests/unit/backend/services/test_validation.py::test_reject_rules | NaN/inf non_finite; pauses -1 out_of_range, 1.5 not_integer | inspection |
| FR-024 | Must | PASS |  | tests/unit/backend/services/test_validation.py::test_reject_rules | 'OK' -> invalid_enum; integration 'bad' rejected | inspection |
| FR-025 | Must | PASS |  | tests/unit/backend/services/test_validation.py::test_roster_checks_and_request_codes; tests/integration/api/test_sessions.py::test_unknown_resident_is_rejected_and_stored | UNKNOWN_RESIDENT / UNKNOWN_DEVICE | inspection |
| FR-026 | Must | PASS |  | tests/integration/api/test_sessions.py::test_withdrawn_resident | 422 RESIDENT_WITHDRAWN detail 'resident withdrawn' | inspection |
| FR-027 | Must | PASS |  | tests/unit/backend/core/test_errors.py::test_validation_locations_drop_the_body_segment |  | test |
| FR-028 | Must | PASS |  | tests/integration/db/test_raw_store.py::test_rejection_and_batch_checks; tests/integration/db/test_repositories.py::test_ingest_batches_and_rejections; tests/unit/backend/schemas/test_json_columns.py::test_ingest_errors_must_be_a_non_empty_list |  | test |
| FR-029 | Must | PASS |  | tests/unit/analytics/test_duplicate_detection.py::test_first_arrival_wins_in_arrival_order; analytics/duplicate_detection.py:13 | first arrival wins; reason 'session_id already received' | inspection |
| FR-030 | Must | PASS |  | tests/unit/analytics/test_quality_screening.py::test_duplicates_pass_through_ungated; tests/unit/analytics/test_pipeline.py::test_dropping_duplicates_changes_nothing_else; analytics/day_ledger.py:66 | duplicates skip gate/screen/baseline/scores/ledger | inspection |
| FR-031 | Must | PASS |  | tests/unit/analytics/test_pipeline.py::test_dropping_duplicates_changes_nothing_else; tests/validation/test_invariance.py::test_vc_r04_inv_identical_without_the_copies; tests/validation/test_r04_duplicate_records.py::test_vc_r04_duplicate_records |  | test |
| FR-032 | Must | PASS |  | tests/integration/api/test_ingest.py::test_legacy_file_is_refused |  | test |
| FR-040 | Must | PASS |  | tests/unit/analytics/test_quality_screening.py::test_thresholds_are_strict; analytics/quality_screening.py:14 | 'quality flag poor' | inspection |
| FR-041 | Must | PASS |  | tests/unit/analytics/test_quality_screening.py::test_thresholds_are_strict | -40.0 passes, -39.9 'noise above limit' | inspection |
| FR-042 | Must | PASS |  | tests/unit/analytics/test_quality_screening.py::test_thresholds_are_strict | 1.0 passes, 0.99 'speech too short' | inspection |
| FR-043 | Must | PASS |  | tests/unit/analytics/test_quality_screening.py::test_all_reasons_in_fixed_order | joined by '; ' in fixed order | inspection |
| FR-044 | Must | PASS |  | tests/unit/analytics/test_baseline_builder.py::test_freeze_points_skip_non_usable_records; tests/unit/analytics/test_composite_score.py::test_src05_scored_sessions; tests/validation/test_r03_set_aside_sessions.py | only usable rows scored/in baseline; R03 answer-key check | inspection |
| FR-050 | Must | PASS |  | tests/unit/analytics/test_epoch_detection.py::test_device_firmware_and_software_changes; ::test_set_aside_record_starts_an_epoch; ::test_time_order_and_duplicates | epoch key change starts new epoch, incl. set-aside | inspection |
| FR-051 | Must | PASS |  | backend/models/epoch.py:54-67; tests/unit/analytics/test_epoch_detection.py::test_src05_r07_epochs; tests/integration/pipeline/test_runner_persistence.py::test_full_run_on_src05 | epochs persisted (11 rows) with device/fw/sw/start/end | inspection |
| FR-052 | Must | PASS |  | tests/unit/analytics/test_baseline_builder.py::test_membership_and_forming_epochs; tests/validation/test_r07_device_move.py::test_vc_r07_device_move | R07 epoch 2 baseline counted from zero | inspection |
| FR-053 | Must | PASS |  | backend/services/pipeline_persistence.py:356-371; tests/unit/analytics/test_alert_generator.py::test_one_event_per_ringing_epoch_with_closure_facts; tests/unit/analytics/test_cusum_engine.py::test_epochs_have_their_own_tally | 'epoch ended' closure; tally per epoch from 0 | inspection |
| FR-060 | Must | PASS |  | tests/unit/analytics/test_speaker_screen.py::test_src05_r05_quarantines_use_the_first_n; analytics/speaker_screen.py:3-8 | raw values vs first up to N prior usable | inspection |
| FR-061 | Must | PASS |  | tests/unit/analytics/test_speaker_screen.py::test_no_screen_below_screen_min_n | <5 prior usable -> usable | inspection |
| FR-062 | Must | PASS |  | tests/unit/analytics/test_speaker_screen.py::test_quarantine_needs_f0_and_two_composite_features | F0 only -> usable; F0 + 2 composites -> quarantined | inspection |
| FR-063 | Must | PASS |  | tests/unit/analytics/test_speaker_screen.py::test_src05_r05_quarantines_use_the_first_n | exact reason strings with 2dp z and count | inspection |
| FR-064 | Must | PASS |  | tests/unit/analytics/test_speaker_screen.py::test_src05_r05_quarantines_use_the_first_n; tests/validation/test_r05_possible_other_speaker.py::test_vc_r05_possible_other_speaker | R05 day 8 (pre-freeze) and day 22 (post-freeze) quarantined | inspection |
| FR-065 | Must | PASS |  | tests/unit/analytics/test_speaker_screen.py::test_quarantine_needs_f0_and_two_composite_features; tests/unit/analytics/test_composite_score.py::test_src05_scored_sessions | quarantined not joining reference; scores only usable | inspection |
| FR-070 | Must | PASS |  | tests/unit/analytics/test_morning_offset.py::test_local_time_vectors | zoneinfo America/Chicago incl. DST; local date/time | inspection |
| FR-071 | Must | PASS |  | tests/unit/analytics/test_morning_offset.py::test_local_time_vectors | 11:59:59 morning, 12:00 not | inspection |
| FR-072 | Must | PASS |  | tests/unit/analytics/test_morning_offset.py::test_r06_day_1_adjustment; ::test_afternoon_and_stored_features_unchanged | morning raw-offset; afternoon unchanged | inspection |
| FR-073 | Must | PASS |  | analytics/morning_offset.py:1-6; tests/unit/analytics/test_config.py::test_profiles_differ_only_in_profile_and_baseline_n; tests/validation/test_invariance.py::test_vc_r06_mut_missing_adjustment_is_detected | offsets from config only, nothing estimated | inspection |
| FR-074 | Must | PASS |  | analytics/baseline_builder.py:6; analytics/speaker_screen.py:3; tests/validation/test_r06_morning_effect.py::test_vc_r06_morning_effect | baseline adjusted, screen raw; R06 answer key | inspection |
| FR-080 | Must | PASS |  | tests/unit/analytics/test_baseline_builder.py::test_freeze_points_skip_non_usable_records; tests/unit/analytics/test_config.py::test_profiles_differ_only_in_profile_and_baseline_n | first N usable; 16 test / 30 production | inspection |
| FR-081 | Must | PASS |  | tests/unit/analytics/test_baseline_builder.py::test_r09_worked_example; ::test_pause_floor_rows | median, MAD, spread x1.4826, pause floor 0.5 | inspection |
| FR-082 | Must | PASS |  | tests/unit/analytics/test_baseline_builder.py::test_r09_worked_example | composite median/MAD/spread | inspection |
| FR-083 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_late_record_keeps_frozen_baselines; tests/unit/analytics/test_pipeline.py::test_frozen_baselines_win_and_mismatch_warns | frozen baselines unchanged | inspection |
| FR-084 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_late_record_keeps_frozen_baselines | late_arrival warning on run; baseline unchanged | inspection |
| FR-085 | Must | PASS |  | tests/integration/api/test_residents.py::test_overview; tests/unit/analytics/test_baseline_builder.py::test_membership_and_forming_epochs | R02 baseline_forming 13 of 16, no scores, not error | inspection |
| FR-086 | Must | PASS |  | backend/models/baseline.py:62-69; tests/unit/analytics/test_baseline_builder.py::test_freeze_points_skip_non_usable_records | n_sessions, first/frozen_after session ids, frozen_at | inspection |
| FR-090 | Must | PASS |  | tests/unit/analytics/test_composite_score.py::test_src05_scored_sessions | 98 scored usable post-freeze sessions | inspection |
| FR-091 | Must | PASS |  | tests/unit/analytics/test_zscore_calculator.py::test_r09_ringing_session_z | R09 worked example | inspection |
| FR-092 | Must | PASS |  | tests/unit/analytics/test_composite_score.py::test_r09_composite | composite_raw 2.325508 | inspection |
| FR-093 | Must | PASS |  | tests/unit/analytics/test_composite_score.py::test_r09_composite | composite_z 4.288307 | inspection |
| FR-094 | Must | PASS |  | backend/models/score.py:67-73; tests/integration/pipeline/test_runner_persistence.py::test_full_run_on_src05 | z, composite_raw/z, tally, alarm_state, local_date, is_morning | inspection |
| FR-095 | Must | PASS |  | tests/unit/analytics/test_morning_offset.py::test_afternoon_and_stored_features_unchanged; tests/unit/analytics/test_feature_specs.py::test_features_equal_trd_23 | 12 features stored, composite uses 7 only | inspection |
| FR-100 | Must | PASS |  | tests/unit/analytics/test_cusum_engine.py::test_tally_and_states | S=max(0,S+z-0.5) | inspection |
| FR-101 | Must | PASS |  | tests/validation/test_r02_missing_days.py::test_vc_r02_missing_days; tests/validation/test_r03_set_aside_sessions.py::test_vc_r03_set_aside_sessions | tally only over scored rows; answer key | inspection |
| FR-102 | Must | PASS |  | tests/unit/analytics/test_cusum_engine.py::test_tally_and_states; ::test_src05_alarms | rings at first >=5, then on | inspection |
| FR-103 | Must | PASS |  | tests/unit/analytics/test_cusum_engine.py::test_tally_and_states | off before crossing | inspection |
| FR-104 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_full_run_on_src05; tests/integration/pipeline/test_runner_persistence.py::test_second_run_changes_nothing | one open alert each R09, R10; rerun no new rows | inspection |
| FR-105 | Must | PASS |  | backend/models/score.py:84-110; tests/integration/db/test_repositories.py (upsert_cusum_state) | one row per epoch: current_tally, last_scored_session_id, alarm_on | inspection |
| FR-106 | Must | PASS |  | tests/integration/api/test_alerts.py::test_reviews; tests/integration/api/test_alerts.py::test_refusals | review sets acknowledged/acknowledged_by; /acknowledge 404/405 | inspection |
| FR-107 | Must | PASS |  | tests/integration/api/test_alerts.py::test_reviews; tests/integration/api/test_alerts.py::test_snooze | scores/cusum_state snapshot unchanged | inspection |
| FR-108 | Must | PASS |  | tests/integration/api/test_alerts.py::test_alert_list | status and resident_code filters | inspection |
| FR-109 | Must | PASS |  | tests/integration/api/test_alerts.py::test_alert_list; tests/unit/backend/test_no_outbound_alerts.py::test_no_messaging_client |  | test |
| FR-110 | Must | PASS |  | backend/services/pipeline_persistence.py:349-371; backend/api/alarms.py:48-130 | only pipeline closes (epoch ended/superseded); no close endpoint. superseded path not tested | inspection |
| FR-120 | Must | PASS |  | tests/unit/analytics/test_day_ledger.py::test_checked_in_gap_and_missed; ::test_src05_ledger; analytics/day_ledger.py:71-74 | enrolment to as-of/withdrawn_on inclusive; 300 rows | inspection |
| FR-121 | Must | PASS |  | tests/unit/analytics/test_day_ledger.py::test_checked_in_gap_and_missed | set-aside record counts as checked_in | inspection |
| FR-122 | Must | PASS |  | tests/unit/analytics/test_day_ledger.py::test_checked_in_gap_and_missed; ::test_src05_ledger | shared-device gap reason string; R02/R03 Oct 12 | inspection |
| FR-123 | Must | PASS |  | tests/unit/analytics/test_day_ledger.py::test_checked_in_gap_and_missed; analytics/day_ledger.py:24 | 'no record received' | inspection |
| FR-124 | Must | PASS |  | tests/unit/analytics/test_pipeline.py::test_src05_counts_and_sessions; tests/validation/test_r02_missing_days.py::test_vc_r02_missing_days | missing days create no session/score/tally | inspection |
| FR-125 | Must | PASS |  | analytics/day_ledger.py:71-74; tests/unit/analytics/test_day_ledger.py::test_checked_in_gap_and_missed | ledger runs to as-of date regardless of records | inspection |
| FR-130 | Must | PASS |  | tests/integration/api/test_residents.py::test_filters_and_paging |  | test |
| FR-131 | Must | PASS |  | tests/integration/api/test_residents.py::test_overview |  | test |
| FR-132 | Must | PASS |  | tests/integration/api/test_residents.py::test_overview |  | test |
| FR-133 | Must | PASS |  | tests/integration/api/test_residents.py::test_overview; frontend/components/FilterButtons/FilterButtons.test.tsx; frontend/tests/pages/residents.test.tsx (filters ?show=) | sort=alarm order, summary counts, Learning only when >=1, ?show= | inspection |
| FR-134 | Must | PASS |  | frontend/components/ResidentsTable/ResidentsTable.test.tsx (FE-182); frontend/components/ChartBanner/ChartBanner.test.tsx | 4 columns; device in banner with shared/replaced suffix | inspection |
| FR-135 | Must | PASS |  | tests/integration/db/test_read_models.py::test_activity_counts_exclude_duplicates_and_count_missed |  | test |
| FR-136 |  | NOT APPLICABLE |  | specs/TRD/02_Functional_Requirements_Specification.md:192 | Retired by TRD 24 D-110 (wireframe v0.2) | inspection |
| FR-137 | Must | PASS |  | tests/integration/api/test_ui_fixture_ds07.py::test_resident_list |  | test |
| FR-138 | Must | PASS |  | frontend/components/DataBar/DataBar.test.tsx; frontend/tests/pages/protected-layout.test.tsx | test_v0_1 and other-profile data bar texts | inspection |
| FR-139 |  | NOT APPLICABLE |  | specs/TRD/02_Functional_Requirements_Specification.md:195 | Retired by TRD 24 D-110 (wireframe v0.2) | inspection |
| FR-140 | Must | PASS |  | frontend/components/ResidentsTable/ResidentsTable.test.tsx (UX-037/UX-040); frontend/tests/pages/residents.test.tsx (opens chart on row click) | 'Open chart for <R>' link and row click | inspection |
| FR-150 | Must | PASS |  | tests/integration/api/test_devices.py::test_device_panel |  | test |
| FR-151 | Must | PASS |  | tests/integration/api/test_devices.py::test_device_panel |  | test |
| FR-152 | Must | PASS |  | tests/integration/api/test_devices.py::test_device_panel |  | test |
| FR-153 | Must | PASS |  | tests/integration/api/test_devices.py::test_device_panel |  | test |
| FR-154 | Should | PASS |  | tests/integration/api/test_devices.py::test_device_panel; tests/integration/db/test_read_models.py::test_device_silent_and_gap_days |  | test |
| FR-155 | Must | PASS |  | tests/integration/api/test_devices.py::test_device_panel |  | test |
| FR-156 | Must | PASS |  | frontend/components/DevicesSection/DevicesSection.test.tsx | grouped row 'D01, D04 to D06, D08 to D10: all uploaded Oct 30. Firmware fw-1.0.0.' | inspection |
| FR-160 | Must | PASS |  | frontend/components/BackLink/BackLink.test.tsx; frontend/tests/pages/resident-layout.test.tsx | '← Resident list' keeps ?show= | inspection |
| FR-161 | Must | PASS |  | frontend/components/ChartBanner/ChartBanner.test.tsx; frontend/components/ChartSectionNav/ChartSectionNav.test.tsx | banner facts, pill, 6 section links | inspection |
| FR-162 | Must | PASS |  | frontend/components/BaselinePanel/BaselinePanel.test.tsx | frozen text incl. restart prefix (R07) | inspection |
| FR-163 | Must | PASS |  | frontend/components/BaselinePanel/BaselinePanel.test.tsx; frontend/tests/unit/wording-chart.test.ts | 'Still forming: n of N...' + progressbar | inspection |
| FR-164 | Must | PASS |  | frontend/components/SummaryPanel/SummaryPanel.test.tsx; frontend/lib/wording/chart.ts:100 | Right now panel, note and PI marker from wording config | inspection |
| FR-165 | Must | PASS |  | frontend/components/ChangeScoreChart/ChangeScoreChart.test.tsx | bars by alarm_state, baseline slot, 'Alarm line: 5', x labels | inspection |
| FR-166 | Must | PASS |  | frontend/components/ChangeScoreChart/ChangeScoreChart.test.tsx | alarm-marker and 'Oct 21 · alarm' tick | inspection |
| FR-167 | Must | PASS |  | frontend/tests/pages/resident-trends.test.tsx; frontend/tests/unit/wording-trends.test.ts | exact panel line | inspection |
| FR-168 | Must | PASS |  | frontend/components/ChangeScoreChart/ChangeScoreChart.test.tsx (UX-090) | 'Show change score as a table' disclosure | inspection |
| FR-169 | Must | PASS |  | frontend/components/MeasurementCards/MeasurementCards.test.tsx | heading, 7 labelled cards with sparklines | inspection |
| FR-170 | Must | PASS |  | frontend/components/OtherMeasurementsCard/OtherMeasurementsCard.test.tsx | '12 other measurements ...' 'Stored, not scored' | inspection |
| FR-171 | Must | PASS |  | frontend/components/MeasurementCards/MeasurementCards.test.tsx; frontend/tests/unit/wording-trends.test.ts | exact caption | inspection |
| FR-172 | Should | PASS |  | frontend/tests/pages/resident-trends.test.tsx (R07 loads epoch 1); backend/api/scores.py:62 | 'Device period' select queries scores?epoch= | inspection |
| FR-173 | Must | PASS |  | tests/integration/api/test_residents.py::test_unknown_resident_is_404 |  | test |
| FR-180 | Must | PASS |  | frontend/tests/pages/resident-log.test.tsx; frontend/components/CheckinLog/CheckinLog.test.tsx | counts + events newest first with dates | inspection |
| FR-181 | Must | PASS |  | frontend/components/CheckinLog/CheckinLog.test.tsx; tests/integration/api/test_residents.py::test_checkin_log | all listed event types incl. checkins_started | inspection |
| FR-182 | Must | PASS |  | tests/integration/api/test_residents.py::test_checkin_log |  | test |
| FR-183 | Should | PASS |  | tests/integration/api/test_residents.py::test_checkin_log_filters | from/to filter | inspection |
| FR-184 | Must | PASS |  | frontend/tests/e2e/isolated.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| FR-190 | Must | PASS |  | tests/integration/api/test_notes.py::test_create_note |  | test |
| FR-191 | Must | PASS |  | tests/integration/api/test_notes.py::test_create_note |  | test |
| FR-192 | Must | PASS |  | tests/integration/api/test_notes.py::test_superseding_and_listing |  | test |
| FR-193 | Must | PASS |  | tests/integration/api/test_notes.py::test_superseding_and_listing |  | test |
| FR-194 | Must | PASS |  | frontend/components/AlarmReviewPanel/AlarmReviewPanel.test.tsx; frontend/components/StaffNotes/StaffNotes.test.tsx; frontend/tests/pages/resident-review.test.tsx | researcher: no forms/buttons, reviews and notes visible | inspection |
| FR-195 |  | NOT APPLICABLE |  | specs/TRD/02_Functional_Requirements_Specification.md:248 | Retired by TRD 24 D-110 (wireframe v0.2) | inspection |
| FR-200 | Must | PASS |  | frontend/components/ExperimentalBanner/ExperimentalBanner.test.tsx; frontend/tests/pages/admissions.test.tsx | exact note | inspection |
| FR-201 | Must | PASS |  | tests/integration/api/test_admissions.py::test_range_not_available |  | test |
| FR-202 | Must | PASS |  | tests/integration/api/test_admissions.py::test_range_not_available; tests/integration/api/test_admissions.py::test_comparison_with_ranges |  | test |
| FR-203 | Must | PASS |  | frontend/components/FacilityRangeChart/FacilityRangeChart.test.tsx; frontend/components/AdmissionsTable/AdmissionsTable.test.tsx | 'Show comparison' and grey band caption | inspection |
| FR-204 | Must | PASS |  | tests/integration/api/test_admissions.py::test_comparison_with_ranges |  | test |
| FR-205 | Must | PASS |  | backend/services/pipeline_persistence.py:433-446; tests/integration/db/test_repositories.py (set_cohort_longitudinal) | cohort -> longitudinal when own baseline frozen | inspection |
| FR-206 | Must | PASS |  | tests/integration/api/test_admissions.py::test_range_not_available |  | test |
| FR-207 |  | NOT APPLICABLE |  | specs/TRD/02_Functional_Requirements_Specification.md:261 | Retired by TRD 24 D-110 (wireframe v0.2) | inspection |
| FR-210 | Must | PASS |  | tests/integration/api/test_auth.py::test_valid_login_returns_a_bearer_token; frontend/tests/pages/login.test.tsx | JWT exp-iat 3600 | inspection |
| FR-211 | Must | PASS |  | frontend/tests/pages/protected-layout.test.tsx (FE-055, FE-056) | no token -> /login?next=; 401 -> /login?reason=expired | inspection |
| FR-212 | Must | PASS |  | tests/integration/test_auth_coverage.py::test_every_route_has_its_auth_dependency; tests/security/test_auth_matrix.py::test_every_cell |  | test |
| FR-213 | Must | PASS |  | tests/integration/api/test_role_checks.py::test_permissions_equal_the_trd_matrix; tests/security/test_auth_matrix.py::test_every_cell |  | test |
| FR-214 | Must | PASS |  | tests/integration/api/test_auth.py::test_failed_logins_are_indistinguishable | inactive user login 401 | inspection |
| FR-215 | Must | PASS |  | tests/integration/api/test_rate_limits.py::test_sixth_login_in_a_minute_is_rate_limited |  | test |
| FR-216 | Must | PASS |  | tests/integration/api/test_auth.py::test_me_and_logout | email, display_name, role | inspection |
| FR-217 | Must | PASS |  | tests/integration/api/test_auth.py::test_me_and_logout; frontend/components/AppHeader/AppHeader.test.tsx (FE-058) | 204 + auth.logout audit; token discarded; no revocation | inspection |
| FR-218 | Must | PASS |  | frontend/components/AppHeader/AppHeader.test.tsx (FE-028) | clinician: no Study team/Admin; admin: both | inspection |
| FR-220 | Must | PASS |  | tests/integration/api/test_users.py::test_create_user |  | test |
| FR-221 | Must | PASS |  | tests/integration/api/test_users.py::test_update_user; tests/integration/api/test_users.py::test_list_and_access |  | test |
| FR-222 | Must | PASS |  | frontend/tests/pages/admin.test.tsx (UX-213, UX-217) | upload shows accepted/rejected rows/duplicates | inspection |
| FR-223 | Must | PASS |  | tests/integration/api/test_pipeline.py::test_admin_starts_a_manual_run |  | test |
| FR-224 | Must | PASS |  | tests/integration/api/test_pipeline.py::test_get_run |  | test |
| FR-225 | Must | PASS |  | tests/integration/api/test_pipeline.py::test_list_runs |  | test |
| FR-226 | Must | PASS |  | tests/integration/test_cli_credentials.py::test_create_api_key_prints_the_key_once_and_stores_its_hash |  | test |
| FR-227 | Must | PASS |  | tests/unit/backend/test_db_inspection.py::test_no_api_route_creates_keys_or_writes_master_data |  | test |
| FR-228 | Must | PASS |  | tests/integration/test_cli_seed.py::test_withdraw_resident; tests/integration/api/test_sessions.py::test_withdrawn_resident; tests/integration/api/test_residents.py::test_filters_and_paging | withdraw CLI; ingest refused; hidden by default | inspection |
| FR-229 | Must | PASS |  | tests/integration/test_cli_pipeline.py::test_set_config_then_rebuild; backend/cli.py:733 | validates, audits config.changed old/new/reason, rebuild notice | inspection |
| FR-230 | Must | PASS |  | tests/integration/api/test_pipeline.py::test_production_refuses_other_profiles |  | test |
| FR-240 | Must | PASS |  | tests/integration/api/test_analytics.py::test_summary |  | test |
| FR-241 | Must | PASS |  | tests/integration/api/test_scores.py::test_baselines |  | test |
| FR-242 | Must | PASS |  | tests/integration/api/test_scores.py::test_scores_json |  | test |
| FR-243 | Must | PASS |  | tests/integration/api/test_analytics.py::test_summary |  | test |
| FR-244 | Must | PASS |  | tests/integration/api/test_scores.py::test_scores_csv |  | test |
| FR-245 | Must | PASS |  | tests/security/test_data_minimisation.py::test_csv_exports_hold_no_note_text |  | test |
| FR-250 | Must | PASS |  | backend/services/audit_service.py:30-55; tests/integration/api/test_auth.py; tests/integration/api/test_ingest.py::test_batch_is_audited_with_the_request_id; tests/integration/api/test_alerts.py::test_reviews | all listed actions in vocabulary and tested | inspection |
| FR-251 | Must | PASS |  | backend/models/audit_log.py:51-64; tests/unit/backend/services/test_audit.py::test_forbidden_details_raise_and_write_nothing | columns present; forbidden keys refused | inspection |
| FR-252 | Must | PASS |  | tests/integration/test_schema_behaviour.py::test_ac_pgs_03_audit_logs_are_append_only_for_app; tests/unit/backend/test_db_inspection.py::test_audit_writes_only_through_the_audit_modules |  | test |
| FR-253 | Must | PASS |  | tests/integration/api/test_health.py::test_tst_054_health_ok_with_database_up; tests/integration/api/test_health.py::test_tst_054_health_degraded_with_database_down |  | test |
| FR-254 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_errors_carry_the_request_id_and_problem_shape |  | test |
| FR-260 |  | NOT APPLICABLE |  | specs/TRD/02_Functional_Requirements_Specification.md:318 | Retired by TRD 24 D-110 (wireframe v0.2) | inspection |
| FR-261 |  | NOT APPLICABLE |  | specs/TRD/02_Functional_Requirements_Specification.md:319 | Retired by TRD 24 D-110 (wireframe v0.2) | inspection |
| FR-262 | Must | PASS |  | frontend/components/SummaryPanel/SummaryPanel.test.tsx; frontend/components/MoreDetailTiles/MoreDetailTiles.test.tsx | Alarm started, days Open, review status, Change score 26.8 | inspection |
| FR-263 | Must | PASS |  | tests/integration/api/test_ui_fixture_ds07.py::test_open_alarms_and_leaning_most |  | test |
| FR-264 | Must | PASS |  | frontend/components/AlarmReviewPanel/AlarmReviewPanel.test.tsx; frontend/components/SummaryPanel/SummaryPanel.test.tsx | panel heading; Review this alert / See what changed links | inspection |
| FR-265 |  | NOT APPLICABLE |  | specs/TRD/02_Functional_Requirements_Specification.md:323 | Retired by TRD 24 D-110 (wireframe v0.2) | inspection |
| FR-266 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_alerts_endpoint_leaning_most; tests/unit/analytics/test_alert_generator.py::test_leaning_most_rules; frontend/components/LeaningMost/LeaningMost.test.tsx | R09 'more pauses, quieter, less voiced sound'; none text; tie order | inspection |
| FR-267 | Must | PASS |  | frontend/components/AlertReviewForm/AlertReviewForm.test.tsx | 5 configured options in order | inspection |
| FR-268 | Must | PASS |  | frontend/components/AlertReviewForm/AlertReviewForm.test.tsx | 4 outcomes, exactly one required | inspection |
| FR-269 | Must | PASS |  | frontend/components/AlertReviewForm/AlertReviewForm.test.tsx; tests/integration/api/test_alerts.py::test_invalid_reviews_write_nothing | note counter 0/2000; 2001 -> 422 | inspection |
| FR-270 | Must | PASS |  | tests/integration/api/test_alerts.py::test_reviews; frontend/components/AlertReviewForm/AlertReviewForm.test.tsx | POST reviews creates alert_reviews row, alert acknowledged, reviewed true | inspection |
| FR-271 | Must | PASS |  | tests/integration/api/test_alerts.py::test_invalid_reviews_write_nothing |  | test |
| FR-272 | Must | PASS |  | tests/integration/api/test_alerts.py::test_reviews; frontend/components/AlarmReviewPanel/AlarmReviewPanel.test.tsx | multiple reviews listed newest first | inspection |
| FR-273 | Must | PASS |  | tests/integration/api/test_alerts.py::test_data_problem_review_creates_then_links |  | test |
| FR-274 | Must | PASS |  | tests/integration/api/test_alerts.py::test_snooze; frontend/components/AlertReviewForm/AlertReviewForm.test.tsx | default 24h, snoozed_by, 'Reminder set for ...', status unchanged | inspection |
| FR-275 | Must | PASS |  | tests/integration/api/test_alerts.py::test_refusals |  | test |
| FR-276 | Must | PASS |  | tests/unit/backend/test_no_outbound_alerts.py; backend/jobs/nightly_run.py | no deadline/escalation code; inspection | inspection |
| FR-277 | Must | PASS |  | frontend/components/AlarmReviewPanel/AlarmReviewPanel.test.tsx | exact open-questions text | inspection |
| FR-278 |  | NOT APPLICABLE |  | specs/TRD/02_Functional_Requirements_Specification.md:336 | Retired by TRD 24 D-110 (wireframe v0.2) | inspection |
| FR-279 | Must | PASS |  | tests/integration/api/test_alerts.py::test_reviews; tests/integration/api/test_alerts.py::test_snooze | alert.reviewed and alert.snoozed audit rows | inspection |
| FR-280 | Must | PASS |  | frontend/tests/pages/resident-review.test.tsx (R01 only Staff notes); frontend/components/AppHeader/AppHeader.test.tsx | no review panel; no badge when count 0 | inspection |
| FR-290 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_full_run_on_src05; tests/unit/analytics/test_config.py::test_profiles_differ_only_in_profile_and_baseline_n | recomputed per run; thresholds from config, same in both profiles | inspection |
| FR-291 | Must | PASS |  | tests/unit/analytics/test_data_alerts.py::test_src05_exactly_four_alerts_in_order; analytics/data_alerts.py:84-93 | R08 title/detail exact | inspection |
| FR-292 | Must | PASS |  | tests/unit/analytics/test_data_alerts.py::test_src05_exactly_four_alerts_in_order; analytics/data_alerts.py:95-103 | R05 title/detail; singular form in code | inspection |
| FR-293 | Must | PASS |  | tests/unit/analytics/test_data_alerts.py::test_src05_exactly_four_alerts_in_order; analytics/data_alerts.py:104-115 | R03 7 of 29, reason order | inspection |
| FR-294 | Must | PASS |  | tests/unit/analytics/test_data_alerts.py::test_src05_exactly_four_alerts_in_order; ::test_single_resident_device_needs_a_run; analytics/data_alerts.py:156-160 | shared-device and 2-day single rule; both title forms | inspection |
| FR-295 | Must | PASS |  | analytics/data_alerts.py:106; tests/unit/analytics/test_data_alerts.py::test_src05_exactly_four_alerts_in_order | one per kind; stalled excludes high_set_aside | inspection |
| FR-296 | Must | PASS |  | backend/services/pipeline_persistence.py:388-401; tests/integration/pipeline/test_runner_persistence.py::test_a_run_at_an_earlier_as_of_keeps_alert_history | first_detected kept, last moves, resolved when gone (resolve path untested) | inspection |
| FR-297 | Must | PASS |  | tests/integration/test_resolve_data_alert.py::test_resolves_a_review_flagged_data_problem |  | test |
| FR-298 | Must | PASS |  | frontend/tests/pages/study.test.tsx (UX-306..UX-308); frontend/components/DataProblemsList/DataProblemsList.test.tsx | list with Staff can help / Study team tags | inspection |
| FR-299 | Must | PASS |  | tests/integration/api/test_alerts.py::test_data_alert_list |  | test |
| FR-300 | Must | PASS |  | tests/integration/api/test_alerts.py::test_data_alert_list; tests/integration/pipeline/test_runner_persistence.py::test_full_run_on_src05 | data alerts not counted as alarms; badge uses alerts status=open | inspection |
| FR-301 | Must | PASS |  | tests/integration/api/test_ui_fixture_ds07.py::test_exactly_four_data_alerts |  | test |
| FR-302 | Must | PASS |  | tests/integration/api/test_residents.py::test_overview; tests/integration/api/test_ui_fixture_ds07.py::test_resident_list; tests/integration/api/test_ui_fixture_ds07.py::test_pages_agree_for_the_same_as_of |  | test |
| FR-310 | Must | PASS |  | tests/integration/api/test_ui_fixture_ds07.py::test_study_team_analytics |  | test |
| FR-311 | Must | PASS |  | frontend/tests/pages/study.test.tsx (UX-010, FE-195) | heading, counts line, answer-key clause test profile only | inspection |
| FR-312 | Must | PASS |  | tests/integration/api/test_analytics.py::test_summary |  | test |
| FR-313 | Must | PASS |  | frontend/components/KpiTiles/KpiTiles.test.tsx; frontend/tests/pages/study.test.tsx; tests/unit/analytics/test_aggregates.py::test_src05_kpis | four tiles with values | inspection |
| FR-314 | Must | PASS |  | tests/unit/analytics/test_aggregates.py::test_pct_half_up_integer | half-up integer | inspection |
| FR-315 | Must | PASS |  | frontend/tests/pages/study.test.tsx (UX-356..UX-360); tests/unit/analytics/test_aggregates.py::test_src05_daily_series | legend Used, Set aside, Held back (other voice), Missed; Oct 12 label | inspection |
| FR-316 | Must | PASS |  | frontend/tests/pages/study.test.tsx (funnel); tests/unit/analytics/test_aggregates.py::test_src05_funnel | four funnel rows exact | inspection |
| FR-317 | Must | PASS |  | frontend/tests/pages/study.test.tsx (by-resident); tests/unit/analytics/test_aggregates.py::test_src05_by_resident | lowest first, accessible names | inspection |
| FR-318 | Must | PASS |  | frontend/tests/pages/study.test.tsx (alarm timing); frontend/components/AlarmTimingTable/AlarmTimingTable.test.tsx; tests/integration/api/test_analytics.py::test_summary | rows from ground truth; 'Other 8' row | inspection |
| FR-319 | Must | PASS |  | tests/integration/api/test_analytics.py::test_production_profile; frontend/components/ReviewOutcomesTable/ReviewOutcomesTable.test.tsx; frontend/tests/pages/study.test.tsx (FE-195) | production review outcomes panel | inspection |
| FR-320 | Must | PASS |  | frontend/tests/pages/study.test.tsx ('Show daily counts as a table'); frontend/components/UsableByResidentChart/UsableByResidentChart.tsx:49 | daily table; meters have accessible names per UX-225 | inspection |
| FR-321 |  | NOT APPLICABLE |  | specs/TRD/02_Functional_Requirements_Specification.md:373 | Retired by TRD 24 D-110 (wireframe v0.2) | inspection |
| FR-322 | Must | PASS |  | tests/integration/api/test_analytics.py::test_summary; ::test_production_profile | kpis, daily_series, funnel, by_resident, alarm_timing/review_outcomes | inspection |
| FR-323 | Must | PASS |  | tests/integration/api/test_ui_fixture_ds07.py::test_study_team_analytics |  | test |
| FR-330 | Must | PASS |  | frontend/components/AppHeader/AppHeader.test.tsx; frontend/lib/hooks.ts:23 | brand, facility line, nav by role, open-alarm badge, name, Sign out | inspection |
| FR-331 | Must | PASS |  | frontend/tests/pages/resident-layout.test.tsx; frontend/tests/pages/protected-layout.test.tsx (activeFor); frontend/tests/pages/admissions.test.tsx:106 | chart back link, nav active Resident list; admissions no back link | inspection |
| FR-332 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_meta_uses_the_latest_succeeded_run |  | test |
| FR-333 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_meta_uses_the_latest_succeeded_run |  | test |

### 03 Non Functional Requirements

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| NFR-001 | Must | PASS |  | tests/performance/test_api_latency.py::test_read_endpoints_p95_on_ds08 | Performance test: budget subset in CI backend-test; nightly budgets run locally (CHECKPOINT_8 §5 rows 3-4) | test |
| NFR-002 | Must | PASS |  | tests/performance/test_api_latency.py::test_read_endpoints_p95_on_ds08 | Performance test: budget subset in CI backend-test; nightly budgets run locally (CHECKPOINT_8 §5 rows 3-4) | test |
| NFR-003 | Must | PASS |  | tests/performance/test_api_latency.py::test_read_endpoints_p95_on_ds08 | Performance test: budget subset in CI backend-test; nightly budgets run locally (CHECKPOINT_8 §5 rows 3-4) | test |
| NFR-004 | Must | PASS |  | tests/performance/test_api_latency.py::test_post_sessions_p95_pr_scope; tests/performance/test_api_latency.py::test_post_sessions_p95_200_requests | Performance test: budget subset in CI backend-test; nightly budgets run locally (CHECKPOINT_8 §5 rows 3-4) | test |
| NFR-005 | Must | PASS |  | tests/performance/test_pipeline_runtime.py::test_pipeline_on_src05_within_5_s | Performance test: budget subset in CI backend-test; nightly budgets run locally (CHECKPOINT_8 §5 rows 3-4) | test |
| NFR-006 | Must | PASS |  | tests/performance/test_pipeline_runtime.py::test_src05_full_rebuild_within_30_s | Performance test: budget subset in CI backend-test; nightly budgets run locally (CHECKPOINT_8 §5 rows 3-4) | test |
| NFR-007 | Must | PASS |  | tests/performance/test_pipeline_runtime.py::test_ds08_full_rebuild_within_120_s | Performance test: budget subset in CI backend-test; nightly budgets run locally (CHECKPOINT_8 §5 rows 3-4) | test |
| NFR-008 | Should | PENDING BLOCK 4 |  | frontend/services/api.ts:40; frontend/lib/queryClient.ts:5 | Manual staging cold-start check; client retries timeouts so loading persists | inspection |
| NFR-009 | Must | PASS |  | tests/performance/test_api_latency.py::test_ingest_src05_accepted_and_processed | Performance test: budget subset in CI backend-test; nightly budgets run locally (CHECKPOINT_8 §5 rows 3-4) | test |
| NFR-010 | Should | FAIL | S4 | frontend/lighthouserc.json:20-27; .github/workflows/e2e.yml:255 | LCP<=2.5s asserted (desktop preset, passing on PRs); INP<200ms and Fast 4G throttling not checked (TST-125 narrowed it) | inspection |
| NFR-011 | Must | PASS |  | frontend/tests/e2e/isolated.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| NFR-012 | Should | PASS |  | scripts/ci/check-bundle.mjs:24; .github/workflows/ci.yml:200 |  | inspection |
| NFR-013 | Should | FAIL | S4 | frontend/components/AlarmReviewPanel/AlarmReviewPanel.tsx:44; frontend/tests/e2e/mutating.spec.ts:55 | Updates without reload via query invalidation; the 1 s budget is never asserted (default expect timeout) | inspection |
| NFR-020 | Should | PENDING BLOCK 4 |  | .github/workflows/uptime.yml:13 | Uptime workflow exists; availability during demo window needs production | inspection |
| NFR-021 | Must | PASS |  | tests/integration/api/test_sessions.py::test_failed_run_answers_pending; backend/services/ingestion.py | Raw record committed before run; kill-process fault injection not separately tested | inspection |
| NFR-022 | Must | PASS |  | tests/integration/api/test_sessions.py::test_failed_run_answers_pending |  | inspection |
| NFR-023 | Must | PASS |  | backend/jobs/nightly_run.py; tests/integration/pipeline/test_nightly_run.py::test_one_run_per_local_night_across_dst; frontend/components/AdminPanel/AdminPanel.tsx:60 | No retry; failed run banner on Admin; manual run available | inspection |
| NFR-024 | Must | PENDING BLOCK 4 |  | docs/deployment.md:219; .github/workflows/deploy-production.yml:10 | Interim waiver; Neon PITR window and DEP-096 dump are platform/procedure evidence | inspection |
| NFR-025 | Should | PENDING BLOCK 4 |  | docs/deployment.md | Restore drill before 15 Nov is a Block 4 rehearsal | inspection |
| NFR-026 | Must | PASS |  | tests/integration/api/test_ingest.py::test_record_errors_do_not_fail_the_batch |  | inspection |
| NFR-027 | Must | PASS |  | backend/core/db.py:66 (connect_timeout 5); tests/integration/api/test_http_middleware.py::test_database_unreachable_is_503_with_retry_after; tests/integration/api/test_health.py::test_tst_054_health_degraded_with_database_down |  | inspection |
| NFR-030 | Must | PASS |  | analytics/robust_stats.py:17; grep analytics for float32/Decimal: none |  | inspection |
| NFR-031 | Must | PASS |  | tests/validation/test_harness.py::test_tier_a_matches_the_answer_key |  | inspection |
| NFR-032 | Must | PASS |  | database/schema.sql (39 double precision); tests/validation/test_harness.py::test_tier_a_equals_tier_b | Tier A (memory) vs Tier B (DB reload) compared with exact equality | inspection |
| NFR-033 | Must | PASS |  | tests/unit/analytics/test_pipeline.py::test_deterministic_and_order_independent; tests/validation/test_global_checks.py::test_vc_g12_determinism_and_rebuild |  | inspection |
| NFR-034 | Must | PASS |  | pyproject.toml:43 (random, os forbidden); analytics/pipeline.py:222 (sorted inputs) | Sets used only for membership | inspection |
| NFR-035 | Must | PASS |  | tests/integration/api/test_pipeline.py::test_run_lifecycle_and_snapshot |  | inspection |
| NFR-036 | Must | FAIL | S3 | backend/requirements.txt:3-17; backend/requirements-dev.txt; frontend/package-lock.json | package-lock.json OK; Python has exact top-level pins only, no lock file with hashes and transitive deps unpinned | inspection |
| NFR-037 | Must | PASS |  | frontend/lib/format.ts:146; analytics/speaker_screen.py:46; grep analytics for round(: none |  | inspection |
| NFR-040 | Must | PASS |  | tests/security/test_no_audio.py::test_audio_is_refused_everywhere |  | test |
| NFR-041 | Must | PASS |  | tests/security/test_data_minimisation.py::test_responses_and_logs_hold_study_ids_only |  | test |
| NFR-042 | Must | PENDING BLOCK 4 |  | tests/smoke/test_tls.py; backend/core/config.py:217 | Startup sslmode check exists; TLS scan of hosted endpoints is Block 4 | inspection |
| NFR-043 | Must | PENDING BLOCK 4 |  | tests/security/test_transport_and_secrets.py::test_backend_sends_hsts_in_staging_and_production; netlify.toml:27; tests/smoke/test_staging_smoke.py::test_i_api_hsts_and_https_redirect | HSTS in code/config; redirect check on hosted origins pending | inspection |
| NFR-044 | Must | PENDING BLOCK 4 |  | docs/deployment.md:68 | Provider encryption evidence is a platform check | inspection |
| NFR-045 | Must | PENDING BLOCK 4 |  | render.yaml:20; docs/deployment.md:11 | Policy documented; hosted ingest audit pending | inspection |
| NFR-046 | Must | NOT APPLICABLE |  | specs/TRD/15_Deployment_and_DevOps_Spec.md:558 | AWS go-live item | inspection |
| NFR-047 | Must | PASS |  | tests/integration/db/test_grants.py::test_app_privileges_are_exactly_section_4_8; tests/integration/api/test_role_checks.py::test_every_matrix_cell | Cloud console access is a platform matter (Block 4) | inspection |
| NFR-048 | Must | PASS |  | tests/security/test_data_minimisation.py::test_responses_and_logs_hold_study_ids_only |  | test |
| NFR-049 | Must | PASS |  | tests/integration/db/test_audit_writer.py::test_audit_row_shares_the_change_transaction |  | inspection |
| NFR-050 | Must | PASS |  | tests/security/test_data_minimisation.py::test_csv_exports_hold_no_note_text |  | test |
| NFR-051 | Must | PASS |  | backend/repositories/raw_session_repository.py; tests/unit/backend/repositories/test_raw_session_repository.py::test_repository_has_no_update_or_delete | No app deletion; only IRB-directed operator CLI purge-resident per TRD 15:421/DB-064 | inspection |
| NFR-052 | Must | PENDING BLOCK 4 |  | render.yaml:47; docs/deployment.md:26 | Render ohio in Blueprint; Neon region is a dashboard setting | inspection |
| NFR-060 | Must | PASS |  | frontend/tests/e2e/a11y.spec.ts | axe on TST-110 routes; manual screen-reader pass not evidenced | inspection |
| NFR-061 | Must | PASS |  | frontend/components/StatusPill/StatusPill.tsx:13; frontend/lib/wording/common.ts:45 |  | inspection |
| NFR-062 | Must | PASS |  | frontend/tests/unit/tokens.test.ts; frontend/styles/tokens.css |  | inspection |
| NFR-063 | Must | PASS |  | frontend/components/ChangeScoreChart/ChangeScoreChart.tsx:109,274 | 1px --muted outline on pre-alarm bars; ChangeScoreTable alternative | inspection |
| NFR-064 | Must | PASS |  | frontend/tests/e2e/responsive.spec.ts:68; frontend/styles/tokens.css:36 |  | inspection |
| NFR-065 | Must | PASS |  | frontend/tests/e2e/a11y.spec.ts:81 | TST-111 keyboard-only run | inspection |
| NFR-066 | Should | FAIL | S3 | grep frontend/tests/docs/scripts for Flesch/readability: none | Plain-language labels exist; no Flesch-Kincaid grade check of the "Right now" strings | inspection |
| NFR-067 | Must | FAIL | S3 | .github/workflows/ci.yml:41 | CI check greps only diagnoses\|severity and scans frontend/lib/wording.ts (a re-export barrel), not frontend/lib/wording/*.ts where copy lives; current copy is clean | inspection |
| NFR-068 | Must | PASS |  | frontend/tests/e2e/responsive.spec.ts:8-13,119,140 | 320-390, 600, 1280 px tested; 768 px and explicit 200% zoom not separately tested | inspection |
| NFR-069 | Should | NOT APPLICABLE |  | specs/TRD/00_Project_Vision_and_Scope.md:302 | Usability session with staff after interviews; requirement on people/later activity | inspection |
| NFR-070 | Must | PASS |  | frontend/lib/wording/common.ts:70; frontend/lib/wording/list.ts:143; frontend/components/SectionState/ |  | inspection |
| NFR-080 | Must | PASS |  | pyproject.toml:25-32; .github/workflows/ci.yml:77 |  | inspection |
| NFR-081 | Must | PASS |  | .github/workflows/ci.yml:75-76,195-197; frontend/tsconfig.json:7 |  | inspection |
| NFR-082 | Must | PASS |  | .github/workflows/ci.yml:126-127; frontend/vitest.config.ts:21 |  | inspection |
| NFR-083 | Must | PASS |  | tests/unit/analytics/test_quality_screening.py::test_thresholds_are_strict; tests/unit/analytics/test_morning_offset.py; tests/unit/analytics/test_cusum_engine.py |  | inspection |
| NFR-084 | Must | PASS |  | tests/integration/test_cli_pipeline.py::test_set_config_then_rebuild |  | inspection |
| NFR-085 | Should | FAIL | S4 | AST scan: 44 of 71 public analytics functions and 35 of 134 public service functions lack docstrings | Docstrings with TRD IDs only partial (many IDs in module docstrings) | inspection |
| NFR-086 | Must | FAIL | S3 | tests/integration/db/test_migrations.py::test_tst_040_upgrade_downgrade_upgrade_round_trip; .github/workflows/ci.yml:116 | Round trip only on empty DB (reset-test-db test uses master data only); no up/down test with the reference dataset loaded | inspection |
| NFR-087 | Should | PASS |  | README.md:13; docs/deployment.md:39 | One-command compose + documented seed; 10-min timing not recorded | inspection |
| NFR-088 | Must | PASS |  | .github/workflows/ci.yml:164-180; tests/contract/test_openapi_contract.py::test_generated_equals_committed |  | inspection |
| NFR-089 | Must | PASS |  | backend/requirements.txt:10; tests/unit/test_repository_layout.py::test_requirements_pinned_without_psycopg2 |  | inspection |
| NFR-090 | Must | PASS |  | backend/Dockerfile:36; .github/workflows/ci.yml:230; .github/workflows/e2e.yml:52 | Env-only config; image run in compose E2E stack | inspection |
| NFR-091 | Must | PASS |  | .github/workflows/ci.yml:84; tests/unit/backend/test_db_inspection.py::test_migrations_never_manage_extensions_or_the_database |  | inspection |
| NFR-092 | Must | PASS |  | .github/workflows/ci.yml:199; netlify.toml:7 |  | inspection |
| NFR-093 | Should | FAIL | S4 | specs/TRD/15_Deployment_and_DevOps_Spec.md:507,558 (DEP-117) | Cut-over procedure documented; no effort estimate (<=5 person-days) or migration analysis recorded | inspection |
| NFR-094 | Must | PASS |  | backend/core/config.py; tests/unit/backend/core/test_config.py::test_dotenv_ignored_in_staging; render.yaml (sync: false) |  | inspection |
| NFR-100 | Must | PASS |  | tests/unit/backend/core/test_logging.py::test_json_lines_have_the_required_keys |  | test |
| NFR-101 | Must | PASS |  | backend/services/pipeline_runner.py:251-309; tests/integration/api/test_pipeline.py::test_get_run |  | inspection |
| NFR-102 | Should | PASS |  | tests/unit/backend/core/test_monitoring.py::test_empty_dsn_logs_error_and_never_calls_transport; tests/unit/backend/core/test_monitoring.py::test_unhandled_exception_event_is_sanitised |  | inspection |
| NFR-103 | Should | PASS |  | frontend/components/AdminPanel/AdminPanel.tsx:57-67; tests/integration/pipeline/test_nightly_run.py::test_missed_night_is_reported; frontend/tests/pages/admin.test.tsx |  | inspection |
| NFR-104 | Should | PASS |  | .github/workflows/uptime.yml:13 | Every 30 min, staging and production health | inspection |
| NFR-105 | Must | PASS |  | tests/integration/db/test_read_models.py::test_device_silent_and_gap_days; tests/validation/test_r02_missing_days.py; tests/integration/api/test_ui_fixture_ds07.py::test_exactly_four_data_alerts |  | inspection |
| NFR-110 | Must | PASS |  | README.md:5; backend/api/openapi.py:34 |  | inspection |
| NFR-111 | Must | FAIL | S3 | tests/trace_report.py (not run in CI); docs/reports/traceability_inspections.md missing; trace_report lists 378 Must IDs w/o test/inspection | Traceability report not generated in CI and many Musts lack a linked test or documented inspection (this audit is the workaround) | inspection |
| NFR-112 | Must | PASS |  | specs/TRD/24_Risk_Assumptions_and_Open_Questions.md (OQ-01, OQ-11); specs/TRD/15_Deployment_and_DevOps_Spec.md:421 | Undecided items recorded as OQs; deletion only IRB-directed | inspection |
| NFR-113 | Must | PASS |  | render.yaml:52 (GIT_SHA from RENDER_GIT_COMMIT); tests/integration/api/test_health.py::test_tst_054_health_ok_with_database_up; tests/integration/api/test_pipeline.py::test_run_lifecycle_and_snapshot |  | inspection |
| NFR-114 | Must | PASS |  | specs/business-requirements/REFERENCES.md:7 | SRC-07 linked, not committed | inspection |
| NFR-115 | Must | PASS |  | .github/workflows/ci.yml:44; tests/security/test_static_scans.py::test_no_forbidden_dependencies |  | inspection |
| NFR-120 | Must | PASS |  | tests/integration/test_schema_behaviour.py::test_ac_pgs_01_raw_sessions_update_fails_for_owner; tests/integration/test_schema_behaviour.py::test_ac_pgs_02_raw_sessions_delete_and_truncate_fail_for_app |  | inspection |
| NFR-121 | Must | PASS |  | tests/validation/test_global_checks.py::test_vc_g11_raw_store_fidelity |  | inspection |
| NFR-122 | Must | PASS |  | tests/integration/db/test_raw_store.py::test_same_session_id_twice_gets_increasing_arrival_seq |  | inspection |
| NFR-123 | Must | PASS |  | tests/integration/db/test_grants.py::test_ac_pgs_13_every_fk_restricts_except_scores; tests/integration/test_schema_reference.py::test_schema_sql_matches_the_migrated_database |  | inspection |
| NFR-124 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_late_record_keeps_frozen_baselines; tests/validation/test_invariance.py::test_vc_r10_frz_frozen_baseline |  | inspection |
| NFR-125 | Must | FAIL | S3 | grep backend/analytics/tests for a per-resident count invariant: none; only SRC-05 totals in tests/validation/test_global_checks.py::test_vc_g01_status_totals | No invariant check after runs; holds on reference data via answer-key totals only | inspection |
| NFR-126 | Must | PASS |  | tests/integration/test_schema_behaviour.py::test_reviews_and_notes_are_append_only; tests/integration/test_schema_behaviour.py::test_ac_pgs_03_audit_logs_are_append_only_for_app |  | inspection |
| NFR-127 | Must | PASS |  | tests/validation/test_harness.py::test_ground_truth_never_changes_the_outputs; tests/integration/db/test_ground_truth_loader.py::test_refuses_outside_test_v0_1 |  | inspection |
| NFR-128 | Must | PASS |  | tests/integration/api/test_ui_fixture_ds07.py::test_pages_agree_for_the_same_as_of |  | test |
| NFR-129 | Must | PASS |  | tests/integration/api/test_sessions.py::test_failed_run_answers_pending |  | inspection |
| NFR-130 | Must | PASS |  | database/schema.sql (timestamptz only); frontend/lib/format.ts; analytics/morning_offset.py |  | inspection |
| NFR-131 | Must | PASS |  | tests/unit/analytics/test_morning_offset.py::test_local_time_vectors |  | test |
| NFR-132 | Must | PASS |  | tests/unit/analytics/test_morning_offset.py::test_local_time_vectors |  | test |
| NFR-133 | Must | PASS |  | frontend/lib/format.ts; frontend/tests/unit/format.test.ts | Facility-zone formatting with abbreviation; no Playwright Europe/London test, test:tz not in CI | inspection |
| NFR-134 | Must | PASS |  | render.yaml:77; tests/integration/pipeline/test_nightly_run.py::test_one_run_per_local_night_across_dst |  | inspection |
| NFR-140 | Must | PASS |  | frontend/playwright.config.ts:17-19; .github/workflows/e2e.yml:29 | Chromium/Firefox/WebKit on nightly schedule; Edge manual check at release | inspection |
| NFR-141 | Should | FAIL | S3 | frontend/playwright.config.ts:16-20; frontend/tests/e2e/responsive.spec.ts:8 | No tablet device emulation (iPad/Android) or 768 px test | inspection |
| NFR-142 | Must | PASS |  | frontend/tests/e2e/a11y.spec.ts ""; frontend/tests/pages/root.test.tsx "root layout and home page" | E2E in CI playwright on 23e558b (success) | test |
| NFR-150 | Must | PASS |  | tests/performance/test_api_latency.py::test_read_endpoints_p95_on_ds08 | Performance test: budget subset in CI backend-test; nightly budgets run locally (CHECKPOINT_8 §5 rows 3-4) | test |
| NFR-151 | Must | PASS |  | tests/integration/api/test_rate_limits.py::test_ingest_routes_are_not_also_capped_by_the_default_limit; tests/performance/test_ingest_sustained.py::test_sustained_10_records_per_second_for_60_s |  | test |
| NFR-152 | Should | PASS |  | tests/performance/test_pipeline_runtime.py::test_ds08_full_rebuild_within_120_s | Performance test: budget subset in CI backend-test; nightly budgets run locally (CHECKPOINT_8 §5 rows 3-4) | test |
| NFR-153 | Must | PASS |  | specs/TRD/03_Non_Functional_Requirements.md:216; specs/TRD/24_Risk_Assumptions_and_Open_Questions.md:125 (ASM-08) | Documented policy | inspection |

### 04 Frontend TRD

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| FE-001 | Must | PASS |  | frontend/package.json:28; frontend/tsconfig.json:7; frontend/app/ (App Router) | next 14.2.35, typescript 5.6.3, strict true | inspection |
| FE-002 | Must | FAIL | S4 | frontend/package.json:50 ("eslint-config-prettier": "10.1.8"); specs/TRD/04_Frontend_TRD.md:80 | eslint-config-prettier is 10.x, §4.1 pins 9.x; other pins match, lockfile committed | inspection |
| FE-003 | Must | PASS |  | frontend/package.json:26-32; frontend/components/*/*.module.css (45); frontend/styles/tokens.css | react 18.3.1, no UI/icon lib; non-ASCII scan of app/components/lib finds only ▲ ! ● ○ ← as glyphs (others are punctuation) | inspection |
| FE-004 | Must | PASS |  | frontend/tests/pages/root.test.tsx "root layout and home page" |  | test |
| FE-005 | Must | FAIL | S4 | frontend/components/FacilityRangeChart/FacilityRangeChart.tsx:1-20 (no recharts import); frontend/package.json:31 | Recharts 2.13.3, no other chart lib, but the facility range chart (§4.1 lists it as Recharts) is hand-built HTML/CSS | inspection |
| FE-006 | Must | PASS |  | frontend/lib/hooks.ts:11-28; frontend/lib/queryClient.ts:12-25; app/(protected)/*/page.tsx useQuery/useMutation | @tanstack/react-query 5.105.0; login/logout and CSV downloads call api directly (not cached server state) | inspection |
| FE-007 | Must | PASS |  | frontend/tests/e2e/privacy.spec.ts:40; .github/workflows/ci.yml:26 | grep for audio/video/MediaRecorder/AudioContext/waveform in frontend source: no hits | inspection |
| FE-008 | Must | PASS |  | .github/workflows/ci.yml:44; frontend/package.json:26-58 | no openai/anthropic/llm/langchain references in frontend source or deps | inspection |
| FE-010 | Must | PASS |  | frontend/app/, frontend/lib/, frontend/services/api.ts, frontend/tests/{unit,pages,fixtures,msw,e2e} | tree matches §4.2; package.json, next.config.js, services/api.ts filled in place | inspection |
| FE-011 | Must | PASS |  | frontend/services/api.ts:146 | only fetch( call in frontend source is in services/api.ts | inspection |
| FE-012 | Must | PASS |  | frontend/package.json:21; .github/workflows/ci.yml:164-179 | CI exports OpenAPI, diffs contract, regenerates lib/api-types.ts and fails on diff | inspection |
| FE-013 | Must | PASS |  | frontend/components/WhatsHappening/WhatsHappening.test.tsx "WhatsHappening"; frontend/tests/unit/wording-admin.test.ts "admissions wording"; frontend/tests/unit/wording-chart.test.ts "" (+4 more) |  | test |
| FE-020 | Must | PASS |  | frontend/app/(protected)/{residents,residents/[residentCode]/{review,trends,baseline,log,device},admissions,study,admin}/page.tsx; app/login/page.tsx; app/page.tsx | all §4.3 routes present; no /alerts or /analytics; #devices at components/DevicesSection/DevicesSection.tsx:159 | inspection |
| FE-021 | Must | PASS |  | frontend/tests/pages/root.test.tsx "root layout and home page" |  | test |
| FE-022 | Must | PASS |  | frontend/tests/pages/protected-layout.test.tsx "" |  | test |
| FE-023 | Must | PASS |  | frontend/components/AppHeader/AppHeader.test.tsx ""; frontend/tests/pages/login.test.tsx "/login"; frontend/tests/pages/protected-layout.test.tsx "" |  | test |
| FE-024 | Must | PASS |  | frontend/components/AppHeader/AppHeader.test.tsx "" |  | test |
| FE-025 | Must | PASS |  | frontend/components/BackLink/BackLink.test.tsx "BackLink"; frontend/tests/pages/resident-layout.test.tsx ""; frontend/tests/pages/residents.test.tsx "" |  | test |
| FE-026 | Must | NOT APPLICABLE |  | frontend/tests/pages/study.test.tsx "" | Retired row (test reference kept for history) | test |
| FE-027 | Must | PASS |  | frontend/components/AppHeader/AppHeader.test.tsx "" |  | test |
| FE-028 | Must | PASS |  | frontend/components/AppHeader/AppHeader.test.tsx "" |  | test |
| FE-029 | Must | PASS |  | frontend/components/AppHeader/AppHeader.test.tsx "" |  | test |
| FE-030 | Must | PASS |  | frontend/tests/pages/resident-device.test.tsx ""; frontend/tests/pages/resident-layout.test.tsx ""; frontend/tests/pages/resident-review.test.tsx "" |  | test |
| FE-031 | Must | PASS |  | frontend/tests/pages/resident-layout.test.tsx "" |  | test |
| FE-032 | Must | PASS |  | frontend/tests/pages/admin.test.tsx ""; frontend/tests/pages/admissions.test.tsx ""; frontend/tests/pages/login.test.tsx "/login" (+8 more) |  | test |
| FE-033 | Must | PASS |  | frontend/tests/pages/root.test.tsx "root layout and home page" |  | test |
| FE-034 | Must | PASS |  | frontend/tests/e2e/auth.spec.ts ""; frontend/tests/pages/admin.test.tsx "" | E2E in CI playwright on 23e558b (success) | test |
| FE-035 | Must | PASS |  | frontend/components/SectionState/SectionState.test.tsx "SectionState"; frontend/tests/pages/residents.test.tsx "" |  | test |
| FE-036 | Must | PASS |  | frontend/components/AppHeader/AppHeader.test.tsx "" |  | test |
| FE-037 | Must | PASS |  | frontend/tests/pages/study.test.tsx "" |  | test |
| FE-206 | Must | PASS |  | frontend/components/ChartSectionNav/ChartSectionNav.test.tsx "ChartSectionNav"; frontend/tests/pages/resident-layout.test.tsx "" |  | test |
| FE-040 | Must | PASS |  | frontend/app/(protected)/layout.tsx:1; all (protected) pages start with "use client" | server components (app/layout, page.tsx redirect, not-found) fetch no data | inspection |
| FE-041 | Must | PASS |  | netlify.toml:16-17; frontend/next.config.js:3-9 | @netlify/plugin-nextjs, no output: "export"; middleware.ts and dynamic routes in use | inspection |
| FE-042 | Must | PASS |  | frontend/middleware.ts:4-12 | sets Cache-Control: private, no-store on /residents, /admissions, /study, /admin, /login | inspection |
| FE-043 | Must | PASS |  | frontend/next.config.js:4-5 | reactStrictMode true, poweredByHeader false, no images config | inspection |
| FE-044 | Must | PASS |  | frontend/next.config.js; frontend/middleware.ts | no Netlify Functions/Edge/Blobs/Forms/Identity imports in frontend source | inspection |
| FE-045 | Must | PASS |  | frontend/lib/queryClient.ts:1-25 | no persister; sessionStorage only for auth token (lib/auth.ts:15) and list filter (BackLink.tsx:12), not query cache | inspection |
| FE-050 | Must | PASS |  | frontend/components/LoginForm/LoginForm.test.tsx ""; frontend/tests/unit/auth.test.ts "auth token store" |  | test |
| FE-051 | Must | PASS |  | frontend/tests/unit/auth.test.ts "auth token store" |  | test |
| FE-052 | Must | PASS |  | frontend/components/LoginForm/LoginForm.test.tsx ""; frontend/tests/unit/auth.test.ts "auth token store" |  | test |
| FE-053 | Must | PASS |  | frontend/tests/unit/auth.test.ts "auth token store" |  | test |
| FE-054 | Must | PASS |  | frontend/tests/pages/protected-layout.test.tsx "" |  | test |
| FE-055 | Must | PASS |  | frontend/tests/pages/protected-layout.test.tsx "" |  | test |
| FE-056 | Must | PASS |  | frontend/tests/pages/protected-layout.test.tsx ""; frontend/tests/pages/residents.test.tsx ""; frontend/tests/unit/api.test.ts "api client" |  | test |
| FE-057 | Must | PASS |  | frontend/components/LoginForm/LoginForm.test.tsx ""; frontend/tests/unit/auth.test.ts "auth token store" |  | test |
| FE-058 | Must | PASS |  | frontend/components/AppHeader/AppHeader.test.tsx "" |  | test |
| FE-059 | Must | PASS |  | frontend/tests/unit/status-roles-groups.test.ts "toDisplayStatus (FE-207)" |  | test |
| FE-060 | Must | PASS |  | tests/unit/test_netlify_config.py::test_connect_src_is_exactly_self_and_the_two_render_origins |  | test |
| FE-061 | Must | PENDING BLOCK 4 |  | netlify.toml:24-31 | repo side done: header set verbatim in netlify.toml; response-header check needs hosted Netlify origins | inspection |
| FE-062 | Must | PASS |  | frontend/.eslintrc.json (react/no-danger: error) | no dangerouslySetInnerHTML/eval/new Function/innerHTML in frontend source | inspection |
| FE-063 | Must | PASS |  | frontend/components/NotesList/NotesList.test.tsx::lists notes newest first with time, type and author, text kept as typed | test renders "<b>not bold</b>" as literal text; no HTML rendering paths | inspection |
| FE-064 | Must | PASS |  | frontend/tests/e2e/privacy.spec.ts:40; frontend/app/layout.tsx:5 | no <script>/next/script/external URLs; E2E asserts only frontend and API origins contacted | inspection |
| FE-065 | Must | PASS |  | .github/workflows/ci.yml:224; scripts/ci/audit_gate.py:25,56 | npm audit --omit=dev, blocks high/critical with SECURITY_EXCEPTIONS.md allow-list | inspection |
| FE-066 | Must | PASS |  | frontend/components/LoginForm/LoginForm.test.tsx "" |  | test |
| FE-067 | Must | PASS |  | frontend/app/(protected)/error.tsx:1-15; frontend/lib/wording/common.ts:74; frontend/components/AdminPanel/formErrors.ts | boundaries show no details; errors map by code to fixed copy; request_id as "Reference:" | inspection |
| FE-068 | Must | PASS |  | frontend/lib/types.ts; grep of app/components/lib | no name/DOB/room fields rendered; room_label in api-types is never used | inspection |
| FE-070 | Must | PASS |  | frontend/tests/unit/api.test.ts "api client" |  | test |
| FE-071 | Must | PASS |  | frontend/tests/unit/api.test.ts "api client" |  | test |
| FE-072 | Must | PASS |  | frontend/tests/unit/api.test.ts "api client" |  | test |
| FE-073 | Must | PASS |  | frontend/tests/unit/api.test.ts "api client" |  | test |
| FE-074 | Must | PASS |  | frontend/tests/unit/api.test.ts "api client" |  | test |
| FE-079 | Must | PASS |  | frontend/components/AdminPanel/AdminPanel.test.tsx ""; frontend/components/AlertReviewForm/AlertReviewForm.test.tsx ""; frontend/components/StaffNotes/StaffNotes.test.tsx "" (+1 more) |  | test |
| FE-075 | Must | PASS |  | frontend/services/api.ts:4-38,186-265; frontend/lib/types.ts:2-3 | all 30 §4.6.2 functions exist; types from lib/api-types.ts via lib/types.ts | inspection |
| FE-076 | Must | PASS |  | frontend/tests/pages/residents.test.tsx ""; frontend/tests/unit/api.test.ts "api client" |  | test |
| FE-077 | Must | PASS |  | frontend/tests/unit/wording-chart.test.ts "" |  | test |
| FE-078 | Must | FAIL | S3 | frontend/services/api.ts:166-170 (res.json() as T) | no runtime check of required fields; a missing field is not turned into an error state; no test found | inspection |
| FE-080 | Must | PASS |  | frontend/tests/unit/api.test.ts "api client" |  | test |
| FE-081 | Should | PASS |  | frontend/tests/pages/residents.test.tsx "" |  | test |
| FE-082 | Must | PASS |  | frontend/components/FilterButtons/FilterButtons.test.tsx "FilterButtons"; frontend/tests/pages/residents.test.tsx "" |  | test |
| FE-083 | Must | PASS |  | frontend/components/ResidentsTable/ResidentsTable.test.tsx ""; frontend/tests/pages/residents.test.tsx "" |  | test |
| FE-084 | Must | PASS |  | frontend/components/ResidentsTable/ResidentsTable.test.tsx ""; frontend/tests/pages/residents.test.tsx "" |  | test |
| FE-085 | Must | PASS |  | frontend/components/StaffNotes/StaffNotes.test.tsx ""; frontend/tests/pages/resident-review.test.tsx "" |  | test |
| FE-086 | Must | PASS |  | frontend/components/AlarmReviewPanel/AlarmReviewPanel.test.tsx ""; frontend/tests/pages/resident-review.test.tsx "" |  | test |
| FE-087 | Must | PASS |  | frontend/tests/pages/resident-baseline.test.tsx ""; frontend/tests/pages/resident-device.test.tsx ""; frontend/tests/pages/resident-log.test.tsx "" (+3 more) |  | test |
| FE-088 | Must | PASS |  | frontend/components/DataBar/DataBar.test.tsx "DataBar"; frontend/tests/pages/protected-layout.test.tsx "" |  | test |
| FE-089 | Must | PASS |  | frontend/components/StaffNotes/StaffNotes.test.tsx "" |  | test |
| FE-090 | Must | PASS |  | frontend/components/<Name>/<Name>.tsx export interface <Name>Props (all §4.8 components) | every inventory component exists with exported Props; retired SummaryTiles/SortSelect/DeviceCell/Footer/Alert*/MiniTallyChart/ReviewDialog absent | inspection |
| FE-091 | Must | FAIL | S4 | frontend/components/AppHeader/AppHeader.tsx:49-51 | AppHeader (listed as presentational) calls useOpenAlarmCount (useQuery GET /alerts) itself instead of receiving the count as a prop | inspection |
| FE-092 | Must | PASS |  | frontend/components/AdmissionsTable/AdmissionsTable.test.tsx ""; frontend/components/RangePill/RangePill.test.tsx "RangePill"; frontend/components/ResidentsTable/ResidentsTable.test.tsx "" (+3 more) |  | test |
| FE-093 | Must | PASS |  | frontend/components/ChangeScoreChart/ChangeScoreChart.test.tsx ""; frontend/tests/pages/resident-trends.test.tsx "" |  | test |
| FE-094 | Must | PASS |  | frontend/components/ChangeScoreChart/ChangeScoreChart.test.tsx "" |  | test |
| FE-095 | Should | PASS |  | frontend/components/ChangeScoreChart/ChangeScoreChart.test.tsx "" |  | test |
| FE-096 | Must | PASS |  | frontend/components/ChangeScoreChart/ChangeScoreChart.test.tsx "" |  | test |
| FE-097 | Must | PASS |  | frontend/components/ChangeScoreChart/ChangeScoreChart.test.tsx ""; frontend/tests/pages/resident-trends.test.tsx ""; frontend/tests/unit/wording-trends.test.ts "" |  | test |
| FE-098 | Must | PASS |  | frontend/components/FeatureCard/FeatureCard.test.tsx "FeatureCard"; frontend/components/Sparkline/Sparkline.test.tsx "Sparkline" |  | test |
| FE-099 | Must | PASS |  | frontend/components/ChangeScoreChart/ChangeScoreChart.test.tsx ""; frontend/components/DailyCheckinsChart/DailyCheckinsChart.test.tsx ""; frontend/components/Sparkline/Sparkline.test.tsx "Sparkline" |  | test |
| FE-100 | Must | PASS |  | frontend/components/FacilityRangeChart/FacilityRangeChart.test.tsx ""; frontend/tests/pages/admissions.test.tsx "" |  | test |
| FE-101 | Must | PASS |  | frontend/components/CheckinLog/CheckinLog.test.tsx ""; frontend/tests/pages/resident-log.test.tsx ""; frontend/tests/unit/wording-chart.test.ts "" |  | test |
| FE-102 | Must | PASS |  | frontend/components/DevicesSection/DevicesSection.test.tsx ""; frontend/tests/pages/study.test.tsx ""; frontend/tests/unit/status-roles-groups.test.ts "toDisplayStatus (FE-207)" |  | test |
| FE-103 |  | NOT APPLICABLE |  | specs/TRD/04_Frontend_TRD.md:538 | retired by TRD 24 D-110 | inspection |
| FE-207 | Must | PASS |  | frontend/components/ResidentsTable/ResidentsTable.test.tsx ""; frontend/components/WhatsHappening/WhatsHappening.test.tsx "WhatsHappening"; frontend/tests/unit/status-roles-groups.test.ts "toDisplayStatus (FE-207)" |  | test |
| FE-208 | Must | PASS |  | frontend/components/DataBar/DataBar.test.tsx "DataBar" |  | test |
| FE-130 | Must | PASS |  | frontend/components/StaffNotes/StaffNotes.test.tsx ""; frontend/tests/pages/resident-review.test.tsx "" |  | test |
| FE-131 |  | NOT APPLICABLE |  | specs/TRD/04_Frontend_TRD.md:549 | retired by TRD 24 D-110 | inspection |
| FE-132 | Must | PASS |  | frontend/components/StaffNotes/StaffNotes.test.tsx "" |  | test |
| FE-133 | Must | PASS |  | frontend/components/StaffNotes/StaffNotes.test.tsx ""; frontend/tests/pages/resident-review.test.tsx "" |  | test |
| FE-134 | Must | PASS |  | frontend/components/AlarmReviewPanel/AlarmReviewPanel.test.tsx ""; frontend/tests/pages/resident-review.test.tsx "" |  | test |
| FE-135 | Must | PASS |  | frontend/components/AlarmReviewPanel/AlarmReviewPanel.test.tsx ""; frontend/components/StaffNotes/StaffNotes.test.tsx ""; frontend/tests/pages/resident-review.test.tsx "" |  | test |
| FE-136 | Must | PASS |  | frontend/components/AlertReviewForm/AlertReviewForm.test.tsx "" |  | test |
| FE-137 | Must | PASS |  | frontend/components/AlertReviewForm/AlertReviewForm.test.tsx "" |  | test |
| FE-138 | Must | PASS |  | frontend/components/AlertReviewForm/AlertReviewForm.test.tsx "" |  | test |
| FE-139 |  | NOT APPLICABLE |  | specs/TRD/04_Frontend_TRD.md:557 | retired by TRD 24 D-110 | inspection |
| FE-209 | Must | PASS |  | frontend/components/AlarmReviewPanel/AlarmReviewPanel.test.tsx ""; frontend/components/AlertReviewForm/AlertReviewForm.test.tsx ""; frontend/components/ReviewHistory/ReviewHistory.test.tsx "" (+1 more) |  | test |
| FE-210 | Must | PASS |  | frontend/components/ChartSectionNav/ChartSectionNav.test.tsx "ChartSectionNav"; frontend/components/SummaryPanel/SummaryPanel.test.tsx ""; frontend/tests/pages/resident-layout.test.tsx "" (+1 more) |  | test |
| FE-140 | Must | PASS |  | frontend/components/SectionState/SectionState.test.tsx "SectionState"; frontend/tests/pages/resident-device.test.tsx "" |  | test |
| FE-141 | Must | PASS |  | frontend/components/SectionState/SectionState.test.tsx "SectionState"; frontend/tests/pages/resident-device.test.tsx "" |  | test |
| FE-142 | Must | PASS |  | frontend/tests/pages/resident-layout.test.tsx "" |  | test |
| FE-143 | Must | PASS |  | frontend/lib/wording/list.ts:29; frontend/lib/wording/study.ts:200; frontend/lib/wording/trends.ts:132; tests/pages/residents.test.tsx; components/DevicesSection/DevicesSection.test.tsx::shows the empty state | UX-204 copy present and tested | inspection |
| FE-144 | Should | PASS |  | frontend/tests/pages/resident-layout.test.tsx "" |  | test |
| FE-145 | Must | PASS |  | frontend/tests/pages/protected-layout.test.tsx "" |  | test |
| FE-150 | Must | PASS |  | frontend/tests/unit/format.test.ts "" |  | test |
| FE-151 | Must | PASS |  | frontend/tests/unit/format.test.ts "" |  | test |
| FE-152 | Must | PASS |  | frontend/tests/unit/format.test.ts "" |  | test |
| FE-153 | Must | PASS |  | frontend/tests/unit/format.test.ts "" |  | test |
| FE-154 | Must | PASS |  | frontend/tests/unit/format.test.ts "" |  | test |
| FE-160 | Must | PASS |  | frontend/tests/unit/tokens.test.ts "design tokens" |  | test |
| FE-161 | Must | PASS |  | frontend/styles/globals.css:9-18,41-46,136-140 | body font/16px/1.45/tabular-nums/ink on canvas/margin 0; main max-width and page-pad 12px below 640px | inspection |
| FE-162 | Must | PASS |  | frontend/tests/e2e/responsive.spec.ts:68-90; frontend/styles/globals.css:102-107 | E2E checks all interactive targets ≥44×44 at 320–390px widths | inspection |
| FE-163 | Must | PASS |  | frontend/styles/globals.css:22-25; frontend/styles/tokens.css:37 | :focus-visible outline var(--focus-ring), offset 2px | inspection |
| FE-164 | Must | PASS |  | frontend/tests/unit/tokens.test.ts "design tokens" |  | test |
| FE-165 | Must | PASS |  | frontend/components/ChartSectionNav/ChartSectionNav.module.css:1; app/(protected)/residents/[residentCode]/layout.module.css:1; tests/e2e/responsive.spec.ts:121,142 | 760px nav row, 640px phone, 1024px tiles; E2E wide/narrow layouts | inspection |
| FE-211 | Should | FAIL | S3 | frontend/styles/tokens.css:42-66; no token-pair contrast analysis found | dark scheme via prefers-color-scheme, no toggle; but light --c-aside 2.23:1 and --c-quar 2.94:1 on --surface (<3:1), no pair check recorded | inspection |
| FE-170 | Must | PASS |  | frontend/tests/unit/config.test.ts "parsePublicConfig" |  | test |
| FE-171 | Must | PASS |  | frontend/tests/unit/config.test.ts "parsePublicConfig" |  | test |
| FE-172 | Should | PASS |  | frontend/components/EnvironmentRibbon/EnvironmentRibbon.test.tsx "EnvironmentRibbon"; frontend/tests/pages/root.test.tsx "root layout and home page" |  | test |
| FE-173 | Must | PASS |  | frontend/lib/config.ts:23-49; frontend/.env.example | only NEXT_PUBLIC_API_BASE_URL/APP_ENV/GIT_SHA; no secret names in frontend source | inspection |
| FE-180 | Must | PASS |  | frontend/vitest.config.ts:15-22 | coverage block matches FE-180 exactly | inspection |
| FE-181 | Must | PASS |  | frontend/components/FilterButtons/FilterButtons.test.tsx "FilterButtons" |  | test |
| FE-182 | Must | PASS |  | frontend/components/ResidentsTable/ResidentsTable.test.tsx "" |  | test |
| FE-183 | Must | PASS |  | frontend/components/ChangeScoreChart/ChangeScoreChart.test.tsx ""; frontend/tests/pages/resident-trends.test.tsx "" |  | test |
| FE-184 | Must | PASS |  | frontend/components/ChangeScoreTable/ChangeScoreTable.test.tsx "ChangeScoreTable"; frontend/tests/pages/resident-trends.test.tsx "" |  | test |
| FE-185 | Must | PASS |  | frontend/tests/e2e/resident-list.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| FE-186 | Must | PASS |  | frontend/tests/e2e/resident-chart.spec.ts ""; frontend/tests/pages/resident-baseline.test.tsx ""; frontend/tests/pages/resident-device.test.tsx "" (+2 more) | E2E in CI playwright on 23e558b (success) | test |
| FE-187 | Must | PASS |  | frontend/tests/e2e/mutating.spec.ts ""; frontend/tests/pages/resident-review.test.tsx "" | E2E in CI playwright on 23e558b (success) | test |
| FE-188 | Must | PASS |  | frontend/tests/e2e/auth.spec.ts ""; frontend/tests/pages/resident-review.test.tsx "" | E2E in CI playwright on 23e558b (success) | test |
| FE-189 | Must | PASS |  | frontend/tests/e2e/admissions.spec.ts "E2E-13 / FE-189 experimental note and empty state"; frontend/tests/pages/admissions.test.tsx "" | E2E in CI playwright on 23e558b (success) | test |
| FE-190 | Must | PASS |  | frontend/tests/e2e/a11y.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| FE-191 | Must | PASS |  | frontend/tests/e2e/responsive.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| FE-192 | Must | PASS |  | frontend/tests/e2e/privacy.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| FE-193 | Must | PASS |  | frontend/tests/e2e/mutating.spec.ts ""; frontend/tests/e2e/review.spec.ts ""; frontend/tests/pages/resident-review.test.tsx "" (+1 more) | E2E in CI playwright on 23e558b (success) | test |
| FE-205 | Must | PASS |  | frontend/components/AlarmReviewPanel/AlarmReviewPanel.test.tsx "" |  | test |
| FE-194 | Must | PASS |  | frontend/tests/e2e/study-team.spec.ts ""; frontend/tests/pages/study.test.tsx "" | E2E in CI playwright on 23e558b (success) | test |
| FE-195 | Must | PASS |  | frontend/components/ReviewOutcomesTable/ReviewOutcomesTable.test.tsx "ReviewOutcomesTable"; frontend/tests/pages/study.test.tsx "" |  | test |
| FE-200 | Must | PASS |  | frontend/.eslintrc.json | extends next/core-web-vitals, @typescript-eslint/recommended, jsx-a11y/strict, prettier last; 3 rules set | inspection |
| FE-201 | Should | PASS |  | frontend/.prettierrc | printWidth 100, singleQuote false, trailingComma all, semi true | inspection |
| FE-202 | Must | PASS |  | .github/workflows/ci.yml:194-199; .github/workflows/e2e.yml:11-13,31-89 | npm ci, lint, typecheck, format:check, test:coverage, build in order; Playwright on PRs to main | inspection |
| FE-203 | Must | PASS |  | frontend/package.json:12 (next lint --max-warnings 0); .github/workflows/ci.yml:195-199 | lint gate at zero warnings plus typecheck and build in CI | inspection |
| FE-204 | Should | PASS |  | scripts/ci/check-bundle.mjs:1-14; .github/workflows/ci.yml:200 | CI fails any dashboard route over 300 KB gzip first-load JS | inspection |

### 05 Backend API TRD

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| API-001 | Must | PASS |  | backend/main.py:68; backend/requirements.txt:3 (fastapi==0.115.12); render.yaml:52,98; backend/Dockerfile:36 | create_app factory; deployed uvicorn commands carry --proxy-headers --forwarded-allow-ips="*" | inspection |
| API-002 | Must | PASS |  | tests/integration/api/test_health.py::test_routes_only_under_api_v1 |  | test |
| API-003 | Must | FAIL | S4 | backend/api/ingest.py:75-95; backend/api/residents.py:84-96,108-112 | No SQL in routers, but some handlers call several service functions/do logic (ingest_batch: name_map+parse_csv_batch+ingest_batch; checkins paging in router) | inspection |
| API-004 | Must | PASS |  | pyproject.toml:50-54 (import-linter forbids fastapi in services); .github/workflows/ci.yml:78; backend/core/errors.py | No fastapi import in backend/services; expected failures raise AppError subclasses (ValueError only for programming errors) | inspection |
| API-005 | Must | FAIL | S4 | backend/services/pipeline_persistence.py:20,95-180; backend/services/engine_read.py:17,88-170; backend/services/pipeline_runner.py:28,145-180 | Services other than analytics_summary build SQLAlchemy select/delete queries directly instead of via repositories; behaviour correct | inspection |
| API-006 | Must | PASS |  | backend/services/pipeline_runner.py:377; backend/services/analytics_summary.py:24; backend/services/alert_service.py:17 | run_pipeline is the only engine entry for runs; reads use build_analytics_summary and leaning_most; stage services are stubs | inspection |
| API-007 | Must | PASS |  | backend/core/config.py:46-50; backend/requirements.txt:5,10; backend/api/sessions.py:44-52; backend/api/ingest.py:75 | Sync SQLAlchemy 2.0/psycopg3; handlers def; async only for ingest body read + run_in_threadpool as sanctioned by TRD 05 §8 line 514 | inspection |
| API-008 | Must | PASS |  | backend/api/{alarms,analytics,health,residents,sessions}.py; backend/services/{baseline,cusum,ingestion,morning_adjustment,scoring,speaker_screen,validation}.py | All skeleton files kept under original names; baseline/cusum/scoring/speaker_screen/morning_adjustment are docstring-only thin adapters (ARC-052) | inspection |
| API-010 | Must | PASS |  | backend/core/config.py:290-293 | get_settings is @lru_cache(maxsize=1) over build_settings() | inspection |
| API-011 | Must | PASS |  | tests/unit/backend/test_deps.py::test_get_db_commits_on_success_and_closes; tests/unit/backend/test_deps.py::test_get_db_rolls_back_on_exception_and_closes |  | test |
| API-012 | Must | PASS |  | tests/integration/api/test_auth.py::test_deactivated_user_token_stops_working; tests/security/test_tokens.py::test_token_of_a_deactivated_user_is_invalid |  | test |
| API-013 | Must | PASS |  | tests/integration/api/test_role_checks.py::test_role_comes_from_the_database_not_the_token |  | test |
| API-014 | Must | PASS |  | backend/services/auth_service.py:128-137; backend/core/security.py:91; backend/api/deps.py:236-242; tests/security/test_api_keys.py::test_key_without_ingest_scope_is_forbidden | SHA-256 lookup of active key, 401 API_KEY_INVALID, 403 FORBIDDEN on missing scope (implemented in authorize()) | inspection |
| API-015 | Must | PASS |  | backend/api/deps.py:158-188,212-245; backend/api/permissions.py:35 | authorize() accepts API key or admin JWT for POST /ingest and returns Principal(actor_type, actor_id, device_id via key) | inspection |
| API-016 | Must | PASS |  | tests/integration/api/test_residents.py::test_invalid_query_parameters; tests/unit/backend/test_deps.py::test_pagination_defaults_and_bounds |  | test |
| API-017 | Must | PASS |  | tests/integration/api/conftest.py:96; tests/integration/api/test_alerts.py:210; tests/integration/api/test_health.py:30 | Tests override get_settings/get_clock/get_engine via app.dependency_overrides | inspection |
| API-020 | Must | PASS |  | tests/integration/api/test_auth.py::test_valid_login_returns_a_bearer_token |  | test |
| API-021 | Must | PASS |  | tests/integration/api/test_auth.py::test_failed_logins_are_indistinguishable |  | test |
| API-022 | Must | PASS |  | tests/integration/api/test_auth.py::test_valid_login_returns_a_bearer_token |  | test |
| API-023 | Must | PASS |  | tests/integration/api/test_auth.py::test_me_and_logout |  | test |
| API-024 | Must | PASS |  | tests/integration/api/test_auth.py::test_bad_tokens_are_refused_with_a_bearer_challenge; tests/security/test_tokens.py::test_token_61_minutes_old_is_expired; tests/security/test_tokens.py::test_altered_and_unsigned_tokens_are_invalid |  | test |
| API-025 | Must | PASS |  | tests/integration/api/test_auth.py::test_me_and_logout |  | test |
| API-030 | Must | PASS |  | tests/integration/api/test_sessions.py::test_only_an_ingest_key_may_post |  | test |
| API-031 | Must | PASS |  | backend/api/sessions.py:24-52; backend/api/ingest.py:30-40,88; tests/integration/api/test_sessions.py::test_unknown_resident_is_rejected_and_stored | Raw body read with await request.body(); openapi_extra references IngestRecord; rejection stored verbatim | inspection |
| API-032 | Must | PASS |  | backend/services/ingestion.py:312-364; tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed | Test asserts raw ingest_batch_id None, api_key_id set, 0 ingest_batches rows; no audit row on single ingest | inspection |
| API-033 | Must | PASS |  | backend/services/validation.py:198-217; tests/integration/api/test_ingest.py::test_mapped_header_is_accepted; tests/unit/backend/services/test_validation.py::test_name_mapping | feature_name_map applied before validation | inspection |
| API-034 | Must | PASS |  | backend/services/validation.py:198-230; tests/unit/backend/services/test_validation.py::test_reject_rules; tests/integration/api/test_sessions.py::test_extra_field_and_audio_are_refused | Hand-written validator collects one error per field incl. extra_forbidden, ranges, timestamp format -> 422 VALIDATION_ERROR | inspection |
| API-035 | Must | PASS |  | backend/services/validation.py:218-230; tests/integration/api/test_sessions.py::test_version_and_timestamp_problems | schema_version 0.2 -> 422 UNSUPPORTED_SCHEMA_VERSION | inspection |
| API-036 | Must | PASS |  | tests/unit/backend/services/test_validation.py::test_roster_checks_and_request_codes |  | test |
| API-037 | Must | PASS |  | tests/unit/backend/services/test_validation.py::test_roster_checks_and_request_codes |  | test |
| API-038 | Must | PASS |  | tests/integration/api/test_sessions.py::test_withdrawn_resident; tests/unit/backend/services/test_validation.py::test_roster_checks_and_request_codes |  | test |
| API-039 | Must | PASS |  | tests/unit/backend/services/test_validation.py::test_roster_checks_and_request_codes |  | test |
| API-040 | Must | PASS |  | tests/integration/api/test_sessions.py::test_device_bound_key_refuses_another_device |  | test |
| API-041 | Must | PASS |  | tests/integration/api/test_sessions.py::test_unknown_resident_is_rejected_and_stored |  | test |
| API-042 | Must | PASS |  | tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed |  | test |
| API-043 | Must | PASS |  | tests/integration/pipeline/test_concurrent_ingest.py::test_concurrent_posts_of_one_session_id |  | test |
| API-044 | Must | PASS |  | tests/integration/api/test_sessions.py::test_repeat_session_id_is_a_duplicate |  | test |
| API-045 | Must | PASS |  | backend/services/ingestion.py:283-291,351-353; tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed | Scope = resident + residents assigned to the device on local date; trigger ingest; synchronous run | inspection |
| API-046 | Must | PASS |  | tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed |  | test |
| API-047 | Must | PASS |  | tests/integration/api/test_sessions.py::test_failed_run_answers_pending |  | test |
| API-048 | Must | PASS |  | backend/core/middleware.py:167-200; backend/api/ingest.py:84-90; backend/services/validation.py:400; tests/integration/api/test_ingest.py::test_legacy_file_is_refused | JSON or multipart CSV only; other media 415; CSV header must be SRC-05 set after mapping | inspection |
| API-049 | Must | PASS |  | backend/api/permissions.py:35; backend/api/ingest.py:86-89; backend/services/ingestion.py:384-387; tests/integration/api/test_ingest.py::test_src05_upload | Test asserts source csv_upload and uploaded_by admin id | inspection |
| API-050 | Must | PASS |  | tests/integration/api/test_ingest.py::test_envelope_errors_store_nothing |  | test |
| API-051 | Must | PASS |  | tests/integration/api/test_ingest.py::test_record_errors_do_not_fail_the_batch |  | test |
| API-052 | Must | PASS |  | tests/integration/api/test_ingest.py::test_src05_upload |  | test |
| API-053 | Must | PASS |  | tests/integration/api/test_ingest.py::test_src05_upload |  | test |
| API-054 | Must | PASS |  | tests/integration/api/test_ingest.py::test_batch_detail_and_roles |  | test |
| API-055 | Should | PASS |  | analytics/pipeline.py:280-299 | device_assignment_mismatch RunWarning with resident_code, session_id and devices in detail; record still accepted | inspection |
| API-056 | Must | PASS |  | tests/integration/api/test_sessions.py::test_logs_carry_no_feature_value_or_key |  | test |
| API-060 | Must | PASS |  | tests/integration/pipeline/test_nightly_run.py::test_one_run_per_local_night_across_dst |  | test |
| API-061 | Must | PASS |  | tests/integration/pipeline/test_nightly_run.py::test_one_run_per_local_night_across_dst |  | test |
| API-062 | Must | PASS |  | backend/jobs/nightly_run.py:95-118; render.yaml:69-80; tests/integration/pipeline/test_nightly_run.py | Scope all, trigger nightly, as-of via runner; exit 1 on failed run | inspection |
| API-063 | Must | PASS |  | tests/integration/api/test_pipeline.py::test_run_lifecycle_and_snapshot |  | test |
| API-064 | Must | PASS |  | backend/services/pipeline_runner.py:383-386,408-409; backend/services/pipeline_persistence.py:103; backend/core/db.py:121-124; tests/integration/db/test_advisory_locks.py | Per-resident pg_advisory_xact_lock in ascending code order; only xact locks (device_alerts/nightly keys sanctioned by DB-021) | inspection |
| API-065 | Must | PASS |  | tests/integration/api/test_pipeline.py::test_admin_starts_a_manual_run; tests/integration/api/test_pipeline.py::test_full_run_in_progress_is_409; tests/integration/api/test_pipeline.py::test_scheduler_key_runs_nightly_once_per_local_date |  | test |
| API-135 | Must | PASS |  | tests/integration/api/test_pipeline.py::test_as_of_precedence |  | test |
| API-066 | Must | PASS |  | tests/integration/api/test_pipeline.py::test_production_refuses_other_profiles |  | test |
| API-058 | Must | PASS |  | backend/core/config.py:201-203,305-317; tests/unit/backend/core/test_config.py::test_cfg_06_production_refuses_test_profile | Startup and nightly (load_settings_or_exit) refuse test_v0_1 in production and exit non-zero | inspection |
| API-059 | Must | PASS |  | backend/core/config.py:191-195,210-217; tests/unit/backend/core/test_config.py::test_staging_requires_sslmode_but_local_does_not | Staging/production refuse DATABASE_URL without sslmode=require/verify-full | inspection |
| API-067 | Must | PASS |  | tests/integration/api/test_pipeline.py::test_get_run |  | test |
| API-128 | Must | PASS |  | backend/services/pipeline_persistence.py:203-237,322-358,361-392; tests/integration/pipeline/test_runner_persistence.py::test_second_run_changes_nothing; ::test_reviews_and_snooze_survive_a_rerun | Epochs/alerts/data_alerts upserted by natural keys; alert ids, reviews and snooze survive reruns | inspection |
| API-068 | Should | PASS |  | tests/integration/api/test_pipeline.py::test_stale_running_run_is_abandoned |  | test |
| API-069 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_meta_uses_the_latest_succeeded_run; tests/integration/api/test_ui_fixture_ds07.py::test_as_of_without_clock_override |  | test |
| API-057 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_meta_uses_the_latest_succeeded_run |  | test |
| API-070 | Must | PASS |  | tests/integration/api/test_residents.py::test_invalid_query_parameters |  | test |
| API-071 | Must | PASS |  | backend/services/resident_service.py:115-122,180-190; tests/integration/api/test_ui_fixture_ds07.py::test_resident_list | Order R09,R10,R03,R08,R01,R02,R04,R05,R06,R07 asserted on DS-07 | inspection |
| API-072 | Must | PASS |  | tests/integration/api/test_residents.py::test_other_sort_orders |  | test |
| API-073 | Must | PASS |  | tests/integration/api/test_residents.py::test_filters_and_paging |  | test |
| API-074 | Must | PASS |  | backend/repositories/read_models.py:83-95; tests/integration/api/test_ui_fixture_ds07.py::test_resident_list | last_30_days used/set_aside/quarantined/missed asserted per resident; duplicates excluded | inspection |
| API-075 | Must | PASS |  | tests/integration/api/test_residents.py::test_detail; tests/integration/api/test_residents.py::test_unknown_resident_is_404 |  | test |
| API-076 | Must | PASS |  | tests/integration/api/test_residents.py::test_detail |  | test |
| API-077 | Must | PASS |  | tests/integration/api/test_residents.py::test_checkin_log; tests/integration/api/test_residents.py::test_same_date_events_follow_ux_141; tests/integration/api/test_residents.py::test_checkin_log_filters |  | test |
| API-138 | Must | PASS |  | backend/services/resident_service.py:111-160; tests/integration/api/test_ui_fixture_ds07.py::test_resident_list; tests/integration/api/test_residents.py:46-80 | needs_attention R03/R08 with reasons, alarm_reviewed false R09/R10, R07 restart_cause device, window asserted | inspection |
| API-078 | Must | PASS |  | tests/integration/api/test_residents.py::test_features |  | test |
| API-079 | Must | PASS |  | tests/integration/api/test_scores.py::test_scores_json; tests/integration/api/test_scores.py::test_scores_parameters |  | test |
| API-129 | Must | PASS |  | tests/integration/api/test_scores.py::test_scores_csv; tests/integration/api/test_scores.py::test_csv_row_limit |  | test |
| API-080 | Must | PASS |  | tests/integration/api/test_alerts.py::test_alert_list; tests/integration/pipeline/test_runner_persistence.py::test_alerts_endpoint_leaning_most |  | test |
| API-081 | Must | PASS |  | tests/integration/api/test_alerts.py::test_reviews |  | test |
| API-130 | Must | PASS |  | tests/integration/api/test_alerts.py::test_data_problem_review_creates_then_links |  | test |
| API-131 | Must | PASS |  | backend/api/alarms.py:88-102; backend/api/permissions.py:45; backend/repositories/alert_repository.py:203; tests/integration/api/test_alerts.py:130 | All staff roles; newest first (created_at desc) with limit/offset | inspection |
| API-132 | Must | PASS |  | tests/integration/api/test_alerts.py::test_snooze |  | test |
| API-082 | Must | PASS |  | tests/integration/api/test_alerts.py::test_invalid_reviews_write_nothing; tests/integration/api/test_alerts.py::test_refusals |  | test |
| API-083 | Must | PASS |  | tests/integration/api/test_notes.py::test_superseding_and_listing |  | test |
| API-084 | Must | PASS |  | tests/integration/api/test_notes.py::test_create_note; tests/integration/api/test_notes.py::test_invalid_notes |  | test |
| API-085 | Must | PASS |  | tests/integration/api/test_notes.py::test_alert_and_supersedes_ownership |  | test |
| API-133 | Must | PASS |  | tests/integration/api/test_alerts.py::test_data_alert_list |  | test |
| API-086 | Must | PASS |  | tests/integration/api/test_devices.py::test_device_panel; tests/integration/api/test_ui_fixture_ds07.py::test_devices |  | test |
| API-087 | Must | PASS |  | tests/integration/api/test_analytics.py::test_summary; tests/integration/pipeline/test_runner_persistence.py::test_analytics_endpoint_after_the_run |  | test |
| API-136 | Must | PASS |  | tests/integration/api/test_analytics.py::test_production_profile; tests/integration/api/test_analytics.py::test_read_only_engine; tests/unit/backend/test_ground_truth_boundary.py::test_only_the_summary_reads_the_answer_key |  | test |
| API-134 | Must | PASS |  | tests/integration/api/test_pipeline.py::test_list_runs |  | test |
| API-137 | Must | PASS |  | tests/integration/api/test_config_ui.py::test_ui_config |  | test |
| API-088 | Must | PASS |  | tests/integration/api/test_scores.py::test_baselines |  | test |
| API-089 | Must | PASS |  | tests/integration/api/test_admissions.py::test_empty_state |  | test |
| API-090 | Should | PASS |  | tests/integration/api/test_admissions.py::test_comparison_only_for_new_admissions |  | test |
| API-091 | Must | PASS |  | tests/integration/api/test_users.py::test_create_user; tests/integration/api/test_users.py::test_duplicate_email; tests/integration/api/test_users.py::test_update_user |  | test |
| API-092 | Must | PASS |  | tests/integration/api/test_users.py::test_update_user; tests/unit/backend/services/test_user_service.py::test_last_active_admin_cannot_be_removed |  | test |
| API-093 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_reversed_date_range_is_invalid; tests/integration/api/test_residents.py::test_checkin_log_filters; tests/integration/api/test_scores.py::test_scores_parameters |  | test |
| API-094 | Must | PASS |  | backend/schemas/common.py:27-30; tests/integration/api/test_ui_fixture_ds07.py::test_as_of_without_clock_override; ::test_resident_list | as_of serialised 2026-10-30T20:00:00Z; last_checkin_local with facility offset; local_date YYYY-MM-DD | inspection |
| API-095 | Must | PASS |  | tests/unit/backend/core/test_errors.py::test_catalogue_equals_trd_05 |  | test |
| API-096 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_unhandled_exception_is_a_generic_500 |  | test |
| API-097 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_database_unreachable_is_503_with_retry_after |  | test |
| API-098 | Must | PASS |  | tests/integration/api/test_rate_limits.py::test_sixth_login_in_a_minute_is_rate_limited |  | test |
| API-100 | Must | PASS |  | tests/integration/api/test_devices.py::test_device_paging |  | test |
| API-101 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_cors_allows_only_configured_origins; tests/security/test_cors.py::test_preflight; tests/security/test_deployed_cors.py::test_deployed_cors_admits_only_its_own_site |  | test |
| API-102 | Must | PASS |  | tests/integration/api/test_rate_limits.py::test_other_endpoints_allow_300_a_minute_per_user; tests/integration/api/test_rate_limits.py::test_ingest_routes_are_not_also_capped_by_the_default_limit; tests/integration/api/test_rate_limits.py::test_login_is_not_also_capped_by_the_default_limit |  | test |
| API-103 | Must | PASS |  | tests/integration/api/test_auth.py::test_audit_ip_comes_from_a_valid_forwarded_address; tests/integration/api/test_rate_limits.py::test_login_limit_keys_on_the_left_most_forwarded_address |  | test |
| API-104 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_body_size_and_media_type_limits; tests/integration/api/test_http_middleware.py::test_streamed_body_over_the_limit_is_rejected |  | test |
| API-105 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_request_id_is_echoed_or_generated; tests/integration/api/test_http_middleware.py::test_errors_carry_the_request_id_and_problem_shape; tests/unit/backend/core/test_logging.py::test_request_id_acceptance |  | test |
| API-139 | Must | PASS |  | backend/core/middleware.py:152-157; tests/integration/api/test_sessions.py::test_extra_field_and_audio_are_refused; tests/security/test_no_audio.py | audio/* refused 415 in middleware before routing, any method | inspection |
| API-106 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_security_headers_and_hsts; tests/security/test_transport_and_secrets.py::test_backend_sends_hsts_in_staging_and_production |  | test |
| API-107 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_one_access_record_per_request_with_levels |  | test |
| API-110 | Must | PASS |  | tests/integration/api/test_health.py::test_tst_054_health_ok_with_database_up |  | test |
| API-111 | Must | PASS |  | tests/integration/api/test_health.py::test_tst_054_health_degraded_with_database_down |  | test |
| API-112 | Must | PASS |  | tests/integration/api/test_rate_limits.py::test_health_is_never_rate_limited |  | test |
| API-113 | Must | PASS |  | tests/contract/test_openapi_contract.py::test_served_document_and_docs; tests/integration/api/test_health.py::test_routes_only_under_api_v1 |  | test |
| API-114 | Must | PASS |  | backend/api/openapi.py:88-92,141-142; docs/api_reference/openapi.json | bearerAuth (http bearer JWT) and apiKeyAuth (header X-API-Key) declared and attached per operation | inspection |
| API-120 | Must | PASS |  | tests/performance/test_api_latency.py::test_health_p95 | Performance test: budget subset in CI backend-test; nightly budgets run locally (CHECKPOINT_8 §5 rows 3-4) | test |
| API-121 | Must | PASS |  | tests/performance/test_api_latency.py::test_read_endpoints_p95_on_ds08 | Performance test: budget subset in CI backend-test; nightly budgets run locally (CHECKPOINT_8 §5 rows 3-4) | test |
| API-122 | Must | PASS |  | tests/performance/test_api_latency.py::test_post_sessions_p95_pr_scope; tests/performance/test_api_latency.py::test_post_sessions_p95_200_requests | Performance test: budget subset in CI backend-test; nightly budgets run locally (CHECKPOINT_8 §5 rows 3-4) | test |
| API-123 | Must | PASS |  | tests/integration/api/test_ingest.py::test_batch_duplicates_and_statement_count; tests/performance/test_api_latency.py::test_ingest_src05_accepted_and_processed |  | test |
| API-124 | Must | PASS |  | tests/performance/test_pipeline_runtime.py::test_ds08_full_rebuild_within_120_s; tests/performance/test_pipeline_runtime.py::test_src05_full_rebuild_within_30_s | Performance test: budget subset in CI backend-test; nightly budgets run locally (CHECKPOINT_8 §5 rows 3-4) | test |
| API-125 | Must | PASS |  | tests/unit/backend/core/test_db.py::test_pool_settings; tests/unit/backend/core/test_db.py::test_connections_disable_prepared_statements |  | test |

### 06 Database Design TRD

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| DB-001 | Must | PASS |  | tests/integration/db/test_raw_store.py::test_same_session_id_twice_gets_increasing_arrival_seq; tests/unit/backend/repositories/test_raw_session_repository.py::test_database_assigned_columns_are_refused; tests/unit/backend/repositories/test_raw_session_repository.py::test_insert_returns_id_and_sequence (+1 more) |  | test |
| DB-002 | Must | PASS |  | backend/services/ingestion.py:219-280; tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed; tests/integration/api/test_ingest.py::test_src05_upload | JSON payload == record; CSV payload holds cell strings (loudness_dbfs '-30.67') | inspection |
| DB-003 | Must | PASS |  | backend/services/ingestion.py:219-280; tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed; tests/integration/db/test_raw_store.py | Typed columns filled from validated values of the payload (loudness_dbfs equals payload value) | inspection |
| DB-004 | Must | PASS |  | tests/integration/test_schema_behaviour.py::test_ac_pgs_01_raw_sessions_update_fails_for_app; tests/integration/test_schema_behaviour.py::test_ac_pgs_01_raw_sessions_update_fails_for_owner; tests/unit/backend/repositories/test_raw_session_repository.py::test_repository_has_no_update_or_delete |  | test |
| DB-005 | Must | PASS |  | backend/services/ingestion.py:324-336; tests/integration/api/test_sessions.py::test_unknown_resident_is_rejected_and_stored | Invalid record -> 1 ingest_rejections row, 0 raw_sessions rows | inspection |
| DB-006 | Must | PASS |  | backend/services/pipeline_persistence.py:80-122; tests/integration/pipeline/test_runner_persistence.py::test_second_run_changes_nothing | Runner loads only raw_sessions typed cols, reference tables and config; rerun reproduces derived rows | inspection |
| DB-007 | Must | PASS |  | tests/unit/backend/test_db_inspection.py::test_ground_truth_is_not_referenced_by_the_pipeline_or_cli |  | test |
| DB-008 | Must | PASS |  | database/schema.sql:178-191,1472,1478,1538,1544 | Row UPDATE/DELETE and statement TRUNCATE triggers on raw_sessions and audit_logs raise EW001 (migrator purge GUC exception per PGS-018) | inspection |
| DB-009 | Must | PASS |  | database/schema.sql:2008,2021,2104,2125,2152,1940,1947,2042,2077; tests/integration/db/test_grants.py | echowell_app SELECT,INSERT on the six tables; no DELETE on alerts/data_alerts; no grant on evaluation_ground_truth | inspection |
| DB-010 | Must | PASS |  | tests/integration/api/test_notes.py::test_superseding_and_listing; tests/integration/db/test_grants.py::test_ac_pgs_13_every_fk_restricts_except_scores |  | test |
| DB-011 | Must | PASS |  | tests/integration/db/test_audit_writer.py::test_audit_row_shares_the_change_transaction |  | test |
| DB-012 | Must | PASS |  | tests/integration/db/test_migrations.py::test_alembic_check_reports_no_difference |  | test |
| DB-013 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_a_failing_resident_is_rolled_back_alone |  | test |
| DB-014 | Must | PASS |  | backend/services/pipeline_persistence.py:168-195 | Deletes scores/processed/ledger/cusum per resident; baselines, alerts, reviews, data_alerts, notes kept; frozen epochs kept | inspection |
| DB-015 | Must | PASS |  | backend/services/pipeline_persistence.py:203-237,181-184 | Epochs upserted on (resident, epoch_number) reusing id; ended_at updated; stale unfrozen epochs deleted | inspection |
| DB-016 | Must | PASS |  | tests/integration/db/test_repositories.py::test_epochs_sessions_ledger_baselines_scores; tests/integration/pipeline/test_runner_persistence.py::test_late_record_keeps_frozen_baselines |  | test |
| DB-017 | Must | PASS |  | backend/services/pipeline_persistence.py:211-222; backend/services/pipeline_runner.py:383-392 | EpochRenumberingBlockedError rolls back the resident txn and appends late_arrival 'epoch renumbering blocked' | inspection |
| DB-018 | Must | PASS |  | tests/integration/db/test_repositories.py::test_epochs_sessions_ledger_baselines_scores |  | test |
| DB-036 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_a_run_at_an_earlier_as_of_keeps_alert_history |  | test |
| DB-019 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_second_run_changes_nothing |  | test |
| DB-020 | Must | PASS |  | tests/integration/api/test_pipeline.py::test_run_lifecycle_and_snapshot; tests/integration/db/test_repositories.py::test_pipeline_runs |  | test |
| DB-021 | Must | PASS |  | tests/integration/db/test_advisory_locks.py::test_second_transaction_waits_for_the_first; tests/integration/db/test_advisory_locks.py::test_different_keys_do_not_block; tests/integration/db/test_advisory_locks.py::test_lock_is_released_at_commit (+5 more) |  | test |
| DB-022 | Must | PASS |  | backend/services/ingestion.py:337-338; tests/integration/api/test_sessions.py::test_failed_run_answers_pending | Raw insert committed before run; failed run leaves raw row (test asserts 1 raw row after failed run) | inspection |
| DB-023 | Must | PASS |  | analytics/day_ledger.py:36,53-54; tests/integration/pipeline/test_runner_persistence.py::test_full_run_on_src05 | Ledger from enrolled_on to min(as_of, withdrawn_on); 300 ledger rows asserted | inspection |
| DB-024 | Must | PASS |  | tests/integration/test_cli_seed.py::test_reset_refuses_the_production_profile; tests/integration/test_cli_seed.py::test_reset_leaves_config_and_one_audit_row |  | test |
| DB-025 | Must | PASS |  | backend/services/pipeline_persistence.py:433-446 | new_admission -> longitudinal one-way with system audit resident.cohort_changed {from,to,epoch_number} | inspection |
| DB-026 | Must | PASS |  | backend/alembic/versions/0001..0004; render.yaml pre-deploy migrate; tests/integration/test_schema_reference.py; tests/integration/db/test_migrations.py::test_alembic_check_reports_no_difference | Alembic is the only DDL path; database/schema.sql is the generated reference checked by test | inspection |
| DB-027 | Must | PASS |  | tests/integration/db/test_migrations.py::test_single_head_with_sequential_revisions |  | test |
| DB-028 | Must | PASS |  | tests/unit/backend/core/test_db.py::test_migrator_setup_statements |  | test |
| DB-029 | Must | PASS |  | tests/integration/db/test_migrations.py::test_tst_040_upgrade_downgrade_upgrade_round_trip |  | test |
| DB-030 | Must | PASS |  | backend/alembic/versions/0001_initial_schema.py; 0002..0004 (grep: no UPDATE/DELETE on raw_sessions/audit_logs) | Satisfied by inspection; the migration grep test named in the TRD is not present | inspection |
| DB-031 | Must | FAIL | S4 | .github/workflows/deploy-production.yml:9-11; specs/TRD/15_Deployment_and_DevOps_Spec.md:399; docs/deployment.md:161 | Deploy job does not create the branch; manual runbook step named pre-<short-sha> (DEP-063), not pre-migration-<git sha>; live part Block 4 | inspection |
| DB-032 | Must | PASS |  | database/schema.sql:255,392-396,412,611-617,737; tests/integration/test_schema_behaviour.py | Enums, CHECK, UNIQUE, partial unique and FK constraints duplicate app rules (AC-PGS behaviour tests) | inspection |
| DB-033 | Must | PASS |  | database/schema.sql (52 FKs; all ON DELETE RESTRICT except scores.processed_session_id CASCADE) | Verified by parsing schema.sql FK clauses | inspection |
| DB-034 | Must | PASS |  | database/schema.sql (15 CREATE TYPE); backend/alembic/versions/0001_initial_schema.py | 15 enum types; no label renamed/removed in migrations 0002-0004 | inspection |
| DB-035 | Must | PASS |  | tests/integration/db/test_master_tables.py::test_no_identifying_columns; tests/security/test_static_scans.py::test_no_personal_or_audio_columns |  | test |
| DB-040 | Must | FAIL | S3 | tests/performance/test_api_latency.py::test_read_endpoints_p95_on_ds08; tests/performance/test_overview_queries.py (absent) | No test measuring <=150 ms DB time for resident-list queries on DS-08; only end-to-end read p95 is tested | inspection |
| DB-041 | Must | PASS |  | tests/integration/db/test_read_models.py::test_activity_counts_exclude_duplicates_and_count_missed; tests/integration/db/test_read_models.py::test_window_never_starts_before_enrolment; tests/integration/db/test_read_models.py::test_seed_values_on_the_full_seed |  | test |
| DB-042 | Should | FAIL | S3 | tests/performance/ (no EXPLAIN / Seq Scan assertion) | No EXPLAIN check that resident-scoped queries avoid Seq Scan on DS-08 | inspection |
| DB-043 | Must | PASS |  | tests/integration/db/test_read_models.py::test_seed_values_on_the_full_seed |  | test |
| DB-044 | Must | PASS |  | tests/integration/api/test_devices.py::test_device_panel; tests/integration/db/test_read_models.py::test_device_silent_and_gap_days; tests/integration/db/test_read_models.py::test_seed_values_on_the_full_seed |  | test |
| DB-045 | Must | PASS |  | tests/integration/db/test_read_models.py::test_last_checkin_ignores_duplicates_and_converts_to_local; tests/integration/db/test_read_models.py::test_seed_values_on_the_full_seed |  | test |
| DB-065 | Must | PASS |  | tests/integration/db/test_read_models.py::test_restart_cause; tests/integration/db/test_read_models.py::test_seed_values_on_the_full_seed; tests/integration/db/test_read_models.py::test_restart_cause_firmware_then_software |  | test |
| DB-066 | Must | PASS |  | tests/integration/api/test_devices.py::test_device_panel; tests/integration/db/test_read_models.py::test_device_in_use_until; tests/integration/db/test_read_models.py::test_seed_values_on_the_full_seed (+1 more) |  | test |
| DB-046 | Should | FAIL | S4 | backend/alembic/versions/0003_ingest_batch_pipeline_run.py:24 | ingest_batches_pipeline_run_idx created without CONCURRENTLY/autocommit_block and not listed in TRD 06 query-pattern section (TRD 20 §4.13 SQL) | inspection |
| DB-047 | Should | PASS |  | tests/integration/db/test_indexes.py::test_fk_columns_lead_an_index |  | test |
| DB-048 | Must | PASS |  | database/schema.sql (no PARTITION); specs/TRD/06_Database_Design_TRD.md capacity table | No partitioning introduced; capacity analysis in TRD 06 | inspection |
| DB-049 | Should | PASS |  | tests/performance/test_pipeline_runtime.py::test_ds08_full_rebuild_within_120_s | Performance test: budget subset in CI backend-test; nightly budgets run locally (CHECKPOINT_8 §5 rows 3-4) | test |
| DB-050 | Must | PENDING BLOCK 4 |  | specs/TRD/22_Third_Party_Services_and_Hosting.md:115; docs/deployment.md:219-221 | Needs Neon plan restore window settings and restore drill on hosted DB; repo docs record the weekly dump policy | inspection |
| DB-051 | Should | PENDING BLOCK 4 |  | docs/deployment.md:221 | Restore drill on Neon not yet run; deployment.md has placeholder to record result | inspection |
| DB-052 | Must | PENDING BLOCK 4 |  | specs/TRD/22_Third_Party_Services_and_Hosting.md:115 | Provider-managed encryption at rest is a platform setting; MVP data is synthetic only | inspection |
| DB-053 | Must | PASS |  | tests/security/test_transport_and_secrets.py::test_every_database_url_needs_sslmode_require; tests/unit/backend/core/test_db.py::test_remote_urls_need_tls_outside_local_and_test |  | test |
| DB-054 | Must | PASS |  | docs/deployment.md:219; .github/workflows/*.yml (no pg_dump; artifacts are reports) | No workflow runs pg_dump or uploads dumps; runbook keeps dumps on PI-designated storage | inspection |
| DB-055 | Must | PASS |  | tests/integration/db/test_config_seed.py::test_ac_pgs_10_config_rows_per_profile |  | test |
| DB-056 | Must | PASS |  | tests/integration/test_cli_seed.py::test_seed_master_only_is_idempotent_and_hides_secrets; tests/integration/test_cli_seed.py::test_seed_refuses_without_the_secrets |  | test |
| DB-057 | Must | PASS |  | tests/integration/test_cli_seed.py::test_seed_master_only_is_idempotent_and_hides_secrets |  | test |
| DB-058 | Must | PASS |  | tests/integration/test_cli_pipeline.py::test_full_seed_ingests_src05_and_runs |  | test |
| DB-059 | Must | PASS |  | tests/integration/test_cli_seed.py::test_production_refuses_seed_and_reset |  | test |
| DB-060 | Should | PASS |  | tests/integration/db/test_repositories.py::test_resident_transitions |  | test |
| DB-061 | Must | PASS |  | render.yaml:69-80,113-124; backend/jobs/nightly_run.py | Only scheduled job is the nightly pipeline; no automated deletion/expiry (purge is a manual CLI command) | inspection |
| DB-062 | Must | PASS |  | tests/integration/test_cli_seed.py::test_withdraw_resident |  | test |
| DB-063 | Must | PASS |  | backend/services/validation.py:344-345; analytics/day_ledger.py:53-54; backend/services/resident_service.py:244; tests/integration/api/test_sessions.py::test_withdrawn_resident | 422 RESIDENT_WITHDRAWN 'resident withdrawn' stored as rejection; ledger capped at withdrawn_on; lists exclude by default | inspection |
| DB-064 | Should | PASS |  | tests/integration/test_cli_seed.py::test_purge_resident_removes_every_row_but_keeps_audit |  | test |

### 07 Analytics Engine TRD

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| ANL-001 | Must | PASS |  | tests/unit/test_repository_layout.py::test_analytics_has_exactly_the_trd07_modules |  | test |
| ANL-002 | Must | PASS |  | tests/unit/backend/test_import_boundary.py::test_analytics_imports_are_allowed |  | test |
| ANL-003 | Must | PASS |  | pyproject.toml:39-43; tests/unit/backend/test_import_boundary.py::test_analytics_imports_are_allowed; tests/unit/analytics/test_pipeline.py::test_deterministic_and_order_independent | No I/O, clock or random imports in analytics/; frozen dataclasses; deterministic | inspection |
| ANL-004 | Must | PASS |  | tests/unit/test_repository_layout.py::test_analytics_has_exactly_the_trd07_modules |  | test |
| ANL-005 | Must | PASS |  | tests/unit/backend/test_import_boundary.py::test_analytics_imports_are_allowed |  | test |
| ANL-006 | Must | PASS |  | analytics/pipeline.py:220-255 | run_pipeline calls stages in the fixed ANL-006 order | inspection |
| ANL-007 | Should | PASS |  | tests/unit/analytics/test_run_engine.py::test_run_engine_on_the_seed_files; tests/unit/analytics/test_run_engine.py::test_json_and_csv_rows_read_alike |  | test |
| ANL-008 | Must | PASS |  | tests/unit/analytics/test_module_tests_exist.py::test_tst_011_every_analytics_module_has_a_test_file |  | test |
| ANL-009 | Must | PASS |  | analytics/__init__.py:7-50; analytics/config.py:24 | Exports run_pipeline, PipelineConfig, PRODUCTION, TEST_V0_1, all contract dataclasses; ENGINE_VERSION = "0.1.0" | inspection |
| ANL-010 | Must | PASS |  | tests/unit/analytics/test_config.py::test_contracts_are_frozen_and_check_features |  | test |
| ANL-011 | Must | PASS |  | analytics/config.py (frozen slots dataclasses); analytics/pipeline.py:220-255 | Stages pass contract dataclasses; no pandas or dict records between stages | inspection |
| ANL-012 | Must | PASS |  | tests/unit/analytics/test_pipeline.py::test_src05_counts_and_sessions |  | test |
| ANL-013 | Must | PASS |  | tests/unit/analytics/test_config.py::test_contracts_are_frozen_and_check_features |  | test |
| ANL-014 | Must | PASS |  | tests/unit/analytics/test_pipeline.py::test_src05_counts_and_sessions |  | test |
| ANL-015 | Must | PASS |  | tests/unit/analytics/test_pipeline.py::test_records_after_as_of_are_excluded |  | test |
| ANL-016 | Must | PASS |  | backend/services/pipeline_persistence.py:94-133; analytics/day_ledger.py:39-50 | load_inputs adds device-sharing residents for the ledger window | inspection |
| ANL-017 | Must | PASS |  | tests/validation/test_global_checks.py::test_vc_g02_annotated_sessions; tests/validation/test_r01_clean_control.py..test_r10_gradual_drift.py; tests/validation/comparator.py | R01-R10 answer-key comparison (tiers A/B) at 1e-6 / exact strings | inspection |
| ANL-018 | Must | PASS |  | tests/unit/analytics/test_pipeline.py::test_contract_violations |  | test |
| ANL-019 | Must | PASS |  | tests/integration/api/test_residents.py::test_before_any_run; tests/unit/analytics/test_pipeline.py::test_normal_conditions_do_not_raise |  | test |
| ANL-020 | Must | PASS |  | tests/unit/analytics/test_pipeline.py::test_deterministic_and_order_independent |  | test |
| ANL-021 | Must | PASS |  | tests/unit/analytics/test_pipeline.py::test_detect_late_arrivals_in_order_input_is_empty |  | test |
| ANL-022 | Must | PASS |  | analytics/robust_stats.py:17-23; analytics/composite_score.py:14-18; analytics/config.py:95 | float64 numpy.median; signed z summed in canonical order; no round() in analytics | inspection |
| ANL-023 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_second_run_changes_nothing |  | test |
| ANL-024 | Must | PASS |  | tests/unit/analytics/test_pipeline.py::test_late_arrival_leaves_r01_unchanged |  | test |
| ANL-025 | Must | PASS |  | tests/unit/analytics/test_epoch_detection.py::test_late_record_takes_the_previous_epoch; tests/unit/analytics/test_pipeline.py::test_late_arrival_leaves_r01_unchanged; tests/unit/analytics/test_speaker_screen.py::test_late_record_reasons |  | test |
| ANL-026 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_late_record_keeps_frozen_baselines |  | test |
| ANL-027 | Must | PASS |  | tests/unit/analytics/test_pipeline.py::test_out_of_order_after_freeze_is_not_late |  | test |
| ANL-028 | Must | PASS |  | tests/unit/analytics/test_config.py::test_profiles_differ_only_in_profile_and_baseline_n |  | test |
| ANL-029 | Must | PASS |  | tests/unit/analytics/test_config.py::test_from_mapping_refuses; tests/unit/analytics/test_config.py::test_missing_key_is_refused |  | test |
| ANL-030 | Must | PASS |  | tests/unit/analytics/test_config.py::test_hash_covers_algorithm_keys_only |  | test |
| ANL-031 | Must | PASS |  | backend/services/config_service.py:33-55; backend/services/pipeline_runner.py:358-366,121-126; backend/core/config.py:202 | config_default_used, pipeline_config_invalid, test_v0_1 refused in production at startup and on POST /pipeline/run | inspection |
| ANL-032 | Must | PASS |  | tests/integration/test_cli_pipeline.py::test_rebuild_reproduces_identical_derived_tables; tests/integration/test_cli_pipeline.py::test_set_config_then_rebuild |  | test |
| ANL-033 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_full_run_on_src05; tests/integration/test_cli_pipeline.py::test_rebuild_reproduces_identical_derived_tables |  | test |
| ANL-034 | Must | PASS |  | backend/services/pipeline_runner.py:383-386; backend/services/pipeline_persistence.py:103; tests/integration/db/test_advisory_locks.py | Per-resident xact lock at start of each resident txn, ascending resident_code | inspection |
| ANL-035 | Must | PASS |  | backend/services/pipeline_persistence.py:80-91 | RawRecord built from typed raw_sessions columns (timestamptz -> aware UTC), never payload | inspection |
| ANL-036 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_full_run_on_src05 |  | test |
| ANL-037 | Must | PASS |  | tests/unit/analytics/test_pipeline.py::test_frozen_baselines_win_and_mismatch_warns |  | test |
| ANL-038 | Must | PASS |  | backend/services/pipeline_persistence.py:203-237; backend/services/pipeline_runner.py:391-392 | Epoch upsert reuses id; renumbering of frozen epoch blocked with late_arrival warning | inspection |
| ANL-039 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_reviews_and_snooze_survive_a_rerun |  | test |
| ANL-040 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_full_run_on_src05 |  | test |
| ANL-041 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_a_failing_resident_is_rolled_back_alone |  | test |
| ANL-042 | Must | PASS |  | tests/validation/comparator.py:22; tests/validation/answer_key.py:21; tests/validation/tier_b.py:79-86 | Workbook labels mapped to engine values (rings/composite/yes-no) in validation incl. GET /analytics/baselines | inspection |
| ANL-043 | Must | PASS |  | backend/services/ingestion.py:351-364; tests/integration/api/test_sessions.py::test_failed_run_answers_pending | Sync run after commit, trigger ingest; failed run -> 201 pending, record stays | inspection |
| ANL-044 | Must | PASS |  | backend/api/ingest.py:90-94; backend/services/ingestion.py:413-422; tests/integration/api/test_ingest.py::test_src05_upload | One BackgroundTasks run for first-arrival scope with co-assigned residents, trigger ingest | inspection |
| ANL-045 | Must | PASS |  | tests/integration/pipeline/test_nightly_run.py::test_one_run_per_local_night_across_dst |  | test |
| ANL-046 | Must | PASS |  | backend/services/pipeline_runner.py:112-118; backend/api/permissions.py:54; backend/core/config.py:204-205 | as_of precedence explicit -> PIPELINE_AS_OF (refused in production) -> now; admin JWT or pipeline:run key | inspection |
| ANL-047 | Must | PASS |  | tests/performance/test_pipeline_runtime.py::test_pipeline_on_src05_within_5_s; tests/unit/analytics/test_pipeline.py::test_src05_runs_within_five_seconds |  | test |
| ANL-048 | Must | PASS |  | tests/performance/test_api_latency.py::test_ingest_src05_accepted_and_processed; tests/performance/test_pipeline_runtime.py::test_ds08_full_rebuild_within_120_s; tests/performance/test_pipeline_runtime.py::test_src05_full_rebuild_within_30_s | Performance test: budget subset in CI backend-test; nightly budgets run locally (CHECKPOINT_8 §5 rows 3-4) | test |
| ANL-049 | Must | PASS |  | tests/performance/test_api_latency.py::test_post_sessions_p95_pr_scope; tests/performance/test_api_latency.py::test_post_sessions_p95_200_requests | Performance test: budget subset in CI backend-test; nightly budgets run locally (CHECKPOINT_8 §5 rows 3-4) | test |
| ANL-050 | Should | PASS |  | analytics/robust_stats.py:17-26; analytics/cusum_engine.py:16-33 | numpy robust stats; linear per-resident stages by inspection; late-arrival exception as TRD | inspection |
| ANL-051 | Must | PASS |  | tests/unit/analytics/test_config.py::test_errors_and_warning_codes |  | test |
| ANL-052 | Must | PASS |  | tests/unit/analytics/test_config.py::test_errors_and_warning_codes |  | test |
| ANL-053 | Must | PASS |  | backend/services/pipeline_runner.py:251-254,293-314 | pipeline_run_started/succeeded/failed with required fields; pipeline_warning per warning (ERROR for baseline_mismatch); no _finished event | inspection |
| ANL-054 | Must | PASS |  | backend/services/pipeline_runner.py:293-314; tests/security/test_data_minimisation.py::test_responses_and_logs_hold_study_ids_only | Logs hold only study IDs and run metadata; test checks no feature values logged | inspection |
| ANL-055 | Should | PASS |  | analytics/morning_offset.py:1-37; analytics/config.py:400 | Offsets read only from PipelineConfig.morning_offsets; no estimator inside run_pipeline | inspection |
| ANL-056 |  | NOT APPLICABLE |  | specs/TRD/07_Analytics_Engine_TRD.md:394 | May; future EWMA (OQ-18), explicitly not implemented in v0.1 | inspection |
| ANL-057 |  | NOT APPLICABLE |  | specs/TRD/07_Analytics_Engine_TRD.md:395 | May; facility_norms.py created only when OQ-08 resolved (post-MVP) | inspection |
| ANL-058 | Should | PASS |  | analytics/config.py:73-96; analytics/composite_score.py:14-18; tests/unit/analytics/test_feature_specs.py | Composite keys/signs derived from FEATURES; no stage code change needed | inspection |
| ANL-059 | Must | PASS |  | analytics/data_alerts.py; analytics/pipeline.py:252; tests/unit/analytics/test_data_alerts.py::test_src05_exactly_four_alerts_in_order | Data alerts recomputed every run by generate_data_alerts | inspection |
| ANL-060 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_a_run_at_an_earlier_as_of_keeps_alert_history |  | test |
| ANL-061 | Must | PASS |  | tests/unit/analytics/test_aggregates.py::test_src05_kpis |  | test |
| ANL-062 | Must | PASS |  | tests/unit/analytics/test_aggregates.py::test_src05_kpis |  | test |
| ANL-063 | Must | PASS |  | tests/unit/analytics/test_aggregates.py::test_pct_half_up_integer |  | test |
| ANL-064 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_runner_never_reads_the_answer_key |  | test |
| ANL-065 | Must | PASS |  | backend/services/analytics_summary.py:100,114 | not_reviewed_count computed at response time from open alerts | inspection |

### 08 Baseline and Scoring Algorithm Spec

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| BSC-001 | Must | PASS |  | tests/unit/analytics/test_robust_stats.py::test_vectors |  | test |
| BSC-002 | Must | PASS |  | tests/unit/analytics/test_robust_stats.py::test_vectors |  | test |
| BSC-003 | Must | PASS |  | tests/unit/analytics/test_baseline_builder.py::test_pause_floor_rows; tests/unit/analytics/test_robust_stats.py::test_vectors |  | test |
| BSC-004 | Must | PASS |  | tests/unit/analytics/test_baseline_builder.py::test_pause_floor_rows; tests/unit/analytics/test_robust_stats.py::test_vectors; tests/unit/analytics/test_robust_stats.py::test_floor_equal_to_scaled_mad_is_not_applied |  | test |
| BSC-005 | Must | PASS |  | tests/unit/analytics/test_robust_stats.py::test_refuses_empty_or_non_finite |  | test |
| BSC-006 | Must | PASS |  | tests/unit/analytics/test_epoch_detection.py::test_set_aside_record_starts_an_epoch |  | test |
| BSC-007 | Must | PASS |  | tests/unit/analytics/test_epoch_detection.py::test_device_firmware_and_software_changes; tests/unit/analytics/test_epoch_detection.py::test_returning_key_gets_a_new_epoch |  | test |
| BSC-008 | Must | PASS |  | tests/unit/analytics/test_epoch_detection.py::test_src05_r07_epochs |  | test |
| BSC-009 | Must | PASS |  | tests/unit/analytics/test_epoch_detection.py::test_time_order_and_duplicates |  | test |
| BSC-010 | Must | PASS |  | analytics/cusum_engine.py:18-22; tests/unit/analytics/test_cusum_engine.py::test_epochs_have_their_own_tally; tests/unit/analytics/test_baseline_builder.py::test_membership_and_forming_epochs | Reference list, baseline and CUSUM keyed per (resident, epoch) | inspection |
| BSC-011 | Must | PASS |  | analytics/speaker_screen.py; tests/unit/analytics/test_speaker_screen.py::test_src05_r05_quarantines_use_the_first_n | pending_screen records screened in time order on raw values | inspection |
| BSC-012 | Must | PASS |  | tests/unit/analytics/test_speaker_screen.py::test_src05_r05_quarantines_use_the_first_n |  | test |
| BSC-013 | Must | PASS |  | tests/unit/analytics/test_speaker_screen.py::test_no_screen_below_screen_min_n |  | test |
| BSC-014 | Must | PASS |  | analytics/zscore_calculator.py; tests/unit/analytics/test_zscore_calculator.py::test_zero_spread_gives_zero | z = (x-median)/spread with floor; 0.0 when spread is 0 | inspection |
| BSC-015 | Must | PASS |  | tests/unit/analytics/test_speaker_screen.py::test_quarantine_needs_f0_and_two_composite_features |  | test |
| BSC-016 | Must | PASS |  | tests/unit/analytics/test_speaker_screen.py::test_quarantine_needs_f0_and_two_composite_features; tests/unit/analytics/test_speaker_screen.py::test_src05_r05_quarantines_use_the_first_n |  | test |
| BSC-017 | Must | PASS |  | tests/unit/analytics/test_speaker_screen.py::test_quarantine_needs_f0_and_two_composite_features |  | test |
| BSC-018 | Must | PASS |  | tests/unit/analytics/test_speaker_screen.py::test_src05_r05_quarantines_use_the_first_n |  | test |
| BSC-019 | Should | PASS |  | backend/services/pipeline_persistence.py:251-252; database/schema.sql:617 | screen_detail stored in processed_sessions for screened records | inspection |
| BSC-020 | Must | PASS |  | tests/unit/analytics/test_morning_offset.py::test_local_time_vectors |  | test |
| BSC-021 | Must | PASS |  | tests/unit/analytics/test_morning_offset.py::test_local_time_vectors |  | test |
| BSC-022 | Must | PASS |  | tests/unit/analytics/test_morning_offset.py::test_r06_day_1_adjustment |  | test |
| BSC-023 | Must | PASS |  | backend/services/pipeline_persistence.py:251-255; database/schema.sql:611; analytics/morning_offset.py:32-37 | adjusted_features (19 keys) stored for non-duplicates; baselines/scores use adjusted | inspection |
| BSC-024 | Must | PASS |  | tests/unit/analytics/test_morning_offset.py::test_src05_r06_mornings |  | test |
| BSC-025 | Must | PASS |  | tests/unit/analytics/test_baseline_builder.py::test_membership_and_forming_epochs |  | test |
| BSC-026 | Must | PASS |  | tests/unit/analytics/test_baseline_builder.py::test_freeze_points_skip_non_usable_records |  | test |
| BSC-027 | Must | PASS |  | tests/unit/analytics/test_baseline_builder.py::test_membership_and_forming_epochs |  | test |
| BSC-028 | Must | PASS |  | tests/unit/analytics/test_baseline_builder.py::test_freeze_points_skip_non_usable_records |  | test |
| BSC-029 | Must | PASS |  | tests/unit/analytics/test_baseline_builder.py::test_freeze_points_skip_non_usable_records |  | test |
| BSC-030 | Must | PASS |  | backend/services/pipeline_persistence.py:262-280; database/schema.sql:2021; analytics/config.py:578 | Baselines insert-only (app role SELECT,INSERT); deleted only by operator rebuild | inspection |
| BSC-031 | Must | PASS |  | tests/unit/analytics/test_baseline_builder.py::test_r09_worked_example |  | test |
| BSC-032 | Must | PASS |  | tests/unit/analytics/test_composite_score.py::test_r09_composite |  | test |
| BSC-033 | Must | PASS |  | tests/unit/analytics/test_baseline_builder.py::test_r09_worked_example |  | test |
| BSC-034 | Must | PASS |  | tests/unit/analytics/test_baseline_builder.py::test_twenty_rows_per_formed_epoch |  | test |
| BSC-035 | Must | PASS |  | tests/unit/analytics/test_zscore_calculator.py::test_zero_spread_gives_zero |  | test |
| BSC-036 | Must | PASS |  | tests/unit/analytics/test_composite_score.py::test_src05_scored_sessions |  | test |
| BSC-037 | Must | PASS |  | tests/integration/api/test_residents.py::test_features; tests/unit/analytics/test_zscore_calculator.py::test_r09_ringing_session_z |  | test |
| BSC-038 | Must | PASS |  | tests/unit/analytics/test_composite_score.py::test_r09_composite |  | test |
| BSC-039 | Must | PASS |  | tests/integration/api/test_residents.py::test_features; tests/unit/analytics/test_feature_specs.py::test_features_equal_trd_23 |  | test |
| BSC-040 | Must | PASS |  | tests/unit/analytics/test_pipeline.py::test_late_arrival_leaves_r01_unchanged; tests/unit/analytics/test_speaker_screen.py::test_late_record_reasons |  | test |
| BSC-041 | Must | PASS |  | tests/unit/analytics/test_pipeline.py::test_late_arrival_leaves_r01_unchanged |  | test |
| BSC-042 | Must | PASS |  | analytics/pipeline.py:220; tests/unit/analytics/test_pipeline.py::test_contract_violations | _validate raises ContractError for missing/non-finite features; no imputation | inspection |
| BSC-043 | Should | PASS |  | analytics/pipeline.py:220-256 | Every record is processed as its own session; no per-day averaging/selection | inspection |

### 09 CUSUM and Alerting Spec

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| CUS-001 | Must | PASS |  | tests/unit/analytics/test_cusum_engine.py::test_tally_and_states |  | test |
| CUS-002 | Must | PASS |  | analytics/cusum_engine.py:23-25; analytics/config.py:397-398,578-579 | k and h read from PipelineConfig (0.5, 5.0) | inspection |
| CUS-003 | Must | PASS |  | analytics/cusum_engine.py:16-33; tests/unit/analytics/test_cusum_engine.py::test_tally_and_states | Tally starts at 0 from first scored session; only scored rows enter run_cusum | inspection |
| CUS-004 | Must | PASS |  | analytics/pipeline.py:243; tests/unit/analytics/test_cusum_engine.py::test_src05_alarms | Only scored sessions update the tally; missing/set-aside/etc. never enter | inspection |
| CUS-005 | Must | PASS |  | tests/unit/analytics/test_cusum_engine.py::test_epochs_have_their_own_tally |  | test |
| CUS-006 | Must | PASS |  | tests/unit/analytics/test_cusum_engine.py::test_tally_and_states |  | test |
| CUS-007 | Must | PASS |  | tests/unit/analytics/test_cusum_engine.py::test_tally_and_states |  | test |
| CUS-008 | Must | PASS |  | tests/integration/api/test_alerts.py::test_reviews |  | test |
| CUS-009 | Must | PASS |  | backend/services/pipeline_persistence.py:297-305; database/schema.sql:865 | cusum_state per epoch with current_tally, last_scored_session_id, alarm_on, updated_at | inspection |
| CUS-010 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_second_run_changes_nothing | Rerun reproduces every derived row incl. cusum_tally/alarm_state | inspection |
| CUS-011 | Must | PASS |  | tests/unit/analytics/test_alert_generator.py::test_one_event_per_ringing_epoch_with_closure_facts; tests/unit/analytics/test_cusum_engine.py::test_src05_alarms |  | test |
| CUS-012 | Must | PASS |  | tests/unit/analytics/test_alert_generator.py::test_one_event_per_ringing_epoch_with_closure_facts |  | test |
| CUS-013 | Must | PASS |  | tests/unit/analytics/test_alert_generator.py::test_one_event_per_ringing_epoch_with_closure_facts |  | test |
| CUS-014 | Must | PASS |  | backend/services/pipeline_persistence.py:332-358; database/schema.sql:809,1112 | Upsert on (epoch_id, session_id), new alerts open; one non-closed alert per epoch index | inspection |
| CUS-015 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_reviews_and_snooze_survive_a_rerun |  | test |
| CUS-016 | Must | PASS |  | tests/integration/api/test_alerts.py::test_reviews |  | test |
| CUS-017 | Must | PASS |  | tests/integration/api/test_alerts.py::test_reviews |  | test |
| CUS-018 | Must | PASS |  | backend/services/pipeline_persistence.py:309-317,342-357 | Alert closed 'epoch ended' with closed_at=as_of and system audit alert.closed | inspection |
| CUS-019 | Must | PASS |  | backend/api/alarms.py (no close endpoint) | No manual close endpoint; closed_reason admin reserved | inspection |
| CUS-020 | Must | PASS |  | backend/services/resident_service.py:139-157; tests/integration/api/test_ui_fixture_ds07.py::test_resident_chart_r09 | alarm_on while alert open or acknowledged; attention flag never overrides | inspection |
| CUS-021 | Must | PASS |  | backend/services/resident_service.py:139-147; tests/integration/api/test_residents.py:73-80 | Status follows current epoch (R07 epoch 2 no_alarm, restart_cause device) | inspection |
| CUS-022 | Must | PASS |  | tests/integration/api/test_alerts.py::test_alert_list; tests/unit/backend/test_no_outbound_alerts.py::test_no_messaging_client |  | test |
| CUS-023 | Must | PASS |  | frontend/components/ChangeScoreChart/ChangeScoreChart.tsx:108,119,263; frontend/lib/wording/trends.ts:16,35,38; frontend/components/ChangeScoreChart/ChangeScoreChart.test.tsx | Bars by alarm_state colours, baseline slot, dashed Alarm line, marker, intro text | inspection |
| CUS-024 | Must | PASS |  | tests/integration/api/test_scores.py::test_scores_json |  | test |
| CUS-025 | Must | PASS |  | tests/integration/api/test_alerts.py::test_alert_list |  | test |
| CUS-026 | Must | PASS |  | frontend/lib/wording/chart.ts:186-187,320; frontend/lib/wording/list.ts:64; frontend/tests/unit/wording-chart.test.ts | Change/check-in wording from single wording config; no diagnosis/severity | inspection |
| CUS-027 | Must | PASS |  | tests/validation/test_r09_step_change.py::test_vc_r09_step_change; tests/validation/test_r10_gradual_drift.py::test_vc_r10_gradual_drift |  | test |
| CUS-028 | Must | PASS |  | tests/validation/test_global_checks.py::test_vc_g10_alerts |  | test |
| CUS-029 | Must | PASS |  | backend/schemas/common.py:47-54; backend/schemas/analytics.py | GET /analytics meta carries cusum_h, baseline_n, pipeline_profile | inspection |
| CUS-030 | Must | NOT APPLICABLE |  | specs/backlog/features/FEAT-093-Alarm-Limit-Calibration-On-Team-1.md | Calibration is future research (FEAT-093, MVP status Future), gated on OQ-13/DS-04 | inspection |
| CUS-031 | Must | NOT APPLICABLE |  | specs/backlog/features/FEAT-093-Alarm-Limit-Calibration-On-Team-1.md | Calibration grid is future research (FEAT-093), not this build | inspection |
| CUS-032 | Must | NOT APPLICABLE |  | specs/backlog/features/FEAT-093-Alarm-Limit-Calibration-On-Team-1.md | Calibration metrics are future research (FEAT-093) | inspection |
| CUS-033 | Must | PASS |  | tests/unit/backend/test_ground_truth_boundary.py::test_only_the_summary_reads_the_answer_key; tests/integration/pipeline/test_runner_persistence.py::test_runner_never_reads_the_answer_key | Answer key never read by analytics/ or pipeline | inspection |
| CUS-034 | Must | NOT APPLICABLE |  | specs/backlog/features/FEAT-093-Alarm-Limit-Calibration-On-Team-1.md; specs/TRD/24_Risk_Assumptions_and_Open_Questions.md:107 | Selection gated on OQ-27/FEAT-093 future research; production values unchanged | inspection |
| CUS-035 | Must | PASS |  | analytics/config.py:578-579; tests/validation/test_global_checks.py | test_v0_1 profile unchanged; validation suite passes on it | inspection |
| CUS-036 | Must | PASS |  | analytics/ (no EWMA); analytics/cusum_engine.py | No EWMA trend implemented in v0.1 | inspection |
| CUS-037 |  | NOT APPLICABLE |  | specs/TRD/09_CUSUM_and_Alerting_Spec.md:255 | Retired by TRD 24 D-110 | inspection |
| CUS-038 | Must | PASS |  | tests/integration/api/test_alerts.py::test_invalid_reviews_write_nothing |  | test |
| CUS-039 | Must | PASS |  | tests/integration/api/test_alerts.py::test_snooze |  | test |
| CUS-040 | Must | PASS |  | tests/integration/api/test_alerts.py::test_data_problem_review_creates_then_links |  | test |
| CUS-041 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_alerts_endpoint_leaning_most; tests/unit/analytics/test_alert_generator.py::test_leaning_most_rules; tests/unit/analytics/test_alert_generator.py::test_src05_alerts_and_leaning_most |  | test |
| CUS-042 | Must | PASS |  | frontend/lib/wording/review.ts:67; frontend/lib/wording/chart.ts:187; frontend/lib/wording/common.ts:13; frontend/components/AlarmReviewPanel/AlarmReviewPanel.test.tsx:34 | OQ note on review panel, 'prompt to check in, not a diagnosis', no-audio data bar; review roles not enforced beyond clinician/admin | inspection |
| CUS-043 | Must | PASS |  | tests/unit/analytics/test_data_alerts.py::test_src05_exactly_four_alerts_in_order |  | test |
| CUS-044 | Must | PASS |  | tests/unit/analytics/test_data_alerts.py::test_src05_exactly_four_alerts_in_order |  | test |
| CUS-045 | Must | PASS |  | tests/integration/api/test_alerts.py::test_data_alert_list |  | test |
| CUS-046 | Must | PASS |  | analytics/config.py (OPERATIONAL_KEYS excluded from hash); tests/unit/analytics/test_config.py::test_hash_covers_algorithm_keys_only | Data-alert thresholds from config_parameters; excluded from config hash, recomputed each run | inspection |
| CUS-047 | Must | PASS |  | tests/integration/api/test_analytics.py::test_summary |  | test |
| CUS-048 | Must | PASS |  | tests/integration/db/test_ground_truth_loader.py::test_refuses_outside_test_v0_1 |  | test |
| CUS-049 | Must | PASS |  | tests/integration/api/test_analytics.py::test_production_profile |  | test |

### 10 Data Ingestion and Validation Spec

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| ING-001 | Must | PASS |  | tests/integration/api/test_sessions.py::test_only_an_ingest_key_may_post |  | test |
| ING-002 | Must | PASS |  | backend/services/ingestion.py:337-364; tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed; ::test_failed_run_answers_pending | 201 with the six fields; pending on failed run | inspection |
| ING-003 | Must | PASS |  | tests/integration/api/test_sessions.py::test_repeat_session_id_is_a_duplicate |  | test |
| ING-004 | Must | PASS |  | tests/integration/api/test_sessions.py::test_unknown_resident_is_rejected_and_stored |  | test |
| ING-005 | Must | PASS |  | backend/services/ingestion.py:65,507,515; backend/core/middleware.py:48; backend/api/permissions.py:35 | JSON or multipart CSV, <=5000 records, <=5 MB; X-API-Key ingest:write or admin JWT | inspection |
| ING-006 | Must | PASS |  | tests/integration/api/test_ingest.py::test_record_errors_do_not_fail_the_batch |  | test |
| ING-007 | Must | PASS |  | tests/integration/api/test_ingest.py::test_envelope_errors_store_nothing; tests/integration/api/test_ingest.py::test_record_errors_do_not_fail_the_batch |  | test |
| ING-008 | Must | PASS |  | tests/integration/api/test_ingest.py::test_reupload_is_all_duplicates |  | test |
| ING-009 | Must | PASS |  | tests/integration/api/test_ingest.py::test_batch_detail_and_roles |  | test |
| ING-010 | Must | PASS |  | tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed |  | test |
| ING-011 | Must | PASS |  | tests/integration/api/test_rate_limits.py::test_ingest_limit_is_per_api_key |  | test |
| ING-012 | Must | PASS |  | tests/integration/api/test_ingest.py::test_envelope_errors_store_nothing; tests/integration/api/test_sessions.py::test_extra_field_and_audio_are_refused |  | test |
| ING-013 | Must | PASS |  | tests/unit/backend/services/test_validation.py::test_schema_versions |  | test |
| ING-014 | Must | PASS |  | tests/unit/backend/services/test_validation.py::test_validator_registry |  | test |
| ING-015 | Must | PASS |  | tests/unit/backend/services/test_validation.py::test_schema_versions |  | test |
| ING-016 | Must | PASS |  | tests/integration/api/test_ingest.py::test_mapped_header_is_accepted; tests/unit/backend/services/test_validation.py::test_name_mapping |  | test |
| ING-017 | Must | PASS |  | tests/integration/api/test_ingest.py::test_invalid_name_map_stops_startup; tests/unit/backend/services/test_validation.py::test_invalid_name_maps_are_refused |  | test |
| ING-018 | Must | PASS |  | tests/integration/api/test_ingest.py::test_mapped_header_is_accepted; tests/unit/backend/services/test_validation.py::test_name_mapping |  | test |
| ING-019 | Must | PASS |  | tests/unit/backend/services/test_validation.py::test_all_violations_are_collected |  | test |
| ING-020 | Must | PASS |  | tests/unit/backend/services/test_validation.py::test_implausible_value_is_a_warning |  | test |
| ING-021 | Must | PASS |  | tests/unit/backend/services/test_validation.py::test_json_numbers_and_csv_cells |  | test |
| ING-022 | Must | PASS |  | tests/unit/backend/services/test_validation.py::test_text_is_kept_exactly |  | test |
| ING-023 | Must | PASS |  | tests/unit/backend/services/test_validation.py::test_warnings |  | test |
| ING-024 | Must | PASS |  | tests/unit/backend/services/test_validation.py::test_every_src_05_row_validates |  | test |
| ING-025 | Must | PASS |  | tests/unit/backend/services/test_validation.py::test_timestamp_formats |  | test |
| ING-026 | Must | PASS |  | database/schema.sql (raw_sessions.timestamp_utc timestamptz); tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed | Stored as timestamptz; received string kept in payload | inspection |
| ING-027 | Must | PASS |  | tests/unit/backend/services/test_validation.py::test_warnings |  | test |
| ING-028 | Must | PASS |  | tests/unit/backend/services/test_validation.py::test_warnings |  | test |
| ING-029 | Must | PASS |  | tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed |  | test |
| ING-030 | Must | PASS |  | database/schema.sql:1538,1544,2104,2125 | Trigger raw_sessions_no_update_delete; app SELECT,INSERT only; ingest_rejections append-only by grants | inspection |
| ING-031 | Must | PASS |  | tests/unit/backend/services/test_validation.py::test_csv_header_errors |  | test |
| ING-032 | Must | PASS |  | tests/integration/api/test_ingest.py::test_src05_upload; tests/integration/api/test_ingest.py::test_record_errors_do_not_fail_the_batch |  | test |
| ING-033 | Must | PASS |  | tests/integration/api/test_sessions.py::test_unknown_resident_is_rejected_and_stored |  | test |
| ING-034 | Must | PASS |  | tests/unit/analytics/test_duplicate_detection.py::test_first_arrival_wins_in_arrival_order |  | test |
| ING-035 | Must | PASS |  | tests/unit/analytics/test_quality_screening.py::test_duplicates_pass_through_ungated |  | test |
| ING-036 | Must | PASS |  | backend/repositories/read_models.py:83-95,127-132; tests/integration/pipeline/test_runner_persistence.py::test_full_run_on_src05 | Duplicate processed rows stored and counted; read models exclude them | inspection |
| ING-037 | Must | PASS |  | tests/integration/api/test_ingest.py::test_batch_duplicates_and_statement_count; tests/integration/api/test_sessions.py::test_repeat_session_id_is_a_duplicate; tests/unit/analytics/test_duplicate_detection.py::test_first_arrival_wins_in_arrival_order |  | test |
| ING-038 | Must | PASS |  | tests/integration/api/test_ingest.py::test_batch_duplicates_and_statement_count; tests/integration/db/test_advisory_locks.py::test_lock_xact_many_takes_the_same_keys_as_lock_xact; tests/integration/pipeline/test_concurrent_ingest.py::test_concurrent_posts_of_one_session_id |  | test |
| ING-039 | Must | PASS |  | tests/integration/api/test_ingest.py::test_reupload_is_all_duplicates; tests/integration/api/test_ingest.py::test_batch_duplicates_and_statement_count; tests/unit/analytics/test_duplicate_detection.py::test_src05_duplicates |  | test |
| ING-040 | Must | PASS |  | tests/unit/analytics/test_quality_screening.py::test_thresholds_are_strict |  | test |
| ING-041 | Must | PASS |  | tests/unit/analytics/test_quality_screening.py::test_all_reasons_in_fixed_order |  | test |
| ING-042 | Must | PASS |  | analytics/quality_screening.py; tests/unit/analytics/test_quality_screening.py::test_src05_set_aside | Set-aside logged, epoch-assigned, not scored or in baseline; ledger counts it | inspection |
| ING-043 | Must | PASS |  | analytics/quality_screening.py:44 | Gate passes get pending_screen for the speaker screen | inspection |
| ING-044 | Must | PASS |  | analytics/day_ledger.py:27-32; database/schema.sql (device_assignments) | Inclusive valid_from/valid_to, null = open; device_on resolves per date | inspection |
| ING-045 | Must | PASS |  | tests/unit/analytics/test_day_ledger.py::test_device_resolution |  | test |
| ING-046 | Must | PASS |  | analytics/day_ledger.py:35-50,84 | Shared when >= shared_device_min_residents enrolled residents assigned on d | inspection |
| ING-047 | Must | PASS |  | analytics/epoch_detection.py:31; analytics/pipeline.py:230,294-299 | Epochs use record device_id; assignments only for ledger/labels/mismatch warning | inspection |
| ING-048 | Must | PASS |  | tests/unit/analytics/test_day_ledger.py::test_checked_in_gap_and_missed |  | test |
| ING-049 | Must | PASS |  | tests/unit/analytics/test_day_ledger.py::test_checked_in_gap_and_missed |  | test |
| ING-050 | Must | PASS |  | tests/unit/analytics/test_day_ledger.py::test_checked_in_gap_and_missed |  | test |
| ING-051 | Must | PASS |  | analytics/day_ledger.py; tests/unit/analytics/test_day_ledger.py::test_checked_in_gap_and_missed | Missing days create no session/score and are recomputed each run | inspection |
| ING-052 | Must | PASS |  | tests/unit/analytics/test_day_ledger.py::test_checked_in_gap_and_missed |  | test |
| ING-053 | Must | PASS |  | tests/integration/api/test_ingest.py::test_answer_key_columns_are_refused; tests/integration/api/test_ingest.py::test_envelope_errors_store_nothing; tests/unit/backend/services/test_validation.py::test_csv_header_errors |  | test |
| ING-054 | Must | PASS |  | tests/unit/backend/test_ground_truth_boundary.py; database/seeds/load_evaluation_ground_truth.py; database/schema.sql:2077 | Only the test loader and analytics_summary (readonly engine) touch ground truth; app role has no SELECT | inspection |
| ING-055 | Must | PASS |  | tests/integration/api/test_ingest.py::test_legacy_file_is_refused; tests/unit/backend/services/test_validation.py::test_csv_header_errors |  | test |
| ING-056 | Must | PASS |  | backend/ analytics/ (no SRC-06 converter); tests/integration/api/test_ingest.py::test_legacy_file_is_refused | No SRC-06 converter; legacy file refused | inspection |
| ING-057 | Must | PASS |  | tests/integration/api/test_sessions.py::test_logs_carry_no_feature_value_or_key |  | test |
| ING-058 | Must | PASS |  | tests/integration/api/test_ingest.py::test_batch_is_audited_with_the_request_id |  | test |
| ING-059 | Must | PASS |  | backend/cli.py:610-622 | Seed uses IngestService.ingest_batch with source seed, no direct SQL inserts | inspection |

### 11 User Interface UX Spec

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| UX-001 | Must | PASS |  | frontend/components/ResidentsTable/ResidentsTable.tsx; grep of app/components/lib | residents shown by resident_code only; no name/photo/room fields rendered | inspection |
| UX-002 | Must | PASS |  | frontend/lib/format.ts:17,41 | Intl formatting with timeZone = meta.facility_tz; no America/Chicago hard-coded in source | inspection |
| UX-003 | Must | PASS |  | frontend/tests/unit/format.test.ts "" |  | test |
| UX-004 | Must | PASS |  | frontend/components/StatusPill/StatusPill.test.tsx "StatusPill" |  | test |
| UX-005 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:83 | retired by TRD 24 D-110 | inspection |
| UX-006 | Must | PASS |  | frontend/tests/e2e/privacy.spec.ts:40 | E2E asserts no audio/video on all routes; no audio controls in source | inspection |
| UX-007 | Must | PASS |  | frontend/app/(protected)/residents/[residentCode]/log/page.tsx:68-71; components/AdmissionsTable/AdmissionsTable.tsx:77; tests/unit/wording-chart.test.ts:103,143 | N and h read from meta.baseline_n/cusum_h; "of 30" and "13 of 16" covered in wording/page tests | inspection |
| UX-008 | Must | PASS |  | frontend/tests/unit/format.test.ts "" |  | test |
| UX-009 | Must | PASS |  | frontend/services/api.ts:186-265 | no DELETE/PUT and no endpoint to edit baseline/score/alarm/records; only PATCH /users | inspection |
| UX-010 | Must | PASS |  | frontend/components/AppHeader/AppHeader.test.tsx "" |  | test |
| UX-011 | Must | PASS |  | frontend/lib/wording/common.ts:11; frontend/components/AppHeader/AppHeader.module.css:15-18 | "<facility_name>, Assisted living", 14px --chrome-muted | inspection |
| UX-012 | Must | PASS |  | frontend/lib/wording/common.ts:11; .github/workflows/ci.yml:40 | rendered from meta.facility_name; old facility name absent (CI grep) | inspection |
| UX-013 | Must | PASS |  | frontend/components/AppHeader/AppHeader.tsx:55-72; AppHeader.module.css:19-41; lib/wording/common.ts:25-31 | nav aria-label Main, order and styles match; aria-current + white 16% (--nav-active) | inspection |
| UX-014 | Must | PASS |  | frontend/tests/e2e/auth.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| UX-015 | Must | PASS |  | frontend/components/AppHeader/AppHeader.tsx:74-79; AppHeader.module.css:51-65 | display name 14px chrome-muted; Sign out min-height 44px, 1px chrome-muted border | inspection |
| UX-016 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:101 | retired by contract §20 R2 / TRD 24 D-110 | inspection |
| UX-017 | Must | PASS |  | frontend/tests/pages/study.test.tsx ""; frontend/tests/unit/wording-study.test.ts "" |  | test |
| UX-018 | Must | PASS |  | frontend/components/AppHeader/AppHeader.test.tsx ""; frontend/components/CountBadge/CountBadge.test.tsx "CountBadge"; frontend/tests/e2e/auth.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| UX-400 | Must | PASS |  | frontend/components/DataBar/DataBar.test.tsx "DataBar" |  | test |
| UX-020 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:114 | retired by TRD 24 D-110 | inspection |
| UX-021 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:115 | retired by TRD 24 D-110 | inspection |
| UX-022 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:116 | retired by TRD 24 D-110 | inspection |
| UX-023 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:117 | retired by TRD 24 D-110 (replaced by UX-402) | inspection |
| UX-024 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:118 | retired by TRD 24 D-110 | inspection |
| UX-030 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:124 | retired by TRD 24 D-110 | inspection |
| UX-031 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:125 | retired by TRD 24 D-110 | inspection |
| UX-032 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:126 | retired by TRD 24 D-110 | inspection |
| UX-033 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:127 | retired by TRD 24 D-110 | inspection |
| UX-401 | Must | PASS |  | frontend/components/FilterButtons/FilterButtons.test.tsx "FilterButtons"; frontend/tests/unit/wording-list.test.ts "" |  | test |
| UX-402 | Must | PASS |  | frontend/components/FilterButtons/FilterButtons.test.tsx "FilterButtons"; frontend/tests/e2e/resident-list.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| UX-403 | Must | PASS |  | frontend/components/FilterButtons/FilterButtons.test.tsx "FilterButtons"; frontend/tests/e2e/resident-list.spec.ts ""; frontend/tests/unit/wording-list.test.ts "" | E2E in CI playwright on 23e558b (success) | test |
| UX-404 | Must | PASS |  | frontend/tests/e2e/resident-list.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| UX-408 | Must | PASS |  | frontend/services/api.ts:202 (sort=alarm); frontend/components/ResidentsTable/ResidentsTable.tsx:33-36 | API default sort requested; UI only filters, never reorders | inspection |
| UX-034 | Must | PASS |  | frontend/components/ResidentsTable/ResidentsTable.test.tsx "" |  | test |
| UX-035 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:141 | retired by TRD 24 D-110 | inspection |
| UX-036 | Must | PASS |  | frontend/components/ResidentsTable/ResidentsTable.test.tsx "" |  | test |
| UX-037 | Must | PASS |  | frontend/components/ResidentsTable/ResidentsTable.test.tsx "" |  | test |
| UX-038 | Must | PASS |  | frontend/components/ResidentsTable/ResidentsTable.test.tsx "" |  | test |
| UX-039 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:145 | retired by TRD 24 D-110 | inspection |
| UX-040 | Must | PASS |  | frontend/components/ResidentsTable/ResidentsTable.test.tsx "" |  | test |
| UX-041 | Must | PASS |  | frontend/tests/pages/residents.test.tsx ""; frontend/tests/unit/wording-list.test.ts "" |  | test |
| UX-042 | Must | PASS |  | frontend/components/ResidentsTable/ResidentsTable.test.tsx "" |  | test |
| UX-043 | Must | PASS |  | frontend/tests/unit/wording-list.test.ts "" |  | test |
| UX-044 | Must | PASS |  | frontend/components/CheckinLog/CheckinLog.tsx:37,95; frontend/lib/wording/study.ts:132-133 | log shows no duplicate events; counts come from API which excludes duplicates | inspection |
| UX-045 | Must | PASS |  | frontend/services/api.ts:202 (include_withdrawn=false) | resident list requests exclude withdrawn residents | inspection |
| UX-046 | Must | PASS |  | frontend/services/api.ts:202 (cohort=longitudinal); backend/services/pipeline_persistence.py:434-444 | list shows longitudinal cohort only; backend moves new_admission→longitudinal when baseline frozen | inspection |
| UX-405 | Must | PASS |  | frontend/components/WhatsHappening/WhatsHappening.test.tsx "WhatsHappening"; frontend/tests/unit/wording-list.test.ts "" |  | test |
| UX-406 | Must | PASS |  | frontend/components/StatusLegend/StatusLegend.test.tsx "StatusLegend" |  | test |
| UX-407 | Must | PASS |  | frontend/tests/unit/wording-list.test.ts "" |  | test |
| UX-047 | Must | PASS |  | frontend/components/CheckinCounts/CheckinCounts.test.tsx "CheckinCounts"; frontend/tests/pages/resident-log.test.tsx "" |  | test |
| UX-048 | Must | PASS |  | frontend/components/CheckinCounts/CheckinCounts.test.tsx "CheckinCounts"; frontend/tests/pages/resident-log.test.tsx "" |  | test |
| UX-050 | Must | PASS |  | frontend/components/DevicesSection/DevicesSection.test.tsx ""; frontend/tests/pages/study.test.tsx "" |  | test |
| UX-051 | Must | PASS |  | frontend/lib/wording/study.ts:229; components/DevicesSection/DevicesSection.test.tsx::renders the §4.13.4 rows for DS-07 | "D02 (shared by R02 and R03): …" tested | inspection |
| UX-052 | Must | PASS |  | frontend/lib/wording/study.ts:214-220; components/DevicesSection/DevicesSection.tsx:77 | "Silent all day Oct 12." on the device row, tested in DS-07 row test | inspection |
| UX-053 | Must | PASS |  | frontend/lib/wording/study.ts:236; components/DevicesSection/DevicesSection.tsx:61-72 | replacement row text tested; retired devices filtered out (active only) | inspection |
| UX-054 | Must | PASS |  | frontend/tests/unit/status-roles-groups.test.ts "toDisplayStatus (FE-207)" |  | test |
| UX-055 | Must | PASS |  | frontend/components/DevicesSection/DevicesSection.tsx:180-212; frontend/lib/wording/study.ts:203-212 | details "Show all devices (n)" with the 7 columns incl. silent_days_last_30 and device_gap_days_last_30 | inspection |
| UX-056 | Must | PASS |  | frontend/tests/unit/wording-study.test.ts "" |  | test |
| UX-057 | Must | PASS |  | frontend/lib/wording/study.ts:240-242; components/DevicesSection/DevicesSection.tsx:151 | "Since <Mon D>" / "<range> · replaced by <D>" | inspection |
| UX-058 | Must | PASS |  | frontend/components/DevicesSection/DevicesSection.test.tsx ""; frontend/tests/pages/study.test.tsx "" |  | test |
| UX-060 | Must | PASS |  | frontend/components/BackLink/BackLink.test.tsx "BackLink"; frontend/tests/pages/resident-layout.test.tsx "" |  | test |
| UX-061 | Must | PASS |  | frontend/components/ChartBanner/ChartBanner.test.tsx ""; frontend/tests/pages/resident-layout.test.tsx "" |  | test |
| UX-062 | Must | PASS |  | frontend/components/ChartBanner/ChartBanner.test.tsx ""; frontend/tests/pages/resident-summary.test.tsx "" |  | test |
| UX-063 | Must | PASS |  | frontend/components/ChartBanner/ChartBanner.test.tsx ""; frontend/tests/pages/resident-summary.test.tsx ""; frontend/tests/unit/wording-chart.test.ts "" |  | test |
| UX-064 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:237 | moved to UX-422 (D-110); definition row only | inspection |
| UX-065 | Must | PASS |  | frontend/components/BaselinePanel/BaselinePanel.test.tsx "BaselinePanel"; frontend/components/SummaryPanel/SummaryPanel.test.tsx ""; frontend/tests/pages/resident-baseline.test.tsx "" (+2 more) |  | test |
| UX-066 | Must | PASS |  | frontend/components/BaselinePanel/BaselinePanel.test.tsx "BaselinePanel"; frontend/tests/pages/resident-baseline.test.tsx "" |  | test |
| UX-410 | Must | PASS |  | frontend/components/ChartSectionNav/ChartSectionNav.test.tsx "ChartSectionNav"; frontend/tests/pages/resident-layout.test.tsx "" |  | test |
| UX-411 | Must | PASS |  | frontend/components/ChartSectionNav/ChartSectionNav.test.tsx "ChartSectionNav"; frontend/components/CountBadge/CountBadge.test.tsx "CountBadge"; frontend/tests/pages/resident-layout.test.tsx "" |  | test |
| UX-412 | Must | PASS |  | frontend/tests/pages/resident-layout.test.tsx "" |  | test |
| UX-070 | Must | PASS |  | frontend/components/SummaryPanel/SummaryPanel.test.tsx ""; frontend/tests/pages/resident-summary.test.tsx "" |  | test |
| UX-071 | Must | PASS |  | frontend/components/SummaryPanel/SummaryPanel.test.tsx "" |  | test |
| UX-072 | Must | PASS |  | frontend/components/SummaryPanel/SummaryPanel.test.tsx ""; frontend/tests/unit/wording-chart.test.ts "" |  | test |
| UX-073 | Must | PASS |  | frontend/components/SummaryPanel/SummaryPanel.test.tsx ""; frontend/tests/unit/wording-chart.test.ts "" |  | test |
| UX-074 | Must | PASS |  | frontend/lib/wording.ts:4-6 (re-exports lib/wording/*); components import from @/lib/wording | all Summary/what's-happening/legend copy in the wording configuration | inspection |
| UX-075 | Must | PASS |  | frontend/components/SummaryPanel/SummaryPanel.test.tsx "" |  | test |
| UX-076 | Must | PASS |  | frontend/components/SummaryPanel/SummaryPanel.test.tsx "" |  | test |
| UX-077 | Must | PASS |  | frontend/components/SummaryPanel/SummaryPanel.test.tsx "" |  | test |
| UX-078 | Must | PASS |  | frontend/components/MoreDetailTiles/MoreDetailTiles.test.tsx ""; frontend/tests/pages/resident-summary.test.tsx "" |  | test |
| UX-080 | Must | PASS |  | frontend/tests/pages/resident-trends.test.tsx ""; frontend/tests/unit/wording-trends.test.ts "" |  | test |
| UX-081 | Must | PASS |  | frontend/components/ChangeScoreChart/ChangeScoreChart.test.tsx "" |  | test |
| UX-082 | Must | PASS |  | frontend/tests/pages/resident-trends.test.tsx "" |  | test |
| UX-083 | Must | PASS |  | frontend/components/ChangeScoreChart/ChangeScoreChart.tsx:90,108-110 | bar fill follows alarm_state: off → --c-aside + 1px --muted stroke; rings/on → --red | inspection |
| UX-084 | Must | PASS |  | frontend/tests/unit/wording-trends.test.ts "" |  | test |
| UX-085 | Must | PASS |  | frontend/tests/unit/wording-trends.test.ts "" |  | test |
| UX-086 | Must | PASS |  | frontend/tests/unit/wording-trends.test.ts "" |  | test |
| UX-087 | Should | PASS |  | frontend/components/ChangeScoreChart/ChangeScoreChart.test.tsx "" |  | test |
| UX-088 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:284 | retired by TRD 24 D-110 | inspection |
| UX-089 | Must | PASS |  | frontend/tests/pages/resident-trends.test.tsx ""; frontend/tests/unit/wording-trends.test.ts "" |  | test |
| UX-090 | Must | PASS |  | frontend/components/ChangeScoreChart/ChangeScoreChart.test.tsx ""; frontend/components/ChangeScoreTable/ChangeScoreTable.test.tsx "ChangeScoreTable"; frontend/tests/unit/wording-trends.test.ts "" |  | test |
| UX-091 | Must | PASS |  | frontend/tests/unit/wording-trends.test.ts "" |  | test |
| UX-092 | Must | PASS |  | frontend/components/ChangeScoreChart/ChangeScoreChart.test.tsx ""; frontend/tests/pages/resident-trends.test.tsx ""; frontend/tests/unit/wording-trends.test.ts "" |  | test |
| UX-100 | Must | PASS |  | frontend/components/MeasurementCards/MeasurementCards.test.tsx ""; frontend/tests/pages/resident-trends.test.tsx ""; frontend/tests/unit/wording-trends.test.ts "" |  | test |
| UX-101 | Must | PASS |  | frontend/components/FeatureCard/FeatureCard.test.tsx "FeatureCard"; frontend/components/MeasurementCards/MeasurementCards.test.tsx "" |  | test |
| UX-102 | Must | PASS |  | frontend/components/FeatureCard/FeatureCard.test.tsx "FeatureCard"; frontend/components/MeasurementCards/MeasurementCards.test.tsx ""; frontend/components/Sparkline/Sparkline.test.tsx "Sparkline" |  | test |
| UX-103 | Must | PASS |  | frontend/components/FeatureCard/FeatureCard.test.tsx "FeatureCard"; frontend/components/MeasurementCards/MeasurementCards.test.tsx ""; frontend/components/Sparkline/Sparkline.test.tsx "Sparkline" (+1 more) |  | test |
| UX-104 | Must | PASS |  | frontend/components/FeatureCard/FeatureCard.test.tsx "FeatureCard"; frontend/components/MeasurementCards/MeasurementCards.test.tsx "" |  | test |
| UX-105 | Must | PASS |  | frontend/components/FeatureCard/FeatureCard.test.tsx "FeatureCard" |  | test |
| UX-106 | Must | PASS |  | frontend/components/MeasurementCards/MeasurementCards.test.tsx ""; frontend/components/OtherMeasurementsCard/OtherMeasurementsCard.test.tsx "OtherMeasurementsCard"; frontend/tests/unit/wording-trends.test.ts "" |  | test |
| UX-107 | Must | PASS |  | frontend/components/MeasurementCards/MeasurementCards.test.tsx ""; frontend/components/OtherMeasurementsCard/OtherMeasurementsCard.test.tsx "OtherMeasurementsCard" |  | test |
| UX-108 | Must | PASS |  | frontend/components/MeasurementCards/MeasurementCards.test.tsx ""; frontend/tests/pages/resident-trends.test.tsx ""; frontend/tests/unit/wording-trends.test.ts "" |  | test |
| UX-120 | Must | PASS |  | frontend/components/StaffNotes/StaffNotes.test.tsx ""; frontend/tests/pages/resident-review.test.tsx "" |  | test |
| UX-121 | Must | PASS |  | frontend/components/StaffNotes/StaffNotes.test.tsx ""; frontend/tests/unit/wording-review.test.ts "review and notes wording" |  | test |
| UX-122 | Must | PASS |  | frontend/styles/globals.css:102-125 | .btn primary 44px, 0 20px, 700, radius 4, chrome bg/border; .btn-secondary surface, ink, 1px --rule | inspection |
| UX-123 | Must | PASS |  | frontend/components/StaffNotes/StaffNotes.test.tsx "" |  | test |
| UX-124 | Must | PASS |  | frontend/components/StaffNotes/StaffNotes.test.tsx ""; frontend/tests/unit/wording-review.test.ts "review and notes wording" |  | test |
| UX-125 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:326 | moved to UX-321 (D-110); definition row only | inspection |
| UX-126 | Must | PASS |  | frontend/components/AlarmReviewPanel/AlarmReviewPanel.test.tsx ""; frontend/tests/pages/resident-review.test.tsx "" |  | test |
| UX-127 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:328 | withdrawn by TRD 24 D-102 | inspection |
| UX-128 | Must | PASS |  | frontend/components/NotesList/NotesList.test.tsx "" |  | test |
| UX-129 | Must | PASS |  | frontend/services/api.ts:211-212 | notes: only GET and POST; no edit/delete controls or endpoints | inspection |
| UX-130 | Must | PASS |  | frontend/components/StaffNotes/StaffNotes.test.tsx ""; frontend/tests/unit/wording-review.test.ts "review and notes wording" |  | test |
| UX-131 | Must | PASS |  | frontend/components/StaffNotes/StaffNotes.test.tsx ""; frontend/tests/unit/wording-review.test.ts "review and notes wording" |  | test |
| UX-132 | Must | PASS |  | frontend/components/StaffNotes/StaffNotes.test.tsx ""; frontend/tests/unit/wording-review.test.ts "review and notes wording" |  | test |
| UX-133 | Must | PASS |  | frontend/components/NotesList/NotesList.test.tsx ""; frontend/components/StaffNotes/StaffNotes.test.tsx "" |  | test |
| UX-134 | Must | PASS |  | frontend/components/NotesList/NotesList.test.tsx ""; frontend/tests/unit/wording-review.test.ts "review and notes wording" |  | test |
| UX-135 | Should | PASS |  | frontend/components/NotesList/NotesList.test.tsx ""; frontend/tests/unit/wording-review.test.ts "review and notes wording" |  | test |
| UX-136 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:337 | retired by TRD 24 D-110 | inspection |
| UX-137 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:338 | retired by TRD 24 D-110 | inspection |
| UX-138 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:339 | retired by TRD 24 D-110 | inspection |
| UX-140 | Must | PASS |  | frontend/components/CheckinCounts/CheckinCounts.test.tsx "CheckinCounts"; frontend/components/CheckinLog/CheckinLog.test.tsx ""; frontend/tests/pages/resident-log.test.tsx "" |  | test |
| UX-141 | Must | PASS |  | tests/integration/api/test_residents.py::test_checkin_log; tests/integration/api/test_residents.py::test_same_date_events_follow_ux_141; frontend/components/CheckinLog/CheckinLog.test.tsx "" |  | test |
| UX-142 | Must | PASS |  | frontend/components/CheckinLog/CheckinLog.test.tsx ""; frontend/tests/unit/wording-chart.test.ts "" |  | test |
| UX-143 | Must | PASS |  | frontend/components/CheckinLog/CheckinLog.test.tsx "" |  | test |
| UX-144 | Must | PASS |  | frontend/components/CheckinLog/CheckinLog.test.tsx ""; frontend/tests/e2e/isolated.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| UX-145 | Must | PASS |  | frontend/components/CheckinLog/CheckinLog.test.tsx "" |  | test |
| UX-146 | Must | PASS |  | frontend/components/CheckinLog/CheckinLog.test.tsx "" |  | test |
| UX-147 | Must | PASS |  | frontend/components/CheckinLog/CheckinLog.test.tsx "" |  | test |
| UX-148 | Must | PASS |  | frontend/components/CheckinLog/CheckinLog.test.tsx "" |  | test |
| UX-149 | Must | PASS |  | frontend/components/CheckinLog/CheckinLog.test.tsx "" |  | test |
| UX-150 | Must | PASS |  | frontend/components/CheckinLog/CheckinLog.test.tsx ""; frontend/tests/pages/resident-log.test.tsx "" |  | test |
| UX-420 | Must | PASS |  | frontend/components/BaselinePanel/BaselinePanel.test.tsx "BaselinePanel"; frontend/tests/pages/resident-baseline.test.tsx "" |  | test |
| UX-421 | Must | PASS |  | frontend/components/BaselinePanel/BaselinePanel.test.tsx "BaselinePanel"; frontend/tests/pages/resident-baseline.test.tsx ""; frontend/tests/unit/wording-chart.test.ts "" |  | test |
| UX-422 | Must | PASS |  | frontend/components/BaselinePanel/BaselinePanel.test.tsx "BaselinePanel"; frontend/tests/pages/resident-baseline.test.tsx "" |  | test |
| UX-423 | Must | PASS |  | frontend/components/BaselinePanel/BaselinePanel.test.tsx "BaselinePanel"; frontend/tests/pages/resident-baseline.test.tsx ""; frontend/tests/unit/wording-chart.test.ts "" |  | test |
| UX-430 | Must | PASS |  | frontend/components/DevicePanel/DevicePanel.test.tsx ""; frontend/tests/pages/resident-device.test.tsx ""; frontend/tests/unit/wording-review.test.ts "review and notes wording" |  | test |
| UX-431 | Must | PASS |  | frontend/components/DevicePanel/DevicePanel.test.tsx ""; frontend/tests/pages/resident-device.test.tsx "" |  | test |
| UX-432 | Must | PASS |  | frontend/components/DevicePanel/DevicePanel.test.tsx ""; frontend/tests/pages/resident-device.test.tsx ""; frontend/tests/unit/wording-review.test.ts "review and notes wording" |  | test |
| UX-433 | Must | PASS |  | frontend/components/DevicePanel/DevicePanel.test.tsx ""; frontend/tests/pages/resident-device.test.tsx "" |  | test |
| UX-160 | Must | PASS |  | frontend/lib/wording/chart.ts:186-187; frontend/lib/wording/list.ts:64 | copy frames results as change from own usual pattern; no measuring/grading wording found | inspection |
| UX-161 | Must | PASS |  | .github/workflows/ci.yml:42; grep of frontend/lib/wording, components, app | no forbidden stems in UI source except "not a diagnosis"; CI grep covers only diagnoses/severity | inspection |
| UX-162 | Must | PASS |  | frontend/lib/wording/chart.ts:186-187; frontend/lib/wording/list.ts:64 | "prompt to check in, not a diagnosis" and list note present | inspection |
| UX-163 | Must | PASS |  | frontend/components/FeatureCard/FeatureCard.test.tsx "FeatureCard"; frontend/components/MeasurementCards/MeasurementCards.test.tsx "" |  | test |
| UX-164 | Must | PASS |  | frontend/lib/wording/common.ts:8; frontend/lib/wording/list.ts:66; frontend/lib/wording/chart.ts:6 | PI marker appended while CLINICAL_WORDING_APPROVED is false | inspection |
| UX-165 | Should | PASS |  | frontend/lib/wording/*.ts | no exclamation marks in copy (only the "!" pill glyph, common.ts:47); sentence case | inspection |
| UX-166 | Must | PASS |  | frontend/lib/wording/common.ts:11; .github/workflows/ci.yml:40 | facility from meta.facility_name; neither old name nor "[Facility name]" in frontend source | inspection |
| UX-167 | Must | PASS |  | frontend/lib/wording/chart.ts:244,295,322; frontend/lib/wording/review.ts:12; frontend/lib/wording/common.ts:36-40 | held back (possible other voice), change score, Comparing with baseline started, What did you find?, status labels | inspection |
| UX-180 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:419 | retired by TRD 24 D-110 | inspection |
| UX-181 | Must | PASS |  | frontend/components/ExperimentalBanner/ExperimentalBanner.test.tsx "ExperimentalBanner"; frontend/tests/e2e/admissions.spec.ts "E2E-13 / FE-189 experimental note and empty state"; frontend/tests/pages/admissions.test.tsx "" (+1 more) | E2E in CI playwright on 23e558b (success) | test |
| UX-182 | Must | PASS |  | frontend/components/AdmissionsTable/AdmissionsTable.test.tsx "" |  | test |
| UX-183 | Must | PASS |  | frontend/lib/wording/admin.ts:16-23; frontend/components/AdmissionsTable/AdmissionsTable.module.css:3 | 5 columns + Actions, min-width 640px | inspection |
| UX-184 | Must | PASS |  | tests/integration/api/test_admissions.py::test_range_not_available |  | test |
| UX-185 | Must | PASS |  | tests/integration/api/test_admissions.py::test_range_not_available; frontend/components/RangePill/RangePill.test.tsx "RangePill"; frontend/tests/unit/wording-admin.test.ts "admissions wording" |  | test |
| UX-186 | Must | PASS |  | tests/integration/api/test_admissions.py::test_range_not_available; frontend/tests/unit/wording-admin.test.ts "admissions wording" |  | test |
| UX-187 | Must | PASS |  | frontend/components/AdmissionsTable/AdmissionsTable.tsx:63,82; AdmissionsTable.module.css:20-27; lib/wording/admin.ts:25 | btn-secondary "Show comparison", aria-selected, 5px --chrome left border | inspection |
| UX-188 | Must | PASS |  | frontend/components/AdmissionsTable/AdmissionsTable.test.tsx "" |  | test |
| UX-189 | Must | PASS |  | frontend/components/FacilityRangeChart/FacilityRangeChart.test.tsx "" |  | test |
| UX-190 | Must | PASS |  | frontend/lib/wording/admin.ts:50; frontend/components/FacilityRangeChart/FacilityRangeChart.tsx:93 | caption via .caption (12px, --muted) | inspection |
| UX-191 | Must | PASS |  | frontend/lib/wording/admin.ts:69-79; components/FacilityRangeChart/FacilityRangeChart.tsx:67,111 | 7 plain labels; fallback is feature_key (ComparisonFeature has no label field) | inspection |
| UX-192 | Must | PASS |  | frontend/tests/unit/wording-admin.test.ts "admissions wording" |  | test |
| UX-193 | Must | PASS |  | frontend/components/FacilityRangeChart/FacilityRangeChart.test.tsx "" |  | test |
| UX-194 | Must | PASS |  | tests/integration/api/test_admissions.py::test_empty_state; frontend/components/AdmissionsTable/AdmissionsTable.test.tsx "" |  | test |
| UX-195 | Should | PASS |  | frontend/tests/pages/admissions.test.tsx ""; frontend/tests/unit/wording-admin.test.ts "admissions wording" |  | test |
| UX-170 | Must | PASS |  | frontend/components/LoginForm/LoginForm.test.tsx "" |  | test |
| UX-171 | Must | PASS |  | frontend/lib/wording/common.ts:98; components/LoginForm/LoginForm.tsx:75; LoginForm.test.tsx::shows the wrong-credentials, rate-limit and network messages | role=alert, generic message | inspection |
| UX-172 | Must | PASS |  | frontend/components/LoginForm/LoginForm.tsx:18; lib/wording/common.ts:99; LoginForm.test.tsx::shows the wrong-credentials, rate-limit and network messages |  | inspection |
| UX-173 | Must | PASS |  | frontend/components/LoginForm/LoginForm.tsx:51-53; lib/wording/common.ts:100 | shown when reason=expired | inspection |
| UX-174 | Must | PASS |  | frontend/components/LoginForm/LoginForm.tsx:78; lib/wording/common.ts:97; LoginForm.test.tsx::shows Signing in… while busy |  | inspection |
| UX-175 | Must | PASS |  | frontend/tests/pages/login.test.tsx "/login" |  | test |
| UX-176 | Must | PASS |  | frontend/components/LoginForm/LoginForm.test.tsx "" |  | test |
| UX-210 | Must | PASS |  | frontend/components/AdminPanel/AdminPanel.test.tsx ""; frontend/tests/pages/admin.test.tsx "" |  | test |
| UX-211 | Must | PASS |  | frontend/lib/wording/admin.ts:101-136; tests/pages/admin.test.tsx::adds a user and clears the form (UX-211, UX-228) | columns, Add user form, Deactivate/Reactivate with confirmation text | inspection |
| UX-212 | Must | PASS |  | frontend/components/AdminPanel/AdminPanel.test.tsx "" |  | test |
| UX-213 | Must | PASS |  | frontend/tests/unit/wording-admin.test.ts "admissions wording" |  | test |
| UX-217 | Must | PASS |  | frontend/tests/unit/wording-admin.test.ts "admissions wording" |  | test |
| UX-219 | Must | PASS |  | frontend/components/AdminPanel/AdminPanel.test.tsx ""; frontend/tests/pages/admin.test.tsx ""; frontend/tests/unit/wording-admin.test.ts "admissions wording" |  | test |
| UX-218 | Must | PASS |  | frontend/services/api.ts:186-265 | admin API surface: users, pipeline runs, upload only; no resident/device/assignment/API-key editing | inspection |
| UX-214 | Must | PASS |  | frontend/lib/wording/admin.ts:205; frontend/components/AdminPanel/UploadTab.tsx:113 | line rendered unconditionally in every environment | inspection |
| UX-215 | Must | PASS |  | frontend/tests/e2e/auth.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| UX-216 | Should | PASS |  | frontend/tests/unit/wording-admin.test.ts "admissions wording" |  | test |
| UX-200 | Must | PASS |  | frontend/components/ChartBanner/ChartBanner.test.tsx ""; frontend/components/CheckinCounts/CheckinCounts.test.tsx "CheckinCounts"; frontend/components/FilterButtons/FilterButtons.test.tsx "FilterButtons" (+4 more) |  | test |
| UX-201 | Must | PASS |  | frontend/app/(protected)/residents/page.tsx:43-48; components/ResidentsTable/ResidentsTable.tsx:33-36 | keepPreviousData; filter applied client-side via ?show= without a request | inspection |
| UX-202 | Must | PASS |  | frontend/tests/pages/admissions.test.tsx ""; frontend/tests/pages/resident-baseline.test.tsx ""; frontend/tests/pages/resident-log.test.tsx "" (+3 more) |  | test |
| UX-203 | Must | PASS |  | frontend/components/SectionState/SectionState.test.tsx "SectionState"; frontend/tests/pages/resident-baseline.test.tsx ""; frontend/tests/pages/resident-log.test.tsx "" |  | test |
| UX-207 | Must | PASS |  | frontend/components/AdminPanel/AdminPanel.test.tsx ""; frontend/components/AlertReviewForm/AlertReviewForm.test.tsx ""; frontend/components/StaffNotes/StaffNotes.test.tsx "" (+1 more) |  | test |
| UX-204 | Must | PASS |  | frontend/components/DevicesSection/DevicesSection.test.tsx ""; frontend/components/MeasurementCards/MeasurementCards.test.tsx ""; frontend/components/NotesList/NotesList.test.tsx "" |  | test |
| UX-205 | Must | PASS |  | frontend/tests/pages/resident-layout.test.tsx "" |  | test |
| UX-206 | Should | PASS |  | frontend/tests/pages/resident-layout.test.tsx "" |  | test |
| UX-240 | Must | PASS |  | frontend/tests/e2e/responsive.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| UX-241 | Must | PASS |  | frontend/tests/e2e/responsive.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| UX-242 | Must | PASS |  | frontend/tests/e2e/responsive.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| UX-243 | Must | PASS |  | frontend/components/ChangeScoreChart/ChangeScoreChart.test.tsx ""; frontend/tests/e2e/responsive.spec.ts ""; frontend/tests/pages/resident-trends.test.tsx "" | E2E in CI playwright on 23e558b (success) | test |
| UX-244 | Must | PASS |  | frontend/tests/e2e/responsive.spec.ts:8-13,30-36 | no horizontal page scroll and no lost content at 320–390px (≥ 200% zoom equivalent reflow); no explicit zoom test | inspection |
| UX-245 | Must | PASS |  | frontend/app/(protected)/residents/page.module.css:3; frontend/components/ChartBanner/ChartBanner.module.css:7,18 | flex-wrap on list header and banner | inspection |
| UX-246 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:510 | retired by TRD 24 D-110 | inspection |
| UX-260 | Must | PASS |  | frontend/tests/e2e/resident-list.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| UX-261 | Must | PASS |  | frontend/tests/e2e/resident-list.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| UX-262 | Must | PASS |  | frontend/components/DevicePanel/DevicePanel.test.tsx ""; frontend/tests/e2e/resident-chart.spec.ts ""; frontend/tests/pages/resident-device.test.tsx "" (+1 more) | E2E in CI playwright on 23e558b (success) | test |
| UX-263 | Must | PASS |  | frontend/tests/e2e/study-team.spec.ts ""; frontend/tests/pages/study.test.tsx "" | E2E in CI playwright on 23e558b (success) | test |
| UX-264 | Must | PASS |  | frontend/tests/e2e/admissions.spec.ts "E2E-13 / FE-189 experimental note and empty state"; frontend/tests/pages/admissions.test.tsx "" | E2E in CI playwright on 23e558b (success) | test |
| UX-220 | Must | PASS |  | frontend/tests/e2e/a11y.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| UX-221 | Must | PASS |  | frontend/tests/e2e/a11y.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| UX-222 | Must | PASS |  | frontend/tests/e2e/a11y.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| UX-223 | Must | PASS |  | frontend/tests/e2e/responsive.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| UX-224 | Must | FAIL | S3 | frontend/styles/tokens.css:28-29; components/DailyCheckinsChart/DailyCheckinsChart.tsx:30-31 | light --c-aside 2.23:1, --c-quar 2.94:1 vs --surface as unoutlined bar segments; no §4.15 token-pair analysis recorded (axe text checks only) | inspection |
| UX-225 | Must | PASS |  | frontend/components/ChangeScoreChart/ChangeScoreChart.test.tsx ""; frontend/components/ChangeScoreTable/ChangeScoreTable.test.tsx "ChangeScoreTable"; frontend/components/FacilityRangeChart/FacilityRangeChart.test.tsx "" (+2 more) |  | test |
| UX-226 | Must | PASS |  | frontend/tests/e2e/a11y.spec.ts:29; frontend/tests/e2e/privacy.spec.ts:55 | one visible h1 per route enforced by strict locator; panels use h2 | inspection |
| UX-227 | Must | PASS |  | frontend/components/AlertReviewForm/AlertReviewForm.test.tsx ""; frontend/components/StaffNotes/StaffNotes.test.tsx ""; frontend/tests/pages/admin.test.tsx "" |  | test |
| UX-228 | Must | PASS |  | frontend/components/AlertReviewForm/AlertReviewForm.test.tsx ""; frontend/components/StaffNotes/StaffNotes.test.tsx ""; frontend/tests/e2e/a11y.spec.ts "" (+1 more) | E2E in CI playwright on 23e558b (success) | test |
| UX-229 | Must | PASS |  | frontend/tests/pages/admin.test.tsx ""; frontend/tests/pages/admissions.test.tsx ""; frontend/tests/pages/login.test.tsx "/login" (+4 more) |  | test |
| UX-230 | Must | PASS |  | frontend/components/ChangeScoreChart/ChangeScoreChart.tsx:257; DailyCheckinsChart.tsx:171; Sparkline.tsx:37; styles/globals.css:142-149 | all Recharts series isAnimationActive=false; reduced-motion rule; no CSS animations | inspection |
| UX-250 | Must | PASS |  | frontend/tests/unit/tokens.test.ts "design tokens" |  | test |
| UX-251 | Must | PASS |  | frontend/lib/wording/common.ts:44-52 | non-ASCII scan: only ▲ ! ● ○ ← used as glyphs; no icon library | inspection |
| UX-252 | Must | PASS |  | frontend/app/layout.tsx:5,12-13; frontend/tests/e2e/privacy.spec.ts:40,65 | next/font/local from app/fonts; E2E asserts no Google Fonts request | inspection |
| UX-253 | Should | PASS |  | frontend/styles/tokens.css:4,42-66; frontend/tests/e2e/a11y.spec.ts:40-56 | prefers-color-scheme dark tokens match §4.15; axe run in both schemes | inspection |
| UX-300 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:686 | retired by TRD 24 D-110 | inspection |
| UX-301 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:687 | retired by TRD 24 D-110 | inspection |
| UX-302 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:688 | retired by TRD 24 D-110 | inspection |
| UX-303 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:689 | retired by TRD 24 D-110 | inspection |
| UX-304 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:690 | retired by TRD 24 D-110 | inspection |
| UX-305 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:691 | retired by TRD 24 D-110 | inspection |
| UX-310 | Must | PASS |  | frontend/components/AlarmReviewPanel/AlarmReviewPanel.test.tsx ""; frontend/tests/e2e/review.spec.ts ""; frontend/tests/pages/resident-review.test.tsx "" (+1 more) | E2E in CI playwright on 23e558b (success) | test |
| UX-311 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:698 | retired by TRD 24 D-110 | inspection |
| UX-312 | Must | PASS |  | frontend/components/LeaningMost/LeaningMost.test.tsx "LeaningMost"; frontend/components/SummaryPanel/SummaryPanel.test.tsx ""; frontend/tests/e2e/review.spec.ts "" (+2 more) | E2E in CI playwright on 23e558b (success) | test |
| UX-313 | Must | PASS |  | frontend/components/AlarmReviewPanel/AlarmReviewPanel.test.tsx ""; frontend/components/AlertReviewForm/AlertReviewForm.test.tsx ""; frontend/tests/unit/wording-review.test.ts "review and notes wording" |  | test |
| UX-314 | Must | PASS |  | frontend/components/AlarmReviewPanel/AlarmReviewPanel.test.tsx ""; frontend/components/AlertReviewForm/AlertReviewForm.test.tsx "" |  | test |
| UX-315 | Must | PASS |  | frontend/components/AlertReviewForm/AlertReviewForm.test.tsx "" |  | test |
| UX-316 | Must | PASS |  | frontend/components/AlertReviewForm/AlertReviewForm.test.tsx ""; frontend/tests/e2e/mutating.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| UX-317 | Must | PASS |  | frontend/components/AlarmReviewPanel/AlarmReviewPanel.test.tsx ""; frontend/components/AlertReviewForm/AlertReviewForm.test.tsx ""; frontend/tests/e2e/isolated.spec.ts "" (+2 more) | E2E in CI playwright on 23e558b (success) | test |
| UX-318 | Must | PASS |  | frontend/components/AlertReviewForm/AlertReviewForm.test.tsx ""; frontend/tests/e2e/mutating.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| UX-319 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:706 | retired by TRD 24 D-110 | inspection |
| UX-320 | Must | PASS |  | frontend/components/AlarmReviewPanel/AlarmReviewPanel.test.tsx ""; frontend/components/ReviewHistory/ReviewHistory.test.tsx ""; frontend/tests/e2e/mutating.spec.ts "" (+1 more) | E2E in CI playwright on 23e558b (success) | test |
| UX-321 | Must | PASS |  | frontend/components/AlarmReviewPanel/AlarmReviewPanel.test.tsx ""; frontend/tests/e2e/review.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| UX-322 | Must | PASS |  | frontend/components/AlarmReviewPanel/AlarmReviewPanel.test.tsx ""; frontend/tests/pages/resident-review.test.tsx ""; frontend/tests/unit/wording-review.test.ts "review and notes wording" |  | test |
| UX-323 |  | NOT APPLICABLE |  | specs/TRD/11_User_Interface_UX_Spec.md:719 | retired by TRD 24 D-110 | inspection |
| UX-324 | Must | PASS |  | frontend/components/AlertReviewForm/AlertReviewForm.test.tsx "" |  | test |
| UX-330 | Must | PASS |  | frontend/tests/e2e/mutating.spec.ts ""; frontend/tests/e2e/review.spec.ts ""; frontend/tests/pages/resident-review.test.tsx "" | E2E in CI playwright on 23e558b (success) | test |
| UX-331 | Must | PASS |  | frontend/components/DataProblemsList/DataProblemsList.test.tsx "DataProblemsList"; frontend/tests/e2e/review.spec.ts ""; frontend/tests/e2e/study-team.spec.ts "" (+1 more) | E2E in CI playwright on 23e558b (success) | test |
| UX-350 | Must | PASS |  | frontend/tests/e2e/study-team.spec.ts ""; frontend/tests/pages/study.test.tsx "" | E2E in CI playwright on 23e558b (success) | test |
| UX-351 | Must | PASS |  | frontend/components/KpiTiles/KpiTiles.test.tsx "KpiTiles" |  | test |
| UX-352 | Must | PASS |  | frontend/tests/unit/wording-study.test.ts "" |  | test |
| UX-353 | Must | PASS |  | frontend/tests/unit/format.test.ts "" |  | test |
| UX-354 | Must | PASS |  | frontend/lib/wording/study.ts:45-55; components/KpiTiles/KpiTiles.test.tsx::renders DS-07 values | formed of active, still forming, restarted once/twice/k times, All baselines formed | inspection |
| UX-355 | Must | PASS |  | frontend/components/KpiTiles/KpiTiles.test.tsx "KpiTiles"; frontend/tests/unit/wording-study.test.ts "" |  | test |
| UX-306 | Must | PASS |  | frontend/components/DataProblemsList/DataProblemsList.test.tsx "DataProblemsList"; frontend/tests/pages/study.test.tsx "" |  | test |
| UX-307 | Must | PASS |  | frontend/components/DataProblemsList/DataProblemsList.test.tsx::orders by kind then natural code (UX-307) |  | inspection |
| UX-308 | Must | PASS |  | frontend/components/DataProblemsList/DataProblemsList.tsx:35,44 | resident → /residents/<R>/log, device → /study#devices, aria-label = API title | inspection |
| UX-309 | Must | PASS |  | frontend/components/DataProblemsList/DataProblemsList.test.tsx "DataProblemsList"; frontend/tests/pages/study.test.tsx "" |  | test |
| UX-356 | Must | PASS |  | frontend/components/DailyCheckinsChart/DailyCheckinsChart.test.tsx "" |  | test |
| UX-357 | Must | PASS |  | frontend/components/DailyCheckinsChart/DailyCheckinsChart.tsx:25-31,166-171; DailyCheckinsChart.module.css:34 | stacked Used/Set aside/Held back/Missed per day, ~160px plot, min-width 560px scroll | inspection |
| UX-358 | Must | PASS |  | frontend/tests/unit/wording-study.test.ts "" |  | test |
| UX-359 | Must | PASS |  | frontend/lib/wording/study.ts:101-102 | "Show daily counts as a table" with Date/Used/Set aside/Held back/Missed/Note | inspection |
| UX-360 | Must | PASS |  | frontend/tests/unit/wording-study.test.ts "" |  | test |
| UX-361 | Must | PASS |  | frontend/components/DailyCheckinsChart/DailyCheckinsChart.test.tsx "" |  | test |
| UX-362 | Must | PASS |  | frontend/components/LossFunnel/LossFunnel.test.tsx "LossFunnel" |  | test |
| UX-363 | Must | PASS |  | tests/unit/analytics/test_aggregates.py::test_src05_funnel; frontend/tests/unit/wording-study.test.ts "" |  | test |
| UX-364 | Must | PASS |  | tests/unit/analytics/test_aggregates.py::test_src05_funnel |  | test |
| UX-365 | Must | PASS |  | tests/unit/analytics/test_aggregates.py::test_src05_funnel |  | test |
| UX-366 | Must | PASS |  | tests/unit/analytics/test_aggregates.py::test_src05_funnel; frontend/components/LossFunnel/LossFunnel.test.tsx "LossFunnel"; frontend/tests/unit/wording-study.test.ts "" |  | test |
| UX-367 | Must | PASS |  | frontend/components/UsableByResidentChart/UsableByResidentChart.test.tsx "" |  | test |
| UX-368 | Must | PASS |  | frontend/components/UsableByResidentChart/UsableByResidentChart.tsx:50; UsableByResidentChart.module.css:37 | --c-used meter; code links to /residents/<R>/log | inspection |
| UX-369 | Must | PASS |  | tests/unit/analytics/test_aggregates.py::test_src05_by_resident |  | test |
| UX-370 | Must | PASS |  | frontend/components/UsableByResidentChart/UsableByResidentChart.test.tsx ""; frontend/tests/unit/wording-study.test.ts "" |  | test |
| UX-371 | Must | PASS |  | frontend/components/AlarmTimingTable/AlarmTimingTable.test.tsx "" |  | test |
| UX-372 | Must | PASS |  | frontend/components/AlarmTimingTable/AlarmTimingTable.test.tsx::DS-07: planted rows then Other 8; ::missed, false alarm, 1 day and alarming others |  | inspection |
| UX-373 | Must | PASS |  | frontend/tests/unit/wording-study.test.ts "" |  | test |
| UX-374 | Must | PASS |  | frontend/components/AlarmTimingTable/AlarmTimingTable.test.tsx "" |  | test |
| UX-375 | Must | PASS |  | frontend/components/ReviewOutcomesTable/ReviewOutcomesTable.test.tsx "ReviewOutcomesTable" |  | test |
| UX-376 | Must | PASS |  | frontend/app/(protected)/study/page.tsx:180-190; frontend/lib/wording/study.ts:165 | timing table only when pipeline_profile is test_v0_1, labelled "Test data only"; production shows review outcomes | inspection |
| UX-377 | Should | PASS |  | frontend/app/(protected)/study/page.tsx:174,197-240; frontend/services/api.ts:238; lib/wording/study.ts:256-257 | Downloads panel with Scores (CSV) / Baselines (CSV) | inspection |
| UX-380 | Must | PASS |  | frontend/components/KpiTiles/KpiTiles.test.tsx "KpiTiles" |  | test |
| UX-381 | Must | PASS |  | frontend/components/DailyCheckinsChart/DailyCheckinsChart.test.tsx::renders the DS-07 totals and never the ▲ glyph (UX-361) | DS-07 daily values rendered; also tests/pages/study.test.tsx | inspection |
| UX-382 | Must | PASS |  | frontend/components/LossFunnel/LossFunnel.test.tsx "LossFunnel" |  | test |
| UX-383 | Must | PASS |  | frontend/components/UsableByResidentChart/UsableByResidentChart.test.tsx "" |  | test |
| UX-384 | Must | PASS |  | frontend/components/AlarmTimingTable/AlarmTimingTable.test.tsx ""; frontend/tests/e2e/study-team.spec.ts ""; frontend/tests/pages/study.test.tsx "" | E2E in CI playwright on 23e558b (success) | test |

### 12 Security and Authentication Spec

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| SEC-001 | Must | PENDING BLOCK 4 |  | docs/deployment.md:11; specs/backlog/DEPLOYMENT_CHECKLIST.md:22 | Rule documented; seeds are synthetic (database/seeds/test_v0_1). Hosted data content verifiable only on live stack. | inspection |
| SEC-002 | Must | PASS |  | docs/deployment.md:11; docs/deployment.md:297; specs/backlog/DEPLOYMENT_CHECKLIST.md:23 | Go-live-on-AWS-only rule documented; no live data anywhere. | inspection |
| SEC-003 | Must | PENDING BLOCK 4 |  | specs/backlog/DEPLOYMENT_CHECKLIST.md:23; docs/deployment.md:168; checklist G.08 | Rule documented (test devices only); key issuance happens on hosted stack in Phase 10. | inspection |
| SEC-004 | Must | PASS |  | render.yaml:67; render.yaml:111; frontend/app/(protected)/layout.tsx:37; frontend/components/DataBar/DataBar.tsx:11 | Synthetic labels set per env; DataBar in protected layout (every page) and login. Hosted screenshot = checklist G.11. | inspection |
| SEC-005 | Must | PASS |  | specs/backlog/DEPLOYMENT_CHECKLIST.md:203 (N.13); docs/deployment.md:297 | Checklist includes the signed go-live item, marked n/a for interim. | inspection |
| SEC-007 | Must | PASS |  | render.yaml:47,75,93,119 (region ohio); docs/deployment.md:26,81 | Render ohio in blueprint; Neon aws-us-east-1 documented (creation = checklist B.01, Block 4). | inspection |
| SEC-006 | Must | PASS |  | backend/requirements.txt; frontend/package.json:27-33 | No Render/Netlify/Neon SDK in backend/analytics/frontend runtime deps; @netlify/plugin-nextjs is build-only devDependency. | inspection |
| SEC-010 | Must | PASS |  | tests/integration/api/test_users.py::test_create_user; tests/unit/backend/core/test_security.py::test_hash_and_verify |  | test |
| SEC-011 | Should | PASS |  | tests/integration/api/test_auth.py::test_login_rehashes_a_hash_with_old_parameters; tests/unit/backend/core/test_security.py::test_dummy_hash_is_a_real_argon2id_hash |  | test |
| SEC-012 | Must | PASS |  | tests/integration/api/test_users.py::test_password_policy; tests/integration/test_cli_credentials.py::test_create_user_refuses_a_weak_password; tests/unit/backend/core/test_security.py::test_validate_password_rejects (+2 more) |  | test |
| SEC-013 | Must | PASS |  | tests/integration/api/test_auth.py::test_failed_logins_are_indistinguishable |  | test |
| SEC-014 | Must | PASS |  | tests/integration/api/test_auth.py::test_failed_logins_are_indistinguishable |  | test |
| SEC-015 | Should | PASS |  | tests/integration/api/test_auth.py::test_eleventh_attempt_after_ten_failures_is_locked; tests/integration/api/test_auth.py::test_failures_older_than_fifteen_minutes_do_not_lock |  | test |
| SEC-016 | Must | PASS |  | tests/integration/db/test_repositories.py::test_users_and_api_keys; tests/integration/test_cli_credentials.py::test_create_user_normalises_email_and_audits; tests/unit/backend/core/test_security.py::test_email_normalisation |  | test |
| SEC-017 | Must | PASS |  | tests/integration/test_cli_credentials.py::test_create_user_normalises_email_and_audits |  | test |
| SEC-020 | Must | PASS |  | tests/integration/test_cli_credentials.py::test_create_api_key_prints_the_key_once_and_stores_its_hash; tests/integration/test_cli_credentials.py::test_create_api_key_with_scopes_and_device; tests/unit/backend/core/test_security.py::test_api_key_format_and_hash |  | test |
| SEC-021 | Must | PASS |  | tests/integration/db/test_repositories.py::test_users_and_api_keys; tests/integration/test_cli_credentials.py::test_create_api_key_prints_the_key_once_and_stores_its_hash; tests/unit/backend/core/test_security.py::test_api_key_format_and_hash |  | test |
| SEC-022 | Must | PASS |  | tests/integration/api/test_auth.py::test_api_key_checks; tests/integration/test_cli_credentials.py::test_create_api_key_with_scopes_and_device; tests/security/test_api_keys.py::test_revoked_key_is_invalid |  | test |
| SEC-023 | Must | PASS |  | tests/integration/api/test_sessions.py::test_device_bound_key_refuses_another_device; tests/integration/test_cli_credentials.py::test_create_api_key_with_scopes_and_device |  | test |
| SEC-024 | Must | PASS |  | tests/integration/api/test_auth.py::test_api_key_checks; tests/integration/db/test_repositories.py::test_users_and_api_keys; tests/integration/test_cli_credentials.py::test_revoke_api_key (+1 more) |  | test |
| SEC-025 | Should | PASS |  | tests/integration/api/test_auth.py::test_last_used_at_is_written_at_most_once_a_minute |  | test |
| SEC-026 | Must | PASS |  | tests/integration/api/test_auth.py::test_api_key_checks; tests/security/test_api_keys.py::test_unknown_or_query_string_key_is_refused |  | test |
| SEC-027 | Must | PASS |  | backend/api/deps.py:233-242; backend/api/permissions.py:28-63; tests/integration/api/test_role_checks.py::test_every_matrix_cell | Non-key endpoints answer 401 to API keys; matrix test asserts 401 for key credentials on every route. | inspection |
| SEC-030 | Must | PASS |  | tests/integration/api/test_auth.py::test_valid_login_returns_a_bearer_token; tests/integration/api/test_auth.py::test_bad_tokens_are_refused_with_a_bearer_challenge |  | test |
| SEC-031 | Must | PASS |  | tests/integration/api/test_auth.py::test_valid_login_returns_a_bearer_token; tests/integration/api/test_auth.py::test_bad_tokens_are_refused_with_a_bearer_challenge |  | test |
| SEC-032 | Must | FAIL | S3 | backend/core/config.py:63; render.yaml:62,107 | No guard caps JWT_EXPIRES_MINUTES at 60 in staging/production (le=1440 everywhere); blueprint sets 60 as workaround. No refresh tokens: OK. | inspection |
| SEC-033 | Must | FAIL | S3 | backend/core/config.py:33-35,202-205,227,243-251; tests/unit/backend/core/test_config.py | Length/template/placeholder/profile/AS_OF guards exist, but other repo values (e.g. test secret Zq8vN3x... in tests/) are not refused in staging/production. | inspection |
| SEC-034 | Must | PASS |  | tests/integration/api/test_auth.py::test_deactivated_user_token_stops_working; tests/integration/api/test_role_checks.py::test_role_comes_from_the_database_not_the_token; tests/integration/api/test_users.py::test_update_user |  | test |
| SEC-035 | Must | PASS |  | tests/integration/api/test_auth.py::test_bad_tokens_are_refused_with_a_bearer_challenge |  | test |
| SEC-036 | Must | PASS |  | tests/integration/api/test_auth.py::test_me_and_logout |  | test |
| SEC-037 | Must | PASS |  | frontend/lib/auth.ts:1-19 | Token in module memory + sessionStorage only; no localStorage/cookie use for token. | inspection |
| SEC-038 | Should | PASS |  | frontend/app/(protected)/layout.tsx:12-20; frontend/lib/AuthProvider.tsx:67; frontend/tests/pages/login.test.tsx; frontend/components/LoginForm/LoginForm.test.tsx:26 | Redirect to /login when signed out/expired; expiry message rendered and tested. | inspection |
| SEC-040 | Must | PASS |  | tests/integration/api/test_role_checks.py::test_permissions_equal_the_trd_matrix |  | test |
| SEC-041 | Must | PASS |  | tests/integration/api/test_role_checks.py::test_every_matrix_cell; tests/security/test_auth_matrix.py::test_matrix_covers_every_endpoint; tests/security/test_auth_matrix.py::test_every_cell |  | test |
| SEC-042 | Must | PASS |  | tests/integration/test_auth_coverage.py::test_every_route_has_its_auth_dependency; tests/integration/test_auth_coverage.py::test_production_has_no_docs_route; tests/integration/test_auth_coverage.py::test_a_route_without_auth_is_detected |  | test |
| SEC-043 | Must | PASS |  | frontend/components/AppHeader/AppHeader.tsx:63-70; frontend/lib/roles.ts; frontend/app/(protected)/admin/page.tsx:14; frontend/app/(protected)/study/page.tsx:53; frontend/tests/e2e/auth.spec.ts | Role-gated nav, pages and review/note forms; read-only messages tested (resident-review.test.tsx:73). | inspection |
| SEC-044 | Must | PASS |  | tests/integration/api/test_users.py::test_self_changes |  | test |
| SEC-045 | Must | PASS |  | tests/integration/api/test_alerts.py::test_refusals; tests/security/test_auth_matrix.py::test_every_cell |  | test |
| SEC-046 | Must | NOT APPLICABLE |  | backend/api/permissions.py:62 (PATCH /users/{id}) | Requirement on admin/people process (IRB roster check, 1-day deactivation); deactivation mechanism exists. | inspection |
| SEC-050 | Must | PASS |  | tests/security/test_transport_and_secrets.py::test_production_with_development_jwt_secret_exits_1_without_logging_it; tests/unit/test_render_blueprint.py::test_no_hostnames_or_credentials_in_blueprint |  | test |
| SEC-051 | Must | PASS |  | tests/unit/test_env_templates.py::test_production_template_has_no_secret_value; tests/unit/test_env_templates.py::test_env_example_secrets_empty_and_commented |  | test |
| SEC-052 | Must | PASS |  | .github/workflows/ci.yml:8,226-227; .gitleaks.toml | gitleaks v8.18.4 detect over full history in security-audit on pull_request; allow-list only placeholders. | inspection |
| SEC-053 | Should | PENDING BLOCK 4 |  | gh api repos/EchoWellApp/echowell -> security_and_analysis null (not visible) | Repo setting not readable with available token; platform setting to confirm in Block 4. | inspection |
| SEC-054 | Must | PASS |  | tests/unit/test_env_templates.py::test_no_next_public_variable_holds_a_secret |  | test |
| SEC-055 | Must | FAIL | S4 | .env.example:8; .env.production.example:8; docs/deployment.md:277; docs/reports/DEPLOYMENT_CONFIGURATION_GUIDE.md:119 | Generator and per-env documented; 180-day and departure rotation not in docs/deployment.md or checklist. | inspection |
| SEC-056 | Must | FAIL | S4 | specs/backlog/DEPLOYMENT_CHECKLIST.md:52 (B.04); docs/deployment.md:278 | Per-env role passwords are Block 4 (B.04); 180-day/departure rotation cadence and >=32-char rule not documented in ops docs. | inspection |
| SEC-057 | Must | FAIL | S4 | backend/cli.py:185 (revoke-api-key); docs/deployment.md:212 | Create/revoke CLI exists, but 365-day/device-replacement rotation procedure is not documented for operators. | inspection |
| SEC-058 | Should | FAIL | S3 | backend/services/audit_service.py:79; docs/deployment.md | No code path writes config.changed for secret rotation and docs/deployment.md has no operations log section. | inspection |
| SEC-060 | Must | PENDING BLOCK 4 |  | netlify.toml:27 (HSTS); tests/smoke/test_tls.py; checklist DEP-080(j)/DEP-081(g) | TLS/redirect on hosted origins needs live check; repo-side HSTS header and TLS smoke test exist. | inspection |
| SEC-061 | Must | PASS |  | tests/security/test_transport_and_secrets.py::test_staging_without_sslmode_exits_1_and_local_starts; tests/security/test_transport_and_secrets.py::test_every_database_url_needs_sslmode_require |  | test |
| SEC-062 | Must | PASS |  | tests/security/test_transport_and_secrets.py::test_backend_sends_hsts_in_staging_and_production; tests/smoke/test_production_smoke.py::test_e_hsts_and_https_redirect_on_api; tests/smoke/test_production_smoke.py::test_e_hsts_and_https_redirect_on_frontend (+3 more) |  | test |
| SEC-063 | Must | PENDING BLOCK 4 |  | docs/deployment.md:68,81 | Provider-managed encryption at rest is a Neon platform property; AWS KMS part is AWS cut-over. | inspection |
| SEC-064 | Must | PENDING BLOCK 4 |  | tests/smoke/test_tls.py; render.yaml | No plain-HTTP path is a Render edge property; verify on live origin. | inspection |
| SEC-065 |  | PASS |  | tests/security/test_transport_and_secrets.py::test_no_hsts_outside_deployed_environments |  | test |
| SEC-066 | Should | PENDING BLOCK 4 |  | tests/smoke/test_tls.py::test_tls_policy_api; tests/smoke/test_tls.py::test_tls_policy_frontend | Covered only by post-deploy smoke tests (skipped without SMOKE_API_BASE_URL) | test |
| SEC-070 | Must | PASS |  | tests/unit/test_netlify_config.py::test_header_block_is_byte_identical_to_trd12_excerpt; tests/unit/test_netlify_config.py::test_connect_src_is_exactly_self_and_the_two_render_origins; tests/unit/test_netlify_config.py::test_check_csp_accepts_listed_origins_from_any_directory (+2 more) |  | test |
| SEC-071 | Must | PASS |  | tests/unit/test_netlify_config.py::test_permissions_policy_denies_microphone_and_camera_and_hsts_is_set |  | test |
| SEC-072 | Must | PASS |  | frontend/app/layout.tsx:1-12; frontend/app/fonts/SourceSans3-latin-variable.woff2; netlify.toml:32 (font-src 'self') | Source Sans 3 self-hosted via next/font/local. | inspection |
| SEC-073 | Must | PASS |  | netlify.toml:32 (script-src 'self'); frontend/package.json dependencies | No external script origins, no analytics/tracker packages, no next/script usage. | inspection |
| SEC-074 | Must | PASS |  | frontend/.eslintrc.json:10 | react/no-danger error; no dangerouslySetInnerHTML in frontend source. | inspection |
| SEC-075 | Should | PASS |  | netlify.toml:32; specs/backlog/DEPLOYMENT_CHECKLIST.md:202 (N.12) | unsafe-inline accepted for MVP; nonce CSP deferred to Amplify per TRD. | inspection |
| SEC-076 | Must | PASS |  | frontend/components/NotesList/NotesList.test.tsx:38-52; frontend/.eslintrc.json:10 | HTML in note body rendered as text, tested. | inspection |
| SEC-080 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_unknown_property_is_rejected_without_echoing_input |  | test |
| SEC-081 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_body_size_and_media_type_limits |  | test |
| SEC-082 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_body_size_and_media_type_limits |  | test |
| SEC-083 | Must | PASS |  | .github/workflows/ci.yml:228-229; backend/alembic/versions/0002_seed_config_parameters.py:108 | Bandit -ll (includes B608) in CI; single nosec on constant-only downgrade SQL. | inspection |
| SEC-084 | Must | PASS |  | backend/schemas/common.py:15-21; backend/api/alarms.py:56,72; backend/api/residents.py:4 | Code pattern, UUID path params, enums via typed params. | inspection |
| SEC-085 | Must | PASS |  | tests/integration/api/test_auth.py::test_logs_hold_no_password_token_or_email; tests/integration/api/test_http_middleware.py::test_unhandled_exception_is_a_generic_500 |  | test |
| SEC-086 | Must | PASS |  | backend/services/ingestion.py:490-506; backend/services/export_service.py:42-66 | csv.DictReader text only; exports hold only pattern-constrained codes, numbers, dates, enums (no free text). | inspection |
| SEC-090 | Must | PASS |  | tests/integration/api/test_rate_limits.py::test_ingest_limit_is_per_api_key; tests/integration/api/test_rate_limits.py::test_ingest_routes_are_not_also_capped_by_the_default_limit |  | test |
| SEC-091 | Must | PASS |  | tests/integration/api/test_rate_limits.py::test_sixth_login_in_a_minute_is_rate_limited; tests/integration/api/test_rate_limits.py::test_login_is_not_also_capped_by_the_default_limit |  | test |
| SEC-092 | Should | PASS |  | tests/integration/api/test_rate_limits.py::test_other_endpoints_allow_300_a_minute_per_user |  | test |
| SEC-093 | Must | PASS |  | tests/integration/api/test_rate_limits.py::test_sixth_login_in_a_minute_is_rate_limited; tests/integration/api/test_rate_limits.py::test_other_endpoints_allow_300_a_minute_per_user; tests/integration/api/test_rate_limits.py::test_ingest_limit_is_per_api_key |  | test |
| SEC-094 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_cors_allows_only_configured_origins |  | test |
| SEC-100 | Must | PASS |  | tests/integration/db/test_audit_writer.py::test_every_action_inserts_exactly_one_row |  | test |
| SEC-101 | Must | PASS |  | tests/integration/db/test_audit_writer.py::test_audit_row_shares_the_change_transaction; tests/integration/db/test_audit_writer.py::test_refused_request_rows_survive_a_rollback; tests/unit/backend/services/test_audit.py::test_record_committed_only_for_refused_requests |  | test |
| SEC-102 | Must | PASS |  | tests/unit/backend/test_db_inspection.py::test_audit_writes_only_through_the_audit_modules |  | test |
| SEC-103 | Must | PASS |  | tests/integration/test_cli_credentials.py::test_create_user_normalises_email_and_audits; tests/integration/test_cli_credentials.py::test_revoke_api_key; tests/integration/test_resolve_data_alert.py::test_resolves_a_review_flagged_data_problem (+1 more) |  | test |
| SEC-104 | Must | PASS |  | tests/integration/api/test_notes.py::test_create_note; tests/unit/backend/services/test_audit.py::test_forbidden_details_raise_and_write_nothing |  | test |
| SEC-105 | Must | PASS |  | backend/api/permissions.py:28-63; backend/alembic/versions/0001_initial_schema.py:800-804 | No audit-log endpoint; echowell_readonly has SELECT on audit_logs. | inspection |
| SEC-106 | Must | PASS |  | backend/alembic/versions/0001_initial_schema.py:763-766; backend/jobs/ | audit_logs append-only triggers; no deletion job. | inspection |
| SEC-107 | Must | PASS |  | tests/unit/backend/core/test_logging.py::test_secret_keys_and_credentialed_urls_are_redacted; tests/unit/backend/core/test_logging.py::test_bearer_tokens_api_keys_and_jwts_are_masked_in_text |  | test |
| SEC-108 | Should | PASS |  | tests/integration/api/test_role_checks.py::test_every_matrix_cell; tests/integration/api/test_scores.py::test_scores_csv |  | test |
| SEC-109 | Must | PASS |  | tests/integration/db/test_audit_writer.py::test_every_action_inserts_exactly_one_row; tests/unit/backend/services/test_audit.py::test_unknown_action_raises_before_sql; tests/unit/backend/services/test_audit.py::test_vocabulary_has_24_actions |  | test |
| SEC-110 | Must | PASS |  | database/roles/provision_login_roles.sql:15-45; backend/alembic/versions/0001_initial_schema.py:784-805 | Roles created by provisioning script, never Alembic (no CREATE ROLE in migrations); grants in migration. | inspection |
| SEC-111 | Must | PASS |  | tests/unit/test_render_blueprint.py::test_cron_job; tests/unit/test_render_blueprint.py::test_migration_and_readonly_urls_only_on_the_right_web_service; tests/unit/test_render_blueprint.py::test_blueprint_values_pass_startup_validation (+1 more) |  | test |
| SEC-112 | Must | PASS |  | backend/alembic/versions/0001_initial_schema.py:759-762,790; tests/integration/test_schema_behaviour.py::test_ac_pgs_01_raw_sessions_update_fails_for_app | Trigger + INSERT/SELECT-only grant; delete/truncate tests too. | inspection |
| SEC-113 | Must | PASS |  | tests/integration/test_schema_behaviour.py::test_reviews_and_notes_are_append_only |  | test |
| SEC-114 | Must | PASS |  | tests/integration/db/test_roles.py::test_app_login_cannot_become_readonly; tests/integration/test_schema_behaviour.py::test_ac_pgs_14_ground_truth_only_through_readonly |  | test |
| SEC-116 | Must | PASS |  | tests/integration/api/test_analytics.py::test_read_only_engine; tests/unit/backend/test_db_inspection.py::test_migrations_never_manage_extensions_or_the_database; tests/unit/backend/test_db_inspection.py::test_set_role_only_to_the_migrator (+2 more) |  | test |
| SEC-115 | Must | PENDING BLOCK 4 |  | specs/backlog/DEPLOYMENT_CHECKLIST.md:56 (B.08) | Custody of Neon owner credentials is checklist row B.08 (unchecked, Phase 10); apps use echowell_* roles. | inspection |
| SEC-120 | Must | PASS |  | tests/integration/db/test_master_tables.py::test_no_identifying_columns; tests/security/test_data_minimisation.py::test_responses_and_logs_hold_study_ids_only |  | test |
| SEC-121 | Must | PASS |  | tests/security/test_no_audio.py::test_audio_is_refused_everywhere; tests/security/test_static_scans.py::test_no_personal_or_audio_columns |  | test |
| SEC-122 | Must | PASS |  | tests/security/test_static_scans.py::test_no_secret_or_raw_fields_in_the_api |  | test |
| SEC-123 | Must | PASS |  | backend/models/device.py:45,58; database/seeds/test_v0_1/devices.csv | room_label nullable, 1-60 chars; seeds null. | inspection |
| SEC-124 | Must | PASS |  | frontend/lib/wording/review.ts:86; frontend/components/StaffNotes/StaffNotes.test.tsx:59,166; backend/schemas/notes.py:19 | Hint and 2000-char limit in UI, API and DB. | inspection |
| SEC-125 | Must | PASS |  | database/schema.sql (CREATE TABLE public.users) | users holds email, display_name, password_hash, role, active, login/timestamps only. | inspection |
| SEC-126 | Must | PASS |  | backend/services/validation.py:344-345; tests/integration/api/test_sessions.py::test_withdrawn_resident | 422 RESIDENT_WITHDRAWN tested. | inspection |
| SEC-127 | Must | PASS |  | tests/unit/backend/core/test_monitoring.py::test_unhandled_exception_event_is_sanitised |  | test |
| SEC-128 | Must | PASS |  | tests/security/test_static_scans.py::test_no_forbidden_dependencies; tests/security/test_static_scans.py::test_the_scan_recognises_forbidden_names |  | test |
| SEC-129 | Must | PASS |  | frontend/lib/wording/list.ts:64; frontend/lib/wording/chart.ts:186; backend/api/openapi.py:35 | 'prompt to check in, not a diagnosis' wording. | inspection |
| SEC-150 | Must | PASS |  | .github/dependabot.yml | pip /backend and npm /frontend weekly, github-actions / and docker /backend monthly. | inspection |
| SEC-151 | Must | PASS |  | .github/workflows/ci.yml:221; scripts/ci/audit_gate.py:43-51 | pip-audit over runtime+dev reqs (analytics deps pinned in backend reqs); waivers via SECURITY_EXCEPTIONS.md. Gate passes if pip-audit emits no JSON. | inspection |
| SEC-152 | Must | PASS |  | .github/workflows/ci.yml:224; scripts/ci/audit_gate.py:54-64 | npm audit --omit=dev, high/critical fail (CIC-019 form); D-159 waivers active to 2026-12-20. | inspection |
| SEC-153 | Should | PASS |  | .github/workflows/ci.yml:228-229 | bandit -r backend analytics -ll. | inspection |
| SEC-154 | Must | PASS |  | .github/workflows/*.yml (uses: only actions/* and docker/* major tags); ci.yml:15-16 | All workflows default contents: read; job-level write only where needed. | inspection |
| SEC-155 | Must | FAIL | S3 | frontend/package.json:35; backend/requirements*.txt; frontend/package-lock.json | Python pinned exactly and lockfile committed, but @netlify/plugin-nextjs is '^5.13.1' (not exact). | inspection |
| SEC-156 | Should | FAIL | S3 | SECURITY_EXCEPTIONS.md:11-16; specs/TRD/24 D-159 | Critical Next.js 14.2.35 and high advisories waived until 2026-12-20 by owner decision D-159, beyond 7/30-day patch windows. | inspection |
| SEC-160 | Must | PENDING BLOCK 4 |  | specs/backlog/DEPLOYMENT_CHECKLIST.md:57,152 (B.09, J.01); docs/deployment.md:85 | PITR window to be recorded in Phase 10; regeneration from seeds available (database/seeds). | inspection |
| SEC-161 | Must | NOT APPLICABLE |  | specs/backlog/DEPLOYMENT_CHECKLIST.md:193 (N.03) | AWS cut-over item. | inspection |
| SEC-162 | Should | PENDING BLOCK 4 |  | specs/backlog/DEPLOYMENT_CHECKLIST.md:154 (J.03) | Restore drill needs hosted stack. | inspection |
| SEC-163 | Must | PENDING BLOCK 4 |  | docs/deployment.md:212; specs/backlog/DEPLOYMENT_CHECKLIST.md:145 (I.04) | Recovery procedure documented; demo requires a restore drill. | inspection |
| SEC-170 | Must | PENDING BLOCK 4 |  | docs/deployment.md:271-279; backend/cli.py:185 | Containment table complete in docs; 1-hour executability is a drill. | inspection |
| SEC-171 | Must | PASS |  | docs/deployment.md:281 | Reporting rule documented. | inspection |
| SEC-172 | Must | PASS |  | database/schema.sql (audit_logs ip, request_id); backend/core/logging.py:41; docs/deployment.md:283 | audit rows carry request_id/ip; every log record carries request_id. | inspection |
| SEC-173 | Should | PASS |  | docs/deployment.md:285 | Post-incident note rule documented (private space). | inspection |
| SEC-180 | Must | PASS |  | docs/deployment.md:289 | Governance documented. | inspection |
| SEC-181 | Must | PASS |  | docs/deployment.md:290; backend/jobs/ (nightly_run.py only) | No retention deletion job. | inspection |
| SEC-182 | Must | PASS |  | docs/deployment.md:291; backend/alembic/versions/0001_initial_schema.py:800-805 | Export rule documented; readonly role excludes credential columns. | inspection |
| SEC-183 | Must | PASS |  | docs/deployment.md:292 | Licence rule documented; no DAIC-WOZ data in repo. | inspection |
| SEC-184 | Must | PASS |  | docs/deployment.md:293; specs/business-requirements/REFERENCES.md | Only committed PDF is the PROSPERO record (allowed by TRD 18 / D-29); preprint by link. | inspection |

### 13 Testing Strategy and Acceptance Criteria

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| TST-001 | Must | FAIL | S4 | backend/requirements-dev.txt:5 (pytest==9.1.1); pyproject.toml:57-61 | pytest 9.1.1 (Dependabot cf1b511) not 8.x as TST-001/TRD16 §6 pin; pytest-cov 7.1 vs 5.x; no D entry; Py3.12+TestClient+httpx ok | inspection |
| TST-002 | Must | PASS |  | tests/conftest.py:102-112; .github/workflows/ci.yml:82-98 | DATABASE_URL when APP_ENV=test else testcontainers postgres:16-alpine; no SQLite anywhere in tests | inspection |
| TST-003 | Must | PASS |  | frontend/vitest.config.ts:45-57; frontend/tests/unit, frontend/tests/pages, frontend/components/*/*.test.tsx | Vitest+RTL+jsdom; layout as specified | inspection |
| TST-004 | Must | PASS |  | frontend/playwright.config.ts:5-7; frontend/playwright.isolated.config.ts:26-31; frontend/package.json scripts test:e2e:*; e2e.yml:52 | demo stack, global-setup, grepInvert, isolated config with grep/workers 1/fullyParallel false | inspection |
| TST-005 | Must | PASS |  | tests/conftest.py:31-100 (frozen clock); e2e.yml:207-210 (pytest -p randomly); docs/reports/CHECKPOINT_8_DEPLOYMENT_CONFIG.md:54 | random-order whole suite run locally in CP8 (757 passed); nightly job never yet run on schedule | inspection |
| TST-006 | Must | PASS |  | tests/unit/test_markers.py::test_tst_006_marker_list_is_exact_and_strict; tests/unit/test_markers.py::test_tst_010_every_test_module_named_and_marked |  | test |
| TST-007 | Must | PASS |  | tests/unit/test_repository_layout.py::test_tst_007_no_audio_files_tracked |  | test |
| TST-010 | Must | PASS |  | tests/unit/test_markers.py::test_tst_010_every_test_module_named_and_marked |  | test |
| TST-011 | Must | PASS |  | tests/unit/analytics/test_module_tests_exist.py::test_tst_011_every_analytics_module_has_a_test_file |  | test |
| TST-012 | Should | FAIL | S4 | tests/unit/analytics/test_robust_stats.py:34; tests/unit/analytics/*.py | Test names mostly lack §4.3 case IDs (e.g. test_vectors, test_r01_loudness...; no test_rob_*/test_cus_*); only vc_r/vc_g/tst_011 names carry IDs | inspection |
| TST-013 | Must | FAIL | S3 | tests/trace_report.py:1-30; .github/workflows/ci.yml (no trace_report step); docs/reports/traceability_inspections.md absent | Script exists but CI does not run/publish it, inspections file missing, and many Musts still lack a req marker (this audit) | inspection |
| TST-020 | Must | FAIL | S3 | tests/unit/analytics/test_robust_stats.py:15-34; test_speaker_screen.py; test_cusum_engine.py | Table 4.3-A cases not implemented by ID; ~49 of 83 (ROB-01,SCR-05,BL-01,CUS-07,PIP-03,CFG-05...) have no identifiable test; validation suite covers end results | inspection |
| TST-021 | Must | PASS |  | tests/unit/backend/test_import_boundary.py::test_analytics_imports_are_allowed |  | test |
| TST-022 | Should | PASS |  | tests/unit/analytics/test_pipeline.py::test_deterministic_and_order_independent |  | test |
| TST-030 | Must | PASS |  | tests/unit/backend/services/test_validation.py:128-197 | missing field, type, audio_quality_flag enum, schema_version, pauses negative/non-integer, timestamp format all covered | inspection |
| TST-031 | Must | PASS |  | tests/integration/api/test_ingest.py::test_mapped_header_is_accepted |  | test |
| TST-032 | Must | PASS |  | tests/unit/backend/core/test_security.py::test_hash_and_verify |  | test |
| TST-033 | Must | PASS |  | tests/integration/api/test_residents.py::test_overview |  | test |
| TST-034 | Must | PASS |  | tests/integration/api/test_http_middleware.py:24-53; tests/unit/backend/core/test_errors.py:40-60 | problem+json, body keys, urn:echowell:error:<CODE>, X-Request-ID asserted | inspection |
| TST-040 | Must | PASS |  | tests/integration/db/test_migrations.py::test_tst_040_upgrade_downgrade_upgrade_round_trip |  | test |
| TST-041 | Must | PASS |  | tests/integration/db/test_grants.py::test_app_privileges_are_exactly_section_4_8; tests/integration/db/test_grants.py::test_scores_z_and_tally_checks |  | test |
| TST-042 | Must | PASS |  | tests/integration/db/test_repositories.py::test_epochs_sessions_ledger_baselines_scores |  | test |
| TST-043 | Must | PASS |  | tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed |  | test |
| TST-037 | Must | PASS |  | tests/integration/api/test_sessions.py::test_failed_run_answers_pending |  | test |
| TST-038 | Must | PASS |  | tests/integration/api/test_pipeline.py::test_as_of_precedence; tests/integration/api/test_pipeline.py::test_get_run; tests/unit/backend/core/test_config.py::test_tst_038_production_refuses_pipeline_as_of |  | test |
| TST-044 | Must | PASS |  | tests/integration/api/test_sessions.py::test_repeat_session_id_is_a_duplicate |  | test |
| TST-045 | Must | PASS |  | tests/integration/api/test_sessions.py::test_unknown_resident_is_rejected_and_stored |  | test |
| TST-046 | Must | PASS |  | tests/integration/api/test_ingest.py::test_src05_upload |  | test |
| TST-047 | Must | PASS |  | tests/integration/api/test_ingest.py::test_legacy_file_is_refused |  | test |
| TST-048 | Must | PASS |  | tests/validation/test_harness.py::test_tier_b_matches_the_answer_key |  | test |
| TST-049 | Must | FAIL | S3 | tests/validation/test_invariance.py:95-120 (R10 only, baselines only); tests/validation/test_global_checks.py:261 | No test ingests all SRC-05 one-by-one via POST /sessions and compares all derived tables with batch+full run; only R10 baselines via CSV | inspection |
| TST-050 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_second_run_changes_nothing; tests/validation/test_global_checks.py::test_vc_g12_determinism_and_rebuild |  | test |
| TST-051 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_full_run_on_src05 |  | test |
| TST-052 | Must | PASS |  | tests/integration/pipeline/test_nightly_run.py:43-63 | injected clock across DST: 07/08 UTC dedupe, one run per local night | inspection |
| TST-053 | Must | PASS |  | tests/integration/api/test_ingest.py::test_batch_is_audited_with_the_request_id; tests/integration/api/test_notes.py::test_create_note |  | test |
| TST-054 | Must | PASS |  | tests/integration/api/test_health.py::test_tst_054_health_ok_with_database_up; tests/integration/api/test_health.py::test_tst_054_health_degraded_with_database_down |  | test |
| TST-055 | Must | PASS |  | tests/integration/api/test_residents.py::test_filters_and_paging |  | test |
| TST-056 | Must | PASS |  | tests/integration/api/test_alerts.py::test_reviews; tests/integration/api/test_ui_fixture_ds07.py::test_after_a_review_of_r09 |  | test |
| TST-057 | Must | PASS |  | tests/integration/api/test_alerts.py::test_reviews |  | test |
| TST-058 | Must | PASS |  | tests/integration/api/test_alerts.py::test_invalid_reviews_write_nothing |  | test |
| TST-059 | Must | PASS |  | tests/integration/api/test_alerts.py::test_data_problem_review_creates_then_links |  | test |
| TST-189 | Must | PASS |  | tests/integration/test_resolve_data_alert.py::test_resolves_a_review_flagged_data_problem; tests/integration/test_resolve_data_alert.py::test_refusals_change_nothing |  | test |
| TST-192 | Must | PASS |  | tests/integration/test_cli_pipeline.py:82-125 (test_set_config_then_rebuild) | Covered in another file/values: audit old/new/reason, rebuild message, failed config_changed_requires_rebuild, unknown key/invalid exit 2 | inspection |
| TST-193 | Must | PASS |  | tests/integration/test_cli_pipeline.py:111-125, 70-79 | rebuild --confirm REBUILD succeeds, pipeline.rebuild audit, later runs ok; wrong confirm exits 2 | inspection |
| TST-194 | Must | FAIL | S3 | tests/integration/test_cli_pipeline.py:58-67; backend/cli.py:540-545 | No test of run-pipeline --scope all vs POST /pipeline/run derived-table equality; only scope R01,R02 tested | inspection |
| TST-195 | Must | FAIL | S3 | tests/integration/test_cli_credentials.py:35-90; backend/cli.py:131-191 | Refusals implemented, but tests miss invalid e-mail, duplicate e-mail, unknown role, unknown device, unknown key name | inspection |
| TST-065 | Must | PASS |  | tests/integration/api/test_alerts.py::test_snooze; frontend/tests/e2e/isolated.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| TST-066 | Must | PASS |  | tests/integration/api/test_alerts.py::test_refusals |  | test |
| TST-067 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_reviews_and_snooze_survive_a_rerun |  | test |
| TST-068 | Must | PASS |  | tests/integration/db/test_ground_truth_loader.py::test_refuses_outside_test_v0_1; tests/unit/backend/test_ground_truth_boundary.py::test_only_the_summary_reads_the_answer_key; tests/unit/backend/test_ground_truth_boundary.py::test_a_forbidden_reference_is_found |  | test |
| TST-069 | Must | PASS |  | tests/integration/api/test_auth.py::test_me_and_logout; tests/integration/api/test_pipeline.py::test_list_runs |  | test |
| TST-079 | Must | PASS |  | tests/integration/api/test_scores.py::test_scores_csv |  | test |
| TST-060 | Must | PASS |  | tests/contract/test_openapi_contract.py::test_generated_equals_committed; tests/contract/test_openapi_contract.py::test_served_document_and_docs |  | test |
| TST-061 | Must | PASS |  | tests/contract/test_response_schemas.py::test_valid_responses_pass; tests/contract/test_response_schemas.py::test_contract_breaks_are_caught; tests/integration/api/test_ingest.py::test_batch_detail_and_roles |  | test |
| TST-062 | Must | PASS |  | tests/contract/test_openapi_contract.py::test_path_set |  | test |
| TST-063 | Must | PASS |  | .github/workflows/ci.yml:170-179, 196 | openapi-typescript regenerated and diffed; tsc --noEmit in frontend job | inspection |
| TST-064 | Must | PASS |  | tests/contract/test_response_schemas.py::test_meta_only_where_declared; tests/integration/api/test_residents.py::test_unknown_resident_is_404 |  | test |
| TST-070 | Must | PASS |  | tests/validation/test_answer_key_integrity.py::test_golden_files_match_specs_and_checksums |  | test |
| TST-071 | Must | PASS |  | tests/validation/test_answer_key_integrity.py::test_golden_files_match_specs_and_checksums |  | test |
| TST-072 | Must | PASS |  | tests/fixtures/answer_key/SHA256SUMS; tests/validation/test_answer_key_integrity.py:69-112; git log (golden files unchanged since 81397a0) | Golden files equal specs copies and regeneration test; never edited | inspection |
| TST-073 | Must | PASS |  | tests/validation/test_answer_key_integrity.py::test_diff_answer_key_prints_the_changed_cell |  | test |
| TST-074 | Must | PASS |  | .github/workflows/ci.yml:122-125; tests/validation/comparator.py:21 | Validation suite in required backend-test fails on any answer-key mismatch | inspection |
| TST-075 | Must | PASS |  | git 2a8e6c5 (CP8 perf defects fixed with tests/performance budget tests) | Only recorded defect fixes in analytics/ingest came with regression tests; weak evidence (no defect issues) | inspection |
| TST-080 | Must | PASS |  | tests/validation/test_r01..test_r10_*.py; tests/validation/test_global_checks.py; docs/reports/ALGORITHM_VALIDATION_REPORT.md:10-36 | VC-R01..R10 and VC-G01..G12 all present and PASS | inspection |
| TST-081 | Must | PASS |  | tests/validation/test_harness.py::test_tier_b_matches_the_answer_key; tests/validation/test_harness.py::test_tier_a_equals_tier_b |  | test |
| TST-082 | Must | PASS |  | tests/validation/report.py:4,26-27; .github/workflows/ci.yml:129-138 | Report MD+JSON written and uploaded as backend-reports artifact | inspection |
| TST-083 | Must | PASS |  | tests/validation/test_harness.py::test_a_skipped_validation_test_fails_the_session |  | test |
| TST-084 | Should | PASS |  | tests/validation/test_robustness_check.py::test_not_part_of_the_gating_selection |  | test |
| TST-090 | Must | PASS |  | frontend/components/<Name>/<Name>.test.tsx (45 of 46 dirs); frontend/tests/pages/study.test.tsx | Every TRD 04 §4.8 inventory component has a co-located test (AccessDenied, not in inventory, has none) | inspection |
| TST-091 | Must | PASS |  | frontend/components/StatusPill/StatusPill.test.tsx:7-16; frontend/tests/unit/status-roles-groups.test.ts:7-17 | mapping incl. alarm_on+attention, glyph aria-hidden; border not asserted in test | inspection |
| TST-092 | Must | PASS |  | frontend/components/ResidentsTable/ResidentsTable.test.tsx:68; frontend/tests/pages/residents.test.tsx:49-121 | DS-07 order, texts, filters with ?show= | inspection |
| TST-093 | Must | PASS |  | frontend/components/ChangeScoreChart/ChangeScoreChart.test.tsx "" |  | test |
| TST-094 | Must | PASS |  | frontend/tests/pages/resident-trends.test.tsx "" |  | test |
| TST-095 | Must | FAIL | S3 | grep: no msw/fixture import in frontend/app\|components\|lib\|services (non-test) | Property holds today but no test asserts production builds contain no MSW/fixture imports | inspection |
| TST-096 | Must | PASS |  | frontend/components/SummaryPanel/SummaryPanel.test.tsx "" |  | test |
| TST-097 | Must | PASS |  | frontend/components/SummaryPanel/SummaryPanel.test.tsx "" |  | test |
| TST-100 | Must | PASS |  | frontend/tests/e2e/*.spec.ts (E2E-01..E2E-21, TST-187); .github/workflows/e2e.yml:29,65-89 | All Table 4.10-A scenarios present; Chromium on PR, 3 browsers nightly, isolated run; playwright green on 57adc71 | inspection |
| TST-101 | Must | PASS |  | frontend/playwright.config.ts:9 | retries 1 in CI, 0 locally | inspection |
| TST-110 | Must | PASS |  | frontend/tests/e2e/a11y.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| TST-111 | Must | PASS |  | frontend/tests/e2e/a11y.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| TST-112 | Must | PASS |  | frontend/components/ChangeScoreChart/ChangeScoreChart.test.tsx ""; frontend/components/ChangeScoreTable/ChangeScoreTable.test.tsx "ChangeScoreTable" |  | test |
| TST-113 | Must | PASS |  | frontend/tests/e2e/a11y.spec.ts:25,56 | axe wcag2aa tags include color-contrast | inspection |
| TST-120 | Must | PASS |  | tests/performance/test_pipeline_runtime.py::test_pipeline_on_src05_within_5_s; tests/unit/analytics/test_pipeline.py::test_src05_runs_within_five_seconds; tests/unit/analytics/test_run_engine.py::test_run_engine_on_the_seed_files |  | test |
| TST-121 | Must | PASS |  | tests/performance/test_api_latency.py::test_post_sessions_p95_pr_scope; tests/performance/test_api_latency.py::test_post_sessions_p95_200_requests | Performance test: budget subset in CI backend-test; nightly budgets run locally (CHECKPOINT_8 §5 rows 3-4) | test |
| TST-122 | Must | PASS |  | tests/performance/test_api_latency.py::test_read_endpoints_p95_on_ds08 | Performance test: budget subset in CI backend-test; nightly budgets run locally (CHECKPOINT_8 §5 rows 3-4) | test |
| TST-123 | Must | PASS |  | tests/performance/test_pipeline_runtime.py::test_ds08_full_rebuild_within_120_s | Performance test: budget subset in CI backend-test; nightly budgets run locally (CHECKPOINT_8 §5 rows 3-4) | test |
| TST-124 | Must | PASS |  | tests/integration/api/test_ingest.py::test_batch_duplicates_and_statement_count; tests/performance/test_api_latency.py::test_ingest_src05_accepted_and_processed |  | test |
| TST-125 | Should | PASS |  | frontend/lighthouserc.json; frontend/tests/lighthouse/login.js; .github/workflows/e2e.yml:228-270 | Lighthouse job success on 57adc71 | inspection |
| TST-190 | Must | PASS |  | tests/integration/api/test_rate_limits.py::test_ingest_routes_are_not_also_capped_by_the_default_limit; tests/performance/test_ingest_sustained.py::test_sustained_10_records_per_second_for_60_s |  | test |
| TST-191 | Should | PASS |  | .github/workflows/ci.yml:200; scripts/ci/check-bundle.mjs:1-24 | check:bundle after build, 300 KB gzip | inspection |
| TST-126 | Must | PASS |  | tests/performance/test_api_latency.py::test_post_sessions_p95_pr_scope; tests/performance/test_api_latency.py::test_ingest_src05_accepted_and_processed | Performance test: budget subset in CI backend-test; nightly budgets run locally (CHECKPOINT_8 §5 rows 3-4) | test |
| TST-130 | Must | PASS |  | tests/security/test_auth_matrix.py::test_matrix_covers_every_endpoint; tests/security/test_auth_matrix.py::test_every_cell; tests/security/test_auth_matrix.py::test_pipeline_run_key_scopes |  | test |
| TST-131 | Must | PASS |  | tests/integration/api/test_rate_limits.py::test_sixth_login_in_a_minute_is_rate_limited; tests/integration/api/test_rate_limits.py::test_ingest_limit_is_per_api_key |  | test |
| TST-132 | Must | PASS |  | tests/integration/api/test_auth.py::test_bad_tokens_are_refused_with_a_bearer_challenge; tests/integration/api/test_auth.py::test_api_key_checks; tests/security/test_api_keys.py::test_revoked_key_is_invalid (+6 more) |  | test |
| TST-133 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_body_size_and_media_type_limits; tests/security/test_no_audio.py::test_audio_is_refused_everywhere; tests/security/test_no_audio.py::test_audio_inside_a_multipart_upload_is_refused (+1 more) |  | test |
| TST-134 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_cors_allows_only_configured_origins; tests/integration/api/test_http_middleware.py::test_security_headers_and_hsts; tests/security/test_cors.py::test_preflight (+2 more) |  | test |
| TST-135 | Must | PASS |  | tests/security/test_transport_and_secrets.py::test_backend_sends_hsts_in_staging_and_production; tests/smoke/test_production_smoke.py::test_e_hsts_and_https_redirect_on_api; tests/smoke/test_production_smoke.py::test_e_hsts_and_https_redirect_on_frontend (+2 more) |  | test |
| TST-136 | Should | PASS |  | .github/workflows/ci.yml:204-229; SECURITY_EXCEPTIONS.md | pip-audit, npm audit high (omit dev), gitleaks 8.18.4 every PR; dated exceptions | inspection |
| TST-137 | Must | PASS |  | tests/security/test_data_minimisation.py::test_responses_and_logs_hold_study_ids_only |  | test |
| TST-140 | Must | PASS |  | .github/workflows/ci.yml:126 | --fail-under=95 for analytics | inspection |
| TST-141 | Must | PASS |  | .github/workflows/ci.yml:127 | --fail-under=85 for backend | inspection |
| TST-142 | Must | PASS |  | frontend/vitest.config.ts:51-57; frontend/package.json (@vitest/coverage-v8 2.1.9) | v8, thresholds.lines 80, tests excluded | inspection |
| TST-143 | Should | PASS |  | pyproject.toml:79; .github/workflows/ci.yml:124,139-151 | Branch coverage measured and reported (combined line+branch figure); not gating as allowed | inspection |
| TST-144 | Must | PASS |  | pyproject.toml:83-86 | only __main__ and TYPE_CHECKING excluded; no pragma: no cover in backend/analytics | inspection |
| TST-150 | Must | FAIL | S2 | gh api repos/EchoWellApp/echowell/rules/branches/main (required_status_checks: []); ci.yml, e2e.yml | All jobs run on PRs, but the main ruleset lists zero required status checks (contradicts D-162); red PRs could merge | inspection |
| TST-151 | Should | PASS |  | .github/workflows/e2e.yml:16-17,29,112-226,272-295 | 08:00 UTC schedule, 3 browsers, performance, randomly+robustness, ci-failure issue; no scheduled run yet | inspection |
| TST-152 | Must | PENDING BLOCK 4 |  | tests/smoke/test_production_smoke.py::test_a_health_ok_with_expected_version; tests/smoke/test_production_smoke.py::test_b_frontend_login_page_over_https; tests/smoke/test_staging_smoke.py::test_a_health_ok_with_expected_version | Covered only by post-deploy smoke tests (skipped without SMOKE_API_BASE_URL) | test |
| TST-153 | Must | PASS |  | tests/conftest.py:29,35-52 | collection hook rejects skip markers without requirement/OQ ID | inspection |
| TST-160 | Must | FAIL | S4 | gh api labels (no defect / sev:S* labels); no issues exist | Defects tracked in PR review rounds, never as labelled GitHub issues | inspection |
| TST-161 | Must | PASS |  | tests/validation/guard.py:11; .github/workflows/ci.yml:122 (no reruns) | Validation tests cannot be skipped/xfail/flaky; no flaky occurrences recorded | inspection |
| TST-162 | Must | PASS |  | tests/fixtures/answer_key/SHA256SUMS; git log (golden files untouched since 81397a0) | No golden-file edits; S1 fixes went to code | inspection |
| TST-170 | Must | PENDING BLOCK 4 |  | docs/reports/CHECKPOINT_8_DEPLOYMENT_CONFIG.md | Acceptance on the release candidate with Block 4 PR and GitHub Release evidence | inspection |
| TST-180 | Must | PENDING BLOCK 4 |  |  | Demo acceptance step 4 on the demo environment | inspection |
| TST-181 | Must | PENDING BLOCK 4 |  |  | Demo acceptance step 5 | inspection |
| TST-182 | Must | PENDING BLOCK 4 |  | docs/deployment.md | Demo-time database separation (answer key on isolated DB, real record in production) | inspection |
| TST-183 | Should | PENDING BLOCK 4 |  | docker-compose.yml:65-78; docs/deployment.md:229 | Local fallback demo; repo-side compose demo profile exists | inspection |
| TST-184 | Should | PENDING BLOCK 4 |  |  | Demo resident pill under production profile | inspection |
| TST-185 | Must | FAIL | S3 | backend/services/pipeline_persistence.py:433-445; tests/integration/api/test_admissions.py (no 16th-record transition) | Cohort change implemented, but no test of N01 15→16 records, cohort_changed audit row and list move | inspection |
| TST-186 | Should | PASS |  | tests/integration/api/test_admissions.py::test_comparison_with_ranges |  | test |
| TST-188 | Must | FAIL | S3 | tests/integration/test_seed_logins.py absent; frontend/tests/e2e/global-setup.ts (logs in all roles) | No integration test of seeded logins + LoginRequest email validation; only indirect E2E coverage | inspection |
| TST-187 | Must | PASS |  | frontend/tests/e2e/isolated.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |

### 14 Test Data and Validation Spec

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| TDV-001 | Must | PASS |  | tests/validation/test_harness.py::test_tier_a_matches_the_answer_key |  | test |
| TDV-002 | Must | PASS |  | tests/validation/test_global_checks.py::test_vc_g11_raw_store_fidelity; tests/validation/test_harness.py::test_tier_a_matches_the_answer_key |  | test |
| TDV-003 | Must | PASS |  | tests/validation/test_global_checks.py::test_vc_g07_morning_offsets; tests/validation/test_global_checks.py::test_vc_g08_parameters |  | test |
| TDV-004 | Must | NOT APPLICABLE |  | specs/TRD/14_Test_Data_and_Validation_Spec.md:56 | DS-04 is a future Team 1 dataset (OQ-13), not delivered; nothing to accept | inspection |
| TDV-005 | Must | PASS |  | tests/validation/test_answer_key_integrity.py::test_legacy_file_is_only_a_negative_ingest_fixture |  | test |
| TDV-006 | Must | PASS |  | git ls-files (no DAIC/WOZ files); .github/workflows/*.yml (not used) | DS-06 never committed or used in CI | inspection |
| TDV-007 | Must | PENDING BLOCK 4 |  | tests/integration/test_cli_seed.py:54-63 (seed refused in production); render.yaml:17-19,29-30 | No real records exist yet; separation on hosted DBs checked in Block 4; repo guards exist | inspection |
| TDV-008 | Should | PASS |  | tests/performance/test_load_dataset.py::test_ds08_is_deterministic_and_follows_tdv_008; tests/performance/test_load_dataset.py::test_no_generated_dataset_is_tracked | Performance test: budget subset in CI backend-test; nightly budgets run locally (CHECKPOINT_8 §5 rows 3-4) | test |
| TDV-010 | Must | PASS |  | tests/validation/test_answer_key_integrity.py::test_pipeline_input_folder_holds_only_ds01 |  | test |
| TDV-011 | Must | PASS |  | tests/validation/test_answer_key_integrity.py::test_no_production_code_reads_the_answer_key |  | test |
| TDV-012 | Must | PASS |  | tests/validation/test_answer_key_integrity.py::test_pipeline_input_folder_holds_only_ds01 |  | test |
| TDV-013 | Must | PASS |  | tests/validation/test_answer_key_integrity.py::test_golden_files_match_specs_and_checksums |  | test |
| TDV-014 | Must | PASS |  | tests/validation/test_answer_key_integrity.py::test_golden_files_match_specs_and_checksums |  | test |
| TDV-015 | Must | PASS |  | tests/validation/answer_key.py:43-48 | pandas read_excel engine openpyxl (opens read_only internally); never written | inspection |
| TDV-016 | Must | FAIL | S3 | frontend/tests/fixtures/capture.mjs; frontend/tests/fixtures/ds07/ | Fixtures captured from the API, but no test re-records and diffs them | inspection |
| TDV-020 | Must | PASS |  | tests/validation/test_answer_key_integrity.py::test_regeneration_reproduces_the_golden_files |  | test |
| TDV-021 | Must | PASS |  | tests/fixtures/answer_key/SHA256SUMS; tests/validation/test_answer_key_integrity.py:69-112 | Golden files unchanged since added | inspection |
| TDV-022 | Must | PASS |  | tests/validation/test_global_checks.py::test_vc_g08_parameters |  | test |
| TDV-023 | Should | PASS |  | tests/validation/test_answer_key_integrity.py::test_diff_answer_key_prints_the_changed_cell |  | test |
| TDV-024 | Must | PASS |  | tests/validation/test_answer_key_integrity.py::test_regeneration_reproduces_the_golden_files |  | test |
| TDV-030 | Must | PASS |  | tests/validation/test_harness.py::test_tier_a_matches_the_answer_key |  | test |
| TDV-031 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_a_run_at_an_earlier_as_of_keeps_alert_history; tests/validation/test_harness.py::test_tier_b_matches_the_answer_key |  | test |
| TDV-032 | Must | PASS |  | tests/validation/test_comparator.py::test_tolerance_boundary; tests/validation/test_comparator.py::test_nan_or_missing_actual_fails |  | test |
| TDV-033 | Must | PASS |  | tests/validation/test_comparator.py::test_blank_none_and_type_rules |  | test |
| TDV-034 | Must | PASS |  | tests/validation/test_comparator.py::test_blank_none_and_type_rules |  | test |
| TDV-035 | Must | PASS |  | tests/validation/test_comparator.py::test_blank_none_and_type_rules |  | test |
| TDV-036 | Must | PASS |  | tests/validation/test_comparator.py::test_mismatches_are_all_recorded_with_stage |  | test |
| TDV-037 | Must | PASS |  | tests/validation/test_comparator.py::test_mismatches_are_all_recorded_with_stage; tests/validation/test_comparator.py::test_stage_follows_the_status |  | test |
| TDV-038 | Must | PASS |  | tests/validation/answer_key.py:44-46 (dtype=object); tests/validation/comparator.py:21 | Full stored precision, no rounding | inspection |
| TDV-040 | Must | PASS |  | tests/validation/comparator.py:3-4,92-140 | Declarative SHEETS mapping for Tables 4.5-A..F | inspection |
| TDV-041 | Must | PASS |  | tests/validation/comparator.py:132-138 | Unsigned z compared | inspection |
| TDV-042 | Must | PASS |  | tests/validation/test_comparator.py::test_mismatches_are_all_recorded_with_stage |  | test |
| TDV-050 | Must | PASS |  | tests/validation/test_global_checks.py::test_vc_g01_status_totals; tests/validation/test_global_checks.py::test_vc_g02_annotated_sessions; tests/validation/test_global_checks.py::test_vc_g03_status_counts (+9 more) |  | test |
| TDV-051 | Must | PASS |  | tests/validation/test_r01_clean_control.py::test_vc_r01_clean_control |  | test |
| TDV-052 | Must | PASS |  | tests/validation/test_r02_missing_days.py::test_vc_r02_missing_days |  | test |
| TDV-053 | Must | PASS |  | tests/validation/test_r03_set_aside_sessions.py::test_vc_r03_set_aside_sessions |  | test |
| TDV-054 | Must | PASS |  | tests/validation/test_invariance.py::test_vc_r04_inv_identical_without_the_copies; tests/validation/test_r04_duplicate_records.py::test_vc_r04_duplicate_records |  | test |
| TDV-055 | Must | PASS |  | tests/validation/test_r05_possible_other_speaker.py::test_vc_r05_possible_other_speaker |  | test |
| TDV-056 | Must | PASS |  | tests/validation/test_invariance.py::test_vc_r06_mut_missing_adjustment_is_detected; tests/validation/test_r06_morning_effect.py::test_vc_r06_morning_effect |  | test |
| TDV-057 | Must | PASS |  | tests/validation/test_r07_device_move.py::test_vc_r07_device_move |  | test |
| TDV-058 | Must | PASS |  | tests/validation/test_r08_too_few_sessions.py::test_vc_r08_too_few_sessions |  | test |
| TDV-059 | Must | PASS |  | tests/validation/test_r09_step_change.py::test_vc_r09_step_change |  | test |
| TDV-060 | Must | PASS |  | tests/validation/test_invariance.py::test_vc_r10_frz_frozen_baseline; tests/validation/test_r10_gradual_drift.py::test_vc_r10_gradual_drift |  | test |
| TDV-061 | Must | PASS |  | tests/integration/api/test_ui_fixture_ds07.py::test_as_of_without_clock_override; tests/integration/test_cli_pipeline.py::test_full_seed_ingests_src05_and_runs |  | test |
| TDV-062 | Must | PASS |  | tests/integration/api/test_ui_fixture_ds07.py::test_resident_list |  | test |
| TDV-063 | Must | PASS |  | tests/integration/api/test_ui_fixture_ds07.py::test_resident_list; tests/integration/api/test_ui_fixture_ds07.py::test_resident_list_sorts |  | test |
| TDV-064 | Must | PASS |  | tests/integration/api/test_ui_fixture_ds07.py::test_resident_list |  | test |
| TDV-065 | Must | PASS |  | tests/integration/api/test_ui_fixture_ds07.py::test_resident_list |  | test |
| TDV-066 | Must | PASS |  | tests/integration/api/test_ui_fixture_ds07.py::test_devices; tests/integration/api/test_ui_fixture_ds07.py::test_resident_chart_r09 |  | test |
| TDV-067 | Must | PASS |  | tests/integration/api/test_ui_fixture_ds07.py::test_open_alarms_and_leaning_most |  | test |
| TDV-068 | Must | PASS |  | tests/integration/api/test_ui_fixture_ds07.py::test_exactly_four_data_alerts |  | test |
| TDV-069 | Should | PASS |  | tests/integration/api/test_ui_fixture_ds07.py::test_open_alarms_and_leaning_most |  | test |
| TDV-074 | Must | PASS |  | tests/integration/api/test_ui_fixture_ds07.py::test_study_team_analytics |  | test |
| TDV-075 | Must | PASS |  | tests/validation/test_ui_fixture_recompute.py::test_study_team_figures_match_the_answer_key |  | test |
| TDV-076 | Should | PASS |  | tests/integration/api/test_ui_fixture_ds07.py::test_after_a_review_of_r09 |  | test |
| TDV-100 | Must | PASS |  | tests/integration/db/test_ground_truth_loader.py::test_loads_ds10_and_replaces_contents; tests/validation/test_answer_key_integrity.py::test_ground_truth_agrees_with_test_plan |  | test |
| TDV-101 | Must | PASS |  | tests/unit/backend/test_ground_truth_boundary.py::test_only_the_summary_reads_the_answer_key; tests/validation/test_harness.py::test_ground_truth_never_changes_the_outputs |  | test |
| TDV-102 | Must | PASS |  | tests/validation/test_harness.py::test_ground_truth_never_changes_the_outputs |  | test |
| TDV-103 | Must | PASS |  | tests/integration/db/test_ground_truth_loader.py::test_loads_ds10_and_replaces_contents; tests/integration/db/test_ground_truth_loader.py::test_refuses_outside_test_v0_1; tests/integration/db/test_ground_truth_loader.py::test_malformed_file_leaves_the_table_unchanged |  | test |
| TDV-104 | Must | PASS |  | tests/integration/api/test_analytics.py::test_production_profile |  | test |
| TDV-070 | Must | PASS |  | tests/validation/test_report.py::test_passing_run; tests/validation/test_report.py::test_failing_case_and_zero_checks; tests/validation/test_report.py::test_gating_supplementary_check_fails_overall |  | test |
| TDV-071 | Must | PASS |  | tests/validation/test_report.py::test_failing_case_and_zero_checks |  | test |
| TDV-072 | Must | PASS |  | docs/reports/ALGORITHM_VALIDATION_REPORT.md:41-52 | No failed cases; sections 4/5 present | inspection |
| TDV-073 | Should | PASS |  | tests/validation/test_report.py::test_only_a_full_session_is_complete |  | test |
| TDV-080 | Should | PASS |  | tests/validation/test_robustness_check.py::test_fixture_seed_has_no_false_alarm_and_reproduces |  | test |
| TDV-081 | Should | PASS |  | tests/validation/test_robustness_check.py::test_publish_fills_section_7_only |  | test |
| TDV-082 | Should | PASS |  | tests/validation/test_robustness_check.py::test_fixture_seed_has_no_false_alarm_and_reproduces |  | test |
| TDV-083 | Should | PASS |  | tests/validation/test_robustness_check.py::test_not_part_of_the_gating_selection |  | test |
| TDV-090 | Must | NOT APPLICABLE |  | specs/TRD/24_Risk_Assumptions_and_Open_Questions.md (D-75, OQ-13) | DS-04 not yet received (future dataset) | inspection |
| TDV-091 | Should | NOT APPLICABLE |  |  | DS-04 evaluation research track; dataset not delivered (OQ-13) | inspection |
| TDV-092 | Must | PASS |  | .github/workflows/*.yml (no DS-04 step) | DS-04 does not gate CI | inspection |
| TDV-093 | Should | NOT APPLICABLE |  |  | Offline OQ-09 evaluation on DS-04, research track; dataset not delivered | inspection |

### 15 Deployment and DevOps Spec

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| DEP-001 | Must | PASS |  | backend/core/config.py:42,58 | APP_ENV local/staging/production (+test for tests) | inspection |
| DEP-002 | Must | PENDING BLOCK 4 |  | .github/workflows/deploy-production.yml:153-160; netlify.toml:1-3 | Netlify site builds-stopped setting; repo-side CLI publish exists | inspection |
| DEP-003 | Must | PENDING BLOCK 4 |  | render.yaml:87-128; .github/workflows/deploy-production.yml:113-150 | autoDeployTrigger off + Render API commitId deploy in repo; live services pending | inspection |
| DEP-004 | Must | PENDING BLOCK 4 |  | render.yaml:41-84 (checksPass); netlify.toml | Platform GitHub integrations; staging vars not yet set | inspection |
| DEP-005 | Must | PENDING BLOCK 4 |  | docs/deployment.md:81-84 | Neon branches main/staging live check | inspection |
| DEP-006 | Must | PENDING BLOCK 4 |  | render.yaml:61,106 (JWT_SECRET sync:false per service) | Cross-environment credential rejection needs live envs | inspection |
| DEP-007 | Must | PENDING BLOCK 4 |  | tests/integration/test_cli_seed.py:54-63 | Live DB content; repo refuses seed in production | inspection |
| DEP-008 | Must | PENDING BLOCK 4 |  | docs/deployment.md | Policy on hosted interim stack; checked in Block 4 | inspection |
| DEP-118 | Must | NOT APPLICABLE |  |  | AWS go-live (D-OWNER-3), post-MVP cut-over | inspection |
| DEP-009 | Must | PENDING BLOCK 4 |  | backend/core/config.py:191-195 (sslmode=require check) | TLS on hosted hops and at-rest encryption are platform checks | inspection |
| DEP-010 | Must | PASS |  | tests/unit/test_env_templates.py::test_compose_services_and_no_version_key |  | test |
| DEP-011 | Must | PASS |  | tests/unit/test_env_templates.py::test_compose_db_and_backend_wiring |  | test |
| DEP-012 | Must | PASS |  | tests/unit/test_env_templates.py::test_compose_db_and_backend_wiring |  | test |
| DEP-013 | Should | PASS |  | docker-compose.yml:37-41 | bind mounts backend/analytics, uvicorn --reload | inspection |
| DEP-119 | Must | PASS |  | tests/unit/test_env_templates.py::test_compose_db_and_backend_wiring |  | test |
| DEP-014 | Must | PASS |  | docker-compose.yml:27-54; .github/workflows/e2e.yml:52 (up --wait, green on 57adc71) | Health check with DB gating used by CI | inspection |
| DEP-015 | Must | PASS |  | tests/integration/test_cli_pipeline.py:41-56; .github/workflows/e2e.yml:54 | seed test_v0_1 loads roster, SRC-05, pipeline at as-of | inspection |
| DEP-016 | Must | PASS |  | frontend/tests/e2e/resident-list.spec.ts:28,65-117 | E2E-04 filters and default order on seeded stack (:3001 demo profile) | inspection |
| DEP-017 | Must | PASS |  | tests/unit/test_env_templates.py::test_compose_services_and_no_version_key |  | test |
| DEP-018 | Must | PASS |  | tests/unit/test_env_templates.py::test_development_secrets_are_local_dev_only_placeholders; tests/unit/test_env_templates.py::test_compose_urls_match_development_template_and_hold_placeholders_only; tests/unit/test_env_templates.py::test_no_hosted_database_or_secret_in_container_files |  | test |
| DEP-020 | Must | PASS |  | backend/Dockerfile:5-28; .dockerignore | python:3.12-slim, root context, copies backend/analytics/database/alembic.ini, runtime reqs only | inspection |
| DEP-021 | Must | PASS |  | tests/unit/test_env_templates.py::test_backend_dockerfile_user_and_command; tests/unit/test_env_templates.py::test_dockerignore_excludes_secrets_tests_specs_frontend |  | test |
| DEP-022 | Must | PASS |  | tests/unit/test_env_templates.py::test_backend_dockerfile_user_and_command |  | test |
| DEP-023 | Must | PASS |  | frontend/Dockerfile:7-37; .github/workflows/ci.yml:249-259 | node:20-alpine multi-stage, build args; built in docker-build | inspection |
| DEP-024 | Must | PASS |  | tests/integration/db/test_migrations.py::test_tst_040_upgrade_downgrade_upgrade_round_trip |  | test |
| DEP-030 | Must | PENDING BLOCK 4 |  | docs/deployment.md:81 | SELECT version() on hosted DBs | inspection |
| DEP-031 | Must | PENDING BLOCK 4 |  | docs/deployment.md:26,81 | Neon region is a platform setting | inspection |
| DEP-032 | Must | PENDING BLOCK 4 |  | backend/alembic/env.py:3-6; render.yaml:25,59 | Repo uses DATABASE_MIGRATION_URL for Alembic; Neon pooled/direct endpoints live | inspection |
| DEP-033 | Must | PASS |  | tests/unit/test_render_blueprint.py::test_variables_follow_the_trd21_matrix_and_secrets_are_sync_false |  | test |
| DEP-034 | Must | PASS |  | tests/security/test_transport_and_secrets.py::test_staging_without_sslmode_exits_1_and_local_starts |  | test |
| DEP-035 |  | NOT APPLICABLE |  |  | May contingency, only if Neon unavailable; not invoked | inspection |
| DEP-040 | Must | PASS |  | tests/unit/test_render_blueprint.py::test_web_service; tests/unit/test_render_blueprint.py::test_migration_and_readonly_urls_only_on_the_right_web_service; tests/unit/test_render_blueprint.py::test_only_the_closed_list_reads_database_migration_url (+1 more) |  | test |
| DEP-041 | Must | PASS |  | tests/unit/test_render_blueprint.py::test_web_service |  | test |
| DEP-042 | Must | PASS |  | tests/unit/test_render_blueprint.py::test_web_service |  | test |
| DEP-046 | Must | PASS |  | tests/unit/test_render_blueprint.py::test_cron_job; tests/unit/test_render_blueprint.py::test_blueprint_values_pass_startup_validation |  | test |
| DEP-047 | Must | PASS |  | tests/integration/pipeline/test_nightly_run.py::test_one_run_per_local_night_across_dst |  | test |
| DEP-048 | Must | PASS |  | tests/integration/pipeline/test_nightly_run.py::test_schema_mismatch_refuses; tests/unit/test_render_blueprint.py::test_cron_job |  | test |
| DEP-043 | Must | PASS |  | tests/unit/test_render_blueprint.py::test_web_service |  | test |
| DEP-044 | Must | PASS |  | tests/unit/test_render_blueprint.py::test_four_services_and_two_groups; tests/unit/test_render_blueprint.py::test_staging_matches_trd15_outline_field_by_field |  | test |
| DEP-045 | Must | PASS |  | tests/security/test_transport_and_secrets.py::test_backend_sends_hsts_in_staging_and_production; tests/security/test_transport_and_secrets.py::test_no_hsts_outside_deployed_environments |  | test |
| DEP-050 | Must | PASS |  | tests/unit/test_netlify_config.py::test_build_settings_match_trd15_outline |  | test |
| DEP-051 | Must | PASS |  | tests/security/test_deployed_cors.py::test_deployed_cors_admits_only_its_own_site |  | test |
| DEP-052 | Should | PASS |  | tests/unit/test_netlify_config.py::test_build_settings_match_trd15_outline |  | test |
| DEP-053 | Must | PASS |  | tests/unit/test_netlify_config.py::test_header_block_is_byte_identical_to_trd12_excerpt |  | test |
| DEP-054 | Must | PASS |  | tests/security/test_deployed_cors.py::test_deployed_cors_admits_only_its_own_site; tests/unit/test_netlify_config.py::test_no_api_url_no_context_blocks_no_secrets |  | test |
| DEP-060 | Must | PASS |  | render.yaml:53,99; backend/cli.py:435-462; .github/workflows/deploy-staging.yml:88-107 | Alembic pre-deploy only; reset guarded to local/test/staging + test_v0_1 | inspection |
| DEP-061 | Must | PASS |  | backend/alembic/versions/0001..0004 (drops only in downgrade) | All migrations additive | inspection |
| DEP-062 | Must | PENDING BLOCK 4 |  | .github/workflows/deploy-production.yml:70-94 | Guard on successful deploy-staging run exists; staging run not yet green | inspection |
| DEP-063 | Must | PENDING BLOCK 4 |  | docs/deployment.md:161 | Release-time Neon restore branch | inspection |
| DEP-064 | Should | PASS |  | backend/alembic/env.py:3-6,43 | pg_advisory_xact_lock(0x45434857) in migration transaction | inspection |
| DEP-065 | Must | PASS |  | render.yaml:53,99; docs/deployment.md:13 | alembic exits non-zero on failure; preDeployCommand fails deploy (D-158) | inspection |
| DEP-070 | Must | PASS |  | tests/integration/test_cli_seed.py::test_production_refuses_seed_and_reset |  | test |
| DEP-071 | Must | PASS |  | tests/integration/test_cli_seed.py::test_reset_leaves_config_and_one_audit_row |  | test |
| DEP-072 | Must | PASS |  | tests/integration/test_cli_seed.py::test_bootstrap_is_idempotent |  | test |
| DEP-073 | Must | PENDING BLOCK 4 |  | tests/smoke/test_production_smoke.py:35-80 | Live production content; note: no SQL check possible in smoke (CIC-050 forbids DB URL) | inspection |
| DEP-074 | Should | PENDING BLOCK 4 |  | .github/workflows/deploy-staging.yml:39-57,88-107 | Repo-side re-seed logic exists; live staging pending | inspection |
| DEP-075 | Must | PENDING BLOCK 4 |  | docs/deployment.md:168 | First production admin in Render Shell at release | inspection |
| DEP-080 | Must | PENDING BLOCK 4 |  | tests/smoke/test_staging_smoke.py::test_a_health_ok_with_expected_version; tests/smoke/test_staging_smoke.py::test_b_frontend_login_page; tests/smoke/test_staging_smoke.py::test_c_login_as_seeded_researcher | Covered only by post-deploy smoke tests (skipped without SMOKE_API_BASE_URL) | test |
| DEP-081 | Must | PENDING BLOCK 4 |  | tests/smoke/test_production_smoke.py::test_a_health_ok_with_expected_version; tests/smoke/test_production_smoke.py::test_b_frontend_login_page_over_https; tests/smoke/test_production_smoke.py::test_c_residents_without_token_is_401_problem | Covered only by post-deploy smoke tests (skipped without SMOKE_API_BASE_URL) | test |
| DEP-082 | Should | PENDING BLOCK 4 |  | tests/smoke/wait_for_deploy.py; deploy-staging.yml:66-69 | 15 s poll/15 min timeout in repo; duration measured on live run | inspection |
| DEP-083 | Should | PENDING BLOCK 4 |  | docs/deployment.md:198-200; deploy-production.yml:236-238 | Manual check after production deploy | inspection |
| DEP-085 | Must | PENDING BLOCK 4 |  | docs/deployment.md:214 | Rollback rehearsal | inspection |
| DEP-086 | Must | PASS |  | docs/deployment.md:13; backend/cli.py:435-439 | No downgrade in production; reset refused outside local/test/staging | inspection |
| DEP-087 | Must | PASS |  | tests/integration/test_cli_pipeline.py:70-79; docs/deployment.md:220 | Rebuild reproduces identical derived tables incl. baselines | inspection |
| DEP-095 | Must | PENDING BLOCK 4 |  | docs/deployment.md:85,218 | PITR window to be recorded in Phase 10 | inspection |
| DEP-096 | Must | PENDING BLOCK 4 |  | docs/deployment.md:219 | Weekly dumps by data steward | inspection |
| DEP-097 | Should | PENDING BLOCK 4 |  | docs/deployment.md:221 | Restore drill | inspection |
| DEP-098 | Must | PASS |  | .gitignore:12; .github/workflows/*.yml upload-artifact paths; git ls-files (no dumps) | No dumps committed or uploaded | inspection |
| DEP-090 | Must | PENDING BLOCK 4 |  | docker-compose.yml:65-78; docs/deployment.md:57 | Demo fallback; compose demo profile exists | inspection |
| DEP-091 | Must | PENDING BLOCK 4 |  | docs/deployment.md:229 | Fallback laptop demo | inspection |
| DEP-092 | Must | PENDING BLOCK 4 |  | docs/deployment.md:232 | Fallback rehearsal to be recorded | inspection |
| DEP-093 | Should | PENDING BLOCK 4 |  |  | Demo content | inspection |
| DEP-100 | Should | PASS |  | render.yaml:48,76,94,120 (starter); docs/deployment.md:67-68 | Netlify/Neon free, 2 Starter web + 2 cron ≈ USD 16; D-157 accepts | inspection |
| DEP-101 | Should | PENDING BLOCK 4 |  | docs/deployment.md:250-256 | Weekly live usage check procedure documented | inspection |
| DEP-102 | Should | PASS |  | docs/deployment.md:258 | Fallback order uptime first, staging suspend second | inspection |
| DEP-110 | Must | PASS |  | render.yaml:52,80,98,124; grep backend/analytics/frontend (no RENDER_/Netlify/Neon SDK) | Platform specifics confined to config | inspection |
| DEP-111 | Must | PASS |  | backend/Dockerfile:36; backend/core/config.py:59-61 | PORT default 8000; DB URLs from env | inspection |
| DEP-112 | Must | NOT APPLICABLE |  |  | AWS target platform (post-MVP cut-over) | inspection |
| DEP-113 | Must | NOT APPLICABLE |  |  | AWS target platform (post-MVP cut-over) | inspection |
| DEP-114 | Must | NOT APPLICABLE |  |  | AWS BAA/HIPAA services (post-MVP cut-over) | inspection |
| DEP-115 | Must | NOT APPLICABLE |  |  | AWS CloudWatch (post-MVP cut-over) | inspection |
| DEP-116 | Must | NOT APPLICABLE |  |  | AWS EventBridge (post-MVP cut-over) | inspection |
| DEP-117 | Must | NOT APPLICABLE |  |  | AWS cut-over procedure (post-MVP) | inspection |

### 16 CI CD Pipeline Spec

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| CIC-001 | Must | PASS |  | .github/workflows/*.yml (only deploy-production.yml uses RENDER_API_KEY/NETLIFY_AUTH_TOKEN); render.yaml:46,92 | No other workflow holds platform tokens; integrations themselves are Block 4 | inspection |
| CIC-002 | Must | PASS |  | .github/workflows/ (ci, e2e, deploy-staging, deploy-production, uptime) | Exactly the five files | inspection |
| CIC-003 | Must | PASS |  | .github/workflows/*.yml; render.yaml:53,99 | Migrations only against CI containers/staging re-seed; never production | inspection |
| CIC-010 | Must | PASS |  | .github/workflows/ci.yml:7-11 | pull_request, push main, workflow_dispatch | inspection |
| CIC-011 | Must | PASS |  | .github/workflows/ci.yml:75-77; pyproject.toml:25-27 | ruff check, ruff format --check, mypy (analytics strict) | inspection |
| CIC-012 | Must | PASS |  | .github/workflows/ci.yml:82-89 | postgres:16-alpine service | inspection |
| CIC-013 | Must | PASS |  | .github/workflows/ci.yml:122-125 | one invocation incl. unit/integration/validation (+contract, security) | inspection |
| CIC-014 | Must | PASS |  | tests/validation/comparator.py:6,21,187 | abs 1e-6, exact strings | inspection |
| CIC-015 | Must | PASS |  | .github/workflows/ci.yml:90-117 | provision roles as superuser, three login URLs, upgrade, downgrade base, upgrade (order before tests) | inspection |
| CIC-016 | Must | PASS |  | .github/workflows/ci.yml:126-127 | 95/85 gates | inspection |
| CIC-017 | Must | PASS |  | .github/workflows/ci.yml:180-200; frontend/package.json scripts | npm ci, lint --max-warnings 0, typecheck, format:check, test:coverage, build | inspection |
| CIC-018 | Must | PASS |  | .github/workflows/ci.yml:153-179 | OpenAPI drift and api-types drift | inspection |
| CIC-019 | Must | PASS |  | .github/workflows/ci.yml:221,224; scripts/ci/audit_gate.py:25,44,56 | pip-audit runtime+dev, npm audit --omit=dev high/critical | inspection |
| CIC-020 | Must | PASS |  | .github/workflows/ci.yml:26-29 | audio extension list | inspection |
| CIC-021 | Must | PASS |  | .github/workflows/ci.yml:30-36 | .env files and 10 MB | inspection |
| CIC-022 | Must | PASS |  | .github/workflows/ci.yml:58-63 | Conventional Commit PR title | inspection |
| CIC-023 | Must | PASS |  | .github/workflows/ci.yml:230-248 | non-root UID 10001; no .env/tests/specs/frontend | inspection |
| CIC-024 | Must | PASS |  | .github/workflows/*.yml permissions blocks; deploy-production.yml:226-227 | contents: read default; only release job contents: write (issues: write elsewhere) | inspection |
| CIC-025 | Must | PASS |  | .github/workflows/*.yml uses: (actions/*, docker/* major tags only) | gitleaks via docker image, no third-party action | inspection |
| CIC-026 | Must | PASS |  | .github/workflows/ci.yml:5,113,165 | no secrets; openssl rand JWT_SECRET | inspection |
| CIC-027 | Must | PASS |  | .github/workflows/*.yml runs-on | all ubuntu-24.04 | inspection |
| CIC-030 | Must | PASS |  | .github/workflows/e2e.yml:31-89; frontend/tests/e2e/global-setup.ts:22-26; isolated-setup.ts:1 | demo stack, seed+DS-10, reset per project, mutating group, echowell_demo isolated run | inspection |
| CIC-031 | Must | FAIL | S3 | .github/workflows/e2e.yml:11-18; gh api rules/branches/main | Triggers correct, but playwright is not a required check (ruleset lists no checks) | inspection |
| CIC-032 | Must | PASS |  | frontend/tests/e2e/resident-list.spec.ts; resident-chart.spec.ts; mutating.spec.ts; study-team.spec.ts; admissions.spec.ts | All listed assertions present | inspection |
| CIC-033 | Should | PASS |  | .github/workflows/e2e.yml:272-295 | ci-failure issue via gh with job-scoped issues: write | inspection |
| CIC-035 | Must | PASS |  | .github/workflows/e2e.yml:112-165; tests/performance/; docs/reports/CHECKPOINT_8_DEPLOYMENT_CONFIG.md:15 | schedule/dispatch only; budgets pass in CP8 | inspection |
| CIC-037 | Should | FAIL | S4 | .github/workflows/e2e.yml:167-226; backend/requirements-dev.txt:7 | Job as specified, but pytest-randomly pinned 5.0.0 not 3.x (Dependabot f3a27b7) | inspection |
| CIC-036 | Should | PASS |  | .github/workflows/ci.yml:128 | pytest -m budget in backend-test | inspection |
| CIC-034 | Must | PASS |  | .github/workflows/e2e.yml:43-50 | per-job, ::add-mask::, .env and GITHUB_ENV | inspection |
| CIC-114 | Must | PASS |  | .github/workflows/ci.yml:37-57 | facility-name, wording, LLM SDK checks; repo clean | inspection |
| CIC-115 | Must | PASS |  | .github/workflows/ci.yml:226-229,78; pyproject.toml:39-43; .gitleaks.toml; .gitleaksignore (D-162) | gitleaks full history, Bandit -ll, import-linter contracts | inspection |
| CIC-116 | Should | PASS |  | .github/workflows/e2e.yml:228-270; frontend/lighthouserc.json | PR-only, not required; success on 57adc71 | inspection |
| CIC-040 | Must | PASS |  | tests/unit/test_deploy_wait.py::test_wait_times_out |  | test |
| CIC-041 | Should | PASS |  | .github/workflows/deploy-staging.yml:39-57,88-107 | re-seed on backend/alembic or analytics change or reseed input | inspection |
| CIC-042 | Must | PASS |  | .github/workflows/deploy-staging.yml:108-116 | smoke tests run, job fails on failure (live run pending vars) | inspection |
| CIC-043 | Must | PENDING BLOCK 4 |  | .github/workflows/deploy-staging.yml:77 | environment: staging in repo; branch rule is GitHub env setting (API not accessible) | inspection |
| CIC-050 | Must | PASS |  | .github/workflows/deploy-production.yml:113-160,198-206 | only RENDER_API_KEY/NETLIFY_AUTH_TOKEN; public HTTPS verification | inspection |
| CIC-051 | Must | PASS |  | .github/workflows/deploy-production.yml:162-217 | 15 min wait and smoke failure stop the run | inspection |
| CIC-052 | Must | PASS |  | .github/workflows/deploy-production.yml:219-238 | tag/release only after smoke, for released SHA | inspection |
| CIC-053 | Must | PENDING BLOCK 4 |  | .github/workflows/deploy-production.yml:15-94,96-103 | verify job present; production env required reviewer is a GitHub setting (Block 4) | inspection |
| CIC-060 | Should | PENDING BLOCK 4 |  | .github/workflows/uptime.yml:133-211 | Workflow complete; real URLs/vars not configured yet | inspection |
| CIC-061 | Should | PASS |  | .github/workflows/uptime.yml:135-136 | */30 | inspection |
| CIC-070 | Must | FAIL | S2 | gh api repos/EchoWellApp/echowell/rules/branches/main (required_status_checks: []); branches/main protection.enabled=false | Ruleset 25310033 requires PRs but lists no required status checks; D-162 says configured, live settings disagree | inspection |
| CIC-071 | Must | PASS |  | gh api rules/branches/main (strict_required_status_checks_policy: true) | Up-to-date setting on (but checks list empty, see CIC-070) | inspection |
| CIC-072 |  | FAIL | S4 | SECURITY_EXCEPTIONS.md:11-15 | Waivers run to 20 Dec (D-159 allows), but none references a tracking issue; repo has no issues | inspection |
| CIC-080 | Should | PASS |  | .github/workflows/ci.yml:69-73 | setup-python pip cache on backend/requirements*.txt | inspection |
| CIC-081 | Must | PASS |  | .github/workflows/*.yml (setup-node cache on package-lock; npm ci only) | no npm install | inspection |
| CIC-082 | Should | PASS |  | .github/workflows/ci.yml:242-243,258-259 | gha cache scopes backend/frontend | inspection |
| CIC-083 |  | PASS |  | .github/workflows/ci.yml:189-193 | lockfile + source hash key | inspection |
| CIC-090 | Must | PENDING BLOCK 4 |  | .github/workflows/*.yml (only the 7 named secrets referenced) | Stored GitHub secrets not readable via API; env setup is Block 4 | inspection |
| CIC-091 | Must | PASS |  | .github/workflows/*.yml (no pull_request_target) |  | inspection |
| CIC-092 | Must | PASS |  | .github/workflows/deploy-staging.yml:92-115; deploy-production.yml:114-123 | secrets via env:, Render key via header file | inspection |
| CIC-100 | Must | PASS |  | tests/validation/report.py:4,26-27; .github/workflows/ci.yml:129-138; docs/reports/ALGORITHM_VALIDATION_REPORT.md:10-52 | sections present, upload if: always() | inspection |
| CIC-101 | Must | PASS |  | .gitignore:12,18-20; .github/workflows/*.yml artifact paths | outputs to build/; reports committed only by checkpoint PRs (9c52725 cp9) | inspection |
| CIC-102 | Should | PASS |  | .github/workflows/ci.yml:139-151 | R01-R10 table and coverage in step summary | inspection |
| CIC-110 | Must | PASS |  | gh api actions/workflows/ci.yml/runs?branch=main (last 20 runs all < 12 min) | p90 well under 15 min | inspection |
| CIC-111 | Must | PASS |  | .github/workflows/*.yml timeout-minutes (max 20) |  | inspection |
| CIC-112 | Should | PASS |  | .github/workflows/e2e.yml:33,115,170,231; playwright ~6 min on 57adc71 | timeouts 20; scheduled jobs not yet run | inspection |
| CIC-113 | Should | PASS |  | gh api ci.yml runs (p90 < 12 min) | Trigger condition not met; no split needed | inspection |

### 17 Logging Monitoring and Error Handling

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| LOG-001 | Must | PASS |  | tests/unit/backend/core/test_logging.py::test_json_lines_have_the_required_keys |  | test |
| LOG-002 | Must | PASS |  | tests/unit/backend/core/test_config.py::test_staging_refuses_console_logs; tests/unit/backend/core/test_logging.py::test_console_format_is_one_readable_line |  | test |
| LOG-003 | Must | PASS |  | backend/core/logging.py:183-205 | Stdlib logging, JSON formatter, uvicorn loggers propagate, uvicorn.access disabled. | inspection |
| LOG-004 | Must | PASS |  | tests/unit/backend/core/test_logging.py::test_context_fields_are_added_and_restored |  | test |
| LOG-005 | Must | PASS |  | backend/core/logging.py:138-140; tests/unit/backend/core/test_logging.py::test_json_lines_have_the_required_keys | UTC 'Z' timestamps asserted. | inspection |
| LOG-006 | Must | PASS |  | analytics/ (no 'import logging'/getLogger); analytics/pipeline.py:218-260 | Warnings returned as RunWarning data. | inspection |
| LOG-010 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_one_access_record_per_request_with_levels |  | test |
| LOG-011 | Should | PASS |  | tests/integration/api/test_http_middleware.py::test_one_access_record_per_request_with_levels; tests/integration/api/test_http_middleware.py::test_healthy_health_check_logs_at_debug |  | test |
| LOG-012 | Should | PASS |  | backend/core/config.py:71,301-302; render.yaml:23,34 | Default INFO; DEBUG in deployed envs logs debug_logging_enabled warning (time-box is operator duty). | inspection |
| LOG-020 | Must | PASS |  | backend/core/logging.py:27-39,100-125; tests/integration/api/test_auth.py::test_logs_hold_no_password_token_or_email; tests/unit/backend/core/test_logging.py | Key- and text-based redaction tested. | inspection |
| LOG-021 | Must | PASS |  | backend/services/ingestion.py:182-193,445-453; backend/core/logging.py:28 (body/note keys redacted) | Ingest logs carry ids, counts, field names/codes only. | inspection |
| LOG-022 | Must | PASS |  | tests/integration/api/test_auth.py::test_logs_hold_no_password_token_or_email; backend/api/deps.py:229 | Email absent from logs (tested); user_id UUID context. | inspection |
| LOG-023 | Must | PASS |  | tests/unit/backend/core/test_logging.py::test_secret_keys_and_credentialed_urls_are_redacted; tests/unit/backend/core/test_monitoring.py::test_before_send_drops_request_fields_and_redacts |  | test |
| LOG-024 | Must | PASS |  | tests/unit/backend/core/test_logging.py::test_secret_keys_and_credentialed_urls_are_redacted; tests/unit/backend/core/test_logging.py::test_bearer_tokens_api_keys_and_jwts_are_masked_in_text; tests/unit/backend/core/test_monitoring.py::test_before_send_drops_request_fields_and_redacts |  | test |
| LOG-025 | Must | PASS |  | tests/security/test_no_audio.py | No audio anywhere. | inspection |
| LOG-030 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_request_id_is_echoed_or_generated; tests/unit/backend/core/test_logging.py::test_request_id_acceptance |  | test |
| LOG-031 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_errors_carry_the_request_id_and_problem_shape |  | test |
| LOG-032 | Must | PASS |  | frontend/services/api.ts:78-82,127-133,93-104; frontend/components/SectionState/SectionState.tsx:31 | New UUID per request; 'Reference: <id>' shown in error states. | inspection |
| LOG-033 | Must | PASS |  | tests/integration/api/test_auth.py::test_audit_ip_comes_from_a_valid_forwarded_address |  | test |
| LOG-034 | Must | PASS |  | tests/unit/backend/core/test_logging.py::test_context_fields_are_added_and_restored |  | test |
| LOG-035 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_cors_allows_only_configured_origins |  | test |
| LOG-040 | Must | PASS |  | tests/unit/backend/core/test_errors.py::test_problem_body_shape |  | test |
| LOG-041 | Must | PASS |  | tests/unit/backend/core/test_errors.py::test_catalogue_equals_trd_05 |  | test |
| LOG-042 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_unhandled_exception_is_a_generic_500 |  | test |
| LOG-043 | Must | PASS |  | tests/integration/api/test_http_middleware.py::test_unknown_property_is_rejected_without_echoing_input; tests/unit/backend/core/test_errors.py::test_validation_locations_drop_the_body_segment |  | test |
| LOG-044 | Must | PASS |  | backend/core/error_handlers.py:120-125; backend/core/errors.py:77 | Handlers for AppError, RequestValidationError, HTTPException, OperationalError, Exception. Base class named AppError, not EchoWellError (naming only). | inspection |
| LOG-050 | Must | PASS |  | tests/integration/api/test_sessions.py::test_logs_carry_no_feature_value_or_key |  | test |
| LOG-051 | Must | PASS |  | tests/integration/api/test_sessions.py::test_logs_carry_no_feature_value_or_key |  | test |
| LOG-052 | Must | PASS |  | tests/integration/api/test_sessions.py::test_database_unavailable_is_503 |  | test |
| LOG-053 | Must | FAIL | S3 | backend/services/ingestion.py:175-193,368-442 | No 'ingest_batch_completed' event; batch path logs 'ingest_request' (no ingest_batch_id) and audit row ingest_batch.received. | inspection |
| LOG-054 | Must | PASS |  | tests/integration/api/test_sessions.py::test_failed_run_answers_pending | 201 with pending when the run fails. | inspection |
| LOG-060 | Must | PASS |  | tests/integration/api/test_pipeline.py::test_run_lifecycle_and_snapshot |  | test |
| LOG-061 | Must | PASS |  | backend/services/pipeline_runner.py:391-410; tests/integration/pipeline/test_runner_persistence.py::test_a_failing_resident_is_rolled_back_alone | One transaction per resident; failure rolls back that resident only. | inspection |
| LOG-062 | Must | PASS |  | backend/services/pipeline_runner.py:265-317,399-405 | Run row failed+finished_at+error_message; exception warning; ERROR pipeline_run_failed with pipeline_run_id context. Stage label issue: see LOG-063. | inspection |
| LOG-063 | Must | FAIL | S4 | backend/services/pipeline_runner.py:402; pipeline_runner.py:273 | Failed-resident warnings use stage 'persistence' (not in the list); whole-run exceptions carry no stage name. | inspection |
| LOG-064 | Must | PASS |  | backend/services/pipeline_runner.py:336-337; backend/services/config_service.py:54; analytics/pipeline.py:228,283 | late_arrival, config_mismatch, no_device_assignment as warning objects. | inspection |
| LOG-065 | Must | PASS |  | backend/services/pipeline_runner.py:277-307; analytics/pipeline.py:247-260 | succeeded + counts keys = TRD 23 list; INFO pipeline_run_succeeded with counts, duration_ms. | inspection |
| LOG-066 | Must | PASS |  | tests/integration/api/test_pipeline.py::test_stale_running_run_is_abandoned |  | test |
| LOG-067 | Should | PASS |  | backend/services/pipeline_runner.py:257-317; frontend/components/AdminPanel/RunsTab.tsx | No retry; each run own row; runs listed on /admin. | inspection |
| LOG-070 | Must | PASS |  | tests/unit/backend/core/test_monitoring.py::test_unhandled_exception_event_is_sanitised |  | test |
| LOG-071 | Must | PASS |  | backend/services/health_service.py:17-25; tests/integration/api/test_health.py::test_tst_054_health_degraded_with_database_down | 200 ok / 503 degraded, no auth, only 4 fields. | inspection |
| LOG-072 | Must | PASS |  | backend/core/config.py:305-327; tests/unit/backend/core/test_config.py::test_cfg_06_process_exits_1_with_critical_log | exit 1, CRITICAL startup_config_invalid with names only. | inspection |
| LOG-080 | Must | FAIL | S4 | frontend/app/(protected)/error.tsx; frontend/app/global-error.tsx | Both boundaries show copy + Reload but never show the request reference when available (FE-067). | inspection |
| LOG-081 | Must | FAIL | S4 | frontend/services/api.ts:157-163; frontend/components/SectionState/SectionState.tsx:43-55; frontend/lib/wording/common.ts:99 | 401/403/404 mapped; 429 and 503 messages of LOG-081 absent (only login 429 text, other errors go to panel error state). TRD 04/11 lack these strings. | inspection |
| LOG-082 | Must | PASS |  | tests/unit/backend/core/test_monitoring.py::test_no_browser_sdk |  | test |
| LOG-083 | Must | PASS |  | frontend/components/SectionState/SectionState.tsx:36-58 (QueryState, used by 16 panels/pages) | Per-panel loading/empty/error states. | inspection |
| LOG-090 | Must | PASS |  | tests/integration/db/test_audit_writer.py::test_audit_row_shares_the_change_transaction |  | test |
| LOG-091 | Must | PASS |  | backend/alembic/versions/0001_initial_schema.py:763-766 | audit_logs append-only in DB, independent of log retention. | inspection |
| LOG-092 | Should | PASS |  | tests/unit/backend/services/test_audit.py::test_one_info_record_without_details |  | test |
| LOG-100 | Should | PASS |  | tests/unit/backend/core/test_monitoring.py::test_init_options; tests/unit/backend/core/test_monitoring.py::test_unhandled_exception_event_is_sanitised; tests/unit/backend/core/test_monitoring.py::test_before_send_drops_request_fields_and_redacts |  | test |
| LOG-101 | Must | PASS |  | tests/unit/backend/core/test_monitoring.py::test_empty_dsn_logs_error_and_never_calls_transport |  | test |
| LOG-102 | Must | PASS |  | tests/unit/backend/core/test_monitoring.py::test_dsn_is_ignored_outside_staging_and_production |  | test |
| LOG-103 | Should | PENDING BLOCK 4 |  | .github/workflows/uptime.yml:12-13; docs/deployment.md:238 | Workflow exists (every 30 min); live run history needed. | inspection |
| LOG-110 | Must | PASS |  | render.yaml:69-77,113-121; backend/jobs/nightly_run.py:99-103; tests/integration/pipeline/test_nightly_run.py::test_one_run_per_local_night_across_dst | Cron 0 7,8 UTC, local-hour gate, nightly advisory xact lock; no scheduler in web app. | inspection |
| LOG-111 | Must | PASS |  | tests/integration/pipeline/test_nightly_run.py::test_missed_night_is_reported; tests/unit/backend/core/test_monitoring.py::test_nightly_run_missing_error_is_reported; frontend/components/AdminPanel/AdminPanel.test.tsx "" |  | test |
| LOG-112 | Must | PASS |  | frontend/components/AdminPanel/AdminPanel.test.tsx "" |  | test |
| LOG-113 | Must | PASS |  | backend/requirements.txt; frontend/package.json | No e-mail/SMS/push libraries or code; alerts shown in dashboard only. | inspection |
| LOG-115 | Must | FAIL | S4 | backend/services/pipeline_runner.py:422-427 | data_alerts_updated logs only open counts per kind; resolved counts missing. | inspection |
| LOG-114 | Should | PENDING BLOCK 4 |  | docs/deployment.md:244; specs/backlog/DEPLOYMENT_CHECKLIST.md:162 (K.04) | Watchers documented; confirmation is a Phase 10 GitHub setting. | inspection |
| LOG-120 | Must | PASS |  | render.yaml; backend/requirements.txt; docs/deployment.md:258-268 | No log shipping/additional store; Sentry optional for errors only. | inspection |
| LOG-121 | Must | NOT APPLICABLE |  |  | AWS cut-over item. | inspection |
| LOG-122 | Should | PASS |  | docs/deployment.md:285 | Incident issue holds only URLs, status codes, timestamps. | inspection |

### 18 GitHub Repository Standards

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| GIT-001 | Must | PASS |  | git ls-files top-level = TRD 18 §4.1 layout (specs/TRD/18:47-68); remote EchoWellApp/echowell | Single monorepo; all top-level dirs match the layout. | inspection |
| GIT-002 | Must | PASS |  | git ls-files top-level dirs: analytics backend database docs frontend scripts specs tests (= specs/TRD/18:55-64) | No undeclared top-level directory (extra root files SECURITY_EXCEPTIONS.md, .gitleaks* are files, not dirs). | inspection |
| GIT-003 | Must | FAIL | S4 | docs/architecture.md, docs/algorithm.md, docs/database_design.md are 0-byte files (wc -l = 0) | Skeleton docs kept but never filled in; content lives in docs/design/*. No backlog feature fills them. | inspection |
| GIT-004 | Must | PASS |  | ls specs/TRD \| wc -l = 26 (00_..25_) | Exactly 26 TRD files. | inspection |
| GIT-010 | Must | FAIL | S2 | gh api repos/../rules/branches/main: ruleset 25310033 has dismiss_stale_reviews_on_push=false, require_code_owner_review=false, required_status_checks=[]; direct pushes to main 29 Oct-3 Nov | PR/1 approval/no force/no delete/conversations OK, but no stale dismissal, no CODEOWNER review, no required checks; admin bypass (7 direct pushes by srahavi). | inspection |
| GIT-011 | Must | FAIL | S4 | PR #1 head trd-generation, PR #2 head backlog-generation; later branches feat/cpN-*, docs/*, fix/* comply | Block 1/2 branches lack feat/docs/chore prefix; all Block 3 branches comply. | inspection |
| GIT-012 | Must | FAIL | S3 | git log --first-parent main: 66c7705, aa7358e, fb46e63, f340545, 019b9e1, 756ea3c, caf3ade pushed directly; feat/cp4 built on feat/cp3 (CHECKPOINT_4_BACKEND_API.md:3) | 7 commits reached main without a PR; checkpoint 4 branch was not created from latest main. | inspection |
| GIT-013 | Must | PASS |  | render.yaml:46 staging autoDeployTrigger checksPass; render.yaml:92,118 production 'off'; .github/workflows/deploy-production.yml:16 workflow_dispatch, :103 environment production | Repo-side satisfied; hosted Netlify production auto-publish setting is a Block 4 dashboard item. | inspection |
| GIT-014 | Should | FAIL | S3 | repo settings allow_rebase_merge=true; dependabot PRs #6-#26 and PRs #29/#30 merged with merge commits (git log --first-parent main) | Checkpoint PRs use merge commits (OK) but rebase merging is enabled and non-plan PRs are not squashed. | inspection |
| GIT-015 | Should | PASS |  | gh api repos/EchoWellApp/echowell delete_branch_on_merge=true; git ls-remote shows only main + 3 open dependabot branches | Merged head branches are deleted. | inspection |
| GIT-020 | Must | FAIL | S3 | git log --no-merges 7a607dc..main: 73/126 subjects not Conventional (e.g. 'CP8 group 1b: ...', 'Fix Netlify deploy'); merge titles 'Merge pull request #N' | Most commits on main are not Conventional Commits; CI PR-title check (ci.yml:61) only added in CP8. | inspection |
| GIT-021 | Should | FAIL | S4 | scopes used on main: cp8, security, cli, e2e (git log subjects) | Scopes outside the allowed list are in use. | inspection |
| GIT-022 | Must | PASS |  | no tagged release yet; alembic migrations additive; no API-contract break flagged in git log | No breaking change has occurred pre-v0.1.0, so nothing required the ! marker. | inspection |
| GIT-023 | Should | PASS |  | 106/106 Claude-authored commits carry Co-Authored-By; .github/pull_request_template.md:4 'Prompt batch' section | Attribution trailers present; template records prompt/checkpoint. | inspection |
| GIT-024 | Should | FAIL | S4 | git log 7a607dc..main: 0 'Implements:' lines; 61/106 agent commits cite any requirement/feature ID | Commit bodies do not consistently reference implemented requirement IDs. | inspection |
| GIT-030 | Must | FAIL | S3 | PRs #3,#4,#17,#18,#20,#22,#28,#31 = checkpoints 1-8; but direct pushes to main and cp4 built on cp3 branch (CHECKPOINT_4_BACKEND_API.md:3) | Checkpoint-per-PR structure followed; other changes not always via short-lived PRs; cp4 not branched from latest main. | inspection |
| GIT-031 | Must | FAIL | S3 | feat/cp4 first commit 9289b93 (27 Oct 20:20Z) parent c9b8cd4 on feat/cp3; PR #17 approved/merged 28 Oct 16:58Z; CHECKPOINT_4_BACKEND_API.md:3 | Checkpoint 4 work started while PR #17 (cp3) was still in review. All other checkpoints complied. | inspection |
| GIT-032 | Must | FAIL | S3 | .github/CODEOWNERS:2-10 maps paths to team2-algorithm, but gh api codeowners/errors: 'Unknown owner' for every team; ruleset require_code_owner_review=false | Not enforced by CODEOWNERS; in practice Shaba9 (algorithm lead) approved every PR (workaround). | inspection |
| GIT-033 | Must | FAIL | S3 | PR bodies #18,#20,#22,#28,#29,#30,#31 lack 'Requirements implemented'/'Testing' template sections (only #4,#17 follow template) | Most PR descriptions do not follow .github/pull_request_template.md. | inspection |
| GIT-034 | Should | PASS |  | PR #28 (+45768) / #31 (+6324) split into ordered group commits ('CP7 group 1..6', 'CP8 group 1a..4'); docs/reports/CHECKPOINT_7_FRONTEND.md:31 | Large checkpoints split into ordered sub-batches within the PR. | inspection |
| GIT-035 | Should | PASS |  | gh api pulls: no PR opened for incomplete work; checkpoint PRs opened when ready for review | No incomplete work needed a draft; Should satisfied by practice. | inspection |
| GIT-036 | Should | NOT APPLICABLE |  | PR history: first review within ~1 day for most PRs; #28 (~45 h) and #31 (Thu→Sat) slower | Requirement on reviewers (people), not the build; observation recorded. | inspection |
| GIT-037 | Must | FAIL | S2 | gh api repos/EchoWellApp/echowell/codeowners/errors: 'Unknown owner' for team2-maintainers/-algorithm/-devops on all 14 lines | Teams absent, not visible or lack write access, so CODEOWNERS is inert. Membership unverifiable via API (403). | inspection |
| GIT-040 | Must | PASS |  | .github/workflows/ci.yml:75-76 ruff check / ruff format --check; pyproject.toml:4-18 | Enforced by CI backend-lint job. | inspection |
| GIT-041 | Must | PASS |  | pyproject.toml:25-31 (analytics strict, backend disallow_untyped_defs); ci.yml:77 mypy analytics backend | Enforced by CI. | inspection |
| GIT-042 | Must | PASS |  | frontend/tsconfig.json:7 strict; frontend/package.json:12 --max-warnings 0, :15 prettier --check; ci.yml:195-197 | Enforced by CI frontend job. | inspection |
| GIT-043 | Should | FAIL | S4 | e.g. backend/cli.py:485,556; backend/services/validation.py:371; backend/api/openapi.py:328 — rule named but no reason comment | Many suppressions name the rule but carry no reason. | inspection |
| GIT-044 | Must | PASS |  | frontend components PascalCase; only exceptions api-types.ts (TRD-mandated) and Next.js global-error/not-found; Python snake_case (ruff N) | Naming conventions followed. | inspection |
| GIT-045 | Should | PASS |  | .pre-commit-config.yaml:6-23 ruff, ruff-format, prettier, no-audio-files, no-env-files |  | inspection |
| GIT-050 | Must | PASS |  | checkpoint reports §'Deviations' and TRD 24 D-rows record TRD changes via PR (e.g. D-160..D-170 in PR #31) | TRDs updated by PR when behaviour diverged. | inspection |
| GIT-051 | Must | PASS |  | every specs/TRD file changed in PRs #22,#28,#31 adds a Revision History row (git diff check); approvals by Shaba9 | Revision rows updated; CODEOWNER approval only de facto (see GIT-037). | inspection |
| GIT-052 | Must | PASS |  | all 26 specs/TRD/*.md have the 10 required ## sections (scripted heading check) |  | inspection |
| GIT-053 | Must | PASS |  | grep TBD/TODO/FIXME specs/TRD: none; OQ/ASM/RSK only in specs/TRD/24:79,116,131 |  | inspection |
| GIT-054 | Must | PASS |  | docs/design/*.md cite TRD IDs (38-140 IDs each); docs/deployment.md (65 IDs) | Note docs/architecture.md, algorithm.md, database_design.md are empty (see GIT-003). | inspection |
| GIT-055 | Should | PASS |  | no binary diagram files outside specs/ (git ls-files *.png/*.svg); docs/design use Mermaid |  | inspection |
| GIT-056 | Must | PASS |  | README.md:5 exact statement; README.md:7 local quick start; README.md:33-34 links to specs/TRD/ and docs/ |  | inspection |
| GIT-060 | Must | PENDING BLOCK 4 |  | .github/workflows/deploy-production.yml:61-66 computes/creates v0.x.y tag; gh api tags = [] | No release yet; repo-side workflow exists. | inspection |
| GIT-061 | Must | PENDING BLOCK 4 |  | .github/workflows/deploy-production.yml (version input/tag); no tags | Applies to production releases (Block 4). | inspection |
| GIT-062 | Must | PENDING BLOCK 4 |  | gh api repos/../tags = []; deploy-production.yml:234 gh release create | First release v0.1.0 is a Block 4 event. | inspection |
| GIT-063 | Must | PENDING BLOCK 4 |  | deploy-production.yml:234 sole tag creator; tag protection is a platform setting (API 404/403) | Repo-side done; tag rule unverifiable until Block 4. | inspection |
| GIT-064 | Must | PENDING BLOCK 4 |  | backend/services/health_service.py:23 version=settings.git_sha; deploy-production.yml:234 release --target SHA | Backend reports GIT_SHA; release mapping awaits first release. | inspection |
| GIT-070 | Should | FAIL | S3 | gh api labels: only GitHub defaults (bug, documentation, ...); docs/team_workflow.md (12 lines) has no gh label create script | Project labels (defect, sev:S1..S4, incident, open-question, area:*) absent; dependabot.yml and docs/deployment.md:244 reference them. | inspection |
| GIT-071 | Should | FAIL | S3 | specs/TRD/24: 26 OQs status Open; gh api issues: 0 issues | No open-question issues exist. | inspection |
| GIT-072 | Should | PASS |  | .github/ISSUE_TEMPLATE/bug_report.yml, feature_request.yml (required fields), config.yml blank_issues_enabled: false |  | inspection |
| GIT-073 | Must | PASS |  | 0 issues; PR bodies #3-#31 scanned: no secrets/connection strings/resident data |  | inspection |
| GIT-080 | Must | PASS |  | tests/unit/test_repository_layout.py::test_no_env_file_or_licence_tracked |  | test |
| GIT-081 | Should | PENDING BLOCK 4 |  | security_and_analysis not readable (null/403); repo-side gitleaks gate in ci.yml (.gitleaks.toml) | Platform setting; verify in Block 4. | inspection |
| GIT-082 | Must | PASS |  | docs/deployment.md:271-278 containment within 1 hour incl. secret rotation | Procedure documented; no incident to date. | inspection |
| GIT-083 | Must | PASS |  | tests/conftest.py:31 'test-only-jwt-secret-...'; tests/support/system.py:43; ci.yml:165 openssl rand |  | inspection |
| GIT-084 | Must | PASS |  | workflows reference only STAGING_DATABASE_URL, STAGING_SEED_* x4, RENDER_API_KEY, NETLIFY_AUTH_TOKEN (= TRD 16 §4.9) | Configured secret list itself not readable (403). | inspection |
| GIT-090 | Must | PASS |  | tests/unit/test_repository_layout.py::test_no_env_file_or_licence_tracked |  | test |
| GIT-091 | Must | PASS |  | tests/unit/test_repository_layout.py::test_tst_007_no_audio_files_tracked |  | test |
| GIT-092 | Must | PASS |  | database/seeds/test_v0_1, specs/data-samples, tests/fixtures synthetic only; database/seeds/load_evaluation_ground_truth.py:5 |  | inspection |
| GIT-093 | Must | PASS |  | specs/business-requirements/REFERENCES.md:7 links SRC-07; no preprint/standard committed (git ls-files) |  | inspection |
| GIT-094 | Must | FAIL | S4 | specs/prompts/TRD_Generation_Prompt.md:31 lists 'EchoWell_preprint-113062-submitted.pdf' under specs/business-requirements/ | A document still references the removed repository path for SRC-07 (human-authored prompt). | inspection |
| GIT-095 | Must | FAIL | S4 | frontend/app/fonts/SourceSans3-latin-variable.woff2 (binary not .svg/.png/.ico); tests/fixtures/answer_key/*.xlsx outside specs/; ci.yml:34 checks only 10 MB | Allowed by D-168 and TST-070 but GIT-095 not amended; CI does not check 1 MB/location rule. | inspection |
| GIT-096 | Must | PASS |  | .gitattributes has no lfs filters; no LFS pointers in git ls-files |  | inspection |
| GIT-097 | Should | FAIL | S4 | frontend/app/fonts/SourceSans3-latin-variable.woff2 committed (c9ea154); TRD 24 D-168 accepts it but TRD 18 GIT-097 unchanged | Doc drift: font committed per D-168; TRD 18 not updated. | inspection |
| GIT-100 | Must | PASS |  | tests/unit/test_repository_layout.py::test_gitignore_keeps_generated_references_tracked |  | test |
| GIT-110 | Must | PASS |  | .github/dependabot.yml: pip /backend, npm /frontend, github-actions, docker /backend, target-branch main | Alerts/security-updates toggles not readable via API; frontend/Dockerfile not covered by docker entry. | inspection |
| GIT-111 | Must | FAIL | S4 | PR #21 (python 3.12-slim→3.15-slim) merged 1 Nov, reverted by direct push 019b9e1; backend/Dockerfile:5 now python:3.12-slim | Platform pin upgrade merged before demo (not a security fix), then reverted; current pins compliant. | inspection |
| GIT-112 | Must | PASS |  | tests/unit/backend/core/test_monitoring.py::test_sentry_sdk_pinned_exactly |  | test |
| GIT-113 | Must | PASS |  | dependency PRs #6-#26 merged with all check-runs success (gh api check-runs) | R01-R10 suite did not exist before CP6, which merged after these PRs. | inspection |

### 19 API Contracts OpenAPI Spec

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| OAS-001 | Must | PASS |  | tests/contract/test_openapi_contract.py::test_path_set |  | test |
| OAS-002 | Must | PASS |  | tests/contract/test_openapi_contract.py::test_document_header |  | test |
| OAS-003 | Must | PASS |  | tests/contract/test_openapi_contract.py::test_path_set; tests/contract/test_openapi_contract.py::test_operations_match_skeleton |  | test |
| OAS-004 | Must | PASS |  | tests/contract/test_openapi_contract.py::test_schemas_match_skeleton; tests/unit/backend/schemas/test_request_models.py::test_omitted_is_fine_null_is_refused; tests/unit/backend/schemas/test_request_models.py::test_nullable_request_fields_stay_nullable |  | test |
| OAS-005 | Must | PASS |  | tests/contract/test_openapi_contract.py::test_generated_equals_committed |  | test |
| OAS-006 | Must | PASS |  | tests/contract/test_response_schemas.py::test_valid_responses_pass; tests/contract/test_response_schemas.py::test_contract_breaks_are_caught |  | test |
| OAS-007 | Must | PASS |  | tests/contract/test_openapi_contract.py::test_schemas_match_skeleton; tests/integration/db/test_enums.py::test_dto_enums_equal_pg_enums |  | test |
| OAS-008 | Must | PASS |  | tests/contract/test_openapi_contract.py::test_schemas_match_skeleton |  | test |
| OAS-009 | Must | PASS |  | tests/contract/test_openapi_contract.py::test_shared_components; tests/contract/test_response_schemas.py::test_contract_breaks_are_caught |  | test |
| OAS-010 | Must | PASS |  | tests/contract/test_openapi_contract.py::test_shared_components; tests/contract/test_response_schemas.py::test_request_id_header_is_required |  | test |
| OAS-011 | Must | PASS |  | tests/integration/api/test_scores.py::test_scores_json |  | test |
| OAS-012 | Must | PASS |  | tests/contract/test_openapi_contract.py::test_schemas_match_skeleton; tests/unit/backend/schemas/test_request_models.py::test_omitted_is_fine_null_is_refused |  | test |
| OAS-013 | Must | PASS |  | tests/contract/test_openapi_contract.py::test_operations_match_skeleton; tests/contract/test_openapi_contract.py::test_shared_components |  | test |
| OAS-014 | Must | PASS |  | .github/workflows/ci.yml:172-179; frontend/package.json:21,54 | openapi-typescript 7.13.0 generates api-types.ts; CI fails on diff | inspection |
| OAS-015 | Should | PASS |  | tests/contract/test_openapi_examples.py::test_examples_are_the_trd_examples; tests/contract/test_openapi_examples.py::test_examples_validate_against_their_schemas |  | test |
| OAS-017 | Must | PASS |  | tests/contract/test_response_schemas.py::test_meta_only_where_declared |  | test |
| OAS-018 | Must | PASS |  | tests/contract/test_openapi_contract.py::test_operations_match_skeleton; tests/integration/api/test_scores.py::test_scores_csv |  | test |
| OAS-016 | Must | PASS |  | tests/contract/test_openapi_contract.py::test_no_audio_or_identity_properties |  | test |
| OAS-020 | Must | PASS |  | tests/contract/test_openapi_contract.py::test_path_set |  | test |
| OAS-021 | Must | PASS |  | tests/integration/api/test_ui_fixture_ds07.py::test_resident_list |  | test |
| OAS-022 | Must | PASS |  | tests/validation/test_r09_step_change.py:17-26; tests/validation/tier_b.py:87-93 | R09 series incl. 5.431965 rings and 26.830256 on checked at 1e-6, tier B via GET /scores | inspection |
| OAS-023 | Must | PASS |  | tests/validation/tier_b.py:79-86; tests/validation/answer_key.py:21 | Tier B compares GET /analytics/baselines rows with Exp_baselines (composite label mapped) | inspection |
| OAS-027 | Must | PASS |  | tests/integration/api/test_ui_fixture_ds07.py::test_open_alarms_and_leaning_most |  | test |
| OAS-028 | Must | PASS |  | tests/integration/api/test_ui_fixture_ds07.py::test_study_team_analytics |  | test |
| OAS-024 | Must | PASS |  | tests/validation/tier_b.py:70-73; tests/validation/test_global_checks.py:25,45; tests/integration/api/test_analytics.py:82 | Per-resident status counts from E-18 compared with workbook; totals 267/12/2/2/17/2 checked; status_totals summed in aggregates | inspection |
| OAS-025 | Must | PASS |  | tests/fixtures/trd19_openapi_skeleton.yaml; backend/schemas/ingest.py:37-69 | YAML and model in SRC-05 header order; note committed openapi.json is key-sorted (cli.py:655 sort_keys) | inspection |
| OAS-026 | Must | PASS |  | docs/api_reference/openapi.json (ScoredFeatureKey, FeatureKey, BaselineFeatureKey) | 7 composite features in §6 order; 19 FeatureKey; BaselineFeatureKey adds composite | inspection |

### 20 PostgreSQL Schema Definition

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| PGS-001 | Must | PASS |  | tests/integration/db/test_roles.py::test_extensions_timezone_and_server_version |  | test |
| PGS-002 | Must | PASS |  | tests/integration/db/test_roles.py::test_extensions_timezone_and_server_version; tests/integration/db/test_roles.py::test_0001_fails_without_the_extensions |  | test |
| PGS-003 | Must | PASS |  | tests/integration/db/test_roles.py::test_every_table_is_owned_by_the_migrator_group |  | test |
| PGS-004 | Must | PASS |  | tests/integration/db/test_roles.py::test_group_and_login_roles |  | test |
| PGS-005 | Must | PASS |  | tests/integration/db/test_roles.py::test_enum_labels_and_order_match_trd_20_and_python |  | test |
| PGS-006 | Must | PASS |  | database/schema.sql; tests/integration/db/test_migrations.py::test_alembic_check_reports_no_difference; tests/integration/test_schema_reference.py | 24 tables plus alembic_version | inspection |
| PGS-007 | Must | PASS |  | database/schema.sql:795-1082,304 | 21 uuid gen_random_uuid PKs; audit_logs bigserial; config_parameters (profile,key); cusum_state epoch_id | inspection |
| PGS-008 | Must | PASS |  | database/schema.sql | No timestamp without time zone columns | inspection |
| PGS-009 | Must | PASS |  | tests/integration/db/test_raw_store.py::test_feature_columns_follow_the_src_05_header |  | test |
| PGS-010 | Must | PASS |  | database/schema.sql (FK clauses) | All FKs ON DELETE RESTRICT except scores.processed_session_id CASCADE | inspection |
| PGS-011 | Must | PASS |  | tests/integration/db/test_raw_store.py::test_raw_session_checks |  | test |
| PGS-012 | Must | PASS |  | tests/integration/test_schema_behaviour.py::test_ac_pgs_04_reason_text_must_join_reasons; tests/integration/test_schema_behaviour.py::test_ac_pgs_05_quarantined_needs_screen_detail; tests/integration/test_schema_behaviour.py::test_late_usable_row_without_epoch_or_ordinal |  | test |
| PGS-013 | Must | PASS |  | database/schema.sql:614 | processed_sessions_local_date_ck within +-1 day of UTC date | inspection |
| PGS-014 | Must | PASS |  | database/schema.sql:412,893 | day_ledger_reason_ck rules and unique (resident_id, local_date) | inspection |
| PGS-015 | Must | PASS |  | tests/integration/db/test_master_tables.py::test_shared_device_allowed_and_overlap_rejected; tests/integration/test_schema_behaviour.py::test_ac_pgs_08_one_device_per_resident_per_day |  | test |
| PGS-016 | Must | PASS |  | tests/integration/test_schema_reference.py::test_schema_sql_matches_the_migrated_database |  | test |
| PGS-017 | Must | PASS |  | tests/integration/test_schema_reference.py::test_schema_sql_matches_the_migrated_database |  | test |
| PGS-018 | Must | PASS |  | tests/integration/test_schema_behaviour.py::test_ac_pgs_02_raw_sessions_delete_and_truncate_fail_for_app; tests/integration/test_schema_behaviour.py::test_ac_pgs_02_raw_sessions_delete_and_truncate_fail_for_owner |  | test |
| PGS-019 | Must | PASS |  | tests/integration/test_cli_seed.py::test_purge_resident_removes_every_row_but_keeps_audit; tests/integration/test_schema_behaviour.py::test_ac_pgs_09_purge_setting_allows_delete_only; tests/unit/backend/core/test_db.py::test_migrator_setup_statements |  | test |
| PGS-020 | Must | PASS |  | database/schema.sql:1460-1556 | Every table with updated_at has BEFORE UPDATE set_updated_at trigger (parsed) | inspection |
| PGS-021 | Must | PASS |  | tests/integration/db/test_grants.py::test_app_privileges_are_exactly_section_4_8; tests/integration/db/test_grants.py::test_readonly_reads_everything_but_credentials; tests/integration/db/test_grants.py::test_ac_pgs_12_readonly_cannot_read_password_hash |  | test |
| PGS-022 | Must | PASS |  | tests/integration/db/test_grants.py::test_ac_pgs_13_every_fk_restricts_except_scores |  | test |
| PGS-023 | Must | PASS |  | tests/integration/db/test_migrations.py::test_alembic_check_reports_no_difference |  | test |
| PGS-024 | Must | PASS |  | tests/integration/db/test_config_seed.py::test_ac_pgs_10_config_rows_per_profile; tests/integration/db/test_config_seed.py::test_repository_reads_the_23_keys; tests/integration/db/test_repositories.py::test_config_update |  | test |
| PGS-025 | Must | PASS |  | tests/integration/db/test_config_seed.py::test_ac_pgs_10_config_rows_per_profile |  | test |
| PGS-026 | Must | PASS |  | backend/cli.py:757-765; tests/integration/test_cli_seed.py::test_production_refuses_seed_and_reset | seed refused with exit 2, nothing written, when APP_ENV=production | inspection |
| PGS-027 | Must | PASS |  | tests/unit/backend/core/test_db.py::test_remote_urls_need_tls_outside_local_and_test |  | test |
| PGS-028 | Must | PASS |  | tests/unit/backend/core/test_errors.py::test_append_only_refusal_names_the_table |  | test |
| PGS-029 | Must | PASS |  | tests/integration/db/test_repositories.py::test_alerts_reviews_notes_and_data_alerts; tests/integration/test_schema_behaviour.py::test_one_non_closed_alert_per_epoch |  | test |
| PGS-030 | Must | PASS |  | tests/integration/test_schema_behaviour.py::test_one_open_epoch_per_resident |  | test |
| PGS-031 | Must | PASS |  | tests/integration/db/test_repositories.py::test_epochs_sessions_ledger_baselines_scores |  | test |
| PGS-032 | Must | PASS |  | tests/integration/db/test_grants.py::test_scores_z_and_tally_checks; tests/unit/backend/schemas/test_json_columns.py::test_score_z_needs_the_composite_keys |  | test |
| PGS-033 | Must | PASS |  | tests/unit/backend/schemas/test_json_columns.py::test_adjusted_features_need_exactly_the_19_keys |  | test |
| PGS-034 | Must | PASS |  | tests/integration/api/test_users.py::test_create_user; tests/integration/api/test_users.py::test_duplicate_email; tests/integration/db/test_master_tables.py::test_user_email_and_hash_constraints |  | test |
| PGS-035 | Must | PASS |  | tests/integration/db/test_master_tables.py::test_api_key_constraints |  | test |
| PGS-036 | Must | PASS |  | tests/integration/api/test_notes.py::test_invalid_notes; tests/integration/test_schema_behaviour.py::test_reviews_and_notes_are_append_only |  | test |
| PGS-037 | Must | PASS |  | tests/integration/db/test_master_tables.py::test_withdrawn_needs_a_date |  | test |
| PGS-038 | Should | PASS |  | tests/integration/db/test_indexes.py::test_every_section_4_7_index_exists_as_defined |  | test |
| PGS-040 | Must | PASS |  | tests/integration/db/test_grants.py::test_app_privileges_are_exactly_section_4_8; tests/integration/db/test_roles.py::test_group_and_login_roles; tests/integration/db/test_roles.py::test_app_login_cannot_become_readonly (+2 more) |  | test |
| PGS-041 | Must | PASS |  | database/schema.sql:394-395,1208 | data_alerts subject/run CHECKs and partial unique open index NULLS NOT DISTINCT | inspection |
| PGS-042 | Must | PASS |  | tests/integration/test_schema_behaviour.py::test_reviews_and_notes_are_append_only |  | test |
| PGS-043 | Must | PASS |  | tests/integration/test_schema_behaviour.py::test_snooze_needs_both_columns |  | test |
| PGS-044 | Must | PASS |  | tests/integration/test_schema_behaviour.py::test_audit_action_format |  | test |
| PGS-039 | Must | PASS |  | tests/integration/test_schema_behaviour.py::test_ac_pgs_15_data_alert_rules_and_no_alert_delete |  | test |

### 21 Environment Configuration Spec

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| ENV-001 | Must | PASS |  | backend/core/config.py:53 Settings(BaseSettings), :290 @lru_cache get_settings; os.environ only in config.py | database/seeds/load_evaluation_ground_truth.py:82 reads os.environ (outside backend/, refusal guard). | inspection |
| ENV-002 | Must | PASS |  | tests/unit/backend/core/test_config.py::test_operator_commands_need_only_their_subset; tests/unit/backend/test_entry_points.py::test_nightly_run_refuses_test_profile_in_production |  | test |
| ENV-003 | Should | PASS |  | tests/unit/backend/core/test_config.py::test_unknown_echowell_variable_rejected |  | test |
| ENV-004 | Must | PASS |  | tests/security/test_transport_and_secrets.py::test_repr_masks_the_five_secret_settings; tests/unit/backend/core/test_config.py::test_secrets_masked_in_repr |  | test |
| ENV-005 | Must | PASS |  | tests/unit/test_render_blueprint.py::test_variables_follow_the_trd21_matrix_and_secrets_are_sync_false |  | test |
| ENV-006 | Must | PASS |  | tests/unit/backend/core/test_config.py::test_dotenv_ignored_in_staging |  | test |
| ENV-010 | Must | PASS |  | tests/unit/backend/core/test_config.py::test_cfg_06_production_refuses_test_profile; tests/unit/backend/test_entry_points.py::test_nightly_run_refuses_test_profile_in_production |  | test |
| ENV-011 | Must | PASS |  | tests/security/test_transport_and_secrets.py::test_staging_without_sslmode_exits_1_and_local_starts; tests/security/test_transport_and_secrets.py::test_every_database_url_needs_sslmode_require; tests/unit/backend/core/test_config.py::test_staging_requires_sslmode_but_local_does_not (+2 more) |  | test |
| ENV-012 | Must | PASS |  | tests/unit/backend/core/test_config.py::test_tst_038_production_refuses_pipeline_as_of; tests/unit/backend/core/test_config.py::test_production_refuses_unsafe_cors_and_console_logs; tests/unit/backend/core/test_config.py::test_staging_refuses_console_logs |  | test |
| ENV-013 | Must | PASS |  | tests/unit/backend/core/test_config.py::test_short_jwt_secret_rejected_everywhere; tests/unit/backend/core/test_config.py::test_deployed_refuses_template_and_placeholder_secrets |  | test |
| ENV-014 | Must | PASS |  | tests/unit/backend/core/test_config.py::test_database_url_normalised_with_query_preserved |  | test |
| ENV-015 | Must | PASS |  | tests/unit/backend/core/test_config.py::test_forbidden_facility_name_rejected |  | test |
| ENV-016 | Must | PASS |  | backend/services/meta_service.py:14-29 facility_name/facility_tz/data_source_label/as_of/baseline_n/cusum_h/pipeline_profile |  | inspection |
| ENV-017 | Must | PASS |  | backend/services/pipeline_runner.py:113-117 explicit → PIPELINE_AS_OF (not production) → now; meta_service.py:18 latest succeeded run as_of |  | inspection |
| ENV-018 | Must | PASS |  | tests/integration/api/test_health.py::test_tst_054_health_ok_with_database_up |  | test |
| ENV-054 | Must | PASS |  | tests/unit/backend/core/test_config.py::test_login_rate_limit_fixed_in_deployed_environments |  | test |
| ENV-053 | Must | PASS |  | tests/unit/backend/core/test_config.py::test_operator_commands_need_only_their_subset; tests/unit/backend/test_entry_points.py::test_cli_without_command_prints_help; tests/unit/test_render_blueprint.py::test_blueprint_values_pass_startup_validation |  | test |
| ENV-020 | Must | PASS |  | tests/integration/api/test_config_ui.py::test_ui_config |  | test |
| ENV-021 | Must | PASS |  | backend/services/config_service.py:44 no rows → ConfigError; pipeline_runner.py:358-365 run fails pipeline_config_invalid; :50 config_default_used | Behaviour met at run time; no explicit startup check in backend/main.py lifespan. | inspection |
| ENV-022 | Must | FAIL | S3 | backend/services/config_service.py:52-56 adds per-run config_mismatch warning; backend/main.py:53-66 lifespan logs nothing for FACILITY_TZ mismatch | Startup WARNING config_mismatch not implemented; per-run warning and profile precedence are. | inspection |
| ENV-030 | Must | PASS |  | frontend/tests/unit/config.test.ts "parsePublicConfig" |  | test |
| ENV-031 | Must | PASS |  | tests/unit/test_env_templates.py::test_no_next_public_variable_holds_a_secret |  | test |
| ENV-032 | Should | PASS |  | frontend/components/EnvironmentRibbon/EnvironmentRibbon.test.tsx "EnvironmentRibbon" |  | test |
| ENV-033 | Must | PASS |  | frontend/next.config.js:7 COMMIT_REF \|\| GIT_SHA \|\| 'unknown' |  | inspection |
| ENV-040 | Must | PASS |  | tests/unit/backend/core/test_env_templates.py::test_env_040_every_settings_field_in_env_example; tests/unit/backend/core/test_env_templates.py::test_env_040_templates_match_trd21; tests/unit/test_env_templates.py::test_production_template_has_no_secret_value (+2 more) |  | test |
| ENV-041 | Must | PASS |  | tests/security/test_transport_and_secrets.py::test_production_with_development_jwt_secret_exits_1_without_logging_it; tests/security/test_transport_and_secrets.py::test_placeholders_refused_for_web_and_operator_processes; tests/unit/backend/core/test_config.py::test_deployed_refuses_template_and_placeholder_secrets (+5 more) |  | test |
| ENV-050 | Must | PASS |  | tests/unit/test_env_templates.py::test_production_template_profile_and_as_of; tests/unit/test_env_templates.py::test_production_template_requires_sslmode_and_no_readonly_url; tests/unit/test_env_templates.py::test_production_template_matches_matrix (+3 more) |  | test |
| ENV-051 | Must | PENDING BLOCK 4 |  | docs/reports/DEPLOYMENT_CONFIGURATION_GUIDE.md:119 unique secret per env; tests/unit/test_env_templates.py:139 dev JWT refused in production | Hosted values set in Block 4. | inspection |
| ENV-052 | Must | PASS |  | backend/core/security.py:109 HS256, no refresh token; docs/deployment.md:277 rotate JWT_SECRET + redeploy | Stateless JWT verified against JWT_SECRET; rotation invalidates tokens. | inspection |

### 22 Third Party Services and Hosting

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| TPS-001 | Must | PASS |  | backend/requirements.txt, frontend/package.json deps; docs/deployment.md:73 services list | Only listed services (GitHub, Netlify, Render, Neon, optional Sentry). | inspection |
| TPS-002 | Must | PASS |  | docs/deployment.md:11; seeds only database/seeds/test_v0_1 and specs/data-samples (backend/cli.py:81) | Repo-side satisfied; hosted data held synthetic. | inspection |
| TPS-003 | Must | NOT APPLICABLE |  | AWS go-live item (D-OWNER-3/4); docs/deployment.md:11 | No go-live in MVP build; AWS cut-over is post-MVP. | inspection |
| TPS-004 | Must | PASS |  | render.yaml:47,75,93,119 region ohio; docs/deployment.md:26 Neon aws-us-east-1 | Neon region itself is a Block 4 dashboard check. | inspection |
| TPS-005 | Must | PENDING BLOCK 4 |  | docs/deployment.md:63-69 owner/administrator columns | Account ownership/MFA verified in Block 4. | inspection |
| TPS-006 | Must | PENDING BLOCK 4 |  | docs/deployment.md:63-69 table; 'Verified on' = 'recorded in Phase 10' | Table exists; verification dates pending Block 4. | inspection |
| TPS-007 | Must | PENDING BLOCK 4 |  | docs/deployment.md:61 limits indicative until verified at account creation |  | inspection |
| TPS-010 | Must | PASS |  | netlify.toml:17 only @netlify/plugin-nextjs; no netlify/functions or edge functions in repo |  | inspection |
| TPS-011 | Must | PASS |  | netlify.toml:12-14 NODE_VERSION, NEXT_TELEMETRY_DISABLED; NEXT_PUBLIC_* as site vars (netlify.toml:19) | Site env vars in dashboard checked in Block 4. | inspection |
| TPS-020 | Must | PASS |  | render.yaml:52,98 RENDER_GIT_COMMIT export only; no Render SDK/API in backend/ or analytics/ |  | inspection |
| TPS-021 | Should | PASS |  | render.yaml:48-49,94-95 plan starter, numInstances 1, no scaling; docs/deployment.md:250 weekly usage check |  | inspection |
| TPS-030 | Must | PASS |  | docs/deployment.md:24 Neon branches; DATABASE_URL/DATABASE_MIGRATION_URL switch documented |  | inspection |
| TPS-031 | Must | PENDING BLOCK 4 |  | docs/deployment.md:24,26 Neon PG16 aws-us-east-1 main/staging | Neon project configuration is a Block 4 platform check. | inspection |
| TPS-032 | Must | PASS |  | backend/requirements.txt psycopg[binary]==3.2.4; no Neon driver/SDK |  | inspection |
| TPS-040 | Must | PENDING BLOCK 4 |  | docs/deployment.md:65; org settings not readable (API 403) | Org 2FA requirement unverifiable from repo. | inspection |
| TPS-041 | Must | PASS |  | repo public; ci.yml gitleaks + .env/audio guards; no issues; PR bodies clean |  | inspection |
| TPS-050 | Must | PASS |  | frontend/tests/e2e/privacy.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| TPS-051 | Must | PASS |  | tests/unit/test_netlify_config.py::test_connect_src_is_exactly_self_and_the_two_render_origins |  | test |
| TPS-060 |  | PASS |  | tests/unit/backend/core/test_monitoring.py::test_no_browser_sdk |  | test |
| TPS-061 | Must | PENDING BLOCK 4 |  | backend/core/monitoring.py:9; docs/deployment.md:266 go-live rule; production SENTRY_DSN decision 'recorded in Phase 10' | Repo-side rule documented; production value set in Block 4. | inspection |
| TPS-070 | Must | NOT APPLICABLE |  | AWS target (post-MVP cut-over) |  | inspection |
| TPS-071 | Must | NOT APPLICABLE |  | AWS target (post-MVP cut-over) |  | inspection |
| TPS-072 | Must | NOT APPLICABLE |  | AWS target (post-MVP cut-over); no AWS access in workflows |  | inspection |
| TPS-080 | Must | PASS |  | tests/security/test_static_scans.py::test_no_forbidden_dependencies |  | test |
| TPS-081 | Must | PASS |  | tests/security/test_static_scans.py::test_no_forbidden_dependencies; frontend/tests/e2e/privacy.spec.ts "" | E2E in CI playwright on 23e558b (success) | test |
| TPS-082 | Must | PASS |  | tests/security/test_static_scans.py::test_no_forbidden_dependencies |  | test |
| TPS-083 | Must | PASS |  | tests/security/test_static_scans.py::test_no_forbidden_dependencies |  | test |
| TPS-084 | Must | PASS |  | tests/security/test_static_scans.py::test_no_forbidden_dependencies |  | test |
| TPS-085 | Must | PASS |  | tests/security/test_static_scans.py::test_no_forbidden_dependencies |  | test |
| TPS-086 | Must | PASS |  | tests/security/test_static_scans.py::test_no_forbidden_dependencies |  | test |

### 23 Data Model and Entity Definitions

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| DME-001 | Must | PASS |  | backend/models/*.py; tests/integration/db/test_migrations.py::test_alembic_check_reports_no_difference | Declarative classes per entity; alembic check reports no diff | inspection |
| DME-002 | Must | PASS |  | tests/unit/analytics/test_config.py::test_feature_constants; tests/unit/analytics/test_feature_specs.py::test_features_equal_trd_23 |  | test |
| DME-003 | Must | PASS |  | tests/integration/db/test_roles.py::test_enum_labels_and_order_match_trd_20_and_python |  | test |
| DME-004 | Must | PASS |  | docs/api_reference/openapi.json; tests/security/test_data_minimisation.py::test_responses_and_logs_hold_study_ids_only | Paths and DTOs use resident_code/device_code; no residents.id/devices.id exposed | inspection |
| DME-005 | Must | PASS |  | tests/integration/api/test_ingest.py::test_batch_detail_and_roles; tests/integration/api/test_users.py::test_list_and_access; tests/security/test_static_scans.py::test_no_secret_or_raw_fields_in_the_api |  | test |
| DME-006 | Must | PASS |  | analytics/quality_screening.py:44; database/schema.sql (session_status enum lacks pending_screen); tests/unit/analytics/test_pipeline.py::test_src05_counts_and_sessions | pending_screen exists only in memory; status counts 267/12/2/2 | inspection |
| DME-007 | Must | PASS |  | tests/integration/api/test_alerts.py::test_reviews |  | test |
| DME-021 | Must | PASS |  | tests/integration/api/test_alerts.py::test_invalid_reviews_write_nothing |  | test |
| DME-022 | Must | PASS |  | tests/integration/api/test_alerts.py::test_snooze |  | test |
| DME-023 | Must | PASS |  | tests/integration/api/test_ui_fixture_ds07.py::test_exactly_four_data_alerts; backend/services/pipeline_persistence.py:361-392 | Exactly 4 open data alerts R08, R05, R03, D02 | inspection |
| DME-024 | Must | PASS |  | backend/services/analytics_summary.py:1-60; tests/integration/api/test_ui_fixture_ds07.py:210; tests/unit/backend/test_ground_truth_boundary.py | Ground truth read only for the Alarm timing check | inspection |
| DME-025 | Must | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_reviews_and_snooze_survive_a_rerun; ::test_second_run_changes_nothing | alerts/reviews/notes/data_alerts keep ids across reruns | inspection |
| DME-008 | Should | PASS |  | tests/integration/db/test_repositories.py::test_resident_transitions |  | test |
| DME-009 | Must | PASS |  | tests/integration/db/test_repositories.py::test_resident_transitions; tests/integration/test_cli_seed.py::test_withdraw_resident |  | test |
| DME-010 | Must | PASS |  | backend/repositories/read_models.py (baseline_progress); tests/integration/api/test_ui_fixture_ds07.py::test_exactly_four_data_alerts | not_started/forming/frozen derived; R08 13 of 16 | inspection |
| DME-011 | Must | PASS |  | backend/services/resident_service.py:111-160; tests/integration/api/test_ui_fixture_ds07.py::test_resident_list | status, needs_attention, alarm_reviewed derived on read, not stored | inspection |
| DME-012 | Must | PASS |  | tests/integration/db/test_read_models.py::test_baseline_progress_watching_and_alarm_since; tests/integration/db/test_read_models.py::test_derived_facts_are_not_stored |  | test |
| DME-013 | Must | FAIL | S4 | backend/services/pipeline_persistence.py:241-305; backend/schemas/json_columns.py:119-127 | Pipeline writes adjusted_features, scores.z, data_alerts.days via ORM without the json_columns Pydantic helpers; DB CHECKs still guard shape | inspection |
| DME-014 | Must | PASS |  | backend/schemas/json_columns.py:1-5; tests/validation/tier_b.py:87-93 | Floats stored/serialised unrounded; tier B 1e-6 round trip of scores through the API | inspection |
| DME-015 | Must | PASS |  | backend/services/ingestion.py:219-280; tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed | resident_id/device_id resolved to FKs; codes kept in resident_code/device_code | inspection |
| DME-016 | Must | PASS |  | tests/validation/comparator.py; tests/validation/test_comparator.py | Validation compares DB output with SRC-03 (exact strings, 1e-6 floats) | inspection |
| DME-017 | Must | PASS |  | tests/validation/tier_b.py:60-66 | no-record rows compared with day_ledger status, others with processed_sessions | inspection |
| DME-018 | Must | PASS |  | tests/integration/api/test_ingest.py::test_legacy_file_is_refused | SRC-06 legacy file -> 422 CSV_HEADER_MISMATCH, raw rows unchanged | inspection |
| DME-019 | Must | PASS |  | analytics/morning_offset.py:22-29; tests/unit/analytics/test_morning_offset.py::test_src05_r06_mornings | UTC stored; local date/time/morning via facility tz | inspection |
| DME-020 | Must | PASS |  | tests/integration/db/test_master_tables.py::test_no_identifying_columns; tests/security/test_static_scans.py::test_no_personal_or_audio_columns |  | test |

### 24 Risk Assumptions and Open Questions

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| RAQ-001 | Must | PASS |  | specs/TRD/24:79 OQ table: all 32 rows have an Owner (scripted check) |  | inspection |
| RAQ-002 | Must | PASS |  | specs/TRD/24:79: statuses Open (26) / Answered <date> (6) |  | inspection |
| RAQ-003 | Must | PASS |  | specs/TRD/24:79: every OQ Raised cell has date + source |  | inspection |
| RAQ-004 | Must | PASS |  | specs/TRD/24:79: all 26 Open OQs have an interim decision |  | inspection |
| RAQ-005 | Must | PASS |  | specs/TRD/24:79 interim decisions consistent; no contradiction found in this audit |  | inspection |
| RAQ-006 | Must | PASS |  | scripted grep of OQ/ASM/RSK/D IDs in TRD 00-23,25: 0 undefined in TRD 24 |  | inspection |
| RAQ-007 | Must | PASS |  | scripted check: no duplicate OQ/ASM/RSK/DSC/D IDs in TRD 24 |  | inspection |
| RAQ-008 | Must | PASS |  | specs/TRD/24:116 all 8 ASM rows have a validation step |  | inspection |
| RAQ-009 | Must | PASS |  | specs/TRD/24:131 all 17 RSK rows have L and I in {L,M,H} |  | inspection |
| RAQ-010 | Must | PASS |  | specs/TRD/24:131 all RSK rows have mitigation, contingency, owner, links |  | inspection |
| RAQ-011 | Must | PASS |  | specs/TRD/24:101-103 OQ-21..23 record answer, date and source; OQ-30..32 likewise |  | inspection |
| RAQ-012 | Must | PASS |  | backend/cli.py:572 set-config audited (record_cli); tests/integration/test_cli_pipeline.py::test_set_config_then_rebuild |  | inspection |
| RAQ-013 | Must | PASS |  | tests/validation/test_global_checks.py::test_vc_g08_parameters; docs/reports/CHECKPOINT_6_VALIDATION.md:11 overall PASS |  | inspection |
| RAQ-014 | Must | PASS |  | specs/TRD/24:107-109 OQ-27..OQ-29 added by agent with owner, Open, raised date, interim |  | inspection |
| RAQ-015 | Should | PASS |  | gh api pulls/N/reviews: Shaba9 approved every PR #1-#31 before merge |  | inspection |
| RAQ-016 | Must | PASS |  | specs/TRD/24:153 all 14 DSC rows have sources, resolution, tracking |  | inspection |
| RAQ-017 | Must | PASS |  | specs/TRD/24:172 all 169 D rows have motivation and implemented-in |  | inspection |
| RAQ-018 | Must | PASS |  | frontend/lib/wording/review.ts:11,67 (OQ-25, OQ-05/26); common.ts:8 PI marker (OQ-12); admin.ts:6 (OQ-08) |  | inspection |

### 25 AI Agent Build Instructions

| ID | Priority | Status | Severity | Evidence | Note | Source |
|---|---|---|---|---|---|---|
| AGT-001 | Must | PASS |  | docs/reports/CHECKPOINT_*.md §'Deviations, conflicts and notes' (e.g. CHECKPOINT_1_DESIGN_DOCS.md §3) | Conflicts reported per checkpoint. | inspection |
| AGT-002 | Must | PASS |  | ci.yml:36-60 hygiene guards; checkpoint review rounds amend TRDs via D-rows rather than diverge | Umbrella requirement; specific deviations are reported under their own IDs. | inspection |
| AGT-003 | Must | PASS |  | frontend Next.js 14.2.35 (package.json:28), FastAPI 0.115 (backend/requirements.txt:3), render.yaml, netlify.toml, ci.yml |  | inspection |
| AGT-004 | Must | PASS |  | tests/security/test_static_scans.py::test_no_forbidden_dependencies |  | test |
| AGT-005 | Must | PASS |  | ci.yml:46-60 blocks ML/LLM packages/imports; analytics/ pure robust stats + CUSUM, no ML deps |  | inspection |
| AGT-006 | Must | PASS |  | tests/security/test_no_audio.py::test_audio_is_refused_everywhere |  | test |
| AGT-007 | Must | PASS |  | tests/validation/test_answer_key_integrity.py::test_no_production_code_reads_the_answer_key |  | test |
| AGT-008 | Must | PASS |  | tests/validation/test_global_checks.py::test_vc_g08_parameters; tests/validation/test_answer_key_integrity.py | test_v0_1 parameters/answer key guarded. | inspection |
| AGT-009 | Must | PASS |  | specs/TRD/24:107-109 OQ-27..29 added with interim decisions |  | inspection |
| AGT-010 | Must | PASS |  | tests/unit/test_repository_layout.py::test_skeleton_files_kept |  | test |
| AGT-011 | Must | PASS |  | code/docs use specs/TRD/; specs/prompts/Test_Case_Generation_Prompt.md:23 still says specs/TRDS/ (interpreted per rule) | Note: OQ-22 answer says all prompts corrected, but this one was not. | inspection |
| AGT-012 | Must | FAIL | S4 | 106 commits authored 'Claude' made before review (e.g. CP8 groups committed 5-7 Nov, first review 7 Nov 21:40Z) | Agent commits and opens PRs itself; human review gates merge, not commits. Process drift from literal rule. | inspection |
| AGT-013 | Must | FAIL | S3 | Checkpoint PRs #3,#4,#17,#18,#20,#22,#28,#31 each approved by Shaba9; cp4 branch built on feat/cp3 before PR #17 merged (CHECKPOINT_4_BACKEND_API.md:3) | One checkpoint not created from latest main / started before previous merge. | inspection |
| AGT-014 | Must | PASS |  | backend/cli.py:81 seeds from database/seeds/test_v0_1; database/seeds/load_evaluation_ground_truth.py:5 tests/fixtures; docs/deployment.md:11 |  | inspection |
| AGT-015 | Must | PASS |  | tests/unit/backend/core/test_config.py::test_cfg_06_production_refuses_test_profile; tests/unit/backend/core/test_config.py::test_cfg_06_process_exits_1_with_critical_log; tests/unit/backend/core/test_config.py::test_tst_038_production_refuses_pipeline_as_of (+2 more) |  | test |
| AGT-016 | Must | PASS |  | git ls-files: only *.example env files; gitleaks gate; REFERENCES.md:7 | Agent did not commit secrets; human-authored prompt still names removed PDF (see GIT-094). | inspection |
| AGT-017 | Must | PASS |  | tests/security/test_data_minimisation.py::test_responses_and_logs_hold_study_ids_only |  | test |
| AGT-018 | Must | PASS |  | grep diagnos\|severity frontend: only negative wording frontend/lib/wording/list.ts:64, chart.ts:186-187; ci.yml:40 |  | inspection |
| AGT-019 | Must | PASS |  | tests/unit/backend/core/test_config.py::test_forbidden_facility_name_rejected |  | test |
| AGT-020 | Must | PASS |  | analytics/config.py PipelineConfig/FeatureSpec; grep float literals in analytics stage modules: none |  | inspection |
| AGT-021 | Must | PASS |  | tests/unit/analytics/test_pipeline.py::test_deterministic_and_order_independent; tests/validation/test_global_checks.py::test_vc_g12_determinism_and_rebuild |  | test |
| AGT-022 | Must | PASS |  | docs/reports/CHECKPOINT_2..8 sections: Tests added, Commands run and results, New OQ and D IDs, Deviations |  | inspection |
| AGT-023 | Must | PASS |  | docs/reports/CHECKPOINT_6_VALIDATION.md:11 R01-R10 PASS (PR #22 merged 2 Nov) before cp7 frontend started |  | inspection |
| AGT-024 | Must | PASS |  | tests/unit/test_repository_layout.py::test_requirements_pinned_without_psycopg2 |  | test |
| AGT-025 | Must | PASS |  | tests/validation/test_answer_key_integrity.py::test_legacy_file_is_only_a_negative_ingest_fixture; only use tests/integration/api/test_ingest.py:113 (rejected) |  | inspection |
| AGT-030 | Must | FAIL | S3 | Checkpoint order 1-8 correct, but cp4 (Phase 5) started on 27 Oct before PR #17 (cp3) merged 28 Oct | A phase started before the previous checkpoint PR was merged. | inspection |
| AGT-031 | Must | PASS |  | PR #2 (Block 2 backlog) merged before Block 3; specs/backlog/BACKLOG.md |  | inspection |
| AGT-032 | Must | PASS |  | docs/reports/*.md; specs/backlog/BACKLOG.md, DEPLOYMENT_CHECKLIST.md, MVP_READINESS_CHECKLIST.md |  | inspection |
| AGT-033 | Must | PASS |  | docs/reports/CHECKPOINT_2..8 §'Exit criteria' all verified before approval |  | inspection |
| AGT-040 |  | PASS |  | tests/unit/analytics/test_morning_offset.py::test_local_time_vectors; tests/validation/test_r06_morning_effect.py::test_vc_r06_morning_effect |  | test |
| AGT-041 |  | PASS |  | tests/validation/test_r01_clean_control.py::test_vc_r01_clean_control |  | test |
| AGT-042 |  | PASS |  | tests/validation/test_global_checks.py::test_vc_g05_baselines |  | test |
| AGT-043 |  | PASS |  | tests/integration/db/test_raw_store.py::test_same_session_id_twice_gets_increasing_arrival_seq; tests/validation/test_invariance.py::test_vc_r04_inv_identical_without_the_copies; tests/validation/test_r04_duplicate_records.py::test_vc_r04_duplicate_records |  | test |
| AGT-044 |  | PASS |  | tests/validation/test_r05_possible_other_speaker.py::test_vc_r05_possible_other_speaker |  | test |
| AGT-045 |  | PASS |  | tests/validation/test_r07_device_move.py::test_vc_r07_device_move |  | test |
| AGT-046 |  | PASS |  | tests/validation/test_global_checks.py::test_vc_g09_day_ledger; tests/validation/test_r02_missing_days.py::test_vc_r02_missing_days |  | test |
| AGT-047 |  | PASS |  | tests/validation/test_r09_step_change.py::test_vc_r09_step_change; tests/validation/test_r10_gradual_drift.py::test_vc_r10_gradual_drift |  | test |
| AGT-048 |  | PASS |  | tests/validation/test_r09_step_change.py::test_vc_r09_step_change; tests/validation/test_r10_gradual_drift.py::test_vc_r10_gradual_drift |  | test |
| AGT-049 |  | PASS |  | tests/validation/test_r03_set_aside_sessions.py::test_vc_r03_set_aside_sessions |  | test |
| AGT-050 |  | PASS |  | tests/validation/test_invariance.py::test_vc_r06_mut_missing_adjustment_is_detected; tests/validation/test_r06_morning_effect.py::test_vc_r06_morning_effect |  | test |
| AGT-051 |  | PASS |  | tests/validation/test_invariance.py::test_vc_r10_frz_frozen_baseline |  | test |
| AGT-052 |  | PASS |  | tests/integration/api/test_residents.py::test_other_sort_orders |  | test |
| AGT-053 |  | PASS |  | tests/validation/test_r04_duplicate_records.py::test_vc_r04_duplicate_records; tests/validation/test_invariance.py::test_vc_r04_inv_identical_without_the_copies |  | inspection |
| AGT-054 |  | PASS |  | tests/validation/test_global_checks.py::test_vc_g06_scores (Exp_scores at 1e-6) |  | inspection |
| AGT-055 |  | PASS |  | analytics/config.py:74-80 FeatureSpec signs (loudness -1, pause_fraction +1, voiced_fraction -1, ...) |  | inspection |
| AGT-056 |  | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_second_run_changes_nothing; tests/validation/test_global_checks.py::test_vc_g12_determinism_and_rebuild |  | test |
| AGT-057 |  | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_runner_never_reads_the_answer_key |  | test |
| AGT-058 |  | PASS |  | tests/integration/pipeline/test_runner_persistence.py::test_reviews_and_snooze_survive_a_rerun; tests/validation/test_global_checks.py::test_vc_g10_alerts |  | inspection |
| AGT-059 |  | PASS |  | tests/integration/pipeline/test_nightly_run.py::test_one_run_per_local_night_across_dst |  | test |
| AGT-060 |  | PASS |  | tests/integration/test_schema_behaviour.py:36 app role UPDATE raw_sessions → privilege error |  | inspection |
| AGT-061 |  | PASS |  | .github/workflows/ci.yml:153-169 openapi-contract job diffs export-openapi output |  | inspection |
| AGT-062 |  | PASS |  | backend/api/permissions.py:12,14 roles admin/clinician/researcher; scopes ingest:write, pipeline:run |  | inspection |

