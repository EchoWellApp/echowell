"""Initial schema: enums, trigger functions, the 24 tables, indexes, triggers and grants.

Revision ID: 0001
Revises: -
Create Date: 2026-10-26

The SQL is copied verbatim from TRD 20 §4.2 (extension check only), §4.4-§4.8 (TRD 20 §8 migration
layout; FEAT-008..FEAT-013). Extensions, roles and database settings are provisioning, never Alembic
(TRD 24 D-72): this migration only checks the extensions and its downgrade never drops them.
"""

from __future__ import annotations

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# TRD 20 §4.2: verify the provisioning step ran (PGS-002).
EXTENSION_CHECK = r"""
DO $$
BEGIN
  IF (SELECT count(*) FROM pg_extension WHERE extname IN ('pgcrypto', 'btree_gist')) < 2 THEN
    RAISE EXCEPTION 'EchoWell needs extensions pgcrypto and btree_gist; run the provisioning step as the database owner or superuser first (TRD 15 §4.2/§4.4, TRD 20 §4.2)';
  END IF;
END
$$;
"""

# TRD 20 §4.4: the 15 enumerated types (PGS-005).
ENUM_TYPES = r"""
CREATE TYPE resident_cohort     AS ENUM ('longitudinal', 'new_admission');
CREATE TYPE resident_status     AS ENUM ('active', 'withdrawn');
CREATE TYPE ingest_source       AS ENUM ('api_single', 'api_batch', 'csv_upload', 'seed');
CREATE TYPE session_status      AS ENUM ('usable', 'set_aside', 'quarantined', 'duplicate');
CREATE TYPE day_status          AS ENUM ('checked_in', 'missing_resident', 'missing_device_gap');
CREATE TYPE alarm_state         AS ENUM ('off', 'rings', 'on');
CREATE TYPE alert_status        AS ENUM ('open', 'acknowledged', 'closed');
CREATE TYPE note_type           AS ENUM ('observation', 'action_taken', 'follow_up');
CREATE TYPE pipeline_trigger    AS ENUM ('ingest', 'nightly', 'manual', 'test');
CREATE TYPE pipeline_run_status AS ENUM ('running', 'succeeded', 'failed');
CREATE TYPE user_role           AS ENUM ('admin', 'clinician', 'researcher');
CREATE TYPE actor_type          AS ENUM ('user', 'api_key', 'system');
CREATE TYPE review_outcome      AS ENUM ('no_concern', 'known_cause', 'referred', 'data_problem');
CREATE TYPE data_alert_kind     AS ENUM ('baseline_stalled', 'possible_other_speaker', 'high_set_aside', 'device_silent',
                                         'review_flagged_data_problem');
CREATE TYPE data_alert_status   AS ENUM ('open', 'resolved');
"""

# TRD 20 §4.5: set_updated_at() and reject_mutation() (PGS-018..PGS-020).
TRIGGER_FUNCTIONS = r"""
CREATE FUNCTION set_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END
$$;

-- Rejects UPDATE, DELETE and TRUNCATE on append-only tables.
-- Single escape hatch: role echowell_migrator with session setting echowell.allow_purge = 'on'
-- (used only by the IRB withdrawal purge, PGS-019; the test-database reset drops and recreates the schema instead).
CREATE FUNCTION reject_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF current_user = 'echowell_migrator'
     AND coalesce(current_setting('echowell.allow_purge', true), 'off') = 'on'
     AND TG_OP IN ('DELETE', 'TRUNCATE') THEN
    IF TG_LEVEL = 'ROW' THEN RETURN OLD; ELSE RETURN NULL; END IF;
  END IF;
  RAISE EXCEPTION 'table % is append-only: % is not allowed', TG_TABLE_NAME, TG_OP
    USING ERRCODE = 'EW001';
END
$$;
"""

