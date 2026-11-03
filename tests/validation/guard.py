"""No skip, xfail or retry under `tests/validation/` (TRD 13 TST-083; FEAT-058-FR-14).

Loaded by `tests/validation/conftest.py`. A validation test that is skipped, xfailed or rerun
makes the session exit non-zero, so the gate can never pass by leaving a case out.
"""

from __future__ import annotations

import pytest

FORBIDDEN_MARKS = ("skip", "skipif", "xfail", "flaky")
_found: list[str] = []


def _validation(nodeid: str) -> bool:
    return "tests/validation/" in nodeid.replace("\\", "/") or nodeid.startswith("test_")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if _validation(item.nodeid):
            for name in FORBIDDEN_MARKS:
                if item.get_closest_marker(name) is not None:
                    _found.append(f"{item.nodeid}: marked {name}")


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if not _validation(report.nodeid):
        return
    if report.skipped:
        kind = "xfailed" if hasattr(report, "wasxfail") else "skipped"
        _found.append(f"{report.nodeid}: {kind}")
    elif report.outcome == "rerun":
        _found.append(f"{report.nodeid}: retried")


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if _found:
        print("\nTST-083: validation tests may not be skipped, xfailed or retried:")
        for line in dict.fromkeys(_found):
            print(f"  {line}")
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
