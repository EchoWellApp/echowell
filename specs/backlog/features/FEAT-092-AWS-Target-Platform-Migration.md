# FEAT-092 AWS target platform migration (go-live platform)

| Field | Value |
|---|---|
| Epic | DevOps & Deployment |
| Build phase | Post-MVP (TRD 25) |
| Priority | P2 |
| Complexity | High |
| MVP status | Future |
| Dependencies | FEAT-091 |
| Status | Not Started |
| Gate | TRD 25 |

## Purpose

Move EchoWell from the interim Netlify + Railway + Neon stack to its target production platform on AWS (Amplify, App Runner from ECR, RDS for PostgreSQL 16 with a KMS customer-managed key, Secrets Manager, CloudWatch Logs and alarms, EventBridge Scheduler for the nightly run) under an AWS Business Associate Addendum, following the DEP-117 cut-over steps with deployment-configuration changes only. AWS is the only platform on which EchoWell may go live with real resident data; this feature is the go-live path.

## Business Context

- D-27 / D-OWNER-3: AWS is the target production platform; live feature data is treated as potentially PHI-derived (TLS 1.2+, KMS encryption at rest, least privilege, audit logging, no PII in logs).
- D-28 / D-OWNER-4, AGT-014, DEP-118, TPS-003, SEC-002: no real resident data anywhere until AWS is approved; go-live only on AWS.
- BR-17 and SRC-01 "Future AWS Migration": portability with "no significant application code changes" (ARC-094, NFR-093).
- BR-02 / BR-16: AWS backups with PITR ≥ 7 days, RPO ≤ 24 h, RTO ≤ 8 working hours, restore drill before go-live (NFR-024, NFR-025, D-60).

## Referenced TRDs

- TRD 15 DEP-110..DEP-117, DEP-118, §4.16 target configuration and mapping tables, AC-DEP-11.
- TRD 22 TPS-003, TPS-061, TPS-070, TPS-071, TPS-072, AWS section.
- TRD 01 ARC-090, ARC-091, ARC-092, ARC-093, ARC-094.
- TRD 03 NFR-024, NFR-025, NFR-090..NFR-094.
- TRD 12 SEC-002, SEC-005, SEC-006, SEC-061, SEC-063, SEC-075, SEC-116, SEC-161, SEC-162, SEC-182.
- TRD 17 LOG-121, DEP-115 alarms (via TRD 15).
- TRD 16 §2 (AWS OIDC deploy job added only at cut-over), §9 OQ-07.
- TRD 21 §4.7 "production — AWS target" column.
- TRD 06 DB-050, DB-051, DB-052.
- TRD 24 OQ-07 (gate), OQ-01, D-27, D-28, D-47, D-60, D-65, D-70, RSK-14, RSK-15.

## Scope

Decided by the TRDs (implementable once the gate opens):

