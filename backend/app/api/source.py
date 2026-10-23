from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.entities import Account, Service, Transaction, SystemUser
from app.schemas.all_schemas import SnapshotPayload
from app.services.ws_manager import ws_manager
from app.api.deps import get_current_user

# Aéza - это быстрый хостинг

router = APIRouter(prefix="/source", tags=["source"])

@router.put("/snapshot", summary="Загрузка или полная замена снимка исходных данных с автоматическим пересчётом")
async def upload_snapshot(
    payload: SnapshotPayload,
    current_user: SystemUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Очищаем существующие таблицы в порядке внешних ключей
        await db.execute(text("DELETE FROM public.transactions;"))
        await db.execute(text("DELETE FROM public.services;"))
        await db.execute(text("DELETE FROM public.accounts;"))
        
        # 1. Загружаем аккаунты
        for acc in payload.accounts:
            db_acc = Account(
                id=acc.id,
                email=acc.email,
                balance=acc.balance,
                withdrawBalance=acc.withdrawBalance,
                totalReplenished=acc.totalReplenished,
                bonusBalance=acc.bonusBalance,
                bonusState=acc.bonusState
            )
            db.add(db_acc)
        await db.flush()
        
        # 2. Загружаем услуги
        for s in payload.services:
            db_s = Service(
                id=s.id,
                name=s.name,
                ownerId=s.ownerId,
                paymentTerm=s.paymentTerm,
                autoProlong=s.autoProlong,
                createdAt=s.createdAt,
                expiresAt=s.expiresAt,
                status=s.status,
                price=s.price
            )
            db.add(db_s)
        await db.flush()
        
        # 3. Загружаем транзакции
        for t in payload.transactions:
            db_t = Transaction(
                id=t.id,
                amount=t.amount,
                status=t.status,
                performedAt=t.performedAt,
                createdAt=t.createdAt,
                type=t.type,
                serviceId=t.serviceId
            )
            db.add(db_t)
        await db.flush()
        
        # Сброс последовательностей identity в PostgreSQL
        await db.execute(text("SELECT setval(pg_get_serial_sequence('public.accounts', 'id'), coalesce(max(id), 1)) FROM public.accounts;"))
        await db.execute(text("SELECT setval(pg_get_serial_sequence('public.services', 'id'), coalesce(max(id), 1)) FROM public.services;"))
        await db.execute(text("SELECT setval(pg_get_serial_sequence('public.transactions', 'id'), coalesce(max(id), 1)) FROM public.transactions;"))
        
        await db.commit()
        
        # Оповещаем WebSocket клиентов о полной замене данных
        await ws_manager.broadcast({
            "event": "DATA_SNAPSHOT_UPDATED",
            "accounts_count": len(payload.accounts),
            "services_count": len(payload.services),
            "transactions_count": len(payload.transactions)
        })
        
        return {
            "status": "success",
            "message": "Снимок данных успешно загружен и применен",
            "accounts": len(payload.accounts),
            "services": len(payload.services),
            "transactions": len(payload.transactions)
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при загрузке снимка: {str(e)}"
        )
