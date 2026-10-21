# Checkpoint 1 Report — Phase 7 Generate Design Docs

PR #3 "Implement Features" (branch `feat/implement-features`) · Checkpoint 1 of 9 · Prompt: `specs/prompts/Implement_Feature_Batches.md` "Phase 7: Generate Design Docs" (including "UI Design Requirements") · TRD 25 Phase 2 · Feature: FEAT-001 · Date: 21 October 2026 · Status: ready for review by the algorithm lead (AGT-012, AGT-013). Nothing was committed.

## 1. What was produced

| File | Size (bytes) | Content |
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

Total 255,125 bytes, 2,977 lines, 97 Markdown tables, 30 Mermaid diagrams. Only these nine files (and this report) were created; no TRD, backlog file, code or configuration was changed.

Requirement IDs elaborated (AGT-022): ARC-001..ARC-105 (TRD 01), API-001..API-137 (TRD 05), OAS-001..OAS-028 (TRD 19), PGS-001..PGS-044 (TRD 20), DB-001..DB-066 (TRD 06), DME-001..DME-025 (TRD 23), ANL-001..ANL-065 (TRD 07), BSC, CUS, ING stage rules (TRD 08–10), FE-001..FE-205 (TRD 04), UX-001..UX-384 (TRD 11), TST, E2E, VC (TRD 13–14), DEP, CIC, GIT, ENV, SEC (TRD 15, 16, 18, 21, 12), AGT-001..AGT-062 (TRD 25); FEAT-001 FR-01..FR-11. Each document cites between 117 and 281 distinct IDs. Tests added: none (documents only, TRD 25 Phase 2). New OQ or D IDs: none (see Q-9).

## 2. Exit criteria and how each was verified

All checks were run with `python3 -I` (script kept in the session scratchpad, not in the repository) plus the shell commands below; final run: 29 of 29 checks passed.

| # | Exit criterion (roadmap §5.1, TRD 25 Phase 2, FEAT-001) | Verification | Result |
|---|---|---|---|
| C01 | Exactly the nine files under `docs/design/` (FEAT-001-AC-01) | `ls docs/design` compared with the expected list | PASS |
| C02 | No placeholders (FEAT-001-AC-06) | `grep -rnE "T[B]D\|T[O]DO" docs/design` and `grep -rnE "T[B]D\|T[O]DO\|\[placeholder\]" docs/design` | PASS, both exit 1 (no match) |
| C03 | No broken Markdown tables | every table outside code fences has a separator row, equal unescaped column count on every row and a trailing pipe | PASS (97 tables) |
| C04 | Mermaid blocks syntactically plausible | valid diagram keyword, balanced brackets and quotes, `subgraph`/`end` and `alt`/`loop`/`end` balance, every `erDiagram` line matches the entity or relationship grammar | PASS (30 blocks) |
| C04b | Mermaid blocks really parse | `mermaid.parse()` of mermaid 10.9.1 under jsdom on every block (this found semicolons in sequence messages, which were fixed) | PASS, 30 ok, 0 failed |
| C05 | Mermaid diagrams for ERD, request flow, pipeline stages, page hierarchy, repository dependencies (FEAT-001-AC-05) plus the prompt's UI diagrams | presence of `erDiagram` (Database_ERD), one-check-in `sequenceDiagram` with `POST /api/v1/sessions` (Backend §7), stage `flowchart` (Analytics §4), page hierarchy `flowchart` (UI §2, Frontend §4.2), dependency `flowchart` (Repository_Structure §8), topology and `gitGraph` (Deployment), `stateDiagram-v2` and data-flow `sequenceDiagram` (UI §4–§5) | PASS |
| C06 | Every TRD 19 endpoint E-01..E-32 maps to a router file and a service (FEAT-001-AC-02) | 32 endpoints parsed from TRD 19; each has exactly one row in OpenAPI_Spec §5 with a router from the TRD 05 §4.1 list, a service module and FEAT IDs; router and service compared with TRD 05 §4.12 row by row; Backend_Architecture §8 covers all 32 | PASS (E-01 is inline in `health.py` per TRD 05 §4.12, see Q-1) |
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
| C20 | No file outside `docs/design/` changed (FEAT-001-AC-07) | `find` for files newer than the session start, excluding `.git` | PASS (only the nine design files and this report) |

Additional command: `grep -rniE "openai|anthropic|langchain|llama|gpt" docs/design` returns one line, the AGT-004 inspection command quoted in Repository_Structure §9.

## 3. Deviations, conflicts and notes

