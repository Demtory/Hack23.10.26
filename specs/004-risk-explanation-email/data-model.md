# Data Model: объяснение риска и письмо клиенту

Новых таблиц и миграций нет. Модель — производные поля ответа `GET /api/v1/customers/{id}`.

## CustomerDetail (расширение)

| Поле | Тип | Источник | Обязательность |
|---|---|---|---|
| `summary` | string | `messages._headline` | всегда; для `unknown` равна `unknownReason` |
| `summaryDetails` | string[] | `messages._details` | всегда, 2–6 фактов |
| `emailDraft` | EmailDraft \| null | `messages._email` | всегда для существующих ситуаций |

Существующие поля (`score`, `level`, `drivers`, `services`, `money`, `explanationRules`,
`unknownReason`, `isEstimated`) не меняются.

## EmailDraft

| Поле | Тип | Смысл |
|---|---|---|
| `situation` | enum | `prolong_wait`, `blocked`, `suspended`, `funds_gap`, `expiry_auto_off`, `unknown`, `on_track` |
| `situationLabel` | string | подпись для чипа в диалоге: «Ждёт оплаты», «Не хватает денег» и т.д. |
| `subject` | string | тема письма с суммой и/или сроком |
| `body` | string | текст письма, `\n` между абзацами, подпись «Команда Aéza» |
| `recipient` | string | email клиента из аккаунта |
| `serviceId` | int \| null | услуга, о которой письмо |
| `serviceName` | string \| null | её имя для подстановки |

## Правила выбора ситуации

Проверяются по порядку; первое совпадение задаёт `situation`:

| # | Условие | `situation` |
|---|---|---|
| 1 | `score is None` | `unknown` |
| 2 | у главной услуги `status == prolong_wait` | `prolong_wait` |
| 3 | `status == blocked` | `blocked` |
| 4 | `status == suspended` | `suspended` |
| 5 | цена > 0 и доступно < цены | `funds_gap` |
| 6 | автопродление выключено и `expiryDays <= 7` | `expiry_auto_off` |
| 7 | иначе | `on_track` |

Главная услуга — максимальная по `score`, при равенстве — по цене.

Доступные деньги: `availableCents` из расчёта (баланс + бонусы при `unlocked`,
с учётом `includeWithdrawBalance`); для старых записей — баланс + доступные бонусы.

## Инварианты

- `summary` не содержит подстрок «добавк», «минимум», «ограничени», «баллов».
- Суммы в текстах совпадают с `money.expectedLoss`/`price`/балансом из того же ответа.
- `emailDraft.recipient == customer.email`.
- `unknown` не имеет оценки, `emailDraft` для него — win-back или уточнение.
- В `body` нет placeholder-скобок и незаполненных подстановок.

## Хранение

`customer_scores.detail` (JSON) — без изменений схемы. Новые поля вычисляются при
сериализации, если отсутствуют; в новых расчётах `summaryText` уже содержит короткий
заголовок, `availableCents` сохраняется для точной проверки нехватки денег.
