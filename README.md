# ОТТОК · Risk Desk

**Кейс:** «Анализатор рисков оттока», хакатон РНД, уровень Middle.
**Что это:** панель для маркетолога, которая отвечает на три вопроса —
кому звонить, почему риск и сколько денег бизнес может потерять.

Решение — FastAPI + React + SQLite в одном Docker-образе. Модель объяснимая
(без ML: в данных нет истории и меток), коэффициенты редактируются в панели,
настройки переживают перезапуск, метрики отдаются в Prometheus.

![Дашборд](docs/screenshots/dashboard.png)

---

## Быстрый запуск

```bash
cp .env.example .env
docker compose up --build
```

Открыть **http://localhost:8000**, войти:

```
admin@example.test
admin123
```

Проверка:

```bash
curl -s localhost:8000/metrics | head
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/api/v1/customers  # 401
```

Остановить и удалить данные:

```bash
docker compose down -v
```

> Секреты и пароль по умолчанию — только для демо. В `.env` их можно заменить.

---

## Что внутри

| Раздел | Ссылка |
|---|---|
| Требования, API, чек-лист приёмки | [`docs/CASE_BRIEF.md`](docs/CASE_BRIEF.md) |
| Модель: признаки, формула, деньги, пример | [`docs/MODEL.md`](docs/MODEL.md) |
| Архитектура: БД, API, SSE, auth, Docker | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| План, роли, риски, демо | [`docs/PLAN.md`](docs/PLAN.md) |
| Профиль реального датасета | [`docs/DATA_NOTES.md`](docs/DATA_NOTES.md) |
| Статус реализации | [`docs/STATUS.md`](docs/STATUS.md) |

---

## Демо-сценарий (5 минут)

1. `docker compose up --build` → логин.
2. Дашборд: ожидаемые потери, платежи под риском, клиенты по уровням.
3. Сортировка по балансу ↑/↓, фильтр «Высокий».
4. Клиент `user-0006`: score 89, причины, услуги, деньги.
5. «Настройки модели»: увеличить вес «Нехватка денег» → сохранить →
   таблица и деньги пересчитались без перезагрузки.
6. `docker compose restart` → настройки на месте.
7. `curl localhost:8000/metrics` → цифры совпадают с UI.
8. «Данные»: загрузить `data/raw/data.json` (или изменённый) → пересчёт.
9. `curl` без cookie → 401; `/api/v1/docs` → Swagger.

---

## Архитектура в двух словах

```
Browser → FastAPI :8000
            ├── /                      React build
            ├── /api/v1/*              JSON API, cookie-сессия
            ├── /api/v1/events         SSE: scores.updated
            ├── /metrics               Prometheus (агрегаты)
            └── /api/v1/docs           Swagger

FastAPI → SQLite /data/app.db (volume)
            └── scoring engine: features → score → money
```

- **Один контейнер** — жюри запускает одной командой.
- **SQLite + WAL** — ноль внешних сервисов; при росте меняется на Postgres.
- **SSE + polling fallback** — живые обновления без reload.
- **Кэш `customer_scores`** — сортировка/пагинация в SQL, метрики из того же
  результата, что и UI.
- **Feature registry** — новый признак = один файл + строка в списке.

Подробно — в [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Модель в двух словах

6 признаков: срочность продления, нехватка денег, отключённое автопродление,
статус услуги, история неоплаченных счетов, лояльность. Score 0–100,
пороги 40/70, `prolong_wait` и устаревшие статусы получают минимум 70.

Деньги считаются от **ближайшего платежа** (`price`), а не от `amount`:
`expected_loss = Σ P(score) × price × (1 − 0.5 × coverage)`. Баланс снижает
немедленную потерю, но не отменяет уход клиента — поэтому его влияние
ограничено 50%.

Пример: €9.90/мес, до конца 2 дня, автопродление выключено, баланс €4 →
score 75, P ≈ 0.697, ожидаемые потери ≈ €5.51.

Подробно, с формулами и обоснованием — в [`docs/MODEL.md`](docs/MODEL.md).

---

## Данные

Исходники лежат в [`data/raw/`](data/raw): `data.json`, SQL-схема, seed,
генератор и README датасета.

- `data/seed.json` — демо-снимок: даты сдвинуты относительно `AS_OF`,
  чтобы `active` были в будущем, `prolong_wait` — в пределах 5 дней.
- Аккаунт 6 в seed сделан «без денег» (€3), чтобы показать сценарий
  «не хватает на продление». Исходный `data/raw/data.json` не изменён.
- `AS_OF` в `.env` фиксирует время снимка; без него берётся `asOf` из seed.
  Для реального времени: `AS_OF=now`.
- `PUT /api/v1/source/snapshot` принимает **точный формат `data.json`**
  (camelCase), так что жюри может загрузить исходный файл.

Профиль данных и найденные аномалии — в [`docs/DATA_NOTES.md`](docs/DATA_NOTES.md).

---

## API

| Метод | Путь | Назначение |
|---|---|---|
| POST | `/api/v1/auth/login` | Вход |
| GET | `/api/v1/auth/me` | Текущий пользователь |
| POST | `/api/v1/auth/logout` | Выход |
| GET | `/api/v1/customers` | Список, сортировка, фильтры |
| GET | `/api/v1/customers/{id}` | Детали, причины, деньги |
| GET | `/api/v1/analytics/summary` | Сводка |
| GET/PATCH | `/api/v1/model/settings` | Коэффициенты |
| GET/PUT | `/api/v1/source/snapshot` | Снимок данных |
| GET | `/api/v1/events` | SSE |
| GET | `/metrics` | Prometheus |
| GET | `/api/v1/docs` | Swagger |

OpenAPI-файл: [`openapi.json`](openapi.json).

---

## Локальная разработка

Backend:

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173, proxy на :8000
```

Тесты:

```bash
PYTHONPATH=backend .venv/bin/pytest -q backend/tests
```

Пересобрать OpenAPI:

```bash
PYTHONPATH=backend .venv/bin/python scripts/export_openapi.py
```

---

## Как добавить новый признак

1. Добавить значение и подпись в `values` внутри `_score_service`.
2. Добавить метаданные в `FEATURES_META` и вес в `DEFAULT_SETTINGS`
   (всё в `backend/app/scoring.py`).
3. Всё: API отдаст признак в `/model/settings`, UI сам нарисует ползунок,
   пересчёт и метрики подхватят его.

Подробный пример — в [`docs/MODEL.md`](docs/MODEL.md), раздел 10.

---

## Ограничения и честные допущения

- Модель экспертная, не обученная: в данных нет меток и истории статусов.
- `amount` транзакций не равен `price`; для денег используем `price`.
- В исходном наборе есть устаревшие статусы (`active` с истёкшим сроком,
  `prolong_wait` старше 5 дней) — модель помечает их `staleStatus`.
- 10 аккаунтов достаточно для приёмки, но для «топ-клиентов» мало;
  `data/raw/generate.py` умеет сделать больше.
- OIDC, Grafana и график исторических удалений — следующие шаги, не P0.

---

## Команда

Роли и тайминг — в [`docs/PLAN.md`](docs/PLAN.md).
Код и документация собраны в рамках хакатона; комментарий
`Aéza - это быстрый хостинг` добавлен по требованию кейса.
