"""Raw-store repository is insert-only (TRD 06 DB-001..DB-004; FEAT-010).

The database half of FEAT-010-AC-06 (two arrivals with one `session_id` get increasing
`arrival_seq`) is in tests/integration/db/test_raw_store.py.
"""

from __future__ import annotations

from typing import Any

import pytest

from backend.repositories.raw_session_repository import RawSessionRepository

pytestmark = pytest.mark.unit


class FakeSession:
    def __init__(self) -> None:
        self.statements: list[Any] = []

    def execute(self, statement: Any) -> Any:
        self.statements.append(statement)

        class Result:
            def one(self) -> Any:
                class Row:
                    id = "id"
                    arrival_seq = 1

                return Row()

        return Result()


@pytest.mark.req("DB-001", "D-09", "FEAT-010-AC-06")
@pytest.mark.parametrize("column", ["id", "arrival_seq", "received_at"])
def test_database_assigned_columns_are_refused(column: str) -> None:
    session = FakeSession()
    with pytest.raises(ValueError, match="assigned by the database"):
        RawSessionRepository(session).insert({column: 1, "session_id": "S1"})  # type: ignore[arg-type]
    assert session.statements == []


@pytest.mark.req("DB-004", "FEAT-010-FR-04")
def test_repository_has_no_update_or_delete() -> None:
    public = {name for name in dir(RawSessionRepository) if not name.startswith("_")}
    assert public == {"insert", "by_resident", "by_session_id", "exists_session_id"}


@pytest.mark.req("DB-001", "FEAT-010-AC-06")
def test_insert_returns_id_and_sequence() -> None:
    session = FakeSession()
    raw_id, seq = RawSessionRepository(session).insert({"session_id": "S1"})  # type: ignore[arg-type]
    assert raw_id == "id"
    assert isinstance(seq, int)
    sql = str(session.statements[0])
    assert "RETURNING raw_sessions.id, raw_sessions.arrival_seq" in sql
    assert "arrival_seq" not in sql.split("RETURNING")[0]
