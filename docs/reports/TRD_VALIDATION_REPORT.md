# TRD Validation Report (Phase 1, round 5)

| Field | Value |
|---|---|
| Scope | `specs/TRD/00`–`25`, checked against `specs/prompts/TRD_Generation_Prompt.md`, `specs/architecture/Deployment_Architecture.md`, `specs/UI-wireframe/*.dc.html` (5 files), `specs/business-requirements/*`, `specs/data-samples/*` |
| Checklist | `specs/prompts/TRD_Implementation_Audit_Checklist.md` Phase 1, and the definition of done in TRD 25 §Phase 1 |
| Round | 5. This report replaces round 4 (9 findings, R4-01..R4-09). It was written after the round-4 fixes in `docs/reports/TRD_VALIDATION_FIXES.md` were applied. |
| Branch | `trd-generation`. This run was read only: no file under `specs/` was changed and no git command was run. |
| Date | 2026-10-19 |

**How locations are written.** `TRD NN:line` means line `line` of `specs/TRD/NN_*.md`.

**Severity scale** (the same as rounds 1–4):

| Severity | Meaning |
|---|---|
| Critical | Built as written, the system would be wrong or unsafe. |
| Major | An ambiguity or conflict that an implementer would probably resolve the wrong way, or a mandated path or check that cannot work as specified. |
| Minor | A real inconsistency or error that a careful implementer would still resolve correctly. |

**Numbering.** New findings in this round are R5-01, R5-02 and so on. Earlier findings keep their numbers (section 8).

---

## 1. Summary

**Verdict: FAIL.** The rule is FAIL if any Critical or Major finding remains. Two Major findings remain. Both concern the seeded test accounts and the E2E database that rounds 3–4 introduced (D-71, R4-05).

- **R5-01 (Major): the seeded users cannot log in on the specified stack.** The seeded accounts use the reserved `.test` top-level domain: `admin@echowell.test`, `clinician@echowell.test` and `researcher@echowell.test` (DB-057, D-71).
  - TRD 19 declares `LoginRequest.email` and `UserCreate.email` as `format: email`. OAS-003, OAS-004 and OAS-005 require the generated OpenAPI to match that skeleton.
  - In FastAPI with Pydantic 2, the normal way to emit `format: email` is `EmailStr`, which uses `email-validator`.
  - Tested with email-validator 2.2.0 and pydantic 2.9.2: `EmailStr` rejects `admin@echowell.test` with "The part after the @-sign is a special-use or reserved name that cannot be used with email." The same test accepts `admin@example.com`.
  - Every E2E login (TST-100, the CIC-031 required check), the staging smoke login (DEP-080(c), CIC-042) and the local quick-start login (TRD 15:143) would get a 422.
- **R5-02 (Major): the main E2E database does not stay unchanged, although CIC-030 says it does.**
  - CIC-030 (TRD 16:389) and TRD 13:554 say the main E2E database "stays exactly the `test_v0_1` seed".
  - However, E2E-09 (TRD 13:370) and E2E-18 (13:378) save reviews on the R09 alarm in that database.
  - E2E-01, E2E-17, E2E-20 and CIC-032 then assert the unreviewed state: "Alerts (2)", R09 "Not reviewed", and "both not yet reviewed".
  - The nightly run executes Chromium, Firefox and WebKit against the same database in one `npx playwright test` call (TRD 16:362). After any one browser saves its review, the scenarios that expect the unreviewed state fail in the other browsers. On pull requests, the result depends on worker order.

The round-4 fixes held where it matters most:
- **D-72 (extensions created by the provisioning step) works.** It was re-tested from scratch on PostgreSQL 16 (section 5, "DDL executes").
  - Provisioning ran as superuser.
  - The migrations ran as `echowell_migrator_login` with `SET ROLE`.
  - The cycle drop-all → re-migrate → drop-all ran with exit 0 each time: 24 tables, 17 triggers, 15 enums and 46 config rows, with both extensions kept.
  - All app and readonly permission checks behaved as TRD 20 §7 requires.
- **R4-01, R4-04, R4-08 and R4-09 are fully resolved.**
- **R4-02, R4-03, R4-05, R4-06 and R4-07 are partly resolved.** At least one TRD touching each topic was not updated (R5-02..R5-06, R5-08, R5-10, R5-11).

| Severity | Count |
|---|---|
| Critical | 0 |
| Major | 2 |
| Minor | 9 |
| **Total new (round 5)** | **11** |

Prior findings:

| Set | Resolved | Partially resolved | Not resolved |
|---|---|---|---|
| R4-01..R4-09 (9) | 4 (R4-01, R4-04, R4-08, R4-09) | 5 (R4-02, R4-03, R4-05, R4-06, R4-07) | 0 |

Phase 1 checks:

| # | Phase 1 check | Result | Key evidence |
|---|---|---|---|
| 1 | Database requirements support all APIs | **PASS** | All 24 tables, 15 enums, CHECK constraints and grants support E-01..E-32. The DDL was re-executed as the migrator on a provisioned database (exit 0), and all 15 TRD 20 §7 permission and trigger checks that were sampled behaved as specified. Minor: R5-07 (who sets the database time zone), R5-08 (stale `reject_mutation` comment). |
| 2 | APIs support all frontend requirements | **PASS** | All 32 endpoints are in TRD 19. Every `/api/v1` path used in the TRDs resolves. TRD 04, 11 and 19 have not changed since round 2. R5-01 is an API validation issue with the test accounts, not a missing endpoint, so it is counted under checks 4 and 5. |
| 3 | Analytics requirements support all business requirements | **PASS** | The workbook was re-verified with `python3 -I` and pandas (section 6.3). Every figure matches. |
| 4 | Testing requirements validate all critical functionality | **FAIL** | R5-01 (seeded logins rejected), R5-02 (shared main E2E database). Minor: R5-03, R5-04, R5-05. |
| 5 | Deployment requirements support the architecture | **FAIL** | R5-01 breaks the staging smoke login (DEP-080(c)) and the local quick start. Minor: R5-06, R5-09, R5-10, R5-11. |

