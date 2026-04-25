#!/usr/bin/env bash
# start-mac-worker.sh — Start the Mac worker daemon (housekeeper)
#
# Usage:
#   bash migration/openclaw/scripts/start-mac-worker.sh
#   make worker-start
#
# Environment (optional, see .env.example):
#   CONTROL_PLANE_BASE_URL  API base URL  (default: http://127.0.0.1:8001)
#   WORKER_DRY_RUN          true/false    (default: false)
#   WORKER_ROLE             role string   (default: housekeeper)
#   WORKER_HEARTBEAT_SEC    seconds       (default: 15)
#   WORKER_CLAIM_POLL_SEC   seconds       (default: 5)
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "${ROOT_DIR}/../.." && pwd)"
PID_FILE="${ROOT_DIR}/logs/worker.pid"
LOG_FILE="${ROOT_DIR}/logs/worker.log"
source "${ROOT_DIR}/scripts/env-common.sh"

mkdir -p "${ROOT_DIR}/logs" "${PROJECT_ROOT}/artifacts/api"

ENV_FILES=()
load_shared_env_files "${PROJECT_ROOT}" "${ROOT_DIR}" ENV_FILES
warn_env_conflicts ENV_FILES CONTROL_PLANE_BASE_URL AUTORESEARCH_API_HOST AUTORESEARCH_API_PORT

CONTROL_PLANE_BASE_URL="${CONTROL_PLANE_BASE_URL:-http://${AUTORESEARCH_API_HOST:-127.0.0.1}:${AUTORESEARCH_API_PORT:-8001}}"
WORKER_DRY_RUN="${WORKER_DRY_RUN:-false}"
WORKER_ROLE="${WORKER_ROLE:-housekeeper}"

print_effective_env_values CONTROL_PLANE_BASE_URL WORKER_DRY_RUN WORKER_ROLE

# ── Already running? ──────────────────────────────────────────────────
if [[ -f "${PID_FILE}" ]]; then
  PID="$(cat "${PID_FILE}")"
  if kill -0 "${PID}" >/dev/null 2>&1; then
    echo "worker already running (pid=${PID})"
    exit 0
  fi
  rm -f "${PID_FILE}"
fi

# ── Prerequisites ─────────────────────────────────────────────────────
HEALTH_URL="${CONTROL_PLANE_BASE_URL}/healthz"
if ! curl -fsS "${HEALTH_URL}" >/dev/null 2>&1; then
  echo "control plane not healthy: ${HEALTH_URL}"
  echo "hint: run 'make telegram-butler-start' or 'make start' first"
  exit 1
fi

# Determine Python interpreter
PYTHON_CMD=""
if [[ -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
  PYTHON_CMD="${PROJECT_ROOT}/.venv/bin/python"
else
  PYTHON_CMD="$(command -v python3 || command -v python)"
fi
if [[ -z "${PYTHON_CMD}" ]]; then
  echo "no python found — create .venv with 'make setup' or install python3"
  exit 1
fi

# ── Launch ─────────────────────────────────────────────────────────────
cd "${PROJECT_ROOT}"

# Resolve DB path relative to PROJECT_ROOT so worker shares the API's database.
# Without this the worker would compute its own _REPO_ROOT from PYTHONPATH and
# may point at a different DB than the running API.
AUTORESEARCH_API_DB_PATH="${AUTORESEARCH_API_DB_PATH:-${PROJECT_ROOT}/artifacts/api/evaluations.sqlite3}"

# Ask the running control plane which DB it uses. If it responds, align the
# worker to the same path — this avoids drift when the script is invoked from
# a git worktree whose PROJECT_ROOT differs from the live API's checkout.
API_REPORTED_DB="$(curl -fsS "${CONTROL_PLANE_BASE_URL}/healthz" 2>/dev/null \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('checks',{}).get('db',{}).get('path',''))" 2>/dev/null || true)"
if [[ -n "${API_REPORTED_DB}" && -f "${API_REPORTED_DB}" ]]; then
  AUTORESEARCH_API_DB_PATH="${API_REPORTED_DB}"
fi

nohup env \
  PYTHONPATH=src \
  CONTROL_PLANE_BASE_URL="${CONTROL_PLANE_BASE_URL}" \
  WORKER_DRY_RUN="${WORKER_DRY_RUN}" \
  WORKER_ROLE="${WORKER_ROLE}" \
  AUTORESEARCH_API_DB_PATH="${AUTORESEARCH_API_DB_PATH}" \
  "${PYTHON_CMD}" -m autoresearch.workers.mac.daemon \
  >> "${LOG_FILE}" 2>&1 &

PID=$!
echo "${PID}" > "${PID_FILE}"

# Wait up to 10s for the process to stay alive
for _ in {1..10}; do
  if ! kill -0 "${PID}" >/dev/null 2>&1; then
    rm -f "${PID_FILE}"
    echo "worker exited prematurely — check ${LOG_FILE}"
    exit 1
  fi
  sleep 1
done

echo "worker started (pid=${PID})"
echo "control plane: ${CONTROL_PLANE_BASE_URL}"
echo "log: ${LOG_FILE}"
