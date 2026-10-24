import json
from pathlib import Path
from app.main import create_app
from .conftest import login

ROOT=Path(__file__).resolve().parents[2]


def test_saved_contract_matches_application():
    assert json.loads((ROOT/'openapi.json').read_text())==create_app().openapi()


def test_security_and_money_contract(client):
    s=client.get('/api/v1/openapi.json').json()
    for path in ('/api/v1/customers','/api/v1/model/settings','/api/v1/source/snapshot'):
        assert s['paths'][path]['get']['security']==[{'APIKeyCookie':[]},{'HTTPBearer':[]}]
        assert client.get(path).status_code==401
    security=s['paths']['/api/v1/auth/logout']['post']['security']
    assert security==[{'APIKeyCookie':[]},{'HTTPBearer':[]},{}]
    assert '/api/v1/customers/{id}' in s['paths']
    schemas=s['components']['schemas']
    for model,fields in [('AccountIn',['balance','withdrawBalance','totalReplenished','bonusBalance']),('ServiceIn',['price']),('TransactionIn',['amount'])]:
        for field in fields:
            prop=schemas[model]['properties'][field]
            assert prop['type']=='integer' and prop['minimum']==0 and prop['maximum']==2**63-1
            assert '100.0' in prop['description']
    assert set(schemas['EffectiveThresholds']['required'])=={'medium','high'}
    page=schemas['CustomerPageOut']['properties']
    assert {'topLosses','summary','calculation'} <= set(page)
    assert page['topLosses']['maxItems']==5
    assert client.get('/metrics').status_code==200
    login(client)
    assert client.get('/api/v1/openapi.json').json()==s
