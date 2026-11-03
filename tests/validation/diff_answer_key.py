"""Show what changed between two answer-key workbooks (TRD 14 TDV-023; TRD 13 TST-073;
FEAT-057-FR-07).

    python -m tests.validation.diff_answer_key <old.xlsx> <new.xlsx>

Per sheet it prints the row count before and after, then every changed cell as
`sheet!key.column: old -> new`, matching rows by the natural keys of TDV-036. A row present on one
side only prints every one of its cells against `(absent)`. The output goes into the description of
an `answer-key-change` PR (TDV-021).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from tests.validation.answer_key import blank, key_of, read_sheets

ABSENT = "(absent)"


def _show(value: Any) -> str:
    return "" if blank(value) else str(value)


def _key_text(key: tuple[Any, ...]) -> str:
    return "/".join(str(part) for part in key)


def diff(old: Path, new: Path) -> list[str]:
    before, after = read_sheets(old), read_sheets(new)
    lines: list[str] = []
    for sheet in list(before) + [s for s in after if s not in before]:
        old_rows = _keyed(sheet, before.get(sheet))
        new_rows = _keyed(sheet, after.get(sheet))
        lines.append(f"{sheet}: rows {len(old_rows)} -> {len(new_rows)}")
        for key in list(old_rows) + [k for k in new_rows if k not in old_rows]:
            a, b = old_rows.get(key), new_rows.get(key)
            for column in list(a or {}) + [c for c in (b or {}) if c not in (a or {})]:
                old_value = ABSENT if a is None else _show(a.get(column))
                new_value = ABSENT if b is None else _show(b.get(column))
                if old_value != new_value:
                    lines.append(f"{sheet}!{_key_text(key)}.{column}: {old_value} -> {new_value}")
    return lines


def _keyed(sheet: str, frame: Any) -> dict[tuple[Any, ...], dict[str, Any]]:
    if frame is None:
        return {}
    records = frame.to_dict(orient="records")
    return {key_of(sheet, row, index): row for index, row in enumerate(records)}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("usage: python -m tests.validation.diff_answer_key <old.xlsx> <new.xlsx>",
              file=sys.stderr)  # fmt: skip
        return 2
    for line in diff(Path(args[0]), Path(args[1])):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
