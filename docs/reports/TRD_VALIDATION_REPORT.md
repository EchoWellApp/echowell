# TRD Validation Report (Phase 1, round 3)

| Field | Value |
|---|---|
| Scope | `specs/TRD/00`–`25`, checked against `specs/prompts/TRD_Generation_Prompt.md`, `specs/architecture/Deployment_Architecture.md`, `specs/UI-wireframe/*.dc.html` (5 files), `specs/business-requirements/*`, `specs/data-samples/*`, `specs/algorithm/generate_pipeline_test_v0_1.py` |
| Checklist | `specs/prompts/TRD_Implementation_Audit_Checklist.md` Phase 1, and the definition of done in TRD 25 §Phase 1 |
| Round | 3. This report replaces round 2 (26 findings, R2-01..R2-26), after the round-2 fixes listed in `docs/reports/TRD_VALIDATION_FIXES.md` were applied. |
| Branch | `trd-generation`. Read only: no file under `specs/` was changed and no git command was run. |
| Date | 2026-10-19 |

**How locations are written.** `TRD NN:line` means line `line` of `specs/TRD/NN_*.md`. For example, `TRD 15:385` is line 385 of `specs/TRD/15_Deployment_and_DevOps_Spec.md`.

**Severity scale** (the same as rounds 1 and 2):

| Severity | Meaning |
|---|---|
| Critical | Built as written, the system would be wrong or unsafe: a core path fails at runtime, or two binding rules cannot both hold. |
| Major | An ambiguity or conflict that an implementer would probably resolve the wrong way, or a mandated path or check that cannot work as specified. |
| Minor | A real inconsistency or error that a careful implementer would still resolve correctly. |

**Numbering.**
- New findings in this round are R3-01, R3-02, and so on.
- Earlier findings keep their numbers: R2-nn from round 2 and F-nn from round 1 (section 8).

---

## 1. Summary

**Verdict: FAIL.** The verdict rule is FAIL if any Critical or Major finding remains. One Major finding remains:

- **R3-01 (Major).** As specified, `seed test_v0_1 --reset` cannot run. TRD 16 deploy-staging step 4, DEP-074, CIC-041 and DEP-071 rely on this command to re-seed staging. This was reproduced on PostgreSQL 16 with the TRD 20 DDL, which fails in three ways:
  - Truncating `devices` while keeping `api_keys` fails on the `api_keys.device_id` foreign key.
  - Truncating `raw_sessions` raises `EW001` unless the purge path is used. PGS-019 reserves the purge path for other procedures, and the purge path needs `SET ROLE echowell_migrator`, which only Alembic is told to issue.
  - The command then re-creates users and an API key that `--reset` deliberately kept, which violates `users_email_uq`. It also prints new credentials into the GitHub Actions log.

The round-2 fixes held.
- **Round 2:** 24 of the 26 findings are fully resolved. R2-16 and R2-25 are partly resolved, because TRD 01 and TRD 23 were not updated. Their remaining parts are filed as R3-03 and R3-04.
- **Round 1:** all 10 findings that were partly resolved after round 2 are now fully resolved.
- **Regressions from the round-2 edits:** two Minor items, both caused by the R2-03 `set-config` fix:
  - R3-02: the list of commands allowed to use the migrator credential leaves out `set-config`.
  - R3-05: ANL-058 tells operators to `set-config` a key that does not exist.

| Severity | Count |
|---|---|
| Critical | 0 |
| Major | 1 |
| Minor | 9 |
| **Total new (round 3)** | **10** |

Prior findings:

| Set | Resolved | Partially resolved | Not resolved |
|---|---|---|---|
| R2-01..R2-26 (26) | 24 | 2 (R2-16, R2-25) | 0 |
| Round-1 findings still partial after round 2 (10) | 10 | 0 | 0 |

Phase 1 checks:

| # | Phase 1 check | Result | Key evidence |
|---|---|---|---|
| 1 | Database requirements support all APIs | **PASS** | All 24 tables, CHECKs, indexes and grants support E-01..E-32. The TRD 20 DDL runs cleanly on PostgreSQL 16. Minor: R3-09 (actor type of `user.created`). |
| 2 | APIs support all frontend requirements | **PASS** | All 32 endpoints are in the summary table and the OpenAPI YAML, with no dangling `$ref`. All 27 frontend type aliases in TRD 04 §4.6.3 resolve to TRD 19 schemas. The check-in log contract now agrees across FR, UX, API, DB and the wireframe (D-67). |
| 3 | Analytics requirements support all business requirements | **PASS** | Every workbook figure was re-verified (section 6.3). `set-config` + `rebuild` gives a defined way to change parameters. Minor: R3-04, R3-05. |
| 4 | Testing requirements validate all critical functionality | **PASS** | Every BR has tests. New admissions are now tested (TST-185, TST-186). Minor: R3-06, R3-07, R3-08, R3-10. |
| 5 | Deployment requirements support the architecture | **FAIL** | R3-01: the staging re-seed path cannot run. Minor: R3-02, R3-03. |

TRD 25 §Phase 1 definition of done:

