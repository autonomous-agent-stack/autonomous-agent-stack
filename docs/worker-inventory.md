# Worker 盘点与状态查询
# Worker Inventory and Status Queries

这份文档说明 Python 控制面新增的 worker 只读盘点接口，以及 Telegram 管家的查询入口。
This document describes the new read-only worker inventory APIs in the Python control plane and the matching Telegram butler entrypoints.

## 设计边界
## Design Boundaries

- AAS 只会展示已经注册并持续心跳上报的 worker，不会自动发现系统里的所有进程。
  AAS only shows workers that have registered and continue to send heartbeats; it does not auto-discover every system process.
- 单独运行 `hermes gateway` 不会自动出现在这里；当前推荐做法是由已注册的 Mac worker 代理 Hermes runtime lane。
  Running `hermes gateway` alone does not make it appear here automatically; the current recommended path is to proxy the Hermes runtime lane through a registered Mac worker.
- 状态展示基于现有 `mode`、`health`、`is_stale`、`accepting_work`、`queue_depth` 做投影，不引入第二套状态机。
  Display status is projected from the existing `mode`, `health`, `is_stale`, `accepting_work`, and `queue_depth` fields; no second state machine is introduced.
- `location` 只表示技术位点，例如 host、runtime、work_dir，不表示物理地理位置。
  `location` represents technical placement only, such as host, runtime, and work directory, not a physical location.

## API
## API

- `GET /api/v1/workers`
  返回聚合后的 worker 列表与总览统计。
  Returns the aggregated worker list together with summary counts.
- `GET /api/v1/workers/{worker_id}`
  返回单个 worker 的完整只读视图。
  Returns the full read-only view for one worker.
- `GET /api/v1/workers/summary`
  仅返回总数、在线、忙碌、异常、离线统计。
  Returns totals only: online, busy, degraded, and offline counts.

主要字段：
Key fields:

- `active_tasks`
  当前该 worker 正在处理的排队中或运行中任务数。
  Number of queued or running tasks currently owned by the worker.
- `latest_task_summary`
  最近一条与该 worker 相关的任务摘要。
  Summary of the most recent task associated with the worker.
- `dispatch_rules`
  基于当前队列与注册信息整理出的结构化调度摘要。
  Structured dispatch hints derived from current queue state and registration data.
- `display_status`
  对人类友好的状态投影，当前值为 `online`、`busy`、`degraded`、`offline`。
  Human-friendly projected status, currently `online`, `busy`, `degraded`, or `offline`.

## Telegram 查询
## Telegram Queries

Telegram 管家现在会把以下问法路由到 worker 盘点视图：
The Telegram butler now routes the following kinds of questions to the worker inventory view:

- `当前 worker 情况`
- `有哪些 worker`
- `谁在线`
- `谁在忙`
- `心跳如何`

返回内容会包含总体统计和最多 4 个 worker 的简短卡片摘要。
The reply includes overall counts and a short card-style summary for up to 4 workers.
