#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "${ROOT_DIR}/../.." && pwd)"
PID_FILE="${ROOT_DIR}/logs/api.pid"
LOG_FILE="${ROOT_DIR}/logs/api.log"
source "${ROOT_DIR}/scripts/env-common.sh"

mkdir -p "${ROOT_DIR}/logs" "${PROJECT_ROOT}/artifacts/api"

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

ENV_FILES=()
load_shared_env_files "${PROJECT_ROOT}" "${ROOT_DIR}" ENV_FILES
warn_env_conflicts ENV_FILES AUTORESEARCH_API_HOST AUTORESEARCH_API_PORT

AUTORESEARCH_API_HOST="${AUTORESEARCH_API_HOST:-127.0.0.1}"
AUTORESEARCH_API_PORT="${AUTORESEARCH_API_PORT:-8001}"
print_effective_env_values AUTORESEARCH_API_HOST AUTORESEARCH_API_PORT

cd "${PROJECT_ROOT}"
nohup env PYTHONPATH=src "${PROJECT_ROOT}/.venv/bin/python" -m uvicorn autoresearch.api.main:app \
  --host "${AUTORESEARCH_API_HOST}" --port "${AUTORESEARCH_API_PORT}" >> "${LOG_FILE}" 2>&1 &
PID=$!
echo "${PID}" > "${PID_FILE}"

for _ in {1..30}; do
  if curl -fsS "http://${AUTORESEARCH_API_HOST}:${AUTORESEARCH_API_PORT}/healthz" >/dev/null 2>&1; then
    echo "api started (pid=${PID})"
    echo "health: http://${AUTORESEARCH_API_HOST}:${AUTORESEARCH_API_PORT}/healthz"
    exit 0
  fi
  sleep 1
done

echo "api failed to become healthy, check: ${LOG_FILE}"
exit 1
