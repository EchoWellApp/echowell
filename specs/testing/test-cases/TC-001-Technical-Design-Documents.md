# FEAT-001 Technical design documents

## Feature Description

FEAT-001 delivers the nine Phase 2 design documents under `docs/design/` (TRD 25 §4.6 Phase 2). They map every endpoint E-01..E-32 of TRD 19 §4.3 to a router file under `backend/api/` and a service module under `backend/services/`, every table of TRD 20 §4.6 to its writer and readers, and every route of TRD 04 §4.3 (D-110) to the endpoints it calls. They contain Mermaid diagrams of the ERD, the request flow of one check-in, the pipeline stage order and the page hierarchy, plus the repository dependency diagram. The feature is documentation only: it adds no code, no table and no endpoint. All test cases are document inspections.

## Preconditions

- A clone of the repository on branch `main` (or the branch under test) with `docs/design/` present.
- A shell with `ls`, `grep`, `git` and, for TC-001-13, the GitHub CLI `gh` signed in with read access to the repository.
- Open in a viewer: TRD 19 §4.3 (endpoint index E-01..E-32), TRD 20 §4.6 (tables 4.6.1–4.6.24), TRD 04 §4.3 (route table), TRD 01 §4.5 and §4.6, TRD 13 §4.
- A Markdown viewer that renders Mermaid (for example the GitHub file view) for TC-001-05.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-001-01 | `docs/design` holds exactly the nine design documents | High | Documentation |
| TC-001-02 | Endpoint mapping table has 32 rows E-01..E-32 with router and service | High | Documentation |
| TC-001-03 | Every TRD 20 §4.6 table is in the `erDiagram` and in the writer/reader table | High | Documentation |
| TC-001-04 | Route mapping lists exactly the D-110 routes, each with an endpoint; no EWMA planned | High | Documentation |
| TC-001-05 | Mermaid diagrams exist for ERD, request flow, pipeline stages, page hierarchy and repository dependencies | High | Documentation |
| TC-001-06 | Hygiene grep for open placeholders returns no match | High | Documentation |
| TC-001-07 | Analytics_Architecture.md shows the stage order, single entry point and purity rules | Medium | Documentation |
| TC-001-08 | Analytics_Architecture.md describes frozen baselines, `late_arrival` and natural keys | Medium | Documentation |
| TC-001-09 | Backend and Deployment documents record the system boundary and security rules | Medium | Documentation |
| TC-001-10 | Repository_Structure.md shows the layout and the dependency direction | Medium | Documentation |
| TC-001-11 | Testing_Architecture.md describes the test pyramid and where R01–R10 run | Medium | Documentation |
| TC-001-12 | Every section cites TRD requirement IDs; diagrams are Mermaid, not binary files | Medium | Documentation |
| TC-001-13 | The Phase 2 PR changed only `docs/design/` and the batch report and no TRD | High | Documentation |
| TC-001-14 | Negative: documents contain no secret, connection string, real data or extra page | High | Negative |

### TC-001-01 `docs/design` holds exactly the nine design documents

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `ls docs/design` from the repository root. | Output lists exactly 9 entries: `Analytics_Architecture.md`, `Backend_Architecture.md`, `Database_ERD.md`, `Deployment_Architecture.md`, `Frontend_Architecture.md`, `OpenAPI_Spec.md`, `Repository_Structure.md`, `Testing_Architecture.md`, `UI_Architecture.md`. |
| 2 | Run `ls docs/design \| wc -l`. | Prints `9`. |
| 3 | Compare the names with FEAT-001-FR-01 (case-sensitive). | Every name matches character for character; no extra file (no image, no `.drawio`, no sub-folder). |

### TC-001-02 Endpoint mapping table has 32 rows E-01..E-32 with router and service

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `docs/design/OpenAPI_Spec.md` section "5. Endpoint → router → service → tables → features". | A table with the columns `ID`, `Method and path (/api/v1)`, `Roles / keys`, `Router file`, `Service function (module)`, `Tables read (R) / written (W)`, `Backlog features` is present. |
| 2 | Count the rows of that table whose first cell is `E-01` to `E-32`. | Exactly 32 rows, one per ID E-01..E-32, none missing and none repeated. |
| 3 | For each row, read the `Router file` and `Service function (module)` cells. | Each row names one file under `backend/api/` (for example `health.py` for E-01, `config.py` for E-32) and one module under `backend/services/` (for example `health_service.py` for E-01). |
| 4 | Find the rows for `GET /alerts`, the alert reviews, snooze and `GET /data-alerts`. | All of them name router file `alarms.py` (skeleton name kept, D-24). |
| 5 | Open `docs/design/Backend_Architecture.md` section "8. Endpoint → router → service map". | The section exists and maps endpoints to router and service modules consistently with step 3 (no endpoint mapped to a different router). |
| 6 | Check the path column for resident endpoints. | Residents are addressed by `{code}` / `resident_code` in paths, never by a UUID. |

