# Архитектура — предложение

> Цель архитектуры на хакатоне — **надёжно запускаться на чужой машине** и
> **расширяться одним файлом**, а не демонстрировать микросервисы.

---

## 1. Стек

| Слой | Выбор | Почему |
|---|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2 | Быстро, Swagger из коробки, удобно считать модель |
| ORM/БД | SQLAlchemy 2 + SQLite (WAL) | Ноль внешних сервисов, данные на volume, переживает рестарт |
| Frontend | React 18 + TypeScript + Vite | Скорость разработки, типы, HMR |
| UI | Tailwind CSS + небольшие свои компоненты | Без тяжёлого дизайн-системного оверхеда |
| Данные/таблицы | TanStack Query + серверная сортировка | Кэш, инвалидация по SSE, меньше кода |
| Графики | Recharts | Быстро и читаемо |
| Auth | Серверные сессии в БД, HttpOnly cookie | Проще и безопаснее JWT в localStorage |
| Метрики | `prometheus-client` | Стандартный формат, без отдельного сервиса |
| Контейнер | Один образ: FastAPI + собранный React | Меньше точек отказа, жюри запускает одной командой |

**Почему не Postgres.** На тестовом объёме SQLite с WAL полностью закрывает
потребности, а `docker compose up` не зависит от второго контейнера. При росте
меняем `DATABASE_URL` на Postgres — SQLAlchemy даёт это почти бесплатно.

**Почему один контейнер, а не api + nginx + db.** На защите важнее, чтобы
`docker compose up` работал с первого раза. FastAPI раздаёт статику React;
API и SPA на одном origin — нет CORS и возни с прокси.

---

## 2. Схема

```
┌───────────────────────────── Docker Compose ─────────────────────────────┐
│                                                                          │
│  Browser ──HTTP──▶ FastAPI :8000                                         │
│    │                 ├── /                → React build (static)         │
│    │                 ├── /api/v1/*        → JSON API (cookie session)     │
│    │                 ├── /api/v1/events   → SSE (живые обновления)        │
│    │                 ├── /metrics         → Prometheus (агрегаты)         │
│    │                 └── /api/v1/docs     → Swagger UI                    │
│    │                                                                     │
│    └── EventSource ─────────────────────────────────────────────────────┘
│                                                                          │
│  FastAPI ── SQLAlchemy ── SQLite /data/app.db  (volume)                  │
│      │                                                                   │
│      └── scoring engine ── feature registry ── money calculator          │
└──────────────────────────────────────────────────────────────────────────┘
```

Поток данных:

```
seed / PUT snapshot
        │
        ▼
  валидация Pydantic
        │
        ▼
  транзакция: заменить accounts/services/transactions
        │
        ▼
  пересчёт: features → score услуг → score клиента → деньги
        │
        ├──▶ customer_scores + summary (кэш для API)
        ├──▶ gauges Prometheus
        └──▶ SSE: scores.updated
                 │
                 ▼
          React Query invalidate → UI без reload
```

---

## 3. Структура репозитория

```
churn-analyzer/
├── backend/
│   ├── app/
│   │   ├── main.py                 # создание приложения, статика, роутеры
│   │   ├── config.py               # pydantic-settings
│   │   ├── db.py                   # engine, session, init
│   │   ├── models.py               # SQLAlchemy-таблицы
│   │   ├── schemas.py              # Pydantic DTO
│   │   ├── security.py             # пароли, сессии, зависимости auth
│   │   ├── features/
│   │   │   ├── base.py             # Feature, контекст
│   │   │   ├── expiry.py
│   │   │   ├── funds.py
│   │   │   ├── autorenew.py
│   │   │   ├── status.py
│   │   │   ├── payments.py
│   │   │   ├── commitment.py
│   │   │   └── __init__.py         # FEATURES = [...]
│   │   ├── scoring/
│   │   │   ├── engine.py           # score услуги/клиента, драйверы
│   │   │   ├── money.py            # MRR, coverage, expected loss
│   │   │   └── defaults.py         # веса, пороги, вероятность
│   │   ├── services/
│   │   │   ├── recompute.py        # оркестрация пересчёта
│   │   │   ├── snapshot.py         # загрузка/замена данных
│   │   │   └── events.py           # in-process pub/sub для SSE
│   │   ├── api/
│   │   │   ├── auth.py
│   │   │   ├── customers.py
│   │   │   ├── analytics.py
│   │   │   ├── model.py
│   │   │   ├── source.py
│   │   │   ├── metrics.py
│   │   │   └── events.py
│   │   └── seed.py                 # первый запуск из data/seed.json
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/                    # клиент, типы, query-хуки
│   │   ├── components/
│   │   ├── pages/                  # Login, Dashboard, Customer, Settings
│   │   ├── hooks/useLiveUpdates.ts
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── data/
│   ├── raw/                        # исходники (в .gitignore, если большие)
│   └── seed.json                   # нормализованный набор для первого старта
├── docs/
│   ├── CASE_BRIEF.md
│   ├── MODEL.md
│   ├── ARCHITECTURE.md
│   └── PLAN.md
├── scripts/
│   ├── export_openapi.py
│   └── smoke.sh
├── compose.yaml
├── openapi.json
├── .env.example
└── README.md
```

