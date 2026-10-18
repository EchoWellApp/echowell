# 02 Functional Requirements Specification

Document ID: ECHOWELL-TRD-02 · Version 0.1 (draft for review) · Date: 18 October 2026 · Owner: Team 2 · Status: Draft

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
| As-of time | Production: the request time for read endpoints and the run start time for pipeline runs. Tests: set by `POST /api/v1/pipeline/run {as_of}` or a frozen clock; for the reference data 2026-10-30 15:00 America/Chicago (R11). Reported in `meta.as_of`. |
| Last 30 days | The 30 local calendar days ending on the as-of local date, inclusive, excluding days before the resident's enrolment date (for the test data: 1–30 Oct 2026) (R10). |
| Last check-in | The local timestamp of the resident's latest non-duplicate record of any status (usable, set aside or quarantined) (R10). |
| Open alarm | An `alerts` row of the current epoch with status `open` or `acknowledged`; the alarm stays on after review (OQ-05). |
| Current epoch | The resident's highest-numbered epoch. |
| Watching since | The local date of the first scored session in the current epoch (R09: Oct 17); before any scored session exists, the local date after the freeze session's local date (R9). |
| Alarm since | The `local_date` of the open alert of the current epoch. |
| Silent device-day | A local day on which a device assigned to 2 or more residents received no record from any of them (the `missing_device_gap` condition). |
| No-upload day | A local day on which a device received no non-duplicate record from any assigned resident (applies to all devices, shared or not). |

### 4.2 Ingestion (BR-01, BR-02)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-001 | The system shall accept one feature record per request at `POST /api/v1/sessions` from a caller presenting an `X-API-Key` with scope `ingest:write`. | Must | BR-01, SRC-13 §6, ASM-05 | 10 ING, 05 API | T |
| FR-002 | The system shall accept a batch of records at `POST /api/v1/ingest` as JSON `{"records": [...]}`. | Must | BR-01, BR-15 | 10 ING, 05 API | T |
| FR-003 | The system shall accept a multipart CSV upload at `POST /api/v1/ingest` whose header equals the SRC-05 header (schema v0.1 field order). | Must | BR-01, BR-15, SRC-05 | 10 ING | T |
| FR-004 | The batch endpoint shall accept callers holding an API key with scope `ingest:write` or a user session with role `admin`. | Must | BR-01, BR-16 | 05 API, 12 SEC | T |
| FR-005 | The system shall store every schema-valid arrival, including repeat `session_id`s, as one new row in `raw_sessions` with `arrival_seq`, `received_at`, `ingest_batch_id` and the payload exactly as received. | Must | BR-02, SRC-02 diagram 1 | 10 ING, 06 DB | T |
| FR-006 | The system shall never modify or delete a `raw_sessions` row. | Must | BR-02, SRC-02 | 06 DB, 20 PGS | T |
| FR-007 | For the first arrival of a `session_id`, `POST /api/v1/sessions` shall return 201 with `raw_session_id`, `arrival_seq` and `status_after_processing` (`usable`, `set_aside`, `quarantined`). | Must | BR-01 | 05 API | T |
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
| FR-027 | A rejected record shall receive HTTP 422 with an RFC 7807-style body listing every failed field and rule. | Must | BR-01 | 05 API, 10 ING | T |
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
| FR-110 | An alert shall move to status `closed` only through epoch end (reason "epoch ended") or an admin command-line action with a recorded reason. | Must | BR-11, ASM-06, R4 | 09 CUS | T |

