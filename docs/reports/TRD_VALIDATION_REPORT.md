# TRD Validation Report (Phase 1, round 8)

> Note (20 Oct 2026): findings R8-01..R8-06 of this report were fixed after it was written, in commits 1d7124f and 321eea0 (recorded in `docs/reports/TRD_VALIDATION_FIXES.md` and the TRD revision histories, v0.9); no round 9 was run.

| Field | Value |
|---|---|
| Scope | `specs/TRD/00`–`25`, checked against `specs/prompts/TRD_Generation_Prompt.md`, `specs/architecture/Deployment_Architecture.md`, `specs/UI-wireframe/*.dc.html` (5 files), `specs/business-requirements/*`, `specs/data-samples/*` |
| Checklist | `specs/prompts/TRD_Implementation_Audit_Checklist.md` Phase 1, and the definition of done in TRD 25 §Phase 1 |
| Round | 8. This report replaces round 7 (6 findings, R7-01..R7-06). It was written after the round-7 fixes in `docs/reports/TRD_VALIDATION_FIXES.md` were applied. |
| Branch | `trd-generation`. This run was read only: no file under `specs/` was changed and no git command was run. |
| Date | 2026-10-19 |

**How locations are written.** `TRD NN:line` means line `line` of `specs/TRD/NN_*.md`.

**Severity scale** (the same as rounds 1–7):

| Severity | Meaning |
|---|---|
| Critical | Built as written, the system would be wrong or unsafe. |
| Major | An implementer following the TRDs would very likely build something that fails its own required tests or the sources. |
| Minor | A real inconsistency or error that a careful implementer would still resolve without harm. |

**Numbering.** New findings in this round are R8-01, R8-02 and so on. Earlier findings keep their numbers (section 8).

**Scripts and scratch data** are in `/tmp/claude-0/-home-user-echowell/06d21bae-4975-509b-846a-5a1512c441c2/scratchpad/`:
- the round-1 to round-7 scripts: `xref.py`, `ids2.py`, `ep.py`, `cols.py`, `env.py`, `err.py`, `aud.py`, `paths.py`, `br3.py` and `wb*.py`;
- for this round: `t_r8.sh` (`t_r7.sh` pointed at `r8/sql/`), `r8/sql/` (the 33 TRD 20 SQL fences), `r8/paths_r8.txt`, `r8/tbl.py` (Markdown table cell-count check), `r8/vt/` and `r8/vt2/` (Vitest 2.1.9 command check; `marked` 12 render check).

---

## 1. Summary

**Verdict: PASS WITH FINDINGS.** No Critical or Major finding remains. Six Minor findings are new in this round.

All six round-7 findings are resolved:
- **R7-01 (Major) is resolved.** `playwright.isolated.config.ts` now has its own `globalSetup`, `frontend/tests/e2e/isolated-setup.ts`. It logs in once per role against the `echowell_demo` backend, never resets or seeds, and writes `frontend/tests/e2e/.auth/isolated-<role>.json`. D-74(a), D-73, TST-004, the TRD 13 preamble, the Table 4.10-A note, §8, CIC-030 and the `e2e.yml` isolated step all say the same. The tokens now carry a `sub` that exists in `echowell_demo`, so API-012 and SEC-034 accept them.
- **R7-02 to R7-06 (Minor) are resolved.** The three `test:e2e:*` scripts and `grepInvert: /@isolated/` are used everywhere, and no bare `test:e2e` or plain `npx playwright test` remains. Exit code 1 is the single settings-validation code, with exit 2 reserved for CLI refusals. DB-021 names `backend/core/db.py`. TST-006 holds the single marker list, and TRD 16 §6 holds the single dev-requirements list. The TRD 18 rulesets note refers to CIC-070.

New findings (all Minor):
- **R8-01:** 12 requirement-table rows in TRD 04, 05, 07, 08, 11 and 17 still contain unescaped `|` inside code spans, so they render broken. One is BSC-015, whose quarantine thresholds disappear from the rendered table.
- **R8-02:** the frontend coverage command fails as specified. TRD 04 `test` = `vitest run --coverage`, and ci.yml runs `npm run test -- --coverage`. This was executed with Vitest 2.1.9 and exits 1 with "Expected a single value for option --coverage". Also, no coverage provider (`@vitest/coverage-v8`) is in the TRD 04 §4.1 pins, and without it `vitest run --coverage` exits 1 ("MISSING DEPENDENCY").
- **R8-03:** Prettier enforcement disagrees between TRDs. FE-202, NFR-081 and GIT-042 require it in CI, but CIC-017 and the ci.yml `frontend` job never run it. GIT-042 also puts `prettier --check` inside `npm run lint`, where TRD 04 has a separate `format:check`.
- **R8-04:** component tests have two different locations. TRD 04 puts them next to the component (`components/<Name>/<Name>.test.tsx`), while TRD 13 §4.2 and TST-010 use `frontend/tests/components/`.
- **R8-05:** after the round-7 change, nothing says how `playwright.isolated.config.ts` selects only the `@isolated` scenarios, or fixes their order. The TRD 04 E2E row also still says "one form login per role, reused per project", which contradicts D-74.
- **R8-06:** the CLI command `resolve-data-alert` has no argument syntax, and FR-297 (a Must with verification "T") has no test.

**R8-02 is Minor, not Major.** Copied verbatim, the required `frontend` check fails on every PR. Under round 7's R7-05 precedent that is Minor: under `--strict-markers` either marker list as written made `backend-test` fail at collection, and R7-05 was rated Minor. Both failures are immediate, self-describing and fixed with a one-token change, with no design decision needed.

