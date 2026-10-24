import copy
from datetime import timedelta
import pytest
from app.scoring import default_settings
from .test_scoring import model_result, NOW
from .conftest import login


def only_commitment():
    settings = default_settings()
    settings['weights'] = dict.fromkeys(settings['weights'], 0.)
    settings['weights']['commitment'] = 1.
    return settings


def one_service(full_snapshot, total=30000, expires=2, status='prolong_wait'):
    snapshot = {'accounts': [dict(full_snapshot['accounts'][0], id=1, email='rules@example.test', totalReplenished=total)],
                'services': [dict(full_snapshot['services'][0], id=1, ownerId=1, price=10000, status=status,
                  createdAt=(NOW-timedelta(days=30)).isoformat(), expiresAt=(NOW+timedelta(days=expires)).isoformat())],
                'transactions': []}
    return snapshot


def test_audit_high78(full_snapshot):
    customer = next(c for c in model_result(full_snapshot, only_commitment())['customers'] if c['id'] == 5)
    assert customer['score'] == 78 and customer['level'] == 'high'
    assert customer['drivers'] == []
    assert 'Риск ниже порога' not in customer['summaryText']
    assert customer['explanationRules'][0]['delta'] == 8
    assert len(customer['explanationRules'][0]['relatedServiceIds']) == 3
    for service in customer['services']:
        assert service['explanationRules'][0]['afterScore'] == 70


@pytest.mark.parametrize('total,expected', [(30000, (0.,70.,70.)), (9012,(70.,70.,0.)), (3000,None)])
def test_floor_and_rounding(full_snapshot, total, expected):
    c = model_result(one_service(full_snapshot, total), only_commitment())['customers'][0]
    rules = c['services'][0]['explanationRules']
    if expected is None:
        assert rules == []
    else:
        rule = rules[0]
        assert (rule['beforeScore'],rule['afterScore'],rule['delta']) == expected
        assert rule['delta'] == pytest.approx(round(rule['afterScore']-rule['beforeScore'],1), abs=1e-9)
        if expected[2] == 0:
            assert 'после округления' in rule['label']
            assert '+0' not in rule['label']


def test_sequential_status_and_stale(full_snapshot):
    s = only_commitment()
    s['statusFloors']['prolong_wait'] = 60
    c = model_result(one_service(full_snapshot, expires=-6), s)['customers'][0]
    rules = c['services'][0]['explanationRules']
    assert [r['code'] for r in rules] == ['status_floor','stale_status_floor']
    assert [(r['beforeScore'],r['afterScore']) for r in rules] == [(0,60),(60,70)]


def test_cap_has_actual_effect(full_snapshot):
    snap = one_service(full_snapshot, total=900)
    for sid in [2,3]:
        snap['services'].append(dict(snap['services'][0], id=sid))
    # total=900, total service price=30000 => commitment=.99 =>99.
    c = model_result(snap, only_commitment())['customers'][0]
    assert c['score'] == 100
    assert [(r['code'],r['beforeScore'],r['afterScore'],r['delta']) for r in c['explanationRules']] == [
        ('customer_bonus',99,107,8),('score_cap',107,100,-7)]


@pytest.mark.parametrize('medium,high,level', [(40,70,'high'),(40,90,'medium'),(80,90,'low')])
def test_summary_uses_actual_thresholds(full_snapshot, medium, high, level):
    s=only_commitment();s['thresholds'].update(medium=medium,high=high)
    c=model_result(one_service(full_snapshot),s)['customers'][0]
    assert c['level'] == level
    if level != 'low':
        assert 'Риск ниже порога' not in c['summaryText']


def test_detail_contract_and_old_cache(client, config):
    import sqlite3,json
    login(client)
    c=client.get('/api/v1/customers/5').json()
    assert set(c) == {'id','email','balance','withdrawBalance','bonusBalance','bonusState','totalReplenished',
        'score','level','confidence','summary','drivers','services','money','unknownReason','isEstimated','explanationRules'}
    service=c['services'][0]
    assert {'values','drivers','price','createdAt','expiresAt','staleStatus','explanationRules'} <= set(service)
    assert not any(r['scope']=='service' for r in c['explanationRules'])
    with sqlite3.connect(config.db_path) as conn:
        row=conn.execute('SELECT run_id, detail FROM customer_scores WHERE account_id=5 ORDER BY run_id DESC LIMIT 1').fetchone()
        detail=json.loads(row[1]);detail.pop('explanationRules',None)
        for svc in detail['services']:svc.pop('explanationRules',None)
        conn.execute('UPDATE customer_scores SET detail=? WHERE run_id=? AND account_id=5',(json.dumps(detail),row[0]))
    old=client.get('/api/v1/customers/5').json()
    assert old['explanationRules']==[]
    assert all(s['explanationRules']==[] for s in old['services'])
    for key in c.keys()-{'explanationRules','services'}:assert c[key]==old[key]
