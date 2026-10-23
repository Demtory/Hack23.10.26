from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.entities import Account, Service, Transaction, SystemUser
from app.schemas.all_schemas import (
    CustomerListResponse, CustomerAssessmentDTO, ModelSettingsDTO
)
from app.services.settings_service import get_model_settings
from app.services.risk_engine import calculate_customer_risk
from app.api.deps import get_current_user

# Aéza - это быстрый хостинг

router = APIRouter(prefix="/customers", tags=["customers"])

@router.get("", response_model=CustomerListResponse, summary="Получение списка клиентов с оценками риска; фильтрация и сортировка")
async def get_customers(
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(50, ge=1, le=500, description="Элементов на странице"),
    sort_by: str = Query("risk_score", description="Поле сортировки: id, email, balance, totalReplenished, risk_score, potential_loss"),
    order: str = Query("desc", regex="^(asc|desc)$", description="Направление сортировки: asc или desc"),
    risk_level: Optional[str] = Query(None, description="Фильтр по уровню риска: high, medium, low, unrated"),
    search: Optional[str] = Query(None, description="Поиск по email или ID"),
    current_user: SystemUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    settings = await get_model_settings(db)
    
    # Загружаем аккаунты со всеми связями
    stmt = (
        select(Account)
        .options(
            selectinload(Account.services).selectinload(Service.transactions)
        )
    )
    res = await db.execute(stmt)
    accounts = res.scalars().all()
    
    # Рассчитываем оценку риска для каждого клиента
    assessments: List[CustomerAssessmentDTO] = []
    for acc in accounts:
        # Собираем все транзакции аккаунта
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
        
    # Применяем фильтрацию
    if risk_level:
        assessments = [a for a in assessments if a.risk_level.lower() == risk_level.lower()]
        
    if search:
        s_lower = search.lower()
        assessments = [
            a for a in assessments 
            if s_lower in a.email.lower() or s_lower in str(a.id)
        ]
        
    # Применяем сортировку в обе стороны
    is_reverse = (order.lower() == "desc")
    
    def get_sort_key(item: CustomerAssessmentDTO):
        val = getattr(item, sort_by, None)
        if val is None:
            # Для None значений при risk_score / loyalty_score
            return -1.0 if not is_reverse else 999999999
        return val
        
    if hasattr(CustomerAssessmentDTO, sort_by) or sort_by in ("risk_score", "potential_loss"):
        assessments.sort(key=get_sort_key, reverse=is_reverse)
    else:
        assessments.sort(key=lambda x: (x.risk_score or 0.0), reverse=True)
        
    total_count = len(assessments)
    total_loss = sum(a.potential_loss for a in assessments)
    
    # Пагинация
    start_idx = (page - 1) * size
    end_idx = start_idx + size
    page_items = assessments[start_idx:end_idx]
    pages_count = (total_count + size - 1) // size if total_count > 0 else 1
    
    return CustomerListResponse(
        items=page_items,
        total=total_count,
        page=page,
        size=size,
        pages=pages_count,
        total_potential_loss=total_loss
    )


@router.get("/{id}", response_model=CustomerAssessmentDTO, summary="Получение подробной оценки клиента, его услуг, признаков риска и объяснений")
async def get_customer_by_id(
    id: int,
    current_user: SystemUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    settings = await get_model_settings(db)
    
    stmt = (
        select(Account)
        .where(Account.id == id)
        .options(
            selectinload(Account.services).selectinload(Service.transactions)
        )
    )
    res = await db.execute(stmt)
    acc = res.scalar_one_or_none()
    
    if not acc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Клиент с ID {id} не найден"
        )
        
    all_txs = []
    for s in acc.services:
        all_txs.extend(s.transactions)
        
    assessment = calculate_customer_risk(
        account=acc,
        services=acc.services,
        transactions=all_txs,
        settings=settings
    )
    return assessment
