#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="${REPO_ROOT}/logs/telegram-poller.pid"
LOG_FILE="${REPO_ROOT}/logs/telegram-poller.log"
RUNNER="${REPO_ROOT}/scripts/run_telegram_poller.sh"
SCRIPT_PATH="${REPO_ROOT}/scripts/telegram_poller.py"
SYSTEMD_SERVICE="autonomous-agent-stack-telegram-poller.service"

mkdir -p "${REPO_ROOT}/logs"

stop_pid() {
  local pid="$1"
  if ! kill -0 "${pid}" >/dev/null 2>&1; then
    return 0
  fi
  kill "${pid}" >/dev/null 2>&1 || true
  sleep 1
  if kill -0 "${pid}" >/dev/null 2>&1; then
    kill -9 "${pid}" >/dev/null 2>&1 || true
  fi
}

find_local_poller_pids() {
  if command -v pgrep >/dev/null 2>&1; then
    pgrep -u "$(id -u)" -f "${SCRIPT_PATH}|${RUNNER}" || true
    return
  fi

  ps -eo pid=,args= | while read -r pid args; do
    if [[ "${args}" == *"${SCRIPT_PATH}"* || "${args}" == *"${RUNNER}"* ]]; then
      echo "${pid}"
    fi
  done
}

systemd_service_pid() {
  if ! command -v systemctl >/dev/null 2>&1; then
    return 0
  fi
  if ! systemctl is-active --quiet "${SYSTEMD_SERVICE}"; then
    return 0
  fi
  systemctl show -p MainPID --value "${SYSTEMD_SERVICE}" 2>/dev/null || true
}

declare -a EXISTING_PIDS=()
while read -r pid; do
  if [[ -n "${pid}" ]]; then
    EXISTING_PIDS+=("${pid}")
  fi
done < <(find_local_poller_pids)

if [[ -f "${PID_FILE}" ]]; then
  PID="$(cat "${PID_FILE}")"
  if [[ -n "${PID}" ]]; then
    EXISTING_PIDS+=("${PID}")
  fi
fi

if (( ${#EXISTING_PIDS[@]} > 0 )); then
  mapfile -t UNIQUE_PIDS < <(printf "%s\n" "${EXISTING_PIDS[@]}" | sort -u)
  SYSTEMD_PID="$(systemd_service_pid)"
  STOPPED_ANY=0
  for pid in "${UNIQUE_PIDS[@]}"; do
    if [[ -n "${SYSTEMD_PID}" && "${SYSTEMD_PID}" != "0" && "${pid}" == "${SYSTEMD_PID}" ]]; then
      continue
    fi
    if [[ "${STOPPED_ANY}" == "0" ]]; then
      echo "stopping existing local telegram poller(s): ${UNIQUE_PIDS[*]}"
      STOPPED_ANY=1
    fi
    stop_pid "${pid}"
  done
fi

SYSTEMD_PID="$(systemd_service_pid)"
if [[ -n "${SYSTEMD_PID}" && "${SYSTEMD_PID}" != "0" ]]; then
  rm -f "${PID_FILE}"
  echo "telegram poller already managed by systemd (${SYSTEMD_SERVICE}, pid=${SYSTEMD_PID})"
  exit 0
fi

rm -f "${PID_FILE}"

if [[ ! -x "${RUNNER}" ]]; then
  echo "missing poller runner: ${RUNNER}"
  exit 1
fi

cd "${REPO_ROOT}"
if command -v setsid >/dev/null 2>&1; then
  setsid "${RUNNER}" </dev/null >> "${LOG_FILE}" 2>&1 &
else
  nohup "${RUNNER}" </dev/null >> "${LOG_FILE}" 2>&1 &
fi
PID=$!
echo "${PID}" > "${PID_FILE}"

sleep 2
if kill -0 "${PID}" >/dev/null 2>&1; then
  echo "telegram poller started (pid=${PID})"
  exit 0
fi

echo "telegram poller failed to start, check: ${LOG_FILE}"
exit 1
