# TRD Validation Report (Phase 1, round 4)

| Field | Value |
|---|---|
| Scope | `specs/TRD/00`–`25`, checked against `specs/prompts/TRD_Generation_Prompt.md`, `specs/architecture/Deployment_Architecture.md`, `specs/UI-wireframe/*.dc.html` (5 files), `specs/business-requirements/*`, `specs/data-samples/*`, `specs/algorithm/generate_pipeline_test_v0_1.py` |
| Checklist | `specs/prompts/TRD_Implementation_Audit_Checklist.md` Phase 1, and the definition of done in TRD 25 §Phase 1 |
| Round | 4. This report replaces round 3 (10 findings, R3-01..R3-10), after the round-3 fixes listed in `docs/reports/TRD_VALIDATION_FIXES.md` were applied. |
| Branch | `trd-generation`. Read only: no file under `specs/` was changed and no git command was run. |
| Date | 2026-10-19 |

**How locations are written.** `TRD NN:line` means line `line` of `specs/TRD/NN_*.md`. For example, `TRD 15:385` is line 385 of `specs/TRD/15_Deployment_and_DevOps_Spec.md`.

**Severity scale** (the same as rounds 1–3):

| Severity | Meaning |
|---|---|
| Critical | Built as written, the system would be wrong or unsafe: a core path fails at runtime, or two binding rules cannot both hold. |
| Major | An ambiguity or conflict that an implementer would probably resolve the wrong way, or a mandated path or check that cannot work as specified. |
| Minor | A real inconsistency or error that a careful implementer would still resolve correctly. |

**Numbering.**
- New findings in this round are R4-01, R4-02, and so on.
- Earlier findings keep their numbers: R3-nn from round 3 (section 8).

---

## 1. Summary

**Verdict: FAIL.** The verdict rule is FAIL if any Critical or Major finding remains. Two Major findings remain, and both concern the database/deployment path that the round-3 fix (D-71) relies on:

- **R4-01 (Major).** The D-71 staging re-seed contradicts two Must rules that were not updated:
  - DB-029 (TRD 06:475) says `downgrade()` is "executed only in local and test environments" and that staging migrations are forward-only.
  - DEP-060 (TRD 15:366) says schema changes reach staging only through the Railway pre-deploy `alembic upgrade head`, and "no manual DDL shall be run against staging".
  - D-71, DB-024, DEP-071, DEP-074 and TRD 16 step 4 run `alembic downgrade base` + `upgrade head` against staging from GitHub Actions on every migration or `analytics/**` push.
- **R4-02 (Major).** On a database provisioned as the TRDs specify, migration 0001 cannot run as `echowell_migrator`. This was reproduced on PostgreSQL 16.
  - PGS-002 puts `CREATE EXTENSION pgcrypto` and `btree_gist` in migration 0001, and Alembic runs as `echowell_migrator` (DB-028, TRD 20 §4.3).
  - The provisioning script (TRD 20:112–118, TRD 15:146–151) creates only roles and the schema owner. It neither creates the extensions nor grants `CREATE` on the database.
  - Result: `ERROR: permission denied to create extension "pgcrypto"`. This breaks Compose start-up (TRD 15:185), `backend-test` (CIC-015), `e2e.yml`, and the D-71 downgrade/upgrade cycle if the 0001 downgrade drops the extensions.
  - The round-3 PostgreSQL verification of D-71 missed this, because the extensions had been created beforehand as the superuser.

The round-3 fixes mostly held:
- **R3-01..R3-10:** 7 resolved and 3 partly resolved (R3-01, R3-02, R3-08). There are no unresolved items.
- **D-71 itself is executable.** With the extensions present, drop-all as `echowell_migrator` followed by the DDL again succeeds: exit 0, 24 tables, 17 triggers, 46 `config_parameters` rows, grants restored.
- **The rest of the TRDs still describe the old design.** The R3-01 parts that remain are the stale "truncates" clause in the TRD 15 `seed` row and the stale DB-029/DEP-060 rules.

| Severity | Count |
|---|---|
| Critical | 0 |
| Major | 2 |
| Minor | 7 |
| **Total new (round 4)** | **9** |

Prior findings:

| Set | Resolved | Partially resolved | Not resolved |
|---|---|---|---|
| R3-01..R3-10 (10) | 7 | 3 (R3-01, R3-02, R3-08) | 0 |

Phase 1 checks:

| # | Phase 1 check | Result | Key evidence |
|---|---|---|---|
| 1 | Database requirements support all APIs | **PASS** | All 24 tables, 15 enums, CHECKs, indexes and grants support E-01..E-32. The TRD 20 DDL runs as superuser with exit 0 (17 triggers, 2 trigger functions, 23 + 23 config rows). Minor: R4-06 (API-key scope cardinality), R4-09. The provisioning defect R4-02 is counted under check 5. |
| 2 | APIs support all frontend requirements | **PASS** | All 32 endpoints are in the TRD 19 table and YAML. Every `/api/v1` path used in the TRDs resolves. No frontend item lacks an API source. |
| 3 | Analytics requirements support all business requirements | **PASS** | Every workbook figure was re-verified with pandas (section 6.3). R3-04 and R3-05 are fixed. |
| 4 | Testing requirements validate all critical functionality | **PASS** | Every BR has TST/TDV/MVP coverage. NFR-011 now has TST-187. Minor: R4-04 (DB-024 test oracle), R4-05 (E2E-15/TST-187 overlay and isolation). |
| 5 | Deployment requirements support the architecture | **FAIL** | R4-01 (staging reset vs DB-029/DEP-060), R4-02 (migrations cannot create extensions as migrator). Minor: R4-03, R4-07, R4-08. |

