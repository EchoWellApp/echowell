# Phase 1 TRD fix log (19 Oct 2026)

Source: docs/reports/TRD_VALIDATION_REPORT.md (55 findings). All edits are in specs/TRD/; every changed TRD is now Version 0.2 with a revision-history row listing its findings.

New IDs: SEC-109, PGS-044, DB-065, DB-066, API-137, DEP-119, CIC-114, CIC-115, CIC-116, endpoint E-32 (GET /api/v1/config/ui), decisions D-56 to D-66, risk RSK-15. No new OQ.

Re-run mechanical checks after the fixes: no duplicate requirement IDs, no dangling requirement/D/OQ/ASM/RSK/DSC IDs (only 'next free' text in TRD 24 §8), every /api/v1 path is in TRD 19 E-01..E-32 (except the endpoints that are declared not to exist), table.column references match the TRD 20 DDL, env-var names are defined in TRD 21, code fences balanced in all 26 files, no TBD/TODO/lorem outside GIT-053. TRD 20 DDL executed cleanly on PostgreSQL 16.15 (scratch database), and the relaxed processed_sessions and audit_logs CHECKs were exercised with accept/reject cases.

| Finding | Severity | What changed (TRDs and requirement IDs) | Status |
|---|---|---|---|
| F-01 | Critical | TRD 07, 09, 10, 12, 15, 20, 23: TRD 12 §4.12 table +8 actions + vocabulary rule, SEC-109 (new); TRD 20 audit_logs_action_ck regex ^[a-z_]+(\.[a-z_]+){1,2}$, PGS-044 (new); CUS-016, CUS-018, CUS-039; ANL-040 + §4.8 diagram; ING-058; DEP-071; TRD 23 §4.2.23 action row | Fixed |
| F-02 | Critical | TRD 06, 08, 20, 23, 24: TRD 20 processed_sessions: new column late_arrival + relaxed epoch/status_reason/ordinal/in_baseline CHECKs (tested in scratch PG16), PGS-012; BSC-040 stored representation; TRD 23 §processed_sessions epoch_id/reasons/baseline_ordinal/in_baseline + late_arrival attribute; TRD 06 ER diagram; D-57 (new) in TRD 24 | Fixed |
| F-03 | Critical | TRD 01, 03, 06, 07, 08, 09, 12, 15, 20, 24: D-56 (config key split + rebuild CLI); ANL-030, ANL-032; NFR-084; CUS-046; DB-016; ARC-043, ARC-070; BSC-030; TRD 15 §4.8 CLI table (new rebuild command); TRD 20 §4.3 login-role table, §4.8 privilege matrix; TRD 12 audit action pipeline.rebuild | Fixed |
| F-04 | Major | TRD 01, 05, 06, 07, 10, 15, 17, 20, 24: DB-021 single source (advisory_key helper, xact locks only, keys a-d, no global lock); ARC-063; API-043, API-064, TRD 05 §4.4 ingest sequence; ANL-034; ING-038; TRD 15 §8 nightly note; LOG-110; TRD 20 §8 pooler pitfall; D-62 (new) in TRD 24 | Fixed |
| F-05 | Major | TRD 05, 07, 17, 24: Per-resident transactions (owner ARC-064/DB-013): TRD 07 §4.8 intro + sequence diagram, ANL-036, ANL-041; LOG-061, LOG-062; TRD 05 §4.4 ingest sequence; D-63 (new) in TRD 24 | Fixed |
| F-06 | Major | TRD 02, 23, 24, 25: FR-110 (pipeline-only closure, no manual close), D-03, AGT-058, TRD 23 alerts status/closed_reason/closed_at + state diagram | Fixed |
| F-07 | Major | TRD 02, 24: FR-110 and D-03 now list superseded by rebuild as second closure path | Fixed |
| F-08 | Major | TRD 02, 05, 09, 19, 23: FR-273 (create-or-link behaviour defined; strings from UX §4.17.2), API-130, CUS-040, DME-021, TRD 23 §4.3 data-alert table, TRD 19 E-14 | Fixed |
| F-09 | Major | TRD 02, 04, 05, 06, 11, 19, 23: TRD 02 §4.1 glossary: single definitions 'Silent day (device)' and 'Device-gap day' mapped to TRD 19 fields, 'No-upload day' retired; FR-153, FR-154, FR-156, FR-294, UC device panel outputs, notes; DB-044; TRD 19 E-17 example total 12->10 + definitions; API-086; TRD 04 §4.6.3; TRD 11 §4.4 silent text, card rules, UX-055, UX-057, UX-142, §6; TRD 23 §4.4.2 rows | Fixed |
| F-10 | Major | TRD 04, 05, 06, 11, 19, 23, 24: DB-065 (new, derived restart cause), DB-066 (new, derived in_use_until); TRD 19 CheckinEvent restart_cause/previous_device_code/from_value/to_value + RestartCause schema, Device.in_use_until, E-10 and E-17 notes; API-077, API-086; TRD 04 §4.6.3; D-64 (new) in TRD 24; TRD 23 §4.4.4 events (alarm_on, derived restart fields) | Fixed |
| F-11 | Major | TRD 04, 11, 23, 24: TRD 04 §4.6.3 rewritten as aliases of generated TRD 19 types (+ §5 note); TRD 11 §4.3 summary.missed_last_30_days and §6 field names; TRD 23 §4.6 DTO class names = TRD 19 schema names; D-64 in TRD 24 | Fixed |
| F-12 | Major | TRD 02, 04, 05, 07, 11, 12, 19, 24: (a) new E-32 GET /api/v1/config/ui + UiConfig/ReviewExplanation schemas + path + summary row, OAS-020 range, API-137 (new), TRD 05 §4.1 router tree and §4.12 endpoint summary, TRD 12 role matrix, TRD 04 getUiConfig + FE-136, UX-313, TRD 11 §6; (b) ByResidentRow split into set_aside_days/quarantined_days (schema + E-18 example), TRD 07 §4.13 by_resident; (c) ComparisonStatus range_not_available + E-22 note, FR-202, UX-185; (d) see F-10; D-64 in TRD 24 | Fixed |
| F-13 | Major | TRD 04, 15, 16, 21, 24: NEXT_PUBLIC_API_BASE_URL = origin only: TRD 21 variable table, .env.development.example, production template, environment matrix; TRD 15 compose frontend env + frontend-prod args; TRD 16 frontend job env; FE-070 reads it via lib/config.ts; D-65 (new) in TRD 24 | Fixed |
| F-14 | Major | TRD 04, 12, 15, 22, 24: TRD 12 §4.9 single owner, hostnames echowell-backend-staging/-production, SEC-070 build command; FE-060 (no middleware CSP in MVP), FE-061; TRD 15 netlify.toml headers copied verbatim + build command, step 3, DEP-045 HSTS includeSubDomains, DEP-050, DEP-053; TPS-051; D-65 in TRD 24 | Fixed |
| F-15 | Major | TRD 15: DEP-119 (new) + compose outline: backend bind-mounts database/ and tests/fixtures/ read-only (local + E2E CI); staging reseed uses CI checkout | Fixed |
| F-16 | Major | TRD 01, 06, 12, 15, 16, 21, 24: D-58 + RSK-15 (new): migrations = Railway pre-deploy command; DEP-022, DEP-040, DEP-060, §4.5 step 2, railway.toml, §4.9 step 3, AWS secrets row (migration task only); TRD 16 §4.1 justification 5, diagram, CIC-003; SEC-111 + role table; DB-028 + §8 note; ARC-015 (adds DATABASE_READONLY_URL); TRD 21 DATABASE_MIGRATION_URL row | Fixed |
| F-17 | Major | TRD 00, 15, 21, 24: D-59 (new): staging keeps fixed PIPELINE_AS_OF for the answer key; live demo check-in goes to interim production (T-prefixed demo ID, as-of = now). AC-VIS-03; TRD 15 environment matrix Data row; ENV-017 | Fixed |
| F-18 | Major | TRD 17: TRD 17 §4.5 code table now a subset of the TRD 05 catalogue (NOT_AUTHENTICATED etc., 409 codes, SERVICE_UNAVAILABLE; pipeline outcomes are lower-case warning codes); LOG-043 (lower-case field codes per TRD 05/ING-023), LOG-044, LOG-052 (SERVICE_UNAVAILABLE, Retry-After 30) | Fixed |
| F-19 | Major | TRD 00, 03, 04, 13, 16: e2e.yml runs on every PR (Chromium + a11y; nightly 3 browsers), CIC-031, CIC-070 adds `playwright` (8 required checks, AC-CIC-08); TST-150 lists the job names; TST-110 is the single route list referenced by FE-190, SC-07, NFR-060, AC-NFR-04 | Fixed |
| F-20 | Major | TRD 13, 16: ci.yml: repo-hygiene forbidden-term + LLM-dependency steps, backend-lint lint-imports, security-audit gitleaks + Bandit; new CIC-114, CIC-115, CIC-116 (Lighthouse job); CIC-070; TST-125, TST-136 references | Fixed |
| F-21 | Major | TRD 02, 10: FR-120 inclusive end date stated; ING-048 and §4.10 pseudocode now through withdrawn_on inclusive (matches DB-023, AC-DB-10) | Fixed |
| F-22 | Major | TRD 10: ING-017 targets may be any of the 30 canonical field names (11 record fields + 19 features), so the TRD 20 §4.11 seed validates | Fixed |
| F-23 | Major | TRD 03, 06, 12, 15, 22, 24: D-60 (new): single target in NFR-024/NFR-025 (AWS: RDS PITR >= 7 d, RPO <= 24 h, RTO <= 8 working h, drill before go-live + every 6 months; interim waiver: Neon window + weekly dump, one drill before 15 Nov 2026); DB-050, DB-051, SEC-162, DEP-095, DEP-097, TRD 22 Neon row | Fixed |
| F-24 | Major | TRD 02, 11, 13, 14: 'Baseline Oct 1–Oct 16' -> 'Baseline Oct 1–16' in AC-FR-09, TST-093, E2E-08, TRD 14 §4.9; AC-UX-06 rewritten (note and review are separate; UX-123/130/137) | Fixed |
| F-25 | Major | TRD 02, 09, 11: FR-261 is the single queue-order definition (unreviewed/unsnoozed, snoozed, reviewed; then date, code); TRD 09 §4.8 and UX-301 reference it | Fixed |
| F-26 | Major | TRD 07, 24: TRD 07 §4.7: PipelineConfig.operational + OperationalConfig table (5 keys) with hashing rule; ANL-029 validation | Fixed |
| F-27 | Minor | TRD 00: S-01..S-13 in MVP feature set and §8 note; S-rows and §9 OQ rows sorted | Fixed |
| F-28 | Minor | TRD 11, 12, 24, 25: TRD 24 scope: R1–R27, D-01..D-66, RSK-01..RSK-15, next free D-67/RSK-16 (§8), AC-RAQ-03; AGT-002 cites SRC-01..SRC-19 and D-01..D-66; TRD 11 and TRD 12 reference rows R1–R27 | Fixed |
| F-29 | Minor | TRD 02: FR-191: button hidden (not disabled) without an open alarm | Fixed |
| F-30 | Minor | TRD 04, 07: TRD 04 §4.2 tree adds alerts/ and analytics/ pages; FE-032 titles; AppHeader active union; AlertsPage and AnalyticsPage in the §4.8 inventory; inventory props use TRD 19 types (BaselineProgress, BaselinePeriod, DailySeriesPoint, Funnel, ByResidentRow, ReviewOutcomes, ReviewExplanation); TRD 07 §4.13 daily_series uses TRD 19 silent_device_codes | Fixed |
| F-31 | Minor | TRD 04: FE-204 budget = 300 kB gzip for every route (TRD 03 NFR-012 owner) | Fixed |
| F-32 | Minor | TRD 01, 07: TRD 01 §4.4 'twelve stages' + row 12, container table/diagram numpy-only runtime (pandas tests only), stages 1–12; ANL-007 CLI moved to scripts/run_engine.py outside analytics/ | Fixed |
| F-33 | Minor | TRD 01: ARC-057 and AC-ARC-09 accept only sslmode=require or verify-full (TRD 21 ENV-011, API-059) | Fixed |
| F-34 | Minor | TRD 05: TRD 05 §4.12 endpoint summary rows POST /sessions (no ingest_batches) and POST /ingest (writes ingest_batches) | Fixed |
| F-35 | Minor | TRD 10, 23: ING-004: stored rejection errors identical to the response (no value echo; raw_body keeps values), as API-041; TRD 23 JSON shape row | Fixed |
| F-36 | Minor | TRD 02, 05: FR-003 and API-048 follow TRD 10 ING-031 (exact field set, any order) | Fixed |
| F-37 | Minor | TRD 02, 11, 23: FR-291, UX §4.17.2 table and TRD 23 §4.3.7 use the TRD 09 inclusive day count ((as-of − epoch start) + 1 ≥ baseline_n) | Fixed |
| F-38 | Minor | TRD 07: TRD 07 §4.13 kpis.alarms_raised note uses the UX-355 wording | Fixed |
| F-39 | Minor | TRD 05, 17, 19: LOG-042 (API-096 text), LOG-071 (2 s), LOG-066 + API-068 (run_abandoned), LOG-080 (FE-145 copy), LOG-081 (FE-035 copy), LOG-112 (50 runs, FR-225), LOG-110 trace DEP-046; TRD 19 warnings example codes | Fixed |
| F-40 | Minor | TRD 03, 13, 16: NFR-020, NFR-104 aligned to the 30-minute uptime check (CIC-060/061, DEP-102); TST-151 label ci-failure (CIC-033) | Fixed |
| F-41 | Minor | TRD 05, 06, 07, 17, 19, 23: Canonical shapes owned by TRD 23 §4.2.10: counts keys (12 keys), warnings {code, resident_code, session_id, detail}, code_version default unknown, config_snapshot = 23 keys + config_hash + as_of; TRD 07 PipelineResult.counts, ANL-033, ANL-041 (sets error_message), ANL-052; DB-016, DB-020; LOG-062, LOG-065; TRD 19 PipelineRun.warnings schema + example counts; API-055 lower-case code | Fixed |
| F-42 | Minor | TRD 12: SEC-102 and the §8 trigger note aligned with TRD 20 (reject_mutation(), triggers on raw_sessions/audit_logs only; alert_reviews/staff_notes append-only by grants) | Fixed |
| F-43 | Minor | TRD 04, 10, 12, 19, 20: Single code pattern ^[A-Z0-9]{1,16}$: TRD 20 residents/devices CHECKs (DDL re-tested), TRD 19 ResidentCode/DeviceCode/SessionId + E-09, SEC-084, FE-030, TRD 10 session_id rule | Fixed |
| F-44 | Minor | TRD 10, 20, 23: raw_sessions.phrase_id NOT NULL + raw_sessions_phrase_id_ck (1–16 chars), PGS-011; TRD 10 §4.4 mean_f0_hz rejects <= 0; TRD 23 phrase_id row (DDL re-tested) | Fixed |
| F-45 | Minor | TRD 12, 18, 22: TRD 18 lint/format rows follow FE-200 (jsx-a11y/strict) and FE-201 (singleQuote false); GIT-081 aligned with SEC-053 (Should, where plan allows); SEC-150 = TRD 18 §4.12 dependabot outline; TRD 22 fonts 400/600 (FE-004) | Fixed |
| F-46 | Minor | TRD 04: FE-170 adds NEXT_PUBLIC_GIT_SHA and lib/config.ts (ENV-030/033); FE-172 ribbon text = ENV-032 | Fixed |
| F-47 | Minor | TRD 05, 12, 24: CORS_ORIGIN_REGEX kept in TRD 21 and allowed by TRD 12 for staging deploy previews only (SEC-094, §8 pitfall); API-101 uses it when set; D-66 (new) in TRD 24 | Fixed |
| F-48 | Minor | TRD 15, 21: DATABASE_READONLY_URL set only where test_v0_1 (never production/AWS): TRD 21 variable row, production template, environment matrix; TRD 15 §4.4 step 6, AWS secrets row, cut-over row; .env.development.example uses echowell_app_login (and migrator/readonly logins) | Fixed |
| F-49 | Minor | TRD 05, 15: Rollback uses revoke-api-key; CLI table withdraw-resident <code> --on <date> (DB-062/DME-009); API-061 skips on running or succeeded (DEP-047 owner); AC-DEP-01 under 10 min (NFR-087) | Fixed |
| F-50 | Minor | TRD 13: TST-011 adds data_alerts and aggregates; CFG-03 ConfigError (ANL-029); E2E-14 precise access-denied expectation; E2E-21 'replaced' per UX-322; TST-013 Must (NFR-111) with inspection evidence route | Fixed |
| F-51 | Minor | TRD 14: TDV-081 rate = count over R01–R06 / 600, R07/R08 reported but excluded (matches TRD 09 61/600) | Fixed |
| F-52 | Minor | TRD 06, 07, 13, 14, 20: ANL-042 is_morning mapping per sheet (yes/no in Annotated_sessions, boolean in Exp_scores); AC-PGS-14 ground truth from loader not seed; DB-056 count list explained; DS-07 and TRD 14 §4.9 roster = database/seeds/test_v0_1/ (single source), TRD 13 fixtures tree | Fixed |
| F-53 | Minor | TRD 25: Workflow merges to staging (GIT-012); Phase 4 users/admin per DB-056/DB-057/SEC-017 (no admin from env); Phase 6 and Phase 8 input lists completed; AGT-060 exports via API CSV, readonly role for offline SQL and analytics_summary only | Fixed |
| F-54 | Minor | TRD 23: AC-DME-01 24 classes; DME-005 batch report returns only TRD 19 IngestRejection fields (no raw_body); §4.2.22 PipelineConfig.from_mapping | Fixed |
| F-55 | Minor | TRD 24: D-61 (new): analytics as root package analytics/ imported by and deployed with the backend = reading of SRC-01 | Fixed |