TRD 25 §Phase 1 definition of done:

| Criterion | Result | Evidence |
|---|---|---|
| Every BR-01..BR-18 maps to at least one TRD requirement and test | **Met** | Section 2.1. Each BR is cited by 25–269 requirement rows across 10–24 TRDs. |
| Every OQ/ASM/RSK/DSC/D ID used exists in TRD 24 | **Met** | ASM-01..08, DSC-01..14, OQ-01..26, RSK-01..15 and D-01..D-72 are all defined. `OQ-27` and `RSK-16` appear only as "next free" text at TRD 24:263. The stated ranges are stale (R5-09). |
| Each of the five checks has a pass/fail line | **Met** | The table above and section 6 |
| No TRD file modified | **Met** | This run was read only |
| `grep -rnE "T[B]D\|T[O]DO\|l[o]rem" specs/TRD` returns nothing | **Met in substance** | The only hit is GIT-053 (TRD 18:219), the rule that forbids these words. The same hit was accepted in rounds 1–4. |

---

## 2. Requirements Traceability Matrix

### 2.1 Business requirements → TRD requirements → tests

The counts below come from a script. A table row counts when its first cell is a requirement ID and the row cites the BR, directly or within a range. The restatement tables (BR, SRC, OQ, ASM, RSK, DSC) are excluded. The counts are identical to round 4.

| BR | Summary (TRD 00) | Rows / TRDs | Key FRs (TRD 02) | Tests / MVP criteria | Gap (round 5) |
|---|---|---|---|---|---|
| BR-01 | Ingest feature records, never audio | 80 / 20 | FR-001–FR-005, FR-020–FR-028 | TST-030, TST-043, TST-045, TST-046, TST-133, TDV-031, TDV-090, MVP-02 | — |
| BR-02 | Keep raw records unaltered | 101 / 17 | FR-005–FR-007, FR-010, FR-028 | TST-037, TST-041, TST-043, TDV-002, TDV-050, TDV-054, MVP-02, MVP-12 | Stale purge-path comment: R5-08 |
| BR-03 | Drop duplicates, keep first arrival | 40 / 13 | FR-008, FR-011, FR-029–FR-031 | TST-020, TST-044, TST-046, TDV-054, MVP-01, MVP-03 | — |
| BR-04 | Set aside poor-quality sessions | 28 / 13 | FR-024, FR-040–FR-044 | TST-020, TDV-053, MVP-01, MVP-03 | — |
| BR-05 | Quarantine wrong-speaker sessions | 27 / 10 | FR-060–FR-065 | TST-020, TDV-055, MVP-01, MVP-03 | — |
| BR-06 | Log missing days honestly | 69 / 15 | FR-120–FR-125, FR-135 | TST-020, TDV-052, TDV-053, TDV-064, TDV-068, MVP-01 | — |
| BR-07 | Remove morning offset | 26 / 11 | FR-070–FR-074 | TST-020, TDV-056, MVP-01 | — |
| BR-08 | Epochs; restart baseline | 34 / 12 | FR-050–FR-053 | TST-020, TDV-057, MVP-01 | — |
| BR-09 | Robust personal baseline, frozen | 55 / 15 | FR-080–FR-086 | TST-020, TST-184, TDV-051, TDV-058, TDV-060, MVP-01 | — |
| BR-10 | Signed z and composite | 25 / 11 | FR-090–FR-095 | TST-020, TDV-051, MVP-01 | — |
| BR-11 | CUSUM persistent-deviation flag | 61 / 14 | FR-100–FR-110, FR-261–FR-265 | TST-020, TDV-059, TDV-060, TDV-067, MVP-01, MVP-13 | E2E-19 snooze expiry: R5-03 |
| BR-12 | Residents overview | 92 / 17 | FR-130–FR-140, FR-150–FR-156 | TST-033, TST-090, TST-110, TST-181, TST-187, TDV-062, TDV-066, MVP-04 | R5-02 (E2E-01), R5-04 (TST-187) |
| BR-13 | Resident detail page | 113 / 15 | FR-160–FR-173, FR-260–FR-280 | TST-090, TST-093, TST-110, TST-181, TST-187, TDV-066, MVP-05, MVP-13 | R5-02 (E2E-09/E2E-17/E2E-18) |
| BR-14 | New-admission arm (Should) | 32 / 10 | FR-200–FR-207 | TST-090, TST-185, TST-186, MVP-06 | — |
| BR-15 | Reproduce workbook R01–R10 | 166 / 22 | FR-240–FR-245, FR-310–FR-323 | 41 TST/TDV/MVP rows | — |
| BR-16 | Data protection, roles, audit | 269 / 24 | FR-210–FR-221, FR-250–FR-254 | TST-007, TST-032, TST-041, TST-053, TST-130, TDV-006, TDV-007, MVP-07 | R5-01, R5-10, R5-11 |
| BR-17 | Monorepo deploy on Netlify/Railway/Neon/GHA | 74 / 15 | FR-253, FR-254 | TST-001, TST-150, TST-170, MVP-08 | R5-01 (staging smoke), R5-06, R5-07 |
| BR-18 | Detection not diagnosis, no LLM/ML | 47 / 15 | FR-164, FR-277, FR-278, FR-298 | TST-096, TST-097, TST-170, MVP-09 | — |

