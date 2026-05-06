# 联邦就绪 AAS v1 / Federation-Ready AAS v1

## 中文

Federation-Ready AAS v1 把项目推进到一个可落地的企业 AAS 群第一版：CrewAI-compatible agent 可以进入 AAS runner，公共 MCP 工具经权限、额度与审批治理后调用，联邦 peer 通过静态双边注册、租约、信用点额度和审计摘要提交远程任务。

v1 不做开放大市场、动态竞价、争议仲裁或真钱结算。它先固定最重要的闭环：每个企业保留自己的控制面、凭据和 promotion 权限，对外只出租受限 capability/worker 时长或交付结果。

### 核心命令

```bash
make crewai-demo
make mcp-doctor
make quota-doctor
make federation-doctor
make federation-demo
```

### 主要配置

- `configs/agents/aas_crewai_demo.yaml`：CrewAI-compatible demo agent manifest。
- `configs/mcp_servers.yaml`：MCP server registry；外部 server 默认关闭。
- `configs/tool_permissions.yaml`：工具风险层级、角色、agent allowlist 与审批策略。
- `configs/quota_policy.yaml`：用户与 peer 的信用点额度策略。
- `configs/federation_peers.yaml`：静态 peer、可发布 capability 与租约边界。
- `configs/butler/rule_candidates.yaml`：Butler 失败复盘产生的候选规则登记表；候选必须通过 `security_audit` 扫描后才能提升到正式规则。

### Butler 自修复闭环

Federation-ready v1 现在把 Butler 失败处理接到同一条本地治理脊柱上。Telegram 上下文追问只用 `追问 / Follow-up` 后的真实短句做路由，任务标题保留用户原话，完整上文只进入 `intent` / `request_text` 供执行或本地回答使用。

新增 `butler.context_status` canonical task 与 `butler_context_status` capability，用上一轮 assistant 结果里的 `知识库 / KB`、repo/topic 与同步状态生成即时中英双语回答。没有可解析上下文时返回本地无法确认，不升级到 Hermes 硬撞依赖。

新增 `ButlerFailureReviewService` 统一复盘 worker/MCP/federation 失败，稳定输出 `failure_kind`、`failure_review_id`、`route_repair_suggestion`、`candidate_skill_summary` 等 metadata，并写入 session timeline。Hermes 的新 review action 是 `hermes.failure_review`，定位为失败研判顾问；Hermes CLI 不可用时复盘归类为 `dependency_missing`，doctor 会通过 `Hermes CLI readiness` 明确暴露。

### API

- `GET /api/v1/mcp/servers`
- `GET /api/v1/mcp/tools`
- `POST /api/v1/mcp/tools/{tool_id}/call`
- `GET /api/v1/usage/quota`
- `GET /api/v1/usage/ledger`
- `GET /api/v1/federation/peers`
- `GET /api/v1/federation/capabilities`
- `POST /api/v1/federation/tasks`
- `GET /api/v1/federation/tasks/{task_id}`
- `POST /api/v1/federation/leases`
- `POST /api/v1/federation/leases/{lease_id}/revoke`

### 扩展边界

后续市场层应复用 v1 的 peer、lease、quota ledger 和 session timeline，不应另起账本。真钱结算、动态撮合、争议仲裁可以在这个账本之上新增 settlement adapter，但 provider 节点仍应本地执行，buyer 只拿结果和审计摘要。

## English

Federation-Ready AAS v1 moves the project to a practical first enterprise-federation release: CrewAI-compatible agents can enter the AAS runner, public MCP tools are governed by permission, quota, and approval checks, and federation peers can submit remote tasks through static bilateral registration, leases, credit-unit budgets, and audit summaries.

v1 does not implement an open marketplace, dynamic pricing, dispute arbitration, or real-money settlement. It first locks in the critical loop: every enterprise keeps its own control plane, credentials, and promotion authority, while exposing only scoped capability/worker time or delivered results.

### Core Commands

```bash
make crewai-demo
make mcp-doctor
make quota-doctor
make federation-doctor
make federation-demo
```

### Main Configs

- `configs/agents/aas_crewai_demo.yaml`: CrewAI-compatible demo agent manifest.
- `configs/mcp_servers.yaml`: MCP server registry; external servers are disabled by default.
- `configs/tool_permissions.yaml`: tool risk tiers, roles, agent allowlists, and approval policy.
- `configs/quota_policy.yaml`: credit-unit quota policy for users and peers.
- `configs/federation_peers.yaml`: static peers, published capabilities, and lease boundaries.
- `configs/butler/rule_candidates.yaml`: registry for Butler rule candidates produced by failure reviews; candidates must pass `security_audit` before promotion into stable rules.

### Butler Self-Repair Loop

Federation-ready v1 now connects Butler failure handling to the same local governance spine. Telegram contextual follow-ups route only on the real short text after `追问 / Follow-up`, task titles keep the user's original wording, and the full previous context stays in `intent` / `request_text` for execution or local answering.

The new `butler.context_status` canonical task and `butler_context_status` capability generate immediate bilingual answers from the previous assistant result's `知识库 / KB`, repo/topic, and sync status. If no parseable context exists, the system returns a local “unable to confirm” answer instead of escalating into Hermes dependency failures.

`ButlerFailureReviewService` now reviews worker/MCP/federation failures, emits stable metadata such as `failure_kind`, `failure_review_id`, `route_repair_suggestion`, and `candidate_skill_summary`, and writes the review to the session timeline. The new Hermes review action is `hermes.failure_review`, scoped to advisory failure analysis; when the Hermes CLI is unavailable, the review is classified as `dependency_missing`, and doctor exposes it through `Hermes CLI readiness`.

### APIs

- `GET /api/v1/mcp/servers`
- `GET /api/v1/mcp/tools`
- `POST /api/v1/mcp/tools/{tool_id}/call`
- `GET /api/v1/usage/quota`
- `GET /api/v1/usage/ledger`
- `GET /api/v1/federation/peers`
- `GET /api/v1/federation/capabilities`
- `POST /api/v1/federation/tasks`
- `GET /api/v1/federation/tasks/{task_id}`
- `POST /api/v1/federation/leases`
- `POST /api/v1/federation/leases/{lease_id}/revoke`

### Extension Boundary

Future marketplace layers should reuse v1 peer, lease, quota-ledger, and session-timeline records instead of creating a separate ledger. Real-money settlement, dynamic matching, and dispute handling can be added as settlement adapters above this ledger, while provider nodes still execute locally and buyers receive only results plus audit summaries.
