"""Provisioning, roles and enum types (TRD 20 PGS-001..PGS-005, PGS-040; DME-003; FEAT-008)."""

from __future__ import annotations

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError

from backend.models import PG_ENUMS
from tests.integration.db_support import sqlstate

pytestmark = pytest.mark.integration

GROUPS = ("echowell_app", "echowell_migrator", "echowell_readonly")


@pytest.mark.req("PGS-001", "PGS-002", "FEAT-008-AC-02")
def test_extensions_timezone_and_server_version(app_conn: Connection) -> None:
    extensions = app_conn.execute(text("SELECT extname FROM pg_extension ORDER BY 1")).scalars()
    assert list(extensions) == ["btree_gist", "pgcrypto", "plpgsql"]
    assert app_conn.execute(text("SHOW timezone")).scalar_one() == "UTC"
    version = int(app_conn.execute(text("SHOW server_version_num")).scalar_one())
    assert 160000 <= version < 170000


@pytest.mark.req("PGS-004", "PGS-040", "FEAT-008-FR-03", "FEAT-008-AC-04")
def test_group_and_login_roles(app_conn: Connection) -> None:
    rows = app_conn.execute(
        text(
            "SELECT rolname, rolcanlogin FROM pg_roles WHERE rolname LIKE 'echowell\\_%' "
            "ORDER BY rolname"
        )
    ).all()
    roles = dict(rows)
    for group in GROUPS:
        assert roles[group] is False
        assert roles[f"{group}_login"] is True
    memberships = app_conn.execute(
        text(
            "SELECT m.rolname, g.rolname FROM pg_auth_members a "
            "JOIN pg_roles m ON m.oid = a.member JOIN pg_roles g ON g.oid = a.roleid "
            "WHERE m.rolname LIKE 'echowell\\_%\\_login'"
        )
    ).all()
    assert sorted(memberships) == sorted((f"{g}_login", g) for g in GROUPS)


@pytest.mark.req("PGS-040", "SEC-114", "AC-PGS-14", "FEAT-008-AC-04")
def test_app_login_cannot_become_readonly(app_conn: Connection) -> None:
    with pytest.raises(DBAPIError) as caught, app_conn.begin_nested():
        app_conn.execute(text("SET ROLE echowell_readonly"))
    assert sqlstate(caught.value) == "42501"


@pytest.mark.req("PGS-003", "FEAT-008-FR-04")
def test_every_table_is_owned_by_the_migrator_group(app_conn: Connection) -> None:
    owners = app_conn.execute(
        text("SELECT DISTINCT tableowner FROM pg_tables WHERE schemaname = 'public'")
    ).scalars()
    assert set(owners) == {"echowell_migrator"}
    count = app_conn.execute(
        text("SELECT count(*) FROM pg_tables WHERE schemaname = 'public'")
    ).scalar_one()
    assert count == 25  # the 24 tables of TRD 20 §4.6 and alembic_version (PGS-006)


@pytest.mark.req("PGS-005", "DME-003", "FEAT-008-AC-05")
def test_enum_labels_and_order_match_trd_20_and_python(app_conn: Connection) -> None:
    rows = app_conn.execute(
        text(
            "SELECT t.typname, e.enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
            "ORDER BY t.typname, e.enumsortorder"
        )
    ).all()
    database: dict[str, list[str]] = {}
    for name, label in rows:
        database.setdefault(name, []).append(label)
    python = {enum.name: list(enum.enums) for enum in PG_ENUMS}
    assert database == python
    assert len(database) == 15