### TC-001-03 Every TRD 20 §4.6 table is in the `erDiagram` and in the writer/reader table

| Step | Action | Expected Result |
|---|---|---|
| 1 | List the 24 table names of TRD 20 §4.6.1–§4.6.24: `facilities`, `users`, `residents`, `devices`, `device_assignments`, `api_keys`, `ingest_batches`, `ingest_rejections`, `raw_sessions`, `pipeline_runs`, `epochs`, `processed_sessions`, `day_ledger`, `baselines`, `scores`, `cusum_state`, `alerts`, `alert_reviews`, `data_alerts`, `staff_notes`, `facility_reference_ranges`, `config_parameters`, `audit_logs`, `evaluation_ground_truth`. | 24 names. |
| 2 | Open `docs/design/Database_ERD.md` section "3. Entity-relationship diagram (all 24 tables of TRD 20 §4.6)" and find the block starting with `erDiagram`. | One Mermaid `erDiagram` block is present. |
| 3 | For each of the 24 names, search the `erDiagram` block for an entity with that name. | All 24 entities are present; each shows its primary key (`PK`) and its foreign keys (`FK`). |
| 4 | Open section "4. Table ownership: writer and readers". | A table lists each of the 24 table names with the module(s) that write it and the module(s) that read it. |
| 5 | Confirm `evaluation_ground_truth` row. | Its readers do not include any `analytics/` module or the pipeline (D-38). |

### TC-001-04 Route mapping lists exactly the D-110 routes, each with an endpoint; no EWMA planned

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `docs/design/Frontend_Architecture.md` section "4.1 Route → endpoint map". | A table with columns `Route`, `Endpoints called`, `Client functions`, `When` is present. |
| 2 | Read the `Route` column. | Routes are exactly `/login`, `/residents`, `/residents/[residentCode]` (Summary) with the sections `…/review`, `…/trends`, `…/baseline`, `…/log`, `…/device`, plus `/admissions`, `/study`, `/admin` (and the shared "chart layout" row). No other page appears. |
| 3 | Read the `Endpoints called` cell of each route. | Each route lists at least one endpoint ID (for example `/login`: E-02 and E-04; `/study`: E-18, E-30, E-17, E-12, E-19). |
| 4 | Open `docs/design/UI_Architecture.md` section "2. Page hierarchy and navigation architecture" and the first paragraph of section 1. | The pages are the same set as step 2; the text states the v0.1 pages are not built (D-110). |
| 5 | Run `grep -rni "ewma" docs/design`. | Every match states that EWMA is deferred or not built (OQ-18, FEAT-096), for example "no EWMA is computed or displayed in the MVP" and "No EWMA chart anywhere"; no match lists an EWMA chart or component as planned. |