| Criterion | Result | Evidence |
|---|---|---|
| Every BR-01..BR-18 maps to at least one TRD requirement and test | **Met** | Section 2.1. Each BR is cited by 25–269 requirement rows across 10–24 TRDs. The TRD 02 §4.28 BR→FR table (TRD 02:570–590) covers all 18 BRs. Every BR has at least 4 TST, TDV or MVP rows. |
| Every OQ/ASM/RSK/DSC/D ID used in the TRDs exists in TRD 24 | **Met** | IDs used: ASM-01..08, DSC-01..14, OQ-01..26, RSK-01..15, D-01..D-70, all defined in TRD 24. `OQ-27`, `RSK-16` and `D-71` appear only as "next free number" text in TRD 24:261. |
| Each of the five checks has a pass/fail line with evidence | **Met** | The Phase 1 checks table above and section 6 |
| No TRD file modified | **Met** | Read-only run |
| `grep -rnE "T[B]D\|T[O]DO\|l[o]rem" specs/TRD` returns nothing | **Met in substance** | The only hit is GIT-053 (TRD 18:219), which is the rule that forbids these words. The same hit was accepted in rounds 1 and 2. |

---

## 2. Requirements Traceability Matrix

### 2.1 Business requirements → TRD requirements → tests

Counts are scripted. A row is counted when its first cell is a requirement ID and it cites the BR, either directly or through a range such as `BR-01..BR-18`. The restatement tables for BR, SRC, OQ, ASM, RSK and DSC are left out.

| BR | Summary (TRD 00) | Rows / TRDs | Key FRs (TRD 02 §4.28) | Tests / MVP criteria | Gap (round 3) |
|---|---|---|---|---|---|
| BR-01 | Ingest feature records, never audio | 80 / 20 | FR-001–FR-005, FR-020–FR-028, FR-184, FR-321 | TST-030, TST-043, TST-045, TST-046, TST-133, TDV-031, TDV-090, MVP-02 | — |
| BR-02 | Keep raw records unaltered | 101 / 17 | FR-005–FR-007, FR-010, FR-028, FR-223, FR-296 | TST-037, TST-041, TST-043, TDV-002, TDV-050, TDV-054, MVP-02, MVP-12 | Purge/reset path: R3-01 |
| BR-03 | Drop duplicates, keep first arrival | 40 / 13 | FR-008, FR-011, FR-029–FR-031, FR-182, FR-316 | TST-020, TST-044, TST-046, TDV-054, MVP-01, MVP-03 | — |
| BR-04 | Set aside poor-quality sessions | 28 / 13 | FR-024, FR-040–FR-044, FR-181, FR-290 | TST-020, TDV-053, MVP-01, MVP-03 | — |
| BR-05 | Quarantine wrong-speaker sessions | 27 / 10 | FR-060–FR-065, FR-074, FR-292 | TST-020, TDV-055, MVP-01, MVP-03 | — |
| BR-06 | Log missing days honestly | 69 / 15 | FR-120–FR-125, FR-135, FR-153, FR-154, FR-294, FR-295 | TST-020, TDV-052, TDV-053, TDV-064, TDV-068, MVP-01 | — |
| BR-07 | Remove morning offset | 26 / 11 | FR-070–FR-074, FR-171 | TST-020, TDV-056, MVP-01 | — |
| BR-08 | Epochs; restart baseline | 34 / 12 | FR-050–FR-053, FR-132, FR-155, FR-172 | TST-020, TDV-057, MVP-01 | — |
| BR-09 | Robust personal baseline, frozen | 55 / 15 | FR-080–FR-086, FR-162, FR-163, FR-205, FR-229, FR-230 | TST-020, TST-184, TDV-051, TDV-058, TDV-060, MVP-01 | `features` key: R3-05 |
| BR-10 | Signed z and composite | 25 / 11 | FR-090–FR-095, FR-169, FR-170, FR-266 | TST-020, TDV-051, MVP-01 | — |
| BR-11 | CUSUM persistent-deviation flag | 61 / 14 | FR-100–FR-110, FR-165–FR-167, FR-261–FR-265, FR-300 | TST-020, TDV-059, TDV-060, TDV-067, MVP-01, MVP-13 | — |
| BR-12 | Residents overview | 92 / 17 | FR-130–FR-140, FR-150–FR-156, FR-312, FR-330 | TST-033, TST-090, TST-110, TST-181, TDV-062, TDV-066, MVP-04 | 5 s target untested: R3-06 |
| BR-13 | Resident detail page | 112 / 15 | FR-160–FR-173, FR-180–FR-184, FR-190–FR-195, FR-260–FR-280 | TST-090, TST-093, TST-110, TST-181, TDV-066, MVP-05, MVP-13 | — |
| BR-14 | New-admission arm (Should) | 32 / 10 | FR-200–FR-207, FR-331 | TST-090, TST-185, TST-186, MVP-06 | Priority mismatch: R3-10 |
| BR-15 | Reproduce workbook R01–R10 | 166 / 22 | FR-240–FR-245, FR-310–FR-323 | 41 TST/TDV/MVP rows (TST-005, TST-022, TST-048, TST-070, TDV-001, TDV-013, …) | Staging re-seed: R3-01 |
| BR-16 | Data protection, roles, audit | 269 / 24 | FR-210–FR-221, FR-226–FR-229, FR-250–FR-254 | TST-007, TST-032, TST-041, TST-053, TST-130, TDV-006, TDV-007, MVP-07 | R3-01 (credentials in CI log), R3-02, R3-09 |
| BR-17 | Monorepo deploy on Netlify/Railway/Neon/GHA | 74 / 15 | FR-253, FR-254 | TST-001, TST-150, TST-170, MVP-08 | R3-01 |
| BR-18 | Detection not diagnosis, no LLM/ML | 47 / 15 | FR-164, FR-277, FR-278, FR-298 | TST-096, TST-097, TST-170, MVP-09 | — |

