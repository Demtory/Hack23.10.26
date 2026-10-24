"""Regressions for the review of cf40840; every writer uses fixture-owned SQLite."""
import csv
import io
import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app import api as api_module
from .conftest import login, database_state


def test_today_is_split_at_instant_in_chart_drilldown_and_csv(client, full_snapshot):
    login(client)
    for service in full_snapshot['services']:
        service['status'] = 'deleted'
    service = full_snapshot['services'][0]
    service.update(status='active', expiresAt='2026-10-23T20:00:00Z')
    assert client.put('/api/v1/source/snapshot', json=full_snapshot).status_code == 200
    chart = client.get('/api/v1/analytics/forecast').json()
    assert chart['totals']['forecastServices'] == 1
    day = client.get('/api/v1/analytics/forecast/day', params={'date':'2026-10-23','runId':chart['runId']}).json()
    assert day['services'] == 1
    rows = list(csv.DictReader(io.StringIO(client.get('/api/v1/analytics/forecast/export.csv').content.decode('utf-8-sig'))))
    assert len(rows) == 1 and rows[0]['kind'] == 'forecast'


def test_blocked_is_visible_but_not_future_revenue(client, full_snapshot):
    login(client)
    for service in full_snapshot['services']:
        service['status'] = 'blocked'
    assert client.put('/api/v1/source/snapshot', json=full_snapshot).status_code == 200
    summary = client.get('/api/v1/analytics/summary').json()
    assert summary['expectedLoss'] == summary['amountAtRisk'] == 0
    assert summary['scoredCustomers'] > 0
    assert client.get('/api/v1/analytics/forecast').json()['totals']['forecastServices'] == 0


def test_demo_event_keeps_exact_integers_and_rejects_stale_run(session, config, full_snapshot):
    client = session.client
    full_snapshot['accounts'][0]['totalReplenished'] = 9007199254740993
    result = client.put('/api/v1/source/snapshot', json=full_snapshot)
    run = result.json()['summary']['calculation']['runId']
    response = client.post('/api/v1/source/events', json={'action':'autoprolong_off','expectedRunId':run})
    assert response.status_code == 200
    assert client.get('/api/v1/source/snapshot').json()['accounts'][0]['totalReplenished'] == 9007199254740993
    before = database_state(config.db_path)
    assert client.post('/api/v1/source/events', json={'action':'topup_20','expectedRunId':run}).status_code == 409
    assert database_state(config.db_path) == before
    assert session.restart().get('/api/v1/source/snapshot').json()['accounts'][0]['totalReplenished'] == 9007199254740993


def rule(**changes):
    return dict(code='custom_budget',title='Маленький баланс',field='balance',operator='lte',value=5,risk=100,**changes)


def test_custom_rule_zero_is_neutral_enabled_changes_score_and_survives_restart(session):
    client = session.client
    old = client.get('/api/v1/model/settings').json()
    before = client.get('/api/v1/customers/6').json()['score']
    added = client.patch('/api/v1/model/settings',json={'expectedVersion':old['version'],'customFactors':[rule()]})
    assert added.status_code == 200, added.text
    settings = added.json()['settings']
    assert settings['weights']['custom_budget'] == 0
    assert client.get('/api/v1/customers/6').json()['score'] == before
    enabled = client.patch('/api/v1/model/settings',json={'expectedVersion':settings['version'],'weights':{'custom_budget':1}})
    assert enabled.status_code == 200
    detail = client.get('/api/v1/customers/6').json()
    assert detail['score'] != before
    assert any('custom_budget' in service['values'] for service in detail['services'])
    restarted = session.restart()
    assert restarted.get('/api/v1/model/settings').json()['customFactors'] == [rule()]
    assert restarted.get('/api/v1/customers/6').json()['score'] == detail['score']
    current = restarted.get('/api/v1/model/settings').json()
    assert restarted.patch('/api/v1/model/settings', json={'expectedVersion':current['version'],'weights':{'custom_budget':0}}).status_code == 200
    assert restarted.get('/api/v1/customers/6').json()['score'] == before


@pytest.mark.parametrize('change',[{'field':'code'},{'title':' '},{'risk':101},{'operator':'exec'},
                                  {'field':'status','operator':'lt','value':'active'},
                                  {'field':'balance','value':'__import__("os")'}])
def test_custom_rule_invalid_is_atomic(client, config, change):
    login(client)
    current = client.get('/api/v1/model/settings').json()
    invalid = rule();invalid.update(change)
    before = database_state(config.db_path)
    assert client.patch('/api/v1/model/settings',json={'expectedVersion':current['version'],'customFactors':[invalid]}).status_code == 422
    assert database_state(config.db_path) == before


def test_custom_removal_cleans_weight_and_conflicts_preserve_state(client, config):
    login(client)
    version = client.get('/api/v1/model/settings').json()['version']
    added = client.patch('/api/v1/model/settings',json={'expectedVersion':version,'customFactors':[rule()]}).json()
    before = database_state(config.db_path)
    assert client.patch('/api/v1/model/settings',json={'expectedVersion':version,'customFactors':[]}).status_code == 409
    assert database_state(config.db_path) == before
    removed = client.patch('/api/v1/model/settings',json={'expectedVersion':added['settings']['version'],'customFactors':[]})
    assert removed.status_code == 200 and 'custom_budget' not in removed.json()['settings']['weights']


