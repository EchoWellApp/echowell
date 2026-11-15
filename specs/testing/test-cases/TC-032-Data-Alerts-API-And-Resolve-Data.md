# Data alerts API and resolve-data-alert CLI

## Feature Description

`GET /api/v1/data-alerts` (TRD 19 E-30) serves the Study team page's "Data problems to follow up" list: data-quality flags (`baseline_stalled`, `possible_other_speaker`, `high_set_aside`, `device_silent`, `review_flagged_data_problem`) filtered by `status` (default `open`) and `kind`, ordered by kind in enum order then natural resident or device code. The API only reads; data alerts are never health alarms, never appear in `GET /alerts` or the nav badge and never touch the tally. The only way to close a review-flagged data problem is the operator command `python -m backend.cli resolve-data-alert --id <uuid> --reason "<text>"`, which is audited (`data_alert.resolved`) and refuses (exit 2) anything else. Source: FEAT-032; TRD 05 API-133; TRD 09 CUS-040, CUS-045, §4.9; TRD 15 §4.8; TRD 12 SEC-103; TRD 24 D-114.

## Preconditions

1. Local Docker Compose stack running; environment file from `.env.development.example`.
2. **DS-07 state:** `docker compose exec backend python -m backend.cli seed test_v0_1` (four open rule-based data alerts).
3. `API=http://localhost:8000/api/v1`; tokens `ADMIN`, `CLIN`, `RES` from `POST $API/auth/login` with the `SEED_*` passwords; `KEY` = the ingest API key from the environment file.
4. `R10_ALERT` = `id` from `GET $API/alerts?resident_code=R10`.
5. `psql` read access; local development stack for the `pytest` cases.
6. Cases that write end with `docker compose exec backend python -m backend.cli seed test_v0_1 --reset`.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-032-01 | Unknown `kind` returns 422; default lists only `open` rows | High | Negative |
| TC-032-02 | Order by kind enum then code: R08 baseline_stalled, R03 high_set_aside, D02 device_silent | High | Positive |
| TC-032-03 | DS-07 open list: exact four rows with titles and details | High | Positive |
| TC-032-04 | CLI resolves an open `review_flagged_data_problem` and writes one audit row | High | Positive |
| TC-032-05 | CLI refuses a `device_silent` id, a random uuid and an already resolved row (exit 2, no change) | High | Negative |
| TC-032-06 | Full pipeline run leaves the `review_flagged_data_problem` row open and unchanged | High | Analytics |
| TC-032-07 | Role access: every user role 200; API key 401 | High | Security |
| TC-032-08 | `status=resolved` and `kind` filters; invalid `status` 422 | Medium | API |
| TC-032-09 | Data alerts never appear in `GET /alerts` or alarm counts | Medium | Positive |
| TC-032-10 | No API route resolves or edits a data alert | Medium | Security |
| TC-032-11 | CLI argument refusals: malformed uuid, empty reason | Low | Negative |

### TC-032-01 Unknown `kind` returns 422; default lists only `open` rows

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s -i "$API/data-alerts?kind=unknown" -H "Authorization: Bearer $RES"` | HTTP 422; `type` "urn:echowell:error:INVALID_QUERY_PARAMETER" |
| 2 | `GET $API/data-alerts` | HTTP 200; every item has `status` "open" |
| 3 | After TC-032-04 (one resolved row exists): `GET $API/data-alerts` | The resolved row is absent |

### TC-032-02 Order by kind enum then code: R08 baseline_stalled, R03 high_set_aside, D02 device_silent

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/data-alerts` (DS-07) and list `kind` / code per item | Order: `baseline_stalled` R08, `possible_other_speaker` R05, `high_set_aside` R03, `device_silent` D02 (enum order, never alphabetical) |
| 2 | `GET $API/data-alerts?kind=baseline_stalled`, then `?kind=high_set_aside`, then `?kind=device_silent` | One item each: R08, R03, D02 |
| 3 | Fixture: `pytest tests/integration/api/test_alerts.py::test_data_alert_list -q` | Passes (fixture with device_silent D02, baseline_stalled R08, high_set_aside R03 returns R08, R03, D02; natural code order R2 before R10 within a kind) |

