from fastapi import APIRouter, Depends
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.entities import Account, Service, SystemUser
from app.schemas.all_schemas import AnalyticsSummaryDTO
from app.services.settings_service import get_model_settings
from app.services.risk_engine import calculate_customer_risk, build_analytics_summary
from app.api.deps import get_current_user

# Aéza - это быстрый хостинг

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/summary", response_model=AnalyticsSummaryDTO, summary="Получение сводных показателей риска и денежной оценки потенциальных потерь")
async def get_analytics_summary(
    current_user: SystemUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    settings = await get_model_settings(db)
    
    stmt = (
        select(Account)
        .options(
            selectinload(Account.services).selectinload(Service.transactions)
        )
    )
    res = await db.execute(stmt)
    accounts = res.scalars().all()
    
    # Все услуги для факта оттока
    all_services_stmt = select(Service)
    s_res = await db.execute(all_services_stmt)
    all_services = s_res.scalars().all()
    
    assessments = []
    for acc in accounts:
        all_txs = []
        for s in acc.services:
            all_txs.extend(s.transactions)
        ass = calculate_customer_risk(
            account=acc,
            services=acc.services,
            transactions=all_txs,
            settings=settings
        )
        assessments.append(ass)
        
    summary = build_analytics_summary(
        assessments=assessments,
        all_services=all_services
    )
    return summary
