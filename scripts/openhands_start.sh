#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OPENHANDS_ENV_FILE="${OPENHANDS_ENV_FILE:-${REPO_ROOT}/ai_lab.env}"

load_env_file() {
  local file="$1"
  if [[ -f "${file}" ]]; then
    # shellcheck disable=SC1090
    set -a
    . "${file}"
    set +a
  fi
}

load_env_file "${OPENHANDS_ENV_FILE}"

PROMPT="${*:-${OPENHANDS_TASK:-}}"
RUNTIME="${OPENHANDS_RUNTIME:-ai-lab}"
DRY_RUN="${OPENHANDS_DRY_RUN:-0}"
WORKSPACE="${OPENHANDS_WORKSPACE:-${REPO_ROOT}}"
if [[ -n "${OPENHANDS_AUDIT_DIR:-}" ]]; then
  AUDIT_DIR="${OPENHANDS_AUDIT_DIR}"
elif [[ "${RUNTIME}" == "ai-lab" ]]; then
  AUDIT_DIR="${WORKSPACE}/.openhands-audit"
else
  AUDIT_DIR="${REPO_ROOT}/logs/audit/openhands/manual"
fi
AUDIT_FILE="${OPENHANDS_AUDIT_FILE:-${AUDIT_DIR}/compliance.json}"
MAX_FILES_PER_STEP="${OPENHANDS_MAX_FILES_PER_STEP:-3}"
OPENHANDS_CMD="${OPENHANDS_CMD:-}"
OPENHANDS_CMD_TEMPLATE="${OPENHANDS_CMD_TEMPLATE:-}"
OPENHANDS_HEADLESS="${OPENHANDS_HEADLESS:-1}"
OPENHANDS_JSON="${OPENHANDS_JSON:-0}"
OPENHANDS_EXPERIMENTAL="${OPENHANDS_EXPERIMENTAL:-1}"
OPENHANDS_SANDBOX_PROVIDER="${OPENHANDS_SANDBOX_PROVIDER:-process}"
OPENHANDS_SANDBOX_VOLUMES="${OPENHANDS_SANDBOX_VOLUMES:-${WORKSPACE}:/workspace:rw}"
OPENHANDS_PERSISTENCE_DIR="${OPENHANDS_PERSISTENCE_DIR:-${AUDIT_DIR}/state}"
OPENHANDS_LOCAL_BIN="${OPENHANDS_LOCAL_BIN:-${REPO_ROOT}/.masfactory_runtime/tools/openhands-cli-py312/bin/openhands}"
OPENHANDS_CONTAINER_BIN="${OPENHANDS_CONTAINER_BIN:-openhands}"
OPENHANDS_BOOTSTRAP_PYTHON="${OPENHANDS_BOOTSTRAP_PYTHON:-}"
OPENHANDS_HOME_ROOT="${OPENHANDS_HOME_ROOT:-${REPO_ROOT}/.masfactory_runtime/tools/openhands-home}"
OPENHANDS_CONFIG_DIR="${OPENHANDS_CONFIG_DIR:-}"
OPENHANDS_CONTAINER_WORKSPACE="${OPENHANDS_CONTAINER_WORKSPACE:-/opt/workspace}"
OPENHANDS_RUN_AS_USER="${OPENHANDS_RUN_AS_USER:-nobody}"
OPENHANDS_RUN_AS_HOME="${OPENHANDS_RUN_AS_HOME:-/tmp/openhands-home}"
OPENHANDS_RUN_AS_ENABLED="${OPENHANDS_RUN_AS_ENABLED:-1}"

if [[ -z "${PROMPT}" ]]; then
  echo "[openhands] missing task prompt" >&2
  exit 40
fi

if [[ -z "${OPENHANDS_CONFIG_DIR}" ]]; then
  if [[ "${RUNTIME}" == "ai-lab" ]]; then
    OPENHANDS_CONFIG_DIR="${LOG_DIR:-${REPO_ROOT}/logs}/openhands-home"
  else
    OPENHANDS_CONFIG_DIR="${OPENHANDS_HOME_ROOT}/.openhands"
  fi
fi

if [[ "${RUNTIME}" == "host" ]]; then
  OPENHANDS_HOME_ROOT="$(dirname "${OPENHANDS_CONFIG_DIR}")"
fi

if [[ -z "${OPENHANDS_BOOTSTRAP_PYTHON}" ]]; then
  if [[ -x "${OPENHANDS_LOCAL_BIN%/*}/python" ]]; then
    OPENHANDS_BOOTSTRAP_PYTHON="${OPENHANDS_LOCAL_BIN%/*}/python"
  else
    OPENHANDS_BOOTSTRAP_PYTHON="${PYTHON_BIN:-python3}"
  fi
