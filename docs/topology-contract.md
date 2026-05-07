# Agent Topology Contract / Agent 拓扑合同

## 中文

**状态**：Draft  
**范围**：公开 contract、schema 和 API 草案  
**不改变**：现有 GA gate、AAS core 行为、runtime 调度行为

本文定义 Agent Topology / Private Industry Package 的公开接入边界。它只描述 AAS 可以暴露和接收的通用拓扑事实，不引入任何行业私有实现、客户数据或业务策略。

机器可读 schema 位于 [`schemas/topology-contract.schema.json`](../schemas/topology-contract.schema.json)。

## English

**Status**: Draft  
**Scope**: public contract, schema, and API draft  
**Unchanged**: existing GA gates, AAS core behavior, and runtime scheduling behavior

This document defines the public integration boundary for Agent Topology and Private Industry Packages. It only describes generic topology facts that AAS may expose or receive. It does not introduce private industry implementations, customer data, or business policy.

The machine-readable schema lives at [`schemas/topology-contract.schema.json`](../schemas/topology-contract.schema.json).

## 中文

## Contract 对象

### `HostNode`

`HostNode` 表示承载 runtime、worker、MCP host 或 federation peer 的 host。它可以公开 host 类型、网络暴露范围、状态和 policy 引用，但不能公开真实机器密钥、内网敏感路径、个人账号或客户环境细节。

### `RuntimeNode`

`RuntimeNode` 表示 AAS 可治理的执行面，例如 gateway、coding worker、workflow worker、process worker、MCP tool host 或 federation agent。它只声明 runtime 类型、承载 host、状态、capability id、isolation profile 和 policy 引用。

### `AgentNode`

`AgentNode` 表示公开 agent card 或可治理 agent 入口。它可以声明角色、runtime 归属、capability id 和 card 引用，但不能嵌入私有 prompt、客户话术、价格规则或行业业务逻辑。

### `CapabilityBinding`

`CapabilityBinding` 把 `CapabilityManifest.capability_id` 绑定到某个 runtime、agent、host、resident worker 或 temporary client。它必须声明风险等级、是否需要 `Approval`、产物类型和 policy 引用。

### `TemporaryClient`

`TemporaryClient` 表示受 lease 限制的短期 client，例如一次性接入的本地工具、临时测试 client 或短效 worker。它必须有 `lease_id` 和 `expires_at`，过期后不得继续调用 capability。

### `ResidentWorker`

`ResidentWorker` 表示长期运行的 worker，例如本机 Mac worker、queue worker 或 MCP bridge。它必须公开 heartbeat、runtime 归属、capability id 和 policy 引用，供 AAS 判断可用性和治理边界。

## English

## Contract Objects

### `HostNode`

`HostNode` represents a host that runs runtimes, workers, MCP hosts, or federation peers. It may expose host type, network exposure scope, status, and policy references. It must not expose real machine secrets, sensitive internal paths, personal accounts, or customer environment details.

### `RuntimeNode`

`RuntimeNode` represents an AAS-governed execution surface such as a gateway, coding worker, workflow worker, process worker, MCP tool host, or federation agent. It only declares runtime type, owning host, status, capability ids, isolation profile, and policy references.

### `AgentNode`

`AgentNode` represents a public agent card or governable agent entrypoint. It may declare role, runtime ownership, capability ids, and card references. It must not embed private prompts, customer-facing scripts, price rules, or industry business logic.

### `CapabilityBinding`

`CapabilityBinding` binds a `CapabilityManifest.capability_id` to a runtime, agent, host, resident worker, or temporary client. It must declare risk tier, whether `Approval` is required, artifact types, and policy references.

### `TemporaryClient`

`TemporaryClient` represents a lease-scoped short-lived client, such as a one-time local tool, temporary test client, or short-lived worker. It must have `lease_id` and `expires_at`; after expiry it must not continue invoking capabilities.

### `ResidentWorker`

