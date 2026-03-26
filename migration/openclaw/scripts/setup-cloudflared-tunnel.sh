#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env.local"
CF_DIR="${ROOT_DIR}/cloudflared"
CF_CONFIG_FILE="${CF_DIR}/config.yml"

mkdir -p "${CF_DIR}" "${ROOT_DIR}/logs"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  source "${ENV_FILE}"
  set +a
fi

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared not found, install with: brew install cloudflared"
  exit 1
fi

CERT_FILE="${HOME}/.cloudflared/cert.pem"
if [[ ! -f "${CERT_FILE}" ]]; then
  echo "missing ${CERT_FILE}"
  echo "run once: cloudflared tunnel login"
  exit 2
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  if [[ -f "${ROOT_DIR}/templates/openclaw-to-autoresearch.env.example" ]]; then
    cp "${ROOT_DIR}/templates/openclaw-to-autoresearch.env.example" "${ENV_FILE}"
    echo "created ${ENV_FILE} from template"
  else
    touch "${ENV_FILE}"
  fi
fi

upsert_env() {
  local key="$1"
  local value="$2"
  if rg -q "^${key}=" "${ENV_FILE}"; then
    sed -i '' "s#^${key}=.*#${key}=${value}#" "${ENV_FILE}"
  else
    echo "${key}=${value}" >> "${ENV_FILE}"
  fi
}

extract_tunnel_id() {
  local info="$1"
  printf '%s\n' "${info}" | sed -n 's/^ID:[[:space:]]*//p' | head -n 1
}

TUNNEL_NAME="${CLOUDFLARE_TUNNEL_NAME:-autonomous-agent-stack}"
TUNNEL_DOMAIN="${1:-${CLOUDFLARE_TUNNEL_DOMAIN:-}}"

if [[ -z "${TUNNEL_DOMAIN}" ]]; then
  echo "usage: bash migration/openclaw/scripts/setup-cloudflared-tunnel.sh <your-domain>"
  echo "example: bash migration/openclaw/scripts/setup-cloudflared-tunnel.sh panel.malu.com"
  exit 3
fi

INFO_OUTPUT="$(cloudflared tunnel info "${TUNNEL_NAME}" 2>/dev/null || true)"
TUNNEL_ID="$(extract_tunnel_id "${INFO_OUTPUT}")"

if [[ -z "${TUNNEL_ID}" ]]; then
  echo "creating tunnel: ${TUNNEL_NAME}"
  cloudflared tunnel create "${TUNNEL_NAME}" >/dev/null
  INFO_OUTPUT="$(cloudflared tunnel info "${TUNNEL_NAME}" 2>/dev/null || true)"
  TUNNEL_ID="$(extract_tunnel_id "${INFO_OUTPUT}")"
fi

if [[ -z "${TUNNEL_ID}" ]]; then
  echo "failed to resolve tunnel id for name=${TUNNEL_NAME}"
  exit 4
fi

TUNNEL_LOCAL_URL="${CLOUDFLARE_TUNNEL_LOCAL_URL:-http://127.0.0.1:8001}"
CREDENTIALS_FILE="${CLOUDFLARE_TUNNEL_CREDENTIALS_FILE:-${HOME}/.cloudflared/${TUNNEL_ID}.json}"

if [[ ! -f "${CREDENTIALS_FILE}" ]]; then
  echo "missing credentials file: ${CREDENTIALS_FILE}"
  echo "ensure tunnel ${TUNNEL_NAME} was created by current user account"
  exit 5
fi

cat > "${CF_CONFIG_FILE}" <<EOF
tunnel: ${TUNNEL_ID}
credentials-file: ${CREDENTIALS_FILE}

ingress:
  - hostname: ${TUNNEL_DOMAIN}
    service: ${TUNNEL_LOCAL_URL}
  - service: http_status:404
EOF

set +e
ROUTE_OUTPUT="$(cloudflared tunnel route dns "${TUNNEL_NAME}" "${TUNNEL_DOMAIN}" 2>&1)"
ROUTE_CODE=$?
set -e
if [[ ${ROUTE_CODE} -ne 0 ]] && ! printf '%s' "${ROUTE_OUTPUT}" | rg -qi "already exists"; then
  echo "${ROUTE_OUTPUT}"
  echo "failed to route dns for ${TUNNEL_DOMAIN}"
  exit 6
fi

PUBLIC_BASE_URL="https://${TUNNEL_DOMAIN}"
PANEL_VIEW_URL="${PUBLIC_BASE_URL}/api/v1/panel/view"

upsert_env "CLOUDFLARE_TUNNEL_NAME" "${TUNNEL_NAME}"
upsert_env "CLOUDFLARE_TUNNEL_ID" "${TUNNEL_ID}"
upsert_env "CLOUDFLARE_TUNNEL_DOMAIN" "${TUNNEL_DOMAIN}"
upsert_env "CLOUDFLARE_TUNNEL_LOCAL_URL" "${TUNNEL_LOCAL_URL}"
upsert_env "CLOUDFLARE_TUNNEL_CREDENTIALS_FILE" "${CREDENTIALS_FILE}"
upsert_env "CLOUDFLARE_TUNNEL_CONFIG_FILE" "${CF_CONFIG_FILE}"
upsert_env "CLOUDFLARE_TUNNEL_PUBLIC_BASE_URL" "${PUBLIC_BASE_URL}"
upsert_env "WEBHOOK_BASE_URL" "${PUBLIC_BASE_URL}"
upsert_env "AUTORESEARCH_PANEL_BASE_URL" "${PANEL_VIEW_URL}"
upsert_env "AUTORESEARCH_TELEGRAM_MINI_APP_URL" "${PANEL_VIEW_URL}"

echo "cloudflare named tunnel ready"
echo "tunnel_name=${TUNNEL_NAME}"
echo "tunnel_id=${TUNNEL_ID}"
echo "domain=${TUNNEL_DOMAIN}"
echo "config=${CF_CONFIG_FILE}"
echo "panel_url=${PANEL_VIEW_URL}"
echo
echo "next:"
echo "  1) bash migration/openclaw/scripts/start-api-daemon.sh"
echo "  2) bash migration/openclaw/scripts/start-cloudflared-tunnel.sh"
echo "  3) bash migration/openclaw/scripts/configure-telegram-webhook.sh"
