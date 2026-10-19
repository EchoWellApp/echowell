# TRD Validation Report (Phase 1)

| Field | Value |
|---|---|
| Scope | `specs/TRD/00`–`25`, checked against `specs/prompts/TRD_Generation_Prompt.md`, `specs/architecture/Deployment_Architecture.md`, `specs/UI-wireframe/*.dc.html`, `specs/business-requirements/*`, `specs/data-samples/*`, `specs/algorithm/generate_pipeline_test_v0_1.py` |
| Checklist | `specs/prompts/TRD_Implementation_Audit_Checklist.md`, Phase 1 (and TRD 25 §Phase 1 definition of done) |
| Branch | `trd-generation` (read only; no file under `specs/` was changed) |
| Date | 2026-10-19 |

How locations are written: `TRD NN:line` means line `line` of `specs/TRD/NN_*.md`. For example, `TRD 20:780` is `specs/TRD/20_PostgreSQL_Schema_Definition.md` line 780.

Severity scale used in this report:

| Severity | Meaning |
|---|---|
| Critical | Built as written, the system would be wrong or unsafe: a core path fails at runtime, or two binding rules cannot both hold. |
| Major | An ambiguity or conflict that an implementer would probably resolve the wrong way, or a mandated check or requirement with nothing behind it. |
| Minor | Wording, a numbering slip or an inconsistency that a careful implementer would resolve correctly. |

---

## 1. Summary

**Verdict: FAIL.** The TRD set has three Critical findings, and the build would break on core paths if implemented as written:

1. The audit-log CHECK constraint rejects almost every audit action the TRDs name. Audit writes share a transaction with the audited action, so login, ingest and pipeline runs would fail.
2. The late-arrival rule writes `processed_sessions` rows that the schema's CHECK constraints reject.
3. The config-change workflow needs to delete frozen baselines. The database grants forbid that, and several other TRDs forbid it outright.

Everything else is in good shape:

- Coverage is complete.
- No requirement ID dangles.
- The expected numbers match the SRC-03 workbook exactly.

The remaining problems are cross-TRD contracts that disagree: field names, lock keys, environment variable shapes, CSP, and CI gates.

| Severity | Count |
|---|---|
| Critical | 3 |
| Major | 23 |
| Minor | 29 |
| **Total** | **55** |

| # | Phase 1 check | Result | Key evidence |
|---|---|---|---|
| 1 | Database requirements support all APIs | **FAIL** | F-01 (audit CHECK), F-02 (late-arrival CHECKs), F-03 (baseline delete not granted), F-09 (silent-day definitions), F-10 (`in_use_until` and restart cause have no source column) |
| 2 | APIs support all frontend requirements | **FAIL** | F-11 (FE interfaces do not match TRD 19 schemas), F-12 (no endpoint for review explanations, snooze hours, restart cause, `in_use_until`, split set-aside/quarantine, "Facility range not available yet") |
| 3 | Analytics requirements support all business requirements | **FAIL** | Coverage of BR-03..BR-11 and BR-15 is complete, and all workbook figures were re-verified (section 6.3). However, F-02 and F-03 make two analytics behaviours (late arrivals; parameter change, NFR-084) unbuildable as specified, and F-26 leaves data-alert configuration out of `PipelineConfig`. |
| 4 | Testing requirements validate all critical functionality | **FAIL** | Every BR has at least one test or MVP criterion (section 2.1). However: F-19 (E2E and a11y are "required" in TRD 13 but not required checks in TRD 16); F-20 (gitleaks, Bandit, LLM-dependency scan, forbidden-term scan, Lighthouse and import-linter have no workflow); F-24 (exact-string tests contradict the UX strings). |
| 5 | Deployment requirements support the architecture | **FAIL** | F-13 (API base URL double `/api/v1`), F-14 (CSP and Railway hostnames), F-15 (seed files absent from the image), F-16 (migrator credential on the web service), F-17 (staging `PIPELINE_AS_OF` hides demo check-ins), F-23 (backup targets beyond the Neon Free plan), F-04 (session advisory lock over the pooler) |

TRD 25 §Phase 1 definition of done:

| Criterion | Result | Evidence |
|---|---|---|
| Every BR-01..BR-18 maps to at least one TRD requirement | **Met** | Section 2.1. Every BR is cited by at least 20 requirement rows across at least 8 TRDs, and the TRD 02 §4.28 BR→FR table covers all 18 (TRD 02:573–590). |
| Every OQ/ASM/RSK/DSC/D ID used in the TRDs exists in TRD 24 | **Met** (see F-28) | Used: ASM-01..08, RSK-01..14, DSC-01..14, OQ-01..OQ-26, D-01..D-55; all are defined in TRD 24. `D-56` and `OQ-27` occur only in TRD 24:245 as "next free number" text, not as references. |
| Each of the five checks has a pass/fail line with evidence | **Met** | Table above and section 6. |

Mechanical checks (scripted, not sampled):

- **Requirement IDs.** I parsed every table row `| PREFIX-NNN |` as a definition and every other occurrence as a reference: 1,989 IDs are defined, with no duplicates and no dangling references (no ID used but never defined, and no ID cited against the wrong TRD).
- **Endpoints.** All 31 endpoints in TRD 19 E-01..E-31 were compared with every `/api/v1/...` path in the 26 TRDs. The only paths that are not in TRD 19 are `/alerts/{id}/acknowledge` (TRD 09:130, 13:295, 24:197, 25:209) and `/audio` (TRD 15:419). Every one of these occurrences says the endpoint must *not* exist, which is correct.
- **Environment variables.** Every backticked environment-variable-shaped name outside TRD 21 is defined in the TRD 21 tables. The only exceptions are error codes, which matched the same pattern and are not environment variables.
- **Placeholders.** Grepping for `TBD`/`TODO`/`lorem` finds only GIT-053 (TRD 18:219), which is the rule that bans them.

---

## 2. Requirements Traceability Matrix

### 2.1 Business requirements → TRD requirements → tests

Column notes:

- **Req. rows citing it, by TRD.** The number of requirement rows (any prefix) whose Trace column cites the BR, given as TRD:count.
- **Key requirement IDs.** Taken from the TRD 02 §4.28 table (TRD 02:573–590) plus the main non-FR rows.
- **Tests / acceptance.** IDs from TRD 13 and TRD 14. "MVP-xx" is TRD 13 Table 4.17-A (TRD 13:482–496), which is the release acceptance gate.

