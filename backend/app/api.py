from __future__ import annotations

import asyncio
import copy
import csv
import io
import secrets
import unicodedata
import json
import math
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse, StreamingResponse
from fastapi.security import APIKeyCookie, HTTPBearer, HTTPAuthorizationCredentials

from . import oidc
from .config import Config
from .db import connect, transaction, read_snapshot as read_transaction
from .schemas import CustomerDetailOut, CustomerViewOut, CustomerPageOut, SummaryOut, SummaryBase, LoginIn, SettingsPatch, SnapshotIn, ForecastOut, detail_response
from .forecast import build_forecast
from .scoring import FEATURES_META
from .security import (
    SESSION_COOKIE,
    authenticate,
    create_session,
    delete_session,
    ensure_oidc_user,
    get_session_user,
    iso_z,
    utcnow,
)
from .seed import get_settings, replace_snapshot, save_settings, validate_snapshot
from .store import (
    customer_detail,
    latest_customers,
    latest_details,
    latest_run,
    latest_summary,
    recompute,
)

router = APIRouter(prefix="/api/v1")
cookie_scheme = APIKeyCookie(name=SESSION_COOKIE, auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def get_config(request: Request) -> Config:
    return request.app.state.config


def get_db(request: Request):
    conn = connect(request.app.state.config.db_path)
    try:
        yield conn
    finally:
        conn.close()


def session_token(
    cookie_token: str | None = Depends(cookie_scheme),
    bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str | None:
    # A nonempty cookie wins, including when it is expired or invalid.
    return cookie_token or (bearer.credentials if bearer else None)


def require_user(
    token: str | None = Depends(session_token),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict[str, Any]:
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
    if summary is not None and "calculation" in summary and "thresholds" in summary:
        return summary
    with transaction(conn):
        summary = latest_summary(conn)
        if summary is None or "calculation" not in summary or "thresholds" not in summary:
            settings, version, _ = get_settings(conn)
            _validate_settings(settings)
            summary = recompute(conn, settings, version, config.as_of)
        return summary


def _summary_api(summary: dict[str, Any], include_context: bool = True) -> dict[str, Any]:
    payload = {
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
    if include_context:
        payload['calculation'] = summary['calculation']
    model = SummaryOut if include_context else SummaryBase
    return model.model_validate(payload).model_dump(by_alias=True)


def _settings_api(payload: dict[str, Any], version: int, updated_at: str) -> dict[str, Any]:
    return {
        **payload,
        "features": FEATURES_META,
        "version": version,
        "updatedAt": updated_at,
    }


def _detail_api(customer: dict[str, Any]) -> dict[str, Any]:
    return detail_response(customer)


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
    return {"id": user_id, "email": body.email, "token": token, "accessToken": token}


@router.get("/auth/me")
def me(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    return user


@router.post("/auth/logout", openapi_extra={"security": [{}]})
def logout(
    response: Response,
    token: str | None = Depends(session_token),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict[str, bool]:
    if token:
        delete_session(conn, token)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}



# ------------------------------------------------------------------------ oidc


OIDC_CALLBACK_PATH = "/api/v1/auth/oidc/callback"
OIDC_FLOW_TTL = timedelta(minutes=10)


def _oidc_redirect_uri(request: Request, config: Config) -> str:
    if config.oidc_redirect_uri:
        return config.oidc_redirect_uri
    return str(request.base_url).rstrip("/") + OIDC_CALLBACK_PATH


def _login_redirect(code: str) -> RedirectResponse:
    return RedirectResponse(f"/#/login?sso_error={code}", status_code=303,
                            headers={"Cache-Control": "no-store"})


def _set_session_cookie(response: Response, token: str, config: Config) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=config.session_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=config.cookie_secure,
        path="/",
    )


@router.get("/auth/oidc/config", openapi_extra={"security": []})
def oidc_config(config: Config = Depends(get_config)) -> dict[str, Any]:
    return {"enabled": config.oidc_enabled, "providerName": config.oidc_provider_name}


@router.get("/auth/oidc/start", openapi_extra={"security": []})
def oidc_start(
    request: Request,
    config: Config = Depends(get_config),
    conn: sqlite3.Connection = Depends(get_db),
) -> RedirectResponse:
    if not config.oidc_enabled:
        raise HTTPException(status_code=404, detail="oidc is not configured")
    try:
        discovery = oidc.discover(config.oidc_issuer, config.oidc_internal_base)
    except oidc.OIDCError:
        return _login_redirect("provider_unavailable")

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    verifier, challenge = oidc.make_pkce_pair()
    conn.execute("DELETE FROM oidc_flows WHERE created_at < ?", (iso_z(utcnow() - timedelta(hours=1)),))
    conn.execute(
        "INSERT INTO oidc_flows (state, nonce, code_verifier, redirect_to, created_at) VALUES (?, ?, ?, ?, ?)",
        (state, nonce, verifier, "/#/", iso_z(utcnow())),
    )
    conn.commit()
    url = oidc.authorize_url(
        discovery, config.oidc_client_id, _oidc_redirect_uri(request, config),
        config.oidc_scopes, state, nonce, challenge,
    )
    return RedirectResponse(url, status_code=303, headers={"Cache-Control": "no-store"})


@router.get("/auth/oidc/callback", openapi_extra={"security": []})
def oidc_callback(
    request: Request,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    config: Config = Depends(get_config),
    conn: sqlite3.Connection = Depends(get_db),
) -> RedirectResponse:
    if error:
        return _login_redirect("access_denied")
    if not code or not state:
        return _login_redirect("state_invalid")

    flow = conn.execute("SELECT * FROM oidc_flows WHERE state = ?", (state,)).fetchone()
    if flow is not None:
        conn.execute("DELETE FROM oidc_flows WHERE state = ?", (state,))
        conn.commit()
    if flow is None:
        return _login_redirect("state_invalid")
    created = datetime.fromisoformat(flow["created_at"].replace("Z", "+00:00"))
    if utcnow() - created > OIDC_FLOW_TTL:
        return _login_redirect("state_invalid")

    try:
        discovery = oidc.discover(config.oidc_issuer, config.oidc_internal_base)
        tokens = oidc.exchange_code(
            discovery, config.oidc_issuer, config.oidc_internal_base,
            config.oidc_client_id, config.oidc_client_secret,
            code, _oidc_redirect_uri(request, config), flow["code_verifier"],
        )
    except oidc.OIDCError as exc:
        return _login_redirect(exc.code)

    try:
        claims = oidc.validate_id_token(
            tokens["id_token"], discovery, config.oidc_issuer, config.oidc_client_id,
            flow["nonce"], config.oidc_internal_base,
        )
    except oidc.OIDCError as exc:
        return _login_redirect(exc.code)

    email = (claims.get("email") or "").strip()
    if not email or claims.get("email_verified") is False:
        return _login_redirect("email_unverified")

    user_id = ensure_oidc_user(conn, email, claims["sub"])
    token = create_session(conn, user_id, config.session_hours)
    response = RedirectResponse(flow["redirect_to"] or "/#/", status_code=303,
                                headers={"Cache-Control": "no-store"})
    _set_session_cookie(response, token, config)
    return response

# ----------------------------------------------------------------------- customers


CUSTOMER_SORTS = {
    "id": "a.id",
    "email": "lower(a.email)",
    "balance": "a.balance",
    "totalReplenished": "a.total_replenished",
    "score": "cs.score",
    "expectedLoss": "cs.expected_loss",
}


def _list_item(row: sqlite3.Row) -> dict[str, Any]:
    return {
        'id': int(row['id']), 'email': row['email'], 'balance': euros(row['balance']),
        'totalReplenished': euros(row['total_replenished']), 'score': row['score'],
        'level': row['level'], 'expectedLoss': euros(row['expected_loss']),
        'amountAtRisk': euros(row['amount_at_risk']), 'servicesAtRisk': int(row['services_at_risk']),
    }


def _selection(run, level, q, urgency):
    if level is not None and level not in {'high', 'medium', 'low', 'unknown'}:
        raise HTTPException(422, detail='unsupported level')
    if urgency not in {'all', 'expired', '48h', '7d'}:
        raise HTTPException(422, detail='unsupported urgency')
    where, params = ['cs.run_id = ?'], [run['id']]
    if level:
        where.append('cs.level = ?'); params.append(level)
    if q:
        query = q.strip()
        like = f'%{query.lower()}%'
        if query.isdigit():
            # Число ищет и по email, и по точному ID клиента.
            where.append('(lower(a.email) LIKE ? OR a.id = ?)'); params.extend([like, int(query)])
        else:
            where.append('lower(a.email) LIKE ?'); params.append(like)
    if urgency != 'all':
        as_of = datetime.fromisoformat(json.loads(run['summary'])['asOf'].replace('Z', '+00:00'))
        iso = lambda dt: dt.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        interval = 's.expires_at <= ?' if urgency == 'expired' else 's.expires_at > ? AND s.expires_at <= ?'
        params.append(iso(as_of))
        if urgency != 'expired': params.append(iso(as_of + timedelta(hours=48 if urgency == '48h' else 168)))
        where.append("EXISTS (SELECT 1 FROM services s WHERE s.owner_id=a.id AND s.status IN ('active','suspended','prolong_wait') AND " + interval + ')')
    return 'FROM customer_scores cs JOIN accounts a ON a.id=cs.account_id WHERE ' + ' AND '.join(where), params


def _order(sort, order):
    if sort not in CUSTOMER_SORTS: raise HTTPException(422, detail='unsupported sort')
    direction = (order or ('desc' if sort in {'score', 'expectedLoss'} else 'asc')).lower()
    if direction not in {'asc', 'desc'}: raise HTTPException(422, detail='unsupported order')
    expression = (f'CASE WHEN cs.score IS NULL THEN 1 ELSE 0 END ASC, cs.score {direction.upper()}'
                  if sort == 'score' else f'{CUSTOMER_SORTS[sort]} {direction.upper()}')
    return expression + ', a.id ASC', direction


CUSTOMER_COLUMNS = ('SELECT a.id, a.email, a.balance, a.total_replenished, '
                    'cs.score, cs.level, cs.expected_loss, cs.amount_at_risk, cs.services_at_risk ')


@router.get('/customers', response_model=CustomerPageOut)
def customers(
    sort: str = Query('score'), order: str | None = Query(None),
    level: str | None = Query(None), q: str | None = Query(None), urgency: str = Query('all'),
    page: int = Query(1, ge=1), pageSize: int = Query(25, ge=1, le=100),
    config: Config = Depends(get_config), conn: sqlite3.Connection = Depends(get_db),
    _user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    order_sql, _ = _order(sort, order)
    _ensure_summary(conn, config)
    with read_transaction(conn):
        run = latest_run(conn)
        assert run is not None
        summary = json.loads(run['summary'])
        source, params = _selection(run, level, q, urgency)
        total = conn.execute('SELECT count(*) AS n ' + source, params).fetchone()['n']
        rows = conn.execute(CUSTOMER_COLUMNS + source + f' ORDER BY {order_sql} LIMIT ? OFFSET ?',
                            [*params, pageSize, (page-1)*pageSize]).fetchall()
        top = conn.execute(CUSTOMER_COLUMNS + source + ' ORDER BY cs.expected_loss DESC, a.id ASC LIMIT 5', params).fetchall()
        return CustomerPageOut.model_validate({
            'items': [_list_item(row) for row in rows], 'total': total, 'page': page, 'pageSize': pageSize,
            'topLosses': [_list_item(row) for row in top], 'summary': _summary_api(summary, False),
            'calculation': summary['calculation'],
        }).model_dump(by_alias=True)


def _csv_text(value: str) -> str:
    normalized = unicodedata.normalize('NFKC', value)
    leading_control = bool(value) and unicodedata.category(value[0]) in {'Cc', 'Cf'}
    probe = normalized.lstrip()
    while probe and unicodedata.category(probe[0]) in {'Cc', 'Cf'}:
        probe = probe[1:].lstrip()
    return 'text:' + value if leading_control or value.startswith('text:') or probe.startswith(('=', '+', '-', '@')) else value


def _decimal_cents(value: int) -> str:
    whole, fraction = divmod(abs(value), 100)
    return ('-' if value < 0 else '') + f'{whole}.{fraction:02d}'


@router.get('/customers/export.csv', response_class=Response, responses={
    200: {'content': {'text/csv': {}}, 'description': 'UTF-8 BOM CSV, all selected customers, exact EUR strings'},
    409: {'description': 'stale_calculation or empty_selection'},
    401: {'description': 'Authentication required'},
})
def export_customers(
    runId: int = Query(..., ge=1), sort: str = Query('score'), order: str | None = Query(None),
    level: str | None = Query(None), q: str | None = Query(None), urgency: str = Query('all'),
    config: Config = Depends(get_config), conn: sqlite3.Connection = Depends(get_db),
    _user: dict[str, Any] = Depends(require_user),
):
    order_sql, direction = _order(sort, order)
    _ensure_summary(conn, config)
    with read_transaction(conn):
        run = latest_run(conn)
        if run is None or run['id'] != runId:
            raise HTTPException(409, detail={'code': 'stale_calculation', 'message': 'Расчёт изменился. Обновите список и повторите экспорт.'})
        summary = json.loads(run['summary'])
        source, params = _selection(run, level, q, urgency)
        rows = conn.execute(CUSTOMER_COLUMNS + source + ' ORDER BY ' + order_sql, params).fetchall()
        if not rows: raise HTTPException(409, detail={'code': 'empty_selection', 'message': 'Нет клиентов для экспорта'})
        output = io.StringIO(newline='')
        writer = csv.writer(output, quoting=csv.QUOTE_ALL, lineterminator='\r\n')
        writer.writerow(['customer_id','email','balance_eur','total_replenished_eur','score','risk_level',
                         'expected_loss_eur','amount_at_risk_eur','services_at_risk','filter_q','filter_level',
                         'filter_urgency','sort','order','run_id','settings_version','as_of','calculated_at',
                         'source_generated_at','currency','csv_format_version'])
        for row in rows:
            writer.writerow([row['id'], _csv_text(row['email']), _decimal_cents(row['balance']),
                _decimal_cents(row['total_replenished']), '' if row['score'] is None else row['score'], row['level'],
                _decimal_cents(row['expected_loss']), _decimal_cents(row['amount_at_risk']), row['services_at_risk'],
                _csv_text(q or ''),level or '',urgency,sort,direction,run['id'],summary['calculation']['settingsVersion'],
                summary['asOf'],summary['updatedAt'],'','EUR',1])
        content = output.getvalue().encode('utf-8-sig')
    return Response(content, media_type='text/csv; charset=utf-8', headers={
        'Content-Disposition': f'attachment; filename="customers-run-{runId}.csv"', 'Cache-Control': 'no-store'})


@router.get("/customers/{id}", response_model=CustomerDetailOut, response_model_exclude_unset=True)
def customer(
    id: int,
    response: Response,
    config: Config = Depends(get_config),
    conn: sqlite3.Connection = Depends(get_db),
    _user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    _ensure_summary(conn, config)
    with read_transaction(conn):
        run = latest_run(conn)
        detail = customer_detail(conn, id)
        if detail is None:
            raise HTTPException(status_code=404, detail="customer not found")
        summary = json.loads(run['summary'])
        response.headers['X-Calculation-Run-Id'] = str(run['id'])
        response.headers['X-Calculation-Settings-Version'] = str(summary['calculation']['settingsVersion'])
        response.headers['X-Calculation-As-Of'] = summary['asOf']
        response.headers['X-Calculation-Updated-At'] = summary['updatedAt']
        return _detail_api(detail)


# ----------------------------------------------------------------------- analytics


@router.get("/analytics/summary", response_model=SummaryOut)
def analytics_summary(
    config: Config = Depends(get_config),
    conn: sqlite3.Connection = Depends(get_db),
    _user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    return _summary_api(_ensure_summary(conn, config))


_FORECAST_CACHE: dict[tuple[str, int, int, int], dict[str, Any]] = {}


@router.get("/analytics/forecast", response_model=ForecastOut)
def analytics_forecast(
    past_days: int = Query(30, ge=1, le=90, alias="pastDays"),
    horizon_days: int = Query(30, ge=1, le=90, alias="horizonDays"),
    config: Config = Depends(get_config),
    conn: sqlite3.Connection = Depends(get_db),
    _user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    """Факт истечений и прогноз непродлений по срокам оплаты."""
    summary = _ensure_summary(conn, config)
    run = latest_run(conn)
    cache_key = (str(config.db_path), int(run["id"]) if run else 0, past_days, horizon_days)
    cached = _FORECAST_CACHE.get(cache_key)
    if cached is not None:
        return cached
    with read_transaction(conn):
        settings, _version, _updated = get_settings(conn)
        details = latest_details(conn)
    as_of = datetime.fromisoformat(summary["asOf"].replace("Z", "+00:00"))
    data = build_forecast(details, as_of, settings, past_days, horizon_days)
    data["forecast"] = [
        {
            "date": point["date"],
            "services": point["services"],
            "expectedNonRenewals": point["expectedNonRenewals"],
            "expectedLoss": euros(point["expectedLossCents"]),
        }
        for point in data["forecast"]
    ]
    totals = data["totals"]
    totals["expectedLoss"] = euros(totals.pop("expectedLossCents"))
    if len(_FORECAST_CACHE) > 16:
        _FORECAST_CACHE.clear()
    _FORECAST_CACHE[cache_key] = data
    return data


# --------------------------------------------------------------------------- model


def _validate_settings(payload: dict[str, Any], known: set[str] | None = None) -> None:
    weights = payload.get("weights", {})
    if known is None:
        known = {feature["code"] for feature in FEATURES_META}
    unknown = set(weights) - known
    if unknown:
        raise ValueError(f"unknown feature weights: {sorted(unknown)}")
    SettingsPatch.model_validate(payload)
    if set(weights) != known:
        raise ValueError("weights must contain all existing feature keys")
    if any(not math.isfinite(float(value)) or float(value) < 0 for value in weights.values()):
        raise ValueError("weights must be >= 0")
    if not any(float(value) > 0 for value in weights.values()):
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
    try:
        with transaction(conn):
            current, version, _ = get_settings(conn)
            if patch.expected_version is not None and patch.expected_version != version:
                raise HTTPException(409, detail={'code':'settings_version_conflict',
                    'expectedVersion':patch.expected_version,'currentVersion':version,
                    'message':'Настройки изменены другим пользователем. Черновик сохранён.'})
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
            response = JSONResponse({
                "settings": _settings_api(merged, new_version, updated_at),
                "summary": _summary_api(summary),
            })
        return response
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Изменение не применено; сохранено прежнее состояние") from None


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
    response: Response,
    config: Config = Depends(get_config),
    conn: sqlite3.Connection = Depends(get_db),
    _user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    _ensure_summary(conn, config)
    with read_transaction(conn):
        run = latest_run(conn)
        summary = json.loads(run['summary'])
        for key, value in {'Run-Id':run['id'], 'Settings-Version':summary['calculation']['settingsVersion'],
                           'As-Of':summary['asOf'], 'Updated-At':summary['updatedAt']}.items():
            response.headers['X-Calculation-' + key] = str(value)
        return _source_snapshot(conn)


@router.put("/source/snapshot")
def put_snapshot(
    body: SnapshotIn,
    config: Config = Depends(get_config),
    conn: sqlite3.Connection = Depends(get_db),
    _user: dict[str, Any] = Depends(require_user),
) -> dict[str, Any]:
    try:
        validate_snapshot(body)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        with transaction(conn):
            settings, version, _ = get_settings(conn)
            _validate_settings(settings)
            counts = replace_snapshot(conn, body)
            summary = recompute(conn, settings, version, config.as_of)
            response = JSONResponse({"counts": counts, "summary": _summary_api(summary)})
        return response
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Изменение не применено; сохранено прежнее состояние") from None


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
