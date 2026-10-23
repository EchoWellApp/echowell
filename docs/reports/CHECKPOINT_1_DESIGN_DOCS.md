# Checkpoint 1 Report — Phase 7 Generate Design Docs

Block 3 "Implement Features", checkpoint 1 of 9, its own PR: GitHub PR #3 (branch `feat/implement-features`) · Prompt: `specs/prompts/Implement_Feature_Batches.md` "Phase 7: Generate Design Docs" (including "UI Design Requirements") · TRD 25 Phase 2 · Feature: FEAT-001 · Date: 21 October 2026, revised 23 October 2026 · Status: review round 1 (changes requested by the repository owner and algorithm lead) applied, section 5; ready for re-review and merge to `main` (AGT-012, AGT-013, D-101). Nothing was committed.

## 1. What was produced

| File | Size (bytes, as delivered on 21 Oct 2026) | Content |
|---|---|---|
| `docs/design/OpenAPI_Spec.md` | 55,059 | conventions; endpoint catalogue E-01..E-32 and all component schemas generated mechanically from the TRD 19 §4.5 YAML; endpoint → router → service → tables → FEAT map; behaviour notes; error catalogue; enum mapping; contract tests |
| `docs/design/Database_ERD.md` | 33,501 | layers; Mermaid `erDiagram` of all 24 TRD 20 tables with PK/FK/UK; writer and reader (API service + analytics module) per table; repository modules; enums; state machine; rebuild and natural keys; indexes; roles and grants; migrations and seeds |
| `docs/design/Backend_Architecture.md` | 26,146 | system context and trust boundaries (no audio, TLS, auth methods, synthetic-only interim); processes; package layout; layering diagram; request lifecycle; request flow of one check-in; router map; service catalogue; triggers and locks; security controls; startup guards; CLI; budgets |
| `docs/design/Frontend_Architecture.md` | 18,561 | stack; layout; the seven routes with route → endpoint map; page hierarchy; rendering and auth; API client; state management and invalidation; shared libraries; states; env vars; build and test |
| `docs/design/Analytics_Architecture.md` | 27,843 | purity and determinism rules; module table with binding signatures; 12-stage pipeline diagram; `run_pipeline` signature (verbatim) and algorithm; data contracts; stage rules with pitfall guards; profiles; frozen baselines, late arrivals and human-data preservation; persistence sequence; expected test values; warnings; extension points |
| `docs/design/Testing_Architecture.md` | 16,721 | pyramid; tooling; directory layout; system part → test level map; R01–R10 two-tier validation; E2E groups; coverage and CI gates; data sets; commands per phase |
| `docs/design/Deployment_Architecture.md` | 20,346 | owner decisions (D-OWNER-1..4) and D-99/D-100; topology; branching and release sequence; deployable units; local stack; workflows; configuration and secrets; security boundaries; migrations and seeding; smoke, rollback, backups; AWS target |
| `docs/design/Repository_Structure.md` | 13,567 | monorepo tree; backend, analytics, frontend trees with skeleton files marked; kept skeleton files; repository dependency diagram with enforcement rules; naming rules |
| `docs/design/UI_Architecture.md` | 43,381 | wireframe vs TRD differences; page hierarchy and navigation; component hierarchy; state management; read and write data flows (staff review workflow); screen designs for Residents overview, Resident detail, New admissions (tables, filters, sorting, device panel, CUSUM visualisation, alert indicators, baseline status displays, staff review); other pages; component → API → database mapping for all 42 components of TRD 04 §4.8 |

Total 255,125 bytes, 2,977 lines, 97 Markdown tables, 30 Mermaid diagrams. The Phase 7 prompt run created only these nine files (and this report) and changed no TRD, backlog file, code or configuration; review round 1 then changed TRDs, backlog files, two prompt files and TRD 24 as the reviewer asked (section 5).

Requirement IDs elaborated (AGT-022): ARC-001..ARC-105 (TRD 01), API-001..API-137 (TRD 05), OAS-001..OAS-028 (TRD 19), PGS-001..PGS-044 (TRD 20), DB-001..DB-066 (TRD 06), DME-001..DME-025 (TRD 23), ANL-001..ANL-065 (TRD 07), BSC, CUS, ING stage rules (TRD 08–10), FE-001..FE-205 (TRD 04), UX-001..UX-384 (TRD 11), TST, E2E, VC (TRD 13–14), DEP, CIC, GIT, ENV, SEC (TRD 15, 16, 18, 21, 12), AGT-001..AGT-062 (TRD 25); FEAT-001 FR-01..FR-11. Each document cites between 117 and 281 distinct IDs. Tests added: none (documents only, TRD 25 Phase 2). New OQ or D IDs: none in the prompt run; review round 1 added D-101 and D-102 and no OQ (section 5).

