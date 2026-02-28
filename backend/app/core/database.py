from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import DATA_DIR, DATABASE_URL


class Base(DeclarativeBase):
    pass


engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    """Create DB directory and all tables."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


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
