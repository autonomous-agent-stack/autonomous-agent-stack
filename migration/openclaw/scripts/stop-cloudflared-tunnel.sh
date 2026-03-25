#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${ROOT_DIR}/logs/cloudflared.pid"

if [[ ! -f "${PID_FILE}" ]]; then
  echo "cloudflared not running (no pid file)"
  exit 0
fi

PID="$(cat "${PID_FILE}")"
if kill -0 "${PID}" >/dev/null 2>&1; then
  kill "${PID}" >/dev/null 2>&1 || true
  sleep 1
  if kill -0 "${PID}" >/dev/null 2>&1; then
    kill -9 "${PID}" >/dev/null 2>&1 || true
  fi
  echo "cloudflared stopped (pid=${PID})"
else
  echo "stale pid file removed (pid=${PID})"
fi
rm -f "${PID_FILE}"
