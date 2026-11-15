# Deployment documentation and readiness checklists

## Feature Description

FEAT-087 (Complete, BACKLOG.md §10) delivers the documents that let a team member deploy, verify, operate and contain incidents without further clarification: `specs/backlog/DEPLOYMENT_CHECKLIST.md`, `specs/backlog/MVP_READINESS_CHECKLIST.md`, `docs/reports/DEPLOYMENT_CONFIGURATION_GUIDE.md`, `docs/reports/CONFIGURATION_VALIDATION_REPORT.md`, and the incident-containment, incident-reporting, research-data-governance and service-ownership sections of `docs/deployment.md`. All cases are document inspections on the checked-out repository, plus one tabletop demo of the containment actions on the local stack.

## Preconditions

- Repository checked out at the commit under test; `grep`, `sed`, `diff` available.
- TRD sources available under `specs/TRD/` (TRD 12, 13, 15, 21, 22, 25).
- For TC-087-08 only: local Compose stack running and seeded (`docker compose up -d --build`, `docker compose exec backend python -m backend.cli seed test_v0_1`), signed in as `admin@example.com` with the local SEED_ADMIN_PASSWORD from `.env`.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-087-01 | The four Phase 9 documents exist at their paths | High | Documentation |
| TC-087-02 | MVP readiness checklist has 15 rows MVP-01..MVP-15 with Table 4.17-A evidence and the acceptance rule | High | Documentation |
| TC-087-03 | Deployment checklist rows cite a source ID and evidence and include the AWS go-live item as not applicable | High | Documentation |
| TC-087-04 | Every TRD 21 §4.2, §4.3 and §4.5 variable appears in the configuration guide | High | Documentation |
| TC-087-05 | Configuration guide reproduces TRD 15 §4.2, §4.9 and §4.10 verbatim | Medium | Documentation |
| TC-087-06 | Configuration validation report has the required pass/fail lines and the no-deployment sentence | High | Documentation |
| TC-087-07 | `docs/deployment.md` contains the five containment actions, the 24-hour reporting rule and the governance rules | High | Documentation |
| TC-087-08 | Containment actions are executable as written (tabletop on the local stack) | Medium | Positive |
| TC-087-09 | Third-party service rules and service ownership are recorded | Medium | Documentation |
| TC-087-10 | Placeholder grep returns nothing | High | Negative |
| TC-087-11 | Documents contain no secret, credential, real data or personal name | High | Security |
| TC-087-12 | Checklist rows cite only TRD IDs that exist | Medium | Negative |

### TC-087-01 The four Phase 9 documents exist at their paths

| Step | Action | Expected Result |
|---|---|---|
| 1 | `ls -l specs/backlog/DEPLOYMENT_CHECKLIST.md specs/backlog/MVP_READINESS_CHECKLIST.md docs/reports/DEPLOYMENT_CONFIGURATION_GUIDE.md docs/reports/CONFIGURATION_VALIDATION_REPORT.md` | Four files listed, each non-empty; exit 0 |
| 2 | Open each file's first line | Titles "# EchoWell Deployment Checklist", "# EchoWell MVP Readiness Checklist", "# EchoWell Deployment Configuration Guide", "# EchoWell Configuration Validation Report" |