# TRD 20 §4.6: tables in creation (dependency) order (PGS-006).
TABLES: tuple[tuple[str, str], ...] = (
    (
        "facilities",
        r"""
CREATE TABLE facilities (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  name        text        NOT NULL,
  timezone    text        NOT NULL DEFAULT 'America/Chicago',
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT facilities_name_uq UNIQUE (name),
  CONSTRAINT facilities_name_ck CHECK (char_length(name) BETWEEN 1 AND 120),
  CONSTRAINT facilities_timezone_ck CHECK (char_length(timezone) BETWEEN 1 AND 64)
);
""",
    ),
    (
        "users",
        r"""
CREATE TABLE users (
  id             uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  email          text        NOT NULL,
  display_name   text        NOT NULL,
  password_hash  text        NOT NULL,
  role           user_role   NOT NULL,
  active         boolean     NOT NULL DEFAULT true,
  last_login_at  timestamptz NULL,
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT users_email_uq UNIQUE (email),
  CONSTRAINT users_email_lower_ck CHECK (email = lower(email)),
  CONSTRAINT users_email_format_ck CHECK (email ~ '^[^@\s]+@[^@\s]+\.[^@\s]+$' AND char_length(email) <= 254),
  CONSTRAINT users_display_name_ck CHECK (char_length(display_name) BETWEEN 1 AND 120),
  CONSTRAINT users_password_hash_ck CHECK (password_hash LIKE '$argon2id$%')
);
""",
    ),
    (
        "residents",
        r"""
CREATE TABLE residents (
  id             uuid            PRIMARY KEY DEFAULT gen_random_uuid(),
  facility_id    uuid            NOT NULL REFERENCES facilities (id) ON DELETE RESTRICT,
  resident_code  text            NOT NULL,
  sex            text            NULL,
  cohort         resident_cohort NOT NULL DEFAULT 'longitudinal',
  enrolled_on    date            NOT NULL,
  admitted_on    date            NULL,
  withdrawn_on   date            NULL,
  status         resident_status NOT NULL DEFAULT 'active',
  created_at     timestamptz     NOT NULL DEFAULT now(),
  updated_at     timestamptz     NOT NULL DEFAULT now(),
  CONSTRAINT residents_resident_code_uq UNIQUE (resident_code),
  CONSTRAINT residents_resident_code_ck CHECK (resident_code ~ '^[A-Z0-9]{1,16}$'),
  CONSTRAINT residents_sex_ck CHECK (sex IS NULL OR sex IN ('F', 'M')),
  CONSTRAINT residents_withdrawn_ck CHECK ((status = 'withdrawn') = (withdrawn_on IS NOT NULL)),
  CONSTRAINT residents_withdrawn_after_enrol_ck CHECK (withdrawn_on IS NULL OR withdrawn_on >= enrolled_on),
  CONSTRAINT residents_admitted_ck CHECK (admitted_on IS NULL OR admitted_on <= enrolled_on)
);
""",
    ),
    (
        "devices",
        r"""
CREATE TABLE devices (
  id                     uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  facility_id            uuid        NOT NULL REFERENCES facilities (id) ON DELETE RESTRICT,
  device_code            text        NOT NULL,
  room_label             text        NULL,
  firmware_version_last  text        NULL,
  active                 boolean     NOT NULL DEFAULT true,
  created_at             timestamptz NOT NULL DEFAULT now(),
  updated_at             timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT devices_device_code_uq UNIQUE (device_code),
  CONSTRAINT devices_device_code_ck CHECK (device_code ~ '^[A-Z0-9]{1,16}$'),
  CONSTRAINT devices_room_label_ck CHECK (room_label IS NULL OR char_length(room_label) BETWEEN 1 AND 60)
);
""",
    ),
    (
        "device_assignments",
        r"""
CREATE TABLE device_assignments (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  resident_id  uuid        NOT NULL REFERENCES residents (id) ON DELETE RESTRICT,
  device_id    uuid        NOT NULL REFERENCES devices (id) ON DELETE RESTRICT,
  valid_from   date        NOT NULL,
  valid_to     date        NULL,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT device_assignments_range_ck CHECK (valid_to IS NULL OR valid_to >= valid_from),
  -- one device per resident on any given day (valid_to is inclusive)
  CONSTRAINT device_assignments_no_overlap_ex EXCLUDE USING gist (
    resident_id WITH =,
    daterange(valid_from, valid_to, '[]') WITH &&
  )
);
""",
    ),
    (
        "api_keys",
        r"""
CREATE TABLE api_keys (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  name          text        NOT NULL,
  key_hash      text        NOT NULL,
  scopes        text[]      NOT NULL DEFAULT ARRAY['ingest:write']::text[],
  device_id     uuid        NULL REFERENCES devices (id) ON DELETE RESTRICT,
  active        boolean     NOT NULL DEFAULT true,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),
  last_used_at  timestamptz NULL,
  CONSTRAINT api_keys_key_hash_uq UNIQUE (key_hash),
  CONSTRAINT api_keys_key_hash_ck CHECK (key_hash ~ '^[0-9a-f]{64}$'),
  CONSTRAINT api_keys_name_ck CHECK (char_length(name) BETWEEN 1 AND 120),
  CONSTRAINT api_keys_scopes_ck CHECK (cardinality(scopes) >= 1 AND scopes <@ ARRAY['ingest:write', 'pipeline:run']::text[])
);
""",
    ),
    (
        "ingest_batches",
        r"""
CREATE TABLE ingest_batches (
  id              uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
  source          ingest_source NOT NULL,
  filename        text          NULL,
  record_count    integer       NOT NULL DEFAULT 0,
  accepted_count  integer       NOT NULL DEFAULT 0,
  rejected_count  integer       NOT NULL DEFAULT 0,
  duplicate_count integer       NOT NULL DEFAULT 0,
  uploaded_by     uuid          NULL REFERENCES users (id) ON DELETE RESTRICT,
  api_key_id      uuid          NULL REFERENCES api_keys (id) ON DELETE RESTRICT,
  received_at     timestamptz   NOT NULL DEFAULT now(),
  created_at      timestamptz   NOT NULL DEFAULT now(),
  updated_at      timestamptz   NOT NULL DEFAULT now(),
  CONSTRAINT ingest_batches_counts_ck CHECK (
    record_count >= 0 AND accepted_count >= 0 AND rejected_count >= 0 AND duplicate_count >= 0
    AND accepted_count + rejected_count <= record_count
    AND duplicate_count <= accepted_count),
  CONSTRAINT ingest_batches_actor_ck CHECK (source = 'seed' OR uploaded_by IS NOT NULL OR api_key_id IS NOT NULL),
  CONSTRAINT ingest_batches_filename_ck CHECK ((source = 'csv_upload') <= (filename IS NOT NULL))
);
""",
    ),
    (
        "ingest_rejections",
        r"""
CREATE TABLE ingest_rejections (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  ingest_batch_id  uuid        NULL REFERENCES ingest_batches (id) ON DELETE RESTRICT,
  api_key_id       uuid        NULL REFERENCES api_keys (id) ON DELETE RESTRICT,
  row_number       integer     NULL,
  received_at      timestamptz NOT NULL DEFAULT now(),
  raw_body         jsonb       NOT NULL,
  errors           jsonb       NOT NULL,
  CONSTRAINT ingest_rejections_errors_ck CHECK (jsonb_typeof(errors) = 'array' AND jsonb_array_length(errors) >= 1),
  CONSTRAINT ingest_rejections_row_number_ck CHECK (row_number IS NULL OR row_number >= 1)
);
""",
    ),
    (
        "raw_sessions",
        r"""
CREATE TABLE raw_sessions (
  id                           uuid             PRIMARY KEY DEFAULT gen_random_uuid(),
  arrival_seq                  bigserial        NOT NULL,
  received_at                  timestamptz      NOT NULL DEFAULT now(),
  ingest_batch_id              uuid             NULL REFERENCES ingest_batches (id) ON DELETE RESTRICT,
  api_key_id                   uuid             NULL REFERENCES api_keys (id) ON DELETE RESTRICT,
  payload                      jsonb            NOT NULL,
  ingest_warnings              jsonb            NOT NULL DEFAULT '[]'::jsonb,  -- TRD 10 plausibility warnings {field, code, message}
  resident_id                  uuid             NOT NULL REFERENCES residents (id) ON DELETE RESTRICT,
  device_id                    uuid             NOT NULL REFERENCES devices (id) ON DELETE RESTRICT,
  -- typed copies of the ingest record schema v0.1 fields (TRD 10), in SRC-05 column order
  schema_version               text             NOT NULL,
  session_id                   text             NOT NULL,
  resident_code                text             NOT NULL,
  device_code                  text             NOT NULL,
  timestamp_utc                timestamptz      NOT NULL,
  mic_noise_level_dbfs         double precision NOT NULL,
  audio_quality_flag           text             NOT NULL,
  extraction_software_version  text             NOT NULL,
  device_firmware_version      text             NOT NULL,
  speech_duration_s            double precision NOT NULL,
  phrase_id                    text             NOT NULL,
  -- 19 acoustic features (contract section 6; names are placeholders, OQ-03)
  loudness_dbfs                double precision NOT NULL,
  total_phrase_duration_s      double precision NOT NULL,
  speech_rate_syl_per_s        double precision NOT NULL,
  articulation_rate_syl_per_s  double precision NOT NULL,
  number_of_pauses             integer          NOT NULL,
  pause_fraction               double precision NOT NULL,
  voiced_fraction              double precision NOT NULL,
  mean_f0_hz                   double precision NOT NULL,
  f0_variability_st            double precision NOT NULL,
  jitter_local_pct             double precision NOT NULL,
  shimmer_local_pct            double precision NOT NULL,
  hnr_db                       double precision NOT NULL,
  cpps_db                      double precision NOT NULL,
  alpha_ratio_db               double precision NOT NULL,
  hammarberg_index_db          double precision NOT NULL,
  mfcc1                        double precision NOT NULL,
  mfcc2                        double precision NOT NULL,
  mfcc3                        double precision NOT NULL,
  mfcc4                        double precision NOT NULL,
  CONSTRAINT raw_sessions_arrival_seq_uq UNIQUE (arrival_seq),
  CONSTRAINT raw_sessions_payload_ck CHECK (jsonb_typeof(payload) = 'object'),
  CONSTRAINT raw_sessions_schema_version_ck CHECK (char_length(schema_version) BETWEEN 1 AND 16),
  CONSTRAINT raw_sessions_session_id_ck CHECK (char_length(session_id) BETWEEN 1 AND 64),
  CONSTRAINT raw_sessions_audio_quality_flag_ck CHECK (audio_quality_flag IN ('ok', 'poor')),
  CONSTRAINT raw_sessions_speech_duration_ck CHECK (speech_duration_s >= 0),
  CONSTRAINT raw_sessions_number_of_pauses_ck CHECK (number_of_pauses >= 0),
  CONSTRAINT raw_sessions_pause_fraction_ck CHECK (pause_fraction BETWEEN 0 AND 1),
  CONSTRAINT raw_sessions_voiced_fraction_ck CHECK (voiced_fraction BETWEEN 0 AND 1),
  CONSTRAINT raw_sessions_mean_f0_ck CHECK (mean_f0_hz > 0),
  CONSTRAINT raw_sessions_phrase_id_ck CHECK (char_length(phrase_id) BETWEEN 1 AND 16),
  CONSTRAINT raw_sessions_versions_ck CHECK (
    char_length(extraction_software_version) BETWEEN 1 AND 64
    AND char_length(device_firmware_version) BETWEEN 1 AND 64)
);
""",
    ),
    (
        "pipeline_runs",
        r"""
CREATE TABLE pipeline_runs (
  id               uuid                PRIMARY KEY DEFAULT gen_random_uuid(),
  trigger          pipeline_trigger    NOT NULL,
  scope            jsonb               NOT NULL,
  config_profile   text                NOT NULL,
  config_snapshot  jsonb               NOT NULL,
  code_version     text                NOT NULL,
  as_of            timestamptz         NOT NULL,
  started_at       timestamptz         NOT NULL DEFAULT now(),
  finished_at      timestamptz         NULL,
  status           pipeline_run_status NOT NULL DEFAULT 'running',
  counts           jsonb               NOT NULL DEFAULT '{}'::jsonb,
  warnings         jsonb               NOT NULL DEFAULT '[]'::jsonb,
  error_message    text                NULL,
  created_at       timestamptz         NOT NULL DEFAULT now(),
  updated_at       timestamptz         NOT NULL DEFAULT now(),
  CONSTRAINT pipeline_runs_profile_ck CHECK (config_profile IN ('production', 'test_v0_1')),
  CONSTRAINT pipeline_runs_scope_ck CHECK (
    (scope = '{"type": "all"}'::jsonb)
    OR (scope->>'type' = 'residents' AND jsonb_typeof(scope->'resident_codes') = 'array'
        AND jsonb_array_length(scope->'resident_codes') >= 1)),
  CONSTRAINT pipeline_runs_snapshot_ck CHECK (jsonb_typeof(config_snapshot) = 'object'),
  CONSTRAINT pipeline_runs_counts_ck CHECK (jsonb_typeof(counts) = 'object'),
  CONSTRAINT pipeline_runs_warnings_ck CHECK (jsonb_typeof(warnings) = 'array'),
  CONSTRAINT pipeline_runs_finished_ck CHECK ((status = 'running') = (finished_at IS NULL)),
  CONSTRAINT pipeline_runs_error_ck CHECK ((status = 'failed') = (error_message IS NOT NULL)),
  CONSTRAINT pipeline_runs_order_ck CHECK (finished_at IS NULL OR finished_at >= started_at)
);
""",
    ),
    (
        "epochs",
        r"""
CREATE TABLE epochs (
  id                           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  resident_id                  uuid        NOT NULL REFERENCES residents (id) ON DELETE RESTRICT,
  epoch_number                 integer     NOT NULL,
  device_id                    uuid        NOT NULL REFERENCES devices (id) ON DELETE RESTRICT,
  device_firmware_version      text        NOT NULL,
  extraction_software_version  text        NOT NULL,
  started_at                   timestamptz NOT NULL,
  ended_at                     timestamptz NULL,
  pipeline_run_id              uuid        NOT NULL REFERENCES pipeline_runs (id) ON DELETE RESTRICT,
  created_at                   timestamptz NOT NULL DEFAULT now(),
  updated_at                   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT epochs_resident_number_uq UNIQUE (resident_id, epoch_number),
  CONSTRAINT epochs_number_ck CHECK (epoch_number >= 1),
  CONSTRAINT epochs_order_ck CHECK (ended_at IS NULL OR ended_at > started_at)
);
""",
    ),
    (
        "processed_sessions",
        r"""
CREATE TABLE processed_sessions (
  id                 uuid             PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_session_id     uuid             NOT NULL REFERENCES raw_sessions (id) ON DELETE RESTRICT,
  session_id         text             NOT NULL,
  resident_id        uuid             NOT NULL REFERENCES residents (id) ON DELETE RESTRICT,
  epoch_id           uuid             NULL REFERENCES epochs (id) ON DELETE RESTRICT,
  status             session_status   NOT NULL,
  reasons            text[]           NOT NULL DEFAULT '{}'::text[],
  reason_text        text             NOT NULL DEFAULT '',
  timestamp_utc      timestamptz      NOT NULL,
  local_date         date             NOT NULL,
  local_time         time(0)          NOT NULL,
  is_morning         boolean          NOT NULL,
  screen_detail      text             NULL,
  baseline_ordinal   integer          NULL,
  in_baseline        boolean          NOT NULL DEFAULT false,
  late_arrival       boolean          NOT NULL DEFAULT false,
  adjusted_features  jsonb            NULL,
  pipeline_run_id    uuid             NOT NULL REFERENCES pipeline_runs (id) ON DELETE RESTRICT,
  created_at         timestamptz      NOT NULL DEFAULT now(),
  CONSTRAINT processed_sessions_raw_session_uq UNIQUE (raw_session_id),
  CONSTRAINT processed_sessions_epoch_ck CHECK (
       (status = 'duplicate' AND epoch_id IS NULL AND NOT late_arrival)
    OR (status <> 'duplicate' AND (epoch_id IS NOT NULL OR late_arrival))),
  CONSTRAINT processed_sessions_local_date_ck CHECK (
    local_date BETWEEN (timestamp_utc AT TIME ZONE 'UTC')::date - 1
                   AND (timestamp_utc AT TIME ZONE 'UTC')::date + 1),
  CONSTRAINT processed_sessions_reason_text_ck CHECK (reason_text = array_to_string(reasons, '; ')),
  CONSTRAINT processed_sessions_status_reason_ck CHECK (
       (status = 'usable'      AND NOT late_arrival AND cardinality(reasons) = 0)
    OR (status = 'usable'      AND late_arrival
        AND reasons = ARRAY['late arrival (not used for baseline or scores)']::text[])
    OR (status = 'duplicate'   AND reasons = ARRAY['session_id already received']::text[])
    OR (status = 'set_aside'   AND cardinality(reasons) BETWEEN 1 AND 3
        AND reasons <@ ARRAY['quality flag poor', 'noise above limit', 'speech too short']::text[])
    OR (status = 'quarantined' AND NOT late_arrival AND cardinality(reasons) = 1
        AND reasons[1] LIKE 'possible other speaker (F0 z=%; composite features with |z|>=3: %)')
    OR (status = 'quarantined' AND late_arrival AND cardinality(reasons) = 2
        AND reasons[1] LIKE 'possible other speaker (F0 z=%; composite features with |z|>=3: %)'
        AND reasons[2] = 'late arrival (not used for baseline or scores)')),
  CONSTRAINT processed_sessions_screen_ck CHECK (status <> 'quarantined' OR screen_detail IS NOT NULL),
  CONSTRAINT processed_sessions_ordinal_ck CHECK (
    (status = 'usable' AND NOT late_arrival) = (baseline_ordinal IS NOT NULL)
    AND (baseline_ordinal IS NULL OR baseline_ordinal >= 1)),
  CONSTRAINT processed_sessions_in_baseline_ck CHECK (NOT in_baseline OR (status = 'usable' AND NOT late_arrival)),
  CONSTRAINT processed_sessions_adjusted_ck CHECK (
    (status = 'duplicate' AND adjusted_features IS NULL)
    OR (status <> 'duplicate' AND jsonb_typeof(adjusted_features) = 'object'
        AND adjusted_features ?& ARRAY['loudness_dbfs','total_phrase_duration_s','speech_rate_syl_per_s',
          'articulation_rate_syl_per_s','number_of_pauses','pause_fraction','voiced_fraction','mean_f0_hz',
          'f0_variability_st','jitter_local_pct','shimmer_local_pct','hnr_db','cpps_db','alpha_ratio_db',
          'hammarberg_index_db','mfcc1','mfcc2','mfcc3','mfcc4']))
);
""",
    ),
    (
        "day_ledger",
        r"""
CREATE TABLE day_ledger (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  resident_id      uuid        NOT NULL REFERENCES residents (id) ON DELETE RESTRICT,
  local_date       date        NOT NULL,
  status           day_status  NOT NULL,
  device_id        uuid        NULL REFERENCES devices (id) ON DELETE RESTRICT,
  reason           text        NOT NULL DEFAULT '',
  pipeline_run_id  uuid        NOT NULL REFERENCES pipeline_runs (id) ON DELETE RESTRICT,
  created_at       timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT day_ledger_resident_date_uq UNIQUE (resident_id, local_date),
  CONSTRAINT day_ledger_reason_ck CHECK (
       (status = 'checked_in'         AND reason = '')
    OR (status = 'missing_resident'   AND reason = 'no record received')
    OR (status = 'missing_device_gap' AND device_id IS NOT NULL
        AND reason LIKE 'all residents on shared device % have no record'))
);
""",
    ),
    (
        "baselines",
        r"""
CREATE TABLE baselines (
  id                       uuid             PRIMARY KEY DEFAULT gen_random_uuid(),
  resident_id              uuid             NOT NULL REFERENCES residents (id) ON DELETE RESTRICT,
  epoch_id                 uuid             NOT NULL REFERENCES epochs (id) ON DELETE RESTRICT,
  feature_key              text             NOT NULL,
  n_sessions               integer          NOT NULL,
  first_session_id         text             NOT NULL,
  frozen_after_session_id  text             NOT NULL,
  median                   double precision NOT NULL,
  mad                      double precision NOT NULL,
  robust_spread            double precision NOT NULL,
  floor_applied            boolean          NOT NULL,
  frozen_at                timestamptz      NOT NULL,
  pipeline_run_id          uuid             NOT NULL REFERENCES pipeline_runs (id) ON DELETE RESTRICT,
  created_at               timestamptz      NOT NULL DEFAULT now(),
  CONSTRAINT baselines_epoch_feature_uq UNIQUE (epoch_id, feature_key),
  CONSTRAINT baselines_feature_key_ck CHECK (feature_key IN (
    'loudness_dbfs','total_phrase_duration_s','speech_rate_syl_per_s','articulation_rate_syl_per_s',
    'number_of_pauses','pause_fraction','voiced_fraction','mean_f0_hz','f0_variability_st',
    'jitter_local_pct','shimmer_local_pct','hnr_db','cpps_db','alpha_ratio_db','hammarberg_index_db',
    'mfcc1','mfcc2','mfcc3','mfcc4','composite')),
  CONSTRAINT baselines_n_sessions_ck CHECK (n_sessions >= 1),
  CONSTRAINT baselines_spread_ck CHECK (mad >= 0 AND robust_spread >= 0)
);
""",
    ),
    (
        "scores",
        r"""
CREATE TABLE scores (
  id                     uuid             PRIMARY KEY DEFAULT gen_random_uuid(),
  processed_session_id   uuid             NOT NULL REFERENCES processed_sessions (id) ON DELETE CASCADE,
  resident_id            uuid             NOT NULL REFERENCES residents (id) ON DELETE RESTRICT,
  epoch_id               uuid             NOT NULL REFERENCES epochs (id) ON DELETE RESTRICT,
  local_date             date             NOT NULL,
  is_morning             boolean          NOT NULL,
  z                      jsonb            NOT NULL,
  composite_raw          double precision NOT NULL,
  composite_z            double precision NOT NULL,
  cusum_tally            double precision NOT NULL,
  alarm_state            alarm_state      NOT NULL,
  pipeline_run_id        uuid             NOT NULL REFERENCES pipeline_runs (id) ON DELETE RESTRICT,
  created_at             timestamptz      NOT NULL DEFAULT now(),
  CONSTRAINT scores_processed_session_uq UNIQUE (processed_session_id),
  CONSTRAINT scores_z_ck CHECK (jsonb_typeof(z) = 'object' AND z ?& ARRAY[
    'z_loudness_dbfs','z_total_phrase_duration_s','z_speech_rate_syl_per_s','z_articulation_rate_syl_per_s',
    'z_number_of_pauses','z_pause_fraction','z_voiced_fraction']),
  CONSTRAINT scores_cusum_ck CHECK (cusum_tally >= 0)
);
""",
    ),
    (
        "cusum_state",
        r"""
CREATE TABLE cusum_state (
  epoch_id                uuid             PRIMARY KEY REFERENCES epochs (id) ON DELETE RESTRICT,
  resident_id             uuid             NOT NULL REFERENCES residents (id) ON DELETE RESTRICT,
  current_tally           double precision NOT NULL DEFAULT 0,
  last_scored_session_id  text             NULL,
  alarm_on                boolean          NOT NULL DEFAULT false,
  pipeline_run_id         uuid             NOT NULL REFERENCES pipeline_runs (id) ON DELETE RESTRICT,
  updated_at              timestamptz      NOT NULL DEFAULT now(),
  CONSTRAINT cusum_state_tally_ck CHECK (current_tally >= 0),
  CONSTRAINT cusum_state_scored_ck CHECK (last_scored_session_id IS NOT NULL OR (current_tally = 0 AND NOT alarm_on))
);
""",
    ),
    (
        "alerts",
        r"""
CREATE TABLE alerts (
  id                uuid             PRIMARY KEY DEFAULT gen_random_uuid(),
  resident_id       uuid             NOT NULL REFERENCES residents (id) ON DELETE RESTRICT,
  epoch_id          uuid             NOT NULL REFERENCES epochs (id) ON DELETE RESTRICT,
  session_id        text             NOT NULL,
  triggered_at      timestamptz      NOT NULL,
  local_date        date             NOT NULL,
  cusum_value       double precision NOT NULL,
  status            alert_status     NOT NULL DEFAULT 'open',
  closed_reason     text             NULL,
  closed_at         timestamptz      NULL,
  acknowledged_by   uuid             NULL REFERENCES users (id) ON DELETE RESTRICT,
  acknowledged_at   timestamptz      NULL,
  snoozed_until     timestamptz      NULL,
  snoozed_by        uuid             NULL REFERENCES users (id) ON DELETE RESTRICT,
  pipeline_run_id   uuid             NOT NULL REFERENCES pipeline_runs (id) ON DELETE RESTRICT,
  created_at        timestamptz      NOT NULL DEFAULT now(),
  updated_at        timestamptz      NOT NULL DEFAULT now(),
  CONSTRAINT alerts_epoch_session_uq UNIQUE (epoch_id, session_id),
  CONSTRAINT alerts_cusum_ck CHECK (cusum_value >= 0),
  CONSTRAINT alerts_closed_ck CHECK (
    (status = 'closed') = (closed_reason IS NOT NULL)
    AND (status = 'closed') = (closed_at IS NOT NULL)),
  CONSTRAINT alerts_closed_reason_ck CHECK (
    closed_reason IS NULL OR closed_reason IN ('epoch ended', 'admin', 'superseded by rebuild')),
  CONSTRAINT alerts_ack_ck CHECK ((acknowledged_by IS NULL) = (acknowledged_at IS NULL)),
  CONSTRAINT alerts_ack_status_ck CHECK (status <> 'acknowledged' OR acknowledged_at IS NOT NULL),
  CONSTRAINT alerts_snooze_ck CHECK ((snoozed_until IS NULL) = (snoozed_by IS NULL))
);
""",
    ),
    (
        "alert_reviews",
        r"""
CREATE TABLE alert_reviews (
  id                uuid           PRIMARY KEY DEFAULT gen_random_uuid(),
  alert_id          uuid           NOT NULL REFERENCES alerts (id) ON DELETE RESTRICT,
  reviewer_user_id  uuid           NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
  explanations      text[]         NOT NULL DEFAULT '{}'::text[],
  outcome           review_outcome NOT NULL,
  note              text           NULL,
  created_at        timestamptz    NOT NULL DEFAULT now(),
  CONSTRAINT alert_reviews_explanations_ck CHECK (
    cardinality(explanations) <= 20
    AND array_to_string(explanations, ',') ~ '^([a-z][a-z0-9_]{0,63}(,[a-z][a-z0-9_]{0,63})*)?$'),
  CONSTRAINT alert_reviews_note_ck CHECK (note IS NULL OR (char_length(btrim(note)) >= 1 AND char_length(note) <= 2000))
);
""",
    ),
    (
        "data_alerts",
        r"""
CREATE TABLE data_alerts (
  id                 uuid              PRIMARY KEY DEFAULT gen_random_uuid(),
  kind               data_alert_kind   NOT NULL,
  resident_id        uuid              NULL REFERENCES residents (id) ON DELETE RESTRICT,
  device_id          uuid              NULL REFERENCES devices (id) ON DELETE RESTRICT,
  alert_review_id    uuid              NULL REFERENCES alert_reviews (id) ON DELETE RESTRICT,
  title              text              NOT NULL,
  detail             text              NOT NULL DEFAULT '',
  first_detected_at  timestamptz       NOT NULL,
  last_detected_at   timestamptz       NOT NULL,
  status             data_alert_status NOT NULL DEFAULT 'open',
  resolved_at        timestamptz       NULL,
  pipeline_run_id    uuid              NULL REFERENCES pipeline_runs (id) ON DELETE RESTRICT,
  created_at         timestamptz       NOT NULL DEFAULT now(),
  updated_at         timestamptz       NOT NULL DEFAULT now(),
  CONSTRAINT data_alerts_alert_review_uq UNIQUE (alert_review_id),
  CONSTRAINT data_alerts_subject_ck CHECK (
       (kind = 'device_silent' AND device_id IS NOT NULL AND resident_id IS NULL AND alert_review_id IS NULL)
    OR (kind IN ('baseline_stalled', 'possible_other_speaker', 'high_set_aside')
        AND resident_id IS NOT NULL AND device_id IS NULL AND alert_review_id IS NULL)
    OR (kind = 'review_flagged_data_problem' AND resident_id IS NOT NULL AND alert_review_id IS NOT NULL)),
  CONSTRAINT data_alerts_run_ck CHECK ((kind = 'review_flagged_data_problem') = (pipeline_run_id IS NULL)),
  CONSTRAINT data_alerts_resolved_ck CHECK ((status = 'resolved') = (resolved_at IS NOT NULL)),
  CONSTRAINT data_alerts_detected_ck CHECK (last_detected_at >= first_detected_at),
  CONSTRAINT data_alerts_text_ck CHECK (char_length(title) BETWEEN 1 AND 200 AND char_length(detail) <= 500)
);
""",
    ),
    (
        "staff_notes",
        r"""
CREATE TABLE staff_notes (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  resident_id      uuid        NOT NULL REFERENCES residents (id) ON DELETE RESTRICT,
  alert_id         uuid        NULL REFERENCES alerts (id) ON DELETE RESTRICT,
  author_user_id   uuid        NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
  note_type        note_type   NOT NULL,
  body             text        NOT NULL,
  marked_reviewed  boolean     NOT NULL DEFAULT false,
  supersedes_id    uuid        NULL REFERENCES staff_notes (id) ON DELETE RESTRICT,
  created_at       timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT staff_notes_body_ck CHECK (char_length(btrim(body)) >= 1 AND char_length(body) <= 2000),
  CONSTRAINT staff_notes_supersedes_uq UNIQUE (supersedes_id),
  CONSTRAINT staff_notes_not_self_ck CHECK (supersedes_id IS NULL OR supersedes_id <> id)
);
""",
    ),
    (
        "facility_reference_ranges",
        r"""
CREATE TABLE facility_reference_ranges (
  id               uuid             PRIMARY KEY DEFAULT gen_random_uuid(),
  facility_id      uuid             NOT NULL REFERENCES facilities (id) ON DELETE RESTRICT,
  feature_key      text             NOT NULL,
  sex              text             NULL,
  low              double precision NOT NULL,
  high             double precision NOT NULL,
  method           text             NOT NULL,
  n_residents      integer          NOT NULL,
  computed_at      timestamptz      NOT NULL,
  pipeline_run_id  uuid             NOT NULL REFERENCES pipeline_runs (id) ON DELETE RESTRICT,
  CONSTRAINT facility_reference_ranges_uq UNIQUE NULLS NOT DISTINCT (facility_id, feature_key, sex, pipeline_run_id),
  CONSTRAINT facility_reference_ranges_feature_ck CHECK (feature_key IN (
    'loudness_dbfs','total_phrase_duration_s','speech_rate_syl_per_s','articulation_rate_syl_per_s',
    'number_of_pauses','pause_fraction','voiced_fraction','mean_f0_hz','f0_variability_st',
    'jitter_local_pct','shimmer_local_pct','hnr_db','cpps_db','alpha_ratio_db','hammarberg_index_db',
    'mfcc1','mfcc2','mfcc3','mfcc4')),
  CONSTRAINT facility_reference_ranges_sex_ck CHECK (sex IS NULL OR sex IN ('F', 'M')),
  CONSTRAINT facility_reference_ranges_bounds_ck CHECK (low <= high),
  CONSTRAINT facility_reference_ranges_n_ck CHECK (n_residents >= 1),
  CONSTRAINT facility_reference_ranges_method_ck CHECK (char_length(method) BETWEEN 1 AND 200)
);
""",
    ),
    (
        "config_parameters",
        r"""
CREATE TABLE config_parameters (
  profile      text        NOT NULL,
  key          text        NOT NULL,
  value        jsonb       NOT NULL,
  description  text        NOT NULL DEFAULT '',
  updated_by   uuid        NULL REFERENCES users (id) ON DELETE RESTRICT,
  updated_at   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT config_parameters_pk PRIMARY KEY (profile, key),
  CONSTRAINT config_parameters_profile_ck CHECK (profile IN ('production', 'test_v0_1')),
  CONSTRAINT config_parameters_key_ck CHECK (key ~ '^[a-z][a-z0-9_]{0,63}$')
);
""",
    ),
    (
        "audit_logs",
        r"""
CREATE TABLE audit_logs (
  id           bigserial   PRIMARY KEY,
  occurred_at  timestamptz NOT NULL DEFAULT now(),
  actor_type   actor_type  NOT NULL,
  actor_id     text        NULL,
  action       text        NOT NULL,
  entity_type  text        NULL,
  entity_id    text        NULL,
  details      jsonb       NOT NULL DEFAULT '{}'::jsonb,
  ip           inet        NULL,
  request_id   text        NULL,
  CONSTRAINT audit_logs_action_ck CHECK (action ~ '^[a-z_]+(\.[a-z_]+){1,2}$'),
  CONSTRAINT audit_logs_details_ck CHECK (jsonb_typeof(details) = 'object'),
  CONSTRAINT audit_logs_actor_ck CHECK (actor_type = 'system' OR actor_id IS NOT NULL)
);
""",
    ),
    (
        "evaluation_ground_truth",
        r"""
CREATE TABLE evaluation_ground_truth (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  resident_code    text        NOT NULL,
  planted_change   text        NOT NULL,
  true_onset_date  date        NULL,
  source_file      text        NOT NULL,
  created_at       timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT evaluation_ground_truth_resident_code_uq UNIQUE (resident_code),
  CONSTRAINT evaluation_ground_truth_onset_ck CHECK ((planted_change = 'None') = (true_onset_date IS NULL)),
  CONSTRAINT evaluation_ground_truth_text_ck CHECK (
    char_length(planted_change) BETWEEN 1 AND 60 AND char_length(source_file) BETWEEN 1 AND 200)
);
""",
    ),
)

