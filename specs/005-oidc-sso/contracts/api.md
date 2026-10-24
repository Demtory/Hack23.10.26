# API Contract: OIDC

Три новых публичных маршрута (без сессии). Существующие `/auth/login`, `/auth/me`,
`/auth/logout` не меняются.

## GET /api/v1/auth/oidc/config

Опубликован, чтобы экран входа знал, показывать ли кнопку. Без секретов.

```json
{ "enabled": true, "providerName": "Keycloak" }
```

Если OIDC не настроен: `{"enabled": false, "providerName": "SSO"}`.

## GET /api/v1/auth/oidc/start

303 на `authorization_endpoint` провайдера. Параметры:

| Параметр | Значение |
|---|---|
| `response_type` | `code` |
| `client_id` | `OIDC_CLIENT_ID` |
| `redirect_uri` | `OIDC_REDIRECT_URI` или выведенный из запроса |
| `scope` | `OIDC_SCOPES` |
| `state` | случайный, хранится в `oidc_flows` |
| `nonce` | случайный, хранится в `oidc_flows` |
| `code_challenge` / `code_challenge_method` | PKCE `S256` |

Заголовки: `Cache-Control: no-store`.
Если OIDC не настроен — `404 {"detail": "oidc is not configured"}`.

## GET /api/v1/auth/oidc/callback

Параметры: `code`, `state`, `error` (последний — от провайдера).

Успех: `303 Location: /#/`, `Set-Cookie: sid=...; HttpOnly; SameSite=Lax; Path=/`.

Ошибка: `303 Location: /#/login?sso_error=<код>`, без `Set-Cookie`.
Коды перечислены в [data-model.md](../data-model.md#коды-ошибок).

## Пример обмена (Keycloak)

```
GET  /api/v1/auth/oidc/start                           → 303 http://localhost:8081/realms/risk-desk/protocol/openid-connect/auth?...
GET  /api/v1/auth/oidc/callback?code=...&state=...     → 303 /#/  + sid cookie
GET  /api/v1/auth/me                                   → 200 {"id": 2, "email": "marketer@example.test"}
```

## Совместимость

- `POST /api/v1/auth/login` не изменён; SSO-пользователь получает на нём 401.
- `/api/v1/auth/me` и `/api/v1/auth/logout` работают с SSO-сессией так же, как с парольной.
- OpenAPI: три новых пути, схемы запросов не добавляются (все параметры — query).
