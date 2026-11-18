# FEAT-004 Frontend scaffold

## Feature Description

FEAT-004 creates the `frontend/` application shell: a Next.js 14.2 App Router project in TypeScript (`strict: true`) with pinned packages and a committed `package-lock.json`, ESLint and Prettier, Vitest with v8 coverage (80 % lines), Playwright configuration, safe `next.config.js` defaults (`reactStrictMode: true`, `poweredByHeader: false`, no `images.remotePatterns`), the build-time check of `NEXT_PUBLIC_API_BASE_URL` / `NEXT_PUBLIC_APP_ENV` in `frontend/lib/config.ts`, self-hosted fonts with no request to Google font hosts, the environment ribbon ("LOCAL" / "STAGING – synthetic data") and a `/login` route that renders. No dashboard page is part of this feature.

## Preconditions

- Node.js 20 (`node --version` prints `v20.x`) and npm; commands run inside `frontend/` unless stated.
- A clean checkout (`git status` clean) so `npm ci` uses the committed lockfile.
- For build cases export the local values: `export NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 NEXT_PUBLIC_APP_ENV=local`.
- For TC-004-07 and TC-004-09 the local Docker Compose stack (`docker compose up --build -d`) or `npm run build && npm run start` on port 3000.
- A browser (Chromium or Firefox) with developer tools for the network check.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-004-01 | Full scaffold command chain exits 0 on Node 20 | High | Positive |
| TC-004-02 | Vitest smoke test renders `/login` | High | UI |
| TC-004-03 | Build fails when `NEXT_PUBLIC_API_BASE_URL` is unset | High | Negative |
| TC-004-04 | Build fails for `http://` URL with `NEXT_PUBLIC_APP_ENV=staging`, and for a URL with a path | High | Negative |
| TC-004-05 | No Google font host is referenced; only the TRD-approved font file is tracked | High | Security |
| TC-004-06 | `package.json` scripts and pinned versions; no bare `test:e2e` script | High | Positive |
| TC-004-07 | `next.config.js` safe defaults; responses carry no `X-Powered-By` | High | Security |
| TC-004-08 | No LLM or audio dependency or component | High | Negative |
| TC-004-09 | Ribbon shows "LOCAL" for local, "STAGING – synthetic data" for staging, nothing for production | High | UI |
| TC-004-10 | ESLint, Prettier, TypeScript strict and coverage configuration match the TRD | Medium | Positive |
| TC-004-11 | Lint warning or type error makes the chain fail | Medium | Negative |
| TC-004-12 | Public variables read only in `lib/config.ts`; no secret or database URL in frontend code | Medium | Security |

### TC-004-01 Full scaffold command chain exits 0 on Node 20

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `node --version`. | `v20.` followed by the minor version. |
| 2 | Run `npm ci && npm run lint && npm run typecheck && npm run format:check && npm run test && npm run build; echo "exit=$?"`. | `npm ci` installs from `package-lock.json` without changing it; lint prints no warning; `tsc --noEmit` prints nothing; Prettier prints `All matched files use Prettier code style!`; Vitest reports all test files passed; `next build` prints the route table; last line `exit=0`. |
| 3 | Run `git status --porcelain package-lock.json`. | No output (lockfile unchanged). |

### TC-004-02 Vitest smoke test renders `/login`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `npx vitest run tests/pages/login.test.tsx`. | `2 passed`; test "renders the brand-only header, the data bar and the form" passes. |
| 2 | Open `http://localhost:3000/login` in the browser. | The page renders a level-1 heading "EchoWell", the text "No audio is stored or played anywhere in EchoWell." in the data bar, and a sign-in form; the tab title is "Sign in – EchoWell". |

### TC-004-03 Build fails when `NEXT_PUBLIC_API_BASE_URL` is unset

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `env -u NEXT_PUBLIC_API_BASE_URL NEXT_PUBLIC_APP_ENV=local npm run build; echo "exit=$?"`. | Build stops with `Error: Invalid frontend configuration: NEXT_PUBLIC_API_BASE_URL is required`; `exit` is non-zero. |
| 2 | Run `env -u NEXT_PUBLIC_APP_ENV NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 npm run build; echo "exit=$?"`. | Build stops with `Invalid frontend configuration: NEXT_PUBLIC_APP_ENV must be local, staging or production`; non-zero exit. |
| 3 | Run `npx vitest run tests/unit/config.test.ts`. | All tests pass (missing URL, non-absolute URL, URL with a path, `http://` with staging each throw). |

