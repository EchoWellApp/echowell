--
-- PostgreSQL database dump
--

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

-- *not* creating schema, since initdb creates it

--
-- Name: btree_gist; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS btree_gist WITH SCHEMA public;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;

--
-- Name: actor_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.actor_type AS ENUM (
    'user',
    'api_key',
    'system'
);

--
-- Name: alarm_state; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.alarm_state AS ENUM (
    'off',
    'rings',
    'on'
);

--
-- Name: alert_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.alert_status AS ENUM (
    'open',
    'acknowledged',
    'closed'
);

--
-- Name: data_alert_kind; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.data_alert_kind AS ENUM (
    'baseline_stalled',
    'possible_other_speaker',
    'high_set_aside',
    'device_silent',
    'review_flagged_data_problem'
);

--
-- Name: data_alert_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.data_alert_status AS ENUM (
    'open',
    'resolved'
);

--
-- Name: day_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.day_status AS ENUM (
    'checked_in',
    'missing_resident',
    'missing_device_gap'
);

--
-- Name: ingest_source; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.ingest_source AS ENUM (
    'api_single',
    'api_batch',
    'csv_upload',
    'seed'
);

--
-- Name: note_type; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.note_type AS ENUM (
    'observation',
    'action_taken',
    'follow_up'
);

--
-- Name: pipeline_run_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.pipeline_run_status AS ENUM (
    'running',
    'succeeded',
    'failed'
);

--
-- Name: pipeline_trigger; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.pipeline_trigger AS ENUM (
    'ingest',
    'nightly',
    'manual',
    'test'
);

--
-- Name: resident_cohort; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.resident_cohort AS ENUM (
    'longitudinal',
    'new_admission'
);

--
-- Name: resident_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.resident_status AS ENUM (
    'active',
    'withdrawn'
);

--
-- Name: review_outcome; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.review_outcome AS ENUM (
    'no_concern',
    'known_cause',
    'referred',
    'data_problem'
);

--
-- Name: session_status; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.session_status AS ENUM (
    'usable',
    'set_aside',
    'quarantined',
    'duplicate'
);

--
-- Name: user_role; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.user_role AS ENUM (
    'admin',
    'clinician',
    'researcher'
);

--
-- Name: reject_mutation(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.reject_mutation() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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

--
-- Name: set_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.set_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END
$$;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);

--
-- Name: alert_reviews; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alert_reviews (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    alert_id uuid NOT NULL,
    reviewer_user_id uuid NOT NULL,
    explanations text[] DEFAULT '{}'::text[] NOT NULL,
    outcome public.review_outcome NOT NULL,
    note text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT alert_reviews_explanations_ck CHECK (((cardinality(explanations) <= 20) AND (array_to_string(explanations, ','::text) ~ '^([a-z][a-z0-9_]{0,63}(,[a-z][a-z0-9_]{0,63})*)?$'::text))),
    CONSTRAINT alert_reviews_note_ck CHECK (((note IS NULL) OR ((char_length(btrim(note)) >= 1) AND (char_length(note) <= 2000))))
);

--
-- Name: alerts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alerts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    resident_id uuid NOT NULL,
    epoch_id uuid NOT NULL,
    session_id text NOT NULL,
    triggered_at timestamp with time zone NOT NULL,
    local_date date NOT NULL,
    cusum_value double precision NOT NULL,
    status public.alert_status DEFAULT 'open'::public.alert_status NOT NULL,
    closed_reason text,
    closed_at timestamp with time zone,
    acknowledged_by uuid,
    acknowledged_at timestamp with time zone,
    snoozed_until timestamp with time zone,
    snoozed_by uuid,
    pipeline_run_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT alerts_ack_ck CHECK (((acknowledged_by IS NULL) = (acknowledged_at IS NULL))),
    CONSTRAINT alerts_ack_status_ck CHECK (((status <> 'acknowledged'::public.alert_status) OR (acknowledged_at IS NOT NULL))),
    CONSTRAINT alerts_closed_ck CHECK ((((status = 'closed'::public.alert_status) = (closed_reason IS NOT NULL)) AND ((status = 'closed'::public.alert_status) = (closed_at IS NOT NULL)))),
    CONSTRAINT alerts_closed_reason_ck CHECK (((closed_reason IS NULL) OR (closed_reason = ANY (ARRAY['epoch ended'::text, 'admin'::text, 'superseded by rebuild'::text])))),
    CONSTRAINT alerts_cusum_ck CHECK ((cusum_value >= (0)::double precision)),
    CONSTRAINT alerts_snooze_ck CHECK (((snoozed_until IS NULL) = (snoozed_by IS NULL)))
);

--
-- Name: api_keys; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.api_keys (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name text NOT NULL,
    key_hash text NOT NULL,
    scopes text[] DEFAULT ARRAY['ingest:write'::text] NOT NULL,
    device_id uuid,
    active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    last_used_at timestamp with time zone,
    CONSTRAINT api_keys_key_hash_ck CHECK ((key_hash ~ '^[0-9a-f]{64}$'::text)),
    CONSTRAINT api_keys_name_ck CHECK (((char_length(name) >= 1) AND (char_length(name) <= 120))),
    CONSTRAINT api_keys_scopes_ck CHECK (((cardinality(scopes) >= 1) AND (scopes <@ ARRAY['ingest:write'::text, 'pipeline:run'::text])))
);

--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    id bigint NOT NULL,
    occurred_at timestamp with time zone DEFAULT now() NOT NULL,
    actor_type public.actor_type NOT NULL,
    actor_id text,
    action text NOT NULL,
    entity_type text,
    entity_id text,
    details jsonb DEFAULT '{}'::jsonb NOT NULL,
    ip inet,
    request_id text,
    CONSTRAINT audit_logs_action_ck CHECK ((action ~ '^[a-z_]+(\.[a-z_]+){1,2}$'::text)),
    CONSTRAINT audit_logs_actor_ck CHECK (((actor_type = 'system'::public.actor_type) OR (actor_id IS NOT NULL))),
    CONSTRAINT audit_logs_details_ck CHECK ((jsonb_typeof(details) = 'object'::text))
);

--
-- Name: audit_logs_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_logs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: audit_logs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_logs_id_seq OWNED BY public.audit_logs.id;

--
-- Name: baselines; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.baselines (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    resident_id uuid NOT NULL,
    epoch_id uuid NOT NULL,
    feature_key text NOT NULL,
    n_sessions integer NOT NULL,
    first_session_id text NOT NULL,
    frozen_after_session_id text NOT NULL,
    median double precision NOT NULL,
    mad double precision NOT NULL,
    robust_spread double precision NOT NULL,
    floor_applied boolean NOT NULL,
    frozen_at timestamp with time zone NOT NULL,
    pipeline_run_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT baselines_feature_key_ck CHECK ((feature_key = ANY (ARRAY['loudness_dbfs'::text, 'total_phrase_duration_s'::text, 'speech_rate_syl_per_s'::text, 'articulation_rate_syl_per_s'::text, 'number_of_pauses'::text, 'pause_fraction'::text, 'voiced_fraction'::text, 'mean_f0_hz'::text, 'f0_variability_st'::text, 'jitter_local_pct'::text, 'shimmer_local_pct'::text, 'hnr_db'::text, 'cpps_db'::text, 'alpha_ratio_db'::text, 'hammarberg_index_db'::text, 'mfcc1'::text, 'mfcc2'::text, 'mfcc3'::text, 'mfcc4'::text, 'composite'::text]))),
    CONSTRAINT baselines_n_sessions_ck CHECK ((n_sessions >= 1)),
    CONSTRAINT baselines_spread_ck CHECK (((mad >= (0)::double precision) AND (robust_spread >= (0)::double precision)))
);

--
-- Name: config_parameters; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.config_parameters (
    profile text NOT NULL,
    key text NOT NULL,
    value jsonb NOT NULL,
    description text DEFAULT ''::text NOT NULL,
    updated_by uuid,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT config_parameters_key_ck CHECK ((key ~ '^[a-z][a-z0-9_]{0,63}$'::text)),
    CONSTRAINT config_parameters_profile_ck CHECK ((profile = ANY (ARRAY['production'::text, 'test_v0_1'::text])))
);

