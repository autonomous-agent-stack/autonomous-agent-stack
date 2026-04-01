#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
COMMAND="${1:-}"
shift || true

RUNTIME_ROOT="${AUTORESEARCH_LINUX_HOUSEKEEPER_ROOT:-${REPO_ROOT}/.masfactory_runtime/linux-housekeeper}"
STATE_DIR="${RUNTIME_ROOT}/state"
PID_FILE="${STATE_DIR}/supervisor.pid"
LOG_FILE="${STATE_DIR}/supervisor.log"
PYTHON_BIN="${AUTORESEARCH_HOUSEKEEPER_PYTHON:-${REPO_ROOT}/.venv/bin/python}"
ENV_FILE="${LINUX_ENV_FILE:-}"

load_env() {
  if [[ -n "${ENV_FILE}" ]]; then
    :
  elif [[ -f "${REPO_ROOT}/.env.linux" ]]; then
    ENV_FILE="${REPO_ROOT}/.env.linux"
  elif [[ -f "${REPO_ROOT}/ai_lab.env" ]]; then
    ENV_FILE="${REPO_ROOT}/ai_lab.env"
  else
    ENV_FILE=""
  fi

  if [[ -n "${ENV_FILE}" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
  fi
}

ensure_dirs() {
  mkdir -p "${STATE_DIR}"
}

require_python() {
  if [[ ! -x "${PYTHON_BIN}" ]]; then
    echo "missing python interpreter: ${PYTHON_BIN}" >&2
    exit 40
  fi
}

is_running() {
  [[ -f "${PID_FILE}" ]] || return 1
  local pid
  pid="$(cat "${PID_FILE}")"
  [[ -n "${pid}" ]] || return 1
  kill -0 "${pid}" 2>/dev/null
}

run_python() {
  load_env
  require_python
  PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}" \
    "${PYTHON_BIN}" "${REPO_ROOT}/scripts/linux_housekeeper_supervisor.py" \
    --repo-root "${REPO_ROOT}" \
    --runtime-root "${RUNTIME_ROOT}" \
    "$@"
}

case "${COMMAND}" in
  start)
    ensure_dirs
    if is_running; then
      echo "linux housekeeper supervisor already running (pid=$(cat "${PID_FILE}"))"
      exit 0
    fi
    load_env
    require_python
    nohup env PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}" \
      "${PYTHON_BIN}" "${REPO_ROOT}/scripts/linux_housekeeper_supervisor.py" \
      --repo-root "${REPO_ROOT}" \
      --runtime-root "${RUNTIME_ROOT}" \
      run-forever >> "${LOG_FILE}" 2>&1 &
    echo "$!" > "${PID_FILE}"
    echo "started linux housekeeper supervisor pid=$!"
    ;;
  stop)
    if ! is_running; then
      echo "linux housekeeper supervisor is not running"
      rm -f "${PID_FILE}"
      exit 0
    fi
    pid="$(cat "${PID_FILE}")"
    kill "${pid}"
    sleep 1
    if kill -0 "${pid}" 2>/dev/null; then
      kill -9 "${pid}"
    fi
    rm -f "${PID_FILE}"
    echo "stopped linux housekeeper supervisor pid=${pid}"
    ;;
  status)
    if is_running; then
      echo "linux housekeeper supervisor running (pid=$(cat "${PID_FILE}"))"
    else
      echo "linux housekeeper supervisor stopped"
    fi
    run_python status
    ;;
  run-once)
    run_python run-once
    ;;
  repair)
    run_python repair
    ;;
  enqueue)
    PROMPT="${1:?usage: $0 enqueue 'task prompt'}"
    shift || true
    run_python enqueue --prompt "${PROMPT}" "$@"
    ;;
  enqueue-test)
    TEST_PROMPT="${LINUX_HOUSEKEEPER_TEST_PROMPT:-Create apps/linux_supervisor_smoke/ok.py and a tiny passing test.}"
    run_python enqueue --prompt "${TEST_PROMPT}"
    ;;
  logs)
    ensure_dirs
    if [[ -f "${LOG_FILE}" ]]; then
      cat "${LOG_FILE}"
    fi
    ;;
  *)
    echo "usage: $0 <start|stop|status|run-once|repair|enqueue|enqueue-test|logs>" >&2
    exit 2
    ;;
esac
