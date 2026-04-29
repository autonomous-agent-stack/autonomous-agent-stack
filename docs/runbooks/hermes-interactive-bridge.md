# Hermes Interactive Bridge Runbook

## 目标

本 runbook 用于启用、探测和演练 Hermes interactive bridge。它只覆盖当前已落地的持久化子集：HTTP transport、SQLite 会话映射、stream cursor 保存，以及 worker 注入。

This runbook is for enabling, probing, and drilling the Hermes interactive bridge. It covers only the implemented persistent subset: HTTP transport, SQLite session mapping, stream cursor storage, and worker injection.

## 启用条件

必须同时满足：

- AAS API 与 Mac worker 使用同一个 `AUTORESEARCH_API_DB_PATH`
- Mac worker 设置 `AUTORESEARCH_HERMES_INTERACTIVE_ENABLED=true`
- Mac worker 设置 `AUTORESEARCH_HERMES_GATEWAY_BASE_URL`
- Hermes gateway 的健康探针可访问

All of the following must be true:

- The AAS API and Mac worker use the same `AUTORESEARCH_API_DB_PATH`
- The Mac worker sets `AUTORESEARCH_HERMES_INTERACTIVE_ENABLED=true`
- The Mac worker sets `AUTORESEARCH_HERMES_GATEWAY_BASE_URL`
- The Hermes gateway health probe is reachable

## 配置示例

```bash
export AUTORESEARCH_API_DB_PATH=/path/to/artifacts/api/evaluations.sqlite3
export AUTORESEARCH_HERMES_INTERACTIVE_ENABLED=true
export AUTORESEARCH_HERMES_GATEWAY_BASE_URL=http://127.0.0.1:8765
export AUTORESEARCH_HERMES_GATEWAY_HEALTH_PATH=/health
export AUTORESEARCH_HERMES_GATEWAY_TIMEOUT_SECONDS=10
```

## 探针步骤

1. 启动 Hermes gateway。
2. 启动 AAS API。
3. 启动 Mac worker。
4. 查询 worker inventory，确认该 worker capability 包含 `hermes_interactive`，metadata 中 `hermes_gateway_configured=true`。
5. 发送显式 `execution_mode=interactive` 的 Hermes worker run。
6. 检查 run metadata/result 是否包含 `hermes_gateway_session_id` 与 `gateway_stream_cursor`。

Probe steps:

1. Start Hermes gateway.
2. Start the AAS API.
3. Start the Mac worker.
4. Query worker inventory and confirm the worker capabilities include `hermes_interactive`, with `hermes_gateway_configured=true` in metadata.
5. Submit an explicit `execution_mode=interactive` Hermes worker run.
6. Check whether run metadata/result includes `hermes_gateway_session_id` and `gateway_stream_cursor`.

## 重启恢复演练

1. 提交一个 interactive run，并确认 SQLite 中存在 `hermes_interactive_sessions` 记录。
2. 在 gateway 仍运行时重启 AAS API。
3. 重启或继续运行 Mac worker。
4. 再次触发同一 AAS session 的 interactive 请求。
5. 确认 bridge 复用已有 `hermes_gateway_session_id`，并从已保存 cursor 之后继续读取事件。

Restart recovery drill:

1. Submit an interactive run and confirm SQLite contains a `hermes_interactive_sessions` record.
2. Restart the AAS API while the gateway remains running.
3. Restart or keep the Mac worker running.
4. Trigger another interactive request for the same AAS session.
5. Confirm the bridge reuses the existing `hermes_gateway_session_id` and continues reading events after the saved cursor.

## 失败处置

- `interactive_bridge_unavailable`：检查 worker 是否启用 interactive、base URL 是否存在、健康探针是否成功。
- `RUNNING` 卡死：优先看 worker lease 是否仍刷新；必要时使用 worker run 的 `requeue` 或 `force-fail` 运维接口。
- gateway 无法回放 cursor：先 force-fail 当前 run，并保留 SQLite 记录用于人工复盘。

Failure handling:

- `interactive_bridge_unavailable`: check whether the worker enabled interactive mode, whether the base URL exists, and whether the health probe succeeds.
- Stuck `RUNNING`: first check whether the worker lease is still being refreshed; if needed, use the worker run `requeue` or `force-fail` operational endpoint.
- Gateway cannot replay from cursor: force-fail the current run first, and preserve the SQLite record for manual review.
