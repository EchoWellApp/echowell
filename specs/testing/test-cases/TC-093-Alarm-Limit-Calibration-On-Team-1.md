# Alarm-limit calibration on Team 1's 50-resident, 120-day dataset (DS-04)

## Feature Description

Status: Not Started — these test cases are written from the feature file and run only once the feature is built (BACKLOG.md §10).

FEAT-093 calibrates the production alarm settings on Team 1's synthetic DS-04 dataset (50 residents, ≥ 120 days, about 20 % with an inserted change, answer key in a separate file). DS-04 is ingested through `POST /api/v1/ingest` into a dedicated calibration database of the local Docker Compose stack (TRD 24 D-75; never staging, never production); the grid `baseline_n` ∈ {16, 20, 30, 45, 60} × `cusum_k` ∈ {0.25, 0.5, 0.75, 1.0} × `cusum_h` ∈ {3, 4, 5, 6, 7, 8, 10} (140 combinations) is run in-process through `scripts/run_engine.py`; each combination reports the CUS-032 metrics (a)–(e); results go to `docs/reports/CALIBRATION_REPORT.md` and `docs/reports/calibration_results.json`. Under the OQ-27 interim decision the grid is reported but no combination is selected and no `set-config` is run; once OQ-13/OQ-27 are answered, chosen values are written to profile `production` only with `set-config` and applied with `rebuild --profile production --confirm REBUILD`. The `test_v0_1` profile and the R01–R10 answer key stay unchanged. Gate: OQ-13, OQ-27 and delivery of DS-04 by Team 1.

Cases that apply `set-config` / `rebuild` are rehearsed on a local database; on hosted production they are performed only by the operator after the gate opens, and the test cases then inspect the resulting audit rows (no change to the working deployment for testing, TRD 24 D-170).

## Preconditions

- DS-04 CSV file(s) in schema v0.1 and its separate answer key delivered by Team 1 (synthetic data only).
- Local Compose stack running; a dedicated calibration database on it (e.g. `echowell_calibration`, created and provisioned like `echowell_demo` in `.github/workflows/e2e.yml:80-90`), roster of the 50 DS-04 residents loaded with `import-master-data`; an admin token or `X-API-Key` for ingest on that database.
- The calibration evaluation script (outside `analytics/` and `backend/`, e.g. `scripts/calibrate_alarm_limits.py`) and `scripts/run_engine.py` at the commit under test.
- OQ-13 / OQ-27 status read from TRD 24 before the selection and application cases.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-093-01 | DS-04 answer key is a separate file under `tests/fixtures/answer_key/team1_v1/` | High | Documentation |
| TC-093-02 | DS-04 intake on the isolated calibration database: 0 rejections or every rejection explained | High | API |
| TC-093-03 | Unexplained intake rejections stop the calibration | High | Negative |
| TC-093-04 | `calibration_results.json` holds 140 combinations, each with metrics (a)–(e) | High | Analytics |
| TC-093-05 | Metric definitions verified on a hand-made result set | High | Analytics |
| TC-093-06 | Per-resident TDV-091 outputs reported under `production` and `test_v0_1` | Medium | Analytics |
| TC-093-07 | The DS-04 answer key is never read by `analytics/` or `backend/` | High | Security |
| TC-093-08 | Without the PI's target (OQ-27 open) no combination is selected and no `set-config` runs | High | Negative |
| TC-093-09 | Production change: one `config.changed` per key with the report as reason, then one `pipeline.rebuild` | High | Database |
| TC-093-10 | Before the rebuild an ingest-triggered run fails with `config_changed_requires_rebuild` | High | Negative |
| TC-093-11 | `test_v0_1` rows unchanged and R01–R10 validation passes after calibration | High | Analytics |
| TC-093-12 | `set-config` refuses an unknown key or invalid value with exit code 2 and no change | Medium | Negative |
| TC-093-13 | No CI required check depends on DS-04 results | High | Documentation |
| TC-093-14 | Study team data still shows the active settings and no detection-performance claim | Medium | UI |
| TC-093-15 | DS-04 and its outputs never reach staging or production | High | Security |