### 4.11 Day ledger and missing days (BR-06)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-120 | The pipeline shall produce one `day_ledger` row per resident per local calendar day from the resident's enrolment date to the as-of local date, or to `withdrawn_on` if earlier. | Must | BR-06, SRC-03 Annotated_sessions | 07 ANL | T |
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
| FR-134 | Each row shall show Resident, Device (with "(shared)" when the device is currently assigned to ≥ 2 residents, or "(was <old>)" after a device change in the current epoch), Status, Last check-in (latest non-duplicate record of any status, local, e.g. "Oct 30, 2:28 PM") and an "Open" link. | Must | BR-12, SRC-09, R10 | 04 FE, 11 UX | T |
| FR-135 | Each row shall show "Last 30 days: used · set aside · quarantined · missed", where missed = missing_resident + missing_device_gap days and duplicates are never counted. | Must | BR-06, BR-12, SRC-09, SRC-12 | 11 UX | T |
| FR-136 | The overview shall show four summary tiles: "Alarm on" (count), "Being watched, no alarm" (count), "Baseline still forming" (count), "Missed check-ins, last 30 days" (sum of missed over listed residents). | Must | BR-12, SRC-09 | 11 UX | T |
| FR-137 | For the SRC-05 data at as-of 2026-10-30 15:00 America/Chicago with profile `test_v0_1`, the tiles shall read 2, 7, 1, 19 and the rows shall show the counts of SRC-03 Exp_status_counts. | Must | BR-12, BR-15, SRC-09 | 14 TDV | T |
| FR-138 | The header subline shall read "Voice check-ins · <FACILITY_NAME> · Showing <DATA_SOURCE_LABEL> as of <Mon D, YYYY, h:mm AM/PM TZ>". | Must | BR-12, SRC-09 | 11 UX | T |
| FR-139 | The overview footer shall read "No audio is stored or played here — only extracted voice measurements. Duplicate records are removed quietly and not shown." | Must | BR-01, BR-03, SRC-09 | 11 UX | I |
| FR-140 | Selecting "Open" on a row shall navigate to `/residents/<resident_code>`. | Must | BR-12, BR-13 | 04 FE | T |

### 4.13 Devices panel (BR-12, BR-06)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-150 | The overview shall include a Devices panel (anchor `#devices`, header nav "Devices") listing every active device with its currently assigned residents. | Must | BR-12, SRC-09, SRC-12 | 11 UX | T |
| FR-151 | A device assigned to ≥ 2 residents shall be shown as "<device> · shared by <residents>" (e.g. "D02 · shared by R02, R03"). | Must | BR-12, SRC-09 | 11 UX | T |
| FR-152 | For each device the panel shall show the last upload time (local) and firmware version. | Must | BR-12, SRC-09 | 11 UX | T |
| FR-153 | For each shared device the panel shall list silent device-days in the last 30 days (e.g. "silent all day Oct 12"). | Must | BR-06, BR-12, SRC-09, SRC-12 | 11 UX | T |
| FR-154 | For each device the API shall report the number of no-upload days in the last 30 days. | Should | BR-06, BR-12, SRC-12 ("days with no device activity") | 05 API, 11 UX | T |
| FR-155 | A device that replaced another for a resident shall be shown with "In use since <Mon D> (replaced <old>)" (e.g. D07B replaced D07 on Oct 13). | Must | BR-08, BR-12, SRC-09 | 11 UX | T |
| FR-156 | Devices with no silent day, no replacement and an upload on the as-of date may be grouped into one line ("D01, D04–D06, D08–D10 · All uploaded on Oct 30 · firmware fw-1.0.0"). | May | BR-12, SRC-09 | 11 UX | D |

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
| FR-168 | The tally chart shall have an equivalent text table (date, composite z, tally, alarm state) available to assistive technology and by a visible toggle. | Must | BR-13, BR-16 (accessibility, TRD 03) | 11 UX | T |
| FR-169 | The page shall show "The 7 measurements behind the score" with one card per composite feature, showing the plain-language label of TRD 08 (e.g. "Quieter (loudness)", "More pauses (number of pauses)") and a sparkline of recent adjusted values. | Must | BR-10, BR-13, SRC-10, SRC-12 | 11 UX | T |
| FR-170 | The page shall show an eighth card "12 other measurements (pitch, jitter, MFCCs …) — stored, not scored" without values in the scoring summary. | Must | BR-10, BR-13, SRC-10, SRC-12 | 11 UX | I |
| FR-171 | The measurements section shall carry the caption "Column names are placeholders until Team 1 confirms extractor output names. Morning check-ins are adjusted before comparing." | Must | BR-07, OQ-03, SRC-10 | 11 UX | I |
| FR-172 | A user shall be able to view an earlier epoch's tally and baseline for a resident with more than one epoch. | Should | BR-08, BR-13 | 04 FE, 05 API | T |
| FR-173 | Requesting an unknown resident code shall show a "Resident not found" page and the API shall return 404. | Must | BR-13 | 05 API, 04 FE | T |

