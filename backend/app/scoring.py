from __future__ import annotations

import copy
import math
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

DEFAULT_SETTINGS: dict[str, Any] = {
    "weights": {
        "expiry_pressure": 0.40,
        "funds_gap": 0.25,
        "autorenew_off": 0.10,
        "status_pressure": 0.10,
        "payment_history": 0.10,
        "commitment": 0.05,
    },
    "thresholds": {"medium": 40.0, "high": 70.0},
    "probability": {"midpoint": 65.0, "steepness": 12.0, "floor": 0.02, "ceiling": 0.95},
    "money": {"balanceMitigation": 0.5, "includeWithdrawBalance": True},
    "statusFloors": {"prolong_wait": 70.0, "blocked": 60.0, "stale": 70.0},
    "recomputeIntervalSec": 300,
}

FEATURES_META = [
    {
        "code": "expiry_pressure",
        "title": "Срочность продления",
        "description": "Сколько дней осталось до конца оплаченного периода",
        "min": 0.0,
        "max": 1.0,
        "step": 0.01,
        "default": 0.40,
    },
    {
        "code": "funds_gap",
        "title": "Нехватка денег",
        "description": "Хватает ли баланса на ближайшее продление",
        "min": 0.0,
        "max": 1.0,
        "step": 0.01,
        "default": 0.25,
    },
    {
        "code": "autorenew_off",
        "title": "Автопродление отключено",
        "description": "Клиент сам отключил автоматическое продление",
        "min": 0.0,
        "max": 1.0,
        "step": 0.01,
        "default": 0.10,
    },
    {
        "code": "status_pressure",
        "title": "Статус услуги",
        "description": "prolong_wait, blocked, suspended или active",
        "min": 0.0,
        "max": 1.0,
        "step": 0.01,
        "default": 0.10,
    },
    {
        "code": "payment_history",
        "title": "История платежей",
        "description": "Были ли неоплаченные счета",
        "min": 0.0,
        "max": 1.0,
        "step": 0.01,
        "default": 0.10,
    },
    {
        "code": "commitment",
        "title": "Лояльность",
        "description": "Отношение пополнений к стоимости услуг",
        "min": 0.0,
        "max": 1.0,
        "step": 0.01,
        "default": 0.05,
    },
]


def default_settings() -> dict[str, Any]:
    return copy.deepcopy(DEFAULT_SETTINGS)


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def eur(cents: float) -> str:
    return f"€{cents / 100:.2f}"


def level_for(score: float | None, thresholds: dict[str, float]) -> str:
    if score is None:
        return "unknown"
    if score >= thresholds["high"]:
        return "high"
    if score >= thresholds["medium"]:
        return "medium"
    return "low"


def probability(score: float, settings: dict[str, Any]) -> float:
    prob = settings["probability"]
    z = (score - prob["midpoint"]) / prob["steepness"]
    if z >= 0:
        raw = 1.0 / (1.0 + math.exp(-z))
    else:
        exp_z = math.exp(z)
        raw = exp_z / (1.0 + exp_z)
    return max(prob["floor"], min(prob["ceiling"], raw))



def explanation_rule(code: str, scope: str, service_id: int | None, label: str,
                     before: float, after: float, related: list[int] | None = None) -> dict[str, Any]:
    # These are display projections; the scoring arithmetic remains untouched.
    before_display, after_display = round(before, 1), round(after, 1)
    delta = round(after_display - before_display, 1) or 0.0
    if delta == 0.0:
        label += "; после округления оценка не изменилась"
    return {"code": code, "scope": scope, "serviceId": service_id, "label": label,
            "beforeScore": before_display, "afterScore": after_display, "delta": delta,
            "relatedServiceIds": related or []}

def available_cents(account: dict[str, Any], settings: dict[str, Any]) -> int:
    value = int(account["balance"]) + (
        int(account["withdraw_balance"]) if settings["money"]["includeWithdrawBalance"] else 0
    )
    if account["bonus_state"] == "unlocked":
        value += int(account["bonus_balance"])
    return value


