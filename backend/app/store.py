from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from .schemas import detail_response
from .scoring import compute, iso_z, parse_iso


def _rows(conn: sqlite3.Connection, sql: str) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute(sql).fetchall()]


def recompute(
    conn: sqlite3.Connection,
    settings: dict[str, Any],
    settings_version: int,
    as_of_raw: str | None,
) -> dict[str, Any]:
    as_of = parse_iso(as_of_raw) if as_of_raw else datetime.now(timezone.utc)
    accounts = _rows(conn, "SELECT * FROM accounts ORDER BY id")
    services = _rows(conn, "SELECT * FROM services ORDER BY id")
    transactions = _rows(conn, "SELECT * FROM transactions ORDER BY id")
    result = compute(accounts, services, transactions, settings, as_of, datetime.now(timezone.utc))
    summary = result["summary"]

    # Fail before any publication on non-finite JSON or an unrepresentable SQL value.
    json.dumps(result, ensure_ascii=False, allow_nan=False)
    for customer in result["customers"]:
        detail_response(customer)
        for key in ("expectedLossCents", "amountAtRiskCents"):
            if not 0 <= customer["money"][key] <= 2**63 - 1:
                raise ValueError(f"result {key} is outside SQLite INTEGER range")
    run = conn.execute(
        "INSERT INTO score_runs (as_of, created_at, settings_version, summary) VALUES (?, ?, ?, ?)",
        (summary["asOf"], summary["updatedAt"], settings_version, json.dumps(summary, ensure_ascii=False)),
    )
    run_id = int(run.lastrowid)
    for customer in result["customers"]:
        conn.execute(
            """
            INSERT INTO customer_scores
            (run_id, account_id, score, level, confidence, drivers, detail,
             expected_loss, amount_at_risk, coverage, services_at_risk,
             is_estimated, unknown_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                customer["id"],
                customer["score"],
                customer["level"],
                customer["confidence"],
                json.dumps(customer["drivers"], ensure_ascii=False),
                json.dumps(customer, ensure_ascii=False),
                customer["money"]["expectedLossCents"],
                customer["money"]["amountAtRiskCents"],
                customer["money"]["coverage"],
                sum(1 for s in customer["services"] if s["score"] >= settings["thresholds"]["medium"]),
                1 if customer["isEstimated"] else 0,
                customer["unknownReason"],
            ),
        )
    # Keep the table small on a hackathon demo DB.
    conn.execute(
        "DELETE FROM score_runs WHERE id NOT IN (SELECT id FROM score_runs ORDER BY id DESC LIMIT 20)"
    )
    return summary


def latest_run(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT id, as_of, created_at, settings_version, summary FROM score_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()


def latest_summary(conn: sqlite3.Connection) -> dict[str, Any] | None:
    row = latest_run(conn)
    return json.loads(row["summary"]) if row else None


def latest_customers(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    run = latest_run(conn)
    if run is None:
        return []
    rows = conn.execute(
        """
        SELECT cs.detail
        FROM customer_scores cs
        WHERE cs.run_id = ?
        ORDER BY cs.account_id
        """,
        (run["id"],),
    ).fetchall()
    return [json.loads(row["detail"]) for row in rows]


def customer_detail(conn: sqlite3.Connection, account_id: int) -> dict[str, Any] | None:
    run = latest_run(conn)
    if run is None:
        return None
    row = conn.execute(
        "SELECT detail FROM customer_scores WHERE run_id = ? AND account_id = ?",
        (run["id"], account_id),
    ).fetchone()
    return json.loads(row["detail"]) if row else None


def run_metadata(conn: sqlite3.Connection) -> dict[str, Any] | None:
    run = latest_run(conn)
    if run is None:
        return None
    return {
        "id": int(run["id"]),
        "asOf": run["as_of"],
        "createdAt": run["created_at"],
        "settingsVersion": int(run["settings_version"]),
    }


def to_iso_now() -> str:
    return iso_z(datetime.now(timezone.utc))
