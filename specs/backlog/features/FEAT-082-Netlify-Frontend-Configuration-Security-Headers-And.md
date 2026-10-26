# FEAT-082 Netlify frontend configuration, security headers and CSP

| Field | Value |
|---|---|
| Epic | DevOps & Deployment |
| Build phase | Phase 9 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-077 |
| Status | Not Started |

## Purpose

Configure the Next.js frontend for Netlify as code: `netlify.toml` with base `frontend/`, the CSP-checking build command, the ignore rule that skips builds when nothing under `frontend/` changed, no deploy-context environment blocks (both Netlify sites build `main`, so `NEXT_PUBLIC_APP_ENV` is a per-site variable, D-99), and the exact TRD 12 §4.9 header set (CSP with `connect-src` limited to the two Railway API origins, HSTS, `X-Frame-Options`, `Referrer-Policy`, `X-Content-Type-Options` and a `Permissions-Policy` denying microphone and camera). The per-site `NEXT_PUBLIC_API_BASE_URL` values are documented so the production site calls only the production backend and the staging site and its deploy previews never do.

## Business Context

- BR-17 and SRC-01: the frontend is deployed from GitHub to Netlify (DEP-002, DEP-004).
- BR-16: browser hardening (CSP, HSTS, no third-party origins, no microphone or camera access) and separation of preview builds from production data (DEP-053, DEP-054, SEC-070, SEC-071).
- BR-01: the dashboard never accesses audio devices (SEC-071).

## Referenced TRDs

- TRD 15 DEP-002, DEP-004, DEP-050, DEP-051, DEP-052, DEP-053, DEP-054, §4.6 procedure and `netlify.toml` outline, §8 Implementation Notes.
- TRD 12 SEC-054, SEC-060, SEC-062, SEC-070, SEC-071, SEC-072, SEC-073, SEC-075, §4.9 header excerpt.
- TRD 04 FE-060, FE-061.
- TRD 22 TPS-010, TPS-011, TPS-050, TPS-051, TPS-081, TPS-085.
- TRD 21 §4.7 matrix (NEXT_PUBLIC_API_BASE_URL, NEXT_PUBLIC_APP_ENV), §4.5.
- TRD 16 §4.4 step 3 (`echowell-build` meta tag compared by deploy workflows).
- TRD 24 D-65 (API base URL is an origin only; TRD 12 §4.9 owns the header set; nonce CSP deferred to Amplify).

## Scope

- `/netlify.toml` per the TRD 15 §4.6 outline: `[build]` base `frontend`, command `node scripts/check-csp.mjs && npm run build`, publish `.next`, ignore `git diff --quiet $CACHED_COMMIT_REF $COMMIT_REF -- . ../netlify.toml`; `[build.environment]` `NODE_VERSION = "20"`, `NEXT_TELEMETRY_DISABLED = "1"`; plugin `@netlify/plugin-nextjs`; no `[context.*]` environment blocks; `[[headers]] for = "/*"` copied verbatim from TRD 12 §4.9.
- `frontend/scripts/check-csp.mjs`: fails the build when the origin in `NEXT_PUBLIC_API_BASE_URL` is not listed in `connect-src` of `netlify.toml`.
- The build-SHA meta tag `<meta name="echowell-build" content="<NEXT_PUBLIC_GIT_SHA>">` on `/login` if not already present (needed by FEAT-086 verification).
- Runbook section in `docs/deployment.md`: two sites (or recorded names): staging site `echowell-und-staging` (production branch `main`, auto publishing on, branch deploys off, deploy previews on) and production site `echowell-und` (builds stopped, published only by `deploy-production.yml` with the Netlify CLI); per-site variables set in the Netlify UI (staging site `NEXT_PUBLIC_API_BASE_URL` = `https://echowell-backend-staging.up.railway.app`, `NEXT_PUBLIC_APP_ENV` = `staging`; production site `https://echowell-backend-production.up.railway.app`, `production`), origin only.

## Out of Scope

