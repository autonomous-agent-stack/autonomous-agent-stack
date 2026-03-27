#!/usr/bin/env bash
# codex_adapter.sh - Codex CLI Driver for AEP v0
# 
# This adapter wraps OpenAI Codex CLI to conform to the Agent Execution Protocol.
# It provides a lightweight, fast alternative to OpenHands for simple coding tasks.
#
# Usage:
#   Environment variables (injected by runner.py):
#     - AEP_RUN_DIR: Run directory (.masfactory_runtime/runs/<run_id>/)
#     - AEP_WORKSPACE: Isolated workspace directory
#     - AEP_ARTIFACT_DIR: Directory for output artifacts
#     - AEP_JOB_SPEC: Path to job.json
#     - AEP_RESULT_PATH: Path to write driver_result.json
#     - AEP_BASELINE: Baseline directory for diff computation
#     - AEP_ATTEMPT: Current attempt number (default: 1)
#
# Exit codes:
#   0  - Success
#   20 - Adapter execution failed
#   40 - Missing required environment variable or invalid job spec
#   42 - Codex CLI not found

set -euo pipefail

# ============================================================================
# Environment Validation
# ============================================================================

require_env() {
  local key="$1"
  if [[ -z "${!key:-}" ]]; then
    echo "[aep][codex] missing env: ${key}" >&2
    exit 40
  fi
}

require_env "AEP_RUN_DIR"
require_env "AEP_WORKSPACE"
require_env "AEP_ARTIFACT_DIR"
require_env "AEP_JOB_SPEC"
require_env "AEP_RESULT_PATH"
require_env "AEP_BASELINE"

# ============================================================================
# Configuration
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PY_BIN="${PYTHON_BIN:-python3}"
ATTEMPT="${AEP_ATTEMPT:-1}"

# Codex-specific configuration
CODEX_MODEL="${CODEX_MODEL:-gpt-4o-mini}"
CODEX_TIMEOUT="${CODEX_TIMEOUT:-300}"  # 5 minutes default
CODEX_APPROVAL_MODE="${CODEX_APPROVAL_MODE:-full-auto}"  # suggest, auto-edit, full-auto

# ============================================================================
# Validate Prerequisites
# ============================================================================

if [[ ! -f "${AEP_JOB_SPEC}" ]]; then
  echo "[aep][codex] missing job spec: ${AEP_JOB_SPEC}" >&2
  exit 40
fi

# Check if codex CLI is available
if ! command -v codex &> /dev/null; then
  echo "[aep][codex] codex CLI not found in PATH" >&2
  echo "[aep][codex] install with: npm install -g @openai/codex" >&2
  exit 42
fi

# ============================================================================
# Job Spec Parser (reuse from openhands_adapter.sh)
# ============================================================================

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

# ============================================================================
# Extract Job Parameters
# ============================================================================

RUN_ID="$(read_job_field run_id)"
AGENT_ID="$(read_job_field agent_id)"
TASK="$(read_job_field task)"
MAX_CHANGED_FILES_RAW="$(read_job_field policy.max_changed_files)"
TIMEOUT_SEC_RAW="$(read_job_field policy.timeout_sec)"

if [[ -z "${RUN_ID}" || -z "${AGENT_ID}" || -z "${TASK}" ]]; then
  echo "[aep][codex] invalid job spec fields" >&2
  exit 40
fi

# Override timeout if specified in policy
if [[ "${TIMEOUT_SEC_RAW}" =~ ^[0-9]+$ ]]; then
  CODEX_TIMEOUT="${TIMEOUT_SEC_RAW}"
fi

# ============================================================================
# Build Codex Prompt
# ============================================================================

# Construct optimized prompt for Codex
PROMPT="${TASK}

Execution contract:
- Single task only, no follow-up questions.
- Do not commit, push, or edit git settings.
- Only edit files in the current workspace.
- Return concise summary of changes."

# ============================================================================
# Execute Codex CLI
# ============================================================================

mkdir -p "${AEP_ARTIFACT_DIR}"

echo "[aep][codex] starting run_id=${RUN_ID} agent_id=${AGENT_ID} attempt=${ATTEMPT}"
echo "[aep][codex] workspace=${AEP_WORKSPACE}"
echo "[aep][codex] model=${CODEX_MODEL} timeout=${CODEX_TIMEOUT}s"

# Create workspace marker for Codex
touch "${AEP_WORKSPACE}/.codex_workspace"

# Record start time
START_TIME=$(date +%s%3N)

# Execute Codex with AEP-compliant settings
set +e
cd "${AEP_WORKSPACE}"

# Build Codex command
CODEX_CMD=(
  codex
  --model "${CODEX_MODEL}"
  --approval-mode "${CODEX_APPROVAL_MODE}"
  --writable-root "${AEP_WORKSPACE}"
)

# Add timeout if supported
if codex --help 2>&1 | grep -q -- "--timeout"; then
  CODEX_CMD+=(--timeout "${CODEX_TIMEOUT}")
fi

# Add quiet mode to reduce output noise
if codex --help 2>&1 | grep -q -- "--quiet"; then
  CODEX_CMD+=(--quiet)