### 4.15 Check-in log (BR-13, BR-06)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-180 | The Resident detail page shall show a "Check-in log" listing events newest first, each as "<Mon D> · <event> · <detail>" (e.g. "Oct 21 · Alarm on · tally crossed 5.0"). | Must | BR-13, SRC-10 | 11 UX | T |
| FR-181 | The log shall include event types: alarm on, watching started, baseline complete ("Baseline complete (n of N)"), set aside (with reasons), quarantined ("possible other speaker"), missed (missing_resident), device silent (missing_device_gap), baseline restarted (new device/firmware/software). | Must | BR-04, BR-05, BR-06, BR-08, BR-11, BR-13, SRC-10, SRC-12 | 05 API, 11 UX | T |
| FR-182 | The log shall never contain duplicate records. | Must | BR-03, SRC-09 footer | 05 API | T |
| FR-183 | The check-in log API shall support filtering by `from` and `to` local dates. | Should | BR-13 | 05 API | T |
| FR-184 | A newly ingested record shall appear in the resident's check-in log and "Last check-in" after the ingest response returns, without manual pipeline action. | Must | BR-01, BR-13, SRC-15 demo step 5 | 01 ARC, 05 API | T, D |

### 4.16 Staff review (BR-13)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-190 | A user with role `clinician` or `admin` shall be able to add a staff note to a resident with a type (`observation`, `action_taken`, `follow_up`) and a body of 1 to 2000 characters. | Must | BR-13, SRC-10, SRC-12 | 05 API, 11 UX | T |
| FR-191 | The "Mark as reviewed" button on Resident detail shall open the alarm review form of FR-266–FR-270 for the resident's open alarm (single review model) and shall be disabled when the resident has no open alarm; staff notes themselves shall not change alert status. | Must | BR-13, SRC-10 ("Mark as reviewed"), SRC-18, R5 | 11 UX, 09 CUS | T |
| FR-192 | Staff notes shall be append-only; an edit shall create a new note row referencing the superseded note via `supersedes_id`. | Must | BR-13, BR-16 | 06 DB | T |
| FR-193 | The Staff review section shall list the resident's notes newest first with type, author display name and local timestamp, showing only the latest version of edited notes. | Must | BR-13 | 11 UX | T |
| FR-194 | Users with role `researcher` shall see notes and reviews read-only and shall not see the note form, the review form, "Mark as reviewed" or "Remind me in 24 h". | Must | BR-13, BR-16, OQ-26 | 12 SEC, 11 UX | T |
| FR-195 | The Staff review section shall display the note "Does review reset the tally? — open question OQ-05" until OQ-05 is closed. | Must | BR-13, OQ-05, SRC-10 | 11 UX | I |

### 4.17 New admissions — future / experimental (BR-14)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-200 | The New admissions page (`/admissions`) shall show the banner "Future / experimental study arm" and the note that the arm is not in pipeline test v0.1. | Must | BR-14, SRC-11, SRC-12 | 11 UX | T |
| FR-201 | The page shall list residents of cohort `new_admission` whose own baseline has not yet formed, with Study ID, admitted date, check-ins so far, comparison status and own-baseline progress "n of N". | Must | BR-14, SRC-11 | 05 API, 11 UX | T |
| FR-202 | The comparison status shall be one of "▲ Outside facility range", "Within facility range", "Not enough check-ins yet", or "Facility range not available yet" when no facility reference range exists (OQ-08). | Must | BR-14, SRC-11, OQ-08 | 11 UX | T |
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
| FR-223 | An admin shall be able to trigger a pipeline run with scope (`all` or a list of resident codes) and profile, receiving a `pipeline_run_id`. | Must | BR-02, BR-15 | 05 API | T |
| FR-224 | Admins and researchers shall be able to view a pipeline run's trigger, scope, profile, status, start/finish times, counts and warnings. | Must | BR-15 | 05 API | T |
| FR-225 | `GET /api/v1/pipeline/runs` (admin, researcher; paginated, newest first) shall list pipeline runs, and the Admin page shall show the most recent 50. | Must | BR-15, R4 | 05 API, 04 FE | T |
| FR-226 | Device API keys shall be created and revoked by an admin through `python -m backend.cli` commands; the plaintext key shall be shown once and only its SHA-256 hash stored; no HTTP endpoint shall exist for API keys. | Must | BR-01, BR-16, R4 | 12 SEC | T |
| FR-227 | Residents, devices, device assignments and the facility shall be managed through version-controlled seed files and `python -m backend.cli` commands, with no HTTP endpoints; no PII field shall exist for them. | Must | BR-12, BR-16, ASM-03, R4 | 06 DB, 15 DEP | T |
| FR-228 | Setting a resident's status to `withdrawn` with `withdrawn_on` shall stop ingestion for that resident (FR-026) and hide the resident from default lists. | Must | BR-16, OQ-11 | 06 DB, 10 ING | T |
| FR-229 | Pipeline parameters shall be stored in `config_parameters` per profile and changes shall be audited. | Must | BR-09, BR-11, BR-16 | 07 ANL, 12 SEC | T |
| FR-230 | The `test_v0_1` profile shall not be selectable in production (`APP_ENV=production`). | Must | BR-09, D-OWNER-2 | 21 ENV | T |

