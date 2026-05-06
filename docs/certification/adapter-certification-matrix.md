# Adapter Certification Matrix / Adapter 认证矩阵

## 中文

所有 adapter 默认 `experimental`。只有通过全部认证项，且存在 live integration path，才可以标记为 `stable`。少一项即降级为 `beta` 或 `experimental`。

认证项：

- real doctor
- real create_session / bind_session
- real run
- real stream
- real cancel
- real status
- real artifact collection
- error taxonomy
- policy hook
- approval hook
- Tool Broker enforcement
- Model Gateway enforcement
- Secret Lease enforcement
- SessionEvent mapping
- live integration test
- failure drill

适用范围：Hermes、OpenClaw、OpenHands、CrewAI、Haystack、LangGraph、LlamaIndex、Dify、AutoGen/AG2、Microsoft Agent Framework、Semantic Kernel、LangChain Agents、Flowise、LangFlow、A2A、MCP Tool Broker。

机器可读来源：`configs/certification/adapters.yaml`。

## English

All adapters default to `experimental`. An adapter may be marked `stable` only when every certification item passes and a live integration path exists. Any missing item downgrades the adapter to `beta` or `experimental`.

Certification items:

- real doctor
- real create_session / bind_session
- real run
- real stream
- real cancel
- real status
- real artifact collection
- error taxonomy
- policy hook
- approval hook
- Tool Broker enforcement
- Model Gateway enforcement
- Secret Lease enforcement
- SessionEvent mapping
- live integration test
- failure drill

Scope: Hermes, OpenClaw, OpenHands, CrewAI, Haystack, LangGraph, LlamaIndex, Dify, AutoGen/AG2, Microsoft Agent Framework, Semantic Kernel, LangChain Agents, Flowise, LangFlow, A2A, and MCP Tool Broker.

Machine-readable source: `configs/certification/adapters.yaml`.
