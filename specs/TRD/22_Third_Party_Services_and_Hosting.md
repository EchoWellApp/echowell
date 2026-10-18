# 22 Third-Party Services and Hosting

Document ID: ECHOWELL-TRD-22 · Version 0.1 (draft for review) · Date: 18 October 2026 · Owner: Team 2 · Status: Draft

## 1. Purpose

This document lists every third-party service EchoWell uses or may use, and for each one states its purpose, the
plan or tier, the limits that matter for the MVP, the data it stores, its region, who owns the account, and the exit
or migration path. It distinguishes the **current interim hosting stack** (Netlify + Railway + Neon, used until the
AWS budget is approved) from the **AWS target production platform** (D-OWNER-3), records the owner decision that no
real resident data is ever placed on the interim stack and that go-live happens only on AWS (D-OWNER-4), and lists
the services that are explicitly excluded.

## 2. Scope

**In scope**

- Current interim stack: Netlify, Railway, Neon (with Railway PostgreSQL as alternative).
- Development and delivery: GitHub (repository, Actions, Dependabot, secret scanning).
- Fonts: IBM Plex via `next/font` self-hosting (Google Fonts at build time only).
- Optional: Sentry error tracking.
- AWS target: Amplify Hosting, App Runner, ECR, RDS for PostgreSQL, KMS, Secrets Manager, CloudWatch, EventBridge Scheduler, SNS, CloudTrail, under an AWS BAA.
- Explicit exclusions.

**Out of scope**

- Team 1 services (device connectivity, wake word engine, feature extractor such as openSMILE) — interface only (ASM-05, OQ-07 transport).
- University systems (UND IT identity, storage for backups) — referenced only (OQ-01, OQ-07).

## 3. References

| ID | Reference |
|---|---|
| SRC-01 | Deployment Architecture (Netlify, Railway, Neon or Railway PostgreSQL, GitHub Actions; future AWS Amplify / App Runner / RDS) |
| SRC-12 | TRD Generation Prompt |
| SRC-14 | Team 2 PRD Guide Part B (no LLMs; raw audio never leaves the room) |
| D-OWNER-3 | AWS is target production; interim stack until budget approval; live feature data treated as potentially PHI-derived |
| D-OWNER-4 | OQ-23 closed: no real resident data on the interim stack; go-live only on AWS |
| TRD 12 | Security and Authentication |
| TRD 15 | Deployment and DevOps (procedures, AWS target configuration §4.16) |
| TRD 16 | CI/CD Pipeline |
| TRD 17 | Logging, Monitoring and Error Handling |
| TRD 21 | Environment Configuration |

## 4. Requirements

### 4.1 Service inventory