### 2.2 Frontend requirements (TRD_Generation_Prompt) → UX / FE IDs

Every item in the prompt's "Frontend Requirements" list was traced to TRD 11 (UX), to TRD 04 §4.8 components (the names below are the binding TRD 04 names) and to a test.

| Prompt frontend item | UX IDs | FE components (TRD 04 §4.8) | Tests | Round-3 note |
|---|---|---|---|---|
| Three primary views (overview, detail, new admissions) and the two added views | D-23; TRD 11 §4.3, §4.5, §4.7, §4.17, §4.18 | Residents page, Resident detail page, AdmissionsTable, AlertsPage, AnalyticsPage | E2E-03..E2E-21, TST-110 (8 routes) | — |
| All enrolled residents; sort by alarm, resident ID, last check-in | UX-020–UX-033, UX-261 | ResidentsTable, SortSelect | E2E-04, E2E-05, E2E-06 (order re-verified against SRC-05 timestamps) | — |
| Statuses Alarm On / No Alarm / Baseline Still Forming | §4.3.4, UX-036 | StatusBadge | E2E-04 | — |
| 30-day used, set aside, quarantined, missed; missing days visible, never backfilled | UX-039, UX-047, UX-048 | ResidentsTable, SummaryTiles | E2E-03, E2E-04, OAS-021 | — |
| Device panel: assigned, shared, silent periods, days with no activity | UX-050–UX-058, UX-263 | DevicePanel, DeviceCell | E2E-07 | — |
| CUSUM tally with alarm line 5.0, baseline period, alarm trigger and persistence | UX-080–UX-092 | CusumChart, CusumTable | TST-093, E2E-08 | — |
| 7 scored measurements in plain language; 12 others stored, not scored | UX-100–UX-108 | FeatureCard (×7), Sparkline, OtherMeasurementsCard | E2E-08, TST-090 | — |
| Baseline status, progress, freeze indicator | UX-060–UX-066 | ResidentHeader, WhatThisMeans | E2E-08, E2E-10, E2E-11 | — |
| Check-in log: alarms, set-asides, quarantines, missed days, baseline restarts | UX-140–UX-149 | CheckinLog | E2E-10, E2E-11, E2E-12, E2E-15 | Resolved (D-67, R2-01) |
| Staff notes: observations, actions, follow-up | UX-120–UX-135 | StaffReviewForm, NotesList, ReviewDialog | E2E-09 | — |
| New admissions: facility comparison, move to main list, "future/experimental" | UX-181–UX-195 | AdmissionsTable, FacilityRangeChart, ExperimentalBanner | E2E-13, TST-185, TST-186 | Resolved (R2-26) |
| Alert review (SRC-18) | UX-300–UX-331 | AlertQueue, AlertCard, DataAlertQueue, AlertReviewPanel, AlertReviewForm | E2E-17, E2E-18, E2E-19 | Role logins: R3-07 |
| Analytics (SRC-19) | UX-351–UX-384 | KpiTiles, DailyCheckinsChart, LossFunnel, UsableByResidentChart, AlarmTimingTable, ReviewOutcomesTable | E2E-20, E2E-21, TDV-074 | Role logins: R3-07 |
| Loading, empty and error states; accessibility; responsive layout; plain language | UX state rows, FE-145, NFR-060, VIS-003..005 | SectionState | TST-090, TST-110, E2E-16, TST-097 | — |

Result: every prompt item maps to UX and FE IDs and to at least one test. No frontend item lacks an API source.

### 2.3 Wireframes → UX sections

The visible text of all five wireframes was extracted and compared with TRD 11 and with the TRD 14 tables.

| Wireframe | UX section | Coverage |
|---|---|---|
| `Main.dc.html` (SRC-09) | TRD 11 §4.3, §4.4, §4.13 | Complete. Tiles 2/7/1/19, row values (for example R08 13·5·0·12, R03 22·7·0·1), last check-in times, D02/D07B device lines and footer all match. |
| `Resident.dc.html` (SRC-10) | TRD 11 §4.5 | Complete. The log lines "Oct 21 · Alarm on · tally crossed 5.0", "Oct 17 · Watching started" and "Oct 16 · Baseline complete (16 of 16)" match the UX-142 table. The event set matches D-67. |
| `Admission.dc.html` (SRC-11) | TRD 11 §4.7 | Complete |
| `Alerts.dc.html` (SRC-18) | TRD 11 §4.17 | Complete. Card strings ("open 9 days · tally 26.8", "open 6 days · tally 13.4"), the four data-alert cards and the five explanation labels all match. |
| `Analytics.dc.html` (SRC-19) | TRD 11 §4.18 | Complete. 94% (281/300), 89% (267/300), 9 of 10, 2; funnel 300/281/269/267; drop reasons 5/5/3 (1 with two reasons); by-resident 43/73/80/93/100; alarm timing 0 and 7 days. |

### 2.4 Items with no test or only a weak test

| Item | Status |
|---|---|
| NFR-011 / SC-03 "within 5 s" (Must) | No automated test. The only acceptance row, TST-181, allows 60 s (R3-06). |
| Role-specific E2E logins (E2E-01, E2E-14, E2E-17..E2E-21) | No defined way to get clinician or researcher credentials in `e2e.yml` (R3-07). |
| Staging re-seed (DEP-074, CIC-041) | Cannot run as specified (R3-01). |

