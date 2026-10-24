from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .schemas import SnapshotIn
from .scoring import default_settings, iso_z


def _as_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def validate_snapshot(snapshot: SnapshotIn) -> dict[str, list[dict[str, Any]]]:
    account_ids = [a.id for a in snapshot.accounts]
    emails = [a.email for a in snapshot.accounts]
    service_ids = [s.id for s in snapshot.services]
    transaction_ids = [t.id for t in snapshot.transactions]

    if len(set(account_ids)) != len(account_ids):
        raise ValueError("duplicate account id")
    if len(set(emails)) != len(emails):
        raise ValueError("duplicate account email")
    if len(set(service_ids)) != len(service_ids):
        raise ValueError("duplicate service id")
    if len(set(transaction_ids)) != len(transaction_ids):
        raise ValueError("duplicate transaction id")
    if any("@" not in email for email in emails):
        raise ValueError("invalid email")

    known_accounts = set(account_ids)
    known_services = set(service_ids)
    for service in snapshot.services:
        if service.owner_id not in known_accounts:
            raise ValueError(f"service {service.id}: unknown ownerId {service.owner_id}")
    for txn in snapshot.transactions:
        if txn.service_id not in known_services:
            raise ValueError(f"transaction {txn.id}: unknown serviceId {txn.service_id}")

    return {
        "accounts": [
            {
                "id": a.id,
                "email": a.email,
                "balance": a.balance,
                "withdraw_balance": a.withdraw_balance,
                "total_replenished": a.total_replenished,
                "bonus_balance": a.bonus_balance,
                "bonus_state": a.bonus_state,
            }
            for a in snapshot.accounts
        ],
        "services": [
            {
                "id": s.id,
                "owner_id": s.owner_id,
                "name": s.name,
                "payment_term": s.payment_term,
                "auto_prolong": int(s.auto_prolong),
                "created_at": _as_iso(s.created_at),
                "expires_at": _as_iso(s.expires_at),
                "status": s.status,
                "price": s.price,
            }
            for s in snapshot.services
        ],
        "transactions": [
            {
                "id": t.id,
                "service_id": t.service_id,
                "amount": t.amount,
                "status": t.status,
                "performed_at": _as_iso(t.performed_at) if t.performed_at else None,
                "created_at": _as_iso(t.created_at),
                "type": t.type,
            }
            for t in snapshot.transactions
        ],
    }


def _insert_snapshot(conn: sqlite3.Connection, data: dict[str, list[dict[str, Any]]]) -> None:
    conn.executemany(
        """
        INSERT INTO accounts (id, email, balance, withdraw_balance, total_replenished, bonus_balance, bonus_state)
        VALUES (:id, :email, :balance, :withdraw_balance, :total_replenished, :bonus_balance, :bonus_state)
        """,
        data["accounts"],
    )
    conn.executemany(
        """
        INSERT INTO services (id, owner_id, name, payment_term, auto_prolong, created_at, expires_at, status, price)
        VALUES (:id, :owner_id, :name, :payment_term, :auto_prolong, :created_at, :expires_at, :status, :price)
        """,
        data["services"],
    )
    conn.executemany(
        """
        INSERT INTO transactions (id, service_id, amount, status, performed_at, created_at, type)
        VALUES (:id, :service_id, :amount, :status, :performed_at, :created_at, :type)
        """,
        data["transactions"],
    )


def replace_snapshot(conn: sqlite3.Connection, snapshot: SnapshotIn) -> dict[str, int]:
    data = validate_snapshot(snapshot)
    conn.execute("DELETE FROM customer_scores")
    conn.execute("DELETE FROM score_runs")
    conn.execute("DELETE FROM transactions")
    conn.execute("DELETE FROM services")
    conn.execute("DELETE FROM accounts")
    _insert_snapshot(conn, data)
    return {key: len(value) for key, value in data.items()}


def load_snapshot_file(path: Path) -> SnapshotIn:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return SnapshotIn.model_validate(payload)


def ensure_seed(conn: sqlite3.Connection, path: Path, enabled: bool = True) -> bool:
    if not enabled:
        return False
    count = conn.execute("SELECT count(*) AS n FROM accounts").fetchone()["n"]
    initialized = conn.execute("SELECT 1 FROM score_runs LIMIT 1").fetchone()
    if count or initialized:
        return False
    if not path.exists():
        raise FileNotFoundError(f"seed not found: {path}")
    replace_snapshot(conn, load_snapshot_file(path))
    return True


def get_settings(conn: sqlite3.Connection) -> tuple[dict[str, Any], int, str]:
    row = conn.execute("SELECT payload, version, updated_at FROM settings WHERE id = 1").fetchone()
    if row is None:
        payload = default_settings()
        version = 1
        updated = datetime.now(timezone.utc)
        conn.execute(
            "INSERT INTO settings (id, payload, version, updated_at) VALUES (1, ?, ?, ?)",
            (json.dumps(payload, ensure_ascii=False), version, _as_iso(updated)),
        )
        return payload, version, _as_iso(updated)
    return json.loads(row["payload"]), int(row["version"]), row["updated_at"]


def save_settings(conn: sqlite3.Connection, payload: dict[str, Any], version: int) -> str:
    updated = _as_iso(datetime.now(timezone.utc))
    conn.execute(
        "UPDATE settings SET payload = ?, version = ?, updated_at = ? WHERE id = 1",
        (json.dumps(payload, ensure_ascii=False), version, updated),
    )
    return updated
