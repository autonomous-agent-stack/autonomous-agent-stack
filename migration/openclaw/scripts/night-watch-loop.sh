#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "${ROOT_DIR}/../.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env.local"
LOG_DIR="${ROOT_DIR}/logs"
LOCAL_LOG="${LOG_DIR}/night-watch.log"
REPORT_MD="${OPENCLAW_WATCH_REPORT_MD:-/Users/iCloud_GZ/.openclaw/workspace/AutonomousAgentStack_NightWatch.md}"
INTERVAL_SECONDS="${NIGHT_WATCH_INTERVAL_SECONDS:-300}"

mkdir -p "${LOG_DIR}" "$(dirname "${REPORT_MD}")"
touch "${LOCAL_LOG}" "${REPORT_MD}"

if ! rg -q "^# Autonomous Agent Stack Night Watch" "${REPORT_MD}" 2>/dev/null; then
  {
    echo "# Autonomous Agent Stack Night Watch"
    echo
    echo "- started_at: $(date '+%Y-%m-%d %H:%M:%S %z')"
    echo "- project_root: ${PROJECT_ROOT}"
    echo "- interval_seconds: ${INTERVAL_SECONDS}"
    echo
  } >> "${REPORT_MD}"
fi

log() {
  local msg="$1"
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S %z')" "${msg}" | tee -a "${LOCAL_LOG}" >/dev/null
}

check_pid_file() {
  local pid_file="$1"
  if [[ ! -f "${pid_file}" ]]; then
    echo "missing"
    return
  fi
  local pid
  pid="$(cat "${pid_file}" 2>/dev/null || true)"
  if [[ -z "${pid}" ]]; then
    echo "empty"
    return
  fi
  if kill -0 "${pid}" >/dev/null 2>&1; then
    echo "running:${pid}"
  else
    echo "stale:${pid}"
  fi
}

while true; do
  if [[ -f "${ENV_FILE}" ]]; then
    set -a
    source "${ENV_FILE}" || true
    set +a
  fi

  ts="$(date '+%Y-%m-%d %H:%M:%S %z')"
  next_ts="$(date -v+${INTERVAL_SECONDS}S '+%Y-%m-%d %H:%M:%S %z' 2>/dev/null || date -r $(( $(date +%s) + INTERVAL_SECONDS )) '+%Y-%m-%d %H:%M:%S %z')"

  api_host="${AUTORESEARCH_API_HOST:-127.0.0.1}"
  api_port="${AUTORESEARCH_API_PORT:-8001}"
  api_status="down"
  if curl -fsS "http://${api_host}:${api_port}/healthz" >/dev/null 2>&1; then
    api_status="ok"
  fi

  api_pid_state="$(check_pid_file "${ROOT_DIR}/logs/api.pid")"
  poller_pid_state="$(check_pid_file "${ROOT_DIR}/logs/telegram-poller.pid")"

  actions=()

  if [[ "${api_status}" != "ok" ]]; then
    if bash "${ROOT_DIR}/scripts/start-api-daemon.sh" >/dev/null 2>&1; then
      actions+=("restart_api:ok")
      api_status="ok"
      api_pid_state="$(check_pid_file "${ROOT_DIR}/logs/api.pid")"
    else
      actions+=("restart_api:failed")
    fi
  fi

  if [[ "${poller_pid_state}" != running:* ]]; then
    if bash "${ROOT_DIR}/scripts/start-telegram-poller.sh" >/dev/null 2>&1; then
      actions+=("restart_poller:ok")
      poller_pid_state="$(check_pid_file "${ROOT_DIR}/logs/telegram-poller.pid")"
    else
      actions+=("restart_poller:failed")
    fi
  fi

  recent_poller="$(tail -n 120 "${ROOT_DIR}/logs/telegram-poller.log" 2>/dev/null || true)"
  recent_api="$(tail -n 120 "${ROOT_DIR}/logs/api.log" 2>/dev/null || true)"

  risk_notes=()
  if printf '%s' "${recent_poller}" | rg -q "HTTP Error 409|Conflict"; then
    risk_notes+=("detected_409_conflict: another consumer may be using the same Telegram bot token")
  fi
  if printf '%s' "${recent_poller}" | rg -q "HTTP Error 404"; then
    risk_notes+=("detected_404: Telegram token might be invalid")
  fi
  if printf '%s' "${recent_api}" | rg -q "ERROR|Traceback"; then
    risk_notes+=("api_log_contains_error: check migration/openclaw/logs/api.log")
  fi

  {
    echo "## ${ts}"
    echo "- api_endpoint: http://${api_host}:${api_port}/healthz"
    echo "- api_health: ${api_status}"
    echo "- api_pid: ${api_pid_state}"
    echo "- poller_pid: ${poller_pid_state}"
    if ((${#actions[@]} > 0)); then
      echo "- auto_actions: ${actions[*]}"
    else
      echo "- auto_actions: none"
    fi
    if ((${#risk_notes[@]} > 0)); then
      echo "- risks:"
      for note in "${risk_notes[@]}"; do
        echo "  - ${note}"
      done
    else
      echo "- risks: none"
    fi
    echo "- next_check: ${next_ts}"
    echo
  } >> "${REPORT_MD}"

  log "api=${api_status} api_pid=${api_pid_state} poller_pid=${poller_pid_state} actions=${actions[*]:-none}"
  sleep "${INTERVAL_SECONDS}"
done
