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
