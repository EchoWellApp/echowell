# TRD Validation Report (Phase 1, round 7)

| Field | Value |
|---|---|
| Scope | `specs/TRD/00`–`25`, checked against `specs/prompts/TRD_Generation_Prompt.md`, `specs/architecture/Deployment_Architecture.md`, `specs/UI-wireframe/*.dc.html` (5 files), `specs/business-requirements/*`, `specs/data-samples/*` |
| Checklist | `specs/prompts/TRD_Implementation_Audit_Checklist.md` Phase 1, and the definition of done in TRD 25 §Phase 1 |
| Round | 7. This report replaces round 6 (8 findings, R6-01..R6-08). It was written after the round-6 fixes in `docs/reports/TRD_VALIDATION_FIXES.md` were applied. |
| Branch | `trd-generation`. This run was read only: no file under `specs/` was changed and no git command was run. |
| Date | 2026-10-19 |

**How locations are written.** `TRD NN:line` means line `line` of `specs/TRD/NN_*.md`.

**Severity scale** (the same as rounds 1–6):

| Severity | Meaning |
|---|---|
| Critical | Built as written, the system would be wrong or unsafe. |
| Major | An implementer following the TRDs would very likely build something that fails its own required tests or the sources. |
| Minor | A real inconsistency or error that a careful implementer would still resolve without harm. |

**Numbering.** New findings in this round are R7-01, R7-02 and so on. Earlier findings keep their numbers (section 8).

**Scripts and scratch data** are in `/tmp/claude-0/-home-user-echowell/06d21bae-4975-509b-846a-5a1512c441c2/scratchpad/`:
- the round-1 to round-6 scripts: `xref.py`, `ids2.py`, `ep.py`, `cols.py`, `env.py`, `err.py`, `aud.py`, `paths.py`, `br3.py` and `wb*.py`;
- for this round: `t_r7.sh`, plus `r7/sql/` (the SQL fences), `r7/paths_r7.txt` and `r7/t/` (the pytest-randomly check).

---

## 1. Summary

**Verdict: FAIL.** The rule is FAIL if any Critical or Major finding remains. One Major finding remains.

- **R7-01 (Major): the `@isolated` E2E run has no valid login session.**
  - D-74 (TRD 24:237) and the TRD 13 note to Table 4.10-A (13:364) define "log in as …" for every scenario except E2E-01, E2E-02 and FE-188. It means the per-role session that `globalSetup` stores in `frontend/tests/e2e/.auth/<role>.json`.
  - The `@isolated` run (E2E-15, TST-187, E2E-19) uses `frontend/playwright.isolated.config.ts`, which has no `globalSetup` (D-73, TST-004, CIC-030, TRD 16:381). Nothing creates sessions for it.
  - The only session files on disk are the ones left over from the last main-run invocation. Their tokens carry the `sub` (user UUID) of the main database's seeded users.
  - The isolated backend serves `echowell_demo`, where `seed --master-only` creates the same e-mail addresses with new `gen_random_uuid()` IDs (TRD 20:270). API-012 (05:124) and SEC-034 reject a token whose `sub` does not exist with 401 `TOKEN_INVALID`. FE-056 then clears the token and redirects to `/login`.
  - Result: built as specified, E2E-15 (`/residents`), TST-187 (reload of `/residents`) and E2E-19 (admin ingest, pipeline run, `/alerts`) fail on every run. They are part of the required `playwright` check (CIC-031, CIC-070).
  - This defect was introduced by the round-6 fix for R6-01. D-74(b) and CIC-030 even raise RATE_LIMIT_LOGIN for the isolated run, but no TRD says who logs in there.

The round-6 fixes otherwise held:
- **Login reuse.** D-74 (`addInitScript` writing the token to `sessionStorage`, because `storageState` does not capture it) is consistent with SEC-037, FE-050 and FE-053.
- **Login rate limit.** RATE_LIMIT_LOGIN is `60/minute` on the E2E stack, ENV-054 enforces `5/minute` in staging and production, and the pytest limiter is reset before every test. These agree across TRD 05, 12, 13, 16, 21 and 24.
- **Engine factory and backend restart.** One engine factory, `backend/core/db.py`, sets `prepare_threshold=None` (API-125, TRD 15:566, TRD 21:284), and `globalSetup` restarts the backend after the reset.
- **The `@mutating` group** is defined once, in D-73 (`mutating.spec.ts`: E2E-18, then E2E-09 implemented by FE-187, then the FE-193 snooze step). It is referenced consistently, and CUS-017 allows the second review on R09.
- **Smaller round-6 fixes.** TST-005 is scoped to pytest and Vitest. DME-022, API-132 and CUS-039 use the application clock, and FE-205 covers snooze expiry in the UI. PGS-016 points to `backend-test`. `nightly-validation` (CIC-037) exists, and `backend-test` uses `-p no:randomly`. `pytest -p randomly` was executed and loads the plugin. The D-list bookkeeping is correct.
- **Database.** The TRD 20 DDL was re-executed on PostgreSQL 16 with identical results: 24 tables, 17 triggers, 15 enums, 46 config rows, `timezone` UTC, and all permission checks pass.
- **Prior findings.** 7 of 8 round-6 findings are fully resolved. R6-01 is partially resolved: the rate-limit contradiction is gone, but the D-74 session reuse does not cover the `@isolated` run (R7-01).

