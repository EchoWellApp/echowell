# FEAT-004 Frontend scaffold (Next.js 14.2 App Router, TypeScript, lint, test tooling)

| Field | Value |
|---|---|
| Epic | Frontend |
| Build phase | Phase 3 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-002 |
| Status | Complete |

## Purpose

Create the `frontend/` application shell that every dashboard feature builds on: a Next.js 14.2 App Router TypeScript project with pinned packages, strict compiler settings, ESLint, Prettier, Vitest with v8 coverage, Playwright configuration, safe `next.config.js` defaults, the build-time configuration check for `NEXT_PUBLIC_API_BASE_URL`, self-hosted IBM Plex fonts and a minimal `/login` route so the Phase 3 smoke test renders. No feature pages are built here.

## Business Context

- BR-17: Next.js App Router in TypeScript deployed to Netlify (ARC-010, FE-001), portable to AWS Amplify (FE-044).
- BR-16: no secrets in frontend code or `NEXT_PUBLIC_*` variables (FE-173, ENV-031); no runtime calls to third-party font hosts (FE-004, TPS-050).
- BR-01 and BR-18: no audio and no LLM dependency in the frontend (FE-007, FE-008).

## Referenced TRDs

- TRD 04 FE-001..FE-008 (stack and prohibitions), FE-010..FE-012 (layout, single API client, generated types), FE-043, FE-044 (`next.config.js`, portability), FE-170..FE-173 (environment variables), FE-200..FE-204 (lint, format, CI order, build budget); §4.1 package table; §4.2 layout; FE-180 (coverage configuration); AC-FE-01.
- TRD 21 ENV-030, ENV-031, ENV-033 (and ENV-032 ribbon, implemented as the FE-172 Should).
- TRD 22 TPS-050.
- TRD 16 CIC-017 and §6 (`frontend/package.json` script names).
- TRD 13 TST-003, TST-004, TST-142.
- TRD 24 D-65 (API base URL is an origin only), D-73 (no bare `test:e2e` script).

## Scope

- `frontend/` Next.js 14.2.x App Router project in TypeScript 5.x (`strict: true`, `noUncheckedIndexedAccess`, `noImplicitOverride`), React 18.3.x, pinned per TRD 04 §4.1, `package-lock.json` committed, `.nvmrc` = `20`.
- Keep and fill the existing `frontend/package.json`, `frontend/next.config.js` and `frontend/services/api.ts` (FE-010).
- Runtime dependencies installed now: `next`, `react`, `react-dom`, `@tanstack/react-query` 5.x, `recharts` 2.x; dev dependencies from §4.1 (openapi-typescript 7.x, vitest 2.x, `@vitest/coverage-v8` 2.x, Testing Library, jsdom 25.x, msw 2.x, `@playwright/test`, `@axe-core/playwright`, ESLint 8.x set, Prettier 3.x, `eslint-config-prettier`).
- `package.json` scripts: `dev`, `build`, `start`, `lint`, `typecheck`, `format`, `format:check`, `test`, `test:coverage`, `test:e2e:readonly`, `test:e2e:mutating`, `test:e2e:isolated`, `gen:api` (TRD 16 §6, FE-012).
- `.eslintrc.json` per FE-200, `.prettierrc` per FE-201, `tsconfig.json`, `vitest.config.ts` per FE-180, `vitest.setup.ts`, `playwright.config.ts` and `playwright.isolated.config.ts` skeletons per TST-004.
- `next.config.js` with `reactStrictMode: true`, `poweredByHeader: false`, no `images.remotePatterns`, and `env.NEXT_PUBLIC_GIT_SHA` from `COMMIT_REF`, else `GIT_SHA`, else `unknown`.
- `frontend/lib/config.ts` as the only reader of `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_APP_ENV`, throwing at build time on missing/invalid values; `frontend/.env.example` with local values.
- `app/layout.tsx` (`<html lang="en">`, IBM Plex Sans 400/600 and IBM Plex Mono 400 via `next/font/google`; wireframe v0.2 replaces them with "Source Sans 3" 400/600/700 in checkpoint 7, FEAT-062, TRD 24 D-112), `app/page.tsx` redirecting `/` to `/residents`, and a minimal `app/login/page.tsx` that renders a heading.
- Environment ribbon of FE-172 in the root layout for `local` and `staging`.
- One smoke test (`frontend/tests/pages/login.test.tsx`) that renders `/login`.

