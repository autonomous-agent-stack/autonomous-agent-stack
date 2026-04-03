# Replay OpenHands Worker Requests

## Purpose

Replay recorded `OpenHandsWorkerJobSpec` payloads through the local worker service
builders without invoking a live backend. Use this to verify contract mapping,
artifact naming, allowed-path handling, and failure classification.

## Minimal Run

```bash
python scripts/replay_openhands_worker_requests.py \
  --input artifacts/worker-replay/recorded_requests.json \
  --output artifacts/worker-replay/replay_results.json
```

## Outputs

- `artifacts/worker-replay/replay_results.json`

## Test

```bash
pytest -q tests/test_openhands_worker_replay.py
```
