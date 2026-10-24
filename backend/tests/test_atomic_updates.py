import copy
import sqlite3
import pytest
from fastapi.testclient import TestClient
from app import api, store
from app.db import connect
from app.main import create_app
from .conftest import database_state, login


@pytest.mark.parametrize('verb', ['patch', 'put'])
@pytest.mark.parametrize('stage', ['compute', 'insert', 'prune', 'response', 'commit'])
def test_failure_is_atomic(session, config, monkeypatch, verb, stage):
    client = session.client
    before = database_state(config.db_path)
    snapshot = client.get('/api/v1/source/snapshot').json()
    snapshot['accounts'][0]['balance'] += 1
    endpoint = '/api/v1/model/settings' if verb == 'patch' else '/api/v1/source/snapshot'
    payload = {'weights': {'funds_gap': .9}} if verb == 'patch' else snapshot

    class FaultConnection(sqlite3.Connection):
        def execute(self, sql, *args, **kwargs):
            result = super().execute(sql, *args, **kwargs)
            if stage == 'insert' and 'INSERT INTO customer_scores' in sql:
                raise RuntimeError('injected private failure')
            if stage == 'prune' and 'DELETE FROM score_runs WHERE' in sql:
                raise RuntimeError('injected private failure')
            return result
        def commit(self):
            if stage == 'commit':
                raise RuntimeError('injected private failure')
            return super().commit()

    def fault_db():
        conn = sqlite3.connect(config.db_path, factory=FaultConnection, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        try:
            yield conn
        finally:
            conn.close()

    def fail(*args, **kwargs):
        raise RuntimeError('injected private failure')

    with monkeypatch.context() as m:
        client.app.dependency_overrides[api.get_db] = fault_db
        if stage == 'compute':
            m.setattr(store, 'compute', fail)
        if stage == 'response':
            m.setattr(api, '_summary_api', fail)
        try:
            response = getattr(client, verb)(endpoint, json=payload)
        finally:
            client.app.dependency_overrides.clear()
    assert response.status_code == 500
    assert 'injected' not in response.text
    assert response.json()['detail']
    assert database_state(config.db_path) == before
    assert client.get('/api/v1/customers').status_code == 200
    restarted = session.restart()
    assert restarted.get('/api/v1/customers').status_code == 200
    assert getattr(restarted, verb)(endpoint, json=payload).status_code == 200


def test_midpoint_survives_restart(session):
    assert session.client.patch('/api/v1/model/settings', json={'probability': {'midpoint': 10000}}).status_code == 200
    c = session.restart()
    assert c.get('/api/v1/model/settings').json()['probability']['midpoint'] == 10000
    assert c.get('/api/v1/analytics/summary').status_code == 200


def test_empty_snapshot_survives_restart(session):
    c = session.client
    assert c.put('/api/v1/source/snapshot', json={'accounts': [], 'services': [], 'transactions': []}).status_code == 200
    assert c.get('/api/v1/analytics/summary').json()['totalCustomers'] == 0
    c = session.restart()
    assert c.get('/api/v1/source/snapshot').json() == {'accounts': [], 'services': [], 'transactions': []}


def test_other_connection_sees_only_committed_state(session, config, monkeypatch):
    before = database_state(config.db_path)
    original = store.compute
    def observe(*args, **kwargs):
        assert database_state(config.db_path) == before
        return original(*args, **kwargs)
    monkeypatch.setattr(store, 'compute', observe)
    assert session.client.patch('/api/v1/model/settings', json={'weights': {'funds_gap': .9}}).status_code == 200
    assert database_state(config.db_path) != before


@pytest.mark.parametrize('verb', ['patch', 'put'])
def test_response_serialization_rolls_back(session, config, monkeypatch, verb):
    c = session.client
    before = database_state(config.db_path)
    original = api._summary_api
    monkeypatch.setattr(api, '_summary_api', lambda s: {**original(s), 'unexpected': float('nan')})
    path = '/api/v1/model/settings' if verb == 'patch' else '/api/v1/source/snapshot'
    payload = {'weights': {'funds_gap': .8}} if verb == 'patch' else c.get('/api/v1/source/snapshot').json()
    response = getattr(c, verb)(path, json=payload)
    assert response.status_code == 500
    assert database_state(config.db_path) == before
    monkeypatch.setattr(api, '_summary_api', original)
    assert getattr(c, verb)(path, json=payload).status_code == 200
    session.restart()


@pytest.mark.parametrize('failure',[False,True])
def test_fallback_recompute_transaction(session, config, monkeypatch, failure):
    with connect(config.db_path) as conn:
        conn.execute('DELETE FROM customer_scores')
        conn.execute('DELETE FROM score_runs')
    before=database_state(config.db_path)
    original=store.compute
    def fail(*args,**kwargs):raise RuntimeError('fallback failure')
    if failure:monkeypatch.setattr(store,'compute',fail)
    response=session.client.get('/api/v1/analytics/summary')
    if failure:
        assert response.status_code==500
        assert database_state(config.db_path)==before
        monkeypatch.setattr(store,'compute',original)
        assert session.client.get('/api/v1/analytics/summary').status_code==200
    else:
        assert response.status_code==200
        assert database_state(config.db_path)['score_runs']


def test_startup_failure_rolls_back_existing_state(session, config, monkeypatch):
    before=database_state(config.db_path)
    original=store.compute
    def fail(*args,**kwargs):raise RuntimeError('startup failure')
    # Startup has its own owner and must not overwrite existing settings/data.
    with monkeypatch.context() as m:
        m.setattr(store,'compute',fail)
        with pytest.raises(RuntimeError,match='startup failure'):
            session.restart()
    assert database_state(config.db_path)==before
    assert session.restart().get('/api/v1/customers').status_code==200


def test_invalid_detail_preflight_rolls_back(session, config, monkeypatch):
    before=database_state(config.db_path)
    original=store.compute
    def invalid(*args,**kwargs):
        result=original(*args,**kwargs)
        result['customers'][0]['services'][0].pop('values')
        return result
    with monkeypatch.context() as m:
        m.setattr(store,'compute',invalid)
        response=session.client.patch('/api/v1/model/settings',json={'weights':{'funds_gap':.9}})
    assert response.status_code==500
    assert database_state(config.db_path)==before
    assert session.restart().get('/api/v1/customers').status_code==200


@pytest.mark.parametrize('verb',['patch','put'])
def test_write_lock_rejection_preserves_state(session, config, verb):
    c=session.client
    payload={'weights':{'funds_gap':.8}} if verb=='patch' else c.get('/api/v1/source/snapshot').json()
    path='/api/v1/model/settings' if verb=='patch' else '/api/v1/source/snapshot'
    before=database_state(config.db_path)
    def impatient_db():
        conn=connect(config.db_path)
        conn.execute('PRAGMA busy_timeout=0')
        try:yield conn
        finally:conn.close()
    locker=connect(config.db_path)
    locker.execute('BEGIN IMMEDIATE')
    c.app.dependency_overrides[api.get_db]=impatient_db
    try:
        response=getattr(c,verb)(path,json=payload)
        assert response.status_code==500
        assert database_state(config.db_path)==before
    finally:
        c.app.dependency_overrides.clear()
        locker.rollback();locker.close()
    assert getattr(c,verb)(path,json=payload).status_code==200
    session.restart()
