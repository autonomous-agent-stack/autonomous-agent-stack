# Adapter Examples v1 / Adapter 示例 v1

## 中文

- CrewAI：`research.agent_reach_crewai` 演示 CrewAI 作为多角色研究 worker，Agent-Reach 作为公开资料读取工具，AAS 负责治理。
- Haystack：`knowledge.haystack_demo` 演示知识/RAG runtime，AAS 负责知识权限、引用审计和产物。
- LangGraph：`workflow.langgraph_order` 演示有状态 workflow runtime，AAS 保存 checkpoint 引用和审批事件。
- A2A：`federation.a2a_bridge` 演示 AAS 作为 A2A server/client，复用 federation lease、quota 和 audit。

所有示例都是可选依赖友好：缺少外部框架包时，doctor 返回 degraded，AAS Core 仍可启动。

## English

- CrewAI: `research.agent_reach_crewai` demonstrates CrewAI as a multi-role research worker, Agent-Reach as the public-source reading tool layer, and AAS as the governance plane.
- Haystack: `knowledge.haystack_demo` demonstrates a knowledge/RAG runtime where AAS owns knowledge permissions, citation audit, and artifacts.
- LangGraph: `workflow.langgraph_order` demonstrates a stateful workflow runtime where AAS stores checkpoint references and approval events.
- A2A: `federation.a2a_bridge` demonstrates AAS as an A2A server/client reusing federation leases, quota, and audit.

All examples are optional-dependency friendly: when a framework package is missing, doctor reports degraded and AAS Core still starts.
