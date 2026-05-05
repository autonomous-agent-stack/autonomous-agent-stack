# Control Plane v2 Smoke 固化 / Control Plane v2 Smoke Hardening

## 用途 / Purpose

中文：`make smoke-cpv2` 会启动一个使用临时 SQLite 数据库的本地 API，验证 Telegram-like YouTube approval、`/approve`、worker claim/report、v2 task/run projection 与 timeline 事件闭环。

English: `make smoke-cpv2` starts a local API with a temporary SQLite database and validates the full Telegram-like YouTube approval, `/approve`, worker claim/report, v2 task/run projection, and timeline event loop.

## 执行 / Run

中文：默认优先使用 `127.0.0.1:8001`；如果端口已占用，会自动尝试 `127.0.0.1:8011`。

English: By default, the smoke prefers `127.0.0.1:8001`; if that port is occupied, it automatically tries `127.0.0.1:8011`.

```bash
make smoke-cpv2
```

## 成功标准 / Success Criteria

中文：脚本成功时输出一行 compact JSON；失败时以非 0 状态退出，并在 stderr 输出失败原因和 API 日志尾部。

English: On success, the script prints one compact JSON line; on failure, it exits non-zero and writes the failure reason plus the API log tail to stderr.

## 运维操作 / Operator Actions

中文：Control Plane v2 提供 operator API 用于取消、重试和强制失败任务或 run：`POST /api/v2/tasks/{task_id}/cancel`、`POST /api/v2/runs/{run_id}/cancel`、`POST /api/v2/tasks/{task_id}/retry`、`POST /api/v2/runs/{run_id}/retry`、`POST /api/v2/tasks/{task_id}/force-fail`、`POST /api/v2/runs/{run_id}/force-fail`。找不到目标返回 404；当前状态不允许操作返回 409。

English: Control Plane v2 exposes operator APIs to cancel, retry, and force-fail tasks or runs: `POST /api/v2/tasks/{task_id}/cancel`, `POST /api/v2/runs/{run_id}/cancel`, `POST /api/v2/tasks/{task_id}/retry`, `POST /api/v2/runs/{run_id}/retry`, `POST /api/v2/tasks/{task_id}/force-fail`, and `POST /api/v2/runs/{run_id}/force-fail`. Missing targets return 404; state-incompatible operations return 409.

中文：取消只允许 queued/running 的 v2 worker run。queued 会直接投影为 `cancelled`；running 只记录 `run.cancel_requested` 和 worker metadata 的 `cancel_requested`，等待 worker 后续 terminal report 再投影为终态。强制失败只允许 queued/running，并通过 worker scheduler force-fail 后同步为 `failed`。

English: Cancellation is allowed only for queued or running v2 worker runs. A queued run projects directly to `cancelled`; a running run records `run.cancel_requested` plus `cancel_requested` in worker metadata, then waits for the worker's later terminal report before terminal projection. Force-fail is allowed only for queued or running runs and syncs to `failed` through the worker scheduler force-fail path.

中文：v2 retry 只允许 `failed` 或 `cancelled` 的当前 run，并采用创建新 run 的语义：保留同一个 task，复制上一条 worker run 的 queue/task/payload/priority/max_retries 和 Telegram completion metadata，生成新的 worker run 与新的 v2 run，更新 `task.run_id` 指向新 run。lineage 写入新 run metadata 的 `retry_of_run_id`、`retry_of_worker_run_id`、`retry_sequence`，并在 task metadata 追加 `previous_run_ids` 与 `latest_retry_of_run_id`；timeline 先记录 `task.retried`，再记录新的 `run.queued`。

English: v2 retry is allowed only for the current `failed` or `cancelled` run and creates a new run instead of reusing the old one: it keeps the same task, copies the previous worker run's queue/task/payload/priority/max_retries and Telegram completion metadata, creates a new worker run plus a new v2 run, and updates `task.run_id` to the new run. Lineage is recorded in the new run metadata as `retry_of_run_id`, `retry_of_worker_run_id`, and `retry_sequence`, and in task metadata as appended `previous_run_ids` plus `latest_retry_of_run_id`; the timeline records `task.retried` followed by the new `run.queued`.

中文：Telegram `/cancel [run_id|task_id]` 和 `/retry [run_id|task_id]` 会优先解析 v2 task/run；非 v2 worker run 继续保留旧 cancel/retry fallback。`/force-fail [run_id|task_id]` 仅 owner role 可用，且只作用于 v2 task/run。本切片不改变 Telegram 普通文本回复格式，不新增 MarkdownV2 或 Butler 消息卡片重构。

English: Telegram `/cancel [run_id|task_id]` and `/retry [run_id|task_id]` resolve v2 tasks/runs first; non-v2 worker runs keep the legacy cancel/retry fallback. `/force-fail [run_id|task_id]` is owner-only and applies only to v2 tasks/runs. This slice keeps Telegram replies as plain text and does not add MarkdownV2 or refactor Butler message cards.
