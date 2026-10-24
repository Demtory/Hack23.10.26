# Tasks: 006 — график оттока

**Ветка:** `main`. Все задачи выполнены 2026-10-24.

- [x] T001 `build_forecast` в `backend/app/forecast.py`: окна факта и прогноза,
  суммы по дням, `note`. Файлы: `backend/app/forecast.py`. Покрытие: FR-002–FR-004.
- [x] T002 `latest_details` в `backend/app/store.py`, DTO `ForecastOut` в `schemas.py`.
  Покрытие: FR-002.
- [x] T003 Эндпоинт `GET /api/v1/analytics/forecast` с валидацией окон и деньгами в EUR.
  Файлы: `backend/app/api.py`. Покрытие: FR-001, FR-005.
- [x] T004 Тесты `backend/tests/test_forecast.py`: структура, детерминизм, новый срок,
  удалённые услуги, 401, 422. Покрытие: SC-001–SC-003.
- [x] T005 Компонент `ForecastChart.tsx`: два ряда, легенда, подписи дат, итоги, note.
  Покрытие: FR-006, FR-007.
- [x] T006 Вставка блока в «Сводку», стили, адаптив. Покрытие: SC-004.
- [x] T007 `openapi.json` (16 путей), скриншоты 02 и 12, README/ARCHITECTURE/STATUS.
  Покрытие: SC-005.
- [x] T008 Слайд 7 в питч-деке и пересборка `.pptx`. Покрытие: презентация бонуса.
