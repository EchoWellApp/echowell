"""Alembic environment (TRD 06 DB-027, DB-028; TRD 20 §4.3; TRD 15 DEP-024, DEP-064; D-72, D-90).

Connects only with DATABASE_MIGRATION_URL, runs `SET ROLE echowell_migrator` and the DB-028
timeouts (`backend.core.db.MIGRATOR_SETUP`), and holds advisory lock 0x45434857 for the whole
upgrade so concurrent starts cannot apply a migration twice (DEP-064). The lock is taken with
`pg_advisory_xact_lock` inside the single migration transaction, so it is released at commit and
no session-level lock is held (DB-021, TRD 24 D-120).
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import text

from backend.core.config import load_settings_or_exit
from backend.core.db import MIGRATION_LOCK_KEY, migrator_connection
from backend.models import Base

target_metadata = Base.metadata
if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name, disable_existing_loggers=False)


def run_migrations_offline() -> None:
    settings = load_settings_or_exit(operator=True)
    context.configure(
        url=settings.migration_url.get_secret_value(),
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    settings = load_settings_or_exit(operator=True)
    with migrator_connection(settings) as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            connection.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": MIGRATION_LOCK_KEY}
            )
            context.run_migrations()
        connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
