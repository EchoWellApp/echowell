# EchoWell Documentation Completeness Audit (post-implementation run)

Document: docs/reports/DOCUMENTATION_COMPLETENESS_AUDIT.md · Date: 8 November 2026 · Commit audited: `23e558b` (branch `feat/cp9-final-audit`, equal to `main`; build checkpoints 1–8 merged) · Prompt: `specs/prompts/Generate_Documentation_Audit_Prompt.md` · Feature: FEAT-091 (TRD 25 §4.6 Phase 11, Block 3 checkpoint 9) · Auditor: independent agent (did not write the audited documents) · Location per TRD 25 AGT-032 / TRD 24 D-21

This file replaces the pre-implementation run of 20 October 2026 (branch `backlog-generation`, findings DA-01..DA-12), as TRD 25 §4.6 Phase 11 requires. Section 5 lists the earlier findings and their current status.

Scope:

- `specs/TRD/` (26 TRDs, 00–25);
- `specs/backlog/` (`BACKLOG.md`, 97 files in `features/`, `IMPLEMENTATION_ROADMAP.md`, `DEPLOYMENT_CHECKLIST.md`, `MVP_READINESS_CHECKLIST.md`);
- `docs/` (`design/` 9 files, `deployment.md`, `api_reference.md`, `api_reference/openapi.json`, `team_workflow.md`, the three other top-level files, `reports/`).

Where a check calls for it, the documentation was compared with the implementation:

- `backend/alembic/versions/` and `backend/api/`;
- `docs/api_reference/openapi.json`;
- `.github/workflows/`, `render.yaml`;
- test markers: `req("ID", ...)` in `tests/` and `// req: ID` in `frontend/`.

This is a findings-only audit. No audited file was changed. No test suite, container, migration or database was run. All counts come from read-only scripts (section 6).

The frontend verification items and the wireframe → feature → component → API → test matrix that the prompt also asks for are written to `docs/reports/UI_REQUIREMENTS_TRACEABILITY_MATRIX.md`, as FEAT-091 Scope and TRD 25 Phase 11 Outputs require. They are not repeated here.

## 1. Summary

**Verdict: FAIL.** 0 Critical, 1 Major, 13 Minor findings (DCA-01 to DCA-14).

The specification set is complete and consistent, and it matches the build where the two can be compared mechanically:

- every BR maps to TRDs;
- 2,025 of 2,026 active TRD requirement IDs are cited by a feature or by BACKLOG;
- all 97 features are in the roadmap with identical status in BACKLOG §10 and in the feature headers;
- all 24 TRD 20 tables exist in the migrations with the same columns;
- the 32 TRD 19 endpoints equal the 32 operations of `openapi.json` and the 32 routes in `backend/api/`;
- the config seed in the migration is TRD 20 §4.11 verbatim;
- every relative link resolves.

The one Major finding is check 7. The required link from acceptance criteria and Must requirements to tests is not in place:

- `python3 tests/trace_report.py` reports 378 Must requirements with no test marker and no inspection entry;
- the inspection register `docs/reports/traceability_inspections.md` named by TST-013 does not exist;
- 140 of 281 TRD acceptance criteria have no linked test.

The tests may well exist (the suites are extensive), but the trace that TST-013, NFR-111 and the Phase 11 definition of done require cannot be shown from the repository.

### 1.1 Pass/fail matrix (prompt items 1–10)

