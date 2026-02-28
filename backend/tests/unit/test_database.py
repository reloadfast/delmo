"""Unit tests for database init, seed, and get_db."""
import pytest
from app.core.config import DEFAULT_SETTINGS
from app.core.database import get_db, init_db, seed_defaults
from app.models.setting import Setting
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.unit


async def test_init_db_creates_tables(db: AsyncSession) -> None:
    """init_db() should be idempotent — calling it on an existing DB is safe."""
    # Tables already exist from the conftest fixture; calling again must not raise
    await init_db()


async def test_seed_defaults_idempotent() -> None:
    """seed_defaults() inserts DEFAULT_SETTINGS keys; safe to call multiple times."""
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import select

    # First call: populates keys
    await seed_defaults()
    # Second call: must not raise (ON CONFLICT DO NOTHING)
    await seed_defaults()

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Setting))
        existing_keys = {s.key for s in result.scalars().all()}

    for key in DEFAULT_SETTINGS:
        assert key in existing_keys, f"Expected default key '{key}' to be seeded"


async def test_get_db_yields_session() -> None:
    """get_db() yields an AsyncSession."""
    gen = get_db()
    session = await gen.__anext__()
    assert isinstance(session, AsyncSession)
    # Clean up
    try:
        await gen.aclose()
    except StopAsyncIteration:
        pass


async def test_setting_repr(db: AsyncSession) -> None:
    """Setting.__repr__ returns the expected string."""
    s = Setting(key="test_key", value="test_value")
    assert "test_key" in repr(s)
    assert "test_value" in repr(s)


async def test_dev_placeholder_route(client: object) -> None:
    """Non-API routes return the dev placeholder when frontend is not built."""
    from httpx import AsyncClient
    assert isinstance(client, AsyncClient)
    resp = await client.get("/some/unknown/path")
    # In test environment, frontend/dist doesn't exist → dev placeholder
    assert resp.status_code == 200
