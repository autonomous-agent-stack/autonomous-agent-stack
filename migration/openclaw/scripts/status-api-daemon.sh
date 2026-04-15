#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "${ROOT_DIR}/../.." && pwd)"
PID_FILE="${ROOT_DIR}/logs/api.pid"
source "${ROOT_DIR}/scripts/env-common.sh"

HOST="127.0.0.1"
PORT="8001"
ENV_FILES=()
load_shared_env_files "${PROJECT_ROOT}" "${ROOT_DIR}" ENV_FILES
warn_env_conflicts ENV_FILES AUTORESEARCH_API_HOST AUTORESEARCH_API_PORT
HOST="${AUTORESEARCH_API_HOST:-$HOST}"
PORT="${AUTORESEARCH_API_PORT:-$PORT}"
AUTORESEARCH_API_HOST="${HOST}"
AUTORESEARCH_API_PORT="${PORT}"
print_effective_env_values AUTORESEARCH_API_HOST AUTORESEARCH_API_PORT

if [[ -f "${PID_FILE}" ]]; then
  PID="$(cat "${PID_FILE}")"
  if kill -0 "${PID}" >/dev/null 2>&1; then
    echo "api running (pid=${PID})"
  else
    echo "api not running (stale pid=${PID})"
  fi
else
  echo "api not running"
fi

if curl -fsS "http://${HOST}:${PORT}/healthz" >/dev/null 2>&1; then
  echo "health ok: http://${HOST}:${PORT}/healthz"
else
  echo "health fail: http://${HOST}:${PORT}/healthz"
fi
