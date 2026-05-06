#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${ROOT_DIR}/logs/mac-worker.pid"

if [[ ! -f "${PID_FILE}" ]]; then
  echo "mac worker not running (no pid file)"
  exit 0
fi

PID="$(cat "${PID_FILE}")"
if kill -0 "${PID}" >/dev/null 2>&1; then
  kill "${PID}" >/dev/null 2>&1 || true
  sleep 2
  if kill -0 "${PID}" >/dev/null 2>&1; then
    echo "mac worker still running after graceful stop (pid=${PID})"
    exit 1
  fi
  echo "mac worker stopped (pid=${PID})"
else
  echo "stale mac worker pid file removed (pid=${PID})"
fi

rm -f "${PID_FILE}"