TRD 25 §Phase 1 definition of done:

| Criterion | Result | Evidence |
|---|---|---|
| Every BR-01..BR-18 maps to at least one TRD requirement and test | **Met** | Section 2.1. Each BR is cited by 25–269 requirement rows across 10–24 TRDs. The BR→FR table at TRD 02:574–591 covers all 18. |
| Every OQ/ASM/RSK/DSC/D ID used in the TRDs exists in TRD 24 | **Met** | IDs used: ASM-01..08, DSC-01..14, OQ-01..26, RSK-01..15, D-01..D-71, all defined in TRD 24. `OQ-27`, `RSK-16` and `D-72` appear only as "next free" text at TRD 24:262. The stated ranges agree (TRD 24:16 "D-01 to D-71"; AGT-002 "D-01..D-71"). |
| Each of the five checks has a pass/fail line with evidence | **Met** | The table above and section 6 |
| No TRD file modified | **Met** | Read-only run |
| `grep -rnE "T[B]D\|T[O]DO\|l[o]rem" specs/TRD` returns nothing | **Met in substance** | The only hit is GIT-053 (TRD 18:219), the rule that forbids these words. The same hit was accepted in rounds 1–3. |

---

## 2. Requirements Traceability Matrix

### 2.1 Business requirements → TRD requirements → tests

Counts are scripted. A row is counted when its first cell is a requirement ID and it cites the BR, either directly or through a range. The restatement tables (BR, SRC, OQ, ASM, RSK, DSC) are left out.

| BR | Summary (TRD 00) | Rows / TRDs | Key FRs (TRD 02 §4.28) | Tests / MVP criteria | Gap (round 4) |
|---|---|---|---|---|---|
| BR-01 | Ingest feature records, never audio | 80 / 20 | FR-001–FR-005, FR-020–FR-028, FR-184, FR-321 | TST-030, TST-043, TST-045, TST-046, TST-133, TDV-031, TDV-090, MVP-02 | — |
| BR-02 | Keep raw records unaltered | 101 / 17 | FR-005–FR-007, FR-010, FR-028, FR-223, FR-296 | TST-037, TST-041, TST-043, TDV-002, TDV-050, TDV-054, MVP-02, MVP-12 | Reset wording: R4-03 |
| BR-03 | Drop duplicates, keep first arrival | 40 / 13 | FR-008, FR-011, FR-029–FR-031, FR-182, FR-316 | TST-020, TST-044, TST-046, TDV-054, MVP-01, MVP-03 | — |
| BR-04 | Set aside poor-quality sessions | 28 / 13 | FR-024, FR-040–FR-044, FR-181, FR-290 | TST-020, TDV-053, MVP-01, MVP-03 | — |
| BR-05 | Quarantine wrong-speaker sessions | 27 / 10 | FR-060–FR-065, FR-074, FR-292 | TST-020, TDV-055, MVP-01, MVP-03 | — |
| BR-06 | Log missing days honestly | 69 / 15 | FR-120–FR-125, FR-135, FR-153, FR-154, FR-294, FR-295 | TST-020, TDV-052, TDV-053, TDV-064, TDV-068, MVP-01 | — |
| BR-07 | Remove morning offset | 26 / 11 | FR-070–FR-074, FR-171 | TST-020, TDV-056, MVP-01 | — |
| BR-08 | Epochs; restart baseline | 34 / 12 | FR-050–FR-053, FR-132, FR-155, FR-172 | TST-020, TDV-057, MVP-01 | — |
| BR-09 | Robust personal baseline, frozen | 55 / 15 | FR-080–FR-086, FR-162, FR-163, FR-205, FR-229, FR-230 | TST-020, TST-184, TDV-051, TDV-058, TDV-060, MVP-01 | — |
| BR-10 | Signed z and composite | 25 / 11 | FR-090–FR-095, FR-169, FR-170, FR-266 | TST-020, TDV-051, MVP-01 | — |
| BR-11 | CUSUM persistent-deviation flag | 61 / 14 | FR-100–FR-110, FR-165–FR-167, FR-261–FR-265, FR-300 | TST-020, TDV-059, TDV-060, TDV-067, MVP-01, MVP-13 | — |
| BR-12 | Residents overview | 92 / 17 | FR-130–FR-140, FR-150–FR-156, FR-312, FR-330 | TST-033, TST-090, TST-110, TST-181, TST-187, TDV-062, TDV-066, MVP-04 | TST-187 run setup: R4-05 |
| BR-13 | Resident detail page | 113 / 15 | FR-160–FR-173, FR-180–FR-184, FR-190–FR-195, FR-260–FR-280 | TST-090, TST-093, TST-110, TST-181, TST-187, TDV-066, MVP-05, MVP-13 | E2E-15 setup: R4-05 |
| BR-14 | New-admission arm (Should) | 32 / 10 | FR-200–FR-207, FR-331 | TST-090, TST-185, TST-186, MVP-06 | — |
| BR-15 | Reproduce workbook R01–R10 | 166 / 22 | FR-240–FR-245, FR-310–FR-323 | 41 TST/TDV/MVP rows (TST-005, TST-022, TST-048, TST-070, TDV-001, TDV-013, …) | Staging re-seed vs DB-029: R4-01; CI migrations: R4-02 |
| BR-16 | Data protection, roles, audit | 269 / 24 | FR-210–FR-221, FR-226–FR-229, FR-250–FR-254 | TST-007, TST-032, TST-041, TST-053, TST-130, TDV-006, TDV-007, MVP-07 | R4-06, R4-07, R4-08 |
| BR-17 | Monorepo deploy on Netlify/Railway/Neon/GHA | 74 / 15 | FR-253, FR-254 | TST-001, TST-150, TST-170, MVP-08 | R4-01, R4-02 |
| BR-18 | Detection not diagnosis, no LLM/ML | 47 / 15 | FR-164, FR-277, FR-278, FR-298 | TST-096, TST-097, TST-170, MVP-09 | — |

