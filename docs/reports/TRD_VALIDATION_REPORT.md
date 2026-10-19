# TRD Validation Report (Phase 1, round 6)

| Field | Value |
|---|---|
| Scope | `specs/TRD/00`–`25`, checked against `specs/prompts/TRD_Generation_Prompt.md`, `specs/architecture/Deployment_Architecture.md`, `specs/UI-wireframe/*.dc.html` (5 files), `specs/business-requirements/*`, `specs/data-samples/*` |
| Checklist | `specs/prompts/TRD_Implementation_Audit_Checklist.md` Phase 1, and the definition of done in TRD 25 §Phase 1 |
| Round | 6. This report replaces round 5 (11 findings, R5-01..R5-11). It was written after the round-5 fixes in `docs/reports/TRD_VALIDATION_FIXES.md` were applied. |
| Branch | `trd-generation`. This run was read only: no file under `specs/` was changed and no git command was run. |
| Date | 2026-10-19 |

**How locations are written.** `TRD NN:line` means line `line` of `specs/TRD/NN_*.md`.

**Severity scale** (the same as rounds 1–5):

| Severity | Meaning |
|---|---|
| Critical | Built as written, the system would be wrong or unsafe. |
| Major | An implementer following the TRDs would very likely build something that fails its own required tests or the sources. |
| Minor | A real inconsistency or error that a careful implementer would still resolve without harm. |

**Numbering.** New findings in this round are R6-01, R6-02 and so on. Earlier findings keep their numbers (section 8).

---

## 1. Summary

**Verdict: FAIL.** The rule is FAIL if any Critical or Major finding remains. One Major finding remains.

- **R6-01 (Major): the E2E suite exceeds the login rate limit that its own stack enforces.**
  - `POST /auth/login` is limited to RATE_LIMIT_LOGIN per client IP, default `5/minute`, using slowapi in-memory storage (API-102 at TRD 05:347, SEC-091 at 12:264, TRD 21:72).
  - `e2e.yml` copies `.env.development.example` unchanged (TRD 16:348), and that file sets `RATE_LIMIT_LOGIN=5/minute` (TRD 21:175). No step overrides it.
  - Every E2E scenario logs in as a seeded user (the TRD 13 §4.10 preamble and Table 4.10-A). E2E-14 and E2E-21 log in twice, and the TRD 04 spec files FE-185..FE-192 log in as well. Every browser request reaches the backend from the same Docker gateway address, so the backend sees one client IP (API-103).
  - Result: from the 6th login within a minute, the backend returns 429 `RATE_LIMITED`. The run as specified needs well over 20 logins per browser project in a few minutes. The required `playwright` check (CIC-031, CIC-070) therefore fails on every run. No TRD says to reuse a login (`storageState`) or to raise the limit for the E2E stack.
  - The in-process pytest suites have the same problem. The `TestClient` always reports the same client host, so login-based integration tests (Table 4.13-A, TST-131, TST-188) share one limiter unless it is reset between tests.

The round-5 fixes held:
- **The seeded addresses now pass validation.** They are `@example.com` everywhere (14 occurrences in 9 TRDs, none with `.test`). Re-tested with pydantic 2.9.2 and email-validator 2.2.0: `EmailStr` emits `format: email`, accepts all three seeded addresses and rejects `admin@echowell.test`.
- **D-73 isolates the main E2E database.** `global-setup.ts` resets and re-seeds the database before each Playwright invocation. Read-only scenarios run first, then the `@mutating` group, and the `@isolated` run uses `echowell_demo`. The design is sound, apart from R6-02 and R6-03.
- **The D-72 provisioning step works**, including the time zone. It was re-executed from scratch on PostgreSQL 16 (section 5):
  - Provisioning on a database preset to America/Chicago, then migrations 0001 and 0002 as the migrator: exit 0.
  - The migrated database has 24 tables, 17 triggers, 15 enums and 46 config rows.
  - `SHOW timezone` returns `UTC`, the extensions are kept across downgrade base, and all permission checks pass.
- **Prior findings.** 9 of the 11 round-5 findings are fully resolved. R5-02 and R5-03 are partially resolved, with residue in R6-03 and R6-05.

| Severity | Count |
|---|---|
| Critical | 0 |
| Major | 1 |
| Minor | 7 |
| **Total new (round 6)** | **8** |

Prior findings:

| Set | Resolved | Partially resolved | Not resolved |
|---|---|---|---|
| R5-01..R5-11 (11) | 9 (R5-01, R5-04..R5-11) | 2 (R5-02, R5-03) | 0 |

Phase 1 checks:

