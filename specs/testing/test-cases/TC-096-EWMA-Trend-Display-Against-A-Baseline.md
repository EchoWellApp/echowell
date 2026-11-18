# EWMA trend display against a baseline band

## Feature Description

Status: Not Started — these test cases are written from the feature file and run only once the feature is built (BACKLOG.md §10).

FEAT-096 would provide the "EWMA trend shown against baseline band" mentioned by the final box of the SRC-02 processing flowchart, if the team decides it is wanted (gate OQ-18). The TRDs fix only its boundaries: an additional output field on `ScoreRow`, computed after scoring (after `run_cusum`) in a pure function with every parameter from `PipelineConfig`, display-only, never altering `cusum_tally`, `alarm_state`, alerts, data alerts or any `test_v0_1` expected value. Whether to build it, its input, smoothing weight, initial value, band definition, display location and wording are open; persistence (a new nullable `scores` column) and an API field need TRD 20 / TRD 19 changes decided with OQ-18. Until then the MVP shows only the change score (CUSUM) chart, and FEAT-096-AC-01 is the standing check that no EWMA code exists. If OQ-18 is answered "no", only TC-096-01..TC-096-03 apply.

Cases run on the checked-out repository and the local Compose stack seeded with `test_v0_1`.

## Preconditions

- Repository at the commit under test; Python 3.12 with backend requirements; `frontend` dependencies installed for component tests.
- Local Compose stack seeded with `test_v0_1` (R01–R10) and the DS-10 loader; clinician login with the local password from `.env`.
- For TC-096-04..TC-096-11: OQ-18 answered "yes" in TRD 24 with input, λ, initial value, band definition and a wireframe; TRD 07, 09, 11, 19, 20 updated.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-096-01 | Before OQ-18: no EWMA code in `analytics`, `backend`, `frontend/app`, `frontend/components` | High | Documentation |
| TC-096-02 | Before OQ-18: no EWMA field in the API contract or the schema | High | Negative |
| TC-096-03 | Before OQ-18: Voice trends shows only the change score chart | Medium | UI |
| TC-096-04 | With the EWMA field, `cusum_tally`, `alarm_state` and alerts are identical for SRC-05 | High | Analytics |
| TC-096-05 | Property test: random inputs give identical `cusum_tally` and `alarm_state` with and without EWMA | High | Analytics |
| TC-096-06 | R01–R10 validation passes unchanged | High | Analytics |
| TC-096-07 | Every EWMA parameter is a `config_parameters` key validated by `PipelineConfig.from_mapping` | High | Database |
| TC-096-08 | EWMA computation is pure and deterministic | Medium | Analytics |
| TC-096-09 | Residents without a frozen baseline have no EWMA values (empty state) | Medium | UI |
| TC-096-10 | Display follows the wording and accessibility rules | High | Accessibility |
| TC-096-11 | EWMA never raises an alarm or data alert | High | Negative |
| TC-096-12 | API field and schema column are added only with the regenerated contract | Medium | API |

### TC-096-01 Before OQ-18: no EWMA code in `analytics`, `backend`, `frontend/app`, `frontend/components`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -rni "ewma" analytics backend frontend/app frontend/components; echo "exit=$?"` | No match; `exit=1` |
| 2 | Record the result in the release evidence | Command, date and output recorded |

Note: on 15 Nov 2026 the command prints `backend/core/common_passwords.txt:1489:newman` (the letters "ewma" inside a word of the common-password deny list, SEC-012), so it does not return "no match" literally; the tester records the hit as a finding for the algorithm lead, as the final audit did for the AGT-004 "llamas" hit (`FINAL_IMPLEMENTATION_AUDIT.md` §2.2). No EWMA implementation exists.

