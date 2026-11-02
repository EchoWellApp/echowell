"""Compare pipeline outputs with the answer key (TRD 14 §4.4, §4.5; TDV-032..TDV-042; FEAT-058).

Tables 4.5-A..4.5-F are the declarative `SHEETS` mappings below: each column names how it is
compared and the pipeline stage (Table 4.5-G) a mismatch is attributed to, so a renamed API field
changes only a mapping (TDV-040). Rows match by natural keys, never order (TDV-036); every mismatch
is recorded and the comparison carries on (TDV-037). Floats pass iff |actual - expected| <= 1e-6
(TDV-032); strings, integers and booleans compare exactly; a blank cell equals null or "" and
`first_alarm_session` "none" equals null (TDV-033..TDV-035).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from tests.validation.answer_key import blank, key_of, rows
from tests.validation.outputs import RECORD_COLUMNS, STATUS_COLUMNS, Key, Outputs

TOLERANCE = 1e-6
ALARMS = {"off": "off", "RINGS (first crossing)": "rings", "on": "on"}
# Table 4.5-G: the stage a status (or status count) belongs to.
STATUS_STAGE = {"duplicate": 1, "set_aside": 2, "usable": 2, "quarantined": 4,
                "missing_resident": 10, "missing_device_gap": 10}  # fmt: skip
ROW = "(row)"


@dataclass(frozen=True)
class Mismatch:
    sheet: str
    key: str
    column: str
    expected: Any
    actual: Any
    abs_diff: float | None
    stage: int

    def as_json(self) -> dict[str, Any]:
        return {"sheet": self.sheet, "key": self.key, "column": self.column,
                "expected": _plain(self.expected), "actual": _plain(self.actual),
                "abs_diff": self.abs_diff, "stage": self.stage}  # fmt: skip


@dataclass
class Result:
    checks: int = 0
    mismatches: list[Mismatch] = field(default_factory=list)

    def __iadd__(self, other: Result) -> Result:
        self.checks += other.checks
        self.mismatches.extend(other.mismatches)
        return self

    @property
    def passed(self) -> bool:
        """A case with no comparison is never a pass (TDV-071)."""
        return self.checks > 0 and not self.mismatches

    @property
    def first_stage(self) -> int | None:
        return min((m.stage for m in self.mismatches), default=None)


@dataclass(frozen=True)
class Column:
    name: str  # workbook column
    kind: str  # exact | float | yesno | alarm | none_null
    stage: int | Callable[[Any, Any], int]
    field: str | None = None  # Outputs field when it differs from the workbook name


@dataclass(frozen=True)
class Sheet:
    name: str
    outputs: str  # Outputs attribute
    columns: tuple[Column, ...]


def _status_stage(expected: Any, actual: Any) -> int:
    return STATUS_STAGE.get(expected) or STATUS_STAGE.get(actual) or 1


_RECORD = tuple(
    Column(c, "float" if c in {"mic_noise_level_dbfs", "speech_duration_s"} or c.islower()
           and c not in {"schema_version", "session_id", "device_id", "timestamp_utc",
                         "audio_quality_flag", "extraction_software_version",
                         "device_firmware_version", "phrase_id"} else "exact", 1)
    for c in RECORD_COLUMNS
)  # fmt: skip

SHEETS: dict[str, Sheet] = {
    # Table 4.5-A (302 rows); in_baseline is checked as baseline_candidate and as stored.
    "Annotated_sessions": Sheet("Annotated_sessions", "annotated", (
        Column("local_time", "exact", 5),
        Column("expected_status", "exact", _status_stage),
        Column("expected_reason", "exact", _status_stage),
        Column("expected_morning", "yesno", 5),
        Column("expected_epoch", "exact", 3),
        Column("in_baseline", "yesno", 6),
        Column("in_baseline", "yesno", 6, field="in_baseline_stored"),
        *_RECORD,
    )),
    # Table 4.5-B
    "Exp_status_counts": Sheet("Exp_status_counts", "status_counts", tuple(
        Column(c, "exact", STATUS_STAGE[c]) for c in STATUS_COLUMNS)),
    # Table 4.5-C
    "Exp_resident_outcomes": Sheet("Exp_resident_outcomes", "outcomes", (
        Column("device_id", "exact", 3),
        Column("usable_in_epoch", "exact", 4),
        Column("baseline_formed", "yesno", 6),
        Column("baseline_frozen_after", "exact", 6),
        Column("scored_sessions", "exact", 7),
        Column("first_alarm_session", "none_null", 9),
        Column("note", "exact", 6),
    )),
    # Table 4.5-D (composite row matched by its label, TDV-042)
    "Exp_baselines": Sheet("Exp_baselines", "baselines", (
        Column("device_id", "exact", 3),
        Column("n_sessions", "exact", 6),
        Column("first_session", "exact", 6),
        Column("baseline_frozen_after", "exact", 6),
        Column("median", "float", 6),
        Column("mad", "float", 6),
        Column("robust_spread", "float", 6),
        Column("floor_applied", "yesno", 6),
    )),
    # Table 4.5-E (offsets; the other parameters are VC-G08)
    "Exp_morning_offset": Sheet("Exp_morning_offset", "morning_offsets", (
        Column("configured_morning_offset", "float", 5),
    )),
    # Table 4.5-F (unsigned z, TDV-041)
    "Exp_scores": Sheet("Exp_scores", "scores", (
        Column("resident_id", "exact", 3),
        Column("epoch", "exact", 3),
        Column("local_date", "exact", 5),
        Column("morning", "exact", 5),
        *(Column(f"z_{k}", "float", 7) for k in (
            "loudness_dbfs", "total_phrase_duration_s", "speech_rate_syl_per_s",
            "articulation_rate_syl_per_s", "number_of_pauses", "pause_fraction",
            "voiced_fraction")),
        Column("composite_raw", "float", 7),
        Column("composite_z", "float", 7),
        Column("cusum_tally", "float", 8),
        Column("alarm", "alarm", 8),
    )),
}  # fmt: skip
ROW_STAGE = {"Annotated_sessions": 1, "Exp_status_counts": 10, "Exp_resident_outcomes": 3,
             "Exp_baselines": 6, "Exp_morning_offset": 5, "Exp_scores": 7}  # fmt: skip


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _expected(kind: str, value: Any) -> Any:
    if blank(value):
        return None
    if kind == "yesno":
        return {"yes": True, "no": False}.get(value, value)
    if kind == "alarm":
        return ALARMS.get(value, value)
    if kind == "none_null":
        return None if value == "none" else value
    if isinstance(value, float) and value.is_integer() and kind == "exact":
        return int(value)
    return value


def compare_value(
    sheet: str, key: str, column: Column, expected_cell: Any, actual: Any
) -> Mismatch | None:
    """One comparison under the rules of TDV-032..TDV-035."""
    expected = _expected(column.kind, expected_cell)
    if actual == "":
        actual = None
    stage = column.stage(expected, actual) if callable(column.stage) else column.stage
    if column.kind == "float" and expected is not None:
        e, a = _number(expected), _number(actual)
        if a is None or math.isnan(a) or e is None:
            return Mismatch(sheet, key, column.name, expected, actual, None, stage)
        diff = abs(a - e)
        return None if diff <= TOLERANCE else Mismatch(sheet, key, column.name, e, a, diff, stage)
    if type(expected) is not type(actual) and not (
        isinstance(expected, int | float) and isinstance(actual, int | float)
        and not isinstance(expected, bool) and not isinstance(actual, bool)
    ):  # fmt: skip
        return Mismatch(sheet, key, column.name, expected, actual, None, stage)
    return None if expected == actual else Mismatch(sheet, key, column.name, expected, actual,
                                                    None, stage)  # fmt: skip


def key_text(key: Key) -> str:
    return "/".join(str(part) for part in key)


def compare_sheet(
    name: str, outputs: Outputs, select: Callable[[Key], bool] = lambda _: True
) -> Result:
    """Every selected row of a DS-02 sheet against the outputs, matched by natural key."""
    spec = SHEETS[name]
    actual: dict[Key, dict[str, Any]] = getattr(outputs, spec.outputs)
    expected = {key_of(name, row, i): row for i, row in enumerate(rows(name))}
    result = Result()
    for key in sorted({k for k in expected if select(k)} | {k for k in actual if select(k)},
                      key=key_text):  # fmt: skip
        result.checks += 1
        if key not in actual or key not in expected:
            result.mismatches.append(Mismatch(
                name, key_text(key), ROW, "present" if key in expected else "absent",
                "present" if key in actual else "absent", None, ROW_STAGE[name]))  # fmt: skip
            continue
        for column in spec.columns:
            result.checks += 1
            found = compare_value(name, key_text(key), column, expected[key][column.name],
                                  actual[key].get(column.field or column.name))  # fmt: skip
            if found is not None:
                result.mismatches.append(found)
    return result


def check(sheet: str, key: str, column: str, expected: Any, actual: Any, stage: int,
          kind: str = "exact") -> Result:  # fmt: skip
    """One ad-hoc comparison (global checks and case rules) under the same rules."""
    found = compare_value(sheet, key, Column(column, kind, stage), expected, actual)
    return Result(1, [found] if found else [])


def compare_outputs(a: Outputs, b: Outputs, label: str = "Tier A vs Tier B") -> Result:
    """Tier A and Tier B results must be equal on every compared value (TST-081)."""
    result = Result()
    for name, left in a.compared().items():
        _walk(result, label, name, left, b.compared()[name])
    return result


def _walk(result: Result, label: str, path: str, left: Any, right: Any) -> None:
    if isinstance(left, dict) and isinstance(right, dict):
        for k in sorted(set(left) | set(right), key=str):
            if k not in left or k not in right:
                result.checks += 1
                result.mismatches.append(Mismatch(label, f"{path}/{k}", ROW,
                                                  k in left, k in right, None, 1))  # fmt: skip
            else:
                _walk(result, label, f"{path}/{k}", left[k], right[k])
        return
    if isinstance(left, list | tuple) and isinstance(right, list | tuple) and not _is_row(left):
        if len(left) != len(right):
            result.checks += 1
            result.mismatches.append(Mismatch(label, path, "length", len(left), len(right),
                                              None, 1))  # fmt: skip
            return
        for i, (x, y) in enumerate(zip(left, right, strict=True)):
            _walk(result, label, f"{path}[{i}]", x, y)
        return
    result.checks += 1
    if left != right:
        result.mismatches.append(Mismatch(label, path, "value", left, right, None, 1))


def _is_row(value: Iterable[Any]) -> bool:
    return isinstance(value, tuple) and not any(isinstance(v, dict | list) for v in value)


def _plain(value: Any) -> Any:
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)
