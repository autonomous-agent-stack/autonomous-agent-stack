#!/usr/bin/env bash
# yt-dlp Agent Adapter
# 遵循 AEP v0 协议
# Linux 主运行，Mac 备用
set -euo pipefail

# ========================================================================
# 环境变量校验
# ========================================================================
require_env() {
  local key="$1"
  if [[ -z "${!key:-}" ]]; then
    echo "[aep][yt-dlp] missing env: ${key}" >&2
    exit 40
  fi
}

require_env "AEP_RUN_DIR"
require_env "AEP_WORKSPACE"
require_env "AEP_ARTIFACT_DIR"
require_env "AEP_JOB_SPEC"
require_env "AEP_RESULT_PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PY_BIN="${PYTHON_BIN:-python3}"
ATTEMPT="${AEP_ATTEMPT:-1}"

# ========================================================================
# 运行时角色检查
# ========================================================================
RUNTIME_HOST="${AUTORESEARCH_RUNTIME_HOST:-unknown}"
EXECUTION_ROLE="${AUTORESEARCH_EXECUTION_ROLE:-unknown}"
TASK_RISK_PROFILE="${AUTORESEARCH_TASK_RISK_PROFILE:-full}"

# Mac 备用机检查 Linux 主控在线状态
check_primary_controller() {
  local probe_urls="${AUTORESEARCH_PRIMARY_CONTROLLER_PROBE_URLS:-}"
  if [[ -z "${probe_urls}" ]]; then
    return 0  # 无配置，允许继续
  fi

  local health_url
  health_url=$(echo "${probe_urls}" | "${PY_BIN}" -c 'import json,sys; d=json.loads(sys.stdin.read()); print(d[0] if d else "")' 2>/dev/null || echo "")
  if [[ -z "${health_url}" ]]; then
    return 0
  fi

  local response
  if response=$(curl -sf --connect-timeout 5 --max-time 10 "${health_url}" 2>/dev/null); then
    local controller_status
    controller_status=$(echo "${response}" | "${PY_BIN}" -c 'import json,sys; d=json.loads(sys.stdin.read()); print(d.get("controller_status","unknown"))' 2>/dev/null || echo "unknown")
    if [[ "${controller_status}" == "online" ]]; then
      echo "[aep][yt-dlp] Linux primary controller is online, should delegate" >&2
      return 1  # Linux 在线，应该转交
    fi
  fi
  return 0  # Linux 离线，Mac 可接管
}

# Mac 备用机风险检查
check_risk_profile() {
  if [[ "${EXECUTION_ROLE}" == "backup" ]]; then
    # Mac 备用只接受 low/medium 风险任务
    if [[ "${TASK_RISK_PROFILE}" == "full" || "${TASK_RISK_PROFILE}" == "high" ]]; then
      echo "[aep][yt-dlp] Mac backup rejects high-risk task" >&2
      return 1
    fi
  fi
  return 0
}

# Mac 备用机检查逻辑
if [[ "${EXECUTION_ROLE}" == "backup" ]]; then
  if ! check_primary_controller; then
    # Linux 在线，生成转交建议结果
    "${PY_BIN}" - "${AEP_RESULT_PATH}" "${RUNTIME_HOST}" <<'PY'
import json
import sys
from pathlib import Path

result_path = Path(sys.argv[1])
runtime_host = sys.argv[2] if len(sys.argv) > 2 else "unknown"

payload = {
    "protocol_version": "aep/v0",
    "run_id": "delegated",
    "agent_id": "yt-dlp",
    "attempt": 1,
    "status": "succeeded",
    "summary": f"Task delegated to Linux primary controller (from {runtime_host})",
    "changed_paths": [],
    "output_artifacts": [],
    "metrics": {"duration_ms": 0, "steps": 0, "commands": 0},
    "recommended_action": "promote",
    "error": None
}
result_path.parent.mkdir(parents=True, exist_ok=True)
result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
PY
    exit 0
  fi

  if ! check_risk_profile; then
    exit 40  # Contract error
  fi

  echo "[aep][yt-dlp] Mac backup taking over (Linux offline, low/medium risk)" >&2
fi

