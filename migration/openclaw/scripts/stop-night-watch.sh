#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SESSION_NAME="${NIGHT_WATCH_SESSION_NAME:-aas_night_watch}"
LOOP_SCRIPT="${ROOT_DIR}/scripts/night-watch-loop.sh"

found="no"

session_ids="$(screen -ls 2>/dev/null | awk "/\\.${SESSION_NAME}/ {print \$1}" || true)"
if [[ -n "${session_ids}" ]]; then
  while IFS= read -r sid; do
    [[ -z "${sid}" ]] && continue
    screen -S "${sid}" -X quit || true
    found="yes"
  done <<< "${session_ids}"
fi

loop_pids="$(pgrep -f "${LOOP_SCRIPT}" || true)"
if [[ -n "${loop_pids}" ]]; then
  while IFS= read -r pid; do
    [[ -z "${pid}" ]] && continue
    kill "${pid}" >/dev/null 2>&1 || true
    found="yes"
  done <<< "${loop_pids}"
fi

if [[ "${found}" == "yes" ]]; then
  echo "night watch stopped"
else
  echo "night watch not running: ${SESSION_NAME}"
fi
