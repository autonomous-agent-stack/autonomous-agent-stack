#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/discover-$(date +%Y%m%d-%H%M%S).log"

OPENCLAW_HOME="${OPENCLAW_HOME:-/Users/iCloud_GZ/.openclaw}"
OPENCLAW_MEMORY_REPO="${OPENCLAW_MEMORY_REPO:-/Volumes/PS1008/Github/openclaw-memory}"
OPENCLAW_REPO="${OPENCLAW_REPO:-/Volumes/PS1008/Github/openclaw}"

{
  echo "# OpenClaw data discovery"
  echo "time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "openclaw_home: ${OPENCLAW_HOME}"
  echo "openclaw_memory_repo: ${OPENCLAW_MEMORY_REPO}"
  echo "openclaw_repo: ${OPENCLAW_REPO}"
  echo

  echo "## candidates: sqlite db files"
  for p in "${OPENCLAW_HOME}" "${OPENCLAW_MEMORY_REPO}" "${OPENCLAW_REPO}"; do
    if [[ -d "${p}" ]]; then
      find "${p}" -type f \( -name "*.sqlite" -o -name "*.sqlite3" -o -name "*.db" \) 2>/dev/null | sed "s/^/  - /"
    else
      echo "  - missing dir: ${p}"
    fi
  done
  echo

  echo "## candidates: openclaw config json"
  for p in "${OPENCLAW_HOME}" "${OPENCLAW_MEMORY_REPO}" "${OPENCLAW_REPO}"; do
    if [[ -d "${p}" ]]; then
      find "${p}" -maxdepth 3 -type f \( -name "openclaw.json" -o -name "*.state.json" -o -name "runs.json" \) 2>/dev/null | sed "s/^/  - /"
    fi
  done
} | tee "${LOG_FILE}"

echo
echo "discovery log written: ${LOG_FILE}"
