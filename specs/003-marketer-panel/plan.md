# Implementation Plan: Панель маркетолога: понятный риск и приоритет действий

**Branch**:003-marketer-panel | **Date**:2026-10-24 | **Spec**:[spec.md](spec.md)
**Input**: уточнённая003, включая ответА: устаревший черновик не перезаписывает
новую версию настроек, его локальные значения сохраняются до явного отказа.

## Summary

Развить текущий интерфейс в последовательность «Сводка → Клиенты → Карточка»
со стилем Aéza и организацией аналитической работы по референсу Метрики.
Переиспользовать таблицу/графики/объяснения/формы002, разделив сводку и работу с выборкой.
Добавить срочность и CSV, сохранение контекста, честные состояния и защиту черновика.
Никаких изменений compute/денежных формул/балансов, истории, OIDC, CRM и saved segments.

Подход: собственный CSS/небольшие компоненты, self-host Exo 2 + Inter, hash data router,
один frontend E2E framework. Backend — небольшие совместимые расширения query,
CSV, контекста времени и expectedVersion в существующих read/write-транзакциях.
[research.md](research.md) фиксирует решения/альтернативы/источники; это план,
а не заявление о реализованном интерфейсе или пройденных будущих проверках.

## Technical Context

**Language/Version**: Python3.12, TypeScript5.6, React18.3/Vite5.4 как в проекте.
**Primary Dependencies**: FastAPI0.161.1, Pydantic2.14.1, uvicorn0.54.0,
stdlib sqlite3/csv/datetime/unicodedata; React/react-dom и существующий CSS.
Планируется только react-router-dom7.18.4 runtime и @playwright/test1.64.1 dev.
Metadata/engines проверены в исследовании: Node>=20/React>=18; локальныйNode24.21,
Docker node22 подходят. При implement зафиксировать exact versions в lockfile,
проверить peers/engines, без @latest/обновлений прочих dependencies.
**Storage**: прежняя SQLite/WAL, без SQL migrations; transient route/list/draft
state в памяти текущего пользователя/history state. Нет бессрочного хранения вlocalStorage
кроме прежнего auth token механизма; его перенос/замена не входят в003.
**Testing**: pytest/httpx из существующего requirements-dev; новые целевые backend
регрессии; tsc/Vite; Playwright Chromium с isolated server/DB; ручная доступность,
контраст, screenshots и3 участника дляSC-001. Другие browser engines — smoke по доступности.
**Target Platform**: существующий браузерный frontend и один FastAPI/Docker origin;
1440/1024/768/360px,200% текста, клавиатура. Не предполагается IE/старый browser runtime.
**Project Type**: существующее fullstack web-приложение, без нового scaffold.
**Performance Goals**: пользовательский путьSC-001 за2мин; серверные фильтры до pagination,
один read snapshot/выборка наCSV, безN+1 и выгрузки source ради списка. Latency/10k+
не обещаются без измерений; записать реальное время/размер экспорта на проверочном наборе.
**Constraints**: formulas/API compatibility/001/002; данные записывать только во временные
БД, secrets/external services не менять. Явное отображение unknown, heuristic money,
разницы source date/asOf/calculatedAt; никаких вымышленных трендов.
**Scale/Scope**:6 экранов,2 смысловых графика,23FR/10SC, все текущие scenarios.
Набор для функциональной приёмки >1 страницы и разнообразные edgecases, не обещание capacity.

## Constitution Check

Gates проверены до исследования и повторно после дизайна. PASS здесь означает
согласованность проектного решения с правилами, не подтверждение его работы.

