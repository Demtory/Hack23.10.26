# Quickstart validation:003

Инструкция для ПОСЛЕ реализации. Сейчас новые scripts/tests/контракты ещё не
существуют; этот документ не утверждает, что они проходят. Baseline002 записан
в docs/STATUS.md. Рабочие БД/.env/volume и внешние сервисы не использовать.

## 1. Предпосылки и изоляция

Ветка003-marketer-panel, активная003. Python3.12 с requirements-dev изREADME,
Node>=20 и зависимости по согласованному package-lock после implement.
Новый router и test runner устанавливаются при реализации, не на этапе plan.
Оба шрифта лицензированы и локальны, материалы знака имеют provenance. Указать путь к подготовленному Python environment:

```bash
TASK_PROJECT="/Users/vlad/vibecode_codex/vaibaton-prohodnaya-current/Hack23.10.26"
TASK_PYTHON="$TASK_PROJECT/.venv/bin/python"
TASK_VERIFY_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/risk-desk-003.XXXXXX")"
export APP_DB="$TASK_VERIFY_ROOT/app.db"
export SEED_PATH="$TASK_PROJECT/data/seed.json"
export SEED_META_PATH="$TASK_PROJECT/data/seed.meta.json"
export AS_OF="2026-10-23T18:00:00.000Z"
export ADMIN_EMAIL="admin@example.test"
export ADMIN_PASSWORD="admin123"
export PYTHONDONTWRITEBYTECODE=1
```

Демонстрационные credentials относятся только к временной среде. Не печатать токены.
APP_DB из рабочего окружения не переиспользовать. При занятом тестовом порте выбрать
другой и согласовать baseURL; не останавливать чужой процесс.

## 2. Автоматические проверки после реализации

```bash
PYTHONPATH="$TASK_PROJECT/backend" "$TASK_PYTHON" -m pytest -q -p no:cacheprovider "$TASK_PROJECT/backend/tests" "$TASK_PROJECT/data/raw/test_generate.py"
npm --prefix "$TASK_PROJECT/frontend" ci
npm --prefix "$TASK_PROJECT/frontend" run build
PYTHONPATH="$TASK_PROJECT/backend" "$TASK_PYTHON" "$TASK_PROJECT/scripts/export_openapi.py"
```

Экспорт обновляет contract file, не запускает lifespan/рабочуюБД. После экспорта
повторить целевой test_openapi_contract.py и сверить полный JSON с live schema.
Backend fixtures обязаны создавать свои tmp_path DB, включая restart/ошибки записи.

После добавления script/config при implement:

```bash
npm --prefix "$TASK_PROJECT/frontend" exec playwright install chromium
TASK_PYTHON="$TASK_PYTHON" npm --prefix "$TASK_PROJECT/frontend" run test:e2e
```

E2E config запускает собственный server через e2e/start-test-server.py с
TemporaryDirectory/APP_DB и demo seed; workers1, reuseExistingServer:false,
например127.0.0.1:8130. Перед каждым тестом fixture восстанавливает synthetic
source/settings только этого сервера; browser context изолирован. Cleanup завершает
только свой server и tempdir. Нельзя подменить baseURL рабочим приложением ради удобства.
Зависимости browser engines ставятся только для тестовой среды. При недоступности
Chromium не отмечать E2E/соответствующие критерии готовыми.

## 3. Обязательная backend матрица

| Сценарий | Ожидание |
|---|---|
| Срок now,+48ч,+7д и±1ms, разные timezone на входе | Строгое попадание по run.asOf; точкаnow —expired, границы48ч/7д включены |
| Active/suspended/prolong_wait vsdeleted/blocked, несколько услуг | Правильная совокупность EXISTS без дублей; all не меняет прежнюю модель |
| Unknown с исходной активной услугой и пустым scored services | Проходит срочность+unknown, не становитсяlow |
| q+level+urgency,8 обязательных направлений иscore/loss | Фильтр доpage, топ/total/CSV совпадают с независимым полным ожиданием; ties поid |
| CSV >1 страницы, большие деньги/ID,0/NULLscore/unknown | Полные строки и точные decimal bytes; метаданные едины, unknown не0score |
| CSV кириллица/quotes/comma/CRLF,=,+,-,@/full-width/control/email/q/text: | csv parser и text:-декодирование корректны, поля не становятся формулами |
| Writer PATCH/PUT между чтениями, устаревший runId | Один pinned snapshot либо409; не смешанныйCSV/detail/source context |
| Два guarded save одной baseVersion | Один200, другой409; отказ не меняет payload/time/version/runs/results |
| Legacy PATCH, null-omission, invalid expectedVersion | Прежняя совместимость; legacy изменяетversion; старый новый-UIdraft получает409 |
| Валидация/расчёт/serialization/commit отказ иrestart | Гарантии001/002 сохранены,75/551 иhigh78 без изменений |
| Cookie/Bearer/401, logout и независимая сессия | Прежние гарантии002, CSV защищён, OpenAPI отражает новые ответы |

