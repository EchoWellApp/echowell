"""Pytest conventions (TRD 13 TST-006, TST-010)."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
LEVELS = {"unit", "integration", "contract", "validation", "security", "performance", "smoke"}
EXPECTED = LEVELS | {"slow", "authenticated", "budget", "req"}


@pytest.mark.req("TST-006")
def test_tst_006_marker_list_is_exact_and_strict() -> None:
    options = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["pytest"]["ini_options"]
    registered = {m.split(":")[0].split("(")[0] for m in options["markers"]}
    assert registered == EXPECTED
    assert "--strict-markers" in options["addopts"]
    assert not (ROOT / "pytest.ini").exists()


@pytest.mark.req("TST-006", "TST-010")
def test_tst_010_every_test_module_named_and_marked() -> None:
    for path in (ROOT / "tests").rglob("*.py"):
        if path.name in ("conftest.py", "__init__.py") or not path.name.startswith("test_"):
            continue
        tree = ast.parse(path.read_text())
        marks = {
            node.attr
            for stmt in tree.body
            if isinstance(stmt, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "pytestmark" for t in stmt.targets)
            for node in ast.walk(stmt.value)
            if isinstance(node, ast.Attribute)
        }
        assert len(marks & LEVELS) == 1, path
