# API Contract Changes: 002

Планируемые изменения. Все существующие пути/методы и прежние поля сохраняются.
Валюта отображения — EUR, входной снимок — целые евроценты.

## 1. PUT /api/v1/source/snapshot

Прежний полный camelCase Snapshot. Шесть денежных полей — strict JSON integers
0…9223372036854775807. amount1001/5000 допустимы. Строки, boolean, float-литералы
включая100.0/1e2, дроби, пропуски/null, отрицательные и overflow дают422 с detail,
loc,msg,type без сырого input/ctx и без частичного применения.

При внутреннем отказе до commit — прежний безопасный500 и rollback. Успешный
ответ сохраняет counts/summary; summary получает calculation из собственного
нового расчёта. После commit нельзя обещать откат при потере доставки ответа.

JSON Schema: type integer, minimum0, maximum9223372036854775807 и description
о strict-типе. Integer в стандарте JSON Schema допускает математически целое100.0;
реальное ограничение типа проверяется HTTP-тестами. UI upload отправляет текст
исходного JSON без parse→stringify, GET/download сохраняет канонический текст.

## 2. GET /api/v1/customers

Параметры sort/order/level/q/page/pageSize и их прежние ограничения сохраняются.
q использует существующий поиск email LIKE, level — high/medium/low/unknown.
Те же условия применяются count/items/top. Валидность sort/order проверяется
как прежде, даже если они не влияют на top.

К прежнему ответу items,total,page,pageSize добавляются:

| Поле | Контракт |
| --- | --- |
| topLosses | CustomerListItem[], максимум5, вся q/level-группа; expectedLoss DESC, id ASC |
| summary | прежняя глобальная Summary без вложенного calculation; не фильтруется q/level |
| calculation | {runId:int,settingsVersion:int,thresholds:{medium:number,high:number}} |

CustomerListItem сохраняет id,email,balance,totalReplenished,score,level,
expectedLoss,amountAtRisk,servicesAtRisk. Изменение page/pageSize/sort/order
не меняет top при неизменных q/level и run. Нулевые/unknown не исключаются скрыто.
При пустой группе items/top пусты,total0, глобальная summary остаётся глобальной.

Все части ответа читаются в одном SQLite read snapshot из одного run_id,
включая accounts JOIN; settings отдельно для порогов не читаются.
Старая программа, читающая только items/total/page/pageSize, продолжает работать.
Новые DTO должны описать реально возвращаемые добавления в OpenAPI.

## 3. GET /api/v1/analytics/summary и mutation summary

Прежние поля countsByLevel,totalCustomers,scoredCustomers,servicesAtRisk,
expectedLoss,amountAtRisk,coverage,aggregateCoverage,underfundedCustomers,
avgScore,asOf,updatedAt,currency сохраняются. Добавляется calculation той же
структуры, что в списке; значения относятся к одному опубликованному run.
В PATCH/PUT они относятся к созданному ими run и валидируются/сериализуются
до commit. Обычная summary не превращается в фильтрованную.

## 4. GET /api/v1/customers/{id}

Реальный маршрут и поля CustomerDetailOut не меняются. Сохранённый OpenAPI
исправляет {account_id} на {id}. Карточка считает рискованные услуги по готовым
service.level medium/high. Medium/high включают нижнюю границу; unknown не число.
Новые поля настроек ради повторной классификации не требуются.

## 5. Cookie/Bearer и logout

Защищённые операции публикуют OpenAPI security как OR:
`[{"APIKeyCookie":[]},{"HTTPBearer":[]}]`, не один объект с обоими ключами.
Cookie scheme: apiKey/in cookie/name sid; Bearer: type http/scheme bearer.
Runtime без действующего credential возвращает401; optional dependency не
означает разрешённый анонимный доступ к клиентам/настройкам/источнику.
Агрегированные /metrics и существующие публичные системные операции не закрываются
побочно. Login остаётся публичным и сохраняет token/accessToken и cookie.

POST/auth/logout использует те же необязательные credential sources и дополнительно
security-альтернативу {}. Без токена, при повторном выходе и expired/revoked —200
{ok:true}; выбранный токен удалён на сервере, cookie удалена. После выхода token
не действует ни как cookie, ни как Bearer, включая restart.
При cookieA+BearerB отзывается только A; отсутствие fallback с invalid cookie
сохраняется. Независимые сессии не отзываются. Ошибка удаления не выдаётся за200.

## 6. Настройки и внутренние изменения

GET/PATCH/model/settings сохраняют публичные ключи и partial-update semantics.
Внутреннее feature_schema_version не является новым пользовательским параметром.
Новый известный код появляется в features/weights; для обновляемой конфигурации
его отсутствующий вес0, для новой базы — объявленный default. Явный сохранённый
вес не переписывается. Неверные/неизвестные keys сохраняют отказ.
Upgrade/settings/results фиксируются как одна согласованная версия.

## 7. OpenAPI-проверка

Экспорт штатным scripts/export_openapi.py после изменения приложения, не в фазе plan.
Сравнить полный JSON с create_app().openapi() той же версии без запуска рабочей БД;
проверить DTO новых полей, денежные bounds/descriptions, OR-security защищённых
операций, optional logout и реальное выполнение cookie/Bearer/401.
Для JSONResponse мутаций явно валидировать payload до commit: response_model
сам по себе не проверяет уже созданный Response. Не изменять OpenAPI-файл вручную
отдельно от кода, иначе равенство схем потеряется.
