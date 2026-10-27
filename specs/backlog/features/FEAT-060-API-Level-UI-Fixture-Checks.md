# FEAT-060 API-level UI fixture checks (DS-07: overview, devices, alerts, data alerts, analytics)

| Field | Value |
|---|---|
| Epic | Testing & Validation |
| Build phase | Phase 7 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-059, FEAT-027, FEAT-029, FEAT-030, FEAT-032, FEAT-051, FEAT-054 |
| Status | Not Started |

## Purpose

Before any page is built, prove that the API returns exactly the values the wireframe v0.2 pages (SRC-21: Resident list, Resident chart, Study team, New admissions) must render for the reference data (TRD 11 §4.13, §4.17.5, §4.18.8). With dataset DS-07 (SRC-05 ingested under `test_v0_1`, roster loaded, as-of set by an explicit pipeline run without a clock override) and DS-10 loaded, integration tests assert the Resident list rows, default order and display-status summary (with the attention flag and `alarm_reviewed`), the chart values (incl. `checkins_started`, `restart_cause`, the 30-day `window`), the device values (incl. `uploaded_on_as_of_date`), the alarm facts, exactly four data alerts with the v0.2 details, the "Leaning most" features, and every Study team figure of TRD 14 Table 4.9-E. These checks also prove that the API values derive from pipeline output, which is the source of the frontend fixtures.

## Business Context

- BR-12, BR-13 (resident list and chart show the right status and counts), BR-11 (alarm review), BR-15 (pages match the answer key), SRC-21 (supersedes SRC-09, SRC-18, SRC-19; TRD 24 D-108).
- NFR-128: the Resident list, the Resident chart and the Study team page must not contradict each other for the same as-of.
- FRs covered (BACKLOG.md): FR-137, FR-263, FR-301, FR-302, FR-323.

## Referenced TRDs

- TRD 11 §4.13 (resident list and chart), §4.17.5, §4.18.8 (Study team) — the expected rendering these API values feed.
- TRD 14 TDV-061 (DS-07 as-of without clock override; in-process tests freeze the clock), TDV-062..TDV-066 (overview rows, order, 30-day semantics, last check-in, devices panel and R09 detail values), TDV-067 (alarm cards), TDV-068 (exactly 4 data alerts and listed non-alerts), TDV-069 (Leaning most), TDV-074 (analytics blocks), TDV-075 (recomputed from DS-02), TDV-076 (after a review), §4.9 Tables 4.9-B..4.9-E, §4.9.1, §4.9.2.
- TRD 02 AC-FR-04, AC-FR-12, AC-FR-13, FR-137, FR-263, FR-301, FR-323.
- TRD 19 OAS-021, OAS-022, OAS-024, OAS-027, OAS-028; E-08, E-09, E-13, E-17, E-18, E-30.
- TRD 05 API-069, API-080, API-086, API-087, API-133; TRD 03 NFR-128.

## Scope

- `tests/integration/api/test_ui_fixture_ds07.py` (marker `integration`) building DS-07: migrated database, `seed test_v0_1` (roster, users, SRC-05, explicit-as-of run) and the DS-10 loader.
- Assertions for `GET /api/v1/residents` (default and each sort), `GET /api/v1/residents/R09`, `GET /api/v1/residents/R09/checkins`, `GET /api/v1/devices`, `GET /api/v1/alerts?status=open`, `GET /api/v1/data-alerts?status=open`, `GET /api/v1/analytics` (researcher).
- Recomputation of every Table 4.9-E figure from DS-02 (Annotated_sessions, Exp_status_counts, Exp_resident_outcomes) inside `tests/validation/` and comparison with the API (TDV-075).
- After-review check (TDV-076) on a separate database copy.

## Out of Scope

