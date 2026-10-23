"""Alembic environment (TRD 06, TRD 20 §4.3, TRD 15 DEP-024; TRD 24 D-72, D-90).

Connects with DATABASE_MIGRATION_URL (role echowell_migrator) and runs `SET ROLE echowell_migrator`
so that every object is owned by the group role. The migrations themselves start in FEAT-008; until
then `alembic upgrade head` is a no-op that proves the migrator login works.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import text

from backend.core.config import load_settings_or_exit
from backend.core.db import get_engine
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
    with get_engine(settings.migration_url).connect() as connection:
        connection.execute(text("SET ROLE echowell_migrator"))
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        connection.commit()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