| Severity | Count |
|---|---|
| Critical | 0 |
| Major | 0 |
| Minor | 6 |
| **Total new (round 8)** | **6** |

Prior findings:

| Set | Resolved | Partially resolved | Not resolved |
|---|---|---|---|
| R7-01..R7-06 (6) | 6 | 0 | 0 |

Phase 1 checks:

| # | Phase 1 check | Result | Key evidence |
|---|---|---|---|
| 1 | Database requirements support all APIs | **PASS** | The 33 TRD 20 `sql` fences are byte-identical to round 7. They were re-executed on PostgreSQL 16 with the same results: 24 tables, 17 triggers, 15 enums, 46 config rows, `timezone` UTC, and every permission and trigger check passes. All E-01..E-32 are backed. DB-021 now names `backend/core/db.py`. |
| 2 | APIs support all frontend requirements | **PASS** | All 32 endpoints are in TRD 19, and every `/api/v1` path used in the TRDs resolves. No frontend item lacks an API source. |
| 3 | Analytics requirements support all business requirements | **PASS** | The workbook and SRC-05 were re-verified with `python3 -I` and pandas (section 6.3). Every figure matches. |
| 4 | Testing requirements validate all critical functionality | **PASS** | The `@isolated` run now authenticates (R7-01 resolved). Minor: R8-02 (Vitest coverage command), R8-04 (component test location), R8-05 (isolated test selection and the TRD 04 wording), R8-06 (FR-297 untested). |
| 5 | Deployment requirements support the architecture | **PASS** | The interim stack (Netlify, Railway, Neon, with Railway PostgreSQL as the alternative) and the AWS target match `Deployment_Architecture.md`. The exit-code rule is now consistent (R7-03), and the required checks are named consistently (R7-06). Minor: R8-03 (Prettier missing from the CI `frontend` job). |

TRD 25 §Phase 1 definition of done:

| Criterion | Result | Evidence |
|---|---|---|
| Every BR-01..BR-18 maps to at least one TRD requirement and test | **Met** | Section 2.1. Each BR is cited by 25–271 requirement rows across 10–24 TRDs. |
| Every OQ/ASM/RSK/DSC/D ID used exists in TRD 24 | **Met** | ASM-01..08, DSC-01..14, OQ-01..26, RSK-01..15 and D-01..D-74 are each defined exactly once, with no gaps. `OQ-27` and `RSK-16` appear only in the "next free" rule (TRD 24:265). |
| Each of the five checks has a pass/fail line | **Met** | The table above and section 6 |
| No TRD file modified | **Met** | This run was read only |
| `grep -rnE "T[B]D\|T[O]DO\|l[o]rem" specs/TRD` returns nothing | **Met in substance** | The only hit is GIT-053 (TRD 18:219), the rule that forbids these words. The same hit was accepted in rounds 1–7. |

---

## 2. Requirements Traceability Matrix

### 2.1 Business requirements → TRD requirements → tests

The counts come from `br3.py`. A table row counts when its first cell is a requirement ID and the row cites the BR, directly or within a range. The restatement tables (BR, SRC, OQ, ASM, RSK, DSC) are excluded. Every count is unchanged from round 7, because round 7 added no requirement IDs.

| BR | Summary (TRD 00) | Rows / TRDs | Key FRs (TRD 02) | Tests / MVP criteria | Gap (round 8) |
|---|---|---|---|---|---|
| BR-01 | Ingest feature records, never audio | 80 / 20 | FR-001–FR-005, FR-020–FR-028 | TST-030, TST-043, TST-045, TST-046, TST-133, TDV-031, TDV-090, MVP-02 | — |
| BR-02 | Keep raw records unaltered | 101 / 17 | FR-005–FR-007, FR-010, FR-028 | TST-037, TST-041, TST-043, TDV-002, TDV-050, TDV-054, MVP-02, MVP-12 | — |
| BR-03 | Drop duplicates, keep first arrival | 40 / 13 | FR-008, FR-011, FR-029–FR-031 | TST-020, TST-044, TST-046, TDV-054, MVP-01, MVP-03 | — |
| BR-04 | Set aside poor-quality sessions | 28 / 13 | FR-024, FR-040–FR-044 | TST-020, TDV-053, MVP-01, MVP-03 | — |
| BR-05 | Quarantine wrong-speaker sessions | 27 / 10 | FR-060–FR-065 | TST-020, TDV-055, MVP-01, MVP-03 | BSC-015 and BSC-016 render broken (R8-01) |
| BR-06 | Log missing days honestly | 69 / 15 | FR-120–FR-125, FR-135 | TST-020, TDV-052, TDV-053, TDV-064, TDV-068, MVP-01 | — |
| BR-07 | Remove morning offset | 26 / 11 | FR-070–FR-074 | TST-020, TDV-056, MVP-01 | — |
| BR-08 | Epochs; restart baseline | 34 / 12 | FR-050–FR-053 | TST-020, TDV-057, MVP-01 | — |
| BR-09 | Robust personal baseline, frozen | 55 / 15 | FR-080–FR-086 | TST-020, TST-184, TDV-051, TDV-058, TDV-060, MVP-01 | — |
| BR-10 | Signed z and composite | 25 / 11 | FR-090–FR-095 | TST-020, TDV-051, MVP-01 | — |
| BR-11 | CUSUM persistent-deviation flag | 61 / 14 | FR-100–FR-110, FR-261–FR-265 | TST-020, TST-065, FE-205, TDV-059, TDV-060, TDV-067, MVP-01, MVP-13 | — |
| BR-12 | Residents overview | 92 / 17 | FR-130–FR-140, FR-150–FR-156 | TST-033, TST-090, TST-110, TST-181, TST-187, TDV-062, TDV-066, MVP-04 | — |
| BR-13 | Resident detail page | 113 / 15 | FR-160–FR-173, FR-260–FR-280, FR-297 | TST-090, TST-093, TST-110, TST-181, TST-187, TDV-066, MVP-05, MVP-13 | FR-297 has no test or CLI syntax (R8-06) |
| BR-14 | New-admission arm (Should) | 32 / 10 | FR-200–FR-207 | TST-090, TST-185, TST-186, MVP-06 | — |
| BR-15 | Reproduce workbook R01–R10 | 166 / 22 | FR-240–FR-245, FR-310–FR-323 | 41 TST/TDV/MVP rows, TST-084 (`nightly-validation`) | — |
| BR-16 | Data protection, roles, audit | 271 / 24 | FR-210–FR-221, FR-250–FR-254 | TST-007, TST-032, TST-041, TST-053, TST-130, TST-131, TST-188, TDV-006, TDV-007, MVP-07 | — |
| BR-17 | Monorepo deploy on Netlify/Railway/Neon/GHA | 74 / 15 | FR-253, FR-254 | TST-001, TST-150, TST-170, MVP-08 | R8-02, R8-03 (CI `frontend` job) |
| BR-18 | Detection not diagnosis, no LLM/ML | 47 / 15 | FR-164, FR-277, FR-278, FR-298 | TST-096, TST-097, TST-170, MVP-09 | — |