### TC-096-02 Before OQ-18: no EWMA field in the API contract or the schema

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -ci "ewma" docs/api_reference/openapi.json frontend/lib/api-types.ts` | `0` for both files |
| 2 | `grep -ni "ewma" database/schema.sql; echo "exit=$?"` | No output; `exit=1` (no `scores` EWMA column) |
| 3 | `docker compose exec db psql -U echowell -d echowell -c "SELECT key FROM config_parameters WHERE key ILIKE '%ewma%';"` | 0 rows |

### TC-096-03 Before OQ-18: Voice trends shows only the change score chart

| Step | Action | Expected Result |
|---|---|---|
| 1 | Sign in as `clinician@example.com`; open `/residents/R09/trends` | Section "Voice trends"; heading "Change score" with "Alarm line: 5"; heading "The 7 voice measurements behind the score" |
| 2 | Look for any other trend chart or a band chart labelled EWMA or "trend" | None present |
| 3 | Open the disclosure "Show change score as a table" | Text table of the change score only |

### TC-096-04 With the EWMA field, `cusum_tally`, `alarm_state` and alerts are identical for SRC-05

| Step | Action | Expected Result |
|---|---|---|
| 1 | On the commit before the feature: seed `test_v0_1`, run `python -m backend.cli run-pipeline --scope all`; record `SELECT md5(string_agg(processed_session_id::text \|\| ':' \|\| cusum_tally::text \|\| ':' \|\| alarm_state::text, ',' ORDER BY processed_session_id)) FROM scores;` (map to session IDs if IDs differ) and `SELECT md5(string_agg(resident_id::text \|\| local_date::text \|\| cusum_value::text \|\| status::text, ',' ORDER BY resident_id, local_date)) FROM alerts;` | Hashes A and B recorded |
| 2 | On the feature commit: reset, seed, run the same | Same hashes A and B |
| 3 | Compare the R09 and R10 alarm dates | R09 alarm since 2026-10-21 unchanged; R10 unchanged |

### TC-096-05 Property test: random inputs give identical `cusum_tally` and `alarm_state` with and without EWMA

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/unit/analytics -q -k "deterministic_and_order_independent or ewma"` | All pass, including the property test extending TST-022 |
| 2 | Read the property test | Generates random composite z sequences, compares `cusum_tally` and `alarm_state` with the EWMA field present and absent |

### TC-096-06 R01–R10 validation passes unchanged

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation -q` | All pass, 0 failed; Exp_scores `cusum_tally` and `alarm_state` comparisons unchanged |
| 2 | `git diff <feature base>..<feature head> -- tests/validation tests/fixtures/answer_key` | No change to expected values |

### TC-096-07 Every EWMA parameter is a `config_parameters` key validated by `PipelineConfig.from_mapping`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT profile, key, value FROM config_parameters WHERE key IN (<OQ-18 parameter keys>) ORDER BY profile, key;` | Each decided parameter (e.g. smoothing weight, initial value, band definition) present in both profiles |
| 2 | `grep -nE "lambda\|0\.[0-9]+" <EWMA module>` | No hard-coded parameter constant |
| 3 | `set-config --profile production --key <λ key> --value '<out-of-range value>' --reason "TC-096-07"; echo "exit=$?"` | `exit=2`; `ConfigError` names the key; no change |
| 4 | Valid `set-config` of an EWMA key, then an ingest-triggered run without `rebuild` | Run fails with `config_changed_requires_rebuild` (algorithm key changes `config_hash()`) |

### TC-096-08 EWMA computation is pure and deterministic

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run the EWMA unit tests twice with `-p randomly` seeds 1 and 2 | Same results both times |
| 2 | Inspect the EWMA module | No database, HTTP, clock, random or logging use (`analytics/` does not log) |

