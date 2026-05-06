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
AUTORESEARCH_API_TMUX_SESSION="${AUTORESEARCH_API_TMUX_SESSION:-aas-api}"
print_effective_env_values AUTORESEARCH_API_HOST AUTORESEARCH_API_PORT

LISTEN_PID="$(listener_pid_for_port "${PORT}")"
PROJECT_PHYSICAL_ROOT="$(resolve_physical_dir "${PROJECT_ROOT}" || true)"

if [[ -f "${PID_FILE}" ]]; then
  PID="$(cat "${PID_FILE}")"
  if kill -0 "${PID}" >/dev/null 2>&1; then
    echo "api running (pid=${PID})"
  else
    echo "api not running (stale pid file pid=${PID})"
  fi
else
  echo "api not running (no pid file)"
fi
if command -v tmux >/dev/null 2>&1 && tmux has-session -t "${AUTORESEARCH_API_TMUX_SESSION}" >/dev/null 2>&1; then
  echo "API tmux 会话运行中 / API tmux session running: ${AUTORESEARCH_API_TMUX_SESSION}"
fi

if curl -fsS "http://${HOST}:${PORT}/healthz" >/dev/null 2>&1; then
  echo "health ok: http://${HOST}:${PORT}/healthz"
  if [[ -n "${LISTEN_PID}" ]]; then
    LISTENER_CWD="$(process_cwd_for_pid "${LISTEN_PID}")"
    LISTENER_PHYSICAL_CWD=""
    if [[ -n "${LISTENER_CWD}" ]]; then
      LISTENER_PHYSICAL_CWD="$(resolve_physical_dir "${LISTENER_CWD}" || true)"
    fi
    echo "tcp listener on ${PORT}: pid=${LISTEN_PID} cwd=${LISTENER_CWD:-unknown}"
    if [[ -n "${PROJECT_PHYSICAL_ROOT}" && -n "${LISTENER_PHYSICAL_CWD}" && "${PROJECT_PHYSICAL_ROOT}" != "${LISTENER_PHYSICAL_CWD}" ]]; then
      echo "警告：监听进程来自其他 checkout / Warning: listener checkout mismatch"
      echo "expected: ${PROJECT_PHYSICAL_ROOT}"
      echo "actual:   ${LISTENER_PHYSICAL_CWD}"
    fi
  fi
else
  echo "health fail: http://${HOST}:${PORT}/healthz"
fi