| # | Phase 1 check | Result | Key evidence |
|---|---|---|---|
| 1 | Database requirements support all APIs | **PASS** | All 24 tables, 15 enums, CHECK constraints and grants support E-01..E-32. The DDL was re-executed as the migrator on a freshly provisioned database (exit 0), and every TRD 20 §7 permission and trigger check that was sampled behaved as specified. PGS-001 (`timezone` = UTC) now holds. Minor: R6-06 (PGS-016 names a CI job that does not exist). |
| 2 | APIs support all frontend requirements | **PASS** | All 32 endpoints are in TRD 19. Every `/api/v1` path used in the TRDs resolves. TRD 11 and TRD 19 have not changed since round 2; TRD 04 changed only in its E2E row. |
| 3 | Analytics requirements support all business requirements | **PASS** | The workbook and SRC-05 were re-verified with `python3 -I` and pandas (section 6.3). Every figure matches. |
| 4 | Testing requirements validate all critical functionality | **FAIL** | R6-01 (login rate limit versus E2E logins). Minor: R6-02 (reset under a live connection pool), R6-03 (FE-187 is outside the `@mutating` group), R6-04 (TST-005 versus E2E ordering and wall clock), R6-05 (the snooze-expiry assertion has no observable state), R6-07 (nightly random-order and robustness jobs are missing). |
| 5 | Deployment requirements support the architecture | **PASS** | The interim stack (Netlify, Railway, Neon, with Railway PostgreSQL as the alternative) and the AWS target match `Deployment_Architecture.md`. D-72 provisioning, including the time zone, is consistent for local/CI, Neon, Railway PostgreSQL and RDS. The staging smoke login uses `researcher@example.com`. Minor: R6-08 (decision-log and revision bookkeeping). |

TRD 25 §Phase 1 definition of done:

| Criterion | Result | Evidence |
|---|---|---|
| Every BR-01..BR-18 maps to at least one TRD requirement and test | **Met** | Section 2.1. Each BR is cited by 25–270 requirement rows across 10–24 TRDs. |
| Every OQ/ASM/RSK/DSC/D ID used exists in TRD 24 | **Met** | ASM-01..08, DSC-01..14, OQ-01..26, RSK-01..15 and D-01..D-73 are all defined. `OQ-27` and `RSK-16` appear only in the "next free" rule (TRD 24:264). The scope line and AGT-002 no longer give a closed D range. |
| Each of the five checks has a pass/fail line | **Met** | The table above and section 6 |
| No TRD file modified | **Met** | This run was read only |
| `grep -rnE "T[B]D\|T[O]DO\|l[o]rem" specs/TRD` returns nothing | **Met in substance** | The only hit is GIT-053 (TRD 18:219), the rule that forbids these words. The same hit was accepted in rounds 1–5. |

---

## 2. Requirements Traceability Matrix

### 2.1 Business requirements → TRD requirements → tests

The counts below come from a script (`br3.py`). A table row counts when its first cell is a requirement ID and the row cites the BR, directly or within a range. The restatement tables (BR, SRC, OQ, ASM, RSK, DSC) are excluded. The only change from round 5 is BR-16, which rose from 269 to 270 rows with the new TST-188.

| BR | Summary (TRD 00) | Rows / TRDs | Key FRs (TRD 02) | Tests / MVP criteria | Gap (round 6) |
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
| BR-11 | CUSUM persistent-deviation flag | 61 / 14 | FR-100–FR-110, FR-261–FR-265 | TST-020, TST-065, TDV-059, TDV-060, TDV-067, MVP-01, MVP-13 | Snooze expiry not observable: R6-05 |
| BR-12 | Residents overview | 92 / 17 | FR-130–FR-140, FR-150–FR-156 | TST-033, TST-090, TST-110, TST-181, TST-187, TDV-062, TDV-066, MVP-04 | E2E logins: R6-01 |
| BR-13 | Resident detail page | 113 / 15 | FR-160–FR-173, FR-260–FR-280 | TST-090, TST-093, TST-110, TST-181, TST-187, TDV-066, MVP-05, MVP-13 | R6-01, R6-03 (FE-187) |
| BR-14 | New-admission arm (Should) | 32 / 10 | FR-200–FR-207 | TST-090, TST-185, TST-186, MVP-06 | — |
| BR-15 | Reproduce workbook R01–R10 | 166 / 22 | FR-240–FR-245, FR-310–FR-323 | 41 TST/TDV/MVP rows | Nightly robustness has no job: R6-07 |
| BR-16 | Data protection, roles, audit | 270 / 24 | FR-210–FR-221, FR-250–FR-254 | TST-007, TST-032, TST-041, TST-053, TST-130, TST-188, TDV-006, TDV-007, MVP-07 | Rate limit versus test logins: R6-01 |
| BR-17 | Monorepo deploy on Netlify/Railway/Neon/GHA | 74 / 15 | FR-253, FR-254 | TST-001, TST-150, TST-170, MVP-08 | R6-06 (job name) |
| BR-18 | Detection not diagnosis, no LLM/ML | 47 / 15 | FR-164, FR-277, FR-278, FR-298 | TST-096, TST-097, TST-170, MVP-09 | — |

### 2.2 Frontend requirements (TRD_Generation_Prompt) → UX / FE IDs

Every item in the prompt's "Frontend Requirements" list (prompt line 93 onwards) was traced again. TRD 11 and TRD 19 have not changed since round 2. TRD 04 changed only in its E2E row.

