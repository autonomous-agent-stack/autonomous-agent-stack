#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="${REPO_ROOT}/.venv/bin/python"

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

resolve_bind_host() {
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

REQUESTED_HOST="${HOST:-${AUTORESEARCH_API_HOST:-127.0.0.1}}"
HOST="$(resolve_bind_host "${REQUESTED_HOST}")"
PORT="${PORT:-${AUTORESEARCH_API_PORT:-8001}}"

export AUTORESEARCH_API_HOST="${HOST}"
export AUTORESEARCH_API_PORT="${AUTORESEARCH_API_PORT:-${PORT}}"
export AUTORESEARCH_LOCAL_API_HOST="${HOST}"
export PYTHONPATH="${REPO_ROOT}/src:${PYTHONPATH:-}"

cd "${REPO_ROOT}"
exec "${VENV_PYTHON}" -m uvicorn autoresearch.api.main:app \
  --host "${HOST}" \
  --port "${PORT}"