| # | Check | Result | Evidence | Issues | Recommendation |
|---|---|---|---|---|---|
| 1 | Every business requirement maps to a TRD | **PASS WITH FINDINGS** | BR-01..BR-18 (TRD 00 §4.6, `00_Project_Vision_and_Scope.md:181–200`) each name primary TRDs. Each BR is cited by 9–25 TRDs and 3–54 feature files (section 2.1). TRD 02 §4.28 maps every BR to FRs. | TRD 02 §4.28 still lists 10 retired FRs (DCA-06). | Remove or mark the retired FR IDs in TRD 02 §4.28. |
| 2 | Every TRD requirement maps to a feature | **PASS WITH FINDINGS** | 2,068 first-cell requirement IDs over 27 prefixes: 42 retired, 2,026 active. 2,025 active IDs (99.95 %) are cited by a feature file or a BACKLOG row (section 2.2). | API-139 (added at checkpoint 4, D-126) is cited by no feature (DCA-04). FE-026 is marked retired yet holds an active Must requirement (DCA-07). | Add API-139 to FEAT-019 or FEAT-025. Restate the status of FE-026. |
| 3 | Every feature maps to implementation tasks | **PASS WITH FINDINGS** | 97/97 features appear in the roadmap feature tables (106 rows; 9 features appear twice, 8 of them in the Phase 7 authentication gate). Status in the 97 feature headers equals BACKLOG §10 (87 Complete, 10 Not Started; 0 differences). 97/97 Definitions of Done contain "All FEAT-NNN acceptance criteria pass". The "Features that build directly on this one" lines equal the reverse of the Dependencies fields (0 differences). | Roadmap §2.1 and BACKLOG §10 still describe checkpoint 8 as in review, although PR #31 is merged at `23e558b` (DCA-12). | Refresh both in the checkpoint 9 PR (D-104). |
| 4 | Every database table is defined | **PASS WITH FINDINGS** | 24 `CREATE TABLE` in TRD 20 §4.6 and 24 in `backend/alembic/versions/0001_initial_schema.py`; same names (diff empty). Column lists agree table by table. The one difference, `data_alerts.days`, is migration 0004 (TRD 20 §4.14). Migration 0003 (`ingest_batches.pipeline_run_id`) is TRD 20 §4.13 verbatim. TRD 23 and `docs/design/Database_ERD.md` (v0.4) carry both added columns. | TRD 20 §4.6 shows `days` inline but omits `pipeline_run_id` (DCA-08). | Annotate `pipeline_run_id` in the §4.6 DDL the same way as `days`. |
| 5 | Every API endpoint is defined | **PASS WITH FINDINGS** | TRD 19 §4.3 lists E-01..E-32. `docs/api_reference/openapi.json` (OpenAPI 3.1.0) has the same 32 method + path pairs (diff empty). The `@router` decorators in `backend/api/*.py` with their router prefixes give the same 32 (section 2.4). Every other method + path reference in TRDs, backlog and `docs/` resolves to one of them, apart from deliberate negative cases (an audio route, a separate review-confirmation route under `/alerts/{id}`, `DELETE /users/{id}`), which the TRDs say must not exist, the framework routes and the Render deploy API. | FEAT-068-FR-08 names a non-existent path `GET /checkins` (DCA-09). | Use E-10 `GET /residents/{resident_code}/checkins`. |
| 6 | Every algorithm requirement is defined | **PASS** | ANL 65/65, BSC 43/43 and CUS 48/48 active IDs are cited by features (CUS-037 retired). The 46-row config seed in migration 0002 (23 keys × 2 profiles) is line-for-line identical to TRD 20 §4.11 (24 `('key', …)` value lines compared). FEAT-001-FR-05 now states data alerts as stage 11 and aggregates as stage 12, last, as ARC-040 and ANL-006 do. | — | — |
| 7 | Every acceptance criterion has associated tests | **FAIL** | See section 2.5. TRD ACs: 281 (+ AC-DB-02a). 90 have a direct marker, 33 a marked feature AC that realises them, 18 a marked test ID named in their text; **140 have none**. Feature ACs: 686; 375 have a direct `FEAT-NNN-AC-NN` marker; 450 are linked directly or through a marked test ID; 82 declare Inspection, Review, Demo or Analysis. 147 ACs of Complete features have no link. MVP-01..MVP-15 have no markers. Must IDs (TST-013 scope): 1,006; 347 unmarked after range expansion (`tests/trace_report.py` prints 378). `docs/reports/traceability_inspections.md` does not exist. | DCA-01 (Major), DCA-02, DCA-03, DCA-05. | Create the inspection register. Add markers. Make CI publish the trace report. Fix the range handling of the script. |
| 8 | Every deployment step is documented | **PASS** | `DEPLOYMENT_CHECKLIST.md` §A–§O covers Neon, Render (web service and cron job, D-153), Netlify, GitHub environments, staging and production release, verification, rollback, backups and restore, monitoring, demo fallback, sign-off, the AWS target and an AC index. The secrets and variables named in §E.01–§E.03 equal the `secrets.*` and `vars.*` used in `.github/workflows/*.yml` (7 secrets, 7 variables). The `render.yaml` cron schedule `0 7,8 * * *` matches TRD 15 DEP-047. `docs/deployment.md` (297 lines) and `docs/reports/DEPLOYMENT_CONFIGURATION_GUIDE.md` give the operator steps. Every remaining "Railway" mention in specs and docs is historical (amended-by notes, revision history). | — (the steps are unchecked because Block 4 has not started, as planned). | — |
| 9 | No conflicting requirements exist | **PASS WITH FINDINGS** | All 159 relative Markdown links in `specs/`, `docs/` and `README.md` resolve. No test marker cites a TRD ID or AC that does not exist (apart from range artefacts). The component names of TRD 04 §4.8 (45) all exist in `frontend/`. | DCA-06, DCA-07, DCA-08, DCA-10, DCA-13, DCA-14 (all Minor). | See the findings. |
| 10 | No placeholder sections remain | **PASS WITH FINDINGS** | No TBD, TODO, FIXME or lorem in TRDs, backlog or `docs/`; the only hits are quotations of earlier checks in `docs/reports/*_FIXES.md`. No empty Markdown section in any audited file. | `docs/architecture.md`, `docs/algorithm.md` and `docs/database_design.md` are empty (0 bytes) (DCA-11). | Fill them, or point them to `docs/design/`, or remove them from the TRD 01, TRD 18 and Repository_Structure trees. |

### 1.2 Findings count

| Severity | Count | IDs |
|---|---|---|
| Critical | 0 | — |
| Major | 1 | DCA-01 |
| Minor | 13 | DCA-02 … DCA-14 |