### TC-093-01 DS-04 answer key is a separate file under `tests/fixtures/answer_key/team1_v1/`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `ls tests/fixtures/answer_key/team1_v1/` | The DS-04 answer key file(s) are present |
| 2 | Inspect the DS-04 input CSV header | No answer-key column (`expected_status`, `expected_reason`, `expected_morning`, `expected_epoch`, `in_baseline`, `error_mode_tested`, `test_case`, `arrival_order`, or the DS-04 change-onset columns) |
| 3 | `git ls-files tests/fixtures/pipeline_input \| grep -i team1` | The answer key is not in any pipeline input folder |

### TC-093-02 DS-04 intake on the isolated calibration database: 0 rejections or every rejection explained

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -sS -X POST http://localhost:8000/api/v1/ingest -H "X-API-Key: <calibration key>" -F "file=@<DS-04 CSV>;type=text/csv"` against the backend bound to the calibration database | 2xx with a batch ID and counts `record_count`, `accepted_count`, `rejected_count`, `duplicate_count` |
| 2 | `GET /api/v1/ingest/batches/{id}` | Same counts; each rejection listed with row number and reason code |
| 3 | Open the intake report | Lists every rejection with its reason; `rejected_count` = 0, or each rejection carries a written Team 1 explanation |
| 4 | Check the evaluation run log | No grid run started before step 3 was satisfied |

### TC-093-03 Unexplained intake rejections stop the calibration

| Step | Action | Expected Result |
|---|---|---|
| 1 | In a copy of DS-04, change one row's `schema_version` to `9.9` and ingest it into a fresh calibration database | `rejected_count` = 1 with reason `unsupported_schema_version` |
| 2 | Start the calibration script without a Team 1 explanation | Script refuses to evaluate (or the operator stops) and the intake report states "rejections not explained"; no `calibration_results.json` is written |

### TC-093-04 `calibration_results.json` holds 140 combinations, each with metrics (a)–(e)

| Step | Action | Expected Result |
|---|---|---|
| 1 | Count the combination entries in `docs/reports/calibration_results.json` (e.g. `jq '<combinations array> \| length'`) | `140` |
| 2 | List the distinct `baseline_n`, `cusum_k`, `cusum_h` values | {16, 20, 30, 45, 60}, {0.25, 0.5, 0.75, 1.0}, {3, 4, 5, 6, 7, 8, 10}; every pair appears once per `baseline_n` |
| 3 | For each entry, check metrics | (a) false-alarm proportion, (b) false alerts per 100 scored sessions, (c) detection proportion within 30 days, (d) detection delay in scored sessions and days (median and IQR), (e) share of residents whose baseline never forms — all present; an entry that raised `ConfigError` is marked invalid with the message, not omitted |
| 4 | Check run settings | All other parameters equal the production profile values; dataset version and `code_version` recorded |

### TC-093-05 Metric definitions verified on a hand-made result set

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run the unit tests of the metric functions (`pytest <calibration metric tests> -q`) | All pass |
| 2 | Hand-made case: a change resident whose first alert is 2 days before the true onset | Counted as a false alarm (alert before onset), not as a detection |
| 3 | Hand-made case: first alert exactly 30 days after onset | Counted as detected (window inclusive); 31 days → not detected |
| 4 | Hand-made case: a no-change resident with two alerts | Counted once in (a); twice in (b) |

### TC-093-06 Per-resident TDV-091 outputs reported under `production` and `test_v0_1`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open the per-resident section of `CALIBRATION_REPORT.md` | Two blocks, profile `production` and profile `test_v0_1` |
| 2 | Read the changed residents | Alarm yes/no and delay in days from true onset to first alarm |
| 3 | Read the unchanged residents and moved residents | False alarm yes/no; epoch count for each moved resident |

### TC-093-07 The DS-04 answer key is never read by `analytics/` or `backend/`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -rn "team1_v1" analytics backend; echo "exit=$?"` | No output; `exit=1` |
| 2 | `grep -rn "team1_v1" scripts tests` | Only the calibration evaluation code (outside `analytics/` and `backend/`) |
| 3 | CI job `backend-lint` (import-linter) on the commit | `success` |

### TC-093-08 Without the PI's target (OQ-27 open) no combination is selected and no `set-config` runs

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read OQ-27 in TRD 24 | Status recorded (Open or answered with a target) |
| 2 | If Open: read `CALIBRATION_REPORT.md` "Chosen values" | States that no combination is selected (OQ-27 open); production values k = 0.5, h = 5.0, `baseline_n` = 30 unchanged |
| 3 | If Open: `SELECT count(*) FROM audit_logs WHERE action = 'config.changed' AND occurred_at > '<calibration start>';` on production (read-only) | `0` |
| 4 | If answered and no combination meets the target | Report states "no admissible combination"; production values unchanged |
| 5 | If answered and the selected `baseline_n` ≠ 30 | Report shows a new owner decision (D entry) before any change of `baseline_n` |

