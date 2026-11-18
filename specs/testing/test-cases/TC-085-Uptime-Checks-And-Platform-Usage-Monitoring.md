# Uptime checks and platform usage monitoring

## Feature Description

FEAT-085 (Complete, BACKLOG.md §10) adds the scheduled GitHub Actions workflow `.github/workflows/uptime.yml` and the monitoring routines in `docs/deployment.md`. Every 30 minutes (never more often) and on manual dispatch, the workflow runs `curl --fail --max-time 30` against production and staging `<API base>/health` and the production frontend `/login`, retries a failing check once after 60 s, and opens (or comments on) the GitHub issue "Uptime check failing" labelled `incident` when a check fails twice in a row. The DevOps owner checks Netlify build minutes, Render month-to-date charges and Neon compute hours and storage weekly and follows the DEP-102 fallback order. Production availability during 16 Nov – 8 Dec 2026 is reported from the run history against NFR-020 (≥ 99.0 %).

The repository-side cases (inspection of the workflow and the runbook) run on the checked-out repository. The cases marked **Hosted** run against the interim deployment (Netlify, Render, Neon; TRD 24 D-180) once the repository variables `PRODUCTION_API_BASE_URL`, `STAGING_API_BASE_URL` and `PRODUCTION_FRONTEND_URL` are set; setting them changes no deployment (`docs/deployment.md`, "Deployment status").

## Preconditions

- Repository checked out at the commit under test (branch `main` or the release candidate); `grep` and `gh` (GitHub CLI, authenticated with repository write access for the Hosted cases) available.
- Hosted cases: repository variables set in GitHub → Settings → Secrets and variables → Actions → Variables: `PRODUCTION_API_BASE_URL` = `<PRODUCTION_API_BASE_URL>`, `STAGING_API_BASE_URL` = `<STAGING_API_BASE_URL>` (both include `/api/v1`), `PRODUCTION_FRONTEND_URL` = `<PRODUCTION_FRONTEND_URL>`. The real values are held by the team and are never written into a test record.
- Hosted cases: the tester can run workflows (Actions → Uptime → Run workflow) and edit repository variables; the DevOps owner and the algorithm lead are reachable to confirm notifications.
- No change to the Render, Netlify or Neon services, no migration and no re-seed is needed by any case in this file (TRD 24 D-170).

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-085-01 | Schedule is `*/30 * * * *` plus `workflow_dispatch`, no shorter interval | High | Documentation |
| TC-085-02 | Runner, permissions, timeout and curl options match FEAT-085 scope | High | Documentation |
| TC-085-03 | Workflow references no secret | High | Security |
| TC-085-04 | Manual dispatch against the hosted environments: all three checks pass | High | Hosted |
| TC-085-05 | Failing URL is retried once after 60 s and opens the `incident` issue | High | Hosted |
| TC-085-06 | A second failing run comments on the open issue instead of opening a new one | Medium | Hosted |
| TC-085-07 | Unset URL variable is reported as not configured and opens no issue | Medium | Negative |
| TC-085-08 | Runbook records owner, admins, plan, limits, verification date, Render instance types and billing recipient | High | Documentation |
| TC-085-09 | At least two team members watch `incident` issues and receive the notification | High | Hosted |
| TC-085-10 | Weekly usage check of Netlify, Render and Neon is recorded in the team status | Medium | Hosted |
| TC-085-11 | DEP-102 fallback order is documented and a shorter interval is refused | Medium | Documentation |
| TC-085-12 | NFR-020 availability is computed from the run history for 16 Nov – 8 Dec 2026 | High | Hosted |
| TC-085-13 | Incident issue text contains only URLs, status codes and timestamps | Medium | Security |

