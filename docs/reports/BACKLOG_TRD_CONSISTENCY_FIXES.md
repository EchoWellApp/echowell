# PR #2 TRD issue resolution log (20 Oct 2026)

Scope: the issues in pr2_trd_issues.md and BACKLOG.md §12 (Q-01..Q-07). New TRD 24 IDs: D-75..D-98, OQ-27..OQ-29 (next free: D-99, OQ-30). New TRD 13 IDs: TST-190..TST-195; new TRD 11 ID: UX-219. Every changed TRD has a new revision row "PR #2 backlog consistency fixes (…)" and a bumped header version; BACKLOG.md is v0.2.

Counts by type: aligned 47, decision 32, new OQ 3 (total 82 rows).

| # | Issue | Resolution | Files / IDs changed | Type |
|---|---|---|---|---|
| A-01 | FEAT-085: BACKLOG says monthly usage check; TRD 15 DEP-101 and TRD 17 §4.8 say weekly | BACKLOG FEAT-085 description says weekly; feature note updated | BACKLOG.md FEAT-085; FEAT-085 | aligned |
| A-02 | CUS-030 ingests DS-04 into staging vs TDV-090 isolated database | Isolated calibration database of the local docker-compose stack, never staging or production | TRD 09 CUS-030; TRD 14 TDV-090; TRD 24 D-75; FEAT-093 | decision D-75 |
| A-03 | CUS-031 grid varies baseline_n vs D-01 fixed 30 (RSK-03 owner approval) | Grid keeps baseline_n for reporting; a value other than 30 is applied only with owner approval (D-01) | TRD 09 CUS-031; FEAT-093 | aligned |
| A-04 | ANL-056 EWMA 'after step 10' (step 10 = day ledger in ANL-006); no EWMA field in scores/TRD 19 | ANL-056 names step 10 of the §4.5 algorithm (run_cusum, stage 8) and the future scores column / ScoreRow field added with OQ-18 | TRD 07 ANL-056; FEAT-096 | aligned |
| A-05 | facility_reference_ranges.pipeline_run_id NOT NULL vs ANL-057 computed outside run_pipeline; no owning run | Pipeline service calls the facility-norm function after run_pipeline within a scope-all run and stamps that run's id | TRD 07 ANL-057; TRD 24 D-76; FEAT-095 | decision D-76 |
| A-06 | Speaker verification needs TRD 20 PGS-012 and ING-017 changes (future) | OQ-14 interim decision now records the required ING-017, raw_sessions column and PGS-012 changes | TRD 24 OQ-14; FEAT-097 | aligned |
| A-07 | SEC-154 full-SHA pinning of all actions vs CIC-025 major tags for actions/*, docker/*, microsoft/playwright | SEC-154 follows CIC-025 (CI TRD owns workflows) | TRD 12 SEC-154; FEAT-078 | aligned |
| A-08 | TRD 18 branch table: main linear history vs GIT-010 staging only | Branch table: no linear-history rule on main; staging adds it | TRD 18 §4 branch table | aligned |
| A-09 | SEC-055 token_urlsafe(48) vs TRD 21 openssl rand -hex 32 | SEC-055 uses openssl rand -hex 32 (TRD 21, env owner, and CI) | TRD 12 SEC-055; FEAT-083 FR-05 and note | aligned |
| A-10 | TST-120 / ANL-047 ubuntu-latest vs CIC-027 ubuntu-24.04 | Both use ubuntu-24.04 | TRD 13 TST-120; TRD 07 ANL-047; FEAT-052 FR-15; FEAT-079 | aligned |
| A-11 | Restore drill: DEP-097 vs DB-051 vs SEC-162 different checks and record locations | One drill defined by DEP-097 (union of checks, record in docs/deployment.md); DB-051 and SEC-162 refer to it | TRD 15 DEP-097; TRD 06 DB-051; TRD 12 SEC-162; TRD 24 D-77; BACKLOG FEAT-089; FEAT-089 | decision D-77 |
| A-12 | Viewport: E2E-16 375x812 vs FE-191 390x844 (also UX-243 320, NFR-068 360) | Requirement from 320px; tests at 320, 360, 375, 390 (plus 768, 1280 for NFR-068); see B-C15 | TRD 03 NFR-068; TRD 04 FE-191, AC-FE-08; TRD 11 AC-UX-09; TRD 13 E2E-16; TRD 24 D-78; BACKLOG FEAT-075; FEAT-075, FEAT-076 | decision D-78 |
| A-13 | TST-135 http->https redirect and SEC-066 TLS check not in DEP-080/081 smoke lists | Added as DEP-080 (i)/(j) and DEP-081 (e)/(g) | TRD 15 DEP-080, DEP-081; FEAT-086 FR-06, FR-09, note | aligned |
| A-14 | DEPLOYMENT_CONFIGURATION_GUIDE.md: TRD 15 §8 repo root vs TRD 25 / D-21 docs/reports/ | TRD 15 §4.2 and §8 use docs/reports/ | TRD 15 §4.2, §8; FEAT-087 | aligned |
| A-15 | Gap: NFR-151 and NFR-012 have no TRD 13 test | New TST-190 (sustained ingest, nightly) and TST-191 (bundle size, frontend CI job); CIC-035 and ci.yml frontend job updated | TRD 13 TST-190, TST-191, TST-126; TRD 03 NFR-012, NFR-151; TRD 16 CIC-035, ci.yml; TRD 24 D-98; BACKLOG FEAT-079; FEAT-079, FEAT-080 | decision D-98 |
| A-16 | Gap: NFR-010 names four pages vs TST-125 only /residents | TST-125 and CIC-116 cover /residents, /residents/R09, /alerts, /analytics | TRD 13 TST-125; TRD 16 CIC-116; TRD 03 NFR-010; FEAT-079 FR-10 | decision D-98 |
| A-17 | Gap: NFR-001 k6/Locust vs TRD 13 pytest perf_counter | NFR-001 verified by TST-122 (pytest + perf_counter in the nightly performance job); §8 note updated | TRD 03 NFR-001, §8; FEAT-079 | decision D-98 |
| A-18 | Gap: weekly dump storage depends on OQ-01 | OQ-01 interim decision states where interim (synthetic) dumps go; DEP-096 cites it | TRD 24 OQ-01; TRD 15 DEP-096; FEAT-089 | aligned |
| A-19 | Gap: OQ-13 has no false-alarm target so CUS-034 cannot run | New OQ-27 (PI false-alarm target); interim: report grid only, select nothing, production keeps k 0.5, h 5.0, N 30 | TRD 24 OQ-27; TRD 09 CUS-034; BACKLOG FEAT-093 gate and refs; FEAT-093 | new OQ-27 |
| B-G1 | GET /analytics: how AnalyticsSummary is produced on request | Rebuild stage inputs from persisted rows of the latest succeeded run and call pure build_analytics_summary; API-006/API-087 state it | TRD 05 API-006, API-087; TRD 24 D-79; FEAT-051 | decision D-79 |
| B-G2 | No TRD 13 test IDs for CLI run-pipeline, rebuild, set-config | New TST-192 (set-config), TST-193 (rebuild), TST-194 (run-pipeline) | TRD 13 TST-192..TST-194; TRD 24 D-98; BACKLOG FEAT-055 refs; FEAT-055 | decision D-98 |
| B-G3 | FR-172 (view earlier epoch) has no UI in TRD 04/11 | New OQ-28 with interim 'Device period' select; FR-172 traces OQ-28 | TRD 24 OQ-28; TRD 02 FR-172; BACKLOG FEAT-067 refs; FEAT-067, FEAT-028 | new OQ-28 |
| B-G4 | /admin: LOG-111 nightly-missing banner has no API field/UX row; UX-212 'profiles allowed by backend' has no endpoint | Banner computed client-side from GET /pipeline/runs (new UX-219); profile select offers only meta.pipeline_profile | TRD 11 UX-212, UX-219; TRD 24 D-96; FEAT-074 | decision D-96 |
| B-G5 | No header text when the Alerts(n) count query fails | Link reads 'Alerts' without a count while loading or on failure | TRD 11 UX-018; TRD 04 FE-036; TRD 24 D-97; FEAT-064 | decision D-97 |
| B-C01 | ANL-037 baseline_mismatch vs DB-016 late_arrival 'epoch <n>' | DB-016 uses baseline_mismatch (algorithm owner); late_arrival kept for late records and blocked renumbering | TRD 06 DB-016; FEAT-053 | aligned |
| B-C02 | ANL-053 pipeline_run_finished vs LOG-062/065 succeeded/failed; LOG-063 lacks stages 11-12; AC-LOG-05 'stage' field; epoch_key_changed undefined | Events pipeline_run_started + exactly one of pipeline_run_succeeded/failed; stage names add data_alerts, aggregates; stage = detail prefix; epoch_key_changed removed | TRD 07 ANL-053; TRD 17 LOG-063, AC-LOG-05; TRD 24 D-80; BACKLOG FEAT-056; FEAT-056, FEAT-053, FEAT-018, FEAT-011 | decision D-80 |
| B-C03 | ARC-040 data alerts last vs TRD 07 aggregates after them | ARC-040 follows TRD 07 order (aggregates last) | TRD 01 ARC-040; FEAT-052 | aligned |
| B-C04 | ANL-045/ARC-061 fixed 02:xx vs API-060/LOG-110 NIGHTLY_RUN_HOUR_LOCAL | All requirement rows say NIGHTLY_RUN_HOUR_LOCAL (default 2, 02:xx) | TRD 01 ARC-061 + diagram; TRD 02 UC actor; TRD 03 NFR-023, NFR-134; TRD 07 ANL-045, §2; TRD 13 TST-052; TRD 15 DEP-047; TRD 24 D-47; TRD 25 Phase 6, AGT-059; BACKLOG FEAT-054; FEAT-054 | aligned |
| B-C05 | LOG-080 app/error.tsx vs TRD 04 app/(protected)/error.tsx | LOG-080 uses app/(protected)/error.tsx | TRD 17 LOG-080; FEAT-062 | aligned |
| B-C06 | E2E-01 clinician nav shows Analytics vs FR-218/FE-028/UX-018/SEC-043/E2E-21 | E2E-01 nav has no Analytics for a clinician | TRD 13 E2E-01; FEAT-064 | aligned |
| B-C07 | FR-150 Devices nav link vs FE-026/UX-016 retired | FR-150 states there is no Devices link | TRD 02 FR-150; FEAT-064, FEAT-065 | aligned |
| B-C08 | FR-134 '(was …)' current epoch vs TRD 11 §5 within 30 days | Single rule of TRD 23 §4.4.1; FR-134 and TRD 11 §8 cite it; UI renders when previous_device_code is returned | TRD 02 FR-134; TRD 11 §8 note; FEAT-065 | aligned |
| B-C09 | FR-169 sparkline adjusted values vs UX-102/FE-098 sign×z | FR-169 says sign × z | TRD 02 FR-169; FEAT-066 | aligned |
| B-C10 | FR-168 tally table incl. composite z vs UX-090/TST-093/FE-184 | FR-168 columns Date, Tally, Alarm | TRD 02 FR-168; FEAT-067 | aligned |
| B-C11 | FR-260 stack <900px vs UX-246 <1024px | FR-260 says 1024 px | TRD 02 FR-260; BACKLOG FEAT-069; FEAT-069 | aligned |
| B-C12 | FR-280 'No open alarms' vs UX-305/UX-319 | FR-280, UC-13 and §8 note use the UX-305/UX-319 texts | TRD 02 FR-280, UC-13, notes; BACKLOG FEAT-069; FEAT-069 | aligned |
| B-C13 | FR-266 vs UX-312 trailing period | FR-266 ends 'stands out.' | TRD 02 FR-266 | aligned |
| B-C14 | FR-310/UC-14 'Not available for your role' vs FE-034/FE-037/UX-350 | FR-310 and UC-14 use 'You do not have access to this page.' | TRD 02 FR-310, UC-14; FEAT-072, FEAT-021 | aligned |
| B-C15 | Phone widths UX-243 320, NFR-068 360, E2E-16 375, FE-191 390 | Same as A-12: test all four widths | see A-12; TRD 24 D-78 | decision D-78 |
| B-C16 | FR-192 notes superseded but no edit UI (UX-129) | FR-192 says corrections come through the API; MVP UI has no edit control | TRD 02 FR-192; FEAT-071 | aligned |
| C-01 | TRD 19 IngestRejection.row_number required int vs TRD 23/ING-032 NULL for JSON | row_number = batch position for CSV and JSON; NULL only for single-record /sessions rejections | TRD 10 ING-032; TRD 23 §4.2.8; TRD 24 D-84; FEAT-026 FR-10 and notes | decision D-84 |
| C-02 | export-openapi: TRD 05 §8 / TRD 25 'writes file' vs TRD 15 §4.8 prints + CIC-018 diff | Prints to stdout only; regenerate with a redirect; CI diffs | TRD 05 §8; TRD 15 §4.8; TRD 25 Phase 5, AGT-061, AC-AGT-11; TRD 24 D-89; FEAT-038 | decision D-89 |
| C-03 | FR-244 CSV columns SRC-03 sheet names vs API-129/TST-079/TRD 19 DTO names | FR-244 uses TRD 19 DTO field names | TRD 02 FR-244; FEAT-034 | aligned |
| C-04 | TRD 19 BaselineRow.robust_spread exclusiveMinimum 0 vs BSC-035 / baselines_spread_ck allow 0 | TRD 19 minimum 0 | TRD 19 BaselineRow; FEAT-034 | aligned |
| C-05 | Quarantine reason: TRD 08 §4.4 pseudocode short form vs TRD 07 §4.3 / PGS-012 full text | Pseudocode stores the full text as the single reason | TRD 08 §4.4; FEAT-044 | aligned |
| C-06 | device_silent title: TRD 09 multi-day vs FR-294 / TRD 11 §4.17.2 only 'all day' | FR-294 and TRD 11 list both titles | TRD 02 FR-294; TRD 11 §4.17.2; FEAT-050 | aligned |
| C-07 | leaning_most computed on read via alert_generator vs API-006 'only analytics.pipeline' | API-006 names the read-side pure helpers | TRD 05 API-006; TRD 24 D-79; FEAT-048, FEAT-030 | decision D-79 |
| C-08a | Admissions: OQ-08/OQ-20 undefined comparison details (min check-ins, raw vs adjusted, features, sex range) | New OQ-29 with interim decision | TRD 24 OQ-29; BACKLOG FEAT-036 refs; FEAT-036 | new OQ-29 |
| C-08b | TRD 04 FE-100 facility_low/facility_high vs TRD 19 low/high | FE-100 uses low/high | TRD 04 FE-100; FEAT-036, FEAT-073 | aligned |
| C-09a | CUS-029 requires cusum_k in analytics response; Meta lacks it | CUS-029 asks only for meta fields (cusum_h, baseline_n, profile); TRD 19 wins | TRD 09 CUS-029; FEAT-035 | aligned |
| C-09b | FR-240 'latest pipeline run' ambiguous | Latest succeeded run (API-069) in FR-240, API-087, TRD 19 E-18 | TRD 02 FR-240; TRD 05 API-087; TRD 19 E-18 prose; FEAT-035 | aligned |
| C-09c | AlarmTimingRow.result lacks a value for an alarm before the planted onset | false_alarm with delay_days null; UI 'False alarm' | TRD 19 AlarmTimingRow; TRD 11 UX-373; TRD 24 D-81; FEAT-035 FR-07 | decision D-81 |
| C-10a | Check-in log baseline_restarted detail defined only for device change | Same detail template for every cause; change in structured fields | TRD 19 E-10 prose; TRD 24 D-82; FEAT-028 | decision D-82 |
| C-10b | BACKLOG 'epochs list' vs TRD 19 epoch_count | BACKLOG FEAT-028 says epoch_count | BACKLOG FEAT-028; FEAT-028 | aligned |
| C-10c | still_above_line defined only by example | still_above_line = latest current-epoch tally >= cusum_h | TRD 19 Explanation; TRD 24 D-82; FEAT-028 FR-07 | decision D-82 |
| C-11 | staff_notes supersedes_id naming an already-superseded note: no response defined | 422 VALIDATION_ERROR (field supersedes_id), also for the unique-constraint race | TRD 05 API-085; TRD 24 D-83; FEAT-033 | decision D-83 |
| C-12 | LAST_ADMIN (API-092) unreachable via API due to SEC-044 | API-092 recorded as a defensive invariant tested at service level | TRD 05 API-092; FEAT-037 | aligned |
| C-13 | duplicate_payload_differs is an ingest warning (ING-023), not a RunWarning (ANL-052) | ING-037 states it is an ingest warning only | TRD 10 ING-037; FEAT-041 | aligned |
| C-14 | assign_epochs signature (rows) vs call with late set | TRD 07 §4.2 signature takes late as keyword with empty default | TRD 07 §4.2; FEAT-042 | aligned |
| C-15 | Composite baseline needs feature_z/composite_raw, assigned to FEAT-046 | BACKLOG assigns feature_z and composite_raw to FEAT-045; FEAT-046 completes composite_z and scoring | BACKLOG FEAT-045, FEAT-046; FEAT-045 | aligned |
| C-16a | BACKLOG FEAT-029 replaced_device_code vs TRD 19 replaces_/replaced_by_device_code | BACKLOG uses TRD 19 names | BACKLOG FEAT-029 | aligned |
| C-16b | Device.in_use_since defined only by examples | in_use_since = earliest valid_from (DB-066, TRD 23 §4.4.2) | TRD 06 DB-066; TRD 23 §4.4.2; TRD 24 D-82; FEAT-029 | decision D-82 |
| D-01 | resident_code pattern TRD 23 letters/digits/hyphen 1–32 vs TRD 20 ^[A-Z0-9]{1,16}$ | TRD 23 uses the TRD 20 pattern | TRD 23 §4.2.3; FEAT-009 | aligned |
| D-02 | Phase 3 health 200 impossible without provision_login_roles.sql and alembic.ini (Phase 4) | Both files move to TRD 25 Phase 3 outputs (FEAT-006) | TRD 25 Phase 3, 4; TRD 15 §8; TRD 24 D-90; BACKLOG FEAT-006, FEAT-008; FEAT-006 (new FR-15), FEAT-007, FEAT-008 | decision D-90 |
| D-03 | TRD 15 §4.8 bootstrap inserts config defaults vs migration 0002 seeds 46 rows | bootstrap only verifies the 0002 rows (exit 2 if missing) | TRD 15 §4.8; TRD 21 §4.4, ENV-021; TRD 24 D-85; FEAT-017 | decision D-85 |
| D-04 | postgres:16-alpine (DEP-010, CIC-012) vs testcontainers postgres:16 (TST-002) | TST-002 uses postgres:16-alpine; TRD 25 Phase 3 compose too | TRD 13 TST-002; TRD 25 Phase 3; BACKLOG FEAT-006; FEAT-005, FEAT-006, FEAT-079 | aligned |
| D-05 | SEC-110 roles by first migration vs TRD 20 §4.3 / D-72 provisioning script | SEC-110 states the provisioning step | TRD 12 SEC-110; FEAT-008 | aligned |
| D-06 | TRD 15 §4.8 create-user lacks --display-name (TRD 05 §8 has it) | --display-name added to TRD 15 §4.8, DEP-075, SEC-017, TRD 25 Phase 4 | TRD 15 §4.8, DEP-075; TRD 12 SEC-017; TRD 25 Phase 4; FEAT-016, FEAT-088 | aligned |
| D-07 | No exit code for refused create-user/create-api-key/revoke-api-key input | Exit code 2, no change (CLI refusal convention); new TST-195 | TRD 15 §4.8; TRD 13 TST-195; TRD 24 D-86; BACKLOG FEAT-016 refs; FEAT-016 | decision D-86 |
| D-08 | Audit rows for auth.login.failed / access.denied / rate-limited vs get_db() rollback (API-011) | Written and committed in their own transaction (SEC-101) | TRD 12 SEC-101; TRD 24 D-87; FEAT-015 FR-02, FEAT-020, FEAT-021 | decision D-87 |
| D-09 | BACKLOG FEAT-021 cites OAS-020..026; only OAS-020 relevant | BACKLOG cites OAS-020 | BACKLOG FEAT-021; FEAT-021 | aligned |
| D-10 | Phase 5 pipeline service interface empty until Phase 6 | Interim executor records runs failed so POST /sessions returns pending; documented in TRD 25 Phase 5 | TRD 25 Phase 5; TRD 24 D-91; BACKLOG §6; FEAT-024 | decision D-91 |
| D-11 | 'Non-local' TLS (DB-053, PGS-027) undefined | Non-local = APP_ENV not local/test (ENV-011) | TRD 06 DB-053; TRD 20 PGS-027; TRD 25 Phase 4; TRD 24 D-88; FEAT-013 | decision D-88 |
| Q-01 | BACKLOG §12 Q-01: phase of the GET /analytics aggregate blocks | Phase 6 (FEAT-051); TRD 25 Phases 5 and 6 aligned | TRD 25 Phases 5, 6; TRD 24 D-92; BACKLOG §12; FEAT-035, FEAT-051 | decision D-92 |
| Q-02 | BACKLOG §12 Q-02: phase of leaning_most in GET /alerts | Phase 6 (FEAT-048) | TRD 25 Phases 5, 6; TRD 24 D-92; BACKLOG §12; FEAT-030, FEAT-048 | decision D-92 |
| Q-03 | BACKLOG §12 Q-03: Phase 4 seed scope | --master-only and --reset in Phase 4; full seed in Phase 6 | TRD 25 Phases 4, 6; TRD 24 D-93; BACKLOG §12, FEAT-055 refs | decision D-93 |
| Q-04 | BACKLOG §12 Q-04: ci.yml jobs after Phase 3 | backend-lint, backend-test, frontend in Phase 3; complete in Phase 9 | TRD 25 Phases 3, 9; TRD 24 D-94; BACKLOG §12, FEAT-007; FEAT-007 | decision D-94 |
| Q-05 | BACKLOG §12 Q-05: checklist 'Sprint 7: Deployment' heading | Heading now 'Sprint 7: Backlog'; unclosed code fences of Sprint 6/7 closed; DSC-12 notes it; BACKLOG §9 mapping updated | specs/prompts/Implementation_Audit_Checklist.md; TRD 24 DSC-12; BACKLOG §9, §12 | aligned |
| Q-06 | BACKLOG §12 Q-06: when completion tracking is refreshed | End of each implementation PR; reconciled after Phase 11 (TRD 25 Phase 12) | TRD 25 Phase 12; TRD 24 D-95; BACKLOG §12 | decision D-95 |
| Q-07 | BACKLOG §12 Q-07: round-9 confirmation of R8 fixes | Note added at the top of the round-8 report; no round 9 | docs/reports/TRD_VALIDATION_REPORT.md; BACKLOG §12 | aligned |
| X-01 | (found while checking) TRD 18 GIT-053 contains the literal marker words, so the TRD 25 Phase 1 grep cannot return nothing | GIT-053 reworded without the literal words; meaning unchanged | TRD 18 GIT-053 | aligned |
| X-02 | (found while checking) 7 feature-file table rows had unescaped \| inside code spans (broken tables) | Pipes escaped as \\| inside the code spans | FEAT-001 AC-06, FEAT-004 AC-07, FEAT-006 AC-06, FEAT-028 FR-04, FEAT-034 FR-06, FEAT-089 AC-05, FEAT-091 AC-04 | aligned |

## Checks after the edits

- `verify.py specs/backlog/BACKLOG.md specs/TRD`: RESULT PASS (97 features, acyclic graph, valid order, mermaid edges match, 211 FRs covered, 0 undefined cited IDs, no marker words).
- `check_feat_001_025.py 1 97` with `w/idx.json` regenerated by `w/idx.py` (34 new IDs, none removed): ALL CHECKS PASSED, 0 errors.
- Structural checks (`p2/chk.py`): no duplicate D/OQ/ASM/RSK/DSC rows in TRD 24, no duplicate requirement IDs across TRDs, no dangling D-/OQ- references (only the "OQ-30 onward" next-free text), balanced code fences in all TRDs, BACKLOG, feature files, the checklist and the report, 0 table rows with a wrong cell count, and no TBD/TODO/[placeholder] in specs/TRD or specs/backlog.

## Documentation audit minor fixes (DA-01..DA-12)


Source: docs/reports/DOCUMENTATION_COMPLETENESS_AUDIT.md (not edited). Scripts: scratchpad/da/ (addver.py, tac.py, rdeps.py, acscan.py), scratchpad/p2/da*.py.

| Finding | Fix | Files changed |
|---|---|---|
| DA-01 | Ten uncovered testable IDs now cited in a Referenced TRDs bullet plus a new FR row: ARC-100 (FEAT-018-FR-20), ARC-100/ARC-101 (FEAT-019-FR-22), ARC-102 (FEAT-008-FR-18), ARC-103 (FEAT-015-FR-12), ARC-104 (FEAT-078-FR-20), ARC-105 (FEAT-009-FR-16), ARC-035 (FEAT-035-FR-11), DME-018 (FEAT-026-FR-19), FE-090/FE-091 (FEAT-062-FR-24, presentational components get data as props and never fetch), TPS-040 (FEAT-088-FR-15) | FEAT-008, 009, 015, 018, 019, 026, 035, 062, 078, 088 |
| DA-02 | New BACKLOG §11.1 "Requirements not implemented as features": VIS (24 IDs, in 2 rows: constraints restated by lower-level requirements; process rows), RAQ-001..RAQ-018 (TRD 24 governance), AGT-002/003/011 (agent rules), with where each group is satisfied | BACKLOG.md |
| DA-03 | 436 feature ACs that named no test ID, test file or method now end with "Verified by: …": a test level with a test file and/or TRD 13 test ID from the feature's Testing Requirements, the command in the criterion, or Inspection/Demo/Analysis with what is checked (method taken from the cited requirement's Verification column). Rescan: 0 ACs without a test or method. New BACKLOG §11.2 maps the 72 uncited TRD ACs (the audit listed 73 but its list holds 72) to the feature that realises each; rescan: 0 of 281 TRD ACs uncited | 93 feature files; BACKLOG.md |
| DA-04 | FEAT-001-FR-05: data alerts (stage 11) then analytics aggregates (stage 12, last) | FEAT-001 |
| DA-05 | UX-141 same-date order (alarm_on, watching_started, baseline_complete, baseline_restarted, quarantined, set_aside, device_silent, missed) added to FEAT-028-FR-08 and its note, TRD 05 API-077 and TRD 19 E-10; new FEAT-028-AC-10 same-date fixture case | FEAT-028; TRD 05, TRD 19 |
| DA-06 | Kept FEAT-061 Optional (BACKLOG §8.2: Optional never blocks a DoD; TDV-080..083 and CIC-037 are Should). Dropped FEAT-061 from FEAT-080's dependencies in BACKLOG §4/§5/§6, mermaid edge, roadmap table and Phase 12.2 note, and the feature header. FEAT-080 runs `tests/validation/robustness.py` only if it exists; FR-08 and AC-03 say so. Graph now has 210 edges | BACKLOG.md, IMPLEMENTATION_ROADMAP.md, FEAT-080 |
| DA-07 | BACKLOG §1 and roadmap inputs name "the decision log (every D-xx row of TRD 24 §4.6)" and "every open question OQ-xx", not a fixed range | BACKLOG.md, IMPLEMENTATION_ROADMAP.md |
| DA-08 | FEAT-069 FR-266 note deleted and FR-06 wording fixed. Stale "conflicts reported in the batch report" DoD bullets in FEAT-026, 028, 033, 034, 036, 038, 045, 048, 050, 064, 066, 069, 072 now say the batch report lists the implemented IDs and the differences were resolved in PR #2 (or name D-83, D-84, OQ-29). "Former TRD conflict" notes in FEAT-038/044 now read "Resolved (PR #2)" | 14 feature files |
| DA-09 | AC-AGT-01 and L.01 now: Phases 1–11 one PR each in TRD 25 §4.5 order; Phase 12 before Phase 2 (AGT-031, PR #2) and re-run after Phase 11 (D-95) as one further PR. The roadmap names the re-run branch `docs/backlog-reconcile` and its own PR | TRD 25, MVP_READINESS_CHECKLIST.md, IMPLEMENTATION_ROADMAP.md |
| DA-10 | "<n> of <N> usable check-ins" and "Once <N> usable check-ins are collected" (UX-186, UX-192, TRD 11 §8 note, FEAT-073-FR-03/FR-09) | TRD 11, FEAT-073 |
| DA-11 | TRD 25 Phase 5 router list adds `config.py` (GET /api/v1/config/ui, E-32) | TRD 25 |
| DA-12 | "All FEAT-NNN acceptance criteria pass." added to the 35 DoDs without that exact clause. The 48 informal dependents lines ("builds directly on" / "Downstream:") replaced in all 97 files by one line generated from BACKLOG §4: "Features that build directly on this one (BACKLOG.md §4): …" (FEAT-059 keeps the AGT-023 gate sentence) | 97 feature files |

New revision rows (20 Oct 2026) and version bumps: TRD 05 0.11, TRD 11 0.11, TRD 19 0.5, TRD 25 0.12, BACKLOG 0.3, IMPLEMENTATION_ROADMAP 0.2, MVP_READINESS_CHECKLIST 0.2.

## Checker results
- verify.py: RESULT PASS (97 features, 210 edges, acyclic, valid order, mermaid matches, 211 FRs covered, 0 undefined cited IDs).
- check_feat_001_025.py 1 97 (idx.json regenerated): ALL CHECKS PASSED, 0 errors.
- p2/chk.py: no duplicate or dangling D/OQ IDs, balanced fences, 0 bad table rows. Roadmap and both checklists: fences balanced, 0 bad table rows.
- No TBD/TODO/[placeholder] in specs/TRD or specs/backlog. Feature ACs without a test or method: 0. TRD ACs uncited by the backlog: 0 of 281.
