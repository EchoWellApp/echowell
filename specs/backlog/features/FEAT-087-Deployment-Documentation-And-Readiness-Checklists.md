# FEAT-087 Deployment documentation and readiness checklists

| Field | Value |
|---|---|
| Epic | DevOps & Deployment |
| Build phase | Phase 9 (TRD 25) |
| Priority | P1 |
| Complexity | Low |
| MVP status | Required |
| Dependencies | FEAT-086 |
| Status | Not Started |

## Purpose

Write the documents that let a team member deploy, verify, operate and contain incidents on EchoWell without further clarification, and that decide readiness objectively: `specs/backlog/DEPLOYMENT_CHECKLIST.md` and `specs/backlog/MVP_READINESS_CHECKLIST.md` derived from the TRD 13 and TRD 15 acceptance criteria, `docs/reports/DEPLOYMENT_CONFIGURATION_GUIDE.md`, `docs/reports/CONFIGURATION_VALIDATION_REPORT.md` (Phase 9 configuration checked against SRC-01 and TRD 22), and the incident-containment and research-data-governance procedures in `docs/deployment.md`. This closes Phase 9 before any deployment happens.

## Business Context

- BR-17: the deployment procedures of SRC-01 and TRD 15 become executable checklists.
- BR-16: incident containment within 1 hour (SEC-170), research-data governance (SEC-180..SEC-184), third-party service rules (TPS-001..TPS-005).
- BR-15 and TRD 13 TST-170: the MVP is accepted only when every MVP-01..MVP-15 criterion passes with evidence.

## Referenced TRDs

- TRD 25 §4.6 Phase 9 outputs and definition of done, AGT-022, AGT-032, AGT-033, AC-AGT-07.
- TRD 15 §4.2 local procedure, §4.4, §4.5, §4.6, §4.8, §4.9, §4.10, §4.11, §4.12, §4.13, §4.14, §7 AC-DEP-01..AC-DEP-11, §8 file list.
- TRD 13 TST-170 (Table 4.17-A MVP-01..MVP-15), TST-180..TST-188, §7 AC-TST-01..AC-TST-13.
- TRD 22 TPS-001..TPS-007.
- TRD 12 SEC-005, SEC-170, SEC-171, SEC-172, SEC-173, SEC-180, SEC-181, SEC-182, SEC-183, SEC-184.
- TRD 21 ENV-050 (every variable documented; deviations recorded).
- TRD 24 D-21 (reports to `docs/reports/`, checklists to `specs/backlog/`).

## Scope

- `specs/backlog/DEPLOYMENT_CHECKLIST.md`: one checkbox row per deployment acceptance item with its source ID and the evidence to attach: AC-DEP-01..AC-DEP-11, AC-CIC-01..AC-CIC-10, DEP-080/DEP-081 smoke results, AC-ENV-01..AC-ENV-09, the Phase 10 definition of done (TRD 25 §4.6), and the go-live item "hosting approved for PHI-derived data (AWS)" signed by the PI and UND IT (SEC-005), marked as not applicable to the interim deployment.
- `specs/backlog/MVP_READINESS_CHECKLIST.md`: MVP-01..MVP-15 (TST-170 Table 4.17-A) and AC-TST-01..AC-TST-13, each with the test or report that evidences it.
- `docs/reports/DEPLOYMENT_CONFIGURATION_GUIDE.md`: the local procedure (TRD 15 §4.2 steps 1–9 verbatim), Neon, Railway and Netlify procedures, environment-variable matrix (every TRD 21 variable), staging and production release steps, smoke tests, rollback table, backup and restore, demo fallback.
- `docs/reports/CONFIGURATION_VALIDATION_REPORT.md`: pass/fail table comparing each Phase 9 artefact (`netlify.toml`, `railway.toml`, `railway.nightly.toml`, Dockerfiles, `docker-compose.yml`, `.env*.example`, workflows) with SRC-01, TRD 15, TRD 16, TRD 21 and TRD 22, including regions (D-54), `sslmode=require` on both database URLs, production templates (`PIPELINE_PROFILE=production`, no `PIPELINE_AS_OF`), and the OpenAPI drift check.
- `docs/deployment.md` sections: incident containment (revoke API keys, deactivate users, rotate JWT_SECRET, rotate database role passwords, scale to zero), incident reporting (PI and Team 2 lead within 24 h; PI decides on UND IT security and IRB reporting), investigation with `audit_logs` correlated by `request_id`, post-incident note kept in the team's private space; research-data governance (UND Speech Study data owned by the PI, IRB protocol, no retention deletion job, exports only via `echowell_readonly` from AWS once live data exists, public datasets only under licence and never with live data, third-party documents by link only); service ownership records.

