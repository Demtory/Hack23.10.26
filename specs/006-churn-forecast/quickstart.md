# Quickstart validation: 006

```bash
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests
npm --prefix frontend run build
PYTHONPATH=backend .venv/bin/python scripts/export_openapi.py
```

Ожидаемо: `431 passed`, сборка, `openapi.json` с 16 путями.

Проверка API:

```bash
curl -s -c /tmp/c -X POST localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' -d '{"email":"admin@example.test","password":"admin123"}'
curl -s -b /tmp/c localhost:8000/api/v1/analytics/forecast | python3 -m json.tool
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/api/v1/analytics/forecast   # 401
```

UI: «Сводка» → блок «Когда наступает отток»: слева тёмные столбцы (факт), справа
голубые (прогноз), подписи дат, итоги и примечание. Проверить на 1440 и 390 px.
