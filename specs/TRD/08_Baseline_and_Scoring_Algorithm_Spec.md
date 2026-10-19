# 08 Baseline and Scoring Algorithm Spec

Document ID: ECHOWELL-TRD-08 · Version 0.9 (draft for review) · Date: 18 October 2026 · Owner: Team 2 · Status: Draft

## 1. Purpose

This document gives the exact mathematics and pseudocode for the EchoWell stages between the quality gate and the
CUSUM: robust statistics, epoch detection, the speaker screen, morning classification and adjustment, baseline
membership and freeze, per-feature baselines, the composite baseline, per-feature z, the signed composite and the
composite z. An implementation that follows this document reproduces the pipeline test workbook (SRC-03) to within
1e-6 (BR-15). Every rule below was verified by an independent re-implementation against SRC-03 (section 4.11).

## 2. Scope

In scope: stages 3–7 of the engine (TRD 07 ANL-006): epoch detection, speaker screen, context (morning) adjustment,
personal baseline, daily deviation score; the shared robust-statistics primitive; edge cases; worked examples.

Out of scope: duplicate detection, quality gate, schema validation and day ledger (TRD 10); CUSUM, alarm states and
alerts (TRD 09); orchestration, persistence and late-arrival detection (TRD 07); morning offset estimation (OQ-09);
facility norms (OQ-08); any diagnostic interpretation (the composite detects a change, it does not measure severity, BR-18).

## 3. References

| ID | Document |
|---|---|
| SRC-02 | Flowcharts: stage 3 "Context adjustment: remove morning offset; mark device epochs", stage 4 "Personal baseline: built from 30 usable sessions, then frozen", stage 5 "Daily deviation score: signed z per feature, then composite" |
| SRC-03 | Workbook: Parameters, Data_dictionary, Annotated_sessions, Exp_baselines, Exp_morning_offset, Exp_scores, README notes 2, 3, 6 |
| SRC-04 | Generator script: functions `robust`, `floor_of`, speaker screen loop, baseline groups, `comp_raw` |
| SRC-05 | Input CSV |
| SRC-07 | Preprint: baseline "from several recordings rather than one"; morning effect; values not comparable across extractor versions |
| SRC-13 | Dataset specification §3 (extractor version), §4 (features, directions), §5 (time-of-day effect, device moves) |
| TRD 07 | Analytics engine (data contracts, orchestration, late arrivals ANL-024..ANL-027) |
| TRD 09 | CUSUM and alerting (consumes `composite_z`) |
| TRD 10 | Ingestion and validation (produces `pending_screen` / `set_aside` records) |
| TRD 14 | Test data and validation |

## 4. Requirements

### 4.1 Notation and definitions

| Symbol / term | Definition |
|---|---|
| F | the 19 canonical features in contract section 6 order |
| C ⊂ F | the 7 composite features: loudness_dbfs, total_phrase_duration_s, speech_rate_syl_per_s, articulation_rate_syl_per_s, number_of_pauses, pause_fraction, voiced_fraction (in this order) |
| s_f | composite sign: loudness −1, phrase duration +1, speech rate −1, articulation rate −1, pauses +1, pause fraction +1, voiced fraction −1; 0 for the other 12 |
| o_f | configured morning offset: loudness −1.50, phrase duration +0.10, speech rate −0.12, articulation rate −0.10, pauses 0, pause fraction +0.010, voiced fraction −0.020; 0 for the other 12 |
| floor_f | spread floor: `pause_floor` (0.5) for number_of_pauses, 0.0 for every other feature |
| x_f(r) | raw value of feature f in record r (as received) |
| a_f(r) | adjusted value (section 4.5) |
| N | `baseline_n` (production 30, test_v0_1 16) |
| epoch key | (device_id, device_firmware_version, extraction_software_version) of a record |
| time order | ascending `(timestamp_utc, arrival_seq)`; `timestamp_utc` compared as an instant (equivalent to comparing the "YYYY-MM-DD HH:MM:SS" strings) |
| usable | status after the speaker screen, not quarantined, not set aside, not duplicate |

### 4.2 Robust statistics (`analytics/robust_stats.py`)

