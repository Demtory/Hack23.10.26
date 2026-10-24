# Quickstart validation: 004

Инструкция для проверки после реализации. Используются только временные БД; рабочая
`data/app.db`, `.env`, секреты и внешние сервисы не затрагиваются.

## 1. Окружение

```bash
cd <project root>
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements-dev.txt
npm --prefix frontend ci
```

## 2. Проверки

```bash
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests data/raw/test_generate.py
npm --prefix frontend run build
PYTHONPATH=backend .venv/bin/python scripts/export_openapi.py
```

Ожидаемо: `404 passed` (baseline 384 + 20 новых), успешная сборка, `openapi.json`
без изменений после повторного экспорта.

## 3. Ручная проверка API

```bash
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --port 8000
curl -s -c /tmp/rd.cookies -X POST localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.test","password":"admin123"}'
curl -s -b /tmp/rd.cookies localhost:8000/api/v1/customers/6 | python3 -m json.tool
```

Проверить:

- `summary` — одно-два предложения, нет слов «добавка», «минимум», «ограничение»;
- `summaryDetails` — 3–6 фактов;
- `emailDraft.recipient` совпадает с `email`, `subject` и `body` непустые,
  `body` заканчивается «Команда Aéza».

## 4. Ручная проверка интерфейса

Открыть `http://localhost:8000`, войти `admin@example.test` / `admin123`,
перейти в «Клиенты» → клиент 6.

1. Заголовок «Почему риск» читается без остальных блоков.
2. «Подробное пояснение» раскрывается и показывает факты.
3. «Детали расчёта» скрыты по умолчанию; у клиента без правил блока нет.
4. «Письмо клиенту» открывает диалог; текст редактируется; «Скопировать» вставляет
   тему и текст; mailto содержит адресата.
5. Escape закрывает диалог, данные не меняются.
6. Ширина 390 px: нет горизонтального скролла, кнопка и диалог доступны.

## 5. Что не проверяется

- Реальная отправка письма (SMTP вне объёма).
- Английская локализация текстов.
- Клиенты с именами: в данных есть только email.
