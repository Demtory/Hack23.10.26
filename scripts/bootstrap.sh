#!/usr/bin/env bash
# Одна команда для любой машины: собрать, запустить и проверить приложение.
#
#   ./scripts/bootstrap.sh           # Docker (рекомендуется)
#   ./scripts/bootstrap.sh --local   # без Docker: venv + uvicorn
#
# Переменные: APP_PORT (по умолчанию 8000), PYTHON (для --local).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODE="docker"
case "${1:-}" in
  --local) MODE="local" ;;
  --docker|"") MODE="docker" ;;
  -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
  *) echo "Неизвестный аргумент: $1 (см. --help)" >&2; exit 2 ;;
esac

PORT="${APP_PORT:-8000}"

if [ "$MODE" = "docker" ]; then
  command -v docker >/dev/null 2>&1 || {
    echo "Docker не установлен. Поставьте Docker Desktop или запустите с --local." >&2
    exit 1
  }
  docker info >/dev/null 2>&1 || {
    echo "Docker-демон не запущен. Откройте Docker Desktop и повторите." >&2
    exit 1
  }

  echo "Собираю и запускаю контейнер…"
  APP_PORT="$PORT" docker compose up --build -d

  echo -n "Жду готовности http://localhost:$PORT"
  for _ in $(seq 1 60); do
    if curl -fsS "http://localhost:$PORT/healthz" >/dev/null 2>&1; then
      echo " — готово"
      break
    fi
    printf '.'
    sleep 2
  done
  curl -fsS "http://localhost:$PORT/healthz" >/dev/null || {
    echo
    echo "Приложение не ответило за 120 секунд. Логи:" >&2
    docker compose logs --tail 50 app >&2
    exit 1
  }

  ./scripts/smoke.sh "http://localhost:$PORT"
  echo
  echo "Открыть: http://localhost:$PORT  (admin@example.test / admin123)"
  echo "Логи:    docker compose logs -f app"
  echo "Стоп:    docker compose down"
  exit 0
fi

PYTHON="${PYTHON:-python3.12}"
command -v "$PYTHON" >/dev/null 2>&1 || PYTHON="python3"
"$PYTHON" --version >/dev/null 2>&1 || {
  echo "Не найден Python 3.12+. Установите его или используйте Docker." >&2
  exit 1
}

if [ ! -x .venv/bin/python ]; then
  echo "Создаю .venv…"
  "$PYTHON" -m venv .venv
fi
echo "Ставлю зависимости…"
.venv/bin/python -m pip install --quiet -r backend/requirements-dev.txt

if [ ! -d frontend/node_modules ]; then
  echo "Ставлю frontend-зависимости…"
  npm --prefix frontend ci
fi
echo "Собираю фронтенд…"
npm --prefix frontend run build

echo
echo "Запускаю uvicorn на http://127.0.0.1:$PORT (Ctrl+C — остановить)"
echo "Проверка в другом терминале: ./scripts/smoke.sh http://127.0.0.1:$PORT"
echo
exec env PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "$PORT" --reload