### 2.2 Frontend requirements (TRD_Generation_Prompt) → UX / FE IDs

Every item in the prompt's "Frontend Requirements" list was traced again. TRD 11 and TRD 19 have not changed since round 2, and TRD 04 changed in round 7 only in the §4.15 scripts table.

| Prompt frontend item | UX IDs | FE components (TRD 04 §4.8) | Tests | Round-8 note |
|---|---|---|---|---|
| Three primary views plus Alerts and Analytics | D-23; TRD 11 §4.3, §4.5, §4.7, §4.17, §4.18 | Residents page, Resident detail page, AdmissionsTable, AlertsPage, AnalyticsPage | E2E-03..E2E-21, TST-110 | — |
| All enrolled residents; sort by alarm, resident ID, last check-in | UX-020–UX-033, UX-261 | ResidentsTable, SortSelect | E2E-04, E2E-05, E2E-06 | FE-082 renders broken (R8-01) |
| Statuses Alarm On / No Alarm / Baseline Still Forming | §4.3.4, UX-036 | StatusBadge | E2E-04 | — |
| 30-day used, set aside, quarantined, missed; no backfill | UX-039, UX-047, UX-048 | ResidentsTable, SummaryTiles | E2E-03, E2E-04, E2E-15 | — |
| Device panel | UX-050–UX-058, UX-263 | DevicePanel, DeviceCell | E2E-07 | — |
| CUSUM tally, alarm line 5.0, baseline period | UX-080–UX-092 | CusumChart, CusumTable | TST-093, E2E-08 | UX-091 renders broken (R8-01) |
| 7 scored measurements; 12 others stored, not scored | UX-100–UX-108 | FeatureCard ×7, OtherMeasurementsCard | E2E-08, TST-090 | — |
| Baseline status, progress, freeze | UX-060–UX-066 | ResidentHeader, WhatThisMeans | E2E-08, E2E-10, E2E-11 | — |
| Check-in log | UX-140–UX-149 | CheckinLog | E2E-10..E2E-12, E2E-15 | — |
| Staff notes | UX-120–UX-135 | StaffReviewForm, NotesList, ReviewDialog | E2E-09 = FE-187 (`@mutating` step 2) | — |
| New admissions, "future/experimental" | UX-181–UX-195 | AdmissionsTable, FacilityRangeChart, ExperimentalBanner | E2E-13, TST-185, TST-186 | — |
| Alert review (SRC-18) | UX-300–UX-331 | AlertQueue, AlertCard, AlertReviewForm | E2E-17, E2E-18, E2E-19, TST-065, FE-193, FE-205 | — |
| Analytics (SRC-19) | UX-351–UX-384 | KpiTiles, LossFunnel, AlarmTimingTable, … | E2E-20, E2E-21, TDV-074 | — |
| Loading, empty and error states; accessibility; responsive | UX state rows, FE-145, NFR-060, NFR-068 | SectionState | TST-090, TST-110, E2E-16, FE-191 | — |

Result: every prompt item maps to UX IDs, FE IDs and at least one test, and every frontend item has an API source.

### 2.3 Wireframes → UX sections

All key strings were found again with grep, in both the wireframe and TRD 11.

| Wireframe | UX section | Key strings checked |
|---|---|---|
| `Main.dc.html` | TRD 11 §4.3, §4.4, §4.13 | "shared by R02", "silent all day" |
| `Resident.dc.html` | TRD 11 §4.5 | "Baseline complete", "alarm line 5.0" |
| `Admission.dc.html` | TRD 11 §4.7 | "Not in pipeline test v0.1" |
| `Alerts.dc.html` | TRD 11 §4.17 | "open 9 days", "26.8", "13.4", "Alerts (2)", "Remind me in" |
| `Analytics.dc.html` | TRD 11 §4.18 | "281", "267" |

### 2.4 Items with no test or only a weak test

