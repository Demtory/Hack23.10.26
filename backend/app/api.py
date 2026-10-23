from __future__ import annotations

import asyncio
import copy
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import PlainTextResponse, StreamingResponse
from fastapi.security import APIKeyCookie

from .config import Config
from .db import connect
from .schemas import LoginIn, SettingsPatch, SnapshotIn
from .scoring import FEATURES_META
from .security import (
    SESSION_COOKIE,
    authenticate,
    create_session,
    delete_session,
    get_session_user,
)
from .seed import get_settings, replace_snapshot, save_settings
from .store import (
    customer_detail,
    latest_customers,
    latest_run,
    latest_summary,
    recompute,
)

router = APIRouter(prefix="/api/v1")
cookie_scheme = APIKeyCookie(name=SESSION_COOKIE, auto_error=False)


def get_config(request: Request) -> Config:
    return request.app.state.config


def get_db(request: Request):
    conn = connect(request.app.state.config.db_path)
    try:
        yield conn
    finally:
        conn.close()


def require_user(
    request: Request,
    cookie_token: str | None = Depends(cookie_scheme),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict[str, Any]:
    token = cookie_token or request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="authentication required")
    user = get_session_user(conn, token)
    if user is None:
        raise HTTPException(status_code=401, detail="session expired")
    return user


def euros(cents: int | float | None) -> float | None:
    if cents is None:
        return None
    return round(float(cents) / 100.0, 2)


def _ensure_summary(conn: sqlite3.Connection, config: Config) -> dict[str, Any]:
    summary = latest_summary(conn)
    if summary is not None:
        return summary
    settings, version, _ = get_settings(conn)
    return recompute(conn, settings, version, config.as_of)


def _summary_api(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "countsByLevel": summary["countsByLevel"],
        "totalCustomers": summary["totalCustomers"],
        "scoredCustomers": summary["scoredCustomers"],
        "servicesAtRisk": summary["servicesAtRisk"],
        "expectedLoss": euros(summary["expectedLossCents"]),
        "amountAtRisk": euros(summary["amountAtRiskCents"]),
        "coverage": summary["coverage"],
        "aggregateCoverage": summary.get("aggregateCoverage", summary["coverage"]),
        "underfundedCustomers": summary.get("underfundedCustomers", 0),
        "avgScore": summary["avgScore"],
        "asOf": summary["asOf"],
        "updatedAt": summary["updatedAt"],
        "currency": summary.get("currency", "EUR"),
    }


def _settings_api(payload: dict[str, Any], version: int, updated_at: str) -> dict[str, Any]:
    return {
        **payload,
        "features": FEATURES_META,
        "version": version,
        "updatedAt": updated_at,
    }


def _detail_api(customer: dict[str, Any]) -> dict[str, Any]:
    services = []
    for service in customer["services"]:
        services.append(
            {
                **{k: v for k, v in service.items() if k != "priceCents"},
                "price": euros(service["priceCents"]),
            }
        )
    money = customer["money"]
    return {
        "id": customer["id"],
        "email": customer["email"],
        "balance": euros(customer["balanceCents"]),
        "withdrawBalance": euros(customer["withdrawCents"]),
        "bonusBalance": euros(customer["bonusCents"]),
        "bonusState": customer["bonusState"],
        "totalReplenished": euros(customer["totalReplenishedCents"]),
        "score": customer["score"],
        "level": customer["level"],
        "confidence": customer["confidence"],
        "summary": customer["summaryText"],
        "drivers": customer["drivers"],
        "services": services,
        "money": {
            "amountAtRisk": euros(money["amountAtRiskCents"]),
            "expectedLoss": euros(money["expectedLossCents"]),
            "coveredLoss": euros(money["coveredLossCents"]),
            "coverage": money["coverage"],
            "mitigation": money["mitigation"],
        },
        "unknownReason": customer["unknownReason"],
        "isEstimated": customer["isEstimated"],
    }


# --------------------------------------------------------------------------- auth


