# Implementation Plan: Корректность данных и согласованность интерфейса

**Branch**: `002-data-ui-consistency` | **Date**: 2026-10-24 | **Spec**: [spec.md](spec.md)

**Input**: `specs/002-data-ui-consistency/spec.md`, включая согласованный вариант A,
топ по q/level, amount>1000 и начальный вес нового признака0.

## Summary

Исправить семь групп дефектов поверх текущего приложения: отдельная строгая
денежная валидация; единые пороги и согласованный топ; действительный logout;
точные пояснения; безопасное расширение старых настроек; актуальная OpenAPI.
Переиспользовать существующие транзакции, score_runs/customer_scores, SQLite,
авторизацию, SSE/polling и UI. Не менять математические формулы и не реализовывать003.

Точечные изменения: исходный JSON передаётся без parse→stringify; GET/customers
аддитивно возвращает топ, глобальную сводку и контекст расчёта в одном read snapshot;
поколение признаков отдельно от пользовательской версии позволяет безопасно
дополнить настройки с весом0. Проектные решения и альтернативы — [research.md](research.md).

## Technical Context

**Language/Version**: Python3.12 (Docker/base и существующая тестовая среда),
TypeScript5.6, React18.3/Vite5.4; сохраняем существующие lockfiles/диапазоны.

**Primary Dependencies**: FastAPI0.161.1, Pydantic2.14.1, uvicorn0.54.0,
stdlib sqlite3. Новых runtime/dev зависимостей не требуется.

**Storage**: существующая SQLite/WAL. Одна аддитивная служебная колонка
settings.feature_schema_version; thresholds в существующем JSON summary score_runs.
Без ORM, новой таблицы миграций, фоновых очередей или смены БД.

**Testing**: pytest9.1.1/httpx0.28.1 из requirements-dev; временные SQLite
и существующие fixtures. Frontend — TypeScript/Vite build и поведенческие
браузерные проверки на изолированном APP_DB. Проверка OpenAPI полным сравнением JSON.

**Target Platform**: существующий Linux Docker-образ и локальная разработка.

**Project Type**: веб-приложение FastAPI + React с cookie/Bearer sessions.

**Performance Goals**: не загружать весь исходный снимок/все страницы ради топа;
SQL LIMIT5 и прежняя пагинация. Чтение — короткий snapshot, без блокировки писателя
через BEGIN IMMEDIATE. Новые SLA/масштаб50тыс/нагрузочные обещания не вводятся.

**Constraints**: только шесть входных денежных полей strict int0…signed64max;
сохранить нули, raw/demo, денежные единицы, округление, формулы и восемь сортировок.
Новые типовые отказы и расширение amount согласованы в spec; старые поля API сохранены.
Рабочие данные/секреты/внешние сервисы не трогаются.

**Scale/Scope**: семь групп ошибок и их интеграционные регрессии; набор12+ клиентов
для топа. Редизайн, CSV, срочность, сохранение контекста из003, OIDC, новая формула,
история и event bus вне объёма.

## Constitution Check

Gate пройден до Phase0 на основании scope и существующего стека; повторно проверен
после проектирования. PASS здесь означает соответствие плана, а не готовность исправлений.

| Принцип | До / после | Основание |
| --- | --- | --- |
| I: развитие прототипа | PASS / PASS | Прежние стек, расчёт, транзакции и UI |
| II: источники и допущения | PASS / PASS | Spec отделяет кейс, аудит и решения команды; research различает доказательства |
| III: ограниченный объём | PASS / PASS | Только002, без реализации003 и повторной реализации001 |
| IV: совместимость | PASS / PASS | Прежние пути/поля; описаны согласованные strict-вход и amount, дополнения ответа |
| V: согласованное состояние | PASS / PASS | Write transaction для upgrade/результатов, read snapshot для представления |
| VI: объяснения | PASS / PASS | Текст соответствует прежним формулам, floors/bonus/cap не меняются |
| VII: неизвестность/ноль | PASS / PASS | Ноль допустим, обязательность/null из001 сохранены, unknown не становится числом |
| VIII: честная модель | PASS / PASS | Пояснения без статистических обещаний; экономическая модель не пересматривается |
| IX: регрессии | PASS / PASS | Матрица воспроизведений, отказ/restart и совместимость включены |
| X: секреты/данные | PASS / PASS | Синтетика и временные базы, токены не пишутся в отчёт |