| BR | Req. rows citing it, by TRD | Key requirement IDs | Tests / acceptance (TRD 13/14) | Gap |
|---|---|---|---|---|
| BR-01 Ingest features, no audio | 81: 00:5 01:8 02:26 03:4 04:2 05:2 06:2 10:4 11:4 12:4 13:8 … | FR-001–005, FR-020–028; ING-0xx; API-03x; SEC no-audio | TST-030, TST-043, TST-045, TST-046, TST-133, TST-170, TST-180; TDV-031, TDV-090; MVP-02 | — |
| BR-02 Keep raw unaltered, derive rest | 101: 01:11 02:8 03:12 05:8 06:16 07:6 10:10 15:6 20:5 … | FR-005–010, FR-223; DB-006, DB-009; ARC rebuild rows | TST-037, TST-041, TST-043; TDV-002, TDV-050, TDV-054; MVP-02, MVP-12 | Rebuild path conflicts with frozen baselines (F-03) |
| BR-03 Duplicates, first arrival wins | 39: 02:8 05:3 06:2 10:7 11:5 13:5 … | FR-008, FR-029–031; API-043; ING-038; DB-021 | TST-020, TST-044, TST-046; TDV-054; MVP-01, MVP-03 | Lock keys differ between TRDs (F-04) |
| BR-04 Set aside with all reasons | 22: 02:10 08:1 10:3 11:2 … | FR-040–044, FR-290 | TDV-053; VC-R03; MVP-01, MVP-03 | — |
| BR-05 Quarantine wrong speaker | 22: 02:11 08:5 … | FR-060–065; BSC speaker screen | TDV-055; VC-R05; MVP-01, MVP-03 | — |
| BR-06 Honest missing days | 66: 02:17 03:8 10:7 11:7 … | FR-120–125, FR-291; ING-048; DB-023, DB-044 | TDV-052, TDV-053, TDV-064, TDV-068; VC-R02; MVP-03 | Ledger end date (F-21); silent-day definition (F-09) |
| BR-07 Morning offset, local time | 21: 02:6 08:3 … | FR-070–074; BSC offset rows | TDV-056; VC-R06; MVP-01 | — |
| BR-08 Device/firmware epochs | 28: 02:8 08:3 11:5 … | FR-050–053; ANL epoch rows | TDV-057; VC-R07; MVP-01 | Restart cause not exposed by the API (F-12) |
| BR-09 Robust frozen baseline | 52: 02:14 08:5 11:7 … | FR-080–086; BSC-030; DB-016 | TST-184; TDV-051, TDV-058, TDV-060; VC-R10; MVP-01 | F-03 |
| BR-10 Signed z and composite | 20: 02:10 08:4 … | FR-090–095 | TDV-051; MVP-01 | — |
| BR-11 CUSUM, persistent deviation only | 63: 00:7 02:25 09:4 24:4 … | FR-100–110; CUS-0xx | TST-020; TDV-059, TDV-060, TDV-067; VC-R09, VC-R10; MVP-01, MVP-13 | Closure paths conflict (F-06, F-07) |
| BR-12 Residents overview | 92: 02:27 03:19 04:5 05:5 11:7 … | FR-130–140, FR-150–156; UX-020–058 | TST-033, TST-090, TST-110, TST-181; TDV-062, TDV-066; E2E-03, E2E-04; MVP-04 | F-09, F-11 |
| BR-13 Resident detail | 111: 02:41 03:12 04:14 05:7 11:15 … | FR-160–195, FR-260–274; UX-060–150, UX-300–322 | TST-090, TST-093, TST-110, TST-181; TDV-066; E2E-08..E2E-10, E2E-17, E2E-18; MVP-05, MVP-13 | F-11, F-12, F-24 |
| BR-14 New-admission arm (Should) | 33: 02:8 04:4 11:6 24:3 … | FR-200–207; UX-181–195 | TST-090; E2E-13; MVP-06 | **Weak:** only the empty state is tested (no fixture with a populated facility range). The "Facility range not available yet" status has no API enum value (F-12). The FR-205 transition (DB-025, Should) has no test. |
| BR-15 Reproduce workbook exactly | 165: 01:16 02:22 03:19 13:15 14:25 … | FR-222–225, FR-240–244; TST-070–083; TDV-0xx | TST-048, TST-070, TST-071, TST-074, TST-081, TST-083, TST-140; MVP-01, MVP-14 | — (all figures re-verified, section 6.3) |
| BR-16 Protect research data | 267: 02:34 04:30 12:21 15:22 16:16 17:13 … | FR-210–221; SEC-0xx; LOG audit rows | TST-007, TST-032, TST-041, TST-053, TST-130–137; TDV-006, TDV-007; MVP-07 | Audit CHECK (F-01); CSP (F-14); gitleaks and Bandit have no workflow (F-20) |
| BR-17 Monorepo; Netlify/Railway/Neon; GH Actions | 76: 01:21 03:22 15:7 … (TRD 02 maps only FR-253, FR-254) | ARC-0xx, DEP-0xx, CIC-0xx | TST-001, TST-150, TST-152; MVP-08 | Thin in TRD 02, but well covered by TRD 01/15/16. Deployment conflicts F-13–F-17. |
| BR-18 No diagnosis, no LLMs, no ML | 48: 00:7 11:8 24:4 25:3 … | FR-164, FR-277, FR-278, FR-298; VIS-003..005, VIS-029 | TST-096, TST-097, TST-170; MVP-09 | LLM-dependency and forbidden-term CI checks have no workflow (F-20) |

Result:

- All 18 BRs map to requirements and to at least one test or MVP criterion.
- No BR is unmapped.
- One BR (BR-14) is only weakly verified.

### 2.2 Frontend requirements (TRD_Generation_Prompt) → UX / FE IDs

TRD 11 §4.16 (TRD 11:586–633) closes with a "Prompt (SRC-12) coverage" paragraph that maps every frontend item in the prompt. I checked each one:

| Prompt frontend item | UX IDs | FE IDs / components | Test |
|---|---|---|---|
| Residents overview | UX-020–UX-048 | FE ResidentsOverviewPage, StatusTiles, ResidentsTable | E2E-03, E2E-04 |
| Sort controls | UX-030–UX-033, UX-261 | FE sort select | E2E-05, E2E-06 |
| Statuses Alarm On / No Alarm / Baseline Still Forming | §4.3.4, UX-036 | StatusBadge | E2E-04 |
| 30-day counts and missing days | UX-039, UX-047, UX-048 | ResidentsTable | E2E-04 |
| Device health / device cards | UX-050–UX-058, UX-263 | DeviceCard | E2E-07 (field names, F-09/F-11) |
| Resident detail header and baseline info | UX-060–UX-066 | ResidentHeader | E2E-08 |
| "What this means" text | UX-070–UX-075, UX-160–UX-164 | WhatThisMeans | TST-096 |
| CUSUM tally chart with alarm line | UX-080–UX-092 | CusumChart | TST-093, E2E-08 (string conflict F-24) |
| 7 measurements | UX-100–UX-108 | FeatureCards | E2E-08 |
| Staff review / notes | UX-120–UX-135 | StaffReview | E2E-09 (AC-UX-06 conflict F-24) |
| Check-in log with reasons | UX-140–UX-150 | CheckinLog | E2E-10, E2E-11, E2E-12 (restart-cause fields missing, F-12) |
| New admissions (experimental) | UX-181–UX-195 | AdmissionsPage, ComparisonChart | E2E-13 |
| Alert review queue | UX-300–UX-322 | AlertsPage, AlertReviewForm | E2E-17, E2E-18, E2E-19, E2E-21 (F-12, F-25) |
| Data alerts | UX-306–UX-309, UX-331 | DataAlertCard | E2E-17 |
| Analytics KPIs, funnel, by-resident, alarm timing | UX-351–UX-384 | AnalyticsPage (missing from FE inventory, F-30) | E2E-20, E2E-21 |
| Login / auth | UX auth rows, FE-03x | LoginPage | E2E-01, E2E-02, E2E-14 |
| Loading, empty and error states | UX state rows, FE-145 | shared states | TST-090 |
| Accessibility | UX/NFR-060 | FE-190 | TST-110 (route-list conflict F-19) |
| Responsive layout | UX layout rows | — | E2E-16 (phone width) |
| Plain-language wording, no diagnosis | VIS-003..005, UX copy | — | TST-097 |

