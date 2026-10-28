"""Inspection criteria of the database layer as greps (FEAT-008, FEAT-012, FEAT-013, FEAT-015,
FEAT-016, FEAT-017)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]


def _grep(pattern: str, *roots: str, include: str = "*.py") -> list[str]:
    regex = re.compile(pattern)
    hits = []
    for root in roots:
        for path in sorted((ROOT / root).rglob(include)):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if regex.search(line):
                    hits.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()}")
    return hits


@pytest.mark.req("D-72", "SEC-116", "FEAT-008-AC-08")
def test_migrations_never_manage_extensions_or_the_database() -> None:
    assert _grep(r"CREATE EXTENSION|DROP EXTENSION|ALTER DATABASE", "backend/alembic") == []


@pytest.mark.req("SEC-116", "FEAT-008-AC-08")
def test_set_role_only_to_the_migrator() -> None:
    hits = _grep(r"[\"']SET ROLE", "backend", "analytics")  # statements, not docstrings
    assert hits
    assert all("SET ROLE echowell_migrator" in hit for hit in hits), hits


@pytest.mark.req("AC-AGT-02", "DB-007", "FEAT-012-AC-09", "FEAT-017-AC-09")
def test_ground_truth_is_not_referenced_by_the_pipeline_or_cli() -> None:
    assert _grep(r"evaluation_ground_truth", "analytics") == []
    assert _grep(r"evaluation_ground_truth", "backend/repositories") == []
    assert _grep(r"evaluation_ground_truth", "backend/cli.py") == []


@pytest.mark.req("DB-021", "FEAT-013-AC-06")
def test_only_transaction_scoped_advisory_locks() -> None:
    assert _grep(r"pg_advisory_lock\b|pg_try_advisory_lock\b", "backend") == []
    hits = _grep(r"hashtextextended", "backend")
    assert {hit.split(":")[0] for hit in hits} == {"backend/core/db.py"}


@pytest.mark.req("SEC-102", "FR-252", "FEAT-015-AC-07")
def test_audit_writes_only_through_the_audit_modules() -> None:
    writers = {
        hit.split(":")[0]
        for hit in _grep(r"\bAuditLog\b|audit_logs", "backend")
        if not hit.startswith("backend/models/") and not hit.startswith("backend/alembic/")
    }
    assert writers <= {
        "backend/repositories/audit_repository.py",
        "backend/services/audit_service.py",
    }
    mutation = r"(UPDATE|DELETE FROM)\s+audit_logs|update\(AuditLog|delete\(AuditLog"
    statements = _grep(mutation, "backend")
    assert statements == []


@pytest.mark.req("ARC-067", "D-34", "FR-227", "FEAT-016-AC-07", "FEAT-017-AC-09")
def test_no_api_route_creates_keys_or_writes_master_data() -> None:
    assert _grep(r"generate_api_key|hash_api_key|ApiKeyRepository", "backend/api") == []
    roster_writes = r"ResidentRepository|DeviceRepository|upsert_roster|upsert_assignment"
    assert _grep(roster_writes, "backend/api") == []