Severities follow `specs/prompts/TRD_Implementation_Audit_Checklist.md` Step 1:

- **Critical:** would cause a wrong or unsafe build.
- **Major:** an implementer following the TRDs would very likely build something that fails its own required tests or contradicts the source documents.
- **Minor:** a genuine inconsistency that a careful implementer would resolve without harm.

The verdict rule is the same: FAIL with any Critical or Major finding.

## 2. Coverage tables

### 2.1 Business requirements → TRDs and features (item 1)

| BR | Primary TRDs (TRD 00 §4.6) | TRDs citing it | Feature files citing it |
|---|---|---|---|
| BR-01 | 05, 10, 19 | 21 | 22 |
| BR-02 | 01, 06, 20 | 19 | 14 |
| BR-03 | 07, 10 | 15 | 15 |
| BR-04 | 07, 10 | 11 | 6 |
| BR-05 | 07, 08 | 9 | 8 |
| BR-06 | 07, 11 | 17 | 18 |
| BR-07 | 07, 08 | 11 | 3 |
| BR-08 | 07, 08 | 13 | 12 |
| BR-09 | 08 | 17 | 14 |
| BR-10 | 08 | 9 | 5 |
| BR-11 | 09 | 16 | 25 |
| BR-12 | 04, 11 | 18 | 21 |
| BR-13 | 04, 11 | 16 | 29 |
| BR-14 | 02, 04, 06, 11 | 11 | 9 |
| BR-15 | 13, 14 | 23 | 54 |
| BR-16 | 12, 17 | 25 | 53 |
| BR-17 | 01, 15, 16, 18, 21, 22 | 15 | 20 |
| BR-18 | all | 18 | 11 |

### 2.2 TRD requirement IDs → features, and test markers (items 2 and 7)

"Cited" means that a feature file or BACKLOG cites the ID directly or through a range (`A..B`, `A–B`). "Marker" means that a `req(...)` call in `tests/` or a `// req:` line in `frontend/` cites the ID, with ranges expanded.

| Prefix | TRD | Active | Retired | Cited | Not cited | With test marker |
|---|---|---|---|---|---|---|
| BR | 00 | 18 | 0 | 18 | 0 | 3 |
| VIS | 00 | 30 | 0 | 30 | 0 | 1 |
| ARC | 01 | 76 | 0 | 76 | 0 | 5 |
| FR | 02 | 203 | 9 | 203 | 0 | 62 |
| NFR | 03 | 102 | 0 | 102 | 0 | 21 |
| FE | 04 | 144 | 4 | 144 | 0 | 103 |
| API | 05 | 122 | 0 | 121 | 1 (API-139) | 90 |
| DB | 06 | 63 | 0 | 63 | 0 | 35 |
| ANL | 07 | 65 | 0 | 65 | 0 | 41 |
| BSC | 08 | 43 | 0 | 43 | 0 | 35 |
| CUS | 09 | 48 | 1 | 48 | 0 | 26 |
| ING | 10 | 59 | 0 | 59 | 0 | 45 |
| UX | 11 | 247 | 28 | 247 | 0 | 217 |
| SEC | 12 | 121 | 0 | 121 | 0 | 60 |
| TST | 13 | 121 | 0 | 121 | 0 | 70 |
| TDV | 14 | 72 | 0 | 72 | 0 | 58 |
| DEP | 15 | 83 | 0 | 83 | 0 | 30 |
| CIC | 16 | 59 | 0 | 59 | 0 | 1 |
| LOG | 17 | 62 | 0 | 62 | 0 | 30 |
| GIT | 18 | 63 | 0 | 63 | 0 | 5 |
| OAS | 19 | 27 | 0 | 27 | 0 | 21 |
| PGS | 20 | 44 | 0 | 44 | 0 | 35 |
| ENV | 21 | 29 | 0 | 29 | 0 | 21 |
| TPS | 22 | 30 | 0 | 30 | 0 | 10 |
| DME | 23 | 25 | 0 | 25 | 0 | 10 |
| RAQ | 24 | 18 | 0 | 18 | 0 | 0 |
| AGT | 25 | 52 | 0 | 52 | 0 | 25 |
| **Total** | | **2,026** | **42** | **2,025** | **1** | **1,060** |

Only the Must rows of TRDs 02, 04, 05 and 07–12 must carry a marker (TST-013). Other TRDs are verified by inspection, analysis or CI, so a low marker count there (for example CIC, GIT, RAQ) is not a finding in itself.

### 2.3 Must requirements without a test marker (TST-013 scope)

| TRD | Must IDs | Without marker (ranges expanded) |
|---|---|---|
| 02 | 200 | 139 |
| 04 | 138 | 38 |
| 05 | 119 | 31 |
| 07 | 59 | 19 |
| 08 | 41 | 6 |
| 09 | 48 | 22 |
| 10 | 59 | 14 |
| 11 | 236 | 25 |
| 12 | 106 | 53 |
| **Total** | **1,006** | **347** (the script `tests/trace_report.py` prints 378, because it does not expand ranges; DCA-03) |

