# Data model/state:003

Плановые сущности и состояния. SQL schema и математическая модель001/002 сохраняются.
Новые таблицы, миграции, история снимков и real-time collaboration service не нужны.

## 1. Существующие persisted сущности

accounts/services/transactions — текущий источник, INTEGER cents, canonical UTC dates.
settings — payload/version/updated_at/feature_schema_version002; поколение не меняется.
score_runs/customer_scores — опубликованный расчёт; thresholds и run/version связаны.
Источник не версионирован по run: старый score_run нельзя JOIN с новым снимком.
Коэффициенты/вероятности/деньги/score/coverage и handling unknown не меняются.

## 2. ClientSelection

q:string(trimmed effective query), level:high|medium|low|unknown|empty,
urgency:all|expired|48h|7d, sort/order:прежние whitelist, page>=1,pageSize(default10 UI).
AND всех фильтров. Смена q/level/urgency →page1, сброс также очищает q/level/urgency,
но оставляет сортировку. Сортировка меняет порядок, не область топа; сбрасывает page1
как текущий UI. Выборка вычисляется сервером до пагинации.

Провайдер состояния расположен выше сменяемых страниц внутри authenticated root.
Условия сохраняются при переходе между разделами и карточкой в текущей сессии;
не сохраняются бессрочно в localStorage, не переносятся между пользователями.
Hash содержит route/customer id; фильтры и scroll/focus хранятся в UI context +
history location.state по location.key, без размещения email-поиска в URL/query.
Сначала на переходе сохраняется origin, затем history navigation. На POP восстанавливается
состояние соответствующей записи, на обычном возвращении раздела — последний контекст.
Прямая ссылка без контекста использует defaults, а не повреждает историю.

## 3. ViewRestorePoint

ownerUserId/viewSessionId, originRoute/locationKey, selection, scrollY, tableScrollLeft,
focusCustomerId/focusControlId. Owner не содержит auth token. ViewSessionId —
нечувствительный nonce текущей UI-сессии; его одного можно держать в sessionStorage
для reload той же вкладки, без фильтров/черновика. После явного выхода/нового входа
nonce меняется, при401 перестаёт разрешать восстановление защищённого контекста.
Перед применением history.state сравнить ownerUserId/viewSessionId с текущим owner;
чужую/завершённую restore-запись игнорировать и заменить безопасными defaults.
Одна очистка React context не считается достаточной очисткой старых history entries.
Сохранение draft для повторной авторизации того же userId не разрешает автоматически
применять прежнюю history.state нового входа.
Фокус сохраняет идентификатор клиента/контрола, не индекс строки.
Восстановление после успешной загрузки актуального bundle и появления строк;
не полагаться только на автоматическое ScrollRestoration до завершения fetch.
Page>max(total): один корректирующий запрос допустимой последней страницы;
total0 →page1/пустота без бесконечного refetch. Исчезнувшая карточка —404-состояние.
Если цель фокуса исчезла — heading списка/счётчик; нельзя фокусировать другого клиента.
Последовательность: данные →коррекция page →scroll + tableScrollLeft →focus({preventScroll:true}).

## 4. ViewBundle/CalculationContext

Существующий bundle002 — единая публикация items/count/top/global summary/calculation.
Локальный stale response не может частично заменить bundle. На обновлении показывать
последний целый bundle с состоянием обновления/устаревания, без ложных нулей.
CustomerView добавляет контекст run только на этапе API response; source context —
в HTTP headers, не в raw arrays. sourceGeneratedAt всегда unknown при текущем формате.
asOf — опорное время, updatedAt — время расчёта, lastReceivedAt — клиентское время
успешного получения; это разные значения, отображаются с timezone.

## 5. SettingsDraft

baseSettings/baseVersion, draft, dirty, submittedCandidate, observedCurrent,
state:loading|clean|dirty|saving|saved|validation_error|conflict|uncertain|load_error.
Черновик/принятые настройки не смешиваются. Проверка dirty по редактируемым полям,
а не по features/version/updatedAt; reset recommendations меняет только draft.