### 2.2 Frontend requirements (TRD_Generation_Prompt) → UX / FE IDs

Every item in the prompt's "Frontend Requirements" list was traced again to TRD 11 (UX), to the TRD 04 §4.8 components and to a test.

| Prompt frontend item | UX IDs | FE components (TRD 04 §4.8) | Tests | Round-4 note |
|---|---|---|---|---|
| Three primary views (overview, detail, new admissions) and the two added views | D-23; TRD 11 §4.3, §4.5, §4.7, §4.17, §4.18 | Residents page, Resident detail page, AdmissionsTable, AlertsPage, AnalyticsPage | E2E-03..E2E-21, TST-110 | — |
| All enrolled residents; sort by alarm, resident ID, last check-in | UX-020–UX-033, UX-261 | ResidentsTable, SortSelect | E2E-04, E2E-05, E2E-06 | — |
| Statuses Alarm On / No Alarm / Baseline Still Forming | §4.3.4, UX-036 | StatusBadge | E2E-04 | — |
| 30-day used, set aside, quarantined, missed; missing days never backfilled | UX-039, UX-047, UX-048 | ResidentsTable, SummaryTiles | E2E-03, E2E-04, OAS-021 | E2E-03 tile counts can be polluted by E2E-15/TST-187 (R4-05) |
| Device panel: assigned, shared, silent periods, days with no activity | UX-050–UX-058, UX-263 | DevicePanel, DeviceCell | E2E-07 | — |
| CUSUM tally with alarm line 5.0, baseline period, alarm trigger and persistence | UX-080–UX-092 | CusumChart, CusumTable | TST-093, E2E-08 | — |
| 7 scored measurements in plain language; 12 others stored, not scored | UX-100–UX-108 | FeatureCard (×7), Sparkline, OtherMeasurementsCard | E2E-08, TST-090 | — |
| Baseline status, progress, freeze indicator | UX-060–UX-066 | ResidentHeader, WhatThisMeans | E2E-08, E2E-10, E2E-11 | — |
| Check-in log: alarms, set-asides, quarantines, missed days, baseline restarts | UX-140–UX-149 | CheckinLog | E2E-10, E2E-11, E2E-12, E2E-15 | — |
| Staff notes: observations, actions, follow-up | UX-120–UX-135 | StaffReviewForm, NotesList, ReviewDialog | E2E-09 | — |
| New admissions: facility comparison, move to main list, "future/experimental" | UX-181–UX-195 | AdmissionsTable, FacilityRangeChart, ExperimentalBanner | E2E-13, TST-185, TST-186 | — |
| Alert review (SRC-18) | UX-300–UX-331 | AlertQueue, AlertCard, DataAlertQueue, AlertReviewPanel, AlertReviewForm | E2E-17, E2E-18, E2E-19 | Role logins now defined (D-71, CIC-034) |
| Analytics (SRC-19) | UX-351–UX-384 | KpiTiles, DailyCheckinsChart, LossFunnel, UsableByResidentChart, AlarmTimingTable, ReviewOutcomesTable | E2E-20, E2E-21, TDV-074 | — |
| Loading, empty and error states; accessibility; responsive; plain language | UX state rows, FE-145, NFR-060, VIS-003..005 | SectionState | TST-090, TST-110, E2E-16, TST-097 | — |

Result: every prompt item maps to UX and FE IDs and to at least one test. No frontend item lacks an API source.

### 2.3 Wireframes → UX sections

Key strings of all five wireframes were extracted again and compared with TRD 11 and the TRD 14 tables.

| Wireframe | UX section | Coverage |
|---|---|---|
| `Main.dc.html` (SRC-09) | TRD 11 §4.3, §4.4, §4.13 | Complete. Tiles 2/7/1/19, per-resident counts and the D02/D07B device lines match (section 6.3). |
| `Resident.dc.html` (SRC-10) | TRD 11 §4.5 | Complete. The "Baseline complete" and alarm log lines match UX-142 and D-67. |
| `Admission.dc.html` (SRC-11) | TRD 11 §4.7 | Complete. The wireframe banner "Not in pipeline test v0.1 — …" is line 2 of UX-181. Line 1, "▲ Future / experimental study arm", is an intended addition. |
| `Alerts.dc.html` (SRC-18) | TRD 11 §4.17 | Complete. "open 9 days", "tally 26.8", "Alerts (2)" and "silent all day" match. |
| `Analytics.dc.html` (SRC-19) | TRD 11 §4.18 | Complete. 281/300 and 267/300 match TDV and E2E-20. |