### TC-004-04 Build fails for `http://` URL with `NEXT_PUBLIC_APP_ENV=staging`, and for a URL with a path

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `NEXT_PUBLIC_API_BASE_URL=http://api.example.org NEXT_PUBLIC_APP_ENV=staging npm run build; echo "exit=$?"`. | Build fails with `Invalid frontend configuration: NEXT_PUBLIC_API_BASE_URL must use https:// in staging and production`; non-zero exit. |
| 2 | Same with `NEXT_PUBLIC_APP_ENV=production`. | Same message; non-zero exit. |
| 3 | Run with `NEXT_PUBLIC_API_BASE_URL=https://api.example.org/api/v1 NEXT_PUBLIC_APP_ENV=staging`. | Fails with `NEXT_PUBLIC_API_BASE_URL must be an origin only (no path, no /api/v1, no trailing slash)`. |
| 4 | Run with `NEXT_PUBLIC_API_BASE_URL=api.example.org NEXT_PUBLIC_APP_ENV=local`. | Fails with `NEXT_PUBLIC_API_BASE_URL must be an absolute http(s) URL`. |
| 5 | Run with `NEXT_PUBLIC_API_BASE_URL=https://api.example.org NEXT_PUBLIC_APP_ENV=staging`. | Build succeeds (`exit=0`). |

### TC-004-05 No Google font host is referenced; only the TRD-approved font file is tracked

| Step | Action | Expected Result |
|---|---|---|
| 1 | After TC-004-01 run `grep -rn "fonts.googleapis.com\|fonts.gstatic.com" .next/server .next/static; echo "exit=$?"`. | No `<link>` or CSS `url(` to either host is printed; `exit=1`. |
| 2 | Run `git ls-files .. \| grep -iE '\.(woff2?\|ttf\|otf\|eot)$'` from `frontend/`. | Exactly one path: `frontend/app/fonts/SourceSans3-latin-variable.woff2`; its licence `frontend/app/fonts/OFL.txt` is tracked. |
| 3 | Open `http://localhost:3000/login`, open developer tools Network tab, reload with cache disabled. | No request to `fonts.googleapis.com` or `fonts.gstatic.com`; the font loads from the frontend origin (`/_next/static/media/…woff2`). |

Note: FEAT-004-AC-04 and FR-04 (IBM Plex via `next/font/google`, no font file committed) are superseded by TRD 04 FE-004 v0.15 and TRD 18 GIT-097 (TRD 24 D-112, D-168, D-179): Source Sans 3 is loaded with `next/font/local` from the one committed woff2 (frontend/app/layout.tsx:5,15). The case follows the current TRD.

### TC-004-06 `package.json` scripts and pinned versions; no bare `test:e2e` script

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `node -e "console.log(Object.keys(require('./package.json').scripts).join('\n'))"`. | Includes `lint`, `typecheck`, `format:check`, `test`, `test:coverage`, `build`, `gen:api`; does not include a script named exactly `test:e2e` (only `test:e2e:readonly`, `test:e2e:mutating`, `test:e2e:isolated`). |
| 2 | Run `node -e "const p=require('./package.json'); console.log(p.dependencies.next, p.dependencies.react, p.dependencies['@tanstack/react-query'], p.dependencies.recharts)"`. | `14.2.35 18.3.1 5.107.1 2.13.3` (next 14.2.x, react 18.3.x, TanStack Query 5.x, Recharts 2.x); no `^` or `~` prefix. |
| 3 | Run `node -e "console.log(require('./package.json').scripts['gen:api'])"`. | `openapi-typescript ../docs/api_reference/openapi.json -o lib/api-types.ts`. |
| 4 | Run `git ls-files package-lock.json`. | `package-lock.json` is tracked. |
| 5 | Run `node -e "console.log(Object.keys(require('./package.json').dependencies).join(','))"`. | `@tanstack/react-query,next,react,react-dom,recharts`: no UI component library and no chart library other than Recharts. |

### TC-004-07 `next.config.js` safe defaults; responses carry no `X-Powered-By`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `cat next.config.js`. | Contains `reactStrictMode: true` and `poweredByHeader: false`; `env.NEXT_PUBLIC_GIT_SHA` is `process.env.COMMIT_REF \|\| process.env.GIT_SHA \|\| "unknown"`; no `images` key and no `remotePatterns`. |
| 2 | With the production build served (`npm run build && npm run start`), run `curl -s -I http://localhost:3000/login`. | Status `200`; no `X-Powered-By` header in the response. |
| 3 | Run `grep -rn "@netlify\|netlify/functions" app components lib services; echo "exit=$?"`. | `exit=1` (no Netlify-specific API, FE-044). |