Result: every prompt item maps to UX and FE IDs and to a test. There are no unmapped items.

### 2.3 Wireframes → UX sections

| Wireframe | UX section | Coverage |
|---|---|---|
| `specs/UI-wireframe/Main.dc.html` (SRC-09) | TRD 11 §4.3, §4.4, §4.13 | Complete: header, tiles 2/7/1/19, sort, table rows R09…R06, badges, device cards, footer |
| `Resident.dc.html` (SRC-10) | TRD 11 §4.5 | Complete (chart range string conflict F-24) |
| `Admission.dc.html` (SRC-11) | TRD 11 §4.7 | Complete |
| `Alerts.dc.html` (SRC-18) | TRD 11 §4.17 | Complete (queue order F-25; review strings F-08) |
| `Analytics.dc.html` (SRC-19) | TRD 11 §4.18 | Complete; KPI 94% / 89% / 9 of 10 / 2, funnel 300/281/269/267 and by-resident 43/73/80/93% were re-verified against the workbook |

### 2.4 Items with no test or only weak verification

| Item | Status |
|---|---|
| FR-205 / DB-025 new-admission → own-baseline transition (Should) | No test |
| Facility comparison with populated data (BR-14) | Only the empty state is tested (E2E-13) |
| NFR-069 | Demo only |
| CI-only mandates in TRD 12 (SEC-052, SEC-128, SEC-153), TRD 00 (VIS-008), TRD 13 (TST-125) and TRD 01 (ARC-041) | Stated as tested in CI, but no workflow runs them (F-20) |

---

## 3. Missing Requirements

| ID | Sev. | Location | Description | Evidence | Recommendation |
|---|---|---|---|---|---|
| F-10 | Major | TRD 20 (devices/device_assignments DDL); TRD 19 `Device`, `CheckinEvent` | The FE and UX require some data that has no source column or API field: the device "in use until" date, and the restart cause of an epoch with its previous device and firmware values. | UX-057 (TRD 11:212) requires "Oct 1–12 · replaced by D07B". UX-142 (TRD 11:352) requires "Baseline restarted · new device D07B (was D07)" and "firmware changed (<from> to <to>)". TRD 19 `Device` has no `in_use_until`, and `CheckinEvent` has only `detail`, `epoch_number`, `session_id`, `cusum_tally`. The E-10 example detail is just "new epoch 2 on device D07B". `epochs` stores the boundary but no cause. | TRD 06/20: store `start_cause` (device, firmware, software) and the previous values on `epochs`. TRD 05/19: add `in_use_until`, `restart_cause`, `previous_device_code`, `from_value` and `to_value`. |
| F-12 | Major | TRD 05, TRD 19 | No endpoint gives the frontend these four things. | (a) The `review_explanations` codes and labels and `alert_snooze_hours`: needed by FE AlertReviewForm `explanations {code,label}[]` and the "Remind me in <h> h" button (FE-136, TRD 04:519), and by UX-313, UX-320 and UX §4.17.4. ENV-020 (TRD 21:112) says these are config keys, never env vars, but no endpoint exposes them. (b) `ByResidentRow` merges `set_aside_or_quarantined_days`, but UX-368 (TRD 11:756) and UX-370 stack set-aside and quarantine separately. (c) `ComparisonStatus` (TRD 19:1147) = `[outside_range, within_range, not_enough_checkins]` has no "Facility range not available yet" value, which FR-202 (TRD 02:257), AC-FR-10 and the TRD 00:239 MVP definition require. (d) The F-10 fields. | TRD 05/19: add a `GET /api/v1/config/ui` (or extend `/auth/me`) carrying `review_explanations` and `alert_snooze_hours`; split the by-resident counts; add `range_not_available` to `ComparisonStatus`. |
| F-26 | Major | TRD 07:270 (`PipelineConfig` field table, "names are binding") | `PipelineConfig` has no fields for the data-alert and review keys, yet stage 11 `generate_data_alerts(..., config, ...)` reads them. | Missing: `data_alert_set_aside_fraction`, `data_alert_device_silent_days`, `data_alert_baseline_stalled_enabled`, `alert_snooze_hours`, `review_explanations`. TRD 21 ENV-020 names these keys, and CUS-046 (TRD 09:288) says thresholds come from `config_parameters`. | TRD 07: add the fields, or define a separate `DataAlertConfig` and say how it is loaded and hashed. |
| F-20 | Major | TRD 16 §CIC-002 (TRD 16:95) | Six CI checks are mandated, but no workflow or job runs them. CIC-002 also says "no other workflows". | gitleaks (SEC-052 Must, TRD 12:192; TST-136); Bandit (SEC-153, TRD 12:341); LLM-dependency scan (SEC-128, TRD 12:331; NFR-115; VIS-004 says "dependency scan in CI, TRD 16"); forbidden-term/"Edge4Care" scan (VIS-008, TRD 00:256; NFR-067); Lighthouse (TST-125, TRD 13:401); import-linter (ARC-041, TRD 01:245; AC-ARC-01). A grep of TRD 16 finds none of `gitleaks`, `bandit`, `Edge4Care`, `openai`, `import-linter`. | TRD 16: add these jobs to `ci.yml` and to the CIC-070 required checks. |
| F-46 | Minor | TRD 04:605 (FE-170) | The frontend env var list is incomplete. | FE-170 says the frontend reads only two variables, but TRD 21 adds `NEXT_PUBLIC_GIT_SHA` and `frontend/lib/config.ts` (ENV-030, TRD 21:135). | Align TRD 04 with TRD 21. |
| F-30 | Minor | TRD 04 §4.2 layout; FE-032; AppHeader | The `/alerts` and `/analytics` pages are not wired into the FE structure. | They are missing from the app layout tree, from the FE-032 page titles and from the AppHeader `active` prop union, and `AnalyticsPage` is not in the component inventory. TRD 11 §4.17/§4.18 and TRD 19 E-xx do define them. | Add them in TRD 04. |

---

## 4. Contradictions

Each row quotes both sides of the conflict.

### 4.1 Critical

**F-01 · Critical · Audit action CHECK rejects the audited actions**

- Side A, TRD 20:780: `CONSTRAINT audit_logs_action_ck CHECK (action ~ '^[a-z_]+\.[a-z_]+$')`. This allows exactly one dot.
- Side B, TRD 12:272–287: the audit table uses `auth.login.succeeded`, `auth.login.failed`, `ingest.batch.received`, `pipeline.run.started` and `pipeline.run.finished`. These have two dots and fail the CHECK.
- Other names fail because they have no dot:
  - ANL-040 (TRD 07:333): `pipeline_run`
  - CUS-016, CUS-018, CUS-039 (TRD 09): `alert_reviewed`, `alert_closed`, `alert_snoozed`
  - ING-058 (TRD 10:255): `ingest_batch`
  - DEP-071 (TRD 15:389): `seed_reset`
- Four vocabularies are in use:
  - TRD 12 §audit table.
  - TRD 05 API-022/063/081/132.
  - TRD 23:483: `auth.login`, `auth.login_failed`, `ingest.batch`, `pipeline.run`, …
  - TRD 06 DB-025, DB-060, DB-062, DB-064: `resident.cohort_changed`, `roster.loaded`, …, which are not in TRD 12's table.
