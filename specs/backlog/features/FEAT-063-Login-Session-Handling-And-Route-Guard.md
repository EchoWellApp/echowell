# FEAT-063 Login, session handling and route guard

| Field | Value |
|---|---|
| Epic | Frontend |
| Build phase | Phase 8 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-062, FEAT-020 |
| Status | Not Started |

## Purpose

Let staff sign in and keep every dashboard page behind a valid session. The feature implements the `/login` page, the token store (`lib/auth.ts`, memory plus `sessionStorage` mirror), `AuthProvider` (restore, `GET /auth/me`, sign-in, sign-out), `AuthGuard` for the protected route group, expiry handling (scheduled sign-out at `exp`, redirect on any 401), safe `next` handling against open redirects, and the role helpers in `lib/roles.ts` that later pages use to show or hide controls. Wireframe v0.2 (SRC-21) does not draw the login page; it keeps its v0.12 content in the v0.2 visual style (TRD 24 D-111): the app bar with the brand only, the yellow data bar (UX-400), a centred panel and the v0.2 primary button.

## Business Context

- BR-16 (only authorised staff see resident data; audited access): sign-in with e-mail and password, 60-minute JWT, logout audited by the backend.
- D-111 (wireframe v0.2): login is kept although not drawn in SRC-21, restyled with the v0.2 tokens (D-112).
- FRs covered (BACKLOG.md): FR-210, FR-211, FR-217.

## Referenced TRDs

- TRD 04 FE-050..FE-059 (token storage, no persistent storage, exp parsing and scheduled sign-out, restore rule, `GET /auth/me`, guard redirect, 401 handling, safe `next`, sign-out, role helpers), §4.5.1 decision and sequence, FE-066 (input attributes), FE-188 (E2E `auth.spec.ts`).
- TRD 11 (v0.13) UX-170..UX-176 (login panel layout, error copy, 429 copy, expiry copy, busy state, data bar on the login page, no self-registration), §4.9 (app bar with the brand only); the primary button style of UX-122 and the data bar of UX-400 are owned by FEAT-062 and FEAT-064 and reused here.
- TRD 12 SEC-037 (memory + sessionStorage only), SEC-038 (redirect and expiry message).
- TRD 19 E-02 `POST /auth/login`, E-03 `POST /auth/logout`, E-04 `GET /auth/me`.
- TRD 02 FR-210, FR-211, FR-217.
- TRD 13 E2E scenarios E2E-01, E2E-02; TST-094 (page tests incl. 401 → `/login`).
- TRD 24 D-111, D-112; SRC-21.

## Scope

- `frontend/app/login/page.tsx` with `LoginForm` (`{ next, reason }`).
- `frontend/lib/auth.ts` (module-scoped token, `sessionStorage["echowell.auth"]` mirror `{token, exp}`, base64url JWT payload decode for `exp`, try/catch fallback to memory).
- `frontend/lib/AuthProvider.tsx` (`useAuth()` exposing `{ id, email, displayName, role }`, `signIn`, `signOut`).
- `frontend/app/(protected)/layout.tsx` rendering `AuthGuard`.
- 401 handler registered with `api.ts` (FEAT-062): clear token, cancel and clear queries, navigate to `/login?reason=expired&next=<path>`.
- `frontend/lib/roles.ts`: `canWriteNotes`, `canReviewAlarms`, `isAdmin`, `canSeeStudyTeam`.
- Page tests and `auth.spec.ts`.

## Out of Scope

