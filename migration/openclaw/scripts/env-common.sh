#!/usr/bin/env bash

load_shared_env_files() {
  local project_root="$1"
  local root_dir="$2"
  local target_name="$3"
  eval "${target_name}=()"
  eval "${target_name}+=(\"\${project_root}/.env\" \"\${project_root}/.env.local\" \"\${root_dir}/.env.local\")"

  local env_file
  eval "set -- \"\${${target_name}[@]}\""
  for env_file in "$@"; do
    if [[ -f "${env_file}" ]]; then
      set -a
      source "${env_file}"
      set +a
    fi
  done
}

warn_env_conflicts() {
  local env_files_name="$1"
  shift
  local vars=("$@")
  local var_name
  local env_file
  local raw_line
  local parsed_value
  local seen_value
  local seen_file

  for var_name in "${vars[@]}"; do
    seen_value=""
    seen_file=""
    eval "set -- \"\${${env_files_name}[@]}\""
    for env_file in "$@"; do
      [[ -f "${env_file}" ]] || continue
      raw_line="$(grep -E "^[[:space:]]*(export[[:space:]]+)?${var_name}=" "${env_file}" | tail -n 1 || true)"
      [[ -n "${raw_line}" ]] || continue
      parsed_value="${raw_line#*=}"
      parsed_value="${parsed_value%%#*}"
      parsed_value="${parsed_value#"${parsed_value%%[![:space:]]*}"}"
      parsed_value="${parsed_value%"${parsed_value##*[![:space:]]}"}"
      if [[ "${parsed_value}" == \"*\" && "${parsed_value}" == *\" ]]; then
        parsed_value="${parsed_value:1:${#parsed_value}-2}"
      elif [[ "${parsed_value}" == \'*\' && "${parsed_value}" == *\' ]]; then
        parsed_value="${parsed_value:1:${#parsed_value}-2}"
      fi
      if [[ -z "${seen_file}" ]]; then
        seen_value="${parsed_value}"
        seen_file="${env_file}"
        continue
      fi
      if [[ "${parsed_value}" != "${seen_value}" ]]; then
        echo "[env-warning] ${var_name} conflict: ${seen_file}='${seen_value}' vs ${env_file}='${parsed_value}'"
      fi
    done
  done
}

print_effective_env_values() {
  local vars=("$@")
  local var_name
  local value
  for var_name in "${vars[@]}"; do
    value="${!var_name:-}"
    if [[ -n "${value}" ]]; then
      echo "[env] ${var_name}=${value}"
    else
      echo "[env] ${var_name}=<unset>"
    fi
  done
}
