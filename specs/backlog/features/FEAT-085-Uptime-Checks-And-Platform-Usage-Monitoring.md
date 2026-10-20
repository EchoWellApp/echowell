# FEAT-085 Uptime checks and platform usage monitoring

| Field | Value |
|---|---|
| Epic | Monitoring & Logging |
| Build phase | Phase 9 (TRD 25) |
| Priority | P1 |
| Complexity | Low |
| MVP status | Required |
| Dependencies | FEAT-081, FEAT-082 |
| Status | Not Started |

## Purpose

Detect outages of the interim deployment and keep free-tier usage under control: a scheduled GitHub Actions workflow `uptime.yml` checks staging and production `GET /api/v1/health` and the production frontend `/login` every 30 minutes (never more often), retries once after 60 s, and opens or updates an `incident` issue when a check fails twice in a row; and a documented routine in which the DevOps owner checks Netlify build minutes, Railway usage dollars (with the hard limit) and Neon compute hours and storage, relaxing the uptime interval first if Neon compute would run out.

## Business Context

- BR-17 and NFR-020: production availability ≥ 99.0 % during the demo and presentation window (16 Nov – 8 Dec 2026) is measured by this 30-minute check.
- RSK-05 (silent failures) and RSK-07 (free-tier limits, sleeping services): `incident` issues reach at least two team members (LOG-114); usage is watched so limits do not stop the demo (DEP-101, DEP-102).

## Referenced TRDs

- TRD 16 CIC-002, CIC-024, CIC-025, CIC-060, CIC-061, §4.6 `uptime.yml`, §4.9 variables (`STAGING_API_BASE_URL`, `PRODUCTION_API_BASE_URL`, `PRODUCTION_FRONTEND_URL`).
- TRD 17 LOG-011, LOG-103, LOG-114, §4.8 monitoring table, §4.9 operational alerts.
- TRD 15 DEP-100, DEP-101, DEP-102.
- TRD 22 TPS-006, TPS-007, TPS-021.
- TRD 03 NFR-020.
- TRD 24 RSK-05, RSK-07.

## Scope

- `.github/workflows/uptime.yml`: trigger `schedule` `*/30 * * * *` and `workflow_dispatch`; one job on `ubuntu-24.04` with `permissions: contents: read` plus `issues: write` for the issue step; `curl --fail --max-time 30` on `${{ vars.PRODUCTION_API_BASE_URL }}/health`, `${{ vars.STAGING_API_BASE_URL }}/health` and `${{ vars.PRODUCTION_FRONTEND_URL }}/login`; one retry after 60 s per failing check; on a second failure open or update the issue titled "Uptime check failing" with label `incident` via `gh`; `timeout-minutes` ≤ 20.
- `docs/deployment.md` section "Usage monitoring": weekly check of Netlify build minutes, Railway usage dollars (hard limit USD 20, alert at USD 10) and Neon compute hours and storage, recorded in the weekly team status; the fallback order (relax the uptime interval first, suspend staging compute second, before any production setting); per-service owner, admins, plan and verified limits.
- Repository issue label `incident` and the watch rule (DevOps owner and algorithm lead watch issues with that label).
- Uptime report procedure for NFR-020: monthly availability computed from the `uptime.yml` run history.

## Out of Scope

- Railway/Netlify/Neon account creation and limit settings (Phase 10, FEAT-088).
- Sentry (FEAT-084); pipeline failure and missing-nightly banners (FEAT-056).
- Paging, SMS or e-mail notifications beyond GitHub issue notifications (TPS-083, LOG-113).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-085-FR-01 | `uptime.yml` shall check production and staging `/api/v1/health` and production frontend `/login` every 30 minutes and on manual dispatch. | CIC-060, LOG-103 |
| FEAT-085-FR-02 | A check shall fail on a non-200 response or a response slower than 30 s (`curl --fail --max-time 30`). | LOG-103 |
| FEAT-085-FR-03 | A failing check shall be retried once after 60 s; when it fails twice in a row the workflow shall open, or update if open, the issue "Uptime check failing" labelled `incident`. | CIC-060, TRD 17 §4.9 |
| FEAT-085-FR-04 | The uptime interval shall never be shorter than 30 minutes. | CIC-061 |
| FEAT-085-FR-05 | The workflow shall use no secret, default `permissions: contents: read`, `issues: write` only for the issue step's job, and actions pinned per CIC-025. | CIC-024, CIC-025, CIC-090 |
| FEAT-085-FR-06 | Operational notifications shall reach at least the DevOps owner and the algorithm lead by watching issues labelled `incident`. | LOG-114 |
| FEAT-085-FR-07 | The DevOps owner shall check Netlify build minutes, Railway usage dollars and Neon compute hours and storage weekly and record them in the weekly team status. | DEP-101, TRD 17 §4.8 |
| FEAT-085-FR-08 | If Neon Free compute hours would be exhausted before month end, the uptime interval shall be relaxed first and staging compute suspended second, before any production setting changes. | DEP-102 |
| FEAT-085-FR-09 | The runbook shall record per service the account owner, administrators, plan and the date limits were last verified, and the verified plan limits, without credentials; Railway shall have a USD 20 hard limit with an alert at USD 10. | TPS-006, TPS-007, TPS-021 |
| FEAT-085-FR-10 | Production availability of `GET /api/v1/health` during 16 Nov – 8 Dec 2026 shall be reported from the uptime run history against the ≥ 99.0 % target. | NFR-020 |

