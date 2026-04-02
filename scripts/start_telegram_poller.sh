#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${REPO_ROOT}/logs/telegram-poller.pid"
LOG_FILE="${REPO_ROOT}/logs/telegram-poller.log"
RUNNER="${REPO_ROOT}/scripts/run_telegram_poller.sh"

mkdir -p "${REPO_ROOT}/logs"

if [[ -f "${PID_FILE}" ]]; then
  PID="$(cat "${PID_FILE}")"
  if kill -0 "${PID}" >/dev/null 2>&1; then
    echo "telegram poller already running (pid=${PID})"
    exit 0
  fi
  rm -f "${PID_FILE}"
fi

if [[ ! -x "${RUNNER}" ]]; then
  echo "missing poller runner: ${RUNNER}"
  exit 1
fi

cd "${REPO_ROOT}"
if command -v setsid >/dev/null 2>&1; then
  setsid "${RUNNER}" </dev/null >> "${LOG_FILE}" 2>&1 &
else
  nohup "${RUNNER}" </dev/null >> "${LOG_FILE}" 2>&1 &
fi
PID=$!
echo "${PID}" > "${PID_FILE}"

sleep 2
if kill -0 "${PID}" >/dev/null 2>&1; then
  echo "telegram poller started (pid=${PID})"
  exit 0
fi

echo "telegram poller failed to start, check: ${LOG_FILE}"
exit 1
