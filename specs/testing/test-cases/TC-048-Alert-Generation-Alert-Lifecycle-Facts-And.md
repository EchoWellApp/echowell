# Alert generation, alert lifecycle facts and Leaning most

## Feature Description

FEAT-048 implements `analytics/alert_generator.py::generate_alerts(scores, epochs, config)` and `leaning_most(scores, alert, config)`. Exactly one alarm event is created per resident-epoch whose scores contain the "rings" row, with that session's `session_id`, `triggered_at` (its `timestamp_utc`), `local_date` and `cusum_value` (its tally); no event is created for a forming epoch, while the tally stays below h, or a second time after the tally drops and recrosses. Each event carries `epoch_ended` / `epoch_ended_at` (the next epoch's `started_at`) so the persistence service closes it with reason "epoch ended", and the natural key (epoch, session_id) so a rebuild keeps the alert row, its reviews, acknowledgement and snooze (an event no longer produced means "superseded by rebuild"). There is no manual closure ("admin" is reserved). "Leaning most" returns up to 3 composite features with the highest positive mean signed z (sign × z) over the alert epoch's scored sessions from the alarm date to the as-of, ties in canonical order, empty when none is positive; `GET /api/v1/alerts` returns it per alert. New-admission comparisons never create alerts and nothing is sent by e-mail, SMS or push. On SRC-05 exactly two events exist: R09 at R09-20261021-01 (5.431965) and R10 at R10-20261024-01 (5.972050); Leaning most is (number_of_pauses, loudness_dbfs, voiced_fraction) for R09 and (number_of_pauses, articulation_rate_syl_per_s, speech_rate_syl_per_s) for R10.

## Preconditions

- Local development stack per `README.md` quick start; Python REPL started from the repository root with `import sys; sys.path.insert(0, ".")`.
- REPL helpers: `from analytics.alert_generator import generate_alerts, leaning_most; from analytics.cusum_engine import run_cusum; from analytics.config import TEST_V0_1 as C, ScoreRow, EpochSummary; from tests.unit.analytics.src05 import records, result, RESIDENTS, ASSIGNMENTS, AS_OF; from analytics.pipeline import run_pipeline; from dataclasses import replace; from datetime import datetime, date, UTC`.
- Local Docker Compose (demo profile) seeded with `python -m backend.cli seed test_v0_1 --reset` (DS-07: as-of 2026-10-30 15:00 America/Chicago); API at `http://localhost:8000/api/v1`; `psql` read access.
- Tokens from `POST /api/v1/auth/login`: ADMIN_TOKEN, CLINICIAN_TOKEN, RESEARCHER_TOKEN (`SEED_*` passwords). The ingest API key from the environment file (INGEST_KEY).
- Cases TC-048-08 and TC-048-09 change data; run them last and reseed afterwards.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-048-01 | A first crossing yields one event; a drop below h and recrossing yields no second event | High | Analytics |
| TC-048-02 | Event of an epoch followed by a later epoch has `epoch_ended` true and `epoch_ended_at` = next `started_at` | High | Analytics |
| TC-048-03 | SRC-05: exactly two events (R09, R10) with session, times and cusum values; not epoch-ended | High | Database |
| TC-048-04 | Leaning most for R09 and R10 | High | Analytics |
| TC-048-05 | Leaning most rules: window from the alarm date, positive means only, top 3, canonical tie-break, empty result | Medium | Analytics |
| TC-048-06 | `GET /api/v1/alerts?status=open` returns the Leaning most arrays (DS-07) | High | API |
| TC-048-07 | No alert for forming epochs or tallies below h; alerts only from own-baseline scoring | High | Database |
| TC-048-08 | After a review and a snooze, a full rebuild keeps the alert id, reviews, `acknowledged` and `snoozed_until` | High | Database |
| TC-048-09 | A new epoch closes the epoch-1 alert with "epoch ended" and the resident shows `baseline_forming` | High | Database |
| TC-048-10 | No manual closure route or reason; no notification channel | Medium | Security |
| TC-048-11 | Alerts list access by role | Medium | Negative |

