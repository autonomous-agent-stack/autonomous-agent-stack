#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "${ROOT_DIR}/../.." && pwd)"
PID_FILE="${ROOT_DIR}/logs/telegram-poller.pid"
LOG_FILE="${ROOT_DIR}/logs/telegram-poller.log"
source "${ROOT_DIR}/scripts/env-common.sh"

ENV_FILES=()
load_shared_env_files "${PROJECT_ROOT}" "${ROOT_DIR}" ENV_FILES
warn_env_conflicts ENV_FILES AUTORESEARCH_TELEGRAM_INGRESS_MODE AUTORESEARCH_TELEGRAM_POLLING_ENABLED

INGRESS_MODE="$(echo "${AUTORESEARCH_TELEGRAM_INGRESS_MODE:-webhook}" | tr '[:upper:]' '[:lower:]')"
if [[ "${INGRESS_MODE}" != "webhook" && "${INGRESS_MODE}" != "polling" ]]; then
  INGRESS_MODE="webhook"
fi

if [[ "${INGRESS_MODE}" != "polling" ]]; then
  echo "telegram poller disabled by ingress mode (AUTORESEARCH_TELEGRAM_INGRESS_MODE=${INGRESS_MODE})"
  exit 0
fi

if is_truthy_env_value "${AUTORESEARCH_TELEGRAM_POLLING_ENABLED:-false}"; then
  echo "Telegram polling 由 API 内置 daemon 承担 / Telegram poller handled by API embedded polling"
  if [[ -f "${PID_FILE}" ]]; then
    PID="$(cat "${PID_FILE}")"
    if kill -0 "${PID}" >/dev/null 2>&1; then
      echo "警告：外置 Telegram poller 仍在运行 pid=${PID} / Warning: external Telegram poller still running"
    fi
  fi
  exit 0
fi

if [[ -f "${PID_FILE}" ]]; then
  PID="$(cat "${PID_FILE}")"
  if kill -0 "${PID}" >/dev/null 2>&1; then
    echo "telegram poller running (pid=${PID})"
  else
    echo "telegram poller not running (stale pid=${PID})"
  fi
else
  echo "telegram poller not running"
fi

if [[ -f "${LOG_FILE}" ]]; then
  tail -n 20 "${LOG_FILE}"
else
  echo "no log: ${LOG_FILE}"
fi

python3 "${PROJECT_ROOT}/scripts/telegram_ingress_health.py" --minutes 30 --json || true