- Account: UND-owned AWS account (or UND-managed organisation member account), BAA accepted in AWS Artifact before any live data, root MFA, IAM Identity Center users with MFA, no long-lived IAM user keys, CloudTrail in all regions with an SSE-KMS bucket.
- Frontend: Amplify Hosting app on `EchoWellApp/echowell`, app root `frontend`, build `npm ci && npm run build`, Node 20, branches `main` → production and `staging` → staging, variables `NEXT_PUBLIC_API_BASE_URL` (App Runner origin) and `NEXT_PUBLIC_APP_ENV`.
- Backend: ECR repository `echowell-backend` (scan on push, KMS), App Runner service `echowell-backend-production` from the same `backend/Dockerfile` image, port 8000 via PORT, health check `/api/v1/health`, 1 vCPU / 2 GB, 1 instance, VPC connector to the RDS private subnets.
- Database: RDS for PostgreSQL 16 (`db.t4g.micro` staging, `db.t4g.small` production), KMS key `alias/echowell-rds`, not publicly accessible, private subnets in 2 AZs, `rds.force_ssl = 1`, automated backups 14 days, deletion protection; master user runs the extension, timezone and role provisioning (D-72).
- Secrets: Secrets Manager `echowell/production/DATABASE_URL`, `.../DATABASE_MIGRATION_URL`, `.../JWT_SECRET`, `.../SENTRY_DSN` (KMS `alias/echowell-secrets`), injected with the TRD 21 names; DATABASE_MIGRATION_URL only into the one-off ECS migration task running `alembic upgrade head`; DATABASE_READONLY_URL not set in production.
- Logs and monitoring: CloudWatch Logs (JSON unchanged) with 90-day retention and KMS; alarms on health-check failure and 5xx rate > 5 % over 10 minutes, RDS CPU and storage; SNS topic to the DevOps owner.
- Nightly: EventBridge Scheduler `cron(0 2 * * ? *)` America/Chicago calling `POST /api/v1/pipeline/run` with an API key of scope `pipeline:run` (recorded as trigger `nightly` with the once-per-night dedupe), or an ECS scheduled task running `python -m backend.jobs.nightly_run`.
- Network: only App Runner and Amplify public; RDS security group allows 5432 only from the App Runner VPC connector.
- Cut-over (DEP-117): (1) provision; (2) deploy the same `main` commit to Amplify and App Runner; (3) extensions, timezone, roles as RDS master, then `alembic upgrade head` (one-off task); (4) `bootstrap`, users and API keys created anew; (5) DEP-081 smoke tests against AWS URLs; (6) re-point Team 1 devices to the App Runner URL; (7) keep the interim stack read-only for 14 days, then delete the Neon project and Railway services. No data is migrated (interim holds synthetic/test data only).
- Before go-live: every service on the live-data path confirmed on the AWS HIPAA Eligible Services Reference; restore drill on AWS; go-live checklist item signed by the PI and UND IT (SEC-005); Sentry disabled in production unless approved (TPS-061).
- GitHub: `deploy-production.yml` gains an AWS OIDC role; Actions variables point to AWS URLs; smoke tests unchanged.
- Nonce-based CSP adopted with the move to Amplify (SEC-075, D-65).

Blocked on open questions (not to be decided by the implementer):

- OQ-07: AWS budget approval timing and account ownership (UND IT). Nothing in this feature starts until OQ-07 is answered and recorded in TRD 24.
- OQ-01: retention periods and storage location for live data, dumps and logs beyond the stated 90-day log retention and 14-day backups.
- Custom domain names (TRD 15 §2 out of scope pending OQ-07); the AWS frontend origin for CORS (`CORS_ORIGINS` = Amplify production domain) and for CSP `connect-src` is known only after provisioning.

Trigger for starting: OQ-07 answered (budget approved and account owner named) and recorded in TRD 24, the AWS BAA accepted for the account, and FEAT-091 completed.

## Out of Scope