```
robust(values, floor, mad_scale):
    a      = float64 array of values                     # len(a) >= 1
    median = numpy.median(a)                             # even n: mean of the two middle values
    mad    = numpy.median(|a - median|)
    spread = max(mad * mad_scale, floor)
    floor_applied = spread > mad * mad_scale             # strictly greater
    return RobustStats(median, mad, spread, floor_applied)
```

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| BSC-001 | `robust()` shall compute the median with `numpy.median` on a float64 array; for an even count n the median shall be the arithmetic mean of the (n/2)-th and (n/2+1)-th order statistics. | Must | SRC-03 README note 2, SRC-04 | Test |
| BSC-002 | `robust()` shall compute MAD as the median of absolute deviations from the median, using the same median rule as BSC-001. | Must | SRC-03 Parameters, SRC-04 | Test |
| BSC-003 | `robust()` shall compute `spread = max(MAD × mad_scale, floor)` with `mad_scale = 1.4826`. | Must | SRC-03 Parameters | Test |
| BSC-004 | `floor_applied` shall be true if and only if `spread > MAD × mad_scale` (strict); when MAD × mad_scale equals the floor exactly, `floor_applied` is false. | Must | SRC-04 | Test |
| BSC-005 | `robust()` shall raise `ContractError` for an empty input or a non-finite value; it is never called with fewer than 1 value by the stages below. | Must | TRD 07 ANL-051 | Test |

Unit-test vectors (exact): `robust([1,2,3,4], 0, 1.4826)` → median 2.5, MAD 1.0, spread 1.4826, floor_applied false;
`robust([1,1,1,1,2,2], 0.5, 1.4826)` → median 1.0, MAD 0.0, spread 0.5, floor_applied true;
`robust([0,0,1,1,1,1,1,1,1,1,2,2,2,2,2,2], 0.5, 1.4826)` → median 1.0, MAD 0.5, spread 0.7413, floor_applied false (R09 number_of_pauses, SRC-03 Exp_baselines).

### 4.3 Epoch detection (`analytics/epoch_detection.py`)

```
assign_epochs(rows, late):                       # rows = output of the quality gate
    for each resident X:
        R = [r in rows of X : r.status != "duplicate" and r not in late], sorted by time order
        key_prev = None; e = 0
        for r in R:
            if key(r) != key_prev: e = e + 1; key_prev = key(r)
            r.epoch_number = e
    duplicates: epoch_number = None
    late records: epoch_number = epoch of the last non-late record of X at or before r in time order (None if none)
```

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| BSC-006 | Epochs shall be computed per resident over all non-duplicate, non-late records (usable candidates and set-aside records alike) sorted in time order. | Must | BR-08, SRC-04, contract §7 step 3 | Test |
| BSC-007 | A record whose epoch key differs from the key of the previous record in that order shall start a new epoch; the first record of a resident starts epoch 1; epoch numbers increase by 1 and are never reused (a return to an earlier key starts a new, higher-numbered epoch). | Must | BR-08, SRC-04 | Test |
| BSC-008 | Each epoch shall have `started_at` = `timestamp_utc` of its first record and `ended_at` = `started_at` of the next epoch of the same resident (null for the current epoch). | Must | TRD 06 | Test |
| BSC-009 | Duplicate records shall have no epoch (`epoch_number = None`; `processed_sessions.epoch_id` null). | Must | SRC-03 Annotated_sessions | Test |
| BSC-010 | Within an epoch the speaker-screen reference list, the baseline count and the CUSUM state shall start empty; nothing carries over from an earlier epoch. | Must | BR-08, ASM-06 | Test |

Fixture check: R07 records 2026-10-01..10-12 on D07 are epoch 1 (12 records); R07-20261013-01 on D07B starts epoch 2.
All other test residents have one epoch, including set-aside records (expected_epoch 1 for R03/R08 set-aside rows).

### 4.4 Speaker screen (`analytics/speaker_screen.py`)

The screen runs on RAW values (not morning-adjusted) in time order within each resident-epoch.