## Round 2 fixes


Source: docs/reports/TRD_VALIDATION_REPORT.md round 2 (R2-01..R2-26: 3 Major, 23 Minor). Edits only in specs/TRD/; changed TRDs (all except 08, 11, 22) are Version 0.3 with a round-2 revision row.

New IDs: D-67 (R2-01), D-68 (R2-02), D-69 (R2-03), D-70 (R2-25) in TRD 24; ENV-053; TST-185, TST-186; new CLI command `set-config` (TRD 15 §4.8). No new OQ or RSK.

Mechanical checks re-run: no duplicate or dangling requirement IDs (AC-DB-02a is defined as list item '2a.'); all D/OQ/ASM/RSK/DSC references defined (only 'next free' text D-71/OQ-27/RSK-16); all /api/v1 paths in TRD 19 (except the endpoints declared not to exist, and the example path /residents/R09); table.column references match the TRD 20 DDL; code fences balanced; no TBD/TODO/lorem outside GIT-053; TRD 20 DDL runs on PostgreSQL 16.15 and the CHECK tests still give the expected 5 rejections.

| Finding | Severity | What changed (TRDs and requirement IDs) | Status |
|---|---|---|---|
| R2-01 | Major | TRD 00, 02, 03, 13, 24: D-67 (new): usable check-ins are not log events; 'shows on the dashboard' = Last check-in + 30-day used +1, and one more tally bar when the baseline is frozen. FR-184, SC-03, AC-VIS-03, TRD 00 §6 demo step 5 row, NFR-011, TST-181, E2E-15 | Fixed |
| R2-02 | Major | TRD 06, 13, 14, 15, 16, 20, 24, 25: D-68 (new): `seed test_v0_1` = roster CSVs (via import-master-data) + users/API key + SRC-05 ingest + pipeline at as_of 2026-10-30 15:00; `--master-only` = roster only; refused in production; no `--with-input`. DB-056, DB-058, DB-060 (facilities.csv, firmware column), AC-DB-01, TRD 06 §8 seed-file note; TRD 20 §4.12 SQL roster replaced by the CSV file contents (+ DS-10 CSV), PGS-026, §2 scope; TRD 15 §4.8 import-master-data and seed rows, DEP-015, DEP-119; TRD 13 §8 E2E note (backend.scripts.load_fixture removed); TRD 14 DS-07; TRD 16 CIC-030; TRD 25 Phase 4 outputs | Fixed |
| R2-03 | Major | TRD 02, 03, 07, 09, 12, 13, 15, 21, 23, 24: D-69 (new): new CLI `backend.cli set-config --profile --key --value --reason` (TRD 15 §4.8 row; migrator role; schema validation; audited config.changed with old/new/reason; algorithm keys print the rebuild instruction and runs fail with config_changed_requires_rebuild until rebuild). FR-229, FR-250, NFR-084, D-56, ANL-032, ANL-055, ANL-058, CUS-034 (set-config then rebuild), TRD 21 §4.4 row, TST-053, TRD 12 audit vocabulary row config.changed + SEC-103, TRD 23 §4.2.22 value row | Fixed |
| R2-04 | Minor | TRD 04: FE-041: middleware sets Cache-Control only, no CSP nonce | Fixed |
| R2-05 | Minor | TRD 15, 25: TRD 15 §4.5 step 6 lists the nightly job's variables explicitly (no migrator/readonly/JWT/CORS); TRD 25 Phase 4 and Phase 10 commands use root alembic.ini and the D-58 pre-deploy step | Fixed |
| R2-06 | Minor | TRD 01, 07, 25: TRD 07 §4.2 pipeline.py has no CLI (scripts/run_engine.py); TRD 01 repo tree and §8 module list add aggregates.py; TRD 25 Phase 3 and Phase 6 module lists add data_alerts/aggregates | Fixed |
| R2-07 | Minor | TRD 01, 17, 23: TRD 17 §4.6.2 state diagram per-resident (D-63); TRD 17 request-ID sequence no longer puts request_id in counts (logs + pipeline.run.started audit row); TRD 23 §4.5 counts example has the 12 keys; ARC-100 aligned | Fixed |
| R2-08 | Minor | TRD 10: ING-030: trigger only on raw_sessions (TRD 20 PGS-018); ingest_rejections append-only by grants (PGS-021) | Fixed |
| R2-09 | Minor | TRD 13: DA-01 and DA-02 restated with the inclusive day count ((as_of − start) + 1); DA-02 = 15 < 16 no alert, plus 16 ≥ 16 boundary case | Fixed |
| R2-10 | Minor | TRD 01, 07, 13, 15: Rollback step issues new keys with create-api-key (no re-activate); one nightly dedupe condition (running or succeeded on the facility-local date, API-061/DEP-047) in ARC-061, TST-052, ANL-045 | Fixed |
| R2-11 | Minor | TRD 07, 19: One model (TRD 06 DB-036 owner, TRD 23 §4.3.7): ANL-060 references DB-036 (new open row on recurrence, never reopen; timestamps = run as_of); TRD 19 E-30 example uses as_of | Fixed |
| R2-12 | Minor | TRD 07, 21: ENV-021, ANL-031 and ANL-052 agree: missing key -> default + config_default_used; no profile rows or invalid value -> run fails with pipeline_config_invalid (listed as a failure code) | Fixed |
| R2-13 | Minor | TRD 02: FR-195 uses the UX-125 note text verbatim | Fixed |
| R2-14 | Minor | TRD 04, 13: TST-090 uses the TRD 04 §4.8 component names; TRD 04 §4.6.3 adds aliases ResidentDetail, StaffNote, AdmissionRow, AdmissionComparison | Fixed |
| R2-15 | Minor | TRD 07: ANL-044 scope = API-053 definition (incl. co-assigned residents) | Fixed |
| R2-16 | Minor | TRD 05, 06: TRD 05 §6 dependency and TRD 06 §4.4 sequence quote the binding run_pipeline(records, residents, assignments, config, as_of, *, frozen_baselines) signature; engine called once per run, writes per resident | Fixed |
| R2-17 | Minor | TRD 06, 07, 09: CUS-018, DB-018 and ANL-039 set closed_at = run as_of on every close (alerts_closed_ck) | Fixed |
| R2-18 | Minor | TRD 16, 21: e2e.yml loads DS-10 ground truth after seeding; staging reseed passes DATABASE_URL/DATABASE_MIGRATION_URL (migrator), APP_ENV, PIPELINE_PROFILE, PIPELINE_AS_OF, FACILITY_NAME, FACILITY_TZ; new ENV-053 (operator commands validate only the variables they use) | Fixed |
| R2-19 | Minor | TRD 04, 14: One generator and path: npm run fixtures:capture -> frontend/tests/fixtures/ds07/ (TRD 04 §4.11/§4.12 notes, TDV-016) | Fixed |
| R2-20 | Minor | TRD 16: CIC-116 pins @lhci/cli 0.14.x (as TRD 13) | Fixed |
| R2-21 | Minor | TRD 18: GIT-010: linear history on staging only; main allows the release/back-merge merge commits of GIT-013/GIT-014 | Fixed |
| R2-22 | Minor | TRD 13: TST-152: authenticated smoke on staging only; production smoke = unauthenticated DEP-081 checks | Fixed |
| R2-23 | Minor | TRD 02: UC-13 uses two single-value status calls (E-13 accepts one enum value) | Fixed |
| R2-24 | Minor | TRD 01, 05: Single-record ingest is not audited (vocabulary audits batches only): API-032, TRD 05 §4.12 row, TRD 01 ingest sequence note | Fixed |
| R2-25 | Minor | TRD 01, 05, 07, 15, 24: D-70 (new): POST /pipeline/run with a pipeline:run API key records trigger = nightly, scope all, with the API-061 once-per-night dedupe (202 with the existing run id); API-065, ANL-045, DEP-116, TRD 01 AWS mapping row, D-47 | Fixed |
| R2-26 | Minor | TRD 13: New TST-185 (FR-205/DB-025 new-admission -> own-baseline transition, Must) and TST-186 (populated facility comparison: API statuses + FacilityRangeChart, Should) | Fixed |

