"""Seed the 46 config_parameters rows (23 keys x 2 profiles).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-26

The SQL is TRD 20 §4.11 verbatim (PGS-024, PGS-025, DB-055; FEAT-009). This migration is never
edited to change a parameter: later changes go through the `set-config` operator command (FR-229,
D-69), and the test_v0_1 values are never changed to make a test pass (AGT-008).
"""

from __future__ import annotations

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

CONFIG_SEED = r"""
INSERT INTO config_parameters (profile, key, value, description)
SELECT p.profile, v.key, v.value, v.description
FROM (VALUES ('production'), ('test_v0_1')) AS p(profile)
CROSS JOIN (VALUES
  ('facility_tz',                 '"America/Chicago"'::jsonb, 'IANA time zone used for morning classification and the day ledger'),
  ('noise_limit_dbfs',            '-40.0'::jsonb,             'Set aside if mic_noise_level_dbfs is above this limit (dBFS)'),
  ('min_speech_s',                '1.0'::jsonb,               'Set aside if speech_duration_s is below this minimum (seconds)'),
  ('screen_min_n',                '5'::jsonb,                 'Prior usable sessions in the epoch required before the speaker screen runs'),
  ('screen_f0_z',                 '4.0'::jsonb,               'Speaker screen: |z| of mean_f0_hz at or above this value'),
  ('screen_other_z',              '3.0'::jsonb,               'Speaker screen: |z| threshold for the 7 composite features'),
  ('screen_other_count',          '2'::jsonb,                 'Speaker screen: minimum count of composite features at or above screen_other_z'),
  ('mad_scale',                   '1.4826'::jsonb,            'Robust spread = MAD x mad_scale'),
  ('pause_floor',                 '0.5'::jsonb,               'Spread floor for number_of_pauses'),
  ('composite_floor',             '0.1'::jsonb,               'Spread floor for the composite baseline'),
  ('cusum_k',                     '0.5'::jsonb,               'CUSUM reference value k'),
  ('cusum_h',                     '5.0'::jsonb,               'CUSUM alarm threshold h (UI alarm line 5.0)'),
  ('morning_cutoff_hour',         '12'::jsonb,                'Session is morning if its local hour is below this value'),
  ('morning_offsets',             '{"loudness_dbfs": -1.5, "total_phrase_duration_s": 0.10, "speech_rate_syl_per_s": -0.12, "articulation_rate_syl_per_s": -0.10, "number_of_pauses": 0, "pause_fraction": 0.010, "voiced_fraction": -0.020, "mean_f0_hz": 0, "f0_variability_st": 0, "jitter_local_pct": 0, "shimmer_local_pct": 0, "hnr_db": 0, "cpps_db": 0, "alpha_ratio_db": 0, "hammarberg_index_db": 0, "mfcc1": 0, "mfcc2": 0, "mfcc3": 0, "mfcc4": 0}'::jsonb,
                                                              'Configured morning offset per feature; adjusted = raw - offset for morning sessions (estimation deferred, OQ-09)'),
  ('shared_device_min_residents', '2'::jsonb,                 'Minimum residents on one device for the missing_device_gap rule')
) AS v(key, value, description);

INSERT INTO config_parameters (profile, key, value, description) VALUES
  ('production', 'baseline_n', '30'::jsonb, 'Usable sessions that form and freeze a baseline (owner decision D-OWNER-2)'),
  ('test_v0_1',  'baseline_n', '16'::jsonb, 'Build/test only: usable sessions that form and freeze a baseline in the 30-day test set (SRC-03)');

-- Alert review and data-alert parameters (contract sections 19/20; provisional, OQ-24, OQ-25)
INSERT INTO config_parameters (profile, key, value, description)
SELECT p.profile, v.key, v.value, v.description
FROM (VALUES ('production'), ('test_v0_1')) AS p(profile)
CROSS JOIN (VALUES
  ('data_alert_baseline_stalled_enabled', 'true'::jsonb, 'Raise baseline_stalled data alerts (forming and days since epoch start >= baseline_n)'),
  ('data_alert_set_aside_fraction',       '0.20'::jsonb, 'high_set_aside data alert when set_aside / received >= this in 30 days (received >= 10)'),
  ('data_alert_device_silent_days',       '2'::jsonb,    'Consecutive silent days on a single-resident device that raise a device_silent data alert'),
  ('alert_snooze_hours',                  '24'::jsonb,   'Hours added by "Remind me in 24 h" (alerts.snoozed_until)'),
  ('review_explanations',
   '[{"code": "cold_cough_sore_throat", "label": "Cold, cough or sore throat"}, {"code": "dental_dentures", "label": "Dental problem or dentures out"}, {"code": "medication_change", "label": "New or changed medication"}, {"code": "poor_sleep_unusual_day", "label": "Poor sleep or unusual day"}, {"code": "room_device_moved", "label": "Room or device moved"}]'::jsonb,
   'Checklist "Anything that could explain it?" on the alert review form (codes stored in alert_reviews.explanations)')
) AS v(key, value, description);

-- Ingest settings (lead decision 18 Oct 2026; read by the ingestion service, TRD 10 ING-013, ING-016)
INSERT INTO config_parameters (profile, key, value, description)
SELECT p.profile, v.key, v.value, v.description
FROM (VALUES ('production'), ('test_v0_1')) AS p(profile)
CROSS JOIN (VALUES
  ('supported_schema_versions', '["0.1"]'::jsonb, 'Accepted values of schema_version; others are rejected (unsupported_schema_version)'),
  ('feature_name_map',
   '{"schema_version": "schema_version", "session_id": "session_id", "resident_id": "resident_id", "device_id": "device_id", "timestamp_utc": "timestamp_utc", "mic_noise_level_dbfs": "mic_noise_level_dbfs", "audio_quality_flag": "audio_quality_flag", "extraction_software_version": "extraction_software_version", "device_firmware_version": "device_firmware_version", "speech_duration_s": "speech_duration_s", "phrase_id": "phrase_id", "loudness_dbfs": "loudness_dbfs", "total_phrase_duration_s": "total_phrase_duration_s", "speech_rate_syl_per_s": "speech_rate_syl_per_s", "articulation_rate_syl_per_s": "articulation_rate_syl_per_s", "number_of_pauses": "number_of_pauses", "pause_fraction": "pause_fraction", "voiced_fraction": "voiced_fraction", "mean_f0_hz": "mean_f0_hz", "f0_variability_st": "f0_variability_st", "jitter_local_pct": "jitter_local_pct", "shimmer_local_pct": "shimmer_local_pct", "hnr_db": "hnr_db", "cpps_db": "cpps_db", "alpha_ratio_db": "alpha_ratio_db", "hammarberg_index_db": "hammarberg_index_db", "mfcc1": "mfcc1", "mfcc2": "mfcc2", "mfcc3": "mfcc3", "mfcc4": "mfcc4"}'::jsonb,
   'External field name -> canonical name (identity for the 11 record fields and 19 features of schema 0.1; OQ-03)')
) AS v(key, value, description);
"""

SEEDED_KEYS = (
    "alert_snooze_hours",
    "baseline_n",
    "composite_floor",
    "cusum_h",
    "cusum_k",
    "data_alert_baseline_stalled_enabled",
    "data_alert_device_silent_days",
    "data_alert_set_aside_fraction",
    "facility_tz",
    "feature_name_map",
    "mad_scale",
    "min_speech_s",
    "morning_cutoff_hour",
    "morning_offsets",
    "noise_limit_dbfs",
    "pause_floor",
    "review_explanations",
    "screen_f0_z",
    "screen_min_n",
    "screen_other_count",
    "screen_other_z",
    "shared_device_min_residents",
    "supported_schema_versions",
)


def upgrade() -> None:
    op.execute(CONFIG_SEED)


def downgrade() -> None:
    # The keys are this module's constants, not input.
    keys = ", ".join(f"'{key}'" for key in SEEDED_KEYS)
    statement = f"DELETE FROM config_parameters WHERE profile IN ('production', 'test_v0_1') AND key IN ({keys})"  # noqa: S608
    op.execute(statement)
