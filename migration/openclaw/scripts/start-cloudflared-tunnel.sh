#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"
PID_FILE="${LOG_DIR}/cloudflared.pid"
LOG_FILE="${LOG_DIR}/cloudflared.log"
mkdir -p "${LOG_DIR}"

if [[ -f "${PID_FILE}" ]]; then
  PID="$(cat "${PID_FILE}")"
  if kill -0 "${PID}" >/dev/null 2>&1; then
    echo "cloudflared already running (pid=${PID})"
    exit 0
  fi
  rm -f "${PID_FILE}"
fi

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared not found"
  exit 1
fi

nohup cloudflared tunnel --url http://127.0.0.1:8000 > "${LOG_FILE}" 2>&1 &
PID=$!
echo "${PID}" > "${PID_FILE}"

for _ in {1..40}; do
  URL="$(sed -n 's/.*\(https:\/\/[a-zA-Z0-9.-]*\.trycloudflare.com\).*/\1/p' "${LOG_FILE}" | tail -n 1)"
  if [[ -n "${URL}" ]]; then
    echo "cloudflared started (pid=${PID})"
    echo "public_url=${URL}"
    exit 0
  fi
  sleep 1
done

echo "cloudflared started but URL not found yet, check log: ${LOG_FILE}"
exit 1
