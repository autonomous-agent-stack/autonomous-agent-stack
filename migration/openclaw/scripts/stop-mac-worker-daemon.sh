#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${ROOT_DIR}/logs/mac-worker.pid"
source "${ROOT_DIR}/scripts/env-common.sh"
AUTORESEARCH_WORKER_TMUX_SESSION="${AUTORESEARCH_WORKER_TMUX_SESSION:-aas-worker}"

_kill_tmux_session() {
  if command -v tmux >/dev/null 2>&1 && tmux has-session -t "${AUTORESEARCH_WORKER_TMUX_SESSION}" >/dev/null 2>&1; then
    tmux kill-session -t "${AUTORESEARCH_WORKER_TMUX_SESSION}" >/dev/null 2>&1 || true
    echo "Mac worker tmux 会话已停止 / Mac worker tmux session stopped (${AUTORESEARCH_WORKER_TMUX_SESSION})"
  fi
}

if [[ ! -f "${PID_FILE}" ]]; then
  echo "mac worker not running (no pid file)"
  _kill_tmux_session
  exit 0
fi

PID="$(cat "${PID_FILE}")"
if kill -0 "${PID}" >/dev/null 2>&1; then
  kill "${PID}" >/dev/null 2>&1 || true
  sleep 2
  if kill -0 "${PID}" >/dev/null 2>&1; then
    echo "mac worker still running after graceful stop (pid=${PID})"
    exit 1
  fi
  echo "mac worker stopped (pid=${PID})"
else
  echo "stale mac worker pid file removed (pid=${PID})"
fi

rm -f "${PID_FILE}"
_kill_tmux_session