The other five findings are Minor:
- R7-02 is a test-invocation inconsistency.
- R7-03 to R7-06 are older inconsistencies that earlier rounds missed. None was introduced by round 6.

| Severity | Count |
|---|---|
| Critical | 0 |
| Major | 1 |
| Minor | 5 |
| **Total new (round 7)** | **6** |

Prior findings:

| Set | Resolved | Partially resolved | Not resolved |
|---|---|---|---|
| R6-01..R6-08 (8) | 7 (R6-02..R6-08) | 1 (R6-01) | 0 |

Phase 1 checks:

| # | Phase 1 check | Result | Key evidence |
|---|---|---|---|
| 1 | Database requirements support all APIs | **PASS** | All 24 tables, 15 enums, CHECK constraints and grants support E-01..E-32. The 33 TRD 20 `sql` fences are byte-identical to round 6, and they were re-executed as the migrator on a freshly provisioned database (exit 0). The permission and trigger checks behave as specified. Minor: R7-04 (two paths for the advisory-lock helper). |
| 2 | APIs support all frontend requirements | **PASS** | All 32 endpoints are in TRD 19, and every `/api/v1` path used in the TRDs resolves. FE-205 needs only `snoozed_until`, which the `Alert` schema provides. |
| 3 | Analytics requirements support all business requirements | **PASS** | The workbook and SRC-05 were re-verified with `python3 -I` and pandas (section 6.3). Every figure matches. |
| 4 | Testing requirements validate all critical functionality | **FAIL** | R7-01: the `@isolated` scenarios have no valid session. Minor: R7-02 (`npx playwright test` versus the D-73 invocation scheme) and R7-05 (pytest markers and dev requirements differ between TRD 13 and TRD 16). |
| 5 | Deployment requirements support the architecture | **PASS** | The interim stack (Netlify, Railway, Neon, with Railway PostgreSQL as the alternative) and the AWS target match `Deployment_Architecture.md`. ENV-054 keeps the login limit at 5/minute in staging and production. Minor: R7-03 (startup exit code) and R7-06 (branch-protection note). |

TRD 25 §Phase 1 definition of done:

| Criterion | Result | Evidence |
|---|---|---|
| Every BR-01..BR-18 maps to at least one TRD requirement and test | **Met** | Section 2.1. Each BR is cited by 25–271 requirement rows across 10–24 TRDs. |
| Every OQ/ASM/RSK/DSC/D ID used exists in TRD 24 | **Met** | ASM-01..08, DSC-01..14, OQ-01..26, RSK-01..15 and D-01..D-74 are all defined, with no duplicates. `OQ-27` and `RSK-16` appear only in the "next free" rule (TRD 24:265). |
| Each of the five checks has a pass/fail line | **Met** | The table above and section 6 |
| No TRD file modified | **Met** | This run was read only |
| `grep -rnE "T[B]D\|T[O]DO\|l[o]rem" specs/TRD` returns nothing | **Met in substance** | The only hit is GIT-053 (TRD 18:219), the rule that forbids these words. The same hit was accepted in rounds 1–6. |

---

## 2. Requirements Traceability Matrix

### 2.1 Business requirements → TRD requirements → tests

The counts come from `br3.py`. A table row counts when its first cell is a requirement ID and the row cites the BR, directly or within a range. The restatement tables (BR, SRC, OQ, ASM, RSK, DSC) are excluded. The only change from round 6 is BR-16, which rose from 270 to 271 rows with ENV-054.

