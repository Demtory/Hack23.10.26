import dataclasses

from fastapi.testclient import TestClient

from app.main import create_app
from .conftest import login


def demo_config(config, token="demo-secret"):
    return dataclasses.replace(config, demo_login_token=token)


def test_demo_disabled_by_default(config):
    with TestClient(create_app(config)) as client:
        response = client.get("/api/v1/auth/demo", params={"token": "anything"})
        assert response.status_code == 404
        assert client.get("/api/v1/auth/me").status_code == 401


def test_demo_requires_correct_token(config):
    with TestClient(create_app(demo_config(config))) as client:
        assert client.get("/api/v1/auth/demo", params={"token": "wrong"}).status_code == 401
        assert client.get("/api/v1/auth/demo").status_code == 401
        assert client.get("/api/v1/auth/me").status_code == 401


def test_demo_token_opens_session(config):
    with TestClient(create_app(demo_config(config))) as client:
        response = client.get("/api/v1/auth/demo", params={"token": "demo-secret"}, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == "/#/overview"
        cookie = response.cookies.get("sid")
        assert cookie
        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["email"] == "admin@example.test"
        # кука даёт доступ к закрытому API
        assert client.get("/api/v1/customers").status_code == 200


def test_password_login_still_sets_session(config):
    with TestClient(create_app(config)) as client:
        login(client)
        assert client.cookies.get("sid")
        assert client.get("/api/v1/auth/me").status_code == 200
