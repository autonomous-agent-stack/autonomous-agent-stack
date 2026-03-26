#!/usr/bin/env bash
set -euo pipefail

LAB_USER="${LAB_USER:-ai_lab}"
LAB_FULLNAME="${LAB_FULLNAME:-AI Lab}"
WORKSPACE_HOME="/Users/${LAB_USER}"
WORKSPACE_DIR="${WORKSPACE_HOME}/workspace"
LOG_DIR="${WORKSPACE_HOME}/logs"
CACHE_DIR="${WORKSPACE_HOME}/.cache"
APFS_VOLUME_NAME="${APFS_VOLUME_NAME:-AI_LAB}"
APFS_MOUNTPOINT="${APFS_MOUNTPOINT:-${WORKSPACE_DIR}}"
APFS_QUOTA="${APFS_QUOTA:-80g}"
APFS_RESERVE="${APFS_RESERVE:-20g}"

usage() {
  cat <<'EOF'
Usage:
  sudo LAB_PASSWORD='...' APFS_PARENT_DISK='disk3s1' ./scripts/setup_ai_lab.sh

Required:
  APFS_PARENT_DISK   Parent APFS container identifier, e.g. disk3s1

Optional:
  LAB_USER           Default: ai_lab
  LAB_FULLNAME       Default: AI Lab
  APFS_VOLUME_NAME   Default: AI_LAB
  APFS_MOUNTPOINT    Default: /Users/ai_lab/workspace
  APFS_QUOTA        Default: 80g
  APFS_RESERVE      Default: 20g
  LAB_PASSWORD      If omitted, you will be prompted interactively
EOF
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "Run as root via sudo."
    exit 1
  fi
}

prompt_password() {
  if [[ -n "${LAB_PASSWORD:-}" ]]; then
    return
  fi
  read -r -s -p "Password for ${LAB_USER}: " LAB_PASSWORD
  echo
  export LAB_PASSWORD
}

create_user() {
  if id "${LAB_USER}" >/dev/null 2>&1; then
    echo "[info] User ${LAB_USER} already exists"
    return
  fi

  echo "[info] Creating standard user ${LAB_USER}"
  sysadminctl -addUser "${LAB_USER}" \
    -fullName "${LAB_FULLNAME}" \
    -password "${LAB_PASSWORD}" \
    -admin false \
    -home "${WORKSPACE_HOME}" \
    -shell /bin/zsh
}

prepare_home_dirs() {
  echo "[info] Preparing directories"
  install -d -o "${LAB_USER}" -g staff -m 0755 "${WORKSPACE_HOME}"
  install -d -o "${LAB_USER}" -g staff -m 0755 "${LOG_DIR}"
  install -d -o "${LAB_USER}" -g staff -m 0755 "${CACHE_DIR}"
  install -d -o "${LAB_USER}" -g staff -m 0755 "$(dirname "${WORKSPACE_DIR}")"
}

create_quota_volume() {
  if mount | grep -q "on ${APFS_MOUNTPOINT} "; then
    echo "[info] ${APFS_MOUNTPOINT} already mounted"
    return
  fi

  if [[ -z "${APFS_PARENT_DISK:-}" ]]; then
    echo "APFS_PARENT_DISK is required."
    usage
    exit 1
  fi

  echo "[info] Creating APFS volume ${APFS_VOLUME_NAME} at ${APFS_MOUNTPOINT}"
  diskutil apfs addVolume "${APFS_PARENT_DISK}" APFS "${APFS_VOLUME_NAME}" \
    -mountpoint "${APFS_MOUNTPOINT}" \
    -quota "${APFS_QUOTA}" \
    -reserve "${APFS_RESERVE}"
}

restrict_permissions() {
  echo "[info] Locking down workspace"
  chown -R "${LAB_USER}:staff" "${WORKSPACE_HOME}"
  chmod 0755 "${WORKSPACE_HOME}"
  chmod 0755 "${WORKSPACE_DIR}"
  chmod 0700 "${LOG_DIR}"
  chmod 0700 "${CACHE_DIR}"
}

main() {
  require_root
  prompt_password
  create_user
  prepare_home_dirs
  create_quota_volume
  restrict_permissions

  cat <<EOF
[done] ai_lab environment prepared
- User: ${LAB_USER}
- Home: ${WORKSPACE_HOME}
- Workspace: ${WORKSPACE_DIR}
- APFS quota: ${APFS_QUOTA}
- APFS reserve: ${APFS_RESERVE}
EOF
}

main "$@"