- The endpoints themselves (FEAT-027, FEAT-028, FEAT-029, FEAT-030, FEAT-032, FEAT-035/FEAT-051).
- Rendering checks of pages and components (FEAT-065..FEAT-072, TRD 04 FE-181..FE-195) and E2E (FEAT-076).
- Capturing the frontend MSW fixtures `frontend/tests/fixtures/ds07/` (`npm run fixtures:capture`, FEAT-062), which must equal what these tests assert.

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-060-FR-01 | DS-07 shall be built without any clock override in the running services: after loading DS-01, an admin `POST /api/v1/pipeline/run` with `as_of` 2026-10-30T15:00:00-05:00 and profile `test_v0_1` makes every read endpoint report `meta.as_of` 2026-10-30T20:00:00Z; `DATA_SOURCE_LABEL` is "pipeline test data v0.1"; in-process `TestClient` tests may freeze the clock with `time-machine` instead. | TDV-061, API-069 |
| FEAT-060-FR-02 | `GET /api/v1/residents` (default sort) shall return the rows in the order R09, R10, R03, R08, R01, R02, R04, R05, R06, R07 (TRD 11 §4.13.1, TRD 24 D-109) with the Table 4.9-B values (device, `status`, last check-in, used · set aside · quarantined · missed), `needs_attention` true only for R03 [high_set_aside] and R08 [baseline_stalled], `alarm_reviewed` false for R09 and R10 and null otherwise, R07 `restart_cause` device, and `summary` changed 2 / needs_attention 2 / learning 0 / usual 6. | TDV-062, TDV-063, FR-137, FR-302, AC-FR-04, OAS-021, D-114 |
| FEAT-060-FR-03 | `sort=resident_id` shall return R01..R10 and `sort=last_checkin` R02, R07, R05, R10, R06, R08, R09, R03, R04, R01. | TRD 11 §4.13.2; TDV-063 |
| FEAT-060-FR-04 | The 30-day counts shall cover the as-of local date and the 29 preceding local dates with missed = missing_resident + missing_device_gap and duplicates excluded (R04 used 30); last check-in shall be the latest non-duplicate record of any status. | TDV-064, TDV-065 |
| FEAT-060-FR-05 | `GET /api/v1/devices` shall return 10 devices with D02 shared by R02, R03, last upload 2026-10-30T19:55:23Z, `silent_days_last_30` and `device_gap_days_last_30` ["2026-10-12"]; D07B replaces D07 in use since 2026-10-13; D07 inactive with `in_use_until` 2026-10-12; firmware fw-1.0.0; `uploaded_on_as_of_date` true for the nine active devices and false for D07. | TDV-066, API-086, TRD 19 E-17, D-114 |
| FEAT-060-FR-06 | `GET /api/v1/residents/R09` and its check-ins shall return status `alarm_on`, `alarm_since` 2026-10-21, baseline frozen after R09-20261016-01 (first 2026-10-01, frozen 2026-10-16), `watching_since` 2026-10-17 and the events alarm_on 2026-10-21 ("tally crossed 5.0"), watching_started 2026-10-17, baseline_complete 2026-10-16 ("16 of 16") and, oldest, checkins_started 2026-10-01 (`device_code` D09), with `needs_attention` false, `alarm_reviewed` false and `window` 2026-10-01..2026-10-30 (30 days); `GET /api/v1/residents/R07/checkins` ends with checkins_started 2026-10-01 `device_code` D07. | TDV-066, TRD 19 E-09, E-10, D-113, D-114 |
| FEAT-060-FR-07 | `GET /api/v1/alerts?status=open` shall return R09 (session R09-20261021-01, local_date 2026-10-21, `open_days` 9, `current_tally` 26.830256 ±1e-6) and R10 (R10-20261024-01, 2026-10-24, 6, 13.418183 ±1e-6), both `open` and not reviewed. | TDV-067, FR-263, OAS-027 |
| FEAT-060-FR-08 | `GET /api/v1/data-alerts?status=open` shall return exactly the four rows of Table 4.9-D in API kind order (R08 baseline_stalled "R08 · baseline stuck at 13 of 16" / "baseline stuck at 13 of 16. 12 missed and 5 set aside in 30 days."; R05 possible_other_speaker "R05 · possible other speaker" / "2 check-ins held back as possible other voice (Oct 8, Oct 22)."; R03 high_set_aside "R03 · many check-ins set aside" / "7 of 29 received check-ins set aside (noise, quality flag, too short)."; D02 device_silent "D02 · device silent all day" / "silent all day Oct 12. Affected R02 and R03."; v0.2 details, D-114; the Study team page displays them as R08, R03, R05, D02) and none of the listed non-alerts (no R08 high_set_aside, no D08 or D07 device_silent, no R07 baseline_stalled). | TDV-068, FR-301, AC-FR-12 |
| FEAT-060-FR-09 | `leaning_most` shall be [number_of_pauses, loudness_dbfs, voiced_fraction] for R09 and [number_of_pauses, articulation_rate_syl_per_s, speech_rate_syl_per_s] for R10. | TDV-069, OAS-027 |
| FEAT-060-FR-10 | `GET /api/v1/analytics` as researcher shall return `kpis`, `daily_series` (30 rows equal to the TRD 14 §4.9.2 per-day list), `funnel`, `by_resident` and `alarm_timing` (R09 Sudden step 2026-10-21 → 2026-10-21, 0 days; R10 Slow drift 2026-10-17 → 2026-10-24, 7 days; eight `correct_no_alarm`) equal to Table 4.9-E. | TDV-074, FR-323, AC-FR-13, OAS-028 |
| FEAT-060-FR-11 | Every Table 4.9-E figure shall also be recomputed from DS-02 by the validation harness and compared with the API response. | TDV-075 |
| FEAT-060-FR-12 | After a review is saved on R09, the R09 alert shall be `acknowledged` (reviewed), R10 still `open`, `GET /alerts?status=open` `total` 1, `kpis.alarms_raised.not_reviewed_count` 1, R09's `alarm_reviewed` true with `status` still `alarm_on` (summary unchanged), and all tallies unchanged. | TDV-076, TST-056, D-114 |
| FEAT-060-FR-13 | Resident `last_30_days` sums, the attention flag, data-alert details and analytics counts shall be consistent for the same as-of (e.g. R08 13/5/0/12 on the resident row, analytics by_resident and the baseline_stalled detail; R03 7 set aside on its row and in its high_set_aside detail). | NFR-128, FR-302 |