- Impact: LOG-090 (TRD 17:250) and SEC-101 (TRD 12:292) write the audit row in the same transaction and fail the action when it fails. Login, every ingest batch and every pipeline run would therefore return 500.
- Recommendation: make TRD 12 §audit table the single vocabulary, with one fixed pattern such as `^[a-z_]+(\.[a-z_]+){1,2}$`. Then update TRD 20:780, TRD 23:483 and the action names in TRD 05, 06, 07, 09, 10 and 15 to match it.

**F-02 · Critical · Late-arrival path violates `processed_sessions` CHECKs**

- Side A, TRD 20:520–530:
  - `usable` rows must have zero reasons.
  - `(status = 'usable') = (baseline_ordinal IS NOT NULL)`, at line 529.
  - `processed_sessions_epoch_ck`: epoch NULL ⇔ status `duplicate`.
- Side B, BSC-040 (TRD 08:227): a passing late record is "`usable` or `quarantined`, with `in_baseline = false`, **no `baseline_ordinal`**, no score, and reason text suffix 'late arrival (not used for baseline or scores)'".
  - TRD 07 `EpochedRecord` sets `epoch_number = None` for a late arrival before the first epoch.
- Impact: when any late record arrives, the insert fails and that resident's run fails (and with F-05's one-transaction model, the whole run fails). ASM-07 and OQ-10 make late arrivals an expected case.
- Recommendation: TRD 20 should relax the CHECKs: allow `usable` with a NULL ordinal when `in_baseline = false` and after the freeze, allow a "late" reason on usable rows, and allow a NULL epoch for late rows. Alternatively, add a `late_arrival` status in TRD 08, 20 and 23. Then align BSC-040 with the chosen option.

**F-03 · Critical · Parameter change requires a baseline delete that grants and other TRDs forbid**

- Side A, ANL-032 (TRD 07:299): a parameter change takes effect only through an admin manual run with scope `all`, "the only run allowed to delete and recompute frozen baselines". Ingest and nightly runs "shall end with status `failed` and warning code `config_changed_requires_rebuild`".
- Side B:
  - DB-009 (TRD 06:417): `echowell_app` holds only `SELECT, INSERT` on `baselines`, so the app cannot delete baselines.
  - ARC-043, FR-083, BSC-030 and DB-016: frozen baselines are never recomputed.
  - NFR-084 (TRD 03:136): parameters are changeable without a redeploy and take effect on the next run.
  - CUS-046 (TRD 09:288): data-alert thresholds need no rebuild, yet they are `config_parameters` rows, so changing one changes the config hash and triggers ANL-032.
  - RAQ-012 (TRD 24).
- Impact:
  - In production, any `config_parameters` edit, including a data-alert threshold, stops all ingest-triggered and nightly runs.
  - The only recovery path cannot run under the TRD 06 grants.
- Recommendation: decide in TRD 24 (new D-xx) which keys are "algorithm" keys (hash-relevant, rebuild only) and which are "operational" keys (data-alert, snooze, explanations; take effect next run). Give the rebuild a defined privileged path (for example, a migrator-role CLI). Then align TRD 03, 06, 07, 09 and 20.

### 4.2 Major

