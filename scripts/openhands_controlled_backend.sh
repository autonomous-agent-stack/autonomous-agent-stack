#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

RUN_ID="${OPENHANDS_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
RUN_ROOT="${OPENHANDS_RUN_ROOT:-${REPO_ROOT}/.masfactory_runtime/openhands-controlled}"
ISOLATED_WORKSPACE="${OPENHANDS_ISOLATED_WORKSPACE:-${RUN_ROOT}/${RUN_ID}/workspace}"
ARTIFACT_DIR="${OPENHANDS_ARTIFACT_DIR:-${REPO_ROOT}/logs/audit/openhands/jobs/${RUN_ID}}"
CHAIN_DRY_RUN="${OPENHANDS_CHAIN_DRY_RUN:-0}"
VALIDATE_CMD="${OPENHANDS_VALIDATE_CMD:-}"
TASK_DEFAULT="Please scan /opt/workspace/src/autoresearch/core, propose minimal edits, and return evidence for validation and promotion gate."

if [[ "$#" -gt 0 ]]; then
  TASK="$*"
else
  TASK="${OPENHANDS_TASK:-${TASK_DEFAULT}}"
fi

for cmd in rsync git; do
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "[controlled-backend] required command not found: ${cmd}" >&2
    exit 1
  fi
done

json_escape() {
  local input="$1"
  input="${input//\\/\\\\}"
  input="${input//\"/\\\"}"
  input="${input//$'\n'/\\n}"
  printf '%s' "${input}"
}

mkdir -p "${ISOLATED_WORKSPACE}" "${ARTIFACT_DIR}"

if [[ -z "${VALIDATE_CMD}" ]]; then
  VALIDATE_CMD="python3 scripts/check_prompt_hygiene.py --root src --output-dir ${ARTIFACT_DIR}/prompt_hygiene --min-repeat 3"
fi

RSYNC_EXCLUDES=(
  --exclude '.git'
  --exclude '.venv'
  --exclude 'node_modules'
  --exclude 'panel/out'
  --exclude 'dashboard/.next'
  --exclude '.pytest_cache'
  --exclude '.ruff_cache'
)

echo "[controlled-backend] run_id: ${RUN_ID}"
echo "[controlled-backend] isolated workspace: ${ISOLATED_WORKSPACE}"
echo "[controlled-backend] artifact dir: ${ARTIFACT_DIR}"

echo "[controlled-backend] preparing isolated workspace snapshot"
rsync -a --delete "${RSYNC_EXCLUDES[@]}" "${REPO_ROOT}/" "${ISOLATED_WORKSPACE}/"

echo "[controlled-backend] executing OpenHands"
set +e
OPENHANDS_WORKSPACE="${ISOLATED_WORKSPACE}" \
OPENHANDS_AUDIT_DIR="${ARTIFACT_DIR}" \
OPENHANDS_AUDIT_FILE="${ARTIFACT_DIR}/openhands_compliance.json" \
OPENHANDS_DRY_RUN="${CHAIN_DRY_RUN}" \
bash "${REPO_ROOT}/scripts/openhands_start.sh" "${TASK}"
OPENHANDS_EXIT_CODE=$?
set -e

VALIDATION_EXIT_CODE=0
if [[ -n "${VALIDATE_CMD}" ]]; then
  echo "[controlled-backend] running validation command"
  set +e
  (
    cd "${ISOLATED_WORKSPACE}"
    bash -lc "${VALIDATE_CMD}"
  )
  VALIDATION_EXIT_CODE=$?
  set -e
fi

echo "[controlled-backend] collecting promotion patch"
set +e
git --no-pager diff --no-index \
  -- \
  "${REPO_ROOT}" \
  "${ISOLATED_WORKSPACE}" \
  > "${ARTIFACT_DIR}/promotion.patch"
DIFF_EXIT_CODE=$?
set -e

if [[ ${DIFF_EXIT_CODE} -gt 1 ]]; then
  echo "[controlled-backend] failed to compute promotion patch" >&2
  exit ${DIFF_EXIT_CODE}
fi

PROMOTION_READY=false
if [[ ${OPENHANDS_EXIT_CODE} -eq 0 && ${VALIDATION_EXIT_CODE} -eq 0 ]]; then
  PROMOTION_READY=true
fi

CHAIN_STATUS="blocked"
if [[ "${PROMOTION_READY}" == "true" ]]; then
  CHAIN_STATUS="ready_for_promotion"
fi

cat > "${ARTIFACT_DIR}/chain_summary.json" <<JSON
{
  "run_id": "$(json_escape "${RUN_ID}")",
  "status": "${CHAIN_STATUS}",
  "task": "$(json_escape "${TASK}")",
  "isolated_workspace": "$(json_escape "${ISOLATED_WORKSPACE}")",
  "artifacts": {
    "compliance": "$(json_escape "${ARTIFACT_DIR}/openhands_compliance.json")",
    "promotion_patch": "$(json_escape "${ARTIFACT_DIR}/promotion.patch")"
  },
  "exit_codes": {
    "openhands": ${OPENHANDS_EXIT_CODE},
    "validation": ${VALIDATION_EXIT_CODE}
  },
  "promotion_ready": ${PROMOTION_READY}
}
JSON

echo "[controlled-backend] openhands_exit_code=${OPENHANDS_EXIT_CODE}"
echo "[controlled-backend] validation_exit_code=${VALIDATION_EXIT_CODE}"
echo "[controlled-backend] promotion_ready=${PROMOTION_READY}"
echo "[controlled-backend] summary: ${ARTIFACT_DIR}/chain_summary.json"
echo "[controlled-backend] patch: ${ARTIFACT_DIR}/promotion.patch"

if [[ ${OPENHANDS_EXIT_CODE} -ne 0 ]]; then
  exit ${OPENHANDS_EXIT_CODE}
fi

if [[ ${VALIDATION_EXIT_CODE} -ne 0 ]]; then
  exit ${VALIDATION_EXIT_CODE}
fi
