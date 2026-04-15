#!/usr/bin/env bash
set -euo pipefail

require_env() {
  local key="$1"
  if [[ -z "${!key:-}" ]]; then
    echo "[aep][claude_code] missing env: ${key}" >&2
    exit 40
  fi
}

require_env "AEP_RUN_DIR"
require_env "AEP_WORKSPACE"
require_env "AEP_ARTIFACT_DIR"
require_env "AEP_JOB_SPEC"
require_env "AEP_RESULT_PATH"
require_env "AEP_BASELINE"

PY_BIN="${PYTHON_BIN:-python3}"
ATTEMPT="${AEP_ATTEMPT:-1}"
CLAUDE_CODE_BIN="${CLAUDE_CODE_BIN:-claude}"
CLAUDE_CODE_DRY_RUN="${CLAUDE_CODE_DRY_RUN:-0}"
CLAUDE_CODE_PERMISSION_MODE="${CLAUDE_CODE_PERMISSION_MODE:-auto}"
CLAUDE_CODE_AUTH_STATUS_FILE="${CLAUDE_CODE_AUTH_STATUS_FILE:-}"

if [[ ! -f "${AEP_JOB_SPEC}" ]]; then
  echo "[aep][claude_code] missing job spec: ${AEP_JOB_SPEC}" >&2
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