### TC-093-09 Production change: one `config.changed` per key with the report as reason, then one `pipeline.rebuild`

Rehearse on a local database with profile `production` first; on hosted production inspect the operator's change after the gate opens.

| Step | Action | Expected Result |
|---|---|---|
| 1 | Local: `docker compose exec backend python -m backend.cli set-config --profile production --key cusum_h --value '<chosen JSON>' --reason "CALIBRATION_REPORT.md <version>"` (one call per changed key) | Exit 0 per call |
| 2 | `docker compose exec backend python -m backend.cli rebuild --profile production --confirm REBUILD` | Exit 0 |
| 3 | `SELECT action, occurred_at FROM audit_logs WHERE action IN ('config.changed','pipeline.rebuild') ORDER BY occurred_at;` | One `config.changed` row per changed key (old value, new value, reason naming the calibration report), followed by exactly one `pipeline.rebuild` row (old and new config hash) |
| 4 | `SELECT key, value, updated_at FROM config_parameters WHERE profile = 'production' AND key IN ('cusum_k','cusum_h','baseline_n');` | New values for changed keys only |
| 5 | Hosted production (read-only, after the operator applied the change): step 3 and 4 queries | Same pattern |

### TC-093-10 Before the rebuild an ingest-triggered run fails with `config_changed_requires_rebuild`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Local (profile `production` data present): run `set-config` for one key, do not run `rebuild` | Exit 0 |
| 2 | POST one valid record with `POST /api/v1/sessions` | Record stored (201); the triggered run fails |
| 3 | `SELECT status, error_message, warnings FROM pipeline_runs ORDER BY started_at DESC LIMIT 1;` | `failed`; error "configuration changed; run the rebuild command"; warnings contain `config_changed_requires_rebuild` |
| 4 | Run `rebuild --profile production --confirm REBUILD`, then post another record | Run `succeeded` |

### TC-093-11 `test_v0_1` rows unchanged and R01–R10 validation passes after calibration

| Step | Action | Expected Result |
|---|---|---|
| 1 | Before calibration: `SELECT md5(string_agg(key \|\| '=' \|\| value::text, ',' ORDER BY key)) FROM config_parameters WHERE profile = 'test_v0_1';` | Hash H recorded |
| 2 | After calibration (and after any production change): same query | Same H |
| 3 | `pytest tests/validation -q` | All pass, 0 failed |

### TC-093-12 `set-config` refuses an unknown key or invalid value with exit code 2 and no change

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker compose exec backend python -m backend.cli set-config --profile production --key cusum_q --value '1' --reason "test"; echo "exit=$?"` | `exit=2`; message names the unknown key |
| 2 | Same with `--key cusum_h --value '"abc"'` | `exit=2`; validation message; no change |
| 3 | `SELECT count(*) FROM audit_logs WHERE action = 'config.changed' AND occurred_at > now() - interval '5 minutes';` | `0` |

### TC-093-13 No CI required check depends on DS-04 results

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -rniE "calibrat\|team1_v1\|DS-04" .github/workflows/; echo "exit=$?"` | No required job runs the calibration (no match, or only an informational, non-required job) |
| 2 | Compare the required checks of `main` with CIC-070 | Exactly `repo-hygiene`, `backend-lint`, `backend-test`, `openapi-contract`, `frontend`, `security-audit`, `docker-build`, `playwright`; none reads DS-04 |

