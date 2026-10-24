"""Прогноз оттока по срокам оплаты.

Факт и прогноз разделены намеренно:
- факт — услуги, у которых оплаченный период уже истёк в снимке, но услуга
  ещё не удалена (значит, не продлена);
- прогноз — услуги, у которых срок истекает в ближайшие дни; вероятность
  непродления берётся из уже посчитанного score.

Исторических удалений здесь нет: в исходных данных отсутствует дата удаления,
поэтому «когда клиент ушёл» восстановить нельзя. Это ограничение вынесено в note.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from .scoring import parse_iso, probability

NOTE = (
    "Исторических удалений нет: в данных отсутствует дата удаления услуги. "
    "Столбцы слева — факт по текущему снимку: срок истёк, услуга не продлена. "
    "Столбцы справа — прогноз: срок истекает, вероятность непродления взята из score."
)


def _day(value: datetime) -> str:
    return value.astimezone(timezone.utc).date().isoformat()


def build_forecast(
    customers: list[dict[str, Any]],
    as_of: datetime,
    settings: dict[str, Any],
    past_days: int = 30,
    horizon_days: int = 30,
) -> dict[str, Any]:
    start = as_of - timedelta(days=past_days)
    end = as_of + timedelta(days=horizon_days)

    # Окно факта включает текущий день: услуга могла истечь утром до среза.
    fact: dict[str, dict[str, Any]] = {
        _day(as_of - timedelta(days=past_days - 1 - offset)): {"services": 0, "customers": set()}
        for offset in range(past_days)
    }
    forecast: dict[str, dict[str, Any]] = {
        _day(as_of + timedelta(days=offset)): {"services": 0, "expected": 0.0, "loss": 0}
        for offset in range(1, horizon_days + 1)
    }
    services_at_risk = 0

    for customer in customers:
        mitigation = float(customer.get("money", {}).get("mitigation") or 0.0)
        for service in customer.get("services") or []:
            if service.get("status") == "deleted":
                continue
            expires = parse_iso(service["expiresAt"])
            if expires <= as_of:
                key = _day(expires)
                if key in fact:
                    fact[key]["services"] += 1
                    fact[key]["customers"].add(customer["id"])
                continue
            if expires > end:
                continue
            key = _day(expires)
            if key not in forecast:
                continue
            chance = probability(float(service["score"]), settings)
            forecast[key]["services"] += 1
            forecast[key]["expected"] += chance
            forecast[key]["loss"] += round(chance * int(service["priceCents"]) * (1.0 - mitigation))
            if service.get("level") in ("high", "medium"):
                services_at_risk += 1

    fact_points = [
        {"date": key, "services": value["services"], "customers": len(value["customers"])}
        for key, value in sorted(fact.items())
    ]
    forecast_points = [
        {
            "date": key,
            "services": value["services"],
            "expectedNonRenewals": round(value["expected"], 2),
            "expectedLossCents": int(value["loss"]),
        }
        for key, value in sorted(forecast.items())
    ]
    return {
        "asOf": as_of.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "pastDays": past_days,
        "horizonDays": horizon_days,
        "currency": "EUR",
        "fact": fact_points,
        "forecast": forecast_points,
        "totals": {
            "factServices": sum(point["services"] for point in fact_points),
            "factCustomers": len({customer for value in fact.values() for customer in value["customers"]}),
            "forecastServices": sum(point["services"] for point in forecast_points),
            "servicesAtRisk": services_at_risk,
            "expectedNonRenewals": round(sum(point["expectedNonRenewals"] for point in forecast_points), 2),
            "expectedLossCents": sum(point["expectedLossCents"] for point in forecast_points),
        },
        "note": NOTE,
    }
