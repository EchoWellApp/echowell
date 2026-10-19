# TRD Validation Report (Phase 1, round 2)

| Field | Value |
|---|---|
| Scope | `specs/TRD/00`–`25`, checked against `specs/prompts/TRD_Generation_Prompt.md`, `specs/architecture/Deployment_Architecture.md`, `specs/UI-wireframe/*.dc.html`, `specs/business-requirements/*`, `specs/data-samples/*`, `specs/algorithm/generate_pipeline_test_v0_1.py` |
| Checklist | `specs/prompts/TRD_Implementation_Audit_Checklist.md`, Phase 1 (and TRD 25 §Phase 1 definition of done) |
| Round | 2. This report replaces round 1 (55 findings F-01..F-55) after the fixes listed in `docs/reports/TRD_VALIDATION_FIXES.md` were applied. |
| Branch | `trd-generation` (read only; no file under `specs/` was changed; no git command was run) |
| Date | 2026-10-19 |

How locations are written: `TRD NN:line` means line `line` of `specs/TRD/NN_*.md`. For example, `TRD 06:592` is `specs/TRD/06_Database_Design_TRD.md` line 592.

Severity scale (unchanged from round 1):

| Severity | Meaning |
|---|---|
| Critical | Built as written, the system would be wrong or unsafe: a core path fails at runtime, or two binding rules cannot both hold. |
| Major | An ambiguity or conflict that an implementer would probably resolve the wrong way, or a mandated check or requirement with nothing behind it. |
| Minor | Wording, a numbering slip or an inconsistency that a careful implementer would resolve correctly. |

New findings are numbered R2-01, R2-02, … Round-1 findings keep their F-nn numbers (section 8).

---

## 1. Summary

**Verdict: FAIL.** The round-1 fixes removed all three Critical findings and 45 of the 55 findings in full. No Critical finding remains. Three Major findings remain, so the verdict rule (FAIL if any Critical or Major) gives FAIL:

1. **R2-01** The demo acceptance criteria require a new usable check-in to appear in the resident check-in log, but the UX spec, the API enum, the DB query and the wireframe all exclude usable check-ins from that log.
2. **R2-02** What `seed test_v0_1` does, and where the roster lives, is defined two incompatible ways (DB-056/DB-058 versus TRD 15, TRD 16, TRD 20, TRD 14). The E2E required check and the staging smoke test depend on the answer.
3. **R2-03** Several Must requirements say `config_parameters` are changed by an admin with an audited `config.changed` event, but no command, endpoint or procedure performs that change. The CUSUM calibration procedure still prescribes a manual `scope=all` run, which ANL-032 now makes fail.

Everything else holds up under a fresh full pass:

- Coverage is complete: every BR-01..BR-18 maps to requirements in at least 10 TRDs and to at least one test or MVP criterion.
- No requirement ID dangles. Every endpoint, table/column, env var, error code and audit action that a TRD names is defined in its owning TRD.
- All workbook figures re-checked against SRC-03 match exactly (section 6.3).

| Severity | Count |
|---|---|
| Critical | 0 |
| Major | 3 |
| Minor | 23 |
| **Total new (round 2)** | **26** |

Round-1 findings: **Resolved 45, Partially resolved 10, Not resolved 0.** The residue of each partially resolved finding is filed as a new round-2 finding (R2-02 to R2-10), so the 26 new findings include those residues.

| # | Phase 1 check | Result | Key evidence |
|---|---|---|---|
| 1 | Database requirements support all APIs | **PASS** | All 24 tables, all CHECKs and grants support the 32 endpoints. Round-1 F-01, F-02, F-03, F-09, F-10 are resolved. Minor only: R2-11 (data-alert re-detection), R2-17 (`closed_at`), R2-24 (single-record ingest audit). |
| 2 | APIs support all frontend requirements | **FAIL** | R2-01: the check-in log contract cannot show the new usable check-in that SC-03 / AC-VIS-03 / E2E-15 require. Minor: R2-14, R2-23. |
| 3 | Analytics requirements support all business requirements | **FAIL** | All analytics numbers verified against the workbook. R2-03: the parameter-change and CUSUM calibration path (BR-09, BR-11, BR-16) has no defined mechanism and the calibration procedure contradicts ANL-032. Minor: R2-11, R2-12, R2-15, R2-16. |
| 4 | Testing requirements validate all critical functionality | **FAIL** | R2-01 (E2E-15 and TST-181 assert an impossible log row), R2-02 (E2E seed flow is undefined), R2-03 (TST-053 tests a config change no TRD lets anyone make). Minor: R2-09, R2-18, R2-22, R2-26. |
| 5 | Deployment requirements support the architecture | **FAIL** | R2-02 (local step 6, `e2e.yml` and staging reseed rely on a seed behaviour that DB-058 denies). Minor: R2-05, R2-18, R2-21, R2-25. |

TRD 25 §Phase 1 definition of done:

| Criterion | Result | Evidence |
|---|---|---|
| Every BR-01..BR-18 maps to at least one TRD requirement and test | **Met** | Section 2.1. Every BR is cited by 26–269 requirement rows across 10–24 TRDs. The TRD 02 §4.28 BR→FR table (TRD 02:570–590) covers all 18. Every BR has at least one TST/TDV/MVP row. |
| Every OQ/ASM/RSK/DSC/D ID used in the TRDs exists in TRD 24 | **Met** | Used: ASM-01..08, RSK-01..15, DSC-01..14, OQ-01..OQ-26, D-01..D-66, all defined in TRD 24. `OQ-27`, `RSK-16` and `D-67` occur only in TRD 24 §8 as "next free number" text, not as references. |
| Each of the five checks has a pass/fail line with evidence | **Met** | Table above and section 6. |

---

## 2. Requirements Traceability Matrix

### 2.1 Business requirements → TRD requirements → tests

Counts are scripted: rows whose first cell is a requirement ID and that cite the BR (explicitly or through a range such as `BR-01..BR-18`). BR/SRC/OQ/ASM/RSK/DSC restatement tables are excluded.

| BR | Summary (TRD 00) | Rows citing / TRDs | Key FRs (TRD 02 §4.28) | Tests / MVP criteria | Gap |
|---|---|---|---|---|---|
| BR-01 | Ingest feature records, never audio | 81 / 20 | FR-001–FR-005, FR-020–FR-028, FR-184, FR-321 | TST-030, TST-043, TST-045, TST-046, TST-133, TST-180, MVP-02 | FR-184 log row: R2-01 |
| BR-02 | Keep raw records unaltered | 102 / 17 | FR-005–FR-007, FR-010, FR-028, FR-223, FR-296 | TST-041, TST-043, TST-037, TDV-002, TDV-050, MVP-02, MVP-12 | — |
| BR-03 | Drop duplicates, keep first arrival | 41 / 14 | FR-008, FR-011, FR-029–FR-031, FR-182, FR-316 | TST-020, TST-044, TST-046, TDV-054, MVP-01, MVP-03 | — |
| BR-04 | Set aside poor-quality sessions | 29 / 13 | FR-024, FR-040–FR-044, FR-181, FR-290 | TST-020, TDV-053, MVP-01, MVP-03 | — |
| BR-05 | Quarantine wrong-speaker sessions | 28 / 10 | FR-060–FR-065, FR-074, FR-292 | TST-020, TDV-055, MVP-01, MVP-03 | — |
| BR-06 | Log missing days honestly | 70 / 15 | FR-120–FR-125, FR-135, FR-153, FR-154, FR-294, FR-295 | TST-020, TDV-052, TDV-053, TDV-064, TDV-068, MVP-01 | — |
| BR-07 | Remove morning offset | 27 / 12 | FR-070–FR-074, FR-171 | TST-020, TDV-056, MVP-01 | — |
| BR-08 | Epochs; restart baseline | 35 / 13 | FR-050–FR-053, FR-132, FR-155, FR-172 | TST-020, TDV-057, MVP-01 | — |
| BR-09 | Robust personal baseline, frozen | 56 / 15 | FR-080–FR-086, FR-162, FR-163, FR-205, FR-229, FR-230 | TST-020, TST-184, TDV-051, TDV-058, TDV-060, MVP-01 | FR-229 change path: R2-03 |
| BR-10 | Signed z and composite | 26 / 11 | FR-090–FR-095, FR-169, FR-170, FR-266 | TST-020, TDV-051, MVP-01 | — |
| BR-11 | CUSUM persistent-deviation flag | 62 / 14 | FR-100–FR-110, FR-165–FR-167, FR-261–FR-265, FR-300 | TST-020, TDV-059, TDV-060, TDV-067, MVP-01, MVP-13 | Calibration path: R2-03 |
| BR-12 | Residents overview | 93 / 17 | FR-130–FR-140, FR-150–FR-156, FR-312, FR-330 | TST-033, TST-090, TST-110, TST-181, TDV-062, TDV-066, MVP-04 | — |
| BR-13 | Resident detail page | 113 / 15 | FR-160–FR-173, FR-180–FR-184, FR-190–FR-195, FR-260–FR-280 | TST-090, TST-093, TST-110, TST-181, TDV-066, MVP-05, MVP-13 | Check-in log: R2-01 |
| BR-14 | New-admission arm (Should) | 30 / 10 | FR-200–FR-207, FR-331 | TST-090, MVP-06 (E2E-13 empty state only) | Weak: R2-26 |
| BR-15 | Reproduce workbook R01–R10 | 167 / 22 | FR-240–FR-245, FR-310–FR-323 | TST-005, TST-022, TST-048, TST-049, TST-070, TST-071, TST-074, TST-080 and 33 more | — |
| BR-16 | Data protection, roles, audit | 269 / 24 | FR-210–FR-221, FR-226–FR-229, FR-250–FR-254 | TST-007, TST-032, TST-041, TST-053, TST-130, TST-133, TST-137 | `config.changed`: R2-03; ingest audit: R2-24 |
| BR-17 | Monorepo deploy on Netlify/Railway/Neon/GHA | 75 / 15 | FR-253, FR-254 | TST-001, TST-150, MVP-08 | Seed flow: R2-02 |
| BR-18 | Detection not diagnosis, no LLM/ML | 48 / 15 | FR-164, FR-277, FR-278, FR-298 | TST-096, TST-097, MVP-09 | — |