### 2.4 Tables and endpoints (items 4 and 5)

| Source | Tables | Endpoints |
|---|---|---|
| TRD 20 §4.6 / TRD 19 §4.3 | 24 | 32 (E-01..E-32) |
| `backend/alembic/versions/` (0001 creates all 24; 0002 seed; 0003 and 0004 add one column each) / `docs/api_reference/openapi.json` | 24 | 32 |
| `backend/api/*.py` (decorators with router prefix; 13 routers mounted under `/api/v1` in `backend/main.py:105–117`) | — | 32 |
| Differences | 0 table names; 1 column, explained by migration 0004 | 0 |

### 2.5 Acceptance criteria → tests (item 7)

TRD acceptance criteria (281, from the §7 lists and tables of all 26 TRDs; AC-DB-02a is extra and also unlinked):

| AC prefix | Total | Direct marker | Via marked feature AC | Via marked test ID in the AC text | No link |
|---|---|---|---|---|---|
| AGT | 11 | 4 | 1 | 0 | 6 |
| ANL | 14 | 9 | 2 | 0 | 3 |
| API | 18 | 6 | 5 | 1 | 6 |
| ARC | 11 | 2 | 0 | 0 | 9 |
| BSC | 8 | 6 | 2 | 0 | 0 |
| CIC | 10 | 0 | 1 | 0 | 9 |
| CUS | 11 | 3 | 2 | 0 | 6 |
| DB | 10 | 2 | 0 | 1 | 7 |
| DEP | 11 | 1 | 2 | 0 | 8 |
| DME | 9 | 0 | 0 | 0 | 9 |
| ENV | 9 | 9 | 0 | 0 | 0 |
| FE | 11 | 3 | 0 | 4 | 4 |
| FR | 14 | 3 | 0 | 0 | 11 |
| GIT | 8 | 1 | 1 | 0 | 6 |
| ING | 11 | 9 | 0 | 0 | 2 |
| LOG | 10 | 3 | 2 | 0 | 5 |
| NFR | 12 | 0 | 0 | 3 | 9 |
| OAS | 7 | 4 | 1 | 2 | 0 |
| PGS | 15 | 15 | 0 | 0 | 0 |
| RAQ | 7 | 0 | 0 | 1 | 6 |
| SEC | 11 | 4 | 1 | 2 | 4 |
| TDV | 12 | 2 | 7 | 0 | 3 |
| TPS | 6 | 0 | 0 | 0 | 6 |
| TST | 13 | 1 | 2 | 3 | 7 |
| UX | 12 | 3 | 4 | 0 | 5 |
| VIS | 10 | 0 | 0 | 1 | 9 |
| **Total** | **281** | **90** | **33** | **18** | **140** |

Of the 140 unlinked TRD ACs, 33 are mentioned in some `docs/reports/` file (possible inspection evidence, not in the TST-013 register). The other 107 are cited nowhere outside `specs/`. Some depend on Block 4 and cannot have evidence yet: the AC-DEP and AC-TPS items and the staging-header part of AC-FE-07. Many are plainly testable on the current build, for example:

- AC-CUS-01 (98 tallies within 1e-6);
- AC-FR-02 (per-resident outcomes);
- AC-DB-06 (late record leaves baselines identical);
- AC-ANL-06 (incremental equals batch);
- AC-SEC-06 (API key revoke);
- AC-UX-02 (`?show=` filters);
- AC-TST-01.

Feature ACs: 686 in total.

- 446 carry a "Verified by" clause.
- 375 have a direct `FEAT-NNN-AC-NN` marker.
- 450 are linked directly or through a marked test ID.
- 82 declare Inspection, Review, Demo, Analysis or AWS.
- 174 have no link: 147 of them belong to Complete features (most in FEAT-003, FEAT-005, FEAT-052, FEAT-072 and FEAT-078) and 27 to Not Started features.

## 3. Findings

### DCA-01 — Major — Acceptance criteria and Must requirements lack the required test or inspection link (TST-013, NFR-111)

- **Location:**
  - `specs/TRD/13_Testing_Strategy_and_Acceptance_Criteria.md:136` (TST-013)
  - `specs/backlog/features/FEAT-091-Final-Implementation-TRD-Traceability-Documentation-And.md:56` (FEAT-091-FR-03)
  - `tests/trace_report.py`
  - `docs/team_workflow.md:9`
  - missing file `docs/reports/traceability_inspections.md`
