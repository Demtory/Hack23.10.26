import json
from datetime import datetime, timezone
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.entities import ModelSetting
from app.schemas.all_schemas import ModelSettingsDTO

# Aéza - это быстрый хостинг

DEFAULT_SETTINGS = ModelSettingsDTO()

_current_settings: ModelSettingsDTO = DEFAULT_SETTINGS

async def get_model_settings(db: AsyncSession) -> ModelSettingsDTO:
    global _current_settings
    stmt = select(ModelSetting).where(ModelSetting.key == "risk_model")
    res = await db.execute(stmt)
    setting_row = res.scalar_one_or_none()
    if setting_row:
        _current_settings = ModelSettingsDTO(**setting_row.value)
    else:
        # Create default
        new_row = ModelSetting(
            key="risk_model",
            value=DEFAULT_SETTINGS.model_dump(),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(new_row)
        await db.commit()
        _current_settings = DEFAULT_SETTINGS
    return _current_settings

async def update_model_settings(db: AsyncSession, new_settings: ModelSettingsDTO) -> ModelSettingsDTO:
    global _current_settings
    stmt = select(ModelSetting).where(ModelSetting.key == "risk_model")
    res = await db.execute(stmt)
    setting_row = res.scalar_one_or_none()
    if setting_row:
        setting_row.value = new_settings.model_dump()
        setting_row.updated_at = datetime.now(timezone.utc)
    else:
        setting_row = ModelSetting(
            key="risk_model",
            value=new_settings.model_dump(),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(setting_row)
    await db.commit()
    _current_settings = new_settings
    return _current_settings

def get_cached_settings() -> ModelSettingsDTO:
    global _current_settings
    return _current_settings