| Item | Status |
|---|---|
| FR-297: an admin resolves a `review_flagged_data_problem` data alert with the CLI | Must, verification T. No TST or TDV covers it, and the command has no defined arguments (R8-06). |
| Selection of the `@isolated` scenarios by `playwright.isolated.config.ts` | Not specified (R8-05). The CI step passes no `--grep`. |

---

## 3. Missing Requirements

| ID | Severity | Where it is needed | What is missing |
|---|---|---|---|
| R8-02 | Minor | TRD 04 §4.1 (04:58–74), FE-002 (04:83), TRD 13 §6 tools line (13:535) | A pinned Vitest coverage provider (`@vitest/coverage-v8` 2.x, matching Vitest 2.x). `npm run test` = `vitest run --coverage` (04:631), FE-180 and CIC-017 gate coverage, and without the provider Vitest exits 1 with "MISSING DEPENDENCY Cannot find dependency '@vitest/coverage-v8'" (executed, CI=true). |
| R8-05 | Minor | TST-004 (13:87), D-73 (24:236), TRD 04 `test:e2e:isolated` (04:634), TRD 04 §4.2 tree (04:134) | How `playwright.isolated.config.ts` restricts its run to the `@isolated` scenarios (for example `grep: /@isolated/`, or a `testMatch` naming one isolated spec file), and how the required order "E2E-15, TST-187, E2E-19" (16:381, E2E-19 "after E2E-15 and TST-187", 13:385) is guaranteed, for example one serial spec file. |
| R8-06 | Minor | TRD 15 §4.8 CLI table (15:394), FR-297 (02:353), TRD 13 | The argument syntax of `resolve-data-alert`, which is the only command in the §4.8 table without one: how the alert is chosen (id, or resident code and kind), the role and connection it runs as, and the refusal for kinds other than `review_flagged_data_problem`. Also a test for FR-297, which is a Must verified by "T". The audit row `data_alert.resolved` (12:292) exists. |

---

## 4. Contradictions

### 4.1 Critical and Major

None.

### 4.2 Minor

| ID | Location (A vs B) | Description and evidence | Recommendation |
|---|---|---|---|
| R8-01 | GFM table syntax versus 12 table rows with an unescaped `\|` inside a code span: FE-082 (04:411); API-065 (05:222); API-129 (05:247); the TRD 07 §4.4 DTO rows `ResidentInfo`, `DeviceAssignment`, `EpochSummary`, `RunWarning` and `DataAlert` (07:194, 195, 198, 199, 200); BSC-015 (08:135); BSC-016 (08:136); UX-091 (11:281); LOG-023 (17:114). | `r8/tbl.py` counts the cells of every table row outside code fences, with `\|` treated as escaped. These 12 rows have 6–15 cells against a header of 5 (2 for TRD 07). In GFM a pipe splits the cell even inside a code span. This was confirmed by rendering BSC-015 with `marked` 12: the Requirement cell ends at "if and only if \`", "z_F0" lands in Priority, and the thresholds `≥ 4.0`, `\|z\| ≥ 3.0` and "≥ 2" are lost or shifted. BSC-016's "exact" quarantine reason string, the LOG-023 redaction key list and API-065's request schema are mangled in the same way. The raw Markdown is still correct, and the round-7 fix escaped only the cells it touched (TRD 04 scripts, D-73, SEC-020 and TRD 21). | Escape every `\|` inside these cells as `\|`, as was done for SEC-020 and D-73. Add the cell-count check to `repo-hygiene` or the docs lint. |
| R8-02 | TRD 04 §4.15 `test` = `vitest run --coverage` (04:631) versus the TRD 16 `frontend` job table (16:112) and ci.yml step `npm run test -- --coverage` (16:258). | npm appends the extra argument, so the job runs `vitest run --coverage --coverage`. Executed with Vitest 2.1.9 (the latest 2.x; TRD 04 pins 2.x): `Error: Expected a single value for option "--coverage", received [true, true]`, exit 1. The `frontend` job is a required check (CIC-070), so it fails on every PR when both TRDs are followed verbatim. Together with the missing coverage provider (section 3), it is a one-line fix that the error message names. It is rated Minor for consistency with R7-05, a required-job failure from conflicting lists that is visible at once. CIC-017 (16:315) already says `npm run test` with no extra flag. | Make the ci.yml step and the job table `npm run test` (the script already enables coverage). Add `@vitest/coverage-v8` 2.x to TRD 04 §4.1 and the TRD 13 §6 tools line. |
| R8-03 | FE-202 (04:642): CI runs "`npm ci`, `npm run lint`, `npm run typecheck`, `npm run format:check`, `npm run test`, `npm run build`". NFR-081 (03:133): TypeScript shall pass Prettier, verified "Test (CI)". GIT-042 (18:207): "Prettier shall report no differences (`prettier --check .` in `npm run lint`)". Versus CIC-017 (16:315), the `frontend` job table (16:112) and ci.yml (16:246–260), which run lint, typecheck, test and build only, and the TRD 16 §6 script list (16:542), which has no `format` or `format:check`. Also TRD 04 `lint` = `next lint --max-warnings 0` (04:628) with a separate `format:check` (04:630), so GIT-042's "in `npm run lint`" is false. | Built from TRD 16, CI never checks Prettier, so FE-202, NFR-081 and GIT-042 are not enforced. Built from GIT-042, `lint` would run Prettier, contradicting the TRD 04 script table. In a related point, TRD 18:198 requires `eslint-config-prettier`, but FE-200 (04:640) and the TRD 04 §4.1 pins do not include it. | Add `npm run format:check` to CIC-017, the job table and ci.yml (after `typecheck`, as FE-202 orders it), and add `format` and `format:check` to TRD 16 §6. Change GIT-042 to "`npm run format:check`". Add `eslint-config-prettier` to FE-200 and §4.1, or remove it from TRD 18:198. |
| R8-04 | TRD 04 §4.2 (04:113: "One folder per component: Component.tsx, Component.module.css, Component.test.tsx"), the §4.8 preamble (04:422: "co-located `<Name>.test.tsx`") and the §4.14 table (04:592: `components/**/<Name>.test.tsx`). Versus TRD 13 §4.2 (13:125–126: `frontend/tests/components/` "one test file per component" and `frontend/tests/pages/`) and TST-010 (13:132, Must): "The test tree shall follow the layout in §4.2". | The same component tests are placed in two locations. An implementer satisfying TST-010 (verified by inspection) violates the TRD 04 layout that FE-010 requires (04:139), and the reverse is also true. TRD 04 has no `tests/pages/` folder. The choice also changes FE-180's coverage measurement, which covers `components/` and so would include co-located test files unless they are excluded. | Choose one location. TRD 04's co-location is used in three places, so align TRD 13 §4.2 to it (and say where page tests live), or the reverse. State the coverage exclusion for `*.test.tsx`. |
| R8-05 | D-74(a) (24:237): `globalSetup` logs in "through `POST /api/v1/auth/login`", and only E2E-01, E2E-02 and FE-188 "perform real logins". CIC-030 says "only the login scenarios perform form logins". The `globalSetup` runs once per Playwright invocation, which is per browser project and group (D-73). Versus the TRD 04 §4.14 E2E row (04:593): "one form login per role, reused per project (D-74)". | Two errors in the TRD 04 row: the per-role login is an API login, not a form login, and it is repeated per invocation (`readonly` and `mutating` each run `globalSetup`), not per project. The row also does not mention `isolated-setup.ts`, and the TRD 04 tree (04:134) lists `playwright.config.ts` but not `playwright.isolated.config.ts`. Harmless in effect, because the token ends up in `sessionStorage` either way, but it is the one TRD 04 statement of D-74 and it disagrees with it. The selection and order gap is listed under section 3. | Change the row to "one API login per role in `globalSetup` per invocation (`isolated-setup.ts` for the `@isolated` run), reused through the role fixture (D-74)". Add `playwright.isolated.config.ts` to the tree. Specify `grep: /@isolated/` and a single serial spec file for the isolated config. |
| R8-06 | FR-297 (02:353): a `review_flagged_data_problem` alert stays open "until an admin resolves it with a command-line action" (Must, T). TRD 23:427 and the TRD 23 state diagram (23:617) name `backend.cli resolve-data-alert`. Versus the TRD 15 §4.8 row (15:394): "`resolve-data-alert` \| Resolves a `review_flagged_data_problem` data alert", with no arguments, while every other command in the table gives its syntax. | An implementer has to invent how the alert is identified and which connection or role is used (the app role can update `data_alerts`, PGS-021). The audit `details` `{"kind", "operator"}` (12:292) do not include the alert id, although the row target is "data alert id". No TST or TDV verifies FR-297. | Define `resolve-data-alert --id <uuid> --reason "<text>"` (or `--resident <code>`), its refusal (exit 2) for other kinds or for an alert already resolved, and the audit details. Add a TRD 13 integration test for FR-297 and the pipeline's non-resolution of this kind (CUS-040). |

