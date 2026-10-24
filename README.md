# ОТТОК · Risk Desk

**Кейс:** «Анализатор рисков оттока», хакатон РНД, уровень Middle.
**Что это:** панель для маркетолога, которая отвечает на три вопроса —
кому звонить, почему риск и сколько денег бизнес может потерять.

Решение — FastAPI + React + SQLite в одном Docker-образе. Модель объяснимая
(без ML: в данных нет истории и меток), коэффициенты редактируются в панели,
настройки переживают перезапуск, метрики отдаются в Prometheus.

![Обзор риска](docs/screenshots/02-overview-1440.png)

---

## Быстрый запуск

Нужен только Docker. Настраивать нечего — все значения уже имеют рабочие демо-умолчания.

```bash
./scripts/bootstrap.sh     # собрать, запустить, дождаться healthz и прогнать smoke
```

Или вручную:

```bash
docker compose up --build
```

Открыть **http://localhost:8000**, войти `admin@example.test` / `admin123`.

Проверить одной командой, что всё поднялось:

```bash
./scripts/smoke.sh
# ok healthz · метрики · закрытый API 401 · панель · логин · сессия
```

Остановить и удалить данные:

```bash
docker compose down -v
```

> Пароль и ключи в примерах — только для демо. Переопределяются через `.env`
> (необязательный файл) или переменные окружения.

### Если что-то не запускается

| Симптом | Причина и решение |
|---|---|
| `Cannot connect to the Docker daemon` | Не запущен Docker Desktop / OrbStack. Запустить и повторить. |
| `port is already allocated` | Порт занят: `APP_PORT=8010 docker compose up --build`, открыть `http://localhost:8010`. |
| `env file ... not found` | Старый `compose.yaml` или свой файл. Обновиться до текущего `main`: `.env` больше не обязателен. |
| Старый Docker Compose | Нужен Compose v2 (`docker compose`, а не `docker-compose`). `docker compose version` → 2.20+. |
| Windows | Те же команды в PowerShell. `./scripts/smoke.sh` — через Git Bash или WSL. |
| Apple Silicon | Образы `python:3.12-slim`, `node:22-alpine` и Keycloak мультиархитектурные, эмуляция не нужна. |
| Данные «застряли» после экспериментов | `docker compose down -v` — том пересоздастся из seed. |

Проверки на чистой машине без Docker (разработка):

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r backend/requirements-dev.txt
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests
npm --prefix frontend ci && npm --prefix frontend run build
```

---

## Работа в команде

Клонируйте репозиторий **один раз**, дальше обновляйтесь через `git pull` — инструкции
и код приезжают вместе, ничего перекачивать не нужно:

```bash
git clone git@github.com:Demtory/Hack23.10.26.git
cd Hack23.10.26
git pull --rebase          # перед началом работы
git switch -c feat/my-task # своя ветка на задачу
```

Правила веток, PR, конфликтов в сгенерированных файлах и разбор «у меня не работает» —
в [`CONTRIBUTING.md`](CONTRIBUTING.md). CI на каждый push проверяет тесты, сборку,
OpenAPI, compose и `docker build`.

После чужого пуша достаточно:

```bash
git pull --rebase && docker compose up --build -d && ./scripts/smoke.sh
```

---

## Вход: пароль и SSO

По умолчанию вход по паролю (`admin@example.test` / `admin123`). OIDC включается
переменными окружения и не ломает парольный вход — он остаётся как fallback.

Демо с Keycloak:

```bash
docker compose -f compose.yaml -f compose.sso.yaml up --build
# Keycloak: http://localhost:8081, панель: http://localhost:8000
```

На экране входа появится «Войти через Keycloak»; тестовый пользователь —
`marketer@example.test` / `marketer123` (realm `risk-desk`, клиент `risk-desk`).

| Переменная | Назначение |
|---|---|
| `OIDC_ISSUER` | публичный issuer, он же ожидаемый `iss` в ID token |
| `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET` | клиент; secret можно не задавать для public-клиента с PKCE |
| `OIDC_REDIRECT_URI` | адрес callback, по умолчанию выводится из запроса |
| `OIDC_SCOPES` | по умолчанию `openid email profile` |
| `OIDC_INTERNAL_BASE` | внутренний адрес issuer для server-to-server вызовов (например `http://keycloak:8080/realms/risk-desk`) |
| `OIDC_PROVIDER_NAME` | подпись кнопки, по умолчанию `SSO` |

