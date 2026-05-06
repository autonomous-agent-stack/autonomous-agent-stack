#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "${ROOT_DIR}/../.." && pwd)"
PID_FILE="${ROOT_DIR}/logs/mac-worker.pid"
LOG_FILE="${ROOT_DIR}/logs/mac-worker.log"
source "${ROOT_DIR}/scripts/env-common.sh"

mkdir -p "${ROOT_DIR}/logs"
AUTORESEARCH_DAEMON_BACKEND="${AUTORESEARCH_DAEMON_BACKEND:-auto}"
AUTORESEARCH_WORKER_TMUX_SESSION="${AUTORESEARCH_WORKER_TMUX_SESSION:-aas-worker}"
WORKER_DRY_RUN_EFFECTIVE="${WORKER_DRY_RUN:-1}"

if [[ -f "${PID_FILE}" ]]; then
  PID="$(cat "${PID_FILE}")"
  if kill -0 "${PID}" >/dev/null 2>&1; then
    echo "mac worker already running (pid=${PID})"
    exit 0
  fi
  rm -f "${PID_FILE}"
fi

if [[ ! -x "${PROJECT_ROOT}/scripts/start-mac-worker.sh" ]]; then
  echo "missing worker launcher: ${PROJECT_ROOT}/scripts/start-mac-worker.sh"
  exit 1
fi

cd "${PROJECT_ROOT}"
PID=""
if [[ "${AUTORESEARCH_DAEMON_BACKEND}" != "process" ]] && command -v tmux >/dev/null 2>&1; then
  if tmux has-session -t "${AUTORESEARCH_WORKER_TMUX_SESSION}" >/dev/null 2>&1; then
    PID="$(tmux_session_pid "${AUTORESEARCH_WORKER_TMUX_SESSION}")"
    if [[ -n "${PID}" ]]; then
      echo "${PID}" > "${PID_FILE}"
    fi
    echo "Mac worker 已在运行 / Mac worker already running (tmux session=${AUTORESEARCH_WORKER_TMUX_SESSION})"
    exit 0
  fi
  PROJECT_ROOT_Q="$(shell_quote "${PROJECT_ROOT}")"
  LOG_FILE_Q="$(shell_quote "${LOG_FILE}")"
  WORKER_DRY_RUN_Q="$(shell_quote "${WORKER_DRY_RUN_EFFECTIVE}")"
  tmux new-session -d -s "${AUTORESEARCH_WORKER_TMUX_SESSION}" \
    "cd ${PROJECT_ROOT_Q}; export WORKER_DRY_RUN=${WORKER_DRY_RUN_Q}; exec bash scripts/start-mac-worker.sh >> ${LOG_FILE_Q} 2>&1"
  PID="$(tmux_session_pid "${AUTORESEARCH_WORKER_TMUX_SESSION}")"
elif command -v setsid >/dev/null 2>&1; then
  setsid bash "${PROJECT_ROOT}/scripts/start-mac-worker.sh" </dev/null >> "${LOG_FILE}" 2>&1 &
  PID=$!
else
  nohup bash "${PROJECT_ROOT}/scripts/start-mac-worker.sh" </dev/null >> "${LOG_FILE}" 2>&1 &
  PID=$!
fi
if [[ -n "${PID}" ]]; then
  echo "${PID}" > "${PID_FILE}"
fi

sleep 1
if [[ -n "${PID}" ]] && kill -0 "${PID}" >/dev/null 2>&1; then
  echo "mac worker started (pid=${PID})"
  echo "log: ${LOG_FILE}"
  exit 0
fi
if command -v tmux >/dev/null 2>&1 && tmux has-session -t "${AUTORESEARCH_WORKER_TMUX_SESSION}" >/dev/null 2>&1; then
  echo "Mac worker 已启动 / Mac worker started (tmux session=${AUTORESEARCH_WORKER_TMUX_SESSION})"
  echo "log: ${LOG_FILE}"
  exit 0
fi

rm -f "${PID_FILE}"
echo "mac worker failed to stay running, check: ${LOG_FILE}"
exit 1
