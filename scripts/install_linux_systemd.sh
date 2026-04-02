#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATE_DIR="${REPO_ROOT}/deployment/systemd"
SYSTEMD_DIR="/etc/systemd/system"
SERVICE_USER="${SUDO_USER:-$(id -un)}"
SERVICE_GROUP="$(id -gn "${SERVICE_USER}" 2>/dev/null || echo "${SERVICE_USER}")"
TARGET_REPO="${REPO_ROOT}"
START_AFTER_INSTALL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --user)
      SERVICE_USER="$2"
      shift 2
      ;;
    --group)
      SERVICE_GROUP="$2"
      shift 2
      ;;
    --repo)
      TARGET_REPO="$2"
      shift 2
      ;;
    --systemd-dir)
      SYSTEMD_DIR="$2"
      shift 2
      ;;
    --start)
      START_AFTER_INSTALL=1
      shift
      ;;
    *)
      echo "unknown arg: $1"
      exit 2
      ;;
  esac
done

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "this installer must run on Linux"
  exit 1
fi

if [[ "${EUID}" -ne 0 ]]; then
  echo "run with sudo: sudo bash scripts/install_linux_systemd.sh --user ${SERVICE_USER} --repo ${TARGET_REPO} --start"
  exit 1
fi

mkdir -p "${SYSTEMD_DIR}"

render_unit() {
  local template_file="$1"
  local target_file="$2"
  python3 - "$template_file" "$target_file" "$SERVICE_USER" "$SERVICE_GROUP" "$TARGET_REPO" <<'PY'
from pathlib import Path
import sys

template = Path(sys.argv[1]).read_text(encoding="utf-8")
target = Path(sys.argv[2])
user = sys.argv[3]
group = sys.argv[4]
workdir = sys.argv[5]
rendered = (
    template
    .replace("__USER__", user)
    .replace("__GROUP__", group)
    .replace("__WORKDIR__", workdir)
)
target.write_text(rendered, encoding="utf-8")
PY
}

render_unit "${TEMPLATE_DIR}/autonomous-agent-stack-api.service.template" "${SYSTEMD_DIR}/autonomous-agent-stack-api.service"
render_unit "${TEMPLATE_DIR}/autonomous-agent-stack-telegram-poller.service.template" "${SYSTEMD_DIR}/autonomous-agent-stack-telegram-poller.service"
render_unit "${TEMPLATE_DIR}/autonomous-agent-stack-boot-report.service.template" "${SYSTEMD_DIR}/autonomous-agent-stack-boot-report.service"

chmod 0644 \
  "${SYSTEMD_DIR}/autonomous-agent-stack-api.service" \
  "${SYSTEMD_DIR}/autonomous-agent-stack-telegram-poller.service" \
  "${SYSTEMD_DIR}/autonomous-agent-stack-boot-report.service"

systemctl daemon-reload
systemctl enable autonomous-agent-stack-api.service autonomous-agent-stack-telegram-poller.service autonomous-agent-stack-boot-report.service

if [[ "${START_AFTER_INSTALL}" == "1" ]]; then
  systemctl restart autonomous-agent-stack-api.service
  systemctl restart autonomous-agent-stack-telegram-poller.service
  systemctl start autonomous-agent-stack-boot-report.service
fi

echo "installed:"
echo "  autonomous-agent-stack-api.service"
echo "  autonomous-agent-stack-telegram-poller.service"
echo "  autonomous-agent-stack-boot-report.service"
echo
echo "status:"
echo "  systemctl status autonomous-agent-stack-api.service --no-pager"
echo "  systemctl status autonomous-agent-stack-telegram-poller.service --no-pager"
echo "  systemctl status autonomous-agent-stack-boot-report.service --no-pager"
