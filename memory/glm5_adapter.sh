#!/usr/bin/env bash
# glm5_adapter.sh - GLM-5 (Zhipu AI) Driver for AEP v0
#
# GLM-5是智谱AI的中文优化模型，特别适合：
# - 中文任务
# - 成本敏感场景（比GPT-4便宜98%）
# - 国产化需求
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
#   export ZHIPUAI_API_KEY="your-glm5-key"
#   export GLM5_MODEL="glm-5"  # 可选: glm-5, glm-5-plus

set -euo pipefail

# ============================================================================
# 环境验证
# ============================================================================

require_env() {
  local key="$1"
  if [[ -z "${!key:-}" ]]; then
    echo "[aep][glm5] missing env: ${key}" >&2
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

# GLM-5 特定配置
GLM5_MODEL="${GLM5_MODEL:-glm-5}"
GLM5_TIMEOUT="${GLM5_TIMEOUT:-300}"
GLM5_API_BASE="${GLM5_API_BASE:-https://open.bigmodel.cn/api/paas/v4}"

# ============================================================================
# 前置检查
# ============================================================================

if [[ ! -f "${AEP_JOB_SPEC}" ]]; then
  echo "[aep][glm5] missing job spec: ${AEP_JOB_SPEC}" >&2
  exit 40
fi

# 检查API Key
if [[ -z "${ZHIPUAI_API_KEY:-}" ]]; then
  echo "[aep][glm5] ZHIPUAI_API_KEY not set" >&2
  echo "[aep][glm5] Get your key from: https://open.bigmodel.cn/" >&2
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
  echo "[aep][glm5] invalid job spec fields" >&2
  exit 40
fi

# 覆盖超时
if [[ "${TIMEOUT_SEC_RAW}" =~ ^[0-9]+$ ]]; then
  GLM5_TIMEOUT="${TIMEOUT_SEC_RAW}"
fi

# ============================================================================
# 构建 GLM-5 请求
# ============================================================================

mkdir -p "${AEP_ARTIFACT_DIR}"

PROMPT="${TASK}

执行约束:
- 仅完成单个任务
- 不要提交、推送或修改git配置
- 仅编辑工作空间内的文件
- 返回简洁的变更总结"

echo "[aep][glm5] starting run_id=${RUN_ID} agent_id=${AGENT_ID} attempt=${ATTEMPT}"
echo "[aep][glm5] workspace=${AEP_WORKSPACE}"
echo "[aep][glm5] model=${GLM5_MODEL} timeout=${GLM5_TIMEOUT}s"

# 记录开始时间
START_TIME=$(date +%s%3N)

# ============================================================================
# 执行 GLM-5 API 调用
# ============================================================================

set +e

# 使用 curl 调用智谱AI API
RESPONSE_FILE="${AEP_ARTIFACT_DIR}/glm5_response.json"

curl -s -X POST "${GLM5_API_BASE}/chat/completions" \
  -H "Authorization: Bearer ${ZHIPUAI_API_KEY}" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${GLM5_MODEL}\",
    \"messages\": [
      {\"role\": \"system\", \"content\": \"你是一个专业的代码助手，擅长中文编程任务。\"},
      {\"role\": \"user\", \"content\": \"${PROMPT}\"}
    ],
    \"temperature\": 0.7,
    \"max_tokens\": 4096
  }" \
  --max-time "${GLM5_TIMEOUT}" \
  -o "${RESPONSE_FILE}"

GLM5_EXIT_CODE=$?
set -e

# 记录结束时间
END_TIME=$(date +%s%3N)
DURATION_MS=$((END_TIME - START_TIME))

echo "[aep][glm5] finished with exit_code=${GLM5_EXIT_CODE} duration=${DURATION_MS}ms"

# ============================================================================
# 解析响应并应用变更
# ============================================================================

if [[ ${GLM5_EXIT_CODE} -eq 0 && -f "${RESPONSE_FILE}" ]]; then
  # 提取响应内容
  CONTENT=$("${PY_BIN}" - "${RESPONSE_FILE}" <<'PY'
import json
import sys
from pathlib import Path

response_path = Path(sys.argv[1])
try:
    data = json.loads(response_path.read_text())
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    print(content)
except Exception as e:
    print(f"Error parsing response: {e}", file=sys.stderr)
    sys.exit(1)
PY
)
  
  # 保存响应到日志
  echo "${CONTENT}" > "${AEP_ARTIFACT_DIR}/stdout.log"
  
  # TODO: 这里需要实现代码应用逻辑
  # 当前版本仅返回响应，不自动应用变更
  # 未来可以集成代码解析和文件修改
  
  echo "[aep][glm5] response saved to ${AEP_ARTIFACT_DIR}/stdout.log"
fi

# ============================================================================
# 生成 Driver Result
# ============================================================================

"${PY_BIN}" - "${AEP_BASELINE}" "${AEP_WORKSPACE}" "${AEP_ARTIFACT_DIR}" "${AEP_RESULT_PATH}" "${RUN_ID}" "${AGENT_ID}" "${ATTEMPT}" "${GLM5_EXIT_CODE}" "${DURATION_MS}" <<'PY'
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
    """收集所有文件路径"""
    if not root.exists():
        return set()
    skip_dirs = {".git", "__pycache__", "node_modules"}
    return {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p.parent.name not in skip_dirs
    }


def compute_diff_files(baseline: Path, workspace: Path) -> list[str]:
    """计算变更文件列表"""
    base_files = collect_files(baseline)
    ws_files = collect_files(workspace)
    changed = []
    
    all_files = base_files | ws_files
    for rel in sorted(all_files):
        base_path = baseline / rel
        ws_path = workspace / rel
        
        if not base_path.exists() or not ws_path.exists():
            changed.append(rel)
            continue
        
        if base_path.exists() and ws_path.exists():
            try:
                if base_path.read_bytes() != ws_path.read_bytes():
                    changed.append(rel)
            except Exception:
                changed.append(rel)
    
    return changed


def extract_summary(artifact_dir: Path) -> str:
    """从响应中提取摘要"""
    stdout_path = artifact_dir / "stdout.log"
    if not stdout_path.exists():
        return "GLM-5 adapter finished"
    
    content = stdout_path.read_text(encoding="utf-8", errors="ignore")
    lines = content.strip().split("\n")
    
    # 返回前200字符作为摘要
    if content:
        return content[:200]
    
    return "GLM-5 adapter finished"


# 计算变更文件
changed_paths = compute_diff_files(baseline, workspace)

# 提取摘要
summary = extract_summary(artifact_dir) if exit_code == 0 else f"GLM-5 adapter exited with code {exit_code}"

# 收集产物
artifacts = []
stdout_artifact = artifact_dir / "stdout.log"
response_artifact = artifact_dir / "glm5_response.json"

if stdout_artifact.exists():
    artifacts.append({
        "name": "stdout",
        "kind": "log",
        "uri": str(stdout_artifact),
        "sha256": None,
    })

if response_artifact.exists():
    artifacts.append({
        "name": "glm5_response",
        "kind": "log",
        "uri": str(response_artifact),
        "sha256": None,
    })

# 确定状态和建议操作
if exit_code == 0:
    status = "succeeded"
    recommended = "promote"
    error = None
elif exit_code == 28:  # curl timeout
    status = "timed_out"
    recommended = "retry"
    error = "GLM-5 API request timed out"
else:
    status = "failed"
    recommended = "fallback"
    error = summary

# 构建结果
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

if [[ ${GLM5_EXIT_CODE} -eq 0 ]]; then
  echo "[aep][glm5] success - result written to ${AEP_RESULT_PATH}"
  exit 0
else
  echo "[aep][glm5] failed - exit_code=${GLM5_EXIT_CODE}" >&2
  exit 20
fi
