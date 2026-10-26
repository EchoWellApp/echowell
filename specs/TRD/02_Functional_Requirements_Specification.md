# 02 Functional Requirements Specification

Document ID: ECHOWELL-TRD-02 · Version 0.6 (draft for review) · Date: 18 October 2026, revised 26 October 2026 · Owner: Team 2 · Status: Draft

## 1. Purpose

This document is the master list of EchoWell functional requirements (FR-xxx). Each FR states one testable system behaviour, traces to a business requirement (BR-xx, TRD 00) and a source (SRC-xx), and points to the TRD that specifies it in detail. The document also defines the use cases (UC-xx) that exercise the FRs and closes with FR → BR and UC → FR traceability tables.

Where an FR and a detailed TRD differ, the detailed TRD governs the "how" and this document governs the "what"; a contradiction in the "what" is a defect to be raised with the lead.

## 2. Scope

**In scope:** every user-visible or interface-visible behaviour of the EchoWell MVP: ingestion, validation and duplicate handling, the ten analytics stages, persistence of results, the dashboard pages of wireframe v0.2 (Resident list, Resident chart with its Summary, Review and notes, Voice trends, Baseline, Check-in log and Device sections, New admissions, Study team with Devices and data problems, Login, Admin; TRD 24 D-110), alarm review and data alerts, staff notes, authentication and roles, researcher analytics read-outs, audit logging.

**Out of scope:** quality attributes (TRD 03), Team 1 device behaviour, outbound alert delivery (OQ-06), data retention and deletion (OQ-01), EWMA trend display (OQ-18), LLM or ML features (BR-18), audio handling of any kind (BR-01).

## 3. References

| ID | Used for |
|---|---|
| SRC-02 | Storage flow and processing stages |
| SRC-03 | Parameters, expected results (acceptance answer key) |
| SRC-04 | Reference implementation of the rules |
| SRC-05 | Ingest CSV header and test input |
| SRC-21 | Clinical dashboard wireframe v0.2 (`specs/UI-wireframe/echowell-wireframes-v0.2.html`): Resident list, Resident chart (Summary, Review and notes, Voice trends, Baseline, Check-in log, Device), New admissions, Study team |
| SRC-09, SRC-10, SRC-11, SRC-18, SRC-19 | Wireframes v0.1 (Residents overview, Resident detail, New admission check, Alert review, Analytics): superseded by SRC-21 (TRD 24 D-108); removed from the repository |
| SRC-12 | Page requirements in the TRD Generation Prompt |
| SRC-13 | Record fields, extractor, phrase ID |
| SRC-14 | Fixed constraints |
| Contract §19–§20 | Owner wireframe decision; lead reconciliation decisions R1–R17 (cited as R-numbers) |
| TRD 24 | Decisions D-108 to D-114 (wireframe v0.2), OQ-31, OQ-32 |

Related TRDs and the prefixes their detailed requirements use: 04 Frontend (FE), 05 Backend API (API), 06 Database (DB), 07 Analytics Engine (ANL), 08 Baseline and Scoring (BSC), 09 CUSUM and Alerting (CUS), 10 Ingestion and Validation (ING), 11 UI/UX (UX), 12 Security (SEC), 17 Logging (LOG), 19 OpenAPI (OAS), 20 PostgreSQL Schema (PGS).

## 4. Requirements

Column "Detail" names the TRD and prefix where the behaviour is specified in full (e.g. "10 ING" = TRD 10, ING-xxx requirements). Priorities: Must / Should / May. Verification: T = Test, I = Inspection, A = Analysis, D = Demo.

### 4.1 Definitions used in this document

| Term | Definition |
|---|---|
| As-of time | For a pipeline run, in order of precedence: explicit `as_of` in `POST /api/v1/pipeline/run` → `PIPELINE_AS_OF` environment variable (refused when APP_ENV=production) → current time. Read endpoints use the `as_of` of the latest succeeded run, reported in `meta.as_of` (R21, superseding R11). In-process tests freeze the clock. Reference data: 2026-10-30 15:00 America/Chicago. |
| Last 30 days | The 30 local calendar days ending on the as-of local date, inclusive, excluding days before the resident's enrolment date (for the test data: 1–30 Oct 2026) (R10). |
| Last check-in | The local timestamp of the resident's latest non-duplicate record of any status (usable, set aside or quarantined) (R10). |
| Open alarm | An `alerts` row of the current epoch with status `open` or `acknowledged`; the alarm stays on after review (OQ-05). |
| Current epoch | The resident's highest-numbered epoch. |
| Watching since | The local date of the first scored session in the current epoch (R09: Oct 17); before any scored session exists, the local date after the freeze session's local date (R9). |
| Alarm since | The `local_date` of the open alert of the current epoch. |
| Silent day (device) | A local day, while the device is assigned to at least one resident, on which the device received no non-duplicate record from any assigned resident; applies to every device, shared or not (TRD 06 DB-044; API field `silent_days_last_30`, TRD 19). This is the single definition used by all TRDs. |
| Device-gap day | A silent day of a device assigned to 2 or more residents that day, i.e. the day ledger records `missing_device_gap` for its residents (API field `device_gap_days_last_30`). The Study team Devices text "Silent all day <Mon D>." lists device-gap days. |
| No-upload day | Retired term (see "Silent day (device)"). |

### 4.2 Ingestion (BR-01, BR-02)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-001 | The system shall accept one feature record per request at `POST /api/v1/sessions` from a caller presenting an `X-API-Key` with scope `ingest:write`. | Must | BR-01, SRC-13 §6, ASM-05 | 10 ING, 05 API | T |
| FR-002 | The system shall accept a batch of records at `POST /api/v1/ingest` as JSON `{"records": [...]}`. | Must | BR-01, BR-15 | 10 ING, 05 API | T |
| FR-003 | The system shall accept a multipart CSV upload at `POST /api/v1/ingest` whose header, after feature-name mapping, consists of exactly the 30 fields of the SRC-05 header (schema v0.1) in any column order; other headers are rejected with `CSV_HEADER_MISMATCH` (TRD 10 ING-031). | Must | BR-01, BR-15, SRC-05 | 10 ING | T |
| FR-004 | The batch endpoint shall accept callers holding an API key with scope `ingest:write` or a user session with role `admin`. | Must | BR-01, BR-16 | 05 API, 12 SEC | T |
| FR-005 | The system shall store every schema-valid arrival, including repeat `session_id`s, as one new row in `raw_sessions` with `arrival_seq`, `received_at`, `ingest_batch_id` and the payload exactly as received. | Must | BR-02, SRC-02 diagram 1 | 10 ING, 06 DB | T |
| FR-006 | The system shall never modify or delete a `raw_sessions` row. | Must | BR-02, SRC-02 | 06 DB, 20 PGS | T |
| FR-007 | For the first arrival of a `session_id`, `POST /api/v1/sessions` shall return 201 with `raw_session_id`, `arrival_seq` and `status_after_processing` (`usable`, `set_aside`, `quarantined`, or `pending` when the record is stored but the synchronous pipeline failed; the next run processes it). | Must | BR-01, BR-02, R23 | 05 API | T |
| FR-008 | For a repeat arrival of a known `session_id`, `POST /api/v1/sessions` shall return 200 with `status_after_processing` = `duplicate`. | Must | BR-03 | 05 API | T |
| FR-009 | `POST /api/v1/ingest` shall return 202 with `ingest_batch_id`, `accepted`, `rejected` and `duplicates` counts. | Must | BR-01 | 05 API | T |
| FR-010 | Each batch or CSV upload shall create one `ingest_batches` row recording source (`api_single`, `api_batch`, `csv_upload`, `seed`), filename, record count, accepted count, rejected count, uploader and receive time. | Must | BR-02, BR-16 | 10 ING, 06 DB | T |
| FR-011 | Within a batch, valid records shall be accepted and invalid records rejected individually, and arrival order shall follow the order of records in the request or file. | Must | BR-01, BR-03 | 10 ING | T |
| FR-012 | The system shall map incoming feature column names to internal feature keys through a configurable feature-name mapping, so that renamed extractor outputs need no code change. | Must | BR-01, OQ-03, RSK-02 | 10 ING, 07 ANL | T |
| FR-013 | The system shall reject a record that contains a field not defined in schema v0.1 (after feature-name mapping), so that no audio or other unexpected content can be stored. | Must | BR-01, BR-16 | 10 ING | T |
| FR-014 | The ingest endpoints shall return 429 when a key exceeds `RATE_LIMIT_INGEST` (600 per minute). | Must | BR-16 | 12 SEC | T |
| FR-015 | The system shall provide no endpoint that accepts, returns or replays audio. | Must | BR-01, BR-16, SRC-14 | 05 API, 19 OAS | I |

### 4.3 Validation and duplicate detection (BR-01, BR-03)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-020 | The system shall reject a record whose `schema_version` is not in the configured list of supported versions (initially `"0.1"`). | Must | BR-01, SRC-13 §6 | 10 ING | T |
| FR-021 | The system shall reject a record that lacks any required field of schema v0.1 (all 11 metadata fields and 19 features; `phrase_id` required while OQ-04 is open). | Must | BR-01, SRC-05 | 10 ING | T |
| FR-022 | The system shall reject a record whose `timestamp_utc` is not in the format `YYYY-MM-DD HH:MM:SS`. | Must | BR-01, SRC-03 Data_dictionary | 10 ING | T |
| FR-023 | The system shall reject a record whose numeric fields are not finite numbers, or whose `number_of_pauses` is not an integer ≥ 0. | Must | BR-01, SRC-03 Data_dictionary | 10 ING | T |
| FR-024 | The system shall reject a record whose `audio_quality_flag` is not `ok` or `poor`. | Must | BR-01, BR-04 | 10 ING | T |
| FR-025 | The system shall reject a record whose `resident_id` is not an enrolled resident code or whose `device_id` is not a registered device. | Must | BR-01, SRC-02 stage 1 ("check schema and device") | 10 ING | T |
| FR-026 | The system shall reject a record for a resident with status `withdrawn` with detail "resident withdrawn". | Must | BR-16, OQ-11 | 10 ING | T |
| FR-027 | A rejected record shall receive HTTP 422 with an `application/problem+json` body (`type` = `urn:echowell:error:<CODE>`) whose `errors[]` items `{field, code, message}` list every failed field and rule. | Must | BR-01, R19 | 05 API, 10 ING | T |
| FR-028 | A rejected record shall be logged in `ingest_rejections` with the raw body and errors, and shall not be written to `raw_sessions`. | Must | BR-01, BR-02 | 10 ING | T |
| FR-029 | The pipeline shall process arrivals in `arrival_seq` order and mark every arrival after the first with the same `session_id` as `duplicate` with reason "session_id already received". | Must | BR-03, SRC-03 R04 | 07 ANL | T |
| FR-030 | Duplicate arrivals shall be excluded from epochs, quality gate, speaker screen, baseline, scoring, CUSUM and the day ledger. | Must | BR-03, SRC-03 R04 | 07 ANL | T |
| FR-031 | The results for a resident with duplicates shall be identical to the results computed from the same input without the duplicate copies. | Must | BR-03, SRC-03 R04 | 07 ANL, 14 TDV | T |
| FR-032 | A CSV upload whose header does not equal the schema v0.1 header (e.g. the legacy SRC-06 file with `entry_id`, `health_wifi`, `speech_feature_1..3`) shall be rejected as a whole with 422 "schema mismatch", and nothing shall be stored in `raw_sessions`. | Must | BR-01, BR-02, SRC-06, R12 | 10 ING | T |

