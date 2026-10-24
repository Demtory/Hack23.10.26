import copy
import json
import sqlite3
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import create_app
from .conftest import database_state, login

FIELDS = {
 'accounts': ['id','email','balance','withdrawBalance','totalReplenished','bonusBalance','bonusState'],
 'services': ['id','name','ownerId','paymentTerm','autoProlong','createdAt','expiresAt','status','price'],
 'transactions': ['id','amount','status','createdAt','type','serviceId','performedAt']}
CASES = [(kind,field) for kind,fields in FIELDS.items() for field in fields] + [('root',f) for f in FIELDS]


@pytest.mark.parametrize('kind,field',CASES)
@pytest.mark.parametrize('mode',['omit','null'])
def test_every_required_value(session, config, full_snapshot, kind, field, mode):
    c=session.client
    before=database_state(config.db_path)
    body=copy.deepcopy(full_snapshot)
    record=body if kind=='root' else body[kind][0]
    if kind=='transactions' and field=='performedAt':
        record['status']='performed';record['performedAt']=record['createdAt']
    if mode=='omit':record.pop(field,None)
    else:record[field]=None
    response=c.put('/api/v1/source/snapshot',json=body)
    assert response.status_code==422
    assert field in response.text
    assert database_state(config.db_path)==before
    assert c.get('/api/v1/customers').status_code==200
    assert c.put('/api/v1/source/snapshot',json=full_snapshot).status_code==200
    assert session.restart().get('/api/v1/customers').status_code==200


def test_audit_incomplete_snapshot(client, config, full_snapshot):
    login(client)
    before=database_state(config.db_path)
    full_snapshot['accounts'][0]={'id':full_snapshot['accounts'][0]['id'],'email':'incomplete@example.test'}
    full_snapshot['services'][0].pop('autoProlong')
    response=client.put('/api/v1/source/snapshot',json=full_snapshot)
    assert response.status_code==422
    assert 'balance' in response.text and 'autoProlong' in response.text
    assert database_state(config.db_path)==before


def test_explicit_zero_false_and_optional_performed_at(client, full_snapshot):
    login(client)
    for a in full_snapshot['accounts']:
        for field in ['balance','withdrawBalance','bonusBalance','totalReplenished']:a[field]=0
    for s in full_snapshot['services']:s['autoProlong']=False
    for tx in full_snapshot['transactions']:
        if tx['status']=='not_performed':tx.pop('performedAt',None)
    assert client.put('/api/v1/source/snapshot',json=full_snapshot).status_code==200
    after=client.get('/api/v1/source/snapshot').json()
    assert all(a['balance']==0 for a in after['accounts'])
    assert all(s['autoProlong'] is False for s in after['services'])
    for tx in full_snapshot['transactions']:
        if tx['status']=='not_performed':tx['performedAt']=None
    assert client.put('/api/v1/source/snapshot',json=full_snapshot).status_code==200


def test_no_history_is_not_automatically_unknown(client, full_snapshot):
    login(client)
    full_snapshot['transactions']=[]
    assert client.put('/api/v1/source/snapshot',json=full_snapshot).status_code==200
    c=client.get('/api/v1/customers/5').json()
    assert c['score'] is not None
    assert all(s['values']['payment_history'] is None for s in c['services'])
    weights=dict.fromkeys(client.get('/api/v1/model/settings').json()['weights'],0)
    weights['payment_history']=1
    assert client.patch('/api/v1/model/settings',json={'weights':weights}).status_code==200
    c=client.get('/api/v1/customers/5').json()
    assert c['score'] is None and c['unknownReason']=='Недостаточно данных для оценки'


@pytest.mark.parametrize('state,reason',[('no_services','Нет услуг'),('deleted','Все услуги удалены')])
def test_unknown_states(client, full_snapshot, state, reason):
    login(client)
    if state=='no_services':full_snapshot['services']=[];full_snapshot['transactions']=[]
    else:
        for s in full_snapshot['services']:s['status']='deleted'
    assert client.put('/api/v1/source/snapshot',json=full_snapshot).status_code==200
    c=client.get('/api/v1/customers/1').json()
    assert c['score'] is None and c['level']=='unknown' and c['unknownReason']==reason
    assert c['summary']==reason


@pytest.mark.parametrize('complete',[False,True])
def test_initial_seed_validation_is_atomic(config, tmp_path, full_snapshot, complete):
    seed=tmp_path/'seed.json'
    if not complete:full_snapshot['accounts'][0].pop('balance')
    seed.write_text(json.dumps(full_snapshot))
    cfg=replace(config,db_path=tmp_path/'fresh.db',seed_path=seed)
    if complete:
        with TestClient(create_app(cfg)) as c:
            login(c);assert c.get('/api/v1/customers').json()['total']==10
    else:
        with pytest.raises(ValidationError):
            with TestClient(create_app(cfg)):pass
        with sqlite3.connect(cfg.db_path) as conn:
            for table in ['accounts','services','transactions','settings','score_runs','customer_scores']:
                assert conn.execute(f'SELECT count(*) FROM {table}').fetchone()[0]==0