```
screen_speakers(rows, config):
    for each (resident, epoch):
        prior = []                                         # usable sessions of this epoch, time order
        for r in records of the epoch in time order, excluding late records:
            if r.status != "pending_screen": continue      # set_aside records are not screened
            ref = prior[0 : baseline_n]                    # FIRST up to N prior usable sessions
            if len(ref) >= screen_min_n:
                for f in [mean_f0_hz] + C:
                    m, _, sp = robust([x_f(p) for p in ref], floor_f, mad_scale)
                    z_f = (x_f(r) - m) / sp   if sp > 0   else 0.0
                n3 = count(f in C with |z_f| >= screen_other_z)
                r.screen_detail = f"F0 z={z_F0:.2f}; composite features with |z|>=3: {n3}"
                if |z_F0| >= screen_f0_z and n3 >= screen_other_count:
                    r.status = "quarantined"
                    r.reasons = ("possible other speaker",)
                    r.reason_text = "possible other speaker (" + r.screen_detail + ")"
                    continue
            r.status = "usable"; prior.append(r)
```

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| BSC-011 | The speaker screen shall evaluate each `pending_screen` record of a resident-epoch in time order, using raw feature values. | Must | BR-05, SRC-03 Parameters | Test |
| BSC-012 | The reference set for record r shall be the first min(N, k) usable sessions of the same epoch that precede r in time order, where k is the number of such sessions (i.e. `prior[:baseline_n]`, not the most recent N). | Must | SRC-04, SRC-03 Parameters | Test |
| BSC-013 | The screen shall run only when the reference set contains at least `screen_min_n` (5) sessions; otherwise r becomes `usable` without a screen and `screen_detail` is null. | Must | SRC-03 Parameters | Test |
| BSC-014 | For mean_f0_hz and each of the 7 composite features, z shall be `(x − median)/spread` from `robust(reference raw values, floor_f, 1.4826)`; if spread equals 0 the z value shall be 0.0. | Must | SRC-04 | Test |
| BSC-015 | A record shall be quarantined if and only if `\|z_F0\| ≥ 4.0` AND the number of composite features with `\|z\| ≥ 3.0` is ≥ 2 (thresholds `screen_f0_z`, `screen_other_z`, `screen_other_count`). | Must | BR-05, SRC-03 Parameters | Test |
| BSC-016 | The quarantine reason text shall be exactly `possible other speaker (F0 z=<z_F0 formatted with 2 decimals>; composite features with \|z\|>=3: <count>)`, using Python format `{:.2f}` on the float64 value (e.g. "-7.34"). | Must | SRC-03 Annotated_sessions | Test |
| BSC-017 | A quarantined record shall not be appended to the reference list, shall not enter a baseline and shall not be scored; a usable record shall be appended. | Must | BR-05, SRC-03 | Test |
| BSC-018 | The screen shall run both before and after the baseline freezes; after freeze the reference is therefore the raw values of the N baseline sessions. | Must | SRC-03 Test_plan R05 | Test |
| BSC-019 | `screen_detail` shall be stored in `processed_sessions.screen_detail` for every screened record (usable or quarantined) so staff and researchers can see the screen values. | Should | BR-05, BR-13 | Test |

Fixture check (SRC-03): R05-20261008-01 (reference = 7 prior usable, days 1–7) → "possible other speaker (F0 z=-8.61;
composite features with |z|>=3: 4)"; R05-20261022-01 (reference = first 16 usable: days 1–7 and 9–17) → "possible other
speaker (F0 z=-7.34; composite features with |z|>=3: 3)". Using the most recent 16 instead gives "F0 z=-6.28" and fails the
exact-string check; using lower-middle medians changes 264 compared values.

### 4.5 Morning classification and adjustment (`analytics/morning_offset.py`)

```
local_dt   = timestamp_utc.astimezone(ZoneInfo(facility_tz))     # America/Chicago
local_date = local_dt.date()
is_morning = local_dt.hour < morning_cutoff_hour                 # 12
a_f(r)     = x_f(r) - o_f   if is_morning  else  x_f(r)          # all 19 features; o_f = 0 for 13 of them
```

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| BSC-020 | The local time of every record shall be computed by converting the UTC instant to `facility_tz` with `zoneinfo` (DST-aware); the UTC hour or UTC date shall never be used for the morning flag or the local date. | Must | BR-07, SRC-03 Parameters, ASM-01 | Test |
| BSC-021 | A record shall be morning if and only if its local hour (0–23) is less than `morning_cutoff_hour` (12). | Must | BR-07, SRC-03 Parameters | Test |
| BSC-022 | For a morning record the adjusted value of each feature shall be `raw − configured offset`; for any other record adjusted = raw. Offsets are configured values (contract section 6), not estimated (OQ-09). | Must | BR-07, SRC-03 Exp_morning_offset, README note 3 | Test |
| BSC-023 | Adjusted values shall be computed for every non-duplicate record and stored in `processed_sessions.adjusted_features` (19 keys); baselines and scores shall use adjusted values only; the speaker screen shall use raw values only. | Must | SRC-03 Parameters "baseline values" | Test |
| BSC-024 | `is_morning`, `local_date` and `local_time` shall be stored per processed session and shown on scores (`scores.is_morning`). | Must | SRC-03 Exp_scores "morning" | Test |

