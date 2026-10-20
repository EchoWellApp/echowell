# FEAT-090 Demo acceptance and local fallback rehearsal (SRC-15 steps 4–5)

| Field | Value |
|---|---|
| Epic | Testing & Validation |
| Build phase | Phase 10 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-088, FEAT-076 |
| Status | Not Started |

## Purpose

Execute and record the end-of-semester demo acceptance: demo step 4 ("pipeline passes the test set answer key, then processes a real record") with the answer-key run on an isolated `test_v0_1` database and one device record from a team-member speaker under a `T`-prefixed demo study ID posted to interim production; demo step 5 ("the new check-in shows up on the dashboard") with the overview's last check-in and 30-day used count updating (and a new tally bar once that resident's baseline is frozen); the automated 5-second latency test and the seeded-login test; and the rehearsed local Docker Compose fallback that is used if production is not passing its smoke tests by 5 Nov 2026.

## Business Context

- TRD 00 §4.8 MVP definition: the MVP exists to produce the demo video of one check-in travelling device → cloud → pipeline → dashboard (SRC-15).
- BR-15 (answer key), BR-01 (raw record stored unaltered), BR-12 / BR-13 (dashboard shows the result).
- FR-184 (a check-in shows on the dashboard), D-67 (what "shows" means), D-59 (the live check-in goes to interim production because staging has a fixed as-of).
- RSK-12 (timeline): local fallback if the cloud is not ready by 5 Nov 2026.

## Referenced TRDs

- TRD 13 TST-170, TST-180, TST-181, TST-182, TST-183, TST-184, TST-185, TST-186, TST-187, TST-188, AC-TST-10, AC-TST-11, MVP-01..MVP-15.
- TRD 15 DEP-090, DEP-091, DEP-092, DEP-093, DEP-008, AC-DEP-09.
- TRD 00 §4.8 (demo steps 1–6), VIS-024, AC-VIS-03, SC-03.
- TRD 03 NFR-011.
- TRD 14 DS-01, DS-09, TDV-007.
- TRD 02 FR-184.
- TRD 11 UX-144.
- TRD 24 RSK-12, D-59, D-67, D-28, OQ-17.

## Scope

- Step 4a: run the answer-key acceptance on an isolated database (local Compose or a disposable Neon branch) seeded only with DS-01 under profile `test_v0_1` on the commit deployed to the demo environment; record "Overall: PASS" from `docs/reports/ALGORITHM_VALIDATION_REPORT.md`.
- Step 4b: register a demo resident with a `T`-prefixed study ID (e.g. `T01`) and a test device on interim production; Team 1 posts one record produced by the device from a team-member speaker to `POST /api/v1/sessions` with an interim test API key; verify 201, the unaltered `raw_sessions.payload`, and a processed status with reasons.
- Step 5: reload `/residents` and confirm, within 60 s of the POST, the demo resident's "Last check-in" = the record's local time and the 30-day used count +1; "Baseline forming · 1 of 30 sessions" after the first usable record (production profile) and no alarm; once its baseline is frozen, one more tally bar on Resident detail.
- Automated evidence: TST-187 (≤ 5 s on the warm Compose stack, in `e2e.yml`) and TST-188 (seeded logins) results attached.
- Local fallback rehearsal: `docker compose --profile demo up -d db backend frontend-prod` on a team laptop with the commit on `main`, dashboard at `http://localhost:3001`, device or `curl` POST to `http://<laptop LAN IP>:8000/api/v1/sessions` with the backend port bound to the LAN only for the rehearsal; steps written in `docs/deployment.md`; performed before 15 Nov 2026.
- Demo acceptance record in `docs/reports/DEPLOYMENT_REPORT.md` (section "Demo acceptance") and in `specs/backlog/MVP_READINESS_CHECKLIST.md` (MVP-01..MVP-15 status).

## Out of Scope

