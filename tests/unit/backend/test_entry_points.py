"""Nightly job and operator CLI entry points share the startup guards (TRD 21 ENV-002, ENV-010,
ENV-053; TRD 25 AGT-015; FEAT-003)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from backend import cli

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.req("ENV-010", "AGT-015", "ENV-002")
def test_nightly_run_refuses_test_profile_in_production() -> None:
    env = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME")}
    env |= {
        "APP_ENV": "production",
        "PIPELINE_PROFILE": "test_v0_1",
        "DATABASE_URL": "postgresql://app:pw-1@db.example.org/echowell?sslmode=require",
        "CORS_ORIGINS": "https://echowell-und.netlify.app",
        "FACILITY_NAME": "Edgewood",
    }
    result = subprocess.run(  # noqa: S603 - fixed interpreter and arguments
        [sys.executable, "-m", "backend.jobs.nightly_run"],
        cwd=ROOT, env=env, capture_output=True, text=True, check=False, timeout=60,
    )  # fmt: skip
    assert result.returncode == 1
    assert "PIPELINE_PROFILE" in result.stderr


@pytest.mark.req("ENV-053")
def test_cli_without_command_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main([]) == 0
    assert "python -m backend.cli" in capsys.readouterr().out