### 2.2 Frontend requirements (TRD_Generation_Prompt) → UX / FE IDs

TRD 11 §4.16 maps every frontend item in the prompt. Each mapping was re-checked:

| Prompt frontend item | UX IDs | FE components (TRD 04 §4.8) | Test | Round-2 note |
|---|---|---|---|---|
| Residents overview, tiles, table | UX-020–UX-048 | ResidentsOverviewPage, StatusTiles, ResidentsTable | E2E-03, E2E-04 | Tiles 2/7/1/19 depend on seed flow (R2-02) |
| Sort controls | UX-030–UX-033, UX-261 | sort select | E2E-05, E2E-06 | — |
| Statuses Alarm On / No Alarm / Baseline Still Forming | §4.3.4, UX-036 | StatusBadge | E2E-04 | — |
| 30-day counts and missing days | UX-039, UX-047, UX-048 | ResidentsTable | E2E-04 | — |
| Device health cards | UX-050–UX-058, UX-263 | DeviceCard, DevicePanel | E2E-07 | Resolved (F-09, F-10) |
| Resident detail header, baseline info | UX-060–UX-066 | ResidentHeader | E2E-08 | — |
| "What this means" text | UX-070–UX-075, UX-160–UX-164 | WhatThisMeans | TST-096 | — |
| CUSUM tally chart | UX-080–UX-092 | CusumChart | TST-093, E2E-08 | Resolved (F-24) |
| 7 measurements | UX-100–UX-108 | FeatureCards | E2E-08 | — |
| Staff review / notes | UX-120–UX-135 | StaffReview | E2E-09 | OQ-05 note text: R2-13 |
| Check-in log with reasons | UX-140–UX-150 | CheckinLog | E2E-10, E2E-11, E2E-12, E2E-15 | **R2-01** |
| New admissions (experimental) | UX-181–UX-195 | AdmissionsPage, ComparisonChart | E2E-13 | Populated case untested (R2-26) |
| Alert review queue | UX-300–UX-322 | AlertCard, AlertReviewPanel, AlertReviewForm | E2E-17, E2E-18, E2E-19, E2E-21 | Resolved (F-08, F-12, F-25) |
| Data alerts | UX-306–UX-309, UX-331 | DataAlertQueue | E2E-17 | — |
| Analytics KPIs, funnel, by-resident, alarm timing | UX-351–UX-384 | AnalyticsPage | E2E-20, E2E-21 | Resolved (F-30); alarm timing data: R2-18 |
| Login / auth | UX auth rows, FE-03x | LoginPage | E2E-01, E2E-02, E2E-14 | — |
| Loading, empty, error states | UX state rows, FE-145 | SectionState | TST-090 | Component names: R2-14 |
| Accessibility | NFR-060 | FE-190 | TST-110 | Resolved (F-19) |
| Responsive layout | UX layout rows | — | E2E-16 | — |
| Plain language, no diagnosis | VIS-003..005 | — | TST-097 | — |

Result: every prompt item maps to UX and FE IDs and to a test. The check-in log item is mapped but its contract is internally contradictory (R2-01).

### 2.3 Wireframes → UX sections

| Wireframe | UX section | Coverage |
|---|---|---|
| `specs/UI-wireframe/Main.dc.html` (SRC-09) | TRD 11 §4.3, §4.4, §4.13 | Complete: header, tiles 2/7/1/19, sort, rows, badges, device cards, footer |
| `Resident.dc.html` (SRC-10) | TRD 11 §4.5 | Complete. The wireframe's check-in log lists alarms, set-asides, quarantines, missed days and restarts only, which matches UX-144 but not SC-03 (R2-01). |
| `Admission.dc.html` (SRC-11) | TRD 11 §4.7 | Complete |
| `Alerts.dc.html` (SRC-18) | TRD 11 §4.17 | Complete; queue order and review strings now agree (F-08, F-25 resolved) |
| `Analytics.dc.html` (SRC-19) | TRD 11 §4.18 | Complete; KPI values, funnel 300/281/269/267 and by-resident 43/73/80/93/100 re-verified against the workbook |

### 2.4 Items with no test or only weak verification

| Item | Status |
|---|---|
| FR-205 (Must) / DB-025 cohort transition new-admission → own baseline | No test in TRD 13 or TRD 14 (R2-26) |
| BR-14 facility comparison with populated data | Only the empty state is tested (E2E-13) (R2-26) |
| FR-229 / FR-250 / NFR-084 config change with `config.changed` audit | TST-053 exists, but there is no mechanism to test (R2-03) |
| ING-030 append-only trigger on `ingest_rejections` | Not in TRD 20 DDL, so no test can pass as written (R2-08) |

---

## 3. Missing Requirements

