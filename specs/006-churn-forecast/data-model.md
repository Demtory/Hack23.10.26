# Data Model: прогноз оттока

Новых таблиц нет: ответ считается из `customer_scores.detail` последнего прогона.

## GET /api/v1/analytics/forecast

| Поле | Тип | Смысл |
|---|---|---|
| `asOf` | ISO-8601 | срез расчёта |
| `pastDays`, `horizonDays` | int 1…90 | окна факта и прогноза |
| `currency` | string | `EUR` |
| `fact[]` | `{date, services, customers}` | истёкшие и не продлённые услуги по дням |
| `forecast[]` | `{date, services, expectedNonRenewals, expectedLoss}` | прогноз по дням |
| `totals` | `{factServices, factCustomers, forecastServices, servicesAtRisk, expectedNonRenewals, expectedLoss}` | итоги окна |
| `note` | string | почему нет исторических удалений |

## Правила

- Факт: `expiresAt ≤ asOf`, статус ≠ `deleted`, дата попадает в окно `[asOf-pastDays+1, asOf]`.
- Прогноз: `asOf < expiresAt ≤ asOf+horizonDays`, статус ≠ `deleted`.
- Ожидаемые непродления: `Σ P(score)` по услугам дня.
- Ожидаемые потери: `Σ round(P(score) × price × (1 − mitigation))`; `mitigation`
  берётся из денежного блока клиента.
- Услуга с ценой 0 учитывается в счётчике услуг и не добавляет деньги.
- У клиента без оценки услуг в деталях нет → он не попадает в прогноз.