### 2.2 Frontend requirements (TRD_Generation_Prompt) → UX / FE IDs

Every item in the prompt's "Frontend Requirements" list (prompt line 93 onwards) was traced again. TRD 04, 11 and 19 have not changed since round 2.

| Prompt frontend item | UX IDs | FE components (TRD 04 §4.8) | Tests | Round-5 note |
|---|---|---|---|---|
| Three primary views plus Alerts and Analytics | D-23; TRD 11 §4.3, §4.5, §4.7, §4.17, §4.18 | Residents page, Resident detail page, AdmissionsTable, AlertsPage, AnalyticsPage | E2E-03..E2E-21, TST-110 | Logins: R5-01 |
| All enrolled residents; sort by alarm, resident ID, last check-in | UX-020–UX-033, UX-261 | ResidentsTable, SortSelect | E2E-04, E2E-05, E2E-06 | — |
| Statuses Alarm On / No Alarm / Baseline Still Forming | §4.3.4, UX-036 | StatusBadge | E2E-04 | — |
| 30-day used, set aside, quarantined, missed; no backfill | UX-039, UX-047, UX-048 | ResidentsTable, SummaryTiles | E2E-03, E2E-04 | Main database now isolated from the overlay (R4-05) |
| Device panel | UX-050–UX-058, UX-263 | DevicePanel, DeviceCell | E2E-07 | — |
| CUSUM tally, alarm line 5.0, baseline period | UX-080–UX-092 | CusumChart, CusumTable | TST-093, E2E-08 | — |
| 7 scored measurements; 12 others stored, not scored | UX-100–UX-108 | FeatureCard ×7, OtherMeasurementsCard | E2E-08, TST-090 | — |
| Baseline status, progress, freeze | UX-060–UX-066 | ResidentHeader, WhatThisMeans | E2E-08, E2E-10, E2E-11 | — |
| Check-in log | UX-140–UX-149 | CheckinLog | E2E-10..E2E-12, E2E-15 | — |
| Staff notes | UX-120–UX-135 | StaffReviewForm, NotesList, ReviewDialog | E2E-09 | E2E-09 changes shared state: R5-02 |
| New admissions, "future/experimental" | UX-181–UX-195 | AdmissionsTable, FacilityRangeChart, ExperimentalBanner | E2E-13, TST-185, TST-186 | — |
| Alert review (SRC-18) | UX-300–UX-331 | AlertQueue, AlertCard, AlertReviewForm | E2E-17, E2E-18, E2E-19 | R5-02, R5-03 |
| Analytics (SRC-19) | UX-351–UX-384 | KpiTiles, LossFunnel, AlarmTimingTable, … | E2E-20, E2E-21, TDV-074 | E2E-20 tile text depends on run order: R5-02 |
| Loading, empty and error states; accessibility; responsive | UX state rows, FE-145, NFR-060 | SectionState | TST-090, TST-110, E2E-16 | — |

Result: every prompt item maps to UX IDs, FE IDs and at least one test. Every frontend item has an API source.

### 2.3 Wireframes → UX sections

The key strings were checked again with grep. All five wireframes are fully covered, with the same result as round 4.

| Wireframe | UX section | Key strings checked |
|---|---|---|
| `Main.dc.html` | TRD 11 §4.3, §4.4, §4.13 | "shared by R02", "silent all day" |
| `Resident.dc.html` | TRD 11 §4.5 | "Baseline complete", "alarm line 5.0" |
| `Admission.dc.html` | TRD 11 §4.7 | "Not in pipeline test v0.1" (line 1 of the banner, "Future / experimental study arm", is an intended addition) |
| `Alerts.dc.html` | TRD 11 §4.17 | "open 9 days", "tally 26.8", "13.4", "Alerts (2)", "Remind me in [24 h]" |
| `Analytics.dc.html` | TRD 11 §4.18 | "281", "267", "Alerts (2)" |

### 2.4 Items with no test or only a weak test

| Item | Status |
|---|---|
| Seeded-user login (every E2E scenario, staging smoke) | Cannot pass with `EmailStr` (R5-01) |
| E2E-01, E2E-17, E2E-18, E2E-20 and CIC-032 in the nightly 3-browser run | Their expectations conflict with E2E-09 and E2E-18 on the shared database (R5-02) |
| E2E-19 second assertion (emphasis returns after 24 h) | No way is given to advance the server clock (R5-03) |
| TST-187 (NFR-011, 5 s) | The record timestamp is not specified. Most natural choices are excluded by `as_of` (R5-04). |
| PGS-001 `SHOW timezone` = `UTC` | No step sets it, and the migrator cannot (R5-07) |

---

## 3. Missing Requirements

| ID | Severity | Where it is needed | What is missing |
|---|---|---|---|
| R5-01 | Major | DB-057 (TRD 06:593), D-71 (24:234), TRD 19 `LoginRequest`/`UserCreate` (19:1281, 19:1299), TRD 05 or TRD 12 | Either seeded e-mail addresses that a standard e-mail validator accepts (for example `@example.com`), or an explicit rule for how `format: email` is validated so that `.test` is accepted outside production. Neither is stated. |
| R5-03 | Minor | E2E-19 (TRD 13:379), `e2e.yml` (16:362–376) | A defined way to make a snooze expire in E2E: a test-only server clock, a shorter snooze, or a client-side comparison with `page.clock`. |
| R5-04 | Minor | TST-187 (TRD 13:512) | The `timestamp_utc` of the second R11 record |
| R5-07 | Minor | PGS-001 (TRD 20:58), provisioning (TRD 15:146–151, 15:230; TRD 20 §4.2–§4.3; D-72) | Who runs `ALTER DATABASE <db> SET timezone = 'UTC'`. Only the database owner or a superuser can, and no provisioning list includes it. |

