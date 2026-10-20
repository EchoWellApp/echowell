# FEAT-089 Backups, restore drill and rollback procedure

| Field | Value |
|---|---|
| Epic | DevOps & Deployment |
| Build phase | Phase 10 (TRD 25) |
| Priority | P1 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-088 |
| Status | Not Started |

## Purpose

Protect the interim production database and make every deploy reversible: establish the weekly `pg_dump` of interim production (and before every release with a migration) to approved storage, record the Neon point-in-time restore window, run and document one restore drill into a Neon `restore-drill` branch before 15 Nov 2026, rehearse rollback of frontend and backend versions within 10 minutes without `alembic downgrade` in production, and document the full pipeline re-run after any restore. The interim stack holds synthetic and test data only, so it runs under the D-60 waiver of the AWS backup targets.

## Business Context

- BR-02 (immutable raw store, every other table rebuildable): recovery restores `raw_sessions` and human-entered tables, then re-runs the pipeline (SEC-163, DEP-087).
- BR-16: dumps encrypted and stored only on approved storage, never in GitHub (DEP-096, DEP-098, DB-054).
- RSK-12: rollback rehearsed before the demo (DEP-085).

## Referenced TRDs

- TRD 15 DEP-063, DEP-085, DEP-086, DEP-087, DEP-095, DEP-096, DEP-097, DEP-098, §4.12 rollback table, §4.13 PITR procedure, AC-DEP-06, AC-DEP-07, AC-DEP-08.
- TRD 06 DB-050, DB-051, DB-052, DB-053, DB-054.
- TRD 12 SEC-160, SEC-161, SEC-162, SEC-163.
- TRD 03 NFR-020..NFR-027 (in particular NFR-024 single backup target with interim waiver, NFR-025 restore drill cadence).
- TRD 20 PGS-039.
- TRD 22 TPS-031 (temporary `pre-<sha>` and `restore-drill` branches deleted within 7 days).
- TRD 24 D-60, ASM-07, OQ-01.

## Scope

- Backup procedure in `docs/deployment.md`: weekly (Mondays) and pre-migration-release `pg_dump --format=custom --no-owner` of production by the data steward from a UND-managed workstation, encrypted at rest, stored only on storage approved for the study's research data; never committed or uploaded as an Actions artifact; the Neon plan restore window in force recorded.
- Pre-release restore point: Neon branch `pre-<short-sha>` from `main` before merging a release with a migration; deleted after 7 days if unused.
- Restore drill (once before 15 Nov 2026): restore the latest dump into a new Neon branch `restore-drill`, point a temporary backend at it (or use `railway run` with the branch URLs), `GET /api/v1/health`, `run-pipeline --scope all`, compare row counts of `raw_sessions`, `alerts` and `audit_logs` with the source, run `pytest tests/validation -q` on the deployed SHA, record the result, delete the branch within 7 days.
- Rollback rehearsal (once before 15 Nov 2026): Netlify "Publish deploy" of the previous deploy and Railway "Redeploy" of the previous deployment, timed (≤ 10 minutes), plus the failing-healthcheck check on staging (AC-DEP-06).
- Rollback table and PITR procedure reproduced in `docs/deployment.md` (TRD 15 §4.12, §4.13), including "never `alembic downgrade` in production" and the post-restore full pipeline run.

## Out of Scope