| ID | Location (A vs B) | Side A (quoted) | Side B (quoted) | Impact | Recommendation |
|---|---|---|---|---|---|
| F-04 | API-043 TRD 05:187; ING-038 TRD 10:154; DB-021 TRD 06:461; API-064 TRD 05:220; ANL-034 TRD 07:327; TRD 06:652; TRD 20:1160 | API-043 `pg_advisory_xact_lock(hashtext(session_id))`; ING-038 `hashtext('session:' \|\| session_id)` | DB-021 `hashtextextended('echowell:session:' \|\| session_id, 0)` and `'echowell:resident:'`; API-064 `hashtext('echowell:pipeline:resident:'\|\|code)` and session-level `pg_advisory_lock(hashtext('echowell:pipeline:all'))`; ANL-034 `hashtext('pipeline:'\|\|code)` | Different keys mean the locks never conflict, so the concurrent-duplicate and run serialisation guarantees fail. The session-level lock in API-064 runs over the Neon pooler (DEP-032, TRD 15:236), which TRD 06:652 and TRD 20:1160 say does not work there. | TRD 06 DB-021 is the single source: one key function; xact locks only, or the full-run lock on the direct host. Make TRD 05, 07 and 10 reference DB-021 instead of restating it. |
| F-05 | TRD 07:304; ANL-041 TRD 07:334; LOG-061 TRD 17:212 vs DB-013 TRD 06:452; ARC-064 TRD 01:316 | "inside one database transaction per run"; ANL-041 rolls back all derived writes on any exception | DB-013: each resident's results "in exactly one database transaction" and the run continues with the next resident | Implementers will choose differently; partial-success semantics and `pipeline_runs.status` differ. | Choose one (per-resident is more robust) in TRD 01 and propagate to 06, 07 and 17. |
| F-06 | FR-110 TRD 02:170; D-03 TRD 24:165 vs CUS-019 TRD 09:133; AGT-058 TRD 25:317 | FR-110: alert moves to `closed` only through epoch end or an admin CLI | CUS-019: `closed_reason='admin'` is reserved and v0.1 has no manual closure; TRD 15 §4.8 has no close command (only `resolve-data-alert`); AGT-058 "an admin closes it" | Closure behaviour is ambiguous. | Pick one (recommended: no manual close in v0.1) and fix FR-110, D-03 and AGT-058. |
| F-07 | DB-018 TRD 06:457; ANL-039; CUS-015 TRD 09:129 vs FR-110 TRD 02:170 | A third closure path, "superseded by rebuild" | FR-110 allows only two paths | The `closed_reason` enum and the UI differ. | Add the superseded path to FR-110 and D-03. |
| F-08 | API-130 TRD 05:249; CUS-040 TRD 09:255; UX §4.17.2 TRD 11:657; TRD 23:629 | API-130: title "<R> · flagged by alarm review", detail "Alarm since <Mon D> · reviewer reported a data problem"; "create" | CUS-040: "<R> · review flagged a data problem" / "From alarm review on <Mon D>", "create (or, if one is open, link)"; UX: detail "Reviewed <Mon D> by <display name>"; TRD 23: "<R> · flagged as data problem in review" | Exact-string tests cannot all pass. Create vs create-or-link changes the data (FR-273, D-35). | Make UX §4.17.2 the single string source and FR-273 the behaviour source, and remove the other copies. |
| F-09 | FR §4.1; DB-044 TRD 06:544; TRD 23 §4.4.2; API-086 TRD 05:257; TRD 19:494–502, 1689–1690; TRD 04:368–369; TRD 11:810 | FR glossary: a silent day applies to a shared device only. DB-044: any device ("D08 silent on R08's 12 missing days"). TRD 19: `silent_days_last_30` = zero arrivals, `device_gap_days_last_30` = `missing_device_gap` days | FE TRD 04:368: `silent_days_30d` = `missing_device_gap` days, `no_activity_days_30d` = no record; the TRD 19 E-17 example says `"total": 12` but the fixture has 10 devices | The device health card shows the wrong days, with the field meanings swapped. | Define a silent day once (TRD 02), then use the TRD 19 names in TRD 04 and TRD 11, and fix the example total. |
| F-11 | TRD 04 §4.6.3 (TRD 04:333–374) and its note at TRD 04:700 vs TRD 19 components; TRD 23 §4.6 vs TRD 19:1992 | FE: `alarm_since_date`, `baseline_progress {n, N}`, `current_epoch_number`, `counts_30d`, `missed_30d`, CheckinEventType `alarm`, `reason_text`, `restart_cause`, `residents`, `replaced_device_code`, `in_use_until`, `reviewer_display_name`, `baseline_period`. TRD 04:700: "TRD 05/19 must define them" | TRD 19: `alarm_since`, `{n_usable, n_required}`, `current_epoch`, `last_30_days`, `missed_last_30_days`, `alarm_on`, `detail`, `resident_codes`, `replaces_device_code`, no `in_use_until`, `reviewer {id, display_name}`, `baseline_periods`. TRD 23 Pydantic names (`TokenResponse`, `UserOut`, `AlertOut`, `DataAlertOut`, `SessionIngestResponse`, …) differ from TRD 19 schema names, while TRD 19:1992 says classes must match schema names | The FE client will not type-check against the API. The OAS-005 contract test fails if TRD 23 names are used. | TRD 19 is the contract. Rewrite TRD 04 §4.6.3 as generated or aliased types from TRD 19, and rename the TRD 23 §4.6 classes. |
| F-13 | FE-070 TRD 04:271; TRD 04:600 vs TRD 21:122, 172, 204; TRD 15:193; TRD 16:237 | FE-070: build `${NEXT_PUBLIC_API_BASE_URL}/api/v1<path>`; FE env table value `http://localhost:8000` | TRD 21: "Backend base URL including `/api/v1`", which must end in `/api/v1`; compose and CI set `http://localhost:8000/api/v1` | Every request goes to `/api/v1/api/v1/...` and returns 404 in every environment. | Choose one (an origin only is simpler for CSP) and fix TRD 21, 15 and 16, or FE-070. |
| F-14 | TRD 12:225 (netlify.toml, "binding"); SEC-075 TRD 12:241 vs FE-060 TRD 04:255; TRD 15:339 | TRD 12: CSP with `script-src 'self' 'unsafe-inline'`; nonce later (SEC-075); connect-src `echowell-api(-staging).up.railway.app` | FE-060: middleware nonce CSP with `'strict-dynamic'` now. TRD 15 netlify.toml: no CSP or Permissions-Policy, HSTS without includeSubDomains, build command without `check-csp.mjs` (SEC-070, TRD 12:236). TRD 15, 16 and 21 use host `echowell-backend-production/-staging.up.railway.app` | With TRD 12's hostnames the browser blocks every API call. There are three different header sets. | One CSP owner (TRD 12), with the hostname taken from `NEXT_PUBLIC_API_BASE_URL`. Make TRD 15's netlify.toml a copy of TRD 12's. |
| F-15 | TRD 15:140 (local step 6); TRD 16:331 (e2e seed) vs DEP-020/021 TRD 15:214–215 | `docker compose exec backend python -m backend.cli seed test_v0_1` and `python database/seeds/load_evaluation_ground_truth.py tests/fixtures/...` | The image contains only `backend/`, `analytics/` and `alembic.ini`, and excludes `tests/`; compose bind-mounts only backend and analytics | Seeding and ground-truth load fail with file-not-found locally and in E2E CI. | Mount `database/` and `tests/fixtures/` in compose, or ship seed data inside the backend package (TRD 15). |
| F-16 | TRD 06:657 vs DEP-040 TRD 15:295; DEP-022; SEC-111 TRD 12:312; ARC-015 TRD 01:106 | "the backend shall never receive the migrator credential" | DEP-040: Railway start command `alembic upgrade head && uvicorn ...`, which needs `DATABASE_MIGRATION_URL` on the web service; ARC-015 omits `DATABASE_READONLY_URL` | Least privilege is broken in production, or migrations cannot run. | Run migrations as a Railway pre-deploy or release command or a CI job with its own secret (TRD 15/16), and keep TRD 06's rule. |
| F-17 | TRD 21:84, 96 (ENV-017), 163; ANL-015 TRD 07:249 vs AC-VIS-03 TRD 00:391; SC-03; DEP environment matrix | Staging `PIPELINE_AS_OF=2026-10-30T15:00:00-05:00`; ANL-015 excludes records after as_of | "A record posted to `POST /api/v1/sessions` in staging appears in the check-in log"; staging hosts "demo check-ins of synthetic demo resident" | A demo record posted today (after 2026-10-30, or with a real timestamp) is never processed in staging, so demo step 5 fails. | Scope the fixed as_of to the `test_v0_1` profile only, or give the demo resident its own profile or environment (TRD 21/15). |
| F-18 | TRD 05:291 ("complete; no other codes may be emitted"); API-097 TRD 05:336 vs TRD 17:154–163; LOG-044 TRD 17:184; LOG-052 TRD 17:194; LOG-043 TRD 17:183 vs ING-023 TRD 10:124 | TRD 05 catalogue: `NOT_AUTHENTICATED`, `SERVICE_UNAVAILABLE`, …; API-097 OperationalError → `SERVICE_UNAVAILABLE`, Retry-After 30 | TRD 17 uses `AUTHENTICATION_REQUIRED`, `CONFLICT`, `DATABASE_UNAVAILABLE`, `PIPELINE_STAGE_FAILED`, `PIPELINE_CONFIG_INVALID`; LOG-052 Retry-After 60; LOG-043 `errors[].code` = "UPPER_SNAKE of the pydantic error type" vs ING-023 lowercase field codes `missing_field`, … | Clients and tests see different codes for the same condition. | TRD 05 is the catalogue. Make TRD 17 reference it, and fix Retry-After and the field-code style. |
| F-19 | TST-150 TRD 13:452; TST-110 TRD 13:385; TST-100 vs CIC-031 TRD 16:352; CIC-070 TRD 16:411; FE-190 TRD 04:633; SC-07 TRD 00:290; AC-NFR-04 TRD 03:235; NFR-060 TRD 03:116 | TST-150: on every PR, E2E (Chromium), accessibility and PR-scope performance are required | CIC-031: `e2e.yml` "not a required check"; CIC-070 lists 7 required checks without E2E or a11y. FE-190's a11y routes omit `/alerts` and `/analytics` (TST-110 includes them). SC-07 "4 pages", AC-NFR-04 "five main pages", NFR-060 lists 7 | Critical UI regressions and a11y failures can merge. | Align TRD 16 CIC-070 with TRD 13 TST-150, and give one route list (TST-110) referenced by FE-190, SC-07 and AC-NFR-04. |
| F-21 | ING-048 TRD 10:228 and pseudocode TRD 10:212 vs FR-120 TRD 02:176; DB-023 TRD 06:463; AC-DB-10 | Ledger stops "the day before `withdrawn_on`" | FR-120 runs "to `withdrawn_on`"; DB-023 and AC-DB-10 include rows through `withdrawn_on` (R08 through 2026-10-20) | Off-by-one in the missing-day counts and tests for withdrawn residents. | Choose inclusive or exclusive in TRD 02 and fix the others. |
| F-22 | ING-016 / TRD 20 seed vs ING-017 TRD 10:78–79 | Seeded `feature_name_map` is an identity map of 11 record fields plus 19 features | ING-017: "each target shall be one of the 19 feature keys", otherwise startup fails | The seeded map fails its own validation, so the backend cannot start. | Let ING-017 allow record-field targets, or remove the 11 field mappings from the seed. |
| F-23 | DB-050 TRD 06:578; DB-051 TRD 06:579 vs NFR-024/025 TRD 03:72–73; SEC-162 TRD 12:352; DEP-097 TRD 15:445; TRD 22:110 | DB-050: PITR ≥ 7 days, RPO ≤ 15 min, RTO ≤ 4 h; DB-051 monthly drill | NFR-024/025: RPO ≤ 24 h, RTO ≤ 8 working hours, drill once before go-live; SEC-162 drill every 6 months; DEP-097 monthly. TRD 22: Neon Free restore window "hours, not days" | The interim plan cannot meet ≥ 7 days PITR, and the targets differ. | Set one target in TRD 03 and state the Neon plan needed in TRD 22, or explicitly waive this for interim synthetic data (D-OWNER-2). |
| F-24 | TST-093 TRD 13:339; E2E-08 TRD 13:366; TDV §4.9 TRD 14:536; AC-FR-09 TRD 02:620 vs UX-082 TRD 11:272; UX §4.13.3; FE `formatLocalDateRange`. AC-UX-06 TRD 11:829 vs UX-123/UX-130; R5 | Tests expect "Baseline Oct 1–Oct 16" | UX and FE format same-month ranges as "Baseline Oct 1–16". AC-UX-06 expects "Note saved and marked as reviewed.", contradicting UX-123/130 (a note does not mark reviewed; R5) | Tests fail against a correct UI, or the UI is built to the wrong spec. | Fix the test strings (TRD 02, 13, 14) to the UX format, and fix AC-UX-06. |
| F-25 | UX-301 TRD 11:641 vs FR-261 TRD 02:320; CUS-037 TRD 09:252 | Queue order: not reviewed and not snoozed first, then snoozed, then reviewed | Ordered by date, then code | E2E order assertions are ambiguous. | Choose one in TRD 02 and reference it from TRD 09 and 11. |

