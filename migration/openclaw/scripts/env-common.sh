#!/usr/bin/env bash

mask_secret_value() {
  local raw_value="$1"
  local length="${#raw_value}"
  if [[ "${length}" -le 8 ]]; then
    printf '***'
    return
  fi
  printf '%s...%s' "${raw_value:0:4}" "${raw_value:length-4:4}"
}

is_sensitive_env_var() {
  local var_name="$1"
  case "${var_name}" in
    *TOKEN*|*KEY*|*SECRET*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

format_env_value_for_output() {
  local var_name="$1"
  local raw_value="$2"
  if is_sensitive_env_var "${var_name}"; then
    mask_secret_value "${raw_value}"
    return
  fi
  printf '%s' "${raw_value}"
}

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
        echo "[env-warning] ${var_name} conflict: ${seen_file}='$(format_env_value_for_output "${var_name}" "${seen_value}")' vs ${env_file}='$(format_env_value_for_output "${var_name}" "${parsed_value}")'"
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
      echo "[env] ${var_name}=$(format_env_value_for_output "${var_name}" "${value}")"
    else
      echo "[env] ${var_name}=<unset>"
    fi
  done
}