---

## 4. Модель данных

Деньги — **целые евроценты** (`*_cents`), не float. Внутри БД — snake_case,
в JSON API — camelCase, как в исходном `data.json` (Pydantic alias generator).

```
users(id, email, password_hash, created_at)
sessions(token_hash, user_id, expires_at, created_at)

accounts(id, email UNIQUE, balance_cents, withdraw_cents, bonus_cents,
         bonus_state TEXT CHECK (bonus_state IN ('locked','unlocked')),
         total_replenished_cents)

services(id, owner_id → accounts.id, name, price_cents, auto_prolong BOOL,
         payment_term, status, created_at, expires_at)

transactions(id, service_id → services.id, amount_cents, status, type,
             performed_at, created_at)

settings(id=1, payload JSON, version, updated_at)
score_runs(id, as_of, created_at, settings_version, summary JSON)
customer_scores(run_id, account_id, score NULL, level, confidence,
                drivers JSON, expected_loss_cents, amount_at_risk_cents,
                coverage, services_at_risk, is_estimated, unknown_reason)
```

Важно: `transactions` ссылается на **услугу**, а не на аккаунт; аккаунт
получаем через `services.owner_id`. Это соответствует исходной схеме
`001_schema.up.sql`.

Почему кэш `customer_scores`, а не расчёт на каждый запрос:
- сортировка и пагинация по score — в SQL, быстро и корректно на всём наборе;
- `/metrics` и `/analytics/summary` читают тот же результат → цифры не расходятся;
- SSE сообщает «пересчитано», UI просто инвалидирует кэш.

Пересчёт запускается:
- после `PATCH /model/settings`;
- после `PUT /source/snapshot`;
- по таймеру (по умолчанию 5 минут) — признаки зависят от `as_of`;
- при старте приложения.

`as_of` — фиксированное время снимка для демо (например, `2026-10-23T18:00:00Z`).
Без него статусы из статического набора «поплывут» относительно реального
времени. В production `as_of = now()`.

На тестовом объёме пересчёт синхронный: ответ на PATCH уже содержит новую сводку.

---

## 5. API

JSON — camelCase, как в исходных DTO; даты — ISO 8601 UTC; деньги — евро
с двумя знаками (`"balance": 4.00`). Внутри — центы.

### Список клиентов

```
GET /api/v1/customers?sort=balance&order=desc&level=high&q=ivan&page=1&pageSize=25
```

```json
{
  "items": [
    {
      "id": 42,
      "email": "ivan@example.com",
      "balance": 4.00,
      "totalReplenished": 120.00,
      "score": 75,
      "level": "high",
      "expectedLoss": 5.51,
      "amountAtRisk": 9.90,
      "servicesAtRisk": 1
    }
  ],
  "total": 137,
  "page": 1,
  "pageSize": 25
}
```

- `sort`: `id | email | balance | totalReplenished | score | expectedLoss`.
- `order`: `asc | desc`, по умолчанию `desc` для score и `asc` для id.
- Сортировка и фильтр — **в SQL по всему набору**, не в памяти страницы.
- `null` score при `level=high` не попадает; для `level=unknown` — отдельно.

### Карточка клиента