---

## 5. Cross-Reference Validation

| Check | Method | Result | Findings |
|---|---|---|---|
| Duplicate requirement IDs | `xref.py` over the first cell of every table row and over list-item AC IDs | 2,006 requirement IDs are defined and 2,006 are referenced, unchanged from round 7 (no new IDs). No duplicates, and no ID in the wrong file. E-01..E-32 appear twice in TRD 19 by design (detail and summary). | — |
| Dangling requirement IDs | `xref.py`, `ids2.py` | None. The only script hits are the known artefacts: E2E-01..E2E-21 (defined as the first cell of Table 4.10-A with the name after the ID) and AC-DB-02a. | — |
| OQ / ASM / RSK / DSC / D vs TRD 24 | Per-prefix script: used versus defined, duplicate definitions and gaps | ASM-01..08, DSC-01..14, OQ-01..26, RSK-01..15 and D-01..D-74 are each defined once, with no gaps. `OQ-27` and `RSK-16` appear only in the "next free" rule (24:265). | — |
| D-column bookkeeping | Script: each D-xx "Implemented in" column compared with the TRDs that cite the decision | D-68..D-74 behave as in round 7: D-73 is cited by 04, 05, 13, 15, 16 and 25 and its column adds 03, and D-74 is cited by 04, 05, 12, 13, 16 and 21 and its column adds 18. The column is not exhaustive for older decisions (31 of 74 rows omit a citing TRD, mostly TRD 25), and it is labelled "Implemented in", not "cited by". This is consistent with rounds 1–7 and not a finding. | — |
| Revision rows | Script | The nine TRDs changed in round 7 (04, 06, 12, 13, 16, 18, 21, 24, 25) read Version 0.8 in the header and each has one "0.8 \| 19 Oct 2026 \| Phase 1 round-7 fixes (…)" row naming the right R7 IDs. No other TRD reads 0.8. | — |
| Endpoints vs TRD 19 | `ep.py` | All match. The only non-matches are the known ones: `/alerts/{id}/acknowledge` and `/audio` (in "shall not exist" text), `/openapi.json`, `/docs`, `PATCH /users` (meaning `/users/{id}`), the `/ingest]` Mermaid label and `/alerts/{R09 alert id}`. | — |
| Tables/columns vs TRD 20 DDL | `cols.py`: 24 `CREATE TABLE` blocks compared with every `table.column` token | All match. The only non-matches are `alerts.spec` (a file name) and `config_parameters.facility_tz` (config-key notation). | — |
| DDL executes | `t_r8.sh` on a PostgreSQL 16 scratch cluster. The 33 fences re-extracted to `r8/sql/` are byte-identical to round 7. | (0) Without extensions, 0001 as the migrator fails with the 0001 message (exit 3). (0b) CREATE EXTENSION as the migrator is denied. (1) Provisioning as superuser: exit 0. (2) 0001 and 0002 as `echowell_migrator_login` with `SET ROLE`: 24 tables, 17 triggers, 15 enums, 46 config rows, all owned by `echowell_migrator`, `timezone` UTC. (2b) The provisioning fence as the migrator is refused ("must be owner of database"). (3) Downgrade base: 0 tables, extensions kept. (3b) DROP EXTENSION as the migrator is refused. (4) Re-migrate: same counts, UTC; `seed.reset` is accepted and `Auth.Login` is rejected by `audit_logs_action_ck`. (5) The app login is denied `evaluation_ground_truth`, `SET ROLE echowell_readonly`, `DELETE alerts`, `UPDATE raw_sessions` and `DELETE audit_logs`; `gen_random_uuid()` works; the readonly login is denied `password_hash`; an owner DELETE on `audit_logs` raises EW001 without the purge setting and succeeds with it. (6) Second database (the `echowell_demo` pattern): provisioning is idempotent and migration succeeds. | — |
| Env vars vs TRD 21 | `env.py` (45 defined names) | All defined. The non-matches are the known ones (error codes, report names, workflow-local and GitHub variables, `RAILWAY_GIT_COMMIT_SHA`, `NIGHTLY_SCHEDULER_ENABLED`). | — |
| Exit codes | grep of "exit code", "exits", "non-zero" in all TRDs | ENV-002 (21:50) is the single rule: exit 1 for every settings-validation failure, and exit 2 for command-specific CLI refusals checked first. ENV-041, ENV-054, the SEED_* row (21:85), LOG-072 and AC-ENV-01..03 use 1. DEP-070, DB-024, DB-057, DB-059, AC-DB-08, AC-DEP-02, TRD 20:83 and `set-config` use 2. "Non-zero" remains only where no specific code is needed (DEP-048, DEP-065, API-058, API-062, TDV-103, AC-AGT-05). | — |
| Error codes vs TRD 05 | `err.py` (36 codes) | All are in the catalogue | — |
| Audit actions vs TRD 12 §4.12 | `aud.py` (24 actions) | All are in the vocabulary | — |
| CLI command names | `backend.cli <cmd>` occurrences compared with the TRD 15 §4.8 table | All 14 commands used are in the table. `resolve-data-alert` has no syntax. | R8-06 |
| CI workflows / jobs / scripts / config files | `*.yml` names; job IDs compared with CIC-070; `npm run` targets compared with the TRD 04 §4.15 scripts | The five CIC-002 workflows are used consistently. `ci.yml` has 7 jobs; `e2e.yml` has `playwright`, `performance`, `lighthouse` and `nightly-validation`. CIC-070 and TRD 18:414 name the same eight required checks. `test:e2e:readonly`, `test:e2e:mutating` and `test:e2e:isolated` are identical in TRD 04, 13, 16, 24 and 25. `global-setup.ts`, `isolated-setup.ts`, `mutating.spec.ts`, `.auth/<role>.json` and `.auth/isolated-<role>.json` are named identically in TRD 13, 16 and 24, and `.auth/` is ignored by TRD 18. Problems: `format:check` is not run by CI, and the coverage flag is doubled. | R8-02, R8-03 |
| Commands executed | `r8/vt/`: Vitest 2.1.9 and @vitest/coverage-v8 2.1.9 on Node 22; `r8/vt2/`: Vitest without the provider | `npm run test` (= `vitest run --coverage`) exits 0. `npm run test -- --coverage` exits 1 ("Expected a single value for option --coverage"). Without the provider, `vitest run --coverage` exits 1 ("MISSING DEPENDENCY"). | R8-02 |
| pytest markers and dev dependencies | Grep of every "marker" and `-m` use; TST-006, TRD 16 §6 and TRD 13 §6 | All markers used (`smoke`, `authenticated`, `performance`, `budget`, `req`, the level markers) are in TST-006. Every tool used by a job (ruff, mypy, `lint-imports`, pytest-randomly, time-machine, testcontainers, openapi-core, Hypothesis, Bandit, pip-audit) is in TRD 16 §6, and the TRD 13 §6 line repeats it. Observation, not a finding: the TRD 25 Phase 3 outputs (25:186) allow "`pytest.ini` or `pyproject.toml`", while TST-006 and TRD 16 §6 require `pyproject.toml`. | — |
| File paths | `paths.py` (227 paths); `r8/paths_r8.txt` compared with round 7 | New since round 7: `frontend/tests/e2e/isolated-setup.ts` and `.auth/isolated-` (13, 16, 24). `backend/db.py` is gone, and `backend/core/db.py` is used by 05 and 06. No directory conflict remains except the by-design ones. Separately, component-test locations conflict between TRD 04 and TRD 13. | R8-04 |
| Session and token chain (D-74) | Read SEC-030..SEC-038, FE-050..FE-056, API-012, the `users` DDL and the `e2e.yml` isolated step | Main run: tokens from the reset main database. Isolated run: `isolated-setup.ts` logs in against `echowell_demo` after `seed --master-only` (16:378), so `sub` exists there, and the SEED_* passwords are the same per-job values. RATE_LIMIT_LOGIN=60/minute applies to both. | — |
| Markdown tables | `r8/tbl.py`: cell count per row compared with the header, outside code fences, with `\|` treated as escaped; render check with `marked` 12 | 12 rows broken (R8-01). No `\|` occurs outside a table or inside a fence. | R8-01 |
| Code fences / placeholders | Script / grep | Fence counts are even in all 26 files. The placeholder grep hits only GIT-053. | — |
| Golden fixtures | pandas with `python3 -I` | Section 6.3 | — |

