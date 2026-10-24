"""OIDC Authorization Code + PKCE без внешних зависимостей.

Поддерживается RS256 (по умолчанию у Keycloak, Okta, Google) и проверка
подписи по JWKS. Модуль не знает про БД и сессии: только discovery, обмен кода
и валидация ID token.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DISCOVERY_TTL_SECONDS = 300.0
JWKS_TTL_SECONDS = 300.0
CLOCK_SKEW_SECONDS = 30
REQUEST_TIMEOUT_SECONDS = 5.0

# DigestInfo prefix для EMSA-PKCS1-v1_5 с SHA-256 (RFC 8017).
SHA256_DIGEST_INFO = bytes.fromhex("3031300d060960864801650304020105000420")

_cache: dict[str, tuple[float, dict[str, Any]]] = {}


class OIDCError(Exception):
    """Ожидаемая ошибка OIDC: код попадает в URL входа, текст — только в лог."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def reset_cache() -> None:
    _cache.clear()


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _get_json(url: str, timeout: float = REQUEST_TIMEOUT_SECONDS) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise OIDCError("provider_unavailable") from exc


def _post_form(
    url: str, data: dict[str, str], timeout: float = REQUEST_TIMEOUT_SECONDS
) -> dict[str, Any]:
    body = urllib.parse.urlencode(data).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise OIDCError("exchange_failed") from exc
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        raise OIDCError("provider_unavailable") from exc


def _rewrite(url: str, issuer: str, internal_base: str) -> str:
    """Адрес для серверных вызовов: публичный issuer заменяется на внутренний."""
    if internal_base and issuer and url.startswith(issuer):
        return internal_base.rstrip("/") + url[len(issuer):]
    return url


def discover(issuer: str, internal_base: str = "") -> dict[str, Any]:
    """Загружает и кэширует discovery-документ провайдера."""
    key = f"{issuer}|{internal_base}"
    now = time.monotonic()
    cached = _cache.get(key)
    if cached is not None and cached[0] > now:
        return cached[1]
    base = (internal_base or issuer).rstrip("/")
    document = _get_json(f"{base}/.well-known/openid-configuration")
    for field in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
        if not isinstance(document.get(field), str) or not document[field].startswith(("http://", "https://")):
            raise OIDCError("provider_unavailable")
    if document.get("issuer") not in (None, issuer):
        raise OIDCError("issuer_mismatch")
    document = dict(document, issuer=issuer)
    _cache[key] = (now + DISCOVERY_TTL_SECONDS, document)
    return document


def make_pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    return verifier, challenge


def authorize_url(
    discovery: dict[str, Any],
    client_id: str,
    redirect_uri: str,
    scopes: str,
    state: str,
    nonce: str,
    code_challenge: str,
) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scopes,
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    endpoint = discovery["authorization_endpoint"]
    separator = "&" if "?" in endpoint else "?"
    return endpoint + separator + urllib.parse.urlencode(params)


def exchange_code(
    discovery: dict[str, Any],
    issuer: str,
    internal_base: str,
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
    code_verifier: str,
) -> dict[str, Any]:
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_verifier": code_verifier,
    }
    if client_secret:
        payload["client_secret"] = client_secret
    token = _post_form(_rewrite(discovery["token_endpoint"], issuer, internal_base), payload)
    if not isinstance(token.get("id_token"), str):
        raise OIDCError("exchange_failed")
    return token


def fetch_jwks(jwks_uri: str, use_cache: bool = True) -> list[dict[str, Any]]:
    now = time.monotonic()
    key = f"jwks|{jwks_uri}"
    cached = _cache.get(key)
    if use_cache and cached is not None and cached[0] > now:
        return cached[1].get("keys", [])
    document = _get_json(jwks_uri)
    keys = document.get("keys")
    if not isinstance(keys, list):
        raise OIDCError("jwks_invalid")
    _cache[key] = (now + JWKS_TTL_SECONDS, {"keys": keys})
    return keys