# ========================================================================
# Job Spec 解析
# ========================================================================
if [[ ! -f "${AEP_JOB_SPEC}" ]]; then
  echo "[aep][yt-dlp] missing job spec: ${AEP_JOB_SPEC}" >&2
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
METADATA_RAW="$(read_job_field metadata)"

# 从 metadata 提取 yt-dlp 特定参数
# 默认值：下载字幕
URL=""
FORMAT="best[height<=1080]"
OUTPUT_TEMPLATE="%(title)s.%(ext)s"
WRITE_SUBS="true"
SUB_LANGS="zh-Hans,zh-Hant,en"
SKIP_DOWNLOAD="true"
FORCE="false"
WRITE_THUMB="false"
EXTRACT_AUDIO="false"
AUDIO_FORMAT="mp3"

if [[ -n "${METADATA_RAW}" ]]; then
  URL="$(echo "${METADATA_RAW}" | "${PY_BIN}" -c 'import json,sys; d=json.load(sys.stdin); print(d.get("url",""))' 2>/dev/null || echo "")"
  FORMAT="$(echo "${METADATA_RAW}" | "${PY_BIN}" -c 'import json,sys; d=json.load(sys.stdin); print(d.get("format","best[height<=1080]"))' 2>/dev/null || echo "best[height<=1080]")"
  OUTPUT_TEMPLATE="$(echo "${METADATA_RAW}" | "${PY_BIN}" -c 'import json,sys; d=json.load(sys.stdin); print(d.get("output_template","%(title)s.%(ext)s"))' 2>/dev/null || echo "%(title)s.%(ext)s")"
  WRITE_SUBS="$(echo "${METADATA_RAW}" | "${PY_BIN}" -c 'import json,sys; d=json.load(sys.stdin); print(str(d.get("write_subs",True)).lower())' 2>/dev/null || echo "true")"
  SUB_LANGS="$(echo "${METADATA_RAW}" | "${PY_BIN}" -c 'import json,sys; d=json.load(sys.stdin); print(d.get("sub_langs","zh-Hans,zh-Hant,en"))' 2>/dev/null || echo "zh-Hans,zh-Hant,en")"
  SKIP_DOWNLOAD="$(echo "${METADATA_RAW}" | "${PY_BIN}" -c 'import json,sys; d=json.load(sys.stdin); print(str(d.get("skip_download",True)).lower())' 2>/dev/null || echo "true")"
  FORCE="$(echo "${METADATA_RAW}" | "${PY_BIN}" -c 'import json,sys; d=json.load(sys.stdin); print(str(d.get("force",False)).lower())' 2>/dev/null || echo "false")"
  WRITE_THUMB="$(echo "${METADATA_RAW}" | "${PY_BIN}" -c 'import json,sys; d=json.load(sys.stdin); print(str(d.get("write_thumbnail",False)).lower())' 2>/dev/null || echo "false")"
  EXTRACT_AUDIO="$(echo "${METADATA_RAW}" | "${PY_BIN}" -c 'import json,sys; d=json.load(sys.stdin); print(str(d.get("extract_audio",False)).lower())' 2>/dev/null || echo "false")"
  AUDIO_FORMAT="$(echo "${METADATA_RAW}" | "${PY_BIN}" -c 'import json,sys; d=json.load(sys.stdin); print(d.get("audio_format","mp3"))' 2>/dev/null || echo "mp3")"
fi