- Backend authentication endpoints, JWT issue/verify and rate limiting (FEAT-020, FEAT-022).
- `AppHeader` with the "Sign out" button and display name, and the `DataBar` component (FEAT-064 renders them, calling `signOut` from this feature; the login page uses the brand-only app bar variant and the data bar).
- Role-based page access-denied states for `/admin` and `/study` (FEAT-064).
- Password reset or self-registration (not in the MVP, UX-176).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-063-FR-01 | `/login` shall show the app bar with the brand "EchoWell" only (no facility line, no navigation) and the data bar of UX-400 (before `meta` is available: "No audio is stored or played anywhere in EchoWell."), then, centred in a panel (`--surface`, 1px `--rule` border, radius 6px, max width 400px, padding 24px), the `<h1>` "EchoWell" (26px, weight 700), the line "Sign in to see voice check-ins" (`--muted`), fields "Email" (`type="email"`, `autocomplete="username"`) and "Password" (`type="password"`, `autocomplete="current-password"`), a full-width primary "Sign in" button (UX-122 primary style: `--chrome` background, `--chrome-ink` text, weight 700, min-height 44px) and the line "Accounts are created by the EchoWell admin." (14px, `--muted`); no self-registration or password reset. | UX-170, UX-175, UX-176, FE-066 |
| FEAT-063-FR-02 | Signing in shall call `POST /api/v1/auth/login`; while pending the button reads "Signing in…" and is disabled. | UX-174, FR-210, E-02 |
| FEAT-063-FR-03 | A 401 `INVALID_CREDENTIALS` shall show "Email or password is incorrect." above the button in a `role="alert"` region without revealing which field was wrong; a 429 shall show "Too many sign-in attempts. Wait one minute and try again." | UX-171, UX-172 |
| FEAT-063-FR-04 | After `reason=expired` redirects the page shall show "Your session has ended. Please sign in again." | UX-173, SEC-038 |
| FEAT-063-FR-05 | `lib/auth.ts` shall hold the access token in a module-scoped variable mirrored to `sessionStorage["echowell.auth"]` as `{ "token": string, "exp": number }`, with every `sessionStorage` access in try/catch falling back to memory only. | FE-050, SEC-037 |
| FEAT-063-FR-06 | The token shall never be written to `localStorage`, cookies, IndexedDB, a URL or query string, the console or an error report. | FE-051, SEC-037 |
| FEAT-063-FR-07 | After login the frontend shall decode the JWT payload (base64url, no signature check) to read `exp` and schedule automatic sign-out at `exp`. | FE-052 |
| FEAT-063-FR-08 | On startup `AuthProvider` shall restore the stored token only if `exp` is more than 30 s in the future, otherwise delete it; after restoring or receiving a token it shall call `GET /api/v1/auth/me` and expose `{ id, email, displayName, role }` through `useAuth()`, while `AuthGuard` shows the page-level loading state. | FE-053, FE-054, E-04 |
| FEAT-063-FR-09 | `AuthGuard` shall redirect to `/login?next=<current path and hash, URL-encoded>` when no valid token exists. | FE-055, FR-211, SEC-038 |
| FEAT-063-FR-10 | On any 401 response the client shall clear the token (memory and `sessionStorage`), call `queryClient.cancelQueries()` and `queryClient.clear()`, and navigate to `/login?reason=expired&next=<current path>`. | FE-056, FR-211 |
| FEAT-063-FR-11 | After sign-in the page shall navigate to `next` only if it starts with a single `/` and neither starts with `//` nor contains `://`; otherwise to `/residents`. | FE-057 |
| FEAT-063-FR-12 | `signOut` shall send `POST /api/v1/auth/logout` best-effort (errors ignored, 3 s timeout), then clear the token and query cache and navigate to `/login`. | FE-058, FR-217, E-03 |
| FEAT-063-FR-13 | `lib/roles.ts` shall define `canWriteNotes(role)` and `canReviewAlarms(role)` true for admin and clinician, `isAdmin(role)` true for admin, `canSeeStudyTeam(role)` true for admin and researcher. | FE-059 |

## Inputs

- User-entered e-mail and password; `next` and `reason` query parameters.
- `POST /api/v1/auth/login` → `Token {access_token, token_type, expires_in, user}`; `GET /api/v1/auth/me` → `User`.

## Outputs

- In-memory token and `sessionStorage` mirror; `useAuth()` context; redirects; logout request.

## Data Flow

`/login` → `login(email, password)` → token stored (memory + sessionStorage) → `exp` read, sign-out scheduled → `getMe()` → navigate to safe `next` or `/residents`. Protected route → `AuthGuard` → token valid? → render, else `/login?next=…`. Any API 401 → clear token and cache → `/login?reason=expired&next=…`. Sign out → `POST /auth/logout` (best effort) → clear → `/login`.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-062, FEAT-020

- FEAT-062 provides `api.ts`, the query client and the 401 hook point.
- FEAT-020 provides the JWT authentication endpoints.

Features that build directly on this one (BACKLOG.md §4): FEAT-064.

## Database Impact

None directly. The backend records `auth.login.succeeded`, `auth.login.failed` and `auth.logout` audit rows (FEAT-020).

## API Impact

Endpoints consumed: `POST /api/v1/auth/login` (E-02), `GET /api/v1/auth/me` (E-04), `POST /api/v1/auth/logout` (E-03). None exposed.

## Frontend Impact

- Pages: `/login` (`app/login/page.tsx`), protected route group layout `app/(protected)/layout.tsx`.
- Components and modules: `LoginForm`, `AuthGuard`, `AuthProvider` (`lib/AuthProvider.tsx`), `lib/auth.ts`, `lib/roles.ts`.

## Analytics Impact

None.

## Security Requirements