- Team 1 device capture, extraction and transport (TRD 00 §4.8 steps 1–3; ASM-05).
- Filming the demo videos (step 6) and the presentations (1 Dec and 8 Dec 2026).
- Loading `test_v0_1` data into production to enrich the demo (forbidden, DEP-093).
- Any real resident data (VIS-024, D-28).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-090-FR-01 | Demo step 4 shall be accepted when the validation suite reports PASS for all VC cases on the commit deployed to the demo environment, and one feature record produced by Team 1's device from a team-member speaker under a demo study ID is received by `POST /api/v1/sessions`, returns 201, appears unaltered in `raw_sessions` and has a processed status (usable, set_aside or quarantined) with reasons. | TST-180, AC-TST-11 |
| FEAT-090-FR-02 | The step 4 answer-key run shall use profile `test_v0_1` on an isolated database seeded only with DS-01; the real record shall be processed with profile `production` in the demo environment; fixture data and real records shall never share one database. | TST-182, TDV-007 |
| FEAT-090-FR-03 | The live demo check-in shall be posted to interim production under a `T`-prefixed demo study ID (profile `production`, as-of = request time), never to staging. | D-59, DEP-093, AC-VIS-03 |
| FEAT-090-FR-04 | Demo step 5 shall be accepted when, after the step 4 POST, reloading `/residents` shows the demo resident's "Last check-in" equal to the record's local time and its 30-day used count increased by 1, and, when its baseline is frozen, the Resident detail tally chart has one more bar for that session, within 60 s of the POST. | TST-181, FR-184, D-67, UX-144 |
| FEAT-090-FR-05 | The demo resident shall show "Baseline forming · 1 of 30 sessions" after its first usable record under the `production` profile (or the correct n) and no alarm. | TST-184 |
| FEAT-090-FR-06 | The automated latency test TST-187 (≤ 5 s on the warm Compose stack) and the seeded-login test TST-188 shall pass and be cited as evidence. | TST-187, TST-188, NFR-011, SC-03 |
| FEAT-090-FR-07 | If production is not passing the DEP-081 smoke tests by 5 Nov 2026, the demo shall run on a team laptop with `docker compose --profile demo up -d db backend frontend-prod` and the commit on `main`, with the same steps and criteria. | DEP-090, TST-183, RSK-12 |
| FEAT-090-FR-08 | The fallback laptop shall serve the dashboard at `http://localhost:3001` and accept device posts at `http://<laptop LAN IP>:8000/api/v1/sessions`, binding the backend port to the LAN interface only for the demo. | DEP-091 |
| FEAT-090-FR-09 | The fallback shall be rehearsed end to end (device or `curl` post → pipeline → dashboard) at least once before 15 Nov 2026, with the steps written in `docs/deployment.md`. | DEP-092, AC-DEP-09 |
| FEAT-090-FR-10 | The demo shall show the device-to-cloud path against production (single demo check-in, baseline forming) and the full dashboard behaviour (R01–R10, R09 alarm) against staging. | DEP-093 |
| FEAT-090-FR-11 | The MVP shall be recorded as accepted only when every MVP-01..MVP-15 criterion passes on the release candidate commit with evidence attached to the release PR. | TST-170, AC-TST-10 |

## Inputs

- Interim production and staging (FEAT-088); the E2E suite and its `@isolated` latency test (FEAT-076, run in `e2e.yml`).
- One device record from Team 1 (DS-09) under a `T`-prefixed study ID; an interim API key bound to that test device.
- The validation suite results on the deployed commit (CI `backend-reports`).

## Outputs

- Demo acceptance section in `docs/reports/DEPLOYMENT_REPORT.md` (step 4a, 4b, 5 results with timestamps, IDs and screenshots references), fallback rehearsal record in `docs/deployment.md`, updated `specs/backlog/MVP_READINESS_CHECKLIST.md`.

## Data Flow

Isolated `test_v0_1` database ← DS-01 → validation PASS (4a). Team 1 device → HTTPS `POST /api/v1/sessions` (X-API-Key) → interim production `raw_sessions` → synchronous per-resident pipeline (production profile) → `processed_sessions`, `day_ledger` → dashboard `/residents` reload shows last check-in and used count (4b, 5). Fallback: device or `curl` → laptop backend :8000 → pipeline → `frontend-prod` :3001.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-088, FEAT-076

- [FEAT-088](FEAT-088-Interim-Staging-And-Production-Deployment.md) Interim staging and production deployment (demo environments, `T`-prefixed roster, test API key).
- [FEAT-076](FEAT-076-End-To-End-Test-Suite-And.md) End-to-end suite (E2E-15 and TST-187 provide the automated version of step 5).

Features that build directly on this one (BACKLOG.md §4): FEAT-091.

## Database Impact