Одна новая колонка необходима для различения добавленного признака и повреждения
уже существующего ключа; это локальная эволюция хранения, а не смена архитектуры.
Исключений из конституции нет; нерешённых продуктовых вопросов нет.

## Project Structure

### Documentation (this feature)

```text
specs/002-data-ui-consistency/
├── spec.md
├── checklists/requirements.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/api.md
└── quickstart.md
```

`tasks.md` создаст следующая команда; сейчас его нет. 001/003, конституция,
AGENTS.md, рабочий код и текущий openapi.json в этой фазе не изменяются.

### Source Code (repository root)

```text
backend/app/
  schemas.py     # строгие деньги и DTO добавлений контракта
  api.py         # представление списка, effective metadata, resolver, OpenAPI auth
  store.py       # thresholds в run и согласованные SQL-представления
  db.py          # аддитивная служебная колонка и read transaction при необходимости
  seed.py        # upgrade settings и проверка сохранённых денежных входов
  main.py        # владение startup upgrade/recompute transaction
  scoring.py     # только декларации поколений/metadata; формулы сохраняются
  security.py    # существующее удаление сессии, изменения только при необходимости
backend/tests/
  test_api.py, test_snapshot_validation.py, test_atomic_updates.py
  test_scoring.py, test_explanations.py, conftest.py
  test_customer_views.py, test_auth_sessions.py
  test_settings_upgrade.py, test_openapi_contract.py   # будущие новые проверки
frontend/src/
  api.ts, types.ts, App.tsx
  pages/{Dashboard,Customer,Settings,Data}.tsx
scripts/export_openapi.py
openapi.json
README.md, docs/{MODEL,ARCHITECTURE,STATUS,CASE_BRIEF,DATA_NOTES}.md
```

**Structure Decision**: сохраняем текущие каталоги и функции. Небольшие DTO,
общая выборка q/level и общий выбор токена — необходимые локальные механизмы;
не создаём отдельные repository/service layers или универсальный migration framework.
Фактические названия новых тестовых файлов уточнятся в tasks, без дублей существующих тестов.

## Phase 0 — Research (завершено как проектирование)

[research.md](research.md) фиксирует решения по strict-валидации и передаче исходного
JSON, согласованному read-view, auth/OpenAPI OR и версионированию признаков.
В памяти исследованы Pydantic strict/bounds и FastAPI security alternatives.
Воспроизведения предыдущего аудита не выдаются за проверку будущего исправления.

## Phase 1 — Design и изменения по областям

### A. Денежные поля и транспорт — FR-001–FR-003, SC-001/SC-008

- schemas.py: MoneyCents с strict/ge/le в одном определении вместо комбинации
  SQLiteInt и отдельного Field. Убрать amount<=1000 только у приложения.
  Сохранить обязательность/null и остальные validators; ID не менять.
- api.py/main.py: переиспользовать безопасный422 handler и существующую полную
  PUT transaction. Не включать JSONResponse сериализацию после commit.
- Data.tsx/api.ts: новый текстовый путь PUT, отправляющий исходное file.text()
  без stringify разобранного объекта; прежний объектный helper сохраняется.
  GET/source текст сохраняется для точной загрузки/скачивания больших int.
  JSON.parse допустим для счётчиков/проверки массивов, но не как источник body.
- seed.py: новая загрузка seed проходит тот же строгий SnapshotIn. При startup
  уже сохранённые деньги проверять без int()-коэрции: исходный тип INTEGER,
  неотрицательность во всех шести колонках. Не ремонтировать их значениями по умолчанию.
  Несовместимое состояние даёт понятный отказ без raw-сумм, стирания или demo.
- Известные целые нули/false других полей остаются допустимы. Сохранённые целые
  после прежней коэрции не позволяют восстановить их исходное написание — это ограничение.
- Проверки: raw HTTP type matrix на каждом поле, bounds, нули/amount5000;
  отдельное отклонение переполненного производного результата с rollback/restart;
  браузерный upload100.0→422 и большой целый в PUT/GET/download без округления.

### B. Согласованный список, топ и пороги — FR-004–FR-007, SC-002/SC-003

