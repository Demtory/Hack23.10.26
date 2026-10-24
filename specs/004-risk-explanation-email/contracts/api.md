# API Contract: деталь клиента

Действует для `GET /api/v1/customers/{id}` (`CustomerDetailOut`). Путь, авторизация
(cookie или Bearer) и заголовки `X-Calculation-*` не меняются.

## Добавленные поля

| Поле JSON | Тип | Примечание |
|---|---|---|
| `summaryDetails` | `string[]` | раскрываемое пояснение |
| `emailDraft` | `object \| null` | см. ниже |

`emailDraft`:

```json
{
  "situation": "funds_gap",
  "situationLabel": "Не хватает денег",
  "subject": "service-0006: продление через 2 дня, не хватает 2,50 €",
  "body": "Здравствуйте!\n\n…\n\nХорошего дня!\nКоманда Aéza",
  "recipient": "user-0006@example.test",
  "serviceId": 6,
  "serviceName": "service-0006"
}
```

`situation` — одно из `prolong_wait`, `blocked`, `suspended`, `funds_gap`,
`expiry_auto_off`, `unknown`, `on_track`.

## Пример ответа (клиент 6, seed)

```json
{
  "id": 6,
  "email": "user-0006@example.test",
  "score": 89.0,
  "level": "high",
  "summary": "На продление service-0006 нужно 5,50 €, на балансе 3,00 € — не хватает 2,50 €.",
  "summaryDetails": [
    "service-0006 истекает 25 октября — через 2 дня.",
    "Стоимость продления: 5,50 €. Доступно на балансе: 3,00 €.",
    "Не хватает 2,50 €.",
    "Автопродление отключено: автоматически услуга не продлится.",
    "Под риском 2 услуги на 10,97 €; ожидаемые потери — 6,44 €.",
    "Оценка риска: 89 из 100 — высокий уровень."
  ],
  "emailDraft": {
    "situation": "funds_gap",
    "subject": "service-0006: продление через 2 дня, не хватает 2,50 €",
    "recipient": "user-0006@example.test",
    "serviceId": 6,
    "serviceName": "service-0006"
  }
}
```

## Совместимость

- Прежние поля и типы сохранены; тест `test_detail_contract_and_old_cache` обновлён
  только добавлением двух ключей.
- Записи без новых полей читаются: тексты собираются из сохранённого `detail`.
- `GET /api/v1/customers` (список) не меняется.
- `openapi.json` пересобран штатным `scripts/export_openapi.py`.