| Prompt frontend item | UX IDs | FE components (TRD 04 §4.8) | Tests | Round-6 note |
|---|---|---|---|---|
| Three primary views plus Alerts and Analytics | D-23; TRD 11 §4.3, §4.5, §4.7, §4.17, §4.18 | Residents page, Resident detail page, AdmissionsTable, AlertsPage, AnalyticsPage | E2E-03..E2E-21, TST-110 | Logins rate-limited: R6-01 |
| All enrolled residents; sort by alarm, resident ID, last check-in | UX-020–UX-033, UX-261 | ResidentsTable, SortSelect | E2E-04, E2E-05, E2E-06 | — |
| Statuses Alarm On / No Alarm / Baseline Still Forming | §4.3.4, UX-036 | StatusBadge | E2E-04 | — |
| 30-day used, set aside, quarantined, missed; no backfill | UX-039, UX-047, UX-048 | ResidentsTable, SummaryTiles | E2E-03, E2E-04 | — |
| Device panel | UX-050–UX-058, UX-263 | DevicePanel, DeviceCell | E2E-07 | — |
| CUSUM tally, alarm line 5.0, baseline period | UX-080–UX-092 | CusumChart, CusumTable | TST-093, E2E-08 | — |
| 7 scored measurements; 12 others stored, not scored | UX-100–UX-108 | FeatureCard ×7, OtherMeasurementsCard | E2E-08, TST-090 | — |
| Baseline status, progress, freeze | UX-060–UX-066 | ResidentHeader, WhatThisMeans | E2E-08, E2E-10, E2E-11 | — |
| Check-in log | UX-140–UX-149 | CheckinLog | E2E-10..E2E-12, E2E-15 | — |
| Staff notes | UX-120–UX-135 | StaffReviewForm, NotesList, ReviewDialog | E2E-09, FE-187 | FE-187 is not in the `@mutating` group: R6-03 |
| New admissions, "future/experimental" | UX-181–UX-195 | AdmissionsTable, FacilityRangeChart, ExperimentalBanner | E2E-13, TST-185, TST-186 | — |
| Alert review (SRC-18) | UX-300–UX-331 | AlertQueue, AlertCard, AlertReviewForm | E2E-17, E2E-18, E2E-19, TST-065 | R6-05 |
| Analytics (SRC-19) | UX-351–UX-384 | KpiTiles, LossFunnel, AlarmTimingTable, … | E2E-20, E2E-21, TDV-074 | — |
| Loading, empty and error states; accessibility; responsive | UX state rows, FE-145, NFR-060 | SectionState | TST-090, TST-110, E2E-16 | — |

Result: every prompt item maps to UX IDs, FE IDs and at least one test, and every frontend item has an API source.

### 2.3 Wireframes → UX sections

The key strings were checked again with grep. All five wireframes are fully covered, with the same result as round 5.

| Wireframe | UX section | Key strings checked |
|---|---|---|
| `Main.dc.html` | TRD 11 §4.3, §4.4, §4.13 | "shared by R02", "silent all day" |
| `Resident.dc.html` | TRD 11 §4.5 | "Baseline complete", "alarm line 5.0" |
| `Admission.dc.html` | TRD 11 §4.7 | "Not in pipeline test v0.1" |
| `Alerts.dc.html` | TRD 11 §4.17 | "open 9 days", "tally 26.8", "13.4", "Alerts (2)", "Remind me in" |
| `Analytics.dc.html` | TRD 11 §4.18 | "281", "267", "Alerts (2)" |

### 2.4 Items with no test or only a weak test

| Item | Status |
|---|---|
| Every E2E login (main run) | The 6th login per minute is refused with 429 (R6-01) |
| UI "Not reviewed" emphasis returning after a snooze expires (UX-303, FR-261) | Not tested at the UI level. The TST-065 assertion has no observable API state (R6-05). |
| Random-order pytest run (TST-005 verification); multi-seed and false-alarm robustness (TST-084, TDV-080..TDV-083) | No workflow or job runs them (R6-07) |

---

## 3. Missing Requirements

| ID | Severity | Where it is needed | What is missing |
|---|---|---|---|
| R6-01 | Major | TRD 13 §4.10 / §8, TRD 16 `e2e.yml` (16:348–368), TRD 21 RATE_LIMIT_LOGIN (21:72, 21:175), TRD 13 §4.2 conftest | Either a login-rate-limit value for the E2E stack and the in-process test app, or a rule that Playwright reuses one login per role (`storageState`) and that pytest resets the limiter between tests. Neither is stated. |
| R6-02 | Minor | API-125 (TRD 05:377), D-73, TRD 13 §8 | What happens to the running backend's connections when `global-setup.ts` drops and recreates the schema. Either disable server-side prepared statements in every environment, or dispose the pool or restart the backend after the reset. |
| R6-07 | Minor | TRD 16 §4.3 (e2e.yml jobs `playwright`, `performance`, `lighthouse`) | A scheduled job that runs the random-order pytest run (TST-005 verification "pytest -p randomly run in nightly", TST-151) and `tests/validation/robustness.py` (TST-084, TDV-080..TDV-083, which says "nightly and on manual dispatch") |

---

## 4. Contradictions

### 4.1 Major

**R6-01 · Major · The E2E main run needs far more logins than the 5-per-minute limit of its own stack**