- **Evidence:**
  - TST-013 (Must) requires every Must requirement of TRDs 02, 04, 05 and 07–12 to be cited by a test marker or listed with inspection evidence in `docs/reports/traceability_inspections.md`.
  - `python3 tests/trace_report.py` ends with "378 Must requirement(s) without a test or inspection entry". After range expansion, 347 of the 1,006 Must IDs remain unmarked. Examples: FR-001..FR-009, SEC-001..SEC-007, CUS-018..CUS-021, ANL-006 (stage order), API-139.
  - The register file does not exist (`ls docs/reports/traceability_inspections.md` gives "No such file or directory").
  - Of the 281 TRD ACs, 140 have no linked test (section 2.5). 147 ACs of Complete features have no link, and MVP-01..MVP-15 carry no marker.
  - The Phase 11 definition of done and FEAT-091-FR-03 require every acceptance criterion to have a linked test or documented inspection. This cannot be shown from the repository at `23e558b`, so the build contradicts a Must requirement of its own TRDs.
  - The test suites are large and many of these criteria are probably exercised under other IDs. The gap is the trace, not necessarily the testing.
- **Recommendation:**
  - Create `docs/reports/traceability_inspections.md` with one row per inspection-verified Must ID and AC (ID, method, evidence file and line).
  - Add `req(...)` / `// req:` markers for the testable IDs, starting with the 107 TRD ACs cited nowhere and the 139 unmarked FR Must rows.
  - Re-run `python3 tests/trace_report.py` until it prints 0 before the readiness decision. Record any remainder as FAIL in `TRD_Implementation_Audit.md`.

### DCA-02 — Minor — CI does not publish the trace report, and no feature owns the inspection register

- **Location:** `specs/TRD/13_Testing_Strategy_and_Acceptance_Criteria.md:136`, `.github/workflows/ci.yml`, `specs/TRD/16_CI_CD_Pipeline_Spec.md`, `specs/backlog/features/FEAT-005-Test-Infrastructure-And-Conventions.md:63`.
- **Evidence:**
  - TST-013 says that "CI shall publish the report".
  - `grep -rn "trace_report" .github` returns nothing, and TRD 16 has no step for it.
  - FEAT-005-FR-09 and FEAT-005-AC-08 cover only the script. FEAT-026 (`:206`) and FEAT-091 (`:78`) only refer to the register. No feature or roadmap task creates `traceability_inspections.md`, which is how DCA-01 could arise unnoticed through eight checkpoints.
- **Recommendation:** Add a `backend-test` step that runs `python tests/trace_report.py` and uploads its output (TRD 16 and FEAT-007). Assign creation of the register to FEAT-091 explicitly.

### DCA-03 — Minor — `tests/trace_report.py` ignores ID ranges and acceptance criteria

- **Location:** `tests/trace_report.py:15` (`ID = r"[A-Z]{2,4}-\d{3}"`) and `:36–38`.
- **Evidence:**
  - The frontend markers use ranges, for example `frontend/tests/pages/study.test.tsx:1` `UX-350..UX-384` and others with `UX-192..UX-195`.
  - The script reads only the end points, so it reports 31 more gaps than exist (378 against 347).
  - The ID pattern matches only three-digit requirement IDs. AC-* and MVP-* markers are never counted, although FEAT-091-FR-03 needs AC coverage.
- **Recommendation:** Expand `A..B` ranges, or forbid ranges in markers (TST-012). Add an AC and MVP section to the report.

### DCA-04 — Minor — API-139 is cited by no feature and carries no marker

- **Location:** `specs/TRD/05_Backend_API_TRD.md:354` (API-139, Must, added in v0.15, D-126).
- **Evidence:**
  - No feature file and no BACKLOG row cites API-139.
  - The behaviour (415 for any `audio/*` request, GET included) is exercised in `tests/integration/api/test_http_middleware.py:136` and `tests/integration/api/test_ingest.py:149`, but neither test carries the ID.
- **Recommendation:** Add API-139 to FEAT-019 (middleware) and to the marker of the middleware test.

### DCA-05 — Minor — Six TRD acceptance criteria are cited by no backlog artefact

- **Location:**
  - `specs/TRD/04_Frontend_TRD.md:784–786, 790, 792` (AC-FE-02, AC-FE-03, AC-FE-04, AC-FE-08, AC-FE-10)
  - `specs/TRD/06_Database_Design_TRD.md:633` (AC-DB-02a)
- **Evidence:** None of the 97 feature files, BACKLOG, the roadmap or the two checklists cites these IDs. The AC-FE rows were rewritten for wireframe v0.2 (`/residents`, the chart sections, review in the chart). AC-DB-02a (rebuild keeps review and snooze) is also unmarked in the tests.
- **Recommendation:** Cite AC-FE-02/03/04/10 from FEAT-065..FEAT-069, AC-FE-08 from FEAT-075 and AC-DB-02a from FEAT-053 or FEAT-031, and link each to its test.

### DCA-06 — Minor — Retired IDs are still cited as live trace targets

- **Location:**
  - `specs/TRD/02_Functional_Requirements_Specification.md:573, 575, 583, 585, 586, 588, 590` (§4.28 BR → FR)
  - `specs/backlog/BACKLOG.md:428–429` (FEAT-030 catalogue row)
