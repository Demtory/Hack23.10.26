"""OIDC: сквозной вход через локальный фейковый провайдер.

Ключ RSA генерируется в тесте (чистый Python), подпись RS256 проверяется тем же
кодом, что и в проде, поэтому тест ловит ошибки проверки токена, а не только ветвления.
"""
from __future__ import annotations

import base64
import hashlib
import json
import random
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from fastapi.testclient import TestClient

from app import oidc as oidc_module
from app.config import Config
from app.main import create_app

SHA256_DIGEST_INFO = bytes.fromhex("3031300d060960864801650304020105000420")


# ---------------------------------------------------------------- RSA helpers

def _is_probable_prime(value: int, rounds: int = 12) -> bool:
    if value < 2:
        return False
    for small in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29):
        if value % small == 0:
            return value == small
    d, s = value - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for _ in range(rounds):
        base = random.randrange(2, value - 2)
        x = pow(base, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(s - 1):
            x = pow(x, 2, value)
            if x == value - 1:
                break
        else:
            return False
    return True


def _random_prime(bits: int) -> int:
    while True:
        candidate = random.getrandbits(bits) | (1 << (bits - 1)) | 1
        if _is_probable_prime(candidate):
            return candidate


class SigningKey:
    def __init__(self, bits: int = 1024, kid: str = "test-key") -> None:
        e = 65537
        while True:
            p = _random_prime(bits // 2)
            q = _random_prime(bits // 2)
            if p == q:
                continue
            phi = (p - 1) * (q - 1)
            if phi % e:
                break
        self.n = p * q
        self.e = e
        self.d = pow(e, -1, phi)
        self.kid = kid

    @staticmethod
    def _b64(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

    @property
    def jwk(self) -> dict[str, str]:
        size = (self.n.bit_length() + 7) // 8
        return {
            "kty": "RSA",
            "kid": self.kid,
            "use": "sig",
            "alg": "RS256",
            "n": self._b64(self.n.to_bytes(size, "big")),
            "e": self._b64(self.e.to_bytes(3, "big")),
        }

    def sign(self, claims: dict, kid: str | None = None) -> str:
        header = {"alg": "RS256", "typ": "JWT", "kid": kid or self.kid}
        signing_input = (
            self._b64(json.dumps(header, separators=(",", ":")).encode())
            + "."
            + self._b64(json.dumps(claims, separators=(",", ":")).encode())
        )
        digest_info = SHA256_DIGEST_INFO + hashlib.sha256(signing_input.encode()).digest()
        size = (self.n.bit_length() + 7) // 8
        encoded = b"\x00\x01" + b"\xff" * (size - len(digest_info) - 3) + b"\x00" + digest_info
        signature = pow(int.from_bytes(encoded, "big"), self.d, self.n).to_bytes(size, "big")
        return signing_input + "." + self._b64(signature)


# --------------------------------------------------------------- fake provider

_SESSION_KEY: SigningKey | None = None


def session_key() -> SigningKey:
    global _SESSION_KEY
    if _SESSION_KEY is None:
        _SESSION_KEY = SigningKey()
    return _SESSION_KEY


class FakeIdP:
    def __init__(self) -> None:
        self.key = session_key()
        self.token_status = 200
        self.token_claims_override: dict | None = None
        self.last_token_form: dict[str, list[str]] = {}
        self.expected_code = "test-code"
        provider = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):  # noqa: D401 - тишина в выводе тестов
                return

            def _send(self, status: int, payload: dict) -> None:
                body = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):  # noqa: N802 - stdlib API
                if self.path.endswith("/.well-known/openid-configuration"):
                    self._send(200, {
                        "issuer": provider.issuer,
                        "authorization_endpoint": provider.issuer + "/authorize",
                        "token_endpoint": provider.issuer + "/token",
                        "jwks_uri": provider.issuer + "/jwks",
                        "response_types_supported": ["code"],
                        "subject_types_supported": ["public"],
                        "id_token_signing_alg_values_supported": ["RS256"],
                    })
                elif self.path.endswith("/jwks"):
                    self._send(200, {"keys": [provider.key.jwk]})
                else:
                    self._send(404, {"error": "not_found"})

            def do_POST(self):  # noqa: N802 - stdlib API
                length = int(self.headers.get("Content-Length", "0"))
                form = urllib.parse.parse_qs(self.rfile.read(length).decode())
                provider.last_token_form = form
                if self.path.endswith("/token") and form.get("code") == [provider.expected_code]:
                    self._send(200, {
                        "access_token": "access",
                        "token_type": "Bearer",
                        "id_token": provider.id_token(),
                    })
                else:
                    self._send(401, {"error": "invalid_grant"})

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.issuer = f"http://127.0.0.1:{self.server.server_port}/realms/test"

    def id_token(self) -> str:
        claims = self.token_claims_override or {
            "iss": self.issuer,
            "aud": "risk-desk",
            "sub": "sso-user-1",
            "email": "marketer@example.test",
            "email_verified": True,
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,
        }
        return self.key.sign(claims)

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()


# --------------------------------------------------------------------- fixtures

@pytest.fixture()
def idp():
    provider = FakeIdP()
    oidc_module.reset_cache()
    yield provider
    provider.stop()
    oidc_module.reset_cache()


@pytest.fixture()
def oidc_config(tmp_path, monkeypatch, idp):
    values = {
        "APP_DB": str(tmp_path / "oidc.db"),
        "SEED_PATH": str(tmp_path.parent / "seed-missing.json"),
        "AS_OF": "2026-10-23T18:00:00.000Z",
        "ADMIN_EMAIL": "admin@example.test",
        "ADMIN_PASSWORD": "admin123",
        "SEED_ON_START": "false",
        "OIDC_ISSUER": idp.issuer,
        "OIDC_CLIENT_ID": "risk-desk",
        "OIDC_CLIENT_SECRET": "dev-secret",
        "OIDC_REDIRECT_URI": "http://testserver/api/v1/auth/oidc/callback",
        "OIDC_PROVIDER_NAME": "Keycloak",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    return Config.from_env()


@pytest.fixture()
def oidc_client(oidc_config):
    with TestClient(create_app(oidc_config), raise_server_exceptions=False) as client:
        yield client


def start_flow(client) -> tuple[str, dict[str, list[str]]]:
    response = client.get("/api/v1/auth/oidc/start", follow_redirects=False)
    assert response.status_code == 303, response.text
    location = response.headers["location"]
    params = urllib.parse.parse_qs(urllib.parse.urlparse(location).query)
    return location, params


def finish(client, idp: FakeIdP, state: str, code: str = "test-code"):
    return client.get(
        "/api/v1/auth/oidc/callback",
        params={"code": code, "state": state},
        follow_redirects=False,
    )


# ------------------------------------------------------------------------ tests

def test_oidc_config_disabled_without_env(client):
    body = client.get("/api/v1/auth/oidc/config").json()
    assert body == {"enabled": False, "providerName": "SSO"}
    assert client.get("/api/v1/auth/oidc/start", follow_redirects=False).status_code == 404


def test_oidc_config_enabled(oidc_client):
    assert oidc_client.get("/api/v1/auth/oidc/config").json() == {"enabled": True, "providerName": "Keycloak"}


def test_authorize_redirect_has_pkce_and_state(oidc_client):
    location, params = start_flow(oidc_client)
    assert location.startswith(f"http://127.0.0.1:")
    assert params["response_type"] == ["code"]
    assert params["client_id"] == ["risk-desk"]
    assert params["code_challenge_method"] == ["S256"]
    assert len(params["state"][0]) > 20 and len(params["nonce"][0]) > 20
    assert params["redirect_uri"] == ["http://testserver/api/v1/auth/oidc/callback"]


def test_oidc_login_creates_user_and_session(oidc_client, oidc_config, idp):
    _, params = start_flow(oidc_client)
    idp.token_claims_override = {
        "iss": idp.issuer, "aud": "risk-desk", "sub": "sso-user-1",
        "email": "Marketer@Example.test", "email_verified": True,
        "nonce": params["nonce"][0], "iat": int(time.time()), "exp": int(time.time()) + 300,
    }
    response = finish(oidc_client, idp, params["state"][0])
    assert response.status_code == 303
    assert response.headers["location"] == "/#/"
    assert "sid" in response.cookies
    # code_verifier и secret уходят провайдеру
    assert idp.last_token_form["code_verifier"][0]
    assert idp.last_token_form["client_secret"] == ["dev-secret"]

    me = oidc_client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "marketer@example.test"

    import sqlite3
    with sqlite3.connect(oidc_config.db_path) as conn:
        row = conn.execute(
            "SELECT email, password_hash, oidc_subject FROM users WHERE email = ?",
            ("marketer@example.test",),
        ).fetchall()
    assert row == [("marketer@example.test", "", "sso-user-1")]


def test_password_login_still_works(oidc_client, oidc_config):
    oidc_client.post("/api/v1/auth/login", json={"email": "admin@example.test", "password": "admin123"})
    assert oidc_client.get("/api/v1/auth/me").status_code == 200


def test_sso_user_cannot_use_password_login(oidc_client, idp):
    _, params = start_flow(oidc_client)
    idp.token_claims_override = {
        "iss": idp.issuer, "aud": "risk-desk", "sub": "sso-user-1",
        "email": "marketer@example.test", "email_verified": True,
        "nonce": params["nonce"][0], "iat": int(time.time()), "exp": int(time.time()) + 300,
    }
    assert finish(oidc_client, idp, params["state"][0]).status_code == 303
    oidc_client.cookies.clear()
    response = oidc_client.post(
        "/api/v1/auth/login", json={"email": "marketer@example.test", "password": "admin123"}
    )
    assert response.status_code == 401


def test_state_is_single_use(oidc_client, idp):
    _, params = start_flow(oidc_client)
    idp.token_claims_override = {
        "iss": idp.issuer, "aud": "risk-desk", "sub": "sso-user-1",
        "email": "marketer@example.test", "email_verified": True,
        "nonce": params["nonce"][0], "iat": int(time.time()), "exp": int(time.time()) + 300,
    }
    assert finish(oidc_client, idp, params["state"][0]).status_code == 303
    again = finish(oidc_client, idp, params["state"][0])
    assert again.headers["location"] == "/#/login?sso_error=state_invalid"


def test_unknown_state_rejected(oidc_client, idp):
    response = finish(oidc_client, idp, "forged-state")
    assert response.status_code == 303
    assert response.headers["location"] == "/#/login?sso_error=state_invalid"


@pytest.mark.parametrize("override,expected", [
    ({"nonce": "wrong"}, "nonce_mismatch"),
    ({"iss": "http://evil.example.test"}, "issuer_mismatch"),
    ({"aud": "another-client"}, "audience_mismatch"),
    ({"exp": 1000}, "token_expired"),
    ({"email": ""}, "email_unverified"),
    ({"email_verified": False}, "email_unverified"),
])
def test_invalid_token_claims_are_rejected(oidc_client, idp, override, expected):
    _, params = start_flow(oidc_client)
    claims = {
        "iss": idp.issuer, "aud": "risk-desk", "sub": "sso-user-1",
        "email": "marketer@example.test", "email_verified": True,
        "nonce": params["nonce"][0], "iat": int(time.time()), "exp": int(time.time()) + 300,
    }
    claims.update(override)
    idp.token_claims_override = claims
    response = finish(oidc_client, idp, params["state"][0])
    assert response.status_code == 303
    assert response.headers["location"] == f"/#/login?sso_error={expected}"


def test_bad_signature_and_unknown_kid_rejected(oidc_client, idp):
    _, params = start_flow(oidc_client)
    token = idp.key.sign({
        "iss": idp.issuer, "aud": "risk-desk", "sub": "sso-user-1",
        "email": "marketer@example.test", "nonce": params["nonce"][0],
        "iat": int(time.time()), "exp": int(time.time()) + 300,
    })
    head, body, signature = token.split(".")
    tampered = f"{head}.{body}.{signature[:-4]}AAAA"
    original_id_token = idp.id_token
    idp.id_token = lambda: tampered  # type: ignore[method-assign]
    response = finish(oidc_client, idp, params["state"][0])
    assert response.headers["location"] == "/#/login?sso_error=token_invalid"

    idp.id_token = lambda: idp.key.sign({  # type: ignore[method-assign]
        "iss": idp.issuer, "aud": "risk-desk", "sub": "sso-user-1",
        "email": "marketer@example.test", "nonce": params["nonce"][0],
        "iat": int(time.time()), "exp": int(time.time()) + 300,
    }, kid="missing-key")
    _, second = start_flow(oidc_client)
    idp.token_claims_override = {
        "iss": idp.issuer, "aud": "risk-desk", "sub": "sso-user-1",
        "email": "marketer@example.test", "nonce": second["nonce"][0],
        "iat": int(time.time()), "exp": int(time.time()) + 300,
    }
    idp.id_token = original_id_token  # type: ignore[method-assign]
    second_token = idp.key.sign(idp.token_claims_override, kid="missing-key")
    idp.id_token = lambda: second_token  # type: ignore[method-assign]
    response = finish(oidc_client, idp, second["state"][0])
    assert response.headers["location"] == "/#/login?sso_error=token_invalid"


def test_exchange_failure_reported(oidc_client, idp):
    _, params = start_flow(oidc_client)
    response = finish(oidc_client, idp, params["state"][0], code="wrong-code")
    assert response.headers["location"] == "/#/login?sso_error=exchange_failed"


def test_provider_unavailable_is_soft_failure(oidc_client, idp):
    idp.stop()
    response = oidc_client.get("/api/v1/auth/oidc/start", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/#/login?sso_error=provider_unavailable"
