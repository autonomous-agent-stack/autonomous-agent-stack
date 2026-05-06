# AAS Evergreen Agent Control Plane / AAS 长青 Agent 控制平面

## 中文

AAS 的长期定位不是更大的 Agent 框架，而是 Agent 框架之上的企业控制平面。CrewAI、LangGraph、Hermes、OpenHands、Haystack、MCP、A2A 和后续框架都作为可插拔 runtime、tool、knowledge service 或 federated agent 接入。

AAS Core 只固定长期抽象：Session、Capability、Runtime、Policy、Approval、Audit、Artifact、Workspace、Promotion 和 Lease。外部框架可以替换，AAS 的权限、额度、审批、审计、产物和联邦账本不替换。

核心命令：

```bash
make runtime-doctor
make capability-doctor
make mcp-doctor
make agent-reach-crewai-demo
make haystack-demo
make langgraph-demo
make a2a-demo
make evergreen-demo
```

## English

AAS is not positioned as a larger agent framework. It is an enterprise control plane above agent frameworks. CrewAI, LangGraph, Hermes, OpenHands, Haystack, MCP, A2A, and future frameworks plug in as runtimes, tools, knowledge services, or federated agents.

AAS Core keeps only long-lived abstractions stable: Session, Capability, Runtime, Policy, Approval, Audit, Artifact, Workspace, Promotion, and Lease. External frameworks may be replaced while AAS permission, quota, approval, audit, artifact, and federation ledgers remain stable.

Core commands:

```bash
make runtime-doctor
make capability-doctor
make mcp-doctor
make agent-reach-crewai-demo
make haystack-demo
make langgraph-demo
make a2a-demo
make evergreen-demo
```
