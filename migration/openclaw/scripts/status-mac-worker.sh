#!/usr/bin/env bash
# status-mac-worker.sh — Show Mac worker daemon status
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "${ROOT_DIR}/../.." && pwd)"
PID_FILE="${ROOT_DIR}/logs/worker.pid"
LOG_FILE="${ROOT_DIR}/logs/worker.log"
source "${ROOT_DIR}/scripts/env-common.sh"

ENV_FILES=()
load_shared_env_files "${PROJECT_ROOT}" "${ROOT_DIR}" ENV_FILES

CONTROL_PLANE_BASE_URL="${CONTROL_PLANE_BASE_URL:-http://${AUTORESEARCH_API_HOST:-127.0.0.1}:${AUTORESEARCH_API_PORT:-8001}}"

# ── Process status ────────────────────────────────────────────────────
if [[ -f "${PID_FILE}" ]]; then
  PID="$(cat "${PID_FILE}")"
  if kill -0 "${PID}" >/dev/null 2>&1; then
    echo "worker running (pid=${PID})"
  else
    echo "worker not running (stale pid file pid=${PID})"
  fi
else
  echo "worker not running (no pid file)"
fi

# ── Control-plane inventory ───────────────────────────────────────────
echo ""
echo "control plane inventory:"
if curl -fsS "${CONTROL_PLANE_BASE_URL}/api/v1/workers/summary" 2>/dev/null; then
  echo ""
else
  echo "  (unreachable: ${CONTROL_PLANE_BASE_URL})"
fi

# ── Recent log ────────────────────────────────────────────────────────
if [[ -f "${LOG_FILE}" ]]; then
  LINES="$(wc -l < "${LOG_FILE}" | tr -d ' ')"
  SHOW=$((LINES < 10 ? LINES : 10))
  echo ""
  echo "last ${SHOW} log lines (${LOG_FILE}):"
  tail -n "${SHOW}" "${LOG_FILE}"
fi
