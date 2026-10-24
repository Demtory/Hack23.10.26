import copy
import json
import sqlite3
import pytest
from app import api, store
from app.db import connect, transaction
from app.seed import get_settings
from .conftest import login, database_state


def many(snapshot):
    result = {'accounts': [], 'services': [], 'transactions': []}
    for i in range(1, 13):
        a = dict(snapshot['accounts'][0], id=i, email=f'audit-{i}@example.test', balance=0, bonusBalance=0, withdrawBalance=0)
        s = dict(snapshot['services'][0], id=i, ownerId=i, name=f'audit-{i}', price=100 if i < 12 else 100000,
                 status='prolong_wait' if i < 12 else 'active', autoProlong=False,
                 createdAt='2026-01-01T00:00:00Z', expiresAt='2026-10-23T17:00:00Z' if i < 12 else '2027-10-23T18:00:00Z')
        result['accounts'].append(a); result['services'].append(s)
    return result


@pytest.mark.parametrize('q', ['', 'AUDIT-1', 'not-found'])
@pytest.mark.parametrize('level', ['', 'high', 'medium', 'low', 'unknown'])
def test_filtered_global_top(client, full_snapshot, q, level):
    login(client)
    assert client.put('/api/v1/source/snapshot', json=many(full_snapshot)).status_code == 200
    params = {'pageSize': 100, 'q': q}
    if level: params['level'] = level
    full = client.get('/api/v1/customers', params=params).json()
    all_items=client.get('/api/v1/customers',params={'pageSize':100}).json()['items']
    selected=[x for x in all_items if (not q or q.lower() in x['email'].lower()) and (not level or x['level']==level)]
    assert {x['id'] for x in full['items']}=={x['id'] for x in selected}
    expected = sorted(selected, key=lambda x: (-x['expectedLoss'], x['id']))[:5]
    for sort, order, page, size in [('score','desc',1,10), ('balance','asc',2,2), ('id','desc',1,3)]:
        view = client.get('/api/v1/customers', params={**params,'sort':sort,'order':order,'page':page,'pageSize':size}).json()
        assert view['topLosses'] == expected
        assert view['summary']['totalCustomers'] == 12
        assert view['calculation'] == full['calculation']
        assert view['total'] == full['total']
    if not q and not level:
        assert expected[0]['id'] == 12
        first = client.get('/api/v1/customers', params={'pageSize':10}).json()
        assert 12 not in [x['id'] for x in first['items']]


def test_effective_threshold_context(session):
    c=session.client
    assert c.patch('/api/v1/model/settings',json={'thresholds':{'medium':80,'high':90}}).status_code==200
    view=c.get('/api/v1/customers').json()
    assert view['calculation']['thresholds']=={'medium':80,'high':90}
    detail=c.get('/api/v1/customers/5').json()
    assert all(s['level']=='low' for s in detail['services'])
    assert next(x for x in view['items'] if x['id']==5)['servicesAtRisk']==0
    assert c.get('/api/v1/analytics/summary').json()['calculation']==view['calculation']
    session.restart()
    assert session.client.get('/api/v1/customers').json()['calculation']['thresholds']=={'medium':80,'high':90}


def test_exact_threshold_boundaries(client,full_snapshot):
    login(client)
    body=many(full_snapshot)
    body['accounts']=body['accounts'][:3]
    body['services']=body['services'][:2]
    for service,status in zip(body['services'],['blocked','prolong_wait']):
        service.update(status=status,expiresAt='2027-10-23T18:00:00Z')
    assert client.put('/api/v1/source/snapshot',json=body).status_code==200
    weights=dict.fromkeys(api.FEATURES_META[i]['code'] for i in range(len(api.FEATURES_META)))
    weights={k:float(k=='commitment') for k in weights}
    result=client.patch('/api/v1/model/settings',json={'weights':weights,'thresholds':{'medium':80,'high':90},'statusFloors':{'blocked':80,'prolong_wait':90}})
    assert result.status_code==200
    items=client.get('/api/v1/customers').json()['items']
    assert [(x['score'],x['level'],x['servicesAtRisk']) for x in sorted(items,key=lambda x:x['id'])]==[(80,'medium',1),(90,'high',1),(None,'unknown',0)]


def test_numeric_search_matches_id_even_when_email_has_no_digits(client, full_snapshot):
    login(client)
    snapshot = copy.deepcopy(full_snapshot)
    for account in snapshot['accounts']:
        if account['id'] == 6:
            account['email'] = 'no-digits@example.test'
    assert client.put('/api/v1/source/snapshot', json=snapshot).status_code == 200

    by_id = client.get('/api/v1/customers', params={'q': '6'}).json()
    assert [item['id'] for item in by_id['items']] == [6]
    assert by_id['total'] == 1

    by_email = client.get('/api/v1/customers', params={'q': 'no-digits'}).json()
    assert [item['id'] for item in by_email['items']] == [6]

    # ID ищется точно: подстрока не должна цеплять 16 или 60.
    assert client.get('/api/v1/customers', params={'q': '16'}).json()['total'] == 0
