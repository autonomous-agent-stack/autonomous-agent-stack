#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="${REPO_ROOT}/.venv/bin/python"
SCRIPT="${REPO_ROOT}/scripts/telegram_poller.py"

for ENV_FILE in "${REPO_ROOT}/.env" "${REPO_ROOT}/.env.local" "${REPO_ROOT}/.env.linux" "${REPO_ROOT}/ai_lab.env"; do
  if [[ -f "${ENV_FILE}" ]]; then
    set -a
    source "${ENV_FILE}"
    set +a
  fi
done

if [[ ! -x "${VENV_PYTHON}" ]]; then
  echo "missing venv python: ${VENV_PYTHON}"
  exit 1
fi

if [[ -n "${AUTORESEARCH_TELEGRAM_BOT_TOKEN:-}" && -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  export TELEGRAM_BOT_TOKEN="${AUTORESEARCH_TELEGRAM_BOT_TOKEN}"
fi
if [[ -n "${TELEGRAM_BOT_TOKEN:-}" && -z "${AUTORESEARCH_TELEGRAM_BOT_TOKEN:-}" ]]; then
  export AUTORESEARCH_TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN}"
fi

API_HOST="${AUTORESEARCH_API_HOST:-127.0.0.1}"
API_PORT="${AUTORESEARCH_API_PORT:-8001}"
resolve_local_api_host() {
  local requested_host="$1"
  if [[ "${requested_host}" != "0.0.0.0" ]]; then
    echo "${requested_host}"
    return
  fi
  if command -v hostname >/dev/null 2>&1; then
    while read -r candidate; do
      if [[ "${candidate}" == 100.* || "${candidate}" == fd7a:115c:a1e0:* ]]; then
        echo "${candidate}"
        return
      fi
    done < <(hostname -I 2>/dev/null | tr ' ' '\n')
  fi
  echo "127.0.0.1"
}

PROBE_HOST="${AUTORESEARCH_LOCAL_API_HOST:-}"
if [[ -z "${PROBE_HOST}" ]]; then
  PROBE_HOST="$(resolve_local_api_host "${API_HOST}")"
fi

export AUTORESEARCH_LOCAL_API_HOST="${PROBE_HOST}"
export TELEGRAM_BRIDGE_LOCAL_WEBHOOK_URL="${TELEGRAM_BRIDGE_LOCAL_WEBHOOK_URL:-http://${PROBE_HOST}:${API_PORT}/api/v1/gateway/telegram/webhook}"

for _ in $(seq 1 30); do
  if curl -fsS "http://${PROBE_HOST}:${API_PORT}/health" >/dev/null 2>&1 || curl -fsS "http://${PROBE_HOST}:${API_PORT}/healthz" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! curl -fsS "http://${PROBE_HOST}:${API_PORT}/health" >/dev/null 2>&1 && ! curl -fsS "http://${PROBE_HOST}:${API_PORT}/healthz" >/dev/null 2>&1; then
  echo "api not healthy on http://${PROBE_HOST}:${API_PORT}/health or /healthz"
  exit 1
fi

cd "${REPO_ROOT}"
exec "${VENV_PYTHON}" "${SCRIPT}"
