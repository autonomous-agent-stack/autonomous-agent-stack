#!/usr/bin/env bash
set -euo pipefail

SESSION_NAME="${NIGHT_WATCH_SESSION_NAME:-aas_night_watch}"

if screen -ls | rg -q "\.${SESSION_NAME}[[:space:]]"; then
  screen -S "${SESSION_NAME}" -X quit || true
  echo "night watch stopped: ${SESSION_NAME}"
else
  echo "night watch not running: ${SESSION_NAME}"
fi
