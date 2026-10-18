# 03 Non-Functional Requirements

Document ID: ECHOWELL-TRD-03 · Version 0.1 (draft for review) · Date: 18 October 2026 · Owner: Team 2 · Status: Draft

## 1. Purpose

This document specifies the measurable quality attributes of EchoWell: performance, availability and reliability, reproducibility and numeric precision, data protection (including handling of potentially PHI-derived feature data), security pointers, usability and accessibility, maintainability, portability to the target AWS platform, observability, compliance posture, data integrity, timezone correctness, browser support and scalability limits. Each NFR has a numeric or pass/fail criterion and a verification method.

## 2. Scope

**In scope:** quality attributes of the Team 2 system (frontend, backend, analytics, database, CI/CD) in the local, staging and production environments, on both the current (interim) Netlify/Railway/Neon hosting and the target AWS hosting (D-OWNER-3).

**Out of scope:** device-side quality (Team 1: capture latency, battery, wake-word accuracy); clinical performance of the alarm (sensitivity/specificity), which is a research question calibrated on Team 1's larger dataset (OQ-13), not a software NFR; detailed security controls (TRD 12) and logging formats (TRD 17), which are referenced here.

## 3. References

| ID | Used for |
|---|---|
| SRC-01 | Hosting (free/trial tiers), future AWS migration, test categories |
| SRC-02 | Raw store immutability, rebuildability |
| SRC-03, SRC-04, SRC-05 | Numeric tolerance (1e-6), determinism, test volumes |
| SRC-07 | Rationale: version comparability, adherence, time-of-day effect (cited by link only, D-OWNER-1) |
| SRC-09, SRC-10, SRC-11 | Design tokens, touch targets, plain language, status glyphs |
| SRC-14 | Fixed constraints (no audio, detection not diagnosis, research system) |
| D-OWNER-2, D-OWNER-3, D-OWNER-4 | Production baseline 30 / test-only 16; AWS target, interim hosting, PHI-derived data protection; no real resident data on the interim stack, go-live on AWS only |

Related TRDs: 00 (BR-xx), 01 (ARC), 12 (SEC), 13 (TST), 15 (DEP), 16 (CIC), 17 (LOG), 21 (ENV), 22 (TPS).

## 4. Requirements

### 4.1 Measurement conditions

Unless stated otherwise, performance NFRs are measured:

- against the **reference dataset**: SRC-05 loaded with profile `test_v0_1` (10 residents, 30 days), or the **scale dataset**: 100 residents × 365 days × 1 session/day (36,500 records) produced by the synthetic generator of TRD 14 (ASM-08 upper bound);
- on the **staging** environment (current interim hosting) with **warm** services (at least one request in the preceding 60 seconds), or in CI against `postgres:16` in Docker for automated checks;
- server-side, from request receipt to last response byte, as recorded in backend request logs (TRD 17), over at least 200 requests per endpoint;
- excluding Team 1 network transit and the browser's network latency unless the NFR says "end to end".

Interim free/trial tiers may suspend idle compute (Neon auto-suspend, Railway sleep; RSK-07). Cold-start behaviour has its own NFR (NFR-008) and is excluded from p95 figures.

