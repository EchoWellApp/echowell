# FEAT-001 Technical design documents

| Field | Value |
|---|---|
| Epic | Infrastructure |
| Build phase | Phase 2 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | None |
| Status | Not Started |

## Purpose

Produce the nine design documents under `docs/design/` that translate the TRDs into a concrete build plan for the later phases: every endpoint mapped to a router and service, every table mapped to the module that writes and reads it, every page mapped to its endpoints, and Mermaid diagrams of the ERD, request flow, pipeline stages and page hierarchy. The documents remove guesswork for the agents that implement Phases 3–11 and give reviewers one place to check the planned structure against the TRDs before any code is written.

## Business Context

- BR-17 (monorepo with Next.js, FastAPI, PostgreSQL and GitHub Actions): the documents fix the module layout of TRD 01 §4.6 for every later phase.
- BR-15 (reproduce the R01–R10 answer key): Analytics_Architecture.md and Testing_Architecture.md lay out the stage order and the validation tiers that the answer key is checked against.
- BR-12, BR-13, BR-14: UI_Architecture.md and Frontend_Architecture.md map the five wireframes (SRC-09, SRC-10, SRC-11, SRC-18, SRC-19) to routes and endpoints.
- BR-16: Backend_Architecture.md and Deployment_Architecture.md record the authentication, role and TLS boundaries (ARC-004..ARC-008).

## Referenced TRDs

- TRD 25 §4.6 Phase 2 (outputs, definition of done, commands, pitfalls), §4.4 (reading order for design documents), AGT-001, AGT-009, AGT-030.
- TRD 01 ARC-001..ARC-008 (system context and boundaries), ARC-040..ARC-046 (pipeline single entry point, purity, determinism, frozen baselines, natural keys, float64), §4.6 module decomposition.
- TRD 04 FE-020 and §4.3 route table.
- TRD 19 §4.3 endpoint index E-01..E-32.
- TRD 20 §4.6 tables (4.6.1–4.6.24), §4.7 indexes.
- TRD 18 GIT-054, GIT-055 (docs content and Mermaid diagrams).
- TRD 24 D-23 (exactly seven routes), OQ-18 (no EWMA chart).
- Source wireframes SRC-09, SRC-10, SRC-11, SRC-18, SRC-19 under `specs/UI-wireframe/`.

## Scope

- Create these files, and only these, under `docs/design/` (TRD 25 §4.6 Phase 2 outputs): `OpenAPI_Spec.md`, `Database_ERD.md`, `Backend_Architecture.md`, `Frontend_Architecture.md`, `Analytics_Architecture.md`, `Testing_Architecture.md`, `Deployment_Architecture.md`, `Repository_Structure.md`, `UI_Architecture.md`.
- Mermaid diagrams for: the ERD (all 24 tables of TRD 20 §4.6), the request flow of one check-in (TRD 01 §4.3), the pipeline stage sequence (TRD 01 §4.5, ARC-040), the page hierarchy (TRD 04 §4.3), and the repository dependency diagram inside `Repository_Structure.md`.
- Mapping tables: endpoint E-01..E-32 → router file under `backend/api/` → service under `backend/services/`; table → writing module and reading module (API repository or analytics stage); route → endpoints consumed.
- Cross-references to the TRD requirement IDs each section elaborates (GIT-054).

## Out of Scope