### TC-032-03 DS-07 open list: exact four rows with titles and details

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/data-alerts` | `total` 4 |
| 2 | Item 1 | `kind` "baseline_stalled"; `resident_code` "R08"; `device_code` null; `title` "R08 · baseline stuck at 13 of 16"; `detail` "baseline stuck at 13 of 16. 12 missed and 5 set aside in 30 days." |
| 3 | Item 2 | `kind` "possible_other_speaker"; "R05"; `title` "R05 · possible other speaker"; `detail` "2 check-ins held back as possible other voice (Oct 8, Oct 22)." |
| 4 | Item 3 | `kind` "high_set_aside"; "R03"; `title` "R03 · many check-ins set aside"; `detail` "7 of 29 received check-ins set aside (noise, quality flag, too short)." |
| 5 | Item 4 | `kind` "device_silent"; `resident_code` null; `device_code` "D02"; `title` "D02 · device silent all day"; `detail` "silent all day Oct 12. Affected R02 and R03." |
| 6 | All items | `status` "open"; `first_detected_at` = `last_detected_at` = "2026-10-30T20:00:00Z"; `pipeline_run_id` = the seed run id; response has `meta` |

### TC-032-04 CLI resolves an open `review_flagged_data_problem` and writes one audit row

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST $API/alerts/$R10_ALERT/reviews` as clinician with `{"outcome": "data_problem"}` | HTTP 201 |
| 2 | `SELECT id FROM data_alerts WHERE kind='review_flagged_data_problem' AND status='open';` → `DA` | 1 row |
| 3 | Note `SELECT count(*) FROM audit_logs WHERE action='data_alert.resolved';` (= 0) | 0 |
| 4 | `docker compose exec backend python -m backend.cli resolve-data-alert --id $DA --reason "checked"` | Output "Data alert <DA> resolved."; exit code 0 |
| 5 | `SELECT status, resolved_at FROM data_alerts WHERE id='$DA';` | `resolved`; `resolved_at` = the resolution time (now) |
| 6 | `SELECT actor_type, entity_type, entity_id, details FROM audit_logs WHERE action='data_alert.resolved';` | Exactly 1 row: `actor_type` system; `entity_type` "data_alert"; `entity_id` = DA; `details` contains `alert_id` = DA, `kind` "review_flagged_data_problem", `reason` "checked", `operator` = the OS user that ran the command |
| 7 | `GET $API/data-alerts?status=resolved&kind=review_flagged_data_problem` | 1 item with `status` "resolved" |

### TC-032-05 CLI refuses a `device_silent` id, a random uuid and an already resolved row (exit 2, no change)

| Step | Action | Expected Result |
|---|---|---|
| 1 | Snapshot: `SELECT md5(string_agg(d::text, '\|' ORDER BY d.id)) FROM data_alerts d;` and `SELECT count(*) FROM audit_logs;` | Hash and count noted |
| 2 | `resolve-data-alert --id <id of the D02 device_silent row> --reason "checked"`; then `echo $?` | Message on stderr naming kind `device_silent` ("…only review_flagged_data_problem alerts are resolved by hand"); exit code 2 |
| 3 | `resolve-data-alert --id 00000000-0000-4000-8000-000000000000 --reason "checked"` | Message "unknown data alert …"; exit code 2 |
| 4 | Run the command of TC-032-04 step 4 again on the already resolved DA | Message "data alert <DA> is not open"; exit code 2 |
| 5 | Repeat the snapshot of step 1 | Hash and audit count unchanged |

### TC-032-06 Full pipeline run leaves the `review_flagged_data_problem` row open and unchanged

| Step | Action | Expected Result |
|---|---|---|
| 1 | From DS-07, create the data alert as in TC-032-04 steps 1–2; snapshot `SELECT id, status, detail, alert_review_id, last_detected_at, resolved_at FROM data_alerts WHERE id='$DA';` | Row noted, `status` open |
| 2 | `POST $API/pipeline/run` as admin with `{"scope": "all"}`; poll `GET $API/pipeline/runs/<id>` | `status` "succeeded" |
| 3 | Repeat the snapshot query | Identical row (still `open`, same detail, review link and timestamps) |
| 4 | `pytest tests/integration/test_resolve_data_alert.py -q` | Both tests pass (TST-189) |

### TC-032-07 Role access: every user role 200; API key 401

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/data-alerts` with each of `$ADMIN`, `$CLIN`, `$RES` | 200 each, identical bodies |
| 2 | `GET $API/data-alerts -H "X-API-Key: $KEY"` | 401 `NOT_AUTHENTICATED` |
| 3 | Validate against `DataAlertList` of `GET $API/openapi.json` | Valid; `meta`, `items`, `total`, `limit`, `offset` |

### TC-032-08 `status=resolved` and `kind` filters; invalid `status` 422

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/data-alerts?status=resolved` (DS-07) | `items` []; `total` 0 |
| 2 | `GET $API/data-alerts?status=closed` | 422 `INVALID_QUERY_PARAMETER` |
| 3 | `GET $API/data-alerts?kind=possible_other_speaker` | 1 item, R05 |
| 4 | `GET $API/data-alerts?limit=0` | 422 `INVALID_QUERY_PARAMETER` |

### TC-032-09 Data alerts never appear in `GET /alerts` or alarm counts

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/alerts?status=open` | `total` 2 (R09, R10); no item with a data-alert `kind` or `title` |
| 2 | `GET $API/residents` | `summary.changed` 2; R05 (open `possible_other_speaker`) and R02 (affected by D02 `device_silent`) remain `no_alarm` |

### TC-032-10 No API route resolves or edits a data alert

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s $API/openapi.json \| jq '.paths \| to_entries[] \| select(.key \| contains("data-alerts")) \| {path: .key, methods: (.value \| keys)}'` | Only `/api/v1/data-alerts` with method `get` |
| 2 | `curl -s -i -X PATCH $API/data-alerts -H "Authorization: Bearer $ADMIN"` | 405 `METHOD_NOT_ALLOWED` |