| ID | Severity | Where it is needed | What is missing |
|---|---|---|---|
| R2-03 | Major | FR-229 (TRD 02:292, Must), FR-250, NFR-084 (TRD 03:136), D-56, TRD 21 §4.4 (TRD 21:104), TRD 23:470, TST-053 (TRD 13:287) | A defined way to change a `config_parameters` row (CLI command, endpoint or SQL procedure) that writes `config.changed` to `audit_logs`. TRD 15 §4.8 lists only `bootstrap-config` (insert-missing). Details in section 4.1. |
| R2-26 | Minor | FR-205 (Must), DB-025, BR-14 | A test for the new-admission → own-baseline transition and for a populated facility comparison. |
| R2-08 | Minor | ING-030 (TRD 10:141) | The `ingest_rejections` append-only trigger in TRD 20 (or drop the requirement). |
| R2-25 | Minor | DEP-116, D-47 | A way for the AWS EventBridge path to record `trigger = nightly`; see section 4.3. |

---

## 4. Contradictions

### 4.1 Major

**R2-01 · Major · The check-in log must and must not show new usable check-ins**

- Side A (shown):
  - FR-184 (TRD 02:239): the check-in log lists the new check-in after ingest.
  - SC-03 (TRD 00:286) and AC-VIS-03 (TRD 00:391): after a demo POST, the new check-in appears in the resident's check-in log.
  - NFR-011, TST-181 (TRD 13:503) and E2E-15 (TRD 13:373) assert that row.
- Side B (not shown):
  - UX-144 (TRD 11:354): the log lists alarms, set-asides, quarantines, missed days and restarts; usable check-ins are not listed.
  - TRD 19 `CheckinEventType` (TRD 19:1184) has no usable/check-in value.
  - The DB-layer log query (TRD 06:524) excludes `usable` rows.
  - `Resident.dc.html` and the prompt list the same five event kinds as UX-144.
- Impact: E2E-15 and the demo "done means" step cannot pass if UX/API/DB are built as written; an implementer will either break the API contract or fail acceptance.
- Recommendation: decide in TRD 24 (new D-67). Either (a) restate SC-03/AC-VIS-03/FR-184/TST-181/E2E-15 as "the new check-in is reflected in last check-in, 30-day count and the tally chart" (which UX already shows), or (b) add a `checkin` event type to TRD 19, TRD 06 and UX-144. Option (a) matches the wireframe.

**R2-02 · Major · The seed command and the test roster are defined two incompatible ways**

- Side A:
  - DB-056 / DB-058 (TRD 06:592, 06:594): `seed test_v0_1` loads master data, users and the API key only; `--with-input` is what ingests SRC-05 and runs the pipeline.
  - The roster is a SQL file `database/seeds/test_v0_1_roster.sql` (TRD 06:647; TRD 20 §4.12 header).
- Side B:
  - DEP-015, TRD 15 §4.8 and local step 6 (TRD 15:129, 141, 385), `e2e.yml` (TRD 16:350) and deploy-staging step 4 (TRD 16:389) run `seed test_v0_1` without `--with-input` and expect a populated overview.
  - TRD 20 §4.12 (TRD 20:1058): "The CLI then ingests SRC-05".
  - TRD 14 DS-07, TRD 13:117 and DEP-119 place the roster as CSVs in `database/seeds/test_v0_1/`.
  - TRD 13:548 still names `backend.scripts.load_fixture`, which no other TRD defines.
- Impact: if DB-058 is followed, the E2E required check, the tiles 2/7/1/19 (DEP-016) and the staging smoke test DEP-080 all see an empty system. The roster's file format and path are ambiguous.
- Recommendation: pick one behaviour (e.g. `seed test_v0_1` always ingests SRC-05 and runs, as TRD 15/16/20 assume) and one roster format/path; update DB-056/DB-058, TRD 06:647 or TRD 14 DS-07, and replace `backend.scripts.load_fixture` in TRD 13:548.

**R2-03 · Major · No defined way to change parameters; calibration procedure contradicts ANL-032**

- Side A:
  - FR-229 (TRD 02:292, Must), FR-250, NFR-084 (TRD 03:136), D-56 and TRD 21 §4.4 (TRD 21:104: "admin via config change (audited)") require an admin parameter change that is audited as `config.changed`. TST-053 (TRD 13:287) tests it.
  - CUS-034 (TRD 09:221): a calibration change is "applied by an admin manual run with scope all".
- Side B:
  - TRD 15 §4.8 CLI has only `bootstrap-config` (insert missing keys). No endpoint in TRD 19 writes `config_parameters`.
  - ANL-032 (after the F-03 fix): a run whose algorithm-key hash differs from the stored baselines' hash fails with `config_changed_requires_rebuild`; a rebuild CLI is the only path. So the CUS-034 manual `scope=all` run fails.
  - ANL-055 / ANL-058 say "full rebuild" without naming the D-56 rebuild command.
- Impact: an implementer has to invent the change path (and where the audit row is written), and following CUS-034 literally produces a failed run.
- Recommendation: add a `set-config KEY VALUE` CLI to TRD 15 §4.8 (writes `config.changed` in the same transaction; for algorithm keys, refuses unless followed by the D-56 rebuild), point CUS-034, ANL-055, ANL-058 and TST-053 to it.

### 4.2 Minor

