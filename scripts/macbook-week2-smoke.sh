#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8001}"
BASE_URL="http://${HOST}:${PORT}"
WORKER_ID="${WORKER_ID:-macbook-week2}"
HOUSEKEEPING_ROOT="${HOUSEKEEPING_ROOT:-${PROJECT_ROOT}}"
CLEANUP_ROOT="${CLEANUP_ROOT:-/Volumes/AI_LAB/Github}"
WORKER_DRY_RUN="${WORKER_DRY_RUN:-1}"
DB_PATH="${DB_PATH:-${PROJECT_ROOT}/artifacts/api/evaluations.sqlite3}"

API_LOG="$(mktemp -t macbook-week2-api.XXXXXX.log)"
WORKER_LOG="$(mktemp -t macbook-week2-worker.XXXXXX.log)"
API_PID=""
WORKER_PID=""

cleanup() {
  local exit_code=$?
  if [[ -n "${WORKER_PID}" ]] && kill -0 "${WORKER_PID}" >/dev/null 2>&1; then
    kill "${WORKER_PID}" >/dev/null 2>&1 || true
    wait "${WORKER_PID}" 2>/dev/null || true
  fi
  if [[ -n "${API_PID}" ]] && kill -0 "${API_PID}" >/dev/null 2>&1; then
    kill "${API_PID}" >/dev/null 2>&1 || true
    wait "${API_PID}" 2>/dev/null || true
  fi
  echo
  echo "api_log=${API_LOG}"
  echo "worker_log=${WORKER_LOG}"
  exit "${exit_code}"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing required command: $1" >&2
    exit 1
  fi
}

wait_for_health() {
  local attempts="${1:-30}"
  for _ in $(seq 1 "${attempts}"); do
    if curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "api did not become healthy at ${BASE_URL}/health" >&2
  return 1
}

extract_run_id() {
  "${VENV_PYTHON}" -c 'import json,sys; print(json.load(sys.stdin)["run_id"])'
}

wait_for_run_status() {
  local run_id="$1"
  local expected_status="${2:-completed}"
  local attempts="${3:-180}"
  local status=""
  for _ in $(seq 1 "${attempts}"); do
    status="$(sqlite3 "${DB_PATH}" "SELECT json_extract(payload_json, '$.status') FROM worker_run_queue WHERE resource_id='${run_id}';")"
    if [[ "${status}" == "${expected_status}" ]]; then
      printf '%s\n' "${status}"
      return 0
    fi
    if [[ "${status}" == "failed" ]]; then
      echo "run ${run_id} failed" >&2
      sqlite3 "${DB_PATH}" "SELECT payload_json FROM worker_run_queue WHERE resource_id='${run_id}';"
      return 1
    fi
    sleep 1
  done
  echo "timed out waiting for ${run_id} to reach ${expected_status}; last_status=${status:-missing}" >&2
  return 1
}

print_run_summary() {
  local run_id="$1"
  sqlite3 "${DB_PATH}" "SELECT resource_id, json_extract(payload_json, '$.status') AS status, json_extract(payload_json, '$.assigned_worker_id') AS worker_id, json_extract(payload_json, '$.result.deleted_count') AS deleted_count FROM worker_run_queue WHERE resource_id='${run_id}';"
  sqlite3 "${DB_PATH}" "SELECT resource_id, json_extract(payload_json, '$.active') AS active FROM worker_leases WHERE json_extract(payload_json, '$.run_id')='${run_id}';"
}

trap cleanup EXIT INT TERM

require_command curl
require_command sqlite3

if [[ ! -x "${VENV_PYTHON}" ]]; then
  echo "missing virtualenv python: ${VENV_PYTHON}" >&2
  echo "run: make setup" >&2
  exit 1
fi

echo "==> Starting API on ${BASE_URL}"
(
  cd "${PROJECT_ROOT}"
  HOST="${HOST}" PORT="${PORT}" bash scripts/dev-start.sh
) >"${API_LOG}" 2>&1 &
API_PID=$!

wait_for_health
curl -fsS "${BASE_URL}/health"
echo

echo "==> Starting Mac standby worker"
(
  cd "${PROJECT_ROOT}"
  CONTROL_PLANE_BASE_URL="${BASE_URL}" \
  WORKER_ID="${WORKER_ID}" \
  HOUSEKEEPING_ROOT="${HOUSEKEEPING_ROOT}" \
  WORKER_DRY_RUN="${WORKER_DRY_RUN}" \
  bash scripts/start-mac-worker.sh
) >"${WORKER_LOG}" 2>&1 &
WORKER_PID=$!

sleep 2

echo "==> Enqueue noop"
NOOP_RUN_ID="$(
  curl -fsS \
    -X POST "${BASE_URL}/api/v1/worker-runs" \
    -H 'Content-Type: application/json' \
    -d '{"queue_name":"housekeeping","task_type":"noop","payload":{"message":"macbook week2 smoke"},"requested_by":"macbook_week2_smoke"}' \
  | extract_run_id
)"
wait_for_run_status "${NOOP_RUN_ID}" completed >/dev/null
print_run_summary "${NOOP_RUN_ID}"

echo
echo "==> Enqueue cleanup_appledouble dry-run"
CLEANUP_RUN_ID="$(
  curl -fsS \
    -X POST "${BASE_URL}/api/v1/worker-runs" \
    -H 'Content-Type: application/json' \
    -d "{\"queue_name\":\"housekeeping\",\"task_type\":\"cleanup_appledouble\",\"payload\":{\"root_path\":\"${CLEANUP_ROOT}\",\"recursive\":true,\"dry_run\":true},\"requested_by\":\"macbook_week2_smoke\"}" \
  | extract_run_id
)"
wait_for_run_status "${CLEANUP_RUN_ID}" completed >/dev/null
print_run_summary "${CLEANUP_RUN_ID}"

echo
echo "dry_run_note=result.deleted_count is a candidate count when payload.dry_run=true"