```json
{
  "id": 42,
  "email": "ivan@example.com",
  "balance": 4.00,
  "withdrawBalance": 0.00,
  "bonusBalance": 0.00,
  "bonusState": "locked",
  "totalReplenished": 120.00,
  "score": 75,
  "level": "high",
  "confidence": 0.95,
  "summary": "Услуга заканчивается через 2 дня, автопродление выключено, баланса не хватает",
  "drivers": [
    {"code": "expiry_pressure", "label": "До окончания 2 дня", "contribution": 0.40, "value": 1.0}
  ],
  "services": [
    {
      "id": 7,
      "name": "service-0007",
      "price": 9.90,
      "paymentTerm": "month",
      "status": "active",
      "autoProlong": false,
      "expiresAt": "2026-10-25T12:00:00Z",
      "score": 75,
      "level": "high",
      "staleStatus": false,
      "drivers": []
    }
  ],
  "money": {
    "amountAtRisk": 9.90,
    "coverage": 0.404,
    "balanceMitigation": 0.202,
    "expectedLoss": 5.51,
    "coveredLoss": 1.39
  }
}
```

### Остальное

| Метод | Путь | Ответ |
|---|---|---|
| GET | `/analytics/summary` | `countsByLevel`, `unknown`, `expectedLoss`, `amountAtRisk`, `coverage`, `asOf`, `updatedAt` |
| GET | `/model/settings` | weights, thresholds, probability, money, features metadata, version |
| PATCH | `/model/settings` | обновлённые настройки + summary после пересчёта |
| PUT | `/source/snapshot` | `{accounts, services, transactions}` в формате `data.json` → counts + summary |
| GET | `/metrics` | Prometheus text |
| GET | `/api/v1/events` | `text/event-stream` |
| GET | `/healthz` | `{"status":"ok"}` |

`PUT /source/snapshot` принимает **точный формат `data.json`** (camelCase),
чтобы жюри могло загрузить исходный файл без конвертации.

Ошибки: `401` без сессии, `403` нет прав, `422` невалидный снапшот,
`404` клиент не найден. Формат — FastAPI `{"detail": ...}`.

---

## 6. Живое обновление

**Основной путь — SSE:**

```
GET /api/v1/events
event: scores.updated
data: {"version": 12, "updated_at": "..."}
```

- `services/events.py` — простой in-process pub/sub (set of `asyncio.Queue`).
- После пересчёта публикуем событие.
- Frontend `useLiveUpdates` слушает `EventSource`, при событии вызывает
  `queryClient.invalidateQueries(["customers"])`, `["summary"]`, `["settings"]`.
- UI показывает зелёный индикатор «Обновлено 12:04:31».

**Фолбэк — polling** каждые 5 секунд, если SSE не подключился (или выбран
переключателем). Acceptance не требует конкретного способа — важно, чтобы
без reload. Поллинг проще и надёжнее на плохом Wi-Fi, поэтому он остаётся
как страховка на защите.

---

## 7. Auth

- Пользователь создаётся при первом старте из `ADMIN_EMAIL` / `ADMIN_PASSWORD`.
- Пароль — `argon2` (или `bcrypt`), никогда не в открытом виде.
- Логин: проверка, создание случайного токена (32 байта), в БД — только `sha256`.
- Cookie: `sid`, `HttpOnly`, `SameSite=Lax`, `Secure` при HTTPS, срок 12 часов.
- `GET /auth/me` — текущий пользователь, `POST /auth/logout` — удаление сессии.
- Зависимость `require_user` на всех `/api/v1/*`, кроме `/auth/login`.
- Простой rate limit на логин (например, 5 попыток / минута на IP).
- `/metrics` — без auth, но только агрегаты, без email и ID (осознанное решение,
  см. `❓` в брифе).
- Swagger `/api/v1/docs` — открыт для чтения; запросы из «Try it out» требуют
  cookie, то есть сначала логин в панели. Это ожидаемо и описано в README.

---

## 8. Метрики

```
# HELP churn_customers_total Клиенты по уровням риска
# TYPE churn_customers_total gauge
churn_customers_total{level="high"} 12
churn_customers_total{level="medium"} 31
churn_customers_total{level="low"} 94
churn_customers_total{level="unknown"} 3

# HELP churn_expected_loss_eur Ожидаемые потери при ближайшем продлении, EUR
# TYPE churn_expected_loss_eur gauge
churn_expected_loss_eur 1234.56

# HELP churn_amount_at_risk_eur Сумма платежей под риском, EUR
# TYPE churn_amount_at_risk_eur gauge
churn_amount_at_risk_eur 4321.00

# HELP churn_services_at_risk Услуги под риском
# TYPE churn_services_at_risk gauge
churn_services_at_risk 34

# HELP churn_risk_score_avg Средний score клиентов с оценкой
# TYPE churn_risk_score_avg gauge
churn_risk_score_avg 46.2

# HELP churn_as_of_timestamp_seconds Время снимка данных
# TYPE churn_as_of_timestamp_seconds gauge
churn_as_of_timestamp_seconds 1761232800

# HELP churn_last_recompute_timestamp_seconds Время последнего пересчёта
# TYPE churn_last_recompute_timestamp_seconds gauge
churn_last_recompute_timestamp_seconds 1761241509
```