---

## 4. Contradictions

### 4.1 Major

**R5-01 · Major · The seeded accounts use the reserved `.test` domain, and `format: email` validation rejects them**

What the TRDs require:
- **Seeded users.** The seed upserts `admin@echowell.test`, `clinician@echowell.test` and `researcher@echowell.test`: DB-057 (TRD 06:593), D-71 (24:234), TRD 20 §4.12, TRD 21:85.
- **Who logs in with them.** E2E logins (TRD 13:358, CIC-034, TRD 21:132), the staging smoke user (DEP-080(c) at TRD 15:428, TRD 21:131, TRD 16 §4.4 step 5), and the local quick start (TRD 15:142–143).
- **The API contract.** TRD 19 types `LoginRequest.email`, `UserCreate.email` and `User.email` as `{type: string, format: email}` (19:1281, 19:1288, 19:1299).
- **Contract tests.** OAS-003, OAS-004 and OAS-005 (19:48–50) require the generated OpenAPI to match that skeleton, including parameter constraints, and test it with `tests/contract/test_openapi_contract.py`.
- **The stack.** TRD 05:472 and TRD 01:94 fix the stack: FastAPI 0.115, Pydantic 2. SEC-080 requires Pydantic models for every request body.

Evidence. Scratch install of email-validator 2.2.0 and pydantic 2.9.2 under the scratchpad (`r5lib`), run with `PYTHONPATH`:
- `EmailStr` emits exactly `{'format': 'email', 'type': 'string'}`.
- `admin@echowell.test` is rejected: "value is not a valid email address: The part after the @-sign is a special-use or reserved name that cannot be used with email."
- `admin@example.com` is accepted.
- The `.test` address is accepted only after `email_validator.TEST_ENVIRONMENT = True`, which no TRD mentions.

Impact:
- An implementer who follows TRD 19 in the standard way gets 422 `VALIDATION_ERROR` on every seeded login.
- That blocks the following:
  - every E2E scenario, and so the required `playwright` check (CIC-031, CIC-070);
  - the staging smoke tests, and so `deploy-staging.yml` (CIC-042);
  - the local demo path (TRD 15 step 8).
- The browser accepts `.test` (FE-066 `type="email"`), so the failure appears only at the API.

Recommendation:
- Choose one option and state it in DB-057, D-71, TRD 21 and TRD 13. Either:
  - change the seeded domain to one that email-validator accepts (for example `example.com`); or
  - state in TRD 05 or TRD 12 that e-mail fields use a validator that accepts special-use domains when `APP_ENV` ≠ `production`, and keep `format: email` in the OpenAPI.
- Add a test that logs in as each seeded user.

**R5-02 · Major · Main-run E2E scenarios change the database that other main-run scenarios assert unchanged**

What the TRDs say:
- CIC-030 (TRD 16:389) and TRD 13:554 say the main E2E database "stays exactly the `test_v0_1` seed".
- TRD 13:554 says the scenarios that change data are E2E-15, TST-187 and E2E-19, and only those are tagged `@isolated`.

What the scenarios actually do on the main database:
- E2E-09 (13:370) saves a review on the R09 alarm, and the alert becomes `acknowledged`.
- E2E-18 (13:378) saves a review on R09, and the nav becomes "Alerts (1)".

What other main-run scenarios assert on the same database:
- E2E-01 (13:362): nav "Alerts (2)".
- E2E-17 (13:377): R09 "Not reviewed" and nav "Alerts (2)".
- E2E-20 (13:380): the TRD 14 Table 4.9-E tile "Alarms raised 2 · R09, R10 · both not yet reviewed" (14:584).
- CIC-032 (16:391): "Alerts (2)" and R09 "Not reviewed".
- E2E-09 and E2E-18 also each assume R09 has not been reviewed yet.

How the runs are set up:
- The nightly run executes `--project=chromium --project=firefox --project=webkit` in one invocation against one database (TRD 16:362). TST-100 requires all three browsers to pass.
- No ordering, serial or worker rule exists for the main run (`playwright.config.ts` is not specified beyond TST-004).

Impact:
- Nightly: once one browser has saved its R09 review, E2E-01, E2E-17, E2E-20, E2E-09 and E2E-18 fail in the other two browsers. This happens on every nightly run.
- On pull requests (Chromium only), the result depends on which worker runs first. TST-101 retries do not help, because the state persists between attempts.
- The invariant that round 4 introduced (R4-05) is therefore false as written.

Recommendation:
- Tag E2E-09 and E2E-18 as `@isolated` too, or give each browser project its own freshly seeded database. Alternatively, make the main run serial with the read-only scenarios first, and run the review scenarios in one browser only.
- State the chosen option in CIC-030, TRD 13 §8 and TST-100.

### 4.2 Minor