## Inputs

- DS-07: DS-01 + roster `database/seeds/test_v0_1/` via `seed test_v0_1` (FEAT-055) with the explicit as-of run; DS-10 via the FEAT-057 loader.
- DS-02 workbook for TDV-075 recomputation.
- Seeded users (admin, clinician, researcher) with test passwords from env.

## Outputs

- Integration tests that pass only when the API serves the DS-07 values; their assertions are the specification that `frontend/tests/fixtures/ds07/` must match.

## Data Flow

Empty DB → migrations → `seed test_v0_1` (roster, users, SRC-05 ingest, run at as-of 2026-10-30T20:00:00Z) → DS-10 loader → test client logs in per role → GET endpoints → assertions against Tables 4.9-B..4.9-E and DS-02 recomputation.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-059, FEAT-027, FEAT-029, FEAT-030, FEAT-032, FEAT-051, FEAT-054

- FEAT-059: the R01–R10 suite must pass first (same pipeline output).
- FEAT-027 (`GET /residents`), FEAT-029 (`GET /devices`), FEAT-030 (`GET /alerts`), FEAT-032 (`GET /data-alerts`), FEAT-051 (analytics blocks): endpoints under test.
- FEAT-054: ingest-triggered runs used while building DS-07.

Features that build directly on this one (BACKLOG.md §4): FEAT-062.

## Database Impact

None beyond the disposable test database populated through the seed and loader (no direct SQL writes).

## API Impact

Endpoints consumed: E-02, E-08, E-09, E-10, E-13, E-14 (after-review check), E-17, E-18, E-20, E-21, E-30. None exposed.

## Frontend Impact

None in code. These assertions define the data that FEAT-062's captured fixtures and the page tests of FEAT-065..FEAT-072 rely on.

## Analytics Impact

None; values come from the pipeline output persisted by FEAT-053.

## Security Requirements

- `GET /api/v1/analytics` is called as researcher; a clinician call returns 403 (FR-310) and is asserted as a negative case.
- Test credentials come from SEED_* environment variables and are never logged (DB-057).

## Error Handling

- A mismatch fails the test with the endpoint, field, expected and actual values.
- If the explicit-as-of run does not reach `succeeded` within 60 s the fixture setup fails (TDV-031 pattern).

## Logging Requirements

None beyond the standard request logs and the audit rows of login and the after-review save (TST-053).

## Testing Requirements

