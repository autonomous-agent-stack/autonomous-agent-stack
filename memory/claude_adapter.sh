#!/usr/bin/env bash
# claude_adapter.sh - Claude (Anthropic) Driver for AEP v0
#
# Claude是Anthropic的高质量推理模型，特别适合：
# - 复杂推理任务
# - 代码审查
# - 架构设计
# - 长文本处理
#
# 使用方法:
#   环境变量（由runner.py注入）:
#     - AEP_RUN_DIR: 运行目录
#     - AEP_WORKSPACE: 工作空间
#     - AEP_ARTIFACT_DIR: 产物目录
#     - AEP_JOB_SPEC: 任务描述文件
#     - AEP_RESULT_PATH: 结果文件路径
#     - AEP_BASELINE: 基线目录
#
# 配置:
#   export ANTHROPIC_API_KEY="your-claude-key"
#   export CLAUDE_MODEL="claude-3-5-sonnet-20241022"  # 推荐

set -euo pipefail

# ============================================================================
# 环境验证
# ============================================================================

require_env() {
  local key="$1"
  if [[ -z "${!key:-}" ]]; then
    echo "[aep][claude] missing env: ${key}" >&2
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
# 配置
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PY_BIN="${PYTHON_BIN:-python3}"
ATTEMPT="${AEP_ATTEMPT:-1}"

# Claude 特定配置
CLAUDE_MODEL="${CLAUDE_MODEL:-claude-3-5-sonnet-20241022}"
CLAUDE_TIMEOUT="${CLAUDE_TIMEOUT:-300}"
CLAUDE_API_BASE="${CLAUDE_API_BASE:-https://api.anthropic.com/v1}"

# ============================================================================
# 前置检查
# ============================================================================

if [[ ! -f "${AEP_JOB_SPEC}" ]]; then
  echo "[aep][claude] missing job spec: ${AEP_JOB_SPEC}" >&2
  exit 40
fi

# 检查API Key
if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "[aep][claude] ANTHROPIC_API_KEY not set" >&2
  echo "[aep][claude] Get your key from: https://console.anthropic.com/" >&2
  exit 42
fi

# ============================================================================
# Job Spec 解析
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
# 提取任务参数
# ============================================================================

RUN_ID="$(read_job_field run_id)"
AGENT_ID="$(read_job_field agent_id)"
TASK="$(read_job_field task)"
TIMEOUT_SEC_RAW="$(read_job_field policy.timeout_sec)"

if [[ -z "${RUN_ID}" || -z "${AGENT_ID}" || -z "${TASK}" ]]; then
  echo "[aep][claude] invalid job spec fields" >&2
  exit 40
fi

# 覆盖超时
if [[ "${TIMEOUT_SEC_RAW}" =~ ^[0-9]+$ ]]; then
  CLAUDE_TIMEOUT="${TIMEOUT_SEC_RAW}"
fi

# ============================================================================
# 构建 Claude 请求
# ============================================================================

mkdir -p "${AEP_ARTIFACT_DIR}"

PROMPT="${TASK}

Execution contract:
- Complete only this single task
- Do not commit, push, or modify git settings
- Only edit files within the workspace
- Provide a concise summary of changes"

echo "[aep][claude] starting run_id=${RUN_ID} agent_id=${AGENT_ID} attempt=${ATTEMPT}"
echo "[aep][claude] workspace=${AEP_WORKSPACE}"
echo "[aep][claude] model=${CLAUDE_MODEL} timeout=${CLAUDE_TIMEOUT}s"

# 记录开始时间
START_TIME=$(date +%s%3N)

# ============================================================================
# 执行 Claude API 调用
# ============================================================================

set +e

# 使用 curl 调用 Anthropic API
RESPONSE_FILE="${AEP_ARTIFACT_DIR}/claude_response.json"

curl -s -X POST "${CLAUDE_API_BASE}/messages" \
  -H "x-api-key: ${ANTHROPIC_API_KEY}" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${CLAUDE_MODEL}\",
    \"max_tokens\": 4096,
    \"messages\": [
      {\"role\": \"user\", \"content\": \"${PROMPT}\"}
    ]
  }" \
  --max-time "${CLAUDE_TIMEOUT}" \
  -o "${RESPONSE_FILE}"