| ID | Location (A vs B) | Description and evidence | Recommendation |
|---|---|---|---|
| R5-03 | E2E-19 (TRD 13:379) vs TDV-061 (14:542), TRD 13:549, `e2e.yml` (16:362–376) | E2E-19 expects the "Not reviewed" emphasis to return "after advancing the server clock 24 h (isolated database only)". However, TDV-061 says the as-of is set "without any clock override in the running services". TRD 13:549 limits `page.clock` to client-side formatting. Neither `e2e.yml` nor Compose provides any server-clock mechanism. `snoozed_until` is `now() + 24 h` (API-132, CUS-039, DME-022), and "now" is real wall-clock time. | Define the mechanism. One option is to compare the emphasis on the client (FR-261 order on the client) and allow `page.clock` for it. Another is a test-only clock in the backend, allowed only when APP_ENV ∈ {local, test}. |
| R5-04 | TST-187 (TRD 13:512) vs ANL-043/ANL-015 (07:364, 07:250), `.env.development.example` `PIPELINE_AS_OF=2026-10-30T15:00:00-05:00` (TRD 21:166) | TST-187 posts "one further valid record for R11 with a new session ID" but gives no timestamp. Because the E2E stack runs with PIPELINE_AS_OF = Oct 30 15:00 CT, ingest-triggered runs exclude every record after 20:00:00Z (ANL-015, `after_as_of`). E2E-15 already holds 19:59:00Z. Only 19:59:01–20:00:00Z, on the same day (ASM-02), makes "Last check-in" change. The natural choice `R11-20261031-01` fails the 5 s test. | Give the record explicitly, for example `R11-20261030-02` at `2026-10-30 19:59:30`. |
| R5-05 | TST-100 (13:355), TRD 13 §4.10 preamble (13:350), TST-004 (13:87) vs `e2e.yml` (16:375), CIC-030 | **Residue of R4-05.** TST-100 says every scenario passes in Firefox and WebKit nightly. The `@isolated` run uses `--project=chromium` always, so E2E-15, E2E-19 and TST-187 never run in Firefox or WebKit. The §4.10 preamble says "All E2E scenarios run on the … stack loaded with dataset DS-07", but the `@isolated` scenarios run on `echowell_demo`, seeded `--master-only` plus the overlay. TST-004 says E2E runs against "frontend :3000", whereas `e2e.yml` and CIC-030 use `frontend-prod` on :3001. | Scope TST-100 and the preamble to the main run and name the `@isolated` exception. Change TST-004 to :3001 / `frontend-prod`. |
| R5-06 | TRD 20 §8 (20:1198–1201) and DEP-035 (15:242) vs PGS-002 (20:59), TRD 20 §4.2, D-72 (24:235) | **Residue of R4-02.** TRD 20 §8 still says migration 0001 contains "sections 4.2–4.8 except role creation", which now includes the provisioning `CREATE EXTENSION` fence. It also says the "Downgrade of 0001 drops everything in reverse order". Re-tested as the migrator: `CREATE EXTENSION` without the extensions present gives "permission denied to create extension", and `DROP EXTENSION` gives "must be owner of extension btree_gist". Either would break CI and the D-71 reset. Separately, DEP-035 says a switch to Railway PostgreSQL needs "only" new URLs plus `pg_dump`/`pg_restore`. It omits the D-72 provisioning step (extensions, roles, schema owner), and D-72 lists only local/CI, Neon and RDS. | In §8, say 0001 contains the §4.2 check block only, and that its downgrade never drops extensions. Add "run the provisioning step first" to DEP-035 and list Railway PostgreSQL in D-72. |
| R5-07 | PGS-001 (TRD 20:58) vs provisioning lists (TRD 15:146–151, 15:230; TRD 20 §4.2–§4.3; D-72) | PGS-001 requires `ALTER DATABASE <db> SET timezone = 'UTC'` and tests `SHOW timezone` = `UTC`. No provisioning step runs it, and the migrator cannot. Re-tested: `ERROR: must be owner of database`. Without the step, the `postgres:16-alpine` default is `Etc/UTC`, so the test as written fails. An implementer who puts the statement in migration 0001 repeats the R4-02 failure. | Add the statement to the provisioning step (script, Neon step 4, RDS step), or relax the test to accept `Etc/UTC`. |
| R5-08 | TRD 20 §4.5 `reject_mutation()` comment (20:231–232) vs PGS-019 (20:76), D-71, DB-024, TRD 15 `reset-test-db` row | **Residue of R3-01/R4-03.** The SQL comment says the purge escape hatch is "used only by the documented test-database reset and IRB withdrawal purge procedures". PGS-019 now says the test reset does not use it. The comment is part of the DDL that the migration copies verbatim. | Change it to "used only by the IRB withdrawal purge (PGS-019)". |
| R5-09 | TRD 24:16 ("D-01 to D-71", "D-56 to D-71"), 24:263 ("next free D number (D-72 onward)"), AGT-002 (25:94, "decision D-01..D-71") vs D-72 (24:235) | The round-4 fix added D-72, and the fix log says "Next free decision: D-73", but the register's scope line, its numbering rule and AGT-002's binding range still end at D-71. AGT-002 is the rule that makes decisions binding on build agents. Also, D-72's TRD column ("06, 15, 16, 20") omits TRD 13 (TST-040). | Update all three to D-72 / D-73, and add 13 to D-72. |
| R5-10 | TRD 05:529 (`create-api-key --name --scope ingest:write\|pipeline:run`), SEC-020 (12:110, `--scope` mandatory) vs TRD 15 `create-api-key` row (15:383, `[--scope S]…`, default `ingest:write`), SEC-022 | **Residue of R4-06.** TRD 05 still shows a single-valued `--scope`. SEC-020 makes `--scope` mandatory, while TRD 15 makes it optional with a default. | Make TRD 05:529 the repeatable form. Choose mandatory or optional-with-default in one place and reference it. |
| R5-11 | DB-057 (06:593, "the only exception is … `local-dev-only` … in `.env.development.example`"), SEC-050 (12:191), CIC-115 (16:397, the gitleaks allow-list is only the `local-dev-only` values), DEP-018 (15:132) vs Compose (15:165–170), `ci.yml` (16:188, 16:195–201), `.env.development.example` (21:157–159) | **Residue of R4-07.** Some committed credentials are not covered by the stated "only exception": `POSTGRES_PASSWORD: echowell`, the login-role passwords `migrator-local`/`app-local`/`readonly-local` (Compose and the template URLs), and `migrator-ci`/`app-ci`/`readonly-ci` plus `PGPASSWORD: echowell` (`ci.yml`). SEC-050 lists "database role passwords" among the secrets. DEP-018 also says the Postgres password `echowell` is "present in `.env.development.example`", but the template has no `POSTGRES_*` line. | Widen the exception to local/CI-only database passwords in `docker-compose.yml`, `ci.yml` and the template (and the gitleaks allow-list), or rename them to `local-dev-only-…`. Fix the DEP-018 example. |

