"""Load the evaluation ground truth (DS-10) into `evaluation_ground_truth` (TRD 14 TDV-103, §4.9.3;
TRD 09 CUS-048; TRD 24 D-38; FEAT-057-FR-10).

    python database/seeds/load_evaluation_ground_truth.py \
        tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv

Test data only: the script refuses (exit 2, nothing written) when APP_ENV is `production` or
PIPELINE_PROFILE is not `test_v0_1`. Otherwise it validates every row of the CSV given on its
command line and replaces the table contents in one transaction as `echowell_migrator`
(DATABASE_MIGRATION_URL); a malformed file exits 1 and leaves the table unchanged. It reads no
other file and is deliberately not a `backend.cli` command (TRD 15 §4.8, D-68). The pipeline never
reads this table (SRC-02, AGT-007); only the Study team alarm-timing block does, after a run.
"""

from __future__ import annotations

import csv
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text

from backend.core.config import load_settings_or_exit
from backend.core.db import migrator_connection

COLUMNS = ["resident_code", "planted_change", "true_onset_date", "source_file"]
NO_CHANGE = "None"


class MalformedError(ValueError):
    pass


def refusal(environ: dict[str, str]) -> str | None:
    """The reason to refuse before touching the database, or None (TDV-103)."""
    if environ.get("APP_ENV", "") == "production":
        return "the evaluation ground truth is never loaded in production"
    if environ.get("PIPELINE_PROFILE", "") != "test_v0_1":
        return "the evaluation ground truth is loaded only under PIPELINE_PROFILE=test_v0_1"
    return None


def read_rows(path: Path) -> list[dict[str, object]]:
    """Every row validated, or MalformedError naming the first problem."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != COLUMNS:
            raise MalformedError(f"columns must be {', '.join(COLUMNS)}")
        rows: list[dict[str, object]] = []
        for number, row in enumerate(reader, start=2):
            code, change = row["resident_code"].strip(), row["planted_change"].strip()
            onset_text, source = row["true_onset_date"].strip(), row["source_file"].strip()
            if not code or not change or not source:
                raise MalformedError(f"line {number}: empty resident_code, change or source")
            try:
                onset = date.fromisoformat(onset_text) if onset_text else None
            except ValueError as exc:
                raise MalformedError(f"line {number}: true_onset_date {onset_text!r}") from exc
            if (change == NO_CHANGE) != (onset is None):
                raise MalformedError(
                    f"line {number}: onset date must be set iff a change is planted"
                )
            rows.append({"resident_code": code, "planted_change": change,
                         "true_onset_date": onset, "source_file": source})  # fmt: skip
    codes = [r["resident_code"] for r in rows]
    if len(set(codes)) != len(codes):
        raise MalformedError("resident_code repeated")
    if not rows:
        raise MalformedError("no rows")
    return rows


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("usage: load_evaluation_ground_truth.py <csv_path>", file=sys.stderr)
        return 2
    reason = refusal(dict(os.environ))
    if reason is not None:
        print(f"Refused: {reason}.", file=sys.stderr)
        return 2
    try:
        rows = read_rows(Path(args[0]))
    except (OSError, MalformedError) as exc:
        print(f"Not loaded: {exc}.", file=sys.stderr)
        return 1
    settings = load_settings_or_exit(operator=True)
    with migrator_connection(settings) as connection, connection.begin():
        connection.execute(text("DELETE FROM evaluation_ground_truth"))
        connection.execute(
            text("INSERT INTO evaluation_ground_truth (resident_code, planted_change, "
                 "true_onset_date, source_file) VALUES (:resident_code, :planted_change, "
                 ":true_onset_date, :source_file)"),
            rows,
        )  # fmt: skip
    print(f"Loaded {len(rows)} evaluation ground-truth rows (profile test_v0_1).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
