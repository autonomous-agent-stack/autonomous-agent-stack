#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="${REPO_ROOT}/logs/telegram-poller.log"

if [[ ! -f "${LOG_FILE}" ]]; then
  echo "no log: ${LOG_FILE}"
  exit 0
fi

tail -n 120 "${LOG_FILE}"
