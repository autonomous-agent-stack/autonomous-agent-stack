#!/usr/bin/env bash
set -euo pipefail

require_env() {
  local key="$1"
  if [[ -z "${!key:-}" ]]; then
    echo "[aep][openhands] missing env: ${key}" >&2
    exit 40
  fi
}

require_env "AEP_RUN_DIR"
require_env "AEP_WORKSPACE"
require_env "AEP_ARTIFACT_DIR"
require_env "AEP_JOB_SPEC"
require_env "AEP_RESULT_PATH"
require_env "AEP_BASELINE"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PY_BIN="${PYTHON_BIN:-python3}"
ATTEMPT="${AEP_ATTEMPT:-1}"

if [[ ! -f "${AEP_JOB_SPEC}" ]]; then
  echo "[aep][openhands] missing job spec: ${AEP_JOB_SPEC}" >&2
  exit 40
fi

read_job_field() {
  local field="$1"
  "${PY_BIN}" - "${AEP_JOB_SPEC}" "${field}" <<'PY'
import json
import sys
from pathlib import Path

job_path = Path(sys.argv[1])
field = sys.argv[2]

payload = json.loads(job_path.read_text(encoding="utf-8"))
value = payload
for token in field.split("."):
    if isinstance(value, dict):
        value = value.get(token)
    else:
        value = None
        break
if value is None:
    print("")
elif isinstance(value, str):
    print(value)
else:
    print(json.dumps(value, ensure_ascii=False))
PY
}

RUN_ID="$(read_job_field run_id)"
AGENT_ID="$(read_job_field agent_id)"
TASK="$(read_job_field task)"
MAX_CHANGED_FILES_RAW="$(read_job_field policy.max_changed_files)"

if [[ -z "${RUN_ID}" || -z "${AGENT_ID}" || -z "${TASK}" ]]; then
  echo "[aep][openhands] invalid job spec fields" >&2
  exit 40
fi

MAX_FILES_PER_STEP=3
if [[ "${MAX_CHANGED_FILES_RAW}" =~ ^[0-9]+$ ]]; then
  if (( MAX_CHANGED_FILES_RAW < 3 )); then
    MAX_FILES_PER_STEP="${MAX_CHANGED_FILES_RAW}"
  fi
  if (( MAX_FILES_PER_STEP < 1 )); then
    MAX_FILES_PER_STEP=1
  fi
fi

PROMPT="${TASK}

Execution contract:
- Single task only.
- Do not commit, push, or edit git settings.
- Only edit files under /opt/workspace.
- Return concise summary and changed files."

mkdir -p "${AEP_ARTIFACT_DIR}"

set +e
OPENHANDS_WORKSPACE="${AEP_WORKSPACE}" \
OPENHANDS_AUDIT_DIR="${AEP_ARTIFACT_DIR}" \
OPENHANDS_AUDIT_FILE="${AEP_ARTIFACT_DIR}/compliance.json" \
OPENHANDS_MAX_FILES_PER_STEP="${MAX_FILES_PER_STEP}" \
bash "${REPO_ROOT}/scripts/openhands_start.sh" "${PROMPT}"
OPENHANDS_EXIT_CODE=$?
set -e

"${PY_BIN}" - "${AEP_BASELINE}" "${AEP_WORKSPACE}" "${AEP_ARTIFACT_DIR}" "${AEP_RESULT_PATH}" "${RUN_ID}" "${AGENT_ID}" "${ATTEMPT}" "${OPENHANDS_EXIT_CODE}" <<'PY'
import json
import sys
from pathlib import Path

baseline = Path(sys.argv[1])
workspace = Path(sys.argv[2])
artifact_dir = Path(sys.argv[3])
result_path = Path(sys.argv[4])
run_id = sys.argv[5]
agent_id = sys.argv[6]
attempt = int(sys.argv[7])
exit_code = int(sys.argv[8])


def collect_files(root: Path) -> set[str]:
    if not root.exists():
        return set()
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


base_files = collect_files(baseline)
ws_files = collect_files(workspace)
changed = []
for rel in sorted(base_files | ws_files):
    base_path = baseline / rel
    ws_path = workspace / rel
    if not base_path.exists() or not ws_path.exists():
        changed.append(rel)
        continue
    if base_path.read_bytes() != ws_path.read_bytes():
        changed.append(rel)

artifacts = []
compliance = artifact_dir / "compliance.json"
if compliance.exists():
    artifacts.append(
        {
            "name": "compliance",
            "kind": "compliance",
            "uri": str(compliance),
            "sha256": None,
        }
    )

status = "succeeded" if exit_code == 0 else "failed"
recommended = "promote" if exit_code == 0 else "fallback"
summary = "OpenHands adapter finished" if exit_code == 0 else f"OpenHands adapter exited with {exit_code}"

payload = {
    "protocol_version": "aep/v0",
    "run_id": run_id,
    "agent_id": agent_id,
    "attempt": attempt,
    "status": status,
    "summary": summary,
    "changed_paths": changed,
    "output_artifacts": artifacts,
    "metrics": {
        "duration_ms": 0,
        "steps": 0,
        "commands": 0,
        "prompt_tokens": None,
        "completion_tokens": None,
    },
    "recommended_action": recommended,
    "error": None if exit_code == 0 else summary,
}

result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
PY

if [[ ${OPENHANDS_EXIT_CODE} -eq 0 ]]; then
  exit 0
fi
exit 20
