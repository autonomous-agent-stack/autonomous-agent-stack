#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "${ROOT_DIR}/../.." && pwd)"
PID_FILE="${ROOT_DIR}/logs/mac-worker.pid"
LOG_FILE="${ROOT_DIR}/logs/mac-worker.log"

mkdir -p "${ROOT_DIR}/logs"

if [[ -f "${PID_FILE}" ]]; then
  PID="$(cat "${PID_FILE}")"
  if kill -0 "${PID}" >/dev/null 2>&1; then
    echo "mac worker already running (pid=${PID})"
    exit 0
  fi
  rm -f "${PID_FILE}"
fi

if [[ ! -x "${PROJECT_ROOT}/scripts/start-mac-worker.sh" ]]; then
  echo "missing worker launcher: ${PROJECT_ROOT}/scripts/start-mac-worker.sh"
  exit 1
fi

cd "${PROJECT_ROOT}"
nohup bash "${PROJECT_ROOT}/scripts/start-mac-worker.sh" >> "${LOG_FILE}" 2>&1 &
PID=$!
echo "${PID}" > "${PID_FILE}"

sleep 1
if kill -0 "${PID}" >/dev/null 2>&1; then
  echo "mac worker started (pid=${PID})"
  echo "log: ${LOG_FILE}"
  exit 0
fi

rm -f "${PID_FILE}"
echo "mac worker failed to stay running, check: ${LOG_FILE}"
exit 1
