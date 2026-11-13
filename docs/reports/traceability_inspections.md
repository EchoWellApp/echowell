# Traceability inspections

Document: docs/reports/traceability_inspections.md · Date: 8 November 2026 · Audited commit: `23e558b` · Checkpoint 9 (FEAT-091)

Inspection evidence for requirements in TRDs 02, 04, 05 and 07–12 that no automated test references by `req("ID")` or `// req: ID` (TRD 13 TST-013, TRD 03 NFR-111). `tests/trace_report.py` reads the IDs in this file. Requirements that FAILED inspection are deliberately not listed here, so the trace report still shows them; they are in `TRD_Implementation_Audit.md` §3. Status PENDING BLOCK 4 rows have their repo-side evidence and are re-checked in Block 4.

| ID | TRD | Priority | Status | Evidence | Note |
|---|---|---|---|---|---|
| FR-001 | 02 | Must | PASS | tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed; tests/integration/api/test_sessions.py::test_only_an_ingest_key_may_post | 201 for ingest:write key; bearer 401, pipeline key 403 |
| FR-002 | 02 | Must | PASS | tests/integration/api/test_ingest.py::test_record_errors_do_not_fail_the_batch; backend/api/ingest.py:66 | JSON {records:[...]} accepted, source api_batch |
| FR-003 | 02 | Must | PASS | tests/integration/api/test_ingest.py::test_src05_upload; tests/unit/backend/services/test_validation.py::test_csv_header_errors; tests/integration/api/test_ingest.py::test_legacy_file_is_refused | 30-field header any order (reversed) accepted; others CSV_HEADER_MISMATCH |
| FR-004 | 02 | Must | PASS | tests/integration/api/test_ingest.py::test_batch_detail_and_roles; tests/integration/api/test_ingest.py::test_record_errors_do_not_fail_the_batch | admin JWT and ingest key accepted; clinician 403 |
| FR-005 | 02 | Must | PASS | tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed; tests/integration/db/test_raw_store.py::test_same_session_id_twice_gets_increasing_arrival_seq; tests/integration/api/test_ingest.py::test_src05_upload | payload stored as received, repeats get new rows/arrival_seq |
| FR-006 | 02 | Must | PASS | tests/integration/test_schema_behaviour.py::test_ac_pgs_01_raw_sessions_update_fails_for_app; ::test_ac_pgs_02_raw_sessions_delete_and_truncate_fail_for_app; tests/unit/backend/repositories/test_raw_session_repository.py::test_repository_has_no_update_or_delete | UPDATE/DELETE/TRUNCATE refused for app and owner; repository has no update/delete |
| FR-007 | 02 | Must | PASS | tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed; tests/integration/api/test_sessions.py::test_failed_run_answers_pending | 201 with raw_session_id, arrival_seq, status; pending when run fails, next run processes |
| FR-008 | 02 | Must | PASS | tests/integration/api/test_sessions.py::test_repeat_session_id_is_a_duplicate | 200 with status duplicate |
| FR-009 | 02 | Must | PASS | tests/integration/api/test_ingest.py::test_src05_upload | 202 with ingest_batch_id, accepted, rejected, duplicates |
| FR-011 | 02 | Must | PASS | tests/integration/api/test_ingest.py::test_record_errors_do_not_fail_the_batch; tests/integration/api/test_ingest.py::test_src05_upload | per-record reject; stored arrival order equals file order |
| FR-012 | 02 | Must | PASS | tests/unit/backend/services/test_validation.py::test_name_mapping; tests/integration/api/test_ingest.py::test_mapped_header_is_accepted | feature_name_map in config_parameters; renamed header accepted without code change |
| FR-013 | 02 | Must | PASS | tests/integration/api/test_sessions.py::test_extra_field_and_audio_are_refused; tests/integration/api/test_ingest.py::test_answer_key_columns_are_refused | extra field -> extra_forbidden 422; nothing stored |
| FR-014 | 02 | Must | PASS | tests/integration/api/test_rate_limits.py::test_ingest_limit_is_per_api_key | 600/minute default asserted; 429 per key on both ingest routes |
| FR-020 | 02 | Must | PASS | tests/unit/backend/services/test_validation.py::test_schema_versions; tests/integration/api/test_sessions.py::test_version_and_timestamp_problems | 0.2 -> UNSUPPORTED_SCHEMA_VERSION |
| FR-021 | 02 | Must | PASS | tests/unit/backend/services/test_validation.py::test_a_missing_field_is_reported; backend/services/validation.py:36 | missing field rejected; phrase_id in required set |
| FR-022 | 02 | Must | PASS | tests/unit/backend/services/test_validation.py::test_timestamp_formats; tests/integration/api/test_sessions.py::test_version_and_timestamp_problems | ISO/fractional/offset/invalid dates rejected invalid_format |
| FR-023 | 02 | Must | PASS | tests/unit/backend/services/test_validation.py::test_json_numbers_and_csv_cells; tests/unit/backend/services/test_validation.py::test_csv_whole_numbers; tests/unit/backend/services/test_validation.py::test_reject_rules | NaN/inf non_finite; pauses -1 out_of_range, 1.5 not_integer |
| FR-024 | 02 | Must | PASS | tests/unit/backend/services/test_validation.py::test_reject_rules | 'OK' -> invalid_enum; integration 'bad' rejected |
| FR-025 | 02 | Must | PASS | tests/unit/backend/services/test_validation.py::test_roster_checks_and_request_codes; tests/integration/api/test_sessions.py::test_unknown_resident_is_rejected_and_stored | UNKNOWN_RESIDENT / UNKNOWN_DEVICE |
| FR-026 | 02 | Must | PASS | tests/integration/api/test_sessions.py::test_withdrawn_resident | 422 RESIDENT_WITHDRAWN detail 'resident withdrawn' |
| FR-029 | 02 | Must | PASS | tests/unit/analytics/test_duplicate_detection.py::test_first_arrival_wins_in_arrival_order; analytics/duplicate_detection.py:13 | first arrival wins; reason 'session_id already received' |
| FR-030 | 02 | Must | PASS | tests/unit/analytics/test_quality_screening.py::test_duplicates_pass_through_ungated; tests/unit/analytics/test_pipeline.py::test_dropping_duplicates_changes_nothing_else; analytics/day_ledger.py:66 | duplicates skip gate/screen/baseline/scores/ledger |
| FR-040 | 02 | Must | PASS | tests/unit/analytics/test_quality_screening.py::test_thresholds_are_strict; analytics/quality_screening.py:14 | 'quality flag poor' |
| FR-041 | 02 | Must | PASS | tests/unit/analytics/test_quality_screening.py::test_thresholds_are_strict | -40.0 passes, -39.9 'noise above limit' |
| FR-042 | 02 | Must | PASS | tests/unit/analytics/test_quality_screening.py::test_thresholds_are_strict | 1.0 passes, 0.99 'speech too short' |
| FR-043 | 02 | Must | PASS | tests/unit/analytics/test_quality_screening.py::test_all_reasons_in_fixed_order | joined by '; ' in fixed order |
| FR-044 | 02 | Must | PASS | tests/unit/analytics/test_baseline_builder.py::test_freeze_points_skip_non_usable_records; tests/unit/analytics/test_composite_score.py::test_src05_scored_sessions; tests/validation/test_r03_set_aside_sessions.py | only usable rows scored/in baseline; R03 answer-key check |
| FR-050 | 02 | Must | PASS | tests/unit/analytics/test_epoch_detection.py::test_device_firmware_and_software_changes; ::test_set_aside_record_starts_an_epoch; ::test_time_order_and_duplicates | epoch key change starts new epoch, incl. set-aside |
| FR-051 | 02 | Must | PASS | backend/models/epoch.py:54-67; tests/unit/analytics/test_epoch_detection.py::test_src05_r07_epochs; tests/integration/pipeline/test_runner_persistence.py::test_full_run_on_src05 | epochs persisted (11 rows) with device/fw/sw/start/end |
| FR-052 | 02 | Must | PASS | tests/unit/analytics/test_baseline_builder.py::test_membership_and_forming_epochs; tests/validation/test_r07_device_move.py::test_vc_r07_device_move | R07 epoch 2 baseline counted from zero |
| FR-053 | 02 | Must | PASS | backend/services/pipeline_persistence.py:356-371; tests/unit/analytics/test_alert_generator.py::test_one_event_per_ringing_epoch_with_closure_facts; tests/unit/analytics/test_cusum_engine.py::test_epochs_have_their_own_tally | 'epoch ended' closure; tally per epoch from 0 |
| FR-060 | 02 | Must | PASS | tests/unit/analytics/test_speaker_screen.py::test_src05_r05_quarantines_use_the_first_n; analytics/speaker_screen.py:3-8 | raw values vs first up to N prior usable |
| FR-061 | 02 | Must | PASS | tests/unit/analytics/test_speaker_screen.py::test_no_screen_below_screen_min_n | <5 prior usable -> usable |
| FR-062 | 02 | Must | PASS | tests/unit/analytics/test_speaker_screen.py::test_quarantine_needs_f0_and_two_composite_features | F0 only -> usable; F0 + 2 composites -> quarantined |
| FR-063 | 02 | Must | PASS | tests/unit/analytics/test_speaker_screen.py::test_src05_r05_quarantines_use_the_first_n | exact reason strings with 2dp z and count |
| FR-064 | 02 | Must | PASS | tests/unit/analytics/test_speaker_screen.py::test_src05_r05_quarantines_use_the_first_n; tests/validation/test_r05_possible_other_speaker.py::test_vc_r05_possible_other_speaker | R05 day 8 (pre-freeze) and day 22 (post-freeze) quarantined |
| FR-065 | 02 | Must | PASS | tests/unit/analytics/test_speaker_screen.py::test_quarantine_needs_f0_and_two_composite_features; tests/unit/analytics/test_composite_score.py::test_src05_scored_sessions | quarantined not joining reference; scores only usable |
| FR-070 | 02 | Must | PASS | tests/unit/analytics/test_morning_offset.py::test_local_time_vectors | zoneinfo America/Chicago incl. DST; local date/time |
| FR-071 | 02 | Must | PASS | tests/unit/analytics/test_morning_offset.py::test_local_time_vectors | 11:59:59 morning, 12:00 not |
| FR-072 | 02 | Must | PASS | tests/unit/analytics/test_morning_offset.py::test_r06_day_1_adjustment; ::test_afternoon_and_stored_features_unchanged | morning raw-offset; afternoon unchanged |
| FR-073 | 02 | Must | PASS | analytics/morning_offset.py:1-6; tests/unit/analytics/test_config.py::test_profiles_differ_only_in_profile_and_baseline_n; tests/validation/test_invariance.py::test_vc_r06_mut_missing_adjustment_is_detected | offsets from config only, nothing estimated |
| FR-074 | 02 | Must | PASS | analytics/baseline_builder.py:6; analytics/speaker_screen.py:3; tests/validation/test_r06_morning_effect.py::test_vc_r06_morning_effect | baseline adjusted, screen raw; R06 answer key |
| FR-080 | 02 | Must | PASS | tests/unit/analytics/test_baseline_builder.py::test_freeze_points_skip_non_usable_records; tests/unit/analytics/test_config.py::test_profiles_differ_only_in_profile_and_baseline_n | first N usable; 16 test / 30 production |
| FR-081 | 02 | Must | PASS | tests/unit/analytics/test_baseline_builder.py::test_r09_worked_example; ::test_pause_floor_rows | median, MAD, spread x1.4826, pause floor 0.5 |
| FR-082 | 02 | Must | PASS | tests/unit/analytics/test_baseline_builder.py::test_r09_worked_example | composite median/MAD/spread |
| FR-083 | 02 | Must | PASS | tests/integration/pipeline/test_runner_persistence.py::test_late_record_keeps_frozen_baselines; tests/unit/analytics/test_pipeline.py::test_frozen_baselines_win_and_mismatch_warns | frozen baselines unchanged |
| FR-084 | 02 | Must | PASS | tests/integration/pipeline/test_runner_persistence.py::test_late_record_keeps_frozen_baselines | late_arrival warning on run; baseline unchanged |
| FR-085 | 02 | Must | PASS | tests/integration/api/test_residents.py::test_overview; tests/unit/analytics/test_baseline_builder.py::test_membership_and_forming_epochs | R02 baseline_forming 13 of 16, no scores, not error |
| FR-086 | 02 | Must | PASS | backend/models/baseline.py:62-69; tests/unit/analytics/test_baseline_builder.py::test_freeze_points_skip_non_usable_records | n_sessions, first/frozen_after session ids, frozen_at |
| FR-090 | 02 | Must | PASS | tests/unit/analytics/test_composite_score.py::test_src05_scored_sessions | 98 scored usable post-freeze sessions |
| FR-091 | 02 | Must | PASS | tests/unit/analytics/test_zscore_calculator.py::test_r09_ringing_session_z | R09 worked example |
| FR-092 | 02 | Must | PASS | tests/unit/analytics/test_composite_score.py::test_r09_composite | composite_raw 2.325508 |
| FR-093 | 02 | Must | PASS | tests/unit/analytics/test_composite_score.py::test_r09_composite | composite_z 4.288307 |
| FR-094 | 02 | Must | PASS | backend/models/score.py:67-73; tests/integration/pipeline/test_runner_persistence.py::test_full_run_on_src05 | z, composite_raw/z, tally, alarm_state, local_date, is_morning |
| FR-095 | 02 | Must | PASS | tests/unit/analytics/test_morning_offset.py::test_afternoon_and_stored_features_unchanged; tests/unit/analytics/test_feature_specs.py::test_features_equal_trd_23 | 12 features stored, composite uses 7 only |
| FR-100 | 02 | Must | PASS | tests/unit/analytics/test_cusum_engine.py::test_tally_and_states | S=max(0,S+z-0.5) |
| FR-101 | 02 | Must | PASS | tests/validation/test_r02_missing_days.py::test_vc_r02_missing_days; tests/validation/test_r03_set_aside_sessions.py::test_vc_r03_set_aside_sessions | tally only over scored rows; answer key |
| FR-102 | 02 | Must | PASS | tests/unit/analytics/test_cusum_engine.py::test_tally_and_states; ::test_src05_alarms | rings at first >=5, then on |
| FR-103 | 02 | Must | PASS | tests/unit/analytics/test_cusum_engine.py::test_tally_and_states | off before crossing |
| FR-104 | 02 | Must | PASS | tests/integration/pipeline/test_runner_persistence.py::test_full_run_on_src05; tests/integration/pipeline/test_runner_persistence.py::test_second_run_changes_nothing | one open alert each R09, R10; rerun no new rows |
| FR-105 | 02 | Must | PASS | backend/models/score.py:84-110; tests/integration/db/test_repositories.py (upsert_cusum_state) | one row per epoch: current_tally, last_scored_session_id, alarm_on |
| FR-106 | 02 | Must | PASS | tests/integration/api/test_alerts.py::test_reviews; tests/integration/api/test_alerts.py::test_refusals | review sets acknowledged/acknowledged_by; /acknowledge 404/405 |
| FR-107 | 02 | Must | PASS | tests/integration/api/test_alerts.py::test_reviews; tests/integration/api/test_alerts.py::test_snooze | scores/cusum_state snapshot unchanged |
| FR-108 | 02 | Must | PASS | tests/integration/api/test_alerts.py::test_alert_list | status and resident_code filters |
| FR-110 | 02 | Must | PASS | backend/services/pipeline_persistence.py:349-371; backend/api/alarms.py:48-130 | only pipeline closes (epoch ended/superseded); no close endpoint. superseded path not tested |
| FR-120 | 02 | Must | PASS | tests/unit/analytics/test_day_ledger.py::test_checked_in_gap_and_missed; ::test_src05_ledger; analytics/day_ledger.py:71-74 | enrolment to as-of/withdrawn_on inclusive; 300 rows |
| FR-121 | 02 | Must | PASS | tests/unit/analytics/test_day_ledger.py::test_checked_in_gap_and_missed | set-aside record counts as checked_in |
| FR-122 | 02 | Must | PASS | tests/unit/analytics/test_day_ledger.py::test_checked_in_gap_and_missed; ::test_src05_ledger | shared-device gap reason string; R02/R03 Oct 12 |
| FR-123 | 02 | Must | PASS | tests/unit/analytics/test_day_ledger.py::test_checked_in_gap_and_missed; analytics/day_ledger.py:24 | 'no record received' |
| FR-124 | 02 | Must | PASS | tests/unit/analytics/test_pipeline.py::test_src05_counts_and_sessions; tests/validation/test_r02_missing_days.py::test_vc_r02_missing_days | missing days create no session/score/tally |
| FR-125 | 02 | Must | PASS | analytics/day_ledger.py:71-74; tests/unit/analytics/test_day_ledger.py::test_checked_in_gap_and_missed | ledger runs to as-of date regardless of records |
| FR-133 | 02 | Must | PASS | tests/integration/api/test_residents.py::test_overview; frontend/components/FilterButtons/FilterButtons.test.tsx; frontend/tests/pages/residents.test.tsx (filters ?show=) | sort=alarm order, summary counts, Learning only when >=1, ?show= |
| FR-134 | 02 | Must | PASS | frontend/components/ResidentsTable/ResidentsTable.test.tsx (FE-182); frontend/components/ChartBanner/ChartBanner.test.tsx | 4 columns; device in banner with shared/replaced suffix |
| FR-136 | 02 |  | NOT APPLICABLE | specs/TRD/02_Functional_Requirements_Specification.md:192 | Retired by TRD 24 D-110 (wireframe v0.2) |
| FR-138 | 02 | Must | PASS | frontend/components/DataBar/DataBar.test.tsx; frontend/tests/pages/protected-layout.test.tsx | test_v0_1 and other-profile data bar texts |
| FR-139 | 02 |  | NOT APPLICABLE | specs/TRD/02_Functional_Requirements_Specification.md:195 | Retired by TRD 24 D-110 (wireframe v0.2) |
| FR-140 | 02 | Must | PASS | frontend/components/ResidentsTable/ResidentsTable.test.tsx (UX-037/UX-040); frontend/tests/pages/residents.test.tsx (opens chart on row click) | 'Open chart for <R>' link and row click |
| FR-156 | 02 | Must | PASS | frontend/components/DevicesSection/DevicesSection.test.tsx | grouped row 'D01, D04 to D06, D08 to D10: all uploaded Oct 30. Firmware fw-1.0.0.' |
| FR-160 | 02 | Must | PASS | frontend/components/BackLink/BackLink.test.tsx; frontend/tests/pages/resident-layout.test.tsx | '← Resident list' keeps ?show= |
| FR-161 | 02 | Must | PASS | frontend/components/ChartBanner/ChartBanner.test.tsx; frontend/components/ChartSectionNav/ChartSectionNav.test.tsx | banner facts, pill, 6 section links |
| FR-162 | 02 | Must | PASS | frontend/components/BaselinePanel/BaselinePanel.test.tsx | frozen text incl. restart prefix (R07) |
| FR-163 | 02 | Must | PASS | frontend/components/BaselinePanel/BaselinePanel.test.tsx; frontend/tests/unit/wording-chart.test.ts | 'Still forming: n of N...' + progressbar |
| FR-164 | 02 | Must | PASS | frontend/components/SummaryPanel/SummaryPanel.test.tsx; frontend/lib/wording/chart.ts:100 | Right now panel, note and PI marker from wording config |
| FR-165 | 02 | Must | PASS | frontend/components/ChangeScoreChart/ChangeScoreChart.test.tsx | bars by alarm_state, baseline slot, 'Alarm line: 5', x labels |
| FR-166 | 02 | Must | PASS | frontend/components/ChangeScoreChart/ChangeScoreChart.test.tsx | alarm-marker and 'Oct 21 · alarm' tick |
| FR-167 | 02 | Must | PASS | frontend/tests/pages/resident-trends.test.tsx; frontend/tests/unit/wording-trends.test.ts | exact panel line |
| FR-168 | 02 | Must | PASS | frontend/components/ChangeScoreChart/ChangeScoreChart.test.tsx (UX-090) | 'Show change score as a table' disclosure |
| FR-169 | 02 | Must | PASS | frontend/components/MeasurementCards/MeasurementCards.test.tsx | heading, 7 labelled cards with sparklines |
| FR-170 | 02 | Must | PASS | frontend/components/OtherMeasurementsCard/OtherMeasurementsCard.test.tsx | '12 other measurements ...' 'Stored, not scored' |
| FR-171 | 02 | Must | PASS | frontend/components/MeasurementCards/MeasurementCards.test.tsx; frontend/tests/unit/wording-trends.test.ts | exact caption |
| FR-172 | 02 | Should | PASS | frontend/tests/pages/resident-trends.test.tsx (R07 loads epoch 1); backend/api/scores.py:62 | 'Device period' select queries scores?epoch= |
| FR-180 | 02 | Must | PASS | frontend/tests/pages/resident-log.test.tsx; frontend/components/CheckinLog/CheckinLog.test.tsx | counts + events newest first with dates |
| FR-181 | 02 | Must | PASS | frontend/components/CheckinLog/CheckinLog.test.tsx; tests/integration/api/test_residents.py::test_checkin_log | all listed event types incl. checkins_started |
| FR-183 | 02 | Should | PASS | tests/integration/api/test_residents.py::test_checkin_log_filters | from/to filter |
| FR-194 | 02 | Must | PASS | frontend/components/AlarmReviewPanel/AlarmReviewPanel.test.tsx; frontend/components/StaffNotes/StaffNotes.test.tsx; frontend/tests/pages/resident-review.test.tsx | researcher: no forms/buttons, reviews and notes visible |
| FR-195 | 02 |  | NOT APPLICABLE | specs/TRD/02_Functional_Requirements_Specification.md:248 | Retired by TRD 24 D-110 (wireframe v0.2) |
| FR-200 | 02 | Must | PASS | frontend/components/ExperimentalBanner/ExperimentalBanner.test.tsx; frontend/tests/pages/admissions.test.tsx | exact note |
| FR-203 | 02 | Must | PASS | frontend/components/FacilityRangeChart/FacilityRangeChart.test.tsx; frontend/components/AdmissionsTable/AdmissionsTable.test.tsx | 'Show comparison' and grey band caption |
| FR-205 | 02 | Must | PASS | backend/services/pipeline_persistence.py:433-446; tests/integration/db/test_repositories.py (set_cohort_longitudinal) | cohort -> longitudinal when own baseline frozen |
| FR-207 | 02 |  | NOT APPLICABLE | specs/TRD/02_Functional_Requirements_Specification.md:261 | Retired by TRD 24 D-110 (wireframe v0.2) |
| FR-210 | 02 | Must | PASS | tests/integration/api/test_auth.py::test_valid_login_returns_a_bearer_token; frontend/tests/pages/login.test.tsx | JWT exp-iat 3600 |
| FR-211 | 02 | Must | PASS | frontend/tests/pages/protected-layout.test.tsx (FE-055, FE-056) | no token -> /login?next=; 401 -> /login?reason=expired |
| FR-214 | 02 | Must | PASS | tests/integration/api/test_auth.py::test_failed_logins_are_indistinguishable | inactive user login 401 |
| FR-216 | 02 | Must | PASS | tests/integration/api/test_auth.py::test_me_and_logout | email, display_name, role |
| FR-217 | 02 | Must | PASS | tests/integration/api/test_auth.py::test_me_and_logout; frontend/components/AppHeader/AppHeader.test.tsx (FE-058) | 204 + auth.logout audit; token discarded; no revocation |
| FR-218 | 02 | Must | PASS | frontend/components/AppHeader/AppHeader.test.tsx (FE-028) | clinician: no Study team/Admin; admin: both |
| FR-222 | 02 | Must | PASS | frontend/tests/pages/admin.test.tsx (UX-213, UX-217) | upload shows accepted/rejected rows/duplicates |
| FR-228 | 02 | Must | PASS | tests/integration/test_cli_seed.py::test_withdraw_resident; tests/integration/api/test_sessions.py::test_withdrawn_resident; tests/integration/api/test_residents.py::test_filters_and_paging | withdraw CLI; ingest refused; hidden by default |
| FR-229 | 02 | Must | PASS | tests/integration/test_cli_pipeline.py::test_set_config_then_rebuild; backend/cli.py:733 | validates, audits config.changed old/new/reason, rebuild notice |
| FR-250 | 02 | Must | PASS | backend/services/audit_service.py:30-55; tests/integration/api/test_auth.py; tests/integration/api/test_ingest.py::test_batch_is_audited_with_the_request_id; tests/integration/api/test_alerts.py::test_reviews | all listed actions in vocabulary and tested |
| FR-251 | 02 | Must | PASS | backend/models/audit_log.py:51-64; tests/unit/backend/services/test_audit.py::test_forbidden_details_raise_and_write_nothing | columns present; forbidden keys refused |
| FR-260 | 02 |  | NOT APPLICABLE | specs/TRD/02_Functional_Requirements_Specification.md:318 | Retired by TRD 24 D-110 (wireframe v0.2) |
| FR-261 | 02 |  | NOT APPLICABLE | specs/TRD/02_Functional_Requirements_Specification.md:319 | Retired by TRD 24 D-110 (wireframe v0.2) |
| FR-262 | 02 | Must | PASS | frontend/components/SummaryPanel/SummaryPanel.test.tsx; frontend/components/MoreDetailTiles/MoreDetailTiles.test.tsx | Alarm started, days Open, review status, Change score 26.8 |
| FR-264 | 02 | Must | PASS | frontend/components/AlarmReviewPanel/AlarmReviewPanel.test.tsx; frontend/components/SummaryPanel/SummaryPanel.test.tsx | panel heading; Review this alert / See what changed links |
| FR-265 | 02 |  | NOT APPLICABLE | specs/TRD/02_Functional_Requirements_Specification.md:323 | Retired by TRD 24 D-110 (wireframe v0.2) |
| FR-266 | 02 | Must | PASS | tests/integration/pipeline/test_runner_persistence.py::test_alerts_endpoint_leaning_most; tests/unit/analytics/test_alert_generator.py::test_leaning_most_rules; frontend/components/LeaningMost/LeaningMost.test.tsx | R09 'more pauses, quieter, less voiced sound'; none text; tie order |
| FR-267 | 02 | Must | PASS | frontend/components/AlertReviewForm/AlertReviewForm.test.tsx | 5 configured options in order |
| FR-268 | 02 | Must | PASS | frontend/components/AlertReviewForm/AlertReviewForm.test.tsx | 4 outcomes, exactly one required |
| FR-269 | 02 | Must | PASS | frontend/components/AlertReviewForm/AlertReviewForm.test.tsx; tests/integration/api/test_alerts.py::test_invalid_reviews_write_nothing | note counter 0/2000; 2001 -> 422 |
| FR-270 | 02 | Must | PASS | tests/integration/api/test_alerts.py::test_reviews; frontend/components/AlertReviewForm/AlertReviewForm.test.tsx | POST reviews creates alert_reviews row, alert acknowledged, reviewed true |
| FR-272 | 02 | Must | PASS | tests/integration/api/test_alerts.py::test_reviews; frontend/components/AlarmReviewPanel/AlarmReviewPanel.test.tsx | multiple reviews listed newest first |
| FR-274 | 02 | Must | PASS | tests/integration/api/test_alerts.py::test_snooze; frontend/components/AlertReviewForm/AlertReviewForm.test.tsx | default 24h, snoozed_by, 'Reminder set for ...', status unchanged |
| FR-276 | 02 | Must | PASS | tests/unit/backend/test_no_outbound_alerts.py; backend/jobs/nightly_run.py | no deadline/escalation code; inspection |
| FR-277 | 02 | Must | PASS | frontend/components/AlarmReviewPanel/AlarmReviewPanel.test.tsx | exact open-questions text |
| FR-278 | 02 |  | NOT APPLICABLE | specs/TRD/02_Functional_Requirements_Specification.md:336 | Retired by TRD 24 D-110 (wireframe v0.2) |
| FR-279 | 02 | Must | PASS | tests/integration/api/test_alerts.py::test_reviews; tests/integration/api/test_alerts.py::test_snooze | alert.reviewed and alert.snoozed audit rows |
| FR-280 | 02 | Must | PASS | frontend/tests/pages/resident-review.test.tsx (R01 only Staff notes); frontend/components/AppHeader/AppHeader.test.tsx | no review panel; no badge when count 0 |
| FR-290 | 02 | Must | PASS | tests/integration/pipeline/test_runner_persistence.py::test_full_run_on_src05; tests/unit/analytics/test_config.py::test_profiles_differ_only_in_profile_and_baseline_n | recomputed per run; thresholds from config, same in both profiles |
| FR-291 | 02 | Must | PASS | tests/unit/analytics/test_data_alerts.py::test_src05_exactly_four_alerts_in_order; analytics/data_alerts.py:84-93 | R08 title/detail exact |
| FR-292 | 02 | Must | PASS | tests/unit/analytics/test_data_alerts.py::test_src05_exactly_four_alerts_in_order; analytics/data_alerts.py:95-103 | R05 title/detail; singular form in code |
| FR-293 | 02 | Must | PASS | tests/unit/analytics/test_data_alerts.py::test_src05_exactly_four_alerts_in_order; analytics/data_alerts.py:104-115 | R03 7 of 29, reason order |
| FR-294 | 02 | Must | PASS | tests/unit/analytics/test_data_alerts.py::test_src05_exactly_four_alerts_in_order; ::test_single_resident_device_needs_a_run; analytics/data_alerts.py:156-160 | shared-device and 2-day single rule; both title forms |
| FR-295 | 02 | Must | PASS | analytics/data_alerts.py:106; tests/unit/analytics/test_data_alerts.py::test_src05_exactly_four_alerts_in_order | one per kind; stalled excludes high_set_aside |
| FR-296 | 02 | Must | PASS | backend/services/pipeline_persistence.py:388-401; tests/integration/pipeline/test_runner_persistence.py::test_a_run_at_an_earlier_as_of_keeps_alert_history | first_detected kept, last moves, resolved when gone (resolve path untested) |
| FR-298 | 02 | Must | PASS | frontend/tests/pages/study.test.tsx (UX-306..UX-308); frontend/components/DataProblemsList/DataProblemsList.test.tsx | list with Staff can help / Study team tags |
| FR-300 | 02 | Must | PASS | tests/integration/api/test_alerts.py::test_data_alert_list; tests/integration/pipeline/test_runner_persistence.py::test_full_run_on_src05 | data alerts not counted as alarms; badge uses alerts status=open |
| FR-311 | 02 | Must | PASS | frontend/tests/pages/study.test.tsx (UX-010, FE-195) | heading, counts line, answer-key clause test profile only |
| FR-313 | 02 | Must | PASS | frontend/components/KpiTiles/KpiTiles.test.tsx; frontend/tests/pages/study.test.tsx; tests/unit/analytics/test_aggregates.py::test_src05_kpis | four tiles with values |
| FR-314 | 02 | Must | PASS | tests/unit/analytics/test_aggregates.py::test_pct_half_up_integer | half-up integer |
| FR-315 | 02 | Must | PASS | frontend/tests/pages/study.test.tsx (UX-356..UX-360); tests/unit/analytics/test_aggregates.py::test_src05_daily_series | legend Used, Set aside, Held back (other voice), Missed; Oct 12 label |
| FR-316 | 02 | Must | PASS | frontend/tests/pages/study.test.tsx (funnel); tests/unit/analytics/test_aggregates.py::test_src05_funnel | four funnel rows exact |
| FR-317 | 02 | Must | PASS | frontend/tests/pages/study.test.tsx (by-resident); tests/unit/analytics/test_aggregates.py::test_src05_by_resident | lowest first, accessible names |
| FR-318 | 02 | Must | PASS | frontend/tests/pages/study.test.tsx (alarm timing); frontend/components/AlarmTimingTable/AlarmTimingTable.test.tsx; tests/integration/api/test_analytics.py::test_summary | rows from ground truth; 'Other 8' row |
| FR-319 | 02 | Must | PASS | tests/integration/api/test_analytics.py::test_production_profile; frontend/components/ReviewOutcomesTable/ReviewOutcomesTable.test.tsx; frontend/tests/pages/study.test.tsx (FE-195) | production review outcomes panel |
| FR-320 | 02 | Must | PASS | frontend/tests/pages/study.test.tsx ('Show daily counts as a table'); frontend/components/UsableByResidentChart/UsableByResidentChart.tsx:49 | daily table; meters have accessible names per UX-225 |
| FR-321 | 02 |  | NOT APPLICABLE | specs/TRD/02_Functional_Requirements_Specification.md:373 | Retired by TRD 24 D-110 (wireframe v0.2) |
| FR-322 | 02 | Must | PASS | tests/integration/api/test_analytics.py::test_summary; ::test_production_profile | kpis, daily_series, funnel, by_resident, alarm_timing/review_outcomes |
| FR-330 | 02 | Must | PASS | frontend/components/AppHeader/AppHeader.test.tsx; frontend/lib/hooks.ts:23 | brand, facility line, nav by role, open-alarm badge, name, Sign out |
| FR-331 | 02 | Must | PASS | frontend/tests/pages/resident-layout.test.tsx; frontend/tests/pages/protected-layout.test.tsx (activeFor); frontend/tests/pages/admissions.test.tsx:106 | chart back link, nav active Resident list; admissions no back link |
| FE-001 | 04 | Must | PASS | frontend/package.json:28; frontend/tsconfig.json:7; frontend/app/ (App Router) | next 14.2.35, typescript 5.6.3, strict true |
| FE-003 | 04 | Must | PASS | frontend/package.json:26-32; frontend/components/*/*.module.css (45); frontend/styles/tokens.css | react 18.3.1, no UI/icon lib; non-ASCII scan of app/components/lib finds only ▲ ! ● ○ ← as glyphs (others are punctuation) |
| FE-006 | 04 | Must | PASS | frontend/lib/hooks.ts:11-28; frontend/lib/queryClient.ts:12-25; app/(protected)/*/page.tsx useQuery/useMutation | @tanstack/react-query 5.105.0; login/logout and CSV downloads call api directly (not cached server state) |
| FE-007 | 04 | Must | PASS | frontend/tests/e2e/privacy.spec.ts:40; .github/workflows/ci.yml:26 | grep for audio/video/MediaRecorder/AudioContext/waveform in frontend source: no hits |
| FE-008 | 04 | Must | PASS | .github/workflows/ci.yml:44; frontend/package.json:26-58 | no openai/anthropic/llm/langchain references in frontend source or deps |
| FE-010 | 04 | Must | PASS | frontend/app/, frontend/lib/, frontend/services/api.ts, frontend/tests/{unit,pages,fixtures,msw,e2e} | tree matches §4.2; package.json, next.config.js, services/api.ts filled in place |
| FE-011 | 04 | Must | PASS | frontend/services/api.ts:146 | only fetch( call in frontend source is in services/api.ts |
| FE-012 | 04 | Must | PASS | frontend/package.json:21; .github/workflows/ci.yml:164-179 | CI exports OpenAPI, diffs contract, regenerates lib/api-types.ts and fails on diff |
| FE-020 | 04 | Must | PASS | frontend/app/(protected)/{residents,residents/[residentCode]/{review,trends,baseline,log,device},admissions,study,admin}/page.tsx; app/login/page.tsx; app/page.tsx | all §4.3 routes present; no /alerts or /analytics; #devices at components/DevicesSection/DevicesSection.tsx:159 |
| FE-040 | 04 | Must | PASS | frontend/app/(protected)/layout.tsx:1; all (protected) pages start with "use client" | server components (app/layout, page.tsx redirect, not-found) fetch no data |
| FE-041 | 04 | Must | PASS | netlify.toml:16-17; frontend/next.config.js:3-9 | @netlify/plugin-nextjs, no output: "export"; middleware.ts and dynamic routes in use |
| FE-042 | 04 | Must | PASS | frontend/middleware.ts:4-12 | sets Cache-Control: private, no-store on /residents, /admissions, /study, /admin, /login |
| FE-043 | 04 | Must | PASS | frontend/next.config.js:4-5 | reactStrictMode true, poweredByHeader false, no images config |
| FE-044 | 04 | Must | PASS | frontend/next.config.js; frontend/middleware.ts | no Netlify Functions/Edge/Blobs/Forms/Identity imports in frontend source |
| FE-045 | 04 | Must | PASS | frontend/lib/queryClient.ts:1-25 | no persister; sessionStorage only for auth token (lib/auth.ts:15) and list filter (BackLink.tsx:12), not query cache |
| FE-061 | 04 | Must | PENDING BLOCK 4 | netlify.toml:24-31 | repo side done: header set verbatim in netlify.toml; response-header check needs hosted Netlify origins |
| FE-062 | 04 | Must | PASS | frontend/.eslintrc.json (react/no-danger: error) | no dangerouslySetInnerHTML/eval/new Function/innerHTML in frontend source |
| FE-063 | 04 | Must | PASS | frontend/components/NotesList/NotesList.test.tsx::lists notes newest first with time, type and author, text kept as typed | test renders "<b>not bold</b>" as literal text; no HTML rendering paths |
| FE-064 | 04 | Must | PASS | frontend/tests/e2e/privacy.spec.ts:40; frontend/app/layout.tsx:5 | no <script>/next/script/external URLs; E2E asserts only frontend and API origins contacted |
| FE-065 | 04 | Must | PASS | .github/workflows/ci.yml:224; scripts/ci/audit_gate.py:25,56 | npm audit --omit=dev, blocks high/critical with SECURITY_EXCEPTIONS.md allow-list |
| FE-067 | 04 | Must | PASS | frontend/app/(protected)/error.tsx:1-15; frontend/lib/wording/common.ts:74; frontend/components/AdminPanel/formErrors.ts | boundaries show no details; errors map by code to fixed copy; request_id as "Reference:" |
| FE-068 | 04 | Must | PASS | frontend/lib/types.ts; grep of app/components/lib | no name/DOB/room fields rendered; room_label in api-types is never used |
| FE-075 | 04 | Must | PASS | frontend/services/api.ts:4-38,186-265; frontend/lib/types.ts:2-3 | all 30 §4.6.2 functions exist; types from lib/api-types.ts via lib/types.ts |
| FE-090 | 04 | Must | PASS | frontend/components/<Name>/<Name>.tsx export interface <Name>Props (all §4.8 components) | every inventory component exists with exported Props; retired SummaryTiles/SortSelect/DeviceCell/Footer/Alert*/MiniTallyChart/ReviewDialog absent |
| FE-103 | 04 |  | NOT APPLICABLE | specs/TRD/04_Frontend_TRD.md:538 | retired by TRD 24 D-110 |
| FE-131 | 04 |  | NOT APPLICABLE | specs/TRD/04_Frontend_TRD.md:549 | retired by TRD 24 D-110 |
| FE-139 | 04 |  | NOT APPLICABLE | specs/TRD/04_Frontend_TRD.md:557 | retired by TRD 24 D-110 |
| FE-143 | 04 | Must | PASS | frontend/lib/wording/list.ts:29; frontend/lib/wording/study.ts:200; frontend/lib/wording/trends.ts:132; tests/pages/residents.test.tsx; components/DevicesSection/DevicesSection.test.tsx::shows the empty state | UX-204 copy present and tested |
| FE-161 | 04 | Must | PASS | frontend/styles/globals.css:9-18,41-46,136-140 | body font/16px/1.45/tabular-nums/ink on canvas/margin 0; main max-width and page-pad 12px below 640px |
| FE-162 | 04 | Must | PASS | frontend/tests/e2e/responsive.spec.ts:68-90; frontend/styles/globals.css:102-107 | E2E checks all interactive targets ≥44×44 at 320–390px widths |
| FE-163 | 04 | Must | PASS | frontend/styles/globals.css:22-25; frontend/styles/tokens.css:37 | :focus-visible outline var(--focus-ring), offset 2px |
| FE-165 | 04 | Must | PASS | frontend/components/ChartSectionNav/ChartSectionNav.module.css:1; app/(protected)/residents/[residentCode]/layout.module.css:1; tests/e2e/responsive.spec.ts:121,142 | 760px nav row, 640px phone, 1024px tiles; E2E wide/narrow layouts |
| FE-173 | 04 | Must | PASS | frontend/lib/config.ts:23-49; frontend/.env.example | only NEXT_PUBLIC_API_BASE_URL/APP_ENV/GIT_SHA; no secret names in frontend source |
| FE-180 | 04 | Must | PASS | frontend/vitest.config.ts:15-22 | coverage block matches FE-180 exactly |
| FE-200 | 04 | Must | PASS | frontend/.eslintrc.json | extends next/core-web-vitals, @typescript-eslint/recommended, jsx-a11y/strict, prettier last; 3 rules set |
| FE-201 | 04 | Should | PASS | frontend/.prettierrc | printWidth 100, singleQuote false, trailingComma all, semi true |
| FE-202 | 04 | Must | PASS | .github/workflows/ci.yml:194-199; .github/workflows/e2e.yml:11-13,31-89 | npm ci, lint, typecheck, format:check, test:coverage, build in order; Playwright on PRs to main |
| FE-203 | 04 | Must | PASS | frontend/package.json:12 (next lint --max-warnings 0); .github/workflows/ci.yml:195-199 | lint gate at zero warnings plus typecheck and build in CI |
| FE-204 | 04 | Should | PASS | scripts/ci/check-bundle.mjs:1-14; .github/workflows/ci.yml:200 | CI fails any dashboard route over 300 KB gzip first-load JS |
| API-001 | 05 | Must | PASS | backend/main.py:68; backend/requirements.txt:3 (fastapi==0.115.12); render.yaml:52,98; backend/Dockerfile:36 | create_app factory; deployed uvicorn commands carry --proxy-headers --forwarded-allow-ips="*" |
| API-004 | 05 | Must | PASS | pyproject.toml:50-54 (import-linter forbids fastapi in services); .github/workflows/ci.yml:78; backend/core/errors.py | No fastapi import in backend/services; expected failures raise AppError subclasses (ValueError only for programming errors) |
| API-006 | 05 | Must | PASS | backend/services/pipeline_runner.py:377; backend/services/analytics_summary.py:24; backend/services/alert_service.py:17 | run_pipeline is the only engine entry for runs; reads use build_analytics_summary and leaning_most; stage services are stubs |
| API-007 | 05 | Must | PASS | backend/core/config.py:46-50; backend/requirements.txt:5,10; backend/api/sessions.py:44-52; backend/api/ingest.py:75 | Sync SQLAlchemy 2.0/psycopg3; handlers def; async only for ingest body read + run_in_threadpool as sanctioned by TRD 05 §8 line 514 |
| API-008 | 05 | Must | PASS | backend/api/{alarms,analytics,health,residents,sessions}.py; backend/services/{baseline,cusum,ingestion,morning_adjustment,scoring,speaker_screen,validation}.py | All skeleton files kept under original names; baseline/cusum/scoring/speaker_screen/morning_adjustment are docstring-only thin adapters (ARC-052) |
| API-010 | 05 | Must | PASS | backend/core/config.py:290-293 | get_settings is @lru_cache(maxsize=1) over build_settings() |
| API-014 | 05 | Must | PASS | backend/services/auth_service.py:128-137; backend/core/security.py:91; backend/api/deps.py:236-242; tests/security/test_api_keys.py::test_key_without_ingest_scope_is_forbidden | SHA-256 lookup of active key, 401 API_KEY_INVALID, 403 FORBIDDEN on missing scope (implemented in authorize()) |
| API-015 | 05 | Must | PASS | backend/api/deps.py:158-188,212-245; backend/api/permissions.py:35 | authorize() accepts API key or admin JWT for POST /ingest and returns Principal(actor_type, actor_id, device_id via key) |
| API-017 | 05 | Must | PASS | tests/integration/api/conftest.py:96; tests/integration/api/test_alerts.py:210; tests/integration/api/test_health.py:30 | Tests override get_settings/get_clock/get_engine via app.dependency_overrides |
| API-031 | 05 | Must | PASS | backend/api/sessions.py:24-52; backend/api/ingest.py:30-40,88; tests/integration/api/test_sessions.py::test_unknown_resident_is_rejected_and_stored | Raw body read with await request.body(); openapi_extra references IngestRecord; rejection stored verbatim |
| API-032 | 05 | Must | PASS | backend/services/ingestion.py:312-364; tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed | Test asserts raw ingest_batch_id None, api_key_id set, 0 ingest_batches rows; no audit row on single ingest |
| API-033 | 05 | Must | PASS | backend/services/validation.py:198-217; tests/integration/api/test_ingest.py::test_mapped_header_is_accepted; tests/unit/backend/services/test_validation.py::test_name_mapping | feature_name_map applied before validation |
| API-034 | 05 | Must | PASS | backend/services/validation.py:198-230; tests/unit/backend/services/test_validation.py::test_reject_rules; tests/integration/api/test_sessions.py::test_extra_field_and_audio_are_refused | Hand-written validator collects one error per field incl. extra_forbidden, ranges, timestamp format -> 422 VALIDATION_ERROR |
| API-035 | 05 | Must | PASS | backend/services/validation.py:218-230; tests/integration/api/test_sessions.py::test_version_and_timestamp_problems | schema_version 0.2 -> 422 UNSUPPORTED_SCHEMA_VERSION |
| API-045 | 05 | Must | PASS | backend/services/ingestion.py:283-291,351-353; tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed | Scope = resident + residents assigned to the device on local date; trigger ingest; synchronous run |
| API-048 | 05 | Must | PASS | backend/core/middleware.py:167-200; backend/api/ingest.py:84-90; backend/services/validation.py:400; tests/integration/api/test_ingest.py::test_legacy_file_is_refused | JSON or multipart CSV only; other media 415; CSV header must be SRC-05 set after mapping |
| API-049 | 05 | Must | PASS | backend/api/permissions.py:35; backend/api/ingest.py:86-89; backend/services/ingestion.py:384-387; tests/integration/api/test_ingest.py::test_src05_upload | Test asserts source csv_upload and uploaded_by admin id |
| API-055 | 05 | Should | PASS | analytics/pipeline.py:280-299 | device_assignment_mismatch RunWarning with resident_code, session_id and devices in detail; record still accepted |
| API-058 | 05 | Must | PASS | backend/core/config.py:201-203,305-317; tests/unit/backend/core/test_config.py::test_cfg_06_production_refuses_test_profile | Startup and nightly (load_settings_or_exit) refuse test_v0_1 in production and exit non-zero |
| API-059 | 05 | Must | PASS | backend/core/config.py:191-195,210-217; tests/unit/backend/core/test_config.py::test_staging_requires_sslmode_but_local_does_not | Staging/production refuse DATABASE_URL without sslmode=require/verify-full |
| API-062 | 05 | Must | PASS | backend/jobs/nightly_run.py:95-118; render.yaml:69-80; tests/integration/pipeline/test_nightly_run.py | Scope all, trigger nightly, as-of via runner; exit 1 on failed run |
| API-064 | 05 | Must | PASS | backend/services/pipeline_runner.py:383-386,408-409; backend/services/pipeline_persistence.py:103; backend/core/db.py:121-124; tests/integration/db/test_advisory_locks.py | Per-resident pg_advisory_xact_lock in ascending code order; only xact locks (device_alerts/nightly keys sanctioned by DB-021) |
| API-071 | 05 | Must | PASS | backend/services/resident_service.py:115-122,180-190; tests/integration/api/test_ui_fixture_ds07.py::test_resident_list | Order R09,R10,R03,R08,R01,R02,R04,R05,R06,R07 asserted on DS-07 |
| API-074 | 05 | Must | PASS | backend/repositories/read_models.py:83-95; tests/integration/api/test_ui_fixture_ds07.py::test_resident_list | last_30_days used/set_aside/quarantined/missed asserted per resident; duplicates excluded |
| API-094 | 05 | Must | PASS | backend/schemas/common.py:27-30; tests/integration/api/test_ui_fixture_ds07.py::test_as_of_without_clock_override; ::test_resident_list | as_of serialised 2026-10-30T20:00:00Z; last_checkin_local with facility offset; local_date YYYY-MM-DD |
| API-114 | 05 | Must | PASS | backend/api/openapi.py:88-92,141-142; docs/api_reference/openapi.json | bearerAuth (http bearer JWT) and apiKeyAuth (header X-API-Key) declared and attached per operation |
| API-128 | 05 | Must | PASS | backend/services/pipeline_persistence.py:203-237,322-358,361-392; tests/integration/pipeline/test_runner_persistence.py::test_second_run_changes_nothing; ::test_reviews_and_snooze_survive_a_rerun | Epochs/alerts/data_alerts upserted by natural keys; alert ids, reviews and snooze survive reruns |
| API-131 | 05 | Must | PASS | backend/api/alarms.py:88-102; backend/api/permissions.py:45; backend/repositories/alert_repository.py:203; tests/integration/api/test_alerts.py:130 | All staff roles; newest first (created_at desc) with limit/offset |
| API-138 | 05 | Must | PASS | backend/services/resident_service.py:111-160; tests/integration/api/test_ui_fixture_ds07.py::test_resident_list; tests/integration/api/test_residents.py:46-80 | needs_attention R03/R08 with reasons, alarm_reviewed false R09/R10, R07 restart_cause device, window asserted |
| API-139 | 05 | Must | PASS | backend/core/middleware.py:152-157; tests/integration/api/test_sessions.py::test_extra_field_and_audio_are_refused; tests/security/test_no_audio.py | audio/* refused 415 in middleware before routing, any method |
| ANL-003 | 07 | Must | PASS | pyproject.toml:39-43; tests/unit/backend/test_import_boundary.py::test_analytics_imports_are_allowed; tests/unit/analytics/test_pipeline.py::test_deterministic_and_order_independent | No I/O, clock or random imports in analytics/; frozen dataclasses; deterministic |
| ANL-006 | 07 | Must | PASS | analytics/pipeline.py:220-255 | run_pipeline calls stages in the fixed ANL-006 order |
| ANL-009 | 07 | Must | PASS | analytics/__init__.py:7-50; analytics/config.py:24 | Exports run_pipeline, PipelineConfig, PRODUCTION, TEST_V0_1, all contract dataclasses; ENGINE_VERSION = "0.1.0" |
| ANL-011 | 07 | Must | PASS | analytics/config.py (frozen slots dataclasses); analytics/pipeline.py:220-255 | Stages pass contract dataclasses; no pandas or dict records between stages |
| ANL-016 | 07 | Must | PASS | backend/services/pipeline_persistence.py:94-133; analytics/day_ledger.py:39-50 | load_inputs adds device-sharing residents for the ledger window |
| ANL-017 | 07 | Must | PASS | tests/validation/test_global_checks.py::test_vc_g02_annotated_sessions; tests/validation/test_r01_clean_control.py..test_r10_gradual_drift.py; tests/validation/comparator.py | R01-R10 answer-key comparison (tiers A/B) at 1e-6 / exact strings |
| ANL-022 | 07 | Must | PASS | analytics/robust_stats.py:17-23; analytics/composite_score.py:14-18; analytics/config.py:95 | float64 numpy.median; signed z summed in canonical order; no round() in analytics |
| ANL-031 | 07 | Must | PASS | backend/services/config_service.py:33-55; backend/services/pipeline_runner.py:358-366,121-126; backend/core/config.py:202 | config_default_used, pipeline_config_invalid, test_v0_1 refused in production at startup and on POST /pipeline/run |
| ANL-034 | 07 | Must | PASS | backend/services/pipeline_runner.py:383-386; backend/services/pipeline_persistence.py:103; tests/integration/db/test_advisory_locks.py | Per-resident xact lock at start of each resident txn, ascending resident_code |
| ANL-035 | 07 | Must | PASS | backend/services/pipeline_persistence.py:80-91 | RawRecord built from typed raw_sessions columns (timestamptz -> aware UTC), never payload |
| ANL-038 | 07 | Must | PASS | backend/services/pipeline_persistence.py:203-237; backend/services/pipeline_runner.py:391-392 | Epoch upsert reuses id; renumbering of frozen epoch blocked with late_arrival warning |
| ANL-042 | 07 | Must | PASS | tests/validation/comparator.py:22; tests/validation/answer_key.py:21; tests/validation/tier_b.py:79-86 | Workbook labels mapped to engine values (rings/composite/yes-no) in validation incl. GET /analytics/baselines |
| ANL-043 | 07 | Must | PASS | backend/services/ingestion.py:351-364; tests/integration/api/test_sessions.py::test_failed_run_answers_pending | Sync run after commit, trigger ingest; failed run -> 201 pending, record stays |
| ANL-044 | 07 | Must | PASS | backend/api/ingest.py:90-94; backend/services/ingestion.py:413-422; tests/integration/api/test_ingest.py::test_src05_upload | One BackgroundTasks run for first-arrival scope with co-assigned residents, trigger ingest |
| ANL-046 | 07 | Must | PASS | backend/services/pipeline_runner.py:112-118; backend/api/permissions.py:54; backend/core/config.py:204-205 | as_of precedence explicit -> PIPELINE_AS_OF (refused in production) -> now; admin JWT or pipeline:run key |
| ANL-050 | 07 | Should | PASS | analytics/robust_stats.py:17-26; analytics/cusum_engine.py:16-33 | numpy robust stats; linear per-resident stages by inspection; late-arrival exception as TRD |
| ANL-053 | 07 | Must | PASS | backend/services/pipeline_runner.py:251-254,293-314 | pipeline_run_started/succeeded/failed with required fields; pipeline_warning per warning (ERROR for baseline_mismatch); no _finished event |
| ANL-054 | 07 | Must | PASS | backend/services/pipeline_runner.py:293-314; tests/security/test_data_minimisation.py::test_responses_and_logs_hold_study_ids_only | Logs hold only study IDs and run metadata; test checks no feature values logged |
| ANL-055 | 07 | Should | PASS | analytics/morning_offset.py:1-37; analytics/config.py:400 | Offsets read only from PipelineConfig.morning_offsets; no estimator inside run_pipeline |
| ANL-056 | 07 |  | NOT APPLICABLE | specs/TRD/07_Analytics_Engine_TRD.md:394 | May; future EWMA (OQ-18), explicitly not implemented in v0.1 |
| ANL-057 | 07 |  | NOT APPLICABLE | specs/TRD/07_Analytics_Engine_TRD.md:395 | May; facility_norms.py created only when OQ-08 resolved (post-MVP) |
| ANL-058 | 07 | Should | PASS | analytics/config.py:73-96; analytics/composite_score.py:14-18; tests/unit/analytics/test_feature_specs.py | Composite keys/signs derived from FEATURES; no stage code change needed |
| ANL-059 | 07 | Must | PASS | analytics/data_alerts.py; analytics/pipeline.py:252; tests/unit/analytics/test_data_alerts.py::test_src05_exactly_four_alerts_in_order | Data alerts recomputed every run by generate_data_alerts |
| ANL-065 | 07 | Must | PASS | backend/services/analytics_summary.py:100,114 | not_reviewed_count computed at response time from open alerts |
| BSC-010 | 08 | Must | PASS | analytics/cusum_engine.py:18-22; tests/unit/analytics/test_cusum_engine.py::test_epochs_have_their_own_tally; tests/unit/analytics/test_baseline_builder.py::test_membership_and_forming_epochs | Reference list, baseline and CUSUM keyed per (resident, epoch) |
| BSC-011 | 08 | Must | PASS | analytics/speaker_screen.py; tests/unit/analytics/test_speaker_screen.py::test_src05_r05_quarantines_use_the_first_n | pending_screen records screened in time order on raw values |
| BSC-014 | 08 | Must | PASS | analytics/zscore_calculator.py; tests/unit/analytics/test_zscore_calculator.py::test_zero_spread_gives_zero | z = (x-median)/spread with floor; 0.0 when spread is 0 |
| BSC-019 | 08 | Should | PASS | backend/services/pipeline_persistence.py:251-252; database/schema.sql:617 | screen_detail stored in processed_sessions for screened records |
| BSC-023 | 08 | Must | PASS | backend/services/pipeline_persistence.py:251-255; database/schema.sql:611; analytics/morning_offset.py:32-37 | adjusted_features (19 keys) stored for non-duplicates; baselines/scores use adjusted |
| BSC-030 | 08 | Must | PASS | backend/services/pipeline_persistence.py:262-280; database/schema.sql:2021; analytics/config.py:578 | Baselines insert-only (app role SELECT,INSERT); deleted only by operator rebuild |
| BSC-042 | 08 | Must | PASS | analytics/pipeline.py:220; tests/unit/analytics/test_pipeline.py::test_contract_violations | _validate raises ContractError for missing/non-finite features; no imputation |
| BSC-043 | 08 | Should | PASS | analytics/pipeline.py:220-256 | Every record is processed as its own session; no per-day averaging/selection |
| CUS-002 | 09 | Must | PASS | analytics/cusum_engine.py:23-25; analytics/config.py:397-398,578-579 | k and h read from PipelineConfig (0.5, 5.0) |
| CUS-003 | 09 | Must | PASS | analytics/cusum_engine.py:16-33; tests/unit/analytics/test_cusum_engine.py::test_tally_and_states | Tally starts at 0 from first scored session; only scored rows enter run_cusum |
| CUS-004 | 09 | Must | PASS | analytics/pipeline.py:243; tests/unit/analytics/test_cusum_engine.py::test_src05_alarms | Only scored sessions update the tally; missing/set-aside/etc. never enter |
| CUS-009 | 09 | Must | PASS | backend/services/pipeline_persistence.py:297-305; database/schema.sql:865 | cusum_state per epoch with current_tally, last_scored_session_id, alarm_on, updated_at |
| CUS-010 | 09 | Must | PASS | tests/integration/pipeline/test_runner_persistence.py::test_second_run_changes_nothing | Rerun reproduces every derived row incl. cusum_tally/alarm_state |
| CUS-014 | 09 | Must | PASS | backend/services/pipeline_persistence.py:332-358; database/schema.sql:809,1112 | Upsert on (epoch_id, session_id), new alerts open; one non-closed alert per epoch index |
| CUS-018 | 09 | Must | PASS | backend/services/pipeline_persistence.py:309-317,342-357 | Alert closed 'epoch ended' with closed_at=as_of and system audit alert.closed |
| CUS-019 | 09 | Must | PASS | backend/api/alarms.py (no close endpoint) | No manual close endpoint; closed_reason admin reserved |
| CUS-020 | 09 | Must | PASS | backend/services/resident_service.py:139-157; tests/integration/api/test_ui_fixture_ds07.py::test_resident_chart_r09 | alarm_on while alert open or acknowledged; attention flag never overrides |
| CUS-021 | 09 | Must | PASS | backend/services/resident_service.py:139-147; tests/integration/api/test_residents.py:73-80 | Status follows current epoch (R07 epoch 2 no_alarm, restart_cause device) |
| CUS-023 | 09 | Must | PASS | frontend/components/ChangeScoreChart/ChangeScoreChart.tsx:108,119,263; frontend/lib/wording/trends.ts:16,35,38; frontend/components/ChangeScoreChart/ChangeScoreChart.test.tsx | Bars by alarm_state colours, baseline slot, dashed Alarm line, marker, intro text |
| CUS-026 | 09 | Must | PASS | frontend/lib/wording/chart.ts:186-187,320; frontend/lib/wording/list.ts:64; frontend/tests/unit/wording-chart.test.ts | Change/check-in wording from single wording config; no diagnosis/severity |
| CUS-029 | 09 | Must | PASS | backend/schemas/common.py:47-54; backend/schemas/analytics.py | GET /analytics meta carries cusum_h, baseline_n, pipeline_profile |
| CUS-030 | 09 | Must | NOT APPLICABLE | specs/backlog/features/FEAT-093-Alarm-Limit-Calibration-On-Team-1.md | Calibration is future research (FEAT-093, MVP status Future), gated on OQ-13/DS-04 |
| CUS-031 | 09 | Must | NOT APPLICABLE | specs/backlog/features/FEAT-093-Alarm-Limit-Calibration-On-Team-1.md | Calibration grid is future research (FEAT-093), not this build |
| CUS-032 | 09 | Must | NOT APPLICABLE | specs/backlog/features/FEAT-093-Alarm-Limit-Calibration-On-Team-1.md | Calibration metrics are future research (FEAT-093) |
| CUS-033 | 09 | Must | PASS | tests/unit/backend/test_ground_truth_boundary.py::test_only_the_summary_reads_the_answer_key; tests/integration/pipeline/test_runner_persistence.py::test_runner_never_reads_the_answer_key | Answer key never read by analytics/ or pipeline |
| CUS-034 | 09 | Must | NOT APPLICABLE | specs/backlog/features/FEAT-093-Alarm-Limit-Calibration-On-Team-1.md; specs/TRD/24_Risk_Assumptions_and_Open_Questions.md:107 | Selection gated on OQ-27/FEAT-093 future research; production values unchanged |
| CUS-035 | 09 | Must | PASS | analytics/config.py:578-579; tests/validation/test_global_checks.py | test_v0_1 profile unchanged; validation suite passes on it |
| CUS-036 | 09 | Must | PASS | analytics/ (no EWMA); analytics/cusum_engine.py | No EWMA trend implemented in v0.1 |
| CUS-037 | 09 |  | NOT APPLICABLE | specs/TRD/09_CUSUM_and_Alerting_Spec.md:255 | Retired by TRD 24 D-110 |
| CUS-042 | 09 | Must | PASS | frontend/lib/wording/review.ts:67; frontend/lib/wording/chart.ts:187; frontend/lib/wording/common.ts:13; frontend/components/AlarmReviewPanel/AlarmReviewPanel.test.tsx:34 | OQ note on review panel, 'prompt to check in, not a diagnosis', no-audio data bar; review roles not enforced beyond clinician/admin |
| CUS-046 | 09 | Must | PASS | analytics/config.py (OPERATIONAL_KEYS excluded from hash); tests/unit/analytics/test_config.py::test_hash_covers_algorithm_keys_only | Data-alert thresholds from config_parameters; excluded from config hash, recomputed each run |
| ING-002 | 10 | Must | PASS | backend/services/ingestion.py:337-364; tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed; ::test_failed_run_answers_pending | 201 with the six fields; pending on failed run |
| ING-005 | 10 | Must | PASS | backend/services/ingestion.py:65,507,515; backend/core/middleware.py:48; backend/api/permissions.py:35 | JSON or multipart CSV, <=5000 records, <=5 MB; X-API-Key ingest:write or admin JWT |
| ING-026 | 10 | Must | PASS | database/schema.sql (raw_sessions.timestamp_utc timestamptz); tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed | Stored as timestamptz; received string kept in payload |
| ING-030 | 10 | Must | PASS | database/schema.sql:1538,1544,2104,2125 | Trigger raw_sessions_no_update_delete; app SELECT,INSERT only; ingest_rejections append-only by grants |
| ING-036 | 10 | Must | PASS | backend/repositories/read_models.py:83-95,127-132; tests/integration/pipeline/test_runner_persistence.py::test_full_run_on_src05 | Duplicate processed rows stored and counted; read models exclude them |
| ING-042 | 10 | Must | PASS | analytics/quality_screening.py; tests/unit/analytics/test_quality_screening.py::test_src05_set_aside | Set-aside logged, epoch-assigned, not scored or in baseline; ledger counts it |
| ING-043 | 10 | Must | PASS | analytics/quality_screening.py:44 | Gate passes get pending_screen for the speaker screen |
| ING-044 | 10 | Must | PASS | analytics/day_ledger.py:27-32; database/schema.sql (device_assignments) | Inclusive valid_from/valid_to, null = open; device_on resolves per date |
| ING-046 | 10 | Must | PASS | analytics/day_ledger.py:35-50,84 | Shared when >= shared_device_min_residents enrolled residents assigned on d |
| ING-047 | 10 | Must | PASS | analytics/epoch_detection.py:31; analytics/pipeline.py:230,294-299 | Epochs use record device_id; assignments only for ledger/labels/mismatch warning |
| ING-051 | 10 | Must | PASS | analytics/day_ledger.py; tests/unit/analytics/test_day_ledger.py::test_checked_in_gap_and_missed | Missing days create no session/score and are recomputed each run |
| ING-054 | 10 | Must | PASS | tests/unit/backend/test_ground_truth_boundary.py; database/seeds/load_evaluation_ground_truth.py; database/schema.sql:2077 | Only the test loader and analytics_summary (readonly engine) touch ground truth; app role has no SELECT |
| ING-056 | 10 | Must | PASS | backend/ analytics/ (no SRC-06 converter); tests/integration/api/test_ingest.py::test_legacy_file_is_refused | No SRC-06 converter; legacy file refused |
| ING-059 | 10 | Must | PASS | backend/cli.py:610-622 | Seed uses IngestService.ingest_batch with source seed, no direct SQL inserts |
| UX-001 | 11 | Must | PASS | frontend/components/ResidentsTable/ResidentsTable.tsx; grep of app/components/lib | residents shown by resident_code only; no name/photo/room fields rendered |
| UX-002 | 11 | Must | PASS | frontend/lib/format.ts:17,41 | Intl formatting with timeZone = meta.facility_tz; no America/Chicago hard-coded in source |
| UX-005 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:83 | retired by TRD 24 D-110 |
| UX-006 | 11 | Must | PASS | frontend/tests/e2e/privacy.spec.ts:40 | E2E asserts no audio/video on all routes; no audio controls in source |
| UX-007 | 11 | Must | PASS | frontend/app/(protected)/residents/[residentCode]/log/page.tsx:68-71; components/AdmissionsTable/AdmissionsTable.tsx:77; tests/unit/wording-chart.test.ts:103,143 | N and h read from meta.baseline_n/cusum_h; "of 30" and "13 of 16" covered in wording/page tests |
| UX-009 | 11 | Must | PASS | frontend/services/api.ts:186-265 | no DELETE/PUT and no endpoint to edit baseline/score/alarm/records; only PATCH /users |
| UX-011 | 11 | Must | PASS | frontend/lib/wording/common.ts:11; frontend/components/AppHeader/AppHeader.module.css:15-18 | "<facility_name>, Assisted living", 14px --chrome-muted |
| UX-012 | 11 | Must | PASS | frontend/lib/wording/common.ts:11; .github/workflows/ci.yml:40 | rendered from meta.facility_name; old facility name absent (CI grep) |
| UX-013 | 11 | Must | PASS | frontend/components/AppHeader/AppHeader.tsx:55-72; AppHeader.module.css:19-41; lib/wording/common.ts:25-31 | nav aria-label Main, order and styles match; aria-current + white 16% (--nav-active) |
| UX-015 | 11 | Must | PASS | frontend/components/AppHeader/AppHeader.tsx:74-79; AppHeader.module.css:51-65 | display name 14px chrome-muted; Sign out min-height 44px, 1px chrome-muted border |
| UX-016 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:101 | retired by contract §20 R2 / TRD 24 D-110 |
| UX-020 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:114 | retired by TRD 24 D-110 |
| UX-021 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:115 | retired by TRD 24 D-110 |
| UX-022 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:116 | retired by TRD 24 D-110 |
| UX-023 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:117 | retired by TRD 24 D-110 (replaced by UX-402) |
| UX-024 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:118 | retired by TRD 24 D-110 |
| UX-030 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:124 | retired by TRD 24 D-110 |
| UX-031 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:125 | retired by TRD 24 D-110 |
| UX-032 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:126 | retired by TRD 24 D-110 |
| UX-033 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:127 | retired by TRD 24 D-110 |
| UX-035 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:141 | retired by TRD 24 D-110 |
| UX-039 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:145 | retired by TRD 24 D-110 |
| UX-044 | 11 | Must | PASS | frontend/components/CheckinLog/CheckinLog.tsx:37,95; frontend/lib/wording/study.ts:132-133 | log shows no duplicate events; counts come from API which excludes duplicates |
| UX-045 | 11 | Must | PASS | frontend/services/api.ts:202 (include_withdrawn=false) | resident list requests exclude withdrawn residents |
| UX-046 | 11 | Must | PASS | frontend/services/api.ts:202 (cohort=longitudinal); backend/services/pipeline_persistence.py:434-444 | list shows longitudinal cohort only; backend moves new_admission→longitudinal when baseline frozen |
| UX-051 | 11 | Must | PASS | frontend/lib/wording/study.ts:229; components/DevicesSection/DevicesSection.test.tsx::renders the §4.13.4 rows for DS-07 | "D02 (shared by R02 and R03): …" tested |
| UX-052 | 11 | Must | PASS | frontend/lib/wording/study.ts:214-220; components/DevicesSection/DevicesSection.tsx:77 | "Silent all day Oct 12." on the device row, tested in DS-07 row test |
| UX-053 | 11 | Must | PASS | frontend/lib/wording/study.ts:236; components/DevicesSection/DevicesSection.tsx:61-72 | replacement row text tested; retired devices filtered out (active only) |
| UX-055 | 11 | Must | PASS | frontend/components/DevicesSection/DevicesSection.tsx:180-212; frontend/lib/wording/study.ts:203-212 | details "Show all devices (n)" with the 7 columns incl. silent_days_last_30 and device_gap_days_last_30 |
| UX-057 | 11 | Must | PASS | frontend/lib/wording/study.ts:240-242; components/DevicesSection/DevicesSection.tsx:151 | "Since <Mon D>" / "<range> · replaced by <D>" |
| UX-064 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:237 | moved to UX-422 (D-110); definition row only |
| UX-074 | 11 | Must | PASS | frontend/lib/wording.ts:4-6 (re-exports lib/wording/*); components import from @/lib/wording | all Summary/what's-happening/legend copy in the wording configuration |
| UX-083 | 11 | Must | PASS | frontend/components/ChangeScoreChart/ChangeScoreChart.tsx:90,108-110 | bar fill follows alarm_state: off → --c-aside + 1px --muted stroke; rings/on → --red |
| UX-088 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:284 | retired by TRD 24 D-110 |
| UX-122 | 11 | Must | PASS | frontend/styles/globals.css:102-125 | .btn primary 44px, 0 20px, 700, radius 4, chrome bg/border; .btn-secondary surface, ink, 1px --rule |
| UX-125 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:326 | moved to UX-321 (D-110); definition row only |
| UX-127 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:328 | withdrawn by TRD 24 D-102 |
| UX-129 | 11 | Must | PASS | frontend/services/api.ts:211-212 | notes: only GET and POST; no edit/delete controls or endpoints |
| UX-136 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:337 | retired by TRD 24 D-110 |
| UX-137 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:338 | retired by TRD 24 D-110 |
| UX-138 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:339 | retired by TRD 24 D-110 |
| UX-160 | 11 | Must | PASS | frontend/lib/wording/chart.ts:186-187; frontend/lib/wording/list.ts:64 | copy frames results as change from own usual pattern; no measuring/grading wording found |
| UX-161 | 11 | Must | PASS | .github/workflows/ci.yml:42; grep of frontend/lib/wording, components, app | no forbidden stems in UI source except "not a diagnosis"; CI grep covers only diagnoses/severity |
| UX-162 | 11 | Must | PASS | frontend/lib/wording/chart.ts:186-187; frontend/lib/wording/list.ts:64 | "prompt to check in, not a diagnosis" and list note present |
| UX-164 | 11 | Must | PASS | frontend/lib/wording/common.ts:8; frontend/lib/wording/list.ts:66; frontend/lib/wording/chart.ts:6 | PI marker appended while CLINICAL_WORDING_APPROVED is false |
| UX-165 | 11 | Should | PASS | frontend/lib/wording/*.ts | no exclamation marks in copy (only the "!" pill glyph, common.ts:47); sentence case |
| UX-166 | 11 | Must | PASS | frontend/lib/wording/common.ts:11; .github/workflows/ci.yml:40 | facility from meta.facility_name; neither old name nor "[Facility name]" in frontend source |
| UX-167 | 11 | Must | PASS | frontend/lib/wording/chart.ts:244,295,322; frontend/lib/wording/review.ts:12; frontend/lib/wording/common.ts:36-40 | held back (possible other voice), change score, Comparing with baseline started, What did you find?, status labels |
| UX-171 | 11 | Must | PASS | frontend/lib/wording/common.ts:98; components/LoginForm/LoginForm.tsx:75; LoginForm.test.tsx::shows the wrong-credentials, rate-limit and network messages | role=alert, generic message |
| UX-172 | 11 | Must | PASS | frontend/components/LoginForm/LoginForm.tsx:18; lib/wording/common.ts:99; LoginForm.test.tsx::shows the wrong-credentials, rate-limit and network messages |  |
| UX-173 | 11 | Must | PASS | frontend/components/LoginForm/LoginForm.tsx:51-53; lib/wording/common.ts:100 | shown when reason=expired |
| UX-174 | 11 | Must | PASS | frontend/components/LoginForm/LoginForm.tsx:78; lib/wording/common.ts:97; LoginForm.test.tsx::shows Signing in… while busy |  |
| UX-180 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:419 | retired by TRD 24 D-110 |
| UX-183 | 11 | Must | PASS | frontend/lib/wording/admin.ts:16-23; frontend/components/AdmissionsTable/AdmissionsTable.module.css:3 | 5 columns + Actions, min-width 640px |
| UX-187 | 11 | Must | PASS | frontend/components/AdmissionsTable/AdmissionsTable.tsx:63,82; AdmissionsTable.module.css:20-27; lib/wording/admin.ts:25 | btn-secondary "Show comparison", aria-selected, 5px --chrome left border |
| UX-190 | 11 | Must | PASS | frontend/lib/wording/admin.ts:50; frontend/components/FacilityRangeChart/FacilityRangeChart.tsx:93 | caption via .caption (12px, --muted) |
| UX-191 | 11 | Must | PASS | frontend/lib/wording/admin.ts:69-79; components/FacilityRangeChart/FacilityRangeChart.tsx:67,111 | 7 plain labels; fallback is feature_key (ComparisonFeature has no label field) |
| UX-201 | 11 | Must | PASS | frontend/app/(protected)/residents/page.tsx:43-48; components/ResidentsTable/ResidentsTable.tsx:33-36 | keepPreviousData; filter applied client-side via ?show= without a request |
| UX-211 | 11 | Must | PASS | frontend/lib/wording/admin.ts:101-136; tests/pages/admin.test.tsx::adds a user and clears the form (UX-211, UX-228) | columns, Add user form, Deactivate/Reactivate with confirmation text |
| UX-214 | 11 | Must | PASS | frontend/lib/wording/admin.ts:205; frontend/components/AdminPanel/UploadTab.tsx:113 | line rendered unconditionally in every environment |
| UX-218 | 11 | Must | PASS | frontend/services/api.ts:186-265 | admin API surface: users, pipeline runs, upload only; no resident/device/assignment/API-key editing |
| UX-226 | 11 | Must | PASS | frontend/tests/e2e/a11y.spec.ts:29; frontend/tests/e2e/privacy.spec.ts:55 | one visible h1 per route enforced by strict locator; panels use h2 |
| UX-230 | 11 | Must | PASS | frontend/components/ChangeScoreChart/ChangeScoreChart.tsx:257; DailyCheckinsChart.tsx:171; Sparkline.tsx:37; styles/globals.css:142-149 | all Recharts series isAnimationActive=false; reduced-motion rule; no CSS animations |
| UX-244 | 11 | Must | PASS | frontend/tests/e2e/responsive.spec.ts:8-13,30-36 | no horizontal page scroll and no lost content at 320–390px (≥ 200% zoom equivalent reflow); no explicit zoom test |
| UX-245 | 11 | Must | PASS | frontend/app/(protected)/residents/page.module.css:3; frontend/components/ChartBanner/ChartBanner.module.css:7,18 | flex-wrap on list header and banner |
| UX-246 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:510 | retired by TRD 24 D-110 |
| UX-251 | 11 | Must | PASS | frontend/lib/wording/common.ts:44-52 | non-ASCII scan: only ▲ ! ● ○ ← used as glyphs; no icon library |
| UX-252 | 11 | Must | PASS | frontend/app/layout.tsx:5,12-13; frontend/tests/e2e/privacy.spec.ts:40,65 | next/font/local from app/fonts; E2E asserts no Google Fonts request |
| UX-253 | 11 | Should | PASS | frontend/styles/tokens.css:4,42-66; frontend/tests/e2e/a11y.spec.ts:40-56 | prefers-color-scheme dark tokens match §4.15; axe run in both schemes |
| UX-300 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:686 | retired by TRD 24 D-110 |
| UX-301 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:687 | retired by TRD 24 D-110 |
| UX-302 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:688 | retired by TRD 24 D-110 |
| UX-303 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:689 | retired by TRD 24 D-110 |
| UX-304 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:690 | retired by TRD 24 D-110 |
| UX-305 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:691 | retired by TRD 24 D-110 |
| UX-307 | 11 | Must | PASS | frontend/components/DataProblemsList/DataProblemsList.test.tsx::orders by kind then natural code (UX-307) |  |
| UX-308 | 11 | Must | PASS | frontend/components/DataProblemsList/DataProblemsList.tsx:35,44 | resident → /residents/<R>/log, device → /study#devices, aria-label = API title |
| UX-311 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:698 | retired by TRD 24 D-110 |
| UX-319 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:706 | retired by TRD 24 D-110 |
| UX-323 | 11 |  | NOT APPLICABLE | specs/TRD/11_User_Interface_UX_Spec.md:719 | retired by TRD 24 D-110 |
| UX-354 | 11 | Must | PASS | frontend/lib/wording/study.ts:45-55; components/KpiTiles/KpiTiles.test.tsx::renders DS-07 values | formed of active, still forming, restarted once/twice/k times, All baselines formed |
| UX-357 | 11 | Must | PASS | frontend/components/DailyCheckinsChart/DailyCheckinsChart.tsx:25-31,166-171; DailyCheckinsChart.module.css:34 | stacked Used/Set aside/Held back/Missed per day, ~160px plot, min-width 560px scroll |
| UX-359 | 11 | Must | PASS | frontend/lib/wording/study.ts:101-102 | "Show daily counts as a table" with Date/Used/Set aside/Held back/Missed/Note |
| UX-368 | 11 | Must | PASS | frontend/components/UsableByResidentChart/UsableByResidentChart.tsx:50; UsableByResidentChart.module.css:37 | --c-used meter; code links to /residents/<R>/log |
| UX-372 | 11 | Must | PASS | frontend/components/AlarmTimingTable/AlarmTimingTable.test.tsx::DS-07: planted rows then Other 8; ::missed, false alarm, 1 day and alarming others |  |
| UX-376 | 11 | Must | PASS | frontend/app/(protected)/study/page.tsx:180-190; frontend/lib/wording/study.ts:165 | timing table only when pipeline_profile is test_v0_1, labelled "Test data only"; production shows review outcomes |
| UX-377 | 11 | Should | PASS | frontend/app/(protected)/study/page.tsx:174,197-240; frontend/services/api.ts:238; lib/wording/study.ts:256-257 | Downloads panel with Scores (CSV) / Baselines (CSV) |
| UX-381 | 11 | Must | PASS | frontend/components/DailyCheckinsChart/DailyCheckinsChart.test.tsx::renders the DS-07 totals and never the ▲ glyph (UX-361) | DS-07 daily values rendered; also tests/pages/study.test.tsx |
| UX-408 | 11 | Must | PASS | frontend/services/api.ts:202 (sort=alarm); frontend/components/ResidentsTable/ResidentsTable.tsx:33-36 | API default sort requested; UI only filters, never reorders |
| SEC-001 | 12 | Must | PENDING BLOCK 4 | docs/deployment.md:11; specs/backlog/DEPLOYMENT_CHECKLIST.md:22 | Rule documented; seeds are synthetic (database/seeds/test_v0_1). Hosted data content verifiable only on live stack. |
| SEC-002 | 12 | Must | PASS | docs/deployment.md:11; docs/deployment.md:297; specs/backlog/DEPLOYMENT_CHECKLIST.md:23 | Go-live-on-AWS-only rule documented; no live data anywhere. |
| SEC-003 | 12 | Must | PENDING BLOCK 4 | specs/backlog/DEPLOYMENT_CHECKLIST.md:23; docs/deployment.md:168; checklist G.08 | Rule documented (test devices only); key issuance happens on hosted stack in Phase 10. |
| SEC-004 | 12 | Must | PASS | render.yaml:67; render.yaml:111; frontend/app/(protected)/layout.tsx:37; frontend/components/DataBar/DataBar.tsx:11 | Synthetic labels set per env; DataBar in protected layout (every page) and login. Hosted screenshot = checklist G.11. |
| SEC-005 | 12 | Must | PASS | specs/backlog/DEPLOYMENT_CHECKLIST.md:203 (N.13); docs/deployment.md:297 | Checklist includes the signed go-live item, marked n/a for interim. |
| SEC-006 | 12 | Must | PASS | backend/requirements.txt; frontend/package.json:27-33 | No Render/Netlify/Neon SDK in backend/analytics/frontend runtime deps; @netlify/plugin-nextjs is build-only devDependency. |
| SEC-007 | 12 | Must | PASS | render.yaml:47,75,93,119 (region ohio); docs/deployment.md:26,81 | Render ohio in blueprint; Neon aws-us-east-1 documented (creation = checklist B.01, Block 4). |
| SEC-027 | 12 | Must | PASS | backend/api/deps.py:233-242; backend/api/permissions.py:28-63; tests/integration/api/test_role_checks.py::test_every_matrix_cell | Non-key endpoints answer 401 to API keys; matrix test asserts 401 for key credentials on every route. |
| SEC-037 | 12 | Must | PASS | frontend/lib/auth.ts:1-19 | Token in module memory + sessionStorage only; no localStorage/cookie use for token. |
| SEC-038 | 12 | Should | PASS | frontend/app/(protected)/layout.tsx:12-20; frontend/lib/AuthProvider.tsx:67; frontend/tests/pages/login.test.tsx; frontend/components/LoginForm/LoginForm.test.tsx:26 | Redirect to /login when signed out/expired; expiry message rendered and tested. |
| SEC-043 | 12 | Must | PASS | frontend/components/AppHeader/AppHeader.tsx:63-70; frontend/lib/roles.ts; frontend/app/(protected)/admin/page.tsx:14; frontend/app/(protected)/study/page.tsx:53; frontend/tests/e2e/auth.spec.ts | Role-gated nav, pages and review/note forms; read-only messages tested (resident-review.test.tsx:73). |
| SEC-046 | 12 | Must | NOT APPLICABLE | backend/api/permissions.py:62 (PATCH /users/{id}) | Requirement on admin/people process (IRB roster check, 1-day deactivation); deactivation mechanism exists. |
| SEC-052 | 12 | Must | PASS | .github/workflows/ci.yml:8,226-227; .gitleaks.toml | gitleaks v8.18.4 detect over full history in security-audit on pull_request; allow-list only placeholders. |
| SEC-053 | 12 | Should | PENDING BLOCK 4 | gh api repos/EchoWellApp/echowell -> security_and_analysis null (not visible) | Repo setting not readable with available token; platform setting to confirm in Block 4. |
| SEC-060 | 12 | Must | PENDING BLOCK 4 | netlify.toml:27 (HSTS); tests/smoke/test_tls.py; checklist DEP-080(j)/DEP-081(g) | TLS/redirect on hosted origins needs live check; repo-side HSTS header and TLS smoke test exist. |
| SEC-063 | 12 | Must | PENDING BLOCK 4 | docs/deployment.md:68,81 | Provider-managed encryption at rest is a Neon platform property; AWS KMS part is AWS cut-over. |
| SEC-064 | 12 | Must | PENDING BLOCK 4 | tests/smoke/test_tls.py; render.yaml | No plain-HTTP path is a Render edge property; verify on live origin. |
| SEC-072 | 12 | Must | PASS | frontend/app/layout.tsx:1-12; frontend/app/fonts/SourceSans3-latin-variable.woff2; netlify.toml:32 (font-src 'self') | Source Sans 3 self-hosted via next/font/local. |
| SEC-073 | 12 | Must | PASS | netlify.toml:32 (script-src 'self'); frontend/package.json dependencies | No external script origins, no analytics/tracker packages, no next/script usage. |
| SEC-074 | 12 | Must | PASS | frontend/.eslintrc.json:10 | react/no-danger error; no dangerouslySetInnerHTML in frontend source. |
| SEC-075 | 12 | Should | PASS | netlify.toml:32; specs/backlog/DEPLOYMENT_CHECKLIST.md:202 (N.12) | unsafe-inline accepted for MVP; nonce CSP deferred to Amplify per TRD. |
| SEC-076 | 12 | Must | PASS | frontend/components/NotesList/NotesList.test.tsx:38-52; frontend/.eslintrc.json:10 | HTML in note body rendered as text, tested. |
| SEC-083 | 12 | Must | PASS | .github/workflows/ci.yml:228-229; backend/alembic/versions/0002_seed_config_parameters.py:108 | Bandit -ll (includes B608) in CI; single nosec on constant-only downgrade SQL. |
| SEC-084 | 12 | Must | PASS | backend/schemas/common.py:15-21; backend/api/alarms.py:56,72; backend/api/residents.py:4 | Code pattern, UUID path params, enums via typed params. |
| SEC-086 | 12 | Must | PASS | backend/services/ingestion.py:490-506; backend/services/export_service.py:42-66 | csv.DictReader text only; exports hold only pattern-constrained codes, numbers, dates, enums (no free text). |
| SEC-105 | 12 | Must | PASS | backend/api/permissions.py:28-63; backend/alembic/versions/0001_initial_schema.py:800-804 | No audit-log endpoint; echowell_readonly has SELECT on audit_logs. |
| SEC-106 | 12 | Must | PASS | backend/alembic/versions/0001_initial_schema.py:763-766; backend/jobs/ | audit_logs append-only triggers; no deletion job. |
| SEC-110 | 12 | Must | PASS | database/roles/provision_login_roles.sql:15-45; backend/alembic/versions/0001_initial_schema.py:784-805 | Roles created by provisioning script, never Alembic (no CREATE ROLE in migrations); grants in migration. |
| SEC-112 | 12 | Must | PASS | backend/alembic/versions/0001_initial_schema.py:759-762,790; tests/integration/test_schema_behaviour.py::test_ac_pgs_01_raw_sessions_update_fails_for_app | Trigger + INSERT/SELECT-only grant; delete/truncate tests too. |
| SEC-115 | 12 | Must | PENDING BLOCK 4 | specs/backlog/DEPLOYMENT_CHECKLIST.md:56 (B.08) | Custody of Neon owner credentials is checklist row B.08 (unchecked, Phase 10); apps use echowell_* roles. |
| SEC-123 | 12 | Must | PASS | backend/models/device.py:45,58; database/seeds/test_v0_1/devices.csv | room_label nullable, 1-60 chars; seeds null. |
| SEC-124 | 12 | Must | PASS | frontend/lib/wording/review.ts:86; frontend/components/StaffNotes/StaffNotes.test.tsx:59,166; backend/schemas/notes.py:19 | Hint and 2000-char limit in UI, API and DB. |
| SEC-125 | 12 | Must | PASS | database/schema.sql (CREATE TABLE public.users) | users holds email, display_name, password_hash, role, active, login/timestamps only. |
| SEC-126 | 12 | Must | PASS | backend/services/validation.py:344-345; tests/integration/api/test_sessions.py::test_withdrawn_resident | 422 RESIDENT_WITHDRAWN tested. |
| SEC-129 | 12 | Must | PASS | frontend/lib/wording/list.ts:64; frontend/lib/wording/chart.ts:186; backend/api/openapi.py:35 | 'prompt to check in, not a diagnosis' wording. |
| SEC-150 | 12 | Must | PASS | .github/dependabot.yml | pip /backend and npm /frontend weekly, github-actions / and docker /backend monthly. |
| SEC-151 | 12 | Must | PASS | .github/workflows/ci.yml:221; scripts/ci/audit_gate.py:43-51 | pip-audit over runtime+dev reqs (analytics deps pinned in backend reqs); waivers via SECURITY_EXCEPTIONS.md. Gate passes if pip-audit emits no JSON. |
| SEC-152 | 12 | Must | PASS | .github/workflows/ci.yml:224; scripts/ci/audit_gate.py:54-64 | npm audit --omit=dev, high/critical fail (CIC-019 form); D-159 waivers active to 2026-12-20. |
| SEC-153 | 12 | Should | PASS | .github/workflows/ci.yml:228-229 | bandit -r backend analytics -ll. |
| SEC-154 | 12 | Must | PASS | .github/workflows/*.yml (uses: only actions/* and docker/* major tags); ci.yml:15-16 | All workflows default contents: read; job-level write only where needed. |
| SEC-160 | 12 | Must | PENDING BLOCK 4 | specs/backlog/DEPLOYMENT_CHECKLIST.md:57,152 (B.09, J.01); docs/deployment.md:85 | PITR window to be recorded in Phase 10; regeneration from seeds available (database/seeds). |
| SEC-161 | 12 | Must | NOT APPLICABLE | specs/backlog/DEPLOYMENT_CHECKLIST.md:193 (N.03) | AWS cut-over item. |
| SEC-162 | 12 | Should | PENDING BLOCK 4 | specs/backlog/DEPLOYMENT_CHECKLIST.md:154 (J.03) | Restore drill needs hosted stack. |
| SEC-163 | 12 | Must | PENDING BLOCK 4 | docs/deployment.md:212; specs/backlog/DEPLOYMENT_CHECKLIST.md:145 (I.04) | Recovery procedure documented; demo requires a restore drill. |
| SEC-170 | 12 | Must | PENDING BLOCK 4 | docs/deployment.md:271-279; backend/cli.py:185 | Containment table complete in docs; 1-hour executability is a drill. |
| SEC-171 | 12 | Must | PASS | docs/deployment.md:281 | Reporting rule documented. |
| SEC-172 | 12 | Must | PASS | database/schema.sql (audit_logs ip, request_id); backend/core/logging.py:41; docs/deployment.md:283 | audit rows carry request_id/ip; every log record carries request_id. |
| SEC-173 | 12 | Should | PASS | docs/deployment.md:285 | Post-incident note rule documented (private space). |
| SEC-180 | 12 | Must | PASS | docs/deployment.md:289 | Governance documented. |
| SEC-181 | 12 | Must | PASS | docs/deployment.md:290; backend/jobs/ (nightly_run.py only) | No retention deletion job. |
| SEC-182 | 12 | Must | PASS | docs/deployment.md:291; backend/alembic/versions/0001_initial_schema.py:800-805 | Export rule documented; readonly role excludes credential columns. |
| SEC-183 | 12 | Must | PASS | docs/deployment.md:292 | Licence rule documented; no DAIC-WOZ data in repo. |
| SEC-184 | 12 | Must | PASS | docs/deployment.md:293; specs/business-requirements/REFERENCES.md | Only committed PDF is the PROSPERO record (allowed by TRD 18 / D-29); preprint by link. |

## Acceptance criteria verified by inspection

| AC | TRD | Status | Evidence | Note |
|---|---|---|---|---|
| AC-VIS-01 | 00 | PASS | tests/validation/test_harness.py::test_tier_a_matches_the_answer_key; tests/validation/test_harness.py::test_tier_b_matches_the_answer_key; tests/validation/test_r01_clean_control.py..test_r10_gradual_drift.py | All SRC-03 comparisons R01-R10, Tier A and B, test_v0_1 |
| AC-VIS-02 | 00 | PASS | frontend/tests/e2e/resident-list.spec.ts "E2E-03 heading, filter buttons, legend and status note", "E2E-04 rows in the default order..."; frontend/tests/e2e/helpers.ts:21 | Filters All (10)/Changed (2)/Needs attention (2)/Usual (6) and R09 row text asserted on DS-07 seed |
| AC-VIS-04 | 00 | PASS | tests/security/test_no_audio.py::test_audio_is_refused_everywhere; tests/contract/test_openapi_contract.py::test_no_audio_or_identity_properties; tests/security/test_static_scans.py::test_no_personal_or_audio_columns; tests/security/test_static_scans.py::test_no_forbidden_dependencies; CI ci.yml repo-hygiene "Forbidden terms" (:37-43) | Old facility name only in specs/ and docs/reports (excluded by CI grep); none in code |
| AC-VIS-07 | 00 | PASS | grep -rniE "diagnos\|severity\|risk score" frontend/app frontend/components frontend/lib: only "not a diagnosis" (lib/wording/list.ts:64, chart.ts:186); CI ci.yml:41-43 | Inspection. Note CI grep path frontend/lib/wording.ts misses the frontend/lib/wording/ directory |
| AC-VIS-08 | 00 | PASS | tests/unit/backend/core/test_config.py::test_cfg_06_production_refuses_test_profile; tests/unit/backend/core/test_config.py::test_cfg_06_process_exits_1_with_critical_log |  |
| AC-VIS-09 | 00 | PASS | git ls-files: no preprint PDF (only EchoWell_PROSPERO.pdf, SRC-08); specs/business-requirements/REFERENCES.md:7 links SRC-07 by URL and DOI | Inspection |
| AC-VIS-10 | 00 | PASS | tests/integration/api/test_ui_fixture_ds07.py::test_open_alarms_and_leaning_most; ::test_exactly_four_data_alerts; ::test_study_team_analytics; frontend/tests/e2e/review.spec.ts "FE-193 Summary facts..."; study-team.spec.ts "E2E-20 / FE-194..." | R09/R10 Not reviewed + 4 data problems + 281/267 of 300 asserted |
| AC-ARC-02 | 01 | PASS | tests/integration/test_schema_behaviour.py::test_ac_pgs_01_raw_sessions_update_fails_for_app; ::test_ac_pgs_02_raw_sessions_delete_and_truncate_fail_for_app |  |
| AC-ARC-03 | 01 | PASS | tests/integration/api/test_sessions.py::test_valid_record_is_stored_and_processed | 201, status_after_processing, one raw row, run trigger ingest status succeeded |
| AC-ARC-04 | 01 | PASS | tests/integration/test_cli_pipeline.py::test_rebuild_reproduces_identical_derived_tables; tests/validation/test_global_checks.py::test_vc_g12_determinism_and_rebuild; tests/validation/test_harness.py::test_tier_b_matches_the_answer_key |  |
| AC-ARC-05 | 01 | PASS | tests/integration/pipeline/test_runner_persistence.py::test_reviews_and_snooze_survive_a_rerun; backend/services/pipeline_persistence.py:9; tests/integration/test_schema_behaviour.py::test_reviews_and_notes_are_append_only | Ack survives full run (test); note retention by inspection (full run never deletes staff_notes) |
| AC-ARC-06 | 01 | PASS | backend/core/db.py:127-146 (sorted advisory locks); tests/integration/db/test_advisory_locks.py::test_lock_xact_many_takes_the_same_keys_as_lock_xact; tests/unit/backend/core/test_db.py::test_lock_residents_sorts_and_deduplicates; tests/integration/pipeline/test_concurrent_ingest.py::test_concurrent_posts_of_one_session_id | Inspection + lock-order tests; no test posts R02 and R03 concurrently (gap noted) |
| AC-ARC-07 | 01 | PASS | CI ci.yml job docker-build (:230-258); .github/workflows/e2e.yml:52 compose up --wait with backend /api/v1/health healthcheck (docker-compose.yml:44-49, postgres:16-alpine); tests/integration/api/test_health.py::test_tst_054_health_ok_with_database_up | E2E push run on 23e558b green |
| AC-ARC-08 | 01 | PASS | tests/contract/test_openapi_contract.py::test_no_audio_or_identity_properties |  |
| AC-ARC-10 | 01 | PASS | tests/validation/test_harness.py::test_ground_truth_never_changes_the_outputs; tests/integration/db/test_ground_truth_loader.py::test_refuses_outside_test_v0_1 |  |
| AC-ARC-11 | 01 | PASS | tests/integration/pipeline/test_runner_persistence.py::test_reviews_and_snooze_survive_a_rerun; backend/services/pipeline_persistence.py:56 (RESIDENT_KINDS excludes review_flagged_data_problem) | Review+snooze by test; flagged data alert untouched by reconcile (inspection) |
| AC-FR-01 | 02 | PASS | tests/validation/test_global_checks.py::test_vc_g01_status_totals; ::test_vc_g03_status_counts; ::test_vc_g09_day_ledger; tests/integration/api/test_ingest.py::test_src05_upload |  |
| AC-FR-02 | 02 | PASS | tests/validation/test_global_checks.py::test_vc_g04_resident_outcomes; tests/unit/analytics/test_cusum_engine.py::test_src05_alarms |  |
| AC-FR-03 | 02 | PASS | tests/validation/test_global_checks.py::test_vc_g05_baselines; ::test_vc_g06_scores |  |
| AC-FR-05 | 02 | PASS | tests/integration/api/test_sessions.py::test_repeat_session_id_is_a_duplicate; tests/validation/test_r04_duplicate_records.py::test_vc_r04_duplicate_records; tests/validation/test_invariance.py::test_vc_r04_inv_identical_without_the_copies | Repeat POST uses R09 record; R04 results unchanged via VC-R04/-INV |
| AC-FR-06 | 02 | PASS | tests/integration/api/test_ingest.py::test_record_errors_do_not_fail_the_batch; tests/unit/backend/services/test_validation.py::test_reject_rules; tests/integration/api/test_sessions.py::test_unknown_resident_is_rejected_and_stored | audio_quality_flag "bad" rejected invalid_enum into ingest_rejections (batch); single-POST 422 path tested with another reject |
| AC-FR-07 | 02 | PASS | frontend/tests/e2e/mutating.spec.ts "(1) E2E-18 save review on R09"; tests/integration/api/test_ui_fixture_ds07.py::test_after_a_review_of_r09; tests/integration/api/test_alerts.py::test_refusals (acknowledge 404, :255) |  |
| AC-FR-08 | 02 | PASS | tests/security/test_auth_matrix.py::test_every_cell; tests/integration/api/test_role_checks.py::test_every_matrix_cell |  |
| AC-FR-09 | 02 | PASS | frontend/tests/e2e/resident-chart.spec.ts "E2E-08 R09 from the list through Voice trends, Baseline and Check-in log" (:220-300), "FE-186 ... Check-in log" (R07 oldest log :107) |  |
| AC-FR-10 | 02 | PASS | frontend/tests/e2e/admissions.spec.ts "E2E-13 / FE-189 experimental note and empty state"; tests/integration/api/test_admissions.py::test_range_not_available |  |
| AC-FR-11 | 02 | PASS | specs/TRD/02_Functional_Requirements_Specification.md §4.28 (all 202 active FRs present, script) and §4.27/§4.29 (UC coverage by range) | Inspection; FR-226..228, 251..254, 331 covered only via §4.29 range statement |
| AC-FR-14 | 02 | PASS | tests/integration/api/test_ingest.py::test_legacy_file_is_refused |  |
| AC-NFR-02 | 03 | PENDING BLOCK 4 | tests/performance/test_pipeline_runtime.py::test_pipeline_on_src05_within_5_s (budget, ci.yml:50); ::test_src05_full_rebuild_within_30_s (e2e.yml performance job :155); tests/validation/test_global_checks.py::test_vc_g12_determinism_and_rebuild | 5 s, 1e-6 match and rebuild identity pass in CI; 30 s rebuild runs only in nightly job, no scheduled run yet |
| AC-NFR-03 | 03 | PASS | .github/workflows/ci.yml:48-49 (analytics 95, backend 85); frontend/vitest.config.ts:21 (lines 80) via ci.yml frontend test:coverage; CHECKPOINT_8 §5 rows 2,5 | 98 / 96 / 99.4 % |
| AC-NFR-05 | 03 | PENDING BLOCK 4 | tests/smoke/test_tls.py::test_tls_policy_api, ::test_tls_policy_frontend; tests/security/test_transport_and_secrets.py::test_every_database_url_needs_sslmode_require; tests/unit/backend/core/test_config.py::test_staging_requires_sslmode_but_local_does_not | sslmode refusal PASS in tests; TLS scan of staging needs hosted deploy |
| AC-NFR-06 | 03 | PENDING BLOCK 4 | specs/backlog/DEPLOYMENT_CHECKLIST.md:193 (N.03 RDS KMS, backups), :195 (N.05 Secrets Manager) | AWS checklist part present; provider evidence for interim DB is a Block 4 platform check |
| AC-NFR-07 | 03 | PENDING BLOCK 4 | render.yaml:67,111 (DATA_SOURCE_LABEL test/synthetic) | Hosted DB rows need staging/production |
| AC-NFR-08 | 03 | PASS | tests/integration/api/test_auth.py::test_logs_hold_no_password_token_or_email; tests/integration/api/test_sessions.py::test_logs_carry_no_feature_value_or_key; tests/security/test_data_minimisation.py::test_responses_and_logs_hold_study_ids_only; backend/core/logging.py:28 | Note creation not log-captured; note_service logs nothing and redaction covers note/body keys (inspection) |
| AC-NFR-10 | 03 | PENDING BLOCK 4 | .github/workflows/e2e.yml:29,70 (3 browsers on schedule only); frontend/playwright.config.ts:16-19; frontend/tests/e2e/helpers.ts:22 ("CT" times on UTC runner) | Chromium green on 23e558b; FF/WebKit nightly not yet run; no explicit Europe/London run (UTC runner shows CT) |
| AC-NFR-12 | 03 | PASS | tests/validation/test_harness.py::test_ground_truth_never_changes_the_outputs; tests/contract/test_openapi_contract.py::test_generated_equals_committed; ci.yml openapi-contract job |  |
| AC-FE-01 | 04 | PASS | .github/workflows/ci.yml frontend job (:180-203, NODE_VERSION 20): npm ci, lint, typecheck, format:check, test:coverage, build | CI green on 23e558b |
| AC-FE-04 | 04 | PASS | frontend/tests/e2e/resident-chart.spec.ts "E2E-11 Needs attention R08"; frontend components read meta.baseline_n (e.g. app/(protected)/residents/[residentCode]/log/page.tsx:71), no hard-coded 16 | Production "of 30" by inspection (N from meta), plus wording tests with N=30 |
| AC-FE-05 | 04 | PASS | frontend/tests/e2e/auth.spec.ts "FE-188 redirect to /login without a token and back to next after sign-in", "FE-188 an external next value is rejected" |  |
| AC-FE-07 | 04 | PENDING BLOCK 4 | netlify.toml; tests/unit/test_netlify_config.py::test_header_block_is_byte_identical_to_trd12_excerpt; ::test_connect_src_is_exactly_self_and_the_two_render_origins | Repo headers verified; staging response headers need hosted deploy |
| AC-API-01 | 05 | PASS | tests/integration/api/test_ingest.py::test_src05_upload; tests/performance/test_api_latency.py::test_ingest_src05_accepted_and_processed | 202, 283/0/2, run succeeded (30 s bound in budget test, ci.yml:50) |
| AC-API-03 | 05 | PASS | tests/integration/api/test_ui_fixture_ds07.py::test_resident_chart_r09; ::test_devices; tests/integration/api/test_residents.py::test_checkin_log; ::test_detail |  |
| AC-API-04 | 05 | PASS | tests/validation/test_r09_step_change.py::test_vc_r09_step_change (Tier B via /scores, tests/validation/tier_b.py:88); tests/integration/api/test_ui_fixture_ds07.py::test_open_alarms_and_leaning_most |  |
| AC-API-08 | 05 | PASS | tests/integration/api/conftest.py:144 (check_response hook on every integration response); tests/contract/response_validation.py:118; tests/integration/api/test_http_middleware.py::test_errors_carry_the_request_id_and_problem_shape | 429/500 cases in test_rate_limits / test_unhandled_exception_is_a_generic_500 |
| AC-API-10 | 05 | PASS | tests/security/test_auth_matrix.py::test_pipeline_run_key_scopes; ::test_every_cell |  |
| AC-API-11 | 05 | PASS | tests/integration/pipeline/test_nightly_run.py::test_one_run_per_local_night_across_dst; tests/integration/api/test_pipeline.py::test_scheduler_key_runs_nightly_once_per_local_date |  |
| AC-API-12 | 05 | PASS | tests/integration/api/test_health.py::test_tst_054_health_ok_with_database_up; ::test_tst_054_health_degraded_with_database_down |  |
| AC-API-15 | 05 | PASS | tests/integration/api/test_ui_fixture_ds07.py::test_after_a_review_of_r09; tests/integration/api/test_alerts.py::test_reviews; tests/integration/pipeline/test_runner_persistence.py::test_reviews_and_snooze_survive_a_rerun |  |
| AC-API-18 | 05 | PASS | tests/integration/api/test_http_middleware.py::test_meta_uses_the_latest_succeeded_run (:217-218); tests/contract/response_validation.py:135-149 |  |
| AC-ANL-04 | 07 | PASS | CI ci.yml backend-lint "lint-imports"; pyproject.toml:40-43 (forbidden backend, sqlalchemy, psycopg, fastapi, httpx, requests); tests/unit/backend/test_import_boundary.py::test_analytics_imports_are_allowed |  |
| AC-ANL-07 | 07 | PENDING BLOCK 4 | tests/performance/test_pipeline_runtime.py::test_pipeline_on_src05_within_5_s (ci.yml:50); ::test_ds08_full_rebuild_within_120_s (e2e.yml performance job) | 5 s passes in CI; DS-08 120 s only in nightly performance job, no scheduled run yet |
| AC-ANL-12 | 07 | PASS | tests/unit/backend/core/test_config.py::test_cfg_06_production_refuses_test_profile; ::test_tst_038_production_refuses_pipeline_as_of |  |
| AC-ANL-14 | 07 | PASS | tests/integration/test_schema_behaviour.py::test_ac_pgs_14_ground_truth_only_through_readonly; tests/integration/db/test_grants.py::test_app_privileges_are_exactly_section_4_8 |  |
| AC-BSC-07 | 08 | PASS | tests/unit/analytics/test_zscore_calculator.py::test_zero_spread_gives_zero; analytics/pipeline.py:238-241 (one zero_spread warning per epoch and feature) | z=0 tested (pause_fraction); warning by inspection only |
| AC-BSC-08 | 08 | PASS | tests/integration/pipeline/test_runner_persistence.py::test_late_record_keeps_frozen_baselines; tests/validation/test_invariance.py::test_vc_r10_frz_frozen_baseline; tests/unit/analytics/test_pipeline.py::test_frozen_baselines_win_and_mismatch_warns |  |
| AC-CUS-01 | 09 | PASS | tests/validation/test_global_checks.py::test_vc_g06_scores |  |
| AC-CUS-02 | 09 | PASS | tests/unit/analytics/test_cusum_engine.py::test_src05_alarms; tests/validation/test_r09_step_change.py; tests/validation/test_r10_gradual_drift.py |  |
| AC-CUS-03 | 09 | PASS | tests/validation/test_global_checks.py::test_vc_g10_alerts; tests/unit/analytics/test_alert_generator.py::test_src05_alerts_and_leaning_most |  |
| AC-CUS-04 | 09 | PASS | tests/unit/analytics/test_cusum_engine.py::test_tally_and_states; ::test_epochs_have_their_own_tally | Equivalent vectors (6.0->5.5 rings; negative resets to 0, state stays on); literal [6,-10,0] case absent |
| AC-CUS-05 | 09 | PASS | tests/unit/analytics/test_pipeline.py::test_dropping_duplicates_changes_nothing_else; tests/validation/test_invariance.py::test_vc_r04_inv_identical_without_the_copies; tests/validation/test_r02_missing_days.py; test_r03_set_aside_sessions.py; test_r05_possible_other_speaker.py |  |
| AC-CUS-07 | 09 | PASS | tests/unit/analytics/test_alert_generator.py::test_one_event_per_ringing_epoch_with_closure_facts; tests/unit/analytics/test_cusum_engine.py::test_epochs_have_their_own_tally; backend/services/pipeline_persistence.py:356-357,370-371 | Closure "epoch ended" persisted by inspection; no single integration test of the whole scenario |
| AC-CUS-09 | 09 | PASS | tests/unit/analytics/test_data_alerts.py::test_src05_exactly_four_alerts_in_order; tests/unit/analytics/test_alert_generator.py::test_src05_alerts_and_leaning_most; tests/integration/pipeline/test_runner_persistence.py::test_alerts_endpoint_leaning_most |  |
| AC-CUS-11 | 09 | PASS | tests/integration/api/test_ui_fixture_ds07.py::test_study_team_analytics; tests/unit/backend/test_db_inspection.py::test_ground_truth_is_not_referenced_by_the_pipeline_or_cli; tests/validation/test_answer_key_integrity.py::test_no_production_code_reads_the_answer_key; tests/integration/test_schema_behaviour.py::test_ac_pgs_14_ground_truth_only_through_readonly |  |
| AC-ING-02 | 10 | PASS | tests/validation/test_global_checks.py::test_vc_g01_status_totals; ::test_vc_g09_day_ledger; tests/unit/analytics/test_day_ledger.py::test_src05_ledger |  |
| AC-ING-07 | 10 | PASS | tests/integration/test_schema_behaviour.py::test_ac_pgs_01_raw_sessions_update_fails_for_app; ::test_ac_pgs_02_raw_sessions_delete_and_truncate_fail_for_app |  |
| AC-UX-01 | 11 | PASS | frontend/tests/e2e/resident-list.spec.ts "FE-185 data bar, nav badge and study-ID link", "E2E-03 ...", "E2E-04 rows in the default order with pills, texts and last check-ins" |  |
| AC-UX-02 | 11 | PASS | frontend/tests/e2e/resident-list.spec.ts "E2E-05 filter Changed then Needs attention", "E2E-06 Usual filter kept...", "E2E-03/UX-261 ... from the URL" (?show= asserted :84-133) |  |
| AC-UX-03 | 11 | PASS | frontend/tests/e2e/study-team.spec.ts expectDevices (:20-64, D08 12 days :63); frontend/tests/pages/study.test.tsx:196 |  |
| AC-UX-08 | 11 | PASS | grep of frontend/app, components, lib for UX-161 stems, old facility name, "[Facility name]": none except "not a diagnosis"; ci.yml:37-43; tests/unit/backend/core/test_config.py::test_forbidden_facility_name_rejected | Inspection; CI grep covers only diagnoses\|severity |
| AC-UX-10 | 11 | PASS | frontend/lib/wording/common.ts:20 (no Test data sentence off test_v0_1); N from meta.baseline_n (no hard-coded 16 in frontend source); frontend/tests/unit/wording-chart.test.ts:102 | Inspection plus wording tests |
| AC-UX-11 | 11 | PASS | frontend/tests/e2e/review.spec.ts "FE-193 review panels of R09 and R10 (TRD 11 §4.17.5)"; frontend/tests/e2e/mutating.spec.ts "(1) E2E-18 save review on R09" (:84-95, pill :31) |  |
| AC-UX-12 | 11 | PASS | frontend/tests/e2e/study-team.spec.ts "E2E-20 / FE-194 ...", "E2E-21 / FE-194 clinician gets the access-denied state on /study"; frontend/tests/pages/study.test.tsx:265 (production profile) |  |
| AC-SEC-06 | 12 | PASS | tests/integration/test_cli_credentials.py::test_create_api_key_prints_the_key_once_and_stores_its_hash; ::test_revoke_api_key; tests/security/test_api_keys.py::test_revoked_key_is_invalid |  |
| AC-SEC-07 | 12 | PENDING BLOCK 4 | netlify.toml; tests/unit/test_netlify_config.py::test_permissions_policy_denies_microphone_and_camera_and_hsts_is_set; tests/smoke/test_tls.py::test_tls_policy_api | Repo config verified; staging headers/TLS 1.1 rejection need hosted deploy |
| AC-SEC-08 | 12 | PASS | tests/unit/backend/core/test_config.py::test_short_jwt_secret_rejected_everywhere; ::test_cfg_06_production_refuses_test_profile; ::test_tst_038_production_refuses_pipeline_as_of; tests/unit/test_env_templates.py::test_ac_env_02_production_url_without_sslmode_refused |  |
| AC-SEC-11 | 12 | PENDING BLOCK 4 | specs/backlog/DEPLOYMENT_CHECKLIST.md:203 (N.13 signed item); render.yaml:67,111; frontend/lib/wording/common.ts:22 | Checklist item present; interim stack header is a hosted check |
| AC-TST-03 | 13 | PASS | tests/validation (CI ci.yml:45); tests/validation/test_harness.py::test_a_skipped_validation_test_fails_the_session; docs/reports/ALGORITHM_VALIDATION_REPORT.md:6 "Overall: PASS" |  |
| AC-TST-04 | 13 | PASS | tests/contract/*; tests/contract/test_openapi_contract.py::test_generated_equals_committed; ci.yml openapi-contract job (api-types.ts up to date step) |  |
| AC-TST-06 | 13 | PASS | .github/workflows/ci.yml:48-49; frontend/vitest.config.ts:21; CHECKPOINT_8 §5 rows 2,5 | 98 / 96 / 99.4 % |
| AC-TST-07 | 13 | PASS | frontend/tests/e2e/*.spec.ts (E2E-01..E2E-21 all present); frontend/tests/e2e/a11y.spec.ts "FE-190 ... no serious or critical violations"; e2e.yml playwright green on 23e558b (Chromium) |  |
| AC-TST-10 | 13 | PENDING BLOCK 4 |  | MVP-01..15 on the release candidate is a Block 4 release check |
| AC-TST-11 | 13 | PENDING BLOCK 4 |  | Demo steps 4-5 (TST-180, TST-181) on the demo environment |
| AC-TDV-01 | 14 | PASS | tests/validation/test_r01_clean_control.py .. test_r10_gradual_drift.py (Tier A and B parametrised) |  |
| AC-TDV-03 | 14 | PASS | tests/validation/test_invariance.py::test_vc_r04_inv_identical_without_the_copies; ::test_vc_r10_frz_frozen_baseline |  |
| AC-TDV-06 | 14 | PASS | docs/reports/ALGORITHM_VALIDATION_REPORT.md:6 "Overall: PASS" (regenerated on 23e558b) | Re-run on the Block 4 release candidate still due |
| AC-TDV-07 | 14 | PASS | tests/integration/api/test_ui_fixture_ds07.py::test_resident_list; ::test_resident_list_sorts |  |
| AC-TDV-08 | 14 | PASS | tests/integration/api/test_ingest.py::test_legacy_file_is_refused |  |
| AC-TDV-09 | 14 | PASS | tests/validation/test_robustness_check.py::test_publish_fills_section_7_only; ::test_not_part_of_the_gating_selection; e2e.yml nightly-validation robustness step (informational) |  |
| AC-TDV-10 | 14 | PASS | tests/integration/api/test_ui_fixture_ds07.py::test_open_alarms_and_leaning_most; ::test_exactly_four_data_alerts; frontend/tests/e2e/review.spec.ts "E2E-17 Study team data problems (researcher)" |  |
| AC-TDV-11 | 14 | PASS | tests/integration/api/test_ui_fixture_ds07.py::test_study_team_analytics; tests/validation/test_ui_fixture_recompute.py::test_study_team_figures_match_the_answer_key; frontend/tests/e2e/study-team.spec.ts "E2E-20 / FE-194 ..." |  |
| AC-DEP-01 | 15 | PASS | README.md:13; docs/deployment.md:39; e2e.yml:52-56 (compose up + seed in CI, playwright job 6 min); frontend/tests/e2e/resident-list.spec.ts E2E-03/E2E-04 | Procedure works (CI, CHECKPOINT_8 §5 row 11); 10-min timing on an 8 GB laptop not recorded |
| AC-DEP-02 | 15 | PASS | tests/integration/test_cli_seed.py::test_production_refuses_seed_and_reset | Exit 2, all tables unchanged (CLI invoked directly, not via compose exec) |
| AC-DEP-03 | 15 | PENDING BLOCK 4 | .github/workflows/deploy-staging.yml; render.yaml | deploy-staging run on 23e558b failed waiting for staging (not provisioned yet) |
| AC-DEP-04 | 15 | PENDING BLOCK 4 | .github/workflows/deploy-production.yml | No production release yet |
| AC-DEP-05 | 15 | PENDING BLOCK 4 |  | Production database check |
| AC-DEP-06 | 15 | PENDING BLOCK 4 | docs/deployment.md | Staging failure drill |
| AC-DEP-07 | 15 | PENDING BLOCK 4 | docs/deployment.md:214 | Rollback rehearsal (DEP-085) |
| AC-DEP-08 | 15 | PENDING BLOCK 4 | docs/deployment.md | Restore drill |
| AC-DEP-09 | 15 | PENDING BLOCK 4 | docs/deployment.md | Demo fallback rehearsal |
| AC-DEP-11 | 15 | NOT APPLICABLE |  | AWS cut-over (DEP-112..117) is post-MVP; Neon content check is AC-TPS-04 (Block 4) |
| AC-CIC-02 | 16 | PASS | .github/workflows/ci.yml:26-29 repo-hygiene "No audio files"; tests/unit/test_repository_layout.py::test_tst_007_no_audio_files_tracked | Inspection: .wav matches the pattern |
| AC-CIC-03 | 16 | PASS | .github/workflows/ci.yml openapi-contract job; tests/contract/test_openapi_contract.py::test_generated_equals_committed |  |
| AC-CIC-04 | 16 | PASS | .github/workflows/ci.yml:58-63 PR-title regex | Regex run locally: "Updated stuff" fails, "feat(api): add device panel endpoint" passes |
| AC-CIC-05 | 16 | PASS | gh api runs: CI on 23e558b 17:01:18-17:06:41 (5.4 min); ci.yml:132-138 backend-reports with ALGORITHM_VALIDATION_REPORT.md and validation_results.json | Report shows 10/10 residents PASS |
| AC-CIC-06 | 16 | PASS | grep -r "secrets\." .github/workflows: STAGING_* x5 in deploy-staging.yml only; RENDER_API_KEY, NETLIFY_AUTH_TOKEN in deploy-production.yml only | Inspection matches the list |
| AC-CIC-07 | 16 | PENDING BLOCK 4 | .github/workflows/deploy-staging.yml; .github/workflows/deploy-production.yml | deploy-staging on 23e558b failed (staging not provisioned); production release is Block 4 |
| AC-CIC-09 | 16 | PENDING BLOCK 4 | .github/workflows/e2e.yml schedule | 3 consecutive green nightly runs; none yet |
| AC-CIC-10 | 16 | PENDING BLOCK 4 | .github/workflows/e2e.yml:112-163 performance job | No scheduled/dispatched e2e.yml run yet; local budget runs in CHECKPOINT_8 §5 rows 3-4 |
| AC-LOG-01 | 17 | PASS | tests/unit/backend/core/test_logging.py::test_json_lines_have_the_required_keys; backend/core/logging.py:146-162; tests/integration/api/conftest.py:305-310 | Formatter always emits the 7 keys; no suite-wide every-line check |
| AC-LOG-03 | 17 | PASS | tests/integration/api/test_sessions.py::test_logs_carry_no_feature_value_or_key (:333 one ingest_record_rejected) |  |
| AC-LOG-04 | 17 | PASS | tests/integration/api/test_http_middleware.py::test_request_id_is_echoed_or_generated; ::test_errors_carry_the_request_id_and_problem_shape; tests/unit/backend/core/test_logging.py::test_request_id_acceptance |  |
| AC-LOG-07 | 17 | PASS | tests/integration/pipeline/test_nightly_run.py::test_missed_night_is_reported; frontend/tests/pages/admin.test.tsx:73-89 ("Nightly run missing for Oct 31") |  |
| AC-LOG-09 | 17 | PASS | tests/unit/backend/core/test_monitoring.py::test_empty_dsn_logs_error_and_never_calls_transport; ::test_dsn_is_ignored_outside_staging_and_production | Transport never called with empty DSN (not a network-isolated forced 500) |
| AC-LOG-10 | 17 | PASS | tests/integration/api/test_health.py::test_tst_054_health_degraded_with_database_down; backend/core/db.py:66,182-186 (5 s connect, 2 s ping) |  |
| AC-GIT-03 | 18 | PASS | git ls-files specs/business-requirements (flowchart docx, PROSPERO pdf, xlsx, REFERENCES.md); REFERENCES.md:7 SRC-07 URL + DOI | PROSPERO record allowed by TRD 18:431 |
| AC-GIT-04 | 18 | PASS | git grep the SRC-07 preprint PDF 23e558b -- specs/TRD docs: only the AC-GIT-04 text itself | On HEAD (cp9) docs/reports/TRD_Implementation_Audit.md quotes the filename in a finding |
| AC-GIT-05 | 18 | PASS | .github/workflows/ci.yml backend-lint (ruff check, ruff format --check, mypy) and frontend (lint, typecheck); CI green on 23e558b; CHECKPOINT_8 §5 row 6 |  |
| AC-GIT-08 | 18 | PENDING BLOCK 4 | gh api repo security_and_analysis not readable (null); ci.yml gitleaks step | Platform setting (GIT-081) |
| AC-TPS-01 | 22 | PENDING BLOCK 4 | docs/deployment.md:61-69 | Table exists; owners/MFA/verified limits with dates recorded in Block 4 (TPS-005/006) |
| AC-TPS-02 | 22 | PASS | frontend/tests/e2e/privacy.spec.ts "FE-192 only the frontend origin and the API origin are contacted; no audio or video" (routes incl. /residents, /residents/R09) |  |
| AC-TPS-03 | 22 | PASS | tests/security/test_static_scans.py::test_no_forbidden_dependencies (FORBIDDEN_PACKAGES :28-43 LLM, analytics, speech, boto3); ci.yml:45-55 |  |
| AC-TPS-04 | 22 | PENDING BLOCK 4 |  | Interim Neon project contents |
| AC-TPS-05 | 22 | NOT APPLICABLE | docs/deployment.md:297; specs/backlog/DEPLOYMENT_CHECKLIST.md N.02 | Precondition for the first real record on AWS (post-MVP cut-over); SENTRY_DSN decision is TPS-061 (Block 4) |
| AC-TPS-06 | 22 | PASS | docs/api_reference/openapi.json: request bodies only application/json, and /ingest multipart file contentMediaType text/csv; tests/security/test_no_audio.py::test_audio_inside_a_multipart_upload_is_refused |  |
| AC-RAQ-01 | 24 | PASS | specs/TRD/24_Risk_Assumptions_and_Open_Questions.md:79-112 (script: 32 OQ rows, 8 cells, none empty) |  |
| AC-RAQ-02 | 24 | PASS | specs/TRD/24_Risk_Assumptions_and_Open_Questions.md:116-126 (script: 8 ASM rows, no empty cell) |  |
| AC-RAQ-03 | 24 | PASS | specs/TRD/24_Risk_Assumptions_and_Open_Questions.md:131-150 (script: 17 RSK rows, L/I in {L,M,H}, no empty cell) |  |
| AC-RAQ-04 | 24 | PASS | script over specs/TRD/*.md: every OQ-, ASM-, RSK-, D-nn reference is defined in TRD 24 | D-152 unused gap (harmless, DCA-14) |
| AC-RAQ-05 | 24 | PASS | docs/reports/TRD_VALIDATION_REPORT.md §4, §6.5; specs/architecture/Deployment_Architecture.md:3 (SRC-01 updated for D-153) | Checked at TRD validation; later decisions not formally re-validated |
| AC-RAQ-06 | 24 | PASS | tests/validation (pass on 23e558b); tests/validation/test_global_checks.py::test_vc_g08_parameters; docs/reports/ALGORITHM_VALIDATION_REPORT.md:6 |  |
| AC-RAQ-07 | 24 | PENDING BLOCK 4 | frontend/lib/wording/review.ts:67 (OQ-05 note); frontend/lib/wording/common.ts:6 (OQ-12 marker); frontend/tests/e2e/review.spec.ts:23 | Present in the build; "deployed UI" check is Block 4 |
| AC-AGT-03 | 25 | PASS | git grep -niE "openai\|anthropic\|langchain" and -i old facility name 23e558b -- frontend backend analytics: 0 matches |  |
| AC-AGT-04 | 25 | PENDING BLOCK 4 | tests/validation pass on 23e558b (full run); docs/reports/CHECKPOINT_6_VALIDATION.md:11 | Repo-side passes; run on the Block 4 deployed commit pending |
| AC-AGT-07 | 25 | PENDING BLOCK 4 | all TRD 25 §4.6 Phase 2-9 reports exist at 23e558b (docs/reports/*_IMPLEMENTATION_REPORT.md, ALGORITHM_VALIDATION_REPORT.md, ...) | DEPLOYMENT_REPORT.md is Block 4; FINAL_IMPLEMENTATION_AUDIT.md (cp9) not yet on the branch |
| AC-AGT-08 | 25 | PASS | specs/TRD/24 §4.2, §4.6 (script: D-01..D-170 and OQ-01..32 all cells filled); no undefined OQ/D reference in docs, code, tests |  |
| AC-AGT-10 | 25 | PENDING BLOCK 4 | .github/workflows/deploy-staging.yml:17 (seed test_v0_1); tests/fixtures/seeds/demo_overlay | Repo side uses synthetic data only; DEPLOYMENT_REPORT.md statement is Block 4 |
