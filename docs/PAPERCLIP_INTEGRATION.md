# Paperclip 集成契约 / Paperclip Integration Contract

## 状态 / Status

中文：
本页是 Paperclip 与 AAS 协同边界、信任模型、术语口径与集成契约的单一真相来源。它基于当前仓库中实际存在的系统事实，而不是历史叙事或愿景性图示。

English:
This page is the single source of truth for Paperclip/AAS boundaries, trust model, terminology, and integration contract. It is grounded in the system that actually exists in this repository, not in historical narratives or aspirational diagrams.

中文：
如果本页与 `ARCHITECTURE.md` 或实现代码冲突，以 `ARCHITECTURE.md` 和代码为准，并应回写本页消除漂移。

English:
If this page conflicts with `ARCHITECTURE.md` or the implementation, follow `ARCHITECTURE.md` and the code first, then update this page to remove drift.

## 边界声明 / Boundary Statement

中文：
Paperclip 代表可替换的公司层编排，负责目标、预算、优先级与组织语义。AAS 代表受治理执行面，负责会话与运行记录、能力隔离、策略合并、验证、晋升与审计。两者是互补关系，不是替代关系。

English:
Paperclip represents a replaceable company layer for goals, budgets, priorities, and organizational semantics. AAS represents the governed execution plane for session/run records, capability isolation, policy merge, validation, promotion, and audit. They are complementary, not substitutes.

中文：
对外可以把 Paperclip 一类产品称为“零人公司”叙事入口；对内应统一为“公司层编排 + 受治理执行面”，避免把产品隐喻误当作信任模型。

English:
Externally, Paperclip-style products may use “zero-human company” as a narrative entry point. Internally, use “company-layer orchestration + governed execution plane” so the metaphor does not replace the trust model.

## 信任模型 / Trust Model

中文：
AAS 的不可外包边界是所有需要可证明信任、拒绝越权和可审计回放的能力，包括：

- `session` / `run` / `promotion` 的系统记录
- capability isolation 与 patch-only 默认执行
- deny-wins policy merge
- validation gate 与 promotion gate
- 审批、降级、审计追溯与可恢复性

English:
The non-outsourcable boundary in AAS is everything that requires provable trust, anti-escalation guarantees, and auditable replay, including:

- `session` / `run` / `promotion` as the system of record
- capability isolation and patch-only default execution
- deny-wins policy merge
- validation and promotion gates
- approvals, downgrade paths, auditability, and recoverability

中文：
Paperclip 或任何公司层只能下达“额外收紧”的业务约束，不应绕开 AAS 去放宽底线策略，也不应拥有直接晋升为分支、提交或 PR 的权限。

English:
Paperclip or any company layer may only send additional tightening constraints. It must not relax AAS base policy and must not own direct authority to promote changes into branches, commits, or PRs.

## 当前实现事实（截至 2026-04-15） / Current Implementation Facts (As of 2026-04-15)

中文：
当前仓库内与 Paperclip 相关的实现事实如下：

- `src/api/paperclip_router.py` 存在一个原型路由器。
- `src/autoresearch/api/main.py` 当前没有挂载该路由器，所以默认启动链路并不会暴露 `/api/v1/paperclip/*`。
- `POST /api/v1/paperclip/budget` 只是在进程内内存字典中记录 `department` 与 `target_budget`，返回 `request_id`。
- `POST /api/v1/paperclip/callback` 只是在进程内列表中记录 `roi`、`token_used`、`timestamp` 与可选 `department`，然后生成一条效率字符串。
- 当前实现不会创建 AAS `session`、`run`、审批流、验证流或晋升流，也不会投递消息队列或 durable state。

English:
The Paperclip-related implementation facts in this repository are:

- `src/api/paperclip_router.py` contains a prototype router.
- `src/autoresearch/api/main.py` does not currently mount that router, so default startup does not expose `/api/v1/paperclip/*`.
- `POST /api/v1/paperclip/budget` only records `department` and `target_budget` in a process-local in-memory dictionary and returns a generated `request_id`.
- `POST /api/v1/paperclip/callback` only records `roi`, `token_used`, `timestamp`, and optional `department` in a process-local list and returns a derived efficiency string.
- The current implementation does not create an AAS `session`, `run`, approval flow, validation flow, promotion flow, queue dispatch, or durable state.

中文：
因此，`docs/PAPERCLIP_API.md` 应被理解为“原型请求/响应形状说明”，而不是默认主应用已经承诺的产品级 API。

English:
Therefore, `docs/PAPERCLIP_API.md` should be read as a prototype request/response shape reference, not as a product-grade API already committed by the default main application.

## API 充分性判断 / API Adequacy Assessment

中文：
当前 `/budget` 与 `/callback` 只能覆盖“预算输入 + 指标回收”的最窄切片，不足以支撑真实的公司层编排与受治理执行面的闭环集成。

English:
The current `/budget` and `/callback` endpoints only cover the narrowest slice of “budget input + metric return,” which is not enough for a real integration between company-layer orchestration and a governed execution plane.

中文：
主要缺口包括：

