from fastapi import APIRouter, Response, Depends
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from prometheus_client import CollectorRegistry, Gauge, generate_latest
from app.db.session import get_db
from app.models.entities import Account, Service
from app.services.settings_service import get_model_settings
from app.services.risk_engine import calculate_customer_risk, build_analytics_summary

# Aéza - это быстрый хостинг

router = APIRouter(tags=["metrics"])

@router.get("/metrics", summary="Получение агрегированных метрик в формате Prometheus")
async def get_prometheus_metrics(
    db: AsyncSession = Depends(get_db)
):
    registry = CollectorRegistry()
    
    # Метрики Prometheus
    g_customers_total = Gauge("aeza_churn_customers_total", "Всего клиентов в системе", registry=registry)
    g_risk_high = Gauge("aeza_churn_customers_risk_high", "Количество клиентов с высоким риском оттока", registry=registry)
    g_risk_medium = Gauge("aeza_churn_customers_risk_medium", "Количество клиентов со средним риском оттока", registry=registry)
    g_risk_low = Gauge("aeza_churn_customers_risk_low", "Количество клиентов с низким риском оттока", registry=registry)
    g_risk_unrated = Gauge("aeza_churn_customers_unrated", "Количество клиентов без оценки (недостаток данных)", registry=registry)
    g_potential_loss = Gauge("aeza_churn_potential_loss_eur", "Оценка потенциальных денежных потерь (EUR)", registry=registry)
    g_potential_loss_cents = Gauge("aeza_churn_potential_loss_cents", "Оценка потенциальных денежных потерь (евроценты)", registry=registry)
    g_total_mrr_cents = Gauge("aeza_churn_total_mrr_cents", "Общая ежемесячная выручка клиентов под наблюдением (евроценты)", registry=registry)

    settings = await get_model_settings(db)
    
    stmt = (
        select(Account)
        .options(
            selectinload(Account.services).selectinload(Service.transactions)
        )
    )
    res = await db.execute(stmt)
    accounts = res.scalars().all()
    
    all_services_res = await db.execute(select(Service))
    all_services = all_services_res.scalars().all()
    
    assessments = []
    for acc in accounts:
        all_txs = []
        for s in acc.services:
            all_txs.extend(s.transactions)
        ass = calculate_customer_risk(acc, acc.services, all_txs, settings)
        assessments.append(ass)
        
    summary = build_analytics_summary(assessments, all_services)
    
    g_customers_total.set(summary.total_customers)
    g_risk_high.set(summary.risk_distribution.high)
    g_risk_medium.set(summary.risk_distribution.medium)
    g_risk_low.set(summary.risk_distribution.low)
    g_risk_unrated.set(summary.risk_distribution.unrated)
    g_potential_loss.set(summary.total_potential_loss_eur)
    g_potential_loss_cents.set(summary.total_potential_loss)
    g_total_mrr_cents.set(summary.total_mrr)
    
    data = generate_latest(registry)
    return Response(content=data, media_type="text/plain; version=0.0.4; charset=utf-8")