| BR | Summary (TRD 00) | Rows / TRDs | Key FRs (TRD 02) | Tests / MVP criteria | Gap (round 7) |
|---|---|---|---|---|---|
| BR-01 | Ingest feature records, never audio | 80 / 20 | FR-001–FR-005, FR-020–FR-028 | TST-030, TST-043, TST-045, TST-046, TST-133, TDV-031, TDV-090, MVP-02 | — |
| BR-02 | Keep raw records unaltered | 101 / 17 | FR-005–FR-007, FR-010, FR-028 | TST-037, TST-041, TST-043, TDV-002, TDV-050, TDV-054, MVP-02, MVP-12 | — |
| BR-03 | Drop duplicates, keep first arrival | 40 / 13 | FR-008, FR-011, FR-029–FR-031 | TST-020, TST-044, TST-046, TDV-054, MVP-01, MVP-03 | — |
| BR-04 | Set aside poor-quality sessions | 28 / 13 | FR-024, FR-040–FR-044 | TST-020, TDV-053, MVP-01, MVP-03 | — |
| BR-05 | Quarantine wrong-speaker sessions | 27 / 10 | FR-060–FR-065 | TST-020, TDV-055, MVP-01, MVP-03 | — |
| BR-06 | Log missing days honestly | 69 / 15 | FR-120–FR-125, FR-135 | TST-020, TDV-052, TDV-053, TDV-064, TDV-068, MVP-01 | — |
| BR-07 | Remove morning offset | 26 / 11 | FR-070–FR-074 | TST-020, TDV-056, MVP-01 | — |
| BR-08 | Epochs; restart baseline | 34 / 12 | FR-050–FR-053 | TST-020, TDV-057, MVP-01 | — |
| BR-09 | Robust personal baseline, frozen | 55 / 15 | FR-080–FR-086 | TST-020, TST-184, TDV-051, TDV-058, TDV-060, MVP-01 | — |
| BR-10 | Signed z and composite | 25 / 11 | FR-090–FR-095 | TST-020, TDV-051, MVP-01 | — |
| BR-11 | CUSUM persistent-deviation flag | 61 / 14 | FR-100–FR-110, FR-261–FR-265 | TST-020, TST-065, FE-205, TDV-059, TDV-060, TDV-067, MVP-01, MVP-13 | E2E-19 has no session: R7-01 |
| BR-12 | Residents overview | 92 / 17 | FR-130–FR-140, FR-150–FR-156 | TST-033, TST-090, TST-110, TST-181, TST-187, TDV-062, TDV-066, MVP-04 | TST-187 has no session: R7-01 |
| BR-13 | Resident detail page | 113 / 15 | FR-160–FR-173, FR-260–FR-280 | TST-090, TST-093, TST-110, TST-181, TST-187, TDV-066, MVP-05, MVP-13 | — |
| BR-14 | New-admission arm (Should) | 32 / 10 | FR-200–FR-207 | TST-090, TST-185, TST-186, MVP-06 | — |
| BR-15 | Reproduce workbook R01–R10 | 166 / 22 | FR-240–FR-245, FR-310–FR-323 | 41 TST/TDV/MVP rows, TST-084 (`nightly-validation`) | — |
| BR-16 | Data protection, roles, audit | 271 / 24 | FR-210–FR-221, FR-250–FR-254 | TST-007, TST-032, TST-041, TST-053, TST-130, TST-131, TST-188, TDV-006, TDV-007, MVP-07 | — |
| BR-17 | Monorepo deploy on Netlify/Railway/Neon/GHA | 74 / 15 | FR-253, FR-254 | TST-001, TST-150, TST-170, MVP-08 | R7-05, R7-06 (CI configuration text) |
| BR-18 | Detection not diagnosis, no LLM/ML | 47 / 15 | FR-164, FR-277, FR-278, FR-298 | TST-096, TST-097, TST-170, MVP-09 | — |

### 2.2 Frontend requirements (TRD_Generation_Prompt) → UX / FE IDs

Every item in the prompt's "Frontend Requirements" list (prompt line 93 onwards) was traced again. TRD 11 and TRD 19 have not changed since round 2. In TRD 04 only the E2E row, FE-187, FE-193 and the new FE-205 changed.

| Prompt frontend item | UX IDs | FE components (TRD 04 §4.8) | Tests | Round-7 note |
|---|---|---|---|---|
| Three primary views plus Alerts and Analytics | D-23; TRD 11 §4.3, §4.5, §4.7, §4.17, §4.18 | Residents page, Resident detail page, AdmissionsTable, AlertsPage, AnalyticsPage | E2E-03..E2E-21, TST-110 | — |
| All enrolled residents; sort by alarm, resident ID, last check-in | UX-020–UX-033, UX-261 | ResidentsTable, SortSelect | E2E-04, E2E-05, E2E-06 | — |
| Statuses Alarm On / No Alarm / Baseline Still Forming | §4.3.4, UX-036 | StatusBadge | E2E-04 | — |
| 30-day used, set aside, quarantined, missed; no backfill | UX-039, UX-047, UX-048 | ResidentsTable, SummaryTiles | E2E-03, E2E-04, E2E-15 | E2E-15: R7-01 |
| Device panel | UX-050–UX-058, UX-263 | DevicePanel, DeviceCell | E2E-07 | — |
| CUSUM tally, alarm line 5.0, baseline period | UX-080–UX-092 | CusumChart, CusumTable | TST-093, E2E-08 | — |
| 7 scored measurements; 12 others stored, not scored | UX-100–UX-108 | FeatureCard ×7, OtherMeasurementsCard | E2E-08, TST-090 | — |
| Baseline status, progress, freeze | UX-060–UX-066 | ResidentHeader, WhatThisMeans | E2E-08, E2E-10, E2E-11 | — |
| Check-in log | UX-140–UX-149 | CheckinLog | E2E-10..E2E-12, E2E-15 | E2E-15: R7-01 |
| Staff notes | UX-120–UX-135 | StaffReviewForm, NotesList, ReviewDialog | E2E-09 = FE-187 (`@mutating` step 2) | — |
| New admissions, "future/experimental" | UX-181–UX-195 | AdmissionsTable, FacilityRangeChart, ExperimentalBanner | E2E-13, TST-185, TST-186 | — |
| Alert review (SRC-18) | UX-300–UX-331 | AlertQueue, AlertCard, AlertReviewForm | E2E-17, E2E-18, E2E-19, TST-065, FE-193, FE-205 | E2E-19: R7-01 |
| Analytics (SRC-19) | UX-351–UX-384 | KpiTiles, LossFunnel, AlarmTimingTable, … | E2E-20, E2E-21, TDV-074 | — |
| Loading, empty and error states; accessibility; responsive | UX state rows, FE-145, NFR-060 | SectionState | TST-090, TST-110, E2E-16 | — |

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
| Demo path "new check-in appears" (E2E-15), the latency budget (TST-187) and the snooze UI (E2E-19) | Specified, but as built they fail at the first authenticated step (R7-01) |
| Local or agent run of the E2E suite (TRD 25 Phase 8 and Phase 11 commands, `npm run test:e2e`) | A single `playwright test` run does not follow the D-73 invocation scheme (R7-02) |