def _rsa_verify_rs256(signing_input: bytes, signature: bytes, jwk: dict[str, Any]) -> bool:
    if jwk.get("kty") != "RSA":
        return False
    try:
        modulus = int.from_bytes(_b64url_decode(jwk["n"]), "big")
        exponent = int.from_bytes(_b64url_decode(jwk["e"]), "big")
    except (KeyError, ValueError):
        return False
    if modulus <= 0 or exponent <= 0:
        return False
    size = (modulus.bit_length() + 7) // 8
    if len(signature) != size:
        return False
    signed = int.from_bytes(signature, "big")
    if signed >= modulus:
        return False
    encoded = pow(signed, exponent, modulus).to_bytes(size, "big")
    digest_info = SHA256_DIGEST_INFO + hashlib.sha256(signing_input).digest()
    if size < len(digest_info) + 11:
        return False
    expected = b"\x00\x01" + b"\xff" * (size - len(digest_info) - 3) + b"\x00" + digest_info
    return hmac.compare_digest(encoded, expected)


def validate_id_token(
    token: str,
    discovery: dict[str, Any],
    issuer: str,
    client_id: str,
    expected_nonce: str | None,
    internal_base: str = "",
    now: float | None = None,
    jwks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise OIDCError("token_invalid")
    try:
        header = json.loads(_b64url_decode(parts[0]))
        claims = json.loads(_b64url_decode(parts[1]))
    except (ValueError, json.JSONDecodeError) as exc:
        raise OIDCError("token_invalid") from exc
    if not isinstance(header, dict) or not isinstance(claims, dict):
        raise OIDCError("token_invalid")
    if header.get("alg") != "RS256":
        raise OIDCError("token_invalid")
    key_id = header.get("kid")
    if not isinstance(key_id, str):
        raise OIDCError("token_invalid")

    signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
    try:
        signature = _b64url_decode(parts[2])
    except ValueError as exc:
        raise OIDCError("token_invalid") from exc

    keys = jwks if jwks is not None else fetch_jwks(_rewrite(discovery["jwks_uri"], issuer, internal_base))
    matches = [key for key in keys if key.get("kid") == key_id]
    if not matches and jwks is None:
        # Ротация ключей: один раз перечитываем JWKS без кэша.
        keys = fetch_jwks(_rewrite(discovery["jwks_uri"], issuer, internal_base), use_cache=False)
        matches = [key for key in keys if key.get("kid") == key_id]
    if not matches or not any(_rsa_verify_rs256(signing_input, signature, key) for key in matches):
        raise OIDCError("token_invalid")

    audience = claims.get("aud")
    audiences = [audience] if isinstance(audience, str) else list(audience or [])
    if client_id not in audiences:
        raise OIDCError("audience_mismatch")
    if isinstance(audience, list) and claims.get("azp") not in (None, client_id):
        raise OIDCError("audience_mismatch")
    if claims.get("iss") != issuer:
        raise OIDCError("issuer_mismatch")

    moment = time.time() if now is None else now
    expires = claims.get("exp")
    if not isinstance(expires, (int, float)) or moment > float(expires) + CLOCK_SKEW_SECONDS:
        raise OIDCError("token_expired")
    if isinstance(claims.get("iat"), (int, float)) and float(claims["iat"]) > moment + CLOCK_SKEW_SECONDS:
        raise OIDCError("token_invalid")
    if isinstance(claims.get("nbf"), (int, float)) and float(claims["nbf"]) > moment + CLOCK_SKEW_SECONDS:
        raise OIDCError("token_invalid")

    if not isinstance(claims.get("sub"), str) or not claims["sub"]:
        raise OIDCError("token_invalid")
    if expected_nonce is not None:
        actual = claims.get("nonce")
        if not isinstance(actual, str) or not hmac.compare_digest(actual, expected_nonce):
            raise OIDCError("nonce_mismatch")
    return claims