### 4.20 Researcher analytics and export (BR-15)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-240 | `GET /api/v1/analytics` shall return per-resident status counts in the shape of SRC-03 Exp_status_counts and per-resident outcomes in the shape of Exp_resident_outcomes, plus the latest pipeline run information. | Must | BR-15, SRC-03 | 05 API | T |
| FR-241 | `GET /api/v1/analytics/baselines` shall return baselines in the shape of SRC-03 Exp_baselines (resident, epoch, feature, n, median, MAD, spread, floor_applied). | Must | BR-15, SRC-03 | 05 API | T |
| FR-242 | `GET /api/v1/scores` shall return scored sessions in the shape of SRC-03 Exp_scores, filterable by resident, epoch and date range. | Must | BR-15, SRC-03 | 05 API | T |
| FR-243 | The analytics endpoints shall be available only to roles `researcher` and `admin`. | Must | BR-16 | 12 SEC | T |
| FR-244 | `GET /api/v1/analytics/baselines` and `GET /api/v1/scores` shall return CSV when requested with `Accept: text/csv` by a researcher or admin, using the column names of the corresponding SRC-03 sheet. | Must | BR-15, SRC-14 B.2 (offline mixed-effects analysis), R4 | 05 API | T |
| FR-245 | Exports shall contain study IDs only and no free-text staff notes. | Must | BR-16 | 05 API, 12 SEC | T |

### 4.21 Audit and health (BR-16, BR-17)

| ID | Requirement | Priority | Trace | Detail | Verif. |
|---|---|---|---|---|---|
| FR-250 | The system shall write an `audit_logs` entry for login, logout, failed login, ingest batch, note created, alert acknowledged, pipeline run, config change and user change. | Must | BR-16 | 12 SEC, 17 LOG | T |
| FR-251 | Each audit entry shall record time, actor type and id, action, entity type and id, details, IP and request ID, and shall contain no feature values or passwords. | Must | BR-16 | 12 SEC | T |
| FR-252 | Audit entries shall be append-only for the application database role. | Must | BR-16 | 20 PGS | T |
| FR-253 | `GET /api/v1/health` shall return `{status, database, version, time}` without authentication. | Must | BR-17 | 05 API | T |
| FR-254 | Every response shall carry an `X-Request-ID` header. | Must | BR-16, BR-17 | 17 LOG | T |

### 4.22 Role permission matrix

| Capability | admin | clinician | researcher | API key (ingest:write) |
|---|---|---|---|---|
| View overview, devices, resident detail, check-in log, notes, alerts, admissions | Yes | Yes | Yes | No |
| Add staff note / mark reviewed / acknowledge alert | Yes | Yes | No | No |
| Analytics, baselines, scores export | Yes | No (scores for charts via resident detail only) | Yes | No |
| View pipeline runs, ingest batch results | Yes | No | Yes | No |
| Trigger pipeline run | Yes | No | No | No |
| Upload CSV / batch ingest | Yes | No | No | Yes |
| Single record ingest (`POST /sessions`) | No | No | No | Yes |
| Manage users | Yes | No | No | No |