---

## 5. Cross-Reference Validation

| Check | Method | Result | Findings |
|---|---|---|---|
| Duplicate requirement IDs | Script over the first cell of every table row and over list-item AC IDs (2,002 requirement IDs) | None. E-01..E-32 appear twice in TRD 19 by design (detail and summary). | — |
| Dangling requirement IDs | Script: defined IDs compared with every reference | None. E2E-01..E2E-21 are defined as the first cell of Table 4.10-A, with the name after the ID (13:362–382). AC-DB-02a is a list item. | — |
| OQ / ASM / RSK / DSC / D vs TRD 24 | `grep -rhoE "(OQ\|ASM\|RSK\|DSC\|D)-[0-9]{2}"` plus a definition check in TRD 24 | 8 ASM, 14 DSC, 26 OQ, 15 RSK and 72 D (D-01..D-72) used, all defined. `OQ-27` and `RSK-16` appear only in "next free" text. The stated D ranges are stale. | R5-09 |
| E-, S-, UC-, AC- IDs | Script | E-01..E-32, S-01..S-13, UC-01..UC-15 and 282 AC IDs are defined | — |
| Endpoints vs TRD 19 | Script: every `METHOD /path` compared with E-01..E-32 | All match. The only non-matches are known: `/alerts/{id}/acknowledge` and `/audio` (in "shall not exist" text), `/openapi.json` and `/docs` (API-113), `PATCH /users` (= `/users/{id}`), the `/ingest]` Mermaid label and `/alerts/{R09 alert id}` (an AC-API-15 placeholder). | — |
| Tables/columns vs TRD 20 DDL | Script: 24 `CREATE TABLE` blocks compared with every `table.column` token | All match. The only non-matches are `alerts.spec` (a file name) and `config_parameters.facility_tz` (config-key notation). | — |
| DDL executes (D-71/D-72 re-test) | PostgreSQL 16 scratch cluster, script `/tmp/claude-0/-home-user-echowell/06d21bae-4975-509b-846a-5a1512c441c2/scratchpad/t_r5.sh`, using the 33 `sql` fences of TRD 20 split exactly as the text says: fence 0 is provisioning; the §4.2 check block and §4.4–§4.8 are 0001; §4.11 is 0002 | (0) A database with roles but no extensions, migrated as `echowell_migrator_login` with `SET ROLE`, failed with the 0001 message (exit 3). (1) Provisioning as superuser (extensions, group roles, schema owner, login roles): exit 0. (2) 0001 + 0002 as the migrator: exit 0, with 24 tables, 17 triggers, 15 enums and 46 config rows; all tables are owned by `echowell_migrator`; the extensions are owned by the superuser. (3) Drop-all (downgrade base) as the migrator: exit 0, 0 tables, extensions kept. (4) Re-migrate: exit 0, 24/17/15/46; `seed.reset` audit insert OK; `Auth.Login` rejected by `audit_logs_action_ck`. (5) `echowell_app_login`: SELECT on `evaluation_ground_truth`, `SET ROLE echowell_readonly`, `DELETE FROM alerts`, `UPDATE raw_sessions` and `DELETE FROM audit_logs` were all denied; INSERT into `facilities` using the `gen_random_uuid()` default works. `echowell_readonly_login`: `password_hash` denied, `email` and `evaluation_ground_truth` readable. Owner DELETE on `audit_logs` without the purge setting → EW001; with it → allowed. (6) A second database in the same cluster (the `echowell_demo` pattern): provisioning re-run idempotently and migration succeeded. Variants: the migrator running the §4.2 `CREATE EXTENSION` fence without the extensions present → permission denied; the migrator running `DROP EXTENSION` → "must be owner"; the migrator running `ALTER DATABASE … SET timezone` → "must be owner". | R5-06, R5-07 |
| Env vars vs TRD 21 | Script: 45 defined names compared with env-style tokens | All defined. The non-matches are the same known ones as in round 4: error codes, report names, `BACKEND_URL`/`FRONTEND_URL` (workflow-local), GitHub variables (21:133), `RAILWAY_GIT_COMMIT_SHA`, `NIGHTLY_SCHEDULER_ENABLED` (in "shall not exist" text). | — |
| Error codes vs TRD 05 | Script (36 codes) | All in the catalogue | — |
| Audit actions vs TRD 12 §4.12 | Script (24 actions) | All in the vocabulary | — |
| CLI command names | `backend.cli <cmd>` and backticked command names compared with the TRD 15 §4.8 table (14 commands) | Every command used is in the table. The scope syntax of `create-api-key` differs across TRDs. | R5-10 |
| Migrator-credential users | Every statement of who may read DATABASE_MIGRATION_URL | ARC-019, TRD 05:481, TRD 06:660, TRD 12:320, SEC-111, TRD 15:230, DEP-040 and TRD 21:81 all point to the TRD 20 §4.3 closed list (Alembic, seed, reset-test-db, purge-resident, rebuild, set-config and the loader) | — |
| CI workflows / jobs | `*.yml` names; TRD 16 job names compared with CIC-070 | The five workflows of CIC-002 (`ci.yml`, `e2e.yml`, `deploy-staging.yml`, `deploy-production.yml`, `uptime.yml`) are used consistently. The jobs `repo-hygiene`, `backend-lint`, `backend-test`, `openapi-contract`, `frontend`, `security-audit`, `docker-build` and `playwright` match CIC-070. The `performance` and `lighthouse` jobs are named consistently. The `e2e.yml` isolated step matches the Compose outline: database `echowell`, initdb mount `/docker-entrypoint-initdb.d/10_provision_login_roles.sql`, db-container password variables, `*-local` URLs, `--service-ports` on 127.0.0.1:8000, client-side API calls (FE-040). | R5-02, R5-05 |
| File paths | Script: backticked paths grouped by file name | Consistent. `tests/fixtures/ds07/` in TRD 04:633 is relative to `frontend/`, and `tests/e2e/a11y.spec.ts` in TRD 04 is the same as `frontend/tests/e2e/a11y.spec.ts`. | — |
| Golden fixtures | pandas with `python3 -I` | Section 6.3 | — |
| Code fences / placeholders | Script / grep | Fence counts are even in all 26 files. The placeholder grep hits only GIT-053. | — |
| Document structure / versions | Script | 11 TRDs at 0.5, each with a round-4 revision row naming the R4 IDs it fixed, matching the fix log. 6 at 0.4, 6 at 0.3, 3 at 0.2. | — |