Worked example (R06-20261004-01, SRC-05): `timestamp_utc` 2026-10-04 14:35:55 → 09:35:55 CDT (UTC−5) → morning.

| feature | raw | offset | adjusted |
|---|---|---|---|
| loudness_dbfs | −29.01 | −1.50 | −27.51 |
| total_phrase_duration_s | 3.86 | +0.10 | 3.76 |
| speech_rate_syl_per_s | 3.56 | −0.12 | 3.68 |
| articulation_rate_syl_per_s | 4.89 | −0.10 | 4.99 |
| number_of_pauses | 3 | 0 | 3 |
| pause_fraction | 0.117 | +0.010 | 0.107 |
| voiced_fraction | 0.590 | −0.020 | 0.610 |

R06 has 10 morning sessions (days 1, 4, …, 28): 6 inside its baseline, 4 scored (R06-20261019-01, -22, -25, -28 with
`morning = True` in Exp_scores). A variant that uses the UTC hour classifies none of them as morning and fails 31 workbook rows.

### 4.6 Baseline membership and freeze (`analytics/baseline_builder.py`)

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| BSC-025 | For each (resident, epoch) the usable, non-late sessions shall be numbered 1, 2, … in time order (`baseline_ordinal`). | Must | SRC-04 | Test |
| BSC-026 | The baseline of the epoch shall consist of the sessions with `baseline_ordinal ≤ N` (`in_baseline = true`); it forms when the N-th usable session exists and is then frozen: later sessions never change it. | Must | BR-09, SRC-02 stage 4 | Test |
| BSC-027 | If an epoch has fewer than N usable sessions, `baseline_formed = false`, no baseline rows are produced, no session of the epoch is scored, and the resident status is "Baseline forming · n of N sessions" (n = usable count of the current epoch); this is not an error. | Must | BR-09, SRC-03 R07 epoch 1, R08 | Test |
| BSC-028 | The baseline shall record `n_sessions` (= N), `first_session_id` (ordinal 1), `frozen_after_session_id` (ordinal N) and `frozen_at` (= `timestamp_utc` of the frozen-after session). | Must | SRC-03 Exp_baselines | Test |
| BSC-029 | Set-aside, quarantined, duplicate and late-arrival records and missing days shall never count toward N; the baseline therefore freezes later in calendar time when such records occur (R02 after R02-20261021-01, R03 after R03-20261023-01, R05 after R05-20261017-01). | Must | BR-04, BR-05, BR-06, SRC-03 | Test |
| BSC-030 | A baseline once persisted shall never be recomputed or updated (ASM-07), except by the operator rebuild command after an algorithm-key change (TRD 07 ANL-032, TRD 24 D-56); production value N = 30, test N = 16 (ASM-04, OQ-13). | Must | BR-09, ASM-07 | Test |

### 4.7 Per-feature and composite baseline