### 2.4 Items with no test or only a weak test

| Item | Status |
|---|---|
| NFR-011 / SC-03 "within 5 s" | TST-187 (Must) now tests it, but the E2E job has no step that loads the overlay roster it depends on (R4-05). |
| E2E-15 "isolated DB" | No isolated database exists in `e2e.yml`; it shares the seeded stack with E2E-03/E2E-04 (R4-05). |
| Fresh-database migration as `echowell_migrator` (TST-040, CIC-015) | Cannot pass as specified (R4-02). |
| `reset-test-db` audit row | The DB-024 test oracle contradicts its own text (R4-04). |

---

## 3. Missing Requirements

| ID | Severity | Where it is needed | What is missing |
|---|---|---|---|
| R4-02 | Major | `database/roles/provision_login_roles.sql` (TRD 20 §4.3 at 20:112–118; TRD 15:146–151), the Neon/RDS provisioning steps (TRD 15:228), migration 0001 (PGS-002, TRD 20:59, 20:106–107) | Who creates `pgcrypto` and `btree_gist`. Either the provisioning step creates them as superuser (and the 0001 downgrade never drops them), or it grants `CREATE ON DATABASE` to `echowell_migrator`. Neither is stated. |
| R4-05 | Minor | `e2e.yml` (TRD 16:347–365), CIC-030 (16:376), E2E-15 (13:376), TST-187 (13:512) | A workflow step that runs `import-master-data --dir tests/fixtures/seeds/demo_overlay`, and a definition of the "isolated DB" for E2E-15 (a separate stack, or test ordering), so that E2E-03/E2E-04 still see 10 residents and tiles 2/7/1/19. |

---

## 4. Contradictions

### 4.1 Major

**R4-01 · Major · The D-71 staging reset contradicts DB-029 and DEP-060**

What the round-3 design requires:
- D-71 (TRD 24:234), DB-024 (TRD 06:465), the TRD 15 `reset-test-db` row (15:390), DEP-071 (15:397), DEP-074 (15:400), TRD 16 deploy-staging step 4 (16:395) and CIC-041 (16:402) all work the same way. `seed test_v0_1 --reset` runs `alembic downgrade base` then `alembic upgrade head` against the **staging** database. It does this from a GitHub Actions runner, through `STAGING_DATABASE_URL`, on every staging push that touches `backend/alembic/**` or `analytics/**`.
- `reset-test-db` explicitly accepts APP_ENV `staging`.

What other binding rules say:
- **DB-029 (TRD 06:475, Must).** "Staging and production migrations shall be forward-only; `downgrade()` shall be implemented for every revision but executed only in local and test environments."
- **DEP-060 (TRD 15:366, Must).** "Database schema changes shall be applied only by Alembic (`alembic upgrade head`) as the Railway pre-deploy command …; no manual DDL shall be run against staging or production."
- DEP-086 (TRD 15:444) limits the downgrade ban to production only. This shows that the authors meant to allow staging downgrades, but DB-029 and DEP-060 were not updated.

Impact:
- DB-029 and DB-024 are both Must rows in the same TRD, ten lines apart, and they cannot both hold.
- An implementer who enforces DB-029 makes the guard in `env.py` or the CLI refuse a downgrade when `APP_ENV=staging`. A natural way to do that is to allow only `local` and `test`. The staging re-seed then fails on every migration push, which is exactly the R3-01 outcome.
- An implementer who follows D-71 knowingly breaks two Must rows. The DB-029 PR-checklist inspection and the DEP-060 review would then flag the deploy-staging workflow.

Recommendation:
- Amend DB-029: "never executed in production; in staging only by `reset-test-db` (D-71)".
- Amend DEP-060: the staging test-database reset of D-71 is the only exception to the pre-deploy rule.
- Cite D-71 from both rows.

**R4-02 · Major · Migration 0001 cannot create its extensions as `echowell_migrator` on a database provisioned as specified**

What the TRDs require:
- PGS-002 (TRD 20:59). The schema (migration 0001) creates `pgcrypto` and `btree_gist`, using the DDL at TRD 20:106–107.
- DB-028 (TRD 06:474) and TRD 20 §4.3 (20:129). Alembic connects with `DATABASE_MIGRATION_URL` and runs `SET ROLE echowell_migrator`.
- Provisioning (TRD 20:112–118, TRD 15:146–151). The local/CI script creates the three group roles, makes `echowell_migrator` owner of schema `public`, and creates the login roles. Nothing more.
  - The database itself is owned by the superuser (`POSTGRES_USER: echowell`, TRD 15 Compose outline; CI service container, TRD 16:195–216).
  - No step creates the extensions, and no step grants `CREATE` on the database.
- TRD 20:1144 says only that the managed service lets "the project owner role" create extensions. Migrations do not run as that role.

Reproduced on PostgreSQL 16.15 with a scratch cluster and the script `/tmp/claude-0/-home-user-echowell/06d21bae-4975-509b-846a-5a1512c441c2/scratchpad/t_r4_ext.sh`:
1. A fresh database was provisioned exactly as above, with roles and schema owner only.
2. All `sql` fences of TRD 20 were run after `SET ROLE echowell_migrator`. Result: `ERROR: permission denied to create extension "pgcrypto"` / `HINT: Must have CREATE privilege on current database`, exit 3, 0 tables.
3. Run as the superuser, or after the superuser had created the extensions, the same DDL exits 0. The round-3 D-71 verification (`t_downgrade.sh`) pre-created the extensions as the superuser, so it did not catch this.