### TC-085-01 Schedule is `*/30 * * * *` plus `workflow_dispatch`, no shorter interval

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -n "cron:" .github/workflows/uptime.yml` | Exactly one line is printed: `- cron: "*/30 * * * *"` |
| 2 | Run `grep -n "workflow_dispatch" .github/workflows/uptime.yml` | One line `workflow_dispatch:` under `on:` |
| 3 | Run `grep -rn "cron:" .github/workflows/` and look for any other schedule that calls the health or login URLs | Only `uptime.yml` calls the uptime URLs; no second schedule with an interval shorter than 30 minutes exists for them |
| 4 | Open Actions → Uptime in GitHub and read the run list | Scheduled runs are at least 30 minutes apart (GitHub may start them late; the interval is a minimum) |

### TC-085-02 Runner, permissions, timeout and curl options match FEAT-085 scope

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `.github/workflows/uptime.yml` and read the top-level `permissions:` block | `permissions:` contains only `contents: read` |
| 2 | Read the job `uptime` | `runs-on: ubuntu-24.04`; job `permissions:` is `contents: read` and `issues: write` |
| 3 | Read `timeout-minutes` of the job | Value is `10` (FEAT-085 scope requires ≤ 20) |
| 4 | Read the `check()` function of step "Check health and login pages (one retry after 60 s)" | It calls `curl --fail --silent --show-error --max-time 30` and writes `%{http_code} %{time_total}s` (FEAT-085-FR-02: non-200 or slower than 30 s fails) |
| 5 | Read the target list | Targets are `$PRODUCTION_API_BASE_URL/health`, `$STAGING_API_BASE_URL/health` and `$PRODUCTION_FRONTEND_URL/login`, taken from `vars.*` |
| 6 | Run `grep -n "uses:" .github/workflows/uptime.yml` | No output: the workflow uses no third-party action, so the CIC-025 pinning rule has nothing to pin |

### TC-085-03 Workflow references no secret

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -n "secrets\." .github/workflows/uptime.yml; echo "exit=$?"` | No matching line; `exit=1` |
| 2 | Run `grep -n "GH_TOKEN" .github/workflows/uptime.yml` | The only token is `GH_TOKEN: ${{ github.token }}` (the run's own token), used only in step "Open or update the incident issue" |

### TC-085-04 Manual dispatch against the hosted environments: all three checks pass

| Step | Action | Expected Result |
|---|---|---|
| 1 | Confirm the three repository variables are set (Preconditions) | `PRODUCTION_API_BASE_URL`, `STAGING_API_BASE_URL`, `PRODUCTION_FRONTEND_URL` are listed with non-empty values |
| 2 | Actions → Uptime → Run workflow on `main` (or `gh workflow run uptime.yml --ref main`) | A run starts with event `workflow_dispatch` |
| 3 | Open the log of step "Check health and login pages (one retry after 60 s)" | Three lines of the form `<UTC timestamp> OK   <url> 200 <seconds>s`, one each for `<PRODUCTION_API_BASE_URL>/health`, `<STAGING_API_BASE_URL>/health` and `<PRODUCTION_FRONTEND_URL>/login`; no `FAIL` line |
| 4 | Check the step "Open or update the incident issue" | Step is skipped |
| 5 | Check the run conclusion | `success`; total run time under 10 minutes |
| 6 | Run `gh issue list --label incident --state open` | No new issue titled "Uptime check failing" was opened by this run |

### TC-085-05 Failing URL is retried once after 60 s and opens the `incident` issue

| Step | Action | Expected Result |
|---|---|---|
| 1 | Note the current value of `STAGING_API_BASE_URL` (do not copy it into the test record). Set the variable temporarily to `<STAGING_API_BASE_URL>/does-not-exist` | Variable saved; no deployment changes |
| 2 | Run `gh issue list --label incident --search "Uptime check failing in:title" --state open` | No open issue with that title (close an existing one first, or run TC-085-06 instead) |
| 3 | Dispatch Actions → Uptime on `main` | Run starts |
| 4 | Read the check step log for the staging target | A line `<timestamp> FAIL <STAGING_API_BASE_URL>/does-not-exist/health 404 …; retrying in 60 s`, then about 60 s later an error annotation `<timestamp> <url> failed twice: …` containing `404` |
| 5 | Read the log lines of the production targets | Both production checks show `OK … 200`; they are not affected |
| 6 | Read the step "Open or update the incident issue" | Step ran and printed the URL of a created issue |
| 7 | Open the issue | Title is exactly `Uptime check failing`; label `incident`; body begins "Checks failed twice in a row (uptime.yml, one retry after 60 s):" and lists the failing URL with its timestamp and the run link |
| 8 | Check the run conclusion | `failure` |
| 9 | Restore `STAGING_API_BASE_URL` to its original value; dispatch Uptime again | New run is `success` with three `OK` lines |
| 10 | Close the issue with a comment "negative test FEAT-085-AC-02, variable restored" | Issue state `closed`; record the run and issue links in `DEPLOYMENT_CHECKLIST.md` K.01 |

### TC-085-06 A second failing run comments on the open issue instead of opening a new one

| Step | Action | Expected Result |
|---|---|---|
| 1 | Repeat TC-085-05 steps 1, 3–6 but leave the issue open | One open issue "Uptime check failing" labelled `incident` |
| 2 | Dispatch Uptime a second time with the variable still pointing to `/does-not-exist` | Run fails again after one retry |
| 3 | Run `gh issue list --label incident --search "Uptime check failing in:title" --state open --json number` | Exactly one issue number is returned |
| 4 | Open that issue | It has a new comment with the second run's failing URL, timestamp and run link; no second issue exists |
| 5 | Restore the variable and close the issue | Next dispatch is `success` |

### TC-085-07 Unset URL variable is reported as not configured and opens no issue

| Step | Action | Expected Result |
|---|---|---|
| 1 | In a fork or before the variables are set, ensure `PRODUCTION_FRONTEND_URL` has no value | Variable absent or empty |
| 2 | Dispatch Uptime | Run starts |
| 3 | Read the check step log | Notice annotation `production frontend: URL variable not configured, skipped`; no `FAIL` line for that target |
| 4 | Check the issue step and the run conclusion | Issue step skipped; conclusion `success`; no `incident` issue opened |

Note: skipping an unset variable (`.github/workflows/uptime.yml:46-49`) is not described by TRD 16 CIC-060; it is recorded in `docs/deployment.md` ("Deployment status") and in the workflow header. Runs where a variable was not configured are excluded from the NFR-020 figure (TC-085-12).

### TC-085-08 Runbook records owner, admins, plan, limits, verification date, Render instance types and billing recipient

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `docs/deployment.md` section "Service accounts" | One row each for Netlify, Render and Neon with columns Owner account, Administrators (≥ 2, MFA), Plan, Region, Limits to verify, Verified on |
| 2 | Read the "Verified on" column and the limit values for Netlify, Render and Neon | Each row shows a date and the verified plan limits (not a placeholder); no password, token or connection string |
| 3 | Read the paragraph under the table | States that Render runs only the two Starter web services and the two cron jobs and that Render billing e-mails go to the project mailbox |
| 4 | Open section "Usage monitoring" | Weekly check of Netlify build minutes, Render month-to-date charges and Neon compute hours and storage, recorded in the weekly team status |
| 5 | Read the fallback paragraph of "Usage monitoring" | Order: first relax the uptime interval (never shorter than 30 minutes), second suspend staging compute, only then any production setting |

Note: on 15 Nov 2026 the "Verified on" cells read "recorded in Phase 10" (`docs/deployment.md:67-71`); step 2 passes only after the team fills them in.

### TC-085-09 At least two team members watch `incident` issues and receive the notification

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `docs/deployment.md` section "Monitoring and alerts", paragraph "Incident watchers" | The DevOps owner and the algorithm lead are named as watchers of issues labelled `incident` (roles only, no personal names required) |
| 2 | Ask each watcher to show GitHub → repository → Watch | Setting is "Custom" with "Issues" ticked (or "All activity") for both |
| 3 | During TC-085-05 step 6, ask both watchers whether they received the GitHub notification for the new issue | Both confirm an e-mail or GitHub notification titled "Uptime check failing" within 15 minutes |
| 4 | Record the confirmation in `DEPLOYMENT_CHECKLIST.md` K.04 | Row K.04 evidence filled with date and the two roles |

### TC-085-10 Weekly usage check of Netlify, Render and Neon is recorded in the team status

| Step | Action | Expected Result |
|---|---|---|
| 1 | As the DevOps owner, open Netlify → Team → Usage | Build minutes used this month for both sites are readable |
| 2 | Open Render → Workspace → Billing | Month-to-date charges are readable; only two Starter web services and two cron jobs are billed |
| 3 | Open Neon → Project `echowell` → Usage | Compute hours used this month and storage per branch are readable |
| 4 | Open the weekly team status of the current week | One entry dated this week lists the three figures (Netlify minutes, Render USD to date, Neon compute hours and storage) |
| 5 | Compare the Neon compute figure with the plan limit | If the projection exceeds the limit before month end, the status names the DEP-102 action taken (TC-085-11); otherwise "no action" |

### TC-085-11 DEP-102 fallback order is documented and a shorter interval is refused

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read `docs/deployment.md` "Usage monitoring" fallback paragraph | Lists, in this order: relax the uptime interval, suspend staging compute (Neon `staging` branch compute and, if needed, the Render staging services), then any production setting |
| 2 | Review a proposed change to `uptime.yml` that sets `cron: "*/15 * * * *"` (review only, not merged) | Reviewer rejects it: CIC-061 / FEAT-085-FR-04 forbid an interval shorter than 30 minutes |
| 3 | Review a proposed change that sets `cron: "0 * * * *"` as the relaxation step | Accepted as the first fallback action (interval longer than 30 minutes) |

### TC-085-12 NFR-020 availability is computed from the run history for 16 Nov – 8 Dec 2026

| Step | Action | Expected Result |
|---|---|---|
| 1 | After 8 Dec 2026, run `gh run list --workflow uptime.yml --created 2026-11-16..2026-12-08 --limit 2000 --json databaseId,conclusion,createdAt` | List of runs in the window |
| 2 | For each run, read the check log; count runs with a production API line (`OK` or `failed twice`) and runs whose production API check failed twice | Two counts: N (checks run) and F (failed twice); runs with "URL variable not configured" for the production API are counted separately and excluded |
| 3 | Compute availability = 1 − F ÷ N | Value ≥ 0.990 (99.0 %) |
| 4 | Record N, F, the excluded count, the figure and the run-history link in `MVP_READINESS_CHECKLIST.md` D.07 and `DEPLOYMENT_CHECKLIST.md` K.05 | Both rows filled; figure below 99.0 % is recorded as FAIL with the incident issue links |

### TC-085-13 Incident issue text contains only URLs, status codes and timestamps

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open the issue created in TC-085-05 | Body contains only the header sentence, failing URL(s) with UTC timestamps and curl status text, and the run link |
| 2 | Search the body for resident codes (`R0`, `T0`), feature names, e-mail addresses, tokens or connection strings | None present (TPS-041) |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | Local: `curl -fsS http://localhost:8000/api/v1/health` (Compose demo stack) | HTTP 200, JSON with `"status":"ok"`, `"database":"ok"` and `"version"` (local value `unknown` unless GIT_SHA is set) |
| 2 | Hosted: `curl --fail --max-time 30 -sS -o /dev/null -w '%{http_code} %{time_total}s\n' "<PRODUCTION_API_BASE_URL>/health"` | `200` and a time below 30 s |
| 3 | Hosted: same for `<STAGING_API_BASE_URL>/health` | `200` and a time below 30 s |
| 4 | Hosted: same for `<PRODUCTION_FRONTEND_URL>/login` | `200` and a time below 30 s |
| 5 | Hosted negative: same for `<STAGING_API_BASE_URL>/does-not-exist/health` | Non-zero curl exit (22) with `404`; this is the condition that triggers the retry |

## Database Validation

Not applicable: FEAT-085 adds no table, row or query (Database Impact "None"); the health endpoint's internal `SELECT 1` is covered by FEAT-081.

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Point `STAGING_API_BASE_URL` at a non-existent path and dispatch (TC-085-05) | One retry after 60 s, then issue "Uptime check failing" with label `incident`; run `failure` |
| 2 | Dispatch again while the issue is open (TC-085-06) | Comment on the existing issue; no duplicate issue |
| 3 | Leave a URL variable unset (TC-085-07) | Notice "URL variable not configured, skipped"; no issue |
| 4 | Propose a 15-minute schedule (TC-085-11) | Rejected under CIC-061 |
| 5 | Search `uptime.yml` for `secrets.` (TC-085-03) | No match |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-085-AC-01 | `uptime.yml` has `cron "*/30 * * * *"` and `workflow_dispatch` and no shorter schedule | TC-085-01, TC-085-11 |
| FEAT-085-AC-02 | A dispatched run against a failing URL retries once after 60 s and opens or comments on "Uptime check failing" with label `incident` | TC-085-05, TC-085-06 |
| FEAT-085-AC-03 | `grep -n "secrets\." .github/workflows/uptime.yml` returns nothing | TC-085-03 |
| FEAT-085-AC-04 | `docs/deployment.md` records owner, admins, plan, verified limits and date for Netlify, Render and Neon, Render instance types and billing recipient, the weekly usage check and the DEP-102 order | TC-085-08, TC-085-10, TC-085-11 |
| FEAT-085-AC-05 | At least two team members are listed as watchers of `incident` issues and are notified | TC-085-09 |

## Test Data Requirements

- No resident data. Only public HTTPS endpoints are called.
- Repository variables `PRODUCTION_API_BASE_URL`, `STAGING_API_BASE_URL`, `PRODUCTION_FRONTEND_URL` (values held by the team; placeholders in this file).
- A temporary invalid value `<STAGING_API_BASE_URL>/does-not-exist` for the negative cases, restored afterwards.
- Access to the Netlify, Render and Neon usage pages (DevOps owner) and to the weekly team status.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| CIC-060, LOG-103 | FEAT-085 | TC-085-04, TC-085-05, TC-085-06 |
| CIC-061 | FEAT-085 | TC-085-01, TC-085-11 |
| CIC-024, CIC-025, CIC-090 | FEAT-085 | TC-085-02, TC-085-03 |
| LOG-114 | FEAT-085 | TC-085-09 |
| DEP-101, TRD 17 §4.8 | FEAT-085 | TC-085-10 |
| DEP-102 | FEAT-085 | TC-085-08, TC-085-11 |
| TPS-006, TPS-007, TPS-021 | FEAT-085 | TC-085-08 |
| NFR-020 | FEAT-085 | TC-085-12 |
| TPS-041 | FEAT-085 | TC-085-13 |
| FEAT-085-FR-01..FEAT-085-FR-10 | FEAT-085 | TC-085-01..TC-085-13 |