| Service | Role | Stage | Holds real resident data? |
|---|---|---|---|
| GitHub (org `EchoWellApp`) | Source code, CI/CD (Actions), Dependabot, issues | current + target | Never |
| Netlify | Frontend hosting (Next.js) | current interim | Never (D-OWNER-4) |
| Railway | Backend hosting (FastAPI + analytics) | current interim | Never (D-OWNER-4) |
| Neon | PostgreSQL 16 database | current interim | Never (D-OWNER-4) |
| Railway PostgreSQL | Alternative database if Neon unavailable | contingency | Never (D-OWNER-4) |
| Google Fonts (via `next/font`) | IBM Plex Sans / Mono font files, fetched at build time | current + target | No data |
| Sentry (optional) | Backend exception tracking | optional | Never on interim stack; on AWS only after re-approval (TPS-061) |
| AWS (Amplify, App Runner, ECR, RDS, KMS, Secrets Manager, CloudWatch, EventBridge, SNS, CloudTrail) | Target production platform | target | Yes, after go-live |

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| TPS-001 | EchoWell shall use no third-party service other than those listed in §4.1; adding a service requires a PR updating this TRD, approved by the project coordinator. | Must | BR-16, BR-18 | Inspection |
| TPS-002 | No real resident data (feature records, study IDs of enrolled residents, staff notes about residents, alerts) shall be stored on or transmitted through Netlify, Railway, Neon or Sentry at any time; these services hold only synthetic and team-test data. | Must | D-OWNER-4, RSK-14 | Inspection |
| TPS-003 | EchoWell shall go live (accept real resident data) only on the AWS target platform, after AWS budget approval, acceptance of the AWS BAA, and the checks of TRD 15 DEP-112 to DEP-114 and DEP-117. | Must | D-OWNER-3, D-OWNER-4, OQ-07 | Inspection |
| TPS-004 | All services that store EchoWell data shall be located in the United States (Neon `aws-us-east-1`, Railway US East, AWS `us-east-1`; Netlify serves static/SSR content from its global edge but stores no data). | Must | BR-16 | Inspection |
| TPS-005 | Every service account shall be owned by the project (team-controlled shared mailbox or UND-managed identity), not by an individual's personal account, and shall have at least 2 administrators with multi-factor authentication enabled. | Must | BR-16, OQ-07 | Inspection |
| TPS-006 | The account owner, administrators, plan and the date limits were last verified shall be recorded per service in `docs/deployment.md` (no credentials). | Must | RSK-07 | Inspection |
| TPS-007 | Plan limits below are indicative as of October 2026; at account creation the DevOps owner shall verify them on the provider's pricing page and record the actual values in `docs/deployment.md`. | Must | RSK-07 | Inspection |

### 4.2 Netlify (frontend hosting, current interim)

| Aspect | Specification |
|---|---|
| Purpose | Build and host the Next.js frontend from `frontend/` with `@netlify/plugin-nextjs` (TRD 15 §4.6); deploy previews for PRs; TLS certificates |
| Plan | Free (Starter) |
| Relevant limits | Monthly build-minute / credit allowance and bandwidth allowance of the Free plan; 1 concurrent build; serverless function execution limits for SSR routes. EchoWell's usage (< 25 users, ASM-08) is far below these; the ignore command (TRD 15 DEP-052) saves build minutes. |
| Data stored | Built frontend assets, build logs, NEXT_PUBLIC_* variables (public values only). No resident data, no secrets. |
| Region | Global CDN edge; SSR functions in the Netlify default US region |
| Ownership | Netlify team "EchoWell" owned by the project mailbox; Team 2 DevOps owner + 1 other admin |
| Exit path | AWS Amplify Hosting with the same base directory, build command and variables (TRD 15 §4.16); no code change |

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| TPS-010 | Netlify shall host only the frontend; no Netlify Functions, Forms, Identity, Blobs, Analytics or Edge Functions shall be used by EchoWell code beyond what `@netlify/plugin-nextjs` generates for Next.js routes. | Must | DEP-110, TPS-001 | Inspection |
| TPS-011 | Netlify environment variables shall contain only NEXT_PUBLIC_* values, NODE_VERSION and NEXT_TELEMETRY_DISABLED (TRD 21 §4.5). | Must | BR-16, TRD 21 | Inspection |

### 4.3 Railway (backend hosting, current interim)

