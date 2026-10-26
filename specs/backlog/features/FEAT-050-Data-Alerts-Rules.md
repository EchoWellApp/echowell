# FEAT-050 Data alerts rules (stage 11)

| Field | Value |
|---|---|
| Epic | Analytics Engine |
| Build phase | Phase 6 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-049, FEAT-048 |
| Status | Not Started |

## Purpose

Compute the data-quality alerts for the study team on every pipeline run over the last 30 days: a baseline that has stalled, a possible other speaker, many set-aside check-ins, and a silent device. These are not health alarms — they never create an alarm or change a tally — but they tell the study team where data collection needs attention. With the test data the rules produce exactly four alerts: R08 baseline stuck at 13 of 16, R05 possible other speaker, R03 many check-ins set aside, D02 silent on Oct 12. They are listed on the Study team page under "Data problems to follow up" as "**<code>:** <detail>" with the wireframe v0.2 detail texts (SRC-21; TRD 24 D-114), and the open `baseline_stalled` and `high_set_aside` alerts make R08 and R03 "Needs attention" on the Resident list (read side, FEAT-027; OQ-31).

## Business Context

- BR-06 (silent devices and missed days), BR-04 (set-aside patterns), BR-05 (other speakers), BR-09 (stalled baselines): four rule-based kinds with exact texts.
- BR-11: data alerts never create alarms or appear in alarm counts.
- BR-15: exactly the four reference alerts of TRD 11 §4.18.8 on SRC-05.
- FRs covered (BACKLOG.md): FR-290, FR-291, FR-292, FR-293, FR-294, FR-295, FR-296, FR-300, FR-301 (FR-302, the attention flag, is read by FEAT-027 from these rows).

## Referenced TRDs

- TRD 09 CUS-043 (rules, texts, suppression, ordering), CUS-044 (exactly four on SRC-05), CUS-046 (thresholds from configuration, no rebuild), §4.9 rule table (v0.1 titles, v0.2 details) and verification.
- TRD 07 ANL-059 (stage 11 module), ANL-060 (reconciliation rules the runner applies to these outputs), §4.2 (`generate_data_alerts` signature), §4.4 (`DataAlert`), §4.7 (`OperationalConfig`), §4.13 (30-day window).
- TRD 11 §4.18.2 (how titles and details are shown on the Study team page; UX-306 to UX-309).
- TRD 23 §4.3.7 (data alert lifecycle); TRD 06 DB-036 (natural keys).
- TRD 13 Table 4.3-B DA-01..DA-11; TRD 07 AC-ANL-10 (data-alert part); TRD 09 AC-CUS-09.
- TRD 24 D-36, D-114 (v0.2 detail texts); OQ-24 (thresholds provisional), OQ-31 (which kinds mean "Needs attention").

## Scope

- `analytics/data_alerts.py::generate_data_alerts(sessions, ledger, epochs, residents, assignments, config, as_of) -> list[DataAlert]` for kinds `baseline_stalled`, `possible_other_speaker`, `high_set_aside`, `device_silent`.
- Exact title and detail strings, suppression, one alert per subject per kind, fixed output order.
- Unit tests `tests/unit/analytics/test_data_alerts.py`.

## Out of Scope

