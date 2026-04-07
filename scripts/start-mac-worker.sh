#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python"

for ENV_FILE in "${PROJECT_ROOT}/.env" "${PROJECT_ROOT}/.env.local"; do
  if [[ -f "${ENV_FILE}" ]]; then
    set -a
    source "${ENV_FILE}"
    set +a
  fi
done

if [[ ! -x "${VENV_PYTHON}" ]]; then
  echo "[FAIL] Missing virtualenv python: ${VENV_PYTHON}"
  echo "       Run: make setup"
  exit 1
fi

export PYTHONPATH="${PROJECT_ROOT}/src:${PYTHONPATH:-}"
export CONTROL_PLANE_BASE_URL="${CONTROL_PLANE_BASE_URL:-http://127.0.0.1:${AUTORESEARCH_API_PORT:-8001}}"
export WORKER_ID="${WORKER_ID:-mac-$(hostname -s)}"
export WORKER_NAME="${WORKER_NAME:-Mac Standby Worker}"
export WORKER_HOST="${WORKER_HOST:-$(hostname)}"
export WORKER_ROLE="${WORKER_ROLE:-housekeeper}"
export WORKER_HEARTBEAT_SEC="${WORKER_HEARTBEAT_SEC:-15}"
export WORKER_CLAIM_POLL_SEC="${WORKER_CLAIM_POLL_SEC:-5}"
export WORKER_LEASE_TTL_SEC="${WORKER_LEASE_TTL_SEC:-60}"
export HOUSEKEEPING_ROOT="${HOUSEKEEPING_ROOT:-${PROJECT_ROOT}}"
export WORKER_DRY_RUN="${WORKER_DRY_RUN:-1}"

echo "==> Starting Mac standby worker"
echo "    worker_id: ${WORKER_ID}"
echo "    control_plane: ${CONTROL_PLANE_BASE_URL}"
echo "    housekeeping_root: ${HOUSEKEEPING_ROOT}"
echo "    dry_run: ${WORKER_DRY_RUN}"

exec "${VENV_PYTHON}" -m autoresearch.workers.mac.daemon
