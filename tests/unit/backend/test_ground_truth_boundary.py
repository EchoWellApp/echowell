"""Only the analytics summary reads the answer key (TRD 05 API-136; TRD 13 TST-068;
FEAT-035-AC-05, FEAT-035-FR-08).

No file under `analytics/` and no backend module other than `backend/services/analytics_summary.py`
may reference the read-only URL or `evaluation_ground_truth` (table or model). The model and
migration that define the table and the settings field that holds the URL are the only exceptions.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
FORBIDDEN = re.compile(
    r"evaluation_ground_truth|EvaluationGroundTruth|DATABASE_READONLY_URL|database_readonly_url"
)
ALLOWED = {
    "backend/services/analytics_summary.py",
    "backend/core/config.py",  # the settings field and its validation
    "backend/models/__init__.py",  # model export
    "backend/models/evaluation.py",  # model definition
}


def offenders(root: Path) -> list[str]:
    found = []
    for path in sorted([*(root / "backend").rglob("*.py"), *(root / "analytics").rglob("*.py")]):
        relative = path.relative_to(root).as_posix()
        if relative in ALLOWED or relative.startswith("backend/alembic/"):
            continue
        if FORBIDDEN.search(path.read_text(encoding="utf-8")):
            found.append(relative)
    return found


@pytest.mark.req("API-136", "TST-068", "TDV-101", "FEAT-035-AC-05")
def test_only_the_summary_reads_the_answer_key() -> None:
    assert offenders(ROOT) == []


@pytest.mark.req("TST-068", "FEAT-035-AC-05")
def test_a_forbidden_reference_is_found(tmp_path: Path) -> None:
    (tmp_path / "backend" / "services").mkdir(parents=True)
    (tmp_path / "analytics").mkdir()
    (tmp_path / "backend" / "services" / "pipeline_runner.py").write_text(
        "rows = session.execute(text('SELECT * FROM evaluation_ground_truth'))\n"
    )
    assert offenders(tmp_path) == ["backend/services/pipeline_runner.py"]