### TC-096-09 Residents without a frozen baseline have no EWMA values (empty state)

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R08/trends` (baseline forming) | Change score area shows "No change score yet. Scoring starts after the baseline is complete (<n> of <N> usable check-ins so far)."; the EWMA display follows the same empty state; no EWMA points |
| 2 | `SELECT count(*) FROM scores s JOIN residents r ON r.id = s.resident_id WHERE r.resident_code = 'R08';` | `0` (no scored sessions, so no EWMA values) |

### TC-096-10 Display follows the wording and accessibility rules

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read the EWMA display text on the decided page | Plain language from the OQ-18 wording; the page keeps the rule that a change is "a prompt to check in, not a diagnosis"; no clinical claim |
| 2 | Check status cues | Not conveyed by colour alone (marker or text accompanies colour) |
| 3 | Check the text alternative | Accessible name summarising the chart and a data table alternative |
| 4 | Axe scan of the route (TST-110 list) in light and dark schemes | 0 serious or critical violations |
| 5 | `git grep -niE "diagnos(e\|is)\|severity" -- frontend/app frontend/components` | Only approved negative wording in tests (as recorded by the final audit) |

### TC-096-11 EWMA never raises an alarm or data alert

| Step | Action | Expected Result |
|---|---|---|
| 1 | Construct a synthetic resident whose EWMA leaves its band while CUSUM stays below h | No `alerts` row and no `data_alerts` row for that resident |
| 2 | `grep -rn "ewma" analytics/alert_generator.py analytics/data_alerts.py analytics/cusum_engine.py; echo "exit=$?"` | No output; `exit=1` |

### TC-096-12 API field and schema column are added only with the regenerated contract

| Step | Action | Expected Result |
|---|---|---|
| 1 | After OQ-18: `python -m backend.cli export-openapi \| diff - docs/api_reference/openapi.json` | No difference (contract regenerated, D-51) |
| 2 | `GET /api/v1/scores?resident_code=R09` | 200; each score item carries the decided EWMA field; `cusum_tally` and `alarm_state` unchanged |
| 3 | New Alembic migration | Adds one nullable `scores` column only (expand-only, DEP-061); `alembic check` reports no difference |
| 4 | CI job `openapi-contract` | `success` |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | Before OQ-18: `GET /api/v1/scores?resident_code=R09` | 200; no EWMA field in any item |
| 2 | After OQ-18: same call | 200; decided EWMA field present; other fields unchanged |
| 3 | `GET /api/v1/scores?resident_code=R08` | 200; empty list (baseline forming) |
| 4 | `GET /api/v1/scores` without token | 401 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | Before OQ-18: no EWMA column or config key (TC-096-02) | None |
| 2 | Score and alert hashes before/after the feature (TC-096-04) | Identical |
| 3 | EWMA config keys in both profiles (TC-096-07) | Present after OQ-18 |
| 4 | R08 scores count (TC-096-09) | 0 |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | EWMA grep before OQ-18 (TC-096-01) | No EWMA implementation (deny-list word hit recorded) |
| 2 | Out-of-range EWMA parameter via `set-config` (TC-096-07) | Exit 2, no change |
| 3 | Run after an EWMA key change without `rebuild` (TC-096-07) | `config_changed_requires_rebuild` |
| 4 | EWMA outside band with CUSUM below h (TC-096-11) | No alert, no data alert |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-096-AC-01 | Before OQ-18, `grep -rni "ewma" analytics backend frontend/app frontend/components` returns no match | TC-096-01, TC-096-02, TC-096-03 |
| FEAT-096-AC-02 | Output with and without the EWMA field has identical `cusum_tally`, `alarm_state` and alerts for SRC-05 and random inputs | TC-096-04, TC-096-05, TC-096-11 |
| FEAT-096-AC-03 | `pytest tests/validation -q` passes unchanged | TC-096-06 |
| FEAT-096-AC-04 | Every EWMA parameter is a `config_parameters` key validated by `PipelineConfig.from_mapping` | TC-096-07, TC-096-08 |

## Test Data Requirements

- `test_v0_1` seed (SRC-05 records, R01–R10; R08 baseline forming, R09 and R10 alarms).
- Random property-test inputs (generated by the test).
- One synthetic resident whose EWMA leaves the band without a CUSUM alarm (TC-096-11).
- OQ-18 parameter keys and values from TRD 24 once decided.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| ANL-056 | FEAT-096 | TC-096-04, TC-096-12 |
| CUS-036 | FEAT-096 | TC-096-04, TC-096-05, TC-096-11 |
| AGT-020, AGT-021, ARC-041, ANL-029 | FEAT-096 | TC-096-07, TC-096-08 |
| OQ-18, AGT-009 | FEAT-096 | TC-096-07, TC-096-10 |
| AGT-008, TST-080 | FEAT-096 | TC-096-06 |
| AGT-018, UX-225 | FEAT-096 | TC-096-10 |
| TRD 25 §4.6 Phase 2 Pitfalls, X-15, D-30 | FEAT-096 | TC-096-01, TC-096-02, TC-096-03 |
| UX-089, D-51, DEP-061 | FEAT-096 | TC-096-09, TC-096-12 |
| FEAT-096-FR-01..FEAT-096-FR-07 | FEAT-096 | TC-096-01..TC-096-12 |
