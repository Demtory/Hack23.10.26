from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

PBKDF2_ITERATIONS = 200_000
SESSION_COOKIE = "sid"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt_b64, digest_b64 = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def ensure_admin(conn: sqlite3.Connection, email: str, password: str) -> None:
    row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
            (email, hash_password(password), iso_z(utcnow())),
        )
        conn.commit()


def authenticate(conn: sqlite3.Connection, email: str, password: str) -> int | None:
    row = conn.execute(
        "SELECT id, password_hash FROM users WHERE email = ?", (email,)
    ).fetchone()
    if row is None or not verify_password(password, row["password_hash"]):
        return None
    return int(row["id"])


def create_session(conn: sqlite3.Connection, user_id: int, hours: int) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    now = utcnow()
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
        (token_hash, user_id, iso_z(now + timedelta(hours=hours)), iso_z(now)),
    )
    conn.commit()
    return token


def get_session_user(conn: sqlite3.Connection, token: str) -> dict | None:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    row = conn.execute(
        """
        SELECT u.id, u.email, s.expires_at
        FROM sessions s JOIN users u ON u.id = s.user_id
        WHERE s.token_hash = ?
        """,
        (token_hash,),
    ).fetchone()
    if row is None:
        return None
    expires = datetime.fromisoformat(row["expires_at"].replace("Z", "+00:00"))
    if expires <= utcnow():
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
        conn.commit()
        return None
    return {"id": int(row["id"]), "email": row["email"]}


def delete_session(conn: sqlite3.Connection, token: str) -> None:
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
    conn.commit()
