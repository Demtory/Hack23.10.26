import copy
import json
import sqlite3
import pytest
from fastapi.testclient import TestClient
from app import scoring, store, main, api
from app.main import create_app
from .conftest import database_state


def add_feature(monkeypatch, generation=2, code='future_signal'):
    monkeypatch.setitem(scoring.FEATURE_GENERATIONS,generation,frozenset({code}))
    monkeypatch.setitem(scoring.DEFAULT_SETTINGS['weights'],code,0.2)
    monkeypatch.setattr(api,'FEATURES_META',scoring.FEATURES_META+[dict(scoring.FEATURES_META[0],code=code,default=.2)])


def test_old_upgrade_once(session,config,monkeypatch):
    assert session.client.patch('/api/v1/model/settings',json={'weights':{'funds_gap':.8},'thresholds':{'medium':35,'high':75},'money':{'balanceMitigation':.7}}).status_code==200
    before=session.client.get('/api/v1/model/settings').json()
    details=session.client.get('/api/v1/customers/5').json()
    session.stack.close()
    add_feature(monkeypatch)
    c=session.restart();after=c.get('/api/v1/model/settings').json()
    assert after['weights']=={**before['weights'],'future_signal':0}
    assert after['version']==before['version']+1
    assert after['thresholds']==before['thresholds'] and after['money']==before['money']
    assert c.get('/api/v1/customers/5').json()==details
    assert session.restart().get('/api/v1/model/settings').json()==after
    with sqlite3.connect(config.db_path) as db:
        assert db.execute('SELECT feature_schema_version FROM settings').fetchone()[0]==2


@pytest.mark.parametrize('damage',['missing','unknown','negative','nan','future_generation'])
def test_corrupt_old_not_repaired(session,config,monkeypatch,damage):
    session.stack.close()
    with sqlite3.connect(config.db_path) as c:
        row=c.execute('SELECT payload FROM settings').fetchone();payload=json.loads(row[0])
        if damage=='missing': payload['weights'].pop('commitment')
        if damage=='unknown': payload['weights']['bogus']=0
        if damage=='negative': payload['weights']['commitment']=-1
        if damage=='nan': payload['weights']['commitment']=float('nan')
        c.execute('UPDATE settings SET payload=?',(json.dumps(payload),))
        if damage=='future_generation': c.execute('UPDATE settings SET feature_schema_version=99')
    before=database_state(config.db_path);add_feature(monkeypatch)
    with pytest.raises((ValueError,TypeError)):
        with TestClient(create_app(config)): pass
    assert database_state(config.db_path)==before


def test_fresh_current_defaults(config,monkeypatch):
    add_feature(monkeypatch)
    with TestClient(create_app(config)) as c:
        from .conftest import login
        login(c);s=c.get('/api/v1/model/settings').json()
        assert s['version']==1 and s['weights']['future_signal']==.2


def test_explicit_future_weight_preserved(session,config,monkeypatch):
    session.stack.close()
    with sqlite3.connect(config.db_path) as c:
        s=json.loads(c.execute('SELECT payload FROM settings').fetchone()[0]);s['weights']['future_signal']=.3
        c.execute('UPDATE settings SET payload=?',(json.dumps(s),))
    add_feature(monkeypatch)
    assert session.restart().get('/api/v1/model/settings').json()['weights']['future_signal']==.3


def test_physical_legacy_schema(session,config,monkeypatch):
    session.stack.close()
    with sqlite3.connect(config.db_path) as c:
        c.execute('ALTER TABLE settings DROP COLUMN feature_schema_version')
    add_feature(monkeypatch)
    c=session.restart()
    assert c.get('/api/v1/model/settings').json()['weights']['future_signal']==0
    assert session.restart().get('/api/v1/model/settings').json()['version']==2


@pytest.mark.parametrize('weight',[0,.3])
def test_multiple_generations_and_explicit(session,config,monkeypatch,weight):
    before=session.client.get('/api/v1/model/settings').json();session.stack.close()
    add_feature(monkeypatch)
    monkeypatch.setitem(scoring.FEATURE_GENERATIONS,3,frozenset({'second_signal'}))
    monkeypatch.setitem(scoring.DEFAULT_SETTINGS['weights'],'second_signal',.1)
    monkeypatch.setattr(api,'FEATURES_META',api.FEATURES_META+[dict(api.FEATURES_META[0],code='second_signal',default=.1)])
    with sqlite3.connect(config.db_path) as c:
        payload=json.loads(c.execute('SELECT payload FROM settings').fetchone()[0]);payload['weights']['future_signal']=weight
        c.execute('UPDATE settings SET payload=?',(json.dumps(payload),))
    after=session.restart().get('/api/v1/model/settings').json()
    assert after['weights']=={**before['weights'],'future_signal':weight,'second_signal':0}
    assert after['version']==before['version']+1
    assert session.restart().get('/api/v1/model/settings').json()==after


def test_missing_current_key_not_repaired(session,config,monkeypatch):
    session.stack.close();add_feature(monkeypatch);session.restart();session.stack.close()
    with sqlite3.connect(config.db_path) as c:
        payload=json.loads(c.execute('SELECT payload FROM settings').fetchone()[0]);payload['weights'].pop('future_signal')
        c.execute('UPDATE settings SET payload=?',(json.dumps(payload),))
    before=database_state(config.db_path)
    with pytest.raises(ValueError):
        with TestClient(create_app(config)): pass
    assert database_state(config.db_path)==before


def test_empty_upgrade_preserves_empty(session,monkeypatch):
    assert session.client.put('/api/v1/source/snapshot',json={'accounts':[],'services':[],'transactions':[]}).status_code==200
    session.stack.close();add_feature(monkeypatch)
    c=session.restart()
    assert c.get('/api/v1/source/snapshot').json()=={'accounts':[],'services':[],'transactions':[]}
    assert c.get('/api/v1/customers').json()['total']==0
