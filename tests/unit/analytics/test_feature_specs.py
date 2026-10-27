"""The built-in feature table equals contract §6 as written in TRD 23 §4.2.9 (DME-002)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from analytics.config import FEATURES

pytestmark = pytest.mark.unit

TRD_23 = next((Path(__file__).resolve().parents[3] / "specs" / "TRD").glob("23_*.md"))
ROW = re.compile(
    r"^\| `(?P<key>[a-z0-9_]+)` \| [a-z ]+ \| no \| Acoustic feature .*?; unit (?P<unit>[^;,]+)"
    r"(?:, [^;]*)?; (?:composite, sign (?P<sign>[+-]1), morning offset (?P<offset>[+-]?[0-9.]+)"
    r"|stored, not scored)",
    re.MULTILINE,
)


@pytest.mark.req("DME-002", "TRD 07 §4.2", "BSC-039")
def test_features_equal_trd_23() -> None:
    rows = [m.groupdict() for m in ROW.finditer(TRD_23.read_text(encoding="utf-8"))]
    assert [r["key"] for r in rows] == [f.key for f in FEATURES]
    for row, spec in zip(rows, FEATURES, strict=True):
        assert spec.unit == row["unit"].strip().removesuffix(" 0..1"), spec.key  # range, not unit
        assert spec.sign == (int(row["sign"]) if row["sign"] else 0), spec.key
        offset = float(row["offset"]) if row["offset"] else 0.0
        assert spec.morning_offset == offset, spec.key
    assert [f.key for f in FEATURES if f.in_composite] == [f.key for f in FEATURES[:7]]
