"""Repository layout, hygiene and pins (TRD 01 ARC-050, TRD 07 ANL-004, TRD 13 TST-007,
TRD 18 GIT-090..GIT-100, TRD 25 AC-AGT-06, AC-AGT-11; FEAT-002)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
ANALYTICS_MODULES = {
    "config", "robust_stats", "duplicate_detection", "quality_screening", "epoch_detection",
    "speaker_screen", "morning_offset", "baseline_builder", "zscore_calculator", "composite_score",
    "cusum_engine", "alert_generator", "day_ledger", "data_alerts", "aggregates", "pipeline",
}  # fmt: skip
SKELETON_FILES = [
    *(f"backend/api/{n}.py" for n in ("alarms", "analytics", "health", "residents", "sessions")),
    *(f"backend/models/{n}.py" for n in ("alarm", "baseline", "resident", "score", "session")),
    *(
        f"backend/services/{n}.py"
        for n in (
            "baseline", "cusum", "ingestion", "morning_adjustment", "scoring", "speaker_screen",
            "validation",
        )  # fmt: skip
    ),
    "backend/main.py", "backend/requirements.txt", "database/schema.sql", "docker-compose.yml",
    "frontend/package.json", "frontend/next.config.js", "frontend/services/api.ts",
    ".github/workflows/ci.yml",
]  # fmt: skip
AUDIO = re.compile(r"\.(wav|mp3|flac|ogg|m4a|opus|aac|webm)$", re.IGNORECASE)


def tracked_files() -> list[str]:
    result = subprocess.run(  # noqa: S603 - fixed git arguments
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],  # noqa: S607
        cwd=ROOT, capture_output=True, text=True, check=True,
    )  # fmt: skip
    return result.stdout.splitlines()


@pytest.mark.req("AC-AGT-06", "ARC-050", "AGT-010")
def test_skeleton_files_kept() -> None:
    assert [f for f in SKELETON_FILES if not (ROOT / f).is_file()] == []


@pytest.mark.req("ANL-004", "ANL-001")
def test_analytics_has_exactly_the_trd07_modules() -> None:
    found = {p.stem for p in (ROOT / "analytics").glob("*.py")}
    assert found == ANALYTICS_MODULES | {"__init__"}


@pytest.mark.req("TST-007", "GIT-091")
def test_tst_007_no_audio_files_tracked() -> None:
    assert [f for f in tracked_files() if AUDIO.search(f)] == []


@pytest.mark.req("GIT-080", "GIT-090", "AC-GIT-02")
def test_no_env_file_or_licence_tracked() -> None:
    files = tracked_files()
    assert [
        f for f in files if re.search(r"(^|/)\.env($|\.)", f) and not f.endswith(".example")
    ] == []
    assert "LICENSE" not in files


@pytest.mark.req("GIT-100")
def test_gitignore_keeps_generated_references_tracked() -> None:
    result = subprocess.run(  # noqa: S603 - fixed git arguments
        ["git", "check-ignore", "database/schema.sql", "docs/api_reference/openapi.json"],  # noqa: S607
        cwd=ROOT, capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert result.stdout == ""


@pytest.mark.req("AC-AGT-11", "AGT-024", "D-53")
def test_requirements_pinned_without_psycopg2() -> None:
    lines = [
        line.strip()
        for line in (ROOT / "backend/requirements.txt").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert all("==" in line for line in lines)
    assert not any("psycopg2" in line for line in lines)
    assert sum(line.startswith("psycopg[binary]==3.") for line in lines) == 1
