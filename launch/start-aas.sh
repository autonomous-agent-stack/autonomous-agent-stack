#!/usr/bin/env bash

set -euo pipefail

ROOT="${AAS_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
DATA_ROOT="${AAS_DATA_ROOT:-${HOME}/aas/data}"

export AUTORESEARCH_API_DB_PATH="${AUTORESEARCH_API_DB_PATH:-${DATA_ROOT}/aas.sqlite3}"
export AUTORESEARCH_MODE="${AUTORESEARCH_MODE:-minimal}"

mkdir -p "${DATA_ROOT}/artifacts" "${DATA_ROOT}/logs"

cd "${ROOT}"
exec scripts/dev-start.sh
