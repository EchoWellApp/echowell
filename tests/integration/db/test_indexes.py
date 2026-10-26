"""Indexes of TRD 20 §4.7 and FK-column coverage (PGS-038, DB-040..DB-047; FEAT-013).

Each §4.7 statement is re-created under a probe name inside a rolled-back transaction and its
`pg_get_indexdef` compared with the migrated index, so PostgreSQL normalises both sides.
"""

from __future__ import annotations

import re

import pytest
from sqlalchemy import Connection, text

from tests.integration.db_support import ROOT

pytestmark = pytest.mark.integration

TRD_20 = ROOT / "specs" / "TRD" / "20_PostgreSQL_Schema_Definition.md"
FK_COLUMNS = (
    "pipeline_run_id", "ingest_batch_id", "api_key_id", "acknowledged_by", "author_user_id",
    "alert_id", "device_id",
)  # fmt: skip


def section_4_7_statements() -> list[tuple[str, str]]:
    doc = TRD_20.read_text(encoding="utf-8")
    section = doc[doc.index("### 4.7 Indexes") : doc.index("### 4.8")]
    sql = section[section.index("```sql") + 6 : section.rindex("```")]
    sql = "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    named = []
    for statement in statements:
        match = re.match(r"CREATE (?:UNIQUE )?INDEX (\w+)", statement)
        assert match, statement
        named.append((match.group(1), " ".join(statement.split())))
    return named


@pytest.mark.req("PGS-038", "FEAT-013-AC-01")
def test_every_section_4_7_index_exists_as_defined(migrator_conn: Connection) -> None:
    statements = section_4_7_statements()
    assert len(statements) >= 50
    for name, statement in statements:
        actual = migrator_conn.execute(
            text("SELECT pg_get_indexdef(:name ::regclass)"), {"name": name}
        ).scalar_one()
        probe = f"probe_{name}"[:63]
        migrator_conn.execute(text(statement.replace(f"INDEX {name} ", f"INDEX {probe} ", 1)))
        expected = migrator_conn.execute(
            text("SELECT pg_get_indexdef(:name ::regclass)"), {"name": probe}
        ).scalar_one()
        assert actual == expected.replace(probe, name, 1), name


@pytest.mark.req("DB-047", "FEAT-013-AC-02")
def test_fk_columns_lead_an_index(migrator_conn: Connection) -> None:
    rows = migrator_conn.execute(
        text(
            "SELECT c.relname, a.attname FROM pg_attribute a "
            "JOIN pg_class c ON c.oid = a.attrelid JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind = 'r' AND a.attnum > 0 "
            "AND NOT a.attisdropped AND a.attname = ANY(:cols)"
        ),
        {"cols": list(FK_COLUMNS)},
    ).all()
    leading = set(
        migrator_conn.execute(
            text(
                "SELECT t.relname, a.attname FROM pg_index i "
                "JOIN pg_class t ON t.oid = i.indrelid "
                "JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = i.indkey[0]"
            )
        )
        .tuples()
        .all()
    )
    missing = sorted(set(map(tuple, rows)) - leading)
    assert missing == []