### TC-093-14 Study team data still shows the active settings and no detection-performance claim

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/analytics` (researcher token) | `meta` contains `cusum_h`, `baseline_n` and `pipeline_profile` equal to the active profile values |
| 2 | Open `/study` | The active settings are shown; no text presents alarm rates as validated detection performance |
| 3 | Search `CALIBRATION_REPORT.md` and `docs/` for "validated detection" claims about v0.1 | None; results labelled informational |

Note: FEAT-093-FR-13 is aligned to the TRD (TRD 24 D-184): `cusum_k` is not a response field (TRD 09 CUS-029; `docs/api_reference/openapi.json` `Meta` has no `cusum_k`) and is reported in the calibration report.

### TC-093-15 DS-04 and its outputs never reach staging or production

| Step | Action | Expected Result |
|---|---|---|
| 1 | Staging and production (read-only): `SELECT count(*) FROM residents WHERE resident_code IN (<DS-04 resident codes>);` | `0` on both |
| 2 | `SELECT filename FROM ingest_batches WHERE filename ILIKE '%ds-04%' OR filename ILIKE '%team1%';` on both | 0 rows |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/ingest` (calibration database) with DS-04 | 2xx with batch counts |
| 2 | `GET /api/v1/ingest/batches/{id}` | Counts and rejection reasons |
| 3 | `POST /api/v1/ingest` with a row of `schema_version` `9.9` | Row rejected with `unsupported_schema_version` |
| 4 | `GET /api/v1/analytics` | `meta.cusum_h`, `meta.baseline_n`, `meta.pipeline_profile` present |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | Calibration DB: `SELECT count(DISTINCT resident_code) FROM raw_sessions;` | `50` |
| 2 | `test_v0_1` config hash before/after (TC-093-11) | Equal |
| 3 | Audit rows `config.changed` / `pipeline.rebuild` (TC-093-09) | One per key, then one rebuild |
| 4 | Failed run before rebuild (TC-093-10) | `status` `failed`, warning `config_changed_requires_rebuild` |
| 5 | DS-04 residents in staging/production (TC-093-15) | 0 |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Unexplained intake rejection (TC-093-03) | Calibration stops |
| 2 | Selection with OQ-27 open (TC-093-08) | No selection, no `set-config` |
| 3 | Run after `set-config` without `rebuild` (TC-093-10) | Run fails with `config_changed_requires_rebuild` |
| 4 | Unknown key / invalid value (TC-093-12) | Exit 2, no change |
| 5 | Answer key referenced from `analytics/` or `backend/` (TC-093-07) | No reference |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-093-AC-01 | Intake report lists 0 rejections, or every rejection with a Team 1 explanation, before any evaluation run | TC-093-02, TC-093-03 |
| FEAT-093-AC-02 | `calibration_results.json` contains 140 combinations, each with metrics (a)–(e) | TC-093-04, TC-093-05 |
| FEAT-093-AC-03 | `grep -rn "team1_v1" analytics backend` returns no matches | TC-093-07 |
| FEAT-093-AC-04 | After calibration `pytest tests/validation -q` passes and `test_v0_1` rows are unchanged | TC-093-11 |
| FEAT-093-AC-05 | Each production change has one `config.changed` row with the report as reason, followed by one `pipeline.rebuild` | TC-093-09, TC-093-10, TC-093-12 |
| FEAT-093-AC-06 | No CI required check depends on DS-04 results | TC-093-13 |

## Test Data Requirements

- DS-04 (synthetic, 50 residents, ≥ 120 days) and its separate answer key under `tests/fixtures/answer_key/team1_v1/`.
- A dedicated local calibration database (D-75); never staging or production.
- Hand-made result sets for the metric unit tests.
- Local profile `production` data for rehearsing `set-config` / `rebuild` (e.g. the SRC-05 records loaded under profile `production`).

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| TDV-004, TDV-010 | FEAT-093 | TC-093-01 |
| TDV-090, CUS-030 | FEAT-093 | TC-093-02, TC-093-03 |
| CUS-030, TDV-007, AGT-014 | FEAT-093 | TC-093-15 |
| CUS-031, ANL-007, D-01 | FEAT-093 | TC-093-04, TC-093-08 |
| CUS-032 | FEAT-093 | TC-093-04, TC-093-05 |
| TDV-091 | FEAT-093 | TC-093-06 |
| CUS-033, AGT-007 | FEAT-093 | TC-093-07 |
| CUS-034, OQ-13, OQ-27 | FEAT-093 | TC-093-08, TC-093-09 |
| ANL-032, D-56, D-69 | FEAT-093 | TC-093-09, TC-093-10, TC-093-12 |
| CUS-035, AGT-008 | FEAT-093 | TC-093-11 |
| TDV-092 | FEAT-093 | TC-093-13 |
| CUS-029 | FEAT-093 | TC-093-14 |
| FEAT-093-FR-01..FEAT-093-FR-13 | FEAT-093 | TC-093-01..TC-093-15 |