### TC-048-01 One event per crossing; no second event on recrossing

| Step | Action | Expected Result |
|---|---|---|
| 1 | `rows = [ScoreRow(f"S{i}", "x", "R01", 1, date(2026, 10, 1 + i), False, {}, 0.0, z, scored_ordinal=i + 1) for i, z in enumerate([6.0, -20.0, 6.0])]; out = run_cusum(rows, C); print([(r.cusum_tally, r.alarm_state) for r in out])` | `[(5.5, 'rings'), (0.0, 'on'), (5.5, 'on')]` |
| 2 | `ev = generate_alerts(out, [], C, timestamps={"S0": datetime(2026, 10, 1, 19, tzinfo=UTC)}); print(len(ev), ev[0].session_id, ev[0].triggered_at, ev[0].cusum_value, ev[0].epoch_ended)` | `1 S0 2026-10-01 19:00:00+00:00 5.5 False` (the recrossing on S2 creates no second event) |
| 3 | `pytest -m unit tests/unit/analytics/test_alert_generator.py -v` | `test_one_event_per_ringing_epoch_with_closure_facts`, `test_leaning_most_rules`, `test_src05_alerts_and_leaning_most` PASSED |

### TC-048-02 Epoch-ended facts

| Step | Action | Expected Result |
|---|---|---|
| 1 | `last = next(r for r in records() if r.session_id == "R09-20261030-01"); new = replace(last, session_id="R09-20261031-01", arrival_seq=2000, raw_session_id="00000000-0000-0000-0000-000000002000", timestamp_utc=datetime(2026, 10, 31, 19, 0, tzinfo=UTC), device_firmware_version="fw-1.0.1"); res = run_pipeline([*records(), new], RESIDENTS, ASSIGNMENTS, C, datetime(2026, 10, 31, 21, tzinfo=UTC))` | No exception |
| 2 | `print([(e.epoch_number, e.started_at, e.ended_at) for e in res.epochs if e.resident_code == "R09"])` | Epoch 1 ended 2026-10-31 19:00:00+00:00; epoch 2 started 2026-10-31 19:00:00+00:00, `ended_at` None |
| 3 | `a = next(a for a in res.alerts if a.resident_code == "R09"); print(a.epoch_number, a.session_id, a.epoch_ended, a.epoch_ended_at)` | `1 R09-20261021-01 True 2026-10-31 19:00:00+00:00` (= epoch 2 `started_at`) |

### TC-048-03 SRC-05: exactly two events

| Step | Action | Expected Result |
|---|---|---|
| 1 | REPL: `for a in result().alerts: print(a.resident_code, a.epoch_number, a.session_id, a.triggered_at, a.local_date, a.cusum_value, a.epoch_ended, a.epoch_ended_at)` | `R09 1 R09-20261021-01 2026-10-21 19:07:50+00:00 2026-10-21 5.431964961894293 False None` and `R10 1 R10-20261024-01 2026-10-24 19:25:37+00:00 2026-10-24 5.972049558349562 False None` |
| 2 | `SELECT r.resident_code, a.session_id, a.triggered_at, a.local_date, a.cusum_value, a.status, a.closed_reason FROM alerts a JOIN residents r ON r.id = a.resident_id ORDER BY 1;` | 2 rows: R09, R09-20261021-01, 2026-10-21 19:07:50+00, 2026-10-21, 5.431965 (±1e-6), `open`, NULL; R10, R10-20261024-01, 2026-10-24 19:25:37+00, 2026-10-24, 5.972050 (±1e-6), `open`, NULL |
| 3 | `SELECT counts->>'alerts_opened' FROM pipeline_runs WHERE status = 'succeeded' ORDER BY started_at DESC LIMIT 1;` | `2` |
| 4 | `pytest -m validation tests/validation/test_global_checks.py -k vc_g10 -v` | `test_vc_g10_alerts` PASSED (exactly the two open alerts with these sessions, times and cusum values) |

