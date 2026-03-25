#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env.local"
PID_FILE="${ROOT_DIR}/logs/api.pid"

HOST="127.0.0.1"
PORT="8000"
if [[ -f "${ENV_FILE}" ]]; then
  set -a
  source "${ENV_FILE}"
  set +a
  HOST="${AUTORESEARCH_API_HOST:-$HOST}"
  PORT="${AUTORESEARCH_API_PORT:-$PORT}"
fi

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