| Принцип | Gate до/после дизайна |
|---|---|
| I. Существующий прототип | PASS/PASS: React/FastAPI/SQLite и рабочие модули сохраняются; router добавляет необходимую историю, не меняет стек |
| II. Требования/допущения | PASS/PASS: CSV/urgency/визуал — решения пользователя; эвристики и референсы отделены от кейса |
| III. Ограниченный объём | PASS/PASS: только003, без повторной реализации002/новых формул/следующих этапов |
| IV. Совместимость | PASS/PASS: optional urgency/expectedVersion, additive detail/headers, отдельныйCSV; old PATCH иrawsource сохранены |
| V. Согласованное состояние | PASS/PASS: pinned reads, guarded settings transaction,409/uncertain без ложного отката/успеха |
| VI. Объяснения | PASS/PASS: прежние drivers/rules сохраняются и показываются по уровням service/customer |
| VII. Unknown≠0 | PASS/PASS: NULLscore/unknown/dateunknown отличены от известного0; исходный снимок не меняется |
| VIII. Честный смысл | PASS/PASS: completeness≠accuracy, money heuristic, без общей месячной суммы/ложной истории |
| IX. Регрессии | PASS/PASS: проверкиAPI/UI/доступности и сохранение380baseline-гарантий запланированы; результаты только после выполнения |
| X. Секреты/ПД | PASS/PASS: только synthetic/tmp; export защищён прежнейauth; рабочиеcredentials не используются |

Новых существенных продуктовых неоднозначностей не осталось. Все исследовательские
решения отражены в research/data-model/contracts. Чек-лист spec00316/16 сохранён.
Новые зависимости обоснованы ниже; installation/код/задачи не выполняются при plan.

## Project Structure

### Documentation (this feature)

```text
specs/003-marketer-panel/
  spec.md                      # уже уточнён, не переписывается этим plan
  checklists/requirements.md   # существующая проверка требований
  plan.md                      # порядок и scope
  research.md                  # решения/альтернативы/источники
  data-model.md                # состояния, выборки, draft/restore/export
  contracts/api.md             # совместимые контракты
  contracts/ui.md              # компоновки, токены, UX/приёмка
  contracts/brand.md           # брендбук, страницы, материалы и правила
  quickstart.md                # проверка ПОСЛЕ реализации
```

tasks.md составлен на этапе $speckit-tasks с учётом брендбука. Все задачи
плановые и не выполнены; бренд обновляет только документы003.

### Source Code (планируемые точечные изменения)

```text
backend/app/
  api.py                       # общий filter/order, urgency/CSV, version guard, read contexts
  schemas.py                   # expectedVersion и additive view/ошибки/CSV OpenAPI
  store.py                     # небольшой read helper только при необходимости
backend/tests/
  conftest.py                  # переиспользовать tmp fixtures, расширить только пробелы
  test_customer_urgency.py      # новый: интервалы/полная совокупность/unknown
  test_customer_export.py       # новый: CSV/точность/авторизация/конкурентные reads
  test_settings_conflicts.py    # новый: guarded/legacy/race/rollback
  test_atomic_updates.py       # существующие гарантии + контекст детали/source
  test_customer_views.py       # сохранить coherent bundle002
  test_openapi_contract.py      # сохранить equality, новые optional contracts
frontend/
  package.json / package-lock.json  # только2 обоснованные dependencies/scripts
  playwright.config.ts         # новый isolated E2E config, workers1/reuseExistingServer:false
  e2e/
    start-test-server.py        # новый маленький wrapper: TemporaryDirectory/APP_DB/cleanup
    fixtures.ts                # synthetic snapshots, reset/логин только test API
    navigation.spec.ts         # Back/Forward/restore/уменьшение набора
    settings.spec.ts           # dirty/conflict/uncertain/две вкладки
    customers-export.spec.ts   # фильтры/urgency/CSV/delays
    states-accessibility.spec.ts # связь/401/keyboard/ширины/overflow
    brand.spec.ts              # реальные шрифты/логотип/поле/палитра/favicon
  public/fonts/Exo2Variable.woff2 / InterVariable.woff2 / Exo2-OFL.txt / Inter-OFL.txt
  public/brand/                # оригинальные варианты знака, паттерн, asset-manifest.json
  public/favicon.svg           # настоящий компактный знак из брендбука
  src/
    main.tsx                   # RouterProvider
    routes.tsx                 # hash data router, auth/protected routes
    App.tsx                    # layout, sidebar/drawer, auth/logout/guards
    api.ts / types.ts          # typed conditions/errors/precondition/Blob/source headers
    styles.css                 # tokens/components, без Tailwind/CSS framework
    components/ui.tsx          # reuse/малые primitives +native Dialog
    components/BrandLogo.tsx / BrandIcon.tsx
    components/ClientFilters.tsx
    components/CustomerTable.tsx
    components/RiskCharts.tsx   #2 существующих графика, props вместо fetch
    components/CalculationContext.tsx
    hooks/useLiveUpdates.ts
    hooks/useViewRestoration.ts
    state/ClientContext.tsx
    state/SettingsDraft.tsx     # applied/base/draft/guard states, без server persistence
    pages/Dashboard.tsx         # сводка из существующего компонента
    pages/Customers.tsx         # таблица/фильтры/CSV из Dashboard, без дублирования
    pages/Customer.tsx / Settings.tsx / Data.tsx / Login.tsx
scripts/export_openapi.py       # использовать без изменений, если не найден дефект
openapi.json / README.md / docs/STATUS.md
```