fi

OPENHANDS_SETTINGS_PATH="${OPENHANDS_SETTINGS_PATH:-${OPENHANDS_CONFIG_DIR}/agent_settings.json}"

mkdir -p "${AUDIT_DIR}" "$(dirname "${AUDIT_FILE}")"
PROMPT_FILE="${AUDIT_DIR}/prompt.txt"
printf '%s\n' "${PROMPT}" > "${PROMPT_FILE}"

if [[ -z "${OPENHANDS_CMD_TEMPLATE}" ]]; then
  if [[ -z "${OPENHANDS_CMD}" ]]; then
    if [[ "${RUNTIME}" == "ai-lab" ]]; then
      OPENHANDS_CMD="${OPENHANDS_CONTAINER_BIN}"
    elif [[ -x "${OPENHANDS_LOCAL_BIN}" ]]; then
      OPENHANDS_CMD="${OPENHANDS_LOCAL_BIN}"
    elif command -v openhands >/dev/null 2>&1; then
      OPENHANDS_CMD="$(command -v openhands)"
    elif [[ "${DRY_RUN}" == "1" ]]; then
      OPENHANDS_CMD="openhands"
    else
      echo "[openhands] OPENHANDS_CMD or OPENHANDS_CMD_TEMPLATE is required for real execution" >&2
      exit 127
    fi
  fi
  if [[ "${OPENHANDS_HEADLESS}" == "1" ]]; then
    OPENHANDS_CMD_TEMPLATE='RUNTIME="${OPENHANDS_SANDBOX_PROVIDER}" SANDBOX_VOLUMES="${OPENHANDS_SANDBOX_VOLUMES}" OH_PERSISTENCE_DIR="${OPENHANDS_PERSISTENCE_DIR}" "${OPENHANDS_CMD}"'
    if [[ "${OPENHANDS_EXPERIMENTAL}" == "1" ]]; then
      OPENHANDS_CMD_TEMPLATE+=' --exp'
    fi
    OPENHANDS_CMD_TEMPLATE+=' --headless'
    if [[ "${OPENHANDS_JSON}" == "1" ]]; then
      OPENHANDS_CMD_TEMPLATE+=' --json'
    fi
    OPENHANDS_CMD_TEMPLATE+=' -t "${OPENHANDS_PROMPT}"'
  else
    OPENHANDS_CMD_TEMPLATE='"${OPENHANDS_CMD}" "${OPENHANDS_PROMPT}"'
  fi
fi

quote_cmd() {
  python3 - "$@" <<'PY'
import shlex
import sys

print(" ".join(shlex.quote(item) for item in sys.argv[1:]))
PY
}

resolve_host_path() {
  local host_path="$1"
  python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "${host_path}"
}