| Aspect | Specification |
|---|---|
| Purpose | Build `backend/Dockerfile` and run the FastAPI backend with the analytics engine, plus the Cron Job service `nightly`; environments `staging` and `production`; GitHub integration with "Wait for CI"; TLS edge |
| Plan | Hobby (monthly subscription that includes a usage credit; usage-based above it). Trial credit only for the first days. |
| Relevant limits | Usage billed by vCPU, memory and egress; one always-on small service per environment is expected to stay near the included credit (about USD 5 per environment per month, TRD 15 DEP-100). The nightly run is a separate Railway Cron Job service (`nightly`, TRD 15 DEP-046) billed only while it runs; the backend may use app sleeping to reduce usage (cold start on the first request), except on demo days (TRD 15 DEP-042). Log retention on Hobby is short (about 7 days, TRD 17 §4.10). Team (shared workspace) features may require the Pro plan. |
| Data stored | Container images, environment variables (secrets: DATABASE_URL, DATABASE_MIGRATION_URL, JWT_SECRET, SENTRY_DSN), application logs (IDs only, TRD 17). Synthetic/test data only passes through (D-OWNER-4). |
| Region | US East (Virginia) |
| Ownership | Railway workspace owned by the project mailbox; DevOps owner + 1 other admin; if team membership needs Pro, the upgrade decision follows OQ-07 |
| Exit path | AWS App Runner running the same image from ECR (TRD 15 §4.16, DEP-116 for the nightly run) |

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| TPS-020 | The Railway backend service shall not use Railway-specific APIs or SDKs; only `railway.toml`, environment variables and the PORT convention couple the code to Railway. | Must | DEP-110 | Inspection |
| TPS-021 | Railway usage shall be capped with a usage limit (hard limit) of USD 20 per month for the workspace, with an e-mail alert at USD 10. | Should | RSK-07 | Inspection |

### 4.4 Neon (PostgreSQL, current interim) and Railway PostgreSQL (alternative)

| Aspect | Neon (preferred) | Railway PostgreSQL (alternative) |
|---|---|---|
| Purpose | Managed PostgreSQL 16 for staging (branch `staging`) and interim production (branch `main`) | Same, if Neon becomes unavailable to the team |
| Plan | Free | Included in Railway Hobby usage |
| Relevant limits | Small storage allowance per project (about 0.5 GB on Free; EchoWell synthetic data is < 50 MB); monthly compute allowance; scale-to-zero after about 5 min idle with sub-second to few-second cold start on first query (RSK-07); limited number of branches; short point-in-time restore window on Free (hours, not days) | Volume-backed single instance; backups depend on plan; no branching; database runs as a service with continuous usage |
| Data stored | All EchoWell tables (synthetic/test data only on the interim stack, D-OWNER-4) | Same |
| Encryption | TLS required (`sslmode=require`), provider-managed encryption at rest | TLS via Railway proxy, provider-managed volume encryption per Railway documentation |
| Region | `aws-us-east-1` | US East |
| Ownership | Neon organisation owned by the project mailbox; 2 admins | Railway workspace (as §4.3) |
| Exit path | `pg_dump`/`pg_restore` or fresh Alembic schema to RDS PostgreSQL 16 (TRD 15 DEP-117) | Same |

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| TPS-030 | Neon shall be the interim database provider; Railway PostgreSQL shall be used only if Neon is unavailable, by changing DATABASE_URL and DATABASE_MIGRATION_URL (TRD 15 DEP-035). | Must | SRC-01 | Inspection |
| TPS-031 | The Neon project shall run PostgreSQL 16 in `aws-us-east-1` with branches `main` and `staging` only, plus temporary `pre-<sha>` and `restore-drill` branches deleted within 7 days (TRD 15 DEP-063, DEP-097). | Must | TRD 15 | Inspection |
| TPS-032 | No Neon-specific features (Neon serverless driver, Neon Auth, Data API) shall be used; access is plain PostgreSQL over psycopg 3. | Must | DEP-110 | Inspection |

### 4.5 GitHub and GitHub Actions

| Aspect | Specification |
|---|---|
| Purpose | Monorepo `EchoWellApp/echowell` (public), pull requests, branch protection, Actions CI/CD (TRD 16), Dependabot, secret scanning, issues |
| Plan | GitHub Free organisation |
| Relevant limits | Standard GitHub-hosted runners are free for public repositories; artifact and log retention as configured (TRD 16 §4.10); scheduled workflows in public repositories are disabled after 60 days without repository activity (re-enable `uptime.yml` and `e2e.yml` if this happens) |
| Data stored | Code, synthetic test data, TRDs, CI logs and artifacts (synthetic only), three staging secrets (TRD 16 §4.9) |
| Region | GitHub-managed (US) |
| Ownership | Organisation `EchoWellApp`; ≥ 2 owners with 2FA required for all members |
| Exit path | Repository is portable (git); workflows map to AWS CodeBuild/CodePipeline if ever required, but GitHub Actions remains the CI/CD platform on the AWS target (SRC-01) |

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| TPS-040 | The `EchoWellApp` organisation shall require two-factor authentication for all members. | Must | BR-16 | Inspection |
| TPS-041 | Because the repository is public, nothing in it, its issues, PRs, Actions logs or artifacts shall contain real resident data, secrets or third-party-licensed documents (TRD 18 GIT-073, GIT-080, GIT-093). | Must | BR-16, D-OWNER-1 | Inspection |