```
B = adjusted records with in_baseline = true, time order           # |B| = N
for f in F:                                                         # all 19 features
    BL[f] = robust([a_f(b) for b in B], floor_f, mad_scale)
composite_raw(r) = (1/7) * Σ_{f in C, canonical order} s_f * (a_f(r) - BL[f].median) / BL[f].spread
BL[composite] = robust([composite_raw(b) for b in B], composite_floor, mad_scale)   # floor 0.1
```

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| BSC-031 | For each formed baseline, the engine shall compute `median`, `mad`, `robust_spread`, `floor_applied` for all 19 features from the adjusted values of the N baseline sessions, using floor 0.5 for number_of_pauses and 0 for the others. | Must | BR-09, SRC-03 Exp_baselines | Test |
| BSC-032 | `composite_raw` of a session shall be the arithmetic mean over the 7 composite features of `s_f × (a_f − median_f)/spread_f`, summed in canonical order and divided by 7. | Must | BR-10, SRC-03 Parameters | Test |
| BSC-033 | The composite baseline shall be `robust()` of the 16 (N) baseline sessions' own `composite_raw` values with floor `composite_floor` (0.1), stored as `feature_key = 'composite'`. | Must | SRC-03 Exp_baselines "COMPOSITE (raw signed mean of 7 z)" | Test |
| BSC-034 | Each formed resident-epoch shall produce exactly 20 baseline rows (19 features + composite); for SRC-05 the engine shall produce 180 rows (9 formed resident-epochs). | Must | SRC-03 | Test |
| BSC-035 | If a composite feature's `robust_spread` is 0 (possible only for features with floor 0 and identical baseline values), its z shall be 0.0 for every session of that epoch, and the engine shall emit `RunWarning(code="zero_spread", detail=<feature_key>)`; the 12 non-composite features may have spread 0 without warning because they are not scored. | Must | TRD 07 ANL-052 | Test |

### 4.8 Daily deviation score (`analytics/zscore_calculator.py`, `analytics/composite_score.py`)

```
for r in usable, non-late sessions of a formed epoch with baseline_ordinal > N, time order:
    z_f(r)        = (a_f(r) - BL[f].median) / BL[f].spread              for f in C (unsigned, stored)
    composite_raw = (1/7) Σ_{f in C} s_f * z_f(r)
    composite_z   = (composite_raw - BL[composite].median) / BL[composite].spread
```

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| BSC-036 | Every usable, non-late session with `baseline_ordinal > N` in a formed epoch shall be scored exactly once; no other session shall be scored. | Must | BR-10, SRC-03 Exp_scores (98 rows) | Test |
| BSC-037 | The stored per-feature values `z_<feature>` shall be the unsigned z `(a_f − median_f)/spread_f` for the 7 composite features (as in Exp_scores); the sign is applied only inside `composite_raw`. | Must | SRC-03 Exp_scores | Test |
| BSC-038 | `composite_z` shall be `(composite_raw − composite_median)/composite_spread`; positive values mean a change toward the depression-associated direction. | Must | BR-10, SRC-03 Parameters | Test |
| BSC-039 | Scores of the 12 non-composite features shall not be computed or stored; their adjusted values and baselines are stored for research and display ("stored, not scored"). | Must | BR-10, SRC-10 | Inspection |

### 4.9 Late arrivals (ASM-07, OQ-10)

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| BSC-040 | A record classified `late_arrival` (TRD 07 ANL-024) shall receive its own status as follows: quality gate as normal; if it passes the gate, the speaker screen shall run with reference = the first N usable non-late sessions that precede it in time order within the epoch assigned to it in section 4.3 (the epoch of the last non-late record at or before it; no screen if it has no epoch) (screen skipped if fewer than 5); it shall then be `usable` or `quarantined`, with `in_baseline = false`, no `baseline_ordinal`, no score, and the reason "late arrival (not used for baseline or scores)" appended as the last element of `reasons` (the only reason of a usable late record; the second reason of a quarantined one; a late record that fails the quality gate keeps only its quality reasons). It is stored with `processed_sessions.late_arrival = true` and, when it has no epoch, `epoch_id = NULL`, which the TRD 20 `processed_sessions` CHECKs admit only for late rows. | Must | ASM-07, OQ-10 | Test |
| BSC-041 | A late arrival shall never alter any other record's status, epoch, screen result, baseline membership, baseline value, score or tally. | Must | ASM-07, BR-09 | Test |

### 4.10 Edge cases

