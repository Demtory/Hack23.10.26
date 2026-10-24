import copy
import csv
import io
import sqlite3
import pytest
from .conftest import login, database_state
from .test_customer_views import many

@pytest.mark.parametrize('urgency,expected',[('expired',[1,2]),('48h',[3,4]),('7d',[3,4,5]),('all',list(range(1,13)))])
def test_urgency_boundaries(client,full_snapshot,urgency,expected):
    login(client); snap=many(full_snapshot)
    dates=['2026-10-23T17:59:59.999Z','2026-10-23T18:00:00.000Z','2026-10-23T18:00:00.001Z','2026-10-25T18:00:00.000Z','2026-10-30T18:00:00.000Z','2026-10-30T18:00:00.001Z']
    for i,s in enumerate(snap['services']):
        s['status']='active'; s['expiresAt']=dates[i] if i<6 else '2027-01-01T00:00:00Z'
    assert client.put('/api/v1/source/snapshot',json=snap).status_code==200
    res=client.get('/api/v1/customers',params={'urgency':urgency,'sort':'id','order':'asc','pageSize':100})
    assert res.status_code==200
    assert [r['id'] for r in res.json()['items']]==expected
    assert res.json()['summary']['totalCustomers']==12

def test_guarded_settings(session,config):
    c=session.client; before=c.get('/api/v1/model/settings').json(); n=before['version']
    assert c.patch('/api/v1/model/settings',json={'expectedVersion':n,'weights':{'funds_gap':.75}}).status_code==200
    state=database_state(config.db_path)
    r=c.patch('/api/v1/model/settings',json={'expectedVersion':n,'weights':{'funds_gap':.1}})
    assert r.status_code==409
    assert r.json()['detail']['code']=='settings_version_conflict'
    assert database_state(config.db_path)==state
    c=session.restart(); assert c.get('/api/v1/model/settings').json()['version']==n+1
    for x in [True,0,1.0,'1']:
        assert c.patch('/api/v1/model/settings',json={'expectedVersion':x}).status_code==422
    assert c.patch('/api/v1/model/settings',json={'expectedVersion':None}).status_code==200

def test_export_full_selection_and_encoding(client,full_snapshot):
    login(client); snap=many(full_snapshot);snap['accounts'][0]['email']='=SUM(1,2)@example.test';snap['accounts'][0]['balance']=9007199254740993
    assert client.put('/api/v1/source/snapshot',json=snap).status_code==200
    view=client.get('/api/v1/customers',params={'sort':'id','order':'asc','pageSize':2}).json()
    res=client.get('/api/v1/customers/export.csv',params={'runId':view['calculation']['runId'],'sort':'id','order':'asc'})
    assert res.status_code==200,res.text
    assert res.content.startswith(b'\xef\xbb\xbf'); assert b'\r\n' in res.content
    rows=list(csv.DictReader(io.StringIO(res.content.decode('utf-8-sig'))))
    assert len(rows)==12
    assert rows[0]['balance_eur']=='90071992547409.93'
    assert rows[0]['email']=='text:=SUM(1,2)@example.test'
    assert len({r['run_id'] for r in rows})==1
    assert all(r['source_generated_at']=='' for r in rows)
    assert client.patch('/api/v1/model/settings',json={'weights':{'funds_gap':.8}}).status_code==200
    assert client.get('/api/v1/customers/export.csv',params={'runId':view['calculation']['runId']}).status_code==409

def test_detail_and_source_context(client):
    login(client); view=client.get('/api/v1/customers').json(); id=view['items'][0]['id']
    res=client.get(f'/api/v1/customers/{id}')
    assert int(res.headers['X-Calculation-Run-Id'])==view['calculation']['runId']
    assert int(res.headers['X-Calculation-Settings-Version'])==view['calculation']['settingsVersion']
    assert res.headers['X-Calculation-As-Of']==view['summary']['asOf']
    assert res.headers['X-Calculation-Updated-At']==view['summary']['updatedAt']
    detail=res.json()
    assert set(detail)=={'id','email','balance','withdrawBalance','bonusBalance','bonusState','totalReplenished',
        'score','level','confidence','summary','summaryDetails','emailDraft','drivers','services','money','unknownReason','isEstimated','explanationRules'}
    src=client.get('/api/v1/source/snapshot')
    assert int(src.headers['X-Calculation-Run-Id'])==view['calculation']['runId']
    assert set(src.json())=={'accounts','services','transactions'}
