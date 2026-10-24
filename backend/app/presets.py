"""Готовые наборы весов: встроенные и пользовательские.

Встроенные живут в коде (их нельзя удалить), пользовательские — в таблице
`weight_presets`. Пресет меняет только веса: пороги и денежные правила
остаются в своих блоках и сохраняются отдельно.
"""
from __future__ import annotations

import json
import math
import sqlite3
from typing import Any

from .scoring import FEATURES_META

FEATURE_CODES = {feature["code"] for feature in FEATURES_META}
NAME_LIMIT = 40
MAX_CUSTOM_PRESETS = 20

BUILTIN_PRESETS: list[dict[str, Any]] = [
    {
        "id": "balanced",
        "name": "Сбалансированный",
        "description": "Стартовые веса: срок и деньги важнее остального",
        "weights": {
            "expiry_pressure": 0.40, "funds_gap": 0.25, "autorenew_off": 0.10,
            "status_pressure": 0.10, "payment_history": 0.10, "commitment": 0.05,
            "auto_off_share": 0.00,
        },
    },
    {
        "id": "money",
        "name": "Деньги важнее",
        "description": "Для кампании по пополнениям: сильнее реагирует на нехватку средств",
        "weights": {
            "expiry_pressure": 0.30, "funds_gap": 0.45, "autorenew_off": 0.08,
            "status_pressure": 0.07, "payment_history": 0.08, "commitment": 0.02,
            "auto_off_share": 0.00,
        },
    },
    {
        "id": "urgency",
        "name": "Срочность важнее",
        "description": "Для обзвона по срокам: на первом месте услуги, которые истекают",
        "weights": {
            "expiry_pressure": 0.55, "funds_gap": 0.18, "autorenew_off": 0.10,
            "status_pressure": 0.08, "payment_history": 0.07, "commitment": 0.02,
            "auto_off_share": 0.00,
        },
    },
    {
        "id": "status",
        "name": "Статус и оплата",
        "description": "Для работы с блокировками и неоплаченными счетами",
        "weights": {
            "expiry_pressure": 0.25, "funds_gap": 0.15, "autorenew_off": 0.05,
            "status_pressure": 0.30, "payment_history": 0.20, "commitment": 0.05,
            "auto_off_share": 0.00,
        },
    },
]


def _normalize_weights(raw: dict[str, Any]) -> dict[str, float]:
    if not isinstance(raw, dict):
        raise ValueError("weights must be an object")
    unknown = set(raw) - FEATURE_CODES
    if unknown:
        raise ValueError(f"unknown feature weights: {sorted(unknown)}")
    result: dict[str, float] = {}
    for code in FEATURE_CODES:
        value = raw.get(code, 0.0)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("weights must be numbers")
        number = float(value)
        if not math.isfinite(number) or number < 0 or number > 1:
            raise ValueError("weights must be finite numbers between 0 and 1")
        result[code] = round(number, 4)
    if not any(result.values()):
        raise ValueError("at least one weight must be greater than zero")
    return result


def _clean_name(raw: Any) -> str:
    if not isinstance(raw, str):
        raise ValueError("name must be a string")
    name = " ".join(raw.split())
    if not name or len(name) > NAME_LIMIT:
        raise ValueError(f"name must be 1..{NAME_LIMIT} characters")
    return name


def list_presets(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    presets = [
        {"id": preset["id"], "name": preset["name"], "builtin": True,
         "description": preset["description"], "weights": dict(preset["weights"])}
        for preset in BUILTIN_PRESETS
    ]
    rows = conn.execute(
        "SELECT id, name, weights FROM weight_presets ORDER BY name COLLATE NOCASE"
    ).fetchall()
    for row in rows:
        stored = json.loads(row["weights"])
        weights = {code: float(stored.get(code, 0.0)) for code in FEATURE_CODES}
        presets.append(
            {"id": f"custom-{row['id']}", "name": row["name"], "builtin": False,
             "description": "Пользовательский набор весов", "weights": weights}
        )
    return presets


def create_preset(conn: sqlite3.Connection, name: Any, weights: Any, now: str) -> dict[str, Any]:
    clean_name = _clean_name(name)
    normalized = _normalize_weights(weights)
    if any(preset["name"].casefold() == clean_name.casefold() for preset in BUILTIN_PRESETS):
        raise LookupError("name is reserved by a built-in preset")
    existing_names = [row["name"] for row in conn.execute("SELECT name FROM weight_presets")]
    if any(name.casefold() == clean_name.casefold() for name in existing_names):
        raise LookupError("preset with this name already exists")
    total = conn.execute("SELECT COUNT(*) FROM weight_presets").fetchone()[0]
    if total >= MAX_CUSTOM_PRESETS:
        raise ValueError(f"at most {MAX_CUSTOM_PRESETS} custom presets")
    cursor = conn.execute(
        "INSERT INTO weight_presets (name, weights, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (clean_name, json.dumps(normalized, ensure_ascii=False), now, now),
    )
    conn.commit()
    return {"id": f"custom-{cursor.lastrowid}", "name": clean_name, "builtin": False,
            "description": "Пользовательский набор весов", "weights": normalized}


def delete_preset(conn: sqlite3.Connection, preset_id: str) -> bool:
    if not preset_id.startswith("custom-"):
        return False
    try:
        number = int(preset_id.split("-", 1)[1])
    except (IndexError, ValueError):
        return False
    cursor = conn.execute("DELETE FROM weight_presets WHERE id = ?", (number,))
    conn.commit()
    return cursor.rowcount > 0
