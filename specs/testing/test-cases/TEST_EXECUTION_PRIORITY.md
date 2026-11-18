# Test execution priority (Block 5)

Block 5 has 1,332 manual test cases and five testers, so the goal this semester is **not** full coverage. It is confidence in the clinician-facing workflows most likely to be shown in presentations and demos (algorithm lead, review of GitHub PR #50; TRD 24 D-186). Run Priority 1 first, then Priority 2, then Priority 3 as time allows.

| Priority | What | Cases |
|---|---|---|
| **1** | Happy-path and UI cases of the clinician dashboard: login and logout, app bar and navigation, resident list and filters, resident chart (Summary, Voice trends, Check-in log and Baseline, Device), alarm review, staff notes | 80 |
| **2** | Happy-path and UI cases of secondary screens: Study team page, New admissions, Admin (users, pipeline runs, CSV upload), shared UI foundations, accessibility and responsive layout, local demo fallback | 58 |
| **3** | Everything else: negative and error-path cases, API-only, database, analytics and pipeline validation, deployment and infrastructure, migration and rollback, security hardening, Not Started features | 1,194 |

**How the cases were sorted.** A test case is Priority 1 or 2 when its feature is listed below and its type (the Type column of the file's summary table) is Positive, UI or Accessibility and not Negative. Every other case is Priority 3. Within each priority, run High before Medium before Low.

**Recording results.** For each case record Pass, Fail (with the step and what was seen) or Not executed (with the reason). Defects go to the follow-up backlog of findings (D-181); Block 5 changes no application code. Hosted cases run against the deployed prototype read-only: a case that would need a deployment setting or configuration change, or that cannot be fully reversed without risk, is recorded as **Not executed** (D-182, D-183). TC-089-07 is Not executed for this reason.

## Priority 1 — execute first (80 cases)

| Feature | Area | Cases | Test case IDs |
|---|---|---|---|
| FEAT-063 | Login, session handling and route guard | 6 | TC-063-01, TC-063-02, TC-063-03, TC-063-07, TC-063-09, TC-063-11 |
| FEAT-064 | App chrome: app bar, data bar, navigation and access-denied states | 10 | TC-064-01, TC-064-02, TC-064-03, TC-064-04, TC-064-05, TC-064-06, TC-064-08, TC-064-09, TC-064-11, TC-064-15 |
| FEAT-065 | Resident list page | 11 | TC-065-01, TC-065-02, TC-065-03, TC-065-04, TC-065-05, TC-065-06, TC-065-07, TC-065-08, TC-065-10, TC-065-11, TC-065-14 |
| FEAT-066 | Resident chart frame and Summary | 14 | TC-066-01, TC-066-02, TC-066-03, TC-066-04, TC-066-05, TC-066-06, TC-066-07, TC-066-08, TC-066-09, TC-066-10, TC-066-11, TC-066-14, TC-066-15, TC-066-16 |
| FEAT-067 | Voice trends: change score chart and the 7 voice measurements | 11 | TC-067-01, TC-067-02, TC-067-03, TC-067-04, TC-067-05, TC-067-06, TC-067-07, TC-067-08, TC-067-09, TC-067-10, TC-067-12 |
| FEAT-068 | Check-in log and Baseline sections of the resident chart | 10 | TC-068-01, TC-068-02, TC-068-03, TC-068-04, TC-068-06, TC-068-07, TC-068-09, TC-068-10, TC-068-11, TC-068-12 |
| FEAT-069 | Alarm review panel in the resident chart | 7 | TC-069-01, TC-069-04, TC-069-06, TC-069-07, TC-069-08, TC-069-13, TC-069-14 |
| FEAT-070 | Device section of the resident chart | 6 | TC-070-01, TC-070-02, TC-070-03, TC-070-04, TC-070-05, TC-070-07 |
| FEAT-071 | Staff notes in the resident chart | 5 | TC-071-01, TC-071-02, TC-071-03, TC-071-04, TC-071-10 |

## Priority 2 (58 cases)

| Feature | Area | Cases | Test case IDs |
|---|---|---|---|
| FEAT-062 | Frontend foundations | 9 | TC-062-01, TC-062-02, TC-062-05, TC-062-06, TC-062-08, TC-062-12, TC-062-14, TC-062-17, TC-062-18 |
| FEAT-072 | Study team page | 12 | TC-072-01, TC-072-02, TC-072-03, TC-072-04, TC-072-05, TC-072-06, TC-072-07, TC-072-08, TC-072-09, TC-072-10, TC-072-11, TC-072-16 |
| FEAT-073 | New admissions page | 11 | TC-073-01, TC-073-02, TC-073-03, TC-073-04, TC-073-06, TC-073-07, TC-073-08, TC-073-09, TC-073-10, TC-073-11, TC-073-12 |
| FEAT-074 | Admin page: users, pipeline runs and CSV upload | 11 | TC-074-01, TC-074-03, TC-074-04, TC-074-05, TC-074-07, TC-074-08, TC-074-10, TC-074-11, TC-074-12, TC-074-14, TC-074-15 |
| FEAT-075 | Accessibility and responsive conformance | 14 | TC-075-01, TC-075-02, TC-075-03, TC-075-04, TC-075-05, TC-075-06, TC-075-07, TC-075-08, TC-075-10, TC-075-11, TC-075-12, TC-075-13, TC-075-14, TC-075-16 |
| FEAT-090 | Demo acceptance and local fallback rehearsal | 1 | TC-090-08 |

## Priority 3 (1,194 cases)

All remaining cases in each file. By area:

| Features | Area | Cases |
|---|---|---|
| FEAT-001–012 | Design documents, repository, scaffolds, CI, database tables | 157 |
| FEAT-013–024 | Database helpers, CLI, logging, errors, authentication, roles, rate limits, ingest validation, pipeline runs | 187 |
| FEAT-025–039 | Backend API endpoints, OpenAPI contract, security suite | 193 |
| FEAT-040–061 | Analytics engine stages, pipeline runner, validation suite | 283 |
| FEAT-062–076 | Negative, security, API-only and E2E-harness cases of the frontend features (incl. FEAT-076) | 90 |
| FEAT-077–091 | Containers, CI, performance, deployment, monitoring, hosted checks, demo acceptance, final audit | 206 |
| FEAT-092–097 | Not Started features (run only once built) | 78 |

## Suggested split across five testers (Priorities 1 and 2)

| Tester | Features | Cases |
|---|---|---|
| 1 | Login (FEAT-063), app bar and navigation (FEAT-064), resident list (FEAT-065) | 27 |
| 2 | Resident chart Summary (FEAT-066), Voice trends (FEAT-067) | 25 |
| 3 | Check-in log and Baseline (FEAT-068), alarm review (FEAT-069), Device (FEAT-070), staff notes (FEAT-071) | 28 |
| 4 | Study team (FEAT-072), New admissions (FEAT-073), Admin (FEAT-074) | 34 |
| 5 | UI foundations (FEAT-062), accessibility and responsive (FEAT-075), local demo fallback (FEAT-090) | 24 |

Testers 1–3 cover Priority 1; testers 4–5 start on Priority 2 and then help with Priority 1 re-runs. After that, each tester takes the Priority 3 cases of the same features first (their negative paths), then the other areas.