# TRD 20 §4.7: additional indexes (PGS-038, DB-040..DB-047).
INDEXES = r"""
-- (UNIQUE constraints above already create indexes; listed here are the additional ones.)
CREATE INDEX residents_facility_idx            ON residents (facility_id);
CREATE INDEX residents_status_cohort_idx       ON residents (status, cohort);
CREATE INDEX devices_facility_idx              ON devices (facility_id);
CREATE INDEX device_assignments_device_idx     ON device_assignments (device_id, valid_from);
CREATE INDEX device_assignments_resident_idx   ON device_assignments (resident_id, valid_from);
CREATE INDEX api_keys_device_idx               ON api_keys (device_id);
CREATE INDEX ingest_batches_received_idx       ON ingest_batches (received_at DESC);
CREATE INDEX ingest_batches_uploaded_by_idx    ON ingest_batches (uploaded_by);
CREATE INDEX ingest_batches_api_key_idx        ON ingest_batches (api_key_id);
CREATE INDEX ingest_rejections_batch_idx       ON ingest_rejections (ingest_batch_id);
CREATE INDEX ingest_rejections_received_idx    ON ingest_rejections (received_at DESC);
CREATE INDEX ingest_rejections_api_key_idx     ON ingest_rejections (api_key_id);
CREATE INDEX raw_sessions_session_id_idx       ON raw_sessions (session_id, arrival_seq);
CREATE INDEX raw_sessions_resident_ts_idx      ON raw_sessions (resident_id, timestamp_utc, arrival_seq);
CREATE INDEX raw_sessions_device_ts_idx        ON raw_sessions (device_id, timestamp_utc DESC);
CREATE INDEX raw_sessions_batch_idx            ON raw_sessions (ingest_batch_id);
CREATE INDEX raw_sessions_api_key_idx          ON raw_sessions (api_key_id);
CREATE INDEX pipeline_runs_started_idx         ON pipeline_runs (started_at DESC);
CREATE INDEX pipeline_runs_status_idx          ON pipeline_runs (status) WHERE status = 'running';
CREATE UNIQUE INDEX epochs_current_uq          ON epochs (resident_id) WHERE ended_at IS NULL;
CREATE INDEX epochs_device_idx                 ON epochs (device_id);
CREATE INDEX epochs_run_idx                    ON epochs (pipeline_run_id);
CREATE INDEX processed_sessions_resident_date_idx ON processed_sessions (resident_id, local_date) INCLUDE (status);
CREATE INDEX processed_sessions_resident_ts_idx   ON processed_sessions (resident_id, timestamp_utc DESC)
  WHERE status <> 'duplicate';
CREATE INDEX processed_sessions_epoch_idx      ON processed_sessions (epoch_id, timestamp_utc);
CREATE INDEX processed_sessions_session_id_idx ON processed_sessions (session_id);
CREATE INDEX processed_sessions_run_idx        ON processed_sessions (pipeline_run_id);
CREATE INDEX day_ledger_missing_idx            ON day_ledger (resident_id, local_date) WHERE status <> 'checked_in';
CREATE INDEX day_ledger_device_date_idx        ON day_ledger (device_id, local_date);
CREATE INDEX day_ledger_run_idx                ON day_ledger (pipeline_run_id);
CREATE INDEX baselines_resident_idx            ON baselines (resident_id);
CREATE INDEX baselines_run_idx                 ON baselines (pipeline_run_id);
CREATE INDEX scores_resident_date_idx          ON scores (resident_id, local_date);
CREATE INDEX scores_epoch_date_idx             ON scores (epoch_id, local_date);
CREATE INDEX scores_run_idx                    ON scores (pipeline_run_id);
CREATE INDEX cusum_state_resident_idx          ON cusum_state (resident_id);
CREATE INDEX cusum_state_run_idx               ON cusum_state (pipeline_run_id);
CREATE UNIQUE INDEX alerts_one_active_per_epoch_uq ON alerts (epoch_id) WHERE status <> 'closed';
CREATE INDEX alerts_status_triggered_idx       ON alerts (status, triggered_at DESC);
CREATE INDEX alerts_resident_triggered_idx     ON alerts (resident_id, triggered_at DESC);
CREATE INDEX alerts_acknowledged_by_idx        ON alerts (acknowledged_by);
CREATE INDEX alerts_run_idx                    ON alerts (pipeline_run_id);
CREATE INDEX alerts_snoozed_by_idx             ON alerts (snoozed_by);
CREATE INDEX alert_reviews_alert_created_idx   ON alert_reviews (alert_id, created_at DESC);
CREATE INDEX alert_reviews_reviewer_idx        ON alert_reviews (reviewer_user_id);
CREATE INDEX alert_reviews_outcome_idx         ON alert_reviews (outcome);
CREATE UNIQUE INDEX data_alerts_open_subject_uq ON data_alerts (kind, resident_id, device_id) NULLS NOT DISTINCT
  WHERE status = 'open' AND kind <> 'review_flagged_data_problem';
CREATE INDEX data_alerts_status_detected_idx   ON data_alerts (status, last_detected_at DESC);
CREATE INDEX data_alerts_resident_idx          ON data_alerts (resident_id);
CREATE INDEX data_alerts_device_idx            ON data_alerts (device_id);
CREATE INDEX data_alerts_run_idx               ON data_alerts (pipeline_run_id);
CREATE INDEX staff_notes_resident_created_idx  ON staff_notes (resident_id, created_at DESC);
CREATE INDEX staff_notes_alert_idx             ON staff_notes (alert_id);
CREATE INDEX staff_notes_author_idx            ON staff_notes (author_user_id);
CREATE INDEX facility_reference_ranges_lookup_idx ON facility_reference_ranges (facility_id, feature_key, computed_at DESC);
CREATE INDEX facility_reference_ranges_run_idx ON facility_reference_ranges (pipeline_run_id);
CREATE INDEX config_parameters_updated_by_idx  ON config_parameters (updated_by);
CREATE INDEX audit_logs_occurred_idx           ON audit_logs (occurred_at DESC);
CREATE INDEX audit_logs_entity_idx             ON audit_logs (entity_type, entity_id);
CREATE INDEX audit_logs_actor_idx              ON audit_logs (actor_type, actor_id, occurred_at DESC);
CREATE INDEX audit_logs_action_idx             ON audit_logs (action, occurred_at DESC);
"""

