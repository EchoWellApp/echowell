# 02 Functional Requirements Specification

Document ID: ECHOWELL-TRD-02 · Version 0.4 (draft for review) · Date: 18 October 2026 · Owner: Team 2 · Status: Draft

## 1. Purpose

This document is the master list of EchoWell functional requirements (FR-xxx). Each FR states one testable system behaviour, traces to a business requirement (BR-xx, TRD 00) and a source (SRC-xx), and points to the TRD that specifies it in detail. The document also defines the use cases (UC-xx) that exercise the FRs and closes with FR → BR and UC → FR traceability tables.

Where an FR and a detailed TRD differ, the detailed TRD governs the "how" and this document governs the "what"; a contradiction in the "what" is a defect to be raised with the lead.

## 2. Scope

**In scope:** every user-visible or interface-visible behaviour of the EchoWell MVP: ingestion, validation and duplicate handling, the ten analytics stages, persistence of results, the dashboard pages (Residents overview with Devices panel, Resident detail, Alert review, Analytics, New admissions, Admin), alarm review and data alerts, staff notes, authentication and roles, researcher analytics read-outs, audit logging.

**Out of scope:** quality attributes (TRD 03), Team 1 device behaviour, outbound alert delivery (OQ-06), data retention and deletion (OQ-01), EWMA trend display (OQ-18), LLM or ML features (BR-18), audio handling of any kind (BR-01).

## 3. References

| ID | Used for |
|---|---|
| SRC-02 | Storage flow and processing stages |
| SRC-03 | Parameters, expected results (acceptance answer key) |
| SRC-04 | Reference implementation of the rules |
| SRC-05 | Ingest CSV header and test input |
| SRC-09 | Residents overview wireframe (tiles, sort, row, devices panel, footer) |
| SRC-10 | Resident detail wireframe (header, What this means, tally chart, 7 measurements, staff review, check-in log) |
| SRC-11 | New admission check wireframe |
| SRC-12 | Page requirements in the TRD Generation Prompt |
| SRC-13 | Record fields, extractor, phrase ID |
| SRC-14 | Fixed constraints |
| SRC-18 | Alert review wireframe (queues, data alerts, review panel, outcomes, snooze) |
| SRC-19 | Analytics wireframe (KPIs, check-ins per day, funnel, usable by resident, alarm timing check) |
| Contract §19–§20 | Owner wireframe decision; lead reconciliation decisions R1–R17 (cited as R-numbers) |

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
| Device-gap day | A silent day of a device assigned to 2 or more residents that day, i.e. the day ledger records `missing_device_gap` for its residents (API field `device_gap_days_last_30`). The Devices panel text "silent all day <Mon D>" lists device-gap days. |
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
| FR-101 | Set-aside, quarantined, duplicate and missing days shall leave the tally unchanged. | Must | BR-11, SRC-10 caption | 09 CUS | T |
| FR-102 | The pipeline shall mark the first scored session whose tally is ≥ h (5.0) with alarm_state `rings` and every later scored session in the same epoch with alarm_state `on`. | Must | BR-11, SRC-03 Parameters "alarm" | 09 CUS | T |
| FR-103 | Scored sessions before the first crossing shall have alarm_state `off`. | Must | BR-11, SRC-03 Exp_scores | 09 CUS | T |
| FR-104 | The pipeline shall create exactly one `alerts` row per first crossing, recording resident, epoch, session_id, triggered_at, local_date and cusum value, with status `open`. | Must | BR-11, SRC-02 ("Flag for clinician review") | 09 CUS | T |
| FR-105 | The pipeline shall keep one `cusum_state` row per resident-epoch with the current tally, last scored session and alarm flag. | Must | BR-11 | 09 CUS, 06 DB | T |
| FR-106 | Saving an alarm review (FR-270) shall set the alert's status to `acknowledged` with `acknowledged_by` and `acknowledged_at`; no separate acknowledge endpoint shall exist (`POST /alerts/{id}/acknowledge` is replaced by `POST /alerts/{id}/reviews`). | Must | BR-11, BR-13, SRC-18, R5 | 09 CUS, 05 API | T |
| FR-107 | Saving a review or snoozing an alarm shall not reset the tally and shall not turn the alarm off. | Must | BR-11, OQ-05, SRC-18 | 09 CUS | T |
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

