#!/usr/bin/env python3
"""Offline preview of the churn model on the seed dataset.

This is a prototype for validating the model with the team; it is not the
production API.  It reads the same JSON shape as the source fixture and prints
a customer ranking plus money estimates.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

WEIGHTS = {
    "expiry_pressure": 0.40,
    "funds_gap": 0.25,
    "autorenew_off": 0.10,
    "status_pressure": 0.10,
    "payment_history": 0.10,
    "commitment": 0.05,
}
THRESHOLDS = {"medium": 40.0, "high": 70.0}
STATUS_FLOORS = {"prolong_wait": 70.0, "blocked": 60.0, "stale": 70.0}
BALANCE_MITIGATION = 0.5
PROB = {"midpoint": 65.0, "steepness": 12.0, "floor": 0.02, "ceiling": 0.95}


def parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def eur(cents: float) -> str:
    return f"€{cents / 100:.2f}"


def probability(score: float) -> float:
    raw = 1.0 / (1.0 + math.exp(-(score - PROB["midpoint"]) / PROB["steepness"]))
    return max(PROB["floor"], min(PROB["ceiling"], raw))


def level(score: float | None) -> str:
    if score is None:
        return "unknown"
    if score >= THRESHOLDS["high"]:
        return "high"
    if score >= THRESHOLDS["medium"]:
        return "medium"
    return "low"


def available_cents(account: dict) -> int:
    value = account["balance"] + account["withdrawBalance"]
    if account["bonusState"] == "unlocked":
        value += account["bonusBalance"]
    return value


def expiry_value(service: dict, available: int, now: datetime) -> tuple[float | None, str]:
    expires = parse_iso(service["expiresAt"])
    days = (expires - now).total_seconds() / 86400
    if days < 0:
        value = 1.0
        label = f"Срок истёк {abs(days):.0f} дн. назад"
    elif days <= 3:
        value = 1.0
        label = f"До окончания {days:.1f} дн."
    elif days <= 7:
        value = 0.75
        label = f"До окончания {days:.1f} дн."
    elif days <= 14:
        value = 0.5
        label = f"До окончания {days:.1f} дн."
    elif days <= 30:
        value = 0.25
        label = f"До окончания {days:.0f} дн."
    else:
        value = 0.05
        label = f"До окончания {days:.0f} дн."
    if service["autoProlong"] and available >= service["price"]:
        value *= 0.4
        label += ", автопродление включено"
    return value, label


def status_value(service: dict, now: datetime) -> tuple[float, bool, str]:
    status = service["status"]
    expires = parse_iso(service["expiresAt"])
    stale = False
    if status in ("active", "suspended") and expires < now:
        stale = True
    if status == "prolong_wait" and (expires - now).days < -5:
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


def score_service(service: dict, account: dict, transactions: list[dict], prices: dict[int, int], now: datetime) -> dict:
    available = available_cents(account)
    expiry, expiry_label = expiry_value(service, available, now)
    if service["price"] <= 0:
        funds = None
        funds_label = "Цена услуги не указана"
    elif available < service["price"]:
        funds = 1.0
        funds_label = f"Баланса {eur(available)} не хватает на {eur(service['price'])}"
    else:
        funds = max(0.0, 0.3 * (1.0 - available / (3.0 * service["price"])))
        funds_label = f"Запас баланса {eur(available)}"
    auto = 0.0 if service["autoProlong"] else 1.0
    status, stale, status_label = status_value(service, now)

    tx = [t for t in transactions if t["serviceId"] == service["id"]]
    if not tx:
        history = None
        history_label = "Нет транзакций"
    elif any(t["status"] == "not_performed" and t["type"] == "prolong" for t in tx):
        history = 1.0
        history_label = "Есть неоплаченное продление"
    elif any(t["status"] == "not_performed" and t["type"] == "order" for t in tx):
        history = 0.6
        history_label = "Есть неоплаченный заказ"
    else:
        history = 0.0
        history_label = "Неоплаченных счетов нет"

    total_price = sum(prices[sid] for sid in prices if prices[sid] > 0)
    if total_price <= 0:
        commitment = None
        commitment_label = "Нет цены услуг"
    else:
        commitment = 1.0 - min(1.0, account["totalReplenished"] / (3.0 * total_price))
        commitment_label = "Мало пополнений относительно стоимости"

    values = {
        "expiry_pressure": (expiry, expiry_label),
        "funds_gap": (funds, funds_label),
        "autorenew_off": (auto, "Автопродление отключено"),
        "status_pressure": (status, status_label),
        "payment_history": (history, history_label),
        "commitment": (commitment, commitment_label),
    }
    total_weight = sum(WEIGHTS.values())
    score = 0.0
    confidence = 0.0
    drivers = []
    for code, (value, label) in values.items():
        weight = WEIGHTS[code]
        if value is None:
            value = 0.5
        else:
            confidence += weight / total_weight
        contribution = (weight / total_weight) * value
        score += contribution
        if contribution > 0.01:
            drivers.append({"code": code, "label": label, "contribution": round(contribution, 3), "value": round(value, 3)})
    score *= 100.0
    if status == 1.0 and service["status"] == "prolong_wait":
        score = max(score, STATUS_FLOORS["prolong_wait"])
    elif service["status"] == "blocked":
        score = max(score, STATUS_FLOORS["blocked"])
    if stale:
        score = max(score, STATUS_FLOORS["stale"])
    drivers.sort(key=lambda item: item["contribution"], reverse=True)
    return {
        "score": round(score, 1),
        "confidence": round(confidence, 2),
        "stale": stale,
        "drivers": drivers[:4],
        "values": {code: (round(value, 2) if value is not None else None) for code, (value, _) in values.items()},
        "expiryDays": round((parse_iso(service["expiresAt"]) - now).total_seconds() / 86400, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/seed.json", type=Path)
    parser.add_argument("--meta", default="data/seed.meta.json", type=Path)
    parser.add_argument("--as-of", default=None)
    parser.add_argument("--json", default=None, type=Path)
    parser.add_argument("--top", default=20, type=int)
    args = parser.parse_args()

    data = json.loads(args.data.read_text(encoding="utf-8"))
    as_of_raw = args.as_of
    if not as_of_raw and args.meta.exists():
        as_of_raw = json.loads(args.meta.read_text(encoding="utf-8")).get("asOf")
    now = parse_iso(as_of_raw) if as_of_raw else datetime.now(timezone.utc)

    accounts = {a["id"]: a for a in data["accounts"]}
    services_by_owner = defaultdict(list)
    for service in data["services"]:
        services_by_owner[service["ownerId"]].append(service)
    prices = {s["ownerId"]: sum(x["price"] for x in services_by_owner[s["ownerId"]]) for s in data["services"]}

    results = []
    for account in data["accounts"]:
        svc = services_by_owner[account["id"]]
        scored = []
        for service in svc:
            if service["status"] == "deleted":
                continue
            result = score_service(service, account, data["transactions"], prices, now)
            if result["confidence"] < 0.5:
                continue
            scored.append((service, result))
        if not scored:
            reason = "Все услуги удалены" if svc and all(s["status"] == "deleted" for s in svc) else "Недостаточно данных"
            results.append({"id": account["id"], "email": account["email"], "score": None, "level": "unknown", "reason": reason, "services": [], "money": {}})
            continue
        customer_score = min(100.0, max(r["score"] for _, r in scored) + 4.0 * max(0, sum(1 for _, r in scored if r["score"] >= 40) - 1))
        scorable = [s for s, _ in scored]
        total_price = sum(s["price"] for s in scorable)
        available = available_cents(account)
        coverage = min(1.0, available / total_price) if total_price else 0.0
        mitigation = BALANCE_MITIGATION * coverage
        expected_loss = 0.0
        amount_at_risk = 0.0
        covered_loss = 0.0
        services_out = []
        for service, result in scored:
            p = probability(result["score"])
            loss = p * service["price"] * (1.0 - mitigation)
            expected_loss += loss
            covered_loss += p * service["price"] * mitigation
            if result["score"] >= 40:
                amount_at_risk += service["price"]
            services_out.append({
                "id": service["id"], "name": service["name"], "status": service["status"],
                "paymentTerm": service["paymentTerm"], "price": service["price"] / 100,
                "autoProlong": service["autoProlong"], "expiresAt": service["expiresAt"],
                "score": result["score"], "confidence": result["confidence"],
                "staleStatus": result["stale"], "drivers": result["drivers"],
                "values": result["values"], "expiryDays": result["expiryDays"],
            })
        results.append({
            "id": account["id"], "email": account["email"], "score": round(customer_score, 1),
            "level": level(customer_score), "reason": None,
            "confidence": round(sum(r["confidence"] for _, r in scored) / len(scored), 2),
            "drivers": sorted([d for _, r in scored for d in r["drivers"]], key=lambda x: x["contribution"], reverse=True)[:4],
            "money": {
                "amountAtRisk": round(amount_at_risk / 100, 2),
                "expectedLoss": round(expected_loss / 100, 2),
                "coveredLoss": round(covered_loss / 100, 2),
                "coverage": round(coverage, 3),
                "mitigation": round(mitigation, 3),
            },
            "services": services_out,
        })

    results.sort(key=lambda r: (r["score"] is not None, r["score"] or -1, r["money"].get("expectedLoss", 0)), reverse=True)
    counts = {"high": 0, "medium": 0, "low": 0, "unknown": 0}
    for r in results:
        counts[r["level"]] += 1

    print(f"AS OF {now.isoformat()}  customers={len(results)}")
    print(f"{'ID':>3} {'email':<24} {'score':>5} {'level':<7} {'at risk':>9} {'loss':>8} {'cov':>5}  drivers")
    for r in results[: args.top]:
        drivers = "; ".join(d["label"] for d in r.get("drivers", [])[:2]) or r.get("reason") or ""
        money = r.get("money", {})
        score = f"{r['score']:.1f}" if r["score"] is not None else "—"
        print(f"{r['id']:3} {r['email']:<24} {score:>5} {r['level']:<7} {money.get('amountAtRisk', 0):9.2f} {money.get('expectedLoss', 0):8.2f} {money.get('coverage', 0):5.2f}  {drivers}")
    total_loss = sum(r.get("money", {}).get("expectedLoss", 0) for r in results)
    total_risk = sum(r.get("money", {}).get("amountAtRisk", 0) for r in results)
    print(f"\nlevels={counts}  expectedLoss=€{total_loss:.2f}  amountAtRisk=€{total_risk:.2f}")

    if args.json:
        payload = {"asOf": now.isoformat(), "counts": counts, "totalExpectedLoss": round(total_loss, 2), "totalAmountAtRisk": round(total_risk, 2), "customers": results}
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
