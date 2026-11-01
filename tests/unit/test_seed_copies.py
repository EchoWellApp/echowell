"""The SRC-05 copies equal SRC-05 (TRD 24 D-133; FEAT-055).

The full `seed test_v0_1` reads `database/seeds/test_v0_1/EchoWell_pipeline_test_input_v0_1.csv`
because the Docker image has no `specs/`; the API tests read the fixture copy. Both must stay
byte-identical to `specs/data-samples/`, so a change to SRC-05 that is not copied fails here.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
SRC_05 = ROOT / "specs" / "data-samples" / "EchoWell_pipeline_test_input_v0_1.csv"
COPIES = (
    ROOT / "database" / "seeds" / "test_v0_1" / SRC_05.name,
    ROOT / "tests" / "fixtures" / "pipeline_input" / SRC_05.name,
)


@pytest.mark.req("D-133", "FEAT-055-FR-06")
@pytest.mark.parametrize("copy", COPIES, ids=lambda p: str(p.relative_to(ROOT)))
def test_copy_equals_src05(copy: Path) -> None:
    assert copy.read_bytes() == SRC_05.read_bytes(), f"copy SRC-05 again to {copy}"