container_path_for_host_path() {
  local host_path="$1"
  local absolute
  local repo_root
  local workspace_root

  absolute="$(resolve_host_path "${host_path}")"
  repo_root="$(resolve_host_path "${REPO_ROOT}")"
  workspace_root="$(resolve_host_path "${WORKSPACE}")"

  case "${absolute}" in
    "${workspace_root}")
      printf '/opt/workspace'
      ;;
    "${workspace_root}"/*)
      printf '/opt/workspace/%s' "${absolute#${workspace_root}/}"
      ;;
    "${repo_root}")
      printf '/workspace'
      ;;
    "${repo_root}"/*)
      printf '/workspace/%s' "${absolute#${repo_root}/}"
      ;;
    *)
      echo "[openhands] path is outside supported mount roots and cannot be mounted into ai-lab: ${absolute}" >&2
      exit 40
      ;;
  esac
}

host_mount_root_for_path() {
  local host_path="$1"
  local absolute
  local repo_root
  local workspace_root

  absolute="$(resolve_host_path "${host_path}")"
  repo_root="$(resolve_host_path "${REPO_ROOT}")"
  workspace_root="$(resolve_host_path "${WORKSPACE}")"

  case "${absolute}" in
    "${workspace_root}"|"${workspace_root}"/*)
      printf '%s' "${workspace_root}"
      ;;
    "${repo_root}"|"${repo_root}"/*)
      printf '%s' "${repo_root}"
      ;;
    *)
      echo "[openhands] path is outside supported mount roots and cannot be mounted into ai-lab: ${absolute}" >&2
      exit 40
      ;;
  esac
}

ensure_openhands_agent_settings() {
  if [[ "${DRY_RUN}" == "1" ]]; then
    return 0
  fi

  if [[ -f "${OPENHANDS_SETTINGS_PATH}" ]] && [[ "${OPENHANDS_FORCE_AGENT_SETTINGS:-0}" != "1" ]]; then
    return 0
  fi

  if [[ -z "${LLM_MODEL:-}" || -z "${LLM_API_KEY:-}" ]]; then
    echo "[openhands] missing LLM_MODEL or LLM_API_KEY for agent settings bootstrap" >&2
    exit 40
  fi

  if [[ ! -x "${OPENHANDS_BOOTSTRAP_PYTHON}" ]] && ! command -v "${OPENHANDS_BOOTSTRAP_PYTHON}" >/dev/null 2>&1; then
    echo "[openhands] bootstrap python not found: ${OPENHANDS_BOOTSTRAP_PYTHON}" >&2
    exit 127
  fi

  mkdir -p "${OPENHANDS_CONFIG_DIR}"

  "${OPENHANDS_BOOTSTRAP_PYTHON}" - "${OPENHANDS_SETTINGS_PATH}" "${LLM_MODEL}" "${LLM_API_KEY}" "${LLM_BASE_URL:-}" <<'PY'
import json
import sys
from pathlib import Path

from openhands.sdk import Agent, LLM
from openhands.tools.preset.default import get_default_tools

settings_path = Path(sys.argv[1])
model = sys.argv[2]
api_key = sys.argv[3]
base_url = sys.argv[4] or None

settings_path.parent.mkdir(parents=True, exist_ok=True)
agent = Agent(
    llm=LLM(model=model, api_key=api_key, base_url=base_url),
    tools=get_default_tools(enable_browser=False),
)
settings_path.write_text(
    json.dumps(agent.model_dump(context={"expose_secrets": True}), indent=2) + "\n",
    encoding="utf-8",
)
PY

  chmod 600 "${OPENHANDS_SETTINGS_PATH}" 2>/dev/null || true
}

run_host() {
  local shell_cmd
  shell_cmd='mkdir -p "${OPENHANDS_AUDIT_DIR}" "${OPENHANDS_PERSISTENCE_DIR}" && cd "${OPENHANDS_WORKSPACE}" && eval "${OPENHANDS_CMD_TEMPLATE}"'
  local -a cmd=(
    env
    "HOME=${OPENHANDS_HOME_ROOT}"
    "OPENHANDS_PROMPT=${PROMPT}"
    "OPENHANDS_PROMPT_FILE=${PROMPT_FILE}"
    "OPENHANDS_WORKSPACE=${WORKSPACE}"
    "OPENHANDS_AUDIT_DIR=${AUDIT_DIR}"
    "OPENHANDS_AUDIT_FILE=${AUDIT_FILE}"
    "OPENHANDS_MAX_FILES_PER_STEP=${MAX_FILES_PER_STEP}"
    "OPENHANDS_CMD=${OPENHANDS_CMD}"
    "OPENHANDS_CMD_TEMPLATE=${OPENHANDS_CMD_TEMPLATE}"
    "OPENHANDS_HEADLESS=${OPENHANDS_HEADLESS}"
    "OPENHANDS_JSON=${OPENHANDS_JSON}"
    "OPENHANDS_EXPERIMENTAL=${OPENHANDS_EXPERIMENTAL}"
    "OPENHANDS_SANDBOX_PROVIDER=${OPENHANDS_SANDBOX_PROVIDER}"
    "OPENHANDS_SANDBOX_VOLUMES=${OPENHANDS_SANDBOX_VOLUMES}"
    "OPENHANDS_PERSISTENCE_DIR=${OPENHANDS_PERSISTENCE_DIR}"
    "OPENHANDS_SETTINGS_PATH=${OPENHANDS_SETTINGS_PATH}"
    /bin/bash -lc "${shell_cmd}"
  )

  if [[ "${DRY_RUN}" == "1" ]]; then
    quote_cmd "${cmd[@]}"
    return 0
  fi

  "${cmd[@]}"
}

run_ai_lab() {
  local container_audit_dir
  local container_audit_file
  local container_prompt_file
  local container_persistence_dir
  local container_sandbox_volumes
  local extra_volume
  local host_mount_root
  local shell_cmd
  local persistence_token
  local runtime_settings_path
  local runtime_config_dir
  local runtime_home
  local runtime_script_path

  container_audit_dir="$(container_path_for_host_path "${AUDIT_DIR}")"
  container_audit_file="$(container_path_for_host_path "${AUDIT_FILE}")"
  container_prompt_file="$(container_path_for_host_path "${PROMPT_FILE}")"
  persistence_token="$(basename "$(dirname "${AUDIT_DIR}")")-$(basename "${AUDIT_DIR}")"
  container_persistence_dir="${OPENHANDS_CONTAINER_WORKSPACE}/.openhands-state/${persistence_token}"
  container_sandbox_volumes="${OPENHANDS_CONTAINER_WORKSPACE}:/workspace:rw"
  host_mount_root="$(host_mount_root_for_path "${PROMPT_FILE}")"
  extra_volume="${WORKSPACE}:${OPENHANDS_CONTAINER_WORKSPACE}:rw"
  runtime_home="${OPENHANDS_RUN_AS_HOME}"
  runtime_config_dir="${runtime_home}/.openhands"
  runtime_settings_path="${runtime_config_dir}/agent_settings.json"
  runtime_script_path="/tmp/openhands-run.sh"

  if [[ "${OPENHANDS_RUN_AS_ENABLED}" == "1" && "${OPENHANDS_RUN_AS_USER}" != "root" && -n "${OPENHANDS_RUN_AS_USER}" ]]; then
    shell_cmd='mkdir -p "${OPENHANDS_AUDIT_DIR}" "${OPENHANDS_PERSISTENCE_DIR}" "'"${runtime_config_dir}"'" && printf "%s\n" "set -euo pipefail" "cd \"\${OPENHANDS_WORKSPACE}\"" "eval \"\${OPENHANDS_CMD_TEMPLATE}\"" > "'"${runtime_script_path}"'" && chmod 755 "'"${runtime_script_path}"'" && cp /root/.openhands/agent_settings.json "'"${runtime_settings_path}"'" && chmod 777 "'"${runtime_home}"'" "'"${runtime_config_dir}"'" && chmod 644 "'"${runtime_settings_path}"'" && chmod o+rx /root && runuser -u "'"${OPENHANDS_RUN_AS_USER}"'" -- env HOME="'"${runtime_home}"'" PATH="/usr/local/bin:/usr/bin:/bin:/root/.local/bin" OPENHANDS_SETTINGS_PATH="'"${runtime_settings_path}"'" /bin/bash "'"${runtime_script_path}"'"'
  else
    shell_cmd='mkdir -p "${OPENHANDS_AUDIT_DIR}" "${OPENHANDS_PERSISTENCE_DIR}" && cd "${OPENHANDS_WORKSPACE}" && eval "${OPENHANDS_CMD_TEMPLATE}"'
  fi

  local -a cmd=(
    env
    "AI_LAB_HOST_MOUNT_ROOT=${host_mount_root}"
    "OPENHANDS_HOME_DIR=${OPENHANDS_CONFIG_DIR}"
    "${REPO_ROOT}/scripts/launch_ai_lab.sh"
    run
    env
    "OPENHANDS_PROMPT=${PROMPT}"
    "OPENHANDS_PROMPT_FILE=${container_prompt_file}"
    "OPENHANDS_WORKSPACE=${OPENHANDS_CONTAINER_WORKSPACE}"
    "OPENHANDS_AUDIT_DIR=${container_audit_dir}"
    "OPENHANDS_AUDIT_FILE=${container_audit_file}"
    "OPENHANDS_MAX_FILES_PER_STEP=${MAX_FILES_PER_STEP}"
    "OPENHANDS_CMD=${OPENHANDS_CMD}"
    "OPENHANDS_CMD_TEMPLATE=${OPENHANDS_CMD_TEMPLATE}"
    "OPENHANDS_HEADLESS=${OPENHANDS_HEADLESS}"
    "OPENHANDS_JSON=${OPENHANDS_JSON}"
    "OPENHANDS_EXPERIMENTAL=${OPENHANDS_EXPERIMENTAL}"
    "OPENHANDS_SANDBOX_PROVIDER=${OPENHANDS_SANDBOX_PROVIDER}"
    "OPENHANDS_SANDBOX_VOLUMES=${container_sandbox_volumes}"
    "OPENHANDS_PERSISTENCE_DIR=${container_persistence_dir}"
    "OPENHANDS_SETTINGS_PATH=${runtime_settings_path}"
    "OPENHANDS_RUN_AS_USER=${OPENHANDS_RUN_AS_USER}"
    "OPENHANDS_RUN_AS_HOME=${runtime_home}"
    "OPENHANDS_RUN_AS_ENABLED=${OPENHANDS_RUN_AS_ENABLED}"
    /bin/bash -lc "${shell_cmd}"
  )

  if [[ "${DRY_RUN}" == "1" ]]; then
    printf 'EXTRA_VOLUME=%s ' "$(quote_cmd "${extra_volume}")"
    quote_cmd "${cmd[@]}"
    return 0
  fi

  EXTRA_VOLUME="${extra_volume}" "${cmd[@]}"
}

mkdir -p "$(dirname "${OPENHANDS_CONFIG_DIR}")"
ensure_openhands_agent_settings

case "${RUNTIME}" in
  host)
    run_host
    ;;
  ai-lab)
    run_ai_lab
    ;;
  *)
    echo "[openhands] unsupported runtime: ${RUNTIME}" >&2
    exit 40
    ;;
esac
