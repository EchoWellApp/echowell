# EchoWell Documentation Completeness Audit

Document: docs/reports/DOCUMENTATION_COMPLETENESS_AUDIT.md · Date: 20 October 2026 · Prompt: `specs/prompts/Generate_Documentation_Audit_Prompt.md` · Branch audited: `backlog-generation` · Auditor: independent (did not write the audited documents) · Location per TRD 25 AGT-032 / TRD 24 D-21

Scope: `specs/TRD/` (26 TRDs, 00–25), `specs/backlog/BACKLOG.md`, `specs/backlog/features/` (97 files), `specs/backlog/IMPLEMENTATION_ROADMAP.md`, `specs/backlog/DEPLOYMENT_CHECKLIST.md`, `specs/backlog/MVP_READINESS_CHECKLIST.md`, and the five wireframes in `specs/UI-wireframe/` (SRC-09 Main, SRC-10 Resident, SRC-11 Admission, SRC-18 Alerts, SRC-19 Analytics). This is a findings-only audit; no audited document was changed.

Note: TRD 25 §4.6 Phase 11 also names this file as a post-implementation output (FEAT-091). This run audits the documentation before implementation (after TRD 25 Phase 12, PR #2); Phase 11 replaces this file with its own run.

## 1. Summary

**Verdict: PASS WITH FINDINGS.** 0 Critical, 0 Major, 12 Minor findings (DA-01 to DA-12).

The documentation set is complete and internally consistent to a high degree. Scripted checks found:

- every BR mapped to a TRD;
- 97.2 % of active TRD requirement IDs cited by a feature, including 100 % of FR, and every gap covered in substance elsewhere;
- all 97 features present with the same metadata in all four places they appear;
- every one of the 24 DDL tables defined and used;
- every one of the 32 endpoints defined and owned by a feature;
- every link resolves;
- no placeholders;
- the wireframe key numbers agree everywhere.

The findings are traceability gaps and small inconsistencies. None would cause a wrong build for an implementer who reads the cited TRD rows.

### 1.1 Pass/fail matrix (prompt items 1–10)

| # | Check | Result | Evidence (summary) | Issues | Recommendation |
|---|---|---|---|---|---|
| 1 | Every business requirement maps to a TRD | **PASS** | BR-01..BR-18 (TRD 00 §4.6) each name primary TRDs; each BR is cited in 9–25 TRDs; TRD 02 §4.28 maps each BR to FRs. | — | — |
| 2 | Every TRD requirement maps to a feature | **PASS WITH FINDINGS** | 1,956 of 2,012 active IDs (26 prefixes) cited by a feature file (1,955) or by a BACKLOG range (1, AGT-031). FR 211/211. 2 retired IDs (FE-026, UX-016) exempt. | 56 IDs uncovered: 10 testable (DA-01), 46 vision, governance or process (DA-02). | Add the 10 testable IDs to feature traces; record the governance exemption. |
| 3 | Every feature maps to implementation tasks | **PASS WITH FINDINGS** | 97/97 features appear in exactly one roadmap phase table, each with a link and an agent prompt for the PR. 12 prompts cover 11 PRs plus After MVP. Every file has the same 21 sections, ≥ 1 FR, ≥ 1 AC and a DoD. Epic, phase, priority, complexity, MVP status and dependencies are identical in the file header, BACKLOG §4, BACKLOG §5 and the roadmap. No dependency points to a later phase. | DA-06 (Required depends on Optional); DA-12 (22 DoDs omit the AC clause; informal "builds on" lists). | See findings. |
| 4 | Every database table is defined | **PASS** | 24 `CREATE TABLE` in TRD 20 §4.6. Every table reference in TRDs, backlog and features resolves to these 24, apart from `alembic_version`, which PGS-006 allows. Each table is used by 3–66 feature files. FEAT-009/010/011/012 split the tables 7 + 3 + 7 + 7 = 24 with no overlap. The grants in the features match TRD 20 §4.8. | — | — |
| 5 | Every API endpoint is defined | **PASS WITH FINDINGS** | E-01..E-32 in TRD 19 §4.3, each with an owner feature. Every `/api/v1/...` reference in all documents resolves to an E-row. The only exceptions are deliberate negative cases (`/alerts/{id}/acknowledge` must not exist, `/audio` must return 404, `DELETE /users/{id}` must return 405/404) and the framework routes `/openapi.json` and `/docs` (API-113). TRD 13 Table 4.13-A agrees with the E-index roles. | DA-11 (TRD 25 Phase 5 router list omits `config.py`). | Add `config.py` to the TRD 25 Phase 5 outputs. |
| 6 | Every algorithm requirement is defined | **PASS WITH FINDINGS** | ANL 65/65, BSC 43/43, CUS 49/49 covered. 23 config keys × 2 profiles in TRD 20 §4.11, and their values (k 0.5, h 5.0, N 16/30, floors, thresholds) are consistent in every document. Stage order ANL-006 (12 stages). Data-alert rules (TRD 09 §4.9) verified against the four expected alerts. | DA-04 (FEAT-001-FR-05 stage order). | Fix the FEAT-001 wording. |
| 7 | Every acceptance criterion has associated tests | **PASS WITH FINDINGS** | All 677 feature ACs are concrete, observable checks. Every feature has a non-empty Testing Requirements section. MVP-01..MVP-15 name tests. FEAT-091-FR-03 and TST-013 own the final AC → test trace. | DA-03: 73 of 281 TRD ACs are cited by no backlog artefact; 155 TRD ACs and 277 feature ACs name no test ID or test file. | Add an AC → test index (or a "Verified by" column). |
| 8 | Every deployment step is documented | **PASS** | DEPLOYMENT_CHECKLIST A–N covers TRD 15 §4.4–§4.16 (Neon, Railway incl. cron, Netlify, GitHub environments, staging and production release, smoke DEP-080/081, bootstrap, first admin, rollback, backups and restore drill, monitoring, demo fallback, AWS go-live). Values match TRD 15/16/21/22 (CORS origins, `DATA_SOURCE_LABEL`, `0 7,8 * * *`, the 8 required checks, the 5 staging secrets, CSP `connect-src`). The local stack is covered by FEAT-006, FEAT-077 and MVP D.06. | — | — |
| 9 | No conflicting requirements exist | **PASS WITH FINDINGS** | Wireframe key numbers agree in every document (§4.3). FR → FEAT agrees in BACKLOG §11, BACKLOG §5 and the feature files (0 differences). All cited IDs exist in the TRDs. | DA-04, DA-05, DA-07, DA-08, DA-09, DA-10, DA-11 (all Minor). | See findings. |
| 10 | No placeholder sections remain | **PASS** | No TBD/TODO/FIXME/lorem. The TRD 25 Phase 12 grep on `specs/backlog` returns nothing. No empty section in any audited file. Remaining "placeholder" words are deliberate domain terms (OQ-03 feature names, local-dev-only passwords, wireframe brackets that UX-* replace). | — | — |

### 1.2 Frontend verification matrix

| Page | Item | Result | Where specified (feature → TRD → test) |
|---|---|---|---|
| Residents Overview | Resident sorting functions | **PASS** | FEAT-027 (API-071/072, `?sort=alarm\|resident_id\|last_checkin`), FEAT-065-FR-02..04 (`SortSelect`, URL state, no client re-sort), TRD 11 §4.13.2; TST-092, E2E-04/05/06, FEAT-060-FR-03 |
| | Alarm status displays correctly | **PASS** | FEAT-065-FR-07 `StatusBadge` ("▲ Alarm since Oct 21", no colour-only), FEAT-027 display status; TST-091, FE-182, E2E-04; UX-021 accent "Alarm on" tile |
| | 30-day counts display correctly | **PASS** | FEAT-065-FR-09, FEAT-027 (`last_30_days`, D-42), UX-039; FE-182, TDV-064/065; R04 duplicates excluded (FEAT-065-AC-06) |
| | Missing days remain visible | **PASS** (trace gap DA-02: VIS-019 uncited) | Overview "missed" count (UX-039/UX-047), tile 4 = 19, check-in log "Missed · no check-in received" / "Device silent" lines (FEAT-068-FR-06/11, UX-150), day ledger never imputed (FEAT-049, VC-G09) |
| | Device panel displays correctly | **PASS** | FEAT-029 (E-17), FEAT-065-FR-13..16 `DevicePanel`, TRD 11 §4.4/§4.13.4; E2E-07, AC-UX-03, FEAT-029-AC-03/04 |
| Resident Detail | CUSUM chart displays correctly | **PASS** | FEAT-067 `CusumChart`/`CusumTable` (E-12 + `baseline_periods`), D-30 colouring from `alarm_state`; FE-183, FE-184, TST-093, TST-112, E2E-08/10/11 |
| | Alarm line at 5.0 present | **PASS** | FEAT-067-FR-05 dashed `ReferenceLine` at `meta.cusum_h` labelled "alarm line 5.0"; FEAT-067-AC-01; UX-084 |
| | Scored features display correctly | **PASS** | FEAT-066-FR-08..12 (7 `FeatureCard`s with `Sparkline` of sign × z, "12 other measurements … stored, not scored"), FEAT-028 (E-11); E2E-08, FEAT-028-AC-07 |
| | Check-In log displays correctly | **PASS** (Minor DA-05) | FEAT-068 `CheckinLog` (UX-140..150), FEAT-028 (E-10); E2E-08/10/11/12 |
| | Staff review section functions | **PASS** | FEAT-071 (`StaffReviewForm`, `NotesList`, `ReviewDialog` reusing `AlertReviewForm`), FEAT-033 (E-15/16), FEAT-031 (E-14/E-28); E2E-09 (FE-187), FE-188, OQ-05 note |
| New Admissions | Facility baseline view exists | **PASS** | FEAT-073 `FacilityRangeChart` + table alternative, FEAT-036 (E-22/23/24), FEAT-012 `facility_reference_ranges`; TST-186, E2E-13, FE-189 |
| | Transition workflow documented | **PASS** (Minor DA-10 wording) | FEAT-053-FR-12 (cohort `new_admission` → `longitudinal` when baseline freezes, audit `resident.cohort_changed`, DB-025), FEAT-036/073 (UX-188, UX-192), TST-185 |
| | Future study-arm functionality identified | **PASS** | FEAT-073 banner "▲ Future / experimental study arm" (UX-181, VIS-009), FEAT-095 (Future; OQ-08, OQ-20, D-76), BACKLOG §8.3 |
| Alert review (D-46) | Change-alarm and data-alert queues, review, snooze | **PASS** | FEAT-069/070, FEAT-030/031/032/048; E2E-17/18/19/21, FE-193, TDV-067/068/076 |
| Analytics (D-46) | KPIs, daily chart, funnel, by-resident, alarm timing / review outcomes, CSV | **PASS** | FEAT-072, FEAT-035/051/034; E2E-20/21, FE-194/195, AN-01..AN-03, TST-068, TST-079 |
| All five | Every wireframe requirement traced to a feature | **PASS** | Each of the 40 rows of TRD 11 §4.16, plus the §4.17/§4.18 requirements, is cited by at least one Phase 8 feature (section 3). |

### 1.3 Findings count

| Severity | Count | IDs |
|---|---|---|
| Critical | 0 | — |
| Major | 0 | — |
| Minor | 12 | DA-01 … DA-12 |

## 2. Coverage tables

### 2.1 Business requirements → TRD (item 1)

| BR | Primary TRDs (TRD 00 §4.6) | TRDs citing it | FRs (TRD 02 §4.28) |
|---|---|---|---|
| BR-01 | 05, 10, 19 | 21 | 33 FRs |
| BR-02 | 01, 06, 20 | 19 | 8 |
| BR-03 | 07, 10 | 15 | 9 |
| BR-04 | 07, 10 | 11 | 10 |
| BR-05 | 07, 08 | 9 | 11 |
| BR-06 | 07, 11 | 16 | 17 |
| BR-07 | 07, 08 | 11 | 6 |
| BR-08 | 07, 08 | 13 | 8 |
| BR-09 | 08 | 17 | 14 |
| BR-10 | 08 | 9 | 10 |
| BR-11 | 09 | 16 | 27 |
| BR-12 | 04, 11 | 18 | 27 |
| BR-13 | 04, 11 | 15 | 50+ |
| BR-14 | 02, 04, 06, 11 | 11 | 9 |
| BR-15 | 13, 14 | 23 | 28 |
| BR-16 | 12, 17 | 25 | 40+ |
| BR-17 | 01, 15, 16, 18, 21, 22 | 15 | 2 |
| BR-18 | all | 18 | 4 + VIS constraints |

All 18 BRs map to TRDs. The scope items S-01..S-13 (TRD 00 §4.8) each name TRDs, and MVP_READINESS §A checks each one.

### 2.2 TRD requirement IDs → features (item 2)

The index was regenerated from the current TRDs. It takes the first-cell IDs of the requirement tables: three-digit IDs, plus BR. The two-digit test IDs CUS-01..07 in TRD 13 are excluded. Coverage counts an ID when it is cited by a feature file, either directly or through an `A..B` range, or by a range in BACKLOG §5.

| Prefix | TRD | Active IDs | Covered | Uncovered | Uncovered IDs |
|---|---|---|---|---|---|
| VIS | 00 | 30 | 6 | 24 | VIS-001..008, 010..013, 015, 017..023, 025..027, 030 (DA-02) |
| ARC | 01 | 76 | 69 | 7 | ARC-035, ARC-100..ARC-105 (DA-01) |
| FR | 02 | 211 | 211 | 0 | — |
| NFR | 03 | 102 | 102 | 0 | — |
| FE | 04 | 141 (+1 retired) | 139 | 2 | FE-090, FE-091 (DA-01) |
| API | 05 | 120 | 120 | 0 | — |
| DB | 06 | 63 | 63 | 0 | — |
| ANL | 07 | 65 | 65 | 0 | — |
| BSC | 08 | 43 | 43 | 0 | — |
| CUS | 09 | 49 | 49 | 0 | — |
| ING | 10 | 59 | 59 | 0 | — |
| UX | 11 | 248 (+1 retired) | 248 | 0 | — |
| SEC | 12 | 121 | 121 | 0 | — |
| TST | 13 | 121 | 121 | 0 | — |
| TDV | 14 | 72 | 72 | 0 | — |
| DEP | 15 | 83 | 83 | 0 | — |
| CIC | 16 | 58 | 58 | 0 | — |
| LOG | 17 | 62 | 62 | 0 | — |
| GIT | 18 | 63 | 63 | 0 | — |
| OAS | 19 | 27 | 27 | 0 | — |
| PGS | 20 | 44 | 44 | 0 | — |
| ENV | 21 | 29 | 29 | 0 | — |
| TPS | 22 | 30 | 29 | 1 | TPS-040 (only DEPLOYMENT_CHECKLIST A.04, DA-01) |
| DME | 23 | 25 | 24 | 1 | DME-018 (DA-01) |
| RAQ | 24 | 18 | 0 | 18 | RAQ-001..RAQ-018 (DA-02) |
| AGT | 25 | 52 | 49 | 3 | AGT-002, AGT-003, AGT-011 (DA-02); AGT-031 is covered only by a BACKLOG range |
| **Total** | | **2,012** | **1,956 (97.2 %)** | **56** | |

Retired and exempt: FE-026, UX-016 (contract §20 R2). No feature cites an ID that does not exist in the TRDs. IDs inside gapped ranges such as FR-001..FR-333 are range artefacts and are not defined requirements.

### 2.3 Features → implementation tasks (item 3)

| Roadmap phase | TRD 25 phase(s) | PRs | Features | Agent prompt |
|---|---|---|---|---|
| 1 Repository Setup | 2, 3 | 2 | 1 + 6 | §5.6 (two prompts) |
| 2 Database Layer | 4 | 1 | 10 | §6.6 |
| 3 Backend API | 5 | 1 | 22 | §7.6 |
| 4 Analytics Engine | 6 | 1 | 17 | §8.6 |
| 5 Algorithm Validation | 7 | 1 | 5 | §9.6 |
| 6 Frontend | 8 | 1 | 15 | §10.6 |
| 7 Authentication (gate) | — | 0 | 0 (verifies FEAT-015/016/020/021/022/039/063/064) | §11.6 |
| 8 Deployment | 9, 10 | 2 | 11 + 3 | §12.6 (two prompts) |
| 9 Final Audit | 11 | 1 | 1 | §13.6 |
| After MVP | Post-MVP / Future | per item | 6 | §14 template |
| **Total** | | | **97** | |

The counts by MVP status are Required 89, Optional 2 (FEAT-061, FEAT-084) and Future 6 (FEAT-092..097), and they match BACKLOG §8. The completion status of all 97 features is Not Started, the same in BACKLOG §10 and in every feature header. All relative links in the roadmap, BACKLOG and feature files resolve.

### 2.4 Database tables (item 4)

| Table (TRD 20 §4.6) | Created by | Features using it | Table (TRD 20 §4.6) | Created by | Features using it |
|---|---|---|---|---|---|
| facilities | FEAT-009 | 14 | pipeline_runs | FEAT-011 | 32 |
| users | FEAT-009 | 25 | epochs | FEAT-011 | 27 |
| residents | FEAT-009 | 66 | processed_sessions | FEAT-011 | 26 |
| devices | FEAT-009 | 41 | day_ledger | FEAT-011 | 21 |
| device_assignments | FEAT-009 | 15 | baselines | FEAT-011 | 34 |
| api_keys | FEAT-009 | 11 | scores | FEAT-011 | 40 |
| config_parameters | FEAT-009 | 23 | cusum_state | FEAT-011 | 20 |
| ingest_batches | FEAT-010 | 9 | alerts | FEAT-012 | 52 |
| ingest_rejections | FEAT-010 | 11 | alert_reviews | FEAT-012 | 11 |
| raw_sessions | FEAT-010 | 30 | data_alerts | FEAT-012 | 14 |
| staff_notes | FEAT-012 | 8 | facility_reference_ranges | FEAT-012 | 3 |
| audit_logs | FEAT-012 | 29 | evaluation_ground_truth | FEAT-012 | 14 |

### 2.5 API endpoints (item 5)

| E | Endpoint | Owner feature | E | Endpoint | Owner feature |
|---|---|---|---|---|---|
| E-01 | GET /health | FEAT-003 | E-17 | GET /devices | FEAT-029 |
| E-02..E-04 | POST /auth/login, POST /auth/logout, GET /auth/me | FEAT-020 | E-18 | GET /analytics | FEAT-035 (+FEAT-051) |
| E-05 | POST /sessions | FEAT-025 | E-19 | GET /analytics/baselines | FEAT-034 |
| E-06, E-07 | POST /ingest, GET /ingest/batches/{id} | FEAT-026 | E-20, E-21, E-31 | pipeline run/runs | FEAT-024 |
| E-08 | GET /residents | FEAT-027 | E-22..E-24 | admissions, comparison, reference ranges | FEAT-036 |
| E-09..E-11 | resident detail, checkins, features | FEAT-028 | E-25..E-27 | users | FEAT-037 |
| E-12 | GET /scores | FEAT-034 | E-28, E-29 | GET reviews, POST snooze | FEAT-031 |
| E-13 | GET /alerts | FEAT-030 (+FEAT-048 `leaning_most`) | E-30 | GET /data-alerts | FEAT-032 |
| E-14 | POST /alerts/{id}/reviews | FEAT-031 | E-32 | GET /config/ui | FEAT-030 |
| E-15, E-16 | notes GET/POST | FEAT-033 | | contract drift (all) | FEAT-038 |

### 2.6 Acceptance criteria → tests (item 7)

| Set | Count | With an explicit test ID or test file | Without | Cited by a backlog artefact |
|---|---|---|---|---|
| TRD AC-xxx-NN | 281 | 126 | 155 (stated as observable checks, no test ID) | 208 (188 by features, 20 more only by checklists/roadmap); **73 by none** (DA-03) |
| Feature FEAT-NNN-AC-NN | 677 | 400 | 277 (99 of them with no test, command or inspection wording; all covered by the feature's Testing Requirements section) | n/a |
| MVP-01..MVP-15 (TRD 13 §4.17) | 15 | 15 | 0 | 15 (MVP_READINESS §C) |
| VC-R01..R10, VC-G01..G12 | 22 | 22 | 0 | 22 (MVP_READINESS §F, FEAT-059) |

## 3. UI_REQUIREMENTS_TRACEABILITY_MATRIX

Columns: Wireframe requirement (TRD 11 §4.16 element, UX IDs) → Feature → Component (TRD 04 §4.8 names) → API (TRD 19 E-xx) → Test coverage. Every component named in TRD 04 §4.8 appears in a feature file. All 40 TRD 11 §4.16 rows have at least one Phase 8 feature.

### 3.1 SRC-09 Residents overview (`/residents`, `Main.dc.html`)

| Wireframe requirement | Feature | Component | API | Test coverage |
|---|---|---|---|---|
| Header "EchoWell", subline "Voice check-ins · [Facility name] · Showing … as of …"; nav (wireframe "Residents / New admissions / Devices", replaced by the unified nav Residents · Alerts (n) · Analytics · New admissions [· Admin], contract R2) — UX-010..UX-018 | FEAT-064, FEAT-065 | AppHeader | E-08 `meta`; E-13 `status=open` (nav count) | AppHeader component test (TST-090), E2E-01, E2E-14, E2E-21 |
| Tiles "Alarm on 2 / Being watched, no alarm 7 / Baseline still forming 1 / Missed check-ins, last 30 days 19" — UX-020..UX-024, UX-260 | FEAT-027, FEAT-065 | SummaryTiles | E-08 `summary` | FE-181, E2E-03, OAS-021, TDV-062, FEAT-027/060 integration, AC-UX-01 |
| "Sort by" Alarms first / Resident ID / Last check-in — UX-030..UX-033, UX-261 | FEAT-027, FEAT-065 | SortSelect, ResidentsTable | E-08 `?sort=` | TST-092, E2E-04/05/06, FEAT-027-AC-08, FEAT-060-FR-03 |
| Table columns and rows R09…R06 (device, status, last check-in, used · set aside · quarantined · missed, Open) — UX-034..UX-048 | FEAT-027, FEAT-065 | ResidentsTable, StatusBadge, DeviceCell | E-08 `items` | FE-182, TST-091, E2E-04, TDV-063..065 |
| Badges "▲ Alarm since Oct 21", "Baseline forming · 13 of 16 sessions", "No alarm · baseline restarted Oct 13", "No alarm" — UX-036, §4.3.4 | FEAT-065 (wording FEAT-062) | StatusBadge (`lib/wording.ts`) | E-08 `status`, `alarm_since`, baseline | TST-091, FEAT-065-AC-07, TST-097 |
| "D07B (was D07)", "D02 (shared)" — UX-035 | FEAT-065, FEAT-027 | DeviceCell | E-08 `device_*` | FE-182, FEAT-065-AC-02 |
| Missing days visible (missed column, never backfilled) — UX-039, UX-047, UX-048 | FEAT-065, FEAT-049, FEAT-014 | ResidentsTable | E-08 `last_30_days.missed` | FE-182, VC-G09, FEAT-065-AC-06 |
| "Open" links — UX-040 | FEAT-065 | ResidentsTable | — | FEAT-065-FR-10, E2E-08 (navigation) |
| Devices cards D02 shared / D07B replacement / grouped D01, D04–D06, D08–D10; "Show all devices (10)" — UX-050..UX-058, UX-263 | FEAT-029, FEAT-065 | DevicePanel | E-17 | E2E-07, AC-UX-03, FEAT-029-AC-03/04, FEAT-065-AC-04/05 |
| Footer (overview variant) — UX-005 | FEAT-065, FEAT-062 | Footer | — | Text tests TST-097, AC-VIS-06 |

### 3.2 SRC-10 Resident detail (`/residents/[residentCode]`, `Resident.dc.html`)

| Wireframe requirement | Feature | Component | API | Test coverage |
|---|---|---|---|---|
| "← Back to all residents" — UX-060 | FEAT-064, FEAT-066 | BackLink | — | FEAT-064-AC-04 |
| "R09 · Device D09", baseline line "first 16 usable check-ins, Oct 1–16 (then frozen) · watched since Oct 17", "▲ Alarm since Oct 21" — UX-061..UX-066 | FEAT-028, FEAT-066 | ResidentHeader, StatusBadge | E-09 | E2E-08, FE-186, AC-API-03, FEAT-028-AC-02, FEAT-066-AC-01/04/05 |
| "What this means" + "[Final clinical wording: confirm with PI]" — UX-070..UX-075, UX-160..UX-164 | FEAT-066, FEAT-062 | WhatThisMeans | E-09 `explanation` | TST-096, TST-097, FEAT-066-AC-02 |
| "Running change tally", subtitle, bars (grey baseline / accent post-alarm), dashed "alarm line 5.0", "Oct 17 / Oct 21 · alarm / Oct 30", caption — UX-080..UX-092 | FEAT-067, FEAT-034 | CusumChart, CusumTable | E-12 (`baseline_periods`, `?epoch=`), `meta.cusum_h` | FE-183, FE-184, TST-093, TST-112, E2E-08/10/11, OAS-022, FEAT-067-AC-01..07 |
| "The 7 measurements behind the score", 7 cards, "12 other measurements … stored, not scored", caption — UX-100..UX-108 | FEAT-066, FEAT-028 | FeatureCard, Sparkline, OtherMeasurementsCard | E-11 | E2E-08, FEAT-028-AC-07, FEAT-066-AC-03/04 |
| "Staff review": note, "Mark as reviewed", OQ-05 note — UX-120..UX-135 | FEAT-071, FEAT-070, FEAT-033, FEAT-031 | StaffReviewForm, NotesList, ReviewDialog (AlertReviewForm) | E-15, E-16, E-14, E-28 | E2E-09 (FE-187), FE-188, FEAT-071-AC-01..07, TST-056..067 |
| "Check-in log" entries and legend — UX-140..UX-150 | FEAT-068, FEAT-028 | CheckinLog | E-10 | E2E-08/10/11/12, FE-186, FEAT-028-AC-03..05, FEAT-068-AC-01..06 |
| Footer (default) — UX-005 | FEAT-066, FEAT-062 | Footer | — | TST-097 |

### 3.3 SRC-11 New admissions (`/admissions`, `Admission.dc.html`)

| Wireframe requirement | Feature | Component | API | Test coverage |
|---|---|---|---|---|
| "← Back to all residents" — UX-180 | FEAT-073, FEAT-064 | BackLink | — | FEAT-073-AC-01 |
| Experimental banner "Not in pipeline test v0.1 …" — UX-181 | FEAT-073 | ExperimentalBanner | — | FE-189, E2E-13, AC-UX-07 |
| "New admissions" header and intro — UX-182 | FEAT-073 | (page header) | — | E2E-13 |
| Table Resident / Admitted / Check-ins so far / Compared with facility range / Own baseline; badges — UX-183..UX-188 | FEAT-073, FEAT-036 | AdmissionsTable | E-22 | TST-186, FEAT-036 integration, FEAT-073-AC-02/03 |
| "[Study ID] compared with facility range" chart, caption "grey band = usual range…", table alternative — UX-189..UX-193 | FEAT-073, FEAT-036, FEAT-012 | FacilityRangeChart | E-23, E-24 | TST-186, FEAT-073-AC-04 |
| Transition sentence "Once [N] days … moves to the main list" (workflow) — UX-188, UX-192, FR-205 | FEAT-053 (cohort transition), FEAT-036, FEAT-073 | — / AdmissionsTable | E-22, E-08 | TST-185, FEAT-053-AC-08 |
| Range method line — UX-195 | FEAT-073, FEAT-095 (Future) | FacilityRangeChart | E-24 | TST-186 |
| Empty state (test data has no admission arm) — UX-194, UX-264 | FEAT-073 | AdmissionsTable | E-22 | FE-189, E2E-13 |
| Footer — UX-005 | FEAT-073 | Footer | — | FEAT-073-AC-05 |

### 3.4 SRC-18 Alert review (`/alerts`, `Alerts.dc.html`)

| Wireframe requirement | Feature | Component | API | Test coverage |
|---|---|---|---|---|
| Header "Alert review", subline, nav "Residents / Alerts (2) / Analytics" — UX-010, UX-013, UX-017, UX-018 | FEAT-064, FEAT-069 | AppHeader | E-13 `status=open` | TST-090, E2E-17 |
| "Change alarms · need a nurse review": R09 · D09 "Not reviewed" "Alarm since Oct 21 · open 9 days · tally 26.8"; R10 … "open 6 days · tally 13.4" — UX-300..UX-305, UX-330 | FEAT-069, FEAT-030 | AlertQueue, AlertCard | E-13 (open + acknowledged) | E2E-17, FE-193, TDV-067, FEAT-069-AC-01/05/07 |
| "Data alerts · go to the study team": R08, R05, R03, D02 — UX-306..UX-309, UX-331 | FEAT-069, FEAT-032, FEAT-050 | DataAlertQueue | E-30 | E2E-17, TDV-068, FEAT-069-AC-02, TRD 13 data-alert unit cases (DA-01..DA-10 of TRD 13 Table 4.3-A, not this report's findings) |
| "R09 · alarm since Oct 21" + "Open full resident view →" — UX-310 | FEAT-069 | AlertReviewPanel | E-13 | FEAT-069-AC-03 |
| Mini chart "Change tally since watching began (alarm line 5.0)" — UX-311 | FEAT-069, FEAT-067 | MiniTallyChart (CusumChart) | E-12 | FEAT-069-AC-03 |
| "Leaning most" (R09 "more pauses, quieter, less voiced sound") — UX-312 | FEAT-069, FEAT-048 | LeaningMost | E-13 `leaning_most` | AN-08, FEAT-069-AC-03/04 |
| "Anything that could explain it?" checklist — UX-313 | FEAT-070, FEAT-030 | AlertReviewForm | E-32 `review_explanations`, E-14 | FEAT-070-AC-03 |
| "Review outcome" radio (required) — UX-314, UX-316 | FEAT-070, FEAT-031 | AlertReviewForm | E-14 | E2E-18, FEAT-070-AC-01/02 |
| "Note", "Save review", "Remind me in [24 h]" — UX-315..UX-318 | FEAT-070, FEAT-031 | AlertReviewForm | E-14, E-29, E-32 `alert_snooze_hours` | E2E-18, E2E-19, FE-193, FEAT-070-AC-02/04, TST-056..067 |
| Previous reviews (contract §19) — UX-320 | FEAT-070 | ReviewHistory | E-28 | FEAT-070-AC-06 |
| Open-questions note (OQ-05, OQ-26) — UX-321 | FEAT-070 | AlertReviewPanel | — | FEAT-070-AC-07 |
| Role restriction (researcher read-only) — UX-322 | FEAT-070, FEAT-021 | AlertReviewForm | E-14/E-29 (403) | E2E-21, FEAT-070-AC-05, TST-130 |
| Footer (alert review) — UX-005 | FEAT-069 | Footer | — | FEAT-069-AC-06 |

### 3.5 SRC-19 Analytics (`/analytics`, `Analytics.dc.html`)

| Wireframe requirement | Feature | Component | API | Test coverage |
|---|---|---|---|---|
| Header, subline "… numbers match the pipeline answer key", nav; researcher/admin only — UX-010, UX-013, UX-017, UX-350 | FEAT-064, FEAT-072 | AppHeader, AnalyticsPage | E-18 `meta` | E2E-21, FEAT-072-AC-06/07, FE-037 |
| KPI tiles 94 % "281 of 300 expected" / 89 % "267 of 300" / "9 of 10" / 2 — UX-351..UX-355, UX-380 | FEAT-072, FEAT-035, FEAT-051 | KpiTiles | E-18 `kpis` | E2E-20, FE-194, AN-01, FEAT-072-AC-01 |
| "Check-ins per day" stacked chart, legend, "Oct 12 · D02 silent" — UX-356..UX-361, UX-381 | FEAT-072, FEAT-051 | DailyCheckinsChart | E-18 `daily_series` | FE-194, FEAT-072-AC-04 |
| "Where check-ins are lost" 300 → 281 → 269 → 267 — UX-362..UX-366, UX-382 | FEAT-072, FEAT-051 | LossFunnel | E-18 `funnel` | AN-03, E2E-20, FEAT-072-AC-02 |
| "Usable check-ins by resident" R08 43 % … R10 100 % — UX-367..UX-370, UX-383 | FEAT-072, FEAT-051 | UsableByResidentChart | E-18 `by_resident` | E2E-20, FEAT-072-AC-03 |
| "Alarm timing check · test data only …" R09 0 days, R10 7 days, Other 8 correct; production variant "alarms raised, reviewed, review outcomes" — UX-371..UX-375, UX-384 | FEAT-072, FEAT-035 | AlarmTimingTable, ReviewOutcomesTable | E-18 `alarm_timing` / `review_outcomes` (evaluation_ground_truth via read-only engine, test_v0_1 only) | E2E-20, FE-195, TST-068, FEAT-072-AC-05/06 |
| Downloads Scores / Baselines CSV — UX-377 | FEAT-072, FEAT-034 | AnalyticsPage | E-12, E-19 (`text/csv`) | TST-079 |
| Footer "Counts only — no audio, no resident names." — UX-005 | FEAT-072 | Footer | — | FEAT-072-AC-05 |

### 3.6 Key numbers cross-check (item 9)

| Value | TRD 11 | TRD 14 / 07 / 19 | Features | MVP checklist | Consistent |
|---|---|---|---|---|---|
| Tiles 2 / 7 / 1 / 19 (19 = 17 missing_resident + 2 missing_device_gap) | §4.3.1, AC-UX-01 | TRD 10 worked check, OAS-021, AC-DB-05, AC-DME-05 | FEAT-027, FEAT-065-AC-01 | B.02, C.04, D.06, K.02 | Yes |
| Default order R09, R10, R08, R07, R03, R02, R05, R01, R04, R06; last-check-in order R02, R07, R05, R10, R06, R08, R09, R03, R04, R01 | §4.13.2 | API-071, E2E-06 | FEAT-027-AC-08, FEAT-060-FR-03, FEAT-065-AC-03 | — | Yes |
| R09 alarm Oct 21 (tally 5.431965 → 26.830256), R10 Oct 24 (5.972050 → 13.418183); open 9 / 6 days | §4.13.3, §4.17.6 | TRD 14 §4.7.9/§4.7.10, CUS-028, AC-VIS-10 | FEAT-059, FEAT-067-AC-02, FEAT-069-AC-01 | K.10, F.09, F.10 | Yes |
| Analytics 281/300 = 94 %, 267/300 = 89 %, 9 of 10, 2; funnel 300/281/269/267; R08 43 %, R03 73 %, R02 80 %, R05 93 %; timing 0 and 7 days | §4.18.7 | TRD 07 §4.13, TRD 19 E-18, AN-01/AN-03, AC-TDV-11 | FEAT-072-AC-01..05 | C.14, K.10 | Yes |
| 4 data alerts (R08 baseline stuck 13 of 16, R05 Oct 8/22, R03 7 of 29, D02 Oct 12) | §4.17.6 | TRD 09 §4.9 | FEAT-050, FEAT-069-AC-02 | C.13 | Yes |
| Baselines 180 rows, scores 98 (off 81, on 15, RINGS 2) | — | VC-G05, VC-G06 | FEAT-059 | B.01, F.15, F.16 | Yes |

## 4. Findings

Each finding was checked against the cited lines. Severity follows the audit brief: Critical (wrong or unsafe build), Major (an implementer would very likely build the wrong thing or a required test would fail), Minor (genuine inconsistency that is harmless to a careful implementer).

### DA-01 — Minor — Ten testable TRD requirements are cited by no feature

- **Location:**
  - `specs/TRD/01_System_Architecture_TRD.md:195` (ARC-035), `:403–408` (ARC-100..ARC-105)
  - `specs/TRD/23_Data_Model_and_Entity_Definitions.md:76` (DME-018)
  - `specs/TRD/04_Frontend_TRD.md:474–475` (FE-090, FE-091)
  - `specs/TRD/22_Third_Party_Services_and_Hosting.md:137` (TPS-040)
- **Evidence:** None of the 97 feature files and no BACKLOG range cites these IDs. The substance is covered elsewhere for all but one of them:
  - X-Request-ID: FEAT-018/019.
  - problem+json: FEAT-019.
  - `timestamptz`: FEAT-008/010.
  - Audit log: FEAT-015.
  - No LLM: FEAT-039/078.
  - Single facility "Edgewood": FEAT-009/017.
  - Review outcomes in production: FEAT-035.
  - SRC-06 rejected with 422: FEAT-026/057.
  - Org 2FA: only DEPLOYMENT_CHECKLIST A.04.

  The exception is FE-090/FE-091: the component props interfaces and the rule that presentational components must not fetch data appear in no feature at all. The FEAT-065..073 data-flow sections only imply that pages fetch.
- **Recommendation:**
  - Add the IDs to the Referenced TRDs and FR traces:
    - ARC-100 and ARC-101: FEAT-018, FEAT-019.
    - ARC-102: FEAT-008.
    - ARC-103: FEAT-015.
    - ARC-104: FEAT-078.
    - ARC-105: FEAT-009.
    - ARC-035: FEAT-035.
    - DME-018: FEAT-026.
    - FE-090 and FE-091: FEAT-062, with an FR "presentational components receive data as props".
    - TPS-040: FEAT-087 or FEAT-088.

### DA-02 — Minor — Vision, governance and process requirement IDs are cited by no feature

- **Location:** `specs/TRD/00_Project_Vision_and_Scope.md:249–278` (VIS), `specs/TRD/24_Risk_Assumptions_and_Open_Questions.md:54–71` (RAQ), `specs/TRD/25_AI_Agent_Build_Instructions.md:94–95, 103` (AGT-002, AGT-003, AGT-011).
- **Evidence:**
  - VIS: 24 of 30 are uncited by features. 11 of those are cited by the roadmap or MVP checklist; 13 are cited nowhere in the backlog (VIS-002, -003, -004, -007, -008, -011, -013, -015, -017, -019, -021, -025, -026).
  - RAQ: 0 of 18 cited.
  - AGT-002, AGT-003, AGT-011: uncited.

  Most are restated by lower-level IDs that are covered. For example, VIS-019 "missing days remain visible" is covered by UX-047, UX-150 and FR-121..125, and VIS-026 by ENV-010. RAQ governs the TRD 24 register and is exercised through AGT-009. Nothing is unimplemented, but the trace from feature to vision row is missing, and BACKLOG does not state that these rows are exempt.
- **Recommendation:** Map the VIS rows to the features that realise them, or add a sentence to BACKLOG §1/§11 stating that the VIS, RAQ and process-only AGT rows are verified by the Phase 1 and Phase 11 audits (FEAT-091) rather than by a feature.

### DA-03 — Minor — Acceptance criteria lack an explicit test link

- **Location:** TRD §7 acceptance-criteria lists (all 26 TRDs); the AC tables of the feature files; `specs/backlog/features/FEAT-091-Final-Implementation-TRD-Traceability-Documentation-And.md:56`.
- **Evidence:**
  - 155 of 281 TRD ACs name no test ID. They are written as observable checks, for example AC-DB-02 "`baselines` has 180 rows …".
  - 73 TRD ACs are cited by no backlog artefact:
    - AC-ARC-02/04/05/07/10/11
    - AC-FR-01/02/03/05/06/07/08/09/11/14
    - AC-NFR-01..12
    - AC-FE-07/09/11
    - AC-API-08/10/11/12/13/18
    - AC-DB-01/02/03/04/06/09
    - AC-ANL-12, AC-CUS-11
    - AC-ING-02/07, AC-UX-08
    - AC-TDV-08
    - AC-LOG-03/09/10
    - AC-GIT-03/04/07/08
    - AC-DME-01..09
    - AC-RAQ-01..07
  - Feature AC tables have the columns ID | Criterion | Realises (a requirement), with no test column. 277 of 677 feature ACs name no test ID or test file. The Testing Requirements sections list the tests, but the AC → test pairing is left implicit.
  - FEAT-091-FR-03 defers the "every AC has a linked test" check to Phase 11 (`tests/trace_report.py`, TST-013).
- **Recommendation:** Add a "Verified by" column to the feature AC tables, or an AC → test index in TRD 13 or BACKLOG. Cite the 73 uncited TRD ACs from the features that realise them; for example AC-DB-01..04 from FEAT-055/059 and AC-API-08..13 from FEAT-024/025/054/003.

### DA-04 — Minor — FEAT-001 states the wrong final pipeline stage

- **Location:** `specs/backlog/features/FEAT-001-Technical-Design-Documents.md:57` (FEAT-001-FR-05).
- **Evidence:** FR-05 requires `Analytics_Architecture.md` to show the stage order "with … data-alert generation last". TRD 01 ARC-040 (`01_System_Architecture_TRD.md:245`) and TRD 07 ANL-006 (`07_Analytics_Engine_TRD.md:72`) fix data alerts as stage 11 and analytics aggregates as stage 12, last. FEAT-050 and FEAT-051 agree with the TRDs. FR-05 also cites ARC-040, so the conflict sits inside one row. FEAT-001-FR-10 forbids the design documents from contradicting a TRD.
- **Recommendation:** Change FR-05 to "data alerts (stage 11) followed by analytics aggregates (stage 12, last)".

### DA-05 — Minor — Same-date order of check-in log events is not passed to the backend feature

- **Location:**
  - `specs/backlog/features/FEAT-028-Resident-Detail-Check-In-Log-And.md:164` (Implementation Notes) and `:61` (FEAT-028-FR-08)
  - `specs/TRD/11_User_Interface_UX_Spec.md:351` (UX-141)
  - `specs/TRD/04_Frontend_TRD.md:485` (FE-101)
  - `specs/TRD/05_Backend_API_TRD.md:244` (API-077)
  - `specs/TRD/19_API_Contracts_OpenAPI_Spec.md:304`
- **Evidence:**
  - UX-141 fixes the order of events on the same date: alarm, watching_started, baseline_complete, baseline_restarted, quarantined, set_aside, device_silent, missed.
  - FE-101 and FEAT-068-FR-02 render the API order and forbid client re-sorting.
  - The backend specs (API-077, TRD 19 E-10) say only "newest first".
  - FEAT-028 tells the backend agent: "TRD 19 shows only date order; choose a deterministic secondary key and document it in the batch report". FEAT-028 does not cite UX-141.

  The DS-07 fixture has no same-date events, so no test catches a mismatch.
- **Recommendation:** Add the UX-141 secondary order to FEAT-028-FR-08 and to API-077 / TRD 19 E-10, and add a same-date fixture case to FEAT-028 or FEAT-068.

### DA-06 — Minor — A Required feature depends on an Optional feature

- **Location:**
  - `specs/backlog/features/FEAT-080-E2E-Performance-And-Nightly-Workflows.md:10` (Dependencies) and `:135` (FEAT-080-AC-03)
  - `specs/backlog/BACKLOG.md:132` (FEAT-080 catalogue row) and `:113` (FEAT-061 Optional)
  - `specs/backlog/BACKLOG.md:2283`
- **Evidence:** FEAT-080 (Required) lists FEAT-061 (Optional, P2) as a hard dependency, and FEAT-080-AC-03 requires the `nightly-validation` robustness step built by FEAT-061. BACKLOG §8.2 states that "Optional features … never block a phase definition of done". This is the only Required → Optional dependency among the 97 features. Impact is low: FEAT-061 is scheduled in Phase 7 anyway, and the TRD rows (TDV-080..083, CIC-037) are Should.
- **Recommendation:** Either reclassify FEAT-061 as Required, or make FEAT-080's robustness step conditional on `tests/validation/robustness.py` existing and drop FEAT-061 from its hard dependencies.

### DA-07 — Minor — Stale decision-range count in BACKLOG inputs

- **Location:** `specs/backlog/BACKLOG.md:13`.
- **Evidence:** "TRD 24 the OQ, ASM, RSK, DSC and D-01..D-74 registers". TRD 24 now defines D-01..D-98 (98 rows), BACKLOG itself cites D-75..D-98 (revision 0.2, §12), and the roadmap (`IMPLEMENTATION_ROADMAP.md:11`) says D-01..D-98.
- **Recommendation:** Change it to D-01..D-98.

### DA-08 — Minor — Stale "conflict" notes in feature files

- **Location:**
  - `specs/backlog/features/FEAT-069-Alert-Review-Page-Change-Alarm-Queue.md:143` and `:137`
  - DoD bullets: `FEAT-034…md:147`, `FEAT-050…md:134`, `FEAT-064…md:142`, `FEAT-066…md:139`, `FEAT-072…md:138`
- **Evidence:**
  - FEAT-069's note says "FR-266 writes the empty Leaning-most text without a final period, UX-312 with one". `specs/TRD/02_Functional_Requirements_Specification.md:326` now reads "No single measurement stands out." with the period, the same as UX-312.
  - The listed DoD bullets say "the TRD conflict(s) below are reported in the batch report". The notes they point to now record conflicts already resolved in PR #2 (FR-150, FR-169, FR-244, FR-294, FR-310 and BaselineRow `minimum: 0`; each was verified as aligned in the TRDs).
  - An agent would report conflicts that no longer exist.
- **Recommendation:** Delete the FR-266 note. Change these DoD bullets to "the batch report lists the implemented IDs", or label the notes "resolved (PR #2)".

### DA-09 — Minor — The "one PR per phase, in order" acceptance rule contradicts the planned Phase 12 runs

- **Location:**
  - `specs/TRD/25_AI_Agent_Build_Instructions.md:338` (AC-AGT-01)
  - `specs/backlog/MVP_READINESS_CHECKLIST.md:204` (L.01)
  - `specs/TRD/25_AI_Agent_Build_Instructions.md:153` (AGT-031) and `:286` (Phase 12 DoD)
  - TRD 24 D-95
  - `specs/backlog/IMPLEMENTATION_ROADMAP.md:54`
- **Evidence:** AC-AGT-01 and L.01 require that each TRD 25 Phase 1–12 has exactly one merged PR, in order. However:
  - Phase 12 ran as PR #2, before Phase 2, which AGT-031 allows.
  - Phase 12 is to be re-run after Phase 11 (D-95; roadmap §3.1, §13).
  - The roadmap gives the re-run no branch or PR.

  Read literally, L.01 cannot pass, even though every row of A–L must pass for MVP acceptance.
- **Recommendation:** Reword AC-AGT-01 / L.01 to "… in the TRD 25 §4.5 order, except Phase 12, which runs before Phase 2 (AGT-031) and is re-run after Phase 11 (D-95)". Name the branch and PR of the re-run in the roadmap.

### DA-10 — Minor — New-admission baseline progress worded as "days" while it counts check-ins

- **Location:**
  - `specs/TRD/11_User_Interface_UX_Spec.md:386` (UX-186) and `:392` (UX-192)
  - `specs/backlog/features/FEAT-073-New-Admissions-Page.md:49` (FR-03) and `:55` (FR-09)
- **Evidence:**
  - UX-186 renders "<n> of <N> days" but defines n as "the resident's usable check-ins towards their own baseline".
  - UX-192 says "Once <N> days of check-ins are collected, this resident moves to the main list".
  - The transition actually happens when the Nth usable record freezes the baseline (DB-025, FEAT-053-FR-12, TST-185).
  - Elsewhere the same quantity reads "<n> of <N> sessions" (UX-036) or "usable check-ins" (UX-063).

  The wording comes from the wireframe ("[n] of [N] days"). With missed or set-aside days, days and usable check-ins differ.
- **Recommendation:** Record the wording choice in TRD 24 (it concerns the OQ-08/OQ-29 page), or change the texts to "check-ins" consistently in UX-186, UX-192 and FEAT-073.

### DA-11 — Minor — TRD 25 Phase 5 router list omits `config.py`

- **Location:** `specs/TRD/25_AI_Agent_Build_Instructions.md:208` (Phase 5 Outputs).
- **Evidence:** The list "Routers under `backend/api/` as listed in TRD 05 §4.1 (… `health.py`, `residents.py`, `sessions.py`, `alarms.py`, `analytics.py`, plus `auth.py`, `ingest.py`, `scores.py`, `devices.py`, `pipeline.py`, `admissions.py`, `users.py`, `deps.py`)" has no `config.py`. TRD 05 §4.1 (`05_Backend_API_TRD.md:75`) and FEAT-030 (`FEAT-030…md:37`) put `GET /api/v1/config/ui` (E-32) in `backend/api/config.py`.
- **Recommendation:** Add `config.py` (E-32) to the TRD 25 Phase 5 output list.

### DA-12 — Minor — Inconsistent Definition of Done and reverse-dependency wording in feature files

- **Location:**
  - DoD sections of FEAT-026, FEAT-028, FEAT-029, FEAT-031..FEAT-040, FEAT-042..FEAT-049 and FEAT-059
  - "Features that build directly on this one" lines in FEAT-002..FEAT-025 (for example `FEAT-007…md`, `FEAT-023…md`, `FEAT-024…md`, Dependencies section)
- **Evidence:**
  - 75 of the 97 DoDs start "All FEAT-NNN acceptance criteria pass". These 22 do not mention the ACs at all; they list implementation and test conditions only.
  - The informal reverse-dependency lines disagree with BACKLOG §4 in 15 files:
    - FEAT-007 names FEAT-080, which depends on it only through FEAT-078.
    - FEAT-023 names FEAT-026.
    - FEAT-024 names FEAT-054/055 but omits FEAT-038 and FEAT-074.
    - Others omit direct dependents (for example FEAT-014 omits FEAT-029, 030, 034, 036).

  The forward dependencies are correct and identical everywhere, so build order is not affected.
- **Recommendation:** Add "All FEAT-NNN acceptance criteria pass" to the 22 DoDs. Regenerate the "builds directly on" lines from BACKLOG §4, or drop them.

## 5. Method

Scripted checks ran with `python3 -I`; the scripts were kept in the session scratchpad, not in the repository:

- **ID index:** regenerated from the current TRDs. It takes the first-cell table IDs of 26 prefixes (2,012 active, 2 retired) and checks that cited IDs exist across all backlog documents.
- **Coverage:** range-aware (`A..B`, en dash) coverage per prefix.
- **Metadata:** epic, phase, priority, complexity, MVP status and dependencies compared across the feature headers, BACKLOG §4, BACKLOG §5 and the roadmap phase tables.
- **Dependencies:** checked for phase order.
- **FR → FEAT:** three-way comparison of BACKLOG §11, BACKLOG §5 and the feature files.
- **Tables:** DDL table extraction, with every table reference resolved against it.
- **Endpoints:** every endpoint reference normalised and resolved against the TRD 19 E-index.
- **Paths:** test and report paths, relative links.
- **Hygiene:** placeholder and empty-section scans.
- **Numbers:** key-value consistency greps (tiles, tallies, funnel, config values).
- **UI:** UX range → feature mapping for each row of TRD 11 §4.16, and component names from TRD 04 §4.8 against the features.

Wireframe text was extracted from the five `*.dc.html` files and compared with TRD 11 §4.3–§4.18. Every finding was then read in context at the cited lines.
