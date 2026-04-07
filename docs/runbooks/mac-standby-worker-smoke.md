# Mac Standby Worker Smoke

## Goal

Validate the first end-to-end `mac` standby worker flow on the Python/FastAPI control plane.

## Prerequisites

- local virtualenv exists at `.venv`
- API DB path is writable
- no TypeScript control-plane changes are involved

## 1. Start the API

```bash
scripts/dev-start.sh
```

Default docs URL:

- `http://127.0.0.1:8001/docs`

## 2. Start the Mac worker

```bash
scripts/start-mac-worker.sh
```

Useful overrides:

```bash
WORKER_ID=mac-mini-01 \
HOUSEKEEPING_ROOT=/Volumes/AI_LAB/Github \
WORKER_DRY_RUN=1 \
scripts/start-mac-worker.sh
```

## 3. Enqueue a noop run

```bash
curl -sS \
  -X POST http://127.0.0.1:8001/api/v1/worker-runs \
  -H 'Content-Type: application/json' \
  -d '{
    "queue_name": "housekeeping",
    "task_type": "noop",
    "payload": {"message": "smoke noop"},
    "requested_by": "manual_smoke"
  }'
```

Expected result:

- worker claims the run
- worker reports `running`
- worker reports `completed`

## 4. Enqueue a dry-run AppleDouble cleanup

```bash
curl -sS \
  -X POST http://127.0.0.1:8001/api/v1/worker-runs \
  -H 'Content-Type: application/json' \
  -d '{
    "queue_name": "housekeeping",
    "task_type": "cleanup_appledouble",
    "payload": {
      "root_path": "/Volumes/AI_LAB/Github",
      "recursive": true,
      "dry_run": true
    },
    "requested_by": "manual_smoke"
  }'
```

Expected result:

- worker keeps files in place because `dry_run=true`
- final run result includes `deleted_count` and `deleted_paths`

## 5. Inspect persistence

If `sqlite3` is available:

```bash
sqlite3 artifacts/api/evaluations.sqlite3 "SELECT resource_id, json_extract(payload_json, '$.status') AS status FROM worker_run_queue ORDER BY updated_at DESC LIMIT 10;"
```

```bash
sqlite3 artifacts/api/evaluations.sqlite3 "SELECT resource_id, json_extract(payload_json, '$.active') AS active FROM worker_leases ORDER BY updated_at DESC LIMIT 10;"
```

Healthy smoke signs:

- queued run moves to `completed`
- terminal run has inactive lease
- worker registration row keeps updating `last_heartbeat_at`

## 6. Enqueue a manual YouTube bridge action

```bash
curl -sS \
  -X POST http://127.0.0.1:8001/api/v1/worker-runs \
  -H 'Content-Type: application/json' \
  -d '{
    "queue_name": "housekeeping",
    "task_type": "youtube_action",
    "payload": {
      "action": "subscribe",
      "target_url": "https://www.youtube.com/watch?v=6yjJ7Prt-RI",
      "source": "manual_smoke"
    },
    "requested_by": "manual_smoke"
  }'
```

Expected result:

- worker claims the run
- worker executes the internal standby-to-YouTube bridge
- run result includes structured fields such as `success`, `status`, `error_kind`, `failed_stage`, `reason`, and returned resource ids
- no Telegram, cron, or autonomous polling behavior is introduced

## 7. Log expectations

During the smoke you should see log lines for:

- worker registration
- heartbeat
- claim
- run start
- run completion or failure

## 8. Enqueue a full YouTube -> GitHub autoflow run

```bash
curl -sS \
  -X POST http://127.0.0.1:8001/api/v1/worker-runs/youtube-autoflow \
  -H 'Content-Type: application/json' \
  -d '{
    "input_text": "请处理这个视频 https://www.youtube.com/watch?v=6yjJ7Prt-RI 并推到 GitHub",
    "repo_hint": "srxly888-creator/autonomous-agent-stack",
    "requested_by": "manual_smoke",
    "metadata": {
      "source": "manual_smoke"
    }
  }'
```

Expected result:

- worker parses the YouTube URL from raw text or direct `source_url`
- worker runs subscription/check/transcript/digest on the existing YouTube bounded context
- worker hands the digest to GitHub assistant routing
- final run result includes `repo`, `output_path`, `github_run_dir`, `github_run_status`, and optional `pr_url`

Notes:

- this path is deterministic and does not require Telegram ingress
- if `repos.yaml` has multiple `youtube_ingest.enabled` repos with no discriminating rules, routing fails closed
- running this against a real remote repo may open a draft PR, so use a sandbox repo if you only want a smoke

## 9. Emulate Telegram thin ingress for one YouTube link

```bash
curl -sS \
  -X POST http://127.0.0.1:8001/api/v1/gateway/telegram/webhook \
  -H 'Content-Type: application/json' \
  -d '{
    "update_id": 9001,
    "message": {
      "message_id": 501,
      "text": "请处理这个视频 https://www.youtube.com/watch?v=6yjJ7Prt-RI",
      "chat": {"id": 9527, "type": "private"},
      "from": {"id": 9527, "username": "manual_smoke"}
    }
  }'
```

Expected result:

- webhook ack returns `accepted=true`
- ack metadata includes `status=accepted` and a control-plane `run_id`
- the queued run keeps `task_type=youtube_autoflow`
- OpenClaw session events record the original message plus `youtube autoflow queued: <run_id>`
- no YouTube or GitHub business logic runs inside the Telegram handler itself

Fail-closed checks:

- send two URLs in one message and expect `accepted=false`
- send a malformed YouTube reference such as `youtu.be/foo` without a full URL and expect `accepted=false`
