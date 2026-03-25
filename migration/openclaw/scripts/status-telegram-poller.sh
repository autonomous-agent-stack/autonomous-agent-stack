#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${ROOT_DIR}/logs/telegram-poller.pid"
LOG_FILE="${ROOT_DIR}/logs/telegram-poller.log"

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