| Case | Rule | ID |
|---|---|---|
| Even count (N = 16 or 30) | median = mean of the two middle values (numpy) for medians and MADs | BSC-001/002 |
| MAD = 0 for number_of_pauses | spread = 0.5, `floor_applied = yes` (8 of 180 SRC-03 rows, all number_of_pauses, MAD 0) | BSC-003/004 |
| MAD = 0 for another composite feature | z = 0, warning `zero_spread` | BSC-035 |
| MAD = 0 in speaker screen | z = 0 for that feature | BSC-014 |
| Composite MAD small | spread floored at 0.1 | BSC-033 |
| Missing feature value | cannot reach the engine: rejected at ingest with 422 (TRD 10) | BSC-042 |
| Epoch with < N usable | baseline forming, nothing scored, no error (R07 epoch 1: 12; R08: 13) | BSC-027 |
| New epoch before freeze | old epoch never forms; its sessions are never scored; count restarts | BSC-010 |
| Late arrival before freeze point | not in baseline, not scored, warning | BSC-040/041 |
| Multiple sessions per local day | each processed in time order; no per-day aggregation | BSC-043 |

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| BSC-042 | The engine shall assume every record carries all 19 finite feature values (enforced by TRD 10) and shall raise `ContractError` otherwise; it shall never impute, carry forward or interpolate a value. | Must | BR-06, TRD 10 | Test |
| BSC-043 | Several records of one resident on one local day shall each be processed as separate sessions in time order; the engine shall not average or select among them (ASM-02 states at most one in v0.1). | Should | ASM-02 | Test |

### 4.11 Worked example (SRC-03, resident R09, epoch 1, device D09)

Baseline: first 16 usable sessions R09-20261001-01 … R09-20261016-01, frozen after R09-20261016-01 (all afternoon, so
adjusted = raw).

Loudness baseline: sorted adjusted values −26.32, −24.12, −23.85, −23.71, −23.17, −22.89, −22.45, **−22.41, −22.40**,
−21.21, −20.95, −20.63, −20.48, −19.94, −19.81, −17.18 → median = (−22.41 + −22.40)/2 = −22.405. Sorted absolute
deviations: 0.005, 0.005, 0.045, 0.485, 0.765, 1.195, 1.305, **1.445, 1.455**, 1.715, … → MAD = 1.45 → spread = 1.45 ×
1.4826 = 2.149770 (Exp_baselines row R09 loudness_dbfs).

Scored session R09-20261021-01 (`timestamp_utc` 2026-10-21 19:07:50 → 14:07:50 CDT, not morning):

| feature | adjusted value | baseline median | robust spread | z | sign | signed z |
|---|---|---|---|---|---|---|
| loudness_dbfs | −28.29 | −22.405 | 2.149770 | −2.737502 | −1 | 2.737502 |
| total_phrase_duration_s | 2.72 | 2.415 | 0.126021 | 2.420232 | +1 | 2.420232 |
| speech_rate_syl_per_s | 3.48 | 3.690 | 0.177912 | −1.180359 | −1 | 1.180359 |
| articulation_rate_syl_per_s | 4.93 | 5.435 | 0.318759 | −1.584269 | −1 | 1.584269 |
| number_of_pauses | 2 | 1.000 | 0.741300 | 1.348982 | +1 | 1.348982 |
| pause_fraction | 0.199 | 0.138 | 0.026687 | 2.285774 | +1 | 2.285774 |
| voiced_fraction | 0.517 | 0.6675 | 0.031876 | −4.721435 | −1 | 4.721435 |

composite_raw = (2.737502 + 2.420232 + 1.180359 + 1.584269 + 1.348982 + 2.285774 + 4.721435)/7 = 16.278553/7 = 2.325508.

Composite baseline: the 16 baseline sessions' composite_raw values, sorted: −1.262861, −0.747043, −0.709576, −0.361084,
−0.315879, −0.215635, −0.104450, **0.007120, 0.069319**, 0.168599, 0.269112, 0.278857, 0.403638, 0.450790, 0.544878,
0.717100 → median 0.038219, MAD 0.359758, spread = max(0.359758 × 1.4826, 0.1) = 0.533378 (floor not applied).

composite_z = (2.325508 − 0.038219)/0.533378 = 4.288307 (Exp_scores). TRD 09 continues this example: the tally rises
from 1.643658 to 1.643658 + 4.288307 − 0.5 = 5.431965 ≥ 5.0, so the alarm first rings at R09-20261021-01.

