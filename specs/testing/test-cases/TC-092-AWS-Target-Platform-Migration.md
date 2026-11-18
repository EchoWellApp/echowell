# AWS target platform migration (go-live platform)

## Feature Description

Status: Not Started — these test cases are written from the feature file and run only once the feature is built (BACKLOG.md §10).

FEAT-092 moves EchoWell from the interim Netlify + Render + Neon stack to its target production platform on AWS under an AWS Business Associate Addendum: Amplify Hosting (frontend), App Runner from ECR with the same `backend/Dockerfile` image, RDS for PostgreSQL 16 with a KMS customer-managed key, Secrets Manager, CloudWatch Logs and alarms with SNS, and EventBridge Scheduler (or an ECS scheduled task) for the nightly run. The cut-over follows DEP-117 steps (1)–(7) with deployment-configuration changes only (no source change in `frontend/`, `backend/` or `analytics/`), credentials created anew and no data migrated. AWS is the only platform on which EchoWell may go live with real resident data. Gate: OQ-07 (AWS budget approval and account ownership) answered and recorded in TRD 24, the BAA accepted, FEAT-091 complete.

Cases marked **Hosted** run against the AWS environment with placeholders `<AWS_API_BASE_URL>` (App Runner origin plus `/api/v1`) and `<AWS_FRONTEND_URL>` (Amplify production domain). The cases inspect settings and records; they never change the interim Render, Netlify or Neon deployment while it is the active platform (TRD 24 D-170).

## Preconditions

- OQ-07 answered and recorded in TRD 24; AWS account owned by UND (or a UND-managed member account); BAA accepted in AWS Artifact.
- Tester has read-only IAM Identity Center access (with MFA) to the AWS console: RDS, KMS, Secrets Manager, App Runner, ECR, Amplify, CloudWatch, EventBridge, SNS, IAM, CloudTrail.
- The cut-over PR is merged and its number known; the GitHub repository variables point to the AWS URLs.
- Read-only `psql` access to RDS from inside the VPC (bastion or session approved by the DevOps owner), `sslmode=require`.
- `docs/reports/DEPLOYMENT_REPORT.md` contains the AWS cut-over and go-live record; `specs/backlog/DEPLOYMENT_CHECKLIST.md` section N is being filled.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-092-01 | Cut-over PR changes no file under `frontend/`, `backend/` or `analytics/` | High | Documentation |
| TC-092-02 | Same image and configuration contract run on AWS (PORT, three database URLs, PostgreSQL 16) | High | Positive |
| TC-092-03 | RDS settings: PostgreSQL 16, KMS CMK, `rds.force_ssl = 1`, private, backups ≥ 14 days, deletion protection | High | Hosted |
| TC-092-04 | Secrets are in Secrets Manager with TRD 21 names; migrator URL only in the migration task | High | Security |
| TC-092-05 | BAA accepted and every live-data-path service on the HIPAA Eligible Services Reference | High | Hosted |
| TC-092-06 | DEP-081 smoke tests pass against the AWS URLs before any device is re-pointed | High | Hosted |
| TC-092-07 | First night after cut-over records exactly one `nightly` run | High | Hosted |
| TC-092-08 | CloudWatch log groups have 90-day retention and KMS; health and 5xx alarms notify via SNS | High | Hosted |
| TC-092-09 | First real resident record is ingested on AWS only, after the verifications and the SEC-005 sign-off | High | Hosted |
| TC-092-10 | AWS restore drill is recorded before go-live with healthy health and passing R01–R10 | High | Hosted |
| TC-092-11 | Network, TLS 1.2+, MFA, no long-lived keys and OIDC for GitHub Actions | High | Security |
| TC-092-12 | Production refuses `test_v0_1` and PIPELINE_AS_OF; DATABASE_READONLY_URL and SENTRY_DSN unset unless approved | High | Negative |
| TC-092-13 | Cut-over steps follow DEP-117 order; interim stack read-only 14 days, then deleted | Medium | Documentation |
| TC-092-14 | Smoke failure on AWS keeps devices on the interim stack; no new workflow file is added | Medium | Negative |

