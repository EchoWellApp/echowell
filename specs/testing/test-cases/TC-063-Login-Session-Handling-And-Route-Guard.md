# Login, session handling and route guard

## Feature Description

Staff sign in on `/login` and every dashboard page stays behind a valid session. The feature covers the login page (brand-only app bar, data bar, centred panel, primary "Sign in" button), the token store `lib/auth.ts` (module memory mirrored to `sessionStorage["echowell.auth"]` as `{token, exp}`, never `localStorage`, cookies, URLs or logs), `AuthProvider` (restore if `exp` is more than 30 s ahead, `GET /api/v1/auth/me`, sign-in, sign-out), `AuthGuard` for the protected route group (redirect to `/login?next=<path>`), expiry handling (scheduled sign-out at `exp`, any 401 → `/login?reason=expired&next=<path>`), safe `next` handling against open redirects, and the role helpers of `lib/roles.ts` (TRD 04 FE-050..FE-059, FE-066, FE-188; TRD 11 UX-170..UX-176; TRD 12 SEC-037, SEC-038; TRD 19 E-02, E-03, E-04).

## Preconditions

- Local Docker Compose demo profile running, seeded with `test_v0_1` (DS-07 pipeline run as-of Oct 30, 2026, 3:00 PM CT); `RATE_LIMIT_LOGIN=5/minute` as in `.env.development.example`.
- Seeded users `clinician@example.com` (display name "Clinician"), `researcher@example.com`, `admin@example.com`; passwords from `SEED_CLINICIAN_PASSWORD`, `SEED_RESEARCHER_PASSWORD`, `SEED_ADMIN_PASSWORD` in the environment file.
- Browser with developer tools (Application → Session Storage / Local Storage / Cookies, Network panel). Start each case in a new private window (no stored session).
- `psql` read access to the local database for the audit checks.
- Restart the backend (`docker compose restart backend`) before the rate-limit case to reset the login limiter.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-063-01 | Login page layout: brand-only app bar, data bar, panel, fields, primary button | High | UI |
| TC-063-02 | Clinician signs in from `/` and lands on `/residents` (E2E-01) | High | Positive |
| TC-063-03 | Protected route without token redirects to `/login?next=…` and returns after sign-in | High | Positive |
| TC-063-04 | Unsafe `next` values lead to `/residents` | High | Security |
| TC-063-05 | Wrong password shows generic error, stores no token, audits the failure (E2E-02) | High | Negative |
| TC-063-06 | 429 on login shows the wait message | High | Negative |
| TC-063-07 | Busy state "Signing in…" while the request is pending | Medium | UI |
| TC-063-08 | Token stored only in `sessionStorage["echowell.auth"]`, never `localStorage`/cookies/URL | High | Security |
| TC-063-09 | Session restored on reload; expired stored token discarded | Medium | Positive |
| TC-063-10 | Any 401 clears the token and redirects with "Your session has ended. Please sign in again." | High | Negative |
| TC-063-11 | "Sign out" calls logout, clears the token and goes to `/login`, also when logout fails | High | Positive |
| TC-063-12 | Role helpers: Study team and Admin links and write controls by role | Medium | Security |
| TC-063-13 | Network failure on login shows a connection message | Medium | Negative |
| TC-063-14 | Built output uses the token key only with `sessionStorage` | High | Security |

### TC-063-01 Login page layout

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/login` | Document title "Sign in – EchoWell"; `Cache-Control: private, no-store` on the response |
| 2 | Check the app bar | Shows only "EchoWell" (20px, weight 700); no facility line, no navigation links, no "Sign out" |
| 3 | Check the data bar below it | Reads "No audio is stored or played anywhere in EchoWell." (`--yellow-bg` background, `--yellow` text) |
| 4 | Check the centred panel | Max width 400px, padding 24px, 1px `--rule` border, radius 6px; `<h1>` "EchoWell" (26px, weight 700); line "Sign in to see voice check-ins" in `--muted` |
| 5 | Inspect the fields | "Email" `type="email"` `autocomplete="username"`; "Password" `type="password"` `autocomplete="current-password"`; both have visible labels |
| 6 | Inspect the button | Full-width "Sign in", min-height 44px, `--chrome` background, `--chrome-ink` text, weight 700 |
| 7 | Check the text under the form | "Accounts are created by the EchoWell admin." (14px, `--muted`); no "Register", "Forgot password" or reset link |

### TC-063-02 Clinician sign-in from /

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/` | Redirected to `/login` (no stored token) |
| 2 | Enter `clinician@example.com` and the `SEED_CLINICIAN_PASSWORD` value; click "Sign in" | `POST /api/v1/auth/login` returns 200 with `access_token`, `token_type` "bearer", `expires_in` and `user` |
| 3 | Observe the navigation | URL becomes `/residents`; `GET /api/v1/auth/me` returns 200 with `role` "clinician" |
| 4 | Check the app bar | "EchoWell", facility line "Edgewood, Assisted living", nav "Resident list" with badge "2" and "New admissions"; no "Study team" and no "Admin" link; display name "Clinician" and button "Sign out" |
| 5 | Check the data bar | "Test data only (pipeline test data v0.1, Oct 1–30, 2026). No real residents. No audio is stored or played anywhere in EchoWell." |