@router.post("/auth/login")
def login(
    body: LoginIn,
    response: Response,
    config: Config = Depends(get_config),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict[str, Any]:
    user_id = authenticate(conn, body.email, body.password)
    if user_id is None:
        raise HTTPException(status_code=401, detail="invalid email or password")
    token = create_session(conn, user_id, config.session_hours)
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=config.session_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=config.cookie_secure,
        path="/",
    )
    return {"id": user_id, "email": body.email}


@router.get("/auth/me")
def me(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    return user


@router.post("/auth/logout")
def logout(
    request: Request,
    response: Response,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict[str, bool]:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        delete_session(conn, token)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


# ----------------------------------------------------------------------- customers


CUSTOMER_SORTS = {
    "id": "a.id",
    "email": "lower(a.email)",
    "balance": "a.balance",
    "totalReplenished": "a.total_replenished",
    "score": "cs.score",
    "expectedLoss": "cs.expected_loss",
}


@router.get("/customers")
def customers(
    sort: str = Query("score"),
    order: str | None = Query(None),
    level: str | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(25, ge=1, le=100),
    config: Config = Depends(get_config),
    conn: sqlite3.Connection = Depends(get_db),
    _user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    if sort not in CUSTOMER_SORTS:
        raise HTTPException(status_code=422, detail=f"unsupported sort: {sort}")
    if level is not None and level not in {"high", "medium", "low", "unknown"}:
        raise HTTPException(status_code=422, detail=f"unsupported level: {level}")
    direction = (order or ("desc" if sort in {"score", "expectedLoss"} else "asc")).lower()
    if direction not in {"asc", "desc"}:
        raise HTTPException(status_code=422, detail="order must be asc or desc")
    _ensure_summary(conn, config)
    run = latest_run(conn)
    assert run is not None

    where = ["cs.run_id = ?"]
    params: list[Any] = [run["id"]]
    if level:
        where.append("cs.level = ?")
        params.append(level)
    if q:
        where.append("lower(a.email) LIKE ?")
        params.append(f"%{q.lower()}%")
    where_sql = " AND ".join(where)

    total = conn.execute(
        f"SELECT count(*) AS n FROM customer_scores cs JOIN accounts a ON a.id = cs.account_id WHERE {where_sql}",
        params,
    ).fetchone()["n"]

    expression = CUSTOMER_SORTS[sort]
    if sort == "score":
        order_sql = f"CASE WHEN cs.score IS NULL THEN 1 ELSE 0 END ASC, cs.score {direction.upper()}"
    else:
        order_sql = f"{expression} {direction.upper()}"
    offset = (page - 1) * pageSize
    rows = conn.execute(
        f"""
        SELECT cs.account_id AS id, a.email, a.balance, a.total_replenished,
               cs.score, cs.level, cs.expected_loss, cs.amount_at_risk, cs.services_at_risk
        FROM customer_scores cs JOIN accounts a ON a.id = cs.account_id
        WHERE {where_sql}
        ORDER BY {order_sql}, a.id ASC
        LIMIT ? OFFSET ?
        """,
        [*params, pageSize, offset],
    ).fetchall()

    items = [
        {
            "id": int(row["id"]),
            "email": row["email"],
            "balance": euros(row["balance"]),
            "totalReplenished": euros(row["total_replenished"]),
            "score": row["score"],
            "level": row["level"],
            "expectedLoss": euros(row["expected_loss"]),
            "amountAtRisk": euros(row["amount_at_risk"]),
            "servicesAtRisk": int(row["services_at_risk"]),
        }
        for row in rows
    ]
    return {"items": items, "total": int(total), "page": page, "pageSize": pageSize}


@router.get("/customers/{account_id}")
def customer(
    account_id: int,
    config: Config = Depends(get_config),
    conn: sqlite3.Connection = Depends(get_db),
    _user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    _ensure_summary(conn, config)
    detail = customer_detail(conn, account_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="customer not found")
    return _detail_api(detail)


# ----------------------------------------------------------------------- analytics


@router.get("/analytics/summary")
def analytics_summary(
    config: Config = Depends(get_config),
    conn: sqlite3.Connection = Depends(get_db),
    _user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    return _summary_api(_ensure_summary(conn, config))


# --------------------------------------------------------------------------- model


def _validate_settings(payload: dict[str, Any]) -> None:
    weights = payload.get("weights", {})
    known = {feature["code"] for feature in FEATURES_META}
    unknown = set(weights) - known
    if unknown:
        raise ValueError(f"unknown feature weights: {sorted(unknown)}")
    if any(float(value) < 0 for value in weights.values()):
        raise ValueError("weights must be >= 0")
    if sum(float(value) for value in weights.values()) <= 0:
        raise ValueError("weights sum must be > 0")
    medium = float(payload["thresholds"]["medium"])
    high = float(payload["thresholds"]["high"])
    if not 0 < medium < high < 100:
        raise ValueError("thresholds must satisfy 0 < medium < high < 100")
    probability = payload["probability"]
    if not 0 <= float(probability["floor"]) < float(probability["ceiling"]) <= 1:
        raise ValueError("probability floor/ceiling are invalid")
    if float(probability["steepness"]) <= 0:
        raise ValueError("probability steepness must be > 0")
    mitigation = float(payload["money"]["balanceMitigation"])
    if not 0 <= mitigation <= 1:
        raise ValueError("balanceMitigation must be in [0, 1]")
    for value in payload.get("statusFloors", {}).values():
        if not 0 <= float(value) <= 100:
            raise ValueError("status floors must be in [0, 100]")


@router.get("/model/settings")
def read_settings(
    conn: sqlite3.Connection = Depends(get_db),
    _user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    payload, version, updated_at = get_settings(conn)
    return _settings_api(payload, version, updated_at)


@router.patch("/model/settings")
def patch_settings(
    patch: SettingsPatch,
    config: Config = Depends(get_config),
    conn: sqlite3.Connection = Depends(get_db),
    _user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    current, version, _ = get_settings(conn)
    merged = copy.deepcopy(current)
    delta = patch.model_dump(by_alias=True, exclude_none=True)
    for key in ("weights", "statusFloors"):
        if key in delta and delta[key] is not None:
            merged.setdefault(key, {}).update(delta[key])
    for key in ("thresholds", "probability", "money"):
        if key in delta and delta[key] is not None:
            merged.setdefault(key, {}).update(delta[key])
    if "recomputeIntervalSec" in delta:
        merged["recomputeIntervalSec"] = delta["recomputeIntervalSec"]
    try:
        _validate_settings(merged)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    new_version = version + 1
    updated_at = save_settings(conn, merged, new_version)
    summary = recompute(conn, merged, new_version, config.as_of)
    return {
        "settings": _settings_api(merged, new_version, updated_at),
        "summary": _summary_api(summary),
    }


# -------------------------------------------------------------------------- source


def _source_snapshot(conn: sqlite3.Connection) -> dict[str, Any]:
    accounts = conn.execute(
        "SELECT id, email, balance, withdraw_balance, total_replenished, bonus_balance, bonus_state FROM accounts ORDER BY id"
    ).fetchall()
    services = conn.execute(
        "SELECT id, name, owner_id, payment_term, auto_prolong, created_at, expires_at, status, price FROM services ORDER BY id"
    ).fetchall()
    transactions = conn.execute(
        "SELECT id, amount, status, performed_at, created_at, type, service_id FROM transactions ORDER BY id"
    ).fetchall()
    return {
        "accounts": [
            {
                "id": int(row["id"]),
                "email": row["email"],
                "balance": int(row["balance"]),
                "withdrawBalance": int(row["withdraw_balance"]),
                "totalReplenished": int(row["total_replenished"]),
                "bonusBalance": int(row["bonus_balance"]),
                "bonusState": row["bonus_state"],
            }
            for row in accounts
        ],
        "services": [
            {
                "id": int(row["id"]),
                "name": row["name"],
                "ownerId": int(row["owner_id"]),
                "paymentTerm": row["payment_term"],
                "autoProlong": bool(row["auto_prolong"]),
                "createdAt": row["created_at"],
                "expiresAt": row["expires_at"],
                "status": row["status"],
                "price": int(row["price"]),
            }
            for row in services
        ],
        "transactions": [
            {
                "id": int(row["id"]),
                "amount": int(row["amount"]),
                "status": row["status"],
                "performedAt": row["performed_at"],
                "createdAt": row["created_at"],
                "type": row["type"],
                "serviceId": int(row["service_id"]),
            }
            for row in transactions
        ],
    }


@router.get("/source/snapshot")
def read_snapshot(
    conn: sqlite3.Connection = Depends(get_db),
    _user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    return _source_snapshot(conn)


@router.put("/source/snapshot")
def put_snapshot(
    body: SnapshotIn,
    config: Config = Depends(get_config),
    conn: sqlite3.Connection = Depends(get_db),
    _user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    try:
        counts = replace_snapshot(conn, body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    settings, version, _ = get_settings(conn)
    summary = recompute(conn, settings, version, config.as_of)
    return {"counts": counts, "summary": _summary_api(summary)}


# ------------------------------------------------------------------------- metrics


@router.get("/events")
async def events(request: Request) -> StreamingResponse:
    config: Config = request.app.state.config

    async def stream():
        last_id: int | None = None
        tick = 0
        while True:
            if await request.is_disconnected():
                break
            conn = connect(config.db_path)
            try:
                row = conn.execute("SELECT id, created_at FROM score_runs ORDER BY id DESC LIMIT 1").fetchone()
            finally:
                conn.close()
            current = int(row["id"]) if row else 0
            if current != last_id:
                last_id = current
                data = json.dumps(
                    {"runId": current, "updatedAt": row["created_at"] if row else None},
                    ensure_ascii=False,
                )
                yield f"event: scores.updated\ndata: {data}\n\n"
            elif tick % 10 == 0:
                yield ": keep-alive\n\n"
            tick += 1
            await asyncio.sleep(1.5)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _metrics_text(summary: dict[str, Any]) -> str:
    counts = summary["countsByLevel"]
    lines = [
        "# HELP churn_customers_total Клиенты по уровням риска",
        "# TYPE churn_customers_total gauge",
        f'churn_customers_total{{level="high"}} {counts["high"]}',
        f'churn_customers_total{{level="medium"}} {counts["medium"]}',
        f'churn_customers_total{{level="low"}} {counts["low"]}',
        f'churn_customers_total{{level="unknown"}} {counts["unknown"]}',
        "",
        "# HELP churn_expected_loss_eur Ожидаемые потери при ближайшем продлении, EUR",
        "# TYPE churn_expected_loss_eur gauge",
        f"churn_expected_loss_eur {summary['expectedLossCents'] / 100:.2f}",
        "",
        "# HELP churn_amount_at_risk_eur Сумма платежей под риском, EUR",
        "# TYPE churn_amount_at_risk_eur gauge",
        f"churn_amount_at_risk_eur {summary['amountAtRiskCents'] / 100:.2f}",
        "",
        "# HELP churn_services_at_risk Услуги под риском",
        "# TYPE churn_services_at_risk gauge",
        f"churn_services_at_risk {summary['servicesAtRisk']}",
        "",
        "# HELP churn_risk_score_avg Средний score клиентов с оценкой",
        "# TYPE churn_risk_score_avg gauge",
        f"churn_risk_score_avg {summary['avgScore'] if summary['avgScore'] is not None else 'NaN'}",
        "",
        "# HELP churn_as_of_timestamp_seconds Время снимка данных",
        "# TYPE churn_as_of_timestamp_seconds gauge",
        f"churn_as_of_timestamp_seconds {int(datetime.fromisoformat(summary['asOf'].replace('Z', '+00:00')).timestamp())}",
        "",
        "# HELP churn_last_recompute_timestamp_seconds Время последнего пересчёта",
        "# TYPE churn_last_recompute_timestamp_seconds gauge",
        f"churn_last_recompute_timestamp_seconds {int(datetime.fromisoformat(summary['updatedAt'].replace('Z', '+00:00')).timestamp())}",
        "",
    ]
    return "\n".join(lines)


@router.get("/metrics", include_in_schema=False)
def metrics(
    config: Config = Depends(get_config),
    conn: sqlite3.Connection = Depends(get_db),
) -> PlainTextResponse:
    summary = _ensure_summary(conn, config)
    return PlainTextResponse(_metrics_text(summary), media_type="text/plain; version=0.0.4; charset=utf-8")
