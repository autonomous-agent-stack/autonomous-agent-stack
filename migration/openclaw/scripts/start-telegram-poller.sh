#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "${ROOT_DIR}/../.." && pwd)"
PID_FILE="${ROOT_DIR}/logs/telegram-poller.pid"
LOG_FILE="${ROOT_DIR}/logs/telegram-poller.log"
SCRIPT="${ROOT_DIR}/scripts/telegram_poller_bridge.py"
source "${ROOT_DIR}/scripts/env-common.sh"

mkdir -p "${ROOT_DIR}/logs"

if [[ -f "${PID_FILE}" ]]; then
  PID="$(cat "${PID_FILE}")"
  if kill -0 "${PID}" >/dev/null 2>&1; then
    echo "telegram poller already running (pid=${PID})"
    exit 0
  fi
  rm -f "${PID_FILE}"
fi

if [[ ! -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
  echo "missing venv python: ${PROJECT_ROOT}/.venv/bin/python"
  exit 1
fi

ENV_FILES=()
load_shared_env_files "${PROJECT_ROOT}" "${ROOT_DIR}" ENV_FILES
warn_env_conflicts ENV_FILES AUTORESEARCH_API_HOST AUTORESEARCH_API_PORT AUTORESEARCH_TELEGRAM_BOT_TOKEN TELEGRAM_BOT_TOKEN

if [[ -n "${AUTORESEARCH_TELEGRAM_BOT_TOKEN:-}" && -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  export TELEGRAM_BOT_TOKEN="${AUTORESEARCH_TELEGRAM_BOT_TOKEN}"
fi
if [[ -n "${TELEGRAM_BOT_TOKEN:-}" && -z "${AUTORESEARCH_TELEGRAM_BOT_TOKEN:-}" ]]; then
  export AUTORESEARCH_TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN}"
fi

API_HOST="${AUTORESEARCH_API_HOST:-127.0.0.1}"
API_PORT="${AUTORESEARCH_API_PORT:-8001}"
AUTORESEARCH_API_HOST="${API_HOST}"
AUTORESEARCH_API_PORT="${API_PORT}"
print_effective_env_values AUTORESEARCH_API_HOST AUTORESEARCH_API_PORT AUTORESEARCH_TELEGRAM_BOT_TOKEN TELEGRAM_BOT_TOKEN
if ! curl -fsS "http://${API_HOST}:${API_PORT}/healthz" >/dev/null 2>&1; then
  echo "api not healthy on http://${API_HOST}:${API_PORT}/healthz"
  echo "run: make start  (or start API daemon with the same port)"
  exit 1
fi

export TELEGRAM_BRIDGE_LOCAL_WEBHOOK_URL="${TELEGRAM_BRIDGE_LOCAL_WEBHOOK_URL:-http://${API_HOST}:${API_PORT}/api/v1/gateway/telegram/webhook}"

cd "${PROJECT_ROOT}"
if command -v setsid >/dev/null 2>&1; then
  setsid "${PROJECT_ROOT}/.venv/bin/python" "${SCRIPT}" </dev/null >> "${LOG_FILE}" 2>&1 &
else
  nohup "${PROJECT_ROOT}/.venv/bin/python" "${SCRIPT}" </dev/null >> "${LOG_FILE}" 2>&1 &
fi
PID=$!
echo "${PID}" > "${PID_FILE}"

sleep 2
if kill -0 "${PID}" >/dev/null 2>&1; then
  echo "telegram poller started (pid=${PID})"
  exit 0
fi

echo "telegram poller failed to start, check: ${LOG_FILE}"
exit 1