## Out of Scope

- Executing any deployment or drill (FEAT-088, FEAT-089, FEAT-090).
- The audits of Phase 11 (FEAT-091).
- Any change to TRDs; contradictions found are listed for TRD 24 (AGT-009).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-087-FR-01 | `specs/backlog/DEPLOYMENT_CHECKLIST.md` and `specs/backlog/MVP_READINESS_CHECKLIST.md` shall be written from the TRD 13 and TRD 15 acceptance criteria if absent, each item citing its source ID and evidence. | TRD 25 §4.6 Phase 9 Outputs, AGT-032, D-21 |
| FEAT-087-FR-02 | The MVP readiness checklist shall list MVP-01..MVP-15 with the evidence named in Table 4.17-A, and state that the MVP is accepted only when all pass on the release candidate commit. | TST-170 |
| FEAT-087-FR-03 | `docs/reports/DEPLOYMENT_CONFIGURATION_GUIDE.md` shall reproduce the TRD 15 §4.2 local setup procedure verbatim and the staging and production release steps of TRD 15 §4.9 and §4.10. | TRD 15 §4.2, §4.9, §4.10 |
| FEAT-087-FR-04 | Every environment variable of TRD 21 shall be documented with its per-environment value source; deviations from the TRD 21 §4.7 matrix shall be recorded in `docs/deployment.md` with a reason. | TRD 25 §4.6 Phase 9 DoD, ENV-050 |
| FEAT-087-FR-05 | `docs/reports/CONFIGURATION_VALIDATION_REPORT.md` shall record pass/fail of each Phase 9 configuration item against SRC-01 and TRD 22, including Neon `aws-us-east-1` and Railway US East, `sslmode=require` on DATABASE_URL and DATABASE_MIGRATION_URL, production templates with `PIPELINE_PROFILE=production` and no `PIPELINE_AS_OF`, and the OpenAPI drift check in CI, and shall state that no deployment was performed. | TRD 25 §4.6 Phase 9 DoD, D-54, D-51 |
| FEAT-087-FR-06 | `docs/deployment.md` shall document containment actions executable within 1 hour: revoke API keys (CLI), deactivate users (`PATCH /api/v1/users/{id}`), rotate JWT_SECRET, rotate database role passwords and scale the Railway or App Runner service to zero. | SEC-170 |
| FEAT-087-FR-07 | It shall state that a suspected incident is reported to the PI and the Team 2 lead within 24 hours, that the PI decides on UND IT security and IRB reporting, that investigation correlates `audit_logs` with application logs by `request_id`, and that post-incident notes are kept outside the public repository. | SEC-171, SEC-172, SEC-173 |
| FEAT-087-FR-08 | It shall state the research-data governance rules: data owned by the PI under the IRB protocol; no retention-based deletion job (OQ-01); exports only via `echowell_readonly` by IRB-listed personnel from AWS once live data exists; DAIC-WOZ/E-DAIC only under licence and never with live data; third-party documents only by link. | SEC-180, SEC-181, SEC-182, SEC-183, SEC-184 |
| FEAT-087-FR-09 | It shall record, per third-party service, that only TRD 22 §4.1 services are used, that no real resident data is stored on Netlify, Railway, Neon or Sentry, that go-live happens only on AWS, that data services are in the United States, and the owner, ≥ 2 MFA administrators, plan and verified limits. | TPS-001..TPS-007 |
| FEAT-087-FR-10 | The deployment checklist shall include the go-live item "hosting approved for PHI-derived data (AWS)" to be signed by the PI and UND IT before any live device is pointed at the API. | SEC-005, DEP-118 |
| FEAT-087-FR-11 | Every report named in TRD 25 §4.6 Phase 9 shall exist at its stated path. | AC-AGT-07 |

## Inputs

- Phase 9 artefacts from FEAT-077..FEAT-086; TRD 13, TRD 15, TRD 16, TRD 21, TRD 22, TRD 12 texts; SRC-01 `specs/architecture/Deployment_Architecture.md`.

## Outputs