### TC-087-02 MVP readiness checklist has 15 rows MVP-01..MVP-15 with Table 4.17-A evidence and the acceptance rule

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -c "^| MVP-" specs/backlog/MVP_READINESS_CHECKLIST.md` | `15` |
| 2 | `grep -o "^| MVP-[0-9]*" specs/backlog/MVP_READINESS_CHECKLIST.md \| tr -d '\| ' \| tr '\n' ' '` | `MVP-01 MVP-02 … MVP-15`, each once, in order |
| 3 | Compare the Evidence column of each MVP row with TRD 13 Table 4.17-A | Each row names the evidence of Table 4.17-A (e.g. MVP-01 `ALGORITHM_VALIDATION_REPORT.md` "Overall: PASS"; MVP-08 TST-152 and `DEPLOYMENT_REPORT.md`) |
| 4 | Read section M intro | States "The MVP is accepted only when every MVP row passes on the release candidate commit (TST-170, AC-TST-10)." |
| 5 | Check that AC-TST-01..AC-TST-13 appear in section M | 13 rows AC-TST-01..AC-TST-13 |
| 6 | Check the column headers of section M | `ID`, `Criterion`, `Source`, `Evidence`, `Status` |

### TC-087-03 Deployment checklist rows cite a source ID and evidence and include the AWS go-live item as not applicable

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `specs/backlog/DEPLOYMENT_CHECKLIST.md` sections A–N | Every step row has a non-empty Source column with a TRD ID |
| 2 | Open section O | Rows for AC-DEP-01..AC-DEP-11, AC-CIC-01..AC-CIC-10, the DEP-080 and DEP-081 smoke checks, AC-ENV-01..AC-ENV-09 and the TRD 25 §4.6 Phase 10 definition of done, each with Evidence and Status |
| 3 | Find row N.13 | Step "Go-live sign-off: item "hosting approved for PHI-derived data (AWS)" signed by the PI and UND IT before any live device is pointed at the API", Source `SEC-005, AC-SEC-11, DEP-118`, Status `[n/a]` |
| 4 | Read the section N heading text | States the rows are not applicable to the interim deployment and run only for FEAT-092 after OQ-07 |

### TC-087-04 Every TRD 21 §4.2, §4.3 and §4.5 variable appears in the configuration guide

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `for v in $(sed -n '/^### 4.2/,/^### 4.4/p;/^### 4.5/,/^### 4.6/p' specs/TRD/21_Environment_Configuration_Spec.md \| grep -oE '^\| \`[A-Z][A-Z0-9_]+\`' \| tr -d '\|\` '); do grep -q "$v" docs/reports/DEPLOYMENT_CONFIGURATION_GUIDE.md \|\| echo "MISSING $v"; done` | No `MISSING` line |
| 2 | Open guide §7 "Environment-variable matrix" | Each variable has a per-environment value source (local, test, staging, production) |
| 3 | Open `docs/deployment.md` "Configuration deviations from the TRD 21 §4.7 matrix" | Every deviation has Variable, Environment, Deviation and Reason (e.g. SENTRY_DSN local/test ignored with WARNING `sentry_dsn_ignored`) |

### TC-087-05 Configuration guide reproduces TRD 15 §4.2, §4.9 and §4.10 verbatim

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open guide §2 "Local procedure (TRD 15 §4.2, verbatim)" and TRD 15 §4.2 side by side | Steps 1–9 are word-for-word identical |
| 2 | Compare guide §8 with TRD 15 §4.9 | Staging deploy steps 1–6 identical; step 2 is "Merge the PR into `main`." |
| 3 | Compare guide §9 with TRD 15 §4.10 | Production release steps 1–5 identical, including the manual `deploy-production.yml` dispatch and the required reviewer |
| 4 | Check guide sections for smoke tests, rollback, backup and restore, demo fallback | §10 smoke tests, §11 rollback, §12 backup and restore, §13 demo fallback present |

### TC-087-06 Configuration validation report has the required pass/fail lines and the no-deployment sentence

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -n "No deployment was performed" docs/reports/CONFIGURATION_VALIDATION_REPORT.md` | Line 5: "**No deployment was performed in this checkpoint.** …" |
| 2 | Read rows B.01 and B.02 | B.01 Render `region: ohio` on all four services **PASS**; B.02 Neon `aws-us-east-1` documented **PASS** |
| 3 | Read rows C.01 and C.02 | `sslmode=require` for DATABASE_URL and DATABASE_MIGRATION_URL **PASS** |
| 4 | Read rows D.01 and D.02 | D.01 production template `PIPELINE_PROFILE=production` **PASS**; D.02 production template has no `PIPELINE_AS_OF` value **PASS** |
| 5 | Read row I.03 | OpenAPI drift check in `ci.yml` **PASS** |
| 6 | Search the report for `FAIL` | Every FAIL (if any) has a reason; §1 states no open FAIL blocks Phase 10 |

