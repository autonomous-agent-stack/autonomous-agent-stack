#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${ROOT_DIR}/logs/mac-worker.pid"
LOG_FILE="${ROOT_DIR}/logs/mac-worker.log"
source "${ROOT_DIR}/scripts/env-common.sh"
AUTORESEARCH_WORKER_TMUX_SESSION="${AUTORESEARCH_WORKER_TMUX_SESSION:-aas-worker}"

if [[ -f "${PID_FILE}" ]]; then
  PID="$(cat "${PID_FILE}")"
  if kill -0 "${PID}" >/dev/null 2>&1; then
    echo "mac worker running (pid=${PID})"
  else
    echo "mac worker not running (stale pid=${PID})"
  fi
else
  echo "mac worker not running"
fi
if command -v tmux >/dev/null 2>&1 && tmux has-session -t "${AUTORESEARCH_WORKER_TMUX_SESSION}" >/dev/null 2>&1; then
  echo "Mac worker tmux 会话运行中 / Mac worker tmux session running: ${AUTORESEARCH_WORKER_TMUX_SESSION}"
fi

if [[ -f "${LOG_FILE}" ]]; then
  tail -n 20 "${LOG_FILE}"
else
  echo "no log: ${LOG_FILE}"
fi
