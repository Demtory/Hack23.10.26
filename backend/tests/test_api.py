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


@pytest.mark.parametrize('raw', ['NaN', 'Infinity', '-Infinity', '1e309', '"NaN"', '"Infinity"', '"bad"'])
def test_nonfinite_midpoint(client, config, raw):
    from .conftest import database_state
    login(client)
    before = database_state(config.db_path)
    response = client.patch('/api/v1/model/settings', content='{"probability":{"midpoint":'+raw+'}}', headers={'content-type': 'application/json'})
    assert response.status_code == 422
    assert response.json()['detail']
    assert database_state(config.db_path) == before


@pytest.mark.parametrize('payload', [
    {'weights': {'funds_gap': -1}}, {'weights': dict.fromkeys(['expiry_pressure','funds_gap','autorenew_off','status_pressure','payment_history','commitment'], 0)},
    {'probability': {'steepness': 0}}, {'thresholds': {'medium': 80}}, {'probability': {'floor': .99}},
    {'money': {'balanceMitigation': 1.1}}, {'statusFloors': {'stale': -1}}, {'weights': {'funds_gap': None}},
])
def test_invalid_merged_settings(client, config, payload):
    from .conftest import database_state
    login(client)
    before = database_state(config.db_path)
    assert client.patch('/api/v1/model/settings', json=payload).status_code == 422
    assert database_state(config.db_path) == before


def test_patch_null_is_no_change(client):
    login(client)
    before = client.get('/api/v1/model/settings').json()
    payload = {'weights': None, 'probability': {'midpoint': None}, 'money': {'balanceMitigation': None}}
    assert client.patch('/api/v1/model/settings', json=payload).status_code == 200
    after = client.get('/api/v1/model/settings').json()
    for key in ('weights', 'probability', 'money'):
        assert before[key] == after[key]


NUMERIC_PATHS = [
 ('weights',key) for key in ['expiry_pressure','funds_gap','autorenew_off','status_pressure','payment_history','commitment']
] + [('thresholds',key) for key in ['medium','high']] + [
 ('probability',key) for key in ['midpoint','steepness','floor','ceiling']
] + [('money','balanceMitigation')] + [('statusFloors',key) for key in ['prolong_wait','blocked','stale']]


@pytest.mark.parametrize('group,key',NUMERIC_PATHS)
@pytest.mark.parametrize('raw',['NaN','Infinity','-Infinity','1e309','"bad"'])
def test_all_numeric_parameters_reject_invalid(client, config, group, key, raw):
    from .conftest import database_state
    login(client)
    before=database_state(config.db_path)
    body='{"'+group+'":{"'+key+'":'+raw+'}}'
    response=client.patch('/api/v1/model/settings',content=body,headers={'content-type':'application/json'})
    assert response.status_code==422
    assert key in response.text
    assert database_state(config.db_path)==before


@pytest.mark.parametrize('payload',[
 {'weights':{'funds_gap':0}}, {'thresholds':{'medium':.001,'high':99.999}},
 {'probability':{'floor':0,'ceiling':1}}, {'money':{'balanceMitigation':0}}, {'money':{'balanceMitigation':1}},
 {'statusFloors':{'stale':0,'blocked':100}}, {'recomputeIntervalSec':10}, {'recomputeIntervalSec':3600},
])
def test_valid_numeric_boundaries(client, payload):
    login(client)
    assert client.patch('/api/v1/model/settings',json=payload).status_code==200


@pytest.mark.parametrize('payload',[
 {'thresholds':{'medium':0}}, {'thresholds':{'high':100}}, {'probability':{'floor':-0.01}},
 {'probability':{'ceiling':1.01}}, {'money':{'balanceMitigation':-.01}}, {'statusFloors':{'stale':100.01}},
 {'recomputeIntervalSec':9}, {'recomputeIntervalSec':3601}, {'recomputeIntervalSec':'bad'}
])
def test_invalid_numeric_boundaries(client, config, payload):
    from .conftest import database_state
    login(client);before=database_state(config.db_path)
    assert client.patch('/api/v1/model/settings',json=payload).status_code==422
    assert database_state(config.db_path)==before


@pytest.mark.parametrize('sort',['id','email','balance','totalReplenished'])
@pytest.mark.parametrize('order',['asc','desc'])
def test_all_required_sorts_paginated(client, sort, order):
    login(client)
    items=[]
    for page in range(1,5):
        response=client.get('/api/v1/customers',params={'sort':sort,'order':order,'pageSize':3,'page':page})
        assert response.status_code==200
        items.extend(response.json()['items'])
    values=[item[sort] for item in items]
    assert len(items)==10 and len({x['id'] for x in items})==10
    assert values==sorted(values,reverse=order=='desc')


def test_logout_and_consistent_totals(client):
    login(client)
    items=client.get('/api/v1/customers').json()['items']
    summary=client.get('/api/v1/analytics/summary').json()
    assert sum(summary['countsByLevel'].values())==len(items)
    for level,count in summary['countsByLevel'].items():assert sum(x['level']==level for x in items)==count
    for key in ['expectedLoss','amountAtRisk']:
        assert sum(x[key] for x in items)==pytest.approx(summary[key],abs=.001)
        details=[client.get(f"/api/v1/customers/{x['id']}").json() for x in items]
        assert sum(x['money'][key] for x in details)==pytest.approx(summary[key],abs=.001)
    assert client.post('/api/v1/auth/logout').status_code==200
    assert client.get('/api/v1/customers').status_code==401


def test_openapi_preserves_contract(client):
    schema=client.get('/api/v1/openapi.json').json()
    models=schema['components']['schemas']
    assert set(models['SnapshotIn']['required'])=={'accounts','services','transactions'}
    for model in ['AccountIn','ServiceIn']:
        assert set(models[model]['properties'])==set(models[model]['required'])
    assert 'explanationRules' in models['CustomerDetailOut']['required']
    assert 'explanationRules' in models['ServiceOut']['required']
    assert 'anyOf' in models['ProbabilityPatch']['properties']['midpoint']


@pytest.mark.parametrize('raw',['NaN','Infinity','-Infinity','1e309'])
def test_nonfinite_integer_setting(client, config, raw):
    from .conftest import database_state
    login(client);before=database_state(config.db_path)
    response=client.patch('/api/v1/model/settings',content='{"recomputeIntervalSec":'+raw+'}',headers={'content-type':'application/json'})
    assert response.status_code==422
    assert response.json()['detail']
    assert database_state(config.db_path)==before