What the TRDs require:
- **Rate limit.** API-102 (TRD 05:347): "slowapi with in-memory storage: `POST /auth/login` limited to RATE_LIMIT_LOGIN per client IP (default 5/minute)".
  - SEC-091 (12:264) repeats the limit.
  - SEC-093 returns 429 `RATE_LIMITED`.
  - TST-131 (13:415) asserts that the 6th login attempt within 60 s returns 429.
  - API-103: locally the client IP is the socket peer.
- **E2E configuration.** `e2e.yml` runs `cp .env.development.example .env` (TRD 16:348), and that template sets `RATE_LIMIT_LOGIN=5/minute` (TRD 21:175). The only later changes to `.env` are the SEED_* values and JWT_SECRET.
- **E2E logins.**
  - The TRD 13 §4.10 preamble says every main-run scenario logs in as a seeded user.
  - E2E-01, E2E-02 (a failed login), E2E-03..E2E-13, E2E-16..E2E-18 and E2E-20 each log in once. E2E-14 and E2E-21 log in as two roles.
  - The TRD 04 spec files also log in: FE-185 to FE-192, including several sign-ins in `auth.spec.ts` and every route in `a11y.spec.ts`.
  - The read-only invocation runs with Playwright's default parallel workers. The limiter state persists across the per-project invocations, because the backend is not restarted.
- **Client IP.** All browser requests reach `127.0.0.1:8000` and are forwarded by Docker port publishing, so the container sees one peer address.

Impact:
- Each browser project needs more than 20 logins within a few minutes. From the 6th login in any minute, `POST /auth/login` returns 429, and the affected scenarios fail at the login step.
- The required `playwright` check (CIC-031, CIC-070, TST-150) therefore fails on every run.
- Retries (TST-101) do not help reliably, because the window is shared.
- The same applies to the backend suites. `TestClient` always reports one client host, so the auth matrix (Table 4.13-A), TST-188 and any fixture that logs in through the API share one limiter with TST-131. The suite then depends on test order, which TST-005 forbids.
- This is the same class of defect as R5-01 (every seeded login rejected), which was Major.

Recommendation:
- State in TRD 16 `e2e.yml`, TRD 21 (the E2E column) and TRD 13 §8 that the E2E stack runs with a higher RATE_LIMIT_LOGIN, for example `-e RATE_LIMIT_LOGIN=1000/minute`. Keep the 5/minute limit verified by TST-131 against a dedicated app instance.
- Alternatively, require one login per role per project (Playwright setup project and `storageState`, created after the `globalSetup` reset), and keep the explicit login scenarios to at most 5 per minute.
- Add a pytest fixture that resets the slowapi limiter between tests.

### 4.2 Minor

