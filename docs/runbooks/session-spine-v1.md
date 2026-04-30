# Session Spine v1 运维手册
# Session Spine v1 Runbook

Session Spine v1 把 OpenClaw session、worker run、approval、Hermes interactive pause/resume 投影到同一条只读时间线，方便排查一次任务从入队到审批再恢复的完整链路。
Session Spine v1 projects OpenClaw sessions, worker runs, approvals, and Hermes interactive pause/resume into one read-only timeline so operators can inspect a task from queueing through approval and resume.

这是 projection layer：现有 OpenClaw、runtime、worker、approval API 的行为不变，历史数据不做 backfill。
This is a projection layer: existing OpenClaw, runtime, worker, and approval API behavior is unchanged, and historical data is not backfilled.

## 1. 查询事件 / Query Events

按 session 查询 canonical events：
Query canonical events by session:

```bash
curl -sS "http://127.0.0.1:8001/api/v1/sessions/<session_id>/events"
```

常用过滤：
Common filters:

```bash
curl -sS "http://127.0.0.1:8001/api/v1/sessions/<session_id>/events?source=worker_scheduler"
curl -sS "http://127.0.0.1:8001/api/v1/sessions/<session_id>/events?run_id=<run_id>"
curl -sS "http://127.0.0.1:8001/api/v1/sessions/<session_id>/events?approval_id=<approval_id>"
curl -sS "http://127.0.0.1:8001/api/v1/sessions/<session_id>/events?after_event_id=<event_id>&limit=50"
```

## 2. 查询 Timeline / Query Timeline

Timeline 返回事件、最新事件、摘要和关联对象：
The timeline returns events, the latest event, summary, and correlated objects:

```bash
curl -sS "http://127.0.0.1:8001/api/v1/sessions/<session_id>/timeline"
```

重点字段：
Key fields:

- `summary.event_count`：当前返回窗口中的事件数。
  `summary.event_count`: number of events in the current response window.
- `summary.latest_status`：最新事件投影出的状态。
  `summary.latest_status`: status projected by the latest event.
- `correlations.run_ids`：时间线关联的 worker/runtime run。
  `correlations.run_ids`: worker/runtime runs correlated with the timeline.
- `correlations.approval_ids`：时间线关联的 approval request。
  `correlations.approval_ids`: approval requests correlated with the timeline.
- `correlations.worker_ids`：参与执行的 worker。
  `correlations.worker_ids`: workers involved in execution.

## 3. Hermes Approval 链路 / Hermes Approval Flow

Hermes interactive 触发审批时，正常链路应出现这些事件：
When Hermes interactive requires approval, the normal flow should show these events:

1. `worker.run.queued`
   Worker run 已进入队列。
   The worker run has been queued.
2. `worker.run.claimed`
   某个 worker 已领取 run。
   A worker has claimed the run.
3. `hermes.interactive.approval_required`
   Hermes gateway 发出审批请求。
   The Hermes gateway emitted an approval request.
4. `approval.requested`
   AAS 创建可由 Telegram、Panel、Admin 或 API 处理的 approval request。
   AAS created an approval request that Telegram, Panel, Admin, or API can resolve.
5. `worker.run.paused`
   Worker 释放 lease，等待外部审批结果后恢复。
   The worker released its lease and is waiting for an approval decision.
6. `approval.approved` 或 `approval.rejected`
   审批结果已在 AAS 内落库。
   The decision has been persisted in AAS.
7. `worker.run.requeued`
   审批 callback 成功送达后，paused run 被重新入队。
   After the approval callback is delivered, the paused run is requeued.

如果 callback 送达失败，应看到：
If callback delivery fails, expect:

- `approval.decision_delivery_failed`
  记录失败原因，approval 保持 `pending`，不会误标 resolved。
  Records the failure reason; the approval remains `pending` and is not marked resolved.

## 4. 幂等与边界 / Idempotency and Boundaries

- `idempotency_key` 命中时返回已有事件，不更新已写入 payload。
  When `idempotency_key` matches an existing event, the existing event is returned and the stored payload is not updated.
- Hermes gateway event 使用 `gateway_session_id + event_id` 去重。
  Hermes gateway events dedupe by `gateway_session_id + event_id`.
- V1 不开放 public append endpoint；所有事件来自已有产品路径投影。
  V1 does not expose a public append endpoint; events are projected from existing product paths.
- V1 不替换 `OpenClawSessionRead.events`，旧 session event 列表继续保留。
  V1 does not replace `OpenClawSessionRead.events`; the legacy session event list remains available.

## 5. 快速排查 / Quick Triage

先从 session timeline 看关联对象：
Start with the session timeline and inspect correlations:

```bash
curl -sS "http://127.0.0.1:8001/api/v1/sessions/<session_id>/timeline"
```

再按 `run_id` 缩小 worker lifecycle：
Then narrow the worker lifecycle by `run_id`:

```bash
curl -sS "http://127.0.0.1:8001/api/v1/sessions/<session_id>/events?run_id=<run_id>"
```

最后按 `approval_id` 检查审批是否已创建、是否送达失败、是否重新入队：
Finally filter by `approval_id` to confirm whether approval was created, whether delivery failed, and whether the run was requeued:

```bash
curl -sS "http://127.0.0.1:8001/api/v1/sessions/<session_id>/events?approval_id=<approval_id>"
```
