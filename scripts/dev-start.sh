#!/usr/bin/env bash
# Friendly local startup wrapper

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-${AUTORESEARCH_API_PORT:-8001}}"

echo "==> Autonomous Agent Stack local startup"
echo "    root: ${PROJECT_ROOT}"
echo "    host: ${HOST}"
echo "    port: ${PORT}"

if [[ ! -x "${VENV_PYTHON}" ]]; then
  echo
  echo "[FAIL] Missing virtualenv python: ${VENV_PYTHON}"
  echo "       Run: make setup"
  exit 1
fi

echo
echo "==> Running doctor checks..."
"${VENV_PYTHON}" "${PROJECT_ROOT}/scripts/doctor.py" --port "${PORT}"

if command -v lsof >/dev/null 2>&1; then
  if lsof -i :"${PORT}" >/dev/null 2>&1; then
    echo
    echo "[WARN] Port ${PORT} is already in use."
    echo "       Try: PORT=8010 make start"
    exit 1
  fi
fi

export PYTHONPATH="${PROJECT_ROOT}/src:${PYTHONPATH:-}"

echo
echo "==> Starting API service..."
echo "    Docs:   http://${HOST}:${PORT}/docs"
echo "    Health: http://${HOST}:${PORT}/health"
echo "    Panel:  http://${HOST}:${PORT}/panel"
echo

exec "${VENV_PYTHON}" -m uvicorn autoresearch.api.main:app \
  --host "${HOST}" \
  --port "${PORT}" \
  --reload