### TC-063-03 Guard redirect and return to the requested route

| Step | Action | Expected Result |
|---|---|---|
| 1 | In a new private window open `/residents/R09/log` | Redirected to `/login?next=%2Fresidents%2FR09%2Flog`; no protected content flashes |
| 2 | Sign in as clinician | Lands on `/residents/R09/log` (Check-in log of R09) |
| 3 | Repeat with `/study#devices` signed in as researcher | Lands on `/study` scrolled to `#devices` (hash kept in `next`) |
| 4 | Repeat with `/admissions` and `/admin` (admin) | Each lands on the requested page |

### TC-063-04 Safe next handling

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/login?next=https://example.com` and sign in as clinician | Lands on `/residents`; no request to example.com |
| 2 | Open `/login?next=//evil` and sign in | Lands on `/residents` |
| 3 | Open `/login?next=/residents%3Fx%3Dhttp://evil` (contains `://`) and sign in | Lands on `/residents` |
| 4 | Open `/login?next=/admissions` and sign in | Lands on `/admissions` (valid relative path accepted) |

### TC-063-05 Wrong password

| Step | Action | Expected Result |
|---|---|---|
| 1 | Restart the backend; open `/login`; enter `clinician@example.com` and a wrong password; click "Sign in" | `POST /api/v1/auth/login` returns 401 problem+json with code `INVALID_CREDENTIALS` |
| 2 | Read the message above the button | "Email or password is incorrect." in a `role="alert"` region; it does not say which field was wrong |
| 3 | Repeat with an unknown email `nobody@example.com` | Same message, same status 401 |
| 4 | Check Application → Session Storage | No `echowell.auth` entry; Local Storage and Cookies hold no token |
| 5 | Run the audit query of Database Validation step 1 | A new `audit_logs` row with `action` = 'auth.login.failed', `actor_type` 'system', `details` containing `email` and `reason` |

### TC-063-06 Rate limit message

| Step | Action | Expected Result |
|---|---|---|
| 1 | After a backend restart, submit a wrong password 6 times within one minute | The 6th attempt returns 429 (`RATE_LIMITED`) |
| 2 | Read the message above the button | "Too many sign-in attempts. Wait one minute and try again." |
| 3 | Wait 60 s and sign in with the correct password | Succeeds and lands on `/residents` |

### TC-063-07 Busy state

| Step | Action | Expected Result |
|---|---|---|
| 1 | Throttle the network to "Slow 3G"; submit valid credentials | While the request is pending the button reads "Signing in…" and is disabled |
| 2 | Click the disabled button again | No second `POST /api/v1/auth/login` is sent |

### TC-063-08 Token storage

| Step | Action | Expected Result |
|---|---|---|
| 1 | Sign in as clinician; open Application → Session Storage for the app origin | One key `echowell.auth` with JSON `{"token": "<jwt>", "exp": <number>}` |
| 2 | Check Local Storage, Cookies and IndexedDB | No token, no `echowell.auth` |
| 3 | Check the address bar and Network request URLs | No token in any URL or query string |
| 4 | Check the browser console | No token printed |
| 5 | Run `npx vitest run tests/unit/auth.test.ts` in `frontend/` | Passes (exp parsing, restore > 30 s, storage fallback, no `localStorage` write) |

### TC-063-09 Restore and expiry

| Step | Action | Expected Result |
|---|---|---|
| 1 | Signed in, reload `/residents` | Page stays signed in; `GET /api/v1/auth/me` returns 200; while it loads the page shows the page-level loading state |
| 2 | In Session Storage edit `echowell.auth` so that `exp` is the current epoch seconds + 10, then reload | Entry is deleted and the browser is redirected to `/login?next=%2Fresidents` |
| 3 | Sign in again and leave the tab open past `exp` (or set `exp` near now in a new sign-in via the page test `tests/pages/protected-layout.test.tsx`) | Automatic sign-out at `exp`; redirect to `/login?reason=expired&next=…` |
| 4 | Disable `sessionStorage` (block site data in browser settings) and sign in | Sign-in works with memory-only storage; a reload requires signing in again |

