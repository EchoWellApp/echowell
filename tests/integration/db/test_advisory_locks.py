"""Transaction-scoped advisory locks (TRD 06 DB-021; D-62; FEAT-013-AC-05)."""

from __future__ import annotations

import threading
import time

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from backend.core import db
from tests.integration.conftest import RoundTrip
from tests.integration.db_support import PgUrls

pytestmark = pytest.mark.integration


@pytest.mark.req("DB-021", "D-62", "FEAT-013-AC-05")
def test_second_transaction_waits_for_the_first(pg_urls: PgUrls, migrated: RoundTrip) -> None:
    engine = create_engine(pg_urls.app, poolclass=NullPool)
    acquired = threading.Event()
    waited: list[float] = []

    def second() -> None:
        with Session(engine) as session, session.begin():
            started = time.monotonic()
            db.lock_xact(session, "resident", "R02")
            waited.append(time.monotonic() - started)

    try:
        with Session(engine) as first, first.begin():
            db.lock_xact(first, "resident", "R02")
            acquired.set()
            worker = threading.Thread(target=second)
            worker.start()
            time.sleep(0.5)
            assert worker.is_alive(), "B must block while A holds the lock"
        worker.join(timeout=5)
        assert not worker.is_alive()
        assert len(waited) == 1
        assert waited[0] >= 0.4
    finally:
        engine.dispose()


@pytest.mark.req("DB-021", "FEAT-013-FR-05")
def test_different_keys_do_not_block(pg_urls: PgUrls, migrated: RoundTrip) -> None:
    engine = create_engine(pg_urls.app, poolclass=NullPool)
    try:
        with Session(engine) as first, first.begin():
            db.lock_residents(first, ["R03", "R02"])
            with Session(engine) as second, second.begin():
                second.execute(text("SET LOCAL lock_timeout = '1s'"))
                db.lock_xact(second, "resident", "R04")
                db.lock_xact(second, "session", "R02")  # same value, other namespace
    finally:
        engine.dispose()


@pytest.mark.req("DB-021", "FEAT-013-AC-05")
def test_lock_is_released_at_commit(pg_urls: PgUrls, migrated: RoundTrip) -> None:
    engine = create_engine(pg_urls.app, poolclass=NullPool)
    try:
        with Session(engine) as session:
            with session.begin():
                db.lock_xact(session, "nightly", "2026-10-30")
            held = session.execute(
                text(
                    "SELECT count(*) FROM pg_locks "
                    "WHERE locktype = 'advisory' AND pid = pg_backend_pid()"
                )
            ).scalar_one()
            assert held == 0
    finally:
        engine.dispose()