- store.recompute сохраняет thresholds в JSON summary вместе с results/settings_version.
  Формулы scoring не меняются. DTO в schemas.py описывают CalculationContext,
  CustomerListItem/CustomerPage и добавление calculation к Summary.
- api.py/store.py: переиспользуем один конструктор q/level-условий и row→item;
  count/items/top/global summary читаются в явной BEGIN read-транзакции по одному run.
  _ensure_summary/fallback вызываются до неё; read SELECT не должны создавать
  скрытую write transaction. Params по-прежнему параметризованы, sort — из whitelist.
- Один ответ GET/customers получает topLosses/summary/calculation; top SQL сортируется
  по expected_loss DESC,id ASC и LIMIT5 независимо от page/sort. Никаких циклов по страницам.
- GET summary и summary ответов PATCH/PUT получают свой calculation из run;
  при mutation финальный payload/JSON валидируется до commit. Не читать current
  settings отдельно для подписи старого расчёта. Старый latest-cache без metadata
  корректно обновляется startup/fallback, не выдаётся с придуманными порогами.
- Dashboard.tsx принимает bundle как единое состояние, убирает отдельный независимый
  summary-fetch и локальный top из items; maxLoss берёт из topLosses. Отбрасывает
  запоздалые ответы на смене dependencies. Подпись порога использует calculation,
  подписи различают «все клиенты» и «текущая выборка».
- Customer.tsx использует service.level medium/high вместо >=40. Новые DTO детали
  для этого не требуются; backend уже возвращает её уровни из того же расчёта.
- Проверки: лидер ID12 вне страницы, q/level/сочетания, ties, ноль/<5 результатов,
  неизвестность, все page/sort варианты, два соединения с commit PUT между SELECT;
  medium80/high90 и три service70 дают0 в list/detail/UI, границы включительны.

### C. Серверный выход — FR-008–FR-009, SC-004

- api.py: общий resolver credential для require_user/logout, cookie имеет приоритет.
  logout без require_user сохраняет идемпотентность. security.delete_session уже
  удаляет выбранный token_hash и фиксирует отзыв; не реализовывать новый механизм.
- HTTPBearer(auto_error=False) и APIKeyCookie(auto_error=False) документируют OR.
  Для logout допускается {} и200 без токена; реальные защищённые операции требуют401.
- api.ts: убрать преждевременное удаление auth_token. App.tsx: очищать пользователя
  после подтверждённого logout, при отказе показать ошибку/повтор без ложного успеха.
- Проверки: cookie/Bearer и перекрёстное повторное применение token после выхода,
  restart, independent session, cookieA/BearerB, invalid-cookie/valid-Bearer,
  repeated/missing/expired; браузерный отказ POST сохраняет возможность повтора.

### D. Пояснения — FR-010, SC-005

- Settings.tsx точечно исправить формулу с масштабом100 и её границы применимости;
  различать долю веса, вклад value, услугу и max/bonus/cap клиента.
- Все шесть описаний сверить с scoring.py: funds_gap — одна цена, payment_history —
  наличие неоплаты, commitment — текущая экспертная пропорция; unknown не ноль,
  autoProlong не доказательство намерения уйти. Floors/добавка не отменяются весом0.
- При неизвестном для hardcoded front-справочника признаке сохраняется fallback
  title/description из metadata. Никакой новой визуальной системы и новых формул.
- Проверка контрольных чисел75/551, high78 при пустых drivers и тестов001;
  браузерное чтение пояснений с сопоставлением данным/дополнительным правилам.

### E. Аддитивное обновление настроек — FR-011–FR-013, SC-006

- db.py: новая служебная колонка и идемпотентное обновление schema старой базы,
  без сброса таблиц. Schema bootstrap/auth остаются до data transaction.
- scoring.py: фиксированное поколение1 и компактная декларация будущих добавлений.
  Объявление нового признака/веса требует явного перехода поколения; реальный
  новый фактор в этом этапе не добавляется.
- seed.py: чистая подготовка upgrade по известному исходному поколению; сначала
  проверить его обязательные ключи и все значения, затем дополнить только объявленные
  новые коды0 и валидировать цель. Существующий явный новый вес сохраняется.
  Неизвестное поколение/ключ и пропавший старый ключ — отказ, не setdefault/reset.
  Обычные GET/get_settings не запускают скрытый upgrade.