| Событие | Переход/гарантия |
|---|---|
| Загрузка | settings и summary показываются совместно только при совпадении settings.version и summary.calculation.settingsVersion; иначе ограниченный refetch/устаревшее состояние |
| Изменение | clean→dirty; baseVersion не меняется |
| Save | dirty→saving, один запрос с expectedVersion=baseVersion; блокировка всех редактируемых полей, повторного save/reset и неоднозначного ухода во время запроса |
|200 | saved/clean, база и draft из подтверждённого settings; summary из того же ответа |
|422/предкоммитный500 | error, draft доступен, прежние результаты остаются; baseVersion не подменяется |
| Внешнее обновление | clean — обновить базу; dirty — сохранить draft и перейти conflict, показать актуальную версию отдельно |
|409 | conflict, никакого rebase/force/автоповтора; действующая модель не изменена |
| Обрыв/потеря ответа | uncertain; сохранить candidate/baseVersion/draft, перечитать settings+summary; не объявлять собственный успех по совпадению значений |
| Явный повтор uncertain | только пользовательский шаг с прежним expectedVersion; уже выполненный запрос приведёт к409, а не перезаписи |
| Загрузить текущие | подтверждение отказа от draft, затем актуальные база/version; автоматического слияния нет |
| Уход | диалог stay/discard, useBlocker дляSPA/Back, beforeunload для reload/закрытия |

Global draft/guard context доступен authenticated layout, Settings и logout flow.
До logoutPOST требуется решение о dirty/uncertain draft; при отказе logout сохраняются
экран и текущая сессия002. Явный успешный выход очищает контексты и sensitive UI state.
При401 защищённый экран скрывается, запросы останавливаются; временный draft может
оставаться только в памяти прежнего userId до повторного входа того же пользователя,
после которого version перечитывается. При другом userId/явном выходе очищается.
Черновик не хранится на сервере/между устройствами; закрытие вкладки после системного
подтверждения может его потерять, восстановление закрытых сессий не обещается.

## 6. UpdateState

transport:sse|polling|offline; data:initial_loading|refreshing|current|stale|error;
lastSuccessfulReadAt,error,authState. SSE open сам по себе не доказывает свежесть данных.
UseLiveUpdates централизует прежний EventSource/15sec polling и cleanup, без server job.
При stream error и успешном HTTP опросе — polling; оба отказали —stale/offline,
последний bundle остаётся помеченным; успешное чтение автоматически восстанавливает.
На401 — signed_out/re-auth, а не бесконечный retry. Проверка /auth/me периодически
нужна и при открытом SSE: сервер сейчас проверяет сессию при открытии потока, не
на каждом событии. После обнаружения401 поток закрывается. Это не обещание мгновенного
отзыва уже открытого server stream; auth mechanism и его scope002 не переписываются.
Не выводить active success/current по navigator.onLine без ответа API.

## 7. ExportOperation

idle→loading(captured selection+sort+runId)→complete либо error/conflict/unauthorized.
Параметры фиксируются на клик; изменение UI не изменяет уже отправленный экспорт.
Повтор не автоматический. При stale_calculation перечитать список и предложить новый
экспорт. Global snapshot не pin-ится на всё время жизни страницы, только на запрос.
Все csv rows одной версии; download после полного чтения body. Формат/защита текста
определены в contracts/api.md. Никаких saved segments или CRM-статусов.

## 8. Статические бренд-материалы (без новой модели хранения)

`frontend/public/brand/asset-manifest.json` описывает тип материала, оригинальный
вариант, источник/физическую страницу, checksum, лицензию и происхождение полного
шрифта. Отделяет оригинальный знак от наших UI-иконок. Не содержит пользовательских
данных, не требует SQLite-таблицы или API. Exo 2 основной, Inter дополнительный;
правила подлинности, охранного поля и палитры — contracts/brand.md.
