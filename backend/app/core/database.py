import asyncio
import sqlite3
from collections.abc import AsyncGenerator
from pathlib import Path

from alembic.config import Config
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from alembic import command
from app.core.config import DATA_DIR, DATABASE_URL, DB_PATH


class Base(DeclarativeBase):
    pass


engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


def _stamp_if_unversioned(cfg: Config) -> None:
    """Stamp a pre-Alembic DB with the correct revision so upgrade can proceed.

    If the DB has tables but no alembic_version table, it was created by the
    old Base.metadata.create_all path.  We detect the schema state and stamp
    at the matching revision so that upgrade head only applies genuinely
    missing migrations.
    """
    if not DB_PATH.exists():
        return  # fresh install — no stamp needed

    with sqlite3.connect(str(DB_PATH)) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }

    if not tables:
        return  # fresh DB — Alembic will create everything from scratch

    if "alembic_version" in tables:
        # Table exists — only skip stamp if it actually contains a version row.
        # An empty alembic_version means a previous upgrade was interrupted.
        with sqlite3.connect(str(DB_PATH)) as vc:
            if vc.execute("SELECT 1 FROM alembic_version LIMIT 1").fetchone():
                return  # already versioned; let upgrade handle the rest

    # Infer current revision from schema shape
    if "rules" not in tables:
        stamp = "0001"
    else:
        cols = {
            row[1]
            for row in sqlite3.connect(str(DB_PATH))
            .execute("PRAGMA table_info(rules)")
            .fetchall()
        }
        stamp = "0003" if "dry_run" in cols else "0002"

    command.stamp(cfg, stamp)


async def init_db() -> None:
    """Apply all pending Alembic migrations (creates or upgrades the DB)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _upgrade() -> None:
        cfg = Config(str(Path("alembic.ini")))
        _stamp_if_unversioned(cfg)
        command.upgrade(cfg, "head")

    # Run in a thread to keep disk I/O off the event loop.
    # env.py uses a plain sync sqlite:// engine — no asyncio.run() involved.
    await asyncio.to_thread(_upgrade)


async def seed_defaults() -> None:
    """Apply default settings if keys are missing."""
    from sqlalchemy.dialects.sqlite import insert

    from app.core.config import DEFAULT_SETTINGS
    from app.models.setting import Setting

    async with AsyncSessionLocal() as session:
        for key, value in DEFAULT_SETTINGS.items():
            stmt = (
                insert(Setting)
                .values(key=key, value=value)
                .on_conflict_do_nothing(index_elements=["key"])
            )
            await session.execute(stmt)
        await session.commit()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