### 4.2 Performance

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| NFR-001 | `GET /api/v1/residents` shall respond with p95 < 500 ms for 100 residents (scale dataset), warm. | Must | BR-12, ASM-08 | Test (load test, k6 or Locust, TRD 13) |
| NFR-002 | `GET /api/v1/residents/{code}`, `/checkins`, `/features`, `/notes` and `GET /api/v1/scores?resident_code=` shall each respond with p95 < 500 ms for a resident with 365 days of data, warm. | Must | BR-13, ASM-08 | Test |
| NFR-003 | `GET /api/v1/devices` and `GET /api/v1/alerts` shall respond with p95 < 500 ms on the scale dataset, warm. | Must | BR-12 | Test |
| NFR-004 | `POST /api/v1/sessions` shall persist the raw record (excluding the pipeline run) with p95 < 300 ms, warm. | Must | BR-01 | Test |
| NFR-005 | The resident-scoped pipeline run triggered by a single ingest shall complete in < 2 s for a resident with 365 days of data (including co-residents of a shared device), so that the full `POST /api/v1/sessions` response returns in < 2.3 s p95. | Must | BR-01, SRC-15 demo step 4 | Test |
| NFR-006 | A full rebuild of the reference dataset (SRC-05, 283 arrivals) shall complete in < 30 s, including database writes. | Must | BR-15, SRC-02 | Test (CI validation job timing) |
| NFR-007 | A full rebuild of the scale dataset (36,500 records) shall complete in < 10 min, so that the nightly run fits comfortably before staff day shifts. | Should | BR-02, ASM-08 | Test (scheduled performance job) |
| NFR-008 | The first request after an idle period (cold start of backend or database on interim tiers) shall complete in < 15 s; the frontend shall show a loading state (not an error) for up to 20 s. | Should | BR-12, RSK-07 | Test (manual, staging) |
| NFR-009 | A CSV upload of the reference dataset (283 rows) shall return 202 in < 5 s and the batch shall be fully processed in < 30 s. | Must | BR-15 | Test |
| NFR-010 | The Residents overview and Resident detail pages shall reach Largest Contentful Paint < 2.5 s and Interaction to Next Paint < 200 ms on a desktop Chrome profile with "Fast 4G" throttling, warm API. | Should | BR-12, BR-13 | Test (Lighthouse CI) |
| NFR-011 | A record accepted by `POST /api/v1/sessions` shall be visible on the Resident detail page (after reload) within 5 s of the API response, end to end. | Must | BR-13, SRC-15 demo step 5 | Test (E2E), Demo |
| NFR-012 | The initial JavaScript transferred for any dashboard route shall be ≤ 300 KB gzip. | Should | BR-12 | Test (`next build` output check in CI) |

### 4.3 Availability and reliability

These targets are honest for a research prototype on free/trial tiers with no on-call staff. They are not clinical-grade service levels; EchoWell is not used for emergency response (TRD 00 §4.2).

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| NFR-020 | During the demo and presentation window (16 Nov – 8 Dec 2026), the production environment shall achieve ≥ 99.0% monthly availability of `GET /api/v1/health` measured by a 5-minute external uptime check, excluding announced maintenance. | Should | BR-17, RSK-07 | Analysis (uptime monitor report) |
| NFR-021 | The system shall not lose an acknowledged record: every record for which `POST /api/v1/sessions` returned 200 or 201 shall exist in `raw_sessions` after any subsequent failure of the pipeline, backend restart or redeploy. | Must | BR-02 | Test (fault injection: kill process after commit) |
| NFR-022 | A pipeline failure shall not prevent ingestion: raw records shall continue to be accepted while runs fail, and the next successful run shall process them. | Must | BR-02, ARC-025 | Test |
| NFR-023 | A failed nightly run shall be retried automatically at most 2 times at 15-minute intervals, and each attempt shall be recorded in `pipeline_runs`. | Should | BR-06, BR-11 | Test |
| NFR-024 | The production database shall have provider point-in-time recovery or daily backups with ≥ 7 days retention, encrypted at rest. | Must | BR-02, BR-16, D-OWNER-3 | Inspection (provider settings evidence, TRD 22) |
| NFR-025 | Recovery point objective shall be ≤ 24 h and recovery time objective ≤ 8 working hours for production; a restore shall be rehearsed once before go-live on AWS. | Should | BR-02, D-OWNER-4 | Demo (restore drill record) |
| NFR-026 | Batch ingest shall be atomic per record: a failure on one record shall not roll back other accepted records of the batch. | Must | BR-01, BR-02 | Test |
| NFR-027 | When the database is unreachable, the API shall return 503 with an RFC 7807 body within 10 s and `GET /api/v1/health` shall report `database: "unavailable"`. | Must | BR-17, TRD 17 | Test |