### 4.6 Fonts: IBM Plex via `next/font`

| Aspect | Specification |
|---|---|
| Purpose | Design tokens require IBM Plex Sans (body) and IBM Plex Mono (footnotes/captions) (contract §11) |
| Decision | Self-host through `next/font/google` (`IBM_Plex_Sans` weights 400/500/600, `IBM_Plex_Mono` weight 400, subset `latin`, `display: "swap"`). Font files are downloaded once at build time and served from the EchoWell frontend origin. |
| Data stored | None; browsers never contact Google; no user data reaches Google |
| Limits / caveat | Build machines (Netlify, CI, Docker build) need outbound access to Google Fonts at build time; if unavailable, the build falls back to the CSS fallback stack (`system-ui, -apple-system, "Segoe UI", sans-serif` / `ui-monospace, Menlo, monospace`). |
| Exit path | Switch to `next/font/local` with the OFL-licensed IBM Plex files if build-time network access is restricted (e.g. on AWS with no egress); fonts are not committed unless this switch happens (TRD 18 GIT-097) |

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| TPS-050 | The frontend shall load IBM Plex Sans and IBM Plex Mono only through `next/font` self-hosting; no `<link>` to `fonts.googleapis.com` or `fonts.gstatic.com` shall exist in rendered HTML or CSS. | Must | BR-16, contract §11 | Test (E2E asserts no request to Google domains) |
| TPS-051 | The frontend shall make network requests only to its own origin and to NEXT_PUBLIC_API_BASE_URL; a Content-Security-Policy with `default-src 'self'; connect-src 'self' <API origin>; font-src 'self'; img-src 'self' data:; frame-ancestors 'none'` shall enforce this (TRD 12). | Must | BR-16, TRD 12 | Test |

### 4.7 Sentry (optional)

| Aspect | Specification |
|---|---|
| Purpose | Grouping and e-mail notification of backend exceptions (TRD 17 LOG-100) |
| Plan | Developer (free) |
| Relevant limits | Small monthly error-event quota, 1 user, about 30 days of event retention |
| Data stored | Exception type, sanitised message, stack trace, release (GIT_SHA), environment; no request bodies, headers, cookies, query strings, user e-mails or IP addresses (`send_default_pii=False`) |
| Region | Sentry US data region |
| Ownership | Sentry organisation owned by the project mailbox |
| Exit path | Disable by emptying SENTRY_DSN; on AWS use CloudWatch alarms (TRD 15 DEP-115) |

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| TPS-060 | Sentry may be enabled on the interim stack (staging, interim production) because those hold synthetic data only; it shall be backend-only (no browser SDK). | May | TRD 17 LOG-082, LOG-102 | Inspection |
| TPS-061 | Before AWS go-live, Sentry shall be disabled in production (SENTRY_DSN empty) unless the project coordinator and UND IT approve it for PHI-derived data under an appropriate agreement; CloudWatch is the default error monitoring on AWS. | Must | D-OWNER-3, D-OWNER-4 | Inspection |

### 4.8 AWS target production platform