- Any code, configuration, migration or test (Phase 3 onward; FEAT-002 and later).
- Changes to any TRD (TRDs are the source of truth, AGT-001; questions go to TRD 24 under AGT-009).
- An EWMA chart or any page beyond the seven routes of D-23 (OQ-18 deferred; FEAT-096 is the Future research item).
- The backlog artefacts under `specs/backlog/` (Phase 12).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-001-FR-01 | The nine documents listed in Scope shall exist under `docs/design/` with exactly those file names. | TRD 25 §4.6 Phase 2 Outputs |
| FEAT-001-FR-02 | `OpenAPI_Spec.md` and `Backend_Architecture.md` shall map every endpoint E-01..E-32 to one router file under `backend/api/` (keeping the skeleton names, so `/api/v1/alerts`, reviews, snooze and data-alerts are served by `backend/api/alarms.py`) and one service module under `backend/services/`. | TRD 19 §4.3; TRD 25 §4.6 Phase 2 DoD; D-24; ARC-050 |
| FEAT-001-FR-03 | `Database_ERD.md` shall show every table of TRD 20 §4.6 (facilities through evaluation_ground_truth) in a Mermaid `erDiagram` with primary and foreign keys, and a table that names, for each table, the API repository or analytics module that writes it and the ones that read it. | TRD 20 §4.6; TRD 25 §4.6 Phase 2 DoD |
| FEAT-001-FR-04 | `Frontend_Architecture.md` and `UI_Architecture.md` shall map each of the routes `/login`, `/residents` (with the `#devices` panel), `/residents/[residentCode]`, `/admissions`, `/alerts`, `/analytics`, `/admin` to the endpoints it calls, and shall contain no other page. | FE-020; D-23; TRD 25 §4.6 Phase 2 Pitfalls |
| FEAT-001-FR-05 | `Analytics_Architecture.md` shall show the stage order of TRD 01 §4.5 with `analytics.pipeline.run_pipeline` as the single entry point and data-alert generation last, and shall state the purity, float64 and determinism rules. | ARC-040, ARC-041, ARC-042, ARC-046 |
| FEAT-001-FR-06 | `Analytics_Architecture.md` shall describe frozen-baseline reuse, the `late_arrival` warning and the natural keys used for idempotent upserts, including preservation of human-entered data on rebuild. | ARC-043, ARC-044, ARC-045 |
| FEAT-001-FR-07 | `Backend_Architecture.md` and `Deployment_Architecture.md` shall show the system boundary (ingest API only), the no-audio rule, the authentication methods (API key scopes `ingest:write`, `pipeline:run`; JWT for users), TLS on every hop including the database, encryption at rest, and the synthetic-data-only rule for the interim stack. | ARC-001..ARC-008 |
| FEAT-001-FR-08 | `Repository_Structure.md` shall reproduce the monorepo layout of TRD 01 §4.6 and include a Mermaid dependency diagram with the direction `api → services → repositories → models` and `analytics/` importing nothing from `backend/`. | TRD 01 §4.6; ARC-041; ARC-051 |
| FEAT-001-FR-09 | `Testing_Architecture.md` shall describe the test pyramid and directories of TRD 13 (unit, integration, validation Tier A and Tier B, contract, security, E2E) and name where the R01–R10 cases run. | TRD 13 §4; TRD 25 §4.4 |
| FEAT-001-FR-10 | Every section of every document shall cite the TRD requirement IDs it elaborates, shall not contradict a TRD, and shall contain no "T[B]D" or "T[O]DO" text. | GIT-054; TRD 25 §4.6 Phase 2 DoD and Commands |
| FEAT-001-FR-11 | Diagrams shall be Mermaid inside Markdown; no binary diagram file is added without a Mermaid or text equivalent. | GIT-055 |
| FEAT-001-FR-12 | Where the TRDs do not settle a design question, the author shall not decide it in the design documents but shall add an OQ row to TRD 24 and report it. | AGT-009 |

## Inputs

- `specs/TRD/` 00–25, read in the TRD 25 §4.4 "Design documents" order: 01, 02, 06, 20, 23, 05, 19, 07, 08, 09, 10, 04, 11, 13, 15, 16, 21, 22.
- Wireframes SRC-09 (Main), SRC-10 (Resident), SRC-11 (Admission), SRC-18 (Alerts), SRC-19 (Analytics) under `specs/UI-wireframe/`.
- `specs/backlog/BACKLOG.md` when present (TRD 25 §4.6 Phase 2 Inputs).

## Outputs

- Nine Markdown files under `docs/design/` (FEAT-001-FR-01).
- A Phase 2 batch report listing requirement IDs elaborated, commands run and any new OQ/D IDs (AGT-022).

## Data Flow

TRDs and wireframes → author reads them in the §4.4 order → mapping tables (endpoint → router → service; table → writer/reader; route → endpoints) and Mermaid diagrams are written into `docs/design/` → `grep` hygiene command run → reviewer checks the mappings against TRD 19 §4.3, TRD 20 §4.6 and TRD 04 §4.3 → merged as the Phase 2 PR. Later phases read `docs/design/` as an input (TRD 25 §4.6 Phase 3 Inputs).

## Dependencies

Required before implementation (BACKLOG.md): None

This is the first feature of the build sequence (TRD 25 §4.5, Phase 2 follows the Phase 1 TRD validation, which is complete per `docs/reports/TRD_VALIDATION_REPORT.md`). FEAT-002 depends on it.

## Database Impact