### 4.4 Quality gate (BR-04)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-040 | The pipeline shall set aside a non-duplicate record whose `audio_quality_flag` is not `ok`, with reason "quality flag poor". | Must | BR-04, SRC-03 Parameters | 07 ANL | T |
| FR-041 | The pipeline shall set aside a non-duplicate record whose `mic_noise_level_dbfs` is greater than `noise_limit_dbfs` (−40.0), with reason "noise above limit". | Must | BR-04, SRC-03 Parameters | 07 ANL | T |
| FR-042 | The pipeline shall set aside a non-duplicate record whose `speech_duration_s` is less than `min_speech_s` (1.0), with reason "speech too short". | Must | BR-04, SRC-03 Parameters | 07 ANL | T |
| FR-043 | When several quality rules fail, the pipeline shall record all failing reasons joined by "; " in the fixed order quality flag, noise, speech duration. | Must | BR-04, SRC-03 R03 day 18 | 07 ANL | T |
| FR-044 | Set-aside sessions shall not be screened, scored, included in a baseline, or used to update the CUSUM tally. | Must | BR-04, SRC-02 ("Logged, never used for baseline") | 07 ANL, 09 CUS | T |

### 4.5 Epochs (BR-08)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-050 | The pipeline shall assign every non-duplicate record (including set-aside records) of a resident, in `timestamp_utc` order, to an epoch, starting a new epoch whenever `(device_id, device_firmware_version, extraction_software_version)` differs from the previous record. | Must | BR-08, SRC-03 Parameters "epoch keys" | 07 ANL | T |
| FR-051 | Epochs shall be numbered 1, 2, … per resident and persisted with device, firmware, software, start and end times. | Must | BR-08 | 06 DB, 07 ANL | T |
| FR-052 | The baseline count shall restart from zero in each new epoch. | Must | BR-08, BR-09, SRC-03 R07 | 08 BSC | T |
| FR-053 | When a new epoch starts, the pipeline shall close any open alert of the previous epoch with reason "epoch ended" and start the CUSUM tally of the new epoch from 0 at its first scored session. | Must | BR-08, BR-11, ASM-06 | 09 CUS | T |

### 4.6 Speaker screen (BR-05)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-060 | The pipeline shall screen each record that passed the quality gate against a reference made of the first up to `baseline_n` prior usable sessions of the same resident-epoch, using raw (unadjusted) values. | Must | BR-05, SRC-03 Parameters | 07 ANL, 08 BSC | T |
| FR-061 | The speaker screen shall run only when at least `screen_min_n` (5) prior usable sessions exist in the epoch; otherwise the record is `usable`. | Must | BR-05, SRC-03 Parameters | 07 ANL | T |
| FR-062 | The pipeline shall quarantine a record when the robust z of `mean_f0_hz` has absolute value ≥ 4.0 and at least 2 of the 7 composite features have robust z with absolute value ≥ 3.0. | Must | BR-05, SRC-03 Parameters, SRC-04 | 08 BSC | T |
| FR-063 | A quarantined record shall carry the reason "possible other speaker (F0 z=<value to 2 dp>; composite features with \|z\|>=3: <n>)". | Must | BR-05, SRC-03 R05 | 07 ANL | T |
| FR-064 | The speaker screen shall apply both before and after the baseline freezes. | Must | BR-05, SRC-03 R05 days 8 and 22 | 07 ANL | T |
| FR-065 | Quarantined sessions shall not be scored, included in a baseline, added to the screen reference, or used to update the CUSUM tally. | Must | BR-05, SRC-03 Parameters | 07 ANL, 09 CUS | T |

### 4.7 Morning adjustment (BR-07)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-070 | The pipeline shall convert `timestamp_utc` to local time in the facility timezone (FACILITY_TZ, default America/Chicago) and derive `local_date` and `local_time` for every non-duplicate record. | Must | BR-07, ASM-01, SRC-03 README note 4 | 07 ANL | T |
| FR-071 | The pipeline shall classify a session as morning when its local hour is less than `morning_cutoff_hour` (12). | Must | BR-07, SRC-03 Parameters | 08 BSC | T |
| FR-072 | For morning sessions the pipeline shall compute each adjusted feature value as raw value minus the configured morning offset; for other sessions adjusted equals raw. | Must | BR-07, SRC-03 Exp_morning_offset | 08 BSC | T |
| FR-073 | Morning offsets shall be read from configuration and shall not be estimated from data in the MVP. | Must | BR-07, SRC-03 README note 3, OQ-09 | 08 BSC | I, T |
| FR-074 | Baselines and scores shall use adjusted values; the speaker screen shall use raw values. | Must | BR-05, BR-07, SRC-03 Parameters | 08 BSC | T |

### 4.8 Personal baseline (BR-09)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-080 | The pipeline shall form a baseline per resident-epoch from the first `baseline_n` usable sessions in timestamp order (30 in production, 16 in `test_v0_1`). | Must | BR-09, SRC-02 stage 4, SRC-03, D-OWNER-2 | 08 BSC | T |
| FR-081 | For each of the 19 features the baseline shall store median, MAD, robust spread = max(MAD × 1.4826, floor) and `floor_applied`, with floor 0.5 for `number_of_pauses` and 0 for other features. | Must | BR-09, SRC-03 Exp_baselines | 08 BSC | T |
| FR-082 | The baseline shall store a composite entry (median, MAD, spread with floor 0.1) computed from the composite_raw values of the baseline sessions. | Must | BR-09, BR-10, SRC-03 Parameters | 08 BSC | T |
| FR-083 | Once formed, a baseline shall be frozen and shall never be updated by later sessions. | Must | BR-09, SRC-03 R10, SRC-12 | 08 BSC | T |
| FR-084 | A late record that would change the membership of a frozen baseline shall leave the baseline unchanged and shall be reported as a `late_arrival` warning on the pipeline run. | Must | BR-09, ASM-07, OQ-10 | 08 BSC, 07 ANL | T |
| FR-085 | A resident-epoch with fewer than `baseline_n` usable sessions shall be reported as "baseline forming" with progress n of N, shall produce no scores, and shall not be treated as an error. | Must | BR-09, SRC-03 R08 | 08 BSC | T |
| FR-086 | Each baseline shall record `n_sessions`, `first_session_id`, `frozen_after_session_id` and `frozen_at`. | Must | BR-09, SRC-03 Exp_resident_outcomes | 06 DB | T |

### 4.9 Scoring (BR-10)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-090 | The pipeline shall score every usable session that occurs after the baseline of its epoch froze. | Must | BR-10, SRC-02 stage 5 | 08 BSC | T |
| FR-091 | For each of the 7 composite features the pipeline shall compute z = (adjusted value − baseline median) / baseline robust spread. | Must | BR-10, SRC-03 Parameters | 08 BSC | T |
| FR-092 | The pipeline shall compute composite_raw as the mean over the 7 composite features of sign × z, using the signs of TRD 08 (positive = depression-associated direction). | Must | BR-10, SRC-03 Data_dictionary | 08 BSC | T |
| FR-093 | The pipeline shall compute composite_z = (composite_raw − composite baseline median) / composite baseline spread. | Must | BR-10, SRC-03 Parameters | 08 BSC | T |
| FR-094 | The pipeline shall persist, per scored session, the 7 z values, composite_raw, composite_z, cusum_tally, alarm_state, local_date and is_morning. | Must | BR-10, SRC-03 Exp_scores | 06 DB | T |
| FR-095 | The 12 stored-not-scored features shall be stored for every non-duplicate record and shall not contribute to composite, CUSUM or alarm. | Must | BR-10, SRC-12, SRC-13 §4 | 08 BSC | T |

### 4.10 CUSUM and alerts (BR-11)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-100 | The pipeline shall compute the running change tally per resident-epoch as S = max(0, S_prev + composite_z − k) with k = 0.5 and S_prev = 0 before the first scored session. | Must | BR-11, SRC-03 Parameters | 09 CUS | T |
| FR-101 | Set-aside, quarantined, duplicate and missing days shall leave the tally unchanged. | Must | BR-11, SRC-21 (Voice trends intro line) | 09 CUS | T |
| FR-102 | The pipeline shall mark the first scored session whose tally is ≥ h (5.0) with alarm_state `rings` and every later scored session in the same epoch with alarm_state `on`. | Must | BR-11, SRC-03 Parameters "alarm" | 09 CUS | T |
| FR-103 | Scored sessions before the first crossing shall have alarm_state `off`. | Must | BR-11, SRC-03 Exp_scores | 09 CUS | T |
| FR-104 | The pipeline shall create exactly one `alerts` row per first crossing, recording resident, epoch, session_id, triggered_at, local_date and cusum value, with status `open`. | Must | BR-11, SRC-02 ("Flag for clinician review") | 09 CUS | T |
| FR-105 | The pipeline shall keep one `cusum_state` row per resident-epoch with the current tally, last scored session and alarm flag. | Must | BR-11 | 09 CUS, 06 DB | T |
| FR-106 | Saving an alarm review (FR-270) shall set the alert's status to `acknowledged` with `acknowledged_by` and `acknowledged_at`; no separate acknowledge endpoint shall exist (`POST /alerts/{id}/acknowledge` is replaced by `POST /alerts/{id}/reviews`). | Must | BR-11, BR-13, SRC-21, R5 | 09 CUS, 05 API | T |
| FR-107 | Saving a review or snoozing an alarm shall not reset the tally and shall not turn the alarm off. | Must | BR-11, OQ-05, SRC-21 | 09 CUS | T |
| FR-108 | The system shall list alerts filtered by status and resident at `GET /api/v1/alerts`. | Must | BR-11, BR-13 | 05 API | T |
| FR-109 | The system shall deliver alerts only inside the dashboard and shall send no SMS, e-mail or push notification. | Must | BR-11, OQ-06 | 09 CUS | I |
| FR-110 | An alert shall move to status `closed` only through the pipeline, in exactly two ways: epoch end (reason "epoch ended", ASM-06) or a rebuild that no longer produces its first crossing (reason "superseded by rebuild", TRD 09 CUS-015); there is no manual (admin) closure in v0.1 (`closed_reason = 'admin'` is reserved, TRD 09 CUS-019). | Must | BR-11, ASM-06, R4 | 09 CUS | T |

### 4.11 Day ledger and missing days (BR-06)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-120 | The pipeline shall produce one `day_ledger` row per resident per local calendar day from the resident's enrolment date to the as-of local date, or to `withdrawn_on` if earlier; both end dates are inclusive (the `withdrawn_on` day itself has a ledger row). | Must | BR-06, SRC-03 Annotated_sessions | 07 ANL | T |
| FR-121 | A day with at least one non-duplicate record shall have ledger status `checked_in`. | Must | BR-06 | 07 ANL | T |
| FR-122 | A day with no non-duplicate record shall have status `missing_device_gap` with reason "all residents on shared device <id> have no record" when the resident's device that day is assigned to ≥ 2 residents and none of them has a record that day. | Must | BR-06, SRC-03 Parameters, R02/R03 day 12 | 07 ANL | T |
| FR-123 | Any other day with no non-duplicate record shall have status `missing_resident` with reason "no record received". | Must | BR-06, SRC-03 R02, R08 | 07 ANL | T |
| FR-124 | Missing days shall never be backfilled, carried forward or imputed, and shall never create a session, score or tally update. | Must | BR-06, SRC-12 | 07 ANL | T |
| FR-125 | The nightly run shall extend the ledger to the new as-of date even if no record arrived. | Must | BR-06 | 07 ANL, 01 ARC | T |

