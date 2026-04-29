# Hermes Interactive Bridge v2 规格草案
# Hermes Interactive Bridge v2 Draft Spec

本文档定义在 AAS 中把 `hermes gateway` 接成一等执行面的最小契约，目标是支持长会话与审批回流，同时保持 v1 oneshot lane 向后兼容。
This document defines the minimum contract for integrating `hermes gateway` as a first-class execution plane in AAS, targeting long-lived sessions and approval callbacks while preserving backward compatibility with the v1 oneshot lane.

## 目标 / Goals

- 保留现有 `runtime_id=hermes` 的 oneshot 行为，新增 `execution_mode=interactive`。
  Keep existing oneshot behavior for `runtime_id=hermes`, and add `execution_mode=interactive`.
- worker 注册 `capabilities` 可声明 `hermes_interactive`，用于调度分流。
  Worker registration can declare `hermes_interactive` in `capabilities` for routing.
- 审批、工具事件、流式状态通过结构化事件上报，不再只靠轮询 `status` 文本。
  Approval/tool/streaming signals are reported as structured events rather than plain status polling only.

## 路由契约 / Routing Contract

- Telegram 入口在 payload 中携带：
  Telegram ingress attaches the following payload fields:
  - `runtime_id: "hermes"`
  - `execution_mode: "oneshot" | "interactive"`
- `WorkerRuntimeDispatchService` 行为：
  `WorkerRuntimeDispatchService` behavior:
  - `oneshot`：走当前 `HermesRuntimeAdapterService`（v1）
    `oneshot`: keep current `HermesRuntimeAdapterService` (v1)
  - `interactive`：走 `HermesGatewayBridge.execute_interactive(payload)`
    `interactive`: route to `HermesGatewayBridge.execute_interactive(payload)`

## 会话模型 / Session Model

- AAS `session_id` 继续作为会话主键。
  AAS `session_id` remains the primary session key.
- interactive bridge 要持久化映射：
  interactive bridge must persist mapping:
  - `aas_session_id -> hermes_gateway_session_id`
  - `run_id -> gateway_stream_cursor`
- 控制面重启后，worker 需能按映射恢复订阅并继续上报。
  After control-plane restart, worker should restore subscriptions via persisted mapping and continue reporting.

## 事件模型 / Event Model

最小事件类型：
Minimum event types:

- `interactive.started`
- `interactive.progress`
- `interactive.approval_required`
- `interactive.approval_decision`
- `interactive.completed`
- `interactive.failed`

每个事件必须包含 `run_id`、`session_id`、`runtime_id`、`timestamp` 与 `event_id`。
Each event must include `run_id`, `session_id`, `runtime_id`, `timestamp`, and `event_id`.

## 安全边界 / Security Boundary

- `approval_mode` 与审批决策必须入审计日志，并绑定 `actor_user_id`。
  `approval_mode` and approval decisions must be audited with `actor_user_id`.
- 未授予审批权限的 channel 不得直接发出 `approval_decision=approve`。
  Channels without approval permission must not emit `approval_decision=approve`.

## 与 v1 兼容 / v1 Compatibility

- v1 文档 [`docs/hermes-runtime-v1.md`](./hermes-runtime-v1.md) 保持不变。
  v1 document remains unchanged.
- interactive 失败时返回 `error_kind=interactive_bridge_unavailable`，并附用户可读 hint。
  On interactive failure, return `error_kind=interactive_bridge_unavailable` with a user-readable hint.