- Creating the Netlify site or setting UI variables (Phase 10, FEAT-088).
- A middleware or nonce-based CSP (deferred to Amplify, SEC-075, FE-060).
- Backend CORS configuration (owned by the backend features; FEAT-086 smoke tests verify it).
- AWS Amplify configuration (FEAT-092).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-082-FR-01 | The Netlify site shall use base directory `frontend/`, build command `node scripts/check-csp.mjs && npm run build`, Node 20 and plugin `@netlify/plugin-nextjs`. | DEP-050, SEC-070 |
| FEAT-082-FR-02 | `NEXT_PUBLIC_API_BASE_URL` shall be set per Netlify site so the production site calls only the production backend and the staging site and its deploy previews only the staging backend; the value is an origin without `/api/v1`. | DEP-051, D-65 |
| FEAT-082-FR-03 | Deploy previews shall never be configured with the production backend URL, and `netlify.toml` shall not contain the production `NEXT_PUBLIC_API_BASE_URL`. | DEP-054, TRD 15 §8 |
| FEAT-082-FR-04 | Netlify shall skip a build when no file under `frontend/` and no `netlify.toml` changed (ignore command evaluated inside the base directory). | DEP-052 |
| FEAT-082-FR-05 | Every response shall carry exactly the TRD 12 §4.9 headers: `Strict-Transport-Security: max-age=31536000; includeSubDomains`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()` and the Content-Security-Policy of the excerpt. | DEP-053, SEC-062, SEC-071, FE-061 |
| FEAT-082-FR-06 | `connect-src` shall list exactly `'self'`, `https://echowell-backend-staging.up.railway.app` and `https://echowell-backend-production.up.railway.app`, with no wildcard; `check-csp.mjs` shall fail the build when `NEXT_PUBLIC_API_BASE_URL` is not one of them. | SEC-070, FE-060, TPS-051 |
| FEAT-082-FR-07 | The frontend shall set no other CSP (no middleware CSP); `script-src 'unsafe-inline'` is accepted for the MVP. | FE-060, SEC-075 |
| FEAT-082-FR-08 | Netlify environment variables shall contain only `NEXT_PUBLIC_*` values, `NODE_VERSION` and `NEXT_TELEMETRY_DISABLED`; no `NEXT_PUBLIC_*` variable holds a secret. | TPS-011, SEC-054 |
| FEAT-082-FR-09 | Netlify shall host only the frontend; no Netlify Functions, Forms, Identity, Blobs, Analytics or Edge Functions beyond what `@netlify/plugin-nextjs` generates. | TPS-010 |
| FEAT-082-FR-10 | The frontend shall load fonts only through `next/font` self-hosting and no third-party scripts, styles, fonts or trackers. | SEC-072, SEC-073, TPS-050, TPS-081, TPS-085 |
| FEAT-082-FR-11 | The staging frontend shall be deployed from `main` on every merge through the Netlify GitHub integration of the staging site; the production frontend shall be published only by an approved `deploy-production.yml` run for a chosen `main` commit (production site builds stopped). | DEP-002, DEP-004, CIC-001 |

## Inputs

- Frontend build (FEAT-062 onward) and the frontend image definition (FEAT-077).
- TRD 12 §4.9 header excerpt (copied verbatim; TRD 12 is its only owner, D-65).
- Railway backend domains from FEAT-081 (record the generated names if the defaults are taken).

## Outputs

- `/netlify.toml`, `frontend/scripts/check-csp.mjs`, `docs/deployment.md` section "Netlify frontend".
- A unit test `frontend/tests/unit/check-csp.test.ts` (or a Node test) for the CSP check.

## Data Flow

Merge to `main` or PR → Netlify GitHub integration of the staging site (production site: `netlify deploy --build --prod` in an approved release run) → ignore command decides whether to build → `check-csp.mjs` validates the API origin against `connect-src` → `npm run build` with the site variables → published with the header set → browser loads pages from Netlify and calls only the backend origin in `NEXT_PUBLIC_API_BASE_URL`, enforced by CSP.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-077