- Reconciling `data_alerts` rows across runs (insert, update `last_detected_at`, resolve; FR-296) — the runner, FEAT-053 (ANL-060, DB-036); this stage recomputes the full current set on every run so the runner can reconcile.
- `review_flagged_data_problem` alerts (review service FEAT-031; resolved by CLI FEAT-032); the pipeline never creates, modifies or resolves them (CUS-040).
- `GET /api/v1/data-alerts` (FEAT-032), the attention flag (FEAT-027) and the Study team UI (FEAT-072); the `data_alerts_updated` log line (FEAT-056, LOG-115).
- Threshold calibration (OQ-24).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-050-FR-01 | The stage shall recompute all rule-based data alerts on every run over the 30 facility-local days ending on the as-of local date (not before each resident's `enrolled_on`), with thresholds from `config.operational` (`data_alert_baseline_stalled_enabled` true, `data_alert_set_aside_fraction` 0.20, `data_alert_device_silent_days` 2; equal in both profiles). | FR-290, CUS-046, ANL-059; TRD 07 §4.13 |
| FEAT-050-FR-02 | `baseline_stalled` (when enabled): resident whose current epoch has no formed baseline and (as-of local date − current epoch start local date) + 1 ≥ `baseline_n`; title "<R> · baseline stuck at <n> of <N>" (n = usable sessions in the current epoch), detail "baseline stuck at <n> of <N>. <missed> missed and <set_aside> set aside in 30 days." (missed = missing_resident + missing_device_gap ledger days in the window). | FR-291, CUS-043 |
| FEAT-050-FR-03 | `possible_other_speaker`: resident with ≥ 1 quarantined record in the window; title "<R> · possible other speaker", detail "<q> check-ins held back as possible other voice (<Mon D>, <Mon D>)." ("1 check-in held back as possible other voice (<Mon D>)." when q = 1), dates ascending. | FR-292, CUS-043 |
| FEAT-050-FR-04 | `high_set_aside`: resident with received (non-duplicate records in the window) ≥ 10 and set_aside / received ≥ `data_alert_set_aside_fraction`; title "<R> · many check-ins set aside", detail "<s> of <received> received check-ins set aside (<kinds>)." with kinds in the fixed order noise, quality flag, too short, listing only kinds that occur; suppressed when the resident has `baseline_stalled`. | FR-293, FR-295, CUS-043 |
| FEAT-050-FR-05 | `device_silent`: a device-day is silent when the device has ≥ 1 resident assigned that day and every such resident's ledger day is missing; it is flagged when the device is shared that day (≥ 2 residents) or belongs to a run of ≥ `data_alert_device_silent_days` consecutive silent days of a single-resident device; one alert per device with title "<D> · device silent all day" (one flagged day) or "<D> · device silent on <k> days" (k ≥ 2) and detail "silent all day <Mon D>. Affected <residents>." (one flagged day) or "silent on <k> days (<Mon D>, <Mon D>, …). Affected <residents>." (residents joined ", " with " and " before the last). | FR-294, CUS-043 |
| FEAT-050-FR-06 | Each resident appears at most once per kind and each device at most once; output order: kind (baseline_stalled, possible_other_speaker, high_set_aside, device_silent), then resident or device code. | FR-295, CUS-043 |
| FEAT-050-FR-07 | Data alerts shall never create an alarm, change a tally or alarm state, or be counted in alarm counts; the stage has no access to alerts' human state. | FR-300, D-36 |
| FEAT-050-FR-08 | Each `DataAlert` shall carry `kind`, `resident_code` or `device_code` (never both), `title`, `detail` and the affected local dates (`days`), so the runner can keep `first_detected_at`, update `last_detected_at` while the rule holds and resolve the row on the first run where it no longer holds. | TRD 07 §4.4; FR-296 (via ANL-060, DB-036) |
| FEAT-050-FR-09 | With SRC-05 at as-of 2026-10-30 15:00 America/Chicago the stage shall produce exactly, in order: R08 baseline_stalled "R08 · baseline stuck at 13 of 16" / "baseline stuck at 13 of 16. 12 missed and 5 set aside in 30 days."; R05 possible_other_speaker "R05 · possible other speaker" / "2 check-ins held back as possible other voice (Oct 8, Oct 22)."; R03 high_set_aside "R03 · many check-ins set aside" / "7 of 29 received check-ins set aside (noise, quality flag, too short)."; D02 device_silent "D02 · device silent all day" / "silent all day Oct 12. Affected R02 and R03." | FR-301, CUS-044, D-114 |

## Inputs

- `AdjustedRecord`s (statuses, reasons, local dates), `LedgerDay`s, `EpochSummary`s (current epoch start, baseline formed, usable count), `ResidentInfo`s, `DeviceAssignment`s, `PipelineConfig` (incl. `operational`, `baseline_n`, `shared_device_min_residents`), `as_of`.

## Outputs

- `list[DataAlert]` in the fixed order.

## Data Flow

1. `run_pipeline` step 14 (FEAT-052): `generate_data_alerts(adjusted, ledger, epochs, residents, assignments, config, as_of)`.
2. Compute the window, per-resident counts (received, set aside with reason kinds, quarantined dates, missed) and per-device silent days from the ledger and assignments.
3. Apply the four rules, suppression and ordering; build texts.
4. The runner reconciles them into `data_alerts` (FEAT-053); stage 12 uses `device_silent` days for `silent_device_codes` (FEAT-051).

## Dependencies

Required before implementation (BACKLOG.md): FEAT-049, FEAT-048

- FEAT-049 (Day ledger): missing-day statuses and assignment resolution for device-days.
- FEAT-048 (Alert generation): epoch summaries and alert facts produced before stage 11 (ordering per ANL-006; data alerts must not alter them).

Features that build directly on this one (BACKLOG.md §4): FEAT-051, FEAT-052.

## Database Impact

None directly. The runner reconciles `data_alerts` (`kind`, `resident_id`, `device_id`, `title`, `detail`, `first_detected_at`, `last_detected_at`, `status`, `resolved_at`, `pipeline_run_id`) per DB-036 (FEAT-053); TRD 20 `data_alerts_subject_ck` requires resident-only or device-only subjects for these kinds.

## API Impact

None directly; results are served by `GET /api/v1/data-alerts` (FEAT-032).

## Frontend Impact

None.

## Analytics Impact

- Algorithms: windowed counting rules with thresholds, suppression and consecutive-day run detection; stage 11 of ANL-006.
- Calculations: inclusive day count since epoch start; set-aside fraction; consecutive silent-day runs.

## Security Requirements

None specific (pure function); alerts contain study IDs and dates only.

## Error Handling

- Residents or devices with no data produce no alert (no error).
- A device with no resident assigned on a day is not silent that day (DA-10).

## Logging Requirements

None in `analytics/` (LOG-006); the runner logs `data_alerts_updated` with counts per kind (LOG-115, FEAT-056); data alerts are not logged as errors.

## Testing Requirements

- Unit (`tests/unit/analytics/test_data_alerts.py`, marker `unit`): DA-01..DA-10 (stalled with R08 inputs; boundary 15 vs 16 inclusive days; other speaker; set aside 7 of 29; 2 of 9 no alert; suppression; shared device D02; isolated single-device misses no alert; 2 consecutive silent days one alert; unassigned device no alert); singular "1 check-in quarantined" text; three-resident "affects R01, R02 and R03" join.
- Integration (with FEAT-053): DA-11 (two runs, one open row, `last_detected_at` updated, resolved when the condition goes away).
- Validation and API (FEAT-059, FEAT-060): AC-ANL-10 data-alert list, AC-CUS-09, TDV-068.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-050-AC-01 | R08 inputs (forming, 30 inclusive days, baseline_n 16) give one baseline_stalled alert "R08 · baseline stuck at 13 of 16" / "baseline stuck at 13 of 16. 12 missed and 5 set aside in 30 days."; an epoch started 14 days before as-of (15 inclusive days) gives none and 15 days before (16) gives one. | DA-01, DA-02, FR-291 |
| FEAT-050-AC-02 | Two quarantined sessions on Oct 8 and Oct 22 give "R05 · possible other speaker" / "2 check-ins held back as possible other voice (Oct 8, Oct 22)."; one session gives "1 check-in held back as possible other voice (<Mon D>).". | DA-03, CUS-043 |
| FEAT-050-AC-03 | 7 set aside of 29 received with reasons noise, quality flag, too short gives "R03 · many check-ins set aside" / "7 of 29 received check-ins set aside (noise, quality flag, too short)."; 2 of 9 gives no alert; a resident qualifying for both baseline_stalled and high_set_aside gets only baseline_stalled. | DA-04..DA-06, FR-293, FR-295 |
| FEAT-050-AC-04 | Shared device D02 with no record from R02 or R03 on Oct 12 gives "D02 · device silent all day" / "silent all day Oct 12. Affected R02 and R03."; a single-resident device with non-consecutive silent days gives none, with 2 consecutive silent days one ("<D> · device silent on 2 days" / "silent on 2 days (<Mon D>, <Mon D>). Affected <R>."); a device with no assigned resident gives none. | DA-07..DA-10, FR-294 |
| FEAT-050-AC-05 | On SRC-05 the output is exactly the four alerts of FEAT-050-FR-09 in that order and no other. Verified by: Validation and API (Validation and API (FEAT-059, FEAT-060): AC-ANL-10 data-alert list, AC-CUS-09, TDV-068). | CUS-044, FR-301, AC-ANL-10 |
| FEAT-050-AC-06 | Changing `data_alert_set_aside_fraction` in the config changes the high_set_aside result without changing `config_hash()`, and no `DataAlert` input or output touches tallies or alarm states. Verified by: Unit (`tests/unit/analytics/test_data_alerts.py`; DA-01, DA-10). | CUS-046, D-56, FR-300 |

## Definition of Done

- All FEAT-050 acceptance criteria pass.
- `generate_data_alerts` implemented with the binding signature; DA-01..DA-10 pass (TST-020); test file exists (TST-011).
- DA-11 passes with FEAT-053; FEAT-050-AC-05 passes in the validation suite; TDV-068 passes in FEAT-060.
- The batch report lists the implemented requirement IDs (AGT-022); the TRD differences noted under Implementation Notes were resolved in PR #2 and need no report.

## Implementation Notes

- The minimum of 10 received records for `high_set_aside` is a fixed rule constant, not a config key (TRD 09 §4.9, TRD 20 §4.11); define it once in `data_alerts.py`.
- Map reason strings to kinds: "noise above limit" → noise, "quality flag poor" → quality flag, "speech too short" → too short; count set-aside sessions, list kinds that occur in the fixed order.
- Date format "<Mon D>" uses English month abbreviations without leading zero ("Oct 8").
- R08 set-aside 5 of 18 (0.278) is suppressed by baseline_stalled; D08's 12 silent days are never consecutive, so no device alert (TRD 09 §4.9 verification).
- TRD 09 §4.9 defines the multi-day title "<D> · device silent on <k> days" next to "<D> · device silent all day"; TRD 02 FR-294 and TRD 11 §4.18.2 now give both (aligned in the PR #2 consistency fixes). The multi-day case does not occur in SRC-05.
- Thresholds are provisional (OQ-24); never hard-code them in the rule bodies (CUS-046).
