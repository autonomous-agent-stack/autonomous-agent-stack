#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "${ROOT_DIR}/../.." && pwd)"
SESSION_NAME="${NIGHT_WATCH_SESSION_NAME:-aas_night_watch}"
LOOP_SCRIPT="${ROOT_DIR}/scripts/night-watch-loop.sh"
REPORT_MD="${OPENCLAW_WATCH_REPORT_MD:-/Users/iCloud_GZ/.openclaw/workspace/AutonomousAgentStack_NightWatch.md}"

existing_pids="$(pgrep -f "${LOOP_SCRIPT}" | tr '\n' ' ' | xargs || true)"
if [[ -n "${existing_pids}" ]]; then
  echo "night watch already running (pids=${existing_pids})"
  echo "report: ${REPORT_MD}"
  exit 0
fi

if screen -ls 2>/dev/null | rg -q "\.${SESSION_NAME}"; then
  echo "night watch already running in screen session: ${SESSION_NAME}"
  echo "report: ${REPORT_MD}"
  exit 0
fi

cd "${PROJECT_ROOT}"
screen -dmS "${SESSION_NAME}" bash -lc "cd '${PROJECT_ROOT}' && bash '${LOOP_SCRIPT}'"

echo "night watch started"
echo "screen session: ${SESSION_NAME}"
echo "report: ${REPORT_MD}"