Файлы новых компонентов — границы ответственности, не требование создавать пустые
абстракции. Малые primitives остаются вui.tsx; hooks/providers не дублируют один state.
В docs/MODEL.md только необходимые подписи/интерпретация, не переписывать формулы.
Не менять AGENTS, конституцию и артефакты001/002. Изменения backend минимальны и
нужны для новых фильтров/CSV/предусловия/достоверного времени, не рефакторинг всего сервера.

## Phase 0 — Research (выполнено как проектирование)

Результат research.md: проверена фактическая структура, оцененыshadcn/router/test
dependencies, определены точные server filtering/CSV/version contracts и UI states.
Новых библиотек иassets пока не установлено. Aéza повторно не прочиталась черезweb;
предыдущее направление сайта не выдаётся за новый просмотр. Полученный затем
брендбук пользователя изучен; правила/страницы и приоритет зафиксированы в contracts/brand.md.

## Phase 1 — Design & Contracts (результат этого plan)

### A. Навигация и сохранение контекста

Hash routes login/overview/customers/customers/:id/settings/data без backend fallback.
ClientContext выше сменяемых страниц; query/page/sort и restore point в памяти/history
state. Card открывается через link сorigin/location.key/customerId; UI Back иBrowser
Back/Forward возвращают реальную history. После появления данных восстановить scroll
и горизонтальную прокрутку таблицы, затем focus поid; при удалении клиента/page — корректировать предсказуемо, не поиндексу.
Страница/фильтры replace текущую запись, не засоряют историю каждой буквой.
useBlocker +native dialog дляSPA, beforeunload длязакрытия/reload; logout проверяет
несохранённость ДО POST, а при ошибке сервера не очищает пользователя002.
Restore point проверяет ownerUserId/viewSessionId до восстановления из history.state;
после logout/нового входа чужие или завершённые записи игнорируются. Auth token
в истории не хранится. Подробные переходы — data-model.md иcontracts/ui.md.

### B. Облик и компоненты

Exo 2 основной, Inter дополнительный; оба локальные, полные, с кириллицей и лицензиями.
Брендбук задаёт голубой #4CC6F1, чёрный #000000, фон #F4F4F4 и дополнительные цвета.
Подлинные монохромные SVG/компактный знак, поле 30 CSS px, заливные иконки и
умеренный паттерн следуют contracts/brand.md. Материалы берутся из утверждённых
векторов или точно экспортируются из PDF; не имитируются текстом/новой отрисовкой.
Служебные токены и контрастные пары определены в UI-контракте. Голубая кнопка
имеет тёмный текст; шрифт/логотип проверяются на фактическом рендере. Тёмные inline styles Settings заменяются классами:
одной смены root palette недостаточно. Badges/formatters/rules переиспользуются.

На сводке: KPI → распределение и топ потерь → переход к списку. На экране клиентов:
условия/chips → топ выбранной группы → таблица. На360/768px — drawer, одна колонка
и локальная прокрутка таблицы; на1024/1440px — плотная аналитическая компоновка.
shadcn/Tailwind не вводятся: существующие CSS/native controls закрывают выбранный
объём без дополнительной системы стилей. Это не утверждение о несовместимости shadcn.

