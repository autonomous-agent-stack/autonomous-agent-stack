#!/usr/bin/env bash
# stop-mac-worker.sh — Stop the Mac worker daemon
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${ROOT_DIR}/logs/worker.pid"
source "${ROOT_DIR}/scripts/env-common.sh"

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
    echo "worker stopped (pid=${PID})"
  else
    echo "worker not running (stale pid file pid=${PID})"
  fi
  rm -f "${PID_FILE}"
else
  echo "worker not running (no pid file)"
fi