### 4.12 Resident list (BR-12)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-130 | The Resident list (`/residents`) shall list every active resident of the longitudinal cohort; withdrawn residents shall be hidden unless `include_withdrawn=true`. | Must | BR-12, SRC-21, SRC-12 | 04 FE, 11 UX | T |
| FR-131 | Each resident shall have exactly one display status, first match wins (TRD 24 D-109): "▲ Changed" when the API `status` is `alarm_on` (an alert with status `open` or `acknowledged` exists in the current epoch); "! Needs attention" when the API `needs_attention` is true (an open `baseline_stalled` or `high_set_aside` data alert, FR-302); "○ Learning" when `status` is `baseline_forming` (the current epoch has fewer than `baseline_n` usable sessions); otherwise "● Usual" (`no_alarm`). Each pill pairs colour, glyph, label and border (TRD 11 §4.3.4); the pipeline `status` values are unchanged. | Must | BR-12, SRC-21, SRC-12, D-109 | 11 UX, 23 DME, 05 API | T |
| FR-132 | A Usual resident whose current epoch is greater than 1 shall show the "What's happening" text "Usual. Baseline restarted <Mon D> after a new device." (cause firmware: "… after a firmware change."; software: "… after a software change.") using the current epoch start date and the API `restart_cause`. | Must | BR-08, BR-12, SRC-21 (R07) | 11 UX, 05 API | T |
| FR-133 | The Resident list shall show the rows in the API default order (`sort=alarm`): Changed (alarm date oldest first, then natural resident code), then Needs attention, then Learning, then Usual (each by natural resident code) (TRD 24 D-109, amending D-17), and filter buttons "All (<n>)", "Changed (<n>)", "Needs attention (<n>)", "Learning (<n>)" (only when ≥ 1 resident is Learning), "Usual (<n>)" with counts from the API `summary`, the filter kept in `?show=`. The API keeps the `resident_id` and `last_checkin` sorts, which the UI does not offer. | Must | BR-12, SRC-21, SRC-12, D-109 | 11 UX, 05 API | T |
| FR-134 | Each row shall show the columns "Status" (pill of FR-131), "Resident" (study ID linking to the chart), "What's happening" (one sentence from the TRD 11 §4.3.6 templates, e.g. "Changed from their usual since Oct 21. Not reviewed yet.", "Missing many check-ins. Baseline stuck at 13 of 16.") and "Last check-in" (latest non-duplicate record of any status, local, e.g. "Oct 30, 2:28 PM CT"). The device moves to the chart banner, with " (shared with <R>)" when the device is currently assigned to ≥ 2 residents or " (replaced <old>)" when the resident's previous device assignment ended the day before the current one started (the single rule of TRD 23 §4.4.1). | Must | BR-12, SRC-21, R10 | 04 FE, 11 UX | T |
| FR-135 | The last-30-day counts used, set aside, quarantined and missed (missed = missing_resident + missing_device_gap days; duplicates never counted) shall be shown in the Resident chart: the banner "Usable check-ins, last 30 days" ("<used> of <days in window>") and the Check-in log counts "Used", "Set aside (noise, poor quality or too short)", "Held back (possible other voice)", "Missed" (TRD 24 D-110, D-113). | Must | BR-06, BR-12, SRC-21, SRC-12 | 11 UX | T |
| FR-136 | (Retired by TRD 24 D-110: wireframe v0.2 has no summary tiles; the status counts are shown on the filter buttons, FR-133, from the API `summary` `changed`, `needs_attention`, `learning`, `usual` (TRD 24 D-114), and the system counts on the Study team page, FR-313) | — | D-110 | — | — |
| FR-137 | For the SRC-05 data at as-of 2026-10-30 15:00 America/Chicago with profile `test_v0_1`, the filter buttons shall read "All (10)", "Changed (2)", "Needs attention (2)", "Usual (6)" (no Learning button), the rows shall be in the order R09, R10, R03, R08, R01, R02, R04, R05, R06, R07 with the "What's happening" texts of TRD 11 §4.13.1, and the chart counts shall equal SRC-03 Exp_status_counts. | Must | BR-12, BR-15, SRC-21 | 14 TDV, 11 UX | T |
| FR-138 | Every page shall show, under the app bar, the data bar "Test data only (<DATA_SOURCE_LABEL>, <period>). No real residents. No audio is stored or played anywhere in EchoWell." in the `test_v0_1` profile and "No audio is stored or played anywhere in EchoWell." otherwise (TRD 11 UX-400; replaces the v0.1 header subline, TRD 24 D-110). | Must | BR-01, BR-12, SRC-21 | 11 UX | T |
| FR-139 | (Retired by TRD 24 D-110: the page footers are replaced by the data bar, FR-138; the caption "Duplicate records are removed quietly and not shown." moves to the check-in log, FR-182, TRD 11 UX-148) | — | D-110 | — | — |
| FR-140 | Selecting a row or its study-ID link ("Open chart for <R>") shall navigate to `/residents/<resident_code>` (the chart Summary). | Must | BR-12, BR-13, SRC-21 | 04 FE | T |

### 4.13 Devices (Study team page and chart Device section) (BR-12, BR-06)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-150 | The Study team page shall include a "Devices" section (anchor `/study#devices`; moved from the v0.1 overview, TRD 24 D-110) listing every active device with its currently assigned residents, and each Resident chart shall have a "Device" section for the resident's current device (TRD 11 §4.4, §4.5.8). | Must | BR-12, SRC-21, SRC-12 | 11 UX | T |
| FR-151 | A device assigned to ≥ 2 residents shall be shown as "<device> (shared by <residents>)" (e.g. "D02 (shared by R02 and R03)") on the Study team page and as "Shared with <other residents>" in the chart's Device section. | Must | BR-12, SRC-21 | 11 UX | T |
| FR-152 | For each device the UI shall show the last upload time (local), the firmware version and the upload state "● Online" / "○ No upload today" from the API `uploaded_on_as_of_date` (TRD 24 D-114); a device without upload does not change a resident's status (OQ-31 answered, TRD 24 D-115). | Must | BR-12, SRC-21, OQ-31 | 11 UX, 05 API | T |
| FR-153 | For each shared device the UI shall list its device-gap days in the last 30 days (Study team: "Silent all day Oct 12."; chart Device history: "Silent all day. Affected R02 and R03."). | Must | BR-06, BR-12, SRC-21, SRC-12 | 11 UX | T |
| FR-154 | For each device the API shall report its silent days in the last 30 days (`silent_days_last_30`). | Should | BR-06, BR-12, SRC-12 ("days with no device activity") | 05 API, 11 UX | T |
| FR-155 | A device that replaced another for a resident shall be shown as "<device> (<resident>): in use since <Mon D>, replacing <old>." (e.g. "D07B (R07): in use since Oct 13, replacing D07.") and in the chart's Device history as "Replaced <old> with <device>. Baseline restarted." | Must | BR-08, BR-12, SRC-21 | 11 UX | T |
| FR-156 | Devices with no device-gap day, no replacement, not shared and an upload on the as-of date shall be grouped into one row per firmware version ("D01, D04 to D06, D08 to D10: all uploaded Oct 30. Firmware fw-1.0.0."). | Must | BR-12, SRC-21 | 11 UX | T |

### 4.14 Resident chart (BR-13)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-160 | The Resident chart (`/residents/[residentCode]`) shall start with the link "← Resident list" to `/residents`, keeping the list's `?show=` filter. | Must | BR-13, SRC-21 | 11 UX | T |
| FR-161 | The chart banner shall show the resident code, "Device", "Last check-in", "Usable check-ins, last 30 days", "Baseline" ("Complete" or "<n> of <N>") and the large status pill of FR-131, followed by a section navigation "Summary", "Review and notes", "Voice trends", "Baseline", "Check-in log", "Device" with one URL per section (TRD 24 D-110). | Must | BR-13, SRC-21 | 11 UX | T |
| FR-162 | When the current epoch's baseline is frozen, the Baseline section shall read "First N usable check-ins, <first date>–<frozen-after date>, then frozen. Compared with it since <Mon D>." (prefixed with the restart sentence when the epoch is greater than 1). | Must | BR-09, BR-13, SRC-21, SRC-12 | 11 UX | T |
| FR-163 | When the current epoch's baseline is forming, the Baseline section shall read "Still forming: n of N usable check-ins so far." with a progress meter "n of N usable check-ins". | Must | BR-09, BR-13, SRC-21, SRC-12 | 11 UX | T |
| FR-164 | The chart Summary shall start with a "Right now" panel whose text comes from PI-reviewed configuration strings per display status, ending with "This compares <R> only with <R>. It is a prompt to check in, not a diagnosis." and the marker "[Final clinical wording: confirm with PI]" until OQ-12 is closed. | Must | BR-13, BR-18, SRC-21, OQ-12 | 11 UX | I |
| FR-165 | The Voice trends section shall show a "Change score" bar chart (UI name of the CUSUM tally, TRD 24 D-113) of the current epoch with one bar per scored session (height = cusum_tally), coloured by `alarm_state` (`--c-aside` while `off`, `--red` when `rings` or `on`), preceded by a grey baseline slot labelled "Baseline <Mon D>–<Mon D>", with a dashed line at cusum_h labelled "Alarm line: <h>" ("Alarm line: 5") and x-axis labels including the first scored date, the alarm date and the last date. | Must | BR-11, BR-13, SRC-21, SRC-12, R1 | 04 FE, 11 UX | T |
| FR-166 | The change-score chart shall make alarm persistence visible by a non-colour cue (▲ marker at the first crossing and the "Oct 21 · alarm"-style label) in addition to the colour of bars with alarm_state `rings` or `on`. | Must | BR-11, BR-13, SRC-12 ("alarm persistence"), R1 | 11 UX | T |
| FR-167 | The change-score panel shall carry the line "Goes up when check-ins keep leaning away from <R>’s usual. The alarm turns on at <h>. Missed, set-aside and held-back check-ins leave it unchanged." | Must | BR-11, SRC-21 | 11 UX | I |
| FR-168 | The change-score chart shall have an equivalent text table (disclosure "Show change score as a table", columns "Date", "Change score", "Alarm", TRD 11 UX-090) available to assistive technology and by a visible toggle. | Must | BR-13, BR-16 (accessibility, TRD 03) | 11 UX | T |
| FR-169 | The Voice trends section shall show "The 7 voice measurements behind the score" with one card per composite feature, showing the plain-language label of TRD 08 (e.g. "Quieter (loudness)", "More pauses (number of pauses)") and a sparkline of the signed deviations (sign × z) of the current epoch's scored sessions (TRD 11 UX-102). | Must | BR-10, BR-13, SRC-21, SRC-12 | 11 UX | T |
| FR-170 | The section shall show an eighth card "12 other measurements (pitch, jitter, MFCCs and others)" with "Stored, not scored", without values in the scoring summary. | Must | BR-10, BR-13, SRC-21, SRC-12 | 11 UX | I |
| FR-171 | The measurements section shall carry the caption "Measurement names are placeholders until Team 1 confirms the openSMILE output names. Morning check-ins are adjusted before comparing." | Must | BR-07, OQ-03, SRC-21 | 11 UX | I |
| FR-172 | A user shall be able to view an earlier epoch's tally and baseline for a resident with more than one epoch. | Should | BR-08, BR-13, OQ-28 | 04 FE, 05 API | T |
| FR-173 | Requesting an unknown resident code shall show "Resident <code> was not found." and the API shall return 404. | Must | BR-13 | 05 API, 04 FE | T |