### 4.3 Minor

| ID | Location | Description and evidence | Recommendation |
|---|---|---|---|
| F-27 | TRD 00:239, 00:402; TRD 00 §2.1, §9 | The MVP feature set and §8 say "S-01 to S-10", but S-11..S-13 (alerts, analytics, …) exist. The S-rows and the §9 OQ list are out of order. | Change to S-01..S-13 and sort the lists. |
| F-28 | TRD 24 scope; TRD 24:245; AGT-002 (TRD 25) | The scope says contract R1–R26, but R27 is used. AGT-002 cites D-01..D-29, while D-01..D-55 exist. `D-56`/`OQ-27` appear only as "next free" text (informational). | Update the ranges. |
| F-29 | FR-191 TRD 02:245 vs FE-131 TRD 04:514; UX-121; UX-138 | "Mark as reviewed" is *disabled* when there is no alarm in FR-191, but *hidden* in FE and UX. | Choose hidden in TRD 02. |
| F-30 | TRD 04 §4.2, FE-032, AppHeader | See section 3. | — |
| F-31 | FE-204 TRD 04:664 vs NFR-012 TRD 03:59 | The first-load JS budget is 250 kB in FE-204 and 300 KB in NFR-012. | Choose one. |
| F-32 | TRD 01 (ARC stage count, container table); ANL-005; ANL-007; ARC-041 TRD 01:245 | ARC says "ten pure stages", while TRD 07 lists 11–12. The ARC container table lists pandas, but ANL-005 says numpy only. ANL-007's CLI file I/O sits inside the module that ARC-041 says must be pure. | Align TRD 01 with TRD 07, and move the CLI outside the pure package. |
| F-33 | API-059 (TRD 05) vs ARC-057 (TRD 01) | `sslmode` require/verify-full vs one that also allows verify-ca. | Align. |
| F-34 | TRD 05:422 vs API-032 TRD 05:176 | The endpoint summary says `POST /sessions` writes `ingest_batches`; API-032 says it creates none. | Fix the summary row. |
| F-35 | ING-004 vs API-041 | Rejection `errors` keep `value` in one, but must be "identical to the response" (no `input` echo, LOG-043) in the other. | Align. |
| F-36 | ING-031 TRD 10:142 vs FR-003 TRD 02:61; API-048 | CSV headers in any order vs exact header (`CSV_HEADER_MISMATCH`). | Choose one. |
| F-37 | CUS `baseline_stalled` rule vs FR-291 TRD 02:346; OQ-24 | Threshold "+1" off-by-one between TRD 09 and FR-291. | Align. |
| F-38 | UX-355 vs TRD 07 §4.13 | The phrasing of the "alarms raised" note differs. | Use UX wording in TRD 07. |
| F-39 | TRD 17 vs TRD 05/04/02 | Six small mismatches: (1) 500 detail text (LOG-042 vs API-096); (2) health timeout 3 s (LOG-071) vs 2 s (API-110); (3) `run_abandoned` (LOG-066) vs `STALE_RUN` (API-068); (4) error copy LOG-080 vs FE-145; (5) 403 copy LOG-081 vs FE-035; (6) run history 20 (LOG-112) vs 50 (FR-225). LOG-110 also cites DEP-042 where DEP-046 is meant. | Make TRD 17 reference the owning rows. |
| F-40 | CIC-060, LOG-103 vs NFR-104, NFR-020; TST-151 vs CIC-033 | Uptime checks run every 30 min, but the NFRs need 5-minute detection. The nightly-failure issue label is `nightly-failure` vs `ci-failure`. | Align. |
| F-41 | DB-020, DB-016, LOG-065, ANL `PipelineResult`, ANL-033, ANL-041, TRD 19 example, TRD 23:256 | The `pipeline_runs` JSON shapes are inconsistent: (1) the count keys differ; (2) warnings use `type` (DB-016, TRD 23) vs `code` (ANL, LOG) vs `{code, message}` (TRD 19); (3) the `code_version` default is `unknown` vs `local`; (4) `config_snapshot` has "16 keys" vs 23. ANL-041 does not set `error_message`, which `pipeline_runs_error_ck` requires, so recording the failure would itself fail. | TRD 20/23 own the shape. Make ANL-041 set `error_message`. |
| F-42 | SEC-102 TRD 12:293; TRD 12 note vs TRD 20 | The trigger names differ: SEC-102 `audit_logs_no_update_delete` plus triggers on `alert_reviews`/`staff_notes` (TRD 12 note: `forbid_mutation()`), while TRD 20 has `reject_mutation` on `raw_sessions`/`audit_logs` only. | Align TRD 12 with TRD 20, or add the triggers to TRD 20. |
| F-43 | TRD 20 residents CHECK; TRD 19; SEC-084; FE-030 | The resident-code patterns differ: `^[A-Z0-9][A-Z0-9-]{0,31}$` vs `^[A-Za-z0-9]{1,16}$` vs `^[A-Za-z0-9_-]{1,32}$`. | Use one pattern. |
| F-44 | TRD 20 `raw_sessions` vs TRD 10 validation | `phrase_id` is nullable in the DDL but required by validation. `mean_f0_hz > 0` CHECK vs validation that rejects only `< 0`, so a value of 0 passes validation and then fails the insert with a 500. | Align. |
| F-45 | TRD 18 vs FE-201; GIT-081 vs SEC-053; SEC-150; TPS vs FE-004 | Tooling settings differ: Prettier `singleQuote` true vs false; jsx-a11y recommended vs strict; GIT-081 Must vs SEC-053 Should; the Dependabot directories differ (`/analytics`); font weights 400/500/600 vs 400/600. | Align. |
| F-46 | FE-170 vs TRD 21; FE-172 vs ENV-032 | Env var list (section 3); the environment ribbon text differs. | Align. |
| F-47 | TRD 21 `CORS_ORIGIN_REGEX` vs TRD 12 note; API-101 TRD 05:344 | TRD 21 defines a regex origin, while TRD 12 says "do not add allow_origin_regex" and API-101 uses exact origins. | Remove it from TRD 21, or allow it in TRD 12 for previews only. |
| F-48 | TRD 21/15 vs SEC-116; `.env.development.example` | `DATABASE_READONLY_URL` is optional in production vs SEC-116 "only where test_v0_1". The example `DATABASE_URL` uses the superuser `echowell:echowell` rather than the app role. | Align. |
| F-49 | TRD 15 rollback; TRD 15 CLI list vs DB-062, DME-009; DEP-047 vs API-061; AC-DEP-01 vs NFR-087 | Three mismatches: (1) the `deactivate-api-key` command is undefined (the CLI defines `revoke-api-key`); (2) `withdraw-resident --code --date` vs `<code> --on`; (3) DEP-047 skips on running *or* succeeded, while API-061 skips on succeeded only. The deploy target is 15 min vs 10 min. | Align. |
| F-50 | TST-011; CFG-03 vs ANL-029; E2E-21 vs UX-322; E2E-14; TST-013 vs NFR-111 | Five test-spec mismatches: (1) the TST-011 module list omits `data_alerts`/`aggregates`; (2) CFG-03 expects `ValueError` where ANL-029 raises `ConfigError`; (3) E2E-21 says the form is "disabled" where UX-322 says "replaced"; (4) E2E-14 is ambiguous; (5) TST-013 is Should vs NFR-111 Must. | Align. |
| F-51 | TDV-081 TRD 14:708 vs TRD 09 | The false-alarm rate is `count / 800`, while TRD 09 cites 61/600 = 10.2%; with /800 the rate is not near 10%. | Fix the denominator. |
| F-52 | ANL-042 TRD 07:335; DS-01 vs DS-07; AC-PGS-14; DB-056 | ANL-042 maps `is_morning` to "yes"/"no", but the workbook `Exp_scores.morning` is a real boolean (verified). The DS-01 and DS-07 names differ. AC-PGS-14 says "10 (test seed)", but ground truth is not seeded. The DB-056 counts "1/10/10/11/3/1/10" have an unexplained trailing 10. | Fix. |
| F-53 | TRD 25 workflow/phases; AGT-060 | TRD 25 merges to `main`, while GIT-012 targets `staging`. Phase 4 seeds an "admin user from env", but SEC-017/DB-057 use a CLI. The Phase 6/8 input lists are incomplete. AGT-060 has the researcher export through the readonly role, while the API offers a CSV export. | Align TRD 25 with TRD 18/12/06. |
| F-54 | TRD 23 (AC-DME-01, DME-005, `PipelineConfig`) | AC-DME-01 says "21 classes" but 24 entities are defined. DME-005 puts `raw_body` in the batch response, but TRD 19 `IngestRejection` has none. `PipelineConfig.from_rows` vs `from_mapping`. | Align with TRD 19/07. |
| F-55 | SRC-01 vs TRDs (informational) | SRC-01 says analytics is "contained within the backend codebase", while the TRDs use a root `analytics/` package, matching the existing repo skeleton. | Record as a decision in TRD 24. |