--
-- Name: cusum_state; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cusum_state (
    epoch_id uuid NOT NULL,
    resident_id uuid NOT NULL,
    current_tally double precision DEFAULT 0 NOT NULL,
    last_scored_session_id text,
    alarm_on boolean DEFAULT false NOT NULL,
    pipeline_run_id uuid NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT cusum_state_scored_ck CHECK (((last_scored_session_id IS NOT NULL) OR ((current_tally = (0)::double precision) AND (NOT alarm_on)))),
    CONSTRAINT cusum_state_tally_ck CHECK ((current_tally >= (0)::double precision))
);

--
-- Name: data_alerts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.data_alerts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    kind public.data_alert_kind NOT NULL,
    resident_id uuid,
    device_id uuid,
    alert_review_id uuid,
    title text NOT NULL,
    detail text DEFAULT ''::text NOT NULL,
    first_detected_at timestamp with time zone NOT NULL,
    last_detected_at timestamp with time zone NOT NULL,
    status public.data_alert_status DEFAULT 'open'::public.data_alert_status NOT NULL,
    resolved_at timestamp with time zone,
    pipeline_run_id uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT data_alerts_detected_ck CHECK ((last_detected_at >= first_detected_at)),
    CONSTRAINT data_alerts_resolved_ck CHECK (((status = 'resolved'::public.data_alert_status) = (resolved_at IS NOT NULL))),
    CONSTRAINT data_alerts_run_ck CHECK (((kind = 'review_flagged_data_problem'::public.data_alert_kind) = (pipeline_run_id IS NULL))),
    CONSTRAINT data_alerts_subject_ck CHECK ((((kind = 'device_silent'::public.data_alert_kind) AND (device_id IS NOT NULL) AND (resident_id IS NULL) AND (alert_review_id IS NULL)) OR ((kind = ANY (ARRAY['baseline_stalled'::public.data_alert_kind, 'possible_other_speaker'::public.data_alert_kind, 'high_set_aside'::public.data_alert_kind])) AND (resident_id IS NOT NULL) AND (device_id IS NULL) AND (alert_review_id IS NULL)) OR ((kind = 'review_flagged_data_problem'::public.data_alert_kind) AND (resident_id IS NOT NULL) AND (alert_review_id IS NOT NULL)))),
    CONSTRAINT data_alerts_text_ck CHECK ((((char_length(title) >= 1) AND (char_length(title) <= 200)) AND (char_length(detail) <= 500)))
);

--
-- Name: day_ledger; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.day_ledger (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    resident_id uuid NOT NULL,
    local_date date NOT NULL,
    status public.day_status NOT NULL,
    device_id uuid,
    reason text DEFAULT ''::text NOT NULL,
    pipeline_run_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT day_ledger_reason_ck CHECK ((((status = 'checked_in'::public.day_status) AND (reason = ''::text)) OR ((status = 'missing_resident'::public.day_status) AND (reason = 'no record received'::text)) OR ((status = 'missing_device_gap'::public.day_status) AND (device_id IS NOT NULL) AND (reason ~~ 'all residents on shared device % have no record'::text))))
);

--
-- Name: device_assignments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.device_assignments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    resident_id uuid NOT NULL,
    device_id uuid NOT NULL,
    valid_from date NOT NULL,
    valid_to date,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT device_assignments_range_ck CHECK (((valid_to IS NULL) OR (valid_to >= valid_from)))
);

--
-- Name: devices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.devices (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    facility_id uuid NOT NULL,
    device_code text NOT NULL,
    room_label text,
    firmware_version_last text,
    active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT devices_device_code_ck CHECK ((device_code ~ '^[A-Z0-9]{1,16}$'::text)),
    CONSTRAINT devices_room_label_ck CHECK (((room_label IS NULL) OR ((char_length(room_label) >= 1) AND (char_length(room_label) <= 60))))
);

--
-- Name: epochs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.epochs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    resident_id uuid NOT NULL,
    epoch_number integer NOT NULL,
    device_id uuid NOT NULL,
    device_firmware_version text NOT NULL,
    extraction_software_version text NOT NULL,
    started_at timestamp with time zone NOT NULL,
    ended_at timestamp with time zone,
    pipeline_run_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT epochs_number_ck CHECK ((epoch_number >= 1)),
    CONSTRAINT epochs_order_ck CHECK (((ended_at IS NULL) OR (ended_at > started_at)))
);

--
-- Name: evaluation_ground_truth; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.evaluation_ground_truth (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    resident_code text NOT NULL,
    planted_change text NOT NULL,
    true_onset_date date,
    source_file text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT evaluation_ground_truth_onset_ck CHECK (((planted_change = 'None'::text) = (true_onset_date IS NULL))),
    CONSTRAINT evaluation_ground_truth_text_ck CHECK ((((char_length(planted_change) >= 1) AND (char_length(planted_change) <= 60)) AND ((char_length(source_file) >= 1) AND (char_length(source_file) <= 200))))
);

--
-- Name: facilities; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.facilities (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name text NOT NULL,
    timezone text DEFAULT 'America/Chicago'::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT facilities_name_ck CHECK (((char_length(name) >= 1) AND (char_length(name) <= 120))),
    CONSTRAINT facilities_timezone_ck CHECK (((char_length(timezone) >= 1) AND (char_length(timezone) <= 64)))
);

--
-- Name: facility_reference_ranges; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.facility_reference_ranges (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    facility_id uuid NOT NULL,
    feature_key text NOT NULL,
    sex text,
    low double precision NOT NULL,
    high double precision NOT NULL,
    method text NOT NULL,
    n_residents integer NOT NULL,
    computed_at timestamp with time zone NOT NULL,
    pipeline_run_id uuid NOT NULL,
    CONSTRAINT facility_reference_ranges_bounds_ck CHECK ((low <= high)),
    CONSTRAINT facility_reference_ranges_feature_ck CHECK ((feature_key = ANY (ARRAY['loudness_dbfs'::text, 'total_phrase_duration_s'::text, 'speech_rate_syl_per_s'::text, 'articulation_rate_syl_per_s'::text, 'number_of_pauses'::text, 'pause_fraction'::text, 'voiced_fraction'::text, 'mean_f0_hz'::text, 'f0_variability_st'::text, 'jitter_local_pct'::text, 'shimmer_local_pct'::text, 'hnr_db'::text, 'cpps_db'::text, 'alpha_ratio_db'::text, 'hammarberg_index_db'::text, 'mfcc1'::text, 'mfcc2'::text, 'mfcc3'::text, 'mfcc4'::text]))),
    CONSTRAINT facility_reference_ranges_method_ck CHECK (((char_length(method) >= 1) AND (char_length(method) <= 200))),
    CONSTRAINT facility_reference_ranges_n_ck CHECK ((n_residents >= 1)),
    CONSTRAINT facility_reference_ranges_sex_ck CHECK (((sex IS NULL) OR (sex = ANY (ARRAY['F'::text, 'M'::text]))))
);

--
-- Name: ingest_batches; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ingest_batches (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    source public.ingest_source NOT NULL,
    filename text,
    record_count integer DEFAULT 0 NOT NULL,
    accepted_count integer DEFAULT 0 NOT NULL,
    rejected_count integer DEFAULT 0 NOT NULL,
    duplicate_count integer DEFAULT 0 NOT NULL,
    uploaded_by uuid,
    api_key_id uuid,
    received_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ingest_batches_actor_ck CHECK (((source = 'seed'::public.ingest_source) OR (uploaded_by IS NOT NULL) OR (api_key_id IS NOT NULL))),
    CONSTRAINT ingest_batches_counts_ck CHECK (((record_count >= 0) AND (accepted_count >= 0) AND (rejected_count >= 0) AND (duplicate_count >= 0) AND ((accepted_count + rejected_count) <= record_count) AND (duplicate_count <= accepted_count))),
    CONSTRAINT ingest_batches_filename_ck CHECK (((source = 'csv_upload'::public.ingest_source) <= (filename IS NOT NULL)))
);

