#!/usr/bin/env bash
# Обновление демо-стенда: rsync проекта + пересборка контейнера.
#
#   ./scripts/deploy_remote.sh                    # на стенд по умолчанию
#   ./scripts/deploy_remote.sh root@1.2.3.4       # другой сервер
#   SSH_KEY=~/.ssh/other ./scripts/deploy_remote.sh
#   SSO=1 ./scripts/deploy_remote.sh               # вместе с Keycloak
#
# Пароли и .env живут только на сервере и в git не попадают.
set -euo pipefail

HOST="${1:-root@193.233.246.179}"
TARGET="${TARGET:-/opt/risk-desk}"
KEY="${SSH_KEY:-$HOME/.ssh/risk_desk_deploy}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Деплой на $HOST:$TARGET"
rsync -az --delete \
  --exclude '.git' --exclude '.venv' --exclude 'node_modules' --exclude 'frontend/dist' \
  --exclude 'data/app.db*' --exclude '__pycache__' --exclude '.pytest_cache' \
  --exclude '.dsh-office.*' --exclude '.env' --exclude 'test-results' \
  -e "ssh -i $KEY -o StrictHostKeyChecking=no" \
  "$ROOT/" "$HOST:$TARGET/"

FILES=(-f compose.yaml)
if [ "${SSO:-0}" = "1" ]; then
  FILES+=(-f compose.sso.yaml)
fi
COMPOSE_ARGS="${FILES[*]}"

ssh -i "$KEY" -o StrictHostKeyChecking=no "$HOST" "cd $TARGET && docker compose $COMPOSE_ARGS up -d --build && docker compose $COMPOSE_ARGS ps --format '{{.Service}} {{.Status}}'"
echo "Готово. Проверка: curl -s http://${HOST#*@}:8000/healthz"