- Any code change in `frontend/`, `backend/` or `analytics/` (ARC-094, NFR-093); if one appears necessary it is a TRD change, not part of this feature.
- Migrating interim data (none is migrated, DEP-117).
- Answering OQ-07 or OQ-01, choosing a custom domain, or setting retention periods.

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-092-FR-01 | No application code shall depend on a Netlify-, Railway- or Neon-specific SDK or API; the backend reads its port only from PORT and its databases only from the three database URLs, so the same image runs on App Runner. | DEP-110, DEP-111, ARC-090, SEC-006 |
| FEAT-092-FR-02 | The migration shall change only deployment configuration (environment variables, workflow files, infrastructure settings); no source change in `frontend/`, `backend/` or `analytics/`. | ARC-094, NFR-093 |
| FEAT-092-FR-03 | The production database shall be RDS for PostgreSQL 16 with KMS customer-managed storage encryption, `rds.force_ssl = 1`, no public access, automated backups ≥ 14 days and deletion protection. | DEP-112, SEC-061, SEC-161, SEC-063 |
| FEAT-092-FR-04 | All production secrets shall be in Secrets Manager (KMS) and injected with TRD 21 names; no secret in Amplify build settings or the image; DATABASE_MIGRATION_URL only in the one-off migration task. | DEP-113, NFR-094, D-58, RSK-15 |
| FEAT-092-FR-05 | The AWS BAA shall be accepted and every service on the live-data path (Amplify, App Runner, ECR, RDS, KMS, Secrets Manager, CloudWatch, EventBridge, SNS) confirmed on the HIPAA Eligible Services Reference before live data; unlisted services removed from the live-data path. | DEP-114, TPS-070 |
| FEAT-092-FR-06 | Application logs shall go to CloudWatch Logs with 90-day retention and KMS encryption; alarms shall notify the DevOps owner on health-check failure and on 5xx rate > 5 % over 10 minutes. | DEP-115, LOG-121 |
| FEAT-092-FR-07 | The nightly run shall be triggered by EventBridge Scheduler at 02:00 America/Chicago calling `POST /api/v1/pipeline/run` with an `X-API-Key` of scope `pipeline:run` (trigger `nightly`, once-per-night dedupe), or by an ECS scheduled task running `python -m backend.jobs.nightly_run`, so the nightly-missing checks see a `nightly` run. | DEP-116, D-47, D-70 |
| FEAT-092-FR-08 | Cut-over shall follow DEP-117 steps (1)–(7) in order, with credentials created anew and the interim stack kept read-only for 14 days before deletion. | DEP-117 |
| FEAT-092-FR-09 | All AWS data stores shall be KMS-encrypted and every endpoint shall require TLS 1.2 or higher; AWS access via IAM Identity Center with MFA, no long-lived IAM user keys, GitHub Actions through OIDC role assumption. | TPS-071, TPS-072, SEC-060 |
| FEAT-092-FR-10 | Go-live (first real resident record) shall happen only on AWS after budget approval, BAA, DEP-112..DEP-114 and DEP-117, with the go-live checklist item signed by the PI and UND IT. | DEP-118, TPS-003, SEC-002, SEC-005 |
| FEAT-092-FR-11 | A restore drill shall run on AWS before go-live and every 6 months; RPO ≤ 24 h and RTO ≤ 8 working hours shall apply with PITR ≥ 7 days. | NFR-024, NFR-025, SEC-162, DB-051, D-60 |
| FEAT-092-FR-12 | Sentry shall be disabled in production (empty SENTRY_DSN) unless the project coordinator and UND IT approve it; CloudWatch is the default error monitoring on AWS. | TPS-061, SEC-127 |
| FEAT-092-FR-13 | Researcher exports outside EchoWell shall be made only via `echowell_readonly` by IRB-listed personnel from the approved AWS platform. | SEC-182 |
| FEAT-092-FR-14 | The frontend shall build and deploy to Amplify without source change, adopting the nonce-based CSP at the move. | NFR-092, ARC-093, SEC-075 |
| FEAT-092-FR-15 | The database layer shall run unchanged on RDS PostgreSQL 16 (standard PostgreSQL features only). | NFR-091, ARC-092 |

## Inputs

- The audited `main` commit (FEAT-091), the backend image, `frontend/`, Alembic migrations, TRD 21 variable names, DEP-081 smoke tests.
- Answer to OQ-07 (budget, account owner), BAA acceptance, AWS account access.

## Outputs

- AWS resources as listed in Scope; infrastructure settings documented in `docs/deployment.md` (AWS section) and `docs/reports/DEPLOYMENT_REPORT.md` (AWS cut-over and go-live record).
- `deploy-production.yml` with an AWS OIDC role and AWS URLs in Actions variables.
- Signed go-live checklist item (SEC-005) in `specs/backlog/DEPLOYMENT_CHECKLIST.md`.

## Data Flow

Team 1 device → HTTPS (TLS 1.2+, X-API-Key) → App Runner (ECR image) → VPC connector → RDS (TLS, `rds.force_ssl`) ; staff browser → Amplify (Next.js) → App Runner; Secrets Manager → App Runner env; App Runner logs → CloudWatch → alarms → SNS e-mail; EventBridge 02:00 America/Chicago → `POST /api/v1/pipeline/run` (pipeline:run key); RDS → automated KMS-encrypted backups and snapshots.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-091

- [FEAT-091](FEAT-091-Final-Implementation-TRD-Traceability-Documentation-And.md) Final implementation and traceability audits (the audited commit that is migrated).

Gate: OQ-07 (AWS budget approval and account ownership).

## Database Impact

- Tables created: the full TRD 20 schema on RDS via `alembic upgrade head` in the one-off migration task; extensions, timezone and roles by the RDS master user (D-72).
- Tables modified: none structurally. Data: `bootstrap` rows, new users and API keys; the first real resident data arrives only after go-live.
- Interim Neon project deleted after 14 read-only days (DEP-117 step 7).

## API Impact

