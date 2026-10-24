import copy
import csv
import io
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
    assert len(data["forecast"]) == 31
    assert "Исторических удалений нет" in data["note"]

    as_of = _dt(data["asOf"]).date()
    assert all(date.fromisoformat(point["date"]) <= as_of for point in data["fact"])
    assert all(date.fromisoformat(point["date"]) >= as_of for point in data["forecast"])
    assert data["fact"][-1]["date"] == "2026-10-23"
    assert data["fact"][-1]["end"] == "2026-10-23"
    assert data["forecast"][0]["date"] == "2026-10-23"

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
    assert len(first["fact"]) == 7 and len(first["forecast"]) == 15


@pytest.mark.parametrize("params", [{"pastDays": 0}, {"horizonDays": 0}, {"pastDays": 91}, {"horizonDays": 91}])
def test_forecast_rejects_bad_windows(client, params):
    login(client)
    assert client.get("/api/v1/analytics/forecast", params=params).status_code == 422


def test_forecast_day_returns_services(client):
    login(client)
    overview = client.get("/api/v1/analytics/forecast").json()
    fact_day = next(point for point in overview["fact"] if point["services"])
    day = client.get(
        "/api/v1/analytics/forecast/day", params={"date": fact_day["date"], "kind": "fact"}
    ).json()
    assert day["kind"] == "fact"
    assert day["services"] == fact_day["services"]
    assert len(day["items"]) == min(day["services"], 200)
    item = day["items"][0]
    assert item["serviceName"] and item["email"]
    assert item["price"] >= 0
    assert "expectedLoss" not in item or item["expectedLoss"] is None


def test_forecast_day_forecast_has_probability_and_money(client):
    login(client)
    overview = client.get("/api/v1/analytics/forecast").json()
    point = next(point for point in overview["forecast"] if point["services"])
    day = client.get(
        "/api/v1/analytics/forecast/day", params={"date": point["date"], "kind": "forecast"}
    ).json()
    assert day["services"] == point["services"]
    assert day["expectedNonRenewals"] == pytest.approx(point["expectedNonRenewals"], abs=0.01)
    assert day["expectedLoss"] == pytest.approx(point["expectedLoss"], abs=0.02)
    first = day["items"][0]
    assert 0 < first["probability"] <= 1
    assert first["expectedLoss"] is not None


def test_forecast_day_validates_date_and_kind(client):
    login(client)
    assert client.get("/api/v1/analytics/forecast/day", params={"date": "not-a-date"}).status_code == 422
    assert client.get("/api/v1/analytics/forecast/day", params={"date": "2026-10-25", "kind": "fact"}).status_code == 422
    assert client.get("/api/v1/analytics/forecast/day", params={"date": "2026-10-20", "kind": "forecast"}).status_code == 422
    assert client.get("/api/v1/analytics/forecast/day", params={"date": "2026-10-25", "kind": "other"}).status_code == 422


def test_forecast_weekly_buckets(client):
    login(client)
    data = client.get("/api/v1/analytics/forecast", params={"bucketDays": 7}).json()
    assert len(data["fact"]) == 5
    assert len(data["forecast"]) == 5
    for point in data["fact"] + data["forecast"]:
        assert point["date"] <= point["end"]
    assert data["fact"][-1]["end"] == "2026-10-23"
    daily = client.get("/api/v1/analytics/forecast").json()
    assert data["totals"]["factServices"] == daily["totals"]["factServices"]
    assert data["totals"]["expectedLoss"] == pytest.approx(daily["totals"]["expectedLoss"], abs=0.02)


def test_forecast_bucket_day_range(client):
    login(client)
    weekly = client.get("/api/v1/analytics/forecast", params={"bucketDays": 7}).json()
    bucket = next(point for point in weekly["forecast"] if point["services"])
    response = client.get(
        "/api/v1/analytics/forecast/day",
        params={"date": bucket["date"], "end": bucket["end"], "kind": "forecast"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["date"] == bucket["date"] and data["end"] == bucket["end"]
    assert data["services"] == bucket["services"]
    assert data["expectedLoss"] == pytest.approx(bucket["expectedLoss"], abs=0.02)
    assert client.get(
        "/api/v1/analytics/forecast/day",
        params={"date": bucket["end"], "end": bucket["date"]},
    ).status_code == 422


def test_forecast_export_requires_auth(client):
    assert client.get("/api/v1/analytics/forecast/export.csv").status_code == 401


def test_forecast_export_matches_totals(client):
    login(client)
    overview = client.get("/api/v1/analytics/forecast", params={"bucketDays": 7}).json()
    response = client.get("/api/v1/analytics/forecast/export.csv", params={"kind": "forecast"})
    assert response.status_code == 200
    assert response.content.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" in response.content
    rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert len(rows) == overview["totals"]["forecastServices"]
    assert {row["kind"] for row in rows} == {"forecast"}
    total = sum(float(row["expected_loss_eur"] or 0) for row in rows)
    assert total == pytest.approx(overview["totals"]["expectedLoss"], abs=0.05)
    assert rows[0]["week_start"] and rows[0]["week_end"] and rows[0]["service_name"]


def test_forecast_export_all_contains_both_kinds(client):
    login(client)
    response = client.get("/api/v1/analytics/forecast/export.csv", params={"kind": "all"})
    rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert {"fact", "forecast"} <= {row["kind"] for row in rows}


def test_forecast_export_sanitizes_formulas(client, full_snapshot):
    login(client)
    snapshot = copy.deepcopy(full_snapshot)
    for account in snapshot["accounts"]:
        if account["id"] == 6:
            account["email"] = "=SUM(1,2)@example.test"
    assert client.put("/api/v1/source/snapshot", json=snapshot).status_code == 200
    text = client.get(
        "/api/v1/analytics/forecast/export.csv", params={"kind": "forecast"}
    ).content.decode("utf-8-sig")
    assert "text:=SUM(1,2)@example.test" in text


def test_forecast_export_empty_is_409(client, full_snapshot):
    login(client)
    snapshot = copy.deepcopy(full_snapshot)
    for service in snapshot["services"]:
        service["status"] = "deleted"
    assert client.put("/api/v1/source/snapshot", json=snapshot).status_code == 200
    assert client.get("/api/v1/analytics/forecast/export.csv").status_code == 409
