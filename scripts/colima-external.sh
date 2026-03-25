#!/usr/bin/env bash
set -euo pipefail

COLIMA_BUNDLE_PATH="${COLIMA_BUNDLE_PATH:-/Volumes/PS1008/colima-store.sparsebundle}"
COLIMA_MOUNT_POINT="${COLIMA_MOUNT_POINT:-/Volumes/ColimaStore}"
COLIMA_HOME_PATH="${COLIMA_HOME_PATH:-${COLIMA_MOUNT_POINT}/.colima-home}"

CPU="${COLIMA_CPU:-2}"
MEMORY_GB="${COLIMA_MEMORY_GB:-4}"
DISK_GB="${COLIMA_DISK_GB:-20}"
PROFILE="${COLIMA_PROFILE:-default}"

attach_bundle() {
  if [[ ! -d "${COLIMA_MOUNT_POINT}" ]]; then
    hdiutil attach "${COLIMA_BUNDLE_PATH}" >/dev/null
  fi
  mkdir -p "${COLIMA_HOME_PATH}"
}

do_start() {
  attach_bundle
  COLIMA_HOME="${COLIMA_HOME_PATH}" colima start \
    --cpu "${CPU}" \
    --memory "${MEMORY_GB}" \
    --disk "${DISK_GB}" \
    --vm-type vz \
    --mount-type virtiofs \
    --profile "${PROFILE}"
}

do_stop() {
  COLIMA_HOME="${COLIMA_HOME_PATH}" colima stop --profile "${PROFILE}" || true
}

do_status() {
  COLIMA_HOME="${COLIMA_HOME_PATH}" colima status --profile "${PROFILE}"
}

do_delete() {
  COLIMA_HOME="${COLIMA_HOME_PATH}" colima delete -f --profile "${PROFILE}" || true
}

case "${1:-status}" in
  start)
    do_start
    ;;
  stop)
    do_stop
    ;;
  status)
    do_status
    ;;
  delete)
    do_delete
    ;;
  *)
    echo "Usage: $0 {start|stop|status|delete}"
    exit 1
    ;;
esac