---

## 3. Missing Requirements

| ID | Severity | Where it is needed | What is missing |
|---|---|---|---|
| R3-01 | Major | TRD 15 §4.8 `seed --reset` row (TRD 15:385), DEP-071 (15:397), DEP-074 (15:400); TRD 16 §4.4 step 4 (16:390), CIC-041 (16:397); PGS-019 (TRD 20:76) | Which tables the reset empties, and how; how the purge path is entered (`SET ROLE echowell_migrator` plus `echowell.allow_purge`); and what happens to users and the API key that are kept. See section 4.1. |
| R3-07 | Minor | `e2e.yml` (TRD 16:349–359); TRD 21:131; E2E-01, E2E-14, E2E-17..E2E-21; DEP-080(c) | A way for E2E to get clinician and researcher credentials; who creates the staging smoke user. |
| R3-08 | Minor | E2E-15 (TRD 13:373), TRD 13 fixture tree (13:113–117) | The format and loader of `tests/fixtures/seeds/demo_overlay.json`. DS-10 is not listed under `tests/fixtures/answer_key/` in the tree. |
| R3-06 | Minor | NFR-011, SC-03 | An automated latency test for the 5 s ingest-to-dashboard target. |

---

## 4. Contradictions

### 4.1 Major

**R3-01 · Major · `seed test_v0_1 --reset` cannot run as specified, so the staging re-seed path is broken**

What the TRDs require:
- TRD 15 §4.8 (TRD 15:385): `--reset` "truncates all tables except `users`, `api_keys`, `audit_logs` and `config_parameters` first". The command then loads the roster, "creates the test users and API key" (DB-056, TRD 06:592) and prints their secrets once to standard output (DB-057, TRD 06:593; TRD 20:1056).
- DEP-074 (TRD 15:400), CIC-041 (TRD 16:397) and deploy-staging step 4 (TRD 16:390) run this command on staging after every push that changes a migration or `analytics/**`. The connection is `STAGING_DATABASE_URL`, which is the migrator login. DEP-071 (TRD 15:397) requires that `--reset` works on `local`, `staging` and `test`.

What the schema and other rules say:
1. **The foreign key blocks the truncate.** `api_keys.device_id` references `devices` (TRD 20:331), and `api_keys` is kept. PostgreSQL refuses to truncate a table that a kept table references.
   - Reproduced on PostgreSQL 16 with the full TRD 20 DDL, using tables owned by `echowell_migrator`: `ERROR: cannot truncate a table referenced in a foreign key constraint — Table "api_keys" references "devices"`.
2. **The trigger blocks `raw_sessions`.** `raw_sessions` has a `BEFORE TRUNCATE` trigger that calls `reject_mutation()` (PGS-018). That function lets a truncate through only when `current_user = 'echowell_migrator'` and `echowell.allow_purge = 'on'` (TRD 20:213–223).
   - PGS-019 (TRD 20:76) reserves this path for "the test-database reset and the IRB withdrawal purge (DB-024, DB-030)". DB-024 is `reset-test-db`, which refuses to run on staging (TRD 06:465, AC-DB-08).
   - Only Alembic's `env.py` is told to run `SET ROLE echowell_migrator` (TRD 20:128). A CLI that connects as `echowell_migrator_login` has `current_user = echowell_migrator_login`.
   - Reproduced: with `allow_purge = on` but without `SET ROLE`, the truncate still raises `EW001` ("table raw_sessions is append-only"). It succeeds only with `SET ROLE echowell_migrator`, `allow_purge = on`, and `devices` left out of the truncate.
   - `purge-resident` (DB-064) and `reset-test-db` (DB-024) have the same unstated `SET ROLE` dependency.
3. **The kept users and API key are created again.** `users` and `api_keys` survive the reset, but the seed then creates `admin@echowell.test`, `clinician@echowell.test`, `researcher@echowell.test` and `test-ingest` again. This violates `users_email_uq` (TRD 20:257). Neither TRD says whether the seed skips, updates or replaces existing rows.
   - If an implementer makes the step regenerate passwords, DB-057's print-once output goes into the deploy-staging Actions log. That conflicts with the intent of TRD 12 SEC-050 and SEC-104.

Impact:
- Built as written, the re-seed step fails on every staging deploy that touches migrations or analytics. Staging then drifts from the answer key, against the purpose of DEP-074. CIC-042 and DEP-080(d) (tiles 2/7/1/19) depend on a correctly seeded staging.
- An implementer must invent:
  - the order of the truncate (or a switch to `DELETE`);
  - an exception to PGS-019;
  - the `SET ROLE` call;
  - the rule for existing users and keys.

Recommendation:
- Define `--reset` precisely: `SET ROLE echowell_migrator`, `SET LOCAL echowell.allow_purge = on`, then a list of tables that leaves out `devices` or also covers `api_keys`. Alternatively, delete in dependency order.
- Add `seed --reset` to the PGS-019 purge-path list.
- Make user and key creation "create if missing; never print or regenerate existing credentials".
- State in TRD 20 §4.3 that every migrator CLI command runs `SET ROLE echowell_migrator` after connecting.

### 4.2 Minor