### TC-004-08 No LLM or audio dependency or component

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -rniE "openai\|anthropic\|langchain\|audio" . --include=*.ts --include=*.tsx --include=package.json --exclude-dir=node_modules --exclude-dir=.next`. | No dependency and no component that records, uploads or plays audio. Matches are limited to wording that states audio is absent (for example `"No audio is stored or played anywhere in EchoWell."`, `"Audio never leaves the device. Only voice measurements are uploaded."`), the `audio_quality_flag` field in generated API types, and tests asserting absence. |
| 2 | Run `grep -n "openai\|anthropic\|langchain" package.json package-lock.json; echo "exit=$?"`. | `exit=1`. |
| 3 | Run `grep -rn "<audio\|<video\|getUserMedia\|MediaRecorder" app components lib; echo "exit=$?"`. | `exit=1`. |

### TC-004-09 Ribbon shows "LOCAL" for local, "STAGING – synthetic data" for staging, nothing for production

| Step | Action | Expected Result |
|---|---|---|
| 1 | With the Compose dev frontend (`NEXT_PUBLIC_APP_ENV=local`) open `http://localhost:3000/login`. | A ribbon with role `note` and text `LOCAL` is the first element at the top of `<body>`; it has no close button; font is the monospace token (`var(--font-mono)`) at 12px. |
| 2 | Build and start with `NEXT_PUBLIC_API_BASE_URL=https://api.example.org NEXT_PUBLIC_APP_ENV=staging`, open `/login`. | Ribbon text is exactly `STAGING – synthetic data` (en dash). |
| 3 | Build and start with `NEXT_PUBLIC_API_BASE_URL=https://api.example.org NEXT_PUBLIC_APP_ENV=production`, open `/login`. | No ribbon element is rendered (no element with role `note` carrying an environment label). |
| 4 | Run `npx vitest run components/EnvironmentRibbon/EnvironmentRibbon.test.tsx`. | 3 tests pass (local, staging, production). |

### TC-004-10 ESLint, Prettier, TypeScript strict and coverage configuration match the TRD

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `cat .eslintrc.json`. | `extends` = `next/core-web-vitals`, `plugin:@typescript-eslint/recommended`, `plugin:jsx-a11y/strict`, `prettier`; rules `react/no-danger: error`, `no-console: ["error", {"allow": ["warn", "error"]}]`, `@typescript-eslint/no-explicit-any: error`. |
| 2 | Run `cat .prettierrc`. | `printWidth: 100`, `singleQuote: false`, `trailingComma: "all"`, `semi: true`. |
| 3 | Run `grep -n '"strict"' tsconfig.json`. | `"strict": true`. |
| 4 | Run `grep -n "provider\|thresholds" vitest.config.ts`. | `provider: "v8"` and `thresholds: { lines: 80 }`. |
| 5 | Run `node -e "console.log(require('./package.json').scripts.lint)"`. | `next lint --max-warnings 0`. |

### TC-004-11 Lint warning or type error makes the chain fail

| Step | Action | Expected Result |
|---|---|---|
| 1 | In a scratch copy add `console.log("x");` inside the component in `app/login/page.tsx` and run `npm run lint; echo "exit=$?"`. | ESLint reports `no-console`; non-zero exit. |
| 2 | Revert, then add `const n: number = "x";` to the same file and run `npm run typecheck; echo "exit=$?"`. | `error TS2322: Type 'string' is not assignable to type 'number'.`; non-zero exit. |
| 3 | Revert, then change one double quote to a single quote in a string in the same file and run `npm run format:check; echo "exit=$?"`. | Prettier lists `app/login/page.tsx`; non-zero exit. Revert afterwards. |

### TC-004-12 Public variables read only in `lib/config.ts`; no secret or database URL in frontend code

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -rn "process.env.NEXT_PUBLIC_API_BASE_URL\|process.env.NEXT_PUBLIC_APP_ENV" app components lib services middleware.ts`. | Matches only in `lib/config.ts`. |
| 2 | Run `grep -rniE "DATABASE_URL\|JWT_SECRET\|SEED_\|postgres(ql)?://" app components lib services middleware.ts next.config.js; echo "exit=$?"`. | `exit=1`. |
| 3 | Run `grep -rn "NEXT_PUBLIC_" ../.env.development.example`. | Only `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_APP_ENV` (no secret under a `NEXT_PUBLIC_` name). |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `curl -s -I http://localhost:3000/login` against the production build | 200; no `X-Powered-By` header |
| 2 | Browser network log while loading `/login` | Requests go only to the frontend origin and `NEXT_PUBLIC_API_BASE_URL`; none to Google font hosts |

The frontend scaffold consumes no backend endpoint itself; backend endpoints are exercised from FEAT-062 onward.