- Interim production: `residents`, `devices`, `device_assignments` rows for the `T`-prefixed demo resident (via `import-master-data`), `raw_sessions`, `processed_sessions`, `day_ledger`, `pipeline_runs`, `audit_logs` rows from the demo POST and runs.
- Isolated validation database: DS-01 load and derived tables (disposable).
- No schema change.

## API Impact

- Consumed: `POST /api/v1/sessions`, `GET /api/v1/residents`, `GET /api/v1/residents/{resident_code}`, `GET /api/v1/scores`, `GET /api/v1/health`, `POST /api/v1/auth/login`.
- Exposed: none new.

## Frontend Impact

- `/residents` and `/residents/[residentCode]` used for verification; no code change.

## Analytics Impact

- The demo record is processed under the `production` profile (baseline_n 30); the answer-key run under `test_v0_1`. No algorithm change.

## Security Requirements

- Only team-member voices or synthetic data; no real resident data on the interim stack (VIS-024, DEP-008, D-28).
- The interim API key is bound to a test device, not an Edgewood device (SEC-003).
- During the fallback, the backend port is exposed on the LAN only for the demo duration (DEP-091); local stack uses synthetic data only (SEC-065).

## Error Handling

- Step 4b returns 422 → inspect `ingest_rejections` reason with Team 1, fix the record format (schema v0.1), repost with a new session ID.
- Step 5 exceeds 60 s because of cold starts → disable app sleeping (DEP-042) and repeat; the automated 5 s check is TST-187.
- Production not passing DEP-081 by 5 Nov 2026 → switch to the rehearsed local fallback (DEP-090).
- Device access windows at Edgewood are not needed (team-member speaker), but re-pointing a device to the laptop depends on OQ-17 where a site device is involved.

## Logging Requirements

- Backend logs `request_completed`, `pipeline_run_started`/`finished` for the demo POST, without feature values (LOG-021).
- Audit rows `pipeline.run.started`/`finished`; the demo record's ingestion is traceable by `request_id`.
- Acceptance results recorded in the report with timestamps and IDs only.

## Testing Requirements

- Demo tests: TST-180, TST-181, TST-183, TST-184 (manual, recorded); TST-182 (inspection).
- Automated: TST-187 (E2E latency, FEAT-076), TST-188 (`tests/integration/test_seed_logins.py`), validation suite VC-R01..VC-R10, VC-G01..VC-G12 on the deployed SHA.
- System acceptance: MVP-01..MVP-15 (TST-170).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-090-AC-01 | The validation report on the demo commit shows "Overall: PASS" for all VC cases, produced on a database that contains no real or demo-device record. | TST-180 (a), TST-182 |
| FEAT-090-AC-02 | The demo POST to interim production returns 201; the stored `raw_sessions.payload` equals the request body; the session has status usable, set_aside or quarantined with its reasons. | TST-180 (b), MVP-02 |
| FEAT-090-AC-03 | Within 60 s of the POST, `/residents` shows the demo resident's last check-in at the record's local time and its 30-day used count +1, and its status "Baseline forming · 1 of 30 sessions" with no alarm after the first usable record. | TST-181, TST-184, AC-VIS-03 |
| FEAT-090-AC-04 | TST-187 passes (≤ 5 s) and TST-188 passes on the release candidate commit. | TST-187, TST-188 |
| FEAT-090-AC-05 | The local fallback rehearsal is documented in `docs/deployment.md` before 15 Nov 2026, and a `curl` POST to the laptop appears on the dashboard after pipeline processing. Verified by: Test (run the command in the criterion against the stated environment and check the stated result). | AC-DEP-09, DEP-092 |
| FEAT-090-AC-06 | `specs/backlog/MVP_READINESS_CHECKLIST.md` shows a status and evidence link for each of MVP-01..MVP-15. | TST-170, AC-TST-10 |

## Definition of Done

- All FEAT-090 acceptance criteria pass, or the report states which failed and why (then Phase 11 records NOT READY FOR DEMO).
- Phase 10 PR approved by the algorithm lead (AGT-013).

## Implementation Notes

- Use a fresh session ID following the device's pattern for every repost; a repeated session_id is stored as a duplicate and not displayed (AGT-053).
- Production resident status "1 of 30" (not "1 of 16"): the production profile has baseline_n 30 (D-01).
- A tally bar appears only after the demo resident's baseline is frozen (30 usable check-ins in production), so the bar criterion is usually not reachable in the demo window; the overview criteria are the acceptance evidence (D-67).
