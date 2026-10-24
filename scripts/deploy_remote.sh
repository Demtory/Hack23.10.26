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

# Админ-консоль Keycloak: master-realm по умолчанию требует HTTPS, поэтому после
# каждого старта контейнера снимаем это требование (только для демо-стенда).
if [ "${SSO:-0}" = "1" ]; then
  echo "Разрешаю админ-консоль Keycloak по HTTP…"
  ssh -i "$KEY" -o StrictHostKeyChecking=no "$HOST" '
    KCPW=$(grep ^KC_ADMIN_PASSWORD /opt/risk-desk/.env | cut -d= -f2)
    for _ in $(seq 1 30); do
      docker exec risk-desk-keycloak-1 /opt/keycloak/bin/kcadm.sh config credentials         --server http://localhost:8080 --realm master --user admin --password "$KCPW" >/dev/null 2>&1 && break
      sleep 2
    done
    docker exec risk-desk-keycloak-1 /opt/keycloak/bin/kcadm.sh update realms/master -s sslRequired=NONE >/dev/null 2>&1       && echo "консоль по HTTP разрешена"' || echo "консоль Keycloak: не удалось снять HTTPS-требование"
fi
echo "Готово. Проверка: curl -s http://${HOST#*@}:8000/healthz"
