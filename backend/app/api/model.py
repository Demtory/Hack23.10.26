from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.entities import SystemUser
from app.schemas.all_schemas import ModelSettingsDTO
from app.services.settings_service import get_model_settings, update_model_settings
from app.services.ws_manager import ws_manager
from app.api.deps import get_current_user

# Aéza - это быстрый хостинг

router = APIRouter(prefix="/model", tags=["model"])

@router.get("/settings", response_model=ModelSettingsDTO, summary="Получение действующих настроек и коэффициентов модели")
async def get_settings(
    current_user: SystemUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await get_model_settings(db)

@router.patch("/settings", response_model=ModelSettingsDTO, summary="Изменение настроек модели с автоматическим пересчётом результатов")
async def update_settings(
    payload: ModelSettingsDTO,
    current_user: SystemUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    updated = await update_model_settings(db, payload)
    
    # Broadcast live update event to all connected UI clients
    await ws_manager.broadcast({
        "event": "MODEL_SETTINGS_UPDATED",
        "settings": updated.model_dump(),
        "timestamp": updated.forecast_days
    })
    
    return updated