### TC-063-10 401 handling

| Step | Action | Expected Result |
|---|---|---|
| 1 | Sign in as clinician; in Session Storage replace the token value in `echowell.auth` with a syntactically valid but wrongly signed JWT keeping a future `exp`; reload `/residents` | `GET /api/v1/residents` (or `/auth/me`) returns 401 |
| 2 | Observe | `echowell.auth` removed; redirected to `/login?reason=expired&next=%2Fresidents` |
| 3 | Read the login page | "Your session has ended. Please sign in again." |
| 4 | Sign in | Returns to `/residents`; no data from the previous session is shown before the new fetch (cache cleared) |

### TC-063-11 Sign out

| Step | Action | Expected Result |
|---|---|---|
| 1 | Signed in as clinician, click "Sign out" in the app bar | `POST /api/v1/auth/logout` sent with Bearer token, returns 204 |
| 2 | Observe | `echowell.auth` removed; URL `/login` |
| 3 | Press the browser Back button | Redirected to `/login?next=…`; no resident data visible |
| 4 | Sign in again; block `*/api/v1/auth/logout*` in the Network panel; click "Sign out" | Local sign-out still completes within about 3 s: token removed, URL `/login` |
| 5 | Run the audit query of Database Validation step 2 | An `audit_logs` row `auth.logout` for the clinician's user ID for the unblocked logout of step 1 |

### TC-063-12 Role helpers

| Step | Action | Expected Result |
|---|---|---|
| 1 | Sign in as researcher | Nav shows "Resident list", "New admissions", "Study team"; no "Admin" |
| 2 | Open `/residents/R09/review` as researcher | Staff notes panel shows "Only clinicians and admins can add notes."; review panel shows "Only clinicians and admins can review alarms." |
| 3 | Sign in as admin | Nav shows "Resident list", "New admissions", "Study team", "Admin"; the note form and review form are available |
| 4 | Sign in as clinician | No "Study team", no "Admin"; note form and review form available |

### TC-063-13 Network failure on login

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/login`, set the Network panel to "Offline", submit valid credentials | Message "Could not reach EchoWell. Check your connection and try again."; no token stored; button returns to "Sign in" |

### TC-063-14 Built output inspection

| Step | Action | Expected Result |
|---|---|---|
| 1 | In `frontend/`, run `npm run build`, then `grep -rl "echowell.auth" .next/static` | Matches only in the chunk(s) containing `lib/auth.ts` |
| 2 | In those chunks, inspect the code around `echowell.auth` | Used only with `sessionStorage` (`setItem`, `getItem`, `removeItem`); no `localStorage` call with the token key |
| 3 | Run `grep -rn "localStorage" frontend/lib/auth.ts frontend/lib/AuthProvider.tsx` | No output |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/auth/login` with `{"email": "clinician@example.com", "password": "<SEED_CLINICIAN_PASSWORD>"}` | 200 `Token` with `access_token`, `token_type` "bearer", `expires_in` 3600 (or the configured lifetime), `user.role` "clinician" |
| 2 | `POST /api/v1/auth/login` with a wrong password | 401 problem+json, code `INVALID_CREDENTIALS` |
| 3 | `POST /api/v1/auth/login` with `{"email": "not-an-email", "password": ""}` | 422 `VALIDATION_ERROR` with `errors[]` |
| 4 | Six wrong logins within a minute | 429 `RATE_LIMITED` (or `ACCOUNT_TEMPORARILY_LOCKED` after 10 failures in 15 minutes) |
| 5 | `GET /api/v1/auth/me` with the token | 200 `User` `{id, email, display_name, role, active, …}` |
| 6 | `GET /api/v1/auth/me` without token | 401 |
| 7 | `POST /api/v1/auth/logout` with the token | 204 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT occurred_at, actor_type, action, details FROM audit_logs WHERE action = 'auth.login.failed' ORDER BY id DESC LIMIT 1;` | Row from TC-063-05: `actor_type` system, `details` has `email` and `reason` (no password) |
| 2 | `SELECT actor_id, action FROM audit_logs WHERE action IN ('auth.login.succeeded','auth.logout') ORDER BY id DESC LIMIT 4;` | `auth.login.succeeded` for each successful sign-in and `auth.logout` for the sign-out of TC-063-11, `actor_id` = the clinician's `users.id` |
| 3 | `SELECT last_login_at FROM users WHERE email = 'clinician@example.com';` | Updated to the time of the latest successful sign-in |
| 4 | `SELECT count(*) FROM audit_logs WHERE details::text ILIKE '%password%';` | 0 (no password stored) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Wrong password or unknown email | "Email or password is incorrect.", no token (TC-063-05) |
| 2 | Too many attempts | "Too many sign-in attempts. Wait one minute and try again." (TC-063-06) |
| 3 | Offline during sign-in | "Could not reach EchoWell. Check your connection and try again." (TC-063-13) |
| 4 | Protected URL without token | Redirect to `/login?next=…` (TC-063-03) |
| 5 | Invalid or expired token on a call | Redirect to `/login?reason=expired&next=…` with "Your session has ended. Please sign in again." (TC-063-10) |
| 6 | `next` pointing off-site | Lands on `/residents` (TC-063-04) |
| 7 | Logout request fails | Local sign-out still completes (TC-063-11) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-063-AC-01 | Protected route without token → `/login`; after sign-in back to that route; `next=https://example.com` and `next=//evil` → `/residents` | TC-063-03, TC-063-04 |
| FEAT-063-AC-02 | Clinician sign-in from `/` lands on `/residents` | TC-063-02 |
| FEAT-063-AC-03 | Wrong password: "Email or password is incorrect.", no token in `sessionStorage`, failed-login audit row | TC-063-05 |
| FEAT-063-AC-04 | 401 on `GET /residents` clears `echowell.auth` and navigates to `/login?reason=expired&next=%2Fresidents` with "Your session has ended. Please sign in again." | TC-063-10 |
| FEAT-063-AC-05 | Built `.next/static` uses the token key only with `sessionStorage` | TC-063-14, TC-063-08 |
| FEAT-063-AC-06 | "Sign out" sends logout, clears the token, goes to `/login`, also when logout fails | TC-063-11 |
| FEAT-063-AC-07 | 429 on login shows "Too many sign-in attempts. Wait one minute and try again." | TC-063-06 |
| FEAT-063-AC-08 | `/login` shows brand-only app bar, data bar "No audio is stored or played anywhere in EchoWell.", `<h1>` "EchoWell", primary "Sign in", no navigation links | TC-063-01 |