- Integration (`tests/integration/api/test_ui_fixture_ds07.py`, marker `integration`): TDV-062..TDV-069, TDV-074, TDV-076; every response validated against the OpenAPI schema (TST-061).
- Validation (`tests/validation/test_ui_fixture_recompute.py`, marker `validation`): TDV-075.
- Also exercised by staging smoke tests DEP-080 (d)–(g) after deployment (FEAT-086 and later).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-060-AC-01 | `GET /api/v1/residents` on DS-07 returns `summary` changed 2 / needs_attention 2 / learning 0 / usual 6 and the default order R09, R10, R03, R08, R01, R02, R04, R05, R06, R07 with the Table 4.9-B values and the FEAT-060-FR-02 attention flags. Verified by: Integration (`tests/integration/api/test_ui_fixture_ds07.py`; TST-061). | AC-FR-04; AC-TDV-07; OAS-021 |
| FEAT-060-AC-02 | `GET /api/v1/alerts?status=open` returns exactly R09 (open_days 9, current_tally 26.830256 ±1e-6) and R10 (open_days 6, 13.418183 ±1e-6) with the TDV-069 `leaning_most` lists. Verified by: Integration (`tests/integration/api/test_ui_fixture_ds07.py`). | TDV-067; TDV-069; OAS-027 |
| FEAT-060-AC-03 | `GET /api/v1/data-alerts?status=open` returns exactly the four Table 4.9-D rows (kind, code, title, v0.2 detail exact) and nothing else. Verified by: Integration (`tests/integration/api/test_ui_fixture_ds07.py`; TST-061). | TDV-068; AC-FR-12; AC-TDV-10 |
| FEAT-060-AC-04 | `GET /api/v1/analytics` as researcher returns 281/300/94, 267/300/89, 9 of 10, 2 alarms, funnel 300/281/269/267 with 5/5/3, by-resident R08 43, R03 73, R02 80, R05 93, others 100, and alarm timing R09 0 days, R10 7 days. Verified by: Integration (`tests/integration/api/test_ui_fixture_ds07.py`). | AC-FR-13; AC-TDV-11; TDV-074 |
| FEAT-060-AC-05 | Every Table 4.9-E figure recomputed from DS-02 equals the API value. Verified by: Validation (`tests/validation/test_ui_fixture_recompute.py`). | TDV-075 |
| FEAT-060-AC-06 | `GET /api/v1/devices` returns D02 with `device_gap_days_last_30` ["2026-10-12"] and `uploaded_on_as_of_date` true, and D07 with `in_use_until` "2026-10-12", `replaced_by_device_code` "D07B" and `uploaded_on_as_of_date` false; every resident's check-in log ends with `checkins_started` on 2026-10-01 (R07 on D07). Verified by: Integration (`tests/integration/api/test_ui_fixture_ds07.py`; TST-061). | TDV-066 |
| FEAT-060-AC-07 | After a clinician review of R09, `GET /alerts?status=open` has `total` 1 and R09's `current_tally` is still 26.830256. | TDV-076; TST-056 |

## Definition of Done

- All FEAT-060 acceptance criteria pass; `pytest tests/integration -q -k ui_fixture` and `pytest tests/validation -q` green.
- The Phase 7 checkpoint PR of Block 3 passes `pytest tests/validation -q`, after which Phase 8 may start (AGT-023).
- Batch report lists IDs (AGT-022).

## Implementation Notes

- Build DS-07 with the same commands CI uses (`seed test_v0_1` then the DS-10 loader, TRD 13 §8 notes) so the backend fixture equals the E2E database.
- The default order follows TRD 24 D-109 (Changed by alarm date, then Needs attention, Learning, Usual, each by natural code), replacing the v0.1 contract §8 / D-17 rule that TRD 14 TDV-063 explained; TDV-063 and Tables 4.9-B and 4.9-D are owned by TRD 14 and must carry the same values (R09, R10, R03, R08, R01, R02, R04, R05, R06, R07; v0.2 data-alert details).
- Run the after-review check (TDV-076) on its own database or last, so read-only assertions see the pristine seed (same idea as D-73 for E2E).
- Compare floats with `abs(a − b) ≤ 1e-6`; strings exactly.