--
-- Name: ingest_rejections; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ingest_rejections (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    ingest_batch_id uuid,
    api_key_id uuid,
    row_number integer,
    received_at timestamp with time zone DEFAULT now() NOT NULL,
    raw_body jsonb NOT NULL,
    errors jsonb NOT NULL,
    CONSTRAINT ingest_rejections_errors_ck CHECK (((jsonb_typeof(errors) = 'array'::text) AND (jsonb_array_length(errors) >= 1))),
    CONSTRAINT ingest_rejections_row_number_ck CHECK (((row_number IS NULL) OR (row_number >= 1)))
);

--
-- Name: pipeline_runs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pipeline_runs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    trigger public.pipeline_trigger NOT NULL,
    scope jsonb NOT NULL,
    config_profile text NOT NULL,
    config_snapshot jsonb NOT NULL,
    code_version text NOT NULL,
    as_of timestamp with time zone NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    finished_at timestamp with time zone,
    status public.pipeline_run_status DEFAULT 'running'::public.pipeline_run_status NOT NULL,
    counts jsonb DEFAULT '{}'::jsonb NOT NULL,
    warnings jsonb DEFAULT '[]'::jsonb NOT NULL,
    error_message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT pipeline_runs_counts_ck CHECK ((jsonb_typeof(counts) = 'object'::text)),
    CONSTRAINT pipeline_runs_error_ck CHECK (((status = 'failed'::public.pipeline_run_status) = (error_message IS NOT NULL))),
    CONSTRAINT pipeline_runs_finished_ck CHECK (((status = 'running'::public.pipeline_run_status) = (finished_at IS NULL))),
    CONSTRAINT pipeline_runs_order_ck CHECK (((finished_at IS NULL) OR (finished_at >= started_at))),
    CONSTRAINT pipeline_runs_profile_ck CHECK ((config_profile = ANY (ARRAY['production'::text, 'test_v0_1'::text]))),
    CONSTRAINT pipeline_runs_scope_ck CHECK (((scope = '{"type": "all"}'::jsonb) OR (((scope ->> 'type'::text) = 'residents'::text) AND (jsonb_typeof((scope -> 'resident_codes'::text)) = 'array'::text) AND (jsonb_array_length((scope -> 'resident_codes'::text)) >= 1)))),
    CONSTRAINT pipeline_runs_snapshot_ck CHECK ((jsonb_typeof(config_snapshot) = 'object'::text)),
    CONSTRAINT pipeline_runs_warnings_ck CHECK ((jsonb_typeof(warnings) = 'array'::text))
);

--
-- Name: processed_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.processed_sessions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    raw_session_id uuid NOT NULL,
    session_id text NOT NULL,
    resident_id uuid NOT NULL,
    epoch_id uuid,
    status public.session_status NOT NULL,
    reasons text[] DEFAULT '{}'::text[] NOT NULL,
    reason_text text DEFAULT ''::text NOT NULL,
    timestamp_utc timestamp with time zone NOT NULL,
    local_date date NOT NULL,
    local_time time(0) without time zone NOT NULL,
    is_morning boolean NOT NULL,
    screen_detail text,
    baseline_ordinal integer,
    in_baseline boolean DEFAULT false NOT NULL,
    late_arrival boolean DEFAULT false NOT NULL,
    adjusted_features jsonb,
    pipeline_run_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT processed_sessions_adjusted_ck CHECK ((((status = 'duplicate'::public.session_status) AND (adjusted_features IS NULL)) OR ((status <> 'duplicate'::public.session_status) AND (jsonb_typeof(adjusted_features) = 'object'::text) AND (adjusted_features ?& ARRAY['loudness_dbfs'::text, 'total_phrase_duration_s'::text, 'speech_rate_syl_per_s'::text, 'articulation_rate_syl_per_s'::text, 'number_of_pauses'::text, 'pause_fraction'::text, 'voiced_fraction'::text, 'mean_f0_hz'::text, 'f0_variability_st'::text, 'jitter_local_pct'::text, 'shimmer_local_pct'::text, 'hnr_db'::text, 'cpps_db'::text, 'alpha_ratio_db'::text, 'hammarberg_index_db'::text, 'mfcc1'::text, 'mfcc2'::text, 'mfcc3'::text, 'mfcc4'::text])))),
    CONSTRAINT processed_sessions_epoch_ck CHECK ((((status = 'duplicate'::public.session_status) AND (epoch_id IS NULL) AND (NOT late_arrival)) OR ((status <> 'duplicate'::public.session_status) AND ((epoch_id IS NOT NULL) OR late_arrival)))),
    CONSTRAINT processed_sessions_in_baseline_ck CHECK (((NOT in_baseline) OR ((status = 'usable'::public.session_status) AND (NOT late_arrival)))),
    CONSTRAINT processed_sessions_local_date_ck CHECK (((local_date >= (((timestamp_utc AT TIME ZONE 'UTC'::text))::date - 1)) AND (local_date <= (((timestamp_utc AT TIME ZONE 'UTC'::text))::date + 1)))),
    CONSTRAINT processed_sessions_ordinal_ck CHECK (((((status = 'usable'::public.session_status) AND (NOT late_arrival)) = (baseline_ordinal IS NOT NULL)) AND ((baseline_ordinal IS NULL) OR (baseline_ordinal >= 1)))),
    CONSTRAINT processed_sessions_reason_text_ck CHECK ((reason_text = array_to_string(reasons, '; '::text))),
    CONSTRAINT processed_sessions_screen_ck CHECK (((status <> 'quarantined'::public.session_status) OR (screen_detail IS NOT NULL))),
    CONSTRAINT processed_sessions_status_reason_ck CHECK ((((status = 'usable'::public.session_status) AND (NOT late_arrival) AND (cardinality(reasons) = 0)) OR ((status = 'usable'::public.session_status) AND late_arrival AND (reasons = ARRAY['late arrival (not used for baseline or scores)'::text])) OR ((status = 'duplicate'::public.session_status) AND (reasons = ARRAY['session_id already received'::text])) OR ((status = 'set_aside'::public.session_status) AND ((cardinality(reasons) >= 1) AND (cardinality(reasons) <= 3)) AND (reasons <@ ARRAY['quality flag poor'::text, 'noise above limit'::text, 'speech too short'::text])) OR ((status = 'quarantined'::public.session_status) AND (NOT late_arrival) AND (cardinality(reasons) = 1) AND (reasons[1] ~~ 'possible other speaker (F0 z=%; composite features with |z|>=3: %)'::text)) OR ((status = 'quarantined'::public.session_status) AND late_arrival AND (cardinality(reasons) = 2) AND (reasons[1] ~~ 'possible other speaker (F0 z=%; composite features with |z|>=3: %)'::text) AND (reasons[2] = 'late arrival (not used for baseline or scores)'::text))))
);

