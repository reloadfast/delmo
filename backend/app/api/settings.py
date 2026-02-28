from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.setting import Setting
from app.schemas.setting import SettingsPatch, SettingsResponse

router = APIRouter(tags=["settings"])


async def _all_settings(db: AsyncSession) -> dict[str, str]:
    result = await db.execute(select(Setting))
    return {s.key: s.value for s in result.scalars().all()}


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(db: AsyncSession = Depends(get_db)) -> SettingsResponse:
    """Return all persisted settings as a flat key→value map."""
    return SettingsResponse(data=await _all_settings(db))


@router.patch("/settings", response_model=SettingsResponse)
async def patch_settings(
    payload: SettingsPatch,
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Upsert one or more settings. Returns the full settings map after update."""
    for key, value in payload.updates.items():
        stmt = (
            insert(Setting)
            .values(key=key, value=value)
            .on_conflict_do_update(index_elements=["key"], set_={"value": value})
        )
        await db.execute(stmt)
    await db.commit()
    return SettingsResponse(data=await _all_settings(db))
