#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "${ROOT_DIR}/../.." && pwd)"
PID_FILE="${ROOT_DIR}/logs/telegram-poller.pid"
LOG_FILE="${ROOT_DIR}/logs/telegram-poller.log"
ENV_FILE="${ROOT_DIR}/.env.local"
SCRIPT="${ROOT_DIR}/scripts/telegram_poller_bridge.py"

mkdir -p "${ROOT_DIR}/logs"

if [[ -f "${PID_FILE}" ]]; then
  PID="$(cat "${PID_FILE}")"
  if kill -0 "${PID}" >/dev/null 2>&1; then
    echo "telegram poller already running (pid=${PID})"
    exit 0
  fi
  rm -f "${PID_FILE}"
fi

if ! curl -fsS http://127.0.0.1:8000/healthz >/dev/null 2>&1; then
  echo "api not healthy on http://127.0.0.1:8000/healthz"
  echo "run: bash migration/openclaw/scripts/start-api-daemon.sh"
  exit 1
fi

if [[ ! -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
  echo "missing venv python: ${PROJECT_ROOT}/.venv/bin/python"
  exit 1
fi

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  source "${ENV_FILE}"
  set +a
fi

cd "${PROJECT_ROOT}"
nohup "${PROJECT_ROOT}/.venv/bin/python" "${SCRIPT}" >> "${LOG_FILE}" 2>&1 &
PID=$!
echo "${PID}" > "${PID_FILE}"

sleep 2
if kill -0 "${PID}" >/dev/null 2>&1; then
  echo "telegram poller started (pid=${PID})"
  exit 0
fi

echo "telegram poller failed to start, check: ${LOG_FILE}"
exit 1