### TC-087-07 `docs/deployment.md` contains the five containment actions, the 24-hour reporting rule and the governance rules

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open section "Incident containment, reporting and investigation" | Table rows 1 Revoke API keys (`python -m backend.cli revoke-api-key --name <key name>`), 2 Deactivate users (`PATCH /api/v1/users/{id}` with `{"active": false}`), 3 Rotate JWT_SECRET, 4 Rotate database role passwords, 5 Suspend the service (Render web service and cron job; on AWS scale App Runner to zero) |
| 2 | Read the paragraph "Reporting (SEC-171)" | States reporting to the PI and the Team 2 lead within 24 hours, and that the PI decides on UND IT security and IRB reporting |
| 3 | Read "Investigation (SEC-172)" and "Post-incident note (SEC-173)" | `audit_logs` correlated with application logs by `request_id`; note kept in the team's private project space, not in the public repository |
| 4 | Open section "Research-data governance" | Five bullets: data owned by the PI under the IRB protocol (SEC-180); no retention-based deletion job, OQ-01 (SEC-181); exports only via `echowell_readonly` by IRB-listed personnel from AWS once live data exists (SEC-182); DAIC-WOZ / E-DAIC only under licence, never with live data (SEC-183); third-party documents by link only (SEC-184) |

### TC-087-08 Containment actions are executable as written (tabletop on the local stack)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker compose exec backend python -m backend.cli create-api-key --name tc087-key --device D01` | Exit 0; key printed once |
| 2 | `docker compose exec backend python -m backend.cli revoke-api-key --name tc087-key` | Exit 0; a `POST /api/v1/sessions` with that key now returns 401 |
| 3 | As admin, `PATCH /api/v1/users/{id}` for `clinician@example.com` with `{"active": false}` | 200; a login as that user now returns 401; re-activate with `{"active": true}` afterwards |
| 4 | Read actions 3–5 aloud against the local stack (change `JWT_SECRET` in `.env`, `docker compose up -d backend`) | After restart, a token issued before the change gets 401 on `GET /api/v1/auth/me` |
| 5 | Time steps 1–4 | Completed well within 1 hour (SEC-170) |
| 6 | `SELECT action FROM audit_logs ORDER BY occurred_at DESC LIMIT 5;` | Rows for the key creation and revocation and the user update are present |

Note: the hosted equivalent (Render Shell, Neon role reset, Render suspend) is not executed by this case; it would change the working deployment (D-170).

### TC-087-09 Third-party service rules and service ownership are recorded

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read `docs/deployment.md` "Service accounts" | Rows for GitHub, Netlify, Render, Neon and Sentry (optional) with owner, ≥ 2 MFA administrators, plan, region, limits, verified date |
| 2 | Read the paragraph below the table | States only TRD 22 §4.1 services are used, no real resident data on Netlify, Render, Neon or Sentry, go-live only on AWS, every data-storing service in the United States |

### TC-087-10 Placeholder grep returns nothing

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -rnE "T[B]D\|T[O]DO\|\[p[l]aceholder\]" specs/backlog docs/reports/DEPLOYMENT_CONFIGURATION_GUIDE.md docs/reports/CONFIGURATION_VALIDATION_REPORT.md; echo "exit=$?"` | No output; `exit=1` |

### TC-087-11 Documents contain no secret, credential, real data or personal name

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -nE "postgres(ql)?(\+psycopg)?://[^:*]+:[^*@]+@" specs/backlog/DEPLOYMENT_CHECKLIST.md docs/reports/DEPLOYMENT_CONFIGURATION_GUIDE.md docs/reports/CONFIGURATION_VALIDATION_REPORT.md docs/deployment.md` | No connection string with a real password (masked examples with `****` only) |
| 2 | `grep -nE "ewk_[A-Za-z0-9]{20,}" ` over the same files | No API key value |
| 3 | Read the four documents for resident names, rooms or personal names | Only study IDs (R01–R10, `T`-prefixed) and roles appear |

