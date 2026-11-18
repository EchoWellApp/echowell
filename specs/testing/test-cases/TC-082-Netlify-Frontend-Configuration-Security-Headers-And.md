# Netlify frontend configuration, security headers and API origin

## Feature Description

FEAT-082 configures the Next.js frontend for Netlify as code (TRD 15 DEP-050..DEP-054, §4.6; TRD 12 SEC-054, SEC-060, SEC-062, SEC-070..SEC-075, §4.9; TRD 04 FE-060, FE-061; TRD 22 TPS-010, TPS-011, TPS-050, TPS-051, TPS-081, TPS-085; TRD 24 D-65, D-99). `netlify.toml` sets base `frontend`, build command `node scripts/check-csp.mjs && npm run build`, `NODE_VERSION = "20"`, plugin `@netlify/plugin-nextjs`, the ignore command that skips builds when nothing under `frontend/` or `netlify.toml` changed, no deploy-context environment blocks, and the exact TRD 12 §4.9 header set (HSTS, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` denying camera and microphone, and a CSP whose `connect-src` lists only `'self'` and the two Render API origins). `frontend/scripts/check-csp.mjs` fails the build when `NEXT_PUBLIC_API_BASE_URL` is not a bare origin listed in `connect-src`. `NEXT_PUBLIC_API_BASE_URL` is a per-site variable: the production site calls only the production backend; the staging site and its deploy previews only the staging backend. The interim deployment is live (TRD 24 D-180); hosted checks are read-only.

In this file `<STAGING_API_ORIGIN>` and `<PRODUCTION_API_ORIGIN>` mean the second and third sources of `connect-src` in TRD 12 §4.9 (and in `netlify.toml`), and `<FRONTEND_URL>` the staging or production site origin held by the team.

## Preconditions

- Repository clone; Node 20; Python 3.12 with `pip install -r backend/requirements-dev.txt` (for `tests/unit/test_netlify_config.py`); `curl`.
- For **Hosted** cases: `<FRONTEND_URL>` for staging and production and read-only (viewer) access to both Netlify sites. No setting, variable or deploy is changed.
- Local Compose demo stack (for the privacy spec), seeded with `test_v0_1`.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-082-01 | `[[headers]]` block of `netlify.toml` is byte-identical to TRD 12 §4.9 | High | Security |
| TC-082-02 | `check-csp.mjs`: unlisted origin exits non-zero, staging origin exits 0 | High | Negative |
| TC-082-03 | No `NEXT_PUBLIC_API_BASE_URL` in `netlify.toml`; production host only in the CSP line | High | Security |
| TC-082-04 | Build settings: base, command, Node 20, plugin, ignore command | High | Documentation |
| TC-082-05 | `Permissions-Policy` contains `camera=()` and `microphone=()` | High | Security |
| TC-082-06 | `connect-src` is exactly `'self'` and the two Render origins, no wildcard | High | Security |
| TC-082-07 | `check-csp.mjs` refuses a path, trailing slash, missing value or wildcard | Medium | Negative |
| TC-082-08 | No middleware CSP; fonts self-hosted; no third-party request (privacy spec) | High | Security |
| TC-082-09 | Hosted: every response of both sites carries the §4.9 headers | High | Hosted |
| TC-082-10 | Hosted: per-site API origin; deploy previews never call production | High | Hosted |
| TC-082-11 | Hosted: Netlify variables and features limited to the frontend | Medium | Hosted |
| TC-082-12 | Staging deploys from `main`; production only through `deploy-production.yml` | Medium | Documentation |

### TC-082-01 `[[headers]]` block of `netlify.toml` is byte-identical to TRD 12 §4.9

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -q tests/unit/test_netlify_config.py -k byte_identical` | `test_header_block_is_byte_identical_to_trd12_excerpt` passes. |
| 2 | Visually diff the `[[headers]]` block of `netlify.toml` with the excerpt in `specs/TRD/12_*.md` §4.9. | Identical: `for = "/*"`, `Strict-Transport-Security = "max-age=31536000; includeSubDomains"`, `X-Content-Type-Options = "nosniff"`, `X-Frame-Options = "DENY"`, `Referrer-Policy = "no-referrer"`, `Permissions-Policy = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"`, and the same `Content-Security-Policy` string. |

### TC-082-02 `check-csp.mjs`: unlisted origin exits non-zero, staging origin exits 0

| Step | Action | Expected Result |
|---|---|---|
| 1 | `NEXT_PUBLIC_API_BASE_URL=https://example.org node frontend/scripts/check-csp.mjs; echo "exit=$?"` | stderr `check-csp: https://example.org is not listed in connect-src of <path>/netlify.toml; update TRD 12 §4.9 first (D-65)`; `exit=1`. |
| 2 | `NEXT_PUBLIC_API_BASE_URL=<STAGING_API_ORIGIN> node frontend/scripts/check-csp.mjs; echo "exit=$?"` | `check-csp: <STAGING_API_ORIGIN> is listed in connect-src`; `exit=0`. |
| 3 | Same with `<PRODUCTION_API_ORIGIN>`. | `exit=0`. |
| 4 | `pytest -q tests/unit/test_netlify_config.py -k check_csp` | All `check_csp` tests pass. |

### TC-082-03 No `NEXT_PUBLIC_API_BASE_URL` in `netlify.toml`; production host only in the CSP line

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -n "NEXT_PUBLIC_API_BASE_URL" netlify.toml` | No output. |
| 2 | `grep -n "<PRODUCTION_API_ORIGIN host>" netlify.toml` (host part of `<PRODUCTION_API_ORIGIN>`) | Exactly one match: the `Content-Security-Policy` line. |
| 3 | `grep -n "\[context" netlify.toml` | No output (no deploy-context blocks). |

### TC-082-04 Build settings: base, command, Node 20, plugin, ignore command

| Step | Action | Expected Result |
|---|---|---|
| 1 | `sed -n '/^\[build\]/,/^\[\[plugins/p' netlify.toml` | `base    = "frontend"`, `command = "node scripts/check-csp.mjs && npm run build"`, `publish = ".next"`, `ignore  = "git diff --quiet $CACHED_COMMIT_REF $COMMIT_REF -- . ../netlify.toml"`, `NODE_VERSION = "20"`, `NEXT_TELEMETRY_DISABLED = "1"`. |
| 2 | `grep -n -A1 "\[\[plugins\]\]" netlify.toml` | `package = "@netlify/plugin-nextjs"`. |
| 3 | `pytest -q tests/unit/test_netlify_config.py -k build_settings` | Pass. |
| 4 | Ignore rule locally: `cd frontend && git diff --quiet HEAD~1 HEAD -- . ../netlify.toml; echo $?` on a commit touching only `backend/`. | `0` (Netlify would skip the build); on a commit touching `frontend/` it prints `1`. |

### TC-082-05 `Permissions-Policy` contains `camera=()` and `microphone=()`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -n "Permissions-Policy" netlify.toml` | Value contains `camera=()` and `microphone=()` (also `geolocation=()`, `payment=()`, `usb=()`). |
| 2 | `pytest -q tests/unit/test_netlify_config.py -k permissions_policy` | Pass. |

### TC-082-06 `connect-src` is exactly `'self'` and the two Render origins, no wildcard

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -o "connect-src[^;]*" netlify.toml` | `connect-src 'self' <STAGING_API_ORIGIN> <PRODUCTION_API_ORIGIN>`; no `*`. |
| 2 | `pytest -q tests/unit/test_netlify_config.py -k connect_src` | Pass. |

### TC-082-07 `check-csp.mjs` refuses a path, trailing slash, missing value or wildcard

| Step | Action | Expected Result |
|---|---|---|
| 1 | `NEXT_PUBLIC_API_BASE_URL=<STAGING_API_ORIGIN>/api/v1 node frontend/scripts/check-csp.mjs; echo $?` | `check-csp: NEXT_PUBLIC_API_BASE_URL must be an origin without path, e.g. <STAGING_API_ORIGIN>`; `1`. |
| 2 | Same with a trailing `/`. | Same message; `1`. |
| 3 | `env -u NEXT_PUBLIC_API_BASE_URL node frontend/scripts/check-csp.mjs; echo $?` | `check-csp: NEXT_PUBLIC_API_BASE_URL is not set`; `1`. |
| 4 | Copy `netlify.toml` to `/tmp/nt.toml`, add `https://*.example.org` to `connect-src`, run `NEXT_PUBLIC_API_BASE_URL=<STAGING_API_ORIGIN> node frontend/scripts/check-csp.mjs /tmp/nt.toml; echo $?` | `check-csp: connect-src must not contain a wildcard (SEC-070)`; `1`. |

### TC-082-08 No middleware CSP; fonts self-hosted; no third-party request (privacy spec)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -rn -i "content-security-policy" frontend/middleware.ts frontend/next.config.js frontend/app` | No output (CSP only in `netlify.toml`). |
| 2 | `grep -n "next/font" frontend/app/layout.tsx` | `next/font/local` with the bundled `SourceSans3-latin-variable.woff2`; no `fonts.googleapis.com`. |
| 3 | `cd frontend && npx playwright test tests/e2e/privacy.spec.ts --project=chromium` (local demo stack) | Passes: only the frontend origin and the API origin contacted; no `<audio>`/`<video>`. |
| 4 | `grep -rn "<script src=\|googletagmanager\|analytics" frontend/app frontend/components` | No third-party script or tracker. |

### TC-082-09 Hosted: every response of both sites carries the §4.9 headers

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -sI <FRONTEND_URL>/login` (staging). | `strict-transport-security: max-age=31536000; includeSubDomains`, `x-content-type-options: nosniff`, `x-frame-options: DENY`, `referrer-policy: no-referrer`, `permissions-policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()`, `content-security-policy` equal to the §4.9 string. |
| 2 | `curl -sI <FRONTEND_URL>/residents` and `curl -sI <FRONTEND_URL>/_next/static/<any chunk path from the page source>`. | Same header set on page and static responses. |
| 3 | Repeat steps 1–2 for production `<FRONTEND_URL>`. | Same result. |
| 4 | `curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' http://<site host>/login` | `301`/`308` to `https://`. |

### TC-082-10 Hosted: per-site API origin; deploy previews never call production

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open production `<FRONTEND_URL>/login`, Network panel, sign-in page load. | API requests go only to `<PRODUCTION_API_ORIGIN>`. |
| 2 | Open staging `<FRONTEND_URL>/login`. | API requests go only to `<STAGING_API_ORIGIN>`. |
| 3 | Open the latest deploy preview of an open PR on the staging site. | API requests go only to `<STAGING_API_ORIGIN>`; never to `<PRODUCTION_API_ORIGIN>`. |
| 4 | Netlify → each site → Site configuration → Environment variables (read only). | Staging: `NEXT_PUBLIC_API_BASE_URL` = `<STAGING_API_ORIGIN>`, `NEXT_PUBLIC_APP_ENV` = `staging`; production: `<PRODUCTION_API_ORIGIN>`, `production`; values are origins without `/api/v1`. |
| 5 | View source of each site's `/login` and find `<meta name="echowell-build">`. | Present (compared by the deploy workflows, TRD 16 §4.4 step 3). |

### TC-082-11 Hosted: Netlify variables and features limited to the frontend

| Step | Action | Expected Result |
|---|---|---|
| 1 | Environment variables of both sites (read only). | Only `NEXT_PUBLIC_*`, `NODE_VERSION`, `NEXT_TELEMETRY_DISABLED`; none holds a key, token or password. |
| 2 | Site configuration: Functions, Forms, Identity, Blobs, Analytics, Edge Functions. | No Forms, Identity, Blobs or Analytics enabled; functions only those generated by `@netlify/plugin-nextjs`. |

### TC-082-12 Staging deploys from `main`; production only through `deploy-production.yml`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read "## Netlify (frontend)" in `docs/deployment.md`. | Staging site: production branch `main`, auto publishing on, deploy previews on; production site: builds stopped, published only by `deploy-production.yml` (`netlify deploy --build --prod`). |
| 2 | Read `.github/workflows/deploy-production.yml`. | Manual trigger with the `production` environment; uses `NETLIFY_AUTH_TOKEN` and `NETLIFY_PRODUCTION_SITE_ID`. |
| 3 | Hosted (read only): Netlify production site → Deploys. | Every production deploy is a CLI deploy from the workflow; "Builds stopped" shown. |

## API Validation

Not applicable: FEAT-082 is frontend hosting configuration; the only API-related check is the origin the browser calls (TC-082-10).

## Database Validation

Not applicable: FEAT-082 has no database impact.

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Unlisted origin `https://example.org` (TC-082-02) | `check-csp` exits 1 naming the origin; Netlify build would fail and the previous deploy stays published |
| 2 | Origin with path, trailing slash, unset, wildcard (TC-082-07) | `check-csp` exits 1 with the specific message |
| 3 | Plain HTTP to a site (TC-082-09 step 4) | Redirect to HTTPS |
| 4 | Deploy preview calling production (TC-082-10 step 3) | Never happens |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-082-AC-01 | `[[headers]]` block of `netlify.toml` byte-identical to the TRD 12 §4.9 excerpt | TC-082-01, TC-082-09 |
| FEAT-082-AC-02 | `NEXT_PUBLIC_API_BASE_URL=https://example.org node frontend/scripts/check-csp.mjs` exits non-zero; with the staging Render origin it exits 0 | TC-082-02 |
| FEAT-082-AC-03 | `grep -n "NEXT_PUBLIC_API_BASE_URL" netlify.toml` returns nothing; the production backend host matches only the CSP line | TC-082-03 |
| FEAT-082-AC-04 | `netlify.toml` has base `frontend`, the build command, `NODE_VERSION = "20"`, the plugin and the ignore command | TC-082-04 |
| FEAT-082-AC-05 | `Permissions-Policy` contains `camera=()` and `microphone=()` | TC-082-05, TC-082-09 |

## Test Data Requirements

- No resident data except the local `test_v0_1` seed for the privacy spec.
- Placeholders `<STAGING_API_ORIGIN>`, `<PRODUCTION_API_ORIGIN>` (from TRD 12 §4.9 `connect-src`), `<FRONTEND_URL>`, `<site host>`; `https://example.org` as the unlisted origin.
- Variables: `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_APP_ENV`, `NODE_VERSION`, `NEXT_TELEMETRY_DISABLED`, `NETLIFY_PRODUCTION_SITE_ID` (GitHub variable), `NETLIFY_AUTH_TOKEN` (name only).

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-082-FR-01 / DEP-050, SEC-070 | FEAT-082 | TC-082-04 |
| FEAT-082-FR-02 / DEP-051, D-65 | FEAT-082 | TC-082-07, TC-082-10 |
| FEAT-082-FR-03 / DEP-054 | FEAT-082 | TC-082-03, TC-082-10 |
| FEAT-082-FR-04 / DEP-052 | FEAT-082 | TC-082-04 |
| FEAT-082-FR-05 / DEP-053, SEC-062, SEC-071, FE-061 | FEAT-082 | TC-082-01, TC-082-05, TC-082-09 |
| FEAT-082-FR-06 / SEC-070, FE-060, TPS-051 | FEAT-082 | TC-082-02, TC-082-06, TC-082-07 |
| FEAT-082-FR-07 / FE-060, SEC-075 | FEAT-082 | TC-082-08 |
| FEAT-082-FR-08 / TPS-011, SEC-054 | FEAT-082 | TC-082-11 |
| FEAT-082-FR-09 / TPS-010 | FEAT-082 | TC-082-11 |
| FEAT-082-FR-10 / SEC-072, SEC-073, TPS-050, TPS-081, TPS-085 | FEAT-082 | TC-082-08 |
| FEAT-082-FR-11 / DEP-002, DEP-004, CIC-001 | FEAT-082 | TC-082-12 |
| FE-192 | FEAT-082 | TC-082-08 |
