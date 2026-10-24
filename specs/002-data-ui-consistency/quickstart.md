# Quickstart Validation: 002

Сценарии проверки реализованной002; фактические результаты приведены в docs/STATUS.md.
Не использовать рабочую базу/.env.

## 1. Изолированная среда

Из корня репозитория, в ветке002; окружение Python3.12 и зависимости по README
(`backend/requirements-dev.txt`), Node и установленные frontend зависимости.
Ниже TASK_PYTHON указывает на имеющуюся .venv; при другом окружении заменить только его.

```bash
TASK_PROJECT="/Users/vlad/vibecode_codex/vaibaton-prohodnaya-current/Hack23.10.26"
TASK_VERIFY_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/risk-desk-002.XXXXXX")"
TASK_PYTHON="$TASK_PROJECT/.venv/bin/python"
export APP_DB="$TASK_VERIFY_ROOT/app.db"
export SEED_PATH="$TASK_PROJECT/data/seed.json"
export SEED_META_PATH="$TASK_PROJECT/data/seed.meta.json"
export AS_OF="2026-10-23T18:00:00.000Z"
export SEED_ON_START=true
export ADMIN_EMAIL="admin@example.test"
export ADMIN_PASSWORD="admin123"
export PYTHONDONTWRITEBYTECODE=1
```

Демонстрационные credentials выше только для временной среды. Не подставлять
рабочие токены/пароли в отчёты. Сохранить TASK_VERIFY_ROOT для повторного запуска
той же тестовой базы; не удалять volume/данные рабочего приложения.

## 2. Автоматические проверки

```bash
PYTHONPATH="$TASK_PROJECT/backend" "$TASK_PYTHON" -m pytest -q -p no:cacheprovider "$TASK_PROJECT/backend/tests" "$TASK_PROJECT/data/raw/test_generate.py"
npm --prefix "$TASK_PROJECT/frontend" run build
```

Новые проверки используют tmp_path/собственный Config, не APP_DB рабочего проекта.
Требуется полный итоговый прогон после целевых регрессий; отсутствие теста не
засчитывается как успех. Ошибки/пропуски перечислить отдельно.

Для OpenAPI сначала после реализации обновить штатный openapi.json:

```bash
PYTHONPATH="$TASK_PROJECT/backend" "$TASK_PYTHON" "$TASK_PROJECT/scripts/export_openapi.py"
```

Экспорт меняет файл контракта, не запускает lifespan/рабочую БД. Отдельный
контрактный тест должен сравнить полный JSON с create_app().openapi(), DTO,
minimum/maximum/description, cookie OR Bearer и optional logout. Не полагаться
на один schema-validator для написания100.0.

## 3. Поведенческая матрица приёмки

| Проверка | Ожидаемый результат | Связь |
| --- | --- | --- |
| Каждое из6 money fields: −1,bool,string100,raw100.0,1e2,100.5,null/missing,overflow | 422 с полем, без частичного применения; restart и следующий корректный PUT успешны | US1, SC-001 |
| Целые0/100 и amount1000/1001/5000; верхняя граница входа отдельно от derived overflow | Допустимые входы проходят, производный отказ откатывает всё | US1, SC-001/008 |
| Upload JSON c100.0; upload/download int>2**53 | 100.0 получает422 и через браузер; большой целый хранится/передаётся/скачивается точно | US1, SC-001 |
| medium80/high90, три score70; значения точно на границах и unknown | list/detail/UI согласованы:0 рискованных услуг для70; подписи актуальны | US2, SC-002 |
| 12+ клиентов, лидер вне score-страницы; q/каждыйlevel/сочетания/ties/0/<5 | top равен независимому полному ранжированию, не зависит от page/sort | US2, SC-003 |
| Два соединения: writer PUT/PATCH между чтениями bundle; delayed UI responses | parts одного run/снимка, нет старого топа поверх нового фильтра | US2, SC-002/003 |
| Cookie/Bearer logout и повторное использование обоими способами после restart | 401 по отозванному токену; независимая сессия жива | US3, SC-004 |
| cookieA+BearerB, invalid cookie, missing/expired/repeated logout | Приоритет и безопасный200 сохранены; только выбранная сессия отозвана | US3, SC-004 |
| POST logout отказал в браузере | Нет ложного выхода, текущий токен не удалён до подтверждения, доступен повтор | US3, SC-004 |
| Шесть пояснений, status/stale floors, bonus/cap, пустые drivers | Текст соответствует модели, контроль75/551 и high78 сохранены | US4, SC-005 |
| Временная база прошлого поколения + синтетический новый признак | Вес0, старые настройки/снимок/score/деньги сохранены; restart без повторного upgrade | US5, SC-006 |
| Явный новый вес, missing старый/текущий ключ, unknown key/version, NaN/negative | Явный вес сохранён; повреждение не маскируется defaults | US5, SC-006 |
| Fault после save/compute/response и commit до фиксации, чтение со второго соединения | Старое либо новое согласованное состояние; при отказе rollback и успешный повтор | US1/US5, SC-001/006 |
| Повреждённая сохранённая money колонка, пустой принятый снимок | Безопасный отказ без ремонта; пустой валидный снимок не заменяется seed | US1/US5, SC-008 |
| Приложенный vs живой OpenAPI, cookie/Bearer actual requests | Документы равны, OR не AND, старые пути/поля/единицы работают | US6, SC-007 |
| Raw/demo,8 сортировок, settings persistence, explanations/unknown, live update | Гарантии001 сохранены; обновления без reload | SC-008 |