## 4. Браузер и визуальная приёмка

Для ручной проверки запустить отдельный server с APP_DB израздела1:

```bash
PYTHONPATH="$TASK_PROJECT/backend" "$TASK_PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8131
```

Открыть127.0.0.1:8131/#/overview, demo login. Использовать synthetic набор >1 страницы.

1. Сводка → клик уровня → список → карточка → UI Back/Browser Back/Forward.
   Проверить поиск/уровень/срочность/сортировку/page2/scroll/focus, прямой hash,
   reload, удалённого клиента и уменьшившееся число страниц. После logout/входа
   другим пользователем Browser Back не восстанавливает предыдущие условия/фокус;
   проверить также новый вход того же пользователя после завершённой сессии.
2. В разделе «Клиенты» count/table/top/CSV относятся к одной выбранной группе.
   KPI и оба графика «Сводки» остаются глобальными. Проверить chips/reset,
   отсутствие истории, delayed response и ошибку нового фильтра.
3. CSV на наборе больше страницы: захваченные условия/порядок, смена фильтра в процессе,
   stale run/refetch/retry,401/обрыв без частичного файла. Независимый parser проверяет
   9007199254740993 и max int64; доступный редактор — формулы, кириллицу и save/reopen.
   Большие числа/ID импортировать как текст. Непроверенный редактор не считать успехом.
4. Настройки в двух вкладках: dirty/reset, stay/discard через sidebar/Back/logout.
   Сохранить в другой вкладке и попытаться применить старый draft:409 без потери правок.
   Потеря ответа после commit — uncertain, без автоматического rebase/retry.
5. Карточка: правила услуги/клиента, пустые drivers, unknown, price0, hour, точное
   время/часовой пояс. Settings/Data не выдают время расчёта за неизвестную дату источника.
6. На каждом экране загрузка/пустота/нет совпадений/ошибка/повтор. SSE отказал,
   polling успешен; затем полный отказ/восстановление.401 скрывает защищённые данные.
7. Только клавиатура: links, сортировки, фильтры, диалог/drawer, Save/CSV/logout.
   Escape и возврат фокуса, без ловушек.1440/1024/768/360px и200% текста: действия
   доступны, таблица прокручивается локально, вся страница не переполнена.
8. Screenshots всех6 экранов на1440/360px и настоящих focus/error/loading/dirty/conflict
   состояний. Измерить actual computed contrast/font, сверить contracts/ui.md и brand.md.
   Проверить Exo 2 как основной и Inter как дополнительный: фактические загруженные
   файлы/кириллица/начертания и fallback при отказе, отсутствие runtime CDN.
   Сверить голубой #4CC6F1, чёрный #000000, фон #F4F4F4, дополнительные цвета,
   оригинальные монохромные знаки/favicon и manifest, поле 30 CSS px, отсутствие
   искажений/эффектов, заливные иконки. Голубые кнопки имеют тёмный текст.
   При 360 px/200% текста поле сохраняется, меню/действия доступны; паттерн не под данными.
   Непроведённую ручную сверку оригинального знака не заменять автоматическим PASS.
9. SC-001:3 участника без подсказок проходят сценарий за2мин каждый. При их отсутствии
   критерий «не проверено», а не «выполнено агентом».

## 5. Упаковка и отчёт

Собрать текущий Dockerfile через отдельный проверочный compose с собственными
project/портом/volume, без рабочей .env. Среда аналогична002 quickstart, но project
risk-desk-003-check и другой свободный localhost порт. Проверить root/hash/login/CSV,
контракты/metrics/settings и persistence после restart. Удалить только собственные
проверочные ресурсы. Рабочий compose и его volume не использовать для проверки записи.

В docs/STATUS.md при implement записать фактические passed/failed/skipped,
команды и среду, screenshots/контраст, результаты офиса/участников, ограничения.
Сверить diff/AST формул и защищённые001/002/spec/constitution/AGENTS/seed/raw,
секреты/dependencies/lockfile и git diff --check. Без запроса не коммитить/push/merge.