# TRD 20 §4.8: append-only and updated_at triggers (PGS-018, PGS-020).
TRIGGERS = r"""
CREATE TRIGGER raw_sessions_no_update_delete BEFORE UPDATE OR DELETE ON raw_sessions
  FOR EACH ROW EXECUTE FUNCTION reject_mutation();
CREATE TRIGGER raw_sessions_no_truncate BEFORE TRUNCATE ON raw_sessions
  FOR EACH STATEMENT EXECUTE FUNCTION reject_mutation();
CREATE TRIGGER audit_logs_no_update_delete BEFORE UPDATE OR DELETE ON audit_logs
  FOR EACH ROW EXECUTE FUNCTION reject_mutation();
CREATE TRIGGER audit_logs_no_truncate BEFORE TRUNCATE ON audit_logs
  FOR EACH STATEMENT EXECUTE FUNCTION reject_mutation();

CREATE TRIGGER facilities_set_updated_at         BEFORE UPDATE ON facilities         FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER users_set_updated_at              BEFORE UPDATE ON users              FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER residents_set_updated_at          BEFORE UPDATE ON residents          FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER devices_set_updated_at            BEFORE UPDATE ON devices            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER device_assignments_set_updated_at BEFORE UPDATE ON device_assignments FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER api_keys_set_updated_at           BEFORE UPDATE ON api_keys           FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER ingest_batches_set_updated_at     BEFORE UPDATE ON ingest_batches     FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER pipeline_runs_set_updated_at      BEFORE UPDATE ON pipeline_runs      FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER epochs_set_updated_at             BEFORE UPDATE ON epochs             FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER cusum_state_set_updated_at        BEFORE UPDATE ON cusum_state        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER alerts_set_updated_at             BEFORE UPDATE ON alerts             FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER data_alerts_set_updated_at        BEFORE UPDATE ON data_alerts        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER config_parameters_set_updated_at  BEFORE UPDATE ON config_parameters  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
"""