---

## 6. The five checks in detail

### 6.1 Database requirements support all APIs: **PASS**

- Every endpoint E-01..E-32 reads and writes only tables and columns of the TRD 20 DDL. This was re-executed (section 5).
- The `echowell_app` grants cover every API write, and the denials of PGS-021 and PGS-040 hold.
- `alert_reviews` allows several reviews per alert (CUS-017), so the D-73 order (E2E-18, then E2E-09 on R09) is valid.
- `snoozed_until` is written from the application clock (DME-022, API-132, CUS-039).
- DB-021 and the TRD 05 module tree now agree on `backend/core/db.py::advisory_key` (R7-04 resolved).

### 6.2 APIs support all frontend requirements: **PASS**

- All 32 endpoints are in the TRD 19 summary and YAML, and every TRD 04 client function resolves to an endpoint.
- `POST /api/v1/ingest` accepts an admin JWT (API-049), which E2E-19 relies on.
- FE-205 relies only on `snoozed_until`.
- No frontend item lacks an API source. R8-01 affects how FE-082 and API-065 render, not their content.

### 6.3 Analytics requirements support all business requirements: **PASS**

SRC-03 and SRC-05 were read again with `python3 -I` and pandas (`wb.py`..`wb4.py`). Every value matches the TRDs.