def _expiry(service: dict[str, Any], available: int, now: datetime) -> tuple[float | None, str]:
    days = (parse_iso(service["expires_at"]) - now).total_seconds() / 86400
    if days < 0:
        value = 1.0
        label = "Срок истёк сегодня" if abs(days) < 1 else f"Просрочена на {round(abs(days))} дн."
    elif days < 1:
        value, label = 1.0, f"Продление через {max(1, round(days * 24))} ч"
    elif days <= 3:
        value, label = 1.0, f"Продление через {round(days)} дн."
    elif days <= 7:
        value, label = 0.75, f"Продление через {round(days)} дн."
    elif days <= 14:
        value, label = 0.5, f"Продление через {round(days)} дн."
    elif days <= 30:
        value, label = 0.25, f"Продление через {round(days)} дн."
    else:
        value, label = 0.05, f"Продление через {round(days)} дн."
    if service["auto_prolong"] and available >= service["price"]:
        value *= 0.4
        label += ", автопродление включено"
    return value, label


def _status(service: dict[str, Any], now: datetime) -> tuple[float, bool, str]:
    status = service["status"]
    expires = parse_iso(service["expires_at"])
    stale = False
    if status in ("active", "suspended") and expires < now:
        stale = True
    if status == "prolong_wait" and (expires - now).total_seconds() / 86400 < -5:
        stale = True
    base = {"prolong_wait": 1.0, "blocked": 0.9, "suspended": 0.7, "active": 0.0}[status]
    if stale:
        base = 1.0
    label = {
        "prolong_wait": "Услуга ожидает оплаты",
        "blocked": "Услуга заблокирована",
        "suspended": "Услуга выключена, но оплачивается",
        "active": "Услуга активна",
    }[status]
    if stale:
        label = "Срок истёк, статус не обновлён"
    return base, stale, label


def _score_service(
    service: dict[str, Any],
    account: dict[str, Any],
    transactions: list[dict[str, Any]],
    account_price: int,
    now: datetime,
    settings: dict[str, Any],
) -> dict[str, Any] | None:
    if service["status"] == "deleted":
        return None

    weights = settings["weights"]
    available = available_cents(account, settings)
    expiry, expiry_label = _expiry(service, available, now)
    if service["price"] <= 0:
        funds, funds_label = None, "Цена услуги не указана"
    elif available < service["price"]:
        funds = 1.0
        funds_label = f"Баланса {eur(available)} не хватает на {eur(service['price'])}"
    else:
        funds = max(0.0, 0.3 * (1.0 - available / (3.0 * service["price"])))
        funds_label = f"Запас баланса {eur(available)}"
    auto = 0.0 if service["auto_prolong"] else 1.0
    status, stale, status_label = _status(service, now)

    tx = [t for t in transactions if t["service_id"] == service["id"]]
    if not tx:
        history, history_label = None, "Нет транзакций"
    elif any(t["status"] == "not_performed" and t["type"] == "prolong" for t in tx):
        history, history_label = 1.0, "Есть неоплаченное продление"
    elif any(t["status"] == "not_performed" and t["type"] == "order" for t in tx):
        history, history_label = 0.6, "Есть неоплаченный заказ"
    else:
        history, history_label = 0.0, "Неоплаченных счетов нет"

    if account_price <= 0:
        commitment, commitment_label = None, "Нет цены услуг"
    else:
        commitment = 1.0 - min(1.0, account["total_replenished"] / (3.0 * account_price))
        commitment_label = "Мало пополнений относительно стоимости"

    values = {
        "expiry_pressure": (expiry, expiry_label),
        "funds_gap": (funds, funds_label),
        "autorenew_off": (auto, "Автопродление отключено"),
        "status_pressure": (status, status_label),
        "payment_history": (history, history_label),
        "commitment": (commitment, commitment_label),
    }

    total_weight = sum(float(weight) for weight in weights.values())
    if not math.isfinite(total_weight):
        scale = max(weights.values())
        weights = {code: weight / scale for code, weight in weights.items()}
        total_weight = sum(weights.values())
    score = 0.0
    confidence = 0.0
    drivers: list[dict[str, Any]] = []
    for code, (value, label) in values.items():
        weight = float(weights[code])
        if value is None:
            value = 0.5
        else:
            confidence += weight / total_weight
        contribution = (weight / total_weight) * value
        score += contribution
        if contribution > 0.01:
            drivers.append(
                {
                    "code": code,
                    "label": label,
                    "contribution": round(contribution, 3),
                    "value": round(value, 3),
                }
            )

    score *= 100.0
    floors = settings["statusFloors"]
    rules: list[dict[str, Any]] = []
    if service["status"] in ("prolong_wait", "blocked"):
        floor = floors[service["status"]]
        if score < floor:
            rules.append(explanation_rule("status_floor", "service", service["id"],
                f"Статус {service['status']}: применён минимум {floor:g}", score, floor))
            score = floor
    if stale and score < floors["stale"]:
        floor = floors["stale"]
        rules.append(explanation_rule("stale_status_floor", "service", service["id"],
            f"Устаревший статус: применён минимум {floor:g}", score, floor))
        score = floor
    drivers.sort(key=lambda item: item["contribution"], reverse=True)

    return {
        "explanationRules": rules,
        "score": round(score, 1),
        "confidence": round(confidence, 2),
        "stale": stale,
        "drivers": drivers[:4],
        "values": {code: (None if value is None else round(value, 2)) for code, (value, _) in values.items()},
        "expiryDays": round((parse_iso(service["expires_at"]) - now).total_seconds() / 86400, 1),
    }


