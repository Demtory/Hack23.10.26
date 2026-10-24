# API contract:003 (план, ещё не реализован)

Сохраняются пути/поля/единицы/авторизация001/002. Новые интерфейсы ниже —
совместимые расширения FR-006/007/011/012/015/016/022. OpenAPI экспортировать
штатным scripts/export_openapi.py только после реализации, сейчас файл не менять.

## 1. Единые условия списка/топа/CSV

GET /api/v1/customers сохраняет q/level/sort/order/page/pageSize и ответ002.
Новый необязательный urgency: all(default), expired,48h,7d; неизвестный код422.
Поиск по email сохраняет прежний LIKE, включая семантику%/_, регистр и параметризацию.
Level и сортировки002 не меняются. UI отправляет эффективный trimmed q, пустой level
не отправляет. Все условия AND; сортировка прежняя whitelist +id ASC при равенстве.

- asOf берётся из выбранного latest score_run внутри read snapshot.
- expired: expiresAt <= asOf;48h: asOf < expiresAt <= asOf+48h;
  7d: asOf < expiresAt <= asOf+7суток.48h входит в7d.
- EXISTS исходной services с owner_id=account.id, status IN active/suspended/prolong_wait.
  Deleted/blocked исключаются только из срочности, не из модели или all.
- Сравниваются канонические UTC ISO milliseconds; bounds вычислены datetime/timedelta,
  не временем браузера и не float julianday. Никакого пересчёта score при фильтрации.
- Unknown с подходящей исходной услугой включается, даже если detail.services пуст.
- Одна read_transaction охватывает run/count/items/top/global summary/account JOIN.
  Общие небольшие helpers WHERE/order использовать и в CSV. Считать клиента один раз.
- topLosses — максимум5 по expected_loss DESC/id ASC из всей выбранной группы;
  page/sort на топ не влияют. Summary остаётся глобальной и явно так обозначена.
- Ответ002 items/total/page/pageSize/topLosses/summary/calculation сохранён без изменения.

## 2. GET /api/v1/customers/export.csv

Объявить route до /customers/{id}. Cookie OR Bearer через require_user как002;
без действительных credentials401. Новый экспорт не становится публичным.
Параметры q/level/urgency/sort/order совпадают со списком; обязательный runId:int>=1
фиксируется из отображённого bundle на момент нажатия. Page/pageSize не используются.
Неверные параметры/отсутствующий runId422. Во время операции UI не меняет captured query.

Порядок: _ensure_summary → read_transaction → latest run → проверить runId →
общий WHERE/order → все выбранные строки и metadata → сформировать полные bytes.
Несовпадение latest и запрошенного runId:409 detail.code=stale_calculation; не пытаться
JOIN старый кэш с текущими accounts/services. Предложить обновить список и повторить
экспорт явным действием. После начала read snapshot параллельный writer допустим:
файл целиком относится к pinned старому состоянию. Последующие live updates не меняют его.
Ноль строк:409 detail.code=empty_selection, без файла; UI при известном total0 блокирует
экспорт с пояснением. До полной подготовки нет успешного HTTP200/StreamingResponse.

Успех200: Content-Type text/csv;charset=utf-8; UTF-8 BOM; comma;CRLF;
все поля QUOTE_ALL через stdlib csv.writer. Один header, без комментариев/sep=/preamble.
Content-Disposition:attachment с безопасным серверным ASCII filename,
например customers-run-123.csv; Content-Length и Cache-Control:no-store.
Клиент читает Blob целиком и лишь затем создаёт download; HTTP/networkfailure
не создаёт частичный успешный файл. Body read failure не скрывается статусом200.

Столбцы в фиксированном порядке:

| Данные | Формат |
|---|---|
| customer_id | десятичный INTEGER, без JS-конвертации |
| email | пользовательский текст с безопасным кодированием ниже |
| balance_eur,total_replenished_eur | точные строки с точкой и2 decimals |
| score | опубликованная оценка; NULL — пустая ячейка, не0 |
| risk_level | high/medium/low/unknown, без подмены unknown |
| expected_loss_eur,amount_at_risk_eur | точные строки из сохранённых INTEGER cents |
| services_at_risk | целое, по сохранённым порогам |
| filter_q,filter_level,filter_urgency | эффективные условия; нет level — пусто |
| sort,order | фактические сортировка/направление |
| run_id,settings_version | pinned calculation |
| as_of,calculated_at | UTC ISO времени run, сZ |
| source_generated_at | пусто: исходный формат не передаёт дату формирования |
| currency,csv_format_version | EUR,1 |

