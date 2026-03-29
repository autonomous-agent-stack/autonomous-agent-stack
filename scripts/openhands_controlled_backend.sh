#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

RUN_ID="${OPENHANDS_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
RUN_ROOT="${OPENHANDS_RUN_ROOT:-${REPO_ROOT}/.masfactory_runtime/openhands-controlled}"
BASELINE_DIR="${OPENHANDS_BASELINE_DIR:-${RUN_ROOT}/${RUN_ID}/baseline}"
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

mkdir -p "${BASELINE_DIR}" "${ISOLATED_WORKSPACE}" "${ARTIFACT_DIR}"

if [[ -z "${VALIDATE_CMD}" ]]; then
  VALIDATE_CMD="python3 scripts/check_prompt_hygiene.py --root src --output-dir ${ARTIFACT_DIR}/prompt_hygiene --min-repeat 3"
fi

RSYNC_EXCLUDES=(
  --exclude '.git'
  --exclude '.venv'
  --exclude '.masfactory_runtime'
  --exclude 'logs'
  --exclude 'node_modules'
  --exclude 'panel/out'
  --exclude 'dashboard/.next'
  --exclude '.pytest_cache'
  --exclude '.ruff_cache'
)

echo "[controlled-backend] run_id: ${RUN_ID}"
echo "[controlled-backend] baseline dir: ${BASELINE_DIR}"
echo "[controlled-backend] isolated workspace: ${ISOLATED_WORKSPACE}"
echo "[controlled-backend] artifact dir: ${ARTIFACT_DIR}"

echo "[controlled-backend] preparing filtered baseline snapshot"
rsync -a --delete "${RSYNC_EXCLUDES[@]}" "${REPO_ROOT}/" "${BASELINE_DIR}/"

echo "[controlled-backend] preparing isolated workspace snapshot"
rsync -a --delete "${BASELINE_DIR}/" "${ISOLATED_WORKSPACE}/"

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
RAW_PATCH_PATH="${ARTIFACT_DIR}/promotion.raw.patch"
git --no-pager diff --no-index \
  -- \
  "${BASELINE_DIR}" \
  "${ISOLATED_WORKSPACE}" \
  > "${RAW_PATCH_PATH}"
DIFF_EXIT_CODE=$?
set -e

if [[ ${DIFF_EXIT_CODE} -gt 1 ]]; then
  echo "[controlled-backend] failed to compute promotion patch" >&2
  exit ${DIFF_EXIT_CODE}
fi

python3 - "${RAW_PATCH_PATH}" "${BASELINE_DIR}" "${ISOLATED_WORKSPACE}" "${ARTIFACT_DIR}/promotion.patch" <<'PY'
from pathlib import Path
import re
import sys

raw_patch_path = Path(sys.argv[1])
baseline_dir = str(Path(sys.argv[2]).resolve())
workspace_dir = str(Path(sys.argv[3]).resolve())
target_path = Path(sys.argv[4])

text = raw_patch_path.read_text(encoding="utf-8") if raw_patch_path.exists() else ""


def normalize_path(token: str, side: str) -> str:
    if token == "/dev/null":
        return token

    candidate = token
    if candidate.startswith("a/") or candidate.startswith("b/"):
        candidate = candidate[2:]

    candidates = {
        candidate,
        candidate.lstrip("/"),
        "/" + candidate.lstrip("/"),
    }

    for prefix in (baseline_dir, workspace_dir):
        prefixes = {
            prefix.rstrip("/"),
            prefix.rstrip("/").lstrip("/"),
            "/" + prefix.rstrip("/").lstrip("/"),
        }
        for probe in candidates:
            for normalized_prefix in prefixes:
                prefix_with_sep = normalized_prefix.rstrip("/") + "/"
                if probe == normalized_prefix or probe.startswith(prefix_with_sep):
                    rel = probe[len(normalized_prefix) :].lstrip("/")
                    return f"{side}/{rel}" if rel else side

    if token.startswith(f"{side}/"):
        return token
    return f"{side}/{candidate.lstrip('/')}"


normalized_lines: list[str] = []
for line in text.splitlines():
    if line.startswith("diff --git "):
        match = re.match(r"^diff --git a/(.+) b/(.+)$", line)
        if match:
            left = normalize_path(match.group(1), "a")
            right = normalize_path(match.group(2), "b")
            normalized_lines.append(f"diff --git {left} {right}")
            continue
    if line.startswith("--- "):
        normalized_lines.append(f"--- {normalize_path(line[4:], 'a')}")
        continue
    if line.startswith("+++ "):
        normalized_lines.append(f"+++ {normalize_path(line[4:], 'b')}")
        continue
    normalized_lines.append(line)

normalized = "\n".join(normalized_lines)
if normalized:
    normalized += "\n"
target_path.write_text(normalized, encoding="utf-8")
PY

rm -f "${RAW_PATCH_PATH}"

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
