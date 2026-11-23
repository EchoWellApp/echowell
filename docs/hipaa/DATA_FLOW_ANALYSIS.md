# Data Flow Analysis

Document ID: ECHOWELL-HIPAA-DFA · Version 0.1 · Date: 22 November 2026 · Owner: Team 2 · Status: Draft
Prompt: `specs/prompts/hipaa/HIPAA_Compliance_Readiness_Prompt.md` Phase 3 · Extends: `HIPAA_READINESS_REPORT.md`
"Data Flow Review" · Findings: `FINDINGS_REGISTER.md` (HF-xx)

"ePHI may exist" means: once live resident data is collected under a covered-entity relationship. Today every
flow below carries synthetic or test data only (TRD 12 SEC-001). Controls marked *observed* are in the
repository; *documented* are in TRDs or the runbook only; *planned* are AWS go-live controls.

## 1. Architecture and data-flow diagram

```text
  RESIDENT ROOM (Team 1, outside repository)          EchoWell (this repository)
 ┌──────────────────────────────┐
 │ Recording device (T1Dxx)     │  HTTPS, X-API-Key
 │  audio → features (openSMILE │  JSON: 1 check-in       ┌───────────────────────────────┐
 │  + timing)  [audio stays     │ ───────────────────────▶│ Backend API (FastAPI)         │
 │  local, deleted after use]   │  POST /api/v1/sessions  │  Render web service (Ohio)    │
 └──────────────────────────────┘                          │  → AWS App Runner at go-live  │
                                                           │  auth · validation · audit    │
  ADMIN (test data / bulk)                                 └───────┬───────────────┬───────┘
 ┌──────────────────────────────┐  HTTPS, JWT or API key         │ TLS           │ TLS
 │ CSV upload                   │ ───────────────────────▶ POST /api/v1/ingest     │
 └──────────────────────────────┘                                 ▼               │
                                                     ┌───────────────────────────┐│
  SCHEDULER                                          │ PostgreSQL 16             ││
 ┌──────────────────────────────┐                    │  Neon (aws-us-east-1)     ││
 │ Render cron (nightly)        │ ── runs pipeline ─▶│  → RDS + KMS at go-live   ││
 │ → EventBridge at go-live     │                    │ raw_sessions (immutable)  ││
 └──────────────────────────────┘                    │ residents, devices, maps  ││
                                                     │ baselines, scores, alerts ││
                                                     │ alert_reviews, staff_notes││
                                                     │ users, api_keys(hashes)   ││
                                                     │ audit_logs (append-only)  ││
                                                     └─────────┬─────────────────┘│
                                    PITR (Neon) / RDS backups  │  weekly pg_dump   │
                                                     ┌─────────▼─────────┐        │
                                                     │ Backups (encrypted│        │
                                                     │ designated store) │        │
                                                     └───────────────────┘        │
  STAFF BROWSER                                                                   │
 ┌──────────────────────────────┐  HTTPS (HSTS, CSP)  ┌──────────────────────┐    │
 │ Clinician / researcher /     │ ◀──────────────────▶│ Frontend (Next.js)   │    │
 │ admin; token in              │                     │ Netlify → Amplify    │    │
 │ sessionStorage               │ ◀── HTTPS JSON/CSV ─┴──────────────────────┴────┘
 └──────────────────────────────┘
  LOGS: backend JSON logs (redacted) → Render logs → CloudWatch at go-live; optional Sentry (PII off, never on live data until approved)
  NO OUTBOUND: no e-mail/SMS/push to staff, no analytics, no AI services, no audio services (TRD 22 §4.9)
```

## 2. Sources, storage, processing, transmission and retention

| Item | Locations |
|---|---|
| Sources of data | Team 1 devices (voice features); admin CSV uploads (test and bulk data); roster import by CLI (facility, residents, devices, assignments); staff input in the dashboard (reviews, notes, user management) |
| Storage locations | PostgreSQL (Neon now; RDS at go-live); backups (Neon PITR window; weekly `pg_dump` on PI-designated storage); CSV exports held by researchers; provider logs; browser `sessionStorage` (token only) |
| Processing locations | Backend API (validation, authentication, audit); nightly and on-demand pipeline in the backend (baselines, quality screen, speaker screen, scores, CUSUM alerts) |
| Transmission paths | Device → API (HTTPS); browser ↔ frontend and API (HTTPS); API → database (TLS); database → backup storage; API → Sentry (optional, scrubbed) |
| Retention points | `raw_sessions` and all tables (no deletion job; OQ-01); `audit_logs` (life of database); backups (PITR window; dumps until retention decided); exports (undefined); logs (provider default) — see HF-06 |