CLAUDE_EXIT_CODE=$?
set -e

# 记录结束时间
END_TIME=$(date +%s%3N)
DURATION_MS=$((END_TIME - START_TIME))

echo "[aep][claude] finished with exit_code=${CLAUDE_EXIT_CODE} duration=${DURATION_MS}ms"

# ============================================================================
# 解析响应
# ============================================================================

if [[ ${CLAUDE_EXIT_CODE} -eq 0 && -f "${RESPONSE_FILE}" ]]; then
  CONTENT=$("${PY_BIN}" - "${RESPONSE_FILE}" <<'PY'
import json
import sys
from pathlib import Path

response_path = Path(sys.argv[1])
try:
    data = json.loads(response_path.read_text())
    # Claude API format: content[0].text
    content = data.get("content", [{}])[0].get("text", "")
    print(content)
except Exception as e:
    print(f"Error parsing response: {e}", file=sys.stderr)
    sys.exit(1)
PY
)
  
  # 保存响应
  echo "${CONTENT}" > "${AEP_ARTIFACT_DIR}/stdout.log"
  echo "[aep][claude] response saved to ${AEP_ARTIFACT_DIR}/stdout.log"
fi

# ============================================================================
# 生成 Driver Result
# ============================================================================

"${PY_BIN}" - "${AEP_BASELINE}" "${AEP_WORKSPACE}" "${AEP_ARTIFACT_DIR}" "${AEP_RESULT_PATH}" "${RUN_ID}" "${AGENT_ID}" "${ATTEMPT}" "${CLAUDE_EXIT_CODE}" "${DURATION_MS}" <<'PY'
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
    if not root.exists():
        return set()
    skip_dirs = {".git", "__pycache__", "node_modules"}
    return {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p.parent.name not in skip_dirs
    }


def compute_diff_files(baseline: Path, workspace: Path) -> list[str]:
    base_files = collect_files(baseline)
    ws_files = collect_files(workspace)
    changed = []
    
    for rel in sorted(base_files | ws_files):
        base_path = baseline / rel
        ws_path = workspace / rel
        
        if not base_path.exists() or not ws_path.exists():
            changed.append(rel)
        elif base_path.read_bytes() != ws_path.read_bytes():
            changed.append(rel)
    
    return changed


def extract_summary(artifact_dir: Path) -> str:
    stdout_path = artifact_dir / "stdout.log"
    if not stdout_path.exists():
        return "Claude adapter finished"
    
    content = stdout_path.read_text(encoding="utf-8", errors="ignore")
    return content[:200] if content else "Claude adapter finished"


changed_paths = compute_diff_files(baseline, workspace)
summary = extract_summary(artifact_dir) if exit_code == 0 else f"Claude adapter exited with code {exit_code}"

artifacts = []
for name in ["stdout.log", "claude_response.json"]:
    path = artifact_dir / name
    if path.exists():
        artifacts.append({
            "name": name.replace(".", "_"),
            "kind": "log",
            "uri": str(path),
            "sha256": None,
        })

if exit_code == 0:
    status = "succeeded"
    recommended = "promote"
    error = None
elif exit_code == 28:
    status = "timed_out"
    recommended = "retry"
    error = "Claude API request timed out"
else:
    status = "failed"
    recommended = "fallback"
    error = summary

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
        "steps": 1,
        "commands": 1,
        "prompt_tokens": None,
        "completion_tokens": None,
    },
    "recommended_action": recommended,
    "error": error,
}

result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
PY

# ============================================================================
# 清理和退出
# ============================================================================

if [[ ${CLAUDE_EXIT_CODE} -eq 0 ]]; then
  echo "[aep][claude] success - result written to ${AEP_RESULT_PATH}"
  exit 0
else
  echo "[aep][claude] failed - exit_code=${CLAUDE_EXIT_CODE}" >&2
  exit 20
fi