- AWS RDS automated backups, PITR ≥ 7 days and the AWS restore drill (FEAT-092; D-60).
- Data retention and deletion policy (OQ-01 open; no deletion job, SEC-181).
- Any change to migrations or pipeline code.

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-089-FR-01 | Interim production data shall be protected by Neon point-in-time restore for the window of the plan in use plus the weekly dump, under the D-60 waiver of NFR-024; the window in force shall be recorded in `docs/deployment.md`. | DEP-095, NFR-024, SEC-160, D-60 |
| FEAT-089-FR-02 | A logical backup `pg_dump --format=custom --no-owner` of production shall be taken weekly (Mondays) and before every release containing a migration, by the data steward from a UND-managed workstation, encrypted at rest, stored only on storage approved for the study's research data. | DEP-096, DB-054 |
| FEAT-089-FR-03 | Backups and dumps shall never be committed to the repository or uploaded as GitHub Actions artifacts. | DEP-098, CIC-101 |
| FEAT-089-FR-04 | Before a release with a migration is merged to `main`, a Neon branch `pre-<short-sha>` shall be created from `main` and deleted after 7 days if unused. | DEP-063, TPS-031 |
| FEAT-089-FR-05 | Every production deploy shall be reversible to the previous frontend and backend version within 10 minutes using the platform "publish/redeploy previous" actions, rehearsed once before 15 Nov 2026. | DEP-085 |
| FEAT-089-FR-06 | `alembic downgrade` shall not be executed against production; schema rollback in production shall be done only by restoring a Neon branch or PITR point. | DEP-086 |
| FEAT-089-FR-07 | After any restore the full pipeline shall be re-run (`run-pipeline --scope all`) and shall reproduce previously frozen baselines. | DEP-087, ASM-07, SEC-163 |
| FEAT-089-FR-08 | One restore drill shall be performed on the interim stack before 15 Nov 2026: latest dump into Neon branch `restore-drill`, `GET /api/v1/health`, `run-pipeline --scope all`, comparison of `raw_sessions` and `alerts` row counts (and `audit_logs`, DB-051) with the source, and the R01–R10 validation on the deployed SHA. | DEP-097, DB-051, SEC-162, NFR-025 |
| FEAT-089-FR-09 | Recovery shall restore `raw_sessions`, reference tables, `staff_notes`, `alerts` (status, snoozes), `alert_reviews`, `users`, `api_keys` and `audit_logs`, then run a full pipeline. | SEC-163 |
| FEAT-089-FR-10 | The rollback table of TRD 15 §4.12 (frontend broken; backend fails healthcheck; backend functionally broken; broken after additive migration; data damaged) with its actions and time targets shall be documented, including revoking device keys with `revoke-api-key`, restoring, redeploying the matching backend, re-running the pipeline and issuing new keys with `create-api-key`, and recording the incident in an issue labelled `incident`. | TRD 15 §4.12 |
| FEAT-089-FR-11 | Storage and backups holding non-synthetic data shall be encrypted at rest; every connection to a non-local database shall use TLS. | DB-052, DB-053, PGS-039 |

## Inputs

- Running interim production and staging (FEAT-088); Neon console access; a UND-managed workstation with `pg_dump`/`pg_restore` 16.
- CLI commands `run-pipeline`, `revoke-api-key`, `create-api-key` (FEAT-016, FEAT-055).

## Outputs

- `docs/deployment.md` sections "Backups", "Restore drill" (with the drill record: date, dump timestamp, row counts, validation result), "Rollback" (with the rehearsal record and measured times), "PITR restore".
- Drill evidence referenced from `specs/backlog/DEPLOYMENT_CHECKLIST.md` (AC-DEP-07, AC-DEP-08).

## Data Flow

Production (Neon `main`) → `pg_dump` over TLS → encrypted file on approved storage → `pg_restore --no-owner` as `echowell_migrator` into Neon branch `restore-drill` → backend pointed at it → health → full pipeline → row-count comparison → record → branch deleted. Rollback: Netlify deploy list → publish previous; Railway deployments → redeploy previous; `version` in health confirms.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-088

- [FEAT-088](FEAT-088-Interim-Staging-And-Production-Deployment.md) Interim staging and production deployment (the environments being backed up and rolled back).

## Database Impact