### TC-048-04 Leaning most for R09 and R10

| Step | Action | Expected Result |
|---|---|---|
| 1 | `a9 = next(a for a in result().alerts if a.resident_code == "R09"); print(leaning_most(result().scores, a9, C))` | `('number_of_pauses', 'loudness_dbfs', 'voiced_fraction')` (sessions Oct 21–30; mean signed z ≈ 2.158, 2.133, 2.092) |
| 2 | `a10 = next(a for a in result().alerts if a.resident_code == "R10"); print(leaning_most(result().scores, a10, C))` | `('number_of_pauses', 'articulation_rate_syl_per_s', 'speech_rate_syl_per_s')` (sessions Oct 24–30) |
| 3 | `print(a9.leaning_most, a10.leaning_most)` | The same tuples carried on the run-time events |

### TC-048-05 Leaning most rules

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read and run `test_leaning_most_rules` (`pytest ... -k leaning_most_rules -v`) | PASSED: a session before the alarm date is ignored; signed means loudness 2.0, pause_fraction 1.0, voiced 1.0, pauses 0.25, speech rate −1.0 give (`loudness_dbfs`, `pause_fraction`, `voiced_fraction`) — pause_fraction before voiced_fraction on the tie (canonical order), speech rate excluded (mean ≤ 0); a single session whose only non-zero signed z is negative gives `()` |
| 2 | `z0 = {f"z_{k}": 0.0 for k in ("loudness_dbfs", "total_phrase_duration_s", "speech_rate_syl_per_s", "articulation_rate_syl_per_s", "number_of_pauses", "pause_fraction", "voiced_fraction")}; s = ScoreRow("S1", "x", "R01", 1, date(2026, 10, 1), False, z0, 0.0, 0.0, cusum_tally=5.0, alarm_state="rings"); ev = generate_alerts([s], [], C, timestamps={"S1": datetime(2026, 10, 1, tzinfo=UTC)})[0]; print(leaning_most([s], ev, C))` | `()` (all means 0, none > 0) |
| 3 | Check that "Leaning most" never lists more than 3 keys | `len(...) ≤ 3` in every case; `Alert.leaning_most` has `maxItems: 3` in `docs/api_reference/openapi.json` |

### TC-048-06 GET /alerts returns Leaning most (DS-07)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/alerts?status=open` with CLINICIAN_TOKEN | 200; `total` = 2; items for R09 and R10 |
| 2 | Inspect the R09 item | `session_id` "R09-20261021-01", `triggered_at` "2026-10-21T19:07:50Z", `local_date` "2026-10-21", `cusum_value` 5.431965 (±1e-6), `current_tally` 26.830256 (±1e-6), `open_days` 9, `status` "open", `reviewed` false, `leaning_most` = ["number_of_pauses", "loudness_dbfs", "voiced_fraction"], `closed_reason` null |
| 3 | Inspect the R10 item | `session_id` "R10-20261024-01", `cusum_value` 5.972050, `current_tally` 13.418183 (±1e-6), `open_days` 6, `leaning_most` = ["number_of_pauses", "articulation_rate_syl_per_s", "speech_rate_syl_per_s"] |
| 4 | Open `http://localhost:3001/residents/R09` logged in as clinician (UI cross-check of FEAT-069) | Summary line reads "Leaning most: more pauses, quieter, less voiced sound" |
| 5 | `pytest -m integration tests/integration/api/test_ui_fixture_ds07.py -k leaning_most -v` and `pytest -m integration tests/integration/pipeline/test_runner_persistence.py -k leaning_most -v` | `test_open_alarms_and_leaning_most` and `test_alerts_endpoint_leaning_most` PASSED |