- **Evidence:**
  - TRD 02 §4.28 lists FR-139, FR-195, FR-207, FR-260, FR-261, FR-265, FR-278 and FR-321 (10 citations in 7 rows). All were retired by D-110.
  - BACKLOG §5 lists FR-261 under "FRs covered" and CUS-037 under "Referenced TRDs" for FEAT-030, without the "(retired by D-110)" note that `FEAT-030…md:22` carries.
  - Every BR still maps to active FRs, so coverage is not affected.
- **Recommendation:** Drop the retired IDs from TRD 02 §4.28 and from the FEAT-030 row, or mark them "(retired)".

### DCA-07 — Minor — FE-026 is marked retired but holds an active Must requirement

- **Location:** `specs/TRD/04_Frontend_TRD.md:204`.
- **Evidence:**
  - The row begins "(Retired in contract §20 R2: the navigation has no "Devices" link.)" and then states a new Must requirement: `/study#devices` scrolls to the section and moves focus to it (D-110).
  - The requirement is implemented (`frontend/components/DevicesSection/DevicesSection.tsx:1`) and tested (`frontend/tests/pages/study.test.tsx:326`).
  - `tests/trace_report.py` treats the row as Must, while an index that honours the retired label drops it. UX-016, which the same rule retired, has no requirement text.
- **Recommendation:** Reword FE-026 as an active requirement ("Replaces the retired Devices link …"), or retire it and move the anchor rule to a new FE ID.

### DCA-08 — Minor — TRD 20 §4.6 annotates one later column but not the other

- **Location:**
  - `specs/TRD/20_PostgreSQL_Schema_Definition.md:368–387` (`ingest_batches`)
  - `specs/TRD/20_PostgreSQL_Schema_Definition.md:722` (`data_alerts.days`)
  - `specs/TRD/20_PostgreSQL_Schema_Definition.md:1163–1183` (§4.13, §4.14)
- **Evidence:** The `data_alerts` DDL in §4.6 includes `days date[] … -- added by migration 0004 (§4.14)`. The `ingest_batches` DDL omits `pipeline_run_id`, which migration 0003 adds (§4.13). A reader of §4.6 alone gets an incomplete `ingest_batches` table; TRD 23 (`:186`) and the ERD have the column.
- **Recommendation:** Add `pipeline_run_id … -- added by migration 0003 (§4.13)` to the §4.6 `ingest_batches` DDL.

### DCA-09 — Minor — FEAT-068 names a non-existent endpoint path

- **Location:** `specs/backlog/features/FEAT-068-Check-In-Log.md:56` (FEAT-068-FR-08).
- **Evidence:** "loads the previous 30 days through `GET /checkins?from=&to=`". The contract path is E-10 `GET /residents/{resident_code}/checkins` (TRD 19 `:718`, TRD 05 API-077, `openapi.json`). No `/checkins` route exists.
- **Recommendation:** Write the full E-10 path.

### DCA-10 — Minor — A design document cites a test file that does not exist

- **Location:** `docs/design/Repository_Structure.md:188`.
- **Evidence:** The rule "Only `backend/core/db.py` builds engines; only the migrator path reads `DATABASE_MIGRATION_URL`" names `tests/unit/backend/core/test_migration_url_boundary.py` as its enforcement. The file does not exist. API-125 is tested in `tests/unit/backend/core/test_db.py:38, 49`, and the migration URL in `tests/unit/backend/core/test_config.py`. GIT-054 requires `docs/` to agree with the TRDs and the build.
- **Recommendation:** Point the row to the existing tests.

### DCA-11 — Minor — Three top-level `docs/` files are empty

- **Location:** `docs/architecture.md`, `docs/algorithm.md`, `docs/database_design.md` (all 0 bytes).
- **Evidence:** TRD 01 (`01_System_Architecture_TRD.md:288`), TRD 18 (`18_GitHub_Repository_Standards.md:62`) and `docs/design/Repository_Structure.md:23` list these files in the repository tree. Their content exists in `docs/design/` (Backend, Frontend and Analytics Architecture, Database_ERD), but the files themselves are empty placeholders. `docs/api_reference.md` was filled in the same way.
- **Recommendation:** Give each file a short pointer page to the `docs/design/` documents, or remove them from the three trees.

### DCA-12 — Minor — Status tracking lags the merge of checkpoint 8

- **Location:**
  - `specs/backlog/IMPLEMENTATION_ROADMAP.md` §2.1 Block 3 status cell
  - `specs/backlog/BACKLOG.md` §10 first paragraph and Complete row
- **Evidence:**
  - The roadmap says "checkpoint 8 in review (GitHub PR #31)".
  - BACKLOG §10 starts "Status as of 2 November 2026" and says that checkpoint 8 "has delivered FEAT-077..FEAT-087 on branch `feat/cp8-deployment-config`".
  - `git log --merges --oneline main` shows `23e558b Merge pull request #31`.
  - D-104 places the refresh in the next PR, so this is expected at the start of checkpoint 9. It is recorded so that the checkpoint 9 PR does not leave it behind.
- **Recommendation:** In the checkpoint 9 PR, update both cells to "merged" with the date, and reconcile §10 with the audit results.