### TC-092-01 Cut-over PR changes no file under `frontend/`, `backend/` or `analytics/`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `gh pr view <cut-over PR> --json files --jq '.files[].path'` | List of changed files |
| 2 | `gh pr view <cut-over PR> --json files --jq '.files[].path' \| grep -E '^(frontend\|backend\|analytics)/'; echo "exit=$?"` | No output; `exit=1` |
| 3 | `git diff --stat <merge>^1 <merge>` | Only workflow files, documentation, infrastructure settings or environment templates |

### TC-092-02 Same image and configuration contract run on AWS (PORT, three database URLs, PostgreSQL 16)

| Step | Action | Expected Result |
|---|---|---|
| 1 | In CI before cut-over, run the backend container against `postgres:16` with `sslmode=require` (ARC-094 verification) | Container starts; `GET /api/v1/health` 200 with `database` `ok` |
| 2 | App Runner service `echowell-backend-production` → Configuration | Image from ECR repository `echowell-backend` built from `backend/Dockerfile`; port 8000 via `PORT`; health check path `/api/v1/health`; 1 vCPU / 2 GB; min 1 / max 1 instance; VPC connector to the RDS private subnets |
| 3 | `curl -s "<AWS_API_BASE_URL>/health"` | 200; `version` = the `main` commit deployed (the same SHA as the last interim release or the chosen cut-over commit) |
| 4 | Amplify app → Build settings | App root `frontend`, build `npm ci && npm run build`, Node 20; variables `NEXT_PUBLIC_API_BASE_URL` (App Runner origin) and `NEXT_PUBLIC_APP_ENV` only |

### TC-092-03 RDS settings: PostgreSQL 16, KMS CMK, `rds.force_ssl = 1`, private, backups ≥ 14 days, deletion protection

| Step | Action | Expected Result |
|---|---|---|
| 1 | RDS → production instance → Configuration | Engine PostgreSQL 16.x; instance class `db.t4g.small` (staging `db.t4g.micro`) |
| 2 | Storage → Encryption | Enabled with KMS key `alias/echowell-rds` (customer managed) |
| 3 | Parameter group | `rds.force_ssl` = `1` |
| 4 | Connectivity | Publicly accessible: No; subnets in 2 Availability Zones; security group inbound 5432 only from the App Runner VPC connector security group |
| 5 | Maintenance & backups | Automated backup retention ≥ 14 days; deletion protection Enabled |
| 6 | Record in `DEPLOYMENT_CHECKLIST.md` N.03 | Evidence filled |

### TC-092-04 Secrets are in Secrets Manager with TRD 21 names; migrator URL only in the migration task

| Step | Action | Expected Result |
|---|---|---|
| 1 | Secrets Manager → list | `echowell/production/DATABASE_URL`, `echowell/production/DATABASE_MIGRATION_URL`, `echowell/production/JWT_SECRET`, `echowell/production/SENTRY_DSN`, encrypted with `alias/echowell-secrets` |
| 2 | App Runner → environment configuration | `DATABASE_URL`, `JWT_SECRET` (and `SENTRY_DSN` only if approved) injected from Secrets Manager; no `DATABASE_MIGRATION_URL`; no `DATABASE_READONLY_URL` |
| 3 | One-off ECS migration task definition | Only it receives `DATABASE_MIGRATION_URL`; command `alembic upgrade head` |
| 4 | Amplify environment variables and the ECR image (`docker history`, `env`) | No secret value |
| 5 | RDS (read-only): `SELECT rolname FROM pg_roles WHERE rolname LIKE 'echowell%' ORDER BY 1;` and read `docs/deployment.md` "Research-data governance" | Roles `echowell_app`, `echowell_migrator`, `echowell_readonly` and their login roles exist; exports are made only via `echowell_readonly` by IRB-listed personnel from AWS (SEC-182) |

### TC-092-05 BAA accepted and every live-data-path service on the HIPAA Eligible Services Reference