- Exposed: the unchanged TRD 19 API at the App Runner origin.
- Consumed: `POST /api/v1/pipeline/run` by EventBridge with a `pipeline:run` key (if the EventBridge option is chosen); `GET /api/v1/health` by App Runner and smoke tests.

## Frontend Impact

- No source change; Amplify hosting replaces Netlify; per-branch `NEXT_PUBLIC_API_BASE_URL`; header set and nonce CSP configured on Amplify (SEC-075).

## Analytics Impact

None. The pipeline runs unchanged with profile `production` (D-01).

## Security Requirements

- BAA, HIPAA-eligible services only, KMS everywhere, TLS 1.2+, private RDS, least-privilege roles, migrator credential only in the migration task, MFA and no long-lived keys, OIDC for Actions (DEP-112..DEP-114, TPS-070..TPS-072, D-27).
- `test_v0_1` profile and PIPELINE_AS_OF refused in production (AGT-015); DATABASE_READONLY_URL not set in production (SEC-116).

## Error Handling

- Smoke tests against AWS URLs fail → do not re-point devices (DEP-117 step 6); interim stack stays the active demo platform.
- Migration task fails → App Runner deployment not started (migrations before the new version serves traffic, DEP-022, ARC-082).
- Any unconfirmed HIPAA eligibility → that service is removed from the live-data path before go-live (DEP-114).

## Logging Requirements

- JSON logs unchanged (TRD 17) into CloudWatch, 90-day retention, KMS (LOG-121); CloudTrail enabled.
- Audit rows for `bootstrap`-time users (`user.created`) and keys (`api_key.created`); the go-live record lists dates and approvers.

## Testing Requirements

- DEP-081 production smoke tests against the AWS URLs (DEP-117 step 5); SEC-066 TLS check.
- Container run against `postgres:16` with `sslmode=require` (ARC-094 verification) in CI before cut-over.
- AWS restore drill (NFR-025, SEC-162): restore to a new RDS instance, `GET /api/v1/health`, R01–R10 validation on the deployed SHA.
- AC-DEP-11 verification of first real record on AWS only.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-092-AC-01 | The cut-over commit changes no file under `frontend/`, `backend/` or `analytics/` (`git diff --stat` of the migration PR). | ARC-094, NFR-093 |
| FEAT-092-AC-02 | RDS settings show PostgreSQL 16, KMS CMK encryption, `rds.force_ssl = 1`, not publicly accessible, backup retention ≥ 14 days and deletion protection on. | DEP-112 |
| FEAT-092-AC-03 | DEP-081 smoke tests pass against the AWS URLs before any device is re-pointed. | DEP-117 step 5 |
| FEAT-092-AC-04 | A nightly run with trigger `nightly` is recorded in `pipeline_runs` on the first night after cut-over, and no second nightly run starts for that local date. | DEP-116, D-70 |
| FEAT-092-AC-05 | CloudWatch log groups have 90-day retention and KMS encryption; the health and 5xx alarms exist with the SNS e-mail target. | DEP-115, LOG-121 |
| FEAT-092-AC-06 | The first real resident record is ingested on AWS only, after DEP-112..DEP-114 and DEP-117 are verified and the SEC-005 item is signed. | AC-DEP-11, DEP-118, SEC-005 |
| FEAT-092-AC-07 | An AWS restore drill is recorded before go-live with healthy `GET /api/v1/health` and passing R01–R10 validation. | NFR-025, SEC-162 |

## Definition of Done

- OQ-07 answered and recorded; all FEAT-092 acceptance criteria pass; go-live record in `DEPLOYMENT_REPORT.md`.
- Interim Neon project and Railway services deleted after the 14-day read-only period.

## Implementation Notes

- Status of decisions: the AWS architecture, settings and cut-over steps are decided (TRD 15 §4.16, D-27); the start date and account ownership are not (OQ-07); retention beyond the stated values is not (OQ-01).
- App Runner has no cron facility; choose EventBridge with a `pipeline:run` key (preferred in D-47) or an ECS scheduled task.
- Re-check AWS HIPAA eligibility at cut-over time rather than relying on earlier lists (DEP-114).
- TRD 16 CIC-002 fixes the five workflow files; the OIDC deploy job is added inside `deploy-production.yml`, not as a new workflow (TRD 16 §2, §9).
