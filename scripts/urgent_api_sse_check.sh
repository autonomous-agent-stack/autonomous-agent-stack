#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN=".venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

echo "[urgent-check] Running API/SSE priority validation..."
"$PYTHON_BIN" -m pytest \
  tests/test_api_real.py \
  tests/test_orchestration_api.py \
  tests/test_integration.py::test_sse_health_endpoint \
  -q

echo "[urgent-check] Done."