### TC-048-07 No alert without formed baseline or below h; own-baseline only

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT r.resident_code, count(a.id) FROM residents r LEFT JOIN alerts a ON a.resident_id = r.id GROUP BY 1 ORDER BY 1;` | R09 1, R10 1, all others 0 (R08 and R07 epoch 1 never formed; R05 peaked at 4.005975 < 5.0) |
| 2 | `SELECT count(*) FROM alerts a JOIN residents r ON r.id = a.resident_id WHERE r.cohort = 'new_admission';` | 0 |
| 3 | `SELECT count(*) FROM alerts a JOIN scores s ON s.epoch_id = a.epoch_id JOIN processed_sessions p ON p.id = s.processed_session_id WHERE p.session_id = a.session_id AND s.alarm_state <> 'rings';` | 0 (every alert points at its epoch's "rings" session) |
| 4 | `GET /api/v1/admissions` as admin | 200; calling it creates no alert (`SELECT count(*) FROM alerts` still 2) |

### TC-048-08 Rebuild keeps alert id, reviews, acknowledgement and snooze

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT id FROM alerts WHERE session_id = 'R09-20261021-01';` — note ALERT_ID | One uuid |
| 2 | As clinician `POST /api/v1/alerts/ALERT_ID/reviews` body `{"outcome": "known_cause", "explanations": ["poor_sleep_unusual_day"]}` | 201 |
| 3 | As clinician `POST /api/v1/alerts/ALERT_ID/snooze` body `{"hours": 24}` | 200; body `status` "acknowledged", `snoozed_until` set (24 h after the request time) |
| 4 | `SELECT status, acknowledged_by IS NOT NULL, snoozed_until FROM alerts WHERE id = 'ALERT_ID'; SELECT count(*) FROM alert_reviews WHERE alert_id = 'ALERT_ID';` | `acknowledged`, true, a timestamp — note it as SNOOZE; review count 1 |
| 5 | With `PIPELINE_AS_OF=2026-10-30T15:00:00-05:00` in the environment run `python -m backend.cli rebuild --profile test_v0_1 --confirm REBUILD; echo "exit=$?"` | `exit=0`; a `pipeline.rebuild` audit row is written |
| 6 | `SELECT id, status, snoozed_until, closed_reason FROM alerts WHERE session_id = 'R09-20261021-01';` | Same ALERT_ID; `acknowledged`; `snoozed_until` = SNOOZE; `closed_reason` NULL |
| 7 | `SELECT count(*) FROM alert_reviews WHERE alert_id = 'ALERT_ID';` | 1 |
| 8 | `python -m backend.cli rebuild --profile test_v0_1 --confirm yes; echo "exit=$?"` | Prints "Refused: type --confirm REBUILD to delete and recompute all baselines"; `exit=2` |

