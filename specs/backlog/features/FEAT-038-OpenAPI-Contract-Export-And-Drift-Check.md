# FEAT-038 OpenAPI contract export and drift check

| Field | Value |
|---|---|
| Epic | Backend API |
| Build phase | Phase 5 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-024, FEAT-026, FEAT-028, FEAT-029, FEAT-031, FEAT-032, FEAT-033, FEAT-035, FEAT-036, FEAT-037 |
| Status | Complete |

## Purpose

Make the API contract of TRD 19 executable: serve the generated OpenAPI 3.1 document at `/api/v1/openapi.json` with the `bearerAuth` and `apiKeyAuth` schemes, export it with `python -m backend.cli export-openapi`, commit it as `docs/api_reference/openapi.json`, and add the contract tests that fail when the code drifts from the committed file or from the TRD 19 skeleton, when a response does not validate against its schema, when a TRD 19 path is missing or extra, or when a list, detail or analytics response lacks `meta`. The frontend generates its types from this file, so drift would break the dashboard silently.

## Business Context

- BR-17 (agreed architecture and contract-first build) and BR-15 (traceable, testable outputs): one committed contract that backend, frontend and tests share.
- BR-01, BR-16: the contract contains no audio property and no resident names (OAS-016).
- FRs covered (BACKLOG.md): FR-015.

## Referenced TRDs

- TRD 19 OAS-001..OAS-016 (versioning, generated document, path/schema equality, CI regeneration, response validation, enums, naming, problem media type, `X-Request-ID`, float precision, nullable fields, security schemes, frontend types, examples, no audio/PII), OAS-017 (`meta` presence), OAS-018 (CSV alternatives), OAS-020 (status codes), §4.4 servers, §4.5 OpenAPI skeleton, §8 implementation notes.
- TRD 05 API-113 (OpenAPI served unauthenticated; Swagger UI outside production; ReDoc disabled), API-114 (security schemes per operation), API-031 (`openapi_extra` for ingest bodies), §8 (`export-openapi`).
- TRD 13 TST-060..TST-064; TRD 19 AC-OAS-01..AC-OAS-07.
- TRD 15 §4.8 (`export-openapi` prints the OpenAPI JSON); TRD 16 CIC-018 (`openapi-contract` CI job).
- TRD 25 AGT-061 (never hand-edit generated files), AC-AGT-11; TRD 24 D-51.

## Scope

- FastAPI application metadata (`openapi: 3.1.0`, title "EchoWell API", version "0.1.0"), OpenAPI URL `/api/v1/openapi.json`, docs URL `/api/v1/docs` only when `APP_ENV` ∈ {local, staging, test}, ReDoc off.
- Security schemes `bearerAuth` and `apiKeyAuth` attached per operation as in TRD 19.
- CLI command `python -m backend.cli export-openapi` that prints the generated document without opening a database connection.
- Committed `docs/api_reference/openapi.json` and the human summary `docs/api_reference.md` (TRD 19 §8).
- Fixture `tests/fixtures/trd19_openapi_skeleton.yaml` (TRD 19 §4.5 verbatim) and the contract tests in `tests/contract/`.
- Enum comparison test DTO enums vs `pg_enum` (OAS-007).

## Out of Scope

