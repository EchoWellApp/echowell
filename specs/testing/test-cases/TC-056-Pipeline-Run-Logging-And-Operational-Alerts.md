# Pipeline run logging and operational alerts

## Feature Description

FEAT-056 makes every pipeline run observable and every operational failure detectable. Around the runner (FEAT-053) it emits structured JSON log events: INFO `pipeline_run_started` (`pipeline_run_id`, `trigger`, `scope`, `profile`, `config_hash`), INFO `pipeline_run_succeeded` or ERROR `pipeline_run_failed` (with `counts`, `duration_ms`, `warning_count`), one `pipeline_warning` per warning (WARNING; ERROR for `baseline_mismatch`) and INFO `data_alerts_updated`. Failed residents add an `exception` warning whose `detail` is "<stage name>: <exception type>: <sanitised message>" with the LOG-063 stage names. Runs left `running` for more than 30 minutes are marked `failed` with warning `run_abandoned`; failed runs are never retried in place; nightly runs add `counts.db_size_bytes`; a non-running nightly firing logs ERROR `nightly_run_missing` (and reports to Sentry when `SENTRY_DSN` is set) when the last due night has no succeeded nightly run. No feature value, payload, e-mail or secret is logged.

## Preconditions

- Local development stack; disposable database seeded with `python -m backend.cli seed test_v0_1` (DS-07) unless stated otherwise.
- Backend started with `LOG_FORMAT=json` and its stdout/stderr redirected to a file, e.g. `uvicorn backend.main:app 2>&1 | tee /tmp/api.log`.
- Run-injection script `inject.py` (repository root) for TC-056-01 and TC-056-04:

```python
import sys
from datetime import datetime, UTC
from unittest import mock
import analytics.pipeline as engine
from backend.core import db
from backend.core.config import load_settings_or_exit
from backend.core.logging import configure_logging
from backend.models import PipelineTrigger
from backend.services.pipeline_runner import PipelineRunner
s = load_settings_or_exit(operator=True)
configure_logging(s.log_level, "json", s.app_env, s.git_sha)
f = db.session_factory(db.create_engine_for(s.database_url, app_env=s.app_env))
runner = PipelineRunner(f, s)
as_of = datetime(2026, 10, 30, 20, tzinfo=UTC)
if sys.argv[1:] == ["cusum"]:
    with mock.patch.object(engine, "run_cusum", side_effect=RuntimeError("injected")):
        print(runner.run("all", PipelineTrigger.TEST, "test_v0_1", as_of)[1])
else:
    print(runner.run("all", PipelineTrigger.TEST, "test_v0_1", as_of)[1])
```

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-056-01 | Exception in the `cusum` stage leaves derived tables unchanged and fails the run with a stage-named `exception` warning | High | Negative |
| TC-056-02 | Run left `running` for 31 minutes is marked `failed` with `run_abandoned` | High | Negative |
| TC-056-03 | Non-running nightly firing logs ERROR `nightly_run_missing` | High | Negative |
| TC-056-04 | Successful run logs exactly one start and one completion JSON event with the required fields | High | Positive |
| TC-056-05 | Nightly run stores `counts.db_size_bytes` as a positive integer | High | Database |
| TC-056-06 | Logs of a SRC-05 batch run contain no feature value and no e-mail address | High | Security |
| TC-056-07 | Warnings are stored as `{code, resident_code, session_id, detail}` and logged as `pipeline_warning` | Medium | Positive |
| TC-056-08 | Failed runs are not retried in place; two failures leave two `failed` rows | Medium | Negative |
| TC-056-09 | `data_alerts_updated` logged once per run with counts per kind | Medium | Positive |
| TC-056-10 | `/admin` banner data is available from `GET /api/v1/pipeline/runs` | Medium | API |

### TC-056-01 Exception in the `cusum` stage leaves derived tables unchanged and fails the run with a stage-named `exception` warning

| Step | Action | Expected Result |
|---|---|---|
| 1 | `\copy (SELECT * FROM scores ORDER BY processed_session_id) TO '/tmp/scores_before.csv' CSV`; same for `cusum_state` (order by `epoch_id`) and `alerts` (order by `session_id`) | Files written |
| 2 | `python inject.py cusum 2> /tmp/inject.log` | Prints `failed` |
| 3 | `SELECT status, error_message, warnings FROM pipeline_runs ORDER BY started_at DESC LIMIT 1;` | `failed`; `error_message` non-empty (`injected`); `warnings` contains one item with `code` `exception`, `resident_code` null, `session_id` null and `detail` starting with `cusum:` |
| 4 | Export the three tables again and `diff` against step 1 | No difference |
| 5 | `grep pipeline_run_failed /tmp/inject.log` | Exactly one ERROR line with the run's `pipeline_run_id`, `exc_type` `RuntimeError` |
| 6 | With the same injection in the API process (integration test), `POST /api/v1/sessions` | 201 with `status_after_processing` "pending" (see TC-054-04) |