---

## 3. Missing Requirements

| ID | Severity | Where it is needed | What is missing |
|---|---|---|---|
| R7-01 | Major | D-74 (TRD 24:237), D-73 (24:236), TRD 13 §4.10 note (13:364) and §8 (13:561), CIC-030 (16:410), `e2e.yml` isolated steps (16:371–383), TST-004 (13:87) | How the `@isolated` scenarios obtain a session for the `echowell_demo` backend. For example, a setup for `playwright.isolated.config.ts` that logs in once per role after the isolated backend is up, or form logins in those three scenarios with D-74's list of real logins extended to match. |
| R7-02 | Minor | `playwright.config.ts` (TST-004), TRD 04 `test:e2e` (04:632), TRD 25 Phase 8 and Phase 11 commands (25:244, 25:277) | A rule that the default config excludes `@isolated` (`grepInvert`), or a script that runs the D-73 sequence. Without it, a plain `playwright test` mixes the groups. |

---

## 4. Contradictions

### 4.1 Major

**R7-01 · Major · The `@isolated` scenarios have no valid session for `echowell_demo`**

What the TRDs require:
- **Session reuse.**
  - D-74(a) (TRD 24:237): Playwright logs in once per role in `globalSetup`, after the D-73 reset and backend restart, and stores each session in `frontend/tests/e2e/.auth/<role>.json`. Scenarios reuse it through a role fixture. "Only the login scenarios (E2E-01, E2E-02, TRD 04 FE-188) … perform real logins."
  - The TRD 13 preamble (13:356–357) and the Table 4.10-A note (13:364) say the same: "Log in as clinician / researcher / admin" means the per-role session stored by `globalSetup`.
- **The isolated run has no `globalSetup`.**
  - D-73, TST-004 (13:87), CIC-030 (16:410) and §8 (13:561) all say that `frontend/playwright.isolated.config.ts` has no `globalSetup`.
  - The `e2e.yml` step (16:381) runs it after the backend has been restarted on `echowell_demo` (16:371–379).
- **The isolated scenarios need a user session.**
  - E2E-15 (13:382) checks the Residents overview and the check-in log.
  - TST-187 (13:519) reloads `/residents`.
  - E2E-19 (13:385) "as admin" posts the SRC-05 CSV to `/api/v1/ingest`, calls `POST /api/v1/pipeline/run` and opens `/alerts`.
- **Tokens are bound to a user row.**
  - SEC-031: `sub` is the user UUID.
  - API-012 (05:124): `get_current_user()` loads the `users` row by `sub` and rejects with 401 `TOKEN_INVALID` when it does not exist. SEC-034 says the same.
  - `users.id` defaults to `gen_random_uuid()` (TRD 20:270). `echowell_demo` is seeded separately with `seed test_v0_1 --master-only`, so its three users have different IDs from the main database's users.

Impact:
- The only session files present are those written by the last main-run `globalSetup`. They are signed with the same JWT_SECRET and not yet expired, but their `sub` does not exist in `echowell_demo`.
- Every authenticated request in the three isolated scenarios therefore returns 401. The frontend clears the token and redirects to `/login` (FE-056), so the scenarios fail at their first authenticated step.
- On a clean checkout with no main run before it, the files do not exist at all.
- The required `playwright` check (CIC-031, CIC-070) includes the isolated step, so it fails on every run.
- D-74(b) and CIC-030 ("Both runs use RATE_LIMIT_LOGIN=60/minute") imply that logins happen in the isolated run, but no TRD says who performs them.
- This is the same class of defect as R6-01 and R5-01 (E2E logins fail on every run), both rated Major.

Recommendation:
- Give `playwright.isolated.config.ts` its own `globalSetup`, for example `frontend/tests/e2e/isolated-setup.ts`. It should perform no reset, wait for `/api/v1/health` of the isolated backend, and write the same `.auth/<role>.json` files.
- Alternatively, add E2E-15, TST-187 and E2E-19 to D-74's list of form logins.
- Update D-73, D-74, TST-004, the TRD 13 note and §8, CIC-030 and the `e2e.yml` comment to match.

### 4.2 Minor