---

## 5. Cross-Reference Validation

| Check | Method | Result | Findings |
|---|---|---|---|
| Dangling requirement IDs | Scripted across all 26 TRDs (1,989 IDs) | None dangling, none duplicate, none mis-filed | — |
| OQ / ASM / RSK / DSC / D IDs vs TRD 24 | Scripted | All defined. `D-56`/`OQ-27` are "next free" text only | F-28 |
| Contract R-IDs | Manual | R1–R27 are used, but the TRD 24 scope says R1–R26 | F-28 |
| Endpoints not in TRD 19 | Scripted (31 contract endpoints) | None. `/alerts/{id}/acknowledge` and `/audio` appear only in "shall not exist" statements | — |
| Schema/field names vs TRD 19 | Manual | Many FE and TRD 23 names are not in TRD 19 | F-09, F-11, F-12 |
| Error codes vs TRD 05 catalogue | Scripted | TRD 17 uses 5 codes that are not in the catalogue | F-18 |
| Tables/columns vs TRD 20 DDL | Manual | Missing: `devices`/`device_assignments` "in use until" source, epoch restart cause. CHECKs conflict with F-01 and F-02. Trigger names differ. | F-01, F-02, F-10, F-42, F-44 |
| Grants vs operations | Manual | The baseline delete is not granted | F-03 |
| Env vars vs TRD 21 | Scripted | All referenced env vars are defined. Their meanings conflict for `NEXT_PUBLIC_API_BASE_URL`, `CORS_ORIGIN_REGEX`, `DATABASE_MIGRATION_URL` (web service) and `DATABASE_READONLY_URL` | F-13, F-16, F-46, F-47, F-48 |
| File paths | Manual | `database/seeds/...` and `tests/fixtures/...` are used inside the backend container but not shipped there. The `frontend/lib/config.ts` vs `api.ts` env reading differs. Railway hostnames differ. | F-14, F-15, F-46 |
| Golden fixtures | Checksums | Fixture checksums match TDV-013; the generator script is 495 lines, as stated | — |
| Placeholders | grep `TBD`/`TODO`/`lorem` | Only GIT-053 (TRD 18:219), which is the rule itself | — |

---

## 6. The five checks in detail

### 6.1 Database requirements support all APIs: **FAIL**

**What passes:**

- Every TRD 19 response field for residents, alerts, scores, features, check-ins, notes, reviews, pipeline runs and users traces to a TRD 20 column or a derivation documented in TRD 06 (DB-044 silent days, `day_ledger`, aggregates).
- The roles and grants (DB-009) support the read and write paths, except as listed below.
- `evaluation_ground_truth` isolation (R20) is enforced by grants and by `DATABASE_READONLY_URL`.

**What fails:**

- F-01: every audited API action fails the `audit_logs_action_ck` CHECK.
- F-02: processing late arrivals fails the `processed_sessions` CHECKs.
- F-03: `POST /pipeline/run` with scope `all` after a config change needs a baseline `DELETE` that `echowell_app` lacks.
- F-10: the restart cause and the device "in use until" date have no stored source.
- F-04: the lock keys do not agree, so the DB-level concurrency guarantee behind API-043 does not hold.

### 6.2 APIs support all frontend requirements: **FAIL**

**What passes:** every page in TRD 11 (§4.3–§4.18) has a backing endpoint in TRD 19 (E-01..E-31).