| ID | Location (A vs B) | Description and evidence | Recommendation |
|---|---|---|---|
| R2-04 | FE-041 TRD 04:205 vs TRD 12 (static CSP, no nonce) | F-14 residue: FE-041 still says the middleware sets a "(CSP nonce)". | Remove the nonce wording. |
| R2-05 | TRD 15:262 vs DEP-040 / SEC-111; TRD 25:200, 266 vs DEP-024, D-58 | F-16 residue: the nightly job "gets the same variables as the backend except PORT", which includes credentials the job does not need; TRD 25 tells the agent to run `cd backend && alembic upgrade head` against the target, while `alembic.ini` is at repo root (DEP-024) and D-58 makes migrations a pre-deploy step. | List the nightly job's vars explicitly; use the D-58 command in TRD 25. |
| R2-06 | TRD 07:94; TRD 01:276–280, 01:440; TRD 25:186, 219 | F-32 residue: `pipeline.py` is still described as a "CLI"; TRD 01 module lists and TRD 25 lists omit `aggregates.py`. | Align module lists with TRD 07 §4.2. |
| R2-07 | TRD 17:207 diagram vs D-63; TRD 23:699 vs TRD 23 "exactly 12 keys"; TRD 17:129 | F-05/F-41 residue: the diagram says "derived tables unchanged (transaction rolled back)" although D-63 is per-resident transactions; the TRD 23 `counts` example has 8 keys; TRD 17:129 puts `request_id` inside `pipeline_runs.counts`. | Update diagram and example; move `request_id` out of `counts`. |
| R2-08 | ING-030 TRD 10:141 vs TRD 20 triggers | F-42 residue: ING-030 says `ingest_rejections` has an append-only trigger; TRD 20 defines none. | Add the trigger or drop the clause. |
| R2-09 | TRD 13:238 (DA-02) vs CUS `baseline_stalled` rule | F-37 residue: test DA-02 says "15 days < 16 → no alert", but the inclusive rule (as_of − start) + 1 gives 16 for that case. | Recompute the DA-02 example. |
| R2-10 | TRD 15:438; ARC-061; TST-052; ANL-045; AC-ANL-13; DEP-047; API-061 | F-49 residue: rollback step "re-activate keys" has no command; the nightly dedupe condition is "exists" / "succeeded" / "running or succeeded" in different places. | Add `activate-api-key` or reword; use one dedupe condition (API-061). |
| R2-11 | ANL-060 TRD 07:419 vs DB-036 TRD 06:459; TRD 23:424, 621; TRD 19 example | A re-detected data alert reopens the old row and uses run time in ANL-060, but DB-036 and TRD 23 insert a new row keyed by `as_of`; the TRD 19 example uses run time. | Choose one model and one timestamp. |
| R2-12 | ENV-021 TRD 21:113 vs ANL-031 TRD 07:316; ANL-052 | An invalid config value fails the run with `pipeline_config_invalid` in ENV-021, but falls back to the default with `config_default_used` in ANL-031; `pipeline_config_invalid` is absent from the ANL-052 failure list. | Align. |
| R2-13 | FR-195 TRD 02:250 vs UX-125 TRD 11:318 | The OQ-05 note text under staff notes differs. | Use the UX-125 text. |
| R2-14 | TST-090 TRD 13:336 vs TRD 04 §4.8; TRD 04 §4.6.3 | TST-090 names components that are not in the TRD 04 inventory (which has AlertCard, DataAlertQueue, AlertReviewPanel, AlertReviewForm, DevicePanel, SectionState). The §4.6.3 alias list lacks ResidentDetail, StaffNote, AdmissionRow, AdmissionComparison used in props. | Align names; add the aliases. |
| R2-15 | ANL-044 TRD 07:365 vs API-053 TRD 05:198 | The batch-triggered run scope omits residents co-assigned to a device in the batch. | Use the API-053 definition in ANL-044. |
| R2-16 | TRD 06:436, TRD 05:475 vs TRD 07 binding signature | Engine call shapes `run_resident(...)` and `run_pipeline(raw_records, config, as_of, frozen_baselines)` differ from the binding `run_pipeline(records, residents, assignments, config, as_of, *, frozen_baselines)`. | Quote the TRD 07 signature. |
| R2-17 | CUS-018 TRD 09:132 vs TRD 20 `alerts_closed_ck`; DB-018; ANL-039 | CUS-018 says closure time is `updated_at`, but TRD 20 requires `closed_at` when closed, and DB-018/ANL-039 do not set it. | Set `closed_at` in DB-018/ANL-039; fix CUS-018. |
| R2-18 | TRD 16:349–352 (e2e.yml); TRD 16:389 (staging reseed) vs E2E-20, FE-194, CIC-032; TRD 21 | e2e.yml does not load the DS-10 ground truth that E2E-20 asserts for alarm timing; staging reseed passes only `DATABASE_URL`, `APP_ENV`, `PIPELINE_PROFILE`, `PIPELINE_AS_OF` although TRD 21 requires `JWT_SECRET`, `CORS_ORIGINS`, `DATABASE_READONLY_URL` in staging. | Load DS-10 in e2e.yml; pass or exempt the vars for the seed step. |
| R2-19 | TRD 04:594, 631 vs TDV-016 TRD 14:101 | UI fixtures are generated by `npm run fixtures:capture` into `frontend/tests/fixtures/` in TRD 04, but by `python -m tests.validation.record_ui_fixtures` into `frontend/tests/fixtures/ds07/` in TDV-016. | Choose one generator and path. |
| R2-20 | CIC-116 TRD 16:379 vs TRD 13:79, 522 | Lighthouse CI 0.13.x vs 0.14.x. | Pin one version. |
| R2-21 | GIT-010 TRD 18:105 vs GIT-014 TRD 18:109; GIT-013; CIC-052 | Linear history required, but merge commits allowed for release merges. | State the exception in GIT-010. |
| R2-22 | TST-152 TRD 13:454 vs DEP-081 TRD 15:426; TRD 21 `SMOKE_USER` | TST-152 logs in during the production smoke test; DEP-081 and TRD 21 say the smoke user is never provisioned in production. | Make prod smoke unauthenticated (health + login page). |
| R2-23 | UC-13 TRD 02:543 vs E-13 / API-080 | UC-13 filters `status=open,acknowledged`; E-13 accepts a single enum value. | Fix UC-13 or allow a list. |
| R2-24 | TRD 01:132, API-032, TRD 05 §4.12 vs TRD 12 §4.12 vocabulary, SEC-109 | `POST /sessions` is said to be audited, but the closed vocabulary has only `ingest.batch.received`. | Add `ingest.session.received` or state that single-record ingest is unaudited. |
| R2-25 | DEP-116, D-47 vs API-061, LOG-111 TRD 17:293, NFR-103, ANL-045, TRD 01:380 | On the AWS option EventBridge calls `POST /pipeline/run`, which records `trigger = manual`, so nightly dedupe and the "nightly run missing" banner never see a nightly run. | Give the scheduler a way to mark `nightly` (e.g. scheduler role or CLI). |
| R2-26 | FR-205, DB-025, BR-14 vs TRD 13/14 | See section 2.4. | Add TST/TDV rows. |