### C. Общая совокупность и время

Backend использует общий WHERE/order для списка, топа и CSV. Срочность — EXISTS
по исходным services относительно asOf выбранного run. Границы0/48ч/7д, статусы
и unknown следуют спецификации; прежняя семантика q/level сохраняется.
Summary/metrics глобальные, топ клиентов явно подписан как выбранная группа.

Контекст времени детали читается с detail одной read-транзакцией. Заголовки source
не меняют raw JSON. Нельзя объединять независимые detail/source и summary разных
версий. Дата формирования источника неизвестна. Показывать часовой пояс и различать
asOf, время расчёта и получения. Срок менее суток не сводить только к «0 дней».

### D. CSV

Сервер выгружает всю выборку в порядке таблицы: captured query/run и один read snapshot,
без JS-пагинации/JSON float. Проверка runId предшествует JOIN источника; если run уже
неактуален —409. Полные bytes доHTTP200, полный Blob до скачивания, без частичного успеха.

Один header, UTF-8 BOM/CRLF/comma; метаданные повторены столбцами. EUR форматируются
точно из INTEGER cents. Опасный текст обратимо кодируется text:, обычный email остаётся
прежним; money/ID не представлены формулами. Нужны parser и проверка редактора.
Большие числа импортируются как текст; универсальное автоопределение типов всеми
редакторами не обещается. Контракт и примеры границ — contracts/api.md.

### E. Настройки и связь

На время saving все редактируемые поля заблокированы, чтобы ответ не затёр новые правки.
Новый UI всегда отправляет expectedVersion=baseVersion; сервер проверяет его внутри
BEGIN IMMEDIATE до изменений.409 сохраняет черновик и актуальные результаты;
автоматический rebase и принудительная перезапись запрещены ответомА.
Legacy PATCH без поля совместим; гарантия условности не приписывается старым consumers.

При обрыве ответа — uncertain: перечитать актуальное состояние, не обещать откат
или успех своего запроса по одному равенству значений; автоматического повтора нет.
Новая база загружается только с подтверждением отказа от черновика.

useLiveUpdates выделяет прежние SSE/15-секундный polling, реальные ответы HTTP
определяют свежесть. Проверка сессии нужна и при открытом SSE;401 скрывает защищённые
данные и останавливает поток. Не создавать server scheduler и не менять механизм сессий.

## Порядок будущей реализации

Подробные зависимости и критерии — [tasks.md](tasks.md); задачи пока не выполнялись.

1. Baseline001/002, изолированная среда и подлинные бренд-материалы.
2. Общий транспорт, токены Exo 2/Inter и голубой палитры, компоненты, layout/router.
3. US1: глобальная сводка и два смысловых графика — первый демонстрируемый срез.
4. US2: общий backend filter/urgency и список с восстановлением контекста.
5. US3: coherent detail/source context, карточка и объяснения.
6. US5: conditional settings transaction, draft/guard, данные и ошибки операций.
7. US6: связь/401, состояния экранов и доступность основных сценариев.
8. US4: серверный CSV полной группы и браузерное скачивание.
9. Полная регрессия001/002, OpenAPI, сборка, браузерная/визуальная приёмка и отчёт.

В каждой истории сначала содержательная проверка нового пробела, затем изменение
и независимая приёмка. Общие api.py/schemas.py/api.ts/styles.css меняются последовательно;
независимые backend/browser тесты можно готовить параллельно после их предпосылок.

## Verification Strategy / покрытие

