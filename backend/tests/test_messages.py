import pytest

from app.messages import build_customer_messages, money_text, plural
from .conftest import login


def customer(**overrides):
    base = {
        "id": 1,
        "email": "client@example.test",
        "balanceCents": 300,
        "withdrawCents": 0,
        "bonusCents": 0,
        "bonusState": "locked",
        "totalReplenishedCents": 107726,
        "availableCents": 300,
        "score": 89.0,
        "level": "high",
        "confidence": 1.0,
        "money": {"amountAtRiskCents": 1097, "expectedLossCents": 644,
                  "coveredLossCents": 94, "coverage": 0.25, "mitigation": 0.125},
        "services": [
            {"id": 6, "name": "service-0006", "priceCents": 550, "status": "active",
             "autoProlong": False, "expiresAt": "2026-10-25T21:00:00Z", "expiryDays": 2.0,
             "score": 85.0, "level": "high", "staleStatus": False},
        ],
        "unknownReason": None,
    }
    base.update(overrides)
    return base


def test_money_text():
    assert money_text(550) == "5,50 €"
    assert money_text(107726) == "1\u00a0077,26 €"
    assert money_text(0) == "0,00 €"


def test_plural():
    assert [plural(n, "услуга", "услуги", "услуг") for n in (1, 2, 5, 11, 21)] == \
        ["услуга", "услуги", "услуг", "услуг", "услуга"]


def test_funds_gap_is_short_and_human():
    message = build_customer_messages(customer())
    assert message["summaryText"] == "На продление service-0006 нужно 5,50 €, на балансе 3,00 € — не хватает 2,50 €."
    assert message["emailDraft"]["situation"] == "funds_gap"
    for fact in message["summaryDetails"]:
        assert "добавк" not in fact and "минимум" not in fact and "ограничени" not in fact


@pytest.mark.parametrize("status,expected", [
    ("prolong_wait", "prolong_wait"),
    ("blocked", "blocked"),
    ("suspended", "suspended"),
])
def test_status_situations(status, expected):
    message = build_customer_messages(customer(
        services=[dict(customer()["services"][0], status=status)]))
    assert message["emailDraft"]["situation"] == expected
    assert message["emailDraft"]["body"].startswith("Здравствуйте!")


def test_expiry_without_autorenew_is_detected_when_zero_days_left():
    """0.0 дней — валидное значение, а не отсутствие данных."""
    message = build_customer_messages(customer(
        availableCents=83810,
        services=[dict(customer()["services"][0], priceCents=95, expiresAt="2026-10-23T22:00:00Z",
                       expiryDays=0.0)]))
    assert message["emailDraft"]["situation"] == "expiry_auto_off"
    assert "автопродление отключено" in message["summaryText"]


def test_unknown_customer_keeps_reason_and_has_winback_email():
    message = build_customer_messages(customer(
        score=None, level="unknown", services=[], money={"expectedLossCents": 0, "amountAtRiskCents": 0},
        unknownReason="Все услуги удалены"))
    assert message["summaryText"] == "Все услуги удалены"
    assert message["emailDraft"]["situation"] == "unknown"
    assert "услуг" in message["emailDraft"]["subject"].lower()


def test_email_uses_client_address_and_no_placeholders():
    draft = build_customer_messages(customer())["emailDraft"]
    assert draft["recipient"] == "client@example.test"
    assert "{" not in draft["body"] and "}" not in draft["body"]
    assert draft["serviceName"] == "service-0006"


@pytest.mark.parametrize("customer_id", range(1, 11))
def test_seed_customers_get_readable_messages(client, customer_id):
    login(client)
    detail = client.get(f"/api/v1/customers/{customer_id}").json()
    assert detail["summary"]
    assert detail["summaryDetails"]
    assert not any(word in detail["summary"] for word in ("добавк", "минимум", "ограничени"))
    draft = detail["emailDraft"]
    assert draft["subject"] and draft["body"].startswith("Здравствуйте!")
    assert draft["recipient"] == detail["email"]
    assert draft["situation"] in {
        "prolong_wait", "blocked", "suspended", "funds_gap",
        "expiry_auto_off", "unknown", "on_track",
    }


def test_low_risk_email_is_calm_not_alarming(client):
    login(client)
    calm = [client.get(f"/api/v1/customers/{i}").json() for i in range(1, 11)]
    calm = [c for c in calm if c["level"] == "low" and c["emailDraft"]["situation"] == "on_track"]
    for detail in calm:
        assert "не хватает" not in detail["emailDraft"]["body"]