| ID | Location (A vs B) | Description and evidence | Recommendation |
|---|---|---|---|
| R7-02 | D-73 (24:236), CIC-030 and the `e2e.yml` loop (16:363–370): "one Playwright invocation per browser project and group", `--grep-invert "@isolated\|@mutating"`, then `--grep @mutating --workers=1`, then the isolated config. Versus TRD 04 `test:e2e` = `playwright test` (04:632), TRD 25 Phase 8 commands `… && npx playwright test` (25:244) and Phase 11 commands `npx playwright test` (25:277). | `playwright.config.ts` is not required to exclude `@isolated`, and nothing orders `@mutating` inside one invocation. A plain `playwright test` therefore runs E2E-15, TST-187 and E2E-19 against the main `test_v0_1` database, which has no R11 and no overlay roster. It also runs `mutating.spec.ts` in parallel with the read-only specs, and all configured browser projects after a single `globalSetup` reset. Phase 8's definition-of-done command then fails or becomes order-dependent, although the CI loop is correct. | Set `grepInvert: /@isolated/` in `playwright.config.ts`. Define `test:e2e` (or a `scripts/e2e.sh`) as the D-73 sequence, and use it in TRD 25 Phases 8 and 11. |
| R7-03 | ENV-041 (TRD 21:220): the backend "shall refuse to start (exit code 2)" when JWT_SECRET, a SEED_* value or a database password contains `local-dev-only`/`ci-only` in staging or production. Versus ENV-002 (21:50): "on any validation failure the process shall exit with code 1", and the TRD 12 note (12:426) that the startup checks live in `Settings.validate_for_env()`. ENV-054 (21:99) uses exit code 1. | One settings-validation path cannot satisfy both tests: an ENV-041 test expects 2, and the ENV-002 rule gives 1. The CLI convention of exit 2 (DB-024, DB-057, `set-config`) explains the origin, but ENV-041 applies it to the backend too. Present since round 4 (R4-07); not reported before. | State that the backend exits 1 (ENV-002) and the CLI commands exit 2, or make ENV-002 name the exception. |
| R7-04 | DB-021 (TRD 06:462): "the single helper `backend/db.py::advisory_key(namespace, value)`". Versus the TRD 05 module tree (05:96–98: `core/db.py — engine, SessionLocal, advisory-lock helpers`) and API-125 (05:377: the one engine factory `backend/core/db.py`). | The same "single" helper is placed in two modules. A builder following DB-021 creates `backend/db.py` next to `backend/core/db.py`. Present since round 1 (F-04); not reported before. | Change DB-021 to `backend/core/db.py::advisory_key`. |
| R7-05 | TRD 16 §6 (16:540–541): `requirements-dev.txt` = "ruff, mypy, pytest 8.x, pytest-cov, pytest-randomly 3.x, httpx, openpyxl 3.1.x, pip-audit", and `pyproject.toml` markers "`smoke`, `authenticated`, `validation`". Versus TST-006 (13:89): markers `unit`, `integration`, `contract`, `validation`, `security`, `performance`, `slow`, registered with `--strict-markers`. Also versus CIC-036 (16:416: marker `budget`), TST-013 (13:135: `@pytest.mark.req`) and the TRD 13 tools list (13:535: testcontainers-python, openapi-core, Hypothesis). | **Markers.** Under `--strict-markers` an unregistered marker is a collection error. Neither list contains `budget` or `req`, and the two lists disagree with each other. Registering either one as written makes `backend-test` fail at collection. **Dependencies.** The `requirements-dev` list omits packages that required jobs import or call: import-linter (`lint-imports` in `backend-lint`, 16:181), testcontainers-python, openapi-core, Hypothesis and `time-machine`. `time-machine` is required by TST-049, TST-065 and §8 but appears in neither tools list. | Make one marker list, the union `unit, integration, contract, validation, security, performance, slow, smoke, authenticated, budget, req`, in TST-006, and refer to it from TRD 16 §6. Complete the `requirements-dev` list, adding `time-machine` to it and to the TRD 13 tools list. |
| R7-06 | TRD 18 §8 (18:414): "required check names are the job ids of `ci.yml`". Versus CIC-070 (16:474), whose eight required checks include `playwright`, a job of `e2e.yml`, and TRD 18:95, which refers to CIC-070. | A ruleset configured from the TRD 18 note omits the `playwright` check, so a PR could merge with failing E2E tests. TRD 18:95 points to the correct list, so a careful implementer resolves it. | Change the note to "the job ids listed in TRD 16 CIC-070 (`ci.yml` and `e2e.yml` `playwright`)". |

---

## 5. Cross-Reference Validation