| ID | Location (A vs B) | Description and evidence | Recommendation |
|---|---|---|---|
| R3-02 | TRD 15 §4.8 `set-config` row (15:386), D-69 (24:232), TRD 21:105, TRD 06:89, ENV-053 (21:98) vs TRD 20 §4.3 (20:123), TRD 12 role table (12:320), SEC-111 (12:327), DEP-040 (15:298) | **Regression from R2-03.** `set-config` "runs as `echowell_migrator` (DATABASE_MIGRATION_URL)". The ground-truth loader also uses the migrator URL (TRD 06:89, ENV-053, TRD 16 step 4). But the closed lists of migrator users name only seed, reset-test-db, purge-resident and rebuild. DEP-040 allows only "the operator CLI commands of §4.8 that TRD 20 §4.3 lists" to read DATABASE_MIGRATION_URL and enforces this with an import-boundary test. That test would reject `set-config` and the loader script. | Add `set-config` and `database/seeds/load_evaluation_ground_truth.py` to TRD 20 §4.3, the TRD 12 role table and SEC-111. |
| R3-03 | TRD 01 §4.4 trigger table (01:307, 01:309), TRD 23:253 vs D-70 (24:233), API-065 (05:222), ANL-046 (07:367); DB-058 (06:594) | **Residue of R2-25.** TRD 01 still maps "API key scope `pipeline:run`" to trigger `manual`, and TRD 23 says `manual` = "POST /pipeline/run". D-70 and API-065 record such calls as `nightly`. Also, DB-058 records the seed's run as trigger `test`, but TRD 01:309 and ANL-046 say `test` is used "only by the automated validation suite". | Update the TRD 01 table and TRD 23:253 to follow D-70. Either allow `test` for the seed command, or make the seed run use `manual`. |
| R3-04 | TRD 01:135 (ingest sequence), TRD 01:441 (§8 "recommended" signature) vs TRD 07 §4.5 (07:213–224), TRD 05:475, TRD 06:434 | **Residue of R2-16.** TRD 01 still shows `run_pipeline(records, config, frozen_baselines, as_of)` and a positional form with `frozen_baselines` fourth. The binding signature is `run_pipeline(records, residents, assignments, config, as_of, *, frozen_baselines=None)`. TRD 05 and TRD 06 were fixed; TRD 01 was not. | Quote the TRD 07 signature in TRD 01 at both places. |
| R3-05 | ANL-058 (07:394) vs TRD 20 §4.11 (23 keys), DB-055 (06:591), TRD 15 `set-config` ("refuses unknown keys") | **Regression from R2-03.** ANL-058 says a feature or sign change needs "only a change of `features` in the config with `set-config`". `features` is not a `config_parameters` key: it is a built-in `PipelineConfig` field, and none of the 23 seeded keys holds it. `set-config` would therefore refuse the change. | Either add a `features` key to TRD 20 §4.11, DB-055 and ANL-029, or reword ANL-058 to say a code change plus `rebuild` is needed. |
| R3-06 | SC-03 (00:286) and NFR-011 (03:58), both "within 5 s", vs TST-181 (13:503), "within 60 s" | The Must 5 s target is accepted by a demo test with a 60 s limit, and no automated test traces NFR-011. | Either add an NFR-011 timing test (staging, warm) or state in SC-03/NFR-011 that the demo is accepted at 60 s. |
| R3-07 | `e2e.yml` (16:349–359), TRD 21:131 vs E2E-01 (13:359), E2E-14 (13:372), E2E-17..E2E-21 (13:374–378); DEP-080(c), TRD 16:452 | The workflow creates one admin E2E user (`e2e@local.test`), and TRD 21 defines one `E2E_USER_*` pair. Several scenarios log in as clinician or researcher. The seeded role users get random passwords that are printed once (DB-057) and never captured. No step creates the staging researcher smoke user behind `STAGING_SMOKE_EMAIL`. | Add `create-user --password-stdin` steps (or `E2E_CLINICIAN_*` / `E2E_RESEARCHER_*` variables) to `e2e.yml` and TRD 21. Name the command that provisions the staging smoke user. |
| R3-08 | E2E-15 (13:373), TRD 13 fixtures tree (13:113–117) vs `import-master-data` (15:383, CSV directory only), TDV-012 (14:97) | `demo_overlay.json` (resident R11, device D11) has no defined format and no loader. The only roster loader reads the four CSV files. The TRD 13 tree lists `answer_key/` with the workbook and SHA256SUMS only, not the DS-10 CSV that `e2e.yml`, DEP-119 and local step 6 load. | Make the overlay a CSV directory loaded by `import-master-data`, or define the JSON loader. Add `evaluation_ground_truth_v0_1.csv` to the tree. |
| R3-09 | TRD 12 §4.12 `user.created` (12:286), actor type `user`, vs SEC-103 (12:308) | SEC-103 says the `create-user` CLI writes audit rows with `actor_type = system`. The vocabulary allows only `user` for `user.created`. Users created by the seed and the CLI have no user actor. | List the actor as "user (API) or system (CLI)". |
| R3-10 | FR-205 (02:261, Must) and TST-185 (13:507, Must) vs DB-025 (06:466, Should) | The only mechanism for the new-admission → longitudinal transition is a Should, while the requirement and its test are Must. | Align the priorities. |

---

## 5. Cross-Reference Validation

