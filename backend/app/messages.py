"""Понятные маркетологу тексты: короткая причина, подробности и письмо клиенту.

Тексты собираются из уже сохранённых результатов расчёта, поэтому одинаковы для
карточки, письма и повторных запросов. ML/LLM не используются: шаблоны детерминированы.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

MONTHS = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)

LEVEL_LABEL = {"high": "высокий", "medium": "средний", "low": "низкий"}

SITUATION_LABEL = {
    "prolong_wait": "Ждёт оплаты",
    "blocked": "Заблокирована",
    "suspended": "Платит за выключенную услугу",
    "funds_gap": "Не хватает денег",
    "expiry_auto_off": "Скоро закончится",
    "unknown": "Нет оценки",
    "on_track": "Плановое продление",
}

STATUS_TITLE = {
    "prolong_wait": "ждёт оплаты",
    "blocked": "заблокирована",
    "suspended": "выключена",
    "active": "активна",
    "deleted": "удалена",
}


def money_text(cents: int | float | None) -> str:
    value = int(round(float(cents or 0)))
    sign = "−" if value < 0 else ""
    whole, frac = divmod(abs(value), 100)
    grouped = f"{whole:,}".replace(",", "\u00a0")
    return f"{sign}{grouped},{frac:02d} €"


def day_month(value: str | None) -> str:
    if not value:
        return "без даты"
    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return f"{moment.day} {MONTHS[moment.month - 1]}"


def plural(count: int, one: str, few: str, many: str) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return one
    if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        return few
    return many


def expiry_phrase(days: float | None) -> str:
    if days is None:
        return "срок неизвестен"
    if days < -1:
        return f"просрочена на {abs(round(days))} {plural(abs(round(days)), 'день', 'дня', 'дней')}"
    if days < 0:
        return "истекла вчера"
    if days < 0.5:
        return f"через {max(1, round(days * 24))} {plural(max(1, round(days * 24)), 'час', 'часа', 'часов')}"
    if days < 1:
        return "сегодня"
    return f"через {round(days)} {plural(round(days), 'день', 'дня', 'дней')}"


def _available(customer: dict[str, Any]) -> int:
    if customer.get("availableCents") is not None:
        return int(customer["availableCents"])
    total = int(customer.get("balanceCents") or 0)
    if customer.get("bonusState") == "unlocked":
        total += int(customer.get("bonusCents") or 0)
    return total


def _services(customer: dict[str, Any]) -> list[dict[str, Any]]:
    return [s for s in customer.get("services") or [] if s.get("level") != "unknown"]


def _main_service(customer: dict[str, Any]) -> dict[str, Any] | None:
    services = _services(customer)
    if not services:
        return None
    return max(services, key=lambda s: (s.get("score") or 0, s.get("priceCents") or 0))


def _at_risk(customer: dict[str, Any]) -> list[dict[str, Any]]:
    return [s for s in _services(customer) if s.get("level") in ("high", "medium")]


def _situation(customer: dict[str, Any], service: dict[str, Any] | None, available: int) -> str:
    if customer.get("score") is None:
        return "unknown"
    if service is None:
        return "unknown"
    status = service.get("status")
    if status == "prolong_wait":
        return "prolong_wait"
    if status == "blocked":
        return "blocked"
    if status == "suspended":
        return "suspended"
    if (service.get("priceCents") or 0) > 0 and available < int(service["priceCents"]):
        return "funds_gap"
    days = service.get("expiryDays")
    if not service.get("autoProlong") and days is not None and days <= 7:
        return "expiry_auto_off"
    return "on_track"


def _money_gap(customer: dict[str, Any], service: dict[str, Any], available: int) -> int:
    return max(0, int(service.get("priceCents") or 0) - available)


def _deletion_date(service: dict[str, Any]) -> str:
    """prolong_wait держится 5 дней после истечения оплаченного периода."""
    expires = service.get("expiresAt")
    if not expires:
        return "без даты"
    moment = datetime.fromisoformat(expires.replace("Z", "+00:00")) + timedelta(days=5)
    return f"{moment.day} {MONTHS[moment.month - 1]}"


def _headline(customer: dict[str, Any], situation: str, service: dict[str, Any] | None, available: int) -> str:
    if situation == "unknown":
        return customer.get("unknownReason") or "Недостаточно данных для оценки"
    name = service.get("name") if service else "услуга"
    price = money_text(service.get("priceCents") if service else 0)
    days = service.get("expiryDays") if service else None
    if situation == "prolong_wait":
        deadline = _deletion_date(service)
        return f"{name} ждёт оплаты: {price} нужно внести до {deadline}, иначе услуга удалится."
    if situation == "blocked":
        return f"{name} заблокирована — клиент не может ей пользоваться, продлить услугу нельзя. Уточните причину блокировки; это не прогноз будущего продления."
    if situation == "suspended":
        return f"{name} выключена, но списание {price} продолжается."
    if situation == "funds_gap":
        gap = money_text(_money_gap(customer, service, available))
        return f"На продление {name} нужно {price}, на балансе {money_text(available)} — не хватает {gap}."
    if situation == "expiry_auto_off":
        verb = "закончилась" if (days or 0) < 0 else "заканчивается"
        return f"{name} {verb} {day_month(service.get('expiresAt'))}, автопродление отключено."
    return f"Плановое продление {name} — {expiry_phrase(days)}, {price}."


def _details(customer: dict[str, Any], situation: str, service: dict[str, Any] | None, available: int) -> list[str]:
    facts: list[str] = []
    if situation == "unknown":
        facts.append("В этом снимке нет услуг, по которым можно посчитать риск.")
        facts.append("Причины: " + (customer.get("unknownReason") or "недостаточно данных").lower() + ".")
        return facts

    name = service.get("name") if service else "услуга"
    price = int(service.get("priceCents") or 0) if service else 0
    days = service.get("expiryDays") if service else None

    if situation == "prolong_wait":
        facts.append(
            f"{name} ждёт оплаты с {day_month(service.get('expiresAt'))}: {money_text(price)} "
            f"нужно внести до {_deletion_date(service)} — это 5 дней после окончания периода."
        )
    elif situation == "blocked":
        facts.append(f"{name} заблокирована: продлить или пользоваться услугой сейчас нельзя.")
    elif situation == "suspended":
        facts.append(f"{name} выключена по запросу клиента, но оплата за неё продолжается.")
    else:
        facts.append(f"{name} истекает {day_month(service.get('expiresAt'))} — {expiry_phrase(days)}.")

    if price > 0:
        facts.append(f"Стоимость продления: {money_text(price)}. Доступно на балансе: {money_text(available)}.")
    if situation not in ("prolong_wait", "blocked", "suspended"):
        gap = _money_gap(customer, service, available)
        if gap:
            facts.append(f"Не хватает {money_text(gap)}.")
    if not service.get("autoProlong"):
        facts.append("Автопродление отключено: автоматически услуга не продлится.")

    at_risk = _at_risk(customer)
    if at_risk:
        total = sum(int(s.get("priceCents") or 0) for s in at_risk)
        facts.append(
            f"Под риском {len(at_risk)} {plural(len(at_risk), 'услуга', 'услуги', 'услуг')} "
            f"на {money_text(total)}; ожидаемые потери — {money_text(customer.get('money', {}).get('expectedLossCents'))}."
        )
    if customer.get("bonusBalance", 0) > 0 and customer.get("bonusState") != "unlocked":
        facts.append(
            f"Бонусный баланс ({money_text(customer['bonusBalance'])}) заблокирован (bonusState: locked) и не может покрыть оплату."
        )
    score = customer.get("score")
    if score is not None:
        facts.append(f"Оценка риска: {round(score)} из 100 — {LEVEL_LABEL.get(customer.get('level'), 'неизвестный')} уровень.")
    return facts


def _email(
    customer: dict[str, Any], situation: str, service: dict[str, Any] | None, available: int
) -> dict[str, Any]:
    email = customer.get("email") or ""
    name = service.get("name") if service else "услуга"
    price = money_text(service.get("priceCents") if service else 0)
    days = service.get("expiryDays") if service else None
    deadline = day_month(service.get("expiresAt")) if service else "без даты"
    deletion = _deletion_date(service) if service else "без даты"
    gap = money_text(_money_gap(customer, service, available)) if service else money_text(0)

    subject = f"{name}: проверим состояние услуги"
    body = "Здравствуйте!\n\n"
    if situation == "unknown":
        subject = "Уточним информацию по услугам Aéza"
        body += "В текущем снимке недостаточно данных для оценки ваших услуг. Проверьте их состояние в личном кабинете или обратитесь в поддержку."
    elif situation == "blocked":
        body += f"Услуга {name} заблокирована. Пользоваться и продлевать её сейчас нельзя. Обратитесь в поддержку, чтобы уточнить причину блокировки и доступные действия."
    else:
        body += f"Услуга {name}: стоимость продления {price}, окончание оплаченного периода — {deadline}. "
        if situation == "suspended":
            body += "Услуга выключена, но оплата продолжается. Проверьте, нужна ли она вам. "
        if situation == "prolong_wait":
            body += "Услуга ожидает оплаты. По правилам кейса через 5 дней после окончания периода она удаляется. Проверьте актуальный статус в личном кабинете. "
        body += f"В расчёте доступно {money_text(available)}; недостающая сумма — {gap}. "
        if service and service.get("autoProlong"):
            body += "Автопродление включено. Проверьте, достаточно ли средств для автоматического списания."
        else:
            body += "Автопродление отключено. Если хотите продолжить пользоваться услугой, продлите её в личном кабинете."
        if customer.get("withdrawCents", 0):
            body += " Реферальные средства перед оплатой нужно перевести на основной баланс; автоматически они не списываются."
    body += "\n\nЕсли нужна помощь, обратитесь в поддержку Aéza.\nКоманда Aéza"

    return {
        "situation": situation,
        "situationLabel": SITUATION_LABEL[situation],
        "subject": subject,
        "body": body,
        "recipient": email,
        "serviceId": service.get("id") if service else None,
        "serviceName": service.get("name") if service else None,
    }


def build_customer_messages(customer: dict[str, Any]) -> dict[str, Any]:
    """Возвращает summaryText, summaryDetails и emailDraft для карточки клиента."""
    available = _available(customer)
    service = _main_service(customer)
    situation = _situation(customer, service, available)
    return {
        "summaryText": _headline(customer, situation, service, available),
        "summaryDetails": _details(customer, situation, service, available),
        "emailDraft": _email(customer, situation, service, available),
    }