Note: TRD 17 LOG-062/LOG-063 require `detail` "<stage name>: <exception type>: <message>" (here `cusum: RuntimeError: injected`); the code writes `RuntimeError: injected` without the stage name for engine exceptions (`backend/services/pipeline_runner.py:274`) and `persistence: …` for resident write failures (`backend/services/pipeline_runner.py:397`), so step 3 is expected to fail until aligned.

### TC-056-02 Run left `running` for 31 minutes is marked `failed` with `run_abandoned`

This case writes a test row (as `echowell_migrator`, disposable database).

| Step | Action | Expected Result |
|---|---|---|
| 1 | `INSERT INTO pipeline_runs (id, trigger, scope, config_profile, config_snapshot, code_version, as_of, started_at, status) SELECT gen_random_uuid(), 'manual', '{"type": "all"}', 'test_v0_1', config_snapshot, 'unknown', as_of, now() - interval '31 minutes', 'running' FROM pipeline_runs WHERE status='succeeded' LIMIT 1 RETURNING id;` | 1 row; note the id |
| 2 | `python -m backend.cli run-pipeline --scope all --as-of 2026-10-30T15:00:00-05:00` | New run `succeeded` |
| 3 | `SELECT status, error_message, warnings, finished_at IS NOT NULL FROM pipeline_runs WHERE id='<id>';` | `failed`; `Run abandoned: still running 30 minutes after it started.`; warnings contain `{"code": "run_abandoned", "resident_code": null, "session_id": null, "detail": "still running 30 minutes after it started"}`; `t` |
| 4 | Repeat step 1 with `interval '29 minutes'`, then step 2 | That row stays `running` until it exceeds 30 minutes |
| 5 | `pytest tests/integration/api/test_pipeline.py -q -k stale_running` | `test_stale_running_run_is_abandoned` passes |

### TC-056-03 Non-running nightly firing logs ERROR `nightly_run_missing`

| Step | Action | Expected Result |
|---|---|---|
| 1 | On DS-07 (no nightly run exists), set `NIGHTLY_RUN_HOUR_LOCAL` to an hour that is not the current America/Chicago hour and has already passed today, `LOG_FORMAT=json` | Environment ready |
| 2 | `python -m backend.jobs.nightly_run 2> /tmp/nightly.log; echo $?` | Exit `0`; no run started |
| 3 | `grep nightly_run_missing /tmp/nightly.log` | One ERROR JSON line with `local_date` = today's facility-local date |
| 4 | `SELECT count(*) FROM pipeline_runs WHERE trigger='nightly';` | `0` (the check never starts a run) |
| 5 | `pytest tests/integration/pipeline/test_nightly_run.py -q -k missed_night` | `test_missed_night_is_reported` passes (`local_date` "2026-10-31", no run row) |

### TC-056-04 Successful run logs exactly one start and one completion JSON event with the required fields

| Step | Action | Expected Result |
|---|---|---|
| 1 | `python inject.py 2> /tmp/ok.log` | Prints `succeeded` |
| 2 | `grep -c pipeline_run_started /tmp/ok.log; grep -c pipeline_run_succeeded /tmp/ok.log` | `1` and `1` |
| 3 | Parse the start line as JSON | Single valid JSON object with `level` INFO, `pipeline_run_id`, `trigger` "test", `scope` {"type": "all"}, `profile` "test_v0_1", `config_hash` (64 hex), plus `ts`, `logger`, `msg`, `env`, `version` |
| 4 | Parse the completion line | `level` INFO, same `pipeline_run_id`, `trigger`, `profile`, `config_hash`, `counts` (12 keys, `usable` 267), `duration_ms` (integer ≥ 0), `warning_count` 0 |
| 5 | `grep -c pipeline_run_failed /tmp/ok.log` | `0` |

### TC-056-05 Nightly run stores `counts.db_size_bytes` as a positive integer

