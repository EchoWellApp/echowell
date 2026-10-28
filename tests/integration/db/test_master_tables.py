"""Master data and identity tables (TRD 20 PGS-015, PGS-034, PGS-035, PGS-037; FEAT-009)."""

from __future__ import annotations

import pytest
from sqlalchemy import Connection, text

from tests.integration.db_support import outcome
from tests.integration.world import World

pytestmark = pytest.mark.integration

CHECK, UNIQUE, EXCLUSION = "23514", "23505", "23P01"
GOOD_HASH = "$argon2id$v=19$m=65536,t=3,p=4$c2FsdA$aGFzaA"


@pytest.mark.req("AC-PGS-08", "PGS-015", "FEAT-009-AC-02")
def test_shared_device_allowed_and_overlap_rejected(world: World) -> None:
    stmt = text(
        "INSERT INTO device_assignments (resident_id, device_id, valid_from, valid_to) "
        "VALUES (:r, :d, :start, :end)"
    )
    r07, d07 = world.residents["R07"], world.devices["D07"]
    overlapping = {"r": r07, "d": d07, "start": "2026-10-10", "end": "2026-10-14"}
    assert outcome(world.session, stmt, overlapping) == EXCLUSION
    before = {"r": r07, "d": d07, "start": "2026-09-01", "end": "2026-09-30"}
    assert outcome(world.session, stmt, before) == "ok"


def _user(email: str, password_hash: str = GOOD_HASH) -> tuple[str, dict[str, str]]:
    return (
        "INSERT INTO users (email, display_name, password_hash, role) "
        "VALUES (:email, 'User', :hash, 'clinician')",
        {"email": email, "hash": password_hash},
    )


@pytest.mark.req("PGS-034", "FEAT-009-AC-03")
def test_user_email_and_hash_constraints(app_conn: Connection) -> None:
    assert outcome(app_conn, *_user("Admin@Example.com")) == CHECK
    assert outcome(app_conn, *_user("admin@example.com", "$2b$12$bcrypt")) == CHECK
    assert outcome(app_conn, *_user("admin@example.com")) == "ok"
    assert outcome(app_conn, *_user("admin@example.com")) == UNIQUE


@pytest.mark.req("PGS-035", "FEAT-009-AC-04")
@pytest.mark.parametrize(
    ("key_hash", "scopes"),
    [
        ("a" * 63, ["ingest:write"]),
        ("A" * 64, ["ingest:write"]),
        ("a" * 64, []),
        ("a" * 64, ["admin"]),
    ],
)
def test_api_key_constraints(app_conn: Connection, key_hash: str, scopes: list[str]) -> None:
    stmt = "INSERT INTO api_keys (name, key_hash, scopes) VALUES ('k', :h, :s)"
    assert outcome(app_conn, stmt, {"h": key_hash, "s": scopes}) == CHECK
    assert outcome(app_conn, stmt, {"h": "b" * 64, "s": ["ingest:write", "pipeline:run"]}) == "ok"


@pytest.mark.req("PGS-037", "FEAT-009-AC-05")
def test_withdrawn_needs_a_date(world: World) -> None:
    params = {"r": world.residents["R08"]}
    assert (
        outcome(world.session, "UPDATE residents SET status = 'withdrawn' WHERE id = :r", params)
        == CHECK
    )
    ok = "UPDATE residents SET status = 'withdrawn', withdrawn_on = '2026-10-20' WHERE id = :r"
    assert outcome(world.session, ok, params) == "ok"


@pytest.mark.req("DB-035", "SEC-120", "DME-020", "FEAT-009-AC-08")
def test_no_identifying_columns(app_conn: Connection) -> None:
    rows = app_conn.execute(
        text(
            "SELECT table_name, column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' "
            "AND column_name ~ '(name|birth|phone|address|email|audio)'"
        )
    ).all()
    allowed = {
        ("users", "email"),
        ("users", "display_name"),  # staff display name (PGS-034), not a resident identifier
        ("facilities", "name"),
        ("api_keys", "name"),
        ("ingest_batches", "filename"),
        ("raw_sessions", "audio_quality_flag"),  # the only audio-related column (FEAT-010-FR-12)
    }
    assert set(map(tuple, rows)) <= allowed