Impact:
- The paths that fail at their first step are:
  - the Compose backend start-up command `alembic upgrade head` (TRD 15:185), so every local stack fails;
  - `backend-test` (CIC-015; TRD 16:217–218);
  - `e2e.yml` (`--wait` on the backend);
  - TST-040.
- If the 0001 `downgrade()` symmetrically drops the extensions, which TRD 06 DB-029 and NFR-086 make likely, D-71's reset also fails on re-upgrade in every environment where the migrator lacks `CREATE` on the database.
- On Neon and RDS the outcome depends on privileges that the TRDs do not state.

Recommendation:
- Make the provisioning step (script and console procedure) create both extensions as superuser/owner.
- State that 0001 uses `CREATE EXTENSION IF NOT EXISTS` and that its downgrade never drops extensions.
- Alternatively, grant `CREATE ON DATABASE` to `echowell_migrator`. Choose one option and state it in TRD 20 §4.2/§4.3, TRD 15 §4.2/§4.4 and PGS-002.

### 4.2 Minor

| ID | Location (A vs B) | Description and evidence | Recommendation |
|---|---|---|---|
| R4-03 | TRD 15 `seed` row (15:385); TRD 20 §8 (20:1192); TRD 25 Phase 4 outputs (25:197) vs D-71, DB-024, TRD 15 `reset-test-db` row (15:390), DEP-071, PGS-019 | **Residue of R3-01.** The `seed test_v0_1 [--master-only] [--reset]` row still ends with "`--reset` truncates all tables except `users`, `api_keys`, `audit_logs` and `config_parameters` first". This is the design R3-01 showed cannot run. Its meaning also differs from D-71, under which users, keys and audit rows are removed. Five lines later, the `reset-test-db` row says `seed --reset` = downgrade/upgrade + seed. Two more places keep the old wording. TRD 20:1192 tells tests to truncate `raw_sessions` "through the purge path (PGS-019)", but PGS-019 now reserves that path for the IRB purge. TRD 25:197 says "`--master-only` loads the roster only", whereas DB-058 and D-68 say roster, users and key, and it says "users and the API key generated by the seed command" although they are upserted from SEED_*. | Replace the `--reset` clause of the seed row with "see `reset-test-db`" (D-71). Reword TRD 20:1192 to "tests use a fresh database from the migrations; never truncate `raw_sessions`". Align TRD 25:197 with DB-057/DB-058. |
| R4-04 | DB-024 verification cell (TRD 06:465) vs DB-024 text, DEP-071 (15:397) | The DB-024 text says `reset-test-db` "then writes one `audit_logs` row `seed.reset`". Its verification expects "24 empty tables except `config_parameters` (46 rows)", which also requires `audit_logs` to be empty. A test written from the cell would fail against a correct implementation. | Expect `config_parameters` 46 and `audit_logs` 1 (`seed.reset`), with every other table empty. |
| R4-05 | `e2e.yml` (TRD 16:347–365) and CIC-030 (16:376) vs E2E-15 (13:376), TST-187 (13:512), TST-100 (13:355), E2E-03/E2E-04 (13:364–365) | **Residue of R3-08.** The overlay is now a CSV directory (TRD 13:117–120). However, `e2e.yml` and CIC-030 seed only `seed test_v0_1` plus DS-10, and never run `import-master-data --dir tests/fixtures/seeds/demo_overlay`. E2E-15 and TST-187 (Must, "in the E2E job") would therefore POST for an unknown resident R11 and get a 422. E2E-15 asks for "an isolated DB", but the job has a single Compose stack, and TST-100 requires every scenario on every PR. Once R11 is added, the overlay changes "Baseline still forming" from 1 to 2 and the row count from 10 to 11, which E2E-03 and E2E-04 assert. E2E-19 ("isolated stack", server clock +24 h) has the same isolation gap. | Add the overlay step, and run E2E-15, TST-187 and E2E-19 in a separate job or stack (or as a last serial project). State this in CIC-030 and TRD 13 §8. |
| R4-06 | SEC-022 (TRD 12:112, "exactly one scope"), SEC-020 (12:110, single `--scope`) vs DB-057 (06:593), TRD 20:1058, TRD 21:85, D-71 (24:234), PGS-035 and `api_keys_scopes_ck` (20:92, 20:340, "non-empty subset") | The seeded key `test-ingest` carries two scopes (`ingest:write`, `pipeline:run`). TRD 12 says every key carries exactly one scope, while the TRD 20 CHECK accepts one or two. | Either relax SEC-022 to "a non-empty subset" (and allow repeated `--scope`), or seed two keys. |
| R4-07 | DB-057 (TRD 06:593, "No credential shall be committed to the repository"), SEC-050 (12:191, SEED_* stored only in platform secret stores) vs `.env.development.example` (TRD 21:167–170) | **Introduced by R3-07.** The committed local template contains `SEED_ADMIN_PASSWORD=local-dev-only-Admin-1` … and `SEED_INGEST_API_KEY=ewk_local-dev-only-…`, which are credentials of real seeded rows. The same pattern already exists for JWT_SECRET and the login-role passwords, but DB-057 and SEC-050 state no exception for local-only values. | Add an explicit exception for "local-only throwaway values in `.env.development.example`" to DB-057 and SEC-050 (and a gitleaks allow-list entry, CIC-115), or leave the template values empty. |
| R4-08 | ARC-019 (TRD 01:110, migrator "used only by Alembic"), TRD 05:481 ("for Alembic only"), TRD 15 §4.4 step 4 (15:228, "used by Alembic only"), TRD 06 §8 (06:661, "only by Alembic and the seed/reset/purge/rebuild CLI commands") vs the closed list in TRD 20 §4.3 (20:123), TRD 12:320, SEC-111, DEP-040 | **Residue of R3-02.** Four statements of who may use the migrator credential still leave out `set-config` and the ground-truth loader (and the first three leave out every CLI command). The binding closed list is correct, but TRD 06:661 is itself a list that an import-boundary allow-list could be built from. | Replace each with a reference to the TRD 20 §4.3 closed list. |
| R4-09 | TRD 20 §2 scope (20:22, "4 group roles") vs PGS-004 (20:61, "Exactly three group roles") and §4.3 | The scope line miscounts the roles: there are three (`echowell_migrator`, `echowell_app`, `echowell_readonly`). The other scope counts were confirmed by executing the DDL (24 tables, 15 enums, 2 trigger functions, 17 triggers). | Change to "3 group roles". |