`ResidentWorker` represents a long-running worker, such as a local Mac worker, queue worker, or MCP bridge. It must expose heartbeat, runtime ownership, capability ids, and policy references so AAS can evaluate availability and governance boundaries.

## 中文

## API 草案

这些 endpoint 是公开合同草案，不代表本次变更新增运行时行为。

| Method | Path | Draft Response | 说明 |
| --- | --- | --- | --- |
| `GET` | `/api/v2/topology` | `TopologyDocument` | 返回完整拓扑快照。 |
| `GET` | `/api/v2/runtimes` | `{ "runtimes": RuntimeNode[] }` | 返回可治理 runtime 摘要。 |
| `GET` | `/api/v2/agents/cards` | `{ "agents": AgentNode[] }` | 返回公开 agent card 摘要，不返回私有 prompt。 |
| `GET` | `/api/v2/capabilities` | `{ "capabilities": CapabilityManifest[], "bindings": CapabilityBinding[] }` | 返回 capability manifest 与绑定关系。 |

### `GET /api/v2/topology`

响应必须符合 `agent-topology/v1` schema。实现时应从 AAS 现有 registry、runtime manifests、worker heartbeat、agent cards 和 capability registry 聚合，不应读取私有行业包内部模块。

### `GET /api/v2/runtimes`

响应只返回 `RuntimeNode` 级别的公开字段。runtime adapter 的内部配置、secret、真实本机路径和 provider 凭据不得出现在响应中。

### `GET /api/v2/agents/cards`

响应只返回 agent card 摘要。私有 prompt、客户话术、行业 SOP 和业务规则必须留在私有包内。

### `GET /api/v2/capabilities`

响应返回 AAS 可治理 capability 的 manifest 和 binding。业务实现只通过 `capability_id`、input/output schema、risk tier、policy refs、artifact types 与 AAS 对齐。

## English

## API Draft

These endpoints are public contract drafts. This change does not add runtime behavior.

| Method | Path | Draft Response | Description |
| --- | --- | --- | --- |
| `GET` | `/api/v2/topology` | `TopologyDocument` | Returns the full topology snapshot. |
| `GET` | `/api/v2/runtimes` | `{ "runtimes": RuntimeNode[] }` | Returns governable runtime summaries. |
| `GET` | `/api/v2/agents/cards` | `{ "agents": AgentNode[] }` | Returns public agent card summaries without private prompts. |
| `GET` | `/api/v2/capabilities` | `{ "capabilities": CapabilityManifest[], "bindings": CapabilityBinding[] }` | Returns capability manifests and bindings. |

### `GET /api/v2/topology`

The response must conform to the `agent-topology/v1` schema. An implementation should aggregate from existing AAS registries, runtime manifests, worker heartbeats, agent cards, and capability registries. It must not import private industry package internals.

### `GET /api/v2/runtimes`

The response only returns public `RuntimeNode` fields. Runtime adapter internals, secrets, real local paths, and provider credentials must not appear in the response.

### `GET /api/v2/agents/cards`

The response only returns agent card summaries. Private prompts, customer scripts, industry SOPs, and business rules must remain inside the private package.

### `GET /api/v2/capabilities`

The response returns governable capability manifests and bindings. Business implementations align with AAS only through `capability_id`, input/output schemas, risk tiers, policy refs, and artifact types.

## 中文

## 禁止事项

- 私有行业包不得 import AAS private internals。
- 行业业务逻辑不得进入 AAS core。
- 公开仓库不得包含真实客户、价格、人员、合同或账号数据。
- prompt-to-image MCP 不得暴露到 LAN 或 public network。
- topology response 不得携带 secret、token、真实本机私密路径或私有 prompt。

## English

## Prohibitions

- Private industry packages must not import AAS private internals.
- Industry business logic must not enter AAS core.
- The public repository must not contain real customer, price, personnel, contract, or account data.
- prompt-to-image MCP must not be exposed to LAN or the public network.
- Topology responses must not carry secrets, tokens, real private local paths, or private prompts.