Фиксировать исходное воспроизведение и результат после исправления. Тест для100.0
должен отправлять literal raw body: json={value:100.0} допустим только если сериализатор
сохраняет float; браузерная проверка обязательна из-за прежней parse→stringify цепочки.
Не проверять UI регулярными выражениями по исходникам вместо поведения.

## 4. Запуск UI на временной базе

После frontend build, в том же терминале с изолированными переменными:

```bash
PYTHONPATH="$TASK_PROJECT/backend" "$TASK_PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8124
```

Открыть http://127.0.0.1:8124, войти demo-пользователем. Рабочий сервис не
перезапускать. Проверить:

1. На временном наборе12+ топ/фильтры/страницы и надписи глобальных карточек.
2. Сохранить medium80/high90 и сравнить клиента с service70; затем вернуть defaults
   только на тестовой базе. В другом окне увидеть обновление без reload.
3. Загрузить полный raw/demo, raw100.0 и целыйamount5000; ошибка не меняет данные.
   Скачать подтверждённый снимок и независимо проверить большие целые.
4. Прочитать новые пояснения; сравнить реальные эффекты минимальных правил и добавки.
5. Успешно выйти; отдельно имитировать отказ logout и проверить отсутствие ложного успеха.
6. Остановить только этот процесс, запустить с тем же APP_DB; проверить сохранение
   настроек/данных и отсутствие повторного upgrade. RunId/время расчёта могут измениться.

## 5. Docker smoke при доступном Docker

Использовать отдельный временный compose-файл, уникальный project name/порт и
собственный volume; build context — текущая реализация проекта. Не брать рабочую .env.
Можно адаптировать следующий исключительно проверочный setup:

```bash
cat > "$TASK_VERIFY_ROOT/compose.yaml" <<EOF
services:
  app:
    build:
      context: $TASK_PROJECT
    ports:
      - "127.0.0.1:18024:8000"
    environment:
      APP_DB: /data/app.db
      SEED_PATH: /app/data/seed.json
      AS_OF: "2026-10-23T18:00:00.000Z"
      ADMIN_EMAIL: admin@example.test
      ADMIN_PASSWORD: admin123
    volumes:
      - check-data:/data
volumes:
  check-data:
EOF
docker compose -p risk-desk-002-check -f "$TASK_VERIFY_ROOT/compose.yaml" up -d --build
```

На http://127.0.0.1:18024 проверить health/login/401 без входа, raw5000, настройки,
метрики и документацию; restart только этого compose project и повторное чтение.
Завершить только собственный проверочный проект:

```bash
docker compose -p risk-desk-002-check -f "$TASK_VERIFY_ROOT/compose.yaml" down --volumes
```

Если имя/порт уже используются чужой проверкой — выбрать другое имя/порт,
не останавливать чужой проект. При недоступности Docker/network записать ограничение;
это не даёт права считать smoke пройденным.

## 6. Финальный отчёт

Указать выполненные задачи/проверки, количество passed/failed/skipped, результаты
браузера и Docker, невозможные проверки с причиной, остаточные ограничения.
Проверить git diff --check и состав изменений. Не коммитить/пушить/мерджить автоматически.
Проверки миграций и сессий не должны печатать сырые токены или рабочие данные.