## 2. Exit criteria and how each was verified

All checks were run with `python3 -I` (script kept in the session scratchpad, not in the repository) plus the shell commands below; final run of the prompt deliverable: 29 of 29 checks passed; re-run after review round 1 in section 5.3.

| # | Exit criterion (roadmap §5.1, TRD 25 Phase 2, FEAT-001) | Verification | Result |
|---|---|---|---|
| C01 | Exactly the nine files under `docs/design/` (FEAT-001-AC-01) | `ls docs/design` compared with the expected list | PASS |
| C02 | No placeholders (FEAT-001-AC-06) | `grep -rnE "T[B]D\|T[O]DO" docs/design` and `grep -rnE "T[B]D\|T[O]DO\|\[placeholder\]" docs/design` | PASS, both exit 1 (no match) |
| C03 | No broken Markdown tables | every table outside code fences has a separator row, equal unescaped column count on every row and a trailing pipe | PASS (97 tables) |
| C04 | Mermaid blocks syntactically plausible | valid diagram keyword, balanced brackets and quotes, `subgraph`/`end` and `alt`/`loop`/`end` balance, every `erDiagram` line matches the entity or relationship grammar | PASS (30 blocks) |
| C04b | Mermaid blocks really parse | `mermaid.parse()` of mermaid 10.9.1 under jsdom on every block (this found semicolons in sequence messages, which were fixed) | PASS, 30 ok, 0 failed |
| C05 | Mermaid diagrams for ERD, request flow, pipeline stages, page hierarchy, repository dependencies (FEAT-001-AC-05) plus the prompt's UI diagrams | presence of `erDiagram` (Database_ERD), one-check-in `sequenceDiagram` with `POST /api/v1/sessions` (Backend §7), stage `flowchart` (Analytics §4), page hierarchy `flowchart` (UI §2, Frontend §4.2), dependency `flowchart` (Repository_Structure §8), topology and `gitGraph` (Deployment), `stateDiagram-v2` and data-flow `sequenceDiagram` (UI §4–§5) | PASS |
| C06 | Every TRD 19 endpoint E-01..E-32 maps to a router file and a service (FEAT-001-AC-02) | 32 endpoints parsed from TRD 19; each has exactly one row in OpenAPI_Spec §5 with a router from the TRD 05 §4.1 list, a service module and FEAT IDs; router and service compared with TRD 05 §4.12 row by row; Backend_Architecture §8 covers all 32 | PASS (after review round 1, E-01 calls `health_service.get_health`, Q-1) |
| C07 | Every TRD 20 table maps to an API or analytics module and is in the ERD (FEAT-001-AC-03) | 24 table names parsed from TRD 20 §4.6; all are `erDiagram` entities; each ownership row names a writer and at least one endpoint or analytics module; every `REFERENCES` column of the TRD 20 DDL is drawn as an FK attribute and a relationship | PASS |
| C08 | Every TRD 04 page maps to endpoints; pages exactly the D-23 seven (FEAT-001-AC-04) | route → endpoint table in Frontend_Architecture §4.1 has exactly `/login`, `/residents`, `/residents/[residentCode]`, `/admissions`, `/alerts`, `/analytics`, `/admin`, each with ≥ 2 endpoint IDs; no other `app/(protected)/` directory or page path appears | PASS |
| C09 | Every UI component maps to APIs and DB entities (UI_Architecture) | all 42 components of TRD 04 §4.8 found in UI_Architecture §10 with endpoint IDs (or "none" for static components) and database tables | PASS |
| C10 | UI prompt topics covered | page hierarchy, navigation, component hierarchy, state management, data flow, three screen designs, tables, filters, sorting, device panel, CUSUM visualisation, alert indicators, baseline status, staff review workflow | PASS |
| C11 | Every cited ID exists | every ID-shaped token in the nine documents looked up in the TRD ID index (`idx.json`) or by exact search in `specs/TRD/`; FEAT IDs in `BACKLOG.md` §4 | PASS (local review labels `Q-n` and `OAS-An` excluded by design) |
| C12 | TRD and FEAT IDs cross-referenced in each document | count of three-digit TRD IDs and FEAT IDs per document | PASS (67–232 TRD IDs, 4–36 FEAT IDs per document) |
| C13 | No EWMA chart (OQ-18) | every EWMA mention states it is deferred or not built | PASS (8 mentions, all negative) |
| C14 | Deployment_Architecture describes D-99 and D-OWNER decisions | presence of "no `staging` branch", staging from `main` on every merge, manual `deploy-production.yml` with required reviewer, D-OWNER-3 (AWS target), D-OWNER-4 (interim Netlify/Railway/Neon, synthetic data only) | PASS |
| C15–C16 | No LLM and no audio anywhere | every mention of LLM-related terms and of "audio" (other than `audio_quality_flag`) is a prohibition | PASS |
| C17–C18 | Wording rules | "diagnosis"/"severity" only in negative or rule statements; "Edge4Care" only in prohibitions | PASS |
| C19 | Endpoint list uses `/api/v1` (TRD 19 supersedes the prompt list) | all 32 catalogue paths start with `/api/v1/` | PASS |
| C20 | No file outside `docs/design/` changed (FEAT-001-AC-07) | `find` for files newer than the session start, excluding `.git` | PASS for the prompt run (only the nine design files and this report); expected to fail after review round 1, which corrected TRDs and backlog files in this PR at the reviewer's request (Q-9) |