## Round 3 fixes


Source: docs/reports/TRD_VALIDATION_REPORT.md round 3 (R3-01 Major, R3-02..R3-10 Minor). Edits only in specs/TRD/; every changed TRD is Version 0.4 with a round-3 revision row.

New IDs: D-71 (TRD 24), TST-187; new TRD 21 variables SEED_ADMIN_PASSWORD, SEED_CLINICIAN_PASSWORD, SEED_RESEARCHER_PASSWORD, SEED_INGEST_API_KEY and GitHub secrets STAGING_SEED_*; retired STAGING_SMOKE_EMAIL/PASSWORD and E2E_USER_*.

Scratch PostgreSQL 16.15 check for D-71 (scratchpad t_downgrade.sh + downgrade_base.sql): superuser creates roles, extensions and schema owner; the TRD 20 DDL runs as echowell_migrator (exit 0); with data present, dropping every table/type/function as echowell_migrator succeeds (DROP fires no reject_mutation trigger; FKs go with the tables), leaving 0 tables and 0 enums; re-running the DDL as echowell_migrator succeeds (exit 0) with 24 migrator-owned tables, 17 triggers, 46 config_parameters rows and grants restored (echowell_app INSERT but not DELETE on raw_sessions; readonly SELECT on evaluation_ground_truth; app none).