### TC-087-12 Checklist rows cite only TRD IDs that exist

| Step | Action | Expected Result |
|---|---|---|
| 1 | `for id in $(grep -ohE "\b(DEP\|CIC\|ENV\|TPS\|SEC\|TST\|AGT)-[0-9]{3}\b" specs/backlog/DEPLOYMENT_CHECKLIST.md \| sort -u); do grep -q "^\| $id " specs/TRD/*.md \|\| echo "UNKNOWN $id"; done` | No `UNKNOWN` line: every cited DEP, CIC, ENV, TPS, SEC, TST and AGT ID is defined in a TRD requirement table |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | Local: `PATCH /api/v1/users/{id}` with Bearer admin token and body `{"active": false}` (containment action 2) | 200; response `active` false |
| 2 | Local: `PATCH /api/v1/users/{id}` with a clinician token | 403 (only admin may deactivate users) |

## Database Validation

Not applicable for the documents themselves (FEAT-087 Database Impact "None"). TC-087-08 step 6 reads `audit_logs` on the local stack only to confirm the containment actions are audited.

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Placeholder grep (TC-087-10) | No match |
| 2 | Variable cross-check (TC-087-04) | No `MISSING` variable |
| 3 | Unknown TRD ID check (TC-087-12) | No `UNKNOWN` ID |
| 4 | Secret and connection-string scan (TC-087-11) | No credential found |
| 5 | Containment action 2 attempted with a clinician token (API Validation step 2) | 403 |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-087-AC-01 | The four files exist at their paths | TC-087-01 |
| FEAT-087-AC-02 | MVP readiness checklist contains 15 rows MVP-01..MVP-15 with Table 4.17-A evidence | TC-087-02 |
| FEAT-087-AC-03 | Every variable of TRD 21 §4.2, §4.3, §4.5 appears in the configuration guide | TC-087-04 |
| FEAT-087-AC-04 | Validation report has pass/fail lines for regions, `sslmode=require` on both URLs, production templates, OpenAPI drift check, and the no-deployment sentence | TC-087-06 |
| FEAT-087-AC-05 | `docs/deployment.md` contains the five SEC-170 actions, the 24-hour rule and SEC-180..SEC-184 | TC-087-07, TC-087-08 |
| FEAT-087-AC-06 | The placeholder grep returns nothing | TC-087-10 |

## Test Data Requirements

- No hosted data. TC-087-08 uses the local `test_v0_1` seed (`admin@example.com`, `clinician@example.com`, device D01) and a throwaway key name `tc087-key`.
- TRD 13 Table 4.17-A, TRD 15 §4.2/§4.9/§4.10, TRD 21 §4.2/§4.3/§4.5 as reference texts.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| AGT-032, AC-AGT-07, D-21 | FEAT-087 | TC-087-01 |
| TST-170, AC-TST-10 | FEAT-087 | TC-087-02 |
| SEC-005, DEP-118 | FEAT-087 | TC-087-03 |
| ENV-050, TRD 25 §4.6 Phase 9 DoD | FEAT-087 | TC-087-04 |
| TRD 15 §4.2, §4.9, §4.10 | FEAT-087 | TC-087-05 |
| D-54, D-51, D-156 | FEAT-087 | TC-087-06 |
| SEC-170..SEC-173 | FEAT-087 | TC-087-07, TC-087-08 |
| SEC-180..SEC-184 | FEAT-087 | TC-087-07 |
| TPS-001..TPS-007 | FEAT-087 | TC-087-09 |
| TRD 25 §4.6 Phase 12 Commands | FEAT-087 | TC-087-10 |
| AGT-016, AGT-017, TPS-041 | FEAT-087 | TC-087-11 |
| AGT-009 | FEAT-087 | TC-087-12 |
| FEAT-087-FR-01..FEAT-087-FR-11 | FEAT-087 | TC-087-01..TC-087-12 |
