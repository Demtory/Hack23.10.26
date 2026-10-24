# API Contract: прогноз

`GET /api/v1/analytics/forecast` — только с сессией (cookie или Bearer), иначе 401.

Параметры: `pastDays` (1…90, по умолчанию 30), `horizonDays` (1…90, по умолчанию 30).
Выход за границы → 422.

```json
{
  "asOf": "2026-10-23T18:00:00.000Z",
  "pastDays": 30,
  "horizonDays": 30,
  "currency": "EUR",
  "fact": [{ "date": "2026-10-23", "services": 2, "customers": 1 }],
  "forecast": [
    { "date": "2026-10-25", "services": 1, "expectedNonRenewals": 0.84, "expectedLoss": 4.04 }
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