--
-- Name: raw_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.raw_sessions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    arrival_seq bigint NOT NULL,
    received_at timestamp with time zone DEFAULT now() NOT NULL,
    ingest_batch_id uuid,
    api_key_id uuid,
    payload jsonb NOT NULL,
    ingest_warnings jsonb DEFAULT '[]'::jsonb NOT NULL,
    resident_id uuid NOT NULL,
    device_id uuid NOT NULL,
    schema_version text NOT NULL,
    session_id text NOT NULL,
    resident_code text NOT NULL,
    device_code text NOT NULL,
    timestamp_utc timestamp with time zone NOT NULL,
    mic_noise_level_dbfs double precision NOT NULL,
    audio_quality_flag text NOT NULL,
    extraction_software_version text NOT NULL,
    device_firmware_version text NOT NULL,
    speech_duration_s double precision NOT NULL,
    phrase_id text NOT NULL,
    loudness_dbfs double precision NOT NULL,
    total_phrase_duration_s double precision NOT NULL,
    speech_rate_syl_per_s double precision NOT NULL,
    articulation_rate_syl_per_s double precision NOT NULL,
    number_of_pauses integer NOT NULL,
    pause_fraction double precision NOT NULL,
    voiced_fraction double precision NOT NULL,
    mean_f0_hz double precision NOT NULL,
    f0_variability_st double precision NOT NULL,
    jitter_local_pct double precision NOT NULL,
    shimmer_local_pct double precision NOT NULL,
    hnr_db double precision NOT NULL,
    cpps_db double precision NOT NULL,
    alpha_ratio_db double precision NOT NULL,
    hammarberg_index_db double precision NOT NULL,
    mfcc1 double precision NOT NULL,
    mfcc2 double precision NOT NULL,
    mfcc3 double precision NOT NULL,
    mfcc4 double precision NOT NULL,
    CONSTRAINT raw_sessions_audio_quality_flag_ck CHECK ((audio_quality_flag = ANY (ARRAY['ok'::text, 'poor'::text]))),
    CONSTRAINT raw_sessions_mean_f0_ck CHECK ((mean_f0_hz > (0)::double precision)),
    CONSTRAINT raw_sessions_number_of_pauses_ck CHECK ((number_of_pauses >= 0)),
    CONSTRAINT raw_sessions_pause_fraction_ck CHECK (((pause_fraction >= (0)::double precision) AND (pause_fraction <= (1)::double precision))),
    CONSTRAINT raw_sessions_payload_ck CHECK ((jsonb_typeof(payload) = 'object'::text)),
    CONSTRAINT raw_sessions_phrase_id_ck CHECK (((char_length(phrase_id) >= 1) AND (char_length(phrase_id) <= 16))),
    CONSTRAINT raw_sessions_schema_version_ck CHECK (((char_length(schema_version) >= 1) AND (char_length(schema_version) <= 16))),
    CONSTRAINT raw_sessions_session_id_ck CHECK (((char_length(session_id) >= 1) AND (char_length(session_id) <= 64))),
    CONSTRAINT raw_sessions_speech_duration_ck CHECK ((speech_duration_s >= (0)::double precision)),
    CONSTRAINT raw_sessions_versions_ck CHECK ((((char_length(extraction_software_version) >= 1) AND (char_length(extraction_software_version) <= 64)) AND ((char_length(device_firmware_version) >= 1) AND (char_length(device_firmware_version) <= 64)))),
    CONSTRAINT raw_sessions_voiced_fraction_ck CHECK (((voiced_fraction >= (0)::double precision) AND (voiced_fraction <= (1)::double precision)))
);

--
-- Name: raw_sessions_arrival_seq_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.raw_sessions_arrival_seq_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

--
-- Name: raw_sessions_arrival_seq_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.raw_sessions_arrival_seq_seq OWNED BY public.raw_sessions.arrival_seq;

--
-- Name: residents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.residents (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    facility_id uuid NOT NULL,
    resident_code text NOT NULL,
    sex text,
    cohort public.resident_cohort DEFAULT 'longitudinal'::public.resident_cohort NOT NULL,
    enrolled_on date NOT NULL,
    admitted_on date,
    withdrawn_on date,
    status public.resident_status DEFAULT 'active'::public.resident_status NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT residents_admitted_ck CHECK (((admitted_on IS NULL) OR (admitted_on <= enrolled_on))),
    CONSTRAINT residents_resident_code_ck CHECK ((resident_code ~ '^[A-Z0-9]{1,16}$'::text)),
    CONSTRAINT residents_sex_ck CHECK (((sex IS NULL) OR (sex = ANY (ARRAY['F'::text, 'M'::text])))),
    CONSTRAINT residents_withdrawn_after_enrol_ck CHECK (((withdrawn_on IS NULL) OR (withdrawn_on >= enrolled_on))),
    CONSTRAINT residents_withdrawn_ck CHECK (((status = 'withdrawn'::public.resident_status) = (withdrawn_on IS NOT NULL)))
);

--
-- Name: scores; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scores (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    processed_session_id uuid NOT NULL,
    resident_id uuid NOT NULL,
    epoch_id uuid NOT NULL,
    local_date date NOT NULL,
    is_morning boolean NOT NULL,
    z jsonb NOT NULL,
    composite_raw double precision NOT NULL,
    composite_z double precision NOT NULL,
    cusum_tally double precision NOT NULL,
    alarm_state public.alarm_state NOT NULL,
    pipeline_run_id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT scores_cusum_ck CHECK ((cusum_tally >= (0)::double precision)),
    CONSTRAINT scores_z_ck CHECK (((jsonb_typeof(z) = 'object'::text) AND (z ?& ARRAY['z_loudness_dbfs'::text, 'z_total_phrase_duration_s'::text, 'z_speech_rate_syl_per_s'::text, 'z_articulation_rate_syl_per_s'::text, 'z_number_of_pauses'::text, 'z_pause_fraction'::text, 'z_voiced_fraction'::text])))
);

--
-- Name: staff_notes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.staff_notes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    resident_id uuid NOT NULL,
    alert_id uuid,
    author_user_id uuid NOT NULL,
    note_type public.note_type NOT NULL,
    body text NOT NULL,
    marked_reviewed boolean DEFAULT false NOT NULL,
    supersedes_id uuid,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT staff_notes_body_ck CHECK (((char_length(btrim(body)) >= 1) AND (char_length(body) <= 2000))),
    CONSTRAINT staff_notes_not_self_ck CHECK (((supersedes_id IS NULL) OR (supersedes_id <> id)))
);

--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    email text NOT NULL,
    display_name text NOT NULL,
    password_hash text NOT NULL,
    role public.user_role NOT NULL,
    active boolean DEFAULT true NOT NULL,
    last_login_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT users_display_name_ck CHECK (((char_length(display_name) >= 1) AND (char_length(display_name) <= 120))),
    CONSTRAINT users_email_format_ck CHECK (((email ~ '^[^@\s]+@[^@\s]+\.[^@\s]+$'::text) AND (char_length(email) <= 254))),
    CONSTRAINT users_email_lower_ck CHECK ((email = lower(email))),
    CONSTRAINT users_password_hash_ck CHECK ((password_hash ~~ '$argon2id$%'::text))
);

--
-- Name: audit_logs id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs ALTER COLUMN id SET DEFAULT nextval('public.audit_logs_id_seq'::regclass);

--
-- Name: raw_sessions arrival_seq; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_sessions ALTER COLUMN arrival_seq SET DEFAULT nextval('public.raw_sessions_arrival_seq_seq'::regclass);

--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);

--
-- Name: alert_reviews alert_reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_reviews
    ADD CONSTRAINT alert_reviews_pkey PRIMARY KEY (id);

--
-- Name: alerts alerts_epoch_session_uq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_epoch_session_uq UNIQUE (epoch_id, session_id);

--
-- Name: alerts alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_pkey PRIMARY KEY (id);

--
-- Name: api_keys api_keys_key_hash_uq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_key_hash_uq UNIQUE (key_hash);

--
-- Name: api_keys api_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_pkey PRIMARY KEY (id);

--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);

--
-- Name: baselines baselines_epoch_feature_uq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.baselines
    ADD CONSTRAINT baselines_epoch_feature_uq UNIQUE (epoch_id, feature_key);

--
-- Name: baselines baselines_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.baselines
    ADD CONSTRAINT baselines_pkey PRIMARY KEY (id);

--
-- Name: config_parameters config_parameters_pk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.config_parameters
    ADD CONSTRAINT config_parameters_pk PRIMARY KEY (profile, key);

--
-- Name: cusum_state cusum_state_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cusum_state
    ADD CONSTRAINT cusum_state_pkey PRIMARY KEY (epoch_id);

--
-- Name: data_alerts data_alerts_alert_review_uq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_alerts
    ADD CONSTRAINT data_alerts_alert_review_uq UNIQUE (alert_review_id);

--
-- Name: data_alerts data_alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_alerts
    ADD CONSTRAINT data_alerts_pkey PRIMARY KEY (id);

--
-- Name: day_ledger day_ledger_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.day_ledger
    ADD CONSTRAINT day_ledger_pkey PRIMARY KEY (id);

--
-- Name: day_ledger day_ledger_resident_date_uq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.day_ledger
    ADD CONSTRAINT day_ledger_resident_date_uq UNIQUE (resident_id, local_date);

--
-- Name: device_assignments device_assignments_no_overlap_ex; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.device_assignments
    ADD CONSTRAINT device_assignments_no_overlap_ex EXCLUDE USING gist (resident_id WITH =, daterange(valid_from, valid_to, '[]'::text) WITH &&);