### 4.15 Check-in log (BR-13, BR-06)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-180 | The Resident chart shall have a "Check-in log" section showing the last-30-day counts and an "Events" list newest first, each line "<Mon D>" plus the event text of TRD 11 §4.5.6 (e.g. "Oct 21" "Alarm on. Change score crossed 5."). | Must | BR-13, SRC-21 | 11 UX | T |
| FR-181 | The log shall include event types: alarm on, watching started ("Comparing with baseline started."), baseline complete ("Baseline complete (n of N)."), set aside (with reasons), quarantined ("Check-in held back: possible other voice."), missed (missing_resident), device silent (missing_device_gap), baseline restarted (new device/firmware/software) and check-ins started (`checkins_started`, "Check-ins started." or "Check-ins started on <D>.", derived on read; TRD 24 D-113). | Must | BR-04, BR-05, BR-06, BR-08, BR-11, BR-13, SRC-21, SRC-12 | 05 API, 11 UX | T |
| FR-182 | The log shall never contain duplicate records, and shall carry the caption "Duplicate records are removed quietly and not shown." | Must | BR-03, SRC-21 | 05 API, 11 UX | T |
| FR-183 | The check-in log API shall support filtering by `from` and `to` local dates. | Should | BR-13 | 05 API | T |
| FR-184 | A newly ingested usable record shall show on the dashboard after the ingest response returns, without manual pipeline action: (a) the Resident list "Last check-in" of that resident shows the record's local time and its 30-day "used" count (chart banner and Check-in log) rises by 1; and (b) when the resident's baseline is frozen, the Resident chart's change-score chart gains one bar for that session (usable check-ins are not check-in log events, TRD 11 UX-144; TRD 24 D-67); a set-aside or quarantined record appears in the check-in log as its event type. | Must | BR-01, BR-13, SRC-15 demo step 5 | 01 ARC, 05 API | T, D |

### 4.16 Staff notes (BR-13)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-190 | A user with role `clinician` or `admin` shall be able to add a staff note to a resident with a type (`observation`, `action_taken`, `follow_up`) and a body of 1 to 2000 characters, in the chart's "Review and notes" section ("Staff notes"). | Must | BR-13, SRC-21, SRC-12 | 05 API, 11 UX | T |
| FR-191 | The alarm review form of FR-266–FR-270 shall exist only in the chart's "Review and notes" section and shall be shown only when the resident is Changed (single review model; the v0.1 "Mark as reviewed" button and dialog are retired, TRD 24 D-110; TRD 11 UX-310); staff notes themselves shall not change alert status. | Must | BR-13, SRC-21, R5, D-110 | 11 UX, 09 CUS | T |
| FR-192 | Staff notes shall be append-only; a correction submitted through the API shall create a new note row referencing the superseded note via `supersedes_id` (the MVP UI offers no edit control, TRD 11 UX-129). | Must | BR-13, BR-16 | 06 DB | T |
| FR-193 | The "Staff notes" panel shall list the resident's notes newest first with type, author display name and local timestamp, showing only the latest version of edited notes. | Must | BR-13, SRC-21 | 11 UX | T |
| FR-194 | Users with role `researcher` shall see notes and reviews read-only and shall not see the note form, the review form, "Save review" or "Remind me in 24 hours". | Must | BR-13, BR-16, OQ-26 | 12 SEC, 11 UX | T |
| FR-195 | (Retired by TRD 24 D-110: the open-questions note is part of the review panel, FR-277, TRD 11 UX-321) | — | D-110 | — | — |

### 4.17 New admissions — future / experimental (BR-14)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-200 | The New admissions page (`/admissions`) shall show at the top the note "Future / experimental. Not in pipeline test v0.1: the test data has no admission group or facility range yet. Open question for Shaba and the PI." (until OQ-08 is closed). | Must | BR-14, SRC-21, SRC-12 | 11 UX | T |
| FR-201 | The page shall list residents of cohort `new_admission` whose own baseline has not yet formed, with the columns "Status", "Resident", "Admitted", "Compared with facility range" and "Own baseline" ("n of N"). | Must | BR-14, SRC-21 | 05 API, 11 UX | T |
| FR-202 | The comparison text shall be one of "Outside facility range", "Within facility range", "Not enough check-ins yet", or "Facility range not available yet" when no facility reference range exists (OQ-08), with the status pill of TRD 11 UX-185; the API values are `outside_range`, `within_range`, `not_enough_checkins` and `range_not_available` (TRD 19 `ComparisonStatus`). | Must | BR-14, SRC-21, OQ-08 | 11 UX | T |
| FR-203 | Selecting a new admission ("Show comparison") shall show a per-feature comparison: the resident's value as a dot against the facility range as a grey band, captioned "Grey band = usual range across current residents". | Must | BR-14, SRC-21 | 04 FE, 11 UX | T |
| FR-204 | Facility reference ranges shall be read from `facility_reference_ranges` with their method, number of residents and computation time; the method of computing them is not defined in the MVP (OQ-08). | Must | BR-14, OQ-08, RSK-13 | 06 DB, 07 ANL | I |
| FR-205 | A new-admission resident shall be compared only with their own baseline, and shall appear on the Resident list instead of the New admissions list, once their own baseline has formed. | Must | BR-09, BR-14, SRC-21, SRC-12 | 07 ANL, 11 UX | T |
| FR-206 | New-admission comparisons shall never create alerts or affect the CUSUM of any resident. | Must | BR-11, BR-14, RSK-13 | 09 CUS | T |
| FR-207 | (Retired by TRD 24 D-110: the page footers are replaced by the data bar, FR-138) | — | D-110 | — | — |

### 4.18 Authentication and roles (BR-16)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-210 | A user shall log in at `/login` with e-mail and password; on success the backend shall return a JWT access token valid for 60 minutes. | Must | BR-16 | 12 SEC, 05 API | T |
| FR-211 | All dashboard pages except `/login` shall require a valid token and shall redirect to `/login` when the token is missing or expired. | Must | BR-16 | 04 FE, 12 SEC | T |
| FR-212 | All API endpoints except `GET /api/v1/health` and `POST /api/v1/auth/login` shall return 401 without valid credentials. | Must | BR-16 | 12 SEC | T |
| FR-213 | The system shall enforce three roles with the permissions of the matrix in section 4.26. | Must | BR-16 | 12 SEC | T |
| FR-214 | An inactive user shall not be able to log in. | Must | BR-16 | 12 SEC | T |
| FR-215 | The login endpoint shall return 429 after 5 attempts per minute from one IP address. | Must | BR-16 | 12 SEC | T |
| FR-216 | `GET /api/v1/auth/me` shall return the current user's e-mail, display name and role. | Must | BR-16 | 05 API | T |
| FR-217 | A user shall be able to log out: the frontend shall call `POST /api/v1/auth/logout` (best effort; the token simply expires, no server-side revocation list) and discard the token, and the backend shall record a logout audit event. | Must | BR-16, R4 | 12 SEC | T |
| FR-218 | The navigation shall show "Admin" only to users with role `admin` and "Study team" only to users with role `researcher` or `admin`. | Must | BR-16, SRC-21 | 04 FE | T |

### 4.19 Administration (BR-15, BR-16, BR-02)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-220 | An admin shall be able to create a user with e-mail, display name, role and initial password at `/admin`. | Must | BR-16 | 05 API, 12 SEC | T |
| FR-221 | An admin shall be able to change a user's role and active flag; users shall not be deleted. | Must | BR-16 | 05 API | T |
| FR-222 | An admin shall be able to upload a CSV with the SRC-05 header from `/admin` and see the batch result: accepted, rejected (with per-row errors) and duplicate counts. | Must | BR-01, BR-15, SRC-05 | 04 FE, 10 ING | T |
| FR-223 | An admin (JWT) or a caller with an API key of scope `pipeline:run` shall be able to trigger a pipeline run with scope (`all` or a list of resident codes), profile and optional `as_of`, receiving a `pipeline_run_id`. | Must | BR-02, BR-15, R18, R21 | 05 API | T |
| FR-224 | Admins and researchers shall be able to view a pipeline run's trigger, scope, profile, status, start/finish times, counts and warnings. | Must | BR-15 | 05 API | T |
| FR-225 | `GET /api/v1/pipeline/runs` (admin, researcher; paginated, newest first) shall list pipeline runs, and the Admin page shall show the most recent 50. | Must | BR-15, R4 | 05 API, 04 FE | T |
| FR-226 | Device API keys shall be created and revoked by an admin through `python -m backend.cli` commands; the plaintext key shall be shown once and only its SHA-256 hash stored; no HTTP endpoint shall exist for API keys. | Must | BR-01, BR-16, R4 | 12 SEC | T |
| FR-227 | Residents, devices, device assignments and the facility shall be managed through version-controlled seed files and `python -m backend.cli` commands, with no HTTP endpoints; no PII field shall exist for them. | Must | BR-12, BR-16, ASM-03, R4 | 06 DB, 15 DEP | T |
| FR-228 | Setting a resident's status to `withdrawn` with `withdrawn_on` shall stop ingestion for that resident (FR-026) and hide the resident from default lists. | Must | BR-16, OQ-11 | 06 DB, 10 ING | T |
| FR-229 | Pipeline parameters shall be stored in `config_parameters` per profile and shall be changed only by the operator command `python -m backend.cli set-config --profile <p> --key <k> --value '<json>' --reason "<text>"` (TRD 15 §4.8), which validates the value against the key's schema and writes an `audit_logs` row `config.changed` with old value, new value and reason; for algorithm keys it prints that `python -m backend.cli rebuild` is required (TRD 24 D-69). | Must | BR-09, BR-11, BR-16 | 07 ANL, 12 SEC | T |
| FR-230 | The `test_v0_1` profile shall not be selectable in production (`APP_ENV=production`). | Must | BR-09, D-OWNER-2 | 21 ENV | T |