| Check | Method | Result | Findings |
|---|---|---|---|
| Duplicate requirement IDs | `xref.py` over the first cell of every table row and over list-item AC IDs | 2,006 requirement IDs defined, which is round 6's 2,003 plus FE-205, ENV-054 and CIC-037. No duplicates and no requirement ID in the wrong file. E-01..E-32 appear twice in TRD 19 by design (detail and summary). | — |
| Dangling requirement IDs | `xref.py` and `ids2.py` | None. The only script hits are the known artefacts: E2E-01..E2E-21 (defined as the first cell of Table 4.10-A with the name after the ID) and AC-DB-02a. | — |
| OQ / ASM / RSK / DSC / D vs TRD 24 | Per-prefix script: used versus defined, plus duplicate definitions | ASM-01..08, DSC-01..14, OQ-01..26, RSK-01..15 and D-01..D-74 are defined exactly once. `OQ-27` and `RSK-16` appear only in the "next free" rule (24:265). | — |
| D-column bookkeeping | Script: each D-68..D-74 TRD column compared with the TRDs that cite the decision | D-71, D-72, D-73 and D-74 list every TRD that cites them. The extra entries are affected but non-citing TRDs: 03 for D-73 (AC-NFR-10) and 18 for D-74 (`.gitignore`). D-73 is now "03, 04, 05, 13, 15, 16, 25", and D-71 records "round 5 R5-01". | — |
| Revision rows | Script | The 15 TRDs changed in round 6 (03, 04, 05, 09, 12, 13, 14, 15, 16, 18, 20, 21, 23, 24, 25) are at 0.7, each with a "round-6 fixes" row. TRD 24 0.6 lists R5-03 and R5-04, and TRD 03 0.6 lists R5-02 (R6-08). Observation, not a finding: the TRD 13 §8 restart text serves both R6-01 and R6-02, and TRD 13's 0.7 row lists only R6-01. | — |
| Endpoints vs TRD 19 | `ep.py`: every `METHOD /path` compared with E-01..E-32 | All match. The only non-matches are the known ones: `/alerts/{id}/acknowledge` and `/audio` (in "shall not exist" text), `/openapi.json` and `/docs`, `PATCH /users` (meaning `/users/{id}`), the `/ingest]` Mermaid label and `/alerts/{R09 alert id}`. | — |
| Tables/columns vs TRD 20 DDL | `cols.py`: 24 `CREATE TABLE` blocks compared with every `table.column` token | All match. The only non-matches are `alerts.spec` (a file name) and `config_parameters.facility_tz` (config-key notation). | — |
| DDL executes | PostgreSQL 16 scratch cluster. `t_r7.sh` is `t_r6.sh` pointed at `r7/sql/`. The 33 fences re-extracted this round are byte-identical to round 6. | (0) Without extensions, 0001 as the migrator fails with the 0001 message (exit 3). (1) The provisioning fence as superuser on a database preset to America/Chicago, then roles: exit 0. (2) 0001 and 0002 as `echowell_migrator_login` with `SET ROLE`: exit 0, giving 24 tables, 17 triggers, 15 enums and 46 config rows, all owned by `echowell_migrator`, and `SHOW timezone` = `UTC`. (2b) The provisioning fence as the migrator is refused. (3) Downgrade base: exit 0, 0 tables, extensions kept. (3b) `DROP EXTENSION` as the migrator: "must be owner". (4) Re-migrate: same counts and `UTC`. The `seed.reset` audit row is accepted and `Auth.Login` is rejected. (5) The app login is denied `evaluation_ground_truth`, `SET ROLE echowell_readonly`, `DELETE alerts`, `UPDATE raw_sessions` and `DELETE audit_logs`, and `gen_random_uuid()` works. The readonly login is denied `password_hash`. An owner DELETE on `audit_logs` raises EW001 without the purge setting and succeeds with it. (6) Second database (the `echowell_demo` pattern): provisioning is idempotent and migration succeeds. | — |
| Env vars vs TRD 21 | `env.py`: 45 defined names compared with env-style tokens | All defined. The non-matches are the same known ones as in round 6: error codes, report names, workflow-local and GitHub variables, `RAILWAY_GIT_COMMIT_SHA` and `NIGHTLY_SCHEDULER_ENABLED`. RATE_LIMIT_LOGIN is consistent in the variable row (21:72), ENV-054 (21:99), both templates (21:176, 21:208), the matrix (21:236), API-102, SEC-091, `e2e.yml` (16:349) and D-74. | R7-03 (exit code) |
| Error codes vs TRD 05 | `err.py` (36 codes) | All in the catalogue | — |
| Audit actions vs TRD 12 §4.12 | `aud.py` (24 actions) | All in the vocabulary | — |
| CLI command names | `backend.cli <cmd>` occurrences compared with the TRD 15 §4.8 table (14 commands) | All 14 commands used are in the table | — |
| CI workflows / jobs / config files | `*.yml` names; job names compared with CIC-070 and CIC-002 | The five CIC-002 workflows are used consistently. Every job name used exists: `ci.yml` has 7 jobs; `e2e.yml` has `playwright`, `performance`, `lighthouse` and `nightly-validation`. PGS-016 now names `backend-test`. `frontend/playwright.config.ts`, `frontend/playwright.isolated.config.ts`, `frontend/tests/e2e/global-setup.ts`, `frontend/tests/e2e/mutating.spec.ts` and `frontend/tests/e2e/.auth/` are named identically in TRD 13, 16, 18 and 24. | R7-02, R7-06 |
| pytest plugin flags | `r7/t/`: pytest 8.3.3 and pytest-randomly 3.15.0 in an isolated target directory | `-p randomly` loads the plugin through its entry point and prints `Using --randomly-seed=…`. `-p no:randomly` disables it. The CIC-037 and `backend-test` commands are valid. | — |
| pytest markers and dev dependencies | Grep of TST-006, TST-013, CIC-035, CIC-036, TRD 15:424 and TRD 16:540–541 | The marker lists disagree and are incomplete under `--strict-markers`. The dev-requirements list omits tools that required jobs use. | R7-05 |
| File paths | `paths.py` (226 paths), plus a new same-file-name/different-directory check | New since round 6: `backend/core/db.py`, `frontend/tests/e2e/.auth/` and `frontend/tests/e2e/mutating.spec.ts`. The only directory conflict that is not by design is `backend/db.py` (TRD 06) versus `backend/core/db.py` (TRD 05). The others are by design: SRC copies in `specs/` versus `tests/fixtures/`, the relative `tests/e2e/` form in TRD 04, and `analytics/config.py` versus `backend/core/config.py`. Playwright spec names are used consistently (`staff-review.spec.ts` no longer appears). | R7-04 |
| Session and token chain (D-74) | Read SEC-030..SEC-038, FE-050..FE-056, API-012 and the `users` DDL | The main run works: tokens are restored from `sessionStorage` (FE-053) and the exp > 30 s condition holds within a 60-minute token life. The isolated run does not (R7-01). | R7-01 |
| Golden fixtures | pandas with `python3 -I` | Section 6.3 | — |
| Code fences / placeholders | Script / grep | Fence counts are even in all 26 files. The placeholder grep hits only GIT-053. | — |