### 4.4 Reproducibility, determinism and numeric precision

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| NFR-030 | All analytics computations shall use IEEE-754 float64 (numpy `float64`); no float32, Decimal or database-side arithmetic shall be used for medians, MAD, spreads, z, composite or CUSUM. | Must | BR-15, SRC-03 | Inspection, Test |
| NFR-031 | Numeric outputs shall match SRC-03 within absolute tolerance 1e-6 for medians, MAD, robust spread, z values, composite_raw, composite_z and CUSUM tally; statuses, reasons, alarm states and session IDs shall match exactly. | Must | BR-15, SRC-03 | Test (validation suite) |
| NFR-032 | Numeric values shall be stored in PostgreSQL as `double precision` (or JSONB numbers produced from float64) so that a stored-and-reloaded value equals the computed value exactly. | Must | BR-15 | Test (round-trip) |
| NFR-033 | Two pipeline runs over the same raw records, configuration snapshot, frozen baselines and as-of time shall produce bit-identical numeric outputs and identical row ordering. | Must | BR-15, ARC-042 | Test |
| NFR-034 | Analytics shall not use randomness, wall-clock time, environment-dependent locale or unordered iteration (e.g. iteration over Python `set`) in a way that affects output. | Must | BR-15 | Inspection, Test |
| NFR-035 | Every pipeline run shall record its configuration snapshot and code version (`GIT_SHA`) so that any historical result can be regenerated. | Must | BR-15, ARC-060 | Test |
| NFR-036 | Dependency versions shall be pinned (Python lock file with hashes; `package-lock.json`) so that CI and deployments build from identical dependency sets. | Must | BR-15, BR-17 | Inspection |
| NFR-037 | Displayed numbers shall be rounded only at presentation time (tally to 1 decimal in labels, F0 z to 2 decimals in reasons); stored values shall not be rounded. | Must | BR-15, SRC-03 | Test |

### 4.5 Data protection and privacy (sensitive, potentially PHI-derived data)

Live feature data is extracted from residents' speech and is treated as sensitive, potentially PHI-derived data (D-OWNER-3). The interim stack holds synthetic and test data only; real resident data goes live only on the approved AWS platform (D-OWNER-4).

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| NFR-040 | No EchoWell component shall store, transmit or render audio; the database shall contain no column, and the API no field, capable of holding audio content. | Must | BR-01, BR-16, SRC-14 | Inspection (schema and OpenAPI scan in CI) |
| NFR-041 | The system shall hold no resident PII: residents are identified only by study ID; free-text inputs (staff notes) shall be displayed with a reminder "Do not enter names or other identifying details." | Must | BR-16, VIS-006 | Inspection, Test |
| NFR-042 | All network connections carrying feature data or credentials shall use TLS 1.2 or higher: device → backend, browser → frontend, frontend → backend, backend → database (`sslmode=require` or stricter), CI → hosting APIs. | Must | BR-16, D-OWNER-3 | Test (TLS scan of staging/production endpoints; startup check of `DATABASE_URL`) |
| NFR-043 | Plain HTTP requests to frontend and backend shall be redirected to HTTPS or refused, and responses shall carry `Strict-Transport-Security: max-age=31536000`. | Must | BR-16, TRD 12 | Test |
| NFR-044 | All persistent storage of feature data, including database volumes, backups and snapshots, shall be encrypted at rest: provider-managed encryption on Neon/Railway (interim); RDS storage encryption with an AWS KMS key, encrypted automated backups and snapshots, and SSE-KMS for any S3 objects (target). | Must | BR-16, D-OWNER-3 | Inspection (provider configuration evidence recorded in TRD 22) |
| NFR-045 | The interim Netlify/Railway/Neon environments shall contain only synthetic and test data; no real resident data shall be ingested there at any time. | Must | BR-16, D-OWNER-4, RSK-14 | Inspection (ingest batch sources, DATA_SOURCE_LABEL, release checklist) |
| NFR-046 | Real resident data shall be ingested only after go-live on the approved AWS platform, with encryption (NFR-042, NFR-044), least-privilege access (NFR-047) and audit logging (NFR-049) verified in a go-live checklist. | Must | BR-16, D-OWNER-4, OQ-07 | Inspection (go-live checklist, TRD 15) |
| NFR-047 | Access shall follow least privilege: the application DB role shall have no UPDATE/DELETE on `raw_sessions` and `audit_logs`; dashboard roles shall be limited per TRD 02 §4.22; cloud console access shall be limited to named Team 2 administrators. | Must | BR-16, TRD 12 | Test, Inspection |
| NFR-048 | Logs, error reports and error-tracking events shall not contain feature values, raw ingest bodies, staff-note text, passwords, tokens or API keys. | Must | BR-16, D-OWNER-3, TRD 17 | Test (log capture assertions) |
| NFR-049 | Security-relevant actions shall be recorded in `audit_logs` (events listed in TRD 12) within the same transaction as the action. | Must | BR-16 | Test |
| NFR-050 | Data export (FR-244) shall be limited to roles `researcher` and `admin` and shall contain study IDs only and no staff-note text. | Must | BR-16 | Test |
| NFR-051 | Data shall not be deleted by the application in the MVP; any retention or deletion behaviour awaits OQ-01 and withdrawal handling awaits OQ-11. | Must | BR-02, OQ-01, OQ-11 | Inspection |