- Generating `frontend/lib/api-types.ts` and `tsc --noEmit` (OAS-014, TST-063; FEAT-062).
- The CI job `openapi-contract` and branch protection wiring (TRD 16 CIC-018, CIC-070; FEAT-078); this feature provides the command and tests the job runs.
- Endpoint behaviour itself (the endpoint features listed as dependencies).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-038-FR-01 | All endpoints shall be mounted under `/api/v1`; a breaking contract change requires a new path version. | OAS-001, API-002 |
| FEAT-038-FR-02 | The generated document shall declare `openapi: 3.1.0`, `info.title` "EchoWell API", `info.version` "0.1.0" and the servers of TRD 19 §4.4, and shall be served unauthenticated at `/api/v1/openapi.json` in every environment; Swagger UI at `/api/v1/docs` only when `APP_ENV` ∈ {local, staging, test}; ReDoc disabled. | OAS-002, API-113 |
| FEAT-038-FR-03 | `python -m backend.cli export-openapi` shall print the generated document as JSON to standard output without connecting to the database, so that CI can run it with a dummy `DATABASE_URL`; the committed contract `docs/api_reference/openapi.json` is regenerated with `python -m backend.cli export-openapi > docs/api_reference/openapi.json` and never edited by hand. | OAS-002, OAS-005; TRD 15 §4.8; TRD 16 CIC-018; AGT-061, D-51 |
| FEAT-038-FR-04 | Every TRD 19 path, method, parameter, request body and response status code shall appear in the generated document and no other path under `/api/v1` shall appear; `/alerts/{id}/acknowledge` shall not appear. | OAS-003, OAS-020, TST-062 |
| FEAT-038-FR-05 | Every schema of TRD 19 §4.5 shall exist with the same property names, types, `required` lists and enum values; enum values equal the database enums (`ProcessedStatus`, `DayStatus`, `AlarmState`, `AlertStatus`, `NoteType`, `Role`, `Cohort`, `ResidentStatus`, `PipelineTrigger`, `PipelineStatus`, `IngestSource`, `ReviewOutcome`, `DataAlertKind`, `DataAlertStatus`). | OAS-004, OAS-007, OAS-008 |
| FEAT-038-FR-06 | Non-2xx responses shall use `application/problem+json` and `Problem`; every response shall declare the `X-Request-ID` header; nullable fields use `type: [X, "null"]` (Pydantic `anyOf` with null treated as equivalent) and are always present; floats are serialised in full precision. | OAS-009, OAS-010, OAS-011, OAS-012 |
| FEAT-038-FR-07 | Security schemes shall be `bearerAuth` (http bearer, JWT) and `apiKeyAuth` (header `X-API-Key`), attached to each operation as in TRD 19 §4.3. | OAS-013, API-114 |
| FEAT-038-FR-08 | `GET /scores` and `GET /analytics/baselines` shall declare a `text/csv` 200 alternative; `POST /sessions` and `POST /ingest` reference `IngestRecord` / `IngestBatchRequest` and the multipart `file` part through `openapi_extra`. | OAS-018, API-031 |
| FEAT-038-FR-09 | No schema shall contain a property for audio data, audio URLs, resident names, dates of birth or free-text identifiers other than study IDs; the only property containing "audio" is `audio_quality_flag`. | OAS-016, FR-015 |
| FEAT-038-FR-10 | TRD 19 §4.3 JSON examples shall be included as `examples` and each shall validate against its schema. | OAS-015 (Should) |
| FEAT-038-FR-11 | Contract tests: (a) the generated document equals the committed file; (b) it matches the TRD 19 skeleton fixture in paths, methods, status codes, parameters, property names, types, required lists and enums; (c) every response produced by `tests/integration/api/` validates against its declared schema with `openapi-core`; (d) every list, detail and analytics response contains `meta` with its seven fields; single-object action responses do not. | OAS-005, OAS-006, OAS-017, TST-060, TST-061, TST-062, TST-064 |

## Inputs

- The FastAPI application from `backend.main:create_app()` with all routers of the dependency features.
- TRD 19 §4.5 YAML skeleton (copied verbatim to `tests/fixtures/trd19_openapi_skeleton.yaml`).
- PostgreSQL `pg_enum` (integration test database) for OAS-007.

## Outputs

- `docs/api_reference/openapi.json` (committed), `docs/api_reference.md` (human summary), `tests/fixtures/trd19_openapi_skeleton.yaml`.
- Tests `tests/contract/test_openapi_contract.py`, `tests/contract/test_response_schemas.py`.
- CLI subcommand `export-openapi` in `backend/cli.py`.

