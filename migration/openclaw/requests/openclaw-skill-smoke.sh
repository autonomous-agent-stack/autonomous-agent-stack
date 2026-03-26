#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8001}"
SKILL_NAME="${SKILL_NAME:-weather}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
  if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "failed: python runtime not found (tried PYTHON_BIN=${PYTHON_BIN} and python)"
    exit 1
  fi
fi

echo "[1/6] Ensure skill exists: ${SKILL_NAME}"
SKILL_JSON="$(curl -sS "${BASE_URL}/api/v1/openclaw/skills/${SKILL_NAME}")"
if [[ "${SKILL_JSON}" == *'"detail":"OpenClaw skill not found"'* ]]; then
  echo "failed: skill not found -> ${SKILL_NAME}"
  echo "hint: GET ${BASE_URL}/api/v1/openclaw/skills"
  exit 1
fi
echo "${SKILL_JSON}"

echo "[2/6] Create OpenClaw-compatible session"
SESSION_JSON="$(curl -sS -X POST "${BASE_URL}/api/v1/openclaw/sessions" \
  -H 'Content-Type: application/json' \
  -d '{"channel":"api","title":"migration-skill-smoke","metadata":{"source":"migration-skill-script"}}')"
echo "${SESSION_JSON}"
SESSION_ID="$(echo "${SESSION_JSON}" | sed -n 's/.*"session_id":"\([^"]*\)".*/\1/p')"
if [[ -z "${SESSION_ID}" ]]; then
  echo "failed: no session_id returned"
  exit 1
fi

echo "[3/6] Load skill into session"
LOAD_JSON="$(curl -sS -X POST "${BASE_URL}/api/v1/openclaw/sessions/${SESSION_ID}/skills" \
  -H 'Content-Type: application/json' \
  -d "{\"skill_names\":[\"${SKILL_NAME}\"],\"merge\":true}")"
echo "${LOAD_JSON}"
if [[ "${LOAD_JSON}" == *'"detail":"OpenClaw skills not found'* ]]; then
  echo "failed: unable to load skill ${SKILL_NAME}"
  exit 1
fi

echo "[4/6] Spawn one agent with deterministic command override"
AGENT_JSON="$(curl -sS -X POST "${BASE_URL}/api/v1/openclaw/agents" \
  -H 'Content-Type: application/json' \
  -d "{\"task_name\":\"migration-skill-smoke-agent\",\"prompt\":\"reply with a concise health message\",\"session_id\":\"${SESSION_ID}\",\"generation_depth\":1,\"timeout_seconds\":30,\"command_override\":[\"${PYTHON_BIN}\",\"-c\",\"import sys; print(sys.argv[-1])\"],\"append_prompt\":true}")"
echo "${AGENT_JSON}"
AGENT_ID="$(echo "${AGENT_JSON}" | sed -n 's/.*"agent_run_id":"\([^"]*\)".*/\1/p')"
if [[ -z "${AGENT_ID}" ]]; then
  echo "failed: no agent_run_id returned"
  exit 1
fi

echo "[5/6] Poll agent status"
FINAL_JSON=""
for _ in $(seq 1 60); do
  RUN_JSON="$(curl -sS "${BASE_URL}/api/v1/openclaw/agents/${AGENT_ID}")"
  STATUS="$(echo "${RUN_JSON}" | sed -n 's/.*"status":"\([^"]*\)".*/\1/p')"
  if [[ "${STATUS}" == "completed" || "${STATUS}" == "failed" || "${STATUS}" == "interrupted" ]]; then
    FINAL_JSON="${RUN_JSON}"
    break
  fi
  sleep 0.2
done

if [[ -z "${FINAL_JSON}" ]]; then
  echo "failed: agent did not reach terminal status"
  exit 1
fi
echo "${FINAL_JSON}"

FINAL_STATUS="$(echo "${FINAL_JSON}" | sed -n 's/.*"status":"\([^"]*\)".*/\1/p')"
if [[ "${FINAL_STATUS}" != "completed" ]]; then
  echo "failed: agent status is ${FINAL_STATUS}"
  exit 1
fi

echo "[6/6] Validate skill prompt injection markers"
if [[ "${FINAL_JSON}" != *"<available_skills>"* || "${FINAL_JSON}" != *"${SKILL_NAME}"* ]]; then
  echo "failed: skill injection marker not found in stdout_preview"
  exit 1
fi

echo "done: session_id=${SESSION_ID} agent_run_id=${AGENT_ID} skill=${SKILL_NAME}"