| Quantity | Value |
|---|---|
| Annotated_sessions `expected_status` (302 rows) | usable 267, missing_resident 17, set_aside 12, missing_device_gap 2, duplicate 2, quarantined 2 (missed tile 19; funnel 300 → 281 → 269 → 267) |
| Exp_status_counts per resident | R02 24 usable, 5 missing, 1 device gap; R03 22 usable, 7 set aside, 1 device gap; R04 2 duplicates; R05 2 quarantined; R08 13 usable, 12 missing, 5 set aside; others 30 usable |
| Exp_baselines | 180 rows. The floor is applied only to `number_of_pauses` (8 of 9 residents; R09 spread 0.7413, not floored). |
| Exp_scores | 98 rows: R01 14, R02 8, R03 6, R04 14, R05 12, R06 14, R07 2, R09 14, R10 14 |
| Alarm states | off 81, on 15, RINGS (first crossing) 2. Final tallies are R09 26.830256 and R10 13.418183, as in Alerts.dc.html, E2E-17, FE-193 and CIC-032. |
| Parameters | baseline length 16; spread MAD × 1.4826; floor 0.5 (pauses) and 0.1 (composite); CUSUM k 0.5; alarm line 5.0; speaker screen \|F0 z\| ≥ 4.0 with ≥ 2 features \|z\| ≥ 3.0 |

No findings. BSC-015, which states the speaker-screen thresholds, is correct in the raw Markdown but renders broken (R8-01).

### 6.4 Testing requirements validate all critical functionality: **PASS**

- Every BR has TST, TDV or MVP coverage.
- The `@isolated` run now has valid sessions (R7-01 resolved).
- The E2E invocation scheme is single-sourced: three scripts, `grepInvert`, `--workers=1` for the `@mutating` group, and the isolated config (R7-02 resolved).
- The marker and dev-tool lists are single and complete (R7-05 resolved).
- Snooze is covered at three levels (E2E-19, TST-065 and FE-205). `backend-test` keeps a fixed order, and `nightly-validation` runs in random order.
- Minor:
  - R8-02: the `frontend` job's coverage invocation fails as written.
  - R8-04: the component-test location differs between TRD 04 and TRD 13.
  - R8-05: test selection and order for the isolated config, and the TRD 04 E2E-row wording.
  - R8-06: FR-297 is untested.

### 6.5 Deployment requirements support the architecture: **PASS**

- The architecture follows `Deployment_Architecture.md`: a monorepo; Next.js on Netlify; FastAPI on Railway; Neon, with Railway PostgreSQL as the alternative; GitHub Actions; and the AWS target (Amplify, App Runner, RDS).
- ENV-002 now gives one exit-code rule, and ENV-041, ENV-054 and the SEED_* row follow it (R7-03 resolved).
- Branch protection has one list (CIC-070, referenced by TRD 18 GIT-010, the TRD 18:95 row and TRD 18:414; R7-06 resolved).
- The D-71 staging exception, the D-72 provisioning step and the placeholder-credential rules are unchanged and consistent.
- Minor: R8-03 (Prettier is required by FE-202, NFR-081 and GIT-042 but not run by the CI `frontend` job).

---

## 7. Recommended fixes (not applied)

In priority order:

