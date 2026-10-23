# Статус реализации

Обновлено: **2026-10-23 21:20 MSK**.

## Что готово

| Требование кейса | Статус | Где проверить |
|---|---|---|
| Веб-панель: score, уровень, причины | ✅ | `/` после логина, карточка клиента |
| «Нет оценки» при нехватке данных | ✅ | клиенты 3 и 8: «Все услуги удалены» |
| Топ клиентов: ID, email, баланс, пополнения, score | ✅ | `GET /api/v1/customers` |
| Сортировка по ID, email, балансу, пополнениям в обе стороны | ✅ | колонки таблицы / query `sort`, `order` |
| Сортировка по всему набору, не по странице | ✅ | SQL + `total` |
| Коэффициенты редактируются в панели | ✅ | «Настройки модели» |
| Настройки переживают перезапуск | ✅ | таблица `settings`, `version` |
| Пересчёт без reload | ✅ | SSE `/api/v1/events` + polling |
| Денежная оценка с ценой, балансом, риском | ✅ | карточки + `money` в детали |
| `/metrics` в формате Prometheus | ✅ | `GET /metrics` |
| Согласованность UI / summary / metrics | ✅ | один `score_runs` + `customer_scores` |
| Docker Compose | ✅ | `compose.yaml` |
| Аутентификация | ✅ | login/me/logout, cookie, 401 |
| Swagger + OpenAPI-файл | ✅ | `/api/v1/docs`, `openapi.json` |
| README + модель + архитектура + «как добавить признак» | ✅ | `README.md`, `docs/` |
| Расширяемость признаков | ✅ | `FEATURES_META`, `backend/app/scoring.py` |
| Комментарий `Aéza` | ✅ | `backend/app/main.py`, `Dockerfile` |
| Тесты | ✅ | `backend/tests`, 5 passed |

## Ещё не сделано (P1/P2)

- OIDC + fallback — осознанно отложено.
- График исторических удалений: в данных нет дат удаления. Можно добавить
  накопление снапшотов и прогноз непродлений по `expiresAt`.
- Prometheus + Grafana в compose (метрики уже отдаются).
- Нагрузочный тест на 10k+ клиентов.
- Бэкап-видео демо и финальная репетиция.

## Быстрая проверка

```bash
cp .env.example .env
docker compose up --build
# http://localhost:8000 — admin@example.test / admin123

curl -s localhost:8000/metrics | head
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/api/v1/customers   # 401
```

```bash
PYTHONPATH=backend .venv/bin/pytest -q backend/tests
```
