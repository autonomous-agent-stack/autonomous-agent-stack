#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SESSION_NAME="${NIGHT_WATCH_SESSION_NAME:-aas_night_watch}"
LOOP_SCRIPT="${ROOT_DIR}/scripts/night-watch-loop.sh"
REPORT_MD="${OPENCLAW_WATCH_REPORT_MD:-/Users/iCloud_GZ/.openclaw/workspace/AutonomousAgentStack_NightWatch.md}"
LOCAL_LOG="/Volumes/PS1008/Github/autonomous-agent-stack/migration/openclaw/logs/night-watch.log"

screen_match="no"
if screen -ls 2>/dev/null | rg -q "\.${SESSION_NAME}"; then
  screen_match="yes"
fi

loop_pids="$(pgrep -f "${LOOP_SCRIPT}" | tr '\n' ' ' | xargs || true)"

if [[ "${screen_match}" == "yes" || -n "${loop_pids}" ]]; then
  echo "night watch running"
  echo "screen_session_match: ${screen_match}"
  echo "loop_pids: ${loop_pids:-none}"
else
  echo "night watch NOT running: ${SESSION_NAME}"
fi

echo "report: ${REPORT_MD}"
if [[ -f "${REPORT_MD}" ]]; then
  tail -n 20 "${REPORT_MD}"
else
  echo "report file not found"
fi

echo
echo "local log: ${LOCAL_LOG}"
if [[ -f "${LOCAL_LOG}" ]]; then
  tail -n 20 "${LOCAL_LOG}"
else
  echo "local log not found"
fi
