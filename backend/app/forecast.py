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
    "Столбцы справа — прогноз: срок истекает, оценка непродления рассчитана по баллу риска. Это экспертная модель, а не подтверждённая вероятность. Заблокированные и удалённые услуги исключены. Текущий день разделён по времени среза (UTC)."
)


def _day(value: datetime) -> str:
    return value.astimezone(timezone.utc).date().isoformat()


def build_forecast(
    customers: list[dict[str, Any]],
    as_of: datetime,
    settings: dict[str, Any],
    past_days: int = 30,
    horizon_days: int = 30,
    bucket_days: int = 1,
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
        for offset in range(horizon_days + 1)
    }
    services_at_risk = 0

    for customer in customers:
        mitigation = float(customer.get("money", {}).get("mitigation") or 0.0)
        for service in customer.get("services") or []:
            if service.get("status") in ("deleted", "blocked"):
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

    fact_points = _bucketize_fact(fact, bucket_days)
    forecast_points = _bucketize_forecast(forecast, bucket_days)
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


def _chunks(keys: list[str], size: int) -> list[list[str]]:
    return [keys[index:index + size] for index in range(0, len(keys), size)]


def _bucketize_fact(points: dict[str, dict[str, Any]], size: int) -> list[dict[str, Any]]:
    keys = sorted(points)
    result = []
    for chunk in _chunks(keys, max(1, size)):
        customers: set[int] = set()
        for key in chunk:
            customers |= points[key]["customers"]
        result.append(
            {
                "date": chunk[0],
                "end": chunk[-1],
                "services": sum(points[key]["services"] for key in chunk),
                "customers": len(customers),
            }
        )
    return result


def _bucketize_forecast(points: dict[str, dict[str, Any]], size: int) -> list[dict[str, Any]]:
    keys = sorted(points)
    result = []
    for chunk in _chunks(keys, max(1, size)):
        result.append(
            {
                "date": chunk[0],
                "end": chunk[-1],
                "services": sum(points[key]["services"] for key in chunk),
                "expectedNonRenewals": round(sum(points[key]["expected"] for key in chunk), 2),
                "expectedLossCents": sum(points[key]["loss"] for key in chunk),
            }
        )
    return result


def range_details(
    customers: list[dict[str, Any]],
    as_of: datetime,
    start_date: str,
    end_date: str,
    kind: str,
    settings: dict[str, Any],
    limit: int = 200,
    window_end: datetime | None = None,
) -> dict[str, Any]:
    """Услуги диапазона дат: факт (уже истекли) или прогноз (истекают)."""
    from datetime import date as date_type

    first = date_type.fromisoformat(start_date)
    last = date_type.fromisoformat(end_date)
    rows: list[dict[str, Any]] = []
    customers_with_events: set[int] = set()
    expected_total = 0.0
    loss_total = 0

    for customer in customers:
        mitigation = float(customer.get("money", {}).get("mitigation") or 0.0)
        for service in customer.get("services") or []:
            if service.get("status") in ("deleted", "blocked"):
                continue
            expires = parse_iso(service["expiresAt"])
            expires_date = expires.astimezone(timezone.utc).date()
            if not (first <= expires_date <= last):
                continue
            if kind == "fact" and expires > as_of:
                continue
            if kind == "forecast" and (expires <= as_of or (window_end is not None and expires > window_end)):
                continue

            customers_with_events.add(customer["id"])
            chance = None
            loss = None
            if kind == "forecast":
                chance = probability(float(service["score"]), settings)
                loss = round(chance * int(service["priceCents"]) * (1.0 - mitigation))
                expected_total += chance
                loss_total += loss

            rows.append(
                {
                    "serviceId": int(service["id"]),
                    "serviceName": service["name"],
                    "customerId": int(customer["id"]),
                    "email": customer["email"],
                    "priceCents": int(service["priceCents"]),
                    "score": float(service["score"]),
                    "level": service.get("level"),
                    "status": service.get("status"),
                    "expiresAt": service["expiresAt"],
                    "probability": None if chance is None else round(chance, 3),
                    "expectedLossCents": loss,
                }
            )

    if kind == "forecast":
        rows.sort(key=lambda row: (row["expectedLossCents"] or 0, row["priceCents"]), reverse=True)
    else:
        rows.sort(key=lambda row: (row["priceCents"], row["score"]), reverse=True)

    return {
        "date": start_date,
        "end": end_date,
        "kind": kind,
        "services": len(rows),
        "customers": len(customers_with_events),
        "expectedNonRenewals": round(expected_total, 2),
        "expectedLossCents": loss_total,
        "items": rows[:limit],
        "truncated": len(rows) > limit,
    }


def export_rows(
    customers: list[dict[str, Any]],
    as_of: datetime,
    settings: dict[str, Any],
    kind: str = "all",
    past_days: int = 30,
    horizon_days: int = 30,
    bucket_days: int = 7,
) -> list[dict[str, Any]]:
    """Плоский список услуг для CSV: факт, прогноз или оба, с недельными интервалами."""
    from datetime import date as date_type

    as_of_date = as_of.astimezone(timezone.utc).date()
    fact_start = as_of_date - timedelta(days=past_days - 1)
    forecast_start = as_of_date
    horizon_end = as_of_date + timedelta(days=horizon_days)
    rows: list[dict[str, Any]] = []

    for customer in customers:
        mitigation = float(customer.get("money", {}).get("mitigation") or 0.0)
        for service in customer.get("services") or []:
            if service.get("status") in ("deleted", "blocked"):
                continue
            expires = parse_iso(service["expiresAt"])
            expires_date = expires.astimezone(timezone.utc).date()
            chance = None
            loss = None
            if expires <= as_of:
                if kind not in ("fact", "all") or expires_date < fact_start:
                    continue
                index = (expires_date - fact_start).days
                bucket = index // bucket_days
                week_start = fact_start + timedelta(days=bucket * bucket_days)
                week_end = min(week_start + timedelta(days=bucket_days - 1), as_of_date)
                row_kind = "fact"
            else:
                if kind not in ("forecast", "all") or expires > as_of + timedelta(days=horizon_days):
                    continue
                index = (expires_date - forecast_start).days
                bucket = index // bucket_days
                week_start = forecast_start + timedelta(days=bucket * bucket_days)
                week_end = min(week_start + timedelta(days=bucket_days - 1), horizon_end)
                chance = probability(float(service["score"]), settings)
                loss = round(chance * int(service["priceCents"]) * (1.0 - mitigation))
                row_kind = "forecast"

            rows.append(
                {
                    "kind": row_kind,
                    "weekStart": week_start.isoformat(),
                    "weekEnd": week_end.isoformat(),
                    "expiresOn": expires_date.isoformat(),
                    "serviceId": int(service["id"]),
                    "serviceName": service["name"],
                    "customerId": int(customer["id"]),
                    "email": customer["email"],
                    "priceCents": int(service["priceCents"]),
                    "score": float(service["score"]),
                    "level": service.get("level"),
                    "probability": None if chance is None else round(chance, 4),
                    "expectedLossCents": loss,
                    "status": service.get("status"),
                }
            )

    rows.sort(key=lambda row: (row["kind"] != "fact", row["weekStart"], -(row["expectedLossCents"] or 0),
                               -row["priceCents"]))
    return rows
