#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8001}"

echo "[1/7] enqueue low priority"
LOW_RUN_ID="$(curl -sS -X POST "${API_BASE}/api/v1/worker-runs" \
  -H "content-type: application/json" \
  -d '{"task_type":"noop","task_name":"low-priority","priority":1,"payload":{"message":"low"}}' | python3 -c 'import json,sys;print(json.load(sys.stdin)["run_id"])')"
echo "low run_id=${LOW_RUN_ID}"

echo "[2/7] enqueue high priority"
HIGH_RUN_ID="$(curl -sS -X POST "${API_BASE}/api/v1/worker-runs" \
  -H "content-type: application/json" \
  -d '{"task_type":"noop","task_name":"high-priority","priority":9,"payload":{"message":"high"}}' | python3 -c 'import json,sys;print(json.load(sys.stdin)["run_id"])')"
echo "high run_id=${HIGH_RUN_ID}"

echo "[3/7] enqueue interactive Hermes metadata"
INTERACTIVE_RUN_ID="$(curl -sS -X POST "${API_BASE}/api/v1/worker-runs" \
  -H "content-type: application/json" \
  -d '{"task_type":"claude_runtime","task_name":"interactive-hermes","priority":8,"max_retries":1,"payload":{"runtime_id":"hermes","execution_mode":"interactive","prompt":"acceptance"},"metadata":{"target_agent":"github_ops_accountA","execution_mode":"interactive","interactive_lease_ttl_seconds":900}}' | python3 -c 'import json,sys;print(json.load(sys.stdin)["run_id"])')"
echo "interactive run_id=${INTERACTIVE_RUN_ID}"

echo "[4/7] manual requeue with backoff"
curl -sS -X POST "${API_BASE}/api/v1/worker-runs/${LOW_RUN_ID}/requeue" \
  -H "content-type: application/json" \
  -d '{"reason":"acceptance_manual_requeue","backoff_seconds":5}' >/dev/null
echo "requeued ${LOW_RUN_ID}"

echo "[5/7] force-fail high priority run"
curl -sS -X POST "${API_BASE}/api/v1/worker-runs/${HIGH_RUN_ID}/force-fail" \
  -H "content-type: application/json" \
  -d '{"reason":"acceptance_force_fail"}' >/dev/null
echo "force-failed ${HIGH_RUN_ID}"

echo "[6/7] force-fail interactive run"
curl -sS -X POST "${API_BASE}/api/v1/worker-runs/${INTERACTIVE_RUN_ID}/force-fail" \
  -H "content-type: application/json" \
  -d '{"reason":"acceptance_interactive_cleanup"}' >/dev/null
echo "force-failed ${INTERACTIVE_RUN_ID}"

echo "[7/7] verify health + worker inventory"
python3 scripts/telegram_ingress_health.py --minutes 10 --json --no-logs || true
curl -sS "${API_BASE}/api/v1/workers/summary"
echo
echo "acceptance done"
