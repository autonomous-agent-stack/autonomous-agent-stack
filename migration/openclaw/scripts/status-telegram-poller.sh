#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${ROOT_DIR}/logs/telegram-poller.pid"
LOG_FILE="${ROOT_DIR}/logs/telegram-poller.log"
INGRESS_MODE="$(echo "${AUTORESEARCH_TELEGRAM_INGRESS_MODE:-webhook}" | tr '[:upper:]' '[:lower:]')"
if [[ "${INGRESS_MODE}" != "webhook" && "${INGRESS_MODE}" != "polling" ]]; then
  INGRESS_MODE="webhook"
fi

if [[ "${INGRESS_MODE}" != "polling" ]]; then
  echo "telegram poller disabled by ingress mode (AUTORESEARCH_TELEGRAM_INGRESS_MODE=${INGRESS_MODE})"
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

PROJECT_ROOT="$(cd "${ROOT_DIR}/../.." && pwd)"
python3 "${PROJECT_ROOT}/scripts/telegram_ingress_health.py" --minutes 30 --json || true
