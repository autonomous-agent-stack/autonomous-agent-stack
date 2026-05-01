#!/usr/bin/env bash

set -euo pipefail

ROOT="${AAS_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
DATA_ROOT="${AAS_DATA_ROOT:-${HOME}/aas/data}"
LOG_ROOT="${DATA_ROOT}/logs"

mkdir -p "${DATA_ROOT}/artifacts" "${LOG_ROOT}"

export AAS_REPO_ROOT="${ROOT}"
export AAS_DATA_ROOT="${DATA_ROOT}"
export AUTORESEARCH_API_DB_PATH="${AUTORESEARCH_API_DB_PATH:-${DATA_ROOT}/aas.sqlite3}"

pids=()

cleanup() {
  for pid in "${pids[@]}"; do
    if kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
    fi
  done
}

trap cleanup INT TERM EXIT

"${ROOT}/launch/start-aas.sh" >"${LOG_ROOT}/aas-api.log" 2>&1 &
pids+=("$!")

sleep 2

"${ROOT}/launch/start-worker.sh" >"${LOG_ROOT}/mac-worker.log" 2>&1 &
pids+=("$!")

if [[ -n "${HERMES_GATEWAY_COMMAND:-}" ]]; then
  "${ROOT}/launch/start-hermes-gateway.sh" >"${LOG_ROOT}/hermes-gateway.log" 2>&1 &
  pids+=("$!")
fi

echo "AAS API 与 Mac worker 正在启动。日志目录：${LOG_ROOT}"
echo "AAS API and Mac worker are starting. Logs: ${LOG_ROOT}"

wait -n "${pids[@]}"
