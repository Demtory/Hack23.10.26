# Quickstart validation: 007

```bash
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests
npm --prefix frontend run build
cd frontend && npx playwright test panel.spec.ts
PYTHONPATH=backend .venv/bin/python scripts/export_openapi.py
```

Ожидаемо: `449 passed`, сборка, `10 passed` e2e, 20 путей в OpenAPI.

Проверка API:

```bash
curl -s -c /tmp/c -X POST localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' -d '{"email":"admin@example.test","password":"admin123"}'
curl -s -b /tmp/c localhost:8000/api/v1/model/presets | python3 -m json.tool
curl -s -b /tmp/c -X POST localhost:8000/api/v1/model/presets \
  -H 'Content-Type: application/json' \
  -d '{"name":"Мой набор","weights":{"expiry_pressure":0.4,"funds_gap":0.4,"autorenew_off":0.05,"status_pressure":0.05,"payment_history":0.05,"commitment":0.05,"auto_off_share":0}}'
```

UI: «Настройки модели» → блок «Наборы весов» → «Деньги важнее» → вес «Нехватка денег»
становится 0,45 → «Сохранить» → версия и цифры меняются. «Сохранить как набор»
создаёт свой набор; «×» удаляет.