1. **R8-02:** change the ci.yml `frontend` step and the TRD 16 job table to `npm run test`. Add `@vitest/coverage-v8` 2.x to TRD 04 §4.1 and the TRD 13 §6 tools line.
2. **R8-03:** add `npm run format:check` to CIC-017, the job table and ci.yml, and add `format` and `format:check` to TRD 16 §6. Change GIT-042 to `npm run format:check`. Reconcile `eslint-config-prettier` between TRD 18:198 and FE-200 and §4.1.
3. **R8-05:** in TST-004 and D-73, specify that `playwright.isolated.config.ts` sets `grep: /@isolated/` (or a `testMatch` for one serial file, for example `isolated.spec.ts`) holding E2E-15, TST-187 and E2E-19 in that order. Fix the TRD 04 E2E row (API login per invocation; `isolated-setup.ts`) and add the isolated config to the TRD 04 tree.
4. **R8-04:** choose one component-test location (TRD 04 co-location is used in three places) and align TRD 13 §4.2 and TST-010. Say where page tests live and exclude `*.test.tsx` from coverage.
5. **R8-06:** define the `resolve-data-alert` syntax, refusals and audit details, and add a TRD 13 test for FR-297.
6. **R8-01:** escape the pipes in the 12 listed rows, and add a table cell-count check to CI.

---

## 8. Prior findings status

### 8.1 Round-7 findings (R7-01..R7-06)

| ID | Round-7 severity | Subject | Status | Evidence (round 8) |
|---|---|---|---|---|
| R7-01 | Major | The `@isolated` E2E run has no valid session | **Resolved** | D-74(a) (24:237): `isolated-setup.ts`, the `globalSetup` of `playwright.isolated.config.ts`, logs in once per role against the `echowell_demo` backend after `e2e.yml` has started and seeded it, never resets or seeds, and writes `frontend/tests/e2e/.auth/isolated-<role>.json`. E2E-15, TST-187 and E2E-19 use these files through the same role fixture. The same text appears in D-73 (24:236), TST-004 (13:87), the §4.10 preamble (13:357), the Table 4.10-A note (13:364), §8 (13:561), CIC-030 (16:410) and the `e2e.yml` step comment (16:381). The isolated step seeds with `seed test_v0_1 --master-only` before `npm run test:e2e:isolated` (16:378–381), so the users exist with their `echowell_demo` IDs when the setup logs in. The TRD 18 `.auth/` ignore entry (18:306) covers the new files. Residual detail (test selection and order) is new finding R8-05, not a regression. |
| R7-02 | Minor | `npx playwright test` versus the D-73 invocation scheme | **Resolved** | TRD 04 §4.15 (04:632–634) defines exactly `test:e2e:readonly` (`--grep-invert "@isolated\|@mutating"`, rendered as one alternation), `test:e2e:mutating` (`--grep @mutating --workers=1`) and `test:e2e:isolated`. TST-004 adds `grepInvert: /@isolated/`. D-73, CIC-030, the `e2e.yml` loop (16:367–369) and isolated step, TRD 16 §6 (16:542, "no bare `test:e2e`") and TRD 25 Phases 8 and 11 (25:244, 25:277) use only these scripts. No bare `test:e2e` or `npx playwright test` remains. The cells touched by the fix render correctly (`r8/tbl.py`); other rows elsewhere are new finding R8-01. |
| R7-03 | Minor | ENV-041 exit 2 versus ENV-002 exit 1 | **Resolved** | ENV-002 (21:50): exit 1 is the single code for every settings-validation failure "in the backend, the nightly job and every CLI command", and exit 2 is reserved for command-specific CLI refusals (DEP-070, the §4.8 table, DB-024, DB-057) checked before settings validation. ENV-041 (21:220), ENV-054 (21:99) and the SEED_* row (21:85) say exit 1. The SEED_* "missing → exit 2" for `seed` is a command-specific refusal (DB-057) and so is consistent. |
| R7-04 | Minor | Advisory-lock helper in two modules | **Resolved** | DB-021 (06:462): `backend/core/db.py::advisory_key`, matching the TRD 05 module tree (05:98) and API-125. `backend/db.py` no longer occurs (`paths.py`). |
| R7-05 | Minor | pytest markers and dev requirements | **Resolved** | TST-006 (13:89) is the single marker list (`unit`, `integration`, `contract`, `validation`, `security`, `performance`, `smoke`, plus `slow`, `authenticated`, `budget`, `req`), registered with `--strict-markers`. TRD 16 §6 (16:541) refers to it. Every marker used in the TRDs is in the list. TRD 16 §6 (16:540) is the single dev-tool list and includes import-linter, testcontainers-python, openapi-core, Hypothesis, time-machine, Bandit and pip-audit. TRD 13 §6 (13:535) repeats it and refers to it. |
| R7-06 | Minor | TRD 18 required-check note omits `playwright` | **Resolved** | TRD 18:414: "required check names are the job ids listed in TRD 16 CIC-070 (from `ci.yml` and `e2e.yml`, including `playwright`)". This matches CIC-070 (16:474), GIT-010 and TRD 18:95. |

Totals: Resolved 6, Partially resolved 0, Not resolved 0.

Spot checks of the resolutions from rounds 1–6 found no regression. They covered:
- the seeded `@example.com` accounts;
- the D-71 staging exception;
- the D-72 provisioning step and time zone (re-executed);
- RATE_LIMIT_LOGIN and ENV-054;
- the `@mutating` group definition in D-73;
- the engine factory (API-125);
- `nightly-validation` (CIC-037) and `backend-test -p no:randomly`;
- the audit vocabulary;
- the CLI table;
- the endpoint, column and env-var cross-references.
