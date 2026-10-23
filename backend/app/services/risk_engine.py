from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from app.models.entities import Account, Service, Transaction
from app.schemas.all_schemas import (
    CustomerAssessmentDTO, ServiceAssessmentDTO, RiskFactorDTO,
    ModelSettingsDTO, AnalyticsSummaryDTO, RiskDistributionDTO, ChurnChartPointDTO
)

# Aéza - это быстрый хостинг

# Вспомогательный коэффициент приведения периодичности оплаты к месячному доходу (MRR)
TERM_TO_MONTHLY_MULTIPLIER = {
    "hour": 24 * 30.5,        # ~732 часа в месяц
    "week": 4.345,            # ~4.345 недель в месяц
    "month": 1.0,
    "quarter_year": 1.0 / 3.0,
    "half_year": 1.0 / 6.0,
    "year": 1.0 / 12.0
}

def calculate_customer_risk(
    account: Account,
    services: List[Service],
    transactions: List[Transaction],
    settings: ModelSettingsDTO,
    reference_date: Optional[datetime] = None
) -> CustomerAssessmentDTO:
    now = reference_date or datetime.now(timezone.utc)
    
    # 1. Проверяем доступный баланс
    bonus_usable = (account.bonusState == "unlocked")
    effective_balance = account.balance + (account.bonusBalance if bonus_usable else 0)
    
    total_services = len(services)
    non_deleted_services = [s for s in services if s.status not in ("deleted", "blocked")]
    active_services = [s for s in services if s.status == "active"]
    
    # Если у клиента вообще нет услуг и пополнений -> Недостаток данных (unrated)
    if total_services == 0 and account.totalReplenished == 0:
        return CustomerAssessmentDTO(
            id=account.id,
            email=account.email,
            balance=account.balance,
            withdrawBalance=account.withdrawBalance,
            totalReplenished=account.totalReplenished,
            bonusBalance=account.bonusBalance,
            bonusState=account.bonusState,
            effective_balance=effective_balance,
            risk_score=None,
            risk_level="unrated",
            loyalty_score=None,
            is_rated=False,
            total_services_count=0,
            active_services_count=0,
            at_risk_services_count=0,
            monthly_recurring_revenue=0,
            potential_loss=0,
            raw_services_value=0,
            risk_factors=[
                RiskFactorDTO(
                    code="NO_DATA",
                    title="Нет данных по услугам",
                    description="У клиента отсутствуют активные или зарегистрированные услуги для анализа.",
                    severity="low",
                    weight_impact=0.0
                )
            ],
            primary_reason="Отсутствуют данные по услугам (клиент без активности)",
            services=[]
        )

    # 2. Оценка рисков по отдельным услугам
    service_assessments: List[ServiceAssessmentDTO] = []
    
    total_renewal_cost_urgent = 0
    at_risk_services_count = 0
    monthly_recurring_revenue = 0
    raw_services_value = 0
    
    count_prolong_wait = 0
    count_no_autoprolong = 0
    count_expiring_soon = 0
    
    for s in services:
        # Убедимся, что даты timezone-aware
        exp = s.expiresAt if s.expiresAt.tzinfo else s.expiresAt.replace(tzinfo=timezone.utc)
        diff_hours = (exp - now).total_seconds() / 3600.0
        
        # Расчет MRR
        mult = TERM_TO_MONTHLY_MULTIPLIER.get(s.paymentTerm, 1.0)
        mrr_val = int(s.price * mult)
        if s.status in ("active", "suspended", "prolong_wait"):
            monthly_recurring_revenue += mrr_val
            raw_services_value += s.price
        
        s_factors = []
        is_service_risk = False
        
        if s.status == "prolong_wait":
            is_service_risk = True
            count_prolong_wait += 1
            s_factors.append("Ожидает оплаты (prolong_wait)")
            total_renewal_cost_urgent += s.price
        elif s.status == "active":
            if not s.autoProlong:
                count_no_autoprolong += 1
                s_factors.append("Автопродление отключено")
            if diff_hours <= (settings.forecast_days * 24):
                total_renewal_cost_urgent += s.price
                if diff_hours <= 48:
                    count_expiring_soon += 1
                    s_factors.append(f"Истекает через {max(0, int(diff_hours))} ч.")
                    is_service_risk = True
            if not s.autoProlong and diff_hours <= (settings.forecast_days * 24):
                is_service_risk = True
        elif s.status == "suspended":
            s_factors.append("Услуга выключена клиентом (suspended)")
            is_service_risk = True
            
        if is_service_risk:
            at_risk_services_count += 1
            
        service_assessments.append(ServiceAssessmentDTO(
            id=s.id,
            name=s.name,
            status=s.status,
            price=s.price,
            paymentTerm=s.paymentTerm,
            autoProlong=s.autoProlong,
            expiresAt=exp,
            hours_until_expiry=round(diff_hours, 1),
            is_at_risk=is_service_risk,
            risk_factors=s_factors
        ))

    # 3. Транзакции клиента
    failed_tx_count = sum(1 for t in transactions if t.status == "not_performed")
    total_tx_count = len(transactions)
    tx_fail_ratio = (failed_tx_count / total_tx_count) if total_tx_count > 0 else 0.0

    # 4. Расчет признаков риска (0.0 до 1.0 каждый)
    # Признак 1: Отключение автопродления среди не-удаленных услуг
    non_del_count = len(non_deleted_services)
    f_no_autoprolong = (count_no_autoprolong / non_del_count) if non_del_count > 0 else 0.0

    # Признак 2: Недостаток баланса для срочных продлений
    if total_renewal_cost_urgent > 0:
        if effective_balance >= total_renewal_cost_urgent:
            f_balance_insufficient = 0.0
        else:
            deficit = total_renewal_cost_urgent - effective_balance
            f_balance_insufficient = min(1.0, deficit / float(total_renewal_cost_urgent))
    else:
        # Если нет срочных продлений, но баланс = 0 и есть услуги
        f_balance_insufficient = 0.2 if (effective_balance == 0 and non_del_count > 0) else 0.0

    # Признак 3: Наличие зависших услуг prolong_wait
    f_prolong_wait = min(1.0, count_prolong_wait / float(max(1, non_del_count))) if count_prolong_wait > 0 else 0.0

    # Признак 4: Скорое истечение срока
    f_expiring_soon = min(1.0, count_expiring_soon / float(max(1, non_del_count))) if count_expiring_soon > 0 else 0.0

    # Признак 5: Ошибки транзакций
    f_failed_tx = min(1.0, tx_fail_ratio * 1.5)

    # Взвешенная сумма с нормализацией весов
    weights = settings.weights
    total_weights = (
        weights.w_no_autoprolong +
        weights.w_balance_insufficient +
        weights.w_prolong_wait +
        weights.w_expiring_soon +
        weights.w_failed_transactions
    )
    if total_weights <= 0:
        total_weights = 1.0

    score = (
        f_no_autoprolong * weights.w_no_autoprolong +
        f_balance_insufficient * weights.w_balance_insufficient +
        f_prolong_wait * weights.w_prolong_wait +
        f_expiring_soon * weights.w_expiring_soon +
        f_failed_tx * weights.w_failed_transactions
    ) / total_weights

    # Если у клиента все услуги уже удалены и баланс 0
    if non_del_count == 0 and total_services > 0:
        score = 0.95

    score = round(max(0.0, min(1.0, score)), 3)
    loyalty = round(1.0 - score, 3)

    # 5. Определение уровня риска
    if score >= settings.thresholds.high:
        risk_level = "high"
    elif score >= settings.thresholds.medium:
        risk_level = "medium"
    else:
        risk_level = "low"

    # 6. Формирование объяснений (Explainability)
    factors: List[RiskFactorDTO] = []
    
    if count_prolong_wait > 0:
        factors.append(RiskFactorDTO(
            code="PROLONG_WAIT",
            title=f"Услуг в ожидании оплаты: {count_prolong_wait}",
            description=f"{count_prolong_wait} услуг перешли в prolong_wait и будут удалены через 5 дней при неоплате.",
            severity="high",
            weight_impact=round(f_prolong_wait * (weights.w_prolong_wait / total_weights), 3)
        ))

    if f_balance_insufficient > 0.01:
        needed = total_renewal_cost_urgent
        factors.append(RiskFactorDTO(
            code="INSUFFICIENT_BALANCE",
            title="Недостаточно средств на балансе",
            description=f"Текущий баланс: {effective_balance/100:.2f} €, требуется для продления: {needed/100:.2f} €.",
            severity="high" if f_balance_insufficient > 0.5 else "medium",
            weight_impact=round(f_balance_insufficient * (weights.w_balance_insufficient / total_weights), 3)
        ))

    if count_no_autoprolong > 0:
        factors.append(RiskFactorDTO(
            code="NO_AUTOPROLONG",
            title=f"Отключено автопродление ({count_no_autoprolong} услуг)",
            description="Клиент отключил автопродление, услуга не продлится автоматически по истечении срока.",
            severity="medium",
            weight_impact=round(f_no_autoprolong * (weights.w_no_autoprolong / total_weights), 3)
        ))

    if count_expiring_soon > 0:
        factors.append(RiskFactorDTO(
            code="EXPIRING_SOON",
            title=f"Истекают в ближайшие 48 часов ({count_expiring_soon} услуг)",
            description="Срок действия услуг заканчивается в течение 1-2 дней.",
            severity="medium",
            weight_impact=round(f_expiring_soon * (weights.w_expiring_soon / total_weights), 3)
        ))

    if failed_tx_count > 0:
        factors.append(RiskFactorDTO(
            code="FAILED_TRANSACTIONS",
            title=f"Неуспешные транзакции ({failed_tx_count} из {total_tx_count})",
            description="Зафиксированы попытки заказов или продлений без подтверждения оплаты.",
            severity="low" if f_failed_tx < 0.3 else "medium",
            weight_impact=round(f_failed_tx * (weights.w_failed_transactions / total_weights), 3)
        ))

    if not factors:
        factors.append(RiskFactorDTO(
            code="NORMAL",
            title="Штатный режим",
            description="Автопродление включено, баланса достаточно для ближайших списаний.",
            severity="low",
            weight_impact=0.0
        ))

    # Главная причина (Primary reason)
    factors_sorted = sorted(factors, key=lambda x: x.weight_impact, reverse=True)
    primary_reason = factors_sorted[0].title if factors_sorted else "Низкий риск"

    # 7. Расчет потенциальных потерь (Potential Loss)
    # Потери рассчитываются на основе ежемесячной ценности клиента (MRR) и цен услуг, умноженных на score
    if settings.loss_estimation_method == "raw_price":
        base_val = raw_services_value
    elif settings.loss_estimation_method == "total_at_risk":
        base_val = sum(s.price for s in service_assessments if s.is_at_risk)
    else: # weighted_mrr (по умолчанию наиболее точный)
        base_val = monthly_recurring_revenue
        
    potential_loss = int(base_val * score)

    return CustomerAssessmentDTO(
        id=account.id,
        email=account.email,
        balance=account.balance,
        withdrawBalance=account.withdrawBalance,
        totalReplenished=account.totalReplenished,
        bonusBalance=account.bonusBalance,
        bonusState=account.bonusState,
        effective_balance=effective_balance,
        risk_score=score,
        risk_level=risk_level,
        loyalty_score=loyalty,
        is_rated=True,
        total_services_count=total_services,
        active_services_count=len(active_services),
        at_risk_services_count=at_risk_services_count,
        monthly_recurring_revenue=monthly_recurring_revenue,
        potential_loss=potential_loss,
        raw_services_value=raw_services_value,
        risk_factors=factors,
        primary_reason=primary_reason,
        services=service_assessments
    )