- [FEAT-077](FEAT-077-Production-Container-Images-Compose-Demo-Profile.md) Production container images and environment templates (frontend production build and `NEXT_PUBLIC_*` template values).

Features that build directly on this one (BACKLOG.md §4): FEAT-083, FEAT-084, FEAT-085, FEAT-086.

## Database Impact

None. The frontend has no database access.

## API Impact

None exposed. The configuration constrains which API origin the browser may call (`connect-src`).

## Frontend Impact

- New: `netlify.toml`, `frontend/scripts/check-csp.mjs`; `echowell-build` meta tag on `/login` (if absent).
- All routes (`/login`, `/residents`, `/residents/[residentCode]` and its sections, `/admissions`, `/study`, `/admin`; TRD 24 D-110) receive the header set; no component logic changes.

## Analytics Impact

None.

## Security Requirements

- Header set and CSP exactly as TRD 12 §4.9 (SEC-070..SEC-075); HTTPS via the Netlify edge with HTTP redirected (SEC-060).
- Microphone and camera denied by `Permissions-Policy` (SEC-071).
- No secrets in Netlify variables or `netlify.toml` (ENV-005, SEC-054).

## Error Handling

- `check-csp.mjs` exits non-zero with a message naming the missing origin; the Netlify build fails and the previous deploy stays published.
- A broken frontend deploy is rolled back with "Publish deploy" on the last good deploy (TRD 15 §4.12; FEAT-089).

## Logging Requirements

- Netlify build logs only; the frontend sends no telemetry or logs to third parties (LOG-082). No audit records.

## Testing Requirements

- Unit: `check-csp` test (missing origin fails, listed origin passes).
- E2E: FE-192 (`privacy.spec.ts`, no third-party hosts) remains green (FEAT-076).
- Post-deploy: header presence and HSTS on both origins in the smoke tests (DEP-081 (e), TST-135; FEAT-086).
- Inspection: header block diffed against TRD 12 §4.9 text.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-082-AC-01 | The `[[headers]]` block of `netlify.toml` is byte-identical to the TRD 12 §4.9 excerpt. Verified by: E2E (`privacy.spec.ts`; FE-192). | DEP-053, SEC-070 |
| FEAT-082-AC-02 | `NEXT_PUBLIC_API_BASE_URL=https://example.org node frontend/scripts/check-csp.mjs` exits non-zero; with `https://echowell-backend-staging.up.railway.app` it exits 0. Verified by: E2E (`privacy.spec.ts`; FE-192). | SEC-070 |
| FEAT-082-AC-03 | `grep -n "NEXT_PUBLIC_API_BASE_URL" netlify.toml` returns nothing, and `grep -n "production.up.railway.app" netlify.toml` matches only the CSP line. Verified by: Inspection (run the command in the criterion and check its output). | DEP-054, TRD 15 §8 |
| FEAT-082-AC-04 | `netlify.toml` contains base `frontend`, the build command `node scripts/check-csp.mjs && npm run build`, `NODE_VERSION = "20"`, the plugin `@netlify/plugin-nextjs` and the ignore command of the outline. Verified by: Inspection (the inspection method of DEP-050, applied to the condition stated in the criterion). | DEP-050, DEP-052 |
| FEAT-082-AC-05 | `Permissions-Policy` in `netlify.toml` contains `camera=()` and `microphone=()`. Verified by: E2E (`privacy.spec.ts`; FE-192). | SEC-071 |

## Definition of Done

- All FEAT-082 acceptance criteria pass; no deployment performed (Phase 9).
- Runbook section written; `CONFIGURATION_VALIDATION_REPORT.md` (FEAT-087) cites the header comparison.
- Batch report entry (AGT-022).

## Implementation Notes

- The ignore command runs inside `frontend/`, so paths are relative to it (TRD 15 §8).
- Changing `NEXT_PUBLIC_*` on Netlify requires "Clear cache and deploy" because Next.js inlines them at build time (TRD 21 §8).
- If Railway assigns different domain names, update `connect-src` in TRD 12 §4.9 first (through a TRD change), then copy it here; never edit the header set only in `netlify.toml` (D-65).
