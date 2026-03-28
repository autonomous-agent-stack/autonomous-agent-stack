#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MODE="${1:-shell}"

ENV_FILE="${ENV_FILE:-${REPO_ROOT}/ai_lab.env}"
DEFAULT_ENV_FILE="${REPO_ROOT}/ai_lab.env.example"
OVERRIDE_COMPOSE_DIR="${COMPOSE_DIR:-}"
OVERRIDE_COMPOSE_FILE="${COMPOSE_FILE:-}"
OVERRIDE_WORKSPACE_DIR="${WORKSPACE_DIR:-}"
OVERRIDE_LOG_DIR="${LOG_DIR:-}"
OVERRIDE_CACHE_DIR="${CACHE_DIR:-}"
OVERRIDE_LAB_USER="${LAB_USER:-}"
OVERRIDE_AUTO_OPEN_DOCKER="${AUTO_OPEN_DOCKER:-}"
OVERRIDE_IMAGE_TAG="${AI_LAB_IMAGE_TAG:-}"
OVERRIDE_FORCE_DOCKER_RUN="${AI_LAB_FORCE_DOCKER_RUN:-}"
OVERRIDE_HOST_MOUNT_ROOT="${AI_LAB_HOST_MOUNT_ROOT:-}"

load_env_file() {
  local file="$1"
  if [[ -f "${file}" ]]; then
    # shellcheck disable=SC1090
    set -a
    . "${file}"
    set +a
  fi
}

load_env_file "${DEFAULT_ENV_FILE}"
load_env_file "${ENV_FILE}"

COMPOSE_DIR="${OVERRIDE_COMPOSE_DIR:-${COMPOSE_DIR:-${REPO_ROOT}/sandbox/ai-lab}}"
COMPOSE_FILE="${OVERRIDE_COMPOSE_FILE:-${COMPOSE_FILE:-${COMPOSE_DIR}/docker-compose.yml}}"
WORKSPACE_DIR="${OVERRIDE_WORKSPACE_DIR:-${WORKSPACE_DIR:-/Users/ai_lab/workspace}}"
LOG_DIR="${OVERRIDE_LOG_DIR:-${LOG_DIR:-/Users/ai_lab/logs}}"
CACHE_DIR="${OVERRIDE_CACHE_DIR:-${CACHE_DIR:-/Users/ai_lab/.cache}}"
LAB_USER="${OVERRIDE_LAB_USER:-${LAB_USER:-ai_lab}}"
AUTO_OPEN_DOCKER="${OVERRIDE_AUTO_OPEN_DOCKER:-${AUTO_OPEN_DOCKER:-1}}"
IMAGE_TAG="${OVERRIDE_IMAGE_TAG:-${AI_LAB_IMAGE_TAG:-ai-lab-local:dev}}"
FORCE_DOCKER_RUN="${OVERRIDE_FORCE_DOCKER_RUN:-${AI_LAB_FORCE_DOCKER_RUN:-0}}"
HOST_MOUNT_ROOT="${OVERRIDE_HOST_MOUNT_ROOT:-${AI_LAB_HOST_MOUNT_ROOT:-${WORKSPACE_DIR}}}"
OPENHANDS_HOME_DIR="${LOG_DIR}/openhands-home"

if [[ "${LAB_USER}" != "ai_lab" ]]; then
  WORKSPACE_DIR="${WORKSPACE_DIR:-/Users/${LAB_USER}/workspace}"
  LOG_DIR="${LOG_DIR:-/Users/${LAB_USER}/logs}"
  CACHE_DIR="${CACHE_DIR:-/Users/${LAB_USER}/.cache}"
fi

if [[ -t 1 ]]; then
  C_RESET=$'\033[0m'
  C_GREEN=$'\033[32m'
  C_YELLOW=$'\033[33m'
  C_RED=$'\033[31m'
  C_CYAN=$'\033[36m'
else
  C_RESET=""
  C_GREEN=""
  C_YELLOW=""
  C_RED=""
  C_CYAN=""
fi

