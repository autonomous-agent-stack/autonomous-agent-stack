# Autonomous Agent Stack

**中文：** Autonomous Agent Stack（AAS）现在定位为 **Evergreen Agent Control Plane**：它不是另一个“万能 Agent 框架”，而是运行在 CrewAI、LangGraph、Hermes、OpenHands、Haystack、MCP、A2A 和后续框架之上的企业控制面。

**English:** Autonomous Agent Stack (AAS) is now positioned as an **Evergreen Agent Control Plane**. It is not another all-in-one agent framework; it is the enterprise control plane above CrewAI, LangGraph, Hermes, OpenHands, Haystack, MCP, A2A, and future agent frameworks.

[![CI](https://github.com/autonomous-agent-stack/autonomous-agent-stack/workflows/CI/badge.svg)](https://github.com/autonomous-agent-stack/autonomous-agent-stack/actions/workflows/ci.yml)
[![Quality Gates](https://github.com/autonomous-agent-stack/autonomous-agent-stack/workflows/Quality%20Gates/badge.svg)](https://github.com/autonomous-agent-stack/autonomous-agent-stack/actions/workflows/quality-gates.yml)
[![RFC](https://img.shields.io/badge/RFC-4%20Draft-orange)](docs/rfc/)

---

## 最新状态 / Current Status

**中文：** 最新里程碑交付的是 Federation-Ready / Evergreen v1：AAS Core 保持小而稳定，外部框架全部通过 adapter、runtime、tool、knowledge service 或 federated agent 接入。已经落地的主线包括 RuntimeAdapter v1、CapabilityManifest v1、Tool Proxy + MCP Host、CrewAI 示例、Haystack 示例、LangGraph 示例和 A2A server/client 桥接。

**English:** The latest milestone delivers Federation-Ready / Evergreen v1. AAS Core stays small and stable while external frameworks plug in through adapters, runtimes, tools, knowledge services, or federated agents. The implemented main line includes RuntimeAdapter v1, CapabilityManifest v1, Tool Proxy + MCP Host, a CrewAI example, a Haystack example, a LangGraph example, and an A2A server/client bridge.

**中文：** 单机版和单企业内部路径已经可以作为开箱基线使用：`make setup -> make doctor -> make start` 启动控制面，`make evergreen-demo` 验证 Evergreen runtime/capability/tool/federation demo。CrewAI、Haystack、LangGraph、A2A 等成熟框架仍是可选依赖；未安装时 doctor 会返回 `degraded`，但不会阻止 AAS 启动。

**English:** The single-machine and single-enterprise path is usable as the default baseline: `make setup -> make doctor -> make start` starts the control plane, and `make evergreen-demo` validates the Evergreen runtime/capability/tool/federation demos. CrewAI, Haystack, LangGraph, A2A, and similar frameworks remain optional dependencies; when they are not installed, doctor reports `degraded` without blocking AAS startup.

**中文：** v1 不做开放市场、真钱结算、动态竞价或完整争议仲裁。现在的边界是双边联邦、静态 peer、租约、额度、审计、审批和结果交付；后续市场层会复用这些账本和治理事件。

**English:** v1 does not implement an open marketplace, real-money settlement, dynamic bidding, or full dispute arbitration. The current boundary is bilateral federation, static peers, leases, quota, audit, approvals, and result delivery; future marketplace layers should reuse these ledgers and governance events.

---

## AAS 是什么 / What AAS Is

**中文：** AAS 是面向长时运行 Agent 的受治理控制面。它回答企业长期不会过时的问题：谁能用、能用什么、用到什么数据、做了什么动作、谁批准、产出了什么、出了问题能不能追溯、结果能不能发布给客户或进入生产流程。

**English:** AAS is a governed control plane for long-running agents. It answers enterprise questions that do not go out of date: who can use the system, what they can use, what data was touched, what actions were taken, who approved them, what artifacts were produced, whether failures are traceable, and whether a result can be promoted to a customer-facing or production workflow.

**中文：** AAS 不把任一 Agent 框架当成 trusted core。CrewAI 可以负责多角色 persona，LangGraph 可以负责有状态 workflow，Hermes / OpenClaw 可以做交互入口和执行 worker，OpenHands 可以做 coding worker，Haystack 可以做 knowledge/RAG，MCP 可以提供工具，A2A 可以连接外部 agent；AAS 负责统一治理。

**English:** AAS does not treat any agent framework as the trusted core. CrewAI can provide multi-role personas, LangGraph can run stateful workflows, Hermes / OpenClaw can act as interactive gateways and workers, OpenHands can run coding work, Haystack can provide knowledge/RAG, MCP can provide tools, and A2A can connect external agents; AAS governs them all.

---

## 长期稳定抽象 / Long-Lived Abstractions

**中文：** AAS Core 只固定这些长期抽象：

**English:** AAS Core keeps only these long-lived abstractions stable:

- `Session`：可恢复的执行历史。 / Recoverable execution history.
- `Capability`：可被调用、租用或发布的能力。 / Callable, leasable, or publishable capability.
- `Runtime`：执行任务的外部或本地 runtime。 / External or local task runtime.
- `Policy`：权限、边界、风险和验证规则。 / Permission, boundary, risk, and validation rules.
- `Approval`：敏感动作的人审入口。 / Human approval for sensitive actions.
- `Audit`：谁、何时、用什么、做了什么的事实日志。 / Factual log of who did what, when, and with what.
- `Artifact`：结果、补丁、报告、引用和交付物。 / Results, patches, reports, citations, and deliverables.
- `Workspace`：隔离执行空间。 / Isolated execution workspace.
- `Promotion`：把结果上线、发出或写回系统的显式门。 / Explicit gate for publishing, sending, or writing results back.
- `Lease`：跨企业或跨团队租用 agent/worker 的边界。 / Boundary for renting agent/worker capacity across teams or enterprises.

---

## 当前已经落地 / What Is Implemented Now

**中文：** 当前实现已经包含：

**English:** The current implementation includes:

- **RuntimeAdapter v1：** `create_session`、`run`、`stream`、`cancel`、`status`、`doctor` 统一合同；`/api/v1/runtime` 统一发现 Hermes、OpenClaw、OpenHands、CrewAI、Haystack、LangGraph、A2A 等 runtime。
  **RuntimeAdapter v1:** unified `create_session`, `run`, `stream`, `cancel`, `status`, and `doctor` contract; `/api/v1/runtime` discovers Hermes, OpenClaw, OpenHands, CrewAI, Haystack, LangGraph, A2A, and other runtimes through one path.

- **CapabilityManifest v1：** `configs/capabilities/*.yaml` 解耦 capability 与具体框架；本地调用和 federation 发布复用同一 registry。
  **CapabilityManifest v1:** `configs/capabilities/*.yaml` decouples capabilities from concrete frameworks; local calls and federation publishing reuse the same registry.

- **Tool Proxy + MCP Host：** 受控 MCP 支持 `local`、`http`、`stdio` discovery 和 `tools/call`，工具调用前经过 permission、quota、approval、audit。
  **Tool Proxy + MCP Host:** governed MCP supports `local`, `http`, and `stdio` discovery plus `tools/call`, guarded by permission, quota, approval, and audit before execution.

- **CrewAI Adapter 示例：** `agent_reach_crewai_researcher` 展示 CrewAI 作为多角色 worker、Agent-Reach 作为公开资料读取工具、AAS 作为治理层的闭环。
  **CrewAI Adapter Example:** `agent_reach_crewai_researcher` demonstrates CrewAI as a multi-role worker, Agent-Reach as a public research tool, and AAS as the governance layer.

- **Haystack Adapter 示例：** Haystack 作为 knowledge/RAG runtime，输出带引用的 artifact。
  **Haystack Adapter Example:** Haystack acts as a knowledge/RAG runtime and emits citation-backed artifacts.

- **LangGraph Adapter 示例：** LangGraph 作为有状态 workflow runtime，checkpoint / interrupt / resume 映射到 AAS artifact 与 approval 语义。
  **LangGraph Adapter Example:** LangGraph acts as a stateful workflow runtime, with checkpoint / interrupt / resume mapped to AAS artifact and approval semantics.

- **A2A Server / Client 桥接：** AAS 可发布 capability card，也可把外部 A2A agent 包成 runtime；调用复用 federation peer、lease、quota、audit。
  **A2A Server / Client Bridge:** AAS can publish capability cards and wrap external A2A agents as runtimes; calls reuse federation peers, leases, quota, and audit.

- **Federation-ready v1：** 支持静态 peer、双边 capability 发布、agent/worker lease、联邦任务、额度账本和审计摘要。
  **Federation-ready v1:** supports static peers, bilateral capability publishing, agent/worker leases, federation tasks, quota ledger, and audit summaries.

---

## 架构位置 / Architecture Position

```text
用户 / API / Telegram / Web Panel / 外部企业
User / API / Telegram / Web Panel / External Enterprise
                  |
                  v
          AAS Agent Control Plane
  Session / Capability / Runtime / Policy
  Approval / Audit / Artifact / Promotion / Lease
                  |
      +-----------+-----------+-----------+
      |           |           |           |
      v           v           v           v
   Runtime      Tool       Knowledge   Federation
   Adapter      Proxy      Runtime     Gateway
      |           |           |           |
      v           v           v           v
CrewAI/LangGraph MCP       Haystack    A2A / Peer
Hermes/OpenHands Tools     RAG         Agent Lease
OpenClaw/Codex
```

**中文：** AAS 的价值不是把这些框架写死在 core 里，而是把它们降级成可替换执行面。框架越多，AAS 越有价值，因为企业真正需要长期保留的是身份、权限、会话、审批、审计、隔离、产物和晋升。

**English:** AAS does not hard-code these frameworks into core. It demotes them into replaceable execution surfaces. The more agent frameworks exist, the more valuable AAS becomes, because enterprises need identity, permission, session, approval, audit, isolation, artifacts, and promotion to remain stable over time.

---

## 快速开始 / Quick Start

**中文：** 基础环境：

**English:** Basic requirements:

- Python `3.11+`
- `make`
- SQLite（默认本地存储） / SQLite for default local storage
- Docker 或 Colima 仅在运行沙箱相关流程时需要 / Docker or Colima only for sandbox-backed flows

```bash
git clone https://github.com/autonomous-agent-stack/autonomous-agent-stack.git
cd autonomous-agent-stack

make setup
make doctor
make start
```

**中文：** 启动后常用入口：

**English:** Common local entry points after startup:

- API docs: `http://127.0.0.1:8001/docs`
- Control Plane v2: `http://127.0.0.1:8001/control-plane`
- Admin panel: `http://127.0.0.1:8001/panel`
- Health check: `http://127.0.0.1:8001/health`

---

## Evergreen 验证命令 / Evergreen Validation Commands

**中文：** 这些命令用于验证当前 Evergreen Agent Control Plane 主线：

**English:** These commands validate the current Evergreen Agent Control Plane path:

```bash
make runtime-doctor
make capability-doctor
make mcp-doctor
make agent-reach-crewai-demo
make haystack-demo
make langgraph-demo
make a2a-demo
make federation-demo
make evergreen-demo
```

**中文：** 常规本地验证：

**English:** Regular local validation:

```bash
make test-quick
make smoke-local
make hygiene-check
```

---

## 主要 API / Main APIs

**中文：** Evergreen v1 暴露的核心 API：

**English:** Core APIs exposed by Evergreen v1:

- `GET /api/v1/runtime`
- `GET /api/v1/runtime/{runtime_id}/manifest`
- `POST /api/v1/runtime/{runtime_id}/runs`
- `GET /api/v1/runtime/{runtime_id}/status`
- `GET /api/v1/capabilities`
- `GET /api/v1/capabilities/{capability_id}`
- `POST /api/v1/capabilities/{capability_id}/runs`
- `GET /api/v1/mcp/servers`
- `GET /api/v1/mcp/tools`
- `POST /api/v1/mcp/tools/{tool_id}/call`
- `GET /api/v1/federation/peers`
- `GET /api/v1/federation/capabilities`
- `POST /api/v1/federation/tasks`
- `POST /api/v1/federation/leases`
- `GET /api/v1/a2a/agent-card`
- `POST /api/v1/a2a/tasks`

**中文：** Control Plane v2 仍是本地任务治理主路径，负责 Butler task、run projection、approval 和 timeline：

**English:** Control Plane v2 remains the main local governance path for Butler tasks, run projections, approvals, and timelines:

- `POST /api/v2/butler/route`
- `POST /api/v2/butler/tasks`
- `POST /api/v2/tasks`
- `GET /api/v2/tasks/{id}`
- `POST /api/v2/tasks/{id}/approval`
- `GET /api/v2/sessions/{id}/timeline`
- `GET /api/v2/capabilities`
- `GET /api/v2/runs/{id}`
- `GET /api/v2/runs/{id}/events`

---

## 配置入口 / Configuration Entry Points

**中文：** 主要配置文件：

**English:** Main configuration files:

- `configs/runtime_agents/*.yaml`：注册 runtime / registers runtimes
- `configs/capabilities/*.yaml`：注册 capability / registers capabilities
- `configs/agents/*.yaml`：AEP process agent demo / AEP process agent demos
- `configs/mcp_servers.yaml`：MCP server registry
- `configs/tool_permissions.yaml`：tool permission and risk policy
- `configs/quota_policy.yaml`：user/peer quota policy
- `configs/federation_peers.yaml`：static federation peer registry

**中文：** 所有外部能力默认应显式配置后启用；敏感读取、外部写入和破坏性动作必须经过工具权限、额度、审批和审计路径。

**English:** External capabilities should be explicitly configured before use. Sensitive reads, external writes, and destructive actions must go through tool permission, quota, approval, and audit paths.

---

## 文档导航 / Documentation Map

**中文：** 先读这些：

**English:** Start here:

- [Evergreen Agent Control Plane](docs/evergreen-agent-control-plane.md)
- [RuntimeAdapter v1](docs/runtime-adapter-v1.md)
- [CapabilityManifest v1](docs/capability-manifest-v1.md)
- [Tool Proxy + MCP Host](docs/tool-proxy-mcp-host.md)
- [Adapter Examples v1](docs/adapter-examples-v1.md)
- [Federation-ready v1](docs/federation-ready-v1.md)
- [Architecture](ARCHITECTURE.md)
- [Agent Execution Protocol](docs/agent-execution-protocol.md)
- [OpenHands Controlled Backend Integration](docs/openhands-cli-integration.md)
- [Windows WSL2 Hermes Control Plane](docs/windows-wsl2-hermes-control-plane.md)

---

## 什么还不是 v1 目标 / What v1 Does Not Claim

**中文：** 当前 v1 不声称已经完成：

**English:** The current v1 does not claim to complete:

- 开放式 agent marketplace / Open agent marketplace
- 真实资金清结算 / Real-money clearing or settlement
- 动态竞价和自动撮合 / Dynamic bidding or automated matching
- 完整跨企业争议仲裁 / Full cross-enterprise dispute arbitration
- 每个外部框架的全功能托管平台 / Full managed platform coverage for every external framework

**中文：** v1 的重点是把底座合同、治理路径、registry、doctor、demo 和审计闭环跑通，后续 Dify、LlamaIndex、更多 MCP server、更多 A2A peer 都应按同一 RuntimeAdapter / CapabilityManifest 模型接入。

**English:** v1 focuses on making the base contracts, governance paths, registries, doctors, demos, and audit loop work. Future Dify, LlamaIndex, additional MCP servers, and additional A2A peers should plug in through the same RuntimeAdapter / CapabilityManifest model.

---

## 一句话 / One Sentence

**中文：** AAS 不是最大的 Agent 框架；它是管理所有 Agent 框架的企业控制系统。

**English:** AAS is not the biggest agent framework; it is the enterprise control system for governing all agent frameworks.