---

## 5. Cross-Reference Validation

| Check | Method | Result | Findings |
|---|---|---|---|
| Dangling requirement IDs | Scripted across all 26 TRDs (2,352 row-defined IDs) | None dangling. Duplicates are only the intended BR/OQ/ASM/SRC restatement tables. | — |
| OQ / ASM / RSK / DSC / D IDs vs TRD 24 | Scripted | All defined (D-01..D-66). `OQ-27`, `RSK-16`, `D-67` are "next free" text only. | — |
| E-, S-, MVP-, AC- IDs | Scripted | E-01..E-32, S-01..S-13, all MVP and AC IDs defined | — |
| Endpoints vs TRD 19 | Scripted (every `/api/v1/...` path) | All present. `/alerts/{id}/acknowledge` and `/audio` appear only in "shall not exist" statements; `/openapi.json` and `/docs` are covered by API-113. | R2-23 (query shape) |
| Tables/columns vs TRD 20 DDL | Scripted (24 tables, every `table.column`) | All match | R2-08 (trigger), R2-17 (`closed_at` not set) |
| Env vars vs TRD 21 | Scripted | All defined | R2-05, R2-18 (who receives which var) |
| Error codes vs TRD 05 catalogue | Scripted (36 codes) | All in catalogue | R2-12 (`pipeline_config_invalid` vs ANL-052) |
| Audit actions vs TRD 12 §4.12 vocabulary | Scripted (24 actions; CHECK `^[a-z_]+(\.[a-z_]+){1,2}$`) | All in vocabulary and match the CHECK (F-01 resolved) | R2-24 |
| File paths and commands | Manual + grep | Seed/roster paths and the fixture generator disagree; `backend.scripts.load_fixture` is stale | R2-02, R2-05, R2-19 |
| Function signatures | Manual | Engine call shape differs in TRD 05/06 | R2-16 |
| Golden fixtures | SHA-256 | Match TDV-013 (`ddbc03…`, `78e77f…`); generator 495 lines; CSV 30 columns, 283 rows | — |
| Code fences / placeholders | Scripted / grep `TBD`, `TODO`, `lorem` | Fences balanced; only GIT-053 (the rule itself) | — |

---

## 6. The five checks in detail

### 6.1 Database requirements support all APIs: **PASS**

- Every endpoint E-01..E-32 reads or writes only tables and columns defined in TRD 20; the grants in TRD 06 allow every write the APIs need, including the D-56 rebuild (F-03 resolved).
- The audit CHECK now accepts every action in the vocabulary (F-01); late-arrival rows satisfy the `processed_sessions` CHECKs (F-02); devices have `in_use_until` and epochs carry a restart cause (F-10); silent-day definitions agree (F-09).
- Minor issues only: R2-11 (two models for re-detected data alerts), R2-17 (`closed_at` required by CHECK but not set by DB-018/ANL-039, which would make the close UPDATE fail if not caught), R2-24.

### 6.2 APIs support all frontend requirements: **FAIL**

- Resolved since round 1: FE interfaces now match TRD 19 schemas (F-11); review explanations, snooze hours, restart cause, `in_use_until` and the facility-range-unavailable flag are carried by the API (F-12, D-64); API base origin and CORS are consistent (F-13, F-47, D-65, D-66).
- Fails on R2-01: the acceptance-critical check-in log row has no API representation.
- Minor: R2-23 (UC-13 filter), R2-14 (component names).

### 6.3 Analytics requirements support all business requirements: **FAIL**

Workbook re-verification (SRC-03 vs TRD 07/08/09/14/11), all exact:

| Quantity | Value |
|---|---|
| Status totals | 267 usable / 12 set aside / 2 quarantined / 2 duplicate / 17 missing / 2 late |
| Baselines | 180 rows; 8 floor-applied, all `number_of_pauses` |
| Scores per resident | R01 14, R02 8, R03 6, R04 14, R05 12, R06 14, R07 2, R09 14, R10 14 (98 total) |
| Alarm states | off 81 / on 15 / RINGS 2; R09 and R10 tallies match |
| Other | Leaning-most means match; R03 7 of 29; R08 13/5/12; by-resident 43/73/80/93/100; funnel 300/281/269/267 with drop reasons 5/5/3 and 1 multi-reason; daily rows Oct 1/8/12/22 match; Table 4.7-B baseline values match |

- Coverage of BR-03..BR-11 and BR-15 is complete, and the late-arrival and per-resident transaction behaviours are now consistent (F-02, F-05, D-57, D-63).
- Fails on R2-03: BR-09/BR-11 parameter tuning (CUS-034 calibration, FR-229) has no defined mechanism and the documented procedure contradicts ANL-032.
- Minor: R2-11, R2-12, R2-15, R2-16.

### 6.4 Testing requirements validate all critical functionality: **FAIL**

- Resolved since round 1: E2E and a11y are required checks (F-19); gitleaks, Bandit, LLM-dependency and other mandated CI checks have workflows (F-20); test-spec mismatches fixed (F-50); false-alarm denominator fixed (F-51).
- Fails on: R2-01 (E2E-15, TST-181 assert an impossible row), R2-02 (E2E seed flow undefined), R2-03 (TST-053 has nothing to exercise).
- Minor: R2-09 (DA-02 boundary), R2-18 (DS-10 not loaded for E2E-20), R2-22 (prod smoke login), R2-26 (FR-205 untested).

### 6.5 Deployment requirements support the architecture: **FAIL**

- Resolved since round 1: seed files ship in the image (F-15); the migrator credential is limited to the pre-deploy step (F-16, D-58, mostly); staging `PIPELINE_AS_OF` (F-17); backups (F-23, D-60); demo data in production is T-prefixed (D-59).
- Fails on R2-02: local step 6, `e2e.yml` and the staging reseed all depend on `seed test_v0_1` producing a populated system, which DB-058 denies.
- Minor: R2-05 (nightly vars, TRD 25 migration command), R2-18 (staging seed vars), R2-21 (linear history vs merge commits), R2-25 (AWS nightly trigger).

---

## 7. Recommended fixes (not applied)

In priority order:

1. **R2-01**: record a decision (D-67) on the check-in log. Recommended: keep UX-144/TRD 19/TRD 06 and the wireframe; rewrite FR-184, SC-03, AC-VIS-03, NFR-011, TST-181 and E2E-15 to assert last check-in, 30-day count and chart instead.
2. **R2-02**: make `seed test_v0_1` ingest SRC-05 and run the pipeline (as TRD 15/16/20 assume) or add `--with-input` everywhere it is used; choose one roster format and path; replace `backend.scripts.load_fixture` (TRD 13:548).
3. **R2-03**: add a `set-config` CLI to TRD 15 §4.8 that writes `config.changed`; tie algorithm keys to the D-56 rebuild; rewrite CUS-034, ANL-055, ANL-058 and TST-053 to use it.
4. Clear the round-1 residues R2-04 to R2-10 (each is a one-line wording fix in the cited location).
5. Align the remaining Minor items R2-11 to R2-26, starting with R2-17 (`closed_at`, which affects a CHECK at runtime), R2-12 and R2-25.

---

## 8. Round-1 findings status