## Out of Scope

- API client implementation, generated types, query cache, formatting, wording and tokens (FEAT-062).
- Login form, session handling and route guard (FEAT-063); app chrome and navigation (FEAT-064); every dashboard page (FEAT-065..FEAT-074).
- `middleware.ts` cache headers (FE-042) and the Netlify CSP (FEAT-082).
- Playwright specs and global setup (FEAT-076); accessibility suite (FEAT-075).
- CI workflow (FEAT-007).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-004-FR-01 | `frontend/` shall be a Next.js 14.2.x App Router application in TypeScript 5.x with `strict: true`. | FE-001, ARC-010 |
| FEAT-004-FR-02 | `frontend/package.json` shall pin the packages of TRD 04 §4.1 and `frontend/package-lock.json` shall be committed. | FE-002, AGT-024 |
| FEAT-004-FR-03 | No UI component library, no charting library other than Recharts 2.x, TanStack Query 5.x for server state; React 18.3.x. | FE-003, FE-005, FE-006 |
| FEAT-004-FR-04 | IBM Plex Sans 400/600 and IBM Plex Mono 400 shall be loaded via `next/font/google` (self-hosted at build time) with no runtime request to `fonts.googleapis.com` or `fonts.gstatic.com`, and no font file committed (checkpoint 2 scaffold; FEAT-062 switches to "Source Sans 3" per the current FE-004, TRD 24 D-112). | FE-004, TPS-050, GIT-097 |
| FEAT-004-FR-05 | No dependency, component or route shall handle audio or provide an LLM feature. | FE-007, FE-008, AGT-004 |
| FEAT-004-FR-06 | The source tree shall follow TRD 04 §4.2; existing `package.json`, `next.config.js` and `services/api.ts` are filled in place. | FE-010 |
| FEAT-004-FR-07 | The `gen:api` script shall be `openapi-typescript ../docs/api_reference/openapi.json -o lib/api-types.ts`. | FE-012 |
| FEAT-004-FR-08 | `next.config.js` shall set `reactStrictMode: true`, `poweredByHeader: false`, enable no `images.remotePatterns`, and set `env.NEXT_PUBLIC_GIT_SHA` from `COMMIT_REF`, else `GIT_SHA`, else `unknown`. | FE-043, ENV-033 |
| FEAT-004-FR-09 | Only standard Next.js 14 features shall be used; no Netlify-specific API. | FE-044 |
| FEAT-004-FR-10 | `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_APP_ENV` shall be read only in `frontend/lib/config.ts`; the build shall fail with a clear message when the URL is missing, not an absolute `http(s)` URL, contains a path (origin only), or is `http://` while the app env is `staging` or `production`. | ENV-030, FE-170, FE-171, D-65 |
| FEAT-004-FR-11 | No secret and no database URL shall be referenced from frontend code or any `NEXT_PUBLIC_*` variable. | FE-173, ENV-031 |
| FEAT-004-FR-12 | When `NEXT_PUBLIC_APP_ENV` is not `production`, the root layout shall render a non-dismissable ribbon "STAGING – synthetic data" (staging) or "LOCAL" (local) in IBM Plex Mono 12px at the top of `<body>` (from checkpoint 7 the system monospace stack, TRD 24 D-112). | FE-172, ENV-032 |
| FEAT-004-FR-13 | ESLint shall extend `next/core-web-vitals`, `plugin:@typescript-eslint/recommended`, `plugin:jsx-a11y/strict` and `prettier`, with `react/no-danger: error`, `no-console` allowing only warn/error, `@typescript-eslint/no-explicit-any: error`; `npm run lint` uses `--max-warnings=0`. | FE-200, GIT-042 |
| FEAT-004-FR-14 | Prettier shall use `printWidth: 100`, `singleQuote: false`, `trailingComma: "all"`, `semi: true`. | FE-201 |
| FEAT-004-FR-15 | `vitest.config.ts` shall configure v8 coverage exactly as FE-180 with `thresholds.lines: 80`. | FE-180, TST-142 |
| FEAT-004-FR-16 | The scripts `lint`, `typecheck`, `format:check`, `test:coverage`, `build` shall exist so CI can run them in the FE-202 order; there shall be no bare `test:e2e` script. | FE-202, CIC-017, D-73 |
| FEAT-004-FR-17 | `npm run build` shall finish with zero TypeScript errors and zero ESLint warnings. | FE-203 |
| FEAT-004-FR-18 | A minimal `/login` route shall render so the Phase 3 frontend smoke test passes. | TRD 25 §4.6 Phase 3 Required tests |