### 4.20 Researcher analytics and export (BR-15)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-240 | `GET /api/v1/analytics` shall return per-resident status counts in the shape of SRC-03 Exp_status_counts and per-resident outcomes in the shape of Exp_resident_outcomes, plus the latest succeeded pipeline run information (TRD 05 API-069). | Must | BR-15, SRC-03 | 05 API | T |
| FR-241 | `GET /api/v1/analytics/baselines` shall return baselines in the shape of SRC-03 Exp_baselines (resident, epoch, feature, n, median, MAD, spread, floor_applied). | Must | BR-15, SRC-03 | 05 API | T |
| FR-242 | `GET /api/v1/scores` shall return scored sessions in the shape of SRC-03 Exp_scores, filterable by resident, epoch and date range. | Must | BR-15, SRC-03 | 05 API | T |
| FR-243 | The analytics endpoints shall be available only to roles `researcher` and `admin`. | Must | BR-16 | 12 SEC | T |
| FR-244 | `GET /api/v1/analytics/baselines` and `GET /api/v1/scores` shall return CSV when requested with `Accept: text/csv` by a researcher or admin, using the TRD 19 DTO field names as column names (TRD 05 API-129). | Must | BR-15, SRC-14 B.2 (offline mixed-effects analysis), R4 | 05 API | T |
| FR-245 | Exports shall contain study IDs only and no free-text staff notes. | Must | BR-16 | 05 API, 12 SEC | T |

### 4.21 Audit and health (BR-16, BR-17)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-250 | The system shall write an `audit_logs` entry for login, logout, failed login, ingest batch, note created, alert acknowledged (review saved), alarm snoozed, pipeline run, config change (`config.changed`, written by the `set-config` CLI) and user change. | Must | BR-16 | 12 SEC, 17 LOG | T |
| FR-251 | Each audit entry shall record time, actor type and id, action, entity type and id, details, IP and request ID, and shall contain no feature values or passwords. | Must | BR-16 | 12 SEC | T |
| FR-252 | Audit entries shall be append-only for the application database role. | Must | BR-16 | 20 PGS | T |
| FR-253 | `GET /api/v1/health` shall return `{status, database, version, time}` without authentication, with HTTP 503 and status "degraded" when the database check fails. | Must | BR-17, R19 | 05 API | T |
| FR-254 | Every response shall carry an `X-Request-ID` header. | Must | BR-16, BR-17 | 17 LOG | T |

