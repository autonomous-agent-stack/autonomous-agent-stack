#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

echo "[1/3] Create OpenClaw-compatible session"
SESSION_JSON="$(curl -sS -X POST "${BASE_URL}/api/v1/openclaw/sessions" \
  -H 'Content-Type: application/json' \
  -d '{"channel":"telegram","title":"migration-smoke","metadata":{"source":"migration-script"}}')"

echo "$SESSION_JSON"
SESSION_ID="$(echo "$SESSION_JSON" | sed -n 's/.*"session_id":"\([^"]*\)".*/\1/p')"
if [[ -z "${SESSION_ID}" ]]; then
  echo "failed: no session_id returned"
  exit 1
fi

echo "[2/3] Append one event"
EVENT_JSON="$(curl -sS -X POST "${BASE_URL}/api/v1/openclaw/sessions/${SESSION_ID}/events" \
  -H 'Content-Type: application/json' \
  -d '{"role":"user","content":"hello from migration smoke","metadata":{"source":"migration-script"}}')"

echo "$EVENT_JSON"

echo "[3/3] Spawn one agent"
AGENT_JSON="$(curl -sS -X POST "${BASE_URL}/api/v1/openclaw/agents" \
  -H 'Content-Type: application/json' \
  -d "{\"task_name\":\"migration-smoke-agent\",\"prompt\":\"Reply with a short health message\",\"session_id\":\"${SESSION_ID}\",\"generation_depth\":1,\"timeout_seconds\":120}")"

echo "$AGENT_JSON"
AGENT_ID="$(echo "$AGENT_JSON" | sed -n 's/.*"agent_run_id":"\([^"]*\)".*/\1/p')"
if [[ -z "${AGENT_ID}" ]]; then
  echo "failed: no agent_run_id returned"
  exit 1
fi

echo "done: session_id=${SESSION_ID} agent_run_id=${AGENT_ID}"
