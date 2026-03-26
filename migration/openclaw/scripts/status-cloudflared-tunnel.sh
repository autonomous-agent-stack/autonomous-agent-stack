#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env.local"
PID_FILE="${ROOT_DIR}/logs/cloudflared.pid"
LOG_FILE="${ROOT_DIR}/logs/cloudflared.log"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  source "${ENV_FILE}"
  set +a
fi

if [[ -f "${PID_FILE}" ]]; then
  PID="$(cat "${PID_FILE}")"
  if kill -0 "${PID}" >/dev/null 2>&1; then
    echo "cloudflared running (pid=${PID})"
  else
    echo "cloudflared not running (stale pid=${PID})"
  fi
else
  echo "cloudflared not running"
fi

if [[ -n "${CLOUDFLARE_TUNNEL_PUBLIC_BASE_URL:-}" ]]; then
  echo "public_url=${CLOUDFLARE_TUNNEL_PUBLIC_BASE_URL}"
elif [[ -n "${CLOUDFLARE_TUNNEL_DOMAIN:-}" ]]; then
  echo "public_url=https://${CLOUDFLARE_TUNNEL_DOMAIN}"
else
  URL="$(sed -n 's/.*\(https:\/\/[a-zA-Z0-9.-]*\.trycloudflare.com\).*/\1/p' "${LOG_FILE}" | tail -n 1)"
  if [[ -n "${URL}" ]]; then
    echo "public_url=${URL}"
  else
    echo "public_url=unknown"
  fi
fi

if [[ -f "${LOG_FILE}" ]]; then
  echo "log=${LOG_FILE}"
fi