### 4.12 Residents overview (BR-12)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-130 | The Residents overview (`/residents`) shall list every active resident of the longitudinal cohort; withdrawn residents shall be hidden unless `include_withdrawn=true`. | Must | BR-12, SRC-09, SRC-12 | 04 FE, 11 UX | T |
| FR-131 | Each resident shall have exactly one display status: `alarm_on` ("▲ Alarm since <Mon D>") when an open alarm (status `open` or `acknowledged`) exists in the current epoch; `baseline_forming` ("Baseline forming · n of N sessions") when the current epoch has fewer than `baseline_n` usable sessions; otherwise `no_alarm` ("No alarm"). | Must | BR-12, SRC-09, SRC-12 | 11 UX | T |
| FR-132 | A `no_alarm` resident whose current epoch is greater than 1 shall show " · baseline restarted <Mon D>" using the current epoch start date. | Must | BR-08, BR-12, SRC-09 (R07) | 11 UX | T |
| FR-133 | The overview shall offer three sorts — "Alarms first" (default), "Resident ID", "Last check-in" — implementing the exact ordering rules of TRD 11. | Must | BR-12, SRC-09, SRC-12 | 11 UX, 05 API | T |
| FR-134 | Each row shall show Resident, Device (with "(shared)" when the device is currently assigned to ≥ 2 residents, or "(was <old>)" when the resident's previous device assignment ended the day before the current one started, the single rule of TRD 23 §4.4.1), Status, Last check-in (latest non-duplicate record of any status, local, e.g. "Oct 30, 2:28 PM") and an "Open" link. | Must | BR-12, SRC-09, R10 | 04 FE, 11 UX | T |
| FR-135 | Each row shall show "Last 30 days: used · set aside · quarantined · missed", where missed = missing_resident + missing_device_gap days and duplicates are never counted. | Must | BR-06, BR-12, SRC-09, SRC-12 | 11 UX | T |
| FR-136 | The overview shall show four summary tiles: "Alarm on" (count), "Being watched, no alarm" (count), "Baseline still forming" (count), "Missed check-ins, last 30 days" (sum of missed over listed residents). | Must | BR-12, SRC-09 | 11 UX | T |
| FR-137 | For the SRC-05 data at as-of 2026-10-30 15:00 America/Chicago with profile `test_v0_1`, the tiles shall read 2, 7, 1, 19 and the rows shall show the counts of SRC-03 Exp_status_counts. | Must | BR-12, BR-15, SRC-09 | 14 TDV | T |
| FR-138 | The header subline shall read "Voice check-ins · <FACILITY_NAME> · Showing <DATA_SOURCE_LABEL> as of <Mon D, YYYY, h:mm AM/PM TZ>". | Must | BR-12, SRC-09 | 11 UX | T |
| FR-139 | The overview footer shall read "No audio is stored or played here — only extracted voice measurements. Duplicate records are removed quietly and not shown." | Must | BR-01, BR-03, SRC-09 | 11 UX | I |
| FR-140 | Selecting "Open" on a row shall navigate to `/residents/<resident_code>`. | Must | BR-12, BR-13 | 04 FE | T |

### 4.13 Devices panel (BR-12, BR-06)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-150 | The overview shall include a Devices panel (anchor `#devices`; there is no "Devices" navigation link, TRD 11 UX-016) listing every active device with its currently assigned residents. | Must | BR-12, SRC-09, SRC-12 | 11 UX | T |
| FR-151 | A device assigned to ≥ 2 residents shall be shown as "<device> · shared by <residents>" (e.g. "D02 · shared by R02, R03"). | Must | BR-12, SRC-09 | 11 UX | T |
| FR-152 | For each device the panel shall show the last upload time (local) and firmware version. | Must | BR-12, SRC-09 | 11 UX | T |
| FR-153 | For each shared device the panel shall list its device-gap days in the last 30 days (e.g. "silent all day Oct 12"). | Must | BR-06, BR-12, SRC-09, SRC-12 | 11 UX | T |
| FR-154 | For each device the API shall report its silent days in the last 30 days (`silent_days_last_30`). | Should | BR-06, BR-12, SRC-12 ("days with no device activity") | 05 API, 11 UX | T |
| FR-155 | A device that replaced another for a resident shall be shown with "In use since <Mon D> (replaced <old>)" (e.g. D07B replaced D07 on Oct 13). | Must | BR-08, BR-12, SRC-09 | 11 UX | T |
| FR-156 | Devices with no device-gap day, no replacement and an upload on the as-of date may be grouped into one line ("D01, D04–D06, D08–D10 · All uploaded on Oct 30 · firmware fw-1.0.0"). | May | BR-12, SRC-09 | 11 UX | D |

### 4.14 Resident detail (BR-13)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-160 | The Resident detail page (`/residents/[residentCode]`) shall show a "← Back to all residents" link to `/residents`. | Must | BR-13, SRC-10 | 11 UX | T |
| FR-161 | The header shall show "<resident_code> · Device <device_code>" and the status badge of FR-131. | Must | BR-13, SRC-10 | 11 UX | T |
| FR-162 | When the current epoch's baseline is frozen, the header shall show "Baseline: first N usable check-ins, <first date>–<last date> (then frozen) · watched since <Mon D>". | Must | BR-09, BR-13, SRC-10, SRC-12 | 11 UX | T |
| FR-163 | When the current epoch's baseline is forming, the header shall show "Baseline forming · n of N sessions" as a progress indicator. | Must | BR-09, BR-13, SRC-12 | 11 UX | T |
| FR-164 | The page shall show a "What this means" section whose text comes from PI-reviewed configuration strings per status, including "It is a prompt to check in, not a diagnosis." and the marker "[Final clinical wording: confirm with PI]" until OQ-12 is closed. | Must | BR-13, BR-18, SRC-10, OQ-12 | 11 UX | I |
| FR-165 | The page shall show a "Running change tally" bar chart of the current epoch with one bar per scored session (height = cusum_tally), coloured #BDBDB8 with a 1 px #8A8A85 outline while alarm_state is `off` and #9A4508 when `rings` or `on`, preceded by a grey baseline slot labelled "Baseline <Mon D>–<Mon D>", with a dashed line at cusum_h labelled "alarm line 5.0" and x-axis labels including the watched-since date and the alarm date. | Must | BR-11, BR-13, SRC-10, SRC-12, R1 | 04 FE, 11 UX | T |
| FR-166 | The tally chart shall make alarm persistence visible by a non-colour cue (▲ marker at the first crossing and the "Oct 21 · alarm"-style label) in addition to the accent colour of bars with alarm_state `rings` or `on`. | Must | BR-11, BR-13, SRC-12 ("alarm persistence"), R1 | 11 UX | T |
| FR-167 | The tally chart shall carry the caption "Set-aside, quarantined and missed days leave the tally unchanged." | Must | BR-11, SRC-10 | 11 UX | I |
| FR-168 | The tally chart shall have an equivalent text table (columns "Date", "Tally", "Alarm", TRD 11 UX-090) available to assistive technology and by a visible toggle. | Must | BR-13, BR-16 (accessibility, TRD 03) | 11 UX | T |
| FR-169 | The page shall show "The 7 measurements behind the score" with one card per composite feature, showing the plain-language label of TRD 08 (e.g. "Quieter (loudness)", "More pauses (number of pauses)") and a sparkline of the signed deviations (sign × z) of the current epoch's scored sessions (TRD 11 UX-102). | Must | BR-10, BR-13, SRC-10, SRC-12 | 11 UX | T |
| FR-170 | The page shall show an eighth card "12 other measurements (pitch, jitter, MFCCs …) — stored, not scored" without values in the scoring summary. | Must | BR-10, BR-13, SRC-10, SRC-12 | 11 UX | I |
| FR-171 | The measurements section shall carry the caption "Column names are placeholders until Team 1 confirms extractor output names. Morning check-ins are adjusted before comparing." | Must | BR-07, OQ-03, SRC-10 | 11 UX | I |
| FR-172 | A user shall be able to view an earlier epoch's tally and baseline for a resident with more than one epoch. | Should | BR-08, BR-13, OQ-28 | 04 FE, 05 API | T |
| FR-173 | Requesting an unknown resident code shall show a "Resident not found" page and the API shall return 404. | Must | BR-13 | 05 API, 04 FE | T |

### 4.15 Check-in log (BR-13, BR-06)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-180 | The Resident detail page shall show a "Check-in log" listing events newest first, each as "<Mon D> · <event> · <detail>" (e.g. "Oct 21 · Alarm on · tally crossed 5.0"). | Must | BR-13, SRC-10 | 11 UX | T |
| FR-181 | The log shall include event types: alarm on, watching started, baseline complete ("Baseline complete (n of N)"), set aside (with reasons), quarantined ("possible other speaker"), missed (missing_resident), device silent (missing_device_gap), baseline restarted (new device/firmware/software). | Must | BR-04, BR-05, BR-06, BR-08, BR-11, BR-13, SRC-10, SRC-12 | 05 API, 11 UX | T |
| FR-182 | The log shall never contain duplicate records. | Must | BR-03, SRC-09 footer | 05 API | T |
| FR-183 | The check-in log API shall support filtering by `from` and `to` local dates. | Should | BR-13 | 05 API | T |
| FR-184 | A newly ingested usable record shall show on the dashboard after the ingest response returns, without manual pipeline action: (a) the Residents overview "Last check-in" of that resident shows the record's local time and its 30-day "used" count rises by 1; and (b) when the resident's baseline is frozen, the Resident detail tally chart gains one bar for that session (usable check-ins are not check-in log events, TRD 11 UX-144; TRD 24 D-67); a set-aside or quarantined record appears in the check-in log as its event type. | Must | BR-01, BR-13, SRC-15 demo step 5 | 01 ARC, 05 API | T, D |

### 4.16 Staff review (BR-13)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-190 | A user with role `clinician` or `admin` shall be able to add a staff note to a resident with a type (`observation`, `action_taken`, `follow_up`) and a body of 1 to 2000 characters. | Must | BR-13, SRC-10, SRC-12 | 05 API, 11 UX | T |
| FR-191 | The "Mark as reviewed" button on Resident detail shall open the alarm review form of FR-266–FR-270 for the resident's open alarm (single review model) and shall be hidden (not rendered) when the resident has no open alarm in the current epoch (TRD 04 FE-131, TRD 11 UX-121, UX-138); staff notes themselves shall not change alert status. | Must | BR-13, SRC-10 ("Mark as reviewed"), SRC-18, R5 | 11 UX, 09 CUS | T |
| FR-192 | Staff notes shall be append-only; a correction submitted through the API shall create a new note row referencing the superseded note via `supersedes_id` (the MVP UI offers no edit control, TRD 11 UX-129). | Must | BR-13, BR-16 | 06 DB | T |
| FR-193 | The Staff review section shall list the resident's notes newest first with type, author display name and local timestamp, showing only the latest version of edited notes. | Must | BR-13 | 11 UX | T |
| FR-194 | Users with role `researcher` shall see notes and reviews read-only and shall not see the note form, the review form, "Mark as reviewed" or "Remind me in 24 h". | Must | BR-13, BR-16, OQ-26 | 12 SEC, 11 UX | T |
| FR-195 | The Staff review section shall display the open-question note of TRD 11 UX-125 ("Open question (OQ-05): does review reset the tally or turn the alarm off? Not in pipeline v0.1 — a saved review marks the alarm as reviewed only; the alarm and the tally stay as they are.") until OQ-05 is closed. | Must | BR-13, OQ-05, SRC-10 | 11 UX | I |

### 4.17 New admissions — future / experimental (BR-14)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-200 | The New admissions page (`/admissions`) shall show the banner "Future / experimental study arm" and the note that the arm is not in pipeline test v0.1. | Must | BR-14, SRC-11, SRC-12 | 11 UX | T |
| FR-201 | The page shall list residents of cohort `new_admission` whose own baseline has not yet formed, with Study ID, admitted date, check-ins so far, comparison status and own-baseline progress "n of N". | Must | BR-14, SRC-11 | 05 API, 11 UX | T |
| FR-202 | The comparison status shall be one of "▲ Outside facility range", "Within facility range", "Not enough check-ins yet", or "Facility range not available yet" when no facility reference range exists (OQ-08); the API values are `outside_range`, `within_range`, `not_enough_checkins` and `range_not_available` (TRD 19 `ComparisonStatus`). | Must | BR-14, SRC-11, OQ-08 | 11 UX | T |
| FR-203 | Selecting a new admission shall show a per-feature comparison: the resident's value as a dot against the facility range as a grey band, captioned "grey band = usual range across current residents". | Must | BR-14, SRC-11 | 04 FE, 11 UX | T |
| FR-204 | Facility reference ranges shall be read from `facility_reference_ranges` with their method, number of residents and computation time; the method of computing them is not defined in the MVP (OQ-08). | Must | BR-14, OQ-08, RSK-13 | 06 DB, 07 ANL | I |
| FR-205 | A new-admission resident shall be compared only with their own baseline, and shall appear in the Residents overview instead of the New admissions list, once their own baseline has formed. | Must | BR-09, BR-14, SRC-11, SRC-12 | 07 ANL, 11 UX | T |
| FR-206 | New-admission comparisons shall never create alerts or affect the CUSUM of any resident. | Must | BR-11, BR-14, RSK-13 | 09 CUS | T |
| FR-207 | The page shall carry the footer "No audio is stored or played here — only extracted voice measurements." | Must | BR-01, SRC-11 | 11 UX | I |

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
| FR-218 | The navigation shall show "Admin" only to users with role `admin` and "Analytics" only to users with role `researcher` or `admin`. | Must | BR-16, SRC-19 | 04 FE | T |

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

### 4.22 Alert review page (BR-11, BR-13) — SRC-18

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-260 | The Alert review page (`/alerts`) shall show the header "Alert review", the subline "For the charge nurse or clinical lead · <DATA_SOURCE_LABEL> as of <Mon D, YYYY>", and a two-column layout: queues on the left, the review panel for the selected alarm on the right (stacked below 1024 px, TRD 11 UX-246). | Must | BR-13, SRC-18 | 04 FE, 11 UX | T |
| FR-261 | Queue 1 "Change alarms · need a nurse review" shall show one card per open alarm (status `open` or `acknowledged` in the resident's current epoch), ordered in three groups: (1) not reviewed and not snoozed, (2) not reviewed and snoozed (`snoozed_until` after now), (3) reviewed; within each group by alarm date ascending, then resident code. This row is the single definition of the queue order (TRD 09 §4.8, TRD 11 UX-301 reference it). | Must | BR-11, BR-13, SRC-18 | 11 UX | T |
| FR-262 | Each alarm card shall show "<resident> · <device>", a badge "Not reviewed" (status `open`) or "Reviewed" (status `acknowledged`), and "Alarm since <Mon D> · open <n> days · tally <x.x>", where n = as-of local date − alarm local date and the tally is `cusum_state.current_tally` rounded to 1 decimal. | Must | BR-11, SRC-18 | 11 UX, 05 API | T |
| FR-263 | With the reference data at as-of 2026-10-30 15:00 America/Chicago, Queue 1 shall show R09 (since Oct 21, open 9 days, tally 26.8) and R10 (since Oct 24, open 6 days, tally 13.4), both "Not reviewed". | Must | BR-11, BR-15, SRC-18 | 14 TDV | T |
| FR-264 | Selecting an alarm card shall show the review panel titled "<resident> · alarm since <Mon D>" with the link "Open full resident view →" to `/residents/<resident_code>`; the first card shall be selected by default. | Must | BR-13, SRC-18 | 11 UX | T |
| FR-265 | The review panel shall show a mini chart "Change tally since watching began (alarm line 5.0)" from the watched-since date to the as-of date, drawn with the bar rules of FR-165. | Must | BR-11, SRC-18, R1 | 11 UX | T |
| FR-266 | The review panel shall show "Leaning most": up to 3 composite features with the highest mean signed z over the scored sessions from the alarm session (inclusive) to the as-of date, listing only features whose mean signed z is > 0, as lowercased plain-language labels without the parenthesised technical name, joined by ", " (test data R09: "more pauses, quieter, less voiced sound"); ties shall be broken by feature order of TRD 08; when no feature qualifies the text shall read "No single measurement stands out." (TRD 11 UX-312). | Must | BR-10, BR-13, SRC-18 | 08 BSC, 11 UX | T |
| FR-267 | The review form shall contain the multi-select fieldset "Anything that could explain it?" with the options of configuration list `review_explanations` (initially: `cold_cough_sore_throat` "Cold, cough or sore throat"; `dental_dentures` "Dental problem or dentures out"; `medication_change` "New or changed medication"; `poor_sleep_unusual_day` "Poor sleep or unusual day"; `room_device_moved` "Room or device moved"). | Must | BR-13, SRC-18, OQ-25 | 11 UX | T |
| FR-268 | The review form shall require exactly one outcome: `no_concern` "Checked on resident, no concern"; `known_cause` "Explained by a known cause"; `referred` "Referred to nurse or provider"; `data_problem` "Looks like a data problem: send to study team". | Must | BR-13, SRC-18 | 11 UX | T |
| FR-269 | The review form shall contain an optional note of at most 2000 characters. | Must | BR-13, SRC-18 | 11 UX | T |
| FR-270 | "Save review" shall call `POST /api/v1/alerts/{id}/reviews` with `{explanations[], outcome, note?}`, creating one `alert_reviews` row (alert, reviewer, explanations, outcome, note, created_at) and setting the alert to `acknowledged` ("Reviewed"). | Must | BR-13, SRC-18, R5 | 05 API, 09 CUS | T |
| FR-271 | The review endpoint shall return 422 when the outcome is missing or unknown, an explanation code is not in `review_explanations`, or the note exceeds 2000 characters. | Must | BR-13 | 05 API | T |
| FR-272 | An alert shall accept multiple reviews; the review panel shall list earlier reviews newest first (reviewer, local time, outcome label, explanations, note) from `GET /api/v1/alerts/{id}/reviews`. | Must | BR-13, SRC-18 | 05 API, 11 UX | T |
| FR-273 | A review with outcome `data_problem` shall create, or link to an existing open, data alert of kind `review_flagged_data_problem` for the resident: when no such alert is open it inserts one; when one is open it does not insert another but sets that alert's `alert_review_id` to the new review and refreshes `detail` and `last_detected_at`. Title and detail strings are those of TRD 11 §4.17.2 (the only source). | Must | BR-13, SRC-18 | 09 CUS | T |
| FR-274 | "Remind me in 24 h" shall call `POST /api/v1/alerts/{id}/snooze {hours?}` (default `alert_snooze_hours` = 24), setting `snoozed_until` = now + hours and `snoozed_by`; while `snoozed_until` is in the future the card shall not show the "Not reviewed" emphasis; the alarm state shall not change. | Must | BR-13, SRC-18 | 05 API, 11 UX | T |
| FR-275 | Only roles `clinician` and `admin` shall save reviews or snooze alarms; other callers shall receive 403. | Must | BR-16, SRC-18, OQ-26 | 12 SEC | T |
| FR-276 | The system shall not enforce a review deadline or escalate unreviewed alarms in the MVP. | Must | BR-11, OQ-06, OQ-26 | 09 CUS | I |
| FR-277 | The review panel shall show "Open questions: Does a saved review reset the tally or turn the alarm off? Who may review? How soon must an alarm be reviewed? Pipeline v0.1 keeps alarms on." until OQ-05 and OQ-26 are closed. | Must | BR-18, SRC-18, OQ-05, OQ-26 | 11 UX | I |
| FR-278 | The page footer shall read "An alarm is a prompt to check in, not a diagnosis. No audio is stored or played here." | Must | BR-01, BR-18, SRC-18 | 11 UX | I |
| FR-279 | Saving a review and snoozing an alarm shall each write an `audit_logs` entry. | Must | BR-16 | 12 SEC | T |
| FR-280 | When no open alarm exists, Queue 1 shall read "No change alarms right now." and the review panel shall read "No change alarms to review." (TRD 11 UX-305, UX-319). | Must | BR-13 | 11 UX | T |

### 4.23 Data alerts for the study team (BR-04, BR-05, BR-06) — SRC-18

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-290 | Every pipeline run shall recompute data alerts over the last 30 days with the rules FR-291–FR-294, using thresholds from `config_parameters` (same values in both profiles). | Must | BR-04, BR-05, BR-06, SRC-18, OQ-24 | 07 ANL, 09 CUS | T |
| FR-291 | `baseline_stalled` (enabled by `data_alert_baseline_stalled_enabled` = true) shall be raised for a resident whose status is baseline forming and whose number of local days in the current epoch, counted inclusively as (as-of local date − current epoch start local date) + 1, is ≥ `baseline_n` (the rule of TRD 09 §4.9), with title "<R> · baseline stuck at <n> of <N>" and detail "<missed> missed and <set aside> set aside in 30 days". | Must | BR-06, BR-09, SRC-18 | 07 ANL | T |
| FR-292 | `possible_other_speaker` shall be raised for a resident with ≥ 1 quarantined session in the last 30 days, with title "<R> · possible other speaker" and detail "<n> check-ins quarantined: <Mon D>, <Mon D>". | Must | BR-05, SRC-18 | 07 ANL | T |
| FR-293 | `high_set_aside` shall be raised for a resident with ≥ 10 received (non-duplicate) records and set_aside / received ≥ `data_alert_set_aside_fraction` (0.20) in the last 30 days, with title "<R> · many check-ins set aside" and detail "<set aside> of <received> received: <reason kinds>", reason kinds in the fixed order noise, quality flag, too short, listing only those present. | Must | BR-04, SRC-18 | 07 ANL | T |
| FR-294 | `device_silent` shall be raised for a device with ≥ 2 assigned residents and at least one device-gap day in the last 30 days, or for a single-resident device with ≥ `data_alert_device_silent_days` (2) consecutive silent days, with title "<device> · device silent all day" (one flagged day) or "<device> · device silent on <k> days" (k ≥ 2 flagged days; TRD 09 §4.9) and detail "<Mon D>[, <Mon D> …] · affects <residents joined by \", \" and \" and \">". | Must | BR-06, SRC-18 | 07 ANL | T |
| FR-295 | Each resident (or device) shall appear at most once per data-alert kind, and a resident with `baseline_stalled` shall not also be listed as `high_set_aside`. | Must | BR-06, SRC-18 | 07 ANL | T |
| FR-296 | A pipeline-generated data alert shall keep `first_detected_at` across runs, update `last_detected_at` while its rule holds, and change to status `resolved` on the first run in which the rule no longer holds. | Must | BR-02, SRC-18, R15 | 07 ANL, 06 DB | T |
| FR-297 | A data alert of kind `review_flagged_data_problem` shall remain `open` until an admin resolves it with a command-line action; the pipeline shall not resolve it. | Must | BR-13, R4 | 09 CUS | T |
| FR-298 | Queue 2 "Data alerts · go to the study team" on `/alerts` shall list open data alerts (title and detail) without the ▲ glyph or alarm accent, and without any review form. | Must | BR-12, BR-18, SRC-18, VIS-029 | 11 UX | T |
| FR-299 | `GET /api/v1/data-alerts` shall return data alerts filterable by status and kind to any authenticated user. | Must | BR-12, SRC-18 | 05 API | T |
| FR-300 | Data alerts shall never create a health alarm, change a CUSUM tally or appear in the Alerts nav count. | Must | BR-11, SRC-18 | 09 CUS | T |
| FR-301 | With the reference data at as-of 2026-10-30 15:00 America/Chicago, the open data alerts shall be exactly: "R08 · baseline stuck at 13 of 16" / "12 missed and 5 set aside in 30 days"; "R05 · possible other speaker" / "2 check-ins quarantined: Oct 8, Oct 22"; "R03 · many check-ins set aside" / "7 of 29 received: noise, quality flag, too short"; "D02 · device silent all day" / "Oct 12 · affects R02 and R03". | Must | BR-15, SRC-18 | 14 TDV | T |

### 4.24 Analytics page (BR-12, BR-15) — SRC-19

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-310 | The Analytics page (`/analytics`) and `GET /api/v1/analytics` shall be available only to roles `researcher` and `admin`; a clinician shall receive 403 and the access-denied page "You do not have access to this page." with "Back to all residents" (TRD 04 FE-037, TRD 11 UX-350). | Must | BR-16, SRC-19 | 12 SEC, 04 FE | T |
| FR-311 | The page shall show the header "Analytics" and the subline "For the study team · <DATA_SOURCE_LABEL>, <period> · numbers match the pipeline answer key", where the last clause is shown only in the `test_v0_1` profile. | Must | BR-15, SRC-19 | 11 UX | T |
| FR-312 | The analytics period shall be the last 30 local days ending on the as-of date (reference data: Oct 1–30, 2026). | Must | BR-12, SRC-19, R10 | 05 API | T |
| FR-313 | The page shall show four KPI tiles: "Check-ins received" (percentage and "<received> of <expected> expected", received = non-duplicate records, expected = Σ over active residents of enrolled days in the period); "Used for scoring" (usable / expected); "Baselines formed" ("<n> of <active residents>" with a note naming forming residents and restart counts); "Alarms raised" (count of alarms triggered in the period with a note naming residents and review state). | Must | BR-12, BR-15, SRC-19 | 05 API, 11 UX | T |
| FR-314 | KPI percentages shall be rounded half-up to an integer. | Must | BR-15, SRC-19 | 05 API | T |
| FR-315 | The page shall show "Check-ins per day": one stacked bar per local day with segments Used, Set aside, Quarantined, Missed (legend in that order), duplicates excluded, x labels for the first day, each day with a silent device ("Oct 12 · D02 silent") and the last day. | Must | BR-06, BR-12, SRC-19 | 11 UX | T |
| FR-316 | The page shall show the funnel "Where check-ins are lost": Expected (with "<residents> residents × <days> days"), Received (with "<missed> missed · <n> duplicate copies removed"), Passed quality checks (with "<n> set aside: quality flag <a>, noise <b>, too short <c>" counting each reason occurrence and "(<k> had two reasons)" when k > 0), Same speaker, used (with "<n> quarantined as possible other speaker"). | Must | BR-03, BR-04, BR-05, BR-06, SRC-19 | 05 API, 11 UX | T |
| FR-317 | The page shall show "Usable check-ins by resident": per resident the share of period days with a usable check-in, lowest first, ties by resident code, as a stacked bar of used / set aside + quarantined / missed. | Must | BR-12, SRC-19 | 11 UX | T |
| FR-318 | In the `test_v0_1` profile the page shall show "Alarm timing check · test data only, where the true change date is known" with columns Resident, Planted change, Change began, Alarm rang, Delay (days = alarm local date − true onset date), read from `evaluation_ground_truth` after the run; residents without a planted change shall be grouped into one row "Other <n> · None · — · No alarm · Correct" when none of them alarmed. | Must | BR-11, BR-15, SRC-19, ARC-034 | 05 API, 14 TDV | T |
| FR-319 | In the `production` profile the alarm timing panel shall be replaced by "alarms raised, reviewed, and review outcomes": counts of alarms raised, alarms with ≥ 1 review, and the latest review outcome per alarm counted by outcome. | Must | BR-13, BR-15, SRC-19 | 05 API, 11 UX | T |
| FR-320 | Each chart on the page shall have a text-table alternative. | Must | BR-12, NFR-060 | 11 UX | T |
| FR-321 | The page footer shall read "Counts only — no audio, no resident names." | Must | BR-01, BR-16, SRC-19 | 11 UX | I |
| FR-322 | `GET /api/v1/analytics` shall return `kpis`, `daily_series`, `funnel`, `by_resident` and either `alarm_timing` (`test_v0_1`) or `review_outcomes` (`production`), in addition to the FR-240 content. | Must | BR-15, SRC-19 | 05 API | T |
| FR-323 | With the reference data the page shall show: received 94% "281 of 300 expected"; used 89% "267 of 300 expected"; baselines "9 of 10" "R08 still forming; R07 restarted once"; alarms 2 "R09, R10 · both not yet reviewed"; funnel 300 → 281 → 269 → 267 with "12 set aside: quality flag 5, noise 5, too short 3 (1 had two reasons)"; usable shares R08 43%, R03 73%, R02 80%, R05 93%, others 100%; alarm timing R09 Sudden step Oct 21 / Oct 21 / 0 days, R10 Slow drift Oct 17 / Oct 24 / 7 days, Other 8 None / — / No alarm / Correct. | Must | BR-15, SRC-19 | 14 TDV | T |

### 4.25 Page chrome, navigation and response metadata

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-330 | `/residents`, `/alerts`, `/analytics` and `/admin` shall show the global header and navigation "Residents", "Alerts (<n>)", "Analytics", "New admissions" (plus "Admin" for admins), where n = number of change alarms with status `open` (not yet reviewed); data alerts are not counted. | Must | BR-12, SRC-18, SRC-19, R2 | 04 FE, 11 UX | T |
| FR-331 | `/residents/[residentCode]` and `/admissions` shall start with "← Back to all residents" and shall not show the global navigation. | Must | BR-13, BR-14, SRC-10, SRC-11, R2 | 11 UX | T |
| FR-332 | Every list, detail and analytics response shall include `meta {facility_name, facility_tz, data_source_label, as_of, baseline_n, cusum_h, pipeline_profile}`. | Must | BR-12, BR-15, R3 | 05 API | T |
| FR-333 | `meta.as_of` on read endpoints shall be the `as_of` of the latest succeeded pipeline run. | Must | BR-06, BR-15, R21 | 05 API | T |

### 4.26 Role permission matrix

| Capability | admin | clinician | researcher | API key `ingest:write` | API key `pipeline:run` |
|---|---|---|---|---|---|
| View overview, devices, resident detail, check-in log, notes, Alert review page (alarms, data alerts, review history), admissions | Yes | Yes | Yes (read-only) | No | No |
| Save alarm review, snooze alarm (Alert review page or "Mark as reviewed") | Yes | Yes | No | No | No |
| Add staff note | Yes | Yes | No | No | No |
| Analytics page and `/analytics*` endpoints | Yes | No | Yes | No | No |
| CSV export of baselines and scores | Yes | No | Yes | No | No |
| `GET /scores` JSON for Resident detail charts | Yes | Yes | Yes | No | No |
| View pipeline runs (list and detail), ingest batch results | Yes | No | Yes | No | No |
| Trigger pipeline run | Yes | No | No | No | Yes |
| Upload CSV / batch ingest | Yes | No | No | Yes | No |
| Single record ingest (`POST /sessions`) | No | No | No | Yes | No |
| Manage users | Yes | No | No | No | No |
| API keys, residents, devices, assignments | CLI only (no endpoints) | No | No | No | No |

Note: `GET /api/v1/scores` is authorised for any user (contract §10) because the Resident detail chart uses it; FR-243 and FR-310 restrict the `/analytics*` endpoints and page; CSV export (FR-244) is researcher/admin only.

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

#### UC-04 Review residents overview

| Field | Content |
|---|---|
| Actor | Clinician (primary); researcher; admin |
| Inputs | Sort choice |
| Processing | `GET /api/v1/residents?sort=…` → render tiles, rows, devices panel |
| Outputs | Tiles, sorted rows with status and 30-day counts, devices panel |
| Errors | Expired token → `/login`; API unavailable → error banner with retry, no stale numbers shown as current |
| Related FRs | FR-130–FR-140, FR-150–FR-156, FR-211 |

#### UC-05 Review resident detail

| Field | Content |
|---|---|
| Actor | Clinician; researcher; admin |
| Inputs | Resident code (from "Open") |
| Processing | `GET /residents/{code}`, `/features`, `/checkins`, `/notes`, `/scores?resident_code=` → render header, What this means, tally chart, 7 measurements, staff review, check-in log |
| Outputs | Detail page per SRC-10 |
| Errors | Unknown code → 404 page; resident with baseline forming → chart shows "Baseline forming · n of N sessions" and no scored bars |
| Related FRs | FR-160–FR-173, FR-180–FR-184, FR-193 |

#### UC-06 Record staff note

| Field | Content |
|---|---|
| Actor | Clinician or admin |
| Preconditions | Resident detail open |
| Inputs | Note type (`observation`, `action_taken`, `follow_up`), body (≤ 2000 chars) |
| Processing | `POST /residents/{code}/notes` → insert note → audit (note created). "Mark as reviewed" on the same page opens the review form of UC-13 instead (R5). |
| Outputs | Note listed; alert status unchanged by notes |
| Errors | Empty or > 2000 chars → 422; researcher → 403 |
| Related FRs | FR-190–FR-195, FR-250 |

#### UC-07 View new admissions (experimental)

| Field | Content |
|---|---|
| Actor | Clinician; researcher; admin |
| Processing | `GET /api/v1/admissions`; select resident → `GET /api/v1/admissions/{code}/comparison`; `GET /api/v1/facility/reference-ranges` |
| Outputs | Experimental banner; list with comparison status; dot-vs-band chart |
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
| Processing | `POST /auth/login` → token → `GET /auth/me` → role-aware navigation; logout discards token |
| Errors | Wrong credentials → 401 generic message; inactive → 401; 6th attempt within a minute → 429 |
| Related FRs | FR-210–FR-218 |

#### UC-10 Review device health

| Field | Content |
|---|---|
| Actor | Clinician; admin |
| Processing | Header nav "Devices" → `#devices` panel from `GET /api/v1/devices` |
| Outputs | Shared devices, replacements, last upload, firmware, silent days and device-gap days |
| Related FRs | FR-150–FR-156 |

#### UC-11 Validate pipeline against the answer key

| Field | Content |
|---|---|
| Actor | Researcher or CI |
| Processing | Load SRC-05 (UC-02 or test harness) with profile `test_v0_1` → full run → `GET /analytics`, `/analytics/baselines`, `/scores` (or direct table reads in tests) → compare with SRC-03 |
| Outputs | Pass/fail per sheet; 100% match required |
| Related FRs | FR-031, FR-137, FR-240–FR-244 |

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
| Trigger | "Alerts (n)" in the navigation shows n > 0, or "Mark as reviewed" on Resident detail |
| Preconditions | Logged in; at least one open alarm |
| Inputs | Selected alarm; explanations (0..5 codes from `review_explanations`); outcome (required); note (optional, ≤ 2000 chars); or "Remind me in 24 h" |
| Processing | `GET /api/v1/alerts?status=open` and `GET /api/v1/alerts?status=acknowledged` (E-13 takes one status value per call) and `GET /api/v1/data-alerts?status=open` → render queues → select card → mini tally chart (`GET /scores`), "Leaning most", review history (`GET /alerts/{id}/reviews`) → "Save review" → `POST /alerts/{id}/reviews` → `alert_reviews` row, alert `acknowledged`, data alert for outcome `data_problem` → audit; or "Remind me in 24 h" → `POST /alerts/{id}/snooze` → audit |
| Outputs | Card shows "Reviewed" (or snoozed without emphasis); review history updated; alarm stays on and tally unchanged (OQ-05) |
| Errors / alternatives | Missing outcome or bad code → 422; researcher → 403 (read-only view); alert closed meanwhile (epoch ended) → 409 and the queue refreshes; no open alarms → "No change alarms right now." (FR-280) |
| Related FRs | FR-106, FR-107, FR-191, FR-260–FR-280, FR-330 |

#### UC-14 View study analytics

| Field | Content |
|---|---|
| Actor | Researcher (study team) or admin |
| Preconditions | Logged in with role `researcher` or `admin`; at least one succeeded pipeline run |
| Inputs | None (period = last 30 local days ending at `meta.as_of`) |
| Processing | `GET /api/v1/analytics` → KPI tiles, check-ins per day, loss funnel, usable check-ins by resident, and alarm timing check (`test_v0_1`, from `evaluation_ground_truth`) or review outcomes (`production`) |
| Outputs | Analytics page per SRC-19 with text-table alternatives; for reference data the values of FR-323 |
| Errors / alternatives | Clinician → 403 access-denied page "You do not have access to this page." (FR-310); no succeeded run → empty state "No pipeline run yet" |
| Related FRs | FR-240–FR-245, FR-310–FR-323, FR-330, FR-332, FR-333 |

#### UC-15 Triage data alerts

| Field | Content |
|---|---|
| Actor | Pipeline (generation); researcher or admin (reading) |
| Processing | Each pipeline run evaluates the data-alert rules over the last 30 days → upserts `data_alerts` (open / resolved) → Queue 2 on `/alerts` lists open data alerts |
| Outputs | Study team sees data-quality issues separate from health alarms |
| Errors / alternatives | Rule disabled in configuration → no alert of that kind; `review_flagged_data_problem` stays open until an admin resolves it by CLI |
| Related FRs | FR-290–FR-301 |

### 4.28 Traceability: BR → FR

| BR | FRs |
|---|---|
| BR-01 | FR-001–FR-005, FR-007, FR-009, FR-011–FR-013, FR-015, FR-020–FR-025, FR-027, FR-028, FR-032, FR-139, FR-184, FR-207, FR-222, FR-226, FR-278, FR-321 |
| BR-02 | FR-005, FR-006, FR-007, FR-010, FR-028, FR-032, FR-223, FR-296 |
| BR-03 | FR-008, FR-011, FR-029–FR-031, FR-139, FR-182, FR-316 |
| BR-04 | FR-024, FR-040–FR-044, FR-181, FR-290, FR-293, FR-316 |
| BR-05 | FR-060–FR-065, FR-074, FR-181, FR-290, FR-292, FR-316 |
| BR-06 | FR-120–FR-125, FR-135, FR-153, FR-154, FR-181, FR-290, FR-291, FR-294, FR-295, FR-315, FR-316, FR-333 |
| BR-07 | FR-070–FR-074, FR-171 |
| BR-08 | FR-050–FR-053, FR-132, FR-155, FR-172, FR-181 |
| BR-09 | FR-052, FR-080–FR-086, FR-162, FR-163, FR-205, FR-229, FR-230, FR-291 |
| BR-10 | FR-082, FR-090–FR-095, FR-169, FR-170, FR-266 |
| BR-11 | FR-053, FR-100–FR-110, FR-165–FR-167, FR-181, FR-206, FR-229, FR-261–FR-263, FR-265, FR-276, FR-300, FR-318 |
| BR-12 | FR-130–FR-140, FR-150–FR-156, FR-227, FR-298, FR-299, FR-312, FR-313, FR-315, FR-317, FR-320, FR-330, FR-332 |
| BR-13 | FR-106, FR-108, FR-160–FR-173, FR-180–FR-184, FR-190–FR-195, FR-260–FR-274, FR-277, FR-280, FR-297, FR-319, FR-331 |
| BR-14 | FR-200–FR-207, FR-331 |
| BR-15 | FR-002, FR-003, FR-031, FR-137, FR-222–FR-225, FR-240–FR-244, FR-263, FR-301, FR-311, FR-313, FR-314, FR-318, FR-319, FR-322, FR-323, FR-332, FR-333 |
| BR-16 | FR-004, FR-013–FR-015, FR-026, FR-168, FR-192, FR-194, FR-210–FR-221, FR-226–FR-229, FR-243, FR-245, FR-250–FR-252, FR-254, FR-275, FR-279, FR-310, FR-321 |
| BR-17 | FR-253, FR-254 |
| BR-18 | FR-164, FR-277, FR-278, FR-298 (and constraints VIS-003..005, VIS-029, TRD 00) |

### 4.29 Traceability: UC → FR coverage check

Every FR in sections 4.2–4.25 is exercised by at least one use case: ingestion/validation/analytics FRs (FR-001–FR-125) by UC-01, UC-02, UC-03, UC-11; overview and devices (FR-130–FR-156) by UC-04, UC-10; detail, log and review (FR-160–FR-195) by UC-05, UC-06; admissions (FR-200–FR-207) by UC-07; auth (FR-210–FR-218) by UC-09; admin (FR-220–FR-230) by UC-02, UC-03, UC-08; analytics (FR-240–FR-245) by UC-11, UC-12; audit/health (FR-250–FR-254) by all use cases; legacy file rejection (FR-032) by UC-02; alert review (FR-260–FR-280) by UC-13; data alerts (FR-290–FR-301) by UC-03, UC-15; Analytics page (FR-310–FR-323) by UC-14; page chrome and metadata (FR-330–FR-333) by UC-04, UC-13, UC-14.

## 5. Assumptions

- ASM-01 (America/Chicago), ASM-02 (≤ 1 session per resident per local day), ASM-03 (single facility), ASM-04 (16 test / 30 production; D-OWNER-2), ASM-05 (HTTPS POST or CSV), ASM-06 (new epoch closes open alert), ASM-07 (frozen baselines never recomputed), ASM-08 (small scale).
- Decided by the lead (contract §20–§21) and applied here: watching since (R9), last check-in and 30-day window (R10), as-of precedence (R21), logout, pipeline runs list, CSV export and CLI-only master data (R4), single review model (R5), chart bars (R1), page chrome (R2), meta block (R3), legacy file rejection (R12), `pending` status (R23).
- Notes for lead (TRD-local definitions introduced here): "Open alarm" = status open or acknowledged; "Silent day (device)" and "Device-gap day" (section 4.1); comparison status "Facility range not available yet" (FR-202); strict rejection of unknown fields (FR-013); ledger stops at `withdrawn_on` (FR-120); alarm queue order and default selection (FR-261, FR-264); "Leaning most" window, tie-break and empty text (FR-266); review history display (FR-272); `review_flagged_data_problem` resolved only by admin CLI (FR-297); alert-queue empty state (FR-280); production review-outcome counting uses the latest review per alarm (FR-319); Analytics nav hidden from clinicians (FR-218).

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
| AC-FR-04 | The overview API and page show tiles 2 / 7 / 1 / 19 and default order R09, R10, R08, R07, R03, R02, R05, R01, R04, R06 at as-of 2026-10-30 15:00 America/Chicago (R16). |
| AC-FR-05 | Posting R04's day-5 record a second time returns 200 with `duplicate`, and the R04 results are unchanged. |
| AC-FR-06 | A record with `audio_quality_flag = "bad"` returns 422 with an error naming `audio_quality_flag`, appears in `ingest_rejections`, and does not appear in `raw_sessions`. |
| AC-FR-07 | A clinician saves a review for R09 (outcome `known_cause`, explanation `cold_cough_sore_throat`): an `alert_reviews` row is created, the alert becomes `acknowledged` and its card shows "Reviewed", the badge still reads "▲ Alarm since Oct 21", and the tally is unchanged; `POST /alerts/{id}/acknowledge` returns 404. |
| AC-FR-08 | A researcher receives 403 on `POST /residents/R09/notes`, `POST /alerts/{id}/reviews` and `POST /pipeline/run`, and 200 on `GET /analytics`; a clinician receives 403 on `GET /analytics` and 200 on `POST /alerts/{id}/reviews`. |
| AC-FR-09 | The R09 detail page shows the tally chart with a grey slot "Baseline Oct 1–16", grey (outlined) bars Oct 17–20, accent bars from Oct 21 to Oct 30, the "alarm line 5.0", an "Oct 21 · alarm" label, and the check-in log entries "Oct 21 · Alarm on · tally crossed 5.0", "Oct 17 · Watching started", "Oct 16 · Baseline complete (16 of 16)". |
| AC-FR-10 | The New admissions page shows the experimental banner and, with no reference ranges loaded, the status "Facility range not available yet" or "Not enough check-ins yet" for every listed resident. |
| AC-FR-11 | Every FR in this document appears in the BR → FR table and in at least one use case. |
| AC-FR-12 | `/alerts` with the reference data shows the two alarm cards of FR-263 and exactly the four data alerts of FR-301; snoozing R10 removes its "Not reviewed" emphasis for 24 h and leaves its alarm on. |
| AC-FR-13 | `/analytics` with the reference data shows every value listed in FR-323. |
| AC-FR-14 | Uploading the legacy SRC-06 file returns 422 "schema mismatch" and creates no `raw_sessions` row. |

## 8. Implementation Notes

- Implement FRs in the batch order of TRD 25; the analytics FRs (4.3–4.11) must pass UC-11 before the UI batches start.
- Keep display strings (status labels, captions, "What this means") in one frontend copy module and backend configuration; tests compare exact strings.
- Use `resident_code` (e.g. R01) in URLs and API paths, never UUIDs.
- The overview counts come from `processed_sessions` and `day_ledger` for the last-30-days window; do not recompute statistics in the frontend.
- `status_after_processing` for a set-aside record is `set_aside` even though the record is stored in `raw_sessions`; the 201 code means "stored", not "usable".
- Data-alert text and Analytics numbers are exact-string tested against FR-301 and FR-323; build them from the same 30-day window helper as the overview.
- The alarm timing panel reads `evaluation_ground_truth` through the read-only role (`echowell_readonly`), never through the app role, which has no SELECT on that table (R20).

## 9. Open Questions

| ID | Affects |
|---|---|
| OQ-03 | FR-012, FR-171 (placeholder feature names) |
| OQ-04 | FR-021 (`phrase_id` kept while open) |
| OQ-05 | FR-107, FR-195, FR-277 |
| OQ-06 | FR-109, FR-276 |
| OQ-08 | FR-202, FR-204, FR-205 |
| OQ-09 | FR-073 |
| OQ-10 | FR-084 |
| OQ-11 | FR-026, FR-228 |
| OQ-12 | FR-164 |
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