Mechanical checks re-run: no duplicate/dangling requirement IDs; D/OQ/ASM/RSK/DSC references all defined (only 'next free' text); endpoints, table.columns and env vars consistent with TRD 19/20/21; code fences balanced; no TBD/TODO/lorem outside GIT-053; DDL and CHECK tests unchanged (5 expected rejections).

| Finding | Severity | What changed (TRDs and requirement IDs) | Status |
|---|---|---|---|
| R3-01 | Major | TRD 06, 15, 16, 20, 24, 25: D-71 (new): reset-test-db = alembic downgrade base + upgrade head as echowell_migrator (SET ROLE), refused unless APP_ENV in {local,test,staging} and PIPELINE_PROFILE=test_v0_1; no TRUNCATE/purge path (DROP fires no triggers; grants and config seed come back with the migrations, PGS-022); seed --reset = reset-test-db + seed; seed upserts users/key by email/name and never prints secrets. DB-024, DB-057, DB-056, AC-DB-08; TRD 20 PGS-019 (purge path only for IRB purge), §4.3 SET ROLE rule, §4.12 text; TRD 15 §4.2 steps 7-8, §4.8 seed and reset-test-db rows, DEP-071; TRD 16 §4.4 step 4; TRD 25 Phase 4. Verified on scratch PG16: DDL as migrator, drop all objects as migrator, DDL again -> exit 0, 24 tables, grants, 46 config rows, 17 triggers | Fixed |
| R3-02 | Minor | TRD 12, 15, 20: Closed migrator list (TRD 20 §4.3, TRD 12 role table, SEC-111, DEP-040) = seed, reset-test-db, purge-resident, rebuild, set-config, load_evaluation_ground_truth.py; all SET ROLE echowell_migrator | Fixed |
| R3-03 | Minor | TRD 01, 06, 23: TRD 01 §4.7 trigger table adds the AWS scheduler row (nightly, D-70) and limits manual to admin JWT/CLI; TRD 23 §4.2.10 trigger row; DB-058 seed run uses trigger manual (test reserved for the validation suite) | Fixed |
| R3-04 | Minor | TRD 01: TRD 01 ingest sequence and §8 note quote the binding TRD 07 run_pipeline signature | Fixed |
| R3-05 | Minor | TRD 07: ANL-058 reworded: features is a built-in config.py field; change = reviewed config.py code change + deploy + rebuild (set-config cannot change it) | Fixed |
| R3-06 | Minor | TRD 00, 03, 13: New TST-187 automated 5 s ingest-to-dashboard timing test (E2E job, warm stack) tracing NFR-011/SC-03; TST-181 notes its 60 s demo limit; NFR-011 and SC-03 verification cells | Fixed |
| R3-07 | Minor | TRD 06, 12, 13, 15, 16, 21, 24, 25: Deterministic seeded users/key (D-71): new TRD 21 vars SEED_ADMIN_PASSWORD, SEED_CLINICIAN_PASSWORD, SEED_RESEARCHER_PASSWORD, SEED_INGEST_API_KEY (test/staging/local only, secret, refused in production; local values in .env.development.example; ENV-053); e2e.yml generates and ::add-mask::s them, no create-user step, CIC-034; staging secrets STAGING_SEED_* (re-seed and smoke), §4.9 table, CIC-090, AC-CIC-06; DEP-080(c) smoke user = seeded researcher; TRD 13 Table 4.10-A login note; E2E_USER_* retired; SEC-050 | Fixed |
| R3-08 | Minor | TRD 13: demo overlay is a CSV directory tests/fixtures/seeds/demo_overlay/ (DB-060 format) loaded by import-master-data (E2E-15 and fixture tree); fixture tree lists evaluation_ground_truth_v0_1.csv under answer_key/ (as TDV-012) | Fixed |
| R3-09 | Minor | TRD 12: TRD 12 §4.12 user.created and user.updated actor = user (API) or system (CLI/seed), matching SEC-103 | Fixed |
| R3-10 | Minor | TRD 06: DB-025 priority Should -> Must (FR-205, TST-185) | Fixed |

