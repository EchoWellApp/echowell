# Security exceptions

Time-boxed waivers for a `security-audit` failure on an unchanged dependency (TRD 16 CIC-072, TRD 13 TST-136,
FEAT-078-FR-18). A waiver lasts at most 7 days, references a tracking issue, and is applied by `scripts/ci/audit_gate.py`,
which the `security-audit` job runs for pip and npm: a row counts only until its `Expires` date, after which the
gate fails again. Remove the row and the ignore entry when the fix is merged or the
waiver expires, whichever comes first. Patch deadlines: critical within 7 days, high within 30 days (TRD 12
SEC-156).

| Advisory | Package and version | Severity | Ignore entry | Tracking issue | Added | Expires | Approved by |
|---|---|---|---|---|---|---|---|
| GHSA-2464-fhr4-w9xw, GHSA-2xp9-vwfh-vxw4, GHSA-36qx-fr4f-26g5, GHSA-3g8h-86w9-wvmq, GHSA-3x4c-7xq6-9pq8, GHSA-4633-3j49-mh5q, GHSA-4c39-4ccg-62r3, GHSA-68g3-v927-f742, GHSA-89xv-2m56-2m9x, GHSA-8h8q-6873-q5fj, GHSA-955p-x3mx-jcvp, GHSA-9g9p-9gw9-jx7f, GHSA-c4j6-fc7j-m34r, GHSA-ffhc-5mcf-pf4q, GHSA-ggv3-7p47-pfv8, GHSA-gx5p-jg67-6x7h, GHSA-h25m-26qc-wcjf, GHSA-h64f-5h5j-jqjh, GHSA-m99w-x7hq-7vfj, GHSA-p293-qw3h-jr36, GHSA-p3m5-59mp-jv5r, GHSA-p9j2-gv94-2wf4, GHSA-q4gf-8mx6-v5v3, GHSA-vfv6-92ff-j949, GHSA-wfc6-r584-vfw7 | next 14.2.35 | critical | `scripts/ci/audit_gate.py npm` | Pinned major (TRD 25 §4.7); fix needs a major upgrade; accepted debt D-105 / RSK-16, decision due in the checkpoint 8 review (GitHub PR for checkpoint 8, Q-1) | 2026-11-05 | 2026-11-12 | pending (D-105) |
| GHSA-6g55-p6wh-862q, GHSA-fxqj-rqcc-2cmp, GHSA-qx2v-qp2m-jg93, GHSA-r28c-9q8g-f849 | postcss (bundled by next 14) | high | `scripts/ci/audit_gate.py npm` | Pinned major (TRD 25 §4.7); fix needs a major upgrade; accepted debt D-105 / RSK-16, decision due in the checkpoint 8 review (GitHub PR for checkpoint 8, Q-1) | 2026-11-05 | 2026-11-12 | pending (D-105) |
| PYSEC-2026-161, PYSEC-2026-249, PYSEC-2026-248, PYSEC-2026-1942, PYSEC-2026-1941, PYSEC-2026-2281, PYSEC-2026-2280 | starlette 0.46.2 (required by fastapi 0.115.x) | various | `scripts/ci/audit_gate.py pip` | Pinned major (TRD 25 §4.7); fix needs a major upgrade; accepted debt D-105 / RSK-16, decision due in the checkpoint 8 review (GitHub PR for checkpoint 8, Q-1) | 2026-11-05 | 2026-11-12 | pending (D-105) |
