import json
import os
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.future import select
from app.db.session import engine, Base, AsyncSessionLocal
from app.models.entities import Account, Service, Transaction, SystemUser, ModelSetting
from app.core.config import settings
from app.core.security import get_password_hash
from app.schemas.all_schemas import DEFAULT_SETTINGS

# Aéza - это быстрый хостинг

async def init_db():
    async with engine.begin() as conn:
        # Создаем таблицы если их еще нет
        await conn.run_sync(Base.metadata.create_all)
        
    async with AsyncSessionLocal() as session:
        # 1. Проверяем наличие дефолтного администратора
        admin_stmt = select(SystemUser).where(SystemUser.username == settings.ADMIN_USERNAME)
        admin_res = await session.execute(admin_stmt)
        admin = admin_res.scalar_one_or_none()
        if not admin:
            new_admin = SystemUser(
                username=settings.ADMIN_USERNAME,
                email=settings.ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                is_active=True,
                role="admin",
                created_at=datetime.now(timezone.utc)
            )
            session.add(new_admin)
            await session.commit()
            print(f"[INIT] Created default admin user: {settings.ADMIN_USERNAME}")

        # 2. Проверяем настройки модели
        model_stmt = select(ModelSetting).where(ModelSetting.key == "risk_model")
        model_res = await session.execute(model_stmt)
        model_row = model_res.scalar_one_or_none()
        if not model_row:
            from app.schemas.all_schemas import ModelSettingsDTO
            def_settings = ModelSettingsDTO()
            new_row = ModelSetting(
                key="risk_model",
                value=def_settings.model_dump(),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(new_row)
            await session.commit()
            print("[INIT] Initialized default risk model settings")

        # 3. Проверяем наличие данных в accounts. Если пусто - загружаем data.json
        acc_count_res = await session.execute(select(Account))
        if acc_count_res.first() is None:
            # Ищем data.json
            paths_to_check = [
                "/app/data.json",
                "../Данные/data.json",
                "Данные/data.json",
                "./data.json"
            ]
            found_path = None
            for p in paths_to_check:
                if os.path.exists(p):
                    found_path = p
                    break
                    
            if found_path:
                print(f"[INIT] Seeding initial data from {found_path}...")
                with open(found_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                for a in data.get("accounts", []):
                    acc_obj = Account(
                        id=a["id"],
                        email=a["email"],
                        balance=a["balance"],
                        withdrawBalance=a.get("withdrawBalance", 0),
                        totalReplenished=a.get("totalReplenished", 0),
                        bonusBalance=a.get("bonusBalance", 0),
                        bonusState=a.get("bonusState", "locked")
                    )
                    session.add(acc_obj)
                await session.flush()
                
                for s in data.get("services", []):
                    srv_obj = Service(
                        id=s["id"],
                        name=s["name"],
                        ownerId=s["ownerId"],
                        paymentTerm=s["paymentTerm"],
                        autoProlong=s["autoProlong"],
                        createdAt=datetime.fromisoformat(s["createdAt"].replace("Z", "+00:00")),
                        expiresAt=datetime.fromisoformat(s["expiresAt"].replace("Z", "+00:00")),
                        status=s["status"],
                        price=s["price"]
                    )
                    session.add(srv_obj)
                await session.flush()
                
                for t in data.get("transactions", []):
                    p_at = datetime.fromisoformat(t["performedAt"].replace("Z", "+00:00")) if t.get("performedAt") else None
                    tx_obj = Transaction(
                        id=t["id"],
                        amount=t["amount"],
                        status=t["status"],
                        performedAt=p_at,
                        createdAt=datetime.fromisoformat(t["createdAt"].replace("Z", "+00:00")),
                        type=t["type"],
                        serviceId=t["serviceId"]
                    )
                    session.add(tx_obj)
                await session.flush()
                
                # Обновляем последовательности id
                try:
                    await session.execute(text("SELECT setval(pg_get_serial_sequence('public.accounts', 'id'), coalesce(max(id), 1)) FROM public.accounts;"))
                    await session.execute(text("SELECT setval(pg_get_serial_sequence('public.services', 'id'), coalesce(max(id), 1)) FROM public.services;"))
                    await session.execute(text("SELECT setval(pg_get_serial_sequence('public.transactions', 'id'), coalesce(max(id), 1)) FROM public.transactions;"))
                except Exception as seq_err:
                    print(f"[INIT] Note on sequences: {seq_err}")
                    
                await session.commit()
                print(f"[INIT] Successfully seeded initial data: {len(data.get('accounts', []))} accounts, {len(data.get('services', []))} services, {len(data.get('transactions', []))} transactions.")