- Token only in memory and `sessionStorage`; never `localStorage` or cookies; no CSRF token needed (SEC-037, FE-051).
- Open-redirect prevention on `next` (FE-057).
- Generic login error that does not reveal which field was wrong (UX-171).
- Expired or invalid tokens always lead back to `/login` (FR-211); the 60-minute expiry is enforced client-side by scheduled sign-out (FE-052).

## Error Handling

- 401 on login → generic error; 429 → wait message; network error → `SectionState`-style message with reference (FEAT-062).
- `sessionStorage` unavailable → memory-only storage (FE-050).
- Logout request failure or timeout is ignored; local sign-out always completes (FE-058).

## Logging Requirements

- No client logging of credentials or tokens (FE-051, LOG-082).
- Audit rows are written by the backend for login success, failure and logout (TRD 12 §4.12); the frontend triggers `auth.logout` through `POST /auth/logout`.

## Testing Requirements

- Unit (`frontend/tests/unit/auth.test.ts`): exp parsing, restore rule (> 30 s), storage fallback, no `localStorage` write.
- Page (`frontend/tests/pages/login.test.tsx`, MSW): populated form, brand-only app bar and data bar text, wrong credentials message, 429 message, `reason=expired` message, busy state, safe/unsafe `next` (TST-094).
- Guard page test: protected route without token → `/login?next=…`; 401 from any call → `/login?reason=expired&next=…` (TST-094).
- E2E: `auth.spec.ts` (FE-188), E2E-01 login lands on `/residents`, E2E-02 bad login shows error and stores no token.
- Inspection: built `.next/static` shows only `sessionStorage` usage for the token key (AC-FE-06).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-063-AC-01 | Opening any protected route without a token redirects to `/login`; after sign-in the user returns to that route; `next=https://example.com` and `next=//evil` lead to `/residents`. | AC-FE-05; FE-188 |
| FEAT-063-AC-02 | E2E-01: logging in as the seeded clinician from `/` lands on `/residents`. | E2E-01 |
| FEAT-063-AC-03 | E2E-02: a wrong password shows "Email or password is incorrect.", stores no token in `sessionStorage`, and the backend records a failed-login audit row. | E2E-02; UX-171 |
| FEAT-063-AC-04 | A mocked 401 on `GET /residents` clears `sessionStorage["echowell.auth"]` and navigates to `/login?reason=expired&next=%2Fresidents`, where "Your session has ended. Please sign in again." is shown. Verified by: Guard page test (TST-094). | FE-056; UX-173 |
| FEAT-063-AC-05 | Searching the built `.next/static` output shows the token key used only with `sessionStorage`; no `localStorage` write of the token exists. Verified by: Inspection (built `.next/static` shows only `sessionStorage` usage for the token key (AC-FE-06)). | AC-FE-06 |
| FEAT-063-AC-06 | "Sign out" sends `POST /api/v1/auth/logout`, clears the token and navigates to `/login`, also when the logout request fails. Verified by: E2E (`auth.spec.ts`; FE-188, E2E-01, E2E-02). | FE-058; FR-217 |
| FEAT-063-AC-07 | A mocked 429 on login shows "Too many sign-in attempts. Wait one minute and try again." Verified by: E2E (`auth.spec.ts`; FE-188, E2E-01, E2E-02). | UX-172 |
| FEAT-063-AC-08 | `/login` shows the brand-only app bar, the data bar "No audio is stored or played anywhere in EchoWell.", the `<h1>` "EchoWell" and the primary "Sign in" button in the v0.2 style, and no navigation links. Verified by: Page test (`frontend/tests/pages/login.test.tsx`; TST-094). | UX-170; UX-175; D-111 |

## Definition of Done

- All FEAT-063 acceptance criteria pass; `npm run test` and the `auth.spec.ts` E2E pass in Chromium.
- No token persistence beyond `sessionStorage` (inspection recorded in the batch report, AGT-022).

## Implementation Notes

- `"use client"` is required in `providers.tsx`, `(protected)/layout.tsx` and the login page (TRD 04 §8).
- The token is a Bearer header, not a cookie, because frontend and backend are different sites (TRD 04 §4.5.1).
- Clear the scheduled sign-out timer on manual sign-out and on new sign-in.
- E2E scenarios other than E2E-01, E2E-02 and FE-188 reuse the per-role sessions stored by `globalSetup` (D-74), so the login form is exercised only by these tests.
- `canSeeStudyTeam` replaces the v0.1 `canSeeAnalytics` helper (the Analytics page is now the Study team page `/study`, TRD 24 D-110); if TRD 04 FE-059 keeps the old name, TRD 04 wins (AGT-001).