---

## 6. The five checks in detail

### 6.1 Database requirements support all APIs: **PASS**

- Every endpoint E-01..E-32 reads and writes only tables and columns of the TRD 20 DDL.
- The `echowell_app` grants cover every API write, and the denials of PGS-021 and PGS-040 hold. This was executed (section 5).
- The extension and role model of D-72 now executes end to end as the migrator. A second database in the same cluster can be provisioned idempotently, which is the pattern `e2e.yml` uses for `echowell_demo`.
- Minor:
  - R5-07: no one owns `ALTER DATABASE … SET timezone`.
  - R5-08: a stale comment about the purge path.

### 6.2 APIs support all frontend requirements: **PASS**

- All 32 endpoints are in the TRD 19 summary and YAML.
- Every TRD 04 client function resolves to an endpoint.
- `GET /config/ui` provides the snooze hours and the review explanations.
- No frontend item lacks an API source.
- R5-01 (seeded `.test` logins) is an API validation versus test-data conflict and is counted under 6.4 and 6.5.

### 6.3 Analytics requirements support all business requirements: **PASS**

SRC-03 was read again with `python3 -I` and pandas. Every value matches the TRDs.

| Quantity | Value |
|---|---|
| Annotated_sessions `expected_status` (302 rows) | usable 267, missing_resident 17, set_aside 12, missing_device_gap 2, duplicate 2, quarantined 2 (missed tile 19; funnel 300 → 281 → 269 → 267) |
| SRC-05 input | 283 rows, 2 duplicate `session_id`s, 30 columns |
| Exp_baselines | 180 rows; floor applied only to `number_of_pauses` (8 residents) |
| Exp_scores | 98 rows: R01 14, R02 8, R03 6, R04 14, R05 12, R06 14, R07 2, R09 14, R10 14 |
| Alarm states | off 81, on 15, RINGS (first crossing) 2. Final tallies R09 26.83 and R10 13.42, as in Alerts.dc.html, E2E-17 and CIC-032. |
| Parameters | facility_tz America/Chicago, noise −40, minimum speech 1 s, duplicate rule as TRD 20 §4.11 |

No findings.

### 6.4 Testing requirements validate all critical functionality: **FAIL**

- Every BR has TST, TDV or MVP coverage.
- R4-05 fixed the overlay step: a separate `echowell_demo` database, provisioned the same way. Its mechanics were checked against Compose and are sound.
- TST-040 and CIC-015 now pass as specified (section 5).
- Fails on:
  - R5-01: every seeded login is rejected with standard `format: email` validation.
  - R5-02: E2E-09 and E2E-18 change the shared main database that E2E-01, E2E-17, E2E-20 and CIC-032 assert unchanged. The nightly 3-browser run fails every time.
- Minor:
  - R5-03: no server-clock mechanism for E2E-19.
  - R5-04: the TST-187 timestamp is not specified.
  - R5-05: TST-100, the §4.10 preamble and TST-004 do not match the isolated run.

### 6.5 Deployment requirements support the architecture: **FAIL**

- The architecture still follows `Deployment_Architecture.md`: a monorepo; Next.js on Netlify; FastAPI on Railway; Neon (Railway PostgreSQL as the alternative); GitHub Actions; and the AWS target (Amplify, App Runner, RDS).
- R4-01 is resolved. DB-029, DEP-060, D-71 and the TRD 15 `reset-test-db` row now state the same single staging exception. DEP-086 still bans downgrade in production. `STAGING_DATABASE_URL` is the direct migrator URL, consistent with DEP-032 and TRD 20 §8.
- D-72 provisioning is stated consistently for local/CI (TRD 15 §4.2, CIC-015, `ci.yml`, `e2e.yml`), Neon (TRD 15 §4.4 step 4) and RDS (DEP-117).
- Fails on R5-01: the staging smoke step logs in as `researcher@echowell.test` (DEP-080(c), CIC-042), and the local quick start logs in as `admin@echowell.test`.
- Minor:
  - R5-06: D-72 is not carried into TRD 20 §8 or into the DEP-035 Railway PostgreSQL switch.
  - R5-09: the decision ranges are stale.
  - R5-10: the API-key scope syntax differs between TRDs.
  - R5-11: committed local/CI database passwords are outside the stated "only exception".

