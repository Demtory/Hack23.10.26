# Implementation Plan: график оттока

**Branch**: `main` | **Date**: 2026-10-24 | **Spec**: [spec.md](spec.md)

## Summary

Эндпоинт `/api/v1/analytics/forecast` считает факт истечений и прогноз непродлений
по сохранённым деталям последнего расчёта; на «Сводке» появляется блок с двумя рядами
столбцов, легендой, датами и честным примечанием. Стек, формулы и контракты не меняются.

## Technical Context

**Backend**: Python 3.12, FastAPI, SQLite; данные — JSON `customer_scores.detail`
последнего прогона, вероятность — существующая `probability(score, settings)`.
**Frontend**: React 18 + TypeScript, CSS-столбцы без новых зависимостей.
**Testing**: pytest (`backend/tests/test_forecast.py`), сборка, браузер.

## Constitution Check

| Принцип | Как соблюдён |
|---|---|
| I | Тот же стек, без новых зависимостей |
| II | «График оттока» — бонус кейса, отмечено в spec |
| III | Только прогноз; формулы и UI не переписаны |
| IV | Новый путь аддитивен, прежние ответы не меняются |
| V | Ошибки/пустые данные не ломают страницу — блок просто не рисуется |
| VI | Прогноз строится из того же score, что и карточка |
| VII | Нет дат удаления — прямо сказано, а не заменено нулями |
| VIII | Ожидаемое число непродлений — сумма вероятностей, подписано |
| IX | 9 регрессионных тестов |
| X | Спека/план/задачи Spec Kit, коммит в main по просьбе команды |

## Structure

```text
backend/app/forecast.py          # build_forecast: окна, суммы, note
backend/app/store.py             # latest_details
backend/app/api.py               # GET /analytics/forecast
backend/app/schemas.py           # ForecastOut
frontend/src/components/ForecastChart.tsx
frontend/src/pages/Dashboard.tsx # вставка блока
docs/screenshots/12-forecast.png
```

## Risks

- Ряды разрежены на 10 клиентах — на больших данных график плотнее, логика та же.
- Прогноз зависит от текущих настроек модели; при их смене пересчитывается весь снимок.
- Сумма за 30 дней не равна общей `expected_loss` сводки (там все услуги) — это разные
  горизонты, в интерфейсе подписано.
