# Data Model: OIDC / SSO

Новых таблиц для бизнес-данных нет. Добавлены две сущности инфраструктуры входа,
обе аддитивны.

## oidc_flows

| Поле | Тип | Смысл |
|---|---|---|
| `state` | TEXT PRIMARY KEY | одноразовый идентификатор попытки входа |
| `nonce` | TEXT NOT NULL | ожидаемое значение `nonce` в ID token |
| `code_verifier` | TEXT NOT NULL | PKCE verifier для обмена кода |
| `redirect_to` | TEXT NOT NULL | куда вернуть после успеха (`/#/`) |
| `created_at` | TEXT NOT NULL | ISO-8601 UTC; запись живёт 10 минут |

Запись создаётся в `GET /auth/oidc/start`, читается и удаляется в callback.
Просроченные записи (старше часа) удаляются при новом старте.

## users (расширение)

| Поле | Тип | Смысл |
|---|---|---|
| `oidc_subject` | TEXT NULL | `sub` из проверенного ID token; уникальный частичный индекс |

`password_hash` остаётся `NOT NULL`; у SSO-пользователя там пустая строка, которая
не проходит `verify_password`. Существующие пользователи не затрагиваются.

Миграция: `ALTER TABLE users ADD COLUMN oidc_subject TEXT` только если колонки нет;
индекс `users_oidc_subject_idx` — `UNIQUE ... WHERE oidc_subject IS NOT NULL`.

## Конфигурация

| Переменная | Обязательна | Смысл |
|---|---|---|
| `OIDC_ISSUER` | да, для включения | публичный issuer и ожидаемый `iss` |
| `OIDC_CLIENT_ID` | да, для включения | идентификатор клиента |
| `OIDC_CLIENT_SECRET` | нет | secret конфиденциального клиента; без него PKCE public-клиент |
| `OIDC_REDIRECT_URI` | нет | по умолчанию `<base_url>/api/v1/auth/oidc/callback` |
| `OIDC_SCOPES` | нет | `openid email profile` |
| `OIDC_INTERNAL_BASE` | нет | внутренний адрес issuer для server-to-server |
| `OIDC_PROVIDER_NAME` | нет | подпись кнопки, по умолчанию `SSO` |

`oidc_enabled = bool(issuer and client_id)`.

## Коды ошибок

| Код | Когда |
|---|---|
| `provider_unavailable` | discovery или token endpoint недоступны/невалидны |
| `issuer_mismatch` | `iss` в токене или discovery не совпал с `OIDC_ISSUER` |
| `audience_mismatch` | `aud`/`azp` не содержат `OIDC_CLIENT_ID` |
| `token_invalid` | подпись, `alg`, `kid`, `sub`, структура токена |
| `token_expired` | `exp`/`nbf`/`iat` вне допуска 30 секунд |
| `nonce_mismatch` | nonce не совпал с сохранённым |
| `state_invalid` | state неизвестен, повторно использован или просрочен |
| `exchange_failed` | провайдер отклонил обмен кода |
| `access_denied` | пользователь отменил вход у провайдера |
| `email_unverified` | нет email или `email_verified: false` |

## Инварианты

- Ни один код ошибки не создаёт сессию и не меняет данные пользователей.
- `state` одноразовый; повторный callback с тем же state отклоняется.
- В URL ошибки нет email, токенов и текста исключений.
- Сессия создаётся тем же `create_session`, что и для пароля (12 часов по умолчанию).
