#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8001}"

echo "[1/5] enqueue low priority"
LOW_RUN_ID="$(curl -sS -X POST "${API_BASE}/api/v1/worker-runs" \
  -H "content-type: application/json" \
  -d '{"task_type":"noop","task_name":"low-priority","priority":1,"payload":{"message":"low"}}' | python3 -c 'import json,sys;print(json.load(sys.stdin)["run_id"])')"
echo "low run_id=${LOW_RUN_ID}"

echo "[2/5] enqueue high priority"
HIGH_RUN_ID="$(curl -sS -X POST "${API_BASE}/api/v1/worker-runs" \
  -H "content-type: application/json" \
  -d '{"task_type":"noop","task_name":"high-priority","priority":9,"payload":{"message":"high"}}' | python3 -c 'import json,sys;print(json.load(sys.stdin)["run_id"])')"
echo "high run_id=${HIGH_RUN_ID}"

echo "[3/5] manual requeue with backoff"
curl -sS -X POST "${API_BASE}/api/v1/worker-runs/${LOW_RUN_ID}/requeue" \
  -H "content-type: application/json" \
  -d '{"reason":"acceptance_manual_requeue","backoff_seconds":5}' >/dev/null
echo "requeued ${LOW_RUN_ID}"

echo "[4/5] force-fail high priority run"
curl -sS -X POST "${API_BASE}/api/v1/worker-runs/${HIGH_RUN_ID}/force-fail" \
  -H "content-type: application/json" \
  -d '{"reason":"acceptance_force_fail"}' >/dev/null
echo "force-failed ${HIGH_RUN_ID}"

echo "[5/5] verify health + worker inventory"
python3 scripts/telegram_ingress_health.py --minutes 10 --json --no-logs || true
curl -sS "${API_BASE}/api/v1/workers/summary"
echo
echo "acceptance done"