---

## 5. Cross-Reference Validation

| Check | Method | Result | Findings |
|---|---|---|---|
| Duplicate requirement IDs | Script over the first cell of every table row in all 26 TRDs, plus list-item AC IDs | None within a file. Cross-file repeats are only the intended SRC, BR, OQ and ASM restatement tables. E-01..E-32 appear twice in TRD 19 by design. | — |
| Dangling requirement IDs | Script: 2,002 defined requirement IDs vs every reference | None dangling. AC-DB-02a is defined as list item "2a." (TRD 06:632). E2E-01..E2E-21 are defined as the first cell of Table 4.10-A (13:362–382). | — |
| OQ / ASM / RSK / DSC / D vs TRD 24 | `grep -rhoE "(OQ\|ASM\|RSK\|DSC\|D)-[0-9]{2}" specs/TRD \| sort -u` | ASM-01..08, DSC-01..14, OQ-01..26, RSK-01..15 and D-01..D-71 are all defined. `OQ-27`, `RSK-16` and `D-72` occur only at TRD 24:262 ("next free"). | — |
| E-, S-, UC-, MVP- and AC- IDs | Script | E-01..E-32, S-01..S-13, UC-01..UC-15, all MVP rows and 282 AC IDs are defined | — |
| Endpoints vs TRD 19 | Script: every `METHOD /path` vs E-01..E-32 | All match. `/alerts/{id}/acknowledge` and `/audio` appear only in "shall not exist" text. `/openapi.json` and `/docs` are covered by API-113. `PATCH /users` refers to `/users/{id}`, and `/ingest]` (TRD 14:86) is a Mermaid label. | — |
| Tables/columns vs TRD 20 DDL | Script: 24 `CREATE TABLE` blocks; every `table.column` token | All match. The non-matches are file names (`alerts.spec.ts`, `residents.csv`, `data_alerts.py`, …) and the config-key notation `config_parameters.facility_tz`. | — |
| DDL executes | PostgreSQL 16.15 scratch cluster, all `sql` fences of TRD 20 | As superuser: exit 0, 24 tables, 15 enums, 17 triggers, 2 trigger functions, 23 + 23 `config_parameters`. As `echowell_migrator` on a fresh database: fails on `CREATE EXTENSION`. With the extensions pre-created: DDL, drop-all and DDL again all exit 0, with grants restored (`echowell_app` INSERT but not DELETE on `raw_sessions`; readonly SELECT on `evaluation_ground_truth`; app none). | R4-02 |
| Env vars vs TRD 21 | Script: 45 names defined in TRD 21; every env-style token checked | All defined. The non-matches are error codes, report names, `BACKEND_URL`/`FRONTEND_URL` (TRD 25:266, workflow-local), GitHub variables listed at TRD 21:133, `RAILWAY_GIT_COMMIT_SHA` (platform), and `NIGHTLY_SCHEDULER_ENABLED` in "shall not exist" text. No `E2E_USER_*` or `STAGING_SMOKE_*` remain except the "retired" note. | R4-07 |
| Error codes vs TRD 05 catalogue | Script (36 codes) | All in the catalogue | — |
| Audit actions vs TRD 12 §4.12 | Script (24 actions; CHECK `^[a-z_]+(\.[a-z_]+){1,2}$`) | All in the vocabulary. `seed.reset`, `config.changed` and `roster.loaded` have rows (TRD 12:285–297). `user.created` and `user.updated` allow the system actor. | — |
| CLI command names | `grep -ohE "backend\.cli [a-z-]+"` (14 commands) plus `backend.jobs.nightly_run` | Every command used is in the TRD 15 §4.8 table. `backend.scripts.load_fixture` occurs only in D-68 as "no …". No `--with-input` remains. | R4-03 (stale `--reset` clause) |
| Migrator-credential users | Every list of who may read DATABASE_MIGRATION_URL | TRD 20 §4.3, TRD 12:320, SEC-111 and DEP-040 agree (6 users). ARC-019, TRD 05:481, TRD 15:228 and TRD 06:661 do not. | R4-08 |
| File paths | Script: backticked paths grouped by file name | Consistent: `database/seeds/test_v0_1/`, `tests/fixtures/seeds/demo_overlay/`, `tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv` and `frontend/tests/fixtures/ds07/` agree everywhere. `tests/fixtures/sample.wav` appears only as the negative case of AC-CIC-02. | — |
| Function signatures | Manual | The binding `run_pipeline(records, residents, assignments, config, as_of, *, frozen_baselines=None)` is quoted in TRD 01:135/442, 05:475, 06:434 and 07:213. The 5-argument forms in TRD 07:23/94/335 omit only the optional keyword. | — |
| Golden fixtures | pandas, `python3 -I` | Workbook sheets and counts as in section 6.3 | — |
| Code fences / placeholders | Script / grep | Fences balanced in all 26 files. The placeholder grep hits only GIT-053. | — |
| Document structure / versions | Script | Versions: 14 TRDs at 0.4 (changed in round 3), 9 at 0.3, 3 at 0.2 (TRD 08, 11, 22). The required section set is present in all TRDs. | — |