Метаданные повторены в каждой строке, поэтому таблицу можно разбирать обычным CSV
parser. Нет отдельных ZIP/JSON файлов. Парсер проверяет одинаковый контекст всех строк.
Денежные строки строятся целочисленным делением/остатком по100, без float, _list_item,
euros() helper или округления через JavaScript. Примеры:0→0.00;
9007199254740993→90071992547409.93;9223372036854775807→92233720368547758.07.
Производные INTEGER — уже сохранённый результат модели; модель не пересчитывается.
Большие ID/EUR следует импортировать в табличный редактор как текст, иначе его
автоматическая числовая интерпретация может потерять точность. XLSX не добавляется.

### Безопасное текстовое кодирование CSV

Только untrusted email/filter_q кодируются перед csv.writer. Для проверки опасного
начала используется NFKC-копия со снятыми ведущими whitespace/control/format chars;
исходная строка не нормализуется и не обрезается. Начало=,+,-,@ (включая full-width),
ведущие control/format chars либо исходный prefix text: требуют добавления одного
ASCII prefix text: к исходной строке. Прочие строки неизменны. Таким образом
text:=1+2 не исполняется; исходное text:abc превращается в text:text:abc.
Декодирование в этих двух колонках снимает один ведущий text:; оно обратимо.
Встроенные quotes/delimiters/newlines экранирует csv.writer; формулы не используются
даже для длинных чисел. Контрактное тестирование покрывает точные encoded bytes.
Это документированная защитная форма текста, не изменение исходных данных.
Проверить первоначальный импорт и save/reopen в доступном редакторе; не обещать
универсальную совместимость любого стороннего spreadsheet. Источник рисков:
[OWASP](https://community.owasp.org/attacks/CSV_Injection).

## 3. Условное сохранение настроек

PATCH /api/v1/model/settings принимает дополнительное expectedVersion?:strict int>=1.
Это служебная precondition, не настройка/признак; в payload SQLite не сохраняется.
Пример нового UI: {"weights":{"funds_gap":0.8},"expectedVersion":4}.
Сохраняются partial PATCH, null-omission и все валидаторы001/002.

В существующей BEGIN IMMEDIATE сначала get_settings, затем сравнение version,
только после него merge/validate/save/recompute/response preflight/commit.
Mismatch409: {"detail":{"code":"settings_version_conflict","expectedVersion":4,
"currentVersion":5,"message":"Настройки изменены другим пользователем"}}.
При409 snapshot/payload/version/time/runs/results остаются прежними.
Новый UI всегда передаёт baseVersion загруженного черновика и на409 сохраняет его.
Нельзя автоматически менять baseVersion на currentVersion, сливать или force-save.
Переход к новой версии требует подтверждения отказа от черновика.

Отсутствующий/null expectedVersion сохраняет прежнее безусловное поведение legacy
consumer. Поэтому гарантия относится к новому UI/условным запросам; старый writer
может сохранить без precondition, но повышает version и делает старый draft конфликтным.
Два одновременно условных PATCH одной версии: один200, второй409. Проверка/запись
не разделяются соединениями. Успешный response settings+summary сохраняет контракт002.
409 не запускает SSE пересчёта;422/500/rollback/restart гарантии001/002 сохраняются.

## 4. Время/контекст карточки и исходного снимка

GET /customers/{id}: добавить calculation,asOf,updatedAt к существующим полям
одним read snapshot latest run + detail. Ввести CustomerViewOut поверх прежнего
CustomerDetailOut; не делать контекст обязательным для cached detail_response,
который используется preflight расчёта001. Никаких правок compute/detail cache JSON.
404 не подменяется другим клиентом. Не JOIN отдельную summary к другой версии детали.

GET /source/snapshot: прежнее body с тремя массивами и точными INTEGER без изменений.
В read snapshot source+latest run добавить X-Calculation-Run-Id,
X-Calculation-Settings-Version,X-Calculation-As-Of,X-Calculation-Updated-At.
_ensure_summary до read transaction. Это контекст расчёта источника, НЕ дата формирования.
UI читает headers и raw text вместе; download продолжает использовать raw text.
Обычный source JSON-parser остаётся совместимым. Не добавлять metadata внутрь снимка.

## 5. Клиентский транспорт и ошибки

api.ts сохраняет cookie/Bearer priority сервера, credentials:include и logout002.
Минимально выделить общий requestResponse с авторизацией/проверкой HTTP, затем
существующие JSON/text wrappers и export Blob/source text+headers; не дублировать auth.
Объединять init.headers после ...init корректно: сейчас ...init может затереть
вычисленные headers; обязательна регрессия сохранения Authorization с custom headers.
ApiError хранит status и структурированный detail.code, сообщение показывается человеку.
401 защищённого запроса закрывает доступ к данным, останавливает SSE/опрос и предлагает
вход; ошибка logout по-прежнему не объявляет выход успешным.500/422 не равны networkerror.
Потеря ответа на save → uncertain, перечитать GET settings/summary с проверкой versions;
совпадение candidate не доказывает собственный успех, автоматического retry нет.
Файл openapi.json обязан полностью совпадать с live schema после реализации.