| ID | Location (A vs B) | Description and evidence | Recommendation |
|---|---|---|---|
| R6-02 | D-73 (TRD 24:236), TRD 13 §8 (13:558), CIC-030: the `globalSetup` runs `seed test_v0_1 --reset` (downgrade base, upgrade head) while the Compose backend keeps running, versus API-125 (05:377, persistent pool, `pool_recycle=300`) and the prepared-statement note, which applies only "behind the Neon pooler" (TRD 15:566, TRD 21:282) | psycopg 3 server-side prepares a statement after 5 executions on one connection (`prepare_threshold` default 5). After the reset, every table and enum type has a new OID. Re-tested on PostgreSQL 16: a statement prepared over an enum column, executed again after DROP/CREATE of the table and type, fails with `ERROR: cached plan must not change result type`. In the main run, the read-only invocation warms the pool. The next invocation (the `@mutating` group, or the next browser project) starts within 5 minutes of the reset, so reads of `alerts.status`, `residents.status` and similar enum columns can return 500. The DS-07 local stack (direct Postgres) is the case that the "Neon pooler only" wording leaves unprotected. | State in API-125 that `connect_args={"prepare_threshold": None}` applies in every environment, or make `global-setup.ts` restart the backend (or call a test-only pool dispose) after the reset. |
| R6-03 | FE-187 (TRD 04:607, `staff-review.spec.ts`: adds a note on R09, saves a review with outcome "Checked on resident, no concern", asserts "Alerts (1)") versus D-73 (24:236), TST-100 (13:358), CIC-030/CIC-032 (16:394/396) and E2E-09 (13:373) | **Residue of R5-02.** D-73, TST-100 and CIC-030 name the `@mutating` group as exactly "E2E-18, then E2E-09". FE-187 is a second mutating spec. TRD 04 neither tags it nor maps it to E2E-09, and it uses a different outcome from E2E-09 ("Explained by a known cause" with "Cold, cough or sore throat"). Built untagged, it runs in the parallel read-only group, and "Alerts (2)" / "Not reviewed" in E2E-01, E2E-17, E2E-20, FE-193 and CIC-032 then depend on order. D-73's general rule ("Scenarios that save a review, a note or a snooze are tagged `@mutating`") lets a careful implementer tag it. | Make FE-187 the implementation of E2E-09 (one spec, one outcome), or list it in the `@mutating` group in D-73, TST-100 and CIC-030 and tag it in TRD 04. |
| R6-04 | TST-005 (13:88: "Every test shall be deterministic: no dependence on wall-clock time … or on test execution order") versus E2E-09 "after E2E-18" (13:373), E2E-19 "after E2E-15 and TST-187" (13:382), E2E-15 and TST-187 (current UTC time, PIPELINE_AS_OF empty; 13:379, 13:516), and the D-73 serial ordering | **Introduced by the round-5 fixes (R5-02, R5-04).** The E2E design now intentionally depends on execution order and on the wall clock. TST-005 still applies to "every test" without exception. Its verification ("pytest -p randomly") shows it was meant for pytest. | Scope TST-005 to the pytest suites, or name the E2E exceptions (D-73 ordering; the `@isolated` current-time scenarios). |
| R6-05 | TST-065 (13:297: "after `time-machine` moves the clock past `snoozed_until`, `GET /api/v1/alerts` lists the alert as not snoozed again") versus the TRD 19 `Alert` schema (19:1626–1643), API-080 (05:248), FR-261 (02:321), UX-303 (11:643), DME-022 (23:62) | **Residue of R5-03.** The API exposes only `snoozed_until`. There is no derived "snoozed" field, and the API orders by `triggered_at`. The snoozed/not-snoozed grouping (FR-261) and the "Not reviewed · reminder …" badge (UX-303) are client-side comparisons with the current time. The `GET` response is therefore identical before and after the clock moves, and the UI path that makes the emphasis return is not tested anywhere. Separately, DME-022 defines `snoozed_until = now()` (the database clock), which `time-machine` cannot freeze, whereas API-132 and CUS-039 say "now + hours". | Assert the expiry in a Vitest test of `AlertQueue` and the review badge, using fake timers. In TST-065, assert only the stored value. Say in DME-022 that the application clock computes `snoozed_until`. |
| R6-06 | PGS-016 (TRD 20:73, "Test (CI job `schema-diff`)") versus CIC-070 (16:457, exactly eight required jobs; AC-CIC-08) and `ci.yml` (16:134–296) | No job `schema-diff` exists. The test `tests/integration/test_schema_reference.py` runs inside `backend-test`. | Replace "CI job `schema-diff`" with `backend-test`. |
| R6-08 | D-73 TRD column "13, 16" (24:236) versus the D-73 citations in TRD 04:593 and TRD 25:243, and the TRD 03 AC-NFR-10 change. TRD 24 revision 0.6 (24:282: "R5-01, R5-02, R5-06, R5-07, R5-09") versus the fix log (R5-03 and R5-04 also changed TRD 24, D-73). The TRD 03 revision 0.6 (03:274) lists only R5-05, although the fix log lists TRD 03 under R5-02. D-71's source column does not record the round-5 amendment that its text states. | Bookkeeping only, of the same kind as the D-72 column omission in R5-09. | Set the D-73 TRDs to 03, 04, 13, 16, 25. Add R5-03 and R5-04 to the TRD 24 row and R5-02 to the TRD 03 row. Add "round 5 R5-01" to the D-71 sources. |

(R6-07 is a missing requirement; see section 3.)

---

## 5. Cross-Reference Validation

