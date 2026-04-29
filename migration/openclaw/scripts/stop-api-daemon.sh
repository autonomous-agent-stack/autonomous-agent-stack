#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "${ROOT_DIR}/../.." && pwd)"
PID_FILE="${ROOT_DIR}/logs/api.pid"
source "${ROOT_DIR}/scripts/env-common.sh"

ENV_FILES=()
load_shared_env_files "${PROJECT_ROOT}" "${ROOT_DIR}" ENV_FILES
warn_env_conflicts ENV_FILES AUTORESEARCH_API_HOST AUTORESEARCH_API_PORT

AUTORESEARCH_API_HOST="${AUTORESEARCH_API_HOST:-127.0.0.1}"
AUTORESEARCH_API_PORT="${AUTORESEARCH_API_PORT:-8001}"
HEALTH_URL="http://${AUTORESEARCH_API_HOST}:${AUTORESEARCH_API_PORT}/healthz"
# Bound wait: a hung listener (TCP up, HTTP never completes) must not block `make telegram-butler-stop`.
CURL_HEALTH=(curl -fsS --connect-timeout 2 --max-time 4)

LISTENER_PID=""
if command -v lsof >/dev/null 2>&1; then
  LISTENER_PID="$(lsof -nP -iTCP:"${AUTORESEARCH_API_PORT}" -sTCP:LISTEN -t 2>/dev/null | head -n 1 || true)"
fi

_kill_pid() {
  local target="$1"
  kill "${target}" >/dev/null 2>&1 || true
  sleep 1
  if kill -0 "${target}" >/dev/null 2>&1; then
    kill -9 "${target}" >/dev/null 2>&1 || true
  fi
}

if [[ -f "${PID_FILE}" ]]; then
  PID="$(cat "${PID_FILE}")"
  if kill -0 "${PID}" >/dev/null 2>&1; then
    _kill_pid "${PID}"
    echo "api stopped (pid=${PID})"
  else
    echo "api not running (stale pid file pid=${PID})"
    if "${CURL_HEALTH[@]}" "${HEALTH_URL}" >/dev/null 2>&1 && [[ -n "${LISTENER_PID}" ]]; then
      echo "stopping stray listener pid=${LISTENER_PID} (pid file was stale)"
      _kill_pid "${LISTENER_PID}"
    fi
  fi
  rm -f "${PID_FILE}"
else
  echo "api not running (no pid file)"
fi