log() {
  printf '%s[ai-lab]%s %s\n' "${C_CYAN}" "${C_RESET}" "$*"
}

ok() {
  printf '%s[ok]%s %s\n' "${C_GREEN}" "${C_RESET}" "$*"
}

warn() {
  printf '%s[warn]%s %s\n' "${C_YELLOW}" "${C_RESET}" "$*"
}

die() {
  printf '%s[error]%s %s\n' "${C_RED}" "${C_RESET}" "$*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing command: $1"
}

docker_ready() {
  python3 - <<'PY' >/dev/null 2>&1
import subprocess
import sys

try:
    completed = subprocess.run(
        ["docker", "info"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=3,
        check=False,
    )
except Exception:
    sys.exit(1)

sys.exit(0 if completed.returncode == 0 else 1)
PY
}

ensure_docker() {
  need_cmd docker
  if docker_ready; then
    return
  fi

  if [[ "${AUTO_OPEN_DOCKER}" == "1" ]] && [[ "$(uname -s)" == "Darwin" ]]; then
    log "Docker daemon not ready; trying to open Docker Desktop"
    open -a Docker >/dev/null 2>&1 || true
    for _ in {1..30}; do
      if docker_ready; then
        return
      fi
      sleep 2
    done
  fi

  die "Docker daemon is not ready. Start Docker Desktop first."
}

compose_cmd() {
  if command -v docker-compose >/dev/null 2>&1; then
    need_cmd docker-compose
    docker-compose "$@"
  elif docker compose version >/dev/null 2>&1; then
    docker compose "$@"
  else
    die "docker compose is not available"
  fi
}

compose_available() {
  if command -v docker-compose >/dev/null 2>&1; then
    return 0
  fi

  docker compose version >/dev/null 2>&1
}

use_direct_docker() {
  if [[ "${FORCE_DOCKER_RUN}" == "1" ]]; then
    return 0
  fi

  if compose_available; then
    return 1
  fi

  return 0
}

ensure_workspace() {
  if [[ -d "${WORKSPACE_DIR}" ]]; then
    return
  fi

  log "workspace not found; attempting guided setup"
  if [[ -x "${REPO_ROOT}/scripts/setup_ai_lab.sh" ]]; then
    if [[ -t 0 ]]; then
      read -r -p "Run ai_lab setup now? [Y/n] " answer
      case "${answer:-Y}" in
        [Nn]*) die "workspace missing: ${WORKSPACE_DIR}" ;;
      esac
    fi

    sudo "${REPO_ROOT}/scripts/setup_ai_lab.sh"
    if [[ -d "${WORKSPACE_DIR}" ]]; then
      return
    fi
  fi

  die "workspace not found: ${WORKSPACE_DIR}. Run scripts/setup_ai_lab.sh first."
}

ensure_launch_prereqs() {
  ensure_docker
  ensure_workspace
  mkdir -p "${CACHE_DIR}" "${LOG_DIR}" "${OPENHANDS_HOME_DIR}" "${WORKSPACE_DIR}"
}

workspace_quota_info() {
  if command -v df >/dev/null 2>&1; then
    df -h "${WORKSPACE_DIR}" 2>/dev/null | tail -n 1 || true
  fi
}

run_guardrails() {
  "${REPO_ROOT}/scripts/check_ai_lab_guardrails.sh"
}

append_env_passthrough() {
  local name="$1"
  if [[ -n "${!name+x}" ]]; then
    DIRECT_DOCKER_ARGS+=("-e" "${name}")
  fi
}

build_direct_image() {
  log "building docker image ${IMAGE_TAG}"
  docker build -t "${IMAGE_TAG}" -f "${COMPOSE_DIR}/Dockerfile" "${COMPOSE_DIR}"
}

