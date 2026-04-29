# 飞书 Channel Driver v1
# Feishu Channel Driver v1

本文档定义飞书入口复用 Telegram 管家编排面的最小字段与回写语义，避免第二入口与 Hermes 执行面失配。
This document defines minimum fields and callback semantics for a Feishu ingress that reuses the Telegram butler orchestration layer, avoiding execution-plane drift.

## 复用原则 / Reuse Principles

- 队列 payload 与 worker 执行逻辑复用现有 `claude_runtime` / `hermes` 路径。
  Reuse existing `claude_runtime` / `hermes` queue payload and worker execution paths.
- channel driver 只负责消息平台差异：发送、编辑、回调、按钮。
  Channel driver should handle platform-specific messaging only: send/edit/callback/button.

## 统一字段 / Unified Metadata Fields

所有 channel 的任务卡必须包含：
All channel task cards must include:

- `run_id`
- `runtime_id`（hermes / claude）
  `runtime_id` (hermes / claude)
- `agent_name`（空值占位 `（未命名）| (unnamed)`）
  `agent_name` (empty fallback: `（未命名）| (unnamed)`)
- `status`
- `summary`（可选）
  `summary` (optional)

## 回写时机 / Callback Timing

- ack：同步发送「已入队」消息。
  ack: send synchronous “queued” message.
- live：按节流策略更新 RUNNING 卡（默认 30s）。
  live: throttled RUNNING updates (default 30s).
- terminal：成功/失败统一编辑同一条卡片；编辑失败时 fallback 发送新消息。
  terminal: edit the same card for success/failure; fallback to send-new on edit failure.

## 审批回调 / Approval Callback

- interactive 模式下，飞书卡片按钮回调应映射到统一审批事件：
  In interactive mode, Feishu card callbacks should map to unified approval events:
  - `interactive.approval_decision=approve`
  - `interactive.approval_decision=reject`

## 非目标 / Non-goals

- 本文档不定义 Hermes gateway 内部协议。
  This document does not define the internal Hermes gateway protocol.
- 本文档不改变 v1 oneshot 运行时契约。
  This document does not alter the v1 oneshot runtime contract.