### TC-048-09 New epoch closes the epoch-1 alert

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/sessions` with `X-API-Key: INGEST_KEY` and the SRC-05 row R09-20261030-01 changed to `session_id` "R09-20261031-01", `timestamp_utc` "2026-10-31 19:00:00", `device_firmware_version` "fw-1.0.1" | 201 |
| 2 | Wait until no run is `running` (`GET /api/v1/pipeline/runs?status=running` → `total` 0); then admin `POST /api/v1/pipeline/run` body `{"scope": ["R09"], "profile": "test_v0_1", "as_of": "2026-10-31T16:00:00-05:00"}` and poll `GET /api/v1/pipeline/runs/{id}` | 202, then `succeeded` |
| 3 | `SELECT e.epoch_number, e.started_at, e.ended_at FROM epochs e JOIN residents r ON r.id = e.resident_id WHERE r.resident_code = 'R09' ORDER BY 1;` | Epoch 1 `ended_at` 2026-10-31 19:00:00+00; epoch 2 `started_at` 2026-10-31 19:00:00+00, `ended_at` NULL |
| 4 | `SELECT status, closed_reason, closed_at FROM alerts WHERE session_id = 'R09-20261021-01';` | `closed`, `epoch ended`, 2026-10-31 21:00:00+00 (the run's as-of) |
| 5 | `SELECT action, details FROM audit_logs WHERE action = 'alert.closed' ORDER BY id DESC LIMIT 1;` | One row: `action` `alert.closed`, `details` = `{"resident_code": "R09", "closed_reason": "epoch ended"}` |
| 6 | `GET /api/v1/residents/R09` as admin | `status` = "baseline_forming"; `epoch_count` = 2; `current_epoch.epoch_number` = 2; `restart_cause` = "firmware" |
| 7 | `GET /api/v1/alerts?status=open` | `total` = 1 (R10 only) |
| 8 | `pytest -m integration tests/integration/pipeline/test_runner_persistence.py -v` | All PASSED |

### TC-048-10 No manual closure; no notification channel

| Step | Action | Expected Result |
|---|---|---|
| 1 | Search `docs/api_reference/openapi.json` paths for a close, acknowledge or delete operation on alerts | Only `GET /alerts`, `GET`/`POST /alerts/{id}/reviews`, `POST /alerts/{id}/snooze` exist |
| 2 | `POST /api/v1/alerts/ALERT_ID/close` and `DELETE /api/v1/alerts/ALERT_ID` with ADMIN_TOKEN | 404 or 405 for both |
| 3 | `SELECT count(*) FROM alerts WHERE closed_reason = 'admin';` | 0 |
| 4 | `grep -rn -i -E "smtplib\|sendgrid\|twilio\|firebase\|web-push\|pywebpush" analytics/ backend/ backend/requirements*.txt` | No match |

### TC-048-11 Alerts list access by role

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/alerts` with ADMIN_TOKEN, CLINICIAN_TOKEN, RESEARCHER_TOKEN | 200, 200, 200 (same `leaning_most` values for each) |
| 2 | `GET /api/v1/alerts` with no credentials and with `X-API-Key: INGEST_KEY` | 401, 401 |
| 3 | `GET /api/v1/alerts?status=bogus` and `GET /api/v1/alerts?resident_code=r09` | 422, 422 problem+json |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/alerts?status=open` | 2 `Alert` items with `leaning_most` arrays of TC-048-06 (schema unchanged: array of up to 3 `ScoredFeatureKey`) |
| 2 | `POST /api/v1/alerts/{id}/reviews`, `POST /api/v1/alerts/{id}/snooze` | 201 / 200; state survives a rebuild (TC-048-08) |
| 3 | Unknown alert operations (close, delete, acknowledge) | 404 or 405 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `alerts` rows after the seed | 2 open alerts (R09, R10) with the values of TC-048-03 |
| 2 | Natural key | `SELECT epoch_id, session_id, count(*) FROM alerts GROUP BY 1, 2 HAVING count(*) > 1;` → 0 rows |
| 3 | After rebuild | Same alert ids, reviews kept (TC-048-08) |
| 4 | After a new epoch | Epoch-1 alert `closed` / `epoch ended`, `closed_at` = as-of; `alert.closed` audit (TC-048-09) |
| 5 | `closed_reason` values present | Only NULL, `epoch ended` or `superseded by rebuild`; never `admin` |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Tally drops below h and recrosses | No second event (TC-048-01) |
| 2 | Forming epoch / tally below h | No alert (TC-048-07) |
| 3 | No feature with positive mean | `leaning_most` = `()` / `[]` (TC-048-05) |
| 4 | Manual close or delete of an alert | 404 or 405 (TC-048-10) |
| 5 | Rebuild without the confirmation word | Refused, exit 2 (TC-048-08) |
| 6 | Anonymous / API-key call to `GET /alerts` | 401 (TC-048-11) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-048-AC-01 | A first crossing yields one `AlertEvent` with resident, epoch, session_id, `triggered_at`, `cusum_value` of the "rings" row; dropping below h and recrossing yields no second event | TC-048-01 |
| FEAT-048-AC-02 | With a later epoch, the epoch-1 event has `epoch_ended` true and `epoch_ended_at` = epoch 2 `started_at` | TC-048-02 |
| FEAT-048-AC-03 | SRC-05: exactly R09 epoch 1 at R09-20261021-01 (2026-10-21 19:07:50 UTC, local 2026-10-21, 5.431965) and R10 epoch 1 at R10-20261024-01 (5.972050), both not epoch-ended | TC-048-03 |
| FEAT-048-AC-04 | `leaning_most` R09 (Oct 21–30) = (number_of_pauses, loudness_dbfs, voiced_fraction); R10 (Oct 24–30) = (number_of_pauses, articulation_rate_syl_per_s, speech_rate_syl_per_s) | TC-048-04, TC-048-05 |
| FEAT-048-AC-05 | With DS-07, `GET /api/v1/alerts?status=open` returns those arrays for R09 and R10 | TC-048-06 |
| FEAT-048-AC-06 | After a review and a snooze on the R09 alert, a full rebuild keeps id, reviews, `acknowledged`, `snoozed_until` | TC-048-08 |
| FEAT-048-AC-07 | A resident with an open epoch-1 alert who starts epoch 2 has the alert `closed` with "epoch ended" and shows `baseline_forming` until epoch 2 forms | TC-048-09 |

## Test Data Requirements

- DS-07 (SRC-05 seeded with `test_v0_1`, as-of 2026-10-30 15:00 America/Chicago); SRC-03 `Exp_scores` and `Exp_resident_outcomes` (first alarm sessions).
- Synthetic follow-on record R09-20261031-01 (copy of R09-20261030-01 with `timestamp_utc` 2026-10-31 19:00:00 and firmware "fw-1.0.1") for TC-048-02 (REPL) and TC-048-09 (API).
- Synthetic `ScoreRow` sequences built in the REPL.
- Review explanation code `poor_sleep_unusual_day`, outcome `known_cause`; snooze 24 h.
- Environment: `PIPELINE_AS_OF=2026-10-30T15:00:00-05:00` for the rebuild (not allowed in production); ingest API key from the environment file.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-048-FR-01 | FEAT-048 | TC-048-01, TC-048-03 |
| FEAT-048-FR-02 | FEAT-048 | TC-048-01, TC-048-07 |
| FEAT-048-FR-03 | FEAT-048 | TC-048-02, TC-048-09 |
| FEAT-048-FR-04 | FEAT-048 | TC-048-08 |
| FEAT-048-FR-05 | FEAT-048 | TC-048-10 |
| FEAT-048-FR-06 | FEAT-048 | TC-048-04, TC-048-05 |
| FEAT-048-FR-07 | FEAT-048 | TC-048-06 |
| FEAT-048-FR-08 | FEAT-048 | TC-048-07 |
| FEAT-048-FR-09 | FEAT-048 | TC-048-10 |
| TRD 09 CUS-011..CUS-021 | FEAT-048 | TC-048-01..TC-048-03, TC-048-07..TC-048-10 |
| TRD 09 CUS-041, §4.8 | FEAT-048 | TC-048-04, TC-048-05, TC-048-06 |
| TRD 09 AC-CUS-02, AC-CUS-03, AC-CUS-07, AC-CUS-09 | FEAT-048 | TC-048-03, TC-048-09, TC-048-06 |
| TRD 06 DB-018; TRD 07 ANL-039 | FEAT-048 | TC-048-08, TC-048-09 |
| TRD 05 API-080 | FEAT-048 | TC-048-06 |
| TRD 13 AL-01..AL-04, AN-08 | FEAT-048 | TC-048-01, TC-048-02, TC-048-08, TC-048-04 |
| TRD 19 OAS-027; TRD 14 TDV-069, VC-G10 | FEAT-048 | TC-048-06, TC-048-03 |
| TRD 11 UX-312 | FEAT-048 | TC-048-06 |
| FR-053, FR-104, FR-109, FR-110, FR-206, FR-266 | FEAT-048 | TC-048-09, TC-048-03, TC-048-10, TC-048-10, TC-048-07, TC-048-04 |