## Data Flow

1. `create_app()` builds the FastAPI app; FastAPI generates the OpenAPI document from routers and Pydantic DTOs (names equal to TRD 19 component names).
2. `export-openapi` builds the app without running the lifespan (no database connection) and prints `app.openapi()` as JSON.
3. `test_openapi_contract.py` regenerates the document in-process, compares it with the committed file and with the normalised skeleton (anyOf-with-null ≡ `type: [X, "null"]`).
4. An integration-suite hook records every (path, method, status, body) and `test_response_schemas.py` validates each against the committed document; a `meta` check runs on the recorded list, detail and analytics bodies.
5. CI (`openapi-contract`, FEAT-078) runs the export and `diff -u` against the committed file.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-024, FEAT-026, FEAT-028, FEAT-029, FEAT-031, FEAT-032, FEAT-033, FEAT-035, FEAT-036, FEAT-037

- FEAT-024 (pipeline run endpoints), FEAT-026 (ingest endpoints), FEAT-028 (resident detail, check-ins, features), FEAT-029 (devices), FEAT-031 (reviews and snooze), FEAT-032 (data alerts), FEAT-033 (notes), FEAT-035 (analytics), FEAT-036 (admissions), FEAT-037 (users): every TRD 19 endpoint must exist before the path-equality test can pass (their own dependencies bring in health, auth, residents, scores, alerts and config).

Features that build directly on this one (BACKLOG.md §4): FEAT-039, FEAT-062, FEAT-078.

## Database Impact

None: no table is created or modified. The enum comparison test only reads `pg_enum` on the test database.

## API Impact

- Exposed: `GET /api/v1/openapi.json` (unauthenticated) and `GET /api/v1/docs` outside production.
- Verifies all endpoints E-01..E-32 against TRD 19.

## Frontend Impact

None in this feature. The committed document is the input of `openapi-typescript` for `frontend/lib/api-types.ts` (FEAT-062, OAS-014).

## Analytics Impact

None: the contract carries analytics values unchanged (full float64, OAS-011).

## Security Requirements

- The OpenAPI document is public by design (API-113) and contains no secrets, example tokens or real data; examples use study IDs only.
- Swagger UI disabled in production (API-113).
- No audio-capable schema or content type (OAS-016, TST-133 in FEAT-039).

## Error Handling

- Drift between code and committed file → `test_openapi_contract.py` fails with a unified diff; fix by regenerating and committing in the same PR (CIC-018, AGT-061).
- A response that fails schema validation → `test_response_schemas.py` fails naming path, method, status and the JSON-schema error.
- `export-openapi` must succeed without a reachable database; a connection attempt is a defect.

## Logging Requirements

None beyond the standard startup logs; `export-openapi` writes only the document to stdout (no log lines on stdout, so the redirect stays valid JSON).

## Testing Requirements