--
-- Name: device_assignments device_assignments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.device_assignments
    ADD CONSTRAINT device_assignments_pkey PRIMARY KEY (id);

--
-- Name: devices devices_device_code_uq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_device_code_uq UNIQUE (device_code);

--
-- Name: devices devices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_pkey PRIMARY KEY (id);

--
-- Name: epochs epochs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.epochs
    ADD CONSTRAINT epochs_pkey PRIMARY KEY (id);

--
-- Name: epochs epochs_resident_number_uq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.epochs
    ADD CONSTRAINT epochs_resident_number_uq UNIQUE (resident_id, epoch_number);

--
-- Name: evaluation_ground_truth evaluation_ground_truth_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_ground_truth
    ADD CONSTRAINT evaluation_ground_truth_pkey PRIMARY KEY (id);

--
-- Name: evaluation_ground_truth evaluation_ground_truth_resident_code_uq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evaluation_ground_truth
    ADD CONSTRAINT evaluation_ground_truth_resident_code_uq UNIQUE (resident_code);

--
-- Name: facilities facilities_name_uq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.facilities
    ADD CONSTRAINT facilities_name_uq UNIQUE (name);

--
-- Name: facilities facilities_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.facilities
    ADD CONSTRAINT facilities_pkey PRIMARY KEY (id);

--
-- Name: facility_reference_ranges facility_reference_ranges_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.facility_reference_ranges
    ADD CONSTRAINT facility_reference_ranges_pkey PRIMARY KEY (id);

--
-- Name: facility_reference_ranges facility_reference_ranges_uq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.facility_reference_ranges
    ADD CONSTRAINT facility_reference_ranges_uq UNIQUE NULLS NOT DISTINCT (facility_id, feature_key, sex, pipeline_run_id);

--
-- Name: ingest_batches ingest_batches_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingest_batches
    ADD CONSTRAINT ingest_batches_pkey PRIMARY KEY (id);

--
-- Name: ingest_rejections ingest_rejections_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingest_rejections
    ADD CONSTRAINT ingest_rejections_pkey PRIMARY KEY (id);

--
-- Name: pipeline_runs pipeline_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pipeline_runs
    ADD CONSTRAINT pipeline_runs_pkey PRIMARY KEY (id);

--
-- Name: processed_sessions processed_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processed_sessions
    ADD CONSTRAINT processed_sessions_pkey PRIMARY KEY (id);

--
-- Name: processed_sessions processed_sessions_raw_session_uq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processed_sessions
    ADD CONSTRAINT processed_sessions_raw_session_uq UNIQUE (raw_session_id);

--
-- Name: raw_sessions raw_sessions_arrival_seq_uq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_sessions
    ADD CONSTRAINT raw_sessions_arrival_seq_uq UNIQUE (arrival_seq);

--
-- Name: raw_sessions raw_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_sessions
    ADD CONSTRAINT raw_sessions_pkey PRIMARY KEY (id);

--
-- Name: residents residents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.residents
    ADD CONSTRAINT residents_pkey PRIMARY KEY (id);

--
-- Name: residents residents_resident_code_uq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.residents
    ADD CONSTRAINT residents_resident_code_uq UNIQUE (resident_code);

--
-- Name: scores scores_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_pkey PRIMARY KEY (id);

--
-- Name: scores scores_processed_session_uq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_processed_session_uq UNIQUE (processed_session_id);

--
-- Name: staff_notes staff_notes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_notes
    ADD CONSTRAINT staff_notes_pkey PRIMARY KEY (id);

--
-- Name: staff_notes staff_notes_supersedes_uq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_notes
    ADD CONSTRAINT staff_notes_supersedes_uq UNIQUE (supersedes_id);

--
-- Name: users users_email_uq; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_uq UNIQUE (email);

--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);

--
-- Name: alert_reviews_alert_created_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX alert_reviews_alert_created_idx ON public.alert_reviews USING btree (alert_id, created_at DESC);

--
-- Name: alert_reviews_outcome_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX alert_reviews_outcome_idx ON public.alert_reviews USING btree (outcome);

--
-- Name: alert_reviews_reviewer_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX alert_reviews_reviewer_idx ON public.alert_reviews USING btree (reviewer_user_id);

--
-- Name: alerts_acknowledged_by_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX alerts_acknowledged_by_idx ON public.alerts USING btree (acknowledged_by);

--
-- Name: alerts_one_active_per_epoch_uq; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX alerts_one_active_per_epoch_uq ON public.alerts USING btree (epoch_id) WHERE (status <> 'closed'::public.alert_status);

--
-- Name: alerts_resident_triggered_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX alerts_resident_triggered_idx ON public.alerts USING btree (resident_id, triggered_at DESC);

--
-- Name: alerts_run_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX alerts_run_idx ON public.alerts USING btree (pipeline_run_id);

--
-- Name: alerts_snoozed_by_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX alerts_snoozed_by_idx ON public.alerts USING btree (snoozed_by);

--
-- Name: alerts_status_triggered_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX alerts_status_triggered_idx ON public.alerts USING btree (status, triggered_at DESC);

--
-- Name: api_keys_device_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX api_keys_device_idx ON public.api_keys USING btree (device_id);

--
-- Name: audit_logs_action_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_action_idx ON public.audit_logs USING btree (action, occurred_at DESC);

--
-- Name: audit_logs_actor_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_actor_idx ON public.audit_logs USING btree (actor_type, actor_id, occurred_at DESC);

--
-- Name: audit_logs_entity_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_entity_idx ON public.audit_logs USING btree (entity_type, entity_id);

--
-- Name: audit_logs_occurred_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX audit_logs_occurred_idx ON public.audit_logs USING btree (occurred_at DESC);

--
-- Name: baselines_resident_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX baselines_resident_idx ON public.baselines USING btree (resident_id);

--
-- Name: baselines_run_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX baselines_run_idx ON public.baselines USING btree (pipeline_run_id);

--
-- Name: config_parameters_updated_by_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX config_parameters_updated_by_idx ON public.config_parameters USING btree (updated_by);

--
-- Name: cusum_state_resident_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX cusum_state_resident_idx ON public.cusum_state USING btree (resident_id);

--
-- Name: cusum_state_run_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX cusum_state_run_idx ON public.cusum_state USING btree (pipeline_run_id);

--
-- Name: data_alerts_device_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX data_alerts_device_idx ON public.data_alerts USING btree (device_id);

--
-- Name: data_alerts_open_subject_uq; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX data_alerts_open_subject_uq ON public.data_alerts USING btree (kind, resident_id, device_id) NULLS NOT DISTINCT WHERE ((status = 'open'::public.data_alert_status) AND (kind <> 'review_flagged_data_problem'::public.data_alert_kind));

--
-- Name: data_alerts_resident_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX data_alerts_resident_idx ON public.data_alerts USING btree (resident_id);

--
-- Name: data_alerts_run_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX data_alerts_run_idx ON public.data_alerts USING btree (pipeline_run_id);

--
-- Name: data_alerts_status_detected_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX data_alerts_status_detected_idx ON public.data_alerts USING btree (status, last_detected_at DESC);

--
-- Name: day_ledger_device_date_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX day_ledger_device_date_idx ON public.day_ledger USING btree (device_id, local_date);

--
-- Name: day_ledger_missing_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX day_ledger_missing_idx ON public.day_ledger USING btree (resident_id, local_date) WHERE (status <> 'checked_in'::public.day_status);

--
-- Name: day_ledger_run_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX day_ledger_run_idx ON public.day_ledger USING btree (pipeline_run_id);

--
-- Name: device_assignments_device_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX device_assignments_device_idx ON public.device_assignments USING btree (device_id, valid_from);

--
-- Name: device_assignments_resident_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX device_assignments_resident_idx ON public.device_assignments USING btree (resident_id, valid_from);

--
-- Name: devices_facility_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX devices_facility_idx ON public.devices USING btree (facility_id);

--
-- Name: epochs_current_uq; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX epochs_current_uq ON public.epochs USING btree (resident_id) WHERE (ended_at IS NULL);

--
-- Name: epochs_device_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX epochs_device_idx ON public.epochs USING btree (device_id);

--
-- Name: epochs_run_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX epochs_run_idx ON public.epochs USING btree (pipeline_run_id);