### TC-032-11 CLI argument refusals: malformed uuid, empty reason

| Step | Action | Expected Result |
|---|---|---|
| 1 | `resolve-data-alert --id not-a-uuid --reason "checked"` | Message "'not-a-uuid' is not a uuid"; exit 2 |
| 2 | `resolve-data-alert --id 00000000-0000-4000-8000-000000000000 --reason "   "` | Message "--reason must not be empty"; exit 2 |
| 3 | `python -m backend.cli --help` | `resolve-data-alert` listed; the command has no `--force` option (`resolve-data-alert --help` shows only `--id` and `--reason`) |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/data-alerts` | 200 `DataAlertList`; default `status=open`; order kind enum then natural code |
| 2 | Item fields | `id`, `kind`, `resident_code`, `device_code`, `title`, `detail`, `status`, `first_detected_at`, `last_detected_at`, `pipeline_run_id` |
| 3 | Invalid `status` / `kind` / paging | 422 `INVALID_QUERY_PARAMETER` |
| 4 | Auth | All user roles 200; API key / anonymous 401 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT kind, status FROM data_alerts ORDER BY kind;` (DS-07) | 4 open rows: baseline_stalled, possible_other_speaker, high_set_aside, device_silent |
| 2 | After CLI resolve | `status` resolved and `resolved_at` not null together (`data_alerts_resolved_ck`) |
| 3 | `audit_logs` after resolve | One `data_alert.resolved` row with `operator` |
| 4 | GET requests | No change to `data_alerts` (API only reads) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | `kind=unknown`, `status=closed`, `limit=0` | 422 `INVALID_QUERY_PARAMETER` |
| 2 | API key | 401 |
| 3 | CLI on `device_silent` id / random uuid / resolved row | Exit 2, no change |
| 4 | CLI malformed uuid / blank reason | Exit 2 |
| 5 | `docker compose stop db`, then the CLI command | Non-zero exit with the error class, no partial change; `docker compose start db` afterwards |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-032-AC-01 | `?kind=unknown` returns 422 `INVALID_QUERY_PARAMETER`; no parameters returns only `open` rows | TC-032-01 |
| FEAT-032-AC-02 | Fixture rows device_silent D02, baseline_stalled R08, high_set_aside R03 listed R08, R03, D02 | TC-032-02 |
| FEAT-032-AC-03 | DS-07 open list exactly R08, R05, R03, D02 with the given titles and v0.2 details | TC-032-03 |
| FEAT-032-AC-04 | CLI with `--reason "checked"` exits 0, sets `resolved` and `resolved_at`, one `data_alert.resolved` row with `alert_id`, `kind`, `reason` "checked", `operator` | TC-032-04 |
| FEAT-032-AC-05 | CLI with a `device_silent` id, random uuid or resolved row exits 2 and changes no row in `data_alerts` or `audit_logs` | TC-032-05 |
| FEAT-032-AC-06 | Full pipeline run after a `data_problem` review leaves the row `open` and unchanged | TC-032-06 |
| FEAT-032-AC-07 | Every user role 200; API key 401 | TC-032-07 |

## Test Data Requirements

- DS-07 (`seed test_v0_1`): open data alerts R08 baseline_stalled, R05 possible_other_speaker, R03 high_set_aside, D02 device_silent (TRD 19 E-30, TRD 11 §4.18.8).
- A `review_flagged_data_problem` row created through a `data_problem` review of the R10 alert.
- Unknown id `00000000-0000-4000-8000-000000000000`; reason text "checked" (no names).
- Integration tests `tests/integration/api/test_alerts.py::test_data_alert_list`, `tests/integration/test_resolve_data_alert.py`.
- Environment: `SEED_*` passwords, `SEED_INGEST_API_KEY` from the environment file; the CLI uses `DATABASE_URL` (app role).

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-032-FR-01 (API-133; FR-299) | FEAT-032 | TC-032-01, TC-032-07, TC-032-08 |
| FEAT-032-FR-02 (API-133, CUS-045) | FEAT-032 | TC-032-02, TC-032-03 |
| FEAT-032-FR-03 (API-133, CUS-045) | FEAT-032 | TC-032-10 |
| FEAT-032-FR-04 (CUS-045, FR-300) | FEAT-032 | TC-032-09 |
| FEAT-032-FR-05 (TRD 15 §4.8; FR-297; SEC-103) | FEAT-032 | TC-032-04 |
| FEAT-032-FR-06 (TRD 15 §4.8; TST-189) | FEAT-032 | TC-032-05, TC-032-11 |
| FEAT-032-FR-07 (FR-297, CUS-040, DB-036) | FEAT-032 | TC-032-06 |
| TST-189 | FEAT-032 | TC-032-04, TC-032-05, TC-032-06 |
| AC-API-14 (data-alert half) / TDV-068 / FR-301 | FEAT-032 | TC-032-03 |
| TST-061, TST-064 | FEAT-032 | TC-032-07 |
| LOG-113 | FEAT-032 | TC-032-09 |