None. The feature documents the tables of TRD 20 §4.6 in `Database_ERD.md` but creates, alters or reads no table.

## API Impact

None. No endpoint is exposed or consumed; `OpenAPI_Spec.md` documents the planned endpoints E-01..E-32 of TRD 19 §4.3.

## Frontend Impact

None in code. `Frontend_Architecture.md` and `UI_Architecture.md` describe the seven routes of D-23 and the component hierarchy that FEAT-062..FEAT-075 implement.

## Analytics Impact

None in code. `Analytics_Architecture.md` describes the stage sequence (ARC-040) implemented later by FEAT-040..FEAT-052; no algorithm is computed.

## Security Requirements

- The documents shall contain no secret, connection string, real resident data or staff names (GIT-073, GIT-080, AGT-017); residents appear only as study IDs (R01..R10).
- The documents shall record the authentication and authorization boundaries of ARC-004 and the role names of AGT-062 without changing them.

## Error Handling

- A TRD contradiction or gap found while writing is not resolved in `docs/design/`; the author adds an OQ row to TRD 24 and stops the unsettled part (AGT-009).
- If the hygiene grep returns a match, the document is corrected before the PR is opened (TRD 25 §4.6 Phase 2 Commands).

## Logging Requirements

None at runtime. The batch report records commands run and their results (AGT-022). No audit records are generated.

## Testing Requirements

- Required tests: none (TRD 25 §4.6 Phase 2 "Required tests: None").
- Inspection commands: `grep -rnE "T[B]D|T[O]DO" docs/design` must return nothing (TRD 25 §4.6 Phase 2 Commands).
- Review checks: each E-01..E-32 row appears in the endpoint mapping table; each TRD 20 §4.6 table appears in the ERD and the writer/reader table; each D-23 route appears in the route mapping and no other route does.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-001-AC-01 | `ls docs/design` lists exactly the nine file names of FEAT-001-FR-01. | TRD 25 §4.6 Phase 2 Outputs |
| FEAT-001-AC-02 | The endpoint mapping table contains 32 rows, one per E-01..E-32, each naming an existing-or-planned file under `backend/api/` and a module under `backend/services/`. | TRD 25 §4.6 Phase 2 DoD |
| FEAT-001-AC-03 | Every table name listed under TRD 20 §4.6 appears in the Mermaid `erDiagram` of `Database_ERD.md` and in its writer/reader table. | TRD 25 §4.6 Phase 2 DoD |
| FEAT-001-AC-04 | The route mapping lists exactly `/login`, `/residents`, `/residents/[residentCode]`, `/admissions`, `/alerts`, `/analytics`, `/admin`, each with at least one endpoint ID, and no EWMA component is mentioned as planned. | FE-020; D-23; OQ-18 |
| FEAT-001-AC-05 | Mermaid diagrams exist for the ERD, the request flow, the pipeline stages and the page hierarchy, and `Repository_Structure.md` contains the repository dependency diagram. | TRD 25 §4.6 Phase 2 Outputs and DoD |
| FEAT-001-AC-06 | `grep -rnE "T[B]D|T[O]DO" docs/design` exits with status 1 (no match). | TRD 25 §4.6 Phase 2 Commands |
| FEAT-001-AC-07 | No file outside `docs/design/` (and the batch report) is changed by the PR, and no TRD file is modified. | AGT-001; TRD 25 §4.6 Phase 2 |

## Definition of Done

- All FEAT-001 acceptance criteria pass.
- Every document cites TRD IDs and contradicts none (GIT-054); any open question is registered in TRD 24 (AGT-009).
- Batch report written listing IDs elaborated, commands and results (AGT-022); PR reviewed and approved by the algorithm lead (AGT-013) before Phase 3 starts (AGT-030).

## Implementation Notes

- Read TRD 25, TRD 00 and TRD 24 first, then the §4.4 design-documents order.
- Keep the skeleton file names in the mappings (D-24, AGT-010): `backend/api/alarms.py` serves `/api/v1/alerts`; `backend/models/alarm.py` holds the Alert model.
- Residents are addressed by `resident_code` in URLs, not UUIDs (TRD 25 §4.6 Phase 5 Pitfalls, DSC-11); show this in the endpoint tables.
- The `run_pipeline` binding signature is in TRD 01 §8 and TRD 07 §4.5; copy it rather than paraphrase it.
- Cite tables and endpoints by their exact TRD names so later features (FEAT-008..FEAT-038) can be checked against the documents with simple text searches.