## Round 4 fixes


Changed TRDs (Version 0.5 and a "0.5 | 19 Oct 2026 | Phase 1 round-4 fixes (...)" row, only in these): 01, 05, 06, 12, 13, 15, 16, 20, 21, 24, 25.
New decision: D-72. D-71 amended (no new D). Next free decision: D-73.

Mechanical checks re-run:
- No duplicate or dangling requirement IDs. The only script hits are the known artefacts: source/BR/ASM/OQ reference rows, AC-DB-02a, and E2E rows whose names follow the ID.
- D-70..D-72 are all defined in TRD 24.
- Endpoints, `table.column` references and env vars agree with TRD 19, 20 and 21. The remaining hits are the same as in round 3 (error codes, workflow-local and GitHub variables, file names). No new env var was introduced.
- Code fences are balanced in all 26 files.
- No TBD, TODO or lorem outside GIT-053.

R4-02 verification on scratch PostgreSQL 16 (script `t_r4_ext2.sh`, using all `sql` fences of TRD 20):
- Without extensions, the migration-0001 check run as migrator fails with the clear message (exit 3).
- Provisioning as superuser (extensions, then roles) succeeded with exit 0.
- DDL as migrator: exit 0, with 24 tables, 17 triggers and 46 config rows.
- Drop-all as migrator: exit 0, with 0 tables, and pgcrypto and btree_gist kept.
- DDL as migrator again: exit 0, with 24/17/46. Grants are restored: app has INSERT but not DELETE on `raw_sessions`, and readonly has SELECT on `evaluation_ground_truth`.

| Finding | Severity | What changed (TRDs and requirement IDs) | Status |
|---|---|---|---|
| R4-01 | Major | TRD 06, 15 and 24. DB-029 and DEP-060 now state one exception: on staging, the D-71 `reset-test-db` (downgrade base, then upgrade head) may run only from the deploy-staging GitHub Actions re-seed step, only with PIPELINE_PROFILE=test_v0_1, and never in production. The TRD 15 §4.8 `reset-test-db` row was aligned with this. D-71 was amended to match. | Fixed |
| R4-02 | Major | TRD 06, 13, 15, 16, 20 and 24. New D-72: the provisioning step creates the extensions, never Alembic as migrator. Locally and in CI this is `provision_login_roles.sql` as superuser; on Neon it is the project owner role (TRD 15 §4.4 step 4); on AWS RDS it is the master user (DEP-117). The step runs `CREATE EXTENSION IF NOT EXISTS pgcrypto; CREATE EXTENSION IF NOT EXISTS btree_gist;` before any migration. Migration 0001 only checks for them and fails with a clear message (TRD 20 §4.2, PGS-002). `downgrade base` never drops them (DB-029). Also updated: TRD 15 §4.2, TRD 20 §4.3 and the project-owner note, TRD 16 CIC-015 and the ci.yml provisioning comment, and TRD 13 TST-040. Verified on PG16 (see above). | Fixed |
| R4-03 | Minor | TRD 15, 20 and 25. In the TRD 15 seed row, `--reset` now reads "see `reset-test-db` (D-71)". The TRD 20 §8 test note now says to use a fresh database from the migrations and never truncate `raw_sessions`, since the purge path is IRB-only. In TRD 25 Phase 4, `--master-only` loads the roster, users and key, and users and key are upserted from SEED_* (DB-057/DB-058). | Fixed |
| R4-04 | Minor | TRD 06. The DB-024 verification now expects `config_parameters` with 46 rows, `audit_logs` with exactly 1 row (`seed.reset`, written after the upgrade, D-71), and every other table empty. | Fixed |
| R4-05 | Minor | TRD 13 and 16. In `e2e.yml` the main Playwright run uses `--grep-invert @isolated`. A new step creates `echowell_demo` in the same Postgres service and provisions it with the same `provision_login_roles.sql` as superuser (extensions and roles). It restarts the backend on that database (the start command runs `alembic upgrade head`), then runs `seed test_v0_1 --master-only` and `import-master-data --dir tests/fixtures/seeds/demo_overlay`. The `@isolated` scenarios E2E-15, TST-187 and E2E-19 then run serially in Chromium. The main database stays exactly the test_v0_1 seed. CIC-030, E2E-15, E2E-19 (first ingests SRC-05 via `/ingest` and runs the pipeline at as_of 2026-10-30), TST-187 (a new session ID for R11) and TRD 13 §8 were updated. | Fixed |
| R4-06 | Minor | TRD 12 and 15. SEC-022: one or more scopes from {ingest:write, pipeline:run}, a non-empty subset matching `api_keys_scopes_ck`. SEC-020 and the TRD 15 `create-api-key` row: `--scope` is repeatable. | Fixed |
| R4-07 | Minor | TRD 06, 12, 16 and 21. In `.env.development.example`, SEED_* now hold obvious placeholders (`local-dev-only-change-me`, and `ewk_local-dev-only-change-me-change-me` for the key). The TRD 21 SEED_* row was updated to match. DB-057 and SEC-050 add the exception: placeholders are allowed and never valid in staging or production. ENV-041 makes the backend and CLI refuse (exit 2) any JWT_SECRET or SEED_* value containing `local-dev-only` when APP_ENV is staging or production. CIC-115 adds a gitleaks allow-list entry limited to these placeholders. | Fixed |
| R4-08 | Minor | TRD 01, 05, 06 and 21. ARC-019, TRD 05 §6 (DATABASE_MIGRATION_URL), the TRD 06 §8 note and the TRD 21 DATABASE_MIGRATION_URL row now refer to the binding closed list of TRD 20 §4.3. TRD 15 §4.4 step 4 was already updated under R4-02. | Fixed |
| R4-09 | Minor | TRD 20. The §2 scope line now reads "3 group roles", with the extensions "created by provisioning, checked by migration 0001". | Fixed |

## Round 5 fixes


Changed TRDs (Version 0.6 and a "0.6 | 19 Oct 2026 | Phase 1 round-5 fixes (...)" row, only in these): 03, 04, 05, 06, 12, 13, 15, 16, 20, 21, 24, 25.
New decision: D-73. D-71 and D-72 amended. New test: TST-188. Next free IDs: D-74, TST-189.

## Verification

**R5-01**, using the reviewer's libraries (`r5lib`: pydantic 2.9.2, email-validator 2.2.0), script `r5chk/emails.py`:
- `EmailStr` emits `{format: email, type: string}`.
- `admin@example.com`, `clinician@example.com` and `researcher@example.com` are accepted.
- `admin@echowell.test` is rejected.

