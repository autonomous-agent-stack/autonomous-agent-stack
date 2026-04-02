#!/usr/bin/env bash
# Friendly local startup wrapper

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python"
API_RUNNER="${PROJECT_ROOT}/scripts/run_api_service.sh"
POLLER_STARTER="${PROJECT_ROOT}/scripts/start_telegram_poller.sh"

for ENV_FILE in "${PROJECT_ROOT}/.env" "${PROJECT_ROOT}/.env.local" "${PROJECT_ROOT}/.env.linux" "${PROJECT_ROOT}/ai_lab.env"; do
  if [[ -f "${ENV_FILE}" ]]; then
    set -a
    source "${ENV_FILE}"
    set +a
  fi
done

resolve_bind_host() {
  local requested_host="$1"
  if [[ "${requested_host}" != "0.0.0.0" ]]; then
    echo "${requested_host}"
    return
  fi
  if command -v hostname >/dev/null 2>&1; then
    while read -r candidate; do
      if [[ "${candidate}" == 100.* || "${candidate}" == fd7a:115c:a1e0:* ]]; then
        echo "${candidate}"
        return
      fi
    done < <(hostname -I 2>/dev/null | tr ' ' '\n')
  fi
  echo "127.0.0.1"
}

REQUESTED_HOST="${HOST:-${AUTORESEARCH_API_HOST:-127.0.0.1}}"
HOST="$(resolve_bind_host "${REQUESTED_HOST}")"
PORT="${PORT:-${AUTORESEARCH_API_PORT:-8001}}"
PROBE_HOST="${HOST}"
export AUTORESEARCH_LOCAL_API_HOST="${HOST}"

api_is_healthy() {
  curl -fsS "http://${PROBE_HOST}:${PORT}/healthz" >/dev/null 2>&1 \
    || curl -fsS "http://${PROBE_HOST}:${PORT}/health" >/dev/null 2>&1
}

stop_pid() {
  local pid="$1"
  if ! kill -0 "${pid}" >/dev/null 2>&1; then
    return 0
  fi
  kill "${pid}" >/dev/null 2>&1 || true
  sleep 1
  if kill -0 "${pid}" >/dev/null 2>&1; then
    kill -9 "${pid}" >/dev/null 2>&1 || true
  fi
}

find_local_api_pids() {
  if command -v pgrep >/dev/null 2>&1; then
    pgrep -u "$(id -u)" -f "${PROJECT_ROOT}/.venv/bin/python -m uvicorn autoresearch.api.main:app" || true
    return
  fi

  ps -eo pid=,args= | while read -r pid args; do
    if [[ "${args}" == *"${PROJECT_ROOT}/.venv/bin/python -m uvicorn autoresearch.api.main:app"* ]]; then
      echo "${pid}"
    fi
  done
}

echo "==> Autonomous Agent Stack local startup"
echo "    root: ${PROJECT_ROOT}"
echo "    host: ${HOST}"
echo "    port: ${PORT}"

if [[ ! -x "${VENV_PYTHON}" ]]; then
  echo
  echo "[FAIL] Missing virtualenv python: ${VENV_PYTHON}"
  echo "       Run: make setup"
  exit 1
fi

echo
echo "==> Running doctor checks..."
"${VENV_PYTHON}" "${PROJECT_ROOT}/scripts/doctor.py" --port "${PORT}"

export PYTHONPATH="${PROJECT_ROOT}/src:${PYTHONPATH:-}"

if api_is_healthy; then
  echo
  echo "==> API already healthy on http://${PROBE_HOST}:${PORT}"
  echo "==> Refreshing Telegram poller sidecar..."
  bash "${POLLER_STARTER}"
  exit 0
fi

if command -v lsof >/dev/null 2>&1; then
  if lsof -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
    declare -a EXISTING_API_PIDS=()
    while read -r pid; do
      if [[ -n "${pid}" ]]; then
        EXISTING_API_PIDS+=("${pid}")
      fi
    done < <(find_local_api_pids)

    if (( ${#EXISTING_API_PIDS[@]} > 0 )); then
      mapfile -t UNIQUE_API_PIDS < <(printf "%s\n" "${EXISTING_API_PIDS[@]}" | sort -u)
      echo
      echo "==> Restarting existing local API listener(s): ${UNIQUE_API_PIDS[*]}"
      for pid in "${UNIQUE_API_PIDS[@]}"; do
        stop_pid "${pid}"
      done
      sleep 1
    fi

    if ! api_is_healthy && lsof -iTCP:"${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
      echo
      echo "[FAIL] Port ${PORT} is already listening but API health is not ready."
      echo "       Resolve the existing listener, or use: PORT=8010 make start"
      exit 1
    fi
  fi
fi

if api_is_healthy; then
    echo
    echo "==> API became healthy on http://${PROBE_HOST}:${PORT}"
    echo "==> Refreshing Telegram poller sidecar..."
    bash "${POLLER_STARTER}"
    exit 0
fi

echo
echo "==> Starting Telegram poller sidecar..."
bash "${POLLER_STARTER}"

echo
echo "==> Starting API service..."
echo "    Docs:   http://${HOST}:${PORT}/docs"
echo "    Health: http://${HOST}:${PORT}/health"
echo "    Panel:  http://${HOST}:${PORT}/panel"
echo

exec "${API_RUNNER}"