- Contract (`tests/contract/test_openapi_contract.py`, marker `contract`): TST-060 equality with the committed file; skeleton comparison (OAS-005); TST-062 path set equality including absence of `/alerts/{id}/acknowledge`; OAS-013 schemes; OAS-016 property scan; OAS-018 CSV alternatives; OAS-015 example validation; AC-OAS-01 both documents validate with `openapi-spec-validator`.
- Contract (`tests/contract/test_response_schemas.py`): TST-061 every recorded integration response validates (AC-OAS-03); TST-064 `meta` on list, detail and analytics responses and absence on action responses (OAS-017).
- Integration (`tests/integration/db/test_enums.py`, marker `integration`): OAS-007 DTO enums equal `pg_enum` labels (AC-OAS-06).
- CLI smoke: `python -m backend.cli export-openapi` with `DATABASE_URL=postgresql+psycopg://x:x@localhost/x` exits 0 and prints valid JSON.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-038-AC-01 | `python -m backend.cli export-openapi > /tmp/openapi.json && diff -u docs/api_reference/openapi.json /tmp/openapi.json` exits 0 on the delivered commit, also with an unreachable dummy `DATABASE_URL`. | TST-060, OAS-005, CIC-018, AC-AGT-11 |
| FEAT-038-AC-02 | `docs/api_reference/openapi.json` and `tests/fixtures/trd19_openapi_skeleton.yaml` both validate as OpenAPI 3.1 with `openapi-spec-validator`. | AC-OAS-01 |
| FEAT-038-AC-03 | The path set of the generated document under `/api/v1` equals the TRD 19 endpoint list E-01..E-32 (plus `/openapi.json`), and `/alerts/{id}/acknowledge` is absent. | TST-062, OAS-003 |
| FEAT-038-AC-04 | Every response captured by `pytest tests/integration -q` validates against its declared schema, including all Problem responses. | TST-061, AC-OAS-03 |
| FEAT-038-AC-05 | Every captured list, detail and analytics response contains `meta` with `facility_name`, `facility_tz`, `data_source_label`, `as_of`, `baseline_n`, `cusum_h`, `pipeline_profile`; `Token`, `User`, `IngestBatchAccepted`, `Alert` and `Health` responses do not. | TST-064, OAS-017 |
| FEAT-038-AC-06 | The enum test finds identical value sets between DTO enums and `pg_enum`. Verified by: Integration (`tests/integration/db/test_enums.py`). | OAS-007, AC-OAS-06 |
| FEAT-038-AC-07 | A scan of the generated document finds no property containing `audio` other than `audio_quality_flag` and no resident `name` or `dob` property. Verified by: Contract (`tests/contract/test_openapi_contract.py`). | OAS-016, AC-OAS-07, FR-015 |
| FEAT-038-AC-08 | `GET /api/v1/openapi.json` returns 200 without credentials; `GET /api/v1/docs` returns 404 when `APP_ENV=production` and 200 when `APP_ENV=test`. Verified by: Contract (`tests/contract/test_openapi_contract.py`; TST-060). | API-113 |

## Definition of Done

- All FEAT-038 acceptance criteria pass.
- Contract tests pass in `pytest -m contract`; the committed document is regenerated in the same PR as any API change (D-51).
- `docs/api_reference.md` summarises every endpoint with its auth and status codes.
- The batch report lists the implemented requirement IDs (AGT-022); the TRD differences noted under Implementation Notes were resolved in PR #2 and need no report.

## Implementation Notes

- Name Pydantic models exactly as TRD 19 components; request models use `ConfigDict(extra="forbid")`; response nullables are `X | None` without defaults and serialised with `response_model_exclude_none=False` (TRD 19 §8).
- Build the app for export without the lifespan handler; the database engine connects lazily in the lifespan (TRD 16 §8 note), which `export-openapi` does not run.
- Sort keys when printing (`json.dumps(doc, indent=2, sort_keys=True)`) so regeneration is byte-stable across runs.
- Resolved (PR #2): TRD 05 §8 described `export-openapi` as "writing `docs/api_reference/openapi.json`" and TRD 25 Phase 5 lists `python -m backend.cli export-openapi` followed by `git diff --exit-code docs/api_reference/openapi.json`, while TRD 15 §4.8 says the command prints the JSON and TRD 16 CIC-018 / `ci.yml` redirect stdout to `/tmp/openapi.json` and diff it with the committed file. Writing the committed file from the same command would make the CI diff always pass. Resolved (TRD 24 D-89): the command prints to stdout and writes no file; TRD 05 §8 and TRD 25 Phase 5 now regenerate with `python -m backend.cli export-openapi > docs/api_reference/openapi.json` and check with the CI diff.
- Use `openapi-core` 0.19.x for response validation and `openapi-spec-validator` 0.7.x for document validation (TRD 19 §6, TRD 16 §6).
