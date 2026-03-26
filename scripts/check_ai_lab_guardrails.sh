#!/usr/bin/env bash
set -euo pipefail

WORKSPACE_DIR="/Users/ai_lab/workspace"

echo "[check] workspace exists"
test -d "${WORKSPACE_DIR}"

echo "[check] workspace writable"
test -w "${WORKSPACE_DIR}"

echo "[check] sensitive paths not mounted by convention"
if mount | grep -E '(/etc|/Users/.*/\.ssh)' >/dev/null 2>&1; then
  echo "Sensitive mount detected."
  exit 1
fi

echo "[check] OK"