| ID | Round-1 severity | Subject | Status | Evidence / residue |
|---|---|---|---|---|
| F-01 | Critical | Audit CHECK rejects named actions | Resolved | TRD 12 §4.12 vocabulary (24 actions) all match the TRD 20 CHECK |
| F-02 | Critical | Late-arrival rows violate `processed_sessions` CHECKs | Resolved | D-57; TRD 20 CHECKs allow late rows |
| F-03 | Critical | Parameter change needs a forbidden baseline delete | Partially resolved | D-56 split + rebuild CLI and grants fixed; CUS-034 (TRD 09:221) still prescribes manual `scope=all`; no change mechanism (R2-03) |
| F-04 | Major | Advisory lock keys differ | Resolved | D-62; one key scheme across TRD 05/06/07/10/20 |
| F-05 | Major | One transaction per run vs per resident | Partially resolved | D-63 applied; TRD 17:207 diagram still "transaction rolled back" (R2-07) |
| F-06 | Major | Extra alert closure path | Resolved | FR-110, CUS-019, AGT-058 agree |
| F-07 | Major | "Superseded by rebuild" closure | Resolved | Closure paths aligned with D-56 |
| F-08 | Major | Data-alert review strings | Resolved | API-130, CUS-040, UX §4.17.2, TRD 23 agree |
| F-09 | Major | Silent-day definitions | Resolved | One definition across FR, DB, API, FE, UX |
| F-10 | Major | `in_use_until` / restart cause without source | Resolved | Columns in TRD 20, fields in TRD 19 |
| F-11 | Major | FE interfaces vs TRD 19 schemas | Resolved | TRD 04 §4.6.3 aliases TRD 19 schemas (alias gaps: R2-14) |
| F-12 | Major | Missing API data for FE | Resolved | D-64; fields added to TRD 19 |
| F-13 | Major | API base URL double `/api/v1` | Resolved | D-65; origin-only everywhere |
| F-14 | Major | CSP and Railway hostnames | Partially resolved | Static CSP agreed; FE-041 (TRD 04:205) still mentions a nonce (R2-04) |
| F-15 | Major | Seed files absent from image | Resolved | DEP-119 ships `database/seeds/` |
| F-16 | Major | Migrator credential on web service | Partially resolved | D-58 pre-deploy; TRD 15:262 nightly vars and TRD 25:200, 266 manual `cd backend && alembic` remain (R2-05) |
| F-17 | Major | Staging `PIPELINE_AS_OF` | Resolved | TRD 21, ANL-015, AC-VIS-03 agree |
| F-18 | Major | Error codes outside catalogue | Resolved | All 36 codes in TRD 05 catalogue |
| F-19 | Major | E2E / a11y not required checks | Resolved | CIC-031 / CIC-070 list them |
| F-20 | Major | Mandated CI checks with no workflow | Resolved | Workflows/jobs defined in TRD 16 |
| F-21 | Major | Ledger end vs `withdrawn_on` | Resolved | ING-048, FR-120, DB-023 agree |
| F-22 | Major | `feature_name_map` seed | Resolved | ING-016/017 and TRD 20 seed agree |
| F-23 | Major | Backup / PITR targets | Resolved | D-60; one set of values |
| F-24 | Major | Chart range string / AC-UX-06 | Resolved | TST-093, E2E-08, UX-082 agree |
| F-25 | Major | Alert queue order | Resolved | UX-301, FR-261, CUS-037 agree |
| F-26 | Major | `PipelineConfig` lacks data-alert/review fields | Resolved | Fields added to TRD 07 table |
| F-27 | Minor | S-01..S-10 vs S-13 | Resolved | — |
| F-28 | Minor | Contract R-range / D-range in TRD 24, AGT-002 | Resolved | — |
| F-29 | Minor | Review button disabled vs hidden | Resolved | — |
| F-30 | Minor | `/alerts`, `/analytics` not in FE structure | Resolved | TRD 04 §4.2, FE-032 |
| F-31 | Minor | JS budget 250 vs 300 kB | Resolved | — |
| F-32 | Minor | Stage count / module lists | Partially resolved | TRD 07:94 "CLI"; TRD 01:276–280, 440 and TRD 25:186, 219 omit `aggregates.py` (R2-06) |
| F-33 | Minor | `sslmode` values | Resolved | — |
| F-34 | Minor | `POST /sessions` batch row | Resolved | — |
| F-35 | Minor | Rejection `errors` shape | Resolved | — |
| F-36 | Minor | CSV header order | Resolved | — |
| F-37 | Minor | `baseline_stalled` off-by-one | Partially resolved | Rule aligned; TRD 13:238 DA-02 example still wrong (R2-09) |
| F-38 | Minor | "Alarms raised" note wording | Resolved | — |
| F-39 | Minor | Six TRD 17 mismatches | Resolved | — |
| F-40 | Minor | Uptime cadence / nightly-failure issue | Resolved | — |
| F-41 | Minor | `pipeline_runs` JSON shapes | Partially resolved | TRD 23:699 example 8 keys vs "exactly 12"; TRD 17:129 `request_id` in `counts` (R2-07) |
| F-42 | Minor | Trigger names | Partially resolved | Names aligned; ING-030 (TRD 10:141) trigger on `ingest_rejections` not in TRD 20 (R2-08) |
| F-43 | Minor | Resident-code patterns | Resolved | — |
| F-44 | Minor | `phrase_id` / `mean_f0_hz` | Resolved | — |
| F-45 | Minor | Tooling settings | Resolved | — |
| F-46 | Minor | Frontend env var list / ribbon text | Resolved | — |
| F-47 | Minor | `CORS_ORIGIN_REGEX` | Resolved | D-66 |
| F-48 | Minor | `DATABASE_READONLY_URL` | Resolved | — |
| F-49 | Minor | `deactivate-api-key`, nightly dedupe, AC-DEP-01 | Partially resolved | TRD 15:438 "re-activate keys" has no command; dedupe "exists"/"succeeded"/"running or succeeded" (R2-10) |
| F-50 | Minor | Five test-spec mismatches | Resolved | — |
| F-51 | Minor | False-alarm denominator | Resolved | — |
| F-52 | Minor | `is_morning` mapping; DS-01 vs DS-07; DB-056 | Partially resolved | `is_morning` fixed; seed/roster source conflict remains and is now Major (R2-02) |
| F-53 | Minor | TRD 25 merge target / admin seed | Resolved | — |
| F-54 | Minor | TRD 23 class count, `raw_body` | Resolved | — |
| F-55 | Minor | SRC-01 analytics location (informational) | Resolved | Noted in TRD 01 |

Totals: Resolved 45, Partially resolved 10, Not resolved 0.
