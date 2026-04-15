#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_DIR="${ROOT_DIR}/scripts"
source "${ROOT_DIR}/scripts/env-common.sh"

PROJECT_ROOT="$(cd "${ROOT_DIR}/../.." && pwd)"
ENV_FILES=()
load_shared_env_files "${PROJECT_ROOT}" "${ROOT_DIR}" ENV_FILES
warn_env_conflicts ENV_FILES AUTORESEARCH_API_HOST AUTORESEARCH_API_PORT AUTORESEARCH_TELEGRAM_BOT_TOKEN TELEGRAM_BOT_TOKEN
echo "[telegram-butler] resolved startup config"
print_effective_env_values AUTORESEARCH_API_HOST AUTORESEARCH_API_PORT AUTORESEARCH_TELEGRAM_BOT_TOKEN TELEGRAM_BOT_TOKEN

bash "${SCRIPT_DIR}/start-api-daemon.sh"
bash "${SCRIPT_DIR}/start-telegram-poller.sh"

echo
echo "[telegram-butler] current status"
bash "${SCRIPT_DIR}/status-api-daemon.sh"
bash "${SCRIPT_DIR}/status-telegram-poller.sh"
