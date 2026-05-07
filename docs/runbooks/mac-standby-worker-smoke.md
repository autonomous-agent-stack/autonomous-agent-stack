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

中文：`scripts/dev-start.sh` 默认以稳定模式启动 API，不启用 `uvicorn --reload`；如需开发热重载，设置 `AUTORESEARCH_API_RELOAD=1 scripts/dev-start.sh`。

English: `scripts/dev-start.sh` starts the API in stable mode by default without `uvicorn --reload`; set `AUTORESEARCH_API_RELOAD=1 scripts/dev-start.sh` when development hot reload is needed.

Default docs URL:

- `http://127.0.0.1:8001/docs`

## 2. Start the Mac worker

```bash
scripts/start-mac-worker.sh
```

中文：默认 worker 显示名为 `AAS Worker`；如需定制回写前缀，可设置 `AUTORESEARCH_TELEGRAM_WORKER_DISPLAY_NAME`。

English: The default worker display name is `AAS Worker`; set `AUTORESEARCH_TELEGRAM_WORKER_DISPLAY_NAME` to customize the write-back prefix.

Useful overrides:

```bash
WORKER_ID=mac-mini-01 \
HOUSEKEEPING_ROOT=$AAS_CODE_ROOT \
WORKER_DRY_RUN=1 \
scripts/start-mac-worker.sh
```

中文：启动后检查 worker inventory，期望至少有一个在线或忙碌 worker，且 capabilities 包含 `source_collect`、`youtube_autoflow` 与 `content_kb_ingest`。同一台 Mac 的旧 worker id 如果已经心跳过期，会被当前活跃注册折叠，不应再把健康检查拖成离线。

English: After startup, inspect worker inventory and expect at least one online or busy worker with `source_collect`, `youtube_autoflow`, and `content_kb_ingest` in capabilities. A stale old worker id for the same Mac is folded behind the current active registration and should not drag health into offline.

```bash
curl -sS http://127.0.0.1:8001/api/v1/workers
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
      "root_path": "$AAS_CODE_ROOT",
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

## 6. Enqueue a source_collect X bookmark fixture

中文：这个 smoke 不触发真实账号采集，只验证 worker 能读取 fixture、写入本地 artifact，并返回可交给 `content_kb_ingest` 的 payload。完整 Butler 路径会在 `source_collect` 成功回报后自动排入 `content_kb_ingest`。

English: This smoke does not trigger a real account collection. It verifies that the worker can read a fixture, write a local artifact, and return a payload suitable for `content_kb_ingest`. The full Butler path queues `content_kb_ingest` automatically after `source_collect` reports success.

```bash
cat >/tmp/aas-x-bookmarks-fixture.json <<'JSON'
{
  "items": [
    {
      "id": "1001",
      "text": "Agent workflows should collect sources before ingest.",
      "user": {"screenName": "example", "name": "Example"},
      "createdAt": "2026-05-06T00:00:00Z"
    }
  ]
}
JSON

curl -sS \
  -X POST http://127.0.0.1:8001/api/v1/worker-runs/source-collect \
  -H 'Content-Type: application/json' \
  -d '{
    "source_kind": "x_bookmarks",
    "fixture_path": "/tmp/aas-x-bookmarks-fixture.json",
    "collector": "xreach",
    "limit": 1,
    "max_pages": 1,
    "title": "Manual X bookmark smoke",
    "requested_by": "manual_smoke"
  }'
```

Expected result:

- worker claims the run
- final run result includes `artifact_path`, `metadata_path`, `collector=fixture`, `item_count=1`, and `content_kb_payload.subtitle_text_path`

中文：真实 X 书签采集会先解析 `AUTORESEARCH_XREACH_BIN`、worker `PATH` 和常见 Homebrew/local bin 路径，再使用 `xreach auth check` / `xreach auth extract` 预检后运行 `xreach bookmarks --json`。如果本机登录态仍需恢复，`source_collect` 不会直接进入失败终态，而是以 `worker_pause_reason=xreach_auth_required` 暂停原 run，Control Plane 会排入 Hermes recovery，并在 Telegram 发送“打开登录页 / 我已完成，继续采集 / 重新检测登录态 / 取消任务”恢复卡片；原始采集器错误只保留在 `collector_error` 里。如果 worker 找不到 `xreach`，任务会以 `worker_pause_reason=xreach_setup_required` 暂停，Hermes recovery 会给出安装、`AUTORESEARCH_XREACH_BIN`、重启 worker 或 `fixture_path` 离线 smoke 的恢复步骤。

English: Real X bookmark collection first resolves `AUTORESEARCH_XREACH_BIN`, the worker `PATH`, and common Homebrew/local bin paths, then runs `xreach auth check` / `xreach auth extract` before `xreach bookmarks --json`. If the local login state still needs recovery, `source_collect` does not enter a terminal failure; it pauses the original run with `worker_pause_reason=xreach_auth_required`, the Control Plane queues Hermes recovery, and Telegram sends an action card with “open login page / resume collection / recheck auth / cancel task”; the raw collector output stays only in `collector_error`. If the worker cannot find `xreach`, the task pauses with `worker_pause_reason=xreach_setup_required`, and Hermes recovery explains installation, `AUTORESEARCH_XREACH_BIN`, worker restart, or `fixture_path` offline smoke steps.

## 7. Enqueue a manual YouTube bridge action

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

## 8. Log expectations

During the smoke you should see log lines for:

- worker registration
- heartbeat
- claim
- run start
- run completion or failure

## 9. Enqueue a full YouTube -> GitHub autoflow run

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
- if `repos.yaml` lacks an explicit `repo_hint` or matching `channel_ids` / `channel_titles` / `keywords`, routing fails closed
- running this against a real remote repo may open a draft PR, so use a sandbox repo if you only want a smoke

## 10. Emulate Telegram thin ingress for one YouTube link

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
