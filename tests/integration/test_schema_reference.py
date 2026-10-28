"""Schema reference: `database/schema.sql` equals a dump of the migrated database (TRD 20 PGS-016,
PGS-017; AC-PGS-11; FEAT-008-AC-07).

Applies the normalisation of `scripts/dump_schema.sh`; on a difference, regenerate the file with
that script and commit it with the migration.
"""

from __future__ import annotations

import difflib
import re
import shutil
import subprocess

import pytest

from tests.integration.conftest import RoundTrip
from tests.integration.db_support import ROOT, PgUrls, libpq

pytestmark = pytest.mark.integration

SCHEMA = ROOT / "database" / "schema.sql"
DROPPED = re.compile(
    r"^(SET |SELECT pg_catalog\.set_config|\\restrict |\\unrestrict |-- Dumped (from|by) )"
)


def _pg_dump() -> tuple[str, int] | None:
    binary = shutil.which("pg_dump")
    if binary is None:
        return None
    version = subprocess.run(  # noqa: S603 - resolved binary, fixed argument
        [binary, "--version"], capture_output=True, text=True, check=True
    ).stdout
    match = re.search(r"(\d+)\.", version)
    return (binary, int(match.group(1))) if match else None


def normalise(dump: str) -> str:
    """`grep -v` of the preamble lines, then `cat -s` (squeeze repeated blank lines)."""
    lines: list[str] = []
    for line in dump.splitlines():
        if DROPPED.match(line):
            continue
        if line == "" and lines and lines[-1] == "":
            continue
        lines.append(line)
    return "\n".join(lines) + "\n"


@pytest.mark.req("PGS-016", "PGS-017", "AC-PGS-11", "FEAT-008-AC-07")
def test_schema_sql_matches_the_migrated_database(pg_urls: PgUrls, migrated: RoundTrip) -> None:
    found = _pg_dump()
    if found is None or found[1] < 16:
        pytest.skip("pg_dump 16 or later is needed for the schema reference (PGS-016)")
    dump = subprocess.run(  # noqa: S603 - fixed arguments
        [found[0], "--schema-only", "--no-owner", "--no-comments",
         f"--dbname={libpq(pg_urls.migrator)}"],
        capture_output=True, text=True, check=True, timeout=120,
    ).stdout  # fmt: skip
    actual = normalise(dump)
    expected = SCHEMA.read_text(encoding="utf-8")
    if actual != expected:
        diff = "".join(
            difflib.unified_diff(
                expected.splitlines(keepends=True), actual.splitlines(keepends=True),
                "database/schema.sql", "migrated database", n=2,
            )
        )  # fmt: skip
        pytest.fail("database/schema.sql is stale; run scripts/dump_schema.sh\n" + diff[:4000])