### DCA-13 — Minor — AC-AGT-01 does not account for merged PRs outside the checkpoint plan

- **Location:** `specs/TRD/25_AI_Agent_Build_Instructions.md:355` (AC-AGT-01).
- **Evidence:** AC-AGT-01 requires "no other build PR". The `main` history also holds:
  - PR #5 (wireframes v0.2, `docs/`);
  - PR #29 (OpenAPI server fix, recorded as D-140);
  - PR #30 (Render deployment docs, D-153..D-158);
  - Dependabot PRs #6–#26.

  Whether these count as "build PRs" is not defined, so the criterion can be read as failing. `MVP_READINESS_CHECKLIST.md:207` (L.01) does not have this clause.
- **Recommendation:** Define "build PR" in AC-AGT-01, or list the allowed kinds (`docs/` PRs, decision-recorded fixes, Dependabot updates).

### DCA-14 — Minor — The decision log skips D-152

- **Location:** `specs/TRD/24_Risk_Assumptions_and_Open_Questions.md` §4.6.
- **Evidence:** 169 D rows, D-01..D-170. A script over the row numbers finds one gap, D-151 → D-153. `grep -rn "D-152" specs docs` and `git log --all -S"D-152"` both return nothing, so no row was deleted and nothing cites it. The gap is harmless but unexplained, and a later reader may suspect a lost decision.
- **Recommendation:** Add a row "D-152 — not used" or a note in the revision history.

## 4. Observations (no finding)

- **Feature file names:** they no longer match some titles after wireframe v0.2 (for example `FEAT-070-Alarm-Review-Form-…md` now holds the Device section). This is deliberate: `IMPLEMENTATION_ROADMAP.md:515` and `docs/reports/WIREFRAMES_V0_2_UPDATE.md:24` keep IDs and file names.
- **`analytics/facility_norms.py`:** it is named in `docs/design/Analytics_Architecture.md:305` and `Database_ERD.md:386` but does not exist. Both documents call it planned (FEAT-095, gated on OQ-08), as ANL-057 does.
- **Forward references:** `DEPLOYMENT_CHECKLIST.md` refers to `docs/reports/DEPLOYMENT_REPORT.md` and `FINAL_IMPLEMENTATION_AUDIT.md`. These are outputs of Phases 10 and 11 that do not exist yet.

## 5. Previous run (20 October 2026, DA-01..DA-12)

| ID | Previous finding (all Minor) | Status | Evidence at `23e558b` |
|---|---|---|---|
| DA-01 | Ten testable TRD IDs cited by no feature (ARC-035, ARC-100..ARC-105, DME-018, FE-090, FE-091, TPS-040) | **Resolved** | Each is now cited by at least one feature file (for example ARC-100 by 2, FE-090 and FE-091 by 1). The section 2.2 index finds them all covered. |
| DA-02 | VIS, RAQ and process-only AGT IDs cited by no feature | **Resolved** | VIS 30/30, RAQ 18/18 and AGT 52/52 are cited by a feature or BACKLOG (section 2.2). |
| DA-03 | Acceptance criteria lack an explicit test link; 73 TRD ACs cited by no backlog artefact | **Partly resolved** | Uncited TRD ACs went from 73 to 6 (DCA-05), and 446 of 686 feature ACs now carry "Verified by". The AC → test link itself is still incomplete: DCA-01. |
| DA-04 | FEAT-001-FR-05 states the wrong final pipeline stage | **Resolved** | `FEAT-001…md:57`: "data alerts (stage 11) followed by analytics aggregates (stage 12, last; TRD 07 ANL-006)". |
| DA-05 | Same-date order of check-in log events not passed to the backend | **Resolved** | API-077 (`05_Backend_API_TRD.md:246`) fixes the same-date order. FEAT-028 cites UX-141 (`:34`), and FEAT-028-AC-10 (`:154`) adds a same-date fixture. |
| DA-06 | Required FEAT-080 depends on Optional FEAT-061 | **Resolved** | FEAT-080 Dependencies: FEAT-078, FEAT-076, FEAT-079. FEAT-061 stays Optional. |
| DA-07 | Stale D-01..D-74 range in BACKLOG inputs | **Resolved** | `BACKLOG.md:13` now says "every D-xx row of TRD 24 §4.6". |
| DA-08 | Stale "conflict" notes in feature files | **Resolved** | No "conflict(s) below" or "TRD conflict" text in any feature file. The FR-266 period note is gone from FEAT-069. |
| DA-09 | "One PR per phase, in order" contradicts the planned Phase 12 runs | **Resolved** | AC-AGT-01 reworded (TRD 25 revisions 0.12 and 0.14) and L.01 reworded (checklist revisions 0.2 and 0.4) for the Block 1–5 plan (D-100, D-101). A different gap in the same row is DCA-13. |
| DA-10 | New-admission progress worded as "days" while it counts check-ins | **Resolved** | UX-186 "<n> of <N>" and UX-192 "After <N> usable check-ins …" (`11_User_Interface_UX_Spec.md:425, 431`). FEAT-073-FR-04 and FR-10 (`:51, :57`) match. |
| DA-11 | TRD 25 Phase 5 router list omits `config.py` | **Resolved** | `25_AI_Agent_Build_Instructions.md:225` lists `config.py` (`GET /api/v1/config/ui`). |
| DA-12 | Inconsistent DoD clause and reverse-dependency lines | **Resolved** | 97/97 DoDs contain "All FEAT-NNN acceptance criteria pass". 0 differences between the "build directly on" lines and the reversed Dependencies fields. |

