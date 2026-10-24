# Tasks: 003 — Панель маркетолога: понятный риск и приоритет действий

**Ветка:** `003-marketer-panel`, исходная база `fc368be` с реализованной002.
**Активная доработка:** `.specify/feature.json` → `specs/003-marketer-panel`.
**Основание:** [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [API](contracts/api.md), [UI](contracts/ui.md),
[брендбук и материалы](contracts/brand.md), [приёмка](quickstart.md).

Все задачи ниже — будущая работа, ни одна не выполнена при составлении документа.
Сохраняются FastAPI/React/TypeScript/Vite/SQLite, формулы и гарантии001/002.
Никаких сохранённых сегментов, истории, новых формул, OIDC или переписывания приложения.
Тесты с записью используют только собственные временные БД; рабочие данные, секреты,
внешние сервисы и файлы001/002/конституция не меняются. Коммиты/push/merge не входят.

Формат: checkbox → последовательный ID → `[P]` для независимых файлов → `[USn]`
в фазе истории → результат, точные файлы, зависимости, требования и критерии.
Все пути ниже относительно корня репозитория. `—` означает отсутствие предшественника.
`[P]` разрешает параллельную работу только после указанных зависимостей и при
отсутствии другого незавершённого изменения тех же файлов. Общие файлы меняются по очереди.
Сначала пишутся содержательные проверки новой истории, затем исправления/интерфейс;
провал из-за отсутствующей003 фиксируется отдельно от неожиданного отказа001/002.


## Этап 1. Подготовка и изолированная проверочная среда

**Результат этапа:** Зафиксирована исходная база и подготовлены только необходимые инструменты/материалы.

**Независимая проверка:** Ветка003, активная003; тестовый сервер не использует рабочую БД, материалы имеют проверяемый источник.


- [x] T001 Зафиксировать baseline существующих001/002: запуск текущих регрессий на tmp_path, результаты/пропуски, защищённые файлы и формулы; не переоткрывать готовые исправления как задачи003. Файлы: `specs/003-marketer-panel/quickstart.md`, `backend/tests/conftest.py`. Зависит: —. Покрытие: FR-022; SC-007, SC-009.


- [x] T002 Подготовить воспроизводимый E2E runner: только react-router-dom7.18.4 runtime и @playwright/test1.64.1 dev по plan; exact lockfile, peers/engines, workers:1, reuseExistingServer:false, собственный server/TemporaryDirectory/APP_DB и cleanup. Synthetic fixtures: больше страницы, ties, unknown, нули, сроки±1ms, большие cents, минимум два пользователя/сессии. Не добавлять публичные test endpoints. Файлы: `frontend/package.json`, `frontend/package-lock.json`, `frontend/playwright.config.ts`, `frontend/e2e/start-test-server.py`, `frontend/e2e/fixtures.ts`. Зависит: T001. Покрытие: FR-022; SC-002, SC-006, SC-007, SC-009.


- [x] T003 [P] Подготовить подлинные монохромные полные/компактные знаки и favicon из утверждённых SVG либо точного векторного экспорта PDF; проверить пропорции/paths/viewBox без эффектов. Подготовить полный Exo 2 и Inter с кириллицей/OFL и provenance/checksum. Не извлекать PDF font subsets, не подменять знак текстом/рисунком. Записать источник/страницы и вариант в manifest; при невозможности точного экспорта отметить блокировку конкретного материала. Файлы: `frontend/public/brand/aeza-logo-black.svg`, `frontend/public/brand/aeza-logo-white.svg`, `frontend/public/brand/aeza-mark-black.svg`, `frontend/public/brand/aeza-mark-white.svg`, `frontend/public/brand/pattern.svg`, `frontend/public/brand/asset-manifest.json`, `frontend/public/favicon.svg`, `frontend/public/fonts/Exo2Variable.woff2`, `frontend/public/fonts/InterVariable.woff2`, `frontend/public/fonts/Exo2-OFL.txt`, `frontend/public/fonts/Inter-OFL.txt`. Зависит: T001. Покрытие: FR-021, FR-023; SC-010.


## Этап 2. Общие компоненты, стили и навигация

**Результат этапа:** Одна бренд-система, безопасный транспорт и навигационный каркас без смены стека.

**Независимая проверка:** Вход/выход и прямые hash-маршруты работают; стили и материалы реально загружаются. Полный сценарий истории проверяется в её фазе.


- [x] T004 Добавить браузерную регрессию транспорта: custom headers не убирают Bearer, credentials cookie сохраняются; structured detail.code, JSON/text+headers/Blob и отказ body различаются. Проверить, что ошибка logout не изображает успешный выход. Файлы: `frontend/e2e/states-accessibility.spec.ts`. Зависит: T002. Покрытие: FR-001, FR-017, FR-018, FR-022; SC-007, SC-009.


- [x] T005 Выделить минимальный requestResponse и тип ApiError(status/code), переиспользовать JSON/text wrappers; корректно объединить init/headers, подготовить чтение source headers и полного Blob. Сохранить cookie/Bearer priority и logout002, не дублировать auth. Файлы: `frontend/src/api.ts`, `frontend/src/types.ts`. Зависит: T004. Покрытие: FR-014, FR-016, FR-017, FR-018, FR-022; SC-006, SC-007, SC-009.


- [x] T006 [P] Добавить проверки фактической загрузки Exo 2/Inter и кириллицы, fallback без CDN, монохромных assets/favicon, пропорций/охранного поля, голубого основного акцента и контрастного текста кнопок. В тестах считать отсутствие новых компонентов ожидаемым исходным отказом, не PASS по одному font-family. Файлы: `frontend/e2e/brand.spec.ts`. Зависит: T002, T003. Покрытие: FR-020, FR-021, FR-023; SC-008, SC-010.


- [x] T007 Ввести токены UI-контракта: #F4F4F4/#000000/#4CC6F1, дополнительные #182D48/#ECCFDB/#E97C35, отдельные семантические статусы; основной Exo 2, дополнительный Inter. Привести небольшие Button/Card/Field/Notice/Dialog и текущие formatters к единой системе; убрать serif и конфликтующие inline Settings colors. Не вводить Tailwind/shadcn или общий framework. Файлы: `frontend/src/styles.css`, `frontend/src/components/ui.tsx`, `frontend/src/pages/Settings.tsx`. Зависит: T006, T005. Покрытие: FR-019, FR-020, FR-021, FR-023; SC-008, SC-010.


- [x] T008 Создать BrandLogo/BrandIcon, применить настоящий знак на входе/в навигации и favicon в HTML. Сохранить поле 30 CSS px вокруг видимой формы, compact min-height84px с ростом, заливные округлые иконки с названиями; паттерн только в свободной бренд-зоне. Поля входа/ошибка/ожидание сохраняют прежний сценарий, без новых уведомлений и маскота. Файлы: `frontend/src/components/BrandLogo.tsx`, `frontend/src/components/BrandIcon.tsx`, `frontend/src/pages/Login.tsx`, `frontend/index.html`, `frontend/src/styles.css`. Зависит: T007, T003. Покрытие: FR-001, FR-017, FR-019, FR-020, FR-021, FR-023; SC-008, SC-009, SC-010.


- [x] T009 Ввести hash data router и authenticated layout: /login,/overview,/customers,/customers/:id,/settings,/data; активный sidebar, компактный drawer, прямой reload без серверного fallback. На этом этапе сохранить существующий список Dashboard как временный экран /customers: добавить initialLevel из ClientContext и рабочий переход к карточке до T013; полноценное извлечение выполнит T017. Поднять общий UI context выше страниц; предусмотреть root guard и очистку при смене владельца, не переносить token в историю. Не создавать несколько источников состояния. Файлы: `frontend/src/main.tsx`, `frontend/src/routes.tsx`, `frontend/src/App.tsx`, `frontend/src/state/ClientContext.tsx`. Зависит: T008, T005. Покрытие: FR-001, FR-005, FR-019, FR-020, FR-022; SC-003, SC-008, SC-009, SC-010.


## Этап 3. US1 (P1): сводка и графики

**Результат этапа:** Глобальная сводка ведёт к группе и клиенту без подмены области расчёта.

**Независимая проверка:** На synthetic наборе KPI/распределение/топ совпадают с полным ожиданием; переходы работают без новых фильтров003.


- [x] T010 [US1] Описать E2E пути сводка→уровень→клиент→назад: глобальные KPI, топ5 всей совокупности, сумма распределения, нули/пустота, текстовая альтернатива и фильтр перехода без скрытых старых q/urgency. Не использовать значения текущей страницы как oracle. Файлы: `frontend/e2e/navigation.spec.ts`. Зависит: T009. Покрытие: FR-001, FR-002, FR-003, FR-007, FR-010, FR-019; SC-001, SC-004.


- [x] T011 [US1] Извлечь из Dashboard два существующих смысловых графика в компоненты с props: распределение уровней и топ потерь. Добавить значения/подписи, доступные ссылки, текстовую альтернативу и контрастные границы; не делать независимый fetch, page ranking или тренды. Файлы: `frontend/src/components/RiskCharts.tsx`, `frontend/src/styles.css`. Зависит: T010. Покрытие: FR-002, FR-003, FR-007, FR-019, FR-020; SC-004, SC-008, SC-010.


- [x] T012 [US1] Собрать Dashboard: контекст времени→4 KPI→графики→переход к списку. Явно подписать глобальную область, полноту и эвристическую денежную оценку, EUR и отсутствие данных. Клик уровня задаёт level/page1, очищает q/urgency, сохраняет sort; топ открывает правильную карточку с origin overview. Файлы: `frontend/src/pages/Dashboard.tsx`, `frontend/src/state/ClientContext.tsx`, `frontend/src/App.tsx`. Зависит: T011. Покрытие: FR-001, FR-002, FR-003, FR-007, FR-010, FR-011; SC-001, SC-004, SC-009, SC-010.


- [x] T013 [US1] Пройти независимую приёмку US1 на временной среде: сравнить KPI/оба графика с известным полным набором, нулевой набор и возврат на исходную ссылку сводки. Зафиксировать фактический результат; человеческий тайминг SC-001 оставить отдельной финальной проверке. Файлы: `frontend/e2e/navigation.spec.ts`, `specs/003-marketer-panel/quickstart.md`. Зависит: T012. Покрытие: FR-001, FR-002, FR-003, FR-007, FR-010, FR-019; SC-001, SC-004.


## Этап 4. US2 (P1): клиенты, фильтры, срочность и контекст

**Результат этапа:** Список, число и топ используют одну выборку; карточка/Back не теряют работу пользователя.

**Независимая проверка:** Набор больше страницы, q AND level AND urgency, независимый oracle, восемь сортировок; Back восстанавливает условия/page/scroll/focus.


- [x] T014 [P] [US2] Добавить backend проверки всей выборки: urgency:all|expired|48h|7d, invalid→422; expiresAt<=asOf, 0<delta<=48h/7d и±1ms, вложенность, UTC/разные offset, active/suspended/prolong_wait против deleted/blocked. Включить unknown с исходной услугой и пустыми scored services, дубли услуг, ties, поиск LIKE002, total/top за пределами страницы и неизменную глобальную summary. Файлы: `backend/tests/test_customer_urgency.py`. Зависит: T009. Покрытие: FR-005, FR-006, FR-007, FR-008, FR-022; SC-002, SC-004.


- [x] T015 [US2] Добавить optional urgency и общий параметризованный WHERE/order до пагинации; EXISTS по исходным services и server run.asOf с каноническими UTC milliseconds. Count/items/top/summary/run читать одной read_transaction; top loss DESC/id ASC независимо от page/sort, summary глобальная. Сохранить all и прежние пути/response, формулы не трогать. Файлы: `backend/app/api.py`. Зависит: T014, T013. Покрытие: FR-005, FR-006, FR-007, FR-008, FR-022; SC-002, SC-004.


- [x] T016 [P] [US2] Добавить сценарии q/level/urgency, chips/reset/page1, sort/page2 и карточка→UI Back/Browser Back/Forward/раздел; прямой hash/reload, уменьшение page count/исчезнувший клиент, быстрые переходы и запоздалый ответ. Проверить отдельные ownerUserId/viewSessionId после logout/входа другого и того же пользователя. Файлы: `frontend/e2e/navigation.spec.ts`, `frontend/e2e/customers-export.spec.ts`. Зависит: T013. Покрытие: FR-004, FR-005, FR-006, FR-007, FR-008, FR-017, FR-022; SC-002, SC-003, SC-009.


- [x] T017 [US2] Завершить ClientSelection: q trimmed, level:high|medium|low|unknown|empty, urgency:all|expired|48h|7d, прежний whitelist sort/order, page>=1, pageSize(default10 UI). Смена фильтра/сортировки→page1; общий сброс очищает q/level/urgency, сохраняет sort/order. Создать filters/chips и Customers с единым bundle и top группы; запретить stale responses заменять текущий запрос. Файлы: `frontend/src/state/ClientContext.tsx`, `frontend/src/components/ClientFilters.tsx`, `frontend/src/pages/Customers.tsx`, `frontend/src/api.ts`, `frontend/src/types.ts`. Зависит: T015, T016. Покрытие: FR-004, FR-005, FR-006, FR-007, FR-017; SC-002, SC-003, SC-009.


- [x] T018 [US2] Извлечь CustomerTable с ID/email/балансом/пополнениями/score/уровнем/денежными полями, восемью направлениями по первым четырём полям и прежними score/loss. Caption/единицы EUR/aria-sort/links/текстовый unknown, локальный scroll; не ранжировать только страницу. Срочность объясняет выбор клиентов, не подменяет денежную сумму платежами интервала. Файлы: `frontend/src/components/CustomerTable.tsx`, `frontend/src/pages/Customers.tsx`, `frontend/src/styles.css`. Зависит: T017. Покрытие: FR-006, FR-007, FR-008, FR-010, FR-019, FR-020; SC-002, SC-008, SC-010.


- [x] T019 [US2] Реализовать restore point в context/history.state по ownerUserId/viewSessionId/locationKey, без token/email в URL и без бессрочного localStorage. На POP: данные→коррекция page→scroll→focus({preventScroll:true}) по ID, а также scrollLeft контейнера таблицы; total0→page1, исчезнувшая цель→heading/счётчик. Replace для фильтров, реальная история для карточки; direct card fallback к списку, чужую/завершённую запись не восстанавливать. Файлы: `frontend/src/hooks/useViewRestoration.ts`, `frontend/src/state/ClientContext.tsx`, `frontend/src/pages/Customers.tsx`, `frontend/src/pages/Customer.tsx`, `frontend/src/routes.tsx`. Зависит: T018. Покрытие: FR-001, FR-005, FR-017, FR-019, FR-022; SC-003, SC-008, SC-009.


- [x] T020 [US2] Запустить приёмку US2 с >pageSize клиентами и минимум одним денежным лидером вне первой страницы: сверить total/items/top, reset/сортировки, вложенные интервалы, Back/Forward, scroll/focus, удаление/уменьшение данных и гонку двух фильтров. Проверить, что changed thresholds002 по-прежнему отражаются везде. Файлы: `backend/tests/test_customer_urgency.py`, `frontend/e2e/navigation.spec.ts`, `frontend/e2e/customers-export.spec.ts`, `specs/003-marketer-panel/quickstart.md`. Зависит: T019. Покрытие: FR-004, FR-005, FR-006, FR-007, FR-008, FR-017, FR-022; SC-002, SC-003, SC-004, SC-009.


## Этап 5. US3 (P1): карточка, объяснения и время

**Результат этапа:** Карточка объясняет опубликованный риск и деньги с контекстом одной версии.

**Независимая проверка:** Контрольные floors/bonus/cap, пустые drivers, unknown, price0 и hour понятны; даты не смешаны.


- [x] T021 [P] [US3] Добавить регрессию coherent detail/source context при writer между чтениями: run/asOf/updatedAt и данные одной read_transaction; cache preflight001 не требует нового обязательного поля. Raw source body сохраняется побайтно по числам/формату контракта, дата формирования не выдумана, 404 не подменён чужой карточкой. Файлы: `backend/tests/test_atomic_updates.py`, `backend/tests/test_customer_views.py`. Зависит: T020. Покрытие: FR-009, FR-010, FR-011, FR-014, FR-022; SC-005, SC-007, SC-009.


- [x] T022 [P] [US3] Добавить проверки карточки с floors/bonus/cap, пустыми drivers, unknown, price0 и почасовой услугой; разделить service reasons и customer rules, полноту/вероятность, ближайший платёж/месяц, 0/нет оценки. Проверить один момент в UTC/Europe/Moscow и недоступную дату источника. Файлы: `frontend/e2e/navigation.spec.ts`. Зависит: T020. Покрытие: FR-009, FR-010, FR-011, FR-019; SC-005, SC-008, SC-009.


- [x] T023 [US3] Ввести CustomerViewOut поверх прежнего CustomerDetailOut и additive calculation/asOf/updatedAt ответа карточки; source получает только X-Calculation-* headers в прежнем read snapshot. _ensure_summary до чтения; не менять cached detail_response, compute, raw arrays/INTEGER или контракт старых consumers. Файлы: `backend/app/schemas.py`, `backend/app/api.py`. Зависит: T021. Покрытие: FR-009, FR-011, FR-014, FR-022; SC-005, SC-007, SC-009.


- [x] T024 [US3] Сделать CalculationContext и typed чтение detail/source context: дата источника unknown, asOf, calculatedAt и last successful read раздельны. Intl.DateTimeFormat с явным timezone; никаких независимых summary другой версии и часов браузера для фильтра. Файлы: `frontend/src/components/CalculationContext.tsx`, `frontend/src/api.ts`, `frontend/src/types.ts`, `frontend/src/pages/Dashboard.tsx`, `frontend/src/pages/Customers.tsx`. Зависит: T023, T022. Покрытие: FR-006, FR-010, FR-011, FR-017; SC-005, SC-009, SC-010.


- [x] T025 [US3] Привести Customer к новой иерархии: исходные деньги→главные причины/полнота→услуги с ценой/периодом/статусом/автопродлением/точным сроком. Показать floors/bonus/cap даже без drivers, unknown объяснить; не суммировать причины услуги как клиентские баллы. Сохранить origin/back и доступность таблицы услуг. Файлы: `frontend/src/pages/Customer.tsx`, `frontend/src/components/ui.tsx`, `frontend/src/styles.css`. Зависит: T024. Покрытие: FR-005, FR-009, FR-010, FR-011, FR-019, FR-021; SC-003, SC-005, SC-008, SC-010.


- [x] T026 [US3] Пройти US3 на контрольных клиентах и сравнить score/денежные значения с backend до UI-изменений; проверить 404, unknown/нулевую цену/короткий срок и часовой пояс. Записать результат и отсутствие изменений формул. Файлы: `frontend/e2e/navigation.spec.ts`, `specs/003-marketer-panel/quickstart.md`. Зависит: T025. Покрытие: FR-009, FR-010, FR-011, FR-022; SC-005, SC-009.


## Этап 6. US5 (P1): настройки, данные и сохранение черновика

**Результат этапа:** Явное сохранение защищает от перезаписи и показывает реальный результат операции.

**Независимая проверка:** Две вкладки: один guarded save успешен, устаревший получает409 и сохраняет draft; отменённый уход не вызывает logout. Ошибочный snapshot не меняет состояние.


- [x] T027 [P] [US5] Добавить регрессии expectedVersion?:strict int>=1, absent/null legacy и invalid bool/float/string/0; два условных writer одной базы→200+409. Проверить конфликт после legacy writer, отсутствие SSE/изменений payload/version/time/runs/results при409 и гарантии rollback/restart при отказах. Файлы: `backend/tests/test_settings_conflicts.py`. Зависит: T026. Покрытие: FR-012, FR-013, FR-022; SC-007.


- [x] T028 [P] [US5] Добавить E2E dirty/reset/stay/discard через sidebar/Back/logout/reload; два редактора, внешнее обновление,409,422/предкоммитный500 и потерю ответа после commit. Проверить сохранность candidate/baseVersion/draft, отсутствие auto retry/rebase и неподмену applied summary. Файлы: `frontend/e2e/settings.spec.ts`. Зависит: T026. Покрытие: FR-012, FR-013, FR-014, FR-017, FR-022; SC-007, SC-009.


- [x] T029 [US5] Добавить optional strict expectedVersion в PATCH schema и проверку внутри существующей BEGIN IMMEDIATE до merge/save/recompute. Mismatch→settings_version_conflict с expected/currentVersion без записи; precondition не хранить в settings. Сохранить partial PATCH/null omission, legacy отсутствие поля и atomic response preflight001/002. Файлы: `backend/app/schemas.py`, `backend/app/api.py`. Зависит: T027. Покрытие: FR-012, FR-013, FR-022; SC-007.


- [x] T030 [US5] Реализовать SettingsDraft: baseSettings/baseVersion/draft/dirty/submittedCandidate/observedCurrent; state:loading|clean|dirty|saving|saved|validation_error|conflict|uncertain|load_error. Dirty только по редактируемым полям; reset меняет draft. На обрыв сохранить candidate и старую базу, перечитать settings/summary с совпадающими версиями; равенство значений не доказывает собственный успех, автоматических rebase/retry нет. Файлы: `frontend/src/state/SettingsDraft.tsx`, `frontend/src/api.ts`, `frontend/src/types.ts`. Зависит: T029, T028. Покрытие: FR-012, FR-013, FR-017; SC-007, SC-009.


- [x] T031 [US5] Обновить Settings: применённая версия отдельно от draft, честные формулы/нормализация/floors/bonus, вес0 доступен для включения; сумма весов не обязана1.00. Save отправляет baseVersion и блокирует все редактируемые поля, повторы/reset/неоднозначный уход до завершения запроса; проверить попытку редактирования при задержанном ответе.409 сохраняет правки; загрузка текущей версии требует отказа от draft. Explicit uncertain retry использует старую baseVersion. Файлы: `frontend/src/pages/Settings.tsx`, `frontend/src/styles.css`. Зависит: T030. Покрытие: FR-010, FR-011, FR-012, FR-013, FR-019, FR-021; SC-007, SC-008, SC-009, SC-010.


- [x] T032 [US5] Подключить root guard к навигации/Browser Back/logout: useBlocker и beforeunload, native диалог «Остаться/Отказаться», Escape отменяет, фокус возвращается. До logout POST требуется решение; ошибка выхода сохраняет текущую сессию002. Успешный явный выход очищает draft/context/owner и не оставляет доступных старых history restore points. Файлы: `frontend/src/App.tsx`, `frontend/src/routes.tsx`, `frontend/src/state/SettingsDraft.tsx`, `frontend/src/components/ui.tsx`. Зависит: T031. Покрытие: FR-001, FR-005, FR-012, FR-017, FR-019, FR-022; SC-003, SC-007, SC-008, SC-009.


- [x] T033 [US5] Привести Data к общему стилю: source context headers/raw text, количества, смысл полной замены, загрузка/успех/ошибка/повтор и неизвестная дата формирования. Upload/download не JSON.parse/stringify для больших INTEGER; нули и отказ100.0 сохраняют контракт002. Обновление считается успешным только после ответа; при неопределённом результате перечитать актуальные данные без ложного отката/успеха. Файлы: `frontend/src/pages/Data.tsx`, `frontend/src/api.ts`, `frontend/src/styles.css`. Зависит: T032, T024. Покрытие: FR-011, FR-014, FR-017, FR-019, FR-021, FR-022; SC-007, SC-008, SC-009, SC-010.


- [x] T034 [US5] Пройти US5 на отдельных временных БД: dirty/reset/guard, конфликт между последней проверкой и save, uncertain после commit, legacy PATCH, повторный запуск и отклонённый snapshot. Сверить сохранность правок и опубликованного состояния; авторизация cookie/Bearer и независимая сессия002 сохранены. Файлы: `backend/tests/test_settings_conflicts.py`, `frontend/e2e/settings.spec.ts`, `specs/003-marketer-panel/quickstart.md`. Зависит: T033. Покрытие: FR-012, FR-013, FR-014, FR-017, FR-022; SC-007, SC-009.


## Этап 7. US6 (P1): ошибки, связь и доступная работа

**Результат этапа:** На каждом экране понятны состояния; потеря сессии скрывает данные без потери допустимого локального draft.

**Независимая проверка:** SSE отказал/poll успешен, оба отказали/recovery,401 при открытом SSE и задержанные ответы проверяются управляемыми сценариями.


- [x] T035 [US6] Добавить сценарии loading/empty/no matches/error/retry для шести экранов, stale response, SSE отказ+успешный polling, полный offline/recovery,401 при открытом потоке и auth/me polling. Проверить, что navigator.onLine/EventSource.open сами не означают свежие данные, старый bundle честно помечен. Файлы: `frontend/e2e/states-accessibility.spec.ts`. Зависит: T034. Покрытие: FR-017, FR-018, FR-019, FR-022; SC-008, SC-009.


- [x] T036 [US6] Централизовать прежние SSE/15sec polling в useLiveUpdates: transport:sse|polling|offline; data:initial_loading|refreshing|current|stale|error, lastSuccessfulReadAt/error/authState. Свежесть по успешным HTTP, cleanup/отмена старых запросов, fallback/recovery без ложных нулей. Проверять сессию и при открытом SSE; на401 закрывать поток/опрос, не менять серверный механизм сессий. Файлы: `frontend/src/hooks/useLiveUpdates.ts`, `frontend/src/App.tsx`, `frontend/src/pages/Dashboard.tsx`, `frontend/src/pages/Customers.tsx`. Зависит: T035. Покрытие: FR-017, FR-018, FR-022; SC-009.


- [x] T037 [US6] Применить общие EmptyState/Notice/ErrorBox/Spinner и доступный retry ко всем шести экранам. Различить смену фильтра/refresh прежнего bundle, неизвестность/ноль/пустую выборку, HTTP422/500/networkerror; запросы старого customer/selection не заменяют актуальные данные. Удалить raw stacktrace из пользовательских ошибок. Файлы: `frontend/src/components/ui.tsx`, `frontend/src/pages/Login.tsx`, `frontend/src/pages/Dashboard.tsx`, `frontend/src/pages/Customers.tsx`, `frontend/src/pages/Customer.tsx`, `frontend/src/pages/Settings.tsx`, `frontend/src/pages/Data.tsx`. Зависит: T036. Покрытие: FR-010, FR-011, FR-017, FR-018, FR-019; SC-005, SC-008, SC-009, SC-010.


- [x] T038 [US6] Связать401 с защищённым layout: скрыть данные, остановить запросы, предложить вход; draft допускается только в памяти прежнего userId до повторного входа того же пользователя с перечитыванием версии. Иной userId/явный logout очищает draft; новый вход меняет viewSessionId и не восстанавливает чужую/завершённую history.state. Не обещать сохранение после закрытия вкладки. Файлы: `frontend/src/App.tsx`, `frontend/src/state/SettingsDraft.tsx`, `frontend/src/state/ClientContext.tsx`, `frontend/src/pages/Login.tsx`. Зависит: T037. Покрытие: FR-005, FR-012, FR-017, FR-018, FR-022; SC-003, SC-007, SC-009.


- [x] T039 [US6] Довести доступность существующих действий: labels/ошибки полей, ссылки вместо click-only строк, aria-current/aria-sort, статусы текстом, текстовые альтернативы графиков; native dialog/drawer c безопасным начальным/возвращаемым фокусом, Escape и без ловушек. Проверить reduced-motion и длинные тексты до финальной матрицы. Файлы: `frontend/src/components/ui.tsx`, `frontend/src/components/CustomerTable.tsx`, `frontend/src/components/RiskCharts.tsx`, `frontend/src/components/ClientFilters.tsx`, `frontend/src/App.tsx`, `frontend/src/styles.css`. Зависит: T038. Покрытие: FR-019, FR-020, FR-021, FR-023; SC-008, SC-010.


- [x] T040 [US6] Запустить независимую матрицу US6: по каждому экрану реальные состояния/повтор, fallback/offline/recovery/401, задержки и сохранение допустимого draft. Пройти основные действия клавиатурой; зафиксировать реальные результаты и предел обнаружения истёкшей сессии, не заявлять мгновенный отзыв уже открытого server stream. Файлы: `frontend/e2e/states-accessibility.spec.ts`, `frontend/e2e/settings.spec.ts`, `specs/003-marketer-panel/quickstart.md`. Зависит: T039. Покрытие: FR-017, FR-018, FR-019, FR-020, FR-022; SC-007, SC-008, SC-009.


## Этап 8. US4 (P2): CSV всей выбранной совокупности

**Результат этапа:** Маркетолог получает полный точный CSV с условиями и одной версией данных.

**Независимая проверка:** Независимый CSV parser проверяет состав/порядок/точность/metadata; браузер не скачивает частичный файл. Доступный редактор проверяется отдельно.


- [x] T041 [P] [US4] Добавить backend матрицу CSV из API-контракта: >pageSize, q/level/urgency, все сортировки/ties, fixed columns/metadata, NULL score пустой/unknown,0 и max int64/ID. Проверить точные bytes 9007199254740993→90071992547409.93 и9223372036854775807→92233720368547758.07; UTF-8 BOM/comma/CRLF/QUOTE_ALL, кириллицу/quotes/newlines, обратимый text: для email/filter_q с NFKC опасными началами/control/format и коллизией text:abc. Файлы: `backend/tests/test_customer_export.py`. Зависит: T040. Покрытие: FR-005, FR-006, FR-007, FR-015, FR-016, FR-022; SC-002, SC-006.


- [x] T042 [US4] В том же тестовом модуле после предыдущего добавить auth cookie/Bearer/401, invalid runId422, empty_selection409, stale_calculation409, writer PATCH/PUT между чтениями и отказ формирования до200. Проверить pin одной read_transaction и отсутствие JOIN старого run с новым source/частичного успешного ответа. Файлы: `backend/tests/test_customer_export.py`. Зависит: T041. Покрытие: FR-015, FR-016, FR-022; SC-006, SC-007, SC-009.


- [x] T043 [P] [US4] Добавить браузерную проверку полного download: захваченные selection/sort/runId при смене фильтров, total0/loading disabled,409→обновить и явный retry,401/обрыв body без файла. Разбирать download независимым parser/oracle, не сравнивать только число видимых строк. Файлы: `frontend/e2e/customers-export.spec.ts`. Зависит: T040. Покрытие: FR-004, FR-005, FR-015, FR-016, FR-017, FR-019; SC-006, SC-008, SC-009.


- [x] T044 [US4] Добавить GET /customers/export.csv до /customers/{id}; require_user cookie OR Bearer, runId:int>=1, общий WHERE/order. _ensure_summary→read_transaction→latest run check→строки/metadata→полные bytes до200;409 по контракту, no-store/attachment/Content-Length. INTEGER cents→decimal через divmod, не euros/float/JSON; текстовое обратимое кодирование и stdlib csv.writer. Не добавлять StreamingResponse/XLSX/ZIP. Файлы: `backend/app/api.py`, `backend/app/schemas.py`. Зависит: T042, T043. Покрытие: FR-005, FR-006, FR-007, FR-015, FR-016, FR-022; SC-002, SC-006, SC-009.


- [x] T045 [US4] Добавить typed экспорт и download после полного чтения Blob с captured query/runId; idle→loading→complete либо error/conflict/unauthorized. Изменение UI не меняет операцию; нет автоматического повтора, stale run требует перечитать список и явного нового экспорта. Освободить object URL, HTTP200 с ошибкой чтения body не считается успехом. Файлы: `frontend/src/api.ts`, `frontend/src/types.ts`, `frontend/src/pages/Customers.tsx`. Зависит: T044. Покрытие: FR-015, FR-016, FR-017, FR-018; SC-006, SC-009.


- [x] T046 [US4] Встроить экспорт в toolbar с понятным статусом, единицами, областью всей группы и причиной disabled при total0/loading. Клавиатурный доступ, ошибка/повтор, подписи защиты text: и импорта длинных чисел как текста; не обещать точность автоматического числового импорта любого редактора. Файлы: `frontend/src/pages/Customers.tsx`, `frontend/src/styles.css`, `frontend/src/components/ui.tsx`. Зависит: T045. Покрытие: FR-004, FR-010, FR-015, FR-016, FR-019, FR-021; SC-006, SC-008, SC-009, SC-010.


- [x] T047 [US4] Проверить CSV в доступном табличном редакторе: первоначальный импорт/save/reopen, кириллица/переносы, опасные email/q не исполняются, длинные ID/деньги импортируются как текст, text: снимается однократно только в двух заданных колонках. Записать редактор/режим/результат; отсутствие редактора отмечать непроверенным, не заменять parser тестом. Файлы: `specs/003-marketer-panel/quickstart.md`. Зависит: T046. Покрытие: FR-015, FR-016; SC-006.


- [x] T048 [US4] Запустить backend и browser приёмку US4: полная выбранная совокупность и порядок, единый run, точные суммы, конкурентный writer, обрыв/401/409, нулевая выборка и смена фильтра во время download. Не менять математические формулы/старый raw source ради CSV. Файлы: `backend/tests/test_customer_export.py`, `frontend/e2e/customers-export.spec.ts`, `specs/003-marketer-panel/quickstart.md`. Зависит: T046. Покрытие: FR-005, FR-006, FR-007, FR-015, FR-016, FR-022; SC-002, SC-006, SC-007, SC-009.


## Этап 9. Итоговая доступность, визуальная приёмка и совместимость

**Результат этапа:** Истории интегрированы, сборка и гарантии001/002 проверены; готовность подтверждена доказательствами.

**Независимая проверка:** Ни CSS, ни наличие теста не являются PASS. Невыполненные проверки/недоступные средства и остаточные ограничения перечислены явно.


- [x] T049 Сверить покрытие FR-001–FR-023/SC-001–SC-010 и пройти сквозной путь сводка→условия→карточка→Back→CSV→настройки→данные. Проверить повторное получение после save/upload без смешения версий; прогнать прежние001/002 regressions без повторной реализации их исправлений. Файлы: `backend/tests/test_customer_views.py`, `backend/tests/test_atomic_updates.py`, `backend/tests/test_settings_upgrade.py`, `backend/tests/test_auth_sessions.py`, `frontend/e2e/navigation.spec.ts`, `frontend/e2e/settings.spec.ts`, `frontend/e2e/customers-export.spec.ts`, `specs/003-marketer-panel/tasks.md`. Зависит: T048. Покрытие: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, FR-010, FR-011, FR-012, FR-013, FR-014, FR-015, FR-016, FR-017, FR-018, FR-019, FR-020, FR-021, FR-022, FR-023; SC-001, SC-002, SC-003, SC-004, SC-005, SC-006, SC-007, SC-008, SC-009, SC-010.


- [x] T050 Провести реальную бренд-приёмку шести экранов/favicon: Exo 2/Inter/кириллица/веса/fallback, точные HEX и голубой акцент, подлинные SVG/manifest, охранное поле 30px для HTML-логотипов (favicon сохраняет исходные пропорции компактного знака, без требования CSS-поля 30px) и пропорции без эффектов, заливные иконки, декор отдельно от данных. Сделать screenshots1440/360 и состояния error/focus/loading/dirty/conflict; ручную сверку с PDF записать отдельно от автотеста. Файлы: `frontend/e2e/brand.spec.ts`, `specs/003-marketer-panel/quickstart.md`. Зависит: T049. Покрытие: FR-019, FR-020, FR-021, FR-023; SC-008, SC-010.


- [x] T051 Пройти keyboard и actual contrast всех значимых пар/состояний на1440/1024/768/360px и200% текста: focus/dialog/drawer, длинный email, тулбар/формы, локальный scroll таблицы без body overflow, графики без цветового кодирования как единственного носителя. Исправить только обнаруженные отклонения003 и повторить затронутый сценарий. Файлы: `frontend/e2e/states-accessibility.spec.ts`, `frontend/src/styles.css`, `specs/003-marketer-panel/quickstart.md`. Зависит: T050. Покрытие: FR-019, FR-020, FR-021, FR-023; SC-008, SC-010.


- [ ] T052 Дать минимум трём реальным участникам команды без подсказок пройти SC-001: найти приоритетную группу/клиента и объяснить причину/денежную оценку за2мин каждому. Записать время, затруднения и результат; агент не имитирует людей. При отсутствии участников SC-001 остаётся непроверенным. Файлы: `specs/003-marketer-panel/quickstart.md`. Зависит: T051. Покрытие: FR-001, FR-002, FR-003, FR-009, FR-010; SC-001, SC-004, SC-005.


- [x] T053 [P] Экспортировать schema штатным scripts/export_openapi.py, обновить openapi.json и полное equality/live OpenAPI тестирование. Отразить urgency/CSV/expectedVersion/409/headers/additive DTO и альтернативную cookie OR Bearer; старые пути/форматы/legacy PATCH сохранены. Не маскировать рассогласование ослаблением теста. Файлы: `openapi.json`, `backend/tests/test_openapi_contract.py`. Зависит: T049. Покрытие: FR-006, FR-011, FR-012, FR-014, FR-015, FR-016, FR-022; SC-002, SC-006, SC-007, SC-009.


- [x] T054 Запустить все backend/data raw тесты, tsc/Vite build и Playwright на собственной временной среде по quickstart; проверить npm ci/lockfile и отсутствие новых необоснованных dependencies. Записать фактические passed/failed/skipped, окружение и воспроизведения отказов. Наличие файла теста не основание отметить его выполненным. Файлы: `backend/tests`, `data/raw/test_generate.py`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/playwright.config.ts`, `specs/003-marketer-panel/quickstart.md`. Зависит: T051, T053. Покрытие: FR-022; SC-002, SC-003, SC-004, SC-005, SC-006, SC-007, SC-008, SC-009, SC-010.


- [ ] T055 Проверить сборку существующего Dockerfile и запуск на отдельном compose project/порту/временном volume без рабочей .env: root/hash/login, fonts/logo, CSV, metrics/API/settings и restart persistence. Удалить только собственные ресурсы; если Docker недоступен, явно записать ограничение. Файлы: `Dockerfile`, `docker-compose.yml`, `specs/003-marketer-panel/quickstart.md`. Зависит: T054. Покрытие: FR-001, FR-012, FR-014, FR-016, FR-021, FR-022, FR-023; SC-006, SC-007, SC-009, SC-010.


- [x] T056 Точечно обновить README и STATUS: запуск/маршруты, область фильтров/срочности/CSV/text:, неизвестные даты/эвристики, conditional settings/draft, источники бренда/лицензии, фактические проверки и ограничения. В tasks отмечать только подтверждённые результаты; непроведённые офис/визуал/люди не скрывать. Файлы: `README.md`, `docs/STATUS.md`, `specs/003-marketer-panel/quickstart.md`, `specs/003-marketer-panel/tasks.md`. Зависит: T055. Покрытие: FR-001, FR-006, FR-010, FR-011, FR-012, FR-014, FR-015, FR-016, FR-021, FR-022, FR-023; SC-001, SC-002, SC-003, SC-004, SC-005, SC-006, SC-007, SC-008, SC-009, SC-010.


- [x] T057 Проверить итоговый diff/whitespace и отсутствие изменений формул, AGENTS/конституции/001/002, seed/raw/рабочих данных/секретов. Подтвердить branch003, активную003, неизменные старые API и только обоснованные зависимости; составить краткий отчёт выполнено/не проверено/ограничения. Без коммита/push/merge. Файлы: `specs/003-marketer-panel/tasks.md`, `specs/003-marketer-panel/quickstart.md`, `docs/STATUS.md`. Зависит: T056. Покрытие: FR-022; SC-007, SC-009, SC-010.


## Зависимости и контрольные точки

```text
Подготовка → общая основа → US1 → US2 → US3 → US5 → US6 → US4 → итоговая приёмка
```

Это выбранный безопасный порядок работы с общими файлами, а не утверждение, что все
продуктовые истории неразделимы. Все P1 идут до P2. US1 проверяется без новых CSV;
US2 — без экспорта, US3 — по собственным контрольным клиентам; US5 — без CSV;
US6 — управляемыми отказами. US4 использует готовые фильтры и транспорт.

На каждой контрольной точке: сначала новый тест воспроизводит ожидаемый пробел003,
потом реализация и независимая проверка истории; неожиданный отказ001/002 исследуется,
а не обходится изменением ожидаемых формул. Backend api.py/schemas.py, api.ts/types.ts,
styles.css и общие E2E-модули редактируются последовательно.

## Параллельные возможности

Только после готовности зависимостей и без общего редактируемого файла:

- Подготовка: материалы бренда могут готовиться независимо от E2E runner.
- Основа: транспортная регрессия и отдельный brand.spec.ts независимы.
- US1: после общего теста проверка числового oracle/легенд может идти отдельно от
  ручной оценки формулировок; Dashboard ждёт готовые props графиков. Независимой
  второй правки тех же файлов не планируется.
- US2: backend urgency тесты и браузерные navigation/customers тесты независимы;
  реализация selection ждёт оба контракта.
- US3: backend coherent-read тесты и сценарий UI-карточки независимы.
- US5: backend settings conflicts и E2E dirty/conflict независимы.
- US6: ручная проверка клавиатуры и сбор доказательств сетевых сценариев допустимы
  параллельно на разных изолированных серверах; общие исправления последовательны.
- US4: backend CSV матрица и браузер download тесты независимы; сервер ждёт обе.
- Финал: OpenAPI equality может проверяться независимо от ручной визуальной/пользовательской
  приёмки. Каждый запуск с записью имеет отдельную БД, не общий E2E server.

## Стратегия поставки и критерий завершения

Минимальный первый демонстрируемый срез: этапы1–3, US1 — оформленный вход/навигация,
глобальная сводка и два полезных графика с переходами. Это не завершение всей003.
Далее последовательно US2/US3/US5/US6, затем CSV US4 и полная приёмка.
Никаких работ следующего этапа или необязательных сегментов ради красивого списка задач.

Задача отмечается `[x]` только после получения указанного результата и проверки;
если средство недоступно — результат «не проверено» и причина, без автоматического PASS.
Ручные бренд/контраст/редактор/люди не подменяются сборкой или наличием CSS.