---

## 7. Recommended fixes (not applied)

In priority order:

1. **R5-01:** choose between a seeded domain that email-validator accepts (for example `@example.com`, across DB-057, D-71, TRD 20 §4.12, TRD 21:85/131/132, TRD 13:358 and TRD 15:142–143) and a non-production validator rule in TRD 05/12. Add a login test for each seeded user.
2. **R5-02:** isolate the review-writing scenarios (E2E-09, E2E-18) or give each browser project its own seeded database. Define the main-run ordering in CIC-030, TRD 13 §8 and TST-100.
3. **R5-03 and R5-04:** define how E2E-19 makes the snooze expire. Give TST-187 an explicit record (for example `R11-20261030-02` at `2026-10-30 19:59:30`).
4. **R5-06 and R5-07:**
   - TRD 20 §8: 0001 contains only the §4.2 check block, and its downgrade never drops extensions.
   - DEP-035: run provisioning first, and add Railway PostgreSQL to D-72.
   - Add `ALTER DATABASE … SET timezone = 'UTC'` to the provisioning step, or relax PGS-001.
5. **R5-05, R5-08..R5-11:**
   - Scope TST-100 and the TRD 13 §4.10 preamble; change TST-004 to :3001.
   - Fix the `reject_mutation()` comment.
   - Update TRD 24:16, 24:263 and AGT-002 to D-72; add TRD 13 to D-72.
   - Align the `create-api-key` syntax in TRD 05, TRD 12 and TRD 15.
   - Extend the DB-057/SEC-050/CIC-115 exception to local/CI database passwords, and fix the DEP-018 example.

---

## 8. Prior findings status

### 8.1 Round-4 findings (R4-01..R4-09)

| ID | Round-4 severity | Subject | Status | Evidence (round 5) |
|---|---|---|---|---|
| R4-01 | Major | Staging reset vs DB-029/DEP-060 | **Resolved** | DB-029 (06:475) and DEP-060 (15:368) state the single D-71 staging exception: only from the deploy-staging re-seed step, only with `test_v0_1`, never in production. D-71 (24:234), the TRD 15 `reset-test-db` row (15:392), DB-024 (06:465) and DEP-071 (15:399) agree. DEP-086 is unchanged. No other TRD forbids the staging downgrade. |
| R4-02 | Major | Migration 0001 cannot create extensions | **Partially resolved** | D-72, PGS-002, TRD 20 §4.2/§4.3, TRD 15 §4.2 and step 4, DEP-117, CIC-015, `ci.yml`, `e2e.yml` and TST-040 are consistent. Re-executed on PostgreSQL 16 as the migrator (section 5): every step exit 0, 24/17/15/46, grants correct. Residue: TRD 20 §8 still puts §4.2 in 0001 and says the downgrade "drops everything in reverse order", and DEP-035 omits provisioning (R5-06). |
| R4-03 | Minor | Stale `--reset` truncate clause, TRD 20:1192, TRD 25:197 | **Partially resolved** | TRD 15:387 ("`--reset`: see `reset-test-db`"), TRD 20:1212–1214 and TRD 25:197 are fixed. Residue: the `reject_mutation()` comment (20:231–232) still names the test-database reset as a user of the purge path (R5-08). |
| R4-04 | Minor | DB-024 test oracle | **Resolved** | The DB-024 verification expects `config_parameters` 46, `audit_logs` exactly 1 (`seed.reset`), and every other table empty. This matches DEP-071 and D-71, and the PostgreSQL re-test confirmed that the `seed.reset` insert works after re-migration. |
| R4-05 | Minor | Overlay step and E2E isolation | **Partially resolved** | `e2e.yml` has the `echowell_demo` step with provisioning, migration, `--master-only` and the overlay. The `@isolated` tags, CIC-030, E2E-15, E2E-19, TST-187 and TRD 13 §8 are updated, and the Compose mechanics check out. Residue: E2E-09/E2E-18 still change the main database (R5-02); E2E-19 has no clock mechanism (R5-03); the TST-187 timestamp is not specified (R5-04); TST-100, the §4.10 preamble and TST-004 are not updated (R5-05). |
| R4-06 | Minor | API-key scope cardinality | **Partially resolved** | SEC-022 (non-empty subset), SEC-020 (repeatable `--scope`) and TRD 15:383 are fixed. Residue: TRD 05:529 still shows a single-valued `--scope`, and SEC-020 (mandatory) differs from TRD 15 (optional, default `ingest:write`) (R5-10). |
| R4-07 | Minor | Committed local seed credentials | **Partially resolved** | The SEED_* placeholders are `local-dev-only-…`. ENV-041, DB-057, SEC-050 and the CIC-115 allow-list are added. Residue: the committed local/CI database passwords (Compose, `ci.yml`, template URLs) are outside the stated "only exception", and DEP-018 cites a template line that does not exist (R5-11). |
| R4-08 | Minor | Migrator "Alembic only" texts | **Resolved** | ARC-019 (01:110), TRD 05:481, TRD 06:660, TRD 15:230 and TRD 21:81 all reference the TRD 20 §4.3 closed list. No narrower list remains anywhere (grep for "Alembic only", "only by Alembic" and "used only by"). |
| R4-09 | Minor | "4 group roles" | **Resolved** | TRD 20:22 reads "3 group roles", and the extensions are "created by provisioning, checked by migration 0001, D-72". |

Totals: Resolved 4, Partially resolved 5, Not resolved 0. Spot checks of the round-1 to round-3 resolutions (D-56..D-71 topics, the closed migrator list, the audit vocabulary, the as-of precedence, CORS/CSP and the nightly variables) found no regression.