Additional command: `grep -rniE "openai|anthropic|langchain|llama|gpt" docs/design` returns one line, the AGT-004 inspection command quoted in Repository_Structure §9.

## 3. Deviations, conflicts and notes

| # | Note | Handling |
|---|---|---|
| N-1 | Prompt endpoint list without `/api/v1` and with `{id}` vs TRD 05/19 (DSC-11) | TRD 19 used (AGT-001); mapping of the shorthand in OpenAPI_Spec §1 |
| N-2 | The prompt's "Create" list names eight files; the UI part adds `UI_Architecture.md` | nine files, as TRD 25 Phase 2 and FEAT-001-FR-01 require |
| N-3 | Wireframes differ from the TRDs (SRC-09 "Devices" nav link and "[Facility name]", row order, SRC-11 "days", SRC-10 staff review and chart caption, SRC-18 sub-line) | TRDs followed; differences listed in UI_Architecture §1.1 |
| N-4 | TRD 01 §4.6 lists routers `data_alerts`, `notes`, `facility`; TRD 05 §4.1 places them in `alarms.py`, `residents.py`, `admissions.py` | TRD 05 followed (also TRD 25 Phase 5); resolved (Q-7): TRD 01 §4.6 aligned with TRD 05 §4.1 |
| N-5 | FEAT-015 and FEAT-020 name `backend/services/audit.py` and `auth.py`; TRD 05 §4.1 and TRD 12 §8 name `audit_service.py` and `auth_service.py` | TRD names used; resolved (Q-3): FEAT-015, FEAT-020 and the roadmap now use `audit_service.py` and `auth_service.py` |
| N-6 | Repository module names are not fixed by any TRD | resolved (Q-5): the Database_ERD §5 names are authoritative and referenced from TRD 05 and TRD 01 |
| N-7 | FEAT-001-FR-12 and AGT-009 ask to add OQ rows to TRD 24 for unsettled points, but this checkpoint may change only `docs/design/` (plus this report) | resolved (Q-9): the reviewer allowed corrections outside `docs/design/` in this PR; every point was answered, so no OQ row was needed; the decisions are TRD 24 D-101 and D-102 (section 5) |
| N-8 | `BACKLOG.md` completion tracking is refreshed at the end of each checkpoint (TRD 25 Phase 12, D-95) | resolved (Q-9): `BACKLOG.md` §10 refreshed in review round 1 (FEAT-001 In Progress until GitHub PR #3 is merged) |
| N-9 | `specs/backlog/` exists, so AGT-031 did not apply | BACKLOG.md §4, §6, §9 and FEAT-001 used |

## 4. Questions for the reviewer (all resolved in review round 1)

| ID | Question (as raised on 21 Oct 2026) | Where | Status |
|---|---|---|---|
| Q-1 | E-01 `GET /health` is inline in `health.py` with no service function (TRD 05 §4.12), while FEAT-001-AC-02 asks for a service module per endpoint and API-003 asks every handler to call one service function. Keep inline, or add a health service function? | OpenAPI_Spec §5, §11 | Resolved (section 5) |
| Q-2 | `config_service.py` serves E-32 (TRD 05 §4.12) and loads `PipelineConfig` (FEAT-040) but is missing from the TRD 05 §4.1 service list. Add it to TRD 05 §4.1? | OpenAPI_Spec §11 | Resolved (section 5) |
| Q-3 | Service file names `auth_service.py`/`audit_service.py` (TRD 05, TRD 12) vs `auth.py`/`audit.py` (FEAT-020, FEAT-015, roadmap §5.3). Which name should the backlog use? | Backend_Architecture §9 | Resolved (section 5) |
| Q-4 | ANL-007 (`scripts/run_engine.py`) and PGS-017 (`scripts/dump_schema.sh`) need a root `scripts/` directory that the TRD 18 §4.1 and TRD 01 §4.6 layouts do not list (GIT-002). Add `scripts/` to the layouts? | Repository_Structure §2, §10 | Resolved (section 5) |
| Q-5 | Accept the proposed repository module names (Database_ERD §5)? | Database_ERD §5 | Resolved (section 5) |
| Q-6 | UX-127 (latest-review line on Resident detail) needs reviewer name and outcome, which only E-28 returns; TRD 04 §4.6.2 and §4.16 list no E-28 call on that page (FEAT-071 does). Add E-28 to the TRD 04 tables? | UI_Architecture §7.5, Frontend_Architecture §4.1 | Resolved (section 5) |
| Q-7 | Align the TRD 01 §4.6 router list with TRD 05 §4.1? | Backend_Architecture §4 | Resolved (section 5) |
| Q-8 | API-005 makes repositories the only query builders, while TRD 23 §4.6, API-136 and FEAT-012 forbid a repository for `evaluation_ground_truth` on the main engine and let `analytics_summary.py` read it through its own read-only engine. Confirm that this read is the one sanctioned exception. | Database_ERD §5 | Resolved (section 5) |
| Q-9 | Should the open points above be added to TRD 24 as OQ rows (AGT-009, FEAT-001-FR-12) and the `BACKLOG.md` completion status for FEAT-001 be updated (D-95) in a follow-up commit of this checkpoint, given the instruction to change only `docs/design/`? | — | Resolved (section 5) |
| Q-10 | API-001 and API-103 require uvicorn `--proxy-headers --forwarded-allow-ips="*"` on Railway, but the DEP-040 start command and the DEP-022 image command omit it. Which command is binding for Phase 9? | Backend_Architecture §3 | Resolved (section 5) |

## 5. Review round 1 resolutions (23 October 2026)

The repository owner and algorithm lead (Shaba) requested changes on GitHub PR #3 on 23 Oct 2026. Every answer below has been applied in this checkpoint's PR; the Phase 7 design documents, the TRDs, the backlog and TRD 24 now agree. Nothing was committed.

### 5.1 Process change (D-101, amends D-100)

- The Instructions document (SRC-20) now names its five units "Block 1" to "Block 5" instead of "PR #1" to "PR #5": Block 1 TRD generation (merged as GitHub PR #1), Block 2 feature backlog (merged as GitHub PR #2), Block 3 implement features, Block 4 deployment, Block 5 test cases.
- Each of the nine Block 3 checkpoints (`Implement_Feature_Batches.md` Phases 7, 8, 9, 10, 11, 12, 13, 14A, 15) is a separate pull request into `main`, on its own feature branch created from the latest `main`. The next checkpoint prompt is not run until the previous checkpoint's PR is approved and merged to `main`. This checkpoint is GitHub PR #3 on `feat/implement-features` (kept, because renaming the branch would close the PR); the branches suggested for checkpoints 2–9 are `feat/cp2-project-skeleton`, `feat/cp3-database`, `feat/cp4-backend-api`, `feat/cp5-analytics-engine`, `feat/cp6-validation`, `feat/cp7-frontend`, `feat/cp8-deployment-config` and `feat/cp9-final-audit` (`specs/backlog/IMPLEMENTATION_ROADMAP.md` §2.1). Blocks 4 and 5 stay one PR each, after the checkpoint 9 PR is merged.
- `BACKLOG.md` §10 is refreshed at the end of each checkpoint PR (D-95 and RAQ-015 reworded). Process references to "PR #1".."PR #5" that meant the Instructions-document units now read "Block 1".."Block 5" in `specs/TRD/`, `specs/backlog/`, `specs/prompts/` (titles and process sentences only) and `docs/design/`; references to actual GitHub pull requests (for example "PR #2 review, comment 1", change-log rows) are kept. Older reports in `docs/reports/` are a historical record and were not changed.
- Files: TRD 24 (D-100 amended, D-101 added, D-95, RAQ-015, SRC-17, SRC-20, §2), TRD 25 (§1, SRC-17, SRC-20, AGT-012, AGT-013, AGT-030, AGT-033, §4.5 diagram and workflow, phase headings, Phase 11 and 12 definitions of done, §6, AC-AGT-01, AC-AGT-04), TRD 18 (§3, branch table, §4.2 diagram, GIT-010, GIT-012, GIT-014, GIT-020, GIT-030, GIT-031, GIT-034, PR template, AC-GIT-01, §8), TRD 13 (TST-170), TRD 14 (TDV-073), TRD 16 (CIC-101), `IMPLEMENTATION_ROADMAP.md` (v0.4: §2.1 block and branch tables, §2.2 per-checkpoint PR flow, §2.3 rules, §3–§9), `BACKLOG.md` (v0.5: §2, §6, §9, §10, §11.1, §12), `DEPLOYMENT_CHECKLIST.md` (v0.3), `MVP_READINESS_CHECKLIST.md` (v0.4), FEAT-001, FEAT-002, FEAT-006..FEAT-025, FEAT-031, FEAT-048, FEAT-059, FEAT-060, FEAT-078, FEAT-080, FEAT-087, FEAT-088, FEAT-090, FEAT-091 (checkpoint wording), `specs/prompts/Implementation_Audit_Checklist.md` and `TRD_Implementation_Audit_Checklist.md` (titles and process sentences), `docs/design/Deployment_Architecture.md` (§1, §2, §4 diagram and rules), the headers of all nine design documents.

### 5.2 Answers to Q-1..Q-10

| ID | Reviewer answer | Resolution | Files changed |
|---|---|---|---|
| Q-1 | Add the health service function, even if it only returns `{"status":"ok"}`. | E-01 handler in `health.py` calls `health_service.get_health()` (`backend/services/health_service.py`), which runs the `SELECT 1` probe and builds `Health` (API-003, API-110, API-111). | TRD 05 §4.1, §4.12 (v0.12); TRD 01 §4.6; FEAT-003; `BACKLOG.md` FEAT-003 row; OpenAPI_Spec §5, §11; Backend_Architecture §8, §9; Repository_Structure §3 |
| Q-2 | Yes, add `config_service.py` to the TRD 05 §4.1 service list. | Added. | TRD 05 §4.1; TRD 01 §4.6; OpenAPI_Spec §11 |
| Q-3 | Standardize on `auth_service.py` and `audit_service.py`. | All backlog references use these names; routers `backend/api/auth.py` and schemas `backend/schemas/auth.py` are unchanged (different layers). | FEAT-015, FEAT-020, `IMPLEMENTATION_ROADMAP.md` §5.3, TRD 01 §4.6; Backend_Architecture §9 |
| Q-4 | Yes, add `scripts/` to the layout. | Root `scripts/` (`run_engine.py`, ANL-007; `dump_schema.sh`, PGS-017) added to both layouts (GIT-002). | TRD 18 §4.1 (v0.13); TRD 01 §4.6 (v0.8); Repository_Structure §2, §4, §10 |
| Q-5 | Yes, adopt the Database_ERD §5 repository module names as the authoritative convention. | "Proposal" wording removed; TRD 05 §4.1, API-005 and TRD 01 §4.6 point to Database_ERD §5; no conflicting module name existed in the TRDs; backlog references made explicit. | Database_ERD §5; TRD 05 §4.1, API-005; TRD 01 §4.6; FEAT-015 (`audit_repository.py`), FEAT-026 (`ingest_repository.py`); Backend_Architecture §4; Repository_Structure §3 |
| Q-6 | The UI wireframes are the source of truth; if the Resident Detail wireframe does not show reviewer name and outcome, no change is needed. | `specs/UI-wireframe/Resident.dc.html` shows "Staff review", the note field and "Mark as reviewed" but no "Reviewed by" line, so E-28 is not added to TRD 04 §4.6.2 or §4.16. D-102 records that Resident detail follows the wireframe; UX-127 is withdrawn from Resident detail. Reviewer and outcome stay visible on `/alerts` in "Previous reviews" (TRD 11 UX-320, E-28, FEAT-070); `Alerts.dc.html` itself shows the review form and the "Not reviewed" card status, and UX-320 defines the list. | TRD 24 D-102; TRD 11 UX-127, §9 (v0.12); FEAT-071 (purpose, references, FR-10, inputs, API impact, tests); UI_Architecture §1.1, §7.5, §10; Frontend_Architecture §4.1 |
| Q-7 | The API TRD is the source of truth for router organisation; both documents must define the same router structure. | TRD 01 §4.6 router list now equals TRD 05 §4.1: `/data-alerts` in `alarms`, notes in `residents`, `/facility/reference-ranges` in `admissions`, plus `config` and `deps`. | TRD 01 §4.6; Backend_Architecture §4 |
| Q-8 | Yes: `evaluation_ground_truth` is a test-only table with its own read-only connection; `analytics_summary.py` may read it directly; document this as the one exception to the repository rule. | API-005 names the exception; TRD 23 §4.6 and Database_ERD §5 state it; Backend_Architecture §5 and Repository_Structure §8 rules mention it. | TRD 05 API-005; TRD 23 §4.6 (v0.9); Database_ERD §5; Backend_Architecture §5; Repository_Structure §8 |
| Q-9 | Update every artefact affected by the resolutions; the `docs/design/` constraint must not prevent correcting traceability or completion status; only genuinely unresolved items go to TRD 24 as OQs. | All affected TRDs, backlog files and design documents updated (this table). `BACKLOG.md` §10: FEAT-001 In Progress (delivered in GitHub PR #3, Complete when it is merged). No item is left unresolved, so no OQ row was added (OQ-30 stays free); the decisions are D-101 and D-102. FEAT-001-AC-07 now allows review corrections in the checkpoint PR. | `BACKLOG.md` §10; FEAT-001; TRD 24; this report |
| Q-10 | Standardize on the uvicorn command with `--proxy-headers --forwarded-allow-ips="*"`; update DEP-022 and DEP-040. | Railway start command `uvicorn backend.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"`; the image default command carries the same flags; the local Compose command keeps the socket peer. | TRD 15 DEP-022, DEP-040, §4.5 step 2 and `railway.toml` outline (v0.12); TRD 05 API-001, API-103; FEAT-003, FEAT-022, FEAT-077, FEAT-081; `DEPLOYMENT_CHECKLIST.md` C.03; Backend_Architecture §3; Deployment_Architecture §5 |

Each changed TRD has a new version and a 23 Oct 2026 change-log row citing the PR #3 review: TRD 01 0.8, 05 0.12, 11 0.12, 13 0.12, 14 0.10, 15 0.12, 16 0.12, 18 0.13, 23 0.9, 24 0.14, 25 0.14.

### 5.3 Verification after review round 1

| Check | Result |
|---|---|
| Design-document checks C01–C19 (including C04b `mermaid.parse` of all 30 blocks) | 28 of 29 pass; C20 ("no file outside `docs/design/` changed") now fails by design, because the reviewer asked for the corrections above in this PR (Q-9) |
| Backlog consistency script (features, dependencies, FR coverage, cited IDs, mermaid edges, placeholders) | PASS |
| Feature-file checks FEAT-001..FEAT-097 (meta block, headings, FR/AC numbering, cited IDs against a TRD ID index rebuilt from the current TRDs) | 0 errors |
| `mermaid.parse` of the edited diagrams in TRD 18, TRD 25, `IMPLEMENTATION_ROADMAP.md`, `BACKLOG.md` | 0 failed |
| Markdown tables of every changed file | equal column counts, trailing pipes |
| grep: process "PR #3 checkpoint", "checkpoint of PR #3", "PR plan" in `specs/` and `docs/design/` | none left outside D-100 (marked amended) and historical change-log rows |
| grep: `services/auth.py`, `services/audit.py` | none |
| D-101, D-102 cited in specs and design documents | both defined in TRD 24 §4.6 |

## 6. Next step

After GitHub PR #3 is approved and merged to `main`, Checkpoint 2 (Implement_Feature_Batches.md Phase 8, TRD 25 Phase 3, FEAT-002..FEAT-007) starts on a new branch `feat/cp2-project-skeleton` created from the updated `main` and is delivered as its own PR; it builds the skeleton from `docs/design/` (TRD 25 §4.6 Phase 3 Inputs). The Phase 8 prompt is not run before that merge (D-101).