resolve_command() {
  local command_name="$1"
  if [[ "${command_name}" == */* ]]; then
    [[ -x "${command_name}" ]] || return 1
    printf '%s\n' "${command_name}"
    return 0
  fi
  command -v "${command_name}"
}

reset_workspace_from_baseline() {
  "${PY_BIN}" - "${AEP_BASELINE}" "${AEP_WORKSPACE}" <<'PY'
import shutil
import sys
from pathlib import Path

baseline = Path(sys.argv[1])
workspace = Path(sys.argv[2])
if workspace.exists():
    shutil.rmtree(workspace)
shutil.copytree(baseline, workspace, dirs_exist_ok=True)
PY
}

workspace_write_probe() {
  local probe_path="${AEP_WORKSPACE}/.claude_code_write_probe.$$"
  : > "${probe_path}" || return 1
  rm -f "${probe_path}"
}

is_auth_error() {
  local text="$1"
  grep -Eqi 'login|authentication|not logged in|not authenticated|unauthorized|setup-token|auth status|oauth|api key' <<<"${text}"
}

RUN_ID="$(read_job_field run_id)"
AGENT_ID="$(read_job_field agent_id)"
TASK="$(read_job_field task)"
MAX_CHANGED_FILES_RAW="$(read_job_field policy.max_changed_files)"
ALLOWED_PATHS_RAW="$(read_job_field policy.allowed_paths)"

if [[ -z "${RUN_ID}" || -z "${AGENT_ID}" || -z "${TASK}" ]]; then
  echo "[aep][claude_code] invalid job spec fields" >&2
  exit 40
fi

MAX_CHANGED_FILES_PROMPT="10"
if [[ "${MAX_CHANGED_FILES_RAW}" =~ ^[0-9]+$ ]]; then
  MAX_CHANGED_FILES_PROMPT="${MAX_CHANGED_FILES_RAW}"
fi

mkdir -p "${AEP_ARTIFACT_DIR}"

PROMPT_PATH="${AEP_ARTIFACT_DIR}/claude_code_prompt.txt"
LAST_MESSAGE_PATH="${AEP_ARTIFACT_DIR}/claude_code_last_message.txt"
CLAUDE_STDOUT_PATH="${AEP_ARTIFACT_DIR}/claude_code_stdout.log"
CLAUDE_STDERR_PATH="${AEP_ARTIFACT_DIR}/claude_code_stderr.log"
CLAUDE_JSON_PATH="${AEP_ARTIFACT_DIR}/claude_code_output.json"
PREFLIGHT_PATH="${AEP_ARTIFACT_DIR}/claude_code_preflight.json"
MODE_PATH="${AEP_ARTIFACT_DIR}/claude_code_mode.txt"

PROMPT="${TASK}

Execution contract:
- Single task only.
- Do not commit.
- Do not push.
- Do not edit git settings.
- Only edit files inside ${AEP_WORKSPACE}.
- Keep changes inside these allowed paths: ${ALLOWED_PATHS_RAW:-[]}
- Change at most ${MAX_CHANGED_FILES_PROMPT} files.
- Return concise summary and changed files."

printf '%s\n' "${PROMPT}" > "${PROMPT_PATH}"
: > "${CLAUDE_STDOUT_PATH}"
: > "${CLAUDE_STDERR_PATH}"
: > "${CLAUDE_JSON_PATH}"
: > "${LAST_MESSAGE_PATH}"

PRECHECK_STATUS="pending"
PRECHECK_REASON=""
SELECTED_MODE="dry_run"
ATTEMPTED_MODES_JSON="[]"
MODE_FAILURES_JSON="{}"
MODE_ATTEMPTS=0
CLAUDE_EXIT_CODE=0
CLAUDE_SUMMARY=""
CLAUDE_ERROR=""

if [[ "${CLAUDE_CODE_DRY_RUN}" == "1" ]]; then
  PRECHECK_STATUS="passed"
  PRECHECK_REASON="dry_run"
  "${PY_BIN}" - "${AEP_WORKSPACE}" "${ALLOWED_PATHS_RAW}" "${TASK}" "${LAST_MESSAGE_PATH}" <<'PY'
import json
import re
import sys
from pathlib import Path

workspace = Path(sys.argv[1])
allowed_raw = sys.argv[2]
task = sys.argv[3].strip().replace('"""', "'''")
last_message_path = Path(sys.argv[4])

try:
    allowed_paths = json.loads(allowed_raw) if allowed_raw else []
except json.JSONDecodeError:
    allowed_paths = []

def pick_target(patterns: list[str]) -> Path:
    for pattern in patterns:
        if not any(char in pattern for char in "*?["):
            return workspace / pattern
    for pattern in patterns:
        prefix = pattern.split("*", 1)[0].split("?", 1)[0].split("[", 1)[0].rstrip("/")
        if prefix:
            if "." in Path(prefix).name:
                return workspace / prefix
            return workspace / prefix / "claude_generated.py"
    return workspace / "src" / "claude_generated.py"

target = pick_target(allowed_paths)
target.parent.mkdir(parents=True, exist_ok=True)
slug = re.sub(r"[^a-z0-9]+", "_", task.lower()).strip("_") or "task"
target.write_text(
    '"""Generated by the Claude Code dry-run adapter."""\n\n'
    "def run() -> dict[str, str]:\n"
    f'    return {{"task": "{slug}", "status": "claude_code_dry_run"}}\n',
    encoding="utf-8",
)
last_message_path.write_text(
    f"Claude Code dry-run completed. Changed file: {target.relative_to(workspace).as_posix()}",
    encoding="utf-8",
)
PY
else
  if ! CLAUDE_CMD_RESOLVED="$(resolve_command "${CLAUDE_CODE_BIN}")"; then
    CLAUDE_EXIT_CODE=40
    CLAUDE_SUMMARY="Claude CLI not found: ${CLAUDE_CODE_BIN}"
    CLAUDE_ERROR="${CLAUDE_SUMMARY}"
    PRECHECK_STATUS="failed"
    PRECHECK_REASON="cli_missing"
  elif ! workspace_write_probe; then
    CLAUDE_EXIT_CODE=40
    CLAUDE_SUMMARY="Workspace is not writable: ${AEP_WORKSPACE}"
    CLAUDE_ERROR="${CLAUDE_SUMMARY}"
    PRECHECK_STATUS="failed"
    PRECHECK_REASON="workspace_not_writable"
  else
    AUTH_STATUS_OUTPUT=""
    if [[ -n "${CLAUDE_CODE_AUTH_STATUS_FILE}" ]]; then
      if [[ ! -s "${CLAUDE_CODE_AUTH_STATUS_FILE}" ]]; then
        CLAUDE_EXIT_CODE=40
        CLAUDE_SUMMARY="Claude auth status file missing or empty: ${CLAUDE_CODE_AUTH_STATUS_FILE}"
        CLAUDE_ERROR="${CLAUDE_SUMMARY}"
        PRECHECK_STATUS="failed"
        PRECHECK_REASON="auth_status_missing"
      else
        AUTH_STATUS_OUTPUT="$(cat "${CLAUDE_CODE_AUTH_STATUS_FILE}")"
      fi
    else
      set +e
      AUTH_STATUS_OUTPUT="$("${CLAUDE_CMD_RESOLVED}" auth status 2>&1)"
      AUTH_STATUS_EXIT=$?
      set -e
      if [[ ${AUTH_STATUS_EXIT} -ne 0 ]]; then
        CLAUDE_EXIT_CODE=40
        CLAUDE_SUMMARY="Claude auth status check failed"
        CLAUDE_ERROR="${AUTH_STATUS_OUTPUT}"
        PRECHECK_STATUS="failed"
        PRECHECK_REASON="auth_status_failed"
      fi
    fi

    if [[ ${CLAUDE_EXIT_CODE} -eq 0 ]]; then
      AUTH_LOGGED_IN="$("${PY_BIN}" - "${AUTH_STATUS_OUTPUT}" <<'PY'
import json
import sys

raw = sys.argv[1]
try:
    payload = json.loads(raw)
except json.JSONDecodeError:
    print("invalid")
    raise SystemExit(0)
print("true" if payload.get("loggedIn") else "false")
PY
)"
      if [[ "${AUTH_LOGGED_IN}" == "invalid" ]]; then
        CLAUDE_EXIT_CODE=40
        CLAUDE_SUMMARY="Claude auth status output was not valid JSON"
        CLAUDE_ERROR="${AUTH_STATUS_OUTPUT}"
        PRECHECK_STATUS="failed"
        PRECHECK_REASON="auth_status_invalid"
      elif [[ "${AUTH_LOGGED_IN}" != "true" ]]; then
        CLAUDE_EXIT_CODE=40
        CLAUDE_SUMMARY="Claude CLI is not logged in"
        CLAUDE_ERROR="${CLAUDE_SUMMARY}"
        PRECHECK_STATUS="failed"
        PRECHECK_REASON="auth_missing"
      else
        PRECHECK_STATUS="passed"
        PRECHECK_REASON="local_checks_ok"
      fi
    fi

    case "${CLAUDE_CODE_PERMISSION_MODE}" in
      auto)
        MODE_CANDIDATES=(acceptEdits bypassPermissions)
        ;;
      acceptEdits)
        MODE_CANDIDATES=(acceptEdits)
        ;;
      bypassPermissions)
        MODE_CANDIDATES=(bypassPermissions)
        ;;
      *)
        MODE_CANDIDATES=()
        if [[ ${CLAUDE_EXIT_CODE} -eq 0 ]]; then
          CLAUDE_EXIT_CODE=40
          CLAUDE_SUMMARY="Unsupported CLAUDE_CODE_PERMISSION_MODE: ${CLAUDE_CODE_PERMISSION_MODE}"
          CLAUDE_ERROR="${CLAUDE_SUMMARY}"
          PRECHECK_STATUS="failed"
          PRECHECK_REASON="invalid_mode"
        fi
        ;;
    esac

    if [[ ${CLAUDE_EXIT_CODE} -eq 0 ]]; then
      for mode in "${MODE_CANDIDATES[@]}"; do
        MODE_ATTEMPTS=$((MODE_ATTEMPTS + 1))
        : > "${CLAUDE_STDOUT_PATH}"
        : > "${CLAUDE_STDERR_PATH}"
        : > "${CLAUDE_JSON_PATH}"
        : > "${LAST_MESSAGE_PATH}"
        printf '%s\n' "${mode}" > "${MODE_PATH}"

        set +e
        (
          cd "${AEP_WORKSPACE}"
          "${CLAUDE_CMD_RESOLVED}" -p \
            --output-format json \
            --permission-mode "${mode}" \
            "${PROMPT}"
        ) >"${CLAUDE_JSON_PATH}" 2>"${CLAUDE_STDERR_PATH}"
        MODE_EXIT_CODE=$?
        set -e

        cp "${CLAUDE_JSON_PATH}" "${CLAUDE_STDOUT_PATH}"
        MODE_STDERR="$(cat "${CLAUDE_STDERR_PATH}")"
        MODE_STDOUT="$(cat "${CLAUDE_STDOUT_PATH}")"

        MODE_LAST_MESSAGE="$("${PY_BIN}" - "${CLAUDE_JSON_PATH}" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists() or not path.read_text(encoding="utf-8").strip():
    print("")
    raise SystemExit(0)
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except json.JSONDecodeError:
    print("")
    raise SystemExit(0)
print(payload.get("result", ""))
PY
)"
        printf '%s\n' "${MODE_LAST_MESSAGE}" > "${LAST_MESSAGE_PATH}"
        MODE_PERMISSION_DENIALS="$("${PY_BIN}" - "${CLAUDE_JSON_PATH}" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists() or not path.read_text(encoding="utf-8").strip():
    print("invalid")
    raise SystemExit(0)
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except json.JSONDecodeError:
    print("invalid")
    raise SystemExit(0)
denials = payload.get("permission_denials") or []
print(len(denials))
PY
)"

        MODE_COMBINED="${MODE_STDERR}
${MODE_STDOUT}
${MODE_LAST_MESSAGE}"

        ATTEMPTED_MODES_JSON="$("${PY_BIN}" - "${ATTEMPTED_MODES_JSON}" "${mode}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
payload.append(sys.argv[2])
print(json.dumps(payload, ensure_ascii=False))
PY
)"
        MODE_FAILURES_JSON="$("${PY_BIN}" - "${MODE_FAILURES_JSON}" "${mode}" "${MODE_EXIT_CODE}" "${MODE_COMBINED}" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
payload[sys.argv[2]] = {
    "exit_code": int(sys.argv[3]),
    "detail": sys.argv[4][:2000],
}
print(json.dumps(payload, ensure_ascii=False))
PY
)"

        if [[ ${MODE_EXIT_CODE} -eq 0 ]]; then
          if [[ "${MODE_PERMISSION_DENIALS}" == "invalid" ]]; then
            SELECTED_MODE="${mode}"
            CLAUDE_EXIT_CODE=40
            CLAUDE_SUMMARY="Claude Code returned invalid JSON"
            CLAUDE_ERROR="${MODE_COMBINED}"
            PRECHECK_STATUS="failed"
            PRECHECK_REASON="output_invalid"
            break
          fi
          if (( MODE_PERMISSION_DENIALS > 0 )) && [[ "${CLAUDE_CODE_PERMISSION_MODE}" == "auto" ]] && [[ "${mode}" == "acceptEdits" ]]; then
            reset_workspace_from_baseline
            continue
          fi
          SELECTED_MODE="${mode}"
          CLAUDE_EXIT_CODE=0
          CLAUDE_SUMMARY="Claude Code adapter finished in ${mode}"
          CLAUDE_ERROR=""
          break
        fi

        if is_auth_error "${MODE_COMBINED}"; then
          SELECTED_MODE="${mode}"
          CLAUDE_EXIT_CODE=40
          CLAUDE_SUMMARY="Claude Code auth check failed in ${mode}"
          CLAUDE_ERROR="${MODE_COMBINED}"
          PRECHECK_STATUS="failed"
          PRECHECK_REASON="auth_runtime_failed"
          break
        fi

        if [[ "${CLAUDE_CODE_PERMISSION_MODE}" == "auto" ]] && [[ "${mode}" == "acceptEdits" ]]; then
          reset_workspace_from_baseline
          continue
        fi

        SELECTED_MODE="${mode}"
        CLAUDE_EXIT_CODE=${MODE_EXIT_CODE}
        CLAUDE_SUMMARY="Claude Code adapter failed in ${mode}"
        CLAUDE_ERROR="${MODE_COMBINED}"
        break
      done

      if [[ ${CLAUDE_EXIT_CODE} -ne 0 && "${SELECTED_MODE}" == "dry_run" ]]; then
        SELECTED_MODE="none"
      fi
    fi
  fi
fi

if [[ -s "${CLAUDE_STDOUT_PATH}" ]]; then
  cat "${CLAUDE_STDOUT_PATH}"
fi
if [[ -s "${CLAUDE_STDERR_PATH}" ]]; then
  cat "${CLAUDE_STDERR_PATH}" >&2
fi

"${PY_BIN}" - "${PREFLIGHT_PATH}" "${PRECHECK_STATUS}" "${PRECHECK_REASON}" "${SELECTED_MODE}" "${ATTEMPTED_MODES_JSON}" "${MODE_FAILURES_JSON}" "${CLAUDE_CODE_BIN}" "${CLAUDE_CODE_DRY_RUN}" "${CLAUDE_CODE_PERMISSION_MODE}" "${CLAUDE_CODE_AUTH_STATUS_FILE}" "${MODE_ATTEMPTS}" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = {
    "status": sys.argv[2],
    "reason": sys.argv[3],
    "selected_mode": sys.argv[4],
    "attempted_modes": json.loads(sys.argv[5]),
    "mode_failures": json.loads(sys.argv[6]),
    "claude_code_bin": sys.argv[7],
    "dry_run": sys.argv[8] == "1",
    "requested_mode": sys.argv[9],
    "auth_status_file": sys.argv[10] or None,
    "mode_attempts": int(sys.argv[11]),
}
path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
PY

"${PY_BIN}" - "${AEP_BASELINE}" "${AEP_WORKSPACE}" "${AEP_ARTIFACT_DIR}" "${AEP_RESULT_PATH}" "${RUN_ID}" "${AGENT_ID}" "${ATTEMPT}" "${CLAUDE_EXIT_CODE}" "${LAST_MESSAGE_PATH}" "${PROMPT_PATH}" "${CLAUDE_STDOUT_PATH}" "${CLAUDE_STDERR_PATH}" "${CLAUDE_JSON_PATH}" "${PREFLIGHT_PATH}" "${MODE_PATH}" "${CLAUDE_SUMMARY}" "${CLAUDE_ERROR}" "${MODE_ATTEMPTS}" <<'PY'
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
last_message_path = Path(sys.argv[9])
prompt_path = Path(sys.argv[10])
stdout_path = Path(sys.argv[11])
stderr_path = Path(sys.argv[12])
json_path = Path(sys.argv[13])
preflight_path = Path(sys.argv[14])
mode_path = Path(sys.argv[15])
precomputed_summary = sys.argv[16]
precomputed_error = sys.argv[17]
mode_attempts = int(sys.argv[18])

def collect_files(root: Path) -> set[str]:
    if not root.exists():
        return set()
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}

def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()

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

last_message = read_text(last_message_path)
stderr_text = read_text(stderr_path)
stdout_text = read_text(stdout_path)

artifacts = []
for name, kind, path in (
    ("claude_code_prompt", "plan", prompt_path),
    ("claude_code_last_message", "report", last_message_path),
    ("claude_code_stdout", "log", stdout_path),
    ("claude_code_stderr", "log", stderr_path),
    ("claude_code_output_json", "report", json_path),
    ("claude_code_preflight", "report", preflight_path),
    ("claude_code_mode", "report", mode_path),
):
    if path.exists():
        artifacts.append(
            {
                "name": name,
                "kind": kind,
                "uri": str(path),
                "sha256": None,
            }
        )

if exit_code == 0:
    status = "succeeded"
    recommended = "promote"
    summary = last_message or precomputed_summary or "Claude Code adapter finished"
    error = None
elif exit_code in {40, 127}:
    status = "contract_error"
    recommended = "reject"
    summary = precomputed_summary or f"Claude Code adapter contract failed with {exit_code}"
    error = precomputed_error or stderr_text or stdout_text or summary
else:
    status = "failed"
    recommended = "fallback"
    summary = precomputed_summary or f"Claude Code adapter exited with {exit_code}"
    error = precomputed_error or stderr_text or stdout_text or summary

payload = {
    "protocol_version": "aep/v0",
    "run_id": run_id,
    "agent_id": agent_id,
    "attempt": attempt,
    "status": status,
    "summary": summary[:500],
    "changed_paths": changed,
    "output_artifacts": artifacts,
    "metrics": {
        "duration_ms": 0,
        "steps": 1,
        "commands": mode_attempts,
        "prompt_tokens": None,
        "completion_tokens": None,
    },
    "recommended_action": recommended,
    "error": error[:2000] if error else None,
}

result_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
PY

if [[ ${CLAUDE_EXIT_CODE} -eq 0 ]]; then
  exit 0
fi
if [[ ${CLAUDE_EXIT_CODE} -eq 40 || ${CLAUDE_EXIT_CODE} -eq 127 ]]; then
  exit 40
fi
exit 20
