#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "${ROOT_DIR}/../.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/verify-$(date +%Y%m%d-%H%M%S).log"

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

{
  echo "# Migration verify"
  echo "time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "project_root: ${PROJECT_ROOT}"
  echo "base_url: ${BASE_URL}"

  echo
  echo "## preflight"
  command -v claude >/dev/null && echo "- claude: ok" || echo "- claude: missing"
  command -v docker >/dev/null && echo "- docker: ok" || echo "- docker: missing"

  echo
  echo "## api health"
  curl -fsS "${BASE_URL}/healthz" && echo

  echo
  echo "## openclaw compat smoke"
  bash "${ROOT_DIR}/requests/openclaw-compat-smoke.sh"
} | tee "${LOG_FILE}"

echo
echo "verify log written: ${LOG_FILE}"