| Check | Method | Result | Findings |
|---|---|---|---|
| Duplicate requirement IDs | Script: first cell of every table row across all 26 TRDs (2,355 row IDs in 61 prefixes), plus list-item AC IDs | None within a file. Cross-file repeats are only the intended BR, OQ, ASM and SRC restatement tables. E-01..E-32 appear twice in TRD 19 by design (section header and summary table). | — |
| Dangling requirement IDs | Script: every `PREFIX-NNN` reference vs its definition (table rows, AC list items, E2E table rows) | None dangling. AC-DB-02a is defined as list item "2a." | — |
| OQ / ASM / RSK / DSC / D IDs vs TRD 24 | `grep -rhoE "(OQ\|ASM\|RSK\|DSC\|D)-[0-9]{2}" specs/TRD \| sort -u` | ASM-01..08, DSC-01..14, OQ-01..26, RSK-01..15 and D-01..D-70 are all defined. `OQ-27`, `RSK-16` and `D-71` occur only at TRD 24:261 ("next free"). The stated ranges agree with the content (TRD 24:16 "D-56 to D-70"; AGT-002 "D-01..D-70"). | — |
| E-, S-, UC-, MVP- and AC- IDs | Script | E-01..E-32, S-01..S-13, UC-01..UC-15, all MVP rows and 282 AC IDs are defined | — |
| Endpoints vs TRD 19 | Script: every `METHOD /path` and `/api/v1/...` vs the E-01..E-32 table. The OpenAPI YAML was parsed with PyYAML: 32 operations, 102 schemas, no dangling `$ref`. | All match. `/alerts/{id}/acknowledge` and `/audio` appear only in "shall not exist" statements. `/openapi.json` and `/docs` are covered by API-113. `PATCH /users` refers to `/users/{id}`. | — |
| Tables/columns vs TRD 20 DDL | Script: 24 `CREATE TABLE` blocks parsed; every `table.column` token checked | All match. The two hits (`alerts.spec.ts`, `config_parameters.facility_tz`) are a file name and a config-key notation. | R3-01 (FK vs reset) |
| DDL executes | PostgreSQL 16 scratch cluster, all `sql` fences of TRD 20 | Exit 0. 17 triggers, 2 trigger functions and 61 indexes, as TRD 20:22 states. | R3-01 reproduced |
| Env vars vs TRD 21 | Script: 41 variables defined in TRD 21; every env-style token in the TRDs checked | All defined. The non-matches are error codes, report file names, workflow-only `BACKEND_URL`/`FRONTEND_URL` (TRD 25:266), the GitHub variables in TRD 21:132, and `NIGHTLY_SCHEDULER_ENABLED`, which appears only in "shall not exist" text. | R3-07 (missing role E2E variables) |
| Error codes vs TRD 05 catalogue | Script (36 codes) | All in the catalogue | — |
| Audit actions vs TRD 12 §4.12 | Script (24 actions; CHECK `^[a-z_]+(\.[a-z_]+){1,2}$`) | All named actions are in the vocabulary and pass the CHECK | R3-09 (actor type) |
| CLI command names | `grep backend.cli <cmd>` across all TRDs (14 commands) | Every command used is in TRD 15 §4.8. No stale `bootstrap-config`, `--with-input`, `load_fixture`, `test_v0_1_roster.sql` or re-activate. | R3-02, R3-03 |
| File paths | Script: backticked paths grouped by file name | Consistent: specs vs fixture copies; `frontend/`-relative and root-relative forms of the same file. Seed roster `database/seeds/test_v0_1/` and fixtures `frontend/tests/fixtures/ds07/` agree everywhere. | R3-08 |
| Function signatures | Manual | TRD 05, 06 and 07 agree; TRD 01 does not | R3-04 |
| Golden fixtures | SHA-256 and pandas | Workbook `ddbc03…2257` and CSV `78e77f…be28` match TDV-013. CSV is 283 × 30 with 2 duplicate `session_id`s. Generator is 495 lines. | — |
| Code fences / placeholders | Script / grep | Fences balanced in all 26 files. The placeholder grep hits only GIT-053. | — |
| Document structure | Script | All TRDs have Purpose, Scope, Requirements, Assumptions, Dependencies, Acceptance Criteria and Implementation Notes. The extra headings in TRD 14 and TRD 18 are template content inside fences. Versions: 0.3 for the TRDs changed in round 2, 0.2 for TRD 08, 11 and 22. | — |

---

## 6. The five checks in detail

### 6.1 Database requirements support all APIs: **PASS**

- Every endpoint E-01..E-32 reads or writes only tables and columns that exist in the TRD 20 DDL.
- The grants cover every write the API makes. The relaxed CHECKs for `processed_sessions`, `alerts_closed_ck` (now satisfied by DB-018, ANL-039 and CUS-018, which set `closed_at`) and `audit_logs_action_ck` all agree with the writers.
- The check-in log query (TRD 06:524) matches `CheckinEventType` and D-67.
- Minor: R3-09.

### 6.2 APIs support all frontend requirements: **PASS**

- All 27 aliases in TRD 04 §4.6.3 resolve to TRD 19 schemas.
- The prop types in the §4.8 inventory use only those aliases.
- `GET /config/ui` supplies the explanations and snooze hours.
- The UC-13 queue calls use one status per call.
- D-67 removed the only round-2 FE/API conflict.
- No findings.

### 6.3 Analytics requirements support all business requirements: **PASS**

Workbook re-verification (SRC-03 read with `python3 -I` and pandas, `dtype=object`). Every value below matches the TRDs:

| Quantity | Value |
|---|---|
| Annotated_sessions statuses | usable 267, set_aside 12, quarantined 2, duplicate 2, missing_resident 17, missing_device_gap 2 (missed tile 19; funnel 300/281/269/267) |
| Per-resident counts | R02 24/0/0/6, R03 22/7/0/1, R05 28/0/2/0, R08 13/5/0/12, others 30/0/0/0 (Main.dc.html and OAS-021 agree) |
| Baselines | 180 rows; floor applied in 8, all `number_of_pauses` |
| Scores | 98 total: R01 14, R02 8, R03 6, R04 14, R05 12, R06 14, R07 2, R09 14, R10 14 |
| Alarm states | off 81, on 15, RINGS 2. First alarms R09-20261021-01 and R10-20261024-01. Final tallies 26.8 (R09) and 13.4 (R10), as in Alerts.dc.html, E2E-17 and FE-193. |
| Resident outcomes | R07 epoch 1 has 12 usable (no baseline); epoch 2 on D07B has 18, frozen after R07-20261028-01, 2 scored. R08 has 13 usable, no baseline. |
| Parameters sheet | Noise −40, speech 1 s, baseline 16, MAD × 1.4826, pause floor 0.5, composite floor 0.1, k 0.5, h 5.0, morning < 12, screen ≥ 5 prior with \|F0 z\| ≥ 4 and 2 features ≥ 3. Matches TRD 20 §4.11 and TRD 07 §4.7. |
| Last check-in order | From SRC-05: R02, R07, R05, R10, R06, R08, R09, R03, R04, R01 (E2E-06) |

- Parameter changes, which were the round-2 gap, now have one defined path: `set-config`, then `rebuild` (D-69, ANL-032, CUS-034).
- Data-alert reconciliation is one model (DB-036 / ANL-060).
- Configuration failure handling is one rule (ENV-021 / ANL-031 / ANL-052).
- Minor: R3-04 (TRD 01 signature) and R3-05 (`features` key).

### 6.4 Testing requirements validate all critical functionality: **PASS**

- Every BR has TST, TDV or MVP coverage.
- The workbook tiers (TDV), the required E2E and a11y checks, and the new-admission tests (TST-185, TST-186) are in place.
- DA-02 now uses the inclusive day count.
- `e2e.yml` loads DS-10 for E2E-20.
- Minor: R3-06 (no 5 s test), R3-07 (role credentials for E2E), R3-08 (overlay fixture), R3-10 (priority).

### 6.5 Deployment requirements support the architecture: **FAIL**

- The architecture follows `Deployment_Architecture.md`: monorepo, Next.js on Netlify, FastAPI on Railway, Neon/Railway PostgreSQL, GitHub Actions, and the AWS target (Amplify, App Runner, RDS).
- The analytics engine is the root `analytics/` package deployed with the backend (D-61).
- Migrations run only as the pre-deploy step (D-58). The nightly service gets an explicit variable list. The AWS scheduler records `nightly` runs (D-70, API-065).
- Fails on R3-01: the staging re-seed command cannot run.
- Minor: R3-02 (migrator command list) and R3-03 (trigger tables).

---

## 7. Recommended fixes (not applied)

In priority order:

1. **R3-01:** in TRD 15 §4.8, DB-056/DB-057 and PGS-019, define `seed --reset`:
   - run `SET ROLE echowell_migrator` and `SET LOCAL echowell.allow_purge = on`;
   - give an explicit truncate/delete order that respects `api_keys → devices`, and add `seed --reset` to the PGS-019 list;
   - make user and API-key creation "create if missing; never print existing credentials";
   - require `SET ROLE` for every migrator CLI command in TRD 20 §4.3.
2. **R3-02:** add `set-config` and `load_evaluation_ground_truth.py` to TRD 20 §4.3, the TRD 12 role table and SEC-111, which feed the DEP-040 import-boundary allow-list.
3. **R3-03 and R3-04:** finish the TRD 01 and TRD 23 parts of D-70 and of the binding `run_pipeline` signature; decide the trigger value of the seed's run.
4. **R3-05:** decide whether `features` is a configuration key, and align ANL-058, ANL-029, DB-055 and TRD 20 §4.11.
5. **R3-06 to R3-10:** add the NFR-011 timing test or the demo tolerance; add role E2E users and smoke-user provisioning; define the overlay fixture and add DS-10 to the tree; fix the `user.created` actor type; align the DB-025 priority.

---

## 8. Prior findings status

### 8.1 Round-2 findings (R2-01..R2-26)