--
-- Name: facility_reference_ranges_lookup_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX facility_reference_ranges_lookup_idx ON public.facility_reference_ranges USING btree (facility_id, feature_key, computed_at DESC);

--
-- Name: facility_reference_ranges_run_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX facility_reference_ranges_run_idx ON public.facility_reference_ranges USING btree (pipeline_run_id);

--
-- Name: ingest_batches_api_key_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ingest_batches_api_key_idx ON public.ingest_batches USING btree (api_key_id);

--
-- Name: ingest_batches_received_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ingest_batches_received_idx ON public.ingest_batches USING btree (received_at DESC);

--
-- Name: ingest_batches_uploaded_by_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ingest_batches_uploaded_by_idx ON public.ingest_batches USING btree (uploaded_by);

--
-- Name: ingest_rejections_api_key_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ingest_rejections_api_key_idx ON public.ingest_rejections USING btree (api_key_id);

--
-- Name: ingest_rejections_batch_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ingest_rejections_batch_idx ON public.ingest_rejections USING btree (ingest_batch_id);

--
-- Name: ingest_rejections_received_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ingest_rejections_received_idx ON public.ingest_rejections USING btree (received_at DESC);

--
-- Name: pipeline_runs_started_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX pipeline_runs_started_idx ON public.pipeline_runs USING btree (started_at DESC);

--
-- Name: pipeline_runs_status_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX pipeline_runs_status_idx ON public.pipeline_runs USING btree (status) WHERE (status = 'running'::public.pipeline_run_status);

--
-- Name: processed_sessions_epoch_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX processed_sessions_epoch_idx ON public.processed_sessions USING btree (epoch_id, timestamp_utc);

--
-- Name: processed_sessions_resident_date_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX processed_sessions_resident_date_idx ON public.processed_sessions USING btree (resident_id, local_date) INCLUDE (status);

--
-- Name: processed_sessions_resident_ts_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX processed_sessions_resident_ts_idx ON public.processed_sessions USING btree (resident_id, timestamp_utc DESC) WHERE (status <> 'duplicate'::public.session_status);

--
-- Name: processed_sessions_run_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX processed_sessions_run_idx ON public.processed_sessions USING btree (pipeline_run_id);

--
-- Name: processed_sessions_session_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX processed_sessions_session_id_idx ON public.processed_sessions USING btree (session_id);

--
-- Name: raw_sessions_api_key_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX raw_sessions_api_key_idx ON public.raw_sessions USING btree (api_key_id);

--
-- Name: raw_sessions_batch_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX raw_sessions_batch_idx ON public.raw_sessions USING btree (ingest_batch_id);

--
-- Name: raw_sessions_device_ts_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX raw_sessions_device_ts_idx ON public.raw_sessions USING btree (device_id, timestamp_utc DESC);

--
-- Name: raw_sessions_resident_ts_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX raw_sessions_resident_ts_idx ON public.raw_sessions USING btree (resident_id, timestamp_utc, arrival_seq);

--
-- Name: raw_sessions_session_id_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX raw_sessions_session_id_idx ON public.raw_sessions USING btree (session_id, arrival_seq);

--
-- Name: residents_facility_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX residents_facility_idx ON public.residents USING btree (facility_id);

--
-- Name: residents_status_cohort_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX residents_status_cohort_idx ON public.residents USING btree (status, cohort);

--
-- Name: scores_epoch_date_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX scores_epoch_date_idx ON public.scores USING btree (epoch_id, local_date);

--
-- Name: scores_resident_date_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX scores_resident_date_idx ON public.scores USING btree (resident_id, local_date);

--
-- Name: scores_run_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX scores_run_idx ON public.scores USING btree (pipeline_run_id);

--
-- Name: staff_notes_alert_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX staff_notes_alert_idx ON public.staff_notes USING btree (alert_id);

--
-- Name: staff_notes_author_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX staff_notes_author_idx ON public.staff_notes USING btree (author_user_id);

--
-- Name: staff_notes_resident_created_idx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX staff_notes_resident_created_idx ON public.staff_notes USING btree (resident_id, created_at DESC);

--
-- Name: alerts alerts_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER alerts_set_updated_at BEFORE UPDATE ON public.alerts FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

--
-- Name: api_keys api_keys_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER api_keys_set_updated_at BEFORE UPDATE ON public.api_keys FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

--
-- Name: audit_logs audit_logs_no_truncate; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_logs_no_truncate BEFORE TRUNCATE ON public.audit_logs FOR EACH STATEMENT EXECUTE FUNCTION public.reject_mutation();

--
-- Name: audit_logs audit_logs_no_update_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_logs_no_update_delete BEFORE DELETE OR UPDATE ON public.audit_logs FOR EACH ROW EXECUTE FUNCTION public.reject_mutation();

--
-- Name: config_parameters config_parameters_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER config_parameters_set_updated_at BEFORE UPDATE ON public.config_parameters FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

--
-- Name: cusum_state cusum_state_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER cusum_state_set_updated_at BEFORE UPDATE ON public.cusum_state FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

--
-- Name: data_alerts data_alerts_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER data_alerts_set_updated_at BEFORE UPDATE ON public.data_alerts FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

--
-- Name: device_assignments device_assignments_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER device_assignments_set_updated_at BEFORE UPDATE ON public.device_assignments FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

--
-- Name: devices devices_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER devices_set_updated_at BEFORE UPDATE ON public.devices FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

--
-- Name: epochs epochs_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER epochs_set_updated_at BEFORE UPDATE ON public.epochs FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

--
-- Name: facilities facilities_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER facilities_set_updated_at BEFORE UPDATE ON public.facilities FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

--
-- Name: ingest_batches ingest_batches_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER ingest_batches_set_updated_at BEFORE UPDATE ON public.ingest_batches FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

--
-- Name: pipeline_runs pipeline_runs_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER pipeline_runs_set_updated_at BEFORE UPDATE ON public.pipeline_runs FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

--
-- Name: raw_sessions raw_sessions_no_truncate; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER raw_sessions_no_truncate BEFORE TRUNCATE ON public.raw_sessions FOR EACH STATEMENT EXECUTE FUNCTION public.reject_mutation();

--
-- Name: raw_sessions raw_sessions_no_update_delete; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER raw_sessions_no_update_delete BEFORE DELETE OR UPDATE ON public.raw_sessions FOR EACH ROW EXECUTE FUNCTION public.reject_mutation();

--
-- Name: residents residents_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER residents_set_updated_at BEFORE UPDATE ON public.residents FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

--
-- Name: users users_set_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER users_set_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

--
-- Name: alert_reviews alert_reviews_alert_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_reviews
    ADD CONSTRAINT alert_reviews_alert_id_fkey FOREIGN KEY (alert_id) REFERENCES public.alerts(id) ON DELETE RESTRICT;

--
-- Name: alert_reviews alert_reviews_reviewer_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alert_reviews
    ADD CONSTRAINT alert_reviews_reviewer_user_id_fkey FOREIGN KEY (reviewer_user_id) REFERENCES public.users(id) ON DELETE RESTRICT;

--
-- Name: alerts alerts_acknowledged_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_acknowledged_by_fkey FOREIGN KEY (acknowledged_by) REFERENCES public.users(id) ON DELETE RESTRICT;

--
-- Name: alerts alerts_epoch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_epoch_id_fkey FOREIGN KEY (epoch_id) REFERENCES public.epochs(id) ON DELETE RESTRICT;

--
-- Name: alerts alerts_pipeline_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_pipeline_run_id_fkey FOREIGN KEY (pipeline_run_id) REFERENCES public.pipeline_runs(id) ON DELETE RESTRICT;

--
-- Name: alerts alerts_resident_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_resident_id_fkey FOREIGN KEY (resident_id) REFERENCES public.residents(id) ON DELETE RESTRICT;

--
-- Name: alerts alerts_snoozed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_snoozed_by_fkey FOREIGN KEY (snoozed_by) REFERENCES public.users(id) ON DELETE RESTRICT;

--
-- Name: api_keys api_keys_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(id) ON DELETE RESTRICT;