# TRD 20 §4.8: grants, issued in the migration that creates the tables (PGS-021, PGS-022).
GRANTS = r"""
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO echowell_app, echowell_readonly;
GRANT USAGE, CREATE ON SCHEMA public TO echowell_migrator;

-- echowell_app: append-only tables (INSERT + SELECT only)
GRANT SELECT, INSERT ON raw_sessions, audit_logs, ingest_rejections, staff_notes, baselines, alert_reviews TO echowell_app;
-- echowell_app: master/config tables and tables whose rows carry human state (no DELETE)
GRANT SELECT, INSERT, UPDATE ON facilities, residents, devices, device_assignments, users, api_keys,
  ingest_batches, pipeline_runs, config_parameters, alerts, data_alerts TO echowell_app;
-- echowell_app: rebuildable derived tables
GRANT SELECT, INSERT, UPDATE, DELETE ON epochs, processed_sessions, day_ledger, scores, cusum_state,
  facility_reference_ranges TO echowell_app;
GRANT USAGE, SELECT ON SEQUENCE raw_sessions_arrival_seq_seq, audit_logs_id_seq TO echowell_app;
-- echowell_app: NO privilege on evaluation_ground_truth (the pipeline never reads the answer key, SRC-02; contract R20)

-- echowell_readonly: everything except credential columns (incl. evaluation_ground_truth, which holds rows only in test_v0_1)
GRANT SELECT ON facilities, residents, devices, device_assignments, ingest_batches, ingest_rejections,
  raw_sessions, epochs, processed_sessions, day_ledger, baselines, scores, cusum_state, alerts, alert_reviews,
  data_alerts, staff_notes, facility_reference_ranges, pipeline_runs, config_parameters, audit_logs,
  evaluation_ground_truth TO echowell_readonly;
GRANT SELECT (id, email, display_name, role, active, last_login_at, created_at, updated_at) ON users TO echowell_readonly;
GRANT SELECT (id, name, scopes, device_id, active, created_at, updated_at, last_used_at) ON api_keys TO echowell_readonly;
"""