fi

# Execute and capture output
"${CODEX_CMD[@]}" "${PROMPT}" \
  > "${AEP_ARTIFACT_DIR}/stdout.log" 2> "${AEP_ARTIFACT_DIR}/stderr.log"

CODEX_EXIT_CODE=$?
set -e

# Record end time
END_TIME=$(date +%s%3N)
DURATION_MS=$((END_TIME - START_TIME))

echo "[aep][codex] finished with exit_code=${CODEX_EXIT_CODE} duration=${DURATION_MS}ms"

# ============================================================================
# Generate Driver Result
# ============================================================================

"${PY_BIN}" - "${AEP_BASELINE}" "${AEP_WORKSPACE}" "${AEP_ARTIFACT_DIR}" "${AEP_RESULT_PATH}" "${RUN_ID}" "${AGENT_ID}" "${ATTEMPT}" "${CODEX_EXIT_CODE}" "${DURATION_MS}" <<'PY'
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
duration_ms = int(sys.argv[9])


def collect_files(root: Path) -> set[str]:
    """Collect all file paths relative to root."""
    if not root.exists():
        return set()
    skip_dirs = {".git", "__pycache__", "node_modules", ".codex_workspace"}
    return {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p.parent.name not in skip_dirs
    }


def compute_diff_files(baseline: Path, workspace: Path) -> list[str]:
    """Compute list of changed/added/deleted files."""
    base_files = collect_files(baseline)
    ws_files = collect_files(workspace)
    changed = []
    
    all_files = base_files | ws_files
    for rel in sorted(all_files):
        base_path = baseline / rel
        ws_path = workspace / rel
        
        # New file
        if not base_path.exists() and ws_path.exists():
            changed.append(rel)
            continue
        
        # Deleted file
        if base_path.exists() and not ws_path.exists():
            changed.append(rel)
            continue
        
        # Modified file
        if base_path.exists() and ws_path.exists():
            try:
                if base_path.read_bytes() != ws_path.read_bytes():
                    changed.append(rel)
            except Exception:
                # Binary file or permission error
                changed.append(rel)
    
    return changed


def extract_summary_from_logs(artifact_dir: Path) -> str:
    """Try to extract a summary from Codex output."""
    stdout_path = artifact_dir / "stdout.log"
    if not stdout_path.exists():
        return "Codex adapter finished"
    
    content = stdout_path.read_text(encoding="utf-8", errors="ignore")
    lines = content.strip().split("\n")
    
    # Look for summary-like patterns
    for line in reversed(lines[-10:]):
        line = line.strip()
        if not line:
            continue
        # Codex often outputs a summary at the end
        if any(keyword in line.lower() for keyword in ["summary:", "changes:", "completed", "modified", "created"]):
            return line[:200]  # Limit length
    
    # Fallback: use last non-empty line
    for line in reversed(lines):
        line = line.strip()
        if line:
            return line[:200]
    
    return "Codex adapter finished"


# Compute changed files
changed_paths = compute_diff_files(baseline, workspace)

# Extract summary from logs
summary = extract_summary_from_logs(artifact_dir) if exit_code == 0 else f"Codex adapter exited with code {exit_code}"

# Collect artifacts
artifacts = []
stdout_artifact = artifact_dir / "stdout.log"
stderr_artifact = artifact_dir / "stderr.log"

if stdout_artifact.exists():
    artifacts.append({
        "name": "stdout",
        "kind": "log",
        "uri": str(stdout_artifact),
        "sha256": None,
    })

if stderr_artifact.exists() and stderr_artifact.stat().st_size > 0:
    artifacts.append({
        "name": "stderr",
        "kind": "log",
        "uri": str(stderr_artifact),
        "sha256": None,
    })

# Determine status and recommended action
if exit_code == 0:
    status = "succeeded"
    recommended = "promote"
    error = None
elif exit_code == 124:  # Timeout exit code
    status = "timed_out"
    recommended = "retry"
    error = "Codex execution timed out"
else:
    status = "failed"
    recommended = "fallback"
    error = summary

# Build driver result
payload = {
    "protocol_version": "aep/v0",
    "run_id": run_id,
    "agent_id": agent_id,
    "attempt": attempt,
    "status": status,
    "summary": summary,
    "changed_paths": changed_paths,
    "output_artifacts": artifacts,
    "metrics": {
        "duration_ms": duration_ms,
        "steps": 1,  # Codex executes as a single step
        "commands": 1,
        "prompt_tokens": None,  # Codex CLI doesn't expose this
        "completion_tokens": None,
    },
    "recommended_action": recommended,
    "error": error,
}

result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
PY

# ============================================================================
# Cleanup and Exit
# ============================================================================

# Remove workspace marker
rm -f "${AEP_WORKSPACE}/.codex_workspace"

if [[ ${CODEX_EXIT_CODE} -eq 0 ]]; then
  echo "[aep][codex] success - result written to ${AEP_RESULT_PATH}"
  exit 0
else
  echo "[aep][codex] failed - exit_code=${CODEX_EXIT_CODE}" >&2
  exit 20
fi
