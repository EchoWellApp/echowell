"""Migration framework (TRD 06 DB-026..DB-030; TRD 20 PGS-002, PGS-016, PGS-023; FEAT-008)."""

from __future__ import annotations

import pytest

from tests.integration.conftest import RoundTrip
from tests.integration.db_support import ROOT, PgUrls, alembic

VERSIONS = ROOT / "backend" / "alembic" / "versions"

pytestmark = pytest.mark.integration


@pytest.mark.req("TST-040", "DEP-024", "FEAT-008-AC-01", "DB-029")
def test_tst_040_upgrade_downgrade_upgrade_round_trip(migrated: RoundTrip) -> None:
    assert (migrated.upgrade, migrated.downgrade, migrated.upgrade_again) == (0, 0, 0)
    assert "Running upgrade 0001 -> 0002" in migrated.output
    assert "Running upgrade 0002 -> 0003" in migrated.output
    assert "Running downgrade 0002 -> 0001" in migrated.output


@pytest.mark.req("DB-027", "FEAT-008-AC-06", "FEAT-008-FR-08")
def test_single_head_with_sequential_revisions(pg_urls: PgUrls, migrated: RoundTrip) -> None:
    numbers = sorted(path.name[:4] for path in VERSIONS.glob("[0-9][0-9][0-9][0-9]_*.py"))
    assert numbers == [f"{n:04d}" for n in range(1, len(numbers) + 1)]
    heads = alembic(pg_urls, "heads")
    assert heads.returncode == 0
    assert heads.stdout.split() == [numbers[-1], "(head)"]


@pytest.mark.req("PGS-023", "DB-012", "AC-PGS-11", "FEAT-008-AC-06", "FEAT-009-AC-07")
def test_alembic_check_reports_no_difference(pg_urls: PgUrls, migrated: RoundTrip) -> None:
    result = alembic(pg_urls, "check")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "No new upgrade operations detected" in result.stdout + result.stderr
