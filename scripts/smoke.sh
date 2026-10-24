#!/usr/bin/env bash
# Проверка, что запущенное приложение действительно работает.
# Использование: ./scripts/smoke.sh [http://localhost:8000]
set -euo pipefail

BASE="${1:-${BASE_URL:-http://localhost:8000}}"
EMAIL="${ADMIN_EMAIL:-admin@example.test}"
PASSWORD="${ADMIN_PASSWORD:-admin123}"
COOKIES="$(mktemp)"
trap 'rm -f "$COOKIES"' EXIT

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
expect() { # code, url, description
  local code
  code="$(curl -s -o /dev/null -w '%{http_code}' "$2")"
  [ "$code" = "$1" ] || fail "$3: ожидали $1, получили $code ($2)"
  printf 'ok   %s (%s)\n' "$3" "$code"
}

printf 'Проверяем %s\n' "$BASE"
expect 200 "$BASE/healthz" "healthz"
expect 200 "$BASE/metrics" "метрики Prometheus"
expect 401 "$BASE/api/v1/customers" "закрытый API без сессии"
expect 200 "$BASE/" "панель отдаётся"

login_code="$(curl -s -o /dev/null -w '%{http_code}' -c "$COOKIES" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  "$BASE/api/v1/auth/login")"
[ "$login_code" = "200" ] || fail "логин: ожидали 200, получили $login_code"
printf 'ok   логин (%s)\n' "$login_code"

me_code="$(curl -s -o /dev/null -w '%{http_code}' -b "$COOKIES" "$BASE/api/v1/auth/me")"
[ "$me_code" = "200" ] || fail "/auth/me: ожидали 200, получили $me_code"
printf 'ok   сессия (/auth/me)\n'

oidc_json="$(curl -s "$BASE/api/v1/auth/oidc/config")"
case "$oidc_json" in *'"enabled":true'*) oidc_state=true ;; *) oidc_state=false ;; esac
printf 'ok   oidc/config (enabled=%s)\n' "$oidc_state"

printf '\nВсё работает: %s\n' "$BASE"