Реализован Authorization Code + PKCE (S256): state и nonce хранятся в БД и одноразовые,
подпись ID token проверяется по JWKS (RS256), проверяются `iss`, `aud`, `exp`, `nonce`.
Первый вход создаёт пользователя по подтверждённому email; у такого пользователя нет
пароля, поэтому парольный вход для него запрещён. Новых зависимостей нет — HTTP-клиент
и проверка RSA на стандартной библиотеке.

Границы: поддерживается только RS256 (дефолт Keycloak/Okta/Google), выход из приложения
не выполняет Single Logout у провайдера, роли и группы не маппятся. Если сменить
`APP_PORT` для SSO-демо, добавьте новый redirect URI в realm — иначе провайдер отклонит вход.

## Что внутри

| Раздел | Ссылка |
|---|---|
| Требования, API, чек-лист приёмки | [`docs/CASE_BRIEF.md`](docs/CASE_BRIEF.md) |
| Модель: признаки, формула, деньги, пример | [`docs/MODEL.md`](docs/MODEL.md) |
| Архитектура: БД, API, SSE, auth, Docker | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| План, роли, риски, демо | [`docs/PLAN.md`](docs/PLAN.md) |
| Профиль реального датасета | [`docs/DATA_NOTES.md`](docs/DATA_NOTES.md) |
| Статус реализации | [`docs/STATUS.md`](docs/STATUS.md) |
| Спецификации по этапам (Spec Kit) | [`specs/`](specs) — 001 модель, 002 данные/UI, 003 панель, 004 тексты и письмо, 005 SSO |
| **Жюри: запуск за 3 минуты** | [`docs/JURY.md`](docs/JURY.md) |
| **Защита: прогон на 5 минут** | [`docs/DEFENSE.md`](docs/DEFENSE.md) — что открыть, что сказать, план Б |
| **Питч-дека** | [`pitch/risk-desk-pitch.pptx`](pitch/risk-desk-pitch.pptx) и [PDF](pitch/risk-desk-pitch.pdf) — 9 слайдов, собирается `pitch/build_pitch.py` |
| **Ответы на вопросы жюри** | [`docs/QNA.md`](docs/QNA.md) — 14 вопросов с короткими ответами |
| **Нагрузочный тест** | [`docs/LOAD_TEST.md`](docs/LOAD_TEST.md) — 10 000 клиентов, замеры и ограничения |

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
10. SSO (если поднят оверлей): «Войти через Keycloak» → дашборд под `marketer@example.test`.

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
- **Признаки** — расчёт, metadata и явное поколение в scoring.py.