- main.py: в существующей startup transaction после подготовки актуальных данных
  и проверки сохранённых денег прочитать/обновить конфигурацию, сохранить поколение,
  payload, пользовательскую version+1/updated_at и пересчитать один раз. При переходе
  нескольких поколений одна итоговая версия; повторный startup не повторяет upgrade.
  Валидация результата, безопасное JSON и отказ commit до фиксации включены в rollback.
- Проверки: старая пользовательская база→синтетическое поколение2, 0 и явные веса,
  unchanged score/money при новом весе0, повторный startup, skipped generations,
  invalid configs, пустой сохранённый снимок, fault injection/второе соединение.

### F. Контракт и документация — FR-014–FR-016, SC-007/SC-008

- Штатно экспортировать openapi.json после реализации. Новые response DTO отражают
  реальные дополнительные поля; schema денежного типа имеет bounds и description
  об ограничении100.0; runtime-примеры обязательны из-за ограничений JSON Schema.
- Защищённые operations публикуют cookie OR Bearer, logout optional; проверить
  полное равенство сохранённого и генерируемого документа одной версии приложения.
- README/docs MODEL/ARCHITECTURE точечно описывают реальный способ добавления признака,
  служебное поколение, атомарность, top/filter scope, обе сессии и strict-деньги.
  CASE_BRIEF/DATA_NOTES уточняют различие исходного dataset amount0–1000 и расширенного
  загрузчика, не переписывают условия кейса/исходный SQL. STATUS сообщает только
  выполненное и подтверждённое. AGENTS/конституция/001/003 не редактируются.

## Риски и меры проверки

| Риск | Мера |
| --- | --- |
| Frontend нормализует100.0 или округляет int64 | Исходный/канонический текст, raw-body и upload/download regression |
| Неверные границы снова переопределены alias | Один MoneyCents, schema+runtime по всем шести позициям |
| Подмена неизвестности/нулей | Отдельные negative и positive сценарии, сохранение001 |
| Разные версии данных в одном UI | Один bundle/read snapshot, метаданные собственного run, cancelled responses |
| Upgrade скрывает повреждение | Явные поколения и миграции, строгая проверка старых ключей |
| Upgrade зафиксировал только настройки | Одна write transaction с results/serialization/commit и fault injection |
| Повторный restart повторяет upgrade | Отдельная схема признаков, идемпотентные metadata/version assertions |
| Старая база содержит отрицательное/REAL поле | Безопасное обнаружение, без ремонта/seed; проверка на временной базе |
| Logout сообщает успех без отзыва | Серверная token matrix и frontend-сбой с повтором |
| JSON Schema считает100.0 integer | Явное описание + HTTP tests, не ложная гарантия schema-only |

## Проверка и критерии выхода из реализации

Матрица и безопасный запуск — [quickstart.md](quickstart.md). Приёмка должна
покрыть все FR-001–FR-016 и SC-001–SC-008, включая прежние гарантии001.
Порядок будущей реализации: воспроизведения → деньги/транспорт (US1) →
согласованный bundle/пороги (US2) → logout (US3) → пояснения (US4) →
upgrade настроек (US5) → контракт (US6) → интеграционная проверка.
Зависимости внутри этого порядка оформит speckit-tasks; этот документ не tasks.md.

Достаточные проверки: целевые новые регрессии, весь backend/tests и generator tests,
frontend build, браузерные сценарии и сравнение OpenAPI; Docker smoke на отдельном
project/volume при наличии Docker. Новых тестовых зависимостей/обновления runtime
не вводим. Не запускать изменяющие данные проверки на рабочем app.db или .env.
Отмечать пропущенное явно, не выдавать наличие кода/плана за готовность.

## Complexity Tracking

Нарушений Constitution Check нет. Необходимая дополнительная сложность ограничена
одной колонкой поколения, небольшими DTO/общими функциями выбора токена и фильтра,
одним согласованным SQL read-view. Более сложные альтернативы отклонены в research.

## Статус подготовки

Phase0/Phase1 документы созданы, gate повторно пройден. Подтверждены исследовательские
поведения библиотек и ранее воспроизведённые исходные ошибки; новые исправления
не реализованы. Тесты приложения/сборка в фазе plan не запускались, рабочая база
не открывалась. Следующий шаг — `$speckit-tasks` только для002.