---

## 6. The five checks in detail

### 6.1 Database requirements support all APIs: **PASS**

- Every endpoint E-01..E-32 reads or writes only tables and columns of the TRD 20 DDL.
- The `echowell_app` grants cover every API write. The relaxed CHECKs agree with their writers: `processed_sessions`, `alerts_closed_ck` and `audit_logs_action_ck`.
- The audit vocabulary covers the new `seed.reset`, `config.changed` and `roster.loaded` actions.
- Minor:
  - R4-06: TRD 12 limits keys to one scope, but the schema and the seed use two.
  - R4-09: the scope line miscounts the group roles.
- R4-02 is a provisioning defect, not a schema defect, so it is counted under 6.5.

### 6.2 APIs support all frontend requirements: **PASS**

- All 32 endpoints are in the TRD 19 summary and the OpenAPI YAML.
- The TRD 04 §4.6.3 aliases resolve to TRD 19 schemas.
- `GET /config/ui` supplies the review explanations and snooze hours.
- No round-3 edit touched TRD 04, TRD 11 or TRD 19, and spot checks found no regression.

### 6.3 Analytics requirements support all business requirements: **PASS**

Workbook re-verification (SRC-03 read with `python3 -I` and pandas, `dtype=object`). Every value below matches the TRDs.

| Quantity | Value |
|---|---|
| Annotated_sessions `expected_status` | usable 267, set_aside 12, quarantined 2, duplicate 2, missing_resident 17, missing_device_gap 2 (missed tile 19; funnel 300/281/269/267) |
| Exp_status_counts | R02 24/0/0/6, R03 22/7/0/1, R04 30 + 2 duplicates, R05 28/0/2/0, R08 13/5/0/12, others 30/0/0/0 |
| Baselines | 180 rows; floor applied only to `number_of_pauses` (8 of 9 residents with a baseline; not R09, MAD 0.5) |
| Scores | 98: R01 14, R02 8, R03 6, R04 14, R05 12, R06 14, R07 2, R09 14, R10 14 |
| Alarm states | off 81, on 15, RINGS (first crossing) 2. Final tallies 26.83 (R09) and 13.42 (R10), as in Alerts.dc.html, E2E-17 and CIC-032. |
| Parameters sheet | baseline 16, MAD × 1.4826, pause floor 0.5, composite floor 0.1, k 0.5, h 5.0, screen \|F0 z\| ≥ 4 and 2 features ≥ 3 after ≥ 5 prior. Matches TRD 20 §4.11 and TRD 07 §4.7. |

- R3-05 is fixed. ANL-058 now says `features` is a code-level `PipelineConfig` field, changed by a reviewed code change followed by `rebuild`.
- R3-04 is fixed: TRD 01 quotes the binding signature at both places.
- No findings.

### 6.4 Testing requirements validate all critical functionality: **PASS**

- Every BR has TST, TDV or MVP coverage.
- NFR-011 and SC-03 now have the automated TST-187 (Must), and TST-181 states its 60 s demo tolerance.
- Role logins for E2E are defined: seeded users with per-job masked SEED_* values (CIC-034, Table 4.10-A note).
- DB-025 is now Must, aligned with FR-205 and TST-185.
- Minor:
  - R4-04: the DB-024 test oracle contradicts the audit row.
  - R4-05: no overlay step in `e2e.yml`, and no isolation for E2E-15, TST-187 and E2E-19.
- TST-040 and CIC-015 are also blocked by R4-02. That is counted under 6.5.

### 6.5 Deployment requirements support the architecture: **FAIL**

- The architecture follows `Deployment_Architecture.md`: monorepo, Next.js on Netlify, FastAPI on Railway, Neon/Railway PostgreSQL, GitHub Actions, and the AWS target (Amplify, App Runner, RDS).
- Migrations run as the Railway pre-deploy step (D-58), and the nightly job gets an explicit variable list.
- The D-71 reset avoids the triggers and the foreign keys. Its downgrade/upgrade cycle was confirmed on PostgreSQL 16, with the extensions present.
- The seeded credentials are deterministic and masked. Staging uses `STAGING_SEED_*`, and smoke tests log in as the seeded researcher.
- Fails on:
  - R4-01: the staging downgrade breaks DB-029 and DEP-060.
  - R4-02: a fresh local or CI database cannot be migrated as `echowell_migrator`.
