"""Read the answer-key workbook DS-02 (TRD 14 §4.5, §8; TDV-015, TDV-036, TDV-038).

The workbook is opened read-only through pandas/openpyxl at its full stored precision and never
written. Only code under `tests/` may import this module (TDV-011, AGT-007).
"""

from __future__ import annotations

import functools
import math
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
WORKBOOK = ROOT / "tests" / "fixtures" / "answer_key" / "EchoWell_pipeline_test_v0_1.xlsx"
INPUT_CSV = ROOT / "tests" / "fixtures" / "pipeline_input" / "EchoWell_pipeline_test_input_v0_1.csv"
GROUND_TRUTH = ROOT / "tests" / "fixtures" / "answer_key" / "evaluation_ground_truth_v0_1.csv"
COMPOSITE_LABEL = "COMPOSITE (raw signed mean of 7 z)"
FIRST_DAY = date(2026, 10, 1)

# Natural keys of TDV-036 (and of the descriptive sheets, for the diff tool).
KEYS: dict[str, tuple[str, ...]] = {
    "Annotated_sessions": ("resident_id", "day", "arrival_order"),
    "Exp_status_counts": ("resident_id",),
    "Exp_resident_outcomes": ("resident_id", "epoch"),
    "Exp_baselines": ("resident_id", "epoch", "feature"),
    "Exp_morning_offset": ("feature",),
    "Exp_scores": ("session_id",),
    "Parameters": ("parameter",),
    "Test_plan": ("resident_id",),
    "Data_dictionary": ("field",),
}


def blank(value: Any) -> bool:
    """A blank workbook cell (NaN or None) or an empty string (TDV-035)."""
    return value is None or (isinstance(value, float) and math.isnan(value)) or value == ""


def read_sheets(path: Path) -> dict[str, pd.DataFrame]:
    """Every sheet as strings and Python numbers (`dtype=object`), read-only (TDV-015)."""
    sheets: dict[str, pd.DataFrame] = pd.read_excel(
        path, sheet_name=None, dtype=object, engine="openpyxl"
    )
    return sheets


@functools.cache
def workbook() -> dict[str, pd.DataFrame]:
    return read_sheets(WORKBOOK)


def rows(sheet: str) -> list[dict[str, Any]]:
    """The rows of a DS-02 sheet as dicts, blanks as None."""
    frame = workbook()[sheet]
    return [{k: (None if blank(v) else v) for k, v in record.items()}
            for record in frame.to_dict(orient="records")]  # fmt: skip


def key_of(sheet: str, row: dict[str, Any], index: int) -> tuple[Any, ...]:
    columns = KEYS.get(sheet)
    if columns is None:
        return (index,)
    return tuple(_normal(row[c]) for c in columns)


def _normal(value: Any) -> Any:
    """Keys compare as ints where the workbook stored a whole number as float."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def local_date(day: Any) -> date:
    """Annotated_sessions `day` 1..30 → local date (TRD 14 §8)."""
    return FIRST_DAY + timedelta(days=int(day) - 1)
