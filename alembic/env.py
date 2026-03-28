import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection

from alembic import context

# Make backend/ importable so models can be loaded
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import app.models.move_log  # noqa: E402, F401 — registers MoveLog
import app.models.rule  # noqa: E402, F401 — registers Rule, RuleCondition
import app.models.setting  # noqa: E402, F401 — registers model with Base.metadata
from app.core.config import DB_PATH  # noqa: E402
from app.core.database import Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Use a plain sync SQLite URL — Alembic is a schema tool, not the hot path.
# Avoids asyncio.run() inside asyncio.to_thread() which caused aiosqlite
# file-lock contention on startup (blocked seed_defaults on the main loop).
_SYNC_URL = f"sqlite:///{DB_PATH}"


def run_migrations_offline() -> None:
    context.configure(
        url=_SYNC_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(_SYNC_URL, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        do_run_migrations(connection)
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
