import hashlib
import sqlite3
import pytest


def issue(client):
    client.cookies.clear()
    r=client.post('/api/v1/auth/login',json={'email':'admin@example.test','password':'admin123'})
    assert r.status_code==200
    token=r.json()['token'];client.cookies.clear()
    return token


@pytest.mark.parametrize('method',['cookie','bearer'])
def test_logout_revokes_only_current(client,method):
    current=issue(client);independent=issue(client)
    headers={'Authorization':f'Bearer {current}'} if method=='bearer' else {'Cookie':f'sid={current}'}
    assert client.get('/api/v1/auth/me',headers=headers).status_code==200
    assert client.post('/api/v1/auth/logout',headers=headers).status_code==200
    client.cookies.clear()
    for old in ({'Cookie':f'sid={current}'},{'Authorization':f'Bearer {current}'}):
        assert client.get('/api/v1/auth/me',headers=old).status_code==401
    assert client.get('/api/v1/auth/me',headers={'Authorization':f'Bearer {independent}'}).status_code==200
    assert client.post('/api/v1/auth/logout',headers=headers).status_code==200
    assert client.post('/api/v1/auth/logout').status_code==200


def test_cookie_priority(client):
    cookie=issue(client);bearer=issue(client)
    headers={'Cookie':f'sid={cookie}','Authorization':f'Bearer {bearer}'}
    assert client.post('/api/v1/auth/logout',headers=headers).status_code==200
    client.cookies.clear()
    assert client.get('/api/v1/auth/me',headers={'Authorization':f'Bearer {bearer}'}).status_code==200
    assert client.get('/api/v1/auth/me',headers=headers).status_code==401
    invalid={'Cookie':'sid=invalid','Authorization':f'Bearer {bearer}'}
    assert client.get('/api/v1/auth/me',headers=invalid).status_code==401
    assert client.post('/api/v1/auth/logout',headers=invalid).status_code==200
    assert client.get('/api/v1/auth/me',headers={'Authorization':f'Bearer {bearer}'}).status_code==200


def test_expired_logout(client,config):
    token=issue(client)
    with sqlite3.connect(config.db_path) as c:
        c.execute("UPDATE sessions SET expires_at='2000-01-01T00:00:00Z' WHERE token_hash=?",(hashlib.sha256(token.encode()).hexdigest(),))
    assert client.post('/api/v1/auth/logout',headers={'Authorization':f'Bearer {token}'}).status_code==200
    assert client.get('/api/v1/auth/me',headers={'Authorization':f'Bearer {token}'}).status_code==401


def test_revocation_restart_and_write(session):
    c=session.client;revoked=issue(c);independent=issue(c)
    assert c.post('/api/v1/auth/logout',headers={'Authorization':f'Bearer {revoked}'}).status_code==200
    c=session.restart();c.cookies.clear()
    for headers in ({'Cookie':f'sid={revoked}'},{'Authorization':f'Bearer {revoked}'}):
        assert c.get('/api/v1/customers',headers=headers).status_code==401
        assert c.patch('/api/v1/model/settings',json={'weights':{'funds_gap':.5}},headers=headers).status_code==401
    assert c.get('/api/v1/customers',headers={'Authorization':f'Bearer {independent}'}).status_code==200


def test_logout_failure_keeps_sessions(client,monkeypatch):
    from app import api
    first=issue(client);second=issue(client)
    def fail(*a): raise RuntimeError('database unavailable')
    with monkeypatch.context() as m:
        m.setattr(api,'delete_session',fail)
        assert client.post('/api/v1/auth/logout',headers={'Authorization':f'Bearer {first}'}).status_code==500
    for token in (first,second):
        assert client.get('/api/v1/auth/me',headers={'Authorization':f'Bearer {token}'}).status_code==200


def test_logout_commit_failure(client,monkeypatch,config):
    from app import api
    first=issue(client);second=issue(client)
    class Fail(sqlite3.Connection):
        def commit(self): raise RuntimeError('commit failure')
    def fail_connect(path):
        c=sqlite3.connect(path,factory=Fail,check_same_thread=False);c.row_factory=sqlite3.Row
        return c
    with monkeypatch.context() as m:
        m.setattr(api,'connect',fail_connect)
        assert client.post('/api/v1/auth/logout',headers={'Authorization':f'Bearer {first}'}).status_code==500
    for token in (first,second):
        assert client.get('/api/v1/auth/me',headers={'Authorization':f'Bearer {token}'}).status_code==200
