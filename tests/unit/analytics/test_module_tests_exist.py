"""Each TRD 07 §4.2 module has tests/unit/analytics/test_<module>.py (TRD 13 TST-011)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.req("TST-011", "ANL-008")
def test_tst_011_every_analytics_module_has_a_test_file() -> None:
    modules = {p.stem for p in (ROOT / "analytics").glob("*.py")} - {"__init__"}
    missing = [
        m for m in sorted(modules) if not (ROOT / f"tests/unit/analytics/test_{m}.py").exists()
    ]
    assert missing == []