## Test Data Requirements

- Seeded users `clinician@example.com`, `researcher@example.com`, `admin@example.com`; passwords only from the `SEED_*` variables (never written down).
- `test_v0_1` DS-07 data so that `/residents` shows the nav badge "2".
- `RATE_LIMIT_LOGIN=5/minute`; backend restart to reset the limiter between cases.
- A tampered JWT for TC-063-10 is built by editing the stored token in the tester's own browser; no real secret is needed.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-063-FR-01 | FEAT-063 | TC-063-01 |
| FEAT-063-FR-02 | FEAT-063 | TC-063-02, TC-063-07 |
| FEAT-063-FR-03 | FEAT-063 | TC-063-05, TC-063-06 |
| FEAT-063-FR-04 | FEAT-063 | TC-063-10 |
| FEAT-063-FR-05, FR-06 | FEAT-063 | TC-063-08, TC-063-14 |
| FEAT-063-FR-07, FR-08 | FEAT-063 | TC-063-09 |
| FEAT-063-FR-09 | FEAT-063 | TC-063-03 |
| FEAT-063-FR-10 | FEAT-063 | TC-063-10 |
| FEAT-063-FR-11 | FEAT-063 | TC-063-04 |
| FEAT-063-FR-12 | FEAT-063 | TC-063-11 |
| FEAT-063-FR-13 | FEAT-063 | TC-063-12 |
| UX-170, UX-175, UX-176 | FEAT-063 | TC-063-01 |
| UX-171 | FEAT-063 | TC-063-05 |
| UX-172 | FEAT-063 | TC-063-06 |
| UX-173 | FEAT-063 | TC-063-10 |
| UX-174 | FEAT-063 | TC-063-07 |
| FE-050, FE-051 | FEAT-063 | TC-063-08, TC-063-14 |
| FE-052, FE-053, FE-054 | FEAT-063 | TC-063-09 |
| FE-055 | FEAT-063 | TC-063-03 |
| FE-056 | FEAT-063 | TC-063-10 |
| FE-057 | FEAT-063 | TC-063-04 |
| FE-058 | FEAT-063 | TC-063-11 |
| FE-059 | FEAT-063 | TC-063-12 |
| FE-066 | FEAT-063 | TC-063-01 |
| FE-188 | FEAT-063 | TC-063-03, TC-063-04, TC-063-11 |
| SEC-037 | FEAT-063 | TC-063-08 |
| SEC-038 | FEAT-063 | TC-063-03, TC-063-10 |
| E2E-01 | FEAT-063 | TC-063-02 |
| E2E-02 | FEAT-063 | TC-063-05 |
| TST-094 | FEAT-063 | TC-063-03, TC-063-10 |