## Inputs

- TRD 04 §4.1 and §4.2; `docs/design/Frontend_Architecture.md` (FEAT-001).
- Build-time environment: `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_APP_ENV`, `COMMIT_REF` or `GIT_SHA`.

## Outputs

- A buildable `frontend/` project, `frontend/.env.example`, lint/format/test configuration files, the minimal `/login` page and the smoke test.
- `next build` output with self-hosted fonts and `NEXT_PUBLIC_GIT_SHA` embedded.

## Data Flow

At build: `next.config.js` resolves `NEXT_PUBLIC_GIT_SHA` → `lib/config.ts` validates the public variables and throws on invalid values → Next.js compiles routes, downloads and self-hosts fonts. At runtime: browser requests `/` → redirect to `/residents` (later protected by FEAT-063) → `/login` renders the root layout with fonts and the environment ribbon. No API call is made by this feature.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-002

- FEAT-002 provides the monorepo layout, `.gitignore` entries for `frontend/` build outputs and the pre-commit configuration.

Features that build directly on this one (BACKLOG.md §4): FEAT-006, FEAT-007, FEAT-062.

## Database Impact

None. The frontend holds no database credentials (ARC-014).

## API Impact

None consumed or exposed. `services/api.ts` stays the single HTTP module (FE-011) and is implemented by FEAT-062.

## Frontend Impact

- Pages: `app/layout.tsx`, `app/page.tsx` (redirect), `app/login/page.tsx` (minimal), `app/not-found.tsx`.
- Modules: `lib/config.ts`.
- Configuration: `package.json`, `package-lock.json`, `tsconfig.json`, `.eslintrc.json`, `.prettierrc`, `.nvmrc`, `next.config.js`, `vitest.config.ts`, `vitest.setup.ts`, `playwright.config.ts`, `playwright.isolated.config.ts`, `.env.example`.

## Analytics Impact

None.

## Security Requirements

- No authentication or authorization logic yet (FEAT-063 adds the guard).
- No secret in any frontend file or `NEXT_PUBLIC_*` value (FE-173, ENV-031); `NEXT_PUBLIC_API_BASE_URL` must be `https://` in staging and production (FE-171).
- `poweredByHeader: false`; no remote image domains (FE-043).

## Error Handling

- Invalid or missing `NEXT_PUBLIC_API_BASE_URL` / `NEXT_PUBLIC_APP_ENV`: `next build` fails with a message naming the variable (FE-171, ENV-030, AC-ENV-08).
- Lint warning, type error or formatting difference: the corresponding script exits non-zero (FE-203).

## Logging Requirements

None. `no-console` forbids `console.log` (FE-200). No audit records.

## Testing Requirements