---

## 6. The five checks in detail

### 6.1 Database requirements support all APIs: **PASS**

- Every endpoint E-01..E-32 reads and writes only tables and columns of the TRD 20 DDL.
- The `echowell_app` grants cover every API write, and the denials of PGS-021 and PGS-040 hold. This was executed (section 5).
- `alert_reviews` allows several reviews per alert (CUS-017), so the D-73 group order (E2E-18, then E2E-09 on the same R09 alert) is valid.
- `snoozed_until` is written from the application clock (DME-022, API-132, CUS-039). The column is a nullable `timestamptz`, so nothing in the DDL depends on `now()`.
- Minor: R7-04 (the advisory-lock helper is placed in two modules).

### 6.2 APIs support all frontend requirements: **PASS**

- All 32 endpoints are in the TRD 19 summary and YAML, and every TRD 04 client function resolves to an endpoint.
- `GET /config/ui` supplies the snooze hours and the review explanations.
- FE-205 relies on `snoozed_until` in the `Alert` schema and needs no new field.
- No frontend item lacks an API source.

### 6.3 Analytics requirements support all business requirements: **PASS**

SRC-03 and SRC-05 were read again with `python3 -I` and pandas (`wb.py`..`wb4.py`). Every value matches the TRDs.

| Quantity | Value |
|---|---|
| Annotated_sessions `expected_status` (302 rows) | usable 267, missing_resident 17, set_aside 12, missing_device_gap 2, duplicate 2, quarantined 2 (missed tile 19; funnel 300 → 281 → 269 → 267) |
| SRC-05 input | 283 rows, 30 columns, 2 duplicate `session_id`s |
| Exp_baselines | 180 rows; floor applied only to `number_of_pauses` (8 of 9 residents; R09 spread 0.7413, not floored) |
| Exp_scores | 98 rows: R01 14, R02 8, R03 6, R04 14, R05 12, R06 14, R07 2, R09 14, R10 14 |
| Alarm states | off 81, on 15, RINGS (first crossing) 2. Final tallies are R09 26.830256 and R10 13.418183, as in Alerts.dc.html, E2E-17, FE-193 and CIC-032. |
| Parameters | baseline length 16, spread MAD × 1.4826, floor 0.5 (pauses) and 0.1 (composite), CUSUM k 0.5, alarm line 5.0, speaker screen \|F0 z\| ≥ 4.0 with ≥ 2 features \|z\| ≥ 3.0 |

No findings.

### 6.4 Testing requirements validate all critical functionality: **FAIL**

- Every BR has TST, TDV or MVP coverage.
- The round-6 fixes work for the main run:
  - one reset and backend restart per invocation;
  - three API logins per invocation, plus at most about six form logins (E2E-01, E2E-02, FE-188), well below 60/minute;
  - read-only scenarios first, then the serial `@mutating` group;
  - the limiter reset before every pytest test, with TST-131 setting its limits explicitly.
- TST-005 is scoped correctly. Random order is verified nightly, and `backend-test` stays fixed-order.
- Snooze is covered at three levels: E2E-19 (UI state and stored value), TST-065 (stored value and expiry with `time-machine`) and FE-205 (UI regrouping with fake timers).
- Fails on R7-01: the `@isolated` scenarios cannot authenticate against `echowell_demo`.
- Minor:
  - R7-02: the plain `playwright test` command contradicts the D-73 invocation scheme.
  - R7-05: the pytest marker and dev-dependency lists are inconsistent.

### 6.5 Deployment requirements support the architecture: **PASS**

- The architecture follows `Deployment_Architecture.md`: a monorepo; Next.js on Netlify; FastAPI on Railway; Neon, with Railway PostgreSQL as the alternative; GitHub Actions; and the AWS target (Amplify, App Runner, RDS).
- ENV-054 makes the backend refuse any RATE_LIMIT_LOGIN other than `5/minute` in staging and production. The staging smoke test performs a single login (DEP-080), and `uptime.yml` does not log in.
- The D-71 staging exception, the D-72 provisioning step and the placeholder-credential rules are unchanged and consistent.
- Minor:
  - R7-03: ENV-041 uses exit 2, while ENV-002 uses exit 1.
  - R7-06: the branch-protection note in TRD 18 omits `playwright`.

---

## 7. Recommended fixes (not applied)

In priority order:

1. **R7-01:** give `playwright.isolated.config.ts` a setup that logs in once per role against the isolated backend and writes `.auth/<role>.json`, without a reset. Alternatively, add E2E-15, TST-187 and E2E-19 to D-74's list of form logins. Then align D-73, D-74, TST-004, TRD 13 (§4.10 note and §8), CIC-030 and the `e2e.yml` comment.
2. **R7-02:** set `grepInvert: /@isolated/` in `playwright.config.ts`, define `test:e2e` as the D-73 sequence, and use it in TRD 25 Phases 8 and 11.
3. **R7-05:** keep one complete pytest marker list in TST-006 (including `smoke`, `authenticated`, `budget` and `req`) and refer to it from TRD 16 §6. Complete the `requirements-dev` list (import-linter, testcontainers-python, openapi-core, Hypothesis, time-machine) and add `time-machine` to the TRD 13 tools list.
4. **R7-03, R7-04, R7-06:**
   - Reconcile the ENV-041 exit code with ENV-002.
   - Change DB-021 to `backend/core/db.py`.
   - Make the TRD 18 §8 note refer to the CIC-070 list.

---

## 8. Prior findings status

### 8.1 Round-6 findings (R6-01..R6-08)

| ID | Round-6 severity | Subject | Status | Evidence (round 7) |
|---|---|---|---|---|
| R6-01 | Major | The E2E suite exceeds the login rate limit | **Partially resolved** | **Resolved part, login reuse:** D-74 (24:237) has `globalSetup` log in once per role after the reset and restart, stores the sessions in a git-ignored `frontend/tests/e2e/.auth/` (TRD 18:306), and uses a role fixture that writes the token with `addInitScript` because `storageState` does not capture `sessionStorage`. This is consistent with SEC-037, FE-050 and FE-053. **Resolved part, limit override:** `e2e.yml` sets RATE_LIMIT_LOGIN=`60/minute` (16:349). ENV-054 (21:99), the variable row and the matrix (21:72, 21:236), API-102 (05:347), SEC-091 (12:264) and CIC-030 agree, and staging and production are pinned to `5/minute`. **Resolved part, pytest:** the autouse limiter reset is in the conftest tree (13:97), and TST-131 (13:418) sets its own limits. **Also aligned:** the TRD 13 preamble and Table 4.10-A note, §8, and the TRD 04 E2E row. **Residue:** the session reuse does not reach the `@isolated` run (R7-01). |
| R6-02 | Minor | Reset under a live connection pool | **Resolved** | API-125 (05:377): one engine factory `backend/core/db.py` with `connect_args={"prepare_threshold": None}` in every environment; TRD 15:566 and TRD 21:284 point to it. `globalSetup` runs `docker compose restart backend` and waits for health (D-73, CIC-030, TRD 13 §8). There is no test-hook endpoint. |
| R6-03 | Minor | FE-187 outside the `@mutating` group | **Resolved** | D-73 is the single definition: `mutating.spec.ts` runs (1) E2E-18, (2) E2E-09 = FE-187 with the same note and outcome ("Cold, cough or sore throat", "Explained by a known cause"), (3) the FE-193 snooze step on R10. TST-100, the §4.10 preamble, §8, E2E-09, E2E-18, CIC-030, CIC-032, the `e2e.yml` comment, the TRD 04 E2E row, FE-187, FE-193 and TRD 25:243 all reference it. CUS-017 allows the second review on R09. |
| R6-04 | Minor | TST-005 versus E2E ordering and wall clock | **Resolved** | TST-005 (13:88) covers unit and integration tests only. E2E may depend on the D-73 order and, where stated, on the current time (E2E-15, TST-187, E2E-19). It is verified in `nightly-validation`. |
| R6-05 | Minor | Snooze expiry not observable | **Resolved** | DME-022 (23:62) and its attribute row (23:393), API-132 (05:252) and CUS-039 (09:254) use the application clock. TST-065 (13:298) asserts the stored value and, after time travel, `snoozed_until` < now. FE-205 (04:615) uses Vitest fake timers to check the regrouping with no API call. E2E-19 and D-73 reference both. |
| R6-06 | Minor | PGS-016 names a nonexistent job | **Resolved** | PGS-016 (20:73): "Test (CI job `backend-test`, TRD 16)". |
| R6-07 | Minor | No nightly random-order or robustness job | **Resolved** | CIC-037 (16:415) adds the `nightly-validation` job to the `e2e.yml` outline (16:391–404), on schedule and dispatch only. It runs `pytest -p randomly` (executed: valid) and `robustness.py` with `continue-on-error`. It is not required (CIC-070), and CIC-112 and CIC-033 cover it. `backend-test` uses `-p no:randomly` (16:220). pytest-randomly is in TRD 13:535 and 16:540. TST-084, TST-151 and TDV-083 point to CIC-037. |
| R6-08 | Minor | D-list and revision bookkeeping | **Resolved** | The D-73 TRD column is "03, 04, 05, 13, 15, 16, 25". D-71's sources include "round 5 R5-01" and its TRDs include 05. TRD 24 0.6 lists R5-03 and R5-04, and TRD 03 0.6 lists R5-02. |

Totals: Resolved 7, Partially resolved 1, Not resolved 0.

Spot checks of the resolutions from rounds 1–5 found no regression. They covered:
- the seeded `@example.com` accounts;
- the D-71 staging exception;
- the D-72 provisioning step and time zone (re-executed);
- the closed migrator list;
- the audit vocabulary;
- the as-of precedence;
- the CLI table;
- the placeholder-credential rules;
- the endpoint, column and env-var cross-references.