direct_docker_base_args() {
  DIRECT_DOCKER_ARGS=(
    docker run --rm
    --platform linux/arm64
    --workdir /workspace
    --user root
    --tmpfs /tmp:size=2g,mode=1777
    --mount "type=bind,src=${HOST_MOUNT_ROOT},dst=/workspace,readonly"
    --mount "type=bind,src=${CACHE_DIR},dst=/root/.cache"
    --mount "type=bind,src=${OPENHANDS_HOME_DIR},dst=/root/.openhands"
    -e HOME=/root
    -e PYTHONDONTWRITEBYTECODE=1
    -e PYTHONUNBUFFERED=1
  )

  append_env_passthrough TELEGRAM_BOT_TOKEN
  append_env_passthrough TELEGRAM_CHAT_ID
  append_env_passthrough GITHUB_TOKEN
  append_env_passthrough LLM_API_KEY
  append_env_passthrough LLM_MODEL
  append_env_passthrough LLM_BASE_URL
}

start_stack() {
  if use_direct_docker; then
    build_direct_image
    ok "docker image ready (compose bypassed)"
    return
  fi
  log "starting compose stack"
  compose_cmd -f "${COMPOSE_FILE}" up -d
}

enter_shell() {
  if use_direct_docker; then
    local -a cmd=()
    direct_docker_base_args
    cmd=("${DIRECT_DOCKER_ARGS[@]}")
    cmd+=("${IMAGE_TAG}" /bin/sh)
    log "entering container shell (compose bypassed)"
    "${cmd[@]}"
    return
  fi
  log "entering container shell"
  compose_cmd -f "${COMPOSE_FILE}" exec ai-lab /bin/sh
}

run_command() {
  shift
  if [[ "$#" -eq 0 ]]; then
    die "no command provided for run mode"
  fi

  if use_direct_docker; then
    local -a cmd=()
    direct_docker_base_args
    cmd=("${DIRECT_DOCKER_ARGS[@]}")
    if [[ -n "${EXTRA_VOLUME:-}" ]]; then
      cmd+=("-v" "${EXTRA_VOLUME}")
    fi
    cmd+=("${IMAGE_TAG}" "$@")
    build_direct_image
    log "running command in container without compose: $*"
    "${cmd[@]}"
    return
  fi

  log "running command in container: $*"
  local compose_args=("-f" "${COMPOSE_FILE}" "run" "--rm")
  if [[ -n "${EXTRA_VOLUME:-}" ]]; then
    compose_args+=("--volume" "${EXTRA_VOLUME}")
  fi
  compose_args+=("ai-lab")
  compose_cmd "${compose_args[@]}" "$@"
}

status() {
  if use_direct_docker; then
    if docker image inspect "${IMAGE_TAG}" >/dev/null 2>&1; then
      ok "docker image available: ${IMAGE_TAG}"
    else
      warn "docker image missing: ${IMAGE_TAG}"
    fi
    return
  fi
  compose_cmd -f "${COMPOSE_FILE}" ps
}

print_readiness() {
  local quota_line
  quota_line="$(workspace_quota_info)"
  ok "environment ready"
  printf '  user: %s\n' "${LAB_USER}"
  printf '  workspace: %s\n' "${WORKSPACE_DIR}"
  if [[ -n "${quota_line}" ]]; then
    printf '  quota: %s\n' "${quota_line}"
  fi
}

stop_stack() {
  compose_cmd -f "${COMPOSE_FILE}" down
}

usage() {
  cat <<'EOF'
Usage:
  scripts/launch_ai_lab.sh [shell|up|down|status|run <cmd...>]

Modes:
  shell   Run guardrails, start stack, then open an interactive shell
  up      Run guardrails and start stack in detached mode
  down    Stop the stack
  status  Show compose status
  run     Run a one-shot command inside the container

Examples:
  ./scripts/launch_ai_lab.sh
  ./scripts/launch_ai_lab.sh up
  ./scripts/launch_ai_lab.sh run python -V
EOF
}

main() {
  ensure_launch_prereqs
  run_guardrails
  print_readiness

  case "${MODE}" in
    shell)
      start_stack
      enter_shell
      ;;
    up)
      start_stack
      status
      ;;
    down)
      stop_stack
      ;;
    status)
      status
      ;;
    run)
      run_command "$@"
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      die "unknown mode: ${MODE}"
      ;;
  esac
}

main "$@"
