from contextlib import ExitStack
import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from app.config import Config
from app.main import create_app

ROOT = Path(__file__).resolve().parents[2]


def login(client):
    assert client.post('/api/v1/auth/login', json={'email': 'admin@example.test', 'password': 'admin123'}).status_code == 200


def database_state(path):
    with sqlite3.connect(path) as conn:
        return {table: conn.execute(f'SELECT * FROM {table} ORDER BY rowid').fetchall()
                for table in ('accounts', 'services', 'transactions', 'settings', 'score_runs', 'customer_scores', 'sqlite_sequence')}


@pytest.fixture()
def config(tmp_path, monkeypatch):
    for key, value in {'APP_DB': str(tmp_path / 'test.db'), 'SEED_PATH': str(ROOT / 'data/seed.json'),
                       'AS_OF': '2026-10-23T18:00:00.000Z', 'ADMIN_EMAIL': 'admin@example.test',
                       'ADMIN_PASSWORD': 'admin123', 'SEED_ON_START': 'true'}.items():
        monkeypatch.setenv(key, value)
    return Config.from_env()


@pytest.fixture()
def client(config):
    with TestClient(create_app(config), raise_server_exceptions=False) as c:
        yield c


@pytest.fixture()
def session(config):
    class Session:
        def restart(self):
            self.stack.close()
            self.stack = ExitStack()
            self.client = self.stack.enter_context(TestClient(create_app(config), raise_server_exceptions=False))
            login(self.client)
            return self.client
    s = Session()
    s.stack = ExitStack()
    s.restart()
    yield s
    s.stack.close()


@pytest.fixture()
def full_snapshot():
    return json.loads((ROOT / 'data/seed.json').read_text())