- `specs/backlog/DEPLOYMENT_CHECKLIST.md`, `specs/backlog/MVP_READINESS_CHECKLIST.md`.
- `docs/reports/DEPLOYMENT_CONFIGURATION_GUIDE.md`, `docs/reports/CONFIGURATION_VALIDATION_REPORT.md`.
- `docs/deployment.md` (incident containment, data governance, service ownership; plus the sections contributed by FEAT-081..FEAT-086).

## Data Flow

TRD acceptance criteria and Phase 9 artefacts → checklist rows and validation table → reviewer checks each item → Phase 10 (FEAT-088..FEAT-090) fills the evidence columns → Phase 11 (FEAT-091) audits them.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-086

- [FEAT-086](FEAT-086-Deploy-Workflows-And-Post-Deploy-Smoke.md) Deploy workflows and post-deploy smoke tests (the last Phase 9 artefact the guide and validation report describe).

## Database Impact

None.

## API Impact

None. The containment procedure references `PATCH /api/v1/users/{id}` (TRD 19 E-27) without changing it.

## Frontend Impact

None.

## Analytics Impact

None.

## Security Requirements

- No secret, connection string with credentials, real resident data or personal names in any document (AGT-016, AGT-017, TPS-041).
- Post-incident notes are not stored in the public repository (SEC-173).

## Error Handling

- A configuration item that fails validation is recorded as FAIL with the reason in `CONFIGURATION_VALIDATION_REPORT.md`; Phase 10 does not start until it is fixed (AGT-033).
- A TRD contradiction found while writing is listed in the report for TRD 24 rather than resolved in the documents (AGT-009).

## Logging Requirements

None at runtime. The batch report lists documents created and validation results (AGT-022).

## Testing Requirements

- Inspection: each checklist row cites an existing TRD ID; `grep -rnE "T[B]D|T[O]DO|\[p[l]aceholder\]" specs/backlog docs/reports/DEPLOYMENT_CONFIGURATION_GUIDE.md docs/reports/CONFIGURATION_VALIDATION_REPORT.md` returns nothing (TRD 25 §4.6 Phase 12 command style).
- Commands recorded in the validation report: `docker compose config`; `docker compose up -d && pytest -q` (TRD 25 §4.6 Phase 9 Commands).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-087-AC-01 | The four files `specs/backlog/DEPLOYMENT_CHECKLIST.md`, `specs/backlog/MVP_READINESS_CHECKLIST.md`, `docs/reports/DEPLOYMENT_CONFIGURATION_GUIDE.md`, `docs/reports/CONFIGURATION_VALIDATION_REPORT.md` exist. | AC-AGT-07, AGT-032 |
| FEAT-087-AC-02 | The MVP readiness checklist contains 15 rows MVP-01..MVP-15 with the evidence of Table 4.17-A. | TST-170 |
| FEAT-087-AC-03 | Every variable name of TRD 21 §4.2, §4.3 and §4.5 appears in the configuration guide. | TRD 25 §4.6 Phase 9 DoD |
| FEAT-087-AC-04 | `CONFIGURATION_VALIDATION_REPORT.md` contains a pass/fail line for regions, `sslmode=require` on both URLs, production profile templates and the OpenAPI drift check, and the sentence that no deployment was performed. | TRD 25 §4.6 Phase 9 DoD |
| FEAT-087-AC-05 | `docs/deployment.md` contains the five containment actions of SEC-170, the 24-hour reporting rule, and the governance rules of SEC-180..SEC-184. | SEC-170, SEC-171, SEC-180..SEC-184 |
| FEAT-087-AC-06 | The placeholder grep of the Testing Requirements returns nothing. | TRD 25 §4.6 Phase 12 Commands |

## Definition of Done

- All FEAT-087 acceptance criteria pass; Phase 9 definition of done (TRD 25 §4.6) met in full (AGT-033).
- Phase 9 PR approved by the algorithm lead (AGT-013).

## Implementation Notes

- The guide lives at `docs/reports/DEPLOYMENT_CONFIGURATION_GUIDE.md` (TRD 25 §4.6 Phase 9, D-21); TRD 15 §4.2 and §8 were aligned to this path in the PR #2 consistency fixes.
- Keep the checklists as Markdown tables with columns ID, Criterion, Source, Evidence, Status so Phase 11 can parse them.
- Copy procedures verbatim where TRD 15 says so (local setup); paraphrasing risks drift.
