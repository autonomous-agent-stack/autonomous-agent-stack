# telegram-youtube-autoflow-ingress-v1

**决策日期 | Decision date:** 2026-04-24（持续更新 | rolling）  
**状态 | Status:** Active（入口 + 回写 + 取消/重试语义已落地 | ingress + writeback + cancel/retry semantics implemented）

## 目标 | Goal

**中文：** 通过当前 Telegram 网关暴露既有内部 `youtube_autoflow` 链路，不在聊天层复制 YouTube / GitHub 业务逻辑。

**English:** Expose the existing internal `youtube_autoflow` chain through the current Telegram gateway without duplicating YouTube or GitHub business logic in the chat layer.

## Scope

This slice includes:

- `src/autoresearch/api/routers/gateway_telegram.py`
- the existing Telegram webhook / poller bridge path
- enqueueing `task_type=youtube_autoflow` onto the existing Python control plane
- immediate Telegram acceptance / rejection / enqueue-failure feedback
- OpenClaw session event + metadata linkage for accepted and rejected ingress attempts
- focused tests for happy-path enqueue, fail-closed rejects, and non-YouTube fallback behavior

## Fixed v1 Decisions

- Telegram stays a thin ingress only:
  - extract message text
  - validate routing shape
  - enqueue the existing `youtube_autoflow`
  - return immediate receipt state
- `youtube_autoflow` remains the only source of truth for:
  - YouTube URL resolution
  - transcript / digest generation
  - GitHub publish routing
- supported ingress shape is exactly one URL in the message, and that URL must be YouTube
- multiple URLs fail closed with rejection
- malformed YouTube references fail closed with rejection
- non-YouTube messages keep the pre-existing Telegram gateway behavior
- receipt state is exposed as:
  - `accepted=true` with `metadata.status=accepted`
  - `accepted=false` with `metadata.status=rejected`
  - `accepted=false` with `metadata.status=failed` when enqueue itself fails
- accepted runs persist `run_id` plus Telegram/OpenClaw session linkage in metadata so later cancel / retract flows can target a stable control-plane id

## 非目标 | Non-goals

**中文：** 仍不在本切片承诺：Telegram 专用 YouTube 处理链、Telegram 专用 GitHub 发布路径、远端真实 PR 冒烟、TypeScript `agent-control-plane/` 改动、多智能体编排层、**隐式自动失败补救链**（仅手动 `/retry <run_id>` 与清晰 doctor/状态面）、依赖 Telegram **删除消息**的撤回（v1 仅编辑原 ack 气泡为已取消/已撤回）。

**English:** Still out of scope for this line: a Telegram-only YouTube processor, a Telegram-only GitHub publish path, remote real-PR smoke, TypeScript `agent-control-plane/` edits, a multi-agent orchestration layer, **implicit auto-remediation chains** (manual `/retry <run_id>` plus doctor/status surfaces only), and withdraw flows that **delete Telegram messages** (v1 edits the original ack bubble to cancelled/withdrawn only).

## Acceptance

- a Telegram message containing one valid YouTube URL enqueues the existing `youtube_autoflow`
- the queue item keeps `task_type=youtube_autoflow`
- the existing Mac standby worker can claim and execute that run unchanged
- GitHub publish still flows through `publish_youtube`
- invalid or ambiguous ingress fails closed
- focused tests cover accept / reject / fallback behavior

## 状态 | Status

**中文 — 已实现：**

- 单链接合法 YouTube 入队前：用 `send_message_get_message_id` 发 ack，并把 `telegram_queue_ack_message_id`、`telegram_completion_via_api`、`chat_id`、`message_thread_id` 写入队列 metadata。
- Mac worker 在自动流各阶段上报 `RUNNING`；API 侧对同一 ack 气泡做节流 live 编辑；metrics 使用 **`telegram_live_card_title`** 区分 YouTube 进度与 Hermes 运行中文案。
- 终态：`telegram_completion_card_text` 由 worker/API primary completion 写回；失败卡含阶段、错误类别、`run_id` 与 `/retry <run_id>` 提示；不自动派生补救任务。
- Telegram：`/cancel`（最近或指定 `run_id`）、`/retry <run_id>`（仅失败态）；队列级取消：`queued` 直接 `cancelled`，`running` 写 `cancel_requested` 并由 worker 协作停后上报 `cancelled`。

**English — Implemented:**

- On accept: send ack via `send_message_get_message_id`, then persist `telegram_queue_ack_message_id`, `telegram_completion_via_api`, `chat_id`, and `message_thread_id` in queue metadata.
- Mac worker reports `RUNNING` per autoflow stage; the API throttled-live-edits the same ack bubble; metrics set **`telegram_live_card_title`** so YouTube progress is not mislabeled as Hermes.
- Terminal state: `telegram_completion_card_text` is delivered via worker/API primary completion; failure cards include stage, error kind, `run_id`, and `/retry <run_id>`; no implicit auto-remediation enqueue.
- Telegram: `/cancel` (latest or explicit `run_id`) and `/retry <run_id>` (failed-only); queue cancel: `queued` → `cancelled`, `running` → `cancel_requested` with cooperative stop → `cancelled` report.

**中文 — 仍延后：** Linux/Mac 上 Telegram poller 自身的 failback 编排等。

**English — Still deferred:** e.g. Linux/Mac failback orchestration for the Telegram poller process itself.

## Related Decision

- [WhatsApp vs Telegram thin ingress comparison](./whatsapp-vs-telegram-thin-ingress.md)
- [Chat platform ingress recommendation](./chat-platform-ingress-recommendation-v1.md)