- Tables read by the dump: all tables of the production database.
- Tables written on the `restore-drill` branch only: all (restore) plus derived tables rewritten by `run-pipeline --scope all` (`epochs`, `processed_sessions`, `day_ledger`, `baselines` unchanged when frozen, `scores`, `cusum_state`, `alerts` by natural key, `data_alerts`, `pipeline_runs`).
- Production tables are not modified by the drill.

## API Impact

- Consumed: `GET /api/v1/health` on the restored backend; no endpoint added.

## Frontend Impact

None in code; rollback rehearsal republishes a previous Netlify deploy.

## Analytics Impact

- Full pipeline re-run after restore; frozen baselines must be reproduced (DEP-087, ASM-07). No algorithm change.

## Security Requirements

- Dumps encrypted at rest, stored only on approved storage, never on GitHub or personal devices (DEP-096, DEP-098, DB-054).
- Restore as `echowell_migrator` with `--no-owner`; the backend on the drill branch uses the app role.
- Neon connection strings for the drill branch used only from the operator workstation; never stored in GitHub.

## Error Handling

- A failed restore or mismatching row counts is recorded as a failed drill with the cause, fixed, and repeated before 15 Nov 2026.
- Rollback rehearsal over 10 minutes is recorded as a failure of DEP-085 with the measured time and the corrective action.
- After a real data-damage incident follow the 60-minute procedure of TRD 15 §4.12 and open an `incident` issue.

## Logging Requirements

- The `run-pipeline` re-run writes `pipeline_runs` and `pipeline.run.started` / `pipeline.run.finished` audit rows on the drill branch.
- The drill and rehearsal records in `docs/deployment.md` contain timestamps, counts and outcomes only (no data, no secrets).

## Testing Requirements

- Demo/inspection tests: AC-DEP-06 (failing healthcheck keeps previous deployment), AC-DEP-07 (rollback ≤ 10 min), AC-DEP-08 (restore drill with matching counts).
- Automated: TST-050 (two full rebuilds identical) and DEP-087 rebuild reproduction are covered by existing integration tests; `pytest tests/validation -q` on the deployed SHA during the drill (SEC-162).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-089-AC-01 | A deliberately failing healthcheck deployment on staging leaves the previous deployment serving requests (health `version` unchanged). | AC-DEP-06, DEP-041 |
| FEAT-089-AC-02 | Rollback rehearsal restores the previous frontend and backend within 10 minutes, with the measured time recorded. | AC-DEP-07, DEP-085 |
| FEAT-089-AC-03 | The restore drill is completed and documented before 15 Nov 2026 with matching `raw_sessions` and `alerts` row counts and a healthy `GET /api/v1/health` on the restored branch. | AC-DEP-08, DEP-097 |
| FEAT-089-AC-04 | `docs/deployment.md` records the Neon restore window in force, the weekly dump schedule and storage location class, and the rollback table. | DEP-095, DEP-096 |
| FEAT-089-AC-05 | `git ls-files | grep -Ei '\.(dump|sql\.gz|backup)$'` returns nothing and no workflow uploads a dump artifact. | DEP-098 |

## Definition of Done

- All FEAT-089 acceptance criteria pass; evidence linked from the deployment checklist.
- Temporary Neon branches deleted within 7 days (TPS-031).
- Batch report entry (AGT-022).

## Implementation Notes

- PITR restore: Neon console → project `echowell` → branch `main` → Restore → timestamp (UTC) → verify `SELECT max(received_at) FROM raw_sessions` → redeploy the matching backend → `run-pipeline --scope all` (TRD 15 §4.13).
- TRD differences to report: DEP-097 compares `raw_sessions` and `alerts` and records in `docs/deployment.md`; DB-051 compares `raw_sessions` and `audit_logs`, runs a schema diff and records in `docs/database_design.md`; SEC-162 asks for health plus R01–R10. The drill above performs the union of these checks and records the result in both files.
- "Approved storage" for interim dumps depends on OQ-01 (open); until it is answered, use storage the PI designates for the study's research data and record the decision.