| Требования | Основные файлы и содержательная проверка |
|---|---|
| FR-001–003;SC-001/004 | App/routes/Dashboard/RiskCharts: KPI/графики → группа → карточка, реальные значения и text alternatives;3 участника за2мин |
| FR-004–008;SC-002/003 | ClientContext/Customers/API: AND, границы±1ms, unknown/статусы/дубли,8 сортировок, pagination/Back/scroll/focus |
| FR-009–011;SC-005/009 | Customer/ui/CalculationContext/DTO: floors/bonus/cap, пустые drivers, price0, почасовая услуга, неизвестная дата/timezone |
| FR-012–014;SC-007 | SettingsDraft/Settings/Data/PATCH: dirty/reset/stay/discard,2 редактора,409/uncertain/422/500/restart/raw integer JSON |
| FR-015–016;SC-006 | CSV/API client/E2E: вся выборка >page, сортировка/ties/metadata, точные cents, unsafe email/q, BOM/CRLF/401/обрыв/stale run |
| FR-017–018;SC-009 | useLiveUpdates/api/App: loading/error/empty, SSE отказ+успешный polling, offline/recovery/401/запоздалые ответы |
| FR-019–021/023;SC-008/010 | CSS/primitives/6 экранов: keyboard/dialogs/labels, контраст actual styles,4 ширины/200%, оба шрифта, подлинные SVG/favicon/поле и screenshots |
| FR-022;SC-007–010 | Существующие001/002 проверки, OpenAPI/metrics/auth/build/Docker: формулы и API совместимы |

Команды и сценарии — quickstart.md. Автотесты не подтверждают SC-001 с людьми или
универсальную совместимость офисных программ. Один screenshot не доказывает WCAG.

## Риски и меры

| Риск | Мера и проверка |
|---|---|
| Незаметная смена модели при разделении экранов | scoring/seed/db/security не планируются к правке; прежние75/551 иhigh78, AST/diff review |
| Разъезд query/table/top/CSV | Общий WHERE/run, captured selection, экспорт недоступен во время загрузки; writer между чтениями |
| Устаревший run экспорта |409; старый кэш не JOIN к новому source; pinned transaction при выполнении |
| Округление CSV/JS Number | INTEGER cents → decimal strings; независимый parser с max int64; raw source не stringify |
| Формулы CSV/автоконвертация редактора | text:-контракт/escaping/проверка редактора; большие числа импортировать как текст |
| Скрытая перезапись настроек | expectedVersion под write lock;2 writers/legacy/rollback/uncertain; без force |
| Потеря черновика наBack/logout | Guard доPOST, useBlocker/beforeunload; быстрые Back/Forward, Escape, фокус |
| Ложный online/fresh | Свежесть поHTTP, отдельно transport;401/cleanup, ошибки ресурса не считаются свежими данными |
| Лишние зависимости | Только router/test framework, без Tailwind/shadcn/chart/query/state packages |
| Подмена бренда или непрочитанный шрифт | Локальные полные Exo 2/Inter и лицензии, provenance SVG, поле 30 px; computed styles/hover/focus и ручная сверка с PDF |
| Запись тестов в рабочуюБД | TemporaryDirectory, workers1, reuseExistingServer:false; отдельный Docker project/volume |
| Нет браузера/редактора/участников | Критерий явно не проверен; автоматическая отметка готовности запрещена |

## Complexity Tracking

Нарушений конституции нет. Обоснованные дополнения:

| Решение | Необходимость | Более простой вариант отклонён |
|---|---|---|
| react-router-dom7.18.4 | Back/Forward, guards и прямой hash без server fallback | Local page state теряет контекст, собственный history guard сложнее |
| @playwright/test1.64.1 dev | Регрессии навигации/фокуса/скачивания/двух окон/ошибок | tsc и одноразовый ручной smoke не фиксируют поведение |

## Выход этого этапа

Подготовлены plan/research/data-model/contracts/api/contracts/ui/contracts/brand/quickstart
и tasks.md. Брендбук обновил только визуальные требования, не API или формулы.
Constitution gates после дизайна пройдены; открытых исследовательских вопросов нет.
Приложение, dependencies, openapi.json, данные, AGENTS, конституция,001/002 не меняются.
Hooks: .specify/extensions.yml отсутствует, pre/post dispatch не требуется.
Следующий этап — $speckit-analyze по согласованным документам перед реализацией.
Задачи не выполнялись; нет изменений кода, коммитов, push или merge.