--
-- Name: baselines baselines_epoch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.baselines
    ADD CONSTRAINT baselines_epoch_id_fkey FOREIGN KEY (epoch_id) REFERENCES public.epochs(id) ON DELETE RESTRICT;

--
-- Name: baselines baselines_pipeline_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.baselines
    ADD CONSTRAINT baselines_pipeline_run_id_fkey FOREIGN KEY (pipeline_run_id) REFERENCES public.pipeline_runs(id) ON DELETE RESTRICT;

--
-- Name: baselines baselines_resident_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.baselines
    ADD CONSTRAINT baselines_resident_id_fkey FOREIGN KEY (resident_id) REFERENCES public.residents(id) ON DELETE RESTRICT;

--
-- Name: config_parameters config_parameters_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.config_parameters
    ADD CONSTRAINT config_parameters_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.users(id) ON DELETE RESTRICT;

--
-- Name: cusum_state cusum_state_epoch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cusum_state
    ADD CONSTRAINT cusum_state_epoch_id_fkey FOREIGN KEY (epoch_id) REFERENCES public.epochs(id) ON DELETE RESTRICT;

--
-- Name: cusum_state cusum_state_pipeline_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cusum_state
    ADD CONSTRAINT cusum_state_pipeline_run_id_fkey FOREIGN KEY (pipeline_run_id) REFERENCES public.pipeline_runs(id) ON DELETE RESTRICT;

--
-- Name: cusum_state cusum_state_resident_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cusum_state
    ADD CONSTRAINT cusum_state_resident_id_fkey FOREIGN KEY (resident_id) REFERENCES public.residents(id) ON DELETE RESTRICT;

--
-- Name: data_alerts data_alerts_alert_review_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_alerts
    ADD CONSTRAINT data_alerts_alert_review_id_fkey FOREIGN KEY (alert_review_id) REFERENCES public.alert_reviews(id) ON DELETE RESTRICT;

--
-- Name: data_alerts data_alerts_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_alerts
    ADD CONSTRAINT data_alerts_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(id) ON DELETE RESTRICT;

--
-- Name: data_alerts data_alerts_pipeline_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_alerts
    ADD CONSTRAINT data_alerts_pipeline_run_id_fkey FOREIGN KEY (pipeline_run_id) REFERENCES public.pipeline_runs(id) ON DELETE RESTRICT;

--
-- Name: data_alerts data_alerts_resident_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.data_alerts
    ADD CONSTRAINT data_alerts_resident_id_fkey FOREIGN KEY (resident_id) REFERENCES public.residents(id) ON DELETE RESTRICT;

--
-- Name: day_ledger day_ledger_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.day_ledger
    ADD CONSTRAINT day_ledger_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(id) ON DELETE RESTRICT;

--
-- Name: day_ledger day_ledger_pipeline_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.day_ledger
    ADD CONSTRAINT day_ledger_pipeline_run_id_fkey FOREIGN KEY (pipeline_run_id) REFERENCES public.pipeline_runs(id) ON DELETE RESTRICT;

--
-- Name: day_ledger day_ledger_resident_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.day_ledger
    ADD CONSTRAINT day_ledger_resident_id_fkey FOREIGN KEY (resident_id) REFERENCES public.residents(id) ON DELETE RESTRICT;

--
-- Name: device_assignments device_assignments_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.device_assignments
    ADD CONSTRAINT device_assignments_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(id) ON DELETE RESTRICT;

--
-- Name: device_assignments device_assignments_resident_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.device_assignments
    ADD CONSTRAINT device_assignments_resident_id_fkey FOREIGN KEY (resident_id) REFERENCES public.residents(id) ON DELETE RESTRICT;

--
-- Name: devices devices_facility_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.devices
    ADD CONSTRAINT devices_facility_id_fkey FOREIGN KEY (facility_id) REFERENCES public.facilities(id) ON DELETE RESTRICT;

--
-- Name: epochs epochs_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.epochs
    ADD CONSTRAINT epochs_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(id) ON DELETE RESTRICT;

--
-- Name: epochs epochs_pipeline_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.epochs
    ADD CONSTRAINT epochs_pipeline_run_id_fkey FOREIGN KEY (pipeline_run_id) REFERENCES public.pipeline_runs(id) ON DELETE RESTRICT;

--
-- Name: epochs epochs_resident_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.epochs
    ADD CONSTRAINT epochs_resident_id_fkey FOREIGN KEY (resident_id) REFERENCES public.residents(id) ON DELETE RESTRICT;

--
-- Name: facility_reference_ranges facility_reference_ranges_facility_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.facility_reference_ranges
    ADD CONSTRAINT facility_reference_ranges_facility_id_fkey FOREIGN KEY (facility_id) REFERENCES public.facilities(id) ON DELETE RESTRICT;

--
-- Name: facility_reference_ranges facility_reference_ranges_pipeline_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.facility_reference_ranges
    ADD CONSTRAINT facility_reference_ranges_pipeline_run_id_fkey FOREIGN KEY (pipeline_run_id) REFERENCES public.pipeline_runs(id) ON DELETE RESTRICT;

--
-- Name: ingest_batches ingest_batches_api_key_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingest_batches
    ADD CONSTRAINT ingest_batches_api_key_id_fkey FOREIGN KEY (api_key_id) REFERENCES public.api_keys(id) ON DELETE RESTRICT;

--
-- Name: ingest_batches ingest_batches_uploaded_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingest_batches
    ADD CONSTRAINT ingest_batches_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES public.users(id) ON DELETE RESTRICT;

--
-- Name: ingest_rejections ingest_rejections_api_key_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingest_rejections
    ADD CONSTRAINT ingest_rejections_api_key_id_fkey FOREIGN KEY (api_key_id) REFERENCES public.api_keys(id) ON DELETE RESTRICT;

--
-- Name: ingest_rejections ingest_rejections_ingest_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingest_rejections
    ADD CONSTRAINT ingest_rejections_ingest_batch_id_fkey FOREIGN KEY (ingest_batch_id) REFERENCES public.ingest_batches(id) ON DELETE RESTRICT;

--
-- Name: processed_sessions processed_sessions_epoch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processed_sessions
    ADD CONSTRAINT processed_sessions_epoch_id_fkey FOREIGN KEY (epoch_id) REFERENCES public.epochs(id) ON DELETE RESTRICT;

--
-- Name: processed_sessions processed_sessions_pipeline_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processed_sessions
    ADD CONSTRAINT processed_sessions_pipeline_run_id_fkey FOREIGN KEY (pipeline_run_id) REFERENCES public.pipeline_runs(id) ON DELETE RESTRICT;

--
-- Name: processed_sessions processed_sessions_raw_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processed_sessions
    ADD CONSTRAINT processed_sessions_raw_session_id_fkey FOREIGN KEY (raw_session_id) REFERENCES public.raw_sessions(id) ON DELETE RESTRICT;

--
-- Name: processed_sessions processed_sessions_resident_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processed_sessions
    ADD CONSTRAINT processed_sessions_resident_id_fkey FOREIGN KEY (resident_id) REFERENCES public.residents(id) ON DELETE RESTRICT;

--
-- Name: raw_sessions raw_sessions_api_key_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_sessions
    ADD CONSTRAINT raw_sessions_api_key_id_fkey FOREIGN KEY (api_key_id) REFERENCES public.api_keys(id) ON DELETE RESTRICT;

--
-- Name: raw_sessions raw_sessions_device_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_sessions
    ADD CONSTRAINT raw_sessions_device_id_fkey FOREIGN KEY (device_id) REFERENCES public.devices(id) ON DELETE RESTRICT;

--
-- Name: raw_sessions raw_sessions_ingest_batch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_sessions
    ADD CONSTRAINT raw_sessions_ingest_batch_id_fkey FOREIGN KEY (ingest_batch_id) REFERENCES public.ingest_batches(id) ON DELETE RESTRICT;

--
-- Name: raw_sessions raw_sessions_resident_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.raw_sessions
    ADD CONSTRAINT raw_sessions_resident_id_fkey FOREIGN KEY (resident_id) REFERENCES public.residents(id) ON DELETE RESTRICT;