def test_forecast_csv_uses_one_generation_during_writer(client, config, monkeypatch):
    login(client)
    old = client.get('/api/v1/analytics/summary').json()['calculation']
    original = api_module.latest_run
    written = False
    def race(conn):
        nonlocal written
        result = original(conn)
        if not written:
            written = True
            with TestClient(create_app(config)) as other:
                login(other)
                assert other.patch('/api/v1/model/settings',json={'weights':{'funds_gap':.8}}).status_code == 200
        return result
    monkeypatch.setattr(api_module, 'latest_run', race)
    response = client.get('/api/v1/analytics/forecast/export.csv')
    assert response.status_code == 200
    rows = list(csv.DictReader(io.StringIO(response.content.decode('utf-8-sig'))))
    assert rows and all(int(r['run_id'])==old['runId'] and int(r['settings_version'])==old['settingsVersion'] for r in rows)


def test_forecast_export_and_drilldown_reject_changed_run(client):
    login(client)
    run = client.get('/api/v1/analytics/forecast').json()['runId']
    assert client.patch('/api/v1/model/settings',json={'weights':{'funds_gap':.8}}).status_code == 200
    assert client.get('/api/v1/analytics/forecast/export.csv',params={'runId':run}).status_code == 409
    assert client.get('/api/v1/analytics/forecast/day',params={'runId':run,'date':'2026-10-25'}).status_code == 409


def test_live_clock_refreshes_after_configured_interval(client, config, monkeypatch):
    from dataclasses import replace
    from app.db import connect
    login(client)
    conn = connect(config.db_path)
    try:
        before = api_module.latest_summary(conn)
        now = datetime.fromisoformat(before['updatedAt'].replace('Z','+00:00'))
        monkeypatch.setattr(api_module,'utcnow',lambda:now+timedelta(seconds=301))
        fixed = api_module._ensure_summary(conn,config)
        assert fixed['calculation']['runId'] == before['calculation']['runId']
        refreshed = api_module._ensure_summary(conn,replace(config,as_of=None))
        assert refreshed['calculation']['runId'] > before['calculation']['runId']
    finally:
        conn.close()


def test_duplicate_rules_are_validation_failure(client, config):
    login(client)
    version=client.get('/api/v1/model/settings').json()['version']
    before=database_state(config.db_path)
    assert client.patch('/api/v1/model/settings',json={'expectedVersion':version,'customFactors':[rule(),rule()]}).status_code==422
    assert database_state(config.db_path)==before

@pytest.mark.parametrize('expires,expected',[('2026-10-23T18:00:00.000Z','fact'),
    ('2026-10-23T18:00:00.001Z','forecast'),('2026-10-23T23:59:59.999+03:00','forecast'),
    ('2026-11-22T18:00:00.000Z','forecast'),('2026-11-22T18:00:00.001Z',None)])
def test_forecast_timestamp_boundaries_match_all_views(client, full_snapshot, expires, expected):
    login(client)
    for service in full_snapshot['services']:
        service['status']='deleted'
    service=full_snapshot['services'][0]
    service.update(status='active',expiresAt=expires)
    assert client.put('/api/v1/source/snapshot',json=full_snapshot).status_code==200
    chart=client.get('/api/v1/analytics/forecast').json()
    assert chart['totals']['forecastServices']==int(expected=='forecast')
    assert chart['totals']['factServices']==int(expected=='fact')
    csv_response=client.get('/api/v1/analytics/forecast/export.csv')
    if expected is None:
        assert csv_response.status_code==409
    else:
        rows=list(csv.DictReader(io.StringIO(csv_response.content.decode('utf-8-sig'))))
        assert len(rows)==1 and rows[0]['kind']==expected
    if expires.startswith('2026-11-22'):
        day=client.get('/api/v1/analytics/forecast/day',params={'date':'2026-11-22','kind':'forecast'}).json()
        assert day['services']==int(expected=='forecast')


def test_failed_custom_factor_recompute_preserves_state_and_restart(session, config, monkeypatch):
    client=session.client
    version=client.get('/api/v1/model/settings').json()['version']
    before=database_state(config.db_path)
    with monkeypatch.context() as patch:
        def fail(*args, **kwargs):
            raise RuntimeError('Injected calculation failure')
        patch.setattr(api_module,'recompute',fail)
        assert client.patch('/api/v1/model/settings',json={'expectedVersion':version,'customFactors':[rule()]}).status_code==500
    assert database_state(config.db_path)==before
    assert session.restart().get('/api/v1/model/settings').json()['version']==version


def test_referral_balance_cannot_make_autopay_ready(full_snapshot):
    from .test_scoring import model_result
    for service in full_snapshot['services']:
        service.update(status='active',autoProlong=True,price=1000,expiresAt='2026-10-25T18:00:00Z')
    for account in full_snapshot['accounts']:
        account.update(balance=0,bonusBalance=0,withdrawBalance=10000)
    with_referral=model_result(full_snapshot)
    for c in with_referral['customers']:
        for s in c['services']:
            assert s['values']['expiry_pressure']==1


def test_risk_counts_consistent_even_for_blocked_services(client):
    login(client)
    summary=client.get('/api/v1/analytics/summary').json()
    rows=client.get('/api/v1/customers',params={'pageSize':100}).json()['items']
    assert sum(c['servicesAtRisk'] for c in rows)==summary['servicesAtRisk']


def test_blocked_only_customer_balance_does_not_cover_other_clients(client, full_snapshot):
    login(client)
    for a in full_snapshot['accounts']:
        a.update(balance=100000,withdrawBalance=0,bonusBalance=0)
    owner=full_snapshot['services'][0]['ownerId']
    for a in full_snapshot['accounts']:
        if a['id']==owner:a['balance']=0
    for s in full_snapshot['services']:
        s.update(status='blocked',price=1000)
    full_snapshot['services'][0]['status']='active'
    assert client.put('/api/v1/source/snapshot',json=full_snapshot).status_code==200
    summary=client.get('/api/v1/analytics/summary').json()
    assert summary['aggregateCoverage']==0
    assert summary['underfundedCustomers']==1