- 缺少工作指令语义：没有 `objective`、`success_criteria`、`deliverable_type`、`deadline`
- 缺少关联键：没有稳定的 `request_id`、`external_correlation_id`、`run_id`、`session_id`
- 缺少生命周期事件：没有 `run.started`、`validation.completed`、`promotion.decision`、`artifact.ready`
- 缺少安全与可靠性语义：没有签名、重放防护、幂等键、事件去重、重试约定

English:
The main gaps are:

- missing work-order semantics: no `objective`, `success_criteria`, `deliverable_type`, or `deadline`
- missing correlation keys: no stable `request_id`, `external_correlation_id`, `run_id`, or `session_id`
- missing lifecycle events: no `run.started`, `validation.completed`, `promotion.decision`, or `artifact.ready`
- missing security and reliability semantics: no signing, replay protection, idempotency key, event dedupe, or retry contract

## 推荐契约形状 / Recommended Contract Shape

### 入站 Work Order / Inbound Work Order

中文：
Paperclip -> AAS 的预算接口应演进为 work order，而不是只传 `department` 与 `target_budget`。最小建议字段：

- `request_id` 或 `Idempotency-Key`
- `external_correlation_id`
- `objective`
- `success_criteria`
- `deliverable_type`，例如 `patch_artifact`、`draft_pr`、`report`
- `deadline`
- `budget_amount`、`currency`、`budget_scope`
- `max_token_cost`
- `requested_promotion_level`
- `requires_human_approval`
- 可选的额外收紧策略，例如允许路径、禁用路径、工具限制、网络限制

English:
The Paperclip -> AAS budget interface should evolve into a work order instead of only carrying `department` and `target_budget`. Minimum recommended fields:

- `request_id` or `Idempotency-Key`
- `external_correlation_id`
- `objective`
- `success_criteria`
- `deliverable_type`, for example `patch_artifact`, `draft_pr`, or `report`
- `deadline`
- `budget_amount`, `currency`, and `budget_scope`
- `max_token_cost`
- `requested_promotion_level`
- `requires_human_approval`
- optional tightening policy such as allowed paths, forbidden paths, tool restrictions, and network restrictions

### 出站事件流 / Outbound Event Stream

中文：
AAS -> Paperclip 的回传不应只剩一个终态 callback，更适合采用事件流或 webhook 事件类型。建议最小事件集合：

- `budget.accepted`
- `run.started`
- `run.progress`
- `run.completed`
- `run.failed`
- `run.canceled`
- `validation.completed`
- `promotion.requested`
- `promotion.decision`
- `artifact.ready`

English:
The AAS -> Paperclip return path should not be limited to a single terminal callback. An event stream or typed webhook model is a better fit. Recommended minimum event set:

- `budget.accepted`
- `run.started`
- `run.progress`
- `run.completed`
- `run.failed`
- `run.canceled`
- `validation.completed`
- `promotion.requested`
- `promotion.decision`
- `artifact.ready`

### 安全与重试语义 / Security and Retry Semantics

中文：
产品级契约至少应定义以下能力：

- 入站与出站请求签名
- 每个事件的唯一 `event_id`
- 幂等请求键
- 明确的重试与重复投递处理规则
- 审计可追溯的时间戳与来源标识

English:
At minimum, the product-grade contract should define:

- signed inbound and outbound requests
- a unique `event_id` per event
- idempotent request keys
- explicit retry and duplicate-delivery handling
- auditable timestamps and source identifiers

## 术语表 / Glossary

中文：

- `zero-human company`：对外叙事隐喻，不是内部信任模型
- `company layer orchestration`：公司层编排，关注目标、预算、优先级与组织语义
- `governed execution plane`：受治理执行面，关注 session、policy、validation、promotion、audit
- `execution surface`：可替换执行器，例如 OpenHands、Codex 或自定义 worker
- `promotion gate`：把 patch candidate 升级为更高权限产物前的显式审查关口

English:

- `zero-human company`: external narrative metaphor, not the internal trust model
- `company layer orchestration`: the layer for goals, budgets, priorities, and organizational semantics
- `governed execution plane`: the layer for session, policy, validation, promotion, and audit
- `execution surface`: a replaceable executor such as OpenHands, Codex, or a custom worker
- `promotion gate`: the explicit review point before a patch candidate can become a higher-privilege artifact

## 文档收敛规则 / Documentation Convergence Rules

中文：
从现在开始，Paperclip 相关文档按以下角色分工维护：

- `docs/PAPERCLIP_INTEGRATION.md`：权威边界与契约页
- `docs/PAPERCLIP_API.md`：当前原型接口形状参考
- `docs/p4-super-agent-stack-architecture-report.md`：历史/叙事文档
- `docs/p4-completion-report-2026-03-26.md`：历史/阶段性总结文档

English:
From now on, maintain Paperclip-related docs with the following roles:

- `docs/PAPERCLIP_INTEGRATION.md`: canonical boundary and contract page
- `docs/PAPERCLIP_API.md`: current prototype API shape reference
- `docs/p4-super-agent-stack-architecture-report.md`: historical/narrative document
- `docs/p4-completion-report-2026-03-26.md`: historical/stage-summary document
