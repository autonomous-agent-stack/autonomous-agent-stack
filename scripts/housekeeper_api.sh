#!/usr/bin/env bash
set -euo pipefail

API_BASE="${AUTORESEARCH_HOUSEKEEPER_API_BASE:-http://127.0.0.1:8000}"
ACTION="${1:-}"

if [[ -z "${ACTION}" ]]; then
  echo "usage: $0 <mode-day|mode-night|night-tick|morning-summary|clear-override|ack-breaker>" >&2
  exit 2
fi

post_json() {
  local path="$1"
  local payload="$2"
  curl -fsS \
    -H "content-type: application/json" \
    -X POST \
    --data "${payload}" \
    "${API_BASE}${path}"
}

case "${ACTION}" in
  mode-day)
    post_json \
      "/api/v1/housekeeper/mode" \
      '{"action":"apply_schedule","target_mode":"day_safe","changed_by":"systemd","reason":"schedule","metadata":{"source":"systemd_timer"}}'
    ;;
  mode-night)
    post_json \
      "/api/v1/housekeeper/mode" \
      '{"action":"apply_schedule","target_mode":"night_readonly_explore","changed_by":"systemd","reason":"schedule","metadata":{"source":"systemd_timer"}}'
    ;;
  night-tick)
    post_json "/api/v1/housekeeper/night-explore/tick" '{}'
    ;;
  morning-summary)
    post_json "/api/v1/housekeeper/summaries/morning" '{}'
    ;;
  clear-override)
    post_json \
      "/api/v1/housekeeper/mode" \
      '{"action":"clear_manual_override","changed_by":"systemd","reason":"manual_api","metadata":{"source":"systemd_timer"}}'
    ;;
  ack-breaker)
    post_json \
      "/api/v1/housekeeper/mode" \
      '{"action":"ack_circuit_breaker","changed_by":"systemd","reason":"recovered_from_circuit_breaker","metadata":{"source":"systemd_timer"}}'
    ;;
  *)
    echo "unsupported action: ${ACTION}" >&2
    exit 2
    ;;
esac