## Inputs

- Repository variables `PRODUCTION_API_BASE_URL`, `STAGING_API_BASE_URL`, `PRODUCTION_FRONTEND_URL` (set in Phase 10).
- Backend health endpoint (FEAT-081 deployment target) and frontend `/login` (FEAT-082).

## Outputs

- `.github/workflows/uptime.yml`; label `incident`; `docs/deployment.md` "Usage monitoring" and "Uptime" sections.
- `incident` issues on outages; NFR-020 availability figure in the readiness evidence (FEAT-087).

## Data Flow

Cron every 30 min → GitHub-hosted runner → HTTPS GET to three URLs → on failure wait 60 s and retry → second failure → `gh issue create|comment` with label `incident` → watchers notified by GitHub e-mail. Weekly: DevOps owner reads Netlify, Railway and Neon usage pages → team status entry → fallback actions if limits approach.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-081, FEAT-082

- [FEAT-081](FEAT-081-Railway-Backend-And-Nightly-Cron-Services.md) Railway backend configuration (health endpoint host, usage limit).
- [FEAT-082](FEAT-082-Netlify-Frontend-Configuration-Security-Headers-And.md) Netlify frontend configuration (`/login` host, build minutes).

## Database Impact

None. Health checks run `SELECT 1` inside the backend (LOG-071) but this feature adds no table or query.

## API Impact

- Consumed: `GET /api/v1/health` on staging and production.
- Exposed: none. Health 200 responses are logged at DEBUG only, so the checks do not flood logs (LOG-011).

## Frontend Impact

None in code; `/login` is fetched as a liveness probe.

## Analytics Impact

None.

## Security Requirements

- No secrets in the workflow; only public HTTPS endpoints are called (CIC-090).
- Issue text contains URLs, status codes and timestamps only, no data (TPS-041).

## Error Handling

- Single failures are tolerated (retry); repeated failures raise one issue per outage (updated, not duplicated).
- A GitHub Actions outage delays checks; the next scheduled run resumes them. Scheduled runs on GitHub may start late; the interval is a minimum, not a guarantee.

## Logging Requirements

- Workflow logs record URL, HTTP status and duration per check.
- The weekly usage entries form the usage log in the team status; no application audit rows.

## Testing Requirements

- Manual dispatch against the deployed environments in Phase 10 (FEAT-088): all three checks pass.
- Negative test: dispatch with a temporary variable pointing to a non-existent path, observe one retry and the `incident` issue, then restore the variable and close the issue.
- Inspection: schedule expression `*/30 * * * *` (CIC-061).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-085-AC-01 | `uptime.yml` has `schedule: cron "*/30 * * * *"` and `workflow_dispatch`, and no schedule with a shorter interval. | CIC-060, CIC-061 |
| FEAT-085-AC-02 | A dispatched run against a failing URL retries once after 60 s and then opens (or comments on) an issue titled "Uptime check failing" with label `incident`. | CIC-060 |
| FEAT-085-AC-03 | `grep -n "secrets\." .github/workflows/uptime.yml` returns nothing. | CIC-090 |
| FEAT-085-AC-04 | `docs/deployment.md` records owner, admins, plan, verified limits and verification date for Netlify, Railway and Neon, the Railway USD 20 hard limit with USD 10 alert, the weekly usage check and the DEP-102 fallback order. | TPS-006, TPS-007, TPS-021, DEP-101, DEP-102 |
| FEAT-085-AC-05 | At least two team members are listed as watchers of `incident` issues in the runbook. | LOG-114 |

## Definition of Done

- All FEAT-085 acceptance criteria pass (FEAT-085-AC-02 executed once in Phase 10).
- Batch report entry (AGT-022).

## Implementation Notes

- Repository variables hold the full API base including `/api/v1` (TRD 16 §4.9 examples), so the health URL is `<base>/health`.
- Use `gh issue list --label incident --search "Uptime check failing in:title" --state open` to find an existing issue before creating one.
- The usage check is weekly (TRD 15 DEP-101, TRD 17 §4.8); BACKLOG.md was aligned to weekly in the PR #2 consistency fixes.