Note: `GET /api/v1/scores` is authorised for any user (contract §10) because the Resident detail chart uses it; FR-243 restricts the `/analytics*` endpoints.

### 4.23 Use cases

#### UC-01 Ingest one check-in record

| Field | Content |
|---|---|
| Actor | Team 1 device (API key `ingest:write`) |
| Trigger | Resident says the wake word and phrase; device has extracted features |
| Preconditions | Resident enrolled and active; device registered; API key active |
| Inputs | JSON record, schema v0.1 (TRD 10) |
| Processing | Authenticate key → rate-limit → validate schema/resident/device → insert `raw_sessions` → run pipeline for resident and device co-residents → audit |
| Outputs | 201 `{raw_session_id, arrival_seq, status_after_processing}`; derived tables updated; check-in visible on dashboard |
| Errors / alternatives | 401 bad key; 422 invalid (logged in `ingest_rejections`); 422 "resident withdrawn"; 200 `duplicate` for a repeat session_id; 429 rate limit; pipeline failure → record kept, run `failed`, next run processes it |
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
| Actor | Scheduler (nightly 02:00 FACILITY_TZ); Admin (manual) |
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

#### UC-06 Record staff note and mark reviewed

| Field | Content |
|---|---|
| Actor | Clinician or admin |
| Preconditions | Resident detail open |
| Inputs | Note type, body (≤ 2000 chars), optional "Mark as reviewed" |
| Processing | `POST /residents/{code}/notes` → insert note → if mark_reviewed and open alert: acknowledge alert → audit (note created, alert acknowledged) |
| Outputs | Note listed; alert status `acknowledged`; alarm badge and tally unchanged (OQ-05) |
| Errors | Empty or > 2000 chars → 422; researcher → 403 |
| Related FRs | FR-106, FR-107, FR-190–FR-195, FR-250 |

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
| Outputs | Shared devices, replacements, last upload, firmware, silent device-days |
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

### 4.24 Traceability: BR → FR

| BR | FRs |
|---|---|
| BR-01 | FR-001–FR-005, FR-007, FR-009, FR-011–FR-013, FR-015, FR-020–FR-025, FR-027, FR-028, FR-139, FR-184, FR-207, FR-222, FR-226 |
| BR-02 | FR-005, FR-006, FR-010, FR-028, FR-223 |
| BR-03 | FR-008, FR-011, FR-029–FR-031, FR-139, FR-182 |
| BR-04 | FR-024, FR-040–FR-044, FR-181 |
| BR-05 | FR-060–FR-065, FR-074, FR-181 |
| BR-06 | FR-120–FR-125, FR-135, FR-153, FR-154, FR-181 |
| BR-07 | FR-070–FR-074, FR-171 |
| BR-08 | FR-050–FR-053, FR-132, FR-155, FR-172, FR-181 |
| BR-09 | FR-052, FR-080–FR-086, FR-162, FR-163, FR-205, FR-229, FR-230 |
| BR-10 | FR-082, FR-090–FR-095, FR-169, FR-170 |
| BR-11 | FR-053, FR-100–FR-110, FR-165–FR-167, FR-181, FR-206, FR-229 |
| BR-12 | FR-130–FR-140, FR-150–FR-156, FR-227 |
| BR-13 | FR-106, FR-108, FR-160–FR-173, FR-180–FR-184, FR-190–FR-195 |
| BR-14 | FR-200–FR-207 |
| BR-15 | FR-002, FR-003, FR-031, FR-137, FR-222–FR-225, FR-240–FR-244 |
| BR-16 | FR-004, FR-013–FR-015, FR-026, FR-168, FR-192, FR-194, FR-210–FR-221, FR-226–FR-229, FR-243, FR-245, FR-250–FR-252, FR-254 |
| BR-17 | FR-253, FR-254 |
| BR-18 | FR-164 (and constraints VIS-003..005, TRD 00) |

### 4.25 Traceability: UC → FR coverage check

Every FR in sections 4.2–4.21 is exercised by at least one use case: ingestion/validation/analytics FRs (FR-001–FR-125) by UC-01, UC-02, UC-03, UC-11; overview and devices (FR-130–FR-156) by UC-04, UC-10; detail, log and review (FR-160–FR-195) by UC-05, UC-06; admissions (FR-200–FR-207) by UC-07; auth (FR-210–FR-218) by UC-09; admin (FR-220–FR-230) by UC-02, UC-03, UC-08; analytics (FR-240–FR-245) by UC-11, UC-12; audit/health (FR-250–FR-254) by all use cases.