| Step | Action | Expected Result |
|---|---|---|
| 1 | Set `NIGHTLY_RUN_HOUR_LOCAL` to the current America/Chicago hour; `PIPELINE_AS_OF=2026-10-30T15:00:00-05:00`; `python -m backend.jobs.nightly_run` | Exit 0 |
| 2 | `SELECT counts->'db_size_bytes', jsonb_typeof(counts->'db_size_bytes') FROM pipeline_runs WHERE trigger='nightly';` | A value > 0, type `number` (integer) |
| 3 | `SELECT counts ? 'db_size_bytes' FROM pipeline_runs WHERE trigger='manual';` | `f` (only nightly runs carry it) |

### TC-056-06 Logs of a SRC-05 batch run contain no feature value and no e-mail address

Empty roster database (`seed test_v0_1 --master-only`), API with `LOG_FORMAT=json`, output in `/tmp/api.log`, `PIPELINE_AS_OF=2026-10-30T15:00:00-05:00`.

| Step | Action | Expected Result |
|---|---|---|
| 1 | Admin login, `POST /api/v1/ingest` with the SRC-05 CSV; poll the run to `succeeded` | 202, then `succeeded` |
| 2 | `grep -E -- "-28\.29|178\.8|4\.93|26\.8|0\.517" /tmp/api.log` (feature values of SRC-05 row R09-20261021-01) | No output |
| 3 | `grep -E "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[a-z]{2,}" /tmp/api.log` | No output (login e-mails redacted) |
| 4 | `grep -i -E "password|X-API-Key|postgresql://" /tmp/api.log` | No secret value or connection string |

### TC-056-07 Warnings are stored as `{code, resident_code, session_id, detail}` and logged as `pipeline_warning`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Cause a warning: `python -m backend.cli set-config --profile test_v0_1 --key cusum_h --value '6.0' --reason "test"` then `python inject.py 2> /tmp/warn.log` | Run `failed` (configuration changed) |
| 2 | `SELECT warnings FROM pipeline_runs ORDER BY started_at DESC LIMIT 1;` | `[{"code": "config_changed_requires_rebuild", "resident_code": null, "session_id": null, "detail": "configuration changed; run the rebuild command"}]` |
| 3 | `grep pipeline_warning /tmp/warn.log` | One WARNING line with `code` `config_changed_requires_rebuild` |
| 4 | Restore: `set-config ... --value '5.0' --reason "test"` | Hash equals the last succeeded run again |

### TC-056-08 Failed runs are not retried in place; two failures leave two `failed` rows

| Step | Action | Expected Result |
|---|---|---|
| 1 | After step 1 of TC-056-07, run `python -m backend.cli run-pipeline --scope all` twice | Each prints `Pipeline run <uuid> failed.` with a different uuid |
| 2 | `SELECT id, status FROM pipeline_runs WHERE status='failed' ORDER BY started_at;` | One row per failed invocation (each failure keeps its own row; no automatic re-run row in between) |
| 3 | `grep -rn "retry\|while True" backend/services/pipeline_runner.py` | No in-process retry loop |
| 4 | Admin `GET /api/v1/pipeline/runs?status=failed` | All failed rows listed, newest first |

### TC-056-09 `data_alerts_updated` logged once per run with counts per kind

| Step | Action | Expected Result |
|---|---|---|
| 1 | In `/tmp/ok.log` from TC-056-04: `grep data_alerts_updated /tmp/ok.log` | Exactly one INFO line with `open` {"baseline_stalled": 1, "possible_other_speaker": 1, "high_set_aside": 1, "device_silent": 1} |
| 2 | Check the level of that line | INFO, not ERROR (data alerts are not operational errors) |

Note: FEAT-056-FR-12 / LOG-115 ask for counts per kind for open and resolved; the code logs only the open counts (`backend/services/pipeline_runner.py:422-427`).

