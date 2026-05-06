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
AUTORESEARCH_API_TMUX_SESSION="${AUTORESEARCH_API_TMUX_SESSION:-aas-api}"
HEALTH_URL="http://${AUTORESEARCH_API_HOST}:${AUTORESEARCH_API_PORT}/healthz"
# Bound wait: a hung listener (TCP up, HTTP never completes) must not block `make telegram-butler-stop`.
CURL_HEALTH=(curl -fsS --connect-timeout 2 --max-time 4)

LISTENER_PID="$(listener_pid_for_port "${AUTORESEARCH_API_PORT}")"

_kill_pid() {
  local target="$1"
  kill "${target}" >/dev/null 2>&1 || true
  sleep 1
  if kill -0 "${target}" >/dev/null 2>&1; then
    kill -9 "${target}" >/dev/null 2>&1 || true
  fi
}

_kill_tmux_session() {
  if command -v tmux >/dev/null 2>&1 && tmux has-session -t "${AUTORESEARCH_API_TMUX_SESSION}" >/dev/null 2>&1; then
    tmux kill-session -t "${AUTORESEARCH_API_TMUX_SESSION}" >/dev/null 2>&1 || true
    echo "API tmux 会话已停止 / API tmux session stopped (${AUTORESEARCH_API_TMUX_SESSION})"
  fi
}

# Keep ingress single-consumer: stop poller first, then API.
if [[ -f "${ROOT_DIR}/scripts/stop-telegram-poller.sh" ]]; then
  bash "${ROOT_DIR}/scripts/stop-telegram-poller.sh" >/dev/null 2>&1 || true
fi

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
  if [[ -n "${LISTENER_PID}" ]]; then
    LISTENER_CWD="$(process_cwd_for_pid "${LISTENER_PID}")"
    if [[ -n "${LISTENER_CWD}" ]]; then
      echo "正在停止无 pid 文件的监听进程 / Stopping stray listener pid=${LISTENER_PID} cwd=${LISTENER_CWD} (no pid file)"
    else
      echo "正在停止无 pid 文件的监听进程 / Stopping stray listener pid=${LISTENER_PID} (no pid file)"
    fi
    _kill_pid "${LISTENER_PID}"
  fi
fi
_kill_tmux_session
