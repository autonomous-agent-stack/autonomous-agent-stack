#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "${ROOT_DIR}/../.." && pwd)"
PID_FILE="${ROOT_DIR}/logs/api.pid"
LOG_FILE="${ROOT_DIR}/logs/api.log"
source "${ROOT_DIR}/scripts/env-common.sh"

mkdir -p "${ROOT_DIR}/logs" "${PROJECT_ROOT}/artifacts/api"

ENV_FILES=()
load_shared_env_files "${PROJECT_ROOT}" "${ROOT_DIR}" ENV_FILES
warn_env_conflicts ENV_FILES AUTORESEARCH_API_HOST AUTORESEARCH_API_PORT

AUTORESEARCH_API_HOST="${AUTORESEARCH_API_HOST:-127.0.0.1}"
AUTORESEARCH_API_PORT="${AUTORESEARCH_API_PORT:-8001}"
AUTORESEARCH_DAEMON_BACKEND="${AUTORESEARCH_DAEMON_BACKEND:-auto}"
AUTORESEARCH_API_TMUX_SESSION="${AUTORESEARCH_API_TMUX_SESSION:-aas-api}"
print_effective_env_values AUTORESEARCH_API_HOST AUTORESEARCH_API_PORT

HEALTH_URL="http://${AUTORESEARCH_API_HOST}:${AUTORESEARCH_API_PORT}/healthz"

# Port already serves health - do not spawn a second uvicorn (would leave a bogus pid file).
if curl -fsS "${HEALTH_URL}" >/dev/null 2>&1; then
  LISTENER_PID="$(listener_pid_for_port "${AUTORESEARCH_API_PORT}")"
  if [[ -n "${LISTENER_PID}" ]]; then
    PROJECT_PHYSICAL_ROOT="$(resolve_physical_dir "${PROJECT_ROOT}" || true)"
    LISTENER_CWD="$(process_cwd_for_pid "${LISTENER_PID}")"
    LISTENER_PHYSICAL_CWD=""
    if [[ -n "${LISTENER_CWD}" ]]; then
      LISTENER_PHYSICAL_CWD="$(resolve_physical_dir "${LISTENER_CWD}" || true)"
    fi
    if [[ -n "${PROJECT_PHYSICAL_ROOT}" && -n "${LISTENER_PHYSICAL_CWD}" && "${PROJECT_PHYSICAL_ROOT}" != "${LISTENER_PHYSICAL_CWD}" ]]; then
      echo "API 监听进程来自其他 checkout / API listener belongs to another checkout"
      echo "expected: ${PROJECT_PHYSICAL_ROOT}"
      echo "actual:   ${LISTENER_PHYSICAL_CWD}"
      echo "请先执行 restart/stop 清理旧进程 / Run restart/stop first"
      exit 1
    fi
    echo "${LISTENER_PID}" > "${PID_FILE}"
    echo "api already healthy (listener pid=${LISTENER_PID}, synced ${PID_FILE})"
    echo "health: ${HEALTH_URL}"
    exit 0
  fi
  echo "api health check passed but could not read listener pid (install lsof to sync ${PID_FILE})"
  echo "health: ${HEALTH_URL}"
  exit 0
fi

if [[ -f "${PID_FILE}" ]]; then
  PID="$(cat "${PID_FILE}")"
  if kill -0 "${PID}" >/dev/null 2>&1; then
    echo "api already running (pid=${PID})"
    exit 0
  fi
  rm -f "${PID_FILE}"
fi

if [[ ! -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
  echo "missing venv python: ${PROJECT_ROOT}/.venv/bin/python"
  exit 1
fi

cd "${PROJECT_ROOT}"
API_CMD=(
  env
  PYTHONPATH=src
  "${PROJECT_ROOT}/.venv/bin/python"
  -m
  uvicorn
  autoresearch.api.main:app
  --host
  "${AUTORESEARCH_API_HOST}"
  --port
  "${AUTORESEARCH_API_PORT}"
)
PID=""
if [[ "${AUTORESEARCH_DAEMON_BACKEND}" != "process" ]] && command -v tmux >/dev/null 2>&1; then
  if tmux has-session -t "${AUTORESEARCH_API_TMUX_SESSION}" >/dev/null 2>&1; then
    echo "正在替换旧 API tmux 会话 / Replacing stale API tmux session: ${AUTORESEARCH_API_TMUX_SESSION}"
    tmux kill-session -t "${AUTORESEARCH_API_TMUX_SESSION}" >/dev/null 2>&1 || true
  fi
  PROJECT_ROOT_Q="$(shell_quote "${PROJECT_ROOT}")"
  PYTHON_Q="$(shell_quote "${PROJECT_ROOT}/.venv/bin/python")"
  LOG_FILE_Q="$(shell_quote "${LOG_FILE}")"
  API_HOST_Q="$(shell_quote "${AUTORESEARCH_API_HOST}")"
  API_PORT_Q="$(shell_quote "${AUTORESEARCH_API_PORT}")"
  tmux new-session -d -s "${AUTORESEARCH_API_TMUX_SESSION}" \
    "cd ${PROJECT_ROOT_Q}; exec env PYTHONPATH=src ${PYTHON_Q} -m uvicorn autoresearch.api.main:app --host ${API_HOST_Q} --port ${API_PORT_Q} >> ${LOG_FILE_Q} 2>&1"
elif command -v setsid >/dev/null 2>&1; then
  setsid "${API_CMD[@]}" </dev/null >> "${LOG_FILE}" 2>&1 &
  PID=$!
else
  nohup "${API_CMD[@]}" </dev/null >> "${LOG_FILE}" 2>&1 &
  PID=$!
fi
if [[ -n "${PID}" ]]; then
  echo "${PID}" > "${PID_FILE}"
fi

for _ in {1..30}; do
  if curl -fsS "${HEALTH_URL}" >/dev/null 2>&1; then
    LISTENER_PID="$(listener_pid_for_port "${AUTORESEARCH_API_PORT}")"
    if [[ -n "${LISTENER_PID}" ]]; then
      PID="${LISTENER_PID}"
      echo "${PID}" > "${PID_FILE}"
    elif [[ -z "${PID}" ]]; then
      PID="$(tmux_session_pid "${AUTORESEARCH_API_TMUX_SESSION}")"
      if [[ -n "${PID}" ]]; then
        echo "${PID}" > "${PID_FILE}"
      fi
    fi
    if [[ -n "${PID}" ]] && ! kill -0 "${PID}" >/dev/null 2>&1; then
      rm -f "${PID_FILE}"
      echo "api error: ${HEALTH_URL} responds but recorded pid ${PID} is not running (stale listener on port ${AUTORESEARCH_API_PORT})."
      echo "Stop the old process or change AUTORESEARCH_API_PORT. Log: ${LOG_FILE}"
      exit 1
    fi
    echo "api started (pid=${PID})"
    echo "health: ${HEALTH_URL}"
    exit 0
  fi
  sleep 1
done

echo "api failed to become healthy, check: ${LOG_FILE}"
exit 1
