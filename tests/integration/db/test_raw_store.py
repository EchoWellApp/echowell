"""Immutable ingest store (TRD 20 PGS-009, PGS-011; FEAT-010).

AC-PGS-01 and AC-PGS-02 (UPDATE, DELETE, TRUNCATE refused) are in test_schema_behaviour.py.
"""

from __future__ import annotations

import pytest
from sqlalchemy import insert, text

from backend.models import FEATURE_KEYS, RawSession
from backend.repositories.raw_session_repository import RawSessionRepository
from tests.integration.db_support import outcome
from tests.integration.world import World

pytestmark = pytest.mark.integration

CHECK = "23514"


@pytest.mark.req("PGS-011", "FEAT-010-AC-04")
@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("audio_quality_flag", "bad"),
        ("number_of_pauses", -1),
        ("pause_fraction", 1.5),
        ("mean_f0_hz", 0),
        ("phrase_id", "P" * 17),
    ],
)
def test_raw_session_checks(world: World, column: str, value: object) -> None:
    good = world.raw_values("R01", "D01")
    assert outcome(world.session, insert(RawSession).values(**good)) == "ok"
    bad = world.raw_values("R01", "D01", **{column: value})
    assert outcome(world.session, insert(RawSession).values(**bad)) == CHECK


@pytest.mark.req("PGS-009", "FEAT-010-AC-05")
def test_feature_columns_follow_the_src_05_header(world: World) -> None:
    columns = dict(
        world.session.execute(
            text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = 'raw_sessions' ORDER BY ordinal_position"
            )
        ).all()
    )
    names = list(columns)
    start = names.index("loudness_dbfs")
    assert tuple(names[start : start + 19]) == FEATURE_KEYS
    assert columns["number_of_pauses"] == "integer"  # FEATURE_KEYS is the SRC-05 order


@pytest.mark.req("FR-028", "FR-010", "FEAT-010-AC-07")
def test_rejection_and_batch_checks(world: World) -> None:
    rejection = "INSERT INTO ingest_rejections (raw_body, errors) VALUES ('{}', '[]')"
    assert outcome(world.session, rejection) == CHECK
    batch = "INSERT INTO ingest_batches (source, uploaded_by) VALUES ('csv_upload', NULL)"
    assert outcome(world.session, batch) == CHECK


@pytest.mark.req("DB-001", "D-09", "AGT-043", "FEAT-010-AC-06")
def test_same_session_id_twice_gets_increasing_arrival_seq(world: World) -> None:
    repo = RawSessionRepository(world.session)
    first = repo.insert(world.raw_values("R01", "D01", session_id="S-dup"))
    second = repo.insert(world.raw_values("R01", "D01", session_id="S-dup"))
    assert first[0] != second[0]
    assert second[1] > first[1]
    assert [r.arrival_seq for r in repo.by_session_id("S-dup")] == [first[1], second[1]]