**R5-06 and R5-07**, script `t_r5b.sh` (the reviewer's `t_r5.sh` with a timezone check added). All 33 sql fences of the current TRD 20 were re-extracted into `r5/`; the reviewer's copy is kept in `r5_reviewer_bak/`. Results:
- (0) Without extensions, migration 0001 as the migrator fails with the 0001 message (exit 3).
- (1) The provisioning fence as superuser (extensions plus `timezone`, on a database preset to America/Chicago), then roles: exit 0.
- (2) Migrations 0001 and 0002 as the migrator: exit 0, with 24 tables, 17 triggers, 15 enums and 46 config rows. `SHOW timezone` as the app login returns `UTC`.
- (2b) The provisioning fence run as the migrator is refused ("must be owner of database"). That is why 0001 never contains it.
- (3) Downgrade base as the migrator: exit 0, with 0 tables and the extensions kept.
- (3b) `DROP EXTENSION` as the migrator: "must be owner". That is why the downgrade never drops extensions.
- (4) Re-migrate: 24/17/15/46, and `timezone` is UTC.
- (5) All permission and trigger checks behave as specified.
- (6) Second database (the `echowell_demo` pattern): provisioning re-runs idempotently and migration succeeds.

## Mechanical checks

- **Requirement IDs:** no duplicate or dangling IDs. 2003 IDs are defined and referenced. The script hits are the same known artefacts as in round 4.
- **Decisions:** D-70..D-73 are all defined in TRD 24.
- **Endpoints, columns and env vars:** they agree with TRD 19, 20 and 21; the hits are the same as in round 4. No new env var was introduced: `PIPELINE_AS_OF` is set to empty with `-e`, which means current time.
- **Text hygiene:** code fences are balanced in all 26 files. There is no TBD, TODO or lorem outside GIT-053. No `@echowell.test` remains, and no old local/CI password (`*-local`, `*-ci`, `echowell`) remains.

| Finding | Severity | What changed (TRDs and requirement IDs) | Status |
|---|---|---|---|
| R5-01 | Major | TRD 06, 13, 15, 16, 20, 21 and 24. The seeded accounts are now `admin@example.com`, `clinician@example.com` and `researcher@example.com` (RFC 2606) everywhere: DB-057, D-71, TRD 20 §4.12, TRD 21 SEED_*/SMOKE_*/E2E rows, TRD 13 Table 4.10-A, the TRD 15 quick start and DEP-080, and TRD 16 §4.4 and e2e.yml. DB-057 and D-71 state that `example.com` passes standard `format: email` validation and that `.test` must not be used. New TST-188 logs in as each seeded user and validates the strings against `LoginRequest`. | Fixed |
| R5-02 | Major | TRD 03, 04, 13, 16, 24 and 25. New D-73: the e2e.yml main run is one Playwright invocation per browser project and group. The `globalSetup` `frontend/tests/e2e/global-setup.ts` resets and re-seeds the main database (`seed test_v0_1 --reset` plus the DS-10 loader) at the start of each. Read-only scenarios run first. The `@mutating` group (E2E-18, then E2E-09) runs last, serially. Updated: CIC-030, CIC-032, TRD 13 §4.10 preamble, TST-100, TST-004, E2E-09, E2E-18 and §8; TRD 04 E2E row, AC-NFR-10 and the TRD 25 Phase-frontend tests. | Fixed |
| R5-03 | Minor | TRD 13 and 24. E2E-19 advances no clock. It asserts the snoozed UI state and that `GET /api/v1/alerts` returns `snoozed_until` = click time + 24 h ± 2 min. Expiry is covered by TST-065, an integration test (`tests/integration/test_alert_snooze.py`) using time-machine. This is noted in D-73. | Fixed |
| R5-04 | Minor | TRD 13, 16 and 24. The `echowell_demo` backend runs with `PIPELINE_AS_OF` empty, so as-of is the current time (e2e.yml `-e PIPELINE_AS_OF=`, CIC-030, §8). E2E-15 and TST-187 post R11 records with `timestamp_utc` set to the current UTC time and fresh session IDs `R11-<local date>-01` and `-02`. E2E-15 no longer pins the as-of, and its last check-in is the local time of the posted timestamp. The overlay's R11 enrolment and D11 assignment moved from 2026-10-30 to 2026-10-01, so a current-time record is never before enrolment. | Fixed |
| R5-05 | Minor | TRD 03, 04 and 13. TST-100 and the §4.10 preamble are scoped to the main run and name the `@isolated` exception (Chromium only, `echowell_demo`). TST-004 now names `frontend-prod` :3001 and `playwright.isolated.config.ts` (no globalSetup), which the e2e.yml isolated run uses. AC-NFR-10 and the TRD 04 E2E row were aligned. | Fixed |
| R5-06 | Minor | TRD 15, 20 and 24. TRD 20 §8: 0001 takes only the §4.2 check block plus §4.4–§4.8, never the provisioning fence or role creation. Its downgrade drops only EchoWell objects, never an extension, role or setting. DEP-035: the D-72 provisioning step runs first as the Railway `postgres` superuser (and DATABASE_READONLY_URL is included). D-72 now lists Railway PostgreSQL and TRD 13. | Fixed |
| R5-07 | Minor | TRD 15, 16, 20 and 24. The provisioning step sets the current database's `timezone` to UTC: the TRD 20 §4.2 fence (a `DO … EXECUTE format('ALTER DATABASE %I …', current_database())` block), the §4.3 script description, PGS-001, TRD 15 §4.2, Neon step 4, Railway and the RDS step (DEP-117), the ci.yml comment and D-72. | Fixed |
| R5-08 | Minor | TRD 20. The `reject_mutation()` comment now reads "used only by the IRB withdrawal purge, PGS-019". | Fixed |
| R5-09 | Minor | TRD 24 and 25. The TRD 24 scope line and numbering rule, and AGT-002, now say "every D-xx of the TRD 24 §4.6 decision log" or "next free D after the last row", so they no longer go stale. TRD 13 was added to D-72. | Fixed |
| R5-10 | Minor | TRD 05, 12 and 15. SEC-020 is the single definition of the syntax: `[--scope …]…`, optional and repeatable, default `ingest:write`. TRD 05 §8 and the TRD 15 row use the same form and refer to it. | Fixed |
| R5-11 | Minor | TRD 06, 12, 15, 16 and 21. The committed local/CI database passwords were renamed: `local-dev-only-postgres`, `local-dev-only-migrator`, `local-dev-only-app` and `local-dev-only-readonly` in Compose, the template URLs and the e2e.yml demo step; `ci-only-postgres`, `ci-only-migrator`, `ci-only-app` and `ci-only-readonly` in ci.yml. The DB-057, SEC-050 and CIC-115 exceptions now cover `local-dev-only-*` and `ci-only-*` in Compose, ci.yml and the template. ENV-041 also refuses these patterns in the passwords of the DB URLs when APP_ENV is staging or production. SEC-056 is scoped to staging, production and AWS. DEP-018 was rewritten (no nonexistent template line). TRD 21 POSTGRES_* and ECHOWELL_*_DB_PASSWORD rows were updated. | Fixed |

## Round 6 fixes


**Changed TRDs:** 03, 04, 05, 09, 12, 13, 14, 15, 16, 18, 20, 21, 23, 24, 25. Each of these, and only these, now carries Version 0.7 and a row "0.7 | 19 Oct 2026 | Phase 1 round-6 fixes (...)".

**New IDs:** D-74, FE-205, ENV-054 and CIC-037. D-71 and D-73 were amended.

**Next free IDs:** D-75, FE-206, ENV-055, CIC-038, TST-189.

## Mechanical checks

- **Requirement IDs:** no duplicate or dangling IDs. 2006 IDs are defined and referenced. The only script hits are the known artefacts: AC-DB-02a, the endpoint list in TRD 19, and the E2E row names.
- **Decisions:** D-70 to D-74 are all defined. Each D-71 to D-74 row's TRD column matches the TRDs that cite it. D-74 also lists TRD 18 for the gitignore entry.
- **Endpoints, `table.column` references and env vars:** all agree with TRD 19, 20 and 21. The leftover hits are the same as in round 5, and no new env var was added. `RATE_LIMIT_LOGIN` already existed.
- **Text:** code fences are balanced in all 26 files, and there is no TBD, TODO or lorem outside GIT-053.

| Finding | Severity | What changed (TRDs and requirement IDs) | Status |
|---|---|---|---|
| R6-01 | Major | TRD 04, 05, 12, 13, 16, 18, 21 and 24. New decision D-74: (a) `globalSetup` logs in once per role through `POST /auth/login`. It runs after the D-73 reset and the backend restart, and stores each session in a git-ignored file `frontend/tests/e2e/.auth/<role>.json`. A role fixture puts the token back into `sessionStorage` with `page.addInitScript`, because Playwright `storageState` does not capture `sessionStorage`, which is where SEC-037 keeps the token. Only E2E-01, E2E-02, FE-188, TST-131 and TST-188 perform real logins. (b) `e2e.yml` sets RATE_LIMIT_LOGIN=60/minute in `.env` for both the main and isolated runs. New ENV-054: any value other than 5/minute is allowed only when APP_ENV is local or test, and startup fails otherwise. Updated to match: the TRD 21 variable row and matrix row, API-102, SEC-091 and CIC-030. (c) A new autouse conftest fixture resets the slowapi limiter before each test. TST-131 sets its limits explicitly. The TRD 13 Table 4.10-A note, the §4.10 preamble and §8 were updated, and TRD 18 now gitignores `frontend/tests/e2e/.auth/`. | Fixed |
| R6-02 | Minor | TRD 05, 15, 16, 21 and 24. API-125: one engine factory, `backend/core/db.py`, passes `prepare_threshold=None` in every environment. This covers the Neon pooler and a schema reset under a running backend. The TRD 15 and TRD 21 implementation notes now point to it. After the reset, `globalSetup` runs `docker compose restart backend` and waits for health, so no test-hook endpoint exists. This is recorded in D-73, CIC-030, the e2e.yml comment and TRD 13 §8. | Fixed |
| R6-03 | Minor | TRD 04, 13, 16, 24 and 25. D-73 now holds the only definition of the `@mutating` group: one file, `frontend/tests/e2e/mutating.spec.ts`, run serially in this order: (1) E2E-18, (2) E2E-09 implemented by FE-187, (3) the FE-193 snooze step on R10. FE-187 now uses E2E-09's note and outcome ("Cold, cough or sore throat", "Explained by a known cause"). FE-193 also mutated data: its snooze step moved into the group and now targets R10, and its remaining assertions are read-only. TST-100, the §4.10 preamble, §8, E2E-09, E2E-18, CIC-030, the e2e.yml comment, the TRD 04 E2E row and TRD 25 all reference the group. | Fixed |
| R6-04 | Minor | TRD 13. TST-005 now covers unit and integration tests only (pytest and Vitest). E2E scenarios may depend on the D-73 order, and on the current time only where stated (E2E-15, TST-187, E2E-19). Its verification is the `nightly-validation` job (CIC-037). | Fixed |
| R6-05 | Minor | TRD 04, 05, 09, 13, 23 and 24. The application clock computes `snoozed_until` (in Python, never the database `now()`): DME-022 and its attribute row, API-132 and CUS-039 all say so. TST-065 asserts the stored value, and after time travel asserts `snoozed_until` < now. New FE-205 is a Vitest test with fake timers: `AlertQueue` and the badge move back into the "Not reviewed" group once `snoozed_until` passes, with no API call. E2E-19, TST-065 and D-73 reference FE-205. | Fixed |
| R6-06 | Minor | TRD 20. PGS-016 now verifies in CI job `backend-test`. | Fixed |
| R6-07 | Minor | TRD 13, 14 and 16. New CIC-037 adds a job `nightly-validation` to `e2e.yml`, run on the schedule and on manual dispatch only. It uses the backend-test service and setup, runs `pytest -p randomly` across all suites, and runs `tests/validation/robustness.py` as an informational step (`continue-on-error`). It is not a required check, and failures open the `ci-failure` issue as in CIC-033. The job is in the YAML outline and the §4.3 trigger text. CIC-070 now names `performance`, `lighthouse` and `nightly-validation` as not required. CIC-112 covers all `e2e.yml` jobs, and an artifact row was added. pytest-randomly 3.x was added to requirements-dev and to the TRD 13 tools list. `backend-test` uses `-p no:randomly` so pull-request order stays fixed. TST-151, TST-084 and TDV-083 point to CIC-037. | Fixed |
| R6-08 | Minor | TRD 03 and 24. The D-73 TRD column now reads 03, 04, 05, 13, 15, 16, 25. D-71's sources gained "round 5 R5-01", and its TRDs gained 05. The TRD 24 0.6 row gained R5-03 and R5-04. The TRD 03 0.6 row gained R5-02. | Fixed |

## Round 7 fixes


**Changed TRDs:** 04, 06, 12, 13, 16, 18, 21, 24, 25. Only these now read Version 0.8, each with a "0.8 | 19 Oct 2026 | Phase 1 round-7 fixes (...)" row.

**IDs:** none new. D-73 and D-74 were amended. The next free IDs are unchanged: D-75, FE-206, ENV-055, CIC-038, TST-189.

## Mechanical checks

- **Requirement IDs:** no duplicate or dangling requirement IDs. 2006 IDs are defined and referenced. The only script hits are the known artefacts: AC-DB-02a, the TRD 19 endpoint list and the E2E row names.
- **Decisions:** D-70 to D-74 are all defined. The TRD columns of D-73 and D-74 still match the TRDs that cite them (D-73 also lists 03 and D-74 also lists 18, as decided in round 6).
- **Cross-references:** endpoints, `table.column` references and env vars agree with TRD 19, 20 and 21. The leftover hits are the same as in round 6.
- **Text hygiene:** code fences are balanced in all 26 files. There is no TBD, TODO or lorem outside GIT-053.
- **Leftovers:** no `backend/db.py`, bare `test:e2e` or plain `npx playwright test` remains anywhere.

| Finding | Severity | What changed (TRDs and requirement IDs) | Status |
|---|---|---|---|
| R7-01 | Major | TRD 13, 16 and 24. `playwright.isolated.config.ts` now has its own `globalSetup`, `frontend/tests/e2e/isolated-setup.ts`. It never resets or seeds, because e2e.yml has already seeded `echowell_demo`. It logs in once per role against the `echowell_demo` backend and writes `frontend/tests/e2e/.auth/isolated-<role>.json`. E2E-15, TST-187 and E2E-19 use these files through the same role fixture. Updated: D-74(a) (amended), D-73, TST-004, the TRD 13 §4.10 preamble, the Table 4.10-A note and §8, CIC-030, and the e2e.yml isolated step and comment. The existing `.auth/` gitignore entry in TRD 18 covers the new files. | Fixed |
| R7-02 | Minor | TRD 04, 12, 13, 16, 21, 24 and 25. `frontend/package.json` now defines exactly `test:e2e:readonly` (`--grep-invert "@isolated\|@mutating"`), `test:e2e:mutating` (`--grep @mutating --workers=1`) and `test:e2e:isolated` (the isolated config, Chromium, one worker). There is no bare `test:e2e`. `playwright.config.ts` sets `grepInvert: /@isolated/`. The scripts are in the TRD 04 table, TST-004, D-73 (amended), the e2e.yml loop and isolated step, CIC-030 and TRD 16 §6. TRD 25 Phase 8 and Phase 11 run readonly then mutating in Chromium, and the isolated run stays in CI. Also fixed: pipes inside code spans in table cells were escaped (TRD 04 scripts table, D-73, SEC-020 and the TRD 21 RATE_LIMIT_LOGIN validation cell), so the cells no longer split. | Fixed |
| R7-03 | Minor | TRD 21. ENV-002: exit code 1 is the single code for every settings-validation failure, in the backend, the nightly job and every CLI command. Exit 2 is reserved for command-specific CLI refusals (DEP-070, the §4.8 table, DB-024, DB-057), which are checked before settings validation. ENV-041 and the SEED_* row were changed from exit 2 to exit 1. | Fixed |
| R7-04 | Minor | TRD 06. DB-021 now places the helper at `backend/core/db.py::advisory_key`, matching the TRD 05 module tree and API-125. | Fixed |
| R7-05 | Minor | TRD 13 and 16. TST-006 is now the single marker list: `unit`, `integration`, `contract`, `validation`, `security`, `performance` and `smoke` as level markers, plus `slow`, `authenticated`, `budget` and `req`. They are registered with `--strict-markers`, and the TRD 16 §6 pyproject entry refers to it. TRD 16 §6 is now the single dev-requirements list: ruff 0.6.x+, mypy 1.11+, pytest 8.x, pytest-cov 5.x, pytest-randomly 3.x, time-machine 2.x, httpx, testcontainers-python 4.x, openapi-core 0.19.x, Hypothesis 6.x, openpyxl 3.1.x, import-linter 2.x, Bandit 1.7.x and pip-audit 2.x. The TRD 13 §6 tools line refers to it. | Fixed |
| R7-06 | Minor | TRD 18. The rulesets note now says the required check names are the job IDs listed in TRD 16 CIC-070, from ci.yml and e2e.yml, including `playwright`. | Fixed |

## Round 8 minor fixes


**Changed TRDs:** 04, 05, 07, 08, 11, 12, 13, 15, 16, 17, 18, 24, 25. Only these now read Version 0.9, each with a "0.9 | 19 Oct 2026 | Phase 1 round-8 minor fixes (...)" row.

**IDs:** TST-189 is new. D-73 is amended in its text; its D-xx columns are left as they were, as instructed. Next free IDs: D-75, FE-206, ENV-055, CIC-038, TST-190.

## Verification

**Tables (`r8fix.py`, `r8/tbl.py`).** `r8fix.py` escaped every `|` inside a code span in a table row outside fences: 11 rows in TRD 04, 05, 07, 08 and 17. The remaining row, UX-091, had its pipe in plain text inside a quoted template, so it was escaped by hand. `r8/tbl.py` counts the cells of each table row against its header. After the fixes it reports 0 rows and 0 escaped pipes outside tables or inside fences, and it still reports 0 after all later edits.

**Vitest (`r8/vt3/`).** Set up with Vitest 2.1.9 and @vitest/coverage-v8 2.1.9 on Node 22, with `vitest.config.ts` using `coverage: { enabled: true, provider: "v8", thresholds: { lines: 80 }, exclude: [*.test.*, ...] }`:
- `npm run test` (= `vitest run`) exits 0 and writes the v8 report.
- `npm run test:coverage` (= `vitest run --coverage`) exits 0.
- With a source file at 44 % line coverage, both commands exit 1 with "Coverage for lines (44.44%) does not meet global threshold (80%)".
- `npm run test:coverage -- --coverage` reproduces "Expected a single value for option --coverage". This is why CI calls `test:coverage` with no extra flag.

## Mechanical checks

- **Requirement IDs:** no duplicate or dangling IDs. 2007 IDs are defined and referenced (TST-189 is new). The only script hits are the known artefacts: AC-DB-02a, the TRD 19 endpoint list and the E2E row names.
- **Decisions:** D-01 to D-74 are all defined.
- **Endpoints, columns and env vars:** they agree with TRD 19, 20 and 21; the leftover hits are the same as in round 7.
- **CLI commands:** every `backend.cli` command used is in the TRD 15 §4.8 table, and `resolve-data-alert` now has its syntax.
- **Text:** code fences are balanced in all 26 files. There is no TBD, TODO or lorem outside GIT-053.
- **Old forms:** none of these remain: `tests/components`, `npm run test -- --coverage`, or "prettier in `npm run lint`".

| Finding | Severity | What changed (TRDs and requirement IDs) | Status |
|---|---|---|---|
| R8-01 | Minor | TRD 04, 05, 07, 08, 11 and 17. Escaped `\|` in FE-082, API-065, API-129, the TRD 07 DTO rows `ResidentInfo`, `DeviceAssignment`, `EpochSummary`, `RunWarning` and `DataAlert`, BSC-015, BSC-016, UX-091 and LOG-023. The table checker now reports 0 broken rows across all TRDs. | Fixed |
| R8-02 | Minor | TRD 04, 13 and 16. The `test` script is `vitest run`, and the new `test:coverage` script is `vitest run --coverage`. FE-180 defines the `vitest.config.ts` coverage block: `enabled`, the v8 provider, lcov/html/text reporters, the include and exclude lists (`*.test.tsx` excluded) and `thresholds.lines` 80. `@vitest/coverage-v8` 2.x (same major as vitest) was added to TRD 04 §4.1. The CI `frontend` job (job table, ci.yml step, CIC-017) and FE-202 now use `npm run test:coverage`. TST-142 and the TRD 13 tools line were aligned. Verified in `r8/vt3`. | Fixed |
| R8-03 | Minor | TRD 04, 16 and 18. The `format:check` script (`prettier --check .`) is now its own step in the CI `frontend` job, after typecheck (ci.yml, job table, CIC-017), and the TRD 16 §6 script list now includes `format`, `format:check` and `test:coverage`. GIT-042 now names `npm run format:check`. `eslint-config-prettier` 9.x was added to TRD 04 §4.1 and to FE-200, extended last. | Fixed |
| R8-04 | Minor | TRD 04 and 13. Component tests are co-located as `components/<Name>/<Name>.test.tsx`, and page tests live in `frontend/tests/pages/`. Aligned: the TRD 04 tree (adds `tests/pages/`), the §4.14 table (adds a Page row), TRD 13 §4.2 tree, TST-003 and TST-010. The FE-180 coverage measurement excludes test files. | Fixed |
| R8-05 | Minor | TRD 04, 13 and 24. `playwright.isolated.config.ts` sets `grep: /@isolated/`, `workers: 1` and `fullyParallel: false`. Its single spec file `tests/e2e/isolated.spec.ts` runs E2E-15, TST-187 and E2E-19 in that order. This is written into TST-004, D-73 (amended text), the TRD 04 `test:e2e:isolated` row and the TRD 13 tree. The TRD 04 E2E row now uses the D-74 wording: one API login per role in `globalSetup` per invocation, with `isolated-setup.ts` for the isolated run. The TRD 04 tree now lists `playwright.isolated.config.ts` and the e2e setup files. | Fixed |
| R8-06 | Minor | TRD 12, 13 and 15. The TRD 15 §4.8 row now defines `resolve-data-alert --id <uuid> --reason "<text>"`: admin/operator only, run with DATABASE_URL (`echowell_app`, PGS-021). It resolves only an open `review_flagged_data_problem` alert, and refuses with exit 2 and no change otherwise. It audits `data_alert.resolved`. The TRD 12 vocabulary details for that action are now `{alert_id, kind, reason, operator}`. New TST-189 tests FR-297, including that the pipeline does not resolve the alert (CUS-040), and the exit-2 refusals. | Fixed |
| Observation | — | TRD 25. The Phase 3 outputs now say the pytest configuration is in `pyproject.toml` (`[tool.pytest.ini_options]` with the TST-006 markers) and that there is no `pytest.ini`. | Fixed |
