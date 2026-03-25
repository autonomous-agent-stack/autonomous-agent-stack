#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="${ROOT_DIR}/logs/telegram-poller.log"

if [[ ! -f "${LOG_FILE}" ]]; then
  echo "no log: ${LOG_FILE}"
  exit 0
fi

tail -n 120 "${LOG_FILE}"
