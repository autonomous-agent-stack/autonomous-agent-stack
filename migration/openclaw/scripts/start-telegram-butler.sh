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
INGRESS_MODE="$(echo "${AUTORESEARCH_TELEGRAM_INGRESS_MODE:-webhook}" | tr '[:upper:]' '[:lower:]')"
if [[ "${INGRESS_MODE}" != "webhook" && "${INGRESS_MODE}" != "polling" ]]; then
  INGRESS_MODE="webhook"
fi
if [[ "${INGRESS_MODE}" == "polling" ]]; then
  echo "[telegram-butler] polling ingress enabled; starting telegram poller"
  bash "${SCRIPT_DIR}/start-telegram-poller.sh"
else
  echo "[telegram-butler] webhook ingress mode; skipping telegram poller startup"
fi

echo
echo "[telegram-butler] current status"
bash "${SCRIPT_DIR}/status-api-daemon.sh"
bash "${SCRIPT_DIR}/status-telegram-poller.sh"
python3 "${PROJECT_ROOT}/scripts/telegram_ingress_health.py" --minutes 60 --json || true