Подробно — в [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Модель в двух словах

7 признаков: срочность продления, нехватка денег, отключённое автопродление,
статус услуги, история неоплаченных счетов, лояльность и новый — доля услуг
без автопродления (по умолчанию вес 0, поэтому прежние оценки не меняются). Score 0–100,
пороги 40/70, `prolong_wait` и устаревшие статусы получают минимум 70.

Деньги считаются от **ближайшего платежа** (`price`), а не от `amount`:
`expected_loss = Σ P(score) × price × (1 − 0.5 × coverage)`. Баланс снижает
немедленную потерю, но не отменяет уход клиента — поэтому его влияние
ограничено 50%.

Пример: €9.90/мес, до конца 2 дня, автопродление выключено, баланс €4 →
score 75, P ≈ 0.697, ожидаемые потери ≈ €5.51.

В панели есть готовые наборы весов («Сбалансированный», «Деньги важнее»,
«Срочность важнее», «Статус и оплата») и возможность сохранить свой набор: пресет
заполняет черновик весов, пороги и денежные правила не трогает.

Подробно, с формулами и обоснованием — в [`docs/MODEL.md`](docs/MODEL.md).

---

## Данные

Исходники лежат в [`data/raw/`](data/raw): `data.json`, SQL-схема, seed,
генератор и README датасета.

- `data/seed.json` — демо-снимок: даты сдвинуты относительно `AS_OF`,
  чтобы `active` были в будущем, `prolong_wait` — в пределах 5 дней.
- Аккаунт 6 в seed сделан «без денег» (€3), чтобы показать сценарий
  «не хватает на продление». Исходный `data/raw/data.json` не изменён.
- `AS_OF` фиксирует время снимка: в compose есть демо-умолчание, переопределяется
  через `.env` или переменные окружения; без него берётся `asOf` из seed.
  Для реального времени: `AS_OF=now`.
- `PUT /api/v1/source/snapshot` принимает **точный формат `data.json`**
  (camelCase), так что жюри может загрузить исходный файл.

Профиль данных и найденные аномалии — в [`docs/DATA_NOTES.md`](docs/DATA_NOTES.md).

---

## API

| Метод | Путь | Назначение |
|---|---|---|
| POST | `/api/v1/auth/login` | Вход по паролю |
| GET | `/api/v1/auth/me` | Текущий пользователь |
| POST | `/api/v1/auth/logout` | Выход |
| GET | `/api/v1/auth/oidc/config` | Включён ли SSO и как называется кнопка |
| GET | `/api/v1/auth/oidc/start` | Редирект к провайдеру (Authorization Code + PKCE) |
| GET | `/api/v1/auth/oidc/callback` | Callback провайдера: проверка токена и сессия |
| GET | `/api/v1/customers` | Список, сортировка, фильтры, `topLosses` |
| GET | `/api/v1/customers/{id}` | Детали, причины, письмо клиенту |
| GET | `/api/v1/customers/export.csv` | Экспорт выбранной группы |
| GET | `/api/v1/analytics/summary` | Сводка |
| GET | `/api/v1/analytics/forecast` | Факт истечений и прогноз непродлений по срокам |
| GET | `/api/v1/analytics/forecast/day` | Услуги выбранного интервала |
| GET | `/api/v1/analytics/forecast/export.csv` | CSV с планом обзвона: недели, услуги, потери |
| GET/PATCH | `/api/v1/model/settings` | Коэффициенты |
| GET/POST | `/api/v1/model/presets` | Готовые наборы весов: список и сохранение своего |
| DELETE | `/api/v1/model/presets/{id}` | Удалить свой набор |
| GET/PUT | `/api/v1/source/snapshot` | Снимок данных |
| GET | `/api/v1/events` | SSE |
| GET | `/metrics` | Prometheus |
| GET | `/healthz` | Проверка живости |
| GET | `/api/v1/docs` | Swagger |

OpenAPI-файл: [`openapi.json`](openapi.json).

Карточка клиента отдаёт `summary` — одну-две фразы для маркетолога, `summaryDetails` —
раскрываемые факты (срок, деньги, автопродление, услуги под риском) и `emailDraft` —
тему и текст письма клиенту под ситуацию: `prolong_wait`, `blocked`, `suspended`,
`funds_gap`, `expiry_auto_off`, `unknown`, `on_track`. Тексты детерминированы
(шаблоны, без LLM): суммы, даты и имя услуги подставляются из расчёта. Отправка
не выполняется — панель копирует письмо или открывает `mailto:`.

Прогноз оттока (`/api/v1/analytics/forecast`, параметры `pastDays`/`horizonDays` до 90,
`bucketDays` для недельной группировки): слева факт по текущему снимку — услуги, у которых
срок истёк и они не продлены; справа прогноз — услуги с истечением впереди и ожидаемое
число непродлений из score. Столбцы кликабельны: открывается список услуг недели
с клиентом, ценой, score и ожидаемыми потерями (`/api/v1/analytics/forecast/day`
с параметрами `date`, `end`, `kind`). Кнопка «Экспорт прогноза» выгружает CSV
с неделями, услугами, вероятностями и ожидаемыми потерями — это готовый план обзвона.
Исторических удалений нет: в данных отсутствует дата удаления, поэтому интерфейс
и API прямо это сообщают, а не рисуют вымышленный тренд.

Денежный вход снимка: JSON-целые евроценты0…9223372036854775807 во всех шести
финансовых полях. Строки, bool, null, дробная/экспоненциальная запись
(`100.0`, `1e2`) отклоняются; amount выше1000 разрешён. Производное переполнение
тоже отклоняет всю замену без потери прежних данных. В UI исходный файл отправляется
и подтверждённый снимок скачивается как текст, без округления больших целых JavaScript.
JSON Schema не различает100 и100.0; это ограничение дополнительно проверяет сервер.

Список дополнен `topLosses`, глобальной `summary` и контекстом `calculation`
(runId/settingsVersion/сохранённые thresholds). Топ учитывает поиск по email или ID
(числовой запрос дополнительно сравнивается с точным ID) и level, но не страницу/сортировку; равенства разрешаются
по id. Верхние карточки остаются глобальными. Пороги в подписях относятся к тому же расчёту.

Доступ: cookie sid **или** Bearer session token. Непустая cookie имеет приоритет,
даже если недействительна: fallback к Bearer отсутствует. Logout отзывает выбранный
токен на сервере; независимые сессии сохраняются. Без токена/при повторном выходе
возвращается200. Браузер удаляет локальный токен только после успешного ответа;
при ошибке остаётся в приложении с сообщением и возможностью повторить выход.


---

## Локальная разработка

Нужны Python 3.12 и Node 22+ (только для разработки; для запуска достаточно Docker).

Backend:

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm ci
npm run dev   # http://localhost:5173, proxy на :8000
```

E2E (опционально, нужны браузеры Playwright):

```bash
cd frontend
npx playwright install chromium
npx playwright test panel.spec.ts   # 7 проверок интерфейса
```

Конфиг сам находит Python: `PYTHON`, затем `.venv` проекта, затем системный `python3`.
Скриншоты для README пересобирает `npx playwright test capture-screens.spec.ts` —
он перезаписывает файлы в `docs/screenshots/`.

Тесты:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests data/raw/test_generate.py
npm --prefix frontend ci
npm --prefix frontend run build
```

Тесты используют отдельные временные SQLite, не рабочую `data/app.db`.
Для замены снимка все три массива и обязательные поля должны быть переданы явно:
отсутствие/null вызывает422 без частичного импорта; явные0/false допустимы.
Явные три пустых массива означают намеренную очистку и сохраняются после restart.
Настройки и снимок фиксируются вместе с успешным пересчётом; при внутреннем отказе
сохраняется прежнее состояние. `drivers` остаётся массивом взвешенных причин,
дополнительные правила доступны в `explanationRules` клиента/услуг и в карточке.

Пересобрать OpenAPI:

```bash
PYTHONPATH=backend .venv/bin/python scripts/export_openapi.py
```

Проверить запущенное приложение без браузера:

```bash
./scripts/smoke.sh http://localhost:8000
```

CI на каждый push (`.github/workflows/ci.yml`): pytest и генератор данных,
синхронность `openapi.json`, `tsc && vite build`, валидность обоих compose-файлов
и `docker build`. Локально те же проверки:

```bash
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests data/raw/test_generate.py
npm --prefix frontend run build
git diff --exit-code openapi.json
```

---

## Как добавить новый признак

1. Добавить значение и подпись в `values` внутри `_score_service`.
2. Добавить метаданные в `FEATURES_META` и вес в `DEFAULT_SETTINGS`
   (всё в `backend/app/scoring.py`).
3. В `FEATURE_GENERATIONS` объявить следующее последовательное поколение с новыми
   кодами. Поколение1 не менять. Старые настройки при startup дополняются только
   объявленными новыми кодами с весом0, без сброса прежних значений. Новая база
   получает рекомендованные defaults. Явный новый вес сохраняется.
4. Проверить upgrade/restart/rollback и неизменность старого расчёта при новом0
   на временной базе. API передаёт metadata, UI показывает ползунок и fallback-описание.
   Неизвестный код, потерянный старый ключ или некорректное значение вызывают отказ,
   а не автоматический ремонт.

Подробный пример — в [`docs/MODEL.md`](docs/MODEL.md), раздел 10.

---

## Ограничения и честные допущения

- Модель экспертная, не обученная: в данных нет меток и истории статусов.
- `amount` транзакций не равен `price`; для денег используем `price`.
- В исходном наборе есть устаревшие статусы (`active` с истёкшим сроком,
  `prolong_wait` старше 5 дней) — модель помечает их `staleStatus`.
- 10 аккаунтов достаточно для приёмки, но для «топ-клиентов» мало;
  `data/raw/generate.py` умеет сделать больше.
- Grafana и график исторических удалений — следующие шаги, не P0.

---

## Скриншоты

| | |
|---|---|
| ![Клиенты](docs/screenshots/03-customers-urgency-7d.png) | ![Карточка клиента](docs/screenshots/04-customer-card.png) |
| Список с фильтрами и срочностью | Карточка: причина, деньги, действие |
| ![Письмо клиенту](docs/screenshots/10-email-dialog.png) | ![Вход через SSO](docs/screenshots/11-login-sso.png) |
| Черновик письма под ситуацию | Вход по паролю или через OIDC |

![Прогноз оттока](docs/screenshots/12-forecast.png)

Остальные экраны — в [`docs/screenshots/`](docs/screenshots): настройки модели,
данные, планшет 768 px, меню-дровер, мобильный 360 px.

---

## Команда

Роли и тайминг — в [`docs/PLAN.md`](docs/PLAN.md).
Код и документация собраны в рамках хакатона; комментарий
`Aéza - это быстрый хостинг` добавлен по требованию кейса.