Verification performed for this TRD: an independent implementation of sections 4.2–4.8 plus TRD 10's gate and ledger,
run on SRC-05 with profile test_v0_1, matched all 302 Annotated_sessions rows (status, reason, morning, epoch,
in_baseline), all 180 Exp_baselines rows and all 98 Exp_scores rows (maximum absolute difference 5.3e-15), with zero mismatches.

## 5. Assumptions

- ASM-01 Facility timezone America/Chicago (all SRC-05 timestamps fall in CDT, UTC−5).
- ASM-02 At most one session per resident per local day in v0.1.
- ASM-04 Test profile N = 16, production N = 30.
- ASM-07 Frozen baselines are never recomputed.
- Morning offsets are configured, not estimated, in v0.1 (SRC-03 README note 3; OQ-09).
- Note for lead (TRD-local): the `zero_spread` rule (BSC-035) and the late-arrival own-status rule (BSC-040) are not
  exercised by SRC-03; they are defined here so that the engine never divides by zero and never alters a frozen baseline.

## 6. Dependencies

- TRD 10 supplies records that passed schema validation with 19 canonical feature keys, and the `pending_screen` / `set_aside` / `duplicate` statuses.
- TRD 07 supplies the late-arrival set, the data contracts and `PipelineConfig`.
- TRD 09 consumes `ScoreRow.composite_z` in time order per epoch.
- numpy 2.x (`numpy.median`), Python `zoneinfo` + `tzdata`.

## 7. Acceptance Criteria

- AC-BSC-01: `robust()` returns the three unit-test vectors in section 4.2 exactly.
- AC-BSC-02: On SRC-05 (test_v0_1), every Exp_baselines value (median, mad, robust_spread) matches within 1e-6 and every `floor_applied`, `n_sessions`, `first_session`, `baseline_frozen_after` matches exactly (180 rows).
- AC-BSC-03: On SRC-05, every Exp_scores `z_*`, `composite_raw`, `composite_z` matches within 1e-6 and `morning` matches exactly (98 rows).
- AC-BSC-04: Both R05 quarantine reason strings match SRC-03 exactly; no other record of SRC-05 is quarantined (267 usable).
- AC-BSC-05: R07 has epoch 1 (12 usable, baseline forming) and epoch 2 (frozen after R07-20261028-01, 2 scored); R08 has no baseline rows and no scores and the run does not raise.
- AC-BSC-06: The R09 worked example values in section 4.11 are reproduced by a unit test to 6 decimals.
- AC-BSC-07: A unit test with a baseline in which voiced_fraction has 16 identical values yields z_voiced_fraction = 0.0 for later sessions and one `zero_spread` warning.
- AC-BSC-08: A unit test shows that changing a scored session's values after freeze never changes any baseline row.

## 8. Implementation Notes

- Do not use `statistics.median_low/high`, pandas `quantile` with a non-linear method, or sorting with integer division; use `numpy.median`.
- Keep raw values and adjusted values separate in the data contracts; a common bug is running the speaker screen on adjusted values.
- The reference list for the screen is `prior[:baseline_n]` (the first N), which after freeze equals the baseline members. Do not use a sliding window.
- Compute the composite baseline from the baseline sessions' own composite_raw values (computed with the just-built feature baselines), not from per-feature MADs.
- `number_of_pauses` arrives as an integer but is treated as float64 in all arithmetic.
- Store all floats unrounded (`double precision`); format only in the UI/API layer.
- Map `feature_key = 'composite'` to the workbook label "COMPOSITE (raw signed mean of 7 z)" only in the validation test.

## 9. Open Questions

- OQ-03 Final feature column names (mapping is configured; formulas unchanged).
- OQ-09 Morning offset estimation method.
- OQ-10 Late-arriving records that predate a frozen baseline.
- OQ-13 Alarm-limit calibration on the larger dataset and the participant-criteria 90-day minimum stay question (production baseline_n = 30 is decided, D-01).
- OQ-14 Speaker verification (the screen is a heuristic substitute; RSK-01).

## Revision History

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1 | 18 Oct 2026 | Initial generation from TRD_Generation_Prompt.md | — |
| 0.1 | 18 Oct 2026 | Cross-TRD consistency review | — |
| 0.2 | 19 Oct 2026 | Phase 1 validation fixes (F-02, F-03) | — |
| 0.9 | 19 Oct 2026 | Phase 1 round-8 minor fixes (R8-01) | — |