**What fails:**

- F-11: the FE TRD's type definitions use different names for at least 15 fields and schemas. TRD 04:700 says TRD 05/19 must adopt the FE names; TRD 19:1992 says the opposite for code. One of the two must give way.
- F-12: the review explanation list, snooze hours, restart cause, `in_use_until`, separate set-aside/quarantine counts and the "Facility range not available yet" status are each required by UX/FE but not returned by any endpoint.
- F-09: the device silent-day fields have opposite meanings in FE and API.
- F-13: the base URL would double the `/api/v1` prefix.

### 6.3 Analytics requirements support all business requirements: **FAIL**

**What passes:**

- TRD 07, 08 and 09 cover BR-03..BR-11 and BR-15 (section 2.1).
- I re-verified the expected outputs in TRD 08, 09 and 14 against `specs/business-requirements/EchoWell_pipeline_test_v0_1.xlsx`. All of the following match:
  - Status counts 267 / 12 / 2 / 2 / 17 / 2.
  - Baselines 180 rows; Scores 98 rows.
  - `floor_applied` = 8 rows, all `number_of_pauses`.
  - R09 tallies 5.431965 → 26.830256.
  - R10 rings at Oct 24 (5.972050), final 13.418183.
  - "Leaning most": R09 pauses / loudness / voiced fraction; R10 pauses / articulation / speech rate.
  - Set-aside reasons: quality flag 5, noise 5, too short 3.
  - Per-day series as in TRD 14.
  - Usable shares: R08 43%, R03 73%, R02 80%, R05 93%.
  - Last check-in times; D07 last upload Oct 12 14:14.
  - DST and midnight vectors.
  - R08's missing days are never consecutive, so there is correctly no D08 data alert.

**What fails:**

- F-02 (late arrivals, ASM-07/OQ-10) and F-03 (parameter change, NFR-084, BR-15/BR-16) are analytics behaviours that cannot be built as specified.
- F-26: the binding `PipelineConfig` omits the data-alert keys that stage 11 needs.
- F-05: the transaction model is ambiguous.
- F-52 (Minor): ANL-042's `is_morning` "yes"/"no" contradicts the workbook's boolean.

### 6.4 Testing requirements validate all critical functionality: **FAIL**

**What passes:**

- Every BR has a test or MVP criterion.
- The answer-key strategy (TST-070–083, two tiers, no skip or xfail, byte-identical golden files) is strong and complete.
- The auth matrix, rate limits and audit tests (TST-130–137) cover BR-16.

**What fails:**

- F-19: E2E and accessibility are mandatory per TRD 13 but not required checks per TRD 16, and the a11y route lists disagree.
- F-20: six CI checks that TRD 00, 01, 12 and 13 rely on for verification have no workflow.
- F-24: three exact-string tests assert strings that contradict the UX spec.
- Weak spots (section 2.4): the BR-14 populated comparison and the FR-205 transition have no test.
- F-50, F-51 (Minor) are test-spec inconsistencies.

### 6.5 Deployment requirements support the architecture: **FAIL**

**What passes:**

- The interim stack (Netlify / Railway / Neon) and the AWS target in `specs/architecture/Deployment_Architecture.md` are consistently described in TRD 01, 15 and 22.
- The environments matrix and the secrets list are complete in TRD 21.
- The nightly run (Railway cron `0 7,8 * * *`), profile guards (MVP-15) and health checks are specified.

**What fails:**

- F-13: double `/api/v1` prefix.
- F-14: CSP hostnames and headers conflict; the API would be blocked.
- F-15: seed and ground-truth files are not in the backend image.
- F-16: the migrator credential is on the web service.
- F-17: the staging fixed as_of hides demo check-ins.
- F-04: a session-level advisory lock over the Neon pooler.
- F-23: backup targets that the interim plan cannot meet.
- F-40, F-49 (Minor).

---

## 7. Recommended fixes (not applied)

Fix in this order: Critical first, then the contract-owner decisions that unblock several Majors.

| # | Fixes | TRD(s) to change | Action |
|---|---|---|---|
| 1 | F-01 | 12 (owner), 20, 23, 05, 06, 07, 09, 10, 15 | Publish one audit-action vocabulary in TRD 12 and a matching CHECK regex in TRD 20:780. Replace every other action name with a reference. |
| 2 | F-02 | 08, 20, 23 | Decide how a late arrival is represented (relaxed CHECKs, or a new `late_arrival` status). Update the CHECKs at TRD 20:520–530 and BSC-040. |
| 3 | F-03 | 24 (new D-xx), 03, 06, 07, 09, 20 | Split config keys into rebuild-required and operational. Define the privileged rebuild path and its role. Reconcile NFR-084, CUS-046, DB-009 and ANL-032. |
| 4 | F-04 | 06 (owner), 05, 07, 10 | Use one lock-key function and transaction-scoped locks only (or the direct host). Other TRDs reference DB-021. |
| 5 | F-05 | 01 (owner), 06, 07, 17 | Choose per-run or per-resident transactions. |
| 6 | F-06, F-07 | 02, 09, 24, 25 | Define the closure paths once (epoch end, superseded; no manual close in v0.1). |
| 7 | F-08 | 11 (owner), 05, 09, 23, 02 | Data-alert strings from UX §4.17.2 only; create-or-link per FR-273. |
| 8 | F-09, F-11 | 19 (owner), 04, 11, 23, 02 | TRD 19 is the single contract. Regenerate the TRD 04 §4.6.3 types and TRD 23 §4.6 class names from it. Define "silent day" once. |
| 9 | F-10, F-12, F-26 | 20, 06, 19, 05, 07 | Add the epoch restart cause, `in_use_until`, a UI-config endpoint, split counts, `range_not_available`, and the data-alert fields in `PipelineConfig`. |
| 10 | F-13 | 21, 15, 16 (or 04) | Decide whether `NEXT_PUBLIC_API_BASE_URL` is an origin only or includes `/api/v1`. |
| 11 | F-14 | 12 (owner), 04, 15, 21 | One CSP, one header set, one hostname scheme. |
| 12 | F-15 | 15, 16 | Make the seed and fixture files available to the seeding process. |
| 13 | F-16 | 15, 16, 12, 01 | Move migrations out of the web start command, and add `DATABASE_READONLY_URL` to ARC-015. |
| 14 | F-17 | 21, 15, 00 | Restrict the fixed as_of to the test profile, or separate the demo resident. |
| 15 | F-18 | 17 → 05 | TRD 17 references the TRD 05 catalogue. Fix Retry-After and the field-code case. |
| 16 | F-19, F-20 | 16 (owner), 13, 04, 00, 03 | Add the missing CI jobs and required checks. Use one a11y route list. |
| 17 | F-21 | 02 (owner), 10, 06 | Set the ledger end date convention for withdrawal. |
| 18 | F-22 | 10, 20 | Make the `feature_name_map` validation consistent with its seed. |
| 19 | F-23 | 03 (owner), 06, 12, 15, 22 | Set one backup and restore target and drill cadence, plus the Neon plan or an interim waiver. |
| 20 | F-24, F-25 | 02, 13, 14, 11, 09 | Correct the test strings and the queue order. |
| 21 | F-27 – F-55 | As listed in §4.3 | Minor alignment pass, best done after fixes 1–20 so the owning rows are stable. |