| Step | Action | Expected Result |
|---|---|---|
| 1 | AWS Artifact → Agreements | AWS BAA status Accepted for the account, with date |
| 2 | Compare Amplify, App Runner, ECR, RDS, KMS, Secrets Manager, CloudWatch, EventBridge, SNS with the current AWS HIPAA Eligible Services Reference (checked at cut-over time) | Each listed; any unlisted service removed from the live-data path and recorded |
| 3 | `DEPLOYMENT_CHECKLIST.md` N.02 | Evidence filled with the check date |

### TC-092-06 DEP-081 smoke tests pass against the AWS URLs before any device is re-pointed

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SMOKE_ENV=production SMOKE_API_BASE_URL=<AWS_API_BASE_URL> SMOKE_FRONTEND_URL=<AWS_FRONTEND_URL> SMOKE_EXPECTED_SHA=<cut-over SHA> pytest -p no:randomly tests/smoke -m "smoke and not authenticated" -rs` | 0 failed; no test skipped for SEC-065 (both origins HTTPS) |
| 2 | Check the results of `test_production_smoke.py` a–f and `test_tls.py` | All passed: health ok, `/login` 200 over HTTPS, `/residents` 401 RFC 7807, `POST /sessions` 401, HSTS and redirect on both origins, `/audio` 404, TLS 1.1 refused and TLS 1.2 accepted |
| 3 | Compare the time of step 1 with the device re-pointing time in the cut-over record | Smoke pass precedes re-pointing |

### TC-092-07 First night after cut-over records exactly one `nightly` run

| Step | Action | Expected Result |
|---|---|---|
| 1 | EventBridge → Schedules | Schedule `cron(0 2 * * ? *)`, time zone America/Chicago, target `POST <AWS_API_BASE_URL>/pipeline/run` with an `X-API-Key` of scope `pipeline:run` (or an ECS scheduled task running `python -m backend.jobs.nightly_run`) |
| 2 | Morning after the first night, RDS (read-only): `SELECT (started_at AT TIME ZONE 'America/Chicago')::date AS night, count(*), max(status::text) FROM pipeline_runs WHERE trigger = 'nightly' GROUP BY 1 ORDER BY 1 DESC LIMIT 1;` | One row for that night with count `1` and status `succeeded` |
| 3 | Search CloudWatch Logs for `nightly_run_missing` | No ERROR for that night |

### TC-092-08 CloudWatch log groups have 90-day retention and KMS; health and 5xx alarms notify via SNS

| Step | Action | Expected Result |
|---|---|---|
| 1 | CloudWatch → Log groups for App Runner | Retention 90 days; KMS key associated; JSON log lines unchanged (fields of TRD 17) |
| 2 | CloudWatch → Alarms | An alarm on health-check failure and an alarm on 5xx rate > 5 % over 10 minutes; RDS CPU and storage alarms |
| 3 | Alarm actions | SNS topic with an e-mail subscription of the DevOps owner (confirmed) |
| 4 | Use "Set alarm state" (test) on the 5xx alarm, or wait for a natural event | DevOps owner receives the SNS e-mail |
| 5 | CloudTrail → Trails | Trail in all regions writing to an SSE-KMS bucket |

### TC-092-09 First real resident record is ingested on AWS only, after the verifications and the SEC-005 sign-off

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read `DEPLOYMENT_CHECKLIST.md` N.13 | Item "hosting approved for PHI-derived data (AWS)" signed by the PI and UND IT with a date S |
| 2 | Read the go-live record in `DEPLOYMENT_REPORT.md` | DEP-112, DEP-113, DEP-114 and DEP-117 verified with dates ≤ S |
| 3 | RDS (read-only): `SELECT min(r.received_at) FROM raw_sessions r WHERE r.resident_code !~ '^T';` | Timestamp ≥ S |
| 4 | Interim Neon (if still present, read-only): `SELECT count(*) FROM residents WHERE resident_code !~ '^(R0[1-9]\|R10\|T.*)$';` | `0` |

### TC-092-10 AWS restore drill is recorded before go-live with healthy health and passing R01–R10

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read the AWS drill record in `docs/deployment.md` | Restore of a snapshot or point in time to a new RDS instance, date before S (TC-092-09) |
| 2 | Read its results | `GET /api/v1/health` against a backend on the restored instance returned 200 with `database` `ok`; `pytest tests/validation -q` on the deployed SHA passed |
| 3 | Check PITR window and targets | PITR ≥ 7 days; RPO ≤ 24 h and RTO ≤ 8 working hours stated; next drill due within 6 months |

### TC-092-11 Network, TLS 1.2+, MFA, no long-lived keys and OIDC for GitHub Actions

| Step | Action | Expected Result |
|---|---|---|
| 1 | IAM → Users → Access keys | No active long-lived access keys for people or CI |
| 2 | IAM Identity Center → users | MFA required; root account MFA enabled |
| 3 | `grep -n "id-token: write\|configure-aws-credentials\|role-to-assume" .github/workflows/deploy-production.yml` | The AWS deploy job assumes a role through OIDC; no AWS access key secret |
| 4 | GitHub → environment `production` secrets | No `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` |
| 5 | `openssl s_client -connect <App Runner host>:443 -tls1_1 </dev/null` | Handshake fails; with `-tls1_2` it succeeds |
| 6 | `curl -sI "<AWS_FRONTEND_URL>/login" \| grep -i content-security-policy` | Header present with a `'nonce-…'` source in `script-src` (SEC-075) and `connect-src` naming the App Runner origin |

### TC-092-12 Production refuses `test_v0_1` and PIPELINE_AS_OF; DATABASE_READONLY_URL and SENTRY_DSN unset unless approved

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read the App Runner environment | `APP_ENV=production`, `PIPELINE_PROFILE=production`, no `PIPELINE_AS_OF`, no `DATABASE_READONLY_URL`; `SENTRY_DSN` empty unless `DEPLOYMENT_CHECKLIST.md` N.11 records the approval of the project coordinator and UND IT |
| 2 | Locally: `docker compose run --rm -e APP_ENV=production -e PIPELINE_PROFILE=test_v0_1 backend; echo "exit=$?"` | `exit=1`; log `startup_config_invalid` naming `PIPELINE_PROFILE` |
| 3 | Locally with `PIPELINE_AS_OF=2026-10-30T15:00:00-05:00` and `APP_ENV=production` | `exit=1`; `PIPELINE_AS_OF` "must be empty when APP_ENV=production" |

### TC-092-13 Cut-over steps follow DEP-117 order; interim stack read-only 14 days, then deleted

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read the cut-over record in `DEPLOYMENT_REPORT.md` | Steps (1) provision, (2) deploy the same `main` commit, (3) extensions/timezone/roles then `alembic upgrade head`, (4) `bootstrap` and new users and keys, (5) smoke, (6) re-point devices, (7) interim read-only, each with a timestamp in this order |
| 2 | RDS (read-only): `SELECT action, count(*) FROM audit_logs WHERE action IN ('user.created','api_key.created') GROUP BY action;` | Both present (credentials created anew) |
| 3 | Fourteen days after step (6) | Record shows the Neon project and Render services deleted no earlier than 14 days after re-pointing; no interim data migrated |

### TC-092-14 Smoke failure on AWS keeps devices on the interim stack; no new workflow file is added

| Step | Action | Expected Result |
|---|---|---|
| 1 | If TC-092-06 fails | Devices are not re-pointed; the cut-over record states the failure; the interim stack remains the active demo platform |
| 2 | `ls .github/workflows/` | Still exactly `ci.yml`, `deploy-production.yml`, `deploy-staging.yml`, `e2e.yml`, `uptime.yml` (the OIDC job is inside `deploy-production.yml`) |
| 3 | If the migration task fails | App Runner deployment of the new version is not started (migrations before traffic) |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET <AWS_API_BASE_URL>/health` | 200; `status` `ok`; `database` `ok`; `version` = deployed SHA |
| 2 | `GET <AWS_API_BASE_URL>/residents` without token | 401, RFC 7807 body |
| 3 | `POST <AWS_API_BASE_URL>/sessions` without `X-API-Key` | 401 |
| 4 | `POST <AWS_API_BASE_URL>/pipeline/run` with the `pipeline:run` key twice in one night | First: run recorded with `trigger` `nightly`; second: 202 with the existing run id (D-70) |
| 5 | `GET <AWS_API_BASE_URL>/audio` | 404 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT version_num FROM alembic_version;` on RDS | Equals the repository head at the cut-over commit |
| 2 | `SHOW ssl;` and `SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid();` | `on`; `t` |
| 3 | `SELECT extname FROM pg_extension ORDER BY 1;` | Includes `btree_gist` and `pgcrypto` |
| 4 | `SHOW timezone;` | `UTC` |
| 5 | Nightly run count per night (TC-092-07) | 1 |
| 6 | `SELECT count(*) FROM ingest_batches WHERE source = 'seed';` | 0 |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Cut-over PR touching `backend/` (TC-092-01) | Rejected in review; case fails |
| 2 | Production configuration with `test_v0_1` or PIPELINE_AS_OF (TC-092-12) | Exit 1, `startup_config_invalid` |
| 3 | TLS 1.1 handshake (TC-092-11) | Refused |
| 4 | Second nightly trigger in one night (API Validation step 4) | 202 with the existing run id; no second run |
| 5 | Smoke failure on AWS (TC-092-14) | Devices stay on the interim stack |
| 6 | Real record before SEC-005 sign-off (TC-092-09) | Not present |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-092-AC-01 | Cut-over commit changes no file under `frontend/`, `backend/` or `analytics/` | TC-092-01, TC-092-02 |
| FEAT-092-AC-02 | RDS shows PostgreSQL 16, KMS CMK, `rds.force_ssl = 1`, not public, backups ≥ 14 days, deletion protection | TC-092-03 |
| FEAT-092-AC-03 | DEP-081 smoke tests pass against the AWS URLs before any device is re-pointed | TC-092-06, TC-092-14 |
| FEAT-092-AC-04 | A `nightly` run is recorded on the first night and no second nightly run starts for that local date | TC-092-07 |
| FEAT-092-AC-05 | Log groups 90-day retention with KMS; health and 5xx alarms with SNS e-mail target | TC-092-08 |
| FEAT-092-AC-06 | First real resident record on AWS only, after DEP-112..DEP-114 and DEP-117 and the SEC-005 sign-off | TC-092-09, TC-092-05, TC-092-04 |
| FEAT-092-AC-07 | AWS restore drill recorded before go-live with healthy health and passing R01–R10 | TC-092-10 |

## Test Data Requirements

- No interim data is migrated. Before go-live AWS holds only `bootstrap` rows, newly created users and API keys and, if used, `T`-prefixed demo IDs.
- The first real resident record exists only after the SEC-005 sign-off; test cases read its timestamp, never its content.
- Placeholders `<AWS_API_BASE_URL>`, `<AWS_FRONTEND_URL>`, `<cut-over PR>`, `<cut-over SHA>`; AWS identifiers recorded in the deployment report, never credentials.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| ARC-094, NFR-093 | FEAT-092 | TC-092-01 |
| DEP-110, DEP-111, ARC-090..ARC-093, NFR-091, NFR-092, SEC-006 | FEAT-092 | TC-092-02 |
| DEP-112, SEC-061, SEC-161, SEC-063 | FEAT-092 | TC-092-03 |
| DEP-113, NFR-094, SEC-116 | FEAT-092 | TC-092-04, TC-092-12 |
| DEP-114, TPS-070 | FEAT-092 | TC-092-05 |
| DEP-117, AC-DEP-11 | FEAT-092 | TC-092-06, TC-092-13, TC-092-14 |
| DEP-116, D-47, D-70 | FEAT-092 | TC-092-07 |
| DEP-115, LOG-121 | FEAT-092 | TC-092-08 |
| DEP-118, TPS-003, SEC-002, SEC-005 | FEAT-092 | TC-092-09 |
| NFR-024, NFR-025, SEC-162, DB-051 | FEAT-092 | TC-092-10 |
| TPS-071, TPS-072, SEC-060, SEC-075 | FEAT-092 | TC-092-11 |
| TPS-061, SEC-127, AGT-015 | FEAT-092 | TC-092-12 |
| SEC-182 | FEAT-092 | TC-092-04 |
| FEAT-092-FR-01..FEAT-092-FR-15 | FEAT-092 | TC-092-01..TC-092-14 |
