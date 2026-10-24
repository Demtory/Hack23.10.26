# API Contract: прогноз

`GET /api/v1/analytics/forecast` — только с сессией (cookie или Bearer), иначе 401.

Параметры: `pastDays` (1…90, по умолчанию 30), `horizonDays` (1…90, по умолчанию 30),
`bucketDays` (1…30, по умолчанию 1 — дни; 7 — недели). Выход за границы → 422.
Каждая точка содержит `date` и `end` (интервал).

```json
{
  "asOf": "2026-10-23T18:00:00.000Z",
  "pastDays": 30,
  "horizonDays": 30,
  "currency": "EUR",
  "fact": [{ "date": "2026-10-22", "end": "2026-10-23", "services": 2, "customers": 1 }],
  "forecast": [
    { "date": "2026-10-24", "end": "2026-10-30", "services": 4, "expectedNonRenewals": 1.7, "expectedLoss": 6.54 }
  ],
  "totals": {
    "factServices": 8, "factCustomers": 3,
    "forecastServices": 7, "servicesAtRisk": 3,
    "expectedNonRenewals": 1.85, "expectedLoss": 7.58
  },
  "note": "Исторических удалений нет: в данных отсутствует дата удаления услуги. …"
}
```

Инварианты: длины `fact`/`forecast` равны окнам; `totals` совпадают с суммами по дням;
`expectedNonRenewals` — дробное число (сумма вероятностей).

## GET /api/v1/analytics/forecast/day

`date` — начало интервала, `end` — конец включительно (по умолчанию равен `date`),
`kind` — `fact` или `forecast`. Возвращает `date`, `end`, `kind`, `services`, `customers`,
`expectedNonRenewals`, `expectedLoss`, `items[]` (услуга, клиент, email, цена, score,
уровень, статус, вероятность и ожидаемые потери для прогноза), `truncated`.
Ошибки: 401 без сессии, 422 на неверную дату, `end < date`, факт после среза,
прогноз не в будущем.
