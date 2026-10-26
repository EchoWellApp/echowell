"""analytics/ imports nothing from backend, database, HTTP, environment or randomness modules
(TRD 07 ANL-002, ANL-005, TRD 01 ARC-041, AC-ARC-01; backs up the lint-imports contract)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
FORBIDDEN = {"backend", "tests", "sqlalchemy", "psycopg", "fastapi", "httpx", "requests", "os"}
FORBIDDEN |= {"random", "pandas", "openpyxl"}


def imported_roots(path: Path) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


@pytest.mark.req("ANL-002", "ANL-005", "AC-ARC-01", "TST-021")
def test_analytics_imports_are_allowed() -> None:
    for path in (ROOT / "analytics").glob("*.py"):
        assert imported_roots(path) & FORBIDDEN == set(), path
