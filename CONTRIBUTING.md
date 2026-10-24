# Как работать над проектом вместе

Документ живёт в репозитории: после `git pull` он всегда актуален. Если у вас на
машине «старая инструкция» — вы скачали архив вместо `git pull`.

## 1. Один раз клонировать

```bash
git clone git@github.com:Demtory/Hack23.10.26.git
cd Hack23.10.26
```

Дальше **не скачивайте ZIP**. История, ветки и инструкции приходят через `git`.

Проверить, что всё готово:

```bash
./scripts/bootstrap.sh        # Docker: соберёт и запустит, дождётся healthz, прогонит smoke
./scripts/bootstrap.sh --local  # без Docker: venv, зависимости, сборка фронта, uvicorn
```

## 2. Ежедневный цикл

```bash
git pull --rebase            # забрать чужие изменения до начала работы
git switch -c feat/short-name
# ... правки ...
git add -p && git commit -m "feat: что сделано"
git push -u origin feat/short-name
```

Открыть Pull Request в `main`. Мержить можно после зелёного CI
(`.github/workflows/ci.yml`: тесты, сборка, OpenAPI, compose, docker build).
После мержа — снова `git switch main && git pull --rebase`.

Правила, которые берегут нервы:

- **Ветка = задача.** Долгоживущие ветки конфликтуют; PR лучше мержить в тот же день.
- **Не работайте в `main` напрямую.** Тогда «кто-то залил» не ломает вашу работу.
- **Не правьте руками сгенерированное:** `openapi.json`, `docs/screenshots/*`.
  `openapi.json` пересобирается командой из README, скриншоты — `capture-screens.spec.ts`.
  При конфликте в них: принять свою версию и пересобрать, а не склеивать.
- **Не коммитьте:** `.env`, `data/app.db`, `frontend/dist`, `node_modules`, `.venv`.
  Они уже в `.gitignore`.
- **Секреты только в `.env`** (локально) или в переменных окружения. В репозиторий — никогда.
- **Окончания строк** заданы в `.gitattributes`; не «исправляйте» их вручную.

## 3. Что делать после чужого пуша

```bash
git pull --rebase
docker compose up --build -d     # пересобрать и перезапустить
./scripts/smoke.sh               # 6 проверок: healthz, метрики, 401, панель, логин, сессия
```

Если менялись только фронтенд/бэкенд-тексты — хватит `docker compose restart app`.
Если менялся `backend/requirements.txt` или `frontend/package.json` — обязателен `--build`.

## 4. Если «у меня не работает, а у него работает»

1. `git status` — нет ли незакоммиченных правок и старых файлов.
2. `git log --oneline -3` — та ли ветка, тот ли коммит.
3. `docker compose down -v && docker compose up --build` — чистая БД из seed.
4. `./scripts/smoke.sh` — покажет, какой именно шаг падает.
5. Если ошибка не воспроизводится — приложите вывод `docker compose logs app`.

## 5. Фичи и спеки

Проект ведётся по Spec Kit: `specs/001…005` — спека, план, задачи, контракт, quickstart.
Порядок: согласовали задачу → `spec.md` → `plan.md` → `tasks.md` → реализация → PR.
Для новой фичи — следующая свободная папка `specs/00N-…` по тем же шаблонам
(`.specify/templates/`). Не создавайте альтернативных документов «вне процесса».

## 6. Роли и договорённости

- Один человек в день отвечает за мерж PR и за то, что `main` зелёный.
- Коммиты и PR — короткие: одна задача, одно изменение.
- Перед защитой: `main` заморожен, все работают только ветками и PR.

## 7. Для владельца репозитория

Эти шаги требуют прав **admin**. Сейчас в репозитории три участника
(`Demtory`, `ilemss`, `surgezxc`); добавлять новых и менять правила может владелец.

### Добавить участника

```bash
gh api -X PUT repos/Demtory/Hack23.10.26/collaborators/USERNAME -f permission=push
```

Или: Settings → Collaborators → Add people.

### Включить защиту `main` (PR + зелёный CI)

Файл `protection.json`:

```json
{
  "required_status_checks": { "strict": true, "contexts": ["backend", "frontend", "compose"] },
  "enforce_admins": false,
  "required_pull_request_reviews": { "required_approving_review_count": 1 },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
```

```bash
gh api -X PUT repos/Demtory/Hack23.10.26/branches/main/protection \
  -H "Accept: application/vnd.github+json" --input protection.json
```

Проверить:

```bash
gh api repos/Demtory/Hack23.10.26/branches/main/protection --jq '.required_status_checks.contexts'
```

Если GitHub ответит, что для приватного репозитория нужен платный план — включите
то же самое через **Settings → Rules → New ruleset**: target `main`, «Require a pull
request before merging», «Require status checks» (`backend`, `frontend`, `compose`).

`enforce_admins: false` оставляет владельцу аварийный прямой пуш — на хакатоне это
полезно, но не злоупотребляйте: остальные участники работают только через PR.
