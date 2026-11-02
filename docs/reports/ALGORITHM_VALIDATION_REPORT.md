# ALGORITHM_VALIDATION_REPORT

Generated: 2026-11-02T18:41:04Z · Git SHA: 1bbcbfa · Profile: test_v0_1 · Config snapshot SHA-256: 51ca68f8aaa253aa4cc7b3b8456d2f3634f3ea96ea57f650f54d7279509ddcca
Input: EchoWell_pipeline_test_input_v0_1.csv (SHA-256 78e77faad423f305dfb83429ccd21978f089e843c181b5d244a5d7d4f5fabe28) · Answer key: EchoWell_pipeline_test_v0_1.xlsx (SHA-256 ddbc03ea6fef37388d2f0265902096cc0fe28559d36cb2855f63ec51ec482257)
Tolerance: abs 1e-6 (float64); strings, integers, booleans exact
Overall: PASS

Synthetic test data only (study IDs and generated values; no real resident data).

## 1. Summary

| Case | Title | Tier A | Tier B | Checks | Mismatches | First failing stage |
|---|---|---|---|---|---|---|
| VC-R01 | Clean control | PASS | PASS | 3310 | 0 |  |
| VC-R02 | Missing days | PASS | PASS | 2920 | 0 |  |
| VC-R03 | Set-aside sessions | PASS | PASS | 2866 | 0 |  |
| VC-R04 | Duplicate records | PASS | PASS | 3233 | 0 |  |
| VC-R05 | Possible other speaker | PASS | PASS | 3016 | 0 |  |
| VC-R06 | Morning effect | PASS | PASS | 3226 | 0 |  |
| VC-R07 | Device move | PASS | PASS | 2836 | 0 |  |
| VC-R08 | Too few sessions | PASS | PASS | 2298 | 0 |  |
| VC-R09 | Step change | PASS | PASS | 3186 | 0 |  |
| VC-R10 | Gradual drift | PASS | PASS | 3186 | 0 |  |
| VC-G01 | Status totals | PASS | PASS | 26 | 0 |  |
| VC-G02 | Annotated sessions row by row | PASS | PASS | 22348 | 0 |  |
| VC-G03 | Per-resident status counts | PASS | PASS | 142 | 0 |  |
| VC-G04 | Resident outcomes | PASS | PASS | 178 | 0 |  |
| VC-G05 | Baselines | PASS | PASS | 3286 | 0 |  |
| VC-G06 | Scores | PASS | PASS | 3160 | 0 |  |
| VC-G07 | Morning offsets | PASS | PASS | 116 | 0 |  |
| VC-G08 | Parameters | PASS | PASS | 32 | 0 |  |
| VC-G09 | Day ledger | PASS | PASS | 8 | 0 |  |
| VC-G10 | Alerts | PASS | PASS | 40 | 0 |  |
| VC-G11 | Raw store fidelity | n/a | PASS | 286 | 0 |  |
| VC-G12 | Determinism and rebuild | PASS | PASS | 32520 | 0 |  |

## 2. Passed cases

VC-R01, VC-R02, VC-R03, VC-R04, VC-R05, VC-R06, VC-R07, VC-R08, VC-R09, VC-R10, VC-G01, VC-G02, VC-G03, VC-G04, VC-G05, VC-G06, VC-G07, VC-G08, VC-G09, VC-G10, VC-G11, VC-G12

## 3. Failed cases

None.

## 4. Root cause analysis

No failed case.

## 5. Recommended fixes

No failed case.

## 6. Supplementary checks

| Check | Result | Checks | Mismatches | Gating |
|---|---|---|---|---|
| VC-R04-INV | PASS | 1699 | 0 | yes |
| VC-R10-FRZ | PASS | 361 | 0 | yes |
| VC-R06-MUT | PASS | 180 | 0 | no (Should) |

## 7. Informational: false-alarm robustness (not gating)

Latest run 2026-11-02T04:43:24Z: seeds 1..100, residents R01-R06 (rate) and R07-R08 (reported), false alarms 61, rate 10.2% (61 of 600).
Per resident: R01 14, R02 7, R03 8, R04 8, R05 13, R06 11, R07 0, R08 0.
Answer-key reproduction mismatches (S2 when non-zero): 0 seeds.
