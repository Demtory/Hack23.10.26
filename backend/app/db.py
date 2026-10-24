from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS oidc_flows (
    state TEXT PRIMARY KEY,
    nonce TEXT NOT NULL,
    code_verifier TEXT NOT NULL,
    redirect_to TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    balance INTEGER NOT NULL DEFAULT 0,
    withdraw_balance INTEGER NOT NULL DEFAULT 0,
    total_replenished INTEGER NOT NULL DEFAULT 0,
    bonus_balance INTEGER NOT NULL DEFAULT 0,
    bonus_state TEXT NOT NULL DEFAULT 'locked'
);

CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY,
    owner_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
    name TEXT NOT NULL,
    payment_term TEXT NOT NULL,
    auto_prolong INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    status TEXT NOT NULL,
    price INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY,
    service_id INTEGER NOT NULL REFERENCES services(id) ON DELETE RESTRICT,
    amount INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    performed_at TEXT,
    created_at TEXT NOT NULL,
    type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    payload TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL,
    feature_schema_version INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS score_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    as_of TEXT NOT NULL,
    created_at TEXT NOT NULL,
    settings_version INTEGER NOT NULL,
    summary TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS customer_scores (
    run_id INTEGER NOT NULL REFERENCES score_runs(id) ON DELETE CASCADE,
    account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    score REAL,
    level TEXT NOT NULL,
    confidence REAL NOT NULL,
    drivers TEXT NOT NULL,
    detail TEXT NOT NULL,
    expected_loss INTEGER NOT NULL,
    amount_at_risk INTEGER NOT NULL,
    coverage REAL NOT NULL,
    services_at_risk INTEGER NOT NULL,
    is_estimated INTEGER NOT NULL,
    unknown_reason TEXT,
    PRIMARY KEY (run_id, account_id)
);

CREATE INDEX IF NOT EXISTS services_owner_idx ON services(owner_id);
CREATE INDEX IF NOT EXISTS transactions_service_idx ON transactions(service_id);
CREATE INDEX IF NOT EXISTS customer_scores_run_idx ON customer_scores(run_id);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(settings)")}
    if "feature_schema_version" not in columns:
        conn.execute("ALTER TABLE settings ADD COLUMN feature_schema_version INTEGER NOT NULL DEFAULT 1")
    user_columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
    if "oidc_subject" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN oidc_subject TEXT")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS users_oidc_subject_idx ON users(oidc_subject) "
        "WHERE oidc_subject IS NOT NULL"
    )
    conn.commit()


@contextmanager
def transaction(conn: sqlite3.Connection):
    """One owner for source/settings, results and commit, including commit errors."""
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield
        conn.commit()
    except BaseException:
        conn.rollback()
        raise


@contextmanager
def read_snapshot(conn: sqlite3.Connection):
    """Pin all SELECTs and account joins without taking the writer lock."""
    try:
        conn.execute('BEGIN')
        yield
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