- Minor: R4-03 (stale `--reset` truncate clause), R4-07 (committed local seed credentials vs DB-057/SEC-050), R4-08 (stale "Alembic only" role text).

---

## 7. Recommended fixes (not applied)

In priority order:

1. **R4-02:** decide who creates `pgcrypto` and `btree_gist`.
   - Recommended: the provisioning script and the console procedure create both extensions as superuser/owner, and migration 0001 keeps `IF NOT EXISTS` and never drops them in `downgrade()`.
   - Update PGS-002, TRD 20 §4.2/§4.3, TRD 15 §4.2/§4.4 and CIC-015.
   - Re-verify on a fresh database by running the DDL after `SET ROLE echowell_migrator`, without pre-created extensions.
2. **R4-01:** amend DB-029 (06:475) and DEP-060 (15:366) so that they allow the D-71 `reset-test-db` on staging, and cite D-71.
3. **R4-03 and R4-04:**
   - Delete the truncate clause from the TRD 15 `seed` row.
   - Reword TRD 20:1192 and TRD 25:197.
   - Fix the DB-024 verification to expect `audit_logs` = 1.
4. **R4-05:** add the overlay `import-master-data` step, and isolate E2E-15, TST-187 and E2E-19 from the scenarios that assert the R01–R10 totals (CIC-030, TRD 13 §8).
5. **R4-06 to R4-09:**
   - Settle API-key scope cardinality (SEC-022 vs PGS-035 and the seed key).
   - Add the local-template exception to DB-057 and SEC-050.
   - Point ARC-019, TRD 05:481, TRD 15:228 and TRD 06:661 to the TRD 20 §4.3 closed list.
   - Change "4 group roles" to 3.

---

## 8. Prior findings status

### 8.1 Round-3 findings (R3-01..R3-10)

| ID | Round-3 severity | Subject | Status | Evidence (round 4) |
|---|---|---|---|---|
| R3-01 | Major | `seed --reset` cannot run | **Partially resolved** | The core redesign is consistent across D-71 (24:234), DB-024 (06:465), DB-057 (06:593), PGS-019 (20:76), TRD 20 §4.3 (20:129) and §4.12 (20:1056–1060), the TRD 15 `reset-test-db` row (15:390), DEP-071 (15:397), TRD 16 step 4 (16:395), CIC-034, TRD 21:85 and TRD 25:197. It is executable once the extensions exist: drop-all as migrator, then DDL again, exits 0 with 24 tables, 17 triggers, 46 config rows and grants. What remains: the TRD 15 `seed` row still describes truncation (R4-03); DB-029 and DEP-060 still forbid the staging downgrade (R4-01); the DB-024 test oracle is inconsistent (R4-04); and the fresh-database migration as migrator fails (R4-02). |
| R3-02 | Minor | Migrator list missing `set-config` and the loader | **Partially resolved** | TRD 20 §4.3 (20:123), TRD 12:320, SEC-111 (12:327) and DEP-040 (15:298) list all six. ARC-019, TRD 05:481, TRD 15:228 and TRD 06:661 still give narrower lists (R4-08). |
| R3-03 | Minor | Trigger tables vs D-70; seed trigger | Resolved | TRD 01:308 (AWS scheduler → `nightly`), 01:309 (manual = admin JWT/CLI incl. seed), TRD 23:253, DB-058 (`manual`), ANL-046 (`test` = validation suite only) |
| R3-04 | Minor | TRD 01 `run_pipeline` signature | Resolved | TRD 01:135 and 01:442 quote the binding TRD 07 signature |
| R3-05 | Minor | ANL-058 `features` via `set-config` | Resolved | ANL-058 (07:394): code change + deploy + `rebuild`; `set-config` cannot change it |
| R3-06 | Minor | No 5 s test | Resolved | TST-187 (13:512, Must) traces NFR-011/SC-03; TST-181 keeps 60 s for the demo. Run setup gap: R4-05. |
| R3-07 | Minor | E2E role credentials; staging smoke user | Resolved | SEED_* (TRD 21:85), e2e.yml masking (16:349–354), CIC-034, Table 4.10-A note (13:358), STAGING_SEED_* (16:457, CIC-090, AC-CIC-06), DEP-080(c). Side effects: R4-06 (two-scope key) and R4-07 (committed local values). |
| R3-08 | Minor | Overlay format; DS-10 in fixture tree | **Partially resolved** | The overlay is a CSV directory in DB-060 format, loaded by `import-master-data` (13:117–120, E2E-15), and DS-10 is in `answer_key/` (13:115). `e2e.yml` and CIC-030 have no overlay step (R4-05). |
| R3-09 | Minor | `user.created` actor | Resolved | TRD 12:286–287: user (API) or system (CLI/seed) |
| R3-10 | Minor | DB-025 priority | Resolved | DB-025 (06:466) is Must |

Totals: Resolved 7, Partially resolved 3, Not resolved 0. Spot checks of the round-1 and round-2 resolutions (D-56..D-70 topics, closed_at, check-in log events, CORS, CSP, nightly variables) found no regression.
