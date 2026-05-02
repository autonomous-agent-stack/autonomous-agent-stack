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

预期结果：

- worker 从原始文本或直接 `source_url` 解析 YouTube URL
- worker 在既有 YouTube bounded context 中执行订阅、检查、字幕、摘要流程
- worker 在配置的知识库根目录下写入 Markdown 和 SQLite 索引行
- worker 把摘要交给 GitHub assistant 路由
- 最终 run result 包含 `repo`、`output_path`、`knowledge_path`、`knowledge_index_path`、`github_run_dir`、`github_run_status` 和可选 `pr_url`

Expected result:

- worker parses the YouTube URL from raw text or direct `source_url`
- worker runs subscription/check/transcript/digest on the existing YouTube bounded context
- worker writes Markdown plus a SQLite index row under the configured knowledge root
- worker hands the digest to GitHub assistant routing
- final run result includes `repo`, `output_path`, `knowledge_path`, `knowledge_index_path`, `github_run_dir`, `github_run_status`, and optional `pr_url`

说明：

- 这条路径是确定性的，不依赖 Telegram ingress
- 如果 `repos.yaml` 缺少显式 `repo_hint`，或没有匹配的 `channel_ids` / `channel_titles` / `keywords`，路由会 fail closed
- 对真实远端仓库运行时可能创建草稿 PR；只做 smoke 时请使用沙盒仓库

Notes:

- this path is deterministic and does not require Telegram ingress
- if `repos.yaml` lacks an explicit `repo_hint` or matching `channel_ids` / `channel_titles` / `keywords`, routing fails closed
- running this against a real remote repo may open a draft PR, so use a sandbox repo if you only want a smoke

## 9. 入队 X 书签归档 / Enqueue X bookmark archive

```bash
curl -sS \
  -X POST http://127.0.0.1:8001/api/v1/worker-runs/content-kb-bookmarks \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "https://x.com/example/status/123",
    "title": "X bookmarks smoke",
    "requested_by": "manual_smoke",
    "open_draft_pr": false,
    "metadata": {
      "source": "manual_smoke"
    }
  }'
```

预期结果：

- worker 从 `text` 提取书签 URL
- worker 写入 `x-bookmarks/*.md`
- worker 更新 `knowledge.sqlite3`
- 最终 run result 包含 `markdown_path`、`sqlite_index_path` 和 `bookmark_count`

Expected result:

- worker extracts the bookmark URL from `text`
- worker writes `x-bookmarks/*.md`
- worker updates `knowledge.sqlite3`
- final run result includes `markdown_path`, `sqlite_index_path`, and `bookmark_count`

如果希望归档后创建草稿 PR，设置 `open_draft_pr=true`，并提供 `owner`、`default_repo` 与 `github_output_dir`。

If you want a draft PR after archive generation, set `open_draft_pr=true` and provide `owner`, `default_repo`, and `github_output_dir`.

## 10. 模拟 Telegram 薄入口处理一个 YouTube 链接 / Emulate Telegram thin ingress for one YouTube link

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

预期结果：

- webhook ack 返回 `accepted=true`
- ack metadata 包含 `status=accepted` 和 control-plane `run_id`
- 入队 run 保持 `task_type=youtube_autoflow`
- OpenClaw session events 记录原始消息和 `youtube autoflow queued: <run_id>`
- Telegram handler 内不执行 YouTube 或 GitHub 业务逻辑

Expected result:

- webhook ack returns `accepted=true`
- ack metadata includes `status=accepted` and a control-plane `run_id`
- the queued run keeps `task_type=youtube_autoflow`
- OpenClaw session events record the original message plus `youtube autoflow queued: <run_id>`
- no YouTube or GitHub business logic runs inside the Telegram handler itself

Fail-closed 检查：

- 发送两个 URL，预期 `accepted=false`
- 发送缺少完整 URL 的 malformed YouTube reference（例如 `youtu.be/foo`），预期 `accepted=false`

Fail-closed checks:

- send two URLs in one message and expect `accepted=false`
- send a malformed YouTube reference such as `youtu.be/foo` without a full URL and expect `accepted=false`
