# FEAT-074 Admin page: users, pipeline runs and CSV upload

| Field | Value |
|---|---|
| Epic | Frontend |
| Build phase | Phase 8 (TRD 25) |
| Priority | P1 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-064, FEAT-037, FEAT-024, FEAT-026 |
| Status | Not Started |

## Purpose

Implement `/admin` for the admin role: an ARIA tabs page with "Users" (list, add user, change role and active flag with confirmation), "Pipeline runs" (latest 50 runs with trigger, status, times, counts and warnings; "Run pipeline now" with status polling; banners for a failed latest run and a missing nightly run), "Upload data" (CSV upload with the synthetic-data warning, polling the batch result: accepted, rejected with row errors, duplicates; whole-file rejection message), and the API status line from the health endpoint. Residents, devices, assignments and API keys stay CLI-managed. Wireframe v0.2 (SRC-21) does not draw the Admin page; it keeps its v0.12 content in the v0.2 visual style (TRD 24 D-111): the app bar with the "Admin" link current, the data bar, the v0.2 tokens and buttons, and the access-denied link "← Resident list".

## Business Context

- BR-16 (user administration by admins only; no self-registration), BR-01 and BR-15 (upload of pipeline-format CSV and visibility of each run's results), RSK-05 (failed or missing runs are visible).
- D-OWNER-3 / D-OWNER-4: the interim stack accepts synthetic or test data only.
- D-111, D-112 (wireframe v0.2): Admin kept although not drawn, restyled with the v0.2 tokens.
- FRs covered (BACKLOG.md): FR-220, FR-221, FR-222, FR-225.

## Referenced TRDs

- TRD 11 (v0.13) — owned by this feature: UX-210..UX-214, UX-216..UX-219 (tabs, users list and form, deactivate confirmation, pipeline runs list and run button, upload tab, synthetic-data line, API status line, whole-file rejection, no master-data editing, nightly-run banner), §4.10. Uses: UX-215 (access-denied state, owned by FEAT-064), the app bar and data bar (UX-010..UX-015, UX-400).
- TRD 04 (v0.11) FE-034 (access denied for non-admins, link "← Resident list"), FE-079 (form field errors), FE-028, §4.6.2 admin client functions, §4.7 admin query keys and `?tab=` URL state, FE-072 (120 s CSV timeout).
- TRD 17 LOG-112 (latest 50 runs, failure banner), LOG-111 ("Nightly run missing for <date>" banner at read time), §4.9.
- TRD 19 E-25, E-26, E-27 (users), E-06, E-07 (ingest), E-20, E-21, E-31 (pipeline runs), E-01 (health).
- TRD 02 FR-220, FR-221, FR-222, FR-225.
- TRD 13 TST-094, TST-110, E2E-14.
- TRD 24 D-96, D-111, D-112; SRC-21.

## Scope

- `app/(protected)/admin/page.tsx` with the `<h1>` "Admin" (the `AppHeader` with `active="admin"` and the `DataBar` come from the protected layout, FEAT-064) and `AdminPanel` (tabs "Users", "Pipeline runs", "Upload data"; `?tab=`; arrow-key navigation).
- Users tab: table "Email", "Display name", "Role", "Active", "Last sign-in"; "Add user" form (Email, Display name, Role select Admin/Clinician/Researcher, Temporary password); per-row "Deactivate"/"Reactivate" with confirmation dialog; role change.
- Pipeline runs tab: latest 50 runs (`GET /pipeline/runs?limit=50`), columns "Started", "Finished", "Trigger", "Profile", "Status", "As of", "Counts" plus warning count; "Run pipeline now" with a profile select offering only `meta.pipeline_profile` (UX-212, D-96); 5-second status polling of a started run; failure and missing-nightly banners.
- Upload tab: file input `.csv` "CSV file (pipeline input format v0.1)", "Upload", result "Accepted <a> · Rejected <r> · Duplicates <d>", rejections table "Row", "Errors", whole-file rejection message, synthetic-data line.
- The line "API status: …" from `GET /health` at the end of the page (14px, `--muted`).

## Out of Scope

- Backend user, ingest and pipeline endpoints (FEAT-037, FEAT-026, FEAT-024); run lifecycle data (FEAT-053, FEAT-056).
- Creation or editing of residents, devices, device assignments and API keys (CLI only, UX-218).
- Access-denied component (FEAT-064).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-074-FR-01 | `/admin` shall show the app bar, the data bar, the `<h1>` "Admin" and three ARIA tabs "Users", "Pipeline runs", "Upload data" with arrow-key navigation; the selected tab is kept in `?tab=`. | UX-210 |
| FEAT-074-FR-02 | Non-admins shall see the access-denied state of FEAT-064 ("You do not have access to this page." with "← Resident list") and no admin API call. | UX-215, FE-034 |
| FEAT-074-FR-03 | "Users" shall list users with "Email", "Display name", "Role", "Active", "Last sign-in", and an "Add user" form (Email, Display name, Role "Admin"/"Clinician"/"Researcher", Temporary password) that calls `POST /api/v1/users`. | UX-211, FR-220, E-25, E-26 |
| FEAT-074-FR-04 | Each row shall offer "Deactivate"/"Reactivate" with the confirmation "Deactivate <email>? They will not be able to sign in." and allow changing the role, both through `PATCH /api/v1/users/{id}`; users are never deleted. | UX-211, FR-221, E-27 |
| FEAT-074-FR-05 | Form errors (409 `EMAIL_ALREADY_EXISTS`, 409 `LAST_ADMIN`, 422 `PASSWORD_POLICY_VIOLATION`, `VALIDATION_ERROR`) shall be shown under the matching field or above the submit button by `ApiError.code`. | FE-079, UX-207 |
| FEAT-074-FR-06 | "Pipeline runs" shall list the latest 50 runs from `GET /api/v1/pipeline/runs` newest first with "Started", "Finished" (facility-local time), "Trigger", "Profile", "Status", "As of", "Counts" and the warning count. | UX-212, LOG-112, FR-225, E-31 |
| FEAT-074-FR-07 | "Run pipeline now" with a profile select whose only option is `meta.pipeline_profile` (the environment's profile, DB-024, API-066; D-96) shall call `POST /api/v1/pipeline/run` and refresh the started run every 5 s via `GET /api/v1/pipeline/runs/{id}` until `succeeded` or `failed`; 409 `PIPELINE_RUN_IN_PROGRESS` and 422 `PROFILE_NOT_ALLOWED` are shown as messages. | UX-212, E-20, E-21, D-96 |
| FEAT-074-FR-08 | A banner shall show while the most recent run of any trigger is `failed`, and the banner "Nightly run missing for <date>" whenever no succeeded nightly run started within the previous 26 hours, both computed at read time from the runs list. | LOG-112, LOG-111 |
| FEAT-074-FR-09 | "Upload data" shall provide a `.csv` file input labelled "CSV file (pipeline input format v0.1)" and "Upload" calling `POST /api/v1/ingest` (multipart field `file`, 120 s timeout), then poll `GET /api/v1/ingest/batches/{id}` and show "Accepted <a> · Rejected <r> · Duplicates <d>" and a rejections table "Row", "Errors". | UX-213, FR-222, FE-072, E-06, E-07 |
| FEAT-074-FR-10 | A whole-file rejection (e.g. legacy SRC-06, 422 `CSV_HEADER_MISMATCH`) shall show "The file was not accepted: <detail>. Nothing was stored." and list the `errors[]` messages. | UX-217 |
| FEAT-074-FR-11 | The Upload tab shall state "Only synthetic or test data may be uploaded to this environment." in every interim-stack environment. | UX-214 |
| FEAT-074-FR-12 | The page shall not offer creation or editing of residents, devices, device assignments or API keys. | UX-218 |
| FEAT-074-FR-13 | The end of the page shall show "API status: ok · version <version>" (200), "API status: degraded (database unavailable) · version <version>" (503 degraded), or "API status: unavailable" (unreachable) from `GET /api/v1/health`. | UX-216, E-01 |

## Inputs

- `GET/POST/PATCH /api/v1/users`, `GET /api/v1/pipeline/runs`, `POST /api/v1/pipeline/run`, `GET /api/v1/pipeline/runs/{id}`, `POST /api/v1/ingest`, `GET /api/v1/ingest/batches/{id}`, `GET /api/v1/health`.
- Admin input (user fields, CSV file, profile choice); role from `useAuth()`.

## Outputs

- Rendered admin tabs; user create/update requests; pipeline run request; CSV upload; banners and status line.

## Data Flow

Role check → tab from `?tab=` → Users: `listUsers` (`["admin", "users"]`) → create/update → invalidate. Runs: `listPipelineRuns` (`["admin", "runs"]`) → banners computed → "Run pipeline now" → `triggerPipelineRun` → poll `getPipelineRun(id)` (`["admin", "run", id]`) every 5 s. Upload: `uploadIngestCsv(file)` → `getIngestBatch(id)` (`["admin", "batch", id]`) → result and rejections. `getHealth()` → status line.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-064, FEAT-037, FEAT-024, FEAT-026

- FEAT-064 (header, access denied), FEAT-037 (users API), FEAT-024 (pipeline run endpoints), FEAT-026 (batch and CSV ingest endpoints).

Features that build directly on this one (BACKLOG.md §4): FEAT-075.

## Database Impact

None directly; the backend writes `users`, `ingest_batches`, `raw_sessions`, `ingest_rejections`, `pipeline_runs` and audit rows (`user.created`, `user.updated`, `ingest.batch.received`, `pipeline.run.started`).

## API Impact

Endpoints consumed: E-25, E-26, E-27, E-06, E-07, E-20, E-21, E-31, E-01 (and E-13 for the nav badge, E-32 for the chrome `meta`, both through FEAT-064). None exposed.

## Frontend Impact

- Page: `app/(protected)/admin/page.tsx`.
- Components: `AdminPanel` (tabs, users table and form, runs table, upload form, banners, status line), confirmation dialog, `SectionState`; v0.2 tokens and button classes (FEAT-062).

## Analytics Impact

None.

## Security Requirements

- Admin only (FE-034, UX-215); the backend returns 403 for other roles.
- Temporary passwords are sent once in the request body and never displayed or stored client-side (FE-051 spirit, SEC rules of FEAT-016).
- Only synthetic or test data on the interim stack (UX-214, AGT-014).

## Error Handling

- Field and form errors by `ApiError.code` (FE-079); 409/422 run errors as messages; upload timeouts after 120 s show a network error with reference (FE-072, FE-074).
- Whole-file rejection text (UX-217); per-row rejections listed (UX-213).
- Health unreachable → "API status: unavailable".

## Logging Requirements

None in the frontend; backend audit rows as listed under Database Impact.

## Testing Requirements

- Component tests for `AdminPanel` tabs (arrow keys, `?tab=`), users form error mapping, deactivate confirmation, runs table and banners (failed latest run; no nightly success within 26 h), upload result and whole-file rejection, status line variants.
- Page test (`frontend/tests/pages/admin.test.tsx`): loading, populated, empty, error, 401 → login, non-admin access denied with no admin request (TST-094).
- E2E: E2E-14 (clinician denied, FEAT-064); axe on `/admin` (TST-110).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-074-AC-01 | As admin, `/admin?tab=runs` lists at most 50 runs newest first with trigger, profile, status, local start/finish times, as-of, counts and warning count. Verified by: Page test (`frontend/tests/pages/admin.test.tsx`; TST-094). | LOG-112; FR-225; UX-212 |
| FEAT-074-AC-02 | With the latest run `failed` a failure banner shows; with no succeeded nightly run in the last 26 hours the banner "Nightly run missing for <date>" shows. Verified by: Test (Component tests for `AdminPanel` tabs (arrow keys, `?tab=`), users form error mapping, deactivate confirmation, runs table and banners (failed latest run). | LOG-112; LOG-111; AC-LOG-07 |
| FEAT-074-AC-03 | Uploading SRC-05 shows "Accepted 283 · Rejected 0 · Duplicates 2". | UX-213; FR-222; TST-046 |
| FEAT-074-AC-04 | Uploading the legacy SRC-06 file shows "The file was not accepted: <detail>. Nothing was stored." with the error messages. | UX-217; TST-047 |
| FEAT-074-AC-05 | Adding a user with an existing e-mail shows the 409 error under the Email field; deactivating a user asks "Deactivate <email>? They will not be able to sign in." before sending `PATCH`. Verified by: Page test (`frontend/tests/pages/admin.test.tsx`; TST-094). | UX-211; FE-079; FR-221 |
| FEAT-074-AC-06 | The Upload tab shows "Only synthetic or test data may be uploaded to this environment." and no control to create residents, devices, assignments or API keys exists on the page. Verified by: Page test (`frontend/tests/pages/admin.test.tsx`; TST-094). | UX-214; UX-218 |
| FEAT-074-AC-07 | With `GET /health` returning 503 degraded, the status line at the end of the page reads "API status: degraded (database unavailable) · version <version>". Verified by: Page test (`frontend/tests/pages/admin.test.tsx`; TST-094). | UX-216 |
| FEAT-074-AC-08 | As admin, `/admin` shows the app bar with "Admin" as the current link, the data bar and the `<h1>` "Admin" in the v0.2 style; as clinician it shows "You do not have access to this page." with "← Resident list". Verified by: Page test (`frontend/tests/pages/admin.test.tsx`; TST-094). | UX-210; UX-215; D-111 |

## Definition of Done

- All FEAT-074 acceptance criteria pass; component and page tests green; axe clean on `/admin`.
- Batch report lists IDs and the gap below (AGT-022).

## Implementation Notes

- LOG-111 places the "Nightly run missing" banner on `/admin` "computed at read time" and no API field carries it; compute it client-side from `GET /pipeline/runs?trigger=nightly&status=succeeded` (newest `started_at` vs now − 26 h). For the banner text "Nightly run missing for <date>" use the most recent facility-local date whose 02:00 hour has passed (the LOG-111 job rule). TRD 11 UX-219 now defines this banner and date rule (TRD 24 D-96).
- The profile options for "Run pipeline now" are "those allowed by the backend for the environment" (UX-212); TRD 11 UX-212 now fixes `meta.pipeline_profile` as the only option (PIPELINE_PROFILE, DB-024, API-066; TRD 24 D-96).
- Poll with TanStack Query `refetchInterval: 5000` while the run is `running`; stop on a terminal status.
