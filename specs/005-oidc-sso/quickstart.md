# Quickstart validation: 005

Проверка после реализации. Рабочая БД, `.env` и секреты не затрагиваются;
для тестов используется временный `APP_DB`.

## 1. Автоматические проверки

```bash
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests data/raw/test_generate.py
npm --prefix frontend run build
PYTHONPATH=backend .venv/bin/python scripts/export_openapi.py
```

Ожидаемо: `421 passed` (404 + 17 новых), успешная сборка, `openapi.json` с 15 путями.

## 2. Вход по паролю (регрессия)

```bash
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --port 8000
curl -s localhost:8000/api/v1/auth/oidc/config          # {"enabled":false,...}
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/api/v1/auth/oidc/start   # 404
```

Открыть `http://localhost:8000`, войти `admin@example.test` / `admin123`.
Кнопки SSO быть не должно.

## 3. Вход через Keycloak (демо)

```bash
cp .env.example .env
# раскомментировать OIDC_* (значения для compose уже подготовлены)
docker compose --profile sso up --build
```

1. `http://localhost:8000/#/login` — видна кнопка «Войти через Keycloak».
2. Нажать → вход в Keycloak `marketer@example.test` / `marketer123`
   (консоль `http://localhost:8081`, `admin` / `admin`).
3. После возврата — дашборд, в боковой панели `marketer@example.test`.

Проверка данных:

```bash
curl -s -b cookies.txt localhost:8000/api/v1/auth/me
sqlite3 data/app.db "select email, oidc_subject, length(password_hash) from users;"
```

У SSO-пользователя `password_hash` пустой; `POST /auth/login` для него вернёт 401.

## 4. Ошибки провайдера

- Остановить Keycloak и нажать кнопку: возврат на вход с «Провайдер входа недоступен».
- Открыть `http://localhost:8000/#/login?sso_error=token_expired` — понятное сообщение.
- Повторно использовать ссылку callback (тот же `state`) — `state_invalid`.

## 5. Без провайдера

Убрать `OIDC_*` из `.env` и перезапустить: приложение снова только с паролем,
`openapi.json` и тесты не меняются.

## Что не проверяется

- Single Logout у провайдера и маппинг ролей/групп — вне объёма.
- ES256/HS256 — поддерживается только RS256, отклонение проверено тестом.
- Реальные внешние провайдеры (Okta, Google) — проверено на Keycloak-совместимом
  фейковом провайдере и Keycloak-конфигурации.