## Database Validation

Not applicable: the frontend never connects to the database (FE-173); no table is read or written by this feature.

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Build without `NEXT_PUBLIC_API_BASE_URL` (TC-004-03) | Build fails naming the variable |
| 2 | Build with `http://` URL and `staging` (TC-004-04) | Build fails: must use https:// |
| 3 | Build with a URL containing `/api/v1` (TC-004-04) | Build fails: origin only |
| 4 | Add `console.log` / a type error / a formatting difference (TC-004-11) | Corresponding script exits non-zero |
| 5 | Search for LLM or audio components (TC-004-08) | None found |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-004-AC-01 | On Node 20, `npm ci && npm run lint && npm run typecheck && npm run format:check && npm run test && npm run build` exits 0. | TC-004-01 |
| FEAT-004-AC-02 | The Vitest smoke test renders `/login` and passes. | TC-004-02 |
| FEAT-004-AC-03 | Build fails with the URL unset, and with `http://api.example.org` + `staging`. | TC-004-03, TC-004-04 |
| FEAT-004-AC-04 | No `<link>` or CSS URL to Google font hosts in `.next/server` and `.next/static`; font files tracked only as allowed by FE-004/GIT-097 (one Source Sans 3 woff2). | TC-004-05 |
| FEAT-004-AC-05 | `package.json` has the scripts, no exact `test:e2e`, and pins next 14.2.x, react 18.3.x, TanStack Query 5.x, Recharts 2.x. | TC-004-06 |
| FEAT-004-AC-06 | `next.config.js` sets `reactStrictMode: true`, `poweredByHeader: false`, no `images.remotePatterns`; no `X-Powered-By` header. | TC-004-07 |
| FEAT-004-AC-07 | The LLM/audio grep finds no dependency or component. | TC-004-08 |
| FEAT-004-AC-08 | `local` shows "LOCAL" ribbon on `/login`; `production` renders no ribbon. | TC-004-09 |

## Test Data Requirements

- No resident data. Synthetic origins only: `http://localhost:8000`, `http://api.example.org`, `https://api.example.org`.
- Environment variables: `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_APP_ENV` (`local`, `staging`, `production`), optional `GIT_SHA` / `COMMIT_REF`.
- Node.js 20 and the committed `package-lock.json`.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-004-FR-01 (FE-001, ARC-010) | FEAT-004 | TC-004-10 |
| FEAT-004-FR-02 (FE-002, AGT-024) | FEAT-004 | TC-004-06 |
| FEAT-004-FR-03 (FE-003, FE-005, FE-006) | FEAT-004 | TC-004-06 |
| FEAT-004-FR-04 (FE-004, TPS-050, GIT-097; D-112, D-168) | FEAT-004 | TC-004-05 |
| FEAT-004-FR-05 (FE-007, FE-008, AGT-004) | FEAT-004 | TC-004-08 |
| FEAT-004-FR-06 (FE-010) | FEAT-004 | TC-004-01 |
| FEAT-004-FR-07 (FE-012) | FEAT-004 | TC-004-06 |
| FEAT-004-FR-08 (FE-043, ENV-033) | FEAT-004 | TC-004-07 |
| FEAT-004-FR-09 (FE-044) | FEAT-004 | TC-004-07 |
| FEAT-004-FR-10 (ENV-030, FE-170, FE-171, D-65) | FEAT-004 | TC-004-03, TC-004-04, TC-004-12 |
| FEAT-004-FR-11 (FE-173, ENV-031) | FEAT-004 | TC-004-12 |
| FEAT-004-FR-12 (FE-172, ENV-032) | FEAT-004 | TC-004-09 |
| FEAT-004-FR-13 (FE-200, GIT-042) | FEAT-004 | TC-004-10, TC-004-11 |
| FEAT-004-FR-14 (FE-201) | FEAT-004 | TC-004-10 |
| FEAT-004-FR-15 (FE-180, TST-142) | FEAT-004 | TC-004-10 |
| FEAT-004-FR-16 (FE-202, CIC-017, D-73) | FEAT-004 | TC-004-06 |
| FEAT-004-FR-17 (FE-203) | FEAT-004 | TC-004-01, TC-004-11 |
| FEAT-004-FR-18 (TRD 25 §4.6 Phase 3) | FEAT-004 | TC-004-02 |
| AC-FE-01 | FEAT-004 | TC-004-01 |
| AC-ENV-08 | FEAT-004 | TC-004-03, TC-004-04 |
| AC-AGT-03 | FEAT-004 | TC-004-08 |
| TST-003 (page smoke test) | FEAT-004 | TC-004-02 |
