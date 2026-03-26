#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="${ROOT_DIR}/logs/cloudflared.log"

if [[ ! -f "${LOG_FILE}" ]]; then
  echo "no log file: ${LOG_FILE}"
  exit 0
fi

tail -n 120 "${LOG_FILE}"
