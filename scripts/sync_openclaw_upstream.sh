#!/usr/bin/env bash
set -euo pipefail

UPSTREAM_URL="${OPENCLAW_UPSTREAM_URL:-https://github.com/openclaw/openclaw.git}"
WORKSPACE_ROOT="${OPENCLAW_SYNC_WORKSPACE_ROOT:-/Volumes/AI_LAB/ai_lab/workspace}"
KEEP_CLONE="${OPENCLAW_SYNC_KEEP_CLONE:-0}"
MAX_COMMITS="${OPENCLAW_SYNC_MAX_COMMITS:-5}"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "[error] missing command: $1" >&2
    exit 1
  }
}

need_cmd git
need_cmd mktemp

mkdir -p "${WORKSPACE_ROOT}"
SYNC_DIR="$(mktemp -d "${WORKSPACE_ROOT%/}/openclaw-upstream.XXXXXX")"

cleanup() {
  if [[ "${KEEP_CLONE}" == "1" ]]; then
    return
  fi
  find "${WORKSPACE_ROOT}" -mindepth 1 -maxdepth 1 -type d -name 'openclaw-upstream.*' -exec rm -rf {} +
}

trap cleanup EXIT

echo "[sync] detecting upstream default branch for ${UPSTREAM_URL}"
DEFAULT_BRANCH="$(git ls-remote --symref "${UPSTREAM_URL}" HEAD | awk '/^ref:/ {sub("refs/heads/","",$2); print $2; exit}')"
DEFAULT_BRANCH="${DEFAULT_BRANCH:-main}"
echo "[sync] cloning ${UPSTREAM_URL} (branch=${DEFAULT_BRANCH}, depth=1)"
echo "[sync] target workspace: ${SYNC_DIR}"
git clone --progress --depth=1 --single-branch --no-tags --branch "${DEFAULT_BRANCH}" "${UPSTREAM_URL}" "${SYNC_DIR}"
git -C "${SYNC_DIR}" fetch --depth="$((MAX_COMMITS + 1))" origin "${DEFAULT_BRANCH}"

echo
echo "[sync] latest commit"
git -C "${SYNC_DIR}" log "origin/${DEFAULT_BRANCH}" -1 --decorate=short --date=iso --stat

echo
echo "[sync] recent commits"
git -C "${SYNC_DIR}" log "origin/${DEFAULT_BRANCH}" -"${MAX_COMMITS}" --date=short --pretty=format:'- %ad %h %s'
echo

echo
echo "[sync] recent touched files"
for commit in $(git -C "${SYNC_DIR}" rev-list --max-count="${MAX_COMMITS}" "origin/${DEFAULT_BRANCH}"); do
  git -C "${SYNC_DIR}" diff-tree --no-commit-id --name-only -r -m "${commit}"
done | sed '/^$/d' | sort -u | sed 's/^/- /'

echo
if [[ "${KEEP_CLONE}" == "1" ]]; then
  echo "[sync] clone ready at ${SYNC_DIR}"
else
  echo "[sync] analysis complete; cleaning ${WORKSPACE_ROOT%/}/openclaw-upstream.*"
fi
