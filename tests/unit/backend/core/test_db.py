"""Connection layer (TRD 06 DB-021, DB-053; TRD 20 PGS-027; API-125; FEAT-013)."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from backend.core import db

pytestmark = pytest.mark.unit

REMOTE = "postgresql+psycopg://u:p@db.example.org/x"


@pytest.fixture(autouse=True)
def _fresh_engines() -> None:
    db._engine.cache_clear()


@pytest.mark.req("DB-053", "PGS-027", "ENV-011", "FEAT-013-AC-03")
@pytest.mark.parametrize("app_env", ["staging", "production"])
def test_remote_urls_need_tls_outside_local_and_test(app_env: str) -> None:
    with pytest.raises(db.InsecureDatabaseUrlError):
        db.create_engine_for(REMOTE, app_env=app_env)
    with pytest.raises(db.InsecureDatabaseUrlError):
        db.create_engine_for(REMOTE + "?sslmode=prefer", app_env=app_env)
    db.create_engine_for(REMOTE + "?sslmode=require", app_env=app_env)
    secret = SecretStr(REMOTE + "?connect_timeout=3&sslmode=verify-full")
    db.create_engine_for(secret, app_env=app_env)


@pytest.mark.req("ENV-011", "FEAT-013-AC-03")
@pytest.mark.parametrize("app_env", ["local", "test"])
def test_local_and_test_accept_plain_urls(app_env: str) -> None:
    db.create_engine_for("postgresql+psycopg://u:p@localhost:5432/echowell", app_env=app_env)


@pytest.mark.req("API-125", "FEAT-013-AC-04")
def test_pool_settings() -> None:
    engine = db.create_engine_for(REMOTE + "?sslmode=require", app_env="production")
    pool = engine.pool
    assert pool.size() == 5  # type: ignore[attr-defined]
    assert pool._max_overflow == 5  # type: ignore[attr-defined]
    assert pool._pre_ping is True
    assert pool._recycle == 300
    assert db.create_engine_for(REMOTE + "?sslmode=require", app_env="production") is engine


@pytest.mark.req("API-125", "FEAT-013-AC-04")
def test_connections_disable_prepared_statements(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_create_engine(url: str, **kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(db, "create_engine", fake_create_engine)
    db._engine("postgresql+psycopg://u:p@localhost/x")
    assert captured["connect_args"] == {"prepare_threshold": None, "connect_timeout": 5}
    assert (captured["pool_size"], captured["max_overflow"]) == (5, 5)
    assert (captured["pool_pre_ping"], captured["pool_recycle"]) == (True, 300)


@pytest.mark.req("DB-021", "FEAT-013-FR-04")
def test_advisory_key_expression_and_namespaces() -> None:
    clause = db.advisory_key("resident", "R02")
    assert clause.text == "hashtextextended('echowell:' || :namespace || ':' || :value, 0)"
    assert clause.compile().params == {"namespace": "resident", "value": "R02"}
    with pytest.raises(ValueError, match="unknown advisory-lock namespace"):
        db.advisory_key("residents", "R02")
    assert {"resident", "session", "device_alerts", "nightly"} == db.ADVISORY_NAMESPACES


@pytest.mark.req("DB-021", "D-62")
def test_lock_residents_sorts_and_deduplicates(monkeypatch: pytest.MonkeyPatch) -> None:
    taken: list[tuple[str, str]] = []
    monkeypatch.setattr(db, "lock_xact", lambda _s, ns, value: taken.append((ns, value)))
    db.lock_residents(object(), ["R03", "R01", "R03"])  # type: ignore[arg-type]
    assert taken == [("resident", "R01"), ("resident", "R03")]


@pytest.mark.req("PGS-019", "DB-028", "FEAT-008-FR-17")
def test_migrator_setup_statements() -> None:
    assert db.MIGRATOR_SETUP == (
        "SET ROLE echowell_migrator",
        "SET lock_timeout = '5s'",
        "SET statement_timeout = '120s'",
    )
    assert db.MIGRATION_LOCK_KEY == 0x45434857
