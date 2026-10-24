# Implementation Plan: вход через OIDC (SSO)

**Branch**: `main` | **Date**: 2026-10-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-oidc-sso/spec.md`

## Summary

Добавить OIDC Authorization Code + PKCE как второй способ входа, не меняя сессии,
парольный вход и остальные контракты. Провайдер настраивается переменными окружения;
делается discovery, обмен кода, проверка ID token по JWKS (RS256). Пользователь
создаётся по подтверждённому email. Для демо — Keycloak в compose профилем `sso`.
Реализация без новых зависимостей: `urllib` и проверка RSA на целых числах.

## Technical Context

**Language/Version**: Python 3.12, React 18 + TypeScript 5 + Vite 5.

**Primary Dependencies**: без новых; `fastapi`, `pydantic` и стандартная библиотека.

**Storage**: SQLite: новая таблица `oidc_flows`, колонка `users.oidc_subject`
(аддитивная миграция `ALTER TABLE`, без переписывания таблиц).

**Testing**: `pytest` с фейковым провайдером (stdlib HTTP-сервер) и настоящей
RS256-подписью; браузерная проверка полного редиректа.

**Target Platform**: Linux-контейнер; локально macOS.

**Project Type**: web-service + SPA.

**Performance Goals**: discovery и JWKS кэшируются на 5 минут; вход — два сетевых
вызова к провайдеру, без влияния на выдачу клиентов.

**Constraints**: секреты только в `.env`; ошибки провайдера не должны давать 500;
`OIDC_INTERNAL_BASE` для server-to-server адресов внутри Docker.

**Scale/Scope**: 1 новый модуль (`backend/app/oidc.py`), 3 маршрута, правки `security.py`,
`db.py`, `config.py`, `Login.tsx`, `api.ts`, compose и демо-realm.

## Constitution Check

| Принцип | Как соблюдён |
|---|---|
| I. Развитие прототипа | Тот же стек, сессии и UI; OIDC — дополнительный маршрут |
| II. Требования и допущения | Провайдер и Keycloak — решение команды, а не требование кейса; отмечено в spec |
| III. Ограниченный объём | Нет Single Logout, ролей и маппинга групп; только вход |
| IV. Совместимость API | Новые пути и поля аддитивны; парольный вход и `/auth/me` не меняются |
| V. Согласованность при ошибках | Любая ошибка OIDC → редирект с кодом, без сессии и без 500 |
| VI. Объяснение соответствует | Не касается модели риска |
| VII. Неизвестное ≠ ноль | Пользователь без `oidc_subject` не считается SSO-пользователем |
| VIII. Честная интерпретация | Документация прямо говорит: это вход, а не SSO-выход и не роли |
| IX. Регрессионные проверки | 17 новых тестов, включая проверку подписи и негативные сценарии |
| X. Порядок работы | Спека/план/задачи Spec Kit, коммит в `main` по просьбе команды |

## Project Structure

```text
backend/app/
├── oidc.py           # новый: discovery, PKCE, обмен кода, JWKS, проверка RS256
├── api.py            # маршруты config/start/callback, редиректы и cookie
├── security.py       # ensure_oidc_user
├── db.py             # oidc_flows + users.oidc_subject
└── config.py         # OIDC_* переменные

backend/tests/test_oidc.py   # фейковый провайдер + RSA в чистом Python

frontend/src/
├── pages/Login.tsx   # кнопка «Войти через {provider}», сообщения об ошибках
└── api.ts            # oidcConfig()

deploy/keycloak/risk-desk-realm.json   # демо-realm
compose.yaml                            # профиль sso
docs/screenshots/11-login-sso.png       # экран входа с SSO
```

## Phase 0. Research

См. [research.md](research.md): почему без новых зависимостей, как разделены публичный
и внутренний адреса, почему state/nonce в БД, а не в cookie, и как проверяется подпись.

## Phase 1. Design

- Модель и коды ошибок — [data-model.md](data-model.md).
- Контракт маршрутов — [contracts/api.md](contracts/api.md).
- Приёмка — [quickstart.md](quickstart.md).

## Phase 2. Implementation

`config.py` → `db.py` → `security.py` → `oidc.py` → `api.py` → тесты → `api.ts` →
`Login.tsx` → `styles.css` → Keycloak/compose → `openapi.json` → документация.
Задачи — в [tasks.md](tasks.md).

## Post-Design Constitution Re-check

Гейт пройден: новых зависимостей и таблиц нет (только аддитивная колонка и таблица flows),
формулы и выдача клиентов не изменены, ошибки не дают 500, парольный вход проверен тестом.

## Risks / Trade-offs

- **Ручная проверка RS256** вместо библиотеки: меньше зависимостей, но код нужно
  сопровождать. Покрыт тестами с настоящей подписью и негативными случаями; поддерживается
  только RS256 (ES256/HS256 отклоняются) — для Keycloak/Okta/Google по умолчанию достаточно.
- **Email как ключ идентификации**: при совпадении email аккаунт связывается. Допустимо
  при доверенном провайдере; в spec зафиксировано как допущение.
- **Docker-сеть**: публичный issuer и внутренний адрес различаются; лечится
  `OIDC_INTERNAL_BASE`, без этого демо в контейнере не заработало бы.
- **Нет Single Logout и ролей** — осознанно вне объёма; перечислено в spec.