## 5. Assumptions

- ASM-01 (America/Chicago), ASM-02 (≤ 1 session per resident per local day), ASM-03 (single facility), ASM-04 (16 test / 30 production; D-OWNER-2), ASM-05 (HTTPS POST or CSV), ASM-06 (new epoch closes open alert), ASM-07 (frozen baselines never recomputed), ASM-08 (small scale).
- Notes for lead (TRD-local definitions introduced here): "Watching since" = day after the freeze session's local date; "Silent device-day" and "No-upload day" (section 4.1); comparison status "Facility range not available yet" (FR-202); strict rejection of unknown fields (FR-013); API keys and resident/device master data managed via CLI and seed files (FR-226, FR-227) because the contract API has no endpoints for them; pipeline run list (FR-225) needs a list endpoint `GET /api/v1/pipeline/runs`; CSV export via `Accept: text/csv` (FR-244); ledger stops at `withdrawn_on` (FR-120).

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
| AC-FR-04 | The overview API and page show tiles 2 / 7 / 1 / 19 and default order beginning R09, R10, R08, R07 at as-of 2026-10-30 15:00 America/Chicago. |
| AC-FR-05 | Posting R04's day-5 record a second time returns 200 with `duplicate`, and the R04 results are unchanged. |
| AC-FR-06 | A record with `audio_quality_flag = "bad"` returns 422 with an error naming `audio_quality_flag`, appears in `ingest_rejections`, and does not appear in `raw_sessions`. |
| AC-FR-07 | A clinician adds a note with "Mark as reviewed" for R09: the alert becomes `acknowledged`, the badge still reads "▲ Alarm since Oct 21", and the tally is unchanged. |
| AC-FR-08 | A researcher receives 403 on `POST /residents/R09/notes` and `POST /pipeline/run`, and 200 on `GET /analytics`. |
| AC-FR-09 | The R09 detail page shows the tally chart with grey baseline bars to Oct 16, accent bars from Oct 17, the "alarm line 5.0", an "Oct 21 · alarm" label, and the check-in log entries "Oct 21 · Alarm on · tally crossed 5.0", "Oct 17 · Watching started", "Oct 16 · Baseline complete (16 of 16)". |
| AC-FR-10 | The New admissions page shows the experimental banner and, with no reference ranges loaded, the status "Facility range not available yet" or "Not enough check-ins yet" for every listed resident. |
| AC-FR-11 | Every FR in this document appears in the BR → FR table and in at least one use case. |

## 8. Implementation Notes

- Implement FRs in the batch order of TRD 25; the analytics FRs (4.3–4.11) must pass UC-11 before the UI batches start.
- Keep display strings (status labels, captions, "What this means") in one frontend copy module and backend configuration; tests compare exact strings.
- Use `resident_code` (e.g. R01) in URLs and API paths, never UUIDs.
- The overview counts come from `processed_sessions` and `day_ledger` for the last-30-days window; do not recompute statistics in the frontend.
- `status_after_processing` for a set-aside record is `set_aside` even though the record is stored in `raw_sessions`; the 201 code means "stored", not "usable".

## 9. Open Questions

| ID | Affects |
|---|---|
| OQ-03 | FR-012, FR-171 (placeholder feature names) |
| OQ-04 | FR-021 (`phrase_id` kept while open) |
| OQ-05 | FR-107, FR-195 |
| OQ-06 | FR-109 |
| OQ-08 | FR-202, FR-204, FR-205 |
| OQ-09 | FR-073 |
| OQ-10 | FR-084 |
| OQ-11 | FR-026, FR-228 |
| OQ-12 | FR-164 |
| OQ-14 | FR-062 (screen compensates for missing speaker verification) |
| OQ-15 | FR-124 |
| OQ-18 | EWMA display not specified |
| OQ-20 | FR-204 (sex needed for F0 ranges) |

## Revision History

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1 | 18 Oct 2026 | Initial generation from TRD_Generation_Prompt.md | — |
