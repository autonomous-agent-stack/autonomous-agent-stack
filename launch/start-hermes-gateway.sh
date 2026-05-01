#!/usr/bin/env bash

set -euo pipefail

ROOT="${AAS_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
DATA_ROOT="${AAS_DATA_ROOT:-${HOME}/aas/data}"

export AUTORESEARCH_API_DB_PATH="${AUTORESEARCH_API_DB_PATH:-${DATA_ROOT}/aas.sqlite3}"
export HERMES_GATEWAY_CONFIG="${HERMES_GATEWAY_CONFIG:-${ROOT}/configs/runtime_agents/hermes.yaml}"

mkdir -p "${DATA_ROOT}/artifacts" "${DATA_ROOT}/logs"

if [[ -z "${HERMES_GATEWAY_COMMAND:-}" ]]; then
  echo "未配置 Hermes gateway 启动命令；设置 HERMES_GATEWAY_COMMAND 后再启动。"
  echo "Hermes gateway command is not configured; set HERMES_GATEWAY_COMMAND to start it."
  exit 0
fi

cd "${ROOT}"
exec bash -lc "${HERMES_GATEWAY_COMMAND}"
