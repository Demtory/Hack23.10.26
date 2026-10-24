import copy

import pytest

from .conftest import login


def preset_weights(code="money"):
    return {
        "expiry_pressure": 0.30, "funds_gap": 0.45, "autorenew_off": 0.08,
        "status_pressure": 0.07, "payment_history": 0.08, "commitment": 0.02,
        "auto_off_share": 0.00,
    }


def test_presets_require_auth(client):
    assert client.get("/api/v1/model/presets").status_code == 401
    assert client.post("/api/v1/model/presets", json={"name": "x", "weights": {}}).status_code == 401
    assert client.delete("/api/v1/model/presets/custom-1").status_code == 401


def test_builtin_presets_listed(client):
    login(client)
    body = client.get("/api/v1/model/presets").json()
    presets = body["presets"]
    assert [preset["id"] for preset in presets] == ["balanced", "money", "urgency", "status"]
    assert all(preset["builtin"] for preset in presets)
    codes = set(preset_weights())
    assert all(set(preset["weights"]) == codes for preset in presets)
    assert next(p for p in presets if p["id"] == "money")["weights"]["funds_gap"] == 0.45


def test_custom_preset_roundtrip(client):
    login(client)
    created = client.post("/api/v1/model/presets", json={"name": "Мой набор", "weights": preset_weights()})
    assert created.status_code == 201, created.text
    preset = created.json()
    assert preset["builtin"] is False and preset["id"].startswith("custom-")
    assert preset["weights"]["funds_gap"] == 0.45

    listed = client.get("/api/v1/model/presets").json()["presets"]
    assert any(item["name"] == "Мой набор" for item in listed)

    assert client.delete(f"/api/v1/model/presets/{preset['id']}").status_code == 204
    assert all(item["name"] != "Мой набор" for item in client.get("/api/v1/model/presets").json()["presets"])


def test_preset_survives_restart(session):
    c = session.client
    created = c.post("/api/v1/model/presets", json={"name": "После рестарта", "weights": preset_weights()})
    assert created.status_code == 201
    restarted = session.restart()
    names = [item["name"] for item in restarted.get("/api/v1/model/presets").json()["presets"]]
    assert "После рестарта" in names


def test_preset_validation(client):
    login(client)
    cases = [
        {"name": "", "weights": preset_weights()},
        {"name": "   ", "weights": preset_weights()},
        {"name": "x" * 41, "weights": preset_weights()},
        {"name": "unknown", "weights": {"bogus": 0.5}},
        {"name": "negative", "weights": {**preset_weights(), "funds_gap": -0.1}},
        {"name": "too-big", "weights": {**preset_weights(), "funds_gap": 1.5}},
        {"name": "zeros", "weights": {code: 0 for code in preset_weights()}},
        {"name": "string", "weights": {**preset_weights(), "funds_gap": "0.4"}},
    ]
    for payload in cases:
        response = client.post("/api/v1/model/presets", json=payload)
        assert response.status_code == 422, (payload, response.text)


def test_preset_name_conflicts(client):
    login(client)
    assert client.post("/api/v1/model/presets", json={"name": "Сбалансированный", "weights": preset_weights()}).status_code == 409
    assert client.post("/api/v1/model/presets", json={"name": "Дубликат", "weights": preset_weights()}).status_code == 201
    assert client.post("/api/v1/model/presets", json={"name": "дубликат", "weights": preset_weights()}).status_code == 409


def test_delete_builtin_or_unknown_is_404(client):
    login(client)
    assert client.delete("/api/v1/model/presets/balanced").status_code == 404
    assert client.delete("/api/v1/model/presets/custom-999").status_code == 404
    assert client.delete("/api/v1/model/presets/not-a-preset").status_code == 404


def test_preset_applied_to_settings_changes_score(client):
    login(client)
    baseline = client.get("/api/v1/customers/6").json()["score"]
    applied = client.patch("/api/v1/model/settings", json={"weights": preset_weights()})
    assert applied.status_code == 200
    after = client.get("/api/v1/customers/6").json()["score"]
    assert after != baseline
    restored = client.patch("/api/v1/model/settings", json={"weights": {"funds_gap": 0.25, "expiry_pressure": 0.4}})
    assert restored.status_code == 200