### TC-001-05 Mermaid diagrams exist for ERD, request flow, pipeline stages, page hierarchy and repository dependencies

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -n '```mermaid' docs/design/*.md`. | At least one match in each of the nine documents (diagrams are Mermaid inside Markdown, GIT-055). |
| 2 | Open `Database_ERD.md` §3. | The Mermaid block is an `erDiagram` (ERD). |
| 3 | Open `Backend_Architecture.md` section "7. Request flow of one check-in". | A Mermaid `sequenceDiagram` shows one check-in: device → `POST /api/v1/sessions (X-API-Key, JSON, no audio)` → `api/sessions.py` → `services/ingestion.py` → PostgreSQL → `services/pipeline_runner.py` → `analytics.pipeline.run_pipeline`. |
| 4 | Open `Analytics_Architecture.md` section "4. Stage order (pipeline stages)". | A Mermaid `flowchart` shows stages 1 to 12 ending in `PipelineResult`. |
| 5 | Open `Frontend_Architecture.md` section "4.2 Page hierarchy". | A Mermaid diagram shows the page hierarchy of the routes of TC-001-04. |
| 6 | Open `Repository_Structure.md` section "8. Repository dependency diagram". | A Mermaid diagram of the repository dependencies is present. |
| 7 | View each file in a Mermaid-capable viewer. | Every diagram renders without a syntax error message. |

### TC-001-06 Hygiene grep for open placeholders returns no match

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -rnE "T[B]D\|T[O]DO" docs/design; echo "exit=$?"`. | No line is printed before `exit=1`; the exit status is `1` (no match). |

### TC-001-07 Analytics_Architecture.md shows the stage order, single entry point and purity rules

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `docs/design/Analytics_Architecture.md` §4 and its stage table. | Stages appear in the order 1 Duplicate detection, 2 Quality gate, 3 Epoch detection, 4 Speaker screen, 5 Morning adjustment, 6 Personal baseline, 7 Scoring, 8 CUSUM, 9 Alert generation, 10 Day ledger, 11 Data alerts, 12 Analytics aggregates (last). |
| 2 | Search the document for `run_pipeline`. | `analytics.pipeline.run_pipeline` is named as the single entry point (ARC-040), with the signature copied from TRD 01 §8 / TRD 07 §4.5. |
| 3 | Open §2 "Architectural rules". | The purity rule (no I/O, no `backend` import, ARC-041), float64 arithmetic (ARC-046) and determinism (ARC-042) are stated, each with its ARC ID. |

### TC-001-08 Analytics_Architecture.md describes frozen baselines, `late_arrival` and natural keys

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open §9 "Frozen baselines, late arrivals and human data on rebuild". | Frozen-baseline reuse (ARC-043) is described: a frozen baseline is reused, not recomputed. |
| 2 | In the same section search for `late_arrival`. | The `late_arrival` warning is described (ARC-044). |
| 3 | Read the natural-key paragraph. | Natural keys for idempotent upserts are named (ARC-045), including that human-entered data (reviews, notes, acknowledgements, snoozes) survives a rebuild. |

### TC-001-09 Backend and Deployment documents record the system boundary and security rules

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `Backend_Architecture.md` §2 "System context and trust boundaries" and §11 "Security controls". | The ingest API is the only system boundary for device data; the no-audio rule is stated. |
| 2 | Search both documents for `ingest:write` and `pipeline:run`. | Both API key scopes are named; users authenticate with JWT. |
| 3 | Open `Deployment_Architecture.md` §9 "Security boundaries in deployment". | TLS on every hop including the database, encryption at rest and the synthetic-data-only rule for the interim stack are stated, citing ARC-001..ARC-008. |

### TC-001-10 Repository_Structure.md shows the layout and the dependency direction

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `docs/design/Repository_Structure.md` §2 "Top-level layout". | The layout matches TRD 01 §4.6 (`analytics/`, `backend/`, `frontend/`, `database/`, `tests/`, `docs/`, `specs/`, `scripts/`, `.github/`). |
| 2 | Open §8 "Repository dependency diagram". | The diagram shows the direction `api → services → repositories → models` and shows `analytics/` importing nothing from `backend/` (ARC-041, ARC-051). |
| 3 | Open §7 "Existing skeleton files (kept and filled)". | The ARC-050 skeleton files are listed as kept, not renamed. |

### TC-001-11 Testing_Architecture.md describes the test pyramid and where R01–R10 run

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `docs/design/Testing_Architecture.md` §2 and §3. | The pyramid and directories of TRD 13 are described: unit, integration, validation Tier A and Tier B, contract, security, E2E. |
| 2 | Open §5 "R01–R10 validation (answer key)". | The document names the directory and test level where the R01–R10 cases run (`tests/validation/`). |

### TC-001-12 Every section cites TRD requirement IDs; diagrams are Mermaid, not binary files

| Step | Action | Expected Result |
|---|---|---|
| 1 | For each of the nine documents, read every `##` section. | Each section cites at least one TRD requirement ID or TRD section (for example `ARC-040`, `TRD 19 §4.3`, `FE-020`, `GIT-054`). |
| 2 | Pick five mapping rows at random (two endpoints, two tables, one route) and compare with TRD 19 §4.3, TRD 20 §4.6 and TRD 04 §4.3. | Path, method, table name and route match the TRD exactly; no contradiction. |
| 3 | Run `git ls-files docs/design`. | Only the nine `.md` files are tracked; no `.png`, `.svg`, `.drawio` or other binary diagram file. |

### TC-001-13 The Phase 2 PR changed only `docs/design/` and the batch report and no TRD

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `gh pr view 3 --json title,state,files --jq '.state, (.files[].path)'`. | State is `MERGED`; the listed paths are under `docs/design/`, the Phase 2 batch report under `docs/reports/` (for example `CHECKPOINT_1_DESIGN_DOCS.md`) and, only for corrections requested in review round 1, files under `specs/`. |
| 2 | Run `gh pr view 3 --comments` and read review round 1. | Every `specs/` change in step 1 corresponds to a correction the reviewer requested in the checkpoint review (D-101); none was made by the Phase 7 prompt run on its own. |
| 3 | Check that open design questions were not decided in the design documents. | Questions raised by the author appear as OQ rows in TRD 24 or in the documents' "Open questions" sections referring to TRD 24 (AGT-009). |

### TC-001-14 Negative: documents contain no secret, connection string, real data or extra page

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -rnE "postgres(ql)?(\+psycopg)?://[^ ]*:[^ ]*@" docs/design`. | No match (no connection string with credentials). |
| 2 | Run `grep -rniE "password *[=:] *[^ ]+\|api[_-]?key *[=:] *[A-Za-z0-9]{16,}" docs/design`. | No secret value is printed; any match only names a variable such as `SEED_ADMIN_PASSWORD` without a value. |
| 3 | Run `grep -rnoE "\bR[0-9]{2}\b" docs/design \| sort -u -t: -k3`. | Residents appear only as study IDs (R01..R11 fixtures); no person name, room number or date of birth appears near them. |
| 4 | Run the "Forbidden terms" step of the CI `repo-hygiene` job locally (copy its first `git grep` line from `.github/workflows/ci.yml`). | No match in `docs/design` (the old facility name of AGT-019 is absent). |
| 5 | Search `Frontend_Architecture.md` and `UI_Architecture.md` for any route other than those of TC-001-04 described as built in v0.1. | None; v0.1 pages are named only as superseded (D-110). |

## API Validation

Not applicable: FEAT-001 exposes and consumes no endpoint; `OpenAPI_Spec.md` only documents the planned endpoints (checked in TC-001-02).

## Database Validation

Not applicable: FEAT-001 creates, alters or reads no table; `Database_ERD.md` only documents TRD 20 §4.6 (checked in TC-001-03).

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -rnE "T[B]D\|T[O]DO" docs/design` (TC-001-06). | Exit status 1, no output. |
| 2 | Search the route map for a page not in D-110 (TC-001-04, TC-001-14 step 5). | None found. |
| 3 | Search for connection strings and secret values (TC-001-14 steps 1–2). | None found. |
| 4 | Search for an EWMA chart planned in the MVP (TC-001-04 step 5). | Only "deferred / not built" statements found. |
| 5 | Check for binary diagram files in `docs/design` (TC-001-12 step 3). | None tracked. |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-001-AC-01 | `ls docs/design` lists exactly the nine FR-01 file names. | TC-001-01 |
| FEAT-001-AC-02 | Endpoint mapping table has 32 rows E-01..E-32, each with a file under `backend/api/` and a module under `backend/services/`. | TC-001-02 |
| FEAT-001-AC-03 | All 24 TRD 20 §4.6 tables appear in the `erDiagram` and the writer/reader table. | TC-001-03 |
| FEAT-001-AC-04 | Route mapping lists exactly the D-110 routes, each with ≥ 1 endpoint ID; no EWMA component planned. | TC-001-04, TC-001-14 |
| FEAT-001-AC-05 | Mermaid diagrams exist for ERD, request flow, pipeline stages, page hierarchy; `Repository_Structure.md` has the dependency diagram. | TC-001-05 |
| FEAT-001-AC-06 | `grep -rnE "T[B]D\|T[O]DO" docs/design` exits 1. | TC-001-06 |
| FEAT-001-AC-07 | The Phase 7 run changed no file outside `docs/design/` and the batch report and no TRD; review corrections are in the same PR #3. | TC-001-13 |

## Test Data Requirements

- No runtime data. The repository files under `docs/design/` and the TRDs named in Preconditions.
- GitHub read access for `gh pr view 3` (TC-001-13).
- No environment variables, no resident records, no audio.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-001-FR-01 (TRD 25 §4.6 Phase 2 Outputs) | FEAT-001 | TC-001-01 |
| FEAT-001-FR-02 (TRD 19 §4.3, D-24, ARC-050) | FEAT-001 | TC-001-02 |
| FEAT-001-FR-03 (TRD 20 §4.6) | FEAT-001 | TC-001-03 |
| FEAT-001-FR-04 (FE-020, D-110) | FEAT-001 | TC-001-04 |
| FEAT-001-FR-05 (ARC-040, ARC-041, ARC-042, ARC-046) | FEAT-001 | TC-001-07 |
| FEAT-001-FR-06 (ARC-043, ARC-044, ARC-045) | FEAT-001 | TC-001-08 |
| FEAT-001-FR-07 (ARC-001..ARC-008) | FEAT-001 | TC-001-09 |
| FEAT-001-FR-08 (TRD 01 §4.6, ARC-041, ARC-051) | FEAT-001 | TC-001-10 |
| FEAT-001-FR-09 (TRD 13 §4, TRD 25 §4.4) | FEAT-001 | TC-001-11 |
| FEAT-001-FR-10 (GIT-054) | FEAT-001 | TC-001-06, TC-001-12 |
| FEAT-001-FR-11 (GIT-055) | FEAT-001 | TC-001-05, TC-001-12 |
| FEAT-001-FR-12 (AGT-009) | FEAT-001 | TC-001-13 |
| AGT-001, D-101 | FEAT-001 | TC-001-13 |
| OQ-18 (no EWMA) | FEAT-001 | TC-001-04 |
| GIT-073, GIT-080, AGT-017 (no secrets, no real data) | FEAT-001 | TC-001-14 |
| TST / E2E IDs | FEAT-001 | None: TRD 25 §4.6 Phase 2 requires no tests; inspection only |