# 从 task 字段解析 URL（如果没有在 metadata 中指定）
if [[ -z "${URL}" ]]; then
  URL="$("${PY_BIN}" -c 'import re,sys; m=re.search(r"(https?://[^\s]+)", sys.argv[1]); print(m.group(1) if m else "")' "${TASK}" 2>/dev/null || echo "")"
fi

if [[ -z "${URL}" ]]; then
  echo "[aep][yt-dlp] no URL found in task or metadata" >&2
  exit 40
fi

echo "[aep][yt-dlp] URL: ${URL}"
echo "[aep][yt-dlp] Format: ${FORMAT}"
echo "[aep][yt-dlp] Runtime: ${RUNTIME_HOST} (${EXECUTION_ROLE})"

# ========================================================================
# 输出目录准备
# ========================================================================
OUTPUT_DIR="${AEP_ARTIFACT_DIR}/downloads"
PROCESSED_URLS_FILE="${REPO_ROOT}/data/yt-dlp_processed.json"
mkdir -p "${OUTPUT_DIR}"
mkdir -p "${REPO_ROOT}/data"

# ========================================================================
# 去重检查：已下载过的链接跳过
# ========================================================================
check_if_processed() {
  local url="$1"
  if [[ ! -f "${PROCESSED_URLS_FILE}" ]]; then
    return 1  # 文件不存在，未处理过
  fi
  "${PY_BIN}" - "${PROCESSED_URLS_FILE}" "${url}" <<'PY'
import json
import sys
from pathlib import Path

state_file = Path(sys.argv[1])
url = sys.argv[2]

try:
    data = json.loads(state_file.read_text(encoding="utf-8"))
    processed = data.get("processed_urls", {})
    if url in processed:
        print(f"[aep][yt-dlp] URL already processed at {processed[url]}, skipping" >&2)
        sys.exit(0)  # 已处理，退出码0
    sys.exit(1)  # 未处理
except (json.JSONDecodeError, FileNotFoundError):
    sys.exit(1)  # 未处理
PY
}

record_processed() {
  local url="$1"
  local timestamp="$2"
  "${PY_BIN}" - "${PROCESSED_URLS_FILE}" "${url}" "${timestamp}" <<'PY'
import json
import sys
from pathlib import Path
from datetime import datetime

state_file = Path(sys.argv[1])
url = sys.argv[2]
timestamp = sys.argv[3]

try:
    data = json.loads(state_file.read_text(encoding="utf-8"))
except (json.JSONDecodeError, FileNotFoundError):
    data = {"processed_urls": {}}

data["processed_urls"][url] = timestamp
data["last_updated"] = timestamp

state_file.parent.mkdir(parents=True, exist_ok=True)
state_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
PY
}

# 检查是否已处理（force=true 时跳过）
if [[ "${FORCE}" != "true" ]] && check_if_processed "${URL}"; then
  # 已处理，生成跳过结果
  "${PY_BIN}" - "${AEP_RESULT_PATH}" "${RUN_ID}" "${URL}" <<'PY'
import json
import sys
from pathlib import Path

result_path = Path(sys.argv[1])
run_id = sys.argv[2]
url = sys.argv[3]

payload = {
    "protocol_version": "aep/v0",
    "run_id": run_id,
    "agent_id": "yt-dlp",
    "attempt": 1,
    "status": "succeeded",
    "summary": f"URL already processed, skipped: {url}",
    "changed_paths": [],
    "output_artifacts": [],
    "metrics": {"duration_ms": 0, "steps": 0, "commands": 0},
    "recommended_action": "promote",
    "error": None
}
result_path.parent.mkdir(parents=True, exist_ok=True)
result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
PY
  exit 0
fi

# ========================================================================
# yt-dlp 执行
# ========================================================================
YT_DLP_BIN="${YT_DLP_BIN:-yt-dlp}"

# 检查 yt-dlp 是否可用
if ! command -v "${YT_DLP_BIN}" &>/dev/null; then
  echo "[aep][yt-dlp] yt-dlp not found in PATH" >&2
  exit 40
fi

# 构建命令参数
YT_ARGS=(
  --no-progress
  --no-warnings
  --ignore-errors
  --output "${OUTPUT_DIR}/${OUTPUT_TEMPLATE}"
  --format "${FORMAT}"
)

if [[ "${WRITE_SUBS}" == "true" ]]; then
  YT_ARGS+=(--write-subs --write-auto-subs --sub-langs "${SUB_LANGS}")
fi

if [[ "${SKIP_DOWNLOAD}" == "true" ]]; then
  YT_ARGS+=(--skip-download)
fi

if [[ "${WRITE_THUMB}" == "true" ]]; then
  YT_ARGS+=(--write-thumbnail)
fi

if [[ "${EXTRACT_AUDIO}" == "true" ]]; then
  YT_ARGS+=(--extract-audio --audio-format "${AUDIO_FORMAT}")
fi

# 执行下载
START_TIME=$(date +%s%3N)
set +e
"${YT_DLP_BIN}" "${YT_ARGS[@]}" "${URL}" 2>&1 | tee "${AEP_ARTIFACT_DIR}/yt-dlp.log"
YT_EXIT_CODE=${PIPESTATUS[0]}
set -e
END_TIME=$(date +%s%3N)
DURATION_MS=$((END_TIME - START_TIME))

# ========================================================================
# 收集结果
# ========================================================================
"${PY_BIN}" - "${AEP_ARTIFACT_DIR}" "${AEP_RESULT_PATH}" "${RUN_ID}" "${AGENT_ID}" "${ATTEMPT}" "${YT_EXIT_CODE}" "${DURATION_MS}" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

artifact_dir = Path(sys.argv[1])
result_path = Path(sys.argv[2])
run_id = sys.argv[3]
agent_id = sys.argv[4]
attempt = int(sys.argv[5])
exit_code = int(sys.argv[6])
duration_ms = int(sys.argv[7])

downloads_dir = artifact_dir / "downloads"


def guess_mime(suffix: str) -> str:
    mimes = {
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".mkv": "video/x-matroska",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".opus": "audio/opus",
        ".vtt": "text/vtt",
        ".srt": "text/srt",
        ".jpg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".json": "application/json",
    }
    return mimes.get(suffix.lower(), "application/octet-stream")


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_downloads(root: Path) -> list[dict]:
    if not root.exists():
        return []
    items = []
    for p in root.rglob("*"):
        if p.is_file():
            stat = p.stat()
            items.append({
                "name": p.name,
                "path": str(p.relative_to(root)),
                "size_bytes": stat.st_size,
                "mime_type": guess_mime(p.suffix),
            })
    return items


# 收集下载的文件
downloaded_files = collect_downloads(downloads_dir)
changed_paths = [item["path"] for item in downloaded_files]

# 构建输出 artifacts
artifacts = []
for item in downloaded_files:
    file_path = downloads_dir / item["path"]
    artifacts.append({
        "name": item["name"],
        "kind": "download",
        "uri": str(file_path),
        "sha256": compute_sha256(file_path) if file_path.exists() else None,
    })

# 添加日志 artifact
log_path = artifact_dir / "yt-dlp.log"
if log_path.exists():
    artifacts.append({
        "name": "yt-dlp.log",
        "kind": "log",
        "uri": str(log_path),
        "sha256": None,
    })

# 确定状态
if exit_code == 0:
    status = "succeeded"
    recommended = "promote"
    summary = f"yt-dlp downloaded {len(downloaded_files)} file(s)"
elif exit_code == 1:
    # yt-dlp 返回 1 表示部分成功
    status = "partial" if downloaded_files else "failed"
    recommended = "promote" if downloaded_files else "retry"
    summary = f"yt-dlp partial success: {len(downloaded_files)} file(s) downloaded"
else:
    status = "failed"
    recommended = "retry"
    summary = f"yt-dlp failed with exit code {exit_code}"

total_bytes = sum(item["size_bytes"] for item in downloaded_files)

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
        "files_downloaded": len(downloaded_files),
        "total_bytes": total_bytes,
    },
    "recommended_action": recommended,
    "error": None if exit_code == 0 else summary,
}

result_path.parent.mkdir(parents=True, exist_ok=True)
result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
PY

# 记录已处理的 URL 并提交到 GitHub（下载成功时）
if [[ ${YT_EXIT_CODE} -eq 0 ]]; then
    TIMESTAMP="$(date -Iseconds)"
    record_processed "${URL}" "${TIMESTAMP}"

    # Git commit & push
    cd "${REPO_ROOT}"
    if git diff --quiet "${PROCESSED_URLS_FILE}" 2>/dev/null; then
      echo "[aep][yt-dlp] No changes to commit"
    else
      git add "${PROCESSED_URLS_FILE}"
      git commit -m "chore(yt-dlp): mark URL as processed - ${URL:0:50}..."
      git push origin HEAD
      echo "[aep][yt-dlp] Pushed to GitHub"
    fi
fi

# 返回适当的退出码
if [[ ${YT_EXIT_CODE} -eq 0 ]]; then
    exit 0
fi
if [[ ${YT_EXIT_CODE} -eq 40 || ${YT_EXIT_CODE} -eq 127 ]]; then
    exit 40
fi
exit 20