## 3. Stage-by-stage analysis

### 3.1 Data inputs: roster and accounts

| Aspect | Content |
|---|---|
| Data elements | Facility name; resident study code, sex, cohort, enrolment/admission/withdrawal dates, status; device code, non-identifying room label; device-resident assignment dates; staff email, display name, role |
| ePHI may exist | Yes (resident records with dates, linked to a facility). Staff data is not PHI. |
| Existing controls | Observed: CLI-only roster import, audited (`roster.loaded`); study codes only, no names (SEC-120); attribute set fixed (SEC-122); code patterns validated |
| Missing controls | Retention for withdrawn residents (HF-06) |
| Recommended controls | Keep the mapping from study code to person only at the facility, never in EchoWell; close OQ-01 |

### 3.2 Device data flows

| Aspect | Content |
|---|---|
| Data elements | Session ID, resident code, device code, UTC timestamp, quality flag, noise level, software and firmware versions, 21 voice features |
| ePHI may exist | Yes |
| Existing controls | Observed: HTTPS only; API key hashed, scoped and bound to the device; header-only key; schema with forbidden extras; 5 MB/64 KB limits; rate limit; refusal for withdrawn residents; audit per batch |
| Missing controls | Device-side key storage and audio deletion undocumented (HF-18); framework vulnerabilities (HF-02) |
| Recommended controls | Device Security Policy (EW-POL-07); Starlette upgrade; ingest anomaly alerting |

### 3.3 Audio processing flows

| Aspect | Content |
|---|---|
| Data elements | Raw voice audio (on device only) |
| ePHI may exist | Yes, on the device |
| Existing controls | Observed in EchoWell: no audio endpoint, column or file; `audio/*` refused (415); CI blocks audio files; dashboard denies microphone |
| Missing controls | Everything on the device side is outside the repository (HF-18) |
| Recommended controls | Team 1 to document encrypted local storage, deletion after extraction, and that local file paths and names are not included in submitted data |

### 3.4 Database storage flows

| Aspect | Content |
|---|---|
| Data elements | All tables in §1 |
| ePHI may exist | Yes |
| Existing controls | Observed: TLS required; least-privilege roles; immutable `raw_sessions`, append-only notes, reviews and audit logs; hashes for passwords and keys hidden from the read-only role. Documented: provider encryption at rest; US East regions |
| Missing controls | At-rest encryption and backups not evidenced (HF-16, HF-08); retention (HF-06) |
| Recommended controls | Planned: RDS with KMS, encrypted backups, deletion protection; restore drill record |

### 3.5 Analytics processing flows

| Aspect | Content |
|---|---|
| Data elements | Features → baselines, quality and speaker screens, change scores, CUSUM state, alerts, data alerts |
| ePHI may exist | Yes (derived health information) |
| Existing controls | Observed: runs inside the backend with the app role; deterministic, no ML or external AI (CI-enforced); runs audited (`pipeline.run.started`/`finished`); outputs worded as change, not diagnosis |
| Missing controls | None specific |
| Recommended controls | Keep analytics in-process; any future offline analysis only via the read-only role on the approved platform (SEC-182) |

### 3.6 Notification flows

| Aspect | Content |
|---|---|
| Data elements | Alerts and reminders shown in the dashboard only |
| ePHI may exist | Yes, in the dashboard |
| Existing controls | Observed/documented: no e-mail, SMS or push notifications (TPS-083); operational alerts (uptime issues) contain no resident data |
| Missing controls | — |
| Recommended controls | If notifications are added, send no ePHI in the message ("log in to view"), and assess the provider under EW-POL-06 |

### 3.7 Administrative access flows

| Aspect | Content |
|---|---|
| Data elements | User accounts and roles; API keys; configuration; audit logs; CSV exports; database owner access |
| ePHI may exist | Yes (exports, database access) |
| Existing controls | Observed: admin-only user management; no self-role change; CLI actions audited with operator name; CSV export audited and limited to admin and researcher; read-only role for audit review; production deploys need a reviewer |
| Missing controls | MFA (HF-03); audit-log review (HF-09); export handling and retention (HF-06) |
| Recommended controls | EW-POL-01 and EW-POL-03; export register; quarterly access review |

---

*This assessment represents a technical HIPAA readiness review based on repository evidence and does not
constitute legal certification, regulatory certification, or a formal HIPAA audit.*