- Page smoke test `frontend/tests/pages/login.test.tsx` (Vitest + React Testing Library + jsdom, TST-003): renders `/login` (TRD 25 §4.6 Phase 3).
- Unit test `frontend/tests/unit/config.test.ts`: `lib/config.ts` throws on a missing URL, a non-absolute URL, a URL with a path, and an `http://` URL with `NEXT_PUBLIC_APP_ENV=staging` (FE-171, AC-ENV-08 second clause).
- Commands: `cd frontend && npm ci && npm run lint && npm run typecheck && npm run format:check && npm run test && npm run build` (AC-FE-01; TRD 25 §4.6 Phase 3 Commands).
- Coverage gate active from the start (TST-142); with only the scaffold the covered source set is small and must still meet 80 %.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-004-AC-01 | In `frontend/` on Node 20, `npm ci && npm run lint && npm run typecheck && npm run format:check && npm run test && npm run build` exits 0. | AC-FE-01, FE-203 |
| FEAT-004-AC-02 | The Vitest smoke test renders `/login` and passes. Verified by: Test (`frontend/tests/pages/login.test.tsx`; TST-003). | TRD 25 §4.6 Phase 3 Required tests |
| FEAT-004-AC-03 | `npm run build` with `NEXT_PUBLIC_API_BASE_URL` unset fails, and with `NEXT_PUBLIC_API_BASE_URL=http://api.example.org` and `NEXT_PUBLIC_APP_ENV=staging` fails. Verified by: Test (run the command in the criterion against the stated environment and check the stated result). | AC-ENV-08, FE-171 |
| FEAT-004-AC-04 | `grep -rn "fonts.googleapis.com\|fonts.gstatic.com" frontend/.next/server frontend/.next/static` after build returns no `<link>` or CSS URL to those hosts, and no font file is tracked by git. Verified by: Inspection (run the command in the criterion and check its output). | FE-004, TPS-050, GIT-097 |
| FEAT-004-AC-05 | `package.json` contains the scripts listed in Scope, does not contain a script named exactly `test:e2e`, and pins `next` 14.2.x, `react` 18.3.x, `@tanstack/react-query` 5.x, `recharts` 2.x. Verified by: Test (`frontend/tests/pages/login.test.tsx`; TST-003). | FE-002, D-73, TRD 16 §6 |
| FEAT-004-AC-06 | `next.config.js` sets `reactStrictMode: true` and `poweredByHeader: false` and has no `images.remotePatterns`; the built app's responses carry no `X-Powered-By` header. Verified by: Inspection (the inspection method of FE-043, applied to the condition stated in the criterion). | FE-043 |
| FEAT-004-AC-07 | `grep -rniE "openai\|anthropic\|langchain\|audio" frontend --include=*.ts --include=*.tsx --include=package.json` (excluding `node_modules`) returns no dependency or component. Verified by: Inspection (run the command in the criterion and check its output). | FE-007, FE-008, AC-AGT-03 |
| FEAT-004-AC-08 | With `NEXT_PUBLIC_APP_ENV=local` the rendered `/login` page shows the text "LOCAL" in the ribbon; with `production` no ribbon is rendered. Verified by: Test (`frontend/tests/pages/login.test.tsx`; TST-003). | FE-172, ENV-032 |

## Definition of Done

- All FEAT-004 acceptance criteria pass.
- Existing skeleton files (`package.json`, `next.config.js`, `services/api.ts`) kept at their paths (FE-010, AGT-010).
- No business page or API call implemented; batch report lists IDs and command results (AGT-022).

## Implementation Notes

- `NEXT_PUBLIC_API_BASE_URL` is an origin only; the client appends `/api/v1` (D-65). Reject a value ending in `/api/v1` at build time.
- Keep `lib/api-types.ts` absent until FEAT-038 has produced `docs/api_reference/openapi.json`; `gen:api` is defined now and first run by FEAT-062.
- `frontend/tests/e2e/.auth/` and `frontend/next-env.d.ts` are git-ignored (TRD 18 §4.11).
- Watch the first-load JS budget of FE-204 (≤ 300 kB gzip per dashboard route) from the start; avoid heavy dependencies in the root layout.
