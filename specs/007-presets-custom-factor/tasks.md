# Tasks: 007 — пресеты весов и седьмой признак

**Ветка:** `main`. Выполнено 2026-10-24.

- [x] T001 Таблица `weight_presets` и модуль `presets.py` (встроенные наборы,
  валидация, CRUD). Файлы: `backend/app/db.py`, `backend/app/presets.py`.
- [x] T002 Эндпоинты `GET/POST /model/presets`, `DELETE /model/presets/{id}`,
  DTO `PresetIn/PresetOut/PresetListOut`. Файлы: `backend/app/api.py`, `schemas.py`.
- [x] T003 Признак `auto_off_share`: значение, метаданные, поколение 2, DEFAULT_SETTINGS.
  Файлы: `backend/app/scoring.py`. Покрытие: FR-006.
- [x] T004 Тесты пресетов (8) и обновление тестов поколений под реальное поколение 2.
  Файлы: `backend/tests/test_presets.py`, `test_settings_upgrade.py`.
- [x] T005 UI: блок «Наборы весов», применение в черновик, «Сохранить как набор»,
  удаление с подтверждением, статусы и ошибки. Файл: `frontend/src/pages/Settings.tsx`.
- [x] T006 Стили карточек пресетов и отступ заголовка признака. Файл: `styles.css`.
- [x] T007 e2e: применение пресета и сохранение своего набора. Файл: `e2e/panel.spec.ts`.
- [x] T008 Документация: README, MODEL, DEFENSE, QNA, STATUS; дека и PDF обновлены.
