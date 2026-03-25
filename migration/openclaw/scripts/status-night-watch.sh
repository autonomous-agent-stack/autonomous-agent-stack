#!/usr/bin/env bash
set -euo pipefail

SESSION_NAME="${NIGHT_WATCH_SESSION_NAME:-aas_night_watch}"
REPORT_MD="${OPENCLAW_WATCH_REPORT_MD:-/Users/iCloud_GZ/.openclaw/workspace/AutonomousAgentStack_NightWatch.md}"
LOCAL_LOG="/Volumes/PS1008/Github/autonomous-agent-stack/migration/openclaw/logs/night-watch.log"

if screen -ls | rg -q "\.${SESSION_NAME}[[:space:]]"; then
  echo "night watch running: ${SESSION_NAME}"
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