| Service | Purpose | Configuration (TRD 15 §4.16) | Data stored |
|---|---|---|---|
| AWS account + AWS Artifact | Account under UND ownership; BAA acceptance | BAA accepted before any live data; root MFA; IAM Identity Center | — |
| AWS Amplify Hosting | Frontend hosting (Next.js SSR) | app root `frontend`, branches `main`/`staging` | build artifacts, public variables |
| Amazon ECR | Backend image registry | repository `echowell-backend`, scan on push, KMS | images (no data) |
| AWS App Runner | Backend runtime | 1 vCPU / 2 GB, 1 instance, VPC connector, health `/api/v1/health` | none persistent |
| Amazon RDS for PostgreSQL 16 | Database | KMS CMK `alias/echowell-rds`, private subnets, `rds.force_ssl=1`, backups 14 days, deletion protection | all EchoWell data incl. live feature data |
| AWS KMS | Encryption keys | CMKs `alias/echowell-rds`, `alias/echowell-secrets`, `alias/echowell-logs`; key rotation enabled | keys |
| AWS Secrets Manager | Secrets | `echowell/<env>/<VARIABLE>` names of TRD 21 | secrets |
| Amazon CloudWatch | Logs, metrics, alarms | 90-day log retention, KMS, alarms to SNS | application logs (IDs only) |
| Amazon EventBridge Scheduler | Nightly pipeline trigger | 02:00 America/Chicago; calls `POST /api/v1/pipeline/run` with an API key of scope `pipeline:run` (or runs `python -m backend.jobs.nightly_run` as an ECS scheduled task) | none |
| Amazon SNS | Operational alert e-mail | topic `echowell-ops` | none |
| AWS CloudTrail | Account audit trail | all regions, encrypted bucket | API activity |

| Aspect | Specification |
|---|---|
| Plan / cost | Pay-as-you-go funded by the approved AWS budget (OQ-07); indicative monthly order of magnitude for this footprint is tens of US dollars (RDS small instance and App Runner dominate) — to be confirmed with AWS Pricing Calculator in the budget request |
| Region | `us-east-1` |
| Ownership | UND-owned account (OQ-07); team members via IAM Identity Center with least-privilege permission sets |
| Exit path | Standard PostgreSQL and OCI image; portable to any PostgreSQL + container host |

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| TPS-070 | The AWS target shall use only the services in the table above for EchoWell; each shall be confirmed on the AWS HIPAA Eligible Services Reference before go-live (TRD 15 DEP-114). | Must | D-OWNER-3 | Inspection |
| TPS-071 | All AWS data stores (RDS, snapshots, ECR, CloudWatch Logs, Secrets Manager, CloudTrail bucket) shall be encrypted with KMS keys, and all endpoints shall require TLS 1.2 or higher. | Must | D-OWNER-3, BR-16 | Inspection |
| TPS-072 | AWS access shall use IAM Identity Center users with MFA; no long-lived IAM user access keys shall exist; GitHub Actions shall use OIDC role assumption if it needs AWS access. | Must | BR-16 | Inspection |

### 4.9 Explicit exclusions

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| TPS-080 | EchoWell shall not call any large language model API or service (e.g. OpenAI, Anthropic, Google Gemini, AWS Bedrock, Azure OpenAI) at runtime, and shall not include LLM-based features, summaries or chat. | Must | BR-18, SRC-14, contract §2 | Inspection (dependency and code scan) |
| TPS-081 | EchoWell shall not use web analytics, tracking pixels, session replay, advertising or marketing tools (e.g. Google Analytics, Netlify Analytics, Hotjar, Segment) in any environment. | Must | BR-16 | Test (E2E asserts no third-party requests) |
| TPS-082 | EchoWell shall not use any voice, speech-to-text, speaker recognition or audio processing cloud service (e.g. AWS Transcribe, Google Speech-to-Text, Azure Speech, Alexa Voice Service), and shall expose no endpoint that accepts audio. | Must | BR-01, contract §2, OQ-16 | Inspection |
| TPS-083 | EchoWell shall not send e-mail, SMS or push notifications to clinical staff in the MVP (no SendGrid, Twilio, SES for clinical alerts); operational e-mails come only from GitHub and SNS to the team (OQ-06). | Must | OQ-06, TRD 17 LOG-113 | Inspection |
| TPS-084 | EchoWell shall not use third-party authentication providers (Auth0, Clerk, Netlify Identity, Cognito) in the MVP; authentication is built in (TRD 12). | Must | TRD 12 | Inspection |
| TPS-085 | EchoWell shall not load scripts, styles, fonts or images from third-party CDNs in the browser. | Must | BR-16, TPS-051 | Test |
| TPS-086 | ML-as-a-service platforms shall not be used; the MVP pipeline is deterministic robust statistics + CUSUM (contract §2). | Must | BR-18 | Inspection |