@pytest.mark.parametrize('kind,field',[('accounts','id'),('accounts','balance'),('services','ownerId'),('services','price'),('transactions','serviceId')])
def test_integer_storage_limit(client, config, full_snapshot, kind, field):
    login(client)
    before=database_state(config.db_path)
    full_snapshot[kind][0][field]=2**63
    assert client.put('/api/v1/source/snapshot',json=full_snapshot).status_code==422
    assert database_state(config.db_path)==before


def test_unrepresentable_customer_aggregate_rolls_back(session, config, full_snapshot):
    c=session.client
    before=database_state(config.db_path)
    a=full_snapshot['accounts'][0]
    s=full_snapshot['services'][0]
    body={'accounts':[a], 'services':[dict(s,id=i,ownerId=a['id'],price=2**63-1,status='prolong_wait') for i in [1,2,3]],'transactions':[]}
    response=c.put('/api/v1/source/snapshot',json=body)
    assert response.status_code==500
    assert database_state(config.db_path)==before
    assert c.put('/api/v1/source/snapshot',json=full_snapshot).status_code==200
    session.restart()


@pytest.mark.parametrize('name',['seed.json','raw/data.json'])
def test_complete_repository_datasets(client, name):
    from .conftest import ROOT
    login(client)
    body=json.loads((ROOT/'data'/name).read_text())
    response=client.put('/api/v1/source/snapshot',json=body)
    assert response.status_code==200
    assert response.json()['counts']=={'accounts':10,'services':30,'transactions':100}


def test_maximum_sqlite_balance_is_accepted(client, full_snapshot):
    login(client)
    full_snapshot['accounts'][0]['balance']=2**63-1
    assert client.put('/api/v1/source/snapshot',json=full_snapshot).status_code==200
    assert client.get('/api/v1/source/snapshot').json()['accounts'][0]['balance']==2**63-1


# 002: strict source money and full-state preservation.
MONEY_FIELDS_002 = [('accounts', k) for k in ('balance', 'withdrawBalance', 'totalReplenished', 'bonusBalance')] + [('services', 'price'), ('transactions', 'amount')]

@pytest.mark.parametrize('entity,field', MONEY_FIELDS_002)
@pytest.mark.parametrize('literal', ['-1', 'true', 'false', '"100"', '100.0', '1e2', '100.5', 'null', '9223372036854775808'])
def test_money_literal_contract_002(session, config, full_snapshot, entity, field, literal):
    from .conftest import database_state
    import json
    snapshot = full_snapshot
    snapshot[entity][0][field] = '__money_literal__'
    raw = json.dumps(snapshot).replace('"__money_literal__"', literal)
    before = database_state(config.db_path)
    response = session.client.put('/api/v1/source/snapshot', content=raw, headers={'Content-Type': 'application/json'})
    assert response.status_code == 422
    assert any(field in e['loc'] for e in response.json()['detail'])
    assert all('input' not in e and 'ctx' not in e for e in response.json()['detail'])
    assert database_state(config.db_path) == before
    session.restart()
    snapshot[entity][0][field] = 100
    assert session.client.put('/api/v1/source/snapshot', json=snapshot).status_code == 200


@pytest.mark.parametrize('entity,field', MONEY_FIELDS_002)
@pytest.mark.parametrize('value', [0, 100])
def test_money_zero_and_integer_002(client, full_snapshot, entity, field, value):
    from .conftest import login
    login(client)
    full_snapshot[entity][0][field] = value
    assert client.put('/api/v1/source/snapshot', json=full_snapshot).status_code == 200
    assert client.get('/api/v1/source/snapshot').json()[entity][0][field] == value


@pytest.mark.parametrize('entity,field', MONEY_FIELDS_002)
def test_money_input_upper_bound_002(full_snapshot, entity, field):
    from app.schemas import SnapshotIn
    full_snapshot[entity][0][field] = 2**63 - 1
    SnapshotIn.model_validate(full_snapshot)


@pytest.mark.parametrize('amount', [1000, 1001, 5000, 9007199254740993, 2**63 - 1])
def test_money_large_amount_roundtrip_002(session, full_snapshot, amount):
    full_snapshot['transactions'][0]['amount'] = amount
    assert session.client.put('/api/v1/source/snapshot', json=full_snapshot).status_code == 200
    session.restart()
    assert session.client.get('/api/v1/source/snapshot').json()['transactions'][0]['amount'] == amount
