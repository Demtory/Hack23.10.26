import copy
import json
import sqlite3
import pytest
from fastapi.testclient import TestClient
from app import api, store, main
from app.db import connect, transaction
from app.main import create_app
from .conftest import database_state, login
from app.seed import get_settings
from .test_settings_upgrade import add_feature


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


@pytest.mark.parametrize('table,column,value', [('accounts', 'balance', -1), ('accounts', 'bonus_balance', 1.5), ('services', 'price', -1), ('transactions', 'amount', -1)])
def test_bad_persisted_money_refused_002(config, client, table, column, value):
    with sqlite3.connect(config.db_path) as conn:
        conn.execute(f'UPDATE {table} SET {column}=? WHERE id=(SELECT min(id) FROM {table})', (value,))
    before = database_state(config.db_path)
    with pytest.raises(ValueError, match='money'):
        with TestClient(create_app(config)):
            pass
    assert database_state(config.db_path) == before


def test_customer_read_snapshot(client, config, monkeypatch):
    login(client)
    original=client.get('/api/v1/customers').json()
    triggered=False
    class Hook(sqlite3.Connection):
        def execute(self, sql, *args, **kwargs):
            nonlocal triggered
            result=super().execute(sql,*args,**kwargs)
            if not triggered and 'count(*)' in sql.lower() and 'customer_scores' in sql.lower():
                triggered=True
                w=connect(config.db_path)
                try:
                    with transaction(w):
                        w.execute("UPDATE accounts SET email='new-' || email")
                        settings,version,_=get_settings(w)
                        store.recompute(w,settings,version,config.as_of)
                finally: w.close()
            return result
    def hooked(path):
        c=sqlite3.connect(path,factory=Hook,check_same_thread=False)
        c.row_factory=sqlite3.Row
        c.execute('PRAGMA foreign_keys=ON')
        return c
    monkeypatch.setattr(api,'connect',hooked)
    response=client.get('/api/v1/customers')
    assert response.status_code==200
    assert triggered
    assert response.json()==original
    assert all(x['email'].startswith('new-') for x in client.get('/api/v1/customers').json()['items'])


def test_missing_run_context_recomputed_atomically(client,config,monkeypatch):
    login(client)
    with sqlite3.connect(config.db_path) as c:
        row=c.execute('SELECT id,summary FROM score_runs ORDER BY id DESC LIMIT 1').fetchone()
        summary=json.loads(row[1]);summary.pop('thresholds',None);summary.pop('calculation',None)
        c.execute('UPDATE score_runs SET summary=? WHERE id=?',(json.dumps(summary),row[0]))
    before=database_state(config.db_path)
    original=api.recompute
    monkeypatch.setattr(api,'recompute',lambda *a,**k: (_ for _ in ()).throw(RuntimeError('fault')))
    assert client.get('/api/v1/customers').status_code==500
    assert database_state(config.db_path)==before
    monkeypatch.setattr(api,'recompute',original)
    assert client.get('/api/v1/customers').json()['calculation']['runId']>row[0]



@pytest.mark.parametrize('fault',['save','compute','serialize','commit'])
def test_upgrade_failure_atomic(session,config,monkeypatch,fault):
    from app import seed
    session.stack.close();before=database_state(config.db_path);add_feature(monkeypatch)
    with monkeypatch.context() as m:
        if fault=='save':
            original=seed.save_settings
            def fail_save(*args):
                original(*args)
                assert database_state(config.db_path)==before
                raise RuntimeError('fault')
            m.setattr(seed,'save_settings',fail_save)
        elif fault=='compute':
            original=main.recompute
            def fail_compute(*args):
                original(*args)
                assert database_state(config.db_path)==before
                raise RuntimeError('fault')
            m.setattr(main,'recompute',fail_compute)
        elif fault=='serialize': m.setattr(store,'detail_response',lambda *a,**k: (_ for _ in ()).throw(RuntimeError('fault')))
        else:
            class Fail(sqlite3.Connection):
                def commit(self):
                    if self.in_transaction:
                        assert database_state(config.db_path)==before
                        raise RuntimeError('fault')
                    super().commit()
            def fail_connect(path):
                c=sqlite3.connect(path,factory=Fail,check_same_thread=False);c.row_factory=sqlite3.Row
                return c
            m.setattr(main,'connect',fail_connect)
        with pytest.raises(RuntimeError,match='fault'):
            with TestClient(create_app(config)): pass
    assert database_state(config.db_path)==before
    after=session.restart().get('/api/v1/model/settings').json()
    assert after['weights']['future_signal']==0
    assert session.restart().get('/api/v1/model/settings').json()==after