--
-- Name: residents residents_facility_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.residents
    ADD CONSTRAINT residents_facility_id_fkey FOREIGN KEY (facility_id) REFERENCES public.facilities(id) ON DELETE RESTRICT;

--
-- Name: scores scores_epoch_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_epoch_id_fkey FOREIGN KEY (epoch_id) REFERENCES public.epochs(id) ON DELETE RESTRICT;

--
-- Name: scores scores_pipeline_run_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_pipeline_run_id_fkey FOREIGN KEY (pipeline_run_id) REFERENCES public.pipeline_runs(id) ON DELETE RESTRICT;

--
-- Name: scores scores_processed_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_processed_session_id_fkey FOREIGN KEY (processed_session_id) REFERENCES public.processed_sessions(id) ON DELETE CASCADE;

--
-- Name: scores scores_resident_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scores
    ADD CONSTRAINT scores_resident_id_fkey FOREIGN KEY (resident_id) REFERENCES public.residents(id) ON DELETE RESTRICT;

--
-- Name: staff_notes staff_notes_alert_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_notes
    ADD CONSTRAINT staff_notes_alert_id_fkey FOREIGN KEY (alert_id) REFERENCES public.alerts(id) ON DELETE RESTRICT;

--
-- Name: staff_notes staff_notes_author_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_notes
    ADD CONSTRAINT staff_notes_author_user_id_fkey FOREIGN KEY (author_user_id) REFERENCES public.users(id) ON DELETE RESTRICT;

--
-- Name: staff_notes staff_notes_resident_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_notes
    ADD CONSTRAINT staff_notes_resident_id_fkey FOREIGN KEY (resident_id) REFERENCES public.residents(id) ON DELETE RESTRICT;

--
-- Name: staff_notes staff_notes_supersedes_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.staff_notes
    ADD CONSTRAINT staff_notes_supersedes_id_fkey FOREIGN KEY (supersedes_id) REFERENCES public.staff_notes(id) ON DELETE RESTRICT;

--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: -
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO echowell_app;
GRANT USAGE ON SCHEMA public TO echowell_readonly;

--
-- Name: TABLE alert_reviews; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT ON TABLE public.alert_reviews TO echowell_app;
GRANT SELECT ON TABLE public.alert_reviews TO echowell_readonly;

--
-- Name: TABLE alerts; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.alerts TO echowell_app;
GRANT SELECT ON TABLE public.alerts TO echowell_readonly;

--
-- Name: TABLE api_keys; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.api_keys TO echowell_app;

--
-- Name: COLUMN api_keys.id; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT(id) ON TABLE public.api_keys TO echowell_readonly;

--
-- Name: COLUMN api_keys.name; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT(name) ON TABLE public.api_keys TO echowell_readonly;

--
-- Name: COLUMN api_keys.scopes; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT(scopes) ON TABLE public.api_keys TO echowell_readonly;

--
-- Name: COLUMN api_keys.device_id; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT(device_id) ON TABLE public.api_keys TO echowell_readonly;

--
-- Name: COLUMN api_keys.active; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT(active) ON TABLE public.api_keys TO echowell_readonly;

--
-- Name: COLUMN api_keys.created_at; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT(created_at) ON TABLE public.api_keys TO echowell_readonly;

--
-- Name: COLUMN api_keys.updated_at; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT(updated_at) ON TABLE public.api_keys TO echowell_readonly;

--
-- Name: COLUMN api_keys.last_used_at; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT(last_used_at) ON TABLE public.api_keys TO echowell_readonly;

--
-- Name: TABLE audit_logs; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT ON TABLE public.audit_logs TO echowell_app;
GRANT SELECT ON TABLE public.audit_logs TO echowell_readonly;

--
-- Name: SEQUENCE audit_logs_id_seq; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,USAGE ON SEQUENCE public.audit_logs_id_seq TO echowell_app;

--
-- Name: TABLE baselines; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT ON TABLE public.baselines TO echowell_app;
GRANT SELECT ON TABLE public.baselines TO echowell_readonly;

--
-- Name: TABLE config_parameters; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.config_parameters TO echowell_app;
GRANT SELECT ON TABLE public.config_parameters TO echowell_readonly;

--
-- Name: TABLE cusum_state; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.cusum_state TO echowell_app;
GRANT SELECT ON TABLE public.cusum_state TO echowell_readonly;

--
-- Name: TABLE data_alerts; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.data_alerts TO echowell_app;
GRANT SELECT ON TABLE public.data_alerts TO echowell_readonly;

--
-- Name: TABLE day_ledger; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.day_ledger TO echowell_app;
GRANT SELECT ON TABLE public.day_ledger TO echowell_readonly;

--
-- Name: TABLE device_assignments; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.device_assignments TO echowell_app;
GRANT SELECT ON TABLE public.device_assignments TO echowell_readonly;

--
-- Name: TABLE devices; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.devices TO echowell_app;
GRANT SELECT ON TABLE public.devices TO echowell_readonly;

--
-- Name: TABLE epochs; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.epochs TO echowell_app;
GRANT SELECT ON TABLE public.epochs TO echowell_readonly;

--
-- Name: TABLE evaluation_ground_truth; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT ON TABLE public.evaluation_ground_truth TO echowell_readonly;

--
-- Name: TABLE facilities; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.facilities TO echowell_app;
GRANT SELECT ON TABLE public.facilities TO echowell_readonly;

--
-- Name: TABLE facility_reference_ranges; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.facility_reference_ranges TO echowell_app;
GRANT SELECT ON TABLE public.facility_reference_ranges TO echowell_readonly;

--
-- Name: TABLE ingest_batches; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.ingest_batches TO echowell_app;
GRANT SELECT ON TABLE public.ingest_batches TO echowell_readonly;

--
-- Name: TABLE ingest_rejections; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT ON TABLE public.ingest_rejections TO echowell_app;
GRANT SELECT ON TABLE public.ingest_rejections TO echowell_readonly;

--
-- Name: TABLE pipeline_runs; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.pipeline_runs TO echowell_app;
GRANT SELECT ON TABLE public.pipeline_runs TO echowell_readonly;

--
-- Name: TABLE processed_sessions; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.processed_sessions TO echowell_app;
GRANT SELECT ON TABLE public.processed_sessions TO echowell_readonly;

--
-- Name: TABLE raw_sessions; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT ON TABLE public.raw_sessions TO echowell_app;
GRANT SELECT ON TABLE public.raw_sessions TO echowell_readonly;

--
-- Name: SEQUENCE raw_sessions_arrival_seq_seq; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,USAGE ON SEQUENCE public.raw_sessions_arrival_seq_seq TO echowell_app;

--
-- Name: TABLE residents; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.residents TO echowell_app;
GRANT SELECT ON TABLE public.residents TO echowell_readonly;

--
-- Name: TABLE scores; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT,DELETE,UPDATE ON TABLE public.scores TO echowell_app;
GRANT SELECT ON TABLE public.scores TO echowell_readonly;

--
-- Name: TABLE staff_notes; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT ON TABLE public.staff_notes TO echowell_app;
GRANT SELECT ON TABLE public.staff_notes TO echowell_readonly;

--
-- Name: TABLE users; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT,INSERT,UPDATE ON TABLE public.users TO echowell_app;

--
-- Name: COLUMN users.id; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT(id) ON TABLE public.users TO echowell_readonly;

--
-- Name: COLUMN users.email; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT(email) ON TABLE public.users TO echowell_readonly;

--
-- Name: COLUMN users.display_name; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT(display_name) ON TABLE public.users TO echowell_readonly;

--
-- Name: COLUMN users.role; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT(role) ON TABLE public.users TO echowell_readonly;

--
-- Name: COLUMN users.active; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT(active) ON TABLE public.users TO echowell_readonly;

--
-- Name: COLUMN users.last_login_at; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT(last_login_at) ON TABLE public.users TO echowell_readonly;

--
-- Name: COLUMN users.created_at; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT(created_at) ON TABLE public.users TO echowell_readonly;

--
-- Name: COLUMN users.updated_at; Type: ACL; Schema: public; Owner: -
--

GRANT SELECT(updated_at) ON TABLE public.users TO echowell_readonly;

--
-- PostgreSQL database dump complete
--

