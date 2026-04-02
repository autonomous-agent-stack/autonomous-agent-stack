#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${REPO_ROOT}/logs/telegram-poller.pid"

if [[ ! -f "${PID_FILE}" ]]; then
  echo "telegram poller not running (no pid file)"
  exit 0
fi

PID="$(cat "${PID_FILE}")"
if kill -0 "${PID}" >/dev/null 2>&1; then
  kill "${PID}" >/dev/null 2>&1 || true
  sleep 1
  if kill -0 "${PID}" >/dev/null 2>&1; then
    kill -9 "${PID}" >/dev/null 2>&1 || true
  fi
  echo "telegram poller stopped (pid=${PID})"
else
  echo "stale pid file removed (pid=${PID})"
fi

rm -f "${PID_FILE}"
