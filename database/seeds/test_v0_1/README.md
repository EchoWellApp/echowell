# test_v0_1 seed files

Synthetic test data only. No real resident or patient data belongs here.

| File | What it is |
|---|---|
| `facilities.csv`, `residents.csv`, `devices.csv`, `device_assignments.csv` | The roster loaded by `python -m backend.cli seed test_v0_1 --master-only` (TRD 20 §4.11, FEAT-017) |
| `EchoWell_pipeline_test_input_v0_1.csv` | **A copy of SRC-05**, `specs/data-samples/EchoWell_pipeline_test_input_v0_1.csv`. The full `seed test_v0_1` ingests it and runs the pipeline (FEAT-055, D-93). It is copied here because the Docker image contains `backend/`, `analytics/` and `database/` but not `specs/` (TRD 24 D-133). |

The copy is never edited by hand. Whenever SRC-05 changes, copy it again:

```bash
cp specs/data-samples/EchoWell_pipeline_test_input_v0_1.csv database/seeds/test_v0_1/
```

`tests/unit/test_seed_copies.py` fails while the copy and SRC-05 differ.
