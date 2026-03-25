#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env.local"
CF_LOG="${ROOT_DIR}/logs/cloudflared.log"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  source "${ENV_FILE}"
  set +a
fi

BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
if [[ -z "${BOT_TOKEN}" && -f "/Users/iCloud_GZ/.openclaw/openclaw.json" ]]; then
  BOT_TOKEN="$(sed -n 's/.*"botToken"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' /Users/iCloud_GZ/.openclaw/openclaw.json | head -n 1)"
fi

SECRET_TOKEN="${AUTORESEARCH_TELEGRAM_SECRET_TOKEN:-}"
if [[ -z "${SECRET_TOKEN}" || "${SECRET_TOKEN}" == "replace_with_your_webhook_secret_token" ]]; then
  SECRET_TOKEN="ocw_$(date +%s)_$RANDOM"
  if [[ -f "${ENV_FILE}" ]]; then
    if rg -q '^AUTORESEARCH_TELEGRAM_SECRET_TOKEN=' "${ENV_FILE}"; then
      sed -i '' 's#^AUTORESEARCH_TELEGRAM_SECRET_TOKEN=.*#AUTORESEARCH_TELEGRAM_SECRET_TOKEN='"${SECRET_TOKEN}"'#' "${ENV_FILE}"
    else
      echo "AUTORESEARCH_TELEGRAM_SECRET_TOKEN=${SECRET_TOKEN}" >> "${ENV_FILE}"
    fi
  fi
  echo "generated AUTORESEARCH_TELEGRAM_SECRET_TOKEN"
fi

WEBHOOK_BASE_URL="${WEBHOOK_BASE_URL:-}"
if [[ -z "${WEBHOOK_BASE_URL}" && -f "${CF_LOG}" ]]; then
  WEBHOOK_BASE_URL="$(sed -n 's/.*\(https:\/\/[a-zA-Z0-9.-]*\.trycloudflare.com\).*/\1/p' "${CF_LOG}" | tail -n 1)"
fi

if [[ -z "${WEBHOOK_BASE_URL}" ]]; then
  echo "missing WEBHOOK_BASE_URL (example: https://your-domain.com)"
  exit 2
fi
if [[ -z "${BOT_TOKEN}" ]]; then
  echo "missing TELEGRAM_BOT_TOKEN and cannot auto-detect from ~/.openclaw/openclaw.json"
  exit 3
fi

WEBHOOK_URL="${WEBHOOK_BASE_URL%/}/api/v1/gateway/telegram/webhook"
API="https://api.telegram.org/bot${BOT_TOKEN}"

echo "setting webhook => ${WEBHOOK_URL}"
SET_RESP="$(curl -sS -X POST "${API}/setWebhook" \
  -d "url=${WEBHOOK_URL}" \
  -d "secret_token=${SECRET_TOKEN}" \
  -d "drop_pending_updates=false")"
echo "setWebhook: ${SET_RESP}"

echo "getWebhookInfo:"
curl -sS "${API}/getWebhookInfo"
echo
