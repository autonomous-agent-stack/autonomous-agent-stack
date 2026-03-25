#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env.local"
LOG_DIR="${ROOT_DIR}/logs"
PID_FILE="${LOG_DIR}/cloudflared.pid"
LOG_FILE="${LOG_DIR}/cloudflared.log"
mkdir -p "${LOG_DIR}"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  source "${ENV_FILE}"
  set +a
fi

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

TUNNEL_LOCAL_URL="${CLOUDFLARE_TUNNEL_LOCAL_URL:-http://127.0.0.1:8000}"
TUNNEL_CONFIG_FILE="${CLOUDFLARE_TUNNEL_CONFIG_FILE:-}"
TUNNEL_NAME="${CLOUDFLARE_TUNNEL_NAME:-}"
TUNNEL_ID="${CLOUDFLARE_TUNNEL_ID:-}"
PUBLIC_BASE_URL="${CLOUDFLARE_TUNNEL_PUBLIC_BASE_URL:-}"
TUNNEL_DOMAIN="${CLOUDFLARE_TUNNEL_DOMAIN:-}"

run_mode="quick"
if [[ -n "${TUNNEL_CONFIG_FILE}" && -f "${TUNNEL_CONFIG_FILE}" ]]; then
  run_mode="named"
elif [[ -f "${ROOT_DIR}/cloudflared/config.yml" ]]; then
  TUNNEL_CONFIG_FILE="${ROOT_DIR}/cloudflared/config.yml"
  run_mode="named"
fi

if [[ "${run_mode}" == "named" ]]; then
  RUN_TARGET="${TUNNEL_NAME:-${TUNNEL_ID:-}}"
  if [[ -z "${RUN_TARGET}" ]]; then
    echo "missing CLOUDFLARE_TUNNEL_NAME or CLOUDFLARE_TUNNEL_ID for named tunnel mode"
    exit 2
  fi
  nohup cloudflared tunnel --config "${TUNNEL_CONFIG_FILE}" run "${RUN_TARGET}" > "${LOG_FILE}" 2>&1 &
else
  nohup cloudflared tunnel --url "${TUNNEL_LOCAL_URL}" > "${LOG_FILE}" 2>&1 &
fi
PID=$!
echo "${PID}" > "${PID_FILE}"

for _ in {1..40}; do
  URL=""
  if [[ -n "${PUBLIC_BASE_URL}" ]]; then
    URL="${PUBLIC_BASE_URL}"
  elif [[ -n "${TUNNEL_DOMAIN}" ]]; then
    URL="https://${TUNNEL_DOMAIN}"
  else
    URL="$(sed -n 's/.*\(https:\/\/[a-zA-Z0-9.-]*\.trycloudflare.com\).*/\1/p' "${LOG_FILE}" | tail -n 1)"
  fi
  if [[ -n "${URL}" && kill -0 "${PID}" >/dev/null 2>&1 ]]; then
    echo "cloudflared started (pid=${PID})"
    echo "mode=${run_mode}"
    echo "public_url=${URL}"
    exit 0
  fi
  if ! kill -0 "${PID}" >/dev/null 2>&1; then
    echo "cloudflared exited unexpectedly, check log: ${LOG_FILE}"
    exit 1
  fi
  sleep 1
done

echo "cloudflared started but URL not found yet, check log: ${LOG_FILE}"
exit 1