## 5. Assumptions

- ASM-03 Single facility (Edgewood): one instance of each service.
- ASM-05 Records arrive via HTTPS POST from Team 1 or CSV upload; the transport service is Team 1's.
- ASM-08 Small usage: free/entry tiers are sufficient for the interim stack.
- D-OWNER-4 The interim stack never holds real resident data, so the absence of a BAA on interim tiers (RSK-14) does not block development or the demo.

## 6. Dependencies

- Project-owned mailbox and organisation accounts (TPS-005) — to be created by the project coordinator before Phase 14B.
- AWS budget approval and UND account provisioning (OQ-07) for §4.8.
- TRD 15 procedures and TRD 21 variables for configuring each service.

## 7. Acceptance Criteria

- AC-TPS-01 `docs/deployment.md` lists, for each service in §4.1 in use, the owner account, two admins with MFA, plan, region and verified limits with a date.
- AC-TPS-02 A Playwright test loading `/residents` and `/residents/R09` records network requests only to the frontend origin and the API origin (no Google, analytics or CDN domains).
- AC-TPS-03 A dependency scan of `backend/requirements.txt` and `frontend/package-lock.json` finds no LLM SDKs (`openai`, `anthropic`, `@google/generative-ai`, `boto3` bedrock usage, `langchain*`), no analytics SDKs and no speech SDKs.
- AC-TPS-04 The interim Neon project contains no resident codes other than `R01`–`R10` (test seed) and `T`-prefixed demo IDs.
- AC-TPS-05 Before the first real resident record is ingested, evidence exists of: AWS BAA accepted, DEP-112 to DEP-114 verified, SENTRY_DSN decision per TPS-061 recorded.
- AC-TPS-06 The OpenAPI document (`docs/api_reference/openapi.json`) contains no path or request body accepting audio content types (`audio/*`, `multipart` audio fields).

## 8. Implementation Notes

- `frontend/app/layout.tsx`: `import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google"`; expose them as CSS variables `--font-sans` and `--font-mono` and reference them in the design tokens.
- Do not add `@sentry/nextjs`; only the Python `sentry-sdk` (optional import guarded by SENTRY_DSN).
- When creating accounts, use the project mailbox as the owner and invite individuals as members; never transfer ownership to a student's personal account, because accounts must survive team changes at semester end.
- Keep a single page in `docs/deployment.md` titled "Service accounts" for TPS-006; it must never contain passwords or tokens.
- Netlify, Railway and Neon offer BAAs only on higher (enterprise/scale) tiers, if at all; that is why D-OWNER-4 forbids real resident data on them (RSK-14). Do not attempt to "upgrade into compliance" without a new owner decision.

## 9. Open Questions

- OQ-07 AWS budget approval timing and account ownership (UND IT) — gates §4.8 and go-live (TPS-003).
- OQ-01 Data retention architecture — determines RDS backup retention beyond 14 days and log retention on AWS.
- OQ-06 Alert delivery — any future notification service must be added here first (TPS-083).
- OQ-16 Smart-home wake phrase vs no-raw-audio rule — TPS-082 excludes cloud voice services on the EchoWell side regardless.

## Revision History

| Version | Date | Description | Author |
|---|---|---|---|
| 0.1 | 18 Oct 2026 | Initial generation from TRD_Generation_Prompt.md | — |