def _service_detail(service: dict[str, Any], result: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": service["id"],
        "name": service["name"],
        "priceCents": int(service["price"]),
        "paymentTerm": service["payment_term"],
        "status": service["status"],
        "autoProlong": bool(service["auto_prolong"]),
        "createdAt": service["created_at"],
        "expiresAt": service["expires_at"],
        "score": result["score"],
        "level": level_for(result["score"], settings["thresholds"]),
        "confidence": result["confidence"],
        "staleStatus": result["stale"],
        "drivers": result["drivers"],
        "explanationRules": result["explanationRules"],
        "values": result["values"],
        "expiryDays": result["expiryDays"],
    }


def compute(
    accounts: list[dict[str, Any]],
    services: list[dict[str, Any]],
    transactions: list[dict[str, Any]],
    settings: dict[str, Any],
    as_of: datetime,
    updated_at: datetime,
) -> dict[str, Any]:
    by_owner: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for service in services:
        by_owner[service["owner_id"]].append(service)
    transactions_by_service: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for txn in transactions:
        transactions_by_service[txn["service_id"]].append(txn)

    customers: list[dict[str, Any]] = []
    counts = {"high": 0, "medium": 0, "low": 0, "unknown": 0}
    total_loss = 0
    total_risk = 0
    total_available = 0
    total_price = 0
    total_services_at_risk = 0
    scored_scores: list[float] = []
    coverage_values: list[float] = []
    underfunded = 0

    for account in accounts:
        owner_services = by_owner.get(account["id"], [])
        account_price = sum(int(s["price"]) for s in owner_services)
        available = available_cents(account, settings)
        scored: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for service in owner_services:
            result = _score_service(
                service,
                account,
                transactions_by_service.get(service["id"], []),
                account_price,
                as_of,
                settings,
            )
            if result is not None and result["confidence"] >= 0.5:
                scored.append((service, result))

        if not scored:
            if owner_services and all(s["status"] == "deleted" for s in owner_services):
                reason = "Все услуги удалены"
            elif not owner_services:
                reason = "Нет услуг"
            else:
                reason = "Недостаточно данных для оценки"
            counts["unknown"] += 1
            customers.append(
                {
                    "id": account["id"],
                    "email": account["email"],
                    "balanceCents": int(account["balance"]),
                    "withdrawCents": int(account["withdraw_balance"]),
                    "bonusCents": int(account["bonus_balance"]),
                    "bonusState": account["bonus_state"],
                    "totalReplenishedCents": int(account["total_replenished"]),
                    "score": None,
                    "level": "unknown",
                    "confidence": 0.0,
                    "summaryText": reason,
                    "drivers": [],
                    "services": [],
                    "money": {
                        "amountAtRiskCents": 0,
                        "expectedLossCents": 0,
                        "coveredLossCents": 0,
                        "coverage": 0.0,
                        "mitigation": 0.0,
                    },
                    "explanationRules": [],
                    "unknownReason": reason,
                    "isEstimated": False,
                }
            )
            continue

        at_risk_services = sum(
            1 for _, result in scored if result["score"] >= settings["thresholds"]["medium"]
        )
        base_score = max(result["score"] for _, result in scored)
        bonus = 4.0 * max(0, at_risk_services - 1)
        uncapped = base_score + bonus
        customer_rules: list[dict[str, Any]] = []
        if bonus:
            related = [service["id"] for service, result in scored
                       if result["score"] >= settings["thresholds"]["medium"]]
            customer_rules.append(explanation_rule("customer_bonus", "customer", None,
                f"Услуг под риском: {at_risk_services}; добавка {bonus:g} баллов до ограничения100",
                base_score, uncapped, related))
        customer_score = min(100.0, uncapped)
        if uncapped > 100:
            customer_rules.append(explanation_rule("score_cap", "customer", None,
                "Ограничение итогового score: 100", uncapped, customer_score))
        customer_level = level_for(customer_score, settings["thresholds"])
        counts[customer_level] += 1
        scored_scores.append(customer_score)

        scorable_price = sum(int(service["price"]) for service, _ in scored)
        coverage = min(1.0, available / scorable_price) if scorable_price else 0.0
        mitigation = settings["money"]["balanceMitigation"] * coverage
        expected_loss = 0
        amount_at_risk = 0
        covered_loss = 0
        services_out: list[dict[str, Any]] = []
        driver_bag: dict[tuple[str, str], float] = defaultdict(float)
        for service, result in scored:
            probability_value = probability(result["score"], settings)
            loss = probability_value * int(service["price"]) * (1.0 - mitigation)
            expected_loss += round(loss)
            covered_loss += round(probability_value * int(service["price"]) * mitigation)
            if result["score"] >= settings["thresholds"]["medium"]:
                amount_at_risk += int(service["price"])
                total_services_at_risk += 1
            services_out.append(_service_detail(service, result, settings))
            for driver in result["drivers"]:
                driver_bag[(driver["code"], driver["label"])] += driver["contribution"]

        drivers = [
            {"code": code, "label": label, "contribution": round(contribution, 3)}
            for (code, label), contribution in sorted(
                driver_bag.items(), key=lambda item: item[1], reverse=True
            )[:4]
        ]
        top_service, top_result = max(scored, key=lambda pair: pair[1]["score"])
        labels = [
            driver["label"][0].lower() + driver["label"][1:]
            for driver in top_result["drivers"][:2]
        ]
        summary_text = f"{top_service['name']}: {', '.join(labels)}" if labels else {
            "low": "Риск ниже порога", "medium": "Средний риск", "high": "Высокий риск"
        }[customer_level]
        rule_labels = [rule["label"] for rule in top_result["explanationRules"] + customer_rules]
        if rule_labels:
            summary_text += "; " + "; ".join(rule_labels)
        remaining = len(scored) - 1
        if remaining > 0:
            if remaining % 10 == 1 and remaining % 100 != 11:
                word = "услуга"
            elif 2 <= remaining % 10 <= 4 and not 12 <= remaining % 100 <= 14:
                word = "услуги"
            else:
                word = "услуг"
            summary_text += f"; ещё {remaining} {word}"
        confidence = round(sum(result["confidence"] for _, result in scored) / len(scored), 2)

        total_loss += expected_loss
        total_risk += amount_at_risk
        total_available += available
        total_price += scorable_price
        coverage_values.append(coverage)
        if coverage < 1:
            underfunded += 1
        customers.append(
            {
                "id": account["id"],
                "email": account["email"],
                "balanceCents": int(account["balance"]),
                "withdrawCents": int(account["withdraw_balance"]),
                "bonusCents": int(account["bonus_balance"]),
                "bonusState": account["bonus_state"],
                "totalReplenishedCents": int(account["total_replenished"]),
                "score": round(customer_score, 1),
                "level": customer_level,
                "confidence": confidence,
                "summaryText": summary_text,
                "explanationRules": customer_rules,
                "drivers": drivers,
                "services": services_out,
                "money": {
                    "amountAtRiskCents": amount_at_risk,
                    "expectedLossCents": expected_loss,
                    "coveredLossCents": covered_loss,
                    "coverage": round(coverage, 4),
                    "mitigation": round(mitigation, 4),
                },
                "unknownReason": None,
                "isEstimated": True,
            }
        )

    summary = {
        "countsByLevel": counts,
        "totalCustomers": len(customers),
        "scoredCustomers": len(scored_scores),
        "servicesAtRisk": total_services_at_risk,
        "expectedLossCents": total_loss,
        "amountAtRiskCents": total_risk,
        "coverage": round(sum(coverage_values) / len(coverage_values), 4) if coverage_values else 0.0,
        "aggregateCoverage": round(min(1.0, total_available / total_price), 4) if total_price else 0.0,
        "underfundedCustomers": underfunded,
        "avgScore": round(sum(scored_scores) / len(scored_scores), 1) if scored_scores else None,
        "asOf": iso_z(as_of),
        "updatedAt": iso_z(updated_at),
        "currency": "EUR",
    }
    customers.sort(
        key=lambda item: (item["score"] is not None, item["score"] or -1, item["money"]["expectedLossCents"]),
        reverse=True,
    )
    return {"customers": customers, "summary": summary}
