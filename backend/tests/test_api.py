from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.main import create_app

PROJECT = Path(__file__).resolve().parents[2]
SEED = PROJECT / "data" / "seed.json"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setenv("APP_DB", str(db))
    monkeypatch.setenv("SEED_PATH", str(SEED))
    monkeypatch.setenv("AS_OF", "2026-10-23T18:00:00.000Z")
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.test")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin123")
    monkeypatch.setenv("SEED_ON_START", "true")
    app = create_app(Config.from_env())
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.test", "password": "admin123"},
    )
    assert response.status_code == 200


def test_health_and_auth(client: TestClient) -> None:
    assert client.get("/healthz").status_code == 200
    assert client.get("/api/v1/customers").status_code == 401
    assert client.get("/api/v1/analytics/summary").status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "admin@example.test", "password": "bad"}).status_code == 401
    login(client)
    assert client.get("/api/v1/auth/me").json()["email"] == "admin@example.test"
    customers = client.get("/api/v1/customers").json()
    assert customers["total"] == 10
    assert len(customers["items"]) == 10


def test_sorting_and_detail(client: TestClient) -> None:
    login(client)
    asc = client.get("/api/v1/customers", params={"sort": "balance", "order": "asc"}).json()["items"]
    desc = client.get("/api/v1/customers", params={"sort": "balance", "order": "desc"}).json()["items"]
    assert asc[0]["balance"] <= asc[-1]["balance"]
    assert desc[0]["balance"] >= desc[-1]["balance"]
    assert asc[0]["id"] == desc[-1]["id"]

    by_score = client.get("/api/v1/customers", params={"sort": "score", "order": "desc"}).json()["items"]
    scores = [item["score"] for item in by_score if item["score"] is not None]
    assert scores == sorted(scores, reverse=True)

    top = client.get(f"/api/v1/customers/{by_score[0]['id']}").json()
    assert top["level"] in {"high", "medium"}
    assert top["drivers"]
    assert top["money"]["expectedLoss"] >= 0

    unknown = client.get("/api/v1/customers/3").json()
    assert unknown["score"] is None
    assert unknown["level"] == "unknown"
    assert unknown["unknownReason"] == "Все услуги удалены"

    assert client.get("/api/v1/customers/99999").status_code == 404


def test_settings_patch_and_persistence(client: TestClient, tmp_path, monkeypatch) -> None:
    login(client)
    before = client.get("/api/v1/customers/6").json()
    response = client.patch("/api/v1/model/settings", json={"weights": {"funds_gap": 0.9}})
    assert response.status_code == 200
    assert response.json()["settings"]["version"] == 2
    after = client.get("/api/v1/customers/6").json()
    assert after["score"] >= before["score"]
    assert client.get("/api/v1/model/settings").json()["version"] == 2

    # Same DB, new app instance: settings must survive a restart.
    app2 = create_app(Config.from_env())
    with TestClient(app2) as second:
        login(second)
        assert second.get("/api/v1/model/settings").json()["version"] == 2
        assert second.get("/api/v1/model/settings").json()["weights"]["funds_gap"] == 0.9

    invalid = client.patch("/api/v1/model/settings", json={"weights": {"unknown": 1.0}})
    assert invalid.status_code == 422
    invalid = client.patch("/api/v1/model/settings", json={"thresholds": {"medium": 80, "high": 70}})
    assert invalid.status_code == 422


def test_snapshot_replace_and_metrics(client: TestClient) -> None:
    login(client)
    snapshot = client.get("/api/v1/source/snapshot").json()
    assert {key: len(value) for key, value in snapshot.items()} == {
        "accounts": 10,
        "services": 30,
        "transactions": 100,
    }
    for account in snapshot["accounts"]:
        if account["id"] == 6:
            account["balance"] = 0
            account["withdrawBalance"] = 0
            account["bonusBalance"] = 0
    before = client.get("/api/v1/customers/6").json()["money"]["expectedLoss"]
    response = client.put("/api/v1/source/snapshot", json=snapshot)
    assert response.status_code == 200
    assert response.json()["counts"]["accounts"] == 10
    after = client.get("/api/v1/customers/6").json()["money"]["expectedLoss"]
    assert after >= before

    summary = client.get("/api/v1/analytics/summary").json()
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert metrics.headers["content-type"].startswith("text/plain")
    text = metrics.text
    assert f'churn_customers_total{{level="high"}} {summary["countsByLevel"]["high"]}' in text
    assert f"churn_expected_loss_eur {summary['expectedLoss']:.2f}" in text
    assert f"churn_amount_at_risk_eur {summary['amountAtRisk']:.2f}" in text


def test_openapi_and_docs(client: TestClient) -> None:
    schema = client.get("/api/v1/openapi.json")
    assert schema.status_code == 200
    paths = schema.json()["paths"]
    assert "/api/v1/customers" in paths
    assert "/api/v1/source/snapshot" in paths
    assert client.get("/api/v1/docs").status_code == 200