| Check | Method | Result | Findings |
|---|---|---|---|
| Duplicate requirement IDs | Script `xref.py` over the first cell of every table row and over list-item AC IDs | 2,003 requirement IDs defined. No duplicates. E-01..E-32 appear twice in TRD 19 by design (detail and summary). | — |
| Dangling requirement IDs | Script: defined IDs compared with every reference | None. The only script hits are the known artefacts: E2E-01..E2E-21 (defined as the first cell of Table 4.10-A, with the name after the ID) and AC-DB-02a (a list item). TST-188 is new and defined. | — |
| OQ / ASM / RSK / DSC / D vs TRD 24 | `grep -rhoE "(OQ\|ASM\|RSK\|DSC\|D)-[0-9]{2}"` plus a definition check | ASM-01..08, DSC-01..14, OQ-01..26, RSK-01..15 and D-01..D-73 are used, and all are defined. `OQ-27` and `RSK-16` appear only in the "next free" rule. The scope line (24:15) and AGT-002 (25:94) refer to "every D-xx of §4.6". | R6-08 (D-73 column) |
| E-, S-, UC-, AC- IDs | Script | E-01..E-32, S-01..S-13, UC-01..UC-15 and the AC IDs are defined | — |
| Endpoints vs TRD 19 | Script `ep.py`: every `METHOD /path` compared with E-01..E-32 | All match. The only non-matches are the known ones: `/alerts/{id}/acknowledge` and `/audio` (in "shall not exist" text), `/openapi.json` and `/docs` (API-113), `PATCH /users` (meaning `/users/{id}`), the `/ingest]` Mermaid label and `/alerts/{R09 alert id}`. | — |
| Tables/columns vs TRD 20 DDL | Script `cols.py`: 24 `CREATE TABLE` blocks compared with every `table.column` token | All match. The only non-matches are `alerts.spec` (a file name) and `config_parameters.facility_tz` (config-key notation). | — |
| DDL executes (D-71/D-72/D-73 re-test) | PostgreSQL 16 scratch cluster. The 33 `sql` fences of the current TRD 20 were re-extracted to `scratchpad/r6/`; they are byte-identical to the round-5 copy. Script `/tmp/claude-0/-home-user-echowell/06d21bae-4975-509b-846a-5a1512c441c2/scratchpad/t_r6.sh` (`t_r5b.sh` pointed at `r6/`). | (0) Without extensions, 0001 as the migrator fails with the 0001 message (exit 3). (1) The provisioning fence as superuser on a database preset to America/Chicago, then roles: exit 0. (2) 0001 and 0002 as `echowell_migrator_login` with `SET ROLE`: exit 0. The database has 24 tables, 17 triggers, 15 enums and 46 config rows, every table is owned by `echowell_migrator`, and `SHOW timezone` as the app login returns `UTC`. (2b) The provisioning fence run as the migrator is refused ("must be owner of database"). (3) Downgrade base as the migrator: exit 0, 0 tables, extensions kept. (3b) `DROP EXTENSION` as the migrator: "must be owner". (4) Re-migrate: same counts, `UTC`. The `seed.reset` audit row is accepted and `Auth.Login` is rejected by `audit_logs_action_ck`. (5) The app login is denied `evaluation_ground_truth`, `SET ROLE echowell_readonly`, `DELETE alerts`, `UPDATE raw_sessions` and `DELETE audit_logs`; `gen_random_uuid()` works. The readonly login is denied `password_hash`. An owner DELETE on `audit_logs` without the purge setting raises EW001 and succeeds with it. (6) A second database (the `echowell_demo` pattern): provisioning is idempotent and migration succeeds. Extra test (R6-02): a prepared SELECT over an enum column, re-executed after DROP/CREATE of the table and type, raises `cached plan must not change result type`. | R6-02 |
| Seeded e-mail validation | `r5lib` (pydantic 2.9.2, email-validator 2.2.0), `r5chk/emails.py` | `EmailStr` emits `{format: email}`, accepts `admin@`, `clinician@` and `researcher@example.com`, and rejects `admin@echowell.test`. No `echowell.test` remains anywhere in the repository outside `docs/reports/`. | — |
| Env vars vs TRD 21 | Script `env.py`: 45 defined names compared with env-style tokens | All defined. The non-matches are the same known ones as in round 5: error codes, report names, workflow-local `BACKEND_URL`/`FRONTEND_URL`, GitHub variables (21:133), `RAILWAY_GIT_COMMIT_SHA`, and `NIGHTLY_SCHEDULER_ENABLED` (in "shall not exist" text). `-e PIPELINE_AS_OF=` relies on the TRD 21:84 rule "empty = current time". | — |
| Error codes vs TRD 05 | Script (36 codes) | All in the catalogue | — |
| Audit actions vs TRD 12 §4.12 | Script (24 actions) | All in the vocabulary | — |
| CLI command names | `backend.cli <cmd>` and backticked command names compared with the TRD 15 §4.8 table (14 commands) | Every command used is in the table. The `create-api-key` syntax is now the same in TRD 05:529, SEC-020 (the single definition) and TRD 15:383. | — |
| CI workflows / jobs / config files | `*.yml` names; job names compared with CIC-070; Playwright config and setup paths | The five CIC-002 workflows are used consistently, and the eight `ci.yml`/`e2e.yml` required jobs match CIC-070. `frontend/playwright.config.ts`, `frontend/playwright.isolated.config.ts` and `frontend/tests/e2e/global-setup.ts` are named identically in TRD 13, 16 and 24, and in TRD 04 via D-73. The one exception is PGS-016's job `schema-diff`. | R6-06 |
| File paths | Script `paths.py`: backticked paths grouped by file name | Consistent. The new paths are `frontend/playwright.isolated.config.ts`, `frontend/tests/e2e/global-setup.ts`, `tests/integration/test_alert_snooze.py` and `tests/integration/test_seed_logins.py`. The relative forms in TRD 04 (`tests/e2e/`, `tests/fixtures/ds07/`) are relative to `frontend/`, as before. | — |
| Local/CI placeholder credentials | grep for the old values (`*-local`, `*-ci`, `PASSWORD: echowell`) | None remain. Compose, `.env.development.example` and the e2e.yml demo step use `local-dev-only-*`, and `ci.yml` uses `ci-only-*`. These match DB-057, SEC-050, SEC-056, DEP-018, ENV-041, CIC-115 and the TRD 21 rows. | — |
| Golden fixtures | pandas with `python3 -I` | Section 6.3 | — |
| Code fences / placeholders | Script / grep | Fence counts are even in all 26 files. The placeholder grep hits only GIT-053. | — |
| Document structure / versions | Script | 12 TRDs at 0.6 (03, 04, 05, 06, 12, 13, 15, 16, 20, 21, 24, 25), each with a round-5 revision row. 1 TRD is at 0.5, 3 at 0.4, 7 at 0.3 and 3 at 0.2. | R6-08 (row contents) |

---

## 6. The five checks in detail

### 6.1 Database requirements support all APIs: **PASS**

