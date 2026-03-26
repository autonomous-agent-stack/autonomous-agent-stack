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
  else
    docker compose "$@"
  fi
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
}

workspace_quota_info() {
  if command -v df >/dev/null 2>&1; then
    df -h "${WORKSPACE_DIR}" 2>/dev/null | tail -n 1 || true
  fi
}

run_guardrails() {
  "${REPO_ROOT}/scripts/check_ai_lab_guardrails.sh"
}

start_stack() {
  log "starting compose stack"
  compose_cmd -f "${COMPOSE_FILE}" up -d
}

enter_shell() {
  log "entering container shell"
  compose_cmd -f "${COMPOSE_FILE}" exec ai-lab /bin/sh
}

run_command() {
  shift
  if [[ "$#" -eq 0 ]]; then
    die "no command provided for run mode"
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
  scripts/launch_ai_lab.sh [shell|up|down|status|run -- <cmd...>]

Modes:
  shell   Run guardrails, start stack, then open an interactive shell
  up      Run guardrails and start stack in detached mode
  down    Stop the stack
  status  Show compose status
  run     Run a one-shot command inside the container

Examples:
  ./scripts/launch_ai_lab.sh
  ./scripts/launch_ai_lab.sh up
  ./scripts/launch_ai_lab.sh run -- python -V
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
