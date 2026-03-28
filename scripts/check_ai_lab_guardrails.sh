#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORKSPACE_DIR="${WORKSPACE_DIR:-/Users/ai_lab/workspace}"
PLATFORM="${AI_LAB_GUARDRAIL_PLATFORM:-$(uname -s)}"
DOCKER_CONTEXT_NAME="${AI_LAB_GUARDRAIL_DOCKER_CONTEXT:-${DOCKER_CONTEXT:-}}"

resolve_path() {
  python3 - "$1" <<'PY'
from pathlib import Path
import sys

print(Path(sys.argv[1]).resolve(strict=False))
PY
}

if [[ -z "${DOCKER_CONTEXT_NAME}" ]]; then
  DOCKER_CONTEXT_NAME="$(docker context show 2>/dev/null || true)"
fi

ABS_WORKSPACE_DIR="$(resolve_path "${WORKSPACE_DIR}")"
ABS_REPO_ROOT="$(resolve_path "${REPO_ROOT}")"

echo "[check] workspace exists"
test -d "${ABS_WORKSPACE_DIR}"

echo "[check] workspace writable"
test -w "${ABS_WORKSPACE_DIR}"

echo "[check] workspace path is not sensitive"
case "${ABS_WORKSPACE_DIR}" in
  /|/etc|/etc/*|*/.ssh|*/.ssh/*)
    echo "Sensitive workspace path rejected: ${ABS_WORKSPACE_DIR}" >&2
    exit 1
    ;;
esac

echo "[check] workspace is outside the main repository"
case "${ABS_WORKSPACE_DIR}" in
  "${ABS_REPO_ROOT}"|"${ABS_REPO_ROOT}"/*)
    echo "Workspace must not point at the main repository: ${ABS_WORKSPACE_DIR}" >&2
    exit 1
    ;;
esac

if [[ "${PLATFORM}" == "Darwin" ]] || [[ "${DOCKER_CONTEXT_NAME}" == "colima" ]]; then
  echo "[check] host mount scan skipped for ${PLATFORM}/${DOCKER_CONTEXT_NAME:-default}"
else
  echo "[check] host mount table has no explicit SSH bind mounts"
  if command -v mount >/dev/null 2>&1 && mount | grep -E '[[:space:]]on[[:space:]]+(.*/\.ssh)([[:space:]]|$)' >/dev/null 2>&1; then
    echo "Sensitive mount detected." >&2
    exit 1
  fi
fi

echo "[check] OK"