- Every endpoint E-01..E-32 reads and writes only tables and columns of the TRD 20 DDL.
- The `echowell_app` grants cover every API write, and the denials of PGS-021 and PGS-040 hold. This was executed (section 5).
- D-72 now covers the `timezone` setting. The provisioning fence sets it for the current database, and PGS-001 is met when executed.
- The `reject_mutation()` comment now names only the IRB purge (R5-08).
- Minor: R6-06 (PGS-016 cites a nonexistent job).

### 6.2 APIs support all frontend requirements: **PASS**

- All 32 endpoints are in the TRD 19 summary and YAML.
- Every TRD 04 client function resolves to an endpoint.
- `GET /config/ui` supplies the snooze hours and the review explanations.
- No frontend item lacks an API source.
- R6-05 concerns test design: the snooze expiry is a client-side computation that no test exercises. It is not a missing API.

### 6.3 Analytics requirements support all business requirements: **PASS**

SRC-03 and SRC-05 were read again with `python3 -I` and pandas. Every value matches the TRDs.

| Quantity | Value |
|---|---|
| Annotated_sessions `expected_status` (302 rows) | usable 267, missing_resident 17, set_aside 12, missing_device_gap 2, duplicate 2, quarantined 2 (missed tile 19; funnel 300 → 281 → 269 → 267) |
| SRC-05 input | 283 rows, 2 duplicate `session_id`s, 30 columns |
| Exp_baselines | 180 rows; floor applied only to `number_of_pauses` (8 residents) |
| Exp_scores | 98 rows: R01 14, R02 8, R03 6, R04 14, R05 12, R06 14, R07 2, R09 14, R10 14 |
| Alarm states | off 81, on 15, RINGS (first crossing) 2. Final tallies are R09 26.830256 and R10 13.418183, as in Alerts.dc.html, E2E-17, API-080 and CIC-032. |
| Parameters | facility_tz America/Chicago, noise −40, minimum speech 1 s, duplicate rule as TRD 20 §4.11 |

The engine processes a second same-day session (TRD 07:435, BSC-043), and the 30-day "used" count counts sessions from `processed_sessions` (DB-041). TST-187 (`R11-<date>-02`) therefore raises the count as it asserts.

No findings.

### 6.4 Testing requirements validate all critical functionality: **FAIL**

- Every BR has TST, TDV or MVP coverage.
- D-73 removes the shared-state conflict of R5-02. Each Playwright invocation starts from a fresh `test_v0_1` seed and DS-10, and the read-only assertions run before the `@mutating` group.
- The `@isolated` run on `echowell_demo` is consistent with the as-of rules. PIPELINE_AS_OF is empty, the R11 records carry the current time, R11 is enrolled on 2026-10-01, and E2E-19 runs an explicit `as_of` 2026-10-30.
- TST-188 covers the seeded logins.
- Fails on R6-01: the login rate limit makes the main run fail.
- Minor:
  - R6-02: the reset happens under a live pool with server-side prepared statements.
  - R6-03: FE-187 is outside the `@mutating` group.
  - R6-04: TST-005 contradicts the E2E ordering and wall-clock use.
  - R6-05: the snooze-expiry assertion is not observable.
  - R6-07: no nightly job runs the random-order or robustness checks.

### 6.5 Deployment requirements support the architecture: **PASS**

- The architecture follows `Deployment_Architecture.md`: a monorepo; Next.js on Netlify; FastAPI on Railway; Neon, with Railway PostgreSQL as the alternative (DEP-035 now runs the D-72 provisioning step first); GitHub Actions; and the AWS target (Amplify, App Runner, RDS; DEP-117 includes extensions, time zone and roles).
- The staging smoke login uses `researcher@example.com` and `STAGING_SEED_RESEARCHER_PASSWORD` (DEP-080(c), TRD 16 §4.4 step 5, TRD 21:131).
- The local quick start (TRD 15 steps 6–8) uses `admin@example.com`.
- The D-71 staging exception stays consistent across DB-029, DEP-060, D-71 and the TRD 15 table.
- The placeholder-credential rules (DB-057, SEC-050, SEC-056, DEP-018, ENV-041, CIC-115) now cover every committed local/CI value.
- Minor: R6-08 (bookkeeping).

---

## 7. Recommended fixes (not applied)

In priority order:

1. **R6-01:** give the E2E stack an explicit RATE_LIMIT_LOGIN override, for example `-e RATE_LIMIT_LOGIN=1000/minute` or a line appended to `.env` in `e2e.yml`, with the TRD 21 E2E column and TRD 13 §8 updated. Alternatively, mandate one login per role per project (`storageState`). In both cases, add a pytest fixture that resets the slowapi limiter, and keep TST-131 on its own app instance.
2. **R6-02:** require `prepare_threshold=None` in every environment (API-125), or restart the backend or dispose its pool in `global-setup.ts` after `seed --reset`.
3. **R6-03 and R6-05:**
   - Merge FE-187 into E2E-09, or add it to the `@mutating` group, with one outcome.
   - Move the snooze-expiry assertion to a Vitest test with fake timers.
   - Make DME-022 say "application clock".
4. **R6-04, R6-06, R6-07:**
   - Scope TST-005 to pytest.
   - Change PGS-016's job to `backend-test`.
   - Add a scheduled job (for example `nightly-validation` in `e2e.yml`) for `pytest -p randomly` and `tests/validation/robustness.py`.
