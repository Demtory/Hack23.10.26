# Implementation Plan: Понятная причина риска и письмо клиенту

**Branch**: `main` | **Date**: 2026-10-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-risk-explanation-email/spec.md`

## Summary

Заменить склейку `summaryText` в `scoring.py` (имя услуги + первые два признака + метки
правил + счётчик услуг) на детерминированный сборщик текстов `app/messages.py`, который
отдаёт короткий заголовок, список фактов и черновик письма клиенту под одну из семи
ситуаций. Тексты считаются на бэкенде и попадают в ответ `GET /api/v1/customers/{id}`;
фронтенд показывает заголовок, раскрываемое пояснение и диалог письма с копированием
и `mailto:`. Стек, формулы, пороги и контракты 001–003 сохраняются.

## Technical Context

**Language/Version**: Python 3.12 (FastAPI, Pydantic v2), React 18 + TypeScript 5 + Vite 5.

**Primary Dependencies**: существующие; новых runtime-зависимостей нет. Тексты — только
стандартная библиотека Python.

**Storage**: SQLite (`customer_scores.detail`); новых таблиц и миграций нет — поля
`summaryDetails`/`emailDraft` вычисляются при чтении, если их нет в старой записи.

**Testing**: `pytest` (`backend/tests/test_messages.py`, контрактные тесты детали),
`tsc --noEmit`, `vite build`, проверка в Chromium.

**Target Platform**: один Docker-образ, Linux.

**Project Type**: web-service + SPA.

**Performance Goals**: сборка текстов — доли миллисекунды на клиента, без дополнительных
запросов к БД.

**Constraints**: без LLM и SMTP; текст обязан совпадать с числовым расчётом; ответы
остаются валидными для старых сохранённых записей.

**Scale/Scope**: 2 новых файла (`backend/app/messages.py`, `frontend/src/components/EmailDraft.tsx`),
правки в `scoring.py`, `schemas.py`, `Customer.tsx`, `types.ts`, `styles.css`.

## Constitution Check

*GATE: проверено до реализации и повторно после.*

| Принцип | Как соблюдён |
|---|---|
| I. Развитие существующего прототипа | Тот же стек; новый модуль и компонент вместо переписывания |
| II. Требования и допущения различаются | Помощник `messages.py` — продуктовое решение команды, не требование кейса; отмечено в spec и research |
| III. Ограниченный объём | Только тексты и письмо; формулы, метрики и снимок не менялись |
| IV. Совместимость API | Прежние поля и пути сохранены; добавлены `summaryDetails`, `emailDraft` |
| V. Согласованность при ошибках | Тексты не пишутся в БД; старый формат читается, ошибок сериализации нет |
| VI. Объяснение соответствует оценке | Заголовок и факты строятся из того же `detail`, что и score; технические правила остались доступны |
| VII. Неизвестное ≠ ноль | `expiryDays = 0.0` трактуется как валидный ноль, а не «нет данных»; `unknown` остаётся без оценки |
| VIII. Честная интерпретация | В карточке остаётся пометка «экспертная оценка, не вероятность»; письмо не обещает гарантий |
| IX. Регрессионные проверки | 20 новых тестов + прежние 384; найденный дефект `0.0` закреплён тестом |
| X. Порядок работы | Спека, план и задачи оформлены Spec Kit; коммит в `main` — по просьбе команды |

## Project Structure

### Documentation (this feature)

```text
specs/004-risk-explanation-email/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── tasks.md
├── quickstart.md
├── checklists/requirements.md
└── contracts/api.md
```

### Source Code (изменения)

```text
backend/app/
├── messages.py          # новый: money_text, day_month, expiry_phrase, build_customer_messages
├── scoring.py           # склейка заменена вызовом сборщика, сохранён availableCents
└── schemas.py           # EmailDraftOut, summaryDetails, emailDraft, fallback для старых записей

backend/tests/
├── test_messages.py     # новый: 20 проверок
├── test_explanations.py # контракт детали дополнен двумя полями
└── test_marketer_panel.py

frontend/src/
├── components/EmailDraft.tsx  # новый диалог
├── pages/Customer.tsx         # заголовок, <details>, кнопка, «Детали расчёта»
├── types.ts                   # EmailDraft, summaryDetails
└── styles.css                 # стили details/hero-actions/диалога
```

## Phase 0. Research

Решения и альтернативы — в [research.md](research.md). Итог: тексты на бэкенде,
детерминированный приоритет ситуаций, никакого SMTP/LLM, вычисление при чтении для
совместимости со старыми записями.

## Phase 1. Design

- Модель ответа и приоритет ситуаций — [data-model.md](data-model.md).
- Контракт детали клиента — [contracts/api.md](contracts/api.md).
- Проверка после реализации — [quickstart.md](quickstart.md).

## Phase 2. Implementation

Порядок: `messages.py` → `scoring.py` → `schemas.py` → тесты бэкенда → `types.ts` →
`EmailDraft.tsx` → `Customer.tsx` → `styles.css` → `openapi.json` → документация.
Задачи с файлами и покрытием — в [tasks.md](tasks.md).

## Post-Design Constitution Re-check

После реализации: формулы и метрики не изменены (проверено прежними тестами), новые поля
аддитивны, старые записи читаются (тест `test_detail_contract_and_old_cache`), новых
runtime-зависимостей и таблиц нет. Гейт пройден.

## Risks / Trade-offs

- **Шаблоны вместо свободного текста** — предсказуемо и проверяемо, но требует ручной
  правки маркетологом; поэтому текст в диалоге редактируемый.
- **Приоритет ситуаций упрощает случай «несколько проблем сразу»** — используется главная
  причина, остальные попадают в «Подробное пояснение».
- **Тексты на русском** — английская локализация вне объёма.
- **`mailto:` ограничен длиной URL** в некоторых клиентах; копирование остаётся основным
  путём, `mailto:` — дополнительным.
