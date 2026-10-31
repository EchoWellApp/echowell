"""Concurrent arrivals of one `session_id` (TRD 06 DB-021 (b); TRD 10 ING-038; FEAT-025-AC-06).

Runs against a throwaway database with committed rows, because two requests must hold real,
separate transactions for the session advisory lock to order them.
"""

from __future__ import annotations

import threading
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from backend.api.deps import get_settings
from backend.cli import load_roster
from backend.core import security
from backend.main import create_app
from backend.repositories.api_key_repository import ApiKeyRepository
from tests.conftest import make_settings
from tests.integration.api.test_sessions import src05_record
from tests.integration.db_support import PgUrls
from tests.integration.world import ROSTER

pytestmark = pytest.mark.integration


@pytest.mark.req("AC-ING-09", "DB-021", "ING-038", "API-043", "FEAT-025-AC-06", "FEAT-025-FR-07")
def test_concurrent_posts_of_one_session_id(fresh_db: PgUrls) -> None:
    engine = create_engine(fresh_db.app, poolclass=NullPool)
    raw_key = security.generate_api_key()
    with Session(engine) as session, session.begin():
        load_roster(session, ROSTER)
        ApiKeyRepository(session).insert(
            name="concurrency", key_hash=security.hash_api_key(raw_key), scopes=["ingest:write"]
        )
    settings = make_settings(database_url=fresh_db.app, database_readonly_url=fresh_db.readonly)
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    record = src05_record("R09-20261021-01")
    barrier = threading.Barrier(2)
    results: list[dict[str, Any]] = []

    def post() -> None:
        with TestClient(app) as client:
            barrier.wait()
            response = client.post("/api/v1/sessions", json=record, headers={"X-API-Key": raw_key})
            results.append({"status": response.status_code, **response.json()})

    threads = [threading.Thread(target=post) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    engine.dispose()
    assert sorted(r["status"] for r in results) == [200, 201], results
    first = next(r for r in results if r["status"] == 201)
    duplicate = next(r for r in results if r["status"] == 200)
    assert duplicate["status_after_processing"] == "duplicate"
    assert first["status_after_processing"] == "usable"  # processed by the synchronous run
    assert first["arrival_seq"] < duplicate["arrival_seq"]
    with create_engine(fresh_db.app, poolclass=NullPool).connect() as conn:
        rows = conn.execute(text("SELECT arrival_seq FROM raw_sessions ORDER BY arrival_seq")).all()
    assert [r.arrival_seq for r in rows] == [first["arrival_seq"], duplicate["arrival_seq"]]
