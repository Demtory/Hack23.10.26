import copy
from datetime import date, datetime

import pytest

from .conftest import login


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_forecast_requires_auth(client):
    assert client.get("/api/v1/analytics/forecast").status_code == 401


def test_forecast_shape_and_honesty(client):
    login(client)
    data = client.get("/api/v1/analytics/forecast").json()
    assert data["pastDays"] == 30 and data["horizonDays"] == 30
    assert len(data["fact"]) == 30
    assert len(data["forecast"]) == 30
    assert "Исторических удалений нет" in data["note"]

    as_of = _dt(data["asOf"]).date()
    assert all(date.fromisoformat(point["date"]) <= as_of for point in data["fact"])
    assert all(date.fromisoformat(point["date"]) > as_of for point in data["forecast"])
    assert data["fact"][-1]["date"] == "2026-10-23"
    assert data["forecast"][0]["date"] == "2026-10-24"

    totals = data["totals"]
    assert totals["factServices"] == sum(point["services"] for point in data["fact"])
    assert totals["forecastServices"] == sum(point["services"] for point in data["forecast"])
    assert totals["expectedNonRenewals"] == pytest.approx(
        sum(point["expectedNonRenewals"] for point in data["forecast"]), abs=0.01
    )
    assert totals["expectedLoss"] == pytest.approx(
        sum(point["expectedLoss"] for point in data["forecast"]), abs=0.02
    )
    assert 0 <= totals["servicesAtRisk"] <= totals["forecastServices"]


def test_forecast_counts_new_expiry(client, full_snapshot):
    login(client)
    snapshot = copy.deepcopy(full_snapshot)
    mine = [service for service in snapshot["services"] if service["ownerId"] == 1]
    for service in mine:
        service["status"] = "active"
        service["expiresAt"] = "2027-01-01T00:00:00.000Z"
    mine[0]["expiresAt"] = "2026-10-25T18:00:00.000Z"
    mine[0]["price"] = 1000
    for account in snapshot["accounts"]:
        if account["id"] == 1:
            account["balance"] = 0
            account["withdrawBalance"] = 0
            account["bonusBalance"] = 0
    assert client.put("/api/v1/source/snapshot", json=snapshot).status_code == 200

    data = client.get("/api/v1/analytics/forecast").json()
    point = next(item for item in data["forecast"] if item["date"] == "2026-10-25")
    assert point["services"] >= 1
    assert 0 < point["expectedNonRenewals"] <= point["services"]
    assert point["expectedLoss"] > 0
    assert data["totals"]["expectedLoss"] >= point["expectedLoss"]


def test_forecast_turns_zero_after_all_deleted(client, full_snapshot):
    login(client)
    snapshot = copy.deepcopy(full_snapshot)
    for service in snapshot["services"]:
        service["status"] = "deleted"
    assert client.put("/api/v1/source/snapshot", json=snapshot).status_code == 200
    data = client.get("/api/v1/analytics/forecast").json()
    assert data["totals"]["forecastServices"] == 0
    assert data["totals"]["expectedLoss"] == 0
    assert all(point["services"] == 0 for point in data["forecast"])


def test_forecast_is_deterministic(client):
    login(client)
    first = client.get("/api/v1/analytics/forecast", params={"pastDays": 7, "horizonDays": 14}).json()
    second = client.get("/api/v1/analytics/forecast", params={"pastDays": 7, "horizonDays": 14}).json()
    assert first == second
    assert len(first["fact"]) == 7 and len(first["forecast"]) == 14


@pytest.mark.parametrize("params", [{"pastDays": 0}, {"horizonDays": 0}, {"pastDays": 91}, {"horizonDays": 91}])
def test_forecast_rejects_bad_windows(client, params):
    login(client)
    assert client.get("/api/v1/analytics/forecast", params=params).status_code == 422
