# 单机版 AAS 定时任务 Runbook

适用范围：

- 单机版 AAS
- 单控制面进程
- SQLite 控制面
- 已有可执行的 worker task

这条 runbook 只解决一件事：

`按时间触发 -> enqueue worker run -> 由现有 worker claim/execute/report`

当前实现使用 **APScheduler** 作为单机时间触发引擎，但仍然复用现有 AAS worker queue / lease / report 主链。

它不是分布式调度器，也不是复杂 cron 平台。

## 1. 先把单机基线跑通

```bash
cd /Volumes/AI_LAB/Github/autonomous-agent-stack
make setup
make doctor
AUTORESEARCH_MODE=minimal make start
```

最小验证：

```bash
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8001/docs
make smoke-local
```

## 2. 定时任务的最佳实践

先手动触发，后定时。

建议顺序：

1. 先确认目标 task 已能手动 enqueue 并成功执行。
2. 再创建 schedule。
3. 先用 `/api/v1/worker-schedules/tick` 手动推进一次。
4. 最后再打开后台 schedule daemon。

原因：

- 这样更容易分辨问题是出在任务本身，还是出在时间触发层。
- 单机试运行阶段，先验证“任务闭环”，再验证“自动触发闭环”更稳。

## 3. 启用后台 schedule daemon

默认不自动启动后台 schedule daemon。

如果要让 AAS 在单机上自动扫描并触发 schedule，请显式打开：

```bash
export AUTORESEARCH_ENABLE_WORKER_SCHEDULE_DAEMON=1
export AUTORESEARCH_WORKER_SCHEDULE_POLL_SECONDS=30
AUTORESEARCH_MODE=minimal make start
```

说明：

- `AUTORESEARCH_ENABLE_WORKER_SCHEDULE_DAEMON=1`
  打开单机 schedule 轮询器
- `AUTORESEARCH_WORKER_SCHEDULE_POLL_SECONDS=30`
  每 30 秒扫描一次到期 schedule

## 4. 创建一个 interval schedule

先用最小 `noop` 验证：

```bash
curl -X POST http://127.0.0.1:8001/api/v1/worker-schedules \
  -H 'Content-Type: application/json' \
  -d '{
    "schedule_name": "noop-every-10m",
    "task_type": "noop",
    "schedule_mode": "interval",
    "interval_seconds": 600,
    "requested_by": "runbook",
    "metadata": {
      "purpose": "smoke"
    }
  }'
```

查看 schedule：

```bash
curl http://127.0.0.1:8001/api/v1/worker-schedules
```

## 5. 创建一个 one-shot schedule

```bash
curl -X POST http://127.0.0.1:8001/api/v1/worker-schedules \
  -H 'Content-Type: application/json' \
  -d '{
    "schedule_name": "noop-once",
    "task_type": "noop",
    "schedule_mode": "once",
    "first_run_at": "2026-04-09T12:00:00+08:00",
    "requested_by": "runbook"
  }'
```

## 6. 手动推进 schedule（推荐先做）

即使后台 daemon 还没打开，也可以手动推进所有已到期 schedule：

```bash
curl -X POST http://127.0.0.1:8001/api/v1/worker-schedules/tick
```

手动触发某一个 schedule：

```bash
curl -X POST http://127.0.0.1:8001/api/v1/worker-schedules/<schedule_id>/trigger
```

暂停 / 恢复：

```bash
curl -X POST http://127.0.0.1:8001/api/v1/worker-schedules/<schedule_id>/pause

curl -X POST http://127.0.0.1:8001/api/v1/worker-schedules/<schedule_id>/resume \
  -H 'Content-Type: application/json' \
  -d '{}'
```

## 7. 让 worker 真正执行

schedule 只负责 enqueue，不负责执行。

要真正执行任务，仍然需要已有 worker 在线：

```bash
./scripts/start-mac-worker.sh
```

查看 worker queue / claim / report 结果，请走现有 API：

- `/api/v1/worker-runs`
- `/api/v1/workers/{worker_id}/claim`
- `/api/v1/workers/{worker_id}/runs/{run_id}/report`

## 8. 当前边界

当前单机 schedule 能力支持：

- `once`
- `interval`
- SQLite 持久化
- 手动 tick
- 可选后台 daemon
- 复用现有 worker queue + lease + report

当前不做：

- 复杂 cron 表达式
- 多节点去重调度
- 补历史 backlog 风暴式回放
- 任务级 SLA / 重试编排

如果后续确实需要：

- 每天几点 / 每周几几点
- 时区语义
- misfire 策略
- 更成熟的持久化 trigger

优先升级方向应是 **APScheduler**，而不是再引入一整套 Celery beat / worker 体系，也不是额外复制一套与当前控制面脱节的调度实现。

## 9. 对 requirement #4 的建议

对“销售统计与提成发放”这条线，建议仍然保持：

1. 先 Telegram 手动触发 requirement-4 CLI。
2. 人工审核结果稳定。
3. 再给该 CLI 挂 schedule。

不要反过来。