ENUM_NAMES = (
    "resident_cohort",
    "resident_status",
    "ingest_source",
    "session_status",
    "day_status",
    "alarm_state",
    "alert_status",
    "note_type",
    "pipeline_trigger",
    "pipeline_run_status",
    "user_role",
    "actor_type",
    "review_outcome",
    "data_alert_kind",
    "data_alert_status",
)


def upgrade() -> None:
    op.execute(EXTENSION_CHECK)
    op.execute(ENUM_TYPES)
    op.execute(TRIGGER_FUNCTIONS)
    for _name, ddl in TABLES:
        op.execute(ddl)
    op.execute(INDEXES)
    op.execute(TRIGGERS)
    op.execute(GRANTS)


def downgrade() -> None:
    # Drops only the objects this revision created, in reverse order; never an extension, a role or
    # a database setting (TRD 20 §8, D-72). DROP fires no row or TRUNCATE trigger (D-71).
    for name, _ddl in reversed(TABLES):
        op.execute(f"DROP TABLE {name}")
    op.execute("DROP FUNCTION reject_mutation()")
    op.execute("DROP FUNCTION set_updated_at()")
    for name in reversed(ENUM_NAMES):
        op.execute(f"DROP TYPE {name}")
    op.execute("REVOKE ALL ON SCHEMA public FROM echowell_app, echowell_readonly")
    op.execute("GRANT USAGE ON SCHEMA public TO PUBLIC")