5. **R6-08:** update the D-73 TRD column, the TRD 03 and TRD 24 revision rows, and the D-71 sources.

---

## 8. Prior findings status

### 8.1 Round-5 findings (R5-01..R5-11)

| ID | Round-5 severity | Subject | Status | Evidence (round 6) |
|---|---|---|---|---|
| R5-01 | Major | Seeded `.test` accounts rejected by `format: email` | **Resolved** | `admin@`, `clinician@` and `researcher@example.com` appear in DB-057 (06:592–593), D-71 (24:234), TRD 20 §4.12 (20:1078), TRD 21:85/131/132, TRD 13:361 and TST-188 (13:515), TRD 15:142–143 and DEP-080 (15:428), and TRD 16:364/414. There is no `echowell.test` anywhere. Re-tested: all three are accepted by `EmailStr`. TST-188 adds a login test for each. |
| R5-02 | Major | Main-run scenarios change the shared E2E database | **Partially resolved** | D-73, the TRD 13 §4.10 preamble, TST-100, E2E-09/E2E-18 (`@mutating`), CIC-030, CIC-032, the `e2e.yml` loop (16:365–368, one invocation per project and group, `globalSetup` reset), TST-004, AC-NFR-10, the TRD 04 E2E row and TRD 25:243 are consistent. Residue: FE-187 (TRD 04:607) is a second mutating spec, untagged and outside the named group (R6-03). |
| R5-03 | Minor | E2E-19 snooze expiry needs a server clock | **Partially resolved** | E2E-19 no longer advances a clock and asserts `snoozed_until` = click + 24 h ± 2 min. Expiry moved to TST-065 with `time-machine` (D-73 notes this). Residue: TST-065's "lists the alert as not snoozed again" has no observable API state, and the UI expiry is untested (R6-05). |
| R5-04 | Minor | TST-187 record timestamp unspecified | **Resolved** | TST-187 (13:516) and E2E-15 (13:379) post at the current UTC time with `R11-<local date>-02`/`-01`, PIPELINE_AS_OF is empty on `echowell_demo` (e2e.yml `-e PIPELINE_AS_OF=`, CIC-030, §8), and R11 is enrolled on 2026-10-01 (13:117–118). A same-day second session is processed and counted (section 6.3). |
| R5-05 | Minor | TST-100, the §4.10 preamble and TST-004 versus the isolated run | **Resolved** | TST-100 scopes Firefox/WebKit to the main run. The preamble names the `@isolated` exception. TST-004 names `frontend-prod` :3001, `global-setup.ts` and `playwright.isolated.config.ts`. AC-NFR-10 and the TRD 04 row agree. |
| R5-06 | Minor | TRD 20 §8 and DEP-035 versus D-72 | **Resolved** | TRD 20 §8 (20:1199–1203): 0001 takes only the §4.2 check block; its downgrade never drops an extension, role or setting. DEP-035 (15:242) runs provisioning first as the Railway `postgres` superuser. D-72 and TRD 20 §4.2 list Railway PostgreSQL. Re-executed (section 5). |
| R5-07 | Minor | No owner for `ALTER DATABASE … SET timezone` | **Resolved** | The provisioning fence (TRD 20 §4.2, a `DO … current_database()` block), PGS-001, TRD 20 §4.3, TRD 15 §4.2 and Neon step 4, DEP-035, DEP-117, the `ci.yml` comment and D-72 now include it. Executed: `SHOW timezone` = `UTC` on a database preset to America/Chicago. |
| R5-08 | Minor | Stale `reject_mutation()` comment | **Resolved** | 20:233–234: "used only by the IRB withdrawal purge, PGS-019; the test-database reset drops and recreates the schema instead". |
| R5-09 | Minor | Stale D ranges; D-72 omitted TRD 13 | **Resolved** | 24:15 and AGT-002 (25:94) refer to "every D-xx of section 4.6", and 24:264 says "next free D number after the last row". D-72 lists 06, 13, 15, 16, 20. (A new column omission for D-73 is R6-08.) |
| R5-10 | Minor | `create-api-key` scope syntax | **Resolved** | SEC-020 (12:110) is the single definition (`[--scope …]…`, optional, repeatable, default `ingest:write`). TRD 05:529 and TRD 15:383 use the same form and refer to it. |
| R5-11 | Minor | Committed local/CI database passwords outside the exception | **Resolved** | Compose (15:163–183), the template URLs (21:157–159), the e2e.yml demo step (16:374) and `ci.yml` (16:186–199) use `local-dev-only-*`/`ci-only-*`. DB-057, SEC-050, SEC-056, DEP-018, ENV-041, CIC-115 and the TRD 21 rows (21:128–129) cover exactly these patterns. No old value remains. |

Totals: Resolved 9, Partially resolved 2, Not resolved 0.

Spot checks of the resolutions from rounds 1–4 found no regression. They covered:
- the D-71 staging exception;
- the closed migrator list (TRD 20 §4.3);
- the audit vocabulary;
- the as-of precedence;
- the CLI table;
- the endpoint, column and env-var cross-references.
