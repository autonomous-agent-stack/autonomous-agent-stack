#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

PROMPT="${*:-${OPENHANDS_TASK:-}}"
RUNTIME="${OPENHANDS_RUNTIME:-ai-lab}"
DRY_RUN="${OPENHANDS_DRY_RUN:-0}"
WORKSPACE="${OPENHANDS_WORKSPACE:-${REPO_ROOT}}"
AUDIT_DIR="${OPENHANDS_AUDIT_DIR:-${REPO_ROOT}/logs/audit/openhands/manual}"
AUDIT_FILE="${OPENHANDS_AUDIT_FILE:-${AUDIT_DIR}/compliance.json}"
MAX_FILES_PER_STEP="${OPENHANDS_MAX_FILES_PER_STEP:-3}"
OPENHANDS_CMD="${OPENHANDS_CMD:-}"
OPENHANDS_CMD_TEMPLATE="${OPENHANDS_CMD_TEMPLATE:-}"

if [[ -z "${PROMPT}" ]]; then
  echo "[openhands] missing task prompt" >&2
  exit 40
fi

mkdir -p "${AUDIT_DIR}" "$(dirname "${AUDIT_FILE}")"
PROMPT_FILE="${AUDIT_DIR}/prompt.txt"
printf '%s\n' "${PROMPT}" > "${PROMPT_FILE}"

if [[ -z "${OPENHANDS_CMD_TEMPLATE}" ]]; then
  if [[ -z "${OPENHANDS_CMD}" ]]; then
    if [[ "${DRY_RUN}" == "1" ]]; then
      OPENHANDS_CMD="openhands"
    else
      echo "[openhands] OPENHANDS_CMD or OPENHANDS_CMD_TEMPLATE is required for real execution" >&2
      exit 127
    fi
  fi
  OPENHANDS_CMD_TEMPLATE='${OPENHANDS_CMD} "${OPENHANDS_PROMPT}"'
fi

quote_cmd() {
  python3 - "$@" <<'PY'
import shlex
import sys

print(" ".join(shlex.quote(item) for item in sys.argv[1:]))
PY
}

repo_relative_path() {
  local host_path="$1"
  local absolute
  absolute="$(python3 -c 'from pathlib import Path; import sys; print(Path(sys.argv[1]).resolve())' "${host_path}")"
  case "${absolute}" in
    "${REPO_ROOT}")
      printf '/workspace'
      ;;
    "${REPO_ROOT}"/*)
      printf '/workspace/%s' "${absolute#${REPO_ROOT}/}"
      ;;
    *)
      echo "[openhands] path is outside repo root and cannot be mounted into ai-lab: ${absolute}" >&2
      exit 40
      ;;
  esac
}

run_host() {
  local shell_cmd
  shell_cmd='mkdir -p "${OPENHANDS_AUDIT_DIR}" && eval "${OPENHANDS_CMD_TEMPLATE}"'
  local -a cmd=(
    env
    "OPENHANDS_PROMPT=${PROMPT}"
    "OPENHANDS_PROMPT_FILE=${PROMPT_FILE}"
    "OPENHANDS_WORKSPACE=${WORKSPACE}"
    "OPENHANDS_AUDIT_DIR=${AUDIT_DIR}"
    "OPENHANDS_AUDIT_FILE=${AUDIT_FILE}"
    "OPENHANDS_MAX_FILES_PER_STEP=${MAX_FILES_PER_STEP}"
    "OPENHANDS_CMD=${OPENHANDS_CMD}"
    "OPENHANDS_CMD_TEMPLATE=${OPENHANDS_CMD_TEMPLATE}"
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
  local extra_volume
  local shell_cmd

  container_audit_dir="$(repo_relative_path "${AUDIT_DIR}")"
  container_audit_file="$(repo_relative_path "${AUDIT_FILE}")"
  container_prompt_file="$(repo_relative_path "${PROMPT_FILE}")"
  extra_volume="${WORKSPACE}:/opt/workspace:rw"
  shell_cmd='mkdir -p "${OPENHANDS_AUDIT_DIR}" && eval "${OPENHANDS_CMD_TEMPLATE}"'

  local -a cmd=(
    "${REPO_ROOT}/scripts/launch_ai_lab.sh"
    run
    env
    "OPENHANDS_PROMPT=${PROMPT}"
    "OPENHANDS_PROMPT_FILE=${container_prompt_file}"
    "OPENHANDS_WORKSPACE=/opt/workspace"
    "OPENHANDS_AUDIT_DIR=${container_audit_dir}"
    "OPENHANDS_AUDIT_FILE=${container_audit_file}"
    "OPENHANDS_MAX_FILES_PER_STEP=${MAX_FILES_PER_STEP}"
    "OPENHANDS_CMD=${OPENHANDS_CMD}"
    "OPENHANDS_CMD_TEMPLATE=${OPENHANDS_CMD_TEMPLATE}"
    /bin/bash -lc "${shell_cmd}"
  )

  if [[ "${DRY_RUN}" == "1" ]]; then
    printf 'EXTRA_VOLUME=%s ' "$(quote_cmd "${extra_volume}")"
    quote_cmd "${cmd[@]}"
    return 0
  fi

  EXTRA_VOLUME="${extra_volume}" "${cmd[@]}"
}

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
