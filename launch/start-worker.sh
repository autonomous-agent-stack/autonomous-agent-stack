#!/usr/bin/env bash

set -euo pipefail

ROOT="${AAS_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
DATA_ROOT="${AAS_DATA_ROOT:-${HOME}/aas/data}"

export AUTORESEARCH_API_DB_PATH="${AUTORESEARCH_API_DB_PATH:-${DATA_ROOT}/aas.sqlite3}"
export CONTROL_PLANE_BASE_URL="${CONTROL_PLANE_BASE_URL:-http://127.0.0.1:8001}"
export HOUSEKEEPING_ROOT="${HOUSEKEEPING_ROOT:-${ROOT}}"
export WORKER_ID="${WORKER_ID:-mac-local-01}"
export WORKER_POOL="${WORKER_POOL:-mac}"

mkdir -p "${DATA_ROOT}/artifacts" "${DATA_ROOT}/logs"

cd "${ROOT}"
exec scripts/start-mac-worker.sh