| ID | Round-2 severity | Subject | Status | Evidence (round 3) |
|---|---|---|---|---|
| R2-01 | Major | Check-in log vs new usable check-in | Resolved | D-67 (TRD 24:230); FR-184, SC-03, AC-VIS-03, NFR-011, TST-181 and E2E-15 assert last check-in, the 30-day count and the tally bar. UX-144, TRD 19 enum, TRD 06:524 and the wireframe agree. No remaining "appears in the check-in log" wording. |
| R2-02 | Major | Seed meaning and roster format | Resolved | D-68. DB-056/DB-058, TRD 15:385, TRD 16:350/390, TRD 20 §4.12 (CSV only), TRD 14 DS-07, TRD 13:117 and TRD 13:550 agree. No `--with-input`, SQL roster or `load_fixture` remains. (`--reset` is a separate new defect: R3-01.) |
| R2-03 | Major | No parameter-change mechanism; calibration vs ANL-032 | Resolved | `set-config` row (TRD 15:386), D-69, FR-229, FR-250, NFR-084, ANL-032, ANL-055, CUS-034 (set-config then rebuild), TST-053, SEC-103, TRD 21:105, TRD 23:470. Regressions R3-02 and R3-05 were introduced. |
| R2-04 | Minor | FE-041 CSP nonce | Resolved | FE-041 sets Cache-Control only; FE-060 defers the nonce |
| R2-05 | Minor | Nightly vars; TRD 25 migration command | Resolved | TRD 15:262 explicit list; TRD 25:200 and 25:266 use root `alembic.ini` and the pre-deploy step |
| R2-06 | Minor | `pipeline.py` "CLI"; `aggregates.py` lists | Resolved | TRD 07:94; TRD 01:280, 01:440; TRD 25:186, 25:219 |
| R2-07 | Minor | TRD 17 diagram; `counts` example; `request_id` | Resolved | TRD 17:207 per-resident; TRD 23:699 has 12 keys; TRD 17:129 "never in pipeline_runs.counts" |
| R2-08 | Minor | ING-030 trigger on `ingest_rejections` | Resolved | ING-030 says grants only (PGS-021) |
| R2-09 | Minor | DA-02 boundary | Resolved | TRD 13:238 gives 15 < 16 and a 16 ≥ 16 companion case |
| R2-10 | Minor | Rollback key re-activation; dedupe wording | Resolved | TRD 15:439 uses `create-api-key`; ARC-061, ANL-045, TST-052, API-061 and DEP-047 all say "running or succeeded" |
| R2-11 | Minor | Data-alert re-detection model | Resolved | ANL-060 defers to DB-036 (new row, run `as_of`, never reopened) |
| R2-12 | Minor | Invalid config handling | Resolved | ENV-021, ANL-031 and ANL-052 agree |
| R2-13 | Minor | OQ-05 note text | Resolved | FR-195 = UX-125 verbatim |
| R2-14 | Minor | Component names; aliases | Resolved | TST-090 uses TRD 04 §4.8 names; aliases at TRD 04:359–360 |
| R2-15 | Minor | ANL-044 batch scope | Resolved | ANL-044 cites API-053 (co-assigned residents) |
| R2-16 | Minor | Engine call shape | **Partially resolved** | TRD 05:475 and TRD 06:434 fixed; TRD 01:135 and 01:441 still differ (R3-04) |
| R2-17 | Minor | `closed_at` on close | Resolved | CUS-018, DB-018 and ANL-039 set `closed_at` = run `as_of` |
| R2-18 | Minor | DS-10 in e2e.yml; staging seed vars | Resolved | TRD 16:351; TRD 16:390 + ENV-053 |
| R2-19 | Minor | Fixture generator/path | Resolved | `npm run fixtures:capture` → `frontend/tests/fixtures/ds07/` (TRD 04:596/633, TDV-016) |
| R2-20 | Minor | Lighthouse CI version | Resolved | 0.14.x in CIC-116 and TRD 13 |
| R2-21 | Minor | Linear history vs merge commits | Resolved | GIT-010: linear history on `staging` only |
| R2-22 | Minor | Production smoke login | Resolved | TST-152: production smoke is unauthenticated (DEP-081) |
| R2-23 | Minor | UC-13 status filter | Resolved | Two single-value calls (TRD 02:543) |
| R2-24 | Minor | Single-record ingest audit | Resolved | API-032, TRD 01:132: not audited |
| R2-25 | Minor | AWS nightly trigger | **Partially resolved** | D-70, API-065, DEP-116 and TRD 01:380 fixed; TRD 01:307 and TRD 23:253 still map scheduler/POST calls to `manual` (R3-03) |
| R2-26 | Minor | New-admission tests | Resolved | TST-185, TST-186 (priority mismatch is R3-10) |

Totals: Resolved 24, Partially resolved 2, Not resolved 0.

### 8.2 Round-1 findings that were partially resolved after round 2

| ID | Round-1 severity | Subject | Status | Evidence (round 3) |
|---|---|---|---|---|
| F-03 | Critical | Parameter change needs a forbidden baseline delete | Resolved | D-56 + D-69: `set-config` then `rebuild` (migrator); CUS-034 no longer prescribes a manual `scope=all` run |
| F-05 | Major | One transaction per run vs per resident | Resolved | TRD 17:207 diagram is per-resident (D-63); LOG-061 agrees |
| F-14 | Major | CSP and Railway hostnames | Resolved | FE-041 has no nonce; static CSP of TRD 12 §4.9 only |
| F-16 | Major | Migrator credential on web service | Resolved | D-58; nightly gets no migrator URL (TRD 15:262); TRD 25 uses the pre-deploy step |
| F-32 | Minor | Stage count / module lists | Resolved | TRD 07:94 and module lists in TRD 01/25 include `aggregates.py` |
| F-37 | Minor | `baseline_stalled` off-by-one | Resolved | DA-01/DA-02 use the inclusive count |
| F-41 | Minor | `pipeline_runs` JSON shapes | Resolved | TRD 23:699 has 12 keys; `request_id` is not in `counts` |
| F-42 | Minor | Trigger names | Resolved | ING-030 says grants only for `ingest_rejections` |
| F-49 | Minor | Key deactivation, nightly dedupe | Resolved | `revoke-api-key` / `create-api-key`; one dedupe condition |
| F-52 | Minor | `is_morning`; DS-01 vs DS-07; DB-056 | Resolved | Single roster source `database/seeds/test_v0_1/` (D-68) |

Totals: Resolved 10, Partially resolved 0, Not resolved 0. The other 45 round-1 findings were already resolved in round 2. Spot checks found no regression in them.