Источник — тот же `summary`, что отдаёт API. Обновляем gauges в `recompute.py`,
не считаем отдельно. Это гарантирует согласованность.

---

## 9. Docker

`compose.yaml`:

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file: .env
    volumes:
      - app-data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 10s
      timeout: 3s
      retries: 5
    restart: unless-stopped

volumes:
  app-data:
```

Dockerfile — multi-stage:

1. `node:20-alpine` собирает `frontend/dist`.
2. `python:3.12-slim` ставит зависимости, копирует backend и `dist`.
3. Запуск `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
4. Не-root пользователь, `HEALTHCHECK`, никаких `node_modules` в финальном образе.

`README`:

```bash
cp .env.example .env
docker compose up --build
# http://localhost:8000
```

Проверка перед сдачей: `docker compose down -v && docker compose up --build`
на чистом клоне, без локальных артефактов.

---

## 10. Расширяемость

Три уровня, все — «минимальная правка»:

1. **Новый признак** — значение в `_score_service`, запись в `FEATURES_META`
   и вес в `DEFAULT_SETTINGS` (всё в `backend/app/scoring.py`). UI получает
   метаданные и рисует ползунок сам; движок и API не меняются.
2. **Новый коэффициент** — это вес существующего признака, уже редактируется.
3. **Новый источник данных** — интерфейс `SourceAdapter`:
   `fetch() -> Snapshot`. Сейчас есть `SeedAdapter` и `SnapshotAdapter`
   (PUT-загрузка); позже — webhook/poller, без изменений в scoring.

`/model/settings` отдаёт:

```json
{
  "weights": {
    "expiry_pressure": 0.40,
    "funds_gap": 0.25,
    "autorenew_off": 0.10,
    "status_pressure": 0.10,
    "payment_history": 0.10,
    "commitment": 0.05
  },
  "thresholds": {"medium": 40, "high": 70},
  "probability": {"midpoint": 65, "steepness": 12, "floor": 0.02, "ceiling": 0.95},
  "money": {"balanceMitigation": 0.5, "includeWithdrawBalance": true},
  "statusFloors": {"prolong_wait": 70, "blocked": 60, "stale": 70},
  "features": [
    {
      "code": "expiry_pressure",
      "title": "Срочность продления",
      "description": "Сколько дней до конца оплаченного периода",
      "min": 0, "max": 1, "step": 0.01, "default": 0.40
    }
  ],
  "version": 1
}
```

---

## 11. Компромиссы, которые честно называем

| Решение | Плюс | Минус | Когда меняем |
|---|---|---|---|
| Один контейнер | Запуск одной командой | Нет отдельного масштабирования | Если вырастет нагрузка |
| SQLite | Ноль инфраструктуры | Один писатель | При переходе на Postgres |
| Rule-based | Объяснимо, нет меток | Не «ML» | Когда появится история |
| SSE | Просто, живые обновления | Нет авторитетного канала | WebSocket при необходимости |
| `/metrics` без auth | Сборщик просто работает | Формально открыт | Если жюри потребует закрыть |
| Синхронный пересчёт | Цифры сразу | Не для миллионов строк | Очередь/воркер при росте |

---

## 12. Что делает каждый участник в первые 6 часов

- **Backend:** модели БД, seed, `Feature`/`engine`, `/customers` на моках,
  `/healthz`, compose.
- **Frontend:** логин-заглушка, layout, таблица с сортировкой на моках,
  карточка клиента, настройки.
- **Data:** профилирование датасета, `DATA_NOTES.md`, seed, 5 демо-кейсов,
  проверка формул на реальных числах.
- **Капитан/QA:** чек-лист приёмки, риски, сценарий демо, тексты README,
  следит, чтобы контракт не расползался.