### 4.22 Alarm review (Resident chart "Review and notes") (BR-11, BR-13) — SRC-21

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-260 | (Retired by TRD 24 D-110: the Alert review page (`/alerts`) is retired; the review form, reminder and previous reviews are in the Resident chart's "Review and notes" section, FR-264) | — | D-110 | — | — |
| FR-261 | (Retired by TRD 24 D-110: there is no alarm queue; Changed residents sort first on the Resident list, FR-133, and the nav badge counts unreviewed alarms, FR-330) | — | D-110 | — | — |
| FR-262 | For a Changed resident the chart Summary shall show the facts "<Mon D>" "Alarm started", "<n> days" "Open" (n = as-of local date − alarm local date) and "Not reviewed" (status `open`) or "Reviewed" (status `acknowledged`) "Review status", and the "Voice trends" tile "Change score <x.x>" (`cusum_state.current_tally` rounded to 1 decimal). | Must | BR-11, SRC-21 | 11 UX, 05 API | T |
| FR-263 | With the reference data at as-of 2026-10-30 15:00 America/Chicago, R09's Summary shall show Oct 21, 9 days, Not reviewed, change score 26.8 and R10's Oct 24, 6 days, Not reviewed, change score 13.4; the nav badge shall read 2. | Must | BR-11, BR-15, SRC-21 | 14 TDV | T |
| FR-264 | When the resident is Changed, the chart's "Review and notes" section shall start with the review panel headed "Review alert: changed since <Mon D>", reviewing the non-closed alert of the current epoch; the Summary buttons "Review this alert" and "See what changed" lead to this section and to Voice trends. | Must | BR-13, SRC-21, D-110 | 11 UX | T |
| FR-265 | (Retired by TRD 24 D-110: the Alert review mini chart is replaced by the change-score chart on Voice trends, FR-165, reached by "See what changed") | — | D-110 | — | — |
| FR-266 | The chart Summary of a Changed resident shall show "Leaning most: <labels>": up to 3 composite features with the highest mean signed z over the scored sessions from the alarm session (inclusive) to the as-of date, listing only features whose mean signed z is > 0, as lowercased plain-language labels without the parenthesised technical name, joined by ", " (test data R09: "more pauses, quieter, less voiced sound"); ties shall be broken by feature order of TRD 08; when no feature qualifies the text shall read "Leaning most: no single measurement stands out." (TRD 11 UX-312). | Must | BR-10, BR-13, SRC-21, D-92 | 08 BSC, 11 UX | T |
| FR-267 | The review form shall contain the multi-select fieldset "Anything that could explain it?" with the options of configuration list `review_explanations` (initially: `cold_cough_sore_throat` "Cold, cough or sore throat"; `dental_dentures` "Dental problem or dentures out"; `medication_change` "New or changed medication"; `poor_sleep_unusual_day` "Poor sleep or unusual day"; `room_device_moved` "Room or device moved"). | Must | BR-13, SRC-21, OQ-25 | 11 UX | T |
| FR-268 | The review form shall require exactly one outcome under "What did you find?": `no_concern` "Checked on resident, no concern"; `known_cause` "Explained by a known cause"; `referred` "Referred to nurse or provider"; `data_problem` "Looks like a data problem: send to study team". | Must | BR-13, SRC-21 | 11 UX | T |
| FR-269 | The review form shall contain an optional note of at most 2000 characters. | Must | BR-13, SRC-21 | 11 UX | T |
| FR-270 | "Save review" shall call `POST /api/v1/alerts/{id}/reviews` with `{explanations[], outcome, note?}`, creating one `alert_reviews` row (alert, reviewer, explanations, outcome, note, created_at) and setting the alert to `acknowledged` ("Reviewed", API `alarm_reviewed` true). | Must | BR-13, SRC-21, R5 | 05 API, 09 CUS | T |
| FR-271 | The review endpoint shall return 422 when the outcome is missing or unknown, an explanation code is not in `review_explanations`, or the note exceeds 2000 characters. | Must | BR-13 | 05 API | T |
| FR-272 | An alert shall accept multiple reviews; the review panel shall list earlier reviews under "Previous reviews" newest first (local time, reviewer, outcome label, explanations, note) from `GET /api/v1/alerts/{id}/reviews`. | Must | BR-13, SRC-21, D-111 | 05 API, 11 UX | T |
| FR-273 | A review with outcome `data_problem` shall create, or link to an existing open, data alert of kind `review_flagged_data_problem` for the resident: when no such alert is open it inserts one; when one is open it does not insert another but sets that alert's `alert_review_id` to the new review and refreshes `detail` and `last_detected_at`. Title and detail strings are those of TRD 09 CUS-040 (detail "a review flagged a data problem (<Mon D>, <display name>)."). | Must | BR-13, SRC-21, D-114 | 09 CUS | T |
| FR-274 | "Remind me in 24 hours" shall call `POST /api/v1/alerts/{id}/snooze {hours?}` (default `alert_snooze_hours` = 24), setting `snoozed_until` = now + hours and `snoozed_by`; the panel then shows "Reminder set for <Mon D, h:mm AM/PM CT>."; the alarm state shall not change. | Must | BR-13, SRC-21 | 05 API, 11 UX | T |
| FR-275 | Only roles `clinician` and `admin` shall save reviews or snooze alarms; other callers shall receive 403. | Must | BR-16, SRC-21, OQ-26 | 12 SEC | T |
| FR-276 | The system shall not enforce a review deadline or escalate unreviewed alarms in the MVP. | Must | BR-11, OQ-06, OQ-26 | 09 CUS | I |
| FR-277 | The review panel shall show "Open questions (OQ-05, OQ-26): Does a saved review reset the change score or turn the alarm off? Who may review? How soon must an alarm be reviewed? Pipeline v0.1 keeps alarms on." until OQ-05 and OQ-26 are closed. | Must | BR-18, SRC-21, OQ-05, OQ-26 | 11 UX | I |
| FR-278 | (Retired by TRD 24 D-110: the page footer is replaced by the data bar, FR-138, and the chart Summary note "It is a prompt to check in, not a diagnosis.", FR-164) | — | D-110 | — | — |
| FR-279 | Saving a review and snoozing an alarm shall each write an `audit_logs` entry. | Must | BR-16 | 12 SEC | T |
| FR-280 | When the resident has no change alarm in the current epoch, the "Review and notes" section shall show only the "Staff notes" panel (no review panel), and when no change alarm is unreviewed the "Resident list" link shall show no badge (TRD 11 UX-018, UX-120). | Must | BR-13, SRC-21 | 11 UX | T |

### 4.23 Data alerts for the study team (BR-04, BR-05, BR-06) — SRC-21

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-290 | Every pipeline run shall recompute data alerts over the last 30 days with the rules FR-291–FR-294, using thresholds from `config_parameters` (same values in both profiles). | Must | BR-04, BR-05, BR-06, SRC-21, OQ-24 | 07 ANL, 09 CUS | T |
| FR-291 | `baseline_stalled` (enabled by `data_alert_baseline_stalled_enabled` = true) shall be raised for a resident whose status is baseline forming and whose number of local days in the current epoch, counted inclusively as (as-of local date − current epoch start local date) + 1, is ≥ `baseline_n` (the rule of TRD 09 §4.9), with title "<R> · baseline stuck at <n> of <N>" and detail "baseline stuck at <n> of <N>. <missed> missed and <set aside> set aside in 30 days." | Must | BR-06, BR-09, SRC-21, D-114 | 07 ANL | T |
| FR-292 | `possible_other_speaker` shall be raised for a resident with ≥ 1 quarantined session in the last 30 days, with title "<R> · possible other speaker" and detail "<n> check-ins held back as possible other voice (<Mon D>, <Mon D>)." ("1 check-in held back as possible other voice (<Mon D>)."). | Must | BR-05, SRC-21, D-114 | 07 ANL | T |
| FR-293 | `high_set_aside` shall be raised for a resident with ≥ 10 received (non-duplicate) records and set_aside / received ≥ `data_alert_set_aside_fraction` (0.20) in the last 30 days, with title "<R> · many check-ins set aside" and detail "<set aside> of <received> received check-ins set aside (<reason kinds>).", reason kinds in the fixed order noise, quality flag, too short, listing only those present. | Must | BR-04, SRC-21, D-114 | 07 ANL | T |
| FR-294 | `device_silent` shall be raised for a device with ≥ 2 assigned residents and at least one device-gap day in the last 30 days, or for a single-resident device with ≥ `data_alert_device_silent_days` (2) consecutive silent days, with title "<device> · device silent all day" (one flagged day) or "<device> · device silent on <k> days" (k ≥ 2 flagged days; TRD 09 §4.9) and detail "silent all day <Mon D>. Affected <residents>." or "silent on <k> days (<Mon D>, …). Affected <residents>." (residents joined by ", " and " and "). | Must | BR-06, SRC-21, D-114 | 07 ANL | T |
| FR-295 | Each resident (or device) shall appear at most once per data-alert kind, and a resident with `baseline_stalled` shall not also be listed as `high_set_aside`. | Must | BR-06, SRC-21 | 07 ANL | T |
| FR-296 | A pipeline-generated data alert shall keep `first_detected_at` across runs, update `last_detected_at` while its rule holds, and change to status `resolved` on the first run in which the rule no longer holds. | Must | BR-02, SRC-21, R15 | 07 ANL, 06 DB | T |
| FR-297 | A data alert of kind `review_flagged_data_problem` shall remain `open` until an admin resolves it with a command-line action; the pipeline shall not resolve it. | Must | BR-13, R4 | 09 CUS | T |
| FR-298 | The Study team page section "Data problems to follow up" (TRD 11 §4.18.2; was queue 2 of the v0.1 Alert review page, TRD 24 D-110) shall list open data alerts as "**<code>:** <detail>" with the tag "Staff can help" (`baseline_stalled`, `high_set_aside`) or "Study team" (other kinds), without the ▲ glyph or red, and without any review form. | Must | BR-12, BR-18, SRC-21, VIS-029 | 11 UX | T |
| FR-299 | `GET /api/v1/data-alerts` shall return data alerts filterable by status and kind to any authenticated user. | Must | BR-12, SRC-21 | 05 API | T |
| FR-300 | Data alerts shall never create a health alarm, change a CUSUM tally or appear in the "Resident list" nav badge count. | Must | BR-11, SRC-21 | 09 CUS | T |
| FR-301 | With the reference data at as-of 2026-10-30 15:00 America/Chicago, the open data alerts shall be exactly: "R08 · baseline stuck at 13 of 16" / "baseline stuck at 13 of 16. 12 missed and 5 set aside in 30 days."; "R05 · possible other speaker" / "2 check-ins held back as possible other voice (Oct 8, Oct 22)."; "R03 · many check-ins set aside" / "7 of 29 received check-ins set aside (noise, quality flag, too short)."; "D02 · device silent all day" / "silent all day Oct 12. Affected R02 and R03." | Must | BR-15, SRC-21, D-114 | 14 TDV | T |
| FR-302 | An open data alert of kind `baseline_stalled` or `high_set_aside` shall set the resident's attention flag (API `needs_attention`, `attention_reasons`; TRD 24 D-114), shown as "! Needs attention" unless the resident is Changed (FR-131); data alerts of the other kinds (`possible_other_speaker`, `device_silent`, `review_flagged_data_problem`) and a device without upload shall not change a resident's display status (OQ-31). With the reference data the flag is set for R03 (`high_set_aside`) and R08 (`baseline_stalled`) only. | Must | BR-04, BR-06, BR-12, SRC-21, D-109, OQ-31 | 23 DME, 05 API, 11 UX | T |

### 4.24 Study team page (BR-12, BR-15) — SRC-21

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-310 | The Study team page (`/study`, replacing `/analytics`, TRD 24 D-110) and `GET /api/v1/analytics` shall be available only to roles `researcher` and `admin`; a clinician shall receive 403 and the access-denied page "You do not have access to this page." with "← Resident list" (TRD 04 FE-037, TRD 11 UX-350). | Must | BR-16, SRC-21 | 12 SEC, 04 FE | T |
| FR-311 | The page shall show the heading "Study team: how the system is working", the line "Counts only. No audio, no names." and the period line "<DATA_SOURCE_LABEL>, <period> · numbers match the pipeline answer key", where the last clause is shown only in the `test_v0_1` profile. | Must | BR-01, BR-15, BR-16, SRC-21 | 11 UX | T |
| FR-312 | The Study team period shall be the last 30 local days ending on the as-of date (reference data: Oct 1–30, 2026). | Must | BR-12, SRC-21, R10 | 05 API | T |
| FR-313 | The page shall show four KPI tiles: "Check-ins received" (percentage and "<received> of <expected> expected", received = non-duplicate records, expected = Σ over active residents of enrolled days in the period); "Used for scoring" (usable / expected); "Baselines formed" ("<n> of <active residents>" with a note naming forming residents and restart counts); "Alarms raised" (count of alarms triggered in the period with a note "<codes>; <review state>"). | Must | BR-12, BR-15, SRC-21 | 05 API, 11 UX | T |
| FR-314 | KPI percentages shall be rounded half-up to an integer. | Must | BR-15, SRC-21 | 05 API | T |
| FR-315 | The page shall show "Check-ins per day": one stacked bar per local day with segments Used, Set aside, Held back (other voice), Missed (legend in that order), duplicates excluded, x labels for the first day, each day with a silent device ("Oct 12: D02 silent") and the last day. | Must | BR-06, BR-12, SRC-21 | 11 UX | T |
| FR-316 | The page shall show "Where check-ins are lost": Expected (with "<residents> residents × <days> days"), Received (with "<missed> missed; <n> duplicate copies removed"), Passed quality checks (with "<n> set aside: quality flag <a>, noise <b>, too short <c>" counting each reason occurrence and "(<k> had two reasons)" when k > 0), Same speaker, used (with "<n> held back as possible other voice"). | Must | BR-03, BR-04, BR-05, BR-06, SRC-21 | 05 API, 11 UX | T |
| FR-317 | The page shall show "Usable check-ins by resident": per resident a meter of the share of period days with a usable check-in, lowest first, ties by resident code, with an accessible name giving used, set aside, held back and missed days. | Must | BR-12, SRC-21 | 11 UX | T |
| FR-318 | In the `test_v0_1` profile the page shall show "Alarm timing check" with the line "Test data only, where the true change date is known." and columns Resident, Planted change, Change began, Alarm rang, Delay (days = alarm local date − true onset date), read from `evaluation_ground_truth` after the run; residents without a planted change shall be grouped into one row "Other <n> · None · None · No alarm · Correct" when none of them alarmed. | Must | BR-11, BR-15, SRC-21, ARC-034 | 05 API, 14 TDV | T |
| FR-319 | In the `production` profile the alarm timing panel shall be replaced by "Alarms and review outcomes": counts of alarms raised, alarms with ≥ 1 review, and the latest review outcome per alarm counted by outcome. | Must | BR-13, BR-15, SRC-21 | 05 API, 11 UX | T |
| FR-320 | Each chart on the page shall have a text-table alternative. | Must | BR-12, NFR-060 | 11 UX | T |
| FR-321 | (Retired by TRD 24 D-110: the page footer is replaced by the header line "Counts only. No audio, no names.", FR-311, and the data bar, FR-138) | — | D-110 | — | — |
| FR-322 | `GET /api/v1/analytics` shall return `kpis`, `daily_series`, `funnel`, `by_resident` and either `alarm_timing` (`test_v0_1`) or `review_outcomes` (`production`), in addition to the FR-240 content. | Must | BR-15, SRC-21 | 05 API | T |
| FR-323 | With the reference data the page shall show: received 94% "281 of 300 expected"; used 89% "267 of 300 expected"; baselines "9 of 10" "R08 still forming; R07 restarted once"; alarms 2 "R09, R10; neither reviewed yet"; data problems R08, R03, R05, D02 (FR-301); funnel 300 → 281 → 269 → 267 with "12 set aside: quality flag 5, noise 5, too short 3 (1 had two reasons)"; usable shares R08 43%, R03 73%, R02 80%, R05 93%, others 100%; alarm timing R09 Sudden step Oct 21 / Oct 21 / 0 days, R10 Slow drift Oct 17 / Oct 24 / 7 days, Other 8 None / None / No alarm / Correct (TRD 11 §4.18.8). | Must | BR-15, SRC-21 | 14 TDV | T |

### 4.25 Page chrome, navigation and response metadata

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-330 | Every signed-in page shall show the app bar with "EchoWell", the facility line "<facility name>, Assisted living", the navigation "Resident list" (followed by a red badge with n when n > 0, where n = number of change alarms with status `open`, i.e. not yet reviewed; data alerts are not counted), "New admissions", "Study team" (researcher, admin) and "Admin" (admin), the signed-in display name and "Sign out" (TRD 11 §4.2; TRD 24 D-110). | Must | BR-12, SRC-21, R2 | 04 FE, 11 UX | T |
| FR-331 | `/residents/[residentCode]` and its sections shall start with "← Resident list" and show the app bar (the chart counts as "Resident list" in the navigation); `/admissions` is reached from the navigation and has no back link. | Must | BR-13, BR-14, SRC-21, R2 | 11 UX | T |
| FR-332 | Every list, detail and analytics response shall include `meta {facility_name, facility_tz, data_source_label, as_of, baseline_n, cusum_h, pipeline_profile}`. | Must | BR-12, BR-15, R3 | 05 API | T |
| FR-333 | `meta.as_of` on read endpoints shall be the `as_of` of the latest succeeded pipeline run. | Must | BR-06, BR-15, R21 | 05 API | T |

### 4.26 Role permission matrix

| Capability | admin | clinician | researcher | API key `ingest:write` | API key `pipeline:run` |
|---|---|---|---|---|---|
| View Resident list, Resident chart (all sections incl. check-in log, notes, review history, devices), admissions | Yes | Yes | Yes (read-only) | No | No |
| Save alarm review, snooze alarm (chart "Review and notes") | Yes | Yes | No | No | No |
| Add staff note | Yes | Yes | No | No | No |
| Study team page (`/study`, incl. data problems and devices) and `/analytics*` endpoints | Yes | No | Yes | No | No |
| CSV export of baselines and scores | Yes | No | Yes | No | No |
| `GET /scores` JSON for Resident chart charts | Yes | Yes | Yes | No | No |
| View pipeline runs (list and detail), ingest batch results | Yes | No | Yes | No | No |
| Trigger pipeline run | Yes | No | No | No | Yes |
| Upload CSV / batch ingest | Yes | No | No | Yes | No |
| Single record ingest (`POST /sessions`) | No | No | No | Yes | No |
| Manage users | Yes | No | No | No | No |
| API keys, residents, devices, assignments | CLI only (no endpoints) | No | No | No | No |

Note: `GET /api/v1/scores` is authorised for any user (contract §10) because the Resident chart's change-score chart uses it; `GET /api/v1/data-alerts` and `GET /api/v1/devices` stay readable by every role although their main consumer is the Study team page, because the attention flag and the chart Device section use the same data; FR-243 and FR-310 restrict the `/analytics*` endpoints and page; CSV export (FR-244) is researcher/admin only.

### 4.27 Use cases

#### UC-01 Ingest one check-in record

| Field | Content |
|---|---|
| Actor | Team 1 device (API key `ingest:write`) |
| Trigger | Resident says the wake word and phrase; device has extracted features |
| Preconditions | Resident enrolled and active; device registered; API key active |
| Inputs | JSON record, schema v0.1 (TRD 10) |
| Processing | Authenticate key → rate-limit → validate schema/resident/device → insert `raw_sessions` → run pipeline for resident and device co-residents → audit |
| Outputs | 201 `{raw_session_id, arrival_seq, status_after_processing}`; derived tables updated; check-in visible on dashboard |
| Errors / alternatives | 401 bad key; 422 invalid (logged in `ingest_rejections`); 422 "resident withdrawn"; 200 `duplicate` for a repeat session_id; 429 rate limit; pipeline failure → record kept, 201 with `status_after_processing: "pending"`, run `failed`, next run processes it (R23) |
| Related FRs | FR-001, FR-005–FR-008, FR-012–FR-015, FR-020–FR-031, FR-040–FR-125, FR-184 |

#### UC-02 Upload test CSV

| Field | Content |
|---|---|
| Actor | Admin |
| Preconditions | Logged in as admin; residents and devices seeded |
| Inputs | CSV file with the SRC-05 header (e.g. SRC-05 itself) |
| Processing | Upload on `/admin` → `POST /api/v1/ingest` multipart → per-row validation in file order → accepted rows to `raw_sessions` → 202 → background pipeline for affected residents → batch result page polls `GET /api/v1/ingest/batches/{id}` |
| Outputs | Batch summary (SRC-05: 283 accepted incl. 2 later marked duplicate, 0 rejected); dashboard reflects data |
| Errors | Wrong header → 422 for the whole file; invalid rows listed with errors; non-admin → 403 |
| Related FRs | FR-002–FR-004, FR-009–FR-011, FR-222, FR-250 |

#### UC-03 Run pipeline (nightly, manual, rebuild)

| Field | Content |
|---|---|
| Actor | Nightly job (separate Railway Cron Job service running `python -m backend.jobs.nightly_run`, proceeding only in the facility-local hour `NIGHTLY_RUN_HOUR_LOCAL`, default 02:xx, R18); Admin or API key `pipeline:run` (manual) |
| Inputs | Scope (`all` or resident codes), profile, as-of time |
| Processing | Create `pipeline_runs` row → load raw records, frozen baselines, config snapshot → `analytics.pipeline.run_pipeline` → upsert derived rows per resident in one transaction → record counts, warnings (`late_arrival`) → status `succeeded` |
| Outputs | Updated derived tables; day ledger extended to as-of date; run record |
| Errors | Exception → run `failed` with error summary, derived tables of unaffected residents unchanged; production with `test_v0_1` profile refused |
| Related FRs | FR-029–FR-125, FR-223–FR-225, FR-229, FR-230 |

#### UC-04 Review the resident list

| Field | Content |
|---|---|
| Actor | Clinician (primary); researcher; admin |
| Inputs | Filter choice (`?show=`) |
| Processing | `GET /api/v1/residents` (default `sort=alarm`) → render filter buttons from `summary`, rows with status pill and "What's happening", status legend; filter in the browser |
| Outputs | Filter counts, rows in the D-109 order with display status, reason and last check-in |
| Errors | Expired token → `/login`; API unavailable → error banner with retry, no stale numbers shown as current |
| Related FRs | FR-130–FR-140, FR-211, FR-302, FR-330 |

#### UC-05 Review a resident's chart

| Field | Content |
|---|---|
| Actor | Clinician; researcher; admin |
| Inputs | Resident code (row or study-ID link on the Resident list) |
| Processing | `GET /residents/{code}`, `/features`, `/checkins`, `/notes`, `/scores?resident_code=`, `/alerts?resident_code=`, `/devices` → render banner, section navigation and the sections Summary, Review and notes, Voice trends (change score, 7 measurements), Baseline, Check-in log, Device |
| Outputs | Resident chart per SRC-21 |
| Errors | Unknown code → "Resident <code> was not found."; resident with baseline forming → Voice trends shows "No change score yet. Scoring starts after the baseline is complete (<n> of <N> usable check-ins so far)." and no bars |
| Related FRs | FR-150–FR-156, FR-160–FR-173, FR-180–FR-184, FR-193, FR-262, FR-266 |

#### UC-06 Record staff note

| Field | Content |
|---|---|
| Actor | Clinician or admin |
| Preconditions | Resident chart open at "Review and notes" |
| Inputs | Note type (`observation`, `action_taken`, `follow_up`), body (≤ 2000 chars) |
| Processing | `POST /residents/{code}/notes` → insert note → audit (note created). Reviewing an alarm uses the review panel of the same section (UC-13, R5). |
| Outputs | Note listed; alert status unchanged by notes |
| Errors | Empty or > 2000 chars → 422; researcher → 403 |
| Related FRs | FR-190–FR-195, FR-250 |

#### UC-07 View new admissions (experimental)

| Field | Content |
|---|---|
| Actor | Clinician; researcher; admin |
| Processing | `GET /api/v1/admissions`; select resident → `GET /api/v1/admissions/{code}/comparison`; `GET /api/v1/facility/reference-ranges` |
| Outputs | Experimental note; list with status pill and comparison text; dot-vs-band chart |
| Errors | No new admissions → empty state "No new admissions"; no reference ranges → "Facility range not available yet" |
| Related FRs | FR-200–FR-207 |

#### UC-08 Manage users

| Field | Content |
|---|---|
| Actor | Admin |
| Inputs | E-mail, display name, role, initial password; role/active changes |
| Processing | `/admin` → `GET/POST/PATCH /api/v1/users` → argon2id hash → audit (user change) |
| Outputs | User list updated |
| Errors | Duplicate e-mail → 409; weak password → 422 (policy in TRD 12); non-admin → 403; an admin cannot deactivate their own account |
| Related FRs | FR-213, FR-214, FR-220, FR-221, FR-250 |

#### UC-09 Log in and out

| Field | Content |
|---|---|
| Actor | Any dashboard user |
| Processing | `POST /auth/login` → token → `GET /auth/me` → role-aware navigation ("Study team" for researcher/admin, "Admin" for admin); "Sign out" discards token |
| Errors | Wrong credentials → 401 generic message; inactive → 401; 6th attempt within a minute → 429 |
| Related FRs | FR-210–FR-218 |

#### UC-10 Review device health

| Field | Content |
|---|---|
| Actor | Researcher, admin (Study team page); any role (chart Device section) |
| Processing | Study team page `/study#devices`, or a resident's chart "Device" section, from `GET /api/v1/devices` |
| Outputs | Online / No upload today, shared devices, replacements, last upload, firmware, silent days and device-gap days |
| Related FRs | FR-150–FR-156 |

#### UC-11 Validate pipeline against the answer key

| Field | Content |
|---|---|
| Actor | Researcher or CI |
| Processing | Load SRC-05 (UC-02 or test harness) with profile `test_v0_1` → full run → `GET /analytics`, `/analytics/baselines`, `/scores` (or direct table reads in tests) → compare with SRC-03 |
| Outputs | Pass/fail per sheet; 100% match required |
| Related FRs | FR-031, FR-137, FR-240–FR-244, FR-302 |

#### UC-12 Export data for offline analysis

| Field | Content |
|---|---|
| Actor | Researcher |
| Processing | Request analytics/baselines/scores as CSV |
| Outputs | CSV files with study IDs only |
| Related FRs | FR-240–FR-245 |

#### UC-13 Review an alarm

| Field | Content |
|---|---|
| Actor | Charge nurse or clinical lead (role `clinician`), or admin |
| Trigger | The "Resident list" navigation badge shows n > 0, or a Changed resident's chart ("Review this alert", "Review and notes" badge) |
| Preconditions | Logged in; at least one open alarm |
| Inputs | The resident's alarm; explanations (0..5 codes from `review_explanations`); outcome (required); note (optional, ≤ 2000 chars); or "Remind me in 24 hours" |
| Processing | `GET /api/v1/alerts?status=open` (nav badge) and `GET /api/v1/alerts?resident_code=<R>` → chart Summary (alarm facts, "Leaning most") and "Review and notes" panel with "Previous reviews" (`GET /alerts/{id}/reviews`); the change itself is seen on Voice trends (`GET /scores`) → "Save review" → `POST /alerts/{id}/reviews` → `alert_reviews` row, alert `acknowledged`, data alert for outcome `data_problem` → audit; or "Remind me in 24 hours" → `POST /alerts/{id}/snooze` → audit |
| Outputs | Summary and list text show "Reviewed" and the badges decrease (or "Reminder set for …"); review history updated; alarm stays on and change score unchanged (OQ-05) |
| Errors / alternatives | Missing outcome → "Choose what you found."; bad code → 422; researcher → 403 (read-only view); alert closed meanwhile (epoch ended) → 409 and the chart refreshes; resident not Changed → no review panel (FR-280) |
| Related FRs | FR-106, FR-107, FR-191, FR-260–FR-280, FR-330 |

#### UC-14 View the Study team page

| Field | Content |
|---|---|
| Actor | Researcher (study team) or admin |
| Preconditions | Logged in with role `researcher` or `admin`; at least one succeeded pipeline run |
| Inputs | None (period = last 30 local days ending at `meta.as_of`) |
| Processing | `GET /api/v1/analytics`, `GET /api/v1/data-alerts`, `GET /api/v1/devices` → KPI tiles, data problems to follow up, check-ins per day, where check-ins are lost, usable check-ins by resident, alarm timing check (`test_v0_1`, from `evaluation_ground_truth`) or alarms and review outcomes (`production`), devices, downloads |
| Outputs | Study team page per SRC-21 with text-table alternatives; for reference data the values of FR-323 |
| Errors / alternatives | Clinician → 403 access-denied page "You do not have access to this page." (FR-310); no succeeded run → empty state "No pipeline run yet" |
| Related FRs | FR-150–FR-156, FR-240–FR-245, FR-298, FR-310–FR-323, FR-330, FR-332, FR-333 |

#### UC-15 Triage data alerts

| Field | Content |
|---|---|
| Actor | Pipeline (generation); researcher or admin (reading) |
| Processing | Each pipeline run evaluates the data-alert rules over the last 30 days → upserts `data_alerts` (open / resolved) → the Study team page lists open data alerts under "Data problems to follow up"; open `baseline_stalled` and `high_set_aside` alerts set the residents' attention flag (Needs attention on the Resident list) |
| Outputs | Study team sees data-quality issues separate from health alarms |
| Errors / alternatives | Rule disabled in configuration → no alert of that kind; `review_flagged_data_problem` stays open until an admin resolves it by CLI |
| Related FRs | FR-290–FR-302 |

### 4.28 Traceability: BR → FR

| BR | FRs |
|---|---|
| BR-01 | FR-001–FR-005, FR-007, FR-009, FR-011–FR-013, FR-015, FR-020–FR-025, FR-027, FR-028, FR-032, FR-138, FR-139, FR-184, FR-207, FR-222, FR-226, FR-278, FR-311, FR-321 |
| BR-02 | FR-005, FR-006, FR-007, FR-010, FR-028, FR-032, FR-223, FR-296 |
| BR-03 | FR-008, FR-011, FR-029–FR-031, FR-139, FR-182, FR-316 |
| BR-04 | FR-024, FR-040–FR-044, FR-181, FR-290, FR-293, FR-302, FR-316 |
| BR-05 | FR-060–FR-065, FR-074, FR-181, FR-290, FR-292, FR-316 |
| BR-06 | FR-120–FR-125, FR-135, FR-153, FR-154, FR-181, FR-290, FR-291, FR-294, FR-295, FR-302, FR-315, FR-316, FR-333 |
| BR-07 | FR-070–FR-074, FR-171 |
| BR-08 | FR-050–FR-053, FR-132, FR-155, FR-172, FR-181 |
| BR-09 | FR-052, FR-080–FR-086, FR-162, FR-163, FR-205, FR-229, FR-230, FR-291 |
| BR-10 | FR-082, FR-090–FR-095, FR-169, FR-170, FR-266 |
| BR-11 | FR-053, FR-100–FR-110, FR-165–FR-167, FR-181, FR-206, FR-229, FR-261–FR-263, FR-265, FR-276, FR-300, FR-318 |
| BR-12 | FR-130–FR-140, FR-150–FR-156, FR-227, FR-298, FR-299, FR-302, FR-312, FR-313, FR-315, FR-317, FR-320, FR-330, FR-332 |
| BR-13 | FR-106, FR-108, FR-160–FR-173, FR-180–FR-184, FR-190–FR-195, FR-260–FR-274, FR-277, FR-280, FR-297, FR-319, FR-331 |
| BR-14 | FR-200–FR-207, FR-331 |
| BR-15 | FR-002, FR-003, FR-031, FR-137, FR-222–FR-225, FR-240–FR-244, FR-263, FR-301, FR-311, FR-313, FR-314, FR-318, FR-319, FR-322, FR-323, FR-332, FR-333 |
| BR-16 | FR-004, FR-013–FR-015, FR-026, FR-168, FR-192, FR-194, FR-210–FR-221, FR-226–FR-229, FR-243, FR-245, FR-250–FR-252, FR-254, FR-275, FR-279, FR-310, FR-321 |
| BR-17 | FR-253, FR-254 |
| BR-18 | FR-164, FR-277, FR-278, FR-298 (and constraints VIS-003..005, VIS-029, TRD 00) |

### 4.29 Traceability: UC → FR coverage check

Every FR in sections 4.2–4.25 is exercised by at least one use case: ingestion/validation/analytics FRs (FR-001–FR-125) by UC-01, UC-02, UC-03, UC-11; resident list and devices (FR-130–FR-156) by UC-04, UC-05, UC-10; chart, log and notes (FR-160–FR-195) by UC-05, UC-06; admissions (FR-200–FR-207) by UC-07; auth (FR-210–FR-218) by UC-09; admin (FR-220–FR-230) by UC-02, UC-03, UC-08; analytics (FR-240–FR-245) by UC-11, UC-12; audit/health (FR-250–FR-254) by all use cases; legacy file rejection (FR-032) by UC-02; alert review (FR-260–FR-280) by UC-13; data alerts (FR-290–FR-302) by UC-03, UC-15; Study team page (FR-310–FR-323) by UC-14; page chrome and metadata (FR-330–FR-333) by UC-04, UC-13, UC-14.

## 5. Assumptions

- ASM-01 (America/Chicago), ASM-02 (≤ 1 session per resident per local day), ASM-03 (single facility), ASM-04 (16 test / 30 production; D-OWNER-2), ASM-05 (HTTPS POST or CSV), ASM-06 (new epoch closes open alert), ASM-07 (frozen baselines never recomputed), ASM-08 (small scale).
- Decided by the lead (contract §20–§21) and applied here: watching since (R9), last check-in and 30-day window (R10), as-of precedence (R21), logout, pipeline runs list, CSV export and CLI-only master data (R4), single review model (R5), chart bars (R1), page chrome (R2), meta block (R3), legacy file rejection (R12), `pending` status (R23).
- Notes for lead (TRD-local definitions introduced here): "Open alarm" = status open or acknowledged; "Silent day (device)" and "Device-gap day" (section 4.1); comparison status "Facility range not available yet" (FR-202); strict rejection of unknown fields (FR-013); ledger stops at `withdrawn_on` (FR-120); "Leaning most" window, tie-break and empty text (FR-266); review history display (FR-272); `review_flagged_data_problem` resolved only by admin CLI (FR-297); no review panel for residents who are not Changed (FR-280); production review-outcome counting uses the latest review per alarm (FR-319); Study team nav hidden from clinicians (FR-218); the attention flag from `baseline_stalled` and `high_set_aside` only (FR-302, OQ-31).

## 6. Dependencies

- TRD 07/08/09 for exact algorithm definitions; TRD 10 for the schema; TRD 05/19 for endpoint contracts; TRD 11 for exact copy and sort rules; TRD 12 for role enforcement.
- SRC-03 workbook copied into `tests/fixtures/` for UC-11.
- Team 1 record conformance for UC-01 in the demo (OQ-03, OQ-04).

## 7. Acceptance Criteria

| ID | Criterion |
|---|---|
| AC-FR-01 | Ingesting SRC-05 via CSV with profile `test_v0_1` yields status counts per resident equal to SRC-03 Exp_status_counts (totals: usable 267, set_aside 12, quarantined 2, duplicate 2, missing_resident 17, missing_device_gap 2). |
| AC-FR-02 | Outcomes per resident equal Exp_resident_outcomes: freeze sessions as listed in TRD 14, R09 first alarm at R09-20261021-01 (tally 5.432 ± 1e-6), R10 at R10-20261024-01, no alarm for R01–R08. |
| AC-FR-03 | `baselines` contains 180 rows and `scores` 98 rows matching Exp_baselines and Exp_scores within 1e-6. |
| AC-FR-04 | The residents API returns summary changed 2, needs attention 2, learning 0, usual 6 and the Resident list shows the filters "All (10)", "Changed (2)", "Needs attention (2)", "Usual (6)" and the default order R09, R10, R03, R08, R01, R02, R04, R05, R06, R07 at as-of 2026-10-30 15:00 America/Chicago (D-109, amending R16). |
| AC-FR-05 | Posting R04's day-5 record a second time returns 200 with `duplicate`, and the R04 results are unchanged. |
| AC-FR-06 | A record with `audio_quality_flag = "bad"` returns 422 with an error naming `audio_quality_flag`, appears in `ingest_rejections`, and does not appear in `raw_sessions`. |
| AC-FR-07 | A clinician saves a review for R09 (outcome `known_cause`, explanation `cold_cough_sore_throat`) in its "Review and notes" section: an `alert_reviews` row is created, the alert becomes `acknowledged`, the Summary shows "Reviewed" and the list text ends "Reviewed.", the pill still reads "▲ Changed", the nav badge drops to 1, and the change score is unchanged; `POST /alerts/{id}/acknowledge` returns 404. |
| AC-FR-08 | A researcher receives 403 on `POST /residents/R09/notes`, `POST /alerts/{id}/reviews` and `POST /pipeline/run`, and 200 on `GET /analytics`; a clinician receives 403 on `GET /analytics` and 200 on `POST /alerts/{id}/reviews`. |
| AC-FR-09 | R09's Voice trends section shows the change-score chart with a grey slot "Baseline Oct 1–16", grey bars Oct 17–20, red bars from Oct 21 to Oct 30, the "Alarm line: 5", an "Oct 21 · alarm" label, and R09's Check-in log shows "Oct 21" "Alarm on. Change score crossed 5.", "Oct 17" "Comparing with baseline started.", "Oct 16" "Baseline complete (16 of 16)." and, oldest, "Oct 1" "Check-ins started." (R07: "Check-ins started on D07."). |
| AC-FR-10 | The New admissions page shows the experimental note and, with no reference ranges loaded, the text "Facility range not available yet" or "Not enough check-ins yet" for every listed resident. |
| AC-FR-11 | Every FR in this document appears in the BR → FR table and in at least one use case. |
| AC-FR-12 | With the reference data the nav badge reads 2, the Summaries of R09 and R10 show the facts of FR-263, and the Study team page lists exactly the four data problems of FR-301 (R08, R03, R05, D02); R03 and R08 are "Needs attention" and R05 is "Usual" (FR-302); snoozing R10 shows "Reminder set for …" and leaves its alarm on. |
| AC-FR-13 | `/study` with the reference data shows every value listed in FR-323. |
| AC-FR-14 | Uploading the legacy SRC-06 file returns 422 "schema mismatch" and creates no `raw_sessions` row. |

## 8. Implementation Notes

- Implement FRs in the batch order of TRD 25; the analytics FRs (4.3–4.11) must pass UC-11 before the UI batches start.
- Keep display strings (status pills, legend, "What's happening", Summary texts, captions) in one frontend copy module and backend configuration; tests compare exact strings.
- Use `resident_code` (e.g. R01) in URLs and API paths, never UUIDs.
- The 30-day counts come from `processed_sessions` and `day_ledger` for the last-30-days window, and the status, attention flag, summary counts and default order come from the API; do not recompute statistics or statuses in the frontend (the display status is a presentation mapping of `status` and `needs_attention`).
- `status_after_processing` for a set-aside record is `set_aside` even though the record is stored in `raw_sessions`; the 201 code means "stored", not "usable".
- Data-alert text and Study team numbers are exact-string tested against FR-301 and FR-323; build them from the same 30-day window helper as the resident list.
- The alarm timing panel reads `evaluation_ground_truth` through the read-only role (`echowell_readonly`), never through the app role, which has no SELECT on that table (R20).

## 9. Open Questions

| ID | Affects |
|---|---|
| OQ-03 | FR-012, FR-171 (placeholder feature names) |
| OQ-04 | FR-021 (`phrase_id` kept while open) |
| OQ-05 | FR-107, FR-277 |
| OQ-06 | FR-109, FR-276 |
| OQ-08 | FR-202, FR-204, FR-205 |
| OQ-09 | FR-073 |
| OQ-10 | FR-084 |
| OQ-11 | FR-026, FR-228 |
| OQ-12 | FR-164 |
| OQ-31 | FR-131, FR-152, FR-302 (which data problems turn a resident to Needs attention; when a device counts as offline); answered 26 Oct 2026, TRD 24 D-115 |
| OQ-32 | FR-134 (room numbers on the Resident list; none shown); answered 26 Oct 2026, TRD 24 D-116 |
| OQ-14 | FR-062 (screen compensates for missing speaker verification) |
| OQ-15 | FR-124 |
| OQ-18 | EWMA display not specified |
| OQ-20 | FR-204 (sex needed for F0 ranges) |
| OQ-24 | FR-290–FR-296 (data-alert thresholds are provisional defaults) |
| OQ-25 | FR-267 (explanation checklist) |
| OQ-26 | FR-275–FR-277 (who may review alarms and how soon) |

## Revision History

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1 | 18 Oct 2026 | Initial generation from TRD_Generation_Prompt.md | — |
| 0.1 | 18 Oct 2026 | Cross-TRD consistency review | — |
| 0.2 | 19 Oct 2026 | Phase 1 validation fixes (F-06, F-07, F-08, F-09, F-12, F-21, F-24, F-25, F-29, F-36, F-37) | — |
| 0.3 | 19 Oct 2026 | Phase 1 round-2 fixes (R2-01, R2-03, R2-13, R2-23) | — |
| 0.4 | 20 Oct 2026 | PR #2 backlog consistency fixes (FR-134, FR-150, FR-168, FR-169, FR-192, FR-240, FR-244, FR-260, FR-266, FR-280, FR-294, FR-310, UC-13, UC-14 aligned with TRD 11/19/23; FR-172 traces OQ-28; nightly actor hour) | — |
| 0.5 | 26 Oct 2026 | Wireframe v0.2 (SRC-21; TRD 24 D-108 to D-114): SRC-09/10/11/18/19 superseded; §4.12–§4.17 and §4.22–§4.25 follow the Resident list, Resident chart, Study team and app bar of TRD 11 v0.13 (four display statuses, D-109 order, filter counts, `checkins_started`, v0.2 data-alert details, change-score and held-back wording); retired FR-136, FR-139, FR-195, FR-207, FR-260, FR-261, FR-265, FR-278, FR-321 (D-110); new FR-302 (attention flag, OQ-31); role matrix, UC-04, UC-05, UC-06, UC-09, UC-10, UC-13 to UC-15, AC-FR-04, -07, -09, -10, -12, -13 updated | — |
| 0.6 | 26 Oct 2026 | PR #5 review round 1 (TRD 24 D-115 to D-119): OQ-31 and OQ-32 answered (D-115, D-116): FR-152 and the OQ table; date-time examples with "CT" (D-119) | — |
