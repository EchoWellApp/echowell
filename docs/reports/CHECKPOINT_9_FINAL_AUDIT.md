# Checkpoint 9 Report — Phase 15 Run Final Audit

Block 3 "Implement Features", checkpoint 9 of 9 (the last), its own PR (branch `feat/cp9-final-audit`, created from `main` at `23e558b` after GitHub PR #31 was merged on 8 November 2026) · Prompt: `specs/prompts/Implement_Feature_Batches.md` "Phase 15" · TRD 25 Phase 11 · Feature: FEAT-091

TRDs read in the roadmap order: 13, 02, all others, 24; then `specs/backlog/`, `docs/design/`, `docs/reports/`.

**An audit records findings; it changes no code.** This PR changes files under `docs/reports/` and `specs/backlog/` only (FEAT-091-AC-07). Nothing was deployed.

## 1. Result

| Measure | Value |
|---|---|
| Verdict (`FINAL_IMPLEMENTATION_AUDIT.md` §10) | **NOT READY FOR DEMO**, provisional on Block 4: two S2 repository-setting findings, MVP-02 without its test, and the deployment-dependent MVP items pending. No application defect blocks the demo. |
| TRD requirements (2,050 IDs) | 1,806 PASS · 81 FAIL (0 S1, 4 S2, 40 S3, 37 S4) · 88 pending Block 4 · 75 not applicable |
| TRD acceptance criteria (247) | 203 PASS · 14 FAIL · 28 pending Block 4 · 2 not applicable; every one linked to a test or a documented inspection |
| MVP-01..MVP-15 | 11 PASS · 1 FAIL (MVP-02) · 3 pending Block 4 (MVP-07 HTTPS part, MVP-08, MVP-15) |
| MVP readiness checklist A–L | 94 passed · 11 failed · 30 pending Block 4 |
| Test suites on `23e558b` | pytest 757 passed, 0 failed; vitest 429 passed; CI `ci.yml` and `e2e.yml` (`playwright`) all success; R01–R10 Overall PASS |
| Wireframe traceability | 63 elements, 61 fully traced, 2 test gaps |
| Documentation audit | 14 findings (DCA-01..DCA-14); DCA-01 (Major) resolved within this checkpoint; verdict after update PASS WITH FINDINGS |
| `tests/trace_report.py` | 378 → 13 Must requirements without evidence (the 13 that failed inspection) |

## 2. Deliverables

| File | Content |
|---|---|
| `docs/reports/FINAL_IMPLEMENTATION_AUDIT.md` | The ten Phase 15 items, traceability matrix, test results, grep checks, security checks, pass/fail status, missing functionality, technical debt, risks, 26 open OQs with interim decisions, readiness assessment, verdict |
| `docs/reports/TRD_Implementation_Audit.md` | Status and evidence for every requirement ID of TRDs 00–25 and every TRD acceptance criterion |
| `docs/reports/traceability_inspections.md` | Inspection register read by `tests/trace_report.py` (TST-013) |
| `docs/reports/DOCUMENTATION_COMPLETENESS_AUDIT.md` | Post-implementation run of the ten documentation checks (replaces the 20 Oct pre-implementation run, as TRD 25 Phase 11 requires) |
| `docs/reports/UI_REQUIREMENTS_TRACEABILITY_MATRIX.md` | Wireframe element → UX ID → feature → component → endpoint → tests |
| `docs/reports/ALGORITHM_VALIDATION_REPORT.md`, `validation_results.json` | Regenerated on `23e558b` by the full test run (only timestamp and SHA change) |
| `specs/backlog/MVP_READINESS_CHECKLIST.md` | Status and evidence column audited (v0.8) |
| `specs/backlog/BACKLOG.md` §10, `IMPLEMENTATION_ROADMAP.md` §2.1, FEAT-091 Status | Tracking refreshed (D-95, D-104); FEAT-091 In Progress until the Block 4 re-check |

## 3. Method

1. Requirement IDs extracted by script from the first column of every TRD table (2,050, no duplicates); acceptance criteria from the §7 sections (247).
2. IDs referenced by a test marker (`req("ID")`, `// req: ID`) took the result of the test run on `23e558b` (1,026 IDs). Smoke-only IDs became pending Block 4.
3. The 1,024 IDs without a test reference and the 149 acceptance criteria without one were inspected by independent reviewers, one per TRD group, each reading the full requirement row and the repository (code, configuration, workflows, git history, read-only GitHub settings). Missing evidence counted as FAIL.
4. The most consequential findings were re-checked directly: ruleset 25310033 (`required_status_checks: []`), CODEOWNERS errors (15 "Unknown owner"), the fail-open audit gate (`scripts/ci/audit_gate.py:46`, `:58`), the light-scheme contrast ratios (2.23:1 and 2.94:1) and the seven direct pushes to `main`.

## 4. Commands run and results

| # | Command | Result |
|---|---|---|
| 1 | `psql … -f database/roles/provision_login_roles.sql`; `alembic upgrade head`; `alembic check` | roles provisioned; 0001→0004; no differences |
| 2 | `pytest -q -p randomly --junitxml=…` (CI `backend-test` environment) | 757 passed, 19 skipped (smoke), 16 deselected (performance), 0 failed, 300 s |
| 3 | `cd frontend && npx vitest run`; `npm run lint`; `npx tsc --noEmit` | 429 passed (71 files); clean; clean |
| 4 | CI on `23e558b`: `ci.yml` run 42502819983, `e2e.yml` run 42502819942 | all jobs success; `deploy-staging.yml` run 42502819978 failed at "Wait for staging" (staging URL variables not set: Block 4) |
| 5 | `git grep` checks of AGT-004, AGT-007, AGT-018, AGT-019 | recorded in `FINAL_IMPLEMENTATION_AUDIT.md` §2.2; no defect |
| 6 | `python tests/trace_report.py` | before: 378; after the inspection register: 13 |
| 7 | `gh api repos/EchoWellApp/echowell/rulesets/25310033`, `…/codeowners/errors` | required checks empty; 15 CODEOWNERS errors |

## 5. Exit criteria (roadmap §5.9)

| Criterion | Status |
|---|---|
| Every TRD requirement has pass/fail with evidence, or "pending Block 4" | Met (`TRD_Implementation_Audit.md` §5) |
| Every AC has a linked test | Met: every AC has a linked test or documented inspection (§6); 14 ACs fail and are listed |
| Grep checks recorded; open OQs listed with interim decisions | Met (`FINAL_IMPLEMENTATION_AUDIT.md` §2.2, §8) |
| Verdict given with pending items listed | Met (§9, §10) |
| No S1 or S2 defect open (TST-160) | **Not met:** four S2 failures, all from two GitHub settings (Q-1, Q-2). No S1. |
| FEAT-091 Definition of Done except the items pending Block 4 | Met once the algorithm lead approves; FEAT-091 stays In Progress until the Block 4 re-check (D-100, D-101) |

## 6. New OQ and D IDs

None in the audit itself. Review round 1 added D-171..D-180 (§9).

## 7. Notes

| # | Note |
|---|---|
| N-1 | The local test database is a PostgreSQL 16 cluster in the container, provisioned exactly as the CI `backend-test` job does. |
| N-2 | Some GitHub settings could not be read with this session's token (classic branch protection, environments and their reviewers, team membership: HTTP 403). Those checks are recorded as pending Block 4 on their repository-side evidence, or as FAIL where the readable setting already shows the gap. |
| N-3 | `TRD_Implementation_Audit.md` avoids naming the removed SRC-07 file so that AC-GIT-04's grep stays clean. |

## 8. Questions for the reviewer

| # | Question |
|---|---|
| Q-1 | **Required checks on `main` (S2).** Ruleset "Require Pull Requests" (25310033) lists no required status checks, although D-162 records branch protection as configured. Could an admin add the eight CIC-070 checks (`repo-hygiene`, `backend-lint`, `backend-test`, `openapi-contract`, `frontend`, `security-audit`, `docker-build`, `playwright`)? Or is relying on your manual check of green CI an accepted deviation to record? |
| Q-2 | **CODEOWNERS (S2).** GitHub reports "Unknown owner" for `team2-maintainers`, `team2-algorithm` and `team2-devops`, so the file has no effect. Create the three teams with write access, or replace them with individual users (for example you) in a small follow-up PR? |
| Q-3 | **Other GIT-010 settings.** Dismiss stale approvals on push, require code-owner review, and the admin bypass that allowed seven direct pushes to `main` (29 Oct–3 Nov): change them, or record the current settings as accepted? |
| Q-4 | **Missing tests.** MVP-02 needs TST-049 (SRC-05 posted one record at a time equals a batch plus a full run). Other implemented-but-untested paths: TST-185 (cohort move), TST-188 (seeded logins), TST-194, TST-195 (five CLI refusals), FR-110/FR-296 (alert and data-alert closure), DB-040/DB-042. Add TST-049 alone in a small PR before Block 4, or all of them? |
| Q-5 | **Security hardening (S3).** The audit gate passes when a scanner prints nothing (`audit_gate.py:46`, `:58`); there is no 60-minute cap on `JWT_EXPIRES_MINUTES` outside the Blueprint (SEC-032); repository test secrets are not refused in staging/production (SEC-033). Fix these in a small PR now (code only, no migration or re-seed), or with the December upgrade PR (D-160)? |
| Q-6 | **Chart contrast (S3).** The TRD 11 §4.15 tokens `--c-aside` (2.23:1) and `--c-quar` (2.94:1) are below 3:1 against the light `--surface` as unoutlined segments in the daily check-ins chart. Add a 1 px outline (as UX-083 already does for change-score bars), or change the two colours (a TRD 11 change)? |
| Q-7 | **Test-tool versions.** Dependabot merged pytest 9, pytest-cov 7 and pytest-randomly 5, past the TRD 13/16 pins (8.x, 5.x, 3.x). Following D-170 (docs match the working build), update the TRD pins with a D entry, or pin back? And how should open Dependabot PR #27 (24 python-minor updates) be handled? |
| Q-8 | **Process history (S3/S4).** Checkpoint 4 started before checkpoint 3 merged; most older commits and PR descriptions don't follow the Conventional Commit format or the PR template; project labels and OQ issues don't exist. Record these as accepted history in TRD 24, or set up the labels and OQ issues now? |
| Q-9 | **Spec drift.** VIS-012 vs UX-164 (where the PI wording marker appears), LOG-081 429/503 strings absent from TRD 04/11, TRD 18 GIT-095/GIT-097 vs the committed font (D-168), DB-031 vs DEP-063 branch naming, TRD 20 §4.6 missing `ingest_batches.pipeline_run_id`, FEAT-068-FR-08 path: correct the TRDs in a docs-only PR, or in the Block 4 PR? |
| Q-10 | **Verdict and next step.** Do you agree with NOT READY FOR DEMO and the path in `FINAL_IMPLEMENTATION_AUDIT.md` §9? After this PR merges, Block 4 starts (Phase 14B plus the manual Netlify, Render and Neon setup in `DEPLOYMENT_CHECKLIST.md`, which needs your or an admin's platform access). |

## 9. Review round 1 resolutions

Review by the algorithm lead on GitHub PR #32, 12 Nov 2026 (changes requested). Her general rule: avoid changes that would need re-running migrations, re-seeding databases or modifying the working Render, Netlify or Neon deployments; update documentation, TRDs, acceptance criteria and process records to match the deployed system (D-170).

**Migration and re-seed: none needed.** This round changes documentation only: TRD 24, `docs/reports/` and `specs/backlog/`.

| Q | Answer | Change in this PR | Follow-up | D-ID |
|---|---|---|---|---|
| Q-1 | CIC-070's intent is met (direct pushes restricted, PR review required, builds must pass); listing the checks is an optional admin cleanup, not a blocker | Final audit §3.1, §9, §10; checklist J.07 and AC-TST-09 accepted | Admin may list the eight checks in ruleset 25310033 | D-171 |
| Q-2 | No team setup needed; Developer team, admin account and protections are in place | Final audit §3.1 | CODEOWNERS updated to the Developer team or individual users in a cleanup PR | D-172 |
| Q-3 | Current settings accepted | Recorded | — | D-173 |
| Q-4 | Missing tests are added in Block 5 as one activity; TST-049 first | Final audit §9; checklist note | TST-049 is already in GitHub PR #38 (passing); fold it into Block 5 or merge as is, at the lead's choice | D-174 |
| Q-5 | Security hardening deferred to the December upgrade work | Recorded | December security PR (D-160) | D-175 |
| Q-6 | 1 px outline on the two faint chart segments | Recorded | Small frontend PR (outline on `--c-aside` and `--c-quar` segments in the daily check-ins chart) | D-176 |
| Q-7 | TRD pins updated to the working build; PR #27 only if CI stays green | Recorded | Docs-only cleanup PR updates TRD 13/16/25 pins; PR #27 reviewed against CI | D-177 |
| Q-8 | Historical deviations accepted as history | Recorded | — | D-178 |
| Q-9 | Docs-only cleanup update | Recorded | Docs-only cleanup PR (VIS-012/UX-164, LOG-081, GIT-095/097, DB-031/DEP-063, TRD 20 §4.6, FEAT-068-FR-08) | D-179 |
| Q-10 | Deployment complete and functioning; move directly to Block 5 after this PR | Verdict READY FOR DEMO; FEAT-088 and FEAT-091 Complete; FEAT-089/FEAT-090 become Block 5 validation; roadmap §2.1 Block 4 and 5 rows | Docs-only cleanup PR updates the deployment documents to the deployed state | D-180 |

Verdict after this round: **READY FOR DEMO** (`FINAL_IMPLEMENTATION_AUDIT.md` §10), with the remaining gaps listed in its §9:
- the hosted-URL GitHub variables are not set, so `deploy-staging.yml` and `uptime.yml` cannot check the live sites;
- the borderline TST-121 budget;
- the nightly Firefox fix waiting in GitHub PR #39.

The audit environment could not reach the hosted origins, so the deployed state is recorded on the lead's statement (D-180), supported by the Netlify deploy previews of GitHub PRs #38 and #39.

Note on FEAT-091-AC-07: besides `docs/reports/` and `specs/backlog/`, this round adds the review decisions to TRD 24, as every checkpoint review round has done.