Security controls in detail (authentication, JWT, argon2id, API keys, CORS, rate limits, secrets) are specified in TRD 12 (SEC).

### 4.6 Usability and accessibility

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| NFR-060 | The dashboard shall conform to WCAG 2.1 Level AA. | Must | BR-12, BR-13 | Test (axe-core in Playwright: 0 serious/critical violations on `/login`, `/residents`, `/residents/R09`, `/admissions`, `/admin`), Inspection (manual keyboard and screen-reader pass) |
| NFR-061 | Status shall never be conveyed by colour alone: alarm states shall combine the ▲ glyph, text ("Alarm on", "Alarm since …") and a 2 px #9A4508 border. | Must | BR-12, SRC-09, SRC-10 | Inspection, Test |
| NFR-062 | Text contrast shall be ≥ 4.5:1 for body text and ≥ 3:1 for large text and non-text UI elements; the specified tokens meet this (#1F1F1E on #F6F6F4 = 15.2:1; #4A4A47 on #F6F6F4 = 8.2:1; #9A4508 on #FFFFFF = 6.5:1). | Must | BR-12, SRC-09 | Test (contrast check) |
| NFR-063 | Baseline-period chart bars (#BDBDB8, 1.9:1 on white) shall carry a 1 px #8A8A85 outline (3.5:1) or equivalent so that they meet the 3:1 non-text contrast criterion, and the chart shall have a text-table alternative. | Must | BR-13, SRC-10, WCAG 1.4.11 | Test, Inspection |
| NFR-064 | Every interactive control shall have a target size of at least 44 × 44 CSS px. | Must | BR-12, SRC-09 | Test (automated size check in E2E) |
| NFR-065 | All functions shall be operable by keyboard alone with a visible focus indicator and a logical tab order. | Must | BR-12, BR-13 | Test (Playwright keyboard flow) |
| NFR-066 | User-facing text shall use plain language: no statistical terms without a plain-language label (e.g. "Running change tally", "Quieter (loudness)"); the "What this means" text shall score ≤ grade 8 on the Flesch-Kincaid scale. | Should | BR-13, BR-18, SRC-10 | Analysis (readability check of configured strings) |
| NFR-067 | Wording shall follow detection-not-diagnosis rules (TRD 00 §4.2); a CI text check shall fail on forbidden terms in UI copy. | Must | BR-18, VIS-003 | Test (CI) |
| NFR-068 | Pages shall remain usable at 200% browser zoom and at viewport widths ≥ 360 px without horizontal page scroll; data tables may scroll horizontally inside their container below 900 px (overview) and 760 px (admissions). | Must | BR-12, SRC-09, SRC-11 | Test (Playwright at 360, 768, 1280 px) |
| NFR-069 | A first-time clinician shall be able to identify which residents have an alarm and open one resident's detail within 60 s without training, in a usability session with at least 3 Edgewood staff or proxy participants. | Should | BR-12, BR-13, SRC-14 Part D §7 | Demo (usability session after the Ann and Lovette interviews) |
| NFR-070 | Loading, empty and error states shall be shown in words for every data region (e.g. "Baseline forming · 5 of 30 sessions", "No new admissions"). | Must | BR-12, BR-13 | Test |

### 4.7 Maintainability

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| NFR-080 | Python code shall be fully type-annotated and pass `mypy --strict` for `analytics/` and `mypy` (default strictness with `disallow_untyped_defs`) for `backend/`. | Must | BR-17 | Test (CI) |
| NFR-081 | Python code shall pass `ruff` lint and `ruff format --check`; TypeScript shall pass `tsc --noEmit` in strict mode, ESLint and Prettier. | Must | BR-17 | Test (CI) |
| NFR-082 | Line coverage shall be ≥ 95% for `analytics/`, ≥ 85% for `backend/`, and ≥ 70% for `frontend/` (Vitest), enforced in CI. | Must | BR-15, BR-17, SRC-01 | Test (CI coverage gate) |
| NFR-083 | Every analytics stage function shall have unit tests covering its boundary values (e.g. noise exactly −40.0 is not set aside; speech exactly 1.0 s is not set aside; local hour 12:00 is not morning; tally exactly 5.0 rings). | Must | BR-04, BR-07, BR-11, BR-15 | Test |
| NFR-084 | Pipeline parameters shall be changeable through `config_parameters` without code change and without redeploy (effective from the next run). | Must | BR-09, BR-11, ARC-053 | Test |
| NFR-085 | Public functions in `analytics/` and service methods in `backend/services/` shall carry docstrings stating inputs, outputs and the TRD requirement IDs they implement. | Should | BR-17, VIS-014 | Inspection |
| NFR-086 | Database schema changes shall be delivered only as Alembic migrations that upgrade and downgrade cleanly on an empty database and on a database with the reference dataset. | Must | BR-17 | Test (CI migration job) |
| NFR-087 | A new developer shall be able to start the full local stack with one command (`docker compose up`) and load the reference dataset with one documented command in < 10 min on a laptop with 8 GB RAM. | Should | BR-17 | Demo |

### 4.8 Portability (current interim → target AWS)

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| NFR-090 | The backend shall run unchanged as a container on Railway (current) and AWS App Runner (target), configured only by environment variables. | Must | BR-17, SRC-01, D-OWNER-3, ARC-090 | Test (container run in CI) |
| NFR-091 | The database layer shall run unchanged on Neon, Railway PostgreSQL, Docker `postgres:16` and AWS RDS PostgreSQL 16. | Must | BR-17, ARC-092 | Test (CI on `postgres:16`), Analysis |
| NFR-092 | The frontend shall build with `next build` and deploy to Netlify (current) and AWS Amplify (target) without source change. | Must | BR-17, ARC-093 | Analysis, Test (build) |
| NFR-093 | Moving to AWS shall require changes only to deployment configuration and workflows, estimated ≤ 5 person-days, with no change to `frontend/`, `backend/` or `analytics/` source. | Should | BR-17, SRC-01, ARC-094 | Analysis (migration runbook, TRD 15) |
| NFR-094 | Secrets shall be read only from environment variables so that they can be supplied by Netlify/Railway settings (current) or AWS Secrets Manager (target). | Must | BR-16, BR-17, D-OWNER-3 | Inspection |

### 4.9 Observability

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| NFR-100 | The backend shall emit structured JSON logs to stdout (`LOG_FORMAT=json`) with timestamp, level, request_id, route, status, duration_ms and actor type for every request. | Must | BR-17, TRD 17 | Test |
| NFR-101 | Every pipeline run shall log start, finish, duration, counts per status and warnings, and shall be queryable via `GET /api/v1/pipeline/runs/{id}`. | Must | BR-15, ARC-060 | Test |
| NFR-102 | Unhandled exceptions shall be reported to Sentry when `SENTRY_DSN` is set, with request ID and without PII or feature values; with `SENTRY_DSN` empty, nothing shall be sent. | Should | BR-16, BR-17 | Test |
| NFR-103 | The absence of a successful nightly run in the previous 26 h shall be detectable from `pipeline_runs` and shall be shown on the Admin page as a warning. | Should | BR-06, RSK-05, RSK-07 | Test |
| NFR-104 | An uptime monitor shall poll `GET /api/v1/health` every 5 minutes in staging and production. | Should | BR-17 | Inspection |
| NFR-105 | Silent devices shall be visible to staff within one nightly run: a shared device with no record from any resident on a local day shall appear in the Devices panel after the next nightly run. | Must | BR-06, BR-12, RSK-05 | Test |

### 4.10 Compliance posture and traceability

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| NFR-110 | EchoWell shall be documented and labelled as a research system, not an FDA-cleared device; no UI text, document or API description shall claim diagnostic use. | Must | BR-18, SRC-14 | Inspection |
| NFR-111 | Development shall follow design-control-style traceability: BR → TRD requirement → test case, with every Must requirement linked to at least one automated test or documented inspection. | Must | BR-15, VIS-014 | Inspection (traceability report generated in CI, TRD 13) |
| NFR-112 | Ethics, consent, data-retention and withdrawal decisions are owned by the faculty IRB; the system shall implement only documented decisions and record undecided items as OQ-xx. | Must | BR-16, OQ-01, OQ-11 | Inspection |
| NFR-113 | Each release shall be identified by a Git SHA shown in `GET /api/v1/health` (`version`) and recorded on every pipeline run. | Must | BR-15, BR-17 | Test |
| NFR-114 | Third-party-licensed documents shall be referenced by link and not committed to the repository (e.g. SRC-07 preprint). | Must | D-OWNER-1, TRD 18 | Inspection |
| NFR-115 | No LLM SDK or API and no ML model shall be a runtime dependency; a CI dependency check shall fail if one is added. | Must | BR-18 | Test (CI) |

### 4.11 Data integrity

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| NFR-120 | `raw_sessions` shall be immutable: UPDATE and DELETE shall be rejected by a trigger and by role grants. | Must | BR-02, SRC-02 | Test |
| NFR-121 | `raw_sessions.payload` shall be byte-for-byte reproducible as the received JSON object (for CSV, the header-keyed row of strings). | Must | BR-02 | Test |
| NFR-122 | `arrival_seq` shall be strictly increasing in commit order and unique. | Must | BR-03 | Test |
| NFR-123 | Referential integrity shall be enforced by foreign keys for all relationships listed in TRD 06; uniqueness constraints shall enforce one processed row per raw session, one score per processed session, one ledger row per resident-day and one baseline per epoch-feature. | Must | BR-02, BR-06, BR-09 | Test |
| NFR-124 | A frozen baseline shall never change value after being persisted; a test shall compare baselines before and after ingesting later records and a full rebuild. | Must | BR-09, ASM-07 | Test |
| NFR-125 | The sum of usable + set_aside + quarantined + duplicate per resident shall equal that resident's arrivals in `raw_sessions`, and checked_in + missing_resident + missing_device_gap shall equal the number of days in the ledger window. | Must | BR-02, BR-06 | Test (invariant check after every run) |
| NFR-126 | `audit_logs` and `staff_notes` shall be append-only for the application role. | Must | BR-16, BR-13 | Test |

### 4.12 Timezone correctness

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| NFR-130 | All instants shall be stored as `timestamptz` in UTC and converted to facility local time only with the IANA zone database (Python `zoneinfo`; frontend `Intl.DateTimeFormat` with `timeZone` set to the facility zone). | Must | BR-07, ASM-01 | Inspection, Test |
| NFR-131 | Local date, local time and morning classification shall be correct across daylight-saving transitions: test vectors 2026-11-01 06:30:00 UTC → 01:30 CDT, and 2026-11-01 07:30:00 UTC → 01:30 CST, both local date 2026-11-01 and morning; 2027-03-14 08:30:00 UTC → 03:30 CDT, morning. | Must | BR-06, BR-07 | Test |
| NFR-132 | Records with local time just before and after midnight shall be assigned to the correct local date (e.g. 2026-10-02 04:59:59 UTC → 2026-10-01 23:59:59 CDT, local date 2026-10-01). | Must | BR-06 | Test |
| NFR-133 | The dashboard shall display all dates and times in the facility timezone with its abbreviation (e.g. "Oct 30, 2026, 3:00 PM CT"), independent of the viewer's browser timezone. | Must | BR-12, SRC-09 | Test (Playwright with browser timezone set to Europe/London) |
| NFR-134 | The nightly run shall run exactly once per local day at the first instant at or after 02:00 facility time, including on DST transition days. | Must | BR-06, ARC-061 | Test |

### 4.13 Browser and device support

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| NFR-140 | The dashboard shall support the latest 2 stable major versions of Chrome, Edge, Firefox and Safari (desktop) at release time. | Must | BR-12 | Test (Playwright Chromium, Firefox, WebKit projects; manual check on Edge) |
| NFR-141 | The dashboard shall be usable on tablet browsers (Safari iPadOS, Chrome Android, latest 2 versions) at widths ≥ 768 px. | Should | BR-12 | Test (Playwright device emulation) |
| NFR-142 | The dashboard shall require JavaScript and shall show "This dashboard needs JavaScript enabled." when it is disabled. | Must | BR-12 | Test |

### 4.14 Scalability limits

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| NFR-150 | The MVP shall meet all performance NFRs at the ASM-08 limits: ≤ 25 dashboard users (≤ 10 concurrent), ≤ 100 residents, ≤ 1 session per resident per day, ≤ 3 years of data per resident. | Must | ASM-08 | Test (load test at limits) |
| NFR-151 | The ingest API shall sustain 10 records/s for 60 s (batch or single) without errors, below the 600/min/key rate limit. | Must | BR-01, ASM-08 | Test |
| NFR-152 | Database size for 100 residents × 3 years shall stay ≤ 2 GB including indexes, to fit interim free/trial tier limits. | Should | BR-17, RSK-07 | Analysis (size projection from the scale dataset) |
| NFR-153 | Exceeding the ASM-08 limits shall be treated as a design change requiring review of TRD 01 (in-process analytics, synchronous resident runs), not as a defect. | Must | ASM-08 | Inspection |

## 5. Assumptions

- ASM-01 facility timezone America/Chicago; ASM-04 test profile 16 / production 30 (D-OWNER-2); ASM-08 small scale (basis of all performance and scalability targets).
- Notes for lead (TRD-local, introduced here): frontend coverage target 70%; scale dataset 100 × 365; cold-start allowance 15 s; availability target 99.0% only in the demo window; RPO 24 h / RTO 8 working hours; 2 GB size budget; Flesch-Kincaid grade ≤ 8; baseline-bar outline #8A8A85 to meet WCAG 1.4.11 (the #BDBDB8 token alone is 1.9:1 on white).

## 6. Dependencies

- TRD 12 for security controls; TRD 13 for test tooling (Pytest, Vitest, Playwright, axe-core, load tool); TRD 14 for the scale-dataset generator; TRD 15/22 for provider settings evidence (encryption at rest, backups); TRD 16 for CI gates (coverage, lint, dependency and forbidden-term checks); TRD 17 for log format.
- AWS approval and account (OQ-07) for NFR-044 (target part), NFR-046 and NFR-090–NFR-094 verification on AWS.

## 7. Acceptance Criteria

| ID | Criterion |
|---|---|
| AC-NFR-01 | Load test report shows p95 < 500 ms for `GET /api/v1/residents` with 100 residents and p95 < 300 ms for raw ingest, warm, on staging. |
| AC-NFR-02 | CI validation job rebuilds SRC-05 in < 30 s and matches SRC-03 within 1e-6; a second rebuild produces identical outputs. |
| AC-NFR-03 | CI coverage gate reports analytics ≥ 95%, backend ≥ 85%, frontend ≥ 70% line coverage. |
| AC-NFR-04 | axe-core reports 0 serious or critical violations on the five main pages; all interactive targets measure ≥ 44 × 44 px. |
| AC-NFR-05 | TLS scan of staging frontend and backend shows only TLS 1.2/1.3; the backend refuses to start in staging/production when `DATABASE_URL` lacks `sslmode=require` or stricter. |
| AC-NFR-06 | Provider evidence (screenshots or configuration exports) shows encryption at rest and backups enabled for the interim database; the AWS go-live checklist includes RDS KMS encryption, encrypted backups and Secrets Manager. |
| AC-NFR-07 | Every `ingest_batches` row in staging and production has a synthetic/test source and DATA_SOURCE_LABEL names test or synthetic data (interim stack). |
| AC-NFR-08 | A log-capture test of ingest, note creation and login finds no feature values, note text, passwords, tokens or API keys in logs. |
| AC-NFR-09 | DST and midnight test vectors of NFR-131 and NFR-132 pass. |
| AC-NFR-10 | Playwright suites pass on Chromium, Firefox and WebKit; a run with browser timezone Europe/London shows times in CT. |
| AC-NFR-11 | An attempt to UPDATE or DELETE `raw_sessions` or `audit_logs` with the application role fails; invariant checks of NFR-125 pass after every pipeline run in the validation suite. |

## 8. Implementation Notes

- Load tests: seed the scale dataset with the TRD 14 generator, run k6 or Locust from CI on a scheduled workflow against staging, never against production with real data.
- Use pandas/numpy float64 throughout; avoid `round()` in analytics; compare with `abs(a - b) <= 1e-6` in tests.
- Overview performance: compute 30-day counts with one grouped SQL query over `processed_sessions` and `day_ledger` using indexes on `(resident_id, local_date)`; do not loop per resident in Python.
- Provide `backend/core/config.py` startup checks: `sslmode` for staging/production (ARC-057), refusal of `test_v0_1` in production (ARC-056), presence and length of `JWT_SECRET`.
- Use `zoneinfo.ZoneInfo(facility.timezone)`; never fixed UTC offsets (America/Chicago is UTC−5 in October but UTC−6 from 1 Nov 2026).
- Chart accessibility: render the Recharts chart with `role="img"` and an `aria-label` summary, and a `<table>` alternative.

## 9. Open Questions

| ID | Relevance |
|---|---|
| OQ-01 | Retention: NFR-051 and backup retention beyond 7 days |
| OQ-07 | AWS budget approval timing and account ownership: target-platform verification of NFR-044, NFR-046, NFR-090–NFR-094 |
| OQ-11 | Withdrawal data handling: NFR-051 |
| OQ-13 | Alarm-limit calibration on the larger dataset (clinical performance is out of scope for NFRs) |
| OQ-17 | Site access timing for the usability session (NFR-069) |

## Revision History

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1 | 18 Oct 2026 | Initial generation from TRD_Generation_Prompt.md | — |