## 6. Method and commands

All commands ran read-only from `/home/user/echowell` at `23e558b`. The Python index scripts ran with `python3 -I` and were kept in the session scratchpad, outside the repository.

**Requirement index.**

- First-cell IDs of the TRD tables: pattern `^\|\s*(<P>-\d{3})\s*\|` per prefix in its own TRD, with `BR-\d{2}` in TRD 00.
- A row counts as retired when it contains "Retired".
- TRD ACs: pattern `^\s*(\|\s*|\d+\.\s*|-\s*)\**(AC-[A-Z]{2,4}-\d{2})\b` over all 26 TRDs.
- Coverage is range-aware (`A..B`, `A–B`, `A…B`) over the feature files and BACKLOG.

**Markers.**

- `req\(([^)]*)\)` in every `tests/**/*.py`, and `//\s*req:(.*)` in every `frontend/**/*.ts(x)` outside `node_modules`, with ranges expanded.
- A feature AC is linked when it has its own marker or names a marked ID.
- A TRD AC is linked when it has a marker, is realised (feature AC "Realises" column) by a linked feature AC, or names a marked test ID.

**Simple commands used for the checks and their results:**

| Command | Result |
|---|---|
| `python3 tests/trace_report.py \| tail -1` | `378 Must requirement(s) without a test or inspection entry` |
| `ls docs/reports/traceability_inspections.md` | No such file or directory |
| `grep -rn "trace_report" .github` | no output |
| `grep -oE "CREATE TABLE [a-z_]+" specs/TRD/20_PostgreSQL_Schema_Definition.md \| awk '{print $3}' \| sort -u \| wc -l` | 24 |
| `grep -ohE "CREATE TABLE [a-z_]+" backend/alembic/versions/*.py \| awk '{print $3}' \| sort -u \| wc -l` | 24 (diff with the TRD list: empty) |
| `grep -E "^\| E-[0-9]{2}" specs/TRD/19_API_Contracts_OpenAPI_Spec.md \| wc -l` | 32 |
| `python3 -c "import json;d=json.load(open('docs/api_reference/openapi.json'));print(sum(m in ('get','post','put','patch','delete') for p in d['paths'].values() for m in p))"` | 32 (method + path list equal to TRD 19) |
| Scan of `@router.<method>("…")` in `backend/api/*.py` joined with each `APIRouter(prefix=…)` | 32 (equal to TRD 19) |
| `grep -rnwE "TBD\|TODO\|FIXME\|lorem" specs/TRD specs/backlog docs --include=*.md` | hits only in quoted check results in `docs/reports/*_FIXES.md` and the previous version of this file |
| `find docs specs -name "*.md" -size 0` | `docs/architecture.md`, `docs/database_design.md`, `docs/algorithm.md` |
| `grep -c "^\| D-[0-9]" specs/TRD/24_Risk_Assumptions_and_Open_Questions.md` | 169 (last row D-170; gap at D-152) |
| `grep -ohE "secrets\.[A-Z_]+\|vars\.[A-Z_]+" .github/workflows/*.yml \| sort -u` | 7 secrets, 7 variables, equal to `DEPLOYMENT_CHECKLIST.md` §E |
| `git log --merges --oneline main` (read-only) | PR #31 merged at `23e558b`; PRs #5, #29 (via `61229e0`), #30 and Dependabot PRs present |

**Other scripted checks:**

- relative Markdown links: 159 checked, 0 broken;
- backtick repository paths in `docs/design/`, `docs/deployment.md`, `DEPLOYMENT_CHECKLIST.md` and the deployment guide checked for existence (DCA-10 and the observations);
- column-by-column comparison of the 24 `CREATE TABLE` bodies in TRD 20 and migration 0001;
- line comparison of the TRD 20 §4.11 seed with migration 0002;
- feature-header status against BACKLOG §10;
- roadmap feature rows;
- DoD clause;
- reverse dependencies;
- retired-ID citations;
- TRD 04 §4.8 component names against `frontend/`.

Every finding was read in context at the cited lines.

## Revision History

| Version | Date | Change |
|---|---|---|
| 1.0 | 20 Oct 2026 | Pre-implementation run on `backlog-generation` (DA-01..DA-12, PASS WITH FINDINGS). |
| 2.0 | 8 Nov 2026 | Post-implementation run (TRD 25 Phase 11, FEAT-091) at `23e558b`; replaces 1.0; DCA-01..DCA-14, FAIL (1 Major). |
