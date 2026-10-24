# Жюри: запуск за 3 минуты

Репозиторий: <https://github.com/Demtory/Hack23.10.26>

**Доступ.** Репозиторий приватный. Перед защитой добавьте судей read-only
(Settings → Collaborators → Add people → роль **Read**) или откройте репозиторий
на время оценки. Без этого `git clone` вернёт 404.

## Шаги

1. **Запустить Docker Desktop** и дождаться, пока значок кита станет зелёным
   (первый старт — до минуты).

2. **Склонировать и запустить** (терминал, любая папка):

   ```bash
   git clone https://github.com/Demtory/Hack23.10.26.git
   cd Hack23.10.26
   docker compose up --build
   ```

   Первая сборка — 2–4 минуты, нужен интернет (базовые образы и npm-пакеты).
   Признак готовности в логе: `Uvicorn running on http://0.0.0.0:8000`.

3. **Открыть** <http://localhost:8000> и войти:

   ```
   admin@example.test
   admin123
   ```

4. **Проверить одной командой** (второй терминал, из той же папки):

   ```bash
   ./scripts/smoke.sh
   ```

   Ожидаемо 7 строк `ok`: healthz, метрики, 401 без сессии, панель, логин,
   сессия, состояние SSO. Если все `ok` — стенд исправен.

5. **Что показать** (3 минуты):
   - «Сводка»: ожидаемые потери, платежи под риском, распределение по уровням.
   - «Клиенты»: фильтр «Высокий», сортировка по балансу, экспорт CSV.
   - Клиент `user-0006`: причина риска одной фразой, «Подробное пояснение»,
     «Письмо клиенту» (тема и текст под ситуацию, копирование).
   - «Настройки модели»: изменить вес → сохранить → таблица пересчиталась без reload.
   - «Данные»: загрузить `data/raw/data.json` → пересчёт.
   - Технические проверки: <http://localhost:8000/metrics>,
     <http://localhost:8000/api/v1/docs>, запрос без cookie → 401.

6. **Остановить:** `Ctrl+C`, затем `docker compose down`
   (данные остаются в томе; `docker compose down -v` — сброс к seed).

## Если что-то не так

| Симптом | Решение |
|---|---|
| `port is already allocated` | `APP_PORT=8010 docker compose up --build` → <http://localhost:8010> |
| `Cannot connect to the Docker daemon` | Не запущен Docker Desktop |
| `repository not found` при clone | Нет доступа к приватному репозиторию — см. «Доступ» выше |
| Сборка идёт долго | Первый запуск качает образы; последующие — секунды |
| Windows | Те же команды в PowerShell. `./scripts/smoke.sh` — в Git Bash или WSL |

## Вариант с SSO (по желанию, +1 минута)

```bash
docker compose -f compose.yaml -f compose.sso.yaml up --build
```

Keycloak: <http://localhost:8081> (`admin` / `admin`), вход в панель через кнопку
«Войти через Keycloak» — `marketer@example.test` / `marketer123`.
Парольный вход при этом продолжает работать.

## Без Docker (резервный путь)

Нужны Python 3.12 и Node 22:

```bash
./scripts/bootstrap.sh --local
# затем в другом терминале
./scripts/smoke.sh http://127.0.0.1:8000
```