| # | Note | Handling |
|---|---|---|
| N-1 | Prompt endpoint list without `/api/v1` and with `{id}` vs TRD 05/19 (DSC-11) | TRD 19 used (AGT-001); mapping of the shorthand in OpenAPI_Spec §1 |
| N-2 | The prompt's "Create" list names eight files; the UI part adds `UI_Architecture.md` | nine files, as TRD 25 Phase 2 and FEAT-001-FR-01 require |
| N-3 | Wireframes differ from the TRDs (SRC-09 "Devices" nav link and "[Facility name]", row order, SRC-11 "days", SRC-10 staff review and chart caption, SRC-18 sub-line) | TRDs followed; differences listed in UI_Architecture §1.1 |
| N-4 | TRD 01 §4.6 lists routers `data_alerts`, `notes`, `facility`; TRD 05 §4.1 places them in `alarms.py`, `residents.py`, `admissions.py` | TRD 05 followed (also TRD 25 Phase 5); Q-7 |
| N-5 | FEAT-015 and FEAT-020 name `backend/services/audit.py` and `auth.py`; TRD 05 §4.1 and TRD 12 §8 name `audit_service.py` and `auth_service.py` | TRD names used; Q-3 |
| N-6 | Repository module names are not fixed by any TRD | names proposed in Database_ERD §5, flagged; Q-5 |
| N-7 | FEAT-001-FR-12 and AGT-009 ask to add OQ rows to TRD 24 for unsettled points, but this checkpoint may change only `docs/design/` (plus this report) | no TRD 24 row added; the points are listed as Q-1..Q-10 below |
| N-8 | `BACKLOG.md` completion tracking is refreshed at the end of each checkpoint (TRD 25 Phase 12, D-95) | not done in this checkpoint because only `docs/design/` may change; see Q-9 |
| N-9 | `specs/backlog/` exists, so AGT-031 did not apply | BACKLOG.md §4, §6, §9 and FEAT-001 used |

## 4. Questions for the reviewer

| ID | Question | Where |
|---|---|---|
| Q-1 | E-01 `GET /health` is inline in `health.py` with no service function (TRD 05 §4.12), while FEAT-001-AC-02 asks for a service module per endpoint and API-003 asks every handler to call one service function. Keep inline, or add a health service function? | OpenAPI_Spec §5, §11 |
| Q-2 | `config_service.py` serves E-32 (TRD 05 §4.12) and loads `PipelineConfig` (FEAT-040) but is missing from the TRD 05 §4.1 service list. Add it to TRD 05 §4.1? | OpenAPI_Spec §11 |
| Q-3 | Service file names `auth_service.py`/`audit_service.py` (TRD 05, TRD 12) vs `auth.py`/`audit.py` (FEAT-020, FEAT-015, roadmap §5.3). Which name should the backlog use? | Backend_Architecture §9 |
| Q-4 | ANL-007 (`scripts/run_engine.py`) and PGS-017 (`scripts/dump_schema.sh`) need a root `scripts/` directory that the TRD 18 §4.1 and TRD 01 §4.6 layouts do not list (GIT-002). Add `scripts/` to the layouts? | Repository_Structure §2, §10 |
| Q-5 | Accept the proposed repository module names (Database_ERD §5)? | Database_ERD §5 |
| Q-6 | UX-127 (latest-review line on Resident detail) needs reviewer name and outcome, which only E-28 returns; TRD 04 §4.6.2 and §4.16 list no E-28 call on that page (FEAT-071 does). Add E-28 to the TRD 04 tables? | UI_Architecture §7.5, Frontend_Architecture §4.1 |
| Q-7 | Align the TRD 01 §4.6 router list with TRD 05 §4.1? | Backend_Architecture §4 |
| Q-8 | API-005 makes repositories the only query builders, while TRD 23 §4.6, API-136 and FEAT-012 forbid a repository for `evaluation_ground_truth` on the main engine and let `analytics_summary.py` read it through its own read-only engine. Confirm that this read is the one sanctioned exception. | Database_ERD §5 |
| Q-9 | Should the open points above be added to TRD 24 as OQ rows (AGT-009, FEAT-001-FR-12) and the `BACKLOG.md` completion status for FEAT-001 be updated (D-95) in a follow-up commit of this checkpoint, given the instruction to change only `docs/design/`? | — |
| Q-10 | API-001 and API-103 require uvicorn `--proxy-headers --forwarded-allow-ips="*"` on Railway, but the DEP-040 start command and the DEP-022 image command omit it. Which command is binding for Phase 9? | Backend_Architecture §3 |

## 5. Next step

After approval, Checkpoint 2 (Implement_Feature_Batches.md Phase 8, TRD 25 Phase 3, FEAT-002..FEAT-007) builds the skeleton from `docs/design/` (TRD 25 §4.6 Phase 3 Inputs).