def build_analytics_summary(
    assessments: List[CustomerAssessmentDTO],
    all_services: List[Service],
    now: Optional[datetime] = None
) -> AnalyticsSummaryDTO:
    now = now or datetime.now(timezone.utc)
    
    total = len(assessments)
    rated = [a for a in assessments if a.is_rated]
    unrated = [a for a in assessments if not a.is_rated]
    
    high = [a for a in rated if a.risk_level == "high"]
    med = [a for a in rated if a.risk_level == "medium"]
    low = [a for a in rated if a.risk_level == "low"]
    
    total_loss = sum(a.potential_loss for a in rated)
    total_mrr = sum(a.monthly_recurring_revenue for a in rated)
    high_loss = sum(a.potential_loss for a in high)
    med_loss = sum(a.potential_loss for a in med)
    
    # Факторы риска для сводки
    factor_counts: Dict[str, Dict[str, Any]] = {}
    for a in rated:
        for f in a.risk_factors:
            if f.code == "NORMAL": continue
            if f.code not in factor_counts:
                factor_counts[f.code] = {
                    "code": f.code,
                    "title": f.title.split("(")[0].strip(),
                    "count": 0,
                    "severity": f.severity
                }
            factor_counts[f.code]["count"] += 1
            
    top_factors = sorted(list(factor_counts.values()), key=lambda x: x["count"], reverse=True)

    # Построение графика оттока (Chart): факт удалений + текущий риск + прогноз
    chart_points: List[ChurnChartPointDTO] = []
    
    # Считаем факт удалений услуг по дням
    deleted_counts_by_day = {}
    for s in all_services:
        if s.status == "deleted":
            exp = s.expiresAt if s.expiresAt.tzinfo else s.expiresAt.replace(tzinfo=timezone.utc)
            d_str = exp.strftime("%Y-%m-%d")
            deleted_counts_by_day[d_str] = deleted_counts_by_day.get(d_str, 0) + 1

    # Генерируем 7 дней: 3 дня в прошлом, сегодня, 3 дня вперед (прогноз)
    base_date = now.date()
    for offset in range(-3, 4):
        cur_d = base_date + timedelta(days=offset)
        cur_str = cur_d.strftime("%Y-%m-%d")
        
        # Факт удалений (актуально для прошлых дней и сегодня)
        fact_del = deleted_counts_by_day.get(cur_str, 0) if offset <= 0 else 0
        
        # Услуги под риском в этот день
        if offset == 0:
            at_risk = sum(a.at_risk_services_count for a in rated)
            pred_churn = sum(1 for a in high for s in (a.services or []) if s.is_at_risk)
            loss_day = int(total_loss / 30.5)
        elif offset > 0:
            at_risk = max(0, sum(a.at_risk_services_count for a in high) - offset)
            pred_churn = max(0, int(len(high) * 0.8) - offset)
            loss_day = int(high_loss / 30.5)
        else:
            at_risk = 0
            pred_churn = 0
            loss_day = 0
            
        chart_points.append(ChurnChartPointDTO(
            date=cur_str,
            fact_deleted_services=fact_del,
            at_risk_services=at_risk,
            predicted_churn_services=pred_churn,
            potential_loss_amount=loss_day
        ))

    return AnalyticsSummaryDTO(
        total_customers=total,
        rated_customers=len(rated),
        unrated_customers=len(unrated),
        risk_distribution=RiskDistributionDTO(
            high=len(high),
            medium=len(med),
            low=len(low),
            unrated=len(unrated)
        ),
        total_potential_loss=total_loss,
        total_potential_loss_eur=round(total_loss / 100.0, 2),
        total_mrr=total_mrr,
        high_risk_loss=high_loss,
        medium_risk_loss=med_loss,
        top_risk_factors=top_factors,
        chart=chart_points,
        updated_at=datetime.now(timezone.utc)
    )