### TC-056-10 `/admin` banner data is available from `GET /api/v1/pipeline/runs`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Admin `GET /api/v1/pipeline/runs?limit=1` | 200; the latest run of any trigger with its `status` (the failure banner shows when it is `failed`) |
| 2 | `GET /api/v1/pipeline/runs?trigger=nightly&status=succeeded&limit=1` | 200; latest succeeded nightly run with `started_at` (banner "Nightly run missing for <date>" when none within 26 hours) |
| 3 | `GET /api/v1/pipeline/runs?trigger=bogus` | 422 `INVALID_QUERY_PARAMETER` |
| 4 | Clinician `GET /api/v1/pipeline/runs` | 403 |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/pipeline/runs/{id}` of the TC-056-02 abandoned row | 200, `status` "failed", `warnings` include `run_abandoned` |
| 2 | `GET /api/v1/pipeline/runs?status=failed` (researcher) | 200 `PipelineRunList` |
| 3 | `GET /api/v1/pipeline/runs/{nightly id}` | `counts.db_size_bytes` > 0 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT count(*) FROM pipeline_runs WHERE status='running' AND started_at < now() - interval '30 minutes';` after any run | `0` |
| 2 | `SELECT jsonb_array_elements(warnings) ? 'code' FROM pipeline_runs WHERE warnings <> '[]';` | `t` for every element; each also has `resident_code`, `session_id`, `detail` |
| 3 | `SELECT count(*) FROM pipeline_runs WHERE status='failed' AND (error_message IS NULL OR error_message='');` | `0` |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Engine stage exception | Run `failed`, `exception` warning, derived tables unchanged |
| 2 | Stale `running` row | Marked `failed` with `run_abandoned` at the next run start |
| 3 | No succeeded nightly run for the last due night | ERROR `nightly_run_missing`, no run started |
| 4 | Repeated failure | Separate `failed` rows, no in-place retry |
| 5 | Log scan for feature values, e-mails, secrets | No match |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-056-AC-01 | Exception in `cusum` leaves `scores`, `cusum_state`, `alerts` unchanged; run `failed` with an `exception` warning naming stage `cusum`; triggering ingest returns 201 | TC-056-01 |
| FEAT-056-AC-02 | Row `running` since 31 minutes ago marked `failed` with `run_abandoned` and non-empty `error_message` at the next run | TC-056-02 |
| FEAT-056-AC-03 | No succeeded nightly run in 26 hours → non-running firing logs ERROR `nightly_run_missing` | TC-056-03 |
| FEAT-056-AC-04 | Exactly one start and one completion JSON event with the required fields | TC-056-04 |
| FEAT-056-AC-05 | Nightly run stores `counts.db_size_bytes` as a positive integer | TC-056-05 |
| FEAT-056-AC-06 | Logs of a SRC-05 batch run contain no feature value and no e-mail | TC-056-06 |

## Test Data Requirements

- DS-07 and an empty roster database; SRC-05 CSV; the `inject.py` helper above (test-only, not committed).
- Environment: `LOG_FORMAT=json`, `LOG_LEVEL=INFO`, `NIGHTLY_RUN_HOUR_LOCAL`, `FACILITY_TZ=America/Chicago`, `PIPELINE_AS_OF` (non-production), `DATABASE_URL`, `DATABASE_MIGRATION_URL` (for the TC-056-02 insert), `SEED_*` passwords; `SENTRY_DSN` unset unless Sentry reporting is checked.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-056-FR-01 / LOG-060, ANL-053 | FEAT-056 | TC-056-04 |
| FEAT-056-FR-02 / LOG-065 | FEAT-056 | TC-056-04 |
| FEAT-056-FR-03 / LOG-062, LOG-061 | FEAT-056 | TC-056-01 |
| FEAT-056-FR-04 / LOG-063, D-80 | FEAT-056 | TC-056-01 |
| FEAT-056-FR-05 / LOG-064, ANL-052 | FEAT-056 | TC-056-07 |
| FEAT-056-FR-06 / LOG-066, API-068 | FEAT-056 | TC-056-02 |
| FEAT-056-FR-07 / LOG-067, D-132 | FEAT-056 | TC-056-08 |
| FEAT-056-FR-08 / DB-049 | FEAT-056 | TC-056-05 |
| FEAT-056-FR-09 / LOG-111 | FEAT-056 | TC-056-03 |
| FEAT-056-FR-10 / LOG-112, API-134 | FEAT-056 | TC-056-10 |
| FEAT-056-FR-11 / ANL-054, LOG-020..LOG-022 | FEAT-056 | TC-056-06 |
| FEAT-056-FR-12 / LOG-115 | FEAT-056 | TC-056-09 |
| FEAT-056-FR-13 / LOG-114 | FEAT-056 | TC-056-01 step 5, TC-056-03 (ERROR events that Sentry and incident watchers receive) |
| AC-LOG-05, AC-LOG-06, AC-LOG-07 | FEAT-056 | TC-056-01, TC-056-02, TC-056-03 |